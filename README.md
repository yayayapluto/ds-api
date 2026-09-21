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
  logbook.py         catatan layanan dan catatan tiap pekerjaan
  request.py         pembaca badan permintaan JSON dan multipart
  envfile.py         pembaca berkas .env
  web/               halaman web panel (html, css, js)
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

Cara paling gampang: salin contoh berkas pengaturan, lalu isi kuncinya.

```bash
cp .env.example .env     # lalu buka .env dan isi DASPRO_AI_API_KEY
python3 -m daspro_api --cek    # pastikan semuanya siap
python3 -m daspro_api          # mulai melayani di 127.0.0.1:8787
```

Isi `.env` dibaca otomatis. Berkas itu tidak ikut masuk git, jadi kunci API
tidak akan terunggah. Kalau berkasnya ditaruh di tempat lain, tunjuk
lokasinya dengan `--env /jalur/ke/berkas.env`. Untuk mengabaikan `.env`
sama sekali, pakai `--tanpa-env`.

Pengaturan juga bisa dikirim lewat variabel lingkungan seperti biasa. Nilai
dari terminal menang atas isi `.env`, jadi ini tetap jalan:

```bash
DASPRO_PORT=9000 python3 -m daspro_api
```

Penyedia lain yang memakai antarmuka sama bisa dipakai dengan mengganti
`DASPRO_AI_BASE_URL`, `DASPRO_AI_API_KEY`, dan `DASPRO_AI_MODEL`.

Layanan ini selalu memakai AI sungguhan. Tidak ada mode jawaban tiruan,
supaya kode C yang dikumpulkan tidak pernah karangan. Kalau kunci belum
diisi, layanan menolak jalan dan `--cek` memberi tahu apa yang kurang.
`--cek` sekaligus mengirim satu pertanyaan kecil ke layanan AI untuk
memastikan kunci dan alamatnya benar.

## Halaman web

Buka `http://127.0.0.1:8787/` di peramban. Halaman ini bisa dipakai untuk
seluruh pekerjaan tanpa mengetik perintah:

1. Isi penyedia, kunci API, dan nama model. Ada tombol uji koneksi.
   Langkah ini opsional kalau server sudah punya kunci sendiri.
2. Unggah modul dan template LKP.
3. Isi identitas, lalu tekan Mulai kerjakan.
4. Lihat kemajuan, lalu unduh hasilnya. Catatan pekerjaan dibuka di modal
   dan bisa diunduh terpisah, termasuk kalau pekerjaannya gagal.

Pemantauan kemajuan tidak langsung menyerah kalau satu permintaan gagal;
ia mencoba beberapa kali dulu. Kalau pemantauan benar-benar terlepas,
pekerjaannya tetap jalan di server dan bisa disambungkan lagi lewat tombol
"pantau" di baris riwayat pekerjaan.

Dokumentasi API ada di `http://127.0.0.1:8787/docs` (Swagger UI), dengan
berkas spesifikasinya di `/openapi.json`.

Kunci API disimpan hanya di peramban (localStorage), dan dikirim ke server
hanya saat pekerjaan berjalan. Server tidak menuliskannya ke berkas, tidak
memasukkannya ke catatan kemajuan, dan tidak pernah mengirimnya balik.
Endpoint `/health` hanya memberi tahu apakah kunci sudah terisi, bukan
isinya. Tombol Hapus di peramban menghilangkan kunci itu dari peramban.

Kalau kunci di halaman web diisi, kunci itu yang dipakai. Kalau kosong,
dipakai kunci milik server dari berkas `.env`.

## Pengaturan

Semua dibaca dari berkas `.env` atau variabel lingkungan. Nama tanpa awalan
`DASPRO_` juga diterima untuk kunci yang sudah biasa dipakai
(`OPENAI_API_KEY`).

