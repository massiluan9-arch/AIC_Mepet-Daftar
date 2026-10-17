"""T9: mencocokkan angka tabel utama paper Rev. 1 (08_audit/paper_final.txt, disalin ke skrip ini) dengan
keluaran Rev. 1 (hasil_terpadu.json, rancangan.json, hasil_excel.json, keluaran R) dan antar-keluaran.

Pemakaian: python periksa_paper.py <folder AIC_CASE Rev. 1>
Aturan cocok: selisih tidak melebihi setengah satuan angka terakhir yang dicetak paper.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
A = Path(sys.argv[1]) / "analisis"
h = json.loads((A / "4_simulasi_terpadu/keluaran/hasil_terpadu.json").read_text(encoding="utf-8"))
r = json.loads((A / "5_solusi_motera/keluaran/rancangan.json").read_text(encoding="utf-8"))
x = json.loads((A / "5_solusi_motera/keluaran/hasil_excel.json").read_text(encoding="utf-8"))
T = A / "4_simulasi_terpadu/keluaran/tabel"
B = A / "2_model_bencana/keluaran"
E = h["meta"]["eksposur_per_premi"]
BARIS = []


def cek(tabel, butir, paper, hitung, desimal, sumber):
    cocok = abs(paper - hitung) <= 0.5 * 10 ** (-desimal) * 1.0001 + 1e-12
    BARIS.append({"tabel": tabel, "butir": butir, "paper": paper, "keluaran": round(hitung, desimal + 3), "desimal": desimal, "cocok": cocok, "sumber": sumber})


# ---------- Tabel 3: ukuran risiko polis standar ----------
u4 = pd.read_csv(B / "04_ukuran_risiko.csv")
u4 = u4[u4["strategi"] == "S0_dasar"].set_index("kurva")
u5 = pd.read_csv(B / "05_ukuran_risiko_campuran.csv").set_index("strategi").loc["S0_dasar"]
t3 = {"aulady": (0.78, 0.188, 0.44, 1.82, 2.6, 62, 253), "klaim": (0.18, 0.214, 0.19, 0.32, 3.0, 27, 44), "pager": (0.04, 0.016, 0.04, 0.27, 0.2, 5, 37)}
for kv, p in t3.items():
    b = u4.loc[kv]
    for nama, pv, hv, d in (("bobot", p[0], h["meta"]["bobot_kurva"][kv], 2), ("rata-rata per mil", p[1], 1000 * b["aal"], 3), ("VaR %", p[2], 100 * b["var_99_5"], 2),
                            ("TVaR %", p[3], 100 * b["tvar_99_5"], 2), ("rata per 100 premi", p[4], 100 * E * b["aal"], 1), ("VaR per 100 premi", p[5], 100 * E * b["var_99_5"], 0),
                            ("TVaR per 100 premi", p[6], 100 * E * b["tvar_99_5"], 0)):
        cek("Tabel 3", f"{kv}: {nama}", pv, hv, d, "04_ukuran_risiko.csv")
for nama, pv, hv, d in (("rata-rata per mil", 0.186, 1000 * u5["aal"], 3), ("VaR %", 0.38, 100 * u5["var_99_5"], 2), ("TVaR %", 1.51, 100 * u5["tvar_99_5"], 2),
                        ("rata per 100 premi", 2.6, 100 * E * u5["aal"], 1), ("VaR per 100 premi", 53, 100 * E * u5["var_99_5"], 0), ("TVaR per 100 premi", 210, 100 * E * u5["tvar_99_5"], 0),
                        ("galat baku VaR %", 0.015, 100 * u5["galat_baku_var_99_5"], 3)):
    cek("Tabel 3", f"campuran: {nama}", pv, hv, d, "05_ukuran_risiko_campuran.csv")

# ---------- Tabel 4: sembilan varian profil ----------
t4 = {"K80": (22.7, 6.48, 121, 0.70, 101), "K75": (22.8, 6.39, 120, 0.70, 101), "K70": (22.9, 6.30, 119, 0.71, 101), "M40": (25.3, 6.98, 108, 0.75, 55),
      "M50": (25.7, 7.04, 107, 0.76, 46), "M60": (36.8, 7.11, 63, 1.30, 40), "A20": (72.9, 7.13, -24, 50.73, 7), "A30": (56.8, 6.94, 17, 13.64, 7), "A40": (59.4, 6.75, 16, 19.87, 7)}
s1 = h["soal1"]["varian"]
csv1 = pd.read_csv(T / "t1_profil.csv").set_index("varian")
for kode, p in t4.items():
    a, e = s1[kode]["target_120"]["S0_dasar"], s1[kode]["ekuitas_sama"]["S0_dasar"]
    for nama, pv, hv, d in (("ekuitas untuk 120%", p[0], a["ekuitas"], 1), ("imbal hasil %", p[1], 100 * a["imbal_hasil_rata"], 2), ("rasio awal ekuitas sama %", p[2], 100 * e["target"], 0),
                            ("P ekuitas sama %", p[3], 100 * e["peluang_di_bawah_100"], 2), ("aset siap cair", p[4], a["aset_siap_cair"], 0)):
        cek("Tabel 4", f"{kode}: {nama}", pv, hv, d, "hasil_terpadu.json soal1")
    assert abs(csv1.loc[kode, "ekuitas_pada_120"] - a["ekuitas"]) < 1e-9 and abs(csv1.loc[kode, "peluang_S0_ekuitas_sama"] - e["peluang_di_bawah_100"]) < 1e-12

# ---------- Tabel 5: modul ----------
t5 = {"asuransi": (16.31, 85.9, 0.6, 23.1, 99.9), "pasar": (0.00, 0.0, 7.8, 4.1, 0.1), "operasional": (0.36, 1.9, 32.4, 2.1, 0.0),
      "likuiditas": (0.49, 2.6, 0.0, 0.2, 0.0), "kredit": (1.83, 9.6, 0.0, 0.0, 0.0)}
m = h["soal3"]["K75_S0_dasar"]["modul"]
for modul, p in t5.items():
    b = m[modul]
    for nama, pv, hv, d in (("beban modal", p[0], b["beban_modal"], 2), ("porsi MMBR %", p[1], 100 * b["porsi_mmbr"], 1), ("P melampaui beban %", p[2], 100 * b["peluang_melampaui_beban"], 1),
                            ("rugi 1/200", p[3], b["rugi_var_99_5"], 1), ("porsi tahun pelanggaran %", p[4], 100 * b["porsi_tahun_gagal_dipicu"], 1)):
        cek("Tabel 5", f"{modul}: {nama}", pv, hv, d, "hasil_terpadu.json soal3")

# ---------- Tabel 6: strategi ----------
t6 = {"S0_dasar": (0.0, 53, 210, 0.70, 190, 235), "S2_rs10": (0.0, 36, 165, 0.46, 110, 150), "S11_batas30": (4.1, 36, 124, 0.53, 130, 160), "S12_batas25": (4.7, 33, 109, 0.48, 120, 140),
      "S3_batas20": (5.6, 28, 92, 0.42, 105, 120), "S4_batas10": (7.5, 16, 48, 0.23, 100, 100), "S5_akumulasi10": (3.8, 45, 161, 0.66, 170, 210), "S19_akum5": (8.5, 35, 106, 0.61, 150, 185),
      "S20_zona_batas20": (3.8, 44, 115, 0.65, 160, 200), "S21_zona_batas10": (5.0, 34, 81, 0.53, 130, 160)}
s2, s4 = h["soal2"], h["soal4"]
for st, p in t6.items():
    b = s2[st]
    for nama, pv, hv, d in (("premi dilepas", p[0], b["premi_dilepas"], 1), ("VaR", p[1], b["L_var_99_5"], 0), ("TVaR", p[2], b["L_tvar_99_5"], 0), ("P pada 120% %", p[3], 100 * b["peluang_di_bawah_100"], 2),
                            ("rasio terkecil campuran %", p[4], 100 * s4["target_minimum"]["K75"][st], 0), ("rasio terkecil Aulady %", p[5], 100 * s4["target_minimum_per_kurva"]["aulady"][st], 0)):
        cek("Tabel 6", f"{st}: {nama}", pv, hv, d, "hasil_terpadu.json soal2/soal4")
    c = r["calon"][st]
    assert abs(c["target_C1"] - s4["target_minimum"]["K75"][st]) < 1e-9 and abs(c["target_C2"] - s4["target_minimum_per_kurva"]["aulady"][st]) < 1e-9, st

# ---------- Tabel 7: tiga jalan ----------
t7 = {"sekarang": (120, 22.8, 19.0, 25.9, 210, 0.70, 0.83, -123, 0.76, 22.14), "modal_saja": (330, 63.3, 19.2, 27.9, 210, 0.29, 0.35, 103, 0.63, 19.02),
      "terpilih": (160, 30.4, 19.0, 23.7, 81, 0.41, 0.49, 145, 0.14, 19.59)}
for jalan, p in t7.items():
    b = r["perbandingan"][jalan]
    for nama, pv, hv, d in (("rasio awal %", p[0], 100 * b["target"], 0), ("ekuitas", p[1], b["ekuitas"], 1), ("MMBR", p[2], b["mmbr"], 1), ("laba bersih", p[3], b["laba_bersih_rata"], 1),
                            ("TVaR", p[4], b["L_tvar_99_5"], 0), ("P campuran %", p[5], 100 * b["peluang_di_bawah_100"], 2), ("P Aulady %", p[6], 100 * b["peluang_aulady"], 2),
                            ("rasio megathrust %", p[7], 100 * b["rasio_setelah_megathrust"], 0), ("defisit", p[8], b["defisit_harapan"], 2), ("nilai bersih", p[9], b["nilai_bersih"], 2)):
        cek("Tabel 7", f"{jalan}: {nama}", pv, hv, d, "rancangan.json perbandingan")
cek("Bab 4", "klaim satu kejadian 1/200 solusi", 33.6, r["perbandingan"]["terpilih"]["klaim_kejadian_var_99_5"], 1, "rancangan.json")
cek("Bab 4", "cakupan K70 %", 112, 100 * r["terpilih"]["kantong_likuiditas"]["K70"]["cakupan"], 0, "rancangan.json")
cek("Bab 4", "cakupan K75 %", 97, 100 * r["terpilih"]["kantong_likuiditas"]["K75"]["cakupan"], 0, "rancangan.json")
cek("Bab 4", "kerugian megathrust sekarang", 82, r["perbandingan"]["sekarang"]["kerugian_megathrust"], 0, "rancangan.json")
cek("Bab 4", "kerugian megathrust solusi", 35, r["perbandingan"]["terpilih"]["kerugian_megathrust"], 0, "rancangan.json")

# ---------- Tabel 9: biaya-manfaat ----------
for nama, pv, hv, d in (("ekuitas tidak disetor", 329, x["ekuitas_dihemat_miliar"], 0), ("laba dilepas", 42.1, x["laba_dilepas_miliar"], 1), ("defisit dihindari", 4.9, x["defisit_dihindari_miliar"], 1),
                        ("biaya awal", 6.0, x["biaya_awal_miliar"], 1), ("biaya tahunan", 2.8, x["biaya_tahunan_miliar"], 1), ("NPV", 4.0, x["npv_miliar"], 1),
                        ("titik impas %", 12.65, 100 * x["biaya_setara_modal"], 2), ("NPV k 10%", -32.6, x["npv_per_biaya_modal"]["0.1"], 1), ("NPV k 16%", 35.6, x["npv_per_biaya_modal"]["0.16"], 1),
                        ("NPV rasio klaim 29,5%", -15.2, x["npv_per_kasus"]["Rasio klaim non-bencana 29,5%"], 1), ("biaya keamanan", 36.3, x["biaya_keamanan_miliar"], 1),
                        ("biaya keamanan % premi", 3.6, 100 * x["biaya_keamanan_terhadap_premi"], 1)):
    cek("Tabel 9", nama, pv, hv, d, "hasil_excel.json")

# ---------- Tabel 21: kepekaan rancangan ----------
t21 = {"Dasar": (0.70, 0.41, 130), "Kurva Aulady & Fujimi saja": (0.83, 0.49, 160), "Eksposur per premi 188": (1.02, 0.58, 195), "Biaya akuisisi 15% premi": (0.93, 0.50, 160),
       "Simpangan rasio klaim dua kali": (1.38, 0.80, 195), "Separuh klaim bencana masih cadangan": (0.79, 0.46, 145), "Korelasi bencana dan pasar 0,25": (0.78, 0.43, 140),
       "Data pasar 2000-2026": (0.72, 0.40, 125), "SBN tenor 10 tahun": (0.73, 0.41, 135), "Gabungan berat": (1.43, 0.90, 265)}
for b in r["terpilih"]["kepekaan"]:
    p = t21[b["kasus"]]
    cek("Tabel 21", f"{b['kasus']}: sekarang %", p[0], 100 * b["peluang_sekarang"], 2, "rancangan.json kepekaan")
    cek("Tabel 21", f"{b['kasus']}: solusi %", p[1], 100 * b["peluang_terpilih"], 2, "rancangan.json kepekaan")
    cek("Tabel 21", f"{b['kasus']}: rasio terkecil %", p[2], 100 * b["target_minimum_terpilih"], 0, "rancangan.json kepekaan")

# ---------- Tabel 22: skenario ----------
t22 = {("Gempa dangkal dekat Timika M 7,5", 0): (11, 223, 5, 272), ("Gempa dangkal dekat Timika M 7,5", 1): (46, 69, 18, 215),
       ("Megathrust Jawa bagian barat M 8,7", 0): (82, -123, 35, 145), ("Megathrust Jawa bagian barat M 8,7", 1): (340, -1485, 127, -345),
       ("Megathrust Mentawai M 8,9", 0): (9, 231, 9, 254), ("Megathrust Mentawai M 8,9", 1): (44, 78, 43, 101),
       ("Sesar Lembang M 6,8", 0): (27, 157, 11, 246), ("Sesar Lembang M 6,8", 1): (181, -647, 53, 50),
       ("Sesar Surabaya M 6,5", 0): (18, 193, 18, 216), ("Sesar Surabaya M 6,5", 1): (119, -319, 119, -300)}
sk = {(b["skenario"], b["eta"], b["strategi"]): b for b in r["terpilih"]["skenario"]}
for (nama, eta), p in t22.items():
    a, s = sk[(nama, eta, "S0_dasar")], sk[(nama, eta, r["terpilih"]["strategi"])]
    for butir, pv, hv in (("kerugian sekarang", p[0], a["kerugian"]), ("rasio sekarang %", p[1], 100 * a["rasio_akhir"]), ("kerugian solusi", p[2], s["kerugian"]), ("rasio solusi %", p[3], 100 * s["rasio_akhir"])):
        cek("Tabel 22", f"{nama}, eta {eta}: {butir}", pv, hv, 0, "rancangan.json skenario")

# ---------- antar-keluaran ----------
antar = []
c2 = pd.read_csv(T / "t2_strategi.csv").set_index("strategi")
antar.append(("t2_strategi.csv lawan hasil_terpadu.json (peluang pada 120%)", max(abs(c2.loc[st, "peluang_pada_120"] - v["peluang_di_bawah_100"]) for st, v in s2.items())))
antar.append(("rancangan.json pada_120 lawan hasil_terpadu.json soal2 (peluang)", max(abs(r["calon"][st]["pada_120"]["peluang_di_bawah_100"] - v["peluang_di_bawah_100"]) for st, v in s2.items())))
antar.append(("rancangan.json pada_120 lawan hasil_terpadu.json soal2 (TVaR)", max(abs(r["calon"][st]["pada_120"]["L_tvar_99_5"] - v["L_tvar_99_5"]) for st, v in s2.items())))
cs = pd.read_csv(A / "5_solusi_motera/keluaran/calon_strategi.csv").set_index("strategi")
antar.append(("calon_strategi.csv lawan rancangan.json (target_perlu)", max(abs((cs.loc[st, "target_perlu"] if pd.notna(cs.loc[st, "target_perlu"]) else -1) - (v["target_perlu"] or -1)) for st, v in r["calon"].items())))
p = r["perbandingan"]
antar.append(("hasil_excel.json ekuitas dihemat lawan rancangan.json", abs(x["ekuitas_dihemat_miliar"] - 10 * (p["modal_saja"]["ekuitas"] - p["terpilih"]["ekuitas"]))))
c3 = pd.read_csv(T / "t3_modul.csv")
antar.append(("t3_modul.csv lawan hasil_terpadu.json soal3 (peluang rugi)", max(abs(b["peluang_rugi"] - h["soal3"][b["konfigurasi"]]["modul"][b["modul"]]["peluang_rugi"]) for _, b in c3.iterrows())))

t = pd.DataFrame(BARIS)
keluar = Path(__file__).resolve().parents[1] / "hasil" / "umum"
keluar.mkdir(parents=True, exist_ok=True)
t.to_csv(keluar / "t9_cocok_paper.csv", index=False)
print(t.groupby("tabel")["cocok"].agg(jumlah="size", cocok="sum").assign(tidak_cocok=lambda d: d["jumlah"] - d["cocok"]).to_string())
print(f"\nJumlah butir {len(t)}; cocok {int(t['cocok'].sum())}; tidak cocok {int((~t['cocok']).sum())}")
if (~t["cocok"]).any():
    pd.set_option("display.width", 220)
    print(t[~t["cocok"]].to_string(index=False))
print("\nKecocokan antar-keluaran (selisih mutlak terbesar):")
for nama, s in antar:
    print(f"  {s:.3e}  {nama}")
