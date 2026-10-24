#!/usr/bin/env python3
"""eski78_gorsel_yukle sahte testi (ag yok, Serdar 24 Eki B4): ARIES_VIRGO benzeri canli galeri (17 gorsel, rank 1 iki kez, rank 12
yok, 4 renk bagi KORU gorsellerinde, WP bagi CIKAR gorselinde) -> hedef 17; on kosul, kota, 20 siniri, renk baglari tek cagri,
sira + alt metin, korunanlar, devam kaydi."""
import copy
import csv
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402

G.time.sleep = lambda s: None
Y.cdn_indir = lambda u: b"jpg"   # CDN yedek (ag yok)
RENK = {"Midnight Blue": (200, 1), "Deep Black": (200, 2), "Pure White": (200, 3), "Champagne Ivory": (200, 4), "Warm Parchment": (200, 5)}


def kur(tmp):
    """hedef 17: 1 KORU, 2 DEG, 3 ALT, 4 KORU, 5-9 DEG, 10 KORU, 11 12 DEG, 13-16 KORU (renk), 17 DEG (WP). Canli: 8 eslesen + 9 CIKAR."""
    hedef_islem = {1: "KORU", 2: "DEGISTIR", 3: "ALT", 4: "KORU", 5: "DEGISTIR", 6: "DEGISTIR", 7: "DEGISTIR", 8: "DEGISTIR",
                   9: "DEGISTIR", 10: "KORU", 11: "DEGISTIR", 12: "DEGISTIR", 13: "KORU", 14: "KORU", 15: "KORU", 16: "KORU", 17: "DEGISTIR"}
    canli_id = {1: 501, 3: 503, 4: 504, 10: 511, 13: 514, 14: 515, 15: 516, 16: 517}
    cikar = [601, 602, 605, 606, 607, 608, 609, 610, 613]
    rows, dosya = [], pathlib.Path(tmp) / "hedef"; dosya.mkdir()
    for s, isl in hedef_islem.items():
        ad = f"{s:02d}_{900 + s}.jpg"
        if isl == "DEGISTIR":
            (dosya / ad).write_bytes(b"jpg")
        rows.append(dict(hedef_sira=s, hedef_gorsel=ad, hedef_alt=f"alt {s}", islem=isl, simdi_sira="", simdi_id=canli_id.get(s, ""),
                         simdi_alt="", ncc="", fark="", en_yakin_hedef=""))
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira="", simdi_id=c, simdi_alt="", ncc="",
                  fark="", en_yakin_hedef="") for c in cikar]
    lp = pathlib.Path(tmp) / "LISTE.csv"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    man = dict(listing_id="4570155846", variation_images=[dict(value=ad, image_id=900 + s) for ad, s in
                                                         zip(RENK, (13, 14, 15, 16, 17))])
    mp = pathlib.Path(tmp) / "manifest.json"; mp.write_text(json.dumps(man))
    canli = [(1, 601), (1, 501), (2, 602), (3, 503), (4, 504), (5, 605), (6, 606), (7, 607), (8, 608), (9, 609), (10, 610),
             (11, 511), (13, 613), (14, 514), (15, 515), (16, 516), (17, 517)]
    bag = {"Midnight Blue": 514, "Deep Black": 515, "Pure White": 516, "Champagne Ivory": 517, "Warm Parchment": 613}
    return lp, dosya, mp, canli, bag


