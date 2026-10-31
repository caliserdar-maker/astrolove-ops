#!/bin/bash
# Sade kupa v2 12 burc (Serdar 31 Eki: canli Orchard tasarimi; on tek sembol + isim, arka nazar + mesaj; renkler renk8,
# sembol tum kupalarda ayni boy K 1,06, "guzel"): kapak (Orange stil), 8 stil, 6 sn video. Var olan cikti atlanir.
# Kullanim: bash sade12.sh <BURC> [<BURC> ...]   (BURC buyuk harf, ornek CANCER); calisma klasorunde <BURC>/ acilir
set -eo pipefail
# inceleme 31 Eki: kabukta kalmis ayar degiskenleri sonucu sessizce degistirmesin
unset SEMBOL_K SEMBOL_Y KALIN BOSLUK ISIM_BOY ISIM_AGIRLIK ISIM_ARALIK ISIM_ARA D_IN KATMAN SABIT_YUKSEKLIK
R=/home/claude/caliserdar-maker/astrolove-ops; K=$R/kupa_orchard; KE=$K/kapak_el
export GOLGE_US=1.0 PARLA=0.7 ALT_ORAN=0.55 IZ_ORAN=0.05 ALT_AGIRLIK=600
STIL='07 ORANGE ORANGER 67,87,42 Orange_Blossom 1.6
08 FIG FIGR 126,43,113 Purple_Fig 1.6
09 OLIVE OLIVER 78,84,30 Olive_Breeze 1.6
10 POMEGRANATE POMEGRANATER 139,46,60 Pomegranate_Bloom 1.6
11 ALMOND ALMONDR 112,58,72 Almond_Blossom 2.4
12 LEMON LEMONR 93,76,31 Lemon_Grove 1.6
13 GRAPE GRAPER 72,59,172 Blue_Grape 1.6
14 LOQUAT LOQUATR 105,69,35 Golden_Loquat 1.6'
for B in "$@"; do
  b=$(echo ${B:0:1}${B:1} | sed 's/./\L&/2g')   # Cancer
  mkdir -p $B/is; cd $B
  [ -s is/glif.png ] || git -C $R show refs/kapak78/sembol:kupa_uretim/sembol/${B}_${B}/sol.png > is/glif.png
  while read no S k rgb ad gg; do
    [ -s SADE_STIL_${B}_${no}_${S}.jpg ] && [ -s is/b_${S}_baski_11oz.png ] && [ SADE_STIL_${B}_${no}_${S}.jpg -nt $K/kod/baski_kes_sade.py ] && continue
    KATMAN=1 python3 -I $K/kod/baski_kes_sade.py $K/varlik/kes/$k is/glif.png EMILY "My favorite place is with you" $rgb is/b_$S > is/log_$S.txt
    grep -E "UYARI|HATA" is/log_$S.txt || true
    python3 -I $KE/kod/kapak_canva4.py $KE/sahne/stil/STIL_${S}_uzun.png is/b_${S}_baski_11oz.png $KE/sahne/geo_A3b.json is/k_$S.png >/dev/null
    ALT_REF='PERSONALIZED GIFT MUG' GOLGE_GUC=$gg python3 -I $KE/kod/baslik2.py is/k_$S.png SADE_STIL_${B}_${no}_${S}.jpg $b - 1500 535 185 252,248,240 "${ad//_/ }" 1 >/dev/null
  done <<< "$STIL"
  # kapak ve video baskidan eskiyse yeniden uretilir (eski cikti yeni sanilmasin)
  [ -s SADE_KAPAK_${B}.jpg ] && [ SADE_KAPAK_${B}.jpg -ot is/b_ORANGE_baski_11oz.png ] && rm -f SADE_KAPAK_${B}.jpg
  [ -s SADE_VIDEO_${B}.mp4 ] && [ SADE_VIDEO_${B}.mp4 -ot SADE_KAPAK_${B}.jpg ] && rm -f SADE_VIDEO_${B}.mp4
  if [ ! -s SADE_KAPAK_${B}.jpg ]; then
    python3 -I $KE/kod/kapak_canva4.py $KE/sahne/A3_uzun2.png is/b_ORANGE_baski_11oz.png $KE/sahne/geo_A3b.json is/k_kapak.png >/dev/null
    GOLGE_GUC=1.6 python3 -I $KE/kod/baslik2.py is/k_kapak.png SADE_KAPAK_${B}.jpg $b - 1500 535 185 252,248,240 "PERSONALIZED GIFT MUG" 1 >/dev/null
  fi
  [ -s SADE_VIDEO_${B}.mp4 ] || python3 -I $KE/kod/video_sade.py is/b_ORANGE SADE_KAPAK_${B}.jpg SADE_VIDEO_${B}.mp4 | grep -E "HATA|tamam|toz|katmanlar:"
  n=$(ls SADE_STIL_${B}_*.jpg SADE_KAPAK_${B}.jpg | wc -l); [ $n -eq 9 ] && [ -s SADE_VIDEO_${B}.mp4 ] || { echo "HATA $B: $n/9 jpg, video $( [ -s SADE_VIDEO_${B}.mp4 ] && echo var || echo YOK )"; exit 1; }
  echo "$B tamam 9 jpg + video"
  cd ..
done
