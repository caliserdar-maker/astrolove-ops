#!/usr/bin/env python3
"""POD sablon V10 - V9.2 katman yapisi + dort duzeltme + sayisal kapilar.

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
from pod_sablon_v8 import (gorunurluk_egrisi, katman_maskeleri,  # noqa: E402
                           kuyruk_normalize, panel_y, temiz_zemin, zamanlama)
from pod_sablon_v9 import (TEMIZ_GENIS, gradient_lut, histogram_esle,  # noqa: E402
                           isim_maskesi, luma, panel_rgb)
from pod_sablon_v9_1 import (cekirdekten_yay, kaydir, kapsam_alfa,  # noqa: E402
                             merkez, parlama_esitle)

TOZ_TABAN = 3.0
DELIK_EN_COK = 40
RAMPA = 1.0
SONME_BASI_SN, SONME_SONU_SN = 0.57, 3.50
KAPI_KARELER = (60, 90, 120)
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
    a = ap.parse_args()
    veri = pathlib.Path(a.veri)
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    (out / "CIFT_KIRPINTI").mkdir(exist_ok=True)

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

    # ---- A: cift maskeleri POSTERDEN
    poster_kapak, poster_not = poster_kapak_yap(poster_yol, kutu_kapak)
    Image.fromarray(poster_kapak).save(out / "_is" / "poster_sanal_kapak.png")
    cift_k, cift_not, _ = katman_maskeleri(poster_kapak)
    cift_isim_k, cift_isim_not = isim_maskesi(
        poster_kapak, cift_k["ana_sembol"],
        (cift_k.get("kucuk_burc_1"), cift_k.get("kucuk_burc_2")))
    cift_m = {ad: kapat(maske_panele(m, kutu_kapak, pw, ph))
              for ad, m in cift_k.items() if m.any()}
    cift_m["isim"] = kapat(maske_panele(cift_isim_k, kutu_kapak, pw, ph))
    # B: kucuk semboller isimden kesin ayri
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in cift_m:
            cift_m["isim"] &= ~ndimage.binary_dilation(cift_m[ad], iterations=2)
    poster_panel = np.asarray(Image.fromarray(poster_kapak).crop(
        (kutu_kapak["sol"], kutu_kapak["ust"], kutu_kapak["sag"] + 1,
         kutu_kapak["alt"] + 1)).resize((pw, ph), Image.Resampling.LANCZOS),
        dtype=np.uint8).astype(np.float32)

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
        kay = kaynak_of.get(ad)
        if m is None or not m.any() or kay is None or not kay.any():
            continue
        lut, ref_l = gradient_lut(ref0, kay)
        eslenen = histogram_esle(poster_l[m], ref_l)
        idx = np.clip(np.rint(eslenen), 0, 255).astype(np.int32)
        renk = np.zeros((ph, pw, 3), dtype=np.float32)
        renk[m] = lut[idx]
        renk = cekirdekten_yay(renk, m)
        al = kapsam_alfa(m, rampa=RAMPA)
        if ad in ("kucuk_burc_1", "kucuk_burc_2"):
            renk, _ = parlama_esitle(renk, al, ref_l)
        dy, dx = kaydirma.get(ad, (0, 0))
        alfa[ad] = kaydir(al, dy, dx)
        boyali[ad] = kaydir(renk, dy, dx)
        maske_k[ad] = kaydir(m, dy, dx)
    konum_fark = {ad: [round(x - y, 1) for x, y in zip(merkez(maske_k[ad]),
                                                        merkez(ref_m[ad]))]
                  for ad in maske_k}
    log(f"konum farki kaydirma sonrasi: {konum_fark}")

    # ---- K4: vurus kalinligi
    kalinlik = {}
    for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim"):
        if ad in maske_k and ad in ref_m:
            kalinlik[ad] = {"referans": vurus_kalinligi(ref_m[ad]),
                            "yeni": vurus_kalinligi(maske_k[ad])}
    log(f"vurus kalinligi: {kalinlik}")

    # ---- Katman 1: temiz kare 0 x kare orani
    temiz_bolge = np.zeros((ph, pw), dtype=bool)
    for ad in OGELER:
        for km in (ref_m.get(ad), maske_k.get(ad)):
            if km is not None and km.any():
                temiz_bolge |= ndimage.binary_dilation(km, iterations=TEMIZ_GENIS)
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
        return np.clip(screen(taban, toz[..., None] * toz_renk[None, None, :]),
                       0, 255)                  # C: toz EN USTTE, screen

    yeni_ke0 = None
    sigmalar, yeni_kenar_oran = [], []
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
                lo, hi, sigma, kare = 0.0, 6.0, 0.0, None
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
            y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw] = Y
            u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = U
            v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = V
            blok.tofile(fh)
    log(f"D: sigma araligi {min(sigmalar)}-{max(sigmalar)} | kare 90 hedef "
        f"{ref_kenar_oran[90]:.3f} yeni {yeni_kenar_oran[90]:.3f}")

    video = out / "Aquarius_Aries_4570110641_video_V10.mp4"
    yuv_video_yaz(ham_yuv, video, vw, vh, fps, sure)
    kapak = out / "Aquarius_Aries_4570110641_kapak_V10.png"
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
    # K4
    k4_gecti = all(v["referans"] is not None and v["yeni"] is not None
                   and abs(v["referans"] - v["yeni"]) <= 1.0 for v in kalinlik.values())
    kapilar["K4"] = {"tolerans_px": 1.0, "kalinlik": kalinlik, "gecti": bool(k4_gecti)}
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
    hepsi = all(kapilar[k]["gecti"] for k in ("K1", "K2", "K3", "K4", "K5"))
    kapilar["HEPSI_GECTI"] = bool(hepsi)
    kapilar["ek"] = {"konum_farki": konum_fark, "kaydirma": kaydirma,
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
        f"K5 {kapilar['K5']['gecti']} -> {hepsi}")

    # ---- gorseller
    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    satir = []
    for ad, yol in [("REFERANS  Aquarius + Gemini", ref_video),
                    ("YENI V10  Aquarius + Aries", video)]:
        g, kl = [], out / "_is" / "k8" / ad.split()[0]
        kl.mkdir(parents=True, exist_ok=True)
        for i, z in enumerate(zamanlar):
            zz = min(z, max(sure - 1.0 / fps, 0))
            pp = kl / f"{i}.png"
            extract_frame(yol, pp, zz)
            g.append((f"{zz:.2f} sn", Image.open(pp).convert("RGB")))
        satir.append((ad, g))
    karsilastirma(satir, out / "KARE_KARSILASTIRMA_V10.jpg")
    for i, z in enumerate(zamanlar):
        zz = min(z, max(sure - 1.0 / fps, 0))
        cift = []
        for ad in ("REFERANS", "YENI"):
            with Image.open(out / "_is" / "k8" / ad / f"{i}.png") as im:
                arr = np.asarray(im.convert("RGB"), dtype=np.uint8)
            pan = Image.fromarray(arr[kutu["ust"]:kutu["alt"] + 1,
                                      kutu["sol"]:kutu["sag"] + 1])
            cift.append((ad, pan.resize((pan.width * 2, pan.height * 2),
                                        Image.Resampling.LANCZOS)))
        karsilastirma([(f"{zz:.2f} sn", cift)],
                      out / "CIFT_KIRPINTI" / f"{i}_{zz:.2f}sn.jpg", hucre=730)
    print(json.dumps({k: kapilar[k]["gecti"] for k in ("K1", "K2", "K3", "K4", "K5")}))
    return 0 if hepsi else 3


if __name__ == "__main__":
    sys.exit(main())
