# MOTERA: Modal Terpicu untuk Resiliensi Asuransi

Repositori pengerjaan paper **"MOTERA: Modal Terpicu untuk Resiliensi Asuransi Berbasis Uji Tekanan Tiga Lapis pada PT Aktu Proteksi tanpa Reasuransi"**, Actuarial Insight Competition (AIC) 2026, studi kasus asuransi umum PT Aktu Proteksi.

Tim Mepet Daftar, Institut Teknologi Sepuluh Nopember: M. Ma'rufutsani Lutfiansyah (ketua), Fabian Lazuardi Khansa, Iqbal Prakusa Hananto.

Naskah final: [`paper/Paper_AIC_2026_PT_Aktu_Proteksi_Rev9.pdf`](paper/Paper_AIC_2026_PT_Aktu_Proteksi_Rev9.pdf)

## Ringkasan

PT Aktu Proteksi menjual asuransi harta benda tanpa menjadikan reasuransi solusi utama, harus memilih satu dari tiga profil investasi, dan memiliki target solvabilitas internal 120%. Ketahanannya diuji dengan kerangka tiga lapis: ekonomi dan pasar, guncangan klaim, serta neraca dan regulasi. Enam model dipakai: kerugian katastrofe berbasis kejadian, klaim atritional, hasil investasi, neraca dan MMBR menurut SEOJK 24/2017 dalam simulasi 100.000 tahun, uji tekanan, dan evaluasi solusi.

| Soal | Jawaban di paper |
| --- | --- |
| 1. Profil investasi | Konservatif 70/30: patuh batas AYD POJK 26/2025, imbal hasil 4,33% pada pasar 2026 (Agresif −4,40%), aset siap cair hampir dua kali klaim satu kejadian 1 dalam 200 tahun |
| 2. Mitigasi klaim massal tanpa reasuransi | Aset siap cair, modal inti dari laba ditahan, dan modal terpicu; persyaratan polis yang lebih ketat tidak cukup secara mandiri |
| 3. Modul MMBR paling mungkin terjadi | Risiko asuransi (20,6% per tahun; modul pasar 10,8%) |
| 4. Kecukupan target 120% | Belum memadai: peluang rasio di bawah 100% sebesar 0,71% (di atas ambang 0,5%), rasio setelah megathrust −122% |
| 5. Solusi inovasi | MOTERA: modal inti 205% dari laba ditahan dan komitmen pinjaman subordinasi siaga 66 turun ke 32 per 100 premi sepanjang tahun. Peluang pelanggaran 0,27%; rasio setelah megathrust 136% (125% pada pasar 2026); dalam 10 hari kerja rasio pulih ke paling rendah 120,3%, sedangkan selama jeda rasio berada di bawah 100%. Biaya 1,43 sampai 4,80 per 100 premi setahun, dibandingkan dengan 6,67 untuk menahan dana yang sama di neraca. Status kelayakan: layak bersyarat |

## Susunan repositori

```
AIC2026-PT-Aktu-Proteksi/
├── paper/                  naskah final (PDF)
├── data/                   data sumber, dikelompokkan per tipe
│   ├── ekonomi_pasar/      BI, BPS, PHEI, SBN, deposito, IHSG, OECD
│   ├── industri_asuransi/  OJK statistik 2024 dan 2025, MAIPARK, AAUI, penetrasi
│   └── katastrofe/         gempa (USGS, intensitas, kerentanan, eksposur GEM), bencana BNPB 2025, IRBI 2024
├── referensi/              regulasi OJK, polis standar, dokumen teknis, jurnal terbuka, daftar pustaka
├── analisis/               kode dan keluaran tiap tahap analisis + register asumsi (Excel)
│   ├── 1_olah_data/        ekstraksi MAIPARK dan OJK menjadi tabel rapi
│   ├── 2_model_bencana/    model kerugian katastrofe (R)
│   ├── 3_investasi_mmbr/   model hasil investasi dan MMBR (Python)
│   ├── 4_simulasi_terpadu/ neraca 100.000 tahun, matriks skenario, kerugian kritis
│   ├── 5_solusi_motera/    rancangan solusi, MOTERA, biaya dan kelayakan
│   └── 6_uji_kepekaan/     uji kepekaan struktural
└── laporan/                kode penyusun angka, gambar, dan naskah; gambar paper
```

Setiap folder utama punya README sendiri: [data](data/README.md), [referensi](referensi/README.md), [analisis](analisis/README.md), [laporan](laporan/README.md).

## Tipe data

| Tipe | Folder | Isi pokok | Dipakai untuk |
| --- | --- | --- | --- |
| Ekonomi dan pasar | [`data/ekonomi_pasar/`](data/ekonomi_pasar/) | Deret SBN, deposito, IHSG dan LQ45, suku bunga OECD, kurva PHEI 9 Oktober 2026, rilis BI, BPS, dan OJK | Model hasil investasi, skenario pasar 2026, soal 1 |
| Industri asuransi | [`data/industri_asuransi/`](data/industri_asuransi/) | Statistik Perasuransian OJK 2024 (xlsx dan PDF), Statistik Asuransi Juli 2025, laporan statistik gempa MAIPARK | Neraca representatif, rasio klaim, eksposur dan klaim gempa |
| Katastrofe | [`data/katastrofe/`](data/katastrofe/) | Katalog gempa USGS 1976–2025, observasi intensitas, kurva kerentanan, eksposur GEM, kejadian bencana BNPB 2025, IRBI 2024 | Model kerugian katastrofe, skenario banjir dan megathrust |
| Regulasi | [`referensi/regulasi/`](referensi/regulasi/) | POJK 26/2025, POJK 28/2025, SEOJK 24/2017, SEOJK 6/2017, Polis Standar Asuransi Gempa Bumi Indonesia | Batas AYD, faktor risiko MMBR, tarif gempa, syarat pinjaman subordinasi |

