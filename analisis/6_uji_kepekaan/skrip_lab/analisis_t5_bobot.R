# T5: kepekaan bobot kurva kerentanan terhadap pembilang, pertumbuhan eksposur, jendela 5 tahun, dan pilihan metode.
# Meniru persis langkah (a) skrip 05 (benih 505, B = 20000, urutan tarikan sama), lalu mengganti nilai teramati.
# Pemakaian: Rscript analisis_t5_bobot.R <folder AIC_CASE salinan> <folder keluaran>

suppressPackageStartupMessages({ library(data.table); library(jsonlite) })
argumen <- commandArgs(trailingOnly = TRUE)
AKAR <- argumen[1]; KELUAR <- argumen[2]
dir.create(KELUAR, showWarnings = FALSE, recursive = TRUE)
DIR_KELUAR <- file.path(AKAR, "analisis", "2_model_bencana", "keluaran")
DIR_DATA <- file.path(AKAR, "analisis", "1_olah_data", "data")
baca_gz <- function(berkas) { kon <- gzfile(berkas, "rt"); on.exit(close(kon)); fread(text = readLines(kon)) }

ylt <- baca_gz(file.path(DIR_KELUAR, "04_ylt.csv.gz"))
industri <- fromJSON(file.path(DIR_DATA, "besaran_industri.json"))
kej <- fread(file.path(DIR_DATA, "maipark_kejadian_klaim.csv"))
par05 <- fromJSON(file.path(DIR_KELUAR, "05_parameter.json"))
KURVA <- c("klaim", "aulady", "pager")
X <- lapply(setNames(KURVA, KURVA), function(kv) ylt[[paste0("jumlah.", kv, ".S0_dasar")]])

eks <- unlist(industri$eksposur_uy_triliun)
klaim_gempa <- kej[jenis == "gempa", sum(klaim_incurred_miliar)]
klaim_erupsi <- kej[jenis == "erupsi", sum(klaim_incurred_miliar)]
eksposur_21 <- function(tumbuh) c(rev(eks[["2020"]] / (1 + tumbuh)^(1:16)), eks)      # 2004..2024, triliun
pengalaman <- function(tumbuh, kali = 1, klaim = klaim_gempa) klaim * kali / (sum(eksposur_21(tumbuh)) * 1000)
amati21 <- pengalaman(0.1451)
amati5 <- industri$klaim_per_eksposur_5_tahun_per_mil / 1000

# ---------- bootstrap persis seperti skrip 05 ----------
set.seed(505)
B <- 20000
blok <- function(x, panjang) rowMeans(matrix(sample(x, B * panjang, TRUE), B, panjang))
b21 <- list(); b5 <- list()
for (kv in KURVA) { b21[[kv]] <- blok(X[[kv]], 21); b5[[kv]] <- blok(X[[kv]], 5) }
kepadatan <- function(b, a, adjust = 1) { kd <- density(log(pmax(b, 1e-9)), n = 2048, adjust = adjust); approx(kd$x, kd$y, log(a), rule = 2)$y }
bobot <- function(daftar_b, a, adjust = 1) { k <- sapply(KURVA, function(kv) kepadatan(daftar_b[[kv]], a, adjust)); k / sum(k) }
persentil <- function(daftar_b, a) sapply(KURVA, function(kv) mean(daftar_b[[kv]] <= a))
dasar <- bobot(b21, amati21)
cat(sprintf("Bobot dasar hasil tiru: klaim %.8f, aulady %.8f, pager %.8f\n", dasar[1], dasar[2], dasar[3]))
cat(sprintf("Bobot di 05_parameter.json: klaim %.8f, aulady %.8f, pager %.8f\n", par05$bobot_kurva$klaim, par05$bobot_kurva$aulady, par05$bobot_kurva$pager))
stopifnot(max(abs(dasar - unlist(par05$bobot_kurva)[KURVA])) < 1e-7)

