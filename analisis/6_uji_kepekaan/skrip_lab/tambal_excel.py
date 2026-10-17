"""Tambalan Rev. 2 untuk 5_solusi_motera/kode/buat_excel.py dan hitung_ulang_excel.py (dijalankan sekali)."""
import sys
from pathlib import Path

d = Path(sys.argv[1])


def tambal(nama, pasangan):
    f = d / nama
    s = f.read_text(encoding="utf-8")
    for a, b in pasangan:
        assert s.count(a) == 1, (nama, a[:70])
        s = s.replace(a, b)
    f.write_text(s, encoding="utf-8")
    print(nama, "ditambal")


tambal("buat_excel.py", [
    ('''    p = h["perbandingan"]
    calon = h["calon"][st_pilih]
''',
     '''    p = h["perbandingan"]
    calon = h["calon"][st_pilih]
    # Rev. 2: skala premi dibaca dari strategi terpilih, bukan ditulis mati untuk batas 10%.
    # porsi = porsi premi gempa yang terkena syarat khusus (1 bila syarat berlaku untuk seluruh portofolio);
    # skala efektif = 1 - (1 - faktor premi gempa strategi) / porsi, sehingga premi dilepas = premi gempa x porsi x (1 - skala).
    khusus = _strategi(st_pilih, "syarat_khusus")
    khusus = khusus if isinstance(khusus, str) and khusus else ""
    porsi_syarat = float(_strategi(st_pilih, "porsi_premi_khusus")) if khusus else 1.0
    skala_syarat = 1.0 - (1.0 - calon["faktor_premi_gempa"]) / porsi_syarat
    nama_syarat = khusus or str(_strategi(st_pilih, "syarat"))
    kd = h.get("kerugian_dialihkan", {})
'''),
    ('''        ("Porsi premi gempa di zona inti", float(_strategi(st_pilih, "porsi_premi_khusus")), "", "data", "Papua, Jawa Barat, Jakarta, Sumatera Utara, Banten; MAIPARK (2025)", PERSEN1, False),
        ("Skala premi polis batas 10% nilai", pt["skala_premi_syarat"]["batas10"]["nilai"], "", "regulasi", "SEOJK 6/2017 Lampiran III Tabel III.B", PERSEN1, False),''',
     '''        ("Porsi premi gempa yang terkena syarat strategi terpilih", porsi_syarat, "", "data", f"{calon['keterangan']}; zona inti: Papua, Jawa Barat, Jakarta, Sumatera Utara, Banten; MAIPARK (2025)", PERSEN1, False),
        (f"Skala premi syarat strategi terpilih ({nama_syarat})", skala_syarat, "", "regulasi", "SEOJK 6/2017 Lampiran III Tabel III.B; dibaca dari strategi terpilih", PERSEN1, False),'''),
    ('''        ("Premi gempa di zona inti", f"=C4*{A['porsi']}", "(1) x porsi premi zona inti", ANGKA, F_TAUT),
        ("Premi yang dilepas karena batas 10%", f"=C5*(1-{A['skala10']})", "(2) x (1 - skala premi loss limit)", ANGKA, F_TAUT),''',
     '''        ("Premi gempa yang terkena syarat strategi terpilih", f"=C4*{A['porsi']}", "(1) x porsi premi yang terkena syarat", ANGKA, F_TAUT),
        (f"Premi yang dilepas karena syarat ({calon['keterangan']})", f"=C5*(1-{A['skala10']})", "(2) x (1 - skala premi loss limit)", ANGKA, F_TAUT),'''),
    ('''    lebar(ws, [50, 14, 14, 14, 14, 14, 14, 62])
    diagram = BarChart()''',
     '''    # ---- Rev. 2: perspektif perusahaan, biaya pelaksanaan dua kali, titik impas, dan kerugian yang dialihkan
    tulis(ws, "A48", "D. Perspektif perusahaan, uji biaya dua kali, dan kerugian yang dialihkan (Rev. 2)", F_TEBAL)
    kepala(ws, 49, ["Butir", "Tahun 0", "Tahun 1", "Tahun 2", "Tahun 3", "Tahun 4", "Tahun 5", "Keterangan"])
    tulis(ws, "A50", "Arus kas bersih, perspektif perusahaan", bungkus=True)
    tulis(ws, "H50", "Arus kas bersih tanpa suku defisit harapan pemegang polis (bukan arus kas pemegang saham)", bungkus=True)
    tulis(ws, "A54", "Arus kas bersih diperluas, biaya pelaksanaan dua kali", bungkus=True)
    tulis(ws, "A56", "Arus kas bersih perusahaan, biaya pelaksanaan dua kali", bungkus=True)
    for c in "BCDEFG":
        tulis(ws, f"{c}50", f"={c}10-{c}7", F_BIASA, ANGKA1)
        tulis(ws, f"{c}54", f"={c}10+({c}8+{c}9)*(2/{A['kali']}-1)", F_BIASA, ANGKA1)
        tulis(ws, f"{c}56", f"={c}54-{c}7", F_BIASA, ANGKA1)
    tambahan = [
        (51, "NPV perspektif perusahaan (tanpa suku defisit)", "=SUMPRODUCT(B50:G50,B11:G11)", ANGKA1, "Positif berarti solusi lebih murah daripada modal saja bagi pemegang saham"),
        (52, "Titik impas biaya modal, perspektif perusahaan", "=IRR(B50:G50,0.1)", PERSEN, "Di atas titik ini solusi lebih murah"),
        (53, "Titik impas biaya modal, diperluas", "=B15", PERSEN, "Sama dengan baris 15"),
        (55, "NPV diperluas, biaya pelaksanaan dua kali", "=SUMPRODUCT(B54:G54,B11:G11)", ANGKA1, "Uji pengali biaya 2 (parameter_solusi.yaml)"),
        (57, "NPV perspektif perusahaan, biaya pelaksanaan dua kali", "=SUMPRODUCT(B56:G56,B11:G11)", ANGKA1, ""),
        (58, "Titik impas biaya modal diperluas, biaya dua kali", "=IRR(B54:G54,0.1)", PERSEN, ""),
        (59, "Titik impas biaya modal perusahaan, biaya dua kali", "=IRR(B56:G56,0.1)", PERSEN, ""),
        (60, "Kerugian dialihkan ke pemegang polis, rata-rata setahun (Rp miliar)", f"={kd.get('rata_per_tahun', 0)}*{A['skala']}", ANGKA1,
         "Kerugian polis standar dikurangi kerugian strategi terpilih pada tahun simulasi yang sama"),
        (61, "Kerugian dialihkan pada 0,5% tahun terburuk (Rp miliar)", f"={kd.get('rata_ekor_0_5', 0)}*{A['skala']}", ANGKA1, "Rata-rata pada tahun ekor polis standar"),
        (62, "Porsi kerugian ekor polis standar yang dialihkan", kd.get("porsi_ekor_0_5", 0), PERSEN1, ""),
        (63, "Premi yang tidak lagi dibayar tertanggung setahun (Rp miliar)", f"={HM}D{R['premi_dilepas'] if 'premi_dilepas' in R else R['premi']}*0+{kd.get('premi_dilepas', 0)}*{A['skala']}", ANGKA1, "Premi gempa yang dilepas"),
    ]
    for i, nama, rumus, fmt, ket in tambahan:
        tulis(ws, f"A{i}", nama, F_TEBAL, bungkus=True)
        tulis(ws, f"B{i}", rumus, F_TEBAL if isinstance(rumus, str) else F_MASUK, fmt, ISI_HASIL)
        tulis(ws, f"H{i}", ket, bungkus=True)
    lebar(ws, [50, 14, 14, 14, 14, 14, 14, 62])
    diagram = BarChart()'''),
])

