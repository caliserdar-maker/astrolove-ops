#!/usr/bin/env python3
"""WALLPAPER KISISELLESTIRME V2 (Serdar 25 Eyl 2026 karari).

"Sil-yeniden yaz" IPTAL. Yeni yol, gece hattinin kendi parcalariyla:
  zemin  = WP_PLATES/CLEAN/PLATE_<ED>_<DEV>_CLEAN.png   (yazisiz, ogesiz)
  murekkep (poster olceginde 7200x9600, tek katman):
     - ciftin murekkebi  : wp_build_pair.diff_ink_mask(poster, MEDIAN_<ED>) -> sembol,
                           glifler, ∞ ve isimler; ISIM SATIRI cikarilir (∞ kalir)
     - halka             : MEDIAN'daki murekkep renkli pikseller (INK_RGB/INK_TOL),
                           halka bandi icinde (POSTER_CLEAN plaka 3000x4000 kucultulmus,
                           poster olceginde kullanilamaz - 25 Eyl olcumu)
     - yeni isimler/mesaj: kisisel-v1 onayli render (Cinzel 500 / EB Garamond Italic),
                           altin doku o edisyonun KENDI posterinden olculur
  yerlesim = wp_plate_pilot.placement (WP_LAYOUT_SPEC 7.1) + GEOM yan dosyasi,
             wp_build_pair.place ile birebir ayni yol. Parlama (glow) YOK:
             maske disinda cikti = CLEAN plaka (kapi 1).

∞ SABIT KUTUYLA (REF_INFINITY) DEGIL, isim satirinda OLCULEN ORTA KUME olarak
alinir (25 Eyl 2026, 3. iterasyon duzeltmesi): REF_INFINITY pilot posterin
(Cancer_Libra) olcumudur ve ARIES_LEO ∞'unu tam kapsamaz.

∞ yalnizca YATAYDA tam sayi piksel kayar: tasarim kurali "satir ortali + esit
bosluk"tur (olcum: ARIES 252 / LEO 196 px, bosluk 57/55, satir merkezi 726 ~
tuval merkezi 720). Isimler degisince esit bosluk ve ortalama ancak ∞ ile
birlikte saglanir; kaydirma tam sayidir, piksel birebir kopyalanir.
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
from wp_mockup_common import DEVICES, imread                                  # noqa: E402
import wp_build_pair as WBP                                                   # noqa: E402
from wp_plate_pilot import (BOX_NAMES, INF_PAD, INK_RGB,                          # noqa: E402
                            REF_TAGLINE, RING_BAND, RING_ELLIPSE, RING_LINE_PX, RING_TIP_Y, placement)

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
POSTER_W, POSTER_H = 7200, 9600
GOVDE_ORAN = 0.25        # govde satiri: murekkep >= medyan satirin %25'i (a1_poster kurali)
KENAR_ORAN = 0.08        # mesaj kenar payi: tuval genisliginin %8'i (Serdar kapisi)
# Kapi 2 olcum kutulari (poster px, WP_LAYOUT_SPEC 7.1 / wp_plate_pilot):
BOX_SYMBOL_RING = (900, 1100, 6300, 5696)     # halka yayi + ici (glif satirinin ustunde biter)
BOX_SYMBOL_CORE = (1900, 1900, 5300, 5100)    # fuzyon sembolu (3 parca birlesimi)
ESIK_OGE = 60        # halka/sembol olcumu: zemin doku sapmasinin (<=40) uzerinde, murekkep kesin
ESIK_METIN = 32      # isim/mesaj kenar olcumu: JPEG q95 halkalanmasinin (<=15) uzerinde
EDISYONLAR = ["Midnight_Blue", "Deep_Black", "Champagne_Ivory", "Warm_Parchment"]
CIHAZLAR = ["Phone", "Tablet", "Desktop"]


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ olcum
def kutu_maske(sekil, kutu):
    m = np.zeros(sekil[:2], np.uint8)
    x0, y0, x1, y1 = kutu
    m[max(y0, 0):y1 + 1, max(x0, 0):x1 + 1] = 1
    return m


def bbox(m):
    ys, xs = np.nonzero(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(ys) else None


def govde(m, x0, x1):
    """Inen kuyruklar haric en uzun kesintisiz govde bandi (satir profilinden)."""
    sat = m[:, x0:x1].sum(1).astype(np.float32)
    poz = sat[sat > 0]
    if not len(poz):
        return None
    ok = sat >= GOVDE_ORAN * np.median(poz)
    en, kos, i = 0, None, 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]:
                j += 1
            if j - i > en:
                en, kos = j - i, (i, j)
            i = j
        else:
            i += 1
    return kos


def murekkep_rengi(img_bgr, ed, kutu=None):
    """Olculen murekkep rengine (INK_RGB) INK_TOL'den yakin pikseller.

    Sabit ogeler (halka, tagline) MEDIAN'da vardir; ayri "temiz" referans
    gerekmez - gece hattinin kendi renk kurali kullanilir.
    """
    r, g, b = INK_RGB[ed]
    h, w = img_bgr.shape[:2]
    m = np.zeros((h, w), bool)
    x0, y0, x1, y1 = kutu if kutu else (0, 0, w, h)
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, w), min(y1, h)
    b_ = img_bgr[y0:y1, x0:x1].astype(np.int16) - np.array([b, g, r], np.int16)
    m[y0:y1, x0:x1] = (b_ ** 2).sum(2) < WBP.INK_TOL * WBP.INK_TOL
    return m


def sutun_kumeleri(maske, kopr=40, en_az=60):
    """Sutun projeksiyonunda bitisik murekkep kumeleri (kopr px'e kadar bosluk koprulenir)."""
    sut = maske.any(0)
    kume, i = [], 0
    while i < len(sut):
        if sut[i]:
            j = i
            while j < len(sut) and (sut[j] or (j + kopr < len(sut) and sut[j:j + kopr].any())):
                j += 1
            kume.append((int(i), int(j))); i = j
        else:
            i += 1
    return [k for k in kume if k[1] - k[0] >= en_az]


def uc_grup(kume):
    """Isim satirini [sol isim | ∞ | sag isim] olarak ayirir.

    KURAL (Serdar 25 Eyl 2026, 4. deneme): kume SAYISI sabitlenmez. Ardisik
    bosluklarin EN BUYUK IKISI secilir; aralarinda kalan kume(ler) = ∞, solunda
    kalanlar = sol isim, saginda kalanlar = sag isim. Boylece harf araligi
    (olcum: 46 px) kume birlestirme esigini assa bile isim bolunmez.
    """
    if len(kume) < 3:
        raise SystemExit(f"HATA: isim satirinda en az 3 kume gerekli, {len(kume)}: {kume}")
    bosluk = [kume[i + 1][0] - kume[i][1] for i in range(len(kume) - 1)]
    sira = sorted(range(len(bosluk)), key=lambda i: -bosluk[i])
    i1, i2 = sorted(sira[:2])
    kalan = max([bosluk[i] for i in sira[2:]], default=0)
    secilen = min(bosluk[i1], bosluk[i2])
    if secilen < 2 * kalan:
        raise SystemExit(f"HATA: isim/∞ ayrimi belirsiz - secilen bosluk {secilen}, "
                         f"kalan en buyuk {kalan}, kumeler {kume}, bosluklar {bosluk}")
    grup = [kume[:i1 + 1], kume[i1 + 1:i2 + 1], kume[i2 + 1:]]
    sol, orta, sag = [(g[0][0], g[-1][1]) for g in grup]
    return sol, orta, sag, {"kume": kume, "bosluk": bosluk, "secilen": [bosluk[i1], bosluk[i2]],
                            "kalan_en_buyuk": int(kalan),
                            "grup": [len(g) for g in grup], "sol": list(sol), "sonsuz": list(orta),
                            "sag": list(sag)}


def metin_olcumu(poster, median, ed):
    """Poster olceginde isim satiri, ∞ ve mesaj satirinin OLCULEN geometrisi."""
    d_c = np.abs(poster.astype(np.int16) - median.astype(np.int16)).max(2) > WBP.DIFF_THR
    d_s = murekkep_rengi(median, ed, REF_TAGLINE)
    satir = (d_c & (kutu_maske(poster.shape, BOX_NAMES) > 0))
    tag = (d_s & (kutu_maske(poster.shape, REF_TAGLINE) > 0))
    for ad, m in (("isim satiri", satir), ("mesaj", tag)):
        if not m.any():
            raise SystemExit(f"HATA: {ad} murekkebi olculemedi")
    sol, orta, sag, kbilgi = uc_grup(sutun_kumeleri(satir))
    sut_ix = np.arange(poster.shape[1])
    inf = satir & ((sut_ix >= orta[0]) & (sut_ix < orta[1]))
    isim = satir & ~inf
    g0, g1 = govde(isim, sol[0], sag[1])
    t = bbox(tag); tg = govde(tag, t[0], t[2])
    return {
        "isim_kutu": bbox(isim), "sol": list(sol), "sag": list(sag),
        "isim_govde": [int(g0), int(g1)], "cap": int(g1 - g0),
        "sonsuz": list(bbox(inf)),
        "mesaj_kutu": list(t), "mesaj_govde": [int(tg[0]), int(tg[1])], "mesaj_cap": int(tg[1] - tg[0]),
        "kume": kbilgi,
    }, isim, inf


def profil(img_bgr, maske, kutu):
    """Satir medyan RGB profili (altin doku) - kaynak posterin kendi murekkebinden."""
    x0, y0, x1, y1 = kutu
    sat = []
    for y in range(y0, y1):
        m = maske[y, x0:x1]
        if m.sum() >= 3:
            sat.append(np.median(img_bgr[y, x0:x1][m][:, ::-1], axis=0))   # BGR -> RGB
    if len(sat) < 4:
        raise SystemExit("HATA: altin profili cikarilamadi")
    return np.asarray(sat, np.float32)


# ------------------------------------------------------------------ render (kisisel-v1, degistirilmez)
def kisisel_kur(kok):
    sys.path.insert(0, str(Path(kok) / "scripts" / "kisisel"))
    import pilot6, pilot7, pilot12
    import kisisel_pilot as kp
    return pilot6, pilot7, pilot12, kp


def plaka_murekkep(pl):
    """Plakanin YATAY murekkep sinirlari (alfa/maske >40) - yan bosluklar haric.

    kisisel-v1 render'i plakayi zaten >40 esiginde kirpar; bu olcum kuralin
    ACIK yazilmis halidir (EK KAPI 3: sol/sag bosluk esit).
    """
    a = np.asarray(pl)
    a = a[..., 3] if (a.ndim == 3 and a.shape[2] == 4) else (a if a.ndim == 2 else a.max(2))
    sut = np.nonzero((a > 40).any(0))[0]
    if not len(sut):
        raise SystemExit("HATA: plakada murekkep yok")
    return int(sut.min()), int(sut.max()) + 1


def plaka_govde(pl):
    """Plakanin govde bandi ve murekkep merkezi (yatay)."""
    a = np.asarray(pl)[..., 3]
    m = a > 40
    kos = govde(m.astype(np.uint8), 0, m.shape[1])
    sut = m.sum(0).astype(np.float32)
    return kos, float((sut * np.arange(len(sut))).sum() / max(sut.sum(), 1))


def metin_katmani(P6, P7, P12, kp, geo, prof, isimler, mesaj):
    """Poster olceginde yeni isimler + mesaj: RGBA plakalar ve yerleri.

    Isim satiri: olculen bosluk (isim-∞) korunur, satir TUVALDE ORTALANIR;
    bunun icin ∞ tam sayi piksel kadar yatayda kayar (dx doner).
    """
    cap = geo["cap"]
    pl = {y: P12.plaka(isimler[y], prof[y], cap, 1.0)[0] for y in ("sol", "sag")}
    mrk = {y: plaka_murekkep(pl[y]) for y in ("sol", "sag")}   # yan bosluk haric murekkep
    g_sol = geo["sonsuz"][0] - geo["sol"][1]
    g_sag = geo["sag"][0] - geo["sonsuz"][2]
    g = int(round((g_sol + g_sag) / 2))                     # esit bosluk (tasarim kurali)
    w_inf = geo["sonsuz"][2] - geo["sonsuz"][0]
    w_sol, w_sag = (mrk["sol"][1] - mrk["sol"][0]), (mrk["sag"][1] - mrk["sag"][0])
    # EK KAPI 3: sol/sag bosluk ESIT -> satir MUREKKEP sinirlarina gore ortalanir
    toplam = w_sol + g + w_inf + g + w_sag
    i0 = int(round(POSTER_W / 2 - toplam / 2))              # satirin murekkep sol kenari
    yer = {"sol": i0 - mrk["sol"][0], "inf": i0 + w_sol + g,
           "sag": i0 + w_sol + g + w_inf + g - mrk["sag"][0]}
    dx_inf = yer["inf"] - geo["sonsuz"][0]

    yerlesim, kutular = [], {}
    for y in ("sol", "sag"):
        (b0, b1), _ = plaka_govde(pl[y])
        py = int(round((geo["isim_govde"][0] + geo["isim_govde"][1]) / 2 - (b0 + b1) / 2))
        yerlesim.append((pl[y], yer[y], py))
        kutular[y] = [yer[y] + mrk[y][0], py, yer[y] + mrk[y][1], py + pl[y].height]

    # mesaj: kenar payi tuval genisliginin %8'i (cihazda) -> poster olceginde en dar cihaz belirler
    pay = max(int(round(KENAR_ORAN * DEVICES[d][0] / placement(d)[0])) for d in ("Phone", "Tablet"))
    sinir = POSTER_W - 2 * pay
    fp = kp.FONT_DIR / P6.TAG_FONT
    punto = P6.cap_punto(fp, P6.TAG_W, geo["mesaj_cap"])
    cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, mesaj)
    olcek = 1.0
    mx0, mx1 = plaka_murekkep(cr)
    if mx1 - mx0 > sinir:
        olcek = sinir / (mx1 - mx0)
        punto = max(int(round(punto * olcek)), 4)
        cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, mesaj)
        mx0, mx1 = plaka_murekkep(cr)
    p1, _ = P7.kuyruk_duzlestir(prof["tag"])
    tg = P7.altin_sekil(cr, p1, (cu, ct))
    (tb0, tb1), tmx = plaka_govde(tg)
    tx = int(round(POSTER_W / 2 - (mx0 + mx1) / 2))          # EK KAPI 3: murekkebe gore ortali
    ty = int(round((geo["mesaj_govde"][0] + geo["mesaj_govde"][1]) / 2 - (tb0 + tb1) / 2))
    yerlesim.append((tg, tx, ty))
    kutular["mesaj"] = [tx + mx0, ty, tx + mx1, ty + tg.height]
    bilgi = {"bosluk": [int(g_sol), int(g_sag), g], "satir": int(toplam), "dx_sonsuz": int(dx_inf),
             "isim_murekkep": [w_sol, w_sag, int(w_inf)],
             "mesaj_punto": punto, "mesaj_olcek": round(olcek, 3), "mesaj_genislik": int(mx1 - mx0),
             "mesaj_sinir": int(sinir), "mesaj_kenar_payi": int(pay), "kutular": kutular}
    return yerlesim, dx_inf, bilgi


