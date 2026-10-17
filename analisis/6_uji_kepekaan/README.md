# Uji kepekaan struktural Rev. 2

Folder ini memuat bahan yang menghasilkan `analisis/5_solusi_motera/keluaran/kepekaan_struktural.csv`.

## Isi

| Berkas atau folder | Isi |
| --- | --- |
| `susun_kepekaan_struktural.py` | Menyusun tabel. Kasus dasar dibaca dari `rancangan.json`; dua kasus premi gempa dihitung dengan mesin repositori; empat kasus lain dibaca dari `hasil_lab/` |
| `hasil_lab/<kasus>/` | Ringkasan rantai penuh yang dijalankan di lab pada Varian A, K70: `t3_strategi.csv` (aturan titik), `t4_aturan_batas_atas.csv` (aturan batas atas), `t3_t4.json`, `05_parameter.json` (bobot kurva) |
| `maipark_juni2025/` | Gambar halaman MAIPARK edisi 30 Juni 2025 yang disalin tangan (`t11_atas.png`, `t11_bawah.png`: Tabel 1.1; `t41.png`: Tabel 4.1; `hlm82.png`: profil risiko), tabel pembanding dua edisi, dan `data_uji/` (empat berkas data yang dipakai uji) |
| `skrip_lab/` | Skrip lab apa adanya (arsip). Jalurnya mengandaikan salinan repo di folder lab (`rev2_lab/<varian>/AIC_CASE/...`), jadi tidak langsung jalan dari sini |

## Kasus

| Kasus | Yang diubah terhadap dasar | Cara dijalankan |
| --- | --- | --- |
| dasar | - | rantai penuh di repositori |
| nu 1,5 dan nu 6 | `NU` di `2_model_bencana/R/00_fungsi.R` | R 04, R 05, mesin, rancangan (lab) |
| eksposur Juni 2025 saja | `portofolio_titik.csv` (bobot provinsi = rata-rata UY 2021-2024 edisi Juni), `maipark_eksposur_provinsi.csv`, `besaran_industri.json` (deret eksposur) | R 04, R 05, mesin, rancangan (lab) |
| eksposur dan tabel klaim Juni 2025 | seperti di atas, ditambah `maipark_kejadian_klaim.csv` | R 03, R 04, R 05, mesin, rancangan (lab) |
| E dasar tahun penutupan 2024 | pilihan `eksposur` = eksposur UY 2024 dibagi premi harta benda 2024 | mesin repositori |
| premi gempa 22,83 per 100 premi | tarif disetarakan sehingga E x tarif = premi gempa UY 2024 dibagi premi harta benda 2024 | mesin repositori |

Pada kasus lab, aturan titik dan aturan batas atas dihitung dari tahun simulasi yang sama. Nilai bersih memakai fungsi tujuan dasar (tanpa biaya pelaksanaan).

## Yang disalin tangan

Teks MAIPARK edisi Juni 2025 berupa gambar vektor dan tidak dapat diekstrak. Angka di `skrip_lab/f03_susun_data.py` (kamus `T11` dan `T41`) disalin dari gambar di `maipark_juni2025/`. Pemeriksaan yang dijalankan skrip itu: jumlah 34 provinsi tiap tahun penutupan cocok dengan baris TOTAL tercetak (selisih paling besar 0,01 triliun), dan 16 rasio klaim cocok dengan rasio tercetak. Tabel premi per provinsi dan eksposur berjalan edisi Juni tidak disalin, sehingga E = 139,16 dan tarif per provinsi tetap dari edisi Desember 2024. Eksposur Papua UY 2020 (tidak ada di edisi Juni) diskalakan dengan rasio revisi UY 2021 (0,512); ini asumsi.

## Cara mengulang kasus lab

1. Salin folder `analisis/` dan `data/` ke folder kerja terpisah dengan susunan `…/<kasus>/AIC_CASE/` (salinan repo, bukan repo ini).
2. Untuk nu: ganti `NU <- 3` di `2_model_bencana/R/00_fungsi.R`. Untuk data Juni 2025: timpa empat berkas di `1_olah_data/data/` dengan isi `maipark_juni2025/data_uji/` (untuk kasus "eksposur saja", biarkan `maipark_kejadian_klaim.csv` edisi Desember).
3. Jalankan `Rscript R/03_kerentanan.R` (hanya bila tabel klaim diganti), `R/04_simulasi_kerugian.R`, `R/05_konsistensi_dan_ekor.R`, lalu `python kode/jalankan_terpadu.py` dan `python 5_solusi_motera/kode/rancang_solusi.py`.
4. Baca `rancangan.json`: `calon[*].target_C1`, `target_C1_titik`, `terpilih`, `terpilih_titik`.

Jangan menjalankan langkah 2 dan 3 di repositori: keluaran dasar akan tertimpa.
