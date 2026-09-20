# Format Laporan jawaban_LKP

Acuan penuh: `contoh_jawaban_LKP_Modul_4.md`. Versi HTML-nya: `contoh_copyable.html`.

## Struktur MD

1. H1 judul + blockquote identitas (Nama - NIM / Kelas) + sumber aturan + catatan Actual dari run nyata.
2. Per section (`## IV.1 ...`, `## V.1 ...`): tabel `Expected | Actual | Status`.
  Actual = stdout run verbatim dalam backtick.
3. `### Pertanyaan analisis`: format `N. **Pertanyaan?**` + jawaban paragraf di bawahnya
  (dipakai generator HTML untuk tombol copy Q/A terpisah).
4. Tracing: trace table `Langkah | Kondisi | nilai | ... | Hasil Kondisi` + `**Prediksi output:** ...`.
5. Eksperimen: tabel `No. | Perubahan | Prediksi | Hasil Aktual | Error/Warning | Penjelasan`.
6. Debugging: blok ```text warning gcc + tabel `Bagian yang Salah | Jenis | Penyebab | Perbaikan`

+ tabel pengujian TC + satu paragraf perubahan terpenting.
1. Tugas: Data Input (variabel/tipe), tabel keputusan tarif, IPO, trace table, tabel pengujian.
2. Tutup: `## Refleksi` (3 jawaban) + `## Pernyataan penggunaan AI`.

## Nilai batas wajib

+ Huruf mutu: `-1, 0, 49.99, 50, 65, 75, 85, 101`.
+ Kecepatan: `30, 40, 80, 81, 150` (80 = Sedang, jebakan `<= 80` vs `< 80`).
+ Parkir: 10 kasus (member vs non, cap maksimal, 3 invalid stop).
+ Kabisat: `2024, 2023, 2000, 1900`.
