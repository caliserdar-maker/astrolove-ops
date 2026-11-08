#!/usr/bin/env python3
"""YAYINA HAZIR KONTROLU (SALT OKUMA; Serdar 8 Kas sistem onerisi 2, "hepsi"). Etsy'ye yazma YOK.
Urun ayar dosyasindaki (SPEC, ornek docs/ornament/ORN_YAYIN_SPEC.json) beklenen degerlerle ilanlari karsilastirir;
Serdar'a linkli liste uretir: YAYINDA / YAYINA HAZIR / HENUZ YAYINLAMAYIN (neden).
Etsy: GET /shops/{shop} (kota) + GET /listings/batch?includes=Images,Videos,Translations (100'luk parca basina 1 cagri);
SPEC'te nitelik varsa ilan basina GET .../properties (1 cagri / ilan; --nitelik-yok ile kapatilirsa sonuc "olculemedi").
mod=olc    : yalniz ilk 2 ilan; batch yanitinda hangi alanlarin geldigini yazar (alan adi + tur; ic ice images[0],
             videos[0], production_partners[0], translations) + properties ucunun alanlari -> OLCUM.json. Deger yazilmaz
             (state ve ortak adi haric).
mod=kontrol: tum ilanlar -> YAYINA_HAZIR.json + YAYINA_HAZIR.md (her ilandan sonra ara JSON; DUR'da yarim cikti kalir).
Kontroller (SPEC'te tanimli olanlar): state, shipping_profile_id, uretim ortagi (ad; SPEC'te id varsa id de), fiyat,
gorsel sayisi + rank tekrarsiz ve artan + rank sirasiyla alt metinlerin TAMAMI (SPEC alt_metin_kaynagi; yoksa yalniz
2. gorsel alt metni), video sayisi, aciklamada zorunlu ve yasak ifadeler, RU baslik ve aciklama (CSV ile tam; CSV'de
kod yoksa FAIL), nitelik degerleri. Bir alan yanitta YOKSA sonuc "olculemedi" (PASS sayilmaz).
Kontrol EDILMEYENLER SPEC "kontrol_edilmeyen" listesinden rapor basligina yazilir.
"""
import argparse
import csv
import hashlib
import html
import importlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10
LINK = "https://www.etsy.com/your/shops/me/listing-editor/edit/{}"
SINIF_SIRA = ("YAYINA HAZIR", "HENUZ YAYINLAMAYIN", "YAYINDA (EKSIK VAR)", "YAYINDA")


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


def norm(t):
    """ornament_galeri9 geri okumasiyla ayni: html cozulur, bosluklar tek."""
    return " ".join(html.unescape(str(t or "")).split())


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


def alt_kaynak(spec):
    """SPEC alt_metin_kaynagi 'modul:fonksiyon' -> f(kod) = (alt listesi, baslik, hata listesi). Yoksa None."""
    k = spec.get("alt_metin_kaynagi")
    if not k:
        return None
    m, f = k.split(":")
    return getattr(importlib.import_module(m), f)


def alan_turleri(d, on="", derin=0):
    """Alan adi -> tur. dict'ler ve listelerin ilk ogesi 2 seviyeye kadar acilir (deger yazilmaz)."""
    out = {}
    if isinstance(d, list):
        out[on.rstrip(".") or "_"] = f"list[{len(d)}]"
        if d and derin < 3:
            out.update(alan_turleri(d[0], on.rstrip(".") + "[0].", derin + 1))
        return out
    if not isinstance(d, dict):
        out[on.rstrip(".") or "_"] = type(d).__name__
        return out
    for k, v in d.items():
        if isinstance(v, (dict, list)) and derin < 2:
            out.update(alan_turleri(v, f"{on}{k}.", derin + 1))
        else:
            out[on + k] = type(v).__name__ if not isinstance(v, list) else f"list[{len(v)}]"
    return out


def batch(api, ids, includes):
    res = []
    for i in range(0, len(ids), 100):
        r = api.get("/listings/batch", params={"listing_ids": ",".join(str(x) for x in ids[i:i + 100]), "includes": includes}) or {}
        res += r.get("results") or []
    return {int(x["listing_id"]): x for x in res if str(x.get("listing_id", "")).isdigit()}


