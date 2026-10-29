#!/usr/bin/env python3
"""Poster 78 galeri v11: ilan basina LISTE_<ilan>.csv + manifest.json + hedef/ (Merkez 29 Eki, plan v2; Serdar kararlari K1-K4).
ETSY API YOK, Drive yok (girdiler kilit ONCESI indirilmis yerel klasorler). Yukleme scripts/kapak78/galeri_v11_yukle.py.
Galeri 10: W01 kapak CI, W02 sembol, W03 kisisellestirme, W04 format (ORTAK), W05 surec, W06 genel bakis (Choose Your Color),
W07 MB, W08 DB, W09 PW, W10 WP. Renk baglari CI->1, MB->7, DB->8, PW->9, WP->10. Canli 9 gorselin (v10) hepsi CIKAR.
Girdiler:
  --ciftler data/pod/pod78_ids.csv   --alt data/pod/galeri_v11_alt.csv (sira 1..10, alt, alt_ayni_burc, durum)
  --galeri-dir <CIFT>_W01_KAPAK|W07_MB|W08_DB|W09_PW|W10_WP.jpg (TEMP/POSTER_GALERI_V11/<damga>, galeri-v11-tasi)
  --kapi-csv   B3 KAPI.csv (galeri-v11-kapi, onayli esikle): ciftin 5 Canva dosyasi PASS ve sha256 ayni
  --kart-manifest bilgi karti toplu uretiminin manifesti (JSON; kart uretimi bu gorevin kapsami disinda, BICIM ONERI / onay bekler):
               {"format_boy_sayisi": <int|null>, "kartlar": {"ORTAK": {"4": "<dosya>"}, "<CIFT>": {"2": .., "3": .., "5": .., "6": ..}}},
               dosyalar manifestin klasorunde. Yoksa ilan BLOK ("bilgi kartlari yok").
  --kesim-dir  ref/kapak_ci (kapak-ci-ref-20261029: CI_<CIFT>.png G8 kesimi, PW_<CIFT>.png G7 kesimi)
  --yedek-dir  B1 yedegi (TEMP/POSTER_GALERI_V11_YEDEK/<damga>: <ilan>_<CIFT>/GALERI.json + r<rank>_<id>.jpg), --yedek-ozet OZET.md,
  --yedek-liste yedek klasorunun rclone lsjson -R ciktisi.
Ilan kapilari (biri tutmazsa BLOK; dosyalar yine yazilir, yukleyici yazmaz):
  yedek: GALERI.json 9 gorsel (tekil), 5 renk bagi (property 200, 5 ad, 5 farkli gorsel, hepsi galeride); Drive'da 9 dosya (boyut > 0)
         ve OZET.md satiri PASS / 9 dosya.
  dosya: 10 hedef var, JPEG 3000x2250, 10 sha256 birbirinden farkli; 5 Canva dosyasi B3 KAPI.csv'de PASS ve sha256 ayni.
  alt metin: sablon 10 satir, <= 250, yasak ifade / tire yok (eski78 YASAK_ALT); --yazim ile durum ONAYLI zorunlu.
  renk (W01 CI, W09 PW): kesimle poster_bul (galeri_v10_liste, gradyan NCC >= NCC_MIN 0.5) + medyan CIELAB: kendi kesimine uzaklik
         < diger kesime uzaklik ve < esik = iki kesimin (CI, PW) birbirine uzakliginin yarisi. W07 / W08 / W10 renk kimligi B3'te
         (canli v10 kartiyla piksel farki) denetlenir.
Cikti <out>/: <ilan>/LISTE_<ilan>.csv, manifest.json (format_boy_sayisi dahil), hedef/NN_N.jpg, LISTE_OZET.json, LISTE_OZET.md. Cikis 0 / 2."""
import argparse
import csv
import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy"))
import eski78_gorsel_yukle as Y  # noqa: E402
import galeri_v10_liste as L  # noqa: E402

