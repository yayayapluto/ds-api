#!/usr/bin/env python3
"""isi_lkp_docx.py - isi template LKP .docx dari jawaban, tanpa ubah format.

Pakai:
  python3 isi_lkp_docx.py peta template.docx [dir_kerja]
      Buka docx tanpa mengubah XML, lalu cetak peta sel tabel kosong dan
      blok jawaban bertitik beserta konteks soal, baris, dan kolom tabel.

  python3 isi_lkp_docx.py isi dir_kerja mapping.json hasil.docx
      Terapkan jawaban yang diberikan, pertahankan isian yang belum dipetakan,
      lalu bungkus ulang. Hanya teks jawaban baru yang dinormalkan ke keyboard.

Bentuk mapping.json:
  {
    "sel": {"1A2B3C4D": "jawaban untuk sel tabel kosong"},
    "titik": {"1": "jawaban blok pertama"}
  }

Kenapa tanpa Word/soffice: skrip ini mengedit XML aslinya langsung, jadi
font, warna, border, dan nomor halaman dari template tidak pernah hilang.
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import lxml.etree as etree  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Paket lxml belum terpasang. Jalankan: pip install lxml"
    )

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
DOC = "word/document.xml"


def buka_docx(docx: Path, kerja: Path) -> None:
    """Bongkar docx ke folder kerja (dokumen luar = tidak dipercaya)."""
    if kerja.exists():
        shutil.rmtree(kerja)
    kerja.mkdir(parents=True)
    with zipfile.ZipFile(docx) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename)
            if name.is_absolute() or ".." in name.parts:
                continue  # tolak path aneh di dalam zip
            target = kerja / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))


W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
DOTS = re.compile(r"\.{10,}")
MANUAL = re.compile(r"screenshot|tangkapan layar|(?:tempelkan|lampirkan|sisipkan|paste|attach).*(?:gambar|foto|image)", re.I)
PROMPT = re.compile(r"\?|:|tuliskan|jelaskan|lengkapi|isikan|jawab|hasil|kesimpulan|pernyataan", re.I)
PLACEHOLDER = re.compile(r"(?:tempelkan|tuliskan|isikan|masukkan)\s+(?:pseudocode|flowchart|kode|jawaban)\b.*", re.I)


def _teks(node) -> str:
    return "".join(t.text or "" for t in node.iter(f"{{{W}}}t"))


def _peta(tree):
    """Satu penelusuran untuk metadata publik dan lokasi XML pengisian."""
    kosong, baris = [], []
    lokasi = {"sel": {}, "titik": {}}
    bagian, konteks = {}, []
    paragraf = list(tree.iter(f"{{{W}}}p"))
    pid_count = {}
    for p in paragraf:
        pid = p.get(f"{{{W14}}}paraId")
        if pid:
            pid_count[pid] = pid_count.get(pid, 0) + 1

    def soal(tambahan=()):
        return "\n".join(dict.fromkeys(
            [*bagian.values(), *konteks[-3:], *tambahan]
        ))

    def titik(p, tambahan, sebelumnya):
        teks = _teks(p)
        cocok = list(DOTS.finditer(teks))
        label = DOTS.sub("", teks).strip()
        if not cocok or MANUAL.search(teks):
            return None
        if not tambahan and not label and konteks and MANUAL.search(konteks[-1]):
            return None
        konteks_soal = soal([*tambahan, label] if label else tambahan)
        if not konteks_soal:
            return None
        lanjutan = sebelumnya if not label and len(cocok) == 1 else None
        for m in cocok:
            bagian_teks, offset = [], 0
            for t in p.iter(f"{{{W}}}t"):
                akhir = offset + len(t.text or "")
                if offset < m.end() and akhir > m.start():
                    bagian_teks.append((t, max(0, m.start() - offset), min(akhir, m.end()) - offset))
                offset = akhir
            if lanjutan is not None:
                lokasi["titik"][lanjutan].append(bagian_teks)
            else:
                no = len(baris) + 1
                label_isian = teks[:m.start()].rsplit(".", 1)[-1].strip() if label else ""
                baris.append({"no": no, "soal": soal([*tambahan, label_isian]) if label_isian else konteks_soal,
                              "wajib": True})
                lokasi["titik"][str(no)] = [bagian_teks]
                lanjutan = str(no) if not label and len(cocok) == 1 else None
        return lanjutan

    def tabel(tbl):
        rows = tbl.findall(f"{{{W}}}tr")
        if not rows:
            return
        teks_tabel = _teks(tbl).strip()
        # ponytail: kotak tanpa label perlu petunjuk soal; template khusus perlu penanda eksplisit.
        if not teks_tabel and (not konteks or MANUAL.search(konteks[-1]) or not PROMPT.search(konteks[-1])):
            return
        header = rows[0].findall(f"{{{W}}}tc")
        ada_header = len(rows) > 1 and len(header) > 1 and all(_teks(c).strip() for c in header)
        kolom, index = {}, 0
        if ada_header:
            for c in header:
                span = c.find("w:tcPr/w:gridSpan", NS)
                lebar = int(span.get(f"{{{W}}}val", "1")) if span is not None else 1
                for k in range(index, index + lebar):
                    kolom[k] = _teks(c).strip()
                index += lebar
        for nr, row in enumerate(rows, 1):
            cells = row.findall(f"{{{W}}}tc")
            nilai = [_teks(c).strip() for c in cells]
            isi_baris = " | ".join(v for v in nilai if v)
            before = row.find("w:trPr/w:gridBefore", NS)
            index = int(before.get(f"{{{W}}}val", "0")) if before is not None else 0
            for c, teks in zip(cells, nilai):
                nama_kolom = kolom.get(index, "") or str(index + 1)
                tambahan = [f"Baris {nr}: {isi_baris}", f"Kolom: {nama_kolom}"]
                span = c.find("w:tcPr/w:gridSpan", NS)
                index += int(span.get(f"{{{W}}}val", "1")) if span is not None else 1
                if MANUAL.search(teks) or MANUAL.search(nama_kolom) or MANUAL.search(isi_baris):
                    continue
                ps = c.findall(f"{{{W}}}p")
                merge = c.find("w:tcPr/w:vMerge", NS)
                if merge is not None and merge.get(f"{{{W}}}val") != "restart":
                    continue
                konten = c.xpath(".//w:drawing | .//w:pict | .//w:object | .//w:tbl | .//w:sym | .//w:fldChar", namespaces=NS)
                placeholder = next((p for p in ps if PLACEHOLDER.fullmatch(_teks(p).strip())), None)
                if (not teks or placeholder is not None) and ps and not konten and not (ada_header and nr == 1):
                    p = next((p for p in ps if not _teks(p).strip()), None)
                    if p is None:
                        p = placeholder if placeholder is not None else ps[0]
                    pid = p.get(f"{{{W14}}}paraId")
                    nomor = len(kosong) + 1
                    kunci = pid if pid and pid_count[pid] == 1 else f"sel{nomor}"
                    kosong.append({"kunci": kunci, "paraId": pid, "nomor": nomor,
                                   "soal": soal(tambahan), "wajib": True})
                    lokasi["sel"][kunci] = (p, p is placeholder)
                lanjut = None
                for p in ps:
                    label = _teks(p).strip()
                    if label and not DOTS.search(label):
                        tambahan = [*tambahan[:2], label]
                    lanjut = titik(p, tambahan, lanjut)
                for nested in c.findall(f"{{{W}}}tbl"):
                    tabel(nested)

    def telusuri(parent):
        lanjut = None
        for node in parent:
            if node.tag == f"{{{W}}}tbl":
                tabel(node)
                lanjut = None
            elif node.tag == f"{{{W}}}p":
                teks = _teks(node).strip()
                if DOTS.search(teks):
                    lanjut = titik(node, (), lanjut)
                    continue
                lanjut = None
                if not teks:
                    continue
                style = node.find("w:pPr/w:pStyle", NS)
                nama = style.get(f"{{{W}}}val", "") if style is not None else ""
                heading = re.fullmatch(r"(?:Heading|Judul)([1-9])", nama, re.I)
                if heading or re.match(r"^[IVX]+(?:\.\d+)?\.?(?:\s|$)", teks):
                    level = int(heading.group(1)) if heading else 1
                    for key in list(bagian):
                        if key >= level:
                            del bagian[key]
                    bagian[level] = teks
                    konteks.clear()
                else:
                    konteks.append(teks)
            else:
                telusuri(node)
    telusuri(tree.getroot().find("w:body", NS))
    return {"sel_kosong": kosong, "baris_titik": baris}, lokasi


def peta(kerja: Path) -> dict:
    """Petakan sel tabel kosong dan blok titik; spacer dan area gambar diabaikan."""
    tree = etree.parse(str(kerja / DOC), etree.XMLParser(resolve_entities=False))
    return _peta(tree)[0]


def peta_json(kerja: Path, p: dict) -> Path:
    """Simpan peta sebagai JSON, dipakai untuk menyusun mapping."""
    out = kerja / "peta.json"
    out.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def isi(kerja: Path, mapping: dict) -> None:
    """Isi lokasi hasil peta sekali, tanpa menghapus isian yang tidak diberikan."""
    path = kerja / DOC
    tree = etree.parse(str(path), etree.XMLParser(resolve_entities=False))
    _, lokasi = _peta(tree)
    jawaban = []
    for jenis in ("sel", "titik"):
        for key, nilai in mapping.get(jenis, {}).items():
            kunci = str(key)
            if kunci not in lokasi[jenis]:
                raise ValueError(f"Kunci {jenis} tidak ada pada peta: {kunci}")
            if not isinstance(nilai, str):
                raise ValueError(f"Jawaban {jenis} {kunci} harus berupa teks")
            if nilai.strip():
                teks = "".join(GANTI.get(ch, ch if ord(ch) < 128 else "?") for ch in nilai)
                jawaban.append((jenis, lokasi[jenis][kunci], teks))
    if not jawaban:
        return
    ganti_teks = {}
    for jenis, target, teks in jawaban:
        if jenis == "sel":
            p, placeholder = target
            texts = list(p.iter(f"{{{W}}}t"))
            t = texts[0] if texts else None
            if placeholder:
                for other in texts[1:]:
                    other.text = ""
            if t is None:
                r = etree.SubElement(p, f"{{{W}}}r")
                t = etree.SubElement(r, f"{{{W}}}t")
            t.text = teks
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        else:
            pertama = True
            for blok in target:
                for t, start, end in blok:
                    ganti_teks.setdefault(t, []).append((start, end, teks if pertama else ""))
                    pertama = False
    # Offset berasal dari teks asli; beberapa isian boleh berada dalam run yang sama.
    for t, edits in ganti_teks.items():
        nilai = t.text or ""
        for start, end, teks in sorted(edits, reverse=True):
            nilai = nilai[:start] + teks + nilai[end:]
        t.text = nilai
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    tree.write(str(path), xml_declaration=True, encoding="UTF-8", standalone=True)


GANTI = {
    "\u2014": "-", "\u2013": "-", "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'", "\u2026": "...", "\u2022": "-",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u00d7": "x",
    "\u00f7": "/", "\u2212": "-", "\u2265": ">=", "\u2264": "<=",
    "\u2260": "!=", "\u00a0": " ", "\u2009": " ", "\u202f": " ",
    "\u00b0": " derajat",
}


def hitung_paragraf(teks_xml: str) -> int:
    return len(re.findall(r"<w:p[\s>/]", teks_xml))


def bungkus(kerja: Path, hasil: Path) -> None:
    if hasil.exists():
        hasil.unlink()
    with zipfile.ZipFile(hasil, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(kerja.rglob("*")):
            if not f.is_file() or f.suffix == ".json":
                continue  # peta.json cuma alat bantu, bukan bagian dokumen; _rels/.rels wajib ikut
            z.write(f, f.relative_to(kerja).as_posix())


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    op = sys.argv[1]

    if op == "peta":
        docx = Path(sys.argv[2])
        kerja = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("unpacked")
        asli = zipfile.ZipFile(docx).read(DOC).decode("utf-8")
        buka_docx(docx, kerja)
        p = peta(kerja)
        pj = peta_json(kerja, p)
        print(f"# Peta {docx} (folder kerja: {kerja})")
        print(f"# jumlah paragraf asli: {hitung_paragraf(asli)}")
        print(f"# sel kosong: {len(p['sel_kosong'])}, baris titik: {len(p['baris_titik'])}")
        print(f"# peta lengkap: {pj}")
        print("\n## Sel kosong (kunci mapping)")
        for s in p["sel_kosong"]:
            print(f"  {s['kunci']}  <- soal: {s['soal'][:70]}")
        print("\n## Baris titik-titik")
        for s in p["baris_titik"]:
            print(f"  {s['no']}. setelah soal: {s['soal'][:70]}")
        return 0

    if op == "isi":
        if len(sys.argv) < 5:
            print(__doc__)
            return 2
        kerja = Path(sys.argv[2])
        mapping = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        hasil = Path(sys.argv[4])
        sebelum = hitung_paragraf((kerja / DOC).read_text(encoding="utf-8"))
        isi(kerja, mapping)
        sesudah = hitung_paragraf((kerja / DOC).read_text(encoding="utf-8"))
        bungkus(kerja, hasil)
        print(f"sel diisi: {len(mapping.get('sel', {}))}")
        print(f"baris titik diisi: {len(mapping.get('titik', []))}")
        print(f"paragraf: {sebelum} -> {sesudah}", end=" ")
        if sebelum == sesudah:
            print("(SAMA, struktur utuh)")
        else:
            print("(BEDA, ada struktur yang berubah)")
            return 1
        print(f"hasil: {hasil} ({hasil.stat().st_size / 1024:.1f}KB)")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
