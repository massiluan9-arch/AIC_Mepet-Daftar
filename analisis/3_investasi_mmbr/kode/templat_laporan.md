# Analisis Hasil Investasi dan MMBR PT Aktu Proteksi

Kondisi pasar per {{meta.tanggal_kondisi_awal}}. Simulasi {{meta.jumlah_tahun_simulasi|a0}} tahun. Nilai neraca dinyatakan {{meta.satuan_neraca}}.

Dokumen ini mencakup dua dari tiga submodel pada alur metode: model hasil investasi dan perhitungan MMBR. Model kerugian bencana ditahan, jadi semua kesimpulan di sini berlaku untuk risiko investasi dan kebutuhan modal menurut regulasi saja. Angka di dokumen ini diisi otomatis dari `keluaran/hasil.json`; jangan disunting dengan tangan (lihat Lampiran B).

## 1. Ringkasan

**Jawaban sementara untuk soal 1: profil Konservatif, dengan SBN bertenor paling panjang 5 tahun.** Enam ukuran yang mendasarinya:

| Ukuran | Konservatif | Moderat | Agresif |
| --- | --- | --- | --- |
| Patuh batas AYD (Pasal 15 POJK 26/2025) | Seluruh rentang | Hanya bila obligasi korporasi paling tinggi 50% | Tidak; 20% sampai 30% investasi tidak diakui |
| Beban modal aset per 100 investasi (SEOJK 24/2017, AAA sampai AA) | {{turunan.rentang_beban_aset_AAA_AA.Konservatif.0|a2}} sampai {{turunan.rentang_beban_aset_AAA_AA.Konservatif.1|a2}} | {{turunan.rentang_beban_aset_AAA_AA.Moderat.0|a2}} sampai {{turunan.rentang_beban_aset_AAA_AA.Moderat.1|a2}} | {{turunan.rentang_beban_aset_AAA_AA.Agresif.0|a2}} sampai {{turunan.rentang_beban_aset_AAA_AA.Agresif.1|a2}} |
| Ekuitas untuk rasio 120%, per 100 premi | {{mmbr.pada_target.K80.ekuitas|a1}} sampai {{mmbr.pada_target.K70.ekuitas|a1}} | {{mmbr.pada_target.M40.ekuitas|a1}} sampai {{mmbr.pada_target.M60.ekuitas|a1}} | {{mmbr.pada_target.A30.ekuitas|a1}} sampai {{mmbr.pada_target.A20.ekuitas|a1}} |
| Imbal hasil rata-rata setahun | {{profil.K70.imbal_hasil.bersama.rata|p1}} sampai {{profil.K80.imbal_hasil.bersama.rata|p1}} | {{profil.M40.imbal_hasil.bersama.rata|p1}} sampai {{profil.M60.imbal_hasil.bersama.rata|p1}} | {{profil.A40.imbal_hasil.bersama.rata|p1}} sampai {{profil.A20.imbal_hasil.bersama.rata|p1}} |
| Peluang rasio jatuh di bawah 100% karena investasi saja | {{solvabilitas_investasi.neraca_sendiri.bersama.K70.peluang_di_bawah_100|p2}} sampai {{solvabilitas_investasi.neraca_sendiri.bersama.K80.peluang_di_bawah_100|p2}} | {{solvabilitas_investasi.neraca_sendiri.bersama.M60.peluang_di_bawah_100|p2}} sampai {{solvabilitas_investasi.neraca_sendiri.bersama.M40.peluang_di_bawah_100|p2}} | {{solvabilitas_investasi.neraca_sendiri.bersama.A20.peluang_di_bawah_100|p2}} sampai {{solvabilitas_investasi.neraca_sendiri.bersama.A40.peluang_di_bawah_100|p2}} |
| Aset siap cair per 100 premi | {{kepatuhan_lain.K80.aset_siap_cair.jumlah|a0}} sampai {{kepatuhan_lain.K70.aset_siap_cair.jumlah|a0}} | {{kepatuhan_lain.M60.aset_siap_cair.jumlah|a0}} sampai {{kepatuhan_lain.M40.aset_siap_cair.jumlah|a0}} | {{kepatuhan_lain.A30.aset_siap_cair.jumlah|a0}} |

Baris kelima dihitung pada jendela data 2012-2024, dengan rasio awal 120% dan hasil underwriting ditahan nol. Ambang yang dipakai alur metode adalah 0,5%.

Empat hal yang perlu diketahui sebelum memakai hasil ini:

1. **Tenor SBN menentukan lebih banyak daripada pilihan 80/20 atau 70/30.** Dengan SBN 10 tahun, peluang pelanggaran profil Konservatif naik menjadi {{tenor_sbn.10.bersama.rasio_akhir.peluang_di_bawah_100|p2}}, lebih buruk daripada profil Moderat. Dengan SBN 2 tahun peluangnya {{tenor_sbn.2.bersama.rasio_akhir.peluang_di_bawah_100|p2}}.
2. **Profil Moderat dengan obligasi korporasi 40% sampai 50% adalah pesaing terdekat.** Imbal hasilnya {{turunan.selisih_imbal_M50_K75|q2}} lebih tinggi. Ia kalah pada jendela data panjang (peluang pelanggaran {{solvabilitas_investasi.neraca_sendiri.panjang.M50.peluang_di_bawah_100|p2}}), tidak punya deposito, dan risiko kreditnya kurang-taksir di model ini.
3. **Bantalan 20% tipis.** Untuk profil Konservatif 75/25 bantalan itu {{turunan.bantalan_di_atas_100|a2}} per 100 premi. Kerugian investasi 1-dalam-200 tahun saja memakai {{turunan.porsi_bantalan_terpakai_investasi|p0}} darinya. Ini masukan untuk soal 4.
4. **Risiko asuransi mengisi {{turunan.porsi_asuransi_patuh.0|p0}} sampai {{turunan.porsi_asuransi_patuh.1|p0}} MMBR** pada varian yang patuh. Ini masukan untuk soal 3, baru dari sisi besaran.

