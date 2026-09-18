#!/usr/bin/env python3
"""4 ornek kapagi REFERANS DUZENINE getirir, videolari yeni kapaga hizalar.

Referans duzeni (kanit: pod-cover-from-video kosulari, roundtrip_mae 0.226,
"exact_visual_source": true): kapak, ilanin KENDI videosunun 0. karesidir.
Uzerine Gold B renk donusumu (config/pod_cover_gold_b_luts.json) uygulanir.

Hiza olcumu GENIS pencerede yapilir; olcum pencere kenarina yapisirsa KABUL
EDILMEZ (KENAR olarak isaretlenir).

Etsy'ye YAZMA YOK: yalniz GET. --apply reddedilir.
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
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    download, gallery, variation_images, videos, video_url,
)
from pod_cover_gold_b_transform import build_candidate, load_luts  # noqa: E402
from match_video_to_cover import extract_frame, mae, probe  # noqa: E402

REFERANS_ID = "4570112095"
KAPAK_OLCU = (2400, 3000)
# GENIS pencere: dar artwork_mask (650-1735 / 1775-2165 / 2260-2425) kenara
# yapisan olcum uretiyordu. Bu pencere poster alaninin tamamini kapsar.
PENCERE = {"y0": 350, "y1": 2750, "x0": 250, "x1": 2150}
KENAR_TOLERANS = 3
ARAMA_PX = 400
ARAMA_OLCU = (600, 750)
UYUMSUZ_ESIK = 10.0


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def eta(i, toplam, t0):
    gecen = time.time() - t0
    kalan = (gecen / i) * (toplam - i) if i else 0
    return (f"[{i}/{toplam} %{i / toplam * 100:4.1f}] gecen {gecen / 60:4.1f} dk, "
            f"kalan ~{kalan / 60:4.1f} dk")


def altin_maske_genis(a):
    """Genis pencerede altin maskesi (artwork_mask ile ayni renk olcutu)."""
    zones = np.zeros(a.shape[:2], dtype=bool)
    zones[PENCERE["y0"]:PENCERE["y1"], PENCERE["x0"]:PENCERE["x1"]] = True
    f = a.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    ham = zones & (r > 44) & (g > 29) & (r > b * 1.16) & (g > b * 1.04) & (r > g * 1.01)
    etiket, _ = ndimage.label(ham, structure=np.ones((3, 3), dtype=np.uint8))
    boyut = np.bincount(etiket.ravel())
    tut = boyut >= 45
    tut[0] = False
    return ndimage.binary_dilation(tut[etiket], iterations=2)


def duzen_olc(kapak):
    """Kapaktaki altin bloklarinin dikey yerlesimi (genis pencere, kenar kontrollu).

    Satir profili uzerinde kesintisiz bloklar bulunur; her blogun ust/alt/merkez
    degeri ve pencere kenarina degip degmedigi raporlanir.
    """
    with Image.open(kapak) as im:
        rgb = im.convert("RGB")
        if rgb.size != KAPAK_OLCU:
            rgb = rgb.resize(KAPAK_OLCU, Image.Resampling.LANCZOS)
        a = np.asarray(rgb, dtype=np.uint8)
    m = altin_maske_genis(a)
    if not m.any():
        return {"bloklar": [], "altin_rgb": None, "maske_orani": 0.0, "kenar": True}
    profil = m.sum(axis=1)
    esik = max(20, int(profil.max() * 0.05))
    dolu = profil >= esik
    bloklar = []
    i = 0
    while i < len(dolu):
        if not dolu[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(dolu) and dolu[j + 1]:
            j += 1
        if j - i >= 15:                      # kucuk gurultuyu at
            agirlik = float((np.arange(i, j + 1) * profil[i:j + 1]).sum()
                            / max(profil[i:j + 1].sum(), 1))
            bloklar.append({"ust": int(i), "alt": int(j), "merkez": round(agirlik, 1),
                            "yukseklik": int(j - i + 1),
                            "piksel": int(profil[i:j + 1].sum())})
        i = j + 1
    bloklar.sort(key=lambda x: -x["piksel"])
    kenar = any(b["ust"] <= PENCERE["y0"] + KENAR_TOLERANS
                or b["alt"] >= PENCERE["y1"] - KENAR_TOLERANS for b in bloklar)
    ys, xs = np.nonzero(m)
    kenar = kenar or xs.min() <= PENCERE["x0"] + KENAR_TOLERANS \
        or xs.max() >= PENCERE["x1"] - KENAR_TOLERANS
    return {"bloklar": bloklar[:4], "altin_rgb":
            [round(float(x), 1) for x in a[m].astype(np.float32).mean(axis=0)],
            "maske_orani": round(float(m.mean()), 6), "kenar": bool(kenar)}


def _gri(yol, olcu):
    with Image.open(yol) as im:
        return np.asarray(im.convert("L").resize(olcu, Image.Resampling.LANCZOS),
                          dtype=np.float32)


def kayma_olc(kapak, video, is_dir, etiket=""):
    """Kapak ile videonun son karesi arasindaki dikey kayma (kapak uzayinda)."""
    meta = probe(video)
    sure = float(meta["format"]["duration"])
    son = is_dir / f"son_kare{etiket}.png"
    extract_frame(video, son, max(sure - 0.15, 0.0))
    k, f = _gri(kapak, ARAMA_OLCU), _gri(son, ARAMA_OLCU)
    olcek = KAPAK_OLCU[1] / ARAMA_OLCU[1]
    en_iyi, en_iyi_dy = None, 0
    for dy in range(0, int(ARAMA_PX / olcek) + 1):
        kk, ff = (k[dy:], f[:-dy]) if dy else (k, f)
        skor = float(np.abs(kk - ff).mean())
        if en_iyi is None or skor < en_iyi:
            en_iyi, en_iyi_dy = skor, dy
    return {"olculen_kayma_kapak_px": int(round(en_iyi_dy * olcek)),
            "arama_skoru": round(en_iyi, 3), "kaynak_sure_sn": round(sure, 3)}


def kapak_uret(video, is_dir, hedef, luts):
    """Referans duzeni: video 0. karesi -> 2400x3000 -> Gold B LUT."""
    ham = is_dir / "video_kare0.png"
    extract_frame(video, ham, 0)
    with Image.open(ham) as im:
        rgb = im.convert("RGB")
        if rgb.width * 5 != rgb.height * 4:
            raise RuntimeError(f"video ilk karesi 4:5 degil: {rgb.size}")
        taban = np.asarray(rgb.resize(KAPAK_OLCU, Image.Resampling.LANCZOS), dtype=np.uint8)
    aday, qa = build_candidate(taban, luts)
    Image.fromarray(aday, mode="RGB").save(hedef, format="PNG", compress_level=3)
    taban_yolu = is_dir / "kapak_goldb_oncesi.png"
    Image.fromarray(taban, mode="RGB").save(taban_yolu, format="PNG", compress_level=3)
    return qa, ham, taban_yolu


def video_kur(kapak, kaynak, cikti, kayma_kapak_px, still, fade, motion_start):
    meta = probe(kaynak)
    akis = meta["streams"][0]
    w, h = int(akis["width"]), int(akis["height"])
    sure = float(meta["format"]["duration"])
    shift = round(kayma_kapak_px * h / KAPAK_OLCU[1])
    if shift % 2:
        shift += 1
    fade_offset = still - fade
    if shift > 0:
        ust = max(8, min(32, shift))
        hareket = (f"[1:v]fps=30,setpts=PTS-STARTPTS,split=2[m0][t0];"
                   f"[t0]crop={w}:{ust}:0:0,vflip,scale={w}:{shift}:flags=lanczos[top];"
                   f"[m0]crop={w}:{h - shift}:0:0[body];[top][body]vstack=inputs=2[shifted];")
    else:
        ust = 0
        hareket = "[1:v]fps=30,setpts=PTS-STARTPTS[shifted];"
    graf = (f"[0:v]scale={w}:{h}:flags=lanczos,fps=30[s0];"
            f"[s0]trim=duration={still},setpts=PTS-STARTPTS[still];" + hareket +
            f"[shifted]trim=start={motion_start},setpts=PTS-STARTPTS[motion];"
            f"[still][motion]xfade=transition=fade:duration={fade}:offset={fade_offset}[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(kapak),
                    "-i", str(kaynak), "-filter_complex", graf, "-map", "[out]", "-an",
                    "-t", f"{sure:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(cikti)], check=True)
    return {"video_px": [w, h], "sure_sn": round(sure, 3), "shift_px": shift,
            "ust_ayna_px": ust, "still_sn": still, "fade_sn": fade}


def video_kimlik(kare0, kaynak_dizin, is_dir, en_fazla=90):
    """Videonun hangi cifte ait oldugunu Drive kaynak videolariyla esler."""
    kok = pathlib.Path(kaynak_dizin)
    if not kok.exists():
        return {"durum": "kaynak dizin yok", "adaylar": []}
    hedef = _gri(kare0, (320, 400))
    adaylar = []
    for i, mp4 in enumerate(sorted(kok.glob("*.mp4"))):
        if i >= en_fazla:
            break
        k = is_dir / f"kaynak_{mp4.stem}.png"
        try:
            extract_frame(mp4, k, 0)
            skor = float(np.abs(hedef - _gri(k, (320, 400))).mean())
        except Exception:                                         # noqa: BLE001
            continue
        adaylar.append({"dosya": mp4.name, "mae": round(skor, 3)})
        k.unlink(missing_ok=True)
    adaylar.sort(key=lambda x: x["mae"])
    return {"durum": "olculdu", "taranan": len(adaylar), "adaylar": adaylar[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--luts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-ids", required=True)
    ap.add_argument("--kaynak-video-dizin", default="")
    ap.add_argument("--kanit-dizin", default="", help="POD_COVER_FROM_VIDEO kanitlari")
    ap.add_argument("--still", type=float, default=0.6)
    ap.add_argument("--fade", type=float, default=0.2)
    ap.add_argument("--motion-start", type=float, default=0.4)
    ap.add_argument("--quota-min", type=int, default=100)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        raise SystemExit("HATA: --apply devre disi. Etsy'ye yazma kodu YOK. DUR.")

    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    luts = load_luts(pathlib.Path(a.luts))
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    sec = [x.strip() for x in a.only_ids.split(",") if x.strip()]
    bilgi = {str(r["id"]): (r.get("pair") or "", r.get("title") or "") for r in katalog}
    hedefler = [(i, *bilgi[i]) for i in sec if i in bilgi]

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    log(f"KURU DENEME. {len(hedefler)} ilan. Kota: {kota_once}")

    t0, sonuclar = time.time(), []
    for i, (lid, cift, _) in enumerate(hedefler, 1):
        is_dir = out / "_is" / lid
        is_dir.mkdir(parents=True, exist_ok=True)
        ad = (cift or lid).replace(" + ", "_").replace(" ", "_")
        kayit = {"listing_id": lid, "cift": cift, "durum": "?", "not": ""}
        try:
            listing = api.get(f"/listings/{lid}", ok404=True) or {}
            gorseller = gallery(api, lid)
            vids = videos(api, lid)
            varyasyon = variation_images(api, shop, lid)
            if not (gorseller and vids):
                raise RuntimeError("gorsel veya video yok")
            mevcut_kapak = is_dir / "mevcut_kapak.png"
            canli_video = is_dir / "canli_video.mp4"
            download(gorseller[0].get("url_fullxfull") or gorseller[0].get("url_570xN"),
                     mevcut_kapak)
            download(video_url(vids[0]), canli_video)
            mevcut_kopya = out / f"{ad}_{lid}_kapak_MEVCUT.png"
            with Image.open(mevcut_kapak) as im:
                im.convert("RGB").save(mevcut_kopya, format="PNG", compress_level=3)

            yeni_kapak = out / f"{ad}_{lid}_kapak_YENI.png"
            qa, kare0, taban = kapak_uret(canli_video, is_dir, yeni_kapak, luts)
            duzen_yeni = duzen_olc(yeni_kapak)
            duzen_mevcut = duzen_olc(mevcut_kapak)
            kayma = kayma_olc(yeni_kapak, canli_video, is_dir)
            uyumsuz = kayma["arama_skoru"] > UYUMSUZ_ESIK
            kayit.update({
                "durum": "URETILDI", "kapak_id": str(gorseller[0].get("listing_image_id")),
                "video_id": str(vids[0].get("video_id")),
                "gorsel_sayisi": len(gorseller), "varyasyon": len(varyasyon),
                "state": listing.get("state"),
                "goldb_qa": qa, "duzen_yeni": duzen_yeni, "duzen_mevcut": duzen_mevcut,
                **kayma, "video_uyumsuz": uyumsuz,
                "kapak_dosya_yeni": yeni_kapak.name,
                "kapak_dosya_mevcut": mevcut_kopya.name, "kota": api.remaining,
            })
            if uyumsuz:
                kayit["not"] = (f"video uyumsuz: arama skoru {kayma['arama_skoru']} > "
                                f"{UYUMSUZ_ESIK}; video URETILMEDI")
                kayit["kimlik"] = video_kimlik(kare0, a.kaynak_video_dizin, is_dir)
                # kanit gorseli: video ilk karesi | mevcut kapak
                with Image.open(kare0) as k, Image.open(mevcut_kapak) as m:
                    kk = k.convert("RGB").resize((700, 875), Image.Resampling.LANCZOS)
                    mm = m.convert("RGB").resize((700, 875), Image.Resampling.LANCZOS)
                    yan = Image.new("RGB", (1414, 875), (240, 240, 240))
                    yan.paste(kk, (0, 0))
                    yan.paste(mm, (714, 0))
                    yan.save(out / f"UYUMSUZ_{ad}_{lid}.jpg", quality=90)
                log(f"{eta(i, len(hedefler), t0)} {lid} {cift}: VIDEO UYUMSUZ "
                    f"(skor {kayma['arama_skoru']}) | en yakin kaynak: "
                    f"{(kayit['kimlik'].get('adaylar') or [{}])[0].get('dosya', '?')}")
            else:
                yeni_video = out / f"{ad}_{lid}_video.mp4"
                vmeta = video_kur(yeni_kapak, canli_video, yeni_video,
                                  kayma["olculen_kayma_kapak_px"], a.still, a.fade,
                                  a.motion_start)
                yk0 = is_dir / "yeni_video_kare0.png"
                extract_frame(yeni_video, yk0, 0)
                kapak_olcekli = is_dir / "kapak_video_olcusu.png"
                with Image.open(yeni_kapak) as im:
                    im.convert("RGB").resize(tuple(vmeta["video_px"]),
                                             Image.Resampling.LANCZOS).save(kapak_olcekli)
                kayit.update({**{f"video_{k}": v for k, v in vmeta.items()},
                              "yeni_kare_kapak_mae": round(mae(yk0, kapak_olcekli), 4),
                              "video_dosya": yeni_video.name})
                log(f"{eta(i, len(hedefler), t0)} {lid} {cift}: URETILDI | kayma "
                    f"{kayma['olculen_kayma_kapak_px']} px | kare-kapak MAE "
                    f"{kayit['yeni_kare_kapak_mae']} | kenar={duzen_yeni['kenar']}")
        except Exception as ex:                                   # noqa: BLE001
            kayit["durum"] = "HATA"
            kayit["not"] = f"{type(ex).__name__}: {ex}"
            log(f"{eta(i, len(hedefler), t0)} {lid}: HATA {kayit['not'][:180]}")
        sonuclar.append(kayit)

    # referans ile hiza/renk farki
    ref = next((x for x in sonuclar if x["listing_id"] == REFERANS_ID
                and x["durum"] == "URETILDI"), None)
    if ref:
        rb = ref["duzen_yeni"]["bloklar"]
        for k in sonuclar:
            if k["durum"] != "URETILDI" or not k.get("duzen_yeni"):
                continue
            kb = k["duzen_yeni"]["bloklar"]
            farklar = []
            for j in range(min(len(rb), len(kb))):
                farklar.append({"blok": j + 1,
                                "ust_fark": kb[j]["ust"] - rb[j]["ust"],
                                "alt_fark": kb[j]["alt"] - rb[j]["alt"],
                                "merkez_fark": round(kb[j]["merkez"] - rb[j]["merkez"], 1)})
            k["hiza_fark"] = farklar
            k["hiza_5px_alti"] = bool(farklar) and all(
                abs(f["ust_fark"]) <= 5 and abs(f["alt_fark"]) <= 5
                and abs(f["merkez_fark"]) <= 5 for f in farklar)
            ra, ka = ref["duzen_yeni"]["altin_rgb"], k["duzen_yeni"]["altin_rgb"]
            if ra and ka:
                k["renk_fark"] = [round(ka[j] - ra[j], 1) for j in range(3)]
                k["renk_ort_fark"] = round(sum(abs(x) for x in k["renk_fark"]) / 3, 2)

    # kanit zinciri
    zincir = []
    if a.kanit_dizin and pathlib.Path(a.kanit_dizin).exists():
        for p in sorted(pathlib.Path(a.kanit_dizin).rglob("result.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:                                     # noqa: BLE001
                continue
            zincir.append({"kanit": str(p.parent.name),
                           "eski_kapak": d.get("old_cover_id"),
                           "yeni_kapak": d.get("new_cover_id"),
                           "mobil_lut": (d.get("qa") or {}).get("mobile_display_compensation"),
                           "roundtrip_mae": (d.get("qa") or {}).get("roundtrip_mae"),
                           "kaynak_video": (d.get("qa") or {}).get("source_video_id"),
                           "yeniden_kullanim": d.get("reused_existing_candidate")})
    ozet = {"calisma": "KURU DENEME - Etsy'ye yazma YOK", "referans_id": REFERANS_ID,
            "pencere": PENCERE, "uyumsuz_esik": UYUMSUZ_ESIK,
            "kota_once": kota_once, "kota_sonra": api.remaining,
            "cagri_ilan_basina": 4, "kapak_zinciri": zincir,
            "tarif": {"duzen": "ilanin kendi videosunun 0. karesi -> 2400x3000 LANCZOS",
                      "renk": "Gold B LUT (config/pod_cover_gold_b_luts.json), "
                              "artwork_mask icinde, geometri degismez",
                      "mobil_lut": "UYGULANMADI",
                      "still_sn": a.still, "fade_sn": a.fade,
                      "motion_start_sn": a.motion_start,
                      "codec": "libx264 crf18 medium", "fps": 30},
            "satirlar": sonuclar}
    (out / "URETIM_SONUC.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    log(json.dumps({k: v for k, v in ozet.items()
                    if k not in ("satirlar", "kapak_zinciri")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
