"""Membandingkan keluaran dua salinan lab (JSON dan CSV) butir demi butir.

Pemakaian: python banding_keluaran.py <folder AIC_CASE acuan> <folder AIC_CASE pembanding>
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ABAIKAN = {"waktu_detik"}


def ratakan(o, awalan=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ABAIKAN:
                continue
            yield from ratakan(v, f"{awalan}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from ratakan(v, f"{awalan}[{i}]")
    else:
        yield awalan, o


def banding_json(a, b):
    da, db = dict(ratakan(json.loads(a.read_text(encoding="utf-8")))), dict(ratakan(json.loads(b.read_text(encoding="utf-8"))))
    hanya = sorted(set(da) ^ set(db))
    beda, maks, kunci_maks = 0, 0.0, ""
    for k in set(da) & set(db):
        x, y = da[k], db[k]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            s = abs(x - y)
            if s > 1e-12 * max(1.0, abs(x), abs(y)):
                beda += 1
                if s > maks:
                    maks, kunci_maks = s, k
        elif x != y:
            beda += 1
            kunci_maks = kunci_maks or k
    return len(da), beda, maks, kunci_maks, len(hanya)


def banding_csv(a, b):
    x, y = pd.read_csv(a), pd.read_csv(b)
    if x.shape != y.shape or list(x.columns) != list(y.columns):
        return x.size, -1, float("nan"), "bentuk berbeda", 0
    beda, maks, kol = 0, 0.0, ""
    for c in x.columns:
        if pd.api.types.is_numeric_dtype(x[c]) and pd.api.types.is_numeric_dtype(y[c]):
            s = (x[c].astype(float) - y[c].astype(float)).abs()
            sama_nan = x[c].isna() & y[c].isna()
            s = s.where(~sama_nan, 0.0).fillna(float("inf"))
            n = int((s > 1e-12 * (1 + x[c].abs().fillna(0))).sum())
        else:
            n = int((x[c].fillna("") != y[c].fillna("")).sum())
            s = pd.Series([0.0])
        beda += n
        if n and float(s.max()) >= maks:
            maks, kol = float(s.max()), c
    return x.size, beda, maks, kol, 0


def main():
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    berkas = ["analisis/4_simulasi_terpadu/keluaran/hasil_terpadu.json",
              "analisis/5_solusi_motera/keluaran/rancangan.json",
              "analisis/5_solusi_motera/keluaran/hasil_excel.json",
              "analisis/5_solusi_motera/keluaran/calon_strategi.csv"]
    berkas += [f"analisis/4_simulasi_terpadu/keluaran/tabel/{n}" for n in
               ("t1_profil.csv", "t2_strategi.csv", "t3_modul.csv", "t4_target.csv", "t4_target_minimum.csv",
                "t5_sensitivitas.csv", "t6_skenario.csv")]
    print(f"acuan     : {a}\npembanding: {b}")
    print(f"{'berkas':<78}{'butir':>8}{'beda':>7}{'selisih maks':>15}  lokasi")
    for f in berkas:
        if not (a / f).exists() or not (b / f).exists():
            print(f"{f:<78}  tidak ada di salah satu salinan")
            continue
        n, beda, maks, kunci, hanya = (banding_json if f.endswith(".json") else banding_csv)(a / f, b / f)
        print(f"{f:<78}{n:>8}{beda:>7}{maks:>15.3e}  {kunci}{'  (kunci tak berpasangan: %d)' % hanya if hanya else ''}")


if __name__ == "__main__":
    main()
