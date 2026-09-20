# daspro-api

Layanan HTTP untuk mengerjakan modul praktikum Dasar Pemrograman C.

Kirim modul praktikum dan template LKP lewat satu permintaan, lalu unduh
hasilnya berupa satu berkas ZIP. Isi ZIP: semua berkas `.c`, laporan
`jawaban_LKP_Modul_X.md`, versi HTML yang tiap selnya bisa disalin, dan
template LKP `.docx` yang sudah terisi.

Yang dikerjakan AI hanya dua hal: menulis kode C dan menyusun isi laporan.
Sisanya dikerjakan program biasa, jadi hasilnya bisa diperiksa dan diulang:
mengompilasi dengan `gcc`, menjalankan program dengan masukan nilai batas,
membuat HTML copyable, mengisi template docx, dan memeriksa gaya bahasa.

## Isi repo

```
daspro_api/          kode layanan
  config.py          pengaturan dari variabel lingkungan
  ai.py              pemanggil model bahasa (antarmuka OpenAI, lewat urllib)
  prompts.py         penyusun permintaan ke AI, memuat acuan gaya dari skill
  extract.py         pembaca berkas modul (PDF, docx, teks)
  compiler.py        kompilasi dan menjalankan program C dengan batas aman
  report.py          penyusun laporan markdown
  sanitize.py        pengganti karakter di luar keyboard
  pipeline.py        alur pengerjaan satu modul
  jobs.py            pekerjaan latar belakang dan kemajuannya
  request.py         pembaca badan permintaan JSON dan multipart
  server.py          endpoint HTTP (pustaka bawaan Python)
  __main__.py        perintah baris
skill/               salinan skill solve-daspro (skrip + acuan gaya)
tests/               pengujian dan berkas contoh
data/                folder kerja, dibuat sendiri saat dijalankan
```

Isi folder `skill/` disalin apa adanya dari skill `solve-daspro`. Isinya
dijaga sama dengan aslinya, kecuali nama dan NIM pada berkas contoh yang
sudah diganti tanda `-`. Karena itu folder ini tidak ikut diperiksa
`pyright` (lihat `pyrightconfig.json`); kode yang diperiksa hanya yang ada
di `daspro_api/` dan `tests/`.

Tidak ada paket pihak ketiga yang wajib dipasang. Kalau modulnya PDF,
pasang `pypdf` supaya teksnya bisa dibaca. Untuk mengisi template docx,
pasang `lxml` (skrip skill memakainya).

## Menjalankan

```bash
export DASPRO_AI_API_KEY="kunci-rahasia"
export DASPRO_AI_BASE_URL="https://api.openai.com/v1"
export DASPRO_AI_MODEL="gpt-4o-mini"

python3 -m daspro_api --cek          # pastikan semuanya siap
python3 -m daspro_api                # mulai melayani di 127.0.0.1:8787
```

Penyedia lain yang memakai antarmuka sama bisa dipakai dengan mengganti
`DASPRO_AI_BASE_URL`, `DASPRO_AI_API_KEY`, dan `DASPRO_AI_MODEL`. Untuk uji
coba tanpa internet, setel `DASPRO_AI_PROVIDER=mock`.

## Pengaturan

Semua dibaca dari variabel lingkungan. Nama tanpa awalan `DASPRO_` juga
diterima untuk kunci yang sudah biasa dipakai (`OPENAI_API_KEY`).

| Variabel | Bawaan | Keterangan |
| --- | --- | --- |
| `DASPRO_HOST` | `127.0.0.1` | alamat yang didengarkan |
| `DASPRO_PORT` | `8787` | nomor port |
| `DASPRO_DATA_DIR` | `./data` | tempat berkas kerja |
| `DASPRO_SKILL_DIR` | `./skill` | folder skill (skrip dan acuan gaya) |
| `DASPRO_AI_BASE_URL` | `https://api.openai.com/v1` | alamat layanan AI |
| `DASPRO_AI_API_KEY` | kosong | kunci layanan AI |
| `DASPRO_AI_MODEL` | `gpt-4o-mini` | nama model |
| `DASPRO_AI_PROVIDER` | `auto` | `auto`, `openai`, atau `mock` |
| `DASPRO_AI_TIMEOUT` | `180` | batas waktu satu panggilan AI (detik) |
| `DASPRO_AI_MAX_TOKENS` | `8192` | batas panjang jawaban AI |
| `DASPRO_GCC` | `gcc` | program kompilator |
| `DASPRO_RUN_TIMEOUT` | `5` | batas waktu menjalankan program (detik) |
| `DASPRO_MEMORY_MB` | `256` | batas memori program C |
| `DASPRO_MAX_UPLOAD_MB` | `32` | batas ukuran unggahan |
| `DASPRO_MAX_REPAIR` | `2` | berapa kali kode diperbaiki kalau gagal |
| `DASPRO_JOB_WORKERS` | `2` | berapa pekerjaan jalan bersamaan |
| `DASPRO_JOB_TTL_JAM` | `24` | umur hasil sebelum dibersihkan |
| `DASPRO_AUTH_TOKEN` | kosong | kalau diisi, wajib dikirim di header `Authorization` |