Yang belum bisa dijawab di sini: peluang pelanggaran gabungan (investasi dan bencana), komposisi akhir di dalam rentang Konservatif, dan target solvabilitas yang memadai. Ketiganya menunggu model kerugian bencana.

## 2. Kaitan dengan kasus

Brief meminta empat hal yang disentuh analisis ini. Tabel berikut menunjukkan bagian mana menjawab apa, supaya analisis tidak keluar dari yang diminta.

| Yang diminta brief atau panduan | Yang dikerjakan di sini | Bagian |
| --- | --- | --- |
| Soal 1: profil mana yang paling sesuai kondisi ekonomi saat ini | Kepatuhan AYD, beban modal, sebaran imbal hasil, peluang pelanggaran, dan likuiditas untuk sembilan varian dari tiga profil | 5, 6, 7, 8 |
| Ketentuan C.5: tidak boleh mengusulkan alokasi di luar tabel | Semua varian adalah titik ujung atau titik tengah rentang brief | 5.3 |
| Latar belakang: inflasi | Imbal hasil riil terhadap inflasi {{data.kondisi_awal.inflasi|p2}} | 5.3 |
| Latar belakang: suku bunga acuan | Kurva imbal hasil 9 Oktober 2026 sebagai titik awal; risiko kenaikan lanjutan lewat bootstrap dan skenario; tenor SBN | 4, 5.5, 8.2 |
| Latar belakang: daya beli masyarakat | Tidak dimodelkan sebagai angka. Dibaca sebagai tekanan arus kas (premi harta benda turun 13,6% dan klaimnya naik 75,8% pada semester I 2026), sehingga likuiditas menjadi kriteria | 7.6 |
| Latar belakang: profil risiko pemegang polis | Tidak dimodelkan sebagai angka. Dibaca sebagai kebutuhan kepastian bayar klaim, sehingga ukuran keputusannya peluang rasio jatuh di bawah 100% | 8.1 |
| Soal 3: modul MMBR dengan kemungkinan tertinggi | Besaran kelima modul per varian. Kemungkinan tiap modul menunggu model bencana | 7.3 |
| Soal 4: kecukupan target 120% | Ukuran bantalan 20%, porsi yang terpakai risiko investasi, dan risiko yang tidak tertangkap rumus MMBR | 8.1, 8.3 |
| Soal 2: mitigasi klaim massal tanpa reasuransi | Hanya satu masukan: aset siap cair per profil | 7.6 |
| Referensi brief: SEOJK 24/2017 | Kelima modul dihitung menurut lampirannya | 7 |
| Panduan Bab 3: analisis deskriptif, hasil pemodelan, interpretasi | Bagian 4 (data), 5 sampai 8 (hasil), 9 (interpretasi per soal) | - |

## 3. Dasar regulasi

Teks kedua peraturan dibaca langsung dari `referensi/regulasi`. Rujukan lengkap per angka ada di `parameter/regulasi.yaml`.

| Ketentuan | Isi | Perlakuan di model |
| --- | --- | --- |
| POJK 26/2025 Pasal 3 ayat (1) | Tingkat Solvabilitas paling rendah 100% MMBR; target internal paling rendah 120% dengan memperhitungkan profil risiko dan stress test | Neraca tiap varian disusun tepat pada 120%, lalu diuji |
| POJK 26/2025 Pasal 1 angka 12 | Tingkat Solvabilitas = AYD dikurangi Liabilitas | Pembilang rasio |
| POJK 26/2025 Pasal 4 ayat (1) | MMBR memperhitungkan risiko kredit, likuiditas, pasar, asuransi, operasional | Lima modul |
| POJK 26/2025 Pasal 5 ayat (1) dan penjelasannya | Prinsip kehati-hatian: keamanan, imbal hasil optimal, kebutuhan likuiditas, profil liabilitas | Empat ukuran pembanding profil |
| POJK 26/2025 Pasal 15 | Batas AYD investasi: deposito 20% per bank; obligasi korporasi 20% per emiten dan 50% seluruhnya; saham 10% per emiten dan 40% seluruhnya; reksa dana 20% per manajer investasi dan 50% seluruhnya; gabungan huruf d sampai m 80%; SBN tanpa batas | Porsi di atas batas tidak dihitung sebagai AYD |
| POJK 26/2025 Pasal 8 | SBN boleh direpokan untuk menjaga likuiditas | SBN masuk aset siap cair setelah potongan |
| POJK 26/2025 Pasal 25 ayat (2) huruf b | Tagihan premi diakui bila berumur paling lama 2 bulan | Tagihan premi = dua bulan premi |
| POJK 26/2025 Pasal 34 | AYD investasi ditambah kas paling sedikit sebesar cadangan teknis dan liabilitas klaim retensi sendiri | Uji kecukupan investasi |
| POJK 26/2025 Pasal 55 dan 56 | Dana jaminan wajib berupa deposito atau SBN | Uji ketersediaan per profil |
| POJK 26/2025 Pasal 85 | Peraturan pelaksana POJK 71/2016 tetap berlaku sepanjang tidak bertentangan | SEOJK 24/2017 tetap menjadi dasar MMBR |
| SEOJK 24/2017 Lampiran II angka 1 | Risiko kredit: SBN 0%; deposito 1,2% sampai 9% menurut peringkat bank; obligasi korporasi 1,6% sampai 12%; tagihan premi 8% | Modul kredit |
| SEOJK 24/2017 Lampiran II angka 2 | Risiko likuiditas: 4% dari kekurangan AYD terhadap liabilitas pada tiap kelompok jatuh tempo | Modul likuiditas |
| SEOJK 24/2017 Lampiran II angka 3 | Risiko pasar: saham IDX30 15%, saham lain 20%; reksa dana ekuitas 16%; risiko tingkat bunga hanya atas cadangan premi jangka panjang | Modul pasar. Obligasi tidak dibebani risiko suku bunga |
| SEOJK 24/2017 Lampiran II angka 4 | Risiko asuransi harta benda: 25% CAPYBMP, 20% cadangan klaim, 25% cadangan bencana, neto reasuransi | Modul asuransi |
| SEOJK 24/2017 Lampiran II angka 5 | Risiko operasional: 1% beban umum dan administrasi setelah dikurangi pendidikan dan pelatihan, ditambah 50% biaya akuisisi ditangguhkan | Modul operasional |

