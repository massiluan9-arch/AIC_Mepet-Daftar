# 05. Konsistensi model terhadap pengalaman klaim industri, bobot kurva, dan ekor distribusi.
# (a) Rata-rata klaim 21 tahun dan 5 tahun hasil simulasi dibandingkan dengan pengalaman MAIPARK.
# (b) Bobot tiap kurva kerentanan = peluang posterior (prior sama rata) dari pengalaman 21 tahun.
# (c) Distribusi Pareto umum (GPD) di atas ambang untuk kerugian tahunan kurva campuran.
# (d) Pembanding luar: Anwar dkk. (2025), tarif rata-rata MAIPARK.
# Keluaran: keluaran/05_*.csv, keluaran/05_parameter.json, gambar/e5_*.png

.arg <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)]))), "00_fungsi.R"))
suppressPackageStartupMessages(library(extRemes))

ylt <- baca_gz(file.path(DIR_KELUAR, "04_ylt.csv.gz"))
industri <- fromJSON(file.path(DIR_DATA, "besaran_industri.json"))
kej <- fread(file.path(DIR_DATA, "maipark_kejadian_klaim.csv"))
KURVA <- c("klaim", "aulady", "pager")
N <- nrow(ylt)

# ---------- (a) pengalaman industri ----------
# Eksposur 2020-2024 teramati. Tahun 2004-2019 dihitung mundur dengan kenaikan rata-rata yang
# dilaporkan MAIPARK (14,51% per tahun); 10% dan 20% sebagai uji banding.
eks <- unlist(industri$eksposur_uy_triliun)
klaim_gempa <- kej[jenis == "gempa", sum(klaim_incurred_miliar)]
pengalaman <- function(tumbuh) {
  mundur <- eks[["2020"]] / (1 + tumbuh)^(1:16)
  klaim_gempa / ((sum(mundur) + sum(eks)) * 1000)        # fraksi nilai pertanggungan per tahun
}
amati21 <- pengalaman(0.1451)
amati5 <- industri$klaim_per_eksposur_5_tahun_per_mil / 1000
cat(sprintf("Pengalaman klaim gempa: 21 tahun %.4f per mil (rentang %.4f sampai %.4f); 5 tahun %.4f per mil\n",
            1000 * amati21, 1000 * pengalaman(0.20), 1000 * pengalaman(0.10), 1000 * amati5))

set.seed(505)
B <- 20000
blok <- function(x, panjang) rowMeans(matrix(sample(x, B * panjang, TRUE), B, panjang))
kons <- rbindlist(lapply(KURVA, function(kv) {
  x <- ylt[[paste0("jumlah.", kv, ".S0_dasar")]]
  b21 <- blok(x, 21); b5 <- blok(x, 5)
  # kepadatan rata-rata 21 tahun pada nilai teramati, dalam skala log
  kd <- density(log(pmax(b21, 1e-9)), n = 2048)
  data.table(kurva = kv, aal = mean(x), median_21 = median(b21), p5_21 = quantile(b21, 0.05), p95_21 = quantile(b21, 0.95),
             persentil_amati_21 = mean(b21 <= amati21), median_5 = median(b5), persentil_amati_5 = mean(b5 <= amati5),
             kepadatan_log = approx(kd$x, kd$y, log(amati21), rule = 2)$y)
}))
kons[, bobot := kepadatan_log / sum(kepadatan_log)]
fwrite(kons, file.path(DIR_KELUAR, "05_konsistensi_klaim_industri.csv"))
print(kons[, .(kurva, aal_permil = round(1000 * aal, 4), median_21 = round(1000 * median_21, 4), p5_21 = round(1000 * p5_21, 4),
               p95_21 = round(1000 * p95_21, 4), persentil_amati_21 = round(persentil_amati_21, 3),
               persentil_amati_5 = round(persentil_amati_5, 3), bobot = round(bobot, 3))])

# Kepekaan bobot terhadap asumsi pertumbuhan eksposur
kepekaan <- rbindlist(lapply(c(0.10, 0.1451, 0.20), function(g) {
  a <- pengalaman(g)
  kd <- sapply(KURVA, function(kv) { b21 <- blok(ylt[[paste0("jumlah.", kv, ".S0_dasar")]], 21)
    d <- density(log(pmax(b21, 1e-9)), n = 2048); approx(d$x, d$y, log(a), rule = 2)$y })
  data.table(pertumbuhan = g, pengalaman_permil = 1000 * a, t(kd / sum(kd)))
}))
fwrite(kepekaan, file.path(DIR_KELUAR, "05_kepekaan_bobot.csv"))
print(kepekaan)

