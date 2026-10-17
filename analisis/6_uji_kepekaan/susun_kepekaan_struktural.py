"""Tabel kepekaan struktural Rev. 2: satu baris per kasus, tiap kasus dinilai dengan dua aturan peluang
(taksiran titik dan batas atas selang Clopper-Pearson 95%).

Sumber tiap baris:
  - dasar: 5_solusi_motera/keluaran/rancangan.json pada repositori (dijalankan ulang penuh).
  - nu 1,5; nu 6; eksposur Juni 2025; eksposur dan tabel klaim Juni 2025: ringkasan dari rantai penuh
    (R 04, R 05, mesin, rancangan) yang dijalankan di lab pada Varian A, K70; disalin ke hasil_lab/.
    Keluaran R kasus-kasus itu tidak disimpan di repositori (lihat README.md untuk mengulanginya).
  - E dasar UY 2024 dan premi gempa 22,83: dihitung di sini dengan mesin repositori (tanpa simulasi R ulang).

Keluaran: analisis/5_solusi_motera/keluaran/kepekaan_struktural.csv
Pemakaian: python analisis/6_uji_kepekaan/susun_kepekaan_struktural.py
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

SINI = Path(__file__).resolve().parent
AKAR = SINI.parents[1]
DIR_T = AKAR / "analisis"
sys.path.insert(0, str(DIR_T / "4_simulasi_terpadu" / "kode"))
import mesin as ms          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
S21 = "S21_zona_batas10"
S0 = "S0_dasar"


def baris_kosong(kasus, sumber, bobot):
    return {"kasus": kasus, "bobot_klaim": bobot["klaim"], "bobot_aulady": bobot["aulady"], "bobot_pager": bobot["pager"], "sumber": sumber}


def isi(b, tabel):
    """tabel: DataFrame berindeks strategi dengan kolom C1_titik, C2_titik, C1_atas, C2_atas, C3, perlu_titik, perlu_atas,
    nb_titik, nb_atas, dikecualikan."""
    for st, nama in ((S0, "polis_standar"), (S21, "S21")):
        r = tabel.loc[st]
        b.update({f"{nama}_target_C1_titik": r["C1_titik"], f"{nama}_target_C2_titik": r["C2_titik"],
                  f"{nama}_target_C1_batas_atas": r["C1_atas"], f"{nama}_target_C2_batas_atas": r["C2_atas"], f"{nama}_target_C3": r["C3"],
                  f"{nama}_target_perlu_titik": r["perlu_titik"], f"{nama}_target_perlu_batas_atas": r["perlu_atas"],
                  f"{nama}_nilai_bersih_titik": r["nb_titik"], f"{nama}_nilai_bersih_batas_atas": r["nb_atas"]})
    layak = tabel[~tabel["dikecualikan"].astype(bool)]
    for aturan in ("titik", "atas"):
        t = layak[layak[f"perlu_{aturan}"].notna()].sort_values(f"nb_{aturan}", ascending=False)
        label = "titik" if aturan == "titik" else "batas_atas"
        b.update({f"pilihan_{label}": t.index[0], f"target_pilihan_{label}": t.iloc[0][f"perlu_{aturan}"],
                  f"nilai_bersih_pilihan_{label}": t.iloc[0][f"nb_{aturan}"], f"kedua_{label}": t.index[1],
                  f"nilai_bersih_kedua_{label}": t.iloc[1][f"nb_{aturan}"]})
    return b


def dari_lab(folder):
    d = SINI / "hasil_lab" / folder
    a = pd.read_csv(d / "t3_strategi.csv").set_index("strategi")
    u = pd.read_csv(d / "t4_aturan_batas_atas.csv").set_index("strategi")
    t = pd.DataFrame({"C1_titik": a["target_C1"], "C2_titik": a["target_C2"], "C3": a["target_C3"], "perlu_titik": a["target_perlu"],
                      "nb_titik": a["nilai_bersih"], "dikecualikan": a["dikecualikan"],
                      "C1_atas": u["target_C1_batas_atas"], "C2_atas": u["target_C2_batas_atas"], "perlu_atas": u["target_perlu_batas_atas"],
                      "nb_atas": u["nilai_bersih_batas_atas"]})
    return t, json.loads((d / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]


def dari_rancangan(r):
    aturan = r["meta"]["aturan_peluang"]
    assert aturan == "batas_atas", "tabel ini mengandaikan aturan dasar batas_atas"
    baris = {}
    for st, v in r["calon"].items():
        d, dt = v.get("pada_target_perlu") or {}, v.get("pada_target_perlu_titik") or {}
        baris[st] = {"C1_atas": v["target_C1"], "C2_atas": v["target_C2"], "C3": v["target_C3"], "perlu_atas": v["target_perlu"],
                     "nb_atas": d.get("nilai_bersih"), "C1_titik": v["target_C1_titik"], "C2_titik": v["target_C2_titik"],
                     "perlu_titik": v["target_perlu_titik"], "nb_titik": dt.get("nilai_bersih"), "dikecualikan": bool(v["dikecualikan"])}
    return pd.DataFrame(baris).T


def dari_mesin(M, pt, ps, acuan, rugi_sken, eksposur=None):
    """Meniru rancang_solusi.py untuk semua strategi pada dua aturan, dengan pilihan eksposur."""
    n = M.n
    amb = {"titik": ms.ambang_aturan(pt, n, "titik"), "atas": ms.ambang_aturan(pt, n, "batas_atas")}
    kisi = np.round(np.arange(pt["target_solvabilitas"]["kisi"]["awal"], pt["target_solvabilitas"]["kisi"]["akhir"] + 1e-9,
                              pt["target_solvabilitas"]["kisi"]["langkah"]), 2)
    k_modal, bawah = ps["biaya_modal"]["nilai"], ps["kendala"]["target_paling_rendah"]
    opsi = {} if eksposur is None else {"eksposur": eksposur}
    baris = {}
    for st in M.strategi.index:
        c3 = next((float(s) for s in kisi if M.rasio_skenario(acuan, st, float(s), rugi_sken.loc[st, "campuran"], **opsi)["rasio_akhir"] >= 1.0), None)
        b = {"C3": c3, "dikecualikan": bool(ps["dikecualikan"].get(st, ""))}
        for nama, a in amb.items():
            c1 = M.target_minimum(acuan, st, ambang=a, **opsi)
            c2 = M.target_minimum(acuan, st, ambang=a, kurva="aulady", **opsi)
            perlu = None if None in (c1, c2, c3) else max(bawah, c1, c2, c3)
            nb = None
            if perlu is not None:
                x = M.jalankan(acuan, st, perlu, **opsi)
                nb = x["laba_bersih_rata"] - k_modal * x["ekuitas"] - x["defisit_harapan"]
            b.update({f"C1_{nama}": c1, f"C2_{nama}": c2, f"perlu_{nama}": perlu, f"nb_{nama}": nb})
        baris[st] = b
    return pd.DataFrame(baris).T


def main():
    p05, pt = ms.muat_semua()
    ps = yaml.safe_load((DIR_T / "5_solusi_motera" / "parameter_solusi.yaml").read_text(encoding="utf-8"))
    acuan = pt["meta"]["profil_acuan"]
    r = json.loads((DIR_T / "5_solusi_motera" / "keluaran" / "rancangan.json").read_text(encoding="utf-8"))
    bobot = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    bi = json.loads((ms.DIR_DATA / "besaran_industri.json").read_text(encoding="utf-8"))
    keluar = []

    keluar.append(isi(baris_kosong("dasar (Varian A, K70, nu 3, MAIPARK Desember 2024, E 139,16)", "rancangan.json repositori (rantai penuh)", bobot), dari_rancangan(r)))
    for kasus, folder in (("presisi Beta nu 1,5", "NU1.5_A_K70"), ("presisi Beta nu 6", "NU6_A_K70"),
                          ("eksposur MAIPARK Juni 2025 saja", "F03b_A_K70"), ("eksposur dan tabel klaim MAIPARK Juni 2025", "F03_A_K70")):
        t, w = dari_lab(folder)
        keluar.append(isi(baris_kosong(kasus, f"rantai penuh di lab (hasil_lab/{folder})", w), t))

    # periksa bahwa salinan lab kasus dasar sama dengan repositori (pengaman terhadap pergeseran kode)
    t_lab, _ = dari_lab("A_K70")
    t_rep = dari_rancangan(r)
    kol = ["C1_titik", "C2_titik", "C1_atas", "C2_atas", "C3", "perlu_titik", "perlu_atas"]
    beda = int((t_lab[kol].astype(float).round(4) != t_rep.loc[t_lab.index, kol].astype(float).round(4)).sum().sum())
    print(f"kasus dasar: target lab lawan repositori berbeda pada {beda} sel dari {t_lab[kol].size}")

    M = ms.Mesin(p05, pt)
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")
    rugi_sken["campuran"] = sum(bobot[k] * rugi_sken[k] for k in ms.KURVA_TUNGGAL)
    E_uy = bi["eksposur_uy_triliun"]["2024"] * 1000 / bi["premi_harta_benda_langsung_2024_miliar"]
    keluar.append(isi(baris_kosong(f"E dasar tahun penutupan 2024 = {E_uy:.1f} (kerugian dan premi naik bersama)", "mesin repositori, pilihan eksposur", bobot),
                      dari_mesin(M, pt, ps, acuan, rugi_sken, eksposur=E_uy)))
    pt2 = copy.deepcopy(pt)
    porsi = bi["premi_gempa_uy_miliar"]["2024"] / bi["premi_harta_benda_langsung_2024_miliar"]
    pt2["bencana"]["tarif_gempa_per_mil"]["nilai"] = porsi * 1000.0 / pt["bencana"]["eksposur_per_premi"]["nilai"]
    M2 = ms.Mesin(p05, pt2)
    keluar.append(isi(baris_kosong(f"premi gempa {100 * porsi:.2f} per 100 premi dengan E 139,16", "mesin repositori, tarif disetarakan", bobot),
                      dari_mesin(M2, pt2, ps, acuan, rugi_sken)))

    t = pd.DataFrame(keluar)
    depan = ["kasus", "bobot_klaim", "bobot_aulady", "bobot_pager"]
    t = t[depan + [c for c in t.columns if c not in depan + ["sumber"]] + ["sumber"]]
    t.to_csv(DIR_T / "5_solusi_motera" / "keluaran" / "kepekaan_struktural.csv", index=False)
    pd.set_option("display.width", 250)
    print(t[["kasus", "bobot_aulady", "polis_standar_target_perlu_titik", "polis_standar_target_perlu_batas_atas", "S21_target_perlu_titik",
             "S21_target_perlu_batas_atas", "S21_nilai_bersih_batas_atas", "polis_standar_nilai_bersih_batas_atas", "pilihan_titik",
             "target_pilihan_titik", "pilihan_batas_atas", "target_pilihan_batas_atas"]].to_string(index=False))


if __name__ == "__main__":
    main()
