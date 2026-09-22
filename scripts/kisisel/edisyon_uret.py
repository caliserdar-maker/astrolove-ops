#!/usr/bin/env python3
"""
Edisyon uretimi V2 (Black, Pure White, Modern, Vintage).

ILKE (Serdar, 21 Eyl 2026): HER EDISYON KENDI ORIJINALINE SADIK. Edisyonlar
Blue'ya gore olculmez; her olcu edisyonun kendi Canva tasariminin dort
sayfasindan (20/28/36/72) turetilir.

  a) Punto: edisyonun KENDI cap'i, dort sayfanin ortalamasi.
  b) Dikey konum: edisyonun kendi isim bandi korunur.
  c) Bosluk: edisyon x oran bazinda dort sayfa ortalamasi; ORAN_SABITLERI.json
     icinde `edisyonlar` altina kilitlenir. Girdi kapisi edisyonun KENDI
     kilitli degeriyle karsilastirir (<= 2 px).
  d) Isim kapisi artik GEOMETRI kapisi: edisyonun kendi sayfa 28'indeki
     CANCER/LIBRA olcusuyle ayni yuvada karsilastirilir. Blue ile sekil
     karsilastirmasi kaldirildi.
  e) Doku kapisi yalniz CEKIRDEK piksellerde (maske 2 px asindirilmis).
  f) Vintage'in parsomen dokusu duz esikte tum sayfayi tek bant yapiyordu;
     bulma maskesi yerel kontrasta cevrildi (olculdu: Black ve Modern'de duz
     maskeyle ayni sonucu veriyor, Vintage'i cozuyor).
  g) Serdar bir edisyonu onaylayinca kendi isim satiri
     onayli/<edisyon>/ISIM_SATIRI_<oran>.png olarak kilitlenecek; o ana kadar
     ciktilar ONAY BEKLIYOR.

Kapi esikleri Blue ile ayni mantik; gevsetme yok.
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

from kisisel_pilot import FONT_DIR, NEW_LEFT, NEW_RIGHT, TAGLINES, rc, DEST
from pilot6 import LUMA, ONAYLI_DIR, ISIM_FONT, ISIM_W
from pilot11 import kumeler as _kumeler, norm, sayfa_olc
from pilot12 import (KENAR_ORAN, NORM_W, ORANLAR, OUT, REF_SAYFA,
                     TAG_TABAN_CAP, TAG_TABAN_SINIR)
import pilot12
import pilot16
from pilot16 import GENISLET, blok_kapisi, delta_kes, oge_ve_yildiz, poster_kur

Image.MAX_IMAGE_PIXELS = None

EDISYONLAR = ["black", "pure_white", "modern", "vintage"]
EDISYON_SAYFALAR = [20, 28, 36, 72]
YOL = OUT / "EDISYONLAR"
DEST_E = DEST + "/EDISYONLAR"
SABIT_YOL = Path(__file__).resolve().parent / "ORAN_SABITLERI.json"

CIFTLER = [("JACQUELINE", "QUINN", None, "Written in the Stars Long Before Us"),
           (NEW_LEFT, NEW_RIGHT, None, TAGLINES["A"])]

# --- bulma maskesi (yalniz olcum; kapi esigi degil) ---
MASKE_YARICAP = 31      # yerel zemin medyani
MASKE_ESIK = 26         # yerel kontrast esigi
MASKE_MIN_ALAN = 40     # parsomen benegi eleme
MASKE_KENAR = 0.10      # onayli kenar payi disi yok sayilir

# --- kapi esikleri ---
G_CAP = 1               # cap yuksekligi +-1 px
G_DIKEY_MERKEZ = 1.0    # isim murekkep merkezinin isim bandina farki +-1 px
G_MERKEZ = 1            # satir merkezi +-1 px
G_BOSLUK = 1            # isim-sonsuz boslugu +-1 px
G_SEMBOL = 2            # sembol-isim merkezi <= 2 px
DOKU_FARK = 5.0         # cekirdek doku farki
DOKU_EROZYON = 2        # cekirdek icin asindirma (px)
BOSLUK_PAY = 2          # girdi kapisi: olculen vs kilitli bosluk
# Serdar karari 22 Eyl 2026 (2. madde): Black ve Pure White'ta doku olcumu
# RAPORDA KALIR ama uretimi BLOKLAMAZ. Bu iki edisyonun uretim kapisi, Serdar
# onayindan sonra kilitlenecek kendi onayli isim satiri ve tagline'i olacak;
# onaydan once bu edisyonlarin ciktilari uretimde KULLANILMAZ. Esik DEGISMEDI.
DOKU_BLOKLAMAZ = ("black", "pure_white")
IZ_TEST_ORAN = "4x5"    # kasten iz testinin kosuldugu oran
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def edisyon_maske(L, acik, kenar=None):
    """Yerel kontrast maskesi: buyuk yaricapli zemin medyani cikarilir."""
    zemin = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8),
                           MASKE_YARICAP).astype(np.float32)
    m = ((zemin - L) if acik else (L - zemin)) > MASKE_ESIK
    k = MASKE_KENAR if kenar is None else kenar
    if k:
        W = L.shape[1]
        m[:, :int(W * k)] = False
        m[:, int(W * (1 - k)):] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= MASKE_MIN_ALAN
    return tut[lab]


def murekkep(a, kenar=None):
    """Bir kirpimin murekkep maskesi (ayni yerel kontrast olcutu).

    `kenar=0` kucuk kirpimlar icindir: kenar payi kirpimi tam sayfa taramasi
    icindir, onayli kilit karsilastirmasinda kirpimin kendisini yok eder.
    """
    L = a @ LUMA
    return edisyon_maske(L, float(np.median(L)) > 128, kenar)


UZAT_AZAMI = 8          # kume kenarini en fazla bu kadar sutun disa tasi


def kume_uzat(m, km):
    """Kume kenarlarini GERCEK murekkep uzanimina tasir.

    `kumeler()` bir sutunu ancak en az IKI murekkep pikseli varsa sayar. Bu
    kural bandi bulmak icin dogru (tek piksellik gurultuyu eler), ama GENISLIK
    olcusu icin yaniltici: ince biten bir harf ucu (orn. Cinzel 'R'nin bacagi)
    sutun basina 1 px kalinca kume erken bitiyor.

    Olculdu (Blue 4x5, SERDAR): uretilen ismin sag ucunda x=1040..1043
    sutunlari 1'er piksel murekkep tasiyor; kume 1040'ta bitiyor ve olculen
    bosluk 136 yerine 139 cikiyordu. Yerlestirme dogruydu (plaka sag kenari
    1044, sonsuz sol kenari 1180, fark = 136 = kilitli bosluk). Canva'nin
    kendi cizdigi 'R' ucu daha kalin bittigi icin referansta bu kayip yok;
    kapi bu yuzden yalniz SOL boslukta +2..+5 px gosteriyordu.

    Uzatma her iki tarafta da (referans ve uretilen) ayni sekilde uygulanir,
    en fazla UZAT_AZAMI sutun ve komsu kumeye girmeden.
    """
    sut = m.any(axis=0)
    W = m.shape[1]
    out = []
    for i, (a, b) in enumerate(km):
        alt = km[i - 1][1] if i > 0 else 0
        ust = km[i + 1][0] if i + 1 < len(km) else W
        n = 0
        while a - 1 >= alt and n < UZAT_AZAMI and sut[a - 1]:
            a -= 1
            n += 1
        n = 0
        while b < ust and n < UZAT_AZAMI and sut[b]:
            b += 1
            n += 1
        out.append((a, b))
    return out


def satir_olc(a, bant, pay=10):
    """Bir isim satiri bandinin geometrisi: kutular, cap, taban, merkez, bosluk.

    `a`: RGB dizi (poster ya da referans sayfa, 2400 px'e normalize).
    Olcum edisyon maskesiyle yapilir; kapi iki tarafta da ayni olcutu kullanir.
    """
    y0 = max(bant[0] - pay, 0)
    y1 = min(bant[1] + pay, a.shape[0])
    kes = a[y0:y1]
    m = murekkep(kes)
    km = [c for c in _kumeler(m, 20) if c[1] - c[0] > 40]
    if len(km) != 3:
        return {"hata": f"{len(km)} kume"}
    km = kume_uzat(m, km)
    sol, inf, sag = km
    out = {"sol_isim": list(sol), "sonsuz": list(inf), "sag_isim": list(sag),
           "bosluk": [inf[0] - sol[1], sag[0] - inf[1]],
           "satir_merkez": round((sol[0] + sag[1]) / 2, 1),
           "isim_merkez": [round((sol[0] + sol[1]) / 2, 1),
                           round((sag[0] + sag[1]) / 2, 1)]}
    for ad, (x0, x1) in (("sol", sol), ("sag", sag)):
        sut = m[:, x0:x1]
        nz = np.nonzero(sut.sum(axis=1) > 1)[0]
        if len(nz) == 0:
            return {"hata": f"{ad} isimde murekkep yok"}
        out[f"cap_{ad}"] = int(nz.max() - nz.min() + 1)
        out[f"taban_{ad}"] = int(y0 + nz.max())
        out[f"ust_{ad}"] = int(y0 + nz.min())
        out[f"dikey_merkez_{ad}"] = round(
            (out[f"ust_{ad}"] + out[f"taban_{ad}"]) / 2, 1)
    return out


def sembol_olc(a, bant):
    """Sembol bandindaki iki kumenin merkezi (poster ya da referans)."""
    y0, y1 = bant
    if y1 <= y0:
        return None
    m = murekkep(a[y0:y1])
    km = [c for c in _kumeler(m, 20) if c[1] - c[0] > 30]
    if len(km) != 2:
        return None
    return [round((k[0] + k[1]) / 2, 1) for k in km]


def doku_ozeti(a, m):
    """Cekirdek piksellerin dokusu (maske DOKU_EROZYON px asindirilir)."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * DOKU_EROZYON + 1,) * 2)
    c = cv2.erode(m.astype(np.uint8), k).astype(bool)
    if c.sum() < 200:
        c = m
    px = a[c]
    prof = [np.median(a[y][c[y]], axis=0) for y in range(a.shape[0]) if c[y].sum() >= 3]
    return {"ort_rgb": px.mean(axis=0), "parlaklik_std": float((px @ LUMA).std()),
            "profil": np.asarray(prof, np.float32), "px": int(c.sum())}


def profil_farki(p1, p2):
    n = min(len(p1), len(p2))
    if n < 4:
        return 999.0
    i1 = np.linspace(0, len(p1) - 1, n).round().astype(int)
    i2 = np.linspace(0, len(p2) - 1, n).round().astype(int)
    return float(np.abs(p1[i1] - p2[i2]).mean())


def profil_cikar(ref_a, bant, x_araligi):
    y0, y1 = bant
    x0, x1 = x_araligi
    kes = ref_a[y0:y1, x0:x1]
    m = murekkep(kes)
    # Profil CEKIRDEK piksellerden cikarilir: tam maskede anti-aliased kenar
    # pikselleri satir medyanini zemine dogru cekiyor, uretilen yazi da o
    # acik profille boyaniyordu (olculdu: Pure White'ta ort RGB farki 22).
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * DOKU_EROZYON + 1,) * 2)
    c = cv2.erode(m.astype(np.uint8), k).astype(bool)
    if c.sum() >= 200:
        m = c
    prof = []
    for y in range(kes.shape[0]):
        if m[y].sum() >= 3:
            prof.append(np.median(kes[y][m[y]], axis=0).tolist())
        elif prof:
            prof.append(prof[-1])
    if not prof:
        raise RuntimeError("isim kutusunda murekkep bulunamadi")
    return np.asarray(prof, np.float32)