Satu hal berupa tafsir: Pasal 15 tidak menyebut akibat pelampauan batas. Model memperlakukan kelebihannya sebagai aset yang tidak diakui. Dasarnya judul pasal (pembatasan atas AYD), penjelasan ayat (1) yang menyebut SBN "dapat seluruhnya diperhitungkan sebagai AYD" karena tidak dibatasi, dan fakta bahwa Pasal 15 tidak ada dalam daftar pasal bersanksi pada Pasal 36.

## 4. Data dan kondisi awal

![Data pasar](keluaran/gambar/g1_data_pasar.png)

*Gambar 1. Tiga deret masukan. Bidang kelabu menandai jendela saat ketiganya tersedia bersama. Sumber: OECD dan AsianBondsOnline (imbal hasil), Yahoo Finance (LQ45), Bank Indonesia SEKI Tabel I.28 (deposito).*

Kondisi awal simulasi:

{{tabel:kondisi_awal}}

Ringkasan data historis:

{{tabel:deskriptif}}

Deret imbal hasil SBN bulanan berhenti di Desember 2024. Karena itu ada dua jendela. Jendela bersama (2012-2024) hanya memakai bulan saat semua deret teramati. Jendela panjang (2000-2026) menambah {{data.jendela.panjang.bulan_diimputasi}} bulan data saham, termasuk 2008 dan 2026; perubahan imbal hasil pada bulan-bulan itu ditaksir dari regresi atas imbal hasil saham (R² {{data.jendela.panjang.r2_dy10|a2}}) ditambah residu acak. Jendela bersama adalah dasar. Jendela panjang adalah uji banding yang lebih keras untuk saham.

## 5. Model hasil investasi

### 5.1 Cara kerja

1. Hitung perubahan bulanan lima faktor: imbal hasil SBN 10 dan 2 tahun, LQ45, IHSG, dan bunga deposito 1 bulan.
2. Susun satu tahun simulasi dari dua potongan enam bulan berurutan yang diambil acak dari sejarah (bootstrap blok). Kelima faktor diambil pada bulan yang sama, sehingga hubungan antarfaktor, misalnya imbal hasil naik saat saham turun, ikut terbawa tanpa asumsi distribusi.
3. Nilai ulang tiap instrumen setahun kemudian:
   - SBN dan obligasi korporasi: dibeli pada harga nominal hari ini, lalu dihargai ulang dengan sisa tenor yang berkurang setahun pada imbal hasil baru, ditambah kupon. Perubahan imbal hasil pada tenor antara 2 dan 10 tahun diinterpolasi lurus.
   - Obligasi korporasi: ditambah kerugian gagal bayar. Portofolio berisi {{instrumen.konfigurasi_dasar.jumlah_emiten}} emiten berbobot sama; tiap emiten gagal bayar dengan peluang tertentu dan saat gagal kehilangan 60% nilainya.
   - Deposito: bunga 1 bulan yang digulirkan dua belas kali.
   - Saham: imbal hasil LQ45 ditambah dividen 3%. Reksa dana saham: imbal hasil IHSG.
4. Jumlahkan menurut bobot tiap varian profil.
5. Ulangi {{meta.jumlah_tahun_simulasi|a0}} kali dan ringkas sebarannya.

Semua imbal hasil sebelum pajak dan biaya transaksi.

### 5.2 Hasil per instrumen

{{tabel:instrumen}}

Dua hal perlu dicatat. Rata-rata imbal hasil saham sangat bergantung pada jendela: {{instrumen.bersama.saham.rata|p1}} pada 2012-2024 dan {{instrumen.panjang.saham.rata|p1}} pada 2000-2026. Ukuran risikonya lebih bisa dipegang daripada rata-ratanya. Kedua, obligasi korporasi tampak hampir tanpa risiko harga karena selisih imbal hasilnya dianggap tetap; itu keterbatasan data, bukan sifat instrumennya (lihat bagian 10).

### 5.3 Hasil per profil

![Sebaran imbal hasil](keluaran/gambar/g2_sebaran_imbal_hasil.png)

*Gambar 2. Sebaran imbal hasil setahun tiap varian. Sumber: simulasi penulis atas data pada Gambar 1.*

{{tabel:profil}}

