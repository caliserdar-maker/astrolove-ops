#!/usr/bin/env python3
"""Galeri ONCE / SONRA karsilastirmasi (78 poster; envanter + aciklama toplu yazimi galeriye dokundu mu?). ETSY API YOK.
Girdi: iki galeri-v11-yedek-oku ciktisi (Drive TEMP/POSTER_GALERI_V11_YEDEK/<damga>/<lid>_<CIFT>/GALERI.json), yerel klasor.
Ilan basina karsilastirilan: rank sirasiyla gorsel kimlikleri + gorsel sayisi (kapak = rank 1), alt_text, renk baglari
(property_id, value, image_id), video kimlikleri, ilan state ve title. YOK SAYILAN: last_modified_timestamp, URL'ler
(url_fullxfull, video_url, thumbnail_url).
Cikti <out>/: KARSILASTIR.csv (listing_id, cift, durum AYNI/FARKLI/EKSIK, fark), OZET.md (sayilar).
Cikis 0 yalniz ONCE'deki her ilan SONRA'da var ve AYNI ise; 1 fark / eksik / bos ONCE; 2 ONCE okunamadi."""
import argparse
import csv
import json
import pathlib
import sys
from collections import Counter

ALANLAR = ("gorsel", "alt", "bag", "video", "state", "title", "cift")


def yukle(kok):
    """{listing_id: (veri | None, hata)}; ayni listing_id iki klasorde ise hata."""
    kok = pathlib.Path(kok)
    out, cift_hata = {}, []
    for p in sorted(kok.glob("*/GALERI.json")):
        lid_kl = p.parent.name.split("_", 1)[0]
        try:
            y = json.loads(p.read_text(encoding="utf-8"))
            lid = str(y.get("listing_id") or lid_kl).strip()
            hata = None
        except (OSError, ValueError) as e:
            y, lid, hata = None, lid_kl, f"GALERI.json okunamadi ({type(e).__name__})"
        if lid in out:
            cift_hata.append(lid)
        out[lid] = (y, hata, p.parent.name)
    return out, cift_hata


def ozellik(y):
    g = sorted(y.get("gorseller") or [], key=lambda x: (x.get("rank") is None, x.get("rank") or 0))
    return dict(
        gorsel=[(x.get("rank"), str(x.get("listing_image_id"))) for x in g],
        alt={x.get("rank"): (x.get("alt_text") or "") for x in g},
        bag=sorted((str(b.get("property_id")), str(b.get("value")), str(b.get("image_id"))) for b in (y.get("baglar") or [])),
        video=sorted(str(v.get("video_id")) for v in (y.get("videolar") or [])),
        state=(y.get("ilan") or {}).get("state"),
        title=(y.get("ilan") or {}).get("title"),
        cift=str(y.get("cift") or ""),
    )


def kisa(s, n=80):
    s = str(s)
    return s if len(s) <= n else s[: n - 3] + "..."


def karsilastir(a, b):
    """(farkli alanlar, fark metni listesi)."""
    fa, fb = ozellik(a), ozellik(b)
    alan, fark = [], []
    if fa["gorsel"] != fb["gorsel"]:
        alan.append("gorsel")
        if len(fa["gorsel"]) != len(fb["gorsel"]):
            fark.append(f"gorsel sayisi {len(fa['gorsel'])}->{len(fb['gorsel'])}")
        ra, rb = dict(fa["gorsel"]), dict(fb["gorsel"])
        for r in sorted(set(ra) | set(rb), key=lambda x: (x is None, x or 0)):
            if ra.get(r) != rb.get(r):
                fark.append(f"rank {r}{' (kapak)' if r == 1 else ''} {ra.get(r, '-')}->{rb.get(r, '-')}")
    alt_r = [r for r in sorted(set(fa["alt"]) | set(fb["alt"]), key=lambda x: (x is None, x or 0)) if fa["alt"].get(r) != fb["alt"].get(r)]
    if alt_r:
        alan.append("alt")
        fark.append("alt_text rank " + ",".join(map(str, alt_r)))
    if fa["bag"] != fb["bag"]:
        alan.append("bag")
        sa, sb = set(fa["bag"]), set(fb["bag"])
        fark.append("bag -" + ("|".join(":".join(x) for x in sorted(sa - sb)) or "yok")
                    + " +" + ("|".join(":".join(x) for x in sorted(sb - sa)) or "yok"))
    if fa["video"] != fb["video"]:
        alan.append("video")
        fark.append(f"video {','.join(fa['video']) or 'yok'}->{','.join(fb['video']) or 'yok'}")
    for k in ("state", "title", "cift"):
        if fa[k] != fb[k]:
            alan.append(k)
            fark.append(f"{k} {kisa(fa[k])!r}->{kisa(fb[k])!r}")
    return alan, fark