# ---------- Rev. 2: kepekaan bobot terhadap pembilang, pertumbuhan, jendela lima tahun, dan statistik ----------
# Rata-rata bootstrap diulang dengan benih dan urutan yang sama seperti di atas, sehingga kasus dasar sama persis
# dengan bobot yang dipakai. Blok ini tidak mengubah bobot maupun cabang kurva campuran (benih 506 dipasang ulang).
set.seed(505)
b21_s <- list(); b5_s <- list()
for (kv in KURVA) { xx <- ylt[[paste0("jumlah.", kv, ".S0_dasar")]]; b21_s[[kv]] <- blok(xx, 21); b5_s[[kv]] <- blok(xx, 5) }
kepadatan_di <- function(b, a) { kd <- density(log(pmax(b, 1e-9)), n = 2048); approx(kd$x, kd$y, log(a), rule = 2)$y }
baris_peka <- function(kasus, statistik, a, daftar, ket) {
  k <- sapply(KURVA, function(kv) kepadatan_di(daftar[[kv]], a)); w <- k / sum(k)
  data.table(kasus = kasus, statistik = statistik, pengalaman_permil = 1000 * a, bobot_klaim = w[["klaim"]], bobot_aulady = w[["aulady"]],
             bobot_pager = w[["pager"]], persentil_klaim = mean(daftar$klaim <= a), persentil_aulady = mean(daftar$aulady <= a),
             persentil_pager = mean(daftar$pager <= a), keterangan = ket)
}
eksposur_21 <- function(tumbuh) c(rev(eks[["2020"]] / (1 + tumbuh)^(1:16)), eks)
pengalaman_kali <- function(tumbuh, kali) kali * pengalaman(tumbuh)
sama_rata <- "rata-rata 21 tahun sama rata (dasar)"
peka <- rbind(
  baris_peka("dasar", sama_rata, amati21, b21_s, "13 kejadian gempa dalam daftar klaim terbesar; pertumbuhan 14,51%"),
  baris_peka("pembilang_x1.25", sama_rata, pengalaman_kali(0.1451, 1.25), b21_s, "pembilang tidak lengkap, dinaikkan 25%"),
  baris_peka("pembilang_x1.5", sama_rata, pengalaman_kali(0.1451, 1.5), b21_s, "pembilang dinaikkan 50%"),
  baris_peka("pembilang_x2", sama_rata, pengalaman_kali(0.1451, 2), b21_s, "pembilang dinaikkan 100%"),
  baris_peka("pertumbuhan_10", sama_rata, pengalaman(0.10), b21_s, "eksposur 2004-2019 dihitung mundur 10%"),
  baris_peka("pertumbuhan_20", sama_rata, pengalaman(0.20), b21_s, "eksposur 2004-2019 dihitung mundur 20%"),
  baris_peka("lima_tahun", "rata-rata 5 tahun sama rata", amati5, b5_s, "klaim seluruh provinsi UY 2020-2024 dibagi eksposur 2020-2024")
)
stopifnot(max(abs(unlist(peka[1, .(bobot_klaim, bobot_aulady, bobot_pager)]) - kons$bobot)) < 1e-12)
set.seed(605)
for (g in c(0.10, 0.1451, 0.20)) {
  w21 <- eksposur_21(g)
  bw <- lapply(setNames(KURVA, KURVA), function(kv) {
    m <- matrix(sample(ylt[[paste0("jumlah.", kv, ".S0_dasar")]], B * 21, TRUE), B, 21); as.numeric(m %*% (w21 / sum(w21))) })
  for (kali in c(1, 1.5, 2)) peka <- rbind(peka, baris_peka(sprintf("berbobot_eksposur_g%s_pembilang_x%s", 100 * g, kali),
    "rata-rata 21 tahun berbobot eksposur (setara jumlah klaim dibagi jumlah eksposur)", pengalaman_kali(g, kali), bw,
    sprintf("jumlah tahun efektif %.1f", sum(w21)^2 / sum(w21^2))))
}
fwrite(peka, file.path(DIR_KELUAR, "05_kepekaan_pembilang.csv"))
print(peka[, .(kasus, pengalaman_permil = round(pengalaman_permil, 4), klaim = round(bobot_klaim, 3), aulady = round(bobot_aulady, 3), pager = round(bobot_pager, 3))])

