#!/usr/bin/env python3
"""Klien AI tiruan, khusus untuk pengujian.

Klien ini hanya dipakai oleh berkas pengujian. Kode layanan di folder
`daspro_api/` selalu memanggil layanan AI sungguhan, supaya kode C yang
dihasilkan tidak pernah karangan.

Cara pakai:
    klien = KlienAiTiruan(pengaturan, balasan=[teks1, teks2, ...])
    pipeline = Pipeline(pengaturan, klien=klien)

Tiap kali `lengkapi` dipanggil, satu balasan diambil dari daftar sesuai
urutan. Kalau balasan berupa fungsi, fungsi itu dipanggil dengan prompt
sebagai nilai masuk.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daspro_api.ai import KlienAi  # noqa: E402


class KlienAiTiruan(KlienAi):
    """Pengganti KlienAi yang menjawab dari daftar balasan siap pakai."""

    def __init__(self, pengaturan, balasan=None):
        super().__init__(pengaturan)
        self.balasan = list(balasan or [])
        self.dipanggil = 0
        self.prompt_terakhir = ""

    def periksa(self) -> None:
        """Selalu siap; tidak butuh kunci karena tidak menghubungi jaringan."""
        return None

    def lengkapi(self, prompt: str, sistem: str = "", suhu=None, token=None) -> str:
        self.dipanggil += 1
        self.prompt_terakhir = prompt
        if not self.balasan:
            return "{}"
        item = self.balasan.pop(0)
        if callable(item):
            return str(item(prompt))
        return str(item)
