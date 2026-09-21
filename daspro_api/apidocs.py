"""Spesifikasi OpenAPI layanan, disusun dari kode.

Spesifikasi ini ditulis tangan, bukan dibangkitkan dari anotasi, supaya
tidak perlu paket tambahan. Isinya sengaja mengikuti apa yang benar-benar
dilayani `server.py`: jalur, kolom, dan bentuk jawabannya.

Halaman Swagger UI ada di `/docs`, dan berkas spesifikasinya di
`/openapi.json`.
"""
from typing import Optional

from daspro_api import __version__

# Keterangan singkat yang dipakai di beberapa tempat.
DESKRIPSI = """Layanan untuk mengerjakan modul praktikum Dasar Pemrograman C.

Kirim modul praktikum dan template LKP, lalu unduh hasilnya berupa satu
berkas ZIP. AI hanya menulis kode C dan menyusun isi laporan; sisanya
dikerjakan program biasa: mengompilasi dengan `gcc`, menjalankan dengan
masukan nilai batas, membuat HTML yang mudah disalin, mengisi template
docx, dan memeriksa gaya bahasa.

Pekerjaan berjalan di latar belakang. Setelah `POST /v1/jobs` dijawab,
tanyakan kemajuannya lewat `GET /v1/jobs/{id}` sampai statusnya `selesai`,
lalu unduh hasilnya lewat `GET /v1/jobs/{id}/download`.
"""

