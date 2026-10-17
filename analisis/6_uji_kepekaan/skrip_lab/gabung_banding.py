"""Menggabungkan hasil tiap varian menjadi CSV pembanding di laporan/banding/.

Pemakaian: python gabung_banding.py <varian> [<varian> ...]
Hanya membaca berkas hasil yang sudah ditulis skrip analisis; tidak menghitung ulang.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
LAB = Path(__file__).resolve().parents[2]
HASIL = LAB / "laporan" / "hasil"
KELUAR = LAB / "laporan" / "banding"
varian = sys.argv[1:]
if varian and varian[0].startswith("--keluar="):          # subfolder lain, misalnya untuk uji kepekaan
    KELUAR = LAB / "laporan" / varian[0].split("=", 1)[1]
    varian = varian[1:]
KELUAR.mkdir(parents=True, exist_ok=True)


def muat(v, nama):
    p = HASIL / v / nama
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


ringkas, strategi, modul, peka, sken, batas_atas, tujuan = [], [], [], [], [], [], []
for v in varian:
    h = muat(v, "t3_t4.json")
    if h is None:
        print("lewati (belum ada t3_t4.json):", v)
        continue
    t, s21, a = h["terpilih"], h["S21_pada_160"], h["aturan_batas_atas"]
    b = {"varian": v, "profil_acuan": h["profil_acuan"], "strategi_terpilih": t["strategi"], "keterangan": t["keterangan"], "target": t["target"],
         "C1_pelanggaran": t["C1"]["jumlah_pelanggaran"], "C1_peluang": t["C1"]["peluang"], "C1_selang95_bawah": t["C1"]["selang95_bawah"], "C1_selang95_atas": t["C1"]["selang95_atas"],
         "C2_pelanggaran": t["C2"]["jumlah_pelanggaran"], "C2_peluang": t["C2"]["peluang"], "C2_selang95_bawah": t["C2"]["selang95_bawah"], "C2_selang95_atas": t["C2"]["selang95_atas"],
         "C3_rasio_setelah_megathrust": t["C3_rasio_setelah_megathrust"], "target_C1": t["target_C1"], "target_C2": t["target_C2"], "target_C3": t["target_C3"],
         "ekuitas": t["ekuitas"], "mmbr": t["mmbr"], "laba_bersih": t["laba_bersih"], "premi_dilepas": t["premi_dilepas"], "L_rata": t["L_rata"], "L_var_99_5": t["L_var_99_5"],
         "L_tvar_99_5": t["L_tvar_99_5"], "defisit_harapan": t["defisit_harapan"], "nilai_bersih": t["nilai_bersih"], "klaim_kejadian_1_200": t["klaim_kejadian_var_99_5"],
         "kerugian_megathrust": t["kerugian_megathrust"],
         "cakupan_K80": t["kantong_likuiditas"]["K80"]["cakupan"], "cakupan_K75": t["kantong_likuiditas"]["K75"]["cakupan"], "cakupan_K70": t["kantong_likuiditas"]["K70"]["cakupan"],
         "C1_berstrata": h["kestabilan_terpilih"]["C1_berstrata"]["peluang"],
         "target_aturan_batas_atas_strategi_terpilih": a["strategi_terpilih_titik"]["target_batas_atas"],
         "terpilih_aturan_batas_atas": a["terpilih"]["strategi"], "target_terpilih_aturan_batas_atas": a["terpilih"]["target"],
         "S21_160_C1": s21["C1"]["peluang"], "S21_160_C2": s21["C2"]["peluang"], "S21_160_C3_rasio": s21["C3_rasio_setelah_megathrust"],
         "S21_160_lolos_tiga_kendala": bool(s21["lolos_C1"] and s21["lolos_C2"] and s21["lolos_C3"]), "S21_target_perlu": s21["target_perlu"],
         "sekarang_peluang_campuran_120": h["sekarang"]["peluang_di_bawah_100"], "sekarang_peluang_aulady_120": h["sekarang"]["peluang_aulady"],
         "sekarang_rasio_megathrust_120": h["sekarang"]["rasio_setelah_megathrust"]}
    if "modal_saja" in h:
        b.update({"modal_saja_target": h["modal_saja"]["target"], "modal_saja_ekuitas": h["modal_saja"]["ekuitas"], "modal_saja_nilai_bersih": h["modal_saja"]["nilai_bersih"]})
    c = muat(v, "t6_cba.json")
    if c and "npv" in c:
        n, i, g = c["npv"], c["titik_impas_biaya_modal"], c["kerugian_berpindah_ke_pemegang_polis"]
        b.update({"npv_diperluas": n["b_diperluas_dengan_defisit (buku kerja)"], "npv_perusahaan": n["a_perspektif_perusahaan_tanpa_defisit"],
                  "npv_biaya_x2_diperluas": n["c_biaya_x2_diperluas"], "npv_biaya_x2_perusahaan": n["c_biaya_x2_perusahaan"],
                  "impas_diperluas": i["d_diperluas"], "impas_perusahaan": i["d_perusahaan"],
                  "ekuitas_dihemat_miliar": c["masukan"]["ekuitas_dihemat_miliar"], "laba_dilepas_miliar": c["masukan"]["laba_dilepas_miliar"],
                  "defisit_dihindari_miliar": c["masukan"]["defisit_dihindari_miliar"],
                  "kerugian_berpindah_rata": g["rata_per_tahun"], "kerugian_berpindah_ekor_0_5": g["rata_pada_0_5persen_tahun_terburuk"],
                  "porsi_kerugian_ekor_berpindah": g["porsi_kerugian_ekor_yang_berpindah"]})
    p = muat(v, "pilihan.json")
    if p:
        k = p["kantong_likuiditas"]
        b.update({"klaim_kejadian_selang95_bawah": k["selang95_kuantil"][0], "klaim_kejadian_selang95_atas": k["selang95_kuantil"][1],
                  "cakupan_K70_selang95_bawah": k["per_profil"]["K70"]["cakupan_selang95"][0], "cakupan_K70_selang95_atas": k["per_profil"]["K70"]["cakupan_selang95"][1],
                  "peluang_klaim_kejadian_melebihi_kas_deposito_K70": k["per_profil"]["K70"]["peluang_klaim_kejadian_melebihi_kas_deposito"]})
        if "biaya_modal_impas_fungsi_tujuan" in p:
            b.update({f"impas_fungsi_tujuan_{kk}": vv for kk, vv in p["biaya_modal_impas_fungsi_tujuan"].items()})
    ringkas.append(b)
    for nama, daftar in (("t3_strategi.csv", strategi), ("t4_aturan_batas_atas.csv", batas_atas), ("pilihan_fungsi_tujuan.csv", tujuan)):
        if (HASIL / v / nama).exists():
            daftar.append(pd.read_csv(HASIL / v / nama))
    if (HASIL / v / "t7_modul.csv").exists():
        modul.append(pd.read_csv(HASIL / v / "t7_modul.csv"))
    for x in t["kepekaan"]:
        peka.append({"varian": v, "strategi": t["strategi"], "target": t["target"], **x})
    for x in t["skenario"]:
        sken.append({"varian": v, **x})

pd.DataFrame(ringkas).to_csv(KELUAR / "banding_solusi_terpilih.csv", index=False)
pd.DataFrame(ringkas).set_index("varian").T.to_csv(KELUAR / "banding_solusi_terpilih_melintang.csv")
if strategi:
    s = pd.concat(strategi)
    s.to_csv(KELUAR / "banding_strategi_panjang.csv", index=False)
    lebar = s.pivot(index=["strategi", "keterangan"], columns="varian", values=["aal", "var_99_5", "tvar_99_5", "premi_dilepas", "peluang_campuran_pada_120", "target_C1", "target_C2",
                                                                             "target_C3", "target_perlu", "ekuitas_pada_target", "nilai_bersih", "peringkat_nilai_bersih"])
    lebar.columns = [f"{a}__{b}" for a, b in lebar.columns]
    lebar.reset_index().to_csv(KELUAR / "banding_strategi_lebar.csv", index=False)
for daftar, nama in ((modul, "banding_modul_soal3.csv"), (batas_atas, "banding_aturan_batas_atas.csv"), (tujuan, "banding_fungsi_tujuan.csv")):
    if daftar:
        pd.concat(daftar).to_csv(KELUAR / nama, index=False)
pd.DataFrame(peka).to_csv(KELUAR / "banding_kepekaan_terpilih.csv", index=False)
pd.DataFrame(sken).to_csv(KELUAR / "banding_skenario_terpilih.csv", index=False)
for nama in ("t8_profil.csv", "t8_skala_bencana.csv", "t5_c1.csv"):
    ada = [pd.read_csv(HASIL / v / nama) for v in varian if (HASIL / v / nama).exists()]
    if ada:
        pd.concat(ada).to_csv(KELUAR / f"banding_{nama}", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 100)
print(pd.DataFrame(ringkas).set_index("varian").T.to_string(float_format=lambda x: f"{x:.4f}"))
print("\nberkas ditulis di", KELUAR)
print("\n".join(sorted(p.name for p in KELUAR.glob("*.csv"))))
