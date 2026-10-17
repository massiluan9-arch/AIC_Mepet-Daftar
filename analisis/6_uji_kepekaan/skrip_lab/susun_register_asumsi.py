"""T10: menyusun register_asumsi_mentah.csv dari berkas parameter (YAML) dan konstanta kode (R, Python).

Baris YAML dibuat otomatis: tiap nilai daun menjadi satu baris, dengan nomor baris dari pengurai YAML dan
status/sumber dari simpul induknya. Konstanta R dan Python didaftar tangan; nomor barisnya dicari ulang di berkas
sumber supaya tidak salah ketik. Kolom uji kepekaan diisi dari keluaran yang benar-benar dijalankan di lab.

Pemakaian: python susun_register_asumsi.py <folder AIC_CASE Rev. 1> <berkas keluaran csv>
"""
import csv
import re
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")
AKAR = Path(sys.argv[1])
KELUAR = Path(sys.argv[2])
META = {"status", "sumber", "dasar", "catatan", "turunan", "isi", "label", "rumus", "alasan", "catatan_urutan", "catatan_deposito", "rentang_brief",
        "aturan", "satuan", "judul", "status_tenor", "status_dividen", "sensitivitas", "pembanding_industri", "dipakai_model", "berlaku_untuk_kasus",
        "aturan_efek_nilai_pasar", "aturan_dimiliki_hingga_jatuh_tempo", "definisi_tingkat_solvabilitas", "dasar_modul", "berkas"}
BARIS = []

