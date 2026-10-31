#!/usr/bin/env python3
"""Kupa sahne fotografinin zeminini kart zeminine (#F5F0E7) esitler (Merkez 27 Eki madde 4, Serdar onayi). Yeniden cizim yok:
kupa pikselleri aynen kalir; yalniz zemin (duvar + masa) duz kart rengine cekilir, kupanin kendi golgesi carpimsal olarak korunur.
- kupa maskesi: GrabCut (kenar 6 px kesin zemin, dikdortgen = sahnenin %3 icerisi), en buyuk parca, 15 px kapama; sonra yerel zeminin
  tek carpanli kopyasi olan ve dis zeminle bitisik pikseller (masadaki golge) cikarilir (kanal oran farki < 0,05); kulp ici delik zemin kalir.
- golge: zemin parlakligi / yerel zemin kestirimi (kupa bolgesi Telea ile doldurulmus sahnenin 101 px medyani; duvar-masa siniri
  korunur). Golge = 1 - oran (0..1), yalniz kupaya YAKIN_PX icinde, uzaklikla dogrusal sonumlenir; uzakta zemin tam #F5F0E7.
- kenar: maske 1 px asindirilir ve 1,2 px yumusatilir (eski zemin rengi hale olarak kalmasin).
- GOVDE KORUMASI (Serdar 31 Eki, K05 kenar kusuru): oyma sonrasi GrabCut'in kupa saydigi govde pikselleri maskeye geri eklenir. Govde = sahnenin
  silindir geometrisi (temiz/kupa-orchard 0196e37a varlik/gorunum/geo_*.json: xl, xr, yt, yb, ust / alt elips yari eksenleri;
  kapak_canva3 baskiyi ayni geometriyle giydirir) + GOVDE_PAY px. Eski kural parlak kenar yansimasini (R > B, dis zeminle bitisik)
  masa golgesi sanip oyuyordu (m15 sag kenar, 31 Eki olcum). Masa golgesi ve kulp ici govde disinda: onlar eskisi gibi cikar.
Olcum (olc): kirpim kenar seridinde (10 px) #F5F0E7'ye en buyuk RGB farki; kupadan > YAKIN_PX uzak zemin piksellerinde en buyuk fark;
kupa kenarindan 2-6 px disaridaki halkada zeminden ACIK sapma (hale) en buyuk deger.
Kullanim: kupa_zemin.py <gorunum klasoru (tek_on.jpg ..., stil_<st>.jpg)> <cikti>  -> z_<ad>.png, k_<ad>.npy, zemin_olcum.json
(yerel dogrulama: pillow 11.0.0, numpy 2.1.3, opencv 4.10.0.84)"""
import numpy as np, cv2
from PIL import Image

ZEMIN = np.float32([245, 240, 231])
YAKIN_PX = 220
GOVDE_PAY = 2      # px: geometri ile gercek kenar arasi kenar yumusatma payi (tek_on xr 1544, GrabCut maskesi 1545)
# temiz/kupa-orchard 0196e37a varlik/gorunum geo_*.json ("sol" / "sag" degeri; [xl, xr, yt, yb, et, eb], sahne pikseli). test_kupa_zemin.py
# bu sabitleri o dosyalarla karsilastirir.
GEO = {"tek_on": (504.0, 1544.0, 450.2, 1615.8, 35.5, 89.4), "tek_arka": (504.0, 1545.0, 452.2, 1621.4, 33.1, 87.5),
       "m15": (522.4, 1600.5, 466.7, 1911.9, 36.8, 92.7)}
ST8 = ("orange", "fig", "olive", "pomegranate", "almond", "lemon", "grape", "loquat")       # orchard_gorunum stil_<st> (kupa 04)
# gorunum adi -> geometri (orchard_gorunum.py / sade_kart.py giydir cagrilariyla ayni)
SAHNE_GEO = {"tek_on": "tek_on", "tek_arka": "tek_arka", "m15": "m15", "ML_on": "tek_on", "ML_arka": "tek_arka", "MJ_on": "tek_on",
             "MJ_arka": "tek_arka", **{f"stil_{x}": "tek_on" for x in ST8}}


