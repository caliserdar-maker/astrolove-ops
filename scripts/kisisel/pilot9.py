#!/usr/bin/env python3
"""
Isim yerlesimi: uc secenek, gercek posterde ornek (Serdar gozle secer).

DEGISEN OGELER: YOK. ONAYLI.json'a dokunulmaz; bu kosu yalniz ornek uretir.
Zemin, logo, sonsuzluk, tagline (SECENEK 1) ve isim dokusu degismez.

  A  mevcut kural   : isim kendi sembolunun altinda ortali; sigmayan isim
                      YALNIZ KENDISI orantili kuculur.
  B  dengeli kucul. : ortali; cift AYNI olcekte kalir, uzun isim sigmiyorsa
                      ikisi birlikte kuculur.
  C  disa genisleme : sigan isim ortali (onayli gorunum); sigmayan isim ic
                      kenarini sonsuzluk boslugunda (136 px) sabit tutar ve
                      poster kenarindan 240 px kalana dek disa uzar; orada da
                      sigmazsa cift birlikte, ayni oranda kuculur.

"Ayni punto" B/C'de ayni OLCEK olarak uygulanir: onayli gorunumde iki isim
zaten farkli puntodadir (Canva kutulari 85.32 / 83.34 px -> SERDAR 117,
LENA 112). Birebir ayni punto zorlanirsa kontrol posteri onaylidan sapar.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kisisel_pilot import (DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           TAGLINES, ciz_metin, cap_icin_boyut, fetch,
                           font_yukle, rc)
from pilot6 import (altin as altin_isim, hedef, met_al, satir_kumeleri,
                    isim_kontrol, kaydet, B, LUMA, MUREKKEP, TUVAL, REFERANS,
                    ISIM_FONT, ISIM_W, TAG_FONT, TAG_W, TAG_PUNTO, ciz_cap)
from pilot7 import kuyruk_duzlestir, altin_sekil, sade
import pilot6

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
YOL = OUT / "YERLESIM"
DEST_Y = DEST + "/YERLESIM"
KENAR_PAYI = 240                       # Mo: poster kenarindan en az 240 px (%10)
TABAN_OLCEK = 0.75                     # Mo: %75 puntoya kadar kuculmeye izin
CIFTLER = [(NEW_LEFT, NEW_RIGHT), ("MEHMET", "ALEXANDRA"),
           ("CHRISTOPHER", "ELIZABETH")]
SECENEKLER = ["A", "B", "C"]
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


# ------------------------------------------------------------------ plaka


def tam_punto(metin, met, kutu):
    """Onayli kural: punto aksansiz govdenin cam yuksekliginden."""
    _, _, cam_h = hedef(kutu, met)
    return cap_icin_boyut(FONT_DIR / ISIM_FONT, sade(metin), cam_h, ISIM_W)


def plaka(metin, met, kutu, tr, olcek=1.0, tam=None):
    tam = tam or tam_punto(metin, met, kutu)
    size = max(int(round(tam * olcek)), 4)
    cr, _ = ciz_metin(font_yukle(FONT_DIR / ISIM_FONT, size, ISIM_W), metin, size * tr)
    return altin_isim(cr, met), size


def gereken_olcek(metin, met, kutu, tr, maks_w, taban=0.0):
    """Metni maks_w'ye sigdiran olcek (taban'in altina inmez)."""
    tam = tam_punto(metin, met, kutu)
    olcek = 1.0
    pl, _ = plaka(metin, met, kutu, tr, 1.0, tam)
    for _ in range(7):
        if pl.width <= maks_w or olcek <= taban:
            break
        olcek = max(olcek * min(maks_w / pl.width, 0.99), taban)
        pl, _ = plaka(metin, met, kutu, tr, olcek, tam)
    return olcek, pl.width


# ------------------------------------------------------------------ yerlesim


def yerlesim(secenek, isimler, yuva, tr):
    """Her isim icin (plaka, punto, olcek, sol_x, ortali_mi) dondurur."""
    sonuc = {}
    tamlar = {y: plaka(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr)[0].width
              for y in ("sol", "sag")}
    if secenek == "A":
        olcekler = {y: gereken_olcek(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr,
                                     yuva[y]["ortali_w"])[0] for y in ("sol", "sag")}
    elif secenek == "B":
        ort = min(gereken_olcek(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr,
                                yuva[y]["ortali_w"])[0] for y in ("sol", "sag"))
        olcekler = {"sol": ort, "sag": ort}
    else:                                            # C
        ort = min(gereken_olcek(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr,
                                yuva[y]["dis_w"])[0] for y in ("sol", "sag"))
        olcekler = {"sol": ort, "sag": ort}
    for y in ("sol", "sag"):
        pl, punto = plaka(isimler[y], yuva[y]["met"], yuva[y]["kutu"], tr, olcekler[y])
        ortali = pl.width <= yuva[y]["ortali_w"] + 0.5
        if secenek in ("A", "B") or ortali:
            x = yuva[y]["merkez"] - pl.width / 2      # sembolun altinda ortali
        elif y == "sol":
            x = yuva[y]["ic_kenar"] - pl.width        # C: ic kenar sabit, disa uzar
        else:
            x = yuva[y]["ic_kenar"]
        sonuc[y] = {"plaka": pl, "punto": punto, "olcek": round(olcekler[y], 3),
                    "genislik": pl.width, "tam_genislik": tamlar[y], "x": x,
                    "ortali": bool(ortali), "isim": isimler[y],
                    "kuculdu": olcekler[y] < 0.999,
                    "dis_kenar": x if y == "sol" else TUVAL[0] - (x + pl.width),
                    "sembol_kaymasi": abs((x + pl.width / 2) - yuva[y]["merkez"])}
    return sonuc


def poster(temiz, yer, yuva, tag_pl, tag_xy):
    t = temiz.convert("RGBA").copy()
    for y in ("sol", "sag"):
        _, my, _ = hedef(yuva[y]["kutu"], yuva[y]["met"])
        pl = yer[y]["plaka"]
        t.alpha_composite(pl, (int(round(yer[y]["x"])), int(round(my - pl.height / 2))))
    t.alpha_composite(tag_pl, tag_xy)
    return t


# ------------------------------------------------------------------ olcum


def harf_siniri(met, kutu, tr, maks_w, taban, harf="M"):
    """maks_w'ye (taban olcegine kadar kuculerek) sigan azami harf sayisi."""
    n = 0
    for k in range(1, 20):
        o, w = gereken_olcek(harf * k, met, kutu, tr, maks_w, taban)
        if w <= maks_w:
            n = k
        else:
            break
    return n


