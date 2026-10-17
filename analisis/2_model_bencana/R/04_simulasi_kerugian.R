# 04. Simulasi kerugian bencana berbasis kejadian.
# Rantai: frekuensi (binomial negatif) -> magnitudo (eksponensial terpotong) -> lokasi (episenter historis
# sekelas) -> intensitas di 37 titik portofolio (Allen dkk., 2012) -> rasio kerugian (tiga kurva) ->
# syarat polis dan strategi mitigasi -> kerugian tahunan dan kerugian kejadian terbesar.
# Satuan kerugian: fraksi dari nilai pertanggungan gempa awal (sebelum mitigasi).
# Keluaran: keluaran/04_*.csv, keluaran/04_ylt.csv.gz
# Jalankan: Rscript R/04_simulasi_kerugian.R [jumlah_tahun] [skenario]
#   argumen kedua "skenario" berhenti setelah uji balik dan skenario (tanpa simulasi)

.arg <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)]))), "00_fungsi.R"))

argumen <- commandArgs(trailingOnly = TRUE)
N_TAHUN <- if (length(argumen)) as.integer(argumen[1]) else 100000L
POTONG <- 5000L                       # tahun per potongan agar memori terjaga
BENIH <- 20261012L
GESER_EPISENTER <- 0.3                # derajat; simpangan baku pergeseran episenter historis
# NU (presisi Beta) didefinisikan di 00_fungsi.R
RS <- 0.025                           # risiko sendiri polis standar

p1 <- fromJSON(file.path(DIR_KELUAR, "01_parameter.json"))
p3 <- fromJSON(file.path(DIR_KELUAR, "03_parameter.json"))
epi <- fread(file.path(DIR_KELUAR, "01_episenter.csv"))
titik <- fread(file.path(DIR_DATA, "portofolio_titik.csv"))
S <- nrow(titik)
w0 <- titik$bobot
beta <- p1$nilai_b * log(10)
M_MIN <- p1$m_min; M_MAKS <- p1$m_maks

# ---------- kurva kerentanan: rata-rata rasio kerusakan bruto per risiko ----------
kurva_klaim_neto <- function(mmi) ifelse(mmi < p3$mmi_min, 0, plogis(p3$a + p3$b * mmi))
# Kurva klaim MAIPARK sudah setelah risiko sendiri 2,5%. Rata-rata bruto dicari sehingga
# E[(X - 2,5%)+] sama dengan kurva klaim.
mu_grid <- c(0, 10^seq(-6, log10(0.999), length.out = 400))
neto_grid <- c(0, lev_beta(mu_grid[-1], NU, RS, 1))
bruto_dari_neto <- approxfun(neto_grid, mu_grid, rule = 2)
BRUTO <- list(
  klaim = function(mmi) bruto_dari_neto(kurva_klaim_neto(mmi)),
  aulady = function(mmi) kurva_aulady(mmi),
  pager = function(mmi) kurva_pager(mmi)
)
# Tabel cepat: rasio setelah syarat polis sebagai fungsi rata-rata bruto
buat_syarat <- function(rs, batas) {
  y <- c(0, lev_beta(mu_grid[-1], NU, rs, batas))
  approxfun(mu_grid, y, rule = 2)
}
SYARAT <- list(rs2_5 = buat_syarat(0.025, 1), rs5 = buat_syarat(0.05, 1), rs10 = buat_syarat(0.10, 1),
               batas20 = buat_syarat(0.025, 0.20), batas10 = buat_syarat(0.025, 0.10),
               rs5_batas20 = buat_syarat(0.05, 0.20),
               batas50 = buat_syarat(0.025, 0.50), batas40 = buat_syarat(0.025, 0.40), batas30 = buat_syarat(0.025, 0.30),
               batas25 = buat_syarat(0.025, 0.25), batas15 = buat_syarat(0.025, 0.15))
# Batas ganti rugi hanya untuk risiko besar (nilai pertanggungan di atas Rp50 miliar). Porsinya dari profil
# risiko MAIPARK; baris terakhir tabel sumber adalah baris jumlah dan dibuang.
profil <- fread(file.path(DIR_DATA, "maipark_profil_risiko.csv"))[no <= 19]
PORSI_BESAR <- profil[ts_dari_juta > 50000, sum(eksposur_juta)] / profil[, sum(eksposur_juta)]
PORSI_JUMLAH_BESAR <- profil[ts_dari_juta > 50000, sum(jumlah_risiko)] / profil[, sum(jumlah_risiko)]
SYARAT$batas20_besar <- function(mu) PORSI_BESAR * SYARAT$batas20(mu) + (1 - PORSI_BESAR) * SYARAT$rs2_5(mu)

