"""F12: seberapa besar hasil bergeser bila potongan jual SBN disamakan dengan potongan repo 10% yang dipakai 05.

Pemakaian: python analisis_f12_likuiditas.py <varian>
"""
import copy
import json
import sys

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")
varian = sys.argv[1]
ctx = al.siapkan(varian)
ms, M, p05, pt, r, acuan = ctx["ms"], ctx["M"], ctx["p05"], ctx["pt"], ctx["rancangan"], ctx["acuan"]
st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
pt2 = copy.deepcopy(pt)
pt2["likuiditas"]["potongan_harga"]["sbn"]["nilai"] = p05["pasar"]["likuiditas"]["potongan_repo_sbn"]
M2 = ms.Mesin(p05, pt2)
out = {"varian": varian, "potongan_sbn_dasar": pt["likuiditas"]["potongan_harga"]["sbn"]["nilai"], "potongan_sbn_uji": pt2["likuiditas"]["potongan_harga"]["sbn"]["nilai"], "kasus": []}
for nama, kode, st, s in (("standar_120", acuan, "S0_dasar", 1.2), ("solusi", acuan, st_p, s_p), ("standar_120_K80", "K80", "S0_dasar", 1.2), ("solusi_K80", "K80", st_p, s_p)):
    a, b = M.jalankan(kode, st, s), M2.jalankan(kode, st, s)
    out["kasus"].append({"kasus": nama, "profil": kode, "strategi": st, "target": s,
                         "peluang_dasar": a["peluang_di_bawah_100"], "peluang_uji": b["peluang_di_bawah_100"],
                         "F_var_99_5_dasar": a["F_var_99_5"], "F_var_99_5_uji": b["F_var_99_5"], "F_rata_dasar": a["F_rata"], "F_rata_uji": b["F_rata"],
                         "target_minimum_dasar": M.target_minimum(kode, st), "target_minimum_uji": M2.target_minimum(kode, st),
                         "aset_siap_cair_nominal": a["aset_siap_cair"],
                         "kas_deposito_dan_SBN_setelah_potongan_10persen": M.nilai["kas_dan_bank"] + sum(a["investasi"] * w * (0.9 if k == "sbn" else 1.0) for k, w in M.varian[kode][2].items() if k in ("deposito", "sbn"))})
al.simpan_json(ctx["keluar"] / "f12_likuiditas.json", out)
for k in out["kasus"]:
    print({a: (round(b, 5) if isinstance(b, float) else b) for a, b in k.items()})
