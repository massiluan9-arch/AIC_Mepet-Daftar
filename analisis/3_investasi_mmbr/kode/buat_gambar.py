"""Menggambar grafik laporan dari keluaran/hasil.json.

Warna, ketebalan tanda, dan celah mengikuti satu aturan: warna kategori dipakai menurut urutan
tetap (biru, jingga, toska, kuning, magenta), profil yang sama selalu berwarna sama, teks memakai
warna tinta, dan tiap grafik punya tabel padanannya di laporan.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MPath

import data_pasar as dp
from umum import BERKAS_HASIL, DIR_GAMBAR, angka

PERMUKAAN, TINTA, TINTA_2, REDUP = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
KISI, SUMBU = "#e1e0d9", "#c3c2b7"
BIRU, JINGGA, TOSKA, KUNING, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
WARNA_PROFIL = {"Konservatif": BIRU, "Moderat": JINGGA, "Agresif": TOSKA}
WARNA_MODUL = {"asuransi": BIRU, "kredit": JINGGA, "pasar": TOSKA, "likuiditas": KUNING, "operasional": MAGENTA}
NAMA_MODUL = {"asuransi": "Asuransi", "kredit": "Kredit", "pasar": "Pasar", "likuiditas": "Likuiditas",
              "operasional": "Operasional"}
DPI = 200

plt.rcParams.update({
    "font.family": ["Segoe UI", "Arial", "DejaVu Sans"], "font.size": 9,
    "figure.facecolor": PERMUKAAN, "axes.facecolor": PERMUKAAN, "savefig.facecolor": PERMUKAAN,
    "axes.edgecolor": SUMBU, "axes.linewidth": 0.8, "axes.labelcolor": TINTA_2,
    "xtick.color": REDUP, "ytick.color": REDUP, "xtick.labelcolor": TINTA_2, "ytick.labelcolor": TINTA,
    "grid.color": KISI, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "axes.titlesize": 10, "axes.titleweight": "semibold", "axes.titlecolor": TINTA,
    "axes.titlelocation": "left", "legend.frameon": False, "legend.fontsize": 8.5,
})


def _rapikan(ax, kisi="x"):
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)
    ax.grid(axis=kisi, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _px(ax, pt):
    """Ukuran dalam titik (pt) dinyatakan dalam satuan data sumbu x dan y."""
    inv = ax.transData.inverted()
    a, b = inv.transform((0, 0)), inv.transform((1, 1))
    k = pt * DPI / 72
    return abs(b[0] - a[0]) * k, abs(b[1] - a[1]) * k


def batang_h(ax, x0, x1, y, warna, tebal=11, bulat=True, zorder=3):
    """Batang mendatar setebal `tebal` pt; ujung data membulat 3 pt, pangkal tetap siku."""
    if abs(x1 - x0) < 1e-12:
        return
    rx, ry = _px(ax, 3)
    _, h = _px(ax, tebal)
    arah = 1 if x1 >= x0 else -1
    rx = min(rx, abs(x1 - x0)) * arah if bulat else 0.0
    ry = min(ry, h / 2) if bulat else 0.0
    b, t = y - h / 2, y + h / 2
    titik = [(x0, b), (x1 - rx, b), (x1, b), (x1, b + ry), (x1, t - ry), (x1, t), (x1 - rx, t), (x0, t), (x0, b)]
    kode = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO,
            MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(titik, kode), facecolor=warna, edgecolor="none", zorder=zorder))


def batang_tumpuk_h(ax, nilai_warna, y, tebal=11):
    """Batang bertumpuk; ruas dipisah celah 1,5 pt berwarna permukaan, hanya ruas terakhir membulat."""
    celah, _ = _px(ax, 1.5)
    kiri = 0.0
    isi = [(v, w) for v, w in nilai_warna if v > 1e-9]
    for i, (v, w) in enumerate(isi):
        akhir = i == len(isi) - 1
        batang_h(ax, kiri, kiri + v - (0 if akhir else celah), y, w, tebal, bulat=akhir)
        kiri += v
    return kiri


def _sumbu_varian(ax, kode, label):
    ax.set_ylim(len(kode) - 0.4, -0.6)
    ax.set_yticks(range(len(kode)))
    ax.set_yticklabels(label)


def _simpan(fig, nama):
    DIR_GAMBAR.mkdir(parents=True, exist_ok=True)
    fig.savefig(DIR_GAMBAR / nama, dpi=DPI)
    plt.close(fig)


def _pct(x, d=1):
    return angka(100 * x, d) + "%"


# Label nilai diberi alas sewarna permukaan agar tidak terpotong garis acuan.
ALAS = {"facecolor": PERMUKAAN, "edgecolor": "none", "pad": 0.8}


def _koma(x, _=None):
    return f"{x:g}".replace(".", ",")


def _legenda_profil(ax, **kw):
    ax.legend(handles=[Patch(facecolor=w, label=n) for n, w in WARNA_PROFIL.items()], **kw)


# ---------- Gambar 1: data masukan ----------
def gambar_data(h):
    df = dp.muat_deret()
    df["t"] = [int(b[:4]) + (int(b[5:]) - 0.5) / 12 for b in df["bulan"]]
    fig, axs = plt.subplots(3, 1, figsize=(7.6, 6.6), dpi=DPI, sharex=True)
    fig.subplots_adjust(left=0.08, right=0.77, top=0.94, bottom=0.07, hspace=0.32)

    ax = axs[0]
    for kol, warna, nama in (("y10", BIRU, "10 tahun"), ("y2", JINGGA, "2 tahun")):
        s = df.dropna(subset=[kol])
        ax.plot(s["t"], s[kol], color=warna, lw=1.6, label=nama, solid_capstyle="round")
        ax.plot(s["t"].iloc[-1], s[kol].iloc[-1], "o", ms=5.5, color=warna, mec=PERMUKAAN, mew=1.2, zorder=4)
        ax.annotate(f"{nama}: {angka(s[kol].iloc[-1], 2)}% (Des 2024)", (s["t"].iloc[-1], s[kol].iloc[-1]),
                    xytext=(6, 4 if kol == "y10" else -9), textcoords="offset points", fontsize=8, color=TINTA_2)
    ax.set_title("Imbal hasil SBN, rata-rata bulanan (%)")
    ax.legend(loc="upper left", ncol=2)

    ax = axs[1]
    ax.plot(df["t"], df["lq45"], color=BIRU, lw=1.6, solid_capstyle="round")
    ax.plot(df["t"].iloc[-1], df["lq45"].iloc[-1], "o", ms=5.5, color=BIRU, mec=PERMUKAAN, mew=1.2, zorder=4)
    ytd = h["data"]["deskriptif"]["saham_2026_sejak_awal_tahun"]["lq45"]
    ax.annotate(f"Okt 2026: {angka(df['lq45'].iloc[-1], 0)}\n{_pct(ytd)} sejak awal 2026",
                (df["t"].iloc[-1], df["lq45"].iloc[-1]), xytext=(6, -4), textcoords="offset points",
                fontsize=8, color=TINTA_2, va="center")
    ax.set_title("Indeks LQ45, penutupan akhir bulan")

    ax = axs[2]
    asli = df[~df["dep1_terisi"]]
    ax.plot(df["t"], df["dep1"], color=BIRU, lw=1.6, solid_capstyle="round")
    ax.plot(asli["t"].iloc[-1], asli["dep1"].iloc[-1], "o", ms=5.5, color=BIRU, mec=PERMUKAAN, mew=1.2, zorder=4)
    ax.annotate(f"Agu 2026: {angka(asli['dep1'].iloc[-1], 2)}%", (asli["t"].iloc[-1], asli["dep1"].iloc[-1]),
                xytext=(6, 6), textcoords="offset points", fontsize=8, color=TINTA_2)
    ax.set_title("Bunga deposito rupiah 1 bulan, bank umum (%)")
    for ax in axs:
        _rapikan(ax, "y")
        ax.axvspan(2012 + 1 / 12, 2025, color=KISI, alpha=0.45, lw=0, zorder=0)
        ax.set_xlim(2000, 2027)
        ax.yaxis.set_major_formatter(_koma)
    axs[1].text(2018.5, axs[1].get_ylim()[0] + 25, "jendela bersama 2012-2024", fontsize=7.5, color=TINTA_2,
                ha="center", va="bottom")
    _simpan(fig, "g1_data_pasar.png")


# ---------- Gambar 2: sebaran imbal hasil per varian ----------
def gambar_sebaran(h, kode, label, profil):
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.3), dpi=DPI, sharey=True)
    fig.subplots_adjust(left=0.17, right=0.985, top=0.83, bottom=0.12, wspace=0.07)
    batas = (-0.27, 0.54)
    inflasi = h["data"]["kondisi_awal"]["inflasi"]
    for ax, j, judul in zip(axs, ("bersama", "panjang"),
                            ("Jendela bersama 2012-2024", "Jendela panjang 2000-2026")):
        _sumbu_varian(ax, kode, label)
        ax.set_xlim(*batas)
        _rapikan(ax, "x")
        ax.axvline(0, color=SUMBU, lw=1.0, zorder=1)
        ax.axvline(inflasi, color=TINTA_2, lw=0.8, zorder=1)
        fig.canvas.draw()
        for i, k in enumerate(kode):
            s, w = h["profil"][k]["imbal_hasil"][j], WARNA_PROFIL[profil[k]]
            ax.plot([s["p0_5"], s["p99_5"]], [i, i], color=w, lw=1.2, alpha=0.55, solid_capstyle="round", zorder=2)
            ax.plot([s["p5"], s["p95"]], [i, i], color=w, lw=5.5, solid_capstyle="round", zorder=3)
            ax.plot(s["rata"], i, "o", ms=6.5, color=TINTA, mec=PERMUKAAN, mew=1.4, zorder=4)
            ax.text(batas[1] - 0.005, i, f"{_pct(s['rata'])}", fontsize=8, color=TINTA_2, ha="right", va="center",
                    bbox=ALAS, zorder=5)
        ax.set_title(judul)
        ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
        ax.set_xlabel("Imbal hasil setahun")
    kunci = [Line2D([], [], color=REDUP, lw=1.2, label="persentil 0,5-99,5"),
             Line2D([], [], color=REDUP, lw=5.5, label="persentil 5-95"),
             Line2D([], [], marker="o", ls="", ms=6.5, color=TINTA, mec=PERMUKAAN, label="rata-rata (angka di kanan)"),
             Line2D([], [], color=TINTA_2, lw=0.8, label=f"inflasi {_pct(inflasi, 2)}")]
    fig.legend(handles=[Patch(facecolor=w, label=n) for n, w in WARNA_PROFIL.items()] + kunci,
               loc="upper left", bbox_to_anchor=(0.01, 0.995), ncol=7, columnspacing=1.1, handlelength=1.5)
    _simpan(fig, "g2_sebaran_imbal_hasil.png")


# ---------- Gambar 3: porsi investasi yang diakui sebagai AYD ----------
def gambar_ayd(h, kode, label):
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=DPI)
    fig.subplots_adjust(left=0.22, right=0.97, top=0.86, bottom=0.14)
    _sumbu_varian(ax, kode, label)
    ax.set_xlim(0, 1.0)
    _rapikan(ax, "x")
    fig.canvas.draw()
    for i, k in enumerate(kode):
        a = h["ayd"][k]
        batang_tumpuk_h(ax, [(a["porsi_diakui"], BIRU), (a["porsi_tidak_diakui"], JINGGA)], i)
        if a["porsi_tidak_diakui"] > 0:
            ax.text(a["porsi_diakui"] + a["porsi_tidak_diakui"] / 2, i, _pct(a["porsi_tidak_diakui"], 0),
                    fontsize=8, color=TINTA, ha="center", va="center", zorder=5)
    ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
    ax.set_xlabel("Porsi dari jumlah investasi")
    ax.legend(handles=[Patch(facecolor=BIRU, label="Diakui sebagai AYD"),
                       Patch(facecolor=JINGGA, label="Tidak diakui (melampaui batas Pasal 15)")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    _simpan(fig, "g3_uji_ayd.png")


# ---------- Gambar 4: MMBR per modul pada target 120% ----------
def gambar_mmbr(h, kode, label):
    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=DPI)
    fig.subplots_adjust(left=0.21, right=0.97, top=0.86, bottom=0.14)
    _sumbu_varian(ax, kode, label)
    ax.set_xlim(0, 31)
    _rapikan(ax, "x")
    fig.canvas.draw()
    for i, k in enumerate(kode):
        b = h["mmbr"]["pada_target"][k]
        ujung = batang_tumpuk_h(ax, [(b["modul"][m], WARNA_MODUL[m]) for m in WARNA_MODUL], i)
        ax.text(ujung + 0.3, i, angka(b["mmbr"], 1), fontsize=8, color=TINTA, va="center")
    ax.set_xlabel("MMBR per 100 premi")
    ax.legend(handles=[Patch(facecolor=w, label=NAMA_MODUL[m]) for m, w in WARNA_MODUL.items()],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=5, columnspacing=1.3)
    _simpan(fig, "g4_mmbr_per_modul.png")


# ---------- Gambar 5: neraca yang sama dan ekuitas yang diperlukan ----------
def gambar_neraca(h, kode, label, profil):
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), dpi=DPI, sharey=True)
    fig.subplots_adjust(left=0.17, right=0.975, top=0.80, bottom=0.14, wspace=0.08)
    target = h["mmbr"]["target"]

    ax = axs[0]
    _sumbu_varian(ax, kode, label)
    ax.set_xlim(-0.45, 1.5)
    _rapikan(ax, "x")
    for x, teks in ((1.0, "minimum 100%"), (target, f"target {100 * target:.0f}%")):
        ax.axvline(x, color=TINTA_2, lw=0.8, zorder=1)
        ax.text(x, -0.62, teks, fontsize=7.5, color=TINTA_2, ha="right" if x == 1.0 else "left", va="bottom")
    ax.axvline(0, color=SUMBU, lw=1.0, zorder=1)
    fig.canvas.draw()
    for i, k in enumerate(kode):
        r = h["mmbr"]["neraca_sama"][k]["rasio"]
        batang_h(ax, 0, r, i, WARNA_PROFIL[profil[k]])
        geser = 0.02 if r >= 0 else -0.02
        ax.text(r + geser, i, _pct(r, 0), fontsize=8, color=TINTA, va="center", ha="left" if r >= 0 else "right",
                bbox=ALAS, zorder=5)
    ax.set_title("Rasio solvabilitas bila neraca sama", pad=18)
    ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
    ax.set_xlabel(f"Tingkat Solvabilitas / MMBR (neraca {h['profil'][h['mmbr']['varian_acuan']]['label']} pada 120%)")

    ax = axs[1]
    ax.set_xlim(0, 84)
    _rapikan(ax, "x")
    fig.canvas.draw()
    for i, k in enumerate(kode):
        e = h["mmbr"]["pada_target"][k]["ekuitas"]
        batang_h(ax, 0, e, i, WARNA_PROFIL[profil[k]])
        ax.text(e + 1, i, angka(e, 1), fontsize=8, color=TINTA, va="center")
    ax.set_title("Ekuitas untuk mencapai 120%", pad=18)
    ax.set_xlabel("Per 100 premi")
    _legenda_profil(fig, loc="upper left", bbox_to_anchor=(0.01, 0.995), ncol=3)
    _simpan(fig, "g5_neraca_sama_dan_ekuitas.png")


# ---------- Gambar 6: peluang pelanggaran dari risiko investasi saja ----------
def gambar_peluang(h, kode, label):
    fig, ax = plt.subplots(figsize=(7.6, 4.3), dpi=DPI)
    fig.subplots_adjust(left=0.21, right=0.96, top=0.84, bottom=0.13)
    _sumbu_varian(ax, kode, label)
    ax.set_xlim(0, 0.135)
    _rapikan(ax, "x")
    ax.axvline(0.005, color=TINTA_2, lw=0.8, zorder=1)
    ax.text(0.005, -0.62, "ambang 0,5%", fontsize=7.5, color=TINTA_2, ha="left", va="bottom")
    fig.canvas.draw()
    sol = h["solvabilitas_investasi"]["neraca_sendiri"]
    for i, k in enumerate(kode):
        nilai = {j: sol[j][k]["peluang_di_bawah_100"] for j in ("bersama", "panjang")}
        terbesar = max(nilai, key=nilai.get)
        for j, geser, w in (("bersama", -0.17, BIRU), ("panjang", 0.17, JINGGA)):
            batang_h(ax, 0, nilai[j], i + geser, w, tebal=7)
            if j == terbesar:
                ax.text(nilai[j] + 0.002, i + geser, _pct(nilai[j], 2), fontsize=8, color=TINTA, va="center",
                        bbox=ALAS, zorder=5)
    ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
    ax.set_xlabel("Peluang rasio akhir tahun di bawah 100% (awal 120%, hanya hasil investasi yang bergerak)")
    ax.legend(handles=[Patch(facecolor=BIRU, label="Jendela bersama 2012-2024"),
                       Patch(facecolor=JINGGA, label="Jendela panjang 2000-2026")],
              loc="lower left", bbox_to_anchor=(0, 1.05), ncol=2)
    _simpan(fig, "g6_peluang_pelanggaran.png")


# ---------- Gambar 7: tenor SBN di dalam profil Konservatif ----------
def gambar_tenor(h):
    acuan = h["profil"][h["mmbr"]["varian_acuan"]]["label"]
    fig, ax = plt.subplots(figsize=(7.6, 2.7), dpi=DPI)
    fig.subplots_adjust(left=0.15, right=0.80, top=0.74, bottom=0.21)
    tenor = ["2", "5", "10"]
    ax.set_ylim(2.5, -0.6)
    ax.set_yticks(range(3))
    ax.set_yticklabels([f"SBN {t} tahun" for t in tenor])
    ax.set_xlim(-0.14, 0.24)
    _rapikan(ax, "x")
    ax.axvline(0, color=SUMBU, lw=1.0, zorder=1)
    pemicu = h["turunan"]["imbal_hasil_pemicu_pelanggaran"]
    ax.axvline(pemicu, color=TINTA_2, lw=0.8, zorder=1)
    ax.text(pemicu, -0.62, f"bantalan 20% habis di {_pct(pemicu)}", fontsize=7.5, color=TINTA_2, ha="right", va="bottom")
    for i, t in enumerate(tenor):
        s = h["tenor_sbn"][t]["bersama"]
        ax.plot([s["p0_5"], s["p99_5"]], [i, i], color=BIRU, lw=1.2, alpha=0.55, solid_capstyle="round", zorder=2)
        ax.plot([s["p5"], s["p95"]], [i, i], color=BIRU, lw=5.5, solid_capstyle="round", zorder=3)
        ax.plot(s["rata"], i, "o", ms=6.5, color=TINTA, mec=PERMUKAAN, mew=1.4, zorder=4)
        ax.text(1.02, i, f"P(rasio < 100%) = {_pct(s['rasio_akhir']['peluang_di_bawah_100'], 2)}",
                transform=ax.get_yaxis_transform(), fontsize=8, color=TINTA, va="center")
    ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
    ax.set_xlabel(f"Imbal hasil setahun, {acuan}, jendela bersama")
    ax.legend(handles=[Line2D([], [], color=BIRU, lw=1.2, alpha=0.55, label="persentil 0,5-99,5"),
                       Line2D([], [], color=BIRU, lw=5.5, label="persentil 5-95"),
                       Line2D([], [], marker="o", ls="", ms=6.5, color=TINTA, mec=PERMUKAAN, label="rata-rata")],
              loc="lower left", bbox_to_anchor=(0, 1.13), ncol=3)
    _simpan(fig, "g7_tenor_sbn.png")


# ---------- Gambar 8: beban modal aset menurut SEOJK lawan kerugian 1-dalam-200 ----------
def gambar_regulasi_ekonomi(h, kode, label):
    fig, ax = plt.subplots(figsize=(7.6, 3.9), dpi=DPI)
    fig.subplots_adjust(left=0.21, right=0.96, top=0.86, bottom=0.14)
    _sumbu_varian(ax, kode, label)
    ax.set_xlim(0, 21)
    _rapikan(ax, "x")
    for i, k in enumerate(kode):
        v = h["regulasi_vs_ekonomi"][k]
        titik = [(v["beban_mmbr_aset"], BIRU), (v["var_99_5_bersama"], JINGGA), (v["var_99_5_panjang"], TOSKA)]
        ax.plot([min(t[0] for t in titik), max(t[0] for t in titik)], [i, i], color=SUMBU, lw=1.4, zorder=2)
        for x, w in titik:
            ax.plot(x, i, "o", ms=7, color=w, mec=PERMUKAAN, mew=1.4, zorder=4)
    ax.set_xlabel("Per 100 investasi")
    ax.xaxis.set_major_formatter(_koma)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=7, color=BIRU, mec=PERMUKAAN, label="Beban modal aset MMBR"),
                       Line2D([], [], marker="o", ls="", ms=7, color=JINGGA, mec=PERMUKAAN, label="VaR 99,5%, 2012-2024"),
                       Line2D([], [], marker="o", ls="", ms=7, color=TOSKA, mec=PERMUKAAN, label="VaR 99,5%, 2000-2026")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, columnspacing=1.0, handletextpad=0.2)
    _simpan(fig, "g8_regulasi_vs_ekonomi.png")


def main():
    h = json.loads(BERKAS_HASIL.read_text(encoding="utf-8"))
    kode = list(h["profil"])
    label = [h["profil"][k]["label"] for k in kode]
    profil = {k: h["profil"][k]["profil"] for k in kode}
    gambar_data(h)
    gambar_sebaran(h, kode, label, profil)
    gambar_ayd(h, kode, label)
    gambar_mmbr(h, kode, label)
    gambar_neraca(h, kode, label, profil)
    gambar_peluang(h, kode, label)
    gambar_tenor(h)
    gambar_regulasi_ekonomi(h, kode, label)
    print("gambar ditulis ke", DIR_GAMBAR)


if __name__ == "__main__":
    main()
