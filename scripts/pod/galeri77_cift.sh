#!/usr/bin/env bash
# 77 cift galerisi, tek cift (Serdar 28 Eyl): krem kaynak kartlari cifte uyarlanir (galeri77_kur.py), sonra CL kesin
# paketiyle (86296c5) AYNI duvar hattindan gecer (galeri-duvar-paket.yml komutlari), QC PASS/FAIL. Etsy YOK, Drive YOK
# (yukleme workflow'da). Cikis 0 = QC PASS; paket OUT/paket (19 jpg + ALT_METIN.csv + SET.json), QC OUT/QC.txt.
# WP baskisi (BASKI_WARM_PARCHMENT.jpg) yoksa 05 ve 19 kurulmaz: 17 gorsel + QC (WP bekliyor); isimsiz WP kullanilmaz.
# Kullanim: galeri77_cift.sh CIFT KAYNAK_DIR OUT_DIR   (KAYNAK_DIR: KAPAK.jpg + BASKI_<RENK>.jpg; CL MB: $CL_MB)
set -euo pipefail
C=$1; Y=$2; O=$3
PY=${PY:-python3}; FD=${FD:-fonts}
CL_MB=${CL_MB:-_work/kaynak/CANCER_LIBRA/BASKI_MIDNIGHT_BLUE.jpg}
Z=${ZEMIN:-_work/duvar.png}
[ -f "$Z" ] || $PY scripts/pod/duvar_zemin.py data/pod/kapak_sahne_v9.png guclu "$Z" acik3
KR=$O/krem; P=$O/paket; rm -rf "$O"; mkdir -p "$KR" "$P"
t0=$(date +%s)
$PY scripts/pod/galeri77_kur.py "$C" "$Y" "$CL_MB" "$FD" "$KR" > "$O/KUR.txt"
read -r A B < <($PY -c "import json;j=json.load(open('$KR/KUR.json'));print(j['a'],j['b'])")
cp "$Y/KAPAK.jpg" "$P/01_kapak.jpg"
$PY scripts/pod/kart02_duvar_kur.py "$KR/02_format.jpg" "$Z" "$FD" "$P/02_format.jpg" "$A" "$B" > /dev/null
WP=1; [ -f "$Y/BASKI_WARM_PARCHMENT.jpg" ] || WP=0; BEK=19; [ $WP = 1 ] || BEK=17
for k in 03_konsept 04_kisisellestirme 05_renk_ve_dijital 07_cerceveler 08_boylar 12_zoom 13_kagit 14_surec; do
  [ $k = 05_renk_ve_dijital ] && [ $WP = 0 ] && continue
  R=""; [ $k = 07_cerceveler ] && R="1556,540,2150,1269"
  $PY scripts/pod/kart_duvar_genel.py "$KR/$k.jpg" "$Z" "$P/$k.jpg" "$R" > /dev/null
done
# 05: kucuk resim halkasindaki krem/acik JPEG halesi duvar zeminine (Serdar 1 Eki; QC 'serit 05' = 0)
[ $WP = 1 ] && $PY scripts/pod/galeri77_halka.py "$P/05_renk_ve_dijital.jpg" "$Z"
for kv in "06_hediye_sahne:145,440,2855,1866,30" "09_yatak_sahne:145,420,2855,1846,30" \
          "10_calisma_sahne:145,420,2855,1846,30" "11_yemek_sahne:145,420,2855,1846,30"; do
  k=${kv%%:*}; $PY scripts/pod/kart_duvar_genel.py "$KR/$k.jpg" "$Z" "$P/$k.jpg" "${kv#*:}" > /dev/null
done
for kv in "15_renk_midnight_blue:Midnight Blue:MIDNIGHT_BLUE" "16_renk_deep_black:Deep Black:DEEP_BLACK" \
          "17_renk_pure_white:Pure White:PURE_WHITE" "18_renk_champagne_ivory:Champagne Ivory:CHAMPAGNE_IVORY" \
          "19_renk_warm_parchment:Warm Parchment:WARM_PARCHMENT"; do
  IFS=: read -r k ad r <<< "$kv"
  [ -f "$Y/BASKI_$r.jpg" ] || continue
  $PY scripts/pod/renk_varyasyon_kur.py "$Y/BASKI_$r.jpg" "$ad" "$FD/Montserrat[wght].ttf" "$KR/$k.jpg" > /dev/null        # krem referans (poster NCC)
  $PY scripts/pod/renk_varyasyon_kur.py "$Y/BASKI_$r.jpg" "$ad" "$FD/Montserrat[wght].ttf" "$P/$k.jpg" "$Z" > /dev/null
done
ARGS=""; for f in "$P"/[01]*.jpg; do k=$(basename "$f" .jpg); [ "$k" = 01_kapak ] && continue; ARGS="$ARGS $f $KR/$k.jpg"; done
set +e
$PY scripts/pod/duvar_qc.py "$Z" data/pod/kapak_sahne_v9.png $ARGS > "$O/QC.txt"; Q1=$?
$PY scripts/pod/metin_qc.py "$KR/METIN.json" >> "$O/QC.txt"; Q2=$?
$PY scripts/pod/galeri77_qc.py "$C" "$Y" "$KR" "$P" "$CL_MB" >> "$O/QC.txt"; Q3=$?
set -e
mkdir -p "$O/json"; mv "$P"/*.json "$O/json/" 2>/dev/null || true
$PY - "$C" "$A" "$B" "$P" <<'PYEOF'
import csv, json, os, sys
C, A, B, P = sys.argv[1:5]
rows = list(csv.reader(open('data/pod/cl_galeri_alt_metin.csv')))
with open(os.path.join(P, 'ALT_METIN.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    for r in rows:
        w.writerow([r[0], r[1].replace('Cancer and Libra', f'{A} and {B}')])
renk = {'15': 'Midnight Blue', '16': 'Deep Black', '17': 'Pure White', '18': 'Champagne Ivory', '19': 'Warm Parchment'}
g = [{'dosya': d, 'renk': renk.get(d[:2])} for d in sorted(x for x in os.listdir(P) if x.endswith('.jpg'))]
json.dump({'cift': C, 'gorseller': g, 'video': None}, open(os.path.join(P, 'SET.json'), 'w'), ensure_ascii=False, indent=1)
PYEOF
$PY scripts/pod/galeri_temas.py "$P" "$O/TEMAS_$C.jpg" "$FD/Montserrat[wght].ttf" > /dev/null
n=$(ls "$P"/*.jpg | wc -l)
ok=1; [ "$Q1" = 0 ] && [ "$Q2" = 0 ] && [ "$Q3" = 0 ] && [ "$n" = "$BEK" ] || ok=0
echo "$C: $n gorsel$([ $WP = 0 ] && echo ' (WP bekliyor: 05, 19 yok)') | duvar_qc $([ $Q1 = 0 ] && echo PASS || echo FAIL) | metin_qc $([ $Q2 = 0 ] && echo PASS || echo FAIL) | sembol_qc $([ $Q3 = 0 ] && echo PASS || echo FAIL) | $(( $(date +%s) - t0 ))s | $([ $ok = 1 ] && echo PASS || echo FAIL)" | tee -a "$O/QC.txt"
[ $ok = 1 ]
