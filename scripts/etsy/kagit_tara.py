#!/usr/bin/env python3
"""Kagit / tedarikci ifadesi taramasi (Serdar 23 Eki; SALT OKUMA, Etsy'ye yazma YOK). Iki asama (Serdar 23 Eki madde 3):
  --mod oku (Etsy kilidi altinda): magaza duzeyi metin alanlari (GET /shops/{id}, duyuru, satis/tesekkur mesajlari, politika
      alanlari) + bolum adlari + 234 aktif ilanin baslik/etiket/materials/EN aciklama + gorsel alt metinleri. Metin bulgulari
      HEMEN yazilir (KAGIT_METIN.csv); sonra gorseller (570 px CDN kopyasi, kota harcamaz) indirilir (GORSEL/ + GORSEL.json).
      About ve SSS icin v3 API'de okuma ucu yok (/shops/{id}/about denenir, 404 ise "uc yok").
  --mod ocr (kilitsiz, Etsy yok): oku ciktisindaki gorsellerde OCR (tesseract) + eski "Fine Art Paper" kartlarina benzerlik
      (64x64 gri MAE). Her gorsel bitince GORSEL_OCR.csv'ye satir eklenir (dosya her an okunabilir); --sure-dk dolunca yeni
      gorsel baslatilmaz, OCR_OZET.json "yarim" isaretiyle yazilir.
Aranan: Hahnemuhle (OCR hatali yazimlari dahil), Photo Rag, 308, giclee, Prodigi, cotton/pamuk/хлопок, museum/музей,
"fine art paper", ISO 9706."""
import argparse
import concurrent.futures as cf
import csv
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beyan_marka_yaz as B  # noqa: E402

DESEN = re.compile(r"h[a-z]{1,3}em[uü]?h?le|photo\s*rag|\b308\b|gicl[eé]e|жикле|prodigi|cotton|pamuk|хлоп\w*|museum|музе\w*|"
                   r"fine\s*art\s*paper|ISO\s*9706", re.I)
METIN_ALAN = ["kaynak", "listing_id", "alan", "terim", "ornek"]


def bul(metin):
    return sorted({m.group(0).lower() for m in DESEN.finditer(metin or "")})


