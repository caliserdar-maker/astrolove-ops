#!/usr/bin/env python3
"""Serdar 21 Eki kararlari 2-4: tek cagrili, geri okumali Etsy adimlari. Toplu kullanim YOK.
  oku   : SALT OKUMA. Magaza sale_message, tum kargo profilleri (hedef/ucret), ornek ilanin (CANCER_LIBRA yil donumu)
          profil + gorsel alt metinleri -> OUT/OKU.json.
  sale  : updateShop yalniz sale_message: Digital paragrafi birebir degisir (parca tam 1 kez olmali). Geri okuma: alan
          beklenenle ayni, diger metin alanlari ayni.
  profil_yeni: "BY Digital Free Worldwide" profili (tek hedef: diger tum ulkeler 0 USD; ayni adla varsa yeniden kullanilir)
          olusturulur, sonra yalniz ornek ilan ona alinir (profil adimi). Serdar 21 Eki: Kupa profiline tasima YOK.
  profil: updateListing yalniz shipping_profile_id (ornek ilan). Hedef profilin TUM hedefleri 0 USD olmali; ilan active
          olmali (taslak yayina alinmaz). Geri okuma: state active, profil yeni, baslik/etiket/aciklama ayni.
Kota tabani 10. Sir loga yazilmaz. Ortam: ETSY_*, TOKEN_FILE."""
import argparse
import html
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ORNEK_ILAN = "4595350971"  # CANCER_LIBRA yil donumu (Serdar canli kontrolu 21 Eki: TEMIZ)
KOTA_TABAN = 10
ESKI_DIJ = "Digital file: we will send your five print-ready PDF files, one for each color, within 24 hours in Etsy Messages."
YENI_DIJ = ("Digital file: within 24 hours we will send your personalized print-ready file in Etsy Messages, made with the "
            "options you chose. If anything needs a change, just reply and we will fix it.")
TIRE = re.compile("[—–]")


class Dur(Exception):
    pass


