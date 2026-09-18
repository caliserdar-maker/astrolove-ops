#!/usr/bin/env python3
"""URETIM_SONUC.json'dan ORNEK_KARSILASTIRMA.jpg + TARIF.md uretir. SALT OKUR.

Sutunlar: kapak | SU ANKI video kare 1 | YENI video kare 1 | yeni kare 2 | yeni kare 3.
"""
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
from match_video_to_cover import probe  # noqa: E402

SUTUN = ["kapak (mevcut Gold B)", "SU ANKI video k1", "YENI video k1",
         "YENI video k2", "YENI video k3"]
HUCRE = 470
BOSLUK = 14
SATIR_BASLIK = 48
SUTUN_BASLIK = 42
BOLGE_AD = {"ana_gorsel": "ana gorsel", "alt_blok": "alt blok", "yazi": "yazi"}


def yazi(ciz, xy, metin, boyut=26, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            ciz.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    ciz.text(xy, metin, fill=renk)


def kare_al(video, hedef, sn):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{sn:.3f}",
                    "-i", str(video), "-frames:v", "1", str(hedef)], check=True)
    return hedef


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uretim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--referans-id", default="4570112095")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    kare_dir = out / "_kare"
    kare_dir.mkdir(parents=True, exist_ok=True)
    d = json.loads(pathlib.Path(a.uretim).read_text(encoding="utf-8"))
    satirlar = [x for x in d["satirlar"] if x["durum"] == "URETILDI"]
    satirlar.sort(key=lambda x: (x["listing_id"] != a.referans_id, x["cift"]))

    goruntu, meta = [], []
    for r in satirlar:
        lid = r["listing_id"]
        kapak = out / r["kapak_dosya"]
        yeni_video = out / r["video_dosya"]
        eski_video = out / "_is" / lid / "canli_video.mp4"
        sure = float(probe(yeni_video)["format"]["duration"])
        noktalar = [0.0, max(sure / 2 - 0.05, 0.0), max(sure - 0.15, 0.0)]
        yeni_kareler = [kare_al(yeni_video, kare_dir / f"{lid}_y{i}.png", sn)
                        for i, sn in enumerate(noktalar, 1)]
        eski_k1 = kare_al(eski_video, kare_dir / f"{lid}_e1.png", 0.0)
        gorseller = [Image.open(kapak).convert("RGB"),
                     Image.open(eski_k1).convert("RGB")]
        gorseller += [Image.open(p).convert("RGB") for p in yeni_kareler]
        etiket = f"{r['cift']}  -  {lid}"
        if lid == a.referans_id:
            etiket += "   [REFERANS]"
        goruntu.append((etiket, gorseller))
        meta.append({**r, "yeni_video_sure": round(sure, 2)})

    yuk = [max(int(HUCRE * g.height / g.width) for g in gs) for _, gs in goruntu]
    genislik = BOSLUK + len(SUTUN) * (HUCRE + BOSLUK)
    yukseklik = BOSLUK + SUTUN_BASLIK + sum(y + SATIR_BASLIK + BOSLUK for y in yuk)
    tuval = Image.new("RGB", (genislik, yukseklik), (247, 247, 247))
    ciz = ImageDraw.Draw(tuval)
    x = BOSLUK
    for s in SUTUN:
        yazi(ciz, (x + 4, BOSLUK + 4), s, 26, (60, 60, 60))
        x += HUCRE + BOSLUK
    y = BOSLUK + SUTUN_BASLIK
    for (etiket, gorseller), sy in zip(goruntu, yuk):
        yazi(ciz, (BOSLUK, y + 8), etiket, 31)
        y += SATIR_BASLIK
        x = BOSLUK
        for g in gorseller:
            h = int(HUCRE * g.height / g.width)
            tuval.paste(g.resize((HUCRE, h), Image.Resampling.LANCZOS), (x, y))
            ciz.rectangle([x, y, x + HUCRE - 1, y + h - 1], outline=(175, 175, 175))
            x += HUCRE + BOSLUK
        y += sy + BOSLUK
    tuval.save(out / "ORNEK_KARSILASTIRMA.jpg", format="JPEG", quality=90, optimize=True)

    ref = next((x for x in meta if x["listing_id"] == a.referans_id), None)
    t = d["tarif"]
    md = [f"# Referans VIDEO hatti - tarif ve olcumler "
          f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi. Uretim yerel; yukleme yok.",
          "**Yeni kapak URETILMEDI** - her ilanin mevcut Gold B kapagi korunur, "
          "yalniz video o kapaga hizalanir.", "",
          "## Referansin canli hali - kaynak kosular", "",
          "| oge | kaynak kosu | zaman (UTC) | kanit |", "|---|---|---|---|",
          "| Kapak 8590281557 | `pod-cover-gold-b` #3, run **35349346706** | 13:17-13:21 | "
          "`TEMP/POD_COVER_GOLD_B/RUN_35349346706/transform_qa.json` |",
          "| Video 843084674 | `pod-video-cover-match` #2, run **35330320821** | 09:35 | "
          "`TEMP/POD_VIDEO_COVER_MATCH/.../qa.json` |", "",
          "`pod-cover-from-video` 7. kosusu (12:00) bir geri almaydi; urettigi kapak "
          "13:17'deki Gold B kosusuyla degistirildi. Canlidaki kapak Gold B ciktisidir, "
          "video karesi degildir.", "",
          "## Video tarifi (uygulanan)", "", "| parametre | deger |", "|---|---|",
          f"| kaydirma | {t['shift_cover_px']} |",
          f"| ilk sabit kare | {t['still_sn']} sn - ilanin KENDI Gold B kapagi, lanczos |",
          f"| gecis | xfade fade {t['fade_sn']} sn, offset "
          f"{t['still_sn'] - t['fade_sn']:.1f} sn |",
          f"| hareket baslangici | {t['motion_start_sn']} sn |",
          "| ust bosluk | kaynak videonun ust 8-32 px seridi vflip ile aynalanir |",
          f"| kare hizi | {t['fps']} fps |",
          f"| codec | {t['codec']}, {t['pix_fmt']}, +faststart, ses yok |",
          "| sure | kaynak videonun suresi |", "",
          "## Olculen kaydirma (ilan basina)", "",
          "| ilan | olculen kaydirma (kapak px) | video uzayinda | arama skoru | video olcu |",
          "|---|---:|---:|---:|---|"]
    for r in meta:
        md.append(f"| {r['cift']}{' (REF)' if r['listing_id'] == a.referans_id else ''} | "
                  f"{r['olculen_kayma_kapak_px']} | {r['video_shift_px']} | "
                  f"{r['arama_skoru']} | {r['video_video_px'][0]}x{r['video_video_px'][1]} |")
    md += ["", "Yontem: ilanin kapagi ile kendi videosunun SON karesi (yerlesmis kompozisyon)",
           "600x750 griye indirgenip kare asagi dogru kaydirilarak ortalama mutlak fark",
           "en kucuk oldugu nokta aranir. 86 px sabiti kullanilmaz.", "",
           "## Ilk kare - kapak farki (referans esigi 1.5404)", "",
           "| ilan | YENI video k0 vs kapak | SU ANKI video k0 vs kapak | referans farkindan sapma |",
           "|---|---:|---:|---:|"]
    for r in meta:
        md.append(f"| {r['cift']} | **{r['yeni_kare_kapak_mae']}** | "
                  f"{r['eski_kare_kapak_mae']} | {r['referans_1_54_fark']:+} |")
    md += ["", "## Kapak altin rengi (yalniz olcum, duzeltme YAPILMADI)", "",
           "| ilan | altin RGB | maske orani | referanstan fark | ort |",
           "|---|---|---:|---|---:|"]
    for r in meta:
        md.append(f"| {r['cift']} | {r['altin_rgb_kapak']} | {r['maske_orani_kapak']} | "
                  f"{r.get('ref_altin_fark', '-')} | {r.get('ref_altin_ort_fark', '-')} |")
    md += ["", "## Kapak duzeni - dikey hiza (simge ve yazi)", "",
           "Her bolgede altin maskesinin en ust / en alt satiri ve agirlik merkezi "
           "(2400x3000 kapak uzayinda, piksel).", "",
           "| ilan | bolge | ust | alt | merkez | referanstan fark (ust/alt/merkez) |",
           "|---|---|---:|---:|---:|---|"]
    for r in meta:
        for ad, deger in (r.get("hiza") or {}).items():
            if not deger:
                md.append(f"| {r['cift']} | {BOLGE_AD.get(ad, ad)} | - | - | - | bolge bos |")
                continue
            rf = (ref or {}).get("hiza", {}).get(ad) if ref else None
            fark = ("-" if not rf else
                    f"{deger['ust'] - rf['ust']:+d} / {deger['alt'] - rf['alt']:+d} / "
                    f"{deger['merkez'] - rf['merkez']:+.1f}")
            md.append(f"| {r['cift']} | {BOLGE_AD.get(ad, ad)} | {deger['ust']} | "
                      f"{deger['alt']} | {deger['merkez']} | {fark} |")
    md += ["", "## 77 ilan icin maliyet", "",
           f"- Ilan basina Etsy cagrisi (salt okur): **{d['cagri_ilan_basina']} GET**.",
           f"- 77 ilan icin salt okur toplam: **{77 * d['cagri_ilan_basina']} GET**.",
           "- Yazma acildiginda ilan basina beklenen: 4 GET + 1 video silme + 1 video "
           "yukleme + 2-3 geri okuma = ~9 cagri -> 77 ilan icin **~690 cagri**.",
           "- Kapak degismedigi icin gorsel yukleme/silme yoktur.", "",
           "## Cikti dosyalari", "",
           "- `ORNEK_KARSILASTIRMA.jpg` - 5 satir x 5 sutun, gercek oranlar.",
           "- `<CIFT>_<id>_video.mp4` - yeni video (yuklenmedi).",
           "- `<CIFT>_<id>_kapak_MEVCUT.png` - ilanin degismeyen Gold B kapagi.",
           "- `URETIM_SONUC.json` - tum olcumler.", ""]
    (out / "TARIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"ORNEK_KARSILASTIRMA.jpg {tuval.size} | {len(meta)} satir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
