"""Menyusun portofolio representatif PT Aktu Proteksi dari statistik MAIPARK.

Brief tidak memberi data polis. Portofolio diwakili sebaran eksposur asuransi gempa industri per
provinsi (MAIPARK, Tabel 1.1, rata-rata tahun underwriting 2020-2024). Tiap provinsi diwakili satu
atau dua titik pusat kegiatan industri dan niaga, karena 65% eksposur berokupasi industri.

Keluaran: 1_olah_data/data/portofolio_titik.csv dan 1_olah_data/data/besaran_industri.json
"""
import json
from pathlib import Path

import pandas as pd

DI_SINI = Path(__file__).resolve().parent
DATA = DI_SINI / "data"
PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR = 26938.117   # OJK, Statistik Perasuransian 2024, Tabel 2.10.4

# (provinsi MAIPARK, nama titik, lintang, bujur, porsi dalam provinsi, alasan pemilihan titik)
TITIK = [
    ("NAD", "Banda Aceh", 5.55, 95.32, 1.0, "ibu kota"),
    ("SUMATERA UTARA", "Medan", 3.59, 98.67, 1.0, "ibu kota dan kawasan industri"),
    ("SUMATERA BARAT", "Padang", -0.95, 100.35, 1.0, "ibu kota"),
    ("RIAU", "Pekanbaru", 0.51, 101.45, 1.0, "ibu kota"),
    ("JAMBI", "Jambi", -1.61, 103.61, 1.0, "ibu kota"),
    ("SUMATERA SELATAN", "Palembang", -2.99, 104.76, 1.0, "ibu kota dan kawasan industri"),
    ("BENGKULU", "Bengkulu", -3.80, 102.27, 1.0, "ibu kota"),
    ("LAMPUNG", "Bandar Lampung", -5.43, 105.26, 1.0, "ibu kota"),
    ("KEP BANGKA-BELITUNG", "Pangkal Pinang", -2.13, 106.11, 1.0, "ibu kota"),
    ("KEPULAUAN RIAU", "Batam", 1.08, 104.03, 1.0, "pusat industri"),
    ("JAKARTA", "Jakarta", -6.20, 106.85, 1.0, "ibu kota"),
    ("JAWA BARAT", "Bekasi-Karawang", -6.30, 107.15, 0.6, "koridor kawasan industri; porsi 60% asumsi"),
    ("JAWA BARAT", "Bandung", -6.91, 107.61, 0.4, "ibu kota; porsi 40% asumsi"),
    ("JAWA TENGAH", "Semarang", -6.99, 110.42, 1.0, "ibu kota dan kawasan industri"),
    ("DIY", "Yogyakarta", -7.80, 110.37, 1.0, "ibu kota"),
    ("JAWA TIMUR", "Surabaya-Gresik", -7.25, 112.75, 1.0, "ibu kota dan kawasan industri"),
    ("BANTEN", "Tangerang", -6.18, 106.63, 0.6, "kawasan industri dan niaga; porsi 60% asumsi"),
    ("BANTEN", "Cilegon", -6.02, 106.05, 0.4, "kawasan industri berat; porsi 40% asumsi"),
    ("BALI", "Denpasar", -8.65, 115.22, 1.0, "ibu kota"),
    ("NUSA TENGGARA BARAT", "Mataram", -8.58, 116.12, 1.0, "ibu kota"),
    ("NUSA TENGGARA TIMUR", "Kupang", -10.18, 123.60, 1.0, "ibu kota"),
    ("KALIMANTAN BARAT", "Pontianak", -0.03, 109.33, 1.0, "ibu kota"),
    ("KALIMANTAN TENGAH", "Palangkaraya", -2.21, 113.92, 1.0, "ibu kota"),
    ("KALIMANTAN SELATAN", "Banjarmasin", -3.32, 114.59, 1.0, "ibu kota"),
    ("KALIMANTAN TIMUR", "Balikpapan", -1.24, 116.85, 1.0, "pusat industri migas"),
    ("SULAWESI UTARA", "Manado", 1.49, 124.84, 1.0, "ibu kota"),
    ("SULAWESI TENGAH", "Morowali", -2.82, 122.15, 0.7, "kawasan industri nikel; eksposur provinsi naik empat kali 2020-2024; porsi 70% asumsi"),
    ("SULAWESI TENGAH", "Palu", -0.90, 119.87, 0.3, "ibu kota; porsi 30% asumsi"),
    ("SULAWESI SELATAN", "Makassar", -5.15, 119.43, 1.0, "ibu kota"),
    ("SULAWESI TENGGARA", "Kendari", -3.99, 122.51, 1.0, "ibu kota, dekat kawasan industri Konawe"),
    ("GORONTALO", "Gorontalo", 0.54, 123.06, 1.0, "ibu kota"),
    ("SULAWESI BARAT", "Mamuju", -2.68, 118.89, 1.0, "ibu kota"),
    ("MALUKU", "Ambon", -3.70, 128.18, 1.0, "ibu kota"),
    ("MALUKU UTARA", "Weda", 0.47, 127.93, 1.0, "kawasan industri nikel Teluk Weda"),
    ("PAPUA BARAT", "Sorong", -0.88, 131.25, 1.0, "pusat kegiatan ekonomi"),
    ("PAPUA", "Timika", -4.55, 136.89, 1.0, "pusat pertambangan; eksposur provinsi didominasi satu kawasan"),
    ("KALIMANTAN UTARA", "Tarakan", 3.30, 117.63, 1.0, "pusat kegiatan ekonomi"),
]


