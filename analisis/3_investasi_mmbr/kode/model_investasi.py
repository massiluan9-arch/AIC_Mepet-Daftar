"""Model hasil investasi satu tahun.

Langkah: (1) bootstrap blok atas perubahan bulanan faktor pasar, (2) penilaian ulang tiap
instrumen setahun kemudian, (3) penjumlahan berbobot menurut profil. Semua imbal hasil
dalam desimal dan sebelum pajak.
"""
import math

import numpy as np

from data_pasar import FAKTOR

IMBAL_MINIMUM = 0.001


def interp_kurva(kurva, kolom, tenor):
    return float(np.interp(tenor, kurva["tenor"], kurva[kolom]))


def harga_obligasi(kupon, imbal, tenor):
    """Harga per 1 nominal untuk obligasi berkupon setengah tahunan."""
    n = round(2 * tenor)
    v = 1.0 / (1.0 + np.asarray(imbal) / 2.0)
    return kupon / np.asarray(imbal) * (1.0 - v ** n) + v ** n


def bootstrap_faktor(jendela, jumlah_tahun, blok, bunga_deposito_awal, rng):
    """Faktor pasar setahun dari bootstrap blok melingkar.

    Tiap tahun simulasi disusun dari potongan `blok` bulan berurutan yang diambil acak dari
    jendela, sehingga hubungan antarfaktor pada bulan yang sama tetap utuh.
    """
    x = jendela[FAKTOR].to_numpy()
    n = len(x)
    n_blok = math.ceil(12 / blok)
    awal = rng.integers(0, n, size=(jumlah_tahun, n_blok))
    idx = (awal[:, :, None] + np.arange(blok)[None, None, :]) % n
    jalur = x[idx.reshape(jumlah_tahun, n_blok * blok)[:, :12]]
    # Deposito 1 bulan digulirkan: bulan ke-m memakai bunga akhir bulan m-1.
    bobot_dd = (12 - np.arange(1, 13)) / 12.0
    deposito = bunga_deposito_awal + (jalur[:, :, 4] * bobot_dd).sum(axis=1) / 100.0
    return {
        "dy10": jalur[:, :, 0].sum(axis=1) / 100.0,
        "dy2": jalur[:, :, 1].sum(axis=1) / 100.0,
        "saham": np.expm1(jalur[:, :, 2].sum(axis=1)),
        "reksadana": np.expm1(jalur[:, :, 3].sum(axis=1)),
        "deposito": np.maximum(deposito, 0.0),
    }


def perubahan_imbal(faktor, tenor):
    """Perubahan imbal hasil SBN pada suatu tenor: interpolasi lurus antara 2 dan 10 tahun."""
    t = min(max(tenor, 2.0), 10.0)
    return faktor["dy2"] + (t - 2.0) / 8.0 * (faktor["dy10"] - faktor["dy2"])


def imbal_sbn(faktor, kurva, tenor, klasifikasi="nilai_wajar"):
    """Imbal hasil total SBN bertenor `tenor` yang dibeli pada harga nominal hari ini."""
    kupon = interp_kurva(kurva, "sbn", tenor)
    if klasifikasi == "dimiliki_hingga_jatuh_tempo":
        return np.full_like(faktor["dy10"], kupon)
    sisa = tenor - 1
    imbal_akhir = interp_kurva(kurva, "sbn", sisa) + perubahan_imbal(faktor, sisa)
    return harga_obligasi(kupon, np.maximum(imbal_akhir, IMBAL_MINIMUM), sisa) + kupon - 1.0


def imbal_korporasi(faktor, kurva, par, peringkat, seragam_gagal, klasifikasi="nilai_wajar",
                    beta_selisih=0.0, pengali_gagal=1.0):
    """Imbal hasil total portofolio obligasi korporasi berbobot sama.

    seragam_gagal: bilangan seragam (tahun x emiten); emiten gagal bayar bila nilainya di bawah
    peluang gagal bayar. Bilangan yang sama dipakai di semua uji agar hasilnya sebanding.
    beta_selisih: pelebaran selisih (bps) tiap 1% penurunan saham setahun.
    """
    tenor, sisa = par["tenor"], par["tenor"] - 1
    kupon = interp_kurva(kurva, peringkat, tenor)
    if klasifikasi == "dimiliki_hingga_jatuh_tempo":
        hidup = np.full_like(faktor["dy10"], kupon)
    else:
        selisih_awal = interp_kurva(kurva, peringkat, sisa) - interp_kurva(kurva, "sbn", sisa)
        selisih = np.maximum(selisih_awal - beta_selisih * faktor["saham"] * 100 / 1e4, 0.0)
        imbal_akhir = interp_kurva(kurva, "sbn", sisa) + perubahan_imbal(faktor, sisa) + selisih
        hidup = harga_obligasi(kupon, np.maximum(imbal_akhir, IMBAL_MINIMUM), sisa) + kupon - 1.0
    peluang = par["peluang_gagal_bayar_setahun"][peringkat] * pengali_gagal
    porsi_gagal = (seragam_gagal < peluang).mean(axis=1)
    return (1.0 - porsi_gagal) * hidup - porsi_gagal * par["tingkat_kerugian_saat_gagal"]


