#!/usr/bin/env python3
"""
Kisisellestirme pilotu v2 (Mo, 21 Eyl 2026) - sadelestirilmis, sure sinirli.

Onceki 3 kosu teslim edemedi; bu surumde:
  - Aday font sayisi 44 -> rol basina 5 aile.
  - Tum olcumler kucultulmus kopyada (IoU 200 px, buyuk JPEG istatistigi 1000 px).
  - Pilot cozunurlugu 2400x3000; Canva 4000x5000 kutulari 0.6 ile olceklenir.
  - Her asama basi/sonu zaman damgali log, 60 sn'de bir kalp atisi.
  - Asama basina sert sinir (varsayilan 8 dk, SIGALRM). Asilirsa asama kesilir,
    o ana kadarki ciktilar Drive'a yazilir ve kosu basarisiz biter.
  - Ara ciktilar asama biter bitmez Drive'a gider; Actions logu okunamasa bile
    ilerleme Drive'dan gorulur.
"""
import argparse
import json
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, iou, lsf, rc,
                           tracking_icin, variable_agirliklar)

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
OLCEK = 0.6                                   # 4000x5000 -> 2400x3000
TUVAL = (2400, 3000)
IOU_H = 200                                   # IoU taramasi normalize yuksekligi
STAT_MAKS = 1000                              # istatistik icin en uzun kenar
TR_TEST = "ğıİöüşçŞÇÜÖ"

ADAYLAR = {
    "isim": ["Cinzel.ttf", "Marcellus.ttf", "Forum.ttf", "CormorantSC.ttf",
             "CormorantSC-Medium.ttf", "CormorantSC-SemiBold.ttf",
             "Trirong.ttf", "Trirong-Medium.ttf"],
    "tagline": ["CormorantGaramond-Italic.ttf", "CormorantInfant-Italic.ttf",
                "EBGaramond-Italic.ttf", "PlayfairDisplay-Italic.ttf",
                "LibreCaslonText-Italic.ttf"],
}
AILE = {"CormorantSC": "Cormorant SC", "Trirong": "Trirong", "Cinzel": "Cinzel",
        "Marcellus": "Marcellus", "Forum": "Forum",
        "CormorantGaramond": "Cormorant Garamond", "CormorantInfant": "Cormorant Infant",
        "EBGaramond": "EB Garamond", "PlayfairDisplay": "Playfair Display",
        "LibreCaslonText": "Libre Caslon Text"}

B = {k: tuple(v * OLCEK for v in box) for k, box in BOX.items()}   # top,left,w,h

T0 = time.time()
_asama = "baslangic"
_asama_t0 = T0


class AsamaZamanAsimi(Exception):
    pass


def ts():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def log(*a):
    print(f"[{ts()} +{time.time() - T0:6.1f}s]", *a, flush=True)


def kalp():
    while True:
        time.sleep(60)
        print(f"[{ts()} +{time.time() - T0:6.1f}s] KALP asama={_asama} "
              f"asamada={time.time() - _asama_t0:.0f}s", flush=True)


def _alarm(signum, frame):
    raise AsamaZamanAsimi(f"'{_asama}' asamasi sert siniri asti")


def asama(ad, sinir_sn):
    """Asama baslat: zaman damgasi + SIGALRM sert siniri."""
    global _asama, _asama_t0
    _asama, _asama_t0 = ad, time.time()
    log(f"=== ASAMA BASLADI: {ad} (sinir {sinir_sn // 60} dk)")
    signal.alarm(sinir_sn)


def asama_bitti(sureler):
    signal.alarm(0)
    s = time.time() - _asama_t0
    sureler[_asama] = round(s, 1)
    log(f"=== ASAMA BITTI: {_asama} ({s:.1f}s)")


def drive_yaz(*adlar):
    """Ureteni bekletmeden Drive'a yaz; Actions logu okunamasa bile ilerleme gorulur."""
    for ad in adlar:
        p = OUT / ad
        if p.exists():
            try:
                rc("copy", str(p), DEST)
                log(f"Drive <- {ad} ({p.stat().st_size / 1e3:.0f} KB)")
            except Exception as e:
                log(f"Drive yazilamadi {ad}: {str(e)[:120]}")


