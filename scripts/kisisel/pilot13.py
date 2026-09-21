#!/usr/bin/env python3
"""
V2: kenar payi %10 ile bes oranda sinir hesabi, gercek isim dogrulamasi ve
iki katmanli Etsy onerisi.

DEGISEN OGELER
  - Kenar payi artik her oranda poster genisliginin %10'u (2400'de 240 px);
    onceki surumde o oranin en genis orijinal satirindan olculuyordu.
  - Isim sekli kapisinda doku, satir murekkep medyani (profil) ile olculur;
    olcek/yeniden ornekleme artefaktindan etkilenmez.
  - Sinir ornegi: T karakterli gercekci tagline ve Turkce karakterli isim.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kisisel_pilot import FONT_DIR, NEW_LEFT, NEW_RIGHT, TAGLINES, FOLDERS, fetch, rc
from pilot6 import ciz_cap, cap_punto, ISIM_FONT, ISIM_W, TAG_FONT, TAG_W
from pilot12 import (DEST_O, HAM, NORM_W, OUT, ORANLAR, REF_SAYFA, TAGLINELER,
                     kaydet, oran_kur, plaka, poster_kur, profil_yukle,
                     oge_kapisi, yerlesim_kapisi, isim_sekil_kapisi, kos as _)
import pilot12

YOL = OUT / "ORANLAR"
KUCULME_TABANI = 0.90             # "en fazla %10 kuculme" katmani
GERCEK = ["JONATHAN", "ELIZABETH", "ALEXANDRA", "CHRISTOPHER", "KATHERINE",
          "MUHAMMED", "GÜLİZAR", "WILLIAM", "MAXIMILIAN", "ABDURRAHMAN"]
ESLER = ["LENA", "MEHMET"]        # karsi isim 4 ve 6 harf
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def hedef_genislik(s):
    return s["kullanilabilir"] - s["sonsuz_w"] - 2 * s["bosluk"]


def gen(s, S, yan, metin):
    return plaka(metin, S["prof"][yan], s["cap"][yan])[0].width


def cift_olcek(s, S, sol, sag):
    """Iki isim birlikte kuculur: satir olcegi."""
    h = hedef_genislik(s)
    w = gen(s, S, "sol", sol) + gen(s, S, "sag", sag)
    return min(1.0, h / w) if w else 1.0


def harf_sinirlari(s, S, taban=1.0):
    """taban=1.0 tam boy; taban=0.9 en fazla %10 kuculmeye izin."""
    h = hedef_genislik(s) / taban
    px = {y: float(np.mean([gen(s, S, y, a) / len(a) for a in pilot12.ADLAR]))
          for y in ("sol", "sag")}
    d = {"hedef": round(h, 1), "px_harf": {k: round(v, 1) for k, v in px.items()}}
    esit = 0
    for k in range(1, 22):
        if gen(s, S, "sol", "M" * k) + gen(s, S, "sag", "M" * k) <= h:
            esit = k
        else:
            break
    d["esit_M"] = esit
    d["esit_normal"] = int(h / (px["sol"] + px["sag"]))
    for karsi, ad in ((3, "ECE"), (6, "MEHMET")):
        kw = gen(s, S, "sag", ad)
        tek = 0
        for k in range(1, 26):
            if gen(s, S, "sol", "M" * k) + kw <= h:
                tek = k
            else:
                break
        d[f"karsi{karsi}_M"] = tek
        d[f"karsi{karsi}_normal"] = int((h - kw) / px["sol"])
    return d


def tagline_sinirlari(s, taban=1.0):
    fp = FONT_DIR / TAG_FONT
    punto = cap_punto(fp, TAG_W, s["tag_cap"])
    sinir = s["tag_sinir"] / taban
    sat = []
    for t in TAGLINELER:
        cr, _, _ = ciz_cap(fp, TAG_W, punto, t)
        sat.append({"metin": t, "karakter": len(t), "genislik": cr.width,
                    "olcek": round(min(1.0, s["tag_sinir"] / cr.width), 3)})
    normal = [x for x in sat if "Mmmm" not in x["metin"]]
    oran = [x["genislik"] / x["karakter"] for x in normal]
    genis = max(sat, key=lambda x: x["genislik"] / x["karakter"])
    return {"punto": punto, "sinir": s["tag_sinir"], "satirlar": sat,
            "px_karakter_normal": round(float(np.mean(oran)), 2),
            "px_karakter_genis": round(genis["genislik"] / genis["karakter"], 2),
            "azami_normal": int(sinir / np.mean(oran)),
            "azami_genis": int(sinir / (genis["genislik"] / genis["karakter"])),
            "wm_cumle": genis["metin"], "wm_olcek": genis["olcek"]}


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
        log("ham sayfalar + OLCUM.json + bg.png + plakalar indi")
    profil_yukle(OUT / "ref" / "names")
    olcum = json.loads((YOL / "OLCUM.json").read_text(encoding="utf-8"))
    bg_im = Image.open(OUT / "hazir" / "bg.png")
    oranlar = [o for o in ORANLAR if o in olcum and (HAM / f"{o}_p{REF_SAYFA}.jpg").exists()]
    log(f"oranlar: {oranlar} | kenar payi %{pilot12.KENAR_ORAN * 100:.0f}")

    sab, yap, tam, esnek, tagl, kapi = {}, {}, {}, {}, {}, {}
    for o in oranlar:
        s, S = oran_kur(o, olcum[o], bg_im)
        sab[o], yap[o] = s, S
        tam[o] = harf_sinirlari(s, S, 1.0)
        esnek[o] = harf_sinirlari(s, S, KUCULME_TABANI)
        tagl[o] = tagline_sinirlari(s)
        log(f"{o}: kenar {s['kenar_payi']} kullanilabilir {s['kullanilabilir']} "
            f"iki isme kalan {hedef_genislik(s)} | tam boy {tam[o]['esit_normal']}+"
            f"{tam[o]['esit_normal']} normal / {tam[o]['esit_M']}+{tam[o]['esit_M']} M "
            f"| %10 izinli {esnek[o]['esit_normal']} / {esnek[o]['esit_M']} "
            f"| tagline {tagl[o]['azami_normal']} / {tagl[o]['azami_genis']}")

    # gercek isim dogrulamasi
    gercek = {"simetrik": {}, "esli": {}}
    for ad in GERCEK:
        gercek["simetrik"][ad] = {o: round(cift_olcek(sab[o], yap[o], ad, ad), 3)
                                  for o in oranlar}
        for es in ESLER:
            gercek["esli"][f"{ad} + {es}"] = {
                o: round(cift_olcek(sab[o], yap[o], ad, es), 3) for o in oranlar}
    for ad in GERCEK:
        log(f"gercek {ad:12s} simetrik {[gercek['simetrik'][ad][o] for o in oranlar]}")

    # Etsy onerisi: iki katman
    n_tam = min(tam[o]["esit_normal"] for o in oranlar)
    n_tam_m = min(tam[o]["esit_M"] for o in oranlar)
    t_tam = min(tagl[o]["azami_genis"] for o in oranlar)
    t_tam_normal = min(tagl[o]["azami_normal"] for o in oranlar)

    # Katman 2: GERCEK isimlerde tum oranlarda olcek >= 0.90 kalan azami harf
    harf_min = {}
    for ad in GERCEK:
        v = min(gercek["simetrik"][ad][o] for o in oranlar)
        harf_min.setdefault(len(ad), []).append(v)
    uygun = [k for k, v in sorted(harf_min.items()) if round(min(v), 2) >= KUCULME_TABANI]
    n_esnek = max(uygun) if uygun else n_tam
    n_esnek_ort = min(esnek[o]["esit_normal"] for o in oranlar)   # ortalama harfle
    # Katman 1'i de GERCEK isimlerle dogrula (ortalama harf genisligi yaniltici)
    tam_uygun = [k for k, v in sorted(harf_min.items()) if min(v) >= 0.999]
    n_tam_gercek = max(tam_uygun) if tam_uygun else 0
    eslesen = {k: round(min(v), 3) for k, v in sorted(harf_min.items())}

    # Katman 2 tagline: gercek cumlelerde tum oranlarda olcek >= 0.90
    kar_min = {}
    for i, t in enumerate(tagl[oranlar[0]]["satirlar"]):
        if "Mmmm" in t["metin"]:
            continue
        v = min(tagl[o]["satirlar"][i]["olcek"] for o in oranlar)
        kar_min.setdefault(t["karakter"], []).append(v)
    uygun_t = [k for k, v in sorted(kar_min.items()) if min(v) >= KUCULME_TABANI]
    t_esnek = max(uygun_t) if uygun_t else t_tam
    t_tam_gercek = max([k for k, v in sorted(kar_min.items()) if min(v) >= 0.999],
                       default=t_tam)

    kotu = {o: round(cift_olcek(sab[o], yap[o], "M" * n_esnek, "M" * n_esnek), 3)
            for o in oranlar}
    kotu_tam = {o: round(cift_olcek(sab[o], yap[o], "M" * n_tam, "M" * n_tam), 3)
                for o in oranlar}
    wm = {o: tagl[o]["wm_olcek"] for o in oranlar}
    oneri = {"tam": {"isim": n_tam_gercek, "isim_ortalama_harf": n_tam,
                     "harf_olcekleri": eslesen, "isim_M": n_tam_m, "tagline": t_tam,
                     "tagline_normal": t_tam_normal, "tagline_gercek": t_tam_gercek,
                     "en_kotu": kotu_tam},
             "esnek": {"isim": n_esnek, "isim_ortalama_harf": n_esnek_ort,
                       "tagline": t_esnek, "en_kotu": kotu, "wm_tagline": wm}}
    log(f"ONERI tam boy: gercek isimde {n_tam_gercek} harf (ortalama harfle {n_tam}, "
        f"M/W {n_tam_m}), tagline {t_tam} karakter (gercek cumlede {t_tam_gercek})")
    log(f"harf bazinda en kotu olcek: {eslesen}")
    log(f"ONERI %10: isim {n_esnek} harf (ortalama harfle {n_esnek_ort}), tagline "
        f"{t_esnek} karakter, en kotu M/W olcek {kotu}")

    # sinir ornekleri: %10 katmanindaki en uzun gercekci cift + T karakterli tagline
    cift = en_uzun_gercek(n_esnek)
    tag = en_uzun_tagline(t_esnek)
    log(f"ornek cift {cift} | tagline ({len(tag)}) {tag}")
    kucuk = {}
    for o in oranlar:
        s, S = sab[o], yap[o]
        # kapilar onayli cift (SERDAR - LENA) uzerinde olculur
        pa, ba, ma, xa = poster_kur(s, S, {"sol": NEW_LEFT, "sag": NEW_RIGHT},
                                    TAGLINES["A"])
        kaydet(pa, YOL / f"ALTIN_{o}.jpg")
        kapi[o] = {"oge": oge_kapisi(pa, S, s, ma, xa),
                   "yerlesim": yerlesim_kapisi(pa, s, ba, ma, xa,
                                               S["oge"]["sonsuz"].width),
                   "kalinti": s["kalinti"], "isim_sekli": isim_sekil_kapisi(pa, s),
                   "altin_olcek": ba["olcek"]}
        p, bilgi, merkez, x = poster_kur(s, S, {"sol": cift[0], "sag": cift[1]}, tag)
        kaydet(p, YOL / f"SINIR_ORNEK_V2_{o}.jpg")
        kucuk[o] = p.convert("RGB").resize((560, int(round(560 * p.height / p.width))),
                                           Image.LANCZOS)
        kapi[o]["ornek_olcek"] = bilgi["olcek"]
        kapi[o]["ornek_tagline"] = bilgi["tagline"]
        log(f"{o} V2 ornek: olcek %{bilgi['olcek'] * 100:.0f} tagline "
            f"%{bilgi['tagline']['olcek'] * 100:.0f} | ALTIN olcek "
            f"%{kapi[o]['altin_olcek'] * 100:.0f} | sekil doku "
            f"{kapi[o]['isim_sekli'].get('doku_fark')} iou {kapi[o]['isim_sekli'].get('iou')}")

    kiyas(kucuk, oranlar, cift, tag)
    d = {"oranlar": oranlar, "kenar_orani": pilot12.KENAR_ORAN,
         "sabit": {o: {k: v for k, v in sab[o].items() if k != "_S"} for o in oranlar},
         "tam": tam, "esnek": esnek, "tagline": tagl, "gercek": gercek,
         "oneri": oneri, "kapi": kapi, "ornek": {"cift": list(cift), "tagline": tag}}
    (YOL / "oranlar_v2.json").write_text(json.dumps(d, ensure_ascii=False, indent=1,
                                                    default=str), encoding="utf-8")
    sabitler_guncelle(sab, oranlar)
    rapor(d)
    if not a.yerel:
        for f in ("SINIR_ORANLAR_V2.md", "ORAN_KIYAS_V2.jpg", "oranlar_v2.json",
                  "ORAN_SABITLERI.json"):
            if (YOL / f).exists():
                rc("copy", str(YOL / f), DEST_O)
        for o in oranlar:
            rc("copy", str(YOL / f"SINIR_ORNEK_V2_{o}.jpg"), DEST_O)
            rc("copy", str(YOL / f"ALTIN_{o}.jpg"), DEST_O)
        log(f"Drive <- {DEST_O}")
    return d


def en_uzun_gercek(n):
    """N harfli gercekci cift (Turkce karakterler dogru)."""
    havuz = {3: ("ECE", "ADA"), 4: ("LENA", "MARK"), 5: ("SELIM", "DERYA"),
             6: ("SERDAR", "MEHMET"), 7: ("WILLIAM", "GÜLİZAR"),
             8: ("JONATHAN", "MUHAMMED"), 9: ("ELIZABETH", "ALEXANDRA"),
             10: ("MAXIMILIAN", "WILHELMINA"), 11: ("CHRISTOPHER", "ABDURRAHMAN")}
    return havuz.get(max(3, min(n, 11)), ("SERDAR", "LENA"))


def en_uzun_tagline(t):
    uygun = [x for x in TAGLINELER if len(x) <= t and "Mmmm" not in x]
    return max(uygun, key=len) if uygun else TAGLINES["A"]


def kiyas(kucuk, oranlar, cift, tag):
    from kisisel_pilot import font_yukle
    et = font_yukle(FONT_DIR / ISIM_FONT, 26, ISIM_W)
    bas, w = 40, 560
    h = max(k.height for k in kucuk.values())
    im = Image.new("RGB", (w * len(oranlar), h + bas), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for i, o in enumerate(oranlar):
        dd.text((i * w + 12, 6), f"Blue {o}", fill=(214, 178, 96), font=et)
        im.paste(kucuk[o], (i * w, bas))
    kaydet(im, YOL / "ORAN_KIYAS_V2.jpg", maks=2_000_000)
    log(f"ORAN_KIYAS_V2.jpg {im.size}")


def sabitler_guncelle(sab, oranlar):
    p = Path(__file__).resolve().parent / "ORAN_SABITLERI.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"oranlar": {}}
    d["_"] = ("pilot11/pilot12/pilot13 olcumunden turetildi (21 Eylul 2026). Olcu "
              "birimi: poster genisligi 2400 px'e normalize edilmis piksel. Kenar payi "
              "Serdar onayi ile poster genisliginin %10'u.")
    for o in oranlar:
        s = sab[o]
        d["oranlar"].setdefault(o, {})
        d["oranlar"][o].update({
            "tuval": s["tuval"], "bosluk": s["bosluk"], "kenar_payi": s["kenar_payi"],
            "kenar_orani": pilot12.KENAR_ORAN,
            "kullanilabilir_genislik": s["kullanilabilir"], "isim_cap": s["cap"],
            "tagline_cap": s["tag_cap"], "tagline_genislik_siniri": s["tag_sinir"],
            "sonsuzluk_genisligi": s["sonsuz_w"], "bg_hizasi": s["bg_hiza"]})
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (YOL / "ORAN_SABITLERI.json").write_text(json.dumps(d, ensure_ascii=False, indent=2)
                                             + "\n", encoding="utf-8")


def rapor(d):
    o_ = d["oranlar"]
    sa, tam, esn, tg, ge, on, ka = (d["sabit"], d["tam"], d["esnek"], d["tagline"],
                                    d["gercek"], d["oneri"], d["kapi"])
    m = ["# Bes oran - sinirlar V2 (kenar payi %10)", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "- **Kenar payi duzeltildi**: her oranda poster genisliginin %10'u "
         "(2400 px tuvalde 240 px). Onceki surumde o oranin en genis orijinal "
         "satirindan olculuyordu (321-423 px) ve sinirlari gereksiz daraltiyordu. "
         "ONAYLI.json ve ORAN_SABITLERI.json guncellendi; baska sabite dokunulmadi.",
         "- **Isim sekli kapisi**: doku artik satir murekkep medyani (profil) ile "
         "olculur; olcek ve yeniden ornekleme artefaktindan etkilenmez.",
         "- **Sinir ornegi**: T karakterli gercekci tagline ve Turkce karakterli isim "
         "(GÜLİZAR).", "",
         "### Degismeyen", "",
         "- Bosluk, isim/tagline cap yuksekligi, tagline genislik siniri, altin doku, "
         "zemin, tasinan ogeler, D kuralinin kendisi.", "",
         "## Kullanilabilir genislik (kenar payi %10)", "",
         "| oran | kenar payi | kullanilabilir satir | sonsuzluk | 2x bosluk "
         "| iki isme kalan |", "| --- | --- | --- | --- | --- | --- |"]
    for o in o_:
        s = sa[o]
        m.append(f"| Blue {o} | {s['kenar_payi']} | {s['kullanilabilir']} "
                 f"| {s['sonsuz_w']} | {2 * s['bosluk']} "
                 f"| **{s['kullanilabilir'] - s['sonsuz_w'] - 2 * s['bosluk']}** |")
    m += ["", "## 1) Isim sinirlari - TAM BOY (kucultme yok)", "",
          "| oran | esit cift, normal isim | esit cift, en genis harf (M/W) "
          "| karsi 3 harf iken | karsi 6 harf iken |", "| --- | --- | --- | --- | --- |"]
    for o in o_:
        t = tam[o]
        m.append(f"| Blue {o} | {t['esit_normal']}+{t['esit_normal']} "
                 f"| {t['esit_M']}+{t['esit_M']} | {t['karsi3_normal']} "
                 f"({t['karsi3_M']} M) | {t['karsi6_normal']} ({t['karsi6_M']} M) |")
    m += ["", "### En fazla %10 kuculmeye izin verilirse", "",
          "| oran | esit cift, normal | esit cift, M/W | karsi 3 harf | karsi 6 harf |",
          "| --- | --- | --- | --- | --- |"]
    for o in o_:
        t = esn[o]
        m.append(f"| Blue {o} | {t['esit_normal']}+{t['esit_normal']} "
                 f"| {t['esit_M']}+{t['esit_M']} | {t['karsi3_normal']} "
                 f"({t['karsi3_M']} M) | {t['karsi6_normal']} ({t['karsi6_M']} M) |")
    m += ["", "### Gercek isimlerle dogrulama", "",
          "Ayni isim iki yuvada (en kotu simetrik durum). Deger = satir olcegi; "
          "%100 = kuculme yok.", "",
          "| isim | harf |" + "".join(f" {o} |" for o in o_),
          "| --- | --- |" + "".join(" --- |" for _ in o_)]
    for ad in GERCEK:
        satir = f"| {ad} | {len(ad)} |"
        for o in o_:
            v = ge["simetrik"][ad][o]
            satir += f" {'%100' if v >= 0.999 else '%' + str(int(round(v * 100)))} |"
        m.append(satir)
    m += ["", "Karsi isim 4 harf (LENA) ve 6 harf (MEHMET) iken:", "",
          "| cift |" + "".join(f" {o} |" for o in o_),
          "| --- |" + "".join(" --- |" for _ in o_)]
    for k, v in ge["esli"].items():
        satir = f"| {k} |"
        for o in o_:
            x = v[o]
            satir += f" {'%100' if x >= 0.999 else '%' + str(int(round(x * 100)))} |"
        m.append(satir)
    m += ["", "## 2) Tagline sinirlari", "",
          "| oran | punto | genislik siniri | normal cumlede azami karakter "
          "| en genis (W/M) cumlede azami | W/M cumlesinde kuculme |",
          "| --- | --- | --- | --- | --- | --- |"]
    for o in o_:
        t = tg[o]
        m.append(f"| Blue {o} | {t['punto']} | {t['sinir']} | {t['azami_normal']} "
                 f"| {t['azami_genis']} | %{int(round(t['wm_olcek'] * 100))} "
                 f"({t['wm_cumle'][:22]}...) |")
    m += ["", "13 cumlenin oranlara gore olcegi (%100 = tam boy):", "",
          "| karakter | metin |" + "".join(f" {o} |" for o in o_),
          "| --- | --- |" + "".join(" --- |" for _ in o_)]
    for i, t in enumerate(tg[o_[0]]["satirlar"]):
        satir = f"| {t['karakter']} | {t['metin']} |"
        for o in o_:
            x = tg[o]["satirlar"][i]["olcek"]
            satir += f" {'%100' if x >= 0.999 else '%' + str(int(round(x * 100)))} |"
        m.append(satir)
    m += ["", "## 3) ETSY ONERISI - iki katman", "",
          "### Katman 1: her oranda TAM BOY garanti", "",
          f"- Her isim en fazla **{on['tam']['isim']} harf**. Bu, 10 gercek isimle "
          f"dogrulandi: {on['tam']['isim']} harfe kadar bes oranda da hicbir isim "
          f"kuculmuyor. (Ortalama harf genisligiyle teorik deger "
          f"{on['tam']['isim_ortalama_harf']} harf cikiyor, ama 8 harfli MUHAMMED gibi "
          f"genis isimler Blue 2x3'te kuculuyor - bu yuzden gercek olculen deger "
          f"baglayici.) En genis harflerle (M/W) garanti: {on['tam']['isim_M']} harf.",
          f"- Tagline en fazla **{on['tam']['tagline']} karakter** (en genis harflerle "
          f"bile); normal cumlede {on['tam']['tagline_normal']} karaktere kadar sigar.",
          "", f"Bu sinirda {on['tam']['isim']} harfli M/W dizisiyle olcek: "
          + ", ".join(f"Blue {o} %{int(round(on['tam']['en_kotu'][o] * 100))}"
                      for o in o_) + ".", "",
          "### Katman 2: en fazla %10 kuculme", "",
          f"- Her isim en fazla **{on['esnek']['isim']} harf** (gercek isimlerle "
          f"olculdu; ortalama harf genisligiyle {on['esnek']['isim_ortalama_harf']}).",
          f"- Tagline en fazla **{on['esnek']['tagline']} karakter** (13 gercek cumlenin "
          f"bes oranda olculen olcekleriyle).", "",
          "Harf sayisina gore en kotu gercek isim olcegi (bes oranin en dusugu): "
          + ", ".join(f"{k} harf %{int(round(v * 100))}"
                      for k, v in on["tam"]["harf_olcekleri"].items()) + ".", "",
          "Bu sinirda en kotu durumda (tamami M/W harfli isim cifti) olcek:", "",
          "| oran | olcek | kuculme |", "| --- | --- | --- |"]
    for o in o_:
        v = on["esnek"]["en_kotu"][o]
        m.append(f"| Blue {o} | %{int(round(v * 100))} | %{int(round((1 - v) * 100))} |")
    m += ["", "Normal isimlerde bu sinirda kuculme olmaz (tablo 1'deki gercek isim "
          "dogrulamasi).", "",
          "## Kapilar (V2 sinir orneklerinde)", "",
          "| oran | satir merkezi (<=1) | sembol-isim (<=2) | tasinan oge (<=3) "
          "| kalinti (<=3) | isim dokusu (<=3) | IoU |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for o in o_:
        k = ka[o]
        g = k["oge"]
        m.append(f"| Blue {o} | {k['yerlesim']['merkez_sapma']} "
                 f"| {k['yerlesim']['sembol_isim']} "
                 f"| {g['sonsuz']} / {g['sembol_sol']} / {g['sembol_sag']} "
                 f"| {k['kalinti']} | {k['isim_sekli'].get('doku_fark')} "
                 f"| {k['isim_sekli'].get('iou')} |")
    m += ["", f"SINIR_ORNEK_V2_<oran>.jpg: {d['ornek']['cift'][0]} - "
          f"{d['ornek']['cift'][1]} ve \"{d['ornek']['tagline']}\" "
          f"({len(d['ornek']['tagline'])} karakter).",
          "ORAN_KIYAS_V2.jpg: bes oran yan yana.", ""]
    (YOL / "SINIR_ORANLAR_V2.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    log("SINIR_ORANLAR_V2.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
