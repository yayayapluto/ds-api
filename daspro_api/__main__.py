#!/usr/bin/env python3
"""Perintah baris untuk menjalankan daspro-api.

Contoh:
    python3 -m daspro_api                 # jalankan layanan
    python3 -m daspro_api --host 0.0.0.0 --port 9000
    python3 -m daspro_api --cek           # periksa persiapan saja
    python3 -m daspro_api --setelan       # tampilkan pengaturan yang terbaca
"""
import argparse
import json
import sys

from .config import Pengaturan
from .errors import DasproError
from .skillbridge import Skill


def _tampilkan_setelan(p: Pengaturan) -> None:
    tampil = {
        "host": p.host,
        "port": p.port,
        "data_dir": str(p.data_dir),
        "skill_dir": str(p.skill_dir),
        "ai_base_url": p.ai_base_url,
        "ai_model": p.ai_model,
        "ai_provider": p.ai_provider,
        "ai_api_key": "(terisi)" if p.ai_api_key else "(kosong)",
        "ai_siap": p.ai_siap,
        "gcc": p.gcc,
        "run_timeout": p.run_timeout,
        "memory_mb": p.memory_mb,
        "max_upload_mb": p.max_upload_mb,
        "job_workers": p.job_workers,
        "auth_token": "(terisi)" if p.auth_token else "(kosong)",
    }
    print(json.dumps(tampil, ensure_ascii=False, indent=2))


def _periksa(p: Pengaturan) -> int:
    """Pastikan semua yang dibutuhkan sudah siap sebelum melayani."""
    masalah = []
    skill = Skill(p.skill_dir)
    try:
        skill.periksa()
        print(f"OK   folder skill: {skill.folder}")
    except DasproError as e:
        masalah.append(str(e))
        print(f"GAGAL folder skill: {e}")

    from .compiler import KompilatorC

    try:
        jalur = KompilatorC(p).periksa_gcc()
        print(f"OK   gcc: {jalur}")
    except DasproError as e:
        masalah.append(str(e))
        print(f"GAGAL gcc: {e}")

    if p.ai_siap:
        print(f"OK   AI: {p.ai_model} lewat {p.ai_base_url}")
    else:
        masalah.append("AI belum diatur")
        print(
            "GAGAL AI: isi DASPRO_AI_API_KEY dan DASPRO_AI_BASE_URL, "
            "atau pakai DASPRO_AI_PROVIDER=mock untuk uji coba."
        )

    if masalah:
        print(f"\n{len(masalah)} hal perlu dibenahi dulu.")
        return 1
    print("\nSemua siap. Jalankan tanpa --cek untuk mulai melayani.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="daspro_api",
        description="Layanan untuk mengerjakan modul praktikum Dasar Pemrograman.",
    )
    parser.add_argument("--host", help="alamat yang didengarkan")
    parser.add_argument("--port", type=int, help="nomor port")
    parser.add_argument("--setelan", action="store_true", help="tampilkan pengaturan")
    parser.add_argument("--cek", action="store_true", help="periksa persiapan lalu keluar")
    parser.add_argument("--versi", action="store_true", help="tampilkan versi")
    args = parser.parse_args(argv)

    if args.versi:
        from . import __version__

        print(__version__)
        return 0

    p = Pengaturan.dari_env()
    if args.host:
        p.host = args.host
    if args.port:
        p.port = args.port

    if args.setelan:
        _tampilkan_setelan(p)
        return 0
    if args.cek:
        return _periksa(p)

    from .server import jalankan

    return jalankan(p)


if __name__ == "__main__":
    sys.exit(main())
