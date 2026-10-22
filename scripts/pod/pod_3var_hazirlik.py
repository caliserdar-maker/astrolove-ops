#!/usr/bin/env python3
"""UC VARYASYON HAZIRLIGI: Urun tipi + Renk + Boy (Serdar onayi 22 Eyl 2026, yapi secenegi C).

!!! BU BETIK BU GOREVDE CALISTIRILMADI. Yalniz hazirlik. Yazma modu acik onay ister. !!!

Modlar (ilki ikisi SALT OKUMA):
  ozellikler : ilanin taxonomy_id'si icin Etsy'nin HAZIR property listesi (3. varyasyon
               Etsy'nin tanimli property'lerinden secilmek zorunda). GET, yazma yok.
  plan       : canli envanteri okur, 3 varyasyonlu govdeyi kurar, JSON olarak yazdirir.
               price_on_property = [<tip property_id>, <boy property_id>] denenir.
               Etsy'ye HICBIR SEY gonderilmez.
  yaz        : govdeyi PUT eder. --confirm UC_VARYASYON zorunlu.
               PUT oncesi anlik goruntu Drive'a yazilir (geri alma dosyasi).
  geri_al    : verilen anlik goruntu dosyasindan ESKI envanteri aynen geri yazar.
               --confirm GERI_AL zorunlu.

Geri alma plani (yaz modunda otomatik hazirlanir):
  1. yaz modu once GET /listings/{lid}/inventory yapar ve ham cevabi
     Drive TEMP/POD_5X7/YEDEK/<lid>/inventory_3VAR_ONCE.json olarak saklar.
  2. Bir sorun olursa: `geri_al --yedek <o dosya> --confirm GERI_AL`.
     Geri alma, eski products dizisini ve eski *_on_property dizilerini aynen PUT eder;
     boylece menu sirasi, fiyatlar ve SKU'lar eski haline doner.
  3. Etsy yeni value_id uretmis olabilir; geri almada eski value_id'ler kullanilir,
     kullanilmayan degerler Etsy tarafinda olu kalir (ilanda gorunmez).

NOT: 3. varyasyon eklendiginde Etsy'nin `max_variations_supported=3` sorgu parametresi
gonderilir (OAS'ta enum ['2','3'], olculdu 22 Eyl kosu 35689867471).
"""
import argparse
import json
import os
import pathlib
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore  # noqa: E402
import pod_pilot_15 as P  # noqa: E402
import pod_boy_15 as B  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
# Serdar karari 22 Eyl: urun tipi secenekleri ve Etsy fiyat farki (cerceve fiyatlari
# CERCEVE_FIYAT.csv'den gelir; burada yalniz secenek adlari sabit).
TIPLER = ["Unframed Print", "Framed, Black", "Framed, White", "Framed, Natural"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def tip_property_bul(api, taxonomy_id):
    """Etsy'nin hazir property listesinden urun tipi icin uygun olani secer.
    Donus: (property_id, property_name, hazir_degerler) ya da (None, None, liste)."""
    d = api.get(f"/buyer-taxonomy/nodes/{taxonomy_id}/properties", ok404=True) or {}
    ozellikler = d.get("results") or []
    if not ozellikler:
        d = api.get(f"/seller-taxonomy/nodes/{taxonomy_id}/properties", ok404=True) or {}
        ozellikler = d.get("results") or []
    ozet = [{"property_id": o.get("property_id"), "name": o.get("name"),
             "display_name": o.get("display_name"),
             "deger_sayisi": len(o.get("possible_values") or []),
             "ornek_degerler": [v.get("name") for v in (o.get("possible_values") or [])[:12]],
             "supports_variations": o.get("supports_variations"),
             "is_multivalued": o.get("is_multivalued")}
            for o in ozellikler]
    # "Framing" / "Style" / "Product type" gibi adaylari one al
    def puan(o):
        ad = (o["name"] or "").lower()
        for i, anahtar in enumerate(("framing", "frame", "product type", "style", "finish")):
            if anahtar in ad:
                return i
        return 99
    ozet.sort(key=puan)
    uygun = [o for o in ozet if o["supports_variations"] and puan(o) < 99]
    if uygun:
        return uygun[0]["property_id"], uygun[0]["name"], ozet
    return None, None, ozet


def govde_3var(inv, tip_pid, tip_adi, fiyat_tablosu):
    """Mevcut 75 urunu (5 renk x 15 boy) 4 urun tipiyle carpar -> 300 urun.

    fiyat_tablosu: {(tip, boy): fiyat}. Eksik kombinasyon = o urun OLUSTURULMAZ
    (ilanda o secenek kapali olur; CERCEVE_FIYAT.csv'de KAPALI isaretli olanlar).
    """
    eski = inv.get("products") or []
    renk_ad = "primary color" if P.pv_of(eski[0], "primary color") else "color"
    boy_pv = P.pv_of(eski[0], "size")
    boy_pid = boy_pv.get("property_id")
    urunler, atlanan = [], []
    for tip in TIPLER:
        for pr in eski:
            boy_et = P.deger(pr, "size")
            boy = B.anahtar_of(boy_et)
            fiyat = fiyat_tablosu.get((tip, boy))
            if fiyat is None:
                atlanan.append((tip, boy))
                continue
            pvs = []
            for pv in pr.get("property_values") or []:
                d = {"property_id": pv.get("property_id"),
                     "values": list(pv.get("values") or [])}
                for k in ("property_name", "scale_id"):
                    if pv.get(k):
                        d[k] = pv[k]
                if pv.get("value_ids"):
                    d["value_ids"] = list(pv["value_ids"])
                pvs.append(d)
            pvs.append({"property_id": tip_pid, "property_name": tip_adi, "values": [tip]})
            o0 = (pr.get("offerings") or [{}])[0]
            off = {"price": fiyat, "quantity": o0.get("quantity"), "is_enabled": True}
            if o0.get("readiness_state_id"):
                off["readiness_state_id"] = o0["readiness_state_id"]
            sku_ek = {"Unframed Print": "UF", "Framed, Black": "FB",
                      "Framed, White": "FW", "Framed, Natural": "FN"}[tip]
            urunler.append({"sku": f"{pr.get('sku')}-{sku_ek}",
                            "property_values": pvs, "offerings": [off]})
    b = {"products": urunler,
         # ASIL DENEY: fiyat hem tipe hem boya bagli
         "price_on_property": [tip_pid, boy_pid],
         "quantity_on_property": inv.get("quantity_on_property") or [],
         "sku_on_property": sorted({tip_pid, boy_pid,
                                    *(inv.get("sku_on_property") or [])})}
    if inv.get("readiness_state_on_property"):
        b["readiness_state_on_property"] = inv["readiness_state_on_property"]
    return b, atlanan


def fiyat_tablosu_yukle(yol):
    """CERCEVE_FIYAT.csv -> {(tip, boy): fiyat}. KAPALI satirlar alinmaz."""
    import csv
    tablo = {}
    for boy, f in B.HEDEF:
        tablo[("Unframed Print", boy)] = f
    if not yol:
        return tablo
    renk_tip = {"black": "Framed, Black", "white": "Framed, White",
                "natural": "Framed, Natural"}
    for r in csv.DictReader(open(yol, encoding="utf-8")):
        if (r.get("karar") or "").strip() != "ACIK":
            continue
        tip = renk_tip.get((r.get("renk") or "").strip())
        fiyat = r.get("fiyat_15_ads") or r.get("fiyat_20_reklamsiz")
        if tip and fiyat:
            tablo[(tip, r["boy"])] = float(fiyat)
    return tablo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["ozellikler", "plan", "yaz", "geri_al"])
    ap.add_argument("--listing", default="4570110641")
    ap.add_argument("--fiyat-csv", default="")
    ap.add_argument("--yedek", default="")
    ap.add_argument("--is-dizin", default="_work/uc_var")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    lid = str(a.listing)

    if a.mod == "geri_al":
        if a.confirm != "GERI_AL" or not a.yedek:
            raise SystemExit("DUR: geri_al icin --confirm GERI_AL ve --yedek <dosya> gerekir")
        eski = json.loads(pathlib.Path(a.yedek).read_text(encoding="utf-8"))
        govde = {"products": [{"sku": p.get("sku") or "",
                               "property_values": [{k: v for k, v in pv.items()
                                                    if k in ("property_id", "property_name",
                                                             "scale_id", "value_ids", "values")}
                                                   for pv in p.get("property_values") or []],
                               "offerings": [{"price": P.para(o.get("price")),
                                              "quantity": o.get("quantity"),
                                              "is_enabled": bool(o.get("is_enabled")),
                                              **({"readiness_state_id": o["readiness_state_id"]}
                                                 if o.get("readiness_state_id") else {})}
                                             for o in p.get("offerings") or []]}
                              for p in eski.get("products") or []],
                 "price_on_property": eski.get("price_on_property") or [],
                 "quantity_on_property": eski.get("quantity_on_property") or [],
                 "sku_on_property": eski.get("sku_on_property") or []}
        log(f"GERI ALMA: {len(govde['products'])} urun, price_on_property "
            f"{govde['price_on_property']}")
        api.put_json(f"/listings/{lid}/inventory", govde)
        log("geri alindi; simdi geri okuyup dogrula (pod_durum_15.py)")
        return 0

    L = api.get(f"/listings/{lid}") or {}
    tax = L.get("taxonomy_id")
    log(f"ilan {lid} | durum {L.get('state')} | taxonomy_id {tax}")
    tip_pid, tip_adi, ozet = tip_property_bul(api, tax)
    if a.mod == "ozellikler":
        p = isd / "TAXONOMY_OZELLIKLER.json"
        p.write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
        for o in ozet[:15]:
            log(f"  {o['property_id']} {o['name']!r} varyasyon={o['supports_variations']} "
                f"deger={o['deger_sayisi']} ornek={o['ornek_degerler'][:6]}")
        log(f"secilen tip property: {tip_pid} {tip_adi!r} | dosya {p}")
        return 0
    if not tip_pid:
        raise SystemExit("DUR: urun tipi icin uygun Etsy property'si bulunamadi "
                         "(3. varyasyon hazir listeden secilmek zorunda). ozellikler modunu calistir.")

    inv = api.get(f"/listings/{lid}/inventory") or {}
    tablo = fiyat_tablosu_yukle(a.fiyat_csv)
    govde, atlanan = govde_3var(inv, tip_pid, tip_adi, tablo)
    log(f"plan: {len(inv.get('products') or [])} -> {len(govde['products'])} urun | "
        f"kapali kombinasyon {len(atlanan)} | price_on_property {govde['price_on_property']}")
    p = isd / "UC_VAR_GOVDE.json"
    p.write_text(json.dumps(govde, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"govde yazildi: {p}")
    if a.mod == "plan":
        log("PLAN MODU: Etsy'ye hicbir sey gonderilmedi.")
        return 0

    if a.confirm != "UC_VARYASYON":
        raise SystemExit("DUR: yaz icin --confirm UC_VARYASYON gerekir")
    yed = isd / "inventory_3VAR_ONCE.json"
    yed.write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    P.rclone("copyto", str(yed), f"{DRV}/YEDEK/{lid}/inventory_3VAR_ONCE.json")
    log(f"geri alma dosyasi: {DRV}/YEDEK/{lid}/inventory_3VAR_ONCE.json")
    api.put_json(f"/listings/{lid}/inventory?max_variations_supported=3", govde)
    sonra = api.get(f"/listings/{lid}/inventory") or {}
    log(f"geri okuma: urun {len(sonra.get('products') or [])} | "
        f"price_on_property {sonra.get('price_on_property')}")
    if sonra.get("price_on_property") != govde["price_on_property"]:
        log("!!! Etsy price_on_property'yi OLDUGU GIBI KABUL ETMEDI — geri alma gerekebilir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
