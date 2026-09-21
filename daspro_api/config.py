"""Pengaturan layanan, dibaca dari variabel lingkungan.

Semua nama variabel diawali DASPRO_. Tidak ada nilai rahasia yang ditulis
di dalam kode, jadi berkas ini aman ikut masuk repo.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

# Folder bawaan tempat berkas kerja disimpan, sebelah folder paket ini.
FOLDER_BAWAAN = Path(__file__).resolve().parent.parent / "data"

# Salinan skill yang ikut di dalam repo. Dipakai lebih dulu supaya layanan
# ini tidak bergantung pada folder di luar repo.
SKILL_VENDOR = Path(__file__).resolve().parent.parent / "skill"

# Salinan skill milik pengguna, dipakai kalau salinan di repo tidak ada.
SKILL_PENGGUNA = Path.home() / ".agents" / "skills" / "solve-daspro"


def folder_skill_bawaan() -> Path:
    """Pilih folder skill: salinan di repo dulu, baru milik pengguna."""
    if (SKILL_VENDOR / "scripts").is_dir():
        return SKILL_VENDOR
    return SKILL_PENGGUNA


def _ke_bool(teks: str, bawaan: bool = False) -> bool:
    if teks is None:
        return bawaan
    return teks.strip().lower() in {"1", "true", "ya", "yes", "on"}


def _ke_int(teks, bawaan: int) -> int:
    try:
        return int(str(teks).strip())
    except (TypeError, ValueError):
        return bawaan


def _ke_float(teks, bawaan: float) -> float:
    try:
        return float(str(teks).strip())
    except (TypeError, ValueError):
        return bawaan


@dataclass
class Pengaturan:
    """Isi pengaturan yang dipakai server dan pipeline."""

    host: str = "127.0.0.1"
    port: int = 8787
    # Berapa port berurutan yang dicoba kalau port di atas sudah dipakai.
    port_fallback: int = 10
    data_dir: Path = field(default_factory=lambda: FOLDER_BAWAAN)
    skill_dir: Path = field(default_factory=folder_skill_bawaan)

    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_timeout: int = 300
    # Model penalaran memakai sebagian jatah token untuk berpikir, jadi
    # jatahnya perlu lega supaya jawaban tidak terpotong di tengah.
    ai_max_tokens: int = 32768
    ai_temperature: float = 0.2

    gcc: str = "gcc"
    run_timeout: int = 5
    memory_mb: int = 256
    compile_warning_max: int = 0

    max_upload_mb: int = 32
    max_repair: int = 2
    job_workers: int = 2
    job_ttl_jam: int = 24
    auth_token: str = ""
    public_base_url: str = ""

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).expanduser()
        self.skill_dir = Path(self.skill_dir).expanduser()

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def ai_siap(self) -> bool:
        """True kalau layanan AI sudah bisa dipanggil.

        Kunci dan alamat wajib ada. Tidak ada mode jawaban tiruan, supaya
        kode C yang dihasilkan selalu datang dari model sungguhan.
        """
        return bool(self.ai_api_key and self.ai_base_url and self.ai_model)

    @property
    def max_upload_bytes(self) -> int:
        return max(1, self.max_upload_mb) * 1024 * 1024

    def ai_ringkas(self) -> dict:
        """Keterangan layanan AI yang aman ditampilkan.

        Kunci API tidak pernah ikut. Yang dikirim hanya keterangan apakah
        kunci sudah terisi, supaya halaman web bisa memberi tahu pengguna
        tanpa membocorkan isinya.
        """
        return {
            "base_url": self.ai_base_url,
            "model": self.ai_model,
            "kunci_terisi": bool(self.ai_api_key),
            "siap": self.ai_siap,
            "timeout": self.ai_timeout,
        }

    def dengan(self, **ubah) -> "Pengaturan":
        """Salinan pengaturan dengan beberapa nilai diganti.

        Dipakai untuk menyisipkan kredensial yang dikirim pengguna lewat
        halaman web. Pengaturan asli milik server tidak ikut berubah, jadi
        kunci milik satu pengguna tidak pernah menempel ke pengguna lain.
        """
        from dataclasses import replace

        bersih = {k: v for k, v in ubah.items() if v not in (None, "")}
        baru = replace(self, **bersih)
        baru.__post_init__()
        return baru

    @classmethod
    def dari_env(cls, env=None, pakai_env_file: bool = True) -> "Pengaturan":
        if env is None and pakai_env_file:
            # Isi berkas .env dipasang dulu supaya pengaturan di bawah
            # membacanya seperti variabel lingkungan biasa.
            from .envfile import muat_env

            muat_env()
        e = os.environ if env is None else env

        def ambil(nama: str, bawaan: str) -> str:
            nilai = e.get(nama)
            return bawaan if nilai is None or nilai == "" else nilai

        # Nama tanpa awalan juga diterima supaya gampang dipakai bersama alat
        # lain (misal OPENAI_API_KEY yang sudah biasa dipasang).
        api_key = ambil("DASPRO_AI_API_KEY", e.get("OPENAI_API_KEY", "") or "")
        base_url = ambil(
            "DASPRO_AI_BASE_URL", e.get("OPENAI_BASE_URL", "") or "https://api.openai.com/v1"
        )
        model = ambil("DASPRO_AI_MODEL", e.get("OPENAI_MODEL", "") or "gpt-4o-mini")

        return cls(
            host=ambil("DASPRO_HOST", "127.0.0.1"),
            port=_ke_int(ambil("DASPRO_PORT", "8787"), 8787),
            port_fallback=_ke_int(ambil("DASPRO_PORT_FALLBACK", "10"), 10),
            data_dir=Path(ambil("DASPRO_DATA_DIR", str(FOLDER_BAWAAN))),
            skill_dir=Path(ambil("DASPRO_SKILL_DIR", str(folder_skill_bawaan()))),
            ai_base_url=base_url.rstrip("/"),
            ai_api_key=api_key,
            ai_model=model,
            ai_timeout=_ke_int(ambil("DASPRO_AI_TIMEOUT", "300"), 300),
            ai_max_tokens=_ke_int(ambil("DASPRO_AI_MAX_TOKENS", "32768"), 32768),
            ai_temperature=_ke_float(ambil("DASPRO_AI_TEMPERATURE", "0.2"), 0.2),
            gcc=ambil("DASPRO_GCC", "gcc"),
            run_timeout=_ke_int(ambil("DASPRO_RUN_TIMEOUT", "5"), 5),
            memory_mb=_ke_int(ambil("DASPRO_MEMORY_MB", "256"), 256),
            max_upload_mb=_ke_int(ambil("DASPRO_MAX_UPLOAD_MB", "32"), 32),
            max_repair=_ke_int(ambil("DASPRO_MAX_REPAIR", "2"), 2),
            job_workers=_ke_int(ambil("DASPRO_JOB_WORKERS", "2"), 2),
            job_ttl_jam=_ke_int(ambil("DASPRO_JOB_TTL_JAM", "24"), 24),
            auth_token=ambil("DASPRO_AUTH_TOKEN", ""),
            public_base_url=ambil("DASPRO_PUBLIC_BASE_URL", "").rstrip("/"),
        )
