"""Ketahanan pilihan pengoptimal, uji F08 (porsi premi gempa), dan selang kantong likuiditas.

Pemakaian: python analisis_pilihan.py <varian>
Keluaran: laporan/hasil/<varian>/pilihan.json, pilihan_fungsi_tujuan.csv, pilihan_f08.csv
"""
import copy
import json
import sys

import numpy as np
import pandas as pd

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")


def main():
    varian = sys.argv[1]
    ctx = al.siapkan(varian)
    ms, M, p05, pt, ps, r, acuan = ctx["ms"], ctx["M"], ctx["p05"], ctx["pt"], ctx["ps"], ctx["rancangan"], ctx["acuan"]
    n = M.n
    k0, horizon = ps["biaya_modal"]["nilai"], ps["horizon_tahun"]
    skala = ps["skala_rupiah"]["premi_harta_benda_miliar"] / 100.0
    awal = sum(v["nilai"] for v in ps["biaya_implementasi"]["awal"].values())
    tahunan = sum(v["nilai"] for v in ps["biaya_implementasi"]["tahunan"].values())
    st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
    hasil = {"varian": varian, "profil_acuan": acuan, "terpilih_dasar": {"strategi": st_p, "target": s_p}}

    # ---------- 1. fungsi tujuan alternatif pada target yang diperlukan (dari rancangan.json) ----------
    calon = {st: v for st, v in r["calon"].items() if v["target_perlu"] is not None and not v["dikecualikan"]}

    def anuitas(k):
        return awal * k / (1 - (1 + k) ** -horizon)

    def nilai(st, k, pakai_defisit, kali_biaya):
        d = calon[st]["pada_target_perlu"]
        biaya = 0.0 if st == "S0_dasar" else kali_biaya * (tahunan + anuitas(k)) / skala
        return d["laba_bersih_rata"] - k * d["ekuitas"] - pakai_defisit * d["defisit_harapan"] - biaya

    kasus = [("dasar (k 13%, defisit ikut, tanpa biaya pelaksanaan)", k0, 1, 0.0), ("biaya modal 8%", 0.08, 1, 0.0), ("biaya modal 10%", 0.10, 1, 0.0),
             ("biaya modal 16%", 0.16, 1, 0.0), ("tanpa suku defisit", k0, 0, 0.0), ("dengan biaya pelaksanaan", k0, 1, 1.0),
             ("dengan biaya pelaksanaan x2", k0, 1, 2.0), ("tanpa suku defisit, dengan biaya pelaksanaan", k0, 0, 1.0),
             ("biaya modal 16%, dengan biaya pelaksanaan", 0.16, 1, 1.0), ("biaya modal 10%, dengan biaya pelaksanaan", 0.10, 1, 1.0)]
    baris = []
    for nama, k, pd_, kb in kasus:
        nb = {st: nilai(st, k, pd_, kb) for st in calon}
        urut = sorted(nb, key=lambda s: -nb[s])
        baris.append({"varian": varian, "fungsi_tujuan": nama, "biaya_modal": k, "suku_defisit": pd_, "pengali_biaya_pelaksanaan": kb,
                      "biaya_pelaksanaan_per_100_premi": kb * (tahunan + anuitas(k)) / skala,
                      "terpilih": urut[0], "target_terpilih": calon[urut[0]]["target_perlu"], "nilai_terpilih": nb[urut[0]],
                      "kedua": urut[1], "nilai_kedua": nb[urut[1]], "ketiga": urut[2], "nilai_ketiga": nb[urut[2]],
                      "nilai_modal_saja_S0": nb.get("S0_dasar"), "nilai_strategi_terpilih_dasar": nb.get(st_p),
                      "selisih_terpilih_dasar_terhadap_modal_saja": (nb[st_p] - nb["S0_dasar"]) if "S0_dasar" in nb and st_p in nb else None})
    tujuan = pd.DataFrame(baris)
    tujuan.to_csv(ctx["keluar"] / "pilihan_fungsi_tujuan.csv", index=False)
    # biaya modal impas antara strategi terpilih dan modal saja pada fungsi tujuan dasar
    if "S0_dasar" in calon and st_p != "S0_dasar":
        a, b = calon[st_p]["pada_target_perlu"], calon["S0_dasar"]["pada_target_perlu"]
        dl, de, dd = b["laba_bersih_rata"] - a["laba_bersih_rata"], b["ekuitas"] - a["ekuitas"], b["defisit_harapan"] - a["defisit_harapan"]
        hasil["biaya_modal_impas_fungsi_tujuan"] = {"dengan_defisit": (dl - dd) / de, "tanpa_defisit": dl / de,
                                                    "dengan_defisit_dan_biaya_pelaksanaan_pada_k13": (dl - dd + (tahunan + anuitas(k0)) / skala) / de}

    # ---------- 2. F08: porsi premi gempa 22,83% (premi UY 2024 dibagi premi harta benda 2024) ----------
    bi = json.loads((ms.DIR_DATA / "besaran_industri.json").read_text(encoding="utf-8"))
    tarif_asal = pt["bencana"]["tarif_gempa_per_mil"]["nilai"]
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    porsi_sumber = bi["premi_gempa_uy_miliar"]["2024"] / bi["premi_harta_benda_langsung_2024_miliar"]
    porsi_model = E * tarif_asal / 1000.0
    jembatan = {"porsi_model": porsi_model, "porsi_sumber_uy2024": porsi_sumber,
                "faktor_dasar_eksposur (UY 2024 / berjalan 2024)": bi["eksposur_uy_triliun"]["2024"] / bi["eksposur_berjalan_2024_rata_triliun"],
                "tarif_uy2024_per_mil": bi["premi_gempa_uy_miliar"]["2024"] / bi["eksposur_uy_triliun"]["2024"],
                "faktor_tarif (UY 2024 / rata-rata 2020-2024)": bi["premi_gempa_uy_miliar"]["2024"] / bi["eksposur_uy_triliun"]["2024"] / tarif_asal}
    jembatan["porsi_model_x_dua_faktor"] = porsi_model * jembatan["faktor_dasar_eksposur (UY 2024 / berjalan 2024)"] * jembatan["faktor_tarif (UY 2024 / rata-rata 2020-2024)"]
    hasil["F08_jembatan_porsi_premi_gempa"] = jembatan

    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")
    rugi_sken["campuran"] = sum(bobot_kurva[kv] * rugi_sken[kv] for kv in ms.KURVA_TUNGGAL)
    kisi = al.kisi_target(pt)
    bawah = ps["kendala"]["target_paling_rendah"]

    def optimasi(mesin, label, eksposur=None):
        out = []
        opsi = {} if eksposur is None else {"eksposur": eksposur}
        for st in mesin.strategi.index:
            if ps["dikecualikan"].get(st):
                continue
            c1 = mesin.target_minimum(acuan, st, **opsi)
            c2 = mesin.target_minimum(acuan, st, kurva="aulady", **opsi)
            c3 = next((float(s) for s in kisi if mesin.rasio_skenario(acuan, st, float(s), rugi_sken.loc[st, "campuran"], **opsi)["rasio_akhir"] >= 1.0), None)
            if None in (c1, c2, c3):
                continue
            s = max(bawah, c1, c2, c3)
            x = mesin.jalankan(acuan, st, s, **opsi)
            out.append({"varian": varian, "kasus": label, "strategi": st, "target_C1": c1, "target_C2": c2, "target_C3": c3, "target_perlu": s,
                        "ekuitas": x["ekuitas"], "premi_dilepas": x["premi_dilepas"], "laba_bersih": x["laba_bersih_rata"], "defisit": x["defisit_harapan"],
                        "nilai_bersih": x["laba_bersih_rata"] - k0 * x["ekuitas"] - x["defisit_harapan"]})
        return pd.DataFrame(out).sort_values("nilai_bersih", ascending=False)

    pt2 = copy.deepcopy(pt)
    pt2["bencana"]["tarif_gempa_per_mil"]["nilai"] = tarif_asal * porsi_sumber / porsi_model
    M2 = ms.Mesin(p05, pt2)
    f08_a = optimasi(M2, "tarif disetarakan: premi gempa 22,83 per 100 premi, E tetap 139,16")
    # Pilihan lain yang konsisten: dasar eksposur UY 2024 untuk kerugian dan premi sekaligus (E = eksposur UY 2024 / premi)
    E_uy = bi["eksposur_uy_triliun"]["2024"] * 1000 / bi["premi_harta_benda_langsung_2024_miliar"]
    f08_b = optimasi(M, f"E dasar UY 2024 = {E_uy:.1f} (kerugian dan premi naik bersama), tarif tetap", eksposur=E_uy)
    dasar = optimasi(M, "dasar")
    f08 = pd.concat([dasar.head(4), f08_a.head(4), f08_b.head(4)])
    f08.to_csv(ctx["keluar"] / "pilihan_f08.csv", index=False)
    assert dasar.iloc[0]["strategi"] == st_p and abs(dasar.iloc[0]["target_perlu"] - s_p) < 1e-9, "tiruan pengoptimal tidak sama dengan rancang_solusi.py"
    hasil["F08"] = {"E_uy_2024": E_uy, "tarif_setara_per_mil": pt2["bencana"]["tarif_gempa_per_mil"]["nilai"],
                    "dasar": dasar.head(3).to_dict("records"), "tarif_disetarakan": f08_a.head(3).to_dict("records"),
                    "E_uy_2024_konsisten": f08_b.head(3).to_dict("records"),
                    "strategi_terpilih_dasar_pada_tarif_disetarakan": f08_a[f08_a["strategi"] == st_p].to_dict("records"),
                    "modal_saja_pada_tarif_disetarakan": f08_a[f08_a["strategi"] == "S0_dasar"].to_dict("records")}

    # ---------- 3. kantong likuiditas dengan selang kuantil ----------
    d = M.jalankan(acuan, st_p, s_p, rinci=True)["deret"]
    kk = np.sort(d["klaim_kejadian"])
    p = 0.995
    g = 1.96 * np.sqrt(n * p * (1 - p))
    q, q_lo, q_hi = float(np.quantile(kk, p)), float(kk[int(np.floor(n * p - g))]), float(kk[int(np.ceil(n * p + g))])
    lik = {"klaim_kejadian_1_200": q, "selang95_kuantil": [q_lo, q_hi], "per_profil": {}}
    for kode in ("K80", "K75", "K70"):
        b = M.neraca_awal(kode, s_p)
        kas_dep = M.nilai["kas_dan_bank"] + b["investasi"] * M.varian[kode][2].get("deposito", 0.0)
        kk_k = M.jalankan(kode, st_p, s_p, rinci=True)["deret"]["klaim_kejadian"]
        lik["per_profil"][kode] = {"kas_dan_deposito": kas_dep, "cakupan": kas_dep / q, "cakupan_selang95": [kas_dep / q_hi, kas_dep / q_lo],
                                   "peluang_klaim_kejadian_melebihi_kas_deposito": float((kk_k > kas_dep).mean()),
                                   "jumlah_tahun_melebihi": int((kk_k > kas_dep).sum())}
    hasil["kantong_likuiditas"] = lik

    al.simpan_json(ctx["keluar"] / "pilihan.json", hasil)
    pd.set_option("display.width", 260)
    print(f"[{varian}] terpilih dasar: {st_p} pada {s_p}")
    print(tujuan[["fungsi_tujuan", "terpilih", "target_terpilih", "nilai_terpilih", "kedua", "nilai_kedua", "nilai_modal_saja_S0",
                  "selisih_terpilih_dasar_terhadap_modal_saja"]].round(3).to_string(index=False))
    print("biaya modal impas (fungsi tujuan):", {a: round(100 * b, 2) for a, b in hasil.get("biaya_modal_impas_fungsi_tujuan", {}).items()})
    print("F08 jembatan:", {a: round(b, 4) for a, b in jembatan.items()})
    print(f08[["kasus", "strategi", "target_C1", "target_C2", "target_C3", "target_perlu", "ekuitas", "premi_dilepas", "nilai_bersih"]].round(3).to_string(index=False))
    print(f"kantong likuiditas: klaim 1/200 = {q:.2f} [{q_lo:.2f}; {q_hi:.2f}]")
    for kode, v in lik["per_profil"].items():
        print(f"  {kode}: kas+deposito {v['kas_dan_deposito']:.2f}; cakupan {100 * v['cakupan']:.1f}% [{100 * v['cakupan_selang95'][0]:.1f}%; {100 * v['cakupan_selang95'][1]:.1f}%]; "
              f"P(klaim kejadian > kas+deposito) {100 * v['peluang_klaim_kejadian_melebihi_kas_deposito']:.3f}%")


if __name__ == "__main__":
    main()
