#!/usr/bin/env python3
"""Galeri v11 B1 yedek yerel testi (ag yok, Etsy yok, Drive yok): galeri_v11_yedek_oku (sahte Etsy) + galeri_v11_yedek_indir
(sahte CDN). Senaryolar: 3 GET / ilan, salt okuma (POST DUR), kontrol sapmalari, kota DUR'unda okunanlar yazilir, sadece
kapisi, indirme boyut kapisi, CDN disi adres, OZET.md galeri_v10_liste.ozet_oku ile okunur, workflow kilit kumesi."""
import csv
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import galeri_v11_yedek_oku as O  # noqa: E402
import galeri_v11_yedek_indir as I  # noqa: E402
import galeri_v10_liste as L  # noqa: E402
import kilit_bekle  # noqa: E402
from yd_envanter_oku import salt_okur  # noqa: E402

SONUC = []
ILAN = {"4570110121": "AQUARIUS_AQUARIUS", "4570110641": "AQUARIUS_ARIES", "4570111111": "ARIES_ARIES"}


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


class Sahte:
    def __init__(self, kota=1000, bozuk=None):
        self.calls, self.remaining, self.yol, self.bozuk = 0, kota, [], bozuk or {}

    def kota_kapisi(self, ne=""):
        if self.remaining - 4 < 10:
            raise SystemExit(f"DUR: kota {self.remaining} ({ne})")

    def _call(self, method, path, *a, **k):
        self.calls += 1; self.remaining -= 1; self.yol.append((method, path))
        lid = path.split("/listings/")[1].split("/")[0]; b = int(lid[-3:]) * 100
        if path.endswith("/images"):
            n = 9 if self.bozuk.get(lid) != "galeri" else 8
            return dict(results=[dict(rank=r, listing_image_id=b + r, alt_text=f"alt {r}", url_fullxfull=f"https://i.etsystatic.com/x/{b + r}.jpg",
                                      full_width=3000, full_height=2250, hex_code="x") for r in range(1, n + 1)][::-1])
        if path.endswith("/variation-images"):
            sira = dict(O.V10_SIRA)
            if self.bozuk.get(lid) == "bag":
                sira["Pure White"] = 8
            return dict(results=[dict(property_id=200, value_id=i, value=k, image_id=b + r) for i, (k, r) in enumerate(sira.items())])
        if path.endswith("/videos"):
            return dict(results=[] if self.bozuk.get(lid) == "video" else [dict(video_id=b, video_url=f"https://v.etsystatic.com/v/{b}.mp4",
                                                                                 thumbnail_url="t", width=1080, height=1920, video_state="active")])
        if path.rstrip("/").endswith(f"/listings/{lid}"):
            return dict(state="active", title="T", last_modified_timestamp=1)
        raise AssertionError(path)

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path)

    def post(self, *a, **k):
        raise AssertionError("post")


def ciftler(d):
    p = d / "c.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"]); w.writerows([[k, v, "x", "y"] for k, v in ILAN.items()])
    return p


