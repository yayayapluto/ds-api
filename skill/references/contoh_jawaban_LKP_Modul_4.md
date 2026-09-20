# Jawaban LKP Modul 4 - IF, IF-ELSE, ELSE-IF, IF DI DALAM IF, DAN SWITCH

> Nama: - / NIM: - / Kelas: -
> Sumber aturan: `Modul_Praktikum_4_Pernyataan_Kondisional - MHS - FINAL.pdf`
> Actual Output di bawah ini hasil eksekusi nyata (gcc, program di repo), bukan karangan.

---

## IV.1 Praktikum Terbimbing 1 - Status Kelulusan (`latihan_01.c`)

### Contoh pengujian (Actual diisi dari run)

| Nilai | Expected Output | Actual Output | Status |
| ----- | ----------------- | --------------------- | ------ |
| -5 | Nilai tidak valid | `Nilai tidak valid.` | Sesuai |
| 0 | Belum lulus | `Status: Belum lulus` | Sesuai |
| 59.99 | Belum lulus | `Status: Belum lulus` | Sesuai |
| 60 | Lulus | `Status: Lulus` | Sesuai |
| 100 | Lulus | `Status: Lulus` | Sesuai |
| 105 | Nilai tidak valid | `Nilai tidak valid.` | Sesuai |

### Pertanyaan analisis

1. **Mengapa validasi dilakukan sebelum penentuan kelulusan?**
  Agar input di luar 0-100 tidak pernah masuk ke cabang Lulus/Belum lulus. `if-else-if` berhenti di kondisi pertama yang true, jadi guard invalid di atas menyaring sampah sebelum klasifikasi.

2. **Mengapa digunakan operator `||`?**
  Kondisi invalid adalah gabungan dua sisi: `< 0 ATAU > 100`. Satu nilai cukup memenuhi salah satunya untuk dinyatakan invalid. Kalau pakai `&&`, tidak ada angka yang sekaligus `< 0 DAN > 100`, kondisi mati total.

3. **Apa yang terjadi apabila validasi ditempatkan setelah kondisi kelulusan?**
  Nilai invalid bocor ke kategori. Contoh `105 >= 60` true -> tercetak `Lulus`. Contoh `-5` jatuh ke `else` -> tercetak `Belum lulus`. Pesan invalid tidak pernah keluar.

4. **Mengapa nilai 60 dinyatakan lulus?**
  Batas kelulusan `nilai >= 60.0`, dan 60 memenuhi `>=`. Kalau ditulis `> 60`, 60 jadi Belum lulus - melanggar aturan modul.

5. **Apa perbedaan `> 100` dan `>= 100`?**
  `> 100`: 100 masih valid (Lulus). `>= 100`: 100 ikut dibuang sebagai invalid. Aturan modul: 100 valid, jadi yang benar `> 100`.

6. **Apakah 59.99 termasuk lulus?**
  Tidak. `59.99 >= 60.0` false -> `Belum lulus`. Batas tegas di 60, tidak ada pembulatan.

7. **Berapa banyak kemungkinan jalur keluaran?**
  3 jalur, saling eksklusif: (a) tidak valid, (b) Lulus, (c) Belum lulus. Satu eksekusi tepat satu jalur.

---

## IV.2 Praktikum Terbimbing 2 - Huruf Mutu (`latihan_02.c`)

### Pengujian nilai batas

| Input | Expected Huruf Mutu | Actual Output | Status |
| --- | --- | --- | --- |
| 0 | E | `Nilai akhir : 0.00`, `Huruf mutu : E` | Sesuai |
| 49.99 | E | `Nilai akhir : 49.99`, `Huruf mutu : E` | Sesuai |
| 50 | D | `Nilai akhir : 50.00`, `Huruf mutu : D` | Sesuai |
| 64.99 | D | `Nilai akhir : 64.99`, `Huruf mutu : D` | Sesuai |
| 65 | C | `Nilai akhir : 65.00`, `Huruf mutu : C` | Sesuai |
| 74.99 | C | `Nilai akhir : 74.99`, `Huruf mutu : C` | Sesuai |
| 75 | B | `Nilai akhir : 75.00`, `Huruf mutu : B` | Sesuai |
| 85 | A | `Nilai akhir : 85.00`, `Huruf mutu : A` | Sesuai |
| -1 / 101 | (tidak valid) | `Nilai tidak valid.` + `return 1` | Sesuai |

