#!/usr/bin/env python3
"""POD sablon V5 - poster icerigi ilanin KENDI videosundan gelir.

V4'ten fark: panel icine baski dosyasi (ORIGINAL_HIGH_RES) yerlestirilmez.
Ilanin kendi videosundaki panel icerigi, referans videonun panel kutusuna
BIREBIR (olcek yok) tasinir. Panel disi referansin baytlaridir; kompozit ham
yuv420p duzleminde yapilir.

ADIM 1  77 ilani sinifla (yalniz GET): S1 panel boyutu referansla ayni,
        S2 boyut/oran farkli, S3 video 0. karesi kendi kapagiyla uyumsuz.
ADIM 2  S1 ornekleri icin yeni video + kapak uret.
ADIM 3  KARSILASTIRMA_V5.jpg (referans + 3 ornek; 4 sutun).

Etsy'ye YAZMA YOK: yalniz GET cagrilari yapilir, --apply reddedilir.
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import download, gallery, videos, video_url  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, KONTROL_KAPAK_ID, REFERANS_ID,  # noqa: E402
                           altin_ort, cift_hizala, kareleri_ac, karsilastirma,
                           kutu_olcekle, ocr, panel_kutusu, yuv_ac,
                           yuv_dis_mae, yuv_video_yaz)

BOYUT_TOLERANS = 5      # S1 icin panel boyutu toleransi (kapak uzayi, px)
S3_MAE = 20.0           # video 0. karesi <-> kendi kapagi uyumsuzluk esigi
GORSEL_KAPI_MAE = 2.0   # referans satiri <-> canli kapak esigi


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def kutu_boyut(k):
    return (k["sag"] - k["sol"] + 1, k["alt"] - k["ust"] + 1)


def kapak_ac(yol):
    with Image.open(yol) as im:
        return np.asarray(im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS),
                          dtype=np.uint8)


def mae(a, b):
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


def rgb_ofset_yuv(ofset):
    """RGB toplamsal ofseti BT.601 sinirli aralik Y/U/V ofsetine cevirir."""
    dr, dg, db = (float(x) for x in ofset)
    return (0.257 * dr + 0.504 * dg + 0.098 * db,
            -0.148 * dr - 0.291 * dg + 0.439 * db,
            0.439 * dr - 0.368 * dg - 0.071 * db)


def kaynak_kutulari(kareler, ref_kutu, tani_list=None):
    """Ornek videonun her karesinde panel kutusunu bulur.

    Kutu boyutu referansin kutusuna esitlenir: tespit edilen sol-ust kose
    baz alinip referans boyutu kadar kirpilir. Tespit basarisiz olursa bir
    onceki karenin kutusu kullanilir.
    """
    pw, ph = kutu_boyut(ref_kutu)
    kutular, basarisiz, onceki = [], 0, None
    for p in kareler:
        with Image.open(p) as im:
            a = np.asarray(im.convert("RGB"), dtype=np.uint8)
        k = panel_kutusu(a)
        if k is None:
            basarisiz += 1
            if onceki is None:
                kutular.append(None)
                continue
            k = onceki
        else:
            k = cift_hizala(k)
        h, w = a.shape[:2]
        ust = min(max(k["ust"], 0), max(h - ph, 0)) // 2 * 2
        sol = min(max(k["sol"], 0), max(w - pw, 0)) // 2 * 2
        kutu = {"ust": ust, "sol": sol, "alt": ust + ph - 1, "sag": sol + pw - 1}
        if kutu["alt"] >= h or kutu["sag"] >= w:
            kutular.append(None)
            continue
        onceki = kutu
        kutular.append(kutu)
        if tani_list is not None:
            tani_list.append({"ust": ust, "sol": sol})
    return kutular, basarisiz


def altin_ofset_bul(ref_kare0, kay_kare0, ref_kutu, kay_kutu0, hedef_altin,
                    dongu=4):
    """Panel ici altin maskesinde uygulanacak RGB ofsetini olcerek bulur.

    Olcum, uretilecek kapagin ta kendisi uzerinde yapilir: yeni videonun
    0. karesi 2400x3000'e buyutulur ve altin ortalamasi referansla
    karsilastirilir.
    """
    pw, ph = kutu_boyut(ref_kutu)
    doseme0 = kay_kare0[kay_kutu0["ust"]:kay_kutu0["ust"] + ph,
                        kay_kutu0["sol"]:kay_kutu0["sol"] + pw].astype(np.float32)

    def kapak_uret(ofset, maske):
        kare = ref_kare0.copy()
        d = doseme0.copy()
        if maske is not None:
            d[maske] += np.asarray(ofset, dtype=np.float32)
        kare[ref_kutu["ust"]:ref_kutu["ust"] + ph,
             ref_kutu["sol"]:ref_kutu["sol"] + pw] = np.rint(
                 np.clip(d, 0, 255)).astype(np.uint8)
        return np.asarray(Image.fromarray(kare).resize(
            KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)

    ilk_kapak = kapak_uret((0.0, 0.0, 0.0), None)
    kapak_maske = artwork_mask(ilk_kapak)
    if not kapak_maske.any():
        return None, None, {"uygulandi": False, "not": "altin maskesi bos"}
    # kapak uzayindaki maskeyi panel yerel koordinatina indir
    ky = int(round(ref_kutu["ust"] * KAPAK[1] / ref_kare0.shape[0]))
    kx = int(round(ref_kutu["sol"] * KAPAK[0] / ref_kare0.shape[1]))
    kh = int(round(ph * KAPAK[1] / ref_kare0.shape[0]))
    kw = int(round(pw * KAPAK[0] / ref_kare0.shape[1]))
    kes = kapak_maske[ky:ky + kh, kx:kx + kw]
    maske = np.asarray(Image.fromarray(kes.astype(np.uint8) * 255).resize(
        (pw, ph), Image.Resampling.NEAREST), dtype=np.uint8) > 127
    if not maske.any():
        return None, None, {"uygulandi": False, "not": "panel maskesi bos"}

    ofset = np.zeros(3, dtype=np.float32)
    gecmis = []
    for _ in range(dongu):
        kapak = kapak_uret(ofset, maske)
        olculen, _ = altin_ort(kapak)
        if olculen is None:
            return None, None, {"uygulandi": False, "not": "altin olculemedi"}
        fark = np.asarray(hedef_altin, dtype=np.float32) - np.asarray(
            olculen, dtype=np.float32)
        gecmis.append({"altin": olculen, "fark": [round(float(x), 2) for x in fark]})
        if np.all(np.abs(fark) < 0.2):
            break
        ofset = ofset + fark
    return ofset, maske, {"uygulandi": True,
                          "ofset_rgb": [round(float(x), 2) for x in ofset],
                          "gecmis": gecmis}


def yuv_kompozit_akis(ref_veri, kay_veri, kare_bayt, adet, ref_kutu, kutular,
                      w, h, cikti, dyuv, maske, maske_uv):
    """Her karede panel icini ornek videodan alip referans kareye tasir.

    Panel DISI bayt bayt referansin verisidir; hicbir donusume ugramaz.
    """
    pw, ph = kutu_boyut(ref_kutu)
    ru, rs = ref_kutu["ust"], ref_kutu["sol"]
    tasinan = 0
    with open(cikti, "wb") as fh:
        for i in range(adet):
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            k = kutular[i] if i < len(kutular) else None
            if k is not None:
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
                if maske is not None:
                    py[maske] += dyuv[0]
                    pu[maske_uv] += dyuv[1]
                    pv[maske_uv] += dyuv[2]
                y[ru:ru + ph, rs:rs + pw] = np.rint(np.clip(py, 16, 235)).astype(np.uint8)
                u[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                    np.rint(np.clip(pu, 16, 240)).astype(np.uint8)
                v[ru // 2:ru // 2 + ph // 2, rs // 2:rs // 2 + pw // 2] = \
                    np.rint(np.clip(pv, 16, 240)).astype(np.uint8)
                tasinan += 1
            blok.tofile(fh)
    return tasinan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ornek-ids", required=True)
    ap.add_argument("--uretmeyen-ids", default="")
    ap.add_argument("--referans-id", default=REFERANS_ID)
    ap.add_argument("--yerel-girdi", default="")
    ap.add_argument("--sinif-limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: bu hat Etsy'ye YAZMAZ; --apply reddedildi.")

    t0 = time.time()
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    ad_of = {str(r["id"]): (r.get("pair") or str(r["id"])) for r in katalog}
    ornekler = [x.strip() for x in a.ornek_ids.split(",") if x.strip()]
    uretmeyen = [x.strip() for x in a.uretmeyen_ids.split(",") if x.strip()]
    kota_once = kota_sonra = None

    # ------------------------------------------------------------ girdiler
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

    # ------------------------------------------------- referans (sablon)
    ref_dir = out / "_is" / "REFERANS"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_kapak, ref_video, ref_kim = indir(a.referans_id, ref_dir)
    ref_meta = probe(ref_video)
    rak = ref_meta["streams"][0]
    vw, vh = int(rak["width"]), int(rak["height"])
    ref_sure = float(ref_meta["format"]["duration"])
    pay, payda = (rak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    ref_fps = round(float(pay) / float(payda), 3)
    ref_kapak_a = kapak_ac(ref_kapak)
    ref_kutu_kapak = panel_kutusu(ref_kapak_a)
    if ref_kutu_kapak is None:
        raise SystemExit("HATA: referans kapaginda panel bulunamadi -> DUR")
    ref_kutu = cift_hizala(kutu_olcekle(ref_kutu_kapak, KAPAK[1], vh, KAPAK[0], vw))
    ref_kareler = kareleri_ac(ref_video, ref_dir / "kare")
    hedef_altin, _ = altin_ort(ref_kapak_a)
    log(f"Referans {vw}x{vh}, {ref_sure:.2f} sn, {ref_fps} fps, "
        f"{len(ref_kareler)} kare | panel kapakta {ref_kutu_kapak} -> "
        f"videoda {ref_kutu} | altin RGB {hedef_altin}")
    ref_w, ref_h = kutu_boyut(ref_kutu_kapak)

    # ------------------------------------------------------ ADIM 1: sinif
    hepsi = [str(r["id"]) for r in katalog if str(r["id"]) != a.referans_id]
    if a.sinif_limit:
        hepsi = hepsi[:a.sinif_limit]
    sinif_yol = out / "SINIF_77.csv"
    siniflar, satirlar_csv = {}, []
    toplam = len(hepsi)
    for n, lid in enumerate(hepsi, start=1):
        cift = ad_of.get(lid, lid)
        kayit = {"listing_id": lid, "cift": cift, "sinif": "?", "kutu": "",
                 "panel_w": "", "panel_h": "", "kare0_kapak_mae": "", "not": ""}
        try:
            is_dir = out / "_is" / lid
            is_dir.mkdir(parents=True, exist_ok=True)
            kapak_yol, video_yol, _ = indir(lid, is_dir)
            kapak_a = kapak_ac(kapak_yol)
            kare0 = is_dir / "kare0.png"
            extract_frame(video_yol, kare0, 0)
            with Image.open(kare0) as im:
                kare0_a = np.asarray(im.convert("RGB").resize(
                    KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
            k0_mae = mae(kapak_a, kare0_a)
            kayit["kare0_kapak_mae"] = round(k0_mae, 3)
            kutu = panel_kutusu(kapak_a)
            if kutu is not None:
                pw, ph = kutu_boyut(kutu)
                kayit.update({"kutu": json.dumps(kutu, separators=(",", ":")),
                              "panel_w": pw, "panel_h": ph})
            if k0_mae > S3_MAE:
                kayit["sinif"] = "S3"
                kayit["not"] = f"kare0-kapak MAE {k0_mae:.1f} > {S3_MAE}"
            elif kutu is None:
                kayit["sinif"] = "S2"
                kayit["not"] = "panel bulunamadi"
            elif (abs(pw - ref_w) <= BOYUT_TOLERANS
                  and abs(ph - ref_h) <= BOYUT_TOLERANS):
                kayit["sinif"] = "S1"
            else:
                kayit["sinif"] = "S2"
                kayit["not"] = f"panel {pw}x{ph}, referans {ref_w}x{ref_h}"
            # sinif adimi icin indirilen agir dosyalar hemen silinir
            if lid not in ornekler:
                video_yol.unlink(missing_ok=True)
                kapak_yol.unlink(missing_ok=True)
        except Exception as ex:                                   # noqa: BLE001
            kayit["sinif"] = "HATA"
            kayit["not"] = f"{type(ex).__name__}: {ex}"[:200]
        siniflar[lid] = kayit["sinif"]
        satirlar_csv.append(kayit)
        with sinif_yol.open("w", newline="", encoding="utf-8") as fh:
            yz = csv.DictWriter(fh, fieldnames=list(satirlar_csv[0].keys()))
            yz.writeheader()
            yz.writerows(satirlar_csv)
        gecen = time.time() - t0
        kalan = gecen / n * (toplam - n)
        log(f"SINIF {n}/{toplam} ({100 * n / toplam:.0f}%) {cift} -> "
            f"{kayit['sinif']} | gecen {gecen / 60:.1f} dk, kalan {kalan / 60:.1f} dk")

    sayim = {s: sum(1 for k in satirlar_csv if k["sinif"] == s)
             for s in ("S1", "S2", "S3", "HATA")}
    log(f"SINIF SAYIMI {sayim}")

    # ------------------------------------------------- ADIM 2: uretim (S1)
    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, ref_dir / "ref.yuv", vw, vh)
    with Image.open(ref_kareler[0]) as im:
        ref_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
    sonuclar = []
    for lid in ornekler:
        cift = ad_of.get(lid, lid)
        ad = cift.replace(" + ", "_").replace(" ", "_")
        kayit = {"listing_id": lid, "cift": cift, "sinif": siniflar.get(lid, "?"),
                 "durum": "?"}
        try:
            if kayit["sinif"] != "S1":
                raise RuntimeError(f"sinif {kayit['sinif']} - S1 degil, uretilmedi")
            is_dir = out / "_is" / lid
            kapak_yol, video_yol = is_dir / "kapak.png", is_dir / "video.mp4"
            meta = probe(video_yol)
            ak = meta["streams"][0]
            sure = float(meta["format"]["duration"])
            p2, q2 = (ak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
            fps = round(float(p2) / float(q2), 3)
            if (int(ak["width"]), int(ak["height"])) != (vw, vh):
                raise RuntimeError(f"cozunurluk {ak['width']}x{ak['height']} "
                                   f"!= referans {vw}x{vh}")
            kayit.update({"sure_sn": round(sure, 3), "fps": fps})
            kareler = kareleri_ac(video_yol, is_dir / "kare")
            if len(kareler) != len(ref_kareler) or abs(fps - ref_fps) > 0.01:
                raise RuntimeError(
                    f"kare eslemesi yok: {len(kareler)} kare/{fps} fps, "
                    f"referans {len(ref_kareler)} kare/{ref_fps} fps")
            kutular, basarisiz = kaynak_kutulari(kareler, ref_kutu)
            if kutular[0] is None:
                raise RuntimeError("0. karede panel kutusu bulunamadi")
            with Image.open(kareler[0]) as im:
                kay_kare0 = np.asarray(im.convert("RGB"), dtype=np.uint8)
            ofset, maske, altin_bilgi = altin_ofset_bul(
                ref_kare0, kay_kare0, ref_kutu, kutular[0], hedef_altin)
            dyuv = rgb_ofset_yuv(ofset) if ofset is not None else (0.0, 0.0, 0.0)
            maske_uv = maske[::2, ::2] if maske is not None else None
            kay_veri, _, kay_adet = yuv_ac(video_yol, is_dir / "kay.yuv", vw, vh)
            adet = min(ref_adet, kay_adet)
            ham = is_dir / "yeni.yuv"
            tasinan = yuv_kompozit_akis(ref_veri, kay_veri, kare_bayt, adet,
                                        ref_kutu, kutular, vw, vh, ham, dyuv,
                                        maske, maske_uv)
            yeni_video = out / f"{ad}_{lid}_video.mp4"
            yuv_video_yaz(ham, yeni_video, vw, vh, ref_fps, ref_sure)
            geri = is_dir / "geri.yuv"
            yeni_veri, _, _ = yuv_ac(yeni_video, geri, vw, vh)
            dis_mae, olculen_kare = yuv_dis_mae(ref_veri, yeni_veri, kare_bayt,
                                                ref_kutu, vw, vh)
            # kapak = yeni videonun 0. karesi -> 2400x3000
            ham0 = is_dir / "yeni_kare0.png"
            extract_frame(yeni_video, ham0, 0)
            with Image.open(ham0) as im:
                kapak_b = np.asarray(im.convert("RGB").resize(
                    KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
            kapak_cikti = out / f"{ad}_{lid}_kapak.png"
            Image.fromarray(kapak_b).save(kapak_cikti)
            altin_yeni, _ = altin_ort(kapak_b)
            altin_fark = ([round(float(x - y), 2)
                           for x, y in zip(altin_yeni, hedef_altin)]
                          if altin_yeni and hedef_altin else None)
            kare0_tekrar = is_dir / "kontrol_kare0.png"
            extract_frame(yeni_video, kare0_tekrar, 0)
            with Image.open(kare0_tekrar) as im:
                k0 = np.asarray(im.convert("RGB").resize(
                    KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
            kapak_kare_mae = round(mae(kapak_b, k0), 4)
            ocr_s = ocr(kapak_b, ref_kutu_kapak)
            beklenen = [x.strip().lower() for x in cift.split("+")]
            ocr_ok = (all(b[:5] in ocr_s["metin"].lower() for b in beklenen)
                      if ocr_s["metin"] else None)
            orta = is_dir / "orta.png"
            extract_frame(yeni_video, orta, max(ref_sure / 2 - 0.05, 0))
            kayit.update({
                "durum": "URETILDI", "kaynak_kutu_kare0": kutular[0],
                "kutu_tespit_basarisiz_kare": basarisiz,
                "tasinan_kare": tasinan, "olculen_kare": olculen_kare,
                "poster_disi_mae": round(dis_mae, 4),
                "poster_disi_mae_1_alti": dis_mae < 1.0,
                "altin_rgb": altin_yeni, "altin_fark": altin_fark,
                "altin_2_alti": bool(altin_fark
                                     and max(abs(x) for x in altin_fark) < 2),
                "altin_esitleme": altin_bilgi,
                "kapak_kare_mae": kapak_kare_mae,
                "ocr": ocr_s, "ocr_dogru": ocr_ok,
                "video_dosya": yeni_video.name, "kapak_dosya": kapak_cikti.name,
                "mevcut_kapak": str(kapak_yol), "orta_kare": str(orta),
            })
            log(f"{cift}: URETILDI | panel disi Y MAE {dis_mae:.4f} "
                f"({olculen_kare} kare) | altin fark {altin_fark} | OCR {ocr_ok} "
                f"| kapak-kare MAE {kapak_kare_mae}")
            ham.unlink(missing_ok=True)
            geri.unlink(missing_ok=True)
            (is_dir / "kay.yuv").unlink(missing_ok=True)
        except Exception as ex:                                   # noqa: BLE001
            kayit.update({"durum": "URETILMEDI",
                          "not": f"{type(ex).__name__}: {ex}"[:300]})
            log(f"{cift}: URETILMEDI - {kayit['not'][:200]}")
        sonuclar.append(kayit)

    for lid in uretmeyen:
        sonuclar.append({"listing_id": lid, "cift": ad_of.get(lid, lid),
                         "sinif": siniflar.get(lid, "?"), "durum": "URETILMEDI",
                         "not": "gorev geregi uretilmedi"})

    if not a.yerel_girdi:
        kota_sonra = api.remaining

    # --------------------------------------------------- ADIM 3: gorsel
    ref_orta = ref_dir / "orta.png"
    extract_frame(ref_video, ref_orta, max(ref_sure / 2 - 0.05, 0))
    gorsel_satirlar = [(f"{ad_of.get(a.referans_id, 'REFERANS')}  -  "
                        f"{a.referans_id}   [REFERANS]",
                        [("REFERANS kapak", Image.open(ref_kapak).convert("RGB")),
                         ("SU ANKI kapak", Image.open(ref_kapak).convert("RGB")),
                         ("YENI kapak", Image.open(ref_kapak).convert("RGB")),
                         ("yeni video orta kare",
                          Image.open(ref_orta).convert("RGB"))])]
    for k in sonuclar:
        if k["durum"] != "URETILDI":
            continue
        gorsel_satirlar.append((
            f"{k['cift']}  -  {k['listing_id']}  [{k['sinif']}]",
            [("REFERANS kapak", Image.open(ref_kapak).convert("RGB")),
             ("SU ANKI kapak", Image.open(k["mevcut_kapak"]).convert("RGB")),
             ("YENI kapak", Image.open(out / k["kapak_dosya"]).convert("RGB")),
             ("yeni video orta kare", Image.open(k["orta_kare"]).convert("RGB"))]))

    kapak_kontrol_mae = None
    if not a.yerel_girdi:
        gor_k = gallery(api, a.referans_id)
        hedef = next((g for g in gor_k
                      if str(g.get("listing_image_id")) == KONTROL_KAPAK_ID), None)
        if hedef is None:
            raise SystemExit(f"HATA: canli kapak {KONTROL_KAPAK_ID} referans "
                             f"galerisinde yok -> gorsel yazilmadi, DUR")
        kontrol_yol = ref_dir / "kontrol_kapak.png"
        download(hedef.get("url_fullxfull") or hedef.get("url_570xN"), kontrol_yol)
        with Image.open(ref_kapak) as im_a, Image.open(kontrol_yol) as im_b:
            ra = im_a.convert("RGB")
            rb = im_b.convert("RGB")
            if rb.size != ra.size:
                rb = rb.resize(ra.size, Image.Resampling.LANCZOS)
            kapak_kontrol_mae = mae(np.asarray(ra), np.asarray(rb))
        kota_sonra = api.remaining
        log(f"GORSEL KAPISI: referans 'SU ANKI kapak' vs canli kapak "
            f"{KONTROL_KAPAK_ID} MAE = {kapak_kontrol_mae:.4f} "
            f"(esik {GORSEL_KAPI_MAE}) | indirilen kapak id {ref_kim.get('kapak_id')}")
        if kapak_kontrol_mae >= GORSEL_KAPI_MAE:
            raise SystemExit("HATA: referans kapagi canli kapakla tutmadi -> "
                             "gorsel yazilmadi, DUR")

    boyut = karsilastirma(gorsel_satirlar, out / "KARSILASTIRMA_V5.jpg")
    log(f"KARSILASTIRMA_V5.jpg {boyut[0]}x{boyut[1]} ({len(gorsel_satirlar)} satir)")

    ozet = {"calisma": "V5 KURU DENEME - Etsy'ye yazma YOK", "zaman": simdi(),
            "referans_id": a.referans_id, "referans_kimlik": ref_kim,
            "referans_video": {"px": [vw, vh], "sure_sn": round(ref_sure, 3),
                               "fps": ref_fps, "kare": len(ref_kareler)},
            "panel_kutusu_kapak": ref_kutu_kapak, "panel_kutusu_video": ref_kutu,
            "referans_panel_boyut": [ref_w, ref_h],
            "referans_altin_rgb": hedef_altin,
            "sinif_sayimi": sayim, "sinif_satirlari": satirlar_csv,
            "kapak_kontrol_id": KONTROL_KAPAK_ID,
            "kapak_kontrol_mae": (round(kapak_kontrol_mae, 4)
                                  if kapak_kontrol_mae is not None else None),
            "kota_once": kota_once, "kota_sonra": kota_sonra,
            "gecen_sn": round(time.time() - t0, 1), "ornekler": sonuclar}
    (out / "URETIM_SONUC_V5.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    md = [f"# Sablon V5 (poster icerigi ilanin kendi videosundan) - {simdi()} UTC",
          "", "Etsy'ye hicbir yazma cagrisi yapilmadi.", "",
          "## Yontem", "",
          "1. Referans videonun panel kutusu kapaktan olculur, videoya olceklenir.",
          "2. Ornek ilanin KENDI videosunda panel kutusu her karede bulunur.",
          "3. Panel ici birebir (olcek yok) referans karenin panel kutusuna tasinir;",
          "   kompozit ham yuv420p duzleminde, panel disi baytlara dokunulmadan.",
          "4. Altin B esitlemesi yalniz panel ici altin maskede uygulanir.",
          "5. Yeni kapak = yeni videonun 0. karesi, 2400x3000 LANCZOS.", "",
          "## Sinif sayimi", "",
          f"S1 {sayim['S1']} | S2 {sayim['S2']} | S3 {sayim['S3']} | "
          f"HATA {sayim['HATA']}", "",
          "## Ornekler", "",
          "| cift | sinif | durum | panel disi MAE | altin fark | OCR | kapak-kare MAE |",
          "|---|---|---|---|---|---|---|"]
    for k in sonuclar:
        md.append(f"| {k['cift']} | {k['sinif']} | {k['durum']} | "
                  f"{k.get('poster_disi_mae', '-')} | {k.get('altin_fark', '-')} | "
                  f"{k.get('ocr_dogru', '-')} | {k.get('kapak_kare_mae', '-')} |")
    (out / "TARIF_V5.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"sinif": sayim,
                      "uretilen": sum(1 for k in sonuclar
                                      if k["durum"] == "URETILDI"),
                      "kota_once": kota_once, "kota_sonra": kota_sonra},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
