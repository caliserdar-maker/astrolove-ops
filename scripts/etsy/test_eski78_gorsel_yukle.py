#!/usr/bin/env python3
"""eski78_gorsel_yukle sahte testi (ag yok; Serdar 24 Eki B4 + son duzeltme turu). Sahte Etsy: kota tabani (istek gondermeden durur),
rank kaymasi (rank verince digerleri kayar), silinen kimligin yeniden verilmesi, GET okuma hatasi, yuklemede 429 / 4xx / 5xx /
yanit dusmesi / gec gorunme, alt metin bosluk farki, renk bagi davranisi. Senaryolar: ilk akis (pilot ve Parti 1 sekli), kapak ve
renk bagi suresi, cift yukleme yok, devam (kota), kurtarma (kota disi hata), belirsiz yukleme, kayit (LISTE / uretim kosusu),
bag / oku modlari, post_file tekrar parametresi."""
import copy
import csv
import io
import json
import os
import pathlib
import stat
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402

G.time.sleep = lambda s: None
Y.cdn_indir = lambda u: b"jpg"   # CDN yedek (ag yok)
RENK = {"Midnight Blue": (200, 1), "Deep Black": (200, 2), "Pure White": (200, 3), "Champagne Ivory": (200, 4), "Warm Parchment": (200, 5)}
LID = "4570155846"


def liste_yaz(tmp, hedef_islem, canli_id, cikar, renk_sira=(13, 14, 15, 16, 17)):
    rows, dosya = [], pathlib.Path(tmp) / "hedef"; dosya.mkdir()
    for s, isl in hedef_islem.items():
        ad = f"{s:02d}_{900 + s}.jpg"
        if isl == "DEGISTIR":
            (dosya / ad).write_bytes(f"jpg {s}".encode())
        rows.append(dict(hedef_sira=s, hedef_gorsel=ad, hedef_alt=f"alt {s}", islem=isl, simdi_sira="", simdi_id=canli_id.get(s, ""),
                         simdi_alt="", ncc="", fark="", en_yakin_hedef=""))
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira="", simdi_id=c, simdi_alt="", ncc="",
                  fark="", en_yakin_hedef="") for c in cikar]
    lp = pathlib.Path(tmp) / "LISTE.csv"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    man = dict(listing_id=LID, variation_images=[dict(value=ad, image_id=900 + s) for ad, s in zip(RENK, renk_sira)])
    mp = pathlib.Path(tmp) / "manifest.json"; mp.write_text(json.dumps(man))
    return lp, dosya, mp


def kur(tmp):
    """hedef 17: 1 KORU, 2 DEG, 3 ALT, 4 KORU, 5-9 DEG, 10 KORU, 11 12 DEG, 13-16 KORU (renk), 17 DEG (WP). Canli: 8 eslesen + 9 CIKAR."""
    hi = {1: "KORU", 2: "DEGISTIR", 3: "ALT", 4: "KORU", 5: "DEGISTIR", 6: "DEGISTIR", 7: "DEGISTIR", 8: "DEGISTIR", 9: "DEGISTIR",
          10: "KORU", 11: "DEGISTIR", 12: "DEGISTIR", 13: "KORU", 14: "KORU", 15: "KORU", 16: "KORU", 17: "DEGISTIR"}
    canli_id = {1: 501, 3: 503, 4: 504, 10: 511, 13: 514, 14: 515, 15: 516, 16: 517}
    cikar = [601, 602, 605, 606, 607, 608, 609, 610, 613]
    lp, dosya, mp = liste_yaz(tmp, hi, canli_id, cikar)
    canli = [(1, 601), (1, 501), (2, 602), (3, 503), (4, 504), (5, 605), (6, 606), (7, 607), (8, 608), (9, 609), (10, 610),
             (11, 511), (13, 613), (14, 514), (15, 515), (16, 516), (17, 517)]
    bag = {"Midnight Blue": 514, "Deep Black": 515, "Pure White": 516, "Champagne Ivory": 517, "Warm Parchment": 613}
    return lp, dosya, mp, canli, bag


def kur_gercek(tmp):
    """pilot plani: 1 KORU (kapak) / 16 DEGISTIR / 16 CIKAR; 4 renk bagi CIKAR gorsellerinde, WP bagsiz."""
    hi = {s: ("KORU" if s == 1 else "DEGISTIR") for s in range(1, 18)}
    cikar = list(range(601, 617))
    lp, dosya, mp = liste_yaz(tmp, hi, {1: 501}, cikar)
    canli = [(1, 501)] + [(i + 1, c) for i, c in enumerate(cikar)]
    bag = {"Midnight Blue": 613, "Deep Black": 614, "Pure White": 615, "Champagne Ivory": 616}
    return lp, dosya, mp, canli, bag


