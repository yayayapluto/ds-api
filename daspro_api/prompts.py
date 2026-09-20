"""Penyusun permintaan ke AI.

Semua aturan gaya dari folder skill disisipkan apa adanya ke dalam
permintaan. Jadi AI menulis dengan aturan yang sama seperti yang dipakai
saat mengerjakan modul secara manual.
"""
import json
from typing import Optional

from daspro_api.extract import ringkas
from daspro_api.skillbridge import Skill

ATURAN_UMUM = """Kamu asisten praktikum Dasar Pemrograman. Tugasmu mengerjakan \
modul praktikum bahasa C untuk mahasiswa semester 1 Informatika.

Aturan yang wajib dipatuhi:
- Ikuti acuan gaya C dan acuan gaya bahasa yang diberikan di bawah.
- Tulis hanya karakter yang ada di keyboard biasa. Jangan pakai tanda panah \
Unicode, tanda kutip melengkung, atau emoji.
- Pesan printf memakai bahasa Indonesia sederhana.
- Nama berkas: huruf kecil, garis bawah, akhiran .c.
- Balas dengan JSON yang sah saja, tanpa kalimat pembuka dan tanpa pagar kode."""


def _contoh_kode(skill: Skill, batas: int = 3) -> str:
    bagian = []
    for item in skill.contoh_kode()[:batas]:
        bagian.append(f"### contoh: {item['nama']}\n```c\n{item['isi'].strip()}\n```")
    return "\n\n".join(bagian)


def sistem_dasar(skill: Skill) -> str:
    """Kalimat pengarah yang sama untuk semua permintaan."""
    return (
        ATURAN_UMUM
        + "\n\n=== ACUAN GAYA C ===\n"
        + skill.acuan_gaya_c()
        + "\n\n=== ACUAN GAYA BAHASA ===\n"
        + skill.acuan_gaya_bahasa()
    )


def _identitas(identitas: dict) -> str:
    return (
        f"Nama: {identitas.get('nama', '-')}\n"
        f"NIM: {identitas.get('nim', '-')}\n"
        f"Kelas: {identitas.get('kelas', '-')}\n"
        f"Modul: {identitas.get('modul', '-')}\n"
        f"Mata kuliah: {identitas.get('matakuliah', 'Praktikum Dasar Pemrograman')}\n"
        f"Nama dosen: {identitas.get('dosen', '-')}\n"
        f"Asisten: {identitas.get('asisten', '-')}"
    )


def prompt_analisis(skill: Skill, modul_teks: str, lkp_teks: str, identitas: dict) -> str:
    """Langkah 1: minta daftar soal yang harus dikerjakan."""
    return f"""Baca modul praktikum dan template LKP berikut, lalu susun daftar soal.

=== IDENTITAS MAHASISWA ===
{_identitas(identitas)}

=== ISI MODUL (hasil baca berkas) ===
{ringkas(modul_teks, 24000)}

=== ISI TEMPLATE LKP ===
{ringkas(lkp_teks, 16000)}

Balas JSON dengan bentuk:
{{
  "modul": 5,
  "judul": "judul modul",
  "soal": [
    {{
      "id": "latihan_01",
      "nama_berkas": "latihan_01.c",
      "folder": "",
      "jenis": "terbimbing",
      "bagian": "IV.1",
      "judul": "judul singkat soal",
      "deskripsi": "apa yang harus dibuat, lengkap dengan aturan batas nilai",
      "kasus_uji": [{{"masukan": "75\\n", "harapan": "keterangan keluaran yang diharapkan"}}]
    }}
  ],
  "catatan": "hal penting lain di modul, misal ada bagian tracing, eksperimen, debugging, atau tugas"
}}

Aturan pengisian:
- "folder" diisi "latihan_mandiri" atau "tugas" kalau soal memang di situ, selain itu kosong.
- "jenis" hanya boleh: terbimbing, tracing, eksperimen, debugging, mandiri, tugas.
- "kasus_uji" minimal 5 baris untuk soal yang membaca masukan, termasuk nilai batas \
dan nilai yang tidak valid. Tulis masukan seperti yang diketik di terminal, tiap nilai \
diakhiri \\n.
- Kalau ada soal debugging, sebut di "deskripsi" bahwa kode yang salah perlu ditulis \
ulang di berkas bernama debugging.c."""


