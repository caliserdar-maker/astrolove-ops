#!/usr/bin/env python3
"""Size Guide karti 14 boy (5x7 eklenmis) - onayli pod_gallery_sample.py'yi import eder,
tasarimi/fontu/duzeni degistirmez; yalniz SIZES listesine 5x7 (13x18 cm) ve "5:7" grubu eklenir.

Cift x edisyon basina 08_SIZES karti yeniden cizilir; QC: 3000x2250, palet sapmasi <= 16,
grup bosluklari esit (|bosluk - hedef| <= 2.5 px, grup sayisi kadar + 2 bosluk).
Cikti: <out>/<PAIR>/<ED>/08_SIZES_<PAIR>_<ED>.jpg -> Drive TEMP/POD_SIZE_GUIDE_15/...
ETSY'YE YUKLEME YOK.
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import pod_gallery_sample as G  # noqa: E402

YENI = ("5x7", 5, 7, 13, 18, "5:7")
YENI_A1 = ("A1", 23.4, 33.1, 59.4, 84.1, "A")      # Serdar karari 20 Eyl: A serisine A1
DURUM_SUT = ["pair", "status", "cards", "fail", "secs", "ts_utc"]
CSV_SUT = ["pair", "edition", "dosya", "boyut", "palet_sapma", "bosluk_sapma", "bosluk_yayilim",
           "metin_bosluk", "durum", "neden"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def yamali():
    """15 boy: 5x7 -> yeni '5:7' grubu (en sona), A1 -> A SERIES grubunun en dis kutusu."""
    if YENI not in G.SIZES:
        G.SIZES.append(YENI)
    if YENI_A1 not in G.SIZES:
        G.SIZES.append(YENI_A1)
    if "5:7" not in G.GROUP_ORDER:
        G.GROUP_ORDER.append("5:7")
    G.GROUP_TITLE["5:7"] = "5:7"


# ------------------------------------------------------------------ v2 yerlesim (20 Eyl: 5:7 sag kenara tasiyordu)
KENAR = 70          # tuval kenarlarindan korunacak en az bosluk (metin ve kutular)
BOSLUK_MIN = 24     # gruplar arasi en az gorunur bosluk
METIN_PAY = 60      # komsu GRUPLARIN metin sinir kutulari arasinda en az yatay bosluk (Serdar, 20 Eyl)
CETVEL_PAY = 210    # eksen cizgisi + "175 CM" yazisi + cm etiketleri icin ayrilan sag pay


def _fontlar(F):
    return {"lab": F.f("sans", G.solve_size(F, "sans", 600, 20), 600),
            "ttl": F.f("sans", G.solve_size(F, "sans", 700, G.REF["body_cap"]), 700),
            "txt": F.f("sans", G.solve_size(F, "sans", 400, 19), 400),
            "ruler": F.f("sans", G.solve_size(F, "sans", 500, 16), 500)}


def _satirlar(z, tek):
    """Boy yazisi satirlari. Tek boylu grupta (11:14, 5:7) iki satir: 'x in' / 'y cm'."""
    lab, win, hin, wcm, hcm, _ = z
    if tek:
        return [f"{lab} in", f"{wcm:g}\u00d7{hcm:g} cm"]
    if lab.startswith("A"):
        return [f"{lab} \u00b7 {win:g}\u00d7{hin:g} in \u00b7 {wcm:g}\u00d7{hcm:g} cm"]
    return [f"{lab} in \u00b7 {wcm:g}\u00d7{hcm:g} cm"]


def _grup_ogeleri(g):
    return sorted([z for z in G.SIZES if z[5] == g], key=lambda z: -z[4])


def cetvel_x():
    """Eksen cizgisi, ONAYLI 13 boy duzenindeki yerinde kalir (5 grup, SG_SCALE)."""
    eski = [z for z in G.SIZES if z[5] != "5:7"]
    dis = [max(z[3] for z in eski if z[5] == g) * G.SG_SCALE
           for g in ["3:4", "2:3", "A", "4:5", "11:14"]]
    return (G.W - sum(dis)) / 7.0


def metin_genislikleri(d, F):
    """Grup basina en genis metin (oran adi ya da boy satiri) px."""
    f = _fontlar(F)
    out = []
    for g in G.GROUP_ORDER:
        ogeler = _grup_ogeleri(g)
        w = G.text_w(d, G.GROUP_TITLE[g], f["ttl"], 4)
        for z in ogeler:
            w = max(w, d.textlength(z[0], font=f["lab"]))          # kutu ici etiket
            for s in _satirlar(z, len(ogeler) == 1):
                w = max(w, d.textlength(s, font=f["txt"]))
        out.append(w)
    return out


def yerlesim_v3(d, F):
    """v3 (20 Eyl, Serdar): 6 grubun EN DIS kutularinin dis kenarlari arasindaki bosluk G
    BIREBIR esit; eksen->ilk kutu = G, son kutu->sag icerik siniri (W-KENAR) = G.
    G = (icerik_genisligi - toplam_kutu) / 7. Alt yazilar kutu merkezine ortali; komsu
    metinler cakisirsa (pay METIN_PAY) ORTAK olcek kucultulur -> kutular daralir, G buyur.
    Donus: (olcek, rx, [(kutu_x0, kutu_x1)], G, [merkezler])."""
    rx = cetvel_x()
    x1_alan = G.W - KENAR
    metin_w = metin_genislikleri(d, F)
    olcek = G.SG_SCALE
    while True:
        kutu_w = [max(z[3] for z in _grup_ogeleri(g)) * olcek for g in G.GROUP_ORDER]
        bos = (x1_alan - rx - sum(kutu_w)) / (len(kutu_w) + 1)
        # kutu yerlesimi
        kutular, x = [], rx + bos
        for w in kutu_w:
            kutular.append((x, x + w))
            x += w + bos
        merkez = [(a + b) / 2 for a, b in kutular]
        tamam = bos >= BOSLUK_MIN
        for i in range(len(merkez) - 1):        # komsu metin cakismasi
            if (merkez[i + 1] - metin_w[i + 1] / 2) - (merkez[i] + metin_w[i] / 2) < METIN_PAY:
                tamam = False
        if merkez[0] - metin_w[0] / 2 < rx:      # ilk metin ekseni gecmesin
            tamam = False
        if merkez[-1] + metin_w[-1] / 2 > G.W - KENAR:   # son metin icerik sinirini gecmesin
            tamam = False
        if tamam or olcek <= 3.0:
            break
        olcek = round(olcek - 0.1, 2)
    return olcek, rx, kutular, bos, merkez


def card_sizes_v2(pal, F, poster, pair_txt):
    """Onayli card_sizes ile ayni tasarim; yerlesim v3 (esit kutu araliklari). Donus: (im, kayit)."""
    from PIL import ImageDraw
    t = G.TEXT["SIZES"]
    im, d = G.card_base(pal, F, G.vtext(t["kicker"]), t["title"], pair_txt, G.vtext(t["footer"]))
    f = _fontlar(F)
    base_y = G.SG_BASE_Y
    accent, rule = pal["bar"], pal["rule"]
    zemin = G.mix(pal["ink"], pal["bg"], 0.90)
    cizgi = G.mix(pal["ink"], pal["bg"], 0.45)
    s, rx, kutular, Gb, merkez = yerlesim_v3(d, F)
    kayit = {"metin": [], "kutu": [], "olcek": s, "bosluk": round(Gb, 2), "rx": round(rx, 1),
             "kutu_plan": [(round(a, 1), round(b, 1)) for a, b in kutular]}
    x_end = kutular[-1][1]
    d.line([rx, base_y, x_end, base_y], fill=cizgi, width=3)
    top = base_y - 175 * s
    d.line([rx, base_y, rx, top], fill=rule, width=3)
    for cm in range(0, 176, 25):
        y = base_y - cm * s
        uzun = cm % 50 == 0
        d.line([rx, y, rx + (30 if uzun else 16), y], fill=rule, width=3)
        if uzun and 0 < cm < 175:
            d.text((rx + 40, y), f"{cm}", font=f["ruler"], fill=G.mix(pal["ink"], pal["bg"], 0.2), anchor="lm")
    d.line([rx - 12, top, rx + 30, top], fill=rule, width=3)
    G.draw_tracked(d, (rx + 6, top - 40), "175 CM \u00b7 5'9\"", f["ruler"], pal["ink"], tracking=3, anchor="l")

    overlay = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    etiketler = []
    for gi, g in enumerate(G.GROUP_ORDER):
        cx = merkez[gi]
        for k, z in enumerate(_grup_ogeleri(g)):
            w, h = z[3] * s, z[4] * s
            x1, y1 = cx - w / 2, base_y - h
            od.rectangle([x1, y1, x1 + w, base_y], fill=(zemin if k == 0 else pal["bg"]) + (255,),
                         outline=(accent if k == 0 else cizgi) + (255,), width=4 if k == 0 else 3)
            kayit["kutu"].append((round(x1, 1), round(y1, 1), round(x1 + w, 1), base_y, z[0]))
            etiketler.append(((cx, y1 + 10), z[0], gi))
    im.paste(overlay, (0, 0), overlay)
    d = ImageDraw.Draw(im)
    for xy, lab, gi in etiketler:
        d.text(xy, lab, font=f["lab"], fill=G.mix(pal["ink"], pal["bg"], 0.15), anchor="ma")
        w = d.textlength(lab, font=f["lab"])
        kayit["metin"].append((xy[0] - w / 2, xy[1], xy[0] + w / 2, xy[1] + 26, lab, gi))
    for gi, g in enumerate(G.GROUP_ORDER):
        cx = merkez[gi]
        ogeler = _grup_ogeleri(g)
        ly = base_y + 24
        w = G.text_w(d, G.GROUP_TITLE[g], f["ttl"], 4)
        G.draw_tracked(d, (cx, ly), G.GROUP_TITLE[g], f["ttl"], accent, tracking=4, anchor="c")
        kayit["metin"].append((cx - w / 2, ly, cx + w / 2, ly + 38, G.GROUP_TITLE[g], gi))
        ly += 50
        for z in ogeler:
            for satir in _satirlar(z, len(ogeler) == 1):
                d.text((cx, ly), satir, font=f["txt"], fill=G.mix(pal["ink"], pal["bg"], 0.2), anchor="ma")
                w = d.textlength(satir, font=f["txt"])
                kayit["metin"].append((cx - w / 2, ly, cx + w / 2, ly + 28, satir, gi))
                ly += 32
    return im, kayit


def qc_v2(kayit):
    """Kapilar: metin/kutu kenardan >= KENAR, metinler kesismiyor, komsu GRUP metin
    sinir kutulari arasinda >= METIN_PAY px yatay bosluk. -> hata listesi."""
    errs = []
    for x0, y0, x1, y1, txt, _gi in kayit["metin"]:
        if x0 < KENAR or y0 < KENAR or x1 > G.W - KENAR or y1 > G.H - KENAR:
            errs.append(f"metin kenara tasti: {txt!r} ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})")
    for x0, y0, x1, y1, lab in kayit["kutu"]:
        if x0 < KENAR or y0 < KENAR or x1 > G.W - KENAR or y1 > G.H - KENAR:
            errs.append(f"kutu kenara yakin: {lab} ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})")
    m = kayit["metin"]
    for i in range(len(m)):
        for j in range(i + 1, len(m)):
            ax0, ay0, ax1, ay1, at, _ = m[i]
            bx0, by0, bx1, by1, bt, _ = m[j]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                errs.append(f"metin cakismasi: {at!r} x {bt!r}")
    kume = {}
    for x0, _y0, x1, _y1, _t, gi in m:
        a, b = kume.get(gi, (x0, x1))
        kume[gi] = (min(a, x0), max(b, x1))
    sirali = [kume[k] for k in sorted(kume)]
    araliklar = [sirali[i + 1][0] - sirali[i][1] for i in range(len(sirali) - 1)]
    kayit["metin_bosluk"] = round(min(araliklar), 1) if araliklar else None
    if araliklar and min(araliklar) < METIN_PAY:
        kotu = min(range(len(araliklar)), key=lambda i: araliklar[i])
        errs.append(f"komsu metin boslugu {araliklar[kotu]:.0f} px < {METIN_PAY} "
                    f"(grup {G.GROUP_ORDER[kotu]}-{G.GROUP_ORDER[kotu + 1]})")
    return errs

def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def kutu_olcumu(kart, F):
    """Cizilen aksan konturlu kutular V2 PLANINDAKI yerde mi? -> (max_sapma_px, olculen_kutu).
    Her grup icin beklenen kutu penceresinde (±20 px) aksan renkli kenarlar aranir."""
    from PIL import ImageDraw
    rgb = np.array(Image.open(kart).convert("RGB")).astype(int)
    y = G.SG_BASE_Y - 30
    bar = rgb[2120, 1500]
    d0 = ImageDraw.Draw(Image.new("RGB", (G.W, G.H), (255, 255, 255)))
    s, rx, kutular, Gb, merkez = yerlesim_v3(d0, F)
    sapmalar, n, kenarlar = [], 0, []
    for bx0, bx1 in kutular:
        a0, a1 = max(0, int(bx0) - 20), min(G.W, int(bx1) + 20)
        seg = np.abs(rgb[y, a0:a1] - bar).sum(1) < 60
        xs = np.where(seg)[0]
        if not len(xs):
            continue
        n += 1
        sol, sag = int(xs.min() + a0), int(xs.max() + a0)
        kenarlar.append((sol, sag))
        sapmalar += [abs(sol - bx0), abs(sag - bx1)]
    araliklar = ([kenarlar[0][0] - rx] + [kenarlar[i + 1][0] - kenarlar[i][1] for i in range(len(kenarlar) - 1)]
                 + [(G.W - KENAR) - kenarlar[-1][1]]) if len(kenarlar) == len(kutular) else []
    yayilim = round(max(araliklar) - min(araliklar), 1) if araliklar else None
    return (round(max(sapmalar), 1) if sapmalar else None), n, yayilim


def bosluklar(kart):
    """(bilgi amacli) bosluk listesi -> (bosluk listesi, hedef)."""
    rgb = np.array(Image.open(kart).convert("RGB")).astype(int)
    y = G.SG_BASE_Y - 30
    bar, rule = rgb[2120, 1500], rgb[418, 1500]
    _, kutular, hedef = G.sg_layout()
    rrow = np.abs(rgb[y] - rule).sum(1) < 60
    lim = int(kutular[0][0]) - 20
    rx = int(np.where(rrow[:lim])[0].min()) if rrow[:lim].any() else None
    kenarlar = []
    for bx0, bx1 in kutular:
        a0, a1 = max(0, int(bx0) - 30), min(G.W, int(bx1) + 30)
        seg = np.abs(rgb[y, a0:a1] - bar).sum(1) < 60
        xs = np.where(seg)[0]
        if len(xs):
            kenarlar.append((int(xs.min() + a0), int(xs.max() + a0)))
    if rx is None or len(kenarlar) != len(kutular):
        return [], hedef
    g = [rx, kenarlar[0][0] - rx]
    g += [kenarlar[i + 1][0] - kenarlar[i][1] for i in range(len(kenarlar) - 1)]
    g.append(G.W - kenarlar[-1][1])
    return g, hedef


def qc(kart, pal, F):
    errs = []
    im = Image.open(kart)
    if im.size != (G.W, G.H):
        errs.append(f"boyut {im.size}")
    mp = G.measure(kart)
    sapma = max(abs(mp[k][i] - pal[k][i]) for k in ("bg", "bar", "ink") for i in range(3))
    if sapma > 16:
        errs.append(f"palet sapmasi {sapma}")
    k_sapma, n_kutu, yayilim = kutu_olcumu(kart, F)
    if n_kutu != len(G.GROUP_ORDER):
        errs.append(f"kutu {n_kutu}/{len(G.GROUP_ORDER)}")
    elif k_sapma is None or k_sapma > 2.5:
        errs.append(f"kutu konum sapmasi {k_sapma}")
    if yayilim is None:
        errs.append("bosluk yayilimi olculemedi")
    elif yayilim > 1.0:
        errs.append(f"bosluk yayilimi {yayilim} px (esik 1.0)")
    return errs, sapma, (k_sapma if k_sapma is not None else ""), yayilim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--src", default="src")
    ap.add_argument("--out", default="out")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="")
    ap.add_argument("--rclone-out", default="")
    ap.add_argument("--ornek-cift", default="")
    ap.add_argument("--ornek-drv", default="gdrive:ASTROLOVE/TEMP/POD_5X7")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    yamali()
    log(f"boy sayisi {len(G.SIZES)} | gruplar {G.GROUP_ORDER}")
    F = G.Fonts(a.fonts)
    ciftler = [l.strip().upper() for l in pathlib.Path(a.pairs_file).read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.startswith("#")]
    ciftler = sorted(dict.fromkeys(ciftler))
    benim = [p for i, p in enumerate(ciftler) if i % a.shards == a.shard]
    durum_yol = pathlib.Path(a.state)
    durum = {}
    if durum_yol.exists():
        for r in csv.DictReader(durum_yol.open(encoding="utf-8")):
            durum[r["pair"]] = r
    todo = [p for p in benim if a.force or durum.get(p, {}).get("status") != "PASS"]
    log(f"shard {a.shard}/{a.shards}: {len(benim)} cift, {len(todo)} islenecek")
    csv_yol = pathlib.Path(a.csv or (durum_yol.parent / f"SIZE_GUIDE_15_shard{a.shard}.csv"))
    if not csv_yol.exists():
        with csv_yol.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_SUT)

    t0 = time.time()
    for i, cift in enumerate(todo, start=1):
        tp = time.time()
        hatalar, satirlar, n = [], [], 0
        pair_txt = " • ".join(cift.split("_"))
        for ed in G.EDITIONS:
            kaynak = pathlib.Path(a.src) / ed / cift
            if a.rclone_src:
                kaynak.mkdir(parents=True, exist_ok=True)
                rclone("copy", f"{a.rclone_src}/{ed}/{cift}", str(kaynak),
                       "--include", "{05,10}_WA_*", "--transfers", "4", "-q", sert=False)
            try:
                pal = G.palette(G.find_src(kaynak, "10"))
                c05 = Image.open(G.find_src(kaynak, "05")).convert("RGB")
            except (FileNotFoundError, OSError) as e:
                hatalar.append(f"{ed}: kaynak {type(e).__name__}")
                continue
            x, y, w, h = G.POSTER_BOX
            poster = c05.crop((x, y, x + w, y + h))
            cikti = pathlib.Path(a.out) / cift / ed / f"08_SIZES_{cift}_{ed}.jpg"
            cikti.parent.mkdir(parents=True, exist_ok=True)
            kart, kayit = card_sizes_v2(pal, F, poster, pair_txt)
            G.save_jpg(kart, cikti, 95)
            errs, p_sapma, b_sapma, yayilim = qc(cikti, pal, F)
            errs = errs + qc_v2(kayit)
            if ed == "MIDNIGHT_BLUE" and not satirlar:
                log(f"  yerlesim: olcek {kayit['olcek']} | G {kayit['bosluk']} px | "
                    f"rx {kayit['rx']} | kutular {kayit['kutu_plan']}")
            satirlar.append({"pair": cift, "edition": ed, "bosluk_yayilim": yayilim,
                             "metin_bosluk": kayit.get("metin_bosluk"),
                             "dosya": str(cikti.relative_to(a.out)),
                             "boyut": "x".join(map(str, Image.open(cikti).size)),
                             "palet_sapma": p_sapma, "bosluk_sapma": b_sapma,
                             "durum": "PASS" if not errs else "FAIL", "neden": "; ".join(errs)[:160]})
            if errs:
                hatalar.append(f"{ed}: " + "; ".join(errs))
            if a.ornek_cift and cift == a.ornek_cift.upper() and ed == "MIDNIGHT_BLUE":
                ornek = pathlib.Path(a.out) / "SIZE_GUIDE_15_ORNEK_v2.jpg"
                im = Image.open(cikti).convert("RGB")
                for genislik, kal in ((2200, 86), (2000, 84), (1800, 80), (1600, 78), (1400, 74)):
                    im.resize((genislik, round(genislik * im.size[1] / im.size[0])),
                              Image.LANCZOS).save(ornek, "JPEG", quality=kal, optimize=True)
                    if ornek.stat().st_size <= 300_000:
                        break
                rclone("copyto", str(ornek), f"{a.ornek_drv}/SIZE_GUIDE_15_ORNEK_v2.jpg")
                log(f"SIZE_GUIDE_15_ORNEK_v2.jpg {ornek.stat().st_size / 1024:.0f} KB "
                    f"{im.size[0]}x{im.size[1]} -> {genislik}px")
            if a.rclone_out:
                rclone("copyto", str(cikti), f"{a.rclone_out}/{cift}/{ed}/{cikti.name}")
                cikti.unlink(missing_ok=True)
            if a.rclone_src:
                subprocess.run(["rm", "-rf", str(kaynak)], check=False)
            n += 1
        with csv_yol.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_SUT, extrasaction="ignore")
            for s in satirlar:
                w.writerow(s)
        ok = n == len(G.EDITIONS) and not hatalar
        durum[cift] = {"pair": cift, "status": "PASS" if ok else "FAIL", "cards": n,
                       "fail": "; ".join(hatalar)[:300], "secs": round(time.time() - tp, 1),
                       "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with durum_yol.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=DURUM_SUT)
            w.writeheader()
            for k in sorted(durum):
                w.writerow({c: durum[k].get(c, "") for c in DURUM_SUT})
        gec = time.time() - t0
        log(f"{i}/{len(todo)} (%{100 * i / len(todo):.1f}) {cift} {'PASS' if ok else 'FAIL'} "
            f"{n}/5 kart {('; '.join(hatalar))[:60]} | gecen {sure(gec)} "
            f"| kalan ~{sure(gec / i * (len(todo) - i))}")
    if a.rclone_out:
        rclone("copyto", str(csv_yol), f"gdrive:ASTROLOVE/TEMP/POD_SIZE_GUIDE_15/parca/{csv_yol.name}")
    print(json.dumps({"shard": a.shard,
                      "pass": sum(1 for p in todo if durum.get(p, {}).get("status") == "PASS"),
                      "fail": sum(1 for p in todo if durum.get(p, {}).get("status") == "FAIL")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
