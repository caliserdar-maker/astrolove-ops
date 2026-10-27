#!/usr/bin/env python3
"""Poster galeri v10 kartlarini Canva disa aktarim linklerinden Drive'a TASIMA (Merkez 26 Eki; Serdar onayi). Etsy'ye dokunmaz.
Girdi TSV: cift, kart_no, design_id, url (baslik satiri olabilir). Imzali URL ::add-mask:: ile maskelenir; loga / rapora yazilmaz.
  kart_no 2,3,6,7,8,9: cift data/pod/pod78_ids.csv'deki 78 ciftten biri -> <CIFT>_G<kart_no>.jpg
  kart_no 4,5: cift ORTAK -> ORTAK_G<kart_no>.jpg
--klasor: Drive klasorunun yerel yansisi (yalniz okunur; hedef_damga ile indirilen mevcut dosyalar). --yeni: bu kosunun yeni dosyalari.
Satir kontrolu: JPEG + 3000x2250. Ayni ad klasorde varsa: sha256 ayni -> ATLA, farkli -> FAIL (uzerine yazma yok).
Klasor kurali: iki farkli adda ayni sha256 -> FAIL (ORTAK dahil; yeni dosya yazilmadan once denetlenir).
Rapor: <yeni>/OZET.md + MANIFEST.csv (ad, cift, kart_no, design_id, boyut, sha256, durum) TUM klasor uzerinden yeniden uretilir.
Tamlik 78 x 6 + 2 = 470: eksikler listelenir, eksik olmasi FAIL degil. Satir FAIL'i varsa cikis 1.
--urun yd (YD 1st Anniversary kapak, plan v3 adim 2; Merkez 27 Eki): ayni kurallar, farklari:
  hedef 2400x2400, ad KAPAK_<CIFT>.jpg (kart_no yalniz 1; cift data/pod/yd78_ids.csv), tamlik 78 (KAPAK_<CIFT>.jpg x 78).
  Baslik disi atlanacak her satir (3 sutun, url yok) FAIL. --metin-kapi METIN_KAPI.tsv zorunlu: (cift, design_id) PASS satiriyla
  ayni degilse FAIL. Link suresi satir basina: X-Amz-Date + X-Amz-Expires - simdi < 5 dk -> indirilmez, SURE_AZ (yeniden disa
  aktarma listesi); parametre yoksa FAIL. Imza tekrari: IMZA.csv (design_id, sha256(X-Amz-Date + imza); ham imza yazilmaz) klasorde;
  ayni tasarim icin onceki kosudaki imza aynen donerse satir DUR (onbellek dongusu yok); dosya zaten klasordeyse (ayni design_id) ATLA.
  SURE_AZ / DUR da cikis 1. Satir kayitlari (FAIL / SURE_AZ / DUR) MANIFEST'te satir<n>:<ad> anahtariyla (dosya satirindan ayri)."""
import argparse
import calendar
import csv
import hashlib
import io
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

HEDEF = (3000, 2250)
CIFT_KART, ORTAK_KART = (2, 3, 6, 7, 8, 9), (4, 5)
AD_RX = re.compile(r"^(?:(?P<c>[A-Z]+_[A-Z]+)|ORTAK)_G(?P<k>\d)\.jpg$")
ALAN = ["ad", "cift", "kart_no", "design_id", "boyut", "sha256", "durum"]
YD_HEDEF = (2400, 2400)
YD_AD_RX = re.compile(r"^KAPAK_(?P<c>[A-Z]+_[A-Z]+)\.jpg$")
SURE_ALT = 300          # sn: indirme aninda kalan link suresi bunun altindaysa indirilmez (plan v3 adim 2: 5 dk)
IMZA_ALAN = ["design_id", "imza_ozet", "kosu"]


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


def satirlar_yd(yol):
    """YD: baslik (ilk hucre 'cift') ve tamamen bos satir disinda atlanan satir yok; gecersiz satir FAIL kaydi olur."""
    out, hata = [], []
    for n, r in enumerate(csv.reader(open(yol, encoding="utf-8-sig"), delimiter="\t"), 1):
        r = [c.strip() for c in r]
        if not any(r) or (r and r[0].lower() == "cift"):
            continue
        url = next((c for c in r if c.lower().startswith("http")), "")
        maskele(url)
        if len(r) < 4 or any(r[4:]) or not r[3].lower().startswith("http"):
            hata.append(dict(ad=f"satir{n}", cift=r[0][:30], kart_no="-", design_id="-", boyut="-", sha256="-",
                             durum=f"FAIL TSV satiri {len(r)} sutun / url 4. sutunda degil (cift, kart_no, design_id, url)"))
            continue
        out.append(dict(cift=r[0], kart_no=r[1], design_id=r[2], url=r[3], satir=n))
    return out, hata