def prompt_kode(
    skill: Skill, soal: dict, identitas: dict, jawaban_ai: Optional[dict] = None
) -> str:
    """Langkah 2: minta kode C untuk satu soal."""
    perbaikan = ""
    if jawaban_ai:
        perbaikan = (
            "\n\n=== KODE SEBELUMNYA YANG MASIH BERMASALAH ===\n```c\n"
            + jawaban_ai.get("kode", "")
            + "\n```\n\n=== CATATAN DARI HASIL KOMPILASI DAN PENGUJIAN ===\n"
            + jawaban_ai.get("catatan", "")
            + "\nPerbaiki kode di atas. Jangan ulang kesalahan yang sama."
        )

    contoh = _contoh_kode(skill)
    kasus = json.dumps(soal.get("kasus_uji", []), ensure_ascii=False, indent=2)
    return f"""Tulis kode C untuk satu soal modul praktikum berikut.

=== IDENTITAS MAHASISWA (isi header komentar) ===
{_identitas(identitas)}

=== SOAL ===
id: {soal.get('id')}
nama berkas: {soal.get('nama_berkas')}
jenis: {soal.get('jenis')}
judul: {soal.get('judul')}
penjelasan: {soal.get('deskripsi')}

=== KASUS UJI YANG HARUS DIPENUHI ===
{kasus}

=== CONTOH GAYA DARI SKILL ===
{contoh}{perbaikan}

Balas JSON dengan bentuk:
{{
  "nama_berkas": "{soal.get('nama_berkas')}",
  "kode": "isi berkas .c lengkap, tulis \\n untuk baris baru",
  "penjelasan": "penjelasan singkat cara kerja program dengan bahasa sederhana",
  "tabel_uji": [
    {{"masukan": "75", "expected": "yang diharapkan", "catatan": "kenapa nilai ini penting"}}
  ]
}}

Aturan kode:
- Baris pertama #include <stdio.h>, lalu int main(void).
- Setiap blok if wajib memakai kurung kurawal walau isinya satu baris.
- Setiap case di dalam switch diakhiri break, dan selalu ada default.
- Periksa masukan yang tidak masuk akal di bagian atas, lalu return 1 sebelum menghitung.
- Untuk rentang nilai, mulai perbandingan dari batas tertinggi.
- Uang selalu dicetak dua angka di belakang koma.
- Berkas tugas wajib diawali komentar berisi Nama, NIM, Kelas, dan Modul."""


def prompt_laporan(
    skill: Skill,
    modul_teks: str,
    lkp_teks: str,
    identitas: dict,
    hasil_uji: list,
    pertanyaan: Optional[list] = None,
) -> str:
    """Langkah 3: minta isi laporan, dengan hasil uji nyata sebagai bahan."""
    ringkas_uji = []
    for item in hasil_uji:
        ringkas_uji.append(
            {
                "soal": item.get("judul"),
                "berkas": item.get("nama_berkas"),
                "masukan": item.get("masukan"),
                "keluaran_nyata": item.get("keluaran"),
                "kode_keluar": item.get("kode_keluar"),
                "status": item.get("status"),
            }
        )

    daftar_pertanyaan = ""
    if pertanyaan:
        daftar_pertanyaan = "\n".join(
            f"{i}. {t}" for i, t in enumerate(pertanyaan, 1)
        )

    return f"""Susun isi laporan LKP berdasarkan modul dan hasil pengujian nyata berikut.

=== IDENTITAS MAHASISWA ===
{_identitas(identitas)}

=== ISI MODUL ===
{ringkas(modul_teks, 20000)}

=== ISI TEMPLATE LKP ===
{ringkas(lkp_teks, 14000)}

=== HASIL PENGUJIAN NYATA (keluaran ini yang benar, jangan diubah) ===
{json.dumps(ringkas_uji, ensure_ascii=False, indent=2)}

=== DAFTAR PERTANYAAN YANG HARUS DIJAWAB ===
{daftar_pertanyaan or "(tidak ada daftar terpisah, baca pertanyaan dari template LKP)"}

Balas JSON dengan bentuk:
{{
  "judul": "judul laporan",
  "bagian": [
    {{
      "kode": "IV.1",
      "judul": "judul bagian",
      "berkas": "latihan_01.c",
      "analisis": [{{"pertanyaan": "...", "jawaban": "..."}}],
      "trace": {{"kolom": ["Langkah", "Kondisi", "Hasil Kondisi"], "baris": [["1", "x > 5", "true"]]}},
      "prediksi_output": "keluaran yang diperkirakan"
    }}
  ],
  "eksperimen": [{{"perubahan": "...", "prediksi": "...", "hasil": "...", "error": "tidak ada", "penjelasan": "..."}}],
  "debugging": {{"error_gcc": "tempelan pesan gcc", "temuan": [{{"bagian": "...", "jenis": "...", "penyebab": "...", "perbaikan": "..."}}]}},
  "refleksi": ["jawaban 1", "jawaban 2", "jawaban 3"],
  "isian_lkp": {{
    "titik": {{"1": "jawaban untuk baris titik nomor 1 di template"}},
    "sel": {{"kunci dari peta template": "jawaban untuk sel itu"}}
  }}
}}

Aturan penulisan:
- Pakai bahasa mahasiswa semester 1. Kalimat pendek, satu ide satu kalimat.
- Jangan pakai istilah teknis tanpa dijelaskan dengan kalimat biasa.
- Kolom hasil nyata diisi persis seperti keluaran pengujian di atas.
- Bagian isian_lkp hanya untuk tempat kosong yang benar-benar ada di template. \
Kunci "sel" harus memakai kunci dari peta template yang diberikan di bawah.
- Jawaban refleksi ditulis jujur, masing-masing 2 sampai 4 kalimat.

=== ACUAN FORMAT LAPORAN ===
{skill.acuan_format_laporan()}

=== CONTOH LAPORAN SEBELUMNYA ===
{ringkas(skill.contoh_laporan(), 9000)}"""