N_HEDEF, CANLI_N = 10, 9
RENKLER = L.RENKLER
RENK_SIRA = {"Champagne Ivory": 1, "Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}
CANVA = {1: "W01_KAPAK", 7: "W07_MB", 8: "W08_DB", 9: "W09_PW", 10: "W10_WP"}
KART = {2: "cift", 3: "cift", 4: "ORTAK", 5: "cift", 6: "cift"}
RENK_KESIM = {1: ("Champagne Ivory", "CI"), 9: ("Pure White", "PW")}


def sablon_oku(yol):
    rows = list(csv.DictReader(open(yol, encoding="utf-8-sig")))
    sab = {int(r["sira"]): r for r in rows}
    if sorted(sab) != list(range(1, N_HEDEF + 1)) or len(rows) != N_HEDEF:
        raise SystemExit(f"alt metin sablonu 1..{N_HEDEF} degil")
    return sab


def kart_oku(yol):
    if not yol:
        return None, None
    p = Path(yol)
    j = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(j.get("kartlar"), dict):
        raise SystemExit("kart manifesti: 'kartlar' sozlugu yok")
    fb = j.get("format_boy_sayisi")
    if fb is not None and not isinstance(fb, int):
        raise SystemExit("kart manifesti: format_boy_sayisi tam sayi ya da null olmali")
    return j, p.parent


def kaynaklar(cift, d):
    """hedef sira -> (yol | None, neden)"""
    k = {s: (Path(d["galeri"]) / f"{cift}_{ad}.jpg", "") for s, ad in CANVA.items()}
    km, kd = d["kart"], d["kart_dir"]
    for s, sahip in KART.items():
        if km is None:
            k[s] = (None, "bilgi kartlari yok (kart toplu uretimi; --kart-manifest)"); continue
        ad = ((km["kartlar"].get("ORTAK" if sahip == "ORTAK" else cift) or {}).get(str(s)))
        k[s] = (Path(kd) / ad, "") if ad and "/" not in ad and ".." not in ad else (None, f"kart manifestinde W{s:02d} yok")
    return dict(sorted(k.items()))


def yedek_oku(yd):
    p = yd / "GALERI.json"
    if not p.exists():
        return [], {}, ["yedek GALERI.json yok"]
    j = json.loads(p.read_text(encoding="utf-8"))
    g = sorted(j.get("gorseller") or [], key=lambda x: x.get("rank") or 0)
    ids = [x.get("listing_image_id") for x in g]
    neden = []
    if len(g) != CANLI_N or len(set(ids)) != CANLI_N:
        neden.append(f"yedek galeri {len(g)} gorsel / {len(set(ids))} tekil ({CANLI_N} beklenir)")
    bag = {}
    for b in j.get("baglar") or []:
        if b.get("property_id") != L.RENK_PID or b.get("value") not in RENKLER or b.get("value") in bag:
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
    neden = []
    row = ozet.get(lid)
    if not row or row[1] != cift or row[3] != "PASS" or row[2] != str(CANLI_N):
        neden.append(f"yedek OZET.md satiri PASS / {CANLI_N} dosya degil ({'yok' if not row else '|'.join(row[1:4])})")
    eksik = [x for x in g if (liste.get(f"{lid}_{cift}/r{x.get('rank')}_{x.get('listing_image_id')}.jpg") or 0) <= 0]
    if eksik:
        neden.append(f"Drive yedeginde {len(eksik)} gorsel dosyasi yok / bos")
    return neden


def renk_kesim(aday, kesim, diger):
    """aday: W01 / W09 dosyasi; kesim: kendi CI / PW kesimi; diger: obur kesim. -> sonuc"""
    k = Image.open(kesim).convert("RGB"); o = Image.open(diger).convert("RGB")
    im = Image.open(aday).convert("RGB")
    skor, kutu = L.poster_bul(im, k)
    if kutu is None or skor < L.NCC_MIN:
        return dict(sonuc="FAIL", ncc=round(skor, 3), neden=f"poster bulunamadi (NCC {skor:.2f} < {L.NCC_MIN})")
    v = L.renk_ozet(im, kutu)
    kk, ko = L.renk_ozet(k, (0, 0, k.width, k.height)), L.renk_ozet(o, (0, 0, o.width, o.height))
    d_k, d_o = float(np.linalg.norm(v - kk)), float(np.linalg.norm(v - ko))
    esik = float(np.linalg.norm(kk - ko)) / 2
    ok = d_k < d_o and d_k < esik
    return dict(sonuc="PASS" if ok else "FAIL", ncc=round(skor, 3), kutu=kutu, kendi=round(d_k, 1), diger=round(d_o, 1), esik=round(esik, 1),
                neden="" if ok else f"kendi kesimine {d_k:.1f}, diger {d_o:.1f}, esik {esik:.1f}")


def kapi_oku(p):
    if not p or not Path(p).exists():
        return {}
    return {r["dosya"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}


def ilan_hazirla(is_):
    r, sab, d = is_["satir"], is_["sablon"], is_["dizin"]
    lid, cift = r["listing_id"], r["cift"]
    neden = []
    yd = Path(d["yedek"]) / f"{lid}_{cift}"
    g, bag, n_ = yedek_oku(yd); neden += n_
    if g:
        neden += yedek_tamlik(lid, cift, g, d["yedek_ozet"], d["yedek_liste"])
    kay = kaynaklar(cift, d)
    for s, (p, nd) in kay.items():
        if nd:
            neden.append(f"W{s:02d}: {nd}"); continue
        e = L.jpeg_kontrol(p)
        if e:
            neden.append(f"W{s:02d} {p.name}: {e}")
    shas = {s: L.sha(p) for s, (p, _) in kay.items() if p is not None and p.exists()}
    if len(shas) == N_HEDEF and len(set(shas.values())) != N_HEDEF:
        neden.append(f"{N_HEDEF} hedef dosyadan en az ikisi ayni (sha256)")
    for s, ad in CANVA.items():
        k = d["kapi"].get(f"{cift}_{ad}.jpg")
        if not k or k.get("durum") != "PASS":
            neden.append(f"W{s:02d} B3 kapisi PASS degil ({(k or {}).get('durum', 'KAPI.csv satiri yok')})")
        elif s in shas and k.get("sha256") != shas[s]:
            neden.append(f"W{s:02d} dosyasi B3 kapisindan gecen dosya degil (sha256)")
    alt = L.alt_metin(sab, r["a"], r["b"])
    for s, t in alt.items():
        if not t or len(t) > 250 or Y.YASAK_ALT.search(t):
            neden.append(f"alt metin {s} gecersiz (bos / >250 / yasak ifade / tire)")
    if d["yazim"] and any((x.get("durum") or "").strip() != "ONAYLI" for x in sab.values()):
        neden.append("alt metin sablonu ONAYLI degil (TASLAK; yazim yok)")
    renk = {}
    for s, (ad, on) in RENK_KESIM.items():
        p = kay[s][0]
        ke, ob = Path(d["kesim"]) / f"{on}_{cift}.png", Path(d["kesim"]) / f"{'PW' if on == 'CI' else 'CI'}_{cift}.png"
        if p is None or L.jpeg_kontrol(p) or not ke.exists() or not ob.exists():
            neden.append(f"renk {ad} (W{s:02d}) olculemedi (dosya / kesim eksik)"); continue
        renk[ad] = renk_kesim(p, ke, ob)
        if renk[ad]["sonuc"] != "PASS":
            neden.append(f"renk {ad} (W{s:02d}): {renk[ad]['neden']}")
    od = Path(d["out"]) / lid; hd = od / "hedef"
    if od.exists():
        shutil.rmtree(od)
    hd.mkdir(parents=True)
    hedef = []
    for s, (p, _) in kay.items():
        if p is not None and p.exists():
            shutil.copyfile(p, hd / L.hedef_ad(s))
        hedef.append(dict(sira=s, ad=L.hedef_ad(s), kaynak=p.name if p else "", sha256=shas.get(s, ""), alt=alt[s]))
    rows = [dict(hedef_sira=s, hedef_gorsel=L.hedef_ad(s), hedef_alt=alt[s], islem="DEGISTIR", simdi_sira="", simdi_id="")
            for s in range(1, N_HEDEF + 1)]
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira=x.get("rank"), simdi_id=x.get("listing_image_id"))
             for x in g]
    with open(od / f"LISTE_{lid}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=L.LISTE_ALAN); w.writeheader(); w.writerows(rows)
    man = dict(listing_id=lid, cift=cift, profil="v11",
               variation_images=[dict(value=ad, image_id=RENK_SIRA[ad]) for ad in RENKLER if ad in bag],
               yedek_ids=sorted(x.get("listing_image_id") for x in g), yedek_galeri=[x.get("listing_image_id") for x in g],
               yedek_baglar={ad: dict(property_id=b.get("property_id"), value_id=b.get("value_id"), image_id=b.get("image_id"))
                             for ad, b in sorted(bag.items())},
               hedef=hedef, renk_kapisi=renk, format_boy_sayisi=(d["kart"] or {}).get("format_boy_sayisi"))
    (od / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    return dict(ilan=lid, cift=cift, durum="BLOK" if neden else "HAZIR", neden=neden, liste_sha=Y.sha256(od / f"LISTE_{lid}.csv"),
                renk={ad: dict(sonuc=x["sonuc"], kendi=x.get("kendi"), diger=x.get("diger"), esik=x.get("esik"), ncc=x.get("ncc"))
                      for ad, x in renk.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--ciftler", "--alt", "--galeri-dir", "--kapi-csv", "--kesim-dir", "--yedek-dir", "--yedek-ozet", "--yedek-liste", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--kart-manifest", default="")
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--yazim", action="store_true", help="yazim kosusu: alt metin sablonu ONAYLI olmali")
    ap.add_argument("--is", type=int, default=os.cpu_count() or 2, dest="is_")
    a = ap.parse_args(argv)
    try:
        ilanlar = L.kapsam(a.ciftler, a.sadece, a.haric)
        sab = sablon_oku(a.alt)
        km, kd = kart_oku(a.kart_manifest)
        yozet = L.ozet_oku(a.yedek_ozet)
        yliste = {x["Path"]: int(x.get("Size") or 0) for x in json.loads(Path(a.yedek_liste).read_text(encoding="utf-8"))}
    except (SystemExit, OSError, ValueError, KeyError) as e:
        print(f"::error::{e}"); return 2
    if not ilanlar:
        print("::error::kapsamda ilan yok"); return 2
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    d = dict(yedek=a.yedek_dir, galeri=a.galeri_dir, kesim=a.kesim_dir, out=str(out), yazim=a.yazim, yedek_ozet=yozet, yedek_liste=yliste,
             kapi=kapi_oku(a.kapi_csv), kart=km, kart_dir=str(kd) if kd else "")
    sonuc = []
    with ProcessPoolExecutor(max(1, a.is_)) as ex:
        for n, s in enumerate(ex.map(ilan_hazirla, [dict(satir=r, sablon=sab, dizin=d) for r in ilanlar]), 1):
            sonuc.append(s)
            print(f"[{n}/{len(ilanlar)}] {s['ilan']} {s['cift']} {s['durum']}" + (f": {s['neden'][0][:120]}" if s["neden"] else ""), flush=True)
    alt_durum = sorted({(x.get("durum") or "").strip() for x in sab.values()})
    oz = dict(profil="v11", alt_sablon_durum=alt_durum, alt_sablon_sha=Y.sha256(a.alt), yazim=a.yazim, ncc_min=L.NCC_MIN,
              format_boy_sayisi=(km or {}).get("format_boy_sayisi"), ilanlar={s["ilan"]: s for s in sonuc})
    (out / "LISTE_OZET.json").write_text(json.dumps(oz, indent=1, ensure_ascii=False), encoding="utf-8")
    hazir = sum(1 for s in sonuc if s["durum"] == "HAZIR")
    with open(out / "LISTE_OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Galeri v11 liste\n\nHAZIR {hazir} / BLOK {len(sonuc) - hazir} (ilan {len(sonuc)}) | alt metin sablonu {', '.join(alt_durum)}\n\n")
        f.writelines(f"- {s['ilan']} {s['cift']}: {'; '.join(s['neden'])}\n" for s in sonuc if s["neden"])
    print(f"LISTE OZET: HAZIR {hazir} BLOK {len(sonuc) - hazir} | alt metin {','.join(alt_durum)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
