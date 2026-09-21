"""Pemanggil layanan AI yang cocok dengan antarmuka OpenAI.

Hanya memakai pustaka bawaan Python (urllib), jadi tidak ada paket tambahan
yang perlu dipasang. Alamat, kunci, dan nama model diambil dari pengaturan,
sehingga penyedia lain yang memakai antarmuka sama (OpenRouter, DeepSeek,
Groq, Ollama) bisa dipakai hanya dengan mengganti tiga nilai itu.

Kelas ini selalu memanggil layanan AI sungguhan. Tidak ada mode jawaban
tiruan di sini, supaya kode C yang dihasilkan tidak pernah karangan. Untuk
keperluan pengujian, kelas tiruan ada di `tests/mockai.py`.
"""
import json
import re
import time
import urllib.error
import urllib.request

from daspro_api.config import Pengaturan
from daspro_api.errors import AiBelumDiatur, AiGagal


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


def baca_json_http(teks: str):
    """Baca nilai JSON pertama dari badan jawaban HTTP.

    Sebagian gerbang (proxy) menambahkan penanda SSE seperti `data: [DONE]`
    di belakang badan JSON yang sebenarnya, sehingga `json.loads` menolak
    dengan "Extra data". Karena itu kita ambil nilai JSON pertama saja dan
    mengabaikan sisanya.
    """
    if teks is None or not teks.strip():
        raise AiGagal("jawaban layanan AI kosong")

    sisa = teks.lstrip()
    if sisa.startswith("data:"):
        sisa = sisa[5:].lstrip()

    try:
        nilai, _ = json.JSONDecoder().raw_decode(sisa)
        return nilai
    except json.JSONDecodeError as e:
        raise AiGagal(
            "jawaban layanan AI bukan JSON yang sah", detail=teks[:600]
        ) from e


def baca_aliran_sse(baris) -> dict:
    """Susun satu jawaban dari potongan aliran (SSE) layanan AI.

    Mode aliran mengirim jawaban sedikit-sedikit dengan awalan `data:`,
    bukan satu badan JSON utuh. Fungsi ini menggabungkan potongan teksnya
    dan mencatat alasan berhenti serta pemakaian token kalau ada.

    Hasilnya berbentuk sama seperti jawaban mode biasa, supaya pemanggil
    tidak perlu tahu mode mana yang dipakai.
    """
    potongan = []
    alasan = ""
    pemakaian = None
    for baris in baris:
        teks = baris.decode("utf-8", "replace").strip() if isinstance(baris, bytes) else str(baris).strip()
        if not teks or not teks.startswith("data:"):
            continue
        isi = teks[5:].strip()
        if isi == "[DONE]":
            break
        try:
            potong = json.loads(isi)
        except json.JSONDecodeError:
            continue
        if not isinstance(potong, dict):
            continue
        if isinstance(potong.get("usage"), dict):
            pemakaian = potong["usage"]
        for pilih in potong.get("choices") or []:
            if not isinstance(pilih, dict):
                continue
            if pilih.get("finish_reason"):
                alasan = str(pilih["finish_reason"])
            delta = pilih.get("delta") or {}
            bagian = delta.get("content")
            if bagian:
                potongan.append(str(bagian))
    return {
        "choices": [
            {"message": {"content": "".join(potongan)}, "finish_reason": alasan}
        ],
        "usage": pemakaian,
    }

