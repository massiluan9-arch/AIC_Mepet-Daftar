"""Uji batas AYD (POJK 26/2025 Pasal 15) dan MMBR lima modul (SEOJK 24/2017).

Semua nilai neraca per 100 premi dicatat. Rujukan pasal tiap angka ada di parameter/regulasi.yaml.
"""
import math

import numpy as np

INSTRUMEN = ["sbn", "deposito", "korporasi", "saham", "reksadana_saham"]
MODUL = ["kredit", "likuiditas", "pasar", "asuransi", "operasional"]


def uji_ayd(bobot, reg):
    """Porsi investasi yang diakui sebagai AYD untuk suatu alokasi.

    Mengembalikan porsi diakui per jenis, porsi tidak diakui, ketentuan yang dilampaui,
    dan jumlah pihak paling sedikit agar batas per pihak terpenuhi.
    """
    batas = reg["batas_ayd_investasi"]
    diakui, dilampaui = {}, []
    for k in INSTRUMEN:
        w = bobot.get(k, 0.0)
        maks = batas[k]["total"]
        diakui[k] = w if maks is None else min(w, maks)
        if w > diakui[k] + 1e-12:
            dilampaui.append({"jenis": k, "porsi": w, "batas": maks, "kelebihan": w - diakui[k],
                              "dasar": batas[k]["dasar"]})
    gab = batas["gabungan"]
    jumlah_gab = sum(diakui[k] for k in gab["anggota"])
    lebih = max(jumlah_gab - gab["total"], 0.0)
    if lebih > 1e-12:
        dilampaui.append({"jenis": "gabungan", "porsi": jumlah_gab, "batas": gab["total"],
                          "kelebihan": lebih, "dasar": gab["dasar"]})
        for k in gab["urutan_potong"]:
            potong = min(lebih, diakui[k])
            diakui[k] -= potong
            lebih -= potong
    minimum_pihak = {k: math.ceil(bobot[k] / batas[k]["per_pihak"] - 1e-9)
                     for k in INSTRUMEN if bobot.get(k, 0) > 0 and batas[k].get("per_pihak")}
    porsi_diakui = sum(diakui.values())
    return {"diakui": diakui, "porsi_diakui": porsi_diakui, "porsi_tidak_diakui": 1.0 - porsi_diakui,
            "patuh": not dilampaui, "dilampaui": dilampaui, "minimum_pihak": minimum_pihak}


def nilai_neraca(neraca, ganti=None):
    """Nilai butir neraca dasar sebagai kamus datar; `ganti` menimpa butir untuk uji sensitivitas."""
    n = {}
    for bagian in ("liabilitas", "aset_bukan_investasi", "beban_dan_dac"):
        for k, v in neraca[bagian].items():
            n[k] = v["nilai"]
    n.update(ganti or {})
    return n


def _kelompok_tenor(tenor, batas):
    """Indeks kelompok jatuh tempo; tenor tepat di batas masuk kelompok yang lebih panjang."""
    return int(np.searchsorted(batas, tenor, side="right"))


def hitung_mmbr(investasi, bobot, n, neraca, reg, peringkat_bank="AA", peringkat_korporasi="AA",
                klasifikasi="nilai_wajar", tenor_sbn=5, tenor_korporasi=3, saham_idx30=True,
                pola_klaim=None):
    """MMBR per modul untuk jumlah investasi dan alokasi tertentu."""
    fr, klaster = reg["faktor_risiko"], reg["klaster_peringkat"]
    ayd = uji_ayd(bobot, reg)
    d = {k: investasi * v for k, v in ayd["diakui"].items()}

    kredit = {
        "deposito": d["deposito"] * fr["kredit"]["deposito_per_klaster"][klaster[peringkat_bank]],
        "korporasi": d["korporasi"] * fr["kredit"]["korporasi_per_klaster"][klaster[peringkat_korporasi]],
        "tagihan_premi": n["tagihan_premi"] * fr["kredit"]["tagihan_premi_langsung"],
    }
    faktor_saham = fr["pasar"]["saham_idx30_atau_jii" if saham_idx30 else "saham_bursa_indonesia_lain"]
    pasar = {
        "saham": d["saham"] * faktor_saham,
        "reksadana_saham": d["reksadana_saham"] * fr["pasar"]["reksadana_ekuitas"],
    }
    f = fr["asuransi"]["harta_benda"]
    asuransi = {
        "capybmp": n["capybmp"] * f["fcp"],
        "cadangan_klaim": n["cadangan_klaim"] * f["fck"],
        "cadangan_bencana": n["cadangan_bencana"] * f["fcb"],
    }
    operasional = {
        "beban_umum": n["bua_dikurangi_bpl"] * fr["operasional"]["faktor_bua"],
        "dac": n["dac"] * fr["operasional"]["faktor_dac"],
    }

    # Risiko likuiditas: kekurangan AYD terhadap liabilitas pada tiap kelompok jatuh tempo.
    batas = fr["likuiditas"]["batas_kelompok_tahun"]
    aset = np.zeros(len(batas) + 1)
    aset[0] += n["kas_dan_bank"] + n["tagihan_premi"] + d["deposito"] + d["saham"] + d["reksadana_saham"]
    if klasifikasi == "nilai_wajar":
        aset[0] += d["sbn"] + d["korporasi"]
    else:
        aset[_kelompok_tenor(tenor_sbn, batas)] += d["sbn"]
        aset[_kelompok_tenor(tenor_korporasi, batas)] += d["korporasi"]
    liab = np.zeros(len(batas) + 1)
    for k, p in neraca["pola_jatuh_tempo"].items():
        porsi = pola_klaim if (k == "cadangan_klaim" and pola_klaim is not None) else p["porsi"]
        liab += n[k] * np.array(porsi)
    kurang = np.maximum(liab - aset, 0.0)
    likuiditas = {nama: float(fr["likuiditas"]["faktor"] * x)
                  for nama, x in zip(fr["likuiditas"]["nama_kelompok"], kurang)}

    rincian = {"kredit": kredit, "likuiditas": likuiditas, "pasar": pasar,
               "asuransi": asuransi, "operasional": operasional}
    modul = {m: float(sum(rincian[m].values())) for m in MODUL}
    total = sum(modul.values())
    return {"modul": modul, "total": total, "porsi": {m: modul[m] / total for m in MODUL},
            "rincian": rincian, "ayd": ayd,
            "likuiditas_kelompok": {"aset": aset.tolist(), "liabilitas": liab.tolist()}}


