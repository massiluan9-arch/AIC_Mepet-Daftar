"""Menjalankan analisis hasil investasi dan MMBR, lalu menulis keluaran/hasil.json dan tabel CSV.

Pemakaian: python kode/jalankan.py [jumlah_tahun]
Model kerugian bencana belum dijalankan di sini; butir yang menunggunya ditandai pada hasil.json.
"""
import json
import sys

import numpy as np
import pandas as pd

import data_pasar as dp
import mmbr as mm
import model_investasi as mi
import rekonstruksi_industri as ri
from umum import BERKAS_HASIL, DIR_TABEL, daftar_varian, muat_parameter

KUNCI_RINGKAS = ["rata", "simpangan", "var_99_5", "tvar_99_5", "peluang_negatif", "rata_riil"]


def _bersih(o):
    """Mengubah tipe numpy menjadi tipe bawaan agar dapat ditulis sebagai JSON."""
    if isinstance(o, dict):
        return {str(k): _bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_bersih(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def _rasio_akhir(b, r):
    """Rasio solvabilitas setahun kemudian bila hanya hasil investasi yang bergerak."""
    akhir = (b["tingkat_solvabilitas"] + b["investasi"] * r) / b["mmbr"]
    return {"rata": float(akhir.mean()), "p0_5": float(np.quantile(akhir, 0.005)),
            "p5": float(np.quantile(akhir, 0.05)),
            "peluang_di_bawah_100": float((akhir < 1.0).mean()),
            "peluang_di_bawah_120": float((akhir < 1.2).mean())}


def main(jumlah_tahun=None):
    par = muat_parameter()
    reg, profil, neraca, pasar = par["regulasi"], par["profil"], par["neraca_dasar"], par["pasar"]
    varian = daftar_varian(profil)
    bs = pasar["bootstrap"]
    n_tahun = jumlah_tahun or bs["jumlah_tahun"]
    blok = bs["panjang_blok_bulan"]
    awal = pasar["kondisi_awal"]
    d0, inflasi = awal["bunga_deposito_1_bulan"]["nilai"], awal["inflasi_tahunan"]["nilai"]
    ins = pasar["instrumen"]

    def rng(i):
        return np.random.default_rng([bs["benih"], i])

    # ---------- 1. Data ----------
    kurva = dp.muat_kurva(awal["kurva"]["berkas"])
    deret = dp.muat_deret()
    ch = dp.perubahan_bulanan(deret)
    bersama = dp.jendela_bersama(ch, *bs["jendela_bersama"])
    panjang, info_imputasi = dp.jendela_panjang(ch, bersama, *bs["jendela_panjang"], rng(1))
    hasil = {"meta": {
        "judul": "Model hasil investasi dan perhitungan MMBR PT Aktu Proteksi",
        "tanggal_kondisi_awal": str(pasar["meta"]["tanggal_kondisi_awal"]),
        "jumlah_tahun_simulasi": n_tahun, "benih": bs["benih"], "panjang_blok_bulan": blok,
        "satuan_neraca": neraca["meta"]["satuan"],
        "satuan_imbal_hasil": "desimal per tahun, sebelum pajak",
        "ditahan": ["model kerugian bencana L(m)", "hasil underwriting non-bencana U",
                    "peluang pelanggaran gabungan P(R<100%)", "cadangan bencana menurut Pasal 28 ayat (7)"],
    }}
    hasil["data"] = {
        "deskriptif": dp.deskriptif(deret, bersama),
        "kurva": kurva.to_dict(orient="records"),
        "jendela": {"bersama": {"awal": bersama["bulan"].iloc[0], "akhir": bersama["bulan"].iloc[-1],
                                "bulan": len(bersama)},
                    "panjang": {"awal": panjang["bulan"].iloc[0], "akhir": panjang["bulan"].iloc[-1],
                                "bulan": len(panjang), **info_imputasi}},
        "kondisi_awal": {
            "sbn_2": mi.interp_kurva(kurva, "sbn", 2), "sbn_5": mi.interp_kurva(kurva, "sbn", 5),
            "sbn_10": mi.interp_kurva(kurva, "sbn", 10),
            "korporasi_AAA_3": mi.interp_kurva(kurva, "AAA", 3), "korporasi_AA_3": mi.interp_kurva(kurva, "AA", 3),
            "deposito_1_bulan": d0, "inflasi": inflasi, "bi_rate": awal["bi_rate"]["nilai"],
        },
    }

    # ---------- 2. Faktor pasar dan imbal hasil instrumen ----------
    faktor = {"bersama": mi.bootstrap_faktor(bersama, n_tahun, blok, d0, rng(10)),
              "panjang": mi.bootstrap_faktor(panjang, n_tahun, blok, d0, rng(11))}
    seragam = rng(20).random((n_tahun, ins["korporasi"]["jumlah_emiten"]))
    R = {j: mi.imbal_instrumen(f, kurva, pasar, seragam) for j, f in faktor.items()}

    # Uji kewajaran bootstrap: perubahan 12 bulan hasil simulasi lawan jendela bergulir historis.
    j12 = deret[(deret["bulan"] >= "2012-01") & (deret["bulan"] <= "2024-12")]
    dy_hist = j12["y10"].diff(12)
    r_hist = j12["lq45"] / j12["lq45"].shift(12) - 1
    fb = faktor["bersama"]
    hasil["validasi_bootstrap"] = {
        "dy10_simpangan": {"simulasi": float(fb["dy10"].std() * 100), "historis": float(dy_hist.std())},
        "dy10_p95": {"simulasi": float(np.quantile(fb["dy10"], 0.95) * 100), "historis": float(dy_hist.quantile(0.95))},
        "dy10_p5": {"simulasi": float(np.quantile(fb["dy10"], 0.05) * 100), "historis": float(dy_hist.quantile(0.05))},
        "saham_simpangan": {"simulasi": float(fb["saham"].std()), "historis": float(r_hist.std())},
        "saham_p5": {"simulasi": float(np.quantile(fb["saham"], 0.05)), "historis": float(r_hist.quantile(0.05))},
        "korelasi_dy10_saham": {"simulasi": float(np.corrcoef(fb["dy10"], fb["saham"])[0, 1]),
                                "historis": float(dy_hist.corr(r_hist))},
        "catatan": "Historis = jendela 12 bulan bergulir 2012-2024 (saling tumpang tindih); satuan dy10 poin persentase.",
    }

    def stat_instrumen(Rj, i):
        return {k: mi.statistik(v, inflasi, bs["jumlah_kelompok_galat_baku"], rng(i)) for k, v in Rj.items()}

    hasil["instrumen"] = {"bersama": stat_instrumen(R["bersama"], 30), "panjang": stat_instrumen(R["panjang"], 31)}
    hasil["instrumen"]["konfigurasi_dasar"] = {
        "tenor_sbn": ins["sbn"]["tenor_dasar"], "tenor_korporasi": ins["korporasi"]["tenor"],
        "peringkat_korporasi": ins["korporasi"]["peringkat_dasar"],
        "klasifikasi": pasar["klasifikasi_akuntansi"]["dasar"],
        "jumlah_emiten": ins["korporasi"]["jumlah_emiten"],
    }

    # ---------- 3. Imbal hasil per varian profil ----------
    imbal = {j: {kode: mi.imbal_portofolio(bobot, R[j]) for kode, _, _, bobot in varian} for j in R}
    hasil["profil"] = {}
    for i, (kode, nama, label, bobot) in enumerate(varian):
        hasil["profil"][kode] = {
            "profil": nama, "label": label, "bobot": bobot,
            "imbal_hasil": {j: mi.statistik(imbal[j][kode], inflasi, bs["jumlah_kelompok_galat_baku"], rng(40 + i))
                            for j in imbal},
        }

    # Sensitivitas: satu hal diubah tiap kali, jendela bersama.
    sens_spec = {
        "tenor_sbn_2": {"tenor_sbn": 2},
        "tenor_sbn_10": {"tenor_sbn": 10},
        "korporasi_AAA": {"peringkat": "AAA"},
        "gagal_bayar_x3": {"pengali_gagal": 3.0},
        "selisih_melebar": {"beta_selisih": pasar["selisih_kredit"]["beta_uji"]},
        "dimiliki_hingga_jatuh_tempo": {"klasifikasi": "dimiliki_hingga_jatuh_tempo"},
        "tanpa_dividen": {"imbal_dividen": 0.0},
    }
    imbal_sens = {}
    for nama_s, kw in sens_spec.items():
        Rs = mi.imbal_instrumen(faktor["bersama"], kurva, pasar, seragam, **kw)
        imbal_sens[nama_s] = {kode: mi.imbal_portofolio(bobot, Rs) for kode, _, _, bobot in varian}
    for b_uji in bs["panjang_blok_uji"]:
        fu = mi.bootstrap_faktor(bersama, n_tahun, b_uji, d0, rng(100 + b_uji))
        Ru = mi.imbal_instrumen(fu, kurva, pasar, seragam)
        imbal_sens[f"blok_{b_uji}"] = {kode: mi.imbal_portofolio(bobot, Ru) for kode, _, _, bobot in varian}
    hasil["sensitivitas_investasi"] = {
        s: {kode: {k: v for k, v in mi.statistik(r, inflasi).items() if k in KUNCI_RINGKAS}
            for kode, r in per.items()}
        for s, per in imbal_sens.items()}

    # Skenario deterministik.
    hasil["skenario"] = {}
    for kunci, sk in pasar["skenario"].items():
        per_varian, per_instrumen = {}, None
        for kode, _, _, bobot in varian:
            per_varian[kode], per_instrumen = mi.imbal_skenario(sk, kurva, pasar, bobot)
        hasil["skenario"][kunci] = {"label": sk["label"], "guncangan": {k: sk[k] for k in ("dy_bps", "saham", "selisih_bps")},
                                    "dasar": sk["dasar"], "instrumen": per_instrumen, "varian": per_varian}

    # ---------- 4. AYD dan MMBR ----------
    n = mm.nilai_neraca(neraca)
    opsi = {"peringkat_bank": "AA", "peringkat_korporasi": "AA", "klasifikasi": "nilai_wajar",
            "tenor_sbn": ins["sbn"]["tenor_dasar"], "tenor_korporasi": ins["korporasi"]["tenor"]}
    target = reg["solvabilitas"]["target_internal_minimum"]["nilai"]
    acuan = profil["varian_acuan"]
    bobot_per = {kode: bobot for kode, _, _, bobot in varian}

    pada_target = {kode: mm.neraca_pada_target(target, b, n, neraca, reg, **opsi) for kode, b in bobot_per.items()}
    inv_acuan = pada_target[acuan]["investasi"]
    neraca_sama = {kode: mm.susun_neraca(inv_acuan, b, n, neraca, reg, **opsi) for kode, b in bobot_per.items()}

    hasil["ayd"] = {kode: mm.uji_ayd(b, reg) for kode, b in bobot_per.items()}
    hasil["mmbr"] = {
        "opsi_dasar": opsi, "neraca_dasar": n, "target": target, "varian_acuan": acuan,
        "beban_aset_per_100_investasi": {
            kode: {p: mm.beban_aset_per_100_investasi(b, reg, p) for p in ("AAA", "AA", "A")}
            for kode, b in bobot_per.items()},
        "pada_target": pada_target,
        "neraca_sama": neraca_sama,
    }

    # Sensitivitas MMBR: neraca dihitung ulang pada target yang sama.
    sens_mmbr = {
        "peringkat_AAA": ({}, {"peringkat_bank": "AAA", "peringkat_korporasi": "AAA"}),
        "peringkat_A": ({}, {"peringkat_bank": "A", "peringkat_korporasi": "A"}),
        "saham_luar_idx30": ({}, {"saham_idx30": False}),
        "hingga_jatuh_tempo_sbn_2": ({}, {"klasifikasi": "dimiliki_hingga_jatuh_tempo", "tenor_sbn": 2}),
        "hingga_jatuh_tempo_sbn_5": ({}, {"klasifikasi": "dimiliki_hingga_jatuh_tempo", "tenor_sbn": 5}),
        "hingga_jatuh_tempo_sbn_10": ({}, {"klasifikasi": "dimiliki_hingga_jatuh_tempo", "tenor_sbn": 10}),
        "capybmp_50": ({"capybmp": neraca["liabilitas"]["capybmp"]["sensitivitas"][0]}, {}),
        "cadangan_bencana_5": ({"cadangan_bencana": neraca["liabilitas"]["cadangan_bencana"]["sensitivitas"][0]}, {}),
        "klaim_semua_di_bawah_1_tahun": ({}, {"pola_klaim": [1, 0, 0, 0, 0]}),
    }
    hasil["mmbr"]["sensitivitas"] = {}
    for nama_s, (ganti, kw) in sens_mmbr.items():
        n_s = mm.nilai_neraca(neraca, ganti)
        o_s = {**opsi, **kw}
        hasil["mmbr"]["sensitivitas"][nama_s] = {
            kode: {k: v for k, v in mm.neraca_pada_target(target, b, n_s, neraca, reg, **o_s).items()
                   if k in ("investasi", "ekuitas", "mmbr", "modul", "porsi_modul", "tingkat_solvabilitas")}
            for kode, b in bobot_per.items()}

    # Target lain: 100% dan rata-rata industri.
    hasil["mmbr"]["pada_target_lain"] = {
        str(t): {kode: {k: v for k, v in mm.neraca_pada_target(t, b, n, neraca, reg, **opsi).items()
                        if k in ("investasi", "ekuitas", "mmbr", "tingkat_solvabilitas")}
                 for kode, b in bobot_per.items()}
        for t in (1.0, 1.5, 2.0, 3.3152)}

    # Ketentuan lain yang bergantung pada komposisi.
    kt = reg["ketentuan_terkait"]
    potongan = pasar["likuiditas"]["potongan_repo_sbn"]
    hasil["kepatuhan_lain"] = {}
    for kode, b in bobot_per.items():
        t = pada_target[kode]
        siap = {"kas_dan_bank": n["kas_dan_bank"], "deposito": t["investasi"] * b.get("deposito", 0.0),
                "sbn_setelah_potongan": t["investasi"] * b.get("sbn", 0.0) * (1 - potongan)}
        hasil["kepatuhan_lain"][kode] = {
            "dana_jaminan": {"jenis_tersedia": [k for k in kt["dana_jaminan"]["jenis_diizinkan"] if b.get(k, 0) > 0],
                             "dapat_dipenuhi_dari_portofolio": any(b.get(k, 0) > 0 for k in kt["dana_jaminan"]["jenis_diizinkan"]),
                             "minimum_per_100_premi": 100 * kt["dana_jaminan"]["porsi_premi_neto"]},
            "porsi_minimum_sbn": {"porsi_sbn": b.get("sbn", 0.0), "terpenuhi": b.get("sbn", 0.0) >= kt["porsi_minimum_sbn"]["nilai"],
                                  "status_ketentuan": kt["porsi_minimum_sbn"]["status"]},
            "repo_sbn_tersedia": b.get("sbn", 0.0) > 0,
            "kecukupan_investasi": t["kecukupan_investasi"],
            "aset_siap_cair": {**siap, "jumlah": sum(siap.values()),
                               "terhadap_cadangan_klaim": sum(siap.values()) / n["cadangan_klaim"]},
        }

    # ---------- 5. Kaitan investasi dan solvabilitas (investasi saja) ----------
    hasil["solvabilitas_investasi"] = {
        "definisi": "Rasio akhir tahun = (Tingkat Solvabilitas awal + investasi x imbal hasil) / MMBR; hasil underwriting dan kerugian bencana ditahan nol.",
        "neraca_sendiri": {j: {kode: _rasio_akhir(pada_target[kode], imbal[j][kode]) for kode in bobot_per} for j in imbal},
        "neraca_sama": {j: {kode: {"rasio_awal": neraca_sama[kode]["rasio"], **_rasio_akhir(neraca_sama[kode], imbal[j][kode])}
                            for kode in bobot_per} for j in imbal},
    }
    # Peluang pelanggaran pada tiap uji sensitivitas. Klasifikasi hingga jatuh tempo mengubah MMBR
    # (risiko likuiditas), jadi neracanya dihitung ulang; uji lain memakai neraca dasar.
    neraca_hjt = {kode: mm.neraca_pada_target(target, b, n, neraca, reg,
                                              **{**opsi, "klasifikasi": "dimiliki_hingga_jatuh_tempo"})
                  for kode, b in bobot_per.items()}
    hasil["solvabilitas_investasi"]["sensitivitas"] = {
        s: {kode: _rasio_akhir(neraca_hjt[kode] if s == "dimiliki_hingga_jatuh_tempo" else pada_target[kode], r)
            for kode, r in per.items()}
        for s, per in imbal_sens.items()}
    hasil["solvabilitas_investasi"]["galat_baku_peluang"] = (
        "Galat baku peluang p dari N tahun simulasi = akar(p(1-p)/N); untuk p = 0,5% dan N = 100.000 nilainya 0,02 poin.")

    # Hasil investasi rata-rata dibanding ekuitas yang harus disediakan pada target.
    hasil["efisiensi_modal"] = {}
    for kode in bobot_per:
        t = pada_target[kode]
        hasil["efisiensi_modal"][kode] = {
            "ekuitas": t["ekuitas"], "investasi": t["investasi"],
            **{f"hasil_investasi_{j}": t["investasi"] * hasil["profil"][kode]["imbal_hasil"][j]["rata"] for j in imbal},
            **{f"hasil_per_ekuitas_{j}": t["investasi"] * hasil["profil"][kode]["imbal_hasil"][j]["rata"] / t["ekuitas"]
               for j in imbal},
        }

    # Tenor SBN sebagai keputusan di dalam profil Konservatif.
    hasil["tenor_sbn"] = {}
    for tenor in (2, 5, 10):
        kunci = "dasar" if tenor == ins["sbn"]["tenor_dasar"] else f"tenor_sbn_{tenor}"
        r = imbal["bersama"][acuan] if kunci == "dasar" else imbal_sens[kunci][acuan]
        Rp = mi.imbal_instrumen(faktor["panjang"], kurva, pasar, seragam, tenor_sbn=tenor)
        rp = mi.imbal_portofolio(bobot_per[acuan], Rp)
        hasil["tenor_sbn"][str(tenor)] = {
            "imbal_awal": mi.interp_kurva(kurva, "sbn", tenor),
            "bersama": {**mi.statistik(r, inflasi), "rasio_akhir": _rasio_akhir(pada_target[acuan], r)},
            "panjang": {**mi.statistik(rp, inflasi), "rasio_akhir": _rasio_akhir(pada_target[acuan], rp)},
        }

    # Beban modal aset menurut SEOJK lawan kerugian 1-dalam-200 hasil simulasi, per 100 investasi.
    hasil["regulasi_vs_ekonomi"] = {
        kode: {"beban_mmbr_aset": hasil["mmbr"]["beban_aset_per_100_investasi"][kode]["AA"]["jumlah"],
               "var_99_5_bersama": 100 * max(hasil["profil"][kode]["imbal_hasil"]["bersama"]["var_99_5"], 0.0),
               "var_99_5_panjang": 100 * max(hasil["profil"][kode]["imbal_hasil"]["panjang"]["var_99_5"], 0.0),
               "tidak_diakui": 100 * hasil["ayd"][kode]["porsi_tidak_diakui"]}
        for kode in bobot_per}

    # Skenario terhadap rasio.
    for kunci, sk in hasil["skenario"].items():
        sk["rasio_akhir_neraca_sendiri"] = {
            kode: (pada_target[kode]["tingkat_solvabilitas"] + pada_target[kode]["investasi"] * sk["varian"][kode])
            / pada_target[kode]["mmbr"] for kode in bobot_per}
        sk["rasio_akhir_neraca_sama"] = {
            kode: (neraca_sama[kode]["tingkat_solvabilitas"] + neraca_sama[kode]["investasi"] * sk["varian"][kode])
            / neraca_sama[kode]["mmbr"] for kode in bobot_per}

    # ---------- 6. Uji kewajaran MMBR terhadap industri ----------
    hasil["rekonstruksi_industri"] = ri.rekonstruksi()

    # ---------- 7. Besaran turunan yang dikutip laporan ----------
    ta, sa = pada_target[acuan], hasil["profil"][acuan]["imbal_hasil"]
    bantalan = (target - 1.0) * ta["mmbr"]
    rugi_200 = sa["bersama"]["var_99_5"] * ta["investasi"]
    em = hasil["efisiensi_modal"]
    hasil["turunan"] = {
        "bantalan_di_atas_100": bantalan,
        "kerugian_investasi_1_dalam_200": rugi_200,
        "porsi_bantalan_terpakai_investasi": rugi_200 / bantalan,
        "sisa_bantalan_setelah_investasi": bantalan - rugi_200,
        "imbal_hasil_pemicu_pelanggaran": -bantalan / ta["investasi"],
        "selisih_imbal_M50_K75": hasil["profil"]["M50"]["imbal_hasil"]["bersama"]["rata"] - sa["bersama"]["rata"],
        "selisih_imbal_K80_K70": (hasil["profil"]["K80"]["imbal_hasil"]["bersama"]["rata"]
                                  - hasil["profil"]["K70"]["imbal_hasil"]["bersama"]["rata"]),
        "selisih_imbal_sbn_10_2": hasil["data"]["kondisi_awal"]["sbn_10"] - hasil["data"]["kondisi_awal"]["sbn_2"],
        "selisih_hasil_investasi_M50_K75": em["M50"]["hasil_investasi_bersama"] - em[acuan]["hasil_investasi_bersama"],
        "selisih_ekuitas_M50_K75": em["M50"]["ekuitas"] - em[acuan]["ekuitas"],
        "kelipatan_ekuitas_A30_K75": em["A30"]["ekuitas"] / em[acuan]["ekuitas"],
        "kelipatan_ekuitas_M60_K75": em["M60"]["ekuitas"] / em[acuan]["ekuitas"],
        "rentang_beban_aset_AAA_AA": {
            nama: [min(hasil["mmbr"]["beban_aset_per_100_investasi"][k]["AAA"]["jumlah"] for k in kode_list),
                   max(hasil["mmbr"]["beban_aset_per_100_investasi"][k]["AA"]["jumlah"] for k in kode_list)]
            for nama, kode_list in (("Konservatif", ("K80", "K75", "K70")), ("Moderat", ("M40", "M50", "M60")),
                                    ("Agresif", ("A20", "A30", "A40")))},
        "porsi_asuransi_patuh": [min(pada_target[k]["porsi_modul"]["asuransi"] for k in ("K80", "K75", "K70", "M40", "M50")),
                                 max(pada_target[k]["porsi_modul"]["asuransi"] for k in ("K80", "K75", "K70", "M40", "M50"))],
        "var_K75_menurut_blok": {str(b_): hasil["sensitivitas_investasi"][f"blok_{b_}"][acuan]["var_99_5"]
                                 for b_ in bs["panjang_blok_uji"]},
    }

    hasil = _bersih(hasil)
    BERKAS_HASIL.parent.mkdir(parents=True, exist_ok=True)
    BERKAS_HASIL.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
    tulis_tabel(hasil, varian)
    return hasil


def tulis_tabel(h, varian):
    """Tabel rapi (satu baris per pengamatan) untuk dibaca program lain."""
    DIR_TABEL.mkdir(parents=True, exist_ok=True)
    kode_urut = [v[0] for v in varian]

    baris = []
    for kode in kode_urut:
        p = h["profil"][kode]
        for j, s in p["imbal_hasil"].items():
            baris.append({"varian": kode, "profil": p["profil"], "label": p["label"], "jendela": j, **s})
    pd.DataFrame(baris).to_csv(DIR_TABEL / "imbal_hasil_profil.csv", index=False)

    baris = [{"jendela": j, "instrumen": k, **s} for j in ("bersama", "panjang") for k, s in h["instrumen"][j].items()]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "imbal_hasil_instrumen.csv", index=False)

    baris = [{"uji": u, "varian": kode, **s} for u, per in h["sensitivitas_investasi"].items() for kode, s in per.items()]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "sensitivitas_investasi.csv", index=False)

    baris = []
    for kode in kode_urut:
        a = h["ayd"][kode]
        baris.append({"varian": kode, "patuh": a["patuh"], "porsi_diakui": a["porsi_diakui"],
                      "porsi_tidak_diakui": a["porsi_tidak_diakui"],
                      **{f"diakui_{k}": v for k, v in a["diakui"].items()},
                      "ketentuan_dilampaui": "; ".join(f"{d['jenis']} {d['porsi']:.0%} > {d['batas']:.0%}" for d in a["dilampaui"])})
    pd.DataFrame(baris).to_csv(DIR_TABEL / "uji_ayd.csv", index=False)

    for nama, sumber in (("mmbr_pada_target_120", h["mmbr"]["pada_target"]), ("mmbr_neraca_sama", h["mmbr"]["neraca_sama"])):
        baris = []
        for kode in kode_urut:
            b = sumber[kode]
            baris.append({"varian": kode, "investasi": b["investasi"], "investasi_tidak_diakui": b["investasi_tidak_diakui"],
                          "ayd": b["ayd"], "liabilitas": b["liabilitas"], "tingkat_solvabilitas": b["tingkat_solvabilitas"],
                          "ekuitas": b["ekuitas"], **{f"mmbr_{m}": v for m, v in b["modul"].items()},
                          "mmbr": b["mmbr"], "rasio": b["rasio"],
                          "kecukupan_investasi": b["kecukupan_investasi"]["rasio"]})
        pd.DataFrame(baris).to_csv(DIR_TABEL / f"{nama}.csv", index=False)

    baris = [{"uji": u, "varian": kode, "investasi": s["investasi"], "ekuitas": s["ekuitas"], "mmbr": s["mmbr"],
              **{f"mmbr_{m}": v for m, v in s["modul"].items()}}
             for u, per in h["mmbr"]["sensitivitas"].items() for kode, s in per.items()]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "sensitivitas_mmbr.csv", index=False)

    baris = [{"neraca": nr, "jendela": j, "varian": kode, **s}
             for nr in ("neraca_sendiri", "neraca_sama")
             for j, per in h["solvabilitas_investasi"][nr].items() for kode, s in per.items()]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "solvabilitas_investasi.csv", index=False)

    baris = [{"skenario": k, "label": sk["label"], "varian": kode, "imbal_hasil": sk["varian"][kode],
              "rasio_akhir_neraca_sendiri": sk["rasio_akhir_neraca_sendiri"][kode],
              "rasio_akhir_neraca_sama": sk["rasio_akhir_neraca_sama"][kode]}
             for k, sk in h["skenario"].items() for kode in kode_urut]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "skenario.csv", index=False)

    baris = [{"skenario": k, "modul": m, "nilai_juta_rp": v, "porsi": s["porsi"][m], "rasio": s["rasio"]}
             for k, s in h["rekonstruksi_industri"]["skenario"].items() for m, v in s["modul"].items()]
    pd.DataFrame(baris).to_csv(DIR_TABEL / "rekonstruksi_industri.csv", index=False)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    h = main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
    print("hasil ditulis ke", BERKAS_HASIL)