def ac(path, maks=None):
    """Buyuk dosyayi hizli ac: JPEG'de draft, PNG'de reduce, sonra RGBA."""
    im = Image.open(path)
    if maks:
        try:
            im.draft("RGB", (maks, maks))
        except Exception:
            pass
        k = max(max(im.size) // maks, 1)
        if k > 1:
            im = im.reduce(k)
    return im.convert("RGBA")


def kucult(im, maks=STAT_MAKS):
    o = maks / max(im.size)
    return im if o >= 1 else im.resize((max(int(im.width * o), 1), max(int(im.height * o), 1)),
                                       Image.LANCZOS)


def maske_kutu(im):
    a = np.asarray(im)
    m = ink_mask(a)
    bb = bbox_of(m)
    return a, m, bb


def ref_metrik(path):
    """Referans plakadan: png boyutu, cam kutusu, satir bazli altin profili."""
    im = ac(path)
    a, m, bb = maske_kutu(im)
    x0, y0, x1, y1 = bb
    prof = []
    for y in range(y0, y1):
        mr = m[y, x0:x1]
        prof.append(np.median(a[y, x0:x1][mr][:, :3], axis=0) if mr.sum() >= 3
                    else (prof[-1] if prof else np.array([200., 170., 110.])))
    al = a[..., 3]
    return {"png": im.size, "bb": bb, "prof": np.asarray(prof, np.float32),
            "yumusak": float(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1)) > 0.45,
            "maske": m, "rgb": np.median(a[..., :3][m], axis=0)}


def ref_maske_kucuk(met, h=IOU_H):
    x0, y0, x1, y1 = met["bb"]
    im = Image.fromarray((met["maske"][y0:y1, x0:x1] * 255).astype(np.uint8), "L")
    o = h / im.height
    return im.resize((max(int(im.width * o), 1), h), Image.LANCZOS)


def font_esle(ref_kucuk, metin, dosyalar, etiket):
    hedef_w, hedef_h = ref_kucuk.size
    ref = np.asarray(ref_kucuk)
    sonuc = []
    ciftler = [(FONT_DIR / d, w) for d in dosyalar for w in variable_agirliklar(FONT_DIR / d)]
    for i, (p, w) in enumerate(ciftler, 1):
        try:
            size = cap_icin_boyut(p, metin, hedef_h, w)
            f = font_yukle(p, size, w)
            tr = tracking_icin(f, metin, hedef_w)
            cr, _ = ciz_metin(f, metin, tr)
            sonuc.append({"font": p.stem, "aile": AILE.get(p.stem.split("-")[0], p.stem),
                          "wght": w, "punto": size, "tracking": round(tr, 2),
                          "tr_orani": round(tr / size, 4),
                          "iou": round(iou(ref, np.asarray(cr.resize((hedef_w, hedef_h),
                                                                     Image.LANCZOS))), 4)})
        except Exception as e:
            log(f"  aday atlandi {p.name} w={w}: {str(e)[:70]}")
    sonuc.sort(key=lambda r: -r["iou"])
    log(f"{etiket}: {len(sonuc)}/{len(ciftler)} aday olculdu, en iyi "
        f"{sonuc[0]['font']} IoU={sonuc[0]['iou']}")
    return sonuc


def altin(mask_img, met):
    """L maskesine referansin altin satir profilini uygular."""
    m = np.asarray(mask_img).astype(np.float32) / 255.0
    h, w = m.shape
    prof = met["prof"]
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    g = prof[lo] * (1 - t) + prof[hi] * t
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(np.repeat(g[:, None, :], w, axis=1), 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    pl = Image.fromarray(o, "RGBA")
    if met["yumusak"]:
        from PIL import ImageFilter
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.GaussianBlur(max(h * 0.05, 1)))
        arr = np.asarray(pl).copy()
        arr[..., 3] = np.clip(np.maximum(arr[..., 3].astype(np.float32),
                                         np.asarray(hale).astype(np.float32) * 0.35),
                              0, 255).astype(np.uint8)
        pl = Image.fromarray(arr, "RGBA")
    return pl