baris <- function(kasus, metode, a, daftar_b, adjust = 1, ket = "") {
  w <- bobot(daftar_b, a, adjust); p <- persentil(daftar_b, a)
  data.table(kasus = kasus, metode = metode, pengalaman_permil = 1000 * a, bobot_klaim = w[["klaim"]], bobot_aulady = w[["aulady"]],
             bobot_pager = w[["pager"]], persentil_klaim = p[["klaim"]], persentil_aulady = p[["aulady"]], persentil_pager = p[["pager"]], keterangan = ket)
}
hasil <- rbind(
  baris("dasar", "21 tahun, rata-rata sama rata (Rev. 1)", amati21, b21, ket = "13 kejadian gempa terbesar; pertumbuhan 14,51%"),
  baris("pembilang_x1.25", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.1451, 1.25), b21, ket = "pembilang tidak lengkap, dinaikkan 25%"),
  baris("pembilang_x1.5", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.1451, 1.5), b21, ket = "pembilang dinaikkan 50%"),
  baris("pembilang_x2", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.1451, 2), b21, ket = "pembilang dinaikkan 100%"),
  baris("pertumbuhan_10", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.10), b21, ket = "eksposur 2004-2019 dihitung mundur 10%"),
  baris("pertumbuhan_20", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.20), b21, ket = "eksposur 2004-2019 dihitung mundur 20%"),
  baris("pembilang_x2_pertumbuhan_20", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.20, 2), b21, ket = "gabungan paling tinggi"),
  baris("pembilang_x1_pertumbuhan_10", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.10, 1), b21, ket = "gabungan paling rendah (sama dengan pertumbuhan_10)"),
  baris("dengan_erupsi", "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman(0.1451, 1, klaim_gempa + klaim_erupsi), b21, ket = "16 kejadian termasuk tiga erupsi"),
  baris("lima_tahun", "5 tahun UY 2020-2024, rata-rata sama rata", amati5, b5, ket = "klaim seluruh provinsi per tahun penutupan dibagi eksposur 2020-2024")
)

# ---------- pilihan metode ----------
# (i) lebar pita kepadatan
for (adj in c(0.5, 2)) hasil <- rbind(hasil, baris(sprintf("dasar_lebar_pita_x%s", adj), "21 tahun, rata-rata sama rata; lebar pita diubah", amati21, b21, adj))
# (ii) statistik yang setara dengan cara pengalaman dihitung: jumlah klaim dibagi jumlah eksposur = rata-rata berbobot eksposur
set.seed(605)
berbobot <- function(x, w) { m <- matrix(sample(x, B * length(w), TRUE), B, length(w)); as.numeric(m %*% (w / sum(w))) }
for (g in c(0.10, 0.1451, 0.20)) {
  w <- eksposur_21(g)
  bw <- lapply(X, berbobot, w = w)
  n_eff <- sum(w)^2 / sum(w^2)
  for (kali in c(1, 1.5, 2)) hasil <- rbind(hasil, baris(sprintf("berbobot_eksposur_g%s_pembilang_x%s", 100 * g, kali),
                                                         "21 tahun, rata-rata berbobot eksposur (setara dengan pembagian jumlah klaim oleh jumlah eksposur)",
                                                         pengalaman(g, kali), bw, ket = sprintf("jumlah tahun efektif %.1f", n_eff)))
}
# (iii) derau bootstrap: ulangi tarikan dengan 20 benih lain
ulang <- rbindlist(lapply(1:20, function(s) { set.seed(1000 + s); bb <- lapply(X, blok, panjang = 21); as.data.table(t(bobot(bb, amati21))) }))
derau <- data.table(kasus = "derau_bootstrap_20_benih", metode = "21 tahun, rata-rata sama rata (Rev. 1)", pengalaman_permil = 1000 * amati21,
                    bobot_klaim = mean(ulang$klaim), bobot_aulady = mean(ulang$aulady), bobot_pager = mean(ulang$pager),
                    persentil_klaim = NA, persentil_aulady = NA, persentil_pager = NA,
                    keterangan = sprintf("simpangan baku antarbenih: klaim %.4f, aulady %.4f, pager %.4f; rentang aulady %.3f sampai %.3f",
                                         sd(ulang$klaim), sd(ulang$aulady), sd(ulang$pager), min(ulang$aulady), max(ulang$aulady)))
hasil <- rbind(hasil, derau)
fwrite(hasil, file.path(KELUAR, "t5_bobot.csv"))
print(hasil[, .(kasus, pengalaman_permil = round(pengalaman_permil, 4), klaim = round(bobot_klaim, 3), aulady = round(bobot_aulady, 3), pager = round(bobot_pager, 3),
                p_klaim = round(persentil_klaim, 4), p_aulady = round(persentil_aulady, 4), p_pager = round(persentil_pager, 4))])
cat(derau$keterangan, "\n")

