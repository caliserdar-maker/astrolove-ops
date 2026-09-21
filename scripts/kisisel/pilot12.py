#!/usr/bin/env python3
"""
SECENEK D uretimi - bes oran (Blue 2/3, 3/4, 4/5, 11/14, A).

Her oran KENDI orijinal sayfalarindan olculen sabitlerle uretilir:
bosluk, kenar payi, isim cap yuksekligi, tagline cap yuksekligi ve genislik
siniri. Tasinan ogeler (sonsuzluk + iki kucuk sembol) ve isim altin dokusu
o oranin KENDI referans sayfasindan (28, CANCER_LIBRA) alinir.

DEGISEN OGELER: yok - ONAYLI.json'a dokunulmaz; bu kosu ornek ve olcum uretir.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kisisel_pilot import (DEST, FONT_DIR, NEW_LEFT, NEW_RIGHT, TAGLINES,
                           bbox_of, cap_icin_boyut, ciz_metin, font_yukle, rc)
from pilot6 import (ONAYLI_DIR, LUMA, MUREKKEP, kumeler, ciz_cap, cap_punto,
                    ISIM_FONT, ISIM_W, TAG_FONT, TAG_W)
from pilot7 import kuyruk_duzlestir, altin_sekil, sade
from pilot11 import HAM, NORM_W, norm, bantlar, sayfa_olc, bg_hizasi
from kisisel_pilot import FOLDERS, fetch
from pilot6 import met_al

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
YOL = OUT / "ORANLAR"
DEST_O = DEST + "/ORANLAR"
ORANLAR = ["2x3", "3x4", "4x5", "11x14", "A"]
REF_SAYFA = 28
KENAR_ORAN = 0.10                 # Serdar onayi: kenar payi = poster genisliginin %10'u
TAG_TABAN_SINIR = 1670.0          # 4:5'te Mo'nun onayladigi sinir
TAG_TABAN_CAP = 71.0              # 4:5'te olculen tagline bant yuksekligi
FARK_ESIK = 18
ALFA_LO, ALFA_HI = 4.0, 34.0
CIFT = (NEW_LEFT, NEW_RIGHT)
TAGLINELER = [
    "It Began With a Kiss in the Rain", "Two Hearts, One Endless Story",
    "We Found Forever in a Moment", "Where Our Worlds Met and Stayed",
    "My Whole World Was Waiting There", "Written in the Stars Long Before Us",
    "Wherever We Wander We Are Home Now",
    "Yağmurun Altındaki İlk Öpücük",
    "Two Souls · One Bond", "Always You, Always Me, Always Us",
    # W/M agirlikli
    "We Married Well, My Wonderful Wife", "Mmmm Wwww Mmmm Wwww Mmmm",
    "Where We Wander, We Welcome More",
    # kisa, gercekci cumleler (sinir orneklerinde kullanilir)
    "Forever Us, Forever Now", "Two Hearts, One Home",
    "Always You, Always Me", "İki Kalp, Tek Yürek",
    "Our Story Starts Here",
]
ADLAR = ["JONATHAN", "ELIZABETH", "ALEXANDRA", "KATHERINE", "NATHANIEL",
         "CHRISTINA", "MAXIMILIAN", "WILHELMINA", "CHRISTOPHER", "MUHAMMED",
         "ABDURRAHMAN", "MEHMET", "WILLIAM", "SERDAR", "LENA", "MARK", "ECE"]
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


# --------------------------------------------------------------- oge kesme


def fark_haritasi(ref, bg_im, s, dy):
    """bg'yi olculen (olcek, dy) ile hizalayip mutlak fark haritasini dondur."""
    w = int(round(NORM_W * s))
    b = bg_im.convert("RGB").resize((w, int(round(bg_im.height * w / bg_im.width))),
                                    Image.LANCZOS)
    bx = (w - NORM_W) // 2
    y0 = (b.height - ref.height) // 2 + dy
    y0 = max(0, min(y0, b.height - ref.height))
    zemin = b.crop((bx, y0, bx + NORM_W, y0 + ref.height))
    a = np.asarray(ref).astype(np.float32)
    c = np.asarray(zemin).astype(np.float32)
    return np.abs(a - c).max(axis=2), zemin


def ince_hiza(ref, bg_im, kaba):
    """Kaba aramanin cevresinde 0.01 / 8 px adimla ince arama."""
    A = np.asarray(ref).astype(np.float32)
    bos = (A @ LUMA) < MUREKKEP
    en = None
    for s in np.arange(kaba["olcek"] - 0.04, kaba["olcek"] + 0.041, 0.01):
        for dy in range(kaba["dy"] - 32, kaba["dy"] + 33, 8):
            f, _ = fark_haritasi(ref, bg_im, float(s), int(dy))
            m = float(np.median(f[bos][::5]))
            if en is None or m < en[0]:
                en = (m, round(float(s), 3), int(dy))
    return {"medyan_fark": round(en[0], 2), "olcek": en[1], "dy": en[2]}


