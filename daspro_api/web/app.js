/* Panel Daspro API.
 *
 * Kunci API disimpan hanya di localStorage peramban, lalu dikirim ke server
 * saat mengerjakan modul. Server memakainya selama pekerjaan berjalan dan
 * tidak menuliskannya ke berkas.
 */


const KUNCI_SIMPAN = "daspro.ai";
const $ = (id) => document.getElementById(id);

/* ---------- simpan dan muat pengaturan AI ---------- */

function bacaSimpanan() {
  try {
    return JSON.parse(localStorage.getItem(KUNCI_SIMPAN) || "{}");
  } catch {
    return {};
  }
}

function tulisSimpanan(data) {
  try {
    localStorage.setItem(KUNCI_SIMPAN, JSON.stringify(data));
    return true;
  } catch (e) {
    pesan("pesan-ai", "Peramban menolak menyimpan. Pakai mode biasa, bukan mode privat.", "gagal");
    return false;
  }
}

function terapkanSimpanan() {
  const s = bacaSimpanan();
  const daftar = [...$("penyedia").options].map((o) => o.value);
  if (s.base_url && daftar.includes(s.base_url)) {
    $("penyedia").value = s.base_url;
  } else if (s.base_url) {
    $("penyedia").value = "lain";
    $("alamat").value = s.base_url;
  }
  $("model").value = s.model || "";
  $("kunci").value = s.api_key || "";
  perbaruiKolomAlamat();
  const id = bacaIdentitas();
  $("nama").value = id.nama || "";
  $("nim").value = id.nim || "";
  $("kelas").value = id.kelas || "";
  $("modul-ke").value = id.modul || "";
  $("matakuliah").value = id.matakuliah || "Praktikum Dasar Pemrograman";
}

const KUNCI_IDENTITAS = "daspro.identitas";

function bacaIdentitas() {
  try {
    return JSON.parse(localStorage.getItem(KUNCI_IDENTITAS) || "{}");
  } catch {
    return {};
  }
}

function simpanIdentitas() {
  const data = {
    nama: $("nama").value.trim(),
    nim: $("nim").value.trim(),
    kelas: $("kelas").value.trim(),
    modul: $("modul-ke").value.trim(),
    matakuliah: $("matakuliah").value.trim(),
  };
  try {
    localStorage.setItem(KUNCI_IDENTITAS, JSON.stringify(data));
  } catch {
    /* gagal menyimpan identitas tidak menghalangi pekerjaan */
  }
  return data;
}

function kredensialSekarang() {
  const pilihan = $("penyedia").value;
  const alamat = pilihan === "lain" ? $("alamat").value.trim() : pilihan;
  return {
    api_key: $("kunci").value.trim(),
    base_url: alamat,
    model: $("model").value.trim(),
  };
}

function perbaruiKolomAlamat() {
  $("bungkus-alamat").classList.toggle("sembunyi", $("penyedia").value !== "lain");
}

/* ---------- tampilan kecil ---------- */

function pesan(id, teks, jenis) {
  const el = $(id);
  el.textContent = teks || "";
  el.className = "pesan " + (jenis || "");
}

function toast(teks) {
  const t = $("toast");
  t.textContent = teks;
  t.classList.add("tampil");
  clearTimeout(t._x);
  t._x = setTimeout(() => t.classList.remove("tampil"), 1800);
}

function pil(teks, warna) {
  const s = document.createElement("span");
  s.className = "pil " + (warna || "abu");
  s.textContent = teks;
  return s;
}

/* Susun jalur unduhan dari nomor pekerjaan.
 *
 * Nomor pekerjaan datang dari server, tapi tetap diperiksa dulu: hanya
 * huruf dan angka yang diterima, dan hasilnya selalu jalur di dalam situs
 * ini. Jadi halaman ini tidak bisa dibelokkan ke alamat lain.
 */
function jalurJob(jobId, aksi) {
  if (!jobId || !/^[A-Za-z0-9]{6,32}$/.test(jobId)) return "";
  const bagian = aksi === "download" ? "download" : "files";
  return "/v1/jobs/" + encodeURIComponent(jobId) + "/" + bagian;
}

/* Jalur catatan pekerjaan. Selalu ada, termasuk untuk pekerjaan yang gagal,
 * supaya sebab kegagalan bisa diperiksa sendiri. */