VaR dan TVaR dinyatakan sebagai kerugian. Galat simulasi kecil: untuk Konservatif 75/25, galat baku rata-rata {{profil.K75.imbal_hasil.bersama.galat_baku_rata|p2}} dan galat baku VaR 99,5% {{profil.K75.imbal_hasil.bersama.galat_baku_var_99_5|p2}}.

Yang terbaca:

- Ketiga profil memberi imbal hasil riil positif. Konservatif memberi {{profil.K70.imbal_hasil.bersama.rata_riil|p1}} sampai {{profil.K80.imbal_hasil.bersama.rata_riil|p1}} di atas inflasi.
- Pada jendela bersama, profil Agresif tidak memberi imbal hasil rata-rata yang lebih tinggi daripada Moderat, tetapi risikonya dua sampai tiga kali lipat.
- Selisih rata-rata Moderat terhadap Konservatif sekitar {{turunan.selisih_imbal_M50_K75|q2}}. Selisih risikonya kecil pada jendela bersama dan melebar pada jendela panjang.
- Di dalam profil Konservatif, menambah deposito dari 20% ke 30% menurunkan VaR 99,5% dari {{profil.K80.imbal_hasil.bersama.var_99_5|p2}} ke {{profil.K70.imbal_hasil.bersama.var_99_5|p2}} dengan biaya {{profil.K80.imbal_hasil.bersama.rata|p2}} menjadi {{profil.K70.imbal_hasil.bersama.rata|p2}} pada rata-rata.

### 5.4 Uji kewajaran dan kepekaan

Sebaran faktor hasil simulasi dibandingkan dengan jendela 12 bulan bergulir pada data:

{{tabel:validasi}}

Simulasi sedikit lebih lebar daripada sejarah. Sebabnya: potongan enam bulan memutus kecenderungan imbal hasil untuk berbalik setelah bergerak jauh. Arah biasnya hati-hati. Hubungan terbalik antara imbal hasil dan saham juga lebih kuat pada simulasi; ini memberatkan profil yang memegang obligasi dan saham sekaligus, yaitu Moderat dan Agresif.

Tabel berikut mengubah satu hal tiap kali. Tiap sel berisi VaR 99,5% dan peluang rasio jatuh di bawah 100% (dijelaskan di bagian 8.1).

{{tabel:sensitivitas_investasi}}

Tiga kepekaan yang mengubah bacaan:

- **Tenor SBN.** Ini kepekaan terbesar untuk profil Konservatif dan Moderat. Dibahas di bagian 8.2.
- **Panjang blok.** Dengan blok 12 bulan (tiap tahun simulasi adalah satu jendela sejarah utuh), VaR 99,5% Konservatif 75/25 turun ke {{turunan.var_K75_menurut_blok.12|p2}}; dengan blok 3 bulan naik ke {{turunan.var_K75_menurut_blok.3|p2}}. Tiga belas tahun data tidak cukup untuk menentukan kejadian 1-dalam-200 tahun dengan pasti. Angka ekor di dokumen ini sebaiknya dibaca sebagai rentang, dan urutan antarprofil lebih bisa dipegang daripada nilainya.
- **Klasifikasi akuntansi.** Bila obligasi dicatat dimiliki hingga jatuh tempo, perubahan harganya tidak masuk Tingkat Solvabilitas dan profil Konservatif tidak pernah rugi. Biayanya muncul di risiko likuiditas (bagian 7.5).

### 5.5 Skenario

Empat guncangan setahun diterapkan serentak pada semua varian:

{{tabel:skenario_guncangan}}

Hasilnya, sebagai imbal hasil setahun dan (dalam kurung) rasio solvabilitas akhir bila rasio awal 120%:

{{tabel:skenario}}

Pada ulangan 2026, profil Konservatif masih memberi {{skenario.ulangan_2026.varian.K75|p1}}, Moderat {{skenario.ulangan_2026.varian.M50|p1}}, dan Agresif 30/70 {{skenario.ulangan_2026.varian.A30|p1}}. Bunga deposito pada skenario diasumsikan mengikuti seperempat pergeseran imbal hasil (separuh penerusan, tercapai bertahap).

## 6. Uji batas AYD

![Uji AYD](keluaran/gambar/g3_uji_ayd.png)

*Gambar 3. Porsi investasi yang diakui sebagai AYD. Sumber: perhitungan penulis atas Pasal 15 POJK 26/2025.*

{{tabel:ayd}}

- **Konservatif** patuh di seluruh rentang. Deposito di atas 20% harus disebar di paling sedikit dua bank.
- **Moderat** patuh pada separuh rentangnya. Pada obligasi korporasi 60%, sepuluh poin persentase investasi tidak diakui. Brief melarang keluar dari tabel, tetapi tidak mewajibkan memakai seluruh rentang; bila profil ini dipilih, alokasinya harus berhenti di 50%.
- **Agresif** tidak patuh di titik mana pun. Obligasi korporasi 60% sampai 80% melampaui 50%, dan pada saham 40% batas gabungan 80% ikut terlampaui.

Kolom terakhir menunjukkan jumlah pihak paling sedikit agar batas per bank, per emiten, dan per manajer investasi terpenuhi.

## 7. Perhitungan MMBR

### 7.1 Neraca dasar

Perusahaan ini fiktif. Neracanya disusun per 100 premi dari rasio industri lini harta benda. Karena kasus tidak mengandalkan reasuransi, seluruh cadangan ditanggung sendiri.

{{tabel:neraca_dasar}}