# Bentuk jawaban yang dipakai berulang.
SKEMA = {
    "Ok": {
        "type": "object",
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean", "example": True}},
    },
    "Galat": {
        "type": "object",
        "required": ["ok", "error", "pesan"],
        "properties": {
            "ok": {"type": "boolean", "example": False},
            "error": {
                "type": "string",
                "description": "Kode galat yang tetap, aman dipakai program lain.",
                "enum": [
                    "input_tidak_valid",
                    "tidak_ditemukan",
                    "ai_gagal",
                    "ai_belum_diatur",
                    "gcc_tidak_ada",
                    "job_bentrok",
                    "internal_error",
                ],
            },
            "pesan": {"type": "string", "description": "Keterangan untuk dibaca manusia."},
            "detail": {
                "description": "Keterangan tambahan, mis. badan jawaban dari layanan AI.",
                "nullable": True,
            },
        },
    },
    "KredensialAi": {
        "type": "object",
        "description": (
            "Kredensial AI milik pengguna. Kalau kuncinya kosong, seluruh "
            "kredensial dianggap tidak dikirim dan kunci milik server dipakai. "
            "Kunci hanya hidup selama permintaan ini berjalan."
        ),
        "properties": {
            "ai_api_key": {"type": "string", "description": "Kunci layanan AI."},
            "ai_base_url": {
                "type": "string",
                "description": "Alamat layanan AI, mis. https://api.openai.com/v1.",
            },
            "ai_model": {"type": "string", "description": "Nama model yang dipakai."},
        },
    },
    "KeadaanLayanan": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "layanan": {"type": "string", "example": "daspro-api"},
            "versi": {"type": "string", "example": "1.0.0"},
            "uptime_detik": {"type": "integer"},
            "skill_siap": {"type": "boolean"},
            "folder_skill": {"type": "string"},
            "ai_siap": {"type": "boolean"},
            "ai": {
                "type": "object",
                "description": "Ringkasan pengaturan AI. Kunci tidak pernah ikut.",
                "properties": {
                    "base_url": {"type": "string"},
                    "model": {"type": "string"},
                    "kunci_terisi": {"type": "boolean"},
                    "siap": {"type": "boolean"},
                    "timeout": {"type": "integer"},
                },
            },
            "gcc": {
                "type": "string",
                "description": (
                    "Jalur program kompilator. String kosong berarti gcc tidak "
                    "ditemukan; endpoint tetap menjawab supaya pemeriksaan "
                    "persiapan bisa jalan."
                ),
            },
            "jumlah_pekerjaan": {"type": "integer"},
        },
    },
    "KeteranganSkill": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "folder": {"type": "string"},
            "siap": {"type": "boolean"},
            "skrip": {"type": "array", "items": {"type": "string"}},
            "acuan": {"type": "array", "items": {"type": "string"}},
            "contoh_kode": {"type": "array", "items": {"type": "string"}},
        },
    },
    "PekerjaanBaru": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "job_id": {"type": "string", "example": "8c93de45fd16"},
            "status": {"type": "string", "example": "menunggu"},
            "pesan": {"type": "string"},
            "status_url": {"type": "string", "example": "/v1/jobs/8c93de45fd16"},
            "download_url": {"type": "string", "example": "/v1/jobs/8c93de45fd16/download"},
        },
    },
    "Pekerjaan": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["menunggu", "jalan", "selesai", "gagal", "dibatalkan"],
            },
            "tahap": {
                "type": "string",
                "description": "Tahap yang sedang dikerjakan, mis. analisis atau kode.",
            },
            "pesan": {"type": "string"},
            "persen": {"type": "integer", "minimum": 0, "maximum": 100},
            "dibuat": {"type": "string", "format": "date-time"},
            "selesai_pada": {"type": "string", "format": "date-time"},
            "error": {"type": "string", "description": "Sebab kegagalan, kalau gagal."},
            "detail_error": {"type": "string", "description": "Jejak lengkap kegagalan."},
            "hasil": {
                "type": "object",
                "description": "Ringkasan hasil; terisi setelah status selesai.",
            },
            "berkas": {
                "type": "array",
                "description": "Berkas hasil; terisi setelah pekerjaan berakhir.",
                "items": {
                    "type": "object",
                    "properties": {
                        "nama": {"type": "string"},
                        "ukuran": {"type": "integer"},
                    },
                },
            },
            "log": {
                "type": "array",
                "description": "Riwayat tahap. Hanya ada di endpoint status satu pekerjaan.",
                "items": {
                    "type": "object",
                    "properties": {
                        "waktu": {"type": "string"},
                        "tahap": {"type": "string"},
                        "pesan": {"type": "string"},
                    },
                },
            },
        },
    },
    "RingkasanHasil": {
        "type": "object",
        "properties": {
            "modul": {"type": "string", "nullable": True},
            "judul_modul": {"type": "string", "nullable": True},
            "jumlah_soal": {"type": "integer"},
            "soal": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "nama_berkas": {"type": "string"},
                        "jenis": {"type": "string"},
                        "percobaan": {"type": "integer"},
                        "jumlah_kasus": {"type": "integer"},
                        "sesuai": {"type": "integer"},
                    },
                },
            },
            "berkas": {
                "type": "object",
                "properties": {
                    "laporan_md": {"type": "string", "nullable": True},
                    "laporan_html": {"type": "string", "nullable": True},
                    "lkp_docx": {"type": "string", "nullable": True},
                    "kompilasi": {"type": "string", "example": "kompilasi.sh"},
                },
            },
            "cek_bahasa": {
                "type": "object",
                "properties": {
                    "lulus": {"type": "boolean"},
                    "jumlah_temuan": {"type": "integer"},
                },
            },
            "karakter_non_keyboard": {
                "type": "object",
                "description": "Karakter di luar keyboard yang masih tersisa, beserta jumlahnya.",
                "additionalProperties": {"type": "integer"},
            },
            "isi_template": {
                "type": "object",
                "description": "Keterangan pengisian template docx, atau alasan gagalnya.",
            },
            "zip": {
                "type": "object",
                "properties": {
                    "nama": {"type": "string"},
                    "jalur": {"type": "string"},
                    "ukuran": {"type": "integer"},
                },
            },
            "berkas_di_zip": {"type": "array", "items": {"type": "string"}},
        },
    },
    "HasilVerify": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean", "description": "True kalau semua berkas lolos."},
            "jumlah": {"type": "integer"},
            "lolos": {"type": "integer"},
            "hasil": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "berkas": {"type": "string"},
                        "ok": {"type": "boolean"},
                        "peringatan": {"type": "array", "items": {"type": "string"}},
                        "pesan_error": {"type": "string"},
                        "kode_keluar": {"type": "integer"},
                        "keluaran": {"type": "string"},
                        "timeout": {"type": "boolean"},
                    },
                },
            },
        },
    },
    "HasilCekBahasa": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "lulus": {"type": "boolean"},
            "jumlah": {"type": "integer", "description": "Jumlah temuan gaya bahasa."},
            "temuan": {"type": "array", "items": {"type": "object"}},
        },
    },
    "PetaDocx": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "jumlah_sel_kosong": {"type": "integer"},
            "jumlah_baris_titik": {"type": "integer"},
            "peta": {
                "type": "object",
                "description": (
                    "Peta tempat kosong: `sel_kosong` berisi kunci sel yang bisa "
                    "diisi, `baris_titik` berisi baris titik-titik."
                ),
            },
        },
    },
    "HasilIsiDocx": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "berkas": {"type": "string"},
            "sel_diisi": {"type": "integer"},
            "baris_diisi": {"type": "integer"},
            "karakter_dibuang": {"type": "object", "additionalProperties": {"type": "integer"}},
            "paragraf_sebelum": {"type": "integer"},
            "paragraf_sesudah": {"type": "integer"},
            "struktur_utuh": {
                "type": "boolean",
                "description": "True kalau jumlah paragraf sebelum dan sesudah sama.",
            },
        },
    },
    "HasilUjiAi": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "model": {"type": "string"},
            "alamat": {"type": "string"},
            "jawaban": {"type": "string"},
            "detik": {"type": "number"},
        },
    },
}