def kur_parti1(tmp):
    """Parti 1 sekli (inceleme O6): 0 KORU, 17 DEGISTIR (kapak dahil), canli 16 = 16 CIKAR, 4 renk bagi CIKAR'da, canli kapak CIKAR."""
    hi = {s: "DEGISTIR" for s in range(1, 18)}
    cikar = list(range(601, 617))
    lp, dosya, mp = liste_yaz(tmp, hi, {}, cikar)
    canli = [(i + 1, c) for i, c in enumerate(cikar)]
    bag = {"Midnight Blue": 613, "Deep Black": 614, "Pure White": 615, "Champagne Ivory": 616}
    return lp, dosya, mp, canli, bag


class Sahte:
    def __init__(self, canli, bag, kota=5000, state="active"):
        self.img = [dict(rank=r, listing_image_id=i, alt_text=f"eski {i}", url_fullxfull=f"u{i}") for r, i in canli]
        self.bag = dict(bag); self.remaining = kota; self.calls = 0; self.state = state; self.yeni = 7000
        self.yaz = []; self.vi_cagri = 0; self.max_n = len(self.img); self.sert_taban = 10
        self.sira_yut = 0          # ilk N rank POST'u etkisiz
        self.kaydir = False        # rank verince digerleri kayar (Etsy benzeri ekleme)
        self.alt_yut = False       # sira POST'u alt metni yazmaz
        self.alt_bosluk = False    # Etsy alt metne bosluk ekler (normalizasyon farki)
        self.kimlik_geri = False   # yeni yukleme son silinen kimligi alir
        self.alt_yukle_farkli = False   # yukleme alt metni farkli kaydeder (yalniz sira POST'u duzeltir)
        self.silinenler = []
        self.bag_yut = False; self.sira_bag_sil = False
        self.yukle_hata = {}       # {kacinci yukleme (1..): ("kod", olusur_mu, gec_okuma)}
        self.n_yukle = 0; self.gec_kuyruk = []; self.tekrar = []
        self.get_hata = set()      # GET sira numaralari -> SystemExit("HATA ... 503")
        self.n_get = 0
        self.izler = []            # her yazimdan sonra (kapak id, bag sayisi)
        self.yabanci = None        # (kacinci yukleme, alt): hata aninda galeride yabanci gorsel belirir
        self.rank_yut = False      # yuklemedeki rank parametresi yok sayilir (sona eklenir)

    def _k(self):   # etsy_common sert taban: istek GONDERILMEDEN durur; her istek kotadan 1 dusurur
        if self.remaining < self.sert_taban:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < {self.sert_taban}")
        self.remaining -= 1; self.calls += 1

    def _iz(self):
        g = sorted(self.img, key=lambda x: (x["rank"], x["listing_image_id"]))
        self.izler.append((g[0]["listing_image_id"] if g else None, len(self.bag)))

    def kota_kapisi(self, ne):
        if self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _alt(self, a):
        return a + "  " if self.alt_bosluk else a

    def get(self, path, params=None, ok404=False):
        self._k(); self.n_get += 1
        if self.n_get in self.get_hata:
            raise SystemExit(f"HATA: GET {path} -> 503: (test)")
        if path.endswith("/images"):
            for q in list(self.gec_kuyruk):
                q[0] -= 1
                if q[0] <= 0:
                    self.img.append(q[1]); self.gec_kuyruk.remove(q)
            return {"results": copy.deepcopy(sorted(self.img, key=lambda x: (x["rank"], x["listing_image_id"])))}
        if path.endswith("/variation-images"):
            return {"results": [dict(property_id=200, value_id=RENK[k][1], value=k, image_id=v) for k, v in self.bag.items()]}
        if path.endswith("/inventory"):
            return {"products": [dict(sku="s", offerings=[dict(price=1)], property_values=[dict(property_id=200,
                    value_ids=[v[1] for v in RENK.values()], values=list(RENK))])]}
        if path.endswith("/videos"):
            return {"results": []}
        return dict(state=self.state, title="T", tags=["a"], description="D")

    def delete(self, path, ok404=False):
        self._k(); iid = int(path.rsplit("/", 1)[1])
        if ok404 and all(x["listing_image_id"] != iid for x in self.img):
            self.yaz.append(("sil404", iid)); return None
        self.yaz.append(("sil", iid)); self.silinenler.append(iid)
        self.bag = {k: v for k, v in self.bag.items() if v != iid}   # bagli gorsel silinince bag cozulur (cl_galeri faz1)
        self.img = [x for x in self.img if x["listing_image_id"] != iid]
        self._iz()

    def post_file(self, path, files=None, data=None, tekrar=3):
        self._k()
        if "image" in (files or {}):
            self.tekrar.append(tekrar); self.n_yukle += 1
            h = self.yukle_hata.pop(self.n_yukle, None)
            if self.kimlik_geri and self.silinenler:
                yid = self.silinenler.pop()
            else:
                self.yeni += 1; yid = self.yeni
            x = dict(rank=max([y["rank"] for y in self.img] + [0]) + 1, listing_image_id=yid,
                     alt_text=self._alt(data["alt_text"]) + (" (eski)" if self.alt_yukle_farkli else ""),
                     url_fullxfull="u")
            rk = int((data or {}).get("rank") or 0)
            if rk and not self.rank_yut and not h:   # Etsy: verilen rank'e eklenir, o ve sonrakiler bir kayar
                for y in self.img:
                    if y["rank"] >= rk:
                        y["rank"] += 1
                x["rank"] = rk
            if h:
                kod, olusur, gec = h
                if self.yabanci and self.yabanci[0] == self.n_yukle:
                    self.img.append(dict(rank=99, listing_image_id=6999, alt_text=self.yabanci[1], url_fullxfull="u"))
                if olusur:
                    (self.gec_kuyruk.append([gec, x]) if gec else self.img.append(x))
                    self.yaz.append(("yukle", yid))
                else:
                    self.yaz.append(("yukle_hata", kod))
                self.max_n = max(self.max_n, len(self.img) + len(self.gec_kuyruk)); self._iz()
                raise SystemExit(f"HATA: POST(file) /x -> {kod}: (test)" if kod else "HATA: ag koptu (test)")
            self.img.append(x); self.yaz.append(("yukle", yid))
            self.max_n = max(self.max_n, len(self.img)); self._iz()
            return {"listing_image_id": yid}
        iid = int(files["listing_image_id"][1]); rk = int(files["rank"][1])
        if self.sira_yut > 0:
            self.sira_yut -= 1; self.yaz.append(("sira_yutuldu", iid, rk)); self._iz(); return {"listing_image_id": iid}
        x = next(y for y in self.img if y["listing_image_id"] == iid)
        if self.kaydir:   # Etsy benzeri: gorsel o siraya eklenir, digerleri kayar (tekil 1..n)
            g = sorted((y for y in self.img if y is not x), key=lambda y: (y["rank"], y["listing_image_id"]))
            g.insert(rk - 1, x)
            for i, y in enumerate(g, 1):
                y["rank"] = i
        else:
            x["rank"] = rk
        if not self.alt_yut:
            x["alt_text"] = self._alt(files["alt_text"][1])
        if self.sira_bag_sil:
            self.bag = {}
        self.yaz.append(("sira", iid, rk)); self._iz()
        return {"listing_image_id": iid}

    def post_json(self, path, body):
        self._k(); self.vi_cagri += 1; self.yaz.append(("bag",))
        if self.bag_yut:
            self.bag = {}; self._iz(); return {}
        self.bag = {k: next(v["image_id"] for v in body["variation_images"] if v["value_id"] == RENK[k][1]) for k in RENK}
        self._iz()


