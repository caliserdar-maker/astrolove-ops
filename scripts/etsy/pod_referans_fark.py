#!/usr/bin/env python3
"""Referans POD ilani ile 4 ornek ilan arasindaki farki olcer. SALT OKUR.

Etsy'ye yalniz GET yapilir. ADIM 1 metadata, ADIM 2 gorsel karsilastirma
(kapak + 3 video karesi), ADIM 3 kaynak dosya aramasi (hazir listelerden).

Kullanim:
  pod_referans_fark.py --out OUT [--drive-index drive.txt] [--repo-kok .]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    download, gallery, variation_images, variation_map, videos, video_url,
)
from pod_cover_gold_b_transform import artwork_mask  # noqa: E402

REFERANS = ("4570112095", "Aquarius + Gemini (REFERANS)")
ORNEKLER = [("4570126104", "Aquarius + Capricorn"),
            ("4570125580", "Aquarius + Cancer"),
            ("4570031205", "Aries + Leo"),
            ("4570224058", "Scorpio + Taurus")]
KARE_GEN = 520          # karsilastirma gorselinde her karenin genisligi
BOSLUK = 16
BASLIK_YUK = 40


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ts(deger):
    """created_timestamp -> okunur UTC."""
    try:
        return datetime.fromtimestamp(int(deger), timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "?"


def ilan_oku(api, shop, lid):
    listing = api.get(f"/listings/{lid}", ok404=True) or {}
    gorseller = gallery(api, lid)
    vids = videos(api, lid)
    varyasyon = variation_images(api, shop, lid)
    return {
        "listing_id": lid,
        "baslik": listing.get("title") or "",
        "state": listing.get("state"),
        "gorseller": [{
            "rank": g.get("rank"),
            "image_id": str(g.get("listing_image_id")),
            "olcu": f"{g.get('full_width')}x{g.get('full_height')}",
            "yuklenme": ts(g.get("created_timestamp")),
            "epoch": int(g.get("created_timestamp") or 0),
            "url": g.get("url_fullxfull") or g.get("url_570xN") or "",
        } for g in gorseller],
        "videolar": [{
            "video_id": str(v.get("video_id")),
            "yuklenme": ts(v.get("created_timestamp")),
            "epoch": int(v.get("created_timestamp") or 0),
            "url": video_url(v),
        } for v in vids],
        "varyasyon": [[str(y) for y in x] for x in variation_map(varyasyon)],
    }


def kareler(video_yolu, hedef_dir, etiket):
    """Videodan baslangic / orta / son karesi. ffprobe ile sure okunur."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(video_yolu)],
                       capture_output=True, text=True)
    try:
        sure = float((r.stdout or "0").strip())
    except ValueError:
        sure = 0.0
    noktalar = [0.0, max(sure / 2 - 0.05, 0.0), max(sure - 0.15, 0.0)]
    cikti = []
    for i, sn in enumerate(noktalar, 1):
        p = hedef_dir / f"{etiket}_kare{i}.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{sn:.3f}",
                        "-i", str(video_yolu), "-frames:v", "1", str(p)], check=True)
        cikti.append(p)
    return cikti, sure


def altin_rgb(kapak_yolu):
    """Kapaktaki altin (artwork) maskesinin ortalama RGB'si."""
    with Image.open(kapak_yolu) as im:
        rgb = im.convert("RGB")
        if rgb.size != (2400, 3000):
            rgb = rgb.resize((2400, 3000), Image.Resampling.LANCZOS)
        a = np.asarray(rgb, dtype=np.uint8)
    m = artwork_mask(a)
    if not m.any():
        return None, 0.0
    ort = a[m].astype(np.float32).mean(axis=0)
    return [round(float(x), 1) for x in ort], round(float(m.mean()), 6)


