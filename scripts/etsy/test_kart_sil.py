#!/usr/bin/env python3
"""kart_sil sahte testi (ag yok): kapilar (state, sira, renk bagi, alt metin kagit ifadesi), kuru silmez, silme + geri okuma
PASS, bozulmada FAIL; coklu liste (Serdar 23 Eki, 22 ilan): ilk DUR / FAIL'de sonraki ilana dokunulmaz, SONRA kaydi."""
import copy
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kart_sil as K  # noqa: E402

KART = "Fine art paper detail, 100 percent cotton, matte finish"


class Ilan:
    def __init__(self, base, n=14, hedef_rank=12, bag=False, state="active", kart_alt=KART):
        self.img = [dict(listing_image_id=base + r, rank=r, alt_text=kart_alt if r == hedef_rank else f"alt {r}",
                         url_fullxfull="u", url_570xN="u") for r in range(1, n + 1)]
        self.hedef = base + hedef_rank
        self.bag = [dict(property_id=200, value_id=1, image_id=base + 1)] + ([dict(property_id=200, value_id=2, image_id=self.hedef)]
                                                                              if bag else [])
        self.state = state


class Sahte:
    def __init__(self, ilanlar, boz=None):
        self.il, self.silinen, self.boz, self.remaining, self.calls, self.kapi = ilanlar, [], boz, 3000, 0, []

    def _lid(self, path):
        p = path.split("/"); return p[p.index("listings") + 1]

    def get(self, path, params=None, ok404=False):
        self.calls += 1; I = self.il[self._lid(path)]
        if path.endswith("/images"):
            return {"results": copy.deepcopy(I.img)}
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(I.bag)}
        return {"state": I.state}

    def delete(self, path):
        I = self.il[self._lid(path)]; gid = int(path.rsplit("/", 1)[1]); self.silinen.append(gid)
        I.img = [x for x in I.img if x["listing_image_id"] != gid]
        for i, x in enumerate(I.img, 1):
            x["rank"] = i
        if self.boz:
            self.boz(I)
        return {}

    def kota_kapisi(self, ne):
        self.kapi.append(ne)


class Depo:
    def __init__(self, *a): pass
    def needs_refresh(self): return False
    def write(self): pass


def kos(api, *arg, liste=None):
    K.Etsy = lambda store: api; K.TokenStore = Depo
    os.environ.update(TOKEN_FILE="x", ETSY_SHOP_ID="7")
    out = pathlib.Path(tempfile.mkdtemp())
    if liste is None:
        I = api.il["4570110121"]
        sys.argv = ["k", "--ilan", "4570110121", "--gorsel", str(I.hedef), "--rank", "12", "--out", str(out)] + list(arg)
    else:
        sys.argv = ["k", "--liste", liste, "--out", str(out)] + list(arg)
    try:
        K.main(); kod = 0
    except SystemExit as e:
        kod = e.code if isinstance(e.code, int) else str(e.code)
    R = out / "SONUC_4570110121.json"
    Z = out / "TOPLU_OZET.json"
    return kod, (json.loads(R.read_text()) if R.exists() else None), out, (json.loads(Z.read_text()) if Z.exists() else None)


def tek(**k):
    return Sahte({"4570110121": Ilan(100, **k)})


def dur_neden(Z):
    return " ".join(Z["ozet"]["dur_fail"][0]["hata"]) if Z and Z["ozet"]["dur_fail"] else ""


def main():
    s = []
    api = tek(); kod, R, out, Z = kos(api, "--kuru")
    s.append(("kuru: silme yok, yedek + plan var", api.silinen == [] and (out / "YEDEK_4570110121.json").exists() and kod == 0
              and Z["ozet"]["plan"] == 1))
    api = tek(); kod, R, _, Z = kos(api)
    s.append(("onaysiz silme yok", api.silinen == [] and "onay" in str(kod)))
    api = tek(); kod, R, out, Z = kos(api, "--onay", K.ONAY)
    S = json.loads((out / "SONRA_4570110121.json").read_text()) if (out / "SONRA_4570110121.json").exists() else {}
    s.append(("silme PASS: sayi -1, sira ve alt metin korundu, SONRA kaydi", kod == 0 and R["sonuc"] == "PASS" and api.silinen == [112]
              and R["sonra"] == 13 and len(S.get("gorseller", [])) == 13 and api.kapi == ["ilan 4570110121"]))
    api = tek(hedef_rank=11); api.il["4570110121"].hedef = 111; kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("beklenen sirada degilse silme yok", api.silinen == [] and kod == 2 and "sira" in dur_neden(Z)))
    api = tek(bag=True); kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("renk baginda ise silme yok", api.silinen == [] and "renk" in dur_neden(Z)))
    api = tek(state="draft"); kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("active degilse silme yok", api.silinen == [] and "state" in dur_neden(Z)))
    api = tek(kart_alt="Close up of the printed gold detail"); kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("alt metinde kagit ifadesi yoksa silme yok", api.silinen == [] and "kagit ifadesi" in dur_neden(Z)))
    api = Sahte({"4570110121": Ilan(100)}, boz=lambda I: I.img[0].update(alt_text="degisti")); kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("geri okumada alt metin degisirse FAIL", R and R["sonuc"] == "FAIL" and kod == 2))
    api = Sahte({"4570110121": Ilan(100)}, boz=lambda I: (I.img[0].update(rank=2), I.img[1].update(rank=1)))
    kod, R, _, Z = kos(api, "--onay", K.ONAY)
    s.append(("geri okumada sira degisirse FAIL", R and R["sonuc"] == "FAIL"))
    # coklu liste
    il = {"4570000001": Ilan(1000), "4570000002": Ilan(2000), "4570000003": Ilan(3000)}
    api = Sahte(il); kod, R, out, Z = kos(api, "--onay", K.ONAY, liste="4570000001:1012:12,4570000002:2012:12,4570000003:3012:12")
    s.append(("coklu: 3 ilan PASS, ilan basina kota kapisi ve SONRA", kod == 0 and Z["ozet"]["pass_"] == 3 and api.silinen == [1012, 2012, 3012]
              and len(api.kapi) == 3 and all((out / f"SONRA_{l}.json").exists() for l in il)))
    il = {"4570000001": Ilan(1000), "4570000002": Ilan(2000, kart_alt="alt 12"), "4570000003": Ilan(3000)}
    api = Sahte(il); kod, R, _, Z = kos(api, "--onay", K.ONAY, liste="4570000001:1012:12,4570000002:2012:12,4570000003:3012:12")
    s.append(("coklu: 2. ilan DUR -> 3. ilana dokunulmaz", kod == 2 and api.silinen == [1012] and Z["ozet"]["islenen"] == 2
              and Z["ilanlar"][1]["sonuc"] == "DUR"))
    il = {"4570000001": Ilan(1000), "4570000002": Ilan(2000)}
    api = Sahte(il); kod, R, _, Z = kos(api, "--kuru", liste="4570000001:1012:12,4570000002:2012:12")
    s.append(("coklu kuru: silme yok, 2 plan", api.silinen == [] and Z["ozet"]["plan"] == 2 and kod == 0))
    api = Sahte(il); kod, R, _, Z = kos(api, "--kuru", liste="4570000001:1012:12,4570000001:1013:13")
    s.append(("coklu: ayni ilan iki kez -> DUR", "iki kez" in str(kod) and api.silinen == []))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"kart_sil testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
