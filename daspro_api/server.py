"""Layanan HTTP memakai pustaka bawaan Python.

Endpoint yang tersedia:
    GET  /health                     keadaan layanan
    GET  /v1/skill                   keterangan folder skill yang dipakai
    POST /v1/jobs                    unggah modul + template, mulai pekerjaan
    GET  /v1/jobs                    daftar pekerjaan
    GET  /v1/jobs/{id}               status dan kemajuan satu pekerjaan
    GET  /v1/jobs/{id}/result        ringkasan hasil
    GET  /v1/jobs/{id}/download      unduh berkas ZIP hasil
    GET  /v1/jobs/{id}/files/{nama}  unduh satu berkas hasil
    POST /v1/jobs/{id}/cancel        batalkan pekerjaan
    POST /v1/verify                  kompilasi dan uji berkas .c
    POST /v1/cek-bahasa              periksa gaya bahasa laporan
    POST /v1/docx/peta               lihat tempat kosong di template docx
    POST /v1/docx/isi                isi template docx dari mapping
"""
import errno
import json
import mimetypes
import re
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from daspro_api import __version__
from daspro_api.ai import KlienAi
from daspro_api.compiler import KompilatorC
from daspro_api.config import Pengaturan
from daspro_api.errors import (
    AiBelumDiatur,
    DasproError,
    InputTidakValid,
    TidakDitemukan,
)
from daspro_api.jobs import GudangPekerjaan
from daspro_api.logbook import catatan_layanan
from daspro_api.pipeline import Pipeline
from daspro_api.request import (
    ambil_berkas,
    ambil_semua_berkas,
    baca_permintaan,
    field,
    field_bool,
    field_json,
)
from daspro_api.skillbridge import Skill

JENIS_BERKAS = {
    ".c": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".zip": "application/zip",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}
NAMA_BERKAS_AMAN = re.compile(r"^[A-Za-z0-9._/-]+$")

# Folder halaman web yang ikut di dalam paket ini.
FOLDER_WEB = Path(__file__).resolve().parent / "web"

# Jenis berkas yang boleh dikirim ke peramban. Selain ini ditolak, supaya
# berkas lain di folder web tidak bisa dibaca paksa.
JENIS_WEB = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}


class LayananDaspro:
    """Kumpulan hal yang dipakai semua permintaan: pengaturan dan pekerjaan."""

    def __init__(self, pengaturan: Pengaturan, wajib_ai: bool = True):
        self.p = pengaturan
        self.p.data_dir.mkdir(parents=True, exist_ok=True)
        self.skill = Skill(pengaturan.skill_dir)
        self.gcc = KompilatorC(pengaturan)
        self.klien = KlienAi(pengaturan)
        # Catatan harian layanan. Kunci API didaftarkan sebagai nilai
        # rahasia supaya tidak pernah ikut tertulis ke berkas.
        self.catatan = catatan_layanan(pengaturan.data_dir)
        self.catatan.tambah_rahasia(pengaturan.ai_api_key)
        self.catatan.tulis(
            f"layanan mulai: {pengaturan.host}:{pengaturan.port}, "
            f"model {pengaturan.ai_model}",
            "mulai",
        )
        # Layanan ini tidak boleh jalan tanpa AI: kode C wajib datang dari
        # model sungguhan, bukan jawaban tiruan.
        if wajib_ai:
            self.klien.periksa()
        self.pekerjaan = GudangPekerjaan(pengaturan)
        self.pipeline = Pipeline(pengaturan, skill=self.skill, klien=self.klien)
        self.unggahan = self.p.data_dir / "unggahan"
        self.unggahan.mkdir(parents=True, exist_ok=True)
        self.mulai = time.time()


