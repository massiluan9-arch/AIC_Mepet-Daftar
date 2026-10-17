# Uji unit rumus pembayaran dengan risiko sendiri (d) dan batas ganti rugi (u).
# Menguji (1) fungsi pembayaran deterministik per risiko, (2) nilai harapan berbasis lev(),
# (3) kesetaraan dengan kode Rev. 1, (4) tabel interpolasi dan inversi bruto_dari_neto di skrip 04.
# Pemakaian: Rscript R/uji_rumus_bayar.R [jalur 00_fungsi.R] [berkas csv Monte Carlo]
# Tanpa argumen: menguji 00_fungsi.R di folder ini dan menulis keluaran/uji_rumus_bayar_mc.csv.
# Keluar dengan kode 1 bila ada satu pemeriksaan gagal.

.arg <- commandArgs(trailingOnly = FALSE)
.sini <- dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)])))
argumen <- commandArgs(trailingOnly = TRUE)
BERKAS <- if (length(argumen) >= 1) argumen[1] else file.path(.sini, "00_fungsi.R")
cat("Berkas yang diuji:", normalizePath(BERKAS), "\n")

# Hanya definisi yang diperlukan yang dievaluasi, supaya jalur dan pembuatan folder di 00_fungsi.R tidak ikut jalan.
perlu <- c("DASAR_BATAS", "NU", "titik_habis", "bayar_per_risiko", "lev_beta")
for (e in parse(BERKAS)) {
  if (is.call(e) && identical(e[[1]], as.name("<-")) && as.character(e[[2]]) %in% perlu) eval(e, globalenv())
}
stopifnot(all(sapply(perlu, exists)))
cat("DASAR_BATAS bawaan berkas:", DASAR_BATAS, "\n\n")

# Fungsi Rev. 1 persis seperti di repositori (tag paper-rev1), sebagai pembanding.
lev_beta_rev1 <- function(mu, nu, risiko_sendiri = 0, batas = 1) {
  mu <- pmin(pmax(mu, 1e-9), 1 - 1e-9)
  a <- mu * nu; b <- (1 - mu) * nu
  lev <- function(x) mu * pbeta(x, a + 1, b) + x * (1 - pbeta(x, a, b))
  lev(batas) - lev(risiko_sendiri)
}