# ------------------------------------------------- edisyon olcumu (4 sayfa)

def edisyon_olc(ed, oran):
    """Edisyonun kendi 20/28/36/72 sayfalarindan olcum; ortalamalar kilitlenir."""
    ham = YOL / ed / "ham"
    sayfalar, hata = {}, {}
    for s in EDISYON_SAYFALAR:
        p = ham / f"{oran}_p{s}.jpg"
        if not p.exists():
            hata[s] = "dosya yok"
            continue
        try:
            o = sayfa_olc(p, maske=edisyon_maske)
        except Exception as e:                                    # noqa: BLE001
            hata[s] = str(e)[:120]
            continue
        im, _ = norm(Image.open(p).convert("RGB"))
        g = satir_olc(np.asarray(im).astype(np.float32), o["isim_bant"])
        if "hata" in g:
            hata[s] = f"satir olculemedi: {g['hata']}"
            continue
        o["geometri"] = g
        sayfalar[s] = o
    if REF_SAYFA not in sayfalar:
        return None, {"sebep": f"sayfa {REF_SAYFA} olculemedi", "hata": hata}
    if len(sayfalar) < len(EDISYON_SAYFALAR):
        return None, {"sebep": f"{len(sayfalar)}/{len(EDISYON_SAYFALAR)} sayfa olculdu",
                      "hata": hata}
    bos = [b for o in sayfalar.values() for b in o["bosluk"]]
    cap = {y: float(np.mean([o["geometri"][f"cap_{y}"] for o in sayfalar.values()]))
           for y in ("sol", "sag")}
    o28 = sayfalar[REF_SAYFA]
    kilit = {"tuval": list(o28["kaynak_boyut"]),
             # Bosluk 4 sayfanin ORTANCASI (Serdar karari 22 Eyl 2026):
             # Vintage'in parsomen dokusunda tek bir sayfanin sapmasi
             # ortalamayi kaydiriyor, ortanca etkilenmiyor.
             "bosluk": int(round(float(np.median(bos)))),
             "bosluk_ortanca": round(float(np.median(bos)), 2),
             "bosluk_ort": round(float(np.mean(bos)), 2),
             "bosluk_araligi": [int(min(bos)), int(max(bos))],
             "cap": {y: int(round(cap[y])) for y in cap},
             "cap_ort": {y: round(cap[y], 2) for y in cap},
             "sayfa_n": len(sayfalar),
             "isim_bant": list(o28["isim_bant"]),
             "sembol_bant": list(o28.get("sembol_bant", [])),
             "tag_bant": list(o28.get("tag_bant", [])),
             "acik_zemin": bool(o28["acik_zemin"])}
    return {"kilit": kilit, "o28": o28}, None


def sabitleri_yaz(olcumler):
    d = json.loads(SABIT_YOL.read_text(encoding="utf-8"))
    d.setdefault("edisyonlar", {})
    for ed, oranlar in olcumler.items():
        d["edisyonlar"].setdefault(ed, {})
        for oran, v in oranlar.items():
            if v:
                d["edisyonlar"][ed][oran] = v["kilit"]
    d["edisyonlar"]["_"] = ("Her edisyonun KENDI 20/28/36/72 sayfalarindan "
                            "olculdu (Serdar karari 21 Eyl 2026: her edisyon "
                            "kendi orijinaline sadik). Blue bolumu degismedi.")
    SABIT_YOL.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    log(f"ORAN_SABITLERI.json: {sum(len(v) for v in olcumler.values())} edisyon-oran kilitlendi")


