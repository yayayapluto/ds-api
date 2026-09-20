#!/usr/bin/env python3
"""Pembuat berkas contoh untuk pengujian.

Menghasilkan tiga berkas di tests/fixtures:
    modul_contoh.pdf        modul praktikum sederhana
    lkp_contoh.docx         template LKP dengan sel kosong dan baris titik-titik
    jawaban_contoh.md       laporan contoh untuk menguji pemeriksa bahasa

Semua dibuat dari nol memakai pustaka bawaan Python supaya pengujian bisa
jalan tanpa memasang apa pun.
"""
import pathlib
import zipfile

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

# --- PDF sederhana --------------------------------------------------------
BARIS_MODUL = [
    "MODUL PRAKTIKUM 5 - PERULANGAN",
    "",
    "IV.1 Praktikum Terbimbing 1 - Deret Bilangan",
    "Buat program latihan_01.c yang membaca satu bilangan bulat n.",
    "Program mencetak angka 1 sampai n, satu angka tiap baris.",
    "Kalau n kurang dari 1, program mencetak pesan tidak valid dan berhenti.",
    "Nilai batas: 1, 5, 10, dan 0.",
    "",
    "IV.2 Praktikum Terbimbing 2 - Rata-rata Nilai",
    "Buat program latihan_02.c yang membaca banyak data nilai lalu",
    "mencetak rata-ratanya dua angka di belakang koma.",
    "Kalau banyak data nol atau negatif, program mencetak pesan tidak valid.",
    "",
    "V.1 Tugas Praktikum - Tabel Perkalian",
    "Buat program tugas_modul_05.c yang mencetak tabel perkalian n.",
    "Nilai n harus antara 1 sampai 10.",
]


def _pdf_escape(teks: str) -> str:
    return teks.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def buat_pdf(tujuan: pathlib.Path) -> None:
    isi = ["BT", "/F1 11 Tf", "14 TL", "50 760 Td"]
    for baris in BARIS_MODUL:
        isi.append(f"({_pdf_escape(baris)}) Tj")
        isi.append("T*")
    isi.append("ET")
    aliran = "\n".join(isi).encode("latin-1", "replace")

    objek = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(aliran)).encode() + b" >>\nstream\n" + aliran + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    keluaran = bytearray(b"%PDF-1.4\n")
    offset = []
    for i, isi_objek in enumerate(objek, 1):
        offset.append(len(keluaran))
        keluaran += f"{i} 0 obj\n".encode() + isi_objek + b"\nendobj\n"
    xref = len(keluaran)
    keluaran += f"xref\n0 {len(objek) + 1}\n".encode()
    keluaran += b"0000000000 65535 f \n"
    for off in offset:
        keluaran += f"{off:010d} 00000 n \n".encode()
    keluaran += (
        f"trailer\n<< /Size {len(objek) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    tujuan.write_bytes(bytes(keluaran))


# --- docx sederhana -------------------------------------------------------
CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""


def _p(teks: str = "", para_id: str = "", kosong: bool = False) -> str:
    """Satu paragraf Word. Kalau kosong, tulis sebagai paragraf tanpa isi."""
    atribut = f' w14:paraId="{para_id}" w14:textId="77777777"' if para_id else ""
    if kosong:
        return f"<w:p{atribut}/>"
    if not teks:
        return f"<w:p{atribut}/>"
    return (
        f"<w:p{atribut}><w:r><w:t xml:space=\"preserve\">{teks}</w:t></w:r></w:p>"
    )


def buat_docx(tujuan: pathlib.Path) -> None:
    baris = [
        _p("LKP Modul 5 - Perulangan"),
        _p("Nama: ......................   NIM: ......................"),
        _p("Kelas: ......................"),
        _p(""),
        _p("IV.1 Praktikum Terbimbing 1 - Deret Bilangan"),
        _p("Tuliskan hasil pengujian program latihan_01.c"),
        # tabel: baris pertama punya sel kosong ber-paraId
        "<w:tbl><w:tr>"
        + f'<w:tc><w:p w14:paraId="1A2B3C4D" w14:textId="11111111"/></w:tc>'
        + f'<w:tc><w:p w14:paraId="1A2B3C4E" w14:textId="11111112"/></w:tc>'
        + "</w:tr></w:tbl>",
        _p("Kesimpulan:"),
        _p("................................................................"),
        _p("V.1 Tugas Praktikum - Tabel Perkalian"),
        _p("Jelaskan cara kerja program:"),
        _p("................................................................"),
        _p("Pernyataan:"),
        _p("................................................................"),
    ]
    dokumen = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
        "<w:body>" + "".join(baris) + "</w:body></w:document>"
    )
    with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", dokumen)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)


def buat_md(tujuan: pathlib.Path) -> None:
    tujuan.write_text(
        "# Jawaban LKP Modul 5\n\n"
        "> Nama: - - NIM: - / Kelas: -\n\n"
        "## IV.1 Deret Bilangan (`latihan_01.c`)\n\n"
        "| Masukan | Expected Output | Actual Output | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| 5 | angka 1 sampai 5 | `1\\n2\\n3\\n4\\n5` | Sesuai |\n\n"
        "### Pertanyaan analisis\n\n"
        "1. **Mengapa nilai nol harus ditolak?**\n"
        "  Karena perulangan dari 1 sampai 0 tidak pernah berjalan, jadi tidak "
        "ada angka yang tercetak.\n",
        encoding="utf-8",
    )


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    buat_pdf(FIXTURES / "modul_contoh.pdf")
    buat_docx(FIXTURES / "lkp_contoh.docx")
    buat_md(FIXTURES / "jawaban_contoh.md")
    for f in sorted(FIXTURES.iterdir()):
        print(f"{f.name}  {f.stat().st_size} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
