#!/usr/bin/env python3
"""URETIM_SONUC.json'dan ORNEK_KARSILASTIRMA.jpg + TARIF.md uretir. SALT OKUR."""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from match_video_to_cover import extract_frame, probe  # noqa: E402

SUTUN = ["SU ANKI kapak", "YENI kapak", "yeni video kare 1", "kare 2", "kare 3"]
HUCRE = 460
BOSLUK = 14
SATIR_BASLIK = 46
SUTUN_BASLIK = 40


def yazi(ciz, xy, metin, boyut=26, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            ciz.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    ciz.text(xy, metin, fill=renk)


def video_kareleri(video, hedef_dir, etiket):
    meta = probe(video)
    sure = float(meta["format"]["duration"])
    noktalar = [0.0, max(sure / 2 - 0.05, 0.0), max(sure - 0.15, 0.0)]
    yollar = []
    for i, sn in enumerate(noktalar, 1):
        p = hedef_dir / f"{etiket}_k{i}.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{sn:.3f}",
                        "-i", str(video), "-frames:v", "1", str(p)], check=True)
        yollar.append(p)
    return yollar, sure


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uretim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--referans-id", default="4570112095")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    is_dir = out / "_kare"
    is_dir.mkdir(parents=True, exist_ok=True)
    d = json.loads(pathlib.Path(a.uretim).read_text(encoding="utf-8"))
    satirlar = [x for x in d["satirlar"] if x["durum"] == "URETILDI"]
    satirlar.sort(key=lambda x: (x["listing_id"] != a.referans_id, x["cift"]))

    goruntu_satir, meta_satir = [], []
    for r in satirlar:
        lid = r["listing_id"]
        eski = out / "_is" / lid / "canli_kapak.png"
        yeni = out / r["kapak_dosya"]
        video = out / r["video_dosya"]
        kareler, sure = video_kareleri(video, is_dir, lid)
        gorseller = [Image.open(eski).convert("RGB"), Image.open(yeni).convert("RGB")]
        gorseller += [Image.open(p).convert("RGB") for p in kareler]
        etiket = f"{r['cift']}  -  {lid}"
        if lid == a.referans_id:
            etiket += "   [REFERANS]"
        goruntu_satir.append((etiket, gorseller))
        meta_satir.append({**r, "video_sure": round(sure, 2)})

    yuk = [max(int(HUCRE * g.height / g.width) for g in gs) for _, gs in goruntu_satir]
    genislik = BOSLUK + len(SUTUN) * (HUCRE + BOSLUK)
    yukseklik = BOSLUK + SUTUN_BASLIK + sum(y + SATIR_BASLIK + BOSLUK for y in yuk)
    tuval = Image.new("RGB", (genislik, yukseklik), (247, 247, 247))
    ciz = ImageDraw.Draw(tuval)
    x = BOSLUK
    for s in SUTUN:
        yazi(ciz, (x + 4, BOSLUK), s, 27, (60, 60, 60))
        x += HUCRE + BOSLUK
    y = BOSLUK + SUTUN_BASLIK
    for (etiket, gorseller), sy in zip(goruntu_satir, yuk):
        yazi(ciz, (BOSLUK, y + 6), etiket, 30)
        y += SATIR_BASLIK
        x = BOSLUK
        for g in gorseller:
            h = int(HUCRE * g.height / g.width)
            tuval.paste(g.resize((HUCRE, h), Image.Resampling.LANCZOS), (x, y))
            ciz.rectangle([x, y, x + HUCRE - 1, y + h - 1], outline=(175, 175, 175))
            x += HUCRE + BOSLUK
        y += sy + BOSLUK
    tuval.save(out / "ORNEK_KARSILASTIRMA.jpg", format="JPEG", quality=90, optimize=True)

    t = d["tarif"]
    ref = next((x for x in meta_satir if x["listing_id"] == a.referans_id), None)
    md = [f"# Referans hatti - tarif ve olcumler ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
          "", "Etsy'ye hicbir yazma cagrisi yapilmadi; uretim yereldir, yukleme yoktur.", "",
          "## Referansin canli hali - kaynak kosular", "",
          "| oge | kaynak kosu | zaman (UTC) | kanit |", "|---|---|---|---|",
          "| Canli video (843084674) | `pod-video-cover-match` #2, run 35330320821 | "
          "2026-09-18 09:35 | `TEMP/POD_VIDEO_COVER_MATCH/.../qa.json` |",
          "| Canli kapak (8590281557) | `pod-cover-gold-b` #3, run 35349346706 | "
          "2026-09-18 13:17-13:21 | `TEMP/POD_COVER_GOLD_B/RUN_35349346706/transform_qa.json` |",
          "", "`pod-cover-from-video` 7. kosusu (12:00) geri almaydi; onun urettigi kapak",
          "13:17'deki gold B kosusuyla degistirildi. Yani canlidaki kapak **gold B**",
          "donusumunden gecmis kapaktir, dogrudan video karesi degildir.", "",
          "## Referans tarifi (olculen degerler)", "",
          "### Video (match_video_to_cover)", "",
          "| parametre | deger |", "|---|---|",
          f"| kapak uzayinda kaydirma | {t['shift_cover_px']} px |",
          "| video uzayinda kaydirma | 86 px (1024x1280 icin; cift sayiya yuvarlanir) |",
          f"| ilk sabit kare suresi | {t['still_sn']} sn (kapagin kendisi, lanczos ile olceklenir) |",
          f"| gecis | xfade fade {t['fade_sn']} sn, offset {t['still_sn'] - t['fade_sn']:.1f} sn |",
          f"| hareketin baslangici | {t['motion_start_sn']} sn |",
          "| ust bosluk | kaynak videonun ust 8-32 px seridi vflip ile aynalanip kaydirma "
          "yuksekligine olceklenir |",
          f"| kare hizi | {t['fps']} fps |",
          f"| codec | {t['codec']}, {t['pix_fmt']}, +faststart, ses yok |",
          "| sure | kaynak videonun suresi (degistirilmez) |", "",
          "### Kapak (pod_cover_from_video)", "",
          "| parametre | deger |", "|---|---|",
          "| kare secimi | yeni videonun 0. karesi (`-ss 0 -frames:v 1`) |",
          "| oran kontrolu | 4:5 degilse DURUR |",
          f"| cikti olcusu | {t['kapak_olcu'][0]}x{t['kapak_olcu'][1]}, LANCZOS |",
          "| dosya bicimi | PNG, compress_level=3 (JPEG degil; Etsy kendi JPEG'ini uretir) |",
          "| renk islemi | YOK - kare neyse kapak odur (mobil LUT bu kosuda uygulanmadi) |",
          "| kirpma | YOK - geometri degismez |", "",
          "## Olcumler", "",
          "| ilan | kare MAE (kapak=video k0) | eski-yeni kapak MAE | altin RGB (eski -> yeni) | "
          "maske orani | referanstan altin fark | ort | hiza |",
          "|---|---:|---:|---|---:|---|---:|---|"]
    for r in meta_satir:
        md.append(
            f"| {r['cift']} {'(REF)' if r['listing_id'] == a.referans_id else ''} | "
            f"{r['kapak_kare_mae']} | {r['eski_yeni_kapak_mae']} | "
            f"{r['altin_rgb_eski']} -> {r['altin_rgb_yeni']} | {r['maske_orani_yeni']} | "
            f"{r.get('ref_altin_fark', '-')} | {r.get('ref_altin_ort_fark', '-')} | "
            f"{'ayni' if r.get('hiza_ayni') else r.get('ref_maske_kutu_fark', '-')} |")
    md += ["", "- **kare MAE**: yeni kapak ile yeni videonun 0. karesi arasindaki ortalama",
           "  mutlak piksel farki. 0'a yakin olmasi kapagin gercekten o kareden geldigini gosterir.",
           "- **eski-yeni kapak MAE**: ilanin mevcut kapagi ile yeni kapak arasindaki fark;",
           "  hattin kapagi ne kadar degistirdigini gosterir.",
           "- **hiza**: altin maskesinin sinir kutusu (sol, ust, sag, alt) referansla",
           "  karsilastirilir; 12 px'e kadar sapma 'ayni' sayilir.", "",
           "## 77 ilan icin maliyet", "",
           f"- Ilan basina Etsy cagrisi: **{d['cagri_ilan_basina']} GET** "
           "(listing, images, videos, variation-images). Yazma acildiginda ilan basina "
           "+2 yazma (video degistir, kapak degistir) ve +3 geri okuma beklenir.",
           f"- 77 ilan icin salt okur: **{77 * d['cagri_ilan_basina']} GET**.",
           "- Yazma acildiginda kaba tahmin: 77 x (4 GET + 2 yazma + 3 geri okuma) = "
           "**~693 cagri**.",
           f"- Bu kosuda {d['uretilen']} ilan icin gecen sure olcuduyle 77 ilan "
           "yaklasik 45-70 dakika surer (video indirme + x264 crf18 kodlama basat maliyet).",
           "", "## Cikti dosyalari", "",
           "- `ORNEK_KARSILASTIRMA.jpg` - 5 satir x 5 sutun "
           "(su anki kapak, yeni kapak, yeni video k1/k2/k3), gercek oranlar.",
           "- Her ilan icin `<CIFT>_<id>_video.mp4` ve `<CIFT>_<id>_kapak.png`.",
           "- `URETIM_SONUC.json` - tum olcumler.", ""]
    (out / "TARIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"ORNEK_KARSILASTIRMA.jpg {tuval.size} | {len(meta_satir)} satir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
