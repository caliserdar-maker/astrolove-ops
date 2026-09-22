#!/usr/bin/env python3
"""
LEGACY asama notu - Kisisellestirme pilotu v7 (Mo kararlari, 21 Eyl 2026).

Asagidaki maddeler v7 kosusunun tarihsel degisiklik kaydidir. Guncel uretim
yerlesimi `pilot12.d_olcek` ile iki ismi birlikte kucultur; bu dosyadaki
"yalniz kendisi" ifadesi guncel uretim sozlesmesi degildir.

DEGISEN OGELER
  - Tagline kabartmasi: bant disi sabit renk KALKTI. Kabartma glifin kendi
    seklinden turetilir (bulanik maskenin dikey gradyani = yuzey normali);
    koyu kenar her cizginin GERCEK alt kenarinda, taban cizgisinde degil.
    Metal gecis bant sinirinda yansitilarak kesintisiz surer.
  - Tagline icin iki secenek uretilir (Mo gozle secer):
      SECENEK 1: altin profili cancer_name_gold.png (alt ucu duzlestirilmis).
      SECENEK 2: altin profili REFERANS posterin kendi "Two Souls" satiri.
    Isimler her iki secenekte de cancer/libra plaka profiliyle, degismeden.
  - Isim puntosu artik AKSANI CIKARILMIS metinden hesaplanir (U/O/I noktalari
    ve S/C cengelleri cam yuksekligini buyutup govdeyi kucultuyordu).
    Aksansiz isimde cikti onayliyla birebir kalir.
  - Isim ile sonsuzluk arasi bosluk referanstakinden az olamaz; sigmayan isim
    YALNIZ KENDISI orantili kuculur.
  - Ustteki kucuk sembollerle en az 20 px bosluk (aksan noktalari dahil).

DEGISMEYEN
  - Zemin (referans poster + bg.png temizligi), isim fontu/agirligi/harf
    araligi/altin dokusu, tagline fontu (EBG-It 400), puntosu (102), cap
    yuksekligi (71).

Taban kapisi (Mo, 21 Eyl): "oran <= 1.5" kaldirildi - referansin kendisi bu
olcutte 8.63 veriyor. Bloklayan esik: taban sicramasi <= A4'un yarisi (48).
"""
import argparse
import json
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, rc, tracking_icin)
from pilot6 import (altin as altin_isim, hedef, kumeler, met_al, ref_maske,
                    satir_kumeleri, temizle, ciz_cap, cap_punto, isim_kontrol,
                    ONAYLI, ONAYLI_DIR, B, BG_OFS, LUMA, MUREKKEP, OLCEK, TUVAL,
                    IOU_H, REFERANS, ISIM_FONT, ISIM_W, TAG_FONT, TAG_W,
                    TAG_PUNTO, TAG_CAP, TAG_MAKS_W, kaydet)
import pilot6

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
T0 = time.time()

# olculen sabitler
A4_TABAN = 97.6                 # mevcut A4'un taban sicramasi
TABAN_ESIK = 48.0               # Mo: A4'un yarisi
GOVDE_ESIK = 3.0
SIGMA, KH, KS = 1.8, 0.10, 0.20
DUZ_ORAN = 0.80
KUYRUK_METNI = "Gypsy Jewel Çağla Şebnem"
CIFTLER = [(NEW_LEFT, NEW_RIGHT), ("ŞÜKRÜ", "İPEK"),
           ("GÖKÇE", "MAXIMILIAN"), ("ÇAĞLA", "ÖMER")]
SEMBOL_BOSLUK = 20


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


