#!/usr/bin/env python3
"""YD (1st Anniversary) 78 kapak: yukleyici girdileri (plan v3 adim 6; Merkez 27 Eki). ETSY API YOK, Drive yok: girdiler yerel.
Yukleme scripts/kapak78/yd_kapak_yukle.py (eski78_gorsel_yukle.bir_ilan, YD profili).

kimlik: data/pod/yd78_ids.csv (listing_id, cift, a, b) KAPAK_KAYNAK.csv tur=yd satirlarindan; YD_OZET.csv ile 78/78 ayni olmali
        (ayni listing_id kumesi, ayni cift; 78 tekil cift). Tutmazsa cikis 2, dosya yazilmaz.
liste : ilan basina <out>/<ilan>/LISTE_<ilan>.csv + manifest.json + hedef/01_1.jpg; <out>/LISTE_OZET.json, LISTE_OZET.md, ESLEME.csv.
  LISTE (HAM/<ilan>.json'dan; Serdar 26 Eki aksam: eski kapak yedeklenip silinir, galeri 13):
    sira 1  DEGISTIR 01_1.jpg (KAPAK_<CIFT>.jpg kopyasi), alt metin "<A> and <B> 1st anniversary zodiac print, paper anniversary gift"
    sira 2-13 KORU NN_<simdi_id>.jpg, alt metin HAM'daki gibi aynen (bos olan bos kalir)
    CIKAR   eski kapak (HAM rank 1)
  manifest: variation_images = HAM'daki 5 Style (property 513) bagi aynen (image_id canli kimlik; Botanical -> rank 12 gorseli);
    kapak bagsiz; yedek_ids / yedek_galeri / yedek_baglar (HAM), eski_kapak, botanical_id (KAPAK_KAYNAK kaynak_image_id),
    hedef (yalniz kapak: ad, kaynak, sha256, tasima_sha256, alt), qc (QC_RAPOR.json satiri), yedek_kapak (adim 5 yedegi).
  ESLEME.csv: listing_id, cift, kaynak (KAPAK_<CIFT>.jpg), hedef_gorsel (01_1.jpg), sha256, tasima_sha256, durum.
  Ilan kapilari (biri tutmazsa BLOK; dosyalar yine yazilir, yukleyici BLOK ilana yazmaz):
    HAM: state active, 13 gorsel, rank 1..13 tekil, tekil kimlik, kapak 2400x2400; 5 Style bagi (property 513, 5 ad, 5 farkli
         gorsel, hepsi galeride, kapak bagsiz); Botanical bagli gorsel = KAPAK_KAYNAK kaynak_image_id ve rank 12; envanter Style value_id'leri
         bag value_id'leriyle ayni.
    dosya: KAPAK_<CIFT>.jpg var, JPEG, 2400x2400, sha256 tasima MANIFEST.csv satiriyla ayni (durum YENI / ATLA / MEVCUT).
    QC: QC_RAPOR.json'da dosyanin durumu PASS ve sha256 bu dosyanin sha256'si (adim 4; PASS degilse yukleme yok).
    yedek: adim 5 yedeginin OZET.md satiri PASS / 13 dosya; yedek klasor listesinde 13 r<rank>_<id>.jpg (boyut > 0), eski kapak dahil.
    alt metin: bos degil, <= 250, eski78 YASAK_ALT (tire / yasak ifade / Art'siz marka) yok.
Cikis: 0 (BLOK olsa da; kararlar OZET'te), 2 girdi hatasi."""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import eski78_gorsel_yukle as Y  # noqa: E402