def kos(api, tmp, lp, dosya, mp, kuru=False, kota_ihtiyac=True, kurtar=False, uretim="40094556004"):
    try:
        return Y.bir_ilan(api, "1", LID, lp, dosya, mp, pathlib.Path(tmp) / "out", kuru=kuru, kota_ihtiyac=kota_ihtiyac,
                          kurtar=kurtar, uretim_kosu=uretim)
    except (Y.Dur, SystemExit) as e:
        return dict(sonuc="DUR", sorun=[str(e)])


def yuklemeler(api):
    return [y for y in api.yaz if y[0] == "yukle"]


def tamam(api, R, n_yukle):
    """PASS + 17 gorsel + rank 1..17 + alt metin hedef + 5 bag + cift yukleme yok (yukleme sayisi = DEGISTIR) + en fazla 17."""
    g = sorted(api.img, key=lambda x: x["rank"])
    alt_ok = [Y.alt_norm(x["alt_text"]) for x in g] == [f"alt {i}" for i in range(1, 18)]
    ids = [x["listing_image_id"] for x in g]
    return (R["sonuc"] == "PASS" and len(g) == 17 and [x["rank"] for x in g] == list(range(1, 18)) and alt_ok and len(api.bag) == 5
            and len(yuklemeler(api)) == n_yukle and len(set(ids)) == 17 and api.max_n <= 17 and not api.gec_kuyruk)


