"""Memuat deret pasar bulanan dan menyiapkan perubahan bulanan untuk bootstrap.

Sumber dan keterbatasan tiap deret ada di data/ekonomi_pasar/pasar_riwayat/README.md.
"""
import numpy as np
import pandas as pd

from umum import AKAR

DIR_PASAR = AKAR / "data" / "ekonomi_pasar" / "pasar_riwayat"
# Urutan kolom faktor pada matriks bootstrap.
FAKTOR = ["dy10", "dy2", "r_saham", "r_reksadana", "dd"]


def _baca(nama):
    return pd.read_csv(DIR_PASAR / nama, encoding="utf-8-sig")


def muat_kurva(berkas_relatif):
    """Kurva imbal hasil per tenor, dalam desimal."""
    k = pd.read_csv(AKAR / berkas_relatif, encoding="utf-8-sig")
    return pd.DataFrame({"tenor": k["tenor_tahun"], "sbn": k["SBN_IGS"] / 100,
                         "AAA": k["AAA"] / 100, "AA": k["AA"] / 100})


def muat_deret():
    """Deret tingkat bulanan Jan 2000 - Okt 2026 dalam satu tabel.

    y10: imbal hasil SBN 10 tahun (rata-rata bulanan, OECD, 2012-2024).
    y2: y10 dikurangi rata-rata bulanan selisih 10 dan 2 tahun (AsianBondsOnline).
    lq45, ihsg: penutupan akhir bulan. dep1: bunga deposito rupiah 1 bulan (SEKI).
    """
    oecd = _baca("suku_bunga_OECD_bulanan.csv").iloc[:, :2]
    oecd.columns = ["bulan", "y10"]
    saham = _baca("saham_IHSG_LQ45_bulanan.csv")
    saham.columns = ["bulan", "ihsg", "lq45"]
    dep = _baca("deposito_rupiah_bank_umum_bulanan_SEKI.csv")[["bulan", "1_bulan"]]
    dep.columns = ["bulan", "dep1"]
    selisih = _baca("SBN_selisih_10th_2th_harian_ABO.csv")
    selisih["bulan"] = selisih["tanggal"].str[:7]
    selisih = selisih.groupby("bulan", as_index=False)["selisih_bps"].mean()

    df = pd.DataFrame({"bulan": pd.period_range("2000-01", "2026-10", freq="M").astype(str)})
    for t in (oecd, saham, dep, selisih):
        df = df.merge(t, on="bulan", how="left")
    df["y2"] = df["y10"] - df["selisih_bps"] / 100
    # SEKI kosong pada Mar-Nov 2024 dan Jan-Jul 2026: diisi garis lurus antara dua titik terdekat.
    df["dep1_terisi"] = df["dep1"].isna()
    df["dep1"] = df["dep1"].interpolate(limit_area="inside").ffill()
    return df


def perubahan_bulanan(df):
    """Perubahan bulanan: imbal hasil dan deposito dalam poin persentase, saham dalam log."""
    return pd.DataFrame({
        "bulan": df["bulan"],
        "dy10": df["y10"].diff(),
        "dy2": df["y2"].diff(),
        "r_saham": np.log(df["lq45"]).diff(),
        "r_reksadana": np.log(df["ihsg"]).diff(),
        "dd": df["dep1"].diff(),
    })


def jendela_bersama(ch, awal, akhir):
    """Bulan saat semua faktor teramati."""
    j = ch[(ch["bulan"] >= awal) & (ch["bulan"] <= akhir)].reset_index(drop=True)
    assert not j[FAKTOR].isna().any().any(), "jendela bersama memuat nilai kosong"
    return j


