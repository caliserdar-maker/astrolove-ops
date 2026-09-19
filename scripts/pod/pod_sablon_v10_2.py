#!/usr/bin/env python3
"""POD sablon V10.2 - V10.1 + uc degisiklik.

A. Kalinlik genisletmesi ve cekirdekten renk yayilmasi KALDIRILDI. Katman 2
   sekilleri posterin kendi piksellerinden gradient map + histogram esleme,
   1 px uzaklik rampasi alfa; baska islem yok.
B. K4: referans ve yeni ayni yontemle olculur -- Y kanali, bolgedeki tepe
   parlakligin %50'sinde ikililestirilir, medyan vurus kalinligi; tol. 1.5 px.
C. Halka (daire cizgisi), oo, "Two Souls - One Bond", yildizlar: referansin
   YUV baytlari birebir; +4 px koruma bandi tum katman islemlerinden disari.
   Kapi: halka bandinda Y/U/V MAE < 0.5.

V10.1 aciklamasi:

A. Isim maskesi: sonsuzluk (oo) dislamasi posterdeki oo bileseninin KENDI sinir
   kutusuna daraltilir (V10 referans isim maskesindeki bos sutun araligini
   kullaniyordu; "AQUARIUS"un S harfi yutuluyordu). Kapi: kare 0 OCR.
B. K2 taban lumasi yalniz Y ekseninde uygulanir (RGB'ye sabit ekleme; BT.601
   U/V degismez). Kapi: ana sembol halka bandinda ort. U/V referansla +-2.

V10 aciklamasi:

A. SEKIL KAYNAGI: Katman 2 maskeleri/sekilleri Drive ORIGINAL_HIGH_RES
   Midnight Blue posterinden (panele olceklenir, altin maske esikle; delik
   doldurma yalniz 40 px alti). Alfa rampasi 1 px.
B. KUCUK SEMBOL SONMESI: kucuk sembol maskeleri isim maskesinden kesin ayri;
   0.57-3.50 sn arasi Katman 2 katkisi 0.
C. KATMAN SIRASI: zemin -> referans ogeleri -> Katman 2 -> TOZ EN USTTE
   (screen).
D. Ana sembol tozun altinda yumusar: referansin ana sembol maskesindeki kenar
   enerjisi orani (kare t / kare 0) olculur, Katman 2 ana sembolune ayni orani
   veren Gauss bulanikligi uygulanir (sembol kaybolmaz).

Kapilar K1-K5 KAPILAR.json'a yazilir; gecmezse cikis kodu 3.
Yerel calisir, Etsy cagrisi yoktur.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, cift_hizala, karsilastirma,  # noqa: E402
                           kareleri_ac, kutu_olcekle, panel_kutusu,
                           rgb_yuv_doseme, yuv_ac, yuv_dis_mae, yuv_video_yaz)
from pod_sablon_v5 import kapak_ac, kutu_boyut, mae  # noqa: E402
from pod_sablon_v6 import maske_panele  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from pod_sablon_v8 import (gorunurluk_egrisi, katman_maskeleri,  # noqa: E402
                           kuyruk_normalize, panel_y, temiz_zemin, zamanlama)
from pod_sablon_v9 import (TEMIZ_GENIS, gradient_lut, histogram_esle,  # noqa: E402
                           isim_maskesi, luma, panel_rgb)
from pod_sablon_v9_1 import kaydir, kapsam_alfa, merkez  # noqa: E402

TOZ_TABAN = 3.0
DELIK_EN_COK = 40
RAMPA = 1.0
SONME_BASI_SN, SONME_SONU_SN = 0.57, 3.50
KAPI_KARELER = (60, 90, 120)
KORUMA_PX = 4
K4_TOL = 1.5
OGELER = ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim")


def kapat(m, en_cok=DELIK_EN_COK):
    dolu = ndimage.binary_fill_holes(m)
    delik = dolu & ~m
    if not delik.any():
        return m
    et, _ = ndimage.label(delik)
    kucuk = np.zeros_like(m)
    for i, dil in enumerate(ndimage.find_objects(et), start=1):
        if dil is None:
            continue
        c = et[dil] == i
        if int(c.sum()) <= en_cok:
            kucuk[dil] |= c
    return m | kucuk


def poster_kapak_yap(poster_yol, kutu_kapak):
    """Posteri referans kapak geometrisine oturtur (2400x3000 sanal kapak).

    Panel kutusuna yuksekligi sigacak sekilde, en-boy korunarak, yatayda
    ortalanarak yerlestirilir. Boylece mevcut maske fonksiyonlari (bolgeli
    altin maskesi, isim ayrimi) degismeden kullanilir.
    """
    ph = kutu_kapak["alt"] - kutu_kapak["ust"] + 1
    pw = kutu_kapak["sag"] - kutu_kapak["sol"] + 1
    with Image.open(poster_yol) as im:
        p = im.convert("RGB")
        olcek = ph / p.height
        yeni_w = round(p.width * olcek)
        if yeni_w > pw:                       # genisse genislige sigdir
            olcek = pw / p.width
            yeni_w = pw
        yeni_h = round(p.height * olcek)
        p = p.resize((yeni_w, yeni_h), Image.Resampling.LANCZOS)
    tuval = Image.new("RGB", KAPAK, (8, 12, 36))
    x = kutu_kapak["sol"] + (pw - yeni_w) // 2
    y = kutu_kapak["ust"] + (ph - yeni_h) // 2
    tuval.paste(p, (x, y))
    return np.asarray(tuval, dtype=np.uint8), {"olcek": round(olcek, 5),
                                               "yerlesim": [x, y, yeni_w, yeni_h]}


def poster_ogeleri(poster_panel, ref_m):
    """Poster panelinden ogeleri, REFERANS DUZENINI oncelik alarak ayirir.

    Sablon ayni oldugu icin her ogenin yeri referanstakiyle ortusur:
    - ana sembol: referans ana kutusuyla ortusen, kutusu referanstan cok
      buyuk olmayan (halka disarida kalir) bilesenler,
    - kucuk semboller: merkezi referans kucuk sembol kutusunun icinde
      (25 px pay) olan bilesenler,
    - isim: merkezi referans isim bandinda olan bilesenler; referans isim
      maskesindeki sonsuzluk boslugu icine dusenler (sonsuzluk) haric.
    """
    r, g, b = poster_panel[..., 0], poster_panel[..., 1], poster_panel[..., 2]
    altin = (r > 44) & (g > 29) & (r > b * 1.16) & (g > b * 1.04) & (r > g * 1.01)
    et, _ = ndimage.label(altin, structure=np.ones((3, 3), np.uint8))
    sekil = altin.shape

    def kutu_of(m):
        ys, xs = np.where(m)
        return [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())]

    rk = {ad: kutu_of(m) for ad, m in ref_m.items() if m.any()}
    # V10.1/A: sonsuzluk dislamasi posterdeki oo bileseninin KENDI sinir
    # kutusu (isim bandinda, panel ortasina en yakin YATAY bilesen)
    ki = rk["isim"]
    orta = sekil[1] // 2
    sonsuz = None
    for i, dil in enumerate(ndimage.find_objects(et), start=1):
        if dil is None:
            continue
        c = et[dil] == i
        if int(c.sum()) < 30:
            continue
        y0, y1, x0, x1 = dil[0].start, dil[0].stop - 1, dil[1].start, dil[1].stop - 1
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        if not (ki[0] - 12 <= cy <= ki[1] + 12):
            continue
        # oo: panel ortasina yakin, harflerden yatay (en/boy >= 2) bilesen
        if abs(cx - orta) < 80 and (x1 - x0 + 1) >= 2 * (y1 - y0 + 1):
            if sonsuz is None or abs(cx - orta) < abs(
                    (sonsuz[2] + sonsuz[3]) / 2 - orta):
                sonsuz = [y0, y1, x0, x1]
    bosluk = (sonsuz[2], sonsuz[3]) if sonsuz else (orta, orta)
    cikti = {ad: np.zeros(sekil, dtype=bool) for ad in
             ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim")}
    for i, dil in enumerate(ndimage.find_objects(et), start=1):
        if dil is None:
            continue
        c = et[dil] == i
        alan = int(c.sum())
        if alan < 30:
            continue
        y0, y1, x0, x1 = dil[0].start, dil[0].stop - 1, dil[1].start, dil[1].stop - 1
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        m = np.zeros(sekil, dtype=bool)
        m[dil] = c
        ra = rk["ana_sembol"]
        if (alan >= 500 and y1 >= ra[0] - 20 and y0 <= ra[1] + 20
                and x1 >= ra[2] - 20 and x0 <= ra[3] + 20
                and (x1 - x0) <= (ra[3] - ra[2]) + 40
                and (y1 - y0) <= (ra[1] - ra[0]) + 40):
            cikti["ana_sembol"] |= m
            continue
        yer = False
        for ad in ("kucuk_burc_1", "kucuk_burc_2"):
            k = rk.get(ad)
            if k and k[0] - 25 <= cy <= k[1] + 25 and k[2] - 25 <= cx <= k[3] + 25:
                cikti[ad] |= m
                yer = True
                break
        if yer:
            continue
        if (ki[0] - 12 <= cy <= ki[1] + 12
                and not (bosluk[0] <= cx <= bosluk[1])):
            cikti["isim"] |= m
    return cikti, {"sonsuzluk_kutusu": sonsuz, "sonsuzluk_boslugu": list(bosluk)}


def panel_uv(veri, kare_bayt, i, kutu, w, h):
    """I420 karesinin U ve V duzlemlerini (tam cozunurluge tekrarli buyutulmus)
    panel kesitiyle dondurur."""
    kare = np.frombuffer(veri[i * kare_bayt:(i + 1) * kare_bayt], dtype=np.uint8)
    n = w * h
    u = kare[n:n + n // 4].reshape(h // 2, w // 2)
    v = kare[n + n // 4:n + n // 2].reshape(h // 2, w // 2)
    cikti = []
    for d in (u, v):
        tam = np.repeat(np.repeat(d, 2, axis=0), 2, axis=1)
        cikti.append(tam[kutu["ust"]:kutu["alt"] + 1,
                         kutu["sol"]:kutu["sag"] + 1].astype(np.float32))
    return cikti


def halka_bandi(maske, kalinlik=3):
    """Ogenin dis kenar bandi (maske - erozyon)."""
    return maske & ~ndimage.binary_erosion(maske, iterations=kalinlik)


def isim_ocr(y_panel, isim_maske, yol):
    """Kare 0 isim bolgesinde tesseract OCR (buyuk harf, tek satir)."""
    import pytesseract
    ys, xs = np.where(isim_maske)
    y0, y1 = max(ys.min() - 8, 0), min(ys.max() + 9, y_panel.shape[0])
    x0, x1 = max(xs.min() - 12, 0), min(xs.max() + 13, y_panel.shape[1])
    kes = y_panel[y0:y1, x0:x1]
    im = Image.fromarray(np.clip(kes, 0, 255).astype(np.uint8))
    im = im.resize((im.width * 3, im.height * 3), Image.Resampling.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    esik = (a.min() + a.max()) / 2
    siyah_ustune = Image.fromarray(np.where(a > esik, 0, 255).astype(np.uint8))
    siyah_ustune.save(yol)
    metin = pytesseract.image_to_string(
        siyah_ustune, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
    return "".join(ch for ch in metin.upper() if ch.isalpha() or ch == " ").strip()


def esikli_kalinlik(y, bolge, oran=0.5):
    """V10.2/B: bolgedeki tepe parlakligin %50'sinde ikililestirilmis Y'den
    medyan vurus kalinligi (referans ve yeni icin ayni yontem)."""
    if not bolge.any():
        return None, None
    tepe = float(np.percentile(y[bolge], 99.5))
    ikili = bolge & (y >= oran * tepe)
    return vurus_kalinligi(ikili), round(oran * tepe, 1)


def kucuk_kirpinti(ref_png, yeni_png, kes, yol, genislik=1200, en_cok_kb=250):
    """referans|yeni yan yana kirpinti; 1200 px genislik, <=250 KB JPEG."""
    par = []
    for yp in (ref_png, yeni_png):
        with Image.open(yp) as im:
            par.append(im.convert("RGB").crop(kes))
    w = par[0].width * 2 + 8
    tuval = Image.new("RGB", (w, par[0].height), (245, 245, 245))
    tuval.paste(par[0], (0, 0))
    tuval.paste(par[1], (par[0].width + 8, 0))
    tuval = tuval.resize((genislik, round(genislik * tuval.height / w)),
                         Image.Resampling.LANCZOS)
    for q in (92, 88, 84, 80, 75, 70, 65, 60, 50, 40):
        tuval.save(yol, quality=q, optimize=True)
        if yol.stat().st_size <= en_cok_kb * 1024:
            break
    return yol.stat().st_size


def vurus_kalinligi(maske):
    """Medyan vurus kalinligi (px): uzaklik donusumunun sirt piksellerinde 2*dt."""
    if not maske.any():
        return None
    dt = ndimage.distance_transform_edt(maske)
    sirt = maske & (dt >= ndimage.maximum_filter(dt, size=3) - 1e-6) & (dt > 0)
    if not sirt.any():
        return None
    return round(float(2.0 * np.median(dt[sirt])), 2)


def kenar_enerji(y, maske):
    gy, gx = np.gradient(y.astype(np.float32))
    return float(np.hypot(gx, gy)[maske].mean()) if maske.any() else 0.0


def komsu_zemin(y, maske, pay=6):
    halka = ndimage.binary_dilation(maske, iterations=pay) & ~ndimage.binary_dilation(
        maske, iterations=2)
    return float(np.median(y[halka])) if halka.any() else float(np.median(y))


def screen(taban, toz_rgb):
    return 255.0 - (255.0 - taban) * (255.0 - np.clip(toz_rgb, 0, 255)) / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="_veri/v8")
    ap.add_argument("--out", required=True)
    ap.add_argument("--onceki", default=None, help="V10 KAPILAR.json (sapma kapisi)")
    a = ap.parse_args()
    veri = pathlib.Path(a.veri)
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    (out / "KUCUK_KIRPINTI").mkdir(exist_ok=True)

    ref_video = veri / "referans_video.mp4"
    v5_video = veri / "v5_ornek_video.mp4"
    poster_yol = veri / "poster_aquarius_aries.png"
    meta = probe(ref_video)
    ak = meta["streams"][0]
    vw, vh = int(ak["width"]), int(ak["height"])
    sure = float(meta["format"]["duration"])
    p, q = (ak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = round(float(p) / float(q), 3)

    ref_kapak_a = kapak_ac(veri / "referans_kapak.png")
    kutu_kapak = panel_kutusu(ref_kapak_a)
    kutu = cift_hizala(kutu_olcekle(kutu_kapak, KAPAK[1], vh, KAPAK[0], vw))
    pw, ph = kutu_boyut(kutu)

    # ---- referans maskeleri
    ref_k, _, _ = katman_maskeleri(ref_kapak_a)
    ref_isim_k, _ = isim_maskesi(ref_kapak_a, ref_k["ana_sembol"],
                                 (ref_k.get("kucuk_burc_1"), ref_k.get("kucuk_burc_2")))
    ref_m = {ad: kapat(maske_panele(m, kutu_kapak, pw, ph))
             for ad, m in ref_k.items() if m.any()}
    ref_m["isim"] = kapat(maske_panele(ref_isim_k, kutu_kapak, pw, ph))
    # V10.2/C: koruma = referans altin pikselleri - degistirilen ogeler
    # (kalan: daire halkasi, oo, alt satir, yildizlar), +KORUMA_PX bant
    ref_altin_p = maske_panele(artwork_mask(ref_kapak_a), kutu_kapak, pw, ph)
    degisen = np.zeros((ph, pw), dtype=bool)
    for m in ref_m.values():
        degisen |= ndimage.binary_dilation(m, iterations=2)
    kalan = ref_altin_p & ~degisen
    et_k, _ = ndimage.label(kalan, structure=np.ones((3, 3), np.uint8))
    halka = np.zeros((ph, pw), dtype=bool)
    en_buyuk = 0
    for i, dil in enumerate(ndimage.find_objects(et_k), start=1):
        if dil is None:
            continue
        alan_k = (dil[0].stop - dil[0].start) * (dil[1].stop - dil[1].start)
        if alan_k > en_buyuk:
            en_buyuk, halka = alan_k, et_k == i
    koruma = ndimage.binary_dilation(kalan, iterations=KORUMA_PX)
    halka_bant = ndimage.binary_dilation(halka, iterations=KORUMA_PX)
    log(f"koruma: kalan px {int(kalan.sum())}, halka px {int(halka.sum())}, "
        f"koruma bandi px {int(koruma.sum())}")

    # ---- A: cift maskeleri POSTERDEN
    poster_kapak, poster_not = poster_kapak_yap(poster_yol, kutu_kapak)
    Image.fromarray(poster_kapak).save(out / "_is" / "poster_sanal_kapak.png")
    poster_panel = np.asarray(Image.fromarray(poster_kapak).crop(
        (kutu_kapak["sol"], kutu_kapak["ust"], kutu_kapak["sag"] + 1,
         kutu_kapak["alt"] + 1)).resize((pw, ph), Image.Resampling.LANCZOS),
        dtype=np.uint8).astype(np.float32)
    cift_ham, cift_not = poster_ogeleri(poster_panel, ref_m)
    cift_m = {ad: kapat(m) for ad, m in cift_ham.items() if m.any()}
    # B: kucuk semboller isimden kesin ayri
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in cift_m and "isim" in cift_m:
            cift_m["isim"] &= ~ndimage.binary_dilation(cift_m[ad], iterations=2)
    log(f"poster ayrim notu: {cift_not}")
    # V10.2/A: kalinlik genisletmesi ve cekirdekten yayilma yok
    cift_cekirdek = dict(cift_m)
    genisletme = {ad: 0 for ad in cift_m}

    def kutu_of(m):
        ys, xs = np.where(m)
        return [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())] \
            if m.any() else None
    log(f"poster: {poster_not} | maske px "
        f"{ {k: int(v.sum()) for k, v in cift_m.items()} }")
    log(f"sinir kutulari (panel): "
        f"{ {k: kutu_of(v) for k, v in cift_m.items()} }")

    ref_kareler = kareleri_ac(ref_video, out / "_is" / "refkare")
    ref0 = panel_rgb(ref_kareler, 0, kutu).astype(np.float32)

    # ---- konum: cift ogelerini referans merkezine oturt
    kaydirma = {}
    for ad in OGELER:
        if ad in cift_m and ad in ref_m and cift_m[ad].any() and ref_m[ad].any():
            mr, mc = merkez(ref_m[ad]), merkez(cift_m[ad])
            kaydirma[ad] = (int(round(mr[0] - mc[0])), int(round(mr[1] - mc[1])))
    log(f"konum kaydirmasi (dy,dx): {kaydirma}")

    # ---- boyama (V9.2 gibi: gradient map + histogram, poster lumasindan)
    poster_l = ndimage.median_filter(luma(poster_panel), size=3)
    kucuk_ref = np.zeros((ph, pw), dtype=bool)
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in ref_m:
            kucuk_ref |= ref_m[ad]
    kaynak_of = {"ana_sembol": ref_m.get("ana_sembol"), "isim": ref_m.get("isim"),
                 "kucuk_burc_1": kucuk_ref, "kucuk_burc_2": kucuk_ref}
    alfa, boyali, maske_k = {}, {}, {}
    for ad in OGELER:
        m = cift_m.get(ad)
        cek = cift_cekirdek.get(ad)
        kay = kaynak_of.get(ad)
        if m is None or not m.any() or kay is None or not kay.any():
            continue
        lut, ref_l = gradient_lut(ref0, kay)
        eslenen = histogram_esle(poster_l[cek], ref_l)
        # K2: eslenen luma 42 altina inmez (LUT girisi sinirlanir)
        idx = np.clip(np.rint(eslenen), 42, 255).astype(np.int32)
        renk = np.zeros((ph, pw, 3), dtype=np.float32)
        renk[cek] = lut[idx]
        al = kapsam_alfa(m, rampa=RAMPA)
        al = al * (~koruma)                    # C: koruma bandina Katman 2 yok
        dy, dx = kaydirma.get(ad, (0, 0))
        alfa[ad] = kaydir(al, dy, dx)
        boyali[ad] = kaydir(renk, dy, dx)
        maske_k[ad] = kaydir(m, dy, dx)
    konum_fark = {ad: [round(x - y, 1) for x, y in zip(merkez(maske_k[ad]),
                                                        merkez(ref_m[ad]))]
                  for ad in maske_k}
    log(f"konum farki kaydirma sonrasi: {konum_fark}")

    kalinlik = {}                             # K4 kodlanmis videodan (asagida)

    # ---- Katman 1: temiz kare 0 x kare orani
    temiz_bolge = np.zeros((ph, pw), dtype=bool)
    for ad in OGELER:
        for km in (ref_m.get(ad), maske_k.get(ad)):
            if km is not None and km.any():
                temiz_bolge |= ndimage.binary_dilation(km, iterations=TEMIZ_GENIS)
    temiz_bolge &= ~koruma                    # C
    zemin0 = np.stack([temiz_zemin(ref0[..., k], temiz_bolge) for k in range(3)],
                      axis=-1)

    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, out / "_is" / "ref.yuv", vw, vh)
    v5_veri, _, v5_adet = yuv_ac(v5_video, out / "_is" / "v5.yuv", vw, vh)
    adet = min(ref_adet, v5_adet, len(ref_kareler))
    ref_y0 = panel_y(ref_veri, kare_bayt, 0, kutu, vw, vh).astype(np.float32)
    v5_y0 = panel_y(v5_veri, kare_bayt, 0, kutu, vw, vh).astype(np.float32)

    oran, toz_olcek, ref_kenar_oran = [], [], []
    ref_ana = ref_m["ana_sembol"]
    ke0 = kenar_enerji(ref_y0, ref_ana)
    for i in range(adet):
        ry = panel_y(ref_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        fark = ry - ref_y0
        tozsuz = fark <= TOZ_TABAN
        oran.append(float(ry[tozsuz].mean() / max(ref_y0[tozsuz].mean(), 1e-6))
                    if tozsuz.any() else 1.0)
        r_toz = float(np.clip(fark - TOZ_TABAN, 0, None).sum())
        vy = panel_y(v5_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        v_toz = float(np.clip(vy - v5_y0 - TOZ_TABAN, 0, None).sum())
        toz_olcek.append(float(np.clip(r_toz / max(v_toz, 1e-6), 0.0, 4.0)))
        ref_kenar_oran.append(kenar_enerji(ry, ref_ana) / max(ke0, 1e-6))
    ornek = []
    for i in (30, 60, 90):
        d = panel_rgb(ref_kareler, i, kutu).astype(np.float32) - ref0
        sec = luma(d) > 12
        if sec.any():
            ornek.append(d[sec].mean(axis=0))
    toz_renk = np.mean(ornek, axis=0) if ornek else np.array([255., 200., 120.])
    toz_renk = toz_renk / max(luma(toz_renk[None, None, :])[0, 0], 1e-6)

    # ---- egriler: kucuk semboller (B) ve isimler
    olcum = {ad: ref_m[ad] for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim")
             if ad in ref_m}
    ham, _ = gorunurluk_egrisi(ref_veri, kare_bayt, adet, kutu, vw, vh, olcum)
    egri = {ad: kuyruk_normalize(e) for ad, e in ham.items()}
    k0s, k1s = int(round(SONME_BASI_SN * fps)), int(round(SONME_SONU_SN * fps))
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in egri:
            e = list(egri[ad])
            for i in range(k0s, min(k1s + 1, len(e))):
                e[i] = 0.0                    # B: Katman 2 katkisi 0
            e[-1] = 1.0
            egri[ad] = e
    if "isim" in egri:
        egri["isim"][-1] = 1.0
    zaman = {ad: zamanlama(e, fps) for ad, e in egri.items()}

    # ---- D: ana sembol bulanikligi - her karede kenar enerjisi oranini esitle
    ana_m = maske_k["ana_sembol"]
    ana_yumusak = np.clip(ndimage.gaussian_filter(
        ndimage.binary_dilation(ana_m, iterations=8).astype(np.float32), 4.0), 0, 1)

    def kompozit(i, sigma):
        taban = zemin0 * oran[i]
        for ad in alfa:
            g = 1.0 if ad == "ana_sembol" else egri.get(ad, [1.0] * adet)[i]
            renk, al = boyali[ad], alfa[ad]
            if ad == "ana_sembol" and sigma > 0:
                renk = np.stack([ndimage.gaussian_filter(renk[..., k], sigma)
                                 for k in range(3)], axis=-1)
                al = ndimage.gaussian_filter(al, sigma)
            aa = (al * float(np.clip(g, 0, 1)))[..., None]
            taban = taban * (1 - aa) + renk * aa
        vy = panel_y(v5_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        toz = np.clip(vy - v5_y0 - TOZ_TABAN, 0, None) * toz_olcek[i]
        toz = toz * (~koruma)                 # C: koruma bandina toz yok
        if sigma > 0:
            # D: sembolun ustunden gecen toz da ayni olcude yumusar (yalniz ana
            # sembol cevresinde); referansta toz sembolu perdeler, keskin degil
            toz = toz * (1 - ana_yumusak) + ndimage.gaussian_filter(toz, sigma) * ana_yumusak
        return np.clip(screen(taban, toz[..., None] * toz_renk[None, None, :]),
                       0, 255)                  # C: toz EN USTTE, screen

    yeni_ke0 = None
    sigmalar, yeni_kenar_oran = [], []
    koruma_yari = koruma.reshape(ph // 2, 2, pw // 2, 2).any(axis=(1, 3))
    ham_yuv = out / "_is" / "yeni.yuv"
    with open(ham_yuv, "wb") as fh:
        for i in range(adet):
            hedef = ref_kenar_oran[i]
            if i == 0 or i == adet - 1:
                sigma = 0.0
                kare = kompozit(i, 0.0)
                if i == 0:
                    yeni_ke0 = kenar_enerji(luma(kare), ana_m)
            else:
                lo, hi, sigma, kare = 0.0, 8.0, 0.0, None
                k_lo = kompozit(i, 0.0)
                r_lo = kenar_enerji(luma(k_lo), ana_m) / max(yeni_ke0, 1e-6)
                if r_lo <= hedef + 0.02:
                    sigma, kare = 0.0, k_lo
                else:
                    for _ in range(7):
                        mid = (lo + hi) / 2
                        k_mid = kompozit(i, mid)
                        r_mid = kenar_enerji(luma(k_mid), ana_m) / max(yeni_ke0, 1e-6)
                        if r_mid > hedef:
                            lo = mid
                        else:
                            hi = mid
                        sigma, kare = mid, k_mid
            sigmalar.append(round(sigma, 3))
            yeni_kenar_oran.append(kenar_enerji(luma(kare), ana_m) / max(yeni_ke0, 1e-6))
            Y, U, V = rgb_yuv_doseme(np.rint(kare).astype(np.uint8))
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            y = blok[:vw * vh].reshape(vh, vw)
            u = blok[vw * vh:vw * vh + vw * vh // 4].reshape(vh // 2, vw // 2)
            v = blok[vw * vh + vw * vh // 4:].reshape(vh // 2, vw // 2)
            # C: koruma bandinda referansin Y/U/V baytlari birebir
            yp = y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw]
            Y = np.where(koruma, yp, Y)
            up = u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
                   kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2]
            vp = v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
                   kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2]
            U = np.where(koruma_yari, up, U)
            V = np.where(koruma_yari, vp, V)
            y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw] = Y
            u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = U
            v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = V
            blok.tofile(fh)
    log(f"D: sigma araligi {min(sigmalar)}-{max(sigmalar)} | kare 90 hedef "
        f"{ref_kenar_oran[90]:.3f} yeni {yeni_kenar_oran[90]:.3f}")

    video = out / "Aquarius_Aries_4570110641_video_V10_2.mp4"
    yuv_video_yaz(ham_yuv, video, vw, vh, fps, sure)
    kapak = out / "Aquarius_Aries_4570110641_kapak_V10_2.png"
    k0 = out / "_is" / "yeni_kare0.png"
    extract_frame(video, k0, 0)
    with Image.open(k0) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(kapak)

    # ---- KAPILAR (kodlanmis videodan olculur)
    yeni_veri, _, yeni_adet = yuv_ac(video, out / "_is" / "geri.yuv", vw, vh)
    kapilar = {}
    # K1
    k1 = {}
    for i in KAPI_KARELER:
        ry = panel_y(ref_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        yy = panel_y(yeni_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        satir = {}
        for ad in ("kucuk_burc_1", "kucuk_burc_2"):
            r = float(ry[ref_m[ad]].mean() - komsu_zemin(ry, ref_m[ad]))
            n = float(yy[maske_k[ad]].mean() - komsu_zemin(yy, maske_k[ad]))
            satir[ad] = {"referans": round(r, 2), "yeni": round(n, 2)}
        k1[str(i)] = satir
    k1_gecti = all(v["yeni"] <= 4.0 for s in k1.values() for v in s.values()
                   if v["referans"] <= 4.0)
    k1_ref_gorunur = [i for i, s in k1.items() if any(v["referans"] > 4.0
                                                     for v in s.values())]
    kapilar["K1"] = {"esik": 4.0, "kareler": k1, "gecti": bool(k1_gecti),
                     "referansin_gorunur_oldugu_kareler": k1_ref_gorunur}
    # K2
    yy0 = panel_y(yeni_veri, kare_bayt, 0, kutu, vw, vh)
    kapilar["K2"] = {"esik": 0,
                     "referans": int((ref_y0[ref_ana] < 40).sum()),
                     "yeni": int((yy0[ana_m] < 40).sum())}
    kapilar["K2"]["gecti"] = kapilar["K2"]["yeni"] == 0
    # K3
    y90r = panel_y(ref_veri, kare_bayt, 90, kutu, vw, vh)
    y90n = panel_y(yeni_veri, kare_bayt, 90, kutu, vw, vh)
    r3 = kenar_enerji(y90r, ref_ana) / max(kenar_enerji(ref_y0, ref_ana), 1e-6)
    n3 = kenar_enerji(y90n, ana_m) / max(kenar_enerji(yy0, ana_m), 1e-6)
    kapilar["K3"] = {"tolerans": 0.10, "referans": round(r3, 3), "yeni": round(n3, 3),
                     "gecti": bool(abs(r3 - n3) <= 0.10)}
    # K4 (V10.2/B): ayni yontem -- Y, bolgede tepe %50 esigi, medyan kalinlik
    for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim"):
        if ad in maske_k and ad in ref_m:
            rb_ = ndimage.binary_dilation(ref_m[ad], iterations=4)
            nb_ = ndimage.binary_dilation(maske_k[ad], iterations=4)
            rk_, re_ = esikli_kalinlik(ref_y0, rb_)
            nk_, ne_ = esikli_kalinlik(yy0.astype(np.float32), nb_)
            kalinlik[ad] = {"referans": rk_, "yeni": nk_,
                            "esik_ref": re_, "esik_yeni": ne_}
    log(f"vurus kalinligi (esikli): {kalinlik}")
    k4_gecti = all(v["referans"] is not None and v["yeni"] is not None
                   and abs(v["referans"] - v["yeni"]) <= K4_TOL for v in kalinlik.values())
    kapilar["K4"] = {"tolerans_px": K4_TOL, "yontem": "Y >= 0.5*tepe, medyan 2*dt",
                     "kalinlik": kalinlik, "gecti": bool(k4_gecti)}
    # K5
    dis_mae, _ = yuv_dis_mae(ref_veri, yeni_veri, kare_bayt, kutu, vw, vh)
    son = out / "_is" / "yeni_son.png"
    extract_frame(video, son, max(sure - 1.0 / fps, 0))
    with Image.open(son) as im:
        son_a = np.asarray(im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS))
    kapak_a = np.asarray(Image.open(kapak).convert("RGB"))
    son_mae = mae(kapak_a, son_a)
    kapilar["K5"] = {"panel_disi_y_mae": round(dis_mae, 4), "esik": 1.0,
                     "kapak_son_kare_mae": round(son_mae, 3),
                     "gecti": bool(dis_mae < 1.0 and son_mae < 2.0)}
    # V10.1 OCR kapisi (kare 0, isim bolgesi)
    ocr_yeni = isim_ocr(yy0, maske_k["isim"], out / "_is" / "ocr_yeni.png")
    ocr_ref = isim_ocr(ref_y0, ref_m["isim"], out / "_is" / "ocr_ref.png")
    harf_yeni = len(ocr_yeni.replace(" ", ""))
    harf_ref = len(ocr_ref.replace(" ", ""))
    beklenen = ("AQUARIUS", "ARIES")
    ocr_gecti = all(b in ocr_yeni.split() for b in beklenen)
    kapilar["OCR"] = {"beklenen": list(beklenen), "referans": ocr_ref,
                      "referans_harf": harf_ref, "yeni": ocr_yeni,
                      "yeni_harf": harf_yeni, "gecti": bool(ocr_gecti)}
    # V10.2/C halka kapisi: halka bandinda yeni vs referans Y/U/V MAE < 0.5
    halka_yari = halka_bant.reshape(ph // 2, 2, pw // 2, 2).any(axis=(1, 3))
    hk = {}
    for i in (0, 40, 90, adet - 1):
        ry_ = panel_y(ref_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        ny_ = panel_y(yeni_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        ru, rv = panel_uv(ref_veri, kare_bayt, i, kutu, vw, vh)
        nu, nv = panel_uv(yeni_veri, kare_bayt, i, kutu, vw, vh)
        hk[str(i)] = {"Y": round(float(np.abs(ry_ - ny_)[halka_bant].mean()), 4),
                      "U": round(float(np.abs(ru - nu)[halka_bant].mean()), 4),
                      "V": round(float(np.abs(rv - nv)[halka_bant].mean()), 4)}
    en_cok_h = max(v for k in hk.values() for v in k.values())
    kapilar["HALKA"] = {"esik": 0.5, "kareler": hk, "en_cok": en_cok_h,
                        "bant_px": int(halka_bant.sum()),
                        "gecti": bool(en_cok_h < 0.5)}
    # V10.1 sapma kapisi: K1-K5 V10 degerlerinden sapmasin
    sapma = {"gecti": True}
    if a.onceki:
        onc = json.loads(pathlib.Path(a.onceki).read_text(encoding="utf-8"))
        tol = {"K1": 0.5, "K2": 0, "K3": 0.02, "K5_dis": 0.05, "K5_kapak": 0.2}
        sapma["tolerans"] = tol
        farklar = {}
        for i, satir in k1.items():
            for ad, v in satir.items():
                o = onc["K1"]["kareler"][i][ad]["yeni"]
                # yalniz K1'in sinirladigi kareler (referans <= 4)
                if v["referans"] <= 4.0:
                    farklar[f"K1_{i}_{ad}"] = [o, v["yeni"], abs(o - v["yeni"]) <= tol["K1"]]
        farklar["K2"] = [onc["K2"]["yeni"], kapilar["K2"]["yeni"],
                         onc["K2"]["yeni"] == kapilar["K2"]["yeni"]]
        farklar["K3"] = [onc["K3"]["yeni"], kapilar["K3"]["yeni"],
                         abs(onc["K3"]["yeni"] - kapilar["K3"]["yeni"]) <= tol["K3"]]
        farklar["K5_dis"] = [onc["K5"]["panel_disi_y_mae"], kapilar["K5"]["panel_disi_y_mae"],
                             abs(onc["K5"]["panel_disi_y_mae"]
                                 - kapilar["K5"]["panel_disi_y_mae"]) <= tol["K5_dis"]]
        farklar["K5_kapak"] = [onc["K5"]["kapak_son_kare_mae"], kapilar["K5"]["kapak_son_kare_mae"],
                               abs(onc["K5"]["kapak_son_kare_mae"]
                                   - kapilar["K5"]["kapak_son_kare_mae"]) <= tol["K5_kapak"]]
        sapma["farklar"] = farklar
        sapma["gecti"] = bool(all(v[2] for v in farklar.values()))
    kapilar["SAPMA"] = sapma
    hepsi = all(kapilar[k]["gecti"] for k in ("K1", "K2", "K3", "K4", "K5",
                                               "OCR", "HALKA", "SAPMA"))
    kapilar["HEPSI_GECTI"] = bool(hepsi)
    kapilar["ek"] = {"konum_farki": konum_fark, "kaydirma": kaydirma,
                     "kalinlik_genisletmesi_px": genisletme,
                     "poster": poster_not, "sinir_kutulari":
                     {k: kutu_of(v) for k, v in maske_k.items()},
                     "sonme_kareleri": [k0s, k1s], "sigma_araligi":
                     [min(sigmalar), max(sigmalar)],
                     "kenar_orani_ref": [round(x, 3) for x in ref_kenar_oran],
                     "kenar_orani_yeni": [round(x, 3) for x in yeni_kenar_oran]}
    (out / "KAPILAR.json").write_text(json.dumps(kapilar, ensure_ascii=False,
                                                 indent=1, default=str),
                                      encoding="utf-8")
    log(f"KAPILAR: K1 {kapilar['K1']['gecti']} K2 {kapilar['K2']['gecti']} "
        f"K3 {kapilar['K3']['gecti']} K4 {kapilar['K4']['gecti']} "
        f"K5 {kapilar['K5']['gecti']} OCR {kapilar['OCR']['gecti']} "
        f"HALKA {kapilar['HALKA']['gecti']} SAPMA {kapilar['SAPMA']['gecti']} -> {hepsi}")
    log(f"OCR ref '{ocr_ref}' yeni '{ocr_yeni}' | HALKA {hk}")

    # ---- gorseller
    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    satir = []
    for ad, yol in [("REFERANS  Aquarius + Gemini", ref_video),
                    ("YENI V10.2  Aquarius + Aries", video)]:
        g, kl = [], out / "_is" / "k8" / ad.split()[0]
        kl.mkdir(parents=True, exist_ok=True)
        for i, z in enumerate(zamanlar):
            zz = min(z, max(sure - 1.0 / fps, 0))
            pp = kl / f"{i}.png"
            extract_frame(yol, pp, zz)
            g.append((f"{zz:.2f} sn", Image.open(pp).convert("RGB")))
        satir.append((ad, g))
    karsilastirma(satir, out / "KARE_KARSILASTIRMA_V10_2.jpg")
    # ---- KUCUK_KIRPINTI (4 dosya, 1200 px, <= 250 KB)
    kk = out / "_is" / "kk"
    kk.mkdir(exist_ok=True)
    kare_png = {}
    for ad, yol in (("ref", ref_video), ("yeni", video)):
        for i in (0, 40, 90):
            pp = kk / f"{ad}_{i}.png"
            extract_frame(yol, pp, min(i / fps, max(sure - 1.0 / fps, 0)))
            kare_png[(ad, i)] = pp
    U0, S0 = kutu["ust"], kutu["sol"]
    kb = [kutu_of(maske_k[ad]) for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim")
          if ad in maske_k]
    kb += [kutu_of(ref_m[ad]) for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim")
           if ad in ref_m]
    bant = (S0, U0 + max(min(b[0] for b in kb) - 10, 0),
            S0 + pw, U0 + min(max(b[1] for b in kb) + 10, ph))
    hb = kutu_of(halka_bant)
    ab = kutu_of(ana_m)
    ana_kes = (S0 + max(min(hb[2], ab[2]) - 6, 0), U0 + max(min(hb[0], ab[0]) - 6, 0),
               S0 + min(max(hb[3], ab[3]) + 7, pw), U0 + min(max(hb[1], ab[1]) + 7, ph))
    panel_kes = (S0, U0, S0 + pw, U0 + ph)
    kirp = {}
    for ad, i, kes in (("1_kare0_isim_kucuk_bandi", 0, bant),
                       ("2_kare0_ana_halka", 0, ana_kes),
                       ("3_kare90_panel", 90, panel_kes),
                       ("4_kare40_panel", 40, panel_kes)):
        yol = out / "KUCUK_KIRPINTI" / f"{ad}.jpg"
        kirp[ad] = kucuk_kirpinti(kare_png[("ref", i)], kare_png[("yeni", i)],
                                  kes, yol)
    log(f"KUCUK_KIRPINTI bayt: {kirp}")
    print(json.dumps({k: kapilar[k]["gecti"] for k in
                      ("K1", "K2", "K3", "K4", "K5", "OCR", "HALKA", "SAPMA")}))
    return 0 if hepsi else 3


if __name__ == "__main__":
    sys.exit(main())
