"""Menyusun LAPORAN.md dan KONTEKS_AI.yaml dari templat dan keluaran/hasil.json.

Semua angka di kedua dokumen diisi dari hasil.json, jadi keduanya tidak bisa berbeda dari
keluaran model. Penanda pada templat:
  {{jalur.ke.nilai|format}}  nilai dari hasil.json; format p0-p2 (persen), q2 (poin persentase),
                             a0-a2 (angka, desimal koma), n2/n4 (angka mentah bertitik untuk YAML),
                             t (teks).
  {{tabel:nama}}             tabel markdown yang dibangun fungsi di berkas ini.
  {{yaml:nama}}              blok YAML yang dibangun fungsi di berkas ini.
"""
import json
import re

import yaml

from umum import BERKAS_HASIL, DIR_ANALISIS, angka, muat_parameter, persen

DIR_KODE = DIR_ANALISIS / "kode"
MODUL = ["asuransi", "kredit", "pasar", "likuiditas", "operasional"]
NAMA_INSTRUMEN = {"sbn": "SBN 5 tahun", "deposito": "Deposito 1 bulan", "korporasi": "Obligasi korporasi AA 3 tahun",
                  "saham": "Saham (LQ45 + dividen)", "reksadana_saham": "Reksa dana saham (IHSG)"}
NAMA_UJI_INVESTASI = {
    "tenor_sbn_2": "SBN 2 tahun", "tenor_sbn_10": "SBN 10 tahun", "korporasi_AAA": "Obligasi korporasi AAA",
    "gagal_bayar_x3": "Peluang gagal bayar x 3", "selisih_melebar": "Selisih melebar saat saham turun",
    "dimiliki_hingga_jatuh_tempo": "Obligasi dimiliki hingga jatuh tempo", "tanpa_dividen": "Tanpa dividen saham",
    "blok_3": "Blok bootstrap 3 bulan", "blok_12": "Blok bootstrap 12 bulan",
}
NAMA_UJI_MMBR = {
    "peringkat_AAA": "Bank dan emiten AAA", "peringkat_A": "Bank dan emiten A",
    "saham_luar_idx30": "Saham di luar IDX30 (faktor 20%)",
    "hingga_jatuh_tempo_sbn_2": "Obligasi dimiliki hingga jatuh tempo, SBN 2 tahun",
    "hingga_jatuh_tempo_sbn_5": "Obligasi dimiliki hingga jatuh tempo, SBN 5 tahun",
    "hingga_jatuh_tempo_sbn_10": "Obligasi dimiliki hingga jatuh tempo, SBN 10 tahun",
    "capybmp_50": "CAPYBMP 50 per 100 premi", "cadangan_bencana_5": "Cadangan bencana 5 per 100 premi",
    "klaim_semua_di_bawah_1_tahun": "Seluruh cadangan klaim jatuh tempo di bawah 1 tahun",
}


def md(kepala, baris, rata=None):
    rata = rata or ["---"] + ["---:"] * (len(kepala) - 1)
    out = ["| " + " | ".join(kepala) + " |", "| " + " | ".join(rata) + " |"]
    out += ["| " + " | ".join(str(c) for c in b) + " |" for b in baris]
    return "\n".join(out)


def p(x, d=1):
    return persen(x, d)


def a(x, d=2):
    return angka(x, d)


# ---------- tabel ----------
def tabel_kondisi_awal(h, par):
    k = h["data"]["kondisi_awal"]
    return md(["Butir", "Nilai", "Sumber"], [
        ["BI-Rate", p(k["bi_rate"], 2), "Bank Indonesia, RDG 22-23 September 2026"],
        ["Inflasi tahunan", p(k["inflasi"], 2), "BPS, September 2026"],
        ["Imbal hasil SBN 2 / 5 / 10 tahun", f"{p(k['sbn_2'], 2)} / {p(k['sbn_5'], 2)} / {p(k['sbn_10'], 2)}", "PHEI, 9 Oktober 2026"],
        ["Imbal hasil obligasi korporasi 3 tahun, AAA / AA", f"{p(k['korporasi_AAA_3'], 2)} / {p(k['korporasi_AA_3'], 2)}", "PHEI, 9 Oktober 2026"],
        ["Bunga deposito rupiah 1 bulan", p(k["deposito_1_bulan"], 2), "BI, SEKI Tabel I.28, Agustus 2026"],
        ["LQ45 sejak awal 2026", p(h["data"]["deskriptif"]["saham_2026_sejak_awal_tahun"]["lq45"]), "Yahoo Finance, penutupan Oktober 2026"],
    ], ["---", "---:", "---"])


