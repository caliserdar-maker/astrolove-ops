#!/usr/bin/env bash
# Bir ciftin ozgun sembol dosyalarini (ana, sol, sag) kupa-printful-sonuc dalindan yalniz OKUYARAK cikarir.
# Kullanim: bash sembol_al.sh <CIFT, ornek CANCER_LIBRA> <cikti_klasoru>
set -euo pipefail
CIFT="$1"; OUT="$2"
mkdir -p "$OUT"
git fetch -q origin kupa-printful-sonuc
for f in ana sol sag; do
  git show "origin/kupa-printful-sonuc:kupa_uretim/sembol/${CIFT}/${f}.png" > "$OUT/${f}.png"
done
echo "tamam $CIFT -> $OUT"