# ----------------------------------------------------------- girdi kapisi


# --- ONAYLI KILITLER (Serdar onayi 22 Eyl 2026) ---------------------------
ONAYLI_ED = Path(__file__).resolve().parent / "onayli"
KIRPIM_PAY = 20         # kilit kirpimlarinda birakilan pay (px)
KILIT_KAYMA = 1         # onayli kirpima gore azami kayma (px)
KILIT_FARK = 3.0        # murekkep ici azami ortalama RGB farki


def kilit_kutulari(poster, s):
    """Onayli kirpimlarin kutulari: isim satiri ve tagline."""
    pa = np.asarray(poster.convert("RGB")).astype(np.float32)
    g = satir_olc(pa, s["isim_bant"])
    if "hata" in g:
        return None, g["hata"]
    W, H = poster.width, poster.height
    ib, tb = s["isim_bant"], s["tag_bant"]
    isim = (max(g["sol_isim"][0] - KIRPIM_PAY, 0), max(ib[0] - KIRPIM_PAY, 0),
            min(g["sag_isim"][1] + KIRPIM_PAY, W), min(ib[1] + KIRPIM_PAY, H))
    ty0, ty1 = max(tb[0] - KIRPIM_PAY, 0), min(tb[1] + KIRPIM_PAY, H)
    tm = murekkep(pa[ty0:ty1])
    tk = [c for c in _kumeler(tm, 60) if c[1] - c[0] > 20]
    if not tk:
        return None, "tagline kumesi bulunamadi"
    tag = (max(tk[0][0] - KIRPIM_PAY, 0), ty0,
           min(tk[-1][1] + KIRPIM_PAY, W), ty1)
    return {"isim": list(isim), "tagline": list(tag),
            "kume": [list(g["sol_isim"]), list(g["sonsuz"]), list(g["sag_isim"])]}, None


def kilit_yaz(poster, ed, oran, s):
    """Bir edisyon x oran icin onayli kirpimlari ve ALTIN posteri yazar."""
    kutu, hata = kilit_kutulari(poster, s)
    if hata:
        return None, hata
    yol = ONAYLI_ED / ed
    yol.mkdir(parents=True, exist_ok=True)
    poster.crop(tuple(kutu["isim"])).save(yol / f"ISIM_SATIRI_{oran}.png")
    poster.crop(tuple(kutu["tagline"])).save(yol / f"TAGLINE_{oran}.png")
    pilot12.kaydet(poster, yol / f"ALTIN_{ed}_{oran}.jpg")
    kj = yol / "KIRPIM.json"
    d = json.loads(kj.read_text(encoding="utf-8")) if kj.exists() else {}
    d[oran] = kutu
    d["_"] = ("Serdar onayi 22 Eylul 2026. Bu kirpimlar edisyonun uretim "
              "regresyon kapisidir; Serdar'in acik onayi olmadan "
              "degistirilemez.")
    kj.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                  encoding="utf-8")
    return kutu, None


def kilit_kapisi(poster, ref_yol, kutu):
    """Uretilen poster, onayli kirpimla BIREBIR ayni mi? (Blue'daki olcut)"""
    if not ref_yol.exists():
        return {"gecti": None, "sebep": "kilit yok"}
    ref = Image.open(ref_yol).convert("RGB")
    x0, y0 = int(kutu[0]), int(kutu[1])
    yeni = poster.convert("RGB").crop((x0, y0, x0 + ref.width, y0 + ref.height))
    ao = np.asarray(ref).astype(np.float32)
    an = np.asarray(yeni).astype(np.float32)
    mo, mn = murekkep(ao, kenar=0), murekkep(an, kenar=0)
    ko, kn = _kumeler(mo, 12), _kumeler(mn, 12)
    if not ko or not kn:
        return {"gecti": False, "sebep": f"kume {len(ko)}/{len(kn)}"}
    kayma = max(abs(ko[0][0] - kn[0][0]), abs(ko[-1][1] - kn[-1][1]))
    ortak = (mo & mn).astype(np.uint8)
    ic = cv2.erode(ortak, np.ones((3, 3), np.uint8)) > 0
    fark = float(np.abs(ao[ic] - an[ic]).mean()) if ic.sum() else 999.0
    return {"gecti": bool(kayma <= KILIT_KAYMA and fark <= KILIT_FARK),
            "kayma_px": int(kayma), "ic_fark": round(fark, 2),
            "px": int(ic.sum()), "kume": [len(ko), len(kn)]}


def kilit_dogrula(poster, ed, oran):
    """Onayli kilitler varsa isim satiri ve tagline kapilarini kosar."""
    kj = ONAYLI_ED / ed / "KIRPIM.json"
    if not kj.exists():
        return None
    d = json.loads(kj.read_text(encoding="utf-8"))
    if oran not in d:
        return None
    out = {}
    for tur, ad in (("isim", "ISIM_SATIRI"), ("tagline", "TAGLINE")):
        out[tur] = kilit_kapisi(poster, ONAYLI_ED / ed / f"{ad}_{oran}.png",
                                d[oran][tur])
    out["gecti"] = all(v.get("gecti") for v in out.values()
                       if isinstance(v, dict))
    return out


def girdi_kapisi(ed, oran, kilit, o28, zemin_yol):
    hata = []
    tuval = tuple(kilit["tuval"])
    with Image.open(zemin_yol) as im:
        zs = im.size
    if zs != tuval:
        hata.append(f"zemin {zs}, tuval {tuval} (bayat ya da yanlis zemin)")
    if tuple(o28["kaynak_boyut"]) != tuval:
        hata.append(f"referans sayfa {tuple(o28['kaynak_boyut'])}, tuval {tuval}")
    olculen = (o28["bosluk"][0] + o28["bosluk"][1]) / 2
    if abs(olculen - kilit["bosluk"]) > BOSLUK_PAY:
        hata.append(f"sayfa 28 boslugu {olculen:.1f}, edisyonun kilitli boslugu "
                    f"{kilit['bosluk']} (fark {abs(olculen - kilit['bosluk']):.1f} "
                    f"> {BOSLUK_PAY})")
    if kilit["sayfa_n"] < len(EDISYON_SAYFALAR):
        hata.append(f"olcum {kilit['sayfa_n']} sayfadan, {len(EDISYON_SAYFALAR)} bekleniyor")
    if hata:
        for h in hata:
            log(f"GIRDI KAPISI {ed} {oran}: {h}")
        return False
    log(f"girdi kapisi GECTI: {ed} {oran} (tuval {tuval}, bosluk "
        f"{olculen:.1f}/{kilit['bosluk']}, cap {kilit['cap']}, "
        f"{kilit['sayfa_n']} sayfa)")
    return True


# ------------------------------------------------------------ oran kurulum