def ru_bul(L):
    """includes=Translations yaniti. Emsal beyan_marka_yaz.ru_ceviri: batch'te dict {dil: ceviri}; liste de kabul.
    -> None (alan yok) | {} (RU yok) | RU kaydi."""
    t = L.get("translations")
    if t is None:
        return None
    if isinstance(t, dict):
        if isinstance(t.get("ru"), dict):
            return t["ru"]
        t = list(t.values())
    for x in t or []:
        if isinstance(x, dict) and str(x.get("language", "")).lower().startswith("ru"):
            return x
    return {}


def gorsel_kontrol(b, ims, alt_beklenen):
    ims = sorted(ims, key=lambda x: (x.get("rank") is None, x.get("rank") or 0))
    r = [x.get("rank") for x in ims]
    if None in r or len(set(r)) != len(r):
        return f"FAIL: rank eksik ya da tekrarli {r}"
    if len(ims) != b["gorsel_sayisi"]:
        return f"FAIL: {len(ims)} gorsel (beklenen {b['gorsel_sayisi']}), rank {r}"
    gelen = [norm(x.get("alt_text")) for x in ims]
    if alt_beklenen is not None:
        bek = [norm(a) for a in alt_beklenen]
        if len(bek) != len(gelen):
            return f"olculemedi: beklenen alt metin sayisi {len(bek)}"
        fark = [i + 1 for i, (g, e) in enumerate(zip(gelen, bek)) if g != e]
        return "PASS" if not fark else f"FAIL: alt metin / sira farkli, sira {fark} (rank {r})"
    k2 = b.get("gorsel2_alt_icerir")
    if k2 and (len(gelen) < 2 or k2.lower() not in gelen[1].lower()):
        return f"FAIL: 2. gorsel alt metni '{k2}' icermiyor"
    return "PASS"


def kontrol_et(spec, kod, L, ru_harita, props=None, alt_f=None):
    """ru_harita: None = RU kontrolu yok; dict = {kod: CSV satiri}. props: None = nitelik okunmadi.
    -> sonuclar dict ad -> 'PASS' | 'FAIL: ...' | 'olculemedi: ...'"""
    S = {}
    b = spec.get("beklenen", {})
    if "shipping_profile_id" in b:
        v = L.get("shipping_profile_id")
        S["kargo profili"] = "olculemedi: alan yok" if v is None else ("PASS" if int(v) == int(b["shipping_profile_id"]) else f"FAIL: {v}")
    if "uretim_ortagi" in b:
        if "production_partners" not in L:
            S["uretim ortagi"] = "olculemedi: alan yok"
        else:
            pp = L.get("production_partners") or []
            adlar = sorted(str(p.get("partner_name")) for p in pp)
            ok = adlar == [b["uretim_ortagi"]]
            if ok and b.get("uretim_ortagi_id") is not None:
                ok = [str(p.get("production_partner_id")) for p in pp] == [str(b["uretim_ortagi_id"])]
            S["uretim ortagi"] = "PASS" if ok else f"FAIL: {[(p.get('production_partner_id'), p.get('partner_name')) for p in pp]}"
    if "fiyat" in b:
        v = fiyat(L.get("price"))
        S["fiyat"] = "olculemedi: alan yok" if v is None else ("PASS" if abs(v - float(b["fiyat"])) < 0.005 else f"FAIL: {v}")
    if "gorsel_sayisi" in b:
        ims = L.get("images")
        if ims is None:
            S["gorsel"] = "olculemedi: alan yok"
        else:
            alt_bek = None
            if alt_f is not None:
                try:
                    alt_bek, _, hata = alt_f(kod)
                except (Exception, SystemExit) as e:  # noqa: BLE001 (kaynak DUR/hata -> olculemedi, PASS degil; Etsy istegi yok)
                    alt_bek, hata = None, [f"{type(e).__name__}: {e}"]
                if hata:
                    S["gorsel"] = f"olculemedi: beklenen alt metin uretilemedi {hata}"
            if "gorsel" not in S:
                S["gorsel"] = gorsel_kontrol(b, ims, alt_bek)
    if "video_sayisi" in b:
        vs = L.get("videos")
        S["video"] = "olculemedi: alan yok" if vs is None else ("PASS" if len(vs) == b["video_sayisi"] else f"FAIL: {len(vs)}")
    if b.get("aciklama_zorunlu") or b.get("aciklama_yasak"):
        if "description" not in L:
            S["aciklama"] = "olculemedi: alan yok"
        else:
            d = norm(L.get("description"))
            for z in b.get("aciklama_zorunlu", []):
                S[f"aciklama zorunlu: {z[:30]}"] = "PASS" if norm(z) in d else "FAIL: yok"
            for y in b.get("aciklama_yasak", []):
                S[f"aciklama yasak: {y}"] = "PASS" if y.lower() not in d.lower() else "FAIL: var"
    if ru_harita is not None:
        bek = ru_harita.get(kod)
        ru = ru_bul(L)
        if bek is None:
            S["RU"] = "FAIL: RU CSV'de kod yok"
        elif ru is None:
            S["RU"] = "olculemedi: translations alani yok"
        else:
            ok = tam(ru.get("title")) == tam(bek["baslik_ru"]) and tam(ru.get("description")) == tam(bek["aciklama_ru"])
            S["RU"] = "PASS" if ok else ("FAIL: RU yok" if not tam(ru.get("title")) else "FAIL: RU farkli")
    if b.get("nitelikler"):
        if props is None:
            S["nitelik"] = "olculemedi: nitelik okunmadi"
        else:
            have = {int(p.get("property_id")): p for p in props if str(p.get("property_id", "")).isdigit()}
            for o in b["nitelikler"]:
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


