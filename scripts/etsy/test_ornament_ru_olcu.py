#!/usr/bin/env python3
"""ornament_ru_olcu.py sahte Etsy testleri (ag yok). Bilinen PASS: RU + olcu yazimi, zaten var. Bilinen FAIL: RU sha, izin disi
yazma, PATCH (acil disi), state active (yazim oncesi DUR, yazim sonrasi ACIL inactive), baslik kimligi, geri okuma farki, pilot kapisi."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ornament_ru_olcu as g  # noqa: E402

LID = 4611501158
OLCU = [{"property_id": 111, "value_ids": [], "values": ["7.6"], "scale_id": 5}]


class Sahte(g.Kilitli):
    def __init__(self, title):
        self.remaining, self.calls, self.kayit = "5000", 0, []
        self.L = {"state": "draft", "title": title}
        self.ru, self.props, self.bozuk_ru, self.aktif_et = {}, {}, False, False

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and data != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        self.kayit.append((method, path, data)); self.calls += 1
        if method == "GET":
            if path.endswith("/translations/ru"):
                return dict(self.ru) or (None if ok404 else {})
            if path.endswith("/properties"):
                return {"results": [dict(property_id=k, scale_id=v[0], values=v[1]) for k, v in self.props.items()]}
            if path == f"/listings/{LID}":
                return dict(self.L)
            return {}
        if method == "PUT" and path.endswith("/translations/ru"):
            self.ru = {"title": data["title"], "description": ("x" if self.bozuk_ru else data["description"])}
            if self.aktif_et:
                self.L["state"] = "active"
            return self.ru
        if method == "PUT" and "/properties/" in path:
            self.props[int(path.rsplit("/", 1)[1])] = (data.get("scale_id"), data["values"].split(","))
            return {}
        if method == "PATCH":
            self.L["state"] = "inactive"; return self.L
        raise SystemExit(f"taklit edilmeyen {method} {path}")


def bekle_dur(fn, metin):
    try:
        fn()
    except SystemExit as e:
        assert metin in str(e.code), (metin, e.code)
        return e
    raise AssertionError(f"DUR bekleniyordu: {metin}")


def main():
    g.time.sleep = lambda s: None
    RU = g.ru_metin()
    Y = {"CANCER_LIBRA": {"listing_id": LID}}
    title = g.en_baslik("CANCER_LIBRA")
    with tempfile.TemporaryDirectory() as t:
        o = Path(t)
        # 1 PASS
        a = Sahte(title); R = g.yaz(a, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU)
        assert all(R["kontrol"].values()) and a.props[111] == (5, ["7.6"]) and not [k for k in a.kayit if k[0] == "PATCH"]
        assert a.ru["title"] == RU["CANCER_LIBRA"]["baslik_ru"]
        # 2 zaten var: RU PUT yok
        n0 = len([k for k in a.kayit if k[0] == "PUT" and k[1].endswith("/ru")]); g.yaz(a, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU)
        assert len([k for k in a.kayit if k[0] == "PUT" and k[1].endswith("/ru")]) == n0
        # 3 izin disi
        b = Sahte(title); b.lid, b.pid_izin = LID, frozenset({111})
        bekle_dur(lambda: b._izin("PUT", f"/shops/1/listings/{LID}/properties/222"), "YASAK")
        bekle_dur(lambda: b._izin("PUT", f"/shops/1/listings/{LID}/translations/de"), "YASAK")
        bekle_dur(lambda: b._izin("POST", f"/shops/1/listings/{LID}/images"), "YASAK")
        bekle_dur(lambda: b._call("PATCH", f"/shops/1/listings/{LID}", data={"title": "x"}), "YASAK")
        # 4 baslangicta active: yazim yok
        c = Sahte(title); c.L["state"] = "active"
        bekle_dur(lambda: g.yaz(c, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU), "dokunulmadi")
        assert not [k for k in c.kayit if k[0] != "GET"]
        # 5 RU yazimi taslagi yayina alirsa: ACIL inactive, exit 2
        d = Sahte(title); d.aktif_et = True
        e = bekle_dur(lambda: g.yaz(d, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU), "")
        assert e.code == 2 and d.L["state"] == "inactive"
        # 6 baslik kimligi
        f = Sahte("baska")
        bekle_dur(lambda: g.yaz(f, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU), "kimlik")
        # 7 geri okuma farkli
        h = Sahte(title); h.bozuk_ru = True
        bekle_dur(lambda: g.yaz(h, "39729443", o, "CANCER_LIBRA", Y, RU, OLCU), "RU geri okuma")
        # 8 sha
        asil = g.RU_SHA; g.RU_SHA = "0" * 64
        bekle_dur(g.ru_metin, "sha256"); g.RU_SHA = asil
    print("test_ornament_ru_olcu: 8/8 PASS")


if __name__ == "__main__":
    main()
