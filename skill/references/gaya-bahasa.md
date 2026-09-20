# Pakem Gaya Bahasa Laporan

Aturan bahasa untuk semua tulisan skill ini: `jawaban_LKP_Modul_X.md`, HTML
copyable, komentar kode, dan pesan `printf` di soal. Contoh hidup:
`contoh_jawaban_LKP_Modul_4.md`.

## Siapa yang baca

Mahasiswa semester 1 Informatika yang baru kenal C. Pembaca ini belum tentu
paham istilah teknis. Jadi tulis seperti kakak tingkat yang menjelaskan ke
adik tingkat, bukan seperti dokumentasi resmi.

## Larangan istilah teknis

Ganti istilah teknis ini dengan bahasa sehari-hari. Kalau memang harus pakai
nama fitur C (misal `switch`), sebut namanya lalu jelaskan artinya dengan
kalimat biasa.

| Jangan tulis | Tulis |
| --- | --- |
| `early-exit`, `early return` | program langsung berhenti, `return 1` di atas |
| `guard clause`, `guard input` | pemeriksaan input tidak valid di bagian atas |
| `short-circuit` | kondisi kedua tidak dicek kalau kondisi pertama sudah gagal |
| `fall-through` | jalan terus ke `case` berikutnya |
| `else-if chain`, rantai kondisi | deretan `if-else-if` |
| `nested if` | `if` di dalam `if` |
| boundary, `edge case` | nilai batas |
| `tradeoff` | pilihan yang dipilih dan alasannya |
| `best practice`, `clean code` | cara penulisan yang disarankan modul |
| `garbage value`, UB, `undefined behavior` | nilai sampah, nilai yang tidak jelas isinya |
| `runtime error` | error saat program dijalankan |
| compile error | gagal dikompilasi, muncul error saat `gcc` |
| `exit status` | kode keluar program |
| `conditional statement` | pernyataan kondisional (`if`, `switch`) |
| increment, decrement | nilai bertambah, nilai berkurang |
| iterasi, loop | perulangan (`for`, `while`) |
| implementasi | cara membuatnya, kodenya |
| parameter, argumen | nilai yang dikirim ke fungsi |
| return value | nilai yang dikembalikan fungsi |
| flow, alur eksekusi | jalan program dari atas ke bawah |

Kata Inggris yang tetap boleh dipakai karena sudah jadi nama di soal:
`if`, `else`, `else-if`, `switch`, `case`, `break`, `default`, `printf`,
`scanf`, `int`, `double`, `char`, dan nama file atau variabel di kode.

## Larangan karakter

Tulis hanya karakter yang ada di keyboard biasa. Karakter di bawah ini
dilarang di semua tulisan laporan.

Kolom "Karakter terlarang" ditulis pakai nama Unicode dan kode heksa,
karena karakter aslinya memang tidak boleh ditulis. Kalau tulisan kamu
memuat salah satunya, ganti dengan versi keyboard di kolom terakhir.

| Nama Unicode | Kode | Ganti dengan |
| --- | --- | --- |
| Rightwards arrow | U+2192 | `->` (minus, lalu lebih besar) |
| Leftwards arrow | U+2190 | `<-` |
| Left right arrow | U+2194 | `<->` |
| Greater-than or equal to | U+2265 | `>=` |
| Less-than or equal to | U+2264 | `<=` |
| Not equal to | U+2260 | `!=` |
| Multiplication sign | U+00D7 | huruf `x` atau `*` |
| Minus sign | U+2212 | `-` (minus biasa) |
| En dash | U+2013 | `-` (minus biasa) |
| Em dash | U+2014 | `-` (minus biasa) |
| Horizontal ellipsis | U+2026 | `...` (tiga titik biasa) |
| Left double quotation mark | U+201C | `"` kutip lurus |
| Right double quotation mark | U+201D | `"` kutip lurus |
| Left single quotation mark | U+2018 | `'` kutip lurus |
| Right single quotation mark | U+2019 | `'` kutip lurus |
| Bullet | U+2022 | `-` (minus biasa) |
| Degree sign | U+00B0 | tulis kata "derajat" |
| Non-breaking space | U+00A0 | spasi biasa |
| No-break space tipis atau spasi aneh lain | U+2009, U+202F | spasi biasa |

Karakter-karakter itu muncul sendiri saat AI menulis, jadi harus diperiksa
habis, bukan cuma dipercaya.

Contoh kalimat benar:

- Nilai 90 masuk ke cabang pertama, jadi huruf mutunya A.
- Setelah `return 1`, program berhenti dan baris hitung tidak dijalankan.
- Kondisi `nilai >= 60` bernilai true, maka tercetak `Lulus`.
- Urutan cabang: `>= 85` dulu, lalu `>= 75`, lalu `>= 65`.
- Rumus: total = (durasi - 1) * tarif_per_jam.

## Cara menulis kalimat

- Kalimat pendek. Satu kalimat satu ide. Maksimal sekitar 25 kata.
- Kalimat aktif: "program mencetak", bukan "output dihasilkan oleh program".
- Sebut nama variabel aslinya dengan backtick: `nilai`, `durasi`, `status`.
- Tulis angka apa adanya: 60, bukan "enam puluh", kalau itu nilai soal.
- Uang dua angka belakang koma: Rp3000.00.
- Jangan pakai tanda seru. Jangan pakai emoji.
- Hindari kata: "merupakan", "tersebut", "dimana", "sedangkan untuk",
  "secara signifikan", "robust", "optimal", "kompleks", "efisien".
  Ganti: "adalah", "itu", "di sini", "kalau", "terlihat jelas", "kuat",
  "paling pas", "berbelit", "hemat waktu".
- Kalau menjelaskan sebab, pakai kata "karena". Kalau menjelaskan akibat,
  pakai "jadi" atau "maka".
- Istilah "line" tulis "baris". "output" tulis "keluaran" (kecuali di judul
  tabel Expected Output yang sudah jadi nama kolom, boleh tetap).
- Tulis "test case" sebagai "kasus uji". "input" sebagai "masukan" atau
  "nilai yang dimasukkan".

## Contoh sebelum dan sesudah

Sebelum (terlalu teknis):

> `Guard clause` di atas mencegah invalid value bocor ke tahap klasifikasi
> karena rangkaian else-if `short-circuit` pada kondisi true pertama.

Sesudah (bahasa mahasiswa):

> Pemeriksaan di bagian atas menahan nilai yang tidak valid supaya tidak
> ikut dihitung. Deretan `if-else-if` berhenti di kondisi pertama yang
> bernilai true, jadi nilai yang salah tidak sampai masuk kategori.

Sebelum:

> `Fall-through` pada `case 1` menyebabkan nilai variabel ditimpa oleh `case 2`.

Sesudah:

> `case 1` tidak punya `break`, jadi program jalan terus ke `case 2` dan
> nilai variabelnya ditimpa. Akibatnya tarif yang tercetak bukan tarif
> yang dipilih.

## Cek akhir sebelum lapor

1. Baca ulang laporan. Kalau ada kata yang kamu sendiri baru paham setelah
   kuliah tiga bulan, ganti.
2. Cari karakter non-keyboard:
   `python3 -c "import sys;s=open(sys.argv[1],encoding='utf-8').read();print([c for c in s if ord(c)>127])" jawaban_LKP_Modul_X.md`
   Hasilnya wajib list kosong `[]`.
3. Cek tiap tabel Expected dan Actual tetap diisi hasil run nyata, bukan
   karangan.
