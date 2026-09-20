#!/usr/bin/env python3
"""Perintah baris untuk menjalankan daspro-api.

Contoh:
    python3 -m daspro_api                 # jalankan layanan
    python3 -m daspro_api --host 0.0.0.0 --port 9000
    python3 -m daspro_api --cek           # periksa persiapan, termasuk AI
    python3 -m daspro_api --cek-ai        # uji koneksi AI saja
    python3 -m daspro_api --setelan       # tampilkan pengaturan yang terbaca

Layanan ini selalu memakai AI sungguhan. Tidak ada mode jawaban tiruan,
supaya kode C yang dihasilkan tidak pernah karangan.
"""
import argparse
import json
import sys

from daspro_api.config import Pengaturan
from daspro_api.errors import DasproError
from daspro_api.skillbridge import Skill


def _tampilkan_setelan(p: Pengaturan) -> None:
    tampil = {
        "host": p.host,
        "port": p.port,
        "data_dir": str(p.data_dir),
        "skill_dir": str(p.skill_dir),
        "ai_base_url": p.ai_base_url,
        "ai_model": p.ai_model,
        "ai_api_key": "(terisi)" if p.ai_api_key else "(kosong)",
        "ai_siap": p.ai_siap,
        "ai_timeout": p.ai_timeout,
        "gcc": p.gcc,
        "run_timeout": p.run_timeout,
        "memory_mb": p.memory_mb,
        "max_upload_mb": p.max_upload_mb,
        "job_workers": p.job_workers,
        "auth_token": "(terisi)" if p.auth_token else "(kosong)",
    }
    print(json.dumps(tampil, ensure_ascii=False, indent=2))


def _periksa_ai(p: Pengaturan, uji_koneksi: bool) -> int:
    """Pastikan layanan AI sudah diatur, dan kalau diminta, benar-benar menjawab."""
    from .ai import KlienAi

    klien = KlienAi(p)
    try:
        klien.periksa()
        print(f"OK   AI terpasang: {p.ai_model} lewat {p.ai_base_url}")
    except DasproError as e:
        print(f"GAGAL AI: {e.pesan}")
        print(
            "\nLayanan ini wajib memakai AI sungguhan karena kode C harus "
            "benar-benar ditulis oleh model.\n"
            "Isi DASPRO_AI_API_KEY di berkas .env, lalu jalankan lagi."
        )
        return 1

    if not uji_koneksi:
        return 0

    print("     menguji koneksi ke layanan AI ...")
    try:
        hasil = klien.uji_koneksi()
    except DasproError as e:
        print(f"GAGAL uji koneksi AI: {e.pesan}")
        if e.detail:
            print(f"     keterangan: {str(e.detail)[:300]}")
        print(
            "\nPeriksa kembali kunci, alamat, dan nama model. Pastikan juga "
            "komputer ini bisa mengakses internet."
        )
        return 1
    print(
        f"OK   AI menjawab dalam {hasil['detik']} detik: "
        f"\"{hasil['jawaban']}\""
    )
    return 0


def _periksa(p: Pengaturan, uji_koneksi: bool = True) -> int:
    """Pastikan semua yang dibutuhkan sudah siap sebelum melayani."""
    masalah = []

    skill = Skill(p.skill_dir)
    try:
        skill.periksa()
        print(f"OK   folder skill: {skill.folder}")
    except DasproError as e:
        masalah.append(str(e))
        print(f"GAGAL folder skill: {e.pesan}")

    from .compiler import KompilatorC

    try:
        jalur = KompilatorC(p).periksa_gcc()
        print(f"OK   gcc: {jalur}")
    except DasproError as e:
        masalah.append(str(e))
        print(f"GAGAL gcc: {e.pesan}")

    if _periksa_ai(p, uji_koneksi) != 0:
        masalah.append("layanan AI belum siap")

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
    parser.add_argument(
        "--env",
        help="berkas .env yang dipakai (bawaan: .env di folder kerja)",
    )
    parser.add_argument(
        "--tanpa-env", action="store_true", help="abaikan berkas .env"
    )
    parser.add_argument("--setelan", action="store_true", help="tampilkan pengaturan")
    parser.add_argument(
        "--cek",
        action="store_true",
        help="periksa persiapan termasuk koneksi AI, lalu keluar",
    )
    parser.add_argument(
        "--cek-ai",
        action="store_true",
        help="uji koneksi ke layanan AI saja, lalu keluar",
    )
    parser.add_argument("--versi", action="store_true", help="tampilkan versi")
    args = parser.parse_args(argv)

    if args.versi:
        from . import __version__

        print(__version__)
        return 0

    # Berkas .env dipasang lebih dulu, baru pengaturan dibaca.
    dipasang = {}
    if not args.tanpa_env:
        from .envfile import muat_env

        dipasang = muat_env(args.env)
        if dipasang:
            sumber = args.env or ".env"
            print(f"pengaturan dari {sumber}: {', '.join(sorted(dipasang))}")

    p = Pengaturan.dari_env(pakai_env_file=False)
    if args.host:
        p.host = args.host
    if args.port:
        p.port = args.port

    if args.setelan:
        _tampilkan_setelan(p)
        return 0
    if args.cek_ai:
        return _periksa_ai(p, uji_koneksi=True)
    if args.cek:
        return _periksa(p, uji_koneksi=True)

    # Tanpa AI, layanan tidak boleh melayani: pekerjaan akan gagal di tengah.
    from .ai import KlienAi

    try:
        KlienAi(p).periksa()
    except DasproError as e:
        print(f"layanan tidak bisa dijalankan: {e.pesan}")
        print(
            "Isi DASPRO_AI_API_KEY di berkas .env, lalu coba lagi. "
            "Jalankan `python3 -m daspro_api --cek` untuk memeriksa."
        )
        return 2

    from .server import jalankan

    return jalankan(p)


if __name__ == "__main__":
    sys.exit(main())