def katman_ekle(src, alfa, rgba, x, y):
    """RGBA plakayi poster olcegindeki murekkep katmanina yazar (tuval disini kirpar)."""
    a = np.asarray(rgba).astype(np.float32)
    h, w = a.shape[:2]
    H, W = alfa.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    al = sub[..., 3] / 255.0
    bgr = sub[..., :3][..., ::-1]
    src[y0:y1, x0:x1] = bgr * al[..., None] + src[y0:y1, x0:x1] * (1 - al[..., None])
    alfa[y0:y1, x0:x1] = np.maximum(alfa[y0:y1, x0:x1], al)


def halka_maskesi(median, ed):
    """Halka murekkebi: MEDIAN'daki murekkep renkli pikseller, halka bandi icinde."""
    d = murekkep_rengi(median, ed)
    bant = np.zeros(d.shape, np.uint8)
    cx, cy, ax, ay = RING_ELLIPSE
    cv2.ellipse(bant, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1,
                int(RING_LINE_PX) + 2 * 5 * RING_BAND, cv2.LINE_8)
    bant[RING_TIP_Y + 1:, :] = 0
    m = (d & (bant > 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((WBP.CLOSE_PX,) * 2, np.uint8))
    k = 2 * WBP.DILATE_PX + 1
    dil = cv2.dilate(m, np.ones((k, k), np.uint8))
    dist = cv2.distanceTransform(dil, cv2.DIST_L2, 3)
    return np.clip(dist / (WBP.FEATHER_PX + 1.0), 0, 1).astype(np.float32), m


def kaydir(a, dx):
    """Tam sayi yatay kaydirma (piksel birebir; disari cikan kirpilir)."""
    o = np.zeros_like(a)
    if dx == 0:
        return a.copy()
    if dx > 0:
        o[:, dx:] = a[:, :-dx]
    else:
        o[:, :dx] = a[:, -dx:]
    return o


def murekkep_kutusu(im, plaka, kutu, esik=12):
    """Goruntunun plakadan ayrildigi (murekkep) bolgenin kutusu + agirlik merkezi.

    `govde`: kuyruklar (cikan/inen harfler) haric ana govde bandi - isim ve mesaj
    ayni kuralla olculsun diye (EK KAPI 4: "mesaj isimlerden buyuk olmasin").
    Tam kutu yuksekligi de `yukseklik` olarak doner; hicbir olcum gizlenmez.
    """
    x0, y0, x1, y1 = [int(v) for v in kutu]
    d = np.abs(im[y0:y1, x0:x1].astype(np.int16) - plaka[y0:y1, x0:x1].astype(np.int16)).max(2) > esik
    if not d.any():
        return None
    ys, xs = np.nonzero(d)
    g = govde(d.astype(np.uint8), 0, d.shape[1])
    return {"kutu": [int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + 1 + x0, int(ys.max()) + 1 + y0],
            "merkez": [round(float(xs.mean()) + x0, 1), round(float(ys.mean()) + y0, 1)], "px": int(d.sum()),
            "yukseklik": int(ys.max()) + 1 - int(ys.min()),
            "govde": [int(g[0]) + y0, int(g[1]) + y0] if g else None,
            "govde_h": int(g[1] - g[0]) if g else 0}


def cihaz_kutusu(kutu, dev, geom):
    """Poster kutusunu cihaz tuvali koordinatina cevirir (place ile ayni donusum)."""
    s, _, x0, y0 = placement(dev)
    sy = float(geom["scale_y"]) if geom else 1.0
    if geom and sy != 1.0:
        y0 = (y0 - geom["crop_top"]) * sy
    bx0, by0, bx1, by1 = kutu
    return [bx0 * s + x0, by0 * s * sy + y0, bx1 * s + x0, by1 * s * sy + y0]


def kirp(kutu, W, H, pay=0):
    x0, y0, x1, y1 = kutu
    return [max(int(x0) - pay, 0), max(int(y0) - pay, 0), min(int(x1) + pay, W), min(int(y1) + pay, H)]


def yanyana(gorseller, yol, hedef_h=1500, ara=20, zemin=(245, 245, 245)):
    ims = [im.resize((max(int(im.width * hedef_h / im.height), 1), hedef_h), Image.LANCZOS) for im in gorseller]
    t = Image.new("RGB", (sum(i.width for i in ims) + ara * (len(ims) - 1), hedef_h), zemin)
    x = 0
    for i in ims:
        t.paste(i, (x, 0)); x += i.width + ara
    t.save(yol, quality=90, subsampling=1)
    return t.size


# ------------------------------------------------------------------ EK KAPI olcumleri
def _luma(rgb):
    return float(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def _ton(rgb):
    t = float(sum(rgb)) or 1.0
    return np.asarray(rgb, np.float32) / t


def renk_olcumu(im, plaka, maske):
    """Murekkep pikselleri: medyan RGB, zeminin medyan RGB'si ve kontrast."""
    if int(maske.sum()) < 20:
        return None
    ink = np.median(im[maske][:, ::-1], axis=0)
    zem = np.median(plaka[maske][:, ::-1], axis=0)
    return {"ink_rgb": [round(float(v), 1) for v in ink], "zemin_rgb": [round(float(v), 1) for v in zem],
            "kontrast": round(abs(_luma(ink) - _luma(zem)), 1), "px": int(maske.sum())}


def _parlak(img_bgr):
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    fon = cv2.GaussianBlur(g, (0, 0), 9)
    return ((g.astype(np.int16) - fon.astype(np.int16)) > 12).astype(np.uint8)


def yildiz_olcumu(plaka, im, degisen):
    """CLEAN plakadaki yildizlar: toplam / murekkeple ortulen / KAYBOLAN (maske disi).

    Kaybolan = plakada yildiz, murekkep maskesiyle hic kesismiyor (dok==0) ve
    ciktida ayni yontemle tespit edilemiyor. Bagimsiz olcumdur; kapi 1'in
    tautolojisi degil (cikti goruntusunden yeniden tespit edilir).
    """
    par = _parlak(plaka)
    n, lab, st, _ = cv2.connectedComponentsWithStats(par, 8)
    alan = st[:, cv2.CC_STAT_AREA]
    sec = np.zeros(n, bool)
    sec[1:] = (alan[1:] >= 3) & (alan[1:] <= 600)
    if not sec.any():
        return {"toplam": 0, "ortulen": 0, "kaybolan": 0}
    dok = np.bincount(lab.ravel(), weights=(degisen > 0).ravel().astype(np.float64), minlength=n)
    yeni_par = _parlak(im)
    var = np.bincount(lab.ravel(), weights=yeni_par.ravel().astype(np.float64), minlength=n)
    kayip = sec & (dok == 0) & (var == 0)
    return {"toplam": int(sec.sum()), "ortulen": int((sec & (dok > 0)).sum()),
            "kaybolan": int(kayip.sum())}



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posterler", required=True)
    ap.add_argument("--plakalar", required=True, help="MEDIAN_<ED>.png + GEOM_*.json")
    ap.add_argument("--temiz", required=True, help="PLATE_<ED>_<DEV>_CLEAN.png (cihaz tuvali olcusunde)")
    ap.add_argument("--orijinal", default="", help="karsilastirma icin canli wallpaper'lar")
    ap.add_argument("--kisisel", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--cift", default="Aries_Leo")
    ap.add_argument("--isimler", default="EMILY,JAMES")
    ap.add_argument("--mesaj", default="It Began With a Kiss in the Rain")
    ap.add_argument("--sadece-olcum", action="store_true", help="yalniz 1. asama: 4 renkte olcum, uretim yok")
    a = ap.parse_args()
    P6, P7, P12, kp = kisisel_kur(a.kisisel)
    sol, sag = [s.strip() for s in a.isimler.split(",")]
    cikti = Path(a.cikti); cikti.mkdir(parents=True, exist_ok=True)
    rapor, geo_ref, urun = [], None, {}

    # --- 1. ASAMA: 4 RENGIN TAMAMI ONCE OLCULUR (uretim yok) -------------
    olcum = {}
    for ed in EDISYONLAR:
        poster = imread(Path(a.posterler) / f"WA_POSTER_{a.cift.upper()}_{ed.upper()}_3X4.jpg")
        if (poster.shape[1], poster.shape[0]) != (POSTER_W, POSTER_H):
            raise SystemExit(f"HATA: poster {ed} {poster.shape[1]}x{poster.shape[0]}")
        median = imread(Path(a.plakalar) / f"MEDIAN_{ed.upper()}.png")
        if (median.shape[1], median.shape[0]) != (POSTER_W, POSTER_H):
            raise SystemExit(f"HATA: MEDIAN {ed} {median.shape[1]}x{median.shape[0]}")
        geo, _, _ = metin_olcumu(poster, median, ed)
        olcum[ed] = geo
        log(f"OLCUM {ed}: kume={json.dumps(geo['kume'])}")
        log(f"       sol={geo['sol']} ∞={geo['sonsuz']} sag={geo['sag']} cap={geo['cap']} mesaj_cap={geo['mesaj_cap']}")
        del poster, median
    (cikti / "WP_V2_OLCUM.json").write_text(json.dumps(olcum, indent=1))
    sapma = {k: int(np.abs(np.asarray([olcum[e][k] for e in EDISYONLAR]) -
                           np.asarray(olcum[EDISYONLAR[0]][k])).max())
             for k in ("sol", "sag", "sonsuz", "isim_govde")}
    log(f"4 renk geometri sapmasi (px): {json.dumps(sapma)}")
    if a.sadece_olcum:
        log("SADECE OLCUM: uretim yapilmadi")
        return [], {}, olcum[EDISYONLAR[0]]

    # --- 2. ASAMA: URETIM ------------------------------------------------
    for ed in EDISYONLAR:
        t0 = time.time()
        poster = imread(Path(a.posterler) / f"WA_POSTER_{a.cift.upper()}_{ed.upper()}_3X4.jpg")
        median = imread(Path(a.plakalar) / f"MEDIAN_{ed.upper()}.png")
        geo, isim_m, inf_m = metin_olcumu(poster, median, ed)
        if geo_ref is None:
            geo_ref = geo                      # 4 renkte AYNI geometri (kapi 3)
        prof = {"sol": profil(poster, isim_m & (np.arange(POSTER_W) < geo_ref["sonsuz"][0]),
                              (geo_ref["sol"][0], geo_ref["isim_govde"][0], geo_ref["sol"][1], geo_ref["isim_govde"][1])),
                "sag": profil(poster, isim_m & (np.arange(POSTER_W) > geo_ref["sonsuz"][2]),
                              (geo_ref["sag"][0], geo_ref["isim_govde"][0], geo_ref["sag"][1], geo_ref["isim_govde"][1]))}
        prof["tag"] = prof["sol"]
        yerlesim, dx_inf, bilgi = metin_katmani(P6, P7, P12, kp, geo_ref, prof, {"sol": sol, "sag": sag}, a.mesaj)

        alpha_c, core_c, mst = WBP.diff_ink_mask(poster, median, ed)
        sx0, sy0, sx1, sy1 = geo["sonsuz"]                    # OLCULEN ∞ (orta kume)
        inf_kutu = (sx0 - INF_PAD, sy0 - INF_PAD, sx1 + INF_PAD, sy1 + INF_PAD)
        inf_box = kutu_maske(poster.shape, inf_kutu).astype(np.float32)
        isim_box = kutu_maske(poster.shape, BOX_NAMES).astype(np.float32)
        a_inf = alpha_c * inf_box
        a_kalan = alpha_c * (1 - np.maximum(isim_box, inf_box))       # eski isimler ve ∞ cikarildi
        a_halka, _ = halka_maskesi(median, ed)
        del median

        src = poster.astype(np.float32)
        alfa = np.maximum(a_kalan, a_halka)
        # ∞: tam sayi kaydirma ile (piksel birebir)
        a_inf_k = kaydir(a_inf, dx_inf)
        src_inf = np.stack([kaydir(src[..., c], dx_inf) for c in range(3)], axis=2)
        yer = a_inf_k > 0
        src[yer] = src_inf[yer]
        alfa = np.maximum(alfa, a_inf_k)
        del a_inf, a_inf_k, src_inf, a_kalan, a_halka, alpha_c
        for rgba, x, y in yerlesim:
            katman_ekle(src, alfa, rgba, x, y)

        for dev in CIHAZLAR:
            plaka = imread(Path(a.temiz) / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png")
            W, H = DEVICES[dev]
            if (plaka.shape[1], plaka.shape[0]) != (W, H):
                log(f"ATLANDI {ed} {dev}: CLEAN plaka {plaka.shape[1]}x{plaka.shape[0]}, beklenen {W}x{H}")
                rapor.append({"edisyon": ed, "cihaz": dev, "hata": f"plaka olcusu {plaka.shape[1]}x{plaka.shape[0]}"})
                continue
            geom = WBP.load_geom(a.plakalar, ed, dev)
            P = WBP.place(src, dev, plaka.shape, geom)
            A = WBP.place(alfa, dev, plaka.shape, geom)[..., None]
            out = np.clip(np.round(A * P + (1 - A) * plaka.astype(np.float32)), 0, 255).astype(np.uint8)
            ad = f"AstroLove_{a.cift}_{ed}_{dev}.jpg"
            Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).save(cikti / ad, "JPEG", quality=95, subsampling=0)
            geri = imread(cikti / ad)
            dis = A[..., 0] <= 0
            # EK5: mesaj bandinda doku kopuklugu / duz yama yok (murekkep maskesi disi, JPEG oncesi)
            mb = kirp(cihaz_kutusu(bilgi["kutular"]["mesaj"], dev, geom), W, H, 4)
            b0, b1 = max(mb[1] - 8, 0), min(mb[3] + 8, H)
            bd = np.abs(out.astype(np.int16) - plaka.astype(np.int16)).max(2)[b0:b1][dis[b0:b1]]
            ek5 = {"bant": [int(b0), int(b1)], "murekkep_disi_maks_fark": int(bd.max()) if bd.size else 0,
                   "jpeg_sonrasi": int(np.abs(geri.astype(np.int16) - plaka.astype(np.int16)).max(2)[b0:b1][dis[b0:b1]].max()) if bd.size else 0,
                   "piksel": int(bd.size), "gecti": bool((bd.max() if bd.size else 0) == 0)}
            k1 = {"gecti": bool(np.abs(out.astype(np.int16) - plaka.astype(np.int16)).max(2)[dis].max() == 0),
                  "maks_fark": int(np.abs(out.astype(np.int16) - plaka.astype(np.int16)).max(2)[dis].max()),
                  "jpeg_sonrasi": int(np.abs(geri.astype(np.int16) - plaka.astype(np.int16)).max(2)[dis].max()),
                  "piksel": int(dis.sum())}
            urun[(ed, dev)] = dict(yol=str(cikti / ad), plaka=str(Path(a.temiz) / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"),
                                   geom=geom, kapi1=k1, ek5=ek5)
            rapor.append({"edisyon": ed, "cihaz": dev, "dosya": ad, "kapi1_maske_disi": k1,
                          "ek5_mesaj_bandi": ek5,
                          "duzen": bilgi, "olcum": geo_ref, "sure_sn": round(time.time() - t0, 1)})
            log(f"{ed} {dev}: maske disi fark {k1['maks_fark']} (JPEG sonrasi {k1['jpeg_sonrasi']})")
        del src, alfa, poster
    (cikti / "WP_V2_URETIM.json").write_text(json.dumps(rapor, indent=1))
    return rapor, urun, geo_ref


def kapilar(urun, geo_ref, duzen, orijinal, cift, cikti, edisyonlar=None):
    """Kapi 2-5: halka/sembol yeri, renkler arasi metin birebirligi, ortalama, kenar payi.

    edisyonlar: bu kosunun edisyon listesi. Verilmezse modulun EDISYONLAR'i.
    Kisisel edisyonlari (PURE_WHITE/BLACK/BLUE...) farkli oldugu icin ZORUNLU:
    liste tutmazsa renkler arasi kapilar SESSIZCE atlanirdi.
    """
    EDS = list(edisyonlar) if edisyonlar else EDISYONLAR
    K = {"halka_sembol": [], "metin_4renk": {}, "ortalama": [], "kenar_payi": [],
         "ek1_mesaj_renk": [], "ek2_yildiz": [], "ek3_esit_bosluk": [], "ek4_harf_yuksekligi": {},
         "ek4_mesaj_isimden_buyuk_degil": [], "ek5_mesaj_bandi": []}
    olculen, ek4_olcu = {}, {}
    for (ed, dev), u in urun.items():
        im = imread(u["yol"]); plaka = imread(u["plaka"]); geom = u["geom"]
        W, H = DEVICES[dev]
        degisen = np.abs(im.astype(np.int16) - plaka.astype(np.int16)).max(2)
        kutular = {
            "halka": kirp(cihaz_kutusu(BOX_SYMBOL_RING, dev, geom), W, H),
            "sembol": kirp(cihaz_kutusu(BOX_SYMBOL_CORE, dev, geom), W, H),   # ESIK_OGE ile olculur
            "sol": kirp(cihaz_kutusu(duzen["kutular"]["sol"], dev, geom), W, H, 12),
            "sag": kirp(cihaz_kutusu(duzen["kutular"]["sag"], dev, geom), W, H, 12),
            "mesaj": kirp(cihaz_kutusu(duzen["kutular"]["mesaj"], dev, geom), W, H, 12),
        }
        olculen[(ed, dev)] = {k: murekkep_kutusu(im, plaka, v, ESIK_OGE if k in ("halka", "sembol") else ESIK_METIN)
                              for k, v in kutular.items()}
        # kapi 2: orijinal wallpaper ile halka + sembol yeri
        o = Path(orijinal) / f"AstroLove_{cift}_{ed}_{dev}.jpg" if orijinal else None
        if o and o.exists():
            oi = imread(o)
            for ad in ("halka", "sembol"):
                y = olculen[(ed, dev)][ad]; x = murekkep_kutusu(oi, plaka, kutular[ad], ESIK_OGE)
                if y and x:
                    d = max(abs(y["merkez"][0] - x["merkez"][0]), abs(y["merkez"][1] - x["merkez"][1]),
                            *[abs(y["kutu"][i] - x["kutu"][i]) for i in range(4)])
                    K["halka_sembol"].append({"edisyon": ed, "cihaz": dev, "oge": ad, "sapma_px": round(float(d), 1),
                                              "gecti": bool(d <= 6.4)})
        # kapi 4: isim satiri ve mesaj yatayda ortali  (+ EK3: sol/sag bosluk esit)
        so, sa, me = (olculen[(ed, dev)][k] for k in ("sol", "sag", "mesaj"))
        for ad, kut in (("isim_satiri", [so["kutu"][0], 0, sa["kutu"][2], 0] if (so and sa) else None),
                        ("mesaj", me["kutu"] if me else None)):
            if not kut:
                continue
            mrk = (kut[0] + kut[2]) / 2
            K["ortalama"].append({"edisyon": ed, "cihaz": dev, "oge": ad,
                                  "sapma_px": round(abs(mrk - W / 2), 1), "gecti": bool(abs(mrk - W / 2) <= 2)})
            bs, bg = int(kut[0]), int(W - kut[2])
            K["ek3_esit_bosluk"].append({"edisyon": ed, "cihaz": dev, "oge": ad, "sol_px": bs, "sag_px": bg,
                                         "fark_px": abs(bs - bg), "gecti": bool(abs(bs - bg) <= 2)})
        if me:
            pay = min(me["kutu"][0], W - me["kutu"][2])
            K["kenar_payi"].append({"edisyon": ed, "cihaz": dev, "pay_px": int(pay),
                                    "gereken": int(KENAR_ORAN * W), "gecti": bool(pay >= KENAR_ORAN * W)})
        # EK1: mesaj rengi isimlerle ayni ton ailesinde + acik zeminde kontrast dusuk degil
        gm = degisen >= 40
        r_i = renk_olcumu(im, plaka, gm & (kutu_maske(im.shape, kutular["sol"]) > 0))
        r_m = renk_olcumu(im, plaka, gm & (kutu_maske(im.shape, kutular["mesaj"]) > 0))
        if r_i and r_m:
            ton = float(np.abs(_ton(r_i["ink_rgb"]) - _ton(r_m["ink_rgb"])).sum())
            acik = ed in ("Champagne_Ivory", "Warm_Parchment")
            gec = ton <= 0.08 and (not acik or r_m["kontrast"] >= r_i["kontrast"] - 3)
            K["ek1_mesaj_renk"].append({"edisyon": ed, "cihaz": dev, "isim": r_i, "mesaj": r_m,
                                        "ton_farki": round(ton, 4), "acik_zemin": acik, "gecti": bool(gec)})
        # EK2: CLEAN plakadaki yildizlar korunuyor mu
        yz = yildiz_olcumu(plaka, im, degisen)
        yz.update({"edisyon": ed, "cihaz": dev, "gecti": bool(yz["kaybolan"] == 0)})
        K["ek2_yildiz"].append(yz)
        # EK4: harf yuksekligi olcusu (4 renk karsilastirmasi asagida) + mesaj isimden buyuk degil
        if so and me:
            # AYNI kuralla olculur: govde bandi (kuyruklar haric). Tam kutu yukseklikleri
            # de yazilir - mesajda inen harf (g, y) tam kutuyu isim capinin ustune cikarir.
            hi, hm = so["govde_h"], me["govde_h"]
            ek4_olcu[(ed, dev)] = int(hi)
            K["ek4_mesaj_isimden_buyuk_degil"].append(
                {"edisyon": ed, "cihaz": dev, "isim_govde_px": int(hi), "mesaj_govde_px": int(hm),
                 "isim_kutu_px": int(so["yukseklik"]), "mesaj_kutu_px": int(me["yukseklik"]),
                 "gecti": bool(hm <= hi)})
        # EK5: mesaj bandinda doku kopuklugu / duz yama yok - olcum main()'te (JPEG oncesi,
        # kapi 1 ile ayni maske). Burada yalniz raporlanir.
        if u.get("ek5"):
            K["ek5_mesaj_bandi"].append(dict(edisyon=ed, cihaz=dev, **u["ek5"]))
    # kapi 3: ayni cihazda 4 renkte isim/mesaj kutulari birebir (<= 1 px)
    for dev in CIHAZLAR:
        d = {}
        for ad in ("sol", "sag", "mesaj"):
            kut = [olculen[(ed, dev)][ad]["kutu"] for ed in EDS if olculen.get((ed, dev), {}).get(ad)]
            if len(kut) == len(EDS):
                k = np.asarray(kut)
                d[ad] = {"maks_sapma_px": int(np.abs(k - k[0]).max()), "gecti": bool(np.abs(k - k[0]).max() <= 1)}
        K["metin_4renk"][dev] = d
    # EK4: ayni cihazda 4 renkte isim harf yuksekligi (+-1 px)
    for dev in CIHAZLAR:
        h = [ek4_olcu[(ed, dev)] for ed in EDS if (ed, dev) in ek4_olcu]
        if len(h) == len(EDS):
            K["ek4_harf_yuksekligi"][dev] = {"px": h, "yayilim_px": int(max(h) - min(h)),
                                             "gecti": bool(max(h) - min(h) <= 1)}
    liste = ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
             "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi")
    K["gecti"] = bool(all(x["gecti"] for ad in liste for x in K[ad])
                      and all(v["gecti"] for dv in K["metin_4renk"].values() for v in dv.values())
                      and all(v["gecti"] for v in K["ek4_harf_yuksekligi"].values())
                      and all(u["kapi1"]["gecti"] for u in urun.values()))
    (Path(cikti) / "WP_V2_KAPILAR.json").write_text(json.dumps(K, indent=1))
    return K


def sayfalar(urun, orijinal, cift, cikti):
    """Cihaz basina 4 renk yan yana + her dosya icin orijinal/yeni kiyas."""
    ciktilar = []
    for dev in CIHAZLAR:
        ims = [Image.open(urun[(ed, dev)]["yol"]) for ed in EDISYONLAR if (ed, dev) in urun]
        yol = Path(cikti) / f"KARSILASTIRMA_4RENK_{dev.upper()}.jpg"
        yanyana(ims, yol); ciktilar.append(str(yol))
    if orijinal:
        for (ed, dev), u in urun.items():
            o = Path(orijinal) / f"AstroLove_{cift}_{ed}_{dev}.jpg"
            if o.exists():
                yol = Path(cikti) / f"ESKI_YENI_{ed}_{dev}.jpg"
                yanyana([Image.open(o), Image.open(u["yol"])], yol); ciktilar.append(str(yol))
    return ciktilar


if __name__ == "__main__":
    rapor, urun, geo = main()
    import sys as _s
    _a = _s.argv
    if not rapor:                      # --sadece-olcum: 1. asama, kapi/sayfa yok
        _s.exit(0)
    cikti = _a[_a.index("--cikti") + 1]
    orij = _a[_a.index("--orijinal") + 1] if "--orijinal" in _a else ""
    cift = _a[_a.index("--cift") + 1] if "--cift" in _a else "Aries_Leo"
    K = kapilar(urun, geo, rapor[0]["duzen"], orij, cift, cikti)
    log(f"KAPILAR gecti={K['gecti']}")
    for ad in ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
               "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
        kot = [x for x in K[ad] if not x["gecti"]]
        log(f"  {ad}: {len(K[ad]) - len(kot)}/{len(K[ad])} gecti" + (f" | KALAN {kot[:3]}" if kot else ""))
    log(f"  metin_4renk: {json.dumps(K['metin_4renk'])}")
    log(f"  ek4_harf_yuksekligi: {json.dumps(K['ek4_harf_yuksekligi'])}")
    s = sayfalar(urun, orij, cift, cikti)
    log(f"sayfa: {len(s)} dosya")
    _s.exit(0 if K["gecti"] else 1)
