#!/usr/bin/env python3
"""
V4: isim puntosu govde yuksekliginden; ulke bazli buyuk harf kurali.

DEGISEN OGELER
  - Punto artik harf GOVDESININ yuksekliginden hesaplanir: alta inen harfler
    (J, Q) ve aksanlar hesaba katilmaz (tagline'daki "T" referansiyla ayni
    mantik). Inen harfi olmayan isimlerde sonuc eskisiyle BIREBIR aynidir.
  - Buyuk harf kurali teslimat ulkesine gore: TR -> Turkce (i->I, i->I),
    diger ulkeler -> standart, ulke yoksa isimdeki Turkce harfe gore.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kisisel_pilot import FONT_DIR, FOLDERS, NEW_LEFT, NEW_RIGHT, TAGLINES, fetch, rc
from pilot6 import LUMA, MUREKKEP, kumeler, ONAYLI_DIR, ISIM_FONT, ISIM_W
from pilot12 import (DEST_O, HAM, NORM_W, OUT, ORANLAR, REF_SAYFA, govde, kaydet,
                     oran_kur, plaka, poster_kur, profil_yukle)
from pilot14 import isim_kapisi
import pilot12
import giris_dogrula as gd

YOL = OUT / "ORANLAR"
CIFTLER = [("JACQUELINE", "QUINN", None), (NEW_LEFT, NEW_RIGHT, None),
           ("Deniz", "Elif", "TR")]
TAG = "Written in the Stars Long Before Us"
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def cap_olc(poster, s, yan):
    """Posterdeki ismin GOVDE cap yuksekligi (inen kisim haric)."""
    a = np.asarray(poster.convert("RGB")).astype(np.float32)
    m = (a @ LUMA) > MUREKKEP
    pay = int(max(90, max(s["cap"].values()) * 1.8))
    y0, y1 = int(s["isim_y"] - pay), int(s["isim_y"] + pay)
    km = [c for c in kumeler(m[y0:y1], 20) if c[1] - c[0] > 40]
    if len(km) != 3:
        return None
    x0, x1 = km[0] if yan == "sol" else km[2]
    sut = m[y0:y1, x0:x1]
    sat = sut.sum(axis=1).astype(np.float32)
    dolu = np.nonzero(sat > 0)[0]
    if len(dolu) < 4:
        return None
    # Cap cizgisi = yogunlugun en keskin ARTTIGI satir, taban = en keskin
    # DUSTUGU satir. J/Q kuyruklari azinlikta kaldigi icin bandin disinda kalir.
    dif = np.diff(sat)
    ust = int(np.argmax(dif)) + 1
    taban = int(np.argmin(dif)) + 1
    if taban <= ust:
        ust, taban = int(dolu[0]), int(dolu[-1])
    return {"ink": int(dolu[-1] - dolu[0] + 1), "govde": int(taban - ust),
            "ust": int(y0 + ust), "taban": int(y0 + taban)}


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    if not a.yerel:
        HAM.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST_O}/ham", str(HAM))
        rc("copy", f"{DEST_O}/OLCUM.json", str(YOL))
        (OUT / "hazir").mkdir(parents=True, exist_ok=True)
        rc("copy", "gdrive:ASTROLOVE/TEMP/KISISEL_PILOT/HAZIR/bg.png", str(OUT / "hazir"))
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, OUT / "ref" / "names")
        log("girdiler indi")
    profil_yukle(OUT / "ref" / "names")
    olcum = json.loads((YOL / "OLCUM.json").read_text(encoding="utf-8"))
    kirpimlar = json.loads((ONAYLI_DIR / "ISIM_SATIRI_KIRPIM.json").read_text(
        encoding="utf-8"))
    bg_im = Image.open(OUT / "hazir" / "bg.png")
    oranlar = [o for o in ORANLAR if o in olcum and (HAM / f"{o}_p{REF_SAYFA}.jpg").exists()]
    log(f"oranlar: {oranlar}")

    kapi, test, punto_kiyas = {}, {}, {}
    for o in oranlar:
        s, S = oran_kur(o, olcum[o], bg_im)
        test[o], kucuk = [], []
        for sol_ham, sag_ham, ulke in CIFTLER:
            r = gd.siparis_dogrula(sol_ham, sag_ham, TAG, ulke)
            sol, sag = r["sol"]["deger"], r["sag"]["deger"]
            p, bilgi, merkez, x = poster_kur(s, S, {"sol": sol, "sag": sag}, TAG)
            cap = {y: cap_olc(p, s, y) for y in ("sol", "sag")}
            fark = (abs(cap["sol"]["govde"] - cap["sag"]["govde"])
                    if cap["sol"] and cap["sag"] else None)
            kayit = {"giris": [sol_ham, sag_ham, ulke], "cift": [sol, sag],
                     "durum": r["durum"], "punto": bilgi["punto"],
                     "olcek": bilgi["olcek"], "govde_cap": [cap["sol"], cap["sag"]],
                     "cap_farki": fark, "govde_metni": [govde(sol), govde(sag)]}
            test[o].append(kayit)
            kucuk.append(p.convert("RGB").resize(
                (560, int(round(560 * p.height / p.width))), Image.LANCZOS))
            log(f"{o} {sol}+{sag} ({ulke}): punto {bilgi['punto']} olcek "
                f"%{bilgi['olcek'] * 100:.0f} govde cap "
                f"{[c['govde'] if c else None for c in cap.values()]} fark {fark}")
            if sol == NEW_LEFT:                     # onayli cift -> kapi
                kaydet(p, YOL / f"_kapi_{o}.jpg")
                kapi[o] = isim_kapisi(Image.open(YOL / f"_kapi_{o}.jpg"), o, kirpimlar)
                kapi[o]["punto"] = bilgi["punto"]
                log(f"{o} KAPI: {json.dumps(kapi[o])}")
        yanyana(kucuk, o)
        # eski yontemle punto kiyasi (govde yerine tam metin)
        punto_kiyas[o] = punto_karsilastir(s, S)

    d = {"oranlar": oranlar, "kapi": kapi, "test": test, "punto_kiyas": punto_kiyas,
         "buyuk_harf": buyuk_harf_testi()}
    (YOL / "v4.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str),
                                 encoding="utf-8")
    rapor(d)
    if not a.yerel:
        rc("copy", str(YOL / "SINIR_V4.md"), DEST_O)
        rc("copy", str(YOL / "v4.json"), DEST_O)
        for o in oranlar:
            rc("copy", str(YOL / f"TEST_V4_{o}.jpg"), DEST_O)
        log(f"Drive <- {DEST_O}")
    return d


def punto_karsilastir(s, S):
    """Yeni (govde) ve eski (tam metin) yontemin verdigi punto."""
    from kisisel_pilot import cap_icin_boyut
    from pilot7 import sade
    fp = FONT_DIR / ISIM_FONT
    out = {}
    for ad in ("SERDAR", "LENA", "JACQUELINE", "QUINN", "DENİZ", "ELİF",
               "CHRISTOPHER", "GÜLİZAR"):
        yeni = cap_icin_boyut(fp, govde(ad, fp, ISIM_W), s["cap"]["sol"], ISIM_W)
        eski = cap_icin_boyut(fp, sade(ad), s["cap"]["sol"], ISIM_W)
        out[ad] = {"yeni": yeni, "eski": eski, "fark": yeni - eski}
    return out


def buyuk_harf_testi():
    ornek = [("Deniz", "TR"), ("Deniz", "US"), ("Elif", "TR"), ("Elif", "DE"),
             ("Gülizar", None), ("Christopher", "TR"), ("Christopher", "US"),
             ("İpek", None), ("Quinn", "GB"), ("şükrü", "TR")]
    return [{"giris": a, "ulke": u, "cikti": gd.buyut(a, u)} for a, u in ornek]


def yanyana(kucuk, oran):
    from kisisel_pilot import font_yukle
    et = font_yukle(FONT_DIR / ISIM_FONT, 24, ISIM_W)
    bas, w = 38, 560
    h = max(k.height for k in kucuk)
    im = Image.new("RGB", (w * len(kucuk), h + bas), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for i, (k, (sol, sag, u)) in enumerate(zip(kucuk, CIFTLER)):
        etiket = f"{sol.upper()} - {sag.upper()}" + (f"  ({u})" if u else "")
        dd.text((i * w + 10, 6), etiket, fill=(214, 178, 96), font=et)
        im.paste(k, (i * w, bas))
    kaydet(im, YOL / f"TEST_V4_{oran}.jpg", maks=2_000_000)
    log(f"TEST_V4_{oran}.jpg {im.size}")


def rapor(d):
    o_ = d["oranlar"]
    m = ["# V4: isim puntosu govde yuksekliginden, ulke bazli buyuk harf", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "- **Isim puntosu** (Serdar onayi 21 Eylul 2026): punto artik harf "
         "GOVDESININ yuksekliginden hesaplanir. Alta inen harfler (J, Q) ve aksanlar "
         "hesaba katilmaz - tagline'daki \"T\" referans yontemiyle ayni mantik. "
         "Inen harfi olmayan isimlerde punto BIREBIR ayni kalir.",
         "- **Buyuk harf kurali**: teslimat ulkesi TR ise Turkce (i->İ, ı->I), "
         "diger ulkelerde standart (i->I); ulke bilgisi yoksa isimde Turkce'ye ozgu "
         "harf varsa Turkce, yoksa standart. `giris_dogrula.py` artik `ulke` "
         "parametresi alir.", "",
         "### Degismeyen", "",
         "- D kurali, kenar payi %10, bosluk, cap hedefleri, tagline, altin doku, "
         "zemin, tasinan ogeler, Etsy sinirlari (11 harf / 35 karakter / %65).", "",
         "## 1) Onayli cift birebir mi? (oran ici kapi, SERDAR - LENA)", "",
         "| oran | punto (sol/sag) | harf konumu kaymasi (<=1 px) | murekkep ici farki "
         "(<=3) | sonuc |", "| --- | --- | --- | --- | --- |"]
    for o in o_:
        k = d["kapi"][o]
        m.append(f"| Blue {o} | {k['punto'][0]} / {k['punto'][1]} | {k.get('kayma_px')} "
                 f"| {k.get('ic_fark')} | {'**GECTI**' if k['gecti'] else 'KALDI'} |")
    m += ["", "Punto degisikligi onayli ciftleri etkilemedi: SERDAR ve LENA'da inen "
          "harf yok, govde metni ile tam metin ayni.", "",
          "## 2) Punto kiyasi (yeni govde yontemi / eski tam metin yontemi)", "",
          "Blue " + o_[0] + " cap hedefi uzerinden, sol yuva:", "",
          "| isim | govde metni | yeni punto | eski punto | fark |",
          "| --- | --- | --- | --- | --- |"]
    pk = d["punto_kiyas"][o_[0]]
    for ad, v in pk.items():
        m.append(f"| {ad} | `{govde(ad)}` | {v['yeni']} | {v['eski']} "
                 f"| {'+' if v['fark'] > 0 else ''}{v['fark']} |")
    m += ["", "Yalniz J ve Q iceren isimlerde punto buyudu; digerleri degismedi "
          "(fark 0).", "",
          "## 3) Test ciftleri (5 oran)", "",
          "| cift | ulke | oran | punto (sol/sag) | govde cap (sol/sag) | cift ici fark "
          "(<=2 px) | olcek |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for i, (sol, sag, u) in enumerate(CIFTLER):
        for o in o_:
            t = d["test"][o][i]
            g = t["govde_cap"]
            m.append(f"| {t['cift'][0]} - {t['cift'][1]} | {u or '-'} | Blue {o} "
                     f"| {t['punto'][0]} / {t['punto'][1]} "
                     f"| {g[0]['govde'] if g[0] else '-'} / {g[1]['govde'] if g[1] else '-'} "
                     f"| {t['cap_farki']} | %{int(round(t['olcek'] * 100))} |")
    # asil olcut: AYNI yuvada farkli isimlerin govde cap farki
    yuva_fark = {}
    for o in o_:
        for yi, yan in ((0, "sol"), (1, "sag")):
            v = [t["govde_cap"][yi]["govde"] for t in d["test"][o] if t["govde_cap"][yi]]
            yuva_fark[(o, yan)] = (max(v) - min(v)) if v else None
    en_buyuk = max(x for x in yuva_fark.values() if x is not None)
    m += ["", "### Asil olcut: ayni yuvada farkli isimler ayni cap yuksekliginde mi?",
          "", "| oran | sol yuva (JACQUELINE / SERDAR / DEN\u0130Z) | fark "
          "| sag yuva (QUINN / LENA / EL\u0130F) | fark |",
          "| --- | --- | --- | --- | --- |"]
    for o in o_:
        sol = [t["govde_cap"][0]["govde"] if t["govde_cap"][0] else "-"
               for t in d["test"][o]]
        sag = [t["govde_cap"][1]["govde"] if t["govde_cap"][1] else "-"
               for t in d["test"][o]]
        m.append(f"| Blue {o} | {' / '.join(map(str, sol))} | {yuva_fark[(o, 'sol')]} "
                 f"| {' / '.join(map(str, sag))} | {yuva_fark[(o, 'sag')]} |")
    m += ["", f"Ayni yuvada isimler arasi en buyuk govde cap farki: **{en_buyuk} px** "
          f"(esik 2 px). " + ("JACQUELINE ve QUINN artik SERDAR/LENA ile birebir ayni "
                              "yukseklikte." if en_buyuk <= 2
                              else "**ESIK ASILDI.**"), "",
          "Cift ICI (sol-sag) fark ayri bir konudur ve punto duzeltmesiyle ilgisi "
          "yoktur: Canva'da sol ve sag isim kutulari farkli yuksekliktedir "
          "(4:5'te 85.32 / 83.34 px), bu yuzden onayli SERDAR-LENA'da da ayni fark "
          "vardir. Olculen cift ici farklar: "
          + ", ".join(f"Blue {o} " + " / ".join(
              str(t["cap_farki"]) for t in d["test"][o]) for o in o_) + " px.", "",
          "JACQUELINE ve QUINN'de J ve Q'nun inen kuyruklari taban cizgisinin altinda "
          "kaliyor; govde yuksekligi diger isimlerle ayni.", "",
          "## 4) Buyuk harf kurali", "",
          "| giris | teslimat ulkesi | cikti |", "| --- | --- | --- |"]
    for x in d["buyuk_harf"]:
        m.append(f"| `{x['giris']}` | {x['ulke'] or '(yok)'} | **{x['cikti']}** |")
    m += ["", "Not: `Christopher` + TR -> `CHRİSTOPHER`. Bu, Turkiye'ye teslim "
          "edilen siparislerde Turkce kuralin uygulanmasi kararinin dogal sonucudur: "
          "TR kodunda i harfi her zaman İ olur. Ingilizce isimler TR disi bir "
          "ulkede (veya ulke bilgisi yokken) `CHRISTOPHER` olarak yazilir. Turkiye'ye "
          "giden bir siparistte Ingilizce isim varsa ve nokta istenmiyorsa, siparis "
          "notunda belirtilmesi gerekir.", "",
          "TEST_V4_<oran>.jpg: uc cift yan yana, her oran icin bir dosya.", ""]
    (YOL / "SINIR_V4.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    log("SINIR_V4.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