Jumlah investasi dan ekuitas tidak diasumsikan. Keduanya dicari sehingga rasio solvabilitas awal tepat sama dengan target (120%). Dengan cara ini tiap profil dinilai pada tingkat solvabilitas yang sama.

### 7.2 Contoh hitung: Konservatif 75/25

{{tabel:rincian_acuan}}

Dengan investasi {{mmbr.pada_target.K75.investasi|a1}}, AYD = {{mmbr.pada_target.K75.ayd|a1}}, liabilitas = {{mmbr.pada_target.K75.liabilitas|a1}}, Tingkat Solvabilitas = {{mmbr.pada_target.K75.tingkat_solvabilitas|a1}}, dan rasio = {{mmbr.pada_target.K75.tingkat_solvabilitas|a1}} / {{mmbr.pada_target.K75.mmbr|a2}} = {{mmbr.pada_target.K75.rasio|p0}}.

Risiko likuiditas muncul karena rumusnya dibaca harfiah: kekurangan dihitung per kelompok jatuh tempo, dan kelebihan aset di kelompok terpendek tidak menutup kekurangan di kelompok yang lebih panjang.

### 7.3 Hasil per varian pada target 120%

![MMBR per modul](keluaran/gambar/g4_mmbr_per_modul.png)

*Gambar 4. MMBR per modul bila tiap varian berada tepat pada rasio 120%. Sumber: perhitungan penulis atas SEOJK 24/2017.*

{{tabel:mmbr_target}}

- Risiko asuransi sama di semua varian ({{mmbr.pada_target.K75.modul.asuransi|a2}}) karena hanya bergantung pada cadangan. Porsinya {{mmbr.pada_target.K75.porsi_modul.asuransi|p0}} pada Konservatif 75/25 dan {{mmbr.pada_target.A40.porsi_modul.asuransi|p0}} pada Agresif 40/60.
- Pilihan profil menggeser MMBR dari {{mmbr.pada_target.K80.mmbr|a1}} ke {{mmbr.pada_target.A40.mmbr|a1}}. Pergeseran itu seluruhnya berasal dari modul kredit dan pasar.
- Modul operasional kecil ({{mmbr.pada_target.K75.modul.operasional|a2}}) karena perusahaan tanpa PAYDI hampir tidak punya biaya akuisisi ditangguhkan.

### 7.4 Dua cara membandingkan profil

![Neraca sama dan ekuitas](keluaran/gambar/g5_neraca_sama_dan_ekuitas.png)

*Gambar 5. Kiri: rasio solvabilitas bila semua varian memakai neraca Konservatif 75/25. Kanan: ekuitas agar tiap varian mencapai 120%. Sumber: perhitungan penulis.*

**Neraca yang sama.** Ambil neraca Konservatif 75/25 pada 120%, lalu ganti hanya komposisi investasinya:

{{tabel:neraca_sama}}

Berpindah ke Moderat 50/40/10 menurunkan rasio ke {{mmbr.neraca_sama.M50.rasio|p0}}. Berpindah ke Agresif 30/70 menurunkannya ke {{mmbr.neraca_sama.A30.rasio|p0}}, jauh di bawah minimum, terutama karena aset yang tidak diakui.

**Ekuitas untuk target yang sama.** Profil Agresif 30/70 membutuhkan ekuitas {{turunan.kelipatan_ekuitas_A30_K75|a1}} kali profil Konservatif 75/25 untuk rasio yang sama. Moderat 60/30/10 membutuhkan {{turunan.kelipatan_ekuitas_M60_K75|a1}} kali. Ekuitas untuk target lain:

{{tabel:target_lain}}

### 7.5 Kepekaan MMBR

Tiap sel: MMBR dan ekuitas pada target 120%.

{{tabel:sensitivitas_mmbr}}

Yang paling menggeser hasil adalah besarnya CAPYBMP, bukan asumsi aset. Mencatat obligasi sebagai dimiliki hingga jatuh tempo menaikkan risiko likuiditas dari {{mmbr.pada_target.K75.modul.likuiditas|a2}} menjadi {{mmbr.sensitivitas.hingga_jatuh_tempo_sbn_5.K75.modul.likuiditas|a2}} untuk Konservatif 75/25, karena SBN keluar dari kelompok jatuh tempo terpendek sementara liabilitasnya tetap pendek.

### 7.6 Ketentuan lain yang bergantung pada komposisi

{{tabel:kepatuhan_lain}}

- **Dana jaminan** wajib berupa deposito atau SBN. Profil Agresif tidak memegang keduanya, jadi dana jaminan harus ditempatkan di luar alokasi profil.
- **Repo SBN** untuk likuiditas hanya tersedia bagi profil yang memegang SBN.
- **Kecukupan investasi** terpenuhi di semua varian pada target 120%. Dengan neraca yang sama, Agresif 20/80 gagal memenuhinya (rasio {{mmbr.neraca_sama.A20.kecukupan_investasi.rasio|a2}}).
- **Aset siap cair** = kas, deposito, dan SBN setelah potongan repo 10%. Saham dan obligasi korporasi bisa dijual, tetapi pada harga pasar saat itu. Profil Konservatif memegang {{kepatuhan_lain.K75.aset_siap_cair.terhadap_cadangan_klaim|a1}} kali cadangan klaimnya dalam bentuk siap cair; Agresif {{kepatuhan_lain.A30.aset_siap_cair.terhadap_cadangan_klaim|a1}} kali. Perbandingan dengan klaim bencana menunggu model bencana.

\* Kewajiban porsi minimum SBN 20% bagi asuransi umum (POJK 1/POJK.05/2016 dan perubahannya) belum terkonfirmasi masih berlaku pada 2026. Kolom itu informasi tambahan, bukan dasar keputusan.

