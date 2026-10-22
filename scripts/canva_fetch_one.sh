#!/usr/bin/env bash
# canva-bulk-fetch is birimi: tek satiri (<hedef>\t<url>) indirir.
# URL hicbir kosulda loga yazilmaz; sonuc _log/progress.txt'ye eklenir.
set -uo pipefail

line="$1"
dest="${line%%$'\t'*}"
url="${line#*$'\t'}"

mkdir -p "_dl/$(dirname "$dest")"
if curl -fsS --retry 3 --retry-delay 2 --retry-connrefused --max-time 300 \
        -o "_dl/$dest" "$url" 2>/dev/null \
   && [ -s "_dl/$dest" ] \
   && [ "$(head -c 2 "_dl/$dest" | od -An -tx1 | tr -d ' ')" = "ffd8" ]; then
  echo "OK   $dest" >> _log/progress.txt
  exit 0
fi

rm -f "_dl/$dest"
echo "FAIL $dest" >> _log/progress.txt
