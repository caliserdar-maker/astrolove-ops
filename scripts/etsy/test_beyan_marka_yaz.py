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


BOLUM_AILE_TEST = {9: "poster", 8: "kupa", 7: "yil"}


def kuru_ozet(api, lid):
    """Kuru planin (kupa / yil) urettigi onay ozeti: ayni plan fonksiyonlari, sahte ilanin o anki metni (2a, Serdar 23 Eki A1)."""
    L, r = api.ilan[lid], api.ru[lid]
    aile = BOLUM_AILE_TEST.get(L.get("shop_section_id"))
    if aile not in m.OZET_AILE:
        return None
    try:
        en1 = m.en_plan(L.get("description"), aile)[0]
        ru1 = m.ru_plan(r.get("description"), aile)[0] if r.get("description") else None
    except m.Dur:
        return None
    return m.aile_ozet(en1, ru1)


def kos(api, lid="1", onay_ozet="kuru"):
    out = pathlib.Path(tempfile.mkdtemp())
    if onay_ozet == "kuru":
        onay_ozet = kuru_ozet(api, lid)
    try:
        R = m.yaz(api, "1", lid, out, onay_ozet=onay_ozet)
    except m.Dur as e:
        return f"DUR {e}", None
    return R["sonuc"] != "FAIL", json.loads((out / f"SONUC_{lid}.json").read_text())


def toplu(api, aile, ids, limit=10, ru_yeniden=False, onay_ozetler=None):
    out = pathlib.Path(tempfile.mkdtemp())
    if onay_ozetler is None and aile in m.OZET_AILE:   # kuru plan taklidi: listedeki her ilanin ozeti
        onay_ozetler = {l: o for l in ids for o in [kuru_ozet(api, l)] if o}
    a = type("A", (), dict(aile=aile, ilan=ids, limit=limit, ru_yeniden=ru_yeniden, onay_ozetler=onay_ozetler or {}))()
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