### Pertanyaan analisis

1. **Mengapa kondisi dimulai dari nilai tertinggi?**
  `else-if` menang di kondisi pertama yang true. Dari atas (`>= 85` dulu), nilai 90 langsung terkunci A. Kalau dari bawah (`>= 50` dulu), 90 sudah menang di D dan cabang A tidak pernah tercapai.

2. **Hasil untuk 84.99?**
  B. `84.99 >= 85` false, `>= 75` true -> B. Bukti batas atas B eksklusif di 85.

3. **Hasil untuk 75?**
  B. `75 >= 85` false, `75 >= 75` true -> B. Batas bawah inklusif (`>=`).

4. **Hasil untuk 49.99?**
  E. Semua cabang `>= 50` gagal -> jatuh ke `else` -> E.

5. **Tujuan `return 1;` setelah input invalid?**
  Stop total. Tanpa itu program lanjut klasifikasi dan mencetak huruf mutu palsu untuk input sampah. `return 1` juga sinyal exit-status non-nol (error) ke OS.

6. **Apakah seluruh rentang 0-100 ditangani?**
  Ya. A (85-100), B (75-<85), C (65-<75), D (50-<65), E (0-<50). Tidak ada lubang; batas atas tiap cabang dijamin oleh kegagalan cabang di atasnya.

7. **Apakah ada rentang tumpang tindih?**
  Tidak secara eksekusi. Secara teks `>= 75` dan `>= 85` memang overlap, tapi `else-if` membuat yang bawah hanya diperiksa jika yang atas gagal - jadi partisi bersih.

---

## IV.3 Praktikum Terbimbing 3 - Kalkulator `switch` (`latihan_03.c`)

### Pengujian jalur eksekusi

| TC | Pilihan | Angka 1 | Angka 2 | Expected Result | Actual Result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 10 | 5 | 15.00 | `Hasil: 15.00` | Sesuai |
| 2 | 2 | 10 | 5 | 5.00 | `Hasil: 5.00` | Sesuai |
| 3 | 3 | 10 | 5 | 50.00 | `Hasil: 50.00` | Sesuai |
| 4 | 4 | 10 | 5 | 2.00 | `Hasil: 2.00` | Sesuai |
| 5 | 4 | 10 | 0 | Pembagian dengan nol tidak diperbolehkan. | sama persis | Sesuai |
| 6 | 7 | 10 | 5 | Pilihan tidak tersedia. | sama persis | Sesuai |

### Pertanyaan analisis

1. **Mengapa `switch` sesuai?**
  Pilihan berupa nilai diskret tunggal (`int` 1-4). `switch-case` memetakan satu ekspresi ke cabang/menu secara langsung; `if-else` rantai perbandingan satu-satu lebih bertele-tele untuk kasus ini.

2. **Mengapa pembagian butuh pemeriksaan tambahan?**
  Pembagi nol secara matematis tak terdefinisi dan crash (`SIGFPE` untuk integer; `inf` sesat untuk float). Guard `if (angka_2 != 0.0)` mencegah operasi sebelum terjadi.

3. **Apa jika `break` setelah `case 1` dihapus?**
  Jalan terus ke case berikutnya: hasil penjumlahan dicetak, lalu program lanjut ke `case 2` dan mencetak hasil pengurangan juga. Satu pilihan -> dua output.

4. **Apa jika pengguna memilih 7?**
  Masuk `default` -> `Pilihan tidak tersedia.` Tanpa `default`, program diam tanpa pesan - user bingung.

