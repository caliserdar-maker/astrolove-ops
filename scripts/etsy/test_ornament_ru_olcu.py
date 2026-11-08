#!/usr/bin/env python3
"""ornament_ru_olcu.py sahte Etsy testleri (ag yok). Sahte yazmalar etsy_common kapilarindan (ru_yazim, ai_beyan, metin_yasak) gecer.
Bilinen PASS: RU yokken POST + olcu, RU farkliyken PUT, zaten var, sayisal olcu (2.99 / "2.99"), pilot dogrulama.
Bilinen FAIL: RU sha, OLCU yok / sha / bos, izin disi yazma, PATCH (acil disi), state active (once DUR, sonra ACIL inactive),
baslik kimligi, geri okuma farki, bicim kaybi, properties 4xx, salt okuma yazmasi, pilot dogrulanmadi."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as ec  # noqa: E402
import ornament_ru_olcu as g  # noqa: E402

LID = 4611501158
OLCU = [{"property_id": 111, "value_ids": [], "values": ["2.99"], "scale_id": 5},
        {"property_id": 222, "value_ids": [], "values": ["0.1"], "scale_id": 5}]


class Sahte(g.Kilitli):
    def __init__(self, title):
        self.remaining, self.calls, self.kayit = "5000", 0, []
        self.L = {"state": "draft", "title": title}
        self.ru, self.props = None, {}
        self.bozuk_ru = self.aktif_et = self.bicim_boz = self.sayi_don = self.prop_400 = False

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and data != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
            ec.ru_yazim_kapisi(method, path, data, json_body)
            ec.ai_beyan_kapisi(method, path, data, json_body, params, canli_ceviri=lambda: None, baslik=self.L["title"])
            ec.metin_yasak_kapisi(method, path, data, json_body, params)
        self.kayit.append((method, path, data)); self.calls += 1
        if method == "GET":
            if path.endswith("/translations/ru"):
                if self.ru is None:
                    if ok404:
                        return None
                    raise SystemExit("404")
                return dict(self.ru)
            if path.endswith("/properties"):
                return {"results": [dict(property_id=k, scale_id=v[0], values=([float(x) for x in v[1]] if self.sayi_don else v[1]))
                                    for k, v in self.props.items()]}
            if path == f"/listings/{LID}":
                return dict(self.L)
            return {}
        if path.endswith("/translations/ru"):
            if method == "PUT" and self.ru is None:
                raise SystemExit("Etsy 404 (PUT, ceviri yok)")
            if method == "POST" and self.ru is not None:
                raise SystemExit("Etsy 409 (POST, ceviri var)")
            ds = data["description"]
            if self.bozuk_ru:
                ds = "x"
            elif self.bicim_boz:
                ds = " ".join(ds.split())
            self.ru = {"title": data["title"], "description": ds}
            if self.aktif_et:
                self.L["state"] = "active"
            return self.ru
        if method == "PUT" and "/properties/" in path:
            if self.prop_400:
                raise SystemExit("Etsy 400 properties")
            self.props[int(path.rsplit("/", 1)[1])] = (data.get("scale_id"), data["values"].split(","))
            return {}
        if method == "PATCH":
            self.L["state"] = "inactive"; return self.L
        raise SystemExit(f"taklit edilmeyen {method} {path}")


class SahteOku(g.SaltOkur):
    def __init__(self):
        self.remaining = "5000"


def bekle_dur(fn, metin):
    try:
        fn()
    except SystemExit as e:
        assert metin in str(e.code), (metin, e.code)
        return e
    raise AssertionError(f"DUR bekleniyordu: {metin}")


def yazlar(a, yol):
    return [k for k in a.kayit if k[0] == yol and k[1].endswith("/translations/ru")]


def main():
    g.time.sleep = lambda s: None
    RU = g.ru_metin()
    Y = {"CANCER_LIBRA": {"listing_id": LID}}
    title = g.en_baslik("CANCER_LIBRA")
    S = "39729443"
    n = 0
    with tempfile.TemporaryDirectory() as t:
        o = Path(t)
        # 1 PASS: RU yok -> POST, olcu 2 nitelik, PATCH yok
        a = Sahte(title); R = g.yaz(a, S, o, "CANCER_LIBRA", Y, RU, OLCU)
        assert all(R["kontrol"].values()) and R["ru_yol"] == "POST" and len(yazlar(a, "POST")) == 1 and not yazlar(a, "PUT")
        assert a.props[111] == (5, ["2.99"]) and a.props[222] == (5, ["0.1"]) and not [k for k in a.kayit if k[0] == "PATCH"]
        assert a.ru["title"] == RU["CANCER_LIBRA"]["baslik_ru"] and R["properties_ham"]; n += 1
        # 2 zaten var: RU yazmasi yok
        g.yaz(a, S, o, "CANCER_LIBRA", Y, RU, OLCU)
        assert len(yazlar(a, "POST")) == 1 and not yazlar(a, "PUT"); n += 1
        # 3 RU var ama farkli -> PUT
        b = Sahte(title); b.ru = {"title": "eski", "description": "eski"}
        R = g.yaz(b, S, o, "CANCER_LIBRA", Y, RU, OLCU)
        assert R["ru_yol"] == "PUT" and len(yazlar(b, "PUT")) == 1 and not yazlar(b, "POST"); n += 1
        # 4 izin disi
        c = Sahte(title); c.lid, c.pid_izin = LID, frozenset({111})
        bekle_dur(lambda: c._izin("PUT", f"/shops/1/listings/{LID}/properties/333"), "YASAK")
        bekle_dur(lambda: c._izin("PUT", f"/shops/1/listings/{LID}/translations/de"), "YASAK")
        bekle_dur(lambda: c._izin("POST", f"/shops/1/listings/{LID}/images"), "YASAK")
        bekle_dur(lambda: c._izin("POST", f"/shops/1/listings/999/translations/ru"), "YASAK")
        bekle_dur(lambda: c._call("PATCH", f"/shops/1/listings/{LID}", data={"title": "x"}), "YASAK"); n += 1
        # 5 baslangicta active: yazim yok
        d = Sahte(title); d.L["state"] = "active"
        bekle_dur(lambda: g.yaz(d, S, o, "CANCER_LIBRA", Y, RU, OLCU), "dokunulmadi")
        assert not [k for k in d.kayit if k[0] != "GET"]; n += 1
        # 6 RU yazimi taslagi yayina alirsa: ACIL inactive, exit 2
        e0 = Sahte(title); e0.aktif_et = True
        e = bekle_dur(lambda: g.yaz(e0, S, o, "CANCER_LIBRA", Y, RU, OLCU), "")
        assert e.code == 2 and e0.L["state"] == "inactive"; n += 1
        # 7 baslik kimligi
        bekle_dur(lambda: g.yaz(Sahte("baska"), S, o, "CANCER_LIBRA", Y, RU, OLCU), "kimlik"); n += 1
        # 8 geri okuma farkli
        h = Sahte(title); h.bozuk_ru = True
        bekle_dur(lambda: g.yaz(h, S, o, "CANCER_LIBRA", Y, RU, OLCU), "RU geri okuma"); n += 1
        # 9 bicim kaybi (satir sonlari silinmis): FAIL bicim
        i = Sahte(title); i.bicim_boz = True
        bekle_dur(lambda: g.yaz(i, S, o, "CANCER_LIBRA", Y, RU, OLCU), "bicim"); n += 1
        # 10 Etsy sayisal deger donerse (2.99 float) PASS
        j = Sahte(title); j.sayi_don = True
        assert all(g.yaz(j, S, o, "CANCER_LIBRA", Y, RU, OLCU)["kontrol"].values()); n += 1
        # 11 olcu farkli deger -> olcu FAIL
        assert not g.olcu_esit([{"property_id": 111, "scale_id": 5, "values": ["2.9"]}, {"property_id": 222, "scale_id": 5, "values": ["0.1"]}], OLCU)
        assert not g.olcu_esit([{"property_id": 111, "scale_id": 7, "values": ["2.99"]}, {"property_id": 222, "scale_id": 5, "values": ["0.1"]}], OLCU)
        assert not g.olcu_esit([{"property_id": 111, "scale_id": 5, "values": ["2.99 in"]}, {"property_id": 222, "scale_id": 5, "values": ["0.1"]}], OLCU)
        assert not g.olcu_esit([], OLCU); n += 1
        # 12 properties 4xx: DUR, RU yazilmis kalir; tekrar kosu RU'yu 'zaten var' gecer
        k = Sahte(title); k.prop_400 = True
        bekle_dur(lambda: g.yaz(k, S, o, "CANCER_LIBRA", Y, RU, OLCU), "400")
        assert g.ru_esit(k.ru, RU["CANCER_LIBRA"]) == "tam"
        k.prop_400 = False; R = g.yaz(k, S, o, "CANCER_LIBRA", Y, RU, OLCU)
        assert R["ru"] == "zaten var" and all(R["kontrol"].values()) and len(yazlar(k, "POST")) == 1; n += 1
        # 13 OLCU_JSON yok / sha / bos
        bekle_dur(lambda: g.olcu_yukle(None), "OLCU_JSON yok")
        bekle_dur(lambda: g.olcu_yukle(str(o / "yok.json")), "OLCU_JSON yok")
        (o / "x.json").write_text("[]")
        bekle_dur(lambda: g.olcu_yukle(str(o / "x.json")), "sha256")
        asil = g.OLCU_SHA; g.OLCU_SHA = __import__("hashlib").sha256(b"[]").hexdigest()
        bekle_dur(lambda: g.olcu_yukle(str(o / "x.json")), "bos"); g.OLCU_SHA = asil
        gercek = g.olcu_yukle(str(g.KOK / "docs" / "ornament" / "ORN_OLCU.json"))
        assert [(x["property_id"], x["values"], x["scale_id"]) for x in gercek] == [
            (47626759898, ["2.99"], 5), (47626759834, ["2.99"], 5), (54142602037, ["0.1"], 5)]; n += 1
        # 14 pilot dogrulama: once yok, yazimdan sonra var
        p = Sahte(title)
        assert not g.pilot_dogru(p, S, Y, RU, OLCU)[0]
        g.yaz(p, S, o, "CANCER_LIBRA", Y, RU, OLCU)
        assert g.pilot_dogru(p, S, Y, RU, OLCU)[0]
        p.L["state"] = "active"; assert not g.pilot_dogru(p, S, Y, RU, OLCU)[0]; n += 1
        # 15 salt okuma yazamaz
        so = SahteOku()
        bekle_dur(lambda: so._call("PUT", f"/shops/1/listings/{LID}/translations/ru", data={}), "salt okuma")
        bekle_dur(lambda: so._call("POST", f"/shops/1/listings/{LID}/translations/ru", data={}), "salt okuma"); n += 1
        # 16 78 RU satiri etsy_common kapilarindan gecer (sahte POST)
        for kod, r in RU.items():
            for yol in ("POST", "PUT"):
                d_ = {"title": r["baslik_ru"], "description": r["aciklama_ru"]}
                ec.ru_yazim_kapisi(yol, f"/shops/1/listings/{LID}/translations/ru", d_, None)
                ec.ai_beyan_kapisi(yol, f"/shops/1/listings/{LID}/translations/ru", d_, None, None, canli_ceviri=lambda: None, baslik="x")
                ec.metin_yasak_kapisi(yol, f"/shops/1/listings/{LID}/translations/ru", d_, None, None)
        n += 1
        # 17 RU sha
        asil = g.RU_SHA; g.RU_SHA = "0" * 64
        bekle_dur(g.ru_metin, "sha256"); g.RU_SHA = asil; n += 1
    print(f"test_ornament_ru_olcu: {n}/17 PASS")
    assert n == 17


if __name__ == "__main__":
    main()