class Sahte:
    def __init__(self, canli, bag, kota=900, state="active"):
        self.img = [dict(rank=r, listing_image_id=i, alt_text=f"eski {i}", url_fullxfull=f"u{i}") for r, i in canli]
        self.bag = dict(bag); self.remaining = kota; self.calls = 0; self.state = state; self.yeni = 7000
        self.yaz = []; self.vi_cagri = 0; self.max_n = len(self.img); self.boz = None
        self.sert_taban = 10;   self.sira_yut = 0   # sira_yut: ilk N rank cagrisi etkisiz (kapak_yukle_78 28 Eyl gozlemi)
        self.sira_bag_sil = False; self.bag_yut = False; self.tekrar = []; self.gitmedi_oldu = False   # 40091265199 hipotezi: rank/alt POST baglari siler; bag POST oturmaz
        self.alt_yut = False; self.gec = 0; self.gec_kuyruk = []   # alt_yut: sira POST'u alt metni yazmaz; gec: yukleme N okuma sonra gorunur

    def _k(self):   # etsy_common sert taban: istek GONDERILMEDEN durur; her istek kotadan 1 dusurur
        if self.remaining < self.sert_taban:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < {self.sert_taban}")
        self.remaining -= 1; self.calls += 1

    def kota_kapisi(self, ne):
        if self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def get(self, path, params=None, ok404=False):
        self._k()
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

    def delete(self, path):
        self._k(); iid = int(path.rsplit("/", 1)[1]); self.yaz.append(("sil", iid))
        self.bag = {k: v for k, v in self.bag.items() if v != iid}   # bagli gorsel silinince bag cozulur (cl_galeri faz1)
        self.img = [x for x in self.img if x["listing_image_id"] != iid]

    def post_file(self, path, files=None, data=None, tekrar=3):
        self._k()
        if "image" in (files or {}):
            self.tekrar.append(tekrar)
            if self.boz in ("gitmedi", "gitmedi500") and self.yeni == 7002 and not self.gitmedi_oldu:   # hata, gorsel olusmadi
                self.gitmedi_oldu = True; self.yaz.append(("yukle_hata",))
                raise SystemExit(f"HATA: POST(file) /x -> {400 if self.boz == 'gitmedi' else 500}: (test)")
            if self.boz == "yabanci" and self.yeni == 7002 and not self.gitmedi_oldu:   # hata + baska kaynaktan gorsel belirir
                self.gitmedi_oldu = True; self.img.append(dict(rank=99, listing_image_id=6999, alt_text="baska", url_fullxfull="u"))
                raise SystemExit("HATA: POST(file) /x -> 502: (test)")
            self.yeni += 1
            x = dict(rank=99, listing_image_id=self.yeni, alt_text=data["alt_text"], url_fullxfull="u")
            if self.gec and self.boz == "yukle" and self.yeni == 7003:
                self.gec_kuyruk.append([self.gec, x])
            else:
                self.img.append(x)
            self.max_n = max(self.max_n, len(self.img) + len(self.gec_kuyruk)); self.yaz.append(("yukle", self.yeni, tuple(sorted(data))))
            if self.boz == "yukle" and self.yeni == 7003:
                raise SystemExit("HATA: ag koptu (test)")
            return {"listing_image_id": self.yeni}
        iid = int(files["listing_image_id"][1]); rk = int(files["rank"][1])
        if self.sira_yut > 0:
            self.sira_yut -= 1; self.yaz.append(("sira_yutuldu", iid, rk)); return {"listing_image_id": iid}
        for x in self.img:
            if x["listing_image_id"] == iid:
                x["rank"] = rk
                if not self.alt_yut:
                    x["alt_text"] = files["alt_text"][1]
        if self.sira_bag_sil:
            self.bag = {}
        self.yaz.append(("sira", iid, rk))
        return {"listing_image_id": iid}

    def post_json(self, path, body):
        self._k(); self.vi_cagri += 1; self.yaz.append(("bag",))
        if self.bag_yut:
            self.bag = {}; return {}
        self.bag = {k: next(v["image_id"] for v in body["variation_images"] if v["value_id"] == RENK[k][1]) for k in RENK}