# Jawaban galat yang mungkin muncul di hampir semua endpoint.
GALAT_UMUM = {
    "400": {"$ref": "#/components/responses/InputTidakValid"},
    "401": {"$ref": "#/components/responses/TokenSalah"},
    "404": {"$ref": "#/components/responses/TidakDitemukan"},
    "500": {"$ref": "#/components/responses/GalatDalam"},
}

RESPONS = {
    "InputTidakValid": {
        "description": "Masukan tidak lengkap atau salah bentuk.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "TokenSalah": {
        "description": "Token akses salah atau tidak dikirim (hanya kalau DASPRO_AUTH_TOKEN diisi).",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "TidakDitemukan": {
        "description": "Pekerjaan atau berkas yang diminta tidak ada.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "GalatDalam": {
        "description": "Kesalahan di luar dugaan. Jejak lengkapnya ada di catatan layanan.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "AiGagal": {
        "description": "Panggilan ke layanan AI gagal atau jawabannya tidak bisa dipakai.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "AiBelumDiatur": {
        "description": "Layanan AI belum diatur, jadi pekerjaan tidak bisa dikerjakan.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
    "JobBentrok": {
        "description": "Pekerjaan tidak bisa dibatalkan karena statusnya sudah berakhir.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Galat"}}},
    },
}

# Kolom kredensial AI yang boleh ikut di permintaan mana pun.
KOLOM_KREDENSIAL = {
    "ai_api_key": {"type": "string", "description": "Kunci AI milik pengguna (opsional)."},
    "ai_base_url": {"type": "string", "description": "Alamat layanan AI milik pengguna."},
    "ai_model": {"type": "string", "description": "Nama model milik pengguna."},
}


def _json(badan: dict) -> dict:
    """Jawaban JSON dari satu skema."""
    return {"content": {"application/json": {"schema": badan}}}


def _multipart(kolom: dict, wajib: Optional[list] = None) -> dict:
    """Badan permintaan multipart dengan kolom yang diberikan."""
    skema = {"type": "object", "properties": {**kolom, **KOLOM_KREDENSIAL}}
    if wajib:
        skema["required"] = wajib
    return {"content": {"multipart/form-data": {"schema": skema}}}


def _berkas(keterangan: str) -> dict:
    return {"type": "string", "format": "binary", "description": keterangan}


