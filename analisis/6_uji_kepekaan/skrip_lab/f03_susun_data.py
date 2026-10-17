"""F03: menyusun data masukan dari MAIPARK edisi 30 Juni 2025 untuk uji kepekaan versi data.

Angka disalin tangan dari halaman PDF 9 (Tabel 1.1) dan 76 (Tabel 4.1) edisi Juni 2025, yang teksnya berupa
gambar vektor (tidak dapat diekstrak). Pemeriksaan: jumlah 34 provinsi tiap tahun dicocokkan dengan baris TOTAL
tercetak, dan rasio klaim dihitung ulang lalu dicocokkan dengan rasio tercetak.

Pemakaian: python f03_susun_data.py <folder AIC_CASE salinan uji> <folder AIC_CASE Rev. 1 sebagai pembanding>
Yang ditimpa di salinan uji: 1_olah_data/data/maipark_eksposur_provinsi.csv, portofolio_titik.csv,
maipark_kejadian_klaim.csv, besaran_industri.json (hanya eksposur_uy_triliun).
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
UJI, REV1 = Path(sys.argv[1]), Path(sys.argv[2])
D_UJI = UJI / "analisis" / "1_olah_data" / "data"
D_REV1 = REV1 / "analisis" / "1_olah_data" / "data"

# Tabel 1.1 edisi Juni 2025, triliun rupiah: UY 2021, 2022, 2023, 2024, 2025 (2025 baru setengah tahun)
T11 = {
    "NAD": (13.48, 18.93, 19.94, 13.21, 4.02), "SUMATERA UTARA": (118.25, 158.37, 157.56, 148.49, 57.12),
    "SUMATERA BARAT": (59.84, 56.34, 46.47, 44.89, 12.10), "RIAU": (63.40, 70.40, 78.61, 78.43, 11.53),
    "JAMBI": (11.55, 11.34, 14.02, 12.94, 2.92), "SUMATERA SELATAN": (68.78, 68.28, 85.01, 82.43, 11.07),
    "BENGKULU": (9.87, 11.52, 12.25, 6.45, 2.14), "LAMPUNG": (44.12, 45.54, 57.11, 63.01, 20.45),
    "KEP BANGKA-BELITUNG": (6.77, 6.97, 6.40, 7.74, 1.38), "KEPULAUAN RIAU": (109.72, 78.51, 91.52, 102.36, 20.80),
    "JAKARTA": (625.91, 724.17, 719.43, 838.67, 196.19), "JAWA BARAT": (895.64, 962.29, 1099.97, 1134.61, 343.79),
    "JAWA TENGAH": (168.73, 216.84, 197.73, 165.47, 48.45), "DIY": (20.55, 22.57, 24.48, 26.55, 12.72),
    "JAWA TIMUR": (398.30, 487.75, 495.98, 461.82, 131.15), "BANTEN": (381.21, 413.46, 491.35, 445.02, 125.69),
    "BALI": (101.57, 80.83, 112.25, 113.72, 32.96), "NUSA TENGGARA BARAT": (12.54, 48.53, 48.50, 37.82, 6.52),
    "NUSA TENGGARA TIMUR": (6.98, 8.85, 8.90, 10.58, 4.16), "KALIMANTAN BARAT": (30.35, 34.42, 37.62, 39.91, 6.39),
    "KALIMANTAN TENGAH": (12.92, 11.76, 23.93, 14.87, 2.48), "KALIMANTAN SELATAN": (40.27, 43.76, 47.85, 32.85, 4.30),
    "KALIMANTAN TIMUR": (96.68, 102.05, 97.04, 127.73, 10.87), "SULAWESI UTARA": (35.84, 33.93, 28.96, 27.55, 8.52),
    "SULAWESI TENGAH": (32.12, 61.32, 138.80, 190.16, 95.41), "SULAWESI SELATAN": (47.25, 54.46, 142.49, 52.49, 12.67),
    "SULAWESI TENGGARA": (42.90, 69.48, 58.06, 60.34, 1.20), "GORONTALO": (6.27, 9.51, 9.41, 11.00, 1.44),
    "SULAWESI BARAT": (4.80, 5.82, 5.47, 4.82, 0.32), "MALUKU": (3.48, 3.20, 3.40, 4.47, 2.07),
    "MALUKU UTARA": (23.47, 38.92, 42.42, 54.90, 9.12), "PAPUA BARAT": (8.51, 9.49, 10.93, 11.30, 1.48),
    "PAPUA": (243.02, 273.28, 327.53, 342.92, 11.77), "KALIMANTAN UTARA": (3.80, 3.95, 4.55, 16.34, 1.18),
}
TOTAL_TERCETAK = (3748.90, 4246.84, 4745.94, 4785.85, 1214.37)
# Tabel 4.1 edisi Juni 2025, miliar rupiah: eksposur terdampak, klaim incurred, rasio tercetak (persen)
T41 = {
    ("Pariaman", "30-Sep-09"): (43998.28, 1086.16, 2.47), ("Donggala", "28-Sep-18"): (133898.15, 1061.19, 0.79),
    ("Aceh", "26-Dec-04"): (24362.49, 973.98, 4.00), ("Lombok", "05-Aug-18"): (175409.47, 364.42, 0.21),
    ("Yogya", "27-May-06"): (11585.64, 320.18, 2.76), ("Kelud", "13-Feb-14"): (1614.88, 216.54, 13.41),
    ("Majene", "15-Jan-21"): (16688.34, 202.68, 1.21), ("Anak Krakatau", "22-Dec-18"): (570.02, 49.80, 8.74),
    ("Bengkulu", "12-Sep-07"): (7323.26, 48.90, 0.67), ("Bima", "09-Nov-09"): (27330.48, 43.04, 0.16),
    ("Padang", "16-Aug-09"): (27445.32, 42.78, 0.16), ("Merapi", "25-Oct-10"): (1060.68, 27.50, 2.59),
    ("Cianjur", "21-Nov-22"): (89045.10, 26.78, 0.03), ("Tasikmalaya", "02-Sep-09"): (42847.61, 24.36, 0.06),
    ("Padang", "06-Mar-07"): (8560.08, 22.80, 0.27), ("Bawean", "22-Mar-24"): (34376.92, 13.86, 0.04),
}

# ---------- pemeriksaan salinan tangan ----------
jumlah = [round(sum(v[i] for v in T11.values()), 2) for i in range(5)]
print("Jumlah 34 provinsi :", jumlah)
print("TOTAL tercetak     :", list(TOTAL_TERCETAK))
selisih = [round(a - b, 2) for a, b in zip(jumlah, TOTAL_TERCETAK)]
print("Selisih            :", selisih)
assert len(T11) == 34 and max(abs(s) for s in selisih) <= 0.10, "salinan Tabel 1.1 tidak cocok dengan baris TOTAL"
for (nama, tgl), (eks, klaim, rasio) in T41.items():
    assert abs(100 * klaim / eks - rasio) < 0.006, (nama, tgl, 100 * klaim / eks, rasio)
print("Rasio 16 kejadian Tabel 4.1 cocok dengan rasio tercetak (toleransi pembulatan 0,005 poin)")

# ---------- eksposur per provinsi ----------
lama = pd.read_csv(D_REV1 / "maipark_eksposur_provinsi.csv")
assert set(lama["provinsi"]) == set(T11)
baru = lama.copy()
for i, kol in enumerate(["uy_2021", "uy_2022", "uy_2023", "uy_2024"]):
    baru[kol] = baru["provinsi"].map(lambda p: T11[p][i])
# UY 2020 tidak ada di edisi Juni. Papua UY 2020 diskalakan dengan rasio revisi UY 2021 (asumsi auditor).
f_papua = T11["PAPUA"][0] / float(lama.loc[lama["provinsi"] == "PAPUA", "uy_2021"].iloc[0])
baru.loc[baru["provinsi"] == "PAPUA", "uy_2020"] = round(float(lama.loc[lama["provinsi"] == "PAPUA", "uy_2020"].iloc[0]) * f_papua, 2)
baru.to_csv(D_UJI / "maipark_eksposur_provinsi.csv", index=False)
banding = pd.DataFrame({"provinsi": lama["provinsi"]})
for kol in ["uy_2021", "uy_2022", "uy_2023", "uy_2024"]:
    banding[f"{kol}_des2024"] = lama[kol]; banding[f"{kol}_jun2025"] = baru[kol]
banding["porsi_rata_des2024_uy2020_2024"] = lama[[f"uy_{y}" for y in range(2020, 2025)]].sum(axis=1) / lama[[f"uy_{y}" for y in range(2020, 2025)]].sum().sum()
banding["porsi_rata_jun2025_uy2021_2024"] = baru[["uy_2021", "uy_2022", "uy_2023", "uy_2024"]].sum(axis=1) / baru[["uy_2021", "uy_2022", "uy_2023", "uy_2024"]].sum().sum()
banding["selisih_porsi_poin"] = 100 * (banding["porsi_rata_jun2025_uy2021_2024"] - banding["porsi_rata_des2024_uy2020_2024"])
print(f"Faktor revisi Papua (UY 2021): {f_papua:.4f}")

# ---------- portofolio titik: bobot dari rata-rata UY 2021-2024 edisi Juni ----------
titik = pd.read_csv(D_REV1 / "portofolio_titik.csv")
bobot = banding.set_index("provinsi")["porsi_rata_jun2025_uy2021_2024"]
titik["bobot_provinsi"] = titik["provinsi"].map(bobot)
titik["bobot"] = titik["bobot_provinsi"] * titik["porsi_dalam_provinsi"]
assert abs(titik["bobot"].sum() - 1) < 1e-9
titik.to_csv(D_UJI / "portofolio_titik.csv", index=False)

# ---------- kejadian klaim ----------
kej = pd.read_csv(D_REV1 / "maipark_kejadian_klaim.csv")
kej_baru = kej.copy()
for i, b in kej.iterrows():
    eks, klaim, _ = T41[(b["kejadian"], b["tanggal"])]
    kej_baru.loc[i, ["eksposur_terdampak_miliar", "klaim_incurred_miliar", "rasio"]] = [eks, klaim, klaim / eks]
kej_baru.to_csv(D_UJI / "maipark_kejadian_klaim.csv", index=False)
kej_banding = kej[["kejadian", "tanggal", "jenis", "eksposur_terdampak_miliar", "klaim_incurred_miliar", "rasio"]].merge(
    kej_baru[["kejadian", "tanggal", "eksposur_terdampak_miliar", "klaim_incurred_miliar", "rasio"]], on=["kejadian", "tanggal"], suffixes=("_des2024", "_jun2025"))

# ---------- besaran industri: hanya deret eksposur ----------
bi = json.loads((D_REV1 / "besaran_industri.json").read_text(encoding="utf-8"))
bi_lama = dict(bi["eksposur_uy_triliun"])
bi["eksposur_uy_triliun"] = {str(y): round(float(baru[f"uy_{y}"].sum()), 2) for y in range(2020, 2025)}
bi["catatan_uji_F03"] = "eksposur_uy_triliun 2021-2024 dari MAIPARK edisi 30 Juni 2025; 2020 = edisi Desember 2024 dengan Papua diskalakan; butir lain tidak diubah"
(D_UJI / "besaran_industri.json").write_text(json.dumps(bi, indent=1, ensure_ascii=False), encoding="utf-8")

keluar = Path(__file__).resolve().parents[1] / "f03_maipark_juni2025"
banding.to_csv(keluar / "banding_eksposur_provinsi.csv", index=False)
kej_banding.to_csv(keluar / "banding_kejadian_klaim.csv", index=False)
pd.set_option("display.width", 250)
print(banding.sort_values("selisih_porsi_poin").head(4)[["provinsi", "porsi_rata_des2024_uy2020_2024", "porsi_rata_jun2025_uy2021_2024", "selisih_porsi_poin"]].round(4).to_string(index=False))
print(banding.sort_values("selisih_porsi_poin").tail(5)[["provinsi", "porsi_rata_des2024_uy2020_2024", "porsi_rata_jun2025_uy2021_2024", "selisih_porsi_poin"]].round(4).to_string(index=False))
zona = ["PAPUA", "JAWA BARAT", "JAKARTA", "SUMATERA UTARA", "BANTEN"]
print(f"Porsi eksposur zona inti: Des 2024 {banding[banding.provinsi.isin(zona)]['porsi_rata_des2024_uy2020_2024'].sum():.4f}; Jun 2025 {banding[banding.provinsi.isin(zona)]['porsi_rata_jun2025_uy2021_2024'].sum():.4f}")
print("Eksposur UY (triliun) Des 2024:", bi_lama, "\n                      Jun 2025:", bi["eksposur_uy_triliun"])
print(kej_banding.round(4).to_string(index=False))
g = kej_banding[kej_banding["jenis"] == "gempa"]
print(f"Klaim 13 kejadian gempa: Des 2024 {g['klaim_incurred_miliar_des2024'].sum():.2f}; Jun 2025 {g['klaim_incurred_miliar_jun2025'].sum():.2f} miliar")