# ---------- strategi: (syarat polis, bobot eksposur yang ditahan) ----------
zona3 <- titik$provinsi %in% c("JAKARTA", "JAWA BARAT", "BANTEN")
# Zona inti: provinsi yang menyumbang lebih dari 3% kerugian tahun ekor pada kurva Aulady & Fujimi
# (04_kontribusi_provinsi.csv, putaran pertama tanpa strategi bersasaran).
ZONA_INTI <- c("PAPUA", "JAWA BARAT", "JAKARTA", "SUMATERA UTARA", "BANTEN")
zona_inti <- titik$provinsi %in% ZONA_INTI
bobot_batas <- function(batas) {            # batas akumulasi per provinsi; kelebihannya dilepas
  prov <- tapply(w0, titik$provinsi, sum)
  faktor <- setNames(pmin(1, as.numeric(batas / prov)), names(prov))
  w0 * faktor[titik$provinsi]
}
STRATEGI <- list(
  S0_dasar = list(syarat = "rs2_5", w = w0, ket = "Polis standar: risiko sendiri 2,5%"),
  S1_rs5 = list(syarat = "rs5", w = w0, ket = "Risiko sendiri 5%"),
  S2_rs10 = list(syarat = "rs10", w = w0, ket = "Risiko sendiri 10%"),
  S3_batas20 = list(syarat = "batas20", w = w0, ket = "Batas ganti rugi gempa 20% nilai pertanggungan per risiko"),
  S4_batas10 = list(syarat = "batas10", w = w0, ket = "Batas ganti rugi gempa 10% nilai pertanggungan per risiko"),
  S5_akumulasi10 = list(syarat = "rs2_5", w = bobot_batas(0.10), ket = "Batas akumulasi 10% per provinsi"),
  S6_koas50 = list(syarat = "rs2_5", w = w0 * ifelse(zona3, 0.5, 1), ket = "Koasuransi 50% di Jakarta, Jawa Barat, Banten"),
  S7_paketA = list(syarat = "rs5_batas20", w = bobot_batas(0.10), ket = "Paket A: risiko sendiri 5%, batas 20%, akumulasi 10%"),
  S8_paketB = list(syarat = "rs5_batas20", w = bobot_batas(0.10) * ifelse(zona3, 0.5, 1), ket = "Paket B: paket A dan koasuransi 50%"),
  S9_batas50 = list(syarat = "batas50", w = w0, ket = "Batas ganti rugi gempa 50%"),
  S10_batas40 = list(syarat = "batas40", w = w0, ket = "Batas ganti rugi gempa 40%"),
  S11_batas30 = list(syarat = "batas30", w = w0, ket = "Batas ganti rugi gempa 30%"),
  S12_batas25 = list(syarat = "batas25", w = w0, ket = "Batas ganti rugi gempa 25%"),
  S13_batas15 = list(syarat = "batas15", w = w0, ket = "Batas ganti rugi gempa 15%"),
  S14_batas20_akum10 = list(syarat = "batas20", w = bobot_batas(0.10), ket = "Batas 20% dan akumulasi 10% per provinsi"),
  S15_batas20_akum5 = list(syarat = "batas20", w = bobot_batas(0.05), ket = "Batas 20% dan akumulasi 5% per provinsi"),
  S16_batas10_akum5 = list(syarat = "batas10", w = bobot_batas(0.05), ket = "Batas 10% dan akumulasi 5% per provinsi"),
  S17_batas20_besar = list(syarat = "batas20_besar", w = w0, ket = "Batas 20% hanya untuk risiko di atas Rp50 miliar"),
  S18_batas20_besar_akum10 = list(syarat = "batas20_besar", w = bobot_batas(0.10), ket = "Batas 20% risiko besar dan akumulasi 10% per provinsi"),
  S19_akum5 = list(syarat = "rs2_5", w = bobot_batas(0.05), ket = "Batas akumulasi 5% per provinsi"),
  # Strategi bersasaran: syarat khusus hanya berlaku pada porsi `a` eksposur tiap titik; sisanya memakai `syarat`.
  S20_zona_batas20 = list(syarat = "rs2_5", khusus = "batas20", a = as.numeric(zona_inti), w = w0,
                          ket = "Batas 20% di zona inti"),
  S21_zona_batas10 = list(syarat = "rs2_5", khusus = "batas10", a = as.numeric(zona_inti), w = w0,
                          ket = "Batas 10% di zona inti"),
  S22_zona_besar_batas20 = list(syarat = "rs2_5", khusus = "batas20", a = PORSI_BESAR * zona_inti, w = w0,
                                ket = "Batas 20% untuk risiko besar di zona inti"),
  S23_zona_batas20_akum10 = list(syarat = "rs2_5", khusus = "batas20", a = as.numeric(zona_inti), w = bobot_batas(0.10),
                                 ket = "Batas 20% di zona inti dan akumulasi 10% per provinsi"),
  S24_zona_batas10_luar_batas30 = list(syarat = "batas30", khusus = "batas10", a = as.numeric(zona_inti), w = w0,
                                       ket = "Batas berjenjang: 10% di zona inti, 30% di luar"),
  S25_zona_batas15 = list(syarat = "rs2_5", khusus = "batas15", a = as.numeric(zona_inti), w = w0,
                          ket = "Batas 15% di zona inti")
)
tarif <- titik$tarif_gempa_per_mil
premi_awal <- sum(w0 * tarif)
ringkas_strategi <- rbindlist(lapply(names(STRATEGI), function(s) {
  x <- STRATEGI[[s]]
  a <- if (is.null(x$a)) rep(0, S) else x$a
  data.table(strategi = s, keterangan = x$ket, syarat = x$syarat,
             syarat_khusus = if (is.null(x$khusus)) "" else x$khusus,
             eksposur_ditahan = sum(x$w), premi_gempa_ditahan = sum(x$w * tarif) / premi_awal,
             porsi_eksposur_khusus = sum(x$w * a) / sum(x$w), porsi_premi_khusus = sum(x$w * tarif * a) / sum(x$w * tarif))
}))
fwrite(ringkas_strategi, file.path(DIR_KELUAR, "04_strategi.csv"))

