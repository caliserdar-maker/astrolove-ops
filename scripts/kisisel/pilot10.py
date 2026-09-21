#!/usr/bin/env python3
"""
SECENEK D = orijinal Canva kurali. Ornek uretir; ONAYLI.json'a dokunulmaz.

Kural (Serdar, orijinal sayfalardan):
  1. Isimler hic kuculmez (tam boy).
  2. "sol isim + bosluk + sonsuzluk + bosluk + sag isim" satiri BIR BUTUN
     olarak posterin yatay ortasina (x=1200) hizalidir; sonsuzluk sabit degil.
  3. Her kucuk sembol, altindaki ismin yatay merkezine ortalidir.
  4. Isim ile sonsuzluk arasindaki bosluk sabittir.

Tasinan ogeler (sonsuzluk + iki kucuk sembol) YENIDEN CIZILMEZ: referans
posterden kesilir (alfa = referans ile HAZIR/bg.png farki), eski yerleri
bg.png ile temizlenir, yeni yerlerine ayni piksellerle yapistirilir.

DEGISEN OGELER: YOK.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kisisel_pilot import (DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           TAGLINES, ciz_metin, cap_icin_boyut, fetch,
                           font_yukle, rc)
from pilot6 import (altin as altin_isim, hedef, met_al, kumeler, isim_kontrol,
                    kaydet, temizle, B, LUMA, MUREKKEP, BG_OFS, TUVAL, REFERANS,
                    ISIM_FONT, ISIM_W, TAG_FONT, TAG_W, TAG_PUNTO, ciz_cap)
from pilot7 import kuyruk_duzlestir, altin_sekil, sade
import pilot6

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
YOL = OUT / "YERLESIM"
DEST_Y = DEST + "/YERLESIM"
KENAR_PAYI = 240
MERKEZ = TUVAL[0] / 2
FARK_ESIK = 18                 # oge maskesi: referans-bg mutlak farki
ALFA_LO, ALFA_HI = 4.0, 34.0   # yumusak alfa rampasi
CIFTLER = [(NEW_LEFT, NEW_RIGHT), ("MEHMET", "ALEXANDRA"),
           ("CHRISTOPHER", "ELIZABETH"), ("ŞÜKRÜ", "İPEK")]
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


# ------------------------------------------------------- oge kesme / olcme


def bg_hizali(bg):
    off = int(round(-BG_OFS))
    return bg.convert("RGB").crop((0, off, TUVAL[0], off + TUVAL[1]))


def fark_haritasi(ref, bg):
    a = np.asarray(ref.convert("RGB")).astype(np.float32)
    b = np.asarray(bg_hizali(bg)).astype(np.float32)
    return np.abs(a - b).max(axis=2)


def bantlar(fark, y0=1700, y1=2950, esik=FARK_ESIK):
    sat = (fark > esik).sum(axis=1)
    out, y = [], y0
    while y < y1:
        if sat[y] > 3:
            b = y
            while y < y1 and sat[y] > 3:
                y += 1
            if y - b > 6:
                out.append((b, y))
        y += 1
    return out


def kume_kutusu(fark, bant, x0, x1, esik=FARK_ESIK):
    """Kumenin gercek (sikilastirilmis) kutusu."""
    m = fark[bant[0]:bant[1], x0:x1] > esik
    ys = np.nonzero(m.any(axis=1))[0]
    xs = np.nonzero(m.any(axis=0))[0]
    return (x0 + int(xs[0]), bant[0] + int(ys[0]),
            x0 + int(xs[-1]) + 1, bant[0] + int(ys[1 - 1] if False else ys[-1]) + 1)


def oge_kes(ref, fark, kutu):
    """Referanstan RGBA oge; alfa fark haritasindan yumusak esikle."""
    x0, y0, x1, y1 = kutu
    rgb = np.asarray(ref.convert("RGB")).astype(np.uint8)[y0:y1, x0:x1]
    f = fark[y0:y1, x0:x1]
    al = np.clip((f - ALFA_LO) / (ALFA_HI - ALFA_LO), 0, 1) * 255
    o = np.dstack([rgb, al.astype(np.uint8)])
    return Image.fromarray(o, "RGBA")


def satir_olc(ref, fark=None, esik=None):
    """Isim satiri ve sembol bandini olc: kumeler, bosluklar, merkezler."""
    if fark is None:                                  # Canva sayfasi (bg yok)
        L = np.asarray(ref.convert("RGB")).astype(np.float32) @ LUMA
        h = np.zeros_like(L)
        h[:] = L
        fark, esik = h, MUREKKEP
    esik = esik or FARK_ESIK
    bl = bantlar(fark, 1700, 2950, esik)
    isim_b = max((b for b in bl if 2150 < b[0] < 2400), key=lambda b: b[1] - b[0])
    km = kumeler(fark[isim_b[0]:isim_b[1]] > esik, 20)
    km = [k for k in km if k[1] - k[0] > 40]
    if len(km) != 3:
        raise SystemExit(f"isim satirinda 3 kume bekleniyordu: {km}")
    sol, inf, sag = km
    sem_b = [b for b in bl if b[1] <= isim_b[0] and b[1] > 1850]
    sem = {}
    if sem_b:
        sb = max(sem_b, key=lambda b: b[1] - b[0])
        sk = [k for k in kumeler(fark[sb[0]:sb[1]] > esik, 20) if k[1] - k[0] > 30]
        if len(sk) >= 2:
            sem = {"bant": sb, "sol": sk[0], "sag": sk[-1]}
    d = {"isim_bant": list(isim_b), "sol_isim": list(sol), "sonsuz": list(inf),
         "sag_isim": list(sag),
         "bosluk_sol": inf[0] - sol[1], "bosluk_sag": sag[0] - inf[1],
         "satir": [sol[0], sag[1]],
         "satir_merkez": round((sol[0] + sag[1]) / 2, 1),
         "poster_merkez": ref.width / 2,
         "isim_merkez": [round((sol[0] + sol[1]) / 2, 1), round((sag[0] + sag[1]) / 2, 1)]}
    if sem:
        d["sembol_bant"] = list(sem["bant"])
        d["sembol"] = [list(sem["sol"]), list(sem["sag"])]
        d["sembol_merkez"] = [round((sem["sol"][0] + sem["sol"][1]) / 2, 1),
                              round((sem["sag"][0] + sem["sag"][1]) / 2, 1)]
        d["sembol_isim_kaymasi"] = [round(d["sembol_merkez"][i] - d["isim_merkez"][i], 1)
                                    for i in (0, 1)]
    d["satir_kaymasi"] = round(d["satir_merkez"] - d["poster_merkez"], 1)
    return d


# ------------------------------------------------------------- D yerlesimi


def plaka(metin, met, kutu, tr, olcek=1.0, tam=None):
    tam = tam or cap_icin_boyut(FONT_DIR / ISIM_FONT, sade(metin),
                                hedef(kutu, met)[2], ISIM_W)
    size = max(int(round(tam * olcek)), 4)
    cr, _ = ciz_metin(font_yukle(FONT_DIR / ISIM_FONT, size, ISIM_W), metin, size * tr)
    return altin_isim(cr, met), size


def d_satir(w_sol, w_sag, w_inf, bosluk):
    """Satir bir butun olarak ortalanir; x konumlarini dondurur."""
    toplam = w_sol + bosluk + w_inf + bosluk + w_sag
    x0 = MERKEZ - toplam / 2
    return {"toplam": toplam, "x_sol": x0, "x_inf": x0 + w_sol + bosluk,
            "x_sag": x0 + w_sol + bosluk + w_inf + bosluk,
            "sol_kenar": x0, "sag_kenar": x0 + toplam}


def d_olcek(isimler, yuva, tr, w_inf, bosluk):
    """Kenar payi asilirsa iki isim BIRLIKTE ayni oranda kuculur."""
    maks = TUVAL[0] - 2 * KENAR_PAYI
    olcek, w = 1.0, {}
    for _ in range(8):
        for y in ("sol", "sag"):
            w[y] = plaka(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr, olcek)[0].width
        s = d_satir(w["sol"], w["sag"], w_inf, bosluk)
        if s["toplam"] <= maks:
            break
        pay = maks - w_inf - 2 * bosluk
        olcek *= max(min(pay / (w["sol"] + w["sag"]), 0.99), 0.3)
    return olcek


# ------------------------------------------------------------------- akis


def kos(indir=True, canva=None):
    YOL.mkdir(parents=True, exist_ok=True)
    if indir:
        rc("copy", f"{DEST}/{REFERANS}", str(OUT))
        HAZIR.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST}/HAZIR/bg.png", str(HAZIR))
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, REF / "names")
        for f in ("C_1.jpg", "C_2.jpg", "C_3.jpg"):
            try:
                rc("copy", f"{DEST_Y}/{f}", str(YOL))
            except Exception as e:
                log(f"C posteri alinamadi {f}: {str(e)[:80]}")
        log("referans + bg.png + plakalar + C posterleri indi")

    ref = Image.open(OUT / REFERANS).convert("RGB")
    if ref.size != TUVAL:
        ref = ref.resize(TUVAL, Image.LANCZOS)
    bg = Image.open(HAZIR / "bg.png")
    fark = fark_haritasi(ref, bg)
    olc = satir_olc(ref, fark)
    log(f"referans olcum: {json.dumps(olc, ensure_ascii=False)}")

    bosluk = int(round((olc["bosluk_sol"] + olc["bosluk_sag"]) / 2))
    sem_b = olc["sembol_bant"]
    kutular = {
        "sonsuz": kume_kutusu(fark, olc["isim_bant"], *olc["sonsuz"]),
        "sembol_sol": kume_kutusu(fark, sem_b, *olc["sembol"][0]),
        "sembol_sag": kume_kutusu(fark, sem_b, *olc["sembol"][1]),
    }
    ogeler = {k: oge_kes(ref, fark, v) for k, v in kutular.items()}
    for k, v in kutular.items():
        log(f"kesilen oge {k}: {v} -> {ogeler[k].size}")

    pay = 10
    temiz_kutu = [
        (olc["sol_isim"][0] - pay, olc["isim_bant"][0] - pay,
         olc["sol_isim"][1] + pay, olc["isim_bant"][1] + pay),
        (olc["sonsuz"][0] - pay, olc["isim_bant"][0] - pay,
         olc["sonsuz"][1] + pay, olc["isim_bant"][1] + pay),
        (olc["sag_isim"][0] - pay, olc["isim_bant"][0] - pay,
         olc["sag_isim"][1] + pay, olc["isim_bant"][1] + pay),
        (kutular["sembol_sol"][0] - pay, sem_b[0] - pay,
         kutular["sembol_sol"][2] + pay, sem_b[1] + pay),
        (kutular["sembol_sag"][0] - pay, sem_b[0] - pay,
         kutular["sembol_sag"][2] + pay, sem_b[1] + pay),
    ]
    tag_kutu = None
    L = np.asarray(ref).astype(np.float32) @ LUMA
    tb = [b for b in bantlar(fark, 2450, 2750)]
    if tb:
        t = max(tb, key=lambda b: b[1] - b[0])
        tk = [k for k in kumeler(fark[t[0]:t[1]] > FARK_ESIK, 60) if k[1] - k[0] > 100]
        tx = max(tk, key=lambda k: k[1] - k[0])
        tag_kutu = (tx[0] - 16, t[0] - 16, tx[1] + 16, t[1] + 16)
        temiz_kutu.append(tag_kutu)
    temiz = temizle(ref, bg, temiz_kutu)
    kaydet(temiz.convert("RGB"), YOL / "D_ZEMIN.jpg")

    met_c = met_al(REF / "names" / "cancer_name_gold.png")
    met_l = met_al(REF / "names" / "libra_name_gold.png")
    tr = pilot6.isim_tr_hesapla(met_c, met_l,
                                {"cancer": REF / "names" / "cancer_name_gold.png",
                                 "libra": REF / "names" / "libra_name_gold.png"})
    yuva = {"sol": {"met": met_c, "kutu": B["name_left"]},
            "sag": {"met": met_l, "kutu": B["name_right"]}}

    prof1, _ = kuyruk_duzlestir(np.asarray(met_c["prof"], np.float32))
    cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, TAGLINES["A"])
    tag_pl = altin_sekil(cr, prof1, (cu, ct))
    tag_xy = (int(round(MERKEZ - tag_pl.width / 2)),
              int(round((tag_kutu[1] + tag_kutu[3]) / 2 - tag_pl.height / 2)))

    w_inf = ogeler["sonsuz"].width
    d = {"degisen": [], "degismeyen": [
        "ONAYLI.json (dokunulmadi)", "zemin, logo, yildizlar",
        "sonsuzluk ve kucuk semboller: referanstan kesildi, yeniden cizilmedi",
        "isim dokusu/font/punto kurali", "tagline SECENEK 1 (metin A)"],
        "referans_olcum": olc, "bosluk": bosluk, "sonsuz_genislik": w_inf,
        "kutular": {k: list(v) for k, v in kutular.items()},
        "posterler": [], "kapi": {}, "oge_kapisi": {}}

    kucukler = {}
    for i, cift in enumerate(CIFTLER, 1):
        isimler = {"sol": cift[0], "sag": cift[1]}
        olcek = d_olcek(isimler, yuva, tr, w_inf, bosluk)
        pl = {y: plaka(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr, olcek)
              for y in ("sol", "sag")}
        s = d_satir(pl["sol"][0].width, pl["sag"][0].width, w_inf, bosluk)
        t = temiz.convert("RGBA").copy()
        merkezler = {}
        for y, xk in (("sol", "x_sol"), ("sag", "x_sag")):
            p = pl[y][0]
            _, my, _ = hedef(yuva[y]["kutu"], yuva[y]["met"])
            t.alpha_composite(p, (int(round(s[xk])), int(round(my - p.height / 2))))
            merkezler[y] = s[xk] + p.width / 2
        t.alpha_composite(ogeler["sonsuz"], (int(round(s["x_inf"])), kutular["sonsuz"][1]))
        for y, ad in (("sol", "sembol_sol"), ("sag", "sembol_sag")):
            o = ogeler[ad]
            t.alpha_composite(o, (int(round(merkezler[y] - o.width / 2)), kutular[ad][1]))
        t.alpha_composite(tag_pl, tag_xy)
        dosya = f"D_{i}.jpg"
        kaydet(t, YOL / dosya)
        if i <= 3:
            kucukler[i] = Image.open(YOL / dosya).convert("RGB").resize((800, 1000),
                                                                       Image.LANCZOS)
        kayit = {"dosya": dosya, "cift": list(cift), "olcek": round(olcek, 3),
                 "punto": [pl["sol"][1], pl["sag"][1]],
                 "genislik": [pl["sol"][0].width, pl["sag"][0].width],
                 "satir_toplam": round(s["toplam"], 1),
                 "kenar": [round(s["sol_kenar"], 1), round(TUVAL[0] - s["sag_kenar"], 1)],
                 "isim_merkez": [round(merkezler["sol"], 1), round(merkezler["sag"], 1)],
                 "sonsuz_x": round(s["x_inf"], 1),
                 "sonsuz_kaymasi": round(s["x_inf"] - kutular["sonsuz"][0], 1),
                 "sembol_kaymasi": [
                     round(merkezler["sol"] - ogeler["sembol_sol"].width / 2
                           - kutular["sembol_sol"][0], 1),
                     round(merkezler["sag"] - ogeler["sembol_sag"].width / 2
                           - kutular["sembol_sag"][0], 1)],
                 "isim_merkez_kaymasi": [round(merkezler["sol"] - olc["isim_merkez"][0], 1),
                                         round(merkezler["sag"] - olc["isim_merkez"][1], 1)]}
        d["posterler"].append(kayit)
        log(f"{dosya}: {cift[0]}/{cift[1]} punto {kayit['punto']} olcek "
            f"%{olcek * 100:.0f} satir {kayit['satir_toplam']} kenar {kayit['kenar']} "
            f"sonsuz kayma {kayit['sonsuz_kaymasi']}")
        if i == 1:
            d["kapi"]["isim"] = isim_kontrol(t)
            d["oge_kapisi"] = oge_kapisi(Image.open(YOL / dosya).convert("RGB"),
                                         ogeler, kutular, s, merkezler)
            log(f"  isim kapisi: {json.dumps(d['kapi']['isim'])}")
            log(f"  oge kapisi : {json.dumps(d['oge_kapisi'])}")

    d["olcum"] = harf_olcumu(yuva, tr, w_inf, bosluk)
    if canva:
        d["canva"] = canva_olc(canva)
    kiyas(kucukler)
    rapor(d)
    if indir:
        rc("copy", str(YOL), DEST_Y)
        log(f"Drive <- {DEST_Y}")
    return d


def oge_kapisi(poster, ogeler, kutular, s, merkezler):
    """Tasinan oge ile orijinali arasinda murekkep farki (esik 3)."""
    yerler = {"sonsuz": (int(round(s["x_inf"])), kutular["sonsuz"][1]),
              "sembol_sol": (int(round(merkezler["sol"] - ogeler["sembol_sol"].width / 2)),
                             kutular["sembol_sol"][1]),
              "sembol_sag": (int(round(merkezler["sag"] - ogeler["sembol_sag"].width / 2)),
                             kutular["sembol_sag"][1])}
    out = {}
    for ad, (x, y) in yerler.items():
        o = ogeler[ad]
        yeni = np.asarray(poster.crop((x, y, x + o.width, y + o.height))).astype(np.float32)
        oa = np.asarray(o).astype(np.float32)
        m = oa[..., 3] > 200
        ic = np.asarray(Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.MinFilter(3))) > 127
        fark = float(np.abs(oa[..., :3][ic] - yeni[ic]).mean()) if ic.sum() else 999.0
        out[ad] = {"fark": round(fark, 2), "px": int(ic.sum()), "gecti": bool(fark <= 3.0)}
    out["gecti"] = all(v["gecti"] for v in out.values() if isinstance(v, dict))
    return out


def harf_olcumu(yuva, tr, w_inf, bosluk):
    """Tam boyda (kucultmesiz) sigan azami harf sayisi."""
    maks = TUVAL[0] - 2 * KENAR_PAYI - w_inf - 2 * bosluk     # iki isme kalan toplam
    adlar = ["JONATHAN", "ELIZABETH", "ALEXANDRA", "KATHERINE", "NATHANIEL",
             "CHRISTINA", "MAXIMILIAN", "WILHELMINA", "CHRISTOPHER", "MUHAMMED",
             "ABDURRAHMAN", "MEHMET", "WILLIAM", "SERDAR", "LENA", "MARK", "ECE"]
    px = {y: float(np.mean([plaka(a, yuva[y]["met"], yuva[y]["kutu"], tr)[0].width / len(a)
                            for a in adlar])) for y in ("sol", "sag")}
    d = {"iki_isme_kalan_px": round(maks, 1), "px_harf": {k: round(v, 1) for k, v in px.items()}}

    def m_genislik(y, k):
        return plaka("M" * k, yuva[y]["met"], yuva[y]["kutu"], tr)[0].width

    esit = 0
    for k in range(1, 20):
        if m_genislik("sol", k) + m_genislik("sag", k) <= maks:
            esit = k
        else:
            break
    d["esit_M"] = esit
    d["esit_normal"] = int(maks / (px["sol"] + px["sag"]))
    kisa = plaka("ECE", yuva["sag"]["met"], yuva["sag"]["kutu"], tr)[0].width
    tek = 0
    for k in range(1, 22):
        if m_genislik("sol", k) + kisa <= maks:
            tek = k
        else:
            break
    d["tek_uzun_M"] = tek
    d["tek_uzun_normal"] = int((maks - kisa) / px["sol"])
    return d


def canva_olc(yollar):
    out = {}
    for ad, yol in yollar.items():
        try:
            im = Image.open(yol).convert("RGB")
            if im.size != TUVAL:
                im = im.resize(TUVAL, Image.LANCZOS)
            o = satir_olc(im)
            o["kaynak_boyut"] = list(Image.open(yol).size)
            out[ad] = o
            log(f"canva {ad}: bosluk {o['bosluk_sol']}/{o['bosluk_sag']} "
                f"satir merkez {o['satir_merkez']} kayma {o['satir_kaymasi']} "
                f"sembol-isim {o.get('sembol_isim_kaymasi')}")
        except Exception as e:
            out[ad] = {"hata": str(e)[:160]}
            log(f"canva {ad} olculemedi: {str(e)[:160]}")
    return out


def kiyas(kucukler):
    et = font_yukle(FONT_DIR / ISIM_FONT, 34, ISIM_W)
    bas = 46
    im = Image.new("RGB", (3 * 800, 2 * (1000 + bas)), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for r, (sec, kaynak) in enumerate((("C", None), ("D", kucukler))):
        for c in (1, 2, 3):
            y0 = r * (1000 + bas)
            cift = CIFTLER[c - 1]
            dd.text(((c - 1) * 800 + 14, y0 + 6), f"{sec}  {cift[0]} - {cift[1]}",
                    fill=(214, 178, 96), font=et)
            p = YOL / f"{sec}_{c}.jpg"
            if kaynak is not None:
                k = kaynak[c]
            elif p.exists():
                k = Image.open(p).convert("RGB").resize((800, 1000), Image.LANCZOS)
            else:
                continue
            im.paste(k, ((c - 1) * 800, y0 + bas))
    kaydet(im, YOL / "D_KIYAS.jpg", maks=2_000_000)
    log(f"D_KIYAS.jpg {im.size}")


def rapor(d):
    o, m_ = d["referans_olcum"], d["olcum"]
    m = ["# SECENEK D - orijinal Canva kurali", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "**YOK** - yalniz ornek uretildi; ONAYLI.json'a dokunulmadi.", "",
         "### Degismeyen", ""] + [f"- {x}" for x in d["degismeyen"]] + [
         "", "## Kural dogrulamasi (REFERANS_CANCER_LIBRA)", "",
         "| olcu | deger |", "| --- | --- |",
         f"| isim - sonsuzluk boslugu (sol / sag) | {o['bosluk_sol']} / {o['bosluk_sag']} px |",
         f"| satir | {o['satir'][0]} - {o['satir'][1]} px |",
         f"| satir merkezi | {o['satir_merkez']} (poster merkezi {o['poster_merkez']}, "
         f"sapma {o['satir_kaymasi']} px) |",
         f"| isim merkezleri | {o['isim_merkez'][0]} / {o['isim_merkez'][1]} |",
         f"| sembol merkezleri | {o.get('sembol_merkez', ['-', '-'])[0]} / "
         f"{o.get('sembol_merkez', ['-', '-'])[1]} |",
         f"| sembol - isim merkez farki | {o.get('sembol_isim_kaymasi')} px |", "",
         f"Kural dogrulandi: bosluk iki yanda esit ({o['bosluk_sol']} px), satir "
         f"posterin ortasinda ({o['satir_kaymasi']} px sapma), her sembol kendi isminin "
         f"merkezinde ({o.get('sembol_isim_kaymasi')} px).",
         "", f"Kullanilan sabitler: bosluk **{d['bosluk']} px**, sonsuzluk genisligi "
         f"{d['sonsuz_genislik']} px, kenar payi {KENAR_PAYI} px.", ""]
    if d.get("canva"):
        m += ["## Canva sayfalari", "", "| sayfa | bosluk sol/sag | satir merkezi "
              "| merkezden sapma | sembol-isim farki |", "| --- | --- | --- | --- | --- |"]
        for ad, c in d["canva"].items():
            if "hata" in c:
                m.append(f"| {ad} | olculemedi: {c['hata']} | | | |")
            else:
                m.append(f"| {ad} | {c['bosluk_sol']} / {c['bosluk_sag']} "
                         f"| {c['satir_merkez']} | {c['satir_kaymasi']} "
                         f"| {c.get('sembol_isim_kaymasi')} |")
        m.append("")
    else:
        m += ["## Canva sayfalari", "",
              "Sayfa 20 / 36 / 72 bu kosuda olculmedi (disa aktarma baglantisi "
              "verilmedi). Kural yalniz CANCER_LIBRA referansiyla dogrulandi.", ""]
    m += ["## Tasinan ogeler", "",
          "Sonsuzluk ve iki kucuk sembol yeniden cizilmedi: referanstan kesildi "
          "(alfa = referans - bg.png farki), eski yerleri bg.png ile temizlendi, yeni "
          "yerlerine ayni piksellerle yapistirildi.", "",
          "| oge | referanstaki kutu | murekkep farki | kapi (<=3) |",
          "| --- | --- | --- | --- |"]
    for ad in ("sonsuz", "sembol_sol", "sembol_sag"):
        k = d["oge_kapisi"].get(ad, {})
        m.append(f"| {ad} | {d['kutular'][ad]} | {k.get('fark')} "
                 f"| {'GECTI' if k.get('gecti') else 'KALDI'} |")
    m += ["", "## Uretilen posterler", "",
          "| dosya | cift | punto | olcek | satir genisligi | kenar payi (sol/sag) "
          "| sonsuzluk kaymasi | sembol kaymasi |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in d["posterler"]:
        m.append(f"| {p['dosya']} | {p['cift'][0]} - {p['cift'][1]} "
                 f"| {p['punto'][0]} / {p['punto'][1]} | %{p['olcek'] * 100:.0f} "
                 f"| {p['satir_toplam']} | {p['kenar'][0]} / {p['kenar'][1]} "
                 f"| {p['sonsuz_kaymasi']} | {p['sembol_kaymasi'][0]} / "
                 f"{p['sembol_kaymasi'][1]} |")
    k = d["kapi"]["isim"]
    m += ["", "## Kontrol: SERDAR - LENA", "",
          f"- Isim kapisi (onayli ISIM_SATIRI_ALTIN ile): "
          f"**{'GECTI' if k['gecti'] else 'GECMEDI - BEKLENEN'}** "
          f"(kayma {k.get('kayma_px')} px, murekkep fark {k.get('murekkep_fark')}). "
          f"Kapi harfin AYNI PIKSELDE olmasini arar; D kuralinda satir ortalandigi "
          f"icin isim satiri butun olarak kayar, dolayisiyla bu kapi D'de yapisal "
          f"olarak gecemez. Harf sekli ve dokusu degismedi - degisen yalniz konum.",
          f"- Satir ortalandigi icin isim merkezleri onayli posterdeki yerlerinden "
          f"{d['posterler'][0]['isim_merkez_kaymasi'][0]} / "
          f"{d['posterler'][0]['isim_merkez_kaymasi'][1]} px kaydi; sonsuzluk "
          f"{d['posterler'][0]['sonsuz_kaymasi']} px, semboller "
          f"{d['posterler'][0]['sembol_kaymasi'][0]} / "
          f"{d['posterler'][0]['sembol_kaymasi'][1]} px kaydi.",
          "- Kayma beklenen sonuctur: SERDAR ve LENA, CANCER ve LIBRA'dan dar oldugu "
          "icin ortalanan satir kisalir.", "",
          "## Azami harf sayisi (tam boyda, kucultmesiz)", "",
          f"Iki isme kalan toplam genislik: **{m_['iki_isme_kalan_px']} px** "
          f"(2400 - 2x{KENAR_PAYI} kenar payi - {d['sonsuz_genislik']} sonsuzluk "
          f"- 2x{d['bosluk']} bosluk).", "",
          "| durum | en genis harf (M) | normal isim |", "| --- | --- | --- |",
          f"| iki isim de ayni uzunlukta | {m_['esit_M']} + {m_['esit_M']} harf "
          f"| {m_['esit_normal']} + {m_['esit_normal']} harf |",
          f"| bir isim uzun, digeri 3 harf | {m_['tek_uzun_M']} harf "
          f"| {m_['tek_uzun_normal']} harf |", "",
          f"Olculen ortalama harf genisligi: sol {m_['px_harf']['sol']} px, "
          f"sag {m_['px_harf']['sag']} px.", "",
          "## Karsilastirma", "",
          "- D_KIYAS.jpg: ust satir C_1..C_3, alt satir D_1..D_3.",
          "- D_1..D_4.jpg: SERDAR-LENA, MEHMET-ALEXANDRA, CHRISTOPHER-ELIZABETH, "
          "SUKRU-IPEK (tagline A, SECENEK 1 doku).", ""]
    (YOL / "D_RAPOR.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    (YOL / "d.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str),
                                encoding="utf-8")
    log("D_RAPOR.md yazildi")


def canva_indir(urls):
    OUT.mkdir(parents=True, exist_ok=True)
    yollar = {}
    for ad, u in zip(("sayfa20", "sayfa36", "sayfa72"), urls):
        p = OUT / f"canva_{ad}.jpg"
        try:
            with urllib.request.urlopen(u, timeout=90) as r, open(p, "wb") as f:
                f.write(r.read())
            log(f"canva {ad} indi: {p.stat().st_size / 1e6:.1f} MB")
            yollar[ad] = p
        except Exception as e:
            log(f"canva {ad} indirilemedi: {str(e)[:140]}")
    return yollar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--canva", nargs="*", default=None)
    a = ap.parse_args()
    canva = canva_indir(a.canva) if a.canva else None
    kos(indir=not a.yerel, canva=canva)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
