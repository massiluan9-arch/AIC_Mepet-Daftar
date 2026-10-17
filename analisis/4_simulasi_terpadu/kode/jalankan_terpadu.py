"""Menjalankan simulasi neraca terpadu dan menulis jawaban angka untuk soal 1 sampai 4.

Keluaran: keluaran/hasil_terpadu.json dan keluaran/tabel/*.csv
Pemakaian: python kode/jalankan_terpadu.py
"""
import json
import sys
import time

import numpy as np
import pandas as pd

import mesin as ms

sys.stdout.reconfigure(encoding="utf-8")
STRATEGI_UTAMA = ["S0_dasar", "S2_rs10", "S12_batas25", "S3_batas20", "S17_batas20_besar", "S21_zona_batas10", "S7_paketA", "S8_paketB"]
RINGKAS = ["target", "investasi", "mmbr", "ekuitas", "premi", "premi_dilepas", "peluang_di_bawah_100",
           "galat_baku_peluang", "peluang_di_bawah_120", "peluang_di_bawah_0", "defisit_harapan", "rasio_rata", "rasio_median", "rasio_p5", "rasio_p0_5",
           "rata_rasio_di_ekor_0_5", "laba_bersih_rata", "U_rata", "I_rata", "L_rata", "L_var_99_5", "L_tvar_99_5",
           "klaim_kejadian_var_99_5", "F_rata", "F_var_99_5", "aset_siap_cair", "peluang_kurang_likuiditas",
           "peluang_aset_tidak_cukup", "imbal_hasil_rata", "imbal_hasil_riil"]


def ambil(r):
    return {k: r[k] for k in RINGKAS}


