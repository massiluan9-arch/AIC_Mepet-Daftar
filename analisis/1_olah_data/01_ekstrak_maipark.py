"""Mengekstrak tabel inti Laporan Statistik Asuransi Gempa Bumi Indonesia (MAIPARK, per 31 Desember 2024).

Sumber: data/industri_asuransi/maipark/MAIPARK_Statistik_Gempa_per_31_Des_2024.pdf
Keluaran (CSV rapi di 1_olah_data/data):
  maipark_eksposur_provinsi.csv   Tabel 1.1, triliun rupiah per tahun underwriting (UY)
  maipark_premi_provinsi.csv      Tabel 2.1, miliar rupiah per UY
  maipark_onrisk_2024.csv         Tabel 1.27, eksposur berjalan per kuartal 2024, triliun rupiah
  maipark_klaim_provinsi.csv      Tabel 4.4, juta rupiah per UY
  maipark_okupasi.csv             Tabel 1.2 dan 2.2
  maipark_kejadian_klaim.csv      Tabel 4.1, 16 kejadian klaim terbesar
  maipark_profil_risiko.csv       Profil risiko semua okupasi UY 2020-2024 (rentang nilai pertanggungan)
Tiap tabel provinsi diperiksa terhadap baris TOTAL yang tercetak.
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

AKAR = Path(__file__).resolve().parents[2]
PDF = AKAR / "data" / "industri_asuransi" / "maipark" / "MAIPARK_Statistik_Gempa_per_31_Des_2024.pdf"
KELUAR = Path(__file__).resolve().parent / "data"
UY = [2020, 2021, 2022, 2023, 2024]


def angka(s):
    """'1.094,98' -> 1094.98; '-' -> 0."""
    s = s.strip()
    if s in ("-", ""):
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def baris_halaman(doc, nomor):
    return [b.strip() for b in doc[nomor - 1].get_text().split("\n") if b.strip()]


def tabel_provinsi(doc, nomor, kolom, pasangan=True):
    """Tabel berpola: NO | PROVINSI | IDN_xx | (nilai, persen) x n. Mengembalikan DataFrame lebar."""
    b = baris_halaman(doc, nomor)
    out, i = [], 0
    langkah = 2 if pasangan else 1
    while i < len(b) - 2:
        if re.fullmatch(r"\d{1,2}", b[i]) and re.fullmatch(r"IDN_[A-Z]{2}", b[i + 2]):
            nilai = [angka(b[i + 3 + langkah * k]) for k in range(len(kolom))]
            out.append([b[i + 1], b[i + 2]] + nilai)
            i += 3 + langkah * len(kolom)
        else:
            i += 1
    df = pd.DataFrame(out, columns=["provinsi", "cresta_id"] + kolom)
    total = None
    if "TOTAL" in b:
        j = b.index("TOTAL")
        total = [angka(b[j + 1 + langkah * k]) for k in range(len(kolom))]
    return df, total


def main():
    doc = pymupdf.open(PDF)
    KELUAR.mkdir(parents=True, exist_ok=True)
    cek = []

    for nama, hal, satuan in (("eksposur", 9, "triliun_rp"), ("premi", 37, "miliar_rp"), ("klaim", 79, "juta_rp")):
        df, total = tabel_provinsi(doc, hal, [f"uy_{y}" for y in UY])
        assert len(df) == 34, (nama, len(df))
        if total:
            for k, y in enumerate(UY):
                selisih = abs(df[f"uy_{y}"].sum() - total[k])
                cek.append((nama, y, df[f"uy_{y}"].sum(), total[k], selisih))
        df.insert(2, "satuan", satuan)
        df.to_csv(KELUAR / f"maipark_{nama}_provinsi.csv", index=False)

    df, total = tabel_provinsi(doc, 35, ["kuartal_1", "kuartal_2", "kuartal_3", "kuartal_4"])
    assert len(df) == 34
    df.insert(2, "satuan", "triliun_rp")
    df.to_csv(KELUAR / "maipark_onrisk_2024.csv", index=False)
    for k in range(4):
        cek.append(("onrisk", f"K{k + 1}", df.iloc[:, 3 + k].sum(), total[k] if total else float("nan"),
                    abs(df.iloc[:, 3 + k].sum() - total[k]) if total else float("nan")))

    # Okupasi: eksposur (hal 10) dan premi (hal 38)
    okupasi = []
    for nama, hal in (("eksposur_triliun_rp", 10), ("premi_miliar_rp", 38)):
        b = baris_halaman(doc, hal)
        for kode in ("A", "C", "I", "R"):
            j = next(i for i in range(len(b) - 1) if b[i] == kode and b[i - 1].isupper())
            for k, y in enumerate(UY):
                okupasi.append({"besaran": nama, "okupasi": b[j - 1].title(), "uy": y, "nilai": angka(b[j + 1 + 2 * k])})
    pd.DataFrame(okupasi).to_csv(KELUAR / "maipark_okupasi.csv", index=False)

    # Kejadian klaim terbesar (hal 76)
    b = baris_halaman(doc, 76)
    kej, i = [], 0
    while i < len(b) - 6:
        if re.fullmatch(r"\d{1,2}", b[i]) and re.fullmatch(r"\d{2}-[A-Za-z]{3}-\d{2}", b[i + 2]):
            if b[i + 3].startswith("Letusan"):
                kej.append({"kejadian": b[i + 1].title(), "tanggal": b[i + 2], "jenis": "erupsi", "magnitudo": None, "mmi_maks": None,
                            "kedalaman_km": None, "eksposur_terdampak_miliar": angka(b[i + 4]),
                            "klaim_incurred_miliar": angka(b[i + 5]), "rasio": angka(b[i + 6].rstrip("%")) / 100})
                i += 7
            else:
                kej.append({"kejadian": b[i + 1].title(), "tanggal": b[i + 2], "jenis": "gempa", "magnitudo": angka(b[i + 3]),
                            "mmi_maks": b[i + 4], "kedalaman_km": angka(b[i + 5]), "eksposur_terdampak_miliar": angka(b[i + 6]),
                            "klaim_incurred_miliar": angka(b[i + 7]), "rasio": angka(b[i + 8].rstrip("%")) / 100})
                i += 9
        else:
            i += 1
    pd.DataFrame(kej).to_csv(KELUAR / "maipark_kejadian_klaim.csv", index=False)
    assert len(kej) == 16, len(kej)

    # Profil risiko semua okupasi, UY 2020-2024 (hal 82): no | dari | sampai | f | F | % | % | premi | kum | % | % | eksposur | kum | % | %
    b = baris_halaman(doc, 82)
    mulai = b.index("(o)") + 1
    prof, i = [], mulai
    while i + 14 < len(b) and re.fullmatch(r"\d{1,2}", b[i]):
        dari = 0.0 if b[i + 1] == "-" else angka(b[i + 1])
        sampai = b[i + 2]
        prof.append({"no": int(b[i]), "ts_dari_juta": dari, "ts_sampai_juta": sampai,
                     "jumlah_risiko": angka(b[i + 3]), "premi_juta": angka(b[i + 7]), "eksposur_juta": angka(b[i + 11])})
        i += 15
    pd.DataFrame(prof).to_csv(KELUAR / "maipark_profil_risiko.csv", index=False)

    print("Pemeriksaan jumlah provinsi terhadap baris TOTAL tercetak:")
    for nama, y, jumlah, tot, selisih in cek:
        print(f"  {nama:9s} {y}: jumlah {jumlah:12.2f}  total tercetak {tot:12.2f}  selisih {selisih:.2f}")
    print("kejadian klaim:", len(kej), "| baris profil risiko:", len(prof))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
