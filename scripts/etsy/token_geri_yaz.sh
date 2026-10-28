#!/usr/bin/env bash
# Yenilenen Etsy token'ini Drive'a geri yazar (Serdar 27-28 Eki: galeri-v10-yukle e29ca27 deseni, ortak betik).
# Kullanim: bash scripts/etsy/token_geri_yaz.sh [yerel_token] [uzak_hedef]
# Yenileme yoksa (yerel_token.updated yok) hicbir sey yazmaz, 0 doner. 3 deneme; hepsi basarisizsa ::error:: ve 1 doner.
# Cagiran adim cikisi geciktirmek icin: TOKEN_RC=0; bash scripts/etsy/token_geri_yaz.sh || TOKEN_RC=1 ... exit $TOKEN_RC
set -u
Y="${1:-_work/ETSY_TOKEN.json}"
U="${2:-gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json}"
if [ ! -f "$Y.updated" ]; then
  echo "Token yenilenmedi (yenileme yok)"
  exit 0
fi
for n in 1 2 3; do
  if rclone copyto "$Y" "$U"; then
    echo "Token geri yazildi (deneme $n)"
    exit 0
  fi
  echo "Token geri yazimi basarisiz (deneme $n)"
  [ "$n" -lt 3 ] && sleep 10
done
echo "::error::ETSY TOKEN GERI YAZILAMADI (3 deneme). Yeni refresh token kaybolabilir; Etsy kosulari baslatma, Merkez'e bildir."
exit 1