def metin_kapi_oku(yol):
    """METIN_KAPI.tsv (cift, design_id, baslik, satir_metni, durum) -> {cift: design_id} yalniz PASS satirlari."""
    rows = list(csv.DictReader(open(yol, encoding="utf-8-sig"), delimiter="\t"))
    if not rows or not {"cift", "design_id", "durum"} <= set(rows[0]):
        raise SystemExit("FAIL: METIN_KAPI.tsv basligi cift, design_id, ..., durum degil")
    kapi = {}
    for r in rows:
        if (r.get("durum") or "").strip() == "PASS":
            c = (r.get("cift") or "").strip().upper()
            if c in kapi and kapi[c] != r["design_id"].strip():
                raise SystemExit(f"FAIL: METIN_KAPI.tsv {c} icin iki farkli PASS tasarim")
            kapi[c] = r["design_id"].strip()
    return kapi


def link_suresi(url, simdi):
    """S3 imzali link: kalan sn = X-Amz-Date + X-Amz-Expires - simdi; imza ozeti = sha256(X-Amz-Date + X-Amz-Signature).
    Parametre eksikse (None, None)."""
    q = {k.lower(): v for k, v in urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)}
    try:
        t0 = calendar.timegm(time.strptime(q["x-amz-date"], "%Y%m%dT%H%M%SZ"))
        kalan = t0 + int(q["x-amz-expires"]) - simdi
    except (KeyError, ValueError):
        return None, None
    imza = q.get("x-amz-signature")
    return kalan, (hashlib.sha256((q["x-amz-date"] + imza).encode()).hexdigest() if imza else None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--klasor", required=True, help="mevcut Drive klasorunun yerel yansisi (yalniz okunur; bos olabilir)")
    ap.add_argument("--yeni", required=True, help="bu kosuda eklenen dosyalar + OZET.md + MANIFEST.csv")
    ap.add_argument("--ciftler", required=True, help="data/pod/pod78_ids.csv (poster) | data/pod/yd78_ids.csv (yd)")
    ap.add_argument("--urun", choices=("poster", "yd"), default="poster")
    ap.add_argument("--metin-kapi", default="", help="yd: METIN_KAPI.tsv (zorunlu)")
    ap.add_argument("--simdi", type=float, default=None, help="test: epoch sn (varsayilan saat)")
    a = ap.parse_args(argv)
    if a.urun == "yd":
        return main_yd(a)
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


def main_yd(a):
    """--urun yd: KAPAK_<CIFT>.jpg 2400x2400 (plan v3 adim 2). Poster akisinin ayni kurallari + satir / metin / sure / imza kapilari."""
    klasor, yeni = pathlib.Path(a.klasor), pathlib.Path(a.yeni)
    klasor.mkdir(parents=True, exist_ok=True); yeni.mkdir(parents=True, exist_ok=True)
    if not a.metin_kapi:
        print("FAIL: --urun yd icin --metin-kapi METIN_KAPI.tsv zorunlu"); return 1
    kapi = metin_kapi_oku(a.metin_kapi)
    ciftler = {r["cift"].strip() for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("cift")}
    hedef_bt = f"{YD_HEDEF[0]}x{YD_HEDEF[1]}"
    eski_manifest = {}
    if (klasor / "MANIFEST.csv").exists():
        eski_manifest = {r["ad"]: r for r in csv.DictReader(open(klasor / "MANIFEST.csv", encoding="utf-8"))}
    imza_eski = {}                                              # design_id -> {imza_ozet}
    if (klasor / "IMZA.csv").exists():
        for r in csv.DictReader(open(klasor / "IMZA.csv", encoding="utf-8")):
            imza_eski.setdefault(r["design_id"], set()).add(r["imza_ozet"])
    imza_yeni = []
    kosu = os.environ.get("GITHUB_RUN_ID", "yerel")
    mevcut = {}
    for p in sorted(klasor.glob("*.jpg")):
        b = p.read_bytes(); f, bt = resim(b)
        mevcut[p.name] = (sha(b), f"{bt[0]}x{bt[1]}" if bt else "-")
    satir, fail, sure_az, dur = {}, [], [], []
    rows, fail_tsv = satirlar_yd(a.tsv)
    fail += fail_tsv
    for v in fail_tsv:
        print(f"{v['ad']} {v['durum']}", flush=True)
    if not rows and not fail_tsv:
        print("FAIL: TSV'de gecerli satir yok (cift, kart_no, design_id, url)"); return 1
    for n, r in enumerate(rows, 1):
        c = r["cift"].upper()
        ad = f"KAPAK_{c}.jpg" if c in ciftler else None
        # satir kaydi (FAIL / SURE_AZ / DUR) dosya adiyla AYNI anahtarda olmaz: satir<n>:<ad> (inceleme 27 Eki: MANIFEST'te ayni ad
        # iki satir -> yd_liste_uret son satiri alip gecerli dosyayi BLOK yapiyordu; eski_manifest design_id bozuluyordu)
        kayit0 = dict(ad=f"satir{r['satir']}:{ad}" if ad else f"satir{r['satir']}", cift=c[:30], kart_no=r["kart_no"][:5], design_id=r["design_id"][:40], boyut="-",
                      sha256="-")
        if c not in ciftler:
            neden = "cift yd78 listesinde yok"
        elif r["kart_no"] != "1":
            neden = f"kart_no {r['kart_no'][:5]} (yd yalniz 1)"
        elif kapi.get(c) != r["design_id"]:
            neden = "METIN_KAPI PASS satiri ile (cift, design_id) ayni degil" + ("" if c in kapi else " (cift PASS degil)")
        else:
            neden = None
        kalan, iz = link_suresi(r["url"], time.time() if a.simdi is None else a.simdi)   # kalan sure bu satirin indirme aninda
        if iz:
            imza_yeni.append(dict(design_id=r["design_id"][:40], imza_ozet=iz, kosu=kosu))
        if not neden and kalan is None:
            neden = "link suresi okunamadi (X-Amz-Date / X-Amz-Expires yok)"
        if not neden and not iz:
            neden = "link imzasi yok (X-Amz-Signature)"
        if neden:
            fail.append(dict(kayit0, durum=f"FAIL {neden}"))
            print(f"[{n}/{len(rows)}] {kayit0['ad']} FAIL {neden}", flush=True); continue
        if iz in imza_eski.get(r["design_id"], set()) and ad in mevcut and mevcut[ad][1] == hedef_bt \
                and eski_manifest.get(ad, {}).get("design_id") == r["design_id"]:   # dosya zaten klasorde: tekrar gonderilen satir
            satir.setdefault(ad, dict(kayit0, ad=ad, cift=c, kart_no="1", design_id=r["design_id"], boyut=mevcut[ad][1], sha256=mevcut[ad][0],
                                      durum="ATLA (dosya mevcut, ayni imza; indirilmedi)"))
            print(f"[{n}/{len(rows)}] {ad} ATLA dosya mevcut (ayni imza)", flush=True); continue
        if iz in imza_eski.get(r["design_id"], set()):
            dur.append(dict(kayit0, durum="DUR ayni imza onceki kosuda (onbellek linki; yeniden disa aktar)"))
            print(f"[{n}/{len(rows)}] {ad} DUR ayni imza", flush=True); continue
        if kalan < SURE_ALT:
            sure_az.append(dict(kayit0, durum=f"SURE_AZ kalan {int(kalan // 60)} dk (< {SURE_ALT // 60}); indirilmedi"))
            print(f"[{n}/{len(rows)}] {ad} SURE_AZ kalan {int(kalan)} sn", flush=True); continue
        try:
            veri = indir(r["url"])
        except urllib.error.HTTPError as e:
            neden = f"HTTP {e.code}" + (" (link suresi dolmus olabilir)" if e.code == 403 else "")
        except Exception as e:  # noqa: BLE001
            neden = f"indirme {type(e).__name__}"
        if neden:
            fail.append(dict(kayit0, durum=f"FAIL {neden}"))
            print(f"[{n}/{len(rows)}] {ad} FAIL {neden}", flush=True); continue
        h = sha(veri); f, bt = resim(veri)
        boyut = f"{bt[0]}x{bt[1]}" if bt else "-"
        kayit = dict(kayit0, ad=ad, cift=c, kart_no="1", design_id=r["design_id"], boyut=boyut, sha256=h)
        if not (veri[:3] == b"\xff\xd8\xff" and f == "JPEG"):
            durum = f"FAIL JPEG degil ({f or 'okunamadi'})"
        elif bt != YD_HEDEF:
            durum = f"FAIL boyut {boyut} != {hedef_bt}"
        elif ad in mevcut or ad in satir:
            onceki = mevcut[ad][0] if ad in mevcut else satir[ad]["sha256"]
            durum = "ATLA (ayni ad, ayni sha256)" if onceki == h else "FAIL ayni ad, farkli sha256 (uzerine yazilmaz)"
        else:
            cak = [x for x, (s_, _) in mevcut.items() if s_ == h] + [x for x, v in satir.items() if v["sha256"] == h]
            durum = f"FAIL sha256 baska adla ayni: {cak[0]}" if cak else "YENI"
        if durum == "YENI":
            (yeni / ad).write_bytes(veri)
            satir[ad] = dict(kayit, durum=durum)
        elif durum.startswith("ATLA"):
            satir.setdefault(ad, dict(kayit, durum=durum))
        else:
            fail.append(dict(kayit, ad=kayit0["ad"], durum=durum))
        print(f"[{n}/{len(rows)}] {ad} {f} {boyut} {durum}", flush=True)
    hepsi = {}
    for ad_, (h, bt) in mevcut.items():
        m = YD_AD_RX.match(ad_)
        e = eski_manifest.get(ad_, {})
        gecerli = bool(m) and bt == hedef_bt and m.group("c") in ciftler
        hepsi[ad_] = dict(ad=ad_, cift=m.group("c") if m else "?", kart_no="1" if m else "?", design_id=e.get("design_id", ""),
                          boyut=bt, sha256=h, durum="MEVCUT" if gecerli else
                          f"FAIL klasordeki dosya ({'ad' if not m else ('cift' if m.group('c') not in ciftler else 'boyut ' + bt)})")
    for ad_, v in satir.items():
        if v["durum"] == "YENI" or ad_ not in hepsi:
            hepsi[ad_] = v
        elif v["durum"].startswith("ATLA"):
            hepsi[ad_] = dict(hepsi[ad_], design_id=hepsi[ad_]["design_id"] or v["design_id"], durum=v["durum"])
    sha_ad = {}
    for v in hepsi.values():
        sha_ad.setdefault(v["sha256"], []).append(v["ad"])
    for h, adlar in sha_ad.items():
        if len(adlar) > 1:
            for x in adlar:
                hepsi[x]["durum"] = f"FAIL sha256 {len(adlar)} adda ayni: {', '.join(sorted(adlar))}"
    beklenen = [f"KAPAK_{c}.jpg" for c in sorted(ciftler)]
    gecerli_ad = {x for x, v in hepsi.items() if not v["durum"].startswith("FAIL")}
    eksik = [x for x in beklenen if x not in gecerli_ad]
    tum = sorted(hepsi.values(), key=lambda v: v["ad"]) + fail + sure_az + dur
    with open(yeni / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALAN); w.writeheader(); w.writerows({k: v.get(k, "") for k in ALAN} for v in tum)
    gor = set()
    with open(yeni / "IMZA.csv", "w", newline="", encoding="utf-8") as fh:   # onceki + bu kosu (ham imza yok)
        w = csv.DictWriter(fh, fieldnames=IMZA_ALAN); w.writeheader()
        eski_satir = list(csv.DictReader(open(klasor / "IMZA.csv", encoding="utf-8"))) if (klasor / "IMZA.csv").exists() else []
        for r in eski_satir + imza_yeni:
            k = (r["design_id"], r["imza_ozet"])
            if k not in gor:
                gor.add(k); w.writerow({x: r.get(x, "") for x in IMZA_ALAN})
    satir_fail = [v for v in tum if v["durum"].startswith("FAIL")]
    say = lambda s_: sum(1 for v in tum if v["durum"].startswith(s_))  # noqa: E731
    with open(yeni / "OZET.md", "w", encoding="utf-8") as fh:
        fh.write(f"# YD kapak tasima\n\nKlasordeki gecerli dosya {len(beklenen) - len(eksik)} / {len(beklenen)} "
                 f"(KAPAK_<CIFT>.jpg, {hedef_bt}) | bu kosu: YENI {say('YENI')}, ATLA {say('ATLA')}, FAIL {len(satir_fail)}, "
                 f"SURE_AZ {len(sure_az)}, DUR {len(dur)}\n\n")
        if satir_fail:
            fh.write("## FAIL\n" + "".join(f"- {v['ad']}: {v['durum'][5:]}\n" for v in satir_fail) + "\n")
        if sure_az or dur:
            fh.write("## Yeniden disa aktar (SURE_AZ / DUR)\n"
                     + "".join(f"- {v['cift']} {v['design_id']}: {v['durum']}\n" for v in sure_az + dur) + "\n")
        fh.write(f"## Eksik ({len(eksik)})\n" + ("".join(f"- {x[6:-4]}\n" for x in eksik) or "- yok\n"))
    print(f"OZET: gecerli {len(beklenen) - len(eksik)}/{len(beklenen)} | YENI {say('YENI')} ATLA {say('ATLA')} FAIL {len(satir_fail)} "
          f"SURE_AZ {len(sure_az)} DUR {len(dur)} | eksik {len(eksik)}", flush=True)
    return 1 if satir_fail or sure_az or dur else 0


if __name__ == "__main__":
    sys.exit(main())
