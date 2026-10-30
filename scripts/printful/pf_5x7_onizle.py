#!/usr/bin/env python3
"""Printful 5x7 (varyant 16364) baski dosyasi ornegi + gercek oranda onizleme (Merkez 30 Eki B4; Etsy yok, Printful'a istek yok).
Girdi: siparis hattinin 5x7 ciktilari (AstroLoveArt_<B1>_<B2>_<Renk>_5x7.jpg, test fisleri, ornek isimler) ve Printful
/mockup-generator/printfiles yaniti (pf_5x7_oku.py ciktisi; printfile olcusu koddan degil bu JSON'dan okunur).
Her dosya icin Printful "cover" yerlesimi uygulanir: olcek = max(pw/w, ph/h), tasan kisim ortadan kirpilir. Kaynak printfile ile
ayni boyuttaysa baski dosyasi bayt bayt kopyadir (sha256 esit). Onizleme 5:7 gercek oranda: kirpilan bolge kirmizi, kesim cizgisi
kirmizi, 1/8 in referans cizgisi sari (Printful kesim toleransi API'de yok: dogrulanmadi). Icerik kenar payi: koselerden alinan zemin
rengine gore satir/sutun profili (fark > 40 olan piksel orani > %1).
PASS: kaynak >= printfile (buyutme yok) ve her eksende kirpma <= %1 ve JPEG RGB.
--fisler verilirse her receipt klasorunde (<yol>_<receipt>) en az 1 dosya sart (Printful'a yukleme oncesi kapi, Serdar 30 Eki).
Isimler yalniz ORNEK.csv ve onizleme gorselinde (Drive); ORNEK.md ve stdout'a yazilmaz (is akisi ozeti / log).
Cikti <out>/: BASKI/<ad>.jpg, ONIZLEME/<ad>_ONIZLEME.jpg, KONTAK.jpg, ORNEK.csv, ORNEK.md."""
import argparse, csv, hashlib, json, re, shutil, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KIRP_MAX = 0.01          # eksen basina en fazla kirpma orani
ZEMIN_FARK, PROFIL = 40, 0.01
REF_IN = 0.125           # referans cizgisi (Printful degeri degil)
OLCEK = 0.5              # onizleme olcegi (1500x2100 -> 750x1050)
AD = re.compile(r"AstroLoveArt_(?P<cift>[A-Za-z]+_[A-Za-z]+)_(?P<renk>[A-Za-z_]+?)_5x7\.jpg$")


def printfile(js, varyant):
    r = js.get("result") or {}
    pf = {x.get("printfile_id"): x for x in r.get("printfiles") or []}
    for e in r.get("variant_printfiles") or []:
        if e.get("variant_id") == varyant:
            return pf[(e.get("placements") or {})["default"]]
    raise SystemExit(f"varyant {varyant} printfile yok")