def kume_kutusu(fark, bant, x0, x1, esik=FARK_ESIK):
    m = fark[bant[0]:bant[1], x0:x1] > esik
    ys, xs = np.nonzero(m.any(axis=1))[0], np.nonzero(m.any(axis=0))[0]
    return (x0 + int(xs[0]), bant[0] + int(ys[0]),
            x0 + int(xs[-1]) + 1, bant[0] + int(ys[-1]) + 1)


def oge_kes(ref, fark, kutu):
    x0, y0, x1, y1 = kutu
    rgb = np.asarray(ref).astype(np.uint8)[y0:y1, x0:x1]
    al = np.clip((fark[y0:y1, x0:x1] - ALFA_LO) / (ALFA_HI - ALFA_LO), 0, 1) * 255
    return Image.fromarray(np.dstack([rgb, al.astype(np.uint8)]), "RGBA")


def profil_cikar(oge):
    """Kesilen isim ogesinin satir medyan RGB profili (altin dokusu)."""
    a = np.asarray(oge).astype(np.float32)
    m = a[..., 3] > 160
    sat = []
    for y in range(a.shape[0]):
        if m[y].sum() >= 3:
            sat.append(np.median(a[y, m[y], :3], axis=0))
    if len(sat) < 4:
        raise SystemExit("profil cikarilamadi")
    return np.asarray(sat, np.float32)


