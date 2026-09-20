#!/usr/bin/env python3
"""isi_lkp_docx.py - isi template LKP .docx dari jawaban, tanpa ubah format.

Pakai:
  python3 isi_lkp_docx.py peta template.docx [dir_kerja]
      Buka docx, gabung run yang terpecah, simpan hasil buka ke dir_kerja,
      lalu cetak peta semua tempat kosong (paraId) dan semua baris titik-titik
      beserta teks soal yang mendahuluinya. Peta ini dipakai untuk menyusun
      mapping di langkah berikutnya.

  python3 isi_lkp_docx.py isi dir_kerja mapping.json hasil.docx
      Terapkan mapping, hapus sisa titik-titik, buang karakter di luar
      keyboard, bungkus ulang jadi docx, lalu bandingkan jumlah paragraf
      dengan aslinya.

Bentuk mapping.json:
  {
    "sel": {"1A2B3C4D": "jawaban untuk sel tabel kosong"},
    "titik": [["teks soal unik", "jawaban baris pertama"], ...]
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

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
DOC = "word/document.xml"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def gabung_run(kerja: Path) -> None:
    """Gabung <w:r> bersebelahan yang gaya teksnya sama.

    Word memecah satu kalimat jadi banyak <w:r> kecil. Tanpa digabung, teks
    soal yang terlihat utuh di dokumen tidak ada sebagai satu string di XML,
    sehingga pencarian soal tidak ketemu.
    """
    path = kerja / DOC
    tree = etree.parse(str(path))
    for p in tree.iter(f"{{{W}}}p"):
        runs = [c for c in list(p) if c.tag == f"{{{W}}}r"]
        i = 0
        while i < len(runs) - 1:
            a, b = runs[i], runs[i + 1]
            ra, rb = a.find(f"{{{W}}}rPr"), b.find(f"{{{W}}}rPr")
            sama = (ra is None and rb is None) or (
                ra is not None and rb is not None
                and etree.tostring(ra) == etree.tostring(rb)
            )
            if not sama:
                i += 1
                continue
            ta = a.find(f"{{{W}}}t")
            tb = b.find(f"{{{W}}}t")
            if ta is not None and tb is not None:
                ta.text = (ta.text or "") + (tb.text or "")
                p.remove(b)
                runs.pop(i + 1)
                continue
            i += 1
    tree.write(str(path), xml_declaration=True, encoding="UTF-8", standalone=True)


TOKEN = re.compile(
    r"<w:t(?:\s[^>]*)?>(.*?)</w:t>"
    r"|<w:p(?P<attrs>(?:\s[^>]*?)?)/>",
    re.S,
)


def peta(kerja: Path) -> dict:
    """Kumpulkan semua sel kosong (paraId) dan semua baris titik-titik.

    Ditelusuri berurutan, bukan per blok paragraf: kalau polanya menelan
    satu paragraf utuh, teks di dalamnya tidak pernah terbaca.
    """
    data = (kerja / DOC).read_text(encoding="utf-8")
    kosong, baris = [], []
    soal_raw = ""
    for m in TOKEN.finditer(data):
        teks = m.group(1)
        if teks is None:  # paragraf kosong self-closing = sel tabel kosong
            attrs = m.group("attrs") or ""
            pid = re.search(r'w14:paraId="([0-9A-Fa-f]+)"', attrs)
            kosong.append({
                # Dokumen buatan Word punya w14:paraId per paragraf, itu kunci
                # paling aman. Kalau tidak ada, pakai nomor urut sel kosong.
                "kunci": pid.group(1) if pid else f"sel{len(kosong) + 1}",
                "paraId": pid.group(1) if pid else None,
                "nomor": len(kosong) + 1,
                "soal": soal_raw,
            })
            continue
        isi_teks = teks.strip()
        if len(isi_teks) >= 10 and set(isi_teks) == {"."}:
            baris.append({"no": len(baris) + 1, "soal": soal_raw})
        elif isi_teks:
            soal_raw = isi_teks
    return {"sel_kosong": kosong, "baris_titik": baris}


def peta_json(kerja: Path, p: dict) -> Path:
    """Simpan peta sebagai JSON, dipakai untuk menyusun mapping."""
    out = kerja / "peta.json"
    out.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def isi(kerja: Path, mapping: dict) -> None:
    path = kerja / DOC
    data = path.read_text(encoding="utf-8")

    # Sel kosong. Kunci dari peta.json ("sel_kosong"[i]["kunci"]):
    #   - paraId heksa -> dicari lewat paraId, tidak mungkin salah pasang
    #   - "selN"       -> sel kosong ke-N, tanpa paraId (dokumen lama)
    sel = mapping.get("sel", {})
    for kunci, val in sel.items():
        if not re.fullmatch(r"[0-9A-Fa-f]{6,}", kunci):
            continue
        pola = re.compile(r'(<w:p [^>]*w14:paraId="' + kunci + r'"[^>]*)/>')
        data, jml = pola.subn(
            r'\1><w:r><w:t xml:space="preserve">' + esc(val) + r"</w:t></w:r></w:p>",
            data,
        )
        assert jml == 1, f"paraId {kunci} tidak ketemu atau dobel: {jml}"

    # Nomor urut diproses dari yang paling belakang: tiap pengisian mengubah
    # panjang XML, jadi offset sel berikutnya baru tetap valid kalau kita
    # bergerak dari belakang ke depan.
    nomor_sel = sorted(
        (int(k.removeprefix("sel")), v)
        for k, v in sel.items()
        if not re.fullmatch(r"[0-9A-Fa-f]{6,}", k)
    )
    for n, val in reversed(nomor_sel):
        # <w:p/> tanpa spasi dan <w:p .../> dua-duanya berarti sel kosong
        pola = re.compile(r"<w:p((?:\s[^>]*?)?)/>")
        cocok = list(pola.finditer(data))
        assert len(cocok) >= n, f"sel kosong ke-{n} tidak ada (sisa {len(cocok)})"
        m = cocok[n - 1]
        data = (data[: m.start()] + f"<w:p{m.group(1) or ''}>"
                + '<w:r><w:t xml:space="preserve">' + esc(val)
                + "</w:t></w:r></w:p>" + data[m.end():])

    # Baris titik-titik: kunci = nomor urut dari peta.json.
    dots = re.compile(r'<w:t[^>]*>\.{10,}</w:t>')
    baris = sorted(((int(k), v) for k, v in mapping.get("titik", {}).items()),
                   reverse=True)
    for n, jawab in baris:
        lokasi = list(dots.finditer(data))
        assert 1 <= n <= len(lokasi), f"baris titik ke-{n} tidak ada (total {len(lokasi)})"
        m = lokasi[n - 1]
        data = (data[: m.start()]
                + '<w:t xml:space="preserve">' + esc(jawab) + "</w:t>"
                + data[m.end():])

    # sisa baris titik-titik yang belum terpakai dikosongkan, bukan dibiarkan
    data = re.sub(r'<w:t[^>]*>\.{10,}</w:t>', "<w:t></w:t>", data)

    path.write_text(data, encoding="utf-8")


GANTI = {
    "\u2014": "-", "\u2013": "-", "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'", "\u2026": "...", "\u2022": "-",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u00d7": "x",
    "\u00f7": "/", "\u2212": "-", "\u2265": ">=", "\u2264": "<=",
    "\u2260": "!=", "\u00a0": " ", "\u2009": " ", "\u202f": " ",
    "\u00b0": " derajat",
}


def buang_non_keyboard(kerja: Path) -> dict:
    """Ganti karakter di luar keyboard di semua teks dokumen."""
    path = kerja / DOC
    data = path.read_text(encoding="utf-8")
    dipakai = {}
    for m in re.finditer(r"<w:t[^>]*>(.*?)</w:t>", data, re.S):
        for ch in m.group(1):
            if ord(ch) > 127:
                dipakai[ch] = dipakai.get(ch, 0) + 1
    for ch in dipakai:
        data = data.replace(ch, GANTI.get(ch, "?"))
    path.write_text(data, encoding="utf-8")
    return dipakai


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
        gabung_run(kerja)
        p = peta(kerja)
        pj = peta_json(kerja, p)
        print(f"# Peta {docx} (folder kerja: {kerja})")
        print(f"# jumlah paragraf asli: {hitung_paragraf(asli)}")
        print(f"# sel kosong: {len(p['sel_kosong'])}, baris titik: {len(p['baris_titik'])}")
        print(f"# peta lengkap: {pj}")
        print("\n## Sel kosong (kunci: paraId)")
        for s in p["sel_kosong"]:
            print(f"  {s['paraId']}  <- soal: {s['soal'][:70]}")
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
        sisa = buang_non_keyboard(kerja)
        sesudah = hitung_paragraf((kerja / DOC).read_text(encoding="utf-8"))
        bungkus(kerja, hasil)
        print(f"sel diisi: {len(mapping.get('sel', {}))}")
        print(f"baris titik diisi: {len(mapping.get('titik', []))}")
        print(f"karakter non-keyboard dibuang: {sisa or 'tidak ada'}")
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