# ---------- kelengkapan pembilang: daftar kejadian terbesar lawan klaim seluruh provinsi 2020-2024 ----------
kl <- fread(file.path(DIR_DATA, "maipark_klaim_provinsi.csv"))
klaim_uy <- colSums(kl[, .(uy_2020, uy_2021, uy_2022, uy_2023, uy_2024)]) / 1000        # miliar
kej[, tahun := 2000 + as.integer(sub(".*-", "", tanggal))]
daftar_2020_2024 <- kej[jenis == "gempa" & tahun >= 2020, .(kejadian, tanggal, klaim_incurred_miliar)]
lengkap <- list(
  klaim_seluruh_provinsi_uy_2020_2024_miliar = as.list(round(klaim_uy, 2)), jumlah_uy_2020_2024_miliar = sum(klaim_uy),
  kejadian_gempa_dalam_daftar_2020_2024 = daftar_2020_2024, jumlah_daftar_2020_2024_miliar = sum(daftar_2020_2024$klaim_incurred_miliar),
  rasio_seluruh_terhadap_daftar = sum(klaim_uy) / sum(daftar_2020_2024$klaim_incurred_miliar),
  klaim_gempa_13_kejadian_miliar = klaim_gempa, klaim_erupsi_3_kejadian_miliar = klaim_erupsi,
  porsi_erupsi_dari_16_kejadian = klaim_erupsi / (klaim_gempa + klaim_erupsi), erupsi_terhadap_gempa = klaim_erupsi / klaim_gempa,
  klaim_kejadian_bertsunami_miliar = kej[kejadian %in% c("Aceh", "Donggala"), sum(klaim_incurred_miliar)],
  porsi_tsunami_dari_klaim_gempa = kej[kejadian %in% c("Aceh", "Donggala"), sum(klaim_incurred_miliar)] / klaim_gempa,
  eksposur_21_tahun_triliun = sum(eksposur_21(0.1451)), eksposur_teramati_2020_2024_triliun = sum(eks),
  porsi_penyebut_dari_hitung_mundur = 1 - sum(eks) / sum(eksposur_21(0.1451)),
  jumlah_tahun_efektif_berbobot_eksposur = sum(eksposur_21(0.1451))^2 / sum(eksposur_21(0.1451)^2),
  pengalaman_21_tahun_permil = 1000 * amati21, pengalaman_5_tahun_permil = 1000 * amati5,
  catatan = "Tahun penutupan (UY) tidak sama dengan tahun kejadian; UY 2024 belum matang. Rasio ini petunjuk kasar kelengkapan, bukan faktor koreksi.")
write_json(lengkap, file.path(KELUAR, "t5_kelengkapan_pembilang.json"), auto_unbox = TRUE, pretty = TRUE, digits = 8)
cat(sprintf("Klaim seluruh provinsi UY 2020-2024: %.2f miliar; kejadian gempa dalam daftar 2020-2024: %.2f miliar; rasio %.2f\n",
            sum(klaim_uy), sum(daftar_2020_2024$klaim_incurred_miliar), lengkap$rasio_seluruh_terhadap_daftar))
cat(sprintf("Erupsi: %.2f miliar = %.2f%% dari 16 kejadian, %.2f%% terhadap klaim gempa; kejadian bertsunami (Aceh, Donggala) %.1f%% klaim gempa\n",
            klaim_erupsi, 100 * lengkap$porsi_erupsi_dari_16_kejadian, 100 * lengkap$erupsi_terhadap_gempa, 100 * lengkap$porsi_tsunami_dari_klaim_gempa))
cat(sprintf("Penyebut 21 tahun %.0f triliun; %.1f%% berasal dari hitung mundur; jumlah tahun efektif %.1f\n",
            lengkap$eksposur_21_tahun_triliun, 100 * lengkap$porsi_penyebut_dari_hitung_mundur, lengkap$jumlah_tahun_efektif_berbobot_eksposur))

# ---------- uji balik: rasio model terhadap klaim teramati ----------
uji <- fread(file.path(DIR_KELUAR, "04_uji_balik.csv"))
uji[, `:=`(rasio_klaim = klaim / klaim_industri, rasio_aulady = aulady / klaim_industri, rasio_pager = pager / klaim_industri)]
fwrite(uji, file.path(KELUAR, "t5_uji_balik_rasio.csv"))
print(uji[, .(kejadian, eta, klaim_industri, mmi = round(mmi_maks_titik, 2), rasio_klaim = round(rasio_klaim, 4), rasio_aulady = round(rasio_aulady, 4), rasio_pager = signif(rasio_pager, 2))])
cat(sprintf("Jumlah lima kejadian, guncangan median: teramati %.1f; klaim %.1f (%.1f%%); aulady %.1f (%.1f%%)\n", uji[eta == 0, sum(klaim_industri)],
            uji[eta == 0, sum(klaim)], 100 * uji[eta == 0, sum(klaim) / sum(klaim_industri)], uji[eta == 0, sum(aulady)], 100 * uji[eta == 0, sum(aulady) / sum(klaim_industri)]))
cat("selesai t5 bobot\n")