def kota(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise Dur(f"kota {api.remaining} < {KOTA_TABAN}")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else float(p or 0)


def profil_ozet(p):
    return dict(id=p.get("shipping_profile_id"), baslik=p.get("title"), islem=(p.get("min_processing_days"), p.get("max_processing_days")),
                hedefler=[dict(ulke=d.get("destination_country_iso"), bolge=d.get("destination_region"), ilk=para(d.get("primary_cost")),
                               ek=para(d.get("secondary_cost")), teslim=(d.get("min_delivery_days"), d.get("max_delivery_days")))
                          for d in p.get("shipping_profile_destinations") or []])


def metinler(x):
    return {k: v for k, v in (x or {}).items() if isinstance(v, str)}


def oku(api, shop, out, R):
    S = api.get(f"/shops/{shop}") or {}
    R["sale_message"] = S.get("sale_message")
    R["profiller"] = [profil_ozet(p) for p in (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []]
    x = api.get(f"/listings/{ORNEK_ILAN}", params={"includes": "Images"}) or {}
    R["ornek"] = dict(state=x.get("state"), profil=x.get("shipping_profile_id"), baslik=x.get("title"),
                      gorsel=[dict(rank=i.get("rank"), id=i.get("listing_image_id"), alt=i.get("alt_text")) for i in x.get("images") or []])
    kota(api)
    ucretsiz = [p["id"] for p in R["profiller"] if p["hedefler"] and all(h["ilk"] == 0 and h["ek"] == 0 for h in p["hedefler"])]
    R["tum_hedefleri_ucretsiz_profil"] = ucretsiz
    print(f"profil {len(R['profiller'])} | tum hedefleri 0 USD olan {len(ucretsiz)} | ornek ilan profili {R['ornek']['profil']} | "
          f"alt metinde print/ship {sum(1 for g in R['ornek']['gorsel'] if re.search(r'print|ship', g['alt'] or '', re.I))}")


def sale(api, shop, out, R):
    once = metinler(api.get(f"/shops/{shop}"))
    (out / "SALE_YEDEK.json").write_text(json.dumps(once, ensure_ascii=False, indent=1), encoding="utf-8")
    eski = once.get("sale_message") or ""
    kota(api)
    if eski.count(ESKI_DIJ) != 1:
        raise Dur(f"Digital paragrafi {eski.count(ESKI_DIJ)} kez (1 olmali)")
    varlik = set(re.findall(r"&#?\w+;", eski)) - {"&#39;"}
    if varlik:
        raise Dur(f"izinsiz HTML varligi {sorted(varlik)}")
    beklenen = eski.replace(ESKI_DIJ, YENI_DIJ)
    if TIRE.search(YENI_DIJ):
        raise Dur("yeni metinde uzun/orta tire")
    api.put(f"/shops/{shop}", {"sale_message": html.unescape(beklenen)})
    sonra = metinler(api.get(f"/shops/{shop}"))
    yeni = sonra.get("sale_message") or ""
    degisen = sorted(k for k in set(once) | set(sonra) if k not in ("sale_message",) and once.get(k) != sonra.get(k))
    R.update(once=eski, sonra=yeni, birebir=yeni == beklenen, gorunur=html.unescape(yeni) == html.unescape(beklenen),
             diger_degisen=degisen, five_kalan=len(re.findall(r"five print-ready", yeni, re.I)))
    if not (R["gorunur"] and not degisen and R["five_kalan"] == 0):
        raise Dur(f"geri okuma FAIL: gorunur {R['gorunur']} degisen {degisen}")
    print(f"SALE PASS | birebir {R['birebir']} | diger alan degisen yok | kota {api.remaining}")


def profil(api, shop, out, R, pid):
    P = profil_ozet(api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {})
    R["hedef_profil"] = P
    if not P["hedefler"] or not all(h["ilk"] == 0 and h["ek"] == 0 for h in P["hedefler"]):
        raise Dur(f"profil {pid} tum hedeflerde ucretsiz degil: yazma yok")
    x = api.get(f"/listings/{ORNEK_ILAN}") or {}
    kota(api)
    R["once"] = dict(state=x.get("state"), profil=x.get("shipping_profile_id"))
    if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
        raise Dur(f"ilan state {x.get('state')}: yazma yok (taslak yayina alinmaz)")
    y = api.patch(f"/shops/{shop}/listings/{ORNEK_ILAN}", {"shipping_profile_id": int(pid)}) or {}
    z = api.get(f"/listings/{ORNEK_ILAN}") or {}
    R["sonra"] = dict(state=z.get("state"), profil=z.get("shipping_profile_id"), patch_state=y.get("state"),
                      baslik_ayni=z.get("title") == x.get("title"), etiket_ayni=z.get("tags") == x.get("tags"),
                      aciklama_ayni=z.get("description") == x.get("description"))
    s = R["sonra"]
    if not (s["state"] == "active" and str(s["profil"]) == str(pid) and s["baslik_ayni"] and s["etiket_ayni"] and s["aciklama_ayni"]):
        raise Dur(f"geri okuma FAIL {s}")
    print(f"PROFIL PASS | {R['once']['profil']} -> {pid} | kota {api.remaining}")


YENI_PROFIL_AD = "BY Digital Free Worldwide"


def profil_yeni(api, shop, out, R):
    """Yil donumu ilanlari icin dunya geneli ucretsiz profil (yoksa olustur; ayni adla varsa yeniden kullan), sonra ornek ilan."""
    lst = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    kota(api)
    var = [p for p in lst if p.get("title") == YENI_PROFIL_AD]
    if len(var) > 1:
        raise Dur(f"ayni adla {len(var)} profil")
    if var:
        pid = var[0]["shipping_profile_id"]
        R["olay"] = f"profil zaten var {pid}"
    else:
        body = {"title": YENI_PROFIL_AD, "origin_country_iso": "TR", "primary_cost": 0, "secondary_cost": 0,
                "min_processing_time": 1, "max_processing_time": 3, "processing_time_unit": "business_days",
                "destination_country_iso": "US", "min_delivery_days": 1, "max_delivery_days": 2}
        # Etsy olusturmada region "none" kabul etmiyor (21 Eki 400): once US 0, sonra "diger tum ulkeler" 0 eklenir (by78_ksa yontemi)
        y = api.post(f"/shops/{shop}/shipping-profiles", body) or {}
        pid = y.get("shipping_profile_id")
        if not pid:
            raise Dur(f"profil olusmadi: {str(y)[:300]}")
        R["olay"] = f"profil olusturuldu {pid}"
    P0 = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
    if not any((d.get("destination_region") or "").lower() == "none" and not d.get("destination_country_iso")
               for d in P0.get("shipping_profile_destinations") or []):
        api.post(f"/shops/{shop}/shipping-profiles/{pid}/destinations",
                 {"primary_cost": 0, "secondary_cost": 0, "destination_region": "none", "min_delivery_days": 1, "max_delivery_days": 2})
        R["olay"] += " + diger tum ulkeler 0 USD eklendi"
        kota(api)
    P = profil_ozet(api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {})
    R["yeni_profil"] = P
    if not any(h["bolge"] == "none" and not h["ulke"] for h in P["hedefler"]):
        raise Dur("profilde 'diger tum ulkeler' hedefi yok")
    print(f"PROFIL {R['olay']} | hedef {len(P['hedefler'])} | hepsi 0 USD: {all(h['ilk'] == 0 and h['ek'] == 0 for h in P['hedefler'])}")
    profil(api, shop, out, R, str(pid))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "sale", "profil", "profil_yeni"])
    ap.add_argument("--profil", default="")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api, shop, R = Etsy(store), os.environ["ETSY_SHOP_ID"], {"mod": a.mod}
    kod = 0
    try:
        if a.mod == "oku":
            oku(api, shop, out, R)
        elif a.mod == "sale":
            sale(api, shop, out, R)
        elif a.mod == "profil_yeni":
            profil_yeni(api, shop, out, R)
        else:
            if not a.profil.isdigit():
                raise Dur("--profil sayi olmali")
            profil(api, shop, out, R, a.profil)
        R["sonuc"] = "PASS"
    except Dur as e:
        R["sonuc"], R["dur"] = "DUR", str(e)
        print(f"::error::DURDU: {e}")
        kod = 4
    finally:
        R["istek"], R["kota_son"] = api.calls, api.remaining
        (out / f"TEK_{a.mod.upper()}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    sys.exit(kod)


if __name__ == "__main__":
    main()
