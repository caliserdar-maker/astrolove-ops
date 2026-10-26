#!/usr/bin/env python3
"""Poster galeri v10 kartlarini Canva disa aktarim linklerinden Drive'a TASIMA (Merkez 26 Eki; Serdar onayi). Etsy'ye dokunmaz.
Girdi TSV: cift, kart_no, design_id, url (baslik satiri olabilir). Imzali URL ::add-mask:: ile maskelenir; loga / rapora yazilmaz.
  kart_no 2,3,6,7,8,9: cift data/pod/pod78_ids.csv'deki 78 ciftten biri -> <CIFT>_G<kart_no>.jpg
  kart_no 4,5: cift ORTAK -> ORTAK_G<kart_no>.jpg
--klasor: Drive klasorunun yerel yansisi (yalniz okunur; hedef_damga ile indirilen mevcut dosyalar). --yeni: bu kosunun yeni dosyalari.
Satir kontrolu: JPEG + 3000x2250. Ayni ad klasorde varsa: sha256 ayni -> ATLA, farkli -> FAIL (uzerine yazma yok).
Klasor kurali: iki farkli adda ayni sha256 -> FAIL (ORTAK dahil; yeni dosya yazilmadan once denetlenir).
Rapor: <yeni>/OZET.md + MANIFEST.csv (ad, cift, kart_no, design_id, boyut, sha256, durum) TUM klasor uzerinden yeniden uretilir.
Tamlik 78 x 6 + 2 = 470: eksikler listelenir, eksik olmasi FAIL degil. Satir FAIL'i varsa cikis 1."""
import argparse
import csv
import hashlib
import io
import pathlib
import re
import sys
import urllib.error
import urllib.request

from PIL import Image

HEDEF = (3000, 2250)
CIFT_KART, ORTAK_KART = (2, 3, 6, 7, 8, 9), (4, 5)
AD_RX = re.compile(r"^(?:(?P<c>[A-Z]+_[A-Z]+)|ORTAK)_G(?P<k>\d)\.jpg$")
ALAN = ["ad", "cift", "kart_no", "design_id", "boyut", "sha256", "durum"]


def maskele(s):
    if s:
        print(f"::add-mask::{s}", flush=True)


def satirlar(yol):
    out = []
    for r in csv.reader(open(yol, encoding="utf-8-sig"), delimiter="\t"):
        r = [c.strip() for c in r]
        if len(r) < 4 or not r[3].lower().startswith("http"):
            continue                                            # baslik / bos satir
        maskele(r[3])
        out.append(dict(cift=r[0], kart_no=r[1], design_id=r[2], url=r[3]))
    return out


def indir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-galeri-v10/1"})
    with urllib.request.urlopen(req, timeout=120) as y:
        return y.read()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def resim(b):
    try:
        im = Image.open(io.BytesIO(b))
        return im.format, im.size
    except Exception:  # noqa: BLE001
        return None, None