5. **Apakah `switch` bisa langsung memeriksa `angka_2 != 0`?**
  Tidak. `case` hanya label nilai konstan (`case 1:`, `case 4:`), bukan ekspresi kondisi. Pengecekan rentang/kondisi wilayah `if`.

6. **Mengapa `if` dipakai di dalam `case 4`?**
  Karena itu satu-satunya cabang yang punya sub-kondisi (pembagi nol atau tidak). Pola `switch` (pilih operasi) + `if` di dalam (validasi khusus cabang itu) - gabungan yang tepat guna.

7. **Berapa banyak jalur eksekusi?**
  6 jalur: case 1, 2, 3, case 4-berhasil, case 4-gagal (nol), default. Satu run tepat satu jalur.

---

## V.1 Tracing (`tracing.c`: if di dalam if untuk nilai dan kehadiran)

### Tracing 1 - kondisi awal (`nilai = 78, kehadiran = 80`)

| Langkah | Kondisi/Pernyataan | nilai | kehadiran | status | Hasil Kondisi |
| --- | --- | --- | --- | --- | --- |
| 1 | `nilai = 78` | 78 | - | - | - |
| 2 | `kehadiran = 80` | 78 | 80 | - | - |
| 3 | `nilai >= 75` | 78 | 80 | - | true |
| 4 | `kehadiran >= 75` | 78 | 80 | - | true |
| 5 | `status = 'L'` | 78 | 80 | L | - |

**Prediksi output:** `Status: L`

### Tracing 2 - kehadiran diubah 70 (`nilai = 78, kehadiran = 70`)

| Langkah | Kondisi/Pernyataan | nilai | kehadiran | status | Hasil Kondisi |
| --- | --- | --- | --- | --- | --- |
| 1 | `nilai = 78` | 78 | - | - | - |
| 2 | `kehadiran = 70` | 78 | 70 | - | - |
| 3 | `nilai >= 75` | 78 | 70 | - | true |
| 4 | `kehadiran >= 75` | 78 | 70 | - | false |
| 5 | `status = 'T'` (else dalam) | 78 | 70 | T | - |

**Prediksi output:** `Status: T`

### Tracing 3 - nilai diubah 60 (`nilai = 60, kehadiran = 80`)

| Langkah | Kondisi/Pernyataan | nilai | kehadiran | status | Hasil Kondisi |
| --- | --- | --- | --- | --- | --- |
| 1 | `nilai = 60` | 60 | - | - | - |
| 2 | `kehadiran = 80` | 60 | 80 | - | - |
| 3 | `nilai >= 75` | 60 | 80 | - | false |
| 4 | `status = 'T'` (else luar, kehadiran tidak diperiksa) | 60 | 80 | T | - |

**Prediksi output:** `Status: T`

### Perbandingan jalur ketiga tracing

- Tracing 1: luar true -> dalam true -> `'L'`. Satu-satunya jalur lulus.
- Tracing 2: luar true -> dalam false -> `'T'` (gagal di kehadiran).
- Tracing 3: luar false -> langsung `'T'` (kehadiran tidak pernah dicek, karena kondisi luar sudah gagal maka cabang dalam tidak dijalankan).
- Output aktual run kondisi awal: `Status: L` - cocok dengan prediksi Tracing 1.

---

## V.2 Eksperimen (`eksperimen.c`, basis `nilai = 75`, `if (nilai >= 60)`)

