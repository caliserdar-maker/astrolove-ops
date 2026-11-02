#!/usr/bin/env python3
"""ornament_katalog.py ciktisini ham JSON ile tek tek karsilastirir. Rapor kodunu KULLANMAZ; her degeri ham'dan yeniden okur.
Kontroller: _istekler (yalniz GET + izinli POST); urun basina varyant sayisi; CSV her varyant satiri (v1 fiyat, 4 v2 fiyat,
printfile id/px/dpi/fill, 9 ulke kargo = ham en ucuz ya da HATA, cikis ulkesi, gonderim listesi); KARGO.csv her satir
(ucret, yontem, gun, tarih, para, en ucuz mu, cikis); MD tablo 1 (fiyat araligi, px, YALNIZ ABD) ve tablo 2 (her hucre).
Kullanim: ornament_dogrula.py <cikti_klasor>. Uyusmazlik varsa cikis 1."""
import csv
import json
import re
import sys
from pathlib import Path

IZINLI_POST = {"/shipping/rates", "/v2/shipping-rates"}
YOK = "API vermedi"


def L(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def D(x):
    return x if isinstance(x, dict) else {}


def main(c):
    ham = c / "ham"
    hata, say = [], [0]

    def j(ad):
        p = ham / ad
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def esit(ad, a, b):
        say[0] += 1
        if ("" if a is None else str(a)) != ("" if b is None else str(b)):
            hata.append(f"{ad}: rapor={a!r} ham={b!r}")

    for x in j("_istekler.json") or []:
        say[0] += 1
        if x["yontem"] != "GET" and not (x["yontem"] == "POST" and x["yol"].split("?")[0] in IZINLI_POST):
            hata.append(f"izinsiz istek {x['yontem']} {x['yol']}")

    K1 = {(str(x["urun"]), str(x["varyant"]), x["ulke"]): x for x in j("kargo_v1.json") or []}
    K2 = {(str(x["urun"]), str(x["varyant"]), x["ulke"]): x for x in j("kargo_v2.json") or []}
    KEYS = set(K1) | set(K2)
    ULKE = sorted({k[2] for k in KEYS}) or []

    def ucuz(x):
        if not x or x.get("http") != 200:
            return None
        r = [o for o in L(D(x.get("yanit")).get("result")) if o.get("rate") not in (None, "")]
        return min(r, key=lambda o: float(o["rate"])) if r else None

    def sec(key):
        """(en ucuz secenek v1 alan adlariyla ya da None, kullanilan ham kayit). v1 200 ve secenekli ise v1, degilse v2."""
        x1, x2 = K1.get(key), K2.get(key)
        e = ucuz(x1)
        if e:
            return e, x1
        if x2 and x2.get("http") == 200:
            r = [o for o in L(D(x2.get("yanit")).get("data")) if o.get("rate") not in (None, "")]
            if r:
                o = min(r, key=lambda o: float(o["rate"]))
                return {"id": o.get("shipping"), "name": o.get("shipping_method_name"), "rate": o.get("rate"),
                        "currency": o.get("currency"), "minDeliveryDays": o.get("min_delivery_days"),
                        "maxDeliveryDays": o.get("max_delivery_days"), "minDeliveryDate": o.get("min_delivery_date"),
                        "maxDeliveryDate": o.get("max_delivery_date")}, x2
        return None, (x1 or x2)

    def cikis(key, e):
        x2 = K2.get(key) or {}
        d = L(D(x2.get("yanit")).get("data"))
        m = next((o for o in d if e and o.get("shipping") == e.get("id")), None)
        if m is None and x2.get("http") == 200:
            r = [o for o in d if o.get("rate") not in (None, "")]
            m = min(r, key=lambda o: float(o["rate"])) if r else None
        return sorted({s.get("departure_country") for s in L((m or {}).get("shipments")) if s.get("departure_country")})

    def varyantlar(pid):
        v1 = L(D(D(j(f"urun_{pid}_v1.json").get("yanit")).get("result")).get("variants"))
        return ("v1", v1) if v1 else ("v2", L(D(j(f"urun_{pid}_v2_variants.json").get("yanit")).get("data")))

    def v2fiyat(pid, cur, vid):
        d = D(D(j(f"urun_{pid}_v2_prices_{cur}.json").get("yanit")).get("data"))
        v = next((x for x in L(d.get("variants")) if str(x.get("id")) == str(vid)), None)
        if v and cur.startswith("EUR") and d.get("currency") != "EUR":
            hata.append(f"{pid}/{vid} {cur}: currency={d.get('currency')}")
        return "; ".join(f"{t.get('technique_key')}:{t.get('price')}" for t in L((v or {}).get("techniques"))) or YOK

    rows = list(csv.DictReader(open(c / "PRINTFUL_ORNAMENT.csv", encoding="utf-8")))
    aday = j("_adaylar.json") or {}
    for pid in aday:
        esit(f"urun {pid} varyant sayisi", sum(1 for r in rows if r["urun_id"] == pid), len(varyantlar(pid)[1]))
    for r in rows:
        pid, vid = r["urun_id"], r["varyant_id"]
        kay, vs = varyantlar(pid)
        v = next((x for x in vs if str(x.get("id")) == vid), None)
        if v is None:
            hata.append(f"{pid}/{vid}: ham {kay} varyantlarinda yok")
            continue
        esit(f"{pid}/{vid} kaynak", r["varyant_kaynagi"], kay)
        esit(f"{pid}/{vid} ad", r["varyant_adi"], v.get("name"))
        esit(f"{pid}/{vid} size", r["sekil_boyut_api"], v.get("size") or YOK)
        if kay == "v1":
            esit(f"{pid}/{vid} fiyat_usd_v1", r["fiyat_usd_v1"], v.get("price"))
        else:
            say[0] += 1
            if not r["fiyat_usd_v1"].startswith(YOK):
                hata.append(f"{pid}/{vid} v1 fiyat olmamali: {r['fiyat_usd_v1']}")
        for cur, kol in (("USD", "fiyat_usd_v2"), ("EUR", "fiyat_eur_v2"), ("EUR_europe", "fiyat_eur_v2_europe"),
                         ("USD_north_america", "fiyat_usd_v2_north_america")):
            esit(f"{pid}/{vid} {kol}", r[kol], v2fiyat(pid, cur, vid))
        pf = D(D(j(f"urun_{pid}_printfiles.json").get("yanit")).get("result"))
        pid_ = {str(x.get("printfile_id")): x for x in L(pf.get("printfiles"))}
        yer = D(next((x.get("placements") for x in L(pf.get("variant_printfiles")) if str(x.get("variant_id")) == vid), {}))
        for kol, f in (("printfile_id", lambda y, i, x: i), ("printfile_px", lambda y, i, x: f"{x.get('width')}x{x.get('height')}"),
                       ("printfile_dpi", lambda y, i, x: x.get("dpi")), ("fill_mode", lambda y, i, x: x.get("fill_mode"))):
            esit(f"{pid}/{vid} {kol}", r[kol], "; ".join(f"{y}={f(y, i, pid_.get(str(i)) or {})}" for y, i in yer.items()) or YOK)
        var, dep = [], set()
        for u in ULKE:
            key = (pid, vid, u)
            if key not in KEYS:
                esit(f"{pid}/{vid} kargo {u}", r.get(f"kargo_{u}_usd"), "sorgulanmadi")
                continue
            e, x = sec(key)
            esit(f"{pid}/{vid} kargo {u}", r.get(f"kargo_{u}_usd"), e["rate"] if e else f"HATA {x['http']}")
            if e:
                var.append(u)
            dep.update(cikis(key, e))
        if any(k[0] == pid for k in KEYS):
            sira = [u for u in ("US CA GB DE FR IT ES NL AU".split()) if u in var]
            esit(f"{pid}/{vid} gonderim_var", r["gonderim_var_9ulke"], ", ".join(sira) or "yok")
            esit(f"{pid}/{vid} cikis", r["cikis_ulkesi_v2"], ", ".join(sorted(dep)) or YOK)

    krows = list(csv.DictReader(open(c / "PRINTFUL_ORNAMENT_KARGO.csv", encoding="utf-8")))
    esit("kargo satir sayisi", len(krows), len(KEYS))
    for r in krows:
        key = (r["urun_id"], r["varyant_id"], r["ulke"])
        if key not in KEYS:
            hata.append(f"kargo {key}: ham yok")
            continue
        e = sec(key)[0]
        esit(f"kargo {key} http", r["http_v1"], K1[key]["http"] if key in K1 else "sorgulanmadi")
        esit(f"kargo {key} kaynak", r["kargo_kaynagi"], ("v1" if ucuz(K1.get(key)) else "v2") if e else YOK)
        if e is None:
            esit(f"kargo {key} ucret", r["ucret"], YOK)
            continue
        for kol, al in (("ucret", "rate"), ("yontem_id", "id"), ("para", "currency"), ("min_gun", "minDeliveryDays"),
                        ("max_gun", "maxDeliveryDays"), ("min_tarih", "minDeliveryDate"), ("max_tarih", "maxDeliveryDate")):
            esit(f"kargo {key} {kol}", r[kol], e.get(al))
        esit(f"kargo {key} yontem_adi", r["yontem_adi"], (e.get("name") or "").strip())
        esit(f"kargo {key} para USD", r["para"], "USD")
        esit(f"kargo {key} cikis", r["cikis_ulkesi_v2"], ", ".join(cikis(key, e)) or YOK)
        d2 = L(D((K2.get(key) or {}).get("yanit")).get("data"))
        m2 = next((o for o in d2 if o.get("shipping") == e.get("id")), None)
        if m2 is None and (K2.get(key) or {}).get("http") == 200:
            r2 = [o for o in d2 if o.get("rate") not in (None, "")]
            m2 = min(r2, key=lambda o: float(o["rate"])) if r2 else None
        esit(f"kargo {key} ucret_v2", r["ucret_v2"], m2.get("rate") if m2 else YOK)
        if r["ucret_v2"] not in (YOK, "") and abs(float(r["ucret_v2"]) - float(r["ucret"])) > 0.005:
            hata.append(f"BILGI kargo {key}: v1 {r['ucret']} != v2 {r['ucret_v2']}")

    md = (c / "PRINTFUL_ORNAMENT.md").read_text(encoding="utf-8")
    t1 = md.split("## 1.")[1].split("## 2.")[0]
    for satir in t1.splitlines():
        m = re.match(r"\| (\d+) ", satir)
        if not m:
            continue
        pid = m.group(1)
        h = [x.strip() for x in satir.strip().strip("|").split("|")]
        kay, vs = varyantlar(pid)
        for etk, cur in (("WW", "USD"), ("NA", "USD_north_america")):
            f = sorted({float(p.split(":")[-1]) for v in vs for p in v2fiyat(pid, cur, v.get("id")).split("; ") if ":" in p})
            m2 = re.search(rf"{etk} ([\d.]+)(?:-([\d.]+))?", h[3])
            sayi = [float(x) for x in m2.groups() if x] if m2 else []
            esit(f"MD1 fiyat {etk} {pid}", sayi and [sayi[0], sayi[-1]], f and [f[0], f[-1]])
            d = D(D(j(f"urun_{pid}_v2_prices_{cur}.json").get("yanit")).get("data"))
            back = [x.get("price") for x in L(D(d.get("product")).get("placements")) if x.get("id") == "back"]
            m3 = re.search(rf"arka yuz ek: WW ([\d.]+) / NA ([\d.]+)", h[3])
            esit(f"MD1 arka {etk} {pid}", (m3.group(1 if etk == "WW" else 2) if m3 else None), back[0] if back else None)
        if kay == "v1":
            for v in vs:
                na = v2fiyat(pid, "USD_north_america", v.get("id")).split(":")[-1]
                if str(v.get("price")) != na:
                    hata.append(f"BILGI {pid}/{v.get('id')}: v1 price {v.get('price')} != v2 NA {na}")
        px = set()
        pf = D(D(j(f"urun_{pid}_printfiles.json").get("yanit")).get("result"))
        for x in L(pf.get("printfiles")):
            px.add(f"{x.get('width')}x{x.get('height')}")
        esit(f"MD1 px {pid}", sorted(set(re.findall(r"(?<![\d.])\d+x\d+(?![\d.])", h[6]))), sorted(px))
        inch = {f"{d.get('placement')}={d.get('width')}x{d.get('height')}" for v in L(D(j(f"urun_{pid}_v2_variants.json").get("yanit")).get("data"))
                for d in L(v.get("placement_dimensions"))}
        sag = {x.strip() for parca in h[6].split("<br>") for x in parca.split(" / ", 1)[-1].split(";")}
        esit(f"MD1 alan inch {pid}", sorted(sag), sorted(inch) or ["API vermedi"])
        ks = [(k, sec(k)) for k in KEYS if k[0] == pid]
        abd_disi = [ex for k, ex in ks if k[2] != "US"]
        yalniz = bool(abd_disi) and all(e is None and "united states only" in json.dumps(x.get("yanit")).lower()
                                        for e, x in abd_disi) and any(k[2] == "US" and ex[0] for k, ex in ks)
        esit(f"MD1 yalniz_abd {pid}", "YALNIZ ABD" in h[5], yalniz)
    t2 = md.split("## 2.")[1].split("## 3.")[0]
    bas = next(s for s in t2.splitlines() if s.startswith("| urun |"))
    ulk = [x.strip() for x in bas.strip().strip("|").split("|")][1:]
    for satir in t2.splitlines():
        m = re.match(r"\| (\d+) ", satir)
        if not m:
            continue
        pid = m.group(1)
        h = [x.strip() for x in satir.strip().strip("|").split("|")][1:]
        for u, hc in zip(ulk, h):
            ks_ = [k for k in KEYS if k[0] == pid and k[2] == u]
            es = [sec(k)[0] for k in ks_]
            xs = ks_
            oran = sorted({float(e["rate"]) for e in es if e})
            gum = any(s_.get("customs_fees_possible") is True for k, e in zip(ks_, es) if e
                      for o in L(D((K2.get(k) or {}).get("yanit")).get("data")) if o.get("shipping") == e.get("id")
                      for s_ in L(o.get("shipments")))
            esit(f"MD2 {pid} {u} gumruk", hc.endswith("†"), gum)
            if not xs:
                esit(f"MD2 {pid} {u}", hc, "sorgulanmadi")
            elif not oran:
                esit(f"MD2 {pid} {u} gonderilmez", hc.startswith("GONDERILMEZ"), True)
            else:
                sayi = [float(x) for x in re.match(r"([\d.]+)(?:-([\d.]+))? \(", hc).groups() if x]
                esit(f"MD2 {pid} {u}", [sayi[0], sayi[-1]], [oran[0], oran[-1]])
                gun = sorted({f"{e['minDeliveryDays']}-{e['maxDeliveryDays']}" for e in es if e})
                esit(f"MD2 {pid} {u} gun", re.search(r", ([\d\-/]+) g", hc).group(1), "/".join(gun))

    bilgi = [h for h in hata if h.startswith("BILGI")]
    gercek = [h for h in hata if not h.startswith("BILGI")]
    for h in hata[:200]:
        print(h)
    print(f"DOGRULAMA kontrol {say[0]} | uyusmazlik {len(gercek)} | bilgi {len(bilgi)} -> {'PASS' if not gercek else 'FAIL'}")
    return 0 if not gercek else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
