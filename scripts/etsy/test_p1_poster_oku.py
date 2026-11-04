#!/usr/bin/env python3
"""p1_poster_oku testi (ag yok). Gercek SaltOku kapisi sinanir: yalniz etsy_common.Etsy._call alttan sahtelenir (inceleme 4 Kas D-2).
Bilinen PASS + bilinen FAIL: yalniz GET; PUT/POST/DELETE/post_file DUR; 404 ve 5xx -> okunamadi; 429 / 403 -> kosu durur;
baslangic ve ilan basina kota kapisi; OZET alanlari."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import p1_poster_oku as O  # noqa: E402

sonuc = []
POSTER = ["11", "22", "33"]


def k(ad, kosul, ayr=""):
    sonuc.append((ad, bool(kosul)))
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {ayr}" if ayr and not kosul else ""), flush=True)


class Ortam:
    def __init__(self, kalan=5000, hata=None, ru_yok=(), ek=0):
        self.kalan, self.hata, self.ru_yok, self.ek, self.cagri = kalan, dict(hata or {}), set(ru_yok), ek, []


def sahte_call(self, method, path, params=None, data=None, ok404=False, json_body=None):
    o = self._ortam
    o.cagri.append((method, path))
    o.kalan -= 1 + (o.ek if path.endswith("/translations/ru") else 0)
    self.remaining = o.kalan
    for anahtar, kod in o.hata.items():
        if anahtar in path:
            if kod == 404 and ok404:
                return {}
            raise SystemExit(f"HATA: {method} {path} -> {kod}: govde" if kod != 429 else "HATA: 429 kota. retry-after=3600")
    if path.endswith("/listings/active"):
        off = (params or {}).get("offset", 0)
        r = [dict(listing_id=int(i), title="x", description="a. If we don&#39;t hear from you within 24 hours of receiving the "
                  "preview, we go ahead with the design as shown: b") for i in POSTER] if off == 0 else []
        return dict(count=len(POSTER) + 1, results=r + ([dict(listing_id=999, title="Cancer mug", description="")] if off == 0 else []))
    if path.endswith("/inventory"):
        return {"products": []}
    if path.endswith("/translations/ru"):
        lid = path.split("/")[-3]
        return {} if lid in o.ru_yok else {"title": "т", "description": "о", "tags": ["т"]}
    lid = path.split("/")[-1]
    return dict(listing_id=int(lid), state="active", title="t", description="d", tags=["a"], materials=["m"])


E.Etsy._call = sahte_call   # ag yok: SaltOku._call -> (yalniz GET ise) super()._call = sahte


def api(o):
    a = O.SaltOku.__new__(O.SaltOku)
    a._ortam, a.remaining, a.esik, a.sert_taban = o, o.kalan, None, None
    return a


def kos(o, poster=POSTER):
    t = pathlib.Path(tempfile.mkdtemp()); oz = {}
    try:
        O.calis(api(o), "39729443", t, poster, set(), oz); hata = None
    except SystemExit as e:
        hata = str(e)
    h = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (t / "HAM").glob("*.json")}
    return t, oz, h, hata


# bilinen PASS
o = Ortam(hata={"/listings/22/inventory": 404}, ru_yok={"33"})
t, oz, h, hata = kos(o)
k("kosu tamam, 3 ilan HAM", hata is None and sorted(h) == POSTER, hata)
k("404 -> okunamadi (yalniz durum kodu), kosu surer", h["22"]["ru_durum"] == "okunamadi" and h["22"]["hata"] == "HTTP 404" and oz["okunamadi"] == ["22"])
k("RU yok -> ru_durum yok", h["33"]["ru_durum"] == "yok" and oz["ru_yok"] == ["33"])
k("yalniz GET cagrildi", o.cagri and all(m == "GET" for m, _ in o.cagri), {m for m, _ in o.cagri})
k("RU tekil yol /shops/{shop}/listings/{id}/translations/ru", ("GET", "/shops/39729443/listings/11/translations/ru") in o.cagri)
sat = (t / "AKTIF_SAYIM.csv").read_text(encoding="utf-8").splitlines()
k("AKTIF_SAYIM: 4 ilan, html cozuldu (genel 1, go_ahead 1)", len(sat) == 5 and ",poster78,1,1,0" in sat[1] and "kupa" in sat[4], sat)
k("islenmedi bos, kota_son yazildi", oz["islenmedi"] == [] and oz.get("kota_son") is not None)
o = Ortam(hata={"/listings/11/inventory": 503}); _, oz, h, hata = kos(o)
k("5xx (denemeler sonrasi) -> okunamadi", hata is None and h["11"]["hata"] == "HTTP 503")
# bilinen FAIL: yazma cagrilari gercek SaltOku kapisinda durur
for ad, f in (("PUT", lambda a: a.put("/shops/1/listings/1", {})), ("PATCH", lambda a: a.patch("/shops/1/listings/1", {})),
              ("POST", lambda a: a.post("/shops/1/listings", {})), ("DELETE", lambda a: a.delete("/shops/1/listings/1")),
              ("post_file", lambda a: a.post_file("/shops/1/listings/1/images", {}))):
    o = Ortam()
    try:
        f(api(o)); k(f"{ad} -> DUR", False)
    except SystemExit as e:
        k(f"{ad} -> DUR (salt okuma), istek gitmedi", "YASAK" in str(e) and not o.cagri, str(e))
# bilinen FAIL: 429 / 403 kosuyu durdurur (okunamadi sayilmaz)
for kod in (429, 403):
    _, oz, h, hata = kos(Ortam(hata={"/listings/22": kod}))
    k(f"{kod} -> kosu durur, islenmedi 22'den itibaren", hata is not None and oz["islenmedi"] == ["22", "33"], (hata, oz.get("islenmedi")))
# bilinen FAIL: baslangic kota kapisi (3 x 3 + 0 + 10 = 19 > 15)
_, oz, h, hata = kos(Ortam(kalan=16))
k("baslangic kota kapisi DUR, HAM yok, islenmedi tum liste", hata and "baslangic" in hata and not h and oz["islenmedi"] == POSTER, (hata, oz))
# bilinen FAIL: ilan basina kota (baska tuketim) -> ortada DUR
_, oz, h, hata = kos(Ortam(kalan=30, ek=6))
k("ilan basina kota DUR + islenmedi + kota_son", hata and "kota" in hata and oz["islenmedi"] and oz.get("kota_son") is not None, (hata, oz))
k("KOTA_SINIRI 10 (degistirilmedi)", E.KOTA_SINIRI == 10)
n = sum(1 for _, v in sonuc if v)
print(f"SONUC {n}/{len(sonuc)}")
sys.exit(0 if n == len(sonuc) else 1)