def poster_yeni_yol():
    """Serdar 23 Eki madde 1-2: poster tek ilan yeni yol (beyan + Latin notu + ru_poster RU), RU kapisi izni, geri okuma olcumu."""
    import test_ru_poster as TP
    import ru_poster as P
    import etsy_common as E
    boy = ["8 x 10", "11 x 14", "12 x 16", "12 x 18", "16 x 20", "16 x 24", "18 x 24", "20 x 30", "24 x 30", "24 x 36", "A4", "A3", "A2"]
    inv = dict(products=[dict(sku=f"S{i}{j}{f}", offerings=[dict(is_enabled=True, quantity=3, price={"amount": 1})],
                              property_values=[dict(property_name="Size", values=[b]), dict(property_name="Primary color", values=[c]),
                                               dict(property_name="Format", values=[f])])
                         for i, b in enumerate(boy) for j, c in enumerate("abcde") for f in ("Digital File", "Print")])
    canli = TP.EN_CANLI.replace("\n\n" + P.BEYAN, "")   # beyansiz canli EN
    eski_ru = "Именной постер. Печатаем на хлопковой бумаге Hahnemühle Photo Rag 308 г/м². AstroLove."
    s = []

    def yeni(en=canli):
        api = Sahte(ilanlar={"4570110121": (en, 9, eski_ru)}); api.inv = copy.deepcopy(inv); return api
    ozet_ok = P.onay_ozet(P.poster_en(canli), P.kur(P.poster_en(canli), __import__("ru_olcum").envanter_ozet(inv))[0])
    api = yeni()
    try:
        m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True, onay_ozet="0" * 64); r = None
    except m.Dur as e:
        r = str(e)
    s.append(("2a: onayli ozet tutmazsa DUR, yazma yok", r is not None and "onayli kuru planla ayni degil" in r and api.yaz == []))
    try:
        m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True); r = None
    except m.Dur as e:
        r = str(e)
    s.append(("2a: onay ozeti verilmezse DUR, yazma yok", r is not None and api.yaz == []))
    api = yeni(); out = pathlib.Path(tempfile.mkdtemp())
    R = m.yaz(api, "1", "4570110121", out, ru_yeniden=True, onay_ozet=ozet_ok)
    en_y = [d for k, _, d in api.yaz if k == "patch"]; ru_y = [d for k, _, d in api.yaz if k == "put"]
    beklenen_ru = P.kur(P.poster_en(canli), __import__("ru_olcum").envanter_ozet(inv))[0]
    s.append(("poster yeni yol: PASS, 1 PATCH + 1 PUT", R["sonuc"] == "PASS" and len(en_y) == 1 and len(ru_y) == 1))
    s.append(("poster yeni yol: EN = beyan + Latin notu", P.BEYAN in en_y[0]["description"] and P.LATIN_EN in en_y[0]["description"]))
    s.append(("poster yeni yol: RU = ru_poster metni, eski RU yok, baslik/etiket ayni", ru_y[0]["description"] == beklenen_ru
              and "Hahnem" not in ru_y[0]["description"] and ru_y[0]["title"] == "RT" and ru_y[0]["tags"] == "x,y"))
    s.append(("poster yeni yol: RU kapisi izni yalniz bu metin", E.RU_POSTER_IZIN.get("4570110121") == E.ozet(beklenen_ru)))
    s.append(("poster yeni yol: YENI_EN/YENI_RU/KONTROL dosyalari", all((out / f"{x}_4570110121.{e}").exists()
              for x, e in (("YENI_EN", "txt"), ("YENI_RU", "txt"), ("KONTROL", "json")))))
    R2 = m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True, onay_ozet=ozet_ok)
    s.append(("poster yeni yol: ikinci kosu ATLA", R2["sonuc"] == "ATLA" and len(api.yaz) == 2))
    api = yeni(); api.inv["products"] = api.inv["products"][:-10]   # 12 boy: EN '13 sizes' ile celisir
    try:
        m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True); r = None
    except m.Dur as e:
        r = str(e)
    s.append(("poster yeni yol: kontrol FAIL -> DUR, yazma yok", r is not None and "kontrolu FAIL" in r and api.yaz == []))
    api = yeni(en=canli.replace("No emoji. ", "No emoji, please. "))
    try:
        m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True); r = None
    except m.Dur as e:
        r = str(e)
    s.append(("poster yeni yol: Latin notu capasi yok -> DUR, yazma yok", r is not None and "capasi" in r and api.yaz == []))
    api = yeni(); bozuk = {"n": 0}
    _put = api.put

    def put_boz(path, data, A=api):
        _put(path, data); A.ru["4570110121"]["description"] += "\n\nHahnemühle"
    api.put = put_boz
    R3 = m.yaz(api, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True, onay_ozet=ozet_ok)
    s.append(("poster yeni yol: geri okunan RU bozuksa FAIL", R3["sonuc"] == "FAIL"))
    api = yeni(); ok, Z = toplu(api, "poster", ["4570110121"], limit=1)
    s.append(("toplu poster ru_yeniden olmadan -> DUR, yazma yok", isinstance(ok, str) and "ru-yeniden" in ok and api.yaz == []))
    # Serdar 23 Eki parti: iki poster, ilan basina ozet
    en2 = canli.replace("Aries and Leo", "Aries and Leo")
    def iki():
        A = Sahte(ilanlar={"4570110121": (canli, 9, eski_ru), "4570110641": (canli, 9, eski_ru)}); A.inv = copy.deepcopy(inv); return A
    api = iki(); ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                               onay_ozetler={"4570110121": ozet_ok})
    s.append(("parti: bir ilanin ozeti yoksa hic yazma yok", isinstance(ok, str) and "onay ozeti" in ok and api.yaz == []))
    api = iki(); ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                               onay_ozetler={"4570110121": ozet_ok, "4570110641": "0" * 64})
    s.append(("parti: 2. ilanin ozeti tutmazsa 1. yazilir, 2. DUR (yazma yok)", isinstance(ok, str)
              and {l for _, l, _ in api.yaz} == {"4570110121"} and Z["ozet"]["fail"][0]["ilan"] == "4570110641"))
    api = iki(); ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                               onay_ozetler={"4570110121": ozet_ok, "4570110641": ozet_ok})
    s.append(("parti: iki ilan PASS, ilan basina PATCH + PUT", ok is True and Z["ozet"]["pass_"] == 2 and len(api.yaz) == 4))
    s.append(("parti: kayitta ilan basina ozet eslesmesi (74 ilan partisi)", Z["ozet"]["ozet_eslesen"] == 2
              and all(x["ozet_eslesme"] is True and x["yarim"] is False for x in Z["ilanlar"]) and Z["ozet"]["yarim"] == []))
    api = iki(); api.ru_bozuk = True
    ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                  onay_ozetler={"4570110121": ozet_ok, "4570110641": ozet_ok})
    s.append(("parti: RU PUT hatasi -> YARIM kaydi, kosu durur, 2. ilana yazma yok", ok is False and Z["ozet"]["yarim"] == ["4570110121"]
              and Z["ilanlar"][0]["yarim"] is True and {l for _, l, _ in api.yaz} == {"4570110121"} and Z["ozet"]["islenen"] == 1))
    api = iki()
    def put_ag(path, data, A=api):
        A.yaz.append(("put", A.lid(path), data)); raise ConnectionError("ag koptu")   # SystemExit disi hata
    api.put = put_ag
    ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                  onay_ozetler={"4570110121": ozet_ok, "4570110641": ozet_ok})
    s.append(("parti: RU PUT ag hatasi -> YARIM, kosu durur, 2. ilana yazma yok", ok is False and Z["ozet"]["yarim"] == ["4570110121"]
              and {l for _, l, _ in api.yaz} == {"4570110121"}))
    api = iki(); api.bozan = lambda A, lid: setattr(A, "get_hata", True)   # PATCH sonrasi her GET coker (RU PUT yine gider)
    ok, Z = toplu(api, "poster", ["4570110121", "4570110641"], limit=3, ru_yeniden=True,
                  onay_ozetler={"4570110121": ozet_ok, "4570110641": ozet_ok})
    s.append(("parti: yazim sonrasi geri okuma coker -> FAIL, kosu durur, 2. ilana yazma yok", ok is False
              and Z["ilanlar"][0]["sonuc"] == "FAIL" and {l for _, l, _ in api.yaz} == {"4570110121"}))
    api = iki(); ok, Z = toplu(api, "poster", ["4570110121"], limit=1, ru_yeniden=True, onay_ozetler={"4570110121": ozet_ok})
    s.append(("parti: limit uygulanir", Z["ozet"]["islenen"] == 1))
    A = yeni(); A.ru["4570110121"]["title"] = "постер Hahnemühle"
    try:
        m.yaz(A, "1", "4570110121", pathlib.Path(tempfile.mkdtemp()), ru_yeniden=True, onay_ozet=ozet_ok); r = None
    except (m.Dur, SystemExit) as e:
        r = str(e)
    s.append(("RU basliginda yasak ifade -> EN PATCH'ten once DUR (yarim yazim yok)", r is not None and A.yaz == []))
    return s


