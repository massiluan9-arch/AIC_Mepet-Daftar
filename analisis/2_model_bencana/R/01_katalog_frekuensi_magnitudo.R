# 01. Katalog gempa: kelengkapan, frekuensi tahunan, dan distribusi magnitudo.
# Keluaran: keluaran/01_*.csv, keluaran/01_parameter.json, gambar/e1_*.png
# Jalankan: Rscript R/01_katalog_frekuensi_magnitudo.R

.arg <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)]))), "00_fungsi.R"))
suppressPackageStartupMessages({ library(MASS); library(fitdistrplus) })

TAHUN <- 1976:2025
M_MIN <- 5.5          # batas bawah simulasi
M_MAKS <- 9.2         # sedikit di atas magnitudo terbesar katalog (Sumatra 2004, Mw 9,1)

k <- baca_katalog()[tahun %in% TAHUN]
cat(sprintf("Katalog USGS %d-%d: %d gempa M >= %.1f\n", min(TAHUN), max(TAHUN), nrow(k), min(k$mag)))

# ---------- 1. Kelengkapan: jumlah per dasawarsa dan kelas magnitudo ----------
k[, dasawarsa := paste0(10 * (tahun %/% 10), "-an")]
k[, kelas := cut(mag, c(5, 5.5, 6, 6.5, 7, 10), right = FALSE, labels = c("5,0-5,4", "5,5-5,9", "6,0-6,4", "6,5-6,9", ">=7,0"))]
lengkap <- dcast(k[, .N, by = .(dasawarsa, kelas)], dasawarsa ~ kelas, value.var = "N", fill = 0)
tahun_das <- k[, .(tahun_teramati = uniqueN(tahun)), by = dasawarsa]
lengkap <- merge(lengkap, tahun_das, by = "dasawarsa")
fwrite(lengkap, file.path(DIR_KELUAR, "01_kelengkapan.csv"))
print(lengkap)

# ---------- 2. Nilai b (Aki, 1965; galat baku Shi & Bolt, 1982) ----------
nilai_b <- function(m, mc, lebar = 0.1) {
  m <- m[m >= mc]; n <- length(m)
  b <- log10(exp(1)) / (mean(m) - (mc - lebar / 2))
  se <- 2.30 * b^2 * sqrt(sum((m - mean(m))^2) / (n * (n - 1)))
  data.table(mc = mc, n = n, b = b, galat_baku = se)
}
tabel_b <- rbindlist(lapply(c(5.0, 5.5, 6.0, 6.5), function(mc) nilai_b(k$mag, mc)))
fwrite(tabel_b, file.path(DIR_KELUAR, "01_nilai_b.csv"))
print(tabel_b)
b_pakai <- tabel_b[mc == M_MIN, b]

# Kecocokan eksponensial terpotong pada M >= M_MIN: uji chi-kuadrat atas kelas 0,5 satuan
beta <- b_pakai * log(10)
cdf_te <- function(m) (1 - exp(-beta * (m - M_MIN))) / (1 - exp(-beta * (M_MAKS - M_MIN)))
batas <- c(seq(M_MIN - 0.05, 7.95, by = 0.5), 10)
m_sim <- k[mag >= M_MIN, mag]
amati <- as.numeric(table(cut(m_sim, batas, right = FALSE)))
harap <- length(m_sim) * diff(cdf_te(pmin(pmax(batas + 0.05, M_MIN), M_MAKS)))
chi_mag <- sum((amati - harap)^2 / harap)
db_mag <- length(amati) - 1 - 1
uji_mag <- data.table(kelas = levels(cut(m_sim, batas, right = FALSE)), amati = amati, harap = round(harap, 1))
fwrite(uji_mag, file.path(DIR_KELUAR, "01_uji_magnitudo.csv"))
cat(sprintf("Magnitudo: chi-kuadrat %.1f, db %d, nilai p %.4f\n", chi_mag, db_mag, pchisq(chi_mag, db_mag, lower.tail = FALSE)))

# ---------- 3. Deklasterisasi jendela Gardner & Knopoff (1974) ----------
deklaster <- function(k) {
  t <- as.numeric(difftime(k$waktu, as.POSIXct("1976-01-01", tz = "UTC"), units = "days"))
  utama <- rep(TRUE, nrow(k))
  for (i in order(-k$mag)) {
    if (!utama[i]) next
    m <- k$mag[i]
    d <- 10^(0.1238 * m + 0.983)
    w <- if (m >= 6.5) 10^(0.032 * m + 2.7389) else 10^(0.5409 * m - 0.547)
    idx <- which(t > t[i] - 0.05 * w & t < t[i] + w & k$mag <= m)
    idx <- idx[jarak_km(k$lintang[i], k$bujur[i], k$lintang[idx], k$bujur[idx]) <= d]
    utama[idx] <- FALSE
    utama[i] <- TRUE
  }
  utama
}
k[, utama := deklaster(k)]
cat(sprintf("Deklasterisasi: %d dari %d kejadian tersisa (%.0f%%)\n", sum(k$utama), nrow(k), 100 * mean(k$utama)))

