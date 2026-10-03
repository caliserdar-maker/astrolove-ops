#!/usr/bin/env python3
"""WALLPAPER V3: murekkep kaynagi = kisisel'in SIPARIS URETICISI (Serdar 25 Eyl 2026).

KARAR: poster + MEDIAN yolu birakildi (dokulu edisyonda ham fark maskesi
isim satirini ayirt edemedi - Warm_Parchment, run 36158458249).

Yeni yol:
  baski   = kisisel'in urettigi ISIMLI 24x32 (3:4, 7200x9600) dosya, edisyonda
  plate   = kisisel PLATE (TEMP/SIPARIS_ISIM/PLATES/<EDISYON>_24X32.png)
  murekkep= baski - plate                      ESIK YOK, ham doku farki YOK
  zemin   = WP_PLATES/CLEAN/PLATE_<ED>_<DEV>_CLEAN.png
  yerlesim= wp_v2 / wp_build_pair afin yolu (WP_LAYOUT_SPEC 7.1) + GEOM
  kapilar = wp_v2'nin 10 kapisi (5 + EK 5)

Aktarim iki bicimde olculebilir (--aktarim):
  fark  (varsayilan): out = CLEAN + place(baski - plate). Premultiply oldugu
        icin glif kenarlarinda kisisel PLATE zemini SIZMAZ; plate ile CLEAN
        ayni oldugu her yerde sonuc tam dogru blend'dir.
  maske             : out = A*place(baski) + (1-A)*CLEAN. Kenar pikselleri
        kisisel PLATE zeminini tasir (hale riski); karsilastirma icin durur.
Iki bicimin farki ve hale olcusu raporlanir; secim olcumle yapilir.
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
import importlib.util                                                         # noqa: E402
_s = importlib.util.spec_from_file_location("wp_v2", Path(__file__).resolve().parent / "wp_v2.py")
V2 = importlib.util.module_from_spec(_s); _s.loader.exec_module(V2)            # noqa: E402
from wp_mockup_common import DEVICES, imread                                   # noqa: E402
import wp_build_pair as WBP                                                    # noqa: E402
from wp_plate_pilot import (BOX_NAMES, INK_RGB, REF_TAGLINE, RING_BAND,          # noqa: E402
                            RING_ELLIPSE, RING_LINE_PX, RING_TIP_Y)

Image.MAX_IMAGE_PIXELS = None
POSTER_W, POSTER_H = V2.POSTER_W, V2.POSTER_H
# Mesaj arama bandi: REF_TAGLINE'in SATIRLARI, tam genislik. Kisisellestirilmis
# mesaj eski slogandan uzun olabilir; x-araligiyla kirpilirsa kutu yanlis olculur
# (yerel olcum 25 Eyl: kutu tam REF_TAGLINE sinirina oturdu, ortalama 2,5 px kaydi).
MESAJ_BANT = (0, REF_TAGLINE[1] - 120, POSTER_W, REF_TAGLINE[3] + 120)
EDISYONLAR, CIHAZLAR = V2.EDISYONLAR, V2.CIHAZLAR
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ girdi
UZANTI = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}


def dosya_bul(kok, parcalar, ne):
    """Adinda verilen tum parcalari (BUYUK/kucuk harf duyarsiz) gecen TEK goruntu.

    Glob yerine parca esleme: gercek plate dosyalari `PURE_WHITE_24x32.png`
    (kucuk x) - 25 Eyl olcumu. Buyuk harfli glob bunu kaciriyordu.
    Yalniz goruntu uzantilari sayilir; kisisel'in cikti klasorundeki yan dosya
    (json, onizleme, kontrol raporu) eslesmeyi bozmasin.
    """
    ad = [x for x in sorted(Path(kok).iterdir()) if x.is_file() and x.suffix.lower() in UZANTI]
    d = [x for x in ad if all(pz.lower() in x.name.lower() for pz in parcalar)]
    if len(d) != 1:
        raise SystemExit(f"HATA: {ne} icin {parcalar} -> {len(d)} goruntu eslesmesi: "
                         f"{[x.name for x in d]}. Tek dosya bekleniyor. "
                         f"Klasorde {len(ad)} goruntu var.")
    return d[0]


def baski_bul(kok, ed, cift):
    """Baski dosyasi: cift ile edisyon YAN YANA olacak sekilde aranir.

    `_{cift}_` yetmez: `_CANCER_LIBRA_` , `_CANCER_LIBRA_UZUN_...` icinde de
    geciyor ve iki eslesme cikiyordu (kosu 36230639918). Cift+edisyon ikilisi
    sinir olarak kullanilir; uretici adlandirmayi ters sirada yaparsa ikinci
    aday denenir.
    """
    hata = []
    for aday in (f"_{cift}_{ed}_", f"_{ed}_{cift}_"):
        try:
            return dosya_bul(kok, ["24x32", aday], f"{ed}/{cift} baski")
        except SystemExit as e:
            hata.append(str(e))
    raise SystemExit("HATA: baski dosyasi bulunamadi. Denenen kaliplar: "
                     f"_{cift}_{ed}_ ve _{ed}_{cift}_ | " + " || ".join(hata))


_PLATE_ONBELLEK, PLATE_ONBELLEK_SINIR = {}, 6


def plate_oku(p):
    """kisisel PLATE edisyon basina AYNI dosyadir; her cift icin yeniden okunuyordu
    (7200x9600 PNG ~1,4 s). Onbellek: en fazla PLATE_ONBELLEK_SINIR edisyon.
    Diziler salt okunur isaretlenir - paylasilan diziye yazma aninda hata verir."""
    k = str(p)
    if k not in _PLATE_ONBELLEK:
        if len(_PLATE_ONBELLEK) >= PLATE_ONBELLEK_SINIR:
            _PLATE_ONBELLEK.pop(next(iter(_PLATE_ONBELLEK)))
        im = imread(p)
        im.flags.writeable = False
        _PLATE_ONBELLEK[k] = im
    return _PLATE_ONBELLEK[k]


def kaynak_oku(baski_kok, plate_kok, ed, cift=""):
    b = baski_bul(baski_kok, ed, cift) if cift else dosya_bul(baski_kok, [ed, "24x32"], f"{ed} baski")
    p = dosya_bul(plate_kok, [ed, "24x32"], f"{ed} plate")
    baski, plate = imread(b), plate_oku(p)
    for ad, im in ((b.name, baski), (p.name, plate)):
        if (im.shape[1], im.shape[0]) != (POSTER_W, POSTER_H):
            raise SystemExit(f"HATA: {ad} {im.shape[1]}x{im.shape[0]}, beklenen {POSTER_W}x{POSTER_H}")
    return baski, plate, b.name, p.name


# ------------------------------------------------------------------ murekkep
def murekkep_rengi(baski, plate, f, ed):
    """Edisyonun murekkep rengi (BGR). Bilinen edisyonda INK_RGB, degilse OLCULUR.

    kisisel edisyonlari (PURE_WHITE, BLACK, BLUE, MODERN, VINTAGE) gece hattinin
    INK_RGB tablosunda YOK - 26 Eyl olcumu. Bu durumda renk tahmin edilmez:
    farkin en guclu %1'indeki baski pikselinin medyani alinir, yani murekkebin
    kendi olculen rengi. Yeni esik getirmez (nicelik dilimi).
    """
    if ed in INK_RGB:
        r, g, b = INK_RGB[ed]
        return np.array([b, g, r], np.float32)
    buy = np.abs(f).max(2)
    var = buy > 0
    if not var.any():
        raise SystemExit(f"HATA: {ed} icin baski - plate farki bos; murekkep rengi olculemez")
    esik = float(np.quantile(buy[var], 0.99))
    sec = buy >= esik
    return np.median(baski[sec].astype(np.float32), axis=0)


def murekkep(baski, plate, ed, hayalet="birak", isaret="uzaklik", sadece_olcum=False,
             yol="hizli"):
    """ESIK YOK: fark = baski - plate (isaretli), murekkep RENGINE UZAKLIKLA ayrilir.

    kisisel PLATE 78 ciftin MEDYANI (kisisel olcumu 25 Eyl): ESKI SLOGAN VAR,
    ∞ YOK, DIS HALKA VAR, isim satiri temiz (%0,02 artik). Bu yuzden farkta:
      poz : baski murekkep rengine plate'ten DAHA YAKIN -> YENI murekkep, aktarilir
      neg : plate daha yakin -> plate'te kalan ESKI oge (eski slogan). CLEAN
            plakada bu oge ZATEN YOK; aktarilirsa negatif hayalet olusur.

    isaret="uzaklik" (varsayilan, Serdar onayi GOREV_0002): 3 boyutlu karsilastirma
      |baski - INK_RGB| < |plate - INK_RGB|. Esik eklemez.
    isaret="izdusum": eski 1 boyutlu test <fark, INK_RGB - zemin>. Yerel olcum
      (25 Eyl): eski murekkebin ALTINDAN cikan YILDIZI altin ekseninde "murekkebe
      yaklasiyor" sayip yeni murekkep saniyordu (53 poster px artik).
    """
    f = baski.astype(np.float32) - plate.astype(np.float32)
    ink = murekkep_rengi(baski, plate, f, ed)
    # yol="referans": GOREV_0014 oncesi kod (denetim ve esitlik testi icin korunur).
    # yol="hizli": ayni karar, daha az tam boyutlu ara dizi. Olculen (7200x9600,
    # sentetik, 4 cekirdek): referans 23,1s -> hizli 9,5s. Esitlik birim testiyle kilitli.
    var = np.abs(f).max(2) > 0 if yol == "referans" else (baski != plate).any(2)
    if isaret == "uzaklik":
        d_b = ((baski.astype(np.float32) - ink) ** 2).sum(2)
        d_p = ((plate.astype(np.float32) - ink) ** 2).sum(2)
        poz, neg, sifir = var & (d_b < d_p), var & (d_b > d_p), var & (d_b == d_p)
        del d_b, d_p
        zemin = None
    else:
        zemin = np.median(plate[::16, ::16].reshape(-1, 3), axis=0).astype(np.float32)
        pr = (f * (ink - zemin)).sum(2)
        poz, neg, sifir = var & (pr > 0), var & (pr < 0), var & (pr == 0)
    # OLCUM her zaman POZITIF maskeden yapilir: hayalet ayari neyin AKTARILDIGINI
    # belirler, neyin OLCULDUGUNU degil. (Yerel olcum 25 Eyl: plate'in isim
    # satirindaki %0,02 artik negatif tarafta; aktarima katilirsa kume olcumu
    # 3 yerine 2 kume buluyor.)
    alfa_olcum = poz.astype(np.float32)
    tani = {"isaret": isaret, "murekkep_bgr": [round(float(v), 1) for v in ink],
            "murekkep_kaynagi": "INK_RGB" if ed in INK_RGB else "olculdu",
            "poz_px": int(poz.sum()), "neg_px": int(neg.sum()),
            "yonsuz_px": int(sifir.sum()),
            "neg_kutu": [int(v) for v in V2.bbox(neg)] if neg.any() else None,
            "neg_maks": round(float(np.abs(f).max(2)[neg].max()), 1) if neg.any() else 0.0}
    if zemin is not None:
        tani["zemin_bgr"] = [round(float(v), 1) for v in zemin]
    # DIKKAT: fark maskesi f'yi YERINDE degistirir; tani ondan ONCE olculur
    # (neg_maks f'nin negatif tarafini okur - birim testiyle kilitli).
    # sadece_olcum: 1. asama yalniz POZITIF maskeyi ve taniyi kullanir; fark/alfa
    # (iki tam boyutlu float32 dizi) bosa uretiliyordu (HIZ, GOREV_0014).
    if sadece_olcum:
        fark = alfa = None
    elif yol == "referans":
        fark = f if hayalet == "gecir" else f * poz[..., None]
        alfa = (np.abs(fark).max(2) > 0).astype(np.float32)
    elif hayalet == "gecir":
        fark = f
        alfa = var.astype(np.float32)         # |f|>0 ile ayni maske (var tanimi)
    else:
        fark = f                              # f * poz[...,None] yerine yerinde maskeleme
        fark[~poz] = 0
        alfa = poz.astype(np.float32)         # alfa == (|fark|>0) : poz ile ayni maske
    return fark, alfa, alfa_olcum, tani


def halka_bandi():
    """Poster olceginde halka bandi (wp_v2.halka_maskesi ile ayni geometri)."""
    bant = np.zeros((POSTER_H, POSTER_W), np.uint8)
    cx, cy, ax, ay = RING_ELLIPSE
    cv2.ellipse(bant, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1,
                int(RING_LINE_PX) + 2 * 5 * RING_BAND, cv2.LINE_8)
    bant[RING_TIP_Y + 1:, :] = 0
    return bant.astype(np.float32)


def halka_katkisi(gece, clean, bant_dev):
    """Halka = (gece plakasi - CLEAN plaka), halka bandiyla sinirli. ESIK YOK.

    Ikisi de ayni cihaz tuvalinde ve CLEAN, gece plakasindan sabit ogeler
    silinerek uretildi; aradaki fark TAM OLARAK sabit ogelerdir. Bant eski
    slogani disarida birakir (RING_TIP_Y altinda kalir).
    """
    d = gece.astype(np.float32) - clean.astype(np.float32)
    m = (np.abs(d).max(2) > 0) & (bant_dev > 0)
    return d * m[..., None], m


def kutular_olc(alfa, halka_ayri=False):
    """Isim satiri (sol / ∞ / sag) ve mesaj kutusu - OLCULEN maskeden, poster px.

    Maske tam (esiksiz) oldugu icin kume ayrimi doku gurultusune bagli degil;
    isim/∞ ayrimi wp_v2'nin "en buyuk iki bosluk" kuralidir.
    """
    m = alfa > 0
    satir = m & (V2.kutu_maske(alfa.shape, BOX_NAMES) > 0)
    mesaj = m & (V2.kutu_maske(alfa.shape, MESAJ_BANT) > 0)
    for ad, x in (("isim satiri", satir), ("mesaj", mesaj)):
        if not x.any():
            raise SystemExit(f"HATA: {ad} murekkebi bulunamadi (baski - plate bos)")
    sol, orta, sag, bilgi = V2.uc_grup(V2.sutun_kumeleri(satir))
    ix = np.arange(alfa.shape[1])
    kutu = {}
    for ad, (x0, x1) in (("sol", sol), ("sonsuz", orta), ("sag", sag)):
        sub = satir & (ix >= x0) & (ix < x1)
        ys = np.nonzero(sub.any(1))[0]
        kutu[ad] = [int(x0), int(ys.min()), int(x1), int(ys.max()) + 1]
    kutu["mesaj"] = list(V2.bbox(mesaj))
    # PLATE'in SABIT ogeleri (halka, fuzyon sembolu) ICERMEDIGI dogrulanir:
    # wallpaper CLEAN plakasinda da yoklar, aktarilmazlarsa kapi 2 duser.
    # HALKA sayimi BOX_SYMBOL_RING ile YAPILMAZ: o kutu fuzyon sembolunu de kapsar
    # (yerel olcum 25 Eyl: halka=sembol=233.264 px, yaniltici uyari). Halka bandi kullanilir.
    say = {"halka": int((m & (halka_bandi() > 0)).sum()),
           "sembol": int((m & (V2.kutu_maske(alfa.shape, V2.BOX_SYMBOL_CORE) > 0)).sum())}
    bekle = ["sembol"] if halka_ayri else ["halka", "sembol"]
    bos = [ad for ad in bekle if say[ad] == 0]
    if bos:
        raise SystemExit(f"HATA: murekkepte {bos} yok ({say}). CLEAN plakada da yoklar; "
                         f"aktarilmazsa kapi 2 duser. Halka plate'te kaliyorsa --halka ver.")
    if halka_ayri and say["halka"] > 0:
        bilgi["uyari"] = (f"--halka verildi ama farkta da halka mürekkebi var ({say['halka']} px); "
                          f"halka iki kez cizilebilir - olcum: kapi 2 halka sapmasi.")
    bilgi["sabit_oge_px"] = say
    return kutu, bilgi


# ------------------------------------------------------------------ uretim
def uret(ed, baski, plate, fark, alfa, temiz, plakalar, cikti, cift, kutu, aktarim, urun, rapor,
         halka_kok="", bant=None, tani_m=None, plaka_ed=None, tani_hale=False, cihazlar=None):
    """plaka_ed: CLEAN/GEOM/gece plakasinin edisyon adi. kisisel edisyonlari
    (PURE_WHITE/BLACK/BLUE) wallpaper edisyonlarindan (MIDNIGHT_BLUE...) FARKLI;
    eslesme --eslesme ile ACIKCA verilir, TAHMIN EDILMEZ."""
    pe = (plaka_ed or ed).upper()
    for dev in (cihazlar or CIHAZLAR):
        yol_p = Path(temiz) / f"PLATE_{pe}_{dev.upper()}_CLEAN.png"
        if not yol_p.exists():
            var = sorted(x.name for x in Path(temiz).glob("PLATE_*_CLEAN.png"))
            raise SystemExit(f"HATA: CLEAN plaka yok: {yol_p.name} (edisyon {ed} -> plaka {pe}). "
                             f"Klasorde: {var[:8]}{'...' if len(var) > 8 else ''}. "
                             f"kisisel edisyonu icin wallpaper plakasi --eslesme ile verilmeli "
                             f"(ornek: --eslesme BLUE=MIDNIGHT_BLUE); tahmin edilmez.")
        clean = imread(yol_p)
        W, H = DEVICES[dev]
        if (clean.shape[1], clean.shape[0]) != (W, H):
            raise SystemExit(f"HATA: CLEAN plaka {yol_p.name} {clean.shape[1]}x{clean.shape[0]}, beklenen {W}x{H}")
        geom = WBP.load_geom(plakalar, pe, dev)
        A = WBP.place(alfa, dev, clean.shape, geom)[..., None]
        C = clean.astype(np.float32)
        if aktarim == "fark":
            out_f = C + WBP.place(fark, dev, clean.shape, geom)
        else:
            out_f = A * WBP.place(baski.astype(np.float32), dev, clean.shape, geom) + (1 - A) * C
        halka_px = 0
        if halka_kok:                      # halka kisisel PLATE'te kaldi -> gece plakasindan
            yol_g = Path(halka_kok) / f"PLATE_{pe}_{dev.upper()}.png"
            if not yol_g.exists():
                raise SystemExit(f"HATA: halkali gece plakasi yok: {yol_g}")
            gece = imread(yol_g)
            if gece.shape[:2] != clean.shape[:2]:
                raise SystemExit(f"HATA: {yol_g.name} {gece.shape[1]}x{gece.shape[0]} != CLEAN {W}x{H}")
            bant_dev = WBP.place(bant, dev, clean.shape, geom)
            hk, hm = halka_katkisi(gece, clean, bant_dev)
            out_f = out_f + hk
            A = np.maximum(A, hm[..., None].astype(np.float32))
            halka_px = int(hm.sum())
            del gece, bant_dev, hk, hm
        out = np.clip(np.round(out_f), 0, 255).astype(np.uint8)
        ad = f"AstroLove_{cift}_{ed}_{dev}.jpg"
        Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).save(Path(cikti) / ad, "JPEG",
                                                                   quality=95, subsampling=0)
        geri = imread(Path(cikti) / ad)
        dis = A[..., 0] <= 0
        d_out = np.abs(out.astype(np.int16) - clean.astype(np.int16)).max(2)
        k1 = {"gecti": bool(d_out[dis].max() == 0), "maks_fark": int(d_out[dis].max()),
              "jpeg_sonrasi": int(np.abs(geri.astype(np.int16) - clean.astype(np.int16)).max(2)[dis].max()),
              "piksel": int(dis.sum())}
        mb = V2.kirp(V2.cihaz_kutusu(kutu["mesaj"], dev, geom), W, H, 4)
        b0, b1 = max(mb[1] - 8, 0), min(mb[3] + 8, H)
        bd = d_out[b0:b1][dis[b0:b1]]
        ek5 = {"bant": [int(b0), int(b1)], "murekkep_disi_maks_fark": int(bd.max()) if bd.size else 0,
               "piksel": int(bd.size), "gecti": bool((bd.max() if bd.size else 0) == 0)}
        # TANI (kapi degil): kisisel PLATE ile CLEAN plaka ne kadar ayri -> hale riski.
        # Tam cozunurluklu fazladan bir place() maliyeti; varsayilan KAPALI (HIZ, GOREV_0014).
        halo = {"olculmedi": True}
        if tani_hale:
            PL = WBP.place(plate.astype(np.float32), dev, clean.shape, geom)
            ring = (A[..., 0] > 0) & (A[..., 0] < 1)
            if ring.any():
                hv = np.abs(PL - C).max(2)[ring]
                halo = {"medyan": round(float(np.median(hv)), 1),
                        "p99": round(float(np.percentile(hv, 99)), 1),
                        "maks": round(float(hv.max()), 1), "px": int(hv.size)}
            else:
                halo = {"medyan": 0.0, "p99": 0.0, "maks": 0.0, "px": 0}
            del PL
        urun[(ed, dev)] = dict(yol=str(Path(cikti) / ad), plaka=str(yol_p), geom=geom, kapi1=k1,
                               ek5=ek5, kutu_duzen=kutu)
        rapor.append({"edisyon": ed, "plaka_edisyonu": pe, "cift": cift, "cihaz": dev,
                      "dosya": ad, "aktarim": aktarim,
                      "kapi1_maske_disi": k1, "ek5_mesaj_bandi": ek5, "halka_px": halka_px,
                      "tani_murekkep": tani_m, "tani_plate_clean_kenar_farki": halo, "kutular": kutu})
        log(f"{ed} {dev}: maske disi {k1['maks_fark']} (JPEG {k1['jpeg_sonrasi']}) | "
            f"mesaj bandi {ek5['murekkep_disi_maks_fark']} | halka {halka_px} px | "
            f"tani hale {'kapali' if halo.get('olculmedi') else halo['medyan']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--baski", required=True, help="kisisel ISIMLI 24x32 baski dosyalari (edisyon basina 1)")
    ap.add_argument("--plate", required=True, help="kisisel PLATE: <EDISYON>_24X32.png")
    ap.add_argument("--temiz", required=True, help="PLATE_<ED>_<DEV>_CLEAN.png")
    ap.add_argument("--plakalar", default="", help="GEOM_<ED>_<DEV>.json (yoksa birim)")
    ap.add_argument("--orijinal", default="", help="kapi 2 icin canli wallpaper'lar")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--cift", default="Aries_Leo", help="tek cift (geriye uyum)")
    ap.add_argument("--ciftler", default="", help="virgulle birden cok cift: CANCER_LIBRA,SAGITTARIUS_SAGITTARIUS,...")
    ap.add_argument("--eslesme", default="", help="kisisel edisyonu -> wallpaper plaka edisyonu, "
                                                 "ornek: BLUE=MIDNIGHT_BLUE,BLACK=DEEP_BLACK. "
                                                 "Verilmezse edisyon adi aynen kullanilir; "
                                                 "plaka bulunamazsa DURur (tahmin yok).")
    ap.add_argument("--aktarim", choices=("fark", "maske"), default="fark")
    ap.add_argument("--halka", default="", help="halkali gece plakalari (PLATE_<ED>_<DEV>.png); "
                                                "kisisel PLATE halkayi iceriyorsa zorunlu")
    ap.add_argument("--isaret", choices=("uzaklik", "izdusum"), default="uzaklik",
                    help="yeni/eski murekkep ayrimi: uzaklik = 3B (onayli), izdusum = eski 1B")
    ap.add_argument("--hayalet", choices=("birak", "gecir"), default="birak",
                    help="plate'te kalan eski ∞/slogan farki: birak=aktarma (varsayilan), gecir=aktar")
    ap.add_argument("--edisyonlar", default=",".join(EDISYONLAR))
    ap.add_argument("--sadece-olcum", action="store_true")
    ap.add_argument("--murekkep-yol", choices=("hizli", "referans"), default="hizli",
                    help="murekkep ayrimi kod yolu: hizli (varsayilan) ya da referans "
                         "(GOREV_0014 oncesi kod; ayni sonuc, olculen 23,1s vs 9,5s)")
    ap.add_argument("--cihaz-isci", type=int, default=1,
                    help="cihaz basina paralellik (olculdu: 3 isci uretim adimini "
                         "4,7s -> 2,3s indirdi; varsayilan 1 = sirali, deterministik)")
    ap.add_argument("--tani-hale", action="store_true",
                    help="plate/CLEAN kenar farki tanisi (cihaz basina fazladan bir tam "
                         "cozunurluklu place; varsayilan kapali - HIZ)")
    a = ap.parse_args(argv)
    ed_list = [e.strip() for e in a.edisyonlar.split(",") if e.strip()]
    cift_list = [c.strip() for c in (a.ciftler or a.cift).split(",") if c.strip()]
    # GOREV_0014 YUKSEK1: bos liste eskiden sessizce 0 dosya + bos rapor + exit 0 uretiyordu.
    if not ed_list:
        raise SystemExit(f"HATA: --edisyonlar bos ({a.edisyonlar!r}) - uretilecek edisyon yok. DUR.")
    if not cift_list:
        raise SystemExit(f"HATA: cift listesi bos ({(a.ciftler or a.cift)!r}). DUR.")
    yinelenen = sorted({x for x in ed_list if ed_list.count(x) > 1})
    if yinelenen:
        raise SystemExit(f"HATA: --edisyonlar yinelenen deger iceriyor: {yinelenen}. DUR.")
    eslesme = {}
    for par in (x for x in a.eslesme.split(",") if x.strip()):
        if "=" not in par:
            raise SystemExit(f"HATA: --eslesme parcasi 'EDISYON=PLAKA' olmali: {par!r}")
        k, v = par.split("=", 1)
        eslesme[k.strip()] = v.strip()
    cikti = Path(a.cikti); cikti.mkdir(parents=True, exist_ok=True)
    bant = halka_bandi() if a.halka else None
    log(f"edisyonlar={ed_list} ciftler={cift_list} eslesme={eslesme or 'yok (ad aynen)'}")

    # --- 1. ASAMA: tum edisyonlar once OLCULUR (uretim yok) --------------
    olcum = {}
    for cift in cift_list:
        for ed in ed_list:
            baski, plate, bn, pn = kaynak_oku(a.baski, a.plate, ed, cift)
            _f, _a, alfa_olcum, tani = murekkep(baski, plate, ed, a.hayalet, a.isaret,
                                                sadece_olcum=True, yol=a.murekkep_yol)
            kutu, bilgi = kutular_olc(alfa_olcum, bool(a.halka))
            olcum[f"{cift}|{ed}"] = {"cift": cift, "edisyon": ed, "baski": bn, "plate": pn,
                                     "kutular": kutu, "kume": bilgi, "tani_murekkep": tani,
                                     "murekkep_px": int((alfa_olcum > 0).sum())}
            log(f"OLCUM {cift} {ed}: kume={json.dumps(bilgi)}")
            log(f"       tani={json.dumps(tani)}")
            log(f"       kutular={json.dumps(kutu)}")
            del baski, plate, _f, _a, alfa_olcum
    (cikti / "WP_SIPARIS_OLCUM.json").write_text(json.dumps(olcum, indent=1))
    for cift in cift_list:                      # ayni ciftte edisyonlar arasi sapma
        an = [f"{cift}|{e}" for e in ed_list if f"{cift}|{e}" in olcum]
        if len(an) > 1:
            sap = {k: int(np.abs(np.asarray([olcum[x]["kutular"][k] for x in an]) -
                                 np.asarray(olcum[an[0]]["kutular"][k])).max())
                   for k in ("sol", "sonsuz", "sag", "mesaj")}
            log(f"{cift}: edisyonlar arasi kutu sapmasi (px): {json.dumps(sap)}")
    if a.sadece_olcum:
        log("SADECE OLCUM: uretim yapilmadi")
        return olcum, [], {}

    # --- 2. ASAMA: URETIM ------------------------------------------------
    # ORTA (GOREV_0014): edisyonlar AYNI yerlesimi paylasir. Eskiden her edisyon KENDI
    # olctugu kutulari kullaniyordu (BLUE mesaj_cap 117 / BLACK 228 -> punto 172 / 337).
    # Referans: ciftin ILK edisyonu; sapma raporlanir, paylasim kapisi wp_v2'de.
    urun, rapor = {}, []
    for cift in cift_list:
        urun[cift] = {}                 # (ed, dev) anahtari ciftler arasinda cakisirdi
        paylasim = olcum[f"{cift}|{ed_list[0]}"]["kutular"]
        for ed in ed_list:
            baski, plate, _, _ = kaynak_oku(a.baski, a.plate, ed, cift)
            fark, alfa, _alfa_o, tani = murekkep(baski, plate, ed, a.hayalet, a.isaret,
                                                 yol=a.murekkep_yol)
            ortak = (ed, baski, plate, fark, alfa, a.temiz, a.plakalar or a.temiz, cikti, cift,
                     paylasim, a.aktarim)
            if a.cihaz_isci > 1:
                def tek(dev, _o=ortak):
                    u, r = {}, []
                    uret(*_o, u, r, a.halka, bant, tani, eslesme.get(ed, ed), a.tani_hale, [dev])
                    return dev, u, r
                with ThreadPoolExecutor(max_workers=a.cihaz_isci) as ex:
                    sonuc = list(ex.map(tek, list(CIHAZLAR)))
                for dev in CIHAZLAR:                 # sira deterministik kalir
                    for d, u, r in sonuc:
                        if d == dev:
                            urun[cift].update(u); rapor += r
            else:
                uret(*ortak, urun[cift], rapor, a.halka, bant, tani,
                     eslesme.get(ed, ed), a.tani_hale)
            del baski, plate, fark, alfa, _alfa_o
    (cikti / "WP_SIPARIS_URETIM.json").write_text(json.dumps(rapor, indent=1))
    # YUKSEK1: beklenen dosya sayisi tutmazsa DUR (eksik cikti "basarili" sayilmaz)
    bekle = len(cift_list) * len(ed_list) * len(CIHAZLAR)
    var = sum(1 for c in urun.values() for u in c.values() if Path(u["yol"]).is_file())
    if len(rapor) != bekle or var != bekle:
        raise SystemExit(f"HATA: beklenen {bekle} dosya ({len(cift_list)} cift x {len(ed_list)} "
                         f"edisyon x {len(CIHAZLAR)} cihaz), rapor {len(rapor)}, diskte {var}. DUR.")
    log(f"dosya sayisi: {var}/{bekle} TAMAM")
    return olcum, rapor, urun


if __name__ == "__main__":
    olcum, rapor, urun = main()
    if not rapor:
        # YUKSEK1: eskiden exit 0 idi. --sadece-olcum disinda bos cikti BASARISIZLIKTIR.
        if "--sadece-olcum" in sys.argv:
            log("SADECE OLCUM: kapi/sayfa yok")
            sys.exit(0)
        raise SystemExit("HATA: hic dosya uretilmedi (bos rapor). DUR.")
    import sys as _s
    _a = _s.argv
    cikti = _a[_a.index("--cikti") + 1]
    orij = _a[_a.index("--orijinal") + 1] if "--orijinal" in _a else ""
    ed_list = sorted({v["edisyon"] for v in olcum.values()},
                     key=lambda e: [v["edisyon"] for v in olcum.values()].index(e))
    hepsi_gecti = True
    for cift, u in urun.items():
        duzen = {"kutular": olcum[f"{cift}|{ed_list[0]}"]["kutular"]}
        es = {}
        if "--eslesme" in _a:
            es = dict(x.split("=", 1) for x in _a[_a.index("--eslesme") + 1].split(",") if "=" in x)
        K = V2.kapilar(u, None, duzen, orij, cift, Path(cikti) / f"KAPI_{cift}", ed_list, es)
        log(f"KAPILAR {cift} gecti={K['gecti']}")
        for ad in ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
                   "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
            kot = [x for x in K[ad] if not x["gecti"]]
            log(f"  {ad}: {len(K[ad]) - len(kot)}/{len(K[ad])} gecti" + (f" | KALAN {kot[:3]}" if kot else ""))
        log(f"  metin_renkler: {json.dumps(K['metin_4renk'])}")
        log(f"  ek4_harf_yuksekligi: {json.dumps(K['ek4_harf_yuksekligi'])}")
        if K.get("halka_sembol_atlanan"):
            log(f"  kapi 2 ATLANAN (orijinal bulunamadi): {json.dumps(K['halka_sembol_atlanan'])}")
        sy = V2.sayfalar(u, orij, cift, cikti, ed_list)
        log(f"  sayfa: {len(sy)} dosya")
        hepsi_gecti = hepsi_gecti and K["gecti"]
    _s.exit(0 if hepsi_gecti else 1)
