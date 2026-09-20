"""Pembaca berkas .env sederhana.

Berkas .env dipakai supaya kunci API dan pengaturan lain tidak perlu
ditulis ulang di terminal setiap kali menjalankan layanan. Isinya hanya
baris `NAMA=nilai`. Baris kosong dan baris berawalan `#` dilewati.

Nilai yang sudah ada di lingkungan sungguhan tidak ditimpa, jadi
`DASPRO_PORT=9000 python3 -m daspro_api` tetap menang atas isi berkas.
"""
import os
from pathlib import Path

NAMA_BAWAAN = ".env"


def _bersihkan_nilai(nilai: str) -> str:
    """Buang spasi dan tanda kutip pembungkus, juga komentar di belakang."""
    nilai = nilai.strip()
    if len(nilai) >= 2 and nilai[0] == nilai[-1] and nilai[0] in {'"', "'"}:
        return nilai[1:-1]
    # Komentar di belakang hanya dipotong kalau didahului spasi, supaya
    # nilai seperti kunci yang memuat tanda # tidak ikut terpotong.
    if " #" in nilai:
        nilai = nilai.split(" #", 1)[0]
    return nilai.strip()


def baca_berkas_env(berkas: Path) -> dict:
    """Baca satu berkas .env dan kembalikan isinya sebagai kamus."""
    berkas = Path(berkas)
    if not berkas.is_file():
        return {}
    isi = {}
    try:
        teks = berkas.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    for baris in teks.splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#"):
            continue
        if baris.lower().startswith("export "):
            baris = baris[7:].strip()
        if "=" not in baris:
            continue
        nama, _, nilai = baris.partition("=")
        nama = nama.strip()
        if not nama:
            continue
        isi[nama] = _bersihkan_nilai(nilai)
    return isi


def muat_env(berkas=None, timpa: bool = False, mulai_dari=None) -> dict:
    """Muat berkas .env ke variabel lingkungan.

    Kalau `berkas` tidak diberikan, berkas .env dicari mulai dari folder
    kerja sekarang lalu naik ke folder di atasnya. Nilai yang sudah ada di
    lingkungan tidak ditimpa kecuali `timpa` bernilai true.

    Kembalikan daftar nama yang benar-benar dipasang.
    """
    if berkas is not None:
        kandidat = [Path(berkas)]
    else:
        awal = Path(mulai_dari) if mulai_dari else Path.cwd()
        kandidat = [folder / NAMA_BAWAAN for folder in [awal, *awal.parents]]

    dipasang = {}
    for k in kandidat:
        isi = baca_berkas_env(k)
        if not isi:
            continue
        for nama, nilai in isi.items():
            if timpa or nama not in os.environ:
                os.environ[nama] = nilai
                dipasang[nama] = nilai
        break  # hanya berkas .env pertama yang ditemukan yang dipakai
    return dipasang