| Variabel | Bawaan | Keterangan |
| --- | --- | --- |
| `DASPRO_HOST` | `127.0.0.1` | alamat yang didengarkan |
| `DASPRO_PORT` | `8787` | nomor port |
| `DASPRO_PORT_FALLBACK` | `10` | berapa port berurutan dicoba kalau port di atas dipakai |
| `DASPRO_DATA_DIR` | `./data` | tempat berkas kerja |
| `DASPRO_SKILL_DIR` | `./skill` | folder skill (skrip dan acuan gaya) |
| `DASPRO_AI_BASE_URL` | `https://api.openai.com/v1` | alamat layanan AI |
| `DASPRO_AI_API_KEY` | kosong | kunci layanan AI (wajib diisi) |
| `DASPRO_AI_MODEL` | `gpt-4o-mini` | nama model (wajib) |
| `DASPRO_AI_TIMEOUT` | `300` | batas waktu satu panggilan AI (detik) |
| `DASPRO_AI_MAX_TOKENS` | `32768` | batas panjang jawaban AI (model penalaran butuh jatah lega) |
| `DASPRO_AI_TEMPERATURE` | `0.2` | tingkat keacakan jawaban AI |
| `DASPRO_AI_RETRY` | `2` | berapa kali panggilan yang gagal sementara diulang |
| `DASPRO_GCC` | `gcc` | program kompilator |
| `DASPRO_RUN_TIMEOUT` | `5` | batas waktu menjalankan program (detik) |
| `DASPRO_MEMORY_MB` | `256` | batas memori program C |
| `DASPRO_MAX_UPLOAD_MB` | `32` | batas ukuran unggahan |
| `DASPRO_MAX_REPAIR` | `2` | berapa kali kode diperbaiki kalau gagal |
| `DASPRO_JOB_WORKERS` | `2` | berapa pekerjaan jalan bersamaan |
| `DASPRO_JOB_TTL_JAM` | `24` | umur hasil sebelum dibersihkan |
| `DASPRO_AUTH_TOKEN` | kosong | kalau diisi, wajib dikirim di header `Authorization` |
| `DASPRO_PUBLIC_BASE_URL` | kosong | alamat publik layanan, dipakai kalau ditautkan dari luar |

## Endpoint

| Metode | Jalur | Keterangan |
| --- | --- | --- |
| `GET` | `/` | halaman web panel pengerjaan |
| `GET` | `/health` | keadaan layanan, kesiapan skill, AI, dan gcc |
| `GET` | `/v1/skill` | daftar skrip dan acuan gaya yang dipakai |
| `POST` | `/v1/jobs` | unggah modul dan template, mulai pekerjaan |
| `GET` | `/v1/jobs` | daftar pekerjaan |
| `GET` | `/v1/jobs/{id}` | status, kemajuan, dan catatan tahap |
| `GET` | `/v1/jobs/{id}/result` | ringkasan hasil |
| `GET` | `/v1/jobs/{id}/download` | unduh berkas ZIP |
| `GET` | `/v1/jobs/{id}/files/{nama}` | unduh satu berkas hasil |
| `GET` | `/v1/jobs/{id}/log` | unduh catatan pekerjaan (teks) |
| `POST` | `/v1/jobs/{id}/cancel` | batalkan pekerjaan |
| `POST` | `/v1/ai/uji` | uji koneksi kredensial AI yang dikirim |
| `POST` | `/v1/verify` | kompilasi dan jalankan berkas `.c` |
| `POST` | `/v1/cek-bahasa` | periksa gaya bahasa laporan |
| `POST` | `/v1/docx/peta` | lihat tempat kosong di template docx |
| `POST` | `/v1/docx/isi` | isi template docx dari mapping |
| `GET` | `/docs` | halaman dokumentasi API (Swagger UI) |
| `GET` | `/openapi.json` | berkas spesifikasi OpenAPI |

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
internet. Berkas contoh di `tests/fixtures` dibuat ulang otomatis oleh
`tests/buat_fixture.py`, jadi cukup dijalankan sekali dengan perintah di
atas. Isinya termasuk pengujian alur lengkap sampai terbentuknya ZIP dan
pengujian semua endpoint HTTP.

## Catatan

- Pekerjaan berjalan di latar belakang. Server boleh dihentikan, dan
  pekerjaan yang belum selesai akan ditandai gagal saat dinyalakan lagi.
- Jangan taruh kunci API di dalam kode. Pakai variabel lingkungan.
- Layanan ini tidak punya pembatasan pengguna. Kalau dibuka ke jaringan
  luas, isi `DASPRO_AUTH_TOKEN` dan taruh di belakang proxy.
- Kredensial AI yang dikirim lewat halaman web hanya hidup selama pekerjaan
  berjalan. Tidak ada jalur yang menuliskannya ke disk.
- Halaman web hanya melayani berkas di dalam `daspro_api/web`. Permintaan
  yang mencoba keluar dari folder itu ditolak.
- Ada dua catatan: catatan harian layanan di `data/logs/daspro-<tanggal>.log`,
  dan catatan tiap pekerjaan di `data/jobs/<id>/job.log`. Nilai rahasia yang
  didaftarkan tidak pernah ikut tertulis, dan berkas yang terlalu besar
  dipotong dari depan.
- Kalau port yang diminta sudah dipakai, layanan mencoba port berikutnya
  sampai `DASPRO_PORT_FALLBACK` kali. Port yang benar-benar dipakai tertulis
  di baris "jalan di" saat layanan dinyalakan.