def tabel_deskriptif(h, par):
    d = h["data"]["deskriptif"]
    t, c = d["tingkat"], d["perubahan_12_bulan"]
    return md(["Ukuran", "Nilai"], [
        ["Bulan pada jendela bersama (Feb 2012 - Des 2024)", d["jumlah_bulan_bersama"]],
        ["Imbal hasil SBN 10 tahun: rata-rata (rentang)", f"{a(t['y10']['rata'])}% ({a(t['y10']['min'])}% sampai {a(t['y10']['maks'])}%)"],
        ["Imbal hasil SBN 2 tahun: rata-rata (rentang)", f"{a(t['y2']['rata'])}% ({a(t['y2']['min'])}% sampai {a(t['y2']['maks'])}%)"],
        ["Perubahan imbal hasil 10 tahun dalam 12 bulan: simpangan baku; persentil 95; terbesar", f"{a(c['y10']['simpangan'])}; +{a(c['y10']['p95'])}; +{a(c['y10']['maks'])} poin"],
        ["Imbal hasil LQ45 12 bulan, 2012-2024: rata-rata; simpangan baku; terburuk", f"{p(c['lq45_2012_2024']['rata'])}; {p(c['lq45_2012_2024']['simpangan'])}; {p(c['lq45_2012_2024']['min'])}"],
        ["Imbal hasil LQ45 12 bulan, 2000-2026: rata-rata; simpangan baku; terburuk", f"{p(c['lq45_2000_2026']['rata'])}; {p(c['lq45_2000_2026']['simpangan'])}; {p(c['lq45_2000_2026']['min'])}"],
        ["Korelasi bulanan perubahan imbal hasil 10 tahun dan imbal hasil LQ45", a(d["korelasi_bulanan"]["dy10_r_saham"])],
        ["Bulan deposito yang diisi interpolasi", d["deposito_bulan_terisi_interpolasi"]],
    ], ["---", "---"])


def tabel_instrumen(h, par):
    baris = []
    for k, nama in NAMA_INSTRUMEN.items():
        b, pj = h["instrumen"]["bersama"][k], h["instrumen"]["panjang"][k]
        baris.append([nama, p(b["rata"], 2), p(b["simpangan"], 2), p(b["p0_5"], 2), p(b["peluang_negatif"]),
                      p(pj["rata"], 2), p(pj["p0_5"], 2)])
    return md(["Instrumen", "Rata-rata", "Simpangan baku", "Persentil 0,5", "Peluang negatif",
               "Rata-rata (jendela panjang)", "Persentil 0,5 (jendela panjang)"], baris)


def tabel_profil(h, par):
    baris = []
    for k, v in h["profil"].items():
        b, pj = v["imbal_hasil"]["bersama"], v["imbal_hasil"]["panjang"]
        baris.append([v["label"], p(b["rata"], 2), p(b["rata_riil"], 2), p(b["simpangan"], 2), p(b["var_99_5"], 2),
                      p(b["tvar_99_5"], 2), p(b["peluang_negatif"]), p(pj["rata"], 2), p(pj["var_99_5"], 2)])
    return md(["Varian", "Rata-rata", "Rata-rata riil", "Simpangan baku", "VaR 99,5%", "TVaR 99,5%",
               "Peluang negatif", "Rata-rata (panjang)", "VaR 99,5% (panjang)"], baris)


def tabel_validasi(h, par):
    v = h["validasi_bootstrap"]
    def b(nama, kunci, f):
        return [nama, f(v[kunci]["simulasi"]), f(v[kunci]["historis"])]
    return md(["Ukuran 12 bulan", "Simulasi (blok 6 bulan)", "Historis bergulir 2012-2024"], [
        b("Perubahan imbal hasil 10 tahun, simpangan baku (poin)", "dy10_simpangan", a),
        b("Perubahan imbal hasil 10 tahun, persentil 95 (poin)", "dy10_p95", a),
        b("Imbal hasil LQ45, simpangan baku", "saham_simpangan", p),
        b("Imbal hasil LQ45, persentil 5", "saham_p5", p),
        b("Korelasi keduanya", "korelasi_dy10_saham", a),
    ])


