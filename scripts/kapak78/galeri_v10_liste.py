#!/usr/bin/env python3
"""Poster 78 galeri v10: ilan basina LISTE_<ilan>.csv + manifest.json + hedef/ klasoru (Merkez 26 Eki; Serdar onayi).
ETSY API YOK, Drive yok: girdiler kilit ONCESI indirilmis yerel klasorlerdir. Yukleme scripts/kapak78/galeri_v10_yukle.py.

Galeri 9: 1 kapak, 2 iki burc tek sembol, 3 kisisellestirme, 4 format ve boy (ORTAK), 5 surec (ORTAK), 6 Deep Black, 7 Pure White,
8 Champagne Ivory, 9 Warm Parchment. Renk baglari MB->1, DB->6, PW->7, CI->8, WP->9. Canli 17 gorselin hepsi CIKAR.
Girdiler:
  --ciftler data/pod/pod78_ids.csv (listing_id, cift, a, b)   --alt data/pod/galeri_v10_alt.csv (sira, alt, alt_ayni_burc, durum)
  --kapak-dir  KAPAK_<CIFT>.jpg (TEMP/POSTER_KAPAK_V10/20261026_153710)
  --galeri-dir <CIFT>_G2,G3,G6,G7,G8,G9.jpg + ORTAK_G4.jpg, ORTAK_G5.jpg (TEMP/POSTER_GALERI_V10/<galeri_damga>)
  --yedek-dir  <ilan>_<CIFT>/GALERI.json + bagli 5 kartin r<rank>_<id>.jpg (TEMP/POSTER_KAPAK_V10_YEDEK/20261026_144404)
  --yedek-ozet yedek kosusunun OZET.md'si   --yedek-liste yedek klasorunun rclone lsjson -R ciktisi (dosya adi + boyut)
Ilan kapilari (biri tutmazsa BLOK, dosya uretilir ama yukleyici yazmaz):
  yedek: GALERI.json 17 gorsel (tekil kimlik), 5 renk bagi (property 200, 5 renk adi, 5 farkli gorsel, hepsi galeride), bagli 5 kart dosyasi;
         Drive'da 17 r<rank>_<id>.jpg (boyut > 0) ve yedek OZET.md satiri PASS / 17 dosya (yukleyici CDN yedegi almaz; silinecek her
         gorselin yedegi bu kapida dogrulanir, inceleme 26 Eki).
  dosya: 9 hedef dosya var, JPEG ve 3000x2250 (kapak dahil), 9 dosyanin sha256'si birbirinden farkli.
  alt metin: sablon 9 satir, uzun/orta tire yok, yasak ifade yok (eski78 YASAK_ALT), <= 250; --yazim ile durum ONAYLI zorunlu.
  renk karisma (renk_kapisi): kapak MB, G6-G9 DB/PW/CI/WP ile ayni ilanin yedekteki canli renk kartina karsi.
Renk karisma yontemi (26 Eki olcumu, yerel; G6-G9 gercek dosyalari henuz tasinmamisti):
  1) yer: referans kartin poster kutusu KUTU (78 MB kartta olculen (810,150)-(2189,1905), kapak78-yedek-mb 40342284109) yeni kartta
     coklu olcekli gradyan buyuklugu NCC ile bulunur (1/12 olcek, poster yuksekligi kart yuksekliginin %30-95'i). Skor < NCC_MIN
     ise FAIL (poster bulunamadi). Olcum: gercek kapak KAPAK_CANCER_LIBRA 0.69; postersiz kartlar (CL 04, 14) 0.33 ve 0.39.
  2) renk: bulunan kutunun ic %70'inde medyan CIELAB; ayni ilanin 5 referans kartinin (yedek, KUTU ic %70) medyan Lab'larina
     uzaklik. PASS: en yakin referans beklenen renk VE uzaklik < esik = 5 referansin birbirine en kucuk uzakliginin yarisi
     (ilan basina veriden; CL kartlarinda en kucuk cift PW-CI 15.5 -> esik 7.75). Olcum: gercek kapak MB 0.4, en yakin yanlis DB 18.4.
  3) referans etiketi: yedekteki 5 bagli kartin her biri, depodaki sabit renk kartlarina (data/pod/cl_galeri_final19 15-19) gore de
     kendi rengine en yakin olmali; degilse BLOK (canli baglari karisik eski ilan, yanlis renkleri dogru sanmasin).
  Bilinen sinir (inceleme 26 Eki): esik dar; dogru kart %10 karartilinca PW 9.1 ve CI 8.3 ile FAIL. G6-G9 gercek dosyalari
  tasindiktan sonra kuru kosu uzakliklari raporlar; FAIL yalniz BLOK (yazma yok), esik Serdar onayi olmadan degistirilmez.
Cikti <out>/: <ilan>/LISTE_<ilan>.csv, <ilan>/manifest.json, <ilan>/hedef/0N_N.jpg, LISTE_OZET.json, LISTE_OZET.md.
Cikis: 0 (BLOK olsa da; kararlar OZET'te), 2 girdi hatasi."""
import argparse
import csv
import hashlib
import itertools
import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import eski78_gorsel_yukle as Y  # noqa: E402

