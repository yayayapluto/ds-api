#!/usr/bin/env python3
"""Pengujian pembaca berkas .env.

Diperiksa: nilai terbaca, tanda kutip dibuang, komentar diabaikan, dan
variabel lingkungan sungguhan tidak ditimpa isi berkas.
"""
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.envfile import baca_berkas_env, muat_env  # noqa: E402

ISI = """# pengaturan uji
DASPRO_PORT=9111
DASPRO_AI_API_KEY="kunci-rahasia"
DASPRO_AI_MODEL=gpt-4o-mini   # komentar di belakang
DASPRO_AI_TIMEOUT='99'

export DASPRO_HOST=0.0.0.0
BARIS TANPA SAMA DENGAN
KOSONG=
"""


class UjiBerkasEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="daspro_env_")
        self.berkas = pathlib.Path(self.tmp) / ".env"
        self.berkas.write_text(ISI, encoding="utf-8")
        self.simpan = dict(os.environ)

    def tearDown(self):
        for nama in ("DASPRO_PORT", "DASPRO_AI_API_KEY", "DASPRO_AI_MODEL",
                     "DASPRO_AI_TIMEOUT", "DASPRO_HOST", "KOSONG"):
            os.environ.pop(nama, None)
        os.environ.update(self.simpan)
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_baca_berkas(self):
        isi = baca_berkas_env(self.berkas)
        self.assertEqual(isi["DASPRO_PORT"], "9111")
        self.assertEqual(isi["DASPRO_AI_API_KEY"], "kunci-rahasia")
        self.assertEqual(isi["DASPRO_AI_MODEL"], "gpt-4o-mini")
        self.assertEqual(isi["DASPRO_AI_TIMEOUT"], "99")
        self.assertEqual(isi["DASPRO_HOST"], "0.0.0.0")
        self.assertEqual(isi["KOSONG"], "")
        self.assertNotIn("BARIS TANPA SAMA DENGAN", isi)

    def test_berkas_tidak_ada(self):
        self.assertEqual(baca_berkas_env(pathlib.Path(self.tmp) / "tidak-ada"), {})

    def test_lingkungan_sunguhan_menang(self):
        os.environ["DASPRO_PORT"] = "7000"
        dipasang = muat_env(self.berkas)
        self.assertEqual(os.environ["DASPRO_PORT"], "7000")
        self.assertNotIn("DASPRO_PORT", dipasang)
        self.assertIn("DASPRO_AI_MODEL", dipasang)

    def test_pengaturan_terbaca_dari_env(self):
        muat_env(self.berkas)
        p = Pengaturan.dari_env(pakai_env_file=False)
        self.assertEqual(p.port, 9111)
        self.assertEqual(p.ai_api_key, "kunci-rahasia")
        self.assertEqual(p.ai_timeout, 99)
        self.assertTrue(p.ai_siap)
        self.assertEqual(p.host, "0.0.0.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
