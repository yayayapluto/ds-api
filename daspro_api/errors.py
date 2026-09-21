"""Jenis error yang dipakai seluruh paket.

Tujuannya supaya lapisan HTTP bisa memetakan error ke kode status dengan
jelas, tanpa menebak-nebak dari isi pesan.
"""


class DasproError(Exception):
    """Dasar semua error paket ini. `status` = kode HTTP yang cocok."""

    status = 500
    kode = "internal_error"

    def __init__(self, pesan: str, detail=None):
        super().__init__(pesan)
        self.pesan = pesan
        self.detail = detail

    def ke_dict(self) -> dict:
        isi = {"ok": False, "error": self.kode, "pesan": self.pesan}
        if self.detail is not None:
            isi["detail"] = self.detail
        return isi


class InputTidakValid(DasproError):
    """Masukan dari pemanggil tidak lengkap atau salah bentuk."""

    status = 400
    kode = "input_tidak_valid"


class TidakDitemukan(DasproError):
    """Job atau berkas yang diminta tidak ada."""

    status = 404
    kode = "tidak_ditemukan"


class AiGagal(DasproError):
    """Panggilan ke layanan AI gagal atau jawabannya tidak bisa dipakai.

    `sementara` menandai kegagalan yang pantas dicoba ulang: jaringan
    tersendat, gerbang menolak sementara, atau jawaban kosong. Kegagalan
    yang tetap (kunci salah, permintaan salah bentuk) tidak ditandai,
    supaya tidak diulang-ulang tanpa guna.
    """

    status = 502
    kode = "ai_gagal"

    def __init__(self, pesan: str, detail=None, sementara: bool = False):
        super().__init__(pesan, detail)
        self.sementara = sementara


class AiBelumDiatur(DasproError):
    """Layanan AI belum diatur, jadi tidak bisa mengerjakan modul."""

    status = 503
    kode = "ai_belum_diatur"


class GccTidakAda(DasproError):
    """Program gcc tidak ada di komputer ini."""

    status = 500
    kode = "gcc_tidak_ada"


class JobBentrok(DasproError):
    """Job tidak bisa dibatalkan karena statusnya sudah selesai."""

    status = 409
    kode = "job_bentrok"