def kur_gercek(tmp):
    """24 Eki inceleme: duzeltilmis kartlarla gercek pilot plani 1 KORU / 16 DEGISTIR / 16 CIKAR; 4 renk bagi CIKAR gorsellerinde,
    WP bagsiz. Eski algoritma 20 gorsel sinirinda yarida duruyordu."""
    rows, dosya = [], pathlib.Path(tmp) / "hedef"; dosya.mkdir()
    for s in range(1, 18):
        ad = f"{s:02d}_{900 + s}.jpg"
        isl = "KORU" if s == 1 else "DEGISTIR"
        if isl == "DEGISTIR":
            (dosya / ad).write_bytes(b"jpg")
        rows.append(dict(hedef_sira=s, hedef_gorsel=ad, hedef_alt=f"alt {s}", islem=isl, simdi_sira="", simdi_id=501 if s == 1 else "",
                         simdi_alt="", ncc="", fark="", en_yakin_hedef=""))
    cikar = list(range(601, 617))
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira="", simdi_id=c, simdi_alt="", ncc="",
                  fark="", en_yakin_hedef="") for c in cikar]
    lp = pathlib.Path(tmp) / "LISTE.csv"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    man = dict(listing_id="4570155846", variation_images=[dict(value=ad, image_id=900 + s) for ad, s in zip(RENK, (13, 14, 15, 16, 17))])
    mp = pathlib.Path(tmp) / "manifest.json"; mp.write_text(json.dumps(man))
    canli = [(1, 501)] + [(i + 1, c) for i, c in enumerate(cikar)]
    bag = {"Midnight Blue": 613, "Deep Black": 614, "Pure White": 615, "Champagne Ivory": 616}
    return lp, dosya, mp, canli, bag


