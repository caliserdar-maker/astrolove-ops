#!/usr/bin/env python3
"""1st Anniversary (YD) ilan aciklamalari: mevcut metin + 78 ilan arasindaki farklar (Serdar 31 Eki karar 5c). ETSY API YOK.
Girdi: Etsy okuma yedegi klasoru (<listing_id>.json; {"listing": {...description...}}), ornek: TEMP/YD_ENVANTER_20261026/HAM.
Yontem: her aciklama html.unescape; burc adlari (cift A / B) yer tutucuyla (<A>, <B>) degistirilir; sonra paragraf paragraf sablon
kumelemesi. Ayni sablona dusen ilanlar ayni metni tasir; farkli paragraflar FARK.csv'de.
Cikti --out: <REF>.txt (referans ilanin tam metni, varsayilan CANCER_LIBRA), SABLON.csv (sablon no, ilan sayisi, ciftler),
FARK.csv (listing_id, cift, paragraf no, referans paragraf, bu ilanin paragrafi), PARAGRAF.csv (paragraf, varyant sayisi), OZET.md.
Metin DEGISTIRILMEZ (yeni metni Merkez hazirlar, Serdar onaylar)."""
import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BURCLAR = ["Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo", "Libra", "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo"]


def norm(t, a, b):
    t = html.unescape(t or "").replace("\r\n", "\n")
    if a == b:
        return re.sub(rf"\b{a}\b", "<A>", t)
    t = re.sub(rf"\b{a}\b", "<A>", t)
    return re.sub(rf"\b{b}\b", "<B>", t)


def paragraflar(t):
    return [p.strip() for p in t.split("\n\n") if p.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", required=True)
    ap.add_argument("--ciftler", default=str(Path(__file__).resolve().parents[2] / "data/pod/yd78_ids.csv"))
    ap.add_argument("--ref", default="CANCER_LIBRA")
    ap.add_argument("--kaynak", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ham, out = Path(a.ham), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cif, lid_cift = {}, {}
    for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")):
        cif[r["cift"]] = (r["a"], r["b"]); lid_cift[str(r["listing_id"]).strip()] = r["cift"]
    ilan = {}
    for p in sorted(ham.glob("*.json")):
        L = json.loads(p.read_text(encoding="utf-8")).get("listing") or {}
        if not L.get("listing_id"):
            continue
        t = L.get("title") or ""
        c = lid_cift.get(str(L["listing_id"]))      # data/pod/yd78_ids.csv listing_id -> cift
        ilan[str(L["listing_id"])] = dict(cift=c, title=t, ham=html.unescape(L.get("description") or ""), state=L.get("state"),
                                         n=norm(L.get("description"), *(cif[c] if c else ("", ""))))
    ref = next((k for k, v in ilan.items() if v["cift"] == a.ref), None)
    if not ref:
        raise SystemExit(f"DUR: referans {a.ref} yedekte yok")
    (out / f"{a.ref}.txt").write_text(ilan[ref]["ham"] + "\n", encoding="utf-8")
    sablon = defaultdict(list)
    for k, v in ilan.items():
        sablon[v["n"]].append(v["cift"] or k)
    sira = sorted(sablon.items(), key=lambda x: -len(x[1]))
    with open(out / "SABLON.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["sablon", "ilan", "ciftler", "referans_mi"])
        for i, (n, cs) in enumerate(sira, 1):
            w.writerow([i, len(cs), " ".join(sorted(cs)), "evet" if n == ilan[ref]["n"] else ""])
    rp = paragraflar(ilan[ref]["n"])
    fark, varyant = [], defaultdict(Counter)
    for k, v in sorted(ilan.items(), key=lambda x: x[1]["cift"] or ""):
        pp = paragraflar(v["n"])
        for i in range(max(len(rp), len(pp))):
            x, y = (rp[i] if i < len(rp) else ""), (pp[i] if i < len(pp) else "")
            varyant[i + 1][y] += 1
            if x != y:
                fark.append([k, v["cift"], i + 1, x, y])
    with open(out / "FARK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "paragraf", "referans", "bu_ilan"]); w.writerows(fark)
    with open(out / "PARAGRAF.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["paragraf", "varyant", "ilan_sayilari", "referans_bas"])
        for i in sorted(varyant):
            w.writerow([i, len(varyant[i]), " ".join(str(n) for _, n in varyant[i].most_common()), (rp[i - 1] if i <= len(rp) else "")[:80]])
    eski = Counter()
    for v in ilan.values():
        for s in ("Digital card 5x7", "Digital file 8x10", "Shipped print 8x10", "8x10", "5x7", "AstroLove "):
            if s in v["ham"]:
                eski[s] += 1
    bilinmeyen = [k for k, v in ilan.items() if not v["cift"]]
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# 1st Anniversary aciklama: mevcut metin ve farklar\n\nkaynak: {a.kaynak or a.ham} (Etsy okuma yedegi; Etsy istegi yok)\n"
                f"ilan {len(ilan)} | cift eslesmeyen {len(bilinmeyen)} {bilinmeyen[:5]} | referans {a.ref} ({ref})\n"
                f"sablon (burc adlari yer tutucuyla): {len(sira)} farkli metin; en buyuk sablon {len(sira[0][1])} ilan\n"
                f"farkli paragraf satiri (referansa gore): {len(fark)}\n\n## Paragraf varyantlari (referans paragraf no)\n\n"
                "| paragraf | varyant | ilan sayilari | referans basi |\n|---|---|---|---|\n")
        for i in sorted(varyant):
            f.write(f"| {i} | {len(varyant[i])} | {' '.join(str(n) for _, n in varyant[i].most_common())} | "
                    f"{(rp[i - 1] if i <= len(rp) else '')[:60]} |\n")
        f.write("\n## Eski format / boy ifadeleri (ilan sayisi; yeni yapiyla celisir)\n\n" + "".join(f"- {s}: {n}\n" for s, n in eski.items()))
        f.write("\nMetin degistirilmedi. Yeni yapiya uygun metni Merkez hazirlar, Serdar onaylar.\n")
    print(f"YD ACIKLAMA: ilan {len(ilan)} sablon {len(sira)} fark satiri {len(fark)} eslesmeyen {len(bilinmeyen)}")
    return 0 if len(ilan) == 78 and not bilinmeyen else 1


if __name__ == "__main__":
    sys.exit(main())