N_HEDEF = 9
RENKLER = ("Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment")
RENK_SIRA = {"Midnight Blue": 1, "Deep Black": 6, "Pure White": 7, "Champagne Ivory": 8, "Warm Parchment": 9}
RENK_PID = 200
BOYUT = (3000, 2250)
KUTU = (810, 150, 2189, 1905)
NCC_MIN = 0.5
OLCEK = 12
IC = 0.15
LISTE_ALAN = ["hedef_sira", "hedef_gorsel", "hedef_alt", "islem", "simdi_sira", "simdi_id"]
SABIT_REF = {ad: Path(__file__).resolve().parents[2] / "data/pod/cl_galeri_final19" / f for ad, f in (
    ("Midnight Blue", "15_renk_midnight_blue.jpg"), ("Deep Black", "16_renk_deep_black.jpg"), ("Pure White", "17_renk_pure_white.jpg"),
    ("Champagne Ivory", "18_renk_champagne_ivory.jpg"), ("Warm Parchment", "19_renk_warm_parchment.jpg"))}
_SABIT = {}


def sabit_ref():
    if not _SABIT:
        _SABIT.update({ad: renk_ozet(Image.open(p).convert("RGB"), KUTU) for ad, p in SABIT_REF.items()})
    return _SABIT


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def kaynaklar(cift, kapak_dir, galeri_dir):
    """hedef sira -> kaynak dosya yolu"""
    k = {1: Path(kapak_dir) / f"KAPAK_{cift}.jpg"}
    for s in (2, 3, 6, 7, 8, 9):
        k[s] = Path(galeri_dir) / f"{cift}_G{s}.jpg"
    for s in (4, 5):
        k[s] = Path(galeri_dir) / f"ORTAK_G{s}.jpg"
    return dict(sorted(k.items()))


def hedef_ad(s):
    return f"{s:02d}_{s}.jpg"   # eski78 hedef_id: NN_<id>.jpg -> id (manifest renk bagi eslemesi)


def sablon_oku(yol):
    rows = list(csv.DictReader(open(yol, encoding="utf-8-sig")))
    sab = {int(r["sira"]): r for r in rows}
    if sorted(sab) != list(range(1, N_HEDEF + 1)) or len(rows) != N_HEDEF:
        raise SystemExit(f"alt metin sablonu 1..{N_HEDEF} degil")
    return sab