def tabel_sensitivitas_investasi(h, par):
    pilih = ["K75", "M50", "A30"]
    dasar_v = {k: h["profil"][k]["imbal_hasil"]["bersama"]["var_99_5"] for k in pilih}
    dasar_p = {k: h["solvabilitas_investasi"]["neraca_sendiri"]["bersama"][k]["peluang_di_bawah_100"] for k in pilih}
    baris = [["Dasar"] + [f"{p(dasar_v[k], 2)} / {p(dasar_p[k], 2)}" for k in pilih]]
    baris.append(["Jendela panjang 2000-2026"] + [
        f"{p(h['profil'][k]['imbal_hasil']['panjang']['var_99_5'], 2)} / {p(h['solvabilitas_investasi']['neraca_sendiri']['panjang'][k]['peluang_di_bawah_100'], 2)}"
        for k in pilih])
    for u, nama in NAMA_UJI_INVESTASI.items():
        baris.append([nama] + [
            f"{p(h['sensitivitas_investasi'][u][k]['var_99_5'], 2)} / {p(h['solvabilitas_investasi']['sensitivitas'][u][k]['peluang_di_bawah_100'], 2)}"
            for k in pilih])
    return md(["Uji"] + [h["profil"][k]["label"] for k in pilih], baris)


def tabel_skenario(h, par):
    kode = list(h["profil"])
    kepala = ["Varian"] + [s["label"] for s in h["skenario"].values()]
    baris = [[h["profil"][k]["label"]] + [f"{p(s['varian'][k])} ({p(s['rasio_akhir_neraca_sendiri'][k], 0)})"
                                           for s in h["skenario"].values()] for k in kode]
    return md(kepala, baris)


def tabel_skenario_guncangan(h, par):
    return md(["Skenario", "Imbal hasil SBN", "Saham", "Selisih kredit", "Dasar"], [
        [s["label"], f"{s['guncangan']['dy_bps']:+d} bps", p(s["guncangan"]["saham"], 0),
         f"{s['guncangan']['selisih_bps']:+d} bps", s["dasar"]] for s in h["skenario"].values()],
        ["---", "---:", "---:", "---:", "---"])


def tabel_ayd(h, par):
    nama = {"korporasi": "obligasi korporasi", "saham": "saham", "reksadana_saham": "reksa dana", "gabungan": "gabungan huruf d-m"}
    baris = []
    for k, v in h["ayd"].items():
        lampau = "; ".join(f"{nama[d['jenis']]} {p(d['porsi'], 0)} di atas batas {p(d['batas'], 0)}" for d in v["dilampaui"]) or "tidak ada"
        sebut = {"deposito": "bank", "korporasi": "emiten obligasi", "saham": "emiten saham",
                 "reksadana_saham": "manajer investasi"}
        pihak = ", ".join(f"{n} {sebut[j]}" for j, n in v["minimum_pihak"].items())
        baris.append([h["profil"][k]["label"], "Ya" if v["patuh"] else "Tidak", p(v["porsi_tidak_diakui"], 0), lampau, pihak])
    return md(["Varian", "Patuh", "Tidak diakui", "Batas yang dilampaui", "Pihak paling sedikit"], baris,
              ["---", "---", "---:", "---", "---"])


def tabel_beban_aset(h, par):
    baris = [[h["profil"][k]["label"], a(v["AAA"]["jumlah"]), a(v["AA"]["jumlah"]), a(v["A"]["jumlah"])]
             for k, v in h["mmbr"]["beban_aset_per_100_investasi"].items()]
    return md(["Varian", "Peringkat AAA", "Peringkat AA", "Peringkat A"], baris)


