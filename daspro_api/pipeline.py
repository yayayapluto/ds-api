"""Alur pengerjaan satu modul dari berkas masukan sampai berkas ZIP.

Tahapannya berurutan dan tiap tahap melaporkan kemajuannya, supaya
pemanggil bisa memantau lewat endpoint status pekerjaan.
"""
import shlex
import shutil
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from daspro_api.ai import KlienAi
from daspro_api.compiler import KompilatorC
from daspro_api.config import Pengaturan
from daspro_api.errors import AiGagal, DasproError, InputTidakValid
from daspro_api.extract import cari_soal, teks_berkas
from daspro_api.prompts import prompt_analisis, prompt_kode, prompt_laporan, sistem_dasar
from daspro_api.report import susun, tulis
from daspro_api.sanitize import bersihkan, bersihkan_dalam, cari_pelanggar
from daspro_api.skillbridge import Skill

WAJIB_IDENTITAS = ("nama", "nim", "kelas", "modul")


def rapikan_identitas(identitas: dict) -> dict:
    """Pastikan identitas lengkap, dan kosongkan yang tidak diisi."""
    bersih = {k: ("" if v is None else str(v).strip()) for k, v in (identitas or {}).items()}
    kurang = [k for k in WAJIB_IDENTITAS if not bersih.get(k)]
    if kurang:
        raise InputTidakValid(
            "identitas belum lengkap, yang kurang: " + ", ".join(kurang)
        )
    bersih["judul_modul"] = bersih.get("judul_modul") or ""
    return bersihkan_dalam(bersih)


