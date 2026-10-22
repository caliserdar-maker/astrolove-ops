#!/usr/bin/env python3
"""marka_tara sahte API testi (ag yok): etsy modu sayfalama + batch + dosya adlari + kota DUR; eslestirici ornekleri."""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common  # noqa: E402
import marka_tara as m  # noqa: E402


class SahteEtsy:
    def __init__(self, n, kota=500):
        self.n, self.remaining, self.calls = n, kota, 0
        self.ilan = {str(i): dict(listing_id=i, title=("AstroLove gift" if i == 1 else "AstroLoveArt gift"),
                                  description="Shop AstroLoveArt.", tags=["astrolove"] if i == 2 else ["zodiac"],
                                  listing_type="download" if i % 2 else "physical",
                                  images=[dict(rank=1, alt_text="by Astro Love" if i == 3 else "ok")]) for i in range(1, n + 1)}

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/listings"):
            off, lim = params["offset"], params["limit"]
            ids = list(self.ilan)[off:off + lim]
            return dict(count=self.n, results=[dict(listing_id=int(i)) for i in ids])
        if path == "/listings/batch":
            return dict(results=[self.ilan[i] for i in params["listing_ids"].split(",")])
        if path.endswith("/files"):
            return dict(results=[dict(filename="ASTROLOVE_DIGITAL_THANKYOU_EN.pdf"), dict(filename="AstroLoveArt_X.zip")])
        return dict(title="AstroLoveArt", announcement="Each original AstroLove design", sale_message="Thanks, AstroLoveArt")


class SahteStore:
    def __init__(self, *a):
        pass

    def needs_refresh(self):
        return False


def kos(n, kota=500):
    api = SahteEtsy(n, kota)
    etsy_common.Etsy, etsy_common.TokenStore = (lambda s: api), SahteStore
    out = tempfile.mkdtemp()
    sys.argv = ["x", "etsy", "--out", out]
    try:
        m.main(); kod = 0
    except SystemExit as e:
        kod = e.code
    oz = {}
    for k in ("MAGAZA", "ILAN", "ETSY_DOSYA"):
        f = pathlib.Path(out) / f"MARKA_{k}.json"
        oz[k] = json.loads(f.read_text())["ozet"] if f.exists() else None
    return kod, api, oz


def main():
    os.environ.update(ETSY_SHOP_ID="1", TOKEN_FILE="/dev/null")
    sonuc = []
    kod, api, oz = kos(234)
    sonuc.append(("234 ilan, 3 sayfa + 3 batch", kod == 0 and oz["ILAN"]["aktif_ilan"] == 234 and oz["ILAN"]["dijital_ilan"] == 117))
    sonuc.append(("ilan gecis 3 (baslik, etiket, alt metin)", oz["ILAN"]["metin_gecis"] == 3
                  and oz["ILAN"]["alan_basina"] == {"title": 1, "tags": 1, "alt_text": 1}))
    sonuc.append(("magaza duyuru 1", oz["MAGAZA"]["metin_gecis"] == 1 and oz["MAGAZA"]["alan_basina"] == {"announcement": 1}))
    sonuc.append(("dosya adi 117 (THANKYOU)", oz["ETSY_DOSYA"]["metin_gecis"] == 117 and oz["ETSY_DOSYA"]["farkli_dosya_adi"] == 2))
    kod, api, oz = kos(234, kota=9)
    sonuc.append(("kota 9 -> DUR", isinstance(kod, str) and kod.startswith("DUR")))
    for t, beklenen in [("AstroLove", 1), ("AstroLoveArt", 0), ("ASTRO LOVE ART", 0), ("astro-love", 1),
                        ("https://x.github.io/astrolove-media/a.jpg", 0)]:
        sonuc.append((f"eslestirici {t!r}", m.bul(t)[0] == beklenen))
    for ad, ok in sonuc:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in sonuc)
    print(f"marka_tara testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
