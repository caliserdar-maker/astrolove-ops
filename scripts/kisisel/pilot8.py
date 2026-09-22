#!/usr/bin/env python3
"""
LEGACY - Kisisellestirme v9 (Serdar karari, 21 Eyl 2026).

Bu betik oran-bazli uretim akisindan onceki olcum aracidir. Yalniz eski
`onayli/TAGLINE_ALTIN.png` kilidini kullanir; guncel uretim ve regresyon
kapilari `pilot16.py` / `edisyon_uret.py` icindeki `TAGLINE_<oran>.png`
kilitleridir. Uretim icin bu betigi kullanmayin.

DEGISEN OGELER
  - Tagline dokusu icin SECENEK 1 kilitlendi (cancer plakasi profili, alt ucu
    yerinde duzlestirilmis, kabartma glif seklinden). Secenek 2 kodu kaldirildi.
  - Tagline icin de isim satirindaki gibi bir kapi eklendi:
    onayli/TAGLINE_ALTIN.png ile karsilastirma.
  - onayli/ALTIN_POSTER.jpg (onaylanan SECENEK1_A) referans olarak eklendi.

GOREV: Etsy giris sinirlarini OLC (poster uretmek degil).
  - Isim: her aday ismi sol ve sag yuvada TAM BOYDA cizip genisligini ve
    yuvanin sinirini olcer; kuculme gerekip gerekmedigini raporlar.
  - Tagline: 10 gercekci cumleyi tam boyda cizip genislik/sinir olcer.
  - Sinir asiminda mevcut kural: YALNIZ o oge orantili kuculur.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, rc)
from pilot6 import (altin as altin_isim, hedef, kumeler, met_al, satir_kumeleri,
                    ciz_cap, isim_kontrol, ONAYLI_DIR, B, LUMA, MUREKKEP,
                    TUVAL, REFERANS, ISIM_FONT, ISIM_W, TAG_FONT, TAG_W,
                    TAG_PUNTO, kaydet)
from pilot7 import kuyruk_duzlestir, altin_sekil, sade, isim_plaka, satir_sicrama
import pilot6
import pilot7

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
TAG_MAKS_W = 1670                      # Mo: tagline genislik siniri
T0 = time.time()

ISIMLER = ["JONATHAN", "ELIZABETH", "ALEXANDRA", "KATHERINE", "NATHANIEL",
           "CHRISTINA", "MAXIMILIAN", "WILHELMINA", "CHRISTOPHER", "MUHAMMED",
           "ABDURRAHMAN", "GÜLİZAR", "MEHMET", "WILLIAM", "MMMMMMMM",
           NEW_LEFT, NEW_RIGHT,
           # kisa adaylar: dar sag yuvanin gercek siniri bunlarla olculur
           "ZEYNEP", "SEDA", "EMMA", "ANNA", "JOHN", "MARK", "LUCA", "NOAH",
           "IRIS", "ELIF", "ECE", "ELA", "ADA", "MIA"]
TAGLINELER = [
    "It Began With a Kiss in the Rain",              # 31
    "Two Hearts, One Endless Story",                 # 29
    "We Found Forever in a Moment",                  # 28
    "Where Our Worlds Met and Stayed",               # 31
    "My Whole World Was Waiting There",              # 32
    "Written in the Stars Long Before Us",           # 35
    "Wherever We Wander We Are Home Now",            # 34
    "Yağmurun Altındaki İlk Öpücük",   # 29 (TR)
    "Mmmm Wwww Mmmm Wwww Mmmm Wwww",                 # 29 (en genis)
    "Two Souls · One Bond",                     # 20 (orijinal)
]


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def gonder(ad):
    p = OUT / ad
    if not p.exists():
        return log(f"gonderilemedi (yok): {ad}")
    try:
        rc("copy", str(p), DEST)
        log(f"Drive <- {ad} ({p.stat().st_size / 1e3:.0f} KB)")
    except Exception as e:
        log(f"Drive yazilamadi {ad}: {str(e)[:130]}")


def tagline_kontrol(poster, kirpim):
    """Onayli tagline kirpimiyla karsilastir (isim kapisiyla ayni yontem)."""
    onay = Image.open(ONAYLI_DIR / "TAGLINE_ALTIN.png").convert("RGB")
    x0, y0 = kirpim[:2]
    yeni = poster.convert("RGB").crop((x0, y0, x0 + onay.width, y0 + onay.height))
    ao, an = np.asarray(onay).astype(np.float32), np.asarray(yeni).astype(np.float32)
    mo, mn = (ao @ LUMA) > MUREKKEP, (an @ LUMA) > MUREKKEP
    ko, kn = kumeler(mo, 12), kumeler(mn, 12)
    ortak = mo & mn
    ic = np.asarray(Image.fromarray((ortak * 255).astype(np.uint8), "L").filter(
        ImageFilter.MinFilter(3))) > 127
    fark = float(np.abs(ao[ic] - an[ic]).mean()) if ic.sum() else 999.0
    kayma = max(abs(ko[0][0] - kn[0][0]), abs(ko[-1][1] - kn[-1][1])) if ko and kn else 999
    return {"gecti": bool(kayma <= 1 and fark <= 3.0), "kayma_px": kayma,
            "murekkep_fark": round(fark, 2), "ic_px": int(ic.sum()),
            "kume": [len(ko), len(kn)]}


def kos(indir=True):
    OUT.mkdir(parents=True, exist_ok=True)
    d = {"degisen": ["tagline dokusu SECENEK 1 olarak kilitlendi; secenek 2 kodu kaldirildi",
                     "tagline icin onayli/TAGLINE_ALTIN.png kapisi eklendi",
                     "onayli/ALTIN_POSTER.jpg eklendi"],
         "degismeyen": ["zemin, logo, isimler ve tagline parametreleri (ONAYLI.json)"]}
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
    pilot6.OUT, pilot6.REF, pilot6.HAZIR = OUT, REF, HAZIR
    temiz, geo = pilot6.zemin_hazirla(ref, bg)
    sonsuz = geo["sonsuzluk"]
    tag_kutu = [geo["tag_x"][0], geo["tag_y"][0], geo["tag_x"][1], geo["tag_y"][1]]
    isim_km = satir_kumeleri(np.asarray(ref).astype(np.float32) @ LUMA, *geo["isim_y"])
    min_bosluk = min(sonsuz[0] - isim_km[0][1], isim_km[-1][0] - sonsuz[1])

    met_c, met_l = (met_al(REF / "names" / "cancer_name_gold.png"),
                    met_al(REF / "names" / "libra_name_gold.png"))
    isim_tr = pilot6.isim_tr_hesapla(met_c, met_l,
                                     {"cancer": REF / "names" / "cancer_name_gold.png",
                                      "libra": REF / "names" / "libra_name_gold.png"})
    prof1, kes = kuyruk_duzlestir(np.asarray(met_c["prof"], np.float32))
    d["profil"] = {"kaynak": "cancer_name_gold.png (SECENEK 1)", "duzlestirme": kes}

    # --- yuva sinirlari
    yuvalar = {}
    for yan, met, kutu in (("sol", met_c, B["name_left"]), ("sag", met_l, B["name_right"])):
        mx, _, cam_h = hedef(kutu, met)
        maks_yari = (sonsuz[0] - min_bosluk - mx) if yan == "sol" else (mx - (sonsuz[1] + min_bosluk))
        yuvalar[yan] = {"merkez": round(mx, 1), "maks_yari": round(maks_yari, 1),
                        "maks_genislik": round(maks_yari * 2, 1), "met": met, "kutu": kutu}
        log(f"yuva {yan}: merkez {mx:.1f}, azami genislik {maks_yari * 2:.1f} px")
    d["yuvalar"] = {k: {x: v[x] for x in ("merkez", "maks_yari", "maks_genislik")}
                    for k, v in yuvalar.items()}
    d["min_bosluk"] = min_bosluk

    # --- isim olcumu
    d["isim_olcum"] = []
    for ad in ISIMLER:
        satir = {"isim": ad, "harf": len(ad)}
        for yan, y in yuvalar.items():
            pl, b = isim_plaka(ad, y["met"], y["kutu"], isim_tr, 10 ** 6)   # sinirsiz = tam boy
            satir[yan] = {"punto": b["punto"], "genislik": b["genislik"],
                          "sinir": y["maks_genislik"],
                          "sigdi": b["genislik"] <= y["maks_genislik"],
                          "gereken_olcek": round(min(y["maks_genislik"] / b["genislik"], 1.0), 3)}
        d["isim_olcum"].append(satir)
        log(f"ISIM {ad:13s} harf={len(ad):2d} sol={satir['sol']['genislik']:4d}/"
            f"{satir['sol']['sinir']:.0f} {'OK' if satir['sol']['sigdi'] else 'TASTI'}  "
            f"sag={satir['sag']['genislik']:4d}/{satir['sag']['sinir']:.0f} "
            f"{'OK' if satir['sag']['sigdi'] else 'TASTI'}")

    # --- tasarim kenar boslugu (referansin kendi ink sinirlari)
    Lref = np.asarray(ref).astype(np.float32) @ LUMA
    sutun = (Lref > MUREKKEP).sum(axis=0)
    ink = np.nonzero(sutun > 2)[0]
    d["kenar"] = {"en_sol": int(ink[0]), "en_sag": int(ink[-1]),
                  "isim_dis_kenar": [isim_km[0][0], isim_km[-1][1]],
                  "simetri": int(TUVAL[0] - isim_km[0][0]) == isim_km[-1][1]}
    log(f"tasarim ink {ink[0]}-{ink[-1]}, isim dis kenarlari "
        f"{isim_km[0][0]}/{isim_km[-1][1]} (ayna: {d['kenar']['simetri']})")

    # --- M ile azami harf sayisi (en genis harf)
    d["m_testi"] = {}
    for yan, y in yuvalar.items():
        n = 0
        for k in range(1, 16):
            pl, b = isim_plaka("M" * k, y["met"], y["kutu"], isim_tr, 10 ** 6)
            if b["genislik"] <= y["maks_genislik"]:
                n = k
            else:
                break
        d["m_testi"][yan] = n
    log(f"M testi (en genis harf): sol {d['m_testi']['sol']}, sag {d['m_testi']['sag']} harf")

    # normal harf genisligi: gercek adaylardan px/harf (MMMM... haric)
    gercek = [s_ for s_ in d["isim_olcum"] if set(s_["isim"]) != {"M"}]
    px_harf = {y: float(np.mean([s_[y]["genislik"] / s_["harf"] for s_ in gercek]))
               for y in ("sol", "sag")}
    d["px_harf"] = {k: round(v, 1) for k, v in px_harf.items()}
    d["normal_azami"] = {y: int(yuvalar[y]["maks_genislik"] / px_harf[y]) for y in px_harf}
    log(f"normal harf genisligi sol {px_harf['sol']:.1f} / sag {px_harf['sag']:.1f} px -> "
        f"azami sol {d['normal_azami']['sol']} / sag {d['normal_azami']['sag']} harf")

    # --- tagline olcumu
    d["tag_olcum"] = []
    for t in TAGLINELER:
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, t)
        d["tag_olcum"].append({"metin": t, "karakter": len(t), "genislik": cr.width,
                               "sinir": TAG_MAKS_W, "sigdi": cr.width <= TAG_MAKS_W,
                               "gereken_olcek": round(min(TAG_MAKS_W / cr.width, 1.0), 3)})
        log(f"TAGLINE {len(t):2d} kr {cr.width:5d}/{TAG_MAKS_W} "
            f"{'OK' if cr.width <= TAG_MAKS_W else 'TASTI'}  {t[:40]}")
    # karakter basina ortalama genislik -> guvenli azami karakter
    oran = [o["genislik"] / o["karakter"] for o in d["tag_olcum"]]
    d["tag_kr_genislik"] = {"ort": round(float(np.mean(oran)), 2),
                            "maks": round(float(np.max(oran)), 2)}
    d["tag_azami"] = {"ortalama_metinde": int(TAG_MAKS_W / np.mean(oran)),
                      "en_genis_metinde": int(TAG_MAKS_W / np.max(oran))}
    log(f"tagline karakter genisligi ort {d['tag_kr_genislik']['ort']} / "
        f"maks {d['tag_kr_genislik']['maks']} -> azami "
        f"{d['tag_azami']['ortalama_metinde']} / {d['tag_azami']['en_genis_metinde']} karakter")

    # --- SINIR_ORNEK: sinirda sigan en uzun isim + en uzun tagline
    en_isim = {}
    for yan in ("sol", "sag"):
        uyan = [s for s in d["isim_olcum"] if s[yan]["sigdi"]]
        en_isim[yan] = max(uyan, key=lambda s: s[yan]["genislik"])["isim"] if uyan else NEW_LEFT
    uyan_t = [o for o in d["tag_olcum"] if o["sigdi"]]
    en_tag = max(uyan_t, key=lambda o: o["genislik"])["metin"] if uyan_t else ORIG_TAGLINE
    d["ornek"] = {"sol": en_isim["sol"], "sag": en_isim["sag"], "tagline": en_tag}
    log(f"SINIR ORNEGI: {en_isim['sol']} / {en_isim['sag']} | {en_tag}")

    t = temiz.convert("RGBA").copy()
    for yan, y in yuvalar.items():
        pl, b = isim_plaka(en_isim[yan], y["met"], y["kutu"], isim_tr, y["maks_yari"])
        mx, my, _ = hedef(y["kutu"], y["met"])
        t.alpha_composite(pl, (int(round(mx - pl.width / 2)), int(round(my - pl.height / 2))))
    cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, en_tag)
    pl = altin_sekil(cr, prof1, (cu, ct))
    t.alpha_composite(pl, (int(round(TUVAL[0] / 2 - pl.width / 2)),
                           int(round((tag_kutu[1] + tag_kutu[3]) / 2 - pl.height / 2))))
    kaydet(t, OUT / "SINIR_ORNEK.jpg")
    gonder("SINIR_ORNEK.jpg")

    # --- kapilar: onayli poster yeniden uretilip karsilastirilir
    kt = temiz.convert("RGBA").copy()
    for yan, y in yuvalar.items():
        ad = NEW_LEFT if yan == "sol" else NEW_RIGHT
        pl, b = isim_plaka(ad, y["met"], y["kutu"], isim_tr, y["maks_yari"])
        mx, my, _ = hedef(y["kutu"], y["met"])
        kt.alpha_composite(pl, (int(round(mx - pl.width / 2)), int(round(my - pl.height / 2))))
    cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, TAGLINES["A"])
    pl = altin_sekil(cr, prof1, (cu, ct))
    kt.alpha_composite(pl, (int(round(TUVAL[0] / 2 - pl.width / 2)),
                            int(round((tag_kutu[1] + tag_kutu[3]) / 2 - pl.height / 2))))
    d["isim_kapisi"] = isim_kontrol(kt)
    d["tagline_kapisi"] = tagline_kontrol(kt, (760, 2545))
    log(f"ISIM KAPISI: {json.dumps(d['isim_kapisi'])}")
    log(f"TAGLINE KAPISI: {json.dumps(d['tagline_kapisi'])}")
    if not d["isim_kapisi"]["gecti"]:
        raise SystemExit(f"ISIM KAPISI BASARISIZ: {d['isim_kapisi']}")
    if not d["tagline_kapisi"]["gecti"]:
        raise SystemExit(f"TAGLINE KAPISI BASARISIZ: {d['tagline_kapisi']}")

    rapor(d)
    return d


def rapor(d):
    sol, sag = d["yuvalar"]["sol"], d["yuvalar"]["sag"]
    m = ["# Etsy giris sinirlari - olcum", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", ""] + [f"- {x}" for x in d["degisen"]] + [
         "", "### Degismeyen", ""] + [f"- {x}" for x in d["degismeyen"]] + [
         "", "## Yuva sinirlari", "",
         f"Isim ile sonsuzluk arasindaki bosluk referanstan (min {d['min_bosluk']} px) az",
         "olamaz. Isim kendi kucuk sembolunun altinda ORTALI oldugu icin kullanilabilir",
         "genislik merkeze gore simetriktir:", "",
         "| yuva | merkez x | azami genislik |", "| --- | --- | --- |",
         f"| sol (Cancer) | {sol['merkez']} | **{sol['maks_genislik']:.0f} px** |",
         f"| sag (Libra) | {sag['merkez']} | **{sag['maks_genislik']:.0f} px** |", "",
         f"Sag yuva belirleyici: sonsuzluk isareti sagda daha yakin oldugu icin "
         f"{sag['maks_genislik']:.0f} px, solun {sol['maks_genislik']:.0f} px'inin "
         f"%{100 * sag['maks_genislik'] / sol['maks_genislik']:.0f}'i.", "",
         "## Isim olcumu (tam boyda, kucultmesiz)", "",
         "| isim | harf | sol px | sol | sag px | sag | sagda gereken olcek |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for s in sorted(d["isim_olcum"], key=lambda x: -x["sag"]["genislik"]):
        m.append(f"| {s['isim']} | {s['harf']} | {s['sol']['genislik']} "
                 f"| {'sigdi' if s['sol']['sigdi'] else 'TASTI'} | {s['sag']['genislik']} "
                 f"| {'sigdi' if s['sag']['sigdi'] else 'TASTI'} "
                 f"| {'%' + str(int(s['sag']['gereken_olcek'] * 100)) if not s['sag']['sigdi'] else '-'} |")
    sol_ok = [s for s in d["isim_olcum"] if s["sol"]["sigdi"]]
    sag_ok = [s for s in d["isim_olcum"] if s["sag"]["sigdi"]]
    sol_en = max((len(s["isim"]) for s in sol_ok), default=0)
    sag_en = max((len(s["isim"]) for s in sag_ok), default=0)
    m += ["", "### Sonuc", "",
          f"- **En genis harfle (MMMM...) tam boyda sigan azami harf sayisi: "
          f"sol {d['m_testi']['sol']}, sag {d['m_testi']['sag']}.** Belirleyici sag yuva: "
          f"**{d['m_testi']['sag']} harf**.",
          f"- **Normal isimlerde (olculen ortalama {d['px_harf']['sag']} px/harf) azami: "
          f"sol {d['normal_azami']['sol']}, sag {d['normal_azami']['sag']} harf.** "
          f"Belirleyici sag yuva: **{d['normal_azami']['sag']} harf**.",
          f"- Listede tam boyda sigan en uzun adlar: sol "
          f"{', '.join(s['isim'] for s in sol_ok if len(s['isim']) == sol_en) or '-'} "
          f"({sol_en} harf), sag "
          f"{', '.join(s['isim'] for s in sag_ok if len(s['isim']) == sag_en) or '-'} "
          f"({sag_en} harf).",
          f"- Toplam {len(d['isim_olcum'])} adayin {len(sag_ok)} tanesi sag yuvaya tam boyda "
          f"sigiyor; kalan {len(d['isim_olcum']) - len(sag_ok)} tanesi kuculuyor.", "",
          "### Neden sag yuva bu kadar dar", "",
          f"Referansta LIBRA {d['kenar']['isim_dis_kenar'][1] - 1495} px genisliginde ve "
          f"yuvanin TAMAMINI dolduruyor: sag isim zaten azami olcude. Isim kendi kucuk "
          f"sembolunun altinda ortali kaldigi ve sonsuzluk isaretine {d['min_bosluk']} px "
          f"birakmak zorunda oldugu icin sagda bir harf bile buyume payi yok. Tasarimin dis "
          f"kenarlari ayna simetrik ({d['kenar']['isim_dis_kenar'][0]} / "
          f"{d['kenar']['isim_dis_kenar'][1]}, toplam genislik {TUVAL[0]}), yani disa dogru "
          f"bos alan da yok. Bu bir hata degil, onayli yerlesimin olcusu.", ""]
    m += ["", "## Tagline olcumu (punto " + str(TAG_PUNTO) + ", sinir "
          f"{TAG_MAKS_W} px)", "",
          "| karakter | genislik px | sonuc | gereken olcek | metin |",
          "| --- | --- | --- | --- | --- |"]
    for o in sorted(d["tag_olcum"], key=lambda x: -x["genislik"]):
        m.append(f"| {o['karakter']} | {o['genislik']} | "
                 f"{'sigdi' if o['sigdi'] else 'TASTI'} | "
                 f"{'%' + str(int(o['gereken_olcek'] * 100)) if not o['sigdi'] else '-'} "
                 f"| {o['metin']} |")
    m += ["", "### Sonuc", "",
          f"- Karakter basina genislik: ortalama {d['tag_kr_genislik']['ort']} px, "
          f"en genis metinde {d['tag_kr_genislik']['maks']} px.",
          f"- **Tam boyda guvenle sigan azami karakter: normal metinde "
          f"{d['tag_azami']['ortalama_metinde']}, en genis harflerle "
          f"{d['tag_azami']['en_genis_metinde']}.**", "",
          "## Sinir asiminda ne olur", "",
          "Mevcut kural degismedi: **yalniz o oge orantili kuculur**, digerlerine",
          "dokunulmaz. Isimde kuculme yalniz o ismi etkiler (cift icindeki diger isim",
          "tam boyda kalir), tagline'da yalniz tagline kuculur. Kucultmenin alt siniri",
          "yoktur; cok uzun girislerde oge belirgin kucuk gorunur (olculdu: MAXIMILIAN",
          "sag yuvada %47'ye iner).", "",
          "## Onerilen Etsy sinirlari", "",
          "| alan | onerilen azami | gerekce |", "| --- | --- | --- |",
          f"| Isim - kuculmesiz garanti | **{d['m_testi']['sag']} harf** | en genis harfle "
          f"(M/W) bile sag yuvaya tam boyda sigar |",
          f"| Isim - normal harflerle | {d['normal_azami']['sag']} harf | olculen ortalama "
          f"{d['px_harf']['sag']} px/harf |",
          f"| Isim - kuculmeye izin verilirse | 11+ harf | ABDURRAHMAN %37'ye inerek sigar; "
          f"ciftin iki adi farkli boyda gorunur |",
          f"| Tagline | **{d['tag_azami']['en_genis_metinde']} karakter** | en genis "
          f"harflerle bile tam boyda sigar |",
          f"| Tagline (yumusak uyari) | {d['tag_azami']['ortalama_metinde']} karakter "
          f"| ortalama metinde sigar |", "",
          f"SINIR_ORNEK.jpg: {d['ornek']['sol']} / {d['ornek']['sag']} "
          f"ve \"{d['ornek']['tagline']}\".", "",
          "## Kapilar", "",
          f"- Isim kapisi: {'GECTI' if d['isim_kapisi']['gecti'] else 'KALDI'} "
          f"(kayma {d['isim_kapisi']['kayma_px']} px, fark {d['isim_kapisi']['murekkep_fark']})",
          f"- Tagline kapisi (YENI): {'GECTI' if d['tagline_kapisi']['gecti'] else 'KALDI'} "
          f"(kayma {d['tagline_kapisi']['kayma_px']} px, "
          f"fark {d['tagline_kapisi']['murekkep_fark']})"]
    (OUT / "SINIR_OLCUM.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("SINIR_OLCUM.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    a = ap.parse_args()
    kos(indir=not a.yerel)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