| No. | Perubahan | Prediksi | Hasil Aktual | Error/Warning | Penjelasan |
| --- | --- | --- | --- | --- | --- |
| 1 | `>= 60` -> `> 60` | Tetap `Lulus.` (75 > 60 true) | `Lulus.` | bersih | 75 di atas kedua batas; beda baru terlihat di nilai = 60 |
| 2 | `nilai` -> 60 | `Lulus.` (60 >= 60 true) | `Lulus.` | bersih | Bukti batas inklusif |
| 3 | `>=` -> `<=` | `Belum lulus.` (75 <= 60 false) | `Belum lulus.` | bersih | Arti kondisi terbalik total |
| 4 | `==` -> `=` (`if (nilai = 60)`) | `Lulus.` paksa + warning | `Lulus.` | `warning: suggest parentheses around assignment used as truth value [-Wparentheses]` (terverifikasi) | Ini assignment, bukan banding. `nilai` jadi 60, nilai ekspresi 60 = true -> selalu Lulus berapa pun input awal |
| 5 | Hapus kurung kurawal blok if | Tetap jalan normal | `Lulus.` | bersih | Satu pernyataan boleh tanpa `{}`; gaya modul tetap mewajibkan `{}` agar aman |
| 6 | Dua pernyataan tanpa `{}` + `else` | **Compile error** | gagal kompilasi | `error: 'else' without a previous 'if'` (terverifikasi) | `printf` kedua memutus ikatan if-else; `else` jadi yatim. Bukti kenapa `{}` wajib untuk multi-statement |
| 7 | Kategori dari batas terendah (`>= 50` dulu) | Nilai 90 salah jadi D | D untuk 90 (sesuai contoh modul) | bersih (bug logika, bukan sintaks) | Cabang pertama yang true menang; batas rendah menelan semua nilai besar |
| 8 | Hapus `break` satu case | Jalan terus ke case berikutnya, dua output | dua `printf` keluar sekaligus | `warning: this statement may fall through [-Wimplicit-fallthrough=]` (terverifikasi di debugging_b4) | Tanpa `break`, eksekusi nyelonong ke case berikut |
| 9 | Hapus `default` | Pilihan liar diam saja | tidak ada output | bersih | Tidak ada cabang cocok + tidak ada fallback = sunyi; user tanpa pesan |
| 10 | `(nilai >= 0) && (nilai <= 100)` | true untuk 75, lanjut klasifikasi | true | bersih | Validasi rentang gabungan AND: kedua sisi harus true; pola guard standar modul |

---

## VI. Debugging Challenge (`debugging_b4.c` -> `debugging.c`)

### Hasil kompilasi awal (`gcc -Wall -Wextra debugging_b4.c`)

```text
warning: format '%d' expects argument of type 'int *', but argument 2 has type 'int' [-Wformat=] (baris 8)
warning: this statement may fall through [-Wimplicit-fallthrough=] (baris 37 -> case 2)
warning: 'usia' is used uninitialized [-Wuninitialized] (baris 8)
```

### Tabel debugging

| No. | Bagian yang Salah | Jenis Kesalahan | Penyebab | Perbaikan |
| --- | --- | --- | --- | --- |
| 1 | Baris 8: `scanf("%d", usia);` | Runtime | `scanf` butuh alamat (`int*`). Tanpa `&`, input ditulis ke alamat sampah; `usia` tidak terisi / crash | `scanf("%d", &usia);` |
| 2 | Baris 14: `if (usia < 0 && usia > 120)` | Logic | `&&` mustahil: tidak ada angka yang sekaligus `< 0 DAN > 120`, validasi mati | `if ((usia < 0) \|\| (usia > 120))` |
| 3 | `case 1` tanpa `break` (baris 36-37) | Logic | Jalan terus ke `case` berikutnya: `harga = 50000` langsung ditimpa `100000`; Reguler bayar harga Premium | Tambah `break;` setelah `harga = 50000;` |
| 4 | `double harga;` tanpa inisialisasi | Runtime | Jika tiket invalid, `harga` tidak pernah diisi tapi tetap dicetak -> nilai sampah | `double harga = 0.0;` + jangan cetak saat invalid |
| 5 | Setelah `Usia tidak valid` program lanjut | Logic | Tidak ada `return`; usia sampah tetap dikategorikan + dihitung harga | `printf(...); return 1;` |
| 6 | `default` + `printf harga` unconditional (baris 41-44) | Logic | Tiket invalid hanya warning lalu tetap cetak `Harga tiket: <sampah>` | `default: ...; tiket_valid = 0; break;` lalu `if (tiket_valid) printf harga;` (atau `return 1` di default) |

