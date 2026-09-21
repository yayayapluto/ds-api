#!/usr/bin/env python3
"""Penempatan jawaban DOCX tanpa mengubah label dan struktur template."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import xml.etree.ElementTree as etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from daspro_api.skillbridge import Skill

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
HEADER = (
    f'<w:document xmlns:w="{W}" '
    'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"><w:body>'
)


def p(teks):
    return f"<w:p><w:r><w:t>{teks}</w:t></w:r></w:p>"


def teks(node):
    return "".join(t.text or "" for t in node.findall(".//w:t", NS))


class DocxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.kerja = self.root / "unpacked"
        self.skill = Skill(ROOT / "skill")

    def petakan(self, body):
        sumber = self.root / "template.docx"
        self.xml = (HEADER + body + "</w:body></w:document>").encode()
        with zipfile.ZipFile(sumber, "w") as archive:
            archive.writestr("word/document.xml", self.xml)
            archive.writestr("word/styles.xml", "<styles/>")
        return self.skill.peta_docx(sumber, self.kerja)

    def isi(self, mapping):
        hasil = self.root / "jawaban.docx"
        self.skill.isi_docx(self.kerja, mapping, hasil)
        with zipfile.ZipFile(hasil) as archive:
            self.assertEqual(archive.read("word/styles.xml"), b"<styles/>")
            return etree.fromstring(archive.read("word/document.xml"))

    def test_sel_campuran_tidak_mengisi_spacer_atau_screenshot(self):
        body = (
            p("IV. Praktikum — Perulangan")
            + '<w:p><w:r><w:t>Lengkapi hasil </w:t></w:r>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t>latihan_01.c &amp; analisis.</w:t></w:r></w:p>'
            '<w:p w14:paraId="DEC0AB12"/><w:p><w:pPr/></w:p>'
            '<w:tbl><w:tr><w:tc>' + p("Input") + '</w:tc><w:tc>'
            + p("Expected") + '</w:tc><w:tc>' + p("Actual") + '</w:tc></w:tr>'
            '<w:tr><w:tc>' + p("5") + '</w:tc><w:tc><w:p w14:paraId="ABCD1234"/>'
            '<w:p/></w:tc><w:tc><w:p><w:pPr><w:jc w:val="right"/></w:pPr></w:p></w:tc></w:tr>'
            '<w:tr><w:tc>' + p("8") + '</w:tc><w:tc><w:p/></w:tc><w:tc><w:p/></w:tc></w:tr></w:tbl>'
            + p("Screenshot Output")
            + '<w:tbl><w:tr><w:tc>' + p("Tempelkan screenshot di area ini")
            + '<w:p/></w:tc></w:tr></w:tbl>'
            '<w:tbl><w:tr><w:tc><w:p><w:pPr/></w:p></w:tc></w:tr></w:tbl>'
            + p("....................")
        )
        mapping = self.petakan(body)
        self.assertEqual((self.kerja / "word/document.xml").read_bytes(), self.xml)
        cells = mapping["sel_kosong"]
        self.assertEqual(len(cells), 4)
        self.assertEqual(mapping["baris_titik"], [])
        self.assertIn("latihan_01.c & analisis.", cells[0]["soal"])
        self.assertIn("Kolom: Expected", cells[0]["soal"])
        self.assertIn("Baris 2: 5", cells[0]["soal"])
        self.assertIn("Kolom: Actual", cells[1]["soal"])
        answers = [r"C:\tmp\1 < 5 & \g<id>", "actual", "8 expected", "8 actual"]
        hasil = self.isi({"sel": {c["kunci"]: a for c, a in reversed(list(zip(cells, answers)))}})
        rows = hasil.findall(".//w:tbl[1]/w:tr", NS)
        self.assertEqual([teks(c) for c in rows[1]], ["5", *answers[:2]])
        self.assertEqual([teks(c) for c in rows[2]], ["8", *answers[2:]])
        self.assertEqual(hasil.findall(".//w:body/w:p[@w14:paraId]/w:r", {**NS, "w14": "http://schemas.microsoft.com/office/word/2010/wordml"}), [])
        self.assertEqual(teks(hasil.findall(".//w:tbl", NS)[1]), "Tempelkan screenshot di area ini")
        self.assertEqual(teks(hasil.findall(".//w:tbl", NS)[2]), "")
        self.assertIn("IV. Praktikum — Perulangan", teks(hasil))
        asli = etree.fromstring(self.xml)
        for tag in ("p", "tbl", "tr", "tc", "pPr", "rPr"):
            self.assertEqual(len(asli.findall(f".//w:{tag}", NS)), len(hasil.findall(f".//w:{tag}", NS)))
        self.assertEqual([etree.tostring(x) for x in asli.findall(".//w:pPr", NS)],
                         [etree.tostring(x) for x in hasil.findall(".//w:pPr", NS)])

    def test_titik_terpecah_satu_blok_dan_isian_parsial_aman(self):
        mapping = self.petakan(
            p("V. Tracing") + p("Apa hasil program?")
            + '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>.....</w:t></w:r>'
            '<w:r><w:rPr><w:i/></w:rPr><w:t>.........</w:t></w:r></w:p>'
            + p("................") + p("Apa sebabnya?") + p("................")
            + p("Input: ............ Output: ............")
        )
        dots = mapping["baris_titik"]
        self.assertEqual(len(dots), 4)
        self.assertIn("Apa hasil program?", dots[0]["soal"])
        self.assertTrue(dots[2]["soal"].endswith("Input:"))
        self.assertTrue(dots[3]["soal"].endswith("Output:"))
        answer = r'printf("%d\n", x); C:\temp\1 & x < 2'
        hasil = self.isi({"titik": {str(dots[0]["no"]): answer,
                                   str(dots[1]["no"]): "",
                                   str(dots[3]["no"]): "keluar",
                                   str(dots[2]["no"]): "masuk"}})
        ps = hasil.findall(".//w:body/w:p", NS)
        self.assertEqual([teks(x) for x in ps], ["V. Tracing", "Apa hasil program?", answer,
                                               "", "Apa sebabnya?", "................",
                                               "Input: masuk Output: keluar"])
        self.assertEqual(len(ps[2].findall("w:r", NS)), 2)
        self.assertIsNotNone(ps[2].find("w:r/w:rPr/w:b", NS))
        self.assertIsNotNone(ps[2].findall("w:r", NS)[1].find("w:rPr/w:i", NS))

    def test_placeholder_pseudocode_bukan_area_screenshot(self):
        mapping = self.petakan(
            p("VIII. Tugas Faktorial") + p("Tuliskan algoritma:")
            + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Tempelkan pseudocode atau </w:t></w:r>'
            '<w:r><w:t>flowchart di area ini</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        )
        cells = mapping["sel_kosong"]
        self.assertEqual(len(cells), 1)
        self.assertIn("Tugas Faktorial", cells[0]["soal"])
        self.assertTrue(cells[0]["wajib"])
        hasil = self.isi({"sel": {cells[0]["kunci"]: "n ← 5; ulangi hingga n ≤ 1"}})
        self.assertEqual(teks(hasil.find(".//w:tc", NS)), "n <- 5; ulangi hingga n <= 1")
        self.assertEqual(len(hasil.findall(".//w:p", NS)), 3)
        self.assertEqual(len(hasil.findall(".//w:tc/w:p/w:r", NS)), 2)

    def test_kunci_tidak_dikenal_tidak_merusak_dokumen(self):
        mapping = self.petakan(p("Jelaskan hasil:") + p("................"))
        with self.assertRaises(ValueError):
            self.isi({"titik": {str(mapping["baris_titik"][0]["no"]): "benar", "999": "salah"}})
        self.assertEqual((self.kerja / "word/document.xml").read_bytes(), self.xml)


if __name__ == "__main__":
    unittest.main()
