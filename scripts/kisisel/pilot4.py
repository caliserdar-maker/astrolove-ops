#!/usr/bin/env python3
"""
Kisisellestirme pilotu v4 (Mo degerlendirmesi, 21 Eyl 2026).

Onaylanan: isim plakalari (SERDAR / LENA) - dokunulmuyor.
Duzeltilecek:
  1) Ana sembol referanstan farkli (daha sari/duz). ONCE OLC, SONRA DUZELT:
     referans posterle bolge bazli RGB/doygunluk/parlaklik karsilastirmasi;
     fark > 5 birimse referanstan olculen kanal duzeltmesi uygulanir.
     (Yerel olcum: reduce+LANCZOS yeniden orneklemesi kaynaga 1.5 birim sadik,
     alfa on-carpimi 35.5 birim SAPTIRIYOR -> sebep yeniden orneklemede degil.)
  2) Tagline: EB Garamond Italic 400, normal harf araligi, yatay sikistirma yok;
     tasarsa punto orantili kuculur. Harf yuksekligi referanstakiyle ayni.
     Altin doku isimlerdeki onayli yontem; renk referansa <= 5 birim.
  3) YAKIN_ISIMLER kirpimi genisletildi (soldaki isim kesiliyordu).

HAZIR/ bilesenleri yeniden kullanilir (devler tekrar islenmez).
Her asama ayri surecte (timeout), her cikti uretilir uretilmez Drive'a gider.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, rc)

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
DURUM = OUT / "durum4.json"

OLCEK, TUVAL = 0.6, (2400, 3000)
B = {k: tuple(v * OLCEK for v in box) for k, box in BOX.items()}
ISIM_FONT, ISIM_W = "Cinzel.ttf", 500
TAG_FONT, TAG_W = "EBGaramond-Italic.ttf", 400       # Mo: Regular, sikistirma yok
MUREKKEP = 70                                         # luma esigi (zemin ~20)
ESIK = 5.0                                            # kabul esigi (birim)
REFERANS = "REFERANS_CANCER_LIBRA.jpg"
HAZIR_DOSYA = ["bg.png", "ring.png", "main.png", "sym_left.png", "sym_right.png",
               "infinity.png", "orij_name_left.png", "orij_name_right.png",
               "orij_tagline.png"]
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def gonder(ad):
    p = OUT / ad
    if not p.exists():
        return log(f"gonderilemedi (yok): {ad}")
    try:
        rc("copy", str(p), DEST)
        log(f"Drive <- {ad} ({p.stat().st_size / 1e3:.0f} KB)")
    except Exception as e:
        log(f"Drive yazilamadi {ad}: {str(e)[:130]}")


def durum_oku():
    return json.loads(DURUM.read_text()) if DURUM.exists() else {}


# ---------------------------------------------------------------- olcum


def bolge_olc(im, kutu, ad=""):
    """Kutudaki murekkep piksellerinin RGB / doygunluk / parlaklik istatistigi."""
    top, left, w, h = kutu
    k = im.convert("RGB").crop((int(left), int(top), int(left + w), int(top + h)))
    x = np.asarray(k).astype(np.float32)
    luma = x @ np.array([0.299, 0.587, 0.114])
    sel = luma > MUREKKEP
    if sel.sum() < 50:
        return {"ad": ad, "murekkep_px": int(sel.sum()), "rgb": None}
    r = x[sel]
    mx, mn = r.max(axis=1), r.min(axis=1)
    return {"ad": ad, "murekkep_px": int(sel.sum()),
            "murekkep_oran": round(float(sel.mean()), 4),
            "rgb": [round(float(v), 1) for v in np.median(r, axis=0)],
            "doygunluk": round(float(np.mean(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0))), 3),
            "parlaklik": round(float(luma[sel].mean()), 1),
            "parlaklik_std": round(float(luma[sel].std()), 1)}


def fark(a, b):
    if not a or not b or not a.get("rgb") or not b.get("rgb"):
        return None
    return round(float(np.abs(np.array(a["rgb"]) - np.array(b["rgb"])).max()), 1)


# ---------------------------------------------------------------- asamalar


def a_ref(d):
    """Canva referansini runner'dan indir (sandbox'a kapali), Drive'a yaz, olc."""
    url = d.get("url") or ""
    p = OUT / REFERANS
    if url:
        print(f"::add-mask::{url}", flush=True)
        r = subprocess.run(["curl", "-fsSL", "--max-time", "120", "-o", str(p), url],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError(f"referans indirilemedi (curl {r.returncode}): {r.stderr[-300:]}")
    if not p.exists():
        raise FileNotFoundError("referans yok ve url verilmedi")
    im = Image.open(p)
    log(f"referans: {p.stat().st_size / 1e3:.0f} KB {im.size}")
    if im.size != TUVAL:
        im = im.resize(TUVAL, Image.LANCZOS)
        log(f"referans {TUVAL} olceklendi")
        im.save(p, "JPEG", quality=95)
    gonder(REFERANS)
    d["ref_olcum"] = {k: bolge_olc(im, B[k], k)
                      for k in ("main", "sym_left", "sym_right", "ring", "tagline",
                                "name_left", "name_right")}
    for k, v in d["ref_olcum"].items():
        log(f"REFERANS {k:11s}: {json.dumps(v, ensure_ascii=False)}")
    # referans tagline cam yuksekligi (harf yuksekligi esitlemesi icin)
    top, left, w, h = B["tagline"]
    k = np.asarray(Image.open(p).convert("RGB").crop(
        (int(left), int(top), int(left + w), int(top + h)))).astype(np.float32)
    sel = (k @ np.array([0.299, 0.587, 0.114])) > MUREKKEP
    bb = bbox_of(sel)
    d["ref_tag_h"] = int(bb[3] - bb[1]) if bb else None
    d["ref_tag_w"] = int(bb[2] - bb[0]) if bb else None
    log(f"referans tagline cam kutusu: {d['ref_tag_w']}x{d['ref_tag_h']} px")
    return d


def a_indir(d):
    """HAZIR/ bilesenleri (yeniden kullan) + isim/tagline plaka asillari."""
    HAZIR.mkdir(parents=True, exist_ok=True)
    for f in HAZIR_DOSYA:
        if not (HAZIR / f).exists():
            rc("copy", f"{DEST}/HAZIR/{f}", str(HAZIR))
    log(f"HAZIR: {[f for f in HAZIR_DOSYA if (HAZIR / f).exists()]}")
    eksik = [f for f in HAZIR_DOSYA if not (HAZIR / f).exists()]
    if eksik:
        raise FileNotFoundError(f"HAZIR eksik: {eksik}")
    for k, f in (("names", "cancer_name_gold.png"), ("names", "libra_name_gold.png"),
                 ("parts", "tagline.png")):
        fetch(FOLDERS[k], f, REF / k)
    log("isim/tagline plaka asillari indi")
    return d


def met_al(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    m = ink_mask(a)
    x0, y0, x1, y1 = bbox_of(m)
    prof = []
    for y in range(y0, y1):
        mr = m[y, x0:x1]
        prof.append(np.median(a[y, x0:x1][mr][:, :3], axis=0).tolist() if mr.sum() >= 3
                    else (prof[-1] if prof else [200., 170., 110.]))
    al = a[..., 3]
    return {"png": list(im.size), "bb": [x0, y0, x1, y1], "prof": prof,
            "yumusak": bool(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1) > 0.45)}


def altin(mask_img, met, duzelt=None):
    m = np.asarray(mask_img).astype(np.float32) / 255.0
    h, w = m.shape
    prof = np.asarray(met["prof"], np.float32)
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    g = prof[lo] * (1 - t) + prof[hi] * t
    if duzelt:
        g = g * np.asarray(duzelt, np.float32)[None, :]
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


def koy(t, im, kutu):
    top, left = kutu[0], kutu[1]
    x, y = int(round(left)), int(round(top))
    kx, ky = max(-x, 0), max(-y, 0)
    if kx or ky:
        im = im.crop((kx, ky, im.width, im.height))
        x, y = x + kx, y + ky
    t.alpha_composite(im.crop((0, 0, min(im.width, t.width - x),
                               min(im.height, t.height - y))), (x, y))


def zemin_kur(ana_duzelt=None):
    t = Image.new("RGBA", TUVAL, (0, 0, 0, 255))
    for f, k in (("bg.png", "bg"), ("ring.png", "ring"), ("main.png", "main"),
                 ("sym_left.png", "sym_left"), ("sym_right.png", "sym_right"),
                 ("infinity.png", "infinity")):
        im = Image.open(HAZIR / f).convert("RGBA")
        if f == "main.png" and ana_duzelt:
            a = np.asarray(im).astype(np.float32)
            a[..., :3] = np.clip(a[..., :3] * np.asarray(ana_duzelt, np.float32)[None, None, :],
                                 0, 255)
            im = Image.fromarray(a.astype(np.uint8), "RGBA")
        koy(t, im, B[k])
    return t


def a_teshis(d):
    """Ana sembol farkini olc; > ESIK ise kanal duzeltmesi turet."""
    t = zemin_kur()
    d["once"] = {k: bolge_olc(t, B[k], k) for k in ("main", "sym_left", "sym_right", "ring")}
    for k, v in d["once"].items():
        f = fark(d["ref_olcum"][k], v)
        log(f"ONCE {k:10s} pilot={json.dumps(v, ensure_ascii=False)} fark={f}")
    r, p = d["ref_olcum"]["main"], d["once"]["main"]
    if r.get("rgb") and p.get("rgb") and fark(r, p) > ESIK:
        oran = [max(min(rr / max(pp, 1e-3), 2.5), 0.4) for rr, pp in zip(r["rgb"], p["rgb"])]
        d["ana_duzelt"] = [round(v, 4) for v in oran]
        log(f"ana sembol duzeltmesi (referans/pilot kanal orani): {d['ana_duzelt']}")
        t2 = zemin_kur(d["ana_duzelt"])
        d["sonra"] = {k: bolge_olc(t2, B[k], k) for k in ("main",)}
        log(f"SONRA main={json.dumps(d['sonra']['main'], ensure_ascii=False)} "
            f"fark={fark(r, d['sonra']['main'])}")
    else:
        d["ana_duzelt"] = None
        log("ana sembol farki esik altinda; duzeltme uygulanmiyor")
    return d


def a_olc(d):
    d["met"] = {"cancer": met_al(REF / "names" / "cancer_name_gold.png"),
                "libra": met_al(REF / "names" / "libra_name_gold.png"),
                "tagline": met_al(REF / "parts" / "tagline.png")}
    # tagline: referans cam yuksekligine oturan punto, NORMAL harf araligi
    tfp = FONT_DIR / TAG_FONT
    d["tag_punto"] = cap_icin_boyut(tfp, ORIG_TAGLINE, d["ref_tag_h"], TAG_W)
    d["tag_maks_w"] = B["tagline"][2]
    log(f"tagline: referans cam h={d['ref_tag_h']} -> punto {d['tag_punto']}, "
        f"harf araligi 0 (sikistirma yok), maks genislik {d['tag_maks_w']:.0f}")
    # renk kontrolu: orijinal tagline metniyle uret, referansla karsilastir
    cr, _ = ciz_metin(font_yukle(tfp, d["tag_punto"], TAG_W), ORIG_TAGLINE, 0.0)
    pl = altin(cr, d["met"]["tagline"])
    a = np.asarray(pl).astype(np.float32)
    mine = [round(float(v), 1) for v in np.median(a[..., :3][a[..., 3] > 40], axis=0)]
    r = d["ref_olcum"]["tagline"]["rgb"]
    fk = round(float(np.abs(np.array(mine) - np.array(r)).max()), 1)
    log(f"tagline rengi: pilot={mine} referans={r} fark={fk}")
    if fk > ESIK:
        d["tag_duzelt"] = [round(max(min(rr / max(mm, 1e-3), 2.5), 0.4), 4)
                           for rr, mm in zip(r, mine)]
        cr2, _ = ciz_metin(font_yukle(tfp, d["tag_punto"], TAG_W), ORIG_TAGLINE, 0.0)
        a2 = np.asarray(altin(cr2, d["met"]["tagline"], d["tag_duzelt"])).astype(np.float32)
        m2 = [round(float(v), 1) for v in np.median(a2[..., :3][a2[..., 3] > 40], axis=0)]
        log(f"tagline duzeltmesi {d['tag_duzelt']} -> {m2} fark="
            f"{float(np.abs(np.array(m2) - np.array(r)).max()):.1f}")
    else:
        d["tag_duzelt"] = None
    # isim harf araligi (onayli plakadan, degistirilmiyor)
    from kisisel_pilot import tracking_icin
    trs = []
    for ad, k in (("CANCER", "cancer"), ("LIBRA", "libra")):
        met = d["met"][k]
        x0, y0, x1, y1 = met["bb"]
        h = 200
        s = cap_icin_boyut(FONT_DIR / ISIM_FONT, ad, h, ISIM_W)
        ft = font_yukle(FONT_DIR / ISIM_FONT, s, ISIM_W)
        trs.append(tracking_icin(ft, ad, int((x1 - x0) * h / (y1 - y0))) / s)
    d["isim_tr"] = sum(trs) / len(trs)
    log(f"isim harf araligi orani {d['isim_tr']:.4f} (onayli, degismedi)")
    return d


def hedef(kutu, met):
    top, left, w, h = kutu
    pw, ph = met["png"]
    x0, y0, x1, y1 = met["bb"]
    oy = h / ph
    return left + w / 2, top + ((y0 + y1) / 2) * oy, (y1 - y0) * oy


def yaz(t, metin, fp, wght, met, kutu, tr_orani, maks_w=None, punto=None, duzelt=None):
    mx, my, cam_h = hedef(kutu, met)
    tam = punto or cap_icin_boyut(fp, metin, cam_h, wght)
    size, olcek = tam, 1.0
    cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    for _ in range(6):                       # tasarsa PUNTO kuculur (yatay sikistirma yok)
        if not maks_w or cr.width <= maks_w:
            break
        olcek *= min(maks_w / cr.width, 0.99)
        size = max(int(round(tam * olcek)), 4)
        cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    pl = altin(cr, met, duzelt)
    t.alpha_composite(pl, (int(round(mx - pl.width / 2)), int(round(my - pl.height / 2))))
    return {"metin": metin, "punto": size, "olcek": round(olcek, 3), "genislik": pl.width,
            "yukseklik": pl.height}


def a_uret(d, kod):
    t = zemin_kur(d.get("ana_duzelt"))
    ifp, tfp = FONT_DIR / ISIM_FONT, FONT_DIR / TAG_FONT
    sol = yaz(t, NEW_LEFT, ifp, ISIM_W, d["met"]["cancer"], B["name_left"], d["isim_tr"])
    sag = yaz(t, NEW_RIGHT, ifp, ISIM_W, d["met"]["libra"], B["name_right"], d["isim_tr"])
    tg = yaz(t, TAGLINES[kod], tfp, TAG_W, d["met"]["tagline"], B["tagline"], 0.0,
             maks_w=d["tag_maks_w"], punto=d["tag_punto"], duzelt=d.get("tag_duzelt"))
    t.save(OUT / f"poster_{kod}2.png")
    q = kaydet(t, OUT / f"PILOT_{kod}2.jpg", 1_500_000)
    log(f"PILOT_{kod}2.jpg q={q} {(OUT / f'PILOT_{kod}2.jpg').stat().st_size / 1e6:.2f} MB "
        f"| {json.dumps(tg, ensure_ascii=False)}")
    gonder(f"PILOT_{kod}2.jpg")
    d.setdefault("yerlesim", {})[kod] = {"sol": sol, "sag": sag, "tagline": tg}
    return d


def kaydet(im, path, maks):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 66, 60, 54, 48):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= maks:
            return q
    return q


