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
GALERI = ["01_KAPAK", "02_AGAC", "03_ELLER", "04_STILLER", "05_KISISEL", "06_SEMBOL", "07_BOYUT", "08_SUREC", "09_YILBOYU",
          "10_RUBY", "11_SAPPHIRE", "12_EMERALD", "13_WHITE", "14_IVORY"]
if os.environ.get("SEMBOL_KARTI") == "1":       # Serdar 8 Kas: yayindaki sembol karti, 15. gorsel (gorsel onayi Serdar'da)
    GALERI = GALERI + ["15_SEMBOL_KARTI"]
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
    alt = [r["alt_01"], yeni2, yeni3, r["alt_06"], r["alt_03"], r["alt_02"], r["alt_04"], r["alt_05"], yeni9,
           r["alt_07"], r["alt_08"], r["alt_09"], r["alt_10"], r["alt_11"]]
    if len(GALERI) == 15:
        iki = f"two {A} signs" if a == b else f"the {A} and {B} signs"
        alt.append(f"{BAS} Two Signs, One Shared Symbol: {iki} joining into one original AstroLoveArt symbol in gold")
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
    if not getattr(api, "kuru", False) and pair != "CANCER_LIBRA" and "CANCER_LIBRA" not in D.get("tamam", []):   # pilot once (inceleme 9; kuru haric)
        kaydet(); raise SystemExit("DUR: CANCER_LIBRA pilotu tamam degil; once pilot")
    v0 = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    yabanci = [v.get("video_id") for v in v0 if v.get("video_id") not in eski_v and not d.get("video_gonderildi")]
    if yabanci:
        kaydet(); raise SystemExit(f"DUR: {pair} yedekte olmayan video {yabanci} (elle kontrol)")
    ims = gorseller()
    yeni = {int(k): v for k, v in d["yeni"].items()}
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
    yanlis = {n: rk.get(yeni[n]) for n in range(1, N_YENI + 1) if rk.get(yeni[n]) != n}
    if yanlis:   # inceleme 1: Etsy ayni rank'ta eskiyi kaydirmaz (6 Kas olcum, ESIT); yalniz yeni gorsellerin kendi rank'i denetlenir
        kaydet(); raise SystemExit(f"DUR: {pair} yeni gorsel rank'lari beklenen degil {yanlis}")
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

    def ilan(self, y):
        self.L = dict(listing_id=y["listing_id"], state=y["state"], title=y["baslik"])
        self.ims = [dict(listing_image_id=g["id"], rank=g["rank"], alt_text=g["alt"], full_width=g["w"], full_height=g["h"]) for g in y["gorsel"]]
        self.vids = [dict(video_id=v["id"], video_state=v["state"]) for v in y["video"]]
        self.vis = [dict(property_id=P_STYLE, value_id=int(k), image_id=v) for k, v in y["bag"].items()]
        self.inv = dict(products=[dict(property_values=[dict(property_id=P_STYLE, values=[s], value_ids=[i])]) for s, i in y["stil"].items()])

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
            self.ims = [x for x in self.ims if x["listing_image_id"] != i]       # olcum (30 Eyl): silme rank sikistirmaz
            return {}
        if method == "DELETE" and "/videos/" in path:
            i = int(path.rsplit("/", 1)[1]); self.vids = [v for v in self.vids if v["video_id"] != i]; return {}
        if path.endswith("/variation-images"):
            self.vis = js["variation_images"]; return dict(results=self.vis)
        if method == "PATCH":
            self.L["state"] = "inactive"; return self.L
        raise SystemExit(f"KURU: taklit edilmeyen {method} {path}")


def kuru(shop, out, pair, Y):
    api = Kuru(shop, Y)
    api.ilan(Y[pair])
    o2 = out / "kuru"; o2.mkdir(parents=True, exist_ok=True)
    (o2 / "DURUM9.json").unlink(missing_ok=True)
    R = yaz(api, shop, o2, pair, Y)
    yazma = [k for k in api.kayit if k["yazma"]]
    ozet = dict(cift=pair, istek=len(api.kayit), yazma=len(yazma), kontrol=R["kontrol"])
    json.dump(dict(ozet=ozet, istekler=api.kayit), open(o2 / f"KURU_{pair}.json", "w"), indent=1, ensure_ascii=False)
    print(f"KURU {pair}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol {sum(R['kontrol'].values())}/{len(R['kontrol'])}")
    (o2 / "DURUM9.json").unlink(missing_ok=True)
    return ozet


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
        w = csv.writer(fh); w.writerow(["cift", "listing_id", "durum", "neden", "link"])
        for c in CIFTLER:
            lid = (Y.get(c) or {}).get("listing_id", "")
            f = out / f"G9_{c}.json"
            hata = (json.load(open(f)).get("hata") or "") if f.exists() else ""
            d = D.get("ciftler", {}).get(c, {})
            durum = "TAMAM" if c in D.get("tamam", []) else "FAIL" if hata else "YARIM" if (d.get("yeni") or d.get("video_gonderildi")) else "BEKLIYOR"
            say[durum] = say.get(durum, 0) + 1
            w.writerow([c, lid, durum, hata[:300], f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}" if str(lid).isdigit() else ""])
    print(f"::warning::LISTE {say}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["yedek", "kuru", "yaz"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    ciftler = cift_listesi(a.ciftler)
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    if a.mod in ("kuru", "yaz"):
        Y = json.load(open(os.environ["YEDEK"]))
    if a.mod == "kuru":
        for c in ciftler:
            kuru(shop, out, c, Y)
        return
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    if a.mod == "yedek":
        harita = json.load(open(os.environ["TASLAK_DURUM"])).get("ciftler", {})
        yedek(SaltOkur(store), shop, out, ciftler, harita); return
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
