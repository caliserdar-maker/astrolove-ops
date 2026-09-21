#!/usr/bin/env python3
"""
Kisisellestirme pilotu, uretim asamasi (kisisel_pilot.py --stage uret).

Kesif asamasinin olctugu font + altin profil ile:
  - SERDAR / LENA isim plakalari (orijinal cap yuksekligi, merkez, doku)
  - 3 tagline varyanti (orijinal punto; sigmazsa orantili kucultme, %70 taban)
  - CANCER / LIBRA dogrulama plakalari + orijinalle piksel karsilastirma
  - Midnight Blue 4:5 poster (bilesenlerden, orijinal tuval 4000x5000)
  - yakin kirpimlar ve STIL_TEST.md
Cikti: ASTROLOVE/TEMP/KISISEL_PILOT/

Yerlesim modeli: Canva kutusu PNG'nin TAMAMINI kapsar. Bu yuzden bir plakanin
tuvaldeki gercek cam yuksekligi  kutu_h * (ink_h / png_h)  olur; yeni yazi
dogrudan tuval koordinatinda bu yukseklikte ve ayni merkezde cizilir, boylece
isim uzunlugu degisince olcek kaymaz.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kisisel_pilot import (BOX, CANVAS, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, OUT, REF, TAGLINES, alpha_of, altin_plaka,
                           bbox_of, cap_icin_boyut, ciz_metin, eta, fetch, font_yukle,
                           ink_mask, iou, jpg_kaydet, log, lsf, rc, satir_profili)

Image.MAX_IMAGE_PIXELS = None
TR_TEST = "ğıİöüşçŞÇÜÖ"


def ref_metrik(path):
    """Referans plakadan: ink bbox, png boyutu, altin satir profili."""
    im, arr = alpha_of(path)
    m = ink_mask(arr)
    bb = bbox_of(m)
    prof = satir_profili(arr, m, bb)
    al = arr[..., 3]
    yumusak = float(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1)) > 0.45
    return {"png": (im.width, im.height), "bb": bb, "prof": prof, "yumusak": yumusak,
            "mask": m, "rgba": arr}


def tuval_hedefi(kutu, met):
    """Kutu + referans plaka -> tuvaldeki (merkez_x, merkez_y, cam_yuksekligi)."""
    top, left, w, h = kutu
    pw, ph = met["png"]
    x0, y0, x1, y1 = met["bb"]
    olcek_y = h / ph
    cam_h = (y1 - y0) * olcek_y
    merkez_y = top + ((y0 + y1) / 2) * olcek_y
    merkez_x = left + w / 2
    return merkez_x, merkez_y, cam_h


def ciz_yaz(tuval, metin, font_path, wght, met, kutu, maks_w=None, min_oran=0.70,
            punto_sabit=None, tr_orani=0.0):
    """Metni tuvale, referansla ayni cam yuksekligi/merkez/altin dokuyla cizer."""
    mx, my, cam_h = tuval_hedefi(kutu, met)
    if punto_sabit is None:
        size = cap_icin_boyut(font_path, metin, cam_h, wght)
    else:
        size = punto_sabit
    olcek = 1.0
    f = font_yukle(font_path, size, wght)
    cr, _ = ciz_metin(f, metin, size * tr_orani)
    if maks_w and cr.width > maks_w:
        olcek = max(maks_w / cr.width, min_oran)
        size = max(int(round(size * olcek)), 4)
        f = font_yukle(font_path, size, wght)
        cr, _ = ciz_metin(f, metin, size * tr_orani)
    plaka = altin_govde(cr, met)
    x = int(round(mx - plaka.width / 2))
    y = int(round(my - plaka.height / 2))
    tuval.alpha_composite(plaka, (x, y))
    return {"metin": metin, "punto": size, "olcek": round(olcek, 3),
            "tracking": round(size * tr_orani, 2),
            "boyut": [plaka.width, plaka.height], "yer": [x, y],
            "sigdi": not (maks_w and cr.width > maks_w and olcek <= min_oran + 1e-6)}


def altin_govde(mask_img, met):
    """L maskesine referansin altin satir profilini uygular."""
    m = np.asarray(mask_img).astype(np.float32) / 255.0
    h, w = m.shape
    prof = met["prof"]
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    grad = prof[lo] * (1 - t) + prof[hi] * t
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(np.repeat(grad[:, None, :], w, axis=1), 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    pl = Image.fromarray(out, "RGBA")
    if met["yumusak"]:
        from PIL import ImageFilter
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.GaussianBlur(max(h * 0.05, 1)))
        arr = np.asarray(pl).copy()
        arr[..., 3] = np.clip(np.maximum(arr[..., 3].astype(np.float32),
                                         np.asarray(hale).astype(np.float32) * 0.35), 0, 255).astype(np.uint8)
        pl = Image.fromarray(arr, "RGBA")
    return pl


def kutuya_koy(tuval, im, kutu):
    """Kutuyu tuvale yapistirir. Negatif ofset (ornek bg top=-168.1) kirpilarak
    karsilanir; alpha_composite negatif hedef kabul etmez."""
    top, left, w, h = kutu
    yeni = im.convert("RGBA").resize((max(int(round(w)), 1), max(int(round(h)), 1)), Image.LANCZOS)
    x, y = int(round(left)), int(round(top))
    kx, ky = max(-x, 0), max(-y, 0)
    if kx or ky:
        if kx >= yeni.width or ky >= yeni.height:
            return
        yeni = yeni.crop((kx, ky, yeni.width, yeni.height))
        x, y = x + kx, y + ky
    if x >= tuval.width or y >= tuval.height:
        return
    yeni = yeni.crop((0, 0, min(yeni.width, tuval.width - x), min(yeni.height, tuval.height - y)))
    tuval.alpha_composite(yeni, (x, y))


def tr_destek(font_path):
    from fontTools.ttLib import TTFont
    cm = set()
    for t in TTFont(str(font_path))["cmap"].tables:
        cm |= set(t.cmap.keys())
    eksik = [c for c in TR_TEST if ord(c) not in cm]
    return eksik


def stage_uret(a):
    OUT.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    rapor = {}

    klas = {k: lsf(v) for k, v in FOLDERS.items()}

    def bul(k, kalip):
        for f in klas[k]:
            if re.fullmatch(kalip, f, re.I):
                return f
        raise FileNotFoundError(f"{k}: {kalip} yok -> {klas[k][:12]}")

    ana_ad = bul("main", r"(cancer_libra|libra_cancer)_gold\.png")
    sym_c = bul("small", r"cancer[^/]*\.png")
    sym_l = bul("small", r"libra[^/]*\.png")

    istek = [("names", "cancer_name_gold.png"), ("names", "libra_name_gold.png"),
             ("parts", "tagline.png"), ("parts", "logo.png"), ("parts", "circle.png"),
             ("parts", "midnight_blue_bg.jpg"), ("main", ana_ad),
             ("small", sym_c), ("small", sym_l)]
    yol = {}
    for i, (k, f) in enumerate(istek, 1):
        yol[(k, f)] = fetch(FOLDERS[k], f, REF / k)
        eta(i, len(istek), "referans indirme")

    m_cancer = ref_metrik(yol[("names", "cancer_name_gold.png")])
    m_libra = ref_metrik(yol[("names", "libra_name_gold.png")])
    m_tag = ref_metrik(yol[("parts", "tagline.png")])

    isim_font = FONT_DIR / a.isim_font
    tag_font = FONT_DIR / a.tagline_font
    iw = int(a.isim_wght) if a.isim_wght else None
    tw = int(a.tagline_wght) if a.tagline_wght else None
    log(f"isim font={isim_font.name} wght={iw} | tagline font={tag_font.name} wght={tw}")

    rapor["turkce"] = {"isim_font_eksik": tr_destek(isim_font),
                       "tagline_font_eksik": tr_destek(tag_font)}
    log("TURKCE eksik glif: " + json.dumps(rapor["turkce"]))

    # --- tagline puntosu: orijinal metnin orijinal yuksekligine gore (bir kez)
    _, _, tag_cam_h = tuval_hedefi(BOX["tagline"], m_tag)
    tag_punto = cap_icin_boyut(tag_font, ORIG_TAGLINE, tag_cam_h, tw)
    tag_maks_w = BOX["tagline"][2]
    from kisisel_pilot import tracking_icin as _tr
    tpw = m_tag["png"][0]
    tx0, _ty0, tx1, _ty1 = m_tag["bb"]
    tag_tr = _tr(font_yukle(tag_font, tag_punto, tw), ORIG_TAGLINE,
                 (tx1 - tx0) * (BOX["tagline"][2] / tpw))
    tag_tr_orani = tag_tr / tag_punto
    log(f"tagline tracking orani {tag_tr_orani:.4f} (orijinal genislikten olculdu)")
    log(f"tagline cam yuksekligi {tag_cam_h:.1f} px -> punto {tag_punto}, maks genislik {tag_maks_w:.0f}")

    # --- zemin (yazisiz poster): her varyant bunun kopyasi
    zemin = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    kutuya_koy(zemin, Image.open(yol[("parts", "midnight_blue_bg.jpg")]), BOX["bg"])
    kutuya_koy(zemin, Image.open(yol[("parts", "circle.png")]), BOX["ring"])
    kutuya_koy(zemin, Image.open(yol[("main", ana_ad)]), BOX["main"])
    kutuya_koy(zemin, Image.open(yol[("small", sym_c)]), BOX["sym_left"])
    kutuya_koy(zemin, Image.open(yol[("small", sym_l)]), BOX["sym_right"])
    kutuya_koy(zemin, Image.open(yol[("parts", "logo.png")]), BOX["infinity"])
    log("zemin kuruldu (bg + halka + ana sembol + 2 kucuk sembol + sonsuzluk)")

    # --- dogrulama: ayni yontemle CANCER/LIBRA uret, orijinalle karsilastir
    rapor["stil_testi"] = {}
    tr_oranlari = []
    for ad, metin, met in (("CANCER", "CANCER", m_cancer), ("LIBRA", "LIBRA", m_libra)):
        kutu = BOX["name_left"] if ad == "CANCER" else BOX["name_right"]
        _, _, cam_h = tuval_hedefi(kutu, met)
        size = cap_icin_boyut(isim_font, metin, cam_h, iw)
        f = font_yukle(isim_font, size, iw)
        # orijinalin tuvaldeki cam genisligine gore harf araligi
        pw, ph = met["png"]
        x0, y0, x1, y1 = met["bb"]
        hedef_w = (x1 - x0) * (kutu[2] / pw)
        from kisisel_pilot import tracking_icin
        tr = tracking_icin(f, metin, hedef_w)
        cr, _ = ciz_metin(f, metin, tr)
        orij = Image.fromarray((met["mask"][y0:y1, x0:x1] * 255).astype(np.uint8), "L")
        yeni = cr.resize(orij.size, Image.LANCZOS)
        skor = iou(np.asarray(orij), np.asarray(yeni))
        # altin rengi karsilastirmasi
        o_rgb = np.median(met["rgba"][..., :3][met["mask"]], axis=0)
        y_pl = altin_govde(cr, met)
        y_arr = np.asarray(y_pl)
        y_rgb = np.median(y_arr[..., :3][y_arr[..., 3] > 40], axis=0)
        tr_oranlari.append(tr / size)
        rapor["stil_testi"][ad] = {"iou": round(skor, 4), "punto": size,
                                   "tracking": round(tr, 2),
                                   "tracking_orani": round(tr / size, 4),
                                   "orijinal_rgb": [int(v) for v in o_rgb],
                                   "yeni_rgb": [int(v) for v in y_rgb],
                                   "rgb_fark": round(float(np.abs(o_rgb - y_rgb).max()), 1)}
        log(f"STIL TESTI {ad}: " + json.dumps(rapor["stil_testi"][ad]))

    isim_tr_orani = sum(tr_oranlari) / len(tr_oranlari)
    log(f"isim tracking orani {isim_tr_orani:.4f} (CANCER/LIBRA ortalamasi)")

    # --- posterler
    rapor["yerlesim"] = {}
    posterler = {}
    for kod in ("A", "B", "C"):
        t = zemin.copy()
        sol = ciz_yaz(t, NEW_LEFT, isim_font, iw, m_cancer, BOX["name_left"],
                      tr_orani=isim_tr_orani)
        sag = ciz_yaz(t, NEW_RIGHT, isim_font, iw, m_libra, BOX["name_right"],
                      tr_orani=isim_tr_orani)
        tg = ciz_yaz(t, TAGLINES[kod], tag_font, tw, m_tag, BOX["tagline"],
                     maks_w=tag_maks_w, punto_sabit=tag_punto, tr_orani=tag_tr_orani)
        rapor["yerlesim"][kod] = {"sol": sol, "sag": sag, "tagline": tg}
        posterler[kod] = t
        p = OUT / f"PILOT_{kod}.jpg"
        q = jpg_kaydet(t.resize((2400, 3000), Image.LANCZOS), p, 1_500_000)
        log(f"PILOT_{kod}.jpg q={q} {p.stat().st_size / 1e6:.2f} MB | tagline {json.dumps(tg, ensure_ascii=False)}")

    # --- orijinal poster (karsilastirma bandi icin): orijinal isim + tagline plakalari
    orij_poster = zemin.copy()
    kutuya_koy(orij_poster, Image.open(yol[("names", "cancer_name_gold.png")]), BOX["name_left"])
    kutuya_koy(orij_poster, Image.open(yol[("names", "libra_name_gold.png")]), BOX["name_right"])
    kutuya_koy(orij_poster, Image.open(yol[("parts", "tagline.png")]), BOX["tagline"])

    # --- YAKIN_ISIMLER: isim bandi, ust orijinal / alt yeni
    bt, bl = BOX["name_left"][0], BOX["sym_left"][1]
    bant = (int(bl - 120), int(bt - 90),
            int(BOX["name_right"][1] + BOX["name_right"][2] + 120), int(bt + BOX["name_left"][3] + 90))
    ust = orij_poster.crop(bant)
    alt = posterler["A"].crop(bant)
    yi = Image.new("RGB", (ust.width, ust.height * 2 + 24), (10, 12, 26))
    yi.paste(ust.convert("RGB"), (0, 0))
    yi.paste(alt.convert("RGB"), (0, ust.height + 24))
    yi = yi.resize((1600, int(yi.height * 1600 / yi.width)), Image.LANCZOS)
    q = jpg_kaydet(yi, OUT / "YAKIN_ISIMLER.jpg", 400_000)
    log(f"YAKIN_ISIMLER.jpg q={q} {(OUT / 'YAKIN_ISIMLER.jpg').stat().st_size / 1e3:.0f} KB")

    # --- YAKIN_TAGLINE: orijinal + 3 varyant alt alta
    tb = (int(BOX["tagline"][1] - 140), int(BOX["tagline"][0] - 70),
          int(BOX["tagline"][1] + BOX["tagline"][2] + 140), int(BOX["tagline"][0] + BOX["tagline"][3] + 70))
    seritler = [orij_poster.crop(tb)] + [posterler[k].crop(tb) for k in ("A", "B", "C")]
    yt = Image.new("RGB", (seritler[0].width, sum(s.height for s in seritler) + 24 * 3), (10, 12, 26))
    y = 0
    for s in seritler:
        yt.paste(s.convert("RGB"), (0, y))
        y += s.height + 24
    yt = yt.resize((1600, int(yt.height * 1600 / yt.width)), Image.LANCZOS)
    q = jpg_kaydet(yt, OUT / "YAKIN_TAGLINE.jpg", 400_000)
    log(f"YAKIN_TAGLINE.jpg q={q} {(OUT / 'YAKIN_TAGLINE.jpg').stat().st_size / 1e3:.0f} KB")

    # --- STIL_TEST.md
    st = rapor["stil_testi"]
    tr_e = rapor["turkce"]
    sigmayan = [k for k, v in rapor["yerlesim"].items() if not v["tagline"]["sigdi"]]
    md = [
        "# Kisisellestirme stil testi", "",
        f"Kaynak: Canva Blue 4/5 sayfa 28 CANCER_LIBRA, tuval {CANVAS[0]}x{CANVAS[1]}.",
        "Temmuz 2026 altin yazi ureteci ne repoda ne Drive'da bulundu; font ve altin",
        "doku mevcut plakalardan OLCULEREK turetildi.", "",
        "## Font ve lisans", "",
        "| rol | font | agirlik | lisans | ticari kullanim |",
        "| --- | --- | --- | --- | --- |",
        f"| isim | {isim_font.name} | {iw or '-'} | SIL OFL 1.1 (google/fonts ofl/) | serbest |",
        f"| tagline | {tag_font.name} | {tw or '-'} | SIL OFL 1.1 (google/fonts ofl/) | serbest |", "",
        "Font secimi olculerek yapildi: her aday referans plakanin cap yuksekligine",
        "oturtuldu, harf araligi referans genisligini tutturacak sekilde arandi, maske",
        "IoU ile siralandi. Yerel kalibrasyon: bilinen bir fontla uretilmis referansta",
        "dogru font 1. sirada IoU 0.855 aldi; yani 0.855 pratik tavandir.", "",
        "## Piksel karsilastirmasi (stil sadakati)", "",
        "Ayni yontemle uretilen CANCER/LIBRA plakasi, orijinal *_name_gold.png ile",
        "ayni kutuya olceklenip karsilastirildi.", "",
        "| plaka | maske IoU | harf araligi/punto | altin RGB (orijinal) | altin RGB (yeni) | maks kanal farki |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for ad, v in st.items():
        md.append(f"| {ad} | {v['iou']} | {v['tracking_orani']} | {tuple(v['orijinal_rgb'])} "
                  f"| {tuple(v['yeni_rgb'])} | {v['rgb_fark']} |")
    md += ["", "## Turkce karakter", "",
           f"Test dizisi: `{TR_TEST}`", "",
           f"- isim fontu eksik glif: {tr_e['isim_font_eksik'] or 'YOK'}",
           f"- tagline fontu eksik glif: {tr_e['tagline_font_eksik'] or 'YOK'}",
           f"- C varyanti ({TAGLINES['C']}) uretildi.", "",
           "## Uzun metin kurali", "",
           f"Tagline kutusu genisligi {tag_maks_w:.0f} px, ortak punto {tag_punto}.",
           "Sigmayan varyantta punto orantili kucultulur, %70 tabanin altina inilmez.", ""]
    for k, v in rapor["yerlesim"].items():
        tg = v["tagline"]
        md.append(f"- {k}: punto {tg['punto']}, olcek %{tg['olcek'] * 100:.0f}, "
                  f"genislik {tg['boyut'][0]} px, {'SIGDI' if tg['sigdi'] else 'TABANA DAYANDI'}")
    if sigmayan:
        md += ["", f"**UYARI:** {', '.join(sigmayan)} varyantinda %70 tabani asildi."]
    (OUT / "STIL_TEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "uret.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))

    # --- Drive'a yaz
    for f in ("PILOT_A.jpg", "PILOT_B.jpg", "PILOT_C.jpg", "YAKIN_ISIMLER.jpg",
              "YAKIN_TAGLINE.jpg", "STIL_TEST.md"):
        rc("copy", str(OUT / f), DEST)
        log(f"Drive'a yazildi: {DEST}/{f}")
    log("uret bitti")
