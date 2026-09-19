#!/usr/bin/env python3
"""POD sablon V7 - referansin ISIK ALANINI aktarir (oge bazli egri iptal).

V6 bulgusu: referanstaki sonme, panelin tumunun isikla kararmasindan geliyor;
semboller arka plana gore sabit. Bu yuzden artik oge egrisi degil, panelin
isik alani aktariliyor:

    LP        = genis Gauss alcak geciren (tozlari ve cizgileri siler), Y'de
    Rref(t)   = LP(ref(t)) / LP(ref(0))
    Rown(t)   = LP(own(t)) / LP(own(0))
    new(t)    = own(t) * Rref(t) / Rown(t)          (yalniz panel ici)

Panel disi referansin baytlaridir (V5 hatti). Tozlar own(t)'den gelir ve
kazanc disinda dokunulmaz. B altin esitlemesi en sonda, yalniz altin maskede.

Etsy'ye YAZMA YOK: yalniz GET, --apply reddedilir.
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import download, gallery, videos, video_url  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, KONTROL_KAPAK_ID, REFERANS_ID,  # noqa: E402
                           altin_ort, cift_hizala, kareleri_ac, karsilastirma,
                           kutu_olcekle, panel_kutusu, yuv_ac, yuv_dis_mae,
                           yuv_video_yaz)
from pod_sablon_v5 import (altin_ofset_bul, kapak_ac, kaynak_kutulari,  # noqa: E402
                           kutu_boyut, mae, rgb_ofset_yuv, simdi)
from pod_sablon_v6 import BOLGE, egri_ciz, maske_panele  # noqa: E402

PANEL_ESIK = 0.03       # panel ortalama parlaklik egrisi farki (oran)
YAZI_ESIK = 0.05        # cift adi bolgesi parlaklik egrisi farki (oran)
GORSEL_KAPI_MAE = 2.0
KAZANC_ALT, KAZANC_UST = 0.2, 3.0


def lp(y, sigma):
    """Y duzleminde isik alani: genis Gauss. Pedestal (16) cikarilir."""
    return ndimage.gaussian_filter(np.clip(y - 16.0, 1.0, None), sigma=sigma,
                                   mode="nearest")


def sigma_sec(pw, ph):
    """Panel genisligine gore sigma; tozlari ve cizgileri silecek kadar genis."""
    return max(round(min(pw, ph) / 30.0), 12)


def lp_kalinti(y, sigma, altin_maske):
    """LP'nin cizgileri ne kadar sildigini olcer.

    Donus: (ham_kontrast, lp_kontrast, oran). Oran kucukse LP yalnizca isigi
    tasiyor demektir.
    """
    if altin_maske is None or not altin_maske.any() or (~altin_maske).all() is False:
        return None, None, None
    ham = float(y[altin_maske].mean() - y[~altin_maske].mean())
    d = lp(y, sigma)
    dusuk = float(d[altin_maske].mean() - d[~altin_maske].mean())
    return round(ham, 2), round(dusuk, 2), round(abs(dusuk) / max(abs(ham), 1e-6), 4)


def panel_duzlemleri(veri, kare_bayt, i, kutu, w, h):
    """Bir karenin panel Y/U/V dilimleri (kopya degil, gorunum)."""
    blok = veri[i * kare_bayt:(i + 1) * kare_bayt]
    y = blok[:w * h].reshape(h, w)
    u = blok[w * h:w * h + w * h // 4].reshape(h // 2, w // 2)
    v = blok[w * h + w * h // 4:].reshape(h // 2, w // 2)
    ph = kutu["alt"] - kutu["ust"] + 1
    pw = kutu["sag"] - kutu["sol"] + 1
    return (y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw],
            u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2],
            v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2])


def parlaklik_egrisi(veri, kare_bayt, adet, kutular, w, h, maske=None):
    """Panel (ya da maskeli bolge) ortalama Y'sinin kare 0'a orani."""
    egri, taban = [], None
    for i in range(adet):
        k = kutular[i] if kutular else None
        if k is None:
            egri.append(None)
            continue
        y, _, _ = panel_duzlemleri(veri, kare_bayt, i, k, w, h)
        yf = y.astype(np.float32)
        ort = float(yf[maske].mean()) if maske is not None and maske.any() \
            else float(yf.mean())
        if taban is None:
            taban = ort
        egri.append(round(ort / max(taban, 1e-6), 4))
    return egri


def kompozit_isik(ref_veri, kay_veri, kare_bayt, adet, ref_kutu, kutular,
                  w, h, cikti, sigma, dyuv, altin_maske, altin_uv,
                  yapi_ist=None):
    """Panel icini own(t) * Rref(t)/Rown(t) ile kurar; panel disi degismez."""
    pw, ph = kutu_boyut(ref_kutu)
    ru, rs = ref_kutu["ust"], ref_kutu["sol"]
    ry0, _, _ = panel_duzlemleri(ref_veri, kare_bayt, 0, ref_kutu, w, h)
    lp_ref0 = lp(ry0.astype(np.float32), sigma)
    k0 = kutular[0]
    oy0, _, _ = panel_duzlemleri(kay_veri, kare_bayt, 0, k0, w, h)
    lp_own0 = lp(oy0.astype(np.float32), sigma)
    kazanc_ist = []
    with open(cikti, "wb") as fh:
        for i in range(adet):
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            k = kutular[i] if i < len(kutular) else None
            if k is None:
                blok.tofile(fh)
                continue
            ry, _, _ = panel_duzlemleri(ref_veri, kare_bayt, i, ref_kutu, w, h)
            oy, ou, ov = panel_duzlemleri(kay_veri, kare_bayt, i, k, w, h)
            lp_ref = lp(ry.astype(np.float32), sigma)
            lp_own = lp(oy.astype(np.float32), sigma)
            g = np.clip((lp_ref / lp_ref0) * (lp_own0 / lp_own),
                        KAZANC_ALT, KAZANC_UST)
            kazanc_ist.append((float(g.min()), float(g.mean()), float(g.max())))
            if yapi_ist is not None and altin_maske is not None:
                # kazancta sembol yapisi kaldi mi: altin maskesi ile arka plan
                # arasindaki kazanc farki, kazancin kendi genligine orani
                fark = float(g[altin_maske].mean() - g[~altin_maske].mean())
                genlik = max(float(g.max() - g.min()), 1e-6)
                yapi_ist.append((round(fark, 5), round(abs(fark) / genlik, 4)))
            g_uv = g[::2, ::2]
            py = 16.0 + (oy.astype(np.float32) - 16.0) * g
            pu = 128.0 + (ou.astype(np.float32) - 128.0) * g_uv
            pv = 128.0 + (ov.astype(np.float32) - 128.0) * g_uv
            if altin_maske is not None:
                py[altin_maske] += dyuv[0]
                pu[altin_uv] += dyuv[1]
                pv[altin_uv] += dyuv[2]
            y = blok[:w * h].reshape(h, w)
            u = blok[w * h:w * h + w * h // 4].reshape(h // 2, w // 2)
            v = blok[w * h + w * h // 4:].reshape(h // 2, w // 2)
            y[ru:ru + ph, rs:rs + pw] = np.rint(np.clip(py, 16, 235)).astype(np.uint8)
            u[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                np.rint(np.clip(pu, 16, 240)).astype(np.uint8)
            v[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                np.rint(np.clip(pv, 16, 240)).astype(np.uint8)
            blok.tofile(fh)
    return kazanc_ist


def fark_ozet(a, b):
    d = [abs(x - y) for x, y in zip(a, b) if x is not None and y is not None]
    if not d:
        return None, None
    return round(max(d), 4), d.index(max(d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ornek-id", required=True)
    ap.add_argument("--referans-id", default=REFERANS_ID)
    ap.add_argument("--yerel-girdi", default="")
    ap.add_argument("--sigma", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: bu hat Etsy'ye YAZMAZ; --apply reddedildi.")

    t0 = time.time()
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    ad_of = {str(r["id"]): (r.get("pair") or str(r["id"])) for r in katalog}
    kota_once = kota_sonra = None

    if a.yerel_girdi:
        kaynak = pathlib.Path(a.yerel_girdi)
        log(f"YEREL PROVA: {kaynak}")

        def indir(lid, is_dir):
            k, v = is_dir / "kapak.png", is_dir / "video.mp4"
            k.write_bytes((kaynak / f"{lid}_kapak.png").read_bytes())
            v.write_bytes((kaynak / f"{lid}_video.mp4").read_bytes())
            return k, v, {"kapak_id": "yerel", "video_id": "yerel"}
    else:
        shop = os.environ["ETSY_SHOP_ID"]
        st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                        os.environ.get("ETSY_SHARED_SECRET"))
        if st.needs_refresh():
            st.refresh()
        api = Etsy(st)
        api.get(f"/shops/{shop}", ok404=True)
        kota_once = api.remaining

        def indir(lid, is_dir):
            gor, vid = gallery(api, lid), videos(api, lid)
            if not gor or not vid:
                raise RuntimeError("gorsel veya video yok")
            k, v = is_dir / "kapak.png", is_dir / "video.mp4"
            download(gor[0].get("url_fullxfull") or gor[0].get("url_570xN"), k)
            download(video_url(vid[0]), v)
            return k, v, {"kapak_id": str(gor[0].get("listing_image_id")),
                          "video_id": str(vid[0].get("video_id"))}

    # ------------------------------------------------------ referans
    ref_dir = out / "_is" / "REFERANS"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_kapak, ref_video, ref_kim = indir(a.referans_id, ref_dir)
    meta = probe(ref_video)
    ak = meta["streams"][0]
    vw, vh = int(ak["width"]), int(ak["height"])
    ref_sure = float(meta["format"]["duration"])
    p1, q1 = (ak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    ref_fps = round(float(p1) / float(q1), 3)
    ref_kapak_a = kapak_ac(ref_kapak)
    ref_kutu_kapak = panel_kutusu(ref_kapak_a)
    if ref_kutu_kapak is None:
        raise SystemExit("HATA: referans kapaginda panel bulunamadi -> DUR")
    ref_kutu = cift_hizala(kutu_olcekle(ref_kutu_kapak, KAPAK[1], vh, KAPAK[0], vw))
    pw, ph = kutu_boyut(ref_kutu)
    sigma = a.sigma or sigma_sec(pw, ph)
    ref_kareler = kareleri_ac(ref_video, ref_dir / "kare")
    hedef_altin, _ = altin_ort(ref_kapak_a)
    log(f"Referans video id {ref_kim.get('video_id')} | {vw}x{vh}, "
        f"{ref_sure:.2f} sn, {ref_fps} fps, {len(ref_kareler)} kare | panel "
        f"{pw}x{ph} | sigma {sigma}")

    altin_kapak = artwork_mask(ref_kapak_a)
    altin_panel = maske_panele(altin_kapak, ref_kutu_kapak, pw, ph)
    yazi_kapak = np.zeros_like(altin_kapak)
    u_, al_, s_, sa_ = BOLGE["cift_adi"]
    yazi_kapak[u_:al_, s_:sa_] = True
    yazi_panel = maske_panele(yazi_kapak, ref_kutu_kapak, pw, ph)

    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, ref_dir / "ref.yuv", vw, vh)
    ry0, _, _ = panel_duzlemleri(ref_veri, kare_bayt, 0, ref_kutu, vw, vh)
    ham_k, lp_k, kalinti = lp_kalinti(ry0.astype(np.float32), sigma, altin_panel)
    log(f"LP kalinti: ham altin-arka kontrast {ham_k}, LP sonrasi {lp_k}, "
        f"oran {kalinti} (kucuk = cizgiler silindi)")

    # ------------------------------------------------------ ornek
    lid = a.ornek_id
    cift = ad_of.get(lid, lid)
    is_dir = out / "_is" / lid
    is_dir.mkdir(parents=True, exist_ok=True)
    kapak_yol, video_yol, kim = indir(lid, is_dir)
    o_meta = probe(video_yol)
    oak = o_meta["streams"][0]
    p2, q2 = (oak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    o_fps = round(float(p2) / float(q2), 3)
    if (int(oak["width"]), int(oak["height"])) != (vw, vh):
        raise SystemExit(f"HATA: cozunurluk {oak['width']}x{oak['height']} "
                         f"referanstan farkli -> DUR")
    kareler = kareleri_ac(video_yol, is_dir / "kare")
    if len(kareler) != len(ref_kareler) or abs(o_fps - ref_fps) > 0.01:
        raise SystemExit(f"HATA: kare eslemesi yok ({len(kareler)}/{o_fps}, "
                         f"referans {len(ref_kareler)}/{ref_fps}) -> DUR")
    kutular, tespit_basarisiz = kaynak_kutulari(kareler, ref_kutu)
    if kutular[0] is None:
        raise SystemExit("HATA: ornegin 0. karesinde panel bulunamadi -> DUR")
    kay_veri, _, kay_adet = yuv_ac(video_yol, is_dir / "kay.yuv", vw, vh)
    adet = min(ref_adet, kay_adet)

    # altin ofseti (V5 ile ayni yontem; kare 0'da kazanc 1)
    with Image.open(ref_kareler[0]) as im:
        ref_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
    with Image.open(kareler[0]) as im:
        kay_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
    ofset, altin_maske, altin_bilgi = altin_ofset_bul(
        ref_kare0, kay_kare0, ref_kutu, kutular[0], hedef_altin)
    dyuv = rgb_ofset_yuv(ofset) if ofset is not None else (0.0, 0.0, 0.0)
    altin_uv = altin_maske[::2, ::2] if altin_maske is not None else None

    ham = is_dir / "yeni.yuv"
    yapi_ist = []
    kazanc = kompozit_isik(ref_veri, kay_veri, kare_bayt, adet, ref_kutu,
                           kutular, vw, vh, ham, sigma, dyuv, altin_maske,
                           altin_uv, yapi_ist)
    yapi_en = round(max((y[1] for y in yapi_ist), default=0.0), 4)
    yapi_fark = round(max((abs(y[0]) for y in yapi_ist), default=0.0), 5)
    log(f"KAZANC YAPISI: altin-arka kazanc farki en buyuk {yapi_fark}, "
        f"kazanc genligine orani {yapi_en} (kucuk = sembol golgesi yok)")
    ad_dosya = cift.replace(" + ", "_").replace(" ", "_")
    yeni_video = out / f"{ad_dosya}_{lid}_video_V7.mp4"
    yuv_video_yaz(ham, yeni_video, vw, vh, ref_fps, ref_sure)
    k_min = round(min(k[0] for k in kazanc), 3)
    k_max = round(max(k[2] for k in kazanc), 3)
    log(f"Yeni video yazildi | kazanc araligi {k_min} - {k_max}")

    # ------------------------------------------------------ kontroller
    yeni_veri, _, yeni_adet = yuv_ac(yeni_video, is_dir / "geri.yuv", vw, vh)
    n = min(adet, yeni_adet)
    ref_kutular = [ref_kutu] * n
    dis_mae, olculen_kare = yuv_dis_mae(ref_veri, yeni_veri, kare_bayt,
                                        ref_kutu, vw, vh)
    ref_panel = parlaklik_egrisi(ref_veri, kare_bayt, n, ref_kutular, vw, vh)
    yeni_panel = parlaklik_egrisi(yeni_veri, kare_bayt, n, ref_kutular, vw, vh)
    own_panel = parlaklik_egrisi(kay_veri, kare_bayt, n, kutular, vw, vh)
    ref_yazi = parlaklik_egrisi(ref_veri, kare_bayt, n, ref_kutular, vw, vh,
                                yazi_panel)
    yeni_yazi = parlaklik_egrisi(yeni_veri, kare_bayt, n, ref_kutular, vw, vh,
                                 yazi_panel)
    own_yazi = parlaklik_egrisi(kay_veri, kare_bayt, n, kutular, vw, vh,
                                yazi_panel)
    panel_fark, panel_kare = fark_ozet(ref_panel, yeni_panel)
    yazi_fark, yazi_kare = fark_ozet(ref_yazi, yeni_yazi)
    onceki_panel, _ = fark_ozet(ref_panel, own_panel)
    onceki_yazi, _ = fark_ozet(ref_yazi, own_yazi)
    log(f"PANEL egri farki en buyuk {panel_fark} (kare {panel_kare}, esik "
        f"{PANEL_ESIK}) | V7 oncesi ayni fark {onceki_panel}")
    log(f"CIFT ADI egri farki en buyuk {yazi_fark} (kare {yazi_kare}, esik "
        f"{YAZI_ESIK}) | V7 oncesi ayni fark {onceki_yazi}")
    log(f"panel disi Y MAE {dis_mae:.4f} ({olculen_kare} kare)")

    kapak_yeni = out / f"{ad_dosya}_{lid}_kapak_V7.png"
    k0p = is_dir / "yeni_kare0.png"
    extract_frame(yeni_video, k0p, 0)
    with Image.open(k0p) as im:
        kapak_b = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    Image.fromarray(kapak_b).save(kapak_yeni)
    altin_yeni, _ = altin_ort(kapak_b)
    altin_fark = ([round(float(x - y), 2) for x, y in zip(altin_yeni, hedef_altin)]
                  if altin_yeni and hedef_altin else None)
    log(f"altin fark {altin_fark}")

    # ------------------------------------------------------ gorseller
    zamanlar = [round(ref_sure * i / 7, 3) for i in range(8)]
    ref_g, yeni_g = [], []
    (ref_dir / "sekiz").mkdir(exist_ok=True)
    (is_dir / "sekiz").mkdir(exist_ok=True)
    for i, z in enumerate(zamanlar):
        zz = min(z, max(ref_sure - 1.0 / ref_fps, 0))
        rp, yp = ref_dir / "sekiz" / f"{i}.png", is_dir / "sekiz" / f"{i}.png"
        extract_frame(ref_video, rp, zz)
        extract_frame(yeni_video, yp, zz)
        ref_g.append((f"{zz:.2f} sn", Image.open(rp).convert("RGB")))
        yeni_g.append((f"{zz:.2f} sn", Image.open(yp).convert("RGB")))

    kapak_kontrol_mae = None
    if not a.yerel_girdi:
        gor_k = gallery(api, a.referans_id)
        hedef = next((g for g in gor_k
                      if str(g.get("listing_image_id")) == KONTROL_KAPAK_ID), None)
        if hedef is None:
            raise SystemExit(f"HATA: canli kapak {KONTROL_KAPAK_ID} yok -> DUR")
        kyol = ref_dir / "kontrol.png"
        download(hedef.get("url_fullxfull") or hedef.get("url_570xN"), kyol)
        with Image.open(ref_kapak) as im_a, Image.open(kyol) as im_b:
            ra, rb = im_a.convert("RGB"), im_b.convert("RGB")
            if rb.size != ra.size:
                rb = rb.resize(ra.size, Image.Resampling.LANCZOS)
            kapak_kontrol_mae = mae(np.asarray(ra), np.asarray(rb))
        kota_sonra = api.remaining
        log(f"GORSEL KAPISI: MAE {kapak_kontrol_mae:.4f} (esik {GORSEL_KAPI_MAE})")
        if kapak_kontrol_mae >= GORSEL_KAPI_MAE:
            raise SystemExit("HATA: referans kapagi canli kapakla tutmadi -> DUR")

    boyut = karsilastirma(
        [(f"REFERANS  {ad_of.get(a.referans_id, '')}  {a.referans_id}", ref_g),
         (f"YENI  {cift}  {lid}", yeni_g)],
        out / "KARE_KARSILASTIRMA_V7.jpg")
    log(f"KARE_KARSILASTIRMA_V7.jpg {boyut[0]}x{boyut[1]}")

    egri_boyut = egri_ciz(out / "EGRI_V7.png", [
        {"ad": "REF panel", "deger": ref_panel},
        {"ad": "YENI panel", "deger": yeni_panel, "kesik": True},
        {"ad": "REF cift adi", "deger": ref_yazi},
        {"ad": "YENI cift adi", "deger": yeni_yazi, "kesik": True},
        {"ad": "V7 ONCESI (ilanin kendi) panel", "deger": own_panel},
        {"ad": "V7 ONCESI (ilanin kendi) cift adi", "deger": own_yazi}],
        f"Parlaklik egrileri (kare 0 = 1.0) - referans vs {cift}")
    log(f"EGRI_V7.png {egri_boyut[0]}x{egri_boyut[1]}")

    with (out / "EGRILER_V7.csv").open("w", newline="", encoding="utf-8") as fh:
        yz = csv.writer(fh)
        yz.writerow(["kare", "ref_panel", "yeni_panel", "kendi_panel",
                     "ref_cift_adi", "yeni_cift_adi", "kendi_cift_adi"])
        for i in range(n):
            yz.writerow([i, ref_panel[i], yeni_panel[i], own_panel[i],
                         ref_yazi[i], yeni_yazi[i], own_yazi[i]])

    ozet = {"calisma": "V7 KURU DENEME - Etsy'ye yazma YOK", "zaman": simdi(),
            "referans_id": a.referans_id, "referans_kimlik": ref_kim,
            "ornek_id": lid, "ornek_kimlik": kim, "cift": cift,
            "video": {"px": [vw, vh], "sure_sn": round(ref_sure, 3),
                      "fps": ref_fps, "kare": n},
            "panel_kutusu_kapak": ref_kutu_kapak, "panel_kutusu_video": ref_kutu,
            "panel_px": [pw, ph], "sigma": sigma,
            "lp_kalinti": {"ham_kontrast": ham_k, "lp_kontrast": lp_k,
                           "oran": kalinti},
            "kazanc_araligi": [k_min, k_max],
            "kazanc_yapi_farki": yapi_fark, "kazanc_yapi_orani": yapi_en,
            "panel_egri_farki": panel_fark, "panel_egri_esik": PANEL_ESIK,
            "panel_egri_gecti": bool(panel_fark is not None
                                     and panel_fark <= PANEL_ESIK),
            "panel_egri_farki_v7_oncesi": onceki_panel,
            "cift_adi_egri_farki": yazi_fark, "cift_adi_esik": YAZI_ESIK,
            "cift_adi_gecti": bool(yazi_fark is not None
                                   and yazi_fark <= YAZI_ESIK),
            "cift_adi_farki_v7_oncesi": onceki_yazi,
            "panel_disi_mae": round(dis_mae, 4),
            "panel_disi_mae_1_alti": dis_mae < 1.0,
            "olculen_kare": olculen_kare,
            "kutu_tespit_basarisiz_kare": tespit_basarisiz,
            "altin_esitleme": altin_bilgi, "altin_rgb": altin_yeni,
            "altin_fark": altin_fark, "referans_altin_rgb": hedef_altin,
            "kapak_kontrol_id": KONTROL_KAPAK_ID,
            "kapak_kontrol_mae": (round(kapak_kontrol_mae, 4)
                                  if kapak_kontrol_mae is not None else None),
            "kota_once": kota_once, "kota_sonra": kota_sonra,
            "gecen_sn": round(time.time() - t0, 1)}
    (out / "URETIM_SONUC_V7.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    md = [f"# Sablon V7 - isik alani aktarimi - {simdi()} UTC", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi.", "",
          "## Yontem", "",
          f"- LP: Gauss sigma {sigma} px (panel {pw}x{ph}), Y duzleminde.",
          f"- LP kalinti orani {kalinti} (altin-arka kontrast {ham_k} -> {lp_k}).",
          "- new(t) = own(t) * LP(ref(t))/LP(ref(0)) * LP(own(0))/LP(own(t))",
          f"- kazanc araligi {k_min} - {k_max} (kirpma {KAZANC_ALT}-{KAZANC_UST})",
          f"- kazancta sembol yapisi: fark {yapi_fark}, genlige oran {yapi_en}",
          "- B altin esitlemesi en sonda, yalniz altin maskede.",
          "- Tozlar own(t)'den gelir; kazanc disinda dokunulmaz.", "",
          "## Kontroller", "",
          "| kontrol | deger | esik | gecti | V7 oncesi |", "|---|---|---|---|---|",
          f"| panel parlaklik egrisi | {panel_fark} | {PANEL_ESIK} | "
          f"{'EVET' if panel_fark is not None and panel_fark <= PANEL_ESIK else 'HAYIR'} "
          f"| {onceki_panel} |",
          f"| cift adi egrisi | {yazi_fark} | {YAZI_ESIK} | "
          f"{'EVET' if yazi_fark is not None and yazi_fark <= YAZI_ESIK else 'HAYIR'} "
          f"| {onceki_yazi} |",
          f"| panel disi Y MAE | {round(dis_mae, 4)} | 1.0 | "
          f"{'EVET' if dis_mae < 1.0 else 'HAYIR'} | - |",
          f"| altin fark | {altin_fark} | 2.0 | - | - |"]
    (out / "TARIF_V7.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"panel_egri_farki": panel_fark,
                      "cift_adi_egri_farki": yazi_fark,
                      "panel_disi_mae": round(dis_mae, 4), "sigma": sigma,
                      "kota_once": kota_once, "kota_sonra": kota_sonra},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
