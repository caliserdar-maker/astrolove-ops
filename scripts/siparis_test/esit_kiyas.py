#!/usr/bin/env python3
"""P0.7 / A3 kabul kiyasi v2 (Serdar 23 Eki A3 plani; v1 22 Eki gece: poster birebir piksel varsayimi yanlisti, siparis_uret
gorseli her kosuda yeniden cizer: siparis_uret.py:31,59,75).
ESIT TANIMI (kosulardan ONCE; test bir sonraki turda):
  Kupa: BASKI_*.png ve ONIZLEME_*.jpg ayni ad kumesi, BAYT birebir (sha256); BASKI 2700x1050 (11 oz); OZET.json sonuc PASS ya
    da GOZ ve iki tarafta ayni; PRINTFUL_TASLAK.json iki tarafta esit.
  Poster (siparis-giris yeni yol):
    1. kod: --agac-eski / --agac-yeni (motor_gpt git tree hash) birebir esit.
    2. dosya kumesi tam olarak 3: AstroLoveArt_<B1>_<B2>.jpg (7200x10800), _<OLCU>.jpg (OLCU inc x 300 dpi), _2000.jpg (2000x3000);
       iki tarafta ayni adlar; fazla/eksik dosya FAIL (bos klasor sarti: eski testten kalan dosya FAIL verir).
    3. her dosya iki tarafta: boyut, DPI (300), format (JPEG), ICC profili (var/yok ve bayt esit) ayni.
    4. siparis.json: cift, isim1, isim2, tagline, olcu iki tarafta esit. KAPI.json iki tarafta FAIL icermez.
    5. TABAN: ayni ref'in en az 3 kosusu (--taban DIR DIR DIR ...) arasindaki dosya basina en buyuk piksel farki (max |fark|);
       eski-temiz max farki her dosyada TABAN'dan buyuk degil.
  Onizleme: ONIZ_*.jpg uzun kenar 1600, gercek oran (Merkez kontrolu); son onay Serdar.
Kullanim: esit_kiyas.py --tur poster|kupa --eski DIR --yeni DIR --out DIR [--agac-eski H --agac-yeni H --taban D1 D2 D3 ...]"""
import argparse
import hashlib
import itertools
import json
import pathlib
import re
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def dosyalar(d, desen):
    return {p.relative_to(d).as_posix(): p for p in sorted(pathlib.Path(d).rglob(desen))}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def max_fark(a, b):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return None
    return int(np.abs(np.asarray(ia, np.int16) - np.asarray(ib, np.int16)).max())


def ozellik(p):
    im = Image.open(p)
    dpi = im.info.get("dpi")
    return dict(boyut=list(im.size), format=im.format, dpi=[round(float(x)) for x in dpi] if dpi else None,
                icc=hashlib.sha256(im.info["icc_profile"]).hexdigest()[:16] if im.info.get("icc_profile") else None)


def beklenen_boyut(olcu):
    m = re.fullmatch(r"(\d+)x(\d+)", olcu or "")
    return (int(m.group(1)) * 300, int(m.group(2)) * 300) if m else None


def oniz(src, out, ad):
    im = Image.open(src).convert("RGB"); im.thumbnail((1600, 1600))
    im.save(out / f"ONIZ_{ad.replace('/', '_').rsplit('.', 1)[0]}.jpg", quality=90)


def kupa(a, out, R, hata):
    for desen in ("BASKI_*.png", "ONIZLEME_*.jpg"):
        de, dy = dosyalar(a.eski, desen), dosyalar(a.yeni, desen)
        if not de or set(de) != set(dy):
            hata.append(f"{desen}: ad kumesi farkli ya da bos (eski {len(de)}, yeni {len(dy)})")
        for ad in sorted(set(de) & set(dy)):
            r = dict(bayt_ayni=sha(de[ad]) == sha(dy[ad]), **ozellik(dy[ad])); R["dosya"][ad] = r
            if not r["bayt_ayni"]:
                hata.append(f"{ad}: bayt farkli")
            if pathlib.Path(ad).name.startswith("BASKI_") and r["boyut"] != [2700, 1050]:
                hata.append(f"{ad}: {r['boyut']}, beklenen 2700x1050")
            oniz(dy[ad], out, ad)
    for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
        R[f"ozet_{taraf}"] = [json.loads(p.read_text()).get("sonuc") for p in sorted(pathlib.Path(d).rglob("OZET.json"))]
    if not R["ozet_eski"] or R["ozet_eski"] != R["ozet_yeni"] or any(str(x).upper() not in ("PASS", "GOZ") for x in R["ozet_eski"]):
        hata.append(f"OZET sonuc eski {R['ozet_eski']} / yeni {R['ozet_yeni']}")
    pe = [p.read_text() for p in sorted(pathlib.Path(a.eski).rglob("PRINTFUL_TASLAK.json"))]
    py = [p.read_text() for p in sorted(pathlib.Path(a.yeni).rglob("PRINTFUL_TASLAK.json"))]
    if not pe or pe != py:
        hata.append("PRINTFUL_TASLAK.json farkli ya da yok")