def olcum(yuva, tr, px_harf):
    """Her secenek icin tam boyda ve %75'e kadar kuculmede azami harf sayisi."""
    cikti = {}
    for sec in SECENEKLER:
        alan = "dis_w" if sec == "C" else "ortali_w"
        s = {}
        for y in ("sol", "sag"):
            w = yuva[y][alan]
            s[y] = {
                "sinir_px": round(w, 1),
                "tam_M": harf_siniri(yuva[y]["met"], yuva[y]["kutu"], tr, w, 1.0),
                "tam_normal": int(w / px_harf[y]),
                "k75_M": harf_siniri(yuva[y]["met"], yuva[y]["kutu"], tr,
                                     w / TABAN_OLCEK, 1.0),
                "k75_normal": int(w / TABAN_OLCEK / px_harf[y]),
            }
        cikti[sec] = s
    return cikti


# ------------------------------------------------------------------ akis


def kos(indir=True):
    YOL.mkdir(parents=True, exist_ok=True)
    if indir:
        rc("copy", f"{DEST}/{REFERANS}", str(OUT))
        HAZIR.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST}/HAZIR/bg.png", str(HAZIR))
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, REF / "names")
        log("referans + bg.png + isim plakalari indi")

    ref = Image.open(OUT / REFERANS).convert("RGB")
    if ref.size != TUVAL:
        ref = ref.resize(TUVAL, Image.LANCZOS)
    bg = Image.open(HAZIR / "bg.png")
    temiz, geo = pilot6.zemin_hazirla(ref, bg)
    sonsuz = geo["sonsuzluk"]
    isim_km = satir_kumeleri(np.asarray(ref).astype(np.float32) @ LUMA, *geo["isim_y"])
    min_bosluk = min(sonsuz[0] - isim_km[0][1], isim_km[-1][0] - sonsuz[1])

    met_c = met_al(REF / "names" / "cancer_name_gold.png")
    met_l = met_al(REF / "names" / "libra_name_gold.png")
    tr = pilot6.isim_tr_hesapla(met_c, met_l,
                                {"cancer": REF / "names" / "cancer_name_gold.png",
                                 "libra": REF / "names" / "libra_name_gold.png"})

    yuva = {}
    for y, met, kutu in (("sol", met_c, B["name_left"]), ("sag", met_l, B["name_right"])):
        mx, _, _ = hedef(kutu, met)
        ic = (sonsuz[0] - min_bosluk) if y == "sol" else (sonsuz[1] + min_bosluk)
        ortali_w = 2 * (mx - ic if y == "sag" else ic - mx)
        dis_w = (ic - KENAR_PAYI) if y == "sol" else (TUVAL[0] - KENAR_PAYI - ic)
        yuva[y] = {"met": met, "kutu": kutu, "merkez": mx, "ic_kenar": ic,
                   "ortali_w": ortali_w, "dis_w": dis_w}
        log(f"yuva {y}: merkez {mx:.1f}, ic kenar {ic}, ortali {ortali_w:.1f} px, "
            f"disa genis {dis_w:.1f} px")

    # tagline A - onayli SECENEK 1 dokusu, hicbir seceneke gore degismez
    prof1, _ = kuyruk_duzlestir(np.asarray(met_c["prof"], np.float32))
    cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, TAGLINES["A"])
    tag_pl = altin_sekil(cr, prof1, (cu, ct))
    tag_xy = (int(round(TUVAL[0] / 2 - tag_pl.width / 2)),
              int(round((geo["tag_y"][0] + geo["tag_y"][1]) / 2 - tag_pl.height / 2)))

    d = {"degisen": [], "degismeyen": [
        "ONAYLI.json (dokunulmadi)", "zemin, logo, sonsuzluk, kucuk semboller",
        "isim dokusu, font, punto kurali, harf araligi",
        "tagline SECENEK 1 (metin A, ayni yerde)"],
        "min_bosluk": min_bosluk, "kenar_payi": KENAR_PAYI,
        "yuva": {y: {k: round(v[k], 1) for k in ("merkez", "ic_kenar", "ortali_w", "dis_w")}
                 for y, v in yuva.items()},
        "posterler": [], "kapi": {}}

    kucukler = {}
    for sec in SECENEKLER:
        for i, cift in enumerate(CIFTLER, 1):
            yer = yerlesim(sec, {"sol": cift[0], "sag": cift[1]}, yuva, tr)
            p = poster(temiz, yer, yuva, tag_pl, tag_xy)
            ad = f"{sec}_{i}.jpg"
            kaydet(p, YOL / ad)
            kucukler[(sec, i)] = p.convert("RGB").resize((800, 1000), Image.LANCZOS)
            kayit = {"dosya": ad, "secenek": sec, "cift": list(cift)}
            for y in ("sol", "sag"):
                kayit[y] = {k: yer[y][k] for k in
                            ("isim", "punto", "olcek", "genislik", "tam_genislik",
                             "ortali", "kuculdu", "dis_kenar", "sembol_kaymasi")}
                for k in ("dis_kenar", "sembol_kaymasi"):
                    kayit[y][k] = round(kayit[y][k], 1)
            d["posterler"].append(kayit)
            log(f"{ad}: {cift[0]}({yer['sol']['punto']}, %{yer['sol']['olcek'] * 100:.0f}"
                f"{', ortali' if yer['sol']['ortali'] else ', disa'}) / "
                f"{cift[1]}({yer['sag']['punto']}, %{yer['sag']['olcek'] * 100:.0f}"
                f"{', ortali' if yer['sag']['ortali'] else ', disa'})")
            if i == 1:
                d["kapi"][sec] = isim_kontrol(p)
                log(f"  kontrol kapisi {sec}: {json.dumps(d['kapi'][sec])}")

    # px/harf: gercek adlardan (pilot8 ile ayni yontem)
    ornek_adlar = ["JONATHAN", "ELIZABETH", "ALEXANDRA", "KATHERINE", "NATHANIEL",
                   "CHRISTINA", "MAXIMILIAN", "WILHELMINA", "CHRISTOPHER", "MUHAMMED",
                   "ABDURRAHMAN", "MEHMET", "WILLIAM", "SERDAR", "LENA", "MARK", "ECE"]
    px_harf = {}
    for y in ("sol", "sag"):
        w = [plaka(a, yuva[y]["met"], yuva[y]["kutu"], tr)[0].width / len(a)
             for a in ornek_adlar]
        px_harf[y] = float(np.mean(w))
    d["px_harf"] = {k: round(v, 1) for k, v in px_harf.items()}
    d["olcum"] = olcum(yuva, tr, px_harf)
    for sec in SECENEKLER:
        s = d["olcum"][sec]
        log(f"olcum {sec}: sag sinir {s['sag']['sinir_px']} px -> tam boy "
            f"M{s['sag']['tam_M']}/normal {s['sag']['tam_normal']}, %75'e kadar "
            f"M{s['sag']['k75_M']}/normal {s['sag']['k75_normal']}")

    kiyas(kucukler)
    rapor(d)
    if indir:
        rc("copy", str(YOL), DEST_Y)
        log(f"Drive <- {DEST_Y}")
    return d