def tabel_neraca_dasar(h, par):
    nd = par["neraca_dasar"]
    nama = {"capybmp": "Cadangan atas premi yang belum merupakan pendapatan (CAPYBMP)", "cadangan_klaim": "Cadangan klaim",
            "cadangan_bencana": "Cadangan atas risiko bencana", "utang_klaim": "Utang klaim", "utang_lain": "Utang lain",
            "kas_dan_bank": "Kas dan bank", "tagihan_premi": "Tagihan premi penutupan langsung",
            "bua_dikurangi_bpl": "Beban umum dan administrasi dikurangi pendidikan dan pelatihan", "dac": "Biaya akuisisi yang ditangguhkan"}
    kelompok = {"liabilitas": "Liabilitas", "aset_bukan_investasi": "Aset bukan investasi", "beban_dan_dac": "Dasar risiko operasional"}
    baris = []
    for bag, judul in kelompok.items():
        for k, v in nd[bag].items():
            baris.append([judul, nama[k], a(v["nilai"]), v["status"], v["turunan"]])
    return md(["Kelompok", "Butir", "Per 100 premi", "Status", "Turunan"], baris, ["---", "---", "---:", "---", "---"])


def _baris_neraca(h, sumber):
    baris = []
    for k, b in sumber.items():
        baris.append([h["profil"][k]["label"], a(b["investasi"], 1), a(b["investasi_tidak_diakui"], 1), a(b["tingkat_solvabilitas"], 1),
                      *[a(b["modul"][m]) for m in MODUL], a(b["mmbr"]), p(b["rasio"], 0), a(b["ekuitas"], 1)])
    return baris


KEPALA_NERACA = ["Varian", "Investasi", "Tidak diakui", "Tingkat Solvabilitas", "Asuransi", "Kredit", "Pasar",
                 "Likuiditas", "Operasional", "MMBR", "Rasio", "Ekuitas"]


def tabel_mmbr_target(h, par):
    return md(KEPALA_NERACA, _baris_neraca(h, h["mmbr"]["pada_target"]))


def tabel_neraca_sama(h, par):
    return md(KEPALA_NERACA, _baris_neraca(h, h["mmbr"]["neraca_sama"]))


def tabel_rincian_acuan(h, par):
    b = h["mmbr"]["pada_target"][h["mmbr"]["varian_acuan"]]
    n = h["mmbr"]["neraca_dasar"]
    r = b["rincian"]
    dep = b["investasi"] * h["profil"][h["mmbr"]["varian_acuan"]]["bobot"]["deposito"]
    return md(["Modul", "Komponen", "Dasar pengenaan", "Faktor", "Beban"], [
        ["Asuransi", "CAPYBMP", a(n["capybmp"]), "25%", a(r["asuransi"]["capybmp"])],
        ["Asuransi", "Cadangan klaim", a(n["cadangan_klaim"]), "20%", a(r["asuransi"]["cadangan_klaim"])],
        ["Asuransi", "Cadangan bencana", a(n["cadangan_bencana"]), "25%", a(r["asuransi"]["cadangan_bencana"])],
        ["Kredit", "Tagihan premi", a(n["tagihan_premi"]), "8%", a(r["kredit"]["tagihan_premi"])],
        ["Kredit", "Deposito, bank AA", a(dep), "2,1%", a(r["kredit"]["deposito"])],
        ["Kredit", "SBN", a(b["investasi"] - dep), "0%", a(0)],
        ["Pasar", "Tidak ada saham atau reksa dana", a(0), "-", a(0)],
        ["Likuiditas", "Cadangan klaim berjatuh tempo 1-3 dan 3-5 tahun tanpa aset sekelompok",
         a(n["cadangan_klaim"] * 0.30), "4%", a(b["modul"]["likuiditas"])],
        ["Operasional", "BUA dikurangi BPL", a(n["bua_dikurangi_bpl"]), "1%", a(r["operasional"]["beban_umum"])],
        ["Operasional", "Biaya akuisisi ditangguhkan", a(n["dac"]), "50%", a(r["operasional"]["dac"])],
        ["**Jumlah**", "", "", "", f"**{a(b['mmbr'])}**"],
    ], ["---", "---", "---:", "---:", "---:"])


def tabel_sensitivitas_mmbr(h, par):
    pilih = ["K75", "M50", "A30"]
    dasar = h["mmbr"]["pada_target"]
    baris = [["Dasar"] + [f"{a(dasar[k]['mmbr'], 1)} / {a(dasar[k]['ekuitas'], 1)}" for k in pilih]]
    for u, nama in NAMA_UJI_MMBR.items():
        baris.append([nama] + [f"{a(h['mmbr']['sensitivitas'][u][k]['mmbr'], 1)} / {a(h['mmbr']['sensitivitas'][u][k]['ekuitas'], 1)}"
                               for k in pilih])
    return md(["Uji"] + [h["profil"][k]["label"] for k in pilih], baris)


