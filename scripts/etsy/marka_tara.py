#!/usr/bin/env python3
"""Marka adi taramasi (Serdar 22 Eki): musteriye gorunen yerde "AstroLove" (Art'siz) gecisleri. SALT OKUMA, yazma YOK.
Marka "AstroLoveArt"; eslesme: harf duyarsiz "astro love" / "astrolove" / "astro-love" ardindan "art" GELMEYEN.
Bir http(s) adresinin icindeki gecis "url" sinifidir (gorunen metin degil), digerleri "metin".

Kaynaklar (alt komut):
  etsy      magaza metin alanlari (GET /shops/{id}); aktif ilanlar (title, description, tags, materials,
            personalization_instructions + sorulari, gorsel alt_text; /listings/batch includes=images,personalization);
            dijital ilan dosya adlari (GET .../files).
            Kota tabani 10 (CLAUDE.md): x-remaining-today < 10 ise DUR.
  metricool PENDING durumundaki (herhangi bir agda) zamanlanmis gonderilerin tum metin alanlari.
  dosya     verilen dizinlerdeki dosya adlari + PDF metni (pdftotext) + ZIP icindeki ad ve PDF metinleri;
            --ad-listesi ile indirilmeyen dosyalarin yalniz adlari.
Cikti: <out>/MARKA_<kaynak>.json (yerler: kaynak, kimlik, alan, sinif, sayi, ornek <= 80 krk) ve log'a yalniz sayilar.
Kullanim: marka_tara.py etsy --out DIR | metricool --token-dosya T.json --out DIR |
          dosya --out DIR --etiket E [--ad-listesi L.txt] [DIZIN ...]"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

MARKA = re.compile(r"astro[\s_-]*love(?![\s_-]*art)", re.I)
URL = re.compile(r"https?://\S+")
KOTA_TABAN = 10


def bul(metin):
    """-> (metin sayisi, url sayisi, ilk ornek)"""
    if not isinstance(metin, str) or not metin:
        return 0, 0, ""
    url_araliklari = [m.span() for m in URL.finditer(metin)]
    n_metin = n_url = 0
    ornek = ""
    for m in MARKA.finditer(metin):
        if any(a <= m.start() < b for a, b in url_araliklari):
            n_url += 1
        else:
            n_metin += 1
            if not ornek:
                ornek = metin[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
    return n_metin, n_url, ornek[:80]


class Kayit:
    def __init__(self, kaynak):
        self.kaynak, self.yerler, self.taranan = kaynak, [], Counter()

    def ekle(self, kimlik, alan, metin):
        self.taranan[alan.split("[")[0]] += 1
        n_m, n_u, ornek = bul(metin)
        if n_m:
            self.yerler.append(dict(kaynak=self.kaynak, kimlik=str(kimlik), alan=alan, sinif="metin", sayi=n_m, ornek=ornek))
        if n_u:
            self.yerler.append(dict(kaynak=self.kaynak, kimlik=str(kimlik), alan=alan, sinif="url", sayi=n_u, ornek=""))

    def yaz(self, out, ek=None):
        oz = dict(kaynak=self.kaynak, taranan=dict(self.taranan),
                  metin_gecis=sum(y["sayi"] for y in self.yerler if y["sinif"] == "metin"),
                  metin_kimlik=len({y["kimlik"] for y in self.yerler if y["sinif"] == "metin"}),
                  alan_basina=dict(Counter(y["alan"].split("[")[0] for y in self.yerler if y["sinif"] == "metin")),
                  url_gecis=sum(y["sayi"] for y in self.yerler if y["sinif"] == "url"), **(ek or {}))
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / f"MARKA_{self.kaynak.upper()}.json").write_text(
            json.dumps(dict(ozet=oz, yerler=self.yerler), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"MARKA {self.kaynak}: taranan {oz['taranan']} | metin gecis {oz['metin_gecis']} ({oz['metin_kimlik']} kimlik) | "
              f"alan {oz['alan_basina']} | url gecis {oz['url_gecis']}" + (f" | {ek}" if ek else ""), flush=True)
        return oz


def kota_dur(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")


def etsy(a):
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop_id = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    magaza = Kayit("magaza")
    shop = api.get(f"/shops/{shop_id}") or {}
    for alan, v in shop.items():
        if isinstance(v, str):
            magaza.ekle("shop", alan, v)
    kota_dur(api)
    ilan = Kayit("ilan")
    ilanlar, off = [], 0
    while True:
        r = api.get(f"/shops/{shop_id}/listings", {"state": "active", "limit": 100, "offset": off}) or {}
        sayfa = r.get("results") or []
        ilanlar += sayfa
        kota_dur(api)
        off += len(sayfa)
        if not sayfa or off >= int(r.get("count") or 0):
            break
    ids = [str(L.get("listing_id")) for L in ilanlar]
    tam = []
    for i in range(0, len(ids), 100):   # by78_denetim kalibi: batch + images, personalization
        tam += (api.get("/listings/batch", {"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,personalization"}) or {}).get("results") or []
        kota_dur(api)
    if len(tam) != len(ids):
        raise SystemExit(f"DUR: batch {len(tam)} ilan dondu, beklenen {len(ids)}")
    ilanlar = tam
    dijital = []
    for L in ilanlar:
        lid = L.get("listing_id")
        for alan in ("title", "description", "personalization_instructions"):
            ilan.ekle(lid, alan, L.get(alan) or "")
        for i, t in enumerate(L.get("tags") or []):
            ilan.ekle(lid, f"tags[{i}]", t)
        for i, t in enumerate(L.get("materials") or []):
            ilan.ekle(lid, f"materials[{i}]", t)
        for i, q in enumerate(L.get("personalization_questions") or L.get("personalization") or []):
            if isinstance(q, dict):
                ilan.ekle(lid, f"kisisellestirme_soru[{i}]", " ".join(str(q.get(k) or "") for k in ("question_text", "instructions")))
        for i, im in enumerate(L.get("images") or []):
            ilan.ekle(lid, f"alt_text[{i}]", im.get("alt_text") or "")
        if L.get("listing_type") in ("download", "both") or L.get("type") == "download" or L.get("is_digital"):
            dijital.append(lid)
    dosya = Kayit("etsy_dosya")
    adlar = Counter()
    for n, lid in enumerate(dijital, 1):
        r = api.get(f"/shops/{shop_id}/listings/{lid}/files", ok404=True) or {}
        for i, f in enumerate(r.get("results") or []):
            ad = f.get("filename") or ""
            adlar[ad] += 1
            dosya.ekle(lid, f"filename[{i}]", ad)
        kota_dur(api)
        if n % 50 == 0 or n == len(dijital):
            print(f"[{n}/{len(dijital)}] dijital ilan dosyalari okundu", flush=True)
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out) / "ETSY_DOSYA_ADLARI.json").write_text(json.dumps(dict(adlar.most_common()), ensure_ascii=False, indent=1),
                                                                encoding="utf-8")
    magaza.yaz(a.out)
    ilan.yaz(a.out, dict(aktif_ilan=len(ilanlar), dijital_ilan=len(dijital)))
    dosya.yaz(a.out, dict(farkli_dosya_adi=len(adlar)))
    print(f"ETSY istek {api.calls} | kota {api.remaining}")


def metricool(a):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "sosyal"))
    from metricool_pin_baslik import MC, TZ, veri
    mc = MC(json.load(open(a.token_dosya)))
    liste = veri(mc.istek("GET", "/v2/scheduler/posts", {"start": a.bas, "end": a.son, "timezone": TZ}))
    if not isinstance(liste, list):
        raise SystemExit(f"DUR: beklenmeyen liste yaniti tipi {type(liste).__name__}")
    kayit = Kayit("metricool")
    bekleyen, ag = 0, Counter()

    def gez(d, yol, kimlik):
        if isinstance(d, dict):
            for k2, v in d.items():
                gez(v, f"{yol}.{k2}" if yol else k2, kimlik)
        elif isinstance(d, list):
            for i, v in enumerate(d):
                gez(v, f"{yol}[{i}]", kimlik)
        elif isinstance(d, str):
            kayit.ekle(kimlik, re.sub(r"\[\d+\]", "", yol), d)

    for p in liste:
        durumlar = [(pr.get("network") or "?", pr.get("status") or "") for pr in p.get("providers") or []]
        if not any(st == "PENDING" for _, st in durumlar):
            continue
        bekleyen += 1
        for n, st in durumlar:
            if st == "PENDING":
                ag[n] += 1
        gez({k2: v for k2, v in p.items() if k2 not in ("providers", "publicationDate", "id", "uuid")}, "", p.get("id"))
    kayit.yaz(a.out, dict(pencere=f"{a.bas}..{a.son}", liste=len(liste), bekleyen=bekleyen, ag=dict(ag)))


def pdf_metin(yol):
    r = subprocess.run(["pdftotext", "-q", str(yol), "-"], capture_output=True, timeout=120)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def dosya(a):
    kayit = Kayit(a.etiket)
    hata = Counter()
    if a.ad_listesi:   # yalniz ad (indirilmeyen dosyalar; rclone lsf -R ciktisi)
        for satir in open(a.ad_listesi, encoding="utf-8"):
            yol = satir.strip()
            if yol and not yol.endswith("/"):
                kayit.ekle(yol, "dosya_adi", pathlib.PurePosixPath(yol).name)
    for kok in a.dizin:
        for p in sorted(pathlib.Path(kok).rglob("*")):
            if not p.is_file():
                continue
            goreli = str(p.relative_to(kok))
            kayit.ekle(goreli, "dosya_adi", p.name)
            uz = p.suffix.lower()
            if uz == ".pdf":
                t = pdf_metin(p)
                if t is None:
                    hata["pdf_okunamadi"] += 1
                else:
                    kayit.ekle(goreli, "pdf_metin", t)
            elif uz == ".zip":
                try:
                    with zipfile.ZipFile(p) as z, tempfile.TemporaryDirectory() as td:
                        for ad in z.namelist():
                            kayit.ekle(f"{goreli}!{ad}", "zip_ic_ad", pathlib.PurePosixPath(ad).name)
                            if ad.lower().endswith(".pdf"):
                                hedef = pathlib.Path(td) / "x.pdf"
                                hedef.write_bytes(z.read(ad))
                                t = pdf_metin(hedef)
                                if t is None:
                                    hata["zip_pdf_okunamadi"] += 1
                                else:
                                    kayit.ekle(f"{goreli}!{ad}", "pdf_metin", t)
                except zipfile.BadZipFile:
                    hata["zip_bozuk"] += 1
    kayit.yaz(a.out, dict(okuma_hatasi=dict(hata)))


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="kaynak", required=True)
    e = alt.add_parser("etsy"); e.add_argument("--out", required=True)
    m = alt.add_parser("metricool"); m.add_argument("--out", required=True); m.add_argument("--token-dosya", required=True)
    m.add_argument("--bas", default="2026-10-22T00:00:00"); m.add_argument("--son", default="2027-06-30T23:59:59")
    d = alt.add_parser("dosya"); d.add_argument("--out", required=True); d.add_argument("--etiket", required=True)
    d.add_argument("--ad-listesi", default="", help="yalniz adlari taranacak yol listesi (satir basina bir yol)")
    d.add_argument("dizin", nargs="*")
    a = ap.parse_args()
    {"etsy": etsy, "metricool": metricool, "dosya": dosya}[a.kaynak](a)


if __name__ == "__main__":
    main()