def kiyas(kucukler):
    et = font_yukle(FONT_DIR / ISIM_FONT, 34, ISIM_W)
    bas = 46
    im = Image.new("RGB", (3 * 800, 3 * (1000 + bas)), (8, 10, 24))
    dd = ImageDraw.Draw(im)
    for r, sec in enumerate(SECENEKLER):
        for c, cift in enumerate(CIFTLER, 1):
            y0 = r * (1000 + bas)
            dd.text((c * 800 - 800 + 14, y0 + 6),
                    f"{sec}  {CIFTLER[c - 1][0]} - {CIFTLER[c - 1][1]}",
                    fill=(214, 178, 96), font=et)
            im.paste(kucukler[(sec, c)], ((c - 1) * 800, y0 + bas))
    kaydet(im, YOL / "YERLESIM_KIYAS.jpg", maks=2_500_000)
    log(f"YERLESIM_KIYAS.jpg {im.size}")


def rapor(d):
    o = d["olcum"]
    m = ["# Isim yerlesimi - uc secenek", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "", "**YOK** - bu kosu yalniz ornek uretir; "
         "ONAYLI.json'a dokunulmadi.", "", "### Degismeyen", ""]
    m += [f"- {x}" for x in d["degismeyen"]]
    m += ["", "## Secenekler", "",
          "| | kural | sag yuvada kullanilabilir genislik |",
          "| --- | --- | --- |",
          f"| A | mevcut: ortali, yalniz sigmayan isim kuculur "
          f"| {o['A']['sag']['sinir_px']} px |",
          f"| B | ortali, cift ayni olcekte kuculur | {o['B']['sag']['sinir_px']} px |",
          f"| C | sigan ortali; sigmayan ic kenari sabit tutup disa uzar "
          f"(kenar payi {d['kenar_payi']} px), sonra cift birlikte kuculur "
          f"| {o['C']['sag']['sinir_px']} px |", "",
          f"Sonsuzluk boslugu her seceneke ayni: {d['min_bosluk']} px. "
          f"Sol yuva: A/B {o['A']['sol']['sinir_px']} px, C {o['C']['sol']['sinir_px']} px.",
          "", "> Not: B ve C'de \"ayni punto\" ayni OLCEK olarak uygulandi. Onayli "
          "gorunumde iki isim zaten farkli puntoda (Canva kutulari 85.32 / 83.34 px "
          "-> SERDAR 117, LENA 112); birebir ayni punto zorlanirsa kontrol posteri "
          "onaylidan sapardi.", "",
          "## Azami harf sayisi (belirleyici sag yuva)", "",
          "| secenek | tam boyda, en genis harf (M) | tam boyda, normal isim "
          "| %75'e kadar kuculmeyle, M | %75'e kadar, normal isim |",
          "| --- | --- | --- | --- | --- |"]
    for sec in SECENEKLER:
        s = o[sec]["sag"]
        m.append(f"| {sec} | {s['tam_M']} | {s['tam_normal']} | {s['k75_M']} "
                 f"| {s['k75_normal']} |")
    m += ["", "Sol yuvada (daha genis) ayni sira:", "",
          "| secenek | tam M | tam normal | %75 M | %75 normal |",
          "| --- | --- | --- | --- | --- |"]
    for sec in SECENEKLER:
        s = o[sec]["sol"]
        m.append(f"| {sec} | {s['tam_M']} | {s['tam_normal']} | {s['k75_M']} "
                 f"| {s['k75_normal']} |")
    m += ["", f"Normal isimde olculen ortalama harf genisligi: sol {d['px_harf']['sol']} px, "
          f"sag {d['px_harf']['sag']} px (tam boyda).", "",
          "## Uretilen posterler", "",
          "| dosya | secenek | sol isim | punto | olcek | yerlesim | sag isim | punto "
          "| olcek | yerlesim | sembol kaymasi (sol/sag) px |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in d["posterler"]:
        m.append(f"| {p['dosya']} | {p['secenek']} | {p['sol']['isim']} "
                 f"| {p['sol']['punto']} | %{p['sol']['olcek'] * 100:.0f} "
                 f"| {'ortali' if p['sol']['ortali'] else 'disa uzadi'} "
                 f"| {p['sag']['isim']} | {p['sag']['punto']} "
                 f"| %{p['sag']['olcek'] * 100:.0f} "
                 f"| {'ortali' if p['sag']['ortali'] else 'disa uzadi'} "
                 f"| {p['sol']['sembol_kaymasi']:.0f} / {p['sag']['sembol_kaymasi']:.0f} |")
    m += ["", "## Kontrol: SERDAR - LENA onayliyla birebir mi", "",
          "| secenek | isim kapisi | harf kaymasi px | murekkep fark |",
          "| --- | --- | --- | --- |"]
    for sec in SECENEKLER:
        k = d["kapi"][sec]
        m.append(f"| {sec} | {'GECTI' if k['gecti'] else 'KALDI'} | {k.get('kayma_px')} "
                 f"| {k.get('murekkep_fark')} |")
    m += ["", "Kapi esigi: harf konumu <= 1 px, murekkep ortalama farki <= 3 "
          "(ONAYLI.json).", "",
          "## Karsilastirma", "", "- YERLESIM_KIYAS.jpg: satir = secenek (A/B/C), "
          "sutun = isim cifti (SERDAR-LENA, MEHMET-ALEXANDRA, CHRISTOPHER-ELIZABETH).",
          "- Tum posterlerde zemin, sonsuzluk ve tagline ayni; yalniz isim yerlesimi "
          "degisiyor.",
          "- C'de bedel olculdu: isim disa uzayinca ustteki kucuk sembolun altindan "
          "kayiyor (tabloda son sutun). A ve B'de kayma her zaman 0'dir, cunku isim "
          "her kosulda ortali kalir.", ""]
    (YOL / "YERLESIM_RAPOR.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    (YOL / "yerlesim.json").write_text(json.dumps(d, ensure_ascii=False, indent=1,
                                                  default=str), encoding="utf-8")
    log("YERLESIM_RAPOR.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    a = ap.parse_args()
    kos(indir=not a.yerel)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
