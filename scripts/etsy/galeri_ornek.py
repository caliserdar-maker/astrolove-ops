#!/usr/bin/env python3
"""23 eski galerili poster ilani, sira 8 galeri isi (Serdar 23 Eki B; PLAN ve ORNEK, Etsy'ye yazma YOK, Etsy API YOK).
Girdi (Drive'dan indirilmis): --hedef-manifest (GALERI_YAYIN/KOSU_20261021_1030/<lid>/yedek/manifest.json: 17 Eki galerisi, 21 Eki
yaziminden ONCE alinan yedek; 55 yeni galerili ilanla ayni duzen), --hedef-dir (GALERI_YAYIN/YEDEK/<lid>_<CIFT>/NN_<id>.jpg),
--simdi (KART_SIL/<kosu>/SONRA_<lid>.json: canli galeri; gorseller CDN'den indirilir, kota harcamaz).
Esleme: her canli gorsel her hedef gorselle 768 px gri NCC ile kiyaslanir; NCC >= 0.999 ayni gorsel sayilir (eski78_gorsel_yukle ve
GERI_YUKLE ile ayni esik). Islem: KORU (ayni gorsel, ayni alt metin) | ALT (ayni gorsel, alt metin degisir) | DEGISTIR (canli gorsel
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
    kullanildi = {}
    for x in sorted(simdi, key=lambda x: -x["ncc"]):          # her hedef en fazla bir canli gorselle eslesir
        if x["ncc"] >= ESIK and x["en_yakin"] not in kullanildi:
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
                          ncc=c["ncc"] if c else ""))
    eslesen = {id(x) for x in kullanildi.values()}
    for x in simdi:
        if id(x) not in eslesen:
            satir.append(dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira=x["rank"], simdi_id=x["id"],
                              simdi_alt=x["alt"], ncc=x["ncc"]))
    alan = ["hedef_sira", "hedef_gorsel", "hedef_alt", "islem", "simdi_sira", "simdi_id", "simdi_alt", "ncc"]
    with open(out / f"LISTE_{lid}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(satir)
    md = [f"# {lid} galeri plani (simdi {len(simdi)} gorsel -> hedef {len(hedef)})", "",
          "| hedef sira | hedef gorsel | hedef alt metin | islem | simdi sira | simdi id | simdi alt metin | NCC |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['hedef_sira']} | {r['hedef_gorsel']} | {r['hedef_alt']} | {r['islem']} | {r['simdi_sira']} | {r['simdi_id']} | "
           f"{r['simdi_alt']} | {r['ncc']} |" for r in satir]
    sayim = {k: sum(r["islem"] == k for r in satir) for k in ("KORU", "ALT", "DEGISTIR", "CIKAR")}
    md += ["", f"Sayim: {sayim}. Esik NCC >= {ESIK} (768 px gri). Renk baglari hedef: "
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
    # yan yana: her hedef sira icin simdi (eslesen ya da ayni siradaki) | hedef
    tw2 = 520; th2 = round(tw2 * 3 / 4); n = len(hedef)
    Y = Image.new("RGB", (2 * tw2 + 3 * pad + 360, 70 + n * (th2 + pad)), "white"); d = ImageDraw.Draw(Y)
    d.text((pad, 20), f"{lid}: SIMDI (canli) | HEDEF", fill=(0, 0, 0), font=fb)
    sira = {x["rank"]: x for x in simdi}
    for i, h in enumerate(hedef):
        y = 70 + i * (th2 + pad)
        c = kullanildi.get(i) or sira.get(h["rank"])
        if c:
            Y.paste(c["im"].resize((tw2, th2), Image.LANCZOS), (pad, y))
        Y.paste(h["im"].resize((tw2, th2), Image.LANCZOS), (2 * pad + tw2, y))
        satir_yaz(d, (3 * pad + 2 * tw2, y + 10), f"{h['rank']}. {satir[i]['islem']}", fb, 340)
    Y.save(out / f"YAN_YANA_{lid}.jpg", quality=88)
    print("GALERI_ORNEK", json.dumps(dict(ilan=lid, simdi=len(simdi), hedef=len(hedef), sayim=sayim), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