def govde(shape, geo, pay=GOVDE_PAY):
    """Silindir kupa govdesi maskesi (uint8): [xl, xr] x [yt, yb] dikdortgeni + ust (yt, et) ve alt (yb, eb) elipsler, pay px genisletilmis."""
    xl, xr, yt, yb, et, eb = geo
    h, w = shape[:2]
    m = np.zeros((h, w), np.uint8)
    cx, ax = (xl + xr) / 2, (xr - xl) / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ic = (xx >= xl) & (xx <= xr) & (yy >= yt) & (yy <= yb)
    ic |= ((xx - cx) / ax) ** 2 + ((yy - yt) / max(et, 1e-6)) ** 2 <= 1
    ic |= ((xx - cx) / ax) ** 2 + ((yy - yb) / max(eb, 1e-6)) ** 2 <= 1
    m[ic] = 1
    return cv2.dilate(m, np.ones((2 * pay + 1, 2 * pay + 1), np.uint8)) if pay > 0 else m


def maske(a):
    h, w = a.shape[:2]
    m = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    b = 6; m[:b] = m[-b:] = cv2.GC_BGD; m[:, :b] = m[:, -b:] = cv2.GC_BGD
    rect = (int(0.03 * w), int(0.03 * h), int(0.94 * w), int(0.94 * h))
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.setRNGSeed(0)       # GrabCut GMM baslangici (kmeans) RNG'ye bagli: her sahne siradan / surecten bagimsiz ayni sonucu verir
    cv2.grabCut(np.ascontiguousarray(a.astype(np.uint8)[..., ::-1]), m, rect, bg, fg, 6, cv2.GC_INIT_WITH_RECT)
    k = np.isin(m, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(k, 8)
    k = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
    return cv2.morphologyEx(k, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def esitle(im, geo):
    """PIL RGB sahne + silindir geometrisi (GEO) -> (PIL RGB zemini esitlenmis sahne, kupa maskesi uint8)"""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    k = maske(a)
    k_gc = k.copy()                                              # GrabCut kupa maskesi (govde korumasi icin)
    lum = a @ np.float32([0.299, 0.587, 0.114])
    dol = cv2.inpaint(a.astype(np.uint8), cv2.dilate(k, np.ones((25, 25), np.uint8)), 9, cv2.INPAINT_TELEA)
    trgb = cv2.medianBlur(dol, 101).astype(np.float32)
    # GrabCut masadaki golgeyi kupaya katabiliyor: golgeli zemin = yerel zemin x tek carpan (kanal oranlari esit); beyaz kupa,
    # baski ve kulp gri tonlari zemine gore kanal orani esit degil (beyaz / bej: 1,04 / 1,10 / 1,16)
    r = a / np.maximum(trgb, 1)
    zeminsi = ((r.max(2) - r.min(2)) < 0.05) & (r.mean(2) > 0.45) & (r.mean(2) < 1.03)
    # masadaki golge zeminden sicak (ten): R >= G >= B, (R - B) / parlaklik 0,05-0,30 (beyaz kupa < 0,04; turuncu baski ~1,2;
    # yaprak G > R). Yalniz dis zeminle bitisik olanlar cikar (asagi), baski ici renkler korunur.
    ten = (a[..., 0] >= a[..., 1]) & (a[..., 1] >= a[..., 2]) & ((a[..., 0] - a[..., 2]) / np.maximum(lum, 1) > 0.05) \
        & ((a[..., 0] - a[..., 2]) / np.maximum(lum, 1) < 0.30) & (lum < 245)
    zeminsi |= ten
    # yalniz dis zeminle bitisik zemin-benzeri bolgeler cikarilir (kupa ici beyaz alanlar oyulmasin)
    n2, lab2 = cv2.connectedComponents((zeminsi | (k == 0)).astype(np.uint8), connectivity=8)
    disa = np.unique(lab2[k == 0])
    k = (k.astype(bool) & ~np.isin(lab2, disa[disa > 0])).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(k, 8)
    k = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
    k = cv2.morphologyEx(k, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    # GOVDE KORUMASI (Serdar 31 Eki): oyma eskisi gibi tam kosar (govde disi sonuc onayli ciktiyla ayni; kenar seridi oyulunca govdeden
    # kopan masa parcasi en buyuk parca adiminda yine atilir), sonra GrabCut'in kupa saydigi GOVDE pikselleri geri eklenir: govde asla
    # zemin sayilmaz. Golge mesafesi eski (govde eklenmemis) maskeden: govde disi golge deseni onayli ciktiyla ayni (yeni maskeyle 1-2 px
    # kayan golge, kart olceginde kopuk ton kapisina takilan 1 px benekler veriyordu; sade CANCER K05 2 px, 31 Eki). (Oymayi govdede baslatmamak masa parcasini govdeye bagli birakiyordu: sade CANCER K05 kopuk ton 10 px, 31 Eki.)
    k_eski = k                                                   # golge alani eski maskeden: govde disi golge onayli ciktiyla AYNI
    k = (k.astype(bool) | (k_gc.astype(bool) & govde(a.shape, geo).astype(bool))).astype(np.uint8)
    tah = trgb @ np.float32([0.299, 0.587, 0.114])
    oran = np.clip(lum / np.maximum(tah, 1), 0, 1)
    uz = cv2.distanceTransform((1 - k_eski).astype(np.uint8), cv2.DIST_L2, 5)
    golge = (1 - oran) * np.clip(1 - uz / YAKIN_PX, 0, 1)
    golge = cv2.GaussianBlur(golge, (0, 0), 2.0)
    zem = ZEMIN[None, None, :] * (1 - golge[..., None])
    al = cv2.GaussianBlur(cv2.erode(k, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2)[..., None]
    out = a * al + zem * (1 - al)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)), k


def olc(out, k):
    """out: esitlenmis kirpim (PIL), k: ayni kirpimin kupa maskesi -> dict"""
    a = np.asarray(out.convert("RGB")).astype(np.float32)
    fark = np.abs(a - ZEMIN).max(axis=2)
    kenar = np.zeros(fark.shape, bool); kenar[:10] = kenar[-10:] = True; kenar[:, :10] = kenar[:, -10:] = True
    uz = cv2.distanceTransform((1 - k).astype(np.uint8), cv2.DIST_L2, 5)
    halka = (uz > 2) & (uz <= 6)
    acik = (a - ZEMIN).max(axis=2)
    return dict(kenar_max=float(fark[kenar & (k == 0)].max()) if (kenar & (k == 0)).any() else 0.0,
                uzak_max=float(fark[(uz > YAKIN_PX)].max()) if (uz > YAKIN_PX).any() else 0.0,
                hale_acik_max=float(acik[halka].max()) if halka.any() else 0.0)


def _isle(g, o, ad):
    if ad not in SAHNE_GEO:
        raise SystemExit(f"DUR: kupa_zemin: {ad} sahnesinin govde geometrisi tanimsiz (SAHNE_GEO)")
    z, k = esitle(Image.open(g / f"{ad}.jpg"), GEO[SAHNE_GEO[ad]])
    z.save(o / f"z_{ad}.png"); np.save(o / f"k_{ad}.npy", k)
    ys, xs = np.nonzero(k)
    return ad, dict(kutu=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], **olc(z, k))


if __name__ == "__main__":
    import json, os, sys
    from concurrent.futures import ProcessPoolExecutor
    from pathlib import Path
    g, o = Path(sys.argv[1]), Path(sys.argv[2]); o.mkdir(parents=True, exist_ok=True); R = {}
    ADLAR = ("tek_on", "tek_arka", "m15", "ML_on", "ML_arka", "MJ_on", "MJ_arka") + tuple(f"stil_{s}" for s in ST8)
    # GrabCut sahne basina ~1-2 dk (2048 px): sahneler paralel (28 Eki yerel: 16 sahne 3 dk 19 sn, CPU toplami 11 dk 20 sn).
    # setRNGSeed(0) ile sonuc siradan bagimsiz; 27 Eki sirali ciktiya gore tek_on disindaki sahnelerde fark 6-15 (maske degisti)
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for ad, r in ex.map(_isle, [g] * len(ADLAR), [o] * len(ADLAR), ADLAR):
            R[ad] = r
            print(ad, r, flush=True)
    import PIL
    R["surum"] = dict(pillow=PIL.__version__, numpy=np.__version__, opencv=cv2.__version__)   # GrabCut opencv surumune duyarli
    (o / "zemin_olcum.json").write_text(json.dumps(R, indent=1))
