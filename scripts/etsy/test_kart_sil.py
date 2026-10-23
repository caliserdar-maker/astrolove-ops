#!/usr/bin/env python3
"""kart_sil sahte testi (ag yok): kapilar (state, sira, renk bagi), kuru silmez, silme + geri okuma PASS, bozulmada FAIL."""
import copy
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kart_sil as K  # noqa: E402


class Sahte:
    def __init__(self, n=14, hedef_rank=12, bag=False, state="active", boz=None):
        self.img = [dict(listing_image_id=100 + r, rank=r, alt_text=f"alt {r}", url_fullxfull="u", url_570xN="u") for r in range(1, n + 1)]
        self.hedef = 100 + hedef_rank
        self.bag = [dict(property_id=200, value_id=1, image_id=101)] + ([dict(property_id=200, value_id=2, image_id=self.hedef)] if bag else [])
        self.state, self.silinen, self.boz, self.remaining, self.calls = state, [], boz, 3000, 0

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/images"):
            return {"results": copy.deepcopy(self.img)}
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(self.bag)}
        return {"state": self.state}

    def delete(self, path):
        gid = int(path.rsplit("/", 1)[1]); self.silinen.append(gid)
        self.img = [x for x in self.img if x["listing_image_id"] != gid]
        for i, x in enumerate(self.img, 1):
            x["rank"] = i
        if self.boz:
            self.boz(self)
        return {}

    def kota_kapisi(self, ne):
        pass


class Depo:
    def __init__(self, *a): pass
    def needs_refresh(self): return False
    def write(self): pass


def kos(api, *arg):
    K.Etsy = lambda store: api; K.TokenStore = Depo
    os.environ.update(TOKEN_FILE="x", ETSY_SHOP_ID="7")
    out = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["k", "--ilan", "4570110121", "--gorsel", str(api.hedef), "--rank", "12", "--out", str(out)] + list(arg)
    try:
        K.main(); kod = 0
    except SystemExit as e:
        kod = e.code if isinstance(e.code, int) else str(e.code)
    R = out / "SONUC_4570110121.json"
    return kod, (json.loads(R.read_text()) if R.exists() else None), out


def main():
    s = []
    api = Sahte(); kod, R, out = kos(api, "--kuru")
    s.append(("kuru: silme yok, yedek + plan var", api.silinen == [] and (out / "YEDEK_4570110121.json").exists() and kod == 0))
    api = Sahte(); kod, R, _ = kos(api)
    s.append(("onaysiz silme yok", api.silinen == [] and "onay" in str(kod)))
    api = Sahte(); kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("silme PASS: sayi -1, sira ve alt metin korundu", kod == 0 and R["sonuc"] == "PASS" and api.silinen == [112] and R["sonra"] == 13))
    api = Sahte(hedef_rank=11); api.hedef = 111; kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("beklenen sirada degilse silme yok", api.silinen == [] and "sira" in str(kod)))
    api = Sahte(bag=True); kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("renk baginda ise silme yok", api.silinen == [] and "renk" in str(kod)))
    api = Sahte(state="draft"); kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("active degilse silme yok", api.silinen == [] and "state" in str(kod)))
    api = Sahte(boz=lambda A: A.img[0].update(alt_text="degisti")); kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("geri okumada alt metin degisirse FAIL", R and R["sonuc"] == "FAIL" and kod == 2))
    api = Sahte(boz=lambda A: (A.img[0].update(rank=2), A.img[1].update(rank=1))); kod, R, _ = kos(api, "--onay", K.ONAY)
    s.append(("geri okumada sira degisirse FAIL", R and R["sonuc"] == "FAIL"))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"kart_sil testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