def oku_testi(d):
    api = Sahte(bozuk={"4570110641": "bag", "4570111111": "video"}); salt_okur(api)
    a = SimpleNamespace(ciftler=str(ciftler(d)), out=str(d / "o"), sadece="")
    rc = O.calistir(api, "shop", a)
    kontrol("oku: cikis 0, 12 istek (3 ilan x 4 GET)", rc == 0 and api.calls == 12 and all(m == "GET" for m, _ in api.yol))
    j = json.loads((d / "o/4570110121_AQUARIUS_AQUARIUS/GALERI.json").read_text())
    kontrol("oku: GALERI.json rank sirali, alt metin + url + boyut, 5 bag, 1 video",
            [g["rank"] for g in j["gorseller"]] == list(range(1, 10)) and j["gorseller"][0]["alt_text"] == "alt 1"
            and len(j["baglar"]) == 5 and j["videolar"][0]["video_id"] == 12100 and "hex_code" not in j["gorseller"][0])
    r = {x["listing_id"]: x for x in csv.DictReader(open(d / "o/OKUMA.csv"))}
    kontrol("oku: UYGUN / SAPMA (bag sirasi, video yok)", r["4570110121"]["durum"] == "UYGUN" and "v10 sirasinda" in r["4570110641"]["neden"]
            and "video 0" in r["4570111111"]["neden"] and r["4570110121"]["istek"] == "4")
    md = (d / "o/OKUMA.md").read_text()
    kontrol("oku: OKUMA.md istek ve kota", "istek (api.calls, bu kosu) 12" in md and "kalan kota 988" in md)
    try:
        api.post("/x"); ok = False
    except SystemExit:
        ok = True
    kontrol("oku: salt okuma (POST DUR)", ok)
    try:
        api._call("PUT", "/listings/1/images"); ok = False
    except SystemExit:
        ok = True
    kontrol("oku: salt okuma (_call PUT DUR)", ok)
    api2 = Sahte(kota=17); salt_okur(api2)
    rc = O.calistir(api2, "shop", SimpleNamespace(ciftler=str(ciftler(d)), out=str(d / "k"), sadece=""))
    kontrol("oku: kota DUR -> cikis 1, okunan ilan yazildi, OKUMA.md DUR", rc == 1 and (d / "k/4570110121_AQUARIUS_AQUARIUS/GALERI.json").exists()
            and not (d / "k/4570111111_ARIES_ARIES").exists() and "DUR:" in (d / "k/OKUMA.md").read_text())
    rc = O.calistir(Sahte(), "shop", SimpleNamespace(ciftler=str(ciftler(d)), out=str(d / "s"), sadece="999"))
    kontrol("oku: sadece listede olmayan ilan -> cikis 1, istek yok", rc == 1)
    rc = O.calistir(Sahte(), "shop", SimpleNamespace(ciftler=str(ciftler(d)), out=str(d / "s2"), sadece="4570110641"))
    kontrol("oku: sadece tek ilan", rc == 0 and len(list((d / "s2").glob("*/GALERI.json"))) == 1)


def jpeg(w, h):
    b = io.BytesIO(); Image.new("RGB", (w, h), (200, 180, 160)).save(b, "JPEG"); return b.getvalue()


def indir_testi(d):
    istek = []

    class R:
        def __init__(self, c): self.content = c
        def raise_for_status(self): pass

    def get(u, timeout=0):
        istek.append(u)
        if u.endswith(".mp4"):
            return R(b"mp4" * 10)
        return R(jpeg(300, 225) if u.endswith("12105.jpg") else jpeg(3000, 2250))
    I.requests.get = get
    kok = d / "o"
    rc = I.main(["--in", str(kok), "--is", "2"])
    oz = L.ozet_oku(kok / "OZET.md")
    kontrol("indir: 3 ilan x (9 gorsel + video), boyut kapisi r5 FAIL", len(istek) == 29 and oz["4570110121"][3] == "FAIL"
            and "r5 boyut" in oz["4570110121"][4] and oz["4570110641"][3] == "PASS" and oz["4570110641"][2] == "9")
    kontrol("indir: video yok ilan PASS (video dosyasi beklenmez), 78 degil -> cikis 1", oz["4570111111"][3] == "PASS" and rc == 1)
    kontrol("indir: dosya adlari r<rank>_<id>.jpg + video_<id>.mp4",
            (kok / "4570110641_AQUARIUS_ARIES/r9_64109.jpg").exists() and (kok / "4570110641_AQUARIUS_ARIES/video_64100.mp4").exists())
    kontrol("indir: CDN disi adres reddi", I.indir("https://ornek.com/x.jpg", d / "x.jpg").startswith("CDN disi"))


def is_akisi():
    kume = kilit_bekle.kilit_kumesi(str(KOK))
    kontrol("is akisi: oku kilit kumesinde, indir kilit kumesinde degil",
            ".github/workflows/galeri-v11-yedek-oku.yml" in kume and ".github/workflows/galeri-v11-yedek-indir.yml" not in kume)
    t = (KOK / ".github/workflows/galeri-v11-yedek-oku.yml").read_text()
    kontrol("is akisi: kilit token indirmeden once, actions: read, token geri yaz, sir_koru",
            t.index("kilit_bekle.py") < t.index("ETSY_TOKEN.json") and "actions: read" in t and "token_geri_yaz.sh" in t and "sir_koru.py" in t)
    t2 = (KOK / ".github/workflows/galeri-v11-yedek-indir.yml").read_text()
    kontrol("is akisi: indir Etsy sirri / token kullanmaz", "ETSY" not in t2.replace("ETSY API YOK", "").replace("Etsy", ""))


def main():
    d = Path(tempfile.mkdtemp(prefix="gv11y_"))
    oku_testi(d); indir_testi(d); is_akisi()
    bad = [a for a, ok in SONUC if not ok]
    print(f"\nTEST {len(SONUC) - len(bad)}/{len(SONUC)} PASS" + (f" | FAIL: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