def sayim(R):
    say = {}
    for x in R["ilanlar"].values():
        say[x["sinif"]] = say.get(x["sinif"], 0) + 1
    return say


def md(R, spec):
    g = {}
    for kod, x in sorted(R["ilanlar"].items()):
        g.setdefault(x["sinif"], []).append((kod, x))
    say = sayim(R)
    out = [f"# Yayına hazır kontrolü: {spec.get('urun')} ({R['zaman']})", "",
           f"SPEC sha {spec['_sha'][:12]}; kota {R.get('kota_bas')} -> {R.get('kota_son')}; çağrı {R.get('cagri')} (bizim veri, salt okuma).",
           f"Toplam {len(R['ilanlar'])}: " + ", ".join(f"{k} {v}" for k, v in sorted(say.items())) + ".",
           "Kontrol EDİLMEYEN: " + (", ".join(spec.get("kontrol_edilmeyen") or []) or "yok") + "."]
    if R.get("yarim"):
        out.append(f"YARIM ÇIKTI: {R['yarim']}")
    out.append("")
    for s in SINIF_SIRA:
        if s in g:
            out.append(f"## {s}: {len(g[s])}")
            for kod, x in g[s]:
                ek = "" if not x["eksik"] else " | " + "; ".join(f"{k}: {v}" for k, v in x["eksik"].items())
                out.append(f"- [{kod}]({LINK.format(x['listing_id'])}){ek}")
            out.append("")
    for s, v in sorted(g.items()):
        if s not in SINIF_SIRA:
            out.append(f"## {s}: {len(v)}")
            out += [f"- {kod} {x['listing_id']} | " + "; ".join(f"{k}: {w}" for k, w in x["eksik"].items()) for kod, x in v] + [""]
    return "\n".join(out)


def ilan_listesi(Y):
    """-> (ids {kod: lid}, okunamayan {kod: neden}). listing_id'siz kayit sessizce atlanmaz."""
    ids, kotu = {}, {}
    for k, v in Y.items():
        if isinstance(v, dict) and str(v.get("listing_id", "")).isdigit():
            ids[k] = int(v["listing_id"])
        else:
            kotu[k] = f"listing id yok ({(v or {}).get('hata') if isinstance(v, dict) else type(v).__name__})"
    return ids, kotu