def bersih(o):
    if isinstance(o, dict):
        return {str(k): bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [bersih(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def main():
    mulai = time.time()
    ms.DIR_TABEL.mkdir(parents=True, exist_ok=True)
    p05, pt = ms.muat_semua()
    M = ms.Mesin(p05, pt)
    acuan, st0 = pt["meta"]["profil_acuan"], pt["meta"]["strategi_acuan"]
    semua_strategi = list(M.strategi.index)
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    hasil = {"meta": {
        "judul": "Simulasi neraca terpadu PT Aktu Proteksi",
        "jumlah_tahun": M.n, "satuan": "per 100 premi dicatat lini harta benda",
        "ambang_peluang": pt["meta"]["ambang_peluang"], "profil_acuan": acuan,
        "eksposur_per_premi": E, "premi_gempa_per_100_premi": 100 * E * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000,
        "bobot_kurva": bobot_kurva,
        "persamaan": "R = [s x MMBR + G - pajak x max(G,0)] / [MMBR + fck x porsi_belum_dibayar x L]; G = U + I - L - F",
    }}

    # ---------------- Soal 1: profil investasi ----------------
    inv_acuan = M.neraca_awal(acuan, 1.2)["investasi"]
    s1 = {}
    for kode, (nama, label, bobot) in M.varian.items():
        ayd = ms.mm.uji_ayd(bobot, M.reg)
        t120 = {st: M.jalankan(kode, st, 1.2) for st in ("S0_dasar", "S7_paketA")}
        sama = {st: M.jalankan(kode, st, None, investasi=inv_acuan) for st in ("S0_dasar", "S7_paketA")}
        s1[kode] = {
            "profil": nama, "label": label, "bobot": bobot, "patuh_ayd": ayd["patuh"],
            "porsi_tidak_diakui": ayd["porsi_tidak_diakui"],
            "ketentuan_dilampaui": "; ".join(f"{d['jenis']} {d['porsi']:.0%} > {d['batas']:.0%}" for d in ayd["dilampaui"]),
            "target_120": {st: ambil(r) for st, r in t120.items()},
            "ekuitas_sama": {st: ambil(r) for st, r in sama.items()},
            "target_minimum": {st: M.target_minimum(kode, st) for st in ("S0_dasar", "S7_paketA")},
        }
    hasil["soal1"] = {"investasi_acuan": inv_acuan, "varian": s1}

    # ---------------- Soal 2: mitigasi tanpa reasuransi ----------------
    dasar = M.jalankan(acuan, st0, 1.2)
    s2 = {}
    for st in semua_strategi:
        r = M.jalankan(acuan, st, 1.2)
        baris = ambil(r)
        baris.update({
            "keterangan": M.strategi.loc[st, "keterangan"], "eksposur_ditahan": float(M.strategi.loc[st, "eksposur_ditahan"]),
            "faktor_premi_gempa": float(M.strategi.loc[st, "faktor_premi_gempa"]),
            "target_minimum": M.target_minimum(acuan, st),
            "penurunan_var": 1 - r["L_var_99_5"] / dasar["L_var_99_5"],
            "penurunan_tvar": 1 - r["L_tvar_99_5"] / dasar["L_tvar_99_5"],
            "penurunan_rata": 1 - r["L_rata"] / dasar["L_rata"],
            "laba_dilepas": dasar["laba_bersih_rata"] - r["laba_bersih_rata"],
            "peluang_per_kurva": {kv: M.jalankan(acuan, st, 1.2, kurva=kv)["peluang_di_bawah_100"] for kv in ms.KURVA_TUNGGAL},
        })
        s2[st] = baris
    hasil["soal2"] = s2

    # ---------------- Soal 3: modul risiko ----------------
    s3 = {}
    for kode, st in ((acuan, "S0_dasar"), (acuan, "S7_paketA"), ("M50", "S0_dasar")):
        r = M.jalankan(kode, st, 1.2, rinci=True)
        s3[f"{kode}_{st}"] = {"peluang_di_bawah_100": r["peluang_di_bawah_100"], "mmbr": r["mmbr"], "modul": r["modul"],
                              "ekuitas": r["ekuitas"], "penyangga_20_persen_mmbr": r["penyangga_20_persen_mmbr"],
                              "ambang_seragam": r["ambang_seragam"], "jumlah_tahun_pelanggaran": int(round(r["peluang_di_bawah_100"] * M.n))}
        if (kode, st) == (acuan, "S0_dasar"):
            deret_dasar = r["deret"]
    hasil["soal3"] = s3
    # Rev. 2: kunci konfigurasi acuan soal 3 mengikuti profil_acuan; pembaca tidak perlu menulis kode profil.
    hasil["meta"]["kunci_soal3_acuan"] = f"{acuan}_S0_dasar"
    hasil["meta"]["kunci_soal3"] = list(s3)

    # ---------------- Soal 4: target solvabilitas ----------------
    kisi = [round(x, 2) for x in np.arange(1.0, 4.0001, 0.1)]
    titik = sorted(set(kisi + pt["target_solvabilitas"]["utama"]))
    kurva_target = []
    for s in titik:
        baris = {"target": s}
        for st in STRATEGI_UTAMA:
            baris[st] = M.jalankan(acuan, st, s)["peluang_di_bawah_100"]
        for kv in ms.KURVA_TUNGGAL:
            baris[f"S0_{kv}"] = M.jalankan(acuan, "S0_dasar", s, kurva=kv)["peluang_di_bawah_100"]
        kurva_target.append(baris)
    utama = {}
    for s in pt["target_solvabilitas"]["utama"]:
        utama[str(s)] = {st: ambil(M.jalankan(acuan, st, s)) for st in STRATEGI_UTAMA}
    minimum = {kode: {st: M.target_minimum(kode, st) for st in semua_strategi}
               for kode in ("K80", "K75", "K70", "M40", "M50")}
    hasil["soal4"] = {"kurva_target": kurva_target, "target_utama": utama, "target_minimum": minimum,
                      "target_minimum_per_kurva": {kv: {st: M.target_minimum(acuan, st, kurva=kv) for st in semua_strategi}
                                                   for kv in ms.KURVA_TUNGGAL}}

    # ---------------- Sensitivitas ----------------
    uw, bc = pt["underwriting"], pt["bencana"]
    sn = pt["sensitivitas"]
    M.pasar_untuk("panjang", jendela="panjang")
    for blok in sn["panjang_blok_bulan"]:
        M.pasar_untuk(f"blok{blok}", blok=blok)
    for tenor in sn["tenor_sbn"]:
        M.pasar_untuk(f"tenor{tenor}", tenor_sbn=tenor)
    imbal_acuan = ms.mi.imbal_portofolio(M.varian[acuan][2], M.pasar["bersama"]["imbal"])
    ylt_korelasi = ms.urutkan_berkorelasi(imbal_acuan, M.ylt["campuran"], sn["korelasi_bencana_pasar"],
                                          [pt["meta"]["benih_pasangan"], 2])
    kasus = [
        ("dasar", "Dasar", {}),
        ("kurva_aulady", "Kurva Aulady & Fujimi saja", {"kurva": "aulady"}),
        ("kurva_klaim", "Kurva klaim MAIPARK saja", {"kurva": "klaim"}),
        ("kurva_pager", "Kurva PAGER saja", {"kurva": "pager"}),
        ("E_rendah", f"Eksposur per premi {bc['eksposur_per_premi']['rentang'][0]:.0f}", {"eksposur": bc["eksposur_per_premi"]["rentang"][0]}),
        ("E_tinggi", f"Eksposur per premi {bc['eksposur_per_premi']['rentang'][1]:.0f}", {"eksposur": bc["eksposur_per_premi"]["rentang"][1]}),
        ("klaim_bruto_2024", "Rasio klaim non-bencana 29,5% (pos langsung 2024)", {"rasio_klaim": uw["rasio_klaim_non_bencana"]["uji_rata"]}),
        ("klaim_simpangan_x2", "Simpangan rasio klaim dua kali", {"pengali_simpangan_klaim": uw["rasio_klaim_non_bencana"]["uji_pengali_simpangan"]}),
        ("komisi_15", "Biaya akuisisi 15% premi", {"komisi": uw["komisi"]["uji"]}),
        ("jendela_panjang", "Data pasar 2000-2026", {"pasar": "panjang"}),
        ("blok_3", "Panjang blok 3 bulan", {"pasar": "blok3"}),
        ("blok_12", "Panjang blok 12 bulan", {"pasar": "blok12"}),
        ("tenor_2", "SBN tenor 2 tahun", {"pasar": "tenor2"}),
        ("tenor_10", "SBN tenor 10 tahun", {"pasar": "tenor10"}),
        ("klaim_belum_dibayar", "Separuh klaim bencana masih cadangan akhir tahun", {"porsi_belum_dibayar": bc["porsi_klaim_belum_dibayar_akhir_tahun"]["uji"]}),
        ("potongan_x2", "Potongan jual paksa dua kali", {"pengali_potongan": pt["likuiditas"]["pengali_uji"]}),
        ("korelasi", "Korelasi bencana dan pasar " + str(sn['korelasi_bencana_pasar']).replace(".", ","), {"ylt": ylt_korelasi}),
        ("gabungan_berat", "Gabungan berat: kurva Aulady, eksposur tinggi, akuisisi 15%",
         {"kurva": "aulady", "eksposur": bc["eksposur_per_premi"]["rentang"][1], "komisi": uw["komisi"]["uji"]}),
    ]
    sens = []
    for kunci, label, opsi in kasus:
        baris = {"kasus": kunci, "label": label}
        for st in ("S0_dasar", "S3_batas20", "S7_paketA"):
            r = M.jalankan(acuan, st, 1.2, **opsi)
            baris[f"peluang_{st}"] = r["peluang_di_bawah_100"]
            baris[f"target_minimum_{st}"] = M.target_minimum(acuan, st, **opsi)
        sens.append(baris)
    hasil["sensitivitas"] = sens

    # ---------------- Skenario deterministik ----------------
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    lebar = sk.pivot_table(index=["skenario", "eta", "strategi"], columns="kurva", values="kerugian").reset_index()
    lebar["campuran"] = sum(bobot_kurva[k] * lebar[k] for k in ms.KURVA_TUNGGAL)
    sk_pasar = {"harapan": None}
    sk_pasar.update({k: v for k, v in p05["pasar"]["skenario"].items()})
    kurva_pasar = ms.dp.muat_kurva(p05["pasar"]["kondisi_awal"]["kurva"]["berkas"])
    bobot_acuan = M.varian[acuan][2]
    b = M.neraca_awal(acuan, 1.2)
    lk = pt["likuiditas"]
    potongan = {k: v["nilai"] for k, v in lk["potongan_harga"].items()}
    posisi = {k: b["investasi"] * w for k, w in bobot_acuan.items()}
    siap_cair = M.nilai["kas_dan_bank"] + posisi.get("deposito", 0) + posisi.get("sbn", 0)
    skenario = []
    for _, br in lebar[lebar["strategi"].isin(["S0_dasar", "S3_batas20", "S7_paketA"])].iterrows():
        st = br["strategi"]
        premi = M.jalankan(acuan, st, 1.2)["premi"]
        U = premi - 100 * uw["rasio_klaim_non_bencana"]["rata"] - uw["komisi"]["nilai"] * premi - uw["beban_usaha"]["nilai"]
        for nama_pasar, spek in sk_pasar.items():
            imbal = float(imbal_acuan.mean()) if spek is None else ms.mi.imbal_skenario(spek, kurva_pasar, p05["pasar"], bobot_acuan)[0]
            for kv in ("campuran", "aulady"):
                L = 100 * E * br[kv]
                F, kurang = ms.jual_paksa(np.array([L]), M.nilai["kas_dan_bank"], posisi, potongan, lk["urutan_cair"])
                G = U + b["investasi"] * imbal - L - float(F[0])
                rasio = (b["tingkat_solvabilitas"] + G - uw["pajak"]["nilai"] * max(G, 0)) / b["mmbr"]
                skenario.append({"skenario": br["skenario"], "eta": int(br["eta"]), "strategi": st, "pasar": nama_pasar,
                                 "kurva": kv, "kerugian_fraksi": br[kv], "kerugian": L, "imbal_hasil": imbal,
                                 "laba_sebelum_pajak": G, "rasio_akhir": rasio, "klaim_terhadap_siap_cair": L / siap_cair})
    hasil["skenario"] = skenario

    # ---------------- Deret ringkas untuk gambar ----------------
    r7 = M.jalankan(acuan, "S7_paketA", 1.2, rinci=True)["deret"]
    kuantil = [0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    hasil["sebaran_rasio"] = {"kuantil": kuantil,
                              "S0_dasar": [float(np.quantile(deret_dasar["R"], q)) for q in kuantil],
                              "S7_paketA": [float(np.quantile(r7["R"], q)) for q in kuantil]}
    hasil["komponen_laba"] = {st: {k: {"rata": float(d[k].mean()), "p0_5": float(np.quantile(d[k], 0.005)),
                                       "p99_5": float(np.quantile(d[k], 0.995))} for k in ("U", "I", "L", "F", "G")}
                              for st, d in (("S0_dasar", deret_dasar), ("S7_paketA", r7))}
    np.savez_compressed(ms.DIR_KELUAR / "deret_rasio.npz", S0=deret_dasar["R"].astype("float32"), S7=r7["R"].astype("float32"),
                        L0=deret_dasar["L"].astype("float32"), L7=r7["L"].astype("float32"))

    hasil["meta"]["waktu_detik"] = round(time.time() - mulai, 1)
    ms.DIR_TABEL.mkdir(parents=True, exist_ok=True)
    (ms.DIR_KELUAR / "hasil_terpadu.json").write_text(json.dumps(bersih(hasil), indent=1, ensure_ascii=False), encoding="utf-8")
    tulis_tabel(hasil)
    print(f"selesai dalam {hasil['meta']['waktu_detik']} detik")


def tulis_tabel(h):
    d = ms.DIR_TABEL
    baris = []
    for kode, v in h["soal1"]["varian"].items():
        t, e = v["target_120"], v["ekuitas_sama"]
        baris.append({
            "varian": kode, "profil": v["profil"], "label": v["label"], "patuh_ayd": v["patuh_ayd"],
            "porsi_tidak_diakui": v["porsi_tidak_diakui"], "ketentuan_dilampaui": v["ketentuan_dilampaui"],
            "ekuitas_pada_120": t["S0_dasar"]["ekuitas"], "mmbr_pada_120": t["S0_dasar"]["mmbr"],
            "imbal_hasil_rata": t["S0_dasar"]["imbal_hasil_rata"], "imbal_hasil_riil": t["S0_dasar"]["imbal_hasil_riil"],
            "peluang_S0_pada_120": t["S0_dasar"]["peluang_di_bawah_100"], "peluang_paketA_pada_120": t["S7_paketA"]["peluang_di_bawah_100"],
            "aset_siap_cair": t["S0_dasar"]["aset_siap_cair"],
            "peluang_kurang_likuiditas_S0": t["S0_dasar"]["peluang_kurang_likuiditas"],
            "peluang_kurang_likuiditas_paketA": t["S7_paketA"]["peluang_kurang_likuiditas"],
            "biaya_jual_paksa_var_S0": t["S0_dasar"]["F_var_99_5"],
            "rasio_awal_ekuitas_sama": e["S0_dasar"]["target"], "peluang_S0_ekuitas_sama": e["S0_dasar"]["peluang_di_bawah_100"],
            "peluang_paketA_ekuitas_sama": e["S7_paketA"]["peluang_di_bawah_100"],
            "target_minimum_S0": v["target_minimum"]["S0_dasar"], "target_minimum_paketA": v["target_minimum"]["S7_paketA"],
        })
    pd.DataFrame(baris).to_csv(d / "t1_profil.csv", index=False)

    baris = []
    for st, v in h["soal2"].items():
        baris.append({"strategi": st, "keterangan": v["keterangan"], "eksposur_ditahan": v["eksposur_ditahan"],
                      "premi": v["premi"], "premi_dilepas": v["premi_dilepas"], "L_rata": v["L_rata"],
                      "L_var_99_5": v["L_var_99_5"], "L_tvar_99_5": v["L_tvar_99_5"],
                      "klaim_kejadian_var_99_5": v["klaim_kejadian_var_99_5"], "penurunan_var": v["penurunan_var"],
                      "penurunan_tvar": v["penurunan_tvar"], "laba_bersih_rata": v["laba_bersih_rata"],
                      "laba_dilepas": v["laba_dilepas"], "peluang_pada_120": v["peluang_di_bawah_100"],
                      "galat_baku": v["galat_baku_peluang"], "target_minimum": v["target_minimum"],
                      **{f"peluang_{k}": p for k, p in v["peluang_per_kurva"].items()}})
    pd.DataFrame(baris).to_csv(d / "t2_strategi.csv", index=False)

    baris = []
    for kunci, v in h["soal3"].items():
        for m, x in v["modul"].items():
            baris.append({"konfigurasi": kunci, "modul": m, **x})
    pd.DataFrame(baris).to_csv(d / "t3_modul.csv", index=False)

    pd.DataFrame(h["soal4"]["kurva_target"]).to_csv(d / "t4_target.csv", index=False)
    pd.DataFrame([{"varian": k, **v} for k, v in h["soal4"]["target_minimum"].items()]).to_csv(d / "t4_target_minimum.csv", index=False)
    pd.DataFrame(h["sensitivitas"]).to_csv(d / "t5_sensitivitas.csv", index=False)
    pd.DataFrame(h["skenario"]).to_csv(d / "t6_skenario.csv", index=False)


if __name__ == "__main__":
    main()
