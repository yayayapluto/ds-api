#!/usr/bin/env python3
"""Pengujian halaman web dan kredensial per pekerjaan.

Yang diperiksa:
1. Halaman web terkirim, dan berkas di luar folder web tidak bisa dibaca.
2. Kunci API yang dikirim pengguna tidak pernah ditulis ke disk, tidak
   masuk catatan tahap, dan tidak dikirim balik oleh endpoint status.
3. Endpoint uji koneksi AI memakai kredensial yang dikirim, bukan milik server.
"""
import io
import json
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.errors import AiBelumDiatur  # noqa: E402
from daspro_api.server import buat_server  # noqa: E402
from mockai import KlienAiTiruan  # noqa: E402
from test_pipeline import jawab_analisis, jawab_kode, jawab_laporan  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
KUNCI_RAHASIA = "sk-rahasia-yang-tidak-boleh-tertulis-1234567890"


def multipart(fields: dict, files: dict) -> tuple:
    batas = "----daspro" + uuid.uuid4().hex
    isi = io.BytesIO()
    for nama, nilai in fields.items():
        isi.write(f"--{batas}\r\n".encode())
        isi.write(f'Content-Disposition: form-data; name="{nama}"\r\n\r\n'.encode())
        isi.write(str(nilai).encode("utf-8"))
        isi.write(b"\r\n")
    for nama, (nama_berkas, data) in files.items():
        isi.write(f"--{batas}\r\n".encode())
        isi.write(
            f'Content-Disposition: form-data; name="{nama}"; filename="{nama_berkas}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n".encode()
        )
        isi.write(data)
        isi.write(b"\r\n")
    isi.write(f"--{batas}--\r\n".encode())
    return isi.getvalue(), f"multipart/form-data; boundary={batas}"