def yaz(out, R, spec):
    json.dump(R, open(out / "YAYINA_HAZIR.json", "w"), indent=1, ensure_ascii=False)
    m = md(R, spec)
    open(out / "YAYINA_HAZIR.md", "w").write(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["olc", "kontrol"], required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--ilanlar", required=True, help="JSON: {KOD: {listing_id: ...}} (ornament YEDEK9.json)")
    ap.add_argument("--nitelik-yok", action="store_true", help="nitelik okunmaz; SPEC'te nitelik varsa sonuc 'olculemedi'")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    spec = spec_yukle(a.spec)
    Y = json.load(open(a.ilanlar))
    ids, okunamayan = ilan_listesi(Y)
    if not ids:
        raise SystemExit("DUR: ilan listesi bos")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    RU = ru_csv(spec) if a.mod == "kontrol" else None
    alt_f = alt_kaynak(spec) if a.mod == "kontrol" else None
    nitelik = bool(spec.get("beklenen", {}).get("nitelikler")) and not a.nitelik_yok
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
        tahmin = 1 + len(sec)
    else:
        sec = sorted(ids.items())
        tahmin = (len(sec) + 99) // 100 + (len(sec) if nitelik else 0)
    if str(kota_bas).isdigit() and int(kota_bas) < tahmin + KOTA_MIN:
        raise SystemExit(f"DUR: kota {kota_bas} < tahmini istek {tahmin} + {KOTA_MIN} (okuma baslamadi)")
    print(f"ilan {len(sec)} | okunamayan {len(okunamayan)} | nitelik {nitelik} | tahmini istek {tahmin} | kota {kota_bas}", flush=True)
    if a.mod == "olc":
        B = batch(api, [v for _, v in sec], "Images,Videos,Translations"); cagri += 1
        O = {}
        for kod, v in sec:
            L = B.get(v) or {}
            props = (api.get(f"/shops/{shop}/listings/{v}/properties") or {}).get("results") or []; cagri += 1
            O[kod] = {"batch_alanlar": alan_turleri(L), "properties_alanlar": alan_turleri(props),
                      "_ornek": {"state": L.get("state"), "translations_tur": type(L.get("translations")).__name__,
                                 "translations_anahtar": sorted(L["translations"]) if isinstance(L.get("translations"), dict) else None,
                                 "ru_var": ru_bul(L) not in (None, {}),
                                 "production_partners": [(p.get("production_partner_id"), p.get("partner_name"))
                                                         for p in L.get("production_partners") or []],
                                 "shipping_profile_id_var": L.get("shipping_profile_id") is not None,
                                 "gorsel_rank": [x.get("rank") for x in L.get("images") or []],
                                 "nitelik_id": [p.get("property_id") for p in props]}}
        O["_kota"] = [kota_bas, api.remaining]; O["_cagri"] = cagri
        json.dump(O, open(out / "OLCUM.json", "w"), indent=1, ensure_ascii=False)
        print(json.dumps(O, ensure_ascii=False)[:6000])
        return
    R = {"ilanlar": {}, "zaman": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "kota_bas": kota_bas, "spec_sha": spec["_sha"]}
    for kod, neden in okunamayan.items():
        R["ilanlar"][kod] = {"listing_id": None, "sinif": "DURUM okunamadi", "eksik": {"okuma": neden}}
    t0 = time.time()
    try:
        B = batch(api, [v for _, v in sec], "Images,Videos,Translations"); cagri += (len(sec) + 99) // 100
        for n, (kod, lid) in enumerate(sec, 1):
            L = B.get(lid)
            if L is None:
                R["ilanlar"][kod] = {"listing_id": lid, "sinif": "DURUM okunamadi", "eksik": {"okuma": "batch yanitinda yok"}}
                continue
            props = None
            if nitelik and L.get("state") in ("draft", "active"):
                props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []; cagri += 1
            S = kontrol_et(spec, kod, L, RU, props, alt_f)
            sinif, kotu = siniflandir(L, S)
            R["ilanlar"][kod] = {"listing_id": lid, "state": L.get("state"), "sinif": sinif, "eksik": kotu, "sonuc": S}
            g = time.time() - t0
            print(f"[{n}/{len(sec)}] {kod} {sinif} | gecen {g:.0f} sn | kalan ~{g / n * (len(sec) - n):.0f} sn | %{100 * n // len(sec)} | "
                  f"kota {api.remaining}", flush=True)
            if n % 10 == 0:
                R.update(kota_son=api.remaining, cagri=cagri)
                yaz(out, R, spec)
    except SystemExit as e:
        R.update(kota_son=api.remaining, cagri=cagri, yarim=str(e.code)[:300])
        yaz(out, R, spec)
        raise
    R.update(kota_son=api.remaining, cagri=cagri)
    m = yaz(out, R, spec)
    print(f"::notice::yayina_hazir {spec.get('urun')} | {sayim(R)} | cagri {cagri} | kota {kota_bas} -> {api.remaining}")
    print(m[:6000])


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
