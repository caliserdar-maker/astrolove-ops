#!/bin/bash
# Ornament galeri kapak / stil gorseli (onayli ayarlar, Serdar 6 Kas: kapak RUBY, golge "3", V_TON=0, beyaz V_BEYAZ=243).
# kullanim: uret3.sh CIFT STIL BASLIK ALT CIKTI [BASKI]
#   STIL: RUBY | SAPPHIRE | EMERALD | SADE | FILDISI ; BASKI verilmezse $ORN_KAYNAK/<CIFT>_<STIL dosya adi>_954.png
# Ip baslikta harf keserse kapak_ornek.py DUR verir (6 Kas inceleme KRITIK); V_MIN_OLCEK 0,5 = 7 dengesiz baslik cozumu (Serdar "cok guzel").
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
CIFT=$1; STIL=$2; BASLIK=$3; ALT=$4; CIK=$5
KAYNAK=${ORN_KAYNAK:-kaynak}
F=font/ek
export V_MIN_OLCEK=0.5 V_PARLA=0 V_HILAL=0.24 V_NOKTA=0.28 V_GRAD=0.06 V_TON=0
export V_FONT1=$F/playfair-display-latin-800-normal.woff V_FONT2=$F/montserrat-latin-600-normal.woff V_IZ2=0.12
export V_AMP=$F/montserrat-latin-500-normal.woff V_AMP_OLCEK=0.62
O="--golge --dondur 0 --zoom 1.2 --hedef 1500,1590 --bant 640,2360 --y 730,895"
case $STIL in
 RUBY) D=1501.0,1467.0,854.6,871.1,83.4; R=92,10,28; B=RUBY; export V_GOLGE=1.4 V_GOLGE_BLUR=2.5;;
 SAPPHIRE) D=1502.1,1476.8,873.7,889.1,81.6; R=22,40,92; B=SAPPHIRE; export V_GOLGE=1.4 V_GOLGE_BLUR=2.5;;
 EMERALD) D=1502.1,1481.8,876.3,891.2,86.2; R=12,72,48; B=EMERALD; export V_GOLGE=1.4 V_GOLGE_BLUR=2.5;;
 SADE) D=1508.2,1480.9,878.8,886.1,70.9; R=246,238,218; B=SADE_ALTIN; export V_GOLGE=1.7 V_BEYAZ=243;;
 FILDISI) D=1506.2,1478.0,876.5,880.0,99.4; R=246,238,218; B=FILDISI; export V_GOLGE=1.7;;
 *) echo "DUR: bilinmeyen stil $STIL" >&2; exit 2;;
esac
BK=${6:-$KAYNAK/${CIFT}_${B}_954.png}
python3 kapak_ornek.py sahne/S2_${STIL}_kd.png "$BK" "$CIK" --baslik "$BASLIK" --alt "$ALT" --baslik_renk $R --disk $D $O > /dev/null
