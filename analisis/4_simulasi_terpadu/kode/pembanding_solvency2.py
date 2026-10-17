"""Pembanding luar: beban modal rumus standar Solvency II untuk buku yang sama.

Memakai pustaka rujukan solvency2-python (C:/Users/massi/ai-finance-tools/solvency2-python), bukan
perhitungan sendiri, untuk dua besaran:
  1. risiko premi dan cadangan non-jiwa, segmen 4 (kebakaran dan kerusakan harta benda);
  2. kerugian gempa bumi untuk wilayah di luar Lampiran XIII (berbasis premi bruto).
Hasilnya hanya pembanding skala terhadap modul risiko asuransi MMBR dan keluaran model bencana;
Solvency II tidak berlaku di Indonesia.

Pemakaian: python -I kode/pembanding_solvency2.py [jalur_repo]
Keluaran: keluaran/pembanding_solvency2.json
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DIR_F = Path(__file__).resolve().parents[1]
REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "ai-finance-tools" / "solvency2-python"
sys.path.insert(0, str(REPO / "src"))

import solvency2 as s2                      # noqa: E402
from solvency2 import nonlife               # noqa: E402

KONTEKS = s2.Context("2025-01-31", "2026-09-23", "EUR", "EU-S2-DOCUMENTS-2024-2025-v0.1")
PREMI = 100.0            # volume premi: premi dicatat lini harta benda setahun
CADANGAN_KLAIM = 40.52   # volume cadangan: cadangan klaim per 100 premi (analisis/3_investasi_mmbr/parameter/neraca_dasar.yaml)


def nilai(hasil):
    """Fungsi pustaka mengembalikan objek hasil atau pasangan (nilai, rincian)."""
    if isinstance(hasil, tuple):
        return float(hasil[0]), hasil[1]
    return float(hasil.value), getattr(hasil, "details", {})


def main():
    kosong = {"premium_volume": 0.0, "reserve_volume": 0.0, "geographic_diversification": 1.0}
    segmen = {str(i): dict(kosong) for i in range(1, 13)}
    segmen["4"] = {"premium_volume": PREMI, "reserve_volume": CADANGAN_KLAIM, "geographic_diversification": 1.0}
    premi_cadangan, rinci_pc = nilai(nonlife.premium_reserve_risk(segmen, context=KONTEKS))
    gempa, rinci_g = nilai(nonlife.natural_cat_other_loss(
        "earthquake", PREMI, 1.0,
        qualification_reference="Pembanding akademik: seluruh premi harta benda di satu wilayah (Indonesia), DIV = 1",
        context=KONTEKS))
    terpadu = json.loads((DIR_F / "keluaran" / "hasil_terpadu.json").read_text(encoding="utf-8"))
    acuan = terpadu["soal2"]["S0_dasar"]
    modul = terpadu["soal3"][f"{terpadu['meta']['profil_acuan']}_S0_dasar"]["modul"]["asuransi"]["beban_modal"]
    out = {
        "sumber": "solvency2-python, profil EU-S2-DOCUMENTS-2024-2025-v0.1 (Delegated Regulation (EU) 2015/35)",
        "satuan": "per 100 premi dicatat",
        "solvency2_premi_dan_cadangan": premi_cadangan,
        "solvency2_gempa_wilayah_lain": gempa,
        "solvency2_faktor_gempa_efektif": rinci_g.get("effective_factor"),
        "solvency2_gabungan_akar_kuadrat": (premi_cadangan ** 2 + gempa ** 2 + 2 * 0.25 * premi_cadangan * gempa) ** 0.5,
        "mmbr_modul_asuransi": modul,
        "model_var_99_5_kerugian_bencana_setahun": acuan["L_var_99_5"],
        "model_var_99_5_klaim_satu_kejadian": acuan["klaim_kejadian_var_99_5"],
        "catatan": "Gabungan memakai korelasi 0,25 antara risiko premi-cadangan dan risiko katastrofe non-jiwa "
                   "(Delegated Regulation Pasal 114). Volume cadangan memakai cadangan klaim bruto.",
        "rincian_premi_cadangan": {k: v for k, v in rinci_pc.items() if isinstance(v, (int, float, str))},
    }
    (DIR_F / "keluaran" / "pembanding_solvency2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for k in ("solvency2_premi_dan_cadangan", "solvency2_gempa_wilayah_lain", "solvency2_faktor_gempa_efektif",
              "solvency2_gabungan_akar_kuadrat", "mmbr_modul_asuransi", "model_var_99_5_kerugian_bencana_setahun"):
        print(f"{k}: {out[k]}")


if __name__ == "__main__":
    main()
