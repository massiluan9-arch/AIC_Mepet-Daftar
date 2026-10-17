"""Membandingkan tabel kerugian tahunan dua salinan: kolom mana yang sama persis dan mana yang berubah.

Pemakaian: python banding_ylt.py <varian acuan> <varian pembanding>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
LAB = Path(__file__).resolve().parents[2]
a, b = sys.argv[1], sys.argv[2]
rel = "AIC_CASE/analisis/2_model_bencana/keluaran"
for nama in ("04_ylt.csv.gz", "05_ylt_campuran.csv.gz"):
    x, y = pd.read_csv(LAB / a / rel / nama), pd.read_csv(LAB / b / rel / nama)
    assert list(x.columns) == list(y.columns) and len(x) == len(y)
    sama, beda = [], []
    for c in x.columns:
        if x[c].dtype == object:
            (sama if (x[c] == y[c]).all() else beda).append(c)
        else:
            (sama if np.array_equal(x[c].to_numpy(), y[c].to_numpy()) else beda).append(c)
    st = lambda kol: sorted({c.split(".")[-1] for c in kol if c.startswith(("jumlah.", "maks."))})
    print(f"{nama}: {len(x)} tahun, {len(x.columns)} kolom; identik {len(sama)}, berubah {len(beda)}")
    print("  strategi yang seluruh kolomnya identik:", [s for s in st(sama) if s not in st(beda)])
    print("  strategi yang berubah:", st(beda))
    if "cabang" in x.columns:
        print("  cabang kurva tiap tahun identik:", bool((x["cabang"] == y["cabang"]).all()))
    for c in beda:
        if c.startswith("jumlah.") and (c.endswith("S21_zona_batas10") or c.endswith("S4_batas10")):
            nol = (x[c] > 0) == (y[c] > 0)
            print(f"  {c}: rata-rata {x[c].mean():.6e} -> {y[c].mean():.6e} (x{y[c].mean() / x[c].mean():.4f}); "
                  f"tahun berkerugian sama: {bool(nol.all())}; pembanding >= acuan di semua tahun: {bool((y[c] >= x[c] - 1e-12).all())}")
