#!/bin/bash
# Sade kupa 12 burc (Serdar 31 Eki "ok" renk onerisi 7b): kapak (Orange stil), 8 stil, 6 sn video. Var olan cikti atlanir.
# Kullanim: bash uret12.sh <BURC> [<BURC> ...]   (BURC buyuk harf, ornek CANCER)
set -e
R=/home/claude/caliserdar-maker/astrolove-ops; K=$R/kupa_orchard; KE=$K/kapak_el
export GOLGE_US=1.0 PARLA=0.7 ALT_ORAN=0.55 IZ_ORAN=0.05 ALT_AGIRLIK=600
STIL='07 ORANGE orange 30,92,52 Orange_Blossom 1.6
08 FIG fig 82,28,74 Purple_Fig 1.6
09 OLIVE olive 78,84,30 Olive_Breeze 1.6
10 POMEGRANATE pomegranate 132,20,36 Pomegranate_Bloom 1.6
11 ALMOND almond 150,78,96 Almond_Blossom 2.4
12 LEMON lemon 150,112,10 Lemon_Grove 1.6
13 GRAPE grape 46,38,110 Blue_Grape 1.6
14 LOQUAT loquat 176,96,20 Golden_Loquat 1.6'
for B in "$@"; do
  b=$(echo ${B:0:1}${B:1} | sed 's/./\L&/2g')   # Cancer
  mkdir -p $B/is; cd $B
  [ -s is/glif.png ] || git -C $R show refs/kapak78/sembol:kupa_uretim/sembol/${B}_${B}/sol.png > is/glif.png
  while read no S s rgb ad gg; do
    [ -s SADE_STIL_${B}_${no}_${S}.jpg ] && continue
    python3 -I $K/kod/baski_sade3.py is/glif.png $K/varlik/dal_sade/$s.jpg EMILY "My favorite place is with you" $rgb is/b_$s >/dev/null
    python3 -I $KE/kod/kapak_canva4.py $KE/sahne/stil/STIL_${S}_uzun.png is/b_${s}_baski_11oz.png $KE/sahne/geo_A3b.json is/k_$s.png >/dev/null
    ALT_REF='PERSONALIZED GIFT MUG' GOLGE_GUC=$gg python3 -I $KE/kod/baslik2.py is/k_$s.png SADE_STIL_${B}_${no}_${S}.jpg $b - 1500 535 185 252,248,240 "${ad//_/ }" 1 >/dev/null
  done <<< "$STIL"
  if [ ! -s SADE_KAPAK_${B}.jpg ]; then
    python3 -I $KE/kod/kapak_canva4.py $KE/sahne/A3_uzun2.png is/b_orange_baski_11oz.png $KE/sahne/geo_A3b.json is/k_kapak.png >/dev/null
    GOLGE_GUC=1.6 python3 -I $KE/kod/baslik2.py is/k_kapak.png SADE_KAPAK_${B}.jpg $b - 1500 535 185 252,248,240 "PERSONALIZED GIFT MUG" 1 >/dev/null
  fi
  [ -s SADE_VIDEO_${B}.mp4 ] || python3 -I $KE/kod/video_sade.py is/b_orange_baski_11oz.png SADE_KAPAK_${B}.jpg SADE_VIDEO_${B}.mp4 | grep -E "HATA|tamam|toz"
  echo "$B tamam $(ls SADE_*.jpg | wc -l) jpg"
  cd ..
done