# ---------- intensitas di titik portofolio ----------
simpangan <- function(r) 0.82 + 0.37 / (1 + (r / 22.9)^2)     # Allen dkk. (2012)
intensitas <- function(m, lat, lon, dalam, arah, eta, eps = NULL) {
  n <- length(m)
  L <- panjang_ruptur_km(m)
  out <- matrix(0, n, S)
  for (s in seq_len(S)) {
    repi <- jarak_km(lat, lon, titik$lintang[s], titik$bujur[s])
    rr <- sqrt(pmax(repi - arah * L / 2, 0)^2 + dalam^2)
    e <- if (is.null(eps)) 0 else eps[, s]
    out[, s] <- pmin(mmi_allen_rrup(m, rr) + simpangan(rr) * (sqrt(0.5) * eta + sqrt(0.5) * e), 10)
  }
  out
}
kerugian_kejadian <- function(mmi, kurva, syarat, w) {
  mu <- BRUTO[[kurva]](mmi)
  d <- SYARAT[[syarat]](mu)
  dim(d) <- dim(mmi)
  as.numeric(d %*% w)
}
# Rasio kerugian per titik untuk satu strategi, termasuk syarat khusus pada sebagian eksposur
rasio_strategi <- function(mu, st, ukuran) {
  x <- STRATEGI[[st]]
  d <- SYARAT[[x$syarat]](mu); dim(d) <- ukuran
  if (!is.null(x$khusus)) {
    d2 <- SYARAT[[x$khusus]](mu); dim(d2) <- ukuran
    d <- sweep(d, 2, 1 - x$a, `*`) + sweep(d2, 2, x$a, `*`)
  }
  d
}

# ---------- uji balik terhadap klaim industri (MAIPARK) ----------
eks <- fread(file.path(DIR_DATA, "maipark_eksposur_provinsi.csv"))
kejadian <- data.table(
  nama = c("Lombok 2018", "Palu-Donggala 2018", "Majene 2021", "Cianjur 2022", "Bawean 2024"),
  m = c(6.9, 7.5, 6.2, 5.6, 6.4), lat = c(-8.2581, -0.2559, -2.9717, -6.836, -5.8754),
  lon = c(116.4375, 119.8462, 118.8899, 106.9968, 112.3646), dalam = c(34, 20, 18, 10, 9.5),
  uy = c("uy_2020", "uy_2020", "uy_2021", "uy_2022", "uy_2024"),
  klaim_miliar = c(364.40, 1058.62, 202.65, 26.44, 16.71))