# ---------- 4. Frekuensi tahunan: Poisson lawan binomial negatif ----------
uji_frekuensi <- function(label, tahun_kejadian) {
  n <- as.numeric(table(factor(tahun_kejadian, levels = TAHUN)))
  mu <- mean(n); v <- var(n)
  fp <- fitdist(n, "pois")
  fn <- tryCatch(fitdist(n, "nbinom"), error = function(e) NULL)
  disp <- (length(n) - 1) * v / mu
  out <- data.table(deret = label, tahun = length(n), rata = mu, varians = v, rasio_varians = v / mu,
                    statistik_dispersi = disp, p_dispersi = pchisq(disp, length(n) - 1, lower.tail = FALSE),
                    aic_poisson = fp$aic, aic_binomial_negatif = if (is.null(fn)) NA_real_ else fn$aic,
                    ukuran_nb = if (is.null(fn)) NA_real_ else fn$estimate[["size"]],
                    mu_nb = if (is.null(fn)) NA_real_ else fn$estimate[["mu"]])
  if (!is.null(fn)) {
    g <- tryCatch(gofstat(list(fp, fn), fitnames = c("poisson", "nb")), error = function(e) NULL)
    if (!is.null(g)) {
      out[, `:=`(p_chi2_poisson = g$chisqpvalue[["poisson"]], p_chi2_nb = g$chisqpvalue[["nb"]])]
    }
    lrt <- 2 * (fn$loglik - fp$loglik)
    out[, `:=`(statistik_lrt = lrt, p_lrt = 0.5 * pchisq(lrt, 1, lower.tail = FALSE))]
  }
  list(tabel = out, hitungan = n)
}
h55 <- uji_frekuensi("M >= 5,5, katalog penuh", k[mag >= 5.5, tahun])
h60 <- uji_frekuensi("M >= 6,0, katalog penuh", k[mag >= 6.0, tahun])
h70 <- uji_frekuensi("M >= 7,0, katalog penuh", k[mag >= 7.0, tahun])
d55 <- uji_frekuensi("M >= 5,5, setelah deklasterisasi", k[mag >= 5.5 & utama == TRUE, tahun])
d60 <- uji_frekuensi("M >= 6,0, setelah deklasterisasi", k[mag >= 6.0 & utama == TRUE, tahun])
frek <- rbindlist(list(h55$tabel, h60$tabel, h70$tabel, d55$tabel, d60$tabel), fill = TRUE)
fwrite(frek, file.path(DIR_KELUAR, "01_frekuensi.csv"))
print(frek[, .(deret, rata = round(rata, 2), rasio_varians = round(rasio_varians, 2), p_dispersi = signif(p_dispersi, 3),
               aic_poisson = round(aic_poisson, 1), aic_nb = round(aic_binomial_negatif, 1), p_lrt = signif(p_lrt, 3))])

# ---------- 5. Parameter untuk simulasi ----------
dasar <- h55$tabel
par <- list(
  sumber = "Katalog USGS 1976-2025, M >= 5, lintang -11..6, bujur 95..141",
  m_min = M_MIN, m_maks = M_MAKS,
  nilai_b = b_pakai, galat_baku_b = tabel_b[mc == M_MIN, galat_baku],
  frekuensi = list(distribusi = "binomial negatif", rata = dasar$mu_nb, ukuran = dasar$ukuran_nb,
                   rata_empiris = dasar$rata, varians_empiris = dasar$varians),
  jumlah_episenter = k[mag >= M_MIN, .N],
  deklasterisasi_porsi_tersisa = mean(k$utama)
)
write_json(par, file.path(DIR_KELUAR, "01_parameter.json"), auto_unbox = TRUE, pretty = TRUE, digits = 8)
fwrite(k[mag >= M_MIN, .(lintang, bujur, dalam, mag, tahun)], file.path(DIR_KELUAR, "01_episenter.csv"))

# ---------- 6. Gambar ----------
hit <- data.table(tahun = TAHUN, jumlah = h55$hitungan)
x <- 0:max(hit$jumlah + 15)
pmf <- rbind(data.table(x = x, peluang = dpois(x, dasar$rata), model = "Poisson"),
             data.table(x = x, peluang = dnbinom(x, size = dasar$ukuran_nb, mu = dasar$mu_nb), model = "Binomial negatif"))
p1 <- ggplot(hit, aes(jumlah)) +
  geom_histogram(aes(y = after_stat(density)), binwidth = 5, fill = "#c3c2b7", colour = "#fcfcfb") +
  geom_line(data = pmf, aes(x, peluang, colour = model), linewidth = 0.8) +
  scale_colour_manual(values = c("Binomial negatif" = WARNA[["biru"]], "Poisson" = WARNA[["jingga"]])) +
  labs(x = "Jumlah gempa M >= 5,5 per tahun (1976-2025)", y = "Kepadatan") + tema_aic()
simpan_gambar(p1, "e1_frekuensi_tahunan.png", 6.2, 3.4)

kum <- data.table(m = seq(M_MIN, 9.1, by = 0.1))
kum[, amati := sapply(m, function(z) sum(k$mag >= z - 1e-9)) / length(TAHUN)]
kum[, model := dasar$rata * (1 - cdf_te(m))]
p2 <- ggplot(kum[amati > 0], aes(m)) +
  geom_point(aes(y = amati, colour = "Katalog"), size = 1.6) +
  geom_line(aes(y = model, colour = "Eksponensial terpotong"), linewidth = 0.8) +
  scale_y_log10() +
  scale_colour_manual(values = c("Katalog" = "#52514e", "Eksponensial terpotong" = WARNA[["biru"]])) +
  labs(x = "Magnitudo", y = "Laju tahunan gempa >= M (skala log)") + tema_aic()
simpan_gambar(p2, "e2_frekuensi_magnitudo.png", 6.2, 3.4)
cat("selesai 01\n")
