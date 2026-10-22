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
                                  personalization={"questions": [{"question_text": "Name for AstroLove card" if i == 4 else "Name"}]},
                                  translations=[{"language": "ru", "title": "AstroLove подарок" if i == 5 else "AstroLoveArt",
                                                 "description": "", "tags": []}],
                                  images=[dict(rank=1, alt_text="by Astro Love" if i == 3 else "ok", url_fullxfull=f"u{i}")])
                     for i in range(1, n + 1)}

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/listings"):
            if params["state"] != "active":
                return dict(count=0, results=[])
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
    for k in ("MAGAZA", "ILAN_ACTIVE", "ETSY_DOSYA"):
        f = pathlib.Path(out) / f"MARKA_{k}.json"
        oz[k] = json.loads(f.read_text())["ozet"] if f.exists() else None
    return kod, api, oz


def gorsel_testi():
    from PIL import Image, ImageDraw, ImageFont
    td = tempfile.mkdtemp()
    im = Image.new("RGB", (1400, 500), "white")
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
    except OSError:
        f = ImageFont.load_default()
    ImageDraw.Draw(im).text((60, 200), "ASTROLOVE / ARIES + LEO", fill="black", font=f)
    im.save(f"{td}/a.png")
    Image.new("RGB", (800, 400), "white").save(f"{td}/b.png")
    liste = [dict(kimlik="1#1", url=f"file://{td}/a.png"), dict(kimlik="2#1", url=f"file://{td}/b.png"),
             dict(kimlik="3#1", url=f"file://{td}/yok.png")]
    json.dump(liste, open(f"{td}/l.json", "w"))
    sys.argv = ["x", "gorsel", "--out", td, "--liste", f"{td}/l.json"]
    m.main()
    oz = json.load(open(f"{td}/MARKA_GORSEL.json"))["ozet"]
    return [("gorsel OCR: 1 gecis, 1 okuma hatasi", oz["metin_gecis"] == 1 and oz["ilan_basina"] == 1 and sum(oz["okuma_hatasi"].values()) == 1)]


def metricool_testi():
    import types
    from datetime import datetime
    cagri = []

    class SahteMC:
        def __init__(self, tok):
            pass

        def istek(self, y, yol, params=None):
            b = datetime.fromisoformat(params["start"]); s = datetime.fromisoformat(params["end"])
            cagri.append((s - b).days)
            n = 120 if (s - b).days >= 6 and b.day == 8 else (3 if (s - b).days >= 6 else 1)   # 8. gunden baslayan hafta 120 kayit
            return [dict(id=f"{params['start']}-{i}", text="AstroLove pin" if i == 0 else "ok",
                         pinterestData={"pinLink": "https://www.etsy.com/listing/1"},
                         providers=[dict(network="pinterest", status="PUBLISHED")]) for i in range(n)]

    mod = types.ModuleType("metricool_pin_baslik"); mod.MC, mod.TZ, mod.veri = SahteMC, "UTC", (lambda j: j)
    sys.modules["metricool_pin_baslik"] = mod
    td = tempfile.mkdtemp(); json.dump({}, open(f"{td}/t.json", "w"))
    sys.argv = ["x", "metricool", "--out", td, "--token-dosya", f"{td}/t.json", "--bas", "2026-08-01T00:00:00", "--son", "2026-08-22T00:00:00"]
    m.main()
    oz = json.load(open(f"{td}/MARKA_METRICOOL.json"))["ozet"]
    return [("metricool: 3 hafta + 100'luk haftada 7 gunluk parca", oz["istek_hafta"] == 3 and oz["istek_gun"] == 7),
            ("metricool: tum durumlar, gecis = gonderi basina 1", oz["metin_gecis"] == 1 + 7 + 1 and oz["gonderi"] == 3 + 7 + 3 and oz["ag_durum"].get("pinterest:PUBLISHED") == oz["gonderi"])]


def main():
    os.environ.update(ETSY_SHOP_ID="1", TOKEN_FILE="/dev/null")
    sonuc = []
    kod, api, oz = kos(234)
    sonuc.append(("234 aktif ilan, 3 sayfa + 3 batch", kod == 0 and oz["ILAN_ACTIVE"]["ilan"] == 234))
    sonuc.append(("ilan gecis 5 (baslik, etiket, alt metin, kisisellestirme sorusu, RU ceviri)", oz["ILAN_ACTIVE"]["metin_gecis"] == 5
                  and oz["ILAN_ACTIVE"]["alan_basina"] == {"title": 1, "tags": 1, "alt_text": 1,
                                                           "personalization.questions.question_text": 1, "ceviri_ru.title": 1}))
    sonuc.append(("magaza duyuru 1", oz["MAGAZA"]["metin_gecis"] == 1 and oz["MAGAZA"]["alan_basina"] == {"announcement": 1}))
    sonuc.append(("dosya adi 117 (THANKYOU)", oz["ETSY_DOSYA"]["metin_gecis"] == 117 and oz["ETSY_DOSYA"]["farkli_dosya_adi"] == 2))
    kod, api, oz = kos(234, kota=9)
    sonuc.append(("kota 9 -> DUR", isinstance(kod, str) and kod.startswith("DUR")))
    for t, beklenen in [("AstroLove", 1), ("AstroLoveArt", 0), ("ASTRO LOVE ART", 0), ("astro-love", 1),
                        ("https://x.github.io/astrolove-media/a.jpg", 0), ("Astro\u2011Love", 1), ("Astro.Love", 1),
                        ("Astro\u200bLove", 1), ("AstroLove's", 1), ("ASTROLOVE / ARIES + LEO", 1)]:
        sonuc.append((f"eslestirici {t!r}", m.bul(t)[0] == beklenen))
    sonuc += gorsel_testi() + metricool_testi()
    for ad, ok in sonuc:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in sonuc)
    print(f"marka_tara testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