HASIL <- logical(0)
cek <- function(nama, syarat, rinci = "") {
  HASIL <<- c(HASIL, isTRUE(syarat))
  cat(if (isTRUE(syarat)) "LULUS  " else "GAGAL  ", nama, if (nzchar(rinci)) paste0("  [", rinci, "]") else "", "\n", sep = "")
}
sama <- function(a, b, tol = 1e-12) all(abs(a - b) <= tol)
cat("NU dari berkas:", NU, "
")
d <- 0.025; u <- 0.10

cat("== 1. Pembayaran deterministik, dasar 'bayar' (Varian A): bayar = min{(y - d)+, u}; d = 2,5%, u = 10% ==\n")
f <- function(y, rs = d, batas = u) bayar_per_risiko(y, rs, batas, "bayar")
cek("A1 kerusakan di bawah risiko sendiri (y = 1%) -> 0", sama(f(0.01), 0), sprintf("%.6f", f(0.01)))
cek("A2 kerusakan tepat di risiko sendiri (y = 2,5%) -> 0", sama(f(0.025), 0), sprintf("%.6f", f(0.025)))
cek("A3 di antara risiko sendiri dan maksimum (y = 8%) -> 5,5%", sama(f(0.08), 0.055), sprintf("%.6f", f(0.08)))
cek("A4 tepat di titik maksimum tercapai (y = d + u = 12,5%) -> 10%", sama(f(0.125), 0.10), sprintf("%.6f", f(0.125)))
cek("A5 di atas titik maksimum (y = 20% dan 100%) -> 10%", sama(f(c(0.20, 1)), 0.10), paste(sprintf("%.6f", f(c(0.20, 1))), collapse = "; "))
kisi <- seq(0, 1, by = 0.0005)
cek("A6 pembayaran tidak negatif pada kisi 0..1", all(f(kisi) >= 0))
cek("A7 pembayaran tidak melebihi batas u", all(f(kisi) <= u + 1e-15), sprintf("maks %.6f", max(f(kisi))))
cek("A8 monoton tidak turun terhadap kerusakan", all(diff(f(kisi)) >= -1e-15))
cek("A9 batas u = 1 sama dengan tanpa batas: (y - d)+", sama(f(kisi, d, 1), pmax(kisi - d, 0)))
cek("A10 d + u > 1 dipotong di 1 (d = 5%, u = 98%): bayar = (y - d)+ dan paling besar 1 - d",
    sama(f(kisi, 0.05, 0.98), pmax(kisi - 0.05, 0)) && max(f(kisi, 0.05, 0.98)) <= 0.95 + 1e-15,
    sprintf("maks %.4f; titik habis %.4f", max(f(kisi, 0.05, 0.98)), titik_habis(0.05, 0.98, "bayar")))
cek("A11 kemiringan 1 di dalam lapisan (d, d + u)", sama(f(0.10) - f(0.06), 0.04))
cek("A12 d = 5%, u = 20% (paket A): kerusakan 30% dibayar 20%", sama(f(0.30, 0.05, 0.20), 0.20), sprintf("%.6f", f(0.30, 0.05, 0.20)))

cat("\n== 2. Pembayaran deterministik, dasar 'rugi' (Varian B = kode Rev. 1): bayar = min{(y - d)+, u - d} ==\n")
g <- function(y, rs = d, batas = u) bayar_per_risiko(y, rs, batas, "rugi")
cek("B1 kerusakan di bawah risiko sendiri (y = 1%) -> 0", sama(g(0.01), 0))
cek("B2 kerusakan tepat di risiko sendiri (y = 2,5%) -> 0", sama(g(0.025), 0))
cek("B3 di antara risiko sendiri dan maksimum (y = 8%) -> 5,5%", sama(g(0.08), 0.055), sprintf("%.6f", g(0.08)))
cek("B4 tepat di titik maksimum tercapai (y = u = 10%) -> 7,5%", sama(g(0.10), 0.075), sprintf("%.6f", g(0.10)))
cek("B5 di atas titik maksimum (y = 12,5%; 20%; 100%) -> 7,5%", sama(g(c(0.125, 0.20, 1)), 0.075), paste(sprintf("%.6f", g(c(0.125, 0.20, 1))), collapse = "; "))
cek("B6 pembayaran tidak negatif", all(g(kisi) >= 0))
cek("B7 pembayaran tidak melebihi u - d", all(g(kisi) <= u - d + 1e-15), sprintf("maks %.6f", max(g(kisi))))
cek("B8 monoton tidak turun terhadap kerusakan", all(diff(g(kisi)) >= -1e-15))
cek("B9 batas u = 1 sama dengan tanpa batas: (y - d)+", sama(g(kisi, d, 1), pmax(kisi - d, 0)))
cek("B10 batas di bawah risiko sendiri tidak menghasilkan pembayaran negatif (d = 10%, u = 5%)", all(g(kisi, 0.10, 0.05) == 0))
cek("B11 selisih A - B pada kerusakan 20% = d = 2,5% nilai pertanggungan", sama(f(0.20) - g(0.20), 0.025), sprintf("A %.4f; B %.4f", f(0.20), g(0.20)))

cat("\n== 3. Nilai harapan berbasis lev(): identitas dan batas ==\n")
mu_uji <- c(1e-6, 1e-4, 0.001, 0.01, 0.05, 0.10, 0.30, 0.60, 0.90, 0.999)
kontrak <- list(c(0.025, 1), c(0.05, 1), c(0.10, 1), c(0.025, 0.10), c(0.025, 0.15), c(0.025, 0.20), c(0.025, 0.25),
                c(0.025, 0.30), c(0.025, 0.40), c(0.025, 0.50), c(0.05, 0.20))
selisih <- max(sapply(kontrak, function(k) max(abs(lev_beta(mu_uji, NU, k[1], k[2], "rugi") - lev_beta_rev1(mu_uji, NU, k[1], k[2])))))
cek("C1 dasar 'rugi' identik dengan lev_beta Rev. 1 pada 11 syarat polis skrip 04", selisih == 0, sprintf("selisih maks %.3g", selisih))
selisih <- max(sapply(list(c(0.025, 1), c(0.05, 1), c(0.10, 1)), function(k) max(abs(lev_beta(mu_uji, NU, k[1], 1, "bayar") - lev_beta_rev1(mu_uji, NU, k[1], 1)))))
cek("C2 tanpa batas (u = 1): 'bayar' identik dengan Rev. 1 (S0, S1, S2 dan inversi kurva klaim tidak berubah)", selisih == 0, sprintf("selisih maks %.3g", selisih))
selisih <- max(sapply(kontrak[4:11], function(k) max(abs(lev_beta(mu_uji, NU, k[1], k[2], "bayar") - lev_beta_rev1(mu_uji, NU, k[1], k[1] + k[2])))))
cek("C3 identitas: E_A(d, u) = lev(d + u) - lev(d) = E_Rev1(d, batas = d + u)", selisih == 0, sprintf("selisih maks %.3g", selisih))
ok <- all(sapply(kontrak, function(k) { e <- lev_beta(mu_uji, NU, k[1], k[2], "bayar"); all(e >= -1e-15 & e <= min(k[2], 1 - k[1]) + 1e-15 & e <= mu_uji + 1e-15) }))
cek("C4 'bayar': 0 <= E <= min(u, 1 - d) dan E <= mu", ok)
ok <- all(sapply(kontrak, function(k) { e <- lev_beta(mu_uji, NU, k[1], k[2], "rugi"); all(e >= -1e-15 & e <= min(k[2], 1) - k[1] + 1e-15 & e <= mu_uji + 1e-15) }))
cek("C5 'rugi': 0 <= E <= u - d dan E <= mu", ok)
mu_rapat <- seq(0.0005, 0.9995, by = 0.0005)
ok <- all(sapply(kontrak, function(k) all(diff(lev_beta(mu_rapat, NU, k[1], k[2], "bayar")) >= -1e-12) && all(diff(lev_beta(mu_rapat, NU, k[1], k[2], "rugi")) >= -1e-12)))
cek("C6 E monoton naik terhadap rata-rata kerusakan mu (kedua dasar)", ok)
u_kisi <- c(0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1)
ok <- all(sapply(mu_uji, function(m) all(diff(lev_beta(m, NU, d, u_kisi, "bayar")) >= -1e-15) && all(diff(lev_beta(m, NU, d, u_kisi, "rugi")) >= -1e-15)))
cek("C7 E monoton naik terhadap batas u (kedua dasar)", ok)
ok <- all(sapply(kontrak, function(k) all(lev_beta(mu_uji, NU, k[1], k[2], "bayar") >= lev_beta(mu_uji, NU, k[1], k[2], "rugi") - 1e-15)))
cek("C8 E_A >= E_B untuk d dan u yang sama", ok)
# lev(x) = E[min(Y, x)] terhadap integrasi numerik int_0^x (1 - F(y)) dy
lev_num <- function(mu, x) integrate(function(y) 1 - pbeta(y, mu * NU, (1 - mu) * NU), 0, x, rel.tol = 1e-10, subdivisions = 2000L)$value
maks <- 0
for (m in c(0.05, 0.10, 0.30, 0.60, 0.90)) for (x in c(0.025, 0.10, 0.125, 0.20, 0.50, 1)) {
  maks <- max(maks, abs(lev_beta(m, NU, 0, x, "rugi") - lev_num(m, x)))
}
cek("C9 lev(x) = E[min(Y, x)] cocok dengan integral numerik fungsi survival", maks < 1e-7, sprintf("selisih maks %.3g", maks))

cat("\n== 4. Nilai harapan analitik lawan rata-rata Monte Carlo pembayaran deterministik, Beta(mu nu, (1 - mu) nu), nu dari berkas ==\n")
set.seed(20261013)
N_MC <- 2e6
mu_mc <- c(0.001, 0.01, 0.05, 0.10, 0.30, 0.60, 0.90)
kontrak_mc <- list(c(0.025, 1), c(0.025, 0.10), c(0.025, 0.20), c(0.05, 0.20), c(0.025, 0.50), c(0.10, 1), c(0.05, 0.98))
tabel <- NULL
for (m in mu_mc) {
  y <- rbeta(N_MC, m * NU, (1 - m) * NU)
  for (k in kontrak_mc) for (dasar in c("bayar", "rugi")) {
    b <- bayar_per_risiko(y, k[1], k[2], dasar)
    an <- lev_beta(m, NU, k[1], k[2], dasar)
    gb <- sd(b) / sqrt(N_MC)
    tabel <- rbind(tabel, data.frame(mu = m, d = k[1], u = k[2], dasar = dasar, analitik = an, monte_carlo = mean(b), galat_baku = gb,
                                     z = if (gb > 0) (mean(b) - an) / gb else 0, maks_bayar = max(b)))
  }
}
print(format(tabel, digits = 6), row.names = FALSE)
cek(sprintf("D1 semua %d pasangan analitik-Monte Carlo berselisih kurang dari 4 galat baku", nrow(tabel)), all(abs(tabel$z) < 4),
    sprintf("|z| maks %.2f; selisih mutlak maks %.2e", max(abs(tabel$z)), max(abs(tabel$analitik - tabel$monte_carlo))))
cek("D2 selisih relatif analitik-Monte Carlo di bawah 1% untuk mu >= 1%", with(tabel[tabel$mu >= 0.01, ], all(abs(monte_carlo / analitik - 1) < 0.01)),
    sprintf("maks %.3f%%", 100 * with(tabel[tabel$mu >= 0.01, ], max(abs(monte_carlo / analitik - 1)))))
cap <- with(tabel, ifelse(dasar == "bayar", pmin(u, 1 - d), pmin(u, 1) - d))
cek("D3 pembayaran tersimulasi terbesar tidak melebihi pembayaran maksimum kontrak", all(tabel$maks_bayar <= cap + 1e-12))
KELUAR_MC <- if (length(argumen) >= 2) argumen[2] else file.path(.sini, "..", "keluaran", "uji_rumus_bayar_mc.csv")
write.csv(tabel, KELUAR_MC, row.names = FALSE)

cat("\n== 5. Tabel interpolasi dan inversi bruto_dari_neto seperti di 04_simulasi_kerugian.R ==\n")
RS <- 0.025
mu_grid <- c(0, 10^seq(-6, log10(0.999), length.out = 400))
neto_grid <- c(0, lev_beta(mu_grid[-1], NU, RS, 1))
bruto_dari_neto <- approxfun(neto_grid, mu_grid, rule = 2)
cek("E1 neto_grid naik tegas, jadi inversi tunggal", all(diff(neto_grid) > 0), sprintf("selisih terkecil %.3g", min(diff(neto_grid))))
neto_uji <- c(1e-6, 1e-5, 1e-4, 6e-4, 0.0021, 0.0057, 0.0121, 0.0488, 0.2, 0.5)
kembali <- lev_beta(bruto_dari_neto(neto_uji), NU, RS, 1)
cek("E2 bolak-balik neto -> bruto -> neto, galat relatif di bawah 0,5%", all(abs(kembali / neto_uji - 1) < 5e-3), sprintf("maks %.3g", max(abs(kembali / neto_uji - 1))))
cek("E3 bruto hasil inversi selalu di atas neto (risiko sendiri memotong klaim)", all(bruto_dari_neto(neto_uji) > neto_uji))
buat_syarat <- function(rs, batas, dasar) approxfun(mu_grid, c(0, lev_beta(mu_grid[-1], NU, rs, batas, dasar)), rule = 2)
mu_acak <- sort(c(runif(2000, 0, 0.999), 10^runif(2000, -6, 0)))
mu_acak <- mu_acak[mu_acak <= 0.999]
gal <- sapply(c("bayar", "rugi"), function(dasar) max(sapply(list(c(0.025, 1), c(0.025, 0.10), c(0.025, 0.20), c(0.05, 0.20)), function(k) {
  max(abs(buat_syarat(k[1], k[2], dasar)(mu_acak) - lev_beta(mu_acak, NU, k[1], k[2], dasar)))
})))
cek("E4 galat interpolasi tabel SYARAT (400 titik) di bawah 1e-4 nilai pertanggungan", all(gal < 1e-4), sprintf("bayar %.3g; rugi %.3g", gal[1], gal[2]))
batas_dipakai <- c(0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
cek("E5 pada strategi yang ada d + u tidak melebihi 1 (terbesar: d 2,5% + u 50%)", max(c(0.025 + batas_dipakai, 0.05 + 0.20)) <= 1,
    sprintf("d + u terbesar %.3f", max(c(0.025 + batas_dipakai, 0.05 + 0.20))))

cat("\n== 6. Besarnya beda Varian A dan B pada rata-rata kerusakan yang relevan (d = 2,5%) ==\n")
banding <- do.call(rbind, lapply(c(0.10, 0.20), function(uu) data.frame(
  u = uu, mu = c(0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40),
  E_A = lev_beta(c(0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40), NU, d, uu, "bayar"),
  E_B = lev_beta(c(0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40), NU, d, uu, "rugi"),
  E_tanpa_batas = lev_beta(c(0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40), NU, d, 1, "bayar"))))
banding$A_per_B <- banding$E_A / banding$E_B
print(format(banding, digits = 5), row.names = FALSE)

cat(sprintf("\n%d dari %d pemeriksaan lulus\n", sum(HASIL), length(HASIL)))
quit(save = "no", status = if (all(HASIL)) 0 else 1)