def altin_isim(mask_img, prof):
    """pilot3 isim dokusu: profil glifin yuksekligine gerilir."""
    m = np.asarray(mask_img).astype(np.float32) / 255.0
    h, w = m.shape
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    g = prof[lo] * (1 - t) + prof[hi] * t
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(np.repeat(g[:, None, :], w, axis=1), 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(o, "RGBA")


def temizle(ref, zemin, kutular, tuy=8):
    t = ref.convert("RGB").copy()
    for (x0, y0, x1, y1) in kutular:
        yama = zemin.crop((x0, y0, x1, y1))
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        m.paste(255, (tuy, tuy, x1 - x0 - tuy, y1 - y0 - tuy))
        t.paste(yama, (x0, y0), m.filter(ImageFilter.GaussianBlur(tuy / 2)))
    return t


# ------------------------------------------------------------ oran kurulum


PROFIL = {}


def profil_yukle(ref_dir):
    """Onayli altin profilleri (ONAYLI.json: cancer/libra_name_gold.png)."""
    global PROFIL
    PROFIL = {"sol": np.asarray(met_al(ref_dir / "cancer_name_gold.png")["prof"], np.float32),
              "sag": np.asarray(met_al(ref_dir / "libra_name_gold.png")["prof"], np.float32)}
    return PROFIL


def oran_kur(oran, olcum_kaydi, bg_im):
    """Bir oranin sabitlerini ve tasinan ogelerini hazirlar."""
    p = HAM / f"{oran}_p{REF_SAYFA}.jpg"
    ham = Image.open(p).convert("RGB")
    ref, k = norm(ham)
    o28 = olcum_kaydi["sayfalar"][str(REF_SAYFA)]
    ozet = olcum_kaydi["ozet"]
    hiza = ince_hiza(ref, bg_im, olcum_kaydi["bg"])
    fark, zemin = fark_haritasi(ref, bg_im, hiza["olcek"], hiza["dy"])

    ib, sb = o28["isim_bant"], o28["sembol_bant"]
    kutu = {"sonsuz": kume_kutusu(fark, ib, *o28["sonsuz"]),
            "sembol_sol": kume_kutusu(fark, sb, *o28["sembol"][0]),
            "sembol_sag": kume_kutusu(fark, sb, *o28["sembol"][1]),
            "isim_sol": kume_kutusu(fark, ib, *o28["sol_isim"]),
            "isim_sag": kume_kutusu(fark, ib, *o28["sag_isim"])}
    oge = {k2: oge_kes(ref, fark, v) for k2, v in kutu.items()}
    prof = PROFIL                      # ONAYLI.json: cancer/libra_name_gold.png
    cap = {"sol": kutu["isim_sol"][3] - kutu["isim_sol"][1],
           "sag": kutu["isim_sag"][3] - kutu["isim_sag"][1]}
    tag_cap = o28["tag_bant"][1] - o28["tag_bant"][0]

    pay = 10
    temiz_kutu = [(kutu[a][0] - pay, kutu[a][1] - pay, kutu[a][2] + pay, kutu[a][3] + pay)
                  for a in ("isim_sol", "sonsuz", "isim_sag", "sembol_sol", "sembol_sag")]
    tk = o28["tag_x"], o28["tag_bant"]
    temiz_kutu.append((tk[0][0] - 16, tk[1][0] - 16, tk[0][1] + 16, tk[1][1] + 16))
    temiz = temizle(ref, zemin, temiz_kutu)

    d = {"oran": oran, "tuval": list(ham.size), "norm": [ref.width, ref.height],
         "olcek": round(1 / k, 4), "bg_hiza": hiza,
         "bosluk": int(round(ozet["bosluk_ort"])),
         "kenar_payi": int(round(NORM_W * KENAR_ORAN)),
         "kullanilabilir": int(NORM_W - 2 * round(NORM_W * KENAR_ORAN)),
         "cap": cap, "tag_cap": tag_cap,
         "tag_sinir": int(round(TAG_TABAN_SINIR * tag_cap / TAG_TABAN_CAP)),
         "sonsuz_w": oge["sonsuz"].width,
         "isim_y": (ib[0] + ib[1]) / 2, "sembol_y": sb[0],
         "tag_y": (o28["tag_bant"][0] + o28["tag_bant"][1]) / 2,
         "kutular": {a: list(b) for a, b in kutu.items()}}
    d["kalinti"] = kalinti_olc(temiz, zemin, temiz_kutu)
    return d, {"ref": ref, "temiz": temiz, "zemin": zemin, "oge": oge, "prof": prof}


def kalinti_olc(temiz, zemin, kutular):
    """Temizlenen alan ile zemin arasindaki fark (kapi <=3)."""
    a = np.asarray(temiz).astype(np.float32)
    b = np.asarray(zemin).astype(np.float32)
    en = 0.0
    for (x0, y0, x1, y1) in kutular:
        f = np.abs(a[y0 + 12:y1 - 12, x0 + 12:x1 - 12]
                   - b[y0 + 12:y1 - 12, x0 + 12:x1 - 12]).mean()
        en = max(en, float(f))
    return round(en, 2)


# --------------------------------------------------------------- yerlesim


def plaka(metin, prof, hedef_cap, olcek=1.0, tam=None):
    fp = FONT_DIR / ISIM_FONT
    tam = tam or cap_icin_boyut(fp, sade(metin), hedef_cap, ISIM_W)
    size = max(int(round(tam * olcek)), 4)
    tr = -0.0388                                  # onayli harf araligi orani
    cr, _ = ciz_metin(font_yukle(fp, size, ISIM_W), metin, size * tr)
    return altin_isim(cr, prof), size, tam


def satir_genislikleri(isimler, s, S, olcek=1.0):
    w, punto = {}, {}
    for y in ("sol", "sag"):
        pl, p, _ = plaka(isimler[y], S["prof"][y], s["cap"][y], olcek)
        w[y], punto[y] = pl.width, p
    return w, punto


def d_olcek(isimler, s, S):
    """Satir kullanilabilir genislige sigmazsa iki isim BIRLIKTE kuculur."""
    hedef = s["kullanilabilir"] - s["sonsuz_w"] - 2 * s["bosluk"]
    olcek = 1.0
    for _ in range(8):
        w, _ = satir_genislikleri(isimler, s, S, olcek)
        if w["sol"] + w["sag"] <= hedef:
            break
        olcek *= max(min(hedef / (w["sol"] + w["sag"]), 0.99), 0.3)
    return olcek


def poster_kur(s, S, isimler, tagline):
    olcek = d_olcek(isimler, s, S)
    pl = {y: plaka(isimler[y], S["prof"][y], s["cap"][y], olcek) for y in ("sol", "sag")}
    w = {y: pl[y][0].width for y in pl}
    inf = S["oge"]["sonsuz"]
    toplam = w["sol"] + s["bosluk"] + inf.width + s["bosluk"] + w["sag"]
    x0 = int(round(NORM_W / 2 - toplam / 2))      # satir butun olarak yuvarlanir
    x = {"sol": x0, "inf": x0 + w["sol"] + s["bosluk"],
         "sag": x0 + w["sol"] + s["bosluk"] + inf.width + s["bosluk"]}
    t = S["temiz"].convert("RGBA").copy()
    merkez = {}
    for y in ("sol", "sag"):
        p = pl[y][0]
        t.alpha_composite(p, (int(round(x[y])), int(round(s["isim_y"] - p.height / 2))))
        merkez[y] = x[y] + p.width / 2
    t.alpha_composite(inf, (int(round(x["inf"])), s["kutular"]["sonsuz"][1]))
    for y, ad in (("sol", "sembol_sol"), ("sag", "sembol_sag")):
        o = S["oge"][ad]
        t.alpha_composite(o, (int(round(merkez[y] - o.width / 2)), s["sembol_y"]))
    tg = tagline_plaka(s, S, tagline)
    t.alpha_composite(tg[0], (int(round(NORM_W / 2 - tg[0].width / 2)),
                              int(round(s["tag_y"] - tg[0].height / 2))))
    bilgi = {"olcek": round(olcek, 3), "punto": [pl["sol"][1], pl["sag"][1]],
             "genislik": [w["sol"], w["sag"]], "satir": round(toplam, 1),
             "kenar": [round(x0, 1), round(NORM_W - x0 - toplam, 1)],
             "merkez": [round(merkez["sol"], 1), round(merkez["sag"], 1)],
             "satir_merkez": round(x0 + toplam / 2, 1),
             "sembol_isim": [0.0, 0.0], "tagline": tg[1]}
    return t, bilgi, merkez, x


def tagline_plaka(s, S, metin):
    fp = FONT_DIR / TAG_FONT
    punto = cap_punto(fp, TAG_W, s["tag_cap"])
    cr, cu, ct = ciz_cap(fp, TAG_W, punto, metin)
    olcek = 1.0
    if cr.width > s["tag_sinir"]:
        olcek = s["tag_sinir"] / cr.width
        punto = max(int(round(punto * olcek)), 4)
        cr, cu, ct = ciz_cap(fp, TAG_W, punto, metin)
    prof1, _ = kuyruk_duzlestir(S["prof"]["sol"])
    return altin_sekil(cr, prof1, (cu, ct)), {"punto": punto, "genislik": cr.width,
                                              "olcek": round(olcek, 3),
                                              "sinir": s["tag_sinir"]}


# ----------------------------------------------------------------- kapilar


def oge_kapisi(poster, S, s, merkez, x):
    yer = {"sonsuz": (int(round(x["inf"])), s["kutular"]["sonsuz"][1]),
           "sembol_sol": (int(round(merkez["sol"] - S["oge"]["sembol_sol"].width / 2)),
                          s["sembol_y"]),
           "sembol_sag": (int(round(merkez["sag"] - S["oge"]["sembol_sag"].width / 2)),
                          s["sembol_y"])}
    out = {}
    for ad, (px, py) in yer.items():
        o = S["oge"][ad]
        yeni = np.asarray(poster.convert("RGB").crop(
            (px, py, px + o.width, py + o.height))).astype(np.float32)
        oa = np.asarray(o).astype(np.float32)
        m = oa[..., 3] > 200
        ic = np.asarray(Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.MinFilter(3))) > 127
        out[ad] = round(float(np.abs(oa[..., :3][ic] - yeni[ic]).mean()), 2) \
            if ic.sum() else 999.0
    return out


