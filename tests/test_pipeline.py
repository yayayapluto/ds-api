#!/usr/bin/env python3
"""Pengujian alur lengkap memakai AI tiruan.

Tidak ada panggilan ke internet di sini. Jawaban AI dibuat-buat, lalu
diperiksa bahwa kode C benar-benar dikompilasi, dijalankan, dan hasilnya
masuk ke laporan dan template docx.
"""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from daspro_api.ai import ambil_json  # noqa: E402
from daspro_api.compiler import KompilatorC  # noqa: E402
from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.pipeline import Pipeline, rapikan_identitas  # noqa: E402
from daspro_api.sanitize import bersihkan, cari_pelanggar  # noqa: E402
from daspro_api.skillbridge import Skill  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

KODE_LATIHAN_01 = """#include <stdio.h>

int main(void)
{
    int n;

    printf("Masukkan n: ");
    scanf("%d", &n);

    if (n < 1)
    {
        printf("Nilai tidak valid.\\n");
        return 1;
    }

    for (int i = 1; i <= n; i++)
    {
        printf("%d\\n", i);
    }

    return 0;
}
"""

KODE_LATIHAN_02 = """#include <stdio.h>

int main(void)
{
    int n;
    double nilai, jumlah = 0.0, rata;

    printf("Masukkan banyak data: ");
    scanf("%d", &n);

    if (n < 1)
    {
        printf("Nilai tidak valid.\\n");
        return 1;
    }

    for (int i = 1; i <= n; i++)
    {
        scanf("%lf", &nilai);
        jumlah = jumlah + nilai;
    }

    rata = jumlah / n;
    printf("Rata-rata : %.2f\\n", rata);

    return 0;
}
"""

KODE_TUGAS = """/*
Nama        : -
NIM         : -
Kelas       : -
Modul       : 5
Deskripsi   : Mencetak tabel perkalian sebuah bilangan.
*/

#include <stdio.h>

int main(void)
{
    int n;

    printf("Masukkan n: ");
    scanf("%d", &n);

    if ((n < 1) || (n > 10))
    {
        printf("Nilai tidak valid.\\n");
        return 1;
    }

    for (int i = 1; i <= 10; i++)
    {
        printf("%d x %d = %d\\n", n, i, n * i);
    }

    return 0;
}
"""


def jawab_analisis(_prompt: str) -> str:
    return json.dumps(
        {
            "modul": 5,
            "judul": "Perulangan",
            "soal": [
                {
                    "id": "latihan_01",
                    "nama_berkas": "latihan_01.c",
                    "folder": "",
                    "jenis": "terbimbing",
                    "judul": "Deret Bilangan",
                    "deskripsi": "Mencetak angka 1 sampai n.",
                    "kasus_uji": [
                        {"masukan": "5\n", "harapan": "angka 1 sampai 5"},
                        {"masukan": "1\n", "harapan": "hanya angka 1"},
                        {"masukan": "0\n", "harapan": "pesan tidak valid"},
                    ],
                },
                {
                    "id": "latihan_02",
                    "nama_berkas": "latihan_02.c",
                    "folder": "",
                    "jenis": "terbimbing",
                    "judul": "Rata-rata Nilai",
                    "deskripsi": "Mencetak rata-rata beberapa nilai.",
                    "kasus_uji": [
                        {"masukan": "3\n70\n80\n90\n", "harapan": "rata-rata 80.00"},
                        {"masukan": "0\n", "harapan": "pesan tidak valid"},
                    ],
                },
                {
                    "id": "tugas_modul_05",
                    "nama_berkas": "tugas_modul_05.c",
                    "folder": "tugas",
                    "jenis": "tugas",
                    "judul": "Tabel Perkalian",
                    "deskripsi": "Mencetak tabel perkalian n.",
                    "kasus_uji": [
                        {"masukan": "3\n", "harapan": "tabel perkalian 3"},
                        {"masukan": "11\n", "harapan": "pesan tidak valid"},
                    ],
                },
            ],
            "catatan": "Modul meminta laporan pengujian dan penjelasan cara kerja.",
        }
    )


def jawab_kode(prompt: str) -> str:
    if "latihan_01.c" in prompt:
        kode = KODE_LATIHAN_01
        judul = "Deret Bilangan"
    elif "latihan_02.c" in prompt:
        kode = KODE_LATIHAN_02
        judul = "Rata-rata Nilai"
    else:
        kode = KODE_TUGAS
        judul = "Tabel Perkalian"
    return json.dumps(
        {
            "nama_berkas": "program.c",
            "kode": kode,
            "penjelasan": f"Program {judul} membaca masukan lalu mencetak hasilnya.",
            "tabel_uji": [{"masukan": "5", "expected": "keluaran sesuai", "catatan": "nilai batas"}],
        }
    )


