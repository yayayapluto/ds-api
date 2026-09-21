"""Penyimpanan pekerjaan yang berjalan di latar belakang.

Mengerjakan satu modul bisa makan waktu beberapa menit, jadi permintaan
tidak ditunggu sampai selesai. Pemanggil menerima nomor pekerjaan, lalu
menanyakan kemajuannya sampai selesai dan mengambil berkas hasilnya.
"""
import json
import shutil
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from daspro_api.config import Pengaturan
from daspro_api.errors import JobBentrok, TidakDitemukan
from daspro_api.logbook import catatan_pekerjaan

MENUNGGU = "menunggu"
JALAN = "jalan"
SELESAI = "selesai"
GAGAL = "gagal"
DIBATALKAN = "dibatalkan"


def sekarang() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ke_int(nilai, bawaan: int = 0) -> int:
    """Ubah nilai jadi bilangan bulat; kalau gagal pakai nilai bawaan."""
    try:
        return int(nilai)
    except (TypeError, ValueError):
        return bawaan


class Pekerjaan:
    """Satu pekerjaan: status, kemajuan, dan berkas hasilnya."""

    def __init__(self, job_id: str, folder: Path, permintaan: dict):
        self.id = job_id
        self.folder = Path(folder)
        self.permintaan = permintaan
        self.status = MENUNGGU
        self.tahap = "menunggu"
        self.pesan = "Pekerjaan masuk antrean."
        self.persen = 0
        self.dibuat = sekarang()
        self.selesai_pada = ""
        self.error = ""
        self.detail_error = ""
        self.hasil = {}
        self.log = []
        self.batal = threading.Event()
        self._kunci = threading.Lock()
        # Catatan berkas untuk pekerjaan ini. Nilai rahasia bisa
        # didaftarkan lewat ``rahasia()`` supaya tidak ikut tertulis.
        self.catatan = catatan_pekerjaan(self.folder)

    def rahasia(self, *nilai) -> None:
        """Daftarkan nilai yang tidak boleh ikut masuk berkas catatan."""
        self.catatan.tambah_rahasia(*nilai)

    # --- perubahan status ------------------------------------------------
    def maju(self, tahap: str, pesan: str = "", persen=None) -> None:
        with self._kunci:
            self.tahap = tahap
            if pesan:
                self.pesan = pesan
            if persen is not None:
                self.persen = max(0, min(100, ke_int(persen, self.persen)))
            self.log.append({"waktu": sekarang(), "tahap": tahap, "pesan": pesan})
            self.catatan.tulis(pesan or "", tahap)
            self.simpan()

    def selesai(self, hasil: dict) -> None:
        with self._kunci:
            self.status = SELESAI
            self.tahap = "selesai"
            self.persen = 100
            self.pesan = "Pekerjaan selesai."
            self.hasil = hasil
            self.selesai_pada = sekarang()
            self.catatan.tulis("Pekerjaan selesai.", "selesai")
            self.simpan()

    def gagal(self, pesan: str, detail: str = "") -> None:
        with self._kunci:
            self.status = GAGAL
            self.tahap = "gagal"
            self.pesan = "Pekerjaan berhenti karena ada masalah."
            self.error = pesan
            self.detail_error = detail
            self.selesai_pada = sekarang()
            # Catatan lengkap ikut ke berkas, supaya bisa diperiksa menyusul.
            baris = f"GAGAL: {pesan}"
            if detail:
                baris += f"\n{detail}"
            self.catatan.tulis(baris, "gagal")
            self.log.append(
                {
                    "waktu": sekarang(),
                    "tahap": "gagal",
                    "pesan": pesan,
                }
            )
            self.simpan()

    def tandai_dibatalkan(self) -> None:
        with self._kunci:
            self.status = DIBATALKAN
            self.tahap = "dibatalkan"
            self.pesan = "Pekerjaan dibatalkan."
            self.selesai_pada = sekarang()
            self.catatan.tulis("Pekerjaan dibatalkan.", "dibatalkan")
            self.simpan()

    def berjalan(self) -> None:
        with self._kunci:
            self.status = JALAN
            self.tahap = "mulai"
            self.persen = 1
            self.pesan = "Pekerjaan mulai dikerjakan."
            self.catatan.tulis(self.pesan, "mulai")
            self.simpan()

    @property
    def selesai_akhir(self) -> bool:
        return self.status in {SELESAI, GAGAL, DIBATALKAN}

    # --- berkas ----------------------------------------------------------
    @property
    def berkas_zip(self) -> Path:
        """Berkas ZIP hasil. Dicari di folder pekerjaan dan di subfolder kerja."""
        jalur = (self.hasil.get("zip") or {}).get("jalur")
        if jalur:
            kandidat = Path(jalur)
            if kandidat.is_file():
                return kandidat
        langsung = self.folder / "hasil.zip"
        if langsung.is_file():
            return langsung
        for kandidat in sorted(self.folder.glob("kerja/*.zip")) + sorted(
            self.folder.glob("*.zip")
        ):
            if kandidat.is_file():
                return kandidat
        return langsung

    def daftar_berkas(self) -> list:
        hasil = []
        for f in sorted(self.folder.rglob("*")):
            if f.is_file():
                hasil.append(
                    {
                        "nama": f.relative_to(self.folder).as_posix(),
                        "ukuran": f.stat().st_size,
                    }
                )
        return hasil

    # --- simpan ke disk --------------------------------------------------
    def ke_dict(self, sertakan_log: bool = False) -> dict:
        isi = {
            "job_id": self.id,
            "status": self.status,
            "tahap": self.tahap,
            "pesan": self.pesan,
            "persen": self.persen,
            "dibuat": self.dibuat,
            "selesai_pada": self.selesai_pada,
            "error": self.error,
            "detail_error": self.detail_error,
            "hasil": self.hasil,
            "berkas": self.daftar_berkas() if self.selesai_akhir else [],
        }
        if sertakan_log:
            isi["log"] = self.log
        return isi

    def simpan(self) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            (self.folder / "status.json").write_text(
                json.dumps(self.ke_dict(sertakan_log=True), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # status di disk hanya salinan, kegagalan menulis tidak fatal


class GudangPekerjaan:
    """Kumpulan pekerjaan yang sedang jalan, beserta antreannya."""

    def __init__(self, pengaturan: Pengaturan):
        self.p = pengaturan
        self.p.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._kunci = threading.Lock()
        self._pekerjaan = {}
        self._antre = []
        self._penjaga = threading.Condition(self._kunci)
        self._berhenti = threading.Event()
        self._pekerja = []
        self._muat_ulang()

    # --- pemuatan kembali ------------------------------------------------
    def _muat_ulang(self) -> None:
        """Baca lagi status pekerjaan lama supaya tetap bisa ditanyakan."""
        for folder in sorted(self.p.jobs_dir.iterdir()):
            status = folder / "status.json"
            if not folder.is_dir() or not status.is_file():
                continue
            try:
                data = json.loads(status.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            job = Pekerjaan(data.get("job_id", folder.name), folder, {})
            job.status = data.get("status", SELESAI)
            job.tahap = data.get("tahap", "")
            job.pesan = data.get("pesan", "")
            job.persen = max(0, min(100, ke_int(data.get("persen"), 0)))
            job.dibuat = data.get("dibuat", "")
            job.selesai_pada = data.get("selesai_pada", "")
            job.error = data.get("error", "")
            job.detail_error = data.get("detail_error", "")
            job.hasil = data.get("hasil", {})
            job.log = data.get("log", [])
            if not job.selesai_akhir:
                job.status = GAGAL
                job.error = "Server pernah berhenti saat pekerjaan ini berjalan."
            self._pekerjaan[job.id] = job

    # --- pengelolaan -----------------------------------------------------
    def buat(self, permintaan: dict, fungsi) -> Pekerjaan:
        job_id = uuid.uuid4().hex[:12]
        folder = self.p.jobs_dir / job_id
        folder.mkdir(parents=True, exist_ok=True)
        job = Pekerjaan(job_id, folder, permintaan)
        job.simpan()
        with self._kunci:
            self._pekerjaan[job_id] = job
            self._antre.append((job, fungsi))
            self._penjaga.notify()
        self.mulai_pekerja()
        return job

    def ambil(self, job_id: str) -> Pekerjaan:
        with self._kunci:
            job = self._pekerjaan.get(job_id)
        if job is None:
            raise TidakDitemukan(f"pekerjaan {job_id} tidak ada")
        return job

    def daftar(self, batas: int = 50) -> list:
        with self._kunci:
            semua = sorted(
                self._pekerjaan.values(), key=lambda j: j.dibuat, reverse=True
            )
        return [j.ke_dict() for j in semua[:batas]]

    def batalkan(self, job_id: str) -> Pekerjaan:
        job = self.ambil(job_id)
        if job.selesai_akhir:
            raise JobBentrok(f"pekerjaan {job_id} sudah {job.status}, tidak bisa dibatalkan")
        job.batal.set()
        if job.status == MENUNGGU:
            job.tandai_dibatalkan()
        return job

    # --- pekerja latar ---------------------------------------------------
    def mulai_pekerja(self) -> None:
        with self._kunci:
            jumlah = max(1, self.p.job_workers)
            while len(self._pekerja) < jumlah:
                t = threading.Thread(target=self._putaran, daemon=True)
                t.start()
                self._pekerja.append(t)

    def _putaran(self) -> None:
        while not self._berhenti.is_set():
            with self._kunci:
                while not self._antre and not self._berhenti.is_set():
                    self._penjaga.wait(timeout=1.0)
                if self._berhenti.is_set():
                    return
                job, fungsi = self._antre.pop(0)
            if job.batal.is_set():
                job.tandai_dibatalkan()
                continue
            job.berjalan()
            try:
                hasil = fungsi(job)
                if job.batal.is_set():
                    job.tandai_dibatalkan()
                else:
                    job.selesai(hasil or {})
            except Exception as e:  # satu pekerjaan gagal tidak boleh mematikan server
                pesan = getattr(e, "pesan", None)
                if not pesan:
                    pesan = f"{type(e).__name__}: {e}"
                # Jejak lengkap ikut masuk berkas catatan pekerjaan, supaya
                # sebab kegagalan bisa diperiksa tanpa menebak-nebak.
                detail = ""
                keterangan = getattr(e, "detail", None)
                if keterangan:
                    detail = f"keterangan: {keterangan}\n"
                detail += traceback.format_exc()
                job.gagal(str(pesan), detail)

    def bersihkan_lama(self) -> int:
        """Hapus pekerjaan lama supaya disk tidak penuh."""
        batas = time.time() - max(1, self.p.job_ttl_jam) * 3600
        jumlah = 0
        with self._kunci:
            for job_id, job in list(self._pekerjaan.items()):
                if not job.selesai_akhir:
                    continue
                try:
                    umur = job.folder.stat().st_mtime
                except OSError:
                    continue
                if umur < batas:
                    shutil.rmtree(job.folder, ignore_errors=True)
                    self._pekerjaan.pop(job_id, None)
                    jumlah += 1
        return jumlah

    def tutup(self) -> None:
        self._berhenti.set()
        with self._kunci:
            self._penjaga.notify_all()
