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
BOLUMLER = {"results": [{"shop_section_id": 9, "title": "Zodiac Couple Posters"}, {"shop_section_id": 8, "title": "Zodiac Couple Mugs"}]}


class Sahte:
    def __init__(self, en=EN, state="active", ru_bozuk=False, bolum=9):
        self.L = dict(listing_id=1, state=state, title="T", tags=["a"], price={"amount": 1}, quantity=5, description=en,
                      listing_type="physical", shipping_profile_id=7, shop_section_id=bolum)
        self.ru = dict(language="ru", title="RT", description=RU, tags=["x", "y"])
        self.inv = dict(products=[dict(offerings=[dict(is_enabled=True, quantity=3)])])
        self.remaining, self.calls, self.yaz, self.ru_bozuk = 500, 0, [], ru_bozuk

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/sections"):
            return BOLUMLER
        if path.endswith("/translations/ru"):
            return copy.deepcopy(self.ru)
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        return copy.deepcopy(self.L)

    def patch(self, path, data):
        self.calls += 1; self.yaz.append(("patch", data)); self.L.update(data)

    def put(self, path, data):
        self.calls += 1; self.yaz.append(("put", data))
        if self.ru_bozuk:
            raise SystemExit("HATA: 400 x")
        self.ru.update(dict(description=data["description"]))


def kos(api):
    out = pathlib.Path(tempfile.mkdtemp())
    try:
        ok = m.yaz(api, "1", "1", out)
    except m.Dur as e:
        return f"DUR {e}", None
    return ok, json.loads((out / "SONUC_1.json").read_text())


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
              and [k for k, _ in api.yaz] == ["patch", "put"] and set(api.yaz[0][1]) == {"description"}
              and api.yaz[1][1]["title"] == "RT" and api.yaz[1][1]["tags"] == "x,y"
              and R["sonra"]["beyan"] == 1 and R["sonra"]["eski_beyan"] == 0 and R["sonra"]["ru_beyan"] == 1 and R["sonra"]["ru_marka"] == 0))
    ok2, R2 = kos(api)
    s.append(("yaz: ikinci kosu idempotent (yazma 0)", ok2 is True and len(api.yaz) == 2 and R2["yazildi"] == []))
    r, _ = kos(Sahte(state="draft"))
    s.append(("yaz: draft -> DUR, yazma yok", isinstance(r, str) and "active degil" in r))
    api = Sahte(ru_bozuk=True); ok3, R3 = kos(api)
    s.append(("yaz: RU PUT hatasi -> FAIL (raporlu)", ok3 is False and "RU PUT" in R3["hata"][0]))
    api = Sahte(en=KUPA, bolum=8); ok4, R4 = kos(api)
    s.append(("yaz: kupa ailesi bolumden, PASS", ok4 is True and R4["aile"] == "kupa"))
    s.append(("ru_ceviri: liste ve sozluk bicimi", m.ru_ceviri({"translations": {"ru": {"language": "ru", "title": "a"}}})["title"] == "a"
              and m.ru_ceviri({"translations": [{"language": "ru", "title": "b"}]})["title"] == "b"))
    s.append(("beyan metinlerinde uzun/orta tire yok", not m.TIRE.search(m.BEYAN + m.RU_BEYAN)))
    for ad, ok_ in s:
        print(("PASS " if ok_ else "FAIL ") + ad)
    n = sum(ok_ for _, ok_ in s)
    print(f"beyan_marka_yaz testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