def jawab_laporan(prompt: str) -> str:
    return json.dumps(
        {
            "judul": "Jawaban LKP Modul 5 - Perulangan",
            "bagian": [
                {
                    "kode": "IV.1",
                    "judul": "Deret Bilangan",
                    "analisis": [
                        {
                            "pertanyaan": "Mengapa nilai nol harus ditolak?",
                            "jawaban": (
                                "Karena perulangan dari 1 sampai 0 tidak pernah berjalan, "
                                "jadi tidak ada angka yang tercetak."
                            ),
                        }
                    ],
                    "trace": {
                        "kolom": ["Langkah", "Kondisi", "Hasil Kondisi"],
                        "baris": [["1", "i <= n", "true"], ["6", "i <= n", "false"]],
                    },
                    "prediksi_output": "Angka 1 sampai 5 tercetak satu tiap baris.",
                }
            ],
            "eksperimen": [
                {
                    "perubahan": "Mengubah batas perulangan jadi i < n",
                    "prediksi": "Angka terakhir tidak tercetak",
                    "hasil": "Angka 5 tidak muncul",
                    "error": "tidak ada",
                    "penjelasan": "Perulangan berhenti sebelum angka terakhir.",
                }
            ],
            "debugging": {
                "error_gcc": "error: expected ';' before '}' token",
                "temuan": [
                    {
                        "bagian": "baris printf terakhir",
                        "jenis": "gagal dikompilasi",
                        "penyebab": "Tanda titik koma belum ditulis.",
                        "perbaikan": "Menambahkan tanda titik koma di akhir baris.",
                    }
                ],
            },
            "refleksi": [
                "Saya jadi lebih paham cara kerja perulangan for.",
                "Nilai batas harus diuji supaya program tidak salah hitung.",
                "Menjalankan program sendiri membuat hasilnya lebih yakin.",
            ],
            "isian_lkp": {
                "titik": {"1": "1 2 3 4 5", "2": "Angka tercetak naik satu tiap baris."},
                "sel": {"1A2B3C4D": "Sesuai", "1A2B3C4E": "1 2 3 4 5"},
            },
        }
    )


class UjiAlat(unittest.TestCase):
    def test_ambil_json_dari_teks_berpenjelasan(self):
        teks = 'Baik, ini hasilnya:\n```json\n{"a": 1, "b": [2, 3]}\n```\nSemoga membantu.'
        self.assertEqual(ambil_json(teks), {"a": 1, "b": [2, 3]})

    def test_ambil_json_gagal(self):
        with self.assertRaises(Exception):
            ambil_json("tidak ada json di sini")

    def test_bersihkan_karakter_aneh(self):
        aneh = "panah \u2192 nilai \u2265 85 \u2014 selesai\u2026 \u201ckutip\u201d"
        hasil = bersihkan(aneh)
        self.assertEqual(hasil, 'panah -> nilai >= 85 - selesai... "kutip"')
        self.assertEqual(cari_pelanggar(hasil), {})

    def test_identitas_kurang(self):
        with self.assertRaises(Exception):
            rapikan_identitas({"nama": "A", "nim": "1"})


class UjiKompilator(unittest.TestCase):
    def setUp(self):
        self.p = Pengaturan(ai_provider="mock")
        self.gcc = KompilatorC(self.p)

    def test_kompilasi_bersih_dan_jalan(self):
        with tempfile.TemporaryDirectory() as tmp:
            berkas = pathlib.Path(tmp) / "uji.c"
            berkas.write_text(KODE_LATIHAN_01, encoding="utf-8")
            kompil, jalan = self.gcc.kompilasi_dan_jalan(berkas, masukan="3\n")
            self.assertTrue(kompil.ok, kompil.pesan_error)
            self.assertEqual(kompil.peringatan, [])
            assert jalan is not None
            self.assertIn("1\n2\n3", jalan.keluaran)

    def test_kompilasi_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            berkas = pathlib.Path(tmp) / "rusak.c"
            berkas.write_text("int main(void) { return }\n", encoding="utf-8")
            kompil, jalan = self.gcc.kompilasi_dan_jalan(berkas)
            self.assertFalse(kompil.ok)
            self.assertIsNone(jalan)

    def test_program_tak_berhenti_dibatasi(self):
        with tempfile.TemporaryDirectory() as tmp:
            berkas = pathlib.Path(tmp) / "putar.c"
            berkas.write_text(
                "int main(void) { for (;;) { } return 0; }\n", encoding="utf-8"
            )
            kompil, jalan = self.gcc.kompilasi_dan_jalan(berkas, timeout=1)
            self.assertTrue(kompil.ok)
            assert jalan is not None
            self.assertTrue(jalan.timeout)