def jendela_panjang(ch, bersama, awal, akhir, rng):
    """Jendela saham penuh; perubahan imbal hasil di luar jendela bersama diimputasi.

    Imputasi: regresi linear dy10 dan dy2 atas r_saham pada jendela bersama, ditambah
    sepasang residu yang diambil acak dari regresi itu.
    """
    x = np.column_stack([np.ones(len(bersama)), bersama["r_saham"]])
    y = bersama[["dy10", "dy2"]].to_numpy()
    koef, *_ = np.linalg.lstsq(x, y, rcond=None)
    residu = y - x @ koef
    r2 = 1 - residu.var(axis=0) / y.var(axis=0)

    p = ch[(ch["bulan"] >= awal) & (ch["bulan"] <= akhir)].reset_index(drop=True).copy()
    kosong = p["dy10"].isna().to_numpy()
    acak = rng.integers(0, len(residu), size=int(kosong.sum()))
    taksir = np.column_stack([np.ones(kosong.sum()), p.loc[kosong, "r_saham"]]) @ koef + residu[acak]
    p.loc[kosong, ["dy10", "dy2"]] = taksir
    assert not p[FAKTOR].isna().any().any(), "jendela panjang memuat nilai kosong"
    info = {
        "bulan_teramati": int((~kosong).sum()),
        "bulan_diimputasi": int(kosong.sum()),
        "kemiringan_dy10_per_log_saham": float(koef[1, 0]),
        "kemiringan_dy2_per_log_saham": float(koef[1, 1]),
        "r2_dy10": float(r2[0]),
        "r2_dy2": float(r2[1]),
    }
    return p, info


def deskriptif(df, bersama):
    """Statistik deskriptif data masukan (Bab 3, analisis deskriptif data)."""
    j = df[(df["bulan"] >= "2012-01") & (df["bulan"] <= "2024-12")]
    out = {"jumlah_bulan_bersama": int(len(bersama)), "tingkat": {}, "perubahan_12_bulan": {}}
    for k in ("y10", "y2", "dep1"):
        s = j[k]
        out["tingkat"][k] = {"rata": float(s.mean()), "min": float(s.min()), "maks": float(s.max()),
                             "terakhir": float(s.iloc[-1])}
    for k in ("y10", "y2"):
        d = j[k].diff(12).dropna()
        out["perubahan_12_bulan"][k] = {"simpangan": float(d.std()), "p5": float(d.quantile(0.05)),
                                         "p95": float(d.quantile(0.95)), "maks": float(d.max()),
                                         "min": float(d.min())}
    for nama, kol, rentang in (("lq45_2012_2024", "lq45", ("2012-01", "2024-12")),
                               ("lq45_2000_2026", "lq45", ("2000-01", "2026-10")),
                               ("ihsg_2012_2024", "ihsg", ("2012-01", "2024-12")),
                               ("ihsg_2000_2026", "ihsg", ("2000-01", "2026-10"))):
        s = df[(df["bulan"] >= rentang[0]) & (df["bulan"] <= rentang[1])][kol]
        r = (s / s.shift(12) - 1).dropna()
        out["perubahan_12_bulan"][nama] = {"rata": float(r.mean()), "simpangan": float(r.std()),
                                            "p5": float(r.quantile(0.05)), "min": float(r.min()),
                                            "jumlah": int(len(r))}
    ytd = df[df["bulan"] == "2026-10"].iloc[0], df[df["bulan"] == "2025-12"].iloc[0]
    out["saham_2026_sejak_awal_tahun"] = {k: float(ytd[0][k] / ytd[1][k] - 1) for k in ("ihsg", "lq45")}
    kor = bersama[FAKTOR].corr()
    out["korelasi_bulanan"] = {"dy10_r_saham": float(kor.loc["dy10", "r_saham"]),
                               "dy10_dy2": float(kor.loc["dy10", "dy2"]),
                               "r_saham_r_reksadana": float(kor.loc["r_saham", "r_reksadana"]),
                               "dy10_dd": float(kor.loc["dy10", "dd"])}
    out["autokorelasi_lag1"] = {k: float(bersama[k].autocorr(1)) for k in FAKTOR}
    out["deposito_bulan_terisi_interpolasi"] = int(df["dep1_terisi"].sum())
    return out
