#!/bin/bash
# halka_yama bindirme (19 Kas, Midnight Blue halka duzeltmesi): MOTOR_DIZINI (checkout edilmis motor_gpt) d2b414ee tabaniyla AYNI ise
# 5 yamali dosya + halka_kodla.py kopyalanir. Taban farkliysa (GPT_REF degismis) HICBIR SEY kopyalanmaz, cikis 1 (eski kopyalar yeni koda
# sessizce yazilmasin). Yamalar yalniz HALKA_DUZELT=1 ile devreye girer.
set -euo pipefail
M="${1:-}"; Y="$(cd "$(dirname "$0")" && pwd)"
[ -n "$M" ] && [ -d "$M" ] || { echo "::error::halka_yama: motor dizini yok"; exit 1; }
( cd "$M" && sha256sum -c --quiet "$Y/TABAN_d2b414ee.sha256" ) || { echo "::error::halka_yama: motor tabani d2b414ee degil, bindirme YOK"; exit 1; }
for f in siparis_uret.py renk_uyum.py olcu.py teslim_jpg.py siparis_kapi.py halka_kodla.py; do cp "$Y/$f" "$M/$f"; done
echo "halka_yama bindirildi (6 dosya, taban d2b414ee)"