def sade(s):
    """Aksanlari cikar: punto harf GOVDESINDEN hesaplansin."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").replace("ı", "i").replace("İ", "I")


# ------------------------------------------------------------------ altin


def kuyruk_duzlestir(prof, oran=DUZ_ORAN):
    """Profilin KENDI kabartma golgesini alt ucta yerinde duzlestirir.

    Gerdirme yok: indeks eslemesi degismedigi icin govde A4 ile ayni kalir.
    Alt kenar golgesi artik sekilden geliyor.
    """
    p = np.asarray(prof, np.float32).copy()
    L = p @ LUMA
    ok = np.nonzero(L >= L.max() * oran)[0]
    p[ok[-1] + 1:] = p[ok[-1]]
    return p, int(ok[-1])


def referans_profil(ref, kutu, esik=130):
    """Referans posterdeki tagline satirindan altin profili ornekle."""
    x0, y0, x1, y1 = kutu
    a = np.asarray(ref.convert("RGB")).astype(np.float32)[y0:y1, x0:x1]
    L = a @ LUMA
    m = L > esik
    prof, son = [], None
    for i in range(a.shape[0]):
        if m[i].sum() >= 6:
            son = np.median(a[i][m[i]], axis=0)
        prof.append(son if son is not None else np.array([200., 170., 110.]))
    return np.asarray(prof, np.float32)


def altin_sekil(mask, prof, bant, yumusak=False, sigma=SIGMA, kh=KH, ks=KS):
    """Metal gecis + GLIF SEKLINDEN kabartma.

    - Gecis bant sinirinda yansitilir (bant disi sabit renk yok).
    - Kabartma: bulanik maskenin dikey gradyani; ust kenar parlar, alt kenar
      koyulasir - her cizginin kendi kenarinda.
    """
    m = np.asarray(mask).astype(np.float32) / 255.0
    h, w = m.shape
    ust, taban = bant
    r = np.arange(h, dtype=np.float32)
    u = (r - ust) / max(taban - ust, 1)
    u = np.where(u < 0, -u, u)
    u = np.where(u > 1, 2 - u, u)
    u = np.clip(u, 0, 1)
    idx = u * (len(prof) - 1)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    base = (prof[lo] * (1 - t) + prof[hi] * t)[:, None, :] * np.ones((1, w, 1), np.float32)
    hf = np.asarray(Image.fromarray((m * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(sigma))).astype(np.float32) / 255.0
    gy = np.gradient(hf, axis=0)
    s = float(np.max(np.abs(gy))) or 1.0
    sh = np.clip(gy / s, -1, 1)[:, :, None]
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(base * (1 + kh * np.clip(sh, 0, 1) + ks * np.clip(sh, -1, 0)),
                         0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(o, "RGBA")


# ------------------------------------------------------------------ olcum


def satir_sicrama(plaka, bant):
    """Satir ortalamasi luma; taban ve kuyruk satirindaki sicrama + govde medyani."""
    a = np.asarray(plaka).astype(np.float32)
    mask = a[..., 3] > 120
    L = a[..., :3] @ LUMA
    h = a.shape[0]
    ort = np.array([L[i][mask[i]].mean() if mask[i].sum() > 3 else np.nan for i in range(h)])
    d = np.abs(np.diff(ort))
    ust, taban = bant
    gov = d[ust + 4:taban - 6]
    gov = gov[~np.isnan(gov)]
    tb = float(np.nanmax(d[max(taban - 4, 0):min(taban + 3, len(d))]))
    # kuyruk satiri: bandin altinda murekkebin basladigi ilk satir
    alt = [i for i in range(taban + 1, h) if mask[i].sum() > 3]
    ky = float(np.nanmax(d[alt[0] - 1:alt[0] + 2])) if alt else float("nan")
    return {"taban": round(tb, 2), "kuyruk": round(ky, 2),
            "govde_medyan": round(float(np.nanmedian(gov)), 2)}


def govde_farki(yeni, a4, bant):
    a, b = np.asarray(yeni).astype(np.float32), np.asarray(a4).astype(np.float32)
    m = (a[..., 3] > 120) & (b[..., 3] > 120)
    ic = np.asarray(Image.fromarray((m * 255).astype(np.uint8), "L").filter(
        ImageFilter.MinFilter(5))) > 127
    g = np.zeros_like(ic)
    g[bant[0] + 5:bant[1] - 5] = ic[bant[0] + 5:bant[1] - 5]
    return round(float(np.abs(a[..., :3][g] - b[..., :3][g]).mean()), 2) if g.sum() else None


# ------------------------------------------------------------------ isimler


def isim_plaka(metin, met, kutu, tr_orani, maks_yari):
    """Punto aksansiz govdeden; sigmazsa YALNIZ bu isim orantili kuculur."""
    mx, my, cam_h = hedef(kutu, met)
    fp = FONT_DIR / ISIM_FONT
    tam = cap_icin_boyut(fp, sade(metin), cam_h, ISIM_W)
    size, olcek = tam, 1.0
    cr, _ = ciz_metin(font_yukle(fp, size, ISIM_W), metin, size * tr_orani)
    for _ in range(6):
        if cr.width / 2 <= maks_yari:
            break
        olcek *= min(maks_yari / (cr.width / 2), 0.99)
        size = max(int(round(tam * olcek)), 4)
        cr, _ = ciz_metin(font_yukle(fp, size, ISIM_W), metin, size * tr_orani)
    pl = altin_isim(cr, met)
    govde_h = ciz_metin(font_yukle(fp, size, ISIM_W), sade(metin), size * tr_orani)[0].height
    return pl, {"metin": metin, "punto": size, "olcek": round(olcek, 3),
                "genislik": pl.width, "govde_h": govde_h,
                "kuculdu": olcek < 0.999}


# ------------------------------------------------------------------ akis


def kos(indir=True):
    OUT.mkdir(parents=True, exist_ok=True)
    d = {"degisen": [
        "tagline kabartmasi glif seklinden (bant disi sabit renk kaldirildi)",
        "tagline icin iki altin profili secenegi uretildi",
        "isim puntosu aksani cikarilmis metinden hesaplaniyor",
        "isim-sonsuzluk boslugu ve kucuk sembol acikligi kurallari eklendi"],
        "degismeyen": [
        "zemin (referans poster + bg.png temizligi)",
        "isim fontu, agirligi, harf araligi ve altin dokusu (ONAYLI.json)",
        "tagline fontu EBG-It 400, punto 102, cap yuksekligi 71"]}
    if indir:
        rc("copy", f"{DEST}/{REFERANS}", str(OUT))
        HAZIR.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST}/HAZIR/bg.png", str(HAZIR))
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, REF / "names")
        log("referans + bg.png + isim plakalari indi")
    ref = Image.open(OUT / REFERANS).convert("RGB")
    if ref.size != TUVAL:
        ref = ref.resize(TUVAL, Image.LANCZOS)
    bg = Image.open(HAZIR / "bg.png")

    pilot6.OUT, pilot6.REF, pilot6.HAZIR = OUT, REF, HAZIR
    temiz, geo = pilot6.zemin_hazirla(ref, bg)
    d["geo"] = geo
    sonsuz = geo["sonsuzluk"]
    tag_kutu = [geo["tag_x"][0], geo["tag_y"][0], geo["tag_x"][1], geo["tag_y"][1]]
    isim_km = satir_kumeleri(np.asarray(ref).astype(np.float32) @ LUMA, *geo["isim_y"])
    d["ref_bosluk"] = [sonsuz[0] - isim_km[0][1], isim_km[-1][0] - sonsuz[1]]
    min_bosluk = min(d["ref_bosluk"])
    log(f"referans bosluklari sol={d['ref_bosluk'][0]} sag={d['ref_bosluk'][1]} "
        f"-> gereken en az {min_bosluk} px")

    met_c = met_al(REF / "names" / "cancer_name_gold.png")
    met_l = met_al(REF / "names" / "libra_name_gold.png")
    isim_tr = pilot6.isim_tr_hesapla(met_c, met_l,
                                     {"cancer": REF / "names" / "cancer_name_gold.png",
                                      "libra": REF / "names" / "libra_name_gold.png"})
    d["isim_tr"] = round(isim_tr, 4)
    prof_c = np.asarray(met_c["prof"], np.float32)

    # --- iki tagline profili
    p1, kes1 = kuyruk_duzlestir(prof_c)
    ham2 = referans_profil(ref, tag_kutu)
    p2, kes2 = kuyruk_duzlestir(ham2)
    d["profiller"] = {"secenek1": {"kaynak": "cancer_name_gold.png", "satir": len(p1),
                                   "duzlestirme_indeksi": kes1},
                      "secenek2": {"kaynak": f"REFERANS tagline {tag_kutu}", "satir": len(p2),
                                   "duzlestirme_indeksi": kes2}}
    log(f"profiller: {json.dumps(d['profiller'], ensure_ascii=False)}")

    def tagline_plaka(metin, prof):
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, metin)
        return altin_sekil(cr, prof, (cu, ct)), (cu, ct), cr

    # --- olcum: A4, secenek1, secenek2, referans
    d["olcum"] = {}
    cr_ham, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, TAGLINES["A"])
    a4 = pilot6.altin_bant(cr_ham, prof_c, (cu, ct), False)
    d["olcum"]["A4"] = satir_sicrama(a4, (cu, ct))
    for ad, prof in (("secenek1", p1), ("secenek2", p2)):
        pl = altin_sekil(cr_ham, prof, (cu, ct))
        d["olcum"][ad] = satir_sicrama(pl, (cu, ct))
        d["olcum"][ad]["govde_farki_A4"] = govde_farki(pl, a4, (cu, ct))
    # referansin kendi olcumu
    rs = np.asarray(ref.convert("RGB")).astype(np.float32)
    rl = rs @ LUMA
    sub = rl[tag_kutu[1] - 4:tag_kutu[3] + 10, tag_kutu[0]:tag_kutu[2]]
    mm = sub > MUREKKEP
    ort = np.array([sub[i][mm[i]].mean() if mm[i].sum() > 3 else np.nan for i in range(sub.shape[0])])
    dd = np.abs(np.diff(ort))
    cu_r = 4
    ct_r = 4 + (tag_kutu[3] - tag_kutu[1])
    gov_r = dd[cu_r + 4:ct_r - 6]
    gov_r = gov_r[~np.isnan(gov_r)]
    d["olcum"]["REFERANS"] = {"taban": round(float(np.nanmax(dd[ct_r - 4:ct_r + 3])), 2),
                              "kuyruk": None,
                              "govde_medyan": round(float(np.nanmedian(gov_r)), 2)}
    for k, v in d["olcum"].items():
        log(f"OLCUM {k:9s}: {json.dumps(v)}")

    # --- KAPI: taban sicramasi
    d["kapi_taban"] = {k: {"taban": d["olcum"][k]["taban"],
                           "gecti": d["olcum"][k]["taban"] <= TABAN_ESIK}
                       for k in ("secenek1", "secenek2")}
    d["kapi_govde"] = {"secenek1": d["olcum"]["secenek1"]["govde_farki_A4"] <= GOVDE_ESIK}
    log(f"KAPI taban (esik {TABAN_ESIK}): {json.dumps(d['kapi_taban'])}")
    log(f"KAPI govde (secenek1, esik {GOVDE_ESIK}): {d['kapi_govde']}")
    if not all(v["gecti"] for v in d["kapi_taban"].values()):
        raise SystemExit(f"TABAN KAPISI BASARISIZ: {d['kapi_taban']}")
    if not d["kapi_govde"]["secenek1"]:
        raise SystemExit(f"GOVDE KAPISI BASARISIZ: {d['olcum']['secenek1']['govde_farki_A4']}")

    # --- poster kurucu
    sembol_alt = max((BOX["sym_left"][0] + BOX["sym_left"][3]) * OLCEK,
                     (BOX["sym_right"][0] + BOX["sym_right"][3]) * OLCEK)

    def poster(sol_ad, sag_ad, tag_metin, prof):
        t = temiz.convert("RGBA").copy()
        bilgi = {}
        for yan, ad, met, kutu in (("sol", sol_ad, met_c, B["name_left"]),
                                   ("sag", sag_ad, met_l, B["name_right"])):
            mx, my, _ = hedef(kutu, met)
            maks_yari = (sonsuz[0] - min_bosluk - mx) if yan == "sol" else \
                        (mx - (sonsuz[1] + min_bosluk))
            pl, b = isim_plaka(ad, met, kutu, isim_tr, maks_yari)
            x = int(round(mx - pl.width / 2))
            y = int(round(my - pl.height / 2))
            t.alpha_composite(pl, (x, y))
            b["x"] = [x, x + pl.width]
            b["bosluk"] = (sonsuz[0] - b["x"][1]) if yan == "sol" else (b["x"][0] - sonsuz[1])
            b["bosluk_ok"] = b["bosluk"] >= min_bosluk
            a = np.asarray(pl)[..., 3] > 40
            ys = np.nonzero(a.any(axis=1))[0]
            b["ust_y"] = int(y + ys[0])
            b["sembol_acikligi"] = round(b["ust_y"] - sembol_alt, 1)
            b["sembol_ok"] = b["sembol_acikligi"] >= SEMBOL_BOSLUK
            bilgi[yan] = b
        bilgi["cap_farki"] = abs(bilgi["sol"]["govde_h"] - bilgi["sag"]["govde_h"])
        pl, bant, _ = tagline_plaka(tag_metin, prof)
        t.alpha_composite(pl, (int(round(TUVAL[0] / 2 - pl.width / 2)),
                               int(round((tag_kutu[1] + tag_kutu[3]) / 2 - pl.height / 2))))
        bilgi["tagline_genislik"] = pl.width
        return t, bilgi

    # --- SECENEK1_A / SECENEK2_A
    d["secenekler"] = {}
    posterler = {}
    for ad, prof in (("SECENEK1", p1), ("SECENEK2", p2)):
        t, b = poster(NEW_LEFT, NEW_RIGHT, TAGLINES["A"], prof)
        posterler[ad] = t
        d["secenekler"][ad] = b
        t.convert("RGB").save(OUT / f"{ad}_A.png")
        q = kaydet(t, OUT / f"{ad}_A.jpg")
        log(f"{ad}_A.jpg q={q} {(OUT / f'{ad}_A.jpg').stat().st_size / 1e6:.2f} MB "
            f"| {json.dumps(b, ensure_ascii=False)}")
        gonder(f"{ad}_A.jpg")
        if ad == "SECENEK1":
            d["isim_kontrol"] = isim_kontrol(t)
            log(f"ISIM KONTROL: {json.dumps(d['isim_kontrol'])}")
            if not d["isim_kontrol"]["gecti"]:
                raise SystemExit(f"ISIM KONTROL BASARISIZ: {d['isim_kontrol']}")

    kiyas(d, ref, p1, p2, prof_c, tag_kutu)
    kuyruk_test(d, p1, p2, prof_c)
    isim_test(d, poster, p1)
    rapor(d)
    gonder("TEMIZ_ZEMIN.jpg")
    return d


def buyut(im, k=3):
    return im.resize((im.width * k, im.height * k), Image.LANCZOS)


def kiyas(d, ref, p1, p2, prof_c, tag_kutu):
    """'Began' 3x: ust referans 'Two Souls', orta secenek1, alt secenek2."""
    r = ref.crop((tag_kutu[0], tag_kutu[1] - 8, tag_kutu[0] + 300, tag_kutu[3] + 14))
    parcalar = [("REFERANS  Two Souls", buyut(r))]
    for ad, prof in (("SECENEK 1", p1), ("SECENEK 2", p2)):
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, TAGLINES["A"])
        pl = altin_sekil(cr, prof, (cu, ct))
        kn = Image.new("RGB", (pl.width, pl.height), (11, 16, 40))
        kn.paste(pl.convert("RGB"), (0, 0), pl)
        # "It Be-gan" bolgesi: ilk ~300 px
        parcalar.append((ad, buyut(kn.crop((0, 0, min(300, kn.width), kn.height)))))
    gen = max(p.width for _, p in parcalar)
    kn = Image.new("RGB", (gen, sum(p.height + 20 for _, p in parcalar)), (11, 16, 40))
    y = 0
    for _, p in parcalar:
        kn.paste(p, (0, y))
        y += p.height + 20
    o = min(1600 / kn.width, 1.0)
    kaydet(kn.resize((int(kn.width * o), int(kn.height * o)), Image.LANCZOS),
           OUT / "SECENEK_KIYAS.jpg", 800_000)
    gonder("SECENEK_KIYAS.jpg")


def kuyruk_test(d, p1, p2, prof_c):
    cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, KUYRUK_METNI)
    d["kuyruk_olcum"] = {}
    parcalar = []
    for ad, prof in (("SECENEK 1", p1), ("SECENEK 2", p2)):
        pl = altin_sekil(cr, prof, (cu, ct))
        d["kuyruk_olcum"][ad] = satir_sicrama(pl, (cu, ct))
        kn = Image.new("RGB", (pl.width + 30, pl.height + 30), (11, 16, 40))
        kn.paste(pl.convert("RGB"), (15, 15), pl)
        parcalar.append(buyut(kn, 2))
        log(f"KUYRUK {ad}: {json.dumps(d['kuyruk_olcum'][ad])}")
    kn = Image.new("RGB", (max(p.width for p in parcalar),
                           sum(p.height + 20 for p in parcalar)), (11, 16, 40))
    y = 0
    for p in parcalar:
        kn.paste(p, (0, y))
        y += p.height + 20
    o = min(1700 / kn.width, 1.0)
    kaydet(kn.resize((int(kn.width * o), int(kn.height * o)), Image.LANCZOS),
           OUT / "KUYRUK_TEST2.jpg", 800_000)
    gonder("KUYRUK_TEST2.jpg")


def isim_test(d, poster, p1):
    bant = (int(min(B["name_left"][1], B["sym_left"][1]) - 120), int(B["name_left"][0] - 80),
            int(max(B["name_right"][1] + B["name_right"][2],
                    B["sym_right"][1] + B["sym_right"][2]) + 120),
            int(B["name_left"][0] + B["name_left"][3] + 70))
    d["ciftler"] = {}
    ser = []
    for sol, sag in CIFTLER:
        t, b = poster(sol, sag, TAGLINES["A"], p1)
        d["ciftler"][f"{sol} / {sag}"] = b
        log(f"CIFT {sol}/{sag}: {json.dumps(b, ensure_ascii=False)}")
        ser.append(t.convert("RGB").crop(bant))
    kn = Image.new("RGB", (ser[0].width, sum(s.height + 16 for s in ser)), (11, 16, 40))
    y = 0
    for s in ser:
        kn.paste(s, (0, y))
        y += s.height + 16
    kn = kn.resize((1500, int(kn.height * 1500 / kn.width)), Image.LANCZOS)
    kaydet(kn, OUT / "ISIM_TEST2.jpg", 800_000)
    gonder("ISIM_TEST2.jpg")


def rapor(d):
    o, ik = d["olcum"], d["isim_kontrol"]
    m = ["# Pilot v8 - iki tagline secenegi", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", ""] + [f"- {x}" for x in d["degisen"]] + \
        ["", "### Degismeyen (ONAYLI.json)", ""] + [f"- {x}" for x in d["degismeyen"]] + [
         "", "## Tagline olcumleri", "",
         "Taban kapisi Mo tarafindan yeniden kalibre edildi: 'oran <= 1.5' kaldirildi",
         f"(referansin kendisi o olcutte 8.63 veriyor). Bloklayan esik: taban <= {TABAN_ESIK}",
         f"(A4'un yarisi; A4 = {A4_TABAN}).", "",
         "| surum | taban sicramasi | kuyruk satiri | govde medyani | govde farki A4 |",
         "| --- | --- | --- | --- | --- |"]
    for k in ("A4", "secenek1", "secenek2", "REFERANS"):
        v = o[k]
        m.append(f"| {k} | {v['taban']} | {v.get('kuyruk') if v.get('kuyruk') is not None else '-'} "
                 f"| {v['govde_medyan']} | {v.get('govde_farki_A4', '-')} |")
    m += ["", "| kapi | secenek1 | secenek2 |", "| --- | --- | --- |",
          f"| taban <= {TABAN_ESIK} | {'GECTI' if d['kapi_taban']['secenek1']['gecti'] else 'KALDI'} "
          f"| {'GECTI' if d['kapi_taban']['secenek2']['gecti'] else 'KALDI'} |",
          f"| govde farki <= {GOVDE_ESIK} | "
          f"{'GECTI' if d['kapi_govde']['secenek1'] else 'KALDI'} | uygulanmaz (ayri profil) |",
          "", "### Profiller", ""]
    for k, v in d["profiller"].items():
        m.append(f"- {k}: {v['kaynak']} ({v['satir']} satir, alt uc "
                 f"{v['duzlestirme_indeksi']}. satirdan itibaren duzlestirildi)")
    m += ["", "Secenek 2'de tagline govdesinin A4'ten farkli olmasi beklenir: profil",
          f"referansin kendi satirindan ornekleniyor (olculen fark "
          f"{o['secenek2'].get('govde_farki_A4')}).", ""]
    m += ["## Kuyruk testi (`" + KUYRUK_METNI + "`)", "",
          "| secenek | taban | kuyruk satiri | govde medyani |", "| --- | --- | --- | --- |"]
    for k, v in d["kuyruk_olcum"].items():
        m.append(f"| {k} | {v['taban']} | {v['kuyruk']} | {v['govde_medyan']} |")
    m += ["", "## Isim kontrolu (onayli ilk PILOT_A)", "",
          f"- Sonuc: **{'GECTI' if ik['gecti'] else 'KALDI'}**, harf konumu kaymasi "
          f"{ik['kayma_px']} px, murekkep fark {ik['murekkep_fark']}", "",
          "## Isim ciftleri", "",
          f"Referans bosluklari: sol {d['ref_bosluk'][0]} px, sag {d['ref_bosluk'][1]} px "
          f"-> gereken en az {min(d['ref_bosluk'])} px.", "",
          "| cift | punto sol/sag | govde h sol/sag | cap farki | bosluk sol/sag | "
          "sembol acikligi | kuculdu |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for k, v in d["ciftler"].items():
        s, g = v["sol"], v["sag"]
        m.append(f"| {k} | {s['punto']}/{g['punto']} | {s['govde_h']}/{g['govde_h']} "
                 f"| {v['cap_farki']} | {s['bosluk']}/{g['bosluk']} "
                 f"| {s['sembol_acikligi']}/{g['sembol_acikligi']} "
                 f"| {'sag' if g['kuculdu'] else ''}{'sol' if s['kuculdu'] else ''}"
                 f"{'-' if not (s['kuculdu'] or g['kuculdu']) else ''} |")
    kotu = [k for k, v in d["ciftler"].items()
            if not (v["sol"]["bosluk_ok"] and v["sag"]["bosluk_ok"]
                    and v["sol"]["sembol_ok"] and v["sag"]["sembol_ok"])]
    m += ["", f"Bosluk ve sembol acikligi kurallari: {'hepsi saglandi' if not kotu else 'SORUN: ' + ', '.join(kotu)}",
          "", "Not: sigmayan isim yalniz kendisi kuculdugu icin o ciftte cap yuksekligi",
          "farki buyuyebilir; bu kural geregidir, asagidaki tabloda gorunur."]
    (OUT / "RAPOR_V8.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("RAPOR_V8.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    a = ap.parse_args()
    kos(indir=not a.yerel)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
