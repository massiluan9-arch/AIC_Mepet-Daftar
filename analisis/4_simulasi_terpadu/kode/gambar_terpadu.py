"""Gambar hasil simulasi neraca terpadu, dari keluaran/hasil_terpadu.json.

Gaya (warna, tinta, kisi) diambil dari analisis/3_investasi_mmbr/kode/buat_gambar.py supaya seragam.
Pemakaian: python kode/gambar_terpadu.py
"""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import mesin as ms
import buat_gambar as bg          # gaya bersama (rcParams, warna, pembantu)

sys.stdout.reconfigure(encoding="utf-8")
BIRU, JINGGA, TOSKA, KUNING, MAGENTA = bg.BIRU, bg.JINGGA, bg.TOSKA, bg.KUNING, bg.MAGENTA
TINTA, TINTA_2, REDUP, PERMUKAAN = bg.TINTA, bg.TINTA_2, bg.REDUP, bg.PERMUKAAN
ALAS = dict(facecolor=PERMUKAAN, edgecolor="none", pad=1.2)
AMBANG = 0.5


def koma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def simpan(fig, nama):
    ms.DIR_GAMBAR.mkdir(parents=True, exist_ok=True)
    fig.savefig(ms.DIR_GAMBAR / nama, dpi=bg.DPI, bbox_inches="tight")
    plt.close(fig)
    print("  ", nama)


