# Data

Data sumber yang dipakai paper, dikelompokkan menurut tipe. Semua data berada pada tingkat industri atau nasional karena studi kasus tidak menyediakan data polis, klaim, atau neraca perusahaan. Hasil olahan (tabel rapi) berada di [`analisis/1_olah_data/data/`](../analisis/1_olah_data/data/).

```
data/
├── ekonomi_pasar/
│   ├── pasar_riwayat/          deret pasar untuk model hasil investasi
│   ├── makro/                  rilis resmi BI dan OJK
│   └── indikator_bersumber.csv indikator makro dan industri beserta sumber dan tanggal akses
├── industri_asuransi/
│   ├── ojk_statistik_2024/     Statistik Perasuransian 2024 (xlsx dan PDF)
│   ├── ojk_statistik_2025/     Statistik Asuransi Juli 2025
│   ├── maipark/                laporan statistik asuransi gempa bumi
│   ├── aaui/                   analisa industri triwulan IV 2025
│   └── penetrasi/              penetrasi asuransi rumah
└── katastrofe/
    ├── gempa/
    │   ├── katalog_usgs/       katalog gempa 1976-2025
    │   ├── intensitas/         observasi intensitas teramati
    │   ├── kerentanan_bangunan/ tabel kurva kerentanan dari literatur
    │   └── eksposur_gem/       ringkasan model eksposur GEM
    ├── bencana_bnpb_2025/      kejadian dan dampak bencana 2025
    └── indeks_risiko_irbi/     indeks risiko bencana per kabupaten dan kota
```

## Ekonomi dan pasar

| Berkas atau folder | Isi | Sumber dan tanggal akses | Dipakai oleh |
| --- | --- | --- | --- |
| `pasar_riwayat/` | IHSG dan LQ45 bulanan, imbal hasil SBN dan suku bunga (OECD), selisih dan volatilitas SBN harian, kurva imbal hasil PHEI 9 Oktober 2026, bunga deposito rupiah (SEKI Tabel I.28, berkas asli `.xls` ikut disimpan), deposito dan inflasi tahunan | Yahoo Finance, OECD, AsianBondsOnline, PHEI, Bank Indonesia, World Bank; 9-11 Oktober 2026. Rincian dan keterbatasan di [README folder](ekonomi_pasar/pasar_riwayat/README.md) | `analisis/3_investasi_mmbr/kode/data_pasar.py`, `parameter/pasar.yaml` |
| `makro/BI_siaran_pers_RDG_September_2026.html` | BI-Rate 5,75% | Bank Indonesia (2026a) | Bab 1, Tabel 26 |
| `makro/BI_Survei_Konsumen_September_2026.pdf` | Porsi tabungan 15,4% dari pendapatan | Bank Indonesia (2026c) | Bab 1, Tabel 26 |
| `makro/OJK_SNLIK_2026_siaran_pers.pdf` | Indeks literasi dan inklusi perasuransian 2026 | OJK, siaran pers SNLIK 2026 | Tabel 26 |
| `indikator_bersumber.csv` | Indikator makro dan industri dengan nilai, periode, sumber, URL, jenis bukti, berkas lokal, dan tanggal akses | Dirangkum penulis, 11-13 Oktober 2026 | `parameter/pasar.yaml`, Lampiran 1 |

## Industri asuransi