def hedef(kutu, met):
    """Kutu + referans -> tuvaldeki (merkez_x, merkez_y, cam_yuksekligi, cam_genisligi)."""
    top, left, w, h = kutu
    pw, ph = met["png"]
    x0, y0, x1, y1 = met["bb"]
    oy = h / ph
    return (left + w / 2, top + ((y0 + y1) / 2) * oy, (y1 - y0) * oy, (x1 - x0) * (w / pw))


def koy(tuval, im, kutu):
    """Kutuyu tuvale yapistirir; negatif ofset (bg) kirpilarak karsilanir."""
    top, left, w, h = kutu
    yeni = im.resize((max(int(round(w)), 1), max(int(round(h)), 1)), Image.LANCZOS)
    x, y = int(round(left)), int(round(top))
    kx, ky = max(-x, 0), max(-y, 0)
    if kx >= yeni.width or ky >= yeni.height:
        return
    if kx or ky:
        yeni = yeni.crop((kx, ky, yeni.width, yeni.height))
        x, y = x + kx, y + ky
    if x >= tuval.width or y >= tuval.height:
        return
    tuval.alpha_composite(yeni.crop((0, 0, min(yeni.width, tuval.width - x),
                                     min(yeni.height, tuval.height - y))), (x, y))


def yaz(tuval, metin, fp, wght, met, kutu, tr_orani, maks_w=None, punto=None, taban=0.70):
    mx, my, cam_h, _ = hedef(kutu, met)
    size = punto or cap_icin_boyut(fp, metin, cam_h, wght)
    olcek = 1.0
    tam = size
    cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    # Orantili kucultme tek adimda tam oturmaz (tracking + yuvarlama); taban
    # %70'e dayanana kadar yinele.
    for _ in range(5):
        if not maks_w or cr.width <= maks_w or olcek <= taban + 1e-9:
            break
        olcek = max(olcek * min(maks_w / cr.width, 0.99), taban)
        size = max(int(round(tam * olcek)), 4)
        cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    pl = altin(cr, met)
    tuval.alpha_composite(pl, (int(round(mx - pl.width / 2)), int(round(my - pl.height / 2))))
    return {"metin": metin, "punto": size, "olcek": round(olcek, 3),
            "genislik": pl.width, "sigdi": not (maks_w and cr.width > maks_w),
            "tabana_dayandi": bool(maks_w and olcek <= taban + 1e-9 and cr.width > maks_w)}


def jpg(im, path, maks_bayt):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 66, 60, 54, 48):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= maks_bayt:
            return q
    return q


def tr_eksik(fp):
    from fontTools.ttLib import TTFont
    cm = set()
    for t in TTFont(str(fp))["cmap"].tables:
        cm |= set(t.cmap.keys())
    return [c for c in TR_TEST if ord(c) not in cm]


# ------------------------------------------------------------------ asamalar


