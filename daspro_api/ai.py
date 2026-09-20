"""Pemanggil layanan AI yang cocok dengan antarmuka OpenAI.

Hanya memakai pustaka bawaan Python (urllib), jadi tidak ada paket tambahan
yang perlu dipasang. Alamat, kunci, dan nama model diambil dari pengaturan,
sehingga penyedia lain yang memakai antarmuka sama (OpenRouter, DeepSeek,
Groq, Ollama) bisa dipakai hanya dengan mengganti tiga nilai itu.
"""
import json
import re
import time
import urllib.error
import urllib.request

from .config import Pengaturan
from .errors import AiBelumDiatur, AiGagal


def ambil_json(teks: str):
    """Ambil nilai JSON pertama yang utuh dari jawaban model.

    Model sering menulis penjelasan dulu, lalu blok ```json ... ```. Fungsi
    ini mencari bagian yang seimbang tanda kurungnya, jadi tahan terhadap
    teks tambahan di depan atau belakang.
    """
    if teks is None:
        raise AiGagal("jawaban model kosong")

    pagar = re.search(r"```(?:json)?\s*(.+?)\s*```", teks, re.S)
    if pagar:
        teks = pagar.group(1)

    mulai = None
    for i, ch in enumerate(teks):
        if ch in "{[":
            mulai = i
            break
    if mulai is None:
        raise AiGagal("jawaban model tidak memuat JSON")

    buka = teks[mulai]
    tutup = "}" if buka == "{" else "]"
    dalam_teks = False
    lolos = False
    kedalaman = 0
    for i in range(mulai, len(teks)):
        ch = teks[i]
        if dalam_teks:
            if lolos:
                lolos = False
            elif ch == "\\":
                lolos = True
            elif ch == '"':
                dalam_teks = False
            continue
        if ch == '"':
            dalam_teks = True
        elif ch == buka:
            kedalaman += 1
        elif ch == tutup:
            kedalaman -= 1
            if kedalaman == 0:
                potong = teks[mulai : i + 1]
                try:
                    return json.loads(potong)
                except json.JSONDecodeError as e:
                    raise AiGagal(f"JSON dari model tidak bisa dibaca: {e}") from e
    raise AiGagal("JSON dari model tidak lengkap")


def _rapikan_pesan(pesan: str) -> str:
    """Buang awalan 'data:' yang dipakai mode streaming."""
    return pesan.strip()


class KlienAi:
    """Pemanggil model bahasa. Punya dua mode: openai dan mock."""

    def __init__(self, pengaturan: Pengaturan, mock_balasan=None):
        self.p = pengaturan
        self._mock = list(mock_balasan or [])

    # --- mode mock -------------------------------------------------------
    def _mock_jawab(self, prompt: str) -> str:
        if self._mock:
            item = self._mock.pop(0)
            if callable(item):
                return str(item(prompt))
            return str(item)
        return "{}"

    # --- panggilan sebenarnya -------------------------------------------
    def _post(self, url: str, isi: dict, header: dict) -> dict:
        data = json.dumps(isi).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=header, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.p.ai_timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            badan = ""
            try:
                badan = e.read().decode("utf-8", "replace")[:600]
            except Exception:  # badan error kadang tidak bisa dibaca
                badan = "(tidak terbaca)"
            raise AiGagal(
                f"layanan AI menolak permintaan (HTTP {e.code})", detail=badan
            ) from e
        except urllib.error.URLError as e:
            raise AiGagal(f"tidak bisa menghubungi layanan AI: {e.reason}") from e
        except TimeoutError as e:
            raise AiGagal("panggilan ke layanan AI melewati batas waktu") from e

    def lengkapi(self, prompt: str, sistem: str = "", suhu=None, token=None) -> str:
        """Minta satu jawaban teks dari model."""
        if self.p.ai_provider == "mock":
            return self._mock_jawab(prompt)
        if not self.p.ai_siap:
            raise AiBelumDiatur(
                "layanan AI belum diatur. Isi DASPRO_AI_API_KEY dan "
                "DASPRO_AI_BASE_URL, atau pakai DASPRO_AI_PROVIDER=mock."
            )

        pesan = []
        if sistem:
            pesan.append({"role": "system", "content": sistem})
        pesan.append({"role": "user", "content": prompt})

        isi = {
            "model": self.p.ai_model,
            "messages": pesan,
            "temperature": self.p.ai_temperature if suhu is None else suhu,
            "max_tokens": self.p.ai_max_tokens if token is None else token,
        }
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.p.ai_api_key}",
        }
        url = f"{self.p.ai_base_url}/chat/completions"
        hasil = self._post(url, isi, header)
        try:
            return _rapikan_pesan(hasil["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as e:
            raise AiGagal("bentuk jawaban layanan AI tidak dikenal", detail=str(hasil)[:600]) from e

    def lengkapi_json(self, prompt: str, sistem: str = "", suhu=None, token=None) -> dict:
        """Minta jawaban, lalu baca sebagai JSON.

        Kalau percobaan pertama gagal dibaca, dicoba sekali lagi dengan
        permintaan yang lebih tegas supaya model hanya menulis JSON.
        """
        mentah = self.lengkapi(prompt, sistem=sistem, suhu=suhu, token=token)
        try:
            return ambil_json(mentah)
        except AiGagal:
            tegas = (
                prompt
                + "\n\nBalas HANYA satu objek JSON yang sah, tanpa kalimat pembuka, "
                "tanpa penjelasan, tanpa pagar kode."
            )
            mentah2 = self.lengkapi(tegas, sistem=sistem, suhu=0.0, token=token)
            return ambil_json(mentah2)

    def coba_lagi(self, prompt: str, sistem: str = "", suhu=None, token=None, kali: int = 3):
        """Ulangi panggilan kalau layanan sedang bermasalah (bukan salah isi)."""
        kali = max(1, kali)
        for n in range(kali):
            try:
                return self.lengkapi(prompt, sistem=sistem, suhu=suhu, token=token)
            except AiGagal as e:
                if n == kali - 1:
                    raise
                time.sleep(min(2 ** n, 8))
        raise AiGagal("panggilan ke layanan AI gagal")
