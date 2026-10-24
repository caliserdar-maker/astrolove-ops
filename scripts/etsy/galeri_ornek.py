#!/usr/bin/env python3
"""23 eski galerili poster ilani, sira 8 galeri isi (Serdar 23 Eki B; PLAN ve ORNEK, Etsy'ye yazma YOK, Etsy API YOK).
Girdi (Drive'dan indirilmis): --hedef-manifest (GALERI_YAYIN/KOSU_20261021_1030/<lid>/yedek/manifest.json: 17 Eki galerisi, 21 Eki
yaziminden ONCE alinan yedek; 55 yeni galerili ilanla ayni duzen), --hedef-dir (GALERI_YAYIN/YEDEK/<lid>_<CIFT>/NN_<id>.jpg),
--simdi (KART_SIL/<kosu>/SONRA_<lid>.json: canli galeri; gorseller CDN'den indirilir, kota harcamaz).
Esleme: her canli gorsel her hedef gorselle 768 px gri NCC ile kiyaslanir; NCC >= 0.999 aday (eski78_gorsel_yukle ve GERI_YUKLE ile
ayni esik). Aday ayni gorsel sayilmak icin piksel fark kapisindan da gecer: hedef boyutunda RGB mutlak fark (kanal max) p99.9 <= 12 ve
max <= 45 (eski78_gorsel_uret onayli JPEG yeniden kodlama esigi). 23 Eki ARIES_VIRGO: NCC 0.9998 / 0.9992 olan iki kart kucuk yazida
farkliydi ("Frame not included", "four frame finishes"); NCC tek basina cerceveli / cercevesiz karti ayiramaz. Islem: KORU (ayni gorsel, ayni alt metin) | ALT (ayni gorsel, alt metin degisir) | DEGISTIR (canli gorsel
cikar, hedef yuklenir) | CIKAR (hedefte karsiligi yok).
Cikti: LISTE_<lid>.csv + .md, HEDEF_GALERI_<lid>.jpg (17 gorsel sirayla, gercek 4:3 oran, sira + alt metin), YAN_YANA_<lid>.jpg
(her sira: simdi | hedef), DEGISEN/ (degisen her hedef gorsel %100, dosya oldugu gibi)."""
import argparse
import csv
import io
import json
import pathlib
import shutil
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ESIK = 0.999
FARK_P999, FARK_MAX = 12, 45


def font(n):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, n)
        except OSError:
            pass
    return ImageFont.load_default()