### Pengujian setelah perbaikan (program `debugging.c`, hasil run nyata)

| TC | Usia | Jenis Tiket | Expected Result | Actual Result | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | 25 | 1 | Dewasa; harga reguler | `Kategori: Dewasa`, `Harga tiket: 50000.00` | Sesuai |
| 2 | 65 | 2 | Lansia; harga premium | `Kategori: Lansia`, `Harga tiket: 100000.00` | Sesuai |
| 3 | 15 | 1 | Remaja; harga reguler | `Kategori: Remaja`, `Harga tiket: 50000.00` | Sesuai |
| 4 | -1 | 1 | Usia tidak valid | `Usia tidak valid.` (stop, tanpa kategori/harga) | Sesuai |
| 5 | 25 | 9 | Jenis tiket tidak valid | `Kategori: Dewasa`, `Jenis tiket tidak valid.` (tanpa harga) | Sesuai |

### Perubahan terpenting agar tidak lanjut hitung saat input invalid

Berhenti lebih awal: `return 1;` tepat setelah `Usia tidak valid`, dan flag `tiket_valid` yang menahan `printf("Harga tiket...")` hanya untuk tiket 1/2. Tanpa dua ini, program memproses data sampah dan mencetak harga fiktif - inti bugnya bukan angka harga, melainkan alur yang tidak pernah berhenti.

---

## VII. Latihan Mandiri

### Level 1 - Positif/Negatif/Nol (`level_01.c`)

| TC | Input | Expected Kategori | Actual Output | Status |
| --- | --- | --- | --- | --- |
| 1 | -8 | Bilangan negatif | `Kategori: Bilangan negatif` | Sesuai |
| 2 | 0 | Nol | `Kategori: Nol` | Sesuai |
| 3 | 9 | Bilangan positif | `Kategori: Bilangan positif` | Sesuai |

### Level 2 - Genap/Ganjil (`level_02.c`, `bilangan % 2 == 0`)

| TC | Input | Expected Kategori | Actual Output | Status |
| --- | --- | --- | --- | --- |
| 1 | 17 | Ganjil | `17 merupakan bilangan ganjil.` | Sesuai |
| 2 | 18 | Genap | `18 merupakan bilangan genap.` | Sesuai |
| 3 | 0 | Genap | `0 merupakan bilangan genap.` | Sesuai |
| 4 | -3 | Ganjil | `-3 merupakan bilangan ganjil.` | Sesuai |

### Level 3 - Validasi + Huruf Mutu (`level_03.c`)

| Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- |
| -1 | Tidak valid | `Nilai tidak valid.` | Sesuai |
| 0 | E | `Huruf mutu: E` | Sesuai |
| 49.99 | E | `Huruf mutu: E` | Sesuai |
| 50 | D | `Huruf mutu: D` | Sesuai |
| 65 | C | `Huruf mutu: C` | Sesuai |
| 75 | B | `Huruf mutu: B` | Sesuai |
| 85 | A | `Huruf mutu: A` | Sesuai |
| 101 | Tidak valid | `Nilai tidak valid.` | Sesuai |

### Challenge - Tahun Kabisat (`level_04.c`)

Aturan: habis dibagi 400 -> kabisat; habis dibagi 100 (tapi bukan 400) -> bukan; habis dibagi 4 (tapi bukan 100) -> kabisat; selain itu bukan. Urutan `if` persis urutan itu.

| Tahun | Expected Result | Actual Result | Status |
| --- | --- | --- | --- |
| 2024 | Kabisat | `2024 merupakan tahun kabisat.` | Sesuai |
| 2023 | Bukan kabisat | `2023 bukan tahun kabisat.` | Sesuai |
| 2000 | Kabisat | `2000 merupakan tahun kabisat.` | Sesuai |
| 1900 | Bukan kabisat | `1900 bukan tahun kabisat.` | Sesuai |

