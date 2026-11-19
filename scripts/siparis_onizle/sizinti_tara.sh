#!/bin/bash
# Push / kosu oncesi sizinti taramasi (19 Kas, GOREV HALKA_KALICI): origin/main..HEAD farki + commit mesajlari + verilen ek metin (dispatch
# girdileri, PR basligi / govdesi, rapor). Arar: 42 ile baslayan 10 haneli sayi (siparis no), e-posta, SIPARIS/<rakam> yolu, ek yasak sozcukler
# (SIZINTI_EK, virgullu; musteri adlari burada VERILMEZ, cagiran ortamdan verir). Bulursa satiri MASKELI basar (deger yazilmaz), cikis 1.
set -uo pipefail
TABAN="${1:-origin/main}"; shift || true
kaynak() { git diff "$TABAN"..HEAD || return 1; git log "$TABAN"..HEAD --format=%B || return 1; for f in "$@"; do [ -f "$f" ] && cat "$f"; done; return 0; }
desen='(?<![0-9])42[0-9]{8}(?![0-9])|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|SIPARIS/[0-9]'   # inceleme G H2: \b alt cizgiyi kelime sayar
ek="${SIZINTI_EK:-}"; [ -n "$ek" ] && desen="$desen|$(printf '%s' "$ek" | sed 's/[][\.^$*+?(){}|/]/\\&/g; s/,/|/g')"
metin=$(kaynak "$@") || { echo "SIZINTI TARAMASI CALISMADI (git hatasi)"; exit 2; }
bulgu=$(printf '%s\n' "$metin" | sed -E 's/noreply@anthropic\.com|4200000001|4299999999/<izinli>/g' | grep -nP "$desen" || true)   # inceleme F 12: yalniz izinli belirtec silinir, satir degil
if [ -n "$bulgu" ]; then echo "SIZINTI: $(printf '%s\n' "$bulgu" | wc -l) satir (degerler yazilmaz)"; printf '%s\n' "$bulgu" | cut -d: -f1 | head -20 | sed 's/^/  satir /'; exit 1; fi
echo "sizinti taramasi temiz ($TABAN..HEAD + $# ek dosya)"
