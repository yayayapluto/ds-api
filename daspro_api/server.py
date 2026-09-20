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
import json
import mimetypes
import re
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .ai import KlienAi
from .compiler import KompilatorC
from .config import Pengaturan
from .errors import DasproError, InputTidakValid, TidakDitemukan
from .jobs import GudangPekerjaan
from .pipeline import Pipeline
from .request import (
    ambil_berkas,
    ambil_semua_berkas,
    baca_permintaan,
    field,
    field_bool,
    field_json,
)
from .skillbridge import Skill

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


class LayananDaspro:
    """Kumpulan hal yang dipakai semua permintaan: pengaturan dan pekerjaan."""

    def __init__(self, pengaturan: Pengaturan, wajib_ai: bool = True):
        self.p = pengaturan
        self.p.data_dir.mkdir(parents=True, exist_ok=True)
        self.skill = Skill(pengaturan.skill_dir)
        self.gcc = KompilatorC(pengaturan)
        self.klien = KlienAi(pengaturan)
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
        """Catat permintaan ke stdout dengan bentuk yang mudah dibaca."""
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {format % args}")

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

    def _kirim_error(self, e: Exception):
        if isinstance(e, DasproError):
            self._kirim(e.status, e.ke_dict())
            return
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

    def _cari_berkas_job(self, job, nama: str) -> Path:
        """Cari berkas hasil pekerjaan, baik di folder job maupun folder kerja."""
        kandidat = [job.folder / nama, job.folder / "kerja" / nama]
        for k in kandidat:
            if k.is_file():
                return k
        raise TidakDitemukan(f"berkas {nama} tidak ada di pekerjaan {job.id}")

    def _kirim_berkas(self, berkas: Path, nama=None):
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
            "Content-Disposition", f'attachment; filename="{nama or berkas.name}"'
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
                    "ai_model": p.ai_model,
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
            if len(bagian) >= 5 and bagian[3] == "files":
                nama = "/".join(bagian[4:])
                if not NAMA_BERKAS_AMAN.match(nama) or ".." in nama:
                    raise InputTidakValid("nama berkas tidak boleh dipakai")
                self._kirim_berkas(self._cari_berkas_job(job, nama))
                return

        raise TidakDitemukan(f"endpoint {self.path} tidak ada")

    def _post(self):
        bagian = self._bagian_jalur()

        if bagian == ["v1", "jobs"]:
            self._mulai_pekerjaan()
            return

        if len(bagian) == 4 and bagian[:2] == ["v1", "jobs"] and bagian[3] == "cancel":
            job = self.layanan.pekerjaan.batalkan(bagian[2])
            self._kirim(200, {"ok": True, **job.ke_dict()})
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
        p = self.layanan.p

        def tugas(job):
            return self.layanan.pipeline.kerjakan(
                job,
                berkas_modul=berkas_modul,
                berkas_lkp=berkas_lkp,
                identitas=identitas,
                opsi=opsi,
            )

        job = self.layanan.pekerjaan.buat(
            {
                "modul": Path(berkas_modul).name,
                "lkp": Path(berkas_lkp).name if berkas_lkp else None,
                "identitas": identitas,
                "opsi": opsi,
                "model": p.ai_model,
            },
            tugas,
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
    httpd = ThreadingHTTPServer((pengaturan.host, pengaturan.port), handler)
    httpd.daemon_threads = True
    return httpd


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
