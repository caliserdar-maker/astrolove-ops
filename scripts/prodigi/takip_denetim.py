#!/usr/bin/env python3
"""GOREV 0033 - yoldaki gonderilerin takip denetimi (varsayilan SALT OKUMA).
Prodigi GET /orders/{id} -> shipments (carrier.name/service, tracking.number/url, dispatchDate).
Receipt: siparisin merchantReference'i (etsy-<rid>-... ya da <rid>) ya da STATE (prodigi_order_id/kanal_oid) - repoya yazilmaz.
Etsy getShopReceipt -> shipments (carrier_name, tracking_code), is_shipped. Takip linkleri HTTP durumu.
Musteri adi/adresi OKUNMAZ/YAZILMAZ. Receipt raporda son 4 hane ile gosterilir.
--yaz: tasiyici uyusmazligi KANITLANAN receipt'e createReceiptShipment ile takip.etsy_plani'nin carrier_name'i +
Prodigi'nin numarasi yazilir (yeni numara uydurulmaz; send_bcc yok). Etsy aliciya bildirim gonderebilir: YALNIZ
Serdar'in o siparise ozel acik onayiyla (CLAUDE.md "MUSTERIYE DOKUNAN HER EYLEM"); koordinator/pano onayi gecersiz.
--gunluk (GOREV 0035 md.2, SALT OKUMA, Etsy'ye hic baglanmaz): Prodigi'de son 45 gunde acilip son 21 gunde
dispatch edilen tum siparisler; out/TAKIP_GUNLUK.md (fis son 4, lab, servis, dispatch, son tarama, gun).
Dispatch'ten 48 saat sonra takip sayfasinda tarama/tarih okunamiyorsa UYARI ve cikis 1 (bilincli FAIL).
--tam (GOREV 0034, SALT OKUMA; --yaz'i iptal eder): shipments tam alanlari + fulfillmentLocation, takip sayfasi
durum ifadeleri (ham metin YAZILMAZ: adres parcasi icerebilir), Prodigi quote (tum kargo yontemleri), Etsy
shipment tam alanlari (bildirim zamani). Cikti out/TAKIP_TAM.json {ozet, detay}.
Kullanim: takip_denetim.py <state_csv> <ord_id,ord_id,...> [--yaz | --tam]
          takip_denetim.py <state_csv> --gunluk"""
import csv
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import takip  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def kod(rid):
    return f"***{str(rid)[-4:]}" if rid else "-"


def http(url):
    if not url:
        return None
    try:
        return requests.get(url, headers=UA, timeout=30, allow_redirects=True).status_code
    except requests.RequestException as e:
        return type(e).__name__


DURUM_RX = re.compile(r"tracking not available|not available|label created|pre-shipment|shipping label|in transit|"
                      r"accepted|arrived|departed|out for delivery|delivered|customs|exception|delay\w*|"
                      r"received|processing|awaiting|no (?:tracking )?information|electronic(?:ally)? (?:notified|shipping)|"
                      r"origin|destination|handed over|international", re.I)


def sayfa_durum(url):
    """Takip sayfasindan yalniz bilinen durum ifadeleri (sirali, tekrarsiz) + tarih bicimleri sayisi."""
    if not url:
        return None
    try:
        r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"http": type(e).__name__}
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", r.text)
    t = re.sub(r"<[^>]+>", " ", t)
    ifade = []
    for m in DURUM_RX.finditer(t):
        k = m.group(0).lower()
        if k not in ifade:
            ifade.append(k)
    tarih = sorted(set(re.findall(r"\b(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2} (?:Sep|Oct)\w* \d{4}|(?:Sep|Oct)\w* \d{1,2},? \d{4})\b", t)))
    return {"http": r.status_code, "son_url": r.url.split("?")[0], "bayt": len(r.text), "ifade": ifade[:25], "tarih": tarih[:15]}