### Kategori Kecepatan (`latihan_bonus_04.c`)

Aturan: `< 40` Lambat; `40-80` Sedang (`<= 80`); `81-120` Cepat (`<= 120`); `> 120` Sangat Cepat. Jebakan batas: 80 harus Sedang, jadi kondisi kedua `<= 80` bukan `< 80`.

| TC | Kecepatan | Expected Kategori | Actual Output | Status |
| --- | --- | --- | --- | --- |
| 1 | 0 | Lambat | `Kategori : Lambat` | Sesuai |
| 2 | 30 | Lambat | `Kategori : Lambat` | Sesuai |
| 3 | 40 | Sedang | `Kategori : Sedang` | Sesuai |
| 4 | 80 | Sedang | `Kategori : Sedang` | Sesuai |
| 5 | 81 | Cepat | `Kategori : Cepat` | Sesuai |
| 6 | 120 | Cepat | `Kategori : Cepat` | Sesuai |
| 7 | 150 | Sangat Cepat | `Kategori : Sangat Cepat` | Sesuai |

---

## VIII. Pengujian Struktur Kondisional (program huruf mutu, 12 kasus)

| No. | Input | Expected Output | Actual Output | Status |
| --- | --- | --- | --- | --- |
| 1 | -1 | Tidak valid | `Nilai tidak valid.` | Sesuai |
| 2 | 0 | E | `Huruf mutu : E` | Sesuai |
| 3 | 49.99 | E | `Huruf mutu : E` | Sesuai |
| 4 | 50 | D | `Huruf mutu : D` | Sesuai |
| 5 | 64.99 | D | `Huruf mutu : D` | Sesuai |
| 6 | 65 | C | `Huruf mutu : C` | Sesuai |
| 7 | 74.99 | C | `Huruf mutu : C` | Sesuai |
| 8 | 75 | B | `Huruf mutu : B` | Sesuai |
| 9 | 84.99 | B | `Huruf mutu : B` | Sesuai |
| 10 | 85 | A | `Huruf mutu : A` | Sesuai |
| 11 | 100 | A | `Huruf mutu : A` | Sesuai |
| 12 | 101 | Tidak valid | `Nilai tidak valid.` | Sesuai |

**Kesimpulan pengujian:** tiap jalur (normal + tiap batas atas/bawah + invalid dua sisi) menghasilkan tepat satu output yang benar. Tidak ada lubang rentang, tidak ada overlap eksekusi, input invalid selalu ditolak sebelum klasifikasi.

---

## IX. Tugas Praktikum - Tarif Parkir (`tugas_modul_04_soal1.c`)

### 1. Data Input

| Data Input | Nama Variabel | Tipe Data | Keterangan |
| --- | --- | --- | --- |
| Jenis kendaraan | `pilihan` | `int` | Kode 1 Motor, 2 Mobil, 3 Bus |
| Durasi parkir | `durasi` | `int` | Jam, minimal 1 |
| Status member | `status` | `int` | 0 bukan member, 1 member |

### 2. Ketentuan Tarif (tabel keputusan)

| Jenis Kendaraan | Jam Pertama | Jam Berikutnya | Tarif Maksimal | Validasi/Ketentuan |
| --- | --- | --- | --- | --- |
| Sepeda motor | Rp3.000 | Rp1.500 | Rp15.000 | Kode 1; durasi >= 1; cap maksimal; diskon 10% jika member + durasi >= 2 |
| Mobil | Rp5.000 | Rp3.000 | Rp30.000 | Kode 2; aturan sama |
| Bus | Rp10.000 | Rp5.000 | Rp60.000 | Kode 3; aturan sama |

Kode kendaraan di luar 1-3 -> `Jenis kendaraan tidak valid.` Status selain 0/1 -> `Status member tidak valid.` Durasi < 1 -> `Durasi tidak valid.` Semua invalid `return 1` sebelum hitung.

### 3. Proses Perhitungan

