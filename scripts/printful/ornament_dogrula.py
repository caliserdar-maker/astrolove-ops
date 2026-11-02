#!/usr/bin/env python3
"""ornament_katalog.py ciktisini ham JSON ile tek tek karsilastirir (rapor kodunu KULLANMAZ; degerleri ham'dan yeniden okur).
Kontroller: CSV her varyant satiri (fiyat v1/v2, boyut, printfile id/px/dpi/fill, bolgeler, 9 ulke kargo = ham en ucuz),
KARGO.csv her satir (ucret, ad, gun, en ucuz mu, cikis ulkesi), MD tablo 1 fiyat araligi ve tablo 2 hucreleri,
_istekler.json'da yalniz GET ve izinli POST. Kullanim: ornament_dogrula.py <cikti_klasor>. Uyusmazlik varsa cikis 1."""
import csv
import json
import re
import sys
from pathlib import Path

IZINLI_POST = {"/shipping/rates", "/v2/shipping-rates"}


def L(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def D(x):
    return x if isinstance(x, dict) else {}


def j(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(c):
    ham = c / "ham"
    hata, say = [], 0

    def esit(ad, csv_deger, ham_deger):
        nonlocal say
        say += 1
        if str(csv_deger) != str(ham_deger):
            hata.append(f"{ad}: csv={csv_deger!r} ham={ham_deger!r}")

    ist = j(ham / "_istekler.json") or []
    for x in ist:
        say += 1
        if x["yontem"] not in ("GET", "POST") or (x["yontem"] == "POST" and x["yol"].split("?")[0] not in IZINLI_POST):
            hata.append(f"izinsiz istek {x['yontem']} {x['yol']}")
    k1 = j(ham / "kargo_v1.json") or []
    k2 = j(ham / "kargo_v2.json") or []
    K1 = {(str(x["urun"]), str(x["varyant"]), x["ulke"]): x for x in k1}
    K2 = {(str(x["urun"]), str(x["varyant"]), x["ulke"]): x for x in k2}

    def ucuz(x):
        res = [r for r in L(D((x or {}).get("yanit")).get("result")) if r.get("rate") not in (None, "")]
        return min(res, key=lambda r: float(r["rate"])) if res else None

    rows = list(csv.DictReader(open(c / "PRINTFUL_ORNAMENT.csv", encoding="utf-8")))
    aday = j(ham / "_adaylar.json") or {}
    for pid in aday:
        n_ham = len((((j(ham / f"urun_{pid}_v1.json") or {}).get("yanit") or {}).get("result") or {}).get("variants") or [])
        esit(f"urun {pid} varyant sayisi", sum(1 for r in rows if r["urun_id"] == pid), n_ham)
    for r in rows:
        pid, vid = r["urun_id"], r["varyant_id"]
        res = ((j(ham / f"urun_{pid}_v1.json") or {}).get("yanit") or {}).get("result") or {}
        v = next((x for x in res.get("variants") or [] if str(x.get("id")) == vid), None)
        if v is None:
            hata.append(f"{pid}/{vid}: ham v1'de yok")
            continue
        esit(f"{pid}/{vid} fiyat_usd_v1", r["fiyat_usd_v1"], v.get("price"))
        esit(f"{pid}/{vid} boyut", r["boyut_api"], v.get("size") or "API vermedi")
        esit(f"{pid}/{vid} ad", r["varyant_adi"], v.get("name"))
        sat = sorted({a.get("region") for a in v.get("availability_status") or [] if a.get("status") in ("in_stock", "stocked_on_demand")})
        esit(f"{pid}/{vid} bolgeler", r["satilabilir_bolgeler_v1"], ", ".join(sat) or "API vermedi")
        esit(f"{pid}/{vid} yalniz_abd", r["yalniz_abd"] == "EVET", sat == ["US"])
        # v2 fiyat
        for cur, kol in (("USD", "fiyat_usd_v2"), ("EUR", "fiyat_eur_v2"), ("EUR_europe", "fiyat_eur_v2_europe"),
                         ("USD_north_america", "fiyat_usd_v2_north_america")):
            d = D(D(D(j(ham / f"urun_{pid}_v2_prices_{cur}.json")).get("yanit")).get("data"))
            vv = next((x for x in L(d.get("variants")) if str(x.get("id")) == vid), None)
            beklenen = "; ".join(f"{t.get('technique_key') or t.get('technique_display_name')}:{t.get('price')}"
                                 for t in L((vv or {}).get("techniques"))) or "API vermedi"
            esit(f"{pid}/{vid} {kol}", r[kol], beklenen)
            if cur.startswith("EUR") and vv and d.get("currency") not in (None, "EUR"):
                hata.append(f"{pid}/{vid}: EUR istegi currency={d.get('currency')}")
        # printfile
        pf = ((j(ham / f"urun_{pid}_printfiles.json") or {}).get("yanit") or {}).get("result") or {}
        pfid = {str(x.get("printfile_id")): x for x in pf.get("printfiles") or []}
        yer = next((x.get("placements") for x in pf.get("variant_printfiles") or [] if str(x.get("variant_id")) == vid), {}) or {}
        for kol, al in (("printfile_px", None), ("printfile_dpi", "dpi"), ("fill_mode", "fill_mode"), ("printfile_id", "id")):
            parca = []
            for y, i in yer.items():
                x = pfid.get(str(i)) or {}
                deg = f"{x.get('width')}x{x.get('height')}" if al is None else (i if al == "id" else x.get(al))
                parca.append(f"{y}={deg}")
            esit(f"{pid}/{vid} {kol}", r[kol], "; ".join(parca) or "API vermedi")
        # kargo
        for ulke in [k[6:-4] for k in r if k.startswith("kargo_") and k.endswith("_usd")]:
            x = K1.get((pid, vid, ulke))
            if x is None:
                continue
            e = ucuz(x)
            esit(f"{pid}/{vid} kargo {ulke}", r[f"kargo_{ulke}_usd"], e.get("rate") if e else f"HATA HTTP {x.get('http')}")

    krows = list(csv.DictReader(open(c / "PRINTFUL_ORNAMENT_KARGO.csv", encoding="utf-8")))
    esit("kargo satir sayisi", len(krows), len(k1))
    for r in krows:
        key = (r["urun_id"], r["varyant_id"], r["ulke"])
        x = K1.get(key)
        if x is None:
            hata.append(f"kargo {key}: ham yok")
            continue
        e = ucuz(x)
        if e is None:
            esit(f"kargo {key} ucret", r["ucret"], "API vermedi")
            continue
        for kol, al in (("ucret", "rate"), ("yontem_id", "id"), ("yontem_adi", "name"), ("para", "currency"),
                        ("min_gun", "minDeliveryDays"), ("max_gun", "maxDeliveryDays")):
            esit(f"kargo {key} {kol}", r[kol], e.get(al) if e.get(al) is not None else "API vermedi")
        esit(f"kargo {key} para USD", r["para"], "USD")
        d2 = L(D((K2.get(key) or {}).get("yanit")).get("data"))
        m2 = next((y for y in d2 if y.get("shipping") == e.get("id")), None)
        if m2 is None and d2:
            m2 = min((y for y in d2 if y.get("rate") not in (None, "")), key=lambda y: float(y["rate"]), default=None)
        dep = sorted({s.get("departure_country") for s in L((m2 or {}).get("shipments")) if s.get("departure_country")})
        esit(f"kargo {key} cikis", r["cikis_ulkesi_v2"], ", ".join(dep) or "API vermedi")
        if m2 and r["ucret_v2"] != "API vermedi" and abs(float(r["ucret_v2"]) - float(r["ucret"])) > 0.005:
            hata.append(f"BILGI kargo {key}: v1 {r['ucret']} != v2 {r['ucret_v2']} (ayni yontem)")

    # MD tablolari
    md = (c / "PRINTFUL_ORNAMENT.md").read_text(encoding="utf-8")
    t2 = md.split("## 2.")[1].split("## 3.")[0]
    bas = [l for l in t2.splitlines() if l.startswith("| urun |")][0]
    ulkeler = [x.strip() for x in bas.strip("|").split("|")][1:]
    for l in t2.splitlines():
        m = re.match(r"\| (\d+) ", l)
        if not m:
            continue
        pid = m.group(1)
        hucre = [x.strip() for x in l.strip().strip("|").split("|")][1:]
        for ul, h in zip(ulkeler, hucre):
            oran = sorted({float(ucuz(x)["rate"]) for k, x in K1.items() if k[0] == pid and k[2] == ul and ucuz(x)})
            sayi = [float(s) for s in re.match(r"([\d.]+)(?:-([\d.]+))? ", h + " ").groups() if s] if re.match(r"[\d.]", h) else []
            esit(f"MD kargo {pid} {ul}", sayi and [sayi[0], sayi[-1]], oran and [oran[0], oran[-1]])
    t1 = md.split("## 1.")[1].split("## 2.")[0]
    for l in t1.splitlines():
        m = re.match(r"\| (\d+) ", l)
        if not m:
            continue
        pid = m.group(1)
        hucre = [x.strip() for x in l.strip().strip("|").split("|")]
        res = ((j(ham / f"urun_{pid}_v1.json") or {}).get("yanit") or {}).get("result") or {}
        f = sorted({float(v["price"]) for v in res.get("variants") or [] if v.get("price") not in (None, "")})
        sayi = [float(s) for s in re.findall(r"[\d.]+", hucre[3])]
        esit(f"MD fiyat {pid}", sayi and [sayi[0], sayi[-1]], f and [f[0], f[-1]])

    bilgi = [h for h in hata if h.startswith("BILGI")]
    gercek = [h for h in hata if not h.startswith("BILGI")]
    for h in hata[:200]:
        print(h)
    print(f"DOGRULAMA kontrol {say} | uyusmazlik {len(gercek)} | bilgi {len(bilgi)} -> {'PASS' if not gercek else 'FAIL'}")
    return 0 if not gercek else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