def orij_poster():
    t = zemin_kur()
    for f, k in (("orij_name_left.png", "name_left"), ("orij_name_right.png", "name_right"),
                 ("orij_tagline.png", "tagline")):
        koy(t, Image.open(HAZIR / f).convert("RGBA"), B[k])
    return t


def a_yakin(d):
    orij, pa = orij_poster(), Image.open(OUT / "poster_A2.png").convert("RGBA")
    # Mo: soldaki isim kesiliyordu -> kirpim isim kutularini da kapsiyor
    x0 = int(min(B["name_left"][1], B["sym_left"][1]) - 120)
    x1 = int(max(B["name_right"][1] + B["name_right"][2],
                 B["sym_right"][1] + B["sym_right"][2]) + 120)
    bant = (max(x0, 0), int(B["name_left"][0] - 70), min(x1, TUVAL[0]),
            int(B["name_left"][0] + B["name_left"][3] + 70))
    log(f"YAKIN_ISIMLER2 kirpim: {bant} (genislik {bant[2] - bant[0]})")
    u, a = orij.crop(bant), pa.crop(bant)
    yi = Image.new("RGB", (u.width, u.height * 2 + 16), (10, 12, 26))
    yi.paste(u.convert("RGB"), (0, 0))
    yi.paste(a.convert("RGB"), (0, u.height + 16))
    yi = yi.resize((1500, int(yi.height * 1500 / yi.width)), Image.LANCZOS)
    log(f"YAKIN_ISIMLER2 q={kaydet(yi, OUT / 'YAKIN_ISIMLER2.jpg', 400_000)}")
    gonder("YAKIN_ISIMLER2.jpg")

    tb = (int(B["tagline"][1] - 110), int(B["tagline"][0] - 50),
          int(B["tagline"][1] + B["tagline"][2] + 110),
          int(B["tagline"][0] + B["tagline"][3] + 50))
    ref = Image.open(OUT / REFERANS).convert("RGB")
    ser = [ref.crop(tb), orij.crop(tb).convert("RGB")] + [
        Image.open(OUT / f"poster_{k}2.png").convert("RGB").crop(tb) for k in ("A", "B", "C")]
    yt = Image.new("RGB", (ser[0].width, sum(s.height for s in ser) + 16 * len(ser)),
                   (10, 12, 26))
    y = 0
    for s in ser:
        yt.paste(s, (0, y))
        y += s.height + 16
    yt = yt.resize((1500, int(yt.height * 1500 / yt.width)), Image.LANCZOS)
    log(f"YAKIN_TAGLINE2 q={kaydet(yt, OUT / 'YAKIN_TAGLINE2.jpg', 400_000)} (ust: REFERANS)")
    gonder("YAKIN_TAGLINE2.jpg")
    return d


