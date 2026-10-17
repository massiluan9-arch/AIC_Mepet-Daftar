"""Mesin simulasi neraca terpadu satu tahun.

Persamaan inti (per tahun simulasi, per 100 premi dicatat):
    G = U + I(a) - L(m) - F(a, m)
    R = [ s x MMBR(a) + G - pajak x max(G, 0) ] / [ MMBR(a) + fck x porsi_belum_dibayar x L(m) ]
U  hasil underwriting di luar bencana; I hasil investasi; L kerugian bencana; F biaya jual paksa.
Model hasil investasi dan MMBR dipakai ulang dari analisis/3_investasi_mmbr/kode; kerugian bencana dibaca
dari 2_model_bencana/keluaran (keluaran R).
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

DIR_F = Path(__file__).resolve().parents[1]
DIR_TERPADU = DIR_F.parent
AKAR = DIR_TERPADU.parent
DIR_BENCANA = DIR_TERPADU / "2_model_bencana" / "keluaran"
DIR_DATA = DIR_TERPADU / "1_olah_data" / "data"
DIR_KELUAR = DIR_F / "keluaran"
DIR_TABEL = DIR_KELUAR / "tabel"
DIR_GAMBAR = DIR_KELUAR / "gambar"
sys.path.insert(0, str(AKAR / "analisis" / "3_investasi_mmbr" / "kode"))

import data_pasar as dp          # noqa: E402
import mmbr as mm                # noqa: E402
import model_investasi as mi     # noqa: E402
from umum import daftar_varian, muat_parameter   # noqa: E402

MODUL = mm.MODUL
KURVA_TUNGGAL = ["aulady", "klaim", "pager"]


def muat_semua():
    """Parameter 05 (regulasi, profil, neraca dasar, pasar) dan parameter terpadu."""
    p05 = muat_parameter()
    pt = yaml.safe_load((DIR_F / "parameter_terpadu.yaml").read_text(encoding="utf-8"))
    return p05, pt


# ---------------------------------------------------------------- pasar
def siapkan_pasar(p05, n, jendela="bersama", blok=None, **opsi):
    """Imbal hasil setahun tiap instrumen, dengan benih yang sama seperti analisis/3_investasi_mmbr."""
    pasar = p05["pasar"]
    bs, awal = pasar["bootstrap"], pasar["kondisi_awal"]

    def rng(i):
        return np.random.default_rng([bs["benih"], i])

    kurva = dp.muat_kurva(awal["kurva"]["berkas"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ch = dp.perubahan_bulanan(dp.muat_deret())
    bersama = dp.jendela_bersama(ch, *bs["jendela_bersama"])
    if jendela == "panjang":
        data, _ = dp.jendela_panjang(ch, bersama, *bs["jendela_panjang"], rng(1))
        benih = 11
    else:
        data, benih = bersama, 10
    faktor = mi.bootstrap_faktor(data, n, blok or bs["panjang_blok_bulan"],
                                 awal["bunga_deposito_1_bulan"]["nilai"], rng(benih))
    seragam = rng(20).random((n, pasar["instrumen"]["korporasi"]["jumlah_emiten"]))
    imbal = mi.imbal_instrumen(faktor, kurva, pasar, seragam, **opsi)
    tanpa_gagal = mi.imbal_instrumen(faktor, kurva, pasar, seragam, pengali_gagal=0.0, **opsi)["korporasi"]
    return {"imbal": imbal, "korporasi_tanpa_gagal": tanpa_gagal, "inflasi": awal["inflasi_tahunan"]["nilai"]}


# ---------------------------------------------------------------- bencana
def muat_strategi(pt):
    """Tabel strategi: eksposur ditahan dan faktor premi gempa (eksposur x skala syarat polis)."""
    df = pd.read_csv(DIR_BENCANA / "04_strategi.csv")
    skala = {k: v["nilai"] for k, v in pt["skala_premi_syarat"].items()}
    meta = json.loads((DIR_BENCANA / "04_meta.json").read_text(encoding="utf-8"))
    porsi_besar = meta.get("porsi_eksposur_risiko_besar")
    if porsi_besar is not None:
        skala["batas20_besar"] = porsi_besar * skala["batas20"] + (1.0 - porsi_besar)
    df["skala_syarat"] = df["syarat"].map(skala)
    # Strategi bersasaran: sebagian premi mengikuti skala syarat khusus, sisanya skala syarat dasar.
    if "syarat_khusus" in df.columns:
        khusus = df["syarat_khusus"].fillna("").astype(str)
        porsi = df["porsi_premi_khusus"].where(khusus != "", 0.0)
        skala_khusus = khusus.map(skala).fillna(0.0)
        df["skala_syarat"] = porsi * skala_khusus + (1.0 - porsi) * df["skala_syarat"]
    df["faktor_premi_gempa"] = df["premi_gempa_ditahan"] * df["skala_syarat"]
    return df.set_index("strategi")


def muat_ylt(kurva, benih, n):
    """Kerugian tahunan dan kerugian kejadian terbesar per strategi (fraksi nilai pertanggungan gempa).

    Urutan tahun diacak sekali dengan benih tetap supaya pasangan dengan tahun pasar bebas dari
    urutan berkas. Acakan yang sama dipakai untuk semua kurva dan strategi.
    """
    if kurva == "campuran":
        df = pd.read_csv(DIR_BENCANA / "05_ylt_campuran.csv.gz")
        awalan = ("jumlah.", "maks.")
    else:
        df = pd.read_csv(DIR_BENCANA / "04_ylt.csv.gz")
        awalan = (f"jumlah.{kurva}.", f"maks.{kurva}.")
    assert len(df) >= n, "tahun simulasi bencana lebih sedikit daripada yang diminta"
    urut = np.random.default_rng(benih).permutation(len(df))[:n]
    out = {}
    for kol in df.columns:
        if kol.startswith(awalan[0]):
            st = kol[len(awalan[0]):]
            out[st] = (df[kol].to_numpy()[urut], df[awalan[1] + st].to_numpy()[urut])
    return out


def urutkan_berkorelasi(acuan, ylt, rho, benih):
    """Menyusun ulang tahun bencana sehingga kerugian besar cenderung jatuh pada tahun pasar yang buruk.

    Kopula Gauss dengan korelasi peringkat mendekati rho antara kerugian bencana dan penurunan `acuan`.
    """
    n = len(acuan)
    from scipy.stats import norm, rankdata
    z_pasar = norm.ppf(rankdata(-acuan) / (n + 1))               # besar = tahun pasar buruk
    z = rho * z_pasar + np.sqrt(1 - rho ** 2) * np.random.default_rng(benih).standard_normal(n)
    peringkat = rankdata(z, method="ordinal").astype(int) - 1     # 0 = paling kecil
    dasar = next(iter(ylt.values()))[0]
    urut_naik = np.argsort(dasar, kind="stable")
    indeks = urut_naik[peringkat]
    return {st: (j[indeks], m[indeks]) for st, (j, m) in ylt.items()}


# ---------------------------------------------------------------- aturan peluang (Rev. 2)
def selang_binomial(k, n, tingkat=0.95):
    """Selang Clopper-Pearson (eksak) dua sisi untuk peluang binomial dari k kejadian dalam n tahun."""
    from scipy.stats import beta
    a = (1.0 - tingkat) / 2.0
    bawah = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    atas = 1.0 if k == n else float(beta.ppf(1.0 - a, k + 1, n - k))
    return bawah, atas


def pelanggaran_terbanyak(ambang, n, tingkat=0.95):
    """Jumlah pelanggaran terbanyak yang batas atas selangnya masih tidak melebihi ambang."""
    k = int(ambang * n)
    while k >= 0 and selang_binomial(k, n, tingkat)[1] > ambang:
        k -= 1
    return k


def ambang_aturan(pt, n, aturan=None):
    """Ambang atas taksiran titik P(R < 100%) yang setara dengan aturan keputusan.

    aturan "titik": taksiran titik tidak melebihi ambang (Rev. 1). aturan "batas_atas": batas atas selang
    Clopper-Pearson tidak melebihi ambang, yaitu jumlah pelanggaran paling banyak pelanggaran_terbanyak().
    """
    ambang = pt["meta"]["ambang_peluang"]
    aturan = aturan or pt["meta"].get("aturan_peluang", "titik")
    if aturan == "titik":
        return ambang
    k = pelanggaran_terbanyak(ambang, n, pt["meta"].get("tingkat_selang", 0.95))
    return (k + 0.5) / n


def ringkas_peluang(p, n, tingkat=0.95):
    k = int(round(p * n))
    bawah, atas = selang_binomial(k, n, tingkat)
    return {"jumlah_pelanggaran": k, "jumlah_tahun": n, "peluang": k / n, "selang_bawah": bawah, "selang_atas": atas, "tingkat_selang": tingkat}


# ---------------------------------------------------------------- likuiditas
def jual_paksa(kebutuhan, kas, posisi, potongan, urutan):
    """Biaya mencairkan aset untuk membayar klaim satu kejadian; sisa = kebutuhan yang tidak tertutup."""
    sisa = np.maximum(kebutuhan - kas, 0.0)
    biaya = np.zeros_like(sisa)
    for k in urutan:
        tunai = posisi.get(k, 0.0) * (1.0 - potongan[k])
        ambil = np.minimum(sisa, tunai)
        biaya += ambil * potongan[k] / (1.0 - potongan[k])
        sisa = sisa - ambil
    return biaya, sisa


# ---------------------------------------------------------------- inti
class Mesin:
    """Menyimpan bilangan acak bersama supaya semua perbandingan memakai tahun simulasi yang sama."""

    def __init__(self, p05, pt, n=None):
        self.p05, self.pt = p05, pt
        self.n = n or pt["meta"]["jumlah_tahun"]
        self.reg, self.neraca = p05["regulasi"], p05["neraca_dasar"]
        self.nilai = mm.nilai_neraca(self.neraca)
        self.varian = {kode: (nama, label, bobot) for kode, nama, label, bobot in daftar_varian(p05["profil"])}
        self.strategi = muat_strategi(pt)
        self.pasar = {"bersama": siapkan_pasar(p05, self.n)}
        benih = pt["meta"]["benih_pasangan"]
        self.ylt = {"campuran": muat_ylt("campuran", benih, self.n)}
        rng = np.random.default_rng([benih, 1])
        self.z_klaim = rng.standard_normal(self.n)
        self.z_beban = rng.standard_normal(self.n)
        self._neraca_cache = {}

    def pasar_untuk(self, kunci, **opsi):
        if kunci not in self.pasar:
            self.pasar[kunci] = siapkan_pasar(self.p05, self.n, **opsi)
        return self.pasar[kunci]

    def ylt_untuk(self, kurva):
        if kurva not in self.ylt:
            self.ylt[kurva] = muat_ylt(kurva, self.pt["meta"]["benih_pasangan"], self.n)
        return self.ylt[kurva]

    def neraca_awal(self, kode, s, **opsi_mmbr):
        kunci = (kode, round(s, 6), tuple(sorted(opsi_mmbr.items())))
        if kunci not in self._neraca_cache:
            self._neraca_cache[kunci] = mm.neraca_pada_target(s, self.varian[kode][2], self.nilai, self.neraca,
                                                              self.reg, **opsi_mmbr)
        return self._neraca_cache[kunci]

    def jalankan(self, kode, st, s, kurva="campuran", pasar="bersama", ylt=None, eksposur=None,
                 rasio_klaim=None, pengali_simpangan_klaim=1.0, komisi=None, porsi_belum_dibayar=None,
                 pengali_potongan=1.0, opsi_mmbr=None, rinci=False, investasi=None):
        """Satu konfigurasi: profil `kode`, strategi `st`, target awal `s`.

        Bila `investasi` diisi, neraca disusun dari jumlah investasi itu (ekuitas sama antarprofil)
        dan `s` diabaikan; rasio awal dilaporkan pada kunci `target`.
        """
        pt, n = self.pt, self.n
        bobot = self.varian[kode][2]
        if investasi is None:
            b = self.neraca_awal(kode, s, **(opsi_mmbr or {}))
        else:
            b = mm.susun_neraca(investasi, bobot, self.nilai, self.neraca, self.reg, **(opsi_mmbr or {}))
            s = b["rasio"]
        inv, mmbr, ts0 = b["investasi"], b["mmbr"], b["tingkat_solvabilitas"]
        psr = self.pasar[pasar]
        posisi = {k: inv * w for k, w in bobot.items()}

        # hasil investasi dan pemisahan kerugian kredit / pasar
        hasil = {k: posisi[k] * psr["imbal"][k] for k in posisi}
        I = sum(hasil.values())
        rugi_kredit = posisi.get("korporasi", 0.0) * (psr["korporasi_tanpa_gagal"] - psr["imbal"]["korporasi"]) \
            if "korporasi" in posisi else np.zeros(n)
        hasil_pasar = I - hasil.get("deposito", 0.0) + rugi_kredit
        rugi_pasar = np.maximum(-hasil_pasar, 0.0)

        # underwriting di luar bencana
        E = pt["bencana"]["eksposur_per_premi"]["nilai"] if eksposur is None else eksposur
        tsi = 100.0 * E
        premi_gempa = tsi * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000.0
        f_premi = float(self.strategi.loc[st, "faktor_premi_gempa"])
        premi = 100.0 - premi_gempa * (1.0 - f_premi)
        uw = pt["underwriting"]
        rata = uw["rasio_klaim_non_bencana"]["rata"] if rasio_klaim is None else rasio_klaim
        simp = uw["rasio_klaim_non_bencana"]["simpangan"] * pengali_simpangan_klaim
        sig2 = np.log1p((simp / rata) ** 2)
        klaim_nb = 100.0 * rata * np.exp(np.sqrt(sig2) * self.z_klaim - sig2 / 2.0)
        kms = (uw["komisi"]["nilai"] if komisi is None else komisi) * premi
        beban_rata = uw["beban_usaha"]["nilai"]
        lebih_beban = uw["beban_usaha"]["simpangan"] * self.z_beban
        U = premi - klaim_nb - kms - beban_rata - lebih_beban

        # bencana dan likuiditas
        jumlah, maks = (ylt or self.ylt_untuk(kurva))[st]
        L = tsi * jumlah
        klaim_kejadian = tsi * maks
        lk = pt["likuiditas"]
        potongan = {k: v["nilai"] * pengali_potongan for k, v in lk["potongan_harga"].items()}
        kas = self.nilai["kas_dan_bank"]
        F, kurang = jual_paksa(klaim_kejadian, kas, posisi, potongan, lk["urutan_cair"])
        siap_cair = kas + posisi.get("deposito", 0.0) + posisi.get("sbn", 0.0)

        G = U + I - L - F
        pajak = uw["pajak"]["nilai"] * np.maximum(G, 0.0)
        porsi_os = pt["bencana"]["porsi_klaim_belum_dibayar_akhir_tahun"]["nilai"] \
            if porsi_belum_dibayar is None else porsi_belum_dibayar
        fck = self.reg["faktor_risiko"]["asuransi"]["harta_benda"]["fck"]
        R = (ts0 + G - pajak) / (mmbr + fck * porsi_os * L)

        gagal = R < 1.0
        p = float(gagal.mean())
        out = {
            "varian": kode, "strategi": st, "target": s, "investasi": inv, "mmbr": mmbr, "ekuitas": b["ekuitas"],
            "tingkat_solvabilitas": ts0, "premi": premi, "premi_dilepas": 100.0 - premi,
            "peluang_di_bawah_100": p, "galat_baku_peluang": float(np.sqrt(p * (1 - p) / n)),
            "peluang_di_bawah_120": float((R < 1.2).mean()),
            "peluang_di_bawah_0": float((R < 0.0).mean()),
            # Defisit harapan: rata-rata kekurangan AYD terhadap liabilitas pada akhir tahun (per 100 premi)
            "defisit_harapan": float(np.maximum(-(ts0 + G - pajak), 0.0).mean()),
            "rasio_rata": float(R.mean()), "rasio_p0_5": float(np.quantile(R, 0.005)),
            "rasio_p5": float(np.quantile(R, 0.05)), "rasio_median": float(np.median(R)),
            "rata_rasio_di_ekor_0_5": float(R[R <= np.quantile(R, 0.005)].mean()),
            "laba_bersih_rata": float((G - pajak).mean()), "U_rata": float(U.mean()), "I_rata": float(I.mean()),
            "L_rata": float(L.mean()), "L_var_99_5": float(np.quantile(L, 0.995)),
            "L_tvar_99_5": float(L[L >= np.quantile(L, 0.995)].mean()),
            "klaim_kejadian_var_99_5": float(np.quantile(klaim_kejadian, 0.995)),
            "F_rata": float(F.mean()), "F_var_99_5": float(np.quantile(F, 0.995)),
            "aset_siap_cair": siap_cair,
            "peluang_kurang_likuiditas": float((klaim_kejadian > siap_cair).mean()),
            "peluang_aset_tidak_cukup": float((kurang > 0).mean()),
            "imbal_hasil_rata": float(I.mean() / inv), "imbal_hasil_riil": float((1 + I.mean() / inv) / (1 + psr["inflasi"]) - 1),
        }
        if rinci:
            teknis = premi - klaim_nb - kms - beban_rata - L
            rugi = {"kredit": rugi_kredit, "likuiditas": F, "pasar": rugi_pasar,
                    "asuransi": np.maximum(-teknis, 0.0), "operasional": np.maximum(lebih_beban, 0.0)}
            matriks = np.column_stack([rugi[m] for m in MODUL])
            pemicu = matriks[gagal].argmax(axis=1) if gagal.any() else np.array([], dtype=int)
            out["modul"] = {}
            # Rev. 2. Ukuran tambahan per modul:
            #  - penyangga = 20% MMBR, yaitu jarak dari target 120% ke batas 100%;
            #  - definisi seragam: hasil modul sebagai komponen laba (makin besar makin baik) dibandingkan dengan nilai
            #    harapannya; "simpangan" = harapan - realisasi, sehingga kelima modul diukur dengan cara yang sama;
            #  - peluang_tanpa_modul: P(R < 100%) bila kerugian modul itu dinolkan;
            #  - disimulasikan: False bila jalur kerugian modul tidak ada pada konfigurasi ini (kredit tanpa obligasi korporasi).
            penyangga = 0.2 * mmbr
            hasil_modul = {"kredit": -rugi_kredit, "likuiditas": -F, "pasar": hasil_pasar, "asuransi": teknis, "operasional": -lebih_beban}
            ambang_seragam = {"0_5": 0.5, "1": 1.0, "2": 2.0, "penyangga": penyangga, "5": 5.0, "10": 10.0, "ekuitas": b["ekuitas"]}
            out["penyangga_20_persen_mmbr"] = penyangga
            out["ambang_seragam"] = ambang_seragam
            for i, m in enumerate(MODUL):
                x = rugi[m]
                beban = b["modul"][m]
                G_tanpa = G + x
                R_tanpa = (ts0 + G_tanpa - uw["pajak"]["nilai"] * np.maximum(G_tanpa, 0.0)) / (mmbr + fck * porsi_os * L)
                simpang = hasil_modul[m].mean() - hasil_modul[m]
                tambahan = {"disimulasikan": bool(m != "kredit" or "korporasi" in posisi),
                            "peluang_melampaui_penyangga": float((x > penyangga).mean()),
                            "peluang_di_bawah_100_tanpa_modul": float((R_tanpa < 1.0).mean()),
                            "hasil_harapan": float(hasil_modul[m].mean()), "simpangan_baku_hasil": float(hasil_modul[m].std())}
                tambahan.update({f"simpangan_lebih_{k}": float((simpang > t).mean()) for k, t in ambang_seragam.items()})
                out["modul"][m] = {
                    "beban_modal": beban, "porsi_mmbr": b["porsi_modul"][m],
                    "peluang_rugi": float((x > 1e-9).mean()),
                    "peluang_melampaui_beban": float((x > beban).mean()),
                    "rugi_rata": float(x.mean()), "rugi_var_99_5": float(np.quantile(x, 0.995)),
                    "rugi_tvar_99_5": float(x[x >= np.quantile(x, 0.995)].mean()),
                    "porsi_tahun_gagal_dipicu": float((pemicu == i).mean()) if len(pemicu) else 0.0,
                    **tambahan,
                }
            out["deret"] = {"R": R, "G": G, "U": U, "I": I, "L": L, "F": F, "klaim_kejadian": klaim_kejadian}
        return out

    def rasio_skenario(self, kode, st, s, kerugian_fraksi, imbal=None, eksposur=None, rasio_klaim=None, komisi=None):
        """Rasio akhir tahun bila satu kejadian dengan kerugian `kerugian_fraksi` (fraksi nilai
        pertanggungan gempa awal) terjadi, sedangkan underwriting dan investasi berjalan pada nilai harapan."""
        pt = self.pt
        bobot = self.varian[kode][2]
        b = self.neraca_awal(kode, s)
        E = pt["bencana"]["eksposur_per_premi"]["nilai"] if eksposur is None else eksposur
        tsi = 100.0 * E
        uw = pt["underwriting"]
        premi = 100.0 - tsi * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000.0 * (1.0 - float(self.strategi.loc[st, "faktor_premi_gempa"]))
        rata_klaim = uw["rasio_klaim_non_bencana"]["rata"] if rasio_klaim is None else rasio_klaim
        tarif_komisi = uw["komisi"]["nilai"] if komisi is None else komisi
        U = premi - 100.0 * rata_klaim - tarif_komisi * premi - uw["beban_usaha"]["nilai"]
        if imbal is None:
            imbal = float(mi.imbal_portofolio(bobot, self.pasar["bersama"]["imbal"]).mean())
        posisi = {k: b["investasi"] * w for k, w in bobot.items()}
        lk = pt["likuiditas"]
        potongan = {k: v["nilai"] for k, v in lk["potongan_harga"].items()}
        L = tsi * kerugian_fraksi
        F, kurang = jual_paksa(np.array([L]), self.nilai["kas_dan_bank"], posisi, potongan, lk["urutan_cair"])
        G = U + b["investasi"] * imbal - L - float(F[0])
        rasio = (b["tingkat_solvabilitas"] + G - uw["pajak"]["nilai"] * max(G, 0.0)) / b["mmbr"]
        return {"rasio_akhir": rasio, "kerugian": L, "laba_sebelum_pajak": G, "biaya_jual_paksa": float(F[0]),
                "kekurangan_kas": float(kurang[0]), "premi": premi, "ekuitas": b["ekuitas"], "mmbr": b["mmbr"]}

    def target_minimum(self, kode, st, ambang=None, **opsi):
        """Target solvabilitas awal terkecil pada kisi yang membuat P(R < 100%) tidak melebihi ambang."""
        ambang = self.pt["meta"]["ambang_peluang"] if ambang is None else ambang
        kisi = self.pt["target_solvabilitas"]["kisi"]
        nilai = np.arange(kisi["awal"], kisi["akhir"] + 1e-9, kisi["langkah"])

        def lolos(i):
            return self.jalankan(kode, st, float(nilai[i]), **opsi)["peluang_di_bawah_100"] <= ambang

        # P(R < 100%) turun bila target naik, jadi cukup bagi dua pada kisi.
        if lolos(0):
            return float(round(nilai[0], 2))
        if not lolos(len(nilai) - 1):
            return None
        bawah, atas = 0, len(nilai) - 1
        while atas - bawah > 1:
            tengah = (bawah + atas) // 2
            if lolos(tengah):
                atas = tengah
            else:
                bawah = tengah
        return float(round(nilai[atas], 2))