def poster(a, out, R, hata):
    if not a.agac_eski or a.agac_eski != a.agac_yeni:
        hata.append(f"kod agaci esit degil ya da verilmedi ({a.agac_eski} / {a.agac_yeni})")
    sj = {}
    for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
        k = list(pathlib.Path(d).rglob("siparis.json"))
        sj[taraf] = {f: json.loads(k[0].read_text()).get(f) for f in ("cift", "isim1", "isim2", "tagline", "olcu")} if k else None
        kp = list(pathlib.Path(d).rglob("KAPI.json"))
        if not kp or "FAIL" in kp[0].read_text():
            hata.append(f"{taraf} KAPI.json yok ya da FAIL iceriyor")
    if not sj["eski"] or sj["eski"] != sj["yeni"]:
        hata.append("siparis.json (cift/isim/tagline/olcu) farkli ya da yok")
    R["siparis"] = {"esit": bool(sj["eski"]) and sj["eski"] == sj["yeni"], "olcu": (sj["yeni"] or {}).get("olcu")}
    de, dy = dosyalar(a.eski, "AstroLoveArt_*.jpg"), dosyalar(a.yeni, "AstroLoveArt_*.jpg")
    olcu = R["siparis"]["olcu"]
    if len(dy) != 3 or set(de) != set(dy):
        hata.append(f"dosya kumesi: eski {sorted(de)}, yeni {sorted(dy)} (tam 3 ve ayni adlar beklenir)")
    tb = [dosyalar(t, "AstroLoveArt_*.jpg") for t in a.taban]
    if len(tb) < 3:
        hata.append(f"taban icin en az 3 ayni-ref kosusu gerekir ({len(tb)})")
    for ad in sorted(set(de) & set(dy)):
        oe, oy = ozellik(de[ad]), ozellik(dy[ad])
        n = pathlib.Path(ad).name
        bek = (2000, 3000) if n.endswith("_2000.jpg") else beklenen_boyut(olcu) if olcu and n.endswith(f"_{olcu}.jpg") \
            else (7200, 10800)
        taban = [max_fark(x[ad], y[ad]) for x, y in itertools.combinations(tb, 2) if ad in x and ad in y]
        r = dict(eski=oe, yeni=oy, max_fark=max_fark(de[ad], dy[ad]), taban_max=max(taban) if taban else None,
                 taban_ciftler=taban, beklenen=list(bek) if bek else None)
        R["dosya"][ad] = r
        if oe != oy:
            hata.append(f"{n}: boyut/format/DPI/ICC farkli")
        if bek is None or oy["boyut"] != list(bek):
            hata.append(f"{n}: {oy['boyut']}, beklenen {bek}")
        if oy["format"] != "JPEG" or oy["dpi"] != [300, 300]:
            hata.append(f"{n}: format {oy['format']} dpi {oy['dpi']}")
        if r["max_fark"] is None or r["taban_max"] is None or None in taban or r["max_fark"] > r["taban_max"]:
            hata.append(f"{n}: eski-temiz farki {r['max_fark']} > taban {r['taban_max']}")
        oniz(dy[ad], out, ad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", choices=["poster", "kupa"], required=True)
    ap.add_argument("--eski", required=True)
    ap.add_argument("--yeni", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--agac-eski", default="")
    ap.add_argument("--agac-yeni", default="")
    ap.add_argument("--taban", nargs="*", default=[])
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R, hata = dict(tur=a.tur, dosya={}), []
    (kupa if a.tur == "kupa" else poster)(a, out, R, hata)
    R["hata"], R["sonuc"] = hata, ("FAIL" if hata else "PASS")
    (out / "KIYAS.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    for ad, r in R["dosya"].items():
        print(f"{pathlib.Path(ad).name}: " + json.dumps({k: v for k, v in r.items() if k != "taban_ciftler"}, ensure_ascii=False))
    print(f"KIYAS {a.tur}: {R['sonuc']} | dosya {len(R['dosya'])} | hata {hata}")
    sys.exit(0 if not hata else 1)


if __name__ == "__main__":
    main()