def temel():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp, kuru=True)
    s.append(("kuru: yazma yok, plan 9 cikar (1 bagli) / 9 yukle, kota durumu yazili", R["sonuc"] == "KURU" and api.yaz == []
              and len(R["plan"]["cikar"]) == 9 and R["plan"]["cikar_bagli"] == [613] and len(R["plan"]["yukle"]) == 9
              and "yeterli" in R["kota_durum"]))
    api = Sahte(canli, bag, kota=300); R = kos(api, tempfile.mkdtemp() and tmp, lp, dosya, mp, kuru=True)
    s.append(("kuru, kota yetmez: durmaz, KURU + 'kota yetersiz (kalan X, gereken Y)'", R["sonuc"] == "KURU" and "yetersiz" in R["kota_durum"]
              and "gereken" in R["kota_durum"] and api.yaz == []))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    g = sorted(api.img, key=lambda x: x["rank"])
    s.append(("PASS: 17 gorsel, rank 1..17, alt metin hedef, KORU kimlikleri korundu", tamam(api, R, 9)
              and g[0]["listing_image_id"] == 501 and g[3]["listing_image_id"] == 504 and g[12]["listing_image_id"] == 514))
    s.append(("renk baglari 2 cagri (erken + son); WP yeni gorsele, 4 renk KORU kimliklerinde", api.vi_cagri == 2
              and api.bag["Warm Parchment"] == g[16]["listing_image_id"] and api.bag["Midnight Blue"] == 514))
    s.append(("son yazim renk bagi; yuklemede rank yok (yalniz alt_text)", api.yaz[-1] == ("bag",)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli + [(18, 777)], bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("canli galeri LISTE'den farkli -> DUR, yazma yok", R["sonuc"] == "DUR" and "LISTE ile ayni degil" in R["sorun"][0]
              and api.yaz == []))
    api = Sahte(canli, bag, state="draft"); R = kos(api, tmp, lp, dosya, mp)
    s.append(("state draft -> DUR, yazma yok", R["sonuc"] == "DUR" and "active" in R["sorun"][0] and api.yaz == []))
    api = Sahte(canli, bag, kota=9); R = kos(api, tmp, lp, dosya, mp)
    s.append(("kota esigi -> DUR, yazma yok", R["sonuc"] == "DUR" and "kota" in R["sorun"][0] and api.yaz == []))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    rows = list(csv.DictReader(open(lp, encoding="utf-8"))); rows[2]["hedef_alt"] = "original AstroLove design"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("alt metinde Art'siz marka -> DUR, yazma yok", R["sonuc"] == "DUR" and "yasak" in R["sorun"][0] and api.yaz == []))
    return s


