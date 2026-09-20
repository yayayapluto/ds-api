#!/usr/bin/env python3
"""Pengujian endpoint HTTP dari ujung ke ujung.

Server dijalankan di dalam proses pada port bebas, lalu semua endpoint
dipanggil memakai urllib seperti pemanggil sungguhan. Tidak ada jaringan
keluar, jadi pengujian ini aman dijalankan di mana saja.
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
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mockai import KlienAiTiruan  # noqa: E402
from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.server import buat_server  # noqa: E402
from daspro_api.skillbridge import Skill  # noqa: E402
from test_pipeline import jawab_analisis, jawab_kode, jawab_laporan  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
KODE_BAIK = """#include <stdio.h>

int main(void)
{
    printf("halo\\n");
    return 0;
}
"""


def multipart(fields: dict, files: dict) -> tuple:
    """Susun badan multipart dan header yang cocok."""
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


class UjiServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="daspro_server_")
        cls.p = Pengaturan(
            host="127.0.0.1",
            port=0,
            data_dir=pathlib.Path(cls.tmp),
            skill_dir=ROOT / "skill",
            job_workers=1,
        )
        cls.httpd = buat_server(cls.p, wajib_ai=False)
        # Klien AI tiruan dipasang setelah server dibuat, sebelum ada permintaan.
        tiruan = KlienAiTiruan(
            cls.p,
            balasan=[
                jawab_analisis,
                jawab_kode,
                jawab_kode,
                jawab_kode,
                jawab_laporan,
            ],
        )
        # Klien tiruan dipasang di layanan dan di pipeline.
        cls.httpd.RequestHandlerClass.layanan.klien = tiruan
        cls.httpd.RequestHandlerClass.layanan.pipeline.klien = tiruan
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # --- alat bantu ------------------------------------------------------
    def panggil(self, jalur: str, metode: str = "GET", badan=None, jenis=None):
        url = f"http://127.0.0.1:{self.port}{jalur}"
        req = urllib.request.Request(url, data=badan, method=metode)
        if jenis:
            req.add_header("Content-Type", jenis)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type", "")

    def json_panggil(self, jalur, metode="GET", badan=None, jenis=None):
        kode, data, _ = self.panggil(jalur, metode, badan, jenis)
        return kode, json.loads(data.decode("utf-8"))

    # --- pengujian -------------------------------------------------------
    def test_01_health(self):
        kode, data = self.json_panggil("/health")
        self.assertEqual(kode, 200)
        self.assertTrue(data["ok"])
        self.assertTrue(data["skill_siap"])
        self.assertTrue(data["gcc"])

    def test_02_skill(self):
        kode, data = self.json_panggil("/v1/skill")
        self.assertEqual(kode, 200)
        self.assertIn("cek_bahasa.py", data["skrip"])

    def test_03_verify(self):
        badan, jenis = multipart(
            {"masukan": "3\n"}, {"files": ("program.c", KODE_BAIK.encode())}
        )
        kode, data = self.json_panggil("/v1/verify", "POST", badan, jenis)
        self.assertEqual(kode, 200)
        self.assertTrue(data["ok"], data)
        self.assertEqual(data["hasil"][0]["keluaran"].strip(), "halo")

    def test_04_verify_gagal(self):
        badan, jenis = multipart({}, {"files": ("rusak.c", b"int main(void) { return }\n")})
        kode, data = self.json_panggil("/v1/verify", "POST", badan, jenis)
        self.assertEqual(kode, 200)
        self.assertFalse(data["ok"])
        self.assertIn("error", data["hasil"][0]["pesan_error"])

    def test_05_cek_bahasa(self):
        data_md = (FIXTURES / "jawaban_contoh.md").read_bytes()
        badan, jenis = multipart({}, {"files": ("laporan.md", data_md)})
        kode, data = self.json_panggil("/v1/cek-bahasa", "POST", badan, jenis)
        self.assertEqual(kode, 200)
        self.assertTrue(data["lulus"], data)

    def test_06_docx_peta_dan_isi(self):
        docx = (FIXTURES / "lkp_contoh.docx").read_bytes()
        badan, jenis = multipart({}, {"template": ("lkp.docx", docx)})
        kode, data = self.json_panggil("/v1/docx/peta", "POST", badan, jenis)
        self.assertEqual(kode, 200)
        self.assertGreater(data["jumlah_sel_kosong"], 0)
        kunci = data["peta"]["sel_kosong"][0]["kunci"]

        mapping = json.dumps({"sel": {kunci: "Sesuai"}, "titik": {"1": "1 2 3 4 5"}})
        badan, jenis = multipart(
            {"mapping": mapping}, {"template": ("lkp.docx", docx)}
        )
        kode, data = self.json_panggil("/v1/docx/isi", "POST", badan, jenis)
        self.assertEqual(kode, 200)
        self.assertTrue(data["struktur_utuh"], data)

    def test_07_job_lengkap_sampai_zip(self):
        docx = (FIXTURES / "lkp_contoh.docx").read_bytes()
        pdf = (FIXTURES / "modul_contoh.pdf").read_bytes()
        identitas = json.dumps(
            {
                "nama": "-",
                "nim": "-",
                "kelas": "-",
                "modul": "5",
                "matakuliah": "Praktikum Dasar Pemrograman",
            }
        )
        badan, jenis = multipart(
            {"identitas": identitas, "isi_docx": "true"},
            {
                "modul": ("modul.pdf", pdf),
                "lkp": ("lkp.docx", docx),
            },
        )
        kode, data = self.json_panggil("/v1/jobs", "POST", badan, jenis)
        self.assertEqual(kode, 202, data)
        job_id = data["job_id"]

        # Tunggu sampai pekerjaan selesai.
        import time

        status = {"status": "menunggu", "persen": 0}
        for _ in range(120):
            kode, status = self.json_panggil(f"/v1/jobs/{job_id}")
            if status["status"] in {"selesai", "gagal", "dibatalkan"}:
                break
            time.sleep(0.25)
        self.assertEqual(status["status"], "selesai", status)
        self.assertEqual(status["persen"], 100)

        kode, hasil = self.json_panggil(f"/v1/jobs/{job_id}/result")
        self.assertEqual(kode, 200)
        ringkas = hasil["hasil"]
        self.assertEqual(ringkas["jumlah_soal"], 3)
        self.assertTrue(ringkas["cek_bahasa"]["lulus"])
        self.assertEqual(ringkas["karakter_non_keyboard"], {})

        kode, zip_data, jenis_isi = self.panggil(f"/v1/jobs/{job_id}/download")
        self.assertEqual(kode, 200)
        self.assertIn("zip", jenis_isi)
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            nama = z.namelist()
            md = z.read(f"jawaban_LKP_Modul_5.md").decode("utf-8")
            docx_isi = z.read(f"LKP_Modul_5_-.docx")
        self.assertIn("latihan_01.c", nama)
        self.assertIn("tugas/tugas_modul_05.c", nama)
        self.assertIn("Expected Output", md)
        self.assertIn("Sesuai", md)
        self.assertTrue(docx_isi.startswith(b"PK"))

        # Satu berkas juga bisa diunduh terpisah.
        kode, isi_c, _ = self.panggil(f"/v1/jobs/{job_id}/files/latihan_01.c")
        self.assertEqual(kode, 200)
        self.assertIn(b"int main", isi_c)

    def test_08_galat_jelas(self):
        kode, data = self.json_panggil("/v1/jobs/tdkada")
        self.assertEqual(kode, 404)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "tidak_ditemukan")

        kode, data = self.json_panggil("/v1/jobs", "POST", b"{}", "application/json")
        self.assertEqual(kode, 400)
        self.assertEqual(data["error"], "input_tidak_valid")

        kode, data = self.json_panggil("/tidak/ada")
        self.assertEqual(kode, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