function jalurLog(jobId) {
  if (!jobId || !/^[A-Za-z0-9]{6,32}$/.test(jobId)) return "";
  return "/v1/jobs/" + encodeURIComponent(jobId) + "/log";
}

async function minta(jalur, opsi) {
  const r = await fetch(jalur, opsi);
  const teks = await r.text();
  let data;
  try {
    data = JSON.parse(teks);
  } catch (e) {
    throw new Error("Jawaban server tidak bisa dibaca: " + teks.slice(0, 200));
  }
  if (!r.ok) {
    const e = new Error(data.pesan || data.error || "Permintaan gagal");
    e.data = data;
    e.status = r.status;
    throw e;
  }
  return data;
}

/* ---------- keadaan layanan ---------- */

/* Kunci server terisi -> kartu pengaturan AI cukup dilewati. Kalau kosong,
 * kartu itu berubah jadi wajib: tanpa kunci, pekerjaan tidak bisa jalan. */
let kunciServerTerisi = null;

function perbaruiStatusAi(d) {
  const kartu = $("kartu-ai");
  const tanda = $("tanda-ai");
  const bantuan = $("bantuan-ai");
  const label = document.querySelector("#kartu-ai .tanda-opsional");
  const punyaKunci = Boolean(d && d.ai && d.ai.kunci_terisi);
  kunciServerTerisi = punyaKunci;

  kartu.classList.toggle("butuh", !punyaKunci);
  if (label) label.textContent = punyaKunci ? "opsional" : "wajib";

  if (!d) {
    tanda.className = "pil merah";
    tanda.textContent = "server tidak terjangkau";
    bantuan.textContent = "Keadaan kunci server belum diketahui.";
    return;
  }
  if (punyaKunci) {
    tanda.className = "pil abu";
    tanda.textContent = "opsional - server sudah punya kunci";
    bantuan.textContent =
      "Kode C ditulis oleh model bahasa. Server sudah punya kunci API, jadi " +
      "bagian ini cukup dibiarkan kosong. Isi hanya kalau mau memakai kunci sendiri.";
  } else {
    tanda.className = "pil merah";
    tanda.textContent = "wajib diisi";
    bantuan.textContent =
      "Server belum punya kunci API, jadi kunci harus diisi di sini supaya " +
      "modul bisa dikerjakan.";
  }
}

async function muatKeadaan() {
  const kotak = $("keadaan");
  kotak.textContent = "";
  try {
    const d = await minta("/health");
    kotak.append(
      pil(d.ai_siap ? "AI siap" : "AI belum diatur", d.ai_siap ? "hijau" : "merah"),
      pil("gcc " + (d.gcc ? "ada" : "tidak ada"), d.gcc ? "hijau" : "merah"),
      pil(d.skill_siap ? "skill siap" : "skill kurang", d.skill_siap ? "hijau" : "merah"),
      pil("versi " + d.versi)
    );
    const ket = document.createElement("span");
    ket.className = "redup";
    ket.textContent =
      "server: " + (d.ai ? d.ai.model : "-") +
      (d.ai && d.ai.kunci_terisi ? " (kunci server terisi)" : " (kunci server kosong)");
    kotak.append(ket);
    perbaruiStatusAi(d);
  } catch (e) {
    kotak.append(pil("server tidak terjangkau", "merah"));
    perbaruiStatusAi(null);
  }
}

/* ---------- uji koneksi AI ---------- */

async function ujiAi() {
  const k = kredensialSekarang();
  pesan("pesan-ai", "menguji koneksi...", "info");
  $("uji-ai").disabled = true;
  try {
    const isi = new FormData();
    isi.append("ai_api_key", k.api_key);
    isi.append("ai_base_url", k.base_url);
    isi.append("ai_model", k.model);
    const d = await minta("/v1/ai/uji", { method: "POST", body: isi });
    pesan("pesan-ai", "Berhasil. Model " + d.model + " menjawab: \"" + d.jawaban + "\" dalam " + d.detik + " detik.", "ok");
  } catch (e) {
    let teks = e.message;
    if (e.data && e.data.detail) teks += " - " + String(e.data.detail).slice(0, 300);
    pesan("pesan-ai", teks, "gagal");
  } finally {
    $("uji-ai").disabled = false;
  }
}

/* ---------- mulai pekerjaan ---------- */

let jobAktif = null;
let pewaktu = null;
// Berapa kali berturut-turut tanya kemajuan gagal. Satu kegagalan belum
// berarti pekerjaannya berhenti.
let gagalBerturut = 0;
const BATAS_GAGAL_PANTAU = 3;

