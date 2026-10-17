# Analisis

Enam tahap analisis paper, berurutan dari data mentah sampai solusi. Setiap tahap menyimpan kode, parameter, dan keluarannya di foldernya sendiri. Keluaran semua tahap sudah disertakan, jadi satu tahap dapat dijalankan ulang tanpa mengulang tahap sebelumnya.

```
analisis/
├── 1_olah_data/            data mentah -> tabel rapi (data/)
├── 2_model_bencana/        model kerugian katastrofe (R) -> keluaran/, gambar/
├── 3_investasi_mmbr/       model hasil investasi dan MMBR -> keluaran/, LAPORAN.md
├── 4_simulasi_terpadu/     neraca 100.000 tahun, matriks skenario, kerugian kritis -> keluaran/
├── 5_solusi_motera/        rancangan solusi dan MOTERA -> keluaran/, Analisis_Solusi_AIC.xlsx
├── 6_uji_kepekaan/         uji kepekaan struktural
├── REGISTER_ASUMSI_DAN_SUMBER.xlsx   buku kerja register asumsi (Lampiran 2 paper)
└── register_asumsi_mentah.csv        bahan register
```

Alur antartahap mengikuti kerangka tiga lapis paper: lapis guncangan klaim (tahap 2), lapis ekonomi dan pasar (tahap 3), dan lapis neraca dan regulasi (tahap 4), lalu solusi (tahap 5).

## Kebutuhan

- Python 3.11 dengan paket di [`requirements.txt`](../requirements.txt).
- R 4.4 dengan paket data.table, ggplot2, jsonlite, MASS, fitdistrplus, extRemes.
- Opsional: Microsoft Excel di Windows untuk `hitung_ulang_excel.py` (menghitung ulang rumus lewat COM), dan pustaka solvency2-python (repositori terpisah, jalurnya diberikan sebagai argumen) untuk `4_simulasi_terpadu/kode/pembanding_solvency2.py`. Keduanya tidak diperlukan untuk angka utama paper.

## Menjalankan

Perintah dijalankan dari folder tahapnya. Benih acak ditetapkan di berkas parameter.

### 1. Olah data (`1_olah_data/`)

```bash
cd analisis/1_olah_data
python 01_ekstrak_maipark.py           # MAIPARK per 31 Des 2024 -> eksposur, premi, klaim per provinsi; 16 kejadian klaim
python 02_susun_portofolio.py          # 37 titik portofolio di 34 provinsi; besaran industri
python 03_ekstrak_underwriting.py      # rasio klaim 2011-2024, komisi, beban usaha
python 04_ekstrak_premi_perusahaan.py  # sebaran premi harta benda per perusahaan
```

Setiap tabel provinsi diperiksa terhadap baris TOTAL yang tercetak di sumbernya.

### 2. Model kerugian bencana (`2_model_bencana/`, R)

```bash
cd analisis/2_model_bencana
Rscript R/01_katalog_frekuensi_magnitudo.R   # binomial negatif, nilai b, deklasterisasi
Rscript R/02_intensitas_validasi.R           # residu intensitas terhadap Allen dkk. (2012)
Rscript R/03_kerentanan.R                    # kurva klaim MAIPARK, Aulady & Fujimi, PAGER
Rscript R/04_simulasi_kerugian.R             # 100.000 tahun; skenario megathrust dan uji balik
Rscript R/05_konsistensi_dan_ekor.R          # bobot kurva campuran, ekor GPD
Rscript R/uji_rumus_bayar.R                  # 40 pemeriksaan rumus pembayaran klaim
```

`R/00_fungsi.R` memuat fungsi bersama (dipanggil oleh skrip lain). Tabel kerugian tahunan `keluaran/04_ylt.csv.gz` (sekitar 40 MB) dan `05_ylt_campuran.csv.gz` dibaca oleh tahap 4.

### 3. Investasi dan MMBR (`3_investasi_mmbr/`)

```bash
cd analisis/3_investasi_mmbr
python kode/semua.py     # model, gambar, laporan, dan 109 pemeriksaan
```

