#!/usr/bin/env python3
"""Referans (Aquarius+Gemini) VIDEO hattini TOPLU calistirir.

Mo 18 Eyl 2026 duzeltmesi: referansin canli kapagi Gold B kosusundan gelir
(run 35349346706), video karesinden DEGIL. Bu yuzden YENI KAPAK URETILMEZ;
her ilanin mevcut Gold B kapagi korunur ve yalniz VIDEO o kapaga hizalanir.

Kaydirma miktari ilan basina OLCULUR (86 px sabit degildir): ilanin kapagi ile
kendi videosunun hareket karesi arasindaki dikey kayma aranir.

Kaynak her ilan icin KENDI canli videosu ve KENDI canli Gold B kapagidir.
Etsy'ye YAZMA YOK: varsayilan --dry-run, yazma kodu devre disi (--apply reddedilir).
Hedef ilanlar katalogdan (pod_changes_v2.json) okunur; sabit LISTING_ID yoktur.

Kullanim:
  pod_referans_hatti_batch.py --catalog pod_changes_v2.json --out OUT \
      [--only-ids 4570126104,4570125580] [--referans-kapak ref.png]
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
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    download, gallery, variation_images, videos, video_url,
)
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402
from match_video_to_cover import extract_frame, mae, probe  # noqa: E402

REFERANS_ID = "4570112095"
KAPAK_OLCU = (2400, 3000)


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def eta(i, toplam, t0):
    gecen = time.time() - t0
    kalan = (gecen / i) * (toplam - i) if i else 0
    return (f"[{i}/{toplam} %{i / toplam * 100:4.1f}] gecen {gecen / 60:4.1f} dk, "
            f"kalan ~{kalan / 60:4.1f} dk")


def video_kur(kapak, kaynak_video, cikti, shift_cover_px, still, fade, motion_start):
    """match_video_to_cover.py ile AYNI filtre grafigi; tek ilan yerine toplu kullanim."""
    meta = probe(kaynak_video)
    akis = meta["streams"][0]
    w, h = int(akis["width"]), int(akis["height"])
    sure = float(meta["format"]["duration"])
    if w * 5 != h * 4:
        raise RuntimeError(f"video 4:5 degil: {w}x{h}")
    with Image.open(kapak) as im:
        if im.width * 5 != im.height * 4:
            raise RuntimeError(f"kapak 4:5 degil: {im.size}")
    shift = round(shift_cover_px * h / KAPAK_OLCU[1])
    if shift % 2:
        shift += 1
    fade_offset = still - fade
    if shift > 0:
        govde = h - shift
        ust_ornek = max(8, min(32, shift))
        hareket = (
            f"[1:v]fps=30,setpts=PTS-STARTPTS,split=2[motion0][top0];"
            f"[top0]crop={w}:{ust_ornek}:0:0,vflip,scale={w}:{shift}:flags=lanczos[top];"
            f"[motion0]crop={w}:{govde}:0:0[body];"
            f"[top][body]vstack=inputs=2[shifted];"
        )
    else:
        govde, ust_ornek = h, 0
        hareket = f"[1:v]fps=30,setpts=PTS-STARTPTS[shifted];"
    graf = (
        f"[0:v]scale={w}:{h}:flags=lanczos,fps=30[still0];"
        f"[still0]trim=duration={still},setpts=PTS-STARTPTS[still];"
        + hareket +
        f"[shifted]trim=start={motion_start},setpts=PTS-STARTPTS[motion];"
        f"[still][motion]xfade=transition=fade:duration={fade}:offset={fade_offset}[out]"
    )
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(kapak),
        "-i", str(kaynak_video), "-filter_complex", graf, "-map", "[out]", "-an",
        "-t", f"{sure:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(cikti),
    ], check=True)
    return {"video_px": [w, h], "sure_sn": round(sure, 3), "shift_px": shift,
            "ust_ayna_px": ust_ornek, "still_sn": still, "fade_sn": fade}


ARAMA_PX = 360          # kapak uzayinda aranan en buyuk kayma
ARAMA_OLCU = (600, 750)  # kaba arama icin kucultulmus tuval


def _gri(yol, olcu):
    with Image.open(yol) as im:
        return np.asarray(im.convert("L").resize(olcu, Image.Resampling.LANCZOS),
                          dtype=np.float32)


def kayma_olc(kapak, video, is_dir):
    """Kapak ile videonun hareket karesi arasindaki dikey kaymayi OLCER.

    Videonun son karesi (yerlesmis kompozisyon) kapakla karsilastirilir; kare
    asagi dogru dy kadar kaydirilip ortalama mutlak fark en kucuk oldugunda
    aranan kayma bulunur. Donus kapak uzayindadir (2400x3000).
    """
    meta = probe(video)
    sure = float(meta["format"]["duration"])
    son_kare = is_dir / "kaynak_son_kare.png"
    extract_frame(video, son_kare, max(sure - 0.15, 0.0))
    k = _gri(kapak, ARAMA_OLCU)
    f = _gri(son_kare, ARAMA_OLCU)
    olcek = KAPAK_OLCU[1] / ARAMA_OLCU[1]
    en_iyi, en_iyi_dy = None, 0
    egri = []
    for dy in range(0, int(ARAMA_PX / olcek) + 1):
        if dy:
            kes_k, kes_f = k[dy:], f[:-dy]
        else:
            kes_k, kes_f = k, f
        skor = float(np.abs(kes_k - kes_f).mean())
        egri.append((dy, round(skor, 3)))
        if en_iyi is None or skor < en_iyi:
            en_iyi, en_iyi_dy = skor, dy
    kayma = int(round(en_iyi_dy * olcek))
    return {"olculen_kayma_kapak_px": kayma, "arama_skoru": round(en_iyi, 3),
            "kayma_egrisi_ilk10": egri[:10], "kaynak_sure_sn": round(sure, 3)}


def hiza_olc(kapak):
    """Kapaktaki altin bolgelerin dikey konumu (simge/yazi hizasi).

    artwork_mask'in uc bolgesi ayri ayri olculur: her bolgede maskeli
    piksellerin en ust, en alt satiri ve agirlik merkezi.
    """
    with Image.open(kapak) as im:
        rgb = im.convert("RGB")
        if rgb.size != KAPAK_OLCU:
            rgb = rgb.resize(KAPAK_OLCU, Image.Resampling.LANCZOS)
        a = np.asarray(rgb, dtype=np.uint8)
    m = artwork_mask(a)
    bolgeler = {"ana_gorsel": (650, 1735), "alt_blok": (1775, 2165), "yazi": (2260, 2425)}
    cikti = {}
    for ad, (y0, y1) in bolgeler.items():
        alt = m[y0:y1]
        if not alt.any():
            cikti[ad] = None
            continue
        satir = np.nonzero(alt.any(axis=1))[0]
        agirlik = float((np.nonzero(alt)[0]).mean())
        cikti[ad] = {"ust": int(y0 + satir.min()), "alt": int(y0 + satir.max()),
                     "merkez": round(y0 + agirlik, 1)}
    return cikti


def altin_olc(kapak):
    """Altin maskesi: ortalama RGB, maske orani ve maske sinir kutusu (hiza)."""
    with Image.open(kapak) as im:
        rgb = im.convert("RGB")
        if rgb.size != KAPAK_OLCU:
            rgb = rgb.resize(KAPAK_OLCU, Image.Resampling.LANCZOS)
        a = np.asarray(rgb, dtype=np.uint8)
    m = artwork_mask(a)
    if not m.any():
        return {"altin_rgb": None, "maske_orani": 0.0, "kutu": None}
    ys, xs = np.nonzero(m)
    return {"altin_rgb": [round(float(x), 1) for x in a[m].astype(np.float32).mean(axis=0)],
            "maske_orani": round(float(m.mean()), 6),
            "kutu": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-ids", default="", help="virgullu ilan kimlikleri")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--referans-kapak", default="", help="karsilastirma icin referans kapak")
    ap.add_argument("--shift-cover-px", type=int, default=0,
                    help="0 = ilan basina olc (varsayilan); >0 = sabit kaydirma")
    ap.add_argument("--still", type=float, default=0.6)
    ap.add_argument("--fade", type=float, default=0.2)
    ap.add_argument("--motion-start", type=float, default=0.4)
    ap.add_argument("--quota-min", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true",
                    help="HENUZ DEVRE DISI - yazma kodu yazilmadi")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: --apply devre disi. Bu surumde Etsy'ye yazma kodu YOK. DUR.")

    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    sec = {x.strip() for x in a.only_ids.split(",") if x.strip()}
    hedefler = [(str(r["id"]), r.get("pair") or "", r.get("title") or "")
                for r in katalog if not sec or str(r["id"]) in sec]
    if a.limit:
        hedefler = hedefler[:a.limit]
    if sec and len(hedefler) != len(sec):
        eksik = sec - {x[0] for x in hedefler}
        raise SystemExit(f"HATA: katalogda yok: {sorted(eksik)}")

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    log(f"KURU DENEME (yazma kodu yok). Hedef {len(hedefler)} ilan. Kota: {kota_once}")

    ref_olcum = altin_olc(a.referans_kapak) if a.referans_kapak and \
        pathlib.Path(a.referans_kapak).exists() else None

    t0, sonuclar = time.time(), []
    for i, (lid, cift, baslik) in enumerate(hedefler, 1):
        is_dir = out / "_is" / lid
        is_dir.mkdir(parents=True, exist_ok=True)
        kayit = {"listing_id": lid, "cift": cift, "durum": "?", "not": ""}
        try:
            if api.remaining is not None and str(api.remaining).isdigit() \
                    and int(api.remaining) < a.quota_min:
                kayit["durum"] = "DURDU"
                kayit["not"] = f"kota tabani: {api.remaining} < {a.quota_min}"
                sonuclar.append(kayit)
                log(f"{eta(i, len(hedefler), t0)} {lid}: kota tabani, DURDU")
                break
            listing = api.get(f"/listings/{lid}", ok404=True) or {}
            gorseller = gallery(api, lid)
            vids = videos(api, lid)
            varyasyon = variation_images(api, shop, lid)
            onkosul = {
                "active": listing.get("state") == "active",
                "gorsel_13": len(gorseller) == 13,
                "tek_video": len(vids) == 1,
                "bes_varyasyon": len(varyasyon) == 5,
                "rank1_var": bool(gorseller and int(gorseller[0].get("rank") or 0) == 1),
                "rank1_varyasyona_bagli_degil": bool(
                    gorseller and gorseller[0].get("listing_image_id") not in
                    {r.get("image_id") for r in varyasyon}),
            }
            if not all(onkosul.values()):
                kayit["durum"] = "ATLANDI"
                kayit["not"] = f"onkosul: {[k for k, v in onkosul.items() if not v]}"
                sonuclar.append(kayit)
                log(f"{eta(i, len(hedefler), t0)} {lid}: ATLANDI {kayit['not']}")
                continue

            canli_kapak = is_dir / "canli_kapak.png"
            canli_video = is_dir / "canli_video.mp4"
            download(gorseller[0].get("url_fullxfull") or gorseller[0].get("url_570xN"),
                     canli_kapak)
            download(video_url(vids[0]), canli_video)

            ad = (cift or lid).replace(" + ", "_").replace(" ", "_")
            yeni_video = out / f"{ad}_{lid}_video.mp4"
            # KAPAK URETILMEZ: ilanin mevcut Gold B kapagi korunur, Drive'a kopyalanir
            kapak_kopya = out / f"{ad}_{lid}_kapak_MEVCUT.png"
            with Image.open(canli_kapak) as im:
                im.convert("RGB").save(kapak_kopya, format="PNG", compress_level=3)

            # kaydirma ILAN BASINA olculur (86 px sabit degil)
            kayma = kayma_olc(canli_kapak, canli_video, is_dir)
            vmeta = video_kur(canli_kapak, canli_video, yeni_video,
                              kayma["olculen_kayma_kapak_px"], a.still, a.fade,
                              a.motion_start)

            # QA: yeni videonun ilk karesi ile KAPAK arasindaki fark (referans: 1.5404)
            yeni_kare0 = is_dir / "yeni_kare0.png"
            extract_frame(yeni_video, yeni_kare0, 0)
            kapak_olcekli = is_dir / "kapak_video_olcusu.png"
            with Image.open(canli_kapak) as im:
                im.convert("RGB").resize(tuple(vmeta["video_px"]),
                                         Image.Resampling.LANCZOS).save(kapak_olcekli)
            kare_mae = mae(yeni_kare0, kapak_olcekli)
            eski_kare0 = is_dir / "eski_kare0.png"
            extract_frame(canli_video, eski_kare0, 0)
            eski_kare_mae = mae(eski_kare0, kapak_olcekli)
            kapak_olcum = altin_olc(canli_kapak)
            kayit.update({
                "durum": "URETILDI",
                "kapak_id": str(gorseller[0].get("listing_image_id")),
                "kapak_px": f"{gorseller[0].get('full_width')}x{gorseller[0].get('full_height')}",
                "video_id": str(vids[0].get("video_id")),
                **{f"video_{k}": v for k, v in vmeta.items()},
                **kayma,
                "yeni_kare_kapak_mae": round(kare_mae, 4),
                "referans_1_54_fark": round(kare_mae - 1.5404, 4),
                "eski_kare_kapak_mae": round(eski_kare_mae, 4),
                "altin_rgb_kapak": kapak_olcum["altin_rgb"],
                "maske_orani_kapak": kapak_olcum["maske_orani"],
                "maske_kutusu_kapak": kapak_olcum["kutu"],
                "hiza": hiza_olc(canli_kapak),
                "video_dosya": yeni_video.name,
                "kapak_dosya": kapak_kopya.name,
                "kota": api.remaining,
                "_olcum": kapak_olcum,
            })
            log(f"{eta(i, len(hedefler), t0)} {lid} {cift}: URETILDI | "
                f"kayma {kayma['olculen_kayma_kapak_px']} px | "
                f"kare-kapak MAE {kare_mae:.3f} (eski video {eski_kare_mae:.3f}) | "
                f"altin {kapak_olcum['altin_rgb']} | kota={api.remaining}")
        except Exception as ex:                                   # noqa: BLE001
            kayit["durum"] = "HATA"
            kayit["not"] = f"{type(ex).__name__}: {ex}"
            log(f"{eta(i, len(hedefler), t0)} {lid}: HATA {kayit['not'][:160]}")
        sonuclar.append(kayit)

    # referans olcumu: once --referans-kapak, yoksa bu kosuda uretilen referans kapagi
    if ref_olcum is None:
        ref_satir = next((x for x in sonuclar
                          if x["listing_id"] == REFERANS_ID and x["durum"] == "URETILDI"), None)
        ref_olcum = ref_satir.get("_olcum") if ref_satir else None
    for kayit in sonuclar:
        olc = kayit.pop("_olcum", None)
        if not (ref_olcum and olc and ref_olcum.get("altin_rgb") and olc.get("altin_rgb")):
            continue
        fark = [round(olc["altin_rgb"][j] - ref_olcum["altin_rgb"][j], 1) for j in range(3)]
        kayit["ref_altin_fark"] = fark
        kayit["ref_altin_ort_fark"] = round(sum(abs(x) for x in fark) / 3, 2)
        kayit["ref_hedef_2_alti"] = kayit["ref_altin_ort_fark"] < 2.0
        if ref_olcum.get("kutu") and olc.get("kutu"):
            kayit["ref_maske_kutu_fark"] = [olc["kutu"][j] - ref_olcum["kutu"][j]
                                            for j in range(4)]
            kayit["hiza_ayni"] = all(abs(x) <= 12 for x in kayit["ref_maske_kutu_fark"])

    ozet = {"calisma": "KURU DENEME - Etsy'ye yazma YOK",
            "referans_id": REFERANS_ID,
            "hedef": len(hedefler),
            "uretilen": sum(1 for x in sonuclar if x["durum"] == "URETILDI"),
            "atlanan": sum(1 for x in sonuclar if x["durum"] == "ATLANDI"),
            "hata": sum(1 for x in sonuclar if x["durum"] == "HATA"),
            "kota_once": kota_once, "kota_sonra": api.remaining,
            "cagri_ilan_basina": 4,
            "kapak_uretimi": "YOK - ilanin mevcut Gold B kapagi korunur",
            "tarif": {"shift_cover_px": "ilan basina OLCULUR (sabit degil)",
                      "still_sn": a.still,
                      "fade_sn": a.fade, "motion_start_sn": a.motion_start,
                      "kapak_olcu": list(KAPAK_OLCU), "codec": "libx264 crf18 medium",
                      "pix_fmt": "yuv420p", "fps": 30},
            "referans_olcum": ref_olcum, "satirlar": sonuclar}
    (out / "URETIM_SONUC.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    log(json.dumps({k: v for k, v in ozet.items() if k != "satirlar"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