1. `switch(pilihan)` set tarif jam pertama / per jam / maksimal; `default` -> pesan + `return 1`.
2. Validasi `durasi < 1` -> pesan + `return 1`. Validasi `status` bukan 0/1 -> pesan + `return 1`.
3. `if (durasi == 1)` tarif awal = jam pertama, `else` tarif awal = jam pertama + (durasi-1) x tarif per jam.
4. `if (tarif_awal > tarif_maksimal)` tarif awal = maksimal (cap).
5. `if ((status == 1) && (durasi >= 2))` diskon = 10% x tarif awal (kondisi gabungan; hanya satu `if`, tanpa nested dalam).
6. Total = tarif awal - diskon. Cetak rincian `%.2f`.

### 5. Struktur Kondisional yang Digunakan

- [x] `switch` jenis kendaraan + tarif
- [x] `if-else` tarif berdasar durasi
- [x] `if` tarif maksimal
- [x] kondisi gabungan `(status == 1) && (durasi >= 2)` untuk diskon
- [x] validasi kendaraan / durasi / status member (masing-masing `return 1`)

### 7. Analisis IPO

| Komponen | Uraian |
| --- | --- |
| Input | `pilihan` (1-3), `durasi` (int >= 1), `status` (0/1) via `scanf` |
| Process | switch tarif -> validasi -> tarif awal (if-else durasi) -> cap maksimal (if) -> diskon member (if gabungan) -> total |
| Output | Rincian: jenis kendaraan, durasi, tarif awal, diskon, total bayar (`Rp%.2f`) |

### Tabel keputusan (kondisi -> tindakan)

| Kondisi/Variabel | Kemungkinan Nilai | Keputusan/Tindakan |
| --- | --- | --- |
| Jenis kendaraan | 1 / 2 / 3 / selain itu | Motor (3000/1500/15000) / Mobil (5000/3000/30000) / Bus (10000/5000/60000) / `Jenis kendaraan tidak valid.` + `return 1` |
| Durasi valid | < 1 / >= 1 | `Durasi tidak valid.` + `return 1` / lanjut hitung |
| Durasi = 1 | ya / tidak | `tarif_awal` = tarif jam pertama / lanjut uji Durasi > 1 |
| Durasi > 1 | ya / tidak | `tarif_awal` = jam pertama + (durasi-1) x per jam / - (sudah ditangani cabang = 1) |
| Tarif > maksimum | ya / tidak | `tarif_awal` = `tarif_maksimal` / biarkan |
| Member dan durasi >= 2 | status = 1 & durasi >= 2 / selain itu | diskon = 10% x `tarif_awal` / diskon = 0 |

### Trace table (data uji: Mobil, 5 jam, member - expected total Rp15.300)

| Langkah | Kondisi/Pernyataan | Variabel yang Berubah | Nilai Setelah Langkah |
| --- | --- | --- | --- |
| 1 | input pilihan=2, durasi=5, status=1 | pilihan, durasi, status | 2, 5, 1 |
| 2 | switch case 2 | jam pertama, per jam, maksimal | 5000, 3000, 30000 |
| 3 | durasi < 1? | - | false, lanjut |
| 4 | status valid? | - | true (1), lanjut |
| 5 | durasi == 1? | - | false -> tarif_awal = 5000 + 4x3000 |
| 6 | tarif_awal | tarif_awal | 17000 |
| 7 | tarif_awal > 30000? | - | false |
| 8 | status==1 && durasi>=2? | diskon | true -> 1700 |
| 9 | total = 17000 - 1700 | total_bayar | 15300 |
| 10 | cetak rincian | - | Total bayar Rp15300.00 |

### Tabel pengujian (10 kasus, Actual dari run nyata, kompilasi bersih tanpa warning)