# ---------- (b) kurva campuran: tiap tahun simulasi mengikuti satu kurva menurut bobotnya ----------
bobot <- setNames(kons$bobot, kons$kurva)
set.seed(506)
cabang <- sample(KURVA, N, TRUE, prob = bobot[KURVA])
strategi <- unique(sub("^jumlah\\.[a-z]+\\.", "", grep("^jumlah\\.klaim\\.", names(ylt), value = TRUE)))
campur <- data.table(tahun = ylt$tahun, cabang = cabang)
for (st in strategi) for (jenis in c("jumlah", "maks")) {
  m <- as.matrix(ylt[, paste(jenis, KURVA, st, sep = "."), with = FALSE])
  campur[[paste(jenis, st, sep = ".")]] <- m[cbind(seq_len(N), match(cabang, KURVA))]
}
fwrite(campur, file.path(DIR_KELUAR, "05_ylt_campuran.csv.gz"))
ukur <- rbindlist(lapply(strategi, function(st) {
  x <- campur[[paste0("jumlah.", st)]]
  data.table(strategi = st, t(ukuran_risiko(x)),
             galat_baku_var_99_5 = galat_baku_kelompok(x, function(z) quantile(z, 0.995)),
             maks_kejadian_var_99_5 = quantile(campur[[paste0("maks.", st)]], 0.995, names = FALSE))
}))
fwrite(ukur, file.path(DIR_KELUAR, "05_ukuran_risiko_campuran.csv"))
print(ukur[, .(strategi, aal_permil = round(1000 * aal, 4), var_99 = round(100 * var_99, 3), var_99_5 = round(100 * var_99_5, 3),
               var_99_9 = round(100 * var_99_9, 3), tvar_99_5 = round(100 * tvar_99_5, 3), gb = round(100 * galat_baku_var_99_5, 3))])

# ---------- (c) ekor: GPD di atas ambang (kurva campuran, strategi dasar) ----------
x <- campur$jumlah.S0_dasar
ambang <- quantile(x, 0.95, names = FALSE)
lebih <- x[x > ambang]
gp <- fevd(x, threshold = ambang, type = "GP", method = "MLE")
par_gp <- gp$results$par
ks <- ks.test(lebih - ambang, function(q) pevd(q, scale = par_gp[["scale"]], shape = par_gp[["shape"]], threshold = 0, type = "GP"))
# Rev. 2: nilai p KS baku mengandaikan parameter tidak ditaksir dari sampel yang sama. Nilai p terkoreksi dihitung
# dengan bootstrap parametrik: sampel GPD dibangkitkan dari parameter taksiran, ditaksir ulang, lalu diuji.
set.seed(1505)
B_KS <- 300
ks_boot <- sapply(seq_len(B_KS), function(i) {
  y <- revd(length(lebih), scale = par_gp[["scale"]], shape = par_gp[["shape"]], threshold = 0, type = "GP")
  p <- tryCatch(fevd(y, threshold = 0, type = "GP", method = "MLE")$results$par, error = function(e) NULL)
  if (is.null(p)) return(NA_real_)
  suppressWarnings(ks.test(y, function(q) pevd(q, scale = p[["scale"]], shape = p[["shape"]], threshold = 0, type = "GP")))$statistic
})
ks_boot <- ks_boot[!is.na(ks_boot)]
ks_p_boot <- (1 + sum(ks_boot >= ks$statistic)) / (1 + length(ks_boot))
pu <- mean(x > ambang)
q_gpd <- function(p) ambang + par_gp[["scale"]] / par_gp[["shape"]] * (((1 - p) / pu)^(-par_gp[["shape"]]) - 1)
ekor <- data.table(ambang = ambang, jumlah_di_atas = length(lebih), skala = par_gp[["scale"]], bentuk = par_gp[["shape"]],
                   ks_statistik = ks$statistic, ks_p = ks$p.value,
                   var_99_5_empiris = quantile(x, 0.995), var_99_5_gpd = q_gpd(0.995),
                   var_99_9_empiris = quantile(x, 0.999), var_99_9_gpd = q_gpd(0.999),
                   ks_p_bootstrap_parametrik = ks_p_boot, ks_bootstrap_ulangan = length(ks_boot))
fwrite(ekor, file.path(DIR_KELUAR, "05_ekor_gpd.csv"))
print(ekor)
# Rata-rata kelebihan di atas ambang (mean residual life) untuk memeriksa pilihan ambang
u_grid <- quantile(x, seq(0.80, 0.995, by = 0.005), names = FALSE)
mrl <- data.table(ambang = u_grid, rata_kelebihan = sapply(u_grid, function(u) mean(x[x > u] - u)))
fwrite(mrl, file.path(DIR_KELUAR, "05_rata_kelebihan.csv"))