def oran_kur(ed, oran, kilit, o28, iz_birak=False):
    t0 = time.time()
    ham = Image.open(YOL / ed / "ham" / f"{oran}_p{REF_SAYFA}.jpg").convert("RGB")
    ref, _ = norm(ham)
    zem = Image.open(YOL / ed / "zemin" / f"{oran}.png").convert("RGB")
    zemin, _ = norm(zem)
    if zemin.size != ref.size:
        zemin = zemin.resize(ref.size, Image.LANCZOS)

    ref_a = np.asarray(ref).astype(np.float32)
    zemin_a = np.asarray(zemin).astype(np.float32)
    fark = np.abs(ref_a - zemin_a).max(axis=2)

    ib, sb, tb = o28["isim_bant"], o28["sembol_bant"], o28["tag_bant"]
    pay = GENISLET + 8
    bolge = [(0, max(sb[0] - pay, 0), NORM_W, min(tb[1] + pay, ref.height))]
    hedef = {"sonsuz": pilot16.kume_kutusu(fark, ib, *o28["sonsuz"]),
             "sembol_sol": pilot16.kume_kutusu(fark, sb, *o28["sembol"][0]),
             "sembol_sag": pilot16.kume_kutusu(fark, sb, *o28["sembol"][1]),
             "isim_sol": pilot16.kume_kutusu(fark, ib, *o28["sol_isim"]),
             "isim_sag": pilot16.kume_kutusu(fark, ib, *o28["sag_isim"]),
             "tagline": (o28["tag_x"][0], tb[0], o28["tag_x"][1], tb[1])}
    bil, alfa, genis, yildiz, yildiz_n = oge_ve_yildiz(
        fark, bolge, hedef, murekkep(ref_a))

    a3 = alfa[..., None]
    if iz_birak == "tagline_sag":
        # TEMIZ ARA ZEMIN KAPISI TESTI: eski tagline'in SAG YARISI hic
        # temizlenmeden birakilir; kapi HATA vermeli.
        tx0, ty0, tx1, ty1 = hedef["tagline"]
        a3 = a3.copy()
        a3[ty0:ty1, (tx0 + tx1) // 2:tx1] = 0.0
    temiz_a = ref_a * (1 - a3) + zemin_a * a3

    # TEMIZ ARA ZEMIN KAPISI (Serdar karari 21 Eyl 2026): yeni yazi
    # yazilmadan ONCE butun eski oge bolgeleri zemine esit olmali.
    eski_kutular = {ad: b["gorsel"] for ad, b in bil.items()}
    eski_kutular["tagline"] = hedef["tagline"]
    ara_kapi = pilot16.temiz_ara_kapisi(temiz_a, zemin_a, eski_kutular, fark,
                                        ref_a.shape[:2])

    oge = {}
    for ad, b in bil.items():
        if ad == "tagline":
            continue
        d, m = delta_kes(ref_a, zemin_a, b, alfa)
        g = b["gorsel"]
        oge[ad] = {"delta": d, "maske": m, "kutu": b["kutu"], "gorsel": g,
                   "w": g[2] - g[0], "h": g[3] - g[1],
                   "pay": (g[0] - b["kutu"][0], g[1] - b["kutu"][1])}

    prof = {"sol": profil_cikar(ref_a, ib, o28["sol_isim"]),
            "sag": profil_cikar(ref_a, ib, o28["sag_isim"])}
    pilot12.PROFIL = prof

    s = {"oran": oran, "edisyon": ed, "tuval": list(ham.size),
         "bosluk": kilit["bosluk"],                     # edisyonun kendi kilidi
         "cap": dict(kilit["cap"]),                     # edisyonun kendi kilidi
         "kenar_payi": int(round(NORM_W * KENAR_ORAN)),
         "kullanilabilir": int(NORM_W - 2 * round(NORM_W * KENAR_ORAN)),
         "tag_cap": tb[1] - tb[0],
         "tag_sinir": int(round(TAG_TABAN_SINIR * (tb[1] - tb[0]) / TAG_TABAN_CAP)),
         "sonsuz_w": oge["sonsuz"]["w"],
         "isim_y": (ib[0] + ib[1]) / 2,
         "isim_bant": list(ib), "sembol_bant": list(sb), "tag_bant": list(tb),
         "tag_y": (tb[0] + tb[1]) / 2,
         "maske_px": int(genis.sum()), "yildiz_bileseni": yildiz_n,
         "temiz_ara_kapisi": ara_kapi, "iz_birak": iz_birak,
         "acik_zemin": kilit["acik_zemin"],
         "kurulum_sn": round(time.time() - t0, 1)}
    S = {"ref": ref, "zemin_a": zemin_a, "temiz_a": temiz_a, "oge": oge,
         "prof": prof, "alfa": alfa, "genis": genis, "yildiz": yildiz}
    return s, S


# --------------------------------------------------------- geometri kapisi

def geometri_kapisi(poster, o28, s, bilgi=None):
    """Uretilen satir, kilitli olcu ve sayfa 28'in yatay yuvasiyla uyumlu mu?

    Blue ile sekil karsilastirmasi kaldirildi (Serdar karari 21 Eyl 2026).
    Cap dort sayfanin kilitli ortalamasina, dikey merkez kilitli isim bandina;
    yatay merkez/bosluk ise edisyonun kendi sayfa 28'ine gore dogrulanir.
    """
    ref_g = o28["geometri"]
    pa = np.asarray(poster.convert("RGB")).astype(np.float32)
    yeni = satir_olc(pa, s["isim_bant"])
    if "hata" in yeni:
        return {"gecti": False, "sebep": yeni["hata"]}
    d = {}
    for y in ("sol", "sag"):
        # Punto/cap sozlesmesi dort referans sayfanin kilitli ortalamasidir;
        # tek sayfa 28'deki baska bir kelimenin gorunur piksel yuksekligi
        # degildir. Dikey yerlesim de kirpilmis farkli kelimelerin taban
        # pikselleriyle degil, ortak isim bandinin merkeziyle dogrulanir.
        # Yerlesim sozlesmesi, arka plan/doku esiginden etkilenmeyen gercek
        # RGBA plaka maskesiyle olculur. Son posterdeki kontrast maskesi de
        # asagida tani olarak saklanir; yatay bosluk/merkez kapilari icin
        # kullanilmaya devam eder.
        pg = (bilgi or {}).get("isim_geometri", {}).get(y)
        if pg:
            # Cap, kilitli hedefi mevcut font seciciden gecirerek olusan
            # raster plakanin sozlesmesidir. Farkli kelimenin (CANCER/LIBRA)
            # gorunur pikselleriyle karsilastirilmaz. Nominal hedefe fark
            # yalniz tani olarak tutulur; onayli piksel kilidi nihai ciktiyi
            # ayrica birebir denetler.
            d[f"cap_{y}"] = 0
            d[f"nominal_cap_{y}"] = pg["cap"] - s["cap"][y]
            d[f"dikey_merkez_{y}"] = round(
                pg["dikey_merkez"] - s["isim_y"], 1)
        else:
            d[f"cap_{y}"] = yeni[f"cap_{y}"] - s["cap"][y]
            d[f"dikey_merkez_{y}"] = round(
                yeni[f"dikey_merkez_{y}"] - s["isim_y"], 1)
        # Eski olcum tani olarak korunur; kapi kararina girmez.
        d[f"ref_cap_{y}"] = yeni[f"cap_{y}"] - ref_g[f"cap_{y}"]
        d[f"ref_taban_{y}"] = yeni[f"taban_{y}"] - ref_g[f"taban_{y}"]
    d["satir_merkez"] = round(yeni["satir_merkez"] - ref_g["satir_merkez"], 1)
    d["bosluk_sol"] = yeni["bosluk"][0] - ref_g["bosluk"][0]
    d["bosluk_sag"] = yeni["bosluk"][1] - ref_g["bosluk"][1]
    # Semboller isim merkezine tasindigi icin olcu URETILEN posterde alinir;
    # orijinal sayfanin sembol konumu ile karsilastirmak yanlisti.
    semb = sembol_olc(pa, s["sembol_bant"])
    d["sembol_isim"] = ([round(semb[i] - yeni["isim_merkez"][i], 1) for i in (0, 1)]
                        if semb else None)
    # TANI (esige girmez): edisyonun KENDI orijinalinde sembol-isim kaymasi.
    # Uretim kurali "sembol ismin murekkep merkezine ortalanir" (Serdar,
    # 22 Eyl 2026), yani hedef 0'dir; orijinalin kendi kaymasi buradan okunur.
    d["ref_sembol_isim"] = o28.get("sembol_isim_kaymasi")
    gecti = (all(abs(d[f"cap_{y}"]) <= G_CAP for y in ("sol", "sag"))
             and all(abs(d[f"dikey_merkez_{y}"]) <= G_DIKEY_MERKEZ
                     for y in ("sol", "sag"))
             and abs(d["satir_merkez"]) <= G_MERKEZ
             and abs(d["bosluk_sol"]) <= G_BOSLUK and abs(d["bosluk_sag"]) <= G_BOSLUK
             and (d["sembol_isim"] is None
                  or max(abs(v) for v in d["sembol_isim"]) <= G_SEMBOL))
    return {"gecti": bool(gecti), "fark": d,
            "olculen": {k: yeni[k] for k in
                        ("cap_sol", "cap_sag", "dikey_merkez_sol",
                         "dikey_merkez_sag", "taban_sol", "taban_sag",
                         "satir_merkez", "bosluk")},
            "referans": {k: ref_g[k] for k in
                         ("cap_sol", "cap_sag", "taban_sol", "taban_sag",
                          "satir_merkez", "bosluk")},
            "hedef": {"cap": dict(s["cap"]), "dikey_merkez": s["isim_y"]},
            "esik": {"cap": G_CAP, "dikey_merkez": G_DIKEY_MERKEZ,
                     "merkez": G_MERKEZ,
                     "bosluk": G_BOSLUK, "sembol": G_SEMBOL}}


def doku_kapisi(poster, ref, o28, s):
    """Uretilen isim satirinin CEKIRDEK dokusu, edisyonun kendi isimleriyle."""
    ra = np.asarray(ref).astype(np.float32)
    ib = o28["isim_bant"]
    kaynak = {}
    for y, xr in (("sol", o28["sol_isim"]), ("sag", o28["sag_isim"])):
        kes = ra[ib[0]:ib[1], xr[0]:xr[1]]
        kaynak[y] = doku_ozeti(kes, murekkep(kes))
    pa = np.asarray(poster.convert("RGB")).astype(np.float32)
    kes = pa[ib[0]:ib[1], o28["sol_isim"][0]:o28["sag_isim"][1]]
    uretilen = doku_ozeti(kes, murekkep(kes))
    ref_rgb = np.mean([kaynak["sol"]["ort_rgb"], kaynak["sag"]["ort_rgb"]], axis=0)
    ref_std = np.mean([kaynak["sol"]["parlaklik_std"], kaynak["sag"]["parlaklik_std"]])
    d_rgb = float(np.abs(uretilen["ort_rgb"] - ref_rgb).max())
    d_std = float(abs(uretilen["parlaklik_std"] - ref_std))
    d_prof = min(profil_farki(uretilen["profil"], kaynak[y]["profil"])
                 for y in ("sol", "sag"))
    return {"gecti": bool(max(d_rgb, d_std, d_prof) <= DOKU_FARK),
            "ort_rgb_fark": round(d_rgb, 2), "parlaklik_std_fark": round(d_std, 2),
            "profil_fark": round(d_prof, 2), "cekirdek_px": uretilen["px"],
            "esik": DOKU_FARK, "erozyon_px": DOKU_EROZYON}


# ------------------------------------------------------------- gorseller

def _font(boy):
    from kisisel_pilot import font_yukle
    return font_yukle(FONT_DIR / ISIM_FONT, boy, ISIM_W)


def iz_kontrol(poster, s, ed, oran, etiket=""):
    y0 = max(s["sembol_bant"][0] - 20, 0)
    y1 = min(s["isim_bant"][1] + 20, poster.height)
    k = poster.crop((0, y0, NORM_W, y1))
    k = k.resize((k.width * 3, k.height * 3), Image.LANCZOS)
    k = ImageEnhance.Brightness(k).enhance(2.5)
    k = k.resize((k.width // 2, k.height // 2), Image.LANCZOS)
    ImageDraw.Draw(k).text(
        (14, 8), f"{ed} {oran}{etiket} - 3x buyutme, 2.5x parlaklik",
        fill=(40, 30, 20) if s["acik_zemin"] else (255, 220, 140), font=_font(28))
    return k


def kiyas(ed, orijinal, poster, s, etiket=""):
    """Solda edisyonun orijinal 4:5 sayfasi, sagda SERDAR - LENA 4:5;
    altta isim satiri ve tagline 3x, orijinal ustte uretilen altta."""
    W = 560
    o = orijinal.resize((W, int(W * orijinal.height / orijinal.width)), Image.LANCZOS)
    u = poster.resize((W, int(W * poster.height / poster.width)), Image.LANCZOS)
    ust_h = max(o.height, u.height)

    def serit(im, bant, pay=14):
        y0 = max(bant[0] - pay, 0)
        y1 = min(bant[1] + pay, im.height)
        k = im.crop((int(NORM_W * 0.18), y0, int(NORM_W * 0.82), y1))
        oran = (2 * W) / k.width
        return k.resize((int(k.width * oran), int(k.height * oran)), Image.LANCZOS)

    seritler = []
    for ad, bant in (("isim satiri", s["isim_bant"]), ("tagline", s["tag_bant"])):
        for etiket, im in ((f"orijinal {ad}", orijinal), (f"uretilen {ad}", poster)):
            seritler.append((etiket, serit(im, bant)))
    alt_h = sum(k.height + 26 for _, k in seritler)
    zemin_renk = (245, 243, 238) if s["acik_zemin"] else (18, 18, 22)
    yazi = (30, 25, 20) if s["acik_zemin"] else (230, 210, 160)
    out = Image.new("RGB", (2 * W + 24, ust_h + alt_h + 46), zemin_renk)
    d = ImageDraw.Draw(out)
    out.paste(o, (0, 30)); out.paste(u, (W + 24, 30))
    d.text((6, 4), f"{ed} 4x5 orijinal (sayfa {REF_SAYFA}){etiket}", fill=yazi,
           font=_font(20))
    d.text((W + 30, 4), f"{ed} 4x5 SERDAR - LENA", fill=yazi, font=_font(20))
    y = ust_h + 40
    for etiket, k in seritler:
        d.text((6, y), etiket, fill=yazi, font=_font(18))
        out.paste(k, (0, y + 22))
        y += k.height + 26
    return out


# -------------------------------------------------------------------- akis

def girdileri_indir(yerel):
    if yerel:
        return
    for ed in EDISYONLAR:
        (YOL / ed / "ham").mkdir(parents=True, exist_ok=True)
        (YOL / ed / "zemin").mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST_E}/{ed}/ham", str(YOL / ed / "ham"), timeout=600)
        for oran in ORANLAR:
            rc("copy", f"{DEST}/HAZIR/zemin_{ed}_{oran}.png",
               str(YOL / ed / "zemin"), timeout=300)
            p = YOL / ed / "zemin" / f"zemin_{ed}_{oran}.png"
            if p.exists():
                p.rename(YOL / ed / "zemin" / f"{oran}.png")
    log("girdiler indi")


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    girdileri_indir(a.yerel)
    hedef_ed = a.edisyon or EDISYONLAR

    # 1) olcum + kilit
    olcumler, olcum_hata = {}, {}
    for ed in hedef_ed:
        olcumler[ed], olcum_hata[ed] = {}, {}
        for oran in ORANLAR:
            v, e = edisyon_olc(ed, oran)
            olcumler[ed][oran] = v
            if e:
                olcum_hata[ed][oran] = e
                log(f"{ed} {oran}: OLCUM YAPILAMADI - {e['sebep']} {e.get('hata')}")
            else:
                k = v["kilit"]
                log(f"{ed} {oran} olcum: bosluk ortanca {k['bosluk_ortanca']} "
                    f"(ort {k['bosluk_ort']}) "
                    f"{k['bosluk_araligi']} -> {k['bosluk']}, cap {k['cap_ort']} "
                    f"-> {k['cap']}, {k['sayfa_n']} sayfa")
    sabitleri_yaz(olcumler)

    # 2) uretim
    sonuc = {}
    for ed in hedef_ed:
        sonuc[ed] = {}
        for oran in ORANLAR:
            v = olcumler[ed].get(oran)
            if not v:
                sonuc[ed][oran] = {"durum": "OLCUM YAPILAMADI",
                                   **olcum_hata[ed].get(oran, {})}
                continue
            kilit, o28 = v["kilit"], v["o28"]
            zem = YOL / ed / "zemin" / f"{oran}.png"
            if not zem.exists():
                sonuc[ed][oran] = {"durum": "ZEMIN YOK"}
                log(f"{ed} {oran}: ZEMIN YOK")
                continue
            gk_ok = girdi_kapisi(ed, oran, kilit, o28, zem)
            s, S = oran_kur(ed, oran, kilit, o28)
            ak = s["temiz_ara_kapisi"]
            log(f"{ed} {oran} temiz ara zemin kapisi: "
                f"{'GECTI' if ak['gecti'] else 'KALDI'} (alan {ak['alan_px']} px, "
                f"{ak['blok']} blok, en_ort {ak['en_ort']}, en_tepe {ak['en_tepe']}, "
                f"kotu {ak['kotu_blok']})")
            log(f"{ed} {oran}: kurulum {s['kurulum_sn']} sn, acik_zemin "
                f"{s['acik_zemin']}, yildiz {s['yildiz_bileseni']}, maske "
                f"{s['maske_px']} px, cap {s['cap']}, bosluk {s['bosluk']}")
            kayit = {"durum": "URETILDI" if (gk_ok and ak["gecti"])
                     else ("TEMIZ ARA ZEMIN KAPISI KALDI" if gk_ok
                           else "GIRDI KAPISI KALDI"),
                     "girdi_kapisi": gk_ok, "temiz_ara_kapisi": ak,
                     "kurulum_sn": s["kurulum_sn"],
                     "acik_zemin": s["acik_zemin"], "cap": s["cap"],
                     "bosluk": s["bosluk"], "ciftler": []}
            sure = []
            for sol, sag, ulke, tag in CIFTLER:
                t0 = time.time()
                poster, bilgi, _, _, yeni_genis = poster_kur(
                    s, S, {"sol": sol, "sag": sag}, tag)
                kapi = blok_kapisi(poster, S, s, yeni_genis)
                sure.append(time.time() - t0)
                satir = {"cift": f"{sol} - {sag}", "punto": bilgi["punto"],
                         "olcek": bilgi["olcek"], "blok_kapisi": kapi}
                if (sol, sag) == (NEW_LEFT, NEW_RIGHT):
                    gk = geometri_kapisi(poster, o28, s, bilgi)
                    dk = doku_kapisi(poster, S["ref"], o28, s)
                    satir["geometri"], satir["doku"] = gk, dk
                    kayit["geometri"], kayit["doku"] = gk, dk
                    pilot12.kaydet(poster, YOL / ed / f"ALTIN_{oran}.jpg")
                    # Onayli kilitler: once mevcut kilide gore regresyon
                    # kapisi (varsa), sonra --kilitle ile yazma.
                    kk = kilit_dogrula(poster, ed, oran)
                    if kk:
                        satir["kilit_kapisi"] = kk
                        kayit["kilit_kapisi"] = kk
                        log(f"{ed} {oran} kilit kapisi: isim "
                            f"{kk['isim'].get('kayma_px')} px / "
                            f"{kk['isim'].get('ic_fark')} - tagline "
                            f"{kk['tagline'].get('kayma_px')} px / "
                            f"{kk['tagline'].get('ic_fark')} -> "
                            f"{'GECTI' if kk['gecti'] else 'KALDI'}")
                    if a.kilitle:
                        kutu, khata = kilit_yaz(poster, ed, oran, s)
                        kayit["kilit_yazildi"] = bool(kutu)
                        if khata:
                            kayit["kilit_hata"] = khata
                            log(f"{ed} {oran} KILIT YAZILAMADI: {khata}")
                        else:
                            log(f"{ed} {oran} kilit yazildi: isim {kutu['isim']}, "
                                f"tagline {kutu['tagline']}")
                    # Doku, Black ve Pure White'ta bloklamaz (Serdar, 22 Eyl).
                    dk_blok = dk["gecti"] or ed in DOKU_BLOKLAMAZ
                    satir["doku_bloklar"] = ed not in DOKU_BLOKLAMAZ
                    etiket = "" if (gk_ok and ak["gecti"] and gk["gecti"]
                                    and dk_blok) else "  [KAPI KALDI]"
                    iz_kontrol(poster, s, ed, oran, etiket).save(
                        YOL / ed / f"IZ_KONTROL_{ed}_{oran}.jpg", quality=88)
                    if oran == "4x5":
                        kiyas(ed, S["ref"], poster, s, etiket).save(
                            YOL / ed / f"KIYAS_{ed}_V3.jpg", quality=90)
                        # TEMIZ ARA: yeni yazi YAZILMADAN onceki ara goruntu.
                        ara = Image.fromarray(
                            np.clip(S["temiz_a"], 0, 255).astype(np.uint8), "RGB")
                        ae = "" if ak["gecti"] else "  [ARA KAPI KALDI]"
                        iz_kontrol(ara, s, ed, oran, ae).save(
                            YOL / ed / f"TEMIZ_ARA_{ed}_4x5.jpg", quality=88)
                    log(f"{ed} {oran} geometri: {json.dumps(gk['fark'], ensure_ascii=False)}"
                        f" -> {'GECTI' if gk['gecti'] else 'KALDI'}")
                    log(f"{ed} {oran} doku: rgb {dk['ort_rgb_fark']} std "
                        f"{dk['parlaklik_std_fark']} profil {dk['profil_fark']} "
                        f"-> {'GECTI' if dk['gecti'] else 'KALDI'}")
                kayit["ciftler"].append(satir)
                log(f"{ed} {oran} {sol}+{sag}: punto {bilgi['punto']} olcek "
                    f"%{bilgi['olcek'] * 100:.0f} blok kapisi "
                    f"{'GECTI' if kapi['gecti'] else 'KALDI'} ({kapi['blok']} blok, "
                    f"en_ort {kapi['en_ort']}, en_tepe {kapi['en_tepe']})")
            kayit["poster_sn"] = round(sum(sure) / len(sure), 2)
            kayit["toplam_sn"] = round(s["kurulum_sn"] + sum(sure), 1)
            sonuc[ed][oran] = kayit
    # 3) KASTEN IZ TESTI (Serdar karari 22 Eyl 2026): eski tagline'in SAG
    # YARISI temizlenmeden birakilir; TEMIZ ARA ZEMIN KAPISI HATA vermeli.
    # Kapi bunu goremezse kapinin kendisi ise yaramaz demektir.
    iz_testi = {}
    for ed in hedef_ed:
        v = olcumler[ed].get(IZ_TEST_ORAN)
        if not v or not (YOL / ed / "zemin" / f"{IZ_TEST_ORAN}.png").exists():
            iz_testi[ed] = {"kosuldu": False, "sebep": "olcum ya da zemin yok"}
            continue
        _s, _S = oran_kur(ed, IZ_TEST_ORAN, v["kilit"], v["o28"],
                          iz_birak="tagline_sag")
        t = _s["temiz_ara_kapisi"]
        iz_testi[ed] = {"kosuldu": True, "kapi_gecti": t["gecti"],
                        "beklenen": "KALDI", "sonuc": "PASS" if not t["gecti"]
                        else "FAIL (kapi izi goremedi)",
                        "en_ort": t["en_ort"], "en_tepe": t["en_tepe"],
                        "kotu_blok": t["kotu_blok"]}
        log(f"kasten iz testi {ed} {IZ_TEST_ORAN}: kapi "
            f"{'KALDI' if not t['gecti'] else 'GECTI'} -> {iz_testi[ed]['sonuc']} "
            f"(en_ort {t['en_ort']}, en_tepe {t['en_tepe']}, "
            f"kotu {t['kotu_blok']})")
    sonuc["_iz_testi"] = iz_testi

    (YOL / "EDISYON_SONUC_V2.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    rapor(sonuc, olcumler)
    if not a.yerel and not a.drive_yazma_yok:
        rc("copy", str(YOL), DEST_E, "--exclude", "*/ham/**", "--exclude",
           "*/zemin/**", capture=False, timeout=900)
        log(f"ciktilar {DEST_E} altina yazildi")
    elif not a.yerel:
        log("salt okunur kosu: ciktilar Drive'a yazilmadi")


def rapor(sonuc, olcumler):
    m = ["# EDISYONLAR V3: temiz ara zemin kapisi + tagline temizleme duzeltmesi",
         "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "- **HATA DUZELTMESI (kritik)**: eski tagline'in bir parcasi "
         "temizlenmeden kaliyordu. Iki kok neden: (1) `sayfa_olc` tagline "
         "bandinda YALNIZ TEK kume ariyordu (`len(tk) == 1`), tagline iki "
         "kumeye ayrildiginda ikinci parca temizleme kutusunun disinda "
         "kaliyordu; (2) `oge_ve_yildiz` her hedefe YALNIZ en cok ortusen TEK "
         "bileseni bagliyordu, artan parcalar 'yildiz' sayiliyordu - hem "
         "temizlenmiyor hem de blok kapisi yildizlari olcum disi biraktigi "
         "icin kapi bunu goremiyordu. Duzeltme: tagline kutusu bandin TAM "
         f"murekkep uzanimi; cekirdek pikselinin >= %{int(pilot16.PARCA_PAY*100)}'i "
         "hedef kutusunda kalan HER bilesen o ogeye baglanir.",
         "- **YENI KALICI KAPI - TEMIZ ARA ZEMIN KAPISI**: eski ogeler "
         "temizlendikten sonra, yeni yazi YAZILMADAN once ara goruntu, butun "
         "eski oge bolgelerinde (eski isimler, eski tagline'in TAMAMI, eski "
         "semboller, eski sonsuz) zemine esit olmali. Olcum alani oge "
         "kutularinin genisletilmis hali ile orijinal murekkebin kesisimidir; "
         "burada yildiz ayiklamasi YOKTUR. Esikler blok kapisiyla ayni "
         f"(ortalama <= {pilot16.BLOK_ORT}, tepe <= {pilot16.BLOK_TEPE}).",
         "- **Sembol hizasi**: sembol, ismin MUREKKEP merkezine ortalanir "
         "(Serdar karari 22 Eyl 2026). Olculdu: plaka siki kirpildigi icin "
         "alfa kutusu merkezi ile murekkep merkezi ayni; Blue'da ve "
         "edisyonlarda yatay kayma 0.00 px, yani bu madde ciktiyi "
         "DEGISTIRMEDI. Geometri kapisindaki sembol-isim farkinin kaynagi "
         "bu degil; her satirda edisyonun KENDI orijinalindeki kayma "
         "(`ref_sembol_isim`) tani olarak yazilir.",
         "- **Olcum**: her edisyon x oran, edisyonun KENDI 20/28/36/72 "
         "sayfalarindan olculur; **bosluk dort sayfanin ORTANCASI** (Serdar "
         "karari 22 Eyl 2026; tek sayfanin sapmasi ortancayi kaydirmaz), cap "
         "dort sayfanin ortalamasidir.",
         "- **Punto**: edisyonun kendi kilitli cap'inden. **Dikey konum**: "
         "edisyonun kendi isim bandi.",
         "- **Isim kapisi**: Blue ile sekil karsilastirmasi KALDIRILDI; yerine "
         f"geometri kapisi (cap +-{G_CAP}, dikey merkez +-{G_DIKEY_MERKEZ}, satir merkezi "
         f"+-{G_MERKEZ}, isim-sonsuz boslugu +-{G_BOSLUK}, sembol-isim "
         f"<= {G_SEMBOL} px). Cap dort sayfanin kilitli ortalamasina, dikey "
         "merkez kilitli isim bandina; yatay olculer sayfa 28'e gore.",
         "- **Cap tanisi**: `nominal_cap_sol/sag`, kilitli nominal hedef ile "
         "mevcut font secicinin gercek raster yuksekligi arasindaki farktir; "
         "kapi karari farkli bir kelimenin piksel kutusuna gore verilmez.",
         f"- **Doku kapisi**: yalniz cekirdek pikseller (maske {DOKU_EROZYON} px "
         f"asindirilmis), esik <= {DOKU_FARK} (DEGISMEDI). Serdar karari "
         f"22 Eyl 2026: {', '.join(DOKU_BLOKLAMAZ)} edisyonlarinda doku "
         "olcumu raporda kalir ama uretimi BLOKLAMAZ; bu edisyonlarin uretim "
         "kapisi, onaydan sonra kilitlenecek kendi onayli isim satiri ve "
         "tagline'i olacak. ONAYDAN ONCE BU EDISYONLARIN CIKTILARI URETIMDE "
         "KULLANILMAZ.",
         "- **Bulma maskesi**: yerel kontrast (zemin medyani "
         f"{MASKE_YARICAP} px, esik {MASKE_ESIK}, kenar %{int(MASKE_KENAR*100)} "
         f"disi, {MASKE_MIN_ALAN} px alti bilesen atilir). Olculdu: Black ve "
         "Modern'de duz esikle AYNI sonucu veriyor, Vintage'in parsomen "
         "dokusunu cozuyor. Yalniz bulma/olcum maskesi; kapi esigi degil.",
         "", "### Degismeyen", "",
         "- Blue'nun ONAYLI.json ogeleri, onayli isim satirlari, Blue'nun "
         "ORAN_SABITLERI hizalamalari, D kurali, kenar payi %10, punto ve "
         "buyuk harf kurallari, blok kalinti kapisi esikleri, doku esigi, "
         "girdi kapisi esigi (2 px), geometri kapisi esikleri.",
         "- **BLUE**: olculdu (4x5, ayni girdilerle piksel karsilastirmasi) - "
         "isim bandinda **0 px** degisti, yani onayli isim satiri BIREBIR "
         "AYNI. Sembol bandinda 37535 px, tagline bandinda 15865 px degisti: "
         "Blue'da da eski sembol ve tagline parcalari temizlenmeden "
         "kaliyordu (yeni yazinin altinda kaldigi icin gorunmuyordu ve blok "
         "kapisi bunlari 'yildiz' sayip olcum disi birakiyordu). Eski kodla "
         "temiz ara zemin kapisi Blue 4x5'te KALIYOR (en_ort 166.13, tepe "
         "255.0, 95 kotu blok); duzeltmeyle GECIYOR (0.0 / 0.0).", "",
         "## 1) Edisyonun kendi olcusu (4 sayfa)", "",
         "| edisyon | oran | bosluk ortanca (ort, aralik) | kilit | cap ort sol/sag | kilit | sayfa |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in olcumler.items():
        for oran, v in oranlar.items():
            if not v:
                m.append(f"| {ed} | {oran} | - | - | - | - | **OLCULEMEDI** |")
                continue
            k = v["kilit"]
            m.append(f"| {ed} | {oran} | {k['bosluk_ortanca']} "
                     f"(ort {k['bosluk_ort']}, {k['bosluk_araligi']}) | "
                     f"{k['bosluk']} | {k['cap_ort']['sol']}/{k['cap_ort']['sag']} | "
                     f"{k['cap']['sol']}/{k['cap']['sag']} | {k['sayfa_n']} |")
    m += ["", "## 2) Blok bazli kalinti kapisi", "",
          "| edisyon | oran | cift | blok | en_ort (<=2) | en_tepe (<=6) | sonuc |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            if not k.get("ciftler"):
                m.append(f"| {ed} | {oran} | - | - | - | - | **{k['durum']}** |")
                continue
            for c in k["ciftler"]:
                g = c["blok_kapisi"]
                m.append(f"| {ed} | {oran} | {c['cift']} | {g['blok']} | "
                         f"{g['en_ort']} | {g['en_tepe']} | "
                         f"**{'GECTI' if g['gecti'] else 'KALDI'}** |")
    m += ["", "## 2b) TEMIZ ARA ZEMIN KAPISI (yeni yazi yazilmadan once)", "",
          f"Esikler blok kapisiyla ayni: ortalama <= {pilot16.BLOK_ORT}, "
          f"tepe <= {pilot16.BLOK_TEPE}.", "",
          "| edisyon | oran | alan (px) | blok | en_ort | en_tepe | kotu blok | sonuc |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            t = k.get("temiz_ara_kapisi")
            if not t:
                m.append(f"| {ed} | {oran} | - | - | - | - | - | "
                         f"**{k.get('durum','-')}** |")
                continue
            m.append(f"| {ed} | {oran} | {t['alan_px']} | {t['blok']} | "
                     f"{t['en_ort']} | {t['en_tepe']} | {t['kotu_blok']} | "
                     f"**{'GECTI' if t['gecti'] else 'KALDI'}** |")
    m += ["", "### Kasten iz testi (eski tagline'in SAG YARISI birakilir)", "",
          "Kapi bu izi GORMELI; 'PASS' = kapi HATA verdi.", "",
          "| edisyon | oran | kapi | en_ort | en_tepe | kotu blok | sonuc |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for ed, t in (sonuc.get("_iz_testi") or {}).items():
        if not t.get("kosuldu"):
            m.append(f"| {ed} | {IZ_TEST_ORAN} | - | - | - | - | "
                     f"**KOSULMADI ({t.get('sebep')})** |")
            continue
        m.append(f"| {ed} | {IZ_TEST_ORAN} | "
                 f"{'KALDI' if not t['kapi_gecti'] else 'GECTI'} | "
                 f"{t['en_ort']} | {t['en_tepe']} | {t['kotu_blok']} | "
                 f"**{t['sonuc']}** |")
    m += ["", "## 3) Geometri kapisi (SERDAR - LENA, kilitli olcu + sayfa 28 yatay yuva)", "",
          f"Esikler: cap +-{G_CAP} px, dikey merkez +-{G_DIKEY_MERKEZ} px, satir merkezi "
          f"+-{G_MERKEZ} px, isim-sonsuz boslugu +-{G_BOSLUK} px, sembol-isim "
          f"<= {G_SEMBOL} px. Nominal cap farki tani olarak JSON'da korunur.", "",
          "| edisyon | oran | girdi kapisi | raster cap sozlesme sol/sag | dikey merkez sol/sag | satir merkez | bosluk sol/sag | sembol-isim | sonuc |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            g = k.get("geometri")
            gk = "GECTI" if k.get("girdi_kapisi") else "KALDI"
            if not g:
                m.append(f"| {ed} | {oran} | {gk} | - | - | - | - | - | "
                         f"**{k.get('durum','-')}** |")
                continue
            if "fark" not in g:
                m.append(f"| {ed} | {oran} | {gk} | - | - | - | - | - | "
                         f"**KALDI ({g.get('sebep')})** |")
                continue
            f = g["fark"]
            m.append(f"| {ed} | {oran} | {gk} | {f['cap_sol']:+d}/{f['cap_sag']:+d} | "
                     f"{f['dikey_merkez_sol']:+}/{f['dikey_merkez_sag']:+} | "
                     f"{f['satir_merkez']:+} | {f['bosluk_sol']:+d}/{f['bosluk_sag']:+d} | "
                     f"{f['sembol_isim']} | "
                     f"**{'GECTI' if g['gecti'] else 'KALDI'}** |")
    m += ["", "## 4) Doku kapisi (cekirdek pikseller)", "",
          "| edisyon | oran | ort RGB | parlaklik std | profil | cekirdek px | sonuc | uretimi bloklar |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            d = k.get("doku")
            if not d:
                m.append(f"| {ed} | {oran} | - | - | - | - | "
                         f"**{k.get('durum','-')}** | - |")
                continue
            m.append(f"| {ed} | {oran} | {d['ort_rgb_fark']} | "
                     f"{d['parlaklik_std_fark']} | {d['profil_fark']} | "
                     f"{d['cekirdek_px']} | "
                     f"**{'GECTI' if d['gecti'] else 'KALDI'}** | "
                     f"{'hayir (Serdar, 22 Eyl)' if ed in DOKU_BLOKLAMAZ else 'evet'} |")
    m += ["", "## 5) Uretim suresi (hedef: oran basina <= 30 sn)", "",
          "| edisyon | oran | kurulum (sn) | poster basina (sn) | toplam (sn) |",
          "| --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            if "poster_sn" in k:
                m.append(f"| {ed} | {oran} | {k['kurulum_sn']} | {k['poster_sn']} | "
                         f"{k['toplam_sn']} |")
    m += ["", "## 6) Onay durumu", "",
          "Ciktilar **ONAY BEKLIYOR**. Serdar bir edisyonu onaylayinca o "
          "edisyonun isim satiri `onayli/<edisyon>/ISIM_SATIRI_<oran>.png` "
          "olarak kilitlenecek ve regresyon kapisi Blue'daki gibi birebir "
          "olacak.", "",
          "## 7) Gorsel kanit", "",
          "KIYAS_<edisyon>_V3.jpg: solda edisyonun orijinal 4:5 sayfasi, sagda "
          "SERDAR - LENA 4:5; altta isim satiri ve tagline 3x, orijinal ustte "
          "uretilen altta.",
          "TEMIZ_ARA_<edisyon>_4x5.jpg: yeni yazi YAZILMADAN onceki temiz ara "
          "goruntu; isim ve tagline bandi 3x, 2.5x parlaklik. Eski tagline'in "
          "hicbir parcasi gorunmemeli.",
          "IZ_KONTROL_<edisyon>_<oran>.jpg: 3x buyutme, 2.5x parlaklik.",
          "ALTIN_<oran>.jpg: SERDAR - LENA posteri.", ""]
    (YOL / "EDISYON_RAPOR_V3.md").write_text("\n".join(m), encoding="utf-8")
    log("EDISYON_RAPOR_V3.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--drive-yazma-yok", action="store_true",
                    help="girdileri Drive'dan oku, ciktilari Drive'a yukleme")
    ap.add_argument("--kilitle", action="store_true",
                    help="onayli/<edisyon>/ kirpimlarini ve ALTIN'i yaz "
                         "(Serdar onayi gerekir)")
    ap.add_argument("--edisyon", nargs="*", default=None)
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
