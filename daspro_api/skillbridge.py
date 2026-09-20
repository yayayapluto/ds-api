"""Penghubung ke skrip dan acuan gaya milik skill solve-daspro.

Skrip di folder skill itu satu-satunya sumber kebenaran untuk hal-hal
seperti pembuatan HTML copyable dan pengisian template docx. Modul ini
memuatnya langsung dari folder skill supaya tidak ada dua versi kode yang
harus dijaga bersamaan.
"""
import importlib.util
import sys
import threading
from pathlib import Path

from daspro_api.errors import InputTidakValid

KUNCI = threading.Lock()
_TERSIMPAN = {}


def _muat(nama: str, berkas: Path):
    """Muat satu berkas .py dari folder skill sebagai modul Python."""
    spec = importlib.util.spec_from_file_location(f"daspro_skill_{nama}", berkas)
    if spec is None or spec.loader is None:
        raise InputTidakValid(f"berkas skrip skill tidak bisa dimuat: {berkas}")
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


class Skill:
    """Akses ke folder skill: skrip dan berkas acuan gaya."""

    def __init__(self, folder: Path):
        self.folder = Path(folder).expanduser()
        self.scripts = self.folder / "scripts"
        self.references = self.folder / "references"

    # --- pemeriksaan -----------------------------------------------------
    def periksa(self) -> None:
        """Pastikan folder skill lengkap sebelum dipakai."""
        if not self.folder.is_dir():
            raise InputTidakValid(
                f"folder skill tidak ditemukan: {self.folder}. "
                "Setel DASPRO_SKILL_DIR ke folder solve-daspro."
            )
        wajib = [
            self.scripts / "md_to_copyable.py",
            self.scripts / "cek_bahasa.py",
            self.scripts / "isi_lkp_docx.py",
            self.references / "gaya-c.md",
            self.references / "gaya-bahasa.md",
            self.references / "format-laporan.md",
        ]
        hilang = [str(p) for p in wajib if not p.is_file()]
        if hilang:
            raise InputTidakValid("berkas skill kurang: " + ", ".join(hilang))

    @property
    def siap(self) -> bool:
        try:
            self.periksa()
            return True
        except InputTidakValid:
            return False

    # --- pemuatan modul --------------------------------------------------
    def modul(self, nama: str):
        """Ambil modul skrip skill (dimuat sekali, lalu disimpan)."""
        with KUNCI:
            if nama in _TERSIMPAN:
                return _TERSIMPAN[nama]
            self.periksa()
            modul = _muat(nama, self.scripts / f"{nama}.py")
            _TERSIMPAN[nama] = modul
            return modul

    # --- berkas acuan ----------------------------------------------------
    def baca_reference(self, nama: str) -> str:
        berkas = self.references / nama
        if not berkas.is_file():
            raise InputTidakValid(f"acuan gaya tidak ada: {berkas}")
        return berkas.read_text(encoding="utf-8")

    def acuan_gaya_c(self) -> str:
        return self.baca_reference("gaya-c.md")

    def acuan_gaya_bahasa(self) -> str:
        return self.baca_reference("gaya-bahasa.md")

    def acuan_format_laporan(self) -> str:
        return self.baca_reference("format-laporan.md")

    def contoh_laporan(self) -> str:
        berkas = self.references / "contoh_jawaban_LKP_Modul_4.md"
        return berkas.read_text(encoding="utf-8") if berkas.is_file() else ""

    def contoh_kode(self) -> list:
        """Kumpulan contoh .c dari skill, dipakai sebagai panutan gaya."""
        hasil = []
        for berkas in sorted(self.references.glob("contoh_*.c")):
            hasil.append({"nama": berkas.name, "isi": berkas.read_text(encoding="utf-8")})
        return hasil

    # --- pembungkus skrip ------------------------------------------------
    def md_ke_copyable(self, md_path: Path, html_path: Path) -> Path:
        """Ubah laporan MD jadi HTML copyable memakai skrip skill."""
        modul = self.modul("md_to_copyable")
        md_teks = Path(md_path).read_text(encoding="utf-8")
        isi = modul.convert(md_teks)
        import html as _html

        judul = _html.escape(Path(md_path).stem.replace("_", " "))
        dokumen = (
            "<!DOCTYPE html>\n<html lang=\"id\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{judul} - Copyable</title>\n<style>{modul.CSS}</style>\n</head>\n<body>\n"
            f'<div class="toolbar"><strong>{judul} - versi copyable</strong>'
            '<span style="font-size:.85rem;color:#555">Klik tombol copy di tiap sel / '
            "jawaban untuk salin teks bersih (tanpa tombol).</span></div>\n"
            f"{isi}\n<hr>\n"
            f'<p style="font-size:.85rem;color:#555">Sumber konten: '
            f"<code>{_html.escape(Path(md_path).name)}</code> (1:1, hanya dibungkus "
            "tombol salin).</p>\n"
            f'<div id="toast"></div>\n<script>{modul.JS}</script>\n</body>\n</html>'
        )
        html_path = Path(html_path)
        html_path.write_text(dokumen, encoding="utf-8")
        return html_path

    def cek_bahasa(self, berkas: list) -> dict:
        """Jalankan pemeriksa gaya bahasa dari skill pada beberapa berkas."""
        modul = self.modul("cek_bahasa")
        temuan = []
        for b in berkas:
            b = Path(b)
            if not b.is_file():
                continue
            temuan.extend(modul.scan(b))
        return {"lulus": not temuan, "jumlah": len(temuan), "temuan": temuan}

    def peta_docx(self, docx: Path, kerja: Path) -> dict:
        """Bongkar template docx dan susun peta tempat kosongnya."""
        modul = self.modul("isi_lkp_docx")
        kerja = Path(kerja)
        kerja.mkdir(parents=True, exist_ok=True)
        modul.buka_docx(Path(docx), kerja)
        modul.gabung_run(kerja)
        p = modul.peta(kerja)
        modul.peta_json(kerja, p)
        return p

    def isi_docx(self, kerja: Path, mapping: dict, hasil: Path) -> dict:
        """Isi template docx sesuai peta, lalu bungkus lagi jadi berkas utuh."""
        modul = self.modul("isi_lkp_docx")
        kerja = Path(kerja)
        berkas_xml = kerja / modul.DOC
        sebelum = modul.hitung_paragraf(berkas_xml.read_text(encoding="utf-8"))
        modul.isi(kerja, mapping)
        sisa = modul.buang_non_keyboard(kerja)
        sesudah = modul.hitung_paragraf(berkas_xml.read_text(encoding="utf-8"))
        modul.bungkus(kerja, Path(hasil))
        return {
            "sel_diisi": len(mapping.get("sel", {})),
            "baris_diisi": len(mapping.get("titik", {})),
            "karakter_dibuang": {k: v for k, v in (sisa or {}).items()},
            "paragraf_sebelum": sebelum,
            "paragraf_sesudah": sesudah,
            "struktur_utuh": sebelum == sesudah,
        }