def st_indir(d):
    klas = {k: lsf(v) for k, v in FOLDERS.items()}
    import re

    def bul(k, kalip):
        for f in klas[k]:
            if re.fullmatch(kalip, f, re.I):
                return f
        raise FileNotFoundError(f"{k}: {kalip} yok -> {klas[k][:10]}")

    istek = [("names", "cancer_name_gold.png"), ("names", "libra_name_gold.png"),
             ("parts", "tagline.png"), ("parts", "logo.png"), ("parts", "circle.png"),
             ("parts", "midnight_blue_bg.jpg"),
             ("main", bul("main", r"(cancer_libra|libra_cancer)_gold\.png")),
             ("small", bul("small", r"cancer[^/]*\.png")),
             ("small", bul("small", r"libra[^/]*\.png"))]
    satir = []
    for i, (k, f) in enumerate(istek, 1):
        p = fetch(FOLDERS[k], f, REF / k)
        with Image.open(p) as im:
            boyut = im.size
        d["yol"][k + "/" + f] = str(p)
        d.setdefault("anahtar", {})[k] = d["anahtar"].get(k, []) + [f] if "anahtar" in d else [f]
        satir.append(f"{k}/{f}  {p.stat().st_size / 1e6:.2f} MB  {boyut[0]}x{boyut[1]}")
        log(f"indi {i}/{len(istek)}: {satir[-1]}")
    d["indirilen"] = satir
    (OUT / "INDIRILEN.txt").write_text("\n".join(satir) + "\n")
    # sonsuzluk kontrolu: beklenen kutu orani 311.9/96.3 = 3.24
    lm = ref_metrik(d["yol"]["parts/logo.png"])
    x0, y0, x1, y1 = lm["bb"]
    d["sonsuzluk_orani"] = round((x1 - x0) / max(y1 - y0, 1), 2)
    log(f"logo.png cam orani {d['sonsuzluk_orani']} (sonsuzluk kutusu bekleneni 3.24)")


def st_font(d):
    d["m_cancer"] = ref_metrik(d["yol"]["names/cancer_name_gold.png"])
    d["m_libra"] = ref_metrik(d["yol"]["names/libra_name_gold.png"])
    d["m_tag"] = ref_metrik(d["yol"]["parts/tagline.png"])
    log(f"referans cam kutulari: CANCER {d['m_cancer']['bb']} LIBRA {d['m_libra']['bb']} "
        f"TAGLINE {d['m_tag']['bb']}")
    d["font"] = {
        "isim": font_esle(ref_maske_kucuk(d["m_cancer"]), "CANCER", ADAYLAR["isim"], "isim"),
        "tagline": font_esle(ref_maske_kucuk(d["m_tag"]), ORIG_TAGLINE,
                             ADAYLAR["tagline"], "tagline"),
    }
    (OUT / "FONT_TABLOSU.json").write_text(json.dumps(d["font"], ensure_ascii=False, indent=1))
    for rol in ("isim", "tagline"):
        for r in d["font"][rol][:5]:
            log(f"  {rol}: {r['font']} w={r['wght']} IoU={r['iou']} tr={r['tr_orani']}")


def st_doku(d):
    """Ayni yontemle CANCER/LIBRA yeniden uretilir, orijinalle karsilastirilir."""
    f = d["font"]["isim"][0]
    fp = FONT_DIR / (f["font"] + ".ttf")
    d["stil"] = {}
    kiyas = []
    for ad, met in (("CANCER", d["m_cancer"]), ("LIBRA", d["m_libra"])):
        orij = ref_maske_kucuk(met)
        size = cap_icin_boyut(fp, ad, IOU_H, f["wght"])
        ftt = font_yukle(fp, size, f["wght"])
        tr = tracking_icin(ftt, ad, orij.width)
        cr, _ = ciz_metin(ftt, ad, tr)
        skor = iou(np.asarray(orij), np.asarray(cr.resize(orij.size, Image.LANCZOS)))
        pl = altin(cr, met)
        a = np.asarray(pl)
        yrgb = np.median(a[..., :3][a[..., 3] > 40], axis=0)
        d["stil"][ad] = {"iou": round(skor, 4), "punto": size, "tr_orani": round(tr / size, 4),
                         "orij_rgb": [int(v) for v in met["rgb"]],
                         "yeni_rgb": [int(v) for v in yrgb],
                         "rgb_fark": round(float(np.abs(met["rgb"] - yrgb).max()), 1)}
        log(f"STIL {ad}: {json.dumps(d['stil'][ad])}")
        # yan yana kiyas serisi
        h = 120
        a_im = orij.resize((int(orij.width * h / orij.height), h), Image.LANCZOS)
        b_im = pl.resize((int(pl.width * h / pl.height), h), Image.LANCZOS)
        kiyas.append((ad, a_im, b_im))
    d["isim_tr_orani"] = sum(v["tr_orani"] for v in d["stil"].values()) / 2
    log(f"isim tracking orani {d['isim_tr_orani']:.4f}")
    w = max(max(a.width, b.width) for _, a, b in kiyas) + 20
    kn = Image.new("RGB", (w, len(kiyas) * 280), (10, 12, 26))
    for i, (ad, a_im, b_im) in enumerate(kiyas):
        kn.paste(Image.merge("RGB", [a_im] * 3), (10, i * 280 + 10))
        kn.paste(b_im.convert("RGB"), (10, i * 280 + 150), b_im)
    jpg(kn, OUT / "STIL_KIYAS.jpg", 400_000)


