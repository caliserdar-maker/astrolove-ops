#!/usr/bin/env python3
"""Kota siniri 10 (Serdar 15 ve 24 Eki) sahte testi, ag yok: her rol 10/10; ilk yanittan sonra kosu kapisi; ilan kapisi;
sert taban; router receipt okumasi kota yuzunden durursa hata; router varsayilani 10."""
import json
import os
import pathlib
import sys
import tempfile

KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "prodigi"))
import etsy_common as E  # noqa: E402


class Yanit:
    def __init__(self, kalan):
        self.status_code, self.headers, self.text = 200, {"x-remaining-today": str(kalan)}, "{}"

    def json(self):
        return {"results": []}


class Depo:
    api_key_header, access_token = "k:s", "t"


def api_kur(kalanlar, rol="genel"):
    os.environ["ETSY_KOTA_ROL"] = rol
    seri = iter(kalanlar)
    E.requests.request = lambda *a, **k: Yanit(next(seri))
    E.time.sleep = lambda s: None
    return E.Etsy(Depo())


def dur_mu(f):
    try:
        f(); return None
    except SystemExit as e:
        return str(e)


def main():
    s = []
    E.log = lambda m: None
    s.append(("KOTA_SINIRI 10 (Serdar 15 ve 24 Eki)", E.KOTA_SINIRI == 10))
    s.append(("her rol (genel, pod-audit, siparis, router, bilinmeyen) -> (10, 10)",
              all((api_kur([1], r).esik, api_kur([1], r).sert_taban) == (10, 10)
                  for r in ("genel", "pod-audit", "siparis", "router", "sipars"))))
    s.append(("kota_esigi rol/dosya argumani etkisiz", E.kota_esigi("pod-audit", "/yok.json") == (10, 10)))
    s.append(("config/etsy_kota_esik.json kaldirildi", not (KOK / "config" / "etsy_kota_esik.json").exists()))
    api = api_kur([477, 470, 300, 11])
    s.append(("23 Eki esiklerinin altinda (477, 300, 11) kosu surer", dur_mu(lambda: [api.get("/x") for _ in range(4)]) is None
              and api.calls == 4))
    s.append(("ilan kapisi: kalan 11 >= 10 gecer", dur_mu(lambda: api.kota_kapisi("ilan 4")) is None))
    api = api_kur([9, 8])
    r = dur_mu(lambda: [api.get("/x") for _ in range(2)])
    s.append(("ilk yanit 9 < 10 -> 2. istekten once DUR", bool(r) and "kota esigi" in r and api.calls == 1))
    api = api_kur([500, 10, 9, 5])
    r = dur_mu(lambda: [api.get("/x") for _ in range(4)])
    s.append(("sert taban 10: 9 yanitindan sonra istek yok", bool(r) and "sert tabani" in r and api.calls == 3))
    api = api_kur([500, 9] + [5] * 50)
    yutulan = 0
    for _ in range(50):   # SystemExit'i yakalayip devam eden betik (digital_desc_batch gibi)
        try:
            api.get("/x")
        except SystemExit:
            yutulan += 1
    s.append(("DUR yutulsa da sonraki istekler gonderilmez", api.calls == 2 and yutulan == 48))
    api = api_kur([500])
    api.get("/x"); api.remaining = None
    s.append(("baslik okunamazsa DUR", "okunamadi" in (dur_mu(lambda: api.get("/x")) or "")))
    import order_router as R  # noqa: E402

    class Api:
        remaining = None

        def get(self, path, params=None):
            self.remaining = "350"
            return {"results": [{"receipt_id": i} for i in range(100)]}
    R.KOTA_DURDU.clear()
    out = R.etsy_receipts(Api(), "1", 7, 10, 400)
    s.append(("router: zorlanmis taban 400, kota 350 -> okuma durur ve KOTA_DURDU dolu", len(out) == 100 and len(R.KOTA_DURDU) == 1))
    s.append(("router --quota-min varsayilani 10", "default=10," in (KOK / "scripts" / "prodigi" / "order_router.py").read_text()
              .split('"--quota-min"')[1][:40]))
    # router --kota-deneme (Serdar 23 Eki 4): sayfa 1, zorlanmis taban -> 1 receipt okunur, KOTA_DURDU.txt; normal -> hepsi
    FIS = [dict(receipt_id=100 + i, created_timestamp=5000 - i) for i in range(5)]

    class FEtsy:
        def __init__(self, store):
            self.calls, self.remaining = 0, None

        def get(self, path, params=None):
            self.calls += 1; self.remaining = "700"
            o, n = params.get("offset", 0), params["limit"]
            assert "was_shipped" not in params
            return {"results": FIS[o:o + n]}

    class FStore:
        def __init__(self, *a):
            pass

        def needs_refresh(self):
            return False
    R.Etsy, R.TokenStore = FEtsy, FStore
    os.environ.update(ETSY_API_KEY="k", ETSY_SHARED_SECRET="s", ETSY_SHOP_ID="1", TOKEN_FILE="x")
    sonuc = {}
    for ad, qmin in (("dusuk", 99999), ("normal", 0)):
        o = pathlib.Path(tempfile.mkdtemp())
        sys.argv = ["x", "--state", str(o / "st.csv"), "--out", str(o), "--kota-deneme", "--sayfa", "1", "--max-pages", "20",
                    "--quota-min", str(qmin)]
        R.main()
        sonuc[ad] = (json.loads((o / "KOTA_DENEME.json").read_text()), (o / "KOTA_DURDU.txt").exists())
    d, n_ = sonuc["dusuk"], sonuc["normal"]
    s.append(("kota-deneme dusuk: 1 receipt, KOTA_DURDU.txt var", d[0]["okunan"] == 1 and d[1] and len(d[0]["kota_durdu"]) == 1))
    s.append(("kota-deneme normal: 5 receipt, okunmayan 4'u de var, KOTA_DURDU yok, sira azalan", n_[0]["okunan"] == 5 and not n_[1]
              and set(d[0]["kodlar"]) < set(n_[0]["kodlar"]) and n_[0]["sira_azalan"] is True))
    FIS[:] = [dict(receipt_id=200 + i) for i in range(3)]
    o = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["x", "--state", str(o / "st.csv"), "--out", str(o), "--kota-deneme", "--sayfa", "1", "--max-pages", "20", "--quota-min", "0"]
    R.main()
    z = json.loads((o / "KOTA_DENEME.json").read_text())
    s.append(("kota-deneme: zaman damgasi yoksa sira None (sahte PASS yok)", z["sira_azalan"] is None and z["zaman_eksik"] == 3))
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"kota siniri testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