def tam_prodigi(prod, o):
    adr = ((o.get("recipient") or {}).get("address") or {})
    ulke = adr.get("countryCode")
    items = [{"sku": i.get("sku"), "attributes": i.get("attributes"), "status": i.get("status")} for i in o.get("items") or []]
    q = []
    for i in items[:1]:
        d, err = prod.quote(i["sku"], i["attributes"] or {}, ulke)
        for x in (d or {}).get("quotes") or []:
            q.append({"yontem": x.get("shipmentMethod"),
                      "gonderi": [{"carrier": sh.get("carrier"), "lab": sh.get("fulfillmentLocation"),
                                   "cost": sh.get("cost")} for sh in x.get("shipments") or []],
                      "anahtar": sorted(x)})
        if err:
            q.append({"hata": err})
    return {"hedef_ulke": ulke, "shippingMethod": o.get("shippingMethod"), "created": o.get("created"),
            "status": o.get("status"), "items": items, "charges_n": len(o.get("charges") or []),
            "shipments": [{k: v for k, v in sh.items() if k != "items"} | {"items_n": len(sh.get("items") or [])}
                          for sh in o.get("shipments") or []],
            "quote": q}


def receipt_bul(o, state):
    mr = str(o.get("merchantReference") or "")
    m = re.match(r"(?:etsy-)?(\d{8,})", mr)
    if m:
        return m.group(1)
    for r in state:
        if o.get("id") in (r.get("prodigi_order_id"), r.get("kanal_oid")):
            return r.get("receipt_id")
    return ""


