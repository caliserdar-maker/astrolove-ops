#!/usr/bin/env python3
"""V11 TOPLU URETIM: 77 cift (Aquarius+Gemini haric).

Yontem SABIT (pod_sablon_v11): panel ici, ciftin V01 MIDNIGHT_BLUE videosundan
referansin donusumuyle (olcek 1.1607, tx -106.1, ty -4.4); panel disi
referansin baytlari; kapak = kare 0 -> 2400x3000 LANCZOS -> Gold B.

Her cift: uret -> kontrol -> Drive'a yukle -> yerelden sil -> state.json.
Yeniden baslatilabilir: Drive'daki state.json'da PASS olan cift atlanir.
Etsy: yalniz GET (referans video 843084674).
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_cover_from_video import download, videos, video_url  # noqa: E402
from pod_cover_gold_b_transform import load_luts  # noqa: E402
from pod_sablon_v11 import (KAPAK, OLCEK, PANEL, TX, TY, kareler,  # noqa: E402
                            uret)
from pod_sablon_v4 import yuv_ac  # noqa: E402

REFERANS_ILAN = "4570112095"
REFERANS_CIFT = "AQUARIUS_GEMINI"
ED = "MIDNIGHT_BLUE"
DRV = "gdrive:ASTROLOVE/TEMP/POD_V11_URETIM"
EXP = ("gdrive:ASTROLOVE/WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/"
       f"01_EXPORTS/{ED}")
CIFT_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
CRF = 6
SUTUN = ["cift", "ilan_id", "sonuc", "not", "panel_disi_mae", "panel_disi_en_cok",
         "panel_ici_mae", "kare", "video_boyut", "kapak_boyut", "kapak_kare0_mae",
         "sn"]
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def ciftler():
    veri = json.loads(CIFT_JSON.read_text(encoding="utf-8"))
    cikti = []
    for r in veri:
        ad = r.get("pair", "")
        if not ad:
            continue
        anahtar = ad.replace(" + ", "_").replace(" ", "_").upper()
        cikti.append((anahtar, str(r.get("id", ""))))
    return sorted(set(cikti))


def durum_oku(yerel):
    r = rclone("copyto", f"{DRV}/state.json", str(yerel))
    if r.returncode == 0 and yerel.is_file():
        try:
            return json.loads(yerel.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"tamamlanan": {}, "basarisiz": {}}


def durum_yaz(durum, yerel):
    yerel.write_text(json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(yerel), f"{DRV}/state.json")


def kucuk(yol, w=300):
    with Image.open(yol) as im:
        return im.convert("RGB").resize((w, round(w * im.height / im.width)),
                                        Image.LANCZOS)


def tablo(hucreler, hedef, sutun=13, en_cok_mb=3.0):
    """13 sutunlu izgara; her hucrede cift adi. Telefonda okunur (hucre 300 px)."""
    if not hucreler:
        raise SystemExit("HATA: tablo icin hucre yok")
    hw, hh = hucreler[0][1].size
    basl = 34
    satir = (len(hucreler) + sutun - 1) // sutun
    tuval = Image.new("RGB", (sutun * hw, satir * (hh + basl)), (250, 250, 250))
    ciz = ImageDraw.Draw(tuval)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (ad, im) in enumerate(hucreler):
        x, y = (i % sutun) * hw, (i // sutun) * (hh + basl)
        ciz.text((x + 6, y + 6), ad.replace("_", " + ").title(), fill=(15, 15, 15), font=font)
        tuval.paste(im, (x, y + basl))
    for q in (92, 88, 84, 80, 75, 70, 65, 60, 55, 50, 45, 40):
        tuval.save(hedef, quality=q, optimize=True)
        if hedef.stat().st_size <= en_cok_mb * 1e6:
            break
    return hedef.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/v11u")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--luts", default="config/pod_cover_gold_b_luts.json")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    (isd / "_is").mkdir(parents=True, exist_ok=True)
    (isd / "kucuk").mkdir(exist_ok=True)

    # referans canli video (Etsy GET)
    ref_video = isd / "referans.mp4"
    if not ref_video.is_file():
        st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                        os.environ.get("ETSY_SHARED_SECRET"))
        if st.needs_refresh():
            st.refresh()
        api = Etsy(st)
        vid = videos(api, REFERANS_ILAN)
        if not vid:
            raise SystemExit("HATA: referans videosu yok")
        download(video_url(vid[0]), ref_video)
        ilerle(f"referans video indi (id {vid[0].get('video_id')}) kota {api.remaining}")

    meta = probe(ref_video)["streams"][0]
    vw, vh = int(meta["width"]), int(meta["height"])
    p, q = (meta.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = round(float(p) / float(q), 3)
    ref_veri, kare_bayt, adet = yuv_ac(ref_video, isd / "_is" / "ref.yuv", vw, vh)
    ref_rgb = kareler(ref_video)
    luts = load_luts(pathlib.Path(a.luts))
    ilerle(f"referans {vw}x{vh} {adet} kare {fps} fps | donusum {OLCEK}/{TX}/{TY} "
           f"| panel {PANEL}")

    # referansin kendi kareleri tablolara girer
    Image.fromarray(ref_rgb[0]).save(isd / "kucuk" / f"{REFERANS_CIFT}_k0.png")
    Image.fromarray(ref_rgb[90]).save(isd / "kucuk" / f"{REFERANS_CIFT}_k90.png")

    durum_yerel = isd / "state.json"
    durum = durum_oku(durum_yerel)
    hepsi = [(c, i) for c, i in ciftler() if c != REFERANS_CIFT]
    if a.limit:
        hepsi = hepsi[:a.limit]
    kalan = [(c, i) for c, i in hepsi if c not in durum["tamamlanan"]]
    ilerle(f"toplam {len(hepsi)} cift | tamamlanan {len(durum['tamamlanan'])} | "
           f"kosulacak {len(kalan)}")

    rapor = isd / "URETIM_RAPORU.csv"
    if not rapor.is_file():
        rclone("copyto", f"{DRV}/URETIM_RAPORU.csv", str(rapor))
    if not rapor.is_file():
        with rapor.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(SUTUN)

    t0 = time.time()
    for j, (cift, ilan) in enumerate(kalan, start=1):
        ts = time.time()
        satir = {"cift": cift, "ilan_id": ilan, "sonuc": "BASARISIZ", "not": ""}
        try:
            v01 = isd / f"v01_{cift}.mp4"
            r = rclone("copyto", f"{EXP}/WA_VIDEO_V01_{cift}_{ED}.mp4", str(v01))
            if r.returncode != 0 or not v01.is_file():
                raise RuntimeError("V01 videosu inmedi")
            k = uret(cift, v01, ref_video, ref_rgb, ref_veri, kare_bayt, adet,
                     vw, vh, fps, adet / fps, isd, luts, crf=CRF)
            video = isd / f"{cift}_V11.mp4"
            kapak = isd / f"{cift}_kapak_V11.png"
            vm = probe(video)["streams"][0]
            vb = f"{vm['width']}x{vm['height']}"
            n_kare = int(vm.get("nb_frames") or k["kare"])
            with Image.open(kapak) as im:
                kb = f"{im.width}x{im.height}"
            # kapak <-> video kare 0 uyumu (Gold B oncesi taban)
            kk = isd / "_is" / f"{cift}_k0b.png"
            extract_frame(video, kk, 0)
            with Image.open(kk) as im:
                taban = np.asarray(im.convert("RGB").resize(KAPAK, Image.LANCZOS),
                                   dtype=np.float32)
            with Image.open(isd / "_is" / f"{cift}_kare0.png") as im:
                taban2 = np.asarray(im.convert("RGB").resize(KAPAK, Image.LANCZOS),
                                    dtype=np.float32)
            k0mae = float(np.abs(taban - taban2).mean())
            satir.update({"panel_disi_mae": k["panel_disi_mae_ort"],
                          "panel_disi_en_cok": k["panel_disi_mae_en_kotu"],
                          "panel_ici_mae": k["panel_ici_mae_ort"],
                          "kare": n_kare, "video_boyut": vb, "kapak_boyut": kb,
                          "kapak_kare0_mae": round(k0mae, 4)})
            sorun = []
            if k["panel_disi_mae_ort"] >= 0.5:
                sorun.append(f"panel disi MAE {k['panel_disi_mae_ort']}")
            if vb != f"{vw}x{vh}":
                sorun.append(f"video boyut {vb}")
            if n_kare != 138:
                sorun.append(f"kare {n_kare}")
            if abs(fps - 30.0) > 0.01:
                sorun.append(f"fps {fps}")
            if kb != f"{KAPAK[0]}x{KAPAK[1]}":
                sorun.append(f"kapak boyut {kb}")
            if k0mae >= 1.0:
                sorun.append(f"kapak-kare0 MAE {k0mae:.3f}")
            if sorun:
                satir["not"] = " | ".join(sorun)
            else:
                satir["sonuc"] = "GECTI"
                for yerel, uzak in ((video, f"{DRV}/VIDEO/{cift}_V11.mp4"),
                                    (kapak, f"{DRV}/KAPAK/{cift}_V11_kapak.png")):
                    ru = rclone("copyto", str(yerel), uzak)
                    if ru.returncode != 0:
                        satir["sonuc"] = "BASARISIZ"
                        satir["not"] = f"yukleme: {ru.stderr.strip()[-80:]}"
            if satir["sonuc"] == "GECTI":
                kareler_v = kareler(video)
                for i, ad in ((0, "k0"), (90, "k90")):
                    Image.fromarray(kareler_v[i]).resize((300, 375), Image.LANCZOS) \
                        .save(isd / "kucuk" / f"{cift}_{ad}.png")
                del kareler_v
                durum["tamamlanan"][cift] = {"ilan": ilan,
                                             "panel_disi": k["panel_disi_mae_ort"]}
                durum["basarisiz"].pop(cift, None)
            else:
                durum["basarisiz"][cift] = satir["not"]
            for f in (video, kapak, v01, isd / "_is" / f"{cift}.yuv",
                      isd / "_is" / f"{cift}_geri.yuv",
                      isd / "_is" / f"{cift}_kare0.png", kk):
                pathlib.Path(f).unlink(missing_ok=True)
        except Exception as e:  # tek cift duserse kosu devam eder
            satir["not"] = f"{type(e).__name__}: {e}"[:160]
            durum["basarisiz"][cift] = satir["not"]
        satir["sn"] = round(time.time() - ts, 1)
        with rapor.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore").writerow(satir)
        durum_yaz(durum, durum_yerel)
        gec = time.time() - t0
        ilerle(f"{j}/{len(kalan)} (%{100 * j / len(kalan):.1f}) {cift} "
               f"{satir['sonuc']} {satir['not'][:40]} | gecen {sure_yaz(gec)} "
               f"kalan ~{sure_yaz(gec / j * (len(kalan) - j))}")

    # tablolar (referans dahil 78)
    ad_sirali = [REFERANS_CIFT] + [c for c, _ in hepsi]
    for ek, hedef in (("k0", "KAPAK_TABLOSU.jpg"), ("k90", "ORTA_KARE_TABLOSU.jpg")):
        hucre = []
        for c in ad_sirali:
            yol = isd / "kucuk" / f"{c}_{ek}.png"
            if yol.is_file():
                hucre.append((c, kucuk(yol, 300)))
        boy = tablo(hucre, isd / hedef)
        rclone("copyto", str(isd / hedef), f"{DRV}/{hedef}")
        ilerle(f"{hedef}: {len(hucre)} hucre, {boy / 1e6:.2f} MB")
    rclone("copyto", str(rapor), f"{DRV}/URETIM_RAPORU.csv")
    ilerle(f"BITTI | gecti {len(durum['tamamlanan'])} | basarisiz "
           f"{len(durum['basarisiz'])} -> {list(durum['basarisiz'])[:10]}")
    print(json.dumps({"gecti": len(durum["tamamlanan"]),
                      "basarisiz": durum["basarisiz"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