def tabel_target_lain(h, par):
    t = h["mmbr"]["pada_target_lain"]
    kepala = ["Varian", "100%", "120%", "150%", "200%", "331,52%"]
    baris = [[h["profil"][k]["label"], a(t["1.0"][k]["ekuitas"], 1), a(h["mmbr"]["pada_target"][k]["ekuitas"], 1),
              a(t["1.5"][k]["ekuitas"], 1), a(t["2.0"][k]["ekuitas"], 1), a(t["3.3152"][k]["ekuitas"], 1)] for k in h["profil"]]
    return md(kepala, baris)


def tabel_kepatuhan_lain(h, par):
    ya = lambda x: "Ya" if x else "Tidak"
    baris = []
    for k, v in h["kepatuhan_lain"].items():
        s = v["aset_siap_cair"]
        baris.append([h["profil"][k]["label"], ya(v["dana_jaminan"]["dapat_dipenuhi_dari_portofolio"]), ya(v["repo_sbn_tersedia"]),
                      a(v["kecukupan_investasi"]["rasio"]), ya(v["porsi_minimum_sbn"]["terpenuhi"]),
                      a(s["kas_dan_bank"], 1), a(s["deposito"], 1), a(s["sbn_setelah_potongan"], 1), a(s["jumlah"], 1)])
    return md(["Varian", "Dana jaminan dari portofolio", "Repo SBN tersedia", "Kecukupan investasi (kali)",
               "SBN paling rendah 20%*", "Kas dan bank", "Deposito", "SBN setelah potongan 10%", "Aset siap cair"], baris,
              ["---", "---", "---", "---:", "---", "---:", "---:", "---:", "---:"])


def tabel_peluang(h, par):
    s = h["solvabilitas_investasi"]
    baris = []
    for k in h["profil"]:
        b, pj = s["neraca_sendiri"]["bersama"][k], s["neraca_sendiri"]["panjang"][k]
        sm = s["neraca_sama"]["bersama"][k]
        baris.append([h["profil"][k]["label"], p(b["rata"], 0), p(b["p0_5"], 0), p(b["peluang_di_bawah_100"], 2),
                      p(pj["peluang_di_bawah_100"], 2), p(b["peluang_di_bawah_120"], 1), p(sm["rasio_awal"], 0),
                      p(sm["peluang_di_bawah_100"], 2)])
    return md(["Varian", "Rasio akhir rata-rata", "Rasio akhir persentil 0,5", "P(rasio < 100%), jendela bersama",
               "P(rasio < 100%), jendela panjang", "P(rasio < 120%)", "Rasio awal bila neraca sama",
               "P(rasio < 100%) bila neraca sama"], baris)


def tabel_tenor(h, par):
    baris = []
    for t, v in h["tenor_sbn"].items():
        b, pj = v["bersama"], v["panjang"]
        baris.append([f"{t} tahun", p(v["imbal_awal"], 2), p(b["rata"], 2), p(b["simpangan"], 2), p(b["var_99_5"], 2),
                      p(b["peluang_negatif"]), p(b["rasio_akhir"]["peluang_di_bawah_100"], 2),
                      p(pj["rasio_akhir"]["peluang_di_bawah_100"], 2)])
    return md(["Tenor SBN", "Imbal hasil awal", "Rata-rata portofolio", "Simpangan baku", "VaR 99,5%", "Peluang negatif",
               "P(rasio < 100%), jendela bersama", "P(rasio < 100%), jendela panjang"], baris)


def tabel_regulasi_ekonomi(h, par):
    baris = [[h["profil"][k]["label"], a(v["beban_mmbr_aset"]), a(v["var_99_5_bersama"]), a(v["var_99_5_panjang"]),
              a(v["tidak_diakui"], 0)] for k, v in h["regulasi_vs_ekonomi"].items()]
    return md(["Varian", "Beban modal aset MMBR", "VaR 99,5%, 2012-2024", "VaR 99,5%, 2000-2026", "Tidak diakui AYD"], baris)


