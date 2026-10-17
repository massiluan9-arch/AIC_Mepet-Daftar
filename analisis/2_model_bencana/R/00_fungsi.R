# Fungsi bersama model kerugian bencana PT Aktu Proteksi.
# Dipanggil lewat source() oleh skrip bernomor di folder ini.

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(jsonlite)
})

# ---------- jalur ----------
.arg <- commandArgs(trailingOnly = FALSE)
.berkas <- sub("^--file=", "", .arg[grep("^--file=", .arg)])
DIR_R <- if (length(.berkas)) dirname(normalizePath(.berkas)) else getwd()
DIR_MODEL <- normalizePath(file.path(DIR_R, ".."))
DIR_KELUAR <- file.path(DIR_MODEL, "keluaran")
DIR_GAMBAR <- file.path(DIR_MODEL, "gambar")
DIR_DATA <- normalizePath(file.path(DIR_MODEL, "..", "1_olah_data", "data"))
DIR_KASUS <- normalizePath(file.path(DIR_MODEL, "..", ".."))
dir.create(DIR_KELUAR, showWarnings = FALSE)
dir.create(DIR_GAMBAR, showWarnings = FALSE)

# ---------- katalog ----------
baca_katalog <- function() {
  berkas <- sort(list.files(file.path(DIR_KASUS, "data", "katastrofe", "gempa", "katalog_usgs"), pattern = "^eq_.*\\.csv$", full.names = TRUE))
  # Kolom waktu dibaca sebagai teks agar tidak bergantung pada tebakan tipe fread.
  k <- rbindlist(lapply(berkas, fread, encoding = "UTF-8", colClasses = list(character = "time")), fill = TRUE)
  k <- k[type == "earthquake", .(waktu = as.POSIXct(substr(time, 1, 19), format = "%Y-%m-%dT%H:%M:%S", tz = "UTC"),
                                  lintang = latitude, bujur = longitude,
                                  dalam = pmax(fifelse(is.na(depth), 10, depth), 5),
                                  mag, jenis_mag = magType)]
  k[, tahun := as.integer(format(waktu, "%Y"))]
  setorder(k, waktu)
  k[]
}

# ---------- geometri ----------
jarak_km <- function(lat1, lon1, lat2, lon2) {
  r <- pi / 180
  a <- sin((lat2 - lat1) * r / 2)^2 + cos(lat1 * r) * cos(lat2 * r) * sin((lon2 - lon1) * r / 2)^2
  2 * 6371 * asin(pmin(1, sqrt(a)))
}

# Panjang ruptur bawah permukaan, semua jenis sesar (Wells & Coppersmith, 1994): log10(L) = -2.44 + 0.59 M
panjang_ruptur_km <- function(m) 10^(-2.44 + 0.59 * m)

# ---------- persamaan intensitas Allen, Wald & Worden (2012) ----------
mmi_allen_rhyp <- function(m, r) {
  rm <- -0.209 + 2.042 * exp(m - 5)
  2.085 + 1.428 * m - 1.402 * log(sqrt(r^2 + rm^2)) + ifelse(r > 50, 0.078 * log(pmax(r, 50) / 50), 0)
}
mmi_allen_rrup <- function(m, r) {
  3.950 + 0.913 * m - 1.107 * log(sqrt(r^2 + (1 + 0.813 * exp(m - 5))^2))
}

# ---------- kurva kerentanan ----------
# Aulady & Fujimi (2019): logistik per tipe bangunan (data/katastrofe/gempa/kerentanan_bangunan/V03), bobot tipologi V01.
AULADY <- data.table(tipe = c("CM", "UM", "RCMR", "TF", "RCLR"),
                     mmi50 = c(8.891, 8.774, 8.393, 9.057, 8.976),
                     k = c(2.736, 1.931, 4.025, 1.844, 2.411),
                     bobot = c(0.5389, 0.1886, 0.1497, 0.0868, 0.0359))
kurva_aulady <- function(mmi) {
  d <- 0
  for (i in seq_len(nrow(AULADY))) d <- d + AULADY$bobot[i] / (1 + exp(-AULADY$k[i] * (mmi - AULADY$mmi50[i])))
  ifelse(mmi < 5.5, 0, d / sum(AULADY$bobot))
}
# PAGER Indonesia (Jaiswal & Wald, 2013): rasio kerugian = Phi(ln(MMI / theta) / beta)
kurva_pager <- function(mmi) pnorm(log(pmax(mmi, 1e-6) / 10.211) / 0.103)

