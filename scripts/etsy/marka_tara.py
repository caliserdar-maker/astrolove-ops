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

MARKA = re.compile(r"astro[\W_]*love(?![\W_]*art)", re.I)   # \W: bosluk, tire turleri, nokta, sifir genislik
DURUMLAR = ("active", "draft", "inactive", "expired", "sold_out")
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

    def gez(self, kimlik, yol, d):
        """tum alt string degerleri (dict/list) tara; alan adi = yol (indekssiz)"""
        if isinstance(d, dict):
            for k2, v in d.items():
                self.gez(kimlik, f"{yol}.{k2}" if yol else str(k2), v)
        elif isinstance(d, list):
            for v in d:
                self.gez(kimlik, yol, v)
        elif isinstance(d, str):
            self.ekle(kimlik, yol, d)

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
    for alan, v in (api.get(f"/shops/{shop_id}/sections") or {}).items():
        if alan == "results":
            magaza.gez("sections", "sections", v)
    kota_dur(api)
    ilanlar, durum_say = [], Counter()
    for durum in DURUMLAR:
        off = 0
        while True:
            r = api.get(f"/shops/{shop_id}/listings", {"state": durum, "limit": 100, "offset": off}) or {}
            sayfa = r.get("results") or []
            ilanlar += [(durum, L) for L in sayfa]
            durum_say[durum] += len(sayfa)
            kota_dur(api)
            off += len(sayfa)
            if not sayfa or off >= int(r.get("count") or 0):
                break
    tam = {}
    ids = [str(L.get("listing_id")) for _, L in ilanlar]
    for i in range(0, len(ids), 100):   # pod_referans_kiyas kalibi: batch + images, videos, translations, personalization
        for x in (api.get("/listings/batch", {"listing_ids": ",".join(ids[i:i + 100]),
                                              "includes": "images,videos,translations,personalization"}) or {}).get("results") or []:
            tam[str(x.get("listing_id"))] = x
        kota_dur(api)
    if len(tam) != len(ids):
        raise SystemExit(f"DUR: batch {len(tam)} ilan dondu, beklenen {len(ids)}")
    kayitlar, gorseller, tip, ceviri = {}, [], Counter(), Counter()
    dijital = []
    for durum, L0 in ilanlar:
        L = tam[str(L0.get("listing_id"))]
        lid = L.get("listing_id")
        ilan = kayitlar.setdefault(durum, Kayit(f"ilan_{durum}"))
        tip[f"{durum}:{L.get('listing_type')}"] += 1
        for alan in ("title", "description", "personalization_instructions"):
            ilan.ekle(lid, alan, L.get(alan) or "")
        for t_ in L.get("tags") or []:
            ilan.ekle(lid, "tags", t_)
        for t_ in L.get("materials") or []:
            ilan.ekle(lid, "materials", t_)
        ilan.gez(lid, "personalization", L.get("personalization"))
        tr = L.get("translations")
        if isinstance(tr, dict):
            tr = list(tr.values())
        for c in tr or []:
            if isinstance(c, dict):
                dil = c.get("language") or "?"
                ceviri[dil] += 1
                for alan in ("title", "description"):
                    ilan.ekle(lid, f"ceviri_{dil}.{alan}", c.get(alan) or "")
                for t_ in c.get("tags") or []:
                    ilan.ekle(lid, f"ceviri_{dil}.tags", t_)
        for im in L.get("images") or []:
            ilan.ekle(lid, "alt_text", im.get("alt_text") or "")
            if durum == "active" and im.get("url_fullxfull"):
                gorseller.append(dict(kimlik=f"{lid}#{im.get('rank')}", url=im["url_fullxfull"]))
        if L.get("listing_type") in ("download", "both") or L.get("is_digital"):
            dijital.append(lid)
    for alan in ("image_url_760x100", "icon_url_fullxfull"):
        if shop.get(alan):
            gorseller.append(dict(kimlik=f"magaza#{alan}", url=shop[alan]))
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
    (pathlib.Path(a.out) / "GORSEL_LISTE.json").write_text(json.dumps(gorseller, ensure_ascii=False), encoding="utf-8")
    magaza.yaz(a.out)
    print(f"ILAN durum {dict(durum_say)} | listing_type {dict(tip)} | ceviri dili {dict(ceviri)} | dijital {len(dijital)} | "
          f"OCR icin gorsel {len(gorseller)}", flush=True)
    for durum, k in kayitlar.items():
        k.yaz(a.out, dict(ilan=durum_say[durum]))
    dosya.yaz(a.out, dict(farkli_dosya_adi=len(adlar)))
    print(f"ETSY istek {api.calls} | kota {api.remaining}")