def plan_ve_kota():
    s = []
    gp = [dict(hedef_sira=x, hedef_gorsel=f"{x}") for x in range(2, 18)]
    a, mx = Y.adim_plani(17, list(range(601, 617)), {613, 614, 615, 616}, gp, {13, 14, 15, 16, 17})
    s.append(("plan (pilot, KORU kapak): kapak ilk adim, 2 bag (erken + son), sira sondan ikinci, en fazla 17", a[0] == ("kapak",)
              and a.count(("bag",)) == 2 and a[-1] == ("bag",) and a[-2] == ("sira",) and mx == 17))
    gp1 = [dict(hedef_sira=x, hedef_gorsel=f"{x}") for x in range(1, 18)]
    a1, mx1 = Y.adim_plani(16, list(range(601, 617)), {613, 614, 615, 616}, gp1, {13, 14, 15, 16, 17}, kapak_degisir=gp1[0])
    ilk_bag = a1.index(("bag",))
    bagli_sil = [i for i, x in enumerate(a1) if x[0] == "sil" and x[1] in {613, 614, 615, 616}]
    s.append(("plan (Parti 1): yeni kapak 1. adim + rank 1 2. adim; erken bag 5 renk yuklemesinden hemen sonra; bagli eski renk kartlari "
              "erken bagdan SONRA silinir; en fazla 17", a1[0] == ("yukle", "1") and a1[1] == ("kapak",)
              and a1[ilk_bag - 1] == ("yukle", "17") and all(i > ilk_bag for i in bagli_sil) and mx1 == 17))
    O = G.OKUMA_TEKRAR
    ek = Y.istek_en_kotu(a1)
    hesap = 7 + 16 * (3 + O) + 17 * (2 * O + 5) + (3 + O) + 2 * (17 * 3 + O) + 2 * (3 + O) + 2 * O + 3
    s.append((f"en kotu tahmin (Parti 1: 16 sil / 17 yukle / kapak / 2 bag) {ek} = {hesap}", ek == hesap))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag, kota=ek + 9); R = kos(api, tmp, lp, dosya, mp)
    s.append((f"kota: kalan {ek + 9} < en kotu {ek} + 10 -> yazmadan DUR", R["sonuc"] == "DUR" and "kota yetmez" in R["sorun"][0]
              and api.yaz == []))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag, kota=ek + 10); R = kos(api, tmp, lp, dosya, mp)
    s.append((f"kota: kalan {ek + 10} = en kotu + 10 -> baslar, PASS", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.sira_yut = 17; api.kaydir = True; R = kos(api, tmp, lp, dosya, mp)
    s.append((f"gercek istek ({api.calls}) <= en kotu tahmin ({ek}); sira 2 gecis + rank kaymasi", tamam(api, R, 17) and api.calls <= ek))
    return s


def parti1():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.kaydir = True; R = kos(api, tmp, lp, dosya, mp)
    hedef_kapak = R.get("yuklenen", {}).get("01_901.jpg")
    yanlis_kapak = sum(1 for i, (k, _) in enumerate(api.izler) if i >= 1 and k != hedef_kapak)   # kapak adimindan sonra
    bagsiz = sum(1 for _, b in api.izler if b < 4)
    s.append((f"Parti 1 sekli: PASS, 17 yukleme, en fazla 17 gorsel; kapak adimindan sonra yanlis kapak {yanlis_kapak} yazim; "
              f"bag sayisi < 4 olan yazim {bagsiz}", tamam(api, R, 17) and yanlis_kapak == 0 and bagsiz == 0))
    ky = R.get("yukleme_kaydi") or []
    import hashlib
    s.append(("icerik kaydi: 17 yukleme, sha256 dosyayla ayni + Etsy gorsel kimligi", len(ky) == 17 and all(k["listing_image_id"] for k in ky)
              and all(k["sha256"] == hashlib.sha256((dosya / k["hedef_gorsel"]).read_bytes()).hexdigest() for k in ky)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.kaydir = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("rank kaymasi (Etsy benzeri ekleme): PASS", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.kimlik_geri = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("Etsy silinen kimligi yeniden verir: PASS, cift yukleme yok", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.alt_bosluk = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("alt metin bosluk farki (Etsy normalizasyonu): PASS", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.sira_yut = 99; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira 2 geciste oturmaz -> DUR (hata), son bag yazilmaz, erken bag 5/5 duruyor", R["sonuc"] == "DUR"
              and "sira 2 geciste" in R["sorun"][0] and api.vi_cagri == 1 and len(api.bag) == 5))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.alt_yukle_farkli = True; api.alt_yut = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: alt metin oturmazsa DUR, son bag yazilmaz", R["sonuc"] == "DUR" and "sira 2 geciste" in R["sorun"][0]
              and api.vi_cagri == 1))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.alt_yukle_farkli = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: yuklemede farkli kaydedilen alt metni sira adimi duzeltir, PASS", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.sira_yut = 3; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: ilk gecis oturmazsa ikinci gecis, PASS", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.sira_bag_sil = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira POST baglari silse de son bag kurar: PASS 5/5", tamam(api, R, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.bag_yut = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("bag POST oturmaz -> DUR, bag tek cagri (tekrar yok)", R["sonuc"] == "DUR" and "renk baglari" in R["sorun"][0]
              and api.vi_cagri == 1))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag)
    Y.cdn_indir = lambda u: (_ for _ in ()).throw(OSError("404"))
    R = kos(api, tmp, lp, dosya, mp); Y.cdn_indir = lambda u: b"jpg"
    s.append(("CDN yedek inmezse yazim yok", R["sonuc"] == "DUR" and "CDN yedek" in R["sorun"][0] and api.yaz == []))
    return s


def yukleme_hatalari():
    s = []
    for ad, hata, bek in (("429, gorsel olusmadi: 15 sn bekler, bir kez daha gonderir, PASS", (429, False, 0), "PASS"),
                          ("400, gorsel olusmadi: tekrar YOK, DUR", (400, False, 0), "DUR"),
                          ("500, gorsel olusmadi: tekrar YOK, DUR", (500, False, 0), "DUR"),
                          ("502 ama gorsel olustu: galeride bulunur, tekrar yok, PASS", (502, True, 0), "PASS"),
                          ("yanit dustu, gorsel 5 okuma gec gorunur: beklenir, tekrar yok, PASS", (None, True, 5), "PASS")):
        tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
        api = Sahte(canli, bag); api.yukle_hata = {3: hata}; R = kos(api, tmp, lp, dosya, mp)
        ok = tamam(api, R, 17) if bek == "PASS" else (R["sonuc"] == "DUR" and len(api.tekrar) == 3 and len(yuklemeler(api)) == 2)
        if bek == "PASS" and hata[0] == 429:
            ok = ok and len(api.tekrar) == 18
        s.append((f"yukleme {ad}", ok and set(api.tekrar) == {1}))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.yukle_hata = {3: (502, False, 0)}; api.yabanci = (3, "baska"); R = kos(api, tmp, lp, dosya, mp)
    s.append(("hata + galeride baska alt metinli yeni gorsel: bizim sayilmaz, DUR", R["sonuc"] == "DUR" and "alt metin farkli" in R["sorun"][0]))
    return s