# ---------- syarat polis: risiko sendiri dan batas ganti rugi ----------
# Semua besaran adalah fraksi nilai pertanggungan satu risiko. y = rasio kerusakan bruto, rs = risiko sendiri
# (titik lekat/attachment), batas = batas ganti rugi.
# Arti `batas` ditentukan DASAR_BATAS (Rev. 2):
#   "bayar": batas = pembayaran maksimum setelah risiko sendiri (sesuai Persamaan 3 paper):
#            bayar = min{(y - rs)+, batas};        lapisan dijamin (rs, rs + batas]
#   "rugi" : batas = kerugian bruto tertinggi yang dijamin (perilaku kode Rev. 1):
#            bayar = min{(y - rs)+, batas - rs};   lapisan dijamin (rs, batas]; pembayaran maksimum batas - rs
DASAR_BATAS <- "bayar"
# Presisi distribusi Beta rasio kerusakan per risiko (asumsi; satu-satunya definisi, dipakai skrip 03 dan 04).
# Uji kepekaan nu = 1,5 dan 6: analisis/6_uji_kepekaan.
NU <- 3
titik_habis <- function(risiko_sendiri, batas, dasar = DASAR_BATAS) {
  dasar <- match.arg(dasar, c("bayar", "rugi"))
  if (dasar == "bayar") pmin(risiko_sendiri + batas, 1) else pmin(pmax(batas, risiko_sendiri), 1)
}
# Pembayaran deterministik untuk satu risiko dengan rasio kerusakan y.
bayar_per_risiko <- function(y, risiko_sendiri = 0, batas = 1, dasar = DASAR_BATAS) {
  pmin(pmax(y - risiko_sendiri, 0), titik_habis(risiko_sendiri, batas, dasar) - risiko_sendiri)
}
# Nilai harapan pembayaran bila rasio kerusakan tiap risiko berdistribusi Beta dengan rata-rata mu dan
# presisi nu (a = mu nu, b = (1 - mu) nu). lev(x) = E[min(Y, x)] adalah nilai harapan terbatas
# (limited expected value; Klugman dkk., 2019), sehingga
#   E[bayar] = lev(titik habis) - lev(rs).
lev_beta <- function(mu, nu, risiko_sendiri = 0, batas = 1, dasar = DASAR_BATAS) {
  mu <- pmin(pmax(mu, 1e-9), 1 - 1e-9)
  a <- mu * nu; b <- (1 - mu) * nu
  lev <- function(x) mu * pbeta(x, a + 1, b) + x * (1 - pbeta(x, a, b))   # E[min(Y, x)]
  lev(titik_habis(risiko_sendiri, batas, dasar)) - lev(risiko_sendiri)
}

# ---------- ukuran risiko ----------
ukuran_risiko <- function(x) {
  q <- quantile(x, c(0.99, 0.995, 0.999), names = FALSE)
  c(aal = mean(x), sd = sd(x), var_99 = q[1], var_99_5 = q[2], var_99_9 = q[3],
    tvar_99_5 = mean(x[x >= q[2]]), p_nol = mean(x == 0))
}
galat_baku_kelompok <- function(x, f, kelompok = 20, benih = 1) {
  set.seed(benih)
  g <- sample(rep_len(seq_len(kelompok), length(x)))
  sd(tapply(x, g, f)) / sqrt(kelompok)
}

# ---------- tampilan grafik (selaras dengan gambar Python di analisis/3_investasi_mmbr) ----------
# Membaca berkas csv.gz tanpa paket tambahan (fread langsung memerlukan R.utils).
baca_gz <- function(berkas) {
  kon <- gzfile(berkas, "rt"); on.exit(close(kon))
  fread(text = readLines(kon))
}

WARNA <- c(biru = "#2a78d6", jingga = "#eb6834", toska = "#1baf7a", kuning = "#eda100", magenta = "#e87ba4")
tema_aic <- function() {
  theme_minimal(base_size = 10) +
    theme(plot.background = element_rect(fill = "#fcfcfb", colour = NA),
          panel.background = element_rect(fill = "#fcfcfb", colour = NA),
          panel.grid.major = element_line(colour = "#e1e0d9", linewidth = 0.3),
          panel.grid.minor = element_blank(),
          axis.text = element_text(colour = "#52514e"), axis.title = element_text(colour = "#52514e"),
          plot.title = element_text(face = "bold", colour = "#0b0b0b", size = 10.5),
          legend.position = "top", legend.title = element_blank(), legend.justification = "left")
}
simpan_gambar <- function(p, nama, lebar = 7.2, tinggi = 3.8) {
  ggsave(file.path(DIR_GAMBAR, nama), p, width = lebar, height = tinggi, dpi = 200, bg = "#fcfcfb")
}
koma <- function(x, d = 2) format(round(x, d), nsmall = d, decimal.mark = ",", big.mark = ".", trim = TRUE)
