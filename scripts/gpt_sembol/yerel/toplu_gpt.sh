#!/bin/bash
# 75 cift: yerel girdi (temiz + kirmizi tepe hatlari) -> 10'luk partiler halinde gpt-sembol dalina push (API kosusu tetiklenir).
# 2 isci (2 CPU, bellek: en fazla 2 paralel render). Gunluk: toplu_gpt.log
B=/home/claude/blender; GS=/home/claude/gs; GD=$B/gi_all; GG=$B/gi_all_girdi
mkdir -p $GD $GG; cd $B
export SERIT_KUME=3.5
LISTE=$(python3 -c "
import csv
bitti={'GEMINI_VIRGO','ARIES_LEO','CANCER_LIBRA'}
print(' '.join(r['cift'] for r in csv.DictReader(open('isim_tagline_78.csv')) if r['cift'] not in bitti))")
N=$(echo $LISTE | wc -w); T0=$(date +%s)
isci() {
  i=0
  for c in $LISTE; do
    i=$((i+1)); [ $((i % ISCI)) -eq $1 ] || continue
    [ -f $GG/${c}_kirmizi.png ] && continue
    KILIT=KILIT_GPTGIRDI.json venv/bin/python uret78.py $c $GD >/dev/null 2>>toplu_gpt.err
    venv/bin/python kirmizi_hat.py $c $GD $GG >>toplu_gpt.err 2>&1 && echo $c >> hazir.txt
    h=$(wc -l < hazir.txt); g=$(( $(date +%s) - T0 ))
    echo "girdi [$h/$N] $c | gecen $((g/60)) dk | kalan ~$(( g*(N-h)/(h>0?h:1)/60 )) dk | %$((100*h/N))" >> toplu_gpt.log
  done
}
touch hazir.txt gonderildi.txt
ISCI=1   # 2 paralel render bellek siniri asiyor (OOM, 7 Eki): tek isci
isci 0 &
# gonderici: 10'luk parti ya da isciler bittiyse kalanlar
while true; do
  kalan=$(grep -vxF -f gonderildi.txt hazir.txt)
  calisan=$(jobs -r | wc -l)
  n=$(echo "$kalan" | grep -c .)
  if [ -f ONAY ] && { [ $n -ge 10 ] || { [ $calisan -eq 0 ] && [ $n -gt 0 ]; }; }; then
    parti=$(echo "$kalan" | head -10)
    for c in $parti; do
      for t in temiz kirmizi; do
        venv/bin/python -c "from PIL import Image; Image.open('$GG/${c}_$t.png').convert('RGB').save('$GS/gpt_sembol/girdi/${c}_$t.jpg', quality=95, subsampling=0)"
      done
    done
    { echo "# gpt-sembol is listesi"; echo "$parti"; } > $GS/gpt_sembol/is.txt
    (cd $GS && git add gpt_sembol && git commit -qm "gpt-sembol parti: $(echo $parti | wc -w) cift

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TQ6T5qTE31RqB6ueSLiZsz" && git push -q origin gpt-sembol) >> toplu_gpt.log 2>&1 \
      && echo "$parti" >> gonderildi.txt && echo "PUSH parti: $(echo $parti)" >> toplu_gpt.log
  fi
  [ $calisan -eq 0 ] && [ -z "$(grep -vxF -f gonderildi.txt hazir.txt)" ] && break
  sleep 30
done
echo "BITTI girdi+push" >> toplu_gpt.log