def devam_kesitleri():
    """Kota tabani her kesim noktasinda: 1. kosu durur (ilan basi kontrol kapali), 2. kosu kota acilinca ayni kayitla tamamlar."""
    kotu = []; n = 0
    for kes in range(12, 300, 6):
        tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
        api = Sahte(canli, bag, kota=10 + kes); api.sira_yut = 3; api.kaydir = True
        R1 = kos(api, tmp, lp, dosya, mp, kota_ihtiyac=False)
        api.remaining = 5000
        R2 = kos(api, tmp, lp, dosya, mp); n += 1
        if not tamam(api, R2, 17):
            kotu.append((kes, R1.get("sonuc"), (R1.get("sorun") or [""])[0][:40], R2.get("sonuc"), (R2.get("sorun") or [""])[0][:70]))
    devam_kesitleri.ok = not kotu
    return f"{n - len(kotu)}/{n} kesim" + (f" | kotu {kotu[:3]}" if kotu else "")


def kurtarma_kesitleri():
    """Kota DISI hata (GET 503) her kesim noktasinda: 1. kosu DUR + hata kaydi; normal devam DUR (otomatik devam yok);
    --kurtar kayitli plan + kararli galeriyle tamamlar (DEVAM elle duzeltilmez), cift yukleme yok."""
    kotu = []; n = 0
    for kes in range(6, 140, 4):
        tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
        api = Sahte(canli, bag); api.get_hata = {kes}; api.kimlik_geri = (kes % 3 == 0)
        R1 = kos(api, tmp, lp, dosya, mp)
        api.get_hata = set()
        R2 = kos(api, tmp, lp, dosya, mp)
        R3 = kos(api, tmp, lp, dosya, mp, kurtar=True) if R1["sonuc"] == "DUR" else R1
        n += 1
        devam_engel = R1["sonuc"] == "PASS" or ("otomatik devam yok" in (R2.get("sorun") or [""])[0] or R2["sonuc"] == "PASS"
                                                or "galeri LISTE ile ayni degil" not in (R2.get("sorun") or [""])[0])
        if not (tamam(api, R3, 17) and devam_engel):
            kotu.append((kes, (R1.get("sorun") or [""])[0][:40], R2.get("sonuc"), (R3.get("sorun") or [""])[0][:70]))
    kurtarma_kesitleri.ok = not kotu
    return f"{n - len(kotu)}/{n} kesim" + (f" | kotu {kotu[:3]}" if kotu else "")


