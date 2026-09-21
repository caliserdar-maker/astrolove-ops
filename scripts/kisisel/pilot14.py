#!/usr/bin/env python3
"""
V3: oran bazli isim kapisi, 11 harf testi ve giris dogrulama raporu.

DEGISEN OGELER
  - Isim kapisi artik ORAN ICINDE birebir: onayli/ISIM_SATIRI_<oran>.png
    (her oranin kendi ALTIN posterinden kirpildi). Mutlak konum + doku olculur.
  - Etsy sinirlari ONAYLI.json'a islendi (11 harf / 35 karakter, alt sinir %65).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kisisel_pilot import FONT_DIR, FOLDERS, NEW_LEFT, NEW_RIGHT, TAGLINES, fetch, rc
from pilot6 import LUMA, MUREKKEP, kumeler, ONAYLI_DIR, ISIM_FONT, ISIM_W
from pilot12 import (DEST_O, HAM, NORM_W, OUT, ORANLAR, REF_SAYFA, kaydet,
                     oran_kur, poster_kur, profil_yukle)
import pilot12
import giris_dogrula as gd

YOL = OUT / "ORANLAR"
CIFTLER = [("CHRISTOPHER", "ELIZABETH"), ("CHRISTOPHER", "ALEXANDRIA"),
           ("ABDURRAHMAN", "LENA"), ("JACQUELINE", "CHRISTOPHER")]
TAG = "Written in the Stars Long Before Us"       # 35 karakter, sinirda
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def isim_kapisi(poster, oran, kirpimlar):
    """Oran ICINDE birebir: ayni oranin onayli isim satiriyla karsilastir."""
    ref = Image.open(ONAYLI_DIR / f"ISIM_SATIRI_{oran}.png").convert("RGB")
    x0, y0 = kirpimlar[oran]["kirpim"][:2]
    yeni = poster.convert("RGB").crop((x0, y0, x0 + ref.width, y0 + ref.height))
    ao, an = np.asarray(ref).astype(np.float32), np.asarray(yeni).astype(np.float32)
    mo, mn = (ao @ LUMA) > MUREKKEP, (an @ LUMA) > MUREKKEP
    ko, kn = kumeler(mo, 12), kumeler(mn, 12)
    if len(ko) < 3 or len(kn) < 3:
        return {"gecti": False, "sebep": f"kume {len(ko)}/{len(kn)}"}
    kayma = max(abs(ko[0][0] - kn[0][0]), abs(ko[-1][1] - kn[-1][1]))
    ortak = mo & mn
    ic = np.asarray(Image.fromarray((ortak * 255).astype(np.uint8), "L").filter(
        ImageFilter.MinFilter(3))) > 127
    fark = float(np.abs(ao[ic] - an[ic]).mean()) if ic.sum() else 999.0
    return {"gecti": bool(kayma <= 1 and fark <= 3.0), "kayma_px": int(kayma),
            "ic_fark": round(fark, 2), "px": int(ic.sum()), "kume": [len(ko), len(kn)]}


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

    kapi, test = {}, {}
    for o in oranlar:
        s, S = oran_kur(o, olcum[o], bg_im)
        # 1) oran ici kapi: SERDAR - LENA
        pa, ba, _, _ = poster_kur(s, S, {"sol": NEW_LEFT, "sag": NEW_RIGHT}, TAGLINES["A"])
        kaydet(pa, YOL / f"_kapi_{o}.jpg")
        kapi[o] = isim_kapisi(Image.open(YOL / f"_kapi_{o}.jpg"), o, kirpimlar)
        kapi[o]["olcek"] = ba["olcek"]
        log(f"{o} KAPI: {json.dumps(kapi[o])}")

        # 2) 11 harf testi
        test[o], kucuk = [], []
        for sol, sag in CIFTLER:
            p, bilgi, _, _ = poster_kur(s, S, {"sol": sol, "sag": sag}, TAG)
            durum, notlar = gd.olcek_kontrol(bilgi["olcek"], "isim")
            test[o].append({"cift": [sol, sag], "harf": [len(sol), len(sag)],
                            "olcek": bilgi["olcek"], "punto": bilgi["punto"],
                            "satir": bilgi["satir"], "kenar": bilgi["kenar"],
                            "tagline_olcek": bilgi["tagline"]["olcek"],
                            "durum": durum, "notlar": notlar})
            kucuk.append(p.convert("RGB").resize(
                (560, int(round(560 * p.height / p.width))), Image.LANCZOS))
            log(f"{o} {sol}+{sag}: olcek %{bilgi['olcek'] * 100:.0f} "
                f"punto {bilgi['punto']} {durum}")
        yanyana(kucuk, o)

    dogrulama = dogrulama_ornekleri()
    fontlar = font_raporu()
    d = {"oranlar": oranlar, "kapi": kapi, "test": test, "dogrulama": dogrulama,
         "font": fontlar, "sinir": {"isim": gd.ISIM_AZAMI, "tagline": gd.TAG_AZAMI,
                                    "alt_sinir": gd.ALT_SINIR}}
    (YOL / "v3.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str),
                                 encoding="utf-8")
    rapor(d)
    if not a.yerel:
        rc("copy", str(YOL / "SINIR_V3.md"), DEST_O)
        rc("copy", str(YOL / "v3.json"), DEST_O)
        for o in oranlar:
            rc("copy", str(YOL / f"TEST_11_{o}.jpg"), DEST_O)
        log(f"Drive <- {DEST_O}")
    return d


def yanyana(kucuk, oran):
    from kisisel_pilot import font_yukle
    et = font_yukle(FONT_DIR / ISIM_FONT, 24, ISIM_W)
    bas, w = 38, 560
    h = max(k.height for k in kucuk)
    im = Image.new("RGB", (w * len(kucuk), h + bas), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for i, (k, (sol, sag)) in enumerate(zip(kucuk, CIFTLER)):
        dd.text((i * w + 10, 6), f"{sol} - {sag}", fill=(214, 178, 96), font=et)
        im.paste(k, (i * w, bas))
    kaydet(im, YOL / f"TEST_11_{oran}.jpg", maks=2_000_000)
    log(f"TEST_11_{oran}.jpg {im.size}")


def dogrulama_ornekleri():
    ornek = [("SERDAR", "LENA", "Two Souls · One Bond"),
             ("Christopher", "elizabeth", "Written in the Stars Long Before Us"),
             ("Gülizar", "İpek", "Yağmurun Altındaki İlk Öpücük"),
             ("O'Brien", "Anne-Marie", "Forever Us, Forever Now"),
             ("Александр", "LENA", "Forever Us"),
             ("ABDURRAHMANOGLU", "LENA", "Two Souls"),
             ("ANNA", "MARK", "We ❤️ Each Other Always And Forever!"),
             ("中文", "LENA", "Our Story")]
    out = []
    for sol, sag, t in ornek:
        r = gd.siparis_dogrula(sol, sag, t)
        out.append({"giris": [sol, sag, t], "durum": r["durum"],
                    "cikti": [r["sol"]["deger"], r["sag"]["deger"], r["tagline"]["deger"]],
                    "notlar": {k: r[k]["notlar"] for k in ("sol", "sag", "tagline")
                               if r[k]["notlar"]}})
    return out


def font_raporu():
    out = {}
    for tur, ad in gd.FONTLAR.items():
        kod = gd.desteklenen(tur)
        bloklar = {
            "ASCII harf (A-Z a-z)": all(ord(c) in kod for c in
                                        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
            "Latin-1 aksanli (À-ÿ)": sum(1 for o in range(0xC0, 0x100) if o in kod),
            "Latin Extended-A (Ā-ſ)": sum(1 for o in range(0x100, 0x180) if o in kod),
        }
        tr = "ÇĞİÖŞÜçğıöşü"
        eksik_tr = [c for c in tr if ord(c) not in kod]
        noktalama = "'’·-.,!?&–—“”"
        eksik_np = [c for c in noktalama if ord(c) not in kod]
        out[tur] = {"dosya": ad, "kod_noktasi": len(kod), "bloklar": bloklar,
                    "turkce_tam": not eksik_tr, "eksik_turkce": eksik_tr,
                    "eksik_noktalama": eksik_np,
                    "kiril": sum(1 for o in range(0x400, 0x460) if o in kod),
                    "yunan": sum(1 for o in range(0x370, 0x400) if o in kod)}
    return out


def rapor(d):
    o_ = d["oranlar"]
    m = ["# V3: oran bazli isim kapisi, 11 harf testi, giris dogrulama", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "- **Isim kapisi oran icinde birebir oldu**: her oran icin "
         "`onayli/ISIM_SATIRI_<oran>.png` (o oranin kendi ALTIN posterinden "
         "kirpildi). Artik olcek normalize edilmiyor; mutlak konum (<=1 px) ve "
         "murekkep ici farki (<=3) olculuyor.",
         f"- **Etsy sinirlari ONAYLI.json'a islendi**: her isim en fazla "
         f"{d['sinir']['isim']} harf, tagline en fazla {d['sinir']['tagline']} karakter, "
         f"orantili kuculmede alt sinir %{int(d['sinir']['alt_sinir'] * 100)}; altina "
         f"inecek giris URETILMEZ, siparis ELLE KONTROL ile durur.",
         "- **Giris dogrulama kodu eklendi**: `scripts/kisisel/giris_dogrula.py`.", "",
         "### Degismeyen", "",
         "- D kurali, kenar payi %10, bosluk, cap yukseklikleri, tagline genislik "
         "siniri, altin doku, zemin, tasinan ogeler.", "",
         "## 1) Oran bazli isim kapisi (SERDAR - LENA)", "",
         "| oran | referans | harf konumu kaymasi (<=1 px) | murekkep ici farki (<=3) "
         "| olculen px | sonuc |", "| --- | --- | --- | --- | --- | --- |"]
    for o in o_:
        k = d["kapi"][o]
        m.append(f"| Blue {o} | onayli/ISIM_SATIRI_{o}.png | {k.get('kayma_px')} "
                 f"| {k.get('ic_fark')} | {k.get('px')} "
                 f"| {'**GECTI**' if k['gecti'] else 'KALDI'} |")
    m += ["", "Kapi oran icinde calisir: ayni oranin onayli isim satiri ile ayni "
          "koordinatta karsilastirilir, olcek degistirilmez. Bu yuzden V2'deki "
          "oranlar arasi yeniden ornekleme artefakti ortadan kalkti.", "",
          "## 2) 11 harf testi (tagline: \"" + TAG + "\", 35 karakter)", "",
          "| cift | harf |" + "".join(f" {o} |" for o in o_),
          "| --- | --- |" + "".join(" --- |" for _ in o_)]
    for i, (sol, sag) in enumerate(CIFTLER):
        satir = f"| {sol} + {sag} | {len(sol)}+{len(sag)} |"
        for o in o_:
            t = d["test"][o][i]
            satir += f" %{int(round(t['olcek'] * 100))} |"
        m.append(satir)
    m += ["", "Punto ve satir genisligi:", "",
          "| cift | oran | punto (sol/sag) | satir px | kenar px | tagline | durum |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for i, (sol, sag) in enumerate(CIFTLER):
        for o in o_:
            t = d["test"][o][i]
            m.append(f"| {sol} + {sag} | Blue {o} | {t['punto'][0]} / {t['punto'][1]} "
                     f"| {t['satir']} | {t['kenar'][0]} / {t['kenar'][1]} "
                     f"| %{int(round(t['tagline_olcek'] * 100))} | {t['durum']} |")
    en_dusuk = min(t["olcek"] for o in o_ for t in d["test"][o])
    m += ["", "Not: JACQUELINE gibi taban cizgisinin altina inen harf iceren (J, Q) "
          "isimlerde punto belirgin kucuk cikar (orn. 4:5'te 87'ye karsi 112). Sebep: "
          "onayli punto kurali metnin TAM murekkep yuksekligini cap kabul eder; inen "
          "harf bu yuksekligi buyutunce govde kuculur. Duzeltme (cap'i 'T' harfiyle "
          "olcmek - tagline'da zaten boyle) ONAYLI ogeye dokunacagi icin onay bekler.", "",
          f"En dusuk olcek: %{int(round(en_dusuk * 100))} "
          f"(alt sinir %{int(d['sinir']['alt_sinir'] * 100)}). "
          + ("Tum ciftler sinir icinde." if en_dusuk >= d["sinir"]["alt_sinir"]
             else "**Alt sinirin altina inen cift var - ELLE KONTROL.**"), "",
          "TEST_11_<oran>.jpg: dort cift yan yana, her oran icin bir dosya.", "",
          "## 3) Font karakter setleri", "",
          "| font | kullanim | kod noktasi | ASCII harf | Latin-1 aksanli | Latin Ext-A "
          "| Turkce (ÇĞİÖŞÜ) | Kiril | Yunan |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for tur, f in d["font"].items():
        b = f["bloklar"]
        m.append(f"| {f['dosya']} | {tur} | {f['kod_noktasi']} "
                 f"| {'tam' if b['ASCII harf (A-Z a-z)'] else 'EKSIK'} "
                 f"| {b['Latin-1 aksanli (À-ÿ)']}/64 "
                 f"| {b['Latin Extended-A (Ā-ſ)']}/128 "
                 f"| {'tam' if f['turkce_tam'] else 'EKSIK: ' + ' '.join(f['eksik_turkce'])} "
                 f"| {f['kiril']} | {f['yunan']} |")
    m += ["", "Kiril ve Yunan sutunlari 0 ise o alfabe desteklenmiyor demektir; "
          "bu girisler ELLE KONTROL'e dusurulur.", ""]
    for tur, f in d["font"].items():
        if f["eksik_noktalama"]:
            m.append(f"- {f['dosya']}: eksik noktalama {' '.join(f['eksik_noktalama'])}")
    m += ["", "## 4) Giris dogrulama kurallari", "",
          f"**Isim** - en fazla {d['sinir']['isim']} harf; yalniz harf (Latin, Turkce "
          "harfler dahil), bosluk, tire ve kesme isareti (' ’). Isimler her zaman "
          "BUYUK harfe cevrilir (Turkce i -> İ kurali dogru uygulanir). "
          "Desteklenmeyen alfabe (Kiril, Yunan, CJK...), emoji veya fontta olmayan "
          "karakter -> ELLE KONTROL.", "",
          f"**Tagline** - en fazla {d['sinir']['tagline']} karakter; musterinin yazdigi "
          "gibi birakilir (buyuk/kucuk harf degistirilmez). Emoji veya fontta olmayan "
          "karakter -> ELLE KONTROL.", "",
          f"**Alt sinir** - orantili kuculmede olcek %{int(d['sinir']['alt_sinir'] * 100)} "
          "altina inerse cikti URETILMEZ; siparis ELLE KONTROL ile durur.", "",
          "### Ornek girisler", "",
          "| sol | sag | tagline | durum | sebep |",
          "| --- | --- | --- | --- | --- |"]
    for x in d["dogrulama"]:
        g = x["giris"]
        sebep = "; ".join(f"{k}: {', '.join(v)}" for k, v in x["notlar"].items()) or "-"
        m.append(f"| `{g[0]}` | `{g[1]}` | `{g[2][:30]}` | {x['durum']} | {sebep} |")
    m += ["", "Dogrulamayi gecen girislerde isimler su sekilde yazilir: "
          + ", ".join(f"`{x['giris'][0]}` -> `{x['cikti'][0]}`"
                      for x in d["dogrulama"] if x["durum"] == "TAMAM") + ".", "",
          "Kod: `scripts/kisisel/giris_dogrula.py` "
          "(`siparis_dogrula(sol, sag, tagline)` -> TAMAM / ELLE KONTROL).", ""]
    (YOL / "SINIR_V3.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    log("SINIR_V3.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
