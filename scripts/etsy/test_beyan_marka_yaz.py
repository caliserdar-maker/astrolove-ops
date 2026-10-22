#!/usr/bin/env python3
"""beyan_marka_yaz sahte testi (ag yok): uc aile plani, eski beyan degisimi, RU beyan + marka, idempotans, state, geri okuma."""
import copy
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beyan_marka_yaz as m  # noqa: E402

EN = ("Personalized Cancer and Libra couple wall art. Our original design joins your two zodiac symbols into one shared symbol. "
      "Valentine&#39;s Day.\n\nCancer: June 21 to July 22.\n\nHOW TO ORDER\n1. Format.")
KUPA = ("A personalized mug for Virgo and Virgo couples: your two zodiac symbols join into one original fusion symbol, with your "
        "names.\n\nSTYLES\nOrange Blossom.")
YIL = ("A personalized 1 year anniversary gift.\n\nEvery AstroLoveArt design merges two zodiac signs into one shared symbol. "
       "This listing is for the Taurus and Virgo symbol.\n\nHOW TO ORDER\n1. Choose.")
RU = "Именной постер. Оригинальный дизайн AstroLove объединяет.\n\nО РИСУНКЕ\nрисунке AstroLove. И AstroLoveArt уже."
BOLUMLER = {"results": [{"shop_section_id": 9, "title": "Zodiac Couple Posters"}, {"shop_section_id": 8, "title": "Zodiac Couple Mugs"},
                         {"shop_section_id": 7, "title": "1st Anniversary Gifts"}]}


PARTNER = [{"production_partner_id": 5817638, "partner_name": "Printing and Fulfillment Partner", "location": "United States"}]


class Sahte:
    """Cok ilanli sahte Etsy. bozan(api, lid) PATCH sonrasi cagrilir (kapi 1b testleri)."""
    def __init__(self, en=EN, state="active", ru_bozuk=False, bolum=9, ilanlar=None, bozan=None):
        self.ilan, self.ru, self.soru = {}, {}, {}
        for lid, (en_, bol_, ru_) in (ilanlar or {"1": (en, bolum, RU)}).items():
            self.ilan[lid] = dict(listing_id=int(lid), state=state, title="T", tags=["a"], price={"amount": 1}, quantity=5,
                                  description=en_, listing_type="physical", shipping_profile_id=7, return_policy_id=3,
                                  shop_section_id=bol_, production_partners=copy.deepcopy(PARTNER), is_personalizable=True,
                                  personalization_is_required=True, personalization_char_count_max=256,
                                  personalization_instructions="Names")
            self.ru[lid] = dict(language="ru", title="RT", description=ru_, tags=["x", "y"]) if ru_ is not None else \
                dict(language="ru", title="", description="", tags=[])   # yil donumu: tekil GET bos kayit (23 Eki 4595350971)
            self.soru[lid] = {"personalization_questions": [{"question_id": 1, "instructions": "Names", "max_allowed_characters": 256}]}
        self.inv = dict(products=[dict(offerings=[dict(is_enabled=True, quantity=3)])])
        self.remaining, self.calls, self.yaz, self.ru_bozuk, self.bozan = 500, 0, [], ru_bozuk, bozan
        self.batch_ru, self.get_hata = True, False

    @staticmethod
    def lid(path):
        p = path.split("/")
        return p[p.index("listings") + 1]

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/sections"):
            return BOLUMLER
        if path == "/listings/batch":
            res = []
            for i in params["listing_ids"].split(","):
                L = copy.deepcopy(self.ilan[i])
                r = self.ru[i]
                L["translations"] = {"ru": copy.deepcopy(r)} if r["description"] and self.batch_ru else {}
                res.append(L)
            return {"results": res}
        lid = self.lid(path)
        if self.get_hata:
            raise SystemExit("HATA: 503 x")
        if path.endswith("/translations/ru"):
            return copy.deepcopy(self.ru[lid])
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        if path.endswith("/personalization"):
            return copy.deepcopy(self.soru[lid])
        return copy.deepcopy(self.ilan[lid])

    def patch(self, path, data):
        self.calls += 1; lid = self.lid(path); self.yaz.append(("patch", lid, data)); self.ilan[lid].update(data)
        if self.bozan:
            self.bozan(self, lid)

    def put(self, path, data):
        self.calls += 1; lid = self.lid(path); self.yaz.append(("put", lid, data))
        if self.ru_bozuk:
            raise SystemExit("HATA: 400 x")
        self.ru[lid].update(dict(description=data["description"]))


def kos(api, lid="1"):
    out = pathlib.Path(tempfile.mkdtemp())
    try:
        R = m.yaz(api, "1", lid, out)
    except m.Dur as e:
        return f"DUR {e}", None
    return R["sonuc"] != "FAIL", json.loads((out / f"SONUC_{lid}.json").read_text())