def isim_sekil_kapisi(poster, s):
    """Hizalanmis sekil/doku kapisi (mutlak konum olculmez).

    Onayli 4:5 isim satirindaki SOL isim ile posterdeki sol isim ayni cap
    yuksegine getirilir; sekil IoU ve satir medyan RGB (doku) farki olculur.
    """
    onay = Image.open(ONAYLI_DIR / "ISIM_SATIRI_ALTIN.png").convert("RGB")
    ao = np.asarray(onay).astype(np.float32)
    ko = kumeler((ao @ LUMA) > 40, 12)
    if not ko:
        return {"gecti": False, "sebep": "onayli kirpimda kume yok"}
    bo = bbox_of(((ao @ LUMA) > 40)[:, ko[0][0]:ko[0][1]])
    onay_sol = onay.crop((ko[0][0] + bo[0], bo[1], ko[0][0] + bo[2], bo[3]))

    P = poster.convert("RGB")
    a = np.asarray(P).astype(np.float32)
    mp = (a @ LUMA) > 40
    pay = int(max(90, max(s["cap"].values()) * 1.6))
    y0, y1 = int(s["isim_y"] - pay), int(s["isim_y"] + pay)
    kp = [c for c in kumeler(mp[y0:y1], 20) if c[1] - c[0] > 40]
    if len(kp) != 3:
        return {"gecti": False, "sebep": f"posterde {len(kp)} kume"}
    bp = bbox_of(mp[y0:y1, kp[0][0]:kp[0][1]])
    yeni_im = P.crop((kp[0][0] + bp[0], y0 + bp[1], kp[0][0] + bp[2], y0 + bp[3]))

    H = 200
    W = max(int(round(onay_sol.width * H / onay_sol.height)), 4)
    o = onay_sol.resize((W, H), Image.LANCZOS)
    n = yeni_im.resize((W, H), Image.LANCZOS)      # ayni kutuya getirilir
    oa, na = np.asarray(o).astype(np.float32), np.asarray(n).astype(np.float32)
    mo, mn = (oa @ LUMA) > 40, (na @ LUMA) > 40
    iou = float((mo & mn).sum()) / max(float((mo | mn).sum()), 1.0)
    # Doku: her satirin murekkep medyani (kenar pikselleri disarida kalir, bu
    # yuzden olcek/yeniden orneklemeden etkilenmez).
    def profil(arr, mask):
        sat = []
        for y in range(arr.shape[0]):
            if mask[y].sum() >= 3:
                sat.append(np.median(arr[y, mask[y], :3], axis=0))
            else:
                sat.append(np.full(3, np.nan))
        return np.asarray(sat, np.float32)

    po, pn = profil(oa, mo), profil(na, mn)
    ok = ~(np.isnan(po).any(axis=1) | np.isnan(pn).any(axis=1))
    doku = float(np.abs(po[ok] - pn[ok]).mean()) if ok.sum() else 999.0
    ic = np.asarray(Image.fromarray(((mo & mn) * 255).astype(np.uint8), "L").filter(
        ImageFilter.MinFilter(5))) > 127
    piksel = float(np.abs(oa[ic] - na[ic]).mean()) if ic.sum() else 999.0
    return {"gecti": bool(doku <= 3.0), "iou": round(iou, 3),
            "doku_fark": round(doku, 2), "piksel_fark": round(piksel, 2),
            "satir": int(ok.sum()), "genislik": [o.width, n.width]}


