#!/usr/bin/env python3
"""P0.7 / A3 kabul kiyasi (Serdar 22 Eki gece A3): eski ref ve temiz ref ile ayni sahte siparisin ciktilari esit mi.
ESIT TANIMI (kosulardan ONCE yazildi, bu commit):
  Poster (siparis-giris yeni yol, MB 8x10): iki klasorde ayni dosya adlari AstroLoveArt_*.jpg; her dosya iki tarafta ayni
    piksel boyutu ve ayni piksel dizisi (cozulmus JPEG, numpy array_equal). Bayt farki tek basina FAIL degil (raporlanir).
    Gerekce: siparis-gpt gorseli YENIDEN URETMEZ; ChatGPT katmani Drive'dan hazir okunur (siparis-giris.yml 'Kaynak indir'),
    gurultu sabit tohumlu (gpt_birlestir2.py:160 default_rng(11), olcu.py:155 default_rng([seed, y0])) -> birebir beklenir.
    Oran: teslim AstroLoveArt_<B1>_<B2>_8x10.jpg = 2400x3000 (8x10 @300 dpi, 4:5), ana kopya 7200x10800 (2:3); KAPI.json'da
    FAIL yok (iki tarafta).
  Kupa (kupa-siparis, sahte receipt 9000000011, 1 kalem 11 oz): BASKI_*.png ve ONIZLEME_*.jpg ayni ad, ayni boyut, ayni piksel;
    BASKI 2700x1050 (11 oz Printful); OZET.json kapi sonucu PASS ya da GOZ (iki tarafta ayni); PRINTFUL_TASLAK.json iki tarafta esit.
  PASS = iki kosu basarili + tum dosyalar ESIT + oran/boyut dogru + kapilar FAIL degil. Biri tutmazsa FAIL.
Cikti: KIYAS.json + ONIZ_<ad>.jpg (uzun kenar 1600, gercek oran) Merkez kontrolu icin. Yalniz sayi/ad loga; isim/mesaj yok.
Kullanim: esit_kiyas.py --tur poster|kupa --eski DIZIN --yeni DIZIN --out DIZIN"""
import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def dosyalar(d, desen):
    return {p.relative_to(d).as_posix(): p for p in sorted(pathlib.Path(d).rglob(desen))}


def kiyas(a, b):
    ia, ib = Image.open(a), Image.open(b)
    r = dict(boyut_eski=list(ia.size), boyut_yeni=list(ib.size), bayt_ayni=hashlib.sha256(a.read_bytes()).hexdigest()
             == hashlib.sha256(b.read_bytes()).hexdigest(), dpi=list(ia.info.get("dpi") or []))
    r["piksel_ayni"] = ia.size == ib.size and np.array_equal(np.asarray(ia.convert("RGBA")), np.asarray(ib.convert("RGBA")))
    if not r["piksel_ayni"] and ia.size == ib.size:
        r["max_fark"] = int(np.abs(np.asarray(ia.convert("RGB"), np.int16) - np.asarray(ib.convert("RGB"), np.int16)).max())
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", choices=["poster", "kupa"], required=True)
    ap.add_argument("--eski", required=True)
    ap.add_argument("--yeni", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    desenler = ["AstroLoveArt_*.jpg"] if a.tur == "poster" else ["BASKI_*.png", "ONIZLEME_*.jpg"]
    R, hata = dict(tur=a.tur, dosya={}), []
    for desen in desenler:
        de, dy = dosyalar(a.eski, desen), dosyalar(a.yeni, desen)
        if not de:
            hata.append(f"eski tarafta {desen} yok")
        if set(de) != set(dy):
            hata.append(f"{desen} ad kumesi farkli: eski {len(de)}, yeni {len(dy)}")
        for ad in sorted(set(de) & set(dy)):
            r = kiyas(de[ad], dy[ad]); R["dosya"][ad] = r
            if not r["piksel_ayni"]:
                hata.append(f"{ad}: piksel farkli")
            ad_ = pathlib.Path(ad).name
            w, h = r["boyut_yeni"]
            if a.tur == "poster":
                if ad_.endswith("_8x10.jpg") and (w, h) != (2400, 3000):
                    hata.append(f"{ad_}: {w}x{h}, beklenen 2400x3000 (8x10 @300 dpi)")
                elif not ad_.endswith("_8x10.jpg") and (w, h) != (7200, 10800):
                    hata.append(f"{ad_}: {w}x{h}, beklenen 7200x10800")
            elif ad_.startswith("BASKI_") and (w, h) != (2700, 1050):
                hata.append(f"{ad_}: {w}x{h}, beklenen 2700x1050 (11 oz)")
            im = Image.open(dy[ad]).convert("RGB"); im.thumbnail((1600, 1600))
            im.save(out / f"ONIZ_{ad.replace('/', '_').rsplit('.', 1)[0]}.jpg", quality=90)
    if a.tur == "poster":
        if a.tur == "poster" and not any(k.endswith("_8x10.jpg") for k in R["dosya"]):
            hata.append("teslim dosyasi _8x10.jpg yok")
        for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
            k = list(pathlib.Path(d).rglob("KAPI.json"))
            t = k[0].read_text() if k else ""
            R[f"kapi_{taraf}"] = "yok" if not k else ("FAIL var" if "FAIL" in t else "FAIL yok")
            if not k or "FAIL" in t:
                hata.append(f"{taraf} KAPI.json: {R[f'kapi_{taraf}']}")
    else:
        for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
            oz = [json.loads(p.read_text()) for p in pathlib.Path(d).rglob("OZET.json")]
            R[f"ozet_{taraf}"] = [o.get("sonuc") or o.get("karar") or o.get("durum") for o in oz]
        if R["ozet_eski"] != R["ozet_yeni"] or not R["ozet_eski"] or any(str(x).upper() not in ("PASS", "GOZ") for x in R["ozet_eski"]):
            hata.append(f"OZET sonuc eski {R['ozet_eski']} / yeni {R['ozet_yeni']}")
        pe = [p.read_text() for p in sorted(pathlib.Path(a.eski).rglob("PRINTFUL_TASLAK.json"))]
        py = [p.read_text() for p in sorted(pathlib.Path(a.yeni).rglob("PRINTFUL_TASLAK.json"))]
        R["printful_taslak_esit"] = bool(pe) and pe == py
        if not R["printful_taslak_esit"]:
            hata.append("PRINTFUL_TASLAK.json farkli ya da yok")
    R["hata"], R["sonuc"] = hata, ("FAIL" if hata else "PASS")
    (out / "KIYAS.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    for ad, r in R["dosya"].items():
        print(f"{pathlib.Path(ad).name}: {r['boyut_yeni'][0]}x{r['boyut_yeni'][1]} piksel_ayni {r['piksel_ayni']} bayt_ayni {r['bayt_ayni']}")
    print(f"KIYAS {a.tur}: {R['sonuc']} | dosya {len(R['dosya'])} | hata {hata}")
    sys.exit(0 if not hata else 1)


if __name__ == "__main__":
    main()
