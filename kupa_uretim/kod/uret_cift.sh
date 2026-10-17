#!/usr/bin/env bash
# Bir burc cifti icin kupa ilaninin tum galerisi + videosu (13 gorsel + 1 video + kontrol paftasi).
# Kullanim: bash kod/uret_cift.sh <KOD> <Burc1> <Burc2> <sembol_klasoru> <cikti_klasoru>
#   ornek:  bash kod/uret_cift.sh CANCER_LIBRA Cancer Libra sembol/CANCER_LIBRA cikti/CANCER_LIBRA
# Calisma klasoru: kupa_uretim/. Isimler: kapak Emily & James; kart 11 Mia & Leo / Maximilian & Josephine.
set -euo pipefail
KOD=$1; B1=$2; B2=$3; SEM=$4; OUT=$5
BURC="$(echo "$B1" | tr a-z A-Z) · $(echo "$B2" | tr a-z A-Z)"
PY="python3 -I"
mkdir -p "$OUT/baski" "$OUT/galeri" "$OUT/ara"
T0=$(date +%s); ADIM=0; TOPLAM=10
adim() { ADIM=$((ADIM+1)); local g=$(( $(date +%s) - T0 )); local k=0; [ $ADIM -gt 1 ] && k=$(( g * (TOPLAM - ADIM + 1) / (ADIM - 1) )); echo "[$ADIM/$TOPLAM %$((100*(ADIM-1)/TOPLAM))] $1  (gecen ${g}s, kalan ~${k}s)"; }
STIL=(01_Botanical 02_Gold 03_NazarBond 04_RoseRibbon 05_PromiseLine 06_AegeanTile 07_Mediterranean)

adim "baski dosyalari (7 stil, Emily & James)"
CIFT="{\"isim1\":\"Emily\",\"isim2\":\"James\",\"burc\":\"$BURC\"}" $PY kod/kupa_7stil.py "$SEM" font susleme "$OUT/baski" >/dev/null

adim "7 kapak"
for s in "${STIL[@]}"; do
  ORTU=(); [ "$s" = 06_AegeanTile ] && ORTU=(geo/ortu_06_AegeanTile.npy)
  $PY kod/kapak_canva.py sahne/kapak/sahne_$s.jpg "$OUT/baski/KUPA_${s}_baski_2700x1050.png" geo/kapak_$s.json "$OUT/ara/KAPAK_$s.jpg" "${ORTU[@]}" >/dev/null
done

adim "stil karti (galeri 2)"
$PY kod/kart_stiller.py "$OUT/ara" font "$BURC" "$OUT/ara/KART_02_STILLER.jpg" >/dev/null

adim "yakin plan + tek kupa (Rose Ribbon)"
R="$OUT/baski/KUPA_04_RoseRibbon_baski_2700x1050.png"
SABIT_YUKSEKLIK=1 $PY kod/kapak_canva.py sahne/yakin/yakin_04.jpg "$R" geo/yakin_04.json "$OUT/ara/YAKIN_04_RoseRibbon.jpg" >/dev/null
for y in on arka; do SABIT_YUKSEKLIK=1 $PY kod/kapak_canva.py sahne/tek/esit_04_$y.jpg "$R" geo/tek_04_$y.json "$OUT/ara/TEK_04_$y.jpg" >/dev/null; done

adim "kisisellestirme karti (galeri 10)"
$PY kod/kart_kisisel.py "$OUT/ara/TEK_04_on.jpg" "$OUT/ara/TEK_04_arka.jpg" font "$B1" "$B2" Emily James "A love worth protecting" "$OUT/ara/KART_10_KISISEL.jpg" >/dev/null

adim "kisa / uzun isim ve mesaj (galeri 11)"
for u in kisa uzun; do
  if [ $u = kisa ]; then I1=Mia; I2=Leo; M="Always"; else I1=Maximilian; I2=Josephine; M="Forever starts with you and me"; fi
  YALNIZ=04 MESAJ="$M" CIFT="{\"isim1\":\"$I1\",\"isim2\":\"$I2\",\"burc\":\"$BURC\"}" $PY kod/kupa_7stil.py "$SEM" font susleme "$OUT/ara/$u" >/dev/null
  for y in on arka; do SABIT_YUKSEKLIK=1 $PY kod/kapak_canva.py sahne/tek/esit_04_$y.jpg "$OUT/ara/$u/KUPA_04_RoseRibbon_baski_2700x1050.png" geo/tek_04_$y.json "$OUT/ara/${u}_$y.jpg" >/dev/null; done
done
$PY kod/kart_uzunluk.py "$OUT/ara/kisa_on.jpg" "$OUT/ara/uzun_on.jpg" "$OUT/ara/kisa_arka.jpg" "$OUT/ara/uzun_arka.jpg" font "$BURC" "$OUT/ara/KART_11_UZUNLUK.jpg" >/dev/null

adim "olcu ve bakim kartlari (galeri 12, 13)"
$PY kod/kart_olcu.py font "$BURC" 130,18,46 "$OUT/ara/KART_12_OLCU.jpg" >/dev/null
$PY kod/kart_bakim.py font "$BURC" 130,18,46 "$OUT/ara/KART_13_BAKIM.jpg" >/dev/null

adim "galeri sirasi (01-13)"
SIRA=(KAPAK_04_RoseRibbon KART_02_STILLER KAPAK_01_Botanical KAPAK_02_Gold KAPAK_03_NazarBond KAPAK_05_PromiseLine KAPAK_06_AegeanTile KAPAK_07_Mediterranean YAKIN_04_RoseRibbon KART_10_KISISEL KART_11_UZUNLUK KART_12_OLCU KART_13_BAKIM)
for i in "${!SIRA[@]}"; do cp "$OUT/ara/${SIRA[$i]}.jpg" "$OUT/galeri/$(printf %02d $((i+1)))_${SIRA[$i]}.jpg"; done

adim "video (Rose Ribbon)"
$PY kod/video_kupa.py sahne/kapak/sahne_04_RoseRibbon.jpg geo/kapak_04_RoseRibbon.json "$R" "$OUT/galeri/01_KAPAK_04_RoseRibbon.jpg" "$OUT/galeri/VIDEO_$KOD.mp4" | tail -1

adim "kontrol paftasi"
$PY - "$OUT/galeri" "$OUT/PAFTA_$KOD.jpg" "$BURC" <<'EOF'
import sys, glob, pathlib
from PIL import Image, ImageDraw, ImageFont
fs = sorted(glob.glob(sys.argv[1] + "/[01]*.jpg")); T, G = 640, 16
s = Image.new("RGB", (5 * T + 6 * G, 100 + 3 * (T + G) + G), (250, 248, 245))
d = ImageDraw.Draw(s); f = ImageFont.truetype("font/EBGaramond[wght].ttf", 52); f.set_variation_by_axes([600])
d.text((G, 22), sys.argv[3] + "  ·  13 gorsel (galeri sirasi)", font=f, fill=(40, 36, 34))
for i, p in enumerate(fs):
    s.paste(Image.open(p).convert("RGB").resize((T, T), Image.LANCZOS), (G + (i % 5) * (T + G), 100 + (i // 5) * (T + G)))
s.save(sys.argv[2], quality=88); print("pafta", len(fs), "gorsel")
EOF
echo "TAMAM $KOD  ($(( $(date +%s) - T0 ))s)  galeri: $OUT/galeri"