# ---------- (d) pembanding luar ----------
anwar <- c(premi_murni = 0.3994e-3, pml_100 = 0.0048, pml_250 = 0.0092, pml_1000 = 0.0237)   # Anwar dkk. (2025), fraksi nilai struktur
banding <- rbindlist(lapply(c(KURVA, "campuran"), function(kv) {
  xx <- if (kv == "campuran") campur$jumlah.S0_dasar else ylt[[paste0("jumlah.", kv, ".S0_dasar")]]
  data.table(sumber = kv, premi_murni_permil = 1000 * mean(xx), pml_100 = quantile(xx, 0.99), pml_250 = quantile(xx, 0.996),
             pml_1000 = quantile(xx, 0.999), rasio_klaim_terhadap_tarif = mean(xx) / (industri$tarif_gempa_rata_per_mil / 1000))
}))
banding <- rbind(banding, data.table(sumber = "Anwar dkk. (2025), hunian nasional, tanpa risiko sendiri",
                                     premi_murni_permil = 1000 * anwar[["premi_murni"]], pml_100 = anwar[["pml_100"]],
                                     pml_250 = anwar[["pml_250"]], pml_1000 = anwar[["pml_1000"]], rasio_klaim_terhadap_tarif = NA),
                 data.table(sumber = "Pengalaman klaim industri 2004-2024 (MAIPARK)", premi_murni_permil = 1000 * amati21,
                            pml_100 = NA, pml_250 = NA, pml_1000 = NA, rasio_klaim_terhadap_tarif = amati21 / (industri$tarif_gempa_rata_per_mil / 1000)))
fwrite(banding, file.path(DIR_KELUAR, "05_pembanding.csv"))
print(banding)

write_json(list(bobot_kurva = as.list(bobot), pengalaman_21_tahun_permil = 1000 * amati21, pengalaman_5_tahun_permil = 1000 * amati5,
                pertumbuhan_eksposur_hitung_mundur = 0.1451, benih_cabang = 506,
                gpd = list(ambang = ambang, skala = par_gp[["scale"]], bentuk = par_gp[["shape"]], ks_p = ks$p.value,
                           ks_p_bootstrap_parametrik = ks_p_boot)),
           file.path(DIR_KELUAR, "05_parameter.json"), auto_unbox = TRUE, pretty = TRUE, digits = 8)

# ---------- gambar: kurva peluang terlampaui ----------
urut <- function(xx, nama) { s <- sort(xx, decreasing = TRUE); data.table(kurva = nama, kerugian = s, peluang = seq_along(s) / length(s)) }
ep <- rbind(urut(ylt$jumlah.aulady.S0_dasar, "Aulady & Fujimi"), urut(ylt$jumlah.pager.S0_dasar, "PAGER"),
            urut(ylt$jumlah.klaim.S0_dasar, "Klaim MAIPARK"), urut(campur$jumlah.S0_dasar, "Campuran berbobot"))
ep <- ep[peluang <= 0.2 & kerugian > 0][, .SD[unique(round(exp(seq(log(1), log(.N), length.out = 400))))], by = kurva]
p <- ggplot(ep, aes(100 * kerugian, peluang, colour = kurva, linewidth = kurva)) + geom_line() +
  geom_hline(yintercept = 0.005, colour = "#52514e", linewidth = 0.3) +
  annotate("text", x = 0.0012, y = 0.0058, label = "1 dalam 200 tahun", hjust = 0, size = 2.8, colour = "#52514e") +
  scale_y_log10(breaks = c(0.2, 0.1, 0.02, 0.01, 0.005, 0.001, 0.0001), labels = function(z) paste0(format(100 * z, drop0trailing = TRUE, decimal.mark = ","), "%")) +
  scale_x_log10(labels = function(z) paste0(format(z, drop0trailing = TRUE, decimal.mark = ","), "%")) +
  scale_colour_manual(values = c("Campuran berbobot" = "#0b0b0b", "Aulady & Fujimi" = WARNA[["jingga"]], "PAGER" = WARNA[["toska"]], "Klaim MAIPARK" = WARNA[["biru"]])) +
  scale_linewidth_manual(values = c("Campuran berbobot" = 1.1, "Aulady & Fujimi" = 0.7, "PAGER" = 0.7, "Klaim MAIPARK" = 0.7), guide = "none") +
  labs(x = "Kerugian tahunan (% nilai pertanggungan gempa, skala log)", y = "Peluang terlampaui setahun (skala log)") + tema_aic()
simpan_gambar(p, "e5_kurva_peluang_terlampaui.png", 6.8, 4.0)
cat("selesai 05\n")
