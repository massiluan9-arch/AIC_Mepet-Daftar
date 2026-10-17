"""Tambalan Rev. 2 untuk 4_simulasi_terpadu/kode/uji_terpadu.py (dijalankan sekali)."""
import sys
from pathlib import Path

f = Path(sys.argv[1])
s = f.read_text(encoding="utf-8")
BARU = '''    # 11. Rev. 2: rumus pembayaran. Pembayaran per risiko paling besar sama dengan batas, jadi kerugian satu kejadian
    #     pada strategi berbatas seragam tidak boleh melampaui batas x eksposur, dan tidak melampaui polis standar.
    meta = json.loads((ms.DIR_BENCANA / "04_meta.json").read_text(encoding="utf-8"))
    cek("04_meta.json mencatat dasar batas = pembayaran maksimum", meta.get("dasar_batas") == "bayar", str(meta.get("dasar_batas")))
    ylt4 = pd.read_csv(ms.DIR_BENCANA / "04_ylt.csv.gz")
    batas = {"S4_batas10": 0.10, "S13_batas15": 0.15, "S3_batas20": 0.20, "S12_batas25": 0.25, "S11_batas30": 0.30,
             "S10_batas40": 0.40, "S9_batas50": 0.50}
    lebih, di_atas_dasar, terbesar = 0, 0, 0.0
    for kv in ms.KURVA_TUNGGAL:
        for st, u in batas.items():
            mk = ylt4[f"maks.{kv}.{st}"].to_numpy()
            lebih += int((mk > u * (1 + 1e-6)).sum())
            di_atas_dasar += int((mk > ylt4[f"maks.{kv}.S0_dasar"].to_numpy() * (1 + 1e-5) + 1e-12).sum())
            terbesar = max(terbesar, float((mk / u).max()))
    cek("kerugian satu kejadian tidak melampaui batas ganti rugi x eksposur (7 batas, 3 kurva)", lebih == 0,
        f"terbesar {terbesar:.3f} dari batas")
    cek("kerugian satu kejadian strategi berbatas tidak melampaui polis standar", di_atas_dasar == 0)
    cek("keluaran uji_rumus_bayar.R ada (uji unit rumus pembayaran dijalankan)", (ms.DIR_BENCANA / "uji_rumus_bayar_mc.csv").exists())

    # 12. Rev. 2: rancangan terpilih. Dilewati bila rancangan.json belum dibangun ulang untuk konfigurasi ini
    #     (jalankan rancang_solusi.py lalu ulangi uji ini).
    berkas_r = ms.DIR_TERPADU / "5_solusi_motera" / "keluaran" / "rancangan.json"
    rc = json.loads(berkas_r.read_text(encoding="utf-8")) if berkas_r.exists() else None
    aturan = pt["meta"].get("aturan_peluang", "titik")
    ambang = pt["meta"]["ambang_peluang"]
    if rc is None or rc["meta"].get("profil") != acuan or rc["meta"].get("aturan_peluang") != aturan or "C1" not in rc.get("terpilih", {}):
        print("DILEWATI  uji rancangan terpilih: rancangan.json belum sesuai konfigurasi; jalankan rancang_solusi.py lalu ulangi")
    else:
        t = rc["terpilih"]
        st_p, s_p = t["strategi"], t["target"]
        k_maks = ms.pelanggaran_terbanyak(ambang, M.n, pt["meta"].get("tingkat_selang", 0.95))
        batas_k = k_maks if aturan == "batas_atas" else int(ambang * M.n)
        hitung = lambda s, kv: int(round(M.jalankan(acuan, st_p, s, kurva=kv)["peluang_di_bawah_100"] * M.n))
        k1, k2 = hitung(s_p, "campuran"), hitung(s_p, "aulady")
        cek(f"rancangan terpilih lolos C1 menurut aturan {aturan}", k1 <= batas_k and k1 == t["C1"]["jumlah_pelanggaran"],
            f"{k1} pelanggaran, paling banyak {batas_k}")
        cek(f"rancangan terpilih lolos C2 menurut aturan {aturan}", k2 <= batas_k and k2 == t["C2"]["jumlah_pelanggaran"],
            f"{k2} pelanggaran, paling banyak {batas_k}")
        kunci = "selang_atas" if aturan == "batas_atas" else "peluang"
        cek(f"{kunci} C1 dan C2 pada rancangan terpilih tidak melebihi ambang", max(t["C1"][kunci], t["C2"][kunci]) <= ambang,
            f"{t['C1'][kunci]:.5f} dan {t['C2'][kunci]:.5f}")
        cek("rancangan terpilih lolos C3 (rasio setelah megathrust paling rendah 100%)", t["C3_rasio_setelah_megathrust"] >= 1.0,
            f"{t['C3_rasio_setelah_megathrust']:.4f}")
        cek("satu langkah kisi di bawah target terpilih gagal paling sedikit satu kendala",
            s_p <= 1.2 + 1e-9 or hitung(s_p - 0.05, "campuran") > batas_k or hitung(s_p - 0.05, "aulady") > batas_k
            or s_p - 0.05 < t["target_C3"] - 1e-9)
        cek("profil_acuan sama dengan profil menurut aturan kantong likuiditas", t["profil_menurut_kantong_likuiditas"] == acuan,
            f"acuan {acuan}; aturan {t['profil_menurut_kantong_likuiditas']}; cakupan "
            + ", ".join(f"{k} {v['cakupan']:.3f}" for k, v in t["kantong_likuiditas"].items()))

'''
rep = [
    ('    pe = [M.jalankan(acuan, "S0_dasar", 1.2, eksposur=e)["peluang_di_bawah_100"] for e in (100, 139.16, 188)]',
     '    rentang_E = pt["bencana"]["eksposur_per_premi"]["rentang"]\n'
     '    pe = [M.jalankan(acuan, "S0_dasar", 1.2, eksposur=e)["peluang_di_bawah_100"] for e in (rentang_E[0], E, rentang_E[1])]'),
    ('    cek("premi dilepas batas 20% = 30% premi gempa", abs(s3["premi_dilepas"] - 0.30 * q) < 1e-9, f"{s3[\'premi_dilepas\']:.4f}")',
     '    skala20 = pt["skala_premi_syarat"]["batas20"]["nilai"]\n'
     '    cek(f"premi dilepas batas 20% = {1 - skala20:.0%} premi gempa (skala dari YAML)", abs(s3["premi_dilepas"] - (1 - skala20) * q) < 1e-9,\n'
     '        f"{s3[\'premi_dilepas\']:.4f}")'),
]
for a, b in rep:
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
kunci = '    print(f"\\n{sum(HASIL)} dari {len(HASIL)} pemeriksaan lulus")'
assert s.count(kunci) == 1
s = s.replace(kunci, BARU + kunci)
f.write_text(s, encoding="utf-8")
print("uji_terpadu.py ditambal")