def ad_dogrula(r, ciftler):
    try:
        k = int(r["kart_no"])
    except ValueError:
        return None, f"kart_no gecersiz ({r['kart_no'][:10]})"
    c = r["cift"].upper()
    if k in ORTAK_KART:
        return (f"ORTAK_G{k}.jpg", None) if c == "ORTAK" else (None, f"kart {k} yalniz ORTAK olabilir")
    if k in CIFT_KART:
        if c == "ORTAK":
            return None, f"ORTAK yalniz kart 4/5 olabilir (kart {k})"
        return (f"{c}_G{k}.jpg", None) if c in ciftler else (None, "cift pod78 listesinde yok")
    return None, f"kart_no {k} beklenen 2-9 disinda"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--klasor", required=True, help="mevcut Drive klasorunun yerel yansisi (yalniz okunur; bos olabilir)")
    ap.add_argument("--yeni", required=True, help="bu kosuda eklenen dosyalar + OZET.md + MANIFEST.csv")
    ap.add_argument("--ciftler", required=True, help="data/pod/pod78_ids.csv")
    a = ap.parse_args(argv)
    klasor, yeni = pathlib.Path(a.klasor), pathlib.Path(a.yeni)
    klasor.mkdir(parents=True, exist_ok=True); yeni.mkdir(parents=True, exist_ok=True)
    ciftler = {r["cift"].strip() for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("cift")}
    eski_manifest = {}
    if (klasor / "MANIFEST.csv").exists():
        eski_manifest = {r["ad"]: r for r in csv.DictReader(open(klasor / "MANIFEST.csv", encoding="utf-8"))}
    mevcut = {}                                                 # ad -> (sha, boyut) klasordeki jpg'ler
    for p in sorted(klasor.glob("*.jpg")):
        b = p.read_bytes(); f, bt = resim(b)
        mevcut[p.name] = (sha(b), f"{bt[0]}x{bt[1]}" if bt else "-")
    satir = {}                                                  # ad -> manifest satiri (bu kosu)
    fail = []
    rows = satirlar(a.tsv)
    if not rows:
        print("FAIL: TSV'de gecerli satir yok (cift, kart_no, design_id, url)"); return 1
    for n, r in enumerate(rows, 1):
        ad, neden = ad_dogrula(r, ciftler)
        etiket = ad or f"satir{n}"
        if neden:
            fail.append(dict(ad=etiket, cift=r["cift"][:30], kart_no=r["kart_no"][:5], design_id=r["design_id"][:40], boyut="-",
                             sha256="-", durum=f"FAIL {neden}"))
            print(f"[{n}/{len(rows)}] {etiket} FAIL {neden}", flush=True); continue
        try:
            veri = indir(r["url"])
        except urllib.error.HTTPError as e:
            neden = f"HTTP {e.code}" + (" (link suresi dolmus olabilir)" if e.code == 403 else "")
        except Exception as e:  # noqa: BLE001
            neden = f"indirme {type(e).__name__}"
        if neden:
            fail.append(dict(ad=ad, cift=r["cift"], kart_no=r["kart_no"], design_id=r["design_id"], boyut="-", sha256="-",
                             durum=f"FAIL {neden}"))
            print(f"[{n}/{len(rows)}] {ad} FAIL {neden}", flush=True); continue
        h = sha(veri); f, bt = resim(veri)
        boyut = f"{bt[0]}x{bt[1]}" if bt else "-"
        kayit = dict(ad=ad, cift=r["cift"].upper(), kart_no=r["kart_no"], design_id=r["design_id"], boyut=boyut, sha256=h)
        if not (veri[:3] == b"\xff\xd8\xff" and f == "JPEG"):
            durum = f"FAIL JPEG degil ({f or 'okunamadi'})"
        elif bt != HEDEF:
            durum = f"FAIL boyut {boyut} != 3000x2250"
        elif ad in mevcut or ad in satir:
            onceki = mevcut[ad][0] if ad in mevcut else satir[ad]["sha256"]
            durum = "ATLA (ayni ad, ayni sha256)" if onceki == h else "FAIL ayni ad, farkli sha256 (uzerine yazilmaz)"
        else:
            cak = [x for x, (s, _) in mevcut.items() if s == h] + [x for x, v in satir.items() if v["sha256"] == h]
            durum = f"FAIL sha256 baska adla ayni: {cak[0]}" if cak else "YENI"
        if durum == "YENI":
            (yeni / ad).write_bytes(veri)
            satir[ad] = dict(kayit, durum=durum)
        elif durum.startswith("ATLA"):
            satir.setdefault(ad, dict(kayit, durum=durum))
        else:
            fail.append(dict(kayit, durum=durum))
        print(f"[{n}/{len(rows)}] {ad} {f} {boyut} {durum}", flush=True)
    # klasor geneli: mevcut + yeni, tum dosyalar uzerinden
    hepsi = {}
    for ad_, (h, bt) in mevcut.items():
        m = AD_RX.match(ad_)
        e = eski_manifest.get(ad_, {})
        hepsi[ad_] = dict(ad=ad_, cift=(m.group("c") or "ORTAK") if m else "?", kart_no=m.group("k") if m else "?",
                          design_id=e.get("design_id", ""), boyut=bt, sha256=h,
                          durum="MEVCUT" if bt == "3000x2250" and m else f"FAIL klasordeki dosya ({'ad' if not m else 'boyut ' + bt})")
    for ad_, v in satir.items():
        if v["durum"] == "YENI" or ad_ not in hepsi:
            hepsi[ad_] = v
        elif v["durum"].startswith("ATLA"):
            hepsi[ad_] = dict(hepsi[ad_], design_id=hepsi[ad_]["design_id"] or v["design_id"], durum=v["durum"])
    sha_ad = {}
    for v in hepsi.values():
        sha_ad.setdefault(v["sha256"], []).append(v["ad"])
    for h, adlar in sha_ad.items():                             # onceden var olan cift kopyalar da yakalanir
        if len(adlar) > 1:
            for x in adlar:
                hepsi[x]["durum"] = f"FAIL sha256 {len(adlar)} adda ayni: {', '.join(sorted(adlar))}"
    beklenen = [f"{c}_G{k}.jpg" for c in sorted(ciftler) for k in CIFT_KART] + [f"ORTAK_G{k}.jpg" for k in ORTAK_KART]
    eksik = [x for x in beklenen if x not in hepsi]
    eksik_cift = {}
    for x in eksik:
        c, k = x[:-4].rsplit("_G", 1); eksik_cift.setdefault(c, []).append(k)
    tum = sorted(hepsi.values(), key=lambda v: v["ad"]) + fail
    with open(yeni / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALAN); w.writeheader(); w.writerows({k: v.get(k, "") for k in ALAN} for v in tum)
    satir_fail = [v for v in tum if v["durum"].startswith("FAIL")]
    say = lambda s: sum(1 for v in tum if v["durum"].startswith(s))  # noqa: E731
    with open(yeni / "OZET.md", "w", encoding="utf-8") as fh:
        fh.write(f"# Poster galeri v10 tasima\n\nKlasordeki gecerli dosya {len(beklenen) - len(eksik)} / {len(beklenen)} "
                 f"(78 cift x 6 kart + 2 ortak) | bu kosu: YENI {say('YENI')}, ATLA {say('ATLA')}, FAIL {len(satir_fail)}\n\n")
        if satir_fail:
            fh.write("## FAIL\n" + "".join(f"- {v['ad']}: {v['durum'][5:]}\n" for v in satir_fail) + "\n")
        fh.write(f"## Eksik ({len(eksik)})\n")
        fh.write("".join(f"- {c}: G{', G'.join(k)}\n" for c, k in sorted(eksik_cift.items())) or "- yok\n")
    print(f"OZET: gecerli {len(beklenen) - len(eksik)}/{len(beklenen)} | YENI {say('YENI')} ATLA {say('ATLA')} FAIL {len(satir_fail)} "
          f"| eksik {len(eksik)}", flush=True)
    return 1 if satir_fail else 0


if __name__ == "__main__":
    sys.exit(main())
