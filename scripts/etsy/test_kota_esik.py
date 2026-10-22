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
    C = dict(aktif=True, taban=400, R=15, M=51, P=546)
    s = []
    api = api_kur([100, 90, 80], None)
    s.append(("config yok -> etkisiz (eski davranis)", api.esik is None and dur_mu(lambda: [api.get("/x") for _ in range(3)]) is None))
    api = api_kur([100, 90], dict(C, aktif=False))
    s.append(("aktif false -> etkisiz", api.esik is None and dur_mu(lambda: [api.get("/x") for _ in range(2)]) is None))
    api = api_kur([100, 90], dict(C, aktif="true"))
    s.append(("aktif 'true' (metin) -> etkisiz", api.esik is None))
    s.append(("esikler: genel 481 / pay 430, pod-audit 976, router muaf", api_kur([1], C).esik == 481 and api_kur([1], C).sert_taban == 430
              and api_kur([1], C, "pod-audit").esik == 976 and api_kur([1], C, "router").esik is None))
    s.append(("aktif + eksik alan / bilinmeyen rol -> DUR (fail-closed)", "eksik" in (dur_mu(lambda: api_kur([1], dict(C, P=None), "pod-audit")) or "")
              and "bilinmiyor" in (dur_mu(lambda: api_kur([1], C, "pod_audit")) or "")))
    api = api_kur([480, 470], C)
    r = dur_mu(lambda: [api.get("/x") for _ in range(2)])
    s.append(("ilk yanit 480 < 481 -> 2. istekten once DUR", bool(r) and "kota esigi" in r and api.calls == 1))
    api = api_kur([1000, 990, 600, 500], C)
    s.append(("esik uzerinde baslayan kosu pay ustunde surer", dur_mu(lambda: [api.get("/x") for _ in range(4)]) is None and api.calls == 4))
    s.append(("ilan kapisi: kalan 500 >= 481 gecer", dur_mu(lambda: api.kota_kapisi("ilan 4")) is None))
    api = api_kur([1000, 440, 429, 400, 390], C)
    r = dur_mu(lambda: [api.get("/x") for _ in range(5)])
    s.append(("siparis payi (430): 429 yanitindan sonra istek yok", bool(r) and "siparis payi" in r and api.calls == 3))
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
    gercek = json.loads((KOK / "config" / "etsy_kota_esik.json").read_text())
    s.append(("depodaki config aktif degil (onay bekliyor)", gercek.get("aktif") is False))
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"kota esigi testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