# Hasil uji kepekaan yang dijalankan (Rev. 1 = rev1_ulang, K75; Rev. 2 = A_K70). Kunci = pola jalur parameter.
UJI = [
    (r"bencana\.eksposur_per_premi", "ya", "E 122/188: P(R<100%) polis standar 120% = 0,63%/1,02% (dasar 0,71%); target solusi A_K70 1,45/2,55 (dasar 1,70); modal saja 2,80/4,65"),
    (r"bencana\.tarif_gempa_per_mil", "tidak di Rev. 1; diuji auditor", "premi gempa disetarakan 22,83 per 100 premi: modal saja menjadi pilihan pengoptimal (A_K70: S0 18,89 lawan S21 18,35)"),
    (r"bencana\.porsi_klaim_belum_dibayar", "ya", "0,5: P polis standar 0,79%; target C1 solusi A_K70 1,60 (dasar 1,40)"),
    (r"skala_premi_syarat\.batas10", "tidak di Rev. 1; diuji auditor", "0,55 (Varian B55): pilihan bergeser ke batas 15% zona inti pada 185%; lihat perbandingan varian"),
    (r"skala_premi_syarat\.", "tidak di Rev. 1; diuji auditor (B55)", "skala menurut pembayaran maksimum efektif mengubah premi dilepas dan urutan nilai bersih"),
    (r"underwriting\.rasio_klaim_non_bencana\.rata", "ya", "29,5%: P polis standar 0,48%; target solusi 1,20; NPV berbalik (Rev. 1: -15,2)"),
    (r"underwriting\.rasio_klaim_non_bencana\.simpangan", "ya", "x2: P polis standar 1,37%; solusi A_K70 pada 170% 0,73% (target C1 2,00)"),
    (r"underwriting\.komisi", "ya", "15%: P polis standar 0,92%; target solusi A_K70 2,05 (tiga kendala)"),
    (r"underwriting\.beban_usaha\.simpangan", "tidak", "menentukan P(rugi operasional > 0) = 49,8% dan P(> beban modal) = 32,4% secara mekanis"),
    (r"underwriting\.beban_usaha\.nilai", "tidak", ""),
    (r"underwriting\.pajak", "tidak", ""),
    (r"likuiditas\.potongan_harga", "ya (x2)", "x2: P polis standar tetap 0,71%; target minimum 1,95 (dasar 1,90)"),
    (r"sensitivitas\.korelasi_bencana_pasar", "ya", "0,25: P polis standar 0,78%; solusi A_K70 0,44% (target C1 1,50)"),
    (r"sensitivitas\.panjang_blok_bulan|bootstrap\.panjang_blok", "ya", "blok 3 dan 12 bulan: P polis standar 0,72% (dasar 0,71%)"),
    (r"sensitivitas\.tenor_sbn|instrumen\.sbn\.tenor", "ya", "tenor 2/10 tahun: P polis standar 0,71%/0,72%; target solusi C1 1,45 pada tenor 10"),
    (r"bootstrap\.jendela", "ya", "jendela 2000-2026: P polis standar 0,72%; solusi 0,42%"),
    (r"meta\.ambang_peluang", "tidak di Rev. 1; diuji auditor (aturan batas atas selang)", "batas atas selang 95% <= 0,5% setara ambang titik 0,456%: target solusi A_K70 1,70 -> 1,90"),
    (r"meta\.jumlah_tahun|bootstrap\.jumlah_tahun", "sebagian (dua paruh)", "galat baku P sekitar 0,02 poin; C2 pada target terpilih 0,499% dengan selang [0,456%; 0,545%]"),
    (r"meta\.profil_acuan", "tidak di Rev. 1; diuji auditor", "K75 -> K70: P dan target sama; ekuitas +0,19; cakupan kas dan deposito 89% -> 103%"),
    (r"biaya_modal", "ya (10% dan 16%)", "10%: modal saja lebih murah; 16%: solusi lebih murah. Titik impas A_K70 13,45% (diperluas), 14,94% (perusahaan)"),
    (r"biaya_implementasi", "dinyatakan (pengali 2) tetapi tidak dilaporkan di Rev. 1; diuji auditor", "x2: NPV Rev. 1 +4,0 -> -11,9; A_K70 -4,9 -> -20,8"),
    (r"horizon_tahun", "ya (3, 5, 7, 10 di Excel)", "Rev. 1: NPV 0,7; 4,0; 6,6; 9,4"),
    (r"skala_rupiah", "tidak", "hanya mengubah satuan; biaya pelaksanaan tidak ikut diskalakan, jadi NPV per premi bergantung skala"),
    (r"kendala\.target_paling_rendah", "tidak", ""),
    (r"skenario_uji", "sebagian", "eta 0 dan +1 dilaporkan; hanya eta 0 yang menjadi kendala C3"),
    (r"instrumen\.korporasi\.peluang_gagal", "ya di 05 (tiga kali)", "tidak berpengaruh pada profil Konservatif (tanpa obligasi korporasi)"),
    (r"selisih_kredit", "ya di 05", "tidak berpengaruh pada profil Konservatif"),
    (r"likuiditas\.potongan_repo_sbn", "tidak", "dipakai di 05 (aset siap cair 94); mesin 06 memakai potongan SBN 0,5% dan nominal penuh (101)"),
    (r"liabilitas\.capybmp", "ya di 05 (50)", ""),
    (r"liabilitas\.cadangan_bencana", "ya di 05 (5)", ""),
    (r"faktor_risiko|batas_ayd|solvabilitas|klaster_peringkat", "tidak (regulasi)", ""),
]


def hasil_uji(jalur):
    for pola, ada, hasil in UJI:
        if re.search(pola, jalur):
            return ada, hasil
    return "tidak", ""


def lemah(status, sumber, catatan):
    s = (status or "").lower()
    t = f"{sumber} {catatan}".lower()
    if s in ("asumsi", "tafsir", "belum_terkonfirmasi"):
        return "ya: " + ("tanpa sumber" if not sumber else "asumsi; sumber perlu dikutip")
    if "belum bersumber" in t or "tidak dapat diakses" in t or "perlu dicek" in t:
        return "ya: sumber dinyatakan belum ada"
    if not s and not sumber:
        return "ya: status dan sumber tidak ditulis"
    return ""


