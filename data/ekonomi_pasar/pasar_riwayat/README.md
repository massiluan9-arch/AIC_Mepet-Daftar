# Data pasar untuk soal 1

Diunduh 11 Oktober 2026. Semua berkas CSV sudah dirapikan dari sumber aslinya; kolom dan satuan tertulis di baris judul.

| Berkas | Isi | Periode | Sumber |
| --- | --- | --- | --- |
| `saham_IHSG_LQ45_bulanan.csv` | Penutupan bulanan IHSG dan LQ45 | Jan 2000 - Okt 2026 | Yahoo Finance, simbol ^JKSE dan ^JKLQ45 |
| `suku_bunga_OECD_bulanan.csv` | Imbal hasil obligasi pemerintah jangka panjang (10 tahun), antarbank 3 bulan, call money | 10 tahun: Jan 2012 - Des 2024; 3 bulan: Jan 2005 - Des 2025; call money: sampai Agu 2026 | OECD Data Explorer, dataset Financial Market (DF_FINMARK), Indonesia |
| `SBN_selisih_10th_2th_harian_ABO.csv` | Selisih imbal hasil SBN 10 tahun dikurangi 2 tahun, basis poin, harian | Jan 2006 - 8 Okt 2026 | AsianBondsOnline (ADB), data dari Bloomberg |
| `SBN_volatilitas_imbal_hasil_10th_harian_ABO.csv` | Simpangan baku perubahan harian imbal hasil 10 tahun dalam 21 hari | Jan 2006 - 8 Okt 2026 | AsianBondsOnline (ADB) |
| `kurva_imbal_hasil_PHEI_2026-10-09.csv` | Kurva imbal hasil SBN dan obligasi korporasi AAA, AA, A, BBB per tenor 0,1 sampai 10 tahun, plus selisih AAA dan AA terhadap SBN | 9 Okt 2026 | PHEI, dikutip dari Pusat Data Kontan |
| `deposito_rupiah_bank_umum_bulanan_SEKI.csv` | Suku bunga deposito rupiah bank umum, tenor 1, 3, 6, 12, 24 bulan | Jan 1990 - Agu 2026 | Bank Indonesia, SEKI Tabel I.28 (berkas asli `BI_SEKI_Tabel_I28_...xls` ikut disimpan) |
| `deposito_dan_inflasi_tahunan_WorldBank.csv` | Bunga deposito dan inflasi IHK tahunan | 1990 - 2025 | World Bank, indikator FR.INR.DPST dan FP.CPI.TOTL.ZG |

## Keterbatasan

- Imbal hasil 10 tahun bulanan berhenti di Desember 2024. Untuk 2025-2026 yang ada hanya selisih 10 tahun terhadap 2 tahun (harian), volatilitas, dan kurva satu hari (9 Oktober 2026). Level bulanan 2025-2026 perlu diambil manual dari DJPPR atau Investing.com bila ingin deret lengkap.
- Obligasi korporasi hanya punya kurva satu hari, tidak ada riwayat. Riwayat selisih per peringkat tidak tersedia terbuka; PHEI menjualnya. Pilihan: pakai selisih hari ini sebagai nilai dasar dan beri guncangan skenario.
- Tingkat gagal bayar per peringkat dari Pefindo tidak bisa diunduh: halaman studi gagal bayarnya meminta login anggota.
- IDX30 tidak tersedia di Yahoo Finance. LQ45 dipakai sebagai pengganti saham unggulan.
- Indeks saham berupa indeks harga, belum termasuk dividen.
- Lembar SEKI 2009-2018 dan 2010-2024 tumpang tindih; nilai dari lembar yang lebih baru yang dipakai.

## Ringkasan statistik awal

Dihitung dari berkas di folder ini.

| Ukuran | Nilai |
| --- | --- |
| Imbal hasil tahunan IHSG 2001-2026 | Rata-rata 14,7%, simpangan baku 29,5% |
| Tahun IHSG turun lebih dari 15% | 2008 (-50,6%) dan 2026 (-29,5% sampai Oktober) |
| Peluang imbal hasil 12 bulan IHSG di bawah -16% (jendela bergulir bulanan, 310 pengamatan) | 9,0% |
| Imbal hasil SBN 10 tahun 2012-2024 | Rata-rata 7,09%, rentang 5,15% sampai 9,64% |
| Perubahan imbal hasil 10 tahun dalam 12 bulan | Simpangan baku 1,11 poin; persentil 95 +2,28 poin; terbesar +3,55 poin |
| Korelasi perubahan imbal hasil 12 bulan dengan imbal hasil IHSG 12 bulan | -0,31 |
| Kurva SBN 9 Okt 2026 | 2 tahun 6,78%; 5 tahun 7,05%; 10 tahun 7,18% |
| Obligasi korporasi 3 tahun, 9 Okt 2026 | AAA 7,46% (selisih 56 bps); AA 7,71% (selisih 81 bps) |
| Deposito rupiah bank umum, Agu 2026 | 1 bulan 5,08%; 12 bulan 5,45% |

Jendela 12 bulan bergulir saling tumpang tindih, jadi peluang 9,0% itu bukan dari pengamatan yang saling bebas.
