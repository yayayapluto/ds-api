"""Pembaca permintaan HTTP: badan JSON dan unggahan multipart.

Ditulis sendiri karena layanan ini hanya memakai pustaka bawaan Python.
Yang didukung hanya bentuk yang benar-benar dipakai layanan ini.
"""
import json
import re
import uuid
from pathlib import Path

from daspro_api.errors import InputTidakValid

PEMISAH = re.compile(rb"\r\n--([^\r\n]+)")
JUDUL_ISI = re.compile(rb'name="([^"]*)"(?:;\s*filename="([^"]*)")?', re.I)


def _panjang(handler) -> int:
    """Panjang badan permintaan; nilai aneh dianggap nol."""
    mentah = handler.headers.get("Content-Length")
    try:
        return max(0, int(mentah or 0))
    except (TypeError, ValueError):
        return 0


def baca_json(handler, batas: int) -> dict:
    """Baca badan permintaan sebagai JSON."""
    panjang = _panjang(handler)
    if panjang <= 0:
        return {}
    if panjang > batas:
        raise InputTidakValid(
            f"badan permintaan terlalu besar ({panjang} byte, batas {batas} byte)"
        )
    mentah = handler.rfile.read(panjang)
    if not mentah.strip():
        return {}
    try:
        data = json.loads(mentah.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InputTidakValid(f"badan permintaan bukan JSON yang sah: {e}") from e
    if not isinstance(data, dict):
        raise InputTidakValid("badan permintaan JSON harus berupa objek")
    return data


def _jenis_konten(handler) -> str:
    return (handler.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def _batas_multipart(handler) -> bytes:
    tipe = handler.headers.get("Content-Type") or ""
    m = re.search(r'boundary="?([^";]+)"?', tipe)
    if not m:
        raise InputTidakValid("permintaan multipart tanpa boundary")
    return m.group(1).strip().encode("utf-8", "replace")


def baca_multipart(handler, batas: int, folder: Path) -> dict:
    """Baca unggahan multipart: berkas disimpan, kolom biasa jadi teks.

    Hasilnya:
        {"fields": {nama: teks}, "files": {nama: [path, ...]}}
    """
    panjang = _panjang(handler)
    if panjang <= 0:
        raise InputTidakValid("permintaan unggah kosong")
    if panjang > batas:
        raise InputTidakValid(
            f"unggahan terlalu besar ({panjang // 1048576} MB, "
            f"batas {batas // 1048576} MB)"
        )
    mentah = handler.rfile.read(panjang)
    pemisah = b"--" + _batas_multipart(handler)

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fields = {}
    files = {}

    for potong in mentah.split(pemisah):
        potong = potong.strip(b"\r\n")
        if not potong or potong in {b"--", b""}:
            continue
        kepala, _, isi = potong.partition(b"\r\n\r\n")
        if not _:
            continue
        baris = kepala.decode("utf-8", "replace").split("\r\n")
        m = JUDUL_ISI.search(baris[0].encode("utf-8", "replace"))
        if not m:
            continue
        nama_kolom = m.group(1).decode("utf-8", "replace")
        nama_berkas = m.group(2).decode("utf-8", "replace") if m.group(2) else None
        isi = isi.rstrip(b"\r\n")
        if nama_berkas:
            aman = Path(nama_berkas).name.replace("\x00", "") or f"unggahan_{uuid.uuid4().hex[:6]}"
            tujuan = folder / f"{uuid.uuid4().hex[:8]}_{aman}"
            tujuan.write_bytes(isi)
            files.setdefault(nama_kolom, []).append(tujuan)
        else:
            fields[nama_kolom] = isi.decode("utf-8", "replace").strip()

    if not files and not fields:
        raise InputTidakValid("tidak ada isi yang bisa dibaca dari unggahan")
    return {"fields": fields, "files": files}


def baca_permintaan(handler, batas: int, folder: Path) -> dict:
    """Pilih cara baca sesuai jenis isi permintaan."""
    tipe = _jenis_konten(handler)
    if tipe == "multipart/form-data":
        return baca_multipart(handler, batas, folder)
    if tipe in {"application/json", "text/json", ""}:
        return {"fields": baca_json(handler, batas), "files": {}}
    raise InputTidakValid(
        f"jenis isi permintaan belum didukung: {tipe}. "
        "Pakai application/json atau multipart/form-data."
    )


def ambil_berkas(data: dict, nama: str):
    """Ambil berkas pertama dari satu nama kolom unggahan."""
    daftar = (data.get("files") or {}).get(nama) or []
    return daftar[0] if daftar else None


def ambil_semua_berkas(data: dict, nama: str) -> list:
    return list((data.get("files") or {}).get(nama) or [])


def field(data: dict, nama: str, bawaan=None):
    return (data.get("fields") or {}).get(nama, bawaan)


def field_json(data: dict, nama: str, bawaan=None):
    """Ambil satu kolom yang isinya JSON, misal identitas."""
    nilai = field(data, nama)
    if nilai in (None, ""):
        return bawaan
    if isinstance(nilai, (dict, list)):
        return nilai
    try:
        return json.loads(nilai)
    except json.JSONDecodeError as e:
        raise InputTidakValid(f"kolom '{nama}' bukan JSON yang sah: {e}") from e


def field_bool(data: dict, nama: str, bawaan: bool) -> bool:
    nilai = field(data, nama)
    if nilai in (None, ""):
        return bawaan
    return str(nilai).strip().lower() in {"1", "true", "ya", "yes", "on"}
