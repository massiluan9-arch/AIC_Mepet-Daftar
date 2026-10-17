"""Rev. 3: Radar Solvabilitas Gempa dan Tangga Modal pada polis standar.

Menghitung, dengan mesin neraca yang sama (profil acuan, polis standar):
  1. Tiga indikator radar pada tiap anak tangga rasio awal: peluang pelanggaran (kurva campuran dan kurva
     Aulady & Fujimi, dengan batas atas selang Clopper-Pearson), rasio setelah skenario megathrust, dan
     cakupan likuiditas atas klaim satu kejadian 1 dalam 200 tahun.
  2. Warna lampu tiap anak tangga dan perkiraan STATIS lama pembentukan ekuitas dari laba ditahan
     (selisih ekuitas dibagi laba bersih harapan setahun; bukan simulasi multitahun).
  3. Biaya ekonomi tangga modal terhadap keadaan sekarang dan pembanding terhadap alternatif batas ganti rugi.
  4. Anak tangga puncak pada kasus kepekaan struktural (dari kepekaan_struktural.csv).

Tidak ada asumsi baru selain yang sudah ada di parameter_solusi.yaml; biaya radar = biaya pelaksanaan Rev. 2
tanpa pos penyesuaian produk (polis tidak diubah).
Keluaran: 5_solusi_motera/keluaran/radar_tangga.json
Pemakaian: python 5_solusi_motera/kode/radar_tangga.py   (setelah rancang_solusi.py dan hitung_ulang_excel.py)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

DIR_G = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_G.parent / "4_simulasi_terpadu" / "kode"))
import mesin as ms          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
DIR_KELUAR = DIR_G / "keluaran"
ST = "S0_dasar"


def main():
    p05, pt = ms.muat_semua()
    ps = yaml.safe_load((DIR_G / "parameter_solusi.yaml").read_text(encoding="utf-8"))
    r = json.loads((DIR_KELUAR / "rancangan.json").read_text(encoding="utf-8"))
    x = json.loads((DIR_KELUAR / "hasil_excel.json").read_text(encoding="utf-8"))
    M = ms.Mesin(p05, pt)
    n = M.n
    acuan = pt["meta"]["profil_acuan"]
    tingkat = pt["meta"].get("tingkat_selang", 0.95)
    ambang = pt["meta"]["ambang_peluang"]
    k_modal = ps["biaya_modal"]["nilai"]
    horizon = ps["horizon_tahun"]
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    sk = sk[(sk["skenario"] == ps["skenario_uji"]["nama"]) & (sk["eta"] == ps["skenario_uji"]["eta"]) & (sk["strategi"] == ST)]
    rugi = sum(bobot_kurva[k] * float(sk[sk["kurva"] == k]["kerugian"].iloc[0]) for k in ms.KURVA_TUNGGAL)
    kas = M.nilai["kas_dan_bank"]
    cal = r["calon"][ST]

    def keadaan(s, kode=acuan):
        a = M.jalankan(kode, ST, s)
        b = M.jalankan(kode, ST, s, kurva="aulady")
        c1 = ms.ringkas_peluang(a["peluang_di_bawah_100"], n, tingkat)
        c2 = ms.ringkas_peluang(b["peluang_di_bawah_100"], n, tingkat)
        mega = M.rasio_skenario(kode, ST, s, rugi)["rasio_akhir"]
        bobot = M.varian[kode][2]
        deposito, sbn = a["investasi"] * bobot.get("deposito", 0.0), a["investasi"] * bobot.get("sbn", 0.0)
        klaim = a["klaim_kejadian_var_99_5"]
        lolos = {"peluang_campuran": c1["selang_atas"] <= ambang, "peluang_aulady": c2["selang_atas"] <= ambang,
                 "megathrust": mega >= 1.0, "likuiditas": (kas + deposito + sbn) >= klaim}
        return {"target": s, "profil": kode, "ekuitas": a["ekuitas"], "mmbr": a["mmbr"], "investasi": a["investasi"],
                "laba_bersih_rata": a["laba_bersih_rata"], "defisit_harapan": a["defisit_harapan"],
                "C1": c1, "C2": c2, "rasio_setelah_megathrust": mega, "klaim_kejadian_var_99_5": klaim,
                "kas_dan_deposito": kas + deposito, "kas_deposito_sbn": kas + deposito + sbn,
                "cakupan_kas_deposito": (kas + deposito) / klaim, "cakupan_kas_deposito_sbn": (kas + deposito + sbn) / klaim,
                "peluang_klaim_kejadian_melebihi_kas_deposito": a.get("peluang_kurang_likuiditas"),
                "lolos": lolos, "jumlah_indikator_lolos": sum(lolos.values()),
                "lampu": "hijau" if all(lolos.values()) else "kuning"}

    anak = [("Sekarang", 1.2), ("Anak tangga 1: lolos pada kurva campuran (C1)", cal["target_C1"]),
            ("Anak tangga 2: lolos pada kurva terberat (C2)", cal["target_C2"]),
            ("Anak tangga 3: tahan skenario megathrust (C3)", cal["target_C3"])]
    tangga = []
    dasar = keadaan(1.2)
    for nama, s in anak:
        d = keadaan(float(s))
        d["nama"] = nama
        d["tambahan_ekuitas"] = d["ekuitas"] - dasar["ekuitas"]
        # perkiraan statis: laba bersih harapan pada keadaan sekarang, seluruhnya ditahan, tanpa tahun buruk
        d["tahun_statis"] = d["tambahan_ekuitas"] / dasar["laba_bersih_rata"]
        d["tahun_statis_laba_di_target"] = d["tambahan_ekuitas"] / d["laba_bersih_rata"]
        tangga.append(d)
    puncak = tangga[-1]
    kantong = {kode: {k: keadaan(puncak["target"], kode)[k] for k in ("kas_dan_deposito", "cakupan_kas_deposito", "cakupan_kas_deposito_sbn",
                                                                      "klaim_kejadian_var_99_5")} for kode in ("K80", "K75", "K70")}

    # ---- biaya ekonomi tangga modal terhadap keadaan sekarang (per 100 premi dan Rp miliar pada premi Rp1 triliun)
    skala = ps["skala_rupiah"]["premi_harta_benda_miliar"] / 100.0
    anuitas = sum(1 / (1 + k_modal) ** t for t in range(1, horizon + 1))
    b = ps["biaya_implementasi"]
    awal = sum(v["nilai"] for kk, v in b["awal"].items() if kk != "penyesuaian_produk_dan_pelaporan")
    tahunan = sum(v["nilai"] for v in b["tahunan"].values())
    tambah_laba = puncak["laba_bersih_rata"] - dasar["laba_bersih_rata"]
    biaya_modal_tahun = k_modal * puncak["tambahan_ekuitas"]
    ekonomi = {
        "biaya_modal": k_modal, "horizon_tahun": horizon, "anuitas": anuitas,
        "tambahan_ekuitas_miliar": puncak["tambahan_ekuitas"] * skala,
        "biaya_modal_atas_tambahan_ekuitas_miliar": biaya_modal_tahun * skala,
        "tambahan_laba_bersih_miliar": tambah_laba * skala,
        "defisit_dihindari_miliar": (dasar["defisit_harapan"] - puncak["defisit_harapan"]) * skala,
        "biaya_radar_awal_miliar": awal, "biaya_radar_tahunan_miliar": tahunan,
        "biaya_keamanan_bersih_per_tahun_miliar": (biaya_modal_tahun - tambah_laba) * skala + tahunan,
        "biaya_keamanan_terhadap_premi": ((biaya_modal_tahun - tambah_laba) * skala + tahunan) / ps["skala_rupiah"]["premi_harta_benda_miliar"],
        "nilai_kini_biaya_radar_miliar": awal + tahunan * anuitas,
        # alternatif batas ganti rugi (Rev. 2) terhadap tangga modal, keduanya memakai radar:
        # NPV Rev. 2 membebankan seluruh biaya pelaksanaan hanya ke alternatif batas; biaya radar yang sama dikembalikan.
        "npv_alternatif_batas_terhadap_tangga_perusahaan_miliar": x["npv_perusahaan_miliar"] + awal + tahunan * anuitas,
        "npv_alternatif_batas_terhadap_tangga_diperluas_miliar": x["npv_diperluas_miliar"] + awal + tahunan * anuitas,
        "premi_dilepas_alternatif_batas_miliar": x["premi_tidak_dibayar_tertanggung_miliar"],
        "kerugian_dialihkan_rata_alternatif_batas_miliar": x["kerugian_dialihkan_rata_miliar"],
        "kerugian_dialihkan_ekor_alternatif_batas_miliar": x["kerugian_dialihkan_ekor_0_5_miliar"],
    }

    # ---- anak tangga puncak pada kasus struktural (ekuitas dari neraca dasar; laba dari kasus dasar)
    ks = pd.read_csv(DIR_KELUAR / "kepekaan_struktural.csv")
    struktural = []
    for _, z in ks.iterrows():
        s = float(z["polis_standar_target_perlu_batas_atas"])
        eku = M.neraca_awal(acuan, s)["ekuitas"]
        struktural.append({"kasus": z["kasus"], "target_C1": float(z["polis_standar_target_C1_batas_atas"]),
                           "target_C2": float(z["polis_standar_target_C2_batas_atas"]), "target_C3": float(z["polis_standar_target_C3"]),
                           "target_puncak": s, "ekuitas": eku, "tahun_statis": (eku - dasar["ekuitas"]) / dasar["laba_bersih_rata"]})
    mb = [z for z in r["muatan_bencana"]["kasus"] if z["jalan"] == "polis_standar"]
    muatan = [{"faktor": z["faktor"], "target_puncak": z["target_perlu"],
               "tahun_statis": (M.neraca_awal(acuan, float(z["target_perlu"]))["ekuitas"] - dasar["ekuitas"]) / dasar["laba_bersih_rata"]} for z in mb]

    hasil = {"meta": {"profil": acuan, "strategi": ST, "jumlah_tahun": n, "ambang": ambang, "aturan_peluang": "batas_atas",
                      "catatan": "tahun_statis = tambahan ekuitas dibagi laba bersih harapan setahun; bukan simulasi multitahun. "
                                 "Indikator likuiditas hijau bila kas, deposito, dan nominal SBN menutup klaim satu kejadian 1 dalam 200 tahun; "
                                 "cakupan kas dan deposito saja dilaporkan terpisah."},
             "tangga": tangga, "kantong_likuiditas_di_puncak": kantong, "ekonomi": ekonomi, "struktural": struktural, "muatan": muatan,
             "kerugian_megathrust": 100 * E * rugi}
    (DIR_KELUAR / "radar_tangga.json").write_text(json.dumps(ms_bersih(hasil), indent=1, ensure_ascii=False), encoding="utf-8")
    for d in tangga:
        print(f"{d['nama'][:48]:50s} s={d['target']:.2f} eku={d['ekuitas']:.2f} C1={d['C1']['jumlah_pelanggaran']} C2={d['C2']['jumlah_pelanggaran']} "
              f"mega={d['rasio_setelah_megathrust']:.3f} kasdep={d['cakupan_kas_deposito']:.3f} +sbn={d['cakupan_kas_deposito_sbn']:.3f} "
              f"lampu={d['lampu']} thn={d['tahun_statis']:.2f}/{d['tahun_statis_laba_di_target']:.2f}")
    print({k: round(v, 3) for k, v in ekonomi.items()})
    print("kantong puncak:", {k: round(v["cakupan_kas_deposito"], 3) for k, v in kantong.items()})
    print([(z["kasus"][:28], z["target_puncak"], round(z["tahun_statis"], 2)) for z in struktural])
    print([(z["faktor"], z["target_puncak"], round(z["tahun_statis"], 2)) for z in muatan])


def ms_bersih(o):
    import numpy as np
    if isinstance(o, dict):
        return {str(k): ms_bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [ms_bersih(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


if __name__ == "__main__":
    main()