def tambah(parameter, nilai, satuan, status, sumber, lokasi, ada_uji=None, hasil=None, bendera=None, catatan=""):
    if ada_uji is None:
        ada_uji, hasil = hasil_uji(parameter)
    BARIS.append({"parameter": parameter, "nilai": nilai, "satuan": satuan, "status_di_kode": status or "", "sumber_tertulis": sumber or "",
                  "lokasi": lokasi, "uji_kepekaan_ada": ada_uji, "hasil_uji_kepekaan": hasil or "",
                  "bendera_sumber_lemah": lemah(status, sumber, catatan) if bendera is None else bendera, "catatan_di_kode": catatan or ""})


# ---------------------------------------------------------------- YAML otomatis
def bangun(simpul):
    if isinstance(simpul, yaml.MappingNode):
        return {k.value: (bangun(v), k.start_mark.line + 1) for k, v in simpul.value}
    if isinstance(simpul, yaml.SequenceNode):
        return [bangun(v) for v in simpul.value]
    return yaml.safe_load(yaml.serialize(simpul)) if False else simpul.value if simpul.tag.endswith("str") else yaml.safe_load(simpul.value)


def polos(x):
    """Membuang nomor baris dari hasil bangun()."""
    if isinstance(x, dict):
        return {k: polos(v[0]) for k, v in x.items()}
    if isinstance(x, list):
        return [polos(v) for v in x]
    return x


def daun_sederhana(x):
    if isinstance(x, dict):
        return all(not isinstance(v[0], (dict, list)) for v in x.values())
    if isinstance(x, list):
        return all(not isinstance(v, (dict, list)) for v in x)
    return True


def jelajah(pohon, jalur, berkas, warisan):
    konteks = dict(warisan)
    for k in ("status", "sumber", "dasar", "catatan", "turunan", "satuan"):
        if k in pohon and not isinstance(pohon[k][0], (dict, list)):
            konteks[k] = str(pohon[k][0])
    for kunci, (isi, baris) in pohon.items():
        if kunci in META:
            continue
        j = f"{jalur}.{kunci}" if jalur else kunci
        lokasi = f"{berkas}:{baris}"
        sumber = konteks.get("sumber") or konteks.get("dasar") or konteks.get("turunan") or ""
        if isinstance(isi, dict) and "nilai" in isi and not isinstance(isi["nilai"][0], dict):
            sub = {k: str(v[0]) for k, v in isi.items() if not isinstance(v[0], (dict, list))}
            nilai = polos(isi["nilai"][0])
            tambahan = {k: polos(v[0]) for k, v in isi.items() if k in ("rentang", "uji", "simpangan", "rata", "uji_rata", "uji_pengali_simpangan")}
            tambah(j, nilai if not tambahan else f"{nilai} {tambahan}", sub.get("satuan", konteks.get("satuan", "")), sub.get("status", konteks.get("status")),
                   sub.get("sumber") or sub.get("dasar") or sub.get("turunan") or sumber, lokasi, catatan=sub.get("catatan", ""))
            sisa = {k: v for k, v in isi.items() if isinstance(v[0], (dict, list)) and k not in META and k not in ("rentang",)}
            if sisa:
                jelajah(sisa, j, berkas, konteks)
        elif isinstance(isi, dict):
            if daun_sederhana(isi) and not any(k in isi for k in ("nilai",)) and len(isi) <= 8 and all(k not in META for k in isi) and jalur.count(".") >= 1:
                tambah(j, polos(isi), konteks.get("satuan", ""), konteks.get("status"), sumber, lokasi, catatan=konteks.get("catatan", ""))
            else:
                sub = {k: str(v[0]) for k, v in isi.items() if k in ("status", "sumber", "dasar", "catatan", "turunan") and not isinstance(v[0], (dict, list))}
                skalar = {k: v for k, v in isi.items() if k not in META and not isinstance(v[0], (dict, list))}
                jelajah(isi, j, berkas, konteks)
                del sub, skalar
        else:
            tambah(j, polos(isi), konteks.get("satuan", ""), konteks.get("status"), sumber, lokasi, catatan=konteks.get("catatan", ""))