def toplu(api, aile, ids, limit=10):
    out = pathlib.Path(tempfile.mkdtemp())
    a = type("A", (), dict(aile=aile, ilan=ids, limit=limit))()
    try:
        ok = m.toplu(api, "1", a, out)
    except m.Dur as e:
        ok = f"DUR {e}"
    oz = out / "TOPLU_OZET.json"
    return ok, (json.loads(oz.read_text()) if oz.exists() else None)


def dur_mu(f, *a):
    try:
        f(*a); return False
    except m.Dur:
        return True


def main():
    m.time.sleep = lambda s: None
    s = []
    par = m.en_plan(EN, "poster")[0].split("\n\n")
    s.append(("poster: beyan 1. paragraftan sonra, &#39; cozuldu", par[1] == m.BEYAN and "Valentine's" in par[0] and par[2].startswith("Cancer:")))
    pilot = EN.replace("Day.\n\n", "Day.\n\n" + m.ESKI_BEYAN + "\n\n")
    y, notu = m.en_plan(pilot, "poster")
    s.append(("poster pilot: eski beyan kaldirilir, yenisi ayni yere", m.ESKI_BEYAN not in y and y.split("\n\n")[1] == m.BEYAN
              and "kaldirildi" in notu and y.count(m.BEYAN) == 1))
    s.append(("poster: beyan varsa degisiklik yok", m.en_plan(m.en_plan(pilot, "poster")[0], "poster")[0] is None))
    s.append(("kupa: 1. paragraftan sonra", m.en_plan(KUPA, "kupa")[0].split("\n\n")[1] == m.BEYAN))
    s.append(("yil: capa paragrafindan sonra", m.en_plan(YIL, "yil")[0].split("\n\n")[2] == m.BEYAN))
    s.append(("capa yok / aile bilinmiyor -> Dur", dur_mu(m.en_plan, "x\n\ny", "poster") and dur_mu(m.en_plan, EN, "?")
              and dur_mu(m.en_plan, KUPA, "poster")))
    ry, n, rn = m.ru_plan(RU, "poster")
    s.append(("RU: marka 2 -> AstroLoveArt, beyan 1. paragraftan sonra", n == 2 and ry.split("\n\n")[1] == m.RU_BEYAN
              and "AstroLoveArtArt" not in ry and ry.count("AstroLoveArt") == 4))
    s.append(("RU: ikinci kez degisiklik yok; yil donumunde RU beyan yok", m.ru_plan(ry, "poster")[0] is None
              and m.ru_plan("a\n\nb", "yil")[0] is None))
    api = Sahte(en=pilot); ok, R = kos(api)
    s.append(("yaz: PASS, PATCH yalniz description + PUT baslik/etiket aynen", ok is True and R["sonuc"] == "PASS"
              and [k for k, _, _ in api.yaz] == ["patch", "put"] and set(api.yaz[0][2]) == {"description"}
              and api.yaz[1][2]["title"] == "RT" and api.yaz[1][2]["tags"] == "x,y"
              and R["sonra"]["beyan"] == 1 and R["sonra"]["eski_beyan"] == 0 and R["sonra"]["ru_beyan"] == 1 and R["sonra"]["ru_marka"] == 0))
    ok2, R2 = kos(api)
    s.append(("yaz: ikinci kosu ATLA (1c), yazma 0", ok2 is True and len(api.yaz) == 2 and R2["yazildi"] == [] and R2["sonuc"] == "ATLA"))
    r, _ = kos(Sahte(state="draft"))
    s.append(("yaz: draft -> DUR, yazma yok", isinstance(r, str) and "active degil" in r))
    api = Sahte(ru_bozuk=True); ok3, R3 = kos(api)
    s.append(("yaz: RU PUT hatasi -> FAIL (raporlu)", ok3 is False and "RU PUT" in R3["hata"][0]))
    api = Sahte(en=KUPA, bolum=8); ok4, R4 = kos(api)
    s.append(("yaz: kupa ailesi bolumden, PASS", ok4 is True and R4["aile"] == "kupa"))
    s.append(("ru_ceviri: liste ve sozluk bicimi", m.ru_ceviri({"translations": {"ru": {"language": "ru", "title": "a"}}})["title"] == "a"
              and m.ru_ceviri({"translations": [{"language": "ru", "title": "b"}]})["title"] == "b"))
    s.append(("beyan metinlerinde uzun/orta tire yok", not m.TIRE.search(m.BEYAN + m.RU_BEYAN)))
    # 1a: yil donumunde bos RU kaydi -> "yok", PUT yok
    api = Sahte(ilanlar={"1": (YIL, 7, None)}); ok5, R5 = kos(api)
    s.append(("1a: yil donumu bos RU kaydi -> ru_ceviri yok, yalniz PATCH, PASS", ok5 is True and R5["ru_ceviri"] == "yok"
              and [k for k, _, _ in api.yaz] == ["patch"] and R5["sonuc"] == "PASS"))
    s.append(("1a: ru_gercek bos/eksik kayit -> {}", m.ru_gercek({"language": "ru", "title": "", "description": None}) == {}
              and m.ru_gercek(None) == {} and m.ru_gercek({"title": "x"})["title"] == "x"))
    # 1b: her korunan alan icin PATCH sonrasi bozulma -> FAIL
    bozanlar = {
        "kisisellestirme acik": lambda A, l: A.ilan[l].update(is_personalizable=False),
        "kisisellestirme zorunlu": lambda A, l: A.ilan[l].update(personalization_is_required=False),
        "karakter siniri": lambda A, l: A.ilan[l].update(personalization_char_count_max=100),
        "talimat": lambda A, l: A.ilan[l].update(personalization_instructions="X"),
        "kisisellestirme sorulari": lambda A, l: A.soru[l].update(personalization_questions=[]),
        "kargo profili": lambda A, l: A.ilan[l].update(shipping_profile_id=8),
        "iade politikasi": lambda A, l: A.ilan[l].update(return_policy_id=4),
        "uretim ortagi": lambda A, l: A.ilan[l].update(production_partners=[]),
        "ilan durumu": lambda A, l: A.ilan[l].update(state="inactive"),
        "satilabilir teklif": lambda A, l: A.inv["products"][0]["offerings"][0].update(is_enabled=False),
        "RU baslik": lambda A, l: A.ru[l].update(title="YENI"),
        "RU etiket": lambda A, l: A.ru[l].update(tags=["z"]),
        "RU aciklama": lambda A, l: A.ru[l].update(description="baska"),
    }
    for ad, f in bozanlar.items():
        def bz(A, l, f=f, ad=ad):
            if ad.startswith("RU"):   # RU bozulmasi PUT'tan sonra olmali: PUT'u sar
                eski = A.put
                def put2(path, data):
                    eski(path, data); f(A, l)
                A.put = put2
            else:
                f(A, l)
        okb, Rb = kos(Sahte(bozan=bz))
        s.append((f"1b: {ad} degisirse FAIL", okb is False and Rb["sonuc"] == "FAIL" and bool(Rb["hata"])))
    api = Sahte(); del api.ilan["1"]["production_partners"]; r, _ = kos(api)
    s.append(("1b: production_partners alani yoksa DUR, yazma yok", isinstance(r, str) and "production_partners" in r and api.yaz == []))
    # 1c + toplu: tamamlanmis ilan aday disi, ilk FAIL'de DUR, limit
    dolu = m.en_plan(KUPA, "kupa")[0]
    api = Sahte(ilanlar={"1": (dolu, 8, m.ru_plan(RU, "kupa")[0]), "2": (KUPA, 8, RU), "3": (KUPA, 8, RU), "4": (KUPA, 8, RU)})
    okt, Z = toplu(api, "kupa", ["1", "2", "3", "4"], limit=2)
    s.append(("toplu: beyani tam ilan aday disi (1c), limit 2 uygulanir", okt is True and Z["ozet"]["aday"] == 3
              and Z["ozet"]["islenen"] == 2 and Z["ozet"]["pass_"] == 2 and {l for _, l, _ in api.yaz} == {"2", "3"}))
    okt2, Z2 = toplu(api, "kupa", ["1", "2", "3", "4"], limit=10)
    s.append(("toplu: yeniden baslatma yalniz kalan ilan (4)", okt2 is True and Z2["ozet"]["aday"] == 1
              and {l for _, l, _ in api.yaz[-2:]} == {"4"}))
    sayac = {"n": 0}
    def ikinci_boz(A, l):
        sayac["n"] += 1
        if sayac["n"] == 2:
            A.ilan[l].update(shipping_profile_id=99)
    api = Sahte(ilanlar={"5": (KUPA, 8, RU), "6": (KUPA, 8, RU), "7": (KUPA, 8, RU)}, bozan=ikinci_boz)
    okt3, Z3 = toplu(api, "kupa", ["5", "6", "7"], limit=10)
    s.append(("toplu: 2. ilanda kapi FAIL -> DUR, 3. ilana yazma yok", okt3 is False and Z3["ozet"]["islenen"] == 2
              and len(Z3["ozet"]["fail"]) == 1 and "7" not in {l for _, l, _ in api.yaz}))
    api = Sahte(ilanlar={"8": (KUPA, 8, RU), "9": (KUPA, 8, RU)}); api.ilan["9"]["state"] = "draft"
    okt4, Z4 = toplu(api, "kupa", ["8", "9"], limit=10)
    s.append(("toplu: draft ilan -> DUR, ozet yazilir, draft'a yazma yok", isinstance(okt4, str) and "active degil" in okt4
              and Z4["ozet"]["fail"][0]["sonuc"] == "DUR" and "9" not in {l for _, l, _ in api.yaz}))
    api = Sahte(ilanlar={"10": (KUPA, 8, RU), "11": (EN, 9, RU)})
    okt5, Z5 = toplu(api, "poster", ["10", "11"], limit=10)
    s.append(("toplu: yalniz secilen aile", okt5 is True and {l for _, l, _ in api.yaz} == {"11"}))
    api = Sahte(ilanlar={"12": (KUPA, 8, RU), "13": (KUPA, 8, RU)}); api.remaining = m.KOTA_TABAN - 1
    okt6, Z6 = toplu(api, "kupa", ["12", "13"], limit=10)
    s.append(("toplu: kota < taban 10 -> DUR, yazma yok", isinstance(okt6, str) and "kota" in okt6 and api.yaz == []))
    # kota esigi (Serdar 23 Eki 2b): toplu ilana baslamadan api.kota_kapisi cagirir
    api = Sahte(ilanlar={"30": (KUPA, 8, RU), "31": (KUPA, 8, RU)}); cagri = []
    def kapi(ne, A=api):
        cagri.append(ne)
        if len(cagri) == 2:
            raise SystemExit("DUR: kota esigi: kalan 470 < 481 (ilan 31 baslamadi)")
    api.kota_kapisi = kapi
    okK, ZK = toplu(api, "kupa", ["30", "31"], limit=10)
    s.append(("kota: toplu her ilandan once kota_kapisi; esik altinda ilan 31 yazilmaz, DUR", isinstance(okK, str)
              and cagri == ["ilan 30", "ilan 31"] and {l for _, l, _ in api.yaz} == {"30"} and ZK["ozet"]["fail"][0]["sonuc"] == "DUR"))
    # inceleme 23 Eki bulgulari
    dolu_en = m.en_plan(KUPA, "kupa")[0]
    api = Sahte(ilanlar={"20": (dolu_en, 8, RU)}); api.batch_ru = False
    okA1, ZA1 = toplu(api, "kupa", ["20"], limit=10)
    s.append(("A1: EN yazilmis, RU yarim; batch RU gostermese de aday (tekil GET), RU yazilir", okA1 is True and ZA1["ozet"]["aday"] == 1
              and [k for k, _, _ in api.yaz] == ["put"] and m.RU_BEYAN in api.ru["20"]["description"]))
    api = Sahte(); api.soru["1"] = {}; r, _ = kos(api)
    s.append(("A3: kisisellestirme acik, sorular okunamadi -> DUR, yazma yok", isinstance(r, str) and "sorular" in r and api.yaz == []))
    api = Sahte(); del api.ilan["1"]["personalization_char_count_max"]; r, _ = kos(api)
    s.append(("A3: kisisellestirme alani yanitta yok -> DUR", isinstance(r, str) and "kisisellestirme alanlari" in r and api.yaz == []))
    def gh(A, l):
        A.get_hata = True
    api = Sahte(ilanlar={"21": (KUPA, 8, RU), "22": (KUPA, 8, RU)}, bozan=gh)
    okA5, ZA5 = toplu(api, "kupa", ["21", "22"], limit=10)
    s.append(("A5: yazim sonrasi okuma hatasi -> FAIL kaydi, kosu durur", okA5 is False and ZA5["ozet"]["fail"][0]["ilan"] == "21"
              and "istisna" in ZA5["ozet"]["fail"][0]["hata"][0] and "22" not in {l for _, l, _ in api.yaz}))
    def fiyat(A, l):
        A.inv["products"][0]["offerings"][0]["price"] = {"amount": 999}
    okA7, RA7 = kos(Sahte(bozan=fiyat))
    s.append(("A7: teklif sayisi ayni, fiyat degisti -> FAIL", okA7 is False and "teklif icerigi" in " ".join(RA7["hata"])))
    api = Sahte(ilanlar={"1": (EN, 9, "")}); api.ru["1"]["title"] = "RT"; r, _ = kos(api)
    s.append(("A8: RU baslik var, RU aciklama bos -> DUR", isinstance(r, str) and "RU aciklama bos" in r and api.yaz == []))
    api = Sahte(); api.remaining = None; r, _ = kos(api)
    s.append(("A6: kota basligi okunamadi -> DUR, yazma yok", isinstance(r, str) and "kota" in r and api.yaz == []))
    for ad, ok_ in s:
        print(("PASS " if ok_ else "FAIL ") + ad)
    n = sum(ok_ for _, ok_ in s)
    print(f"beyan_marka_yaz testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
