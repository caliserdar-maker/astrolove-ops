#!/usr/bin/env python3
"""YAYINA HAZIR KONTROLU (SALT OKUMA; Serdar 8 Kas sistem onerisi 2, "hepsi"). Etsy'ye yazma YOK.
Urun ayar dosyasindaki (SPEC, ornek docs/ornament/ORN_YAYIN_SPEC.json) beklenen degerlerle ilanlari karsilastirir;
Serdar'a linkli liste uretir: YAYINDA / YAYINA HAZIR / HENUZ YAYINLAMAYIN (neden).
Etsy: GET /shops/{shop} (kota) + GET /listings/batch?includes=Images,Videos,Translations (100'luk parca basina 1 cagri);
--nitelik verilirse ilan basina GET .../properties (1 cagri / ilan).
mod=olc   : yalniz ilk 2 ilan; batch yanitinda hangi alanlarin geldigini yazar (deger degil, alan adi + tur) -> OLCUM.json.
mod=kontrol: tum ilanlar -> YAYINA_HAZIR.json + YAYINA_HAZIR.md.
Kontroller (SPEC'te tanimli olanlar): state, shipping_profile_id, uretim ortagi adi, fiyat, gorsel sayisi, video sayisi,
2. gorselin alt metni (anahtar ifade), aciklamada zorunlu ve yasak ifadeler, RU baslik ve aciklama (CSV ile tam), nitelik degerleri.
Bir alan yanitta YOKSA sonuc "olculemedi" (PASS sayilmaz).
"""
import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10
LINK = "https://www.etsy.com/your/shops/me/listing-editor/edit/{}"


class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r


def tam(t):
    return html.unescape(str(t or "")).replace("\r\n", "\n").strip()