def st_uret(d):
    fi = d["font"]["isim"][0]
    ft = d["font"]["tagline"][0]
    fip, ftp = FONT_DIR / (fi["font"] + ".ttf"), FONT_DIR / (ft["font"] + ".ttf")
    d["tr_eksik"] = {"isim": tr_eksik(fip), "tagline": tr_eksik(ftp)}
    log(f"TURKCE eksik glif: {json.dumps(d['tr_eksik'])}")

    _, _, tag_h, _ = hedef(B["tagline"], d["m_tag"])
    d["tag_punto"] = cap_icin_boyut(ftp, ORIG_TAGLINE, tag_h, ft["wght"])
    d["tag_tr"] = ft["tr_orani"]
    d["tag_maks_w"] = B["tagline"][2]
    log(f"tagline: cam_h={tag_h:.1f} punto={d['tag_punto']} tr_orani={d['tag_tr']:.4f} "
        f"maks_w={d['tag_maks_w']:.0f}")

    zemin = Image.new("RGBA", TUVAL, (0, 0, 0, 255))
    for ad, kutu in (("parts/midnight_blue_bg.jpg", B["bg"]), ("parts/circle.png", B["ring"])):
        koy(zemin, ac(d["yol"][ad], 3000), kutu)
    ana = [k for k in d["yol"] if k.startswith("main/")][0]
    koy(zemin, ac(d["yol"][ana], 2200), B["main"])
    kucukler = sorted(k for k in d["yol"] if k.startswith("small/"))
    koy(zemin, ac(d["yol"][[k for k in kucukler if "cancer" in k.lower()][0]], 800), B["sym_left"])
    koy(zemin, ac(d["yol"][[k for k in kucukler if "libra" in k.lower()][0]], 800), B["sym_right"])
    koy(zemin, ac(d["yol"]["parts/logo.png"], 800), B["infinity"])
    log("zemin kuruldu")
    d["zemin"] = zemin

    d["orij"] = zemin.copy()
    koy(d["orij"], ac(d["yol"]["names/cancer_name_gold.png"], 1600), B["name_left"])
    koy(d["orij"], ac(d["yol"]["names/libra_name_gold.png"], 1600), B["name_right"])
    koy(d["orij"], ac(d["yol"]["parts/tagline.png"], 2400), B["tagline"])

    d["poster"] = {}
    d["yerlesim"] = {}
    for kod in ("A", "B", "C"):
        t = zemin.copy()
        sol = yaz(t, NEW_LEFT, fip, fi["wght"], d["m_cancer"], B["name_left"], d["isim_tr_orani"])
        sag = yaz(t, NEW_RIGHT, fip, fi["wght"], d["m_libra"], B["name_right"], d["isim_tr_orani"])
        tg = yaz(t, TAGLINES[kod], ftp, ft["wght"], d["m_tag"], B["tagline"], d["tag_tr"],
                 maks_w=d["tag_maks_w"], punto=d["tag_punto"])
        d["poster"][kod] = t
        d["yerlesim"][kod] = {"sol": sol, "sag": sag, "tagline": tg}
        q = jpg(t, OUT / f"PILOT_{kod}.jpg", 1_500_000)
        log(f"PILOT_{kod}.jpg q={q} {(OUT / f'PILOT_{kod}.jpg').stat().st_size / 1e6:.2f} MB "
            f"tagline={json.dumps(tg, ensure_ascii=False)}")


