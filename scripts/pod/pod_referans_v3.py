#!/usr/bin/env python3
"""V3: posteri referans Aquarius+Gemini ile AYNI DIKEY KONUMA getirir.

Uretim ve rapor TEK BETIKTEDIR; ara JSON semasi yoktur (V2'deki KeyError sinifi
hata bu yuzden olusamaz). Etsy'ye YAZMA YOK: yalniz GET.

Yontem:
  1. Poster CERCEVE kenarlari (altin maskesi degil) gradyan projeksiyonuyla
     bulunur; referansin ust kenari hedef konumdur.
  2. Ilanin videosu, cercevenin ust kenari hedefe gelecek kadar asagi kaydirilir;
     acilan ust bosluk referanstaki gibi kaynak videonun ust seridi aynalanarak
     doldurulur (match_video_to_cover yontemi).
  3. Yeni kapak = yeni videonun 0. karesi -> 2400x3000 LANCZOS -> Gold B LUT.
     A: yalniz Gold B.  B: A + altin bolge ortalamasi referansa esitlenmis.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import download, gallery, videos, video_url  # noqa: E402
from pod_cover_gold_b_transform import artwork_mask, build_candidate, load_luts  # noqa: E402
from match_video_to_cover import extract_frame, mae, probe  # noqa: E402

KAPAK = (2400, 3000)
HIZA_TOLERANS = 5


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------- cerceve
def _gri(yol):
    with Image.open(yol) as im:
        rgb = im.convert("RGB")
        if rgb.size != KAPAK:
            rgb = rgb.resize(KAPAK, Image.Resampling.LANCZOS)
        return np.asarray(rgb.convert("L"), dtype=np.float32)


def cerceve_kenar(yol, en_az_oran=0.04, en_cok_oran=0.75):
    """Posterin CERCEVE/baski paneli kenarlari (ust/alt/sol/sag), 2400x3000.

    Altin maskesi KULLANILMAZ. Sahnedeki en buyuk koyu dikdortgen (cerceve
    icindeki baski paneli) baglantili bilesen olarak bulunur; kutusu cerceve
    kenari olarak raporlanir. Esik, goruntunun kendi parlaklik dagilimindan
    turetilir; masa/duvar gibi orta tonlar disarida kalir.
    """
    from scipy import ndimage as _nd
    g = _gri(yol)
    h, w = g.shape
    taban, orta = float(g.min()), float(np.median(g))
    esik = taban + 0.35 * max(orta - taban, 1.0)
    koyu = g < esik
    koyu = _nd.binary_closing(koyu, structure=np.ones((9, 9), dtype=bool))
    etiket, adet = _nd.label(koyu, structure=np.ones((3, 3), dtype=np.uint8))
    if not adet:
        raise RuntimeError("koyu panel bulunamadi")
    alan = np.bincount(etiket.ravel())
    alan[0] = 0
    toplam = h * w
    adaylar = [(i, alan[i]) for i in range(1, adet + 1)
               if en_az_oran * toplam <= alan[i] <= en_cok_oran * toplam]
    if not adaylar:
        adaylar = [(int(np.argmax(alan)), int(alan.max()))]
    en_iyi = max(adaylar, key=lambda x: x[1])[0]
    ys, xs = np.nonzero(etiket == en_iyi)
    ust, alt, sol, sag = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    return {"ust": ust, "alt": alt, "sol": sol, "sag": sag,
            "yukseklik": alt - ust, "genislik": sag - sol,
            "oran": round((sag - sol) / max(alt - ust, 1), 4),
            "panel_orani": round(float(alan[en_iyi]) / toplam, 5),
            "esik": round(esik, 1)}


def altin_ortalama(yol):
    with Image.open(yol) as im:
        rgb = im.convert("RGB")
        if rgb.size != KAPAK:
            rgb = rgb.resize(KAPAK, Image.Resampling.LANCZOS)
        a = np.asarray(rgb, dtype=np.uint8)
    m = artwork_mask(a)
    if not m.any():
        return None, 0.0, m
    return ([round(float(x), 1) for x in a[m].astype(np.float32).mean(axis=0)],
            round(float(m.mean()), 6), m)


# ----------------------------------------------------------------- video
def video_kaydir(kaynak, cikti, kayma_video_px):
    """Kaynak videoyu kayma_video_px kadar asagi kaydirir; ust bosluk
    kaynak videonun ust seridinin aynasiyla doldurulur (referans yontemi)."""
    meta = probe(kaynak)
    ak = meta["streams"][0]
    w, h = int(ak["width"]), int(ak["height"])
    sure = float(meta["format"]["duration"])
    shift = int(kayma_video_px)
    if shift % 2:
        shift += 1
    if shift <= 0:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(kaynak),
                        "-c", "copy", str(cikti)], check=True)
        return {"video_px": [w, h], "sure_sn": round(sure, 3), "shift_px": 0,
                "ust_ayna_px": 0}
    ust = max(8, min(32, shift))
    graf = (f"[0:v]fps=30,setpts=PTS-STARTPTS,split=2[m0][t0];"
            f"[t0]crop={w}:{ust}:0:0,vflip,scale={w}:{shift}:flags=lanczos[top];"
            f"[m0]crop={w}:{h - shift}:0:0[body];[top][body]vstack=inputs=2[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(kaynak),
                    "-filter_complex", graf, "-map", "[out]", "-an",
                    "-t", f"{sure:.3f}", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(cikti)], check=True)
    return {"video_px": [w, h], "sure_sn": round(sure, 3), "shift_px": shift,
            "ust_ayna_px": ust}


def video_kur(kapak_png, kaydirilmis, cikti, still=0.6, fade=0.2, motion_start=0.4):
    """Referans kurgusu: ilk 0.6 sn sabit kapak, xfade, sonra hareket."""
    meta = probe(kaydirilmis)
    ak = meta["streams"][0]
    w, h = int(ak["width"]), int(ak["height"])
    sure = float(meta["format"]["duration"])
    graf = (f"[0:v]scale={w}:{h}:flags=lanczos,fps=30[s0];"
            f"[s0]trim=duration={still},setpts=PTS-STARTPTS[still];"
            f"[1:v]fps=30,setpts=PTS-STARTPTS,trim=start={motion_start},"
            f"setpts=PTS-STARTPTS[motion];"
            f"[still][motion]xfade=transition=fade:duration={fade}:"
            f"offset={still - fade}[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i",
                    str(kapak_png), "-i", str(kaydirilmis), "-filter_complex", graf,
                    "-map", "[out]", "-an", "-t", f"{sure:.3f}", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(cikti)], check=True)
    return {"sure_sn": round(sure, 3), "still_sn": still, "fade_sn": fade,
            "motion_start_sn": motion_start, "video_px": [w, h]}


def kare_kapak(video, ham, hedef):
    extract_frame(video, ham, 0)
    with Image.open(ham) as im:
        rgb = im.convert("RGB")
        if rgb.width * 5 != rgb.height * 4:
            raise RuntimeError(f"ilk kare 4:5 degil: {rgb.size}")
        rgb.resize(KAPAK, Image.Resampling.LANCZOS).save(hedef, "PNG", compress_level=3)


def goldb(taban_png, hedef_png, luts):
    with Image.open(taban_png) as im:
        taban = np.asarray(im.convert("RGB"), dtype=np.uint8)
    aday, qa = build_candidate(taban, luts)
    Image.fromarray(aday, "RGB").save(hedef_png, "PNG", compress_level=3)
    return qa


def renk_esitle(kaynak_png, hedef_png, hedef_rgb):
    """Altin maske ICINDE ortalama rengi hedefe tasir; maske disi degisim 0."""
    with Image.open(kaynak_png) as im:
        a = np.asarray(im.convert("RGB"), dtype=np.uint8)
    m = artwork_mask(a)
    if not m.any() or not hedef_rgb:
        Image.fromarray(a, "RGB").save(hedef_png, "PNG", compress_level=3)
        return {"uygulandi": False, "kayma": None}
    hedef = np.asarray(hedef_rgb, dtype=np.float32)
    toplam_kayma = np.zeros(3, dtype=np.float32)
    cikti = a
    # iki gecis: kaydirma sonrasi maske degistigi icin kalan fark bir kez daha kapatilir
    for _ in range(2):
        mm = artwork_mask(cikti)
        if not mm.any():
            break
        kayma = hedef - cikti[mm].astype(np.float32).mean(axis=0)
        if np.all(np.abs(kayma) < 0.05):
            break
        toplam_kayma += kayma
        yeni = a.astype(np.float32).copy()
        yeni[m] += toplam_kayma
        cikti = np.rint(np.clip(yeni, 0, 255)).astype(np.uint8)
        cikti[~m] = a[~m]                  # maske disi bire bir korunur
    Image.fromarray(cikti, "RGB").save(hedef_png, "PNG", compress_level=3)
    return {"uygulandi": True, "kayma": [round(float(x), 2) for x in toplam_kayma],
            "maske_disi_degisim": int(np.any(cikti[~m] != a[~m]))}


# ----------------------------------------------------------------- gorsel
def yazi(ciz, xy, metin, boyut=30, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            ciz.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    ciz.text(xy, metin, fill=renk)


def karsilastirma(satirlar, hedef, hucre=620, bosluk=16, satir_baslik=56,
                  sutun_baslik=48):
    """satirlar: [(etiket, [(altyazi, PIL.Image), ...])] -> tek JPG."""
    if not satirlar:
        raise RuntimeError("karsilastirma gorseli icin satir yok (bos tuval)")
    sutun = len(satirlar[0][1])
    yuk = [max(int(hucre * g.height / g.width) for _, g in gs) for _, gs in satirlar]
    tuval = Image.new("RGB", (bosluk + sutun * (hucre + bosluk),
                              bosluk + sutun_baslik
                              + sum(y + satir_baslik + bosluk for y in yuk)),
                      (248, 248, 248))
    ciz = ImageDraw.Draw(tuval)
    x = bosluk
    for altyazi, _ in satirlar[0][1]:
        yazi(ciz, (x + 4, bosluk + 6), altyazi, 32, (55, 55, 55))
        x += hucre + bosluk
    y = bosluk + sutun_baslik
    for (etiket, gorseller), sy in zip(satirlar, yuk):
        yazi(ciz, (bosluk, y + 10), etiket, 36)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--luts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--referans-id", default="4570112095")
    ap.add_argument("--ornek-ids", required=True)
    ap.add_argument("--yerel-girdi", default="",
                    help="Etsy yerine bu dizinden oku (yerel prova icin)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: --apply devre disi. Etsy'ye yazma kodu YOK. DUR.")

    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    luts = load_luts(pathlib.Path(a.luts))
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    ad_of = {str(r["id"]): (r.get("pair") or str(r["id"])) for r in katalog}
    ornekler = [x.strip() for x in a.ornek_ids.split(",") if x.strip()]
    hepsi = [a.referans_id] + ornekler

    kota_once = kota_sonra = None
    if a.yerel_girdi:
        log(f"YEREL PROVA: girdiler {a.yerel_girdi} dizininden okunuyor")
        kaynak = pathlib.Path(a.yerel_girdi)

        def indir(lid, is_dir):
            kapak, video = is_dir / "kapak.png", is_dir / "video.mp4"
            kapak.write_bytes((kaynak / f"{lid}_kapak.png").read_bytes())
            video.write_bytes((kaynak / f"{lid}_video.mp4").read_bytes())
            return kapak, video, {"kapak_id": "yerel", "video_id": "yerel"}
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
            gor = gallery(api, lid)
            vid = videos(api, lid)
            if not gor or not vid:
                raise RuntimeError("gorsel veya video yok")
            kapak, video = is_dir / "kapak.png", is_dir / "video.mp4"
            download(gor[0].get("url_fullxfull") or gor[0].get("url_570xN"), kapak)
            download(video_url(vid[0]), video)
            return kapak, video, {"kapak_id": str(gor[0].get("listing_image_id")),
                                  "video_id": str(vid[0].get("video_id"))}

    t0 = time.time()
    veri = {}
    for lid in hepsi:
        is_dir = out / "_is" / lid
        is_dir.mkdir(parents=True, exist_ok=True)
        kapak, video, kim = indir(lid, is_dir)
        veri[lid] = {"listing_id": lid, "cift": ad_of.get(lid, lid), **kim,
                     "mevcut_kapak": kapak, "canli_video": video,
                     "mevcut_cerceve": cerceve_kenar(kapak)}
        log(f"{ad_of.get(lid, lid)} ({lid}) mevcut cerceve: "
            f"{veri[lid]['mevcut_cerceve']['ust']}-{veri[lid]['mevcut_cerceve']['alt']} "
            f"/ {veri[lid]['mevcut_cerceve']['sol']}-{veri[lid]['mevcut_cerceve']['sag']}")

    ref = veri[a.referans_id]
    hedef_ust = ref["mevcut_cerceve"]["ust"]
    hedef_altin, ref_maske_orani, _ = altin_ortalama(ref["mevcut_kapak"])
    log(f"HEDEF cerceve ust = {hedef_ust} px | referans altin RGB {hedef_altin}")

    sonuclar = []
    for lid in ornekler:
        d = veri[lid]
        is_dir = out / "_is" / lid
        ad = d["cift"].replace(" + ", "_").replace(" ", "_")
        kayit = {"listing_id": lid, "cift": d["cift"], "kapak_id": d["kapak_id"],
                 "video_id": d["video_id"], "mevcut_cerceve": d["mevcut_cerceve"],
                 "durum": "?"}
        try:
            # videonun kendi 0. karesindeki cerceve konumu
            ham0 = is_dir / "kaynak_kare0.png"
            kapak0 = is_dir / "kaynak_kare0_2400.png"
            kare_kapak(d["canli_video"], ham0, kapak0)
            video_cerceve = cerceve_kenar(kapak0)
            kayit["video_cerceve"] = video_cerceve
            kayma_kapak = hedef_ust - video_cerceve["ust"]
            with Image.open(ham0) as im:
                vw, vh = im.size
            kayma_video = int(round(kayma_kapak * vh / KAPAK[1]))
            kayit["kayma_kapak_px"] = kayma_kapak
            kayit["kayma_video_px"] = kayma_video
            if kayma_kapak <= 0:
                kayit.update({"durum": "KALDI",
                              "not": f"gereken kaydirma {kayma_kapak} px (<=0); "
                                     "poster zaten hedefte veya daha asagida"})
                sonuclar.append(kayit)
                log(f"{d['cift']}: KALDI, kaydirma {kayma_kapak} px")
                continue

            kaydirilmis = is_dir / "kaydirilmis.mp4"
            kmeta = video_kaydir(d["canli_video"], kaydirilmis, kayma_video)
            yeni_ham = is_dir / "yeni_kare0.png"
            yeni_taban = is_dir / "yeni_kare0_2400.png"
            kare_kapak(kaydirilmis, yeni_ham, yeni_taban)
            yeni_video = out / f"{ad}_{lid}_video.mp4"
            vmeta = video_kur(yeni_taban, kaydirilmis, yeni_video)

            son_ham = is_dir / "son_kare0.png"
            son_taban = is_dir / "son_kare0_2400.png"
            kare_kapak(yeni_video, son_ham, son_taban)
            kapak_a = out / f"{ad}_{lid}_kapak_A.png"
            kapak_b = out / f"{ad}_{lid}_kapak_B.png"
            qa = goldb(son_taban, kapak_a, luts)
            esit = renk_esitle(kapak_a, kapak_b, hedef_altin)
            a_rgb, a_oran, _ = altin_ortalama(kapak_a)
            b_rgb, b_oran, _ = altin_ortalama(kapak_b)
            yeni_cerceve = cerceve_kenar(kapak_a)
            ust_f = yeni_cerceve["ust"] - hedef_ust
            alt_f = yeni_cerceve["alt"] - ref["mevcut_cerceve"]["alt"]
            tuttu = abs(ust_f) <= HIZA_TOLERANS and abs(alt_f) <= HIZA_TOLERANS
            kayit.update({
                "durum": "URETILDI" if tuttu else "KALDI",
                "kaydirma_meta": kmeta, "video_meta": vmeta, "goldb_qa": qa,
                "renk_esitleme": esit, "yeni_cerceve": yeni_cerceve,
                "cerceve_ust_fark": ust_f, "cerceve_alt_fark": alt_f,
                "hiza_5px": tuttu,
                "altin_A": a_rgb, "altin_A_oran": a_oran,
                "altin_B": b_rgb, "altin_B_oran": b_oran,
                "kare0_kapak_mae": round(mae(son_ham, yeni_taban), 4),
                "video_dosya": yeni_video.name,
                "kapak_A_dosya": kapak_a.name, "kapak_B_dosya": kapak_b.name,
            })
            if not tuttu:
                kayit["not"] = (f"cerceve farki ust {ust_f:+d} / alt {alt_f:+d} px "
                                f"> {HIZA_TOLERANS}")
            log(f"{d['cift']}: {kayit['durum']} | kaydirma {kayma_kapak} kapak px "
                f"({kayma_video} video px) | cerceve farki ust {ust_f:+d} alt {alt_f:+d} "
                f"| altin A {a_rgb} B {b_rgb}")
        except Exception as ex:                                   # noqa: BLE001
            kayit.update({"durum": "HATA", "not": f"{type(ex).__name__}: {ex}"})
            log(f"{d['cift']}: HATA {kayit['not'][:200]}")
        sonuclar.append(kayit)

    if not a.yerel_girdi:
        kota_sonra = api.remaining

    # ------------------------------------------------------------- gorsel
    gorsel_satir = []
    ref_kapak = Image.open(ref["mevcut_kapak"]).convert("RGB")
    for k in sonuclar:
        if k["durum"] == "HATA":
            continue
        lid = k["listing_id"]
        mevcut = Image.open(veri[lid]["mevcut_kapak"]).convert("RGB")
        hucreler = [("REFERANS kapak", ref_kapak), ("SU ANKI kapak", mevcut)]
        if k.get("kapak_A_dosya"):
            hucreler.append(("YENI A (Gold B)", Image.open(out / k["kapak_A_dosya"])
                             .convert("RGB")))
            hucreler.append(("YENI B (renk esit)", Image.open(out / k["kapak_B_dosya"])
                             .convert("RGB")))
        else:
            bos = Image.new("RGB", (2400, 3000), (228, 228, 228))
            yazi(ImageDraw.Draw(bos), (120, 1450), "URETILMEDI", 90, (120, 120, 120))
            hucreler += [("YENI A (Gold B)", bos), ("YENI B (renk esit)", bos)]
        etiket = f"{k['cift']}  -  {lid}"
        if k["durum"] == "KALDI":
            etiket += "   [KALDI]"
        gorsel_satir.append((etiket, hucreler))
    boyut = karsilastirma(gorsel_satir, out / "KARSILASTIRMA_V3.jpg")
    if boyut[1] < 600:
        raise SystemExit(f"HATA: karsilastirma gorseli bos gorunuyor: {boyut}")
    log(f"KARSILASTIRMA_V3.jpg {boyut[0]}x{boyut[1]} ({len(gorsel_satir)} satir)")

    # ------------------------------------------------------------- rapor
    ozet = {"calisma": "KURU DENEME - Etsy'ye yazma YOK", "referans_id": a.referans_id,
            "hedef_cerceve_ust": hedef_ust, "referans_altin_rgb": hedef_altin,
            "referans_cerceve": ref["mevcut_cerceve"],
            "hiza_tolerans_px": HIZA_TOLERANS,
            "kota_once": kota_once, "kota_sonra": kota_sonra,
            "gecen_sn": round(time.time() - t0, 1), "satirlar": sonuclar}
    (out / "URETIM_SONUC.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    md = [f"# Referans dikey hiza V3 ({simdi()} UTC)", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi; uretim yereldir.", "",
          "## Yontem", "", "| adim | islem |", "|---|---|",
          "| 1 | Poster CERCEVE kenarlari gradyan projeksiyonuyla bulunur "
          "(altin maskesi kullanilmaz) |",
          f"| 2 | Video, cerceve ust kenari referansin {hedef_ust} px'ine gelecek "
          "kadar asagi kaydirilir; ust bosluk kaynak videonun ust seridinin "
          "aynasiyla doldurulur |",
          "| 3 | Yeni kapak = yeni videonun 0. karesi -> 2400x3000 LANCZOS |",
          "| 4A | Gold B LUT (config/pod_cover_gold_b_luts.json) |",
          "| 4B | A + altin maske icinde ortalama renk referansa esitlenir "
          "(maske disi degisim 0) |", "",
          "## Cerceve kenarlari (2400x3000 px)", "",
          "| ilan | mevcut ust | mevcut alt | sol | sag | referanstan ust farki |",
          "|---|---:|---:|---:|---:|---:|"]
    rc = ref["mevcut_cerceve"]
    md.append(f"| {ref['cift']} (REFERANS) | {rc['ust']} | {rc['alt']} | {rc['sol']} | "
              f"{rc['sag']} | 0 |")
    for k in sonuclar:
        c = k["mevcut_cerceve"]
        md.append(f"| {k['cift']} | {c['ust']} | {c['alt']} | {c['sol']} | {c['sag']} | "
                  f"{c['ust'] - rc['ust']:+d} |")
    md += ["", "## Uygulanan kaydirma ve sonuc", "",
           "| ilan | kaydirma (kapak px) | kaydirma (video px) | yeni cerceve ust | "
           "ust fark | alt fark | <=5px | durum |",
           "|---|---:|---:|---:|---:|---:|---|---|"]
    for k in sonuclar:
        yc = k.get("yeni_cerceve") or {}
        md.append(f"| {k['cift']} | {k.get('kayma_kapak_px', '-')} | "
                  f"{k.get('kayma_video_px', '-')} | {yc.get('ust', '-')} | "
                  f"{k.get('cerceve_ust_fark', '-')} | {k.get('cerceve_alt_fark', '-')} | "
                  f"{'EVET' if k.get('hiza_5px') else 'HAYIR'} | {k['durum']} |")
    md += ["", "## Altin RGB", "",
           f"Referans (mevcut kapak): **{hedef_altin}**, maske orani {ref_maske_orani}", "",
           "| ilan | A (yalniz Gold B) | B (renk esitlenmis) | B kaymasi | maske disi degisim |",
           "|---|---|---|---|---:|"]
    for k in sonuclar:
        e = k.get("renk_esitleme") or {}
        md.append(f"| {k['cift']} | {k.get('altin_A', '-')} | {k.get('altin_B', '-')} | "
                  f"{e.get('kayma', '-')} | {e.get('maske_disi_degisim', '-')} |")
    md += ["", "## Cikti dosyalari", "",
           "- `KARSILASTIRMA_V3.jpg` - satir basina REFERANS | SU ANKI | YENI A | YENI B.",
           "- `<CIFT>_<id>_kapak_A.png`, `_kapak_B.png`, `_video.mp4`.",
           "- `URETIM_SONUC.json` - tum olcumler.", ""]
    (out / "TARIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    uretilen = sum(1 for x in sonuclar if x["durum"] == "URETILDI")
    log(json.dumps({"uretilen": uretilen, "kaldi":
                    sum(1 for x in sonuclar if x["durum"] == "KALDI"),
                    "hata": sum(1 for x in sonuclar if x["durum"] == "HATA"),
                    "kota_once": kota_once, "kota_sonra": kota_sonra},
                   ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
