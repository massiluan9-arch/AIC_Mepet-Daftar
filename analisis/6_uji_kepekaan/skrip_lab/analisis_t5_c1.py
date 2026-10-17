"""T5: kendala C1, C3, dan target yang diperlukan bila bobot kurva kerentanan diganti.

Peluang pada kurva campuran dihitung sebagai jumlah berbobot peluang tiga kurva tunggal pada 100.000 tahun yang
sama (nilai harapan dari pengambilan cabang acak di skrip 05), sehingga bobot dapat diganti tanpa simulasi ulang.

Pemakaian: python analisis_t5_c1.py <varian>
Masukan: laporan/hasil/umum/t5_bobot.csv (keluaran analisis_t5_bobot.R)
Keluaran: laporan/hasil/<varian>/t5_c1.csv
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
    KV = ms.KURVA_TUNGGAL
    bobot_dasar = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")

    strategi = ["S0_dasar"] + ([st_p] if st_p != "S0_dasar" else [])
    # peluang tiap kurva tunggal pada tiap titik kisi
    P = {st: {kv: np.array([M.jalankan(acuan, st, float(s), kurva=kv)["peluang_di_bawah_100"] for s in kisi]) for kv in KV} for st in strategi}

    def indeks(s):
        return int(np.argmin(np.abs(kisi - s)))

    def baris(kasus, metode, w, ket=""):
        out = {"varian": varian, "kasus": kasus, "metode": metode, "bobot_klaim": w["klaim"], "bobot_aulady": w["aulady"], "bobot_pager": w["pager"], "keterangan": ket}
        for nama, st, s in (("standar", "S0_dasar", 1.2), ("solusi", st_p, s_p)):
            pm = sum(w[kv] * P[st][kv] for kv in KV)
            lolos = np.where(pm <= ambang)[0]
            c1 = float(kisi[lolos[0]]) if len(lolos) else None
            rugi = float(sum(w[kv] * rugi_sken.loc[st, kv] for kv in KV))
            c3 = next((float(x) for x in kisi if M.rasio_skenario(acuan, st, float(x), rugi)["rasio_akhir"] >= 1.0), None)
            c2 = r["calon"][st]["target_C2"]
            out.update({f"peluang_{nama}": float(pm[indeks(s)]), f"target_C1_{nama}": c1, f"target_C2_{nama}": c2, f"target_C3_{nama}": c3,
                        f"rasio_megathrust_{nama}": M.rasio_skenario(acuan, st, s, rugi)["rasio_akhir"],
                        f"target_perlu_{nama}": None if None in (c1, c2, c3) else max(bawah, c1, c2, c3)})
        out["solusi_lolos_C1_dan_C3_pada_target_terpilih"] = bool(out["peluang_solusi"] <= ambang and out["rasio_megathrust_solusi"] >= 1.0)
        return out

    tabel = [baris("bobot_05_parameter", "penaksir berstrata", bobot_dasar, "bobot Rev. 1; pembanding bagi hasil cabang acak")]
    bobot = pd.read_csv(al.DIR_HASIL / "umum" / "t5_bobot.csv")
    for _, b in bobot.iterrows():
        tabel.append(baris(b["kasus"], b["metode"], {"klaim": b["bobot_klaim"], "aulady": b["bobot_aulady"], "pager": b["bobot_pager"]},
                           b["keterangan"] if isinstance(b["keterangan"], str) else ""))
    for kv in KV:
        tabel.append(baris(f"hanya_{kv}", "satu kurva", {k: float(k == kv) for k in KV}))
    tabel.append(baris("sama_rata", "bobot sepertiga", {k: 1 / 3 for k in KV}))
    t = pd.DataFrame(tabel)
    t.to_csv(ctx["keluar"] / "t5_c1.csv", index=False)
    pd.set_option("display.width", 280)
    print(f"[{varian}] solusi {st_p} pada {s_p}; kendala C2 (Aulady saja) tidak bergantung pada bobot: standar {r['calon']['S0_dasar']['target_C2']}, solusi {r['calon'][st_p]['target_C2']}")
    print(t[["kasus", "bobot_klaim", "bobot_aulady", "bobot_pager", "peluang_standar", "target_C1_standar", "target_C3_standar", "target_perlu_standar",
             "peluang_solusi", "target_C1_solusi", "target_C3_solusi", "rasio_megathrust_solusi", "target_perlu_solusi"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