def a_kiyas(d):
    ref = Image.open(OUT / REFERANS).convert("RGB")
    pa = Image.open(OUT / "poster_A2.png").convert("RGB")
    W = 900
    ust = Image.new("RGB", (W * 2 + 24, int(W * 3000 / 2400)), (10, 12, 26))
    ust.paste(ref.resize((W, int(W * 3000 / 2400)), Image.LANCZOS), (0, 0))
    ust.paste(pa.resize((W, int(W * 3000 / 2400)), Image.LANCZOS), (W + 24, 0))
    kes = []
    for ad, kutu, pay in (("ANA SEMBOL", B["main"], 30), ("TAGLINE", B["tagline"], 60)):
        bx = (int(kutu[1] - pay), int(kutu[0] - pay),
              int(kutu[1] + kutu[2] + pay), int(kutu[0] + kutu[3] + pay))
        a, b = ref.crop(bx), pa.crop(bx)
        o = min(W / a.width, 520 / a.height)
        kes.append((a.resize((int(a.width * o), int(a.height * o)), Image.LANCZOS),
                    b.resize((int(b.width * o), int(b.height * o)), Image.LANCZOS)))
    alt_h = sum(a.height for a, _ in kes) + 24 * len(kes)
    kn = Image.new("RGB", (ust.width, ust.height + 24 + alt_h), (10, 12, 26))
    kn.paste(ust, (0, 0))
    y = ust.height + 24
    for a, b in kes:
        kn.paste(a, (0, y))
        kn.paste(b, (W + 24, y))
        y += a.height + 24
    o = 1600 / kn.width
    kn = kn.resize((1600, int(kn.height * o)), Image.LANCZOS)
    log(f"KIYAS_REFERANS q={kaydet(kn, OUT / 'KIYAS_REFERANS.jpg', 900_000)} "
        "(sol referans, sag PILOT_A2)")
    gonder("KIYAS_REFERANS.jpg")

    m = ["# Pilot v4 - referans karsilastirmasi", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## Ana sembol ve komsu ogeler (murekkep pikselleri, 2400x3000 tuval)", "",
         "| bolge | referans RGB | pilot RGB (once) | fark | doygunluk ref/pilot | parlaklik ref/pilot |",
         "| --- | --- | --- | --- | --- | --- |"]
    for k in ("main", "sym_left", "sym_right", "ring"):
        r, p = d["ref_olcum"][k], d["once"][k]
        m.append(f"| {k} | {r['rgb']} | {p['rgb']} | {fark(r, p)} | "
                 f"{r.get('doygunluk')}/{p.get('doygunluk')} | "
                 f"{r.get('parlaklik')}/{p.get('parlaklik')} |")
    if d.get("ana_duzelt"):
        s = d.get("sonra", {}).get("main")
        m += ["", f"Ana sembol kanal duzeltmesi (referans/pilot): {d['ana_duzelt']}",
              f"Duzeltme sonrasi: {s['rgb'] if s else '-'} "
              f"fark={fark(d['ref_olcum']['main'], s) if s else '-'}"]
    else:
        m += ["", "Ana sembol farki esik (5 birim) altinda kaldi; duzeltme uygulanmadi."]
    m += ["", "## Tagline", "",
          f"- Font: EB Garamond Italic {TAG_W} (Regular), harf araligi 0, yatay sikistirma yok",
          f"- Referans cam yuksekligi {d['ref_tag_h']} px -> punto {d['tag_punto']}",
          f"- Renk duzeltmesi: {d.get('tag_duzelt') or 'gerekmedi'}"]
    for k, v in d.get("yerlesim", {}).items():
        t = v["tagline"]
        m.append(f"- {k}: punto {t['punto']} (%{t['olcek'] * 100:.0f}), "
                 f"genislik {t['genislik']} px / kutu {d['tag_maks_w']:.0f}")
    (OUT / "RAPOR_V4.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("RAPOR_V4.md")
    return d


ADIMLAR = ["ref", "indir", "teshis", "olc", "uret_A", "uret_B", "uret_C", "yakin", "kiyas"]


def adim_kos(ad, url):
    d = durum_oku()
    if url:
        d["url"] = url
    fn = {"ref": a_ref, "indir": a_indir, "teshis": a_teshis, "olc": a_olc,
          "yakin": a_yakin, "kiyas": a_kiyas}.get(ad)
    d = fn(d) if fn else a_uret(d, ad.split("_")[1])
    d.pop("url", None)
    DURUM.write_text(json.dumps(d, ensure_ascii=False))


def orkestra(sinir, url):
    OUT.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    if DURUM.exists():
        DURUM.unlink()
    log(f"pilot4 basladi | {len(ADIMLAR)} asama, ayri surec, timeout {sinir}s")
    sureler = {}
    for ad in ADIMLAR:
        t = time.time()
        log(f"=== ASAMA BASLADI: {ad}")
        cmd = [sys.executable, __file__, "--adim", ad]
        if ad == "ref" and url:
            cmd += ["--url", url]
        try:
            r = subprocess.run(cmd, timeout=sinir, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            log(f"!!! ZAMAN ASIMI: {ad} ({sinir}s)")
            sys.exit(1)
        s = round(time.time() - t, 1)
        sureler[ad] = s
        if r.returncode != 0:
            log(f"!!! ASAMA HATASI: {ad} (cikis {r.returncode}, {s}s)")
            sys.exit(1)
        log(f"=== ASAMA BITTI: {ad} ({s}s)")
    log(f"TOPLAM {time.time() - T0:.1f}s | {json.dumps(sureler)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adim", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--sinir", type=int, default=420)
    a = ap.parse_args()
    if a.adim:
        adim_kos(a.adim, a.url)
    else:
        orkestra(a.sinir, a.url)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
