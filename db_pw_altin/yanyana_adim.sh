#!/usr/bin/env bash
# Yan yana (eski | yeni) + Drive + ozet. Kullanim: yanyana_adim.sh IS ESKI TESLIM SONUC [DRIVE_HEDEF]
# IS: db_pw_uret ciktisi, ESKI: eski sistem cikti koku (<ESKI>/<RENK>/<RENK>/*_2x3_*.jpg), TESLIM: Drive'a giden klasor,
# SONUC: dala yazilan ozet klasoru. DRIVE_HEDEF bos ise yukleme yapilmaz (yerel deneme).
set -u
IS=$1; ESKI=$2; O=$3; S=$4; D=${5:-}
PY=${MOTOR_PY:-/home/claude/blender/venv/bin/python}; K=$(dirname "$0")
C=$(echo "$CIFT" | python3 -c "import sys;a,b=sys.stdin.read().strip().split('_');print(a.capitalize()+'_'+b.capitalize())")
mkdir -p "$O" "$S"; HATA=0
for r in DEEP_BLACK PURE_WHITE; do
  rn=$(echo $r | python3 -c "import sys;print('_'.join(w.capitalize() for w in sys.stdin.read().strip().split('_')))")
  for f in "$IS"/$r/AstroLoveArt_*.jpg; do if [ -e "$f" ]; then cp "$f" "$O"/; fi; done
  for p in "2x3 24x36" "4x5 16x20"; do
    set -- $p
    e=$(ls "$ESKI"/$r/$r/*_${1}_*.jpg 2>/dev/null | grep -v _olcekli_ | head -1)
    y="$IS"/$r/AstroLoveArt_${C}_${rn}_$2.jpg
    if [ -z "$e" ]; then echo "UYARI eski yok $r $1"; HATA=1; continue; fi
    cp "$e" "$O"/ESKI_AstroLoveArt_${C}_${rn}_$2.jpg
    if [ -e "$y" ]; then "$PY" "$K"/yanyana.py "$e" "$y" "$O"/YANYANA_${rn}_$2_ESKI_YENI.jpg "$S"/ONIZLEME_${rn}_$2.jpg || HATA=1
    else echo "UYARI yeni yok $y"; HATA=1; fi
  done
  cp "$IS"/$r/AstroLoveArt_*_2000.jpg "$S"/ 2>/dev/null
done
cp "$IS"/MIDNIGHT_BLUE/AstroLoveArt_*_Midnight_Blue_2000.jpg "$S"/ 2>/dev/null
python3 - "$IS" "$S" <<'PY'
import json, os, sys
s = json.load(open(sys.argv[1] + '/siparis.json')) if os.path.exists(sys.argv[1] + '/siparis.json') else {}
for k in ('isim1', 'isim2', 'tagline'): s.pop(k, None)
json.dump(s, open(sys.argv[2] + '/URETIM.json', 'w'), indent=1)
PY
if [ -e "$IS"/KAPI.json ]; then cp "$IS"/KAPI.json "$S"/; cp "$IS"/KAPI.json "$O"/; fi
if [ -e "$IS"/plaka/PLAKA.json ]; then cp "$IS"/plaka/PLAKA.json "$S"/; fi
if [ -n "$D" ]; then
  rclone copy "$O" "$D" || HATA=1
  rclone lsjson "$D" --files-only | python3 -c "import json,sys;json.dump({x['Name']: 'https://drive.google.com/file/d/'+x['ID']+'/view' for x in json.load(sys.stdin)}, open(sys.argv[1],'w'), indent=1)" "$S"/LINKLER.json || HATA=1
  cat "$S"/LINKLER.json
fi
ls -la "$O" "$S"
exit $HATA
