---
name: solve-daspro
description: Kerjakan tugas praktikum Dasar Pemrograman C (modul + LKP): tulis semua file .c, verifikasi gcc + run nyata, susun jawaban_LKP_Modul_X.md + versi HTML copyable, dan isikan jawaban ke template LKP .docx tanpa mengubah format aslinya. Use when user says kerjakan modul/LKP/tugas/latihan daspro, tracing, eksperimen, debugging C, atau isi LKP/docx/worksheet sesuai jawaban.
---

# Solve Daspro

Kerjakan satu folder modul praktikum C sampai tuntas: kode + verifikasi + laporan.

## 1. Pindai input

Cari di folder modul: PDF modul (`Modul_Praktikum_*.pdf`), docx LKP, dan
`jawaban_LKP_Modul_*.md` lama (contoh format). Daftar semua soal: terbimbing
(`latihan_01.c`...), `tracing.c`, `eksperimen.c`, `debugging_b4.c`->`debugging.c`,
mandiri (`latihan_mandiri/level_*.c`), tugas (`tugas/tugas_modul_*.c`).

## 2. Tulis kode C

Baca `references/gaya-c.md` dulu, tiru `references/contoh_*.c`:

- `int main(void)`, `#include <stdio.h>` dulu.
- Blok `if` WAJIB `{}` walau satu baris.
- `switch`: tiap `case` diakhiri `break`, selalu ada `default`.
- Periksa input tidak valid di ATAS + `return 1` sebelum hitung.
- `switch` untuk kode diskret, `if-else-if` dari batas TERTINGGI untuk rentang.
- Uang selalu `%.2f`. Header komentar Nama/NIM/Kelas/Modul di file tugas.
- Nama file: lowercase + underscore + `.c`.

## 2b. Gaya bahasa (WAJIB)

Baca `references/gaya-bahasa.md` sebelum menulis apa pun yang dibaca dosen:
laporan MD, HTML copyable, komentar kode, dan pesan `printf`.

- Tulis seperti mahasiswa semester 1 Informatika yang baru kenal C, bukan
 seperti dokumentasi resmi. Pembaca belum tentu paham istilah teknis.
- Jangan pakai istilah teknis tanpa dijelaskan: `guard clause`,
 `short-circuit`, `fall-through`, `early-exit`, `edge case`,
 `undefined behavior`, `garbage value`, `runtime error`, dan sejenisnya. Pakai kalimat biasa (lihat tabel ganti di
 `references/gaya-bahasa.md`).
- Kalau harus menyebut nama fitur C, sebut namanya lalu jelaskan artinya
 satu kalimat dengan bahasa sehari-hari.
- Kalimat pendek, satu ide satu kalimat, gaya aktif, maksimal sekitar 25 kata.
- Karakter panah JANGAN pakai simbol Unicode. Tulis `->` (minus lalu lebih
 besar). Sama untuk `>=`, `<=`, `!=`, kali pakai `*` atau huruf `x`, minus
 pakai `-` biasa, dan titik-tiga pakai tiga titik biasa.
- Jangan pakai emoji dan tanda seru.
- Hanya karakter yang ada di keyboard. Cek tiap file sebelum lapor:
 `python3 -c "import sys;s=open(sys.argv[1],encoding='utf-8').read();print([c for c in s if ord(c)>127])" jawaban_LKP_Modul_X.md`
 Hasil wajib `[]`.

## 3. Verifikasi (HARD GATE)

Jangan klaim tanpa bukti. Setiap `.c`:

1. `gcc -Wall -Wextra -o /tmp/prog file.c` - nol error, nol warning.
2. Run tiap nilai batas nyata via stdin pipe, catat stdout verbatim
  (daftar batas: `references/format-laporan.md`).
3. Kolom Actual di MD diambil dari stdout run, bukan karangan.
4. Cepat: `bash scripts/verify.sh <dir-modul>` untuk smoke compile semua file.

## 4. Susun laporan

Baca `references/format-laporan.md` dan `references/gaya-bahasa.md`, tiru
`references/contoh_jawaban_LKP_Modul_4.md`:

- `jawaban_LKP_Modul_X.md`: header identitas, tabel Expected|Actual|Status,
 analisis, trace table, tabel eksperimen, tabel debugging, refleksi, pernyataan AI.
- `jawaban_LKP_Modul_X_copyable.html`: generate via
 `python3 scripts/md_to_copyable.py jawaban_LKP_Modul_X.md`
 (tiap sel tabel + tiap Q/A dapat tombol `copy`; contoh hasil:
 `references/contoh_copyable.html`).

Tulis dengan gaya bahasa di `references/gaya-bahasa.md`: bahasa mahasiswa
semester 1, tanpa istilah teknis yang tidak dijelaskan, tanpa karakter di
luar keyboard. Sebelum lapor, cek tiap file dan pastikan hasilnya `[]`:

```bash
python3 scripts/cek_bahasa.py jawaban_LKP_Modul_X.md jawaban_LKP_Modul_X_copyable.html
```

## 5. Isi LKP docx (kalau modul minta file .docx diisi)

User mengunggah template docx penuh titik-titik/sel kosong + sumber jawaban
terpisah, dan minta jawabannya dimasukkan tanpa mengubah format aslinya:

1. `python3 scripts/isi_lkp_docx.py peta template.docx unpacked`
   buka docx tanpa mengubah XML. Cetak peta sel jawaban dan blok titik-titik
   beserta konteks soal, baris, dan kolom ke `unpacked/peta.json`.
2. Isi `mapping.json` dari peta itu:
   `{"sel": {"kunci": "jawaban sel"}, "titik": {"1": "jawaban baris 1"}}`
   kunci sel dari `peta.json` (`paraId` unik kalau ada, kalau tidak `selN`),
   kunci titik = nomor blok jawaban di `peta.json`. Beberapa baris lanjutan
   untuk satu jawaban memakai satu nomor.
3. `python3 scripts/isi_lkp_docx.py isi unpacked mapping.json hasil.docx`
   terapkan mapping, normalkan hanya jawaban baru ke karakter keyboard,
   lalu bungkus ulang. Isian tanpa jawaban tetap utuh, bukan dihapus atau
   diisi kalimat generik. Cek jumlah paragraf sama persis (struktur utuh).

Aturan isi: kotak "tempelkan screenshot" dibiarkan kosong, label/nomor soal
asli tidak disentuh, jawaban ditulis dengan gaya bahasa `references/gaya-bahasa.md`
(bahasa mahasiswa baru, karakter keyboard saja).

## 6. Serah terima

Lapor: file `.c` dibuat/diubah, hasil `verify.sh` (PASS n/n), contoh Actual vs
Expected yang diverifikasi run. Kalau ada docx: nama file hasil + jumlah sel/baris
yang diisi + hasil cek paragraf (SAMA). Jangan tawarkan langkah lanjutan.
