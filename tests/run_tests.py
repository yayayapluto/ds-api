#!/usr/bin/env python3
"""Jalankan semua pengujian: python3 tests/run_tests.py"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    # Fixture dibuat ulang supaya selalu ada sebelum diuji.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import buat_fixture

    buat_fixture.main()
    print()

    pemuat = unittest.TestLoader()
    rangkaian = pemuat.discover(
        start_dir=str(pathlib.Path(__file__).resolve().parent), pattern="test_*.py"
    )
    hasil = unittest.TextTestRunner(verbosity=2).run(rangkaian)
    return 0 if hasil.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