## Menjalankan ulang

Kebutuhan: Python 3.11 dengan paket di [`requirements.txt`](requirements.txt), dan R 4.4 dengan paket data.table, ggplot2, jsonlite, MASS, fitdistrplus, extRemes. Benih acak ditetapkan di berkas parameter, jadi angka yang sama akan diperoleh.

```bash
pip install -r requirements.txt
```

Urutan tahap dan perintah lengkapnya ada di [analisis/README.md](analisis/README.md). Ringkasnya: `1_olah_data` → `2_model_bencana` (R) → `3_investasi_mmbr` → `4_simulasi_terpadu` → `5_solusi_motera`. Keluaran setiap tahap sudah disertakan, sehingga tahap mana pun bisa dijalankan tanpa mengulang tahap sebelumnya.

Pemeriksaan bawaan yang lulus pada repositori ini (15 Oktober 2026): 109 pemeriksaan model investasi dan MMBR, 40 pemeriksaan rumus pembayaran klaim (R), dan 32 pemeriksaan simulasi terpadu. Seluruh rantai, dari ekstraksi data, model bencana R (termasuk simulasi 100.000 tahun), simulasi terpadu, dan matriks skenario sampai rancangan solusi dan MOTERA, dijalankan ulang di sini dan menghasilkan angka yang sama dengan keluaran yang disertakan.

## Padanan jalur di paper

Lampiran 1 dan 5 paper menulis jalur folder kerja tim. Padanannya di repositori ini:

| Jalur di paper | Lokasi di repositori |
| --- | --- |
| `02_data/katalog_usgs` | [`data/katastrofe/gempa/katalog_usgs/`](data/katastrofe/gempa/katalog_usgs/) |
| `02_data/hazard_gempa` | [`data/katastrofe/gempa/intensitas/`](data/katastrofe/gempa/intensitas/) |
| `02_data/arsip_resmi/raw/bnpb` | [`data/katastrofe/bencana_bnpb_2025/`](data/katastrofe/bencana_bnpb_2025/) |
| `02_data/bahaya_multi` | [`data/katastrofe/indeks_risiko_irbi/`](data/katastrofe/indeks_risiko_irbi/) |
| `02_data/ojk_statistik_2024` | [`data/industri_asuransi/ojk_statistik_2024/`](data/industri_asuransi/ojk_statistik_2024/) |
| `02_data/indikator_bersumber.csv` | [`data/ekonomi_pasar/indikator_bersumber.csv`](data/ekonomi_pasar/indikator_bersumber.csv) |
| `01_referensi/regulasi` | [`referensi/regulasi/`](referensi/regulasi/) |
| `D_data/01` sampai `04` | [`analisis/1_olah_data/`](analisis/1_olah_data/) |
| `E_model_bencana/R/00` sampai `05`, `uji_rumus_bayar.R` | [`analisis/2_model_bencana/R/`](analisis/2_model_bencana/R/) |
| `05_investasi_mmbr/kode`, `05_investasi_mmbr/parameter` (termasuk `regulasi.yaml`) | [`analisis/3_investasi_mmbr/`](analisis/3_investasi_mmbr/) |
| `F_simulasi_terpadu/parameter_terpadu.yaml`, `F_simulasi_terpadu/kode`, `F_simulasi_terpadu/keluaran/matriks_skenario.json` | [`analisis/4_simulasi_terpadu/`](analisis/4_simulasi_terpadu/) |
| `G_solusi/kode` (`rancang_solusi.py`, `motera.py`) | [`analisis/5_solusi_motera/kode/`](analisis/5_solusi_motera/kode/) |
| Buku kerja register asumsi (Lampiran 2) | [`analisis/REGISTER_ASUMSI_DAN_SUMBER.xlsx`](analisis/REGISTER_ASUMSI_DAN_SUMBER.xlsx) |
| `07_laporan/kode` | [`laporan/kode/`](laporan/kode/) |

## Yang tidak disertakan

- Dokumen studi kasus dan buku panduan AIC 2026, beserta templat naskahnya, karena merupakan materi lomba. Profil investasi dari studi kasus tercatat di [`analisis/3_investasi_mmbr/parameter/profil.yaml`](analisis/3_investasi_mmbr/parameter/profil.yaml) dan Tabel 24 paper.
- PDF jurnal dan buku yang tidak berlisensi terbuka. Semua rujukan tetap tercantum lengkap dengan DOI atau tautannya di [referensi/README.md](referensi/README.md).
- Lembar orisinalitas bertanda tangan. Di PDF publik, halamannya diganti keterangan agar nomor halaman tetap sama dengan daftar isi.
- Naskah Word, termasuk versi yang disunting tim sesuai EYD. Skrip `laporan/kode/rev8_*.py` dan `rev9_padat.py` disertakan sebagai jejak penyuntingan, tetapi memerlukan berkas Word tersebut.
- Arsip mentah yang tidak dipakai di paper (katalog BMKG, layanan InaRISK, tabel BPS SP2022, GeoJSON USGS mentah) serta dokumen kerja internal (catatan kerja, audit, dan draf revisi).

## Hak cipta

Data dan dokumen di `data/` dan `referensi/` tetap milik penerbitnya masing-masing dan disertakan untuk keperluan reproduksi dengan sumber yang dicantumkan. Artikel di `referensi/jurnal/` mengikuti lisensi Creative Commons yang tertera pada tiap artikel. Kode dan analisis disusun oleh Tim Mepet Daftar.
