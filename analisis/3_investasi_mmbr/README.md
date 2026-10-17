# analisis/3_investasi_mmbr

Satu tempat untuk dua submodel pada alur metode paper AIC: **model hasil investasi** dan **perhitungan MMBR** PT Aktu Proteksi, disesuaikan dengan POJK 26/2025 dan SEOJK 24/2017. Model kerugian bencana sengaja belum dijalankan di sini.

## Mulai dari mana

| Pembaca | Buka | Isinya |
| --- | --- | --- |
| Manusia | [LAPORAN.md](LAPORAN.md) | Gambaran analisis lengkap: ringkasan, kaitan dengan kasus, dasar regulasi, data, model, hasil, arti untuk tiap soal, keterbatasan |
| AI atau program | [KONTEKS_AI.yaml](KONTEKS_AI.yaml) | Hal yang sama dalam bentuk terstruktur: lingkup, aturan pakai, alur, rumus, jejak regulasi ke kode, asumsi, angka kunci per varian, temuan beserta buktinya, pertanyaan terbuka |
| Yang butuh angka mentah | [keluaran/hasil.json](keluaran/hasil.json) dan `keluaran/tabel/*.csv` | Semua hasil; sumber kebenaran angka |
| Yang ingin mengubah masukan | `parameter/*.yaml` | Regulasi, profil, neraca dasar, pasar; tiap butir bersumber atau ditandai asumsi |

## Isi folder

```
analisis/3_investasi_mmbr/
├── README.md               peta ini
├── LAPORAN.md              laporan untuk manusia (dihasilkan)
├── KONTEKS_AI.yaml         konteks untuk AI (dihasilkan)
├── parameter/
│   ├── regulasi.yaml       batas AYD dan faktor risiko, dengan rujukan pasal
│   ├── profil.yaml         tiga profil brief dan sembilan variannya
│   ├── neraca_dasar.yaml   neraca per 100 premi: nilai, sumber, status
│   └── pasar.yaml          kondisi awal, instrumen, bootstrap, skenario
├── kode/
│   ├── semua.py            menjalankan empat langkah di bawah berurutan
│   ├── jalankan.py         model -> keluaran/hasil.json dan tabel CSV
│   ├── buat_gambar.py      hasil.json -> keluaran/gambar/*.png
│   ├── buat_laporan.py     templat + hasil.json -> LAPORAN.md dan KONTEKS_AI.yaml
│   ├── uji.py              pemeriksaan konsistensi
│   ├── data_pasar.py, model_investasi.py, mmbr.py, rekonstruksi_industri.py, umum.py
│   └── templat_laporan.md, templat_konteks_ai.yaml
└── keluaran/
    ├── hasil.json
    ├── tabel/              sepuluh tabel rapi
    └── gambar/             delapan gambar
```

## Cara menjalankan

Dari folder ini, dengan Python 3.11 dan paket numpy, pandas, matplotlib, openpyxl, pyyaml:

```powershell
python kode\semua.py
```

Lamanya kurang dari satu menit. Benih acak tetap, jadi hasilnya sama tiap kali.

Dua aturan agar dokumen dan angka tidak berselisih:

1. `LAPORAN.md` dan `KONTEKS_AI.yaml` jangan disunting langsung. Ubah `kode/templat_laporan.md` atau `kode/templat_konteks_ai.yaml`, lalu jalankan ulang.
2. Angka tidak diketik di templat. Templat merujuk jalur di `hasil.json`, misalnya `{{mmbr.pada_target.K75.mmbr|a2}}`.

## Yang sudah dan yang belum

| Bagian | Status |
| --- | --- |
| Model hasil investasi (bootstrap blok, lima instrumen, sembilan varian) | Selesai |
| Uji batas AYD (POJK 26/2025 Pasal 15) | Selesai |
| MMBR lima modul (SEOJK 24/2017) dan neraca pada target 120% | Selesai |
| Peluang rasio di bawah 100% dari risiko investasi saja | Selesai |
| Model kerugian bencana dan hasil underwriting | Ditahan |
| Peluang pelanggaran gabungan, komposisi akhir dalam rentang, target solvabilitas | Menunggu model bencana |

Hasil utama dan batas pemakaiannya ada di [LAPORAN.md](LAPORAN.md) bagian 1 dan 10.
