# F15: nilai p uji Kolmogorov-Smirnov untuk GPD bila parameter ditaksir dari sampel yang sama.
# Bootstrap parametrik: bangkitkan sampel GPD dari parameter taksiran, taksir ulang, hitung statistik KS.
# Pemakaian: Rscript analisis_f15_ks.R <folder AIC_CASE salinan> <folder keluaran>

suppressPackageStartupMessages({ library(data.table); library(extRemes); library(jsonlite) })
argumen <- commandArgs(trailingOnly = TRUE)
DIR_KELUAR <- file.path(argumen[1], "analisis", "2_model_bencana", "keluaran")
KELUAR <- argumen[2]
baca_gz <- function(berkas) { kon <- gzfile(berkas, "rt"); on.exit(close(kon)); fread(text = readLines(kon)) }
campur <- baca_gz(file.path(DIR_KELUAR, "05_ylt_campuran.csv.gz"))
x <- campur$jumlah.S0_dasar
ambang <- quantile(x, 0.95, names = FALSE)
lebih <- x[x > ambang] - ambang
n <- length(lebih)
pgpd <- function(q, skala, bentuk) pevd(q, scale = skala, shape = bentuk, threshold = 0, type = "GP")
taksir <- function(y) { f <- fevd(y, threshold = 0, type = "GP", method = "MLE"); f$results$par }
par0 <- taksir(lebih)
ks0 <- suppressWarnings(ks.test(lebih, function(q) pgpd(q, par0[["scale"]], par0[["shape"]])))
cat(sprintf("n = %d; skala %.6g; bentuk %.4f; statistik KS %.6f; nilai p baku %.4f\n", n, par0[["scale"]], par0[["shape"]], ks0$statistic, ks0$p.value))
cat(sprintf("Nilai yang sama (ties) di antara kelebihan: %d dari %d (YLT disimpan 6 angka penting)\n", n - length(unique(lebih)), n))

set.seed(1505)
B <- 300
stat <- numeric(B)
for (b in seq_len(B)) {
  y <- revd(n, scale = par0[["scale"]], shape = par0[["shape"]], threshold = 0, type = "GP")
  p <- tryCatch(taksir(y), error = function(e) NULL)
  if (is.null(p)) { stat[b] <- NA; next }
  stat[b] <- suppressWarnings(ks.test(y, function(q) pgpd(q, p[["scale"]], p[["shape"]])))$statistic
}
stat <- stat[!is.na(stat)]
p_boot <- (1 + sum(stat >= ks0$statistic)) / (1 + length(stat))
cat(sprintf("Bootstrap parametrik (%d ulangan sah): nilai p terkoreksi %.4f; kuantil 95%% statistik KS bootstrap %.6f\n", length(stat), p_boot, quantile(stat, 0.95)))

# Kestabilan bentuk terhadap pilihan ambang
amb <- c(0.90, 0.95, 0.975, 0.99)
stabil <- rbindlist(lapply(amb, function(a) { u <- quantile(x, a, names = FALSE); y <- x[x > u] - u; p <- taksir(y)
  data.table(kuantil_ambang = a, ambang = u, jumlah = length(y), skala = p[["scale"]], bentuk = p[["shape"]]) }))
print(stabil)
write_json(list(n = n, skala = par0[["scale"]], bentuk = par0[["shape"]], ks_statistik = unname(ks0$statistic), ks_p_baku = ks0$p.value,
                ks_p_bootstrap_parametrik = p_boot, ulangan = length(stat), jumlah_ties = n - length(unique(lebih)),
                kestabilan_ambang = stabil,
                catatan = "Bentuk > 0,5 berarti varians tak hingga; bentuk mendekati 1 berarti rata-rata ekor nyaris tak hingga, sehingga TVaR empiris tidak stabil."),
           file.path(KELUAR, "f15_ks_gpd.json"), auto_unbox = TRUE, pretty = TRUE, digits = 8)
cat("selesai f15\n")
