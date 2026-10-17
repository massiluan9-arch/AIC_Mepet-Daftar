"""Alat bersama skrip analisis lab Rev. 2.

Tiap skrip dipanggil dengan nama varian (folder di rev2_lab). Mesin neraca diimpor dari salinan varian itu,
jadi kode mesin tidak diubah dan parameter yang dipakai adalah parameter salinan tersebut.
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import beta as sebaran_beta

LAB = Path(__file__).resolve().parents[2]
DIR_HASIL = LAB / "laporan" / "hasil"
MODUL = ["kredit", "likuiditas", "pasar", "asuransi", "operasional"]


def siapkan(varian):
    """Mengimpor mesin dari salinan varian dan memuat keluaran rancangannya."""
    akar = LAB / varian / "AIC_CASE" / "analisis"
    sys.path.insert(0, str(akar / "4_simulasi_terpadu" / "kode"))
    import mesin as ms
    assert Path(ms.__file__).resolve().is_relative_to((LAB / varian).resolve()), "mesin diimpor dari salinan yang salah"
    p05, pt = ms.muat_semua()
    ps = yaml.safe_load((akar / "5_solusi_motera" / "parameter_solusi.yaml").read_text(encoding="utf-8"))
    M = ms.Mesin(p05, pt)
    berkas = akar / "5_solusi_motera" / "keluaran" / "rancangan.json"
    rancangan = json.loads(berkas.read_text(encoding="utf-8")) if berkas.exists() else None
    keluar = DIR_HASIL / varian
    keluar.mkdir(parents=True, exist_ok=True)
    return {"ms": ms, "M": M, "p05": p05, "pt": pt, "ps": ps, "rancangan": rancangan, "akar": akar, "keluar": keluar,
            "acuan": pt["meta"]["profil_acuan"]}


def selang_binomial(k, n, tingkat=0.95):
    """Selang Clopper-Pearson (eksak) untuk peluang binomial."""
    a = (1 - tingkat) / 2
    bawah = 0.0 if k == 0 else float(sebaran_beta.ppf(a, k, n - k + 1))
    atas = 1.0 if k == n else float(sebaran_beta.ppf(1 - a, k + 1, n - k))
    return bawah, atas


def batas_atas_satu_sisi(k, n, tingkat=0.95):
    return 1.0 if k == n else float(sebaran_beta.ppf(tingkat, k + 1, n - k))


def kisi_target(pt):
    k = pt["target_solvabilitas"]["kisi"]
    return np.round(np.arange(k["awal"], k["akhir"] + 1e-9, k["langkah"]), 2)


def komponen(ctx, kode, st, s, kurva="campuran", ylt=None, eksposur=None):
    """Menyusun ulang komponen satu konfigurasi persis seperti Mesin.jalankan, tetapi mengembalikan deret
    kerugian tiap modul. Kesamaan dengan mesin diperiksa lewat deret R."""
    ms, M, pt = ctx["ms"], ctx["M"], ctx["pt"]
    n = M.n
    bobot = M.varian[kode][2]
    b = M.neraca_awal(kode, s)
    inv, mmbr, ts0 = b["investasi"], b["mmbr"], b["tingkat_solvabilitas"]
    psr = M.pasar["bersama"]
    posisi = {k: inv * w for k, w in bobot.items()}
    hasil = {k: posisi[k] * psr["imbal"][k] for k in posisi}
    I = sum(hasil.values())
    rugi_kredit = posisi["korporasi"] * (psr["korporasi_tanpa_gagal"] - psr["imbal"]["korporasi"]) \
        if "korporasi" in posisi else np.zeros(n)
    hasil_pasar = I - hasil.get("deposito", 0.0) + rugi_kredit
    rugi_pasar = np.maximum(-hasil_pasar, 0.0)
    E = pt["bencana"]["eksposur_per_premi"]["nilai"] if eksposur is None else eksposur
    tsi = 100.0 * E
    premi_gempa = tsi * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000.0
    premi = 100.0 - premi_gempa * (1.0 - float(M.strategi.loc[st, "faktor_premi_gempa"]))
    uw = pt["underwriting"]
    rata, simp = uw["rasio_klaim_non_bencana"]["rata"], uw["rasio_klaim_non_bencana"]["simpangan"]
    sig2 = np.log1p((simp / rata) ** 2)
    klaim_nb = 100.0 * rata * np.exp(np.sqrt(sig2) * M.z_klaim - sig2 / 2.0)
    kms = uw["komisi"]["nilai"] * premi
    beban_rata = uw["beban_usaha"]["nilai"]
    lebih_beban = uw["beban_usaha"]["simpangan"] * M.z_beban
    U = premi - klaim_nb - kms - beban_rata - lebih_beban
    jumlah, maks = (ylt or M.ylt_untuk(kurva))[st]
    L = tsi * jumlah
    klaim_kejadian = tsi * maks
    lk = pt["likuiditas"]
    potongan = {k: v["nilai"] for k, v in lk["potongan_harga"].items()}
    F, _ = ms.jual_paksa(klaim_kejadian, M.nilai["kas_dan_bank"], posisi, potongan, lk["urutan_cair"])
    G = U + I - L - F
    tarif_pajak = uw["pajak"]["nilai"]
    R = (ts0 + G - tarif_pajak * np.maximum(G, 0.0)) / mmbr
    teknis = premi - klaim_nb - kms - beban_rata - L
    teknis_tanpa_bencana = premi - klaim_nb - kms - beban_rata
    rugi = {"kredit": rugi_kredit, "likuiditas": F, "pasar": rugi_pasar,
            "asuransi": np.maximum(-teknis, 0.0), "operasional": np.maximum(lebih_beban, 0.0)}
    return {"neraca": b, "mmbr": mmbr, "ts0": ts0, "premi": premi, "I": I, "U": U, "L": L, "F": F, "G": G, "R": R,
            "rugi": rugi, "teknis": teknis, "teknis_tanpa_bencana": teknis_tanpa_bencana, "klaim_nb": klaim_nb,
            "klaim_kejadian": klaim_kejadian, "pajak": tarif_pajak, "posisi": posisi, "hasil": hasil,
            # Hasil tiap modul sebagai komponen laba (lebih besar = lebih baik), untuk ukuran simpangan terhadap harapan.
            "hasil_modul": {"kredit": -rugi_kredit, "likuiditas": -F, "pasar": hasil_pasar, "asuransi": teknis,
                            "operasional": -lebih_beban}}


def bersih(o):
    if isinstance(o, dict):
        return {str(k): bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [bersih(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def simpan_json(jalur, isi):
    Path(jalur).write_text(json.dumps(bersih(isi), indent=1, ensure_ascii=False), encoding="utf-8")