class Penanganan(BaseHTTPRequestHandler):
    server_version = f"daspro-api/{__version__}"
    layanan: LayananDaspro  # selalu diisi oleh buat_server
    batas_unggah = 32 * 1024 * 1024

    # --- alat bantu ------------------------------------------------------
    def log_message(self, format, *args):
        """Catat permintaan ke stdout dan ke berkas catatan harian."""
        baris = f"{self.address_string()} {format % args}"
        print(f"[{time.strftime('%H:%M:%S')}] {baris}")
        self.layanan.catatan.tulis(baris, "permintaan")

    def log_error(self, format, *args):
        """Catat permintaan yang gagal ke berkas catatan harian."""
        baris = f"{self.address_string()} {format % args}"
        print(f"[{time.strftime('%H:%M:%S')}] {baris}")
        self.layanan.catatan.tulis(baris, "permintaan-gagal")

    def _kirim(self, kode: int, data, jenis: str = "application/json; charset=utf-8"):
        if isinstance(data, (dict, list)):
            badan = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        elif isinstance(data, str):
            badan = data.encode("utf-8")
        else:
            badan = data
        self.send_response(kode)
        self.send_header("Content-Type", jenis)
        self.send_header("Content-Length", str(len(badan)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(badan)

    def _kirim_log(self, job):
        """Kirim catatan pekerjaan sebagai berkas teks.

        Pekerjaan lama (dibuat sebelum catatan berkas ada) belum punya
        ``job.log``. Untuk itu catatan disusun ulang dari riwayat tahap,
        supaya tautannya tidak pernah buntu.
        """
        berkas = job.catatan.berkas
        if berkas.is_file():
            self._kirim_berkas(berkas, nama=f"{job.id}.log")
            return
        baris = [f"# Catatan pekerjaan {job.id}"]
        baris.append(f"status: {job.status} ({job.tahap})")
        baris.append(f"dibuat: {job.dibuat}")
        baris.append(f"selesai: {job.selesai_pada}")
        if job.error:
            baris.append(f"galat: {job.error}")
        if job.detail_error:
            baris.append(f"keterangan: {job.detail_error}")
        baris.append("")
        baris.append("# Riwayat tahap")
        for catat in job.log or []:
            baris.append(
                f"[{catat.get('waktu', '')}] {catat.get('tahap', '')}: "
                f"{catat.get('pesan', '')}"
            )
        isi = ("\n".join(baris) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(isi)))
        self.send_header("Content-Disposition", f'attachment; filename="{job.id}.log"')
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(isi)

    def _kirim_error(self, e: Exception):
        if isinstance(e, DasproError):
            self.layanan.catatan.tulis(f"{e.kode}: {e.pesan}", "galat")
            self._kirim(e.status, e.ke_dict())
            return
        # Kesalahan di luar dugaan: jejak lengkap masuk berkas catatan,
        # yang dikirim ke pemanggil hanya ringkasannya.
        self.layanan.catatan.tulis(traceback.format_exc(), "galat-dalam")
        self._kirim(
            500,
            {
                "ok": False,
                "error": "internal_error",
                "pesan": f"{type(e).__name__}: {e}",
                "jejak": traceback.format_exc().splitlines()[-3:],
            },
        )

    def _cek_token(self) -> None:
        wajib = self.layanan.p.auth_token
        if not wajib:
            return
        dikirim = self.headers.get("Authorization") or ""
        if dikirim.removeprefix("Bearer ").strip() != wajib:
            raise InputTidakValid("token akses salah atau tidak dikirim")

    def _bagian_jalur(self) -> list:
        jalur = self.path.split("?", 1)[0]
        return [b for b in jalur.strip("/").split("/") if b]

    def _isi(self) -> dict:
        return baca_permintaan(self, self.batas_unggah, self.layanan.unggahan / self._sesi())

    def _sesi(self) -> str:
        return str(abs(hash(self.client_address)) % 10_000)

    def _berkas_web(self, jalur: str) -> Path:
        """Cari berkas halaman web dengan aman.

        Semua jalur diselesaikan dulu, lalu dipastikan masih berada di
        dalam folder web. Jadi permintaan seperti `../../.env` tidak bisa
        membaca berkas di luar folder itu.
        """
        if not FOLDER_WEB.is_dir():
            raise TidakDitemukan(
                "halaman web belum ada. Folder daspro_api/web tidak ditemukan."
            )
        nama = jalur.strip("/") or "index.html"
        if ".." in nama.split("/"):
            raise InputTidakValid("jalur berkas tidak boleh dipakai")

        kandidat = FOLDER_WEB / nama
        if kandidat.is_dir():
            kandidat = kandidat / "index.html"
        try:
            nyata = kandidat.resolve()
            dasar = FOLDER_WEB.resolve()
        except OSError as e:
            raise InputTidakValid(f"jalur berkas tidak bisa dibaca: {e}") from e
        if dasar not in nyata.parents and nyata != dasar:
            raise InputTidakValid("jalur berkas keluar dari folder web")
        if not nyata.is_file():
            raise TidakDitemukan(f"berkas {nama} tidak ada")
        if nyata.suffix.lower() not in JENIS_WEB:
            raise InputTidakValid(f"jenis berkas {nyata.suffix} tidak dilayani")
        return nyata

    def _kirim_halaman(self, jalur: str):
        berkas = self._berkas_web(jalur)
        # Halaman web wajib dirender di peramban, bukan diunduh.
        self._kirim_berkas(berkas, disposition="inline")

    def _cari_berkas_job(self, job, nama: str) -> Path:
        """Cari berkas hasil pekerjaan, baik di folder job maupun folder kerja."""
        kandidat = [job.folder / nama, job.folder / "kerja" / nama]
        for k in kandidat:
            if k.is_file():
                return k
        raise TidakDitemukan(f"berkas {nama} tidak ada di pekerjaan {job.id}")

    def _kirim_berkas(self, berkas: Path, nama=None, disposition: str = "attachment"):
        if not berkas.is_file():
            raise TidakDitemukan(f"berkas {berkas.name} tidak ada")
        jenis = JENIS_BERKAS.get(
            berkas.suffix.lower(), mimetypes.guess_type(berkas.name)[0] or "application/octet-stream"
        )
        data = berkas.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", jenis)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition", f'{disposition}; filename="{nama or berkas.name}"'
        )
        self.end_headers()
        self.wfile.write(data)

    # --- penanganan permintaan ------------------------------------------
    def do_GET(self):
        try:
            self._cek_token()
            self._get()
        except Exception as e:  # semua error dijawab JSON, bukan halaman HTML
            self._kirim_error(e)

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        try:
            self._cek_token()
            self._post()
        except Exception as e:
            self._kirim_error(e)

    def _get(self):
        bagian = self._bagian_jalur()
        if bagian == ["health"]:
            p = self.layanan.p
            self._kirim(
                200,
                {
                    "ok": True,
                    "layanan": "daspro-api",
                    "versi": __version__,
                    "uptime_detik": int(time.time() - self.layanan.mulai),
                    "skill_siap": self.layanan.skill.siap,
                    "folder_skill": str(self.layanan.skill.folder),
                    "ai_siap": p.ai_siap,
                    "ai": p.ai_ringkas(),
                    "gcc": self.layanan.gcc.periksa_gcc(),
                    "jumlah_pekerjaan": len(self.layanan.pekerjaan.daftar(1000)),
                },
            )
            return

        if bagian == ["v1", "skill"]:
            skill = self.layanan.skill
            self._kirim(
                200,
                {
                    "ok": True,
                    "folder": str(skill.folder),
                    "siap": skill.siap,
                    "skrip": sorted(f.name for f in skill.scripts.glob("*.py")),
                    "acuan": sorted(f.name for f in skill.references.glob("*.md")),
                    "contoh_kode": sorted(f.name for f in skill.references.glob("contoh_*.c")),
                },
            )
            return

        if bagian == ["v1", "jobs"]:
            self._kirim(200, {"ok": True, "pekerjaan": self.layanan.pekerjaan.daftar()})
            return

        if len(bagian) >= 3 and bagian[:2] == ["v1", "jobs"]:
            job = self.layanan.pekerjaan.ambil(bagian[2])
            if len(bagian) == 3:
                self._kirim(200, {"ok": True, **job.ke_dict(sertakan_log=True)})
                return
            if len(bagian) == 4 and bagian[3] == "result":
                self._kirim(
                    200,
                    {
                        "ok": True,
                        "job_id": job.id,
                        "status": job.status,
                        "hasil": job.hasil,
                        "error": job.error,
                    },
                )
                return
            if len(bagian) == 4 and bagian[3] == "download":
                if not job.berkas_zip.is_file():
                    raise TidakDitemukan("berkas ZIP belum siap")
                self._kirim_berkas(job.berkas_zip)
                return
            if len(bagian) == 4 and bagian[3] == "log":
                self._kirim_log(job)
                return
            if len(bagian) >= 5 and bagian[3] == "files":
                nama = "/".join(bagian[4:])
                if not NAMA_BERKAS_AMAN.match(nama) or ".." in nama:
                    raise InputTidakValid("nama berkas tidak boleh dipakai")
                self._kirim_berkas(self._cari_berkas_job(job, nama))
                return

        # Bukan endpoint API: coba sajikan sebagai halaman web.
        if bagian and bagian[0] in {"v1", "health"}:
            raise TidakDitemukan(f"endpoint {self.path} tidak ada")
        self._kirim_halaman(self.path.split("?", 1)[0])

    def _post(self):
        bagian = self._bagian_jalur()

        if bagian == ["v1", "jobs"]:
            self._mulai_pekerjaan()
            return

        if len(bagian) == 4 and bagian[:2] == ["v1", "jobs"] and bagian[3] == "cancel":
            job = self.layanan.pekerjaan.batalkan(bagian[2])
            self._kirim(200, {"ok": True, **job.ke_dict()})
            return

        if bagian == ["v1", "ai", "uji"]:
            self._uji_ai()
            return

        if bagian == ["v1", "verify"]:
            self._verify()
            return

        if bagian == ["v1", "cek-bahasa"]:
            self._cek_bahasa()
            return

        if bagian == ["v1", "docx", "peta"]:
            self._docx_peta()
            return

        if bagian == ["v1", "docx", "isi"]:
            self._docx_isi()
            return

        raise TidakDitemukan(f"endpoint {self.path} tidak ada")

    # --- endpoint pekerjaan ---------------------------------------------
    def _mulai_pekerjaan(self):
        data = self._isi()
        berkas_modul = ambil_berkas(data, "modul")
        berkas_lkp = ambil_berkas(data, "lkp")
        if berkas_modul is None:
            raise InputTidakValid(
                "berkas modul belum dikirim. Kirim kolom 'modul' berisi PDF atau docx."
            )
        identitas = field_json(data, "identitas", {})
        if not isinstance(identitas, dict):
            raise InputTidakValid("kolom 'identitas' harus berupa objek JSON")
        opsi = {
            "buat_copyable": field_bool(data, "buat_copyable", True),
            "isi_docx": field_bool(data, "isi_docx", True),
        }
        # Kredensial dari pengguna, kalau dikirim. Isinya hanya dipakai
        # selama pekerjaan ini berjalan, dan tidak pernah ditulis ke disk.
        kredensial = self._kredensial(data)

        def tugas(job):
            return self.layanan.pipeline.kerjakan(
                job,
                berkas_modul=berkas_modul,
                berkas_lkp=berkas_lkp,
                identitas=identitas,
                opsi=opsi,
                kredensial=kredensial,
            )

        job = self.layanan.pekerjaan.buat(
            {
                "modul": Path(berkas_modul).name,
                "lkp": Path(berkas_lkp).name if berkas_lkp else None,
                "identitas": identitas,
                "opsi": opsi,
                # Sengaja hanya nama modelnya. Kunci dan alamat tidak ikut,
                # supaya berkas status.json tidak pernah memuat rahasia.
                "model": (kredensial or {}).get("model") or self.layanan.p.ai_model,
                "pakai_kredensial_sendiri": bool(kredensial),
            },
            tugas,
        )
        job.rahasia((kredensial or {}).get("api_key"))
        job.catatan.tulis(
            f"permintaan baru: modul {Path(berkas_modul).name}, "
            f"lkp {Path(berkas_lkp).name if berkas_lkp else '-'}, "
            f"model {(kredensial or {}).get('model') or self.layanan.p.ai_model}, "
            f"kredensial {'pengguna' if kredensial else 'server'}",
            "masuk",
        )
        self.layanan.catatan.tulis(
            f"pekerjaan {job.id} dibuat oleh {self.address_string()}", "pekerjaan"
        )
        self._kirim(
            202,
            {
                "ok": True,
                "job_id": job.id,
                "status": job.status,
                "pesan": "Pekerjaan masuk antrean. Tanyakan kemajuannya lewat GET /v1/jobs/"
                + job.id,
                "status_url": f"/v1/jobs/{job.id}",
                "download_url": f"/v1/jobs/{job.id}/download",
            },
        )

    def _kredensial(self, data: dict):
        """Baca kredensial AI yang dikirim pengguna, kalau ada.

        Kunci hanya dipakai di memori selama pekerjaan berjalan. Nilai ini
        tidak pernah ditulis ke berkas status, tidak masuk catatan tahap,
        dan tidak pernah dikirim balik ke pemanggil.

        Kunci wajib ada. Halaman web selalu mengirim alamat dan nama model
        (dari daftar pilihan), walau kolom kuncinya dibiarkan kosong. Kalau
        alamat itu dipakai tanpa kunci, kunci milik server akan terkirim ke
        alamat lain, dan layanan AI akan menolaknya. Jadi kalau kuncinya
        kosong, seluruh kredensial dianggap tidak dikirim.
        """
        kunci = (field(data, "ai_api_key") or "").strip()
        alamat = (field(data, "ai_base_url") or "").strip()
        model = (field(data, "ai_model") or "").strip()
        if not kunci:
            return None
        return {"api_key": kunci, "base_url": alamat, "model": model}

    # --- endpoint AI ------------------------------------------------------
    def _uji_ai(self):
        """Uji kredensial AI yang dikirim, tanpa menyimpannya."""
        data = self._isi()
        kredensial = self._kredensial(data) or {}
        p = self.layanan.p.dengan(
            ai_api_key=kredensial.get("api_key"),
            ai_base_url=kredensial.get("base_url"),
            ai_model=kredensial.get("model"),
        )
        # Diperiksa di sini, bukan di dalam klien, supaya aturannya tetap
        # berlaku walau kliennya diganti saat pengujian.
        if not p.ai_siap:
            raise AiBelumDiatur(
                "kunci, alamat, dan nama model harus terisi untuk menguji koneksi."
            )
        klien = self.layanan.pipeline.buat_klien(p)
        hasil = klien.uji_koneksi()
        self._kirim(200, {"ok": True, **hasil})

    # --- endpoint pemeriksaan -------------------------------------------
    def _verify(self):
        data = self._isi()
        berkas = ambil_semua_berkas(data, "files") or ambil_semua_berkas(data, "file")
        if not berkas:
            raise InputTidakValid("tidak ada berkas .c yang dikirim")
        hasil = []
        for f in berkas:
            if f.suffix.lower() != ".c":
                hasil.append(
                    {"berkas": f.name, "ok": False, "pesan": "bukan berkas .c"}
                )
                continue
            biner = f.with_suffix("")
            kompil = self.layanan.gcc.kompilasi(f, biner)
            if not kompil.ok:
                hasil.append(
                    {
                        "berkas": f.name,
                        "ok": False,
                        "peringatan": kompil.peringatan,
                        "pesan_error": kompil.pesan_error,
                    }
                )
                continue
            masukan = field(data, f"masukan:{f.name}", "") or field(data, "masukan", "")
            jalan = self.layanan.gcc.jalan(biner, masukan=str(masukan))
            hasil.append(
                {
                    "berkas": f.name,
                    "ok": not kompil.peringatan,
                    "peringatan": kompil.peringatan,
                    "kode_keluar": jalan.kode_keluar,
                    "keluaran": jalan.keluaran,
                    "pesan_error": jalan.pesan_error,
                    "timeout": jalan.timeout,
                }
            )
        jumlah_ok = sum(1 for h in hasil if h.get("ok"))
        self._kirim(
            200,
            {
                "ok": jumlah_ok == len(hasil),
                "jumlah": len(hasil),
                "lolos": jumlah_ok,
                "hasil": hasil,
            },
        )

    def _cek_bahasa(self):
        data = self._isi()
        berkas = ambil_semua_berkas(data, "files")
        if not berkas:
            raise InputTidakValid("tidak ada berkas laporan yang dikirim")
        laporan = self.layanan.skill.cek_bahasa([str(f) for f in berkas])
        self._kirim(200, {"ok": laporan["lulus"], **laporan})

    # --- endpoint docx ---------------------------------------------------
    def _docx_peta(self):
        data = self._isi()
        template = ambil_berkas(data, "template")
        if template is None:
            raise InputTidakValid("berkas template docx belum dikirim")
        kerja = Path(template).parent / (Path(template).stem + "_kerja")
        peta = self.layanan.skill.peta_docx(template, kerja)
        self._kirim(
            200,
            {
                "ok": True,
                "jumlah_sel_kosong": len(peta.get("sel_kosong") or []),
                "jumlah_baris_titik": len(peta.get("baris_titik") or []),
                "peta": peta,
            },
        )

    def _docx_isi(self):
        data = self._isi()
        template = ambil_berkas(data, "template")
        if template is None:
            raise InputTidakValid("berkas template docx belum dikirim")
        mapping = field_json(data, "mapping", None)
        if not isinstance(mapping, dict):
            raise InputTidakValid(
                "kolom 'mapping' harus objek JSON berisi 'sel' dan 'titik'"
            )
        kerja = Path(template).parent / (Path(template).stem + "_kerja")
        self.layanan.skill.peta_docx(template, kerja)
        hasil = Path(template).parent / f"{Path(template).stem}_terisi.docx"
        laporan = self.layanan.skill.isi_docx(kerja, mapping, hasil)
        self._kirim(200, {"ok": True, **laporan, "berkas": hasil.name})