def gercekci():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    g = sorted(api.img, key=lambda x: x["rank"])
    s.append(("gercekci pilot (1 KORU / 16 DEG / 16 CIKAR, 4 bag CIKAR'da): PASS, en fazla 17 gorsel, 5 bag yeni kartlarda",
              R["sonuc"] == "PASS" and api.max_n <= 17 and len(g) == 17 and api.vi_cagri == 1
              and all(api.bag[k] == g[s_ - 1]["listing_image_id"] for k, s_ in zip(RENK, (13, 14, 15, 16, 17)))))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    en_kotu = Y.istek_en_kotu(Y.adim_plani(17, list(range(601, 617)), set(), [dict(hedef_sira=s_, hedef_gorsel=f"{s_}") for s_ in
                                                                              range(2, 18)], {13, 14, 15, 16, 17})[0])
    api = Sahte(canli, bag, kota=en_kotu + 9); R = kos(api, tmp, lp, dosya, mp)
    s.append((f"kota: kalan {en_kotu + 9} - en kotu tahmin {en_kotu} < 10 -> yazmadan DUR", R["sonuc"] == "DUR"
              and "kota yetmez" in R["sorun"][0] and api.yaz == []))
    s.append((f"en kotu tahmin (16 sil / 16 yukle) {en_kotu} = 7 + 16x11 + 16x21 + 2x(17x3+8) + 11 + 19",
              en_kotu == 7 + 16 * 11 + 16 * 21 + 2 * (17 * 3 + 8) + 11 + 19))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag, kota=5000); api.sira_yut = 17; R = kos(api, tmp, lp, dosya, mp)
    s.append((f"gercek istek ({api.calls}) <= en kotu tahmin ({en_kotu}), sira 2 gecis dahil", R["sonuc"] == "PASS" and api.calls <= en_kotu))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.alt_yut = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: alt metin oturmazsa 2 gecis sonra DUR, renk bagi yazilmaz", R["sonuc"] == "DUR" and "sira 2 geciste" in R["sorun"][0]
              and api.vi_cagri == 0))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag)
    Y.cdn_indir = lambda u: (_ for _ in ()).throw(OSError("404"))
    R = kos(api, tmp, lp, dosya, mp); Y.cdn_indir = lambda u: b"jpg"
    s.append(("CDN yedek inmezse yazim yok", R["sonuc"] == "DUR" and "CDN yedek" in R["sorun"][0] and api.yaz == []))
    s.append(("ilan ortasinda kota durmasi -> devam kosusu tamamlar (cift yukleme yok, 17 gorsel, 5 bag): "
              + devam_kesitleri(), devam_kesitleri.ok))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.sira_yut = 99; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira 2 geciste oturmaz -> DUR, renk bagi yazilmaz", R["sonuc"] == "DUR" and "sira 2 geciste" in R["sorun"][0]
              and api.vi_cagri == 0))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    ky = R.get("yukleme_kaydi") or []
    import hashlib
    s.append(("icerik kaydi: 16 yukleme, her biri sha256 (dosyayla ayni) + Etsy gorsel kimligi", R["sonuc"] == "PASS" and len(ky) == 16
              and all(k["listing_image_id"] for k in ky)
              and all(k["sha256"] == hashlib.sha256((dosya / k["hedef_gorsel"]).read_bytes()).hexdigest() for k in ky)))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.sira_yut = 3; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: ilk gecis oturmazsa ikinci gecis, PASS", R["sonuc"] == "PASS"
              and len([y for y in api.yaz if y[0] == "sira"]) == 17 + 14))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    rows = list(csv.DictReader(open(lp, encoding="utf-8"))); rows[2]["hedef_alt"] = "original AstroLove design"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("alt metinde Art'siz marka -> DUR, yazma yok", R["sonuc"] == "DUR" and "yasak" in R["sorun"][0] and api.yaz == []))
    a, mx = Y.adim_plani(17, list(range(601, 617)), {613, 614, 615, 616}, [dict(hedef_sira=s_, hedef_gorsel=f"{s_}") for s_ in
                                                                          range(2, 18)], {13, 14, 15, 16, 17})
    s.append(("adim plani: sira sondan ikinci, bag EN SONDA (tek); en fazla 17", mx == 17 and a[-1] == ("bag",) and a[-2] == ("sira",)
              and a.count(("bag",)) == 1))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.sira_bag_sil = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira POST baglari silse de (40091265199 hipotezi) bag en sonda: PASS 5/5", R["sonuc"] == "PASS" and len(api.bag) == 5))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.bag_yut = True; R = kos(api, tmp, lp, dosya, mp)
    s.append(("bag POST oturmaz (geri okuma bos) -> DUR, bag tek cagri, tekrar yok", R["sonuc"] == "DUR" and "renk baglari" in R["sorun"][0]
              and api.vi_cagri == 1))
    s += bag_testleri()
    s += post_file_testleri()
    return s


def post_file_testleri():
    """etsy_common.post_file tekrar parametresi: tekrar=1 hata yanitinda yeniden gondermez; 401 bir kez yenilenir; varsayilan 3."""
    import etsy_common as E
    E.time.sleep = lambda s: None

    class Y:
        def __init__(self, kod):
            self.status_code, self.headers, self.text = kod, {}, "x"

        def json(self):
            return {"listing_image_id": 1}

    class St:
        n = 0

        def refresh(self):
            St.n += 1
    out = []
    for kodlar, tekrar, bek_cagri, bek_ok in (([500, 200], 1, 1, False), ([401, 200], 1, 2, True), ([500, 500, 200], 3, 3, True),
                                              ([500, 500, 500, 200], 3, 3, False)):
        seri = list(kodlar); n = [0]

        def post(*a, **k):
            n[0] += 1; return Y(seri.pop(0))
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
    """gercekci pilot tam akisla yazilir, sonra baglar silinir (40091265199 durumu); bag/oku modu icin DEVAM kaydi."""
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    assert R["sonuc"] == "PASS", R
    hedef = {k: v for k, v in api.bag.items()}; api.bag = {}; api.yaz = []; api.vi_cagri = 0
    return tmp, lp, mp, api, hedef


