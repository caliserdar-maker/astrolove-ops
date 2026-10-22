#!/usr/bin/env python3
"""magaza_parca_yaz sahte API testi (ag yok). Senaryolar: PASS, parca yok -> DUR, parca 2 kez -> DUR, kota dusuk -> DUR,
izinsiz HTML varligi -> DUR, geri okumada baska alan degisti -> FAIL, &#39; -> PASS_GORUNUR, yanlis onay -> HATA."""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import magaza_parca_yaz as m  # noqa: E402

DUYURU = "Welcome! Each original AstroLove design is made to order. Thank you."


class SahteEtsy:
    def __init__(self, shop, kota=500, bozan=False):
        self.shop, self.remaining, self.calls, self.bozan, self.puts = dict(shop), kota, 0, bozan, []

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        return dict(self.shop)

    def put(self, path, data):
        self.calls += 1
        self.puts.append(dict(data))
        self.shop.update(data)
        if self.bozan:
            self.shop["sale_message"] = "degisti"


class SahteStore:
    def __init__(self, *a):
        pass

    def needs_refresh(self):
        return False


def kos(shop, kota=500, bozan=False, onay="DUYURU_MARKA"):
    api = SahteEtsy(shop, kota, bozan)
    m.Etsy, m.TokenStore = (lambda store: api), SahteStore
    out = tempfile.mkdtemp()
    sys.argv = ["x", "--is", "duyuru_marka", "--out", out, "--confirm", onay]
    try:
        m.main(); kod = 0
    except SystemExit as e:
        kod = e.code if isinstance(e.code, int) else ("HATA" if e.code else 0)
    rapor = (pathlib.Path(out) / "DUYURU_GERI_OKUMA.txt")
    return kod, api, rapor.read_text() if rapor.exists() else ""


def main():
    os.environ.update(ETSY_SHOP_ID="1", TOKEN_FILE="/dev/null")
    taban = {"title": "t", "announcement": DUYURU, "sale_message": "s"}
    sonuc = []

    kod, api, r = kos(taban)
    sonuc.append(("PASS", kod == 0 and len(api.puts) == 1 and api.puts[0] == {"announcement": DUYURU.replace("AstroLove design", "AstroLoveArt design")}
                  and "SONUC: PASS" in r and "yeni parca 1" in r and "eski parca (Art'siz) 0" in r))
    kod, api, r = kos({**taban, "announcement": "Each original AstroLoveArt design."})
    sonuc.append(("zaten duzeltilmis -> DUR", kod == 3 and not api.puts))
    kod, api, r = kos({**taban, "announcement": DUYURU + " " + DUYURU})
    sonuc.append(("parca 2 kez -> DUR", kod == 3 and not api.puts))
    kod, api, r = kos(taban, kota=9)
    sonuc.append(("kota 9 -> DUR", kod == 3 and not api.puts))
    kod, api, r = kos({**taban, "announcement": DUYURU + " A &amp; B"})
    sonuc.append(("&amp; -> DUR", kod == 3 and not api.puts))
    kod, api, r = kos(taban, bozan=True)
    sonuc.append(("baska alan degisti -> FAIL", kod == 2 and "SONUC: FAIL" in r))
    kod, api, r = kos({**taban, "announcement": DUYURU + " We don&#39;t stop."})
    sonuc.append(("&#39; -> gonderilen unescape", len(api.puts) == 1 and "don't" in api.puts[0]["announcement"]))
    kod, api, r = kos(taban, onay="YANLIS")
    sonuc.append(("yanlis onay -> yazma yok", kod == "HATA" and not api.puts))

    for ad, ok in sonuc:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in sonuc)
    print(f"magaza_parca_yaz testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
