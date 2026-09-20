"""Penyusun laporan jawaban_LKP_Modul_X.md.

Bagian yang boleh berisi karangan hanya penjelasan dan jawaban pertanyaan.
Kolom hasil nyata selalu diambil dari hasil menjalankan program, bukan dari
tulisan AI.
"""
from pathlib import Path
from typing import Optional

from daspro_api.sanitize import bersihkan


def _sel(teks) -> str:
    """Rapikan satu sel tabel: baris baru jadi spasi, tanda pipa diloloskan."""
    if teks is None:
        return "-"
    isi = str(teks).strip().replace("|", "\\|")
    isi = " ".join(isi.split())
    return isi or "-"


def _blok_kode(isi: str, bahasa: str = "text") -> str:
    return f"```{bahasa}\n{isi.strip()}\n```"


def _tabel(kolom: list, baris: list) -> str:
    if not baris:
        return "_belum ada data_"
    garis = ["| " + " | ".join(_sel(k) for k in kolom) + " |"]
    garis.append("|" + "|".join([" --- "] * len(kolom)) + "|")
    for r in baris:
        garis.append("| " + " | ".join(_sel(c) for c in r) + " |")
    return "\n".join(garis)


def _identitas_block(identitas: dict) -> str:
    return (
        f"> Nama: {identitas.get('nama') or '-'} - NIM: {identitas.get('nim') or '-'} / "
        f"Kelas: {identitas.get('kelas') or '-'}\n"
        f"> Mata kuliah: {identitas.get('matakuliah') or 'Praktikum Dasar Pemrograman'}\n"
        f"> Modul: {identitas.get('modul') or '-'} - {identitas.get('judul_modul') or ''}\n"
        "> Kolom hasil nyata di bawah ini diambil dari menjalankan program, "
        "bukan ditulis tanpa diuji."
    )


def bagian_pengujian(hasil_uji: list, judul: str, catatan: str = "") -> str:
    """Tabel Expected dan Actual untuk satu soal."""
    baris = []
    for u in hasil_uji:
        masukan = (u.get("masukan") or "").replace("\n", "\\n")
        actual = (u.get("keluaran") or "").strip()
        if u.get("kode_keluar") not in (0, None):
            actual = (actual + f"\n(kode keluar {u.get('kode_keluar')})").strip()
        if not actual:
            actual = "(tidak ada keluaran)"
        status = "Sesuai" if u.get("status") == "sesuai" else "Perlu dicek"
        baris.append([masukan, u.get("harapan") or "-", f"`{actual}`", status])
    teks = f"### {judul}\n\n"
    if catatan:
        teks += catatan.strip() + "\n\n"
    teks += _tabel(["Masukan", "Expected Output", "Actual Output", "Status"], baris)
    return teks


def bagian_pertanyaan(analisis: list) -> str:
    if not analisis:
        return ""
    teks = "### Pertanyaan analisis\n\n"
    for i, item in enumerate(analisis, 1):
        tanya = (item.get("pertanyaan") or "").strip()
        jawab = (item.get("jawaban") or "").strip()
        teks += f"{i}. **{tanya}**\n  {jawab}\n\n"
    return teks.rstrip() + "\n"


def bagian_trace(trace: dict, prediksi: str = "") -> str:
    if not trace or not trace.get("baris"):
        return ""
    kolom = trace.get("kolom") or ["Langkah", "Kondisi", "Hasil Kondisi"]
    teks = "### Trace table\n\n" + _tabel(kolom, trace.get("baris") or [])
    if prediksi:
        teks += f"\n\n**Prediksi output:** {prediksi.strip()}"
    return teks + "\n"


def bagian_eksperimen(eksperimen: list) -> str:
    if not eksperimen:
        return ""
    baris = []
    for e in eksperimen:
        baris.append(
            [
                e.get("perubahan"),
                e.get("prediksi"),
                e.get("hasil"),
                e.get("error") or "tidak ada",
                e.get("penjelasan"),
            ]
        )
    teks = (
        "### Tabel eksperimen\n\n"
        + _tabel(
            ["No.", "Perubahan", "Prediksi", "Hasil Aktual", "Error/Warning", "Penjelasan"],
            [[i] + b for i, b in enumerate(baris, 1)],
        )
    )
    return teks + "\n"


def bagian_debugging(debugging: dict) -> str:
    if not debugging:
        return ""
    teks = "### Bagian debugging\n\n"
    error = (debugging.get("error_gcc") or "").strip()
    if error:
        teks += "Pesan dari gcc:\n\n" + _blok_kode(error) + "\n\n"
    temuan = debugging.get("temuan") or []
    baris = [
        [t.get("bagian"), t.get("jenis"), t.get("penyebab"), t.get("perbaikan")]
        for t in temuan
    ]
    teks += _tabel(["Bagian yang Salah", "Jenis", "Penyebab", "Perbaikan"], baris)
    if debugging.get("pelajaran"):
        teks += "\n\n" + str(debugging["pelajaran"]).strip()
    return teks + "\n"


