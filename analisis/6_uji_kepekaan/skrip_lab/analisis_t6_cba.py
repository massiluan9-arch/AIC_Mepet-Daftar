"""T6: analisis biaya-manfaat disusun ulang seperti lembar Biaya_Manfaat, lalu dipecah menurut perspektif.

Pemakaian: python analisis_t6_cba.py <varian>
Keluaran: laporan/hasil/<varian>/t6_cba.json
"""
import json
import sys

import numpy as np
from scipy.optimize import brentq

import alat_lab as al

sys.stdout.reconfigure(encoding="utf-8")


def npv(arus, k):
    return float(sum(a / (1 + k) ** t for t, a in enumerate(arus)))


def impas(arus):
    """Tingkat diskonto yang membuat NPV nol (None bila tidak ada pergantian tanda pada 0,1% sampai 100%)."""
    f = lambda k: npv(arus, k)
    if f(0.001) * f(1.0) > 0:
        return None
    return float(brentq(f, 0.001, 1.0))


def main():
    varian = sys.argv[1]
    ctx = al.siapkan(varian)
    M, pt, ps, r, acuan = ctx["M"], ctx["pt"], ctx["ps"], ctx["rancangan"], ctx["acuan"]
    p = r["perbandingan"]
    k, n = ps["biaya_modal"]["nilai"], ps["horizon_tahun"]
    skala = ps["skala_rupiah"]["premi_harta_benda_miliar"] / 100.0
    awal = sum(v["nilai"] for v in ps["biaya_implementasi"]["awal"].values())
    tahunan = sum(v["nilai"] for v in ps["biaya_implementasi"]["tahunan"].values())
    st_p, s_p = r["terpilih"]["strategi"], r["terpilih"]["target"]
    hasil = {"varian": varian, "profil_acuan": acuan, "strategi": st_p, "target": s_p, "biaya_modal": k, "horizon": n,
             "skala_miliar_per_satuan": skala, "biaya_awal": awal, "biaya_tahunan": tahunan}
    if "modal_saja" not in p:
        hasil["catatan"] = "jalan modal saja tidak tersedia (tidak ada target yang lolos tiga kendala)"
        al.simpan_json(ctx["keluar"] / "t6_cba.json", hasil)
        print(json.dumps(hasil, indent=1, ensure_ascii=False))
        return
    dE = (p["modal_saja"]["ekuitas"] - p["terpilih"]["ekuitas"]) * skala
    dL = (p["modal_saja"]["laba_bersih_rata"] - p["terpilih"]["laba_bersih_rata"]) * skala
    dD = (p["modal_saja"]["defisit_harapan"] - p["terpilih"]["defisit_harapan"]) * skala

    def arus(pakai_defisit, kali=1.0, de=dE, dl=dL, dd=dD):
        t = -(dl - pakai_defisit * dd + tahunan * kali)
        return [de - awal * kali] + [t] * (n - 1) + [t - de]

    hasil["masukan"] = {"target_modal_saja": p["modal_saja"]["target"], "ekuitas_modal_saja": p["modal_saja"]["ekuitas"], "ekuitas_terpilih": p["terpilih"]["ekuitas"],
                        "ekuitas_dihemat_miliar": dE, "laba_dilepas_miliar": dL, "defisit_dihindari_miliar": dD,
                        "peluang_modal_saja": p["modal_saja"]["peluang_di_bawah_100"], "peluang_terpilih": p["terpilih"]["peluang_di_bawah_100"]}
    hasil["arus_kas_buku_kerja"] = arus(1)
    hasil["npv"] = {
        "b_diperluas_dengan_defisit (buku kerja)": npv(arus(1), k),
        "a_perspektif_perusahaan_tanpa_defisit": npv(arus(0), k),
        "c_biaya_x2_diperluas": npv(arus(1, 2.0), k),
        "c_biaya_x2_perusahaan": npv(arus(0, 2.0), k),
        "tanpa_biaya_pelaksanaan_perusahaan": npv(arus(0, 0.0), k),
    }
    hasil["titik_impas_biaya_modal"] = {"d_diperluas": impas(arus(1)), "d_perusahaan": impas(arus(0)),
                                        "diperluas_biaya_x2": impas(arus(1, 2.0)), "perusahaan_biaya_x2": impas(arus(0, 2.0))}
    hasil["npv_per_biaya_modal"] = {f"{kk:.2f}": {"diperluas": npv(arus(1), kk), "perusahaan": npv(arus(0), kk)} for kk in (0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16)}
    hasil["nilai_kini_manfaat_buku_kerja"] = dE + sum(dD / (1 + k) ** t for t in range(1, n + 1))
    hasil["nilai_kini_biaya_buku_kerja"] = awal + sum((dL + tahunan) / (1 + k) ** t for t in range(1, n + 1)) + dE / (1 + k) ** n

    # Cocokkan dengan hasil_excel.json bila ada di salinan ini.
    bx = ctx["akar"] / "5_solusi_motera" / "keluaran" / "hasil_excel.json"
    if bx.exists():
        x = json.loads(bx.read_text(encoding="utf-8"))
        hasil["cocok_excel"] = {"npv_excel": x["npv_miliar"], "selisih_npv": x["npv_miliar"] - hasil["npv"]["b_diperluas_dengan_defisit (buku kerja)"],
                                "impas_excel": x["biaya_setara_modal"], "selisih_impas": x["biaya_setara_modal"] - (hasil["titik_impas_biaya_modal"]["d_diperluas"] or float("nan")),
                                "catatan": "hasil_excel.json salinan ini hanya sah bila buat_excel dan hitung_ulang_excel sudah dijalankan untuk varian ini"}

    # (e) kerugian yang berpindah ke pemegang polis karena batas: L_standar - L_solusi pada tahun yang sama
    E = pt["bencana"]["eksposur_per_premi"]["nilai"]
    tsi = 100.0 * E
    ylt = M.ylt_untuk("campuran")
    L0, Ls = tsi * ylt["S0_dasar"][0], tsi * ylt[st_p][0]
    geser = L0 - Ls
    q0 = np.quantile(L0, 0.995)
    ekor = L0 >= q0
    tahan = float(M.strategi.loc[st_p, "eksposur_ditahan"])
    premi_dilepas = p["terpilih"]["premi_dilepas"]
    hasil["kerugian_berpindah_ke_pemegang_polis"] = {
        "eksposur_ditahan_strategi": tahan,
        "catatan": "eksposur ditahan 1 berarti seluruh selisih adalah kerugian di atas batas ganti rugi yang kini ditanggung pemegang polis"
                   if abs(tahan - 1) < 1e-12 else "strategi juga melepas eksposur; selisih memuat kerugian polis yang tidak lagi ditutup",
        "rata_per_tahun": float(geser.mean()), "rata_per_tahun_miliar": float(geser.mean() * skala),
        "rata_pada_0_5persen_tahun_terburuk": float(geser[ekor].mean()), "rata_pada_0_5persen_tahun_terburuk_miliar": float(geser[ekor].mean() * skala),
        "tvar_standar": float(L0[ekor].mean()), "rata_solusi_pada_tahun_ekor_standar": float(Ls[ekor].mean()),
        "porsi_kerugian_ekor_yang_berpindah": float(geser[ekor].mean() / L0[ekor].mean()),
        "porsi_kerugian_rata_yang_berpindah": float(geser.mean() / L0.mean()),
        "selisih_tidak_negatif_di_semua_tahun": bool((geser >= -1e-9).all()),
        "premi_dilepas": premi_dilepas, "premi_dilepas_miliar": premi_dilepas * skala,
        "rasio_kerugian_berpindah_terhadap_premi_dilepas": float(geser.mean() / premi_dilepas) if premi_dilepas > 0 else None}

    # Pencatatan ganda: laba harapan sudah memuat seluruh kerugian bencana, termasuk bagian yang tidak terbayar saat TS < 0.
    def urai(st, s):
        x = M.jalankan(acuan, st, s, rinci=True)
        d = x["deret"]
        ts1 = x["tingkat_solvabilitas"] + d["G"] - ps_pajak * np.maximum(d["G"], 0.0)
        return {"laba_bersih_rata": x["laba_bersih_rata"], "defisit_harapan": float(np.maximum(-ts1, 0).mean()),
                "L_rata": float(d["L"].mean()), "L_rata_pada_tahun_defisit": float(d["L"][ts1 < 0].mean()) if (ts1 < 0).any() else 0.0,
                "peluang_TS_negatif": float((ts1 < 0).mean()),
                "laba_pemegang_saham_tanggung_jawab_terbatas": float((x["laba_bersih_rata"]) + np.maximum(-ts1, 0).mean())}
    ps_pajak = pt["underwriting"]["pajak"]["nilai"]
    u_m, u_t = urai("S0_dasar", p["modal_saja"]["target"]), urai(st_p, s_p)
    hasil["pencatatan_ganda"] = {
        "modal_saja": u_m, "terpilih": u_t,
        "selisih_L_rata_miliar": (u_m["L_rata"] - u_t["L_rata"]) * skala,
        "defisit_dihindari_miliar": dD,
        "uraian": "Laba bersih harapan dihitung seolah pemegang saham membayar seluruh klaim, termasuk pada tahun TS akhir negatif. "
                  "Turunnya kerugian bencana karena batas sudah menaikkan laba solusi sebesar selisih L rata-rata (sebelum pajak). "
                  "Defisit yang dihindari adalah bagian dari kerugian yang sama pada tahun bangkrut, jadi menambahkannya lagi sebagai manfaat "
                  "menghitung bagian itu dua kali, kecuali dimaknai sebagai kerugian pihak lain (pemegang polis) dalam analisis sosial."}

    al.simpan_json(ctx["keluar"] / "t6_cba.json", hasil)
    print(f"[{varian}] {st_p} pada {s_p:.2f} lawan modal saja pada {p['modal_saja']['target']:.2f} (profil {acuan})")
    print(f"  dE {dE:.2f}; dLaba {dL:.3f}; dDefisit {dD:.3f}; biaya awal {awal}; tahunan {tahunan}")
    for a, b in hasil["npv"].items():
        print(f"  NPV {a}: {b:.3f}")
    print("  titik impas:", {a: (None if b is None else round(100 * b, 3)) for a, b in hasil["titik_impas_biaya_modal"].items()})
    g = hasil["kerugian_berpindah_ke_pemegang_polis"]
    print(f"  kerugian berpindah: rata {g['rata_per_tahun']:.3f} per 100 premi (Rp{g['rata_per_tahun_miliar']:.1f} miliar); ekor 0,5% {g['rata_pada_0_5persen_tahun_terburuk']:.1f} "
          f"(Rp{g['rata_pada_0_5persen_tahun_terburuk_miliar']:.0f} miliar); porsi ekor {100 * g['porsi_kerugian_ekor_yang_berpindah']:.1f}%; premi dilepas {g['premi_dilepas']:.3f}")
    if "cocok_excel" in hasil:
        print("  cocok Excel:", hasil["cocok_excel"])


if __name__ == "__main__":
    main()