def kurtarma():
    s = []
    s.append(("ilan ortasinda kota durmasi -> devam tamamlar (cift yukleme yok, 17 gorsel, 5 bag): " + devam_kesitleri(), devam_kesitleri.ok))
    s.append(("kota disi hata (GET 503) -> kurtarma tamamlar: " + kurtarma_kesitleri(), kurtarma_kesitleri.ok))
    # belirsiz yukleme: 502, gorsel gec olusur (hata okumasinda gorunmez) -> DUR; kurtarma gorseli bulur, yeniden yuklemez
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.yukle_hata = {5: (502, True, 99)}; R1 = kos(api, tmp, lp, dosya, mp)
    for q in api.gec_kuyruk:
        q[0] = 1
    R2 = kos(api, tmp, lp, dosya, mp, kurtar=True)
    s.append(("belirsiz yukleme (gorsel gec olustu) -> DUR; kurtarma galeride bulur, yeniden yuklemez, PASS", R1["sonuc"] == "DUR"
              and tamam(api, R2, 17)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); api.yukle_hata = {5: (502, False, 0)}; R1 = kos(api, tmp, lp, dosya, mp)
    n = len(yuklemeler(api)); R2 = kos(api, tmp, lp, dosya, mp, kurtar=True)
    s.append(("belirsiz yukleme (gorsel olusmadi) -> kurtarma DUR, yukleme YOK (belirsizde yukleme yapilmaz)", R1["sonuc"] == "DUR"
              and R2["sonuc"] == "DUR" and "belirsiz" in R2["sorun"][0] and len(yuklemeler(api)) == n))
    # inceleme Y2: belirsiz yuklemenin (502, gorsel gec olusur) okuma penceresinde kota tabani -> devam belirsiz kaydini gorur;
    # gorsel sonra belirirse bulunur (yeniden yuklenmez), hic belirmezse DUR (yukleme yok)
    pencere, kotu = 0, []
    for kalan in range(15, 90):
        for belirir in (True, False):
            tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
            api = Sahte(canli, bag, kota=10 + kalan); api.yukle_hata = {4: (502, True, 99)}
            R1 = kos(api, tmp, lp, dosya, mp, kota_ihtiyac=False)
            dv = pathlib.Path(tmp) / "out" / f"DEVAM_{LID}.json"
            if not ("kota" in (R1.get("sorun") or [""])[0] and dv.exists() and json.loads(dv.read_text()).get("belirsiz")):
                continue
            pencere += 1; api.remaining = 5000; n = len(yuklemeler(api))
            if belirir:
                for q in api.gec_kuyruk:
                    q[0] = 1
            else:
                api.gec_kuyruk = []
            R2 = kos(api, tmp, lp, dosya, mp)
            ok = tamam(api, R2, 17) if belirir else (R2["sonuc"] == "DUR" and "belirsiz" in R2["sorun"][0] and len(yuklemeler(api)) == n)
            if not ok:
                kotu.append((kalan, belirir, (R2.get("sorun") or [""])[0][:60]))
    s.append((f"belirsiz yukleme okumasinda kota tabani ({pencere} durum): gorsel belirirse bulunur, belirmezse DUR; cift yukleme yok"
              + (f" | kotu {kotu[:2]}" if kotu else ""), pencere > 0 and not kotu))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag, kota=10 + 60); R1 = kos(api, tmp, lp, dosya, mp, kota_ihtiyac=False); api.remaining = 5000
    R2 = kos(api, tmp, lp, dosya, mp, uretim="40099999999")
    s.append(("devam baska uretim kosusuyla -> DUR, yazim yok", R1["sonuc"] == "DUR" and R2["sonuc"] == "DUR"
              and "baska LISTE / uretim" in R2["sorun"][0]))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag, kota=10 + 60); R1 = kos(api, tmp, lp, dosya, mp, kota_ihtiyac=False); api.remaining = 5000
    (dosya / "17_917.jpg").write_bytes(b"baska")
    yk = json.loads((pathlib.Path(tmp) / "out" / f"DEVAM_{LID}.json").read_text()).get("sha", {})
    R2 = kos(api, tmp, lp, dosya, mp)
    s.append(("devamda yuklenmis dosyanin icerigi degismis -> DUR", "17_917.jpg" in yk and R2["sonuc"] == "DUR"
              and "sha256" in R2["sorun"][0]))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp, kurtar=True)
    s.append(("kurtarma DEVAM kaydi yokken -> DUR, yazim yok", R["sonuc"] == "DUR" and api.yaz == []))
    return s


def kayit_drive():
    """DEVAM_HEDEF: her yaz() rclone copyto (sahte rclone: kopya sayar)."""
    d = pathlib.Path(tempfile.mkdtemp()); r = d / "rclone"; say = d / "say"
    r.write_text(f"#!/bin/sh\ncp \"$2\" \"$3\" && echo x >> {say}\n"); r.chmod(r.stat().st_mode | stat.S_IEXEC)
    eski = os.environ.get("PATH", ""); os.environ["PATH"] = f"{d}:{eski}"; os.environ["DEVAM_HEDEF"] = str(d / "drive.json")
    try:
        tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_parti1(tmp)
        api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
        n = len(say.read_text().split()) if say.exists() else 0
        dv = json.loads((d / "drive.json").read_text())
    finally:
        os.environ["PATH"] = eski; os.environ.pop("DEVAM_HEDEF", None)
    return [(f"DEVAM her yazimdan once ve sonra Drive'a ({n} kopya); kayitta LISTE sha256 + uretim kosusu", R["sonuc"] == "PASS"
             and n >= 2 * len(dv["plan"]) and dv.get("uretim_kosu") == "40094556004" and len(dv.get("liste_sha", "")) == 64)]


