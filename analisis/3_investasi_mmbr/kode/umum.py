"""Jalur berkas, pemuat parameter, dan format angka Indonesia."""
from pathlib import Path

import yaml

DIR_ANALISIS = Path(__file__).resolve().parents[1]
AKAR = DIR_ANALISIS.parents[1]
DIR_PARAMETER = DIR_ANALISIS / "parameter"
DIR_KELUARAN = DIR_ANALISIS / "keluaran"
DIR_TABEL = DIR_KELUARAN / "tabel"
DIR_GAMBAR = DIR_KELUARAN / "gambar"
BERKAS_HASIL = DIR_KELUARAN / "hasil.json"


def muat_parameter():
    """Empat berkas parameter sebagai satu kamus: regulasi, profil, neraca_dasar, pasar."""
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted(DIR_PARAMETER.glob("*.yaml"))}


def daftar_varian(profil):
    """Varian profil menurut urutan baku: [(kode, nama_profil, label, bobot)]."""
    peta = {}
    for nama, isi in profil["profil"].items():
        for kode, v in isi["varian"].items():
            peta[kode] = (kode, nama, v["label"], v["bobot"])
    return [peta[k] for k in profil["urutan_varian"]]


def angka(x, desimal=2):
    """1234.5 -> '1.234,50'."""
    s = f"{x:,.{desimal}f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def persen(x, desimal=1):
    """0.1234 -> '12,3%'."""
    return angka(100 * x, desimal) + "%"
