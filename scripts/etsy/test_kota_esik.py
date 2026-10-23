#!/usr/bin/env python3
"""Kota esigi (Serdar 23 Eki 2b) sahte testi, ag yok: config yok/pasif = etkisiz; genel / pod-audit / router esikleri;
ilk yanittan sonra kosu kapisi; ilan kapisi; sert taban; router receipt okumasi kota yuzunden durursa hata."""
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


def api_kur(kalanlar, conf, rol="genel"):
    d = pathlib.Path(tempfile.mkdtemp()) / "esik.json"
    if conf is not None:
        d.write_text(json.dumps(conf))
    E.KOTA_ESIK_DOSYA = d
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
    C = dict(aktif=True, taban=400, R=15, M=51, P=1638)
    s = []
    api = api_kur([100, 90, 80], None)
    s.append(("config yok -> etkisiz (eski davranis)", api.esik is None and dur_mu(lambda: [api.get("/x") for _ in range(3)]) is None))
    api = api_kur([100, 90], dict(C, aktif=False))
    s.append(("aktif false -> etkisiz", api.esik is None and dur_mu(lambda: [api.get("/x") for _ in range(2)]) is None))
    api = api_kur([100, 90], dict(C, aktif="true"))
    s.append(("aktif 'true' (metin) -> etkisiz", api.esik is None))
    s.append(("onayli esikler: genel 481/430, pod-audit 2068/430, siparis yok/415, router muaf",
              (api_kur([1], C).esik, api_kur([1], C).sert_taban) == (481, 430)
              and (api_kur([1], C, "pod-audit").esik, api_kur([1], C, "pod-audit").sert_taban) == (2068, 430)
              and (api_kur([1], C, "siparis").esik, api_kur([1], C, "siparis").sert_taban) == (None, 415)
              and (api_kur([1], C, "router").esik, api_kur([1], C, "router").sert_taban) == (None, None)))
    d = pathlib.Path(tempfile.mkdtemp()) / "bozuk.json"; d.write_text("{aktif: true,,")
    s.append(("bozuk JSON -> PASIF, kosu durmaz (Serdar 23 Eki)", E.kota_esigi("genel", d) == (None, None)))
    s.append(("aktif + eksik alan / tuhaf deger -> PASIF; bilinmeyen rol -> siparis tabani 415",
              api_kur([1], dict(C, P=None), "pod-audit").sert_taban is None and api_kur([1], dict(C, taban=True)).sert_taban is None
              and api_kur([1], dict(C, taban=40000)).sert_taban is None
              and (api_kur([1], C, "sipars").esik, api_kur([1], C, "sipars").sert_taban) == (None, 415)))
    api = api_kur([1000, 420, 416, 414, 400], C, "siparis")
    r = dur_mu(lambda: [api.get("/x") for _ in range(5)])
    s.append(("siparis rolu: 481'in altinda baslar, 415 altinda durur", bool(r) and "sert tabani" in r and api.calls == 4))
    api = api_kur([480, 470], C)
    r = dur_mu(lambda: [api.get("/x") for _ in range(2)])
    s.append(("ilk yanit 480 < 481 -> 2. istekten once DUR", bool(r) and "kota esigi" in r and api.calls == 1))
    api = api_kur([1000, 990, 600, 500], C)
    s.append(("esik uzerinde baslayan kosu pay ustunde surer", dur_mu(lambda: [api.get("/x") for _ in range(4)]) is None and api.calls == 4))
    s.append(("ilan kapisi: kalan 500 >= 481 gecer", dur_mu(lambda: api.kota_kapisi("ilan 4")) is None))
    api = api_kur([1000, 440, 429, 400, 390], C)
    r = dur_mu(lambda: [api.get("/x") for _ in range(5)])
    s.append(("sert taban (430): 429 yanitindan sonra istek yok", bool(r) and "sert tabani" in r and api.calls == 3))
    api = api_kur([1000, 429] + [400] * 50, C)
    yutulan = 0
    for _ in range(50):   # SystemExit'i yakalayip devam eden betik (digital_desc_batch gibi)
        try:
            api.get("/x")
        except SystemExit:
            yutulan += 1
    s.append(("DUR yutulsa da sonraki istekler gonderilmez", api.calls == 2 and yutulan == 48))
    api = api_kur([1000], C)
    api.get("/x"); api.remaining = None
    s.append(("aktifken baslik okunamazsa DUR", "okunamadi" in (dur_mu(lambda: api.get("/x")) or "")))
    import order_router as R  # noqa: E402

    class Api:
        remaining = None

        def get(self, path, params=None):
            self.remaining = "350"
            return {"results": [{"receipt_id": i} for i in range(100)]}
    R.KOTA_DURDU.clear()
    out = R.etsy_receipts(Api(), "1", 7, 10, 400)
    s.append(("router: kota 350 < 400 -> okuma durur ve KOTA_DURDU dolu", len(out) == 100 and len(R.KOTA_DURDU) == 1))
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
    gercek = json.loads((KOK / "config" / "etsy_kota_esik.json").read_text())
    s.append(("depodaki config aktif degil (onay bekliyor)", gercek.get("aktif") is False))
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"kota esigi testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