### 7.7 Uji kewajaran terhadap industri

Mesin hitung yang sama diterapkan pada neraca industri asuransi umum konvensional per 31 Juli 2025 (OJK). Peringkat, jatuh tempo, dan pembagian aset reasuransi tidak dipublikasikan, jadi dipakai dua set asumsi.

{{tabel:industri}}

Rekonstruksi dengan faktor terendah memberi {{rekonstruksi_industri.skenario.faktor_rendah.rasio|p0}}, dekat dengan tetapi di bawah angka resmi {{rekonstruksi_industri.rasio_resmi_ojk|p1}}. Angka resmi berada sedikit di luar rentang. Artinya mesin ini menghasilkan besaran yang seorde dan cenderung menaksir MMBR agak tinggi. Ia layak untuk membandingkan profil, tidak untuk meniru angka OJK sampai satuan persen.

Pada industri, risiko asuransi mengisi sekitar separuh MMBR. Pada PT Aktu Proteksi porsinya lebih besar karena dua hal: tidak ada reasuransi yang mengurangi cadangan neto, dan asetnya lebih sederhana.

## 8. Kaitan hasil investasi dan solvabilitas

### 8.1 Peluang pelanggaran dari risiko investasi saja

Rasio akhir tahun = (Tingkat Solvabilitas awal + investasi × imbal hasil) / MMBR. Hasil underwriting dan kerugian bencana ditahan nol. Ini potongan investasi dari ukuran tunggal pada alur metode, belum ukuran lengkapnya.

![Peluang pelanggaran](keluaran/gambar/g6_peluang_pelanggaran.png)

*Gambar 6. Peluang rasio akhir tahun di bawah 100%, rasio awal 120%. Label menunjukkan nilai yang lebih besar dari dua jendela. Sumber: simulasi penulis.*

{{tabel:peluang}}

- Profil Konservatif berada di bawah ambang 0,5% pada kedua jendela.
- Profil Moderat berada di sekitar ambang pada jendela bersama dan melewatinya pada jendela panjang.
- Profil Agresif melewati ambang pada kedua jendela, padahal sudah diberi ekuitas {{turunan.kelipatan_ekuitas_A30_K75|a1}} kali lebih besar.
- Dua kolom terakhir menunjukkan keadaan bila ekuitasnya tidak ditambah: Moderat 60/30/10 dan seluruh varian Agresif sudah berada di bawah 100% sejak awal.

Galat baku peluang 0,5% dari {{meta.jumlah_tahun_simulasi|a0}} tahun simulasi sekitar 0,02 poin. Ketidakpastian yang lebih besar datang dari panjang blok (bagian 5.4): pada blok 3 bulan Konservatif 80/20 menjadi {{solvabilitas_investasi.sensitivitas.blok_3.K80.peluang_di_bawah_100|p2}}, sedikit di atas ambang.

### 8.2 Tenor SBN

![Tenor SBN](keluaran/gambar/g7_tenor_sbn.png)

*Gambar 7. Konservatif 75/25 dengan tiga pilihan tenor SBN. Sumber: simulasi penulis.*

{{tabel:tenor}}

Imbal hasil awal SBN 10 tahun hanya {{turunan.selisih_imbal_sbn_10_2|q2}} di atas SBN 2 tahun, sementara risikonya berlipat. Rata-rata portofolionya hampir sama di ketiga tenor. Pada kurva sedatar ini, tenor panjang tidak dibayar.

Rumus MMBR tidak membedakan tenor: faktor risiko SBN 0% berapa pun tenornya. Jadi pilihan tenor tidak terlihat di rasio solvabilitas awal, tetapi menentukan seberapa cepat rasio itu bisa turun.

### 8.3 Beban modal menurut rumus lawan kerugian 1-dalam-200 tahun

![Regulasi lawan ekonomi](keluaran/gambar/g8_regulasi_vs_ekonomi.png)

*Gambar 8. Per 100 investasi: beban modal kredit dan pasar menurut SEOJK 24/2017 dan VaR 99,5% hasil simulasi. Sumber: perhitungan dan simulasi penulis.*

{{tabel:regulasi_ekonomi}}

Di semua varian, kerugian 1-dalam-200 tahun hasil simulasi lebih besar daripada beban modal yang diminta rumus. Untuk Konservatif 75/25 selisihnya {{regulasi_vs_ekonomi.K75.var_99_5_bersama|a2}} lawan {{regulasi_vs_ekonomi.K75.beban_mmbr_aset|a2}}: hampir seluruh risiko pasarnya adalah risiko suku bunga atas SBN, yang tidak dibebani SEOJK 24/2017.

Akibatnya untuk bantalan: pada Konservatif 75/25, bantalan 20% bernilai {{turunan.bantalan_di_atas_100|a2}} per 100 premi. Kerugian investasi 1-dalam-200 tahun bernilai {{turunan.kerugian_investasi_1_dalam_200|a2}}. Sisanya, {{turunan.sisa_bantalan_setelah_investasi|a2}} per 100 premi, adalah ruang untuk semua guncangan asuransi sebelum laba underwriting diperhitungkan.

### 8.4 Hasil investasi dibanding ekuitas yang ditanam

{{tabel:efisiensi}}

Moderat 50/40/10 menghasilkan {{turunan.selisih_hasil_investasi_M50_K75|a2}} per 100 premi lebih banyak daripada Konservatif 75/25 dengan tambahan ekuitas {{turunan.selisih_ekuitas_M50_K75|a2}}. Hasil per ekuitas keduanya hampir sama pada jendela bersama. Varian yang melampaui batas AYD jauh tertinggal karena sebagian ekuitasnya membiayai aset yang tidak diakui.

