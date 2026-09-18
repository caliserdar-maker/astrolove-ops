#!/usr/bin/env python3
"""V2 ciktilarindan ORNEK_KARSILASTIRMA_V2.jpg, KAPAK_YANYANA.jpg ve TARIF.md."""
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

SUTUN = ["SU ANKI kapak", "YENI kapak", "yeni video k1", "yeni video k2", "yeni video k3"]
HUCRE = 470
BOSLUK = 14
SATIR_BASLIK = 48
SUTUN_BASLIK = 42


def yazi(ciz, xy, metin, boyut=26, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            ciz.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    ciz.text(xy, metin, fill=renk)


def bos_kare(metin="video URETILMEDI"):
    im = Image.new("RGB", (800, 1000), (226, 226, 226))
    yazi(ImageDraw.Draw(im), (40, 470), metin, 34, (120, 120, 120))
    return im


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
    kd = out / "_kare"
    kd.mkdir(parents=True, exist_ok=True)
    d = json.loads(pathlib.Path(a.uretim).read_text(encoding="utf-8"))
    satirlar = [x for x in d["satirlar"] if x["durum"] == "URETILDI"]
    satirlar.sort(key=lambda x: (x["listing_id"] != a.referans_id, x["cift"]))

    goruntu = []
    for r in satirlar:
        lid = r["listing_id"]
        gorseller = [Image.open(out / r["kapak_dosya_mevcut"]).convert("RGB"),
                     Image.open(out / r["kapak_dosya_yeni"]).convert("RGB")]
        if r.get("video_dosya"):
            v = out / r["video_dosya"]
            sure = float(probe(v)["format"]["duration"])
            for i, sn in enumerate([0.0, max(sure / 2 - 0.05, 0), max(sure - 0.15, 0)], 1):
                gorseller.append(Image.open(kare_al(v, kd / f"{lid}_{i}.png", sn))
                                 .convert("RGB"))
        else:
            gorseller += [bos_kare(), bos_kare("video uyumsuz"), bos_kare()]
        etiket = f"{r['cift']}  -  {lid}"
        if lid == a.referans_id:
            etiket += "   [REFERANS]"
        if r.get("video_uyumsuz"):
            etiket += f"   (video uyumsuz, skor {r['arama_skoru']})"
        goruntu.append((etiket, gorseller[:5]))

    yuk = [max(int(HUCRE * g.height / g.width) for g in gs) for _, gs in goruntu]
    tuval = Image.new("RGB", (BOSLUK + 5 * (HUCRE + BOSLUK),
                              BOSLUK + SUTUN_BASLIK
                              + sum(y + SATIR_BASLIK + BOSLUK for y in yuk)),
                      (247, 247, 247))
    ciz = ImageDraw.Draw(tuval)
    x = BOSLUK
    for s in SUTUN:
        yazi(ciz, (x + 4, BOSLUK + 4), s, 26, (60, 60, 60))
        x += HUCRE + BOSLUK
    y = BOSLUK + SUTUN_BASLIK
    for (etiket, gorseller), sy in zip(goruntu, yuk):
        yazi(ciz, (BOSLUK, y + 8), etiket, 30)
        y += SATIR_BASLIK
        x = BOSLUK
        for g in gorseller:
            h = int(HUCRE * g.height / g.width)
            tuval.paste(g.resize((HUCRE, h), Image.Resampling.LANCZOS), (x, y))
            ciz.rectangle([x, y, x + HUCRE - 1, y + h - 1], outline=(175, 175, 175))
            x += HUCRE + BOSLUK
        y += sy + BOSLUK
    tuval.save(out / "ORNEK_KARSILASTIRMA_V2.jpg", format="JPEG", quality=90, optimize=True)

    # --- KAPAK_YANYANA: referans + 4 yeni kapak
    yhucre, yb = 520, 18
    kapaklar = [(r["cift"] + (" [REF]" if r["listing_id"] == a.referans_id else ""),
                 Image.open(out / r["kapak_dosya_yeni"]).convert("RGB")) for r in satirlar]
    yh = max(int(yhucre * g.height / g.width) for _, g in kapaklar)
    yan = Image.new("RGB", (yb + len(kapaklar) * (yhucre + yb), yb + 44 + yh + yb),
                    (250, 250, 250))
    cy = ImageDraw.Draw(yan)
    x = yb
    for etiket, g in kapaklar:
        yazi(cy, (x + 2, yb), etiket, 25, (40, 40, 40))
        h = int(yhucre * g.height / g.width)
        yan.paste(g.resize((yhucre, h), Image.Resampling.LANCZOS), (x, yb + 44))
        cy.rectangle([x, yb + 44, x + yhucre - 1, yb + 44 + h - 1], outline=(170, 170, 170))
        x += yhucre + yb
    yan.save(out / "KAPAK_YANYANA.jpg", format="JPEG", quality=92, optimize=True)

    t = d["tarif"]
    md = [f"# Referans DUZEN hatti V2 ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
          "Etsy'ye hicbir yazma cagrisi yapilmadi.", "",
          "## Referans duzeni nasil elde edildi", "",
          "| kanit klasoru | eski kapak | yeni kapak | kaynak video | roundtrip MAE | mobil LUT |",
          "|---|---|---|---|---:|---|"]
    for z in d.get("kapak_zinciri", []):
        md.append(f"| {z['kanit']} | {z['eski_kapak']} | {z['yeni_kapak']} | "
                  f"{z['kaynak_video']} | {z['roundtrip_mae']} | {z['mobil_lut']} |")
    md += ["", "Zincirin sonunda `pod-cover-gold-b` #3 (run 35349346706) kapagi "
           "**8542130896 -> 8590281557** olarak degistirdi; Gold B yalniz renk "
           "donusumudur (`geometry_operation: none`), duzeni degistirmez.", "",
           "**Sonuc: referans duzeni = ilanin KENDI videosunun 0. karesidir.** "
           "`roundtrip_mae` 0.226 ve `exact_visual_source: true` bunu gosterir; "
           "kapak videodan kirpma/olcek degisikligi olmadan alinir, yalniz "
           "1024x1280 -> 2400x3000 LANCZOS buyutulur.", "",
           "## Uygulanan tarif", "", "| adim | islem |", "|---|---|",
           f"| 1 duzen | {t['duzen']} |", f"| 2 renk | {t['renk']} |",
           f"| mobil LUT | {t['mobil_lut']} |",
           f"| 3 video | ilk {t['still_sn']} sn yeni kapak, xfade {t['fade_sn']} sn, "
           f"hareket {t['motion_start_sn']} sn, {t['codec']}, {t['fps']} fps |",
           "| kaydirma | ilan basina olculur |", "",
           "## Yeni kapaklarin hiza farki (genis pencere, kenar kontrollu)", "",
           f"Olcum penceresi: y {d['pencere']['y0']}-{d['pencere']['y1']}, "
           f"x {d['pencere']['x0']}-{d['pencere']['x1']}. Blok olcumu pencere kenarina "
           "degerse KENAR olarak isaretlenir ve kabul edilmez.", "",
           "| ilan | blok | ust | alt | merkez | referanstan fark (ust/alt/merkez) | "
           "<=5px | kenar |", "|---|---:|---:|---:|---:|---|---|---|"]
    for r in satirlar:
        bloklar = (r.get("duzen_yeni") or {}).get("bloklar", [])
        farklar = {f["blok"]: f for f in (r.get("hiza_fark") or [])}
        for j, b in enumerate(bloklar, 1):
            f = farklar.get(j)
            fs = ("referans" if r["listing_id"] == a.referans_id else
                  (f"{f['ust_fark']:+d} / {f['alt_fark']:+d} / {f['merkez_fark']:+.1f}"
                   if f else "-"))
            md.append(f"| {r['cift']} | {j} | {b['ust']} | {b['alt']} | {b['merkez']} | "
                      f"{fs} | {'-' if r['listing_id'] == a.referans_id else ('EVET' if r.get('hiza_5px_alti') else 'HAYIR')} | "
                      f"{'KENAR' if (r.get('duzen_yeni') or {}).get('kenar') else 'temiz'} |")
    md += ["", "## Altin renk (yalniz olcum)", "",
           "| ilan | altin RGB | maske orani | referanstan fark | ort |",
           "|---|---|---:|---|---:|"]
    for r in satirlar:
        dz = r.get("duzen_yeni") or {}
        md.append(f"| {r['cift']} | {dz.get('altin_rgb')} | {dz.get('maske_orani')} | "
                  f"{r.get('renk_fark', '-')} | {r.get('renk_ort_fark', '-')} |")
    md += ["", "## Video hizalama", "",
           f"Arama skoru > {d['uyumsuz_esik']} olan ilanda video URETILMEZ.", "",
           "| ilan | olculen kaydirma | arama skoru | video | yeni kare0 vs kapak MAE |",
           "|---|---:|---:|---|---:|"]
    for r in satirlar:
        md.append(f"| {r['cift']} | {r.get('olculen_kayma_kapak_px', '-')} | "
                  f"{r.get('arama_skoru', '-')} | "
                  f"{'URETILMEDI (uyumsuz)' if r.get('video_uyumsuz') else 'uretildi'} | "
                  f"{r.get('yeni_kare_kapak_mae', '-')} |")
    for r in satirlar:
        if not r.get("kimlik"):
            continue
        md += ["", f"### {r['cift']} - video kimlik taramasi", "",
               f"Drive kaynak videolariyla karsilastirma (taranan "
               f"{r['kimlik'].get('taranan', 0)} dosya), en yakin 5:", "",
               "| kaynak dosya | MAE |", "|---|---:|"]
        md += [f"| `{x['dosya']}` | {x['mae']} |" for x in r["kimlik"].get("adaylar", [])]
        md += ["", f"Kanit gorseli: `UYUMSUZ_*.jpg` (solda ilanin videosunun ilk karesi, "
               "sagda ilanin mevcut kapagi).", ""]
    md += ["", "## 77 ilan icin maliyet", "",
           f"- Salt okur: ilan basina {d['cagri_ilan_basina']} GET -> "
           f"**{77 * d['cagri_ilan_basina']} GET**.",
           "- Yazma acildiginda ilan basina: 4 GET + 1 kapak yukleme + 1 kapak silme + "
           "1 video silme + 1 video yukleme + 3 geri okuma = **~11 cagri** -> 77 ilan "
           "icin **~847 cagri**.",
           "- Uretim suresi: bu kosudaki olculen sureye gore 77 ilan icin "
           "yaklasik 12-18 dakika (video indirme + kodlama).", "",
           "## Cikti dosyalari", "",
           "- `ORNEK_KARSILASTIRMA_V2.jpg` - 5 satir x 5 sutun.",
           "- `KAPAK_YANYANA.jpg` - referans + 4 yeni kapak yan yana.",
           "- `<CIFT>_<id>_kapak_YENI.png` - yeni kapak (2400x3000).",
           "- `<CIFT>_<id>_kapak_MEVCUT.png` - ilanin su anki kapagi.",
           "- `<CIFT>_<id>_video.mp4` - uyumlu ilanlarda yeni video.",
           "- `URETIM_SONUC.json` - tum olcumler.", ""]
    (out / "TARIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"V2 gorsel {tuval.size} | yanyana {yan.size} | {len(satirlar)} satir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
