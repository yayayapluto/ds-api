"""Pengubah karakter di luar keyboard menjadi karakter keyboard biasa.

Model bahasa sering menulis tanda panah, tanda kutip melengkung, atau tanda
pisah panjang tanpa diminta. Tulisan untuk dosen harus memakai karakter yang
ada di keyboard, jadi semua karakter aneh diganti di sini.
"""
import unicodedata
from typing import Any

GANTI = {
    "\u2014": "-",
    "\u2013": "-",
    "\u2012": "-",
    "\u2212": "-",
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2026": "...",
    "\u2022": "-",
    "\u00b7": "-",
    "\u2192": "->",
    "\u2190": "<-",
    "\u2194": "<->",
    "\u21d2": "=>",
    "\u00d7": "x",
    "\u00f7": "/",
    "\u2265": ">=",
    "\u2264": "<=",
    "\u2260": "!=",
    "\u2248": "kira-kira",
    "\u00a0": " ",
    "\u2009": " ",
    "\u202f": " ",
    "\u200b": "",
    "\u00b0": " derajat",
    "\u00ba": " derajat",
    "\u2028": "\n",
    "\u2029": "\n",
    "\u201e": '"',
    "\u2033": '"',
    "\u2032": "'",
    "\u2044": "/",
    "\uff08": "(",
    "\uff09": ")",
    "\uff0c": ",",
    "\uff1a": ":",
    "\u00ab": '"',
    "\u00bb": '"',
}


def bersihkan(teks: str) -> str:
    """Ganti semua karakter di luar keyboard pada satu teks."""
    if not teks:
        return teks
    hasil = []
    for ch in teks:
        if ord(ch) <= 127:
            hasil.append(ch)
        elif ch in GANTI:
            hasil.append(GANTI[ch])
        else:
            hasil.append(_pengganti_umum(ch))
    return "".join(hasil)


def _pengganti_umum(ch: str) -> str:
    """Usaha terakhir untuk karakter yang tidak ada di tabel ganti.

    Tanda aksen dipisah jadi huruf biasa, tanda hubung panjang jadi minus,
    dan sisanya dibuang supaya tidak ada karakter aneh yang lolos.
    """
    try:
        pisah = unicodedata.normalize("NFKD", ch)
    except ValueError:
        return ""
    inti = "".join(c for c in pisah if ord(c) <= 127)
    if inti:
        return inti
    if unicodedata.category(ch).startswith("P"):
        return "-"
    if unicodedata.category(ch).startswith("Z"):
        return " "
    return ""


def cari_pelanggar(teks: str) -> dict:
    """Daftar karakter di luar keyboard yang masih ada, beserta jumlahnya."""
    temuan = {}
    for ch in teks:
        if ord(ch) > 127:
            nama = "TIDAK DIKENAL"
            try:
                nama = unicodedata.name(ch)
            except ValueError:
                pass
            kunci = f"{nama} (U+{ord(ch):04X})"
            temuan[kunci] = temuan.get(kunci, 0) + 1
    return temuan


def bersihkan_dalam(data: Any) -> Any:
    """Bersihkan semua teks di dalam struktur data bersarang."""
    if isinstance(data, str):
        return bersihkan(data)
    if isinstance(data, list):
        return [bersihkan_dalam(x) for x in data]
    if isinstance(data, dict):
        return {k: bersihkan_dalam(v) for k, v in data.items()}
    return data