def susun_neraca(investasi, bobot, n, neraca, reg, **opsi):
    """Posisi solvabilitas untuk jumlah investasi tertentu."""
    m = hitung_mmbr(investasi, bobot, n, neraca, reg, **opsi)
    alfa = m["ayd"]["porsi_diakui"]
    cadangan_teknis = n["capybmp"] + n["cadangan_klaim"] + n["cadangan_bencana"]
    liabilitas = cadangan_teknis + n["utang_klaim"] + n["utang_lain"]
    bukan_investasi = n["kas_dan_bank"] + n["tagihan_premi"]
    ayd = alfa * investasi + bukan_investasi
    ts = ayd - liabilitas
    wajib_ditutup = cadangan_teknis + n["utang_klaim"]
    penutup = alfa * investasi + n["kas_dan_bank"]
    return {
        "investasi": investasi,
        "investasi_diakui": alfa * investasi,
        "investasi_tidak_diakui": (1 - alfa) * investasi,
        "aset_bukan_investasi": bukan_investasi,
        "ayd": ayd,
        "liabilitas": liabilitas,
        "cadangan_teknis": cadangan_teknis,
        "tingkat_solvabilitas": ts,
        # Dana pemegang saham yang tertanam: Tingkat Solvabilitas ditambah aset yang tidak diakui.
        "ekuitas": investasi + bukan_investasi - liabilitas,
        "mmbr": m["total"],
        "modul": m["modul"],
        "porsi_modul": m["porsi"],
        "rincian": m["rincian"],
        "rasio": ts / m["total"],
        "kecukupan_investasi": {"penutup": penutup, "wajib_ditutup": wajib_ditutup,
                                "rasio": penutup / wajib_ditutup, "terpenuhi": penutup >= wajib_ditutup},
    }


def neraca_pada_target(target, bobot, n, neraca, reg, **opsi):
    """Jumlah investasi (dan ekuitas) yang membuat rasio solvabilitas tepat sebesar target."""
    def selisih(inv):
        b = susun_neraca(inv, bobot, n, neraca, reg, **opsi)
        return b["tingkat_solvabilitas"] - target * b["mmbr"]

    bawah, atas = 0.0, 10000.0
    assert selisih(bawah) < 0 < selisih(atas), "target tidak terkurung"
    for _ in range(80):
        tengah = (bawah + atas) / 2
        if selisih(tengah) < 0:
            bawah = tengah
        else:
            atas = tengah
    return susun_neraca((bawah + atas) / 2, bobot, n, neraca, reg, **opsi)


def beban_aset_per_100_investasi(bobot, reg, peringkat):
    """Beban modal kredit dan pasar atas aset investasi yang diakui, per 100 investasi."""
    fr, klaster = reg["faktor_risiko"], reg["klaster_peringkat"]
    d = uji_ayd(bobot, reg)["diakui"]
    kredit = 100 * (d["deposito"] * fr["kredit"]["deposito_per_klaster"][klaster[peringkat]]
                    + d["korporasi"] * fr["kredit"]["korporasi_per_klaster"][klaster[peringkat]])
    pasar = 100 * (d["saham"] * fr["pasar"]["saham_idx30_atau_jii"]
                   + d["reksadana_saham"] * fr["pasar"]["reksadana_ekuitas"])
    return {"kredit": kredit, "pasar": pasar, "jumlah": kredit + pasar}