def metricool(a):
    """Tum durumlar (yayimlanmis + bekleyen). Pencere parcali: 7 gun; 100+ kayit donerse o hafta gun gun yeniden (k2_link
    olcumu: 5 gunde 100 kayitta kesiliyordu). Ayni id bir kez sayilir."""
    from datetime import datetime, timedelta
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "sosyal"))
    from metricool_pin_baslik import MC, TZ, veri
    mc = MC(json.load(open(a.token_dosya)))
    fmt = "%Y-%m-%dT%H:%M:%S"

    def cek(b, s):
        r = veri(mc.istek("GET", "/v2/scheduler/posts", {"start": b.strftime(fmt), "end": s.strftime(fmt), "timezone": TZ}))
        if not isinstance(r, list):
            raise SystemExit(f"DUR: beklenmeyen liste yaniti tipi {type(r).__name__}")
        return r

    gonderi, parca, gunluk = {}, 0, 0
    b, son = datetime.fromisoformat(a.bas), datetime.fromisoformat(a.son)
    while b < son:
        s = min(b + timedelta(days=7), son)
        r = cek(b, s - timedelta(seconds=1)); parca += 1
        if len(r) >= 100:
            r = []
            g = b
            while g < s:
                gr = cek(g, min(g + timedelta(days=1), s) - timedelta(seconds=1)); gunluk += 1
                if len(gr) >= 100:
                    raise SystemExit(f"DUR: {g:%Y-%m-%d} tek gunde {len(gr)} kayit (kesilme olabilir)")
                r += gr
                g += timedelta(days=1)
        for p in r:
            gonderi[p.get("id") or p.get("uuid") or id(p)] = p
        b = s
    kayit = Kayit("metricool")
    durum = Counter()
    for pid, p in gonderi.items():
        for pr in p.get("providers") or []:
            durum[f"{pr.get('network') or '?'}:{pr.get('status') or '?'}"] += 1
        kayit.gez(pid, "", {k2: v for k2, v in p.items() if k2 not in ("providers", "publicationDate", "id", "uuid", "creationDate",
                                                                     "creatorUserMail")})
    url_alan = Counter(y["alan"] for y in kayit.yerler if y["sinif"] == "url")
    kayit.yaz(a.out, dict(pencere=f"{a.bas}..{a.son}", gonderi=len(gonderi), istek_hafta=parca, istek_gun=gunluk,
                          ag_durum=dict(durum), url_alan=dict(url_alan)))


def gorsel(a):
    """GORSEL_LISTE.json'daki gorseller (Etsy CDN; API kotasi kullanmaz) indirilir, 1600 px'e kucultulur, tesseract ile okunur."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    from PIL import Image
    liste = json.load(open(a.liste))
    kayit = Kayit(a.etiket)
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    td = tempfile.mkdtemp()
    hata = Counter()

    def bir(i_g):
        i, g = i_g
        try:
            ham = pathlib.Path(td) / f"{i}.img"
            with urllib.request.urlopen(urllib.request.Request(g["url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                ham.write_bytes(r.read())
            im = Image.open(ham); im.draft("L", (1600, 1600)); im = im.convert("L"); im.thumbnail((1600, 1600))
            k = pathlib.Path(td) / f"{i}.png"; im.save(k); ham.unlink()
            o = subprocess.run(["tesseract", str(k), "-", "--psm", "11"], capture_output=True, env=env, timeout=120)
            k.unlink()
            return g["kimlik"], " ".join(o.stdout.decode("utf-8", "replace").split())   # tek satir (satir bolunmesi eslesmeyi kirmasin)
        except Exception as e:  # noqa: BLE001
            return g["kimlik"], type(e).__name__

    import time
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        for n, (kim, metin) in enumerate(ex.map(bir, enumerate(liste)), 1):
            if metin in ("HTTPError", "URLError", "TimeoutError", "UnidentifiedImageError", "OSError", "timeout"):
                hata[metin] += 1
            else:
                kayit.ekle(kim, "gorsel_ocr", metin)
            if n % 250 == 0 or n == len(liste):
                g_ = time.time() - t0
                print(f"[{n}/{len(liste)}] %{100 * n // len(liste)} gecen {g_:.0f} sn kalan ~{g_ / n * (len(liste) - n):.0f} sn", flush=True)
    kayit.yaz(a.out, dict(gorsel=len(liste), okuma_hatasi=dict(hata),
                          ilan_basina=len({y["kimlik"].split("#")[0] for y in kayit.yerler if y["sinif"] == "metin"})))


def pdf_metin(yol):
    """metin + metadata (pdfinfo: Title/Author/Subject/Keywords/Creator); eğriye cevrilmis/raster yazi okunmaz."""
    r = subprocess.run(["pdftotext", "-q", str(yol), "-"], capture_output=True, timeout=120)
    if r.returncode != 0:
        return None
    i = subprocess.run(["pdfinfo", str(yol)], capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    meta = " ".join(s for s in i.splitlines() if s.split(":", 1)[0] in ("Title", "Author", "Subject", "Keywords", "Creator"))
    return r.stdout.decode("utf-8", "replace") + "\n" + meta


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
    m.add_argument("--bas", default="2026-08-01T00:00:00"); m.add_argument("--son", default="2027-06-30T23:59:59")
    g = alt.add_parser("gorsel"); g.add_argument("--out", required=True); g.add_argument("--liste", required=True)
    g.add_argument("--etiket", default="gorsel")
    d = alt.add_parser("dosya"); d.add_argument("--out", required=True); d.add_argument("--etiket", required=True)
    d.add_argument("--ad-listesi", default="", help="yalniz adlari taranacak yol listesi (satir basina bir yol)")
    d.add_argument("dizin", nargs="*")
    a = ap.parse_args()
    {"etsy": etsy, "metricool": metricool, "dosya": dosya, "gorsel": gorsel}[a.kaynak](a)


if __name__ == "__main__":
    main()
