#!/bin/bash
cd /home/claude/blender
N=78; i=0; T0=$(date +%s); : > renk_toplu.log
for c in $(python3 -c "import csv;print(' '.join(r['cift'] for r in csv.DictReader(open('isim_tagline_78.csv'))))"); do
  i=$((i+1))
  case $c in GEMINI_VIRGO|ARIES_LEO|CANCER_LIBRA) TB=gb_api;; *) TB=gb_all;; esac
  r=$(venv/bin/python renk_uyum.py $c $TB renkli78 2>&1 | tail -1)
  g=$(( $(date +%s) - T0 ))
  echo "[$i/$N] $c $r | gecen $((g/60)) dk | kalan ~$(( g*(N-i)/i/60 )) dk | %$((100*i/N))" >> renk_toplu.log
done
echo BITTI >> renk_toplu.log
