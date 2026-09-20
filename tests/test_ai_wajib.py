#!/usr/bin/env python3
"""Pengujian bahwa layanan menolak jalan tanpa layanan AI.

Kode C harus benar-benar ditulis oleh model, jadi layanan wajib berhenti
kalau kunci AI belum diisi. Berkas ini memastikan penolakan itu terjadi di
semua pintu masuk: klien AI, pipeline, dan pembuatan server.
"""
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from daspro_api.ai import KlienAi  # noqa: E402
from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.errors import AiBelumDiatur  # noqa: E402
from daspro_api.pipeline import Pipeline, rapikan_identitas  # noqa: E402
from daspro_api.server import buat_server  # noqa: E402
from daspro_api.skillbridge import Skill  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


class UjiAiWajib(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="daspro_wajib_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _p(self, **ubah):
        dasar = {
            "data_dir": pathlib.Path(self.tmp),
            "skill_dir": ROOT / "skill",
            # Port 0 = minta port bebas dari sistem, supaya pengujian tidak
            # bentrok dengan layanan lain yang sedang jalan.
            "port": 0,
            "ai_api_key": "",
            "ai_base_url": "https://api.openai.com/v1",
        }
        dasar.update(ubah)
        return Pengaturan(**dasar)

    # --- klien AI --------------------------------------------------------
    def test_tanpa_kunci_ditolak(self):
        klien = KlienAi(self._p(ai_api_key=""))
        with self.assertRaises(AiBelumDiatur) as ctx:
            klien.periksa()
        self.assertIn("DASPRO_AI_API_KEY", ctx.exception.pesan)

    def test_tanpa_alamat_ditolak(self):
        klien = KlienAi(self._p(ai_api_key="kunci", ai_base_url=""))
        with self.assertRaises(AiBelumDiatur):
            klien.periksa()

    def test_panggilan_tanpa_kunci_ditolak(self):
        """Bahkan sebelum menyentuh jaringan, panggilan harus ditolak."""
        klien = KlienAi(self._p(ai_api_key=""))
        with self.assertRaises(AiBelumDiatur):
            klien.lengkapi("halo")

    def test_ai_siap_hanya_kalau_lengkap(self):
        self.assertFalse(self._p(ai_api_key="").ai_siap)
        self.assertFalse(self._p(ai_api_key="kunci", ai_base_url="").ai_siap)
        self.assertTrue(self._p(ai_api_key="kunci").ai_siap)

    # --- pipeline --------------------------------------------------------
    def test_pipeline_berhenti_di_awal(self):
        """Tanpa AI, pekerjaan gagal sebelum berkas apa pun dibuat."""
        p = self._p(ai_api_key="")
        job = self._job()
        pipeline = Pipeline(p, skill=Skill(p.skill_dir), klien=KlienAi(p))

        with self.assertRaises(AiBelumDiatur):
            pipeline.kerjakan(
                job,
                berkas_modul=FIXTURES / "modul_contoh.pdf",
                identitas={"nama": "-", "nim": "-", "kelas": "-", "modul": "5"},
            )
        # Tahap pertama adalah pemeriksaan, dan tidak ada kode yang ditulis.
        self.assertEqual(job.tahap[0], "periksa")
        self.assertNotIn("kode", job.tahap)
        self.assertEqual(list((pathlib.Path(self.tmp) / "job").rglob("*.c")), [])

    def _job(self):
        class Job:
            def __init__(self, folder):
                self.folder = pathlib.Path(folder)
                self.batal = __import__("threading").Event()
                self.tahap = []
                self.folder.mkdir(parents=True, exist_ok=True)

            def maju(self, tahap, pesan="", persen=None):
                self.tahap.append(tahap)

        return Job(pathlib.Path(self.tmp) / "job")

    # --- server ----------------------------------------------------------
    def test_server_menolak_tanpa_ai(self):
        with self.assertRaises(AiBelumDiatur):
            buat_server(self._p(ai_api_key=""))

    def test_server_terbangun_kalau_ai_ada(self):
        httpd = buat_server(self._p(ai_api_key="kunci"))
        try:
            self.assertTrue(httpd.RequestHandlerClass.layanan.p.ai_siap)
        finally:
            httpd.server_close()

    def test_identitas_tetap_wajib(self):
        with self.assertRaises(Exception):
            rapikan_identitas({"nama": "-"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