| No. | Kendaraan | Durasi | Member | Expected Result | Actual Result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Motor | 1 | Tidak | Rp3.000 | `Tarif awal : Rp3000.00`, `Total bayar : Rp3000.00` | Sesuai |
| 2 | Motor | 2 | Tidak | Rp4.500 | `Tarif awal : Rp4500.00`, `Total bayar : Rp4500.00` | Sesuai |
| 3 | Motor | 2 | Ya | Rp4.050 | `Diskon : Rp450.00`, `Total : Rp4050.00` | Sesuai |
| 4 | Mobil | 5 | Ya | Rp15.300 | `Tarif awal : Rp17000.00`, `Diskon : Rp1700.00`, `Total : Rp15300.00` | Sesuai |
| 5 | Mobil | 20 | Tidak | Rp30.000 (cap) | `Tarif awal : Rp30000.00` (5000+19x3000=62000 -> dicap) | Sesuai |
| 6 | Bus | 3 | Tidak | Rp20.000 | `Tarif awal : Rp20000.00`, `Total : Rp20000.00` | Sesuai |
| 7 | Bus | 20 | Ya | Rp54.000 | `Tarif awal : Rp60000.00` (cap), `Diskon : Rp6000.00`, `Total : Rp54000.00` | Sesuai |
| 8 | Kode 5 | 3 | Tidak | Input tidak valid | `Jenis kendaraan tidak valid.` (stop) | Sesuai |
| 9 | Mobil | 0 | Tidak | Durasi tidak valid | `Durasi tidak valid.` (stop) | Sesuai |
| 10 | Mobil | 3 | Status 4 | Status tidak valid | `Status member tidak valid.` (stop) | Sesuai |

Kompilasi: `gcc -Wall -Wextra` bersih, tanpa error/warning.

### 3. Status Diskon Member (`tugas_modul_04_soal2.c`)

Aturan: `switch` kode 1 -> 5%, 2 -> 10%, 3 -> 15%, default -> 0%. `harga_akhir = harga_awal - harga_awal x persen/100.0`. Uang selalu `%.2f`. Kompilasi bersih.

| TC | Kode Member | Harga Awal | Expected Diskon | Expected Harga Akhir | Actual Result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 100000 | 5% | Rp95000.00 | `Diskon : 5%`, `Harga akhir : Rp95000.00` | Sesuai |
| 2 | 3 | 200000 | 15% | Rp170000.00 | `Diskon : 15%`, `Harga akhir : Rp170000.00` | Sesuai |
| 3 | 9 | 50000 | 0% | Rp50000.00 | `Diskon : 0%`, `Harga akhir : Rp50000.00` (via default) | Sesuai |

---

## Refleksi

1. **Bagian kondisi tersulit di tugas parkir?**
  Urutan validasi vs perhitungan. Validasi kendaraan/durasi/status harus tuntas + `return 1` sebelum satu pun rupiah dihitung; kalau cap maksimal atau diskon dikerjakan dulu, data invalid ikut terhitung.

2. **Test case paling membantu menemukan kesalahan logika?**
  Kasus batas dan cap: Motor 2 jam member vs non-member (bedakan syarat `durasi >= 2`), Mobil 20 jam (buktikan cap 30.000 menelan 62.000), dan ketiga invalid (buktikan stop, bukan sekadar pesan).

3. **Perbedaan switch, if-else, dan if di dalam if setelah tugas?**
  `switch` untuk satu nilai diskret (kode kendaraan/member) - bersih. `if-else-if` untuk rentang/threshold (durasi, tarif, nilai). Kondisi gabungan `&&`/`\|\|` menggantikan if di dalam if yang dangkal; if di dalam if hanya layak kalau cabang dalam memang tidak relevan sebelum cabang luar lolos.

---

## Pernyataan penggunaan AI

Menggunakan AI: Saya menggunakan AI untuk membantu menjelaskan operator logika validasi, perilaku jalan terus ke case berikutnya pada switch, dan menyusun prediksi eksperimen. Hasil tersebut saya periksa melalui tracing manual, kompilasi `gcc -Wall -Wextra`, pengujian nilai batas, dan perbandingan dengan aturan pada soal/modul.