def yoldakiler(prod, simdi, gun_ac=45, gun_dispatch=21):
    """Prodigi GET /orders (sayfali): son gun_ac gunde acilan, son gun_dispatch gunde dispatch edilmis siparisler."""
    from datetime import timedelta
    bas = (simdi - timedelta(days=gun_ac)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, skip = [], 0
    while True:
        r = prod._call("GET", f"/orders?top=100&skip={skip}&createdFrom={bas}")
        d = r.json() if r.status_code == 200 else {}
        sayfa = d.get("orders") or []
        for o in sayfa:
            for sh in o.get("shipments") or []:
                dt = zaman(sh.get("dispatchDate"))
                if dt and (simdi - dt).days <= gun_dispatch:
                    out.append((o, sh, dt))
        if not d.get("hasMore") or not sayfa:
            return out, r.status_code
        skip += len(sayfa)


def zaman(t):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except ValueError:
        return None


def gunluk(prod, state):
    from datetime import datetime, timezone
    simdi = datetime.now(timezone.utc)
    liste, http_ = yoldakiler(prod, simdi)
    satir, uyari = [], 0
    for o, sh, dt in sorted(liste, key=lambda x: x[2]):
        c, lab = sh.get("carrier") or {}, sh.get("fulfillmentLocation") or {}
        sd = sayfa_durum((sh.get("tracking") or {}).get("url")) or {}
        son = sd.get("tarih")[-1] if sd.get("tarih") else ("OKUNAMADI" if sd.get("http") != 200 or not sd.get("ifade") else "YOK")
        saat = (simdi - dt).total_seconds() / 3600
        u = saat > 48 and not sd.get("tarih")
        uyari += u
        satir.append(f"| {kod(receipt_bul(o, state))} | {lab.get('countryCode', '')}/{lab.get('labCode', '')} | {c.get('name', '')} {c.get('service', '')} "
                     f"| {dt:%Y-%m-%d %H:%M} | {son} (http {sd.get('http')}) | {saat / 24:.1f} | {'UYARI' if u else 'ok'} |")
    md = [f"# TAKIP_GUNLUK {simdi:%Y-%m-%d %H:%M} UTC (salt okuma; Prodigi liste http {http_})", "",
          f"- yoldaki gonderi: {len(satir)} | UYARI (48 saat+ tarama yok/okunamadi): {uyari}", "",
          "| fis | lab | servis | dispatch | son tarama | gun | durum |", "|---|---|---|---|---|---|---|"] + satir
    Path("out").mkdir(exist_ok=True)
    Path("out/TAKIP_GUNLUK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:3]), flush=True)
    return 1 if uyari or http_ != 200 else 0


def main():
    from prodigi_pilot_quote import Api, load_key
    state = list(csv.DictReader(open(sys.argv[1], encoding="utf-8"))) if Path(sys.argv[1]).exists() else []
    if "--gunluk" in sys.argv:
        sys.exit(gunluk(Api(load_key()), state))
    from etsy_common import Etsy, TokenStore, mask
    oids = [x.strip() for x in sys.argv[2].split(",") if x.strip()]
    tam = "--tam" in sys.argv
    yaz = "--yaz" in sys.argv and not tam
    prod = Api(load_key())
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    sonuc = []
    for oid in oids:
        r = prod._call("GET", f"/orders/{oid}")
        d = r.json() if r.status_code == 200 else {}
        o = d.get("order") or {}
        rid = receipt_bul(o, state)
        if tam:
            s_tam = tam_prodigi(prod, o)
            for sh in s_tam["shipments"]:
                sh["sayfa"] = sayfa_durum((sh.get("tracking") or {}).get("url"))
        s = {"order": oid, "http": r.status_code, "stage": (o.get("status") or {}).get("stage"),
             "kanal": not str(o.get("merchantReference") or "").startswith("etsy-"), "receipt": kod(rid), "gonderi": []}
        for sh in o.get("shipments") or []:
            b = takip.takip_bilgi(sh)
            plan = takip.etsy_plani(b)
            s["gonderi"].append({"tasiyici": b["tasiyici_ad"], "hizmet": b["tasiyici_hizmet"], "numara": b["numara"],
                                 "son_ayak": b["son_ayak_numara"], "dispatch": sh.get("dispatchDate"),
                                 "prodigi_url": b["url"], "prodigi_url_http": http(b["url"]),
                                 "plan_carrier": plan["carrier_name"], "plan_kod": plan["tracking_code"],
                                 "plan_url": plan["takip_url"], "plan_url_http": http(plan["takip_url"]),
                                 "gerekce": plan["gerekce"], "uyari": plan["uyari"]})
        if rid:
            e = api.get(f"/shops/{shop}/receipts/{rid}", ok404=True) or {}
            if tam:
                s_tam["etsy"] = {"status": e.get("status"), "is_shipped": e.get("is_shipped"),
                                 "updated": e.get("updated_timestamp"),
                                 "shipments": [{k: v for k, v in x.items() if not re.search(r"email|name|address", k) or k == "carrier_name"}
                                               for x in e.get("shipments") or []]}
            s["etsy"] = {"is_shipped": e.get("is_shipped"),
                         "gonderi": [{"carrier_name": x.get("carrier_name"), "tracking_code": x.get("tracking_code")}
                                     for x in e.get("shipments") or []]}
            yazili = {(str(x["carrier_name"] or "").lower(), takip.temiz(x["tracking_code"])) for x in s["etsy"]["gonderi"]}
            for g in s["gonderi"]:
                dogru = (g["plan_carrier"], takip.temiz(g["plan_kod"]))
                g["etsy_durum"] = ("AYNI" if dogru in yazili else
                                   "TASIYICI_FARKLI" if any(t == dogru[1] or t == takip.temiz(g["numara"]) for _, t in yazili) else
                                   "ETSY_TAKIP_YOK" if not yazili else "FARKLI")
                if yaz and g["etsy_durum"] in ("TASIYICI_FARKLI", "ETSY_TAKIP_YOK") and g["plan_carrier"] != "other" and g["plan_kod"]:
                    w = api.post(f"/shops/{shop}/receipts/{rid}/tracking",
                                 data={"tracking_code": g["plan_kod"], "carrier_name": g["plan_carrier"]})
                    g["yazildi"] = bool(w)
        if tam:
            s["tam"] = s_tam
        sonuc.append(s)
        print(json.dumps(s, ensure_ascii=False), flush=True)
    Path("out").mkdir(exist_ok=True)
    if tam:
        ozet = [{"order": s["order"], "receipt": s["receipt"], "hedef": s["tam"]["hedef_ulke"], "yontem": s["tam"]["shippingMethod"],
                 "gonderi": [{"lab": sh.get("fulfillmentLocation"), "status": sh.get("status"), "dispatch": sh.get("dispatchDate"),
                              "carrier": sh.get("carrier"), "sayfa": sh.get("sayfa")} for sh in s["tam"]["shipments"]],
                 "etsy_n": len((s["tam"].get("etsy") or {}).get("shipments") or []),
                 "etsy_bildirim": [x.get("shipment_notification_timestamp") for x in (s["tam"].get("etsy") or {}).get("shipments") or []]}
                for s in sonuc]
        Path("out/TAKIP_TAM.json").write_text(json.dumps({"ozet": ozet, "detay": sonuc}, ensure_ascii=False, indent=1))
    Path("out/TAKIP_DENETIM.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    print(f"cagri etsy {api.calls}, kota {api.remaining}", flush=True)


if __name__ == "__main__":
    main()