def yazi(cizim, xy, metin, boyut=26, renk=(20, 20, 20)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if pathlib.Path(yol).exists():
            cizim.text(xy, metin, fill=renk, font=ImageFont.truetype(yol, boyut))
            return
    cizim.text(xy, metin, fill=renk)


def karsilastirma_gorseli(satirlar, hedef):
    """satirlar: [(etiket, [PIL.Image x4])] -> tek JPG, gercek oranlar korunur."""
    olculer = []
    for _, gorseller in satirlar:
        yuks = [int(KARE_GEN * g.height / g.width) for g in gorseller]
        olculer.append(max(yuks))
    genislik = BOSLUK + 4 * (KARE_GEN + BOSLUK)
    yukseklik = BOSLUK + sum(y + BASLIK_YUK + BOSLUK for y in olculer)
    tuval = Image.new("RGB", (genislik, yukseklik), (245, 245, 245))
    ciz = ImageDraw.Draw(tuval)
    y = BOSLUK
    for (etiket, gorseller), satir_yuk in zip(satirlar, olculer):
        yazi(ciz, (BOSLUK, y + 6), etiket, 28)
        y += BASLIK_YUK
        x = BOSLUK
        for i, g in enumerate(gorseller):
            yeni_yuk = int(KARE_GEN * g.height / g.width)
            kucuk = g.resize((KARE_GEN, yeni_yuk), Image.Resampling.LANCZOS)
            tuval.paste(kucuk, (x, y))
            ciz.rectangle([x, y, x + KARE_GEN - 1, y + yeni_yuk - 1], outline=(180, 180, 180))
            yazi(ciz, (x + 6, y + 6),
                 ["kapak", "video k1", "video k2", "video k3"][i], 20, (255, 255, 255))
            x += KARE_GEN + BOSLUK
        y += satir_yuk + BOSLUK
    tuval.save(hedef, format="JPEG", quality=88, optimize=True)
    return tuval.size


def kaynak_arama(repo_kok, drive_index):
    """ADIM 3: repo ve Drive'da uretim dosyasi/betigi arar (yeni tarama yok)."""
    bulgu = {"repo_betik": [], "repo_config": [], "drive": {}, "drive_ornek": {}}
    kok = pathlib.Path(repo_kok)
    for p in sorted(kok.glob("scripts/**/*.py")):
        ad = p.name.lower()
        if "cover" in ad or "gold_b" in ad:
            bulgu["repo_betik"].append(str(p.relative_to(kok)))
    for p in sorted(kok.glob("config/*")):
        if "cover" in p.name.lower():
            bulgu["repo_config"].append(str(p.relative_to(kok)))
    if drive_index and pathlib.Path(drive_index).exists():
        satirlar = [x.strip() for x in
                    pathlib.Path(drive_index).read_text(encoding="utf-8").split("\n")
                    if x.strip()]
        gruplar = {}
        for y in satirlar:
            kok_klasor = y.split("/")[0] if "/" in y else "(kok)"
            gruplar.setdefault(kok_klasor, []).append(y)
        bulgu["drive"] = {k: len(v) for k, v in sorted(gruplar.items())}
        for k, v in gruplar.items():
            bulgu["drive_ornek"][k] = sorted(v)[:6]
        bulgu["drive_toplam"] = len(satirlar)
    return bulgu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--drive-index", default="")
    ap.add_argument("--repo-kok", default=".")
    ap.add_argument("--wf-gecmis", default="", help="referans workflow kosu gecmisi JSON")
    ap.add_argument("--master-state", default="", help="POD_MASTER_LOCKED_78/state.json")
    ap.add_argument("--gold-state", default="", help="POD_COVER_GOLD_B_77/state.json")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "_medya").mkdir(parents=True, exist_ok=True)

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    log(f"ADIM 1 - canli okuma (yalniz GET). Kota ONCE: {kota_once}")

    hepsi = [REFERANS] + ORNEKLER
    veri = {}
    for lid, ad in hepsi:
        veri[lid] = ilan_oku(api, shop, lid)
        veri[lid]["ad"] = ad
        d = veri[lid]
        log(f"  {ad:34s} {lid}: {len(d['gorseller'])} gorsel, "
            f"{len(d['videolar'])} video, {len(d['varyasyon'])} varyasyon")
    kota_adim1 = api.remaining

    ref = veri[REFERANS[0]]
    ref_kapak = ref["gorseller"][0]
    # referansta yeni olan: en yeni yuklenme damgasi
    farklar = []
    for lid, ad in ORNEKLER:
        d = veri[lid]
        o_kapak = d["gorseller"][0]
        farklar.append({
            "listing_id": lid, "ad": ad,
            "gorsel_sayisi": len(d["gorseller"]),
            "gorsel_sayisi_fark": len(d["gorseller"]) - len(ref["gorseller"]),
            "kapak_olcu": o_kapak["olcu"], "ref_kapak_olcu": ref_kapak["olcu"],
            "kapak_yuklenme": o_kapak["yuklenme"], "ref_kapak_yuklenme": ref_kapak["yuklenme"],
            "kapak_gun_farki": round((ref_kapak["epoch"] - o_kapak["epoch"]) / 86400, 2),
            "video_sayisi": len(d["videolar"]),
            "video_yuklenme": d["videolar"][0]["yuklenme"] if d["videolar"] else "-",
            "ref_video_yuklenme": ref["videolar"][0]["yuklenme"] if ref["videolar"] else "-",
            "varyasyon_sayisi": len(d["varyasyon"]),
            "ref_varyasyon_sayisi": len(ref["varyasyon"]),
            "kapak_1_2_gun_farki": round(
                (d["gorseller"][0]["epoch"] - d["gorseller"][1]["epoch"]) / 86400, 2)
            if len(d["gorseller"]) > 1 else None,
            "ref_kapak_1_2_gun_farki": round(
                (ref["gorseller"][0]["epoch"] - ref["gorseller"][1]["epoch"]) / 86400, 2),
        })

    # ------------------------------------------------------------------ ADIM 2
    log("ADIM 2 - kapak + video kareleri")
    satirlar, olcumler = [], {}
    for lid, ad in hepsi:
        d = veri[lid]
        md = out / "_medya"
        kapak = md / f"{lid}_kapak.png"
        download(d["gorseller"][0]["url"], kapak)
        rgb, oran = altin_rgb(kapak)
        olcumler[lid] = {"ad": ad, "altin_rgb": rgb, "maske_orani": oran,
                         "kapak_id": d["gorseller"][0]["image_id"],
                         "kapak_olcu": d["gorseller"][0]["olcu"]}
        gorseller = [Image.open(kapak).convert("RGB")]
        if d["videolar"] and d["videolar"][0]["url"]:
            vid = md / f"{lid}.mp4"
            download(d["videolar"][0]["url"], vid)
            kare_yollari, sure = kareler(vid, md, lid)
            olcumler[lid]["video_sure_sn"] = round(sure, 2)
            gorseller += [Image.open(p).convert("RGB") for p in kare_yollari]
        else:
            olcumler[lid]["video_sure_sn"] = None
            bos = Image.new("RGB", (800, 1000), (225, 225, 225))
            gorseller += [bos, bos, bos]
        satirlar.append((f"{ad}  -  {lid}", gorseller[:4]))
        log(f"  {ad}: altin RGB {rgb}, maske {oran}, video {olcumler[lid]['video_sure_sn']} sn")

    boyut = karsilastirma_gorseli(satirlar, out / "KARSILASTIRMA.jpg")
    log(f"  KARSILASTIRMA.jpg {boyut[0]}x{boyut[1]}")

    ref_rgb = olcumler[REFERANS[0]]["altin_rgb"]
    for lid, o in olcumler.items():
        if o["altin_rgb"] and ref_rgb:
            o["ref_fark_rgb"] = [round(o["altin_rgb"][i] - ref_rgb[i], 1) for i in range(3)]
            o["ref_fark_mutlak_ort"] = round(
                sum(abs(x) for x in o["ref_fark_rgb"]) / 3, 2)
        else:
            o["ref_fark_rgb"], o["ref_fark_mutlak_ort"] = None, None

    # ------------------------------------------------------------------ ADIM 3
    kaynak = kaynak_arama(a.repo_kok, a.drive_index)

    def durum_ozeti(yol, ad):
        """Toplu is durum dosyasindan kac ilana uygulandigini okur."""
        p = pathlib.Path(yol) if yol else None
        if not p or not p.exists():
            return {"ad": ad, "durum": "dosya yok"}
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as ex:                                   # noqa: BLE001
            return {"ad": ad, "durum": f"okunamadi: {type(ex).__name__}"}
        rows = d.get("rows") or {}
        say = {}
        for r in rows.values():
            ap_blok = r.get("apply") or {}
            anahtar = ap_blok.get("status") or "(apply yok)"
            say[anahtar] = say.get(anahtar, 0) + 1
        return {"ad": ad, "durum": "okundu", "satir": len(rows), "apply_dagilimi": say,
                "apply_complete": d.get("apply_complete"),
                "dry_run_complete": d.get("dry_run_complete"),
                "guncelleme": d.get("updated_utc")}

    durumlar = [durum_ozeti(a.master_state, "POD_MASTER_LOCKED_78"),
                durum_ozeti(a.gold_state, "POD_COVER_GOLD_B_77")]
    wf = {}
    if a.wf_gecmis and pathlib.Path(a.wf_gecmis).exists():
        wf = json.loads(pathlib.Path(a.wf_gecmis).read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ rapor
    md = [f"# POD referans fark raporu ({simdi()} UTC)", "",
          f"Referans: **{REFERANS[1]}** - {REFERANS[0]}  |  ornek 4 ilan.",
          f"Etsy kotasi: once **{kota_once}**, ADIM 1 sonrasi **{kota_adim1}**, "
          f"bitis **{api.remaining}**. Yalniz GET yapildi, yazma YOK.", "",
          "## ADIM 1 - galeri, video ve varyasyon", "",
          "| ilan | gorsel | kapak olcu | kapak yuklenme | kapak-2.gorsel gun farki | "
          "video | video yuklenme | varyasyon |", "|---|---:|---|---|---:|---:|---|---:|"]
    for lid, ad in hepsi:
        d = veri[lid]
        g0 = d["gorseller"][0]
        gf = (round((g0["epoch"] - d["gorseller"][1]["epoch"]) / 86400, 2)
              if len(d["gorseller"]) > 1 else "-")
        md.append(f"| {ad} | {len(d['gorseller'])} | {g0['olcu']} | {g0['yuklenme']} | "
                  f"{gf} | {len(d['videolar'])} | "
                  f"{d['videolar'][0]['yuklenme'] if d['videolar'] else '-'} | "
                  f"{len(d['varyasyon'])} |")
    md += ["", "### Referansta olup orneklerde olmayan", ""]
    ayni_kapak_gun = all(abs(f["kapak_gun_farki"]) < 0.02 for f in farklar)
    md += [f"- Kapak olcusu: referans {ref_kapak['olcu']}; orneklerde "
           + ", ".join(f"{f['ad']} {f['kapak_olcu']}" for f in farklar),
           f"- Gorsel sayisi: referans {len(ref['gorseller'])}; "
           + ", ".join(f"{f['ad']} {f['gorsel_sayisi']}" for f in farklar),
           f"- Kapak yuklenme damgasi ayni gun mu: "
           f"{'EVET, hepsi ayni toplu kosudan' if ayni_kapak_gun else 'HAYIR'}",
           f"- Referans kapagi galerideki 2. gorselden "
           f"{farklar[0]['ref_kapak_1_2_gun_farki']} gun sonra yuklenmis.", ""]
    md += ["## ADIM 2 - kapak altin bolge rengi", "",
           "| ilan | kapak id | altin RGB | maske orani | referanstan fark (R,G,B) | "
           "mutlak ort fark | video sure |", "|---|---|---|---:|---|---:|---:|"]
    for lid, ad in hepsi:
        o = olcumler[lid]
        md.append(f"| {ad} | {o['kapak_id']} | {o['altin_rgb']} | {o['maske_orani']} | "
                  f"{o['ref_fark_rgb']} | {o['ref_fark_mutlak_ort']} | "
                  f"{o['video_sure_sn']} |")
    md += ["", "Olcum yontemi: `pod_cover_gold_b_transform.artwork_mask` ile poster alanindaki",
           "altin pikseller secilir, o piksellerin ortalama RGB'si alinir. Maske orani",
           "kapagin yuzde kaci altin olarak secildigini gosterir.", "",
           "## ADIM 3 - kaynak dosyalar", "",
           "### Repodaki uretim betikleri", ""]
    md += [f"- `{x}`" for x in kaynak["repo_betik"]] or ["- (yok)"]
    md += ["", "### Repodaki tetikleyici/config", ""]
    md += [f"- `{x}`" for x in kaynak["repo_config"]] or ["- (yok)"]
    md += ["", "### Drive uretim klasorleri", ""]
    if kaynak.get("drive"):
        md += [f"Toplam eslesen dosya: **{kaynak['drive_toplam']}**", "",
               "| klasor | dosya |", "|---|---:|"]
        md += [f"| {k} | {v} |" for k, v in kaynak["drive"].items()]
        md += ["", "Ornek yollar:", ""]
        for k, v in kaynak["drive_ornek"].items():
            md += [f"- **{k}**: " + ", ".join(f"`{x}`" for x in v)]
    else:
        md += ["- Drive listesi verilmedi."]
    if wf:
        md += ["", "### Referansa dokunan workflow'lar", "",
               "| workflow | hedef | kosu | son durum | 77'ye neden uygulanmadi |",
               "|---|---|---:|---|---|"]
        for w in wf.get("workflowlar", []):
            son = (w["kosular"] or [{}])[-1]
            md.append(f"| `{w['ad']}` | {w['hedef']} | {w['kosu_sayisi']} | "
                      f"{son.get('utc', '?')} {son.get('sonuc', '?')} | "
                      f"{w['77_ilana_neden_uygulanmadi']} |")
        md += ["", "Kosu dokumu ve referansa etkisi:", ""]
        for w in wf.get("workflowlar", []):
            md += [f"**{w['ad']}** (onay dizesi `{w['onay_dizesi']}`)",
                   f"- Betikler: " + ", ".join(f"`{x}`" for x in w["betikler"]),
                   f"- Referansa etkisi: {w['referansa_etkisi']}",
                   "- Kosular: " + "; ".join(
                       f"#{k['no']} {k['utc']} {k['sonuc']}" for k in w["kosular"]), ""]
    md += ["", "### Toplu is durum dosyalari (77 icin hazir mi)", "",
           "| is | satir | apply dagilimi | apply_complete | guncelleme |",
           "|---|---:|---|---|---|"]
    for d in durumlar:
        if d["durum"] != "okundu":
            md.append(f"| {d['ad']} | - | {d['durum']} | - | - |")
        else:
            md.append(f"| {d['ad']} | {d['satir']} | {d['apply_dagilimi']} | "
                      f"{d['apply_complete']} | {d.get('guncelleme', '-')} |")
    md += ["", "## Cikti", "",
           "- `KARSILASTIRMA.jpg` - 5 satir x 4 kare (kapak, video k1/k2/k3), gercek oranlar.",
           "- `FARK_RAPORU.md` - bu dosya.", "",
           "Etsy'ye hicbir yazma cagrisi yapilmadi."]
    (out / "FARK_RAPORU.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "OLCUMLER.json").write_text(json.dumps(
        {"veri": veri, "olcumler": olcumler, "farklar": farklar, "kaynak": kaynak,
         "durumlar": durumlar, "wf_gecmis": wf,
         "kota_once": kota_once, "kota_sonra": api.remaining},
        ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"BITTI. Kota sonra: {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