def yerlesim_kapisi(poster, s, bilgi, merkez, x, inf_w):
    """Satir merkezi +-1 px, sembol-isim merkez farki <=2 px.

    Kapi YERLESIM geometrisiyle karara baglanir (cizim niyeti). Ayrica ayni
    olcum posterin murekkebinden de yapilir ve bilgi olarak raporlanir; o olcum
    harflerin kenar yumusatmasina duyarlidir (referansin kendisi de sifir vermez).
    """
    d = {"satir_merkez": bilgi["satir_merkez"],
         "merkez_sapma": round(bilgi["satir_merkez"] - NORM_W / 2, 1),
         "sembol_isim": [0.0, 0.0]}
    a = np.asarray(poster.convert("RGB")).astype(np.float32)
    m = (a @ LUMA) > MUREKKEP
    y0, y1 = int(s["isim_y"] - 80), int(s["isim_y"] + 80)
    km = [c for c in kumeler(m[y0:y1], 20) if c[1] - c[0] > 40]
    sy0, sy1 = int(s["sembol_y"]), int(s["sembol_y"] + max(
        s["kutular"]["sembol_sol"][3] - s["kutular"]["sembol_sol"][1],
        s["kutular"]["sembol_sag"][3] - s["kutular"]["sembol_sag"][1]) + 10)
    sk = [c for c in kumeler(m[sy0:sy1], 20) if c[1] - c[0] > 30]
    if len(km) == 3:
        d["olculen_satir_merkez"] = round((km[0][0] + km[2][1]) / 2, 1)
        d["olculen_sapma"] = round(d["olculen_satir_merkez"] - NORM_W / 2, 1)
        im = [round((km[0][0] + km[0][1]) / 2, 1), round((km[2][0] + km[2][1]) / 2, 1)]
        if len(sk) >= 2:
            sm = [round((sk[0][0] + sk[0][1]) / 2, 1), round((sk[-1][0] + sk[-1][1]) / 2, 1)]
            d["olculen_sembol_isim"] = [round(sm[i] - im[i], 1) for i in (0, 1)]
    d["gecti"] = bool(abs(d["merkez_sapma"]) <= 1.0
                      and max(abs(v) for v in d["sembol_isim"]) <= 2.0)
    return d


# ------------------------------------------------------------------ sinir


def sinir_olc(s, S):
    d = {}
    hedef = s["kullanilabilir"] - s["sonsuz_w"] - 2 * s["bosluk"]
    d["iki_isme_kalan"] = hedef
    px = {y: float(np.mean([plaka(a, S["prof"][y], s["cap"][y])[0].width / len(a)
                            for a in ADLAR])) for y in ("sol", "sag")}
    d["px_harf"] = {k: round(v, 1) for k, v in px.items()}

    def gen(y, metin):
        return plaka(metin, S["prof"][y], s["cap"][y])[0].width

    esit_m = 0
    for k in range(1, 20):
        if gen("sol", "M" * k) + gen("sag", "M" * k) <= hedef:
            esit_m = k
        else:
            break
    d["esit_M"] = esit_m
    d["esit_normal"] = int(hedef / (px["sol"] + px["sag"]))
    for karsi in (3, 6):
        kw = gen("sag", "ECE" if karsi == 3 else "MEHMET")
        tek_m = 0
        for k in range(1, 24):
            if gen("sol", "M" * k) + kw <= hedef:
                tek_m = k
            else:
                break
        d[f"karsi{karsi}_M"] = tek_m
        d[f"karsi{karsi}_normal"] = int((hedef - kw) / px["sol"])
    # tagline
    fp = FONT_DIR / TAG_FONT
    punto = cap_punto(fp, TAG_W, s["tag_cap"])
    d["tag_punto"] = punto
    sat = []
    for t in TAGLINELER:
        cr, _, _ = ciz_cap(fp, TAG_W, punto, t)
        sat.append({"metin": t, "karakter": len(t), "genislik": cr.width,
                    "sigdi": cr.width <= s["tag_sinir"]})
    d["tag_satirlar"] = sat
    oran = [x["genislik"] / x["karakter"] for x in sat]
    d["tag_px_karakter"] = {"ort": round(float(np.mean(oran)), 2),
                            "maks": round(float(np.max(oran)), 2)}
    d["tag_azami_normal"] = int(s["tag_sinir"] / np.mean(oran))
    d["tag_azami_genis"] = int(s["tag_sinir"] / np.max(oran))
    return d


