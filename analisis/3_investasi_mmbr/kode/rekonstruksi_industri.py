"""Uji kewajaran: menghitung ulang MMBR industri asuransi umum dari neraca publik OJK.

Tujuannya memeriksa apakah faktor SEOJK 24/2017 yang diterapkan pada neraca publik menghasilkan
rasio solvabilitas yang seorde dengan angka resmi. Data peringkat, jatuh tempo, dan pembagian
aset reasuransi tidak dipublikasikan, jadi hasilnya berupa rentang antara dua set asumsi.
"""
import warnings

import openpyxl

from umum import AKAR

BERKAS = AKAR / "data" / "industri_asuransi" / "ojk_statistik_2025" / "OJK_Statistik_Asuransi_Juli_2025.xlsx"
KOLOM_JULI = 8
BULAN = 7


def _baca_lembar(wb, nama):
    out = {}
    for r in wb[nama].iter_rows(values_only=True):
        if isinstance(r[0], (int, float)) and isinstance(r[1], str) and isinstance(r[KOLOM_JULI], (int, float)):
            out[r[1].strip()] = float(r[KOLOM_JULI])
    return out


def baca_industri():
    """Neraca dan laba rugi asuransi umum konvensional, Juli 2025, juta rupiah."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(BERKAS, read_only=True, data_only=True)
    fp = _baca_lembar(wb, "FP-General Insurance")
    lr = _baca_lembar(wb, "IS-General Insurance")
    rasio_resmi = None
    blok = None
    for r in wb["Ratio"].iter_rows(values_only=True):
        teks = " ".join(str(c) for c in r if isinstance(c, str))
        if "Rasio Asuransi Umum Konvensional" in teks:
            blok = "umum"
        elif "Rasio Reasuransi" in teks or "Rasio Asuransi Jiwa" in teks:
            blok = None
        if blok == "umum" and "Rasio Tingkat Solvabilitas" in teks:
            rasio_resmi = float(r[9])
    return fp, lr, rasio_resmi


def rasio_per_100_premi_langsung(fp, lr):
    """Rasio industri yang dipakai parameter/neraca_dasar.yaml (untuk kode/uji.py)."""
    premi = lr["Premi Penutupan Langsung"] * 12 / BULAN
    bua = (lr["Beban Pegawai dan Pengurus"] + lr["Beban Umum dan Administrasi lainnya"]) * 12 / BULAN
    utang_lain = (fp["Utang Komisi"] + fp["Utang Pajak"] + fp["Biaya yang Masih Harus Dibayar"] + fp["Utang Lain"])
    return {
        "premi_langsung_disetahunkan": premi,
        "cadangan_bencana": 100 * fp["Cadangan atas Risiko Bencana (Catastrophic)"] / premi,
        "utang_klaim": 100 * fp["Utang Klaim"] / premi,
        "utang_lain": 100 * utang_lain / premi,
        "kas_dan_bank": 100 * fp["Kas dan Bank"] / premi,
        "tagihan_premi_industri": 100 * fp["Tagihan Premi Penutupan Langsung"] / premi,
        "bua_dikurangi_bpl": 100 * bua / premi,
        "dac": 100 * fp["Biaya Akuisisi yang Ditangguhkan"] / premi,
        "investasi": 100 * fp["Jumlah Investasi"] / premi,
    }


# Dua set asumsi untuk butir yang tidak dipublikasikan.
ASUMSI = {
    "faktor_rendah": {
        "keterangan": "Bank dan emiten AAA, reasuradur dalam negeri, reksa dana non-saham, saham IDX30, "
                      "penyertaan diawasi OJK, tanpa beban atas cadangan premi jangka panjang dan likuiditas",
        "deposito": 0.012, "obligasi": 0.016, "reasuransi": 0.028, "reksadana": 0.06, "saham": 0.15,
        "penyertaan": 0.10, "properti_investasi": 0.07, "fcp": 0.25, "fck": 0.20,
        "cadangan_premi": 0.0, "likuiditas_porsi_cadangan_neto": 0.0,
    },
    "faktor_tinggi": {
        "keterangan": "Bank dan emiten A, reasuradur klaster 3, reksa dana saham, saham di luar IDX30, "
                      "penyertaan tidak diawasi OJK, beban 10% atas cadangan premi jangka panjang, "
                      "kekurangan likuiditas 30% cadangan neto",
        "deposito": 0.030, "obligasi": 0.040, "reasuransi": 0.060, "reksadana": 0.16, "saham": 0.20,
        "penyertaan": 0.20, "properti_investasi": 0.15, "fcp": 0.30, "fck": 0.25,
        "cadangan_premi": 0.10, "likuiditas_porsi_cadangan_neto": 0.30,
    },
}


def rekonstruksi():
    fp, lr, rasio_resmi = baca_industri()
    # AYD: seluruh investasi kecuali "Investasi Lain", ditambah aset bukan investasi yang diperkenankan.
    ayd = (fp["Jumlah Investasi"] - fp["Investasi Lain"] + fp["Kas dan Bank"]
           + fp["Tagihan Premi Penutupan Langsung"] + fp["Tagihan Premi Reasuransi"] + fp["Aset Reasuransi"]
           + fp["Tagihan Klaim Koasuransi"] + fp["Tagihan Klaim Reasuransi"] + fp["Tagihan Investasi"]
           + fp["Tagihan Hasil Investasi"]
           + fp["Bangunan dengan Hak Strata atau Tanah dengan Bangunan untuk Dipakai Sendiri"])
    ts = ayd - fp["Jumlah Liabilitas"]
    cadangan_bruto = fp["Jumlah Cadangan Teknis"]
    retensi = 1 - fp["Aset Reasuransi"] / cadangan_bruto
    bua = (lr["Beban Pegawai dan Pengurus"] + lr["Beban Umum dan Administrasi lainnya"]) * 12 / BULAN

    hasil = {"tanggal": "2025-07-31", "satuan": "juta rupiah", "ayd": ayd,
             "liabilitas": fp["Jumlah Liabilitas"], "tingkat_solvabilitas": ts,
             "ekuitas": fp["Jumlah Ekuitas"], "porsi_cadangan_retensi_sendiri": retensi,
             "rasio_resmi_ojk": rasio_resmi,
             "catatan_rasio_resmi": "Lembar Ratio; gabungan asuransi umum dan reasuransi, nilainya sama di semua bulan pada berkas.",
             "skenario": {}}
    for nama, a in ASUMSI.items():
        kredit = (fp["Deposito Berjangka"] * a["deposito"]
                  + (fp["Obligasi Korporasi"] + fp["MTN"]) * a["obligasi"]
                  + fp["Tagihan Premi Penutupan Langsung"] * 0.08
                  + fp["Tagihan Premi Reasuransi"] * 0.028
                  + fp["Aset Reasuransi"] * a["reasuransi"]
                  + (fp["Tagihan Klaim Koasuransi"] + fp["Tagihan Klaim Reasuransi"]) * a["reasuransi"]
                  + (fp["Tagihan Investasi"] + fp["Tagihan Hasil Investasi"]) * 0.02)
        pasar = (fp["Saham"] * a["saham"] + fp["Reksa Dana"] * a["reksadana"]
                 + fp["Penyertaan Langsung"] * a["penyertaan"]
                 + fp["Tanah, Bangunan dengan Hak Strata, atau Tanah dengan Bangunan, untuk Investasi"] * a["properti_investasi"]
                 + fp["Bangunan dengan Hak Strata atau Tanah dengan Bangunan untuk Dipakai Sendiri"] * 0.04)
        asuransi = retensi * (fp["Cadangan Atas Premi Yang Belum Merupakan Pendapatan"] * a["fcp"]
                              + fp["Cadangan Klaim"] * a["fck"]
                              + fp["Cadangan Premi"] * a["cadangan_premi"]
                              + fp["Cadangan atas Risiko Bencana (Catastrophic)"] * 0.25)
        likuiditas = 0.04 * a["likuiditas_porsi_cadangan_neto"] * retensi * cadangan_bruto
        operasional = 0.01 * bua + 0.5 * fp["Biaya Akuisisi yang Ditangguhkan"]
        modul = {"kredit": kredit, "likuiditas": likuiditas, "pasar": pasar,
                 "asuransi": asuransi, "operasional": operasional}
        total = sum(modul.values())
        hasil["skenario"][nama] = {"keterangan": a["keterangan"], "modul": modul, "mmbr": total,
                                   "porsi": {k: v / total for k, v in modul.items()},
                                   "rasio": ts / total}
    return hasil