def main():
    m.time.sleep = lambda s: None
    s = []
    # inceleme 23 Eki E1: varsayilan poster yazimi kapali; kapi testleri (poster fixture) icin acilir, sonda geri kapatilir
    api = Sahte(); r, _ = kos(api)
    s.append(("E1: poster eski yol kapali (varsayilan) -> DUR, yazma yok", m.POSTER_YAZIM_KAPALI is True and isinstance(r, str)
              and "yalniz --ru-yeniden" in r and api.yaz == []))
    s += poster_yeni_yol()
    m.POSTER_YAZIM_KAPALI = False
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
    okt5, Z5 = toplu(api, "kupa", ["10", "11"], limit=10)
    s.append(("toplu kupa: listedeki ilanin ozeti yoksa (aile disi) hic yazma yok", isinstance(okt5, str) and "onay ozeti" in okt5
              and api.yaz == []))
    api = Sahte(ilanlar={"10": (KUPA, 8, RU), "11": (EN, 9, RU)})
    okt5, Z5 = toplu(api, "kupa", ["10", "11"], limit=10, onay_ozetler={"10": kuru_ozet(api, "10"), "11": "0" * 64})
    s.append(("toplu: yalniz secilen aile", okt5 is True and {l for _, l, _ in api.yaz} == {"10"}))
    # Serdar 23 Eki A1: kupa / yil 2a ozet kapisi
    api = Sahte(en=KUPA, bolum=8); r, _ = kos(api, onay_ozet=None)
    s.append(("kupa: onay ozeti yoksa DUR, yazma yok", isinstance(r, str) and "onayli kuru planla" in r and api.yaz == []))
    api = Sahte(en=KUPA, bolum=8); r, _ = kos(api, onay_ozet="0" * 64)
    s.append(("kupa: ozet tutmazsa DUR, yazma yok", isinstance(r, str) and "onayli kuru planla" in r and api.yaz == []))
    api = Sahte(ilanlar={"1": (YIL, 7, None)}); r, _ = kos(api, onay_ozet="0" * 64)
    s.append(("yil: ozet tutmazsa DUR, yazma yok", isinstance(r, str) and "onayli kuru planla" in r and api.yaz == []))
    api = Sahte(en=KUPA, bolum=8); oz0 = kuru_ozet(api, "1"); api.ilan["1"]["description"] += "\n\nYeni paragraf."
    r, _ = kos(api, onay_ozet=oz0)
    s.append(("kupa: kurudan sonra canli EN degisti -> ozet tutmaz, DUR", isinstance(r, str) and "onayli kuru planla" in r and api.yaz == []))
    api = Sahte(ilanlar={"50": (KUPA, 8, RU), "51": (KUPA, 8, RU)})
    okz, Zz = toplu(api, "kupa", ["50", "51"], limit=10)
    s.append(("toplu kupa: kayitta ilan basina ozet eslesmesi", okz is True and Zz["ozet"]["ozet_eslesen"] == 2
              and all(x["ozet_eslesme"] is True for x in Zz["ilanlar"])))
    api = Sahte(ilanlar={"52": (YIL, 7, None), "53": (YIL, 7, None)})
    oky, Zy = toplu(api, "yil", ["52", "53"], limit=10)
    s.append(("toplu yil: yalniz EN PATCH, ozet eslesmesi 2", oky is True and Zy["ozet"]["ozet_eslesen"] == 2
              and [k for k, _, _ in api.yaz] == ["patch", "patch"]))
    api = Sahte(ilanlar={"54": (KUPA, 8, RU), "55": (KUPA, 8, RU)})
    _patch = api.patch
    def patch_dus(path, data, A=api):
        _patch(path, data); raise ConnectionError("yanit dustu")   # PATCH uygulandi, yanit gelmedi
    api.patch = patch_dus
    oka5, Za5 = toplu(api, "kupa", ["54", "55"], limit=10)
    s.append(("A5: PATCH uygulandi yanit dustu -> canli EN okunur, YARIM, 2. ilana yazma yok", oka5 is False
              and Za5["ozet"]["yarim"] == ["54"] and {l for _, l, _ in api.yaz} == {"54"}))
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
    # SIRA 5 (Serdar 23 Eki): GERCEK etsy_common.Etsy.kota_kapisi ile parti; esik 481 (onayli config), kalan 1. ilandan sonra 470
    import types
    import etsy_common as E
    api = Sahte(ilanlar={"40": (KUPA, 8, RU), "41": (KUPA, 8, RU), "42": (KUPA, 8, RU)}); api.esik = 481
    api.kota_kapisi = types.MethodType(E.Etsy.kota_kapisi, api)
    _put = api.put
    def put_dus(path, data, A=api):
        r = _put(path, data); A.remaining = 470; return r
    api.put = put_dus
    okG, ZG = toplu(api, "kupa", ["40", "41", "42"], limit=10)
    s.append(("kota (gercek kota_kapisi): parti 1. ilan sonrasi kalan 470 < 481 -> 2. ilan baslamaz, DUR, 41/42 yazilmaz",
              isinstance(okG, str) and "kalan 470 < 481 (ilan 41 baslamadi)" in okG
              and {l for _, l, _ in api.yaz} == {"40"} and ZG["ozet"]["islenen"] == 2))
    # inceleme 23 Eki bulgulari
    dolu_en = m.en_plan(KUPA, "kupa")[0]
    api = Sahte(ilanlar={"20": (dolu_en, 8, RU)}); api.batch_ru = False
    okA1, ZA1 = toplu(api, "kupa", ["20"], limit=10)
    s.append(("A1: EN yazilmis, RU yarim; batch RU gostermese de aday (tekil GET), RU yazilir", okA1 is True and ZA1["ozet"]["aday"] == 1
              and [k for k, _, _ in api.yaz] == ["put"] and m.RU_BEYAN in api.ru["20"]["description"]))
    api = Sahte(); api.soru["1"] = {}; r, _ = kos(api)
    s.append(("A3: kisisellestirme acik, sorular okunamadi -> DUR, yazma yok", isinstance(r, str) and "sorular" in r and api.yaz == []))
    api = Sahte(); del api.ilan["1"]["is_personalizable"]; r, _ = kos(api)
    s.append(("A3: is_personalizable yanitta yok -> DUR", isinstance(r, str) and "kisisellestirme alanlari" in r and api.yaz == []))
    # 23 Eki (4570031205): coklu soru modeli, eski skaler alanlar yanitta yok; sorular var -> yazar, kapi sorulari kiyaslar
    api = Sahte()
    for k in ("personalization_is_required", "personalization_char_count_max", "personalization_instructions"):
        del api.ilan["1"][k]
    ok, R = kos(api)
    s.append(("yeni model: eski alanlar yok, sorular var -> PASS", ok is True and R["sonuc"] == "PASS"))
    api = Sahte()
    for k in ("personalization_is_required", "personalization_char_count_max", "personalization_instructions"):
        del api.ilan["1"][k]
    _p = api.patch
    def patch_soru(path, data, A=api):
        r = _p(path, data); A.soru["1"]["personalization_questions"] = [{"question_id": 1, "instructions": "X", "max_allowed_characters": 9}]
        return r
    api.patch = patch_soru
    ok, R = kos(api)
    s.append(("yeni model: yazim sonrasi soru degisirse -> FAIL", ok is False and "kisisellestirme sorulari degisti" in R["hata"]))
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
