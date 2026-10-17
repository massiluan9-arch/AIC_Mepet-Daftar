"""Menjalankan seluruh rangkaian: model, gambar, dokumen, lalu pemeriksaan."""
import subprocess
import sys
from pathlib import Path

DI_SINI = Path(__file__).resolve().parent

for langkah in ("jalankan.py", "buat_gambar.py", "buat_laporan.py", "uji.py"):
    print(f"\n=== {langkah} ===", flush=True)
    kode = subprocess.run([sys.executable, str(DI_SINI / langkah)]).returncode
    if kode != 0:
        sys.exit(f"{langkah} berhenti dengan kode {kode}")
