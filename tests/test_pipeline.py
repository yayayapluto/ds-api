#!/usr/bin/env python3
"""Pengujian alur lengkap memakai AI tiruan.

Tidak ada panggilan ke internet di sini. Jawaban AI dibuat-buat, lalu
diperiksa bahwa kode C benar-benar dikompilasi, dijalankan, dan hasilnya
masuk ke laporan dan template docx.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import unittest.mock
import urllib.error
import email.message
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from daspro_api.ai import KlienAi, ambil_json, baca_json_http  # noqa: E402
from daspro_api.compiler import KompilatorC  # noqa: E402
from daspro_api.config import Pengaturan  # noqa: E402
from daspro_api.errors import AiGagal  # noqa: E402
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
    peta = json.loads(prompt.split("=== PETA ISIAN LKP ===", 1)[1].split("\n===", 1)[0])
    identitas = dict(
        baris.split(": ", 1)
        for baris in prompt.split("=== IDENTITAS MAHASISWA ===", 1)[1].split("\n===", 1)[0].strip().splitlines()
    )
    hasil = json.loads(
        prompt.split("=== HASIL PENGUJIAN NYATA (keluaran ini yang benar, jangan diubah) ===", 1)[1]
        .split("\n===", 1)[0]
    )
    deret = next(item for item in hasil if item["berkas"] == "latihan_01.c")
    kasus = deret["kasus_uji"]
    bukti = "\n\n".join(
        f"Masukan: {uji['masukan'].strip()}\nHarapan: {uji['harapan']}\n"
        f"Keluaran nyata:\n{uji['keluaran']}\nKode keluar: {uji['kode_keluar']}\n"
        f"Status: {uji['status']}"
        for uji in kasus
    )
    sel = {}
    for item in peta["sel_kosong"]:
        if not item.get("wajib", True):
            sel[item["kunci"]] = ""
        elif "latihan_01.c" in item["soal"]:
            sel[item["kunci"]] = bukti
        else:
            raise AssertionError(f"Sel fixture tidak dikenali: {item}")
    titik = {}
    for item in peta["baris_titik"]:
        soal = item["soal"]
        label = soal.splitlines()[-1].rstrip(":")
        if not item.get("wajib", True):
            jawaban = ""
        elif label in ("Nama", "NIM", "Kelas"):
            jawaban = identitas[label]
        elif "Pernyataan:" in soal:
            jawaban = (
                "Program diuji otomatis dengan gcc, bukan dijalankan manual oleh mahasiswa. "
                "Masukan 0 ditolak dengan pesan Nilai tidak valid. dan kode keluar 1."
            )
        elif "Jelaskan cara kerja program:" in soal:
            jawaban = (
                "Program membaca n lalu memeriksa apakah nilainya 1 sampai 10. "
                "Perulangan for menaikkan i dari 1 sampai 10 dan mencetak n * i. "
                "Masukan 3 menghasilkan perkalian dari 3 x 1 = 3 sampai 3 x 10 = 30."
            )
        elif "Kesimpulan:" in soal:
            jawaban = (
                "Program mencetak bilangan dari 1 sampai n. "
                "Nilai n kurang dari 1 ditolak sebelum perulangan.\n" + bukti
            )
        else:
            raise AssertionError(f"Baris fixture tidak dikenali: {item}")
        titik[str(item["no"])] = jawaban
    return json.dumps(
        {
            "judul": "Jawaban LKP Modul 5 - Perulangan",
            "bagian": [
                {
                    "kode": "IV.1",
                    "judul": "Deret Bilangan",
                    "berkas": "latihan_01.c",
                    "analisis": [
                        {
                            "pertanyaan": "Bagaimana hasil pengujian program latihan_01.c?",
                            "jawaban": bukti,
                        }
                    ],
                }
            ],
            "eksperimen": [],
            "debugging": {},
            "refleksi": [
                "Perulangan for mencetak angka dari 1 sampai n. Nilai i bertambah satu setiap putaran.",
                "Nilai nol ditolak sebelum perulangan. Program berhenti dengan kode keluar 1.",
                "Hasil ini berasal dari pengujian otomatis. Pengujian manual mahasiswa belum dicatat.",
            ],
            "isian_lkp": {"titik": titik, "sel": sel},
        }
    )


class UjiAlat(unittest.TestCase):
    def test_ambil_json_dari_teks_berpenjelasan(self):
        teks = 'Baik, ini hasilnya:\n```json\n{"a": 1, "b": [2, 3]}\n```\nSemoga membantu.'
        self.assertEqual(ambil_json(teks), {"a": 1, "b": [2, 3]})

    def test_ambil_json_gagal(self):
        with self.assertRaises(Exception):
            ambil_json("tidak ada json di sini")

    def test_baca_json_http_mengabaiki_trailing_sse(self):
        teks = chr(10) + "         " + chr(10) + '{"id":"x","choices":[]}data: [DONE]' + chr(10) + chr(10)
        self.assertEqual(baca_json_http(teks), {"id": "x", "choices": []})

    def test_baca_json_http_leading_whitespace(self):
        teks = '   {"a": 1}  '
        self.assertEqual(baca_json_http(teks), {"a": 1})

    def test_baca_json_http_awal_data_sse(self):
        teks = 'data: {"a": 1}' + chr(10) + 'data: [DONE]'
        self.assertEqual(baca_json_http(teks), {"a": 1})

    def test_baca_json_http_kosong(self):
        with self.assertRaises(Exception):
            baca_json_http('')

    def test_bersihkan_karakter_aneh(self):
        aneh = "panah \u2192 nilai \u2265 85 \u2014 selesai\u2026 \u201ckutip\u201d"
        hasil = bersihkan(aneh)
        self.assertEqual(hasil, 'panah -> nilai >= 85 - selesai... "kutip"')
        self.assertEqual(cari_pelanggar(hasil), {})

    def test_identitas_kurang(self):
        with self.assertRaises(Exception):
            rapikan_identitas({"nama": "A", "nim": "1"})


class UjiPengulanganAi(unittest.TestCase):
    """Panggilan yang gagal sementara diulang, yang tetap tidak.

    Ini yang dulu membuat pekerjaan berhenti di tengah: satu jawaban kosong
    dari layanan AI langsung menandai seluruh pekerjaan gagal, padahal
    percobaan berikutnya biasanya berhasil.
    """

    class KlienUji(KlienAi):
        """Klien yang satu percobaannya dijalankan oleh fungsi `jawaban`."""

        def __init__(self, pengaturan, jawaban):
            super().__init__(pengaturan)
            self.jawaban = jawaban
            self.hitung = 0

        def _lengkapi_sekali(self, prompt, sistem="", suhu=None, token=None) -> str:
            self.hitung += 1
            return self.jawaban(self.hitung)

    def _p(self, ai_retry: int = 2) -> Pengaturan:
        return Pengaturan(
            ai_api_key="kunci-uji",
            ai_base_url="http://localhost/v1",
            ai_model="model-uji",
            ai_retry=ai_retry,
        )

    def test_gagal_sementara_diulang_lalu_berhasil(self):
        def jawaban(n):
            if n <= 2:
                raise AiGagal("jawaban AI kosong", sementara=True)
            return "halo"

        klien = self.KlienUji(self._p(), jawaban)
        self.assertEqual(klien.lengkapi("apa saja"), "halo")
        self.assertEqual(klien.hitung, 3)

    def test_gagal_tetap_tidak_diulang(self):
        def jawaban(n):
            raise AiGagal("kunci salah", sementara=False)

        klien = self.KlienUji(self._p(), jawaban)
        with self.assertRaises(AiGagal):
            klien.lengkapi("apa saja")
        # Kegagalan tetap hanya dicoba sekali, tidak menunggu sia-sia.
        self.assertEqual(klien.hitung, 1)

    def test_menyerah_setelah_batas_pengulangan(self):
        def jawaban(n):
            raise AiGagal("jawaban AI kosong", sementara=True)

        klien = self.KlienUji(self._p(ai_retry=2), jawaban)
        with self.assertRaises(AiGagal):
            klien.lengkapi("apa saja")
        # Satu percobaan awal + dua pengulangan.
        self.assertEqual(klien.hitung, 3)

    def test_retry_nol_berarti_sekali_coba(self):
        def jawaban(n):
            raise AiGagal("jawaban AI kosong", sementara=True)

        klien = self.KlienUji(self._p(ai_retry=0), jawaban)
        with self.assertRaises(AiGagal):
            klien.lengkapi("apa saja")
        self.assertEqual(klien.hitung, 1)

    def _galat_http(self, kode: int, alasan: str) -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            "http://localhost/v1", kode, alasan, email.message.Message(), None
        )

    def test_kegagalan_jaringan_ditandai_sementara(self):
        """Galat jaringan pantas diulang, kunci salah tidak."""
        klien = KlienAi(self._p())
        with unittest.mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("koneksi ditolak"),
        ):
            with self.assertRaises(AiGagal) as ctx:
                klien._kirim("http://localhost/v1", {}, {})
        self.assertTrue(ctx.exception.sementara)

    def test_http_429_ditandai_sementara(self):
        klien = KlienAi(self._p())
        galat = self._galat_http(429, "Too Many Requests")
        with unittest.mock.patch("urllib.request.urlopen", side_effect=galat):
            with self.assertRaises(AiGagal) as ctx:
                klien._kirim("http://localhost/v1", {}, {})
        self.assertTrue(ctx.exception.sementara)

    def test_http_401_tidak_ditandai_sementara(self):
        klien = KlienAi(self._p())
        galat = self._galat_http(401, "Unauthorized")
        with unittest.mock.patch("urllib.request.urlopen", side_effect=galat):
            with self.assertRaises(AiGagal) as ctx:
                klien._kirim("http://localhost/v1", {}, {})
        self.assertFalse(ctx.exception.sementara)

class UjiKompilator(unittest.TestCase):
    def setUp(self):
        self.p = Pengaturan(ai_api_key="uji", ai_base_url="http://localhost")
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
            job_workers=1,
        )
        from mockai import KlienAiTiruan

        self.klien = KlienAiTiruan(
            self.p,
            balasan=[jawab_analisis, jawab_kode, jawab_kode, jawab_kode, jawab_laporan],
        )
        self.pipeline = Pipeline(self.p, skill=Skill(self.p.skill_dir), klien=self.klien)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_isian_lkp_tidak_sah_ditolak(self):
        kerja = pathlib.Path(self.tmp) / "docx_kerja"
        peta = {
            "sel_kosong": [{"kunci": "ABCD1234", "soal": "Tuliskan hasil pengujian."}],
            "baris_titik": [],
        }
        for sel in (
            {},
            {"ABCD1234": " \n"},
            {"ABCD1234": 42},
            {"ABCD1234": "Sudah dikerjakan sesuai modul."},
            {"ABCD1234": "Masukan 5 mencetak 1 sampai 5.", "SALAH": "Jawaban salah tempat."},
        ):
            with self.subTest(sel=sel), self.assertRaises(AiGagal):
                self.pipeline.isi_template(None, kerja, peta, {"isian_lkp": {"sel": sel}})
        self.assertFalse((kerja.parent / "LKP_terisi.docx").exists())

    def test_alur_lengkap_menghasilkan_zip(self):
        class Job:
            def __init__(self, folder):
                self.folder = pathlib.Path(folder)
                self.batal = threading.Event()
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
        self.assertIn("Masukkan n: 1", md)
        self.assertIn("Nilai tidak valid.", md)
        self.assertEqual(cari_pelanggar(md), {})

        # Berkas kode ikut, termasuk yang di folder tugas.
        with zipfile.ZipFile(zip_path) as z:
            nama = z.namelist()
            paket = pathlib.Path(self.tmp) / "paket hasil"
            z.extractall(paket)
        self.assertIn("latihan_01.c", nama)
        self.assertIn("latihan_02.c", nama)
        self.assertIn("tugas/tugas_modul_05.c", nama)
        self.assertTrue(any(n.endswith("_copyable.html") for n in nama))
        self.assertTrue(any(n.startswith("LKP_Modul_5") for n in nama))
        self.assertNotIn("ringkasan.json", nama)
        self.assertFalse((zip_path.parent / "ringkasan.json").exists())
        self.assertIn("kompilasi.sh", nama)

        # Bukti kasus nyata harus sampai ke AI lalu ke teks DOCX, bukan hanya MD.
        docx = next(paket.glob("LKP_Modul_5*.docx"))
        with zipfile.ZipFile(docx) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        teks_docx = " ".join(" ".join(root.itertext()).split())
        self.assertIn("Masukkan n: 1 2 3 4 5", teks_docx)
        self.assertIn("Masukkan n: Nilai tidak valid.", teks_docx)
        self.assertIn("Kode keluar: 1", teks_docx)
        self.assertIn("n * i", teks_docx)
        self.assertNotIn("Sudah dikerjakan sesuai modul.", teks_docx)

        # Skrip harus bekerja dari folder lain, termasuk sumber di subfolder.
        cwd_lain = pathlib.Path(self.tmp) / "folder lain"
        cwd_lain.mkdir()
        kompil = subprocess.run(
            ["sh", str(paket / "kompilasi.sh")], cwd=cwd_lain,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(kompil.returncode, 0, kompil.stderr)
        for berkas, masukan, keluaran in (
            ("latihan_01", "5\n", "Masukkan n: 1\n2\n3\n4\n5\n"),
            ("latihan_02", "3\n70\n80\n90\n", "Masukkan banyak data: Rata-rata : 80.00\n"),
            ("tugas/tugas_modul_05", "3\n", "Masukkan n: " + "".join(
                f"3 x {i} = {3 * i}\n" for i in range(1, 11)
            )),
        ):
            with self.subTest(berkas=berkas):
                jalan = subprocess.run(
                    [str(paket / "bin" / berkas)], input=masukan, cwd=cwd_lain,
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(jalan.returncode, 0, jalan.stderr)
                self.assertEqual(jalan.stdout, keluaran)


if __name__ == "__main__":
    unittest.main(verbosity=2)