uji <- rbindlist(lapply(seq_len(nrow(kejadian)), function(i) {
  k <- kejadian[i]
  eks_titik <- eks[[k$uy]][match(titik$provinsi, eks$provinsi)] * titik$porsi_dalam_provinsi * 1000   # miliar
  rbindlist(lapply(c(0, 1), function(eta) {
    mmi <- intensitas(k$m, k$lat, k$lon, k$dalam, 0.5, eta)
    data.table(kejadian = k$nama, eta = eta, klaim_industri = k$klaim_miliar, mmi_maks_titik = max(mmi),
               titik_terdekat = titik$titik[which.max(mmi)],
               klaim = kerugian_kejadian(mmi, "klaim", "rs2_5", eks_titik),
               aulady = kerugian_kejadian(mmi, "aulady", "rs2_5", eks_titik),
               pager = kerugian_kejadian(mmi, "pager", "rs2_5", eks_titik))
  }))
}))
fwrite(uji, file.path(DIR_KELUAR, "04_uji_balik.csv"))
cat("Uji balik (miliar rupiah; eta = residu antar-gempa dalam simpangan baku):\n"); print(uji)

# ---------- skenario deterministik ----------
sken <- data.table(
  nama = c("Megathrust Jawa bagian barat M 8,7", "Sesar Lembang M 6,8", "Sesar Surabaya M 6,5", "Megathrust Mentawai M 8,9", "Gempa dangkal dekat Timika M 7,5"),
  m = c(8.7, 6.8, 6.5, 8.9, 7.5), lat = c(-7.5, -6.83, -7.30, -1.5, -4.2), lon = c(106.0, 107.62, 112.70, 99.8, 136.6),
  dalam = c(30, 10, 10, 25, 20),
  dasar = c("Potensi magnitudo megathrust Selat Sunda menurut BMKG (2024), mengacu Peta Sumber dan Bahaya Gempa Indonesia 2017", "Sesar aktif di utara Bandung (PuSGeN 2017)",
            "Sesar Surabaya dan Waru (PuSGeN 2017)", "Potensi magnitudo megathrust Mentawai-Siberut menurut BMKG (2024)", "Skenario bagi konsentrasi eksposur Papua"))