def tabel_efisiensi(h, par):
    baris = [[h["profil"][k]["label"], a(v["investasi"], 1), a(v["ekuitas"], 1), a(v["hasil_investasi_bersama"]),
              p(v["hasil_per_ekuitas_bersama"]), p(v["hasil_per_ekuitas_panjang"])] for k, v in h["efisiensi_modal"].items()]
    return md(["Varian", "Investasi", "Ekuitas", "Hasil investasi rata-rata", "Hasil per ekuitas, jendela bersama",
               "Hasil per ekuitas, jendela panjang"], baris)


def tabel_industri(h, par):
    r = h["rekonstruksi_industri"]
    baris = []
    for k, nama in (("faktor_rendah", "Faktor terendah"), ("faktor_tinggi", "Faktor tertinggi")):
        s = r["skenario"][k]
        baris.append([nama, a(s["mmbr"] / 1e6, 1), p(s["rasio"], 0), *[p(s["porsi"][m], 0) for m in MODUL]])
    baris.append(["Angka resmi OJK (asuransi umum dan reasuransi)", "-", p(r["rasio_resmi_ojk"]), "-", "-", "-", "-", "-"])
    return md(["Set asumsi", "MMBR (Rp triliun)", "Rasio solvabilitas", "Asuransi", "Kredit", "Pasar", "Likuiditas", "Operasional"], baris)


def tabel_asumsi(h, par):
    """Daftar asumsi: seluruh butir berstatus asumsi pada berkas parameter."""
    ps, nd = par["pasar"], par["neraca_dasar"]
    ins = ps["instrumen"]
    return md(["Asumsi", "Nilai dasar", "Uji banding", "Catatan"], [
        ["Tenor SBN", f"{ins['sbn']['tenor_dasar']} tahun", "2 dan 10 tahun", "Brief tidak menyebut tenor"],
        ["Obligasi korporasi", f"{ins['korporasi']['peringkat_dasar']}, {ins['korporasi']['tenor']} tahun, {ins['korporasi']['jumlah_emiten']} emiten", "AAA", "Wajib investment grade (Pasal 6 ayat 2)"],
        ["Peluang gagal bayar setahun", "AAA 0,1%; AA 0,3%", "Tiga kali lipat", "Belum bersumber; studi Pefindo tidak dapat diakses"],
        ["Tingkat kerugian saat gagal bayar", p(ins["korporasi"]["tingkat_kerugian_saat_gagal"], 0), "-", "Belum bersumber"],
        ["Selisih imbal hasil korporasi", "Tetap", "Melebar 2 bps tiap 1% penurunan saham", "Riwayat selisih tidak tersedia terbuka"],
        ["Imbal dividen saham", p(ins["saham"]["imbal_dividen"], 0), "0%", "Indeks LQ45 adalah indeks harga"],
        ["Reksa dana saham", "Mengikuti IHSG; dividen habis untuk biaya", "-", ""],
        ["Deposito", "1 bulan, digulirkan", "-", "Agar siap cair"],
        ["Klasifikasi obligasi", "Nilai wajar", "Dimiliki hingga jatuh tempo", "Menentukan apakah perubahan harga masuk Tingkat Solvabilitas"],
        ["Panjang blok bootstrap", f"{ps['bootstrap']['panjang_blok_bulan']} bulan", "3 dan 12 bulan", ""],
        ["Tagihan premi", a(nd["aset_bukan_investasi"]["tagihan_premi"]["nilai"]) + " per 100 premi", "-", "Dua bulan premi, batas umur AYD"],
        ["Pola jatuh tempo cadangan klaim", "70% / 25% / 5% (<1, 1-3, 3-5 tahun)", "Seluruhnya <1 tahun", "Menentukan risiko likuiditas"],
        ["Peringkat bank deposito", "AA", "AAA dan A", ""],
        ["Potongan repo SBN", p(ps["likuiditas"]["potongan_repo_sbn"], 0), "-", "Hanya untuk ukuran aset siap cair"],
    ], ["---", "---", "---", "---"])


TABEL = {k[len("tabel_"):]: v for k, v in globals().items() if k.startswith("tabel_")}


# ---------- blok YAML ----------
def _bulat(o, d=4):
    if isinstance(o, dict):
        return {k: _bulat(v, d) for k, v in o.items()}
    if isinstance(o, list):
        return [_bulat(v, d) for v in o]
    return round(o, d) if isinstance(o, float) else o