def susun(
    identitas: dict,
    analisis: dict,
    hasil_kode: list,
    laporan_ai: dict,
    sumber: Optional[list] = None,
) -> str:
    """Rangkai seluruh bagian jadi satu berkas laporan markdown."""
    judul = laporan_ai.get("judul") or (
        f"Jawaban LKP Modul {identitas.get('modul') or '-'} - "
        f"{identitas.get('judul_modul') or 'Praktikum Dasar Pemrograman'}"
    )
    bagian = [f"# {bersihkan(str(judul)).strip()}", "", _identitas_block(identitas), ""]
    if sumber:
        bagian.append("> Sumber aturan: " + ", ".join(f"`{s}`" for s in sumber))
        bagian.append("")

    # Bagian per soal: hasil pengujian nyata + jawaban pertanyaan.
    peta_uji = {h.get("id"): h for h in hasil_kode}
    for i, soa in enumerate(analisis.get("soal") or [], 1):
        kode = str(soa.get("bagian") or f"{identitas.get('modul') or ''}.{i}").strip()
        judul_soal = soa.get("judul") or soa.get("id")
        berkas = soa.get("nama_berkas") or ""
        bagian.append("---")
        bagian.append("")
        bagian.append(f"## {kode} {judul_soal} (`{berkas}`)")
        bagian.append("")
        hasil = peta_uji.get(soa.get("id")) or {}
        if hasil.get("catatan"):
            bagian.append(str(hasil["catatan"]).strip())
            bagian.append("")
        if hasil.get("kasus_uji"):
            bagian.append(
                bagian_pengujian(
                    hasil["kasus_uji"], "Contoh pengujian (Actual diisi dari run nyata)"
                )
            )
            bagian.append("")
        if hasil.get("kode"):
            bagian.append("### Kode yang dipakai")
            bagian.append("")
            bagian.append(_blok_kode(hasil["kode"], "c"))
            bagian.append("")
        if hasil.get("penjelasan"):
            bagian.append("### Cara kerja")
            bagian.append("")
            bagian.append(str(hasil["penjelasan"]).strip())
            bagian.append("")

    # Bagian dari jawaban AI: analisis, trace, eksperimen, debugging.
    for bg in laporan_ai.get("bagian") or []:
        if not isinstance(bg, dict):
            continue
        judul_bg = bg.get("judul") or bg.get("kode") or "Bagian"
        if bg.get("kode"):
            bagian.append(f"## {bg['kode']} {judul_bg}")
        else:
            bagian.append(f"## {judul_bg}")
        bagian.append("")
        if bg.get("analisis"):
            bagian.append(bagian_pertanyaan(bg["analisis"]))
        if bg.get("trace"):
            bagian.append(bagian_trace(bg["trace"], bg.get("prediksi_output") or ""))
        bagian.append("")

    if laporan_ai.get("eksperimen"):
        bagian.append("---")
        bagian.append("")
        bagian.append("## Eksperimen")
        bagian.append("")
        bagian.append(bagian_eksperimen(laporan_ai["eksperimen"]))
        bagian.append("")

    if laporan_ai.get("debugging"):
        bagian.append("---")
        bagian.append("")
        bagian.append("## Debugging")
        bagian.append("")
        bagian.append(bagian_debugging(laporan_ai["debugging"]))
        bagian.append("")

    refleksi = laporan_ai.get("refleksi") or []
    if refleksi:
        bagian.append("---")
        bagian.append("")
        bagian.append("## Refleksi")
        bagian.append("")
        for i, r in enumerate(refleksi, 1):
            bagian.append(f"{i}. {str(r).strip()}")
        bagian.append("")

    bagian.append("---")
    bagian.append("")
    bagian.append("## Pernyataan penggunaan AI")
    bagian.append("")
    bagian.append(
        "Kode C dan susunan laporan ini dibuat dengan bantuan AI, lalu semua "
        "program dikompilasi dengan gcc dan dijalankan ulang. Kolom hasil nyata "
        "diisi dari keluaran program tersebut. Saya sudah membaca, mencoba, dan "
        "memahami isi laporan ini sebelum dikumpulkan."
    )
    bagian.append("")

    teks = "\n".join(bagian)
    return bersihkan(teks)


def tulis(teks: str, berkas: Path) -> Path:
    berkas = Path(berkas)
    berkas.parent.mkdir(parents=True, exist_ok=True)
    berkas.write_text(teks, encoding="utf-8")
    return berkas