def buat_server(pengaturan: Pengaturan, wajib_ai: bool = True) -> ThreadingHTTPServer:
    """Siapkan server HTTP siap dijalankan.

    `wajib_ai` hanya dimatikan oleh pengujian, yang memakai klien AI tiruan.
    Pada pemakaian sungguhan nilainya selalu true, sehingga layanan menolak
    jalan kalau AI belum diatur.
    """
    layanan = LayananDaspro(pengaturan, wajib_ai=wajib_ai)
    handler = type("PenangananSiap", (Penanganan,), {"layanan": layanan})
    handler.batas_unggah = pengaturan.max_upload_bytes
    httpd = _bind_server(
        pengaturan.host, pengaturan.port, handler, pengaturan.port_fallback
    )
    httpd.daemon_threads = True
    return httpd


def _bind_server(host, port, handler, fallback) -> ThreadingHTTPServer:
    """Bind server; bila portnya sudah dipakai, turun ke port berikutnya.

    Menghindari layanan gagal total sekadar karena satu port bentrok (mis.
    dipakai alat lain). Port yang memang terpakai terbaca di
    ``httpd.server_address[1]``.
    """
    attempts = max(1, fallback)
    for i in range(attempts):
        try:
            return ThreadingHTTPServer((host, port), handler)
        except OSError as e:
            if e.errno != errno.EADDRINUSE:
                raise
            if i == attempts - 1:
                raise
            print(f"  port {port} sudah dipakai, mencoba {port + 1} ...")
            port += 1
    raise RuntimeError("tidak ada port yang bisa dipakai")


def jalankan(pengaturan: Pengaturan) -> int:
    """Jalankan server sampai dihentikan dengan Ctrl+C."""
    httpd = buat_server(pengaturan)
    p = pengaturan
    print(f"daspro-api {__version__} jalan di http://{p.host}:{p.port}")
    print(f"folder kerja  : {p.data_dir}")
    print(f"folder skill  : {p.skill_dir}")
    print(f"layanan AI    : {p.ai_model} lewat {p.ai_base_url}")
    print("hentikan dengan Ctrl+C")
    try:
        httpd.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        print("\nberhenti atas permintaan pengguna")
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0
