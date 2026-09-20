# Pakem Gaya C Daspro

Aturan gaya yang dipakai semua file `.c` skill ini. Contoh hidup di folder ini.

## Struktur file

- `#include <stdio.h>` paling atas, lalu `int main(void)`.
- File tugas wajib header komentar: Nama / NIM / Kelas / Modul / Deskripsi.
- Contoh: `contoh_latihan_01_guard.c`, `contoh_tugas_parkir.c`.

## Kondisional

- Blok `if` WAJIB `{}` walau satu baris. Tanpa `{}` multi-statement + `else`
 = `error: 'else' without a previous 'if'`.
- Guard invalid di ATAS, `return 1` sebelum hitung apa pun.
- `if-else-if` rentang mulai dari batas TERTINGGI (`>= 85` dulu).
 Dari bawah (`>= 50` dulu) menelan semua nilai besar = bug logika.
- Validasi dua sisi pakai `||` (`nilai < 0 || nilai > 100`).
 `&&` di sini mustahil true = validasi mati.
- `switch` hanya untuk kode diskret (`int` 1-4). Tiap `case` = `break`,
 selalu ada `default`. Kondisi/rentang di dalam `case` pakai `if`.
 Contoh: `contoh_switch_kalkulator.c` (guard nol di `case 4`).

## I/O

- `scanf` selalu `&`: `scanf("%d", &usia);` - tanpa `&` = alamat sampah / crash.
- `double` pakai `%lf` di `scanf`, `%.2f` di `printf` (uang selalu 2 desimal).
- Inisialisasi variabel harga/diskon (`= 0.0`) agar jalur invalid tak cetak sampah.

## Batas inklusif

- `>=` batas bawah inklusif: 60 lulus, 75 = B, 80 = Sedang.
- `> 100` (bukan `>= 100`) agar 100 tetap valid.
- Jangan tulis `if (x = 60)` - itu assignment (selalu true) + warning `-Wparentheses`.
