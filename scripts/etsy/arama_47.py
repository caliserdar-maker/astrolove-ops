#!/usr/bin/env python3
"""47: bizim 78 POD ilan + kargo profilleri + magaza + rakip ilanlarin alanlari (SALT OKUR, etsy-arama, 10 Eki 2026 gece).

Yalniz Etsy.get; toplu uclar (getListingsByShop + includes, getListingsByListingIds 100'luk). Cagri siniri 60:
asilacaksa okuma durur, eldeki yazilir ve notta bildirilir. Etsy'ye yazmaz.
Kullanim: python3 arama_47.py <cikti_klasoru> <47_rakip_ids.csv> [40d_ek.csv]
"""
import csv
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from seo_live_snapshot import zodiac_pair  # noqa: E402

SINIR = 60


class Sinir(Exception):
    pass


class Okuyucu:
    def __init__(self, api):
        self.api, self.n, self.hata = api, 0, []

    def get(self, path, params=None):
        if self.n + 1 > SINIR:
            raise Sinir(f"cagri siniri {SINIR}: {path} okunmadi")
        self.n += 1
        try:
            return self.api.get(path, params=params, ok404=True) or {}
        except SystemExit as e:
            self.hata.append(f"{path}: {e}")
            return {}


def ts(v):
    try:
        return datetime.fromtimestamp(int(v), timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def para(m):
    if not isinstance(m, dict) or m.get("amount") is None:
        return ""
    try:
        return f"{int(m['amount']) / int(m.get('divisor') or 100):.2f} {m.get('currency_code', '')}".strip()
    except (TypeError, ValueError, ZeroDivisionError):
        return ""


def u(x):
    return html.unescape(str(x or ""))


def abd_hedef(dest):
    """ABD hedefi: once US ulke satiri, yoksa 'everywhere else' (ulke yok, bolge none) satiri."""
    us = [d for d in dest if d.get("destination_country_iso") == "US"]
    if us:
        return us[0], "US"
    ee = [d for d in dest if not d.get("destination_country_iso") and d.get("destination_region") in (None, "", "none")]
    return (ee[0], "everywhere else") if ee else ({}, "")


def eksik(sayac, obj, alanlar):
    for a in alanlar:
        if a not in obj:
            sayac[a] += 1


def bizim(ok, shop, kayip):
    rows, offset = [], 0
    while True:
        r = ok.get(f"/shops/{shop}/listings", {"state": "active", "limit": 100, "offset": offset,
                                                 "includes": "Images,Shipping,Inventory,Videos,Translations"})
        page = r.get("results") or []
        rows += page
        if len(page) < 100:
            break
        offset += 100
    sec = {s.get("shop_section_id"): u(s.get("title")) for s in (ok.get(f"/shops/{shop}/sections").get("results") or [])}
    pp = {p.get("production_partner_id"): f"{u(p.get('partner_name'))} ({u(p.get('location'))})"
          for p in (ok.get(f"/shops/{shop}/production-partners").get("results") or [])}
    out = []
    for x in rows:
        if x.get("listing_type") != "physical":
            continue
        eksik(kayip, x, ["production_partners", "translations", "inventory", "images", "videos", "shipping_profile",
                         "personalization_instructions", "views"])
        inv = x.get("inventory") or {}
        varyant, adlar, fiyatlar = [], [], []
        for p in inv.get("products") or []:
            ad = " / ".join(f"{u(pv.get('property_name'))}: {', '.join(u(v) for v in pv.get('values') or [])}"
                            for pv in p.get("property_values") or [])
            for pv in p.get("property_values") or []:
                n = u(pv.get("property_name"))
                if n and n not in adlar:
                    adlar.append(n)
            for o in p.get("offerings") or []:
                pr = para(o.get("price"))
                varyant.append(f"{ad or 'tek'} = {pr}")
                try:
                    fiyatlar.append(int(o["price"]["amount"]) / int(o["price"].get("divisor") or 100))
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    pass
        imgs = sorted(x.get("images") or [], key=lambda i: i.get("rank") or 0)
        partners = x.get("production_partners")
        if isinstance(partners, list):
            pp_txt = " | ".join(pp.get(p.get("production_partner_id") if isinstance(p, dict) else p,
                                       u(p.get("partner_name")) if isinstance(p, dict) else str(p)) for p in partners) or "yok"
        else:
            pp_txt = "API vermedi"
        tr = x.get("translations")
        if isinstance(tr, list):
            diller = " | ".join(sorted({u(t.get("language")) for t in tr if isinstance(t, dict)})) or "yok"
        elif isinstance(tr, dict):
            diller = " | ".join(sorted(tr)) or "yok"
        else:
            diller = "API vermedi"
        title = u(x.get("title"))
        desc = u(x.get("description"))
        out.append({
            "listing_id": x.get("listing_id"), "cift": zodiac_pair(title), "title": title,
            "tags": " | ".join(u(t) for t in x.get("tags") or []),
            "description_ilk300": desc[:300], "description_uzunluk": len(desc),
            "taxonomy_id": x.get("taxonomy_id"), "materials": " | ".join(u(m) for m in x.get("materials") or []),
            "section_id": x.get("shop_section_id"), "section_adi": sec.get(x.get("shop_section_id"), ""),
            "fiyat_ilan": para(x.get("price")), "has_variations": x.get("has_variations"),
            "varyasyon_adlari": " | ".join(adlar), "varyasyon_sayisi": len(varyant),
            "fiyat_min": f"{min(fiyatlar):.2f}" if fiyatlar else "", "fiyat_max": f"{max(fiyatlar):.2f}" if fiyatlar else "",
            "varyasyon_fiyatlari": " ; ".join(varyant) if varyant else "API vermedi",
            "is_personalizable": x.get("is_personalizable"),
            "personalization_is_required": x.get("personalization_is_required"),
            "personalization_char_count_max": x.get("personalization_char_count_max"),
            "personalization_instructions": u(x.get("personalization_instructions")) or "bos",
            "who_made": x.get("who_made"), "when_made": x.get("when_made"), "production_partners": pp_txt,
            "should_auto_renew": x.get("should_auto_renew"), "state": x.get("state"),
            "created": ts(x.get("original_creation_timestamp") or x.get("created_timestamp")),
            "updated": ts(x.get("updated_timestamp")), "last_modified": ts(x.get("last_modified_timestamp")),
            "foto_sayisi": len(imgs),
            "fotolar": " ; ".join(f"{i.get('rank')}: {i.get('full_width')}x{i.get('full_height')} alt={u(i.get('alt_text')) or 'bos'}"
                                  for i in imgs),
            "video_sayisi": len(x.get("videos") or []), "shipping_profile_id": x.get("shipping_profile_id"),
            "ceviri_dilleri": diller, "views": x.get("views"), "num_favorers": x.get("num_favorers"),
        })
    return sorted(out, key=lambda r: r["cift"])


def kargo(ok, shop):
    out = []
    for p in ok.get(f"/shops/{shop}/shipping-profiles").get("results") or []:
        dest = p.get("shipping_profile_destinations") or []
        d0, kaynak = abd_hedef(dest)
        diger = [f"{d.get('destination_country_iso') or d.get('destination_region') or '?'}: {para(d.get('primary_cost'))}"
                 f" + {para(d.get('secondary_cost'))} ({d.get('min_delivery_days')}-{d.get('max_delivery_days')} gun)"
                 for d in dest if d is not d0]
        ilk = para(d0.get("primary_cost"))
        out.append({
            "shipping_profile_id": p.get("shipping_profile_id"), "ad": u(p.get("title")),
            "origin_country": p.get("origin_country_iso"), "origin_postal": p.get("origin_postal_code") or "",
            "min_processing_days": p.get("min_processing_days"), "max_processing_days": p.get("max_processing_days"),
            "processing_etiket": u(p.get("processing_days_display_label")),
            "abd_hedef_var": f"evet ({kaynak})" if d0 else "hayir", "abd_ilk_urun": ilk or "-",
            "abd_ek_urun": para(d0.get("secondary_cost")) or "-",
            "abd_ucretsiz": ("evet" if ilk.startswith("0.00") else "hayir") if ilk else "-",
            "abd_teslim_min_gun": d0.get("min_delivery_days"), "abd_teslim_max_gun": d0.get("max_delivery_days"),
            "abd_tasiyici": u(d0.get("shipping_carrier_id") or d0.get("mail_class") or ""),
            "diger_hedefler": " ; ".join(diger) or "yok",
            "upgrade_sayisi": len(p.get("shipping_profile_upgrades") or []),
        })
    return out


def magaza(ok, shop):
    s = ok.get(f"/shops/{shop}")
    rows = []
    for k in ["shop_name", "title", "announcement", "sale_message", "digital_sale_message", "url", "currency_code",
              "listing_active_count", "review_average", "review_count", "transaction_sold_count", "languages",
              "accepts_custom_requests", "is_using_structured_policies", "policy_welcome", "policy_payment",
              "policy_shipping", "policy_refunds", "policy_additional", "policy_seller_info", "policy_privacy",
              "policy_has_private_receipt_info", "policy_updated_timestamp", "vacation_mode", "shipping_from_country_iso"]:
        v = s.get(k, "API vermedi")
        if k == "policy_updated_timestamp" and v != "API vermedi":
            v = ts(v)
        rows.append({"alan": k, "deger": json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else u(v) if v is not None else "bos"})
    rows.append({"alan": "icon_var", "deger": "evet" if s.get("icon_url_fullxfull") else "hayir"})
    for p in ok.get(f"/shops/{shop}/policies/return").get("results") or []:
        rows.append({"alan": f"iade_politikasi_{p.get('return_policy_id')}",
                     "deger": f"accepts_returns={p.get('accepts_returns')}; accepts_exchanges={p.get('accepts_exchanges')}; "
                              f"return_deadline={p.get('return_deadline')}"})
    for sct in ok.get(f"/shops/{shop}/sections").get("results") or []:
        rows.append({"alan": f"bolum: {u(sct.get('title'))}", "deger": f"{sct.get('active_listing_count')} aktif ilan"})
    rows.append({"alan": "about", "deger": "API v3'te magaza About ucu yok; okunmadi"})
    return rows


def rakip(ok, ids_csv, ek_csv, not_):
    ifade = {}
    for p in [ids_csv] + ([ek_csv] if ek_csv and Path(ek_csv).exists() else []):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            lid = r.get("listing_id") or (re.search(r"/listing/(\d+)", r.get("listing_url", "")) or [None, None])[1]
            if lid:
                ifade.setdefault(str(lid), [])
                if r.get("mi_ifadeler"):
                    ifade[str(lid)].append(r["mi_ifadeler"])
                elif r.get("kaynak_ifade"):
                    ifade[str(lid)].append(f"{r['kaynak_ifade']} (#{r.get('sira', '')})")
    not_.append(f"Rakip ID kaynagi: {Path(ids_csv).name}" + (f" + {Path(ek_csv).name}" if ek_csv and Path(ek_csv).exists() else
                                                            "; 40d_MI_EK_TOP.csv yok (sonra eklenecek)"))
    ids = list(ifade)
    out, donen = [], set()
    for i in range(0, len(ids), 100):
        parti = ids[i:i + 100]
        r = ok.get("/listings/batch", {"listing_ids": ",".join(parti), "includes": "Images,Shipping,Videos,Shop"})
        for x in r.get("results") or []:
            lid = str(x.get("listing_id"))
            donen.add(lid)
            sp = x.get("shipping_profile") or {}
            dest = sp.get("shipping_profile_destinations") or []
            d0, _ = abd_hedef(dest)
            ucret = para(d0.get("primary_cost")) if d0 else ""
            out.append({
                "listing_id": lid, "magaza": u((x.get("shop") or {}).get("shop_name")) or "API vermedi",
                "title": u(x.get("title")), "tags": " | ".join(u(t) for t in x.get("tags") or []),
                "taxonomy_id": x.get("taxonomy_id"), "fiyat": para(x.get("price")),
                "abd_kargo": ucret or ("kargo profili API vermedi" if not sp else "ABD hedefi yok"),
                "abd_ucretsiz": ("evet" if ucret.startswith("0.00") else "hayir") if ucret else "-",
                "processing_days": (f"{sp.get('min_processing_days')}-{sp.get('max_processing_days')}" if sp else
                                    (f"{x.get('processing_min')}-{x.get('processing_max')}" if x.get("processing_min") is not None
                                     else "API vermedi")),
                "foto_sayisi": len(x.get("images") or []), "video_sayisi": len(x.get("videos") or []),
                "is_personalizable": x.get("is_personalizable"),
                "materials": " | ".join(u(m) for m in x.get("materials") or []), "when_made": x.get("when_made"),
                "created": ts(x.get("original_creation_timestamp") or x.get("created_timestamp")),
                "state": x.get("state"), "num_favorers": x.get("num_favorers", "API vermedi"),
                "views": x.get("views", "API vermedi"), "mi_ifadeleri": " | ".join(ifade.get(lid, [])),
            })
    not_.append(f"Rakip: {len(ids)} tekil ID istendi, {len(donen)} ilan dondu, {len(ids) - len(donen)} donmedi "
                f"(silinmis/pasif olabilir)")
    return out


def yaz(out, ad, rows):
    if not rows:
        (out / ad).write_text("veri yok\n", encoding="utf-8")
        return 0
    with open(out / ad, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def run(api, shop, out, ids_csv, ek_csv=None):
    out.mkdir(parents=True, exist_ok=True)
    ok, kayip, not_ = Okuyucu(api), Counter(), []
    sonuc = {}
    durdu = ""
    try:
        sonuc["47_BIZIM_ILAN_ALANLAR.csv"] = bizim(ok, shop, kayip)
        sonuc["47b_KARGO.csv"] = kargo(ok, shop)
        sonuc["47c_MAGAZA.csv"] = magaza(ok, shop)
        sonuc["47d_RAKIP_ILAN_ALANLAR.csv"] = rakip(ok, ids_csv, ek_csv, not_)
    except Sinir as e:
        durdu = str(e)
    satir = {ad: yaz(out, ad, rows) for ad, rows in sonuc.items()}
    lines = ["47 OKUMA NOTU (etsy-arama, salt okur; Etsy'ye yazma 0)",
             f"Okuma zamani: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             f"API cagri: {ok.n} (sinir {SINIR}); kalan kota: {api.remaining}",
             f"DURDU: {durdu}" if durdu else "Cagri siniri asilmadi.",
             *[f"{ad}: {n} satir (+1 baslik)" for ad, n in satir.items()],
             *not_,
             f"API hatalari: {len(ok.hata)}", *[f"  - {h}" for h in ok.hata],
             "Bizim ilanlarda API yanitinda HIC olmayan alanlar (alan: ilan sayisi): "
             + (", ".join(f"{k}: {v}" for k, v in kayip.most_common()) or "yok"),
             "Magaza About: Etsy API v3'te uc yok, okunmadi.",
             "Kisisellestirme: API yalniz tek alan (personalization_instructions / char_count_max) verir; "
             "Shop Manager'daki coklu kisisellestirme alanlari API'de gorunmuyorsa 'bos' yazar."]
    (out / "47_OKUMA_NOTU.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"SONUC: cagri {ok.n}, satir {satir}, hata {len(ok.hata)}, durdu={bool(durdu)}; Etsy yazma 0")
    return 0 if not durdu and not ok.hata else 1


def main():
    key, secret, shop = (os.environ.get(k, "") for k in ("ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_SHOP_ID"))
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    return run(Etsy(store), shop, Path(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)


if __name__ == "__main__":
    sys.exit(main())
