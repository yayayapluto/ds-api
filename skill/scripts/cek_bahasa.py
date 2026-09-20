#!/usr/bin/env python3
"""cek_bahasa.py - periksa gaya bahasa laporan jawaban_LKP.

Pakai: python3 cek_bahasa.py jawaban_LKP_Modul_X.md [file lain ...]

Yang diperiksa:
1. Karakter di luar keyboard (ord > 127). Lihat references/gaya-bahasa.md.
2. Istilah teknis yang harus diganti bahasa sehari-hari.

Keluar dengan kode 1 kalau ada temuan, 0 kalau bersih.
"""
import pathlib
import re
import sys
import unicodedata

# Istilah teknis yang dilarang muncul di laporan mahasiswa semester 1.
JARGON = [
    "guard clause", "guard input", "early-exit", "early exit", "early return",
    "short-circuit", "short circuit", "fall-through", "fallthrough",
    "garbage value", "undefined behavior", "runtime error", "edge case",
    "tradeoff", "trade-off", "best practice", "clean code", "exit status",
    "conditional statement", "execution flow", "control flow",
    "nested if", "else-if chain", "boundary value",
]

# Semua karakter di luar keyboard dianggap pelanggaran, tanpa pengecualian.


def char_name(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "TIDAK DIKENAL"
    return f"{name} (U+{ord(ch):04X})"


def scan(path: pathlib.Path) -> list:
    findings = []
    text = path.read_text(encoding="utf-8")
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        for col, ch in enumerate(line, 1):
            if ord(ch) > 127:
                findings.append(
                    f"{path}:{lineno}:{col}: karakter terlarang {char_name(ch)}"
                )
        if in_fence:
            continue  # isi blok kode apa adanya, misal pesan warning gcc
        if path.suffix != ".md":
            continue  # skrip bukan tulisan untuk dosen, cukup cek karakter
        # Buang potongan di dalam backtick dulu: itu nama fungsi/variabel/pesan
        # compiler yang memang tidak boleh diubah.
        plain = re.sub(r"`[^`]*`", "", line).lower()
        for word in JARGON:
            if word in plain:
                findings.append(
                    f"{path}:{lineno}: istilah teknis '{word.strip('.')}' - "
                    "ganti pakai bahasa sehari-hari (lihat references/gaya-bahasa.md)"
                )
    return findings


def main() -> int:
    files = [pathlib.Path(a) for a in sys.argv[1:]]
    if not files:
        print(__doc__)
        return 2
    all_find = []
    for f in files:
        if not f.is_file():
            print(f"LEWAT: {f} bukan file")
            continue
        found = scan(f)
        status = "BERSIH" if not found else f"{len(found)} temuan"
        print(f"{f}: {status}")
        all_find += found
    if all_find:
        print("---")
        for line in all_find:
            print(line)
        print(f"---\nGAGAL: {len(all_find)} temuan. Perbaiki dulu.")
        return 1
    print("---\nLULUS: semua file bersih.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
