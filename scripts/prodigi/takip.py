#!/usr/bin/env python3
"""Kargo takip bilgisi: Prodigi gonderisi -> Etsy kargo bildirimi (saf fonksiyonlar, ag yok).

23 Eyl 2026 incelemesinin 4 bulgusu burada kapatilir:
  1. Onaylanan kargo yontemi tek kaynaktan gelir (siparis govdesi order_router.order_body'de
     shipping_method parametresiyle; bu modul yalniz takip tarafini tutar).
  2. Takipte numara + URL + tasiyici adi + hizmet + (varsa) son ayak numarasi saklanir.
  3. USPS eslestirmesi TAHMINLE yapilmaz: hizmet/tasiyici adi taninmis bir son-ayak hizmeti ise VE
     numara USPS IMpb bicimine birebir uyuyorsa yapilir. Ikisinden biri tutmazsa eslestirme YOK.
  4. Basari olcutu: dogru receipt + tam numara + dogru carrier_name + calisan takip linki.
     is_shipped tek basina PASS DEGILDIR.

GECMIS SIPARIS KORUMASI (24 Eyl 2026, Serdar karari): kod ileride canliya alinsa bile gecmis
siparislere takip YAZMAZ; Etsy her basarili createReceiptShipment'ta aliciya otomatik e-posta atar.
Yalniz sinirdan (YENI_SIPARIS_BASLANGIC_UTC) sonra acilmis VE Etsy'de hic gonderi kaydi olmayan
receipt'e yazilir (bkz. yazma_karari). Sinir yalniz ILERI tasinabilir (bkz. sinir_ts).
"""
import calendar
import re
import time

# Etsy carrier_name kodlari: yalniz BIRE BIR tanidigimiz tasiyicilar eslenir, digerleri "other".
# (Etsy'nin kabul ettigi ad listesi createReceiptShipment dokumaninda; kod bunlarin disina cikmaz.)
ETSY_TASIYICI = {
    "usps": "usps",
    "united states postal service": "usps",
    "ups": "ups",
    "ups mail innovations": "usps",          # son ayagi USPS teslim eder (numara dogrulanirsa)
    "fedex": "fedex",
    "fedex smartpost": "fedex",
    "dhl": "dhl",
    "dhl express": "dhl",
    "royal mail": "royal-mail",
    "canada post": "canada-post",
    "australia post": "australia-post",
}
# Son ayagi USPS olan hizmet/tasiyici adlari (bunlar disinda USPS eslestirmesi yapilmaz)
USPS_SON_AYAK = ("usps", "united states postal service", "mail innovations", "parcel select",
                 "first class", "first-class", "priority mail", "ground advantage")
# USPS IMpb: 22 veya 26 hane, 92/93/94/95 ile baslar. Onunde 420+posta kodu varsa o onek ayrilir.
_USPS = re.compile(r"9[2-5]\d{20}(?:\d{4})?$")
_USPS_420 = re.compile(r"^420\d{5}(?:\d{4})?(9[2-5]\d{20}(?:\d{4})?)$")
TAKIP_URL = {
    "usps": "https://tools.usps.com/go/TrackConfirmAction?tLabels={n}",
    "ups": "https://www.ups.com/track?tracknum={n}",
    "fedex": "https://www.fedex.com/fedextrack/?trknbr={n}",
    "dhl": "https://www.dhl.com/global-en/home/tracking.html?tracking-id={n}",
    "royal-mail": "https://www.royalmail.com/track-your-item#/tracking-results/{n}",
    "canada-post": "https://www.canadapost-postescanada.ca/track-reperage/en#/resultList?searchFor={n}",
    "australia-post": "https://auspost.com.au/mypost/track/#/details/{n}",
}


def temiz(n):
    return re.sub(r"[^0-9A-Za-z]", "", str(n or ""))


def usps_numarasi(numara):
    """USPS IMpb bicimine BIREBIR uyuyorsa (gerekirse 420 oneki ayrilarak) numarayi dondurur."""
    n = temiz(numara)
    m = _USPS_420.match(n)
    if m:
        return m.group(1), "420 oneki ayrildi"
    if _USPS.fullmatch(n):
        return n, ""
    return "", ""


def son_ayak_hizmeti(*metinler):
    d = " ".join(str(x or "").lower() for x in metinler)
    return any(k in d for k in USPS_SON_AYAK)


def takip_bilgi(shipment):
    """Prodigi shipment -> {numara, url, tasiyici_ad, tasiyici_hizmet, son_ayak_numara}."""
    tr = (shipment or {}).get("tracking") or {}
    ca = (shipment or {}).get("carrier") or {}
    numara = temiz(tr.get("number"))
    son_ayak, _ = usps_numarasi(numara)
    return {"numara": numara,
            "url": (tr.get("url") or "").strip(),
            "tasiyici_ad": (ca.get("name") or "").strip(),
            "tasiyici_hizmet": (ca.get("service") or "").strip(),
            "son_ayak_numara": son_ayak if son_ayak and son_ayak != numara else ""}


