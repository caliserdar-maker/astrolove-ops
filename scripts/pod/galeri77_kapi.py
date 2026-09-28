#!/usr/bin/env python3
"""77 cift galerisi: siparis_dosyasi KAPI_RAPORU.json galeri icin kabul edilir mi.
Kabul: durum URETILDI ve 'olcek' disindaki tum kapilar gecti (None = uygulanmadi). 'olcek' kapisi isim satirinin
2400 onayli render'a <= 1-2 px (3307 px baskida) konum/kenar uyumudur; galeri gorselinde (poster <= 1379 px) gorunmez.
Sembol, kalinti, leke, temiz ara zemin, mesaj murekkebi kapilari MUTLAKA gecmeli.
Kullanim: galeri77_kapi.py KAPI_RAPORU.json  -> tek satir, cikis 0 = kabul
"""
import json
import sys

r = json.load(open(sys.argv[1]))
k = r.get('kapilar') or {}
kalan = [a for a, v in k.items() if v is False]
ok = r.get('durum') == 'URETILDI' and bool(k) and set(kalan) <= {'olcek'}
print(f"{r.get('receipt')}: durum {r.get('durum')} | kalan kapi {kalan or '-'} | {'KABUL' if ok else 'RED'}"
      + (f" | hata {r.get('hata')}" if r.get('hata') else ''))
sys.exit(0 if ok else 1)
