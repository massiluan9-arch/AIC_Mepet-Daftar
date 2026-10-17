"""T3 dan T4: tabel strategi, status S21 pada 160%, rancangan terpilih, dan ketidakpastian Monte Carlo.

Pemakaian: python analisis_t3_t4.py <varian>
Keluaran: laporan/hasil/<varian>/t3_strategi.csv, t3_t4.json
"""
import json
import sys

import numpy as np
import pandas as pd

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")
S21 = "S21_zona_batas10"


def main():
    varian = sys.argv[1]
    ctx = al.siapkan(varian)
    ms, M, pt, ps, r, acuan = ctx["ms"], ctx["M"], ctx["pt"], ctx["ps"], ctx["rancangan"], ctx["acuan"]
    n = M.n
    ambang = pt["meta"]["ambang_peluang"]
    k_modal = ps["biaya_modal"]["nilai"]
    bawah = ps["kendala"]["target_paling_rendah"]
    kisi = al.kisi_target(pt)
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")
    rugi_sken["campuran"] = sum(bobot_kurva[k] * rugi_sken[k] for k in ms.KURVA_TUNGGAL)
    hasil = {"varian": varian, "profil_acuan": acuan, "jumlah_tahun": n, "bobot_kurva": bobot_kurva}

    def megathrust(st, s):
        return M.rasio_skenario(acuan, st, float(s), rugi_sken.loc[st, "campuran"])["rasio_akhir"]

    def target_c3(st):
        for s in kisi:
            if megathrust(st, s) >= 1.0:
                return float(s)
        return None

    def nilai(st, s):
        x = M.jalankan(acuan, st, s)
        return {"ekuitas": x["ekuitas"], "laba_bersih": x["laba_bersih_rata"], "defisit": x["defisit_harapan"],
                "nilai_bersih": x["laba_bersih_rata"] - k_modal * x["ekuitas"] - x["defisit_harapan"],
                "peluang": x["peluang_di_bawah_100"], "premi_dilepas": x["premi_dilepas"], "L_tvar": x["L_tvar_99_5"]}

    def hitung(st, s, kurva):
        p = M.jalankan(acuan, st, float(s), kurva=kurva)["peluang_di_bawah_100"]
        k = int(round(p * n))
        lo, hi = al.selang_binomial(k, n)
        return {"peluang": p, "jumlah_pelanggaran": k, "selang95_bawah": lo, "selang95_atas": hi}

    # ---------- 1. tabel strategi (dari rancangan.json salinan ini) ----------
    urut = r["urutan_nilai_bersih"]
    baris = []
    for st, v in r["calon"].items():
        d, p120 = v.get("pada_target_perlu") or {}, v["pada_120"]
        baris.append({
            "strategi": st, "keterangan": v["keterangan"], "dikecualikan": bool(v["dikecualikan"]),
            "aal": p120["L_rata"], "var_99_5": p120["L_var_99_5"], "tvar_99_5": p120["L_tvar_99_5"],
            "premi_dilepas": p120["premi_dilepas"], "peluang_campuran_pada_120": p120["peluang_di_bawah_100"],
            "peluang_aulady_pada_120": p120["peluang_aulady"], "rasio_megathrust_pada_120": p120["rasio_setelah_megathrust"],
            "target_C1": v["target_C1"], "target_C2": v["target_C2"], "target_C3": v["target_C3"], "target_perlu": v["target_perlu"],
            "ekuitas_pada_target": d.get("ekuitas"), "laba_bersih_pada_target": d.get("laba_bersih_rata"),
            "defisit_pada_target": d.get("defisit_harapan"), "nilai_bersih": d.get("nilai_bersih"),
            "peringkat_nilai_bersih": (urut.index(st) + 1) if st in urut else None,
            "terpilih": st == r["terpilih"]["strategi"]})
    tabel = pd.DataFrame(baris)
    tabel.insert(0, "varian", varian)
    tabel.to_csv(ctx["keluar"] / "t3_strategi.csv", index=False)

    # ---------- 2. S21 pada 160%: masih lolos? ----------
    c1, c2 = hitung(S21, 1.6, "campuran"), hitung(S21, 1.6, "aulady")
    rasio = megathrust(S21, 1.6)
    x = M.jalankan(acuan, S21, 1.6)
    hasil["S21_pada_160"] = {
        "C1": c1, "C2": c2, "C3_rasio_setelah_megathrust": rasio,
        "lolos_C1": c1["peluang"] <= ambang, "lolos_C2": c2["peluang"] <= ambang, "lolos_C3": rasio >= 1.0,
        "target_C1": r["calon"][S21]["target_C1"], "target_C2": r["calon"][S21]["target_C2"], "target_C3": r["calon"][S21]["target_C3"],
        "target_perlu": r["calon"][S21]["target_perlu"], "ekuitas": x["ekuitas"], "premi_dilepas": x["premi_dilepas"],
        "L_rata": x["L_rata"], "L_var_99_5": x["L_var_99_5"], "L_tvar_99_5": x["L_tvar_99_5"], "defisit_harapan": x["defisit_harapan"],
        "klaim_kejadian_var_99_5": x["klaim_kejadian_var_99_5"], "kerugian_megathrust": 100 * pt["bencana"]["eksposur_per_premi"]["nilai"] * rugi_sken.loc[S21, "campuran"]}

    # ---------- 3. rancangan terpilih pengoptimal yang tidak diubah ----------
    st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
    pb = r["perbandingan"]
    hasil["terpilih"] = {
        "strategi": st_p, "keterangan": r["calon"][st_p]["keterangan"], "target": s_p,
        "C1": hitung(st_p, s_p, "campuran"), "C2": hitung(st_p, s_p, "aulady"), "C3_rasio_setelah_megathrust": megathrust(st_p, s_p),
        "target_C1": r["calon"][st_p]["target_C1"], "target_C2": r["calon"][st_p]["target_C2"], "target_C3": r["calon"][st_p]["target_C3"],
        "ekuitas": pb["terpilih"]["ekuitas"], "mmbr": pb["terpilih"]["mmbr"], "laba_bersih": pb["terpilih"]["laba_bersih_rata"],
        "premi_dilepas": pb["terpilih"]["premi_dilepas"], "L_rata": pb["terpilih"]["L_rata"], "L_var_99_5": pb["terpilih"]["L_var_99_5"],
        "L_tvar_99_5": pb["terpilih"]["L_tvar_99_5"], "defisit_harapan": pb["terpilih"]["defisit_harapan"],
        "nilai_bersih": pb["terpilih"]["nilai_bersih"], "klaim_kejadian_var_99_5": pb["terpilih"]["klaim_kejadian_var_99_5"],
        "kerugian_megathrust": pb["terpilih"]["kerugian_megathrust"],
        "kantong_likuiditas": r["terpilih"]["kantong_likuiditas"], "kepekaan": r["terpilih"]["kepekaan"], "skenario": r["terpilih"]["skenario"],
        "enam_teratas": [{"strategi": s, "target": r["calon"][s]["target_perlu"], "nilai_bersih": r["calon"][s]["pada_target_perlu"]["nilai_bersih"],
                          "ekuitas": r["calon"][s]["pada_target_perlu"]["ekuitas"]} for s in urut[:6]]}
    hasil["sekarang"] = {k: pb["sekarang"][k] for k in ("target", "ekuitas", "mmbr", "laba_bersih_rata", "peluang_di_bawah_100", "peluang_aulady",
                                                       "rasio_setelah_megathrust", "defisit_harapan", "L_rata", "L_var_99_5", "L_tvar_99_5", "nilai_bersih")}
    if "modal_saja" in pb:
        hasil["modal_saja"] = {k: pb["modal_saja"][k] for k in ("target", "ekuitas", "mmbr", "laba_bersih_rata", "peluang_di_bawah_100", "peluang_aulady",
                                                               "rasio_setelah_megathrust", "defisit_harapan", "L_tvar_99_5", "nilai_bersih")}

    # ---------- 4. aturan batas atas selang (T4) ----------
    k_maks = max(k for k in range(0, int(2 * ambang * n)) if al.selang_binomial(k, n)[1] <= ambang)
    ambang_ketat = (k_maks + 0.5) / n
    hasil["aturan_batas_atas"] = {"jumlah_pelanggaran_terbanyak": k_maks, "peluang_titik_setara": k_maks / n,
                                  "keterangan": "batas atas selang Clopper-Pearson 95% dua sisi tidak melebihi ambang 0,5%"}
    ulang = []
    for st, v in r["calon"].items():
        u1 = M.target_minimum(acuan, st, ambang=ambang_ketat)
        u2 = M.target_minimum(acuan, st, ambang=ambang_ketat, kurva="aulady")
        c3 = v["target_C3"]
        perlu = None if None in (u1, u2, c3) else max(bawah, u1, u2, c3)
        b = {"strategi": st, "dikecualikan": bool(v["dikecualikan"]), "target_C1_batas_atas": u1, "target_C2_batas_atas": u2, "target_C3": c3,
             "target_perlu_batas_atas": perlu, "target_perlu_titik": v["target_perlu"]}
        if perlu is not None:
            b.update({f"{k}_batas_atas": x for k, x in nilai(st, perlu).items()})
        ulang.append(b)
    ulang = pd.DataFrame(ulang)
    ulang.insert(0, "varian", varian)
    ulang.to_csv(ctx["keluar"] / "t4_aturan_batas_atas.csv", index=False)
    layak = ulang[(~ulang["dikecualikan"]) & ulang["target_perlu_batas_atas"].notna()].sort_values("nilai_bersih_batas_atas", ascending=False)
    pilih = layak.iloc[0]
    hasil["aturan_batas_atas"]["terpilih"] = {
        "strategi": pilih["strategi"], "target": float(pilih["target_perlu_batas_atas"]), "ekuitas": float(pilih["ekuitas_batas_atas"]),
        "nilai_bersih": float(pilih["nilai_bersih_batas_atas"]), "target_C1": pilih["target_C1_batas_atas"], "target_C2": pilih["target_C2_batas_atas"],
        "target_C3": pilih["target_C3"]}
    hasil["aturan_batas_atas"]["tiga_teratas"] = layak.head(3)[["strategi", "target_perlu_batas_atas", "ekuitas_batas_atas", "nilai_bersih_batas_atas"]].to_dict("records")
    b_p = ulang[ulang["strategi"] == st_p].iloc[0]
    hasil["aturan_batas_atas"]["strategi_terpilih_titik"] = {
        "strategi": st_p, "target_titik": s_p, "target_batas_atas": b_p["target_perlu_batas_atas"],
        "target_C1_batas_atas": b_p["target_C1_batas_atas"], "target_C2_batas_atas": b_p["target_C2_batas_atas"]}
    b_0 = ulang[ulang["strategi"] == "S0_dasar"].iloc[0]
    hasil["aturan_batas_atas"]["S0_dasar"] = {"target_C1_titik": r["calon"]["S0_dasar"]["target_C1"], "target_C2_titik": r["calon"]["S0_dasar"]["target_C2"],
                                              "target_C1_batas_atas": b_0["target_C1_batas_atas"], "target_C2_batas_atas": b_0["target_C2_batas_atas"]}

    # ---------- 5. kestabilan: dua paruh, sepuluh kelompok, penaksir berstrata ----------
    simpanan = {}

    def deret_gagal(st, s, kurva):
        kunci = (st, round(float(s), 2), kurva)
        if kunci not in simpanan:
            simpanan[kunci] = M.jalankan(acuan, st, float(s), kurva=kurva, rinci=True)["deret"]["R"] < 1.0
        return simpanan[kunci]

    stabil = {}
    for nama, kurva in (("C1_campuran", "campuran"), ("C2_aulady", "aulady")):
        g = deret_gagal(st_p, s_p, kurva)
        paruh = [float(g[: n // 2].mean()), float(g[n // 2:].mean())]
        kel = [float(x.mean()) for x in np.array_split(g, 10)]
        # target minimum tiap paruh dan tiap kelompok lima (20.000 tahun)
        def target_bagian(indeks):
            for s in kisi:
                if deret_gagal(st_p, s, kurva)[indeks].mean() <= ambang:
                    return float(s)
            return None
        bagian = {"paruh_1": slice(0, n // 2), "paruh_2": slice(n // 2, n)}
        bagian.update({f"kelima_{i + 1}": slice(i * n // 5, (i + 1) * n // 5) for i in range(5)})
        stabil[nama] = {"peluang_penuh": float(g.mean()), "paruh": paruh, "sepuluh_kelompok": kel,
                        "simpangan_baku_kelompok": float(np.std(kel, ddof=1)), "galat_baku_dari_kelompok": float(np.std(kel, ddof=1) / np.sqrt(10)),
                        "galat_baku_binomial": float(np.sqrt(g.mean() * (1 - g.mean()) / n)),
                        "kelompok_di_atas_ambang": int(sum(k > ambang for k in kel)),
                        "target_minimum_bagian": {k: target_bagian(v) for k, v in bagian.items()}}
    # Penaksir berstrata kurva campuran: rata-rata berbobot indikator tiga kurva pada tahun yang sama.
    ind = np.column_stack([deret_gagal(st_p, s_p, kv) for kv in ms.KURVA_TUNGGAL]).astype(float)
    w = np.array([bobot_kurva[kv] for kv in ms.KURVA_TUNGGAL])
    z = ind @ w
    lo, hi = z.mean() - 1.96 * z.std(ddof=1) / np.sqrt(n), z.mean() + 1.96 * z.std(ddof=1) / np.sqrt(n)
    stabil["C1_berstrata"] = {"peluang": float(z.mean()), "galat_baku": float(z.std(ddof=1) / np.sqrt(n)), "selang95_normal": [float(lo), float(hi)],
                              "peluang_per_kurva": {kv: float(ind[:, i].mean()) for i, kv in enumerate(ms.KURVA_TUNGGAL)}}
    hasil["kestabilan_terpilih"] = stabil

    al.simpan_json(ctx["keluar"] / "t3_t4.json", hasil)
    t = hasil["terpilih"]
    print(f"[{varian}] profil {acuan}; terpilih {t['strategi']} pada {t['target']:.2f}; ekuitas {t['ekuitas']:.2f}; nilai bersih {t['nilai_bersih']:.3f}")
    for k in ("C1", "C2"):
        print(f"  {k}: {t[k]['jumlah_pelanggaran']} pelanggaran = {100 * t[k]['peluang']:.3f}% [{100 * t[k]['selang95_bawah']:.3f}%; {100 * t[k]['selang95_atas']:.3f}%]")
    print(f"  C3: rasio setelah megathrust {100 * t['C3_rasio_setelah_megathrust']:.1f}%; target C1/C2/C3 = {t['target_C1']}/{t['target_C2']}/{t['target_C3']}")
    s = hasil["S21_pada_160"]
    print(f"  S21 pada 160%: C1 {100 * s['C1']['peluang']:.3f}% ({'lolos' if s['lolos_C1'] else 'GAGAL'}), C2 {100 * s['C2']['peluang']:.3f}% "
          f"({'lolos' if s['lolos_C2'] else 'GAGAL'}), C3 {100 * s['C3_rasio_setelah_megathrust']:.1f}% ({'lolos' if s['lolos_C3'] else 'GAGAL'}); "
          f"target perlu S21 = {s['target_perlu']}")
    a = hasil["aturan_batas_atas"]
    print(f"  aturan batas atas (k <= {a['jumlah_pelanggaran_terbanyak']}): terpilih {a['terpilih']['strategi']} pada {a['terpilih']['target']:.2f}; "
          f"strategi terpilih-titik perlu {a['strategi_terpilih_titik']['target_batas_atas']}")
    print(tabel[["strategi", "aal", "var_99_5", "tvar_99_5", "premi_dilepas", "peluang_campuran_pada_120", "target_C1", "target_C2", "target_C3",
                 "target_perlu", "ekuitas_pada_target", "nilai_bersih", "peringkat_nilai_bersih"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