def kos_bag(api, tmp, lp, mp, yaz, bag_arg=None):
    try:
        return Y.bag_kur(api, "1", "4570155846", lp, mp, pathlib.Path(tmp) / "out" / "DEVAM_4570155846.json",
                         pathlib.Path(tmp) / "bag", bag_arg=bag_arg, yaz=yaz)
    except (Y.Dur, SystemExit) as e:
        return dict(sonuc="DUR", sorun=[str(e)])


def bag_testleri():
    s = []
    tmp, lp, mp, api, hedef = bag_hazir(); R = kos_bag(api, tmp, lp, mp, False)
    s.append(("oku modu: yazma yok, bos baglar FAIL (0/5)", api.yaz == [] and R["sonuc"] == "FAIL" and R["bag_sayisi"] == 0))
    R = kos_bag(api, tmp, lp, mp, True, bag_arg=dict(hedef))
    s.append(("bag modu: TEK variation-images cagrisi, gorsele yazim yok, 5/5 PASS, 17 gorsel", R["sonuc"] == "PASS"
              and api.yaz == [("bag",)] and R["bag_sayisi"] == 5 and R["gorsel"] == 17
              and (pathlib.Path(tmp) / "bag" / "BAG_4570155846.json").exists()))
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


def devam_kesitleri():
    """Her kesim noktasinda: 1. kosu kota tabaninda durur (ilan basi kontrol kapali), 2. kosu kota acilinca ayni kayitla tamamlar."""
    kotu = []; n = 0
    for kes in range(12, 260, 5):
        tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
        api = Sahte(canli, bag, kota=10 + kes); api.sira_yut = 3
        R1 = kos(api, tmp, lp, dosya, mp, kota_ihtiyac=False)
        api.remaining = 5000
        R2 = kos(api, tmp, lp, dosya, mp)
        g = sorted(api.img, key=lambda x: x["rank"]); n += 1
        if not (R2["sonuc"] == "PASS" and len(g) == 17 and len([y for y in api.yaz if y[0] == "yukle"]) == 16 and len(api.bag) == 5
                and api.max_n <= 17):
            kotu.append((kes, R1.get("sonuc"), (R1.get("sorun") or [""])[0][:40], R2.get("sonuc"), (R2.get("sorun") or [""])[0][:60]))
    devam_kesitleri.ok = not kotu
    return f"{n - len(kotu)}/{n} kesim" + (f" | kotu {kotu[:3]}" if kotu else "")


def kos(api, tmp, lp, dosya, mp, kuru=False, kota_ihtiyac=True):
    try:
        return Y.bir_ilan(api, "1", "4570155846", lp, dosya, mp, pathlib.Path(tmp) / "out", kuru=kuru, kota_ihtiyac=kota_ihtiyac)
    except (Y.Dur, SystemExit) as e:
        return dict(sonuc="DUR", sorun=[str(e)])