def etsy_plani(bilgi):
    """Takip bilgisi -> Etsy'ye yazilacak plan. Tahmin yok; eslesmeyen tasiyici 'other' olur."""
    ad = (bilgi.get("tasiyici_ad") or "").strip()
    hizmet = (bilgi.get("tasiyici_hizmet") or "").strip()
    numara = temiz(bilgi.get("numara"))
    gerekce, uyari = [], []

    usps_num, not_420 = usps_numarasi(numara)
    hizmet_usps = son_ayak_hizmeti(ad, hizmet)
    if hizmet_usps and usps_num:
        kod, kullanilan = "usps", usps_num
        gerekce.append(f"hizmet adi son-ayak USPS ('{ad} / {hizmet}') + numara USPS IMpb bicimi"
                       + (f" ({not_420})" if not_420 else ""))
    else:
        kod = ETSY_TASIYICI.get(ad.lower().strip(), "")
        kullanilan = numara
        if kod == "usps" and not usps_num:
            kod, uyari = "other", uyari + [f"'{ad}' USPS'e eslenirdi ama numara USPS bicimine uymuyor; "
                                           "eslestirme YAPILMADI"]
        if not kod:
            kod = "other"
            uyari.append(f"tasiyici adi tabloda yok: '{ad}'")
        else:
            gerekce.append(f"tasiyici adi tabloda: '{ad}' -> {kod}")
        if hizmet_usps and not usps_num:
            uyari.append("hizmet USPS son ayagi gibi duruyor ama numara bicimi dogrulanmadi (tahmin yok)")

    url = (bilgi.get("url") or "").strip() or (TAKIP_URL.get(kod, "").format(n=kullanilan) if kullanilan else "")
    return {"tracking_code": kullanilan, "carrier_name": kod, "takip_url": url,
            "url_kaynagi": "prodigi" if (bilgi.get("url") or "").strip() else ("tablo" if url else "YOK"),
            "gerekce": "; ".join(gerekce), "uyari": "; ".join(uyari)}


def zaten_var(receipt, plan):
    """Etsy receipt'inde ayni numara zaten kayitli mi -> (var_mi, kayitli_carrier)."""
    for s in (receipt or {}).get("shipments") or []:
        if temiz(s.get("tracking_code")) == temiz(plan["tracking_code"]):
            return True, (s.get("carrier_name") or "").strip()
    return False, ""


YENI_SIPARIS_BASLANGIC_UTC = "2026-09-24 20:00:00"   # bu andan ONCE acilan receipt'e asla yazilmaz
_ZAMAN = "%Y-%m-%d %H:%M:%S"


def utc_metin(ts):
    return time.strftime(_ZAMAN, time.gmtime(int(ts)))


def sinir_ts(ileri=""):
    """Yeni siparis siniri (epoch). `ileri` verilirse yalniz daha GEC bir ana tasir; geriye alinamaz."""
    taban = calendar.timegm(time.strptime(YENI_SIPARIS_BASLANGIC_UTC, _ZAMAN))
    if not str(ileri or "").strip():
        return taban
    return max(taban, calendar.timegm(time.strptime(str(ileri).strip(), _ZAMAN)))


def yazma_karari(receipt, rid, plan, sinir):
    """Etsy'ye createReceiptShipment POST'u yapilabilir mi -> (karar, neden).
    karar: "yaz"     yeni siparis, Etsy'de hic gonderi yok -> tek POST
           "dogrula" ayni numara zaten kayitli (onceki kosunun POST'u) -> POST YOK, yalniz dogrulama
           "gecmis"  sinirdan once acilmis ya da Etsy'de baska gonderi/is_shipped var -> POST YOK, kalici
           "hata"    receipt okunamadi / zaman yok -> POST YOK (guvenli taraf), elle bakilir"""
    r = receipt or {}
    if str(r.get("receipt_id") or "") != str(rid):
        return "hata", f"receipt eslesmedi ({r.get('receipt_id')} != {rid})"
    try:
        ts = int(r.get("create_timestamp") or r.get("created_timestamp"))
    except (TypeError, ValueError):
        return "hata", "receipt olusturma zamani okunamadi (guvenli taraf: yazilmaz)"
    if ts < sinir:
        return "gecmis", f"gecmis siparis: receipt {utc_metin(ts)} < sinir {utc_metin(sinir)} UTC"
    var, kayitli = zaten_var(r, plan)
    if var:
        return "dogrula", f"ayni numara Etsy'de zaten kayitli (carrier '{kayitli}'); tekrar POST yok"
    gonderiler = r.get("shipments") or []
    if gonderiler or r.get("is_shipped"):
        return "gecmis", (f"Etsy'de baska gonderi kaydi var ({len(gonderiler)} adet, is_shipped="
                          f"{bool(r.get('is_shipped'))}); ikinci bildirim yok")
    return "yaz", "yeni siparis, Etsy'de gonderi kaydi yok"


def dogrula(receipt, rid, plan, url_durumu):
    """Basari olcutu: dogru receipt + tam numara + dogru carrier_name + calisan link.
    is_shipped TEK BASINA yeterli degildir. -> (pass_mi, [eksikler])."""
    eksik = []
    if str((receipt or {}).get("receipt_id") or "") != str(rid):
        eksik.append(f"receipt eslesmedi ({(receipt or {}).get('receipt_id')} != {rid})")
    ayni = [g for g in (receipt or {}).get("shipments") or []
            if temiz(g.get("tracking_code")) == temiz(plan["tracking_code"])]
    if not ayni:
        eksik.append(f"numara Etsy gonderilerinde yok: {plan['tracking_code']}")
    else:
        kayitli = [(g.get("carrier_name") or "").strip().lower() for g in ayni]
        if plan["carrier_name"].lower() not in kayitli:
            eksik.append(f"carrier_name farkli: Etsy {kayitli} != plan '{plan['carrier_name']}'")
    if not plan.get("takip_url"):
        eksik.append("takip linki uretilemedi")
    elif url_durumu not in ("ok",):
        eksik.append(f"takip linki calismiyor ({url_durumu})")
    return (not eksik), eksik