N_HEDEF = 13
STIL_PID = 513
STILLER = ("Starlit", "Timeless", "First Page", "Layers", "Botanical")
BOYUT = (2400, 2400)
KAPAK_AD = "01_1.jpg"          # eski78 hedef_id: NN_<id>.jpg -> 1 (canli kimliklerle cakismaz)
ALT_SABLON = "<A> and <B> 1st anniversary zodiac print, paper anniversary gift"   # Serdar 26 Eki aksam
LISTE_ALAN = ["hedef_sira", "hedef_gorsel", "hedef_alt", "islem", "simdi_sira", "simdi_id"]
ESLEME_ALAN = ["listing_id", "cift", "kaynak", "hedef_gorsel", "sha256", "tasima_sha256", "durum"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def burc(x):
    return x.strip().capitalize()


def kimlik(kaynak, ozet, out):
    rows = [r for r in csv.DictReader(open(kaynak, encoding="utf-8-sig")) if r.get("tur") == "yd"]
    oz = {r["listing_id"]: r["cift"] for r in csv.DictReader(open(ozet, encoding="utf-8-sig"))}
    kk = {r["listing_id"]: r["cift"] for r in rows}
    hata = []
    if len(rows) != 78 or len(kk) != 78:
        hata.append(f"KAPAK_KAYNAK tur=yd {len(rows)} satir / {len(kk)} tekil ilan (78 beklenir)")
    if len(set(kk.values())) != len(kk):
        hata.append("KAPAK_KAYNAK tur=yd ciftleri tekil degil")
    if set(kk) != set(oz):
        hata.append(f"YD_OZET ilan kumesi farkli (+{sorted(set(oz) - set(kk))[:5]} -{sorted(set(kk) - set(oz))[:5]})")
    fark = [lid for lid in kk if lid in oz and oz[lid] != kk[lid]]
    if fark:
        hata.append(f"YD_OZET cifti farkli: {fark[:5]}")
    if any(len(c.split("_")) != 2 for c in kk.values()):
        hata.append("cift adi <A>_<B> degil")
    if hata:
        for h in hata:
            print(f"::error::{h}")
        return 2
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"])
        for lid, c in sorted(kk.items(), key=lambda x: x[1]):
            a, b = c.split("_"); w.writerow([lid, c, burc(a), burc(b)])
    print(f"KIMLIK: {len(kk)} ilan -> {out} (KAPAK_KAYNAK tur=yd = YD_OZET 78/78)")
    return 0


def alt_metin(a, b):
    return " ".join(ALT_SABLON.replace("<A>", a.strip()).replace("<B>", b.strip()).split())


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
        return f"boyut {bt[0]}x{bt[1]} != 2400x2400"
    return ""


def stil_degerleri(inv):
    """envanter -> {stil adi: value_id} (property 513; Format 514 disarida). Bir ad iki farkli value_id ise None."""
    out = {}
    for pr in (inv or {}).get("products") or []:
        for pv in pr.get("property_values") or []:
            if pv.get("property_id") != STIL_PID:
                continue
            for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                if out.get(val, vid) != vid:
                    out[val] = None
                else:
                    out[val] = vid
    return out


def ham_kapisi(h, botanical_id):
    """-> (gorseller rank sirali, baglar {stil: bag}, neden listesi)"""
    neden = []
    L = h.get("listing") or {}
    if L.get("state") != "active":
        neden.append(f"HAM state {L.get('state')} (active degil)")
    g = sorted(h.get("images") or [], key=lambda x: x.get("rank") or 0)
    ids = [x.get("listing_image_id") for x in g]
    if len(g) != N_HEDEF or len(set(ids)) != N_HEDEF:
        neden.append(f"HAM galeri {len(g)} gorsel / {len(set(ids))} tekil (13 beklenir)")
    if [x.get("rank") for x in g] != list(range(1, len(g) + 1)):
        neden.append(f"HAM rank 1..{len(g)} tekil/artan degil")
    if g and (g[0].get("full_width"), g[0].get("full_height")) != BOYUT:
        neden.append(f"HAM kapak {g[0].get('full_width')}x{g[0].get('full_height')} (2400x2400 beklenir)")
    bag = {}
    for b in h.get("variation_images") or []:
        if b.get("property_id") != STIL_PID or b.get("value") not in STILLER or b.get("value") in bag:
            neden.append(f"HAM bag gecersiz ({b.get('property_id')}, {b.get('value')})"); continue
        bag[b["value"]] = b
    if sorted(bag) != sorted(STILLER):
        neden.append(f"HAM'da {len(bag)} Style bagi (5 beklenir)")
    bimg = [b.get("image_id") for b in bag.values()]
    if len(set(bimg)) != len(bimg):
        neden.append("HAM'da bir gorsel birden fazla stile bagli")
    if any(i not in ids for i in bimg):
        neden.append("HAM'da bagli gorsel galeride yok")
    if g and g[0].get("listing_image_id") in bimg:
        neden.append("HAM kapak (rank 1) bagli (bagsiz beklenir)")
    if str((bag.get("Botanical") or {}).get("image_id")) != str(botanical_id):
        neden.append(f"Botanical bagli gorsel {(bag.get('Botanical') or {}).get('image_id')} != KAPAK_KAYNAK {botanical_id}")
    bot_rank = next((x.get("rank") for x in g if x.get("listing_image_id") == (bag.get("Botanical") or {}).get("image_id")), None)
    if bot_rank != 12:
        neden.append(f"Botanical bagli gorsel rank {bot_rank} (12 beklenir; Serdar 15 / 26 Eki)")
    sv = stil_degerleri(h.get("inventory"))
    for ad, b in bag.items():
        if sv.get(ad) != b.get("value_id"):
            neden.append(f"envanter Style degeri ({ad}) bag value_id ile ayni degil")
    return g, bag, neden


def ozet_oku(p):
    out = {}
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0].isdigit():
            out[c[0]] = c
    return out


