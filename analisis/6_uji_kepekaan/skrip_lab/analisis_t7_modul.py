"""T7: ukuran tiap modul MMBR untuk soal 3 (peluang terjadi menurut beberapa definisi).

Pemakaian: python analisis_t7_modul.py <varian>
Keluaran: laporan/hasil/<varian>/t7_modul.csv dan t7_modul.json
"""
import sys

import numpy as np
import pandas as pd

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")


def main():
    varian = sys.argv[1]
    ctx = al.siapkan(varian)
    M, r, acuan = ctx["M"], ctx["rancangan"], ctx["acuan"]
    st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
    konfigurasi = [("acuan_standar_120", acuan, "S0_dasar", 1.2), ("solusi_terpilih", acuan, st_p, s_p),
                   ("moderat_M50_standar_120", "M50", "S0_dasar", 1.2), ("agresif_A30_standar_120", "A30", "S0_dasar", 1.2)]
    baris, ringkas = [], {}
    for nama, kode, st, s in konfigurasi:
        k = al.komponen(ctx, kode, st, s)
        mesin = M.jalankan(kode, st, s, rinci=True)
        assert np.allclose(k["R"], mesin["deret"]["R"]), "susunan ulang tidak sama dengan mesin"
        b = k["neraca"]
        mmbr, ekuitas, ts0, pajak = k["mmbr"], b["ekuitas"], k["ts0"], k["pajak"]
        gagal = k["R"] < 1.0
        matriks = np.column_stack([k["rugi"][m] for m in al.MODUL])
        pemicu = matriks[gagal].argmax(axis=1)
        ambang = {"0,5": 0.5, "1": 1.0, "2": 2.0, "penyangga_20persen_MMBR": 0.2 * mmbr, "5": 5.0, "10": 10.0, "ekuitas": ekuitas}

        def peluang_tanpa(tambah):
            G = k["G"] + tambah
            return float((((ts0 + G - pajak * np.maximum(G, 0.0)) / mmbr) < 1.0).mean())

        ringkas[nama] = {"profil": kode, "strategi": st, "target": s, "mmbr": mmbr, "ekuitas": ekuitas, "penyangga_20persen_MMBR": 0.2 * mmbr,
                         "peluang_di_bawah_100": float(gagal.mean()), "jumlah_tahun_pelanggaran": int(gagal.sum()),
                         "peluang_tanpa_bencana": peluang_tanpa(k["L"] + k["F"]),
                         "peluang_tanpa_rugi_teknis_non_bencana": peluang_tanpa(np.maximum(-k["teknis_tanpa_bencana"], 0.0)),
                         "peluang_rugi_teknis_non_bencana": float((k["teknis_tanpa_bencana"] < 0).mean()),
                         "peluang_ada_kerugian_bencana": float((k["L"] > 0).mean())}
        for i, m in enumerate(al.MODUL):
            x = k["rugi"][m]
            q = float(np.quantile(x, 0.995))
            e = mesin["modul"][m]
            assert abs(e["peluang_rugi"] - float((x > 1e-9).mean())) < 1e-12 and abs(e["rugi_var_99_5"] - q) < 1e-9
            d = {"varian": varian, "konfigurasi": nama, "profil": kode, "strategi": st, "target": s, "modul": m,
                 "beban_modal": b["modul"][m], "porsi_mmbr": b["porsi_modul"][m],
                 "peluang_rugi_positif": float((x > 1e-9).mean()), "peluang_melampaui_beban_modal": float((x > b["modul"][m]).mean()),
                 "rugi_rata": float(x.mean()), "rugi_var_99_5": q, "rugi_tvar_99_5": float(x[x >= q].mean()), "rugi_maks": float(x.max())}
            for label, t in ambang.items():
                d[f"peluang_lebih_{label}"] = float((x > t).mean())
            # Definisi seragam: simpangan merugikan terhadap nilai harapan komponen laba modul itu.
            h = k["hasil_modul"][m]
            simpang = h.mean() - h
            d["hasil_harapan"] = float(h.mean())
            d["simpangan_baku_hasil"] = float(h.std())
            for label, t in ambang.items():
                d[f"peluang_simpangan_lebih_{label}"] = float((simpang > t).mean())
            d["porsi_tahun_pelanggaran_rugi_terbesar"] = float((pemicu == i).mean()) if gagal.any() else 0.0
            d["rugi_rata_pada_tahun_pelanggaran"] = float(x[gagal].mean()) if gagal.any() else 0.0
            d["peluang_di_bawah_100_tanpa_modul"] = peluang_tanpa(x)
            d["penurunan_peluang_tanpa_modul"] = float(gagal.mean()) - d["peluang_di_bawah_100_tanpa_modul"]
            baris.append(d)
    t = pd.DataFrame(baris)
    t.to_csv(ctx["keluar"] / "t7_modul.csv", index=False)
    al.simpan_json(ctx["keluar"] / "t7_modul.json", ringkas)
    pd.set_option("display.width", 250)
    for nama in ringkas:
        x = ringkas[nama]
        print(f"\n[{varian}] {nama}: profil {x['profil']}, {x['strategi']}, target {x['target']:.2f}; MMBR {x['mmbr']:.2f}; ekuitas {x['ekuitas']:.2f}; "
              f"penyangga {x['penyangga_20persen_MMBR']:.2f}; P(R<100%) {100 * x['peluang_di_bawah_100']:.3f}% ({x['jumlah_tahun_pelanggaran']} tahun); "
              f"tanpa bencana {100 * x['peluang_tanpa_bencana']:.3f}%; tanpa rugi teknis non-bencana {100 * x['peluang_tanpa_rugi_teknis_non_bencana']:.3f}%")
        kol = ["modul", "beban_modal", "peluang_rugi_positif", "peluang_melampaui_beban_modal", "rugi_rata", "rugi_var_99_5", "rugi_tvar_99_5",
               "peluang_lebih_0,5", "peluang_lebih_1", "peluang_lebih_2", "peluang_lebih_penyangga_20persen_MMBR", "peluang_lebih_5", "peluang_lebih_10",
               "peluang_lebih_ekuitas", "porsi_tahun_pelanggaran_rugi_terbesar", "peluang_di_bawah_100_tanpa_modul"]
        print(t[t["konfigurasi"] == nama][kol].round(5).to_string(index=False))
        kol2 = ["modul", "hasil_harapan", "simpangan_baku_hasil"] + [f"peluang_simpangan_lebih_{a}" for a in ambang]
        print("  definisi seragam (simpangan merugikan terhadap harapan):")
        print(t[t["konfigurasi"] == nama][kol2].round(5).to_string(index=False))


if __name__ == "__main__":
    main()
