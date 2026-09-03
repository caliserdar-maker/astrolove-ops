#!/usr/bin/env bash
# canva-bulk-fetch: Canva export listesini tek kosuda indirir ve Drive'a yazar.
#
# Liste (TSV, repo icinde):  <SAYFA_BASLIGI>\t<CIHAZ>\t<EDISYON>\t<URL>
# Hedef: ASTROLOVE/<out_root>/<SIGN1>_<SIGN2>/AstroLove_<Sign1>_<Sign2>_<EDISYON>_<Cihaz>.jpg
# Edisyon satir bazinda; tek kosuda birden fazla edisyon karisik olabilir.
#
# Imzali URL'ler yalniz dosyadan okunur ve alt surece argumanla gecer; loga yazilmaz.
set -euo pipefail

MANIFEST="${1:?liste dosyasi}"
OUT_ROOT="${2:?drive kok klasoru}"
LABEL="${3:-}"
PAR="${4:-8}"

rm -rf _dl _log
mkdir -p _dl _log
: > _log/progress.txt

# TSV -> is listesi (<hedef yol>\t<url>). Ad kalibi ve yazim duzeltmesi burada.
python3 - "$MANIFEST" > _log/jobs.tsv <<'PY'
import pathlib, sys

man = sys.argv[1]
FIX = {"VIGRO": "VIRGO"}          # Canva sayfa basliklarindaki yazim hatasi
seen, out = set(), []
for ln, raw in enumerate(pathlib.Path(man).read_text().splitlines(), 1):
    if not raw.strip() or raw.lstrip().startswith("#"):
        continue
    parts = raw.split("\t")
    if len(parts) != 4:
        sys.exit(f"HATA: satir {ln} 4 alan degil ({len(parts)})")
    title, device, edition, url = (p.strip() for p in parts)
    signs = title.upper().split("_")
    if len(signs) != 2:
        sys.exit(f"HATA: satir {ln} baslik SIGN1_SIGN2 degil: {title}")
    s1, s2 = (FIX.get(s, s) for s in signs)
    dest = f"{s1}_{s2}/AstroLove_{s1.capitalize()}_{s2.capitalize()}_{edition}_{device}.jpg"
    if dest in seen:
        sys.exit(f"HATA: yinelenen hedef {dest} (satir {ln})")
    seen.add(dest)
    out.append(f"{dest}\t{url}")
for line in out:
    print(line)
PY

total=$(wc -l < _log/jobs.tsv)
echo "liste: $MANIFEST -> $total dosya, $PAR paralel${LABEL:+, $LABEL}"

start=$(date +%s)
(
  while [ ! -f _log/bitti ]; do
    sleep 15
    n=$(wc -l < _log/progress.txt)
    el=$(( $(date +%s) - start ))
    if [ "$n" -gt 0 ]; then kalan=$(( el * (total - n) / n )); else kalan=-1; fi
    printf 'ETA %d/%d  gecen %ds  kalan %ds  %%%d\n' "$n" "$total" "$el" "$kalan" $(( n * 100 / total ))
  done
) &
eta=$!

xargs -d '\n' -a _log/jobs.tsv -P "$PAR" -n 1 scripts/canva_fetch_one.sh || true
touch _log/bitti
wait "$eta" 2>/dev/null || true

ok=$(grep -c '^OK'   _log/progress.txt || true)
fail=$(grep -c '^FAIL' _log/progress.txt || true)
echo "indirme: OK $ok / FAIL $fail / toplam $total  (${SECONDS}s)"
[ "$fail" -eq 0 ] && [ "$ok" -eq "$total" ] || {
  echo "::error::indirme eksik (OK $ok, FAIL $fail, beklenen $total)"
  grep '^FAIL' _log/progress.txt || true
  exit 1
}

rclone copy _dl "gdrive:ASTROLOVE/$OUT_ROOT" --transfers 8 --checkers 16 --stats-one-line --stats 30s
rclone check _dl "gdrive:ASTROLOVE/$OUT_ROOT" --one-way

{
  echo "## canva-bulk-fetch: $total dosya"
  echo
  echo '```'
  echo "kok: ASTROLOVE/$OUT_ROOT${LABEL:+   etiket: $LABEL}   sure: ${SECONDS}s"
  for d in $(cut -f2 "$MANIFEST" | sort -u); do
    printf '%-8s %s dosya\n' "$d" "$(find _dl -name "*_${d}.jpg" | wc -l)"
  done
  for e in $(cut -f3 "$MANIFEST" | sort -u); do
    printf '%-18s %s dosya\n' "$e" "$(find _dl -name "*_${e}_*.jpg" | wc -l)"
  done
  printf 'klasor   %s\n' "$(find _dl -mindepth 1 -maxdepth 1 -type d | wc -l)"
  echo '```'
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"

echo "TAMAM: $total dosya ASTROLOVE/$OUT_ROOT altina yazildi ve dogrulandi"
