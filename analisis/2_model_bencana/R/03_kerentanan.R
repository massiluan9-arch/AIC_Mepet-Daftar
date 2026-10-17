# 03. Kurva kerentanan portofolio tertanggung.
# Kurva utama dipaskan pada pengalaman klaim industri (MAIPARK, Tabel 4.1): rasio klaim terhadap eksposur
# terdampak menurut intensitas maksimum. Klaim sudah setelah risiko sendiri polis standar.
# Pembanding: Aulady & Fujimi (2019) untuk hunian (batas atas) dan PAGER Indonesia (batas bawah).
# Rev. 2: ketiga kurva dipakai dalam campuran berbobot (bobot dari skrip 05); tabel dan gambar memakai dasar
# yang sama, yaitu setelah risiko sendiri 2,5%.
# Keluaran: keluaran/03_*.csv, keluaran/03_parameter.json, gambar/e4_kurva_kerentanan.png

.arg <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)]))), "00_fungsi.R"))

kej <- fread(file.path(DIR_DATA, "maipark_kejadian_klaim.csv"))
g <- kej[jenis == "gempa"]
g[, mmi := as.numeric(as.roman(mmi_maks))]
# Kejadian dengan tsunami atau likuefaksi besar ditandai; keduanya dijamin polis yang sama.
g[, tsunami := kejadian %in% c("Aceh", "Donggala")]
print(g[, .(kejadian, tanggal, magnitudo, mmi, rasio, tsunami)])

# Logit pecahan (quasi-binomial): rasio = 1 / (1 + exp(-(a + b MMI)))
pas <- function(d) glm(rasio ~ mmi, family = quasibinomial(link = "logit"), data = d)
m_semua <- pas(g)
m_tanpa_tsunami <- pas(g[tsunami == FALSE])
ringkas <- function(m, nama) {
  s <- summary(m)$coefficients
  data.table(model = nama, a = s[1, 1], se_a = s[1, 2], b = s[2, 1], se_b = s[2, 2], p_b = s[2, 4],
             n = nobs(m), devians_nol = m$null.deviance, devians = m$deviance,
             pseudo_r2 = 1 - m$deviance / m$null.deviance)
}
koef <- rbind(ringkas(m_semua, "semua kejadian gempa"), ringkas(m_tanpa_tsunami, "tanpa Aceh dan Donggala"))
fwrite(koef, file.path(DIR_KELUAR, "03_koefisien_kurva_klaim.csv"))
print(koef)

# Kepekaan: buang satu kejadian tiap kali
lo <- rbindlist(lapply(seq_len(nrow(g)), function(i) {
  m <- pas(g[-i]); data.table(dibuang = g$kejadian[i], tanggal = g$tanggal[i], a = coef(m)[1], b = coef(m)[2],
                               rasio_mmi8 = plogis(coef(m)[1] + 8 * coef(m)[2]), rasio_mmi9 = plogis(coef(m)[1] + 9 * coef(m)[2]))
}))
fwrite(lo, file.path(DIR_KELUAR, "03_kepekaan_buang_satu.csv"))
cat(sprintf("Buang-satu: rasio pada MMI VIII antara %.2f%% dan %.2f%%; pada MMI IX antara %.2f%% dan %.2f%%\n",
            100 * min(lo$rasio_mmi8), 100 * max(lo$rasio_mmi8), 100 * min(lo$rasio_mmi9), 100 * max(lo$rasio_mmi9)))

a <- coef(m_semua)[[1]]; b <- coef(m_semua)[[2]]
kurva_klaim <- function(mmi) ifelse(mmi < 5, 0, plogis(a + b * mmi))

# Presisi Beta NU didefinisikan di 00_fungsi.R
RS_STANDAR <- 0.025      # risiko sendiri polis standar gempa: 2,5% nilai pertanggungan (SEOJK 6/2017 Lampiran III)
mmi <- seq(5, 10, by = 0.5)
tab <- data.table(mmi = mmi,
                  klaim_maipark = kurva_klaim(mmi),
                  aulady_bruto = kurva_aulady(mmi),
                  aulady_setelah_rs = lev_beta(kurva_aulady(mmi), NU, RS_STANDAR, 1),
                  pager = kurva_pager(mmi),
                  # Rev. 2: PAGER pada dasar yang sama dengan dua kurva lain (setelah risiko sendiri 2,5%)
                  pager_setelah_rs = lev_beta(kurva_pager(mmi), NU, RS_STANDAR, 1))
fwrite(tab, file.path(DIR_KELUAR, "03_kurva_kerentanan.csv"))
print(tab[, lapply(.SD, function(x) round(100 * x, 3)), .SDcols = -1][, mmi := mmi][])

write_json(list(kurva_utama = "logit pecahan atas rasio klaim MAIPARK", a = a, b = b, mmi_min = 5,
                jumlah_kejadian = nrow(g), pseudo_r2 = koef$pseudo_r2[1],
                a_tanpa_tsunami = coef(m_tanpa_tsunami)[[1]], b_tanpa_tsunami = coef(m_tanpa_tsunami)[[2]],
                presisi_beta = NU, risiko_sendiri_standar = RS_STANDAR,
                porsi_klaim_erupsi = kej[jenis == "erupsi", sum(klaim_incurred_miliar)] / kej[, sum(klaim_incurred_miliar)],
                catatan = "Rasio dihitung terhadap nilai pertanggungan polis yang mengajukan klaim, jadi berlaku sebagai batas atas bagi seluruh eksposur pada intensitas yang sama."),
           file.path(DIR_KELUAR, "03_parameter.json"), auto_unbox = TRUE, pretty = TRUE, digits = 8)

garis <- data.table(mmi = seq(5, 10, by = 0.05))
garis <- melt(garis[, .(mmi, `Logit klaim MAIPARK (sudah setelah risiko sendiri)` = kurva_klaim(mmi),
                        `Aulady & Fujimi setelah risiko sendiri` = lev_beta(kurva_aulady(mmi), NU, RS_STANDAR, 1),
                        `PAGER Indonesia setelah risiko sendiri` = lev_beta(kurva_pager(mmi), NU, RS_STANDAR, 1))], id.vars = "mmi", variable.name = "kurva", value.name = "rasio")
p <- ggplot() +
  geom_line(data = garis, aes(mmi, pmax(rasio, 1e-5), colour = kurva), linewidth = 0.9) +
  geom_point(data = g, aes(mmi, rasio, shape = tsunami), size = 2.2, colour = "#0b0b0b") +
  scale_shape_manual(values = c(`FALSE` = 16, `TRUE` = 17), labels = c("Kejadian klaim", "Kejadian dengan tsunami"), name = NULL) +
  scale_y_log10(labels = function(x) paste0(format(100 * x, drop0trailing = TRUE, decimal.mark = ","), "%")) +
  scale_colour_manual(values = c(WARNA[["biru"]], WARNA[["jingga"]], WARNA[["toska"]])) +
  guides(colour = guide_legend(nrow = 2), shape = guide_legend(nrow = 2)) +
  labs(x = "Intensitas (MMI)", y = "Rasio kerugian terhadap nilai pertanggungan (skala log)") + tema_aic()
simpan_gambar(p, "e4_kurva_kerentanan.png", 6.8, 4.0)
cat("selesai 03\n")