def metinler(o, yol=""):
    """Sozluk/listedeki tum metin alanlari: (yol, metin)."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from metinler(v, f"{yol}.{k}" if yol else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from metinler(v, f"{yol}[{i}]")
    elif isinstance(o, str):
        yield yol, o


def gri64(b):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(io.BytesIO(b)).convert("L").resize((64, 64)), float)


def ocr(b):
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11", "-l", "eng"], input=b, capture_output=True, timeout=60,
                       env=dict(os.environ, OMP_THREAD_LIMIT="1"))   # 23 Eki dersi: is parcacigi basina tek cekirdek
    return r.stdout.decode("utf-8", "ignore")


class Yazici:
    """Satir satir CSV; her satirdan sonra flush (kosu durursa da dosyada kalir)."""
    def __init__(self, yol, alanlar):
        self.f = open(yol, "w", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=alanlar); self.w.writeheader(); self.f.flush()

    def yaz(self, satir):
        self.w.writerow(satir); self.f.flush()

    def kapat(self):
        self.f.close()


def indir(url, yol):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        yol.write_bytes(r.read())


def oku(a):
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    B.mask(k); B.mask(s)
    store = B.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = B.Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    t0 = time.time()
    yz = Yazici(out / "KAGIT_METIN.csv", METIN_ALAN)
    sayac = {}

    def bulgu(**x):
        yz.yaz(x); sayac[x["kaynak"]] = sayac.get(x["kaynak"], 0) + 1
    gorsel, ilan = [], []
    try:
        dukkan = api.get(f"/shops/{shop}") or {}
        B.kota(api)
        for yol, m in metinler(dukkan):
            for t in bul(m):
                bulgu(kaynak="magaza", listing_id="", alan=yol, terim=t, ornek=m[:160].replace("\n", " "))
        alanlar = sorted(y for y, _ in metinler(dukkan))
        try:
            about = api.get(f"/shops/{shop}/about", ok404=True)
        except Exception:   # noqa: BLE001  v3'te uc yoksa 4xx: tarama durmaz
            about = None
        bolum = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
        for sb in bolum:
            for t in bul(sb.get("title")):
                bulgu(kaynak="magaza", listing_id="", alan="section", terim=t, ornek=sb.get("title"))
        ids = B.aktif_idler(api, shop)
        for i in range(0, len(ids), 100):
            ilan += (api.get("/listings/batch", {"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []
            B.kota(api)
        bol = {str(x["shop_section_id"]): x.get("title") for x in bolum}
        for n, L in enumerate(sorted(ilan, key=lambda x: int(x["listing_id"])), 1):
            lid = str(L["listing_id"]); aile = B.BOLUM_AILE.get(bol.get(str(L.get("shop_section_id"))), "?")
            api.kota_kapisi(f"ilan {lid}")
            for alan in ("title", "description", "tags", "materials"):
                v = L.get(alan)
                for t in bul(" ".join(v) if isinstance(v, list) else v):
                    bulgu(kaynak="ilan", listing_id=lid, alan=alan, terim=t, ornek="")
            imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
            B.kota(api)
            for im in imgs:
                for t in bul(im.get("alt_text")):
                    bulgu(kaynak="alt_metin", listing_id=lid, alan=f"rank {im.get('rank')}", terim=t,
                          ornek=(im.get("alt_text") or "")[:160])
                gorsel.append(dict(listing_id=lid, aile=aile, rank=im.get("rank"), image_id=im.get("listing_image_id"),
                                   url=im.get("url_570xN"), dosya=f"{lid}_{int(im.get('rank') or 0):02d}_{im.get('listing_image_id')}.jpg"))
            if n % 50 == 0:
                el = time.time() - t0
                print(f"[{n}/{len(ilan)}] gecen {el:.0f}s kalan~{el / n * (len(ilan) - n):.0f}s %{100 * n // len(ilan)} | "
                      f"kota {api.remaining}", flush=True)
    except B.Dur as e:
        print(f"DUR: {e} | istek {api.calls} | kota {api.remaining}", flush=True); yz.kapat(); sys.exit(3)
    yz.kapat()
    t_etsy = time.time() - t0
    print(f"ETSY bitti {t_etsy:.0f}s: {len(ilan)} ilan, {len(gorsel)} gorsel | istek {api.calls} | kota {api.remaining}", flush=True)
    (out / "GORSEL.json").write_text(json.dumps(gorsel, ensure_ascii=False, indent=0), encoding="utf-8")
    gd = out / "GORSEL"; gd.mkdir(exist_ok=True)
    hata, t1 = [], time.time()
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        isler = {ex.submit(indir, g["url"], gd / g["dosya"]): g for g in gorsel}
        for n, f in enumerate(cf.as_completed(isler), 1):
            try:
                f.result()
            except Exception as e:   # noqa: BLE001  tek gorsel indirilemezse sayilir
                hata.append(dict(dosya=isler[f]["dosya"], hata=str(e)[:120]))
            if n % 500 == 0:
                print(f"indirme [{n}/{len(gorsel)}] gecen {time.time() - t1:.0f}s", flush=True)
    oz = dict(asama="oku", magaza_alanlari=alanlar, about_ucu="var" if about else "yok (404)", ilan=len(ilan), gorsel=len(gorsel),
              indirilen=len(gorsel) - len(hata), indirme_hata=hata[:20], metin_bulgu=sayac, istek=api.calls, kota=api.remaining,
              sure_etsy_sn=round(t_etsy), sure_indirme_sn=round(time.time() - t1))
    (out / "OKU_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OKU_OZET", json.dumps({k: v for k, v in oz.items() if k != "magaza_alanlari"}, ensure_ascii=False), flush=True)


def gorsel_isle(g, gd, refler):
    b = (gd / g["dosya"]).read_bytes()
    gg = gri64(b)
    mae = {ad: round(float(abs(gg - v).mean()), 2) for ad, v in refler.items()}
    return dict(listing_id=g["listing_id"], aile=g["aile"], rank=g["rank"], image_id=g["image_id"], ocr_bulgu=" ".join(bul(ocr(b))),
                **{f"mae_{k}": v for k, v in mae.items()})


def ocr_mod(a):
    kay, out = pathlib.Path(a.kaynak), pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    gorsel = json.loads((kay / "GORSEL.json").read_text(encoding="utf-8"))
    gd = kay / "GORSEL"
    gorsel = [g for g in gorsel if (gd / g["dosya"]).exists()]
    refler = {pathlib.Path(p).stem: gri64(open(p, "rb").read()) for p in a.ref}
    alan = ["listing_id", "aile", "rank", "image_id", "ocr_bulgu"] + [f"mae_{k}" for k in refler]
    yz = Yazici(out / "GORSEL_OCR.csv", alan)
    t0, son = time.time(), time.time() + a.sure_dk * 60
    isci = a.isci or os.cpu_count() or 2
    sonuc, hata, n = [], 0, 0
    with cf.ThreadPoolExecutor(max_workers=isci) as ex:
        bekleyen, it = set(), iter(gorsel)
        while True:
            while len(bekleyen) < isci and time.time() < son:
                g = next(it, None)
                if g is None:
                    break
                bekleyen.add(ex.submit(gorsel_isle, g, gd, refler))
            if not bekleyen:
                break
            bitti, bekleyen = cf.wait(bekleyen, return_when=cf.FIRST_COMPLETED)
            for f in bitti:
                n += 1
                try:
                    r = f.result(); sonuc.append(r); yz.yaz(r)
                except Exception:   # noqa: BLE001  tek gorsel islenemezse sayilir
                    hata += 1
                if n % 100 == 0:
                    el = time.time() - t0
                    print(f"OCR [{n}/{len(gorsel)}] gecen {el:.0f}s kalan~{el / n * (len(gorsel) - n):.0f}s %{100 * n // len(gorsel)}",
                          flush=True)
    yz.kapat()
    bulgu_ilan = sorted({r["listing_id"] for r in sonuc if r["ocr_bulgu"]})
    terim = {}
    for r in sonuc:
        for t in r["ocr_bulgu"].split(" ") if r["ocr_bulgu"] else []:
            terim[t] = terim.get(t, 0) + 1
    oz = dict(asama="ocr", toplam=len(gorsel), islenen=n, hata=hata, yarim=n < len(gorsel), sure_sn=round(time.time() - t0),
              isci=isci, ocr_bulgu_gorsel=sum(bool(r["ocr_bulgu"]) for r in sonuc), ocr_bulgu_ilan=len(bulgu_ilan),
              ocr_bulgu_ilan_aile={x: len({r["listing_id"] for r in sonuc if r["ocr_bulgu"] and r["aile"] == x})
                                   for x in sorted({r["aile"] for r in sonuc})},
              terim=terim)
    for ad in refler:
        oz[f"en_yakin_{ad}"] = [(x["listing_id"], x["rank"], x[f"mae_{ad}"]) for x in sorted(sonuc, key=lambda x: x[f"mae_{ad}"])[:10]]
    (out / "OCR_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OCR_OZET", json.dumps(oz, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", choices=["oku", "ocr"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kaynak", help="ocr: oku asamasinin cikti klasoru (GORSEL.json + GORSEL/)")
    ap.add_argument("--ref", nargs="*", default=[], help="ocr: eski kart dosyalari (Drive'dan indirilmis)")
    ap.add_argument("--sure-dk", type=float, default=80, help="ocr: bu sureden sonra yeni gorsel baslatilmaz")
    ap.add_argument("--isci", type=int, default=0)
    a = ap.parse_args()
    if a.mod == "oku":
        oku(a)
    else:
        if not a.kaynak:
            raise SystemExit("HATA: ocr icin --kaynak")
        ocr_mod(a)


if __name__ == "__main__":
    main()
