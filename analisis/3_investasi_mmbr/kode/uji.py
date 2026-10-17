"""Pemeriksaan konsistensi. Gagal (kode keluar 1) bila ada satu pun yang tidak cocok.

Yang diperiksa: parameter terhadap berkas sumbernya, aritmetika AYD dan MMBR, rumus harga obligasi,
kecocokan hasil.json dengan perhitungan ulang, dan dokumen hasil terhadap hasil.json.
"""
import json
import sys
import warnings

import openpyxl
import yaml

import mmbr as mm
import model_investasi as mi
import rekonstruksi_industri as ri
from umum import AKAR, BERKAS_HASIL, DIR_ANALISIS, daftar_varian, muat_parameter

lulus, gagal = [], []


def periksa(nama, syarat, rincian=""):
    (lulus if syarat else gagal).append(nama)
    print(("  lulus  " if syarat else "  GAGAL  ") + nama + (f"  [{rincian}]" if rincian else ""))


def dekat(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


par = muat_parameter()
reg, profil, neraca, pasar = par["regulasi"], par["profil"], par["neraca_dasar"], par["pasar"]
h = json.loads(BERKAS_HASIL.read_text(encoding="utf-8"))
varian = daftar_varian(profil)
n = mm.nilai_neraca(neraca)

print("1. Parameter")
for kode, nama, label, bobot in varian:
    periksa(f"bobot {kode} berjumlah 100%", dekat(sum(bobot.values()), 1.0))
r = profil["profil"]
periksa("varian Konservatif di dalam rentang brief",
        all(0.70 <= v["bobot"]["sbn"] <= 0.80 and 0.20 <= v["bobot"]["deposito"] <= 0.30 for v in r["Konservatif"]["varian"].values()))
periksa("varian Moderat di dalam rentang brief",
        all(0.40 <= v["bobot"]["korporasi"] <= 0.60 and 0.30 <= v["bobot"]["sbn"] <= 0.50 and v["bobot"]["reksadana_saham"] == 0.10
            for v in r["Moderat"]["varian"].values()))
periksa("varian Agresif di dalam rentang brief",
        all(0.20 <= v["bobot"]["saham"] <= 0.40 and 0.60 <= v["bobot"]["korporasi"] <= 0.80 for v in r["Agresif"]["varian"].values()))

fp, lr, _ = ri.baca_industri()
ind = ri.rasio_per_100_premi_langsung(fp, lr)
for butir in ("cadangan_bencana", "utang_klaim", "utang_lain", "kas_dan_bank", "bua_dikurangi_bpl", "dac"):
    periksa(f"neraca_dasar.{butir} cocok dengan Statistik Asuransi Juli 2025", abs(n[butir] - ind[butir]) < 0.006,
            f"yaml {n[butir]} lawan sumber {ind[butir]:.3f}")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    wb = openpyxl.load_workbook(AKAR / "data/industri_asuransi/ojk_statistik_2024/2.10 Rekapitulasi Premi, Klaim dan Komisi Tahun 2024.xlsx",
                                read_only=True, data_only=True)
langsung = [row[2] for row in wb["4 REKAP"].iter_rows(values_only=True) if isinstance(row[2], (int, float))]
premi, capybmp, klaim_os = langsung[0], langsung[3], langsung[8]
periksa("neraca_dasar.capybmp cocok dengan Tabel 2.10.4", abs(n["capybmp"] - 100 * capybmp / premi) < 0.006, f"{100 * capybmp / premi:.3f}")
periksa("neraca_dasar.cadangan_klaim cocok dengan Tabel 2.10.4", abs(n["cadangan_klaim"] - 100 * klaim_os / premi) < 0.006, f"{100 * klaim_os / premi:.3f}")

print("2. Uji AYD")
harap = {"K80": 0.0, "K75": 0.0, "K70": 0.0, "M40": 0.0, "M50": 0.0, "M60": 0.10, "A20": 0.30, "A30": 0.20, "A40": 0.20}
for kode, _, _, bobot in varian:
    periksa(f"porsi tidak diakui {kode} = {harap[kode]:.2f}", dekat(mm.uji_ayd(bobot, reg)["porsi_tidak_diakui"], harap[kode]))
a40 = mm.uji_ayd(next(b for k, _, _, b in varian if k == "A40"), reg)
periksa("A40: gabungan diakui tepat 80%", dekat(a40["diakui"]["korporasi"] + a40["diakui"]["saham"], 0.80))

print("3. MMBR")
opsi = h["mmbr"]["opsi_dasar"]
for kode, _, _, bobot in varian:
    t = mm.neraca_pada_target(1.2, bobot, n, neraca, reg, **opsi)
    periksa(f"{kode}: rasio pada target = 120%", dekat(t["rasio"], 1.2, 1e-9))
    periksa(f"{kode}: jumlah modul = MMBR", dekat(sum(t["modul"].values()), t["mmbr"]))
    periksa(f"{kode}: ekuitas = Tingkat Solvabilitas + tidak diakui", dekat(t["ekuitas"], t["tingkat_solvabilitas"] + t["investasi_tidak_diakui"]))
    periksa(f"{kode}: hasil.json cocok dengan hitung ulang", dekat(t["mmbr"], h["mmbr"]["pada_target"][kode]["mmbr"]))
k75 = h["mmbr"]["pada_target"]["K75"]
asuransi_tangan = 0.25 * n["capybmp"] + 0.20 * n["cadangan_klaim"] + 0.25 * n["cadangan_bencana"]
periksa("K75: risiko asuransi cocok dengan hitungan tangan", dekat(k75["modul"]["asuransi"], asuransi_tangan))
periksa("K75: risiko pasar nol", k75["modul"]["pasar"] == 0.0)
kredit_tangan = 0.08 * n["tagihan_premi"] + 0.021 * 0.25 * k75["investasi"]
periksa("K75: risiko kredit cocok dengan hitungan tangan", dekat(k75["modul"]["kredit"], kredit_tangan))
periksa("neraca sama: varian acuan kembali ke 120%", dekat(h["mmbr"]["neraca_sama"]["K75"]["rasio"], 1.2, 1e-9))

print("4. Model investasi")
periksa("obligasi pada imbal hasil = kupon berharga nominal", dekat(float(mi.harga_obligasi(0.07, 0.07, 4)), 1.0))
periksa("harga turun bila imbal hasil naik", float(mi.harga_obligasi(0.07, 0.08, 4)) < 1.0)
durasi = (float(mi.harga_obligasi(0.07, 0.0695, 4)) - float(mi.harga_obligasi(0.07, 0.0705, 4))) / 0.001
periksa("durasi obligasi 4 tahun antara 3 dan 4", 3.0 < durasi < 4.0, f"{durasi:.2f}")
for kode, _, _, bobot in varian:
    s = h["profil"][kode]["imbal_hasil"]["bersama"]
    periksa(f"{kode}: urutan persentil benar", s["p0_5"] <= s["p5"] <= s["median"] <= s["p95"] <= s["p99_5"])
    periksa(f"{kode}: TVaR tidak lebih kecil dari VaR", s["tvar_99_5"] >= s["var_99_5"] - 1e-12)
dep = h["instrumen"]["bersama"]["deposito"]
periksa("deposito tidak pernah rugi", dep["peluang_negatif"] == 0.0)
v = h["validasi_bootstrap"]
periksa("simpangan perubahan imbal hasil simulasi dalam 25% dari historis",
        abs(v["dy10_simpangan"]["simulasi"] / v["dy10_simpangan"]["historis"] - 1) < 0.25)
periksa("korelasi imbal hasil dan saham bertanda sama dengan historis",
        v["korelasi_dy10_saham"]["simulasi"] * v["korelasi_dy10_saham"]["historis"] > 0)

print("5. Kaitan dan turunan")
t = h["turunan"]
periksa("bantalan = 20% MMBR varian acuan", dekat(t["bantalan_di_atas_100"], 0.2 * k75["mmbr"]))
periksa("peluang naik bersama tenor SBN",
        h["tenor_sbn"]["2"]["bersama"]["rasio_akhir"]["peluang_di_bawah_100"]
        <= h["tenor_sbn"]["5"]["bersama"]["rasio_akhir"]["peluang_di_bawah_100"]
        <= h["tenor_sbn"]["10"]["bersama"]["rasio_akhir"]["peluang_di_bawah_100"])
periksa("tenor dasar pada tenor_sbn sama dengan hasil profil acuan",
        dekat(h["tenor_sbn"]["5"]["bersama"]["rata"], h["profil"]["K75"]["imbal_hasil"]["bersama"]["rata"]))

print("6. Dokumen")
konteks = yaml.safe_load((DIR_ANALISIS / "KONTEKS_AI.yaml").read_text(encoding="utf-8"))
periksa("KONTEKS_AI.yaml terurai sebagai YAML", isinstance(konteks, dict))
periksa("KONTEKS_AI.yaml memuat sembilan varian", set(konteks["varian"]) == {k for k, *_ in varian})
periksa("KONTEKS_AI.yaml: MMBR K75 sama dengan hasil.json", dekat(konteks["varian"]["K75"]["pada_target_120"]["mmbr"], k75["mmbr"], 1e-3))
laporan = (DIR_ANALISIS / "LAPORAN.md").read_text(encoding="utf-8")
periksa("LAPORAN.md tanpa penanda kosong", "{{" not in laporan)
for g in sorted((DIR_ANALISIS / "keluaran" / "gambar").glob("*.png")):
    periksa(f"gambar {g.name} dirujuk laporan", g.name in laporan)

print(f"\n{len(lulus)} lulus, {len(gagal)} gagal")
sys.exit(1 if gagal else 0)