def alt_metin(sab, a, b):
    """<A>, <B>: burc adlari; ayni burcta alt_ayni_burc doluysa o kullanilir. -> {sira: metin}"""
    ayni = a.strip().lower() == b.strip().lower()
    out = {}
    for s, r in sab.items():
        t = (r.get("alt_ayni_burc") or "").strip() if ayni else ""
        out[s] = " ".join((t or r["alt"]).replace("<A>", a.strip()).replace("<B>", b.strip()).split())
    return out


# ---------------- renk karisma kapisi ----------------
def lab(rgb):
    a = rgb / 255.0
    a = np.where(a > 0.04045, ((a + 0.055) / 1.055) ** 2.4, a / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = a @ m.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def _grad(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]; gy[1:-1] = g[2:] - g[:-2]
    return np.hypot(gx, gy)


def poster_bul(kart, sablon):
    """kart, sablon: PIL RGB. Coklu olcekli gradyan NCC. -> (skor, kutu (tam cozunurluk))"""
    k = kart.resize((kart.width // OLCEK, kart.height // OLCEK), Image.BILINEAR)
    kg = _grad(np.asarray(k.convert("L"), np.float32))
    ii = np.pad(kg, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ii2 = np.pad(kg * kg, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    en = (-1.0, None)
    H, W = kg.shape
    for h in range(int(H * 0.3), int(H * 0.95) + 1):
        w = round(h * sablon.width / sablon.height)
        if w >= W:
            continue
        t = _grad(np.asarray(sablon.resize((w, h), Image.BILINEAR).convert("L"), np.float32))
        t = t - t.mean(); tn = float(np.sqrt((t * t).sum()))
        if tn == 0:
            continue
        sh = (H + h, W + w)
        c = np.fft.irfft2(np.fft.rfft2(kg, sh) * np.conj(np.fft.rfft2(t, sh)), sh)[:H - h + 1, :W - w + 1]
        s1 = ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]
        s2 = ii2[h:, w:] - ii2[:-h, w:] - ii2[h:, :-w] + ii2[:-h, :-w]
        r = c / (np.sqrt(np.maximum(s2 - s1 * s1 / (h * w), 1e-6)) * tn)
        i = np.unravel_index(int(np.argmax(r)), r.shape)
        if r[i] > en[0]:
            en = (float(r[i]), (int(i[1] * OLCEK), int(i[0] * OLCEK), int((i[1] + w) * OLCEK), int((i[0] + h) * OLCEK)))
    return en


def renk_ozet(im, kutu):
    x0, y0, x1, y1 = kutu
    dx, dy = (x1 - x0) * IC, (y1 - y0) * IC
    a = np.asarray(im.crop((int(x0 + dx), int(y0 + dy), int(x1 - dx), int(y1 - dy))).resize((100, 130)), np.float32)
    return np.median(lab(a).reshape(-1, 3), 0)


def renk_kapisi(referans, aday):
    """referans: {renk: yedek kart yolu (5)}; aday: {renk: yeni dosya yolu}. -> {renk: sonuc}, esik"""
    ref_im = {r: Image.open(p).convert("RGB") for r, p in referans.items()}
    ref = {r: renk_ozet(im, KUTU) for r, im in ref_im.items()}
    esik = min(float(np.linalg.norm(ref[a] - ref[b])) for a, b in itertools.combinations(ref, 2)) / 2
    out = {}
    sb = sabit_ref()
    for r_, v in ref.items():   # referans etiketi: yedek kartin rengi sabit renk kartina gore de ayni ad olmali
        yk = min(sb, key=lambda k: float(np.linalg.norm(v - sb[k])))
        if yk != r_:
            out["_referans"] = dict(sonuc="FAIL", neden=f"yedekte {r_} bagli kart sabit kartlara gore {yk} rengi (bag karisik olabilir)")
            return out, round(esik, 2)
    for renk, p in aday.items():
        skor, kutu = poster_bul(Image.open(p).convert("RGB"), ref_im[renk].crop(KUTU))
        if kutu is None or skor < NCC_MIN:
            out[renk] = dict(sonuc="FAIL", neden=f"poster bolgesi bulunamadi (NCC {skor:.2f} < {NCC_MIN})", ncc=round(skor, 3))
            continue
        v = renk_ozet(Image.open(p).convert("RGB"), kutu)
        d = {r: round(float(np.linalg.norm(v - x)), 1) for r, x in ref.items()}
        yakin = min(d, key=d.get)
        ok = yakin == renk and d[renk] < esik
        out[renk] = dict(sonuc="PASS" if ok else "FAIL", ncc=round(skor, 3), kutu=kutu, uzaklik=d, en_yakin=yakin,
                         neden="" if ok else f"en yakin {yakin} ({d[yakin]}), beklenen {renk} {d[renk]}, esik {esik:.1f}")
    return out, round(esik, 2)


# ---------------- ilan ----------------
def jpeg_kontrol(p):
    if not p.exists():
        return "dosya yok"
    b = p.read_bytes()[:3]
    try:
        with Image.open(p) as im:
            f, bt = im.format, im.size
    except Exception:  # noqa: BLE001
        return "okunamadi"
    if b != b"\xff\xd8\xff" or f != "JPEG":
        return f"JPEG degil ({f})"
    if bt != BOYUT:
        return f"boyut {bt[0]}x{bt[1]} != 3000x2250"
    return ""


def yedek_oku(yd):
    """-> (gorseller rank sirali, baglar {renk: bag}, neden listesi)"""
    p = yd / "GALERI.json"
    if not p.exists():
        return [], {}, ["yedek GALERI.json yok"]
    j = json.loads(p.read_text(encoding="utf-8"))
    g = sorted(j.get("gorseller") or [], key=lambda x: x.get("rank") or 0)
    neden = []
    ids = [x.get("listing_image_id") for x in g]
    if len(g) != 17 or len(set(ids)) != 17:
        neden.append(f"yedek galeri {len(g)} gorsel / {len(set(ids))} tekil (17 beklenir)")
    bag = {}
    for b in j.get("baglar") or []:
        if b.get("property_id") != RENK_PID or b.get("value") not in RENKLER or b.get("value") in bag:
            neden.append(f"yedek bag gecersiz ({b.get('property_id')}, {b.get('value')})"); continue
        bag[b["value"]] = b
    if sorted(bag) != sorted(RENKLER):
        neden.append(f"yedekte {len(bag)} renk bagi (5 beklenir)")
    bimg = [b.get("image_id") for b in bag.values()]
    if len(set(bimg)) != len(bimg):
        neden.append("yedekte bir gorsel birden fazla renge bagli")
    if any(i not in ids for i in bimg):
        neden.append("yedekte bagli gorsel galeride yok")
    return g, bag, neden


def yedek_tamlik(lid, cift, g, ozet, liste):
    """Drive yedeginde 17 dosya (boyut > 0) + OZET.md satiri PASS ve 17 dosya."""
    neden = []
    row = ozet.get(lid)
    if not row or row[1] != cift or row[3] != "PASS" or row[2] != "17":
        neden.append(f"yedek OZET.md satiri PASS / 17 dosya degil ({'yok' if not row else '|'.join(row[1:4])})")
    eksik = [x for x in g if (liste.get(f"{lid}_{cift}/r{x.get('rank')}_{x.get('listing_image_id')}.jpg") or 0) <= 0]
    if eksik:
        neden.append(f"Drive yedeginde {len(eksik)} gorsel dosyasi yok / bos (r{', r'.join(str(x.get('rank')) for x in eksik[:5])})")
    return neden


def ozet_oku(p):
    out = {}
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0].isdigit():
            out[c[0]] = c
    return out


def ilan_hazirla(is_):
    """Tek ilan (surec havuzunda). -> ozet satiri"""
    r, sab, d = is_["satir"], is_["sablon"], is_["dizin"]
    lid, cift = r["listing_id"], r["cift"]
    neden = []
    yd = Path(d["yedek"]) / f"{lid}_{cift}"
    g, bag, n_ = yedek_oku(yd); neden += n_
    if g:
        neden += yedek_tamlik(lid, cift, g, d["yedek_ozet"], d["yedek_liste"])
    kay = kaynaklar(cift, d["kapak"], d["galeri"])
    for s, p in kay.items():
        e = jpeg_kontrol(p)
        if e:
            neden.append(f"G{s} {p.name}: {e}")
    shas = {s: sha(p) for s, p in kay.items() if p.exists()}
    if len(shas) == N_HEDEF and len(set(shas.values())) != N_HEDEF:
        neden.append("9 hedef dosyadan en az ikisi ayni (sha256)")
    alt = alt_metin(sab, r["a"], r["b"])
    for s, t in alt.items():
        if not t or len(t) > 250 or Y.YASAK_ALT.search(t):
            neden.append(f"alt metin {s} gecersiz (bos / >250 / yasak ifade / tire)")
    if d["yazim"] and any((x.get("durum") or "").strip() != "ONAYLI" for x in sab.values()):
        neden.append("alt metin sablonu ONAYLI degil (TASLAK; yazim yok)")
    renk, esik = {}, None
    ref = {}
    for ad, b in bag.items():
        rk = next((x.get("rank") for x in g if x.get("listing_image_id") == b.get("image_id")), None)
        p = yd / f"r{rk}_{b.get('image_id')}.jpg"
        if jpeg_kontrol(p):
            neden.append(f"yedek {ad} karti {p.name}: {jpeg_kontrol(p)}")
        ref[ad] = p
    aday = {ad: kay[s] for ad, s in RENK_SIRA.items()}   # kapak (1) MB karti ile, G6-G9 kendi renkleriyle
    if len(ref) == 5 and all(not jpeg_kontrol(p) for p in ref.values()) and all(not jpeg_kontrol(p) for p in aday.values()):
        renk, esik = renk_kapisi(ref, aday)
        for ad, x in renk.items():
            if x["sonuc"] != "PASS":
                neden.append(f"renk karisma {ad} (G{RENK_SIRA.get(ad, '-')}): {x['neden']}")
    else:
        neden.append("renk karisma kapisi olculemedi (referans ya da aday dosya eksik)")
    od = Path(d["out"]) / lid; hd = od / "hedef"
    if od.exists():
        shutil.rmtree(od)
    hd.mkdir(parents=True)
    hedef = []
    for s, p in kay.items():
        if p.exists():
            shutil.copyfile(p, hd / hedef_ad(s))
        hedef.append(dict(sira=s, ad=hedef_ad(s), kaynak=p.name, sha256=shas.get(s, ""), alt=alt[s]))
    rows = [dict(hedef_sira=s, hedef_gorsel=hedef_ad(s), hedef_alt=alt[s], islem="DEGISTIR", simdi_sira="", simdi_id="")
            for s in range(1, N_HEDEF + 1)]
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira=x.get("rank"),
                  simdi_id=x.get("listing_image_id")) for x in g]
    with open(od / f"LISTE_{lid}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LISTE_ALAN); w.writeheader(); w.writerows(rows)
    man = dict(listing_id=lid, cift=cift,
               variation_images=[dict(value=ad, image_id=RENK_SIRA[ad]) for ad in RENKLER if ad in bag],
               yedek_ids=sorted(x.get("listing_image_id") for x in g),
               yedek_galeri=[x.get("listing_image_id") for x in g],
               yedek_baglar={ad: dict(property_id=b.get("property_id"), value_id=b.get("value_id"), image_id=b.get("image_id"))
                             for ad, b in sorted(bag.items())},
               hedef=hedef, renk_kapisi=renk, renk_esik=esik)
    (od / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    return dict(ilan=lid, cift=cift, durum="BLOK" if neden else "HAZIR", neden=neden,
                liste_sha=Y.sha256(od / f"LISTE_{lid}.csv"), renk_esik=esik,
                renk={ad: dict(sonuc=x["sonuc"], uzaklik=x.get("uzaklik", {}).get(ad), ncc=x.get("ncc"), en_yakin=x.get("en_yakin"))
                      for ad, x in renk.items()})


def kapsam(ciftler, sadece="", haric=""):
    rows = [r for r in csv.DictReader(open(ciftler, encoding="utf-8-sig")) if r.get("listing_id")]
    s = {x.strip() for x in sadece.split(",") if x.strip()}
    h = {x.strip() for x in haric.split(",") if x.strip()}
    for x in s | h:
        if not x.isdigit():
            raise SystemExit(f"sadece/haric yalniz rakam ({x[:20]})")
    bilinmeyen = (s | h) - {r["listing_id"] for r in rows}
    if bilinmeyen:
        raise SystemExit(f"sadece/haric 78 ilan listesinde olmayan ilan: {sorted(bilinmeyen)}")
    return [r for r in rows if (not s or r["listing_id"] in s) and r["listing_id"] not in h]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--ciftler", "--alt", "--kapak-dir", "--galeri-dir", "--yedek-dir", "--yedek-ozet", "--yedek-liste", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--yazim", action="store_true", help="yazim kosusu: alt metin sablonu ONAYLI olmali")
    ap.add_argument("--is", type=int, default=os.cpu_count() or 2, dest="is_")
    a = ap.parse_args(argv)
    try:
        ilanlar = kapsam(a.ciftler, a.sadece, a.haric)
        sab = sablon_oku(a.alt)
        yozet = ozet_oku(a.yedek_ozet)
        yliste = {x["Path"]: int(x.get("Size") or 0) for x in json.loads(Path(a.yedek_liste).read_text(encoding="utf-8"))}
    except (SystemExit, OSError, ValueError, KeyError) as e:
        print(f"::error::{e}"); return 2
    if not ilanlar:
        print("::error::kapsamda ilan yok"); return 2
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    d = dict(yedek=a.yedek_dir, kapak=a.kapak_dir, galeri=a.galeri_dir, out=str(out), yazim=a.yazim, yedek_ozet=yozet, yedek_liste=yliste)
    isler = [dict(satir=r, sablon=sab, dizin=d) for r in ilanlar]
    sonuc = []
    with ProcessPoolExecutor(max(1, a.is_)) as ex:
        for n, s in enumerate(ex.map(ilan_hazirla, isler), 1):
            sonuc.append(s)
            print(f"[{n}/{len(isler)}] {s['ilan']} {s['cift']} {s['durum']}" + (f": {s['neden'][0][:120]}" if s["neden"] else ""), flush=True)
    alt_durum = sorted({(x.get("durum") or "").strip() for x in sab.values()})
    oz = dict(alt_sablon_durum=alt_durum, alt_sablon_sha=Y.sha256(a.alt), yazim=a.yazim, ncc_min=NCC_MIN, kutu=KUTU,
              ilanlar={s["ilan"]: s for s in sonuc})
    (out / "LISTE_OZET.json").write_text(json.dumps(oz, indent=1, ensure_ascii=False), encoding="utf-8")
    hazir = sum(1 for s in sonuc if s["durum"] == "HAZIR")
    with open(out / "LISTE_OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Galeri v10 liste\n\nHAZIR {hazir} / BLOK {len(sonuc) - hazir} (ilan {len(sonuc)}) | alt metin sablonu {', '.join(alt_durum)}\n\n")
        f.writelines(f"- {s['ilan']} {s['cift']}: {'; '.join(s['neden'])}\n" for s in sonuc if s["neden"])
    print(f"LISTE OZET: HAZIR {hazir} BLOK {len(sonuc) - hazir} | alt metin {','.join(alt_durum)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
