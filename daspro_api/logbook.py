"""Catatan kejadian layanan dalam bentuk berkas teks.

Dua jenis catatan yang ditulis:

1. Catatan layanan, satu berkas per hari di ``<data_dir>/logs/``. Isinya
   permintaan HTTP, kegagalan yang tidak terduga, dan kejadian penting lain.
2. Catatan pekerjaan, satu berkas ``job.log`` di folder tiap pekerjaan.
   Isinya urutan tahap, panggilan AI, dan sebab kegagalan.

Semua tulisan lewat ``Catatan`` supaya:

- penulisan aman dari banyak thread sekaligus (server ini memakai thread),
- berkas tidak tumbuh tanpa batas (dipotong setelah beberapa MB),
- nilai rahasia seperti kunci API tidak pernah ikut tertulis.
"""
import threading
from datetime import datetime
from pathlib import Path

# Ukuran maksimum satu berkas catatan sebelum dipotong dari depan.
BATAS_BYTES = 4 * 1024 * 1024

def cap_waktu() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Catatan:
    """Penulis satu berkas catatan yang aman dipakai bersama banyak thread."""

    def __init__(self, berkas: Path, rahasia=None):
        self.berkas = Path(berkas)
        self._kunci = threading.Lock()
        self._rahasia = {r for r in (rahasia or []) if r}

    def tambah_rahasia(self, *nilai) -> None:
        """Daftarkan nilai yang tidak boleh ikut tertulis ke berkas."""
        with self._kunci:
            self._rahasia.update(n for n in nilai if n)

    def bersihkan(self, teks) -> str:
        """Ganti semua nilai rahasia yang terdaftar dengan penanda."""
        hasil = str(teks)
        for rahasia in self._rahasia:
            if rahasia:
                hasil = hasil.replace(rahasia, "(disembunyikan)")
        return hasil

    def tulis(self, teks: str, tahap: str = "") -> None:
        """Tambahkan satu baris bercap waktu. Kegagalan menulis diabaikan."""
        baris = f"[{cap_waktu()}]"
        if tahap:
            baris += f" {tahap}:"
        baris += f" {self.bersihkan(teks)}"
        self._tulis_mentah(baris + "\n")

    def _tulis_mentah(self, isi: str) -> None:
        with self._kunci:
            try:
                self.berkas.parent.mkdir(parents=True, exist_ok=True)
                self._potong_kalau_besar()
                with self.berkas.open("a", encoding="utf-8") as f:
                    f.write(isi)
            except OSError:
                # Catatan tidak boleh mematikan layanan.
                pass

    def _potong_kalau_besar(self) -> None:
        try:
            if self.berkas.stat().st_size <= BATAS_BYTES:
                return
            isi = self.berkas.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        # Sisakan bagian akhir saja, mulai dari baris yang utuh.
        sisa = isi[-BATAS_BYTES // 2 :]
        potong = sisa.find("\n")
        if potong != -1:
            sisa = sisa[potong + 1 :]
        self.berkas.write_text(
            f"[{cap_waktu()}] catatan lama dipotong karena berkas terlalu besar\n" + sisa,
            encoding="utf-8",
        )

def catatan_layanan(data_dir: Path, rahasia=None) -> Catatan:
    """Catatan harian layanan: satu berkas per hari."""
    nama = datetime.now().strftime("daspro-%Y-%m-%d.log")
    return Catatan(Path(data_dir) / "logs" / nama, rahasia=rahasia)

def catatan_pekerjaan(folder: Path, rahasia=None) -> Catatan:
    """Catatan satu pekerjaan: ``job.log`` di dalam folder pekerjaan."""
    return Catatan(Path(folder) / "job.log", rahasia=rahasia)