def font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def kenar_payi(a):
    k = 20
    kose = np.concatenate([a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3), a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    zemin = np.median(kose, axis=0)
    m = np.abs(a.astype(np.int16) - zemin.astype(np.int16)).max(axis=2) > ZEMIN_FARK
    sat, sut = np.where(m.mean(axis=1) > PROFIL)[0], np.where(m.mean(axis=0) > PROFIL)[0]
    if not len(sat) or not len(sut):
        return None, zemin
    h, w = m.shape
    return {"ust": int(sat[0]), "alt": int(h - 1 - sat[-1]), "sol": int(sut[0]), "sag": int(w - 1 - sut[-1])}, zemin


def isimler(d):
    bul = {}
    for j in sorted(d.glob("*.json")):
        try:
            v = json.loads(j.read_text(encoding="utf-8"))
        except Exception:
            continue
        yigin = [v]
        while yigin:
            x = yigin.pop()
            if isinstance(x, dict):
                for a, b in x.items():
                    if re.fullmatch(r"isim[12]?|ad[12]|name[12]?", str(a)) and isinstance(b, str):
                        bul.setdefault(a, b)
                    else:
                        yigin.append(b)
            elif isinstance(x, list):
                yigin.extend(x)
    return " / ".join(f"{a}={b}" for a, b in sorted(bul.items())) or "-"


def isle(p, pf, out, dpi):
    im = Image.open(p); fmt, mod = im.format, im.mode; w, h = im.size
    pw, ph = pf["width"], pf["height"]
    if pf.get("can_rotate") and (w > h) != (pw > ph):
        pw, ph = ph, pw
    s = max(pw / w, ph / h); sw, sh = round(w * s), round(h * s)
    kx, ky = sw - pw, sh - ph
    baski = out / "BASKI" / p.name
    if (w, h) == (pw, ph):
        shutil.copyfile(p, baski)
    else:
        r = im.convert("RGB").resize((sw, sh), Image.LANCZOS).crop((kx // 2, ky // 2, kx // 2 + pw, ky // 2 + ph))
        r.save(baski, "JPEG", quality=95, dpi=(dpi, dpi), icc_profile=im.info.get("icc_profile"))
    b = Image.open(baski); a = np.asarray(b.convert("RGB"))
    pay, zemin = kenar_payi(a)
    sha_k, sha_b = (hashlib.sha256(x.read_bytes()).hexdigest() for x in (p, baski))
    kirp_x, kirp_y = kx / sw, ky / sh
    pas = fmt == "JPEG" and mod == "RGB" and w >= pw and h >= ph and kirp_x <= KIRP_MAX and kirp_y <= KIRP_MAX
    m = AD.search(p.name)
    satir = {"dosya": p.name, "renk": m["renk"] if m else "?", "kaynak_px": f"{w}x{h}", "kaynak_mod": f"{fmt} {mod}",
             "kaynak_dpi": str(im.info.get("dpi", "-")), "icc": "var" if im.info.get("icc_profile") else "yok",
             "printfile_px": f"{pw}x{ph}", "olcek": round(s, 5), "kirp_x_px": kx, "kirp_y_px": ky,
             "kirp_x_yuzde": round(100 * kirp_x, 3), "kirp_y_yuzde": round(100 * kirp_y, 3),
             "baski_ayni_bayt": sha_k == sha_b, "baski_bayt": baski.stat().st_size, "baski_dpi": str(b.info.get("dpi", "-")),
             "zemin_rgb": ",".join(str(int(v)) for v in zemin), "isimler": isimler(p.parent),
             "sonuc": "PASS" if pas else "FAIL"}
    for k in ("ust", "alt", "sol", "sag"):
        satir[f"pay_{k}_in"] = round(pay[k] / dpi, 3) if pay else "-"
    satir["onizleme"] = onizle(im.convert("RGB"), (sw, sh), (kx, ky), (pw, ph), pay, satir, out, dpi)
    return satir


def onizle(im, sk, kk, pp, pay, s, out, dpi):
    (sw, sh), (kx, ky), (pw, ph) = sk, kk, pp
    o = OLCEK; kn = 40; alt = 250
    W, H = round(sw * o) + 2 * kn, round(sh * o) + 2 * kn + alt
    c = Image.new("RGB", (W, H), (128, 128, 128))
    c.paste(im.resize((round(sw * o), round(sh * o)), Image.LANCZOS), (kn, kn))
    d = ImageDraw.Draw(c, "RGBA")
    x0, y0 = kn + round(kx // 2 * o), kn + round(ky // 2 * o); x1, y1 = x0 + round(pw * o), y0 + round(ph * o)
    for r in ((kn, kn, kn + round(sw * o), y0), (kn, y1, kn + round(sw * o), kn + round(sh * o)),
              (kn, y0, x0, y1), (x1, y0, kn + round(sw * o), y1)):
        if r[2] > r[0] and r[3] > r[1]:
            d.rectangle(r, fill=(255, 0, 0, 110))
    d.rectangle((x0 - 1, y0 - 1, x1, y1), outline=(230, 20, 20), width=2)
    g = round(REF_IN * dpi * o)
    for i in range(x0 + g, x1 - g, 14):
        d.line((i, y0 + g, min(i + 7, x1 - g), y0 + g), fill=(255, 210, 0), width=1)
        d.line((i, y1 - g, min(i + 7, x1 - g), y1 - g), fill=(255, 210, 0), width=1)
    for j in range(y0 + g, y1 - g, 14):
        d.line((x0 + g, j, x0 + g, min(j + 7, y1 - g)), fill=(255, 210, 0), width=1)
        d.line((x1 - g, j, x1 - g, min(j + 7, y1 - g)), fill=(255, 210, 0), width=1)
    f, fb = font(15), font(19)
    y = kn + round(sh * o) + 14
    d.text((kn, y), f"{s['renk']}  |  Printful 5x7 (16364) printfile {s['printfile_px']} @ {dpi} dpi  |  {s['sonuc']}", fill=(0, 0, 0), font=fb)
    satirlar = [
        f"kaynak {s['kaynak_px']} {s['kaynak_mod']}, dpi {s['kaynak_dpi']}, ICC {s['icc']}  ->  olcek {s['olcek']}",
        f"cover kirpma: yatay {s['kirp_x_px']} px ({s['kirp_x_yuzde']}%), dikey {s['kirp_y_px']} px ({s['kirp_y_yuzde']}%)  [kirmizi alan]",
        f"icerik kenar payi (in): ust {s['pay_ust_in']}  alt {s['pay_alt_in']}  sol {s['pay_sol_in']}  sag {s['pay_sag_in']}",
        "kirmizi = baski kenari 5x7 in | sari = 1/8 in referans (Printful toleransi dogrulanmadi)",
        f"baski dosyasi {s['baski_bayt'] / 1e6:.2f} MB, kaynakla ayni bayt: {s['baski_ayni_bayt']}",
        f"isimler: {s['isimler']}"]
    for t in satirlar:
        y += 27; d.text((kn, y), t, fill=(0, 0, 0), font=f)
    p = out / "ONIZLEME" / (Path(s["dosya"]).stem + "_ONIZLEME.jpg")
    c.save(p, "JPEG", quality=90)
    return p.name


def kontak(out, adlar):
    ims = [Image.open(out / "ONIZLEME" / a) for a in adlar]
    if not ims:
        return
    o = 0.6; ims = [i.resize((round(i.width * o), round(i.height * o)), Image.LANCZOS) for i in ims]
    k = Image.new("RGB", (sum(i.width for i in ims) + 10 * (len(ims) + 1), max(i.height for i in ims) + 20), (255, 255, 255))
    x = 10
    for i in ims:
        k.paste(i, (x, 10)); x += i.width + 10
    k.save(out / "KONTAK.jpg", "JPEG", quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--printfiles", required=True); ap.add_argument("--varyant", type=int, default=16364)
    ap.add_argument("--in", dest="giris", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--beklenen", type=int, default=5)
    ap.add_argument("--fisler", default="", help="virgullu receipt; her biri icin en az 1 dosya (klasor adi _<receipt> ile biter)")
    a = ap.parse_args()
    pf = printfile(json.loads(Path(a.printfiles).read_text()), a.varyant)
    dpi = int(pf["dpi"])
    out = Path(a.out); (out / "BASKI").mkdir(parents=True, exist_ok=True); (out / "ONIZLEME").mkdir(exist_ok=True)
    dosyalar = sorted(p for p in Path(a.giris).rglob("AstroLoveArt_*_5x7.jpg"))
    rows = [isle(p, pf, out, dpi) for p in dosyalar]
    kontak(out, [r["onizleme"] for r in rows])
    if rows:
        with open(out / "ORNEK.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    npas = sum(r["sonuc"] == "PASS" for r in rows)
    md = [f"# Printful 5x7 baski dosyasi ornegi (varyant {a.varyant}, printfile {pf['printfile_id']}: {pf['width']}x{pf['height']} "
          f"@ {dpi} dpi, fill_mode {pf.get('fill_mode')}, can_rotate {pf.get('can_rotate')})\n",
          f"- dosya {len(rows)} / beklenen {a.beklenen} | PASS {npas} | FAIL {len(rows) - npas}",
          f"- kapi: kaynak >= printfile, eksen basina kirpma <= {KIRP_MAX:.0%}, JPEG RGB", "",
          "| renk | kaynak | kirpma x/y (%) | pay ust/alt/sol/sag (in) | MB | ayni bayt | isim alani | sonuc |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['renk']} | {r['kaynak_px']} | {r['kirp_x_yuzde']} / {r['kirp_y_yuzde']} | {r['pay_ust_in']} / {r['pay_alt_in']} / "
                  f"{r['pay_sol_in']} / {r['pay_sag_in']} | {r['baski_bayt'] / 1e6:.2f} | {r['baski_ayni_bayt']} | {'var' if r['isimler'] != '-' else '-'} | {r['sonuc']} |")
    (out / "ORNEK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    fis = [x.strip() for x in a.fisler.split(",") if x.strip()]
    eksik = [f for f in fis if not any(p.parent.name.endswith(f"_{f}") for p in dosyalar)]
    if fis:
        md.append(f"\n- fis kapisi: {len(fis) - len(eksik)}/{len(fis)} fiste 5x7 dosyasi" + (f" | EKSIK: {eksik}" if eksik else ""))
        (out / "ORNEK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print(md[-1], flush=True)
    return 0 if rows and npas == len(rows) == a.beklenen and not eksik else 1


if __name__ == "__main__":
    sys.exit(main())