def kurva_target(h):
    kt = h["soal4"]["kurva_target"]
    x = np.array([100 * b["target"] for b in kt])
    seri = [("S0_dasar", "Polis standar", BIRU), ("S12_batas25", "Batas ganti rugi 25%", KUNING),
            ("S3_batas20", "Batas ganti rugi 20%", JINGGA), ("S7_paketA", "Paket A", TOSKA)]
    fig, ax = plt.subplots(figsize=(6.6, 3.5), dpi=bg.DPI)
    for st, nama, warna in seri:
        y = np.array([100 * b[st] for b in kt if st in b])
        if len(y) != len(x):
            continue
        ax.plot(x, y, color=warna, linewidth=2, label=nama, zorder=3)
        geser = {"S12_batas25": 0.014, "S3_batas20": -0.014}.get(st, 0.0)
        ax.text(x[-1] + 4, y[-1] + geser, nama, color=TINTA, fontsize=8.5, va="center")
    ax.axhline(AMBANG, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax.text(478, AMBANG + 0.012, "Ambang 0,5% setahun", color=TINTA_2, fontsize=8.5, va="bottom", ha="right")
    for s, teks in ((120, "Target 120%"), (331.52, "Industri 331,5%")):
        ax.axvline(s, color=REDUP, linewidth=0.8, zorder=1)
        ax.text(s + 3, 0.035, teks, color=TINTA_2, fontsize=8.5, va="bottom", bbox=ALAS)
    bg._rapikan(ax, "y")
    ax.set_xlim(100, 480)
    ax.set_xticks([100, 150, 200, 250, 300, 350, 400])
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(lambda v, _: koma(v, 1) + "%")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlabel("Rasio solvabilitas awal tahun")
    ax.set_ylabel("Peluang rasio akhir tahun di bawah 100%")
    simpan(fig, "t1_kurva_target.png")


def perbatasan_strategi(h):
    s2 = h["soal2"]
    kelompok = {"Risiko sendiri": (["S1_rs5", "S2_rs10"], MAGENTA),
                "Batas ganti rugi per risiko": (["S9_batas50", "S10_batas40", "S11_batas30", "S12_batas25", "S3_batas20",
                                                 "S13_batas15", "S4_batas10", "S17_batas20_besar"], JINGGA),
                "Batas akumulasi atau koasuransi": (["S5_akumulasi10", "S6_koas50", "S19_akum5"], KUNING),
                "Gabungan": (["S7_paketA", "S8_paketB", "S14_batas20_akum10", "S15_batas20_akum5", "S16_batas10_akum5",
                              "S18_batas20_besar_akum10"], TOSKA)}
    # teks, geser x, geser y (titik), perataan
    label = {"S0_dasar": ("Polis standar", -8, 6, "right"), "S2_rs10": ("Risiko sendiri 10%", 0, 9, "center"),
             "S9_batas50": ("Batas 50%", 7, 5, "left"), "S11_batas30": ("30%", 7, 3, "left"),
             "S12_batas25": ("25%", 8, -5, "left"), "S3_batas20": ("Batas 20%", 7, 4, "left"), "S4_batas10": ("Batas 10%", -7, -11, "right"),
             "S6_koas50": ("Koasuransi 50%", 7, 4, "left"), "S19_akum5": ("Akumulasi 5%", 7, 4, "left"),
             "S7_paketA": ("Paket A", 7, 5, "left"), "S16_batas10_akum5": ("Batas 10% + akumulasi 5%", -7, -12, "right"),
             "S17_batas20_besar": ("20%, risiko besar saja", -7, -11, "right")}
    fig, ax = plt.subplots(figsize=(6.6, 3.7), dpi=bg.DPI)
    ax.scatter([0], [100 * s2["S0_dasar"]["peluang_di_bawah_100"]], s=46, color=BIRU, zorder=4, label="Polis standar")
    for nama, (anggota, warna) in kelompok.items():
        ada = [st for st in anggota if st in s2]
        ax.scatter([s2[st]["laba_dilepas"] for st in ada], [100 * s2[st]["peluang_di_bawah_100"] for st in ada],
                   s=46, color=warna, zorder=4, label=nama, edgecolors=PERMUKAAN, linewidths=1.2)
    for st, (teks, dx, dy, rata) in label.items():
        if st not in s2:
            continue
        ax.annotate(teks, (s2[st]["laba_dilepas"], 100 * s2[st]["peluang_di_bawah_100"]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8, color=TINTA, ha=rata)
    ax.axhline(AMBANG, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax.text(7.5, AMBANG + 0.012, "Ambang 0,5%", color=TINTA_2, fontsize=8.5, ha="right")
    bg._rapikan(ax, "y")
    ax.set_xlim(-1.6, 7.6)
    ax.set_ylim(0, 0.8)
    ax.yaxis.set_major_formatter(lambda v, _: koma(v, 1) + "%")
    ax.xaxis.set_major_formatter(lambda v, _: koma(v, 0))
    ax.set_xlabel("Laba bersih yang dilepas setahun (per 100 premi)")
    ax.set_ylabel("Peluang rasio di bawah 100%, target awal 120%")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, columnspacing=1.4, handletextpad=0.3)
    simpan(fig, "t2_perbatasan_strategi.png")


def profil(h):
    v = h["soal1"]["varian"]
    kode = list(v)
    warna = [bg.WARNA_PROFIL[v[k]["profil"]] for k in kode]
    y = np.arange(len(kode))[::-1]
    fig, sumbu = plt.subplots(1, 3, figsize=(7.4, 3.3), sharey=True, gridspec_kw={"wspace": 0.12}, dpi=bg.DPI)
    panel = [("Ekuitas untuk rasio awal 120%", [v[k]["target_120"]["S0_dasar"]["ekuitas"] for k in kode], 0),
             ("Aset siap cair", [v[k]["target_120"]["S0_dasar"]["aset_siap_cair"] for k in kode], 0),
             ("Rasio awal bila ekuitas sama", [100 * v[k]["ekuitas_sama"]["S0_dasar"]["target"] for k in kode], 0)]
    for ax, (judul, nilai, d) in zip(sumbu, panel):
        ax.set_xlim(min(0, min(nilai) * 1.25), max(nilai) * 1.22)
        ax.set_ylim(-0.6, len(kode) - 0.4)
        for yi, x, w in zip(y, nilai, warna):
            bg.batang_h(ax, 0, x, yi, w, tebal=9)
            ax.text(x + (ax.get_xlim()[1] * 0.02 if x >= 0 else -ax.get_xlim()[1] * 0.02), yi, koma(x, d), va="center",
                    ha="left" if x >= 0 else "right", fontsize=8, color=TINTA)
        ax.set_title(judul, fontsize=9)
        bg._rapikan(ax, "x")
        ax.set_yticks(y)
        ax.set_yticklabels(kode)
        ax.set_ylim(-0.6, len(kode) - 0.4)
        ax.xaxis.set_major_formatter(lambda t, _: koma(t, 0))
    klaim = h["soal2"]["S0_dasar"]["klaim_kejadian_var_99_5"]
    sumbu[1].axvline(klaim, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)))
    sumbu[1].text(klaim + 2, -0.45, "Klaim satu kejadian,\n1 dalam 200 tahun", fontsize=7.5, color=TINTA_2, va="bottom", bbox=ALAS)
    sumbu[2].axvline(100, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)))
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c, label=n) for n, c in bg.WARNA_PROFIL.items()], loc="lower center", ncol=3,
               bbox_to_anchor=(0.5, -0.08))
    simpan(fig, "t3_profil.png")