def st_poster(d):
    bant = (int(B["sym_left"][1] - 70), int(B["name_left"][0] - 55),
            int(B["name_right"][1] + B["name_right"][2] + 70),
            int(B["name_left"][0] + B["name_left"][3] + 55))
    ust, alt = d["orij"].crop(bant), d["poster"]["A"].crop(bant)
    yi = Image.new("RGB", (ust.width, ust.height * 2 + 16), (10, 12, 26))
    yi.paste(ust.convert("RGB"), (0, 0))
    yi.paste(alt.convert("RGB"), (0, ust.height + 16))
    yi = yi.resize((1500, int(yi.height * 1500 / yi.width)), Image.LANCZOS)
    log(f"YAKIN_ISIMLER q={jpg(yi, OUT / 'YAKIN_ISIMLER.jpg', 400_000)}")

    tb = (int(B["tagline"][1] - 90), int(B["tagline"][0] - 45),
          int(B["tagline"][1] + B["tagline"][2] + 90),
          int(B["tagline"][0] + B["tagline"][3] + 45))
    ser = [d["orij"].crop(tb)] + [d["poster"][k].crop(tb) for k in ("A", "B", "C")]
    yt = Image.new("RGB", (ser[0].width, sum(s.height for s in ser) + 48), (10, 12, 26))
    y = 0
    for s in ser:
        yt.paste(s.convert("RGB"), (0, y))
        y += s.height + 16
    yt = yt.resize((1500, int(yt.height * 1500 / yt.width)), Image.LANCZOS)
    log(f"YAKIN_TAGLINE q={jpg(yt, OUT / 'YAKIN_TAGLINE.jpg', 400_000)}")


