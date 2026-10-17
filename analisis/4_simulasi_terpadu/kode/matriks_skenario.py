"""Rev. 4: matriks skenario neraca (ekonomi dan pasar x guncangan klaim x profil investasi).

Untuk tiap profil wakil (Konservatif 70/30, Moderat 50/40/10, Agresif 30/70), tiap guncangan klaim
(tahun tanpa guncangan katastrofe tambahan, banjir Jabodetabek 2020 yang diskalakan, megathrust Selat Sunda
M 8,7 dengan guncangan median) dan tiap kondisi pasar (imbal hasil harapan; skenario "Ulangan 2026" dari
analisis/3_investasi_mmbr/parameter/pasar.yaml), dihitung rasio solvabilitas akhir tahun dengan fungsi skenario yang
sama dengan uji megathrust: underwriting pada nilai harapan, satu kejadian bencana, hasil investasi setahun,
biaya jual paksa, dan pajak bila laba. Polis standar; rasio awal 120% (dan 330% untuk profil Konservatif).

Skenario adalah uji tekanan bersyarat, bukan peluang gabungan. Status: H (>= 120%), K (100% sampai < 120%),
M (< 100%); status ini klasifikasi internal, bukan status hukum.
Keluaran: 4_simulasi_terpadu/keluaran/matriks_skenario.json
Pemakaian: python 4_simulasi_terpadu/kode/matriks_skenario.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesin as ms          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
DIR_KELUAR = Path(__file__).resolve().parents[1] / "keluaran"
ST = "S0_dasar"
PROFIL = ["K70", "M50", "A30"]


def status(r):
    return "H" if r >= 1.2 else ("K" if r >= 1.0 else "M")


def main():
    p05, pt = ms.muat_semua()
    M = ms.Mesin(p05, pt)
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    tsi = 100.0 * E
    uw, lk = pt["underwriting"], pt["likuiditas"]
    potongan = {k: v["nilai"] for k, v in lk["potongan_harga"].items()}
    kas = M.nilai["kas_dan_bank"]

    # guncangan klaim, per 100 premi
    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")
    mg = sk[(sk["skenario"] == "Megathrust Jawa bagian barat M 8,7") & (sk["eta"] == 0) & (sk["strategi"] == ST)]
    L_mega = tsi * sum(bobot_kurva[k] * float(mg[mg["kurva"] == k]["kerugian"].iloc[0]) for k in ms.KURVA_TUNGGAL)
    bj = pt["skenario_banjir"]
    L_banjir = 100.0 * bj["klaim_properti_triliun"]["nilai"] / bj["premi_langsung_harta_benda_triliun"]["nilai"]
    guncangan = {"normal": 0.0, "banjir_2020": L_banjir, "megathrust": L_mega}

    # kondisi pasar
    kurva_pasar = ms.dp.muat_kurva(p05["pasar"]["kondisi_awal"]["kurva"]["berkas"])
    spek_2026 = p05["pasar"]["skenario"]["ulangan_2026"]
    # durasi termodifikasi SBN acuan setelah setahun (cara harga sama dengan imbal_skenario)
    t_sbn = p05["pasar"]["instrumen"]["sbn"]["tenor_dasar"]
    kupon = ms.mi.interp_kurva(kurva_pasar, "sbn", t_sbn)
    y0 = ms.mi.interp_kurva(kurva_pasar, "sbn", t_sbn - 1)
    harga = lambda y: float(ms.mi.harga_obligasi(kupon, y, t_sbn - 1))
    durasi_sbn = -(harga(y0 + 1e-4) - harga(y0 - 1e-4)) / (2e-4 * harga(y0))
    turun_harga_sbn = harga(y0 + spek_2026["dy_bps"] / 1e4) / harga(y0) - 1

    def imbal(kode, pasar):
        bobot = M.varian[kode][2]
        if pasar == "normal":
            return float(ms.mi.imbal_portofolio(bobot, M.pasar["bersama"]["imbal"]).mean()), None
        tot, r = ms.mi.imbal_skenario(spek_2026, kurva_pasar, p05["pasar"], bobot)
        return float(tot), r

    def sel(kode, s, L, pasar):
        bobot = M.varian[kode][2]
        b = M.neraca_awal(kode, s)
        premi = 100.0
        U = premi - 100.0 * uw["rasio_klaim_non_bencana"]["rata"] - uw["komisi"]["nilai"] * premi - uw["beban_usaha"]["nilai"]
        i, _ = imbal(kode, pasar)
        posisi = {k: b["investasi"] * w for k, w in bobot.items()}
        F, kurang = ms.jual_paksa(np.array([L]), kas, posisi, potongan, lk["urutan_cair"])
        G = U + b["investasi"] * i - L - float(F[0])
        rasio = (b["tingkat_solvabilitas"] + G - uw["pajak"]["nilai"] * max(G, 0.0)) / b["mmbr"]
        kas_dep = kas + posisi.get("deposito", 0.0)
        siap = kas_dep + posisi.get("sbn", 0.0)
        return {"profil": kode, "label": M.varian[kode][1], "target_awal": s, "pasar": pasar, "kerugian": L,
                "imbal_hasil": i, "hasil_investasi": b["investasi"] * i, "hasil_underwriting": U, "biaya_jual_paksa": float(F[0]),
                "laba_sebelum_pajak": G, "rasio_akhir": rasio, "status": status(rasio),
                "ekuitas": b["ekuitas"], "mmbr": b["mmbr"], "investasi": b["investasi"], "tingkat_solvabilitas_awal": b["tingkat_solvabilitas"],
                "kas_dan_deposito": kas_dep, "aset_siap_cair": siap,
                "klaim_di_atas_kas_deposito": max(L - kas_dep, 0.0), "klaim_di_atas_aset_siap_cair": max(L - siap, 0.0),
                "kekurangan_setelah_semua_aset": float(kurang[0])}

    def kerugian_kritis(kode, s, pasar):
        """Kerugian satu kejadian yang membawa rasio akhir tepat ke 100% (bagi dua)."""
        lo, hi = 0.0, 400.0
        if sel(kode, s, 0.0, pasar)["rasio_akhir"] < 1.0:
            return 0.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if sel(kode, s, mid, pasar)["rasio_akhir"] >= 1.0 else (lo, mid)
        return lo

    matriks = []
    for kode in PROFIL:
        for nama, L in guncangan.items():
            for pasar in ("normal", "ulangan_2026"):
                d = sel(kode, 1.2, L, pasar)
                d["guncangan"] = nama
                matriks.append(d)
    tambahan = []
    for nama, L in guncangan.items():
        for pasar in ("normal", "ulangan_2026"):
            d = sel("K70", 3.3, L, pasar)
            d["guncangan"] = nama
            tambahan.append(d)
    kritis = [{"profil": kode, "target_awal": s, "pasar": pasar, "kerugian_kritis": kerugian_kritis(kode, s, pasar)}
              for kode in PROFIL for s in (1.2,) for pasar in ("normal", "ulangan_2026")]
    kritis += [{"profil": "K70", "target_awal": 3.3, "pasar": pasar, "kerugian_kritis": kerugian_kritis("K70", 3.3, pasar)}
               for pasar in ("normal", "ulangan_2026")]
    for k in kritis:
        k["kali_banjir_2020"] = k["kerugian_kritis"] / L_banjir
        k["porsi_megathrust"] = k["kerugian_kritis"] / L_mega
    # rasio akhir menurut besar kerugian satu kejadian (untuk grafik naskah)
    grid = [float(x) for x in np.arange(0.0, 100.01, 1.0)]
    kurva = {"kerugian": grid}
    for kode, s in [(k, 1.2) for k in PROFIL] + [("K70", 3.3)]:
        for pasar in ("normal", "ulangan_2026"):
            kurva[f"{kode}_{s}_{pasar}"] = [sel(kode, s, L, pasar)["rasio_akhir"] for L in grid]
    imbal_profil = {}
    for kode in PROFIL:
        i0, _ = imbal(kode, "normal")
        i1, r1 = imbal(kode, "ulangan_2026")
        imbal_profil[kode] = {"normal": i0, "ulangan_2026": i1, "per_instrumen_2026": r1}

    hasil = {"meta": {"strategi": ST, "satuan": "per 100 premi dicatat", "pajak": uw["pajak"]["nilai"],
                      "status": {"H": "rasio akhir >= 120%", "K": "100% sampai < 120%", "M": "< 100%"},
                      "skenario_pasar_2026": spek_2026, "skenario_banjir": bj,
                      "catatan": "Uji tekanan bersyarat; underwriting pada nilai harapan; satu kejadian bencana. Kekurangan setelah semua aset "
                                 "= klaim yang tidak tertutup walau seluruh investasi dijual."},
             "guncangan": guncangan, "matriks": matriks, "konservatif_330": tambahan, "kerugian_kritis": kritis,
             "imbal_hasil_profil": imbal_profil, "kurva_rasio": kurva,
             "sbn_acuan": {"tenor_awal": t_sbn, "kupon": kupon, "imbal_awal_setelah_setahun": y0, "durasi_termodifikasi": durasi_sbn,
                           "perubahan_harga_ulangan_2026": turun_harga_sbn}}
    (DIR_KELUAR / "matriks_skenario.json").write_text(json.dumps(hasil, indent=1, ensure_ascii=False, default=float), encoding="utf-8")

    print(f"guncangan: banjir {L_banjir:.2f}; megathrust {L_mega:.2f} per 100 premi")
    for kode, v in imbal_profil.items():
        print(f"imbal {kode}: normal {100*v['normal']:.2f}%  2026 {100*v['ulangan_2026']:.2f}%  {({k: round(100*x, 2) for k, x in v['per_instrumen_2026'].items()})}")
    for d in matriks + tambahan:
        print(f"{d['profil']} s={d['target_awal']:.1f} {d['guncangan']:12s} {d['pasar']:13s} I={d['hasil_investasi']:6.2f} G={d['laba_sebelum_pajak']:7.2f} "
              f"R={100*d['rasio_akhir']:7.1f}% {d['status']}  >kasdep={d['klaim_di_atas_kas_deposito']:6.2f} >siapcair={d['klaim_di_atas_aset_siap_cair']:6.2f} "
              f"F={d['biaya_jual_paksa']:5.2f} kurang={d['kekurangan_setelah_semua_aset']:6.2f} eku={d['ekuitas']:6.2f}")
    for k in kritis:
        print(f"kritis {k['profil']} s={k['target_awal']} {k['pasar']:13s} L*={k['kerugian_kritis']:6.2f} = {k['kali_banjir_2020']:.1f} x banjir 2020 = {100*k['porsi_megathrust']:.0f}% megathrust")


if __name__ == "__main__":
    main()