def sayi(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def fiyat(p):
    if isinstance(p, dict) and p.get("amount") is not None and p.get("divisor"):
        return round(p["amount"] / p["divisor"], 2)
    return sayi(p)


def spec_yukle(yol):
    b = open(yol, "rb").read()
    s = json.loads(b)
    s["_sha"] = hashlib.sha256(b).hexdigest()
    return s


def ru_csv(spec):
    r = spec.get("ru")
    if not r:
        return None
    b = open(KOK / r["csv"], "rb").read()
    if hashlib.sha256(b).hexdigest() != r["sha256"]:
        raise SystemExit("DUR: RU CSV sha256 SPEC ile ayni degil")
    return {x[r.get("anahtar", "kod")]: x for x in csv.DictReader(open(KOK / r["csv"], encoding="utf-8"))}


def alan_turleri(d, on=""):
    out = {}
    for k, v in (d or {}).items():
        t = type(v).__name__
        out[on + k] = t if not isinstance(v, list) else f"list[{len(v)}]"
        if isinstance(v, dict) and k in ("price", "translations"):
            out.update(alan_turleri(v, on + k + "."))
    return out


def batch(api, ids, includes):
    res = []
    for i in range(0, len(ids), 100):
        r = api.get("/listings/batch", params={"listing_ids": ",".join(str(x) for x in ids[i:i + 100]), "includes": includes}) or {}
        res += r.get("results") or []
    return {int(x["listing_id"]): x for x in res if str(x.get("listing_id", "")).isdigit()}


def ru_bul(L):
    """includes=Translations yaniti: 'translations' liste ya da dict olabilir (olcum modunda gorulur)."""
    t = L.get("translations")
    if t is None:
        return None
    if isinstance(t, dict):
        return t.get("ru") or {}
    for x in t:
        if str(x.get("language", "")).lower().startswith("ru"):
            return x
    return {}


def kontrol_et(spec, kod, L, ru_beklenen, props=None):
    """-> (sonuclar dict ad -> 'PASS' | 'FAIL: ...' | 'olculemedi: ...')"""
    S = {}
    b = spec.get("beklenen", {})
    if "shipping_profile_id" in b:
        v = L.get("shipping_profile_id")
        S["kargo profili"] = "olculemedi: alan yok" if v is None else ("PASS" if int(v) == int(b["shipping_profile_id"]) else f"FAIL: {v}")
    if "uretim_ortagi" in b:
        if "production_partners" not in L:
            S["uretim ortagi"] = "olculemedi: alan yok"
        else:
            adlar = sorted(str(p.get("partner_name")) for p in L.get("production_partners") or [])
            S["uretim ortagi"] = "PASS" if adlar == [b["uretim_ortagi"]] else f"FAIL: {adlar}"
    if "fiyat" in b:
        v = fiyat(L.get("price"))
        S["fiyat"] = "olculemedi: alan yok" if v is None else ("PASS" if abs(v - float(b["fiyat"])) < 0.005 else f"FAIL: {v}")
    if "gorsel_sayisi" in b:
        ims = L.get("images")
        if ims is None:
            S["gorsel"] = "olculemedi: alan yok"
        else:
            ims = sorted(ims, key=lambda x: x.get("rank") or 0)
            r = [x.get("rank") for x in ims]
            ok = len(ims) == b["gorsel_sayisi"] and len(set(r)) == len(r) and r == sorted(r)
            k2 = b.get("gorsel2_alt_icerir")
            if ok and k2:
                ok = len(ims) > 1 and k2.lower() in str(ims[1].get("alt_text") or "").lower()
            S["gorsel"] = "PASS" if ok else f"FAIL: {len(ims)} gorsel, rank {r}"
    if "video_sayisi" in b:
        vs = L.get("videos")
        S["video"] = "olculemedi: alan yok" if vs is None else ("PASS" if len(vs) == b["video_sayisi"] else f"FAIL: {len(vs)}")
    d = tam(L.get("description"))
    for z in b.get("aciklama_zorunlu", []):
        S[f"aciklama zorunlu: {z[:30]}"] = "PASS" if tam(z) in d else "FAIL: yok"
    for y in b.get("aciklama_yasak", []):
        S[f"aciklama yasak: {y}"] = "PASS" if y.lower() not in d.lower() else "FAIL: var"
    if ru_beklenen is not None:
        ru = ru_bul(L)
        if ru is None:
            S["RU"] = "olculemedi: translations alani yok"
        else:
            ok = tam(ru.get("title")) == tam(ru_beklenen["baslik_ru"]) and tam(ru.get("description")) == tam(ru_beklenen["aciklama_ru"])
            S["RU"] = "PASS" if ok else ("FAIL: RU yok" if not tam(ru.get("title")) else "FAIL: RU farkli")
    if props is not None:
        have = {int(p.get("property_id")): p for p in props if str(p.get("property_id", "")).isdigit()}
        for o in b.get("nitelikler", []):
            p = have.get(int(o["property_id"]))
            if p is None:
                S[f"nitelik {o['ad']}"] = "FAIL: yok"
                continue
            a = [sayi(v) for v in p.get("values") or []]
            e = [sayi(v) for v in o["values"]]
            ok = None not in a and len(a) == len(e) and all(abs(x - y) < 1e-6 for x, y in zip(a, e)) and p.get("scale_id") == o.get("scale_id")
            S[f"nitelik {o['ad']}"] = "PASS" if ok else f"FAIL: {p.get('values')} scale {p.get('scale_id')}"
    return S


def siniflandir(L, S):
    st = L.get("state")
    kotu = {k: v for k, v in S.items() if v != "PASS"}
    if st == "active":
        return ("YAYINDA" if not kotu else "YAYINDA (EKSIK VAR)"), kotu
    if st != "draft":
        return f"DURUM {st}", kotu
    return ("YAYINA HAZIR" if not kotu else "HENUZ YAYINLAMAYIN"), kotu


def md(R, spec):
    g = {}
    for kod, x in sorted(R["ilanlar"].items()):
        g.setdefault(x["sinif"], []).append((kod, x))
    out = [f"# Yayına hazır kontrolü: {spec.get('urun')} ({R['zaman']})", "",
           f"SPEC sha {spec['_sha'][:12]}; kota {R['kota_bas']} -> {R['kota_son']}; çağrı {R['cagri']} (bizim veri, salt okuma).", ""]
    for s in ("YAYINA HAZIR", "HENUZ YAYINLAMAYIN", "YAYINDA (EKSIK VAR)", "YAYINDA"):
        if s in g:
            out.append(f"## {s}: {len(g[s])}")
            for kod, x in g[s]:
                ek = "" if not x["eksik"] else " | " + "; ".join(f"{k}: {v}" for k, v in x["eksik"].items())
                out.append(f"- [{kod}]({LINK.format(x['listing_id'])}){ek}")
            out.append("")
    for s, v in g.items():
        if s.startswith("DURUM"):
            out.append(f"## {s}: {len(v)}")
            out += [f"- {kod} {x['listing_id']}" for kod, x in v] + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["olc", "kontrol"], required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--ilanlar", required=True, help="JSON: {KOD: {listing_id: ...}} (ornament YEDEK9.json)")
    ap.add_argument("--nitelik", action="store_true")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    spec = spec_yukle(a.spec)
    Y = json.load(open(a.ilanlar))
    ids = {k: int(v["listing_id"]) for k, v in Y.items() if isinstance(v, dict) and str(v.get("listing_id", "")).isdigit()}
    if not ids:
        raise SystemExit("DUR: ilan listesi bos")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = SaltOkur(store)
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    api.get(f"/shops/{shop}")
    kota_bas, cagri = api.remaining, 1
    if a.mod == "olc":
        sec = sorted(ids.items())[:2]
        B = batch(api, [v for _, v in sec], "Images,Videos,Translations"); cagri += 1
        O = {kod: alan_turleri(B.get(v) or {}) for kod, v in sec}
        for kod, v in sec:
            L = B.get(v) or {}
            O[kod]["_ornek"] = {"state": L.get("state"), "translations_tur": type(L.get("translations")).__name__,
                                "ru_var": ru_bul(L) not in (None, {}), "production_partners_ad": [p.get("partner_name") for p in L.get("production_partners") or []],
                                "shipping_profile_id_var": L.get("shipping_profile_id") is not None}
        O["_kota"] = [kota_bas, api.remaining]
        json.dump(O, open(out / "OLCUM.json", "w"), indent=1, ensure_ascii=False)
        print(json.dumps(O, ensure_ascii=False)[:3000])
        return
    RU = ru_csv(spec)
    B = batch(api, list(ids.values()), "Images,Videos,Translations"); cagri += (len(ids) + 99) // 100
    R = {"ilanlar": {}, "zaman": __import__("time").strftime("%Y-%m-%d %H:%M UTC", __import__("time").gmtime())}
    for kod, lid in sorted(ids.items()):
        L = B.get(lid)
        if L is None:
            R["ilanlar"][kod] = {"listing_id": lid, "sinif": "DURUM okunamadi", "eksik": {"okuma": "batch yanitinda yok"}}
            continue
        props = None
        if a.nitelik and L.get("state") in ("draft", "active"):
            props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []; cagri += 1
        S = kontrol_et(spec, kod, L, (RU or {}).get(kod) if RU is not None else None, props)
        sinif, kotu = siniflandir(L, S)
        R["ilanlar"][kod] = {"listing_id": lid, "state": L.get("state"), "sinif": sinif, "eksik": kotu, "sonuc": S}
    R.update(kota_bas=kota_bas, kota_son=api.remaining, cagri=cagri)
    json.dump(R, open(out / "YAYINA_HAZIR.json", "w"), indent=1, ensure_ascii=False)
    m = md(R, spec)
    open(out / "YAYINA_HAZIR.md", "w").write(m)
    say = {}
    for x in R["ilanlar"].values():
        say[x["sinif"]] = say.get(x["sinif"], 0) + 1
    print(f"::notice::yayina_hazir {spec.get('urun')} | {say} | cagri {cagri} | kota {kota_bas} -> {api.remaining}")
    print(m[:6000])


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