def stil_test_yaz(d, sureler, hata=None):
    fi = d.get("font", {}).get("isim", [{}])[0] if d.get("font") else {}
    ft = d.get("font", {}).get("tagline", [{}])[0] if d.get("font") else {}
    m = ["# Kisisellestirme stil testi (pilot v2)", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}, "
         f"tuval {TUVAL[0]}x{TUVAL[1]} (Canva 4000x5000 kutulari x{OLCEK}).", ""]
    if hata:
        m += [f"**KOSU TAMAMLANMADI:** {hata}", ""]
    m += ["## Asama sureleri", "", "| asama | saniye |", "| --- | --- |"]
    m += [f"| {k} | {v} |" for k, v in sureler.items()]
    m += ["", "## Font secimi (IoU, 200 px normalize referans)", ""]
    for rol in ("isim", "tagline"):
        sira = d.get("font", {}).get(rol)
        if not sira:
            continue
        m += [f"### {rol}", "", "| sira | aile | dosya | agirlik | IoU | harf araligi/punto |",
              "| --- | --- | --- | --- | --- | --- |"]
        m += [f"| {i} | {r['aile']} | {r['font']} | {r['wght'] or '-'} | {r['iou']} "
              f"| {r['tr_orani']} |" for i, r in enumerate(sira[:5], 1)]
        m += [""]
    if fi:
        m += ["## Lisans", "",
              "| rol | aile | lisans | ticari kullanim |", "| --- | --- | --- | --- |",
              f"| isim | {fi.get('aile')} | SIL OFL 1.1 (google/fonts ofl/) | serbest |",
              f"| tagline | {ft.get('aile')} | SIL OFL 1.1 (google/fonts ofl/) | serbest |", ""]
    if d.get("stil"):
        m += ["## Stil fark skoru", "",
              "Ayni yontemle uretilen plaka, orijinal *_name_gold.png ile ayni yukseklige",
              "getirilip karsilastirildi (STIL_KIYAS.jpg: ust orijinal, alt yeni).", "",
              "| plaka | maske IoU | altin RGB orijinal | altin RGB yeni | maks kanal farki |",
              "| --- | --- | --- | --- | --- |"]
        m += [f"| {k} | {v['iou']} | {tuple(v['orij_rgb'])} | {tuple(v['yeni_rgb'])} "
              f"| {v['rgb_fark']} |" for k, v in d["stil"].items()]
        m += [""]
    if d.get("tr_eksik") is not None:
        m += ["## Turkce karakter", "", f"Test dizisi: `{TR_TEST}`", "",
              f"- isim fontu eksik glif: {d['tr_eksik']['isim'] or 'YOK'}",
              f"- tagline fontu eksik glif: {d['tr_eksik']['tagline'] or 'YOK'}", ""]
    if d.get("yerlesim"):
        m += ["## Uzun metin kurali", "",
              f"Tagline kutusu {d['tag_maks_w']:.0f} px, ortak punto {d['tag_punto']}, "
              "taban %70.", ""]
        for k, v in d["yerlesim"].items():
            t = v["tagline"]
            m.append(f"- {k}: punto {t['punto']} (%{t['olcek'] * 100:.0f}), "
                     f"genislik {t['genislik']} px, "
                     f"{'sigdi' if t['sigdi'] else 'TABANA DAYANDI (kutuyu asiyor)'}")
        dayanan = [k for k, v in d["yerlesim"].items() if v["tagline"].get("tabana_dayandi")]
        if dayanan:
            m += ["", f"**UYARI:** {', '.join(dayanan)} varyantinda %70 tabani asildi."]
        m += [""]
    if d.get("sonsuzluk_orani"):
        m += ["## Sonsuzluk isareti", "",
              f"logo.png cam orani {d['sonsuzluk_orani']}, Canva sonsuzluk kutusu orani 3.24.", ""]
    if d.get("indirilen"):
        m += ["## Indirilen referanslar", ""] + [f"- {s}" for s in d["indirilen"]] + [""]
    (OUT / "STIL_TEST.md").write_text("\n".join(m) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asama-sinir", type=int, default=480)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGALRM, _alarm)
    threading.Thread(target=kalp, daemon=True).start()
    log(f"pilot2 basladi; asama siniri {a.asama_sinir}s, tuval {TUVAL}, olcek {OLCEK}")

    d = {"yol": {}}
    sureler = {}
    adimlar = [("indir", st_indir, ["INDIRILEN.txt"]),
               ("font", st_font, ["FONT_TABLOSU.json", "STIL_TEST.md"]),
               ("doku", st_doku, ["STIL_KIYAS.jpg", "STIL_TEST.md"]),
               ("uret", st_uret, ["PILOT_A.jpg", "PILOT_B.jpg", "PILOT_C.jpg", "STIL_TEST.md"]),
               ("poster", st_poster, ["YAKIN_ISIMLER.jpg", "YAKIN_TAGLINE.jpg", "STIL_TEST.md"])]
    for ad, fn, ciktilar in adimlar:
        asama(ad, a.asama_sinir)
        try:
            fn(d)
        except Exception as e:
            signal.alarm(0)
            sureler[ad] = round(time.time() - _asama_t0, 1)
            log(f"!!! ASAMA HATASI {ad}: {type(e).__name__}: {e}")
            stil_test_yaz(d, sureler, hata=f"{ad} asamasi: {type(e).__name__}: {e}")
            drive_yaz("STIL_TEST.md", "INDIRILEN.txt", "FONT_TABLOSU.json", "STIL_KIYAS.jpg",
                      "PILOT_A.jpg", "PILOT_B.jpg", "PILOT_C.jpg",
                      "YAKIN_ISIMLER.jpg", "YAKIN_TAGLINE.jpg")
            log("ara ciktilar Drive'a yazildi; kosu basarisiz bitiyor")
            sys.exit(1)
        asama_bitti(sureler)
        stil_test_yaz(d, sureler)
        drive_yaz(*ciktilar)

    log(f"TOPLAM {time.time() - T0:.1f}s | sureler {json.dumps(sureler)}")
    log("pilot2 bitti")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