def yedek_kapisi(lid, cift, g, ozet, liste):
    neden = []
    row = ozet.get(lid)
    if not row or row[1] != cift or row[3] != "PASS" or row[2] != str(N_HEDEF):
        neden.append(f"yedek OZET.md satiri PASS / 13 dosya degil ({'yok' if not row else '|'.join(row[1:4])})")
    eksik = [x for x in g if (liste.get(f"{lid}_{cift}/r{x.get('rank')}_{x.get('listing_image_id')}.jpg") or 0) <= 0]
    if eksik:
        neden.append(f"yedekte {len(eksik)} gorsel dosyasi yok / bos (r{', r'.join(str(x.get('rank')) for x in eksik[:5])})")
    eski = g[0] if g else None
    yk = None
    if eski is not None:
        yol = f"{lid}_{cift}/r1_{eski.get('listing_image_id')}.jpg"
        if (liste.get(yol) or 0) > 0:
            yk = dict(id=eski.get("listing_image_id"), yol=yol, boyut=liste[yol])
        else:
            neden.append("yedekte eski kapak yok")
    return neden, yk


def qc_oku(p):
    j = json.loads(Path(p).read_text(encoding="utf-8"))
    return {x["dosya"]: x for x in j.get("dosyalar") or []}, j


def ilan_hazirla(r, d):
    lid, cift = r["listing_id"], r["cift"]
    neden = []
    hp = Path(d["ham"]) / f"{lid}.json"
    if not hp.exists():
        return dict(ilan=lid, cift=cift, durum="BLOK", neden=[f"HAM/{lid}.json yok"])
    h = json.loads(hp.read_text(encoding="utf-8"))
    if str((h.get("listing") or {}).get("listing_id")) != lid:
        neden.append("HAM listing_id dosya adiyla ayni degil")
    bot = d["kaynak"].get(lid)
    g, bag, n_ = ham_kapisi(h, bot); neden += n_
    yn, yk = yedek_kapisi(lid, cift, g, d["yedek_ozet"], d["yedek_liste"]); neden += yn
    kaynak_ad = f"KAPAK_{cift}.jpg"
    kp = Path(d["kapak"]) / kaynak_ad
    e = jpeg_kontrol(kp)
    if e:
        neden.append(f"{kaynak_ad}: {e}")
    s_ = sha(kp) if kp.exists() else ""
    m = d["tasima"].get(kaynak_ad) or {}
    t_sha = m.get("sha256", "")
    if not m or not (m.get("durum") or "").startswith(("YENI", "ATLA", "MEVCUT")):
        neden.append(f"tasima MANIFEST'te {kaynak_ad} gecerli satir yok ({(m.get('durum') or 'yok')[:40]})")
    elif s_ and t_sha != s_:
        neden.append(f"{kaynak_ad} sha256 tasima MANIFEST ile ayni degil")
    q = d["qc"].get(kaynak_ad)
    if not q or q.get("durum") != "PASS":
        neden.append(f"QC_RAPOR {kaynak_ad}: {(q or {}).get('durum', 'yok')} (PASS degil; yukleme yok)")
    elif not s_ or q.get("sha256") != s_:      # QC PASS bu baytlara ait olmali (inceleme 27 Eki: yeniden aktarilan kapak QC'siz gecerdi)
        neden.append(f"QC_RAPOR {kaynak_ad} PASS baska dosyaya ait (sha256 farkli); QC yeniden kosulmali")
    alt = alt_metin(r["a"], r["b"])
    if not alt or len(alt) > 250 or Y.YASAK_ALT.search(alt):
        neden.append("kapak alt metni gecersiz (bos / >250 / yasak ifade / tire)")
    for x in g[1:]:
        t = x.get("alt_text") or ""
        if len(t) > 250 or Y.YASAK_ALT.search(t):
            neden.append(f"HAM rank {x.get('rank')} alt metni yasak ifade / >250 (sira geciste aynen geri gonderilir)")
    od = Path(d["out"]) / lid; hd = od / "hedef"
    if od.exists():
        shutil.rmtree(od)
    hd.mkdir(parents=True)
    if kp.exists():
        shutil.copyfile(kp, hd / KAPAK_AD)
    rows = [dict(hedef_sira=1, hedef_gorsel=KAPAK_AD, hedef_alt=alt, islem="DEGISTIR", simdi_sira="", simdi_id="")]
    rows += [dict(hedef_sira=x.get("rank"), hedef_gorsel=f"{x.get('rank'):02d}_{x.get('listing_image_id')}.jpg",
                  hedef_alt=x.get("alt_text") or "", islem="KORU", simdi_sira=x.get("rank"), simdi_id=x.get("listing_image_id"))
             for x in g[1:]]
    if g:
        rows.append(dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira=1, simdi_id=g[0].get("listing_image_id")))
    with open(od / f"LISTE_{lid}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LISTE_ALAN); w.writeheader(); w.writerows(rows)
    yb = {ad: dict(property_id=b.get("property_id"), value_id=b.get("value_id"), image_id=b.get("image_id")) for ad, b in sorted(bag.items())}
    man = dict(listing_id=lid, cift=cift, a=r["a"], b=r["b"],
               variation_images=[dict(value=ad, image_id=b["image_id"], property_id=b["property_id"], value_id=b["value_id"])
                                 for ad, b in yb.items()],
               yedek_ids=sorted(x.get("listing_image_id") for x in g), yedek_galeri=[x.get("listing_image_id") for x in g],
               yedek_alt=[x.get("alt_text") or "" for x in g], yedek_baglar=yb,
               eski_kapak=g[0].get("listing_image_id") if g else None, botanical_id=int(bot) if str(bot or "").isdigit() else None,
               hedef=[dict(sira=1, ad=KAPAK_AD, kaynak=kaynak_ad, sha256=s_, tasima_sha256=t_sha, alt=alt)],
               qc=q or {}, yedek_kapak=yk, ham_sha=sha(hp))
    (od / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    es = dict(listing_id=lid, cift=cift, kaynak=kaynak_ad, hedef_gorsel=KAPAK_AD, sha256=s_, tasima_sha256=t_sha,
              durum="PASS" if s_ and s_ == t_sha else "FAIL")
    return dict(ilan=lid, cift=cift, durum="BLOK" if neden else "HAZIR", neden=neden, liste_sha=Y.sha256(od / f"LISTE_{lid}.csv"),
                esleme=es)


def liste(a):
    try:
        ilanlar = [r for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("listing_id")]
        kaynak = {r["listing_id"]: r["kaynak_image_id"] for r in csv.DictReader(open(a.kaynak, encoding="utf-8-sig")) if r.get("tur") == "yd"}
        qc, qj = qc_oku(a.qc)
        tasima = {r["ad"]: r for r in csv.DictReader(open(Path(a.kapak_dir) / "MANIFEST.csv", encoding="utf-8"))}
        yozet = ozet_oku(a.yedek_ozet)
        yliste = {x["Path"]: int(x.get("Size") or 0) for x in json.loads(Path(a.yedek_liste).read_text(encoding="utf-8"))}
    except (SystemExit, OSError, ValueError, KeyError) as e:
        print(f"::error::{e}"); return 2
    s = {x.strip() for x in a.sadece.split(",") if x.strip()}
    if s - {r["listing_id"] for r in ilanlar}:
        print(f"::error::sadece: listede olmayan ilan {sorted(s - {r['listing_id'] for r in ilanlar})}"); return 2
    ilanlar = [r for r in ilanlar if not s or r["listing_id"] in s]
    if not ilanlar:
        print("::error::kapsamda ilan yok"); return 2
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    d = dict(ham=a.ham_dir, kapak=a.kapak_dir, out=str(out), kaynak=kaynak, qc=qc, tasima=tasima, yedek_ozet=yozet, yedek_liste=yliste)
    sonuc = []
    for n, r in enumerate(ilanlar, 1):
        x = ilan_hazirla(r, d); sonuc.append(x)
        print(f"[{n}/{len(ilanlar)}] {x['ilan']} {x['cift']} {x['durum']}" + (f": {x['neden'][0][:120]}" if x["neden"] else ""), flush=True)
    with open(out / "ESLEME.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ESLEME_ALAN); w.writeheader(); w.writerows(x["esleme"] for x in sonuc if x.get("esleme"))
    oz = dict(urun="yd", n_hedef=N_HEDEF, alt_sablon=ALT_SABLON, qc_sha=Y.sha256(a.qc), qc_esik=qj.get("esik"),
              tasima_sha=Y.sha256(Path(a.kapak_dir) / "MANIFEST.csv"), yazim=True,
              ilanlar={x["ilan"]: {k: v for k, v in x.items() if k != "esleme"} for x in sonuc})
    (out / "LISTE_OZET.json").write_text(json.dumps(oz, indent=1, ensure_ascii=False), encoding="utf-8")
    hazir = sum(1 for x in sonuc if x["durum"] == "HAZIR")
    with open(out / "LISTE_OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# YD kapak liste\n\nHAZIR {hazir} / BLOK {len(sonuc) - hazir} (ilan {len(sonuc)}) | alt metin: {ALT_SABLON}\n\n")
        f.writelines(f"- {x['ilan']} {x['cift']}: {'; '.join(x['neden'])}\n" for x in sonuc if x["neden"])
    print(f"LISTE OZET: HAZIR {hazir} BLOK {len(sonuc) - hazir}", flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="komut", required=True)
    k = sub.add_parser("kimlik")
    k.add_argument("--kaynak", required=True, help="docs/yd_kapak/KAPAK_KAYNAK.csv")
    k.add_argument("--ozet", required=True, help="YD_OZET.csv (TEMP/YD_ENVANTER_20261026)")
    k.add_argument("--out", required=True, help="data/pod/yd78_ids.csv")
    li = sub.add_parser("liste")
    for x in ("--ciftler", "--kaynak", "--ham-dir", "--kapak-dir", "--qc", "--yedek-ozet", "--yedek-liste", "--out"):
        li.add_argument(x, required=True)
    li.add_argument("--sadece", default="")
    a = ap.parse_args(argv)
    if a.komut == "kimlik":
        return kimlik(a.kaynak, a.ozet, a.out)
    return liste(a)


if __name__ == "__main__":
    sys.exit(main())
