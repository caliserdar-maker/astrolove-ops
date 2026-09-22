#!/usr/bin/env python3
"""POD SKU -> Prodigi kalemi (urun tipi dahil). HAZIRLIK: order_router'a henuz baglanmadi.

SKU kalibi (Serdar onayi 22 Eyl 2026):
    POD-<CIFT>-<ED>-<BOY>[-<TIP>]
  TIP yoksa eski davranis: cercevesiz baski (geriye donuk uyumlu, mevcut 78 ilan bozulmaz).
  TIP kodlari: UF = Unframed Print, FB = Framed Black, FW = Framed White, FN = Framed Natural.

Prodigi eslemesi (22 Eyl olcumu, kosu 35690283371):
  UF -> GLOBAL-HPR-<boy>            (Hahnemuhle Photo Rag 308gsm, nitelik yok)
  F* -> GLOBAL-CFP-<boy> + attributes {"color": <renk>}   (Classic Frame, EMA 200gsm)
  Cerceveli kalemde 'color' niteligi ZORUNLU: niteliksiz teklif HTTP 400 dondu.
"""
import re

TIP_KOD = {"UF": {"ad": "Unframed Print", "aile": "GLOBAL-HPR", "nitelik": {}},
           "FB": {"ad": "Framed, Black", "aile": "GLOBAL-CFP", "nitelik": {"color": "black"}},
           "FW": {"ad": "Framed, White", "aile": "GLOBAL-CFP", "nitelik": {"color": "white"}},
           "FN": {"ad": "Framed, Natural", "aile": "GLOBAL-CFP", "nitelik": {"color": "natural"}}}
SKU_TIP_RE = re.compile(r"^(POD-[A-Z]{3}_[A-Z]{3}-[A-Z]{2})-([A-Za-z0-9]+?)(?:-(UF|FB|FW|FN))?$")


def prodigi_kalem(sku, adet=1):
    """POD SKU -> {'prodigi_sku', 'attributes', 'copies', 'tip'} ya da None."""
    m = SKU_TIP_RE.match((sku or "").strip())
    if not m:
        return None
    _kok, boy, tip = m.group(1), m.group(2), m.group(3) or "UF"
    t = TIP_KOD[tip]
    return {"prodigi_sku": f"{t['aile']}-{boy}", "attributes": dict(t["nitelik"]),
            "copies": int(adet), "tip": tip, "tip_adi": t["ad"], "boy": boy}


def quote_kalemi(k):
    """Prodigi /quotes ve /orders icin kalem govdesi."""
    g = {"sku": k["prodigi_sku"], "copies": k["copies"],
         "assets": [{"printArea": "default"}]}
    if k["attributes"]:
        g["attributes"] = dict(k["attributes"])
    return g
