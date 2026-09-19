#!/usr/bin/env python3
"""POD sablon V6 - referans videonun ogelere ait gorunurluk egrisini aktarir.

V5 hatti aynen korunur (panel disi referansin baytlari, panel ici ilanin kendi
videosu, B altin esitlemesi). Ek olarak: referans videoda burc sembolleri ve
yazilar isikla birlikte sonup geri geliyor; bu egri, ilanin kendi ogelerine
KARE KARE ayni oranla uygulanir. Tozlar (statik oge maskeleri disindaki
hareketli altin parcaciklar) hic degistirilmez.

ADIM 1  Referans + ornek videoda oge bazli gorunurluk egrisi olcumu.
ADIM 2  Egri aktarimi ve yeni video.
ADIM 3  KARE_KARSILASTIRMA.jpg, EGRI.png.

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
from PIL import Image, ImageDraw
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
                           kutu_olcekle, panel_kutusu, yazi, yuv_ac,
                           yuv_dis_mae, yuv_video_yaz)
from pod_sablon_v5 import (altin_ofset_bul, kapak_ac, kaynak_kutulari,  # noqa: E402
                           kutu_boyut, mae, rgb_ofset_yuv, simdi)

# artwork_mask'in kapak uzayindaki sabit bolgeleri: ana sembol / cift adi /
# alt satir. Oge ayrimi bu bolgeler uzerinden yapilir.
BOLGE = {"ana": (650, 1735, 565, 1870),
         "cift_adi": (1775, 2165, 630, 1810),
         "two_souls": (2260, 2425, 900, 1540)}
EGRI_ESIK = 0.05        # ornek <-> referans kare basina en buyuk fark
GORSEL_KAPI_MAE = 2.0


def _bilesenler(maske):
    etiket, adet = ndimage.label(maske, structure=np.ones((3, 3), dtype=np.uint8))
    cikti = []
    for i, dilim in enumerate(ndimage.find_objects(etiket), start=1):
        if dilim is None:
            continue
        m = etiket[dilim] == i
        ky, kx = dilim
        h, w = ky.stop - ky.start, kx.stop - kx.start
        cikti.append({"no": i, "alan": int(m.sum()), "yuk": h, "gen": w,
                      "doluluk": float(m.sum()) / max(h * w, 1),
                      "dilim": dilim, "etiket": etiket})
    return cikti


def oge_maskeleri(kapak_a):
    """Kapaktan (2400x3000) oge maskelerini cikarir.

    Donus: {ad: kapak uzayinda bool maske}. Ayirt edilemeyen oge yazilmaz;
    hangi ogenin neyle birlestigi `not` alaninda raporlanir.
    """
    altin = artwork_mask(kapak_a)
    notlar, ogeler = [], {}
    if not altin.any():
        return ogeler, ["altin maskesi bos"], altin

    for ad, (u, al, s, sa) in BOLGE.items():
        bolge = np.zeros_like(altin)
        bolge[u:al, s:sa] = True
        yerel = altin & bolge
        if not yerel.any():
            notlar.append(f"{ad}: bolgede altin yok")
            continue
        if ad != "ana":
            ogeler[ad] = yerel
            continue
        # ana bolge: ana sembol / daire / iki kucuk burc sembolu
        comps = sorted(_bilesenler(yerel), key=lambda c: -c["alan"])
        if not comps:
            notlar.append("ana: bilesen yok")
            continue
        bolge_gen = sa - s
        daire = None
        for c in comps:
            if c["gen"] >= 0.55 * bolge_gen and c["doluluk"] < 0.30:
                daire = c
                break
        ana = next((c for c in comps if daire is None or c["no"] != daire["no"]),
                   None)
        kucukler = [c for c in comps
                    if c is not ana and (daire is None or c["no"] != daire["no"])
                    and c["alan"] >= 0.002 * yerel.sum()][:2]

        def maske(c):
            m = np.zeros_like(altin)
            m[c["dilim"]] = c["etiket"][c["dilim"]] == c["no"]
            return m

        if daire is not None:
            ogeler["daire_cizgisi"] = maske(daire)
        else:
            notlar.append("daire cizgisi ayri bilesen degil "
                          "(ana sembolle birlesik sayildi)")
        if ana is not None:
            ogeler["ana_sembol"] = maske(ana)
        for i, c in enumerate(kucukler, start=1):
            ogeler[f"kucuk_burc_{i}"] = maske(c)
        if len(kucukler) < 2:
            notlar.append(f"kucuk burc sembolu {len(kucukler)} adet ayrildi "
                          "(digeri ana sembolle birlesik)")
    return ogeler, notlar, altin


def maske_panele(maske_kapak, kutu_kapak, pw, ph):
    """Kapak uzayindaki maskeyi panel yerel (video) cozunurlugune indirir."""
    kes = maske_kapak[kutu_kapak["ust"]:kutu_kapak["alt"] + 1,
                      kutu_kapak["sol"]:kutu_kapak["sag"] + 1]
    return np.asarray(Image.fromarray(kes.astype(np.uint8) * 255).resize(
        (pw, ph), Image.Resampling.NEAREST), dtype=np.uint8) > 127


def panel_y(veri, kare_bayt, i, kutu, w, h):
    blok = veri[i * kare_bayt:i * kare_bayt + w * h]
    y = blok.reshape(h, w)
    return y[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]


def egriler_olc(veri, kare_bayt, adet, kutular, w, h, maskeler, altin_hepsi):
    """Her oge icin kare kare gorunurluk egrisi.

    gorunurluk(i) = (oge_ort(i) - arka_plan(i)) / (oge_ort(0) - arka_plan(0))
    ham_oran(i)   = oge_ort(i) / oge_ort(0)      (Serdar'in tarifi)
    Arka plan, panel icinde altin maskesine girmeyen piksellerin medyanidir.
    """
    sonuc = {ad: {"gorunurluk": [], "ham_oran": []} for ad in maskeler}
    taban = {}
    for i in range(adet):
        k = kutular[i] if kutular else None
        if k is None:
            for ad in maskeler:
                sonuc[ad]["gorunurluk"].append(None)
                sonuc[ad]["ham_oran"].append(None)
            continue
        p = panel_y(veri, kare_bayt, i, k, w, h).astype(np.float32)
        arka = float(np.median(p[~altin_hepsi])) if (~altin_hepsi).any() else 0.0
        for ad, m in maskeler.items():
            ort = float(p[m].mean()) if m.any() else 0.0
            if i == 0:
                taban[ad] = (ort, arka)
            ort0, arka0 = taban[ad]
            payda = max(ort0 - arka0, 1e-6)
            sonuc[ad]["gorunurluk"].append(round((ort - arka) / payda, 4))
            sonuc[ad]["ham_oran"].append(round(ort / max(ort0, 1e-6), 4))
    return sonuc


def egri_ozet(egri):
    """Sonme baslangici / en dusuk deger / geri donus karelerini cikarir."""
    g = [x for x in egri if x is not None]
    if not g:
        return {}
    en_dusuk = min(g)
    en_dusuk_kare = g.index(en_dusuk)
    basla = next((i for i, x in enumerate(g) if x < 0.90), None)
    geri = None
    if basla is not None:
        for i in range(en_dusuk_kare, len(g)):
            if g[i] >= 0.90:
                geri = i
                break
    return {"sonme_basi_kare": basla, "en_dusuk": round(en_dusuk, 3),
            "en_dusuk_kare": en_dusuk_kare, "geri_donus_kare": geri,
            "son_kare": round(g[-1], 3)}


def kompozit_egrili(ref_veri, kay_veri, kare_bayt, adet, ref_kutu, kutular,
                    w, h, cikti, dyuv, altin_maske, altin_uv, maskeler,
                    maskeler_uv, hedef_egri, altin_hepsi):
    """V5 kompoziti + oge bazli egri aktarimi.

    Her karede: panel ici ornegin kendi videosundan gelir (tozlar dahil).
    Statik oge maskelerinde piksel degeri, ornegin 0. karesindeki gorunumunun
    referans egrisiyle olceklenmis hali ile degistirilir:
        deger(i) = arka_plan(i) + (deger_0 - arka_plan_0) * egri_ref(i)
    Boylece oge sonup geri gelir, panel disi ve tozlar dokunulmadan kalir.
    """
    pw, ph = kutu_boyut(ref_kutu)
    ru, rs = ref_kutu["ust"], ref_kutu["sol"]
    taban = {}
    uygulanan = 0
    with open(cikti, "wb") as fh:
        for i in range(adet):
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            k = kutular[i] if i < len(kutular) else None
            if k is None:
                blok.tofile(fh)
                continue
            kay = kay_veri[i * kare_bayt:(i + 1) * kare_bayt]
            y = blok[:w * h].reshape(h, w)
            u = blok[w * h:w * h + w * h // 4].reshape(h // 2, w // 2)
            v = blok[w * h + w * h // 4:].reshape(h // 2, w // 2)
            ky = kay[:w * h].reshape(h, w)
            ku = kay[w * h:w * h + w * h // 4].reshape(h // 2, w // 2)
            kv = kay[w * h + w * h // 4:].reshape(h // 2, w // 2)
            py = ky[k["ust"]:k["ust"] + ph, k["sol"]:k["sol"] + pw].astype(np.float32)
            pu = ku[k["ust"] // 2:k["ust"] // 2 + ph // 2,
                    k["sol"] // 2:k["sol"] // 2 + pw // 2].astype(np.float32)
            pv = kv[k["ust"] // 2:k["ust"] // 2 + ph // 2,
                    k["sol"] // 2:k["sol"] // 2 + pw // 2].astype(np.float32)
            if altin_maske is not None:
                py[altin_maske] += dyuv[0]
                pu[altin_uv] += dyuv[1]
                pv[altin_uv] += dyuv[2]
            # --- oge egrisi aktarimi
            arka_y = float(np.median(py[~altin_hepsi])) if (~altin_hepsi).any() else 0.0
            arka_u = float(np.median(pu[~altin_hepsi[::2, ::2]]))
            arka_v = float(np.median(pv[~altin_hepsi[::2, ::2]]))
            if i == 0:
                taban["y"], taban["u"], taban["v"] = py.copy(), pu.copy(), pv.copy()
                taban["arka"] = (arka_y, arka_u, arka_v)
            else:
                a0y, a0u, a0v = taban["arka"]
                for ad, m in maskeler.items():
                    r = hedef_egri.get(ad, [None] * adet)[i]
                    if r is None or not m.any():
                        continue
                    muv = maskeler_uv[ad]
                    py[m] = arka_y + (taban["y"][m] - a0y) * r
                    pu[muv] = arka_u + (taban["u"][muv] - a0u) * r
                    pv[muv] = arka_v + (taban["v"][muv] - a0v) * r
                uygulanan += 1
            y[ru:ru + ph, rs:rs + pw] = np.rint(np.clip(py, 16, 235)).astype(np.uint8)
            u[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                np.rint(np.clip(pu, 16, 240)).astype(np.uint8)
            v[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                np.rint(np.clip(pv, 16, 240)).astype(np.uint8)
            blok.tofile(fh)
    return uygulanan


def egri_ciz(hedef, seriler, baslik, genislik=1800, yukseklik=1000):
    """Oge egrilerini ust uste cizer (referans duz, yeni kesikli)."""
    renkler = [(196, 62, 62), (46, 116, 196), (34, 142, 82), (182, 122, 30),
               (128, 76, 168), (60, 60, 60), (0, 150, 160)]
    sol, ust, sag, alt = 110, 90, 40, 90
    tuval = Image.new("RGB", (genislik, yukseklik), (250, 250, 250))
    ciz = ImageDraw.Draw(tuval)
    gw, gh = genislik - sol - sag, yukseklik - ust - alt
    n = max(len(s["deger"]) for s in seriler)
    ciz.rectangle([sol, ust, sol + gw, ust + gh], outline=(190, 190, 190))
    for t in range(0, 11, 2):
        yy = ust + gh - int(gh * t / 10)
        ciz.line([sol, yy, sol + gw, yy], fill=(225, 225, 225))
        yazi(ciz, (sol - 70, yy - 14), f"{t / 10:.1f}", 26, (90, 90, 90))
    for kx in range(0, n, max(n // 8, 1)):
        xx = sol + int(gw * kx / max(n - 1, 1))
        ciz.line([xx, ust, xx, ust + gh], fill=(235, 235, 235))
        yazi(ciz, (xx - 20, ust + gh + 10), str(kx), 24, (90, 90, 90))
    for i, s in enumerate(seriler):
        renk = renkler[i % len(renkler)]
        nokta = []
        for kx, d in enumerate(s["deger"]):
            if d is None:
                continue
            xx = sol + int(gw * kx / max(n - 1, 1))
            yy = ust + gh - int(gh * min(max(d, 0.0), 1.2) / 1.2)
            nokta.append((xx, yy))
        if len(nokta) > 1:
            if s.get("kesik"):
                for j in range(0, len(nokta) - 1, 2):
                    ciz.line([nokta[j], nokta[j + 1]], fill=renk, width=4)
            else:
                ciz.line(nokta, fill=renk, width=3)
        yazi(ciz, (sol + 12, ust + 12 + i * 32), s["ad"], 26, renk)
    yazi(ciz, (sol, 30), baslik, 34, (30, 30, 30))
    yazi(ciz, (sol, yukseklik - 44), "yatay: kare | dikey: gorunurluk orani "
         "(duz = referans, kesik = yeni)", 26, (90, 90, 90))
    tuval.save(hedef, "PNG")
    return tuval.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ornek-id", required=True)
    ap.add_argument("--referans-id", default=REFERANS_ID)
    ap.add_argument("--yerel-girdi", default="")
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
    ref_kareler = kareleri_ac(ref_video, ref_dir / "kare")
    hedef_altin, _ = altin_ort(ref_kapak_a)
    log(f"Referans video id {ref_kim.get('video_id')} | {vw}x{vh}, "
        f"{ref_sure:.2f} sn, {ref_fps} fps, {len(ref_kareler)} kare | "
        f"panel {ref_kutu_kapak} -> {ref_kutu}")

    # ADIM 1a: referans oge maskeleri + egrileri
    ref_ogeler_k, ref_notlar, ref_altin_k = oge_maskeleri(ref_kapak_a)
    if not ref_ogeler_k:
        raise SystemExit("HATA: referansta oge ayrilamadi -> DUR")
    ref_maske = {ad: maske_panele(m, ref_kutu_kapak, pw, ph)
                 for ad, m in ref_ogeler_k.items()}
    ref_altin_panel = maske_panele(ref_altin_k, ref_kutu_kapak, pw, ph)
    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, ref_dir / "ref.yuv", vw, vh)
    ref_kutular = [ref_kutu] * ref_adet
    ref_egri = egriler_olc(ref_veri, kare_bayt, ref_adet, ref_kutular, vw, vh,
                           ref_maske, ref_altin_panel)
    # tozlar: altin maskesinde olup hicbir ogeye girmeyen pikseller (olcum icin)
    oge_birlesim = np.zeros((ph, pw), dtype=bool)
    for m in ref_maske.values():
        oge_birlesim |= m
    toz_maske = ref_altin_panel & ~ndimage.binary_dilation(oge_birlesim,
                                                           iterations=3)
    if toz_maske.any():
        ref_egri.update(egriler_olc(ref_veri, kare_bayt, ref_adet, ref_kutular,
                                    vw, vh, {"tozlar": toz_maske},
                                    ref_altin_panel))
    for ad, e in ref_egri.items():
        o = egri_ozet(e["gorunurluk"])
        log(f"REF {ad}: sonme {o.get('sonme_basi_kare')} | en dusuk "
            f"{o.get('en_dusuk')} (kare {o.get('en_dusuk_kare')}) | geri "
            f"{o.get('geri_donus_kare')} | son {o.get('son_kare')}")
    for n in ref_notlar:
        log(f"REF NOT: {n}")

    # ------------------------------------------------------ ornek
    lid = a.ornek_id
    cift = ad_of.get(lid, lid)
    is_dir = out / "_is" / lid
    is_dir.mkdir(parents=True, exist_ok=True)
    kapak_yol, video_yol, kim = indir(lid, is_dir)
    o_meta = probe(video_yol)
    oak = o_meta["streams"][0]
    o_sure = float(o_meta["format"]["duration"])
    p2, q2 = (oak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    o_fps = round(float(p2) / float(q2), 3)
    if (int(oak["width"]), int(oak["height"])) != (vw, vh):
        raise SystemExit(f"HATA: cozunurluk {oak['width']}x{oak['height']} "
                         f"referanstan farkli -> DUR")
    kareler = kareleri_ac(video_yol, is_dir / "kare")
    if len(kareler) != len(ref_kareler) or abs(o_fps - ref_fps) > 0.01:
        raise SystemExit(f"HATA: kare eslemesi yok ({len(kareler)} kare/{o_fps} "
                         f"fps, referans {len(ref_kareler)}/{ref_fps}) -> DUR")
    kapak_a = kapak_ac(kapak_yol)
    kutu_kapak = panel_kutusu(kapak_a)
    if kutu_kapak is None:
        raise SystemExit("HATA: ornek kapaginda panel bulunamadi -> DUR")
    kutular, tespit_basarisiz = kaynak_kutulari(kareler, ref_kutu)
    if kutular[0] is None:
        raise SystemExit("HATA: ornegin 0. karesinde panel bulunamadi -> DUR")

    # oge maskeleri ILANIN KENDI kapagindan
    ogeler_k, notlar, altin_k = oge_maskeleri(kapak_a)
    ortak = [ad for ad in ref_maske if ad in ogeler_k]
    maskeler = {ad: maske_panele(ogeler_k[ad], kutu_kapak, pw, ph) for ad in ortak}
    maskeler_uv = {ad: m[::2, ::2] for ad, m in maskeler.items()}
    altin_panel = maske_panele(altin_k, kutu_kapak, pw, ph)
    log(f"{cift}: oge {sorted(maskeler)} | referansta olup ornekte olmayan "
        f"{sorted(set(ref_maske) - set(ogeler_k))}")
    for n in notlar:
        log(f"ORNEK NOT: {n}")

    # ADIM 1b: ornegin KENDI (V5 oncesi) egrisi - fark raporu icin
    kay_veri, _, kay_adet = yuv_ac(video_yol, is_dir / "kay.yuv", vw, vh)
    adet = min(ref_adet, kay_adet)
    v5_egri = egriler_olc(kay_veri, kare_bayt, adet, kutular, vw, vh,
                          maskeler, altin_panel)

    # ADIM 2: altin ofseti (V5 ile ayni) + egri aktarimi
    with Image.open(ref_kareler[0]) as im:
        ref_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
    with Image.open(kareler[0]) as im:
        kay_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
    ofset, altin_maske, altin_bilgi = altin_ofset_bul(
        ref_kare0, kay_kare0, ref_kutu, kutular[0], hedef_altin)
    dyuv = rgb_ofset_yuv(ofset) if ofset is not None else (0.0, 0.0, 0.0)
    altin_uv = altin_maske[::2, ::2] if altin_maske is not None else None
    hedef_egri = {ad: ref_egri[ad]["gorunurluk"] for ad in maskeler}
    ham = is_dir / "yeni.yuv"
    uygulanan = kompozit_egrili(ref_veri, kay_veri, kare_bayt, adet, ref_kutu,
                                kutular, vw, vh, ham, dyuv, altin_maske,
                                altin_uv, maskeler, maskeler_uv, hedef_egri,
                                altin_panel)
    ad_dosya = cift.replace(" + ", "_").replace(" ", "_")
    yeni_video = out / f"{ad_dosya}_{lid}_video_V6.mp4"
    yuv_video_yaz(ham, yeni_video, vw, vh, ref_fps, ref_sure)
    log(f"Yeni video yazildi ({uygulanan} karede egri uygulandi)")

    # ------------------------------------------------------ kontroller
    yeni_veri, _, yeni_adet = yuv_ac(yeni_video, is_dir / "geri.yuv", vw, vh)
    dis_mae, olculen_kare = yuv_dis_mae(ref_veri, yeni_veri, kare_bayt,
                                        ref_kutu, vw, vh)
    yeni_egri = egriler_olc(yeni_veri, kare_bayt, min(adet, yeni_adet),
                            [ref_kutu] * min(adet, yeni_adet), vw, vh,
                            maskeler, altin_panel)
    farklar = {}
    for ad in maskeler:
        r = ref_egri[ad]["gorunurluk"]
        y = yeni_egri[ad]["gorunurluk"]
        d = [abs(x - z) for x, z in zip(r, y) if x is not None and z is not None]
        farklar[ad] = round(max(d), 4) if d else None
    en_buyuk_fark = max([v for v in farklar.values() if v is not None] or [None])
    log(f"EGRI FARKI (oge basina en buyuk): {farklar}")

    kapak_yeni = out / f"{ad_dosya}_{lid}_kapak_V6.png"
    k0 = is_dir / "yeni_kare0.png"
    extract_frame(yeni_video, k0, 0)
    with Image.open(k0) as im:
        kapak_b = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    Image.fromarray(kapak_b).save(kapak_yeni)
    son = is_dir / "yeni_son.png"
    extract_frame(yeni_video, son, max(ref_sure - 1.0 / ref_fps, 0))
    with Image.open(son) as im:
        son_a = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    kapak_kare0_mae = round(mae(kapak_b, kapak_b), 4)
    kapak_son_mae = round(mae(kapak_b, son_a), 4)
    ref_son = ref_dir / "ref_son.png"
    extract_frame(ref_video, ref_son, max(ref_sure - 1.0 / ref_fps, 0))
    with Image.open(ref_son) as im:
        ref_son_a = np.asarray(im.convert("RGB").resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    ref_kapak_son_mae = round(mae(ref_kapak_a, ref_son_a), 4)
    altin_yeni, _ = altin_ort(kapak_b)
    altin_fark = ([round(float(x - y), 2) for x, y in zip(altin_yeni, hedef_altin)]
                  if altin_yeni and hedef_altin else None)
    log(f"panel disi Y MAE {dis_mae:.4f} ({olculen_kare} kare) | kapak-son kare "
        f"MAE yeni {kapak_son_mae} / referans {ref_kapak_son_mae} | altin fark "
        f"{altin_fark}")

    # ------------------------------------------------------ ADIM 3: gorseller
    ref_orta_dir = ref_dir / "sekiz"
    yeni_dir = is_dir / "sekiz"
    ref_orta_dir.mkdir(exist_ok=True)
    yeni_dir.mkdir(exist_ok=True)
    zamanlar = [round(ref_sure * i / 7, 3) for i in range(8)]
    ref_g, yeni_g = [], []
    for i, z in enumerate(zamanlar):
        zz = min(z, max(ref_sure - 1.0 / ref_fps, 0))
        rp, yp = ref_orta_dir / f"{i}.png", yeni_dir / f"{i}.png"
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
        out / "KARE_KARSILASTIRMA.jpg")
    log(f"KARE_KARSILASTIRMA.jpg {boyut[0]}x{boyut[1]}")

    seriler = []
    for ad in sorted(maskeler):
        seriler.append({"ad": f"REF {ad}", "deger": ref_egri[ad]["gorunurluk"]})
        seriler.append({"ad": f"YENI {ad}", "deger": yeni_egri[ad]["gorunurluk"],
                        "kesik": True})
    egri_boyut = egri_ciz(out / "EGRI.png", seriler,
                          f"Oge gorunurluk egrileri - referans vs {cift}")
    log(f"EGRI.png {egri_boyut[0]}x{egri_boyut[1]}")

    with (out / "EGRILER.csv").open("w", newline="", encoding="utf-8") as fh:
        yz = csv.writer(fh)
        basliklar = ["kare"]
        for ad in sorted(ref_egri):
            basliklar += [f"ref_{ad}", f"ref_ham_{ad}"]
        for ad in sorted(maskeler):
            basliklar += [f"v5_{ad}", f"yeni_{ad}"]
        yz.writerow(basliklar)
        for i in range(adet):
            satir = [i]
            for ad in sorted(ref_egri):
                satir += [ref_egri[ad]["gorunurluk"][i],
                          ref_egri[ad]["ham_oran"][i]]
            for ad in sorted(maskeler):
                satir += [v5_egri[ad]["gorunurluk"][i] if i < len(
                    v5_egri[ad]["gorunurluk"]) else None,
                    yeni_egri[ad]["gorunurluk"][i] if i < len(
                        yeni_egri[ad]["gorunurluk"]) else None]
            yz.writerow(satir)

    ozet = {"calisma": "V6 KURU DENEME - Etsy'ye yazma YOK", "zaman": simdi(),
            "referans_id": a.referans_id, "referans_kimlik": ref_kim,
            "ornek_id": lid, "ornek_kimlik": kim, "cift": cift,
            "video": {"px": [vw, vh], "sure_sn": round(ref_sure, 3),
                      "fps": ref_fps, "kare": adet},
            "panel_kutusu_kapak": ref_kutu_kapak, "panel_kutusu_video": ref_kutu,
            "oge_notlari": {"referans": ref_notlar, "ornek": notlar},
            "referans_egri_ozet": {ad: egri_ozet(e["gorunurluk"])
                                   for ad, e in ref_egri.items()},
            "ornek_v5_egri_ozet": {ad: egri_ozet(e["gorunurluk"])
                                   for ad, e in v5_egri.items()},
            "yeni_egri_ozet": {ad: egri_ozet(e["gorunurluk"])
                               for ad, e in yeni_egri.items()},
            "egri_farki": farklar, "egri_farki_esik": EGRI_ESIK,
            "egri_farki_gecti": bool(en_buyuk_fark is not None
                                     and en_buyuk_fark <= EGRI_ESIK),
            "panel_disi_mae": round(dis_mae, 4),
            "panel_disi_mae_1_alti": dis_mae < 1.0,
            "olculen_kare": olculen_kare,
            "kutu_tespit_basarisiz_kare": tespit_basarisiz,
            "kapak_kare0_mae": kapak_kare0_mae,
            "kapak_son_kare_mae_yeni": kapak_son_mae,
            "kapak_son_kare_mae_referans": ref_kapak_son_mae,
            "altin_esitleme": altin_bilgi, "altin_rgb": altin_yeni,
            "altin_fark": altin_fark, "referans_altin_rgb": hedef_altin,
            "kapak_kontrol_id": KONTROL_KAPAK_ID,
            "kapak_kontrol_mae": (round(kapak_kontrol_mae, 4)
                                  if kapak_kontrol_mae is not None else None),
            "kota_once": kota_once, "kota_sonra": kota_sonra,
            "gecen_sn": round(time.time() - t0, 1)}
    (out / "URETIM_SONUC_V6.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    md = [f"# Sablon V6 - oge gorunurluk egrisi aktarimi - {simdi()} UTC", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi.", "",
          "## Referans animasyon", "",
          "| oge | sonme basi (kare) | en dusuk | en dusuk kare | geri donus (kare) | son kare |",
          "|---|---|---|---|---|---|"]
    for ad, e in ref_egri.items():
        o = egri_ozet(e["gorunurluk"])
        md.append(f"| {ad} | {o.get('sonme_basi_kare')} | {o.get('en_dusuk')} | "
                  f"{o.get('en_dusuk_kare')} | {o.get('geri_donus_kare')} | "
                  f"{o.get('son_kare')} |")
    md += ["", "## Yeni ornek egri farki (referansa gore kare basina en buyuk)",
           "", "| oge | en buyuk fark | esik | gecti |", "|---|---|---|---|"]
    for ad, f in farklar.items():
        md.append(f"| {ad} | {f} | {EGRI_ESIK} | "
                  f"{'EVET' if f is not None and f <= EGRI_ESIK else 'HAYIR'} |")
    md += ["", f"- panel disi Y MAE: {round(dis_mae, 4)} (esik 1.0)",
           f"- kapak <-> son kare MAE: yeni {kapak_son_mae}, "
           f"referans {ref_kapak_son_mae}",
           f"- altin fark: {altin_fark}",
           "- tozlar: statik oge maskeleri disinda kaldi, degistirilmedi."]
    (out / "TARIF_V6.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"egri_farki": farklar, "panel_disi_mae": round(dis_mae, 4),
                      "kota_once": kota_once, "kota_sonra": kota_sonra},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