class UjiWebDanKredensial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="daspro_web_")
        cls.p = Pengaturan(
            host="127.0.0.1",
            port=0,
            data_dir=pathlib.Path(cls.tmp),
            skill_dir=ROOT / "skill",
            ai_api_key="kunci-server",
            job_workers=1,
        )
        cls.httpd = buat_server(cls.p, wajib_ai=False)
        tiruan = KlienAiTiruan(
            cls.p,
            balasan=[jawab_analisis, jawab_kode, jawab_kode, jawab_kode, jawab_laporan],
        )
        layanan = cls.httpd.RequestHandlerClass.layanan
        layanan.klien = tiruan
        layanan.pipeline.klien = tiruan
        # Pabrik klien diganti supaya endpoint uji koneksi memakai klien
        # tiruan, bukan menghubungi jaringan sungguhan.
        layanan.pipeline.buat_klien = lambda p: KlienAiTiruan(
            p, balasan=[json.dumps({"siap": True})]
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def panggil(self, jalur, metode="GET", badan=None, jenis=None):
        url = f"http://127.0.0.1:{self.port}{jalur}"
        req = urllib.request.Request(url, data=badan, method=metode)
        if jenis:
            req.add_header("Content-Type", jenis)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type", "")

    # --- halaman web -----------------------------------------------------
    def test_01_halaman_utama(self):
        kode, data, jenis = self.panggil("/")
        self.assertEqual(kode, 200)
        self.assertIn("text/html", jenis)
        self.assertIn(b"Daspro API", data)

    def test_02_berkas_pendukung(self):
        for jalur, harus in [("/style.css", b"--biru"), ("/app.js", b"localStorage")]:
            kode, data, _ = self.panggil(jalur)
            self.assertEqual(kode, 200, jalur)
            self.assertIn(harus, data)

    def test_03_tidak_bisa_baca_berkas_luar(self):
        """Jalur yang keluar dari folder web harus ditolak."""
        for jalur in [
            "/../daspro_api/config.py",
            "/..%2Fconfig.py",
            "/%2e%2e/config.py",
            "/../.env",
            "/../../README.md",
        ]:
            kode, _, _ = self.panggil(jalur)
            self.assertIn(kode, (400, 404), f"{jalur} harus ditolak, dapat {kode}")

    def test_04_jenis_berkas_lain_ditolak(self):
        kode, _, _ = self.panggil("/../pyrightconfig.json")
        self.assertIn(kode, (400, 404))

    def test_05_endpoint_api_tidak_dianggap_halaman(self):
        kode, data, _ = self.panggil("/v1/tidak-ada")
        self.assertEqual(kode, 404)
        self.assertIn("tidak_ditemukan", data.decode())

    # --- kredensial tidak bocor -----------------------------------------
    def test_06_kunci_tidak_masuk_berkas_status(self):
        docx = (FIXTURES / "lkp_contoh.docx").read_bytes()
        pdf = (FIXTURES / "modul_contoh.pdf").read_bytes()
        identitas = json.dumps(
            {"nama": "-", "nim": "-", "kelas": "-", "modul": "5"}
        )
        badan, jenis = multipart(
            {
                "identitas": identitas,
                "ai_api_key": KUNCI_RAHASIA,
                "ai_base_url": "https://contoh.invalid/v1",
                "ai_model": "model-uji",
            },
            {"modul": ("modul.pdf", pdf), "lkp": ("lkp.docx", docx)},
        )
        kode, data, _ = self.panggil("/v1/jobs", "POST", badan, jenis)
        self.assertEqual(kode, 202, data)
        job_id = json.loads(data)["job_id"]

        import time

        status = {}
        for _ in range(120):
            kode, data, _ = self.panggil(f"/v1/jobs/{job_id}")
            status = json.loads(data)
            if status["status"] in {"selesai", "gagal"}:
                break
            time.sleep(0.25)

        # 1. Jawaban status tidak memuat kunci.
        teks = json.dumps(status)
        self.assertNotIn(KUNCI_RAHASIA, teks, "kunci bocor di jawaban status")

        # 2. Berkas di folder pekerjaan tidak memuat kunci.
        for berkas in pathlib.Path(self.tmp).rglob("*"):
            if not berkas.is_file():
                continue
            isi = berkas.read_bytes()
            self.assertNotIn(
                KUNCI_RAHASIA.encode(),
                isi,
                f"kunci bocor di berkas {berkas.relative_to(self.tmp)}",
            )

        # 3. Catatan tahap tidak memuat kunci.
        for catat in status.get("log") or []:
            self.assertNotIn(KUNCI_RAHASIA, json.dumps(catat))

    def test_07_kunci_tidak_dikirim_balik_oleh_health(self):
        kode, data, _ = self.panggil("/health")
        self.assertEqual(kode, 200)
        isi = json.loads(data)
        self.assertNotIn(KUNCI_RAHASIA, data.decode())
        self.assertNotIn("api_key", json.dumps(isi))
        # Yang ada hanya keterangan apakah kunci terisi.
        self.assertIn("kunci_terisi", isi["ai"])
        self.assertTrue(isi["ai"]["kunci_terisi"])

    def test_08_ai_ringkas_tidak_memuat_kunci(self):
        p = self.p.dengan(ai_api_key="rahasia-abc")
        ringkas = p.ai_ringkas()
        self.assertNotIn("rahasia-abc", json.dumps(ringkas))
        self.assertTrue(ringkas["kunci_terisi"])
        # Pengaturan asli tidak ikut berubah.
        self.assertEqual(self.p.ai_api_key, "kunci-server")

    def test_09_kredensial_kosong_tetap_memakai_server(self):
        p = self.p.dengan(ai_api_key="", ai_base_url="", ai_model="")
        self.assertEqual(p.ai_api_key, "kunci-server")

    # --- uji koneksi AI --------------------------------------------------
    def test_10_uji_koneksi_memakai_kredensial_yang_dikirim(self):
        badan, jenis = multipart(
            {
                "ai_api_key": "kunci-uji",
                "ai_base_url": "https://contoh.invalid/v1",
                "ai_model": "model-uji",
            },
            {},
        )
        kode, data, _ = self.panggil("/v1/ai/uji", "POST", badan, jenis)
        self.assertEqual(kode, 200, data)
        isi = json.loads(data)
        self.assertEqual(isi["model"], "model-uji")
        self.assertNotIn("kunci-uji", data.decode())

    def test_11_uji_koneksi_tanpa_kunci_ditolak(self):
        """Kalau server juga tidak punya kunci, uji koneksi harus ditolak."""
        layanan = self.httpd.RequestHandlerClass.layanan
        simpan = layanan.p.ai_api_key
        layanan.p.ai_api_key = ""
        try:
            badan, jenis = multipart({"ai_model": "model-uji"}, {})
            kode, data, _ = self.panggil("/v1/ai/uji", "POST", badan, jenis)
        finally:
            layanan.p.ai_api_key = simpan
        self.assertEqual(kode, 503, data)
        self.assertEqual(json.loads(data)["error"], "ai_belum_diatur")

    def test_12_kredensial_pengguna_menang_atas_server(self):
        """Kredensial yang dikirim pengguna dipakai, bukan milik server."""
        badan, jenis = multipart(
            {
                "ai_api_key": "kunci-pengguna",
                "ai_base_url": "https://contoh.invalid/v1",
                "ai_model": "model-pengguna",
            },
            {},
        )
        kode, data, _ = self.panggil("/v1/ai/uji", "POST", badan, jenis)
        self.assertEqual(kode, 200, data)
        self.assertEqual(json.loads(data)["model"], "model-pengguna")
        # Kunci server tidak ikut berubah.
        self.assertEqual(
            self.httpd.RequestHandlerClass.layanan.p.ai_api_key, "kunci-server"
        )


class UjiKredensialTanpaServer(unittest.TestCase):
    """Bagian yang tidak butuh server berjalan."""

    def test_klien_untuk_memakai_kredensial_job(self):
        from daspro_api.pipeline import Pipeline
        from daspro_api.skillbridge import Skill

        p = Pengaturan(ai_api_key="kunci-server", ai_model="model-server")
        pl = Pipeline(p, skill=Skill(ROOT / "skill"))
        bawaan = pl.klien_untuk(None)
        self.assertIs(bawaan, pl.klien)
        self.assertEqual(bawaan.p.ai_api_key, "kunci-server")

        khusus = pl.klien_untuk({"api_key": "kunci-lain", "model": "model-lain"})
        self.assertIsNot(khusus, pl.klien)
        self.assertEqual(khusus.p.ai_api_key, "kunci-lain")
        self.assertEqual(khusus.p.ai_model, "model-lain")
        # Pengaturan server tidak ikut berubah.
        self.assertEqual(pl.p.ai_api_key, "kunci-server")

    def test_kredensial_tanpa_kunci_tetap_ditolak(self):
        from daspro_api.pipeline import Pipeline
        from daspro_api.skillbridge import Skill

        p = Pengaturan(ai_api_key="")
        pl = Pipeline(p, skill=Skill(ROOT / "skill"))
        klien = pl.klien_untuk({"model": "model-lain"})
        with self.assertRaises(AiBelumDiatur):
            klien.periksa()


if __name__ == "__main__":
    unittest.main(verbosity=2)