## Endpoint

| Metode | Jalur | Keterangan |
| --- | --- | --- |
| `GET` | `/health` | keadaan layanan, kesiapan skill, AI, dan gcc |
| `GET` | `/v1/skill` | daftar skrip dan acuan gaya yang dipakai |
| `POST` | `/v1/jobs` | unggah modul dan template, mulai pekerjaan |
| `GET` | `/v1/jobs` | daftar pekerjaan |
| `GET` | `/v1/jobs/{id}` | status, kemajuan, dan catatan tahap |
| `GET` | `/v1/jobs/{id}/result` | ringkasan hasil |
| `GET` | `/v1/jobs/{id}/download` | unduh berkas ZIP |
| `GET` | `/v1/jobs/{id}/files/{nama}` | unduh satu berkas hasil |
| `POST` | `/v1/jobs/{id}/cancel` | batalkan pekerjaan |
| `POST` | `/v1/verify` | kompilasi dan jalankan berkas `.c` |
| `POST` | `/v1/cek-bahasa` | periksa gaya bahasa laporan |
| `POST` | `/v1/docx/peta` | lihat tempat kosong di template docx |
| `POST` | `/v1/docx/isi` | isi template docx dari mapping |

Isi permintaan bisa `multipart/form-data` (kalau ada berkas) atau
`application/json`. Kolom yang dipakai endpoint `/v1/jobs`:

| Kolom | Wajib | Keterangan |
| --- | --- | --- |
| `modul` | ya | berkas PDF atau docx modul praktikum |
| `lkp` | tidak | template LKP docx yang mau diisi |
| `identitas` | ya | JSON berisi `nama`, `nim`, `kelas`, `modul`, dan `matakuliah` |
| `isi_docx` | tidak | `true` untuk mengisi template, bawaan `true` |
| `buat_copyable` | tidak | `true` untuk membuat versi HTML, bawaan `true` |

## Contoh pemakaian

Mulai pekerjaan:

```bash
curl -s -X POST http://127.0.0.1:8787/v1/jobs \
  -F 'modul=@Modul_Praktikum_5.pdf' \
  -F 'lkp=@LKP_Modul_5.docx' \
  -F 'identitas={"nama":"Nama Mahasiswa","nim":"1234567890","kelas":"B","modul":"5","matakuliah":"Praktikum Dasar Pemrograman"}'
```

Balasannya berisi `job_id`. Tanyakan kemajuannya:

```bash
curl -s http://127.0.0.1:8787/v1/jobs/<job_id>
```

Kalau `status` sudah `selesai`, unduh hasilnya:

```bash
curl -sL -o hasil.zip http://127.0.0.1:8787/v1/jobs/<job_id>/download
```

Periksa berkas C tanpa AI:

```bash
curl -s -X POST http://127.0.0.1:8787/v1/verify -F 'files=@latihan_01.c' -F 'masukan=5'
```

## Aturan yang dipegang

- Kode C wajib lolos `gcc -Wall -Wextra` tanpa error dan tanpa peringatan.
  Kalau belum lolos, kode dikirim balik ke AI untuk diperbaiki.
- Kolom Actual pada laporan diisi dari keluaran program saat dijalankan,
  bukan tulisan AI.
- Program dijalankan dengan batas waktu, batas memori, dan tanpa jaringan.
- Tulisan untuk dosen hanya memakai karakter yang ada di keyboard.
- Pengisian template docx tidak mengubah format: jumlah paragraf sebelum
  dan sesudah pengisian harus sama.

## Pengujian

```bash
python3 tests/run_tests.py
```

Pengujian memakai AI tiruan, jadi tidak butuh kunci dan tidak mengakses
internet. Isinya termasuk pengujian alur lengkap sampai terbentuknya ZIP dan
pengujian semua endpoint HTTP.

## Catatan

- Pekerjaan berjalan di latar belakang. Server boleh dihentikan, dan
  pekerjaan yang belum selesai akan ditandai gagal saat dinyalakan lagi.
- Jangan taruh kunci API di dalam kode. Pakai variabel lingkungan.
- Layanan ini tidak punya pembatasan pengguna. Kalau dibuka ke jaringan
  luas, isi `DASPRO_AUTH_TOKEN` dan taruh di belakang proxy.