hasil_sken <- rbindlist(lapply(seq_len(nrow(sken)), function(i) {
  k <- sken[i]
  rbindlist(lapply(c(0, 1), function(eta) {
    mmi <- intensitas(k$m, k$lat, k$lon, k$dalam, 0.5, eta)
    data.table(skenario = k$nama, dasar = k$dasar, eta = eta, mmi_maks_titik = max(mmi), titik = titik$titik[which.max(mmi)],
               klaim = kerugian_kejadian(mmi, "klaim", "rs2_5", w0), aulady = kerugian_kejadian(mmi, "aulady", "rs2_5", w0),
               pager = kerugian_kejadian(mmi, "pager", "rs2_5", w0),
               klaim_paketA = kerugian_kejadian(mmi, "klaim", "rs5_batas20", STRATEGI$S7_paketA$w),
               klaim_paketB = kerugian_kejadian(mmi, "klaim", "rs5_batas20", STRATEGI$S8_paketB$w))
  }))
}))
fwrite(hasil_sken, file.path(DIR_KELUAR, "04_skenario.csv"))
# Skenario untuk semua kurva dan semua strategi (bentuk panjang), dipakai uji tekanan neraca.
sken_strategi <- rbindlist(lapply(seq_len(nrow(sken)), function(i) {
  k <- sken[i]
  rbindlist(lapply(c(0, 1), function(eta) {
    mmi <- intensitas(k$m, k$lat, k$lon, k$dalam, 0.5, eta)
    rbindlist(lapply(names(STRATEGI), function(s) rbindlist(lapply(names(BRUTO), function(kv) data.table(
      skenario = k$nama, eta = eta, strategi = s, kurva = kv,
      kerugian = as.numeric(rasio_strategi(BRUTO[[kv]](mmi), s, dim(mmi)) %*% STRATEGI[[s]]$w))))))
  }))
}))
fwrite(sken_strategi, file.path(DIR_KELUAR, "04_skenario_strategi.csv"))
if (length(argumen) >= 2 && argumen[2] == "skenario") { cat("selesai 04 (hanya uji balik dan skenario)
"); quit(save = "no") }
cat("Skenario (fraksi nilai pertanggungan):\n"); print(hasil_sken[, .(skenario, eta, mmi_maks_titik = round(mmi_maks_titik, 2), titik, klaim = round(100 * klaim, 3), aulady = round(100 * aulady, 3), pager = round(100 * pager, 3))])

# ---------- simulasi ----------
set.seed(BENIH)
kelas_lokasi <- list(besar = which(epi$mag >= 7.0), sedang = which(epi$mag >= 6.5), semua = seq_len(nrow(epi)))
KURVA <- names(BRUTO)
kol <- as.vector(outer(KURVA, names(STRATEGI), paste, sep = "."))
ylt_jumlah <- matrix(0, N_TAHUN, length(kol), dimnames = list(NULL, kol))
ylt_maks <- ylt_jumlah
KURVA_TITIK <- c("aulady", "klaim")           # strategi dasar: kerugian tahunan per titik
titik_tahunan <- lapply(setNames(KURVA_TITIK, KURVA_TITIK), function(k) matrix(0, N_TAHUN, S))
n_kejadian_total <- 0; n_merugikan <- 0
mulai <- Sys.time()
for (p in seq_len(ceiling(N_TAHUN / POTONG))) {
  tahun_potong <- ((p - 1) * POTONG + 1):min(p * POTONG, N_TAHUN)
  n <- rnbinom(length(tahun_potong), size = p1$frekuensi$ukuran, mu = p1$frekuensi$rata)
  tot <- sum(n)
  thn <- rep(tahun_potong, n)
  m <- M_MIN - log(1 - runif(tot) * (1 - exp(-beta * (M_MAKS - M_MIN)))) / beta
  # Lokasi dari episenter historis pada kelas magnitudo yang sama atau lebih besar
  idx <- integer(tot)
  b <- m >= 7.5; s <- m >= 6.5 & !b; r <- !b & !s
  idx[b] <- sample(kelas_lokasi$besar, sum(b), TRUE)
  idx[s] <- sample(kelas_lokasi$sedang, sum(s), TRUE)
  idx[r] <- sample(kelas_lokasi$semua, sum(r), TRUE)
  lat <- epi$lintang[idx] + rnorm(tot, 0, GESER_EPISENTER)
  lon <- epi$bujur[idx] + rnorm(tot, 0, GESER_EPISENTER)
  eta <- pmax(pmin(rnorm(tot), 2), -2)
  eps <- matrix(pmax(pmin(rnorm(tot * S), 2), -2), tot, S)
  mmi <- intensitas(m, lat, lon, epi$dalam[idx], runif(tot), eta, eps)
  kena <- which(mmi %*% rep(1, S) > 0 & apply(mmi, 1, max) >= 5)
  n_kejadian_total <- n_kejadian_total + tot; n_merugikan <- n_merugikan + length(kena)
  if (!length(kena)) next
  mmi <- mmi[kena, , drop = FALSE]; thn_k <- thn[kena]
  for (kv in KURVA) {
    mu <- BRUTO[[kv]](mmi); dim(mu) <- dim(mmi)
    for (st in names(STRATEGI)) {
      d <- rasio_strategi(mu, st, dim(mmi))
      rugi <- as.numeric(d %*% STRATEGI[[st]]$w)
      dt <- data.table(t = thn_k, x = rugi)[, .(j = sum(x), mx = max(x)), by = t]
      ylt_jumlah[dt$t, paste(kv, st, sep = ".")] <- dt$j
      ylt_maks[dt$t, paste(kv, st, sep = ".")] <- dt$mx
      if (kv %in% KURVA_TITIK && st == "S0_dasar") {
        per_titik <- rowsum(sweep(d, 2, w0, `*`), thn_k)
        titik_tahunan[[kv]][as.integer(rownames(per_titik)), ] <- per_titik
      }
    }
  }
  cat(sprintf("  potongan %d/%d selesai (%.0f detik)\n", p, ceiling(N_TAHUN / POTONG), as.numeric(difftime(Sys.time(), mulai, units = "secs"))))
}
cat(sprintf("Kejadian tersimulasi: %d (%.1f per tahun); yang menimbulkan intensitas >= V di salah satu titik: %d (%.2f per tahun)\n",
            n_kejadian_total, n_kejadian_total / N_TAHUN, n_merugikan, n_merugikan / N_TAHUN))

# ---------- ukuran risiko ----------
ukur <- rbindlist(lapply(kol, function(k) {
  bagian <- strsplit(k, ".", fixed = TRUE)[[1]]
  u <- ukuran_risiko(ylt_jumlah[, k])
  data.table(kurva = bagian[1], strategi = bagian[2], t(u),
             galat_baku_var_99_5 = galat_baku_kelompok(ylt_jumlah[, k], function(z) quantile(z, 0.995)),
             maks_kejadian_var_99_5 = quantile(ylt_maks[, k], 0.995, names = FALSE),
             maks_kejadian_var_99 = quantile(ylt_maks[, k], 0.99, names = FALSE))
}))
ukur <- merge(ukur, ringkas_strategi[, .(strategi, keterangan, eksposur_ditahan, premi_gempa_ditahan)], by = "strategi", sort = FALSE)
fwrite(ukur, file.path(DIR_KELUAR, "04_ukuran_risiko.csv"))
cat("Ukuran risiko, persen nilai pertanggungan awal:\n")
print(ukur[, .(kurva, strategi, aal_permil = round(1000 * aal, 4), var_99 = round(100 * var_99, 3), var_99_5 = round(100 * var_99_5, 3),
               tvar_99_5 = round(100 * tvar_99_5, 3), gb = round(100 * galat_baku_var_99_5, 3))])

# Kontribusi provinsi terhadap rata-rata dan terhadap tahun-tahun ekor (strategi dasar)
kontribusi <- rbindlist(lapply(KURVA_TITIK, function(kv) {
  tot <- ylt_jumlah[, paste0(kv, ".S0_dasar")]
  ekor <- tot >= quantile(tot, 0.995)
  k <- data.table(kurva = kv, provinsi = titik$provinsi, bobot = w0, aal = colMeans(titik_tahunan[[kv]]),
                  ekor = colMeans(titik_tahunan[[kv]][ekor, , drop = FALSE]))
  k <- k[, .(bobot = sum(bobot), aal = sum(aal), ekor = sum(ekor)), by = .(kurva, provinsi)]
  k[, `:=`(porsi_aal = aal / sum(aal), porsi_ekor = ekor / sum(ekor), aal_per_mil_provinsi = 1000 * aal / bobot)]
  setorder(k, -porsi_ekor)
}))
fwrite(kontribusi, file.path(DIR_KELUAR, "04_kontribusi_provinsi.csv"))
print(kontribusi[, head(.SD, 8), by = kurva][, .(kurva, provinsi, bobot = round(100 * bobot, 1), porsi_aal = round(100 * porsi_aal, 1),
                                                 porsi_ekor = round(100 * porsi_ekor, 1), aal_per_mil_provinsi = round(aal_per_mil_provinsi, 4))])

# ---------- tabel kerugian tahunan untuk mesin neraca ----------
ylt <- data.table(tahun = seq_len(N_TAHUN))
for (k in kol) { ylt[[paste0("jumlah.", k)]] <- signif(ylt_jumlah[, k], 6); ylt[[paste0("maks.", k)]] <- signif(ylt_maks[, k], 6) }
fwrite(ylt, file.path(DIR_KELUAR, "04_ylt.csv.gz"))
write_json(list(jumlah_tahun = N_TAHUN, benih = BENIH, m_min = M_MIN, m_maks = M_MAKS, geser_episenter_derajat = GESER_EPISENTER,
                presisi_beta = NU, dasar_batas = DASAR_BATAS,
                kejadian_per_tahun = n_kejadian_total / N_TAHUN, kejadian_merugikan_per_tahun = n_merugikan / N_TAHUN,
                satuan = "fraksi nilai pertanggungan gempa awal", kurva = KURVA, strategi = names(STRATEGI),
                porsi_eksposur_risiko_besar = PORSI_BESAR, porsi_jumlah_risiko_besar = PORSI_JUMLAH_BESAR,
                zona_inti = ZONA_INTI, porsi_eksposur_zona_inti = sum(w0[zona_inti])),
           file.path(DIR_KELUAR, "04_meta.json"), auto_unbox = TRUE, pretty = TRUE)
cat("selesai 04\n")