| Berkas atau folder | Isi | Sumber | Dipakai oleh |
| --- | --- | --- | --- |
| `ojk_statistik_2024/` | Indikator kunci, tabel keuangan, rekap premi-klaim-komisi, premi dan klaim per perusahaan 2024, beserta buku PDF-nya | OJK (2025b), Statistik Perasuransian 2024 | `analisis/1_olah_data/03_*.py`, `04_*.py`; `analisis/3_investasi_mmbr` (neraca dasar dan uji); Gambar 2 |
| `ojk_statistik_2025/OJK_Statistik_Asuransi_Juli_2025.xlsx` | Neraca dan laba rugi asuransi umum, Juli 2025 | OJK (2025c) | `analisis/1_olah_data/03_*.py`, `analisis/3_investasi_mmbr/kode/rekonstruksi_industri.py` |
| `maipark/MAIPARK_Statistik_Gempa_per_31_Des_2024.pdf` | Eksposur, premi, dan klaim gempa per provinsi; 16 kejadian klaim terbesar; profil risiko | PT Reasuransi MAIPARK Indonesia (2025); diakses 12 Oktober 2026 | `analisis/1_olah_data/01_ekstrak_maipark.py` |
| `maipark/MAIPARK_Statistik_Gempa_Juni_2025.pdf` | Edisi 30 Juni 2025 | MAIPARK | Uji kepekaan (`analisis/6_uji_kepekaan`) |
| `aaui/AAUI_Analisa_Triwulan_IV_2025.pdf` | Komposisi investasi asuransi umum | AAUI | `indikator_bersumber.csv` |
| `penetrasi/I06_penetrasi_asuransi_rumah.csv` | Porsi rumah yang diasuransikan | MAIPARK melalui ANTARA dan Bisnis.com | Bab 1 |

## Katastrofe

| Berkas atau folder | Isi | Sumber dan tanggal akses | Dipakai oleh |
| --- | --- | --- | --- |
| `gempa/katalog_usgs/eq_a.csv`, `eq_b.csv`, `eq_c.csv` | Katalog gempa wilayah Indonesia, M ≥ 5, berturut-turut 1976-1995, 1996-2010, 2011-2025 | U.S. Geological Survey, ANSS ComCat; 10 Oktober 2026 | `analisis/2_model_bencana/R/00_fungsi.R` (dibaca R01, R04, R05) |
| `gempa/intensitas/mmi_obs_indonesia.csv` | Observasi intensitas gempa dangkal beserta jarak dan Vs30 | USGS ShakeMap dan DYFI | `R/02_intensitas_validasi.R` |
| `gempa/kerentanan_bangunan/V01` sampai `V08` | Tipologi bangunan dan rasio kerusakan Aulady dan Fujimi (2019), parameter logistik hasil pencocokan, rasio kerugian per tingkat kerusakan, kerusakan rumah gempa 2006, parameter PAGER Indonesia | Literatur (sumber tertulis pada kolom `sumber` tiap berkas) | Parameter kurva di `R/00_fungsi.R` |
| `gempa/eksposur_gem/` | Ringkasan eksposur bangunan Indonesia per provinsi dan taksonomi | GEM Foundation, Global Exposure Model | `analisis/1_olah_data/02_susun_portofolio.py` |
| `bencana_bnpb_2025/` | Jumlah kejadian, rekap kejadian dan dampak, rumah rusak 2025 (JSON DataStore) | BNPB (2026), Kompilasi Data Kejadian dan Dampak Bencana 2025; 12 Oktober 2026 | Gambar 2, Tabel 10 |
| `indeks_risiko_irbi/IRBI_2024_indeks_per_ancaman_kabkota.csv` | Skor dan kelas risiko gempa, tsunami, dan gunung api per kabupaten dan kota | BNPB, IRBI 2024 (salinan BPBD Kota Dumai); diekstrak dari buku; 11 Oktober 2026 | Bab 1, Tabel 10 |

## Skenario tanpa berkas mentah

- Skenario banjir Jabodetabek 2020: klaim properti Rp1,008 triliun (Kontan, 2020) dibagi premi langsung harta benda 2020 Rp17,93 triliun (OJK, 2021). Kedua angka tercatat dengan sumbernya di [`analisis/4_simulasi_terpadu/parameter_terpadu.yaml`](../analisis/4_simulasi_terpadu/parameter_terpadu.yaml).
- Skenario megathrust Selat Sunda M 8,7: parameter sumber gempa ada di [`analisis/2_model_bencana/R/04_simulasi_kerugian.R`](../analisis/2_model_bencana/R/04_simulasi_kerugian.R), dengan rujukan potensi magnitudo menurut BMKG (dikutip Tempo, 2024) dan peta sumber gempa nasional 2017 ([`referensi/dokumen_teknis/`](../referensi/dokumen_teknis/)).
- Skenario pasar Ulangan 2026: kenaikan imbal hasil 100 bps, selisih korporasi 50 bps, dan saham turun 30%, tercatat di `analisis/3_investasi_mmbr/parameter/pasar.yaml`.