def main():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp, kuru=True)
    s.append(("kuru: yazma yok, plan 9 cikar (1 bagli) / 9 yukle", R["sonuc"] == "KURU" and api.yaz == [] and api.vi_cagri == 0
              and len(R["plan"]["cikar"]) == 9 and R["plan"]["cikar_bagli"] == [613] and len(R["plan"]["yukle"]) == 9))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    g = sorted(api.img, key=lambda x: x["rank"])
    s.append(("PASS: 17 gorsel, rank 1..17, alt metin hedef, KORU kimlikleri korundu", R["sonuc"] == "PASS" and len(g) == 17
              and [x["rank"] for x in g] == list(range(1, 18)) and [x["alt_text"] for x in g] == [f"alt {i}" for i in range(1, 18)]
              and g[0]["listing_image_id"] == 501 and g[3]["listing_image_id"] == 504 and g[12]["listing_image_id"] == 514))
    s.append(("renk baglari tek cagri; WP yeni gorsele, 4 renk KORU kimliklerinde", api.vi_cagri == 1
              and api.bag["Warm Parchment"] == g[16]["listing_image_id"] and api.bag["Midnight Blue"] == 514
              and api.bag["Champagne Ivory"] == 517))
    s.append(("gorsel sayisi en fazla 18; son yazim renk bagi (sira + alt metinden sonra)", api.max_n <= 18
              and api.yaz[-1] == ("bag",) and max(i for i, y in enumerate(api.yaz) if y[0] == "sira") < len(api.yaz) - 1))
    s.append(("yuklemede overwrite / rank yok (yalniz alt_text)", all(y[2] == ("alt_text",) for y in api.yaz if y[0] == "yukle")
              and len([y for y in api.yaz if y[0] == "yukle"]) == 9))
    # on kosul: canli galeri LISTE'den farkli
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli + [(18, 777)], bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("canli galeri LISTE'den farkli -> DUR, yazma yok", R["sonuc"] == "DUR" and "LISTE ile ayni degil" in R["sorun"][0]
              and api.yaz == []))
    api = Sahte(canli, bag, state="draft"); R = kos(api, tempfile.mkdtemp() and tmp, lp, dosya, mp)
    s.append(("state draft -> DUR, yazma yok", R["sonuc"] == "DUR" and "active" in R["sorun"][0] and api.yaz == []))
    api = Sahte(canli, bag, kota=9); R = kos(api, tmp, lp, dosya, mp)
    s.append(("kota esigi -> DUR, yazma yok", R["sonuc"] == "DUR" and "kota" in R["sorun"][0] and api.yaz == []))
    # 24 Eki madde 2: 3. yuklemede yanit duser ama gorsel Etsy'de olusur -> galeri okunur, yuklenmis sayilir, tekrar YOK
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "yukle"; R1 = kos(api, tmp, lp, dosya, mp)
    s.append(("cift yukleme yok: yanit dusen yukleme galeride bulunur, yeniden gonderilmez, PASS (9 yukleme)",
              R1["sonuc"] == "PASS" and len([y for y in api.yaz if y[0] == "yukle"]) == 9 and set(api.tekrar) == {1}))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "gitmedi"; R1 = kos(api, tmp, lp, dosya, mp)
    s.append(("yukleme kesin 4xx, gorsel olusmadi: galeri okunur, bir kez daha gonderilir, PASS",
              R1["sonuc"] == "PASS" and ("yukle_hata",) in api.yaz and len([y for y in api.yaz if y[0] == "yukle"]) == 9))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "gitmedi500"; R1 = kos(api, tmp, lp, dosya, mp)
    s.append(("yukleme 5xx, galeride yeni gorsel yok: TEKRAR GONDERILMEZ, DUR (belirsiz)", R1["sonuc"] == "DUR"
              and "belirsiz" in R1["sorun"][0] and len([y for y in api.yaz if y[0] == "yukle"]) == 2 and len(api.tekrar) == 3))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "yukle"; api.gec = 5; R1 = kos(api, tmp, lp, dosya, mp)
    s.append(("yanit dusen yukleme galeride 5 okuma gec gorunur: beklenir, tekrar yok, PASS (9 yukleme)", R1["sonuc"] == "PASS"
              and len([y for y in api.yaz if y[0] == "yukle"]) == 9))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "yabanci"; R1 = kos(api, tmp, lp, dosya, mp)
    s.append(("hata + galeride baska alt metinli yeni gorsel: bizim sayilmaz, DUR", R1["sonuc"] == "DUR"
              and "alt metin farkli" in R1["sorun"][0]))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R1 = kos(api, tmp, lp, dosya, mp)
    n = api.calls; yaz = len(api.yaz); R2 = kos(api, tmp, lp, dosya, mp)
    s.append(("devam: tamamlanmis ilanda ikinci kosu yeniden yuklemez / silmez", R1["sonuc"] == "PASS" and R2["sonuc"] == "PASS"
              and len([y for y in api.yaz[yaz:] if y[0] in ("yukle", "sil")]) == 0))
    s += gercekci()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"eski78_gorsel_yukle testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