def etsy_onerisi(sabit, sinir):
    """Tum oranlarda tam boy kalacak TEK sinir; en dar oran belirler."""
    n = min(sinir[o]["esit_normal"] for o in sinir)
    n_m = min(sinir[o]["esit_M"] for o in sinir)
    t = min(sinir[o]["tag_azami_genis"] for o in sinir)
    belirleyen_n = min(sinir, key=lambda o: sinir[o]["esit_normal"])
    belirleyen_t = min(sinir, key=lambda o: sinir[o]["tag_azami_genis"])
    kucul = {}
    for o in sinir:
        hedef = sabit[o]["kullanilabilir"] - sabit[o]["sonsuz_w"] - 2 * sabit[o]["bosluk"]
        pxh = sinir[o]["px_harf"]
        en_kotu = (pxh["sol"] + pxh["sag"]) * n * 1.0
        kucul[o] = {"normal_doluluk": round(100 * en_kotu / hedef, 1),
                    "M_sigar_mi": sinir[o]["esit_M"] >= n_m}
    return {"isim_harf": n, "isim_harf_M": n_m, "tagline_karakter": t,
            "belirleyen_isim": belirleyen_n, "belirleyen_tagline": belirleyen_t,
            "doluluk": kucul}


# -------------------------------------------------------------------- akis


def kaydet(im, p, maks=2_200_000):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80):
        im.save(p, "JPEG", quality=q, subsampling=1, optimize=True)
        if p.stat().st_size <= maks:
            break
    return p


def en_uzun_ad(s, S, n):
    """n harfe sigan gercekci en uzun ad cifti."""
    havuz = {6: ("SERDAR", "MEHMET"), 7: ("WILLIAM", "GÜLİZAR"),
             8: ("JONATHAN", "MUHAMMED"), 9: ("ELIZABETH", "ALEXANDRA"),
             10: ("MAXIMILIAN", "WILHELMINA"), 11: ("CHRISTOPHER", "ABDURRAHMAN"),
             5: ("SELIM", "DERYA"), 4: ("LENA", "MARK"), 3: ("ECE", "ADA")}
    n = max(3, min(n, 11))
    return havuz.get(n, ("SERDAR", "LENA"))


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    if not a.yerel:
        HAM.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST_O}/ham", str(HAM))
        rc("copy", f"{DEST_O}/OLCUM.json", str(YOL))
        (OUT / "hazir").mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST}/HAZIR/bg.png", str(OUT / "hazir"))
        log("ham sayfalar + OLCUM.json + bg.png indi")
    refd = OUT / "ref" / "names"
    if not a.yerel:
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, refd)
    profil_yukle(refd)
    olcum = json.loads((YOL / "OLCUM.json").read_text(encoding="utf-8"))
    bg_im = Image.open(OUT / "hazir" / "bg.png")
    oranlar = [o for o in ORANLAR if o in olcum and (HAM / f"{o}_p{REF_SAYFA}.jpg").exists()]
    log(f"islenecek oranlar: {oranlar}")

    sabit, sinir, kapi, poster_bilgi, kucukler = {}, {}, {}, {}, {}
    for oran in oranlar:
        s, S = oran_kur(oran, olcum[oran], bg_im)
        sabit[oran] = s
        log(f"{oran}: tuval {s['tuval']} bosluk {s['bosluk']} kenar {s['kenar_payi']} "
            f"cap {s['cap']} tag_cap {s['tag_cap']} tag_sinir {s['tag_sinir']} "
            f"bg {s['bg_hiza']} kalinti {s['kalinti']}")

        # 1) altin poster: SERDAR - LENA
        p, bilgi, merkez, x = poster_kur(s, S, {"sol": CIFT[0], "sag": CIFT[1]},
                                         TAGLINES["A"])
        ad = YOL / f"ALTIN_{oran}.jpg"
        kaydet(p, ad)
        poster_bilgi[oran] = bilgi
        kapi[oran] = {"oge": oge_kapisi(p, S, s, merkez, x),
                      "yerlesim": yerlesim_kapisi(p, s, bilgi, merkez, x,
                                                  S["oge"]["sonsuz"].width),
                      "kalinti": s["kalinti"],
                      "isim_sekli": isim_sekil_kapisi(p, s)}
        log(f"{oran} ALTIN: punto {bilgi['punto']} satir {bilgi['satir']} "
            f"kenar {bilgi['kenar']} tagline {bilgi['tagline']}")
        log(f"{oran} kapilar: oge {kapi[oran]['oge']} "
            f"yerlesim sapma {kapi[oran]['yerlesim']['merkez_sapma']} "
            f"(olculen {kapi[oran]['yerlesim'].get('olculen_sapma')}) sembol olculen "
            f"{kapi[oran]['yerlesim'].get('olculen_sembol_isim')} kalinti {s['kalinti']} "
            f"sekil iou {kapi[oran]['isim_sekli'].get('iou')} "
            f"doku {kapi[oran]['isim_sekli'].get('doku_fark')}")

        # 2) sinir olcumu
        sinir[oran] = sinir_olc(s, S)
        log(f"{oran} sinir: esit {sinir[oran]['esit_normal']} normal / "
            f"{sinir[oran]['esit_M']} M harf, tagline {sinir[oran]['tag_azami_normal']} / "
            f"{sinir[oran]['tag_azami_genis']} karakter")
        sabit[oran]["_S"] = S                       # sonraki asamada lazim

    oneri = etsy_onerisi(sabit, sinir)
    log(f"ETSY ONERISI: isim {oneri['isim_harf']} harf (M: {oneri['isim_harf_M']}), "
        f"tagline {oneri['tagline_karakter']} karakter; belirleyen "
        f"{oneri['belirleyen_isim']} / {oneri['belirleyen_tagline']}")

    # 3) sinir ornekleri
    tag_ornek = max((t for t in TAGLINELER
                     if len(t) <= oneri["tagline_karakter"]), key=len, default=TAGLINES["A"])
    cift = en_uzun_ad(None, None, oneri["isim_harf"])
    for oran in oranlar:
        s = sabit[oran]
        p, bilgi, _, _ = poster_kur(s, s["_S"], {"sol": cift[0], "sag": cift[1]}, tag_ornek)
        kaydet(p, YOL / f"SINIR_ORNEK_{oran}.jpg")
        kucukler[oran] = p.convert("RGB").resize(
            (560, int(round(560 * p.height / p.width))), Image.LANCZOS)
        poster_bilgi[oran]["sinir_ornek"] = {
            "cift": list(cift), "tagline": tag_ornek, "olcek": bilgi["olcek"],
            "punto": bilgi["punto"], "satir": bilgi["satir"], "kenar": bilgi["kenar"],
            "tagline_bilgi": bilgi["tagline"]}
        log(f"{oran} SINIR_ORNEK: {cift} / {tag_ornek[:30]} olcek %{bilgi['olcek'] * 100:.0f}")

    kiyas(kucukler, oranlar, cift, tag_ornek)
    d = {"sabit": {o: {k: v for k, v in sabit[o].items() if k != "_S"} for o in oranlar},
         "poster": poster_bilgi, "sinir": sinir, "kapi": kapi, "oneri": oneri,
         "ornek": {"cift": list(cift), "tagline": tag_ornek}}
    (YOL / "oranlar.json").write_text(json.dumps(d, ensure_ascii=False, indent=1,
                                                 default=str), encoding="utf-8")
    sabitler_json(sabit, oranlar)
    rapor(d, oranlar)
    if not a.yerel:
        rc("copy", str(YOL), DEST_O, "--exclude", "ham/**")
        log(f"Drive <- {DEST_O}")
    return d


