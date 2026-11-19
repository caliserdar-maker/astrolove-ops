#!/usr/bin/env python3
"""Siparis V2 girdisi (18-19 Kas, REAL GO V2): Etsy okumasi KISISEL.json -> uretim istegi istek.json (cift, isim1, isim2, mesaj_b64, renk,
olcu). Isim ve mesaj dispatch girdisine GIRMEZ; bu betik once ::add-mask:: satirlarini basar (satir, kelime >= 3, buyuk/kucuk bicimler),
sonra yalniz True/False basar. DEGER BASMAZ. Beklenen cift / olcu / renk / Format (dispatch girdisi, musteri verisi degil) Etsy
okumasiyla tutmazsa cikis 1, istek yazilmaz.
Kullanim: siparis_v2_girdi.py KISISEL.json CIFT OLCU RENK FORMAT ISTEK_JSON"""
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kesit_olcum import olcu_oku  # noqa: E402

AYIRICI = r"[\r\n\x0b\x0c\x85  ]+"


def maskeler(degerler):
    m = set()
    for t0 in degerler:
        for t in [t0] + re.split(AYIRICI, t0):
            t = t.strip()
            if not t or re.search(AYIRICI, t):
                continue
            m |= {t, t.upper(), t.lower(), t.title(), t.capitalize()}
            for w in t.split() + re.split(r"[^\w]+", t):            # bosluk ve noktalama / tire parcalari (Always-and-Forever -> Forever)
                w = w.strip(".,!?;:\"'()")
                if len(w) >= 3:
                    m |= {w, w.upper(), w.lower(), w.capitalize()}
    return sorted(x for x in m if x)


def main(a):
    kis, cift, olcu, renk, fmt, cikti = a
    k = json.load(open(kis, encoding="utf-8"))["kalemler"]
    v = {x["ad"]: x["deger"] for x in k[0]["varyasyon"]} if k else {}
    isimler = {ad[len("Name under "):].strip().upper(): d for ad, d in v.items() if ad.startswith("Name under ")}
    mesaj = v.get("Your message", "")
    rid = str((json.load(open(kis, encoding="utf-8")) or {}).get("receipt_id") or "")
    for t in maskeler(list(isimler.values()) + [mesaj]) + ([rid] if rid else []):   # ONCE maske, sonra her sey
        print("::add-mask::" + t.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"))
    b1, b2 = sorted(cift.upper().split("_"))
    d = dict(kalem_1=len(k) == 1, cift_alfabetik=cift.upper() == f"{b1}_{b2}", isim_alan_2=len(isimler) == 2,
             isim_burclari_cift=set(isimler) == {b1, b2}, isimler_dolu=all(x.strip() for x in isimler.values()) and len(isimler) == 2,
             mesaj_dolu=bool(mesaj.strip()), mesaj_35=len(mesaj.strip()) <= 35, mesaj_tek_satir=not re.search(AYIRICI, mesaj.strip()),
             renk_ayni=v.get("Color", "").strip().upper().replace(" ", "_") == renk, olcu_ayni=olcu_oku(v.get("Size", "")) == olcu,
             format_ayni=v.get("Format", "") == fmt)
    d["PASS"] = all(d.values())
    print("GIRDI", json.dumps(d))
    if not d["PASS"]:
        return 1
    ist = dict(cift=f"{b1}_{b2}", isim1=isimler[b1].strip(), isim2=isimler[b2].strip(),
               mesaj_b64=base64.b64encode(mesaj.strip().encode("utf-8")).decode(), renk=renk, olcu=olcu)
    Path(cikti).write_text(json.dumps(ist, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
