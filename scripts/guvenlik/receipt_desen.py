#!/usr/bin/env python3
"""Etsy fis (receipt) desenleri, tek kaynak (S1, Serdar 4 Kas 2026 "A."). Sabit onek varsayimi YOK: fis no'lari 40, 41, 42 ...
diye ilerliyor; eski "4[01]" deseni 42'lileri kaciriyordu. Ilke: supheli = maskele (yanlis pozitif kabul, yanlis negatif degil).

ROUTER / ROUTER_B : router stdout'unda tek basina duran 10-12 haneli her sayi (ilan id'leri dahil) -> opak kod.
TARAMA / TARAMA_B : log tarayicisi (gizlilik_temizlik): tam 10 hane. 11+ haneli GitHub kosu id'leri isaretlenmez
                    (genis desen neredeyse her logu isaretlerdi). Canli loglarda fazla isaretleme sayisi OLCULMEDI.
satir_satir       : "::add-mask::" ile baslayan satirlar degistirilmez (sirrin icindeki rakam dizisi degisirse gercek sir
                    maskesiz kalir; kargo_maske.py ile ayni muafiyet)."""
import re

ROUTER = re.compile(r"(?a)(?<!\d)(?<!ord_)\d{10,12}(?!\d)")   # ord_<n> Prodigi kimligi kargo_maske'de (son 4)
ROUTER_B = re.compile(rb"(?<!\d)(?<!ord_)\d{10,12}(?!\d)")
TARAMA = re.compile(r"(?a)(?<!\d)\d{10}(?!\d)")
TARAMA_B = re.compile(rb"(?<!\d)\d{10}(?!\d)")
ADD_MASK = "::add-mask::"


def satir_satir(metin, fn):
    """metin satir satir fn'den gecer; ::add-mask:: satirlari aynen kalir."""
    # yalniz "\n"de bolunur (runner satiri "\n"de boler; splitlines \x85, \u2028, \x0b vb.de de bolerdi: inceleme S1 madde 6)
    return "".join(s if s.lstrip().startswith(ADD_MASK) else fn(s) for s in re.split(r"(?<=\n)", metin) if s)