def imbal_instrumen(faktor, kurva, pasar, seragam_gagal, tenor_sbn=None, peringkat=None,
                    klasifikasi=None, beta_selisih=None, pengali_gagal=1.0, imbal_dividen=None):
    """Imbal hasil setahun tiap instrumen untuk satu konfigurasi."""
    ins = pasar["instrumen"]
    tenor_sbn = ins["sbn"]["tenor_dasar"] if tenor_sbn is None else tenor_sbn
    peringkat = ins["korporasi"]["peringkat_dasar"] if peringkat is None else peringkat
    klasifikasi = pasar["klasifikasi_akuntansi"]["dasar"] if klasifikasi is None else klasifikasi
    beta = pasar["selisih_kredit"]["beta_bps_per_persen_saham"] if beta_selisih is None else beta_selisih
    dividen = ins["saham"]["imbal_dividen"] if imbal_dividen is None else imbal_dividen
    return {
        "sbn": imbal_sbn(faktor, kurva, tenor_sbn, klasifikasi),
        "deposito": faktor["deposito"],
        "korporasi": imbal_korporasi(faktor, kurva, ins["korporasi"], peringkat, seragam_gagal,
                                     klasifikasi, beta, pengali_gagal),
        "saham": faktor["saham"] + dividen,
        "reksadana_saham": faktor["reksadana"] + ins["reksadana_saham"]["dividen_dikurangi_biaya"],
    }


def imbal_portofolio(bobot, instrumen):
    return sum(w * instrumen[k] for k, w in bobot.items())


def statistik(r, inflasi, kelompok=20, rng=None):
    """Ringkasan sebaran imbal hasil setahun. VaR dan TVaR dinyatakan sebagai kerugian positif."""
    q = np.quantile(r, [0.005, 0.01, 0.05, 0.5, 0.95, 0.995])
    out = {
        "rata": float(r.mean()),
        "simpangan": float(r.std()),
        "p0_5": float(q[0]), "p1": float(q[1]), "p5": float(q[2]),
        "median": float(q[3]), "p95": float(q[4]), "p99_5": float(q[5]),
        "var_99_5": float(-q[0]),
        "tvar_99_5": float(-r[r <= q[0]].mean()),
        "peluang_negatif": float((r < 0).mean()),
        "peluang_di_bawah_inflasi": float((r < inflasi).mean()),
        "rata_riil": float((1 + r.mean()) / (1 + inflasi) - 1),
    }
    if rng is not None:
        bagian = np.array_split(rng.permutation(r), kelompok)
        out["galat_baku_rata"] = float(np.std([b.mean() for b in bagian], ddof=1) / math.sqrt(kelompok))
        out["galat_baku_var_99_5"] = float(
            np.std([np.quantile(b, 0.005) for b in bagian], ddof=1) / math.sqrt(kelompok))
    return out


def imbal_skenario(sk, kurva, pasar, bobot):
    """Imbal hasil setahun pada satu skenario deterministik (pergeseran sejajar kurva)."""
    ins = pasar["instrumen"]
    dy, ds = sk["dy_bps"] / 1e4, sk["selisih_bps"] / 1e4
    t_sbn, t_kor, rating = ins["sbn"]["tenor_dasar"], ins["korporasi"]["tenor"], ins["korporasi"]["peringkat_dasar"]
    kupon_sbn = interp_kurva(kurva, "sbn", t_sbn)
    sbn = float(harga_obligasi(kupon_sbn, interp_kurva(kurva, "sbn", t_sbn - 1) + dy, t_sbn - 1)) + kupon_sbn - 1
    kupon_kor = interp_kurva(kurva, rating, t_kor)
    kor = float(harga_obligasi(kupon_kor, interp_kurva(kurva, rating, t_kor - 1) + dy + ds, t_kor - 1)) + kupon_kor - 1
    # Bunga deposito diasumsikan mengikuti separuh pergeseran imbal hasil secara bertahap.
    deposito = pasar["kondisi_awal"]["bunga_deposito_1_bulan"]["nilai"] + 0.5 * dy * 0.5
    r = {"sbn": sbn, "korporasi": kor, "deposito": max(deposito, 0.0),
         "saham": sk["saham"] + ins["saham"]["imbal_dividen"],
         "reksadana_saham": sk["saham"] + ins["reksadana_saham"]["dividen_dikurangi_biaya"]}
    return float(sum(w * r[k] for k, w in bobot.items())), r