BERKAS_YAML = [("analisis/3_investasi_mmbr/parameter/regulasi.yaml", "regulasi"), ("analisis/3_investasi_mmbr/parameter/profil.yaml", "data (brief kasus)"),
               ("analisis/3_investasi_mmbr/parameter/neraca_dasar.yaml", None), ("analisis/3_investasi_mmbr/parameter/pasar.yaml", None),
               ("analisis/4_simulasi_terpadu/parameter_terpadu.yaml", None), ("analisis/5_solusi_motera/parameter_solusi.yaml", None)]
for rel, status_bawaan in BERKAS_YAML:
    teks = (AKAR / rel).read_text(encoding="utf-8")
    pohon = bangun(yaml.compose(teks))
    n0 = len(BARIS)
    jelajah(pohon, Path(rel).stem, rel, {"status": status_bawaan} if status_bawaan else {})
    print(f"{rel}: {len(BARIS) - n0} baris")


# ---------------------------------------------------------------- konstanta kode
def baris_kode(rel, pola):
    for i, b in enumerate((AKAR / rel).read_text(encoding="utf-8").splitlines(), 1):
        if re.search(pola, b):
            return f"{rel}:{i}"
    raise SystemExit(f"pola tidak ditemukan: {rel} :: {pola}")


R = "analisis/2_model_bencana/R/"
KODE = [
    # parameter, nilai, satuan, status, sumber tertulis, berkas, pola, uji ada, hasil uji, bendera, catatan
    ("R04.NU (presisi Beta rasio kerusakan per risiko)", 3, "-", "asumsi", "komentar kode: 'presisi Beta rasio kerusakan per risiko (asumsi)'", R + "04_simulasi_kerugian.R", r"^NU <- 3",
     "tidak di Rev. 1; diuji auditor (NU 1,5 dan 6)", "NU 1,5: S21 terpilih pada 160% (nilai bersih 19,47; modal saja 18,22 pada 365%). NU 6: polis standar terpilih pada 275% (19,89; S21 18,80 pada 190%). Pilihan strategi berbalik", "ya: asumsi tanpa sumber; menentukan efek risiko sendiri dan batas", ""),
    ("R03.NU (salinan kedua konstanta yang sama)", 3, "-", "asumsi", "komentar kode", R + "03_kerentanan.R", r"^NU <- 3", "tidak", "", "ya: didefinisikan dua kali (03 dan 04)", ""),
    ("R04.RS (risiko sendiri polis standar)", 0.025, "fraksi nilai pertanggungan", "regulasi", "SEOJK 6/2017 Lampiran III (komentar di 03_kerentanan.R)", R + "04_simulasi_kerugian.R", r"^RS <- 0.025", "ya (S1 5%, S2 10%)", "risiko sendiri 10%: P 0,46% pada 120%, tetapi dikecualikan dari calon", "", ""),
    ("R04.GESER_EPISENTER", 0.3, "derajat (simpangan baku)", "asumsi", "komentar kode", R + "04_simulasi_kerugian.R", r"^GESER_EPISENTER", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R04.N_TAHUN", 100000, "tahun simulasi", "pilihan komputasi", "", R + "04_simulasi_kerugian.R", r"^N_TAHUN", "sebagian", "galat baku VaR 99,5% campuran 0,015% nilai pertanggungan", "", ""),
    ("R04.BENIH", 20261012, "-", "pilihan komputasi", "", R + "04_simulasi_kerugian.R", r"^BENIH", "tidak (satu benih)", "kestabilan diperiksa lewat paruh dan kelompok, bukan benih lain", "", ""),
    ("R01.M_MIN", 5.5, "magnitudo", "asumsi", "komentar: batas bawah simulasi", R + "01_katalog_frekuensi_magnitudo.R", r"^M_MIN", "tidak", "", "ya: pilihan penulis", ""),
    ("R01.M_MAKS", 9.2, "magnitudo", "asumsi", "komentar: sedikit di atas magnitudo terbesar katalog (Sumatra 2004, Mw 9,1)", R + "01_katalog_frekuensi_magnitudo.R", r"^M_MAKS", "tidak", "", "ya: pilihan penulis; ekor sangat peka", ""),
    ("R01.TAHUN katalog", "1976:2025", "tahun", "data", "USGS", R + "01_katalog_frekuensi_magnitudo.R", r"^TAHUN <-", "tidak", "", "", ""),
    ("R01.frekuensi (binomial negatif: rata, ukuran)", "59,06; 11,85", "kejadian M>=5,5 per tahun", "estimasi", "kemungkinan maksimum atas katalog USGS", R + "01_katalog_frekuensi_magnitudo.R", r"h55 <- uji_frekuensi", "sebagian", "Poisson ditolak (AIC 599 lawan 436)", "", "nilai di keluaran/01_parameter.json"),
    ("R01.nilai_b", 1.0461, "-", "estimasi", "Aki (1965), kemungkinan maksimum", R + "01_katalog_frekuensi_magnitudo.R", r"^b_pakai", "tidak", "galat baku 0,019", "", ""),
    ("R01.deklasterisasi Gardner-Knopoff: radius", "10^(0,1238 M + 0,983)", "km", "literatur", "Gardner & Knopoff (1974)", R + "01_katalog_frekuensi_magnitudo.R", r"0\.1238", "ya (dengan/tanpa)", "frekuensi simulasi memakai katalog penuh, bukan terdeklaster", "", ""),
    ("R04.lokasi: kolam episenter untuk M >= 7,5", "episenter historis M >= 7,0", "-", "asumsi", "alur_metode: 'kelas magnitudo yang sama atau lebih besar'", R + "04_simulasi_kerugian.R", r"kelas_lokasi <- list", "tidak", "", "ya: kolam M>=7,0 dipakai untuk kejadian M>=7,5, tidak persis seperti uraian metode", ""),
    ("R04.lokasi: batas kelas magnitudo", "7,5 dan 6,5", "magnitudo", "asumsi", "", R + "04_simulasi_kerugian.R", r"b <- m >= 7\.5", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R04.intensitas: porsi varians antar-gempa", 0.5, "fraksi", "asumsi", "alur_metode: 'separuh varians antar-gempa'", R + "04_simulasi_kerugian.R", r"sqrt\(0\.5\) \* eta", "tidak", "", "ya: asumsi; 02 menaksir tau dan phi tetapi tidak dipakai di sini", ""),
    ("R04.intensitas: pemotongan residu", "+-2", "simpangan baku", "asumsi", "", R + "04_simulasi_kerugian.R", r"eta <- pmax\(pmin\(rnorm", "tidak", "", "ya: asumsi tanpa sumber; memotong ekor guncangan", ""),
    ("R04.intensitas: batas atas MMI", 10, "MMI", "asumsi", "", R + "04_simulasi_kerugian.R", r"pmin\(mmi_allen_rrup", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R04.simpangan intensitas", "0,82 + 0,37 / (1 + (r/22,9)^2)", "MMI", "literatur", "Allen dkk. (2012)", R + "04_simulasi_kerugian.R", r"^simpangan <- function", "tidak", "", "", ""),
    ("R04.ambang kejadian merugikan", "MMI maksimum titik >= 5", "MMI", "asumsi", "", R + "04_simulasi_kerugian.R", r"kena <- which", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R00.persamaan intensitas Allen dkk. (jarak ruptur)", "3,950 + 0,913 M - 1,107 ln sqrt(r^2 + (1 + 0,813 e^(M-5))^2)", "MMI", "literatur", "Allen, Wald & Worden (2012)", R + "00_fungsi.R", r"^mmi_allen_rrup", "sebagian", "bias antar-gempa -0,23 MMI (p 0,17) pada 436 observasi", "", ""),
    ("R00.panjang ruptur", "10^(-2,44 + 0,59 M)", "km", "literatur", "Wells & Coppersmith (1994)", R + "00_fungsi.R", r"^panjang_ruptur_km", "tidak", "", "", ""),
    ("R00.kurva Aulady & Fujimi: mmi50, k, bobot tipologi", "CM 8,891/2,736/0,539; UM 8,774/1,931/0,189; RCMR 8,393/4,025/0,150; TF 9,057/1,844/0,087; RCLR 8,976/2,411/0,036", "-", "literatur", "Aulady & Fujimi (2019); data/katastrofe/gempa/kerentanan_bangunan V01, V03", R + "00_fungsi.R", r"^AULADY <- data.table", "ya (kurva lain)", "kurva Aulady saja: P polis standar 0,84%; C2 mengikat pada solusi", "ya: kurva hunian Bantul dipakai untuk portofolio industri dan komersial", ""),
    ("R00.kurva Aulady: ambang nol", "MMI < 5,5 -> 0", "MMI", "asumsi", "", R + "00_fungsi.R", r"ifelse\(mmi < 5\.5", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R00.kurva PAGER Indonesia: theta, beta", "10,211; 0,103", "-", "literatur", "Jaiswal & Wald (2013)", R + "00_fungsi.R", r"^kurva_pager", "ya (kurva lain)", "kurva PAGER saja: P polis standar 0,08%", "", ""),
    ("R03.kurva klaim MAIPARK: a, b (logit pecahan)", "-11,744; 0,946", "-", "estimasi", "MAIPARK Tabel 4.1, 13 kejadian gempa", R + "03_kerentanan.R", r"^m_semua <- pas", "ya (tanpa Aceh dan Donggala; buang satu)", "tanpa dua kejadian bertsunami: a -12,57, b 1,005", "ya: n = 13; rasio terhadap eksposur 'terdampak' yang direvisi besar di edisi Juni 2025", ""),
    ("R03.kurva klaim: ambang nol", "MMI < 5 -> 0", "MMI", "asumsi", "", R + "03_kerentanan.R", r"^kurva_klaim <- function", "tidak", "", "ya: asumsi tanpa sumber", ""),
    ("R04.strategi: ZONA_INTI", "Papua, Jawa Barat, Jakarta, Sumatera Utara, Banten", "-", "turunan", "provinsi dengan porsi kerugian tahun ekor > 3% pada kurva Aulady (04_kontribusi_provinsi.csv)", R + "04_simulasi_kerugian.R", r"^ZONA_INTI", "tidak", "bobot Papua 12,5% turun menjadi 6,8% pada MAIPARK edisi Juni 2025 (uji F03)", "ya: ambang 3% pilihan penulis; bergantung versi data", ""),
    ("R04.strategi: PORSI_BESAR (risiko > Rp50 miliar)", 0.82, "fraksi eksposur", "data", "MAIPARK profil risiko, baris 1-19", R + "04_simulasi_kerugian.R", r"^PORSI_BESAR", "tidak", "edisi Juni 2025: 85,6% eksposur pada 4,6% risiko", "ya: baris 19 dan 20 tabel sumber edisi Desember 2024 tidak konsisten", ""),
    ("R04.skenario C3: megathrust Jawa bagian barat", "M 8,7; -7,5 LS; 106,0 BT; kedalaman 30 km; arah 0,5; eta 0", "-", "asumsi", "BMKG (2024) lewat pemberitaan; PuSGeN 2017", R + "04_simulasi_kerugian.R", r"nama = c\(\"Megathrust Jawa bagian barat", "sebagian (eta +1)", "eta +1: rasio solusi A_K70 -482%", "ya: lokasi, kedalaman, dan arah ruptur pilihan penulis", ""),
    ("R04.uji balik: parameter lima kejadian", "Lombok 6,9; Palu 7,5; Majene 6,2; Cianjur 5,6; Bawean 6,4", "-", "data", "USGS/BMKG (tidak dikutip di kode)", R + "04_simulasi_kerugian.R", r"nama = c\(\"Lombok 2018\"", "tidak", "model 1%-14% klaim teramati pada guncangan median", "ya: sumber parameter kejadian tidak ditulis", ""),
    ("R05.pertumbuhan eksposur hitung mundur 2004-2019", 0.1451, "per tahun", "data", "komentar: kenaikan rata-rata yang dilaporkan MAIPARK", R + "05_konsistensi_dan_ekor.R", r"^amati21 <- pengalaman", "ya (10% dan 20%)", "bobot Aulady 0,88/0,64; lihat t5_bobot.csv", "ya: 49% penyebut berasal dari hitung mundur", ""),
    ("R05.pembilang pengalaman 21 tahun", "13 kejadian gempa dari daftar klaim terbesar (Rp4.121,9 miliar)", "Rp miliar", "data", "MAIPARK Tabel 4.1", R + "05_konsistensi_dan_ekor.R", r"^klaim_gempa <-", "tidak di Rev. 1; diuji auditor", "x1,25/x1,5/x2: bobot Aulady 0,50/0,29/0,16", "ya: bukan seluruh klaim industri (F02)", ""),
    ("R05.bobot kurva campuran", "Aulady 0,784; klaim 0,178; PAGER 0,038", "-", "estimasi", "kepadatan rata-rata 21 tahun hasil bootstrap pada nilai teramati; prior sama rata", R + "05_konsistensi_dan_ekor.R", r"kons\[, bobot :=", "sebagian (pertumbuhan)", "lihat t5_bobot.csv dan t5_c1.csv", "ya: sangat peka pada pembilang; kurva klaim dipaskan pada data yang sama", ""),
    ("R05.bootstrap bobot: B, panjang, benih", "20000; 21 dan 5 tahun; 505", "-", "pilihan komputasi", "", R + "05_konsistensi_dan_ekor.R", r"^B <- 20000", "tidak di Rev. 1; diuji auditor", "20 benih lain: simpangan baku bobot Aulady 0,010", "", ""),
    ("R05.benih cabang kurva campuran", 506, "-", "pilihan komputasi", "", R + "05_konsistensi_dan_ekor.R", r"^set.seed\(506\)", "tidak di Rev. 1; diuji auditor", "penaksir berstrata: C1 solusi A_K70 0,399% lawan 0,418% (cabang acak)", "", ""),
    ("R05.ambang GPD", "kuantil 95%", "-", "asumsi", "", R + "05_konsistensi_dan_ekor.R", r"^ambang <- quantile", "tidak di Rev. 1; diuji auditor", "bentuk 0,80-0,91 pada ambang 90%-99%", "ya: nilai p KS tanpa koreksi (0,81; terkoreksi 0,40)", ""),
    ("D02.titik portofolio: 37 titik, porsi dalam provinsi", "Jawa Barat 60/40; Banten 60/40; Sulawesi Tengah 70/30", "-", "asumsi", "02_susun_portofolio.py: 'porsi ... asumsi'", "analisis/1_olah_data/02_susun_portofolio.py", r"^TITIK = \[", "tidak", "", "ya: satu atau dua titik per provinsi; pilihan titik menentukan jarak ke sumber gempa", ""),
    ("D02.bobot provinsi", "rata-rata eksposur UY 2020-2024", "-", "data", "MAIPARK Tabel 1.1 edisi 31 Desember 2024", "analisis/1_olah_data/02_susun_portofolio.py", r"bobot = ek.set_index", "tidak di Rev. 1; diuji auditor (F03)", "edisi Juni 2025: Papua 12,5% -> 6,8%; lihat hasil F03_A_K70", "ya: edisi lebih baru merevisi Papua", ""),
    ("mesin.rugi kredit", "hanya gagal bayar obligasi korporasi", "-", "pilihan model", "komentar Tabel 5 paper", "analisis/4_simulasi_terpadu/kode/mesin.py", r"rugi_kredit = posisi.get", "tidak", "", "ya: gagal bayar bank dan tagihan premi tidak disimulasikan", ""),
    ("mesin.rugi operasional", "max(simpangan beban usaha, 0)", "-", "pilihan model", "komentar Tabel 5 paper", "analisis/4_simulasi_terpadu/kode/mesin.py", r"\"operasional\": np.maximum\(lebih_beban", "tidak", "", "ya: proksi; P(rugi > 0) = 50% karena derau simetris", ""),
    ("mesin.sebaran klaim non-bencana", "lognormal", "-", "asumsi", "parameter_terpadu.yaml: sebaran: lognormal", "analisis/4_simulasi_terpadu/kode/mesin.py", r"klaim_nb = 100.0 \* rata", "tidak", "", "ya: bentuk sebaran tidak diuji", ""),
    ("mesin.kebebasan bencana, pasar, klaim, beban", "saling bebas", "-", "asumsi", "alur_metode bagian 7", "analisis/4_simulasi_terpadu/kode/mesin.py", r"self.z_klaim = rng.standard_normal", "ya (korelasi bencana-pasar 0,25)", "P polis standar 0,78%", "", ""),
    ("mesin.pajak atas rugi", "tidak ada aset pajak tangguhan", "-", "asumsi", "parameter_terpadu.yaml pajak.sumber", "analisis/4_simulasi_terpadu/kode/mesin.py", r"pajak = uw\[\"pajak\"\]", "tidak", "", "", ""),
    ("rancang.fungsi tujuan", "laba bersih - biaya modal x ekuitas - defisit harapan", "per 100 premi", "pilihan model", "Butsic (1994); Myers & Read (2001) di komentar", "analisis/5_solusi_motera/kode/rancang_solusi.py", r"out\[\"nilai_bersih\"\] =", "tidak di Rev. 1; diuji auditor", "tanpa suku defisit atau dengan biaya pelaksanaan: modal saja terpilih (A_K70)", "ya: biaya pelaksanaan tidak masuk fungsi tujuan; suku defisit tumpang tindih dengan laba", ""),
    ("rancang.calon dikecualikan", "S1, S2, S7, S8 (risiko sendiri > 2,5%)", "-", "pilihan model", "parameter_solusi.yaml dikecualikan", "analisis/5_solusi_motera/kode/rancang_solusi.py", r"layak = \{st: v", "tidak", "S2 (risiko sendiri 10%) bernilai bersih tertinggi bila tidak dikecualikan (22,4)", "ya: alasan 'sulit dipasarkan' tidak diukur", ""),
]
for (par, nilai, satuan, status, sumber, rel, pola, ada, hasil, bendera, cat) in KODE:
    tambah(par, nilai, satuan, status, sumber, baris_kode(rel, pola), ada, hasil, bendera, cat)

# Buang baris yang bukan parameter model: metadata berkas, uraian ketentuan yang tidak dipakai, dan teks panjang.
BUANG = (r"^regulasi\.meta\.", r"^regulasi\.ketentuan_terkait\.", r"^neraca_dasar\.meta\.", r"^neraca_dasar\.tidak_dimodelkan", r"^pasar\.meta\.(tanggal|catatan)",
         r"^profil\.instrumen\.", r"^parameter_solusi\.kendala\.C[123]$", r"\.proksi$", r"^profil\.urutan_varian$", r"^regulasi\.batas_ayd_investasi\.perlakuan_kelebihan",
         r"^regulasi\.solvabilitas\.modul_mmbr$", r"^parameter_terpadu\.bencana\.kurva_dasar$", r"\.sebaran$", r"^regulasi\.batas_ayd_investasi\.satu_pihak_bukan_terkait")
sebelum = len(BARIS)
BARIS = [b for b in BARIS if not any(re.search(pola, b["parameter"]) for pola in BUANG)]
print(f"dibuang {sebelum - len(BARIS)} baris bukan parameter model")

KELUAR.parent.mkdir(parents=True, exist_ok=True)
with open(KELUAR, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(BARIS[0].keys()))
    w.writeheader()
    w.writerows(BARIS)
print(f"{len(BARIS)} baris ditulis ke {KELUAR}")
from collections import Counter
print("status:", dict(Counter(b["status_di_kode"] or "(kosong)" for b in BARIS)))
print("berbendera:", sum(1 for b in BARIS if b["bendera_sumber_lemah"]), "; uji kepekaan ada (ya...):", sum(1 for b in BARIS if str(b["uji_kepekaan_ada"]).startswith("ya")),
      "; diuji auditor:", sum(1 for b in BARIS if "auditor" in str(b["uji_kepekaan_ada"])))
