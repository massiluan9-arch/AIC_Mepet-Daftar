#!/usr/bin/env bash
# Menjalankan rantai Python untuk satu salinan varian di lab dan mencatat kode keluar serta lama tiap langkah.
# Pemakaian: bash jalankan_varian.sh <nama varian> [lewati_excel]
# Rantai: jalankan_terpadu.py -> uji_terpadu.py -> rancang_solusi.py -> buat_excel.py -> hitung_ulang_excel.py
# Keluaran R (04, 05) harus sudah ada di 2_model_bencana/keluaran salinan itu.
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VARIAN="${1:?nama varian wajib diisi}"
LEWATI_EXCEL="${2:-}"
V="$LAB/$VARIAN/AIC_CASE/analisis"
M="$LAB/laporan/mentah"
[ -d "$V" ] || { echo "tidak ada: $V"; exit 2; }
mkdir -p "$M"
RINGKAS="$M/${VARIAN}_ringkas.txt"
: > "$RINGKAS"
jalan() {
  local nama="$1"; shift
  local t0; t0=$(date +%s)
  "$@" > "$M/${VARIAN}_${nama}.log" 2>&1
  local kode=$?
  local lama=$(( $(date +%s) - t0 ))
  echo "exit=$kode detik=$lama" >> "$M/${VARIAN}_${nama}.log"
  echo "$nama: exit=$kode detik=$lama" | tee -a "$RINGKAS"
}
cd "$V/4_simulasi_terpadu" || exit 2
jalan jalankan python kode/jalankan_terpadu.py
jalan uji python kode/uji_terpadu.py
cd "$V" || exit 2
jalan rancang python 5_solusi_motera/kode/rancang_solusi.py
if [ -z "$LEWATI_EXCEL" ]; then
  jalan buat_excel python 5_solusi_motera/kode/buat_excel.py
  jalan hitung_excel python 5_solusi_motera/kode/hitung_ulang_excel.py
fi
echo "uji_terpadu: $(grep -c '^LULUS' "$M/${VARIAN}_uji.log") lulus, $(grep -c '^GAGAL' "$M/${VARIAN}_uji.log") gagal" | tee -a "$RINGKAS"
head -n 1 "$M/${VARIAN}_rancang.log" | tee -a "$RINGKAS"
