#!/usr/bin/env bash
# GALERI_77/HAZIR.csv: _HAZIR/<CIFT>.csv satirlarindan yeniden yazilir (her biten cift sonrasi + kosu sonunda).
# Es zamanli yazmada Drive'da ayni adli iki dosya olusmasin diye sonra dedupe (en yeni kalir).
set -uo pipefail
G=gdrive:ASTROLOVE/TEMP/GALERI_77
d=$(mktemp -d); rclone copy "$G/_HAZIR" "$d" --include "*.csv" -q 2>/dev/null
{ echo "cift,listing_id,klasor,gorsel,qc,damga,wp_kaynak,pw_kaynak_tarihi"; cat "$d"/*.csv 2>/dev/null | sort; } > "$d/HAZIR.out"
rclone copyto "$d/HAZIR.out" "$G/HAZIR.csv" -q && rclone dedupe --dedupe-mode newest --max-depth 1 "$G" -q 2>/dev/null
echo "HAZIR.csv: $(( $(wc -l < "$d/HAZIR.out") - 1 )) cift"
rm -rf "$d"
