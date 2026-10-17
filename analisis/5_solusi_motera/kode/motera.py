"""Rev. 4: MOTERA (Modal Terpicu untuk Resiliensi Asuransi) dan opsi pembandingnya.

MOTERA = modal inti dari laba ditahan sampai rasio 205% + komitmen pinjaman subordinasi siaga (POJK 26/2025 Pasal 32)
yang disetor bila pemicu terpenuhi. Komitmen yang belum disetor bukan AYD, jadi rasio awal tidak berubah; dalam
simulasi, tahun yang memicu mendapat tambahan Tingkat Solvabilitas sebesar komitmen (paling banyak), lalu rasio dibaca
ulang. Pemicu: kerugian satu kejadian >= 20 per 100 premi (mewakili pemicu parametrik BMKG dan estimasi kerugian)
atau rasio akhir < 120%.

Isi keluaran:
  - konfigurasi: status quo, 205% tanpa komitmen, MOTERA peralihan (120% + 45), MOTERA tetap (205% + 30),
    tambah modal ke 330%, tambah modal setara (ekuitas = modal inti + komitmen);
    tiap konfigurasi: pelanggaran C1/C2 dan selang, rasio setelah megathrust (pasar normal/2026), peluang komitmen cair;
  - waktu kejadian: kerugian kritis L* menurut bulan kejadian (laba tahun berjalan dianggap terkumpul merata);
  - opsi O0 sampai O7 bila berdiri sendiri; biaya bersih tahunan dengan rentang jaminan SBN; matriks penilaian.
Keluaran: 5_solusi_motera/keluaran/motera.json
Pemakaian: python 5_solusi_motera/kode/motera.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import brentq

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "4_simulasi_terpadu" / "kode"))
import mesin as ms          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
DIR_KELUAR = AKAR / "5_solusi_motera" / "keluaran"
ST = "S0_dasar"


def main():
    p05, pt = ms.muat_semua()
    ps = yaml.safe_load((AKAR / "5_solusi_motera" / "parameter_solusi.yaml").read_text(encoding="utf-8"))
    mo = ps["motera"]
    M = ms.Mesin(p05, pt)
    N = M.n
    batas = ms.pelanggaran_terbanyak(pt["meta"]["ambang_peluang"], N, pt["meta"]["tingkat_selang"])
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    tsi = 100.0 * E
    uw, lk = pt["underwriting"], pt["likuiditas"]
    pajak = uw["pajak"]["nilai"]
    k_modal = ps["biaya_modal"]["nilai"]
    skala = ps["skala_rupiah"]["premi_harta_benda_miliar"] / 100.0          # Rp miliar per 1 unit per 100 premi

    kurva_pasar = ms.dp.muat_kurva(p05["pasar"]["kondisi_awal"]["kurva"]["berkas"])
    spek26 = p05["pasar"]["skenario"]["ulangan_2026"]
    imbal26 = lambda kode: float(ms.mi.imbal_skenario(spek26, kurva_pasar, p05["pasar"], M.varian[kode][2])[0])

    bobot_kurva = json.loads((ms.DIR_BENCANA / "05_parameter.json").read_text(encoding="utf-8"))["bobot_kurva"]
    sk = pd.read_csv(ms.DIR_BENCANA / "04_skenario_strategi.csv")

    def L_mega(st):
        mg = sk[(sk["skenario"] == "Megathrust Jawa bagian barat M 8,7") & (sk["eta"] == 0) & (sk["strategi"] == st)]
        return tsi * sum(bobot_kurva[k] * float(mg[mg["kurva"] == k]["kerugian"].iloc[0]) for k in ms.KURVA_TUNGGAL)

    def mega(kode, s, K=0.0, st=ST, dU=0.0):
        """Rasio akhir setelah megathrust pada pasar normal dan Ulangan 2026, ditambah komitmen K bila cair."""
        out = []
        for im in (None, imbal26(kode)):
            r = M.rasio_skenario(kode, st, s, L_mega(st) / tsi, imbal=im)
            G = r["laba_sebelum_pajak"] + dU
            R = (r["ekuitas"] * 0 + M.neraca_awal(kode, s)["tingkat_solvabilitas"] + G - pajak * max(G, 0.0) + K) / r["mmbr"]
            out.append(R)
        return out

    def simulasi(kode, s, K, kurva, st=ST, rasio_klaim=None):
        o = M.jalankan(kode, st, s, kurva=kurva, rinci=True, rasio_klaim=rasio_klaim)
        d = o["deret"]
        R, m = d["R"], o["mmbr"]
        picu = (d["klaim_kejadian"] >= mo["pemicu_kerugian"]["nilai"]) | (R < mo["pemicu_rasio"]["nilai"])
        R2 = np.where(picu, R + K / m, R) if K > 0 else R
        n = int((R2 < 1.0).sum())
        lo, hi = ms.selang_binomial(n, N, pt["meta"]["tingkat_selang"])
        return {"pelanggaran": n, "peluang": n / N, "selang": [lo, hi], "lolos": n <= batas, "peluang_cair": float(picu.mean()) if K > 0 else 0.0,
                "peluang_cair_bencana": float((d["klaim_kejadian"] >= mo["pemicu_kerugian"]["nilai"]).mean()),
                "rata_dicairkan": float(np.where(picu, np.minimum(K, np.maximum(mo["pemicu_rasio"]["nilai"] * m - R * m, 0.0)), 0.0).mean()) if K > 0 else 0.0,
                "ekuitas": o["ekuitas"], "mmbr": m, "laba_bersih": o["laba_bersih_rata"], "imbal_hasil": o["imbal_hasil_rata"]}

    s_inti, K_tetap, K_alih = mo["target_inti"]["nilai"], mo["komitmen_tetap"]["nilai"], mo["komitmen_peralihan"]["nilai"]
    eku_inti = M.neraca_awal("K70", s_inti)["ekuitas"]
    s_setara = brentq(lambda s: M.neraca_awal("K70", s)["ekuitas"] - (eku_inti + K_tetap), 2.0, 6.0)

    konfig = {"status_quo": ("K70", 1.2, 0.0), "inti_saja": ("K70", s_inti, 0.0), "motera_peralihan": ("K70", 1.2, K_alih),
              "motera_tetap": ("K70", s_inti, K_tetap), "modal_330": ("K70", 3.3, 0.0), "modal_setara": ("K70", s_setara, 0.0)}
    hasil = {}
    for nama, (kode, s, K) in konfig.items():
        c1, c2 = simulasi(kode, s, K, "campuran"), simulasi(kode, s, K, "aulady")
        mn, m26 = mega(kode, s, K)
        b = M.neraca_awal(kode, s)
        hasil[nama] = {"profil": kode, "rasio_awal": s, "komitmen": K, "ekuitas": b["ekuitas"], "mmbr": b["mmbr"], "C1": c1, "C2": c2,
                       "rasio_megathrust_normal": mn, "rasio_megathrust_2026": m26, "lolos_C3": mn >= 1.0,
                       "kebutuhan_komitmen_megathrust": [max(b["mmbr"] * (1 - x), 0.0) for x in mega(kode, s)]}
        print(f"{nama:17s} s={s:.3f} K={K:4.0f} eku={b['ekuitas']:5.1f} C1={c1['pelanggaran']:4d} C2={c2['pelanggaran']:4d} "
              f"mega={100*mn:6.1f}%/{100*m26:6.1f}% cair={100*c1['peluang_cair']:.2f}% butuh={hasil[nama]['kebutuhan_komitmen_megathrust']}")

    # ---------------- waktu kejadian: L* menurut bulan (laba berjalan terkumpul merata)
    def L_kritis_waktu(kode, s, t, K=0.0):
        b = M.neraca_awal(kode, s)

        def R_pada(L):
            r = M.rasio_skenario(kode, ST, s, L / tsi)
            U_I = r["laba_sebelum_pajak"] + L + r["biaya_jual_paksa"]          # U + I setahun
            G = t * U_I - L - r["biaya_jual_paksa"]
            return (b["tingkat_solvabilitas"] + G - pajak * max(G, 0.0) + K) / b["mmbr"]
        return brentq(lambda L: R_pada(L) - 1.0, 0.0, 400.0) if R_pada(0.0) >= 1.0 else 0.0, R_pada
    waktu = {}
    for nama, (kode, s, K) in {"120": ("K70", 1.2, 0.0), "205": ("K70", s_inti, 0.0), "330": ("K70", 3.3, 0.0),
                               "motera_tetap": ("K70", s_inti, K_tetap)}.items():
        baris = []
        for t in mo["bulan_laporan"]:
            Lk, R_pada = L_kritis_waktu(kode, s, t, K)
            baris.append({"porsi_tahun": t, "kerugian_kritis": Lk, "rasio_banjir": R_pada(L_mega(ST) * 0 + pt["skenario_banjir"]["klaim_properti_triliun"]["nilai"] /
                                                                                         pt["skenario_banjir"]["premi_langsung_harta_benda_triliun"]["nilai"] * 100.0),
                          "rasio_megathrust": R_pada(L_mega(ST))})
        waktu[nama] = baris
    # komitmen agar megathrust di awal tahun tetap >= 100% pada rasio inti
    b = M.neraca_awal("K70", s_inti)
    _, R0 = L_kritis_waktu("K70", s_inti, 0.0)
    komitmen_awal_tahun = max(b["mmbr"] * (1.0 - R0(L_mega(ST))), 0.0)
    print("L* menurut waktu:", {k: [round(x["kerugian_kritis"], 1) for x in v] for k, v in waktu.items()}, "komitmen awal tahun", round(komitmen_awal_tahun, 1))

    # ---------------- opsi bila berdiri sendiri (rasio awal 120%, kecuali disebut lain)
    op = mo["opsi"]
    prem_gempa_zona = tsi * pt["bencana"]["tarif_gempa_per_mil"]["nilai"] / 1000.0 * json.loads((ms.DIR_BENCANA / "04_meta.json").read_text(encoding="utf-8"))["porsi_eksposur_zona_inti"]
    dU4 = op["O4_kenaikan_tarif_zona"] * prem_gempa_zona * (1 - uw["komisi"]["nilai"])
    lr4 = uw["rasio_klaim_non_bencana"]["rata"] - dU4 / 100.0                  # tambahan pendapatan dimasukkan lewat klaim yang lebih rendah
    opsi = {
        "O0": {"nama": "Status quo", "c1": simulasi("K70", 1.2, 0, "campuran"), "mega": mega("K70", 1.2)},
        "O1": {"nama": "Tambah modal disetor ke 330%", "c1": simulasi("K70", 3.3, 0, "campuran"), "mega": mega("K70", 3.3)},
        "O2": {"nama": "Sistem peringatan dini tiga lapis", "c1": simulasi("K70", 1.2, 0, "campuran"), "mega": mega("K70", 1.2)},
        "O3": {"nama": "Polis gempa berlapis untuk risiko besar di zona inti", "c1": simulasi("K70", 1.2, 0, "campuran", st=op["O3_proksi"]),
               "mega": mega("K70", 1.2, st=op["O3_proksi"]), "L_mega": L_mega(op["O3_proksi"])},
        "O4": {"nama": "Re-pricing tarif gempa zona inti", "c1": simulasi("K70", 1.2, 0, "campuran", rasio_klaim=lr4), "mega": mega("K70", 1.2, dU=dU4), "tambahan_premi_bersih": dU4},
        "O5": {"nama": "MOTERA", "c1": hasil["motera_tetap"]["C1"], "mega": [hasil["motera_tetap"]["rasio_megathrust_normal"], hasil["motera_tetap"]["rasio_megathrust_2026"]]},
        "O6": {"nama": "Konservatif 80/20 dengan repo SBN", "c1": simulasi(op["O6_profil"], 1.2, 0, "campuran"), "mega": mega(op["O6_profil"], 1.2)},
        "O7": {"nama": "Obligasi katastrofe", "c1": None, "mega": None},
    }
    opsi["O3"]["premi_dilepas"] = float(M.jalankan("K70", op["O3_proksi"], 1.2)["premi_dilepas"])

    # ---------------- biaya bersih tahunan, per 100 premi
    friksi = k_modal - hasil["status_quo"]["C1"]["imbal_hasil"] * (1 - pajak)          # biaya ekuitas dikurangi imbal hasil setelah pajak
    friksi_luar = k_modal - hasil["status_quo"]["C1"]["imbal_hasil"]                    # jaminan SBN di tangan pemegang saham
    ops = mo["biaya_operasional_miliar"]["nilai"] / skala
    eku0 = hasil["status_quo"]["ekuitas"]

    def biaya_modal(nama):
        return (hasil[nama]["ekuitas"] - eku0) * friksi
    harga_komitmen = hasil["motera_tetap"]["C1"]["peluang_cair"] * K_tetap                 # kerugian harapan pemegang saham bila dana tidak kembali
    biaya = {
        "modal_330": {"modal": biaya_modal("modal_330"), "komitmen": 0.0, "operasional": 0.0},
        "modal_setara": {"modal": biaya_modal("modal_setara"), "komitmen": 0.0, "operasional": 0.0},
        "motera_tetap": {"modal": biaya_modal("motera_tetap"), "komitmen_tanpa_jaminan": harga_komitmen,
                         "komitmen_dijamin_penuh": harga_komitmen + K_tetap * friksi_luar, "operasional": ops},
    }
    for k, x in biaya.items():
        if k == "motera_tetap":
            x["bersih"] = [x["modal"] + x["komitmen_tanpa_jaminan"] + ops, x["modal"] + x["komitmen_dijamin_penuh"] + ops]
        else:
            x["bersih"] = [x["modal"], x["modal"]]
        x["rupiah_miliar"] = [skala * y for y in x["bersih"]]
    print("biaya:", {k: [round(y, 2) for y in v["bersih"]] for k, v in biaya.items()}, "friksi", round(friksi, 4), round(friksi_luar, 4))

    # ---------------- matriks penilaian: dampak dan biaya dari angka, sisanya penilaian penulis
    def skor_dampak(o):
        if o["c1"] is None:
            return 4                                                   # O7: bila berhasil diterbitkan (asumsi)
        lolos = o["c1"]["pelanggaran"] <= batas
        if lolos and o["mega"][1] >= 1.0:
            return 5
        if lolos and o["mega"][0] >= 1.0:
            return 4
        if lolos:
            return 3
        return 2 if o["c1"]["peluang"] <= 0.8 * opsi["O0"]["c1"]["peluang"] else 1

    def skor_biaya(c):
        if c is None:
            return 1
        c = float(np.mean(c))
        return 5 if c <= 0 else 4 if c <= 2 else 3 if c <= 3 else 2 if c <= 4 else 1
    t_hasil = json.loads((AKAR / "4_simulasi_terpadu" / "keluaran" / "hasil_terpadu.json").read_text(encoding="utf-8"))
    ek_radar = json.loads((DIR_KELUAR / "radar_tangga.json").read_text(encoding="utf-8"))["ekonomi"]
    biaya_radar = ek_radar["biaya_radar_tahunan_miliar"] / skala                       # biaya tahunan sistem pemantauan (Rev. 3)
    laba_dilepas_O3 = t_hasil["soal2"][op["O3_proksi"]]["laba_dilepas"]                # laba harapan yang ikut dilepas bersama lapis atas
    opsi["O3"]["laba_dilepas"] = laba_dilepas_O3
    biaya_opsi = {"O1": biaya["modal_330"]["bersih"], "O2": [biaya_radar, biaya_radar], "O3": [laba_dilepas_O3, laba_dilepas_O3],
                  "O4": [-dU4, -dU4], "O5": biaya["motera_tetap"]["bersih"],
                  "O6": [-(opsi["O6"]["c1"]["imbal_hasil"] - opsi["O0"]["c1"]["imbal_hasil"]) * M.neraca_awal("K80", 1.2)["investasi"]] * 2, "O7": None}
    # cakupan, regulasi, operasional, inovasi: penilaian penulis (lihat rubrik di naskah)
    nilai_lain = {"O1": (5, 5, 3, 1), "O2": (3, 5, 4, 4), "O3": (2, 3, 2, 4), "O4": (1, 3, 3, 1), "O5": (5, 4, 4, 4), "O6": (2, 5, 5, 2), "O7": (2, 1, 1, 5)}
    skema = {"utama": (0.30, 0.15, 0.20, 0.15, 0.10, 0.10), "sama": (1 / 6,) * 6, "biaya": (0.20, 0.10, 0.35, 0.15, 0.10, 0.10)}
    penilaian = {}
    for k in ("O1", "O2", "O3", "O4", "O5", "O6", "O7"):
        sk_ = [skor_dampak(opsi[k]), nilai_lain[k][0], skor_biaya(biaya_opsi[k]), nilai_lain[k][1], nilai_lain[k][2], nilai_lain[k][3]]
        penilaian[k] = {"skor": sk_, "nilai": {nm: float(np.dot(w, sk_)) for nm, w in skema.items()}, "biaya": biaya_opsi[k]}
    for nm in skema:
        urut = sorted(penilaian, key=lambda k: -penilaian[k]["nilai"][nm])
        print("peringkat", nm, [(k, round(penilaian[k]["nilai"][nm], 2)) for k in urut])

    # ---------------- Rev. 6: komitmen bulanan yang memulihkan rasio ke 120% setelah megathrust pada bulan mana pun
    r6 = mo["rev6"]
    tgt = r6["target_pemulihan"]["nilai"]
    bulan = [m_ / 12.0 for m_ in range(12)] + [1.0]                                 # awal Januari ... awal Desember, akhir Desember

    def posisi_setelah_mega(kode, s, t, imbal):
        """Tingkat solvabilitas dan MMBR bila megathrust terjadi pada porsi tahun t (laba berjalan terkumpul merata)."""
        b = M.neraca_awal(kode, s)
        r = M.rasio_skenario(kode, ST, s, L_mega(ST) / tsi, imbal=imbal)
        U_I = r["laba_sebelum_pajak"] + L_mega(ST) + r["biaya_jual_paksa"]
        G = t * U_I - L_mega(ST) - r["biaya_jual_paksa"]
        return b["tingkat_solvabilitas"] + G - pajak * max(G, 0.0), b["mmbr"]

    def jadwal(kode, s):
        out = []
        for t in bulan:
            butuh = []
            for im in (None, imbal26(kode)):
                ts, mm = posisi_setelah_mega(kode, s, t, im)
                butuh.append(max(tgt * mm - ts, 0.0))
            out.append({"porsi_tahun": t, "butuh_normal": butuh[0], "butuh_2026": butuh[1], "komitmen": float(np.ceil(max(butuh)))})
        return out

    def rasio_waktu(kode, s, jdw):
        """Rasio setelah megathrust pada tiap bulan dengan komitmen bulan itu (pasar normal dan 2026)."""
        res = []
        for t, j in zip(bulan, jdw):
            for nm_, im in (("normal", None), ("2026", imbal26(kode))):
                ts, mm = posisi_setelah_mega(kode, s, t, im)
                res.append({"porsi_tahun": t, "pasar": nm_, "tanpa": ts / mm, "dengan": (ts + j["komitmen"]) / mm})
        return res
    jdw_t, jdw_a = jadwal("K70", s_inti), jadwal("K70", 1.2)
    K_akhir_t, K_akhir_a = jdw_t[-1]["komitmen"], jdw_a[-1]["komitmen"]
    K_maks_t, K_maks_a = max(j["komitmen"] for j in jdw_t), max(j["komitmen"] for j in jdw_a)
    K_rata_t = float(np.mean([j["komitmen"] for j in jdw_t[:12]]))                      # rata-rata komitmen yang berlaku sepanjang 12 bulan
    K_rata_a = float(np.mean([j["komitmen"] for j in jdw_a[:12]]))
    s_setara_penuh = brentq(lambda s: M.neraca_awal("K70", s)["ekuitas"] - (eku_inti + K_maks_t), 2.0, 9.0)
    s_setara_akhir = brentq(lambda s: M.neraca_awal("K70", s)["ekuitas"] - (eku_inti + K_akhir_t), 2.0, 9.0)
    konfig6 = {"status_quo": ("K70", 1.2, 0.0), "inti_saja": ("K70", s_inti, 0.0), "motera_peralihan": ("K70", 1.2, K_akhir_a),
               "motera": ("K70", s_inti, K_akhir_t), "modal_330": ("K70", 3.3, 0.0), "modal_setara_akhir": ("K70", s_setara_akhir, 0.0),
               "modal_setara_penuh": ("K70", s_setara_penuh, 0.0)}
    hasil6 = {}
    for nama, (kode, s, K) in konfig6.items():
        c1, c2 = simulasi(kode, s, K, "campuran"), simulasi(kode, s, K, "aulady")
        mn, m26 = mega(kode, s, K)
        jd = jdw_t if nama == "motera" else jdw_a if nama == "motera_peralihan" else [{"komitmen": 0.0}] * len(bulan)
        rw = rasio_waktu(kode, s, jd)
        b = M.neraca_awal(kode, s)
        hasil6[nama] = {"rasio_awal": s, "ekuitas": b["ekuitas"], "mmbr": b["mmbr"], "komitmen_akhir": K, "C1": c1, "C2": c2,
                        "rasio_megathrust_normal": mn, "rasio_megathrust_2026": m26,
                        "rasio_terendah_sepanjang_tahun": min(x["dengan"] for x in rw), "rasio_awal_tahun_2026": [x for x in rw if x["porsi_tahun"] == 0 and x["pasar"] == "2026"][0]["dengan"],
                        "rasio_waktu": rw}
        print(f"[rev6] {nama:19s} s={s:.3f} eku={b['ekuitas']:6.1f} K={K:4.0f} C1={c1['pelanggaran']:4d} C2={c2['pelanggaran']:4d} "
              f"mega={100*mn:6.1f}%/{100*m26:6.1f}% terendah={100*hasil6[nama]['rasio_terendah_sepanjang_tahun']:6.1f}% cair={100*c1['peluang_cair']:.2f}%")
    # biaya bersih tahunan: dua perspektif, uji biaya ekuitas, imbalan komitmen, dan porsi jaminan
    bi = p05["pasar"]["kondisi_awal"]["bi_rate"]["nilai"] if isinstance(p05["pasar"]["kondisi_awal"].get("bi_rate"), dict) else 0.0575
    i0 = hasil["status_quo"]["C1"]["imbal_hasil"]

    def biaya6(k):
        f_in, f_out = k - i0 * (1 - pajak), k - i0
        inti = (eku_inti - eku0) * f_in
        bunga = hasil6["motera"]["C1"]["rata_dicairkan"] * r6["bunga_pinjaman_per_bi_rate"]["nilai"] * bi
        fee = [r * K_rata_t for r in r6["imbalan_komitmen"]["nilai"]]
        return {"biaya_modal": k, "friksi_dalam": f_in, "friksi_luar": f_out,
                "perusahaan": {"modal_inti": inti, "imbalan_komitmen": fee, "bunga_saat_ditarik": bunga, "operasional": ops,
                               "jumlah": [inti + f + bunga + ops for f in fee]},
                "gabungan": {"modal_inti": inti, "jaminan_sbn": [0.0, 0.5 * K_rata_t * f_out, K_rata_t * f_out], "operasional": ops,
                             "jumlah": [inti + j + ops for j in (0.0, 0.5 * K_rata_t * f_out, K_rata_t * f_out)]},
                "modal_330": (hasil6["modal_330"]["ekuitas"] - eku0) * f_in,
                "modal_setara_akhir": (hasil6["modal_setara_akhir"]["ekuitas"] - eku0) * f_in,
                "modal_setara_penuh": (hasil6["modal_setara_penuh"]["ekuitas"] - eku0) * f_in}
    biaya_r6 = {str(k): biaya6(k) for k in r6["biaya_modal_uji"]}
    b13 = biaya_r6[str(k_modal)]
    print("[rev6] jadwal komitmen (tetap):", [j["komitmen"] for j in jdw_t], "rata", round(K_rata_t, 1), "| peralihan:", [j["komitmen"] for j in jdw_a])
    print("[rev6] biaya 13%: perusahaan", [round(x, 2) for x in b13["perusahaan"]["jumlah"]], "gabungan", [round(x, 2) for x in b13["gabungan"]["jumlah"]],
          "modal330", round(b13["modal_330"], 2), "setara_akhir", round(b13["modal_setara_akhir"], 2), "setara_penuh", round(b13["modal_setara_penuh"], 2))
    pjm = r6["potongan_jaminan_sbn"]["nilai"]
    prasyarat = {
        "efektivitas": {"C1": hasil6["motera"]["C1"]["pelanggaran"], "C2": hasil6["motera"]["C2"]["pelanggaran"], "batas": batas,
                        "rasio_megathrust": [hasil6["motera"]["rasio_megathrust_normal"], hasil6["motera"]["rasio_megathrust_2026"]],
                        "terpenuhi": bool(hasil6["motera"]["C1"]["pelanggaran"] <= batas and hasil6["motera"]["C2"]["pelanggaran"] <= batas
                                          and min(hasil6["motera"]["rasio_megathrust_normal"], hasil6["motera"]["rasio_megathrust_2026"]) >= tgt - 1e-9)},
        "ketepatan_waktu": {"rasio_terendah": hasil6["motera"]["rasio_terendah_sepanjang_tahun"],
                            "rasio_terendah_peralihan": hasil6["motera_peralihan"]["rasio_terendah_sepanjang_tahun"],
                            "terpenuhi": bool(min(hasil6["motera"]["rasio_terendah_sepanjang_tahun"], hasil6["motera_peralihan"]["rasio_terendah_sepanjang_tahun"]) >= 1.0)},
        "pendanaan": {"jaminan_sbn_minimum": K_maks_a / (1 - pjm), "jaminan_sbn_tetap": K_maks_t / (1 - pjm), "potongan": pjm},
    }
    print("[rev6] prasyarat:", {k: v.get("terpenuhi") for k, v in prasyarat.items()}, "jaminan", round(prasyarat["pendanaan"]["jaminan_sbn_minimum"], 1), round(prasyarat["pendanaan"]["jaminan_sbn_tetap"], 1))
    rev6 = {"jadwal_tetap": jdw_t, "jadwal_peralihan": jdw_a, "K_akhir": K_akhir_t, "K_maks": K_maks_t, "K_rata": K_rata_t,
            "K_akhir_peralihan": K_akhir_a, "K_maks_peralihan": K_maks_a, "K_rata_peralihan": K_rata_a,
            "konfigurasi": hasil6, "biaya": biaya_r6, "prasyarat": prasyarat, "bi_rate": bi, "target_pemulihan": tgt}

    keluar = {"meta": {"batas_pelanggaran": batas, "jumlah_tahun": N, "friksi_modal": friksi, "friksi_jaminan": friksi_luar, "biaya_modal": k_modal,
                       "skala_miliar_per_unit": skala, "rasio_setara": s_setara, "L_megathrust": L_mega(ST), "parameter": mo, "skema_bobot": skema},
              "konfigurasi": hasil, "waktu": waktu, "komitmen_awal_tahun": komitmen_awal_tahun, "opsi": opsi, "biaya": biaya, "penilaian": penilaian,
              "rev6": rev6}
    (DIR_KELUAR / "motera.json").write_text(json.dumps(keluar, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print("tersimpan:", DIR_KELUAR / "motera.json")


if __name__ == "__main__":
    main()