def post_file_testleri():
    """etsy_common.post_file tekrar parametresi: tekrar=1 hata yanitinda yeniden gondermez; 401 bir kez yenilenir; varsayilan 3."""
    import etsy_common as E
    E.time.sleep = lambda s: None

    class Yn:
        def __init__(self, kod):
            self.status_code, self.headers, self.text = kod, {}, "x"

        def json(self):
            return {"listing_image_id": 1}

    class St:
        def refresh(self):
            pass
    out = []
    for kodlar, tekrar, bek_cagri, bek_ok in (([500, 200], 1, 1, False), ([401, 200], 1, 2, True), ([401, 500, 200], 1, 2, False),
                                              ([500, 500, 200], 3, 3, True), ([500, 500, 500, 200], 3, 3, False),
                                              ([401, 500, 200], 3, 3, True)):
        seri = list(kodlar); n = [0]

        def post(*a, **k):
            n[0] += 1; return Yn(seri.pop(0))
        E.requests.post = post
        api = E.Etsy.__new__(E.Etsy); api.calls = 0; api.pace = 0; api.verbose_quota = False; api.remaining = None
        api.store = St(); api._headers = lambda: {}; api._istek_oncesi = lambda: None
        try:
            api.post_file("/x", files={"image": ("a", io.BytesIO(b"1"), "image/jpeg")}, tekrar=tekrar); ok = True
        except SystemExit:
            ok = False
        out.append((f"post_file {kodlar} tekrar={tekrar}: {bek_cagri} gonderim, {'basari' if bek_ok else 'hata'}",
                    n[0] == bek_cagri and ok == bek_ok))
    return out


def bag_hazir():
    """pilot tam akisla yazilir, sonra baglar silinir (40091265199 durumu); bag/oku modu icin DEVAM kaydi."""
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    assert R["sonuc"] == "PASS", R
    hedef = {k: v for k, v in api.bag.items()}; api.bag = {}; api.yaz = []; api.vi_cagri = 0
    return tmp, lp, mp, api, hedef


def kos_bag(api, tmp, lp, mp, yaz, bag_arg=None):
    try:
        return Y.bag_kur(api, "1", LID, lp, mp, pathlib.Path(tmp) / "out" / f"DEVAM_{LID}.json",
                         pathlib.Path(tmp) / "bag", bag_arg=bag_arg, yaz=yaz)
    except (Y.Dur, SystemExit) as e:
        return dict(sonuc="DUR", sorun=[str(e)])


def bag_testleri():
    s = []
    tmp, lp, mp, api, hedef = bag_hazir(); R = kos_bag(api, tmp, lp, mp, False)
    s.append(("oku modu: yazma yok, bos baglar FAIL (0/5)", api.yaz == [] and R["sonuc"] == "FAIL" and R["bag_sayisi"] == 0))
    R = kos_bag(api, tmp, lp, mp, True, bag_arg=dict(hedef))
    s.append(("bag modu: TEK variation-images cagrisi, gorsele yazim yok, 5/5 PASS, 17 gorsel", R["sonuc"] == "PASS"
              and api.yaz == [("bag",)] and R["bag_sayisi"] == 5 and R["gorsel"] == 17))
    n = len(api.yaz); R = kos_bag(api, tmp, lp, mp, False)
    s.append(("ayri salt okuma: 5/5 PASS, yazma yok", R["sonuc"] == "PASS" and len(api.yaz) == n and R["bag_sayisi"] == 5))
    tmp, lp, mp, api, hedef = bag_hazir(); yanlis = dict(hedef); yanlis["Deep Black"] = 1
    R = kos_bag(api, tmp, lp, mp, True, bag_arg=yanlis)
    s.append(("verilen bag hesaplanandan farkli -> DUR, yazma yok", R["sonuc"] == "DUR" and "ayni degil" in R["sorun"][0] and api.yaz == []))
    tmp, lp, mp, api, hedef = bag_hazir(); api.img[0]["alt_text"] = "baska"
    R = kos_bag(api, tmp, lp, mp, True)
    s.append(("galeri alt metni hedeften farkli -> DUR, bag yazilmaz", R["sonuc"] == "DUR" and "galeri hedefle" in R["sorun"][0]
              and api.yaz == []))
    tmp, lp, mp, api, hedef = bag_hazir(); api.bag_yut = True; R = kos_bag(api, tmp, lp, mp, True)
    s.append(("bag yazildi ama geri okuma bos -> FAIL, yeniden yazma yok (1 cagri)", R["sonuc"] == "FAIL" and api.vi_cagri == 1
              and any("yeniden yazma YOK" in x for x in R["sorun"])))
    tmp, lp, mp, api, hedef = bag_hazir(); api.remaining = 39
    R = kos_bag(api, tmp, lp, mp, True)   # kota 39 - tahmini 30 < 10 (tahmini istek + 10 kurali)
    s.append(("bag modu kota: kalan - tahmini < sert taban -> DUR, yazma yok", R["sonuc"] == "DUR" and "kota yetmez" in R["sorun"][0]
              and api.yaz == []))
    return s


def main():
    s = temel() + plan_ve_kota() + parti1() + yukleme_hatalari() + kurtarma() + kayit_drive() + bag_testleri() + post_file_testleri()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"eski78_gorsel_yukle testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