async function mulai() {
  const k = kredensialSekarang();
  const id = simpanIdentitas();

  const kurang = [];
  if (!$("modul").files.length) kurang.push("berkas modul");
  if (!id.nama) kurang.push("nama");
  if (!id.nim) kurang.push("NIM");
  if (!id.kelas) kurang.push("kelas");
  if (!id.modul) kurang.push("nomor modul");
  if (kurang.length) {
    pesan("pesan-mulai", "Belum diisi: " + kurang.join(", ") + ".", "gagal");
    return;
  }
  if (kunciServerTerisi === false && !k.api_key) {
    pesan(
      "pesan-mulai",
      "Kunci API belum ada. Server tidak punya kunci sendiri, jadi isi dulu di bagian " +
        "\"Pengaturan AI\" di atas.",
      "gagal"
    );
    $("kartu-ai").scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  pesan("pesan-mulai", "", "");

  const isi = new FormData();
  isi.append("modul", $("modul").files[0]);
  if ($("lkp").files.length) isi.append("lkp", $("lkp").files[0]);
  isi.append("identitas", JSON.stringify(id));
  isi.append("buat_copyable", $("copyable").checked ? "true" : "false");
  isi.append("isi_docx", $("isi-docx").checked ? "true" : "false");
  // Kredensial hanya dikirim kalau kuncinya diisi. Kalau alamat dan nama
  // model ikut terkirim tanpa kunci, kunci milik server akan dipakai untuk
  // alamat itu, dan layanan AI akan menolak permintaannya.
  if (k.api_key) {
    isi.append("ai_api_key", k.api_key);
    if (k.base_url) isi.append("ai_base_url", k.base_url);
    if (k.model) isi.append("ai_model", k.model);
  }

  $("mulai").disabled = true;
  pesan("pesan-mulai", "mengirim berkas...", "info");
  try {
    const d = await minta("/v1/jobs", { method: "POST", body: isi });
    jobAktif = d.job_id;
    gagalBerturut = 0;
    $("batal").disabled = false;
    $("kartu-kemajuan").classList.remove("sembunyi");
    $("kartu-hasil").classList.add("sembunyi");
    pesan("pesan-mulai", "Pekerjaan dimulai. Nomor: " + d.job_id, "ok");
    pantau();
  } catch (e) {
    pesan("pesan-mulai", e.message, "gagal");
    $("mulai").disabled = false;
  }
}

function pantau() {
  clearInterval(pewaktu);
  gagalBerturut = 0;
  pewaktu = setInterval(tanyaKemajuan, 1500);
}

/* Satu kali gagal bukan berarti pekerjaannya berhenti: jaringan bisa
 * tersendat, atau server sebentar dijalankan ulang. Pemantauan baru
 * dilepas setelah beberapa kali gagal berturut-turut, dan pekerjaannya
 * sendiri tetap jalan di server. */
async function tanyaKemajuan() {
  if (!jobAktif) return;
  try {
    const d = await minta("/v1/jobs/" + jobAktif);
    if (gagalBerturut) {
      gagalBerturut = 0;
      pesan("pesan-mulai", "Pemantauan tersambung lagi.", "ok");
    }
    tampilkanKemajuan(d);
    if (["selesai", "gagal", "dibatalkan"].includes(d.status)) {
      clearInterval(pewaktu);
      $("mulai").disabled = false;
      $("batal").disabled = true;
      if (d.status === "selesai") tampilkanHasil(d);
      else pesan("pesan-mulai", d.error || d.pesan, "gagal");
      muatRiwayat();
    }
  } catch (e) {
    gagalBerturut += 1;
    if (gagalBerturut < BATAS_GAGAL_PANTAU) {
      pesan(
        "pesan-mulai",
        "Pemantauan tersendat (" + e.message + "). Mencoba lagi...",
        "info"
      );
      return;
    }
    clearInterval(pewaktu);
    pesan(
      "pesan-mulai",
      "Gagal memantau: " + e.message + ". Pekerjaan tetap jalan di server; " +
        "tekan \"pantau\" di riwayat pekerjaan untuk menyambung lagi.",
      "gagal"
    );
    $("mulai").disabled = false;
    $("batal").disabled = true;
    muatRiwayat();
  }
}

/* Sambungkan panel ke pekerjaan yang sudah jalan, mis. setelah halaman
 * dimuat ulang atau setelah pemantauan sempat tersendat. */
function pantauJob(jobId) {
  if (!/^[A-Za-z0-9]{6,32}$/.test(jobId || "")) return;
  jobAktif = jobId;
  $("kartu-kemajuan").classList.remove("sembunyi");
  $("kartu-hasil").classList.add("sembunyi");
  $("mulai").disabled = true;
  $("batal").disabled = false;
  pesan("pesan-mulai", "Memantau pekerjaan " + jobId + ".", "info");
  pantau();
}

function tampilkanKemajuan(d) {
  $("bar").style.width = (d.persen || 0) + "%";
  $("persen").textContent = (d.persen || 0) + "%";
  const t = $("tahap");
  t.textContent = d.tahap || d.status;
  t.className = "pil " + (d.status === "selesai" ? "hijau" : d.status === "gagal" ? "merah" : "kuning");
  $("pesan-jalan").textContent = d.pesan || "";
  const log = (d.log || []).map(
    (x) =>
      "[" + String(x.waktu || "").slice(11, 19) + "] " +
      (x.tahap || "") + ": " + (x.pesan || "")
  );
  const kotak = $("log");
  kotak.textContent = log.join("\n");
  kotak.scrollTop = kotak.scrollHeight;
}

/* ---------- hasil ---------- */

function tampilkanHasil(d) {
  const h = d.hasil || {};
  $("kartu-hasil").classList.remove("sembunyi");
  const ringkas = $("ringkasan");
  ringkas.textContent = "";

  const grid = document.createElement("div");
  grid.className = "ringkas-grid";
  const kotak = [
    ["Soal dikerjakan", h.jumlah_soal || 0],
    ["Bahasa lulus", h.cek_bahasa && h.cek_bahasa.lulus ? "ya" : "tidak"],
    ["Karakter aneh", Object.keys(h.karakter_non_keyboard || {}).length],
  ];
  kotak.forEach(([label, angka]) => {
    const k = document.createElement("div");
    k.className = "ringkas-kotak";
    k.innerHTML = '<div class="angka"></div><div class="label"></div>';
    k.querySelector(".angka").textContent = angka;
    k.querySelector(".label").textContent = label;
    grid.append(k);
  });
  ringkas.append(grid);

  if (h.isi_template && h.isi_template.struktur_utuh !== undefined) {
    const p = document.createElement("p");
    p.className = "redup";
    p.textContent = h.isi_template.struktur_utuh
      ? "Template LKP terisi dan formatnya tetap utuh."
      : "Template LKP terisi, tetapi jumlah paragrafnya berubah.";
    ringkas.append(p);
  }

  const tabel = $("tabel-berkas");
  const badan = tabel.querySelector("tbody");
  badan.textContent = "";
  (d.berkas || []).forEach((b) => {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td");
    td1.textContent = b.nama;
    const td2 = document.createElement("td");
    td2.className = "kanan";
    td2.textContent = (b.ukuran / 1024).toFixed(1) + " KB";
    const td3 = document.createElement("td");
    td3.className = "kanan";
    const a = document.createElement("a");
    a.className = "tombol kecil";
    a.href = jalurJob(d.job_id, "files") + "/" + encodeURIComponent(b.nama);
    a.textContent = "unduh";
    td3.append(a);
    tr.append(td1, td2, td3);
    badan.append(tr);
  });
  tabel.classList.toggle("sembunyi", !(d.berkas || []).length);
  toast("Pekerjaan selesai");
}

async function batalkan() {
  if (!jobAktif) return;
  try {
    await minta("/v1/jobs/" + jobAktif + "/cancel", { method: "POST" });
    toast("Permintaan batal dikirim");
  } catch (e) {
    toast(e.message);
  }
}

/* ---------- riwayat ---------- */

async function muatRiwayat() {
  const kotak = $("riwayat");
  kotak.textContent = "memuat...";
  try {
    const d = await minta("/v1/jobs");
    kotak.textContent = "";
    if (!d.pekerjaan.length) {
      kotak.className = "redup";
      kotak.textContent = "Belum ada pekerjaan.";
      return;
    }
    kotak.className = "";
    d.pekerjaan.slice(0, 12).forEach((j) => {
      const baris = document.createElement("div");
      baris.className = "riwayat-baris";

      const id = document.createElement("span");
      id.className = "id";
      id.textContent = j.job_id;

      const warna = j.status === "selesai" ? "hijau" : j.status === "gagal" ? "merah" : "kuning";
      const p = pil(j.status, warna);

      const waktu = document.createElement("span");
      waktu.className = "redup";
      waktu.textContent = (j.dibuat || "").replace("T", " ").slice(0, 16);

      const kanan = document.createElement("span");
      kanan.className = "kanan";
      if (j.status === "selesai") {
        const a = document.createElement("a");
        a.className = "tombol kecil";
        a.href = jalurJob(j.job_id, "download");
        a.textContent = "unduh ZIP";
        kanan.append(a);
      } else if (["menunggu", "jalan"].includes(j.status)) {
        // Pekerjaan yang masih jalan bisa disambungkan lagi ke panel ini,
        // mis. setelah halaman dimuat ulang.
        const p = document.createElement("button");
        p.type = "button";
        p.className = "tombol kecil garis";
        p.textContent = "pantau";
        p.addEventListener("click", () => pantauJob(j.job_id));
        kanan.append(p);
      }
      // Catatan pekerjaan selalu bisa dibaca, termasuk kalau gagal.
      const log = document.createElement("button");
      log.type = "button";
      log.className = "tombol kecil garis";
      log.textContent = "log";
      log.addEventListener("click", () => bukaLog(j.job_id));
      kanan.append(log);

      baris.append(id, p, waktu, kanan);
      kotak.append(baris);
    });
  } catch (e) {
    kotak.textContent = "Gagal memuat riwayat: " + e.message;
  }
}

/* ---------- modal catatan pekerjaan ---------- */

/* Catatan dibuka dulu di modal supaya bisa dibaca tanpa mengunduh apa pun.
 * Berkasnya baru diambil kalau tombol unduh ditekan. */
async function bukaLog(jobId) {
  if (!/^[A-Za-z0-9]{6,32}$/.test(jobId || "")) return;
  const jalur = jalurLog(jobId);
  $("modal-judul").textContent = "Catatan pekerjaan " + jobId;
  $("modal-isi").textContent = "memuat...";
  $("unduh-log").href = jalur;
  $("modal-log").classList.remove("sembunyi");
  try {
    const r = await fetch(jalur);
    if (!r.ok) throw new Error("server menjawab " + r.status);
    $("modal-isi").textContent = await r.text();
  } catch (e) {
    $("modal-isi").textContent = "Gagal memuat catatan: " + e.message;
  }
}

function tutupLog() {
  $("modal-log").classList.add("sembunyi");
}

/* ---------- pasang semua ---------- */

function pasang() {
  terapkanSimpanan();
  muatKeadaan();
  muatRiwayat();

  $("penyedia").addEventListener("change", perbaruiKolomAlamat);

  $("simpan-ai").addEventListener("click", () => {
    const k = kredensialSekarang();
    if (tulisSimpanan(k)) pesan("pesan-ai", "Pengaturan disimpan di peramban ini.", "ok");
  });

  $("hapus-ai").addEventListener("click", () => {
    try {
      localStorage.removeItem(KUNCI_SIMPAN);
    } catch {
      /* tidak apa-apa kalau gagal */
    }
    $("kunci").value = "";
    pesan("pesan-ai", "Pengaturan dihapus dari peramban ini.", "info");
  });

  $("lihat-kunci").addEventListener("click", () => {
    const k = $("kunci");
    const terbuka = k.type === "text";
    k.type = terbuka ? "password" : "text";
    $("lihat-kunci").textContent = terbuka ? "lihat" : "sembunyi";
  });

  $("uji-ai").addEventListener("click", ujiAi);
  $("mulai").addEventListener("click", mulai);
  $("batal").addEventListener("click", batalkan);
  $("muat-riwayat").addEventListener("click", muatRiwayat);
  $("unduh-zip").addEventListener("click", () => {
    const jalur = jalurJob(jobAktif, "download");
    if (jalur) window.location.assign(jalur);
  });
  $("lihat-log").addEventListener("click", () => {
    if (jobAktif) bukaLog(jobAktif);
  });
  $("tutup-log").addEventListener("click", tutupLog);
  $("modal-log").addEventListener("click", (e) => {
    // Klik di luar kotak (di latar gelap) ikut menutup modal.
    if (e.target === $("modal-log")) tutupLog();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") tutupLog();
  });
}

document.addEventListener("DOMContentLoaded", pasang);
