"""Pemeriksaan simulasi neraca terpadu. Gagal satu saja menghentikan dengan kode keluar 1.

Pemakaian: python kode/uji_terpadu.py
"""
import json
import sys

import numpy as np

import mesin as ms

sys.stdout.reconfigure(encoding="utf-8")
HASIL = []


def cek(nama, syarat, rinci=""):
    HASIL.append(bool(syarat))
    print(("LULUS  " if syarat else "GAGAL  ") + nama + (f"  [{rinci}]" if rinci else ""))


def main():
    p05, pt = ms.muat_semua()
    M = ms.Mesin(p05, pt)
    h05 = json.loads((ms.AKAR / "analisis" / "3_investasi_mmbr" / "keluaran" / "hasil.json").read_text(encoding="utf-8"))
    acuan = pt["meta"]["profil_acuan"]

    # 1. Mesin investasi menghasilkan angka yang sama dengan analisis/3_investasi_mmbr
    for kode in ("K75", "M50", "A30"):
        r = ms.mi.imbal_portofolio(M.varian[kode][2], M.pasar["bersama"]["imbal"])
        lama = h05["profil"][kode]["imbal_hasil"]["bersama"]
        cek(f"imbal hasil {kode} sama dengan 05", abs(r.mean() - lama["rata"]) < 1e-12 and abs(-np.quantile(r, 0.005) - lama["var_99_5"]) < 1e-12,
            f"{r.mean():.6f} lawan {lama['rata']:.6f}")

    # 2. Neraca awal: rasio tepat pada target dan MMBR sama dengan 05
    b = M.neraca_awal(acuan, 1.2)
    lama = h05["mmbr"]["pada_target"][acuan] if "pada_target" in h05.get("mmbr", {}) else None
    cek("rasio awal tepat 120%", abs(b["rasio"] - 1.2) < 1e-9, f"{b['rasio']:.10f}")
    cek("jumlah modul sama dengan MMBR", abs(sum(b["modul"].values()) - b["mmbr"]) < 1e-9)
    if lama:
        cek("MMBR pada target sama dengan 05", abs(lama["mmbr"] - b["mmbr"]) < 1e-9)

    # 3. Identitas laba dan rasio pada deret mentah
    r = M.jalankan(acuan, "S0_dasar", 1.2, rinci=True)
    d = r["deret"]
    cek("G = U + I - L - F", np.allclose(d["G"], d["U"] + d["I"] - d["L"] - d["F"]))
    pajak = pt["underwriting"]["pajak"]["nilai"] * np.maximum(d["G"], 0)
    cek("R = (TS0 + G - pajak) / MMBR", np.allclose(d["R"], (r["tingkat_solvabilitas"] + d["G"] - pajak) / r["mmbr"]))
    cek("kerugian kejadian terbesar tidak melebihi kerugian setahun", bool((d["klaim_kejadian"] <= d["L"] + 1e-9).all()))
    cek("biaya jual paksa tidak negatif dan nol bila klaim di bawah kas",
        bool((d["F"] >= 0).all() and (d["F"][d["klaim_kejadian"] <= M.nilai["kas_dan_bank"]] == 0).all()))

    # 4. Skala kerugian bencana cocok dengan keluaran R
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    import pandas as pd
    camp = pd.read_csv(ms.DIR_BENCANA / "05_ukuran_risiko_campuran.csv").set_index("strategi")
    cek("rata-rata L = E x 100 x rata-rata fraksi", abs(r["L_rata"] - 100 * E * camp.loc["S0_dasar", "aal"]) < 1e-6,
        f"{r['L_rata']:.4f}")
    cek("VaR 99,5% L = E x 100 x VaR fraksi", abs(r["L_var_99_5"] / (100 * E * camp.loc["S0_dasar", "var_99_5"]) - 1) < 1e-6)

    # 5. Kasus batas: tanpa bencana, tanpa underwriting acak -> kembali ke peluang investasi murni (dengan laba U tetap)
    tanpa = M.jalankan(acuan, "S0_dasar", 1.2, eksposur=1e-12)
    cek("tanpa eksposur gempa kerugian bencana nol", tanpa["L_rata"] < 1e-9 and tanpa["premi_dilepas"] < 1e-9)
    cek("tanpa bencana peluang pelanggaran jauh lebih kecil", tanpa["peluang_di_bawah_100"] < 0.1 * r["peluang_di_bawah_100"],
        f"{tanpa['peluang_di_bawah_100']:.5f} lawan {r['peluang_di_bawah_100']:.5f}")

    # 6. Kemonotonan
    p = [M.jalankan(acuan, "S0_dasar", s)["peluang_di_bawah_100"] for s in (1.0, 1.2, 1.5, 2.0, 3.0, 4.0)]
    cek("peluang turun bila target naik", all(a >= b for a, b in zip(p, p[1:])), ", ".join(f"{x:.4f}" for x in p))
    urut = ["S9_batas50", "S10_batas40", "S11_batas30", "S12_batas25", "S3_batas20", "S13_batas15", "S4_batas10"]
    v = [M.jalankan(acuan, st, 1.2)["L_var_99_5"] for st in urut]
    cek("VaR turun bila batas ganti rugi makin ketat", all(a >= b for a, b in zip(v, v[1:])), ", ".join(f"{x:.1f}" for x in v))
    rentang_E = pt["bencana"]["eksposur_per_premi"]["rentang"]
    pe = [M.jalankan(acuan, "S0_dasar", 1.2, eksposur=e)["peluang_di_bawah_100"] for e in (rentang_E[0], E, rentang_E[1])]
    cek("peluang naik bila eksposur per premi naik", pe[0] <= pe[1] <= pe[2], ", ".join(f"{x:.4f}" for x in pe))

    # 7. Premi yang dilepas konsisten dengan skala regulasi
    q = 100 * E * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000
    s3 = M.jalankan(acuan, "S3_batas20", 1.2)
    skala20 = pt["skala_premi_syarat"]["batas20"]["nilai"]
    cek(f"premi dilepas batas 20% = {1 - skala20:.0%} premi gempa (skala dari YAML)", abs(s3["premi_dilepas"] - (1 - skala20) * q) < 1e-9,
        f"{s3['premi_dilepas']:.4f}")

    # 8. Target minimum benar-benar memenuhi ambang, dan satu langkah di bawahnya tidak
    for st in ("S0_dasar", "S12_batas25"):
        sm = M.target_minimum(acuan, st)
        atas = M.jalankan(acuan, st, sm)["peluang_di_bawah_100"]
        bawah = M.jalankan(acuan, st, sm - 0.05)["peluang_di_bawah_100"] if sm > 1.0 else 1.0
        cek(f"target minimum {st} = {sm}", atas <= 0.005 < bawah, f"{atas:.5f} dan {bawah:.5f}")

    # 9. Ekuitas sama: investasi sama untuk semua profil
    inv = M.neraca_awal(acuan, 1.2)["investasi"]
    e = [M.jalankan(k, "S0_dasar", None, investasi=inv)["ekuitas"] for k in M.varian]
    cek("ekuitas sama antarprofil pada uji ekuitas sama", max(e) - min(e) < 1e-9, f"{e[0]:.4f}")

    # 10. Kestabilan Monte Carlo: dua paruh sampel
    R = d["R"]
    paruh = [float((R[:M.n // 2] < 1).mean()), float((R[M.n // 2:] < 1).mean())]
    cek("dua paruh sampel berselisih kurang dari tiga galat baku", abs(paruh[0] - paruh[1]) < 3 * np.sqrt(2) * r["galat_baku_peluang"] * np.sqrt(2),
        f"{paruh[0]:.5f} dan {paruh[1]:.5f}")

    # 11. Rev. 2: rumus pembayaran. Pembayaran per risiko paling besar sama dengan batas, jadi kerugian satu kejadian
    #     pada strategi berbatas seragam tidak boleh melampaui batas x eksposur, dan tidak melampaui polis standar.
    meta = json.loads((ms.DIR_BENCANA / "04_meta.json").read_text(encoding="utf-8"))
    cek("04_meta.json mencatat dasar batas = pembayaran maksimum", meta.get("dasar_batas") == "bayar", str(meta.get("dasar_batas")))
    ylt4 = pd.read_csv(ms.DIR_BENCANA / "04_ylt.csv.gz")
    batas = {"S4_batas10": 0.10, "S13_batas15": 0.15, "S3_batas20": 0.20, "S12_batas25": 0.25, "S11_batas30": 0.30,
             "S10_batas40": 0.40, "S9_batas50": 0.50}
    lebih, di_atas_dasar, terbesar = 0, 0, 0.0
    for kv in ms.KURVA_TUNGGAL:
        for st, u in batas.items():
            mk = ylt4[f"maks.{kv}.{st}"].to_numpy()
            lebih += int((mk > u * (1 + 1e-6)).sum())
            di_atas_dasar += int((mk > ylt4[f"maks.{kv}.S0_dasar"].to_numpy() * (1 + 1e-5) + 1e-12).sum())
            terbesar = max(terbesar, float((mk / u).max()))
    cek("kerugian satu kejadian tidak melampaui batas ganti rugi x eksposur (7 batas, 3 kurva)", lebih == 0,
        f"terbesar {terbesar:.3f} dari batas")
    cek("kerugian satu kejadian strategi berbatas tidak melampaui polis standar", di_atas_dasar == 0)
    cek("keluaran uji_rumus_bayar.R ada (uji unit rumus pembayaran dijalankan)", (ms.DIR_BENCANA / "uji_rumus_bayar_mc.csv").exists())

    # 12. Rev. 2: rancangan terpilih. Dilewati bila rancangan.json belum dibangun ulang untuk konfigurasi ini
    #     (jalankan rancang_solusi.py lalu ulangi uji ini).
    berkas_r = ms.DIR_TERPADU / "5_solusi_motera" / "keluaran" / "rancangan.json"
    rc = json.loads(berkas_r.read_text(encoding="utf-8")) if berkas_r.exists() else None
    aturan = pt["meta"].get("aturan_peluang", "titik")
    ambang = pt["meta"]["ambang_peluang"]
    if rc is None or rc["meta"].get("profil") != acuan or rc["meta"].get("aturan_peluang") != aturan or "C1" not in rc.get("terpilih", {}):
        print("DILEWATI  uji rancangan terpilih: rancangan.json belum sesuai konfigurasi; jalankan rancang_solusi.py lalu ulangi")
    else:
        t = rc["terpilih"]
        st_p, s_p = t["strategi"], t["target"]
        k_maks = ms.pelanggaran_terbanyak(ambang, M.n, pt["meta"].get("tingkat_selang", 0.95))
        batas_k = k_maks if aturan == "batas_atas" else int(ambang * M.n)
        hitung = lambda s, kv: int(round(M.jalankan(acuan, st_p, s, kurva=kv)["peluang_di_bawah_100"] * M.n))
        k1, k2 = hitung(s_p, "campuran"), hitung(s_p, "aulady")
        cek(f"rancangan terpilih lolos C1 menurut aturan {aturan}", k1 <= batas_k and k1 == t["C1"]["jumlah_pelanggaran"],
            f"{k1} pelanggaran, paling banyak {batas_k}")
        cek(f"rancangan terpilih lolos C2 menurut aturan {aturan}", k2 <= batas_k and k2 == t["C2"]["jumlah_pelanggaran"],
            f"{k2} pelanggaran, paling banyak {batas_k}")
        kunci = "selang_atas" if aturan == "batas_atas" else "peluang"
        cek(f"{kunci} C1 dan C2 pada rancangan terpilih tidak melebihi ambang", max(t["C1"][kunci], t["C2"][kunci]) <= ambang,
            f"{t['C1'][kunci]:.5f} dan {t['C2'][kunci]:.5f}")
        cek("rancangan terpilih lolos C3 (rasio setelah megathrust paling rendah 100%)", t["C3_rasio_setelah_megathrust"] >= 1.0,
            f"{t['C3_rasio_setelah_megathrust']:.4f}")
        cek("satu langkah kisi di bawah target terpilih gagal paling sedikit satu kendala",
            s_p <= 1.2 + 1e-9 or hitung(s_p - 0.05, "campuran") > batas_k or hitung(s_p - 0.05, "aulady") > batas_k
            or s_p - 0.05 < t["target_C3"] - 1e-9)
        cek("profil_acuan sama dengan profil menurut aturan kantong likuiditas", t["profil_menurut_kantong_likuiditas"] == acuan,
            f"acuan {acuan}; aturan {t['profil_menurut_kantong_likuiditas']}; cakupan "
            + ", ".join(f"{k} {v['cakupan']:.3f}" for k, v in t["kantong_likuiditas"].items()))

    print(f"\n{sum(HASIL)} dari {len(HASIL)} pemeriksaan lulus")
    sys.exit(0 if all(HASIL) else 1)


if __name__ == "__main__":
    main()
