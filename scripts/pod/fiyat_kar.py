#!/usr/bin/env python3
""".99 -> asagi yuvarlama (Serdar karari 28 Eyl) icin fiyat donusumu + net kar kapisi. Etsy'ye YAZMAZ; Prodigi yalniz /quotes.

yeni_fiyat(p): .99 ile biten fiyat asagi yuvarlanir (39.99 -> 39, 109.99 -> 109); digerleri DEGISMEZ (None).
Kar: net = fiyat - Etsy kesintisi - Prodigi maliyeti.
  Etsy kesintisi = 0.698 + 0.2062 x fiyat (KDV dahil; docs/REFERANS_ILAN_CL.md 27 Eyl; Offsite Ads haric).
  Prodigi maliyeti = canli /quotes toplam (urun + kargo, router'in kargo yontemi) + router EKLER_USD; ulke basina
  (router'in otomatik ulkeleri US, CA, AU, GB). Dijital: maliyet 0.
Kapi: yeni fiyatta herhangi bir ulkede net <= 0 olan kalem varsa FAIL (yazma yok).
Kalem turu SKU v3 sonekinden: -DIGITAL | (yok)=PRINT | -FGO/-FBK/-FWH/-FNA.
"""
import math
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/prodigi")); sys.path.insert(0, str(KOK / "scripts/etsy"))

UCRET_SABIT, UCRET_ORAN = 0.698, 0.2062
ULKELER = ["US", "CA", "AU", "GB"]
SKU_RX = re.compile(r"-(\d+x\d+|A[1-4])(?:-(DIGITAL|FGO|FBK|FWH|FNA))?$")


def yeni_fiyat(p):
    c = round(float(p) * 100)
    return float(c // 100) if c % 100 == 99 else None


def tur_boy(sku):
    m = SKU_RX.search(sku or "")
    if not m:
        return None, None
    return (m.group(2) or "PRINT"), m.group(1)


def ucret(fiyat):
    return UCRET_SABIT + UCRET_ORAN * fiyat


class Maliyet:
    """(tur, boy, ulke) -> Prodigi maliyeti USD (onbellekli canli teklif)."""

    def __init__(self, prod=None, env="live"):
        import order_router as R
        self.R = R
        self.prod = prod or R.Prodigi(R.load_prodigi_key(env), env)
        self.prod.shipping_method = getattr(self.prod, "shipping_method", R.DEFAULT_SHIPPING_METHOD)
        self.cer = R.cerceve_haritasi()
        self.c, self.skular = {}, {}

    def sku(self, on, boy):
        """Katalogdaki kesin SKU yazimi (GET /products; order_router.sku_haritasi ile ayni aday sirasi)."""
        k = (on, boy)
        if k not in self.skular:
            bul = ""
            for aday in dict.fromkeys([f"GLOBAL-{on}-{boy}", f"GLOBAL-{on}-{boy.upper()}", f"GLOBAL-{on}-{boy.lower()}"]):
                st, d = self.prod.urun(aday)
                if st == 200:
                    bul = ((d.get("product") or {}).get("sku")) or aday
                    break
            if not bul:
                raise SystemExit(f"HATA: Prodigi katalogda SKU yok: GLOBAL-{on}-{boy}. DUR.")
            self.skular[k] = bul
        return self.skular[k]

    def teklif(self, item, ulke):
        """Kendi POST /quotes istegi (yalniz fiyat teklifi; siparis ACILMAZ). Kalemde 'sizing' YOK (29 Eyl: /quotes
        UnknownField). Router'a dokunulmaz; maliyet = urun + kargo (router'in kargo yontemi) + router EKLER_USD."""
        kalem = {"sku": item["prodigi_sku"], "copies": 1, "assets": [{"printArea": "default"}]}
        if item.get("attributes"):
            kalem["attributes"] = item["attributes"]
        st, d = self.prod.call("POST", "/quotes", {"shippingMethod": self.prod.shipping_method, "destinationCountryCode": ulke,
                                                  "currencyCode": "USD", "items": [kalem]})
        if st != 200 or not d.get("quotes"):
            return None, f"HTTP {st}: {str(d)[:300]}"
        cs = d["quotes"][0].get("costSummary") or {}
        toplam = float((cs.get("items") or {}).get("amount") or 0) + float((cs.get("shipping") or {}).get("amount") or 0)
        return round(toplam + self.R.EKLER_USD, 2), ""

    def __call__(self, tur, boy, ulke):
        if tur == "DIGITAL":
            return 0.0
        k = (tur, boy, ulke)
        if k not in self.c:
            if tur == "PRINT":
                item = {"prodigi_sku": self.sku("HPR", boy), "qty": 1, "attributes": {}}
            else:
                e = self.cer.get((boy, tur[1:]))
                if not e:
                    raise SystemExit(f"HATA: cerceve eslemesi yok ({boy}, {tur}). DUR.")
                item = {"prodigi_sku": self.sku("CFP", boy), "qty": 1, "attributes": e["attributes"]}
            maliyet, hata = self.teklif(item, ulke)
            if maliyet is None:
                raise SystemExit(f"HATA: Prodigi teklifi alinamadi {k} ({item['prodigi_sku']}): {hata}. DUR.")
            self.c[k] = float(maliyet)            # quote() EKLER_USD dahil doner
        return self.c[k]


def kalem_kar(tur, boy, eski, yeni, maliyet):
    """-> {ulke: (net_eski, net_yeni)}"""
    return {u: (round(eski - ucret(eski) - maliyet(tur, boy, u), 2), round(yeni - ucret(yeni) - maliyet(tur, boy, u), 2))
            for u in ULKELER}


def envanter_kar(inv, maliyet):
    """Bir ilanin envanteri -> (kalemler, dokunulmayanlar, sorunlar). kalem: (tur, boy, eski, yeni, {ulke: (eski, yeni)})."""
    gor, kalem, dok, sorun = set(), [], [], []
    for p in inv.get("products") or []:
        tur, boy = tur_boy(p.get("sku"))
        o = [o for o in p.get("offerings") or [] if not o.get("is_deleted")]
        if not tur or not o:
            sorun.append(f"SKU cozulmedi: {p.get('sku')}"); continue
        pr = o[0].get("price")
        eski = pr if isinstance(pr, (int, float)) else round(float(pr.get("amount")) / float(pr.get("divisor") or 100), 2)
        yeni = yeni_fiyat(eski)
        if yeni is None:
            dok.append((p.get("sku"), eski)); yeni = eski
        if (tur, boy, eski) in gor:
            continue
        gor.add((tur, boy, eski))
        k = kalem_kar(tur, boy, eski, yeni, maliyet)
        kalem.append((tur, boy, eski, yeni, k))
        for u, (_, ny) in k.items():
            if ny <= 0:
                sorun.append(f"net <= 0: {tur} {boy} {eski} -> {yeni} {u} net {ny}")
    return kalem, dok, sorun


def kar_md(kalem):
    md = ["| tur | boy | eski | yeni | " + " | ".join(f"net {u} eski/yeni" for u in ULKELER) + " |",
          "|---|---|---|---|" + "---|" * len(ULKELER)]
    for tur, boy, eski, yeni, k in sorted(kalem, key=lambda x: (x[0], x[2])):
        md.append(f"| {tur} | {boy} | {eski:.2f} | {yeni:.2f} | " + " | ".join(
            f"{k[u][0]:.2f} / {'**' if k[u][1] <= 0 else ''}{k[u][1]:.2f}{'**' if k[u][1] <= 0 else ''}" for u in ULKELER) + " |")
    return md