class KlienAi:
    """Pemanggil model bahasa sungguhan lewat antarmuka OpenAI."""

    def __init__(self, pengaturan: Pengaturan):
        self.p = pengaturan

    # --- pemeriksaan kesiapan -------------------------------------------
    def periksa(self) -> None:
        """Pastikan layanan AI sudah diatur sebelum dipakai.

        Dipanggil saat server dinyalakan dan sebelum setiap pekerjaan mulai,
        supaya pekerjaan tidak berjalan setengah jalan lalu gagal.
        """
        if not self.p.ai_api_key:
            raise AiBelumDiatur(
                "kunci layanan AI belum diisi. Isi DASPRO_AI_API_KEY di berkas "
                ".env atau di variabel lingkungan."
            )
        if not self.p.ai_base_url:
            raise AiBelumDiatur(
                "alamat layanan AI belum diisi. Isi DASPRO_AI_BASE_URL, "
                "misalnya https://api.openai.com/v1"
            )
        if not self.p.ai_model:
            raise AiBelumDiatur("nama model belum diisi. Isi DASPRO_AI_MODEL.")

    def uji_koneksi(self) -> dict:
        """Kirim satu pertanyaan kecil untuk memastikan layanan AI menjawab.

        Dipakai oleh `--cek` dan endpoint pengujian, supaya kesalahan kunci
        atau alamat ketahuan sebelum modul dikerjakan.
        """
        self.periksa()
        mulai = time.time()
        jawab = self.lengkapi(
            "Balas dengan satu kata: siap",
            sistem="Jawab sesingkat mungkin.",
            suhu=0.0,
            token=16,
        )
        return {
            "ok": True,
            "model": self.p.ai_model,
            "alamat": self.p.ai_base_url,
            "jawaban": jawab.strip()[:80],
            "detik": round(time.time() - mulai, 2),
        }

    # --- panggilan sebenarnya -------------------------------------------
    def _kirim(self, url: str, isi: dict, header: dict):
        """Kirim permintaan dan kembalikan badan jawaban sebagai baris-baris.

        Selalu memakai mode aliran. Sebagian gerbang menahan jawaban mode
        biasa sampai seluruh teks selesai ditulis, sehingga panggilan panjang
        gampang melewati batas waktu. Dengan aliran, potongan pertama sudah
        sampai jauh sebelum batas waktu habis.
        """
        data = json.dumps(isi).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=header, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.p.ai_timeout) as r:
                return list(r)
        except urllib.error.HTTPError as e:
            badan = ""
            try:
                badan = e.read().decode("utf-8", "replace")[:600]
            except Exception:  # badan error kadang tidak bisa dibaca
                badan = "(tidak terbaca)"
            # 408, 429, dan 5xx biasanya lewat: gerbang sedang sibuk atau
            # meneruskan permintaan ke model yang sedang mengantre.
            sementara = e.code in {408, 409, 425, 429} or e.code >= 500
            raise AiGagal(
                f"layanan AI menolak permintaan (HTTP {e.code})",
                detail=badan,
                sementara=sementara,
            ) from e
        except urllib.error.URLError as e:
            raise AiGagal(
                f"tidak bisa menghubungi layanan AI: {e.reason}", sementara=True
            ) from e
        except TimeoutError as e:
            raise AiGagal(
                "panggilan ke layanan AI melewati batas waktu", sementara=True
            ) from e

    def _post(self, url: str, isi: dict, header: dict) -> dict:
        """Panggil layanan AI dalam mode aliran, lalu susun jadi satu jawaban."""
        return baca_aliran_sse(self._kirim(url, isi, header))

    def lengkapi(self, prompt: str, sistem: str = "", suhu=None, token=None) -> str:
        """Minta satu jawaban teks dari model.

        Kegagalan yang sifatnya sementara (jaringan tersendat, gerbang
        menolak sementara, jawaban kosong) dicoba lagi dengan jeda
        bertambah. Kegagalan tetap seperti kunci salah langsung dilempar,
        supaya tidak menunggu sia-sia.
        """
        self.periksa()
        kali = max(1, self.p.ai_retry + 1)
        for n in range(kali):
            try:
                return self._lengkapi_sekali(prompt, sistem, suhu, token)
            except AiGagal as e:
                if not e.sementara or n == kali - 1:
                    raise
                time.sleep(min(2**n, 8))
        raise AiGagal("panggilan ke layanan AI gagal")

    def _lengkapi_sekali(
        self, prompt: str, sistem: str = "", suhu=None, token=None
    ) -> str:
        """Satu percobaan panggilan tanpa pengulangan."""
        pesan = []
        if sistem:
            pesan.append({"role": "system", "content": sistem})
        pesan.append({"role": "user", "content": prompt})

        isi = {
            "model": self.p.ai_model,
            "messages": pesan,
            "temperature": self.p.ai_temperature if suhu is None else suhu,
            "max_tokens": self.p.ai_max_tokens if token is None else token,
            "stream": True,
            # Supaya pemakaian token tetap ikut dikirim di mode aliran.
            "stream_options": {"include_usage": True},
        }
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.p.ai_api_key}",
        }
        url = f"{self.p.ai_base_url}/chat/completions"
        hasil = self._post(url, isi, header)
        try:
            pilih = hasil["choices"][0]
            teks = str(pilih["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as e:
            raise AiGagal(
                "bentuk jawaban layanan AI tidak dikenal",
                detail=str(hasil)[:600],
                sementara=True,
            ) from e

        if not teks:
            # Model penalaran bisa menghabiskan seluruh jatah token untuk
            # berpikir, sehingga teks jawabannya kosong dan jawaban terpotong.
            alasan = str(pilih.get("finish_reason") or "")
            if alasan == "length":
                raise AiGagal(
                    "jawaban AI terpotong sebelum selesai: seluruh jatah "
                    f"token ({isi['max_tokens']}) habis dipakai untuk berpikir. "
                    "Naikkan DASPRO_AI_MAX_TOKENS atau pakai model tanpa "
                    "penalaran."
                )
            # Jawaban kosong tanpa alasan jelas biasanya gangguan sesaat di
            # gerbang atau model yang sedang mengantre, jadi pantas diulang.
            raise AiGagal(
                "jawaban AI kosong", detail=str(hasil)[:600], sementara=True
            )
        return teks

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

