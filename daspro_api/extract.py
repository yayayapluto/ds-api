"""Cara membaca berkas masukan: PDF modul dan docx template.

Untuk docx, teksnya dibaca langsung dari XML di dalam arsip, jadi tidak
butuh paket tambahan. Untuk PDF, teks diambil per halaman lalu digabung.
"""
import re
import zipfile
from pathlib import Path

from daspro_api.errors import InputTidakValid

DOC = "word/document.xml"
NS_T = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
NS_P = re.compile(r"<w:p[\s>/]")
NS_BR = re.compile(r"<w:(?:br|tab)(?:\s[^>]*)?/>")
ENTITAS = [
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&apos;", "'"),
    ("&#39;", "'"),
    ("&amp;", "&"),
]


def bersihkan_teks(teks: str) -> str:
    """Kembalikan entitas XML ke karakter aslinya."""
    for pola, ganti in ENTITAS:
        teks = teks.replace(pola, ganti)
    return teks


def teks_docx(berkas: Path) -> str:
    """Ambil seluruh teks dari berkas .docx, paragraf dipisah baris baru."""
    berkas = Path(berkas)
    try:
        with zipfile.ZipFile(berkas) as z:
            xml = z.read(DOC).decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError) as e:
        raise InputTidakValid(f"{berkas.name} bukan berkas docx yang sah") from e

    xml = NS_BR.sub("\n", xml)
    baris = []
    for par in re.split(r"</w:p>", xml):
        potongan = [m.group(1) for m in NS_T.finditer(par)]
        teks = bersihkan_teks("".join(potongan)).strip()
        if teks:
            baris.append(teks)
    return "\n".join(baris)


def teks_pdf(berkas: Path) -> str:
    """Ambil teks dari berkas .pdf memakai pustaka yang tersedia."""
    berkas = Path(berkas)
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as e:
        raise InputTidakValid(
            "pembaca PDF tidak tersedia. Pasang pypdf (pip install pypdf) "
            "atau kirim modul dalam bentuk docx."
        ) from e

    try:
        reader = PdfReader(str(berkas))
    except Exception as e:  # pypdf melempar banyak jenis error berbeda
        raise InputTidakValid(f"{berkas.name} tidak bisa dibaca sebagai PDF") from e

    halaman = []
    for i, hal in enumerate(reader.pages, 1):
        try:
            isi = hal.extract_text() or ""
        except Exception:
            isi = ""
        isi = isi.strip()
        if isi:
            halaman.append(f"--- halaman {i} ---\n{isi}")
    if not halaman:
        raise InputTidakValid(
            f"{berkas.name} tidak memuat teks yang bisa dibaca. "
            "Kalau hasil pindai gambar, kirim versi docx atau teksnya."
        )
    return "\n\n".join(halaman)


def teks_berkas(berkas: Path) -> str:
    """Pilih cara baca sesuai jenis berkas: docx, pdf, atau teks biasa."""
    berkas = Path(berkas)
    if not berkas.is_file():
        raise InputTidakValid(f"berkas tidak ada: {berkas}")
    akhiran = berkas.suffix.lower()
    if akhiran == ".docx":
        return teks_docx(berkas)
    if akhiran == ".pdf":
        return teks_pdf(berkas)
    if akhiran in {".txt", ".md", ".c"}:
        return berkas.read_text(encoding="utf-8", errors="replace")
    raise InputTidakValid(f"jenis berkas belum didukung: {akhiran or berkas.name}")


def ringkas(teks: str, batas: int = 20000) -> str:
    """Potong teks panjang supaya permintaan ke AI tidak kebesaran."""
    teks = teks.strip()
    if len(teks) <= batas:
        return teks
    return teks[:batas] + "\n\n[... isi dipotong karena terlalu panjang ...]"


def cari_soal(teks_modul: str) -> list:
    """Tebak daftar soal dari judul bagian di modul.

    Hasilnya hanya petunjuk untuk AI, bukan patokan mutlak. Kalau tidak ada
    yang cocok, kembalikan daftar kosong dan biar AI membaca modulnya.
    """
    pola = re.compile(
        r"^\s*(?:(?:IV|V|VI|VII)\.\d+|Langkah\s+\d+|\d+\.\d+)\s+(.{3,120})$",
        re.M,
    )
    judul = [m.group(1).strip() for m in pola.finditer(teks_modul)]
    return judul[:40]
