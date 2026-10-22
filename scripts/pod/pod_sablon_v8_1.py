#!/usr/bin/env python3
"""POD sablon V8.1 - V8 hatti, tek duzeltme + uc ornek.

V8'e gore tek fark: kucuk burc sembolu maskeleri 3 px genisletilir; boylece
sembolun kenar yumusatma (anti-alias) halkasi da maskeye girer ve sonme
aninda yerinde soluk iz kalmaz. Ana sembol, daire cizgisi, tozlar ve
zamanlama V8 ile AYNI.

Yerel calisir, Etsy cagrisi yoktur.
"""
import argparse
import csv
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
                           kutu_olcekle, panel_kutusu, yuv_ac, yuv_video_yaz)
from pod_sablon_v5 import kapak_ac, kutu_boyut  # noqa: E402
from pod_sablon_v6 import maske_panele  # noqa: E402
from pod_sablon_v8 import (SOLAN_KATMANLAR, YUMUSATMA,  # noqa: E402
                           gorunurluk_egrisi, katman_maskeleri,
                           kuyruk_normalize, temiz_zemin, zamanlama)

GENISLETME = 3          # kucuk sembol maskesi genisletme (panel uzayi px)
TOZ_ESIK = 8.0


def ornek_uret(etiket, lid, v5_video, out, ref_egri, kutu, kutu_kapak,
               vw, vh, fps, sure, kare_bayt):
    """Bir ornek icin V8.1 videosu + kapagi uretir."""
    is_dir = out / "_is" / lid
    is_dir.mkdir(parents=True, exist_ok=True)
    v5_veri, _, adet = yuv_ac(v5_video, is_dir / "v5.yuv", vw, vh)
    pw, ph = kutu_boyut(kutu)

    kare0 = is_dir / "v5_kare0.png"
    extract_frame(v5_video, kare0, 0)
    with Image.open(kare0) as im:
        kapak_a = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    maske_k, notlar, _ = katman_maskeleri(kapak_a)
    maske = {ad: maske_panele(m, kutu_kapak, pw, ph)
             for ad, m in maske_k.items() if m.any()}
    ortak = [ad for ad in ref_egri if ad in maske and ad in SOLAN_KATMANLAR]
    if not ortak:
        raise SystemExit(f"HATA: {etiket} icin solan katman yok -> DUR")
    # TEK DUZELTME: kucuk sembol maskeleri 3 px genisletilir
    genis = {ad: ndimage.binary_dilation(maske[ad], iterations=GENISLETME)
             for ad in ortak}
    log(f"{etiket}: katman {ortak} | maske px "
        f"{ {ad: int(maske[ad].sum()) for ad in ortak} } -> genisletilmis "
        f"{ {ad: int(genis[ad].sum()) for ad in ortak} }")
    log(f"{etiket}: dokunulmayan {[a for a in maske if a not in ortak]} | "
        f"not {json.dumps(notlar, ensure_ascii=False)[:200]}")

    alfa_kat = {ad: np.clip(ndimage.gaussian_filter(
        genis[ad].astype(np.float32), sigma=YUMUSATMA), 0.0, 1.0)
        for ad in ortak}

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
        dolgu |= ndimage.binary_dilation(genis[ad], iterations=3)
    zemin_y = temiz_zemin(y0, dolgu)
    zemin_u = temiz_zemin(u0, dolgu[::2, ::2])
    zemin_v = temiz_zemin(v0, dolgu[::2, ::2])
    y0f = y0.astype(np.float32)

    ham = is_dir / "yeni.yuv"
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
            toz = np.clip(py - y0f, 0.0, None)
            toz_agirlik = np.clip(toz / TOZ_ESIK, 0.0, 1.0)
            b = np.zeros((ph, pw), dtype=np.float32)
            for ad in ortak:
                g = ref_egri[ad][i] if i < len(ref_egri[ad]) else 1.0
                b = np.maximum(b, alfa_kat[ad] * (1.0 - float(np.clip(g, 0, 1))))
            b *= (1.0 - toz_agirlik)
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

    video = out / f"{etiket}_{lid}_video_V8_1.mp4"
    yuv_video_yaz(ham, video, vw, vh, fps, sure)
    kapak = out / f"{etiket}_{lid}_kapak_V8_1.png"
    k0 = is_dir / "yeni_kare0.png"
    extract_frame(video, k0, 0)
    with Image.open(k0) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(kapak)
    ham.unlink(missing_ok=True)
    (is_dir / "v5.yuv").unlink(missing_ok=True)
    return {"etiket": etiket, "listing_id": lid, "video": video, "kapak": kapak,
            "maske_px": {ad: int(maske[ad].sum()) for ad in ortak},
            "genis_px": {ad: int(genis[ad].sum()) for ad in ortak},
            "katmanlar": ortak, "maske_notu": notlar}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="_veri/v8")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    veri = pathlib.Path(a.veri)
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)

    ornekler = [
        ("Aquarius_Aries", "4570110641", veri / "v5_ornek_video.mp4"),
        ("Aries_Leo", "4570031205", veri / "v5_Aries_Leo_4570031205_video.mp4"),
        ("Aquarius_Cancer", "4570125580",
         veri / "v5_Aquarius_Cancer_4570125580_video.mp4"),
    ]
    ref_video = veri / "referans_video.mp4"
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
    ref_maske_k, ref_not, _ = katman_maskeleri(ref_kapak_a)
    ref_maske = {ad: maske_panele(m, kutu_kapak, pw, ph)
                 for ad, m in ref_maske_k.items() if m.any()}
    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, out / "_is" / "ref.yuv",
                                           vw, vh)
    ham_egri, _ = gorunurluk_egrisi(ref_veri, kare_bayt, ref_adet, kutu, vw, vh,
                                    ref_maske)
    ref_egri = {ad: kuyruk_normalize(e) for ad, e in ham_egri.items()}
    zaman = {ad: zamanlama(e, fps) for ad, e in ref_egri.items()}
    for ad in SOLAN_KATMANLAR:
        if ad in zaman:
            z = zaman[ad]
            log(f"REF {ad}: yok {z['tam_yok_ilk_sn']}-{z['tam_yok_son_sn']} sn "
                f"| geri {z['geri_sn']} sn")
    del ref_veri

    sonuc = []
    for etiket, lid, yol in ornekler:
        if not yol.exists():
            raise SystemExit(f"HATA: {yol} yok -> DUR")
        sonuc.append(ornek_uret(etiket, lid, yol, out, ref_egri, kutu,
                                kutu_kapak, vw, vh, fps, sure, kare_bayt))

    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    satirlar = []
    for ad, yol in [("REFERANS  Aquarius + Gemini  4570112095", ref_video)] + \
            [(f"{s['etiket'].replace('_', ' + ')}  {s['listing_id']}",
              s["video"]) for s in sonuc]:
        g = []
        klasor = out / "_is" / "kare" / ad.split()[0]
        klasor.mkdir(parents=True, exist_ok=True)
        for i, z in enumerate(zamanlar):
            zz = min(z, max(sure - 1.0 / fps, 0))
            p2 = klasor / f"{i}.png"
            extract_frame(yol, p2, zz)
            g.append((f"{zz:.2f} sn", Image.open(p2).convert("RGB")))
        satirlar.append((ad, g))
    boyut = karsilastirma(satirlar, out / "KARE_KARSILASTIRMA_V8_1.jpg")
    log(f"KARE_KARSILASTIRMA_V8_1.jpg {boyut[0]}x{boyut[1]} "
        f"({len(satirlar)} satir)")

    with (out / "ZAMANLAMA_V8_1.csv").open("w", newline="", encoding="utf-8") as fh:
        yz = csv.writer(fh)
        yz.writerow(["kare", "sn"] + list(ref_egri))
        for i in range(ref_adet):
            yz.writerow([i, round(i / fps, 3)] + [ref_egri[ad][i] for ad in ref_egri])
    (out / "URETIM_SONUC_V8_1.json").write_text(json.dumps(
        {"genisletme_px": GENISLETME, "zamanlama": zaman,
         "referans_maske_notu": ref_not,
         "ornekler": [{k: (str(v) if isinstance(v, pathlib.Path) else v)
                       for k, v in s.items()} for s in sonuc]},
        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"ornek": [s["etiket"] for s in sonuc],
                      "genisletme_px": GENISLETME}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