def yaml_varian(h, par):
    """Angka kunci tiap varian dalam satu blok, menjorok dua spasi di bawah kunci `varian`."""
    sol = h["solvabilitas_investasi"]
    out = {}
    for k, v in h["profil"].items():
        t = h["mmbr"]["pada_target"][k]
        ih = v["imbal_hasil"]
        out[k] = {
            "profil": v["profil"], "label": v["label"], "bobot": v["bobot"],
            "patuh_ayd": h["ayd"][k]["patuh"],
            "porsi_tidak_diakui": h["ayd"][k]["porsi_tidak_diakui"],
            "beban_aset_per_100_investasi": {r: h["mmbr"]["beban_aset_per_100_investasi"][k][r]["jumlah"] for r in ("AAA", "AA")},
            "imbal_hasil": {j: {u: ih[j][u] for u in ("rata", "rata_riil", "simpangan", "var_99_5", "tvar_99_5", "peluang_negatif")}
                            for j in ("bersama", "panjang")},
            "pada_target_120": {"investasi": t["investasi"], "investasi_tidak_diakui": t["investasi_tidak_diakui"],
                                "tingkat_solvabilitas": t["tingkat_solvabilitas"], "ekuitas": t["ekuitas"],
                                "mmbr": t["mmbr"], "modul": t["modul"], "porsi_asuransi": t["porsi_modul"]["asuransi"]},
            "rasio_bila_neraca_sama": h["mmbr"]["neraca_sama"][k]["rasio"],
            "peluang_rasio_di_bawah_100_investasi_saja": {j: sol["neraca_sendiri"][j][k]["peluang_di_bawah_100"]
                                                          for j in ("bersama", "panjang")},
            "aset_siap_cair_per_100_premi": h["kepatuhan_lain"][k]["aset_siap_cair"]["jumlah"],
            "dana_jaminan_dari_portofolio": h["kepatuhan_lain"][k]["dana_jaminan"]["dapat_dipenuhi_dari_portofolio"],
            "imbal_hasil_skenario": {s: sk["varian"][k] for s, sk in h["skenario"].items()},
        }
    teks = yaml.safe_dump(_bulat(out), sort_keys=False, allow_unicode=True, default_flow_style=None, width=160)
    return "\n".join("  " + baris for baris in teks.rstrip().split("\n"))


BLOK_YAML = {"varian": yaml_varian}


# ---------- pengisi templat ----------
def _ambil(h, jalur):
    x = h
    for bagian in jalur.split("."):
        x = x[int(bagian)] if isinstance(x, list) else x[bagian]
    return x


def _format(x, f):
    if f == "t":
        return str(x)
    jenis, d = f[0], int(f[1:])
    if jenis == "p":
        return persen(x, d)
    if jenis == "q":
        return angka(100 * x, d) + " poin persentase"
    if jenis == "a":
        return angka(x, d)
    if jenis == "n":
        return f"{x:.{d}f}"
    raise ValueError(f"format tidak dikenal: {f}")


def isi(templat, h, par):
    def ganti(m):
        isi_ = m.group(1).strip()
        if isi_.startswith("tabel:"):
            return TABEL[isi_[len("tabel:"):]](h, par)
        if isi_.startswith("yaml:"):
            return BLOK_YAML[isi_[len("yaml:"):]](h, par)
        jalur, _, f = isi_.partition("|")
        return _format(_ambil(h, jalur.strip()), f.strip() or "t")
    return re.sub(r"\{\{(.+?)\}\}", ganti, templat)


def main():
    h = json.loads(BERKAS_HASIL.read_text(encoding="utf-8"))
    par = muat_parameter()
    for templat, keluaran in (("templat_laporan.md", "LAPORAN.md"), ("templat_konteks_ai.yaml", "KONTEKS_AI.yaml")):
        teks = isi((DIR_KODE / templat).read_text(encoding="utf-8"), h, par)
        sisa = re.findall(r"\{\{.+?\}\}", teks)
        assert not sisa, f"penanda belum terisi pada {templat}: {sisa[:3]}"
        (DIR_ANALISIS / keluaran).write_text(teks, encoding="utf-8")
        print("ditulis:", keluaran)


if __name__ == "__main__":
    main()