def calistir(once, sonra, out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    A, ca = yukle(once)
    B, cb = yukle(sonra)
    bozuk_once = sorted(l for l, (y, h, _) in A.items() if y is None)
    if bozuk_once or ca:
        print(f"::error::ONCE okunamadi {bozuk_once[:5]} / tekrar eden ilan {ca[:5]}", flush=True)
        return 2
    satir, alan_say = [], Counter()
    for lid in sorted(A):
        a, _, kl = A[lid]
        cift = str(a.get("cift") or kl.split("_", 1)[-1])
        if lid not in B:
            satir.append(dict(listing_id=lid, cift=cift, durum="EKSIK", fark="SONRA'da GALERI.json yok"))
            continue
        b, hb, _ = B[lid]
        if b is None:
            satir.append(dict(listing_id=lid, cift=cift, durum="EKSIK", fark=f"SONRA {hb}"))
            continue
        alan, fark = karsilastir(a, b)
        alan_say.update(alan)
        satir.append(dict(listing_id=lid, cift=cift, durum="FARKLI" if alan else "AYNI", fark="; ".join(fark)))
    with open(out / "KARSILASTIR.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "cift", "durum", "fark"])
        w.writeheader(); w.writerows(satir)
    d = Counter(x["durum"] for x in satir)
    fazla = sorted(set(B) - set(A))
    gecti = bool(satir) and d["AYNI"] == len(satir)
    ozet = (f"# Galeri karsilastirma ONCE / SONRA\n\n"
            f"once: {pathlib.Path(once).name} ({len(A)} ilan) | sonra: {pathlib.Path(sonra).name} ({len(B)} ilan)\n\n"
            f"SONUC: {'PASS' if gecti else 'FAIL'}\n\n"
            f"| durum | ilan |\n|---|---|\n| AYNI | {d['AYNI']} |\n| FARKLI | {d['FARKLI']} |\n| EKSIK | {d['EKSIK']} |\n"
            f"| yalniz SONRA'da | {len(fazla)} |\n\n"
            "Farkli alan sayilari (ilan): " + " ".join(f"{k} {alan_say[k]}" for k in ALANLAR) + "\n\n"
            "Karsilastirilan: rank sirasiyla gorsel kimligi + sayi (kapak rank 1), alt_text, bag (property_id, value, image_id), "
            "video kimligi, state, title. Yok sayilan: last_modified_timestamp, URL'ler.\n"
            + ("\n## AYNI olmayanlar\n\n" + "".join(f"- {x['listing_id']} {x['cift']} {x['durum']}: {x['fark']}\n"
                                                  for x in satir if x["durum"] != "AYNI") if d["AYNI"] != len(satir) else "")
            + ("\nyalniz SONRA'da: " + ", ".join(fazla[:20]) + "\n" if fazla else "")
            + ("\nONCE bos: karsilastirilacak ilan yok\n" if not satir else ""))
    (out / "OZET.md").write_text(ozet, encoding="utf-8")
    print(ozet, flush=True)
    return 0 if gecti else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", required=True); ap.add_argument("--sonra", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return calistir(a.once, a.sonra, a.out)


if __name__ == "__main__":
    sys.exit(main())
