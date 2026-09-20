"""Mengompilasi dan menjalankan kode C dengan aman.

Semua program dijalankan sebagai proses terpisah dengan batas waktu, batas
memori, dan tanpa akses jaringan. Jadi kode dari AI tidak bisa mengunci
komputer atau memakan seluruh memori.
"""
import os
import resource
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .config import Pengaturan
from .errors import GccTidakAda


@dataclass
class HasilKompilasi:
    ok: bool
    peringatan: list = field(default_factory=list)
    pesan_error: str = ""
    berkas_biner: str = ""
    perintah: str = ""


@dataclass
class HasilJalan:
    kode_keluar: int
    keluaran: str
    pesan_error: str
    timeout: bool
    masukan: str = ""
    perintah: str = ""


def _batasi(memori_mb: int):
    """Fungsi yang dipanggil di proses anak sebelum program dijalankan."""
    batas = memori_mb * 1024 * 1024

    def pasang():
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        try:
            resource.setrlimit(resource.RLIMIT_AS, (batas, batas))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        except (ValueError, OSError):
            pass
        os.setsid()

    return pasang


class KompilatorC:
    """Pembungkus gcc: mengompilasi, menjalankan, dan mengukur hasilnya."""

    def __init__(self, pengaturan: Pengaturan):
        self.p = pengaturan

    def periksa_gcc(self) -> str:
        jalur = shutil.which(self.p.gcc)
        if not jalur:
            raise GccTidakAda(
                f"program '{self.p.gcc}' tidak ada di komputer ini. "
                "Pasang gcc dulu sebelum memakai layanan ini."
            )
        return jalur

    def kompilasi(self, berkas_c: Path, keluaran: Path) -> HasilKompilasi:
        gcc = self.periksa_gcc()
        perintah = [
            gcc,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-O0",
            "-o",
            str(keluaran),
            str(berkas_c),
        ]
        try:
            hasil = subprocess.run(
                perintah,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path(berkas_c).parent),
            )
        except subprocess.TimeoutExpired:
            return HasilKompilasi(
                ok=False,
                pesan_error="gcc berjalan lebih dari 60 detik lalu dihentikan",
                perintah=" ".join(perintah),
            )
        kecuali = (hasil.stderr or "").strip()
        baris_peringatan = [
            b for b in kecuali.splitlines() if ": warning:" in b or "warning:" in b
        ]
        berhasil = hasil.returncode == 0 and Path(keluaran).is_file()
        return HasilKompilasi(
            ok=berhasil,
            peringatan=baris_peringatan,
            pesan_error="" if berhasil else kecuali,
            berkas_biner=str(keluaran) if berhasil else "",
            perintah=" ".join(perintah),
        )

    def jalan(self, biner: Path, masukan: str = "", timeout=None) -> HasilJalan:
        batas = self.p.run_timeout if timeout is None else timeout
        perintah = [str(biner)]
        try:
            hasil = subprocess.run(
                perintah,
                input=masukan,
                capture_output=True,
                text=True,
                timeout=batas,
                preexec_fn=_batasi(self.p.memory_mb),
                cwd=tempfile.gettempdir(),
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
        except subprocess.TimeoutExpired:
            return HasilJalan(
                kode_keluar=124,
                keluaran="",
                pesan_error="program dihentikan karena berjalan terlalu lama",
                timeout=True,
                masukan=masukan,
                perintah=" ".join(perintah),
            )
        return HasilJalan(
            kode_keluar=hasil.returncode,
            keluaran=hasil.stdout or "",
            pesan_error=hasil.stderr or "",
            timeout=False,
            masukan=masukan,
            perintah=" ".join(perintah),
        )

    def kompilasi_dan_jalan(self, berkas_c: Path, masukan: str = "", timeout=None):
        """Sekali pakai: kompilasi ke folder sementara, lalu jalankan."""
        berkas_c = Path(berkas_c)
        with tempfile.TemporaryDirectory(prefix="daspro_run_") as tmp:
            biner = Path(tmp) / berkas_c.stem
            kompil = self.kompilasi(berkas_c, biner)
            if not kompil.ok:
                return kompil, None
            jalan = self.jalan(biner, masukan=masukan, timeout=timeout)
            return kompil, jalan