def main():
    ek = pd.read_csv(DATA / "maipark_eksposur_provinsi.csv")
    pr = pd.read_csv(DATA / "maipark_premi_provinsi.csv")
    on = pd.read_csv(DATA / "maipark_onrisk_2024.csv")
    kl = pd.read_csv(DATA / "maipark_klaim_provinsi.csv")
    uy = [f"uy_{y}" for y in range(2020, 2025)]
    bobot = ek.set_index("provinsi")[uy].mean(axis=1)
    bobot = bobot / bobot.sum()
    tarif = (pr.set_index("provinsi")[uy].sum(axis=1) / ek.set_index("provinsi")[uy].sum(axis=1))  # per mil

    t = pd.DataFrame(TITIK, columns=["provinsi", "titik", "lintang", "bujur", "porsi_dalam_provinsi", "alasan"])
    assert set(t["provinsi"]) == set(ek["provinsi"]), set(ek["provinsi"]) ^ set(t["provinsi"])
    assert (t.groupby("provinsi")["porsi_dalam_provinsi"].sum().round(9) == 1).all()
    t["bobot_provinsi"] = t["provinsi"].map(bobot)
    t["bobot"] = t["bobot_provinsi"] * t["porsi_dalam_provinsi"]
    t["tarif_gempa_per_mil"] = t["provinsi"].map(tarif)
    t["cresta_id"] = t["provinsi"].map(ek.set_index("provinsi")["cresta_id"])
    assert abs(t["bobot"].sum() - 1) < 1e-9
    t.to_csv(DATA / "portofolio_titik.csv", index=False)

    onrisk = on[[f"kuartal_{k}" for k in range(1, 5)]].sum()
    besaran = {
        "sumber": "MAIPARK, Laporan Statistik Asuransi Gempa Bumi Indonesia per 31 Desember 2024; OJK, Statistik Perasuransian 2024 Tabel 2.10.4",
        "eksposur_uy_triliun": {y: round(float(ek[c].sum()), 2) for y, c in zip(range(2020, 2025), uy)},
        "premi_gempa_uy_miliar": {y: round(float(pr[c].sum()), 2) for y, c in zip(range(2020, 2025), uy)},
        "klaim_uy_miliar": {y: round(float(kl[c].sum()) / 1000, 2) for y, c in zip(range(2020, 2025), uy)},
        "eksposur_berjalan_2024_rata_triliun": round(float(onrisk.mean()), 2),
        "premi_harta_benda_langsung_2024_miliar": PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR,
        "E_eksposur_gempa_per_premi": round(float(onrisk.mean()) * 1000 / PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR, 2),
        "E_rentang": [round(float(onrisk.min()) * 1000 / PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR, 1),
                      round(float(ek["uy_2023"].sum()) * 1000 / PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR, 1)],
        "tarif_gempa_rata_per_mil": round(float(pr[uy].sum().sum() / ek[uy].sum().sum()), 4),
        "porsi_premi_gempa_dalam_premi_harta_benda": round(float(pr["uy_2024"].sum()) / PREMI_HARTA_BENDA_LANGSUNG_2024_MILIAR, 4),
        "rasio_klaim_5_tahun": round(float(kl[uy].sum().sum() / 1000 / pr[uy].sum().sum()), 4),
        "klaim_per_eksposur_5_tahun_per_mil": round(float(kl[uy].sum().sum() / 1000 / ek[uy].sum().sum()), 4),
        "catatan_E": "E = eksposur gempa berjalan rata-rata empat kuartal 2024 dibagi premi harta benda penutupan langsung 2024.",
    }
    (DATA / "besaran_industri.json").write_text(json.dumps(besaran, indent=1, ensure_ascii=False), encoding="utf-8")
    print(t[["provinsi", "titik", "bobot", "tarif_gempa_per_mil"]].sort_values("bobot", ascending=False).head(12).to_string(index=False))
    print(json.dumps(besaran, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
