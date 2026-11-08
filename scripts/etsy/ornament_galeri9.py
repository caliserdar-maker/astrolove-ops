#!/usr/bin/env python3
"""ORNAMENT 78 TASLAK: galeri degisimi v9 (Serdar 7-8 Kas: "Evet, degistir" + "5 stil gorseli uretilecek" + "Gevsetme: 78 gece").
Eski 11 gorsel (01 kapak, 02-06 kart, 07-11 stil) + eski video -> yeni 14 gorsel + yeni video. Stil secimi (Style) yeni 10-14'e baglanir.
YAYIN YOK: updateListing (PATCH) yalniz acil state=inactive. Yalniz o taslagin gorsel / video / variation-images uclari; DELETE yalniz
YEDEK'teki eski gorsel ve video id'leri.

--mod yedek : SALT OKUMA. Her cift: ilan (state, baslik), gorseller (id, sira, alt, url), videolar, variation-images, envanter Style
              value_id. Cikti OUT/YEDEK9.json (yazimdan once zorunlu; eski gorsel dosyalari Drive galeri78 klasorunde).
--mod kuru  : AG YOK, TOKEN YOK. yaz() ile ayni kod yolu, Etsy YEDEK9.json'dan bellekte taklit; istekler OUT/kuru/KURU_<CIFT>.json.
--mod yaz   : cift basina: (1) eski 01-06 silinir (stile bagli 5 eski gorsel kalir) (2) yeni 14 gorsel sira 1..14, alt metinli
              (3) Style -> yeni 10-14 (4) eski 5 stil gorseli silinir (5) eski video silinir, yeni video (6) tam geri okuma.
              Her adimdan sonra state okunur; "active" -> aninda inactive + DUR. Ilan durumu OUT/DURUM9.json (kaldigi yerden devam).
Medya: IMG_ROOT/<CIFT>/<CIFT>_01_KAPAK.jpg ... _14_IVORY.jpg, <CIFT>_VIDEO.mp4, <CIFT>_OLCUM.json (sonuc PASS; uret_cift.py v9).
Ilan id: TASLAK_DURUM (Drive TEMP/ORNAMENT_TASLAK/DURUM.json "ciftler"). Metin: data/pod/ORNAMENT78_METIN.csv (baslik kimligi + alt).
"""
import argparse
import csv
import html
import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, Etsy, TokenStore, ai_beyan_kapisi, mask, metin_yasak_kapisi  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10
BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
CIFTLER = sorted("_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2))
P_STYLE = 513
STIL_SIRA = {"Ruby": 10, "Sapphire": 11, "Emerald": 12, "White": 13, "Ivory": 14}
# Serdar 8 Kas: sembol karti 2. sirada ("bizi rakiplerden ayiran en degerli sey ozgun tasarimimiz"; "Evet, bu sirayla").
# Dosya adlari uretimdeki gibi kalir (06_SEMBOL), Etsy sirasi bu listedir.
GALERI = ["01_KAPAK", "06_SEMBOL", "02_AGAC", "03_ELLER", "04_STILLER", "05_KISISEL", "07_BOYUT", "08_SUREC", "09_YILBOYU",
          "10_RUBY", "11_SAPPHIRE", "12_EMERALD", "13_WHITE", "14_IVORY"]
ESKI_GALERI9 = ["01_KAPAK", "02_AGAC", "03_ELLER", "04_STILLER", "05_KISISEL", "06_SEMBOL", "07_BOYUT", "08_SUREC", "09_YILBOYU",
                "10_RUBY", "11_SAPPHIRE", "12_EMERALD", "13_WHITE", "14_IVORY"]          # pilot CANCER_LIBRA bu sirayla yazildi
SIRA_DEG = [n for n in range(1, 15) if GALERI[n - 1] != ESKI_GALERI9[n - 1]]            # 2..6
if os.environ.get("SEMBOL_KARTI") == "1":       # 8 Kas: sembol karti galeride 2. sirada (06_SEMBOL); 15. gorsel secenegi kapandi
    raise SystemExit("DUR: SEMBOL_KARTI=1 kapandi (sembol karti 2. sirada, Serdar 8 Kas)")
N_YENI = len(GALERI)
ESKI_N = 11                     # ornament_taslak.py N_GORSEL
ESKI_STIL_SIRA = {"Ruby": 7, "Sapphire": 8, "Emerald": 9, "White": 10, "Ivory": 11}
KOTA_ILAN = 70                  # ilan basina istek: kuru 46, en kotu (geri okuma + video bekleme + tekrarlar) ~70; + 10 kapida: ilan yarim birakilmaz (CLAUDE.md Etsy 3)
PARTI_MAX = 20                  # tek kosuda en fazla cift (CLAUDE.md KILIT SURESI)
SURE_DK = 60                    # kilit anindan sonra yeni cifte baslanmaz
TIRE = re.compile("[–—]")


# ------------------------------------------------------------------ metin
def metin(pair):
    rows = [r for r in csv.DictReader(open(KOK / "data" / "pod" / "ORNAMENT78_METIN.csv", encoding="utf-8")) if r["kod"] == pair]
    if len(rows) != 1:
        raise SystemExit(f"DUR-ON: METIN {pair} satiri {len(rows)}")
    return rows[0]


def alt_metinler(pair):
    """14 alt metin (Serdar 8 Kas "Evet, sen yaz"): mevcut onayli alt_01..alt_11 yeni siraya, 02 / 03 / 09 yeni (ayni kalip)."""
    r = metin(pair)
    a, b = pair.split("_")
    A, B, BAS = a.capitalize(), b.capitalize(), f"{a} & {b}"
    yeni2 = f"{BAS} on the Tree: {A} and {B} zodiac couple ornament in Ruby hanging on a Christmas tree, shown with sample names and date"
    yeni3 = f"{BAS} Ornament for Two: {A} and {B} zodiac couple ornament in Ruby held by a couple, shown with sample names and date"
    yeni9 = (f"{BAS} All Year Round: {A} and {B} zodiac couple ornament in Ruby on a bedside table, shown with sample names and date, "
             f"display stand not included")
    dosya_alt = {"01_KAPAK": r["alt_01"], "02_AGAC": yeni2, "03_ELLER": yeni3, "04_STILLER": r["alt_06"], "05_KISISEL": r["alt_03"],
                 "06_SEMBOL": r["alt_02"], "07_BOYUT": r["alt_04"], "08_SUREC": r["alt_05"], "09_YILBOYU": yeni9,
                 "10_RUBY": r["alt_07"], "11_SAPPHIRE": r["alt_08"], "12_EMERALD": r["alt_09"], "13_WHITE": r["alt_10"], "14_IVORY": r["alt_11"]}
    alt = [dosya_alt[x] for x in GALERI if x in dosya_alt]
    hata = []
    if any(not x or len(x) > 250 for x in alt):
        hata.append("alt metin bos ya da > 250")
    if TIRE.search("\n".join(alt)):
        hata.append("uzun/orta tire")
    if re.search(r"\b(?:Lena|Serdar)\b", "\n".join(alt), re.I):
        hata.append("kisi adi")
    for stil, rk in STIL_SIRA.items():
        if f"{stil.upper()} STYLE" not in alt[rk - 1].upper():
            hata.append(f"alt {rk} stil {stil} degil")
    if "TWO SIGNS, ONE SHARED SYMBOL" not in alt[1].upper():
        hata.append("alt 2 sembol karti degil")
    try:
        metin_yasak_kapisi("POST", "/shops/0/listings/0/images", data={f"alt_{i}": x for i, x in enumerate(alt, 1)}, mod="ENGEL")
    except SystemExit as e:
        hata.append(str(e.code)[:200])
    return alt, html.unescape(r["baslik"]), hata


def medya(pair):
    kok = Path(os.environ["IMG_ROOT"]) / pair
    g = [kok / f"{pair}_{d}.jpg" for d in GALERI]
    v = kok / f"{pair}_VIDEO.mp4"
    hata = [p.name for p in g + [v] if not p.exists()]
    o = kok / f"{pair}_OLCUM.json"
    if not o.exists() or json.load(open(o)).get("sonuc") != "PASS":
        hata.append("OLCUM PASS degil")
    if not hata and os.environ.get("BOYUT_KAPI", "1") == "1":     # inceleme 10: boyut yazimdan ONCE
        from PIL import Image
        kotu = [p.name for p in g if Image.open(p).size != (3000, 2250)]
        if kotu:
            hata.append(f"boyut 3000x2250 degil {kotu}")
    return g, v, hata


# ------------------------------------------------------------------ api
class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


class Kilitli(Etsy):
    """Izinli yazmalar: YALNIZ api.lid taslaginin gorsel / video / variation-images uclari; DELETE yalniz api.sil_izin id'leri.
    PATCH yalniz acil state=inactive."""
    lid = None
    sil_izin = frozenset()
    vid_izin = frozenset()
    yalniz_gorsel = False          # sira modu: video ve variation-images yazimi yasak (inceleme 4)
    video_yasak = False            # yeniden modu: video yazimi yasak

    def _izin(self, method, path):
        L = self.lid
        if not L:
            raise SystemExit(f"YASAK yazma (ilan yok): {method} {path}")
        ok = [("POST", rf"^/shops/\d+/listings/{L}/images$"), ("POST", rf"^/shops/\d+/listings/{L}/videos$"),
              ("POST", rf"^/shops/\d+/listings/{L}/variation-images$"), ("PATCH", rf"^/shops/\d+/listings/{L}$")]
        m = re.match(rf"^/shops/\d+/listings/{L}/images/(\d+)$", path)
        if method == "DELETE" and m:
            if int(m.group(1)) not in self.sil_izin:
                raise SystemExit(f"YASAK: yedekte olmayan gorsel silme {path}")
            return
        m = re.match(rf"^/shops/\d+/listings/{L}/videos/(\d+)$", path)
        if method == "DELETE" and m:
            if int(m.group(1)) not in self.vid_izin:
                raise SystemExit(f"YASAK: yedekte olmayan video silme {path}")
            return
        if not any(mm == method and re.match(p, path) for mm, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")
        if self.yalniz_gorsel and method == "POST" and (path.endswith("/videos") or path.endswith("/variation-images")):
            raise SystemExit(f"YASAK (sira modu): {method} {path}")
        if self.video_yasak and "/videos" in path:
            raise SystemExit(f"YASAK (yeniden modu): {method} {path}")

    def _call(self, method, path, **kw):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and kw.get("data") != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        r = super()._call(method, path, **kw)
        self.kota()
        return r

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        r = super().post_file(path, files, data, tekrar=1)       # tekrar yok: hata yanitinda cift yukleme riski; cagiran galeriyi okur
        self.kota()
        return r

    def kota(self, esik=KOTA_MIN):
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < esik:
            raise SystemExit(f"DUR: kota {self.remaining} < {esik}")


# ------------------------------------------------------------------ yedek
def ilan_oku(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
    inv = api.get(f"/listings/{lid}/inventory") or {}
    stil = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
            if v.get("property_id") == P_STYLE and v.get("value_ids")}
    return dict(listing_id=lid, state=L.get("state"), baslik=html.unescape(L.get("title") or ""),
                gorsel=[dict(id=x.get("listing_image_id"), rank=x.get("rank"), alt=x.get("alt_text"), w=x.get("full_width"),
                             h=x.get("full_height"), url=x.get("url_fullxfull")) for x in ims],
                video=[dict(id=v.get("video_id"), state=v.get("video_state"), url=v.get("video_url")) for v in vids],
                bag={str(v.get("value_id")): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}, stil=stil)


def yedek(api, shop, out, ciftler, lid_harita):
    """inceleme 6: var olan YEDEK9 kaydi EZILMEZ (yazim basladiktan sonra eski id'ler kaybolmasin); yalniz eksik ciftler eklenir."""
    onceki = json.load(open(os.environ["YEDEK_ONCEKI"])) if os.environ.get("YEDEK_ONCEKI") and Path(os.environ["YEDEK_ONCEKI"]).exists() else {}
    Y = dict(onceki)
    ciftler = [c for c in ciftler if c not in onceki or onceki[c].get("hata")]
    print(f"yedek: onceki {len(onceki)} cift korunur, okunacak {len(ciftler)}")
    t0 = time.time()
    for n, c in enumerate(ciftler, 1):
        lid = lid_harita.get(c)
        if not str(lid).isdigit():
            Y[c] = dict(hata=f"listing id yok ({lid})"); continue
        Y[c] = ilan_oku(api, shop, int(lid))
        g = time.time() - t0
        print(f"yedek [{n}/{len(ciftler)}] {c} {lid} {Y[c]['state']} gorsel {len(Y[c]['gorsel'])} video {len(Y[c]['video'])} | gecen {g:.0f} sn | "
              f"kalan ~{g / n * (len(ciftler) - n):.0f} sn | %{100 * n // len(ciftler)} | kota {api.remaining}", flush=True)
    json.dump(Y, open(out / "YEDEK9.json", "w"), indent=1, ensure_ascii=False)
    ok = {c: (y.get("state") == "draft" and len(y.get("gorsel", [])) == ESKI_N and len(y.get("video", [])) == 1
              and sorted(y.get("stil", {})) == sorted(STIL_SIRA)) for c, y in Y.items()}
    print(f"::warning::YEDEK {len(Y)} cift | beklenen yapida (draft, 11 gorsel, 1 video, 5 stil) {sum(ok.values())} | "
          f"farkli {[c for c, v in ok.items() if not v]} | kota {api.remaining}")
    return Y


# ------------------------------------------------------------------ yaz
def yaz(api, shop, out, pair, Y):
    """Tek ilan. Her hata DUR (SystemExit). DURUM9[pair]: yeni{sira:id}, video_gonderildi, tamam."""
    R = {"cift": pair, "adimlar": []}
    durum_f = out / "DURUM9.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    d = D.setdefault("ciftler", {}).setdefault(pair, {"yeni": {}})
    rapor_f = out / f"G9_{pair}.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    alt, baslik, hata = alt_metinler(pair)
    galeri, video, mh = medya(pair)
    if hata or mh:
        kaydet(); raise SystemExit(f"DUR-ON: {pair} metin {hata} medya {mh}")
    y = Y.get(pair) or {}
    if not y.get("gorsel") or not str(y.get("listing_id", "")).isdigit():
        kaydet(); raise SystemExit(f"DUR-ON: {pair} yedek yok")
    lid = int(y["listing_id"])
    eski = [g["id"] for g in sorted(y["gorsel"], key=lambda g: g["rank"])]
    eski_v = [v["id"] for v in y["video"]]
    if y.get("state") != "draft" or len(eski) != ESKI_N or len(eski_v) != 1 or sorted(y.get("stil", {})) != sorted(STIL_SIRA):
        kaydet(); raise SystemExit(f"DUR-ON: {pair} yedek yapisi beklenmeyen (gorsel {len(eski)}, video {len(eski_v)}, stil {sorted(y.get('stil', {}))})")
    eski_bag = {str(y["stil"][s]): eski[r - 1] for s, r in ESKI_STIL_SIRA.items()}
    if y["bag"] != eski_bag:
        kaydet(); raise SystemExit(f"DUR-ON: {pair} yedekte stil baglari 7-11 degil {y['bag']}")
    api.lid, api.sil_izin, api.vid_izin = lid, frozenset(eski), frozenset(eski_v)
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    api.kota(KOTA_ILAN + 10)

    def state_oku(adim, acil=True):
        L = None
        for i in range(6):
            L = api.get(f"/listings/{lid}", ok404=True)
            if L:
                break
            time.sleep(5 * (i + 1))
        if not L:
            kaydet(); raise SystemExit(f"DUR: /listings/{lid} okunamadi ({adim})")
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active" and not acil:            # inceleme 3: yazimdan ONCE active = Serdar yayina almis olabilir; dokunulmaz
            kaydet(); raise SystemExit(f"DUR: {pair} {lid} active ({adim}); dokunulmadi")
        if st == "active":
            st2, gitti = "?", False
            try:
                api.patch(f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
                gitti = True
                st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            except BaseException as e:  # noqa: BLE001
                st2 = f"{'PATCH gitti, okuma' if gitti else 'PATCH gonderilemedi'} hatasi {type(e).__name__}: {str(e)[:200]}"
            finally:
                R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
                print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive (simdi {st2}). DUR.", flush=True)
                if st2 != "inactive":
                    print(f"::error::ACIL BASARISIZ: {pair} listing {lid} hala {st2}; Etsy panelinden elle inactive yapilmali.", flush=True)
                raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: {pair} state {st} ({adim}); dokunulmadi")
        return L

    def gorseller():
        return sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)

    L = state_oku("0 baslangic", acil=False)
    if html.unescape(L.get("title") or "") != baslik:
        kaydet(); raise SystemExit(f"DUR: {pair} {lid} baslik METIN ile ayni degil (kimlik)")
    if not getattr(api, "kuru", False) and pair != "CANCER_LIBRA" and not ("CANCER_LIBRA" in D.get("tamam", [])
                                                                           and "CANCER_LIBRA" in D.get("sira_v2", [])):
        kaydet(); raise SystemExit("DUR: CANCER_LIBRA pilotu tamam degil (yeni sira dahil); once pilot")   # pilot once (inceleme 9; kuru haric)
    v0 = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    yabanci = [v.get("video_id") for v in v0 if v.get("video_id") not in eski_v and not d.get("video_gonderildi")]
    if yabanci:
        kaydet(); raise SystemExit(f"DUR: {pair} yedekte olmayan video {yabanci} (elle kontrol)")
    ims = gorseller()
    yeni = {int(k): v for k, v in d["yeni"].items()}
    if yeni and d.get("sira") != "v2":                 # inceleme 8: eski sirayla (sembol karti 6.) yarim kalmis cift
        kaydet(); raise SystemExit(f"DUR: {pair} DURUM9'da eski sirayla yarim yazim var (elle kontrol)")
    d["sira"] = "v2"
    simdi = [x["listing_image_id"] for x in ims]
    bilinmeyen = [i for i in simdi if i not in eski and i not in yeni.values()]
    if bilinmeyen:
        kaydet(); raise SystemExit(f"DUR: {pair} galeride bilinmeyen gorsel {bilinmeyen} (onceki kosu yarida? elle kontrol)")
    # 1) eski 01-06 (stile bagli degil) silinir
    for i in eski[:6]:
        if i in simdi:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    state_oku("1 eski 01-06 silindi")
    # 2) yeni 14 gorsel, sira 1..14 (eksik olanlar); her yuklemeden sonra id DURUM9'a
    say = len(gorseller())
    for n in range(1, N_YENI + 1):
        if n in yeni:
            continue
        if say >= 20:
            kaydet(); raise SystemExit(f"DUR: {pair} galeri {say} gorsel (20 siniri), yeni {n} yuklenemez")
        with open(galeri[n - 1], "rb") as fh:
            r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (galeri[n - 1].name, fh, "image/jpeg")},
                              data={"rank": str(n), "alt_text": alt[n - 1]})
        yeni[n] = int(r["listing_image_id"]); d["yeni"] = {str(k): v for k, v in yeni.items()}; kaydet(); say += 1
    state_oku("2 yeni 14 gorsel")
    rk = {x["listing_image_id"]: x.get("rank") for x in gorseller()}
    sira_r = [rk.get(yeni[n]) for n in range(1, N_YENI + 1)]
    if None in sira_r or any(a_ >= b_ for a_, b_ in zip(sira_r, sira_r[1:])):
        # GEVSETME (Serdar 8 Kas "Evet, sira kapisi"): 8 Kas olcum (42461185221) Etsy silmede kalanlari 1..N yeniden numaralar; yeni
        # gorseller n'den kayabilir -> tam rank == n yerine var ve kesin artan. Son geri okuma: 14 gorsel, rank kesin artan, id sirasi, alt metin.
        kaydet(); raise SystemExit(f"DUR: {pair} yeni gorsel rank'lari sirali degil {dict(zip(range(1, N_YENI + 1), sira_r))}")
    # 3) Style -> yeni 10-14
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == P_STYLE and v.get("value_ids")}
    if sorted(vid) != sorted(STIL_SIRA) or {s: vid[s] for s in vid} != {s: y["stil"][s] for s in vid}:
        kaydet(); raise SystemExit(f"DUR: {pair} Style value_id yedekten farkli {vid}")
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": [dict(property_id=P_STYLE, value_id=vid[s], image_id=yeni[r]) for s, r in STIL_SIRA.items()]})
    state_oku("3 stil baglari")
    # 4) eski 5 stil gorseli silinir (yalniz bag yeniye gectiyse)
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
    bag = {v.get("value_id"): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}
    if bag != {vid[s]: yeni[r] for s, r in STIL_SIRA.items()}:
        kaydet(); raise SystemExit(f"DUR: {pair} stil baglari yeniye gecmedi {bag}")
    simdi = [x["listing_image_id"] for x in gorseller()]
    for i in eski[6:]:
        if i in simdi:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    state_oku("4 eski stil gorselleri silindi")
    # 5) video: eski silinir, yeni yuklenir (gonderim isareti yuklemeden ONCE: kopma sonrasi ikinci video yok)
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    yv = [v for v in vids if v.get("video_id") not in eski_v]
    if d.get("video_gonderildi") and not yv:
        for _ in range(6):
            time.sleep(15)
            vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
            yv = [v for v in vids if v.get("video_id") not in eski_v]
            if yv:
                break
        if not yv:
            kaydet(); raise SystemExit(f"DUR: {pair} video onceki kosuda gonderildi ama gorunmuyor (ikinci video yuklenmedi)")
    for v in vids:
        if v.get("video_id") in eski_v:
            api.delete(f"/shops/{shop}/listings/{lid}/videos/{v['video_id']}")
    if not yv:
        d["video_gonderildi"] = True; kaydet()
        try:
            with open(video, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("video.mp4", fh, "video/mp4")},
                              data={"name": f"AstroLoveArt_{pair}_ornament_video.mp4"})
        except SystemExit as e:                   # inceleme 4: kesin red (4xx) -> video olusmadi; isaret geri, DUR
            if re.search(r"-> 4\d\d", str(e.code)):
                d["video_gonderildi"] = False; kaydet()
            raise
    state_oku("5 video")
    # 6) geri okuma
    for _ in range(6):
        ims = gorseller()
        vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
        if all(x.get("full_width") for x in ims) and vids:
            break
        time.sleep(10)
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
    L = api.get(f"/listings/{lid}") or {}
    norm = lambda t: " ".join(html.unescape(str(t or "")).split())  # noqa: E731
    rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
    K = {
        f"{N_YENI} gorsel, rank kesin artan": len(ims) == N_YENI and all(a_ < b_ for a_, b_ in zip([x.get("rank") for x in ims], [x.get("rank") for x in ims][1:])),
        "gorseller yeni id sirasi": [x.get("listing_image_id") for x in ims] == [yeni[n] for n in range(1, N_YENI + 1)],
        "eski gorsel yok": not (set(rank_id.values()) & set(eski)),
        "3000x2250": all((x.get("full_width"), x.get("full_height")) == (3000, 2250) for x in ims),
        "alt metinler": [norm(x.get("alt_text")) for x in ims] == [norm(a) for a in alt],
        "video 1 yeni": len(vids) == 1 and vids[0].get("video_id") not in eski_v,
        "stil 10-14": {v.get("value_id"): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}
        == {vid[s]: yeni[r] for s, r in STIL_SIRA.items()},
        "state draft": L.get("state") == "draft",
        "baslik ayni": html.unescape(L.get("title") or "") == baslik,
    }
    R["kontrol"] = K
    R["son"] = dict(listing_id=lid, link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    gorsel=[(x.get("rank"), x.get("listing_image_id"), x.get("full_width"), x.get("full_height")) for x in ims],
                    video=[(v.get("video_id"), v.get("video_state")) for v in vids])
    R["kota_son"] = api.remaining
    kotu = [k for k, v in K.items() if not v]
    print(f"::warning::{pair} {lid} galeri9 | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        kaydet(); raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    d["tamam"] = True
    D.setdefault("tamam", [])
    if pair not in D["tamam"]:
        D["tamam"].append(pair)
    D.setdefault("sira_v2", [])                         # inceleme 2: yeni sirayla yazilan cift sira modunda tekrar islenmez
    if pair not in D["sira_v2"]:
        D["sira_v2"].append(pair)
    kaydet()
    return R


# ------------------------------------------------------------------ sira (Serdar 8 Kas: sembol karti 2. siraya; eski siradaki pilot)
def sira(api, shop, out, pair, Y):
    """DURUM9'da eski sirayla (ESKI_GALERI9) TAMAM olan ilanda yalniz SIRA_DEG (2-6) gorselleri silinir ve yeni sirayla yuklenir.
    Stil baglari (10-14), video, 1 ve 7-14 dokunulmaz. Her hata DUR; PATCH yok. DURUM9[pair].sira2 ile yarim kosudan devam."""
    R = {"cift": pair, "mod": "sira", "adimlar": []}
    durum_f = out / "DURUM9.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    rapor_f = out / f"S9_{pair}.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    d = D.get("ciftler", {}).get(pair) or {}
    if pair != "CANCER_LIBRA":                         # inceleme 2: eski sirayla yazilan tek ilan pilot
        raise SystemExit(f"DUR-ON: {pair} sira modu yalniz CANCER_LIBRA")
    if pair in D.get("sira_v2", []):
        print(f"::warning::{pair}: ATLANDI, sira zaten yeni (sira_v2)"); R["atlandi"] = "sira_v2"; return R
    if pair not in D.get("tamam", []) or not d.get("tamam") or sorted(int(k) for k in d.get("yeni", {})) != list(range(1, 15)):
        kaydet(); raise SystemExit(f"DUR-ON: {pair} DURUM9'da eski sirayla tamam degil")
    alt, baslik, hata = alt_metinler(pair)
    galeri, _video, mh = medya(pair)
    if hata or mh:
        kaydet(); raise SystemExit(f"DUR-ON: {pair} metin {hata} medya {mh}")
    y = Y.get(pair) or {}
    if not str(y.get("listing_id", "")).isdigit():
        kaydet(); raise SystemExit(f"DUR-ON: {pair} yedek yok")
    lid = int(y["listing_id"])
    eski = {int(k): v for k, v in d["yeni"].items()}
    s2 = d.setdefault("sira2", {})
    yeni = {int(k): v for k, v in s2.get("yeni", {}).items()}
    sil = [eski[n] for n in SIRA_DEG]
    api.lid, api.sil_izin, api.vid_izin, api.yalniz_gorsel = lid, frozenset(sil), frozenset(), True
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    api.kota(30 + 10)

    def durum(adim, acil=True):
        L = api.get(f"/listings/{lid}") or {}
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active" and acil:                    # inceleme 4: yazimdan SONRA active -> acil inactive (yaz() ile ayni)
            st2 = "?"
            try:
                api.patch(f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
                st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            except BaseException as e:  # noqa: BLE001
                st2 = f"hata {type(e).__name__}: {str(e)[:200]}"
            finally:
                R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
                print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive (simdi {st2}). DUR.", flush=True)
                if st2 != "inactive":
                    print(f"::error::ACIL BASARISIZ: {pair} listing {lid} hala {st2}; Etsy panelinden elle inactive yapilmali.", flush=True)
                raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: {pair} state {st} ({adim}); dokunulmadi")
        return L

    def gorseller():
        return sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)

    def baglar():
        vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
        return {v.get("value_id"): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}

    def videolar():
        return [v.get("video_id") for v in ((api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or [])]

    L = durum("0 baslangic", acil=False)
    if html.unescape(L.get("title") or "") != baslik:
        kaydet(); raise SystemExit(f"DUR: {pair} {lid} baslik METIN ile ayni degil (kimlik)")
    bag0, vid0 = baglar(), videolar()
    ims0 = gorseller()
    R["once"] = dict(gorsel=[(x.get("listing_image_id"), x.get("rank"), x.get("alt_text"), x.get("url_fullxfull")) for x in ims0],
                     bag=bag0, video=vid0)                                       # inceleme 1: onceki durumun kaydi (S9 raporu)
    kaydet()
    a_ = dict(zip(GALERI, alt))
    alt_eski = [a_[x] for x in ESKI_GALERI9]
    norm0 = lambda t: " ".join(html.unescape(str(t or "")).split())  # noqa: E731
    bag_bek = {y["stil"][s_]: eski[r] for s_, r in STIL_SIRA.items()}
    if not s2.get("basladi"):                      # inceleme 1: ilk kosu; galeri tam olarak eski sirali 14 gorsel olmali, yoksa yazmadan DUR
        on = {
            "gorseller eski id ve rank 1-14": [(x.get("listing_image_id"), x.get("rank")) for x in ims0] == [(eski[n], n) for n in range(1, 15)],
            "alt metinler eski sira": [norm0(x.get("alt_text")) for x in ims0] == [norm0(t) for t in alt_eski],
            "stil baglari 10-14": bag0 == bag_bek,
            "video 1": len(vid0) == 1,
        }
    else:                                          # inceleme 2. tur: devam (silme basladiysa yeni bos olabilir)
        rk0 = {x.get("listing_image_id"): x for x in ims0}
        on = {
            "yalniz eski 1-14 ve bu kosunun yeni id'leri": set(rk0) <= (set(eski.values()) | set(yeni.values())),
            "eski 1 ve 7-14 kendi rank ve alt metninde": all(eski[n] in rk0 and rk0[eski[n]].get("rank") == n
                                                             and norm0(rk0[eski[n]].get("alt_text")) == norm0(alt_eski[n - 1])
                                                             for n in range(1, 15) if n not in SIRA_DEG),
            "kalan eski 2-6 kendi rank'inda": all(rk0[eski[n]].get("rank") == n for n in SIRA_DEG if eski[n] in rk0),
            "yeni 2-6 kendi rank'inda": all(rk0.get(yeni[n], {}).get("rank") == n for n in yeni),
            "stil baglari 10-14": bag0 == bag_bek,
            "video 1": len(vid0) == 1,
        }
    R["on_kontrol"] = on
    if not all(on.values()):
        kaydet(); raise SystemExit(f"DUR: {pair} on kontrol {[k for k, v in on.items() if not v]} (yazim yapilmadi)")
    simdi = [x["listing_image_id"] for x in ims0]
    # 1) eski 2-6 silinir (ilk silmeden ONCE "basladi" kaydedilir: kopma sonrasi devam yolu)
    s2["basladi"] = True; kaydet()
    for i in sil:
        if i in simdi:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    durum("1 eski 2-6 silindi")
    # 2) yeni sirayla 2-6
    say = len(gorseller())
    for n in SIRA_DEG:
        if n in yeni:
            continue
        if say >= 20:
            kaydet(); raise SystemExit(f"DUR: {pair} galeri {say} gorsel (20 siniri)")
        with open(galeri[n - 1], "rb") as fh:
            r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (galeri[n - 1].name, fh, "image/jpeg")},
                              data={"rank": str(n), "alt_text": alt[n - 1]})
        yeni[n] = int(r["listing_image_id"]); s2["yeni"] = {str(k): v for k, v in yeni.items()}; kaydet(); say += 1
    durum("2 yeni 2-6")
    # 3) geri okuma
    son = {n: (yeni[n] if n in SIRA_DEG else eski[n]) for n in range(1, 15)}
    for _ in range(6):
        ims = gorseller()
        if all(x.get("full_width") for x in ims):
            break
        time.sleep(10)
    L = api.get(f"/listings/{lid}") or {}
    norm = lambda t: " ".join(html.unescape(str(t or "")).split())  # noqa: E731
    K = {
        "14 gorsel, rank kesin artan": len(ims) == 14 and all(a_ < b_ for a_, b_ in zip([x.get("rank") for x in ims], [x.get("rank") for x in ims][1:])),
        "gorseller yeni sira id": [x.get("listing_image_id") for x in ims] == [son[n] for n in range(1, 15)],
        "yeni 2-6 kendi rank'inda": all(next((x.get("rank") for x in ims if x.get("listing_image_id") == yeni[n]), None) == n for n in SIRA_DEG),
        "eski 2-6 yok": not (set(x.get("listing_image_id") for x in ims) & set(sil)),
        "3000x2250": all((x.get("full_width"), x.get("full_height")) == (3000, 2250) for x in ims),
        "alt metinler": [norm(x.get("alt_text")) for x in ims] == [norm(a) for a in alt],
        "stil baglari ayni": baglar() == bag0,
        "video ayni": videolar() == vid0,
        "state draft": L.get("state") == "draft",
        "baslik ayni": html.unescape(L.get("title") or "") == baslik,
    }
    R["kontrol"] = K
    R["son"] = dict(listing_id=lid, link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    gorsel=[(x.get("rank"), x.get("listing_image_id")) for x in ims])
    R["kota_son"] = api.remaining
    kotu = [k for k, v in K.items() if not v]
    print(f"::warning::{pair} {lid} sira | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        kaydet(); raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    d["yeni"] = {str(n): son[n] for n in range(1, 15)}; d["sira"] = "v2"; d.pop("sira2", None)
    D.setdefault("sira_v2", [])
    if pair not in D["sira_v2"]:
        D["sira_v2"].append(pair)
    kaydet()
    return R


# ------------------------------------------------------------------ yeniden (Serdar 8 Kas "Kodla yeniden yaz")
def yeniden(api, shop, out, pair, Y):
    """sira kosusu (42461185221) FAIL: Etsy silinen 2-6'nin yerini kapatti, sira karisik. Galeri, bu ilanda gercek Etsy'de 9/9 gecen yaz()
    yoluyla yeni sirayla kurulur: stile bagli olmayan 9 gorsel silinir, 14 yeni gorsel 1-14 yuklenir, Style yeni 10-14'e baglanir, eski 5 stil
    gorseli silinir. Video, baslik, state dokunulmaz. Yalniz CANCER_LIBRA. DURUM9[pair].yeniden ile devam. Her hata DUR."""
    R = {"cift": pair, "mod": "yeniden", "adimlar": []}
    durum_f = out / "DURUM9.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    rapor_f = out / f"Y9_{pair}.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    if pair != "CANCER_LIBRA":
        raise SystemExit(f"DUR-ON: {pair} yeniden modu yalniz CANCER_LIBRA")
    d = D.get("ciftler", {}).get(pair) or {}
    if pair in D.get("sira_v2", []):
        print(f"::warning::{pair}: ATLANDI, sira zaten yeni (sira_v2)"); R["atlandi"] = "sira_v2"; return R
    if pair not in D.get("tamam", []) or sorted(int(k) for k in d.get("yeni", {})) != list(range(1, 15)):
        kaydet(); raise SystemExit(f"DUR-ON: {pair} DURUM9'da eski sirayla tamam degil")
    alt, baslik, hata = alt_metinler(pair)
    galeri, _video, mh = medya(pair)
    if hata or mh:
        kaydet(); raise SystemExit(f"DUR-ON: {pair} metin {hata} medya {mh}")
    y = Y.get(pair) or {}
    if not str(y.get("listing_id", "")).isdigit():
        kaydet(); raise SystemExit(f"DUR-ON: {pair} yedek yok")
    lid = int(y["listing_id"])
    eski = {int(k): v for k, v in d["yeni"].items()}                                  # eski sirali tamam galeri (pilot)
    s2y = {int(k): v for k, v in (d.get("sira2") or {}).get("yeni", {}).items()}      # sira kosusunun yukledigi 2-6
    bekl = {eski[n] for n in range(1, 15) if n not in SIRA_DEG} | set(s2y.values())   # su anki galerinin beklenen 14 id'si
    bagli = {eski[r] for r in STIL_SIRA.values()}
    serbest = bekl - bagli
    Ye = d.setdefault("yeniden", {})
    yeni = {int(k): v for k, v in Ye.get("yeni", {}).items()}
    api.lid, api.sil_izin, api.vid_izin, api.video_yasak = lid, frozenset(bekl), frozenset(), True
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    api.kota(KOTA_ILAN + 10)

    def durum(adim, acil=True):
        L = api.get(f"/listings/{lid}") or {}
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active" and acil:
            st2 = "?"
            try:
                api.patch(f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
                st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            except BaseException as e:  # noqa: BLE001
                st2 = f"hata {type(e).__name__}: {str(e)[:200]}"
            finally:
                R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
                print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive (simdi {st2}). DUR.", flush=True)
                if st2 != "inactive":
                    print(f"::error::ACIL BASARISIZ: {pair} listing {lid} hala {st2}; Etsy panelinden elle inactive yapilmali.", flush=True)
                raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: {pair} state {st} ({adim}); dokunulmadi")
        return L

    def gorseller():
        return sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: (x.get("rank") or 0, x.get("listing_image_id")))

    def baglar():
        vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
        return {v.get("value_id"): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}

    def videolar():
        return [v.get("video_id") for v in ((api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or [])]

    L = durum("0 baslangic", acil=False)
    if html.unescape(L.get("title") or "") != baslik:
        kaydet(); raise SystemExit(f"DUR: {pair} {lid} baslik METIN ile ayni degil (kimlik)")
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == P_STYLE and v.get("value_ids")}
    if sorted(vid) != sorted(STIL_SIRA) or vid != {s_: y["stil"][s_] for s_ in vid}:
        kaydet(); raise SystemExit(f"DUR: {pair} Style value_id yedekten farkli {vid}")
    ims0, bag0, vid0 = gorseller(), baglar(), videolar()
    R["once"] = dict(gorsel=[(x.get("listing_image_id"), x.get("rank"), x.get("alt_text"), x.get("url_fullxfull")) for x in ims0],
                     bag=bag0, video=vid0)
    kaydet()
    simdi = {x.get("listing_image_id") for x in ims0}
    bag_eski = {vid[s_]: eski[r] for s_, r in STIL_SIRA.items()}
    bag_yeni = {vid[s_]: yeni.get(r) for s_, r in STIL_SIRA.items()}
    if not Ye.get("basladi"):
        on = {"galeri = beklenen 14 id": simdi == bekl and len(ims0) == 14, "stil baglari eski 10-14": bag0 == bag_eski,
              "video 1": len(vid0) == 1}
    else:
        on = {"yalniz beklenen + bu kosunun yeni id'leri": simdi <= (bekl | set(yeni.values())),
              "kayitli yeni id'ler galeride, rank kesin artan": all(yeni[n] in simdi for n in yeni) and (lambda r: all(a_ < b_ for a_, b_ in zip(r, r[1:])))(
                  [next((x.get("rank") for x in ims0 if x.get("listing_image_id") == yeni[n]), None) for n in sorted(yeni)]),
              "bag yeniye gectiyse kalan eski yalniz stil gorselleri": bag0 != bag_yeni or not (simdi & serbest),
              "stil baglari eski ya da yeni 10-14": bag0 in (bag_eski, bag_yeni), "video 1": len(vid0) == 1}
    R["on_kontrol"] = on
    if not all(on.values()):
        kaydet(); raise SystemExit(f"DUR: {pair} on kontrol {[k for k, v in on.items() if not v]} (yazim yapilmadi)")
    if not Ye.get("basladi"):
        Ye["video"] = vid0; Ye["basladi"] = True; kaydet()
    # 1) stile bagli olmayan 9 gorsel silinir
    for i in sorted(serbest):
        if i in simdi:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    durum("1 bagsiz 9 silindi")
    # 2) yeni 14 gorsel 1..14
    say = len(gorseller())
    for n in range(1, N_YENI + 1):
        if n in yeni:
            continue
        if say >= 20:
            kaydet(); raise SystemExit(f"DUR: {pair} galeri {say} gorsel (20 siniri)")
        with open(galeri[n - 1], "rb") as fh:
            r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (galeri[n - 1].name, fh, "image/jpeg")},
                              data={"rank": str(n), "alt_text": alt[n - 1]})
        yeni[n] = int(r["listing_image_id"]); Ye["yeni"] = {str(k): v for k, v in yeni.items()}; kaydet(); say += 1
    durum("2 yeni 14 gorsel")
    rk = {x["listing_image_id"]: x.get("rank") for x in gorseller()}
    sira_r = [rk.get(yeni[n]) for n in range(1, N_YENI + 1)]
    if None in sira_r or any(a_ >= b_ for a_, b_ in zip(sira_r, sira_r[1:])):    # GEVSETME (Serdar 8 Kas "Evet, sira kapisi"), yaz() ile ayni
        kaydet(); raise SystemExit(f"DUR: {pair} yeni gorsel rank'lari sirali degil {dict(zip(range(1, N_YENI + 1), sira_r))}")
    # 3) Style -> yeni 10-14
    bag_yeni = {vid[s_]: yeni[r] for s_, r in STIL_SIRA.items()}
    if baglar() != bag_yeni:
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                      {"variation_images": [dict(property_id=P_STYLE, value_id=vid[s_], image_id=yeni[r]) for s_, r in STIL_SIRA.items()]})
    durum("3 stil baglari")
    if baglar() != bag_yeni:
        kaydet(); raise SystemExit(f"DUR: {pair} stil baglari yeniye gecmedi")
    # 4) eski 5 stil gorseli silinir
    simdi = {x["listing_image_id"] for x in gorseller()}
    for i in sorted(bagli):
        if i in simdi:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    durum("4 eski stil gorselleri silindi")
    # 5) geri okuma
    for _ in range(6):
        ims = gorseller()
        if all(x.get("full_width") for x in ims):
            break
        time.sleep(10)
    L = api.get(f"/listings/{lid}") or {}
    norm = lambda t: " ".join(html.unescape(str(t or "")).split())  # noqa: E731
    K = {
        "14 gorsel, rank kesin artan": len(ims) == 14 and all(a_ < b_ for a_, b_ in zip([x.get("rank") for x in ims], [x.get("rank") for x in ims][1:])),
        "gorseller yeni id sirasi": [x.get("listing_image_id") for x in ims] == [yeni[n] for n in range(1, 15)],
        "eski gorsel yok": not ({x.get("listing_image_id") for x in ims} & bekl),
        "3000x2250": all((x.get("full_width"), x.get("full_height")) == (3000, 2250) for x in ims),
        "alt metinler": [norm(x.get("alt_text")) for x in ims] == [norm(a) for a in alt],
        "stil 10-14": baglar() == bag_yeni,
        "video ayni": videolar() == Ye.get("video"),
        "state draft": L.get("state") == "draft",
        "baslik ayni": html.unescape(L.get("title") or "") == baslik,
    }
    R["kontrol"] = K
    R["son"] = dict(listing_id=lid, link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    gorsel=[(x.get("rank"), x.get("listing_image_id")) for x in ims])
    R["kota_son"] = api.remaining
    kotu = [k for k, v in K.items() if not v]
    print(f"::warning::{pair} {lid} yeniden | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        kaydet(); raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    d["yeni"] = {str(n): yeni[n] for n in range(1, 15)}; d["sira"] = "v2"
    d.pop("sira2", None); d.pop("yeniden", None)
    D.setdefault("sira_v2", [])
    if pair not in D["sira_v2"]:
        D["sira_v2"].append(pair)
    kaydet()
    return R


# ------------------------------------------------------------------ kuru (ag yok, yedekten taklit)
class Kuru(Kilitli):
    kuru = True

    def __init__(self, shop, Y):
        self.shop, self.calls, self.remaining, self.lid = str(shop), 0, "KURU", None
        self.kayit, self.Y = [], Y
        self.n = 0
        self.kaydir = False
        self.sikistir = False      # silme davranisi: 30 Eyl olcumu kapatmaz, 8 Kas olcumu (42461185221) kapatti; kuru ve testler iki modu da kosar

    def ilan(self, y):
        self.L = dict(listing_id=y["listing_id"], state=y["state"], title=y["baslik"])
        self.ims = [dict(listing_image_id=g["id"], rank=g["rank"], alt_text=g["alt"], full_width=g["w"], full_height=g["h"]) for g in y["gorsel"]]
        self.vids = [dict(video_id=v["id"], video_state=v["state"]) for v in y["video"]]
        self.vis = [dict(property_id=P_STYLE, value_id=int(k), image_id=v) for k, v in y["bag"].items()]
        self.inv = dict(products=[dict(property_values=[dict(property_id=P_STYLE, values=[s], value_ids=[i])]) for s, i in y["stil"].items()])

    def ilan_sira(self, y, d, pair):
        """sira kurusu: DURUM9'daki eski sirali 14 gorsel (eski siradaki alt metinleriyle) + 1 video + stil baglari 10-14 (taklit)"""
        self.ilan(y)
        e = {int(k): v for k, v in d["yeni"].items()}
        a = dict(zip(GALERI, alt_metinler(pair)[0]))
        self.ims = [dict(listing_image_id=e[n], rank=n, alt_text=a[ESKI_GALERI9[n - 1]], full_width=3000, full_height=2250) for n in range(1, 15)]
        self.vids = [dict(video_id=990001, video_state="active")]
        self.vis = [dict(property_id=P_STYLE, value_id=y["stil"][s], image_id=e[r]) for s, r in STIL_SIRA.items()]

    def ilan_yeniden(self, y, d, pair):
        """yeniden kurusu: sira kosusu sonrasi karisik galeri (8 Kas olcumu 42461185221 sirasi; rank'lar esit) + 1 video + eski bag (taklit)"""
        self.ilan(y)
        e = {int(k): v for k, v in d["yeni"].items()}
        s2 = {int(k): v for k, v in (d.get("sira2") or {}).get("yeni", {}).items()}
        a = dict(zip(GALERI, alt_metinler(pair)[0]))
        sira = [(1, e[1], "01_KAPAK")] + [(n, s2[n], GALERI[n - 1]) for n in SIRA_DEG] + \
               [(n - 5, e[n], ESKI_GALERI9[n - 1]) for n in range(7, 15)]                # eski 7-14 -> 2-9 (sikisti)
        self.ims = [dict(listing_image_id=i, rank=r, alt_text=a[f], full_width=3000, full_height=2250) for r, i, f in sira]
        self.vids = [dict(video_id=990001, video_state="active")]
        self.vis = [dict(property_id=P_STYLE, value_id=y["stil"][s], image_id=e[r]) for s, r in STIL_SIRA.items()]

    def _kaydet(self, method, path, params=None, data=None, json_body=None, files=None):
        k = dict(no=len(self.kayit) + 1, method=method, url=API + path, yazma=method != "GET")
        for ad, v in (("params", params), ("form", data), ("json", json_body)):
            if v is not None:
                k[ad] = v
        if files:
            k["dosya"] = {a: dict(ad=f[0], mime=f[2], bayt=os.fstat(f[1].fileno()).st_size) for a, f in files.items()}
        self.kayit.append(k); self.calls += 1

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and data != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum")
            ai_beyan_kapisi(method, path, data, json_body, params); metin_yasak_kapisi(method, path, data, json_body, params)
        self._kaydet(method, path, params, data, json_body)
        return self._sim(method, path, json_body)

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        metin_yasak_kapisi("POST", path, data)
        self._kaydet("POST", path, data=data, files=files)
        self.n += 1
        if path.endswith("/images"):
            rk = int(data["rank"])
            if self.kaydir:                           # test modu; gercek Etsy olcumu (6 Kas, w05_degistir.py:25) ESIT: kaydirma yok
                for x in self.ims:
                    if x["rank"] >= rk:
                        x["rank"] += 1
            self.ims.append(dict(rank=rk, listing_image_id=800000 + self.n, full_width=3000, full_height=2250, alt_text=data.get("alt_text")))
            self.ims.sort(key=lambda x: x["rank"])
            return next(x for x in self.ims if x["listing_image_id"] == 800000 + self.n)
        self.vids.append(dict(video_id=900000 + self.n, video_state="active")); return self.vids[-1]

    def _sim(self, method, path, js):
        s, lid = self.shop, self.lid
        if method == "GET":
            if path == f"/shops/{s}":
                return {}
            if path == f"/listings/{lid}":
                return self.L
            if path == f"/listings/{lid}/images":
                return dict(results=[dict(x) for x in sorted(self.ims, key=lambda x: (x["rank"], x["listing_image_id"]))])
            if path == f"/listings/{lid}/videos":
                return dict(results=self.vids)
            if path == f"/listings/{lid}/inventory":
                return self.inv
            if path == f"/shops/{s}/listings/{lid}/variation-images":
                return dict(results=self.vis)
            raise SystemExit(f"KURU: taklit edilmeyen GET {path}")
        if method == "DELETE" and "/images/" in path:
            i = int(path.rsplit("/", 1)[1])
            r0 = next((x["rank"] for x in self.ims if x["listing_image_id"] == i), None)
            self.ims = [x for x in self.ims if x["listing_image_id"] != i]       # olcum (30 Eyl): silme rank sikistirmaz
            if self.sikistir and r0 is not None:          # olcum (8 Kas, 42461185221): kalanlar sirasi korunarak 1..N yeniden numaralandi
                for k, x in enumerate(sorted(self.ims, key=lambda x: (x["rank"], x["listing_image_id"])), 1):
                    x["rank"] = k
            return {}
        if method == "DELETE" and "/videos/" in path:
            i = int(path.rsplit("/", 1)[1]); self.vids = [v for v in self.vids if v["video_id"] != i]; return {}
        if path.endswith("/variation-images"):
            self.vis = js["variation_images"]; return dict(results=self.vis)
        if method == "PATCH":
            self.L["state"] = "inactive"; return self.L
        raise SystemExit(f"KURU: taklit edilmeyen {method} {path}")


def kuru(shop, out, pair, Y):
    """8 Kas: Etsy silmede rank'lari bazen kapatir (42461185221), bazen kapatmaz (30 Eyl olcumu): iki davranis da kosulur, ikisi de PASS olmali"""
    o2 = out / "kuru"; o2.mkdir(parents=True, exist_ok=True)
    ozet = {}
    for sik in (True, False):
        api = Kuru(shop, Y); api.sikistir = sik
        api.ilan(Y[pair])
        (o2 / "DURUM9.json").unlink(missing_ok=True)
        R = yaz(api, shop, o2, pair, Y)
        yazma = [k for k in api.kayit if k["yazma"]]
        ozet[f"sikistir={sik}"] = dict(cift=pair, istek=len(api.kayit), yazma=len(yazma), kontrol=R["kontrol"])
        json.dump(dict(ozet=ozet[f"sikistir={sik}"], istekler=api.kayit), open(o2 / f"KURU_{pair}_{sik}.json", "w"), indent=1, ensure_ascii=False)
        print(f"KURU {pair} sikistir={sik}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol {sum(R['kontrol'].values())}/{len(R['kontrol'])}")
    (o2 / "DURUM9.json").unlink(missing_ok=True)
    return ozet


def sira_kuru(shop, out, pair, Y):
    D = json.load(open(out / "DURUM9.json")) if (out / "DURUM9.json").exists() else {}
    d = D.get("ciftler", {}).get(pair)
    if pair != "CANCER_LIBRA" or not d or not d.get("tamam") or sorted(int(k) for k in d.get("yeni", {})) != list(range(1, 15)):
        raise SystemExit(f"DUR-ON: {pair} DURUM9'da eski sirayla tamam degil (sira_kuru)")
    api = Kuru(shop, Y)
    api.ilan_sira(Y[pair], d, pair)
    o2 = out / "sira_kuru"; o2.mkdir(parents=True, exist_ok=True)
    json.dump(D, open(o2 / "DURUM9.json", "w"))
    R = sira(api, shop, o2, pair, Y)
    yazma = [k for k in api.kayit if k["yazma"]]
    json.dump(dict(ozet=dict(cift=pair, istek=len(api.kayit), yazma=len(yazma), kontrol=R.get("kontrol")), istekler=api.kayit),
              open(o2 / f"SIRA_KURU_{pair}.json", "w"), indent=1, ensure_ascii=False)
    if R.get("atlandi"):
        print(f"SIRA KURU {pair}: ATLANDI ({R['atlandi']})")
    else:
        print(f"SIRA KURU {pair}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol {sum((R.get('kontrol') or {}).values())}/{len(R.get('kontrol') or {})} "
              f"| ZAYIF TEST: taklit DURUM9'dan kurulur (gercek galeri sira kosusunun on kontrolunde denetlenir)")
    (o2 / "DURUM9.json").unlink(missing_ok=True)


def yeniden_kuru(shop, out, pair, Y):
    D = json.load(open(out / "DURUM9.json")) if (out / "DURUM9.json").exists() else {}
    d = D.get("ciftler", {}).get(pair)
    if pair != "CANCER_LIBRA" or not d or not d.get("tamam") or sorted(int(k) for k in d.get("yeni", {})) != list(range(1, 15)) \
            or sorted(int(k) for k in (d.get("sira2") or {}).get("yeni", {})) != SIRA_DEG:
        raise SystemExit(f"DUR-ON: {pair} DURUM9 beklenen degil (yeniden_kuru)")
    o2 = out / "yeniden_kuru"; o2.mkdir(parents=True, exist_ok=True)
    sonuc = {}
    for sik in (True, False):                     # Etsy silmede rank kapatir mi: iki davranis da denenir
        api = Kuru(shop, Y); api.sikistir = sik
        api.ilan_yeniden(Y[pair], d, pair)
        json.dump(D, open(o2 / "DURUM9.json", "w"))
        R = yeniden(api, shop, o2, pair, Y)
        yazma = [k for k in api.kayit if k["yazma"]]
        sonuc[f"sikistir={sik}"] = dict(istek=len(api.kayit), yazma=len(yazma), kontrol=R.get("kontrol"))
        json.dump(dict(ozet=sonuc, istekler=api.kayit), open(o2 / f"YENIDEN_KURU_{pair}_{sik}.json", "w"), indent=1, ensure_ascii=False)
        print(f"YENIDEN KURU {pair} sikistir={sik}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol "
              f"{sum((R.get('kontrol') or {}).values())}/{len(R.get('kontrol') or {})} | ZAYIF TEST: taklit DURUM9'dan (gercek on kontrolde)")
    (o2 / "DURUM9.json").unlink(missing_ok=True)


# ------------------------------------------------------------------ dongu
def cift_listesi(girdi):
    secim = CIFTLER if girdi.strip().upper() == "TUMU" else [c.strip().upper() for c in re.split(r"[,\s]+", girdi) if c.strip()]
    bil = [c for c in secim if c not in CIFTLER]
    if bil or not secim:
        raise SystemExit(f"DUR: bilinmeyen cift {bil}")
    if "CANCER_LIBRA" in secim:                     # Serdar 8 Kas: CANCER_LIBRA ilk yazilir
        secim = ["CANCER_LIBRA"] + [c for c in secim if c != "CANCER_LIBRA"]
    return secim


def yaz_dongu(api, shop, out, ciftler, Y, parti_max=PARTI_MAX, sure_dk=SURE_DK):
    """Her hata DUR (CLAUDE.md Etsy 3). Tek istisna ag ONCESI DUR ("DUR-ON:"): o cift atlanir, listede; ard arda 3 -> DUR."""
    t0 = time.time()
    t_kilit = float(os.environ.get("KILIT_T0") or t0)
    D = json.load(open(out / "DURUM9.json")) if (out / "DURUM9.json").exists() else {}
    on_ard, yeni = 0, 0
    for i, c in enumerate(ciftler, 1):
        api.lid = None
        if c in D.get("tamam", []):
            continue
        if yeni >= parti_max or (time.time() - t_kilit) / 60 >= sure_dk:
            kalan = [x for x in ciftler[i - 1:] if x not in D.get("tamam", [])]
            print(f"::warning::PARTI SINIRI: {yeni} cift / {(time.time() - t_kilit) / 60:.0f} dk; KALAN {len(kalan)} cift yeniden kosuda")
            break
        yeni += 1
        try:
            yaz(api, shop, out, c, Y)
            on_ard = 0
        except BaseException as e:  # noqa: BLE001
            f = out / f"G9_{c}.json"
            R = json.load(open(f)) if f.exists() else {}
            R["hata"] = f"{type(e).__name__}: {e}"[:1500]
            json.dump(R, open(f, "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::error::G9 HATA {c} {R['hata'][:600]}")
            if not (isinstance(e, SystemExit) and isinstance(e.code, str) and e.code.startswith("DUR-ON:")):
                raise
            on_ard += 1
            if on_ard >= 3:
                raise
        D = json.load(open(out / "DURUM9.json")) if (out / "DURUM9.json").exists() else D
        g = time.time() - t0
        print(f"ETA parti [{yeni}] {c} | gecen {g / 60:.1f} dk | ortalama {g / yeni / 60:.1f} dk/ilan | kota {api.remaining}", flush=True)


def liste_yaz(out, Y):
    D = json.load(open(out / "DURUM9.json")) if (out / "DURUM9.json").exists() else {}
    say = {}
    with open(out / "G9_LISTE.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["cift", "listing_id", "durum", "sira", "neden", "link"])
        for c in CIFTLER:
            lid = (Y.get(c) or {}).get("listing_id", "")
            f = out / f"G9_{c}.json"
            hata = (json.load(open(f)).get("hata") or "") if f.exists() else ""
            d = D.get("ciftler", {}).get(c, {})
            durum = "TAMAM" if c in D.get("tamam", []) else "FAIL" if hata else "YARIM" if (d.get("yeni") or d.get("video_gonderildi")) else "BEKLIYOR"
            say[durum] = say.get(durum, 0) + 1
            w.writerow([c, lid, durum, "v2" if c in D.get("sira_v2", []) else ("ESKI" if durum == "TAMAM" else ""), hata[:300],
                        f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}" if str(lid).isdigit() else ""])
    print(f"::warning::LISTE {say}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["yedek", "kuru", "yaz", "sira_kuru", "sira", "yeniden_kuru", "yeniden"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    ciftler = cift_listesi(a.ciftler)
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    if a.mod in ("kuru", "yaz", "sira_kuru", "sira", "yeniden_kuru", "yeniden"):
        Y = json.load(open(os.environ["YEDEK"]))
    if a.mod == "kuru":
        for c in ciftler:
            kuru(shop, out, c, Y)
        return
    if a.mod == "sira_kuru":
        for c in ciftler:
            sira_kuru(shop, out, c, Y)
        return
    if a.mod == "yeniden_kuru":
        for c in ciftler:
            yeniden_kuru(shop, out, c, Y)
        return
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    if a.mod == "yedek":
        harita = json.load(open(os.environ["TASLAK_DURUM"])).get("ciftler", {})
        yedek(SaltOkur(store), shop, out, ciftler, harita); return
    if a.mod == "yeniden":                           # Serdar 8 Kas "Kodla yeniden yaz": pilot galeri yeni sirayla yeniden
        api = Kilitli(store)
        for c in ciftler:
            api.lid = None
            yeniden(api, shop, out, c, Y)
        return
    if a.mod == "sira":                              # Serdar 8 Kas: pilot sira duzeltmesi (yalniz CANCER_LIBRA beklenir)
        api = Kilitli(store)
        for c in ciftler:
            api.lid = None
            sira(api, shop, out, c, Y)
        return
    try:
        yaz_dongu(Kilitli(store), shop, out, ciftler, Y)
    finally:
        liste_yaz(out, Y)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
