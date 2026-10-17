"""Perancangan solusi berbasis hasil simulasi.

Langkah:
  1. Untuk tiap strategi mitigasi, cari rasio solvabilitas awal terkecil yang memenuhi tiga kendala
     (C1 peluang pada kurva campuran, C2 peluang pada kurva Aulady, C3 skenario megathrust).
  2. Hitung laba ekonomi = laba bersih harapan - biaya modal x ekuitas pada rasio itu.
  3. Pilih calon dengan nilai bersih terbesar; bandingkan dengan keadaan sekarang dan dengan jalan
     "modal saja".
  4. Uraikan rancangan terpilih: peluang menurut target, kepekaan, skenario, kantong likuiditas,
     pemicu solvabilitas, dan arus kas inkremental untuk analisis biaya-manfaat.

Rev. 2:
  - Kendala peluang C1 dan C2 lolos hanya bila batas atas selang Clopper-Pearson eksak 95% tidak melebihi
    ambang 0,5% (meta.aturan_peluang = batas_atas). Target menurut aturan titik (Rev. 1) tetap disimpan pada
    kunci berakhiran `_titik`.
  - Tambahan keluaran: jumlah pelanggaran dan selang untuk tiga jalan, kerugian yang dialihkan ke pemegang
    polis, tabel modul rancangan terpilih, fungsi tujuan alternatif, muatan bencana, dan selang kuantil
    kantong likuiditas. Semua kunci Rev. 1 dipertahankan.

Keluaran: 5_solusi_motera/keluaran/rancangan.json dan tabel CSV.
Pemakaian: python 5_solusi_motera/kode/rancang_solusi.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

DIR_G = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_G.parent / "4_simulasi_terpadu" / "kode"))
import mesin as ms          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
DIR_KELUAR = DIR_G / "keluaran"
RINGKAS = ["target", "investasi", "mmbr", "ekuitas", "premi", "premi_dilepas", "peluang_di_bawah_100",
           "galat_baku_peluang", "peluang_di_bawah_0", "defisit_harapan", "rata_rasio_di_ekor_0_5", "rasio_rata",
           "laba_bersih_rata", "U_rata", "I_rata", "L_rata", "L_var_99_5", "L_tvar_99_5", "klaim_kejadian_var_99_5",
           "aset_siap_cair", "peluang_kurang_likuiditas", "F_var_99_5"]


def bersih(o):
    if isinstance(o, dict):
        return {str(k): bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [bersih(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def main():
    p05, pt = ms.muat_semua()
    ps = yaml.safe_load((DIR_G / "parameter_solusi.yaml").read_text(encoding="utf-8"))
    M = ms.Mesin(p05, pt)
    n = M.n
    acuan = pt["meta"]["profil_acuan"]
    ambang = pt["meta"]["ambang_peluang"]
    aturan = pt["meta"].get("aturan_peluang", "titik")
    tingkat = pt["meta"].get("tingkat_selang", 0.95)
    amb = {"batas_atas": ms.ambang_aturan(pt, n, "batas_atas"), "titik": ms.ambang_aturan(pt, n, "titik")}
    amb_pakai = amb[aturan]
    lain = "titik" if aturan == "batas_atas" else "batas_atas"
    kisi = np.round(np.arange(pt["target_solvabilitas"]["kisi"]["awal"], pt["target_solvabilitas"]["kisi"]["akhir"] + 1e-9,
                              pt["target_solvabilitas"]["kisi"]["langkah"]), 2)
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    k_modal = ps["biaya_modal"]["nilai"]
    bawah = ps["kendala"]["target_paling_rendah"]
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]

    # kerugian skenario uji per strategi (kurva campuran = rata-rata berbobot tiga kurva)
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"])]
    rugi_sken = sk.pivot_table(index="strategi", columns="kurva", values="kerugian")
    rugi_sken["campuran"] = sum(bobot_kurva[k] * rugi_sken[k] for k in ms.KURVA_TUNGGAL)

    def target_skenario(st, pengali=1.0, **opsi):
        pilih = {k: v for k, v in opsi.items() if k in ("eksposur", "rasio_klaim", "komisi")}
        for s in kisi:
            if M.rasio_skenario(acuan, st, float(s), rugi_sken.loc[st, "campuran"] * pengali, **pilih)["rasio_akhir"] >= 1.0:
                return float(s)
        return None

    def target_perlu(st, a=None, **opsi):
        """Rasio awal terkecil yang memenuhi C1, C2, dan C3 pada suatu kasus asumsi."""
        a = amb_pakai if a is None else a
        c1 = M.target_minimum(acuan, st, ambang=a, **opsi)
        c2 = M.target_minimum(acuan, st, ambang=a, **{**opsi, "kurva": "aulady"})
        c3 = target_skenario(st, **opsi)
        return None if None in (c1, c2, c3) else max(bawah, c1, c2, c3)

    def peluang(st, s, kurva):
        return ms.ringkas_peluang(M.jalankan(acuan, st, s, kurva=kurva)["peluang_di_bawah_100"], n, tingkat)

    def nilai(st, s):
        r = M.jalankan(acuan, st, s)
        out = {k: r[k] for k in RINGKAS}
        out["peluang_aulady"] = M.jalankan(acuan, st, s, kurva="aulady")["peluang_di_bawah_100"]
        out["rasio_setelah_megathrust"] = M.rasio_skenario(acuan, st, s, rugi_sken.loc[st, "campuran"])["rasio_akhir"]
        out["kerugian_megathrust"] = 100 * E * rugi_sken.loc[st, "campuran"]
        out["laba_ekonomi"] = r["laba_bersih_rata"] - k_modal * r["ekuitas"]
        # Nilai bersih: laba ekonomi dikurangi defisit harapan pemegang polis (Butsic, 1994; Myers & Read, 2001)
        out["nilai_bersih"] = out["laba_ekonomi"] - r["defisit_harapan"]
        out["laba_ekonomi_uji"] = {str(k): r["laba_bersih_rata"] - k * r["ekuitas"] for k in ps["biaya_modal"]["uji"]}
        out["imbal_ekuitas"] = r["laba_bersih_rata"] / r["ekuitas"]
        return out

    # ---------- 1 dan 2: target yang diperlukan dan laba ekonomi tiap strategi ----------
    calon = {}
    for st in M.strategi.index:
        c3 = target_skenario(st)
        t = {}
        for nama, a in amb.items():
            c1 = M.target_minimum(acuan, st, ambang=a)
            c2 = M.target_minimum(acuan, st, ambang=a, kurva="aulady")
            t[nama] = {"C1": c1, "C2": c2,
                       "perlu": None if None in (c1, c2, c3) else max(bawah, c1, c2, c3),
                       "perlu_12": None if None in (c1, c2) else max(bawah, c1, c2)}
        u, v = t[aturan], t[lain]
        baris = {"keterangan": M.strategi.loc[st, "keterangan"], "eksposur_ditahan": float(M.strategi.loc[st, "eksposur_ditahan"]),
                 "faktor_premi_gempa": float(M.strategi.loc[st, "faktor_premi_gempa"]),
                 "target_C1": u["C1"], "target_C2": u["C2"], "target_C3": c3, "target_perlu": u["perlu"], "target_perlu_tanpa_C3": u["perlu_12"],
                 f"target_C1_{lain}": v["C1"], f"target_C2_{lain}": v["C2"], f"target_perlu_{lain}": v["perlu"],
                 "dikecualikan": ps["dikecualikan"].get(st, "")}
        if u["perlu"] is not None:
            baris["pada_target_perlu"] = nilai(st, u["perlu"])
        if u["perlu_12"] is not None:
            baris["pada_target_tanpa_C3"] = nilai(st, u["perlu_12"])
        if v["perlu"] is not None:
            baris[f"pada_target_perlu_{lain}"] = nilai(st, v["perlu"])
        baris["pada_120"] = nilai(st, 1.2)
        calon[st] = baris

    layak = {st: v for st, v in calon.items() if v["target_perlu"] is not None and not v["dikecualikan"]}
    urut = sorted(layak, key=lambda st: -layak[st]["pada_target_perlu"]["nilai_bersih"])
    terpilih = urut[0]
    s_pilih = layak[terpilih]["target_perlu"]
    layak_lain = {st: v for st, v in calon.items() if v[f"target_perlu_{lain}"] is not None and not v["dikecualikan"]}
    urut_lain = sorted(layak_lain, key=lambda st: -layak_lain[st][f"pada_target_perlu_{lain}"]["nilai_bersih"])
    hasil = {"meta": {"profil": acuan, "biaya_modal": k_modal, "ambang": ambang, "skenario_uji": ps["skenario_uji"],
                      "kendala": ps["kendala"], "satuan": "per 100 premi dicatat", "jumlah_tahun": n,
                      "aturan_peluang": aturan, "tingkat_selang": tingkat,
                      "pelanggaran_terbanyak_batas_atas": ms.pelanggaran_terbanyak(ambang, n, tingkat),
                      "ambang_setara_taksiran_titik": amb,
                      "keterangan_aturan": "C1 dan C2 lolos bila batas atas selang Clopper-Pearson eksak tidak melebihi ambang; kunci *_titik memakai taksiran titik (Rev. 1)"
                      if aturan == "batas_atas" else "C1 dan C2 lolos bila taksiran titik tidak melebihi ambang"},
             "calon": calon, "urutan_nilai_bersih": urut, f"urutan_nilai_bersih_{lain}": urut_lain,
             "terpilih": {"strategi": terpilih, "target": s_pilih}}
    st_l = urut_lain[0]
    hasil[f"terpilih_{lain}"] = {"strategi": st_l, "target": calon[st_l][f"target_perlu_{lain}"],
                                 "keterangan": calon[st_l]["keterangan"], **calon[st_l][f"pada_target_perlu_{lain}"],
                                 "C1": peluang(st_l, calon[st_l][f"target_perlu_{lain}"], "campuran"),
                                 "C2": peluang(st_l, calon[st_l][f"target_perlu_{lain}"], "aulady")}

    # ---------- 3: tiga jalan yang dibandingkan ----------
    jalan = {"sekarang": ("S0_dasar", 1.2), "modal_saja": ("S0_dasar", calon["S0_dasar"]["target_perlu"]),
             "terpilih": (terpilih, s_pilih)}
    hasil["perbandingan"] = {}
    for nama, (st, s) in jalan.items():
        if s is None:
            continue
        d = nilai(st, s)
        d.update({"strategi": st, "modul": M.neraca_awal(acuan, s)["modul"],
                  "C1": peluang(st, s, "campuran"), "C2": peluang(st, s, "aulady")})
        hasil["perbandingan"][nama] = d
    pt_ = hasil["perbandingan"]["terpilih"]
    hasil["terpilih"].update({"keterangan": calon[terpilih]["keterangan"], "C1": pt_["C1"], "C2": pt_["C2"],
                              "C3_rasio_setelah_megathrust": pt_["rasio_setelah_megathrust"],
                              "target_C1": calon[terpilih]["target_C1"], "target_C2": calon[terpilih]["target_C2"],
                              "target_C3": calon[terpilih]["target_C3"],
                              "lolos": {"C1": pt_["C1"]["selang_atas"] <= ambang if aturan == "batas_atas" else pt_["C1"]["peluang"] <= ambang,
                                        "C2": pt_["C2"]["selang_atas"] <= ambang if aturan == "batas_atas" else pt_["C2"]["peluang"] <= ambang,
                                        "C3": pt_["rasio_setelah_megathrust"] >= 1.0}})

    # ---------- 4: uraian rancangan terpilih ----------
    titik = sorted(set([round(x, 2) for x in np.arange(1.0, 3.0001, 0.1)] + [1.2, 1.5, s_pilih]))
    hasil["terpilih"]["kurva_target"] = [
        {"target": s, "peluang": M.jalankan(acuan, terpilih, s)["peluang_di_bawah_100"],
         "peluang_aulady": M.jalankan(acuan, terpilih, s, kurva="aulady")["peluang_di_bawah_100"],
         "rasio_setelah_megathrust": M.rasio_skenario(acuan, terpilih, s, rugi_sken.loc[terpilih, "campuran"])["rasio_akhir"],
         "ekuitas": M.neraca_awal(acuan, s)["ekuitas"]} for s in titik]

    uw, bc, sn = pt["underwriting"], pt["bencana"], pt["sensitivitas"]
    M.pasar_untuk("panjang", jendela="panjang")
    M.pasar_untuk("tenor10", tenor_sbn=10)
    imbal_acuan = ms.mi.imbal_portofolio(M.varian[acuan][2], M.pasar["bersama"]["imbal"])
    ylt_kor = ms.urutkan_berkorelasi(imbal_acuan, M.ylt["campuran"], sn["korelasi_bencana_pasar"], [pt["meta"]["benih_pasangan"], 2])
    kasus = [("Dasar", {}), ("Kurva Aulady & Fujimi saja", {"kurva": "aulady"}),
             ("Eksposur per premi 188", {"eksposur": bc["eksposur_per_premi"]["rentang"][1]}),
             ("Biaya akuisisi 15% premi", {"komisi": uw["komisi"]["uji"]}),
             ("Simpangan rasio klaim dua kali", {"pengali_simpangan_klaim": 2.0}),
             ("Separuh klaim bencana masih cadangan", {"porsi_belum_dibayar": 0.5}),
             ("Korelasi bencana dan pasar 0,25", {"ylt": ylt_kor}),
             ("Data pasar 2000-2026", {"pasar": "panjang"}), ("SBN tenor 10 tahun", {"pasar": "tenor10"}),
             ("Gabungan berat", {"kurva": "aulady", "eksposur": bc["eksposur_per_premi"]["rentang"][1], "komisi": uw["komisi"]["uji"]})]
    hasil["terpilih"]["kepekaan"] = [
        {"kasus": nama,
         "peluang_sekarang": M.jalankan(acuan, "S0_dasar", 1.2, **opsi)["peluang_di_bawah_100"],
         "peluang_terpilih": M.jalankan(acuan, terpilih, s_pilih, **opsi)["peluang_di_bawah_100"],
         "target_minimum_terpilih": M.target_minimum(acuan, terpilih, ambang=amb_pakai, **opsi),
         f"target_minimum_terpilih_{lain}": M.target_minimum(acuan, terpilih, ambang=amb[lain], **opsi)} for nama, opsi in kasus]

    # skenario: semua kejadian, guncangan median dan +1 simpangan baku
    semua = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    lebar = semua.pivot_table(index=["skenario", "eta", "strategi"], columns="kurva", values="kerugian").reset_index()
    lebar["campuran"] = sum(bobot_kurva[k] * lebar[k] for k in ms.KURVA_TUNGGAL)
    sken = []
    for _, b in lebar[lebar["strategi"].isin(["S0_dasar", terpilih])].iterrows():
        s = 1.2 if b["strategi"] == "S0_dasar" else s_pilih
        r = M.rasio_skenario(acuan, b["strategi"], s, b["campuran"])
        sken.append({"skenario": b["skenario"], "eta": int(b["eta"]), "strategi": b["strategi"], "target": s,
                     "kerugian": r["kerugian"], "rasio_akhir": r["rasio_akhir"], "kekurangan_kas": r["kekurangan_kas"]})
    if terpilih == "S0_dasar":        # polis standar terpilih: tambahkan barisnya pada target terpilih
        for _, b in lebar[lebar["strategi"] == "S0_dasar"].iterrows():
            r = M.rasio_skenario(acuan, "S0_dasar", s_pilih, b["campuran"])
            sken.append({"skenario": b["skenario"], "eta": int(b["eta"]), "strategi": "S0_dasar", "target": s_pilih,
                         "kerugian": r["kerugian"], "rasio_akhir": r["rasio_akhir"], "kekurangan_kas": r["kekurangan_kas"]})
    hasil["terpilih"]["skenario"] = sken

    # kantong likuiditas: klaim satu kejadian 1 dalam 200 tahun lawan kas dan deposito tiap varian Konservatif
    rt = M.jalankan(acuan, terpilih, s_pilih, rinci=True)
    kk = np.sort(rt["deret"]["klaim_kejadian"])
    g = 1.96 * np.sqrt(n * 0.995 * 0.005)
    q_lo, q_hi = float(kk[int(np.floor(n * 0.995 - g))]), float(kk[min(n - 1, int(np.ceil(n * 0.995 + g)))])
    likuid = {}
    for kode in ("K80", "K75", "K70"):
        b = M.neraca_awal(kode, s_pilih)
        dep = b["investasi"] * M.varian[kode][2].get("deposito", 0.0)
        kas_dep = M.nilai["kas_dan_bank"] + dep
        likuid[kode] = {"kas": M.nilai["kas_dan_bank"], "deposito": dep, "kas_dan_deposito": kas_dep,
                        "klaim_kejadian_var_99_5": rt["klaim_kejadian_var_99_5"],
                        "cakupan": kas_dep / rt["klaim_kejadian_var_99_5"],
                        "klaim_kejadian_selang95": [q_lo, q_hi], "cakupan_selang95": [kas_dep / q_hi, kas_dep / q_lo],
                        "peluang_klaim_kejadian_melebihi_kas_deposito": float((rt["deret"]["klaim_kejadian"] > kas_dep).mean()),
                        "bobot_sbn": M.varian[kode][2].get("sbn", 0.0)}
    hasil["terpilih"]["kantong_likuiditas"] = likuid
    # Aturan kantong likuiditas: di antara varian Konservatif yang cakupannya paling sedikit 100%, pilih porsi SBN terbesar;
    # bila tidak ada yang mencapai 100%, pilih cakupan terbesar.
    cukup = [k for k, v in likuid.items() if v["cakupan"] >= 1.0]
    hasil["terpilih"]["profil_menurut_kantong_likuiditas"] = (max(cukup, key=lambda k: likuid[k]["bobot_sbn"]) if cukup
                                                              else max(likuid, key=lambda k: likuid[k]["cakupan"]))
    hasil["terpilih"]["profil_acuan_sama_dengan_rekomendasi"] = hasil["terpilih"]["profil_menurut_kantong_likuiditas"] == acuan

    # pemicu solvabilitas: peluang jatuh di bawah 100% bila tahun dimulai dari berbagai rasio
    hasil["terpilih"]["pemicu"] = [{"rasio_awal": s, "peluang": M.jalankan(acuan, terpilih, s)["peluang_di_bawah_100"],
                                    "peluang_sekarang": M.jalankan(acuan, "S0_dasar", s)["peluang_di_bawah_100"]}
                                   for s in (1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0)]

    # tabel modul rancangan terpilih (ukuran sama dengan soal 3 di hasil_terpadu.json)
    hasil["terpilih"]["modul"] = rt["modul"]
    hasil["terpilih"]["penyangga_20_persen_mmbr"] = rt["penyangga_20_persen_mmbr"]
    hasil["terpilih"]["ambang_seragam"] = rt["ambang_seragam"]

    # ---------- kerugian yang dialihkan ke pemegang polis ----------
    # Selisih kerugian polis standar dan strategi terpilih pada tahun simulasi yang sama (kurva campuran).
    skala = ps["skala_rupiah"]["premi_harta_benda_miliar"] / 100.0      # Rp miliar per satuan "per 100 premi"
    ylt = M.ylt_untuk("campuran")
    L0, Ls = 100.0 * E * ylt["S0_dasar"][0], 100.0 * E * ylt[terpilih][0]
    geser = L0 - Ls
    ekor = L0 >= np.quantile(L0, 0.995)
    tahan = float(M.strategi.loc[terpilih, "eksposur_ditahan"])
    hasil["kerugian_dialihkan"] = {
        "pembanding": "S0_dasar", "strategi": terpilih, "eksposur_ditahan": tahan,
        "murni_di_atas_batas": bool(abs(tahan - 1.0) < 1e-12),
        "rata_per_tahun": float(geser.mean()), "rata_per_tahun_miliar": float(geser.mean() * skala),
        "rata_ekor_0_5": float(geser[ekor].mean()), "rata_ekor_0_5_miliar": float(geser[ekor].mean() * skala),
        "tvar_polis_standar": float(L0[ekor].mean()), "rata_strategi_pada_tahun_ekor_polis_standar": float(Ls[ekor].mean()),
        "porsi_rata": float(geser.mean() / L0.mean()), "porsi_ekor_0_5": float(geser[ekor].mean() / L0[ekor].mean()),
        "tidak_negatif_di_semua_tahun": bool((geser >= -1e-9).all()),
        "premi_dilepas": pt_["premi_dilepas"], "premi_dilepas_miliar": pt_["premi_dilepas"] * skala,
        "catatan": "Kerugian fisik yang tidak lagi dibayar penanggung karena batas ganti rugi; menjadi beban tertanggung."}

    # ---------- fungsi tujuan alternatif ----------
    horizon = ps["horizon_tahun"]
    awal = sum(v["nilai"] for v in ps["biaya_implementasi"]["awal"].values())
    tahunan = sum(v["nilai"] for v in ps["biaya_implementasi"]["tahunan"].values())

    def biaya_per_100(k, kali):
        return kali * (tahunan + awal * k / (1 - (1 + k) ** -horizon)) / skala

    def nilai_alt(st, k, pakai_defisit, kali):
        d = layak[st]["pada_target_perlu"]
        biaya = 0.0 if st == "S0_dasar" else biaya_per_100(k, kali)
        return d["laba_bersih_rata"] - k * d["ekuitas"] - pakai_defisit * d["defisit_harapan"] - biaya

    alt = []
    for nama, k, pd_, kali in [("dasar", k_modal, 1, 0.0), ("biaya_modal_10", 0.10, 1, 0.0), ("biaya_modal_16", 0.16, 1, 0.0),
                               ("tanpa_suku_defisit", k_modal, 0, 0.0), ("dengan_biaya_pelaksanaan", k_modal, 1, 1.0),
                               ("biaya_pelaksanaan_x2", k_modal, 1, 2.0), ("tanpa_suku_defisit_dengan_biaya_pelaksanaan", k_modal, 0, 1.0)]:
        nb = {st: nilai_alt(st, k, pd_, kali) for st in layak}
        u2 = sorted(nb, key=lambda st: -nb[st])
        alt.append({"kasus": nama, "biaya_modal": k, "suku_defisit": pd_, "pengali_biaya_pelaksanaan": kali,
                    "biaya_pelaksanaan_per_100_premi": biaya_per_100(k, kali), "terpilih": u2[0], "target_terpilih": layak[u2[0]]["target_perlu"],
                    "nilai_terpilih": nb[u2[0]], "kedua": u2[1], "nilai_kedua": nb[u2[1]],
                    "nilai_strategi_terpilih_dasar": nb[terpilih], "nilai_modal_saja": nb.get("S0_dasar"),
                    "selisih_terhadap_modal_saja": nb[terpilih] - nb["S0_dasar"] if "S0_dasar" in nb else None})
    hasil["fungsi_tujuan_alternatif"] = alt

    # ---------- muatan bencana: seluruh kerugian bencana dikalikan faktor ----------
    muatan = []
    for f in (1.0, 1.07, 1.25, 1.5):
        y_c = {st: (j * f, m * f) for st, (j, m) in M.ylt_untuk("campuran").items()}
        y_a = {st: (j * f, m * f) for st, (j, m) in M.ylt_untuk("aulady").items()}
        for label, st, s in (("polis_standar", "S0_dasar", 1.2), ("terpilih", terpilih, s_pilih)):
            c1, c2 = M.target_minimum(acuan, st, ambang=amb_pakai, ylt=y_c), M.target_minimum(acuan, st, ambang=amb_pakai, ylt=y_a)
            c3 = target_skenario(st, pengali=f)
            muatan.append({"faktor": f, "jalan": label, "strategi": st, "target": s,
                           "peluang": M.jalankan(acuan, st, s, ylt=y_c)["peluang_di_bawah_100"],
                           "peluang_aulady": M.jalankan(acuan, st, s, ylt=y_a)["peluang_di_bawah_100"],
                           "rasio_setelah_megathrust": M.rasio_skenario(acuan, st, s, rugi_sken.loc[st, "campuran"] * f)["rasio_akhir"],
                           "target_C1": c1, "target_C2": c2, "target_C3": c3,
                           "target_perlu": None if None in (c1, c2, c3) else max(bawah, c1, c2, c3)})
    hasil["muatan_bencana"] = {"keterangan": "1,07 = klaim erupsi terhadap klaim gempa pada daftar kejadian terbesar MAIPARK; 1,25 dan 1,5 = bahaya sekunder yang tidak dimodelkan",
                               "aturan_peluang": aturan, "kasus": muatan}

    # ---------- arus kas inkremental untuk analisis biaya-manfaat ----------
    p = hasil["perbandingan"]
    hasil["biaya_manfaat"] = {
        "skala_miliar_per_satuan": skala, "horizon_tahun": ps["horizon_tahun"], "biaya_modal": k_modal,
        "biaya_implementasi": ps["biaya_implementasi"],
        "terhadap_sekarang": {
            "laba_dilepas": p["sekarang"]["laba_bersih_rata"] - p["terpilih"]["laba_bersih_rata"],
            "tambahan_ekuitas": p["terpilih"]["ekuitas"] - p["sekarang"]["ekuitas"],
            "penurunan_rata_kerugian": p["sekarang"]["L_rata"] - p["terpilih"]["L_rata"],
            "penurunan_var": p["sekarang"]["L_var_99_5"] - p["terpilih"]["L_var_99_5"],
            "penurunan_tvar": p["sekarang"]["L_tvar_99_5"] - p["terpilih"]["L_tvar_99_5"],
            "penurunan_defisit_harapan": p["sekarang"]["defisit_harapan"] - p["terpilih"]["defisit_harapan"],
        },
    }
    if "modal_saja" in p:
        hasil["biaya_manfaat"]["terhadap_modal_saja"] = {
            "ekuitas_dihemat": p["modal_saja"]["ekuitas"] - p["terpilih"]["ekuitas"],
            "laba_dilepas": p["modal_saja"]["laba_bersih_rata"] - p["terpilih"]["laba_bersih_rata"],
            "selisih_laba_ekonomi": p["terpilih"]["laba_ekonomi"] - p["modal_saja"]["laba_ekonomi"],
        }

    # Kepekaan perbandingan dua jalan: target yang diperlukan dihitung ulang pada tiap kasus asumsi
    ulang = []
    for nama, opsi in [("Dasar", {}), ("Eksposur per premi 122", {"eksposur": bc["eksposur_per_premi"]["rentang"][0]}),
                       ("Eksposur per premi 188", {"eksposur": bc["eksposur_per_premi"]["rentang"][1]}),
                       ("Biaya akuisisi 15% premi", {"komisi": uw["komisi"]["uji"]}),
                       ("Rasio klaim non-bencana 29,5%", {"rasio_klaim": uw["rasio_klaim_non_bencana"]["uji_rata"]})]:
        baris = {"kasus": nama}
        for label, st in (("modal_saja", "S0_dasar"), ("terpilih", terpilih)):
            s = target_perlu(st, **opsi)
            baris[f"target_{label}"] = s
            if s is not None:
                r = M.jalankan(acuan, st, s, **opsi)
                baris.update({f"ekuitas_{label}": r["ekuitas"], f"laba_{label}": r["laba_bersih_rata"],
                              f"defisit_{label}": r["defisit_harapan"], f"peluang_{label}": r["peluang_di_bawah_100"]})
        ulang.append(baris)
    hasil["biaya_manfaat"]["kasus_ulang"] = ulang

    DIR_KELUAR.mkdir(parents=True, exist_ok=True)
    (DIR_KELUAR / "rancangan.json").write_text(json.dumps(bersih(hasil), indent=1, ensure_ascii=False), encoding="utf-8")
    baris = []
    for st, v in calon.items():
        d = v.get("pada_target_perlu") or {}
        dl = v.get(f"pada_target_perlu_{lain}") or {}
        baris.append({"strategi": st, "keterangan": v["keterangan"], "dikecualikan": bool(v["dikecualikan"]),
                      "target_C1": v["target_C1"], "target_C2": v["target_C2"], "target_C3": v["target_C3"],
                      "target_perlu": v["target_perlu"], "ekuitas": d.get("ekuitas"), "laba_bersih": d.get("laba_bersih_rata"),
                      "laba_ekonomi": d.get("laba_ekonomi"), "nilai_bersih": d.get("nilai_bersih"), "imbal_ekuitas": d.get("imbal_ekuitas"),
                      "peluang": d.get("peluang_di_bawah_100"), "peluang_aulady": d.get("peluang_aulady"),
                      "rasio_setelah_megathrust": d.get("rasio_setelah_megathrust"), "premi_dilepas": d.get("premi_dilepas"),
                      "defisit_harapan": d.get("defisit_harapan"), "L_tvar_99_5": d.get("L_tvar_99_5"),
                      "laba_ekonomi_pada_120": v["pada_120"]["laba_ekonomi"], "peluang_pada_120": v["pada_120"]["peluang_di_bawah_100"],
                      f"target_C1_{lain}": v[f"target_C1_{lain}"], f"target_C2_{lain}": v[f"target_C2_{lain}"],
                      f"target_perlu_{lain}": v[f"target_perlu_{lain}"], f"ekuitas_{lain}": dl.get("ekuitas"), f"nilai_bersih_{lain}": dl.get("nilai_bersih")})
    pd.DataFrame(baris).to_csv(DIR_KELUAR / "calon_strategi.csv", index=False)
    print(f"aturan peluang: {aturan} (pelanggaran paling banyak {hasil['meta']['pelanggaran_terbanyak_batas_atas']} dari {n})")
    print("terpilih:", terpilih, "pada target", s_pilih, f"| aturan {lain}:", st_l, "pada target", calon[st_l][f"target_perlu_{lain}"])
    print(pd.DataFrame(baris)[["strategi", "target_perlu", "ekuitas", "laba_bersih", "laba_ekonomi", "defisit_harapan",
                               "nilai_bersih", "L_tvar_99_5", f"target_perlu_{lain}", f"nilai_bersih_{lain}"]].round(3).sort_values("nilai_bersih", ascending=False).head(9).to_string(index=False))
    print(pd.DataFrame(ulang).round(3).to_string(index=False))
    print(pd.DataFrame(alt)[["kasus", "terpilih", "target_terpilih", "nilai_terpilih", "nilai_modal_saja", "selisih_terhadap_modal_saja"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
