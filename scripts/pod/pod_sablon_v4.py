#!/usr/bin/env python3
"""V4: referans sahnesini TEK SABLON yapar; yalniz poster ici degisir.

Referans (Aquarius+Gemini) videosunun her karesinde cerceve icindeki BASKI
PANELI tespit edilir. Panel disi piksellere DOKUNULMAZ; panel ici hedef ciftin
Midnight Blue posteriyle degistirilir, referans posterin ton/keskinlik/gren
gorunumune esitlenir, altin bolge B yontemiyle referansa esitlenir.

Yontem kapisi: ayni yontemle referansin KENDI posteri yeniden uretilir ve
orijinaliyle panel ici MAE olculur. MAE >= esik ise ornek uretilmez.

Etsy'ye YAZMA YOK: yalniz GET; --apply reddedilir.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import download, gallery, videos, video_url  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402

KAPAK = (2400, 3000)
REFERANS_ID = "4570112095"


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def kareleri_ac(video, hedef_dir):
    """Videoyu PNG kare dizisine acar (kayipsiz ara format)."""
    hedef_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video),
                    "-start_number", "0", str(hedef_dir / "%05d.png")], check=True)
    return sorted(hedef_dir.glob("*.png"))


def _otsu(g):
    """Iki modlu esik (Otsu). Panel goruntunun yarisini kaplasa da kayar esik
    gibi cokmez."""
    hist, _ = np.histogram(g, bins=256, range=(0, 256))
    toplam = hist.sum()
    if toplam == 0:
        return 128.0
    seviye = np.arange(256, dtype=np.float64)
    agirlik1 = np.cumsum(hist)
    agirlik2 = toplam - agirlik1
    kum = np.cumsum(hist * seviye)
    gecerli = (agirlik1 > 0) & (agirlik2 > 0)
    ort1 = np.where(gecerli, kum / np.maximum(agirlik1, 1), 0)
    ort2 = np.where(gecerli, (kum[-1] - kum) / np.maximum(agirlik2, 1), 0)
    varyans = agirlik1 * agirlik2 * (ort1 - ort2) ** 2
    varyans[~gecerli] = -1
    return float(np.argmax(varyans))


def panel_kutusu(a, en_az=0.04, en_cok=0.80, doluluk=0.80):
    """Koyu baski panelinin kutusu.

    Otsu esigiyle koyu maske cikarilir; panel, kutusunu en az `doluluk` oraninda
    dolduran (yani dikdortgen olan) en buyuk bilesendir. Altin maskesi
    kullanilmaz.
    """
    g = np.asarray(Image.fromarray(a).convert("L"), dtype=np.float32)
    esik = _otsu(g)
    koyu = ndimage.binary_closing(g < esik, structure=np.ones((9, 9), dtype=bool))
    koyu = ndimage.binary_fill_holes(koyu)
    etiket, adet = ndimage.label(koyu, structure=np.ones((3, 3), dtype=np.uint8))
    if not adet:
        return None
    toplam = g.size
    nesneler = ndimage.find_objects(etiket)
    adaylar = []
    for i, dilim in enumerate(nesneler, start=1):
        if dilim is None:
            continue
        alan = int((etiket[dilim] == i).sum())
        if not (en_az * toplam <= alan <= en_cok * toplam):
            continue
        ky, kx = dilim
        kutu_alan = (ky.stop - ky.start) * (kx.stop - kx.start)
        if alan / max(kutu_alan, 1) < doluluk:
            continue
        adaylar.append((alan, ky, kx))
    if not adaylar:
        return None
    _, ky, kx = max(adaylar, key=lambda x: x[0])
    return {"ust": int(ky.start), "alt": int(ky.stop) - 1,
            "sol": int(kx.start), "sag": int(kx.stop) - 1}


def kutu_olcekle(kutu, kaynak_yuk, hedef_yuk, kaynak_gen, hedef_gen):
    sy, sx = hedef_yuk / kaynak_yuk, hedef_gen / kaynak_gen
    return {"ust": int(round(kutu["ust"] * sy)), "alt": int(round(kutu["alt"] * sy)),
            "sol": int(round(kutu["sol"] * sx)), "sag": int(round(kutu["sag"] * sx))}


def kutu_dogrula(kare, kutu, pay=40):
    """Kutunun kare icinde gercekten koyu panel oldugunu ve kenarlarinin
    disariya gore koyu kaldigini olcer. Donus: (uyum, ic_ort, dis_ort)."""
    g = np.asarray(Image.fromarray(kare).convert("L"), dtype=np.float32)
    h, w = g.shape
    u, al = max(kutu["ust"], 0), min(kutu["alt"], h - 1)
    s, sa = max(kutu["sol"], 0), min(kutu["sag"], w - 1)
    ic = g[u:al + 1, s:sa + 1]
    dis = np.concatenate([
        g[max(u - pay, 0):u, s:sa + 1].ravel(),
        g[al + 1:min(al + 1 + pay, h), s:sa + 1].ravel(),
        g[u:al + 1, max(s - pay, 0):s].ravel(),
        g[u:al + 1, sa + 1:min(sa + 1 + pay, w)].ravel()])
    ic_ort = float(ic.mean())
    dis_ort = float(dis.mean()) if dis.size else ic_ort
    return (dis_ort - ic_ort), round(ic_ort, 2), round(dis_ort, 2)


def poster_yerlestir(kare, kutu, poster_rgb, ton):
    """Panel icini poster ile degistirir; panel disi bire bir korunur."""
    h = kutu["alt"] - kutu["ust"] + 1
    w = kutu["sag"] - kutu["sol"] + 1
    yeni = Image.fromarray(poster_rgb).resize((w, h), Image.Resampling.LANCZOS)
    if ton.get("bulaniklik"):
        yeni = yeni.filter(ImageFilter.GaussianBlur(ton["bulaniklik"]))
    p = np.asarray(yeni, dtype=np.float32)
    if ton.get("kazanc") is not None:
        p = p * np.asarray(ton["kazanc"], dtype=np.float32) \
            + np.asarray(ton["ofset"], dtype=np.float32)
    if ton.get("gren"):
        rng = np.random.default_rng(ton.get("tohum", 7))
        p = p + rng.normal(0.0, ton["gren"], p.shape)
    p = np.clip(p, 0, 255).astype(np.uint8)
    cikti = kare.copy()
    cikti[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1] = p
    return cikti


def ton_olc(referans_bolge, kaynak_bolge):
    """Kaynak posteri referans panelin ton istatistigine tasiyan lineer donusum."""
    r = referans_bolge.reshape(-1, 3).astype(np.float32)
    k = kaynak_bolge.reshape(-1, 3).astype(np.float32)
    r_ort, r_std = r.mean(axis=0), r.std(axis=0) + 1e-6
    k_ort, k_std = k.mean(axis=0), k.std(axis=0) + 1e-6
    kazanc = r_std / k_std
    ofset = r_ort - kazanc * k_ort
    return {"kazanc": [round(float(x), 5) for x in kazanc],
            "ofset": [round(float(x), 3) for x in ofset],
            "referans_ort": [round(float(x), 2) for x in r_ort],
            "referans_std": [round(float(x), 2) for x in r_std]}


def altin_ort(a):
    m = artwork_mask(a if a.shape[:2] == (3000, 2400) else
                     np.asarray(Image.fromarray(a).resize(KAPAK, Image.Resampling.LANCZOS)))
    if not m.any():
        return None, m
    kaynak = a if a.shape[:2] == (3000, 2400) else \
        np.asarray(Image.fromarray(a).resize(KAPAK, Image.Resampling.LANCZOS))
    return [round(float(x), 1) for x in kaynak[m].astype(np.float32).mean(axis=0)], m


def altin_esitle(kapak_rgb, hedef_rgb):
    """Altin maske icinde ortalamayi hedefe tasir; maske disi degisim 0."""
    a = kapak_rgb
    m = artwork_mask(a)
    if not m.any() or not hedef_rgb:
        return a, {"uygulandi": False}
    hedef = np.asarray(hedef_rgb, dtype=np.float32)
    toplam = np.zeros(3, dtype=np.float32)
    cikti = a
    for _ in range(5):
        mm = artwork_mask(cikti)
        if not mm.any():
            break
        fark = hedef - cikti[mm].astype(np.float32).mean(axis=0)
        if np.all(np.abs(fark) < 0.05):
            break
        toplam += fark
        yeni = a.astype(np.float32).copy()
        yeni[m] += toplam
        cikti = np.rint(np.clip(yeni, 0, 255)).astype(np.uint8)
        cikti[~m] = a[~m]
    return cikti, {"uygulandi": True, "kayma": [round(float(x), 2) for x in toplam],
                   "maske_disi_degisim": int(np.any(cikti[~m] != a[~m]))}


def video_yaz(kare_dir, hedef, fps, sure):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps),
                    "-start_number", "0", "-i", str(kare_dir / "%05d.png"),
                    "-t", f"{sure:.3f}", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(hedef)], check=True)


def ocr(a, kutu):
    """Panel icindeki metni okur (tesseract varsa)."""
    if not shutil.which("tesseract"):
        return {"durum": "tesseract yok", "metin": ""}
    kes = a[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]
    im = Image.fromarray(kes).convert("L")
    im = im.resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)
    im = im.point(lambda v: 255 if v > 110 else 0)
    p = pathlib.Path("/tmp/_ocr.png")
    im.save(p)
    r = subprocess.run(["tesseract", str(p), "stdout", "--psm", "6"],
                       capture_output=True, text=True)
    return {"durum": "okundu", "metin": " ".join((r.stdout or "").split())[:200]}


def yazi(ciz, xy, metin, boyut=32, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            ciz.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    ciz.text(xy, metin, fill=renk)


def karsilastirma(satirlar, hedef, hucre=640, bosluk=16, satir_baslik=58, sutun_baslik=50):
    if not satirlar:
        raise RuntimeError("karsilastirma icin satir yok")
    yuk = [max(int(hucre * g.height / g.width) for _, g in gs) for _, gs in satirlar]
    n = len(satirlar[0][1])
    tuval = Image.new("RGB", (bosluk + n * (hucre + bosluk),
                              bosluk + sutun_baslik
                              + sum(y + satir_baslik + bosluk for y in yuk)),
                      (248, 248, 248))
    ciz = ImageDraw.Draw(tuval)
    x = bosluk
    for altyazi, _ in satirlar[0][1]:
        yazi(ciz, (x + 4, bosluk + 6), altyazi, 33, (55, 55, 55))
        x += hucre + bosluk
    y = bosluk + sutun_baslik
    for (etiket, gorseller), sy in zip(satirlar, yuk):
        yazi(ciz, (bosluk, y + 10), etiket, 37)
        y += satir_baslik
        x = bosluk
        for _, g in gorseller:
            h = int(hucre * g.height / g.width)
            tuval.paste(g.resize((hucre, h), Image.Resampling.LANCZOS), (x, y))
            ciz.rectangle([x, y, x + hucre - 1, y + h - 1], outline=(170, 170, 170))
            x += hucre + bosluk
        y += sy + bosluk
    tuval.save(hedef, "JPEG", quality=92, optimize=True)
    return tuval.size


def poster_bul(kok, cift):
    """Cifte ait Midnight Blue poster dosyasini bulur (buyuk/kucuk harf duyarsiz)."""
    ad = cift.replace(" + ", "_").replace(" ", "_").lower()
    adaylar = [p for p in pathlib.Path(kok).rglob("*.jpg")
               if p.stem.lower() == ad] if pathlib.Path(kok).exists() else []
    if not adaylar:
        adaylar = [p for p in pathlib.Path(kok).rglob("*.jpg")
                   if ad in p.stem.lower()] if pathlib.Path(kok).exists() else []
    return adaylar


def poster_sec(adaylar, hedef_oran):
    """Panel oranina en yakin posteri secer."""
    en_iyi, en_fark = None, None
    for p in adaylar:
        with Image.open(p) as im:
            o = im.width / im.height
        fark = abs(o - hedef_oran)
        if en_fark is None or fark < en_fark:
            en_iyi, en_fark = p, fark
    return en_iyi, (round(en_fark, 4) if en_fark is not None else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--poster-kok", required=True)
    ap.add_argument("--ornek-ids", required=True)
    ap.add_argument("--referans-id", default=REFERANS_ID)
    ap.add_argument("--dogrulama-esigi", type=float, default=3.0)
    ap.add_argument("--yerel-girdi", default="")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: --apply devre disi. Etsy'ye yazma kodu YOK. DUR.")

    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    ad_of = {str(r["id"]): (r.get("pair") or str(r["id"])) for r in katalog}
    ornekler = [x.strip() for x in a.ornek_ids.split(",") if x.strip()]
    t0 = time.time()
    kota_once = kota_sonra = None

    # ---------------------------------------------------- girdiler
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

    # ---------------------------------------------------- ADIM 1: sablon
    ref_dir = out / "_is" / "REFERANS"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_kapak, ref_video, ref_kim = indir(a.referans_id, ref_dir)
    meta = probe(ref_video)
    ak = meta["streams"][0]
    vw, vh = int(ak["width"]), int(ak["height"])
    sure = float(meta["format"]["duration"])
    fps_ham = ak.get("r_frame_rate", "30/1")
    fps = round(eval(fps_ham)) if "/" in str(fps_ham) else float(fps_ham)   # noqa: S307
    kare_dir = ref_dir / "kare"
    kareler = kareleri_ac(ref_video, kare_dir)
    log(f"Referans video {vw}x{vh}, {sure:.2f} sn, {fps} fps, {len(kareler)} kare")

    # Panel, TEMIZ kapak uzerinde (2400x3000) tespit edilir ve video uzayina
    # olceklenir; kare basina esik kaymasi boylece devre disi kalir.
    ref_kapak_a = np.asarray(Image.open(ref_kapak).convert("RGB").resize(
        KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
    kapak_kutu = panel_kutusu(ref_kapak_a)
    if kapak_kutu is None:
        raise SystemExit("HATA: kapakta panel bulunamadi -> DUR")
    ref_kutu = kutu_olcekle(kapak_kutu, KAPAK[1], vh, KAPAK[0], vw)
    log(f"Panel kapakta {kapak_kutu} -> videoda {ref_kutu}")

    # kararlilik: kutunun ic/dis kontrasti her karede korunuyor mu
    kontrast = []
    for p_k in kareler:
        kare = np.asarray(Image.open(p_k).convert("RGB"), dtype=np.uint8)
        fark, ic_o, dis_o = kutu_dogrula(kare, ref_kutu)
        kontrast.append(fark)
    kontrast_min = round(float(min(kontrast)), 2)
    # bagimsiz tespitle kaydirma kontrolu (ilk/orta/son kare)
    ornek_kutular = []
    for i in (0, len(kareler) // 2, len(kareler) - 1):
        kare = np.asarray(Image.open(kareler[i]).convert("RGB"), dtype=np.uint8)
        k = panel_kutusu(kare)
        if k:
            ornek_kutular.append({"kare": i, **k})
    hareket = {}
    if len(ornek_kutular) >= 2:
        for anahtar in ("ust", "alt", "sol", "sag"):
            deger = [x[anahtar] for x in ornek_kutular]
            hareket[anahtar] = max(deger) - min(deger)
    log(f"Panel ic/dis kontrast en dusuk {kontrast_min} | bagimsiz tespit "
        f"kaydirmasi {hareket}")
    if kontrast_min <= 0:
        raise SystemExit(f"HATA: panel kutusu bazi karelerde gecerli degil "
                         f"(kontrast {kontrast_min}) -> DUR")

    hedef_oran = (ref_kutu["sag"] - ref_kutu["sol"] + 1) / \
                 (ref_kutu["alt"] - ref_kutu["ust"] + 1)
    ref_kare0 = np.asarray(Image.open(kareler[0]).convert("RGB"), dtype=np.uint8)
    ref_bolge = ref_kare0[ref_kutu["ust"]:ref_kutu["alt"] + 1,
                          ref_kutu["sol"]:ref_kutu["sag"] + 1]
    hedef_altin, _ = altin_ort(ref_kapak_a)
    log(f"Panel orani {hedef_oran:.4f} | referans altin RGB {hedef_altin}")

    # ---------------------------------------------------- ADIM 2: yontem kapisi
    ref_cift = ad_of.get(a.referans_id, "Aquarius + Gemini")
    ref_adaylar = poster_bul(a.poster_kok, ref_cift)
    if not ref_adaylar:
        raise SystemExit(f"HATA: referans posteri bulunamadi ({ref_cift}) -> DUR")
    ref_poster_yol, ref_oran_fark = poster_sec(ref_adaylar, hedef_oran)
    ref_poster = np.asarray(Image.open(ref_poster_yol).convert("RGB"), dtype=np.uint8)
    ham_yerlesim = Image.fromarray(ref_poster).resize(
        (ref_bolge.shape[1], ref_bolge.shape[0]), Image.Resampling.LANCZOS)
    ton = ton_olc(ref_bolge, np.asarray(ham_yerlesim, dtype=np.uint8))
    ton["bulaniklik"] = 0.6
    ton["gren"] = 1.2
    yeniden = poster_yerlestir(ref_kare0, ref_kutu, ref_poster, ton)
    ic_dilim = (slice(ref_kutu["ust"], ref_kutu["alt"] + 1),
                slice(ref_kutu["sol"], ref_kutu["sag"] + 1))
    dogrulama_mae = float(np.abs(yeniden[ic_dilim].astype(np.float32)
                                 - ref_kare0[ic_dilim].astype(np.float32)).mean())
    log(f"YONTEM KAPISI: referans kendini yeniden uretme panel ici MAE = "
        f"{dogrulama_mae:.3f} (esik {a.dogrulama_esigi})")
    kapi_gecti = dogrulama_mae < a.dogrulama_esigi

    sonuclar = []
    if not kapi_gecti:
        log("KAPI GECMEDI: ornek uretilmedi.")
    else:
        for lid in ornekler:
            is_dir = out / "_is" / lid
            is_dir.mkdir(parents=True, exist_ok=True)
            cift = ad_of.get(lid, lid)
            ad = cift.replace(" + ", "_").replace(" ", "_")
            kayit = {"listing_id": lid, "cift": cift, "durum": "?"}
            try:
                mev_kapak, _, kim = indir(lid, is_dir)
                kayit.update(kim)
                adaylar = poster_bul(a.poster_kok, cift)
                if not adaylar:
                    raise RuntimeError(f"poster dosyasi yok: {cift}")
                poster_yol, oran_fark = poster_sec(adaylar, hedef_oran)
                poster = np.asarray(Image.open(poster_yol).convert("RGB"), dtype=np.uint8)
                ham = np.asarray(Image.fromarray(poster).resize(
                    (ref_bolge.shape[1], ref_bolge.shape[0]),
                    Image.Resampling.LANCZOS), dtype=np.uint8)
                ton_i = ton_olc(ref_bolge, ham)
                ton_i["bulaniklik"], ton_i["gren"] = ton["bulaniklik"], ton["gren"]

                yeni_kare_dir = is_dir / "kare"
                yeni_kare_dir.mkdir(exist_ok=True)
                for i, p in enumerate(kareler):
                    kare = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
                    yeni = poster_yerlestir(kare, ref_kutu, poster, ton_i)
                    Image.fromarray(yeni, "RGB").save(yeni_kare_dir / f"{i:05d}.png")
                yeni_video = out / f"{ad}_{lid}_video.mp4"
                video_yaz(yeni_kare_dir, yeni_video, fps, sure)

                # kapak = yeni videonun 0. karesi
                ham0 = is_dir / "yeni_kare0.png"
                extract_frame(yeni_video, ham0, 0)
                with Image.open(ham0) as im:
                    kapak_a = np.asarray(im.convert("RGB").resize(
                        KAPAK, Image.Resampling.LANCZOS), dtype=np.uint8)
                kapak_b, esit = altin_esitle(kapak_a, hedef_altin)
                kapak_yol = out / f"{ad}_{lid}_kapak.png"
                Image.fromarray(kapak_b, "RGB").save(kapak_yol, "PNG", compress_level=3)

                # KONTROLLER
                yeni_kare_dir_c = is_dir / "kontrol"
                yeni_kareler = kareleri_ac(yeni_video, yeni_kare_dir_c)
                dis_mae, n = 0.0, 0
                for i, p in enumerate(yeni_kareler[:len(kareler)]):
                    yk = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
                    rk = np.asarray(Image.open(kareler[i]).convert("RGB"), dtype=np.float32)
                    fark = np.abs(yk - rk)
                    fark[ic_dilim] = 0.0
                    dis_piksel = fark.size - (fark[ic_dilim].size)
                    dis_mae += float(fark.sum() / max(dis_piksel, 1))
                    n += 1
                dis_mae = dis_mae / max(n, 1)
                kapak_kare_mae = float(np.abs(
                    np.asarray(Image.open(ham0).convert("RGB").resize(
                        KAPAK, Image.Resampling.LANCZOS), dtype=np.float32)
                    - kapak_a.astype(np.float32)).mean())
                altin_yeni, _ = altin_ort(kapak_b)
                altin_fark = ([round(altin_yeni[j] - hedef_altin[j], 2) for j in range(3)]
                              if altin_yeni and hedef_altin else None)
                ocr_s = ocr(np.asarray(Image.open(ham0).convert("RGB"), dtype=np.uint8),
                            ref_kutu)
                beklenen = [x.strip().lower() for x in cift.split("+")]
                ocr_ok = all(b[:5] in ocr_s["metin"].lower() for b in beklenen) \
                    if ocr_s["metin"] else None
                kayit.update({
                    "durum": "URETILDI", "poster_dosya": poster_yol.name,
                    "poster_oran_farki": oran_fark, "ton": ton_i,
                    "renk_esitleme": esit,
                    "poster_disi_mae": round(dis_mae, 4),
                    "poster_disi_mae_1_alti": dis_mae < 1.0,
                    "kapak_kare_mae": round(kapak_kare_mae, 4),
                    "altin_rgb": altin_yeni, "altin_fark": altin_fark,
                    "altin_2_alti": bool(altin_fark
                                         and max(abs(x) for x in altin_fark) < 2),
                    "ocr": ocr_s, "ocr_dogru": ocr_ok,
                    "video_dosya": yeni_video.name, "kapak_dosya": kapak_yol.name,
                    "mevcut_kapak": str(mev_kapak),
                })
                log(f"{cift}: URETILDI | poster disi MAE {dis_mae:.3f} | "
                    f"altin fark {altin_fark} | OCR {ocr_ok} | "
                    f"kapak-kare MAE {kapak_kare_mae:.3f}")
                shutil.rmtree(yeni_kare_dir, ignore_errors=True)
                shutil.rmtree(yeni_kare_dir_c, ignore_errors=True)
            except Exception as ex:                               # noqa: BLE001
                kayit.update({"durum": "HATA", "not": f"{type(ex).__name__}: {ex}"})
                log(f"{cift}: HATA {kayit['not'][:200]}")
            sonuclar.append(kayit)

    if not a.yerel_girdi:
        kota_sonra = api.remaining

    # ---------------------------------------------------- ADIM 4: gorsel
    orta_i = len(kareler) // 2
    satirlar = [(f"{ref_cift}  -  {a.referans_id}   [REFERANS]",
                 [("SU ANKI kapak", Image.open(ref_kapak).convert("RGB")),
                  ("YENI kapak", Image.open(ref_kapak).convert("RGB")),
                  ("video orta kare", Image.open(kareler[orta_i]).convert("RGB"))])]
    for k in sonuclar:
        if k["durum"] != "URETILDI":
            continue
        v = out / k["video_dosya"]
        orta = out / "_is" / k["listing_id"] / "orta.png"
        extract_frame(v, orta, max(sure / 2 - 0.05, 0))
        satirlar.append((f"{k['cift']}  -  {k['listing_id']}",
                         [("SU ANKI kapak", Image.open(k["mevcut_kapak"]).convert("RGB")),
                          ("YENI kapak", Image.open(out / k["kapak_dosya"]).convert("RGB")),
                          ("video orta kare", Image.open(orta).convert("RGB"))]))
    boyut = karsilastirma(satirlar, out / "KARSILASTIRMA_V4.jpg")
    log(f"KARSILASTIRMA_V4.jpg {boyut[0]}x{boyut[1]} ({len(satirlar)} satir)")

    ozet = {"calisma": "KURU DENEME - Etsy'ye yazma YOK",
            "referans_id": a.referans_id, "referans_video": ref_kim,
            "video": {"px": [vw, vh], "sure_sn": round(sure, 3), "fps": fps,
                      "kare": len(kareler)},
            "panel_hareketi_px": hareket, "panel_kutusu_video": ref_kutu,
            "panel_kutusu_kapak": kapak_kutu, "panel_kontrast_min": kontrast_min,
            "panel_orani": round(hedef_oran, 4),
            "referans_altin_rgb": hedef_altin,
            "referans_poster": ref_poster_yol.name,
            "referans_poster_oran_farki": ref_oran_fark,
            "ton": ton, "dogrulama_mae": round(dogrulama_mae, 4),
            "dogrulama_esigi": a.dogrulama_esigi, "kapi_gecti": kapi_gecti,
            "kota_once": kota_once, "kota_sonra": kota_sonra,
            "gecen_sn": round(time.time() - t0, 1), "satirlar": sonuclar}
    (out / "URETIM_SONUC.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    md = [f"# Referans sablon V4 ({simdi()} UTC)", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi; uretim yereldir.", "",
          "## Sablon", "", "| olcum | deger |", "|---|---|",
          f"| referans video | {vw}x{vh}, {sure:.2f} sn, {fps} fps, {len(kareler)} kare |",
          f"| panel kutusu (video) | ust {ref_kutu['ust']}, alt {ref_kutu['alt']}, "
          f"sol {ref_kutu['sol']}, sag {ref_kutu['sag']} |",
          f"| panel kutusu (kapak 2400x3000) | {kapak_kutu} |",
          f"| bagimsiz tespit kaydirmasi | {hareket} px |",
          f"| panel ic/dis kontrast (en dusuk kare) | {kontrast_min} |",
          f"| panel orani | {hedef_oran:.4f} |",
          f"| referans poster | `{ref_poster_yol.name}` (oran farki {ref_oran_fark}) |",
          f"| ton donusumu | kazanc {ton['kazanc']}, ofset {ton['ofset']}, "
          f"bulaniklik {ton['bulaniklik']}, gren {ton['gren']} |", "",
          "## Yontem kapisi", "",
          f"Referansin KENDI posteri ayni yontemle yeniden uretildi; panel ici "
          f"**MAE = {dogrulama_mae:.3f}** (esik {a.dogrulama_esigi}) -> "
          f"**{'GECTI' if kapi_gecti else 'GECMEDI'}**.", ""]
    if sonuclar:
        md += ["## Ornekler", "",
               "| ilan | poster disi MAE | <1 | altin farki | <2 | OCR | kapak-kare MAE | durum |",
               "|---|---:|---|---|---|---|---:|---|"]
        for k in sonuclar:
            md.append(f"| {k['cift']} | {k.get('poster_disi_mae', '-')} | "
                      f"{'EVET' if k.get('poster_disi_mae_1_alti') else 'HAYIR'} | "
                      f"{k.get('altin_fark', '-')} | "
                      f"{'EVET' if k.get('altin_2_alti') else 'HAYIR'} | "
                      f"{k.get('ocr_dogru')} | {k.get('kapak_kare_mae', '-')} | "
                      f"{k['durum']} |")
        md += ["", "OCR ham metinleri:", ""]
        md += [f"- **{k['cift']}**: `{(k.get('ocr') or {}).get('metin', '')}`"
               for k in sonuclar]
    md += ["", "## Cikti", "",
           "- `KARSILASTIRMA_V4.jpg` - satir basina SU ANKI kapak | YENI kapak | "
           "video orta kare.",
           "- `<CIFT>_<id>_video.mp4`, `<CIFT>_<id>_kapak.png`.",
           "- `URETIM_SONUC.json` - tum olcumler.", ""]
    (out / "TARIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    shutil.rmtree(kare_dir, ignore_errors=True)
    log(json.dumps({"kapi_gecti": kapi_gecti, "dogrulama_mae": round(dogrulama_mae, 3),
                    "uretilen": sum(1 for x in sonuclar if x["durum"] == "URETILDI"),
                    "hata": sum(1 for x in sonuclar if x["durum"] == "HATA"),
                    "kota_once": kota_once, "kota_sonra": kota_sonra},
                   ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