def sabitler_json(sabit, oranlar):
    d = {"_": "pilot11/pilot12 olcumunden turetildi (21 Eylul 2026). Olcu birimi: "
              "poster genisligi 2400 px'e normalize edilmis piksel.",
         "oranlar": {}}
    for o in oranlar:
        s = sabit[o]
        d["oranlar"][o] = {"tuval": s["tuval"], "bosluk": s["bosluk"],
                           "kenar_payi": s["kenar_payi"],
                           "kullanilabilir_genislik": s["kullanilabilir"],
                           "isim_cap": s["cap"], "tagline_cap": s["tag_cap"],
                           "tagline_genislik_siniri": s["tag_sinir"],
                           "sonsuzluk_genisligi": s["sonsuz_w"],
                           "bg_hizasi": s["bg_hiza"]}
    (YOL / "ORAN_SABITLERI.json").write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                             encoding="utf-8")


def kiyas(kucukler, oranlar, cift, tag):
    et = font_yukle(FONT_DIR / ISIM_FONT, 26, ISIM_W)
    bas, w = 40, 560
    h = max(k.height for k in kucukler.values()) if kucukler else 700
    im = Image.new("RGB", (w * len(oranlar), h + bas), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for i, o in enumerate(oranlar):
        dd.text((i * w + 12, 6), f"Blue {o}", fill=(214, 178, 96), font=et)
        im.paste(kucukler[o], (i * w, bas))
    kaydet(im, YOL / "ORAN_KIYAS.jpg", maks=2_000_000)
    log(f"ORAN_KIYAS.jpg {im.size}")


def rapor(d, oranlar):
    sa, si, ka, po, on = d["sabit"], d["sinir"], d["kapi"], d["poster"], d["oneri"]
    m = ["# Bes oran - SECENEK D olcumu, sinirlari ve altin posterleri", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "**YOK** - ONAYLI.json'daki onayli ogeler degistirilmedi; bu kosu olcum ve "
         "ornek uretir. (Kararin kendisi - SECENEK D, kapilar - ayri commit'te "
         "ONAYLI.json'a islendi.)", "",
         "### Degismeyen", "",
         "- Zemin, logo, yildizlar; sonsuzluk ve kucuk semboller (referans sayfadan "
         "kesilip tasindi, yeniden cizilmedi)",
         "- Isim dokusu: her oranin KENDI sayfa 28'inden cikarilan altin profili",
         "- Tagline SECENEK 1 dokusu ve metin A", "",
         "## Olcum: her oranin sabitleri", "",
         "Olcu birimi: poster genisligi 2400 px'e normalize edilmis piksel.", "",
         "| oran | tuval | isim-sonsuzluk boslugu | kenar payi | kullanilabilir satir "
         "| isim cap (sol/sag) | tagline cap | tagline sinir | bg medyan fark |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for o in oranlar:
        s = sa[o]
        m.append(f"| Blue {o} | {s['tuval'][0]}x{s['tuval'][1]} | {s['bosluk']} "
                 f"| {s['kenar_payi']} | {s['kullanilabilir']} "
                 f"| {s['cap']['sol']} / {s['cap']['sag']} | {s['tag_cap']} "
                 f"| {s['tag_sinir']} | {s['bg_hiza']['medyan_fark']} |")
    m += ["", "Kenar payi, o oranin en genis orijinal satirindan (sayfa 72, "
          "SAGITTARIUS_VIRGO) olculdu. Tagline sinir = 4:5'te onayli 1670 px, o oranin "
          "tagline cap yuksekligiyle olceklendi.", "",
          "## Kapilar", "",
          "| oran | satir merkezi sapmasi (<=1) | sembol-isim (<=2) | tasinan oge farki "
          "(<=3) | kalinti (<=3) | isim sekli (IoU>=0.95, doku<=3) |",
          "| --- | --- | --- | --- | --- | --- |"]
    for o in oranlar:
        k = ka[o]
        og = k["oge"]
        m.append(f"| Blue {o} | {k['yerlesim']['merkez_sapma']} "
                 f"(murekkepten {k['yerlesim'].get('olculen_sapma')}) "
                 f"| {k['yerlesim']['sembol_isim']} "
                 f"(murekkepten {k['yerlesim'].get('olculen_sembol_isim')}) "
                 f"| {og['sonsuz']} / {og['sembol_sol']} / {og['sembol_sag']} "
                 f"| {k['kalinti']} | IoU {k['isim_sekli'].get('iou')}, "
                 f"doku {k['isim_sekli'].get('doku_fark')} |")
    m += ["", "Isim sekli kapisi mutlak konumu degil, hizalanmis kirpimda sekil ve "
          "dokuyu olcer (onayli 4:5 isim satiriyla; farkli oranlarda onayli kirpim "
          "boyuta getirilir).", "",
          "## Sinirlar (tam boy, kucultme yok)", "",
          "| oran | iki isme kalan px | esit uzunlukta normal | esit uzunlukta en genis (M) "
          "| karsi 3 harf iken | karsi 6 harf iken | tagline normal | tagline en genis |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for o in oranlar:
        s = si[o]
        m.append(f"| Blue {o} | {s['iki_isme_kalan']} | {s['esit_normal']}+{s['esit_normal']} "
                 f"| {s['esit_M']}+{s['esit_M']} | {s['karsi3_normal']} ({s['karsi3_M']} M) "
                 f"| {s['karsi6_normal']} ({s['karsi6_M']} M) | {s['tag_azami_normal']} "
                 f"| {s['tag_azami_genis']} |")
    m += ["", "## Tagline cumleleri (13 cumle, her oranda)", "", "| karakter | metin |"
          + "".join(f" {o} px |" for o in oranlar),
          "| --- | --- |" + "".join(" --- |" for _ in oranlar)]
    for i, t in enumerate(si[oranlar[0]]["tag_satirlar"]):
        satir = f"| {t['karakter']} | {t['metin']} |"
        for o in oranlar:
            x = si[o]["tag_satirlar"][i]
            satir += f" {x['genislik']}{'' if x['sigdi'] else ' TASTI'} |"
        m.append(satir)
    m += ["", "## ETSY ONERISI (tum oranlarda tam boy)", "",
          f"- **Her isim en fazla {on['isim_harf']} harf** "
          f"(en genis harflerle - M/W - {on['isim_harf_M']} harf). "
          f"Belirleyen oran: Blue {on['belirleyen_isim']}.",
          f"- **Tagline en fazla {on['tagline_karakter']} karakter** (en genis harflerle "
          f"bile tam boy). Belirleyen oran: Blue {on['belirleyen_tagline']}.", "",
          "En kotu durumda (onerilen sinirda, ortalama harf genisligiyle) satir doluluk "
          "orani:", "", "| oran | doluluk % | en genis harflerle sigar mi |",
          "| --- | --- | --- |"]
    for o in oranlar:
        v = on["doluluk"][o]
        m.append(f"| Blue {o} | {v['normal_doluluk']} | "
                 f"{'evet' if v['M_sigar_mi'] else 'HAYIR - kuculur'} |")
    m += ["", "## Uretilen posterler", "",
          "| oran | ALTIN (SERDAR - LENA) punto | olcek | satir px | kenar px "
          "| tagline punto/genislik |", "| --- | --- | --- | --- | --- | --- |"]
    for o in oranlar:
        p = po[o]
        m.append(f"| Blue {o} | {p['punto'][0]} / {p['punto'][1]} | %{p['olcek'] * 100:.0f} "
                 f"| {p['satir']} | {p['kenar'][0]} / {p['kenar'][1]} "
                 f"| {p['tagline']['punto']} / {p['tagline']['genislik']} |")
    m += ["", f"SINIR_ORNEK_<oran>.jpg: {d['ornek']['cift'][0]} - {d['ornek']['cift'][1]} "
          f"ve \"{d['ornek']['tagline']}\".",
          "ORAN_KIYAS.jpg: bes oranin sinir ornegi yan yana.", ""]
    (YOL / "SINIR_ORANLAR.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    log("SINIR_ORANLAR.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
