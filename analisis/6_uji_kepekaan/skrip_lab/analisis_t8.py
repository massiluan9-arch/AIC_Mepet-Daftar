"""T8: soal 1 (perbandingan profil setelah perubahan) dan soal 2 (kepekaan terhadap bahaya yang tidak dimodelkan).

Pemakaian: python analisis_t8.py <varian>
Keluaran: laporan/hasil/<varian>/t8_profil.csv, t8_skala_bencana.csv, t8.json
"""
import json
import sys

import numpy as np
import pandas as pd

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")


def main():
    varian = sys.argv[1]
    ctx = al.siapkan(varian)
    ms, M, pt, ps, r, acuan = ctx["ms"], ctx["M"], ctx["pt"], ctx["ps"], ctx["rancangan"], ctx["acuan"]
    ambang = pt["meta"]["ambang_peluang"]
    bawah = ps["kendala"]["target_paling_rendah"]
    kisi = al.kisi_target(pt)
    st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")
    rugi_sken["campuran"] = sum(bobot_kurva[k] * rugi_sken[k] for k in ms.KURVA_TUNGGAL)

    # ---------- soal 1: sembilan varian profil ----------
    h = json.loads((ms.DIR_KELUAR / "hasil_terpadu.json").read_text(encoding="utf-8"))
    inv_acuan = h["soal1"]["investasi_acuan"]
    rt = M.jalankan(acuan, st_p, s_p)
    klaim_1_200_solusi = rt["klaim_kejadian_var_99_5"]
    klaim_1_200_standar = M.jalankan(acuan, "S0_dasar", 1.2)["klaim_kejadian_var_99_5"]
    baris = []
    for kode, v in h["soal1"]["varian"].items():
        t, e = v["target_120"]["S0_dasar"], v["ekuitas_sama"]["S0_dasar"]
        bobot = M.varian[kode][2]
        b_sol = M.neraca_awal(kode, s_p)
        b_120 = M.neraca_awal(kode, 1.2)
        kas = M.nilai["kas_dan_bank"]
        x_sol = M.jalankan(kode, st_p, s_p)
        baris.append({
            "varian": varian, "kode": kode, "profil": v["profil"], "label": v["label"], "patuh_ayd": v["patuh_ayd"],
            "porsi_tidak_diakui": v["porsi_tidak_diakui"], "ketentuan_dilampaui": v["ketentuan_dilampaui"],
            "ekuitas_pada_120": t["ekuitas"], "imbal_hasil_rata": t["imbal_hasil_rata"], "imbal_hasil_riil": t["imbal_hasil_riil"],
            "peluang_standar_pada_120": t["peluang_di_bawah_100"],
            "rasio_awal_ekuitas_sama": e["target"], "peluang_standar_ekuitas_sama": e["peluang_di_bawah_100"],
            "aset_siap_cair_pada_120": t["aset_siap_cair"],
            "kas_dan_deposito_pada_120": kas + b_120["investasi"] * bobot.get("deposito", 0.0),
            "cakupan_kas_deposito_klaim_1_200_standar": (kas + b_120["investasi"] * bobot.get("deposito", 0.0)) / klaim_1_200_standar,
            "peluang_klaim_kejadian_melebihi_siap_cair_pada_120": t["peluang_kurang_likuiditas"],
            "target_minimum_standar": v["target_minimum"]["S0_dasar"],
            "ekuitas_pada_solusi": b_sol["ekuitas"], "peluang_solusi": x_sol["peluang_di_bawah_100"],
            "kas_dan_deposito_pada_solusi": kas + b_sol["investasi"] * bobot.get("deposito", 0.0),
            "cakupan_kas_deposito_klaim_1_200_solusi": (kas + b_sol["investasi"] * bobot.get("deposito", 0.0)) / klaim_1_200_solusi,
            "biaya_jual_paksa_var_99_5_solusi": x_sol["F_var_99_5"], "laba_bersih_solusi": x_sol["laba_bersih_rata"]})
    profil = pd.DataFrame(baris)
    profil.to_csv(ctx["keluar"] / "t8_profil.csv", index=False)

    # ---------- soal 2: kerugian bencana dikalikan faktor (erupsi, bahaya sekunder) ----------
    def skala_ylt(kurva, f):
        return {st: (j * f, m * f) for st, (j, m) in M.ylt_untuk(kurva).items()}

    def target_c3(st, f):
        for s in kisi:
            if M.rasio_skenario(acuan, st, float(s), rugi_sken.loc[st, "campuran"] * f)["rasio_akhir"] >= 1.0:
                return float(s)
        return None

    baris = []
    for f in (1.0, 1.07, 1.25, 1.5):
        y_c, y_a = skala_ylt("campuran", f), skala_ylt("aulady", f)
        for nama, st, s in (("polis_standar_120", "S0_dasar", 1.2), ("solusi_terpilih", st_p, s_p)):
            x = M.jalankan(acuan, st, s, ylt=y_c)
            xa = M.jalankan(acuan, st, s, ylt=y_a)
            c1 = M.target_minimum(acuan, st, ylt=y_c)
            c2 = M.target_minimum(acuan, st, ylt=y_a)
            c3 = target_c3(st, f)
            baris.append({"varian": varian, "faktor_kerugian_bencana": f, "konfigurasi": nama, "strategi": st, "target": s,
                          "peluang_campuran": x["peluang_di_bawah_100"], "peluang_aulady": xa["peluang_di_bawah_100"],
                          "rasio_setelah_megathrust": M.rasio_skenario(acuan, st, s, rugi_sken.loc[st, "campuran"] * f)["rasio_akhir"],
                          "L_rata": x["L_rata"], "L_var_99_5": x["L_var_99_5"], "L_tvar_99_5": x["L_tvar_99_5"], "defisit_harapan": x["defisit_harapan"],
                          "klaim_kejadian_var_99_5": x["klaim_kejadian_var_99_5"],
                          "target_C1": c1, "target_C2": c2, "target_C3": c3,
                          "target_perlu": None if None in (c1, c2, c3) else max(bawah, c1, c2, c3),
                          "lolos_tiga_kendala_pada_target": bool(x["peluang_di_bawah_100"] <= ambang and xa["peluang_di_bawah_100"] <= ambang
                                                                 and M.rasio_skenario(acuan, st, s, rugi_sken.loc[st, "campuran"] * f)["rasio_akhir"] >= 1.0)})
    skala = pd.DataFrame(baris)
    skala.to_csv(ctx["keluar"] / "t8_skala_bencana.csv", index=False)

    al.simpan_json(ctx["keluar"] / "t8.json", {"varian": varian, "profil_acuan": acuan, "investasi_acuan": inv_acuan, "strategi": st_p, "target": s_p,
                                               "klaim_kejadian_1_200_standar": klaim_1_200_standar, "klaim_kejadian_1_200_solusi": klaim_1_200_solusi})
    pd.set_option("display.width", 260)
    print(f"[{varian}] profil acuan {acuan}; solusi {st_p} pada {s_p}; klaim satu kejadian 1/200: standar {klaim_1_200_standar:.2f}, solusi {klaim_1_200_solusi:.2f}")
    print(profil[["kode", "patuh_ayd", "ekuitas_pada_120", "imbal_hasil_rata", "imbal_hasil_riil", "peluang_standar_pada_120", "rasio_awal_ekuitas_sama",
                  "peluang_standar_ekuitas_sama", "aset_siap_cair_pada_120", "cakupan_kas_deposito_klaim_1_200_standar", "ekuitas_pada_solusi",
                  "peluang_solusi", "cakupan_kas_deposito_klaim_1_200_solusi"]].round(4).to_string(index=False))
    print(skala[["faktor_kerugian_bencana", "konfigurasi", "target", "peluang_campuran", "peluang_aulady", "rasio_setelah_megathrust", "L_tvar_99_5",
                 "target_C1", "target_C2", "target_C3", "target_perlu", "lolos_tiga_kendala_pada_target"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