## 9. Arti hasil ini untuk tiap soal

**Soal 1.** Profil Konservatif. Alasannya berurutan:

1. Satu-satunya profil yang patuh AYD di seluruh rentangnya (bagian 6).
2. Beban modal asetnya terendah, sehingga ekuitas untuk target 120% paling kecil (bagian 7.4).
3. Imbal hasil riilnya positif, sekitar {{profil.K75.imbal_hasil.bersama.rata_riil|p1}} di atas inflasi (bagian 5.3).
4. Peluang pelanggaran dari risiko investasi di bawah 0,5% pada kedua jendela data (bagian 8.1).
5. Aset siap cairnya terbesar, dan hanya profil ini yang memegang deposito (bagian 7.6).
6. Pada ulangan guncangan 2026 imbal hasilnya masih {{skenario.ulangan_2026.varian.K75|p1}} (bagian 5.5).

Syaratnya: SBN bertenor paling panjang 5 tahun (bagian 8.2). Biayanya: sekitar {{turunan.selisih_imbal_M50_K75|q2}} imbal hasil per tahun dibanding Moderat, atau {{turunan.selisih_hasil_investasi_M50_K75|a2}} per 100 premi.

Komposisi di dalam rentang belum diputuskan. Deposito 30% unggul pada risiko dan likuiditas; SBN 80% unggul {{turunan.selisih_imbal_K80_K70|q2}} pada imbal hasil. Keputusannya bergantung pada kebutuhan likuiditas saat klaim massal, yaitu keluaran model bencana.

**Soal 2.** Satu masukan: aset siap cair per profil (bagian 7.6). Strategi mitigasinya sendiri menunggu model bencana.

**Soal 3.** Dari sisi besaran, risiko asuransi adalah modul terbesar: {{turunan.porsi_asuransi_patuh.0|p0}} sampai {{turunan.porsi_asuransi_patuh.1|p0}} MMBR pada varian yang patuh. Sisi kemungkinan belum dihitung. Satu catatan sudah bisa ditulis: dengan profil Konservatif, modul pasar bernilai nol menurut rumus, padahal risiko suku bunga SBN nyata (bagian 8.3).

**Soal 4.** Tiga bahan sudah tersedia. Bantalan 20% hanya {{turunan.bantalan_di_atas_100|a2}} per 100 premi. Risiko investasi saja bisa memakai {{turunan.porsi_bantalan_terpakai_investasi|p0}} darinya pada kejadian 1-dalam-200 tahun. Dan MMBR tidak peka terhadap dua risiko yang paling menentukan perusahaan ini: risiko suku bunga atas SBN, dan besar eksposur bencana (risiko asuransi dihitung dari cadangan, bukan dari nilai pertanggungan). Jawaban lengkapnya menunggu model bencana.

## 10. Keterbatasan

1. **Model bencana belum masuk.** Peluang pelanggaran di sini hanya dari investasi. Angka gabungan akan lebih tinggi untuk semua profil.
2. **Data hanya 13 tahun untuk imbal hasil.** Kejadian 1-dalam-200 tahun tidak bisa ditentukan dari 155 bulan. VaR 99,5% Konservatif 75/25 berkisar {{turunan.var_K75_menurut_blok.12|p1}} sampai {{turunan.var_K75_menurut_blok.3|p1}} menurut panjang blok.
3. **Risiko obligasi korporasi kurang-taksir.** Riwayat selisih imbal hasil per peringkat tidak tersedia, dan peluang gagal bayar memakai asumsi. Arah biasnya menguntungkan profil Moderat dan Agresif, jadi kesimpulan memilih Konservatif tidak dilemahkan olehnya.
4. **Jendela panjang memakai imputasi.** Perubahan imbal hasil 2000-2011 dan 2025-2026 ditaksir dari saham dengan R² {{data.jendela.panjang.r2_dy10|a2}}. Gejolak suku bunga 2005 dan 2008 yang sebenarnya lebih besar daripada taksiran itu.
5. **Neraca fiktif.** Rasio industri lini harta benda mencakup perusahaan yang mereasuransikan risikonya. CAPYBMP adalah butir yang paling menggeser hasil.
6. **Imbal hasil saham rata-rata tidak stabil antarjendela.** Kesimpulan tidak bertumpu padanya.
7. **Sebelum pajak dan biaya.** Pajak final atas bunga deposito dan kupon obligasi berbeda dan tidak dimodelkan.
8. **Rumus risiko likuiditas dibaca harfiah.** Bila OJK mengizinkan kelebihan aset jangka pendek menutup kekurangan jangka panjang, modul likuiditas menjadi nol dan MMBR turun {{mmbr.pada_target.K75.modul.likuiditas|a2}}.

## 11. Yang perlu diputuskan atau dicek tim

