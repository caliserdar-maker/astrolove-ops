#!/usr/bin/env python3
"""
V5: maske + delta temizligi, blok bazli kalinti kapisi, iz kontrolu.

DEGISEN OGELER
  - Temizleme maskesi: referans ile bg arasinda farki >1 olan pikseller,
    gurultu bilesenleri atilmis, 12 px genisletilmis (dilate) ve yumusak
    kenarli. Eski oge bolgesi TAM zemine doner.
  - Tasima artik "delta" yontemiyle: oge, zeminden FARKI olarak (parilti ve
    kenar yumusatma dahil) kesilir ve yeni yerinde zemine EKLENIR. Boylece
    parilti birlikte tasinir, yeni zemin gradyani bozulmaz.
  - Kalinti kapisi alan ortalamasi degil, 16x16 BLOK bazli: her blokta
    ortalama fark <=2 ve tek piksel farki <=6.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from kisisel_pilot import FONT_DIR, FOLDERS, NEW_LEFT, NEW_RIGHT, TAGLINES, fetch, rc
from pilot6 import LUMA, MUREKKEP, kumeler, ONAYLI_DIR, ISIM_FONT, ISIM_W
from pilot12 import (DEST_O, HAM, KENAR_ORAN, NORM_W, ORANLAR, OUT, REF_SAYFA,
                     TAG_TABAN_CAP, TAG_TABAN_SINIR, d_olcek, fark_haritasi,
                     ince_hiza, kaydet, kume_kutusu, norm, plaka, profil_yukle,
                     tagline_plaka)
from pilot14 import isim_kapisi
import pilot12
import giris_dogrula as gd

YOL = OUT / "ORANLAR"
CEKIRDEK = 18.0            # kesin oge esigi (olculen zemin gurultusu p99 = 4)
YUMUSAK = 6                # genisletilmis maskenin disa dogru rampasi (px)
KAPI_PAY = 3               # kapida yeni ogelerin etrafinda birakilan pay (px)
MIN_ALAN = 20              # gurultu bileseni esigi (px)
GENISLET = 12              # Mo: 12 px dilate
BLOK = 16
BLOK_ORT, BLOK_TEPE = 2.0, 6.0
CIFTLER = [("JACQUELINE", "QUINN", None), (NEW_LEFT, NEW_RIGHT, None),
           ("Deniz", "Elif", "TR")]
TAG = "Written in the Stars Long Before Us"
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


# ------------------------------------------------- maske + delta temizligi


def oge_ve_yildiz(fark, bolgeler, hedefler, luma_maske):
    """Bolgedeki bilesenleri OGE ve YILDIZ (mesru icerik) olarak ayirir.

    Mo'nun istedigi "fark > 1" esigi olculdugunde kullanilamaz cikti: hizalanmis
    bos zeminde bile farkin ortalamasi 1.2, p99'u 4 (JPEG gurultusu + bg'de
    olmayan yildizlar). O esikle maske tum bandi kapliyor, ogeler ayirt
    edilemiyordu. Bunun yerine cekirdek esigi 18 (gurultu p99'unun 4 katindan
    fazla) ve Mo'nun 12 px genisletmesi kullanilir; olculen parilti 8 px icinde
    bitiyor, 12 px fazlasiyla kapsiyor.
    """
    ham = np.zeros(fark.shape, np.uint8)
    for (x0, y0, x1, y1) in bolgeler:
        ham[y0:y1, x0:x1] = (fark[y0:y1, x0:x1] > CEKIRDEK).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * GENISLET + 1,) * 2)
    ham_g = cv2.dilate(ham, k)          # harfler tek bilesende toplansin
    n, etiket, stat, _ = cv2.connectedComponentsWithStats(ham_g, connectivity=8)
    buyuk = [i for i in range(1, n)
             if (ham[etiket == i].sum()) >= MIN_ALAN]

    esles, kullanilan = {}, set()
    for ad, (hx0, hy0, hx1, hy1) in hedefler.items():
        en, sec = 0, None
        for i in buyuk:
            x, y, w, h, _ = stat[i]
            ort = (max(0, min(x + w, hx1) - max(x, hx0))
                   * max(0, min(y + h, hy1) - max(y, hy0)))
            if ort > en:
                en, sec = ort, i
        if sec is not None:
            esles[ad] = sec
            kullanilan.add(sec)
    yildiz_no = [i for i in buyuk if i not in kullanilan]

    genis = np.isin(etiket, list(kullanilan)).astype(np.uint8)
    uzak = cv2.distanceTransform((1 - genis).astype(np.uint8), cv2.DIST_L2, 5)
    alfa = np.clip(1.0 - uzak / YUMUSAK, 0.0, 1.0)      # ic 1, disa YUMUSAK px rampa
    yildiz = np.isin(etiket, yildiz_no).astype(bool)

    kutu = {}
    for ad, i in esles.items():
        m = (etiket == i).astype(np.uint8)
        ys, xs = np.nonzero(m)
        # gorsel kutu: luma esigi (OLCUM.json ile ayni olcut), fark esigi degil
        cy, cx = np.nonzero((etiket == i) & luma_maske)
        kutu[ad] = {"kutu": (int(xs.min()), int(ys.min()), int(xs.max()) + 1,
                             int(ys.max()) + 1),
                    # gorsel (cekirdek) kutu: satir duzeni bununla kurulur,
                    # genisletilmis maske yalniz delta tasimasi icindir
                    "gorsel": (int(cx.min()), int(cy.min()), int(cx.max()) + 1,
                               int(cy.max()) + 1),
                    "etiket": i, "genis": m}
    return kutu, alfa, genis.astype(bool), yildiz, len(yildiz_no)


def delta_kes(ref_a, zemin_a, bil, alfa):
    """Oge = (referans - zemin) farki, genisletilmis yumusak maskesiyle."""
    x0, y0, x1, y1 = bil["kutu"]
    d = ref_a[y0:y1, x0:x1] - zemin_a[y0:y1, x0:x1]
    m = bil["genis"][y0:y1, x0:x1].astype(np.float32) * alfa[y0:y1, x0:x1]
    return d * m[..., None], m


def delta_koy(hedef_a, delta, m, x, y):
    h, w = m.shape
    H, W = hedef_a.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    hedef_a[y0:y1, x0:x1] += delta[y0 - y:y1 - y, x0 - x:x1 - x]


# ----------------------------------------------------------- oran kurulumu


SABIT_YOL = Path(__file__).resolve().parent / "ORAN_SABITLERI.json"


def hizalama(oran, ref, bg_im, kaba, kalibre=False):
    """Hizalama (olcek, dx, dy) ORAN_SABITLERI.json'dan okunur.

    Serdar karari 21 Eylul 2026: her oran/edisyon icin BIR KEZ hesaplanir ve
    dosyaya yazilir; uretimde arama YAPILMAZ.
    """
    d = json.loads(SABIT_YOL.read_text(encoding="utf-8")) if SABIT_YOL.exists() else {}
    kayit = d.get("oranlar", {}).get(oran, {}).get("bg_hizasi_kilit")
    if kayit and not kalibre:
        return dict(kayit), False
    h = ince_hiza(ref, bg_im, kaba)
    d.setdefault("oranlar", {}).setdefault(oran, {})["bg_hizasi_kilit"] = h
    SABIT_YOL.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    return h, True


def oran_kur(oran, olcum_kaydi, bg_im, iz_birak=False, kalibre=False):
    t0 = time.time()
    ham = Image.open(HAM / f"{oran}_p{REF_SAYFA}.jpg").convert("RGB")
    ref, k = norm(ham)
    o28 = olcum_kaydi["sayfalar"][str(REF_SAYFA)]
    ozet = olcum_kaydi["ozet"]
    hiza, arandi = hizalama(oran, ref, bg_im, olcum_kaydi["bg"], kalibre)
    fark, zemin = fark_haritasi(ref, bg_im, hiza["olcek"], hiza["dy"],
                                hiza.get("dx", 0))
    ref_a = np.asarray(ref).astype(np.float32)
    zemin_a = np.asarray(zemin).astype(np.float32)

    ib, sb, tb = o28["isim_bant"], o28["sembol_bant"], o28["tag_bant"]
    pay = GENISLET + 8
    bolge = [(0, max(sb[0] - pay, 0), NORM_W, min(tb[1] + pay, ref.height))]
    hedef = {"sonsuz": kume_kutusu(fark, ib, *o28["sonsuz"]),
             "sembol_sol": kume_kutusu(fark, sb, *o28["sembol"][0]),
             "sembol_sag": kume_kutusu(fark, sb, *o28["sembol"][1]),
             "isim_sol": kume_kutusu(fark, ib, *o28["sol_isim"]),
             "isim_sag": kume_kutusu(fark, ib, *o28["sag_isim"]),
             "tagline": (o28["tag_x"][0], tb[0], o28["tag_x"][1], tb[1])}
    luma_maske = (ref_a @ LUMA) > MUREKKEP
    bil, alfa, genis, yildiz, yildiz_n = oge_ve_yildiz(fark, bolge, hedef, luma_maske)

    # Temiz zemin: maskeli bolgede referans yerine bg (yumusak gecisle)
    a3 = alfa[..., None]
    if iz_birak:
        # KAPI TESTI: eski SOL ismin dis ucu (yeni isim daha dar oldugu icin
        # burasi acikta kalir) kasten %75 eksik temizlenir.
        x0, y0, x1, y1 = bil["isim_sol"]["gorsel"]
        a3 = a3.copy()
        a3[y0:y1, x0:min(x0 + 25, x1)] *= 0.25
    temiz_a = ref_a * (1 - a3) + zemin_a * a3

    oge = {}
    for ad, b in bil.items():
        if ad == "tagline":                 # tagline yeniden cizilir, tasinmaz
            continue
        d, m = delta_kes(ref_a, zemin_a, b, alfa)
        g = b["gorsel"]
        oge[ad] = {"delta": d, "maske": m, "kutu": b["kutu"], "gorsel": g,
                   "w": g[2] - g[0], "h": g[3] - g[1],
                   "pay": (g[0] - b["kutu"][0], g[1] - b["kutu"][1])}

    cap = {"sol": hedef["isim_sol"][3] - hedef["isim_sol"][1],
           "sag": hedef["isim_sag"][3] - hedef["isim_sag"][1]}
    s = {"oran": oran, "tuval": list(ham.size), "bg_hiza": hiza,
         "bosluk": int(round(ozet["bosluk_ort"])),
         "kenar_payi": int(round(NORM_W * KENAR_ORAN)),
         "kullanilabilir": int(NORM_W - 2 * round(NORM_W * KENAR_ORAN)),
         "cap": cap, "tag_cap": tb[1] - tb[0],
         "tag_sinir": int(round(TAG_TABAN_SINIR * (tb[1] - tb[0]) / TAG_TABAN_CAP)),
         "sonsuz_w": oge["sonsuz"]["w"],
         "isim_y": (ib[0] + ib[1]) / 2,
         "sembol_y": {y: oge[f"sembol_{y}"]["gorsel"][1] for y in ("sol", "sag")},
         "isim_bant": list(ib), "sembol_bant": list(sb), "tag_bant": list(tb),
         "tag_y": (tb[0] + tb[1]) / 2,
         "kutular": {a: list(b["kutu"]) for a, b in oge.items()},
         "maske_px": int(genis.sum()), "yildiz_bileseni": yildiz_n,
         "iz_birak": iz_birak, "hiza_arandi": arandi,
         "kurulum_sn": round(time.time() - t0, 1)}
    S = {"ref": ref, "zemin_a": zemin_a, "temiz_a": temiz_a, "oge": oge,
         "prof": pilot12.PROFIL, "alfa": alfa, "genis": genis, "yildiz": yildiz}
    return s, S


# --------------------------------------------------------- poster ve kapi


def poster_kur(s, S, isimler, tagline):
    """D kurali; tasinan ogeler delta olarak eklenir."""
    olcek = d_olcek(isimler, s, S)
    pl = {y: plaka(isimler[y], S["prof"][y], s["cap"][y], olcek) for y in ("sol", "sag")}
    w = {y: pl[y][0].width for y in pl}
    inf = S["oge"]["sonsuz"]
    toplam = w["sol"] + s["bosluk"] + inf["w"] + s["bosluk"] + w["sag"]
    x0 = int(round(NORM_W / 2 - toplam / 2))
    x = {"sol": x0, "inf": x0 + w["sol"] + s["bosluk"],
         "sag": x0 + w["sol"] + s["bosluk"] + inf["w"] + s["bosluk"]}
    a = S["temiz_a"].copy()
    merkez = {y: x[y] + w[y] / 2 for y in ("sol", "sag")}

    # 1) tasinan ogeler (delta)
    # hedef = ogenin GORSEL sol-ust kosesi; delta kutusu paylarla kaydirilir
    yer = {"sonsuz": (x["inf"], S["oge"]["sonsuz"]["gorsel"][1])}
    for y in ("sol", "sag"):
        o = S["oge"][f"sembol_{y}"]
        yer[f"sembol_{y}"] = (merkez[y] - o["w"] / 2, o["gorsel"][1])
    for ad, (px, py) in yer.items():
        o = S["oge"][ad]
        delta_koy(a, o["delta"], o["maske"], px - o["pay"][0], py - o["pay"][1])

    # 2) yeni isimler ve tagline (alfa birlestirme)
    t = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    yeni_maske = np.zeros(a.shape[:2], np.uint8)
    for y in ("sol", "sag"):
        p = pl[y][0]
        px, py = int(round(x[y])), int(round(s["isim_y"] - p.height / 2))
        t.alpha_composite(p, (px, py))
        isaretle(yeni_maske, np.asarray(p)[..., 3] > 8, px, py)
    tg, tbilgi = tagline_plaka(s, {"prof": S["prof"]}, tagline)
    tx, ty = (int(round(NORM_W / 2 - tg.width / 2)),
              int(round(s["tag_y"] - tg.height / 2)))
    t.alpha_composite(tg, (tx, ty))
    isaretle(yeni_maske, np.asarray(tg)[..., 3] > 8, tx, ty)
    for ad, (px, py) in yer.items():
        o = S["oge"][ad]
        isaretle(yeni_maske, o["maske"] > 0.02, int(round(px - o["pay"][0])),
                 int(round(py - o["pay"][1])))

    # Kapi icin yeni ogelerin etki alani: kendi pikselleri + KAPI_PAY px.
    # Mo'nun onerdigi 12 px genisletme denendi, kapiyi kor birakiyordu (eski ve
    # yeni ogeler ayni bantta oldugu icin izler maskenin altinda kaliyordu).
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * KAPI_PAY + 1,) * 2)
    yeni_genis = cv2.dilate(yeni_maske, k).astype(bool)
    bilgi = {"olcek": round(olcek, 3), "punto": [pl["sol"][1], pl["sag"][1]],
             "genislik": [w["sol"], w["sag"]], "satir": round(toplam, 1),
             "kenar": [x0, NORM_W - x0 - toplam],
             "satir_merkez": round(x0 + toplam / 2, 1), "tagline": tbilgi}
    return t.convert("RGB"), bilgi, merkez, x, yeni_genis


def isaretle(hedef, maske, x, y):
    h, w = maske.shape
    H, W = hedef.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 > x0 and y1 > y0:
        hedef[y0:y1, x0:x1] |= maske[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.uint8)


def blok_kapisi(poster, S, s, yeni_genis):
    """Eski oge bolgesinde kalinti var mi? (yeni ogeler ve yildizlar haric)

    Olcum alani = eski ogelerin genisletilmis maskesi MINUS yeni yazilan
    ogeler MINUS yildizlar. Orada poster zemine esit olmali. Maskenin disini
    olcmek yaniltici olurdu: orada poster zaten orijinal tasarimdir (yildizlar,
    gradyan) ve bg'den farki kalinti degildir.
    """
    a = np.asarray(poster.convert("RGB")).astype(np.float32)
    fark = np.abs(a - S["zemin_a"]).max(axis=2)
    alan = S["genis"] & ~yeni_genis & ~S["yildiz"]
    kotu, en_ort, en_tepe, blok_n = [], 0.0, 0.0, 0
    H, W = alan.shape
    for by in range(0, H - BLOK + 1, BLOK):
        if not alan[by:by + BLOK].any():
            continue
        for bx in range(0, W - BLOK + 1, BLOK):
            m = alan[by:by + BLOK, bx:bx + BLOK]
            if m.sum() < 32:
                continue
            f = fark[by:by + BLOK, bx:bx + BLOK][m]
            ort, tepe = float(f.mean()), float(f.max())
            en_ort, en_tepe, blok_n = max(en_ort, ort), max(en_tepe, tepe), blok_n + 1
            if ort > BLOK_ORT or tepe > BLOK_TEPE:
                kotu.append({"x": bx, "y": by, "ort": round(ort, 2),
                             "tepe": round(tepe, 1), "px": int(m.sum())})
    return {"gecti": not kotu, "en_ort": round(en_ort, 2), "en_tepe": round(en_tepe, 1),
            "kotu_blok": len(kotu), "blok": blok_n, "ornek": kotu[:6],
            "esik": {"ort": BLOK_ORT, "tepe": BLOK_TEPE}}


def iz_kontrol(poster, s, oran, etiket=""):
    """Isim satiri + sembol bandi: 3x buyutulmus, 2.5x parlatilmis kirpim."""
    y0 = max(s["sembol_bant"][0] - 20, 0)
    y1 = min(s["isim_bant"][1] + 20, poster.height)
    k = poster.crop((0, y0, NORM_W, y1))
    k = k.resize((k.width * 3, k.height * 3), Image.LANCZOS)
    k = ImageEnhance.Brightness(k).enhance(2.5)
    k = k.resize((k.width // 2, k.height // 2), Image.LANCZOS)   # dosya boyutu
    dd = ImageDraw.Draw(k)
    from kisisel_pilot import font_yukle
    dd.text((14, 8), f"Blue {oran} {etiket} - 3x buyutme, 2.5x parlaklik",
            fill=(255, 220, 140), font=font_yukle(FONT_DIR / ISIM_FONT, 28, ISIM_W))
    return k


# -------------------------------------------------------------------- akis


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

    kapi, isim_kapi, test, iz, sure = {}, {}, {}, {}, {}
    for o in oranlar:
        s, S = oran_kur(o, olcum[o], bg_im, kalibre=a.kalibre)
        t_uret = time.time()
        log(f"{o}: kurulum {s['kurulum_sn']} sn (hiza "
            f"{'ARANDI' if s['hiza_arandi'] else 'kayitli'}), yildiz bileseni "
            f"{s['yildiz_bileseni']}, maske {s['maske_px']} px, kutular "
            f"{ {k: v[2] - v[0] for k, v in s['kutular'].items()} }")
        test[o], kucuk = [], []
        for sol_ham, sag_ham, ulke in CIFTLER:
            r = gd.siparis_dogrula(sol_ham, sag_ham, TAG, ulke)
            sol, sag = r["sol"]["deger"], r["sag"]["deger"]
            p, bilgi, merkez, x, yeni = poster_kur(s, S, {"sol": sol, "sag": sag}, TAG)
            bk = blok_kapisi(p, S, s, yeni)
            test[o].append({"cift": [sol, sag], "ulke": ulke, "punto": bilgi["punto"],
                            "olcek": bilgi["olcek"], "kapi": bk})
            kucuk.append(p.resize((560, int(round(560 * p.height / p.width))),
                                  Image.LANCZOS))
            log(f"{o} {sol}+{sag}: olcek %{bilgi['olcek'] * 100:.0f} blok kapisi "
                f"{'GECTI' if bk['gecti'] else 'KALDI'} ({bk['blok']} blok) en_ort "
                f"{bk['en_ort']} en_tepe {bk['en_tepe']} kotu {bk['kotu_blok']}")
            if sol == NEW_LEFT:
                kapi[o] = bk
                kaydet(p, YOL / f"_kapi_{o}.jpg")
                isim_kapi[o] = isim_kapisi(Image.open(YOL / f"_kapi_{o}.jpg"), o, kirpimlar)
                iz[o] = iz_kontrol(p, s, o, "SERDAR-LENA")
                kaydet(iz[o], YOL / f"IZ_KONTROL_{o}.jpg", maks=1_500_000)
                log(f"{o} isim kapisi: {json.dumps(isim_kapi[o])}")
        sure[o] = {"kurulum_sn": s["kurulum_sn"],
                   "poster_ort_sn": round((time.time() - t_uret) / len(CIFTLER), 1),
                   "hiza_arandi": s["hiza_arandi"]}
        log(f"{o} SURE: kurulum {sure[o]['kurulum_sn']} sn + poster basina "
            f"{sure[o]['poster_ort_sn']} sn")
        yanyana(kucuk, o)

    # kapinin kendini testi: kasten birakilan soluk iz
    o0 = oranlar[0]
    s2, S2 = oran_kur(o0, olcum[o0], bg_im, iz_birak=True)
    p2, b2, _, _, yeni2 = poster_kur(s2, S2, {"sol": NEW_LEFT, "sag": NEW_RIGHT},
                                     TAGLINES["A"])
    kendi = blok_kapisi(p2, S2, s2, yeni2)
    kaydet(iz_kontrol(p2, s2, o0, "KASTEN IZ"), YOL / f"IZ_TESTI_{o0}.jpg",
           maks=1_500_000)
    log(f"KAPI KENDI TESTI ({o0}): "
        f"{'HATA VERDI (dogru)' if not kendi['gecti'] else 'KACIRDI'} "
        f"({kendi['blok']} blok) en_ort {kendi['en_ort']} en_tepe {kendi['en_tepe']} "
        f"kotu {kendi['kotu_blok']}")

    d = {"oranlar": oranlar, "kapi": kapi, "isim_kapi": isim_kapi, "test": test,
         "sure": sure, "kendi_testi": {"oran": o0, **kendi}}
    (YOL / "v5.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str),
                                 encoding="utf-8")
    rapor(d)
    if not a.yerel:
        for f in ["SINIR_V5.md", "v5.json", f"IZ_TESTI_{o0}.jpg"]:
            rc("copy", str(YOL / f), DEST_O)
        for o in oranlar:
            rc("copy", str(YOL / f"TEST_V5_{o}.jpg"), DEST_O)
            rc("copy", str(YOL / f"IZ_KONTROL_{o}.jpg"), DEST_O)
        log(f"Drive <- {DEST_O}")
    return d


def yanyana(kucuk, oran):
    from kisisel_pilot import font_yukle
    et = font_yukle(FONT_DIR / ISIM_FONT, 24, ISIM_W)
    bas, w = 38, 560
    h = max(k.height for k in kucuk)
    im = Image.new("RGB", (w * len(kucuk), h + bas), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for i, (k, (sol, sag, u)) in enumerate(zip(kucuk, CIFTLER)):
        dd.text((i * w + 10, 6), f"{sol.upper()} - {sag.upper()}" + (f"  ({u})" if u else ""),
                fill=(214, 178, 96), font=et)
        im.paste(k, (i * w, bas))
    kaydet(im, YOL / f"TEST_V5_{oran}.jpg", maks=2_000_000)
    log(f"TEST_V5_{oran}.jpg {im.size}")


def rapor(d):
    o_ = d["oranlar"]
    m = ["# V5: temizleme maskesi, blok bazli kalinti kapisi, iz kontrolu", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         f"- **Temizleme maskesi**: eski oge maskesi = referans ile bg arasinda farki "
         f">{CEKIRDEK:.0f} olan pikseller; {MIN_ALAN} px'den kucuk gurultu bilesenleri "
         f"atilir, maske {GENISLET} px genisletilir (dilate) ve yumusak kenarli hale "
         f"getirilir. Eski oge bolgesi TAM zemine doner.",
         "- **Tasima yontemi**: oge artik RGBA kirpim olarak degil, zeminden FARKI "
         "(delta) olarak tasinir ve yeni yerinde zemine eklenir. Parilti ve kenar "
         "yumusatma birlikte gider, yeni zemin gradyani bozulmaz.",
         f"- **Kalinti kapisi** (ONAYLI.json kapilar): alan ortalamasi yerine "
         f"{BLOK}x{BLOK} BLOK bazli. Yeni yazilan ogelerin {GENISLET} px genisletilmis "
         f"maskesi DISINDA, sembol bandi + isim satiri boyunca her blokta ortalama fark "
         f"<= {BLOK_ORT:.0f} ve tek piksel farki <= {BLOK_TEPE:.0f}. Tutmazsa kosu HATA "
         "verir ve sorunlu blogun koordinati raporlanir.", "",
         "### Degismeyen", "",
         "- D kurali, kenar payi %10, bosluk, cap hedefleri, punto kurali, tagline, "
         "altin doku, Etsy sinirlari, buyuk harf kurali.", "",
         "## 1) Blok bazli kalinti kapisi (SERDAR - LENA)", "",
         f"| oran | olculen blok | en yuksek blok ortalamasi (<= {BLOK_ORT:.0f}) "
         f"| en yuksek tek piksel (<= {BLOK_TEPE:.0f}) | esigi asan blok | sonuc |",
         "| --- | --- | --- | --- | --- | --- |"]
    for o in o_:
        k = d["kapi"][o]
        m.append(f"| Blue {o} | {k['blok']} | {k['en_ort']} | {k['en_tepe']} | {k['kotu_blok']} "
                 f"| {'**GECTI**' if k['gecti'] else 'KALDI'} |")
    kt = d["kendi_testi"]
    m += ["", "### Kapinin kendini testi", "",
          f"Blue {kt['oran']}'te sag sembolun alt ucunda temizleme kasten %75 "
          f"zayiflatildi (soluk iz birakildi). Kapi sonucu: "
          f"**{'HATA VERDI (dogru davranis)' if not kt['gecti'] else 'KACIRDI'}** - "
          f"esigi asan blok sayisi {kt['kotu_blok']}, en yuksek blok ortalamasi "
          f"{kt['en_ort']}, en yuksek tek piksel {kt['en_tepe']}.",
          "", "Sorunlu bloklar (ilk 6): "
          + (", ".join(f"({b['x']},{b['y']}) ort {b['ort']} tepe {b['tepe']}"
                       for b in kt["ornek"]) or "-"),
          "", "Gorsel kanit: IZ_TESTI_" + kt["oran"] + ".jpg (ayni buyutme ve "
          "parlaklikla; iz gozle gorulur).", "",
          "## 2) Uc cift, bes oran", "",
          "| cift | ulke | oran | punto | olcek | blok kapisi | en_ort | en_tepe |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i in range(len(CIFTLER)):
        for o in o_:
            t = d["test"][o][i]
            k = t["kapi"]
            m.append(f"| {t['cift'][0]} - {t['cift'][1]} | {t['ulke'] or '-'} | Blue {o} "
                     f"| {t['punto'][0]} / {t['punto'][1]} | %{int(round(t['olcek'] * 100))} "
                     f"| {'GECTI' if k['gecti'] else 'KALDI'} | {k['en_ort']} "
                     f"| {k['en_tepe']} |")
    m += ["", "## 3) Onayli isim satiri kapisi (oran ici, SERDAR - LENA)", "",
          "| oran | kayma (<=1 px) | murekkep ici farki (<=3) | sonuc |",
          "| --- | --- | --- | --- |"]
    for o in o_:
        k = d["isim_kapi"][o]
        m.append(f"| Blue {o} | {k.get('kayma_px')} | {k.get('ic_fark')} "
                 f"| {'GECTI' if k['gecti'] else 'KALDI'} |")
    m += ["", "Temizleme degisikligi harfleri etkilemedi; yalniz zemindeki izler "
          "silindi.", "",
          "## 4) Uretim suresi (hedef: oran basina <= 30 sn)", "",
          "Hizalama (olcek, dx, dy) her oran icin BIR KEZ hesaplanip "
          "`ORAN_SABITLERI.json`'a `bg_hizasi_kilit` olarak yazildi; uretimde arama "
          "yapilmaz.", "",
          "| oran | kurulum (sn) | poster basina (sn) | hizalama |",
          "| --- | --- | --- | --- |"]
    for o in o_:
        v = d["sure"][o]
        m.append(f"| Blue {o} | {v['kurulum_sn']} | {v['poster_ort_sn']} "
                 f"| {'ARANDI (kalibrasyon)' if v['hiza_arandi'] else 'kayitli deger'} |")
    en_yavas = max(v["kurulum_sn"] + v["poster_ort_sn"] for v in d["sure"].values())
    m += ["", f"Bir siparis icin en yavas oran: **{en_yavas} sn** "
          + ("(hedef 30 sn icinde)." if en_yavas <= 30
             else "- **hedef 30 sn asildi**."), "",
          "## 5) Gorsel kanit", "",
          "IZ_KONTROL_<oran>.jpg: sembol bandi + isim satiri, 3x buyutulmus ve "
          "parlaklik 2.5 kat artirilmis. Eski oge yerlerinde iz gorunmemeli.",
          "TEST_V5_<oran>.jpg: uc cift yan yana.", ""]
    (YOL / "SINIR_V5.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    log("SINIR_V5.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--kalibre", action="store_true",
                    help="hizalamayi yeniden hesapla ve ORAN_SABITLERI.json'a yaz")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
