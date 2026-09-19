#!/usr/bin/env python3
"""POD sablon V8 - referansin katman zamanlamasini V5 videosuna uygular.

Temel: V5 Aquarius+Aries videosu (tozlar iyi, leke yok). Referansta ana sembol
ve iki kucuk burc sembolu toza karisip kaybolur, sonra geri gelir; daire
cizgisi hep gorunur, cift adi ve alt satir degismez.

ADIM 1  Referans videodan katman gorunurlugu (kenar enerjisiyle, parlaklikla
        DEGIL; toz gecisi sembol sanilmasin).
ADIM 2  Ayni 3 maske V5 videosunun 0. karesinden cikarilir; her karede
        maske ici = V5(t)*g(t) + (temiz zemin + o karenin tozu)*(1-g(t)).

Yerel calisir, Etsy cagrisi yoktur.
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, cift_hizala, karsilastirma,  # noqa: E402
                           kutu_olcekle, panel_kutusu, yuv_ac, yuv_video_yaz)
from pod_sablon_v5 import kapak_ac, kutu_boyut  # noqa: E402
from pod_sablon_v6 import BOLGE, maske_panele  # noqa: E402

KALINLIK_ESIK = 6.0     # ana sembol: ortalama yari kalinlik (px, kapak uzayi)
EN_AZ_ALAN = 400        # bilesen alt siniri (kapak uzayi px)
KENAR_YUZDE = 70        # kenar maskesi: gradyanin ust yuzdeligi
YUMUSATMA = 1.0         # maske kenari yumusatma sigmasi (panel uzayi px)
# Referans olcumu (kare kare bakilarak dogrulandi): ana sembol HIC kaybolmuyor,
# uzerinden toz gecerken yerinde duruyor. Bu yuzden yalniz kucuk burc
# sembolleri soldurulur; ana sembol ve daire cizgisi dokunulmadan kalir.
SOLAN_KATMANLAR = ("kucuk_burc_1", "kucuk_burc_2")


def _comps(maske, en_az=EN_AZ_ALAN):
    et, _ = ndimage.label(maske, structure=np.ones((3, 3), np.uint8))
    cikti = []
    for i, dil in enumerate(ndimage.find_objects(et), start=1):
        if dil is None:
            continue
        c = et[dil] == i
        alan = int(c.sum())
        if alan < en_az:
            continue
        dt = ndimage.distance_transform_edt(np.pad(c, 2))
        cikti.append({"no": i, "alan": alan, "dilim": dil, "etiket": et,
                      "kalinlik": float(dt[np.pad(c, 2)].mean()),
                      "y0": dil[0].start, "y1": dil[0].stop,
                      "x0": dil[1].start, "x1": dil[1].stop})
    return cikti


def _maske_of(comp, sekil):
    m = np.zeros(sekil, dtype=bool)
    m[comp["dilim"]] = comp["etiket"][comp["dilim"]] == comp["no"]
    return m


def katman_maskeleri(kapak_a):
    """Kapaktan ana sembol ve iki kucuk burc sembolu maskesi.

    - Ana sembol: 'ana' bolgesinde kalin (ort yari kalinlik >= esik) bilesenler.
      Daire cizgisi ve yildizlar ince oldugu icin disarida kalir (dokunulmaz).
    - Kucuk burc sembolleri: cift adi bandinin USTUNDEKI bilesenler; yazi
      satirindan, bilesen ustlerindeki en buyuk bosluga gore ayrilir. Sol/sag
      olarak iki gruba bolunur.
    """
    altin = artwork_mask(kapak_a)
    sekil = altin.shape
    notlar = {}

    u, al, s, sa = BOLGE["ana"]
    bolge = np.zeros(sekil, dtype=bool)
    bolge[u:al, s:sa] = True
    ana_c = _comps(altin & bolge)
    kalin = [c for c in ana_c if c["kalinlik"] >= KALINLIK_ESIK]
    ana = np.zeros(sekil, dtype=bool)
    for c in kalin:
        ana |= _maske_of(c, sekil)
    notlar["ana_bilesen"] = [{"alan": c["alan"], "kalinlik": round(c["kalinlik"], 1)}
                             for c in kalin]
    notlar["ana_disi_ince"] = [round(c["kalinlik"], 1)
                               for c in ana_c if c["kalinlik"] < KALINLIK_ESIK]

    # kucuk burc sembolleri: cift adi bolgesi + ustundeki tampon
    u2, al2, s2, sa2 = BOLGE["cift_adi"]
    bolge2 = np.zeros(sekil, dtype=bool)
    bolge2[u2 - 200:al2, s2:sa2] = True
    # ana sembole ait kalin bilesenler haric
    yerel = (altin & bolge2) & ~ana
    comps = sorted(_comps(yerel), key=lambda c: c["y0"])
    kucuk1 = np.zeros(sekil, dtype=bool)
    kucuk2 = np.zeros(sekil, dtype=bool)
    if comps:
        ustler = [c["y0"] for c in comps]
        bosluk = [(ustler[i + 1] - ustler[i], i) for i in range(len(ustler) - 1)]
        kesim = None
        if bosluk:
            en_buyuk, idx = max(bosluk)
            if en_buyuk >= 40:
                kesim = idx
        glifler = comps[:kesim + 1] if kesim is not None else []
        notlar["glif_sayisi"] = len(glifler)
        notlar["glif_kutulari"] = [{"y": [c["y0"], c["y1"]], "x": [c["x0"], c["x1"]],
                                    "alan": c["alan"]} for c in glifler]
        notlar["yazi_ust"] = comps[kesim + 1]["y0"] if kesim is not None else None
        if glifler:
            orta = sum((c["x0"] + c["x1"]) / 2 for c in glifler) / len(glifler)
            for c in glifler:
                m = _maske_of(c, sekil)
                if (c["x0"] + c["x1"]) / 2 <= orta:
                    kucuk1 |= m
                else:
                    kucuk2 |= m
    return {"ana_sembol": ana, "kucuk_burc_1": kucuk1, "kucuk_burc_2": kucuk2}, \
        notlar, altin


def panel_y(veri, kare_bayt, i, kutu, w, h):
    blok = veri[i * kare_bayt:i * kare_bayt + w * h]
    y = blok.reshape(h, w)
    ph = kutu["alt"] - kutu["ust"] + 1
    pw = kutu["sag"] - kutu["sol"] + 1
    return y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw]


def gradyan(y):
    gy, gx = np.gradient(y.astype(np.float32))
    return np.hypot(gx, gy)


def gorunurluk_egrisi(veri, kare_bayt, adet, kutu, w, h, maskeler):
    """Kare kare sembol gorunurlugu: kenar enerjisi (parlaklik DEGIL).

    Kenar maskesi 0. kareden sabitlenir; boylece maskenin icinden gecen toz
    sembol sanilmaz. Taban, maske ici ama kenar disi bolgedeki gradyanin
    medyanidir (tozun ve gurultunun payi).
    """
    y0 = panel_y(veri, kare_bayt, 0, kutu, w, h)
    g0 = gradyan(y0)
    kenar, taban_m, pay0 = {}, {}, {}
    for ad, m in maskeler.items():
        if not m.any():
            continue
        esik = np.percentile(g0[m], KENAR_YUZDE)
        k = m & (g0 >= esik)
        t = m & ~ndimage.binary_dilation(k, iterations=2)
        kenar[ad] = k
        taban_m[ad] = t if t.any() else m
        pay0[ad] = float(g0[k].mean() - np.median(g0[taban_m[ad]]))
    egri = {ad: [] for ad in kenar}
    for i in range(adet):
        gi = gradyan(panel_y(veri, kare_bayt, i, kutu, w, h))
        for ad in kenar:
            v = float(gi[kenar[ad]].mean() - np.median(gi[taban_m[ad]]))
            egri[ad].append(round(float(np.clip(v / max(pay0[ad], 1e-6), 0.0, 1.5)), 4))
    return egri, kenar


def kuyruk_normalize(egri):
    """Egriyi, geri donusteki yayla (plato) 1.0 olacak sekilde olcekler.

    Kenar enerjisi olcumu geri donusu oldugundan dusuk gosteriyor: referansta
    3.94 sn'de semboller gozle TAM gorunurken olcum 0.45-0.62 veriyor. Dip
    sonrasi bolum [dip..plato] araligindan [dip..1.0] araligina tasinir;
    kaybolma bolumu aynen kalir.
    """
    g = list(egri)
    dip_i = int(np.argmin(g))
    dip = g[dip_i]
    plato = max(g[dip_i:]) if dip_i < len(g) else 1.0
    if plato <= dip + 1e-6:
        return [round(float(np.clip(x, 0, 1)), 4) for x in g]
    olcek = (1.0 - dip) / (plato - dip)
    cikti = []
    for i, x in enumerate(g):
        v = x if i < dip_i else dip + (x - dip) * olcek
        cikti.append(round(float(np.clip(v, 0.0, 1.0)), 4))
    return cikti


def zamanlama(egri, fps, yok_esik=0.15, tam_esik=0.85):
    g = egri
    n = len(g)
    basla = next((i for i, x in enumerate(g) if x < tam_esik), None)
    yok = [i for i, x in enumerate(g) if x <= yok_esik]
    geri = None
    if yok:
        for i in range(yok[-1], n):
            if g[i] >= tam_esik:
                geri = i
                break
    elif basla is not None:
        dip = int(np.argmin(g))
        for i in range(dip, n):
            if g[i] >= tam_esik:
                geri = i
                break
    return {"sonme_basi_kare": basla,
            "sonme_basi_sn": round(basla / fps, 2) if basla is not None else None,
            "tam_yok_ilk_kare": yok[0] if yok else None,
            "tam_yok_ilk_sn": round(yok[0] / fps, 2) if yok else None,
            "tam_yok_son_kare": yok[-1] if yok else None,
            "tam_yok_son_sn": round(yok[-1] / fps, 2) if yok else None,
            "geri_kare": geri,
            "geri_sn": round(geri / fps, 2) if geri is not None else None,
            "en_dusuk": round(min(g), 3), "en_dusuk_kare": int(np.argmin(g))}


def temiz_zemin(duzlem, maske_altin, tekrar=3, sigma=9):
    """Maske icindeki altin pikselleri komsu zeminden doldurur (normalize
    konvolusyon). Sembolsuz lacivert zemin uretir."""
    v = duzlem.astype(np.float32).copy()
    w = (~maske_altin).astype(np.float32)
    v[maske_altin] = 0.0
    for _ in range(tekrar):
        vs = ndimage.gaussian_filter(v * w, sigma=sigma, mode="nearest")
        ws = ndimage.gaussian_filter(w, sigma=sigma, mode="nearest")
        dolu = vs / np.maximum(ws, 1e-6)
        v = np.where(maske_altin, dolu, duzlem.astype(np.float32))
        w = np.ones_like(w)
        w[maske_altin] = 0.0
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="_veri/v8")
    ap.add_argument("--out", required=True)
    ap.add_argument("--toz-esik", type=float, default=8.0)
    ap.add_argument("--sadece-olcum", action="store_true")
    a = ap.parse_args()
    veri = pathlib.Path(a.veri)
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)

    ref_video = veri / "referans_video.mp4"
    v5_video = veri / "v5_ornek_video.mp4"
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
    log(f"panel kapakta {kutu_kapak} -> videoda {kutu} ({pw}x{ph}), "
        f"{vw}x{vh} {sure:.2f} sn {fps} fps")

    # ---- ADIM 1: referans katman egrileri
    ref_maske_k, ref_not, _ = katman_maskeleri(ref_kapak_a)
    ref_maske = {ad: maske_panele(m, kutu_kapak, pw, ph)
                 for ad, m in ref_maske_k.items() if m.any()}
    log(f"referans maskeler: { {k: int(v.sum()) for k, v in ref_maske.items()} }")
    log(f"referans not: {json.dumps(ref_not, ensure_ascii=False)[:400]}")
    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, out / "_is" / "ref.yuv", vw, vh)
    ham_egri, _ = gorunurluk_egrisi(ref_veri, kare_bayt, ref_adet, kutu, vw, vh,
                                    ref_maske)
    egri = {ad: kuyruk_normalize(e) for ad, e in ham_egri.items()}
    zaman = {ad: zamanlama(e, fps) for ad, e in egri.items()}
    for ad, z in zaman.items():
        log(f"REF {ad}: sonme {z['sonme_basi_sn']} sn | tam yok "
            f"{z['tam_yok_ilk_sn']}-{z['tam_yok_son_sn']} sn | geri "
            f"{z['geri_sn']} sn | en dusuk {z['en_dusuk']}")
    with (out / "ZAMANLAMA.csv").open("w", newline="", encoding="utf-8") as fh:
        yz = csv.writer(fh)
        yz.writerow(["kare", "sn"] + [f"{ad}" for ad in egri]
                    + [f"ham_{ad}" for ad in ham_egri])
        for i in range(ref_adet):
            yz.writerow([i, round(i / fps, 3)] + [egri[ad][i] for ad in egri]
                        + [ham_egri[ad][i] for ad in ham_egri])
    (out / "ZAMANLAMA_OZET.json").write_text(
        json.dumps({"zamanlama": zaman, "maske_notu": ref_not},
                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if a.sadece_olcum:
        return 0

    # ---- ADIM 2: V5 videosuna uygulama
    v5_veri, _, v5_adet = yuv_ac(v5_video, out / "_is" / "v5.yuv", vw, vh)
    adet = min(ref_adet, v5_adet)
    kare0 = out / "_is" / "v5_kare0.png"
    extract_frame(v5_video, kare0, 0)
    with Image.open(kare0) as im:
        v5_kapak_a = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    v5_maske_k, v5_not, v5_altin_k = katman_maskeleri(v5_kapak_a)
    v5_maske = {ad: maske_panele(m, kutu_kapak, pw, ph)
                for ad, m in v5_maske_k.items() if m.any()}
    v5_altin = maske_panele(v5_altin_k, kutu_kapak, pw, ph)
    log(f"V5 maskeler: { {k: int(v.sum()) for k, v in v5_maske.items()} }")
    log(f"V5 not: {json.dumps(v5_not, ensure_ascii=False)[:400]}")

    ortak = [ad for ad in ref_maske if ad in v5_maske and ad in SOLAN_KATMANLAR]
    log(f"soldurulacak katmanlar: {ortak} | dokunulmayanlar: "
        f"{[ad for ad in v5_maske if ad not in ortak]}")
    if not ortak:
        raise SystemExit("HATA: ortak katman yok -> DUR")
    # alfa: yumusak kenarli maske (2-3 px)
    alfa = np.zeros((ph, pw), dtype=np.float32)
    for ad in ortak:
        alfa = np.maximum(alfa, ndimage.gaussian_filter(
            v5_maske[ad].astype(np.float32), sigma=YUMUSATMA))
    alfa = np.clip(alfa / max(alfa.max(), 1e-6), 0.0, 1.0)
    # katman basina alfa (gorunurluk katman basina farkli)
    alfa_kat = {ad: np.clip(ndimage.gaussian_filter(
        v5_maske[ad].astype(np.float32), sigma=YUMUSATMA), 0.0, 1.0)
        for ad in ortak}

    # temiz zemin: 0. karenin panel duzlemlerinde altin silinmis hali
    blok0 = v5_veri[0:kare_bayt]
    y0 = blok0[:vw * vh].reshape(vh, vw)[kutu["ust"]:kutu["ust"] + ph,
                                          kutu["sol"]:kutu["sol"] + pw]
    u0 = blok0[vw * vh:vw * vh + vw * vh // 4].reshape(vh // 2, vw // 2)[
        kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
        kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2]
    v0 = blok0[vw * vh + vw * vh // 4:].reshape(vh // 2, vw // 2)[
        kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
        kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2]
    dolgu = np.zeros((ph, pw), dtype=bool)
    for ad in ortak:
        dolgu |= ndimage.binary_dilation(v5_maske[ad], iterations=3)
    # delik = genisletilmis katman maskesi; normalize konvolusyon disaridaki
    # lacivert zeminden doldurur (sembol silinir, zemin kalir)
    zemin_y = temiz_zemin(y0, dolgu)
    zemin_u = temiz_zemin(u0, dolgu[::2, ::2])
    zemin_v = temiz_zemin(v0, dolgu[::2, ::2])
    y0f = y0.astype(np.float32)

    ham = out / "_is" / "yeni.yuv"
    with open(ham, "wb") as fh:
        for i in range(adet):
            blok = v5_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            y = blok[:vw * vh].reshape(vh, vw)
            u = blok[vw * vh:vw * vh + vw * vh // 4].reshape(vh // 2, vw // 2)
            v = blok[vw * vh + vw * vh // 4:].reshape(vh // 2, vw // 2)
            py = y[kutu["ust"]:kutu["ust"] + ph,
                   kutu["sol"]:kutu["sol"] + pw].astype(np.float32)
            pu = u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
                   kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2].astype(np.float32)
            pv = v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
                   kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2].astype(np.float32)
            # toz: 0. kareye gore POZITIF fark (parlayan parcaciklar)
            toz = np.clip(py - y0f, 0.0, None)
            toz_agirlik = np.clip(toz / max(a.toz_esik, 1e-6), 0.0, 1.0)
            b = np.zeros((ph, pw), dtype=np.float32)
            for ad in ortak:
                g = egri[ad][i] if i < len(egri[ad]) else 1.0
                b = np.maximum(b, alfa_kat[ad] * (1.0 - float(np.clip(g, 0, 1))))
            b *= (1.0 - toz_agirlik)          # toz oldugu yerde dokunma
            b_uv = b[::2, ::2]
            py = py * (1.0 - b) + zemin_y * b
            pu = pu * (1.0 - b_uv) + zemin_u * b_uv
            pv = pv * (1.0 - b_uv) + zemin_v * b_uv
            y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw] = \
                np.rint(np.clip(py, 16, 235)).astype(np.uint8)
            u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = \
                np.rint(np.clip(pu, 16, 240)).astype(np.uint8)
            v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = \
                np.rint(np.clip(pv, 16, 240)).astype(np.uint8)
            blok.tofile(fh)
    yeni_video = out / "Aquarius_Aries_4570110641_video_V8.mp4"
    yuv_video_yaz(ham, yeni_video, vw, vh, fps, sure)
    kapak_yol = out / "Aquarius_Aries_4570110641_kapak_V8.png"
    k0 = out / "_is" / "yeni_kare0.png"
    extract_frame(yeni_video, k0, 0)
    with Image.open(k0) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(kapak_yol)

    # ---- gorsel
    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    ref_g, yeni_g = [], []
    (out / "_is" / "r8").mkdir(exist_ok=True)
    (out / "_is" / "y8").mkdir(exist_ok=True)
    for i, z in enumerate(zamanlar):
        zz = min(z, max(sure - 1.0 / fps, 0))
        rp = out / "_is" / "r8" / f"{i}.png"
        yp = out / "_is" / "y8" / f"{i}.png"
        extract_frame(ref_video, rp, zz)
        extract_frame(yeni_video, yp, zz)
        ref_g.append((f"{zz:.2f} sn", Image.open(rp).convert("RGB")))
        yeni_g.append((f"{zz:.2f} sn", Image.open(yp).convert("RGB")))
    boyut = karsilastirma([("REFERANS  Aquarius + Gemini  4570112095", ref_g),
                           ("YENI V8  Aquarius + Aries  4570110641", yeni_g)],
                          out / "KARE_KARSILASTIRMA_V8.jpg")
    log(f"KARE_KARSILASTIRMA_V8.jpg {boyut[0]}x{boyut[1]}")

    # yeni videonun kendi egrisi (kontrol)
    yeni_veri, _, yeni_adet = yuv_ac(yeni_video, out / "_is" / "yeni_geri.yuv",
                                     vw, vh)
    yeni_egri, _ = gorunurluk_egrisi(yeni_veri, kare_bayt,
                                     min(adet, yeni_adet), kutu, vw, vh,
                                     {ad: v5_maske[ad] for ad in ortak})
    v5_egri, _ = gorunurluk_egrisi(v5_veri, kare_bayt, adet, kutu, vw, vh,
                                   {ad: v5_maske[ad] for ad in ortak})
    fark = {ad: round(max(abs(x - y) for x, y in zip(egri[ad], yeni_egri[ad])), 4)
            for ad in ortak}
    log(f"katman egri farki (referans vs yeni): {fark}")
    with (out / "ZAMANLAMA.csv").open("a", newline="", encoding="utf-8") as fh:
        yz = csv.writer(fh)
        yz.writerow([])
        yz.writerow(["# yeni video egrisi"])
        yz.writerow(["kare", "sn"] + [f"yeni_{ad}" for ad in ortak]
                    + [f"v5_{ad}" for ad in ortak])
        for i in range(min(adet, yeni_adet)):
            yz.writerow([i, round(i / fps, 3)]
                        + [yeni_egri[ad][i] for ad in ortak]
                        + [v5_egri[ad][i] for ad in ortak])
    (out / "ZAMANLAMA_OZET.json").write_text(json.dumps(
        {"zamanlama": zaman, "maske_notu_referans": ref_not,
         "maske_notu_v5": v5_not, "yeni_zamanlama":
             {ad: zamanlama(yeni_egri[ad], fps) for ad in ortak},
         "v5_zamanlama": {ad: zamanlama(v5_egri[ad], fps) for ad in ortak},
         "egri_farki": fark}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print(json.dumps({"egri_farki": fark,
                      "zamanlama": {ad: {k: z[k] for k in
                                         ("sonme_basi_sn", "tam_yok_ilk_sn",
                                          "tam_yok_son_sn", "geri_sn")}
                                    for ad, z in zaman.items()}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