| Hal | Mengapa penting | Usulan |
| --- | --- | --- |
| Tenor SBN | Mengubah peluang pelanggaran dari {{tenor_sbn.2.bersama.rasio_akhir.peluang_di_bawah_100|p2}} menjadi {{tenor_sbn.10.bersama.rasio_akhir.peluang_di_bawah_100|p2}} | Nyatakan di paper sebagai bagian rekomendasi: paling panjang 5 tahun |
| Klasifikasi akuntansi obligasi | Menentukan apakah perubahan harga masuk Tingkat Solvabilitas | Pakai nilai wajar sebagai dasar; perusahaan asuransi umum perlu bisa menjual SBN saat klaim besar |
| Peluang gagal bayar per peringkat | Asumsi tanpa sumber | Ambil dari studi gagal bayar Pefindo bila ada akses; bila tidak, tulis sebagai asumsi dengan uji tiga kali lipat |
| Imbal dividen dan proksi LQ45 | Asumsi 3%; IDX30 tidak tersedia | Cek lembar fakta indeks BEI |
| Status POJK 1/POJK.05/2016 | Bila masih berlaku, profil Agresif gugur atas satu alasan lagi | Cek di JDIH OJK |
| Imbal hasil SBN bulanan 2025-2026 | Menghapus kebutuhan imputasi untuk dua tahun terakhir | Ambil dari DJPPR |
| Satuan neraca | Dokumen ini memakai per 100 premi dicatat; `rekomendasi_metode.md` menulis per 100 premi neto | Tanpa reasuransi keduanya sama sebelum komisi; pakai satu istilah di paper |

## 12. Perbedaan dari rancangan metode awal tim

Dokumen itu memuat angka indikatif yang dihitung sebelum analisis ini. Empat di antaranya berubah:

| Butir | Di dokumen lama | Di sini | Sebab |
| --- | --- | --- | --- |
| Beban modal aset Moderat per 100 investasi | 2,24 sampai 3,28 | {{turunan.rentang_beban_aset_AAA_AA.Moderat.0|a2}} sampai {{turunan.rentang_beban_aset_AAA_AA.Moderat.1|a2}} | Faktor risiko hanya dikenakan atas porsi yang diakui AYD |
| Beban modal aset Agresif per 100 investasi | 5,24 sampai 7,68 | {{turunan.rentang_beban_aset_AAA_AA.Agresif.0|a2}} sampai {{turunan.rentang_beban_aset_AAA_AA.Agresif.1|a2}} | Sama; porsi tidak diakui dipotong dari AYD, bukan dibebani |
| MMBR per 100 premi | 24 sampai 35 | {{mmbr.pada_target.K80.mmbr|a1}} sampai {{mmbr.pada_target.A40.mmbr|a1}} | Cadangan dari data lini harta benda; biaya akuisisi ditangguhkan dari rasio industri, bukan asumsi 7,5 |
| Rekonstruksi rasio industri | 256% sampai 352%, mengapit angka OJK | {{rekonstruksi_industri.skenario.faktor_tinggi.rasio|p0}} sampai {{rekonstruksi_industri.skenario.faktor_rendah.rasio|p0}}, angka OJK sedikit di atasnya | Pembilang di sini AYD dikurangi liabilitas, bukan ekuitas |

Akibat bagi soal 4: tabel indikatif pada bagian 8.3 dokumen lama memakai MMBR 24 sampai 35. Dengan MMBR sekitar {{mmbr.pada_target.K75.mmbr|a0}}, bantalan 20% lebih kecil dan target yang dibutuhkan pada tiap nilai E akan lebih tinggi. Tabel itu perlu dihitung ulang saat model bencana dijalankan.

Yang tidak berubah: arah jawaban soal 1 (Konservatif), kepatuhan AYD tiap profil, dan temuan bahwa SEOJK 24/2017 tidak membebani risiko suku bunga atas SBN.

## Lampiran A. Daftar asumsi

{{tabel:asumsi}}

## Lampiran B. Berkas dan cara mengulang

| Berkas | Isi |
| --- | --- |
| `README.md` | Peta folder |
| `KONTEKS_AI.yaml` | Isi yang sama dengan dokumen ini dalam bentuk terstruktur untuk dibaca program atau AI |
| `parameter/*.yaml` | Seluruh masukan: regulasi, profil, neraca dasar, pasar |
| `kode/jalankan.py` | Menjalankan model dan menulis `keluaran/hasil.json` serta `keluaran/tabel/*.csv` |
| `kode/buat_gambar.py`, `kode/buat_laporan.py` | Menggambar dan mengisi dokumen ini dari `hasil.json` |
| `kode/uji.py` | Pemeriksaan konsistensi |
| `keluaran/hasil.json` | Semua angka |

Untuk mengulang seluruhnya dari folder `analisis/3_investasi_mmbr`:

```powershell
python kode\semua.py
```

Benih acak tetap ({{meta.benih}}), jadi hasilnya sama tiap kali dijalankan.

## Lampiran C. Sumber

- Otoritas Jasa Keuangan. Peraturan OJK Nomor 26 Tahun 2025 tentang Pengelolaan Aset dan Liabilitas Perusahaan Asuransi dan Perusahaan Reasuransi. `referensi/regulasi`.
- Otoritas Jasa Keuangan. Surat Edaran OJK Nomor 24/SEOJK.05/2017 tentang Pedoman Perhitungan Jumlah Modal Minimum Berbasis Risiko. `referensi/regulasi`.
- Otoritas Jasa Keuangan. Statistik Perasuransian 2024, Tabel 2.10.4. `data/industri_asuransi/ojk_statistik_2024`.
- Otoritas Jasa Keuangan. Statistik Asuransi Juli 2025. `data/industri_asuransi/ojk_statistik_2025`.
- Data pasar: OECD, AsianBondsOnline, Yahoo Finance, Bank Indonesia SEKI Tabel I.28, PHEI lewat Pusat Data Kontan. Rincian dan keterbatasan di `data/ekonomi_pasar/pasar_riwayat/README.md`.
- Indikator makro dan industri 2026: `data/ekonomi_pasar/indikator_bersumber.csv`.