class UjiSkill(unittest.TestCase):
    def setUp(self):
        self.skill = Skill(ROOT / "skill")
        self.skill.periksa()

    def test_md_ke_copyable(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = FIXTURES / "jawaban_contoh.md"
            html = pathlib.Path(tmp) / "hasil.html"
            self.skill.md_ke_copyable(md, html)
            isi = html.read_text(encoding="utf-8")
            self.assertIn("copy</button>", isi)
            self.assertEqual(cari_pelanggar(isi), {})

    def test_peta_dan_isi_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            kerja = pathlib.Path(tmp) / "kerja"
            peta = self.skill.peta_docx(FIXTURES / "lkp_contoh.docx", kerja)
            self.assertTrue(peta["sel_kosong"])
            self.assertTrue(peta["baris_titik"])
            kunci = peta["sel_kosong"][0]["kunci"]
            hasil = pathlib.Path(tmp) / "hasil.docx"
            laporan = self.skill.isi_docx(
                kerja,
                {"sel": {kunci: "Sesuai"}, "titik": {"1": "1 2 3 4 5"}},
                hasil,
            )
            self.assertTrue(laporan["struktur_utuh"], laporan)
            self.assertTrue(hasil.is_file())


class UjiPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="daspro_uji_")
        self.p = Pengaturan(
            data_dir=pathlib.Path(self.tmp),
            skill_dir=ROOT / "skill",
            ai_provider="mock",
            job_workers=1,
        )
        from daspro_api.ai import KlienAi

        self.klien = KlienAi(self.p, mock_balasan=[jawab_analisis, jawab_kode, jawab_kode, jawab_kode, jawab_laporan])
        self.pipeline = Pipeline(self.p, skill=Skill(self.p.skill_dir), klien=self.klien)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_alur_lengkap_menghasilkan_zip(self):
        class Job:
            def __init__(self, folder):
                self.folder = pathlib.Path(folder)
                self.batal = __import__("threading").Event()
                self.tahap = []
                self.folder.mkdir(parents=True, exist_ok=True)

            def maju(self, tahap, pesan="", persen=None):
                self.tahap.append(tahap)

        job = Job(pathlib.Path(self.tmp) / "job1")
        hasil = self.pipeline.kerjakan(
            job,
            berkas_modul=FIXTURES / "modul_contoh.pdf",
            berkas_lkp=FIXTURES / "lkp_contoh.docx",
            identitas={
                "nama": "-",
                "nim": "-",
                "kelas": "-",
                "modul": "5",
                "matakuliah": "Praktikum Dasar Pemrograman",
            },
        )

        self.assertEqual(hasil["jumlah_soal"], 3)
        zip_path = pathlib.Path(self.tmp) / "job1" / "kerja" / hasil["zip"]["nama"]
        self.assertTrue(zip_path.is_file(), f"zip tidak ada: {zip_path}")
        self.assertTrue(hasil["cek_bahasa"]["lulus"], hasil["cek_bahasa"])
        self.assertEqual(hasil["karakter_non_keyboard"], {})
        self.assertTrue(hasil["isi_template"]["struktur_utuh"], hasil["isi_template"])
        self.assertGreater(hasil["isi_template"]["sel_diisi"], 0)
        self.assertGreater(hasil["isi_template"]["baris_diisi"], 0)

        # Keluaran nyata harus muncul di laporan, bukan karangan.
        md = (
            pathlib.Path(self.tmp) / "job1" / "kerja" / hasil["berkas"]["laporan_md"]
        ).read_text(encoding="utf-8")
        self.assertIn("Sesuai", md)
        self.assertEqual(cari_pelanggar(md), {})

        # Berkas kode ikut, termasuk yang di folder tugas.
        import zipfile

        with zipfile.ZipFile(zip_path) as z:
            nama = z.namelist()
        self.assertIn("latihan_01.c", nama)
        self.assertIn("latihan_02.c", nama)
        self.assertIn("tugas/tugas_modul_05.c", nama)
        self.assertTrue(any(n.endswith("_copyable.html") for n in nama))
        self.assertTrue(any(n.startswith("LKP_Modul_5") for n in nama))
        self.assertIn("ringkasan.json", nama)


if __name__ == "__main__":
    unittest.main(verbosity=2)