Penjelasan lengkap tahap ini ada di [README](3_investasi_mmbr/README.md) dan [LAPORAN.md](3_investasi_mmbr/LAPORAN.md). Parameter regulasi (batas AYD, faktor risiko) ada di `parameter/regulasi.yaml` dengan rujukan pasalnya.

### 4. Simulasi terpadu (`4_simulasi_terpadu/`)

```bash
cd analisis/4_simulasi_terpadu
python kode/jalankan_terpadu.py    # neraca 100.000 tahun untuk sembilan varian profil dan rancangan
python kode/matriks_skenario.py    # matriks skenario dan kerugian kritis L*
python kode/uji_terpadu.py         # 32 pemeriksaan
python kode/gambar_terpadu.py      # gambar keluaran/gambar/
```

`kode/mesin.py` adalah mesin neraca yang dipakai bersama oleh tahap 4 dan 5. Parameter skenario (banjir 2020, megathrust, pasar 2026) ada di `parameter_terpadu.yaml`.

### 5. Solusi dan MOTERA (`5_solusi_motera/`)

```bash
cd analisis/5_solusi_motera
python kode/rancang_solusi.py      # opsi mitigasi bila berdiri sendiri
python kode/buat_excel.py          # buku kerja Analisis_Solusi_AIC.xlsx
python kode/hitung_ulang_excel.py  # perlu Excel (Windows)
python kode/radar_tangga.py
python kode/motera.py              # jadwal komitmen, dampak, biaya dua perspektif, prasyarat kelayakan
```

Parameter MOTERA (target pemulihan 120%, potongan jaminan SBN, imbalan komitmen, biaya modal) ada di `parameter_solusi.yaml`.

### 6. Uji kepekaan (`6_uji_kepekaan/`)

`susun_kepekaan_struktural.py` menyusun `5_solusi_motera/keluaran/kepekaan_struktural.csv`. Kasus yang memerlukan rantai penuh dijalankan di salinan terpisah; caranya ada di [README tahap ini](6_uji_kepekaan/README.md).

## Keluaran utama dan paper

| Keluaran | Isi | Di paper |
| --- | --- | --- |
| `2_model_bencana/keluaran/` | Parameter dan uji model bencana, ukuran risiko, uji balik | Subbab 3.2.1, Lampiran 3 |
| `3_investasi_mmbr/keluaran/hasil.json` | Imbal hasil, AYD, dan MMBR tiap varian | Subbab 3.2.2, Lampiran 4 |
| `4_simulasi_terpadu/keluaran/hasil_terpadu.json` | Peluang pelanggaran, modul, rasio awal terkecil yang lolos C1-C3 | Subbab 3.2.2 sampai 3.2.5 |
| `4_simulasi_terpadu/keluaran/matriks_skenario.json` | Matriks skenario, profil 330%, kerugian kritis | Tabel 3, Tabel 4, Tabel 30 |
| `5_solusi_motera/keluaran/motera.json` | Jadwal komitmen, dampak MOTERA dan pembanding, biaya, prasyarat | Bab 4, Tabel 28 |
| `5_solusi_motera/keluaran/rancangan.json`, `radar_tangga.json` | Opsi lain yang diuji bila berdiri sendiri | Tabel 29 |
| `REGISTER_ASUMSI_DAN_SUMBER.xlsx` | Nilai, sumber, alasan, dan uji tiap asumsi | Lampiran 2 |

## Pemeriksaan pada repositori ini

Dijalankan 15 Oktober 2026 setelah repositori disusun:

| Langkah | Hasil |
| --- | --- |
| `3_investasi_mmbr/kode/uji.py` | 109 pemeriksaan lulus |
| `2_model_bencana/R/uji_rumus_bayar.R` | 40 pemeriksaan lulus |
| `4_simulasi_terpadu/kode/uji_terpadu.py` | 32 pemeriksaan lulus |
| Tahap 1 (empat skrip), model bencana R 01-05 (termasuk simulasi 100.000 tahun, sekitar 3,5 menit), simulasi terpadu (sekitar 75 detik), matriks skenario, rancangan solusi, MOTERA | Semua angka keluaran sama dengan yang disertakan; yang berbeda hanya catatan lama waktu jalan dan satu teks jalur |
