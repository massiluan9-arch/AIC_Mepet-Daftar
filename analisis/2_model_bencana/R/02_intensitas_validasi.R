# 02. Validasi persamaan intensitas Allen, Wald & Worden (2012) terhadap observasi Indonesia.
# Data: data/katastrofe/gempa/intensitas/mmi_obs_indonesia.csv (observasi intensitas gempa dangkal, USGS ShakeMap/DYFI).
# Keluaran: keluaran/02_*.csv, keluaran/02_parameter.json, gambar/e3_residu_intensitas.png

.arg <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(normalizePath(sub("^--file=", "", .arg[grep("^--file=", .arg)]))), "00_fungsi.R"))

o <- fread(file.path(DIR_KASUS, "data", "katastrofe", "gempa", "intensitas", "mmi_obs_indonesia.csv"))
# Empat observasi berjarak sekitar 10.000 km dari sumbernya (koordinat stasiun keliru) dibuang.
n_awal <- nrow(o)
o <- o[rhypo_km <= 1000]
cat(sprintf("Dibuang karena jarak tidak wajar: %d observasi\n", n_awal - nrow(o)))
o[, rrup := pmax(rrup_km, 1)]
o[, `:=`(res_rhyp = mmi_obs - mmi_allen_rhyp(mag, rhypo_km), res_rrup = mmi_obs - mmi_allen_rrup(mag, rrup))]
cat(sprintf("Observasi: %d dari %d gempa; M %.1f-%.1f; kedalaman paling dalam %.0f km\n",
            nrow(o), uniqueN(o$event_id), min(o$mag), max(o$mag), max(o$depth_km)))

ringkas <- function(d, kelompok) {
  d[, .(n = .N, bias_rhyp = mean(res_rhyp), rmse_rhyp = sqrt(mean(res_rhyp^2)),
        bias_rrup = mean(res_rrup), rmse_rrup = sqrt(mean(res_rrup^2))), by = kelompok]
}
o[, kelas_jarak := cut(rhypo_km, c(0, 50, 100, 200, 1e4), labels = c("<=50 km", "50-100 km", "100-200 km", ">200 km"))]
o[, kelas_mag := cut(mag, c(0, 6.5, 7.5, 10), right = FALSE, labels = c("M<6,5", "6,5<=M<7,5", "M>=7,5"))]
tab <- rbind(cbind(kelompok = "semua", ringkas(o, NULL)),
             setnames(ringkas(o, "kelas_jarak"), "kelas_jarak", "kelompok"),
             setnames(ringkas(o, "kelas_mag"), "kelas_mag", "kelompok"), fill = TRUE)
fwrite(tab, file.path(DIR_KELUAR, "02_bias_intensitas.csv"))
print(tab)

# Pemisahan residu: antar-gempa (tau) dan dalam-gempa (phi), cara momen
pisah <- function(res, id) {
  rata <- tapply(res, id, mean); n <- tapply(res, id, length)
  dalam <- res - rata[as.character(id)]
  phi <- sqrt(sum(dalam^2) / (length(res) - length(rata)))
  tau2 <- max(var(rata) - phi^2 * mean(1 / n), 0)
  c(bias_antar_gempa = mean(rata), tau = sqrt(tau2), phi = phi, total = sqrt(tau2 + phi^2))
}
sig <- rbind(data.table(versi = "jarak hiposenter", t(pisah(o$res_rhyp, o$event_id))),
             data.table(versi = "jarak ruptur", t(pisah(o$res_rrup, o$event_id))))
fwrite(sig, file.path(DIR_KELUAR, "02_simpangan_residu.csv"))
print(sig)

# Uji t atas bias antar-gempa versi jarak ruptur (H0: bias = 0)
rata_gempa <- o[, .(r = mean(res_rrup)), by = event_id]$r
uji <- t.test(rata_gempa)
cat(sprintf("Bias antar-gempa versi jarak ruptur: %.3f; t = %.2f; nilai p = %.3f\n", mean(rata_gempa), uji$statistic, uji$p.value))

write_json(list(versi_dipakai = "jarak ruptur", tau = sig[versi == "jarak ruptur", tau], phi = sig[versi == "jarak ruptur", phi],
                bias_antar_gempa = mean(rata_gempa), p_bias = uji$p.value, jumlah_observasi = nrow(o),
                jumlah_gempa = uniqueN(o$event_id), kedalaman_maks_km = max(o$depth_km),
                catatan = "phi memuat galat pengamatan intensitas; dipakai apa adanya sehingga sebaran simulasi cenderung lebar"),
           file.path(DIR_KELUAR, "02_parameter.json"), auto_unbox = TRUE, pretty = TRUE, digits = 6)

p <- ggplot(o, aes(rrup, res_rrup)) +
  geom_hline(yintercept = 0, colour = "#c3c2b7") +
  geom_point(colour = WARNA[["biru"]], alpha = 0.45, size = 1.2) +
  geom_smooth(method = "loess", formula = y ~ x, se = FALSE, colour = WARNA[["jingga"]], linewidth = 0.8) +
  scale_x_log10() +
  labs(x = "Jarak ruptur (km, skala log)", y = "Residu MMI (teramati - model)") + tema_aic()
simpan_gambar(p, "e3_residu_intensitas.png", 6.2, 3.4)
cat("selesai 02\n")