class Pipeline:
    """Penggerak utama: berkas masuk, berkas ZIP keluar."""

    def __init__(self, pengaturan: Pengaturan, skill=None, klien=None):
        self.p = pengaturan
        self.skill = skill or Skill(pengaturan.skill_dir)
        self.klien = klien or KlienAi(pengaturan)
        self.gcc = KompilatorC(pengaturan)
        # Pabrik klien. Pada pemakaian sungguhan selalu KlienAi, jadi kode C
        # tetap ditulis oleh model asli. Pengujian boleh menggantinya.
        self.buat_klien = KlienAi

    def periksa_siap(self) -> None:
        """Pastikan AI dan gcc siap sebelum pekerjaan dimulai.

        Dipanggil di awal `kerjakan` supaya pekerjaan gagal cepat dengan
        pesan jelas, bukan berhenti di tengah jalan setelah berkas dibuat.
        """
        self.klien.periksa()
        self.skill.periksa()
        self.gcc.periksa_gcc()

    def klien_untuk(self, kredensial):
        """Pilih klien AI: dari kredensial job, atau milik server.

        Kredensial yang dikirim pengguna lewat halaman web tidak pernah
        disimpan. Objek pengaturan salinannya hanya hidup selama pekerjaan
        ini berjalan, lalu ikut terbuang bersama variabel lokalnya.
        """
        if not kredensial:
            return self.klien
        p = self.p.dengan(
            ai_api_key=kredensial.get("api_key"),
            ai_base_url=kredensial.get("base_url"),
            ai_model=kredensial.get("model"),
        )
        return self.buat_klien(p)

    # --- alat bantu ------------------------------------------------------
    def _catat(self, job, teks: str, tahap: str = "") -> None:
        """Tulis ke catatan pekerjaan, kalau pekerjaannya punya catatan.

        Dipakai supaya pipeline tetap bisa dipanggil dengan pengganti
        pekerjaan yang sederhana (mis. di pengujian).
        """
        catatan = getattr(job, "catatan", None)
        if catatan is not None:
            catatan.tulis(teks, tahap)

    def _cek_batal(self, job) -> None:
        if job is not None and job.batal.is_set():
            raise InputTidakValid("pekerjaan dibatalkan")

    def _minta_json(self, job, prompt: str, tahap: str, klien=None) -> dict:
        self._cek_batal(job)
        klien = klien or self.klien
        mulai = time.time()
        try:
            data = klien.lengkapi_json(prompt, sistem=sistem_dasar(self.skill))
        except DasproError as e:
            self._catat(
                job,
                f"panggilan AI gagal setelah {time.time() - mulai:.1f} detik: "
                f"{e.pesan}",
                "ai-gagal",
            )
            raise
        self._catat(
            job,
            f"panggilan AI ({tahap}) selesai dalam {time.time() - mulai:.1f} detik",
            "ai",
        )
        if not isinstance(data, dict):
            raise AiGagal("jawaban AI bukan objek JSON")
        return bersihkan_dalam(data)

    def _tulis_kode(self, folder: Path, nama_berkas: str, kode: str) -> Path:
        nama = bersihkan(Path(nama_berkas).name) or "program.c"
        if not nama.endswith(".c"):
            nama += ".c"
        berkas = folder / nama
        berkas.parent.mkdir(parents=True, exist_ok=True)
        berkas.write_text(bersihkan(kode).rstrip() + "\n", encoding="utf-8")
        return berkas

    # --- tahapan ---------------------------------------------------------
    def baca_masukan(self, berkas_modul: Path, berkas_lkp=None) -> dict:
        modul = teks_berkas(Path(berkas_modul))
        lkp = teks_berkas(Path(berkas_lkp)) if berkas_lkp else ""
        return {"modul": modul, "lkp": lkp, "soal_modul": cari_soal(modul)}

    def analisis_soal(self, job, isi: dict, identitas: dict, klien=None) -> dict:
        prompt = prompt_analisis(self.skill, isi["modul"], isi["lkp"], identitas)
        data = self._minta_json(job, prompt, "analisis", klien)
        soal = data.get("soal")
        if not isinstance(soal, list) or not soal:
            raise AiGagal("AI tidak mengembalikan daftar soal")
        rapi = []
        for i, s in enumerate(soal, 1):
            if not isinstance(s, dict):
                continue
            nama = bersihkan(str(s.get("nama_berkas") or f"latihan_{i:02d}.c"))
            if not nama.endswith(".c"):
                nama += ".c"
            rapi.append(
                {
                    "id": str(s.get("id") or f"soal_{i}"),
                    "nama_berkas": nama,
                    "folder": bersihkan(str(s.get("folder") or "")).strip("/"),
                    "jenis": str(s.get("jenis") or "terbimbing"),
                    "judul": str(s.get("judul") or f"Soal {i}"),
                    "deskripsi": str(s.get("deskripsi") or ""),
                    "kasus_uji": s.get("kasus_uji") or [],
                    "bagian": str(s.get("bagian") or s.get("kode") or ""),
                }
            )
        if not rapi:
            raise AiGagal("daftar soal dari AI kosong setelah dibaca")
        data["soal"] = rapi
        if not identitas.get("judul_modul"):
            identitas["judul_modul"] = str(data.get("judul") or "")
        return data

    def tulis_semua_kode(
        self, job, analisis: dict, identitas: dict, folder: Path, klien=None
    ) -> list:
        hasil = []
        soal = analisis["soal"]
        total = len(soal)
        for i, s in enumerate(soal, 1):
            self._cek_batal(job)
            persen = 10 + int(45 * (i - 1) / max(1, total))
            job.maju(
                "kode",
                f"Membuat kode {s['nama_berkas']} ({i} dari {total}).",
                persen,
            )
            catatan_perbaikan = None
            kode = ""
            penjelasan = ""
            tabel_uji = []
            percobaan = 0
            for percobaan in range(self.p.max_repair + 1):
                jawab = self._minta_json(
                    job,
                    prompt_kode(self.skill, s, identitas, catatan_perbaikan),
                    "kode",
                    klien,
                )
                kode = str(jawab.get("kode") or "").strip()
                penjelasan = str(jawab.get("penjelasan") or "").strip()
                tabel_uji = jawab.get("tabel_uji") or []
                if not kode:
                    catatan_perbaikan = {"kode": "", "catatan": "Jawaban sebelumnya kosong."}
                    continue
                if "int main" not in kode:
                    catatan_perbaikan = {
                        "kode": kode,
                        "catatan": "Kode belum memuat fungsi main.",
                    }
                    continue
                sub = folder / s["folder"] if s["folder"] else folder
                berkas = self._tulis_kode(sub, s["nama_berkas"], kode)
                kompil, _ = self.gcc.kompilasi_dan_jalan(berkas, masukan="")
                if kompil.ok and not kompil.peringatan:
                    break
                masalah = []
                if not kompil.ok:
                    masalah.append("gagal dikompilasi:\n" + kompil.pesan_error[:800])
                if kompil.peringatan:
                    masalah.append("masih ada peringatan:\n" + "\n".join(kompil.peringatan[:6]))
                catatan_perbaikan = {"kode": kode, "catatan": "\n".join(masalah)}

            sub = folder / s["folder"] if s["folder"] else folder
            berkas = self._tulis_kode(sub, s["nama_berkas"], kode)
            hasil.append(
                {
                    "id": s["id"],
                    "judul": s["judul"],
                    "nama_berkas": s["nama_berkas"],
                    "folder": s["folder"],
                    "jalur": berkas.relative_to(folder).as_posix(),
                    "jenis": s["jenis"],
                    "kode": kode,
                    "penjelasan": penjelasan,
                    "tabel_uji": tabel_uji,
                    "kasus_uji": [],
                    "catatan": "",
                    "percobaan": percobaan + 1,
                }
            )
        return hasil

    def uji_semua(self, job, analisis: dict, hasil_kode: list, folder: Path) -> list:
        soal = {s["id"]: s for s in analisis["soal"]}
        total = len(hasil_kode)
        for i, h in enumerate(hasil_kode, 1):
            self._cek_batal(job)
            job.maju(
                "uji",
                f"Menguji {h['nama_berkas']} ({i} dari {total}).",
                55 + int(15 * (i - 1) / max(1, total)),
            )
            s = soal.get(h["id"]) or {}
            berkas = folder / h["jalur"]
            kasus = s.get("kasus_uji") or []
            if not kasus:
                kasus = [{"masukan": "", "harapan": "program berjalan tanpa masukan"}]
            baris = []
            for k in kasus:
                if not isinstance(k, dict):
                    k = {"masukan": str(k)}
                masukan = str(k.get("masukan") or "")
                kompil, jalan = self.gcc.kompilasi_dan_jalan(berkas, masukan=masukan)
                if not kompil.ok or jalan is None:
                    baris.append(
                        {
                            "masukan": masukan,
                            "harapan": str(k.get("harapan") or "-"),
                            "keluaran": "(gagal dikompilasi) " + kompil.pesan_error[:200],
                            "kode_keluar": 1,
                            "status": "perlu dicek",
                        }
                    )
                    continue
                keluaran = (jalan.keluaran or "").strip()
                # Program yang menolak masukan tidak valid memang berhenti
                # dengan kode keluar 1, jadi itu masih dianggap wajar. Yang
                # perlu dicek adalah program yang berhenti karena sinyal,
                # tidak mengeluarkan apa pun, atau berjalan terlalu lama.
                if jalan.timeout or jalan.kode_keluar < 0 or not keluaran:
                    status = "perlu dicek"
                else:
                    status = "sesuai"
                baris.append(
                    {
                        "masukan": masukan,
                        "harapan": str(k.get("harapan") or "-"),
                        "keluaran": keluaran,
                        "kode_keluar": jalan.kode_keluar,
                        "status": status,
                    }
                )
            h["kasus_uji"] = baris
            sesuai = sum(1 for b in baris if b["status"] == "sesuai")
            ditolak = sum(
                1 for b in baris if b["kode_keluar"] not in (0, None) and b["status"] == "sesuai"
            )
            catatan = (
                f"Program diuji {len(baris)} kali dengan masukan berbeda. "
                f"{sesuai} kali keluarannya sesuai harapan."
            )
            if ditolak:
                catatan += (
                    f" Di antaranya {ditolak} kali program sengaja berhenti karena "
                    "masukannya tidak masuk akal."
                )
            h["catatan"] = catatan
        return hasil_kode

    def buat_laporan(
        self,
        job,
        isi: dict,
        analisis: dict,
        identitas: dict,
        hasil_kode: list,
        klien=None,
        peta_lkp=None,
    ) -> dict:
        pertanyaan = [
            q.get("pertanyaan")
            for bg in (analisis.get("bagian") or [])
            if isinstance(bg, dict)
            for q in (bg.get("analisis") or [])
            if isinstance(q, dict)
        ]
        prompt = prompt_laporan(
            self.skill, isi["modul"], isi["lkp"], identitas, hasil_kode, pertanyaan,
            peta_lkp=peta_lkp,
        )
        return self._minta_json(job, prompt, "laporan", klien)

    # --- pengisian template docx ----------------------------------------
    def isi_template(self, job, kerja: Path, peta: dict, laporan_ai: dict) -> dict:
        mapping_ai = laporan_ai.get("isian_lkp")
        if not isinstance(mapping_ai, dict):
            raise AiGagal("AI tidak mengembalikan isian template LKP")
        mapping = {}
        kurang = []
        for jenis, entri, atribut in (
            ("sel", peta.get("sel_kosong", []), "kunci"),
            ("titik", peta.get("baris_titik", []), "no"),
        ):
            jawaban = mapping_ai.get(jenis, {})
            if not isinstance(jawaban, dict):
                raise AiGagal(f"isian LKP bagian {jenis} harus berupa objek JSON")
            kunci_sah = {str(item[atribut]) for item in entri}
            if jawaban.keys() - kunci_sah:
                raise AiGagal(f"isian LKP bagian {jenis} memuat kunci di luar peta template")
            mapping[jenis] = {}
            for item in entri:
                kunci = str(item[atribut])
                nilai = jawaban.get(kunci, "")
                if not isinstance(nilai, str):
                    raise AiGagal(f"isian LKP {jenis}:{kunci} harus berupa teks")
                nilai = bersihkan(nilai).strip()
                if nilai.casefold().rstrip(".") == "sudah dikerjakan sesuai modul":
                    raise AiGagal(f"isian LKP {jenis}:{kunci} berisi jawaban generik")
                if item.get("wajib", True) and not nilai:
                    kurang.append(f"{jenis}:{kunci}")
                if nilai:
                    mapping[jenis][kunci] = nilai

        if kurang:
            raise AiGagal(
                f"AI belum menjawab {len(kurang)} isian LKP; DOCX tidak diterbitkan",
                detail=", ".join(kurang),
            )
        hasil_docx = kerja.parent / "LKP_terisi.docx"
        laporan = self.skill.isi_docx(kerja, mapping, hasil_docx)
        if not laporan["struktur_utuh"]:
            raise InputTidakValid("struktur template LKP berubah setelah pengisian")
        laporan["sel_kosong_di_template"] = len(peta.get("sel_kosong", []))
        laporan["baris_titik_di_template"] = len(peta.get("baris_titik", []))
        return {"berkas": hasil_docx, "laporan": laporan}

    # --- penyusunan hasil ------------------------------------------------
    def bungkus_zip(self, folder: Path, nama: str) -> Path:
        perintah = ["#!/bin/sh", "set -eu", 'cd -- "$(dirname -- "$0")"']
        for sumber in sorted(folder.rglob("*.c")):
            if not sumber.is_file():
                continue
            relatif = sumber.relative_to(folder)
            biner = Path("bin") / relatif.with_suffix("")
            perintah.append(shlex.join(["mkdir", "-p", biner.parent.as_posix()]))
            perintah.append(shlex.join([
                "gcc", "-std=c11", "-Wall", "-Wextra", "-O0",
                "./" + relatif.as_posix(), "-o", biner.as_posix(),
            ]))
        perintah.append("printf '%s\\n' 'Kompilasi selesai. Biner ada di bin/.'")
        skrip = folder / "kompilasi.sh"
        skrip.write_text("\n".join(perintah) + "\n", encoding="utf-8")
        skrip.chmod(0o755)
        tujuan = folder / nama
        with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.rglob("*")):
                if not f.is_file() or f.name == nama:
                    continue
                z.write(f, f.relative_to(folder).as_posix())
        return tujuan

    # --- alur utama ------------------------------------------------------
    def kerjakan(
        self,
        job,
        berkas_modul: Path,
        berkas_lkp=None,
        identitas=None,
        opsi=None,
        kredensial=None,
    ) -> dict:
        opsi = opsi or {}
        folder = Path(job.folder) / "kerja"
        folder.mkdir(parents=True, exist_ok=True)
        identitas = rapikan_identitas(identitas or {})

        # Kredensial dari job dipakai kalau ada. Kalau tidak, dipakai
        # kredensial milik server. Kredensial job tidak pernah ditulis ke
        # disk; hanya hidup selama pekerjaan ini berjalan.
        klien = self.klien_untuk(kredensial)

        # AI, gcc, dan folder skill diperiksa di awal. Kalau ada yang belum
        # siap, pekerjaan berhenti di sini dengan pesan jelas, bukan gagal
        # di tengah setelah separuh berkas dibuat.
        self._catat(
            job,
            f"berkas masuk: modul {Path(berkas_modul).name}, "
            f"lkp {Path(berkas_lkp).name if berkas_lkp else '-'}, "
            f"opsi {opsi}",
            "berkas",
        )
        self._catat(
            job,
            f"AI: {klien.p.ai_model} lewat {klien.p.ai_base_url}",
            "konfigurasi",
        )
        job.maju("periksa", "Memeriksa kesiapan AI dan gcc.", 2)
        klien.periksa()
        self.skill.periksa()
        self.gcc.periksa_gcc()

        job.maju("baca", "Membaca modul dan template LKP.", 3)
        isi = self.baca_masukan(Path(berkas_modul), berkas_lkp)

        job.maju("analisis", "Menyusun daftar soal dari modul.", 8)
        analisis = self.analisis_soal(job, isi, identitas, klien)

        hasil_kode = self.tulis_semua_kode(job, analisis, identitas, folder, klien)

        job.maju("uji", "Menjalankan program dengan nilai batas.", 55)
        hasil_kode = self.uji_semua(job, analisis, hasil_kode, folder)

        docx_hasil = None
        laporan_docx = None
        nomor = identitas.get("modul")
        with tempfile.TemporaryDirectory(prefix="daspro_docx_") as tmp:
            kerja = Path(tmp) / "template"
            peta = None
            if berkas_lkp and opsi.get("isi_docx", True):
                peta = self.skill.peta_docx(Path(berkas_lkp), kerja)
            job.maju("laporan", "Menyusun isi laporan.", 72)
            laporan_ai = self.buat_laporan(
                job, isi, analisis, identitas, hasil_kode, klien, peta_lkp=peta,
            )
            if peta is not None:
                job.maju("docx", "Mengisi template LKP tanpa mengubah format.", 78)
                keluaran = self.isi_template(job, kerja, peta, laporan_ai)
                laporan_docx = keluaran["laporan"]
                docx_hasil = folder / f"LKP_Modul_{nomor}_{bersihkan(str(identitas.get('nim')))}.docx"
                shutil.move(str(keluaran["berkas"]), str(docx_hasil))

        job.maju("susun", "Merangkai berkas laporan.", 80)
        sumber = [Path(berkas_modul).name] + ([Path(berkas_lkp).name] if berkas_lkp else [])
        md_teks = susun(identitas, analisis, hasil_kode, laporan_ai, sumber)
        md_path = tulis(md_teks, folder / f"jawaban_LKP_Modul_{nomor}.md")

        html_path = None
        if opsi.get("buat_copyable", True):
            job.maju("html", "Membuat versi HTML yang mudah disalin.", 84)
            html_path = self.skill.md_ke_copyable(
                md_path, folder / f"jawaban_LKP_Modul_{nomor}_copyable.html"
            )


        # --- pemeriksaan akhir -------------------------------------------
        job.maju("cek", "Memeriksa bahasa dan karakter tulisan.", 93)
        periksa_berkas = [md_path] + ([html_path] if html_path else [])
        cek = self.skill.cek_bahasa([str(x) for x in periksa_berkas])
        pelanggar = {}
        for f in periksa_berkas:
            pelanggar.update(cari_pelanggar(Path(f).read_text(encoding="utf-8")))

        ringkasan = {
            "modul": nomor,
            "judul_modul": identitas.get("judul_modul"),
            "jumlah_soal": len(analisis["soal"]),
            "soal": [
                {
                    "id": h["id"],
                    "nama_berkas": h["jalur"],
                    "jenis": h["jenis"],
                    "percobaan": h["percobaan"],
                    "jumlah_kasus": len(h["kasus_uji"]),
                    "sesuai": sum(1 for b in h["kasus_uji"] if b["status"] == "sesuai"),
                }
                for h in hasil_kode
            ],
            "berkas": {
                "laporan_md": md_path.name,
                "laporan_html": html_path.name if html_path else None,
                "lkp_docx": docx_hasil.name if docx_hasil else None,
                "kompilasi": "kompilasi.sh",
            },
            "cek_bahasa": {"lulus": cek["lulus"], "jumlah_temuan": cek["jumlah"]},
            "karakter_non_keyboard": pelanggar,
            "isi_template": laporan_docx,
        }

        job.maju("bungkus", "Membungkus semua berkas jadi satu ZIP.", 97)
        nama_zip = f"daspro_modul_{nomor}_{bersihkan(str(identitas.get('nim')))}.zip"
        zip_path = self.bungkus_zip(folder, nama_zip)

        ringkasan["zip"] = {
            "nama": zip_path.name,
            "jalur": str(zip_path),
            "ukuran": zip_path.stat().st_size,
        }
        ringkasan["berkas_di_zip"] = [
            f.relative_to(folder).as_posix()
            for f in sorted(folder.rglob("*"))
            if f.is_file() and f.name != nama_zip
        ]
        self._catat(
            job,
            f"selesai: {len(ringkasan['berkas_di_zip'])} berkas, "
            f"zip {zip_path.name} ({zip_path.stat().st_size} bita)",
            "ringkasan",
        )
        return ringkasan


def jalankan_modul(
    pengaturan: Pengaturan,
    berkas_modul: Path,
    berkas_lkp=None,
    identitas=None,
    opsi=None,
    job=None,
):
    """Jalan pintas untuk memakai pipeline tanpa gudang pekerjaan."""
    return Pipeline(pengaturan).kerjakan(
        job=_JobKosong(job),
        berkas_modul=Path(berkas_modul),
        berkas_lkp=berkas_lkp,
        identitas=identitas,
        opsi=opsi,
    )


class _JobKosong:
    """Pengganti pekerjaan kalau pipeline dipakai tanpa latar belakang."""

    def __init__(self, job=None):
        self._job = job
        self.batal = threading.Event()

    def maju(self, tahap: str, pesan: str = "", persen=None) -> None:
        if self._job is not None:
            self._job.maju(tahap, pesan, persen)
