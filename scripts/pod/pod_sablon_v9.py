#!/usr/bin/env python3
"""POD sablon V9 - panel ici KATMANLI kurulur.

V8.1 geri bildirimi: altin rengi/dokusu referansla ayni degil, daire bozuk,
1.31-1.97 sn'de sembol iclerinde karartilar var. Kok neden: panel ici ilanin
kendi videosundan geliyordu.

V9'da panel ici sifirdan kurulur:
  KATMAN 1  Referansin kendi pikselleri (zemin, yildizlar, daire, sonsuzluk
            isareti, alt satir). Referansa ozgu ogelerin bolgeleri 0. kareden
            temiz zemin ile doldurulur (referans tozu da kalmaz).
  KATMAN 2  Cifte ozel statik sekiller (ana sembol, 2 kucuk sembol, 2 burc
            adi). Boyama: referansin AYNI TUR ogesinden ogrenilen
            parlaklik->renk esleme (gradient map) + parlaklik dagilimi
            histogram eslemesi.
  KATMAN 3  Animasyon: kucuk semboller referans zamanlamasiyla soner/doner,
            ana sembol hic sonmez, burc adlari referansin hafif sonme
            egrisini alir, tozlar V5'ten YALNIZ TOPLAMALI eklenir.
  KATMAN 4  Panel disi referansin baytlari (YUV kompozit).

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
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, cift_hizala, karsilastirma,  # noqa: E402
                           kareleri_ac, kutu_olcekle, panel_kutusu,
                           rgb_yuv_doseme, yuv_ac, yuv_video_yaz)
from pod_sablon_v5 import kapak_ac, kutu_boyut  # noqa: E402
from pod_sablon_v6 import BOLGE, maske_panele  # noqa: E402
from pod_sablon_v8 import (_comps, _maske_of, gorunurluk_egrisi,  # noqa: E402
                           katman_maskeleri, kuyruk_normalize, panel_y,
                           temiz_zemin, zamanlama)

YUMUSAK = 0.8           # sekil kenari yumusatma sigmasi (panel px)
TEMIZ_GENIS = 6         # referans oge bolgesi genisletme (panel px)
TOZ_TABAN = 3.0         # bu esigin altindaki fark toz sayilmaz (Y)


def luma(rgb):
    a = rgb.astype(np.float32)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def isim_maskesi(kapak_a, ana_maske, kucuk_maskeler=()):
    """Iki burc adi yazisi (cift adi bandindaki ALT satir, sonsuzluk haric)."""
    altin = artwork_mask(kapak_a)
    sekil = altin.shape
    u2, al2, s2, sa2 = BOLGE["cift_adi"]
    bolge = np.zeros(sekil, dtype=bool)
    bolge[u2 - 200:al2 + 60, s2:sa2] = True
    disla = np.zeros(sekil, dtype=bool)
    glif_alt = 0
    for m in kucuk_maskeler:
        if m is not None and m.any():
            disla |= m
            glif_alt = max(glif_alt, int(np.where(m)[0].max()))
    yerel = (altin & bolge) & ~ana_maske & ~ndimage.binary_dilation(
        disla, iterations=3)
    comps = sorted(_comps(yerel, en_az=150), key=lambda c: c["y0"])
    if not comps:
        return np.zeros(sekil, dtype=bool), {}
    if glif_alt:
        # burc adlari kucuk sembollerin ALTINDA
        yazilar = [c for c in comps if c["y0"] > glif_alt - 10]
    else:
        ustler = [c["y0"] for c in comps]
        bosluk = [(ustler[i + 1] - ustler[i], i) for i in range(len(ustler) - 1)]
        kesim = None
        if bosluk:
            en_buyuk, idx = max(bosluk)
            if en_buyuk >= 40:
                kesim = idx
        yazilar = comps[kesim + 1:] if kesim is not None else comps
    orta_x = (s2 + sa2) / 2
    isim = np.zeros(sekil, dtype=bool)
    sonsuz = []
    for c in yazilar:
        cx = (c["x0"] + c["x1"]) / 2
        genislik = c["x1"] - c["x0"]
        if abs(cx - orta_x) < 90 and genislik < 130:
            sonsuz.append({"x": [c["x0"], c["x1"]], "alan": c["alan"]})
            continue                      # sonsuzluk isareti KATMAN 1'de kalir
        isim |= _maske_of(c, sekil)
    return isim, {"yazi_bilesen": len(yazilar), "sonsuzluk": sonsuz,
                  "yazi_ust": yazilar[0]["y0"] if yazilar else None}


def gradient_lut(kaynak_rgb, kaynak_maske):
    """Referans ogesinden parlaklik -> RGB esleme tablosu."""
    p = kaynak_rgb[kaynak_maske].astype(np.float32)
    l = luma(p)
    lut = np.zeros((256, 3), dtype=np.float32)
    dolu = np.zeros(256, dtype=bool)
    idx = np.clip(np.rint(l), 0, 255).astype(np.int32)
    for b in np.unique(idx):
        sec = idx == b
        lut[b] = p[sec].mean(axis=0)
        dolu[b] = True
    b_dolu = np.where(dolu)[0]
    for k in range(3):
        lut[:, k] = np.interp(np.arange(256), b_dolu, lut[b_dolu, k])
    return lut, np.sort(l)


def histogram_esle(deger, hedef_sirali):
    """Degerleri hedef dagilimin siralanmis ornegine esler."""
    sira = np.argsort(np.argsort(deger))
    q = sira / max(len(deger) - 1, 1)
    yer = q * (len(hedef_sirali) - 1)
    alt = np.floor(yer).astype(np.int32)
    ust = np.clip(alt + 1, 0, len(hedef_sirali) - 1)
    pay = yer - alt
    return hedef_sirali[alt] * (1 - pay) + hedef_sirali[ust] * pay


def boya(hedef_rgb, hedef_maske, ref_rgb, ref_maske):
    """Cift seklini referansin ayni tur ogesinin renk/dokusuyla boyar."""
    lut, ref_l = gradient_lut(ref_rgb, ref_maske)
    l_tam = ndimage.median_filter(luma(hedef_rgb), size=3)
    l = l_tam[hedef_maske]
    eslenen = histogram_esle(l, ref_l)
    idx = np.clip(np.rint(eslenen), 0, 255).astype(np.int32)
    cikti = np.zeros(hedef_rgb.shape, dtype=np.float32)
    cikti[hedef_maske] = lut[idx]
    return cikti, {"ref_luma_ort": round(float(ref_l.mean()), 1),
                   "hedef_luma_ort_once": round(float(l.mean()), 1),
                   "hedef_luma_ort_sonra": round(float(eslenen.mean()), 1),
                   "piksel": int(hedef_maske.sum())}


def panel_rgb(kareler, i, kutu):
    with Image.open(kareler[i]) as im:
        a = np.asarray(im.convert("RGB"), dtype=np.uint8)
    return a[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]


def yumusak(maske, sigma=YUMUSAK):
    return np.clip(ndimage.gaussian_filter(maske.astype(np.float32), sigma), 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="_veri/v8")
    ap.add_argument("--out", required=True)
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
    log(f"panel {pw}x{ph} | video {vw}x{vh} {sure:.2f} sn {fps} fps")

    # ---- maskeler: referans
    ref_k, ref_not, _ = katman_maskeleri(ref_kapak_a)
    ref_isim_k, ref_isim_not = isim_maskesi(
        ref_kapak_a, ref_k["ana_sembol"],
        (ref_k.get("kucuk_burc_1"), ref_k.get("kucuk_burc_2")))
    ref_m = {ad: maske_panele(m, kutu_kapak, pw, ph)
             for ad, m in ref_k.items() if m.any()}
    ref_m["isim"] = maske_panele(ref_isim_k, kutu_kapak, pw, ph)
    log(f"referans maske px { {k: int(v.sum()) for k, v in ref_m.items()} } | "
        f"sonsuzluk {ref_isim_not.get('sonsuzluk')}")

    # ---- maskeler: cift (V5 karesi 0, referans panel geometrisinde)
    v5_kareler = kareleri_ac(v5_video, out / "_is" / "v5kare")
    ref_kareler = kareleri_ac(ref_video, out / "_is" / "refkare")
    v5_k0 = out / "_is" / "v5_kapak0.png"
    with Image.open(v5_kareler[0]) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(v5_k0)
    v5_kapak_a = kapak_ac(v5_k0)
    cift_k, cift_not, _ = katman_maskeleri(v5_kapak_a)
    cift_isim_k, cift_isim_not = isim_maskesi(
        v5_kapak_a, cift_k["ana_sembol"],
        (cift_k.get("kucuk_burc_1"), cift_k.get("kucuk_burc_2")))
    def kapat(m):
        """Delikleri doldurup 1 px genisletir: boyamada siyah benek kalmaz."""
        return ndimage.binary_dilation(
            ndimage.binary_fill_holes(ndimage.binary_closing(
                m, structure=np.ones((5, 5), bool))), iterations=1)

    cift_m = {ad: kapat(maske_panele(m, kutu_kapak, pw, ph))
              for ad, m in cift_k.items() if m.any()}
    cift_m["isim"] = kapat(maske_panele(cift_isim_k, kutu_kapak, pw, ph))
    log(f"cift maske px { {k: int(v.sum()) for k, v in cift_m.items()} }")

    def kutu_of(m):
        ys, xs = np.where(m)
        return [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())] \
            if m.any() else None
    duzen = {ad: {"referans": kutu_of(ref_m.get(ad, np.zeros((ph, pw), bool))),
                  "cift": kutu_of(cift_m.get(ad, np.zeros((ph, pw), bool)))}
             for ad in ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim")}
    for ad, d in duzen.items():
        if d["referans"] and d["cift"]:
            f = [d["cift"][i] - d["referans"][i] for i in range(4)]
            log(f"DUZEN {ad}: referans {d['referans']} cift {d['cift']} fark {f}")

    # ---- referans egrileri (kucuk semboller + isimler)
    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, out / "_is" / "ref.yuv",
                                           vw, vh)
    olcum_m = {ad: ref_m[ad] for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim")
               if ad in ref_m and ref_m[ad].any()}
    ham, _ = gorunurluk_egrisi(ref_veri, kare_bayt, ref_adet, kutu, vw, vh, olcum_m)
    egri = {ad: kuyruk_normalize(e) for ad, e in ham.items()}
    zaman = {ad: zamanlama(e, fps) for ad, e in egri.items()}
    for ad, z in zaman.items():
        log(f"REF egri {ad}: yok {z['tam_yok_ilk_sn']}-{z['tam_yok_son_sn']} sn "
            f"| geri {z['geri_sn']} sn | en dusuk {z['en_dusuk']}")

    # ---- KATMAN 1: referans zemini, ogeler bosaltilmis
    ref0 = panel_rgb(ref_kareler, 0, kutu).astype(np.float32)
    temiz_bolge = np.zeros((ph, pw), dtype=bool)
    for ad in ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim"):
        if ad in ref_m:
            temiz_bolge |= ndimage.binary_dilation(ref_m[ad],
                                                   iterations=TEMIZ_GENIS)
    for ad in ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim"):
        if ad in cift_m:
            temiz_bolge |= ndimage.binary_dilation(cift_m[ad],
                                                   iterations=TEMIZ_GENIS)
    log(f"temiz zemin bolgesi {int(temiz_bolge.sum())} px "
        f"(her karede o karenin kendi pikselinden doldurulur)")

    # ---- KATMAN 2: cift sekilleri, referans renk/dokusuyla
    v5_0 = panel_rgb(v5_kareler, 0, kutu).astype(np.float32)
    kucuk_ref = np.zeros((ph, pw), dtype=bool)
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in ref_m:
            kucuk_ref |= ref_m[ad]
    kaynak_of = {"ana_sembol": ref_m.get("ana_sembol"), "isim": ref_m.get("isim"),
                 "kucuk_burc_1": kucuk_ref, "kucuk_burc_2": kucuk_ref}
    boyali, boya_not = {}, {}
    for ad in ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim"):
        m = cift_m.get(ad)
        kay = kaynak_of.get(ad)
        if m is None or not m.any() or kay is None or not kay.any():
            continue
        boyali[ad], boya_not[ad] = boya(v5_0, m, ref0, kay)
    log(f"boyama: {json.dumps(boya_not, ensure_ascii=False)}")

    # ---- toz rengi (referansin kendi tozundan)
    toz_ornek = []
    for i in (30, 60, 90):
        d = panel_rgb(ref_kareler, i, kutu).astype(np.float32) - ref0
        sec = luma(d) > 12
        if sec.any():
            toz_ornek.append(d[sec].mean(axis=0))
    toz_renk = (np.mean(toz_ornek, axis=0) if toz_ornek
                else np.array([255.0, 200.0, 120.0], dtype=np.float32))
    toz_renk = toz_renk / max(luma(toz_renk[None, None, :])[0, 0], 1e-6)
    log(f"toz rengi (birim luma basina RGB) {np.round(toz_renk, 3).tolist()}")

    # ---- kompozit
    v5_veri, _, v5_adet = yuv_ac(v5_video, out / "_is" / "v5.yuv", vw, vh)
    v5_y0 = panel_y(v5_veri, kare_bayt, 0, kutu, vw, vh).astype(np.float32)
    adet = min(ref_adet, v5_adet, len(ref_kareler), len(v5_kareler))
    alfa_m = {ad: yumusak(cift_m[ad]) for ad in boyali}
    ham_yuv = out / "_is" / "yeni.yuv"
    with open(ham_yuv, "wb") as fh:
        for i in range(adet):
            kare = panel_rgb(ref_kareler, i, kutu).astype(np.float32)
            # KATMAN 1: referansa ozgu ogelerin bolgesi O KARENIN kendi
            # cevresinden doldurulur; boylece referansin akan tozu korunur ve
            # sembol cevresinde statik koyu hale olusmaz.
            zemin_i = np.stack([temiz_zemin(kare[..., k], temiz_bolge)
                                for k in range(3)], axis=-1)
            taban = np.where(temiz_bolge[..., None], zemin_i, kare)
            for ad, boyalim in boyali.items():
                if ad in ("kucuk_burc_1", "kucuk_burc_2"):
                    g = egri[ad][i] if ad in egri else 1.0
                elif ad == "isim":
                    g = egri["isim"][i] if "isim" in egri else 1.0
                else:
                    g = 1.0
                al = (alfa_m[ad] * float(np.clip(g, 0, 1)))[..., None]
                taban = taban * (1 - al) + boyalim * al
            # toz: YALNIZ toplamali
            toz = np.clip(panel_y(v5_veri, kare_bayt, i, kutu, vw, vh
                                  ).astype(np.float32) - v5_y0 - TOZ_TABAN,
                          0.0, None)
            taban = np.clip(taban + toz[..., None] * toz_renk[None, None, :],
                            0, 255)
            Y, U, V = rgb_yuv_doseme(np.rint(taban).astype(np.uint8))
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

    video = out / "Aquarius_Aries_4570110641_video_V9.mp4"
    yuv_video_yaz(ham_yuv, video, vw, vh, fps, sure)
    kapak = out / "Aquarius_Aries_4570110641_kapak_V9.png"
    k0 = out / "_is" / "yeni_kare0.png"
    extract_frame(video, k0, 0)
    with Image.open(k0) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(kapak)
    ham_yuv.unlink(missing_ok=True)
    (out / "_is" / "v5.yuv").unlink(missing_ok=True)
    (out / "_is" / "ref.yuv").unlink(missing_ok=True)

    # ---- kontrol gorselleri
    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    satir = []
    for ad, yol in [("REFERANS  Aquarius + Gemini", ref_video),
                    ("YENI V9  Aquarius + Aries", video)]:
        g = []
        kl = out / "_is" / "k8" / ad.split()[0]
        kl.mkdir(parents=True, exist_ok=True)
        for i, z in enumerate(zamanlar):
            zz = min(z, max(sure - 1.0 / fps, 0))
            pp = kl / f"{i}.png"
            extract_frame(yol, pp, zz)
            g.append((f"{zz:.2f} sn", Image.open(pp).convert("RGB")))
        satir.append((ad, g))
    b1 = karsilastirma(satir, out / "KARE_KARSILASTIRMA_V9.jpg")

    # yakin plan: kare 0 kirpintilari
    def kirp(img_rgb, kutu4, olcek=2):
        y0, y1, x0, x1 = kutu4
        pay = 12
        y0, y1 = max(y0 - pay, 0), min(y1 + pay, img_rgb.shape[0] - 1)
        x0, x1 = max(x0 - pay, 0), min(x1 + pay, img_rgb.shape[1] - 1)
        im = Image.fromarray(img_rgb[y0:y1 + 1, x0:x1 + 1].astype(np.uint8))
        return im.resize((im.width * olcek, im.height * olcek),
                         Image.Resampling.LANCZOS)

    yeni0 = panel_rgb(sorted((out / "_is" / "k8" / "YENI").glob("*.png")), 0,
                      {"ust": 0, "alt": vh - 1, "sol": 0, "sag": vw - 1})
    yeni0 = yeni0[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]
    ref0u = ref0.astype(np.uint8)
    daire_kutu = [int(0.06 * ph), int(0.26 * ph), int(0.02 * pw), int(0.30 * pw)]
    yakin = []
    for ad, kt in [("ana sembol", duzen["ana_sembol"]),
                   ("kucuk sembol", duzen["kucuk_burc_1"]),
                   ("burc adi", duzen["isim"])]:
        if kt["referans"] and kt["cift"]:
            yakin.append((ad, kt))
    satir2 = [("REFERANS", [(ad, kirp(ref0u, kt["referans"])) for ad, kt in yakin]
               + [("daire", kirp(ref0u, daire_kutu))]),
              ("YENI V9", [(ad, kirp(yeni0, kt["cift"])) for ad, kt in yakin]
               + [("daire", kirp(yeni0, daire_kutu))])]
    b2 = karsilastirma(satir2, out / "ALTIN_YAKIN.jpg", hucre=520)

    # 1.31 / 1.97 sn ana sembol yakin plan
    satir3 = []
    for ad, yol in [("REFERANS", ref_video), ("YENI V9", video)]:
        g = []
        for sn in (1.314, 1.971):
            pp = out / "_is" / f"{ad[:3]}_{sn}.png"
            extract_frame(yol, pp, sn)
            with Image.open(pp) as im:
                arr = np.asarray(im.convert("RGB"), dtype=np.uint8)
            pan = arr[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]
            kt = duzen["ana_sembol"]["referans" if ad == "REFERANS" else "cift"]
            g.append((f"{sn:.2f} sn", kirp(pan, kt)))
        satir3.append((ad, g))
    b3 = karsilastirma(satir3, out / "YAKIN_131_197.jpg", hucre=640)
    log(f"gorseller: KARE {b1} | ALTIN_YAKIN {b2} | YAKIN_131_197 {b3}")

    (out / "URETIM_SONUC_V9.json").write_text(json.dumps(
        {"panel": [pw, ph], "duzen": duzen, "boyama": boya_not,
         "zamanlama": zaman, "toz_renk": np.round(toz_renk, 4).tolist(),
         "referans_maske_notu": ref_not, "cift_maske_notu": cift_not,
         "referans_isim_notu": ref_isim_not, "cift_isim_notu": cift_isim_not},
        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"duzen_farki": {ad: ([d["cift"][i] - d["referans"][i]
                                            for i in range(4)]
                                           if d["referans"] and d["cift"] else None)
                                      for ad, d in duzen.items()}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