tambal("hitung_ulang_excel.py", [
    ('''    bm = nilai["Biaya_Manfaat"]
''',
     '''    bm = nilai["Biaya_Manfaat"]
    # Rev. 2: perspektif perusahaan dan biaya pelaksanaan dua kali, dihitung ulang di Python untuk pencocokan
    arus_p = [dE - awal] + [-(dL + tahunan)] * (n - 1) + [-(dL + tahunan) - dE]
    npv_p = sum(a / (1 + k) ** t for t, a in enumerate(arus_p))
    arus_x2 = [dE - 2 * awal] + [-(dL - dD + 2 * tahunan)] * (n - 1) + [-(dL - dD + 2 * tahunan) - dE]
    npv_x2 = sum(a / (1 + k) ** t for t, a in enumerate(arus_x2))
    arus_p_x2 = [dE - 2 * awal] + [-(dL + 2 * tahunan)] * (n - 1) + [-(dL + 2 * tahunan) - dE]
    npv_p_x2 = sum(a / (1 + k) ** t for t, a in enumerate(arus_p_x2))
    kd = h.get("kerugian_dialihkan", {})
'''),
    ('''               ("Nilai bersih solusi", nilai["Hasil_Model"]["D25"].value, p["terpilih"]["nilai_bersih"])]''',
     '''               ("Nilai bersih solusi", nilai["Hasil_Model"]["D25"].value, p["terpilih"]["nilai_bersih"]),
               ("NPV perspektif perusahaan", bm["B51"].value, npv_p), ("NPV diperluas, biaya dua kali", bm["B55"].value, npv_x2),
               ("NPV perusahaan, biaya dua kali", bm["B57"].value, npv_p_x2),
               ("Kerugian dialihkan rata-rata (Rp miliar)", bm["B60"].value, kd.get("rata_per_tahun", 0.0) * skala)]'''),
    ('''             "jumlah_rumus": jumlah_rumus, "galat_rumus": len(galat)}''',
     '''             "jumlah_rumus": jumlah_rumus, "galat_rumus": len(galat),
             # ---- Rev. 2 (kunci baru; kunci lama tidak diubah) ----
             "profil_acuan": h["meta"]["profil"], "aturan_peluang": h["meta"].get("aturan_peluang"),
             "strategi_terpilih": h["terpilih"]["strategi"], "target_terpilih": h["terpilih"]["target"],
             "target_modal_saja": p["modal_saja"]["target"],
             "npv_diperluas_miliar": bm["B14"].value, "npv_perusahaan_miliar": bm["B51"].value,
             "npv_diperluas_biaya_x2_miliar": bm["B55"].value, "npv_perusahaan_biaya_x2_miliar": bm["B57"].value,
             "impas_biaya_modal_diperluas": bm["B53"].value, "impas_biaya_modal_perusahaan": bm["B52"].value,
             "impas_biaya_modal_diperluas_biaya_x2": bm["B58"].value, "impas_biaya_modal_perusahaan_biaya_x2": bm["B59"].value,
             "kerugian_dialihkan_rata_miliar": bm["B60"].value, "kerugian_dialihkan_ekor_0_5_miliar": bm["B61"].value,
             "porsi_kerugian_ekor_dialihkan": bm["B62"].value, "premi_tidak_dibayar_tertanggung_miliar": bm["B63"].value,
             "skala_premi_syarat_terpilih": nilai["Asumsi"]["B12"].value, "porsi_premi_terkena_syarat": nilai["Asumsi"]["B11"].value}'''),
])