def modul(h):
    acuan = h["meta"]["profil_acuan"]
    m = h["soal3"][f"{acuan}_S0_dasar"]["modul"]
    urut = ["asuransi", "pasar", "operasional", "likuiditas", "kredit"]
    y = np.arange(len(urut))[::-1]
    fig, sumbu = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True, gridspec_kw={"wspace": 0.14}, dpi=bg.DPI)
    baris_baru = chr(10)
    panel = [("Porsi dalam MMBR" + baris_baru, [100 * m[k]["porsi_mmbr"] for k in urut]),
             ("Peluang rugi melampaui" + baris_baru + "beban modal", [100 * m[k]["peluang_melampaui_beban"] for k in urut]),
             ("Porsi tahun pelanggaran" + baris_baru + "yang dipicunya", [100 * m[k]["porsi_tahun_gagal_dipicu"] for k in urut])]
    for ax, (judul, nilai) in zip(sumbu, panel):
        ax.set_xlim(0, 118)
        ax.set_ylim(-0.6, len(urut) - 0.4)
        for yi, x, k in zip(y, nilai, urut):
            bg.batang_h(ax, 0, x, yi, bg.WARNA_MODUL[k], tebal=10)
            ax.text(x + 2.5, yi, koma(x, 1) + "%", va="center", fontsize=8, color=TINTA)
        ax.set_title(judul, fontsize=9)
        bg._rapikan(ax, "x")
        ax.set_yticks(y)
        ax.set_yticklabels([bg.NAMA_MODUL[k] for k in urut])
        ax.set_ylim(-0.6, len(urut) - 0.4)
        ax.set_xticks([0, 50, 100])
        ax.xaxis.set_major_formatter(lambda t, _: f"{t:.0f}%")
    simpan(fig, "t4_modul.png")


def sensitivitas(h):
    s = h["sensitivitas"]
    y = np.arange(len(s))[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=bg.DPI)
    seri = [("peluang_S0_dasar", "Polis standar", BIRU), ("peluang_S3_batas20", "Batas ganti rugi 20%", JINGGA),
            ("peluang_S7_paketA", "Paket A", TOSKA)]
    for yi, b in zip(y, s):
        nilai = [100 * b[k] for k, _, _ in seri]
        ax.plot([min(nilai), max(nilai)], [yi, yi], color=bg.SUMBU, linewidth=1.2, zorder=2)
    for k, nama, warna in seri:
        ax.scatter([100 * b[k] for b in s], y, s=38, color=warna, zorder=4, label=nama, edgecolors=PERMUKAAN, linewidths=1.0)
    ax.axvline(AMBANG, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    bg._rapikan(ax, "x")
    ax.set_yticks(y)
    ax.set_yticklabels([b["label"] for b in s], fontsize=8.2)
    ax.set_ylim(-0.7, len(s) - 0.3)
    ax.set_xlim(0, None)
    ax.xaxis.set_major_formatter(lambda t, _: koma(t, 1) + "%")
    ax.set_xlabel("Peluang rasio akhir tahun di bawah 100% (target awal 120%); garis putus = ambang 0,5%")
    ax.set_xticks([0, 0.5, 1.0, 1.5])
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.42), ncol=1)
    simpan(fig, "t5_sensitivitas.png")


def skenario(h):
    sk = [b for b in h["skenario"] if b["kurva"] == "campuran" and b["pasar"] == "harapan"]
    nama = list(dict.fromkeys(b["skenario"] for b in sk))
    pendek = {n: n.replace("Megathrust ", "Megathrust\n").replace("Gempa dangkal dekat ", "Gempa dangkal\ndekat ").replace("Sesar ", "Sesar\n") for n in nama}
    fig, sumbu = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True, gridspec_kw={"wspace": 0.08}, dpi=bg.DPI)
    seri = [("S0_dasar", "Polis standar", BIRU), ("S3_batas20", "Batas ganti rugi 20%", JINGGA), ("S7_paketA", "Paket A", TOSKA)]
    y = np.arange(len(nama))[::-1]
    for ax, eta, judul in zip(sumbu, (0, 1), ("Guncangan median", "Guncangan satu simpangan baku di atas median")):
        for st, lab, warna in seri:
            x = [100 * next(b["rasio_akhir"] for b in sk if b["skenario"] == n and b["eta"] == eta and b["strategi"] == st) for n in nama]
            ax.scatter(np.clip(x, -520, None), y, s=40, color=warna, zorder=4, label=lab, edgecolors=PERMUKAAN, linewidths=1.0)
        ax.axvline(100, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
        ax.axvline(0, color=bg.SUMBU, linewidth=0.9, zorder=1)
        ax.set_title(judul, fontsize=9)
        bg._rapikan(ax, "x")
        ax.set_yticks(y)
        ax.set_yticklabels([pendek[n] for n in nama], fontsize=8)
        ax.set_ylim(-0.6, len(nama) - 0.4)
        ax.set_xlim(-560, 300)
        ax.xaxis.set_major_formatter(lambda t, _: f"{t:.0f}%")
        ax.set_xlabel("Rasio solvabilitas setelah kejadian")
    sumbu[1].legend(loc="upper center", bbox_to_anchor=(-0.05, -0.24), ncol=3)
    simpan(fig, "t6_skenario.png")


def main():
    h = json.loads((ms.DIR_KELUAR / "hasil_terpadu.json").read_text(encoding="utf-8"))
    for f in (kurva_target, perbatasan_strategi, profil, modul, sensitivitas, skenario):
        f(h)


if __name__ == "__main__":
    main()