def gri(im, w=768):
    g = im.convert("L").resize((w, round(im.height * w / im.width)), Image.BILINEAR)
    a = np.asarray(g, np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def ncc(a, b):
    if a.shape != b.shape:
        h = min(a.shape[0], b.shape[0]); a, b = a[:h], b[:h]
    return float((a * b).mean())


def fark(a, b):
    """a'yi b boyutuna getirip RGB mutlak fark (kanal max): (p99.9, max)."""
    if a.size != b.size:
        a = a.resize(b.size, Image.LANCZOS)
    d = np.abs(np.asarray(a, np.int16) - np.asarray(b, np.int16)).max(2)
    return round(float(np.percentile(d, 99.9)), 1), int(d.max())


def indir(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def satir_yaz(d, xy, metin, f, w):
    """metni w genislige sigacak sekilde satirlara bol."""
    x, y = xy; sat = ""
    for k in metin.split():
        t = (sat + " " + k).strip()
        if d.textlength(t, font=f) > w and sat:
            d.text((x, y), sat, fill=(30, 30, 30), font=f); y += f.size + 4; sat = k
        else:
            sat = t
    if sat:
        d.text((x, y), sat, fill=(30, 30, 30), font=f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hedef-manifest", required=True)
    ap.add_argument("--hedef-dir", required=True)
    ap.add_argument("--simdi", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); (out / "DEGISEN").mkdir(parents=True, exist_ok=True)
    man = json.loads(pathlib.Path(a.hedef_manifest).read_text(encoding="utf-8"))
    lid = str(man["listing_id"])
    hd = pathlib.Path(a.hedef_dir)
    hedef = []
    for g in sorted(man["galeri"], key=lambda x: int(x["rank"])):
        p = hd / f"{int(g['rank']):02d}_{g['listing_image_id']}.jpg"
        if not p.exists():
            raise SystemExit(f"DUR: hedef dosya yok {p.name}")
        hedef.append(dict(rank=int(g["rank"]), id=g["listing_image_id"], alt=g.get("alt_text") or "", yol=p, im=Image.open(p).convert("RGB")))
    s = json.loads(pathlib.Path(a.simdi).read_text(encoding="utf-8"))
    simdi = [dict(rank=int(x["rank"]), id=x["listing_image_id"], alt=x.get("alt_text") or "", url=x["url_fullxfull"])
             for x in sorted(s["gorseller"], key=lambda x: (int(x["rank"]), int(x["listing_image_id"])))]
    for x in simdi:
        x["im"] = indir(x["url"])
    hg = [gri(h["im"]) for h in hedef]
    for x in simdi:
        sg = gri(x["im"]); n = [ncc(sg, h) for h in hg]
        j = int(np.argmax(n)); x["en_yakin"], x["ncc"] = j, round(n[j], 5)
        x["fark"] = fark(x["im"], hedef[j]["im"]) if n[j] >= ESIK else None
        x["ayni"] = bool(x["fark"]) and x["fark"][0] <= FARK_P999 and x["fark"][1] <= FARK_MAX
    kullanildi = {}
    for x in sorted(simdi, key=lambda x: -x["ncc"]):          # her hedef en fazla bir canli gorselle eslesir
        if x["ayni"] and x["en_yakin"] not in kullanildi:
            kullanildi[x["en_yakin"]] = x
    satir = []
    for j, h in enumerate(hedef):
        c = kullanildi.get(j)
        if c:
            islem = "KORU" if c["alt"] == h["alt"] else "ALT"
        else:
            islem = "DEGISTIR"
            shutil.copy(h["yol"], out / "DEGISEN" / h["yol"].name)
        satir.append(dict(hedef_sira=h["rank"], hedef_gorsel=h["yol"].name, hedef_alt=h["alt"], islem=islem,
                          simdi_sira=c["rank"] if c else "", simdi_id=c["id"] if c else "", simdi_alt=c["alt"] if c else "",
                          ncc=c["ncc"] if c else "", fark="%s/%s" % c["fark"] if c else ""))
    eslesen = {id(x) for x in kullanildi.values()}
    for x in simdi:
        if id(x) not in eslesen:
            satir.append(dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira=x["rank"], simdi_id=x["id"],
                              simdi_alt=x["alt"], ncc=x["ncc"], fark="%s/%s" % x["fark"] if x["fark"] else "",
                              en_yakin_hedef=hedef[x["en_yakin"]]["rank"]))
    alan = ["hedef_sira", "hedef_gorsel", "hedef_alt", "islem", "simdi_sira", "simdi_id", "simdi_alt", "ncc", "fark", "en_yakin_hedef"]
    with open(out / f"LISTE_{lid}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, restval=""); w.writeheader(); w.writerows(satir)
    md = [f"# {lid} galeri plani (simdi {len(simdi)} gorsel -> hedef {len(hedef)})", "",
          "| hedef sira | hedef gorsel | hedef alt metin | islem | simdi sira | simdi id | simdi alt metin | NCC | fark p99.9/max |",
          "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['hedef_sira']} | {r['hedef_gorsel']} | {r['hedef_alt']} | {r['islem']} | {r['simdi_sira']} | {r['simdi_id']} | "
           f"{r['simdi_alt']} | {r['ncc']} | {r['fark']} |" for r in satir]
    sayim = {k: sum(r["islem"] == k for r in satir) for k in ("KORU", "ALT", "DEGISTIR", "CIKAR")}
    md += ["", f"Sayim: {sayim}. Ayni gorsel: NCC >= {ESIK} (768 px gri) ve fark p99.9 <= {FARK_P999}, max <= {FARK_MAX}. Renk baglari hedef: "
           + ", ".join(f"{v['value']} -> {v['image_id']}" for v in man.get("variation_images", []))]
    (out / f"LISTE_{lid}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    # hedef galeri: Etsy sirasi, gercek oran (4:3), 4 sutun
    tw = 720; f = font(22); fb = font(30)
    th = round(tw * hedef[0]["im"].height / hedef[0]["im"].width)
    kol, pad, yazi = 4, 24, 110
    sat = -(-len(hedef) // kol)
    S = Image.new("RGB", (kol * (tw + pad) + pad, 90 + sat * (th + yazi + pad)), "white"); d = ImageDraw.Draw(S)
    d.text((pad, 24), f"HEDEF GALERI {lid} (17 gorsel, Etsy sirasi; gorseller 4:3 gercek oran)", fill=(0, 0, 0), font=fb)
    for i, h in enumerate(hedef):
        x = pad + (i % kol) * (tw + pad); y = 90 + (i // kol) * (th + yazi + pad)
        S.paste(h["im"].resize((tw, th), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(180, 180, 180))
        satir_yaz(d, (x, y + th + 6), f"{h['rank']}. [{satir[i]['islem']}] {h['alt']}", f, tw)
    S.save(out / f"HEDEF_GALERI_{lid}.jpg", quality=92)
    # yan yana: her hedef sira icin YALNIZ eslesen canli gorsel | hedef (24 Eki: ayni siradaki eslesmeyen canli gorsel cizilmez;
    # 23 Eki sayfasi canli rank 17'yi hedef 17'nin yanina koyup "CI iki kez" yanilgisi yaratmisti)
    tw2 = 520; th2 = round(tw2 * 3 / 4); n = len(hedef)
    Y = Image.new("RGB", (2 * tw2 + 3 * pad + 360, 70 + n * (th2 + pad)), "white"); d = ImageDraw.Draw(Y)
    d.text((pad, 20), f"{lid}: SIMDI (canli, yalniz eslesen) | HEDEF", fill=(0, 0, 0), font=fb)
    for i, h in enumerate(hedef):
        y = 70 + i * (th2 + pad)
        c = kullanildi.get(i)
        if c:
            Y.paste(c["im"].resize((tw2, th2), Image.LANCZOS), (pad, y))
        else:   # bu hedefe en yakin CIKAR canli gorsel (eski surum) varsa o gosterilir, yoksa bos
            eski = max((x for x in simdi if x["en_yakin"] == i and id(x) not in eslesen and x["ncc"] >= 0.9),
                       key=lambda x: x["ncc"], default=None)
            if eski:
                Y.paste(eski["im"].resize((tw2, th2), Image.LANCZOS), (pad, y))
                d.rectangle([pad, y, pad + tw2, y + 34], fill=(255, 255, 255))
                satir_yaz(d, (pad + 6, y + 4), f"canli eski surum r{eski['rank']} (NCC {eski['ncc']}, CIKAR)", f, tw2 - 12)
            else:
                d.rectangle([pad, y, pad + tw2, y + th2], fill=(235, 235, 235))
                satir_yaz(d, (pad + 20, y + th2 // 2 - 20), "canlida karsiligi yok (yeni yuklenir)", f, tw2 - 40)
        Y.paste(h["im"].resize((tw2, th2), Image.LANCZOS), (2 * pad + tw2, y))
        satir_yaz(d, (3 * pad + 2 * tw2, y + 10), f"{h['rank']}. {satir[i]['islem']}", fb, 340)
    Y.save(out / f"YAN_YANA_{lid}.jpg", quality=88)
    print("GALERI_ORNEK", json.dumps(dict(ilan=lid, simdi=len(simdi), hedef=len(hedef), sayim=sayim), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