def spesifikasi() -> dict:
    """Susun spesifikasi OpenAPI lengkap sebagai kamus biasa."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "daspro-api",
            "version": __version__,
            "description": DESKRIPSI,
            "license": {"name": "MIT"},
        },
        # Alamat relatif, jadi halaman ini tetap benar di port berapa pun.
        "servers": [{"url": "/", "description": "Layanan yang sedang berjalan"}],
        "tags": [
            {"name": "layanan", "description": "Keadaan layanan dan keterangan skill."},
            {"name": "pekerjaan", "description": "Mengerjakan satu modul sampai jadi ZIP."},
            {"name": "alat", "description": "Pemeriksaan tanpa AI: kompilasi, bahasa, dan docx."},
        ],
        "components": {
            "schemas": SKEMA,
            "responses": RESPONS,
            "securitySchemes": {
                "token": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "Hanya dipakai kalau `DASPRO_AUTH_TOKEN` diisi. Kirim "
                        "`Authorization: Bearer <token>` di setiap permintaan."
                    ),
                }
            },
        },
        # Token opsional, jadi keamanan tidak diwajibkan di tingkat global.
        "security": [{"token": []}, {}],
        "paths": {
            "/health": {
                "get": {
                    "tags": ["layanan"],
                    "summary": "Keadaan layanan",
                    "description": (
                        "Kesiapan skill, AI, dan gcc. Kunci API tidak pernah ikut "
                        "dikirim balik; yang ada hanya keterangan apakah sudah terisi."
                    ),
                    "operationId": "keadaanLayanan",
                    "responses": {
                        "200": {
                            "description": "Keadaan layanan sekarang.",
                            **_json({"$ref": "#/components/schemas/KeadaanLayanan"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/skill": {
                "get": {
                    "tags": ["layanan"],
                    "summary": "Keterangan folder skill",
                    "description": "Daftar skrip dan acuan gaya yang dipakai layanan.",
                    "operationId": "keteranganSkill",
                    "responses": {
                        "200": {
                            "description": "Isi folder skill.",
                            **_json({"$ref": "#/components/schemas/KeteranganSkill"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs": {
                "post": {
                    "tags": ["pekerjaan"],
                    "summary": "Mulai pekerjaan baru",
                    "description": (
                        "Unggah modul dan template LKP, lalu pekerjaan berjalan di "
                        "latar belakang. Jawabannya berisi `job_id` yang dipakai untuk "
                        "menanyakan kemajuan dan mengunduh hasil."
                    ),
                    "operationId": "mulaiPekerjaan",
                    "requestBody": _multipart(
                        {
                            "modul": _berkas("Berkas PDF atau docx modul praktikum."),
                            "lkp": _berkas("Template LKP docx yang mau diisi (opsional)."),
                            "identitas": {
                                "type": "string",
                                "description": (
                                    "Objek JSON berisi `nama`, `nim`, `kelas`, `modul`, "
                                    "dan `matakuliah`."
                                ),
                                "example": (
                                    '{"nama":"Nama Mahasiswa","nim":"1234567890",'
                                    '"kelas":"B","modul":"5",'
                                    '"matakuliah":"Praktikum Dasar Pemrograman"}'
                                ),
                            },
                            "buat_copyable": {
                                "type": "boolean",
                                "default": True,
                                "description": "Buat versi HTML yang tiap selnya bisa disalin.",
                            },
                            "isi_docx": {
                                "type": "boolean",
                                "default": True,
                                "description": "Isi template LKP tanpa mengubah formatnya.",
                            },
                        },
                        wajib=["modul", "identitas"],
                    ),
                    "responses": {
                        "202": {
                            "description": "Pekerjaan masuk antrean.",
                            **_json({"$ref": "#/components/schemas/PekerjaanBaru"}),
                        },
                        "503": {"$ref": "#/components/responses/AiBelumDiatur"},
                        **GALAT_UMUM,
                    },
                },
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Daftar pekerjaan",
                    "description": "Pekerjaan terbaru lebih dulu, paling banyak 50 baris.",
                    "operationId": "daftarPekerjaan",
                    "responses": {
                        "200": {
                            "description": "Daftar pekerjaan.",
                            **_json(
                                {
                                    "type": "object",
                                    "properties": {
                                        "ok": {"type": "boolean"},
                                        "pekerjaan": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/Pekerjaan"
                                            },
                                        },
                                    },
                                }
                            ),
                        },
                        **GALAT_UMUM,
                    },
                },
            },
            "/v1/jobs/{id}": {
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Status satu pekerjaan",
                    "description": (
                        "Kemajuan, catatan tahap, dan sebab kegagalan kalau ada. "
                        "Tanyakan berkala sampai statusnya `selesai`, `gagal`, atau "
                        "`dibatalkan`."
                    ),
                    "operationId": "statusPekerjaan",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "example": "8c93de45fd16",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Keadaan pekerjaan sekarang.",
                            **_json({"$ref": "#/components/schemas/Pekerjaan"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs/{id}/result": {
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Ringkasan hasil",
                    "description": "Ringkasan hasil dalam respons API; tidak disertakan sebagai berkas di ZIP.",
                    "operationId": "hasilPekerjaan",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Ringkasan hasil pekerjaan.",
                            **_json(
                                {
                                    "type": "object",
                                    "properties": {
                                        "ok": {"type": "boolean"},
                                        "job_id": {"type": "string"},
                                        "status": {"type": "string"},
                                        "hasil": {
                                            "$ref": "#/components/schemas/RingkasanHasil"
                                        },
                                        "error": {"type": "string"},
                                    },
                                }
                            ),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs/{id}/download": {
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Unduh berkas ZIP hasil",
                    "operationId": "unduhHasil",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Berkas ZIP berisi semua hasil.",
                            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs/{id}/files/{nama}": {
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Unduh satu berkas hasil",
                    "description": (
                        "Nama berkas boleh memuat subfolder, mis. "
                        "`tugas/tugas_modul_05.c`."
                    ),
                    "operationId": "unduhBerkasHasil",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {
                            "name": "nama",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "example": "latihan_01.c",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Isi berkas yang diminta.",
                            "content": {
                                "application/octet-stream": {
                                    "schema": {"type": "string", "format": "binary"}
                                }
                            },
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs/{id}/log": {
                "get": {
                    "tags": ["pekerjaan"],
                    "summary": "Catatan pekerjaan",
                    "description": (
                        "Catatan tahap sebagai berkas teks, termasuk pekerjaan yang "
                        "gagal. Isinya sama dengan `job.log` di folder pekerjaan. "
                        "Halaman web menampilkan catatan ini di modal lebih dulu; "
                        "unduhan berkasnya opsional."
                    ),
                    "operationId": "catatanPekerjaan",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Catatan pekerjaan sebagai teks.",
                            "content": {
                                "text/plain": {
                                    "schema": {"type": "string"},
                                    "example": (
                                        "[2026-09-21 10:41:57] masuk: permintaan baru: "
                                        "modul modul.pdf, lkp lkp.docx\n"
                                        "[2026-09-21 10:44:58] selesai: Pekerjaan selesai.\n"
                                    ),
                                }
                            },
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/jobs/{id}/cancel": {
                "post": {
                    "tags": ["pekerjaan"],
                    "summary": "Batalkan pekerjaan",
                    "description": (
                        "Pekerjaan yang belum berakhir ditandai dibatalkan. "
                        "Pekerjaan yang sudah selesai atau gagal tidak bisa dibatalkan."
                    ),
                    "operationId": "batalkanPekerjaan",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Pekerjaan sudah ditandai dibatalkan.",
                            **_json({"$ref": "#/components/schemas/Pekerjaan"}),
                        },
                        "409": {"$ref": "#/components/responses/JobBentrok"},
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/ai/uji": {
                "post": {
                    "tags": ["layanan"],
                    "summary": "Uji koneksi AI",
                    "description": (
                        "Kirim satu pertanyaan kecil memakai kredensial yang dikirim, "
                        "tanpa menyimpannya. Kunci tidak pernah ikut di jawaban."
                    ),
                    "operationId": "ujiAi",
                    "requestBody": _multipart({}),
                    "responses": {
                        "200": {
                            "description": "Layanan AI menjawab.",
                            **_json({"$ref": "#/components/schemas/HasilUjiAi"}),
                        },
                        "502": {"$ref": "#/components/responses/AiGagal"},
                        "503": {"$ref": "#/components/responses/AiBelumDiatur"},
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/verify": {
                "post": {
                    "tags": ["alat"],
                    "summary": "Kompilasi dan jalankan berkas .c",
                    "description": (
                        "Tanpa AI. Setiap berkas dikompilasi dengan `gcc -Wall -Wextra`, "
                        "lalu dijalankan dengan masukan yang dikirim. Masukan bisa "
                        "berlaku untuk semua berkas (`masukan`) atau satu berkas saja "
                        "(`masukan:<nama berkas>`)."
                    ),
                    "operationId": "verifyBerkas",
                    "requestBody": _multipart(
                        {
                            "files": {
                                "type": "array",
                                "items": _berkas("Berkas .c yang diperiksa."),
                                "description": "Boleh lebih dari satu berkas.",
                            },
                            "masukan": {
                                "type": "string",
                                "description": "Masukan untuk program, mis. `5\\n`.",
                            },
                        },
                        wajib=["files"],
                    ),
                    "responses": {
                        "200": {
                            "description": "Hasil kompilasi dan jalan tiap berkas.",
                            **_json({"$ref": "#/components/schemas/HasilVerify"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/cek-bahasa": {
                "post": {
                    "tags": ["alat"],
                    "summary": "Periksa gaya bahasa laporan",
                    "description": "Tanpa AI. Memakai pemeriksa gaya dari folder skill.",
                    "operationId": "cekBahasa",
                    "requestBody": _multipart(
                        {
                            "files": {
                                "type": "array",
                                "items": _berkas("Berkas laporan yang diperiksa."),
                            }
                        },
                        wajib=["files"],
                    ),
                    "responses": {
                        "200": {
                            "description": "Hasil pemeriksaan gaya bahasa.",
                            **_json({"$ref": "#/components/schemas/HasilCekBahasa"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/docx/peta": {
                "post": {
                    "tags": ["alat"],
                    "summary": "Lihat tempat kosong di template docx",
                    "description": (
                        "Bongkar template, lalu tunjukkan sel kosong dan baris "
                        "titik-titik yang bisa diisi. Kuncinya dipakai di `/v1/docx/isi`."
                    ),
                    "operationId": "petaDocx",
                    "requestBody": _multipart(
                        {"template": _berkas("Template LKP docx.")}, wajib=["template"]
                    ),
                    "responses": {
                        "200": {
                            "description": "Peta tempat kosong template.",
                            **_json({"$ref": "#/components/schemas/PetaDocx"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
            "/v1/docx/isi": {
                "post": {
                    "tags": ["alat"],
                    "summary": "Isi template docx dari mapping",
                    "description": (
                        "Isi template sesuai peta, lalu bungkus lagi jadi docx utuh. "
                        "Formatnya dijaga: jumlah paragraf sebelum dan sesudah sama."
                    ),
                    "operationId": "isiDocx",
                    "requestBody": _multipart(
                        {
                            "template": _berkas("Template LKP docx."),
                            "mapping": {
                                "type": "string",
                                "description": "Objek JSON berisi `sel` dan `titik`.",
                                "example": '{"sel":{"1A2B3C4D":"Sesuai"},"titik":{"1":"1 2 3 4 5"}}',
                            },
                        },
                        wajib=["template", "mapping"],
                    ),
                    "responses": {
                        "200": {
                            "description": "Hasil pengisian template.",
                            **_json({"$ref": "#/components/schemas/HasilIsiDocx"}),
                        },
                        **GALAT_UMUM,
                    },
                }
            },
        },
    }
