#!/usr/bin/env python3
"""beyan_marka_yaz sahte testi (ag yok): plan, idempotans, capa yok/iki, state, geri okuma."""
import copy
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beyan_marka_yaz as m  # noqa: E402
import etsy_common  # noqa: E402

EN = ("Personalized Cancer and Libra couple wall art. Our original design joins your two zodiac symbols into one shared symbol. "
      "Valentine&#39;s Day.\n\nCancer: June 21 to July 22.\n\nHOW TO ORDER\n1. Format.")
RU = "Именной постер. Оригинальный дизайн AstroLove объединяет.\n\nО РИСУНКЕ\nрисунке AstroLove. И AstroLoveArt уже."


class Sahte:
    def __init__(self, en=EN, state="active", ru_bozuk=False):
        self.L = dict(listing_id=1, state=state, title="T", tags=["a"], price={"amount": 1}, quantity=5, description=en,
                      listing_type="physical", shipping_profile_id=7, shop_section_id=9)
        self.ru = dict(language="ru", title="RT", description=RU, tags=["x", "y"])
        self.inv = dict(products=[dict(offerings=[dict(is_enabled=True, quantity=3)])])
        self.remaining, self.calls, self.yaz, self.ru_bozuk = 500, 0, [], ru_bozuk

    def get(self, path, params=None, ok404=False):
        self.calls += 1
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


def main():
    m.time.sleep = lambda s: None
    sonuc = []
    yeni, notu = m.en_plan(EN)
    par = yeni.split("\n\n")
    sonuc.append(("en_plan: beyan capa paragrafindan hemen sonra, &#39; cozuldu", par[1] == m.BEYAN and "Valentine's" in par[0]
                  and par[2].startswith("Cancer:")))
    sonuc.append(("en_plan: beyan varsa degisiklik yok", m.en_plan(yeni)[0] is None))
    for ad, en in (("capa yok", "x\n\ny"), ("capa iki", f"{m.CAPA} a\n\n{m.CAPA} b")):
        try:
            m.en_plan(en); sonuc.append((f"en_plan: {ad} -> Dur", False))
        except m.Dur:
            sonuc.append((f"en_plan: {ad} -> Dur", True))
    ry, n = m.ru_plan(RU)
    sonuc.append(("ru_plan: 2 Art'siz -> AstroLoveArt, mevcut AstroLoveArt bozulmaz", n == 2 and ry.count("AstroLoveArt") == 3
                  and "AstroLoveArtArt" not in ry))
    api = Sahte(); ok, R = kos(api)
    sonuc.append(("yaz: PASS, 1 PATCH (yalniz description) + 1 PUT (baslik/etiket aynen)", ok is True and R["sonuc"] == "PASS"
                  and [k for k, _ in api.yaz] == ["patch", "put"] and set(api.yaz[0][1]) == {"description"}
                  and api.yaz[1][1]["title"] == "RT" and api.yaz[1][1]["tags"] == "x,y" and R["sonra"]["ru_marka"] == 0))
    ok2, R2 = kos(api)
    sonuc.append(("yaz: ikinci kosu idempotent (yazma 0)", ok2 is True and len(api.yaz) == 2 and R2["yazildi"] == []))
    r, _ = kos(Sahte(state="draft"))
    sonuc.append(("yaz: draft -> DUR, yazma yok", isinstance(r, str) and "active degil" in r))
    api = Sahte(ru_bozuk=True); ok3, R3 = kos(api)
    sonuc.append(("yaz: RU PUT hatasi -> FAIL (EN yazili, raporlu)", ok3 is False and R3["sonuc"] == "FAIL" and "RU PUT" in R3["hata"][0]))
    sonuc.append(("beyan metninde uzun/orta tire yok", not m.TIRE.search(m.BEYAN)))
    for ad, ok_ in sonuc:
        print(("PASS " if ok_ else "FAIL ") + ad)
    n = sum(ok_ for _, ok_ in sonuc)
    print(f"beyan_marka_yaz testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
