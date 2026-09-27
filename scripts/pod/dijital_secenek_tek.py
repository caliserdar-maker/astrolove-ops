#!/usr/bin/env python3
"""Tek POD ilanina "Digital File (5 colors)" secenegi + aciklama blogu (Serdar onayi 27 Eyl 2026).

  oku <ilan>   : SALT OKUMA. Plan + kapilar, yazma yok.
  yaz <ilan>   : --confirm DIJITAL_TEK ile yazar:
                 1) updateListingInventory: Size listesine ILK deger ETIKET, 5 renkte FIYAT, SKU -DIGITAL.
                    Diger 80 urun (fiyat, SKU, adet, gorunurluk) birebir ayni kalir.
                 2) renk -> gorsel eslesmesi PUT sonrasi okunur, bozulduysa ayni degerlerle geri yazilir.
                 3) aciklama: BLOK, "16 SIZES" satirinin hemen ustune eklenir (yalniz description PATCH).
                 Her adimdan sonra geri okuma; ilk hatada DUR. ONCE/SONRA yedek out/ altina.
Ilan active degilse DOKUNULMAZ (updateListing taslagi yayina alir, CLAUDE.md). Sirlar loga yazilmaz."""
import json
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK.parent / "etsy"))
import dijital_secenek_plan as D  # noqa: E402
import pod_pilot_15 as P  # noqa: E402

ETIKET = "Digital File (5 colors)"
FIYAT = 9.99
D.ETIKET, D.FIYAT = ETIKET, FIYAT
OUT = Path("out")
BLOK = """✦ DIGITAL FILE OPTION
Choose "Digital File (5 colors)" in the Size menu. This option is a digital file. Nothing is shipped.

What you receive:
• Your personalized design with your names and message, in all 5 colors: Midnight Blue, Deep Black, Pure White, Champagne Ivory and Warm Parchment.
• 5 print ready PDF files, one for each color. Each file has 5 ratios: 4:5, 3:4, 2:3, 11:14 and ISO A.
• Print at home, at a local print shop or online.

How delivery works:
We check every order by hand. Once your personalization is reviewed, we send your files to you in Etsy Messages. If anything is unclear, we message you first.

Prefer a finished print? Choose any size in the Size menu and we will have it printed and shipped to you.
"""
KISISEL = ("is_personalizable", "personalization_is_required", "personalization_char_count_max",
           "personalization_instructions")


def log(m):
    print(m, flush=True)


def yeni_aciklama(desc):
    if "DIGITAL FILE OPTION" in desc:
        return None                                   # zaten var
    satirlar = desc.split("\n")
    idx = next((i for i, s in enumerate(satirlar) if s.strip().lstrip("✦").strip().upper().startswith("16 SIZES")), None)
    if idx is None:
        raise SystemExit("HATA: aciklamada '16 SIZES' satiri yok. DUR (yazma yapilmadi).")
    return "\n".join(satirlar[:idx] + BLOK.rstrip("\n").split("\n") + [""] + satirlar[idx:])


def beklenen(body):
    return {D.anahtar(p): (p["sku"], round(float(p["offerings"][0]["price"]), 2), p["offerings"][0]["quantity"],
                           bool(p["offerings"][0]["is_enabled"])) for p in body["products"]}


def okunan(inv):
    return {D.anahtar(p): (p.get("sku") or "", D.para(p["offerings"][0].get("price")), p["offerings"][0].get("quantity"),
                           bool(p["offerings"][0].get("is_enabled"))) for p in inv.get("products") or []}


def main():
    mod, lid = sys.argv[1], sys.argv[2]
    yaz = mod == "yaz"
    if yaz and "--confirm" not in sys.argv or yaz and sys.argv[sys.argv.index("--confirm") + 1] != "DIJITAL_TEK":
        raise SystemExit("HATA: yaz icin --confirm DIJITAL_TEK gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)
    sonuc = {"ilan": lid, "mod": mod}

    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    (OUT / f"DIJ_{lid}_ONCE.json").write_text(json.dumps({"listing": L, "inventory": inv, "variation_images": vi},
                                                         ensure_ascii=False))
    if L.get("state") != "active":
        sonuc["durum"] = f"ATLANDI state={L.get('state')}"
        return bitir(sonuc, 3)
    zaten_inv = any(D.anahtar(p)[1] == ETIKET for p in inv.get("products") or [])
    desc2 = yeni_aciklama(L.get("description") or "")
    if zaten_inv and desc2 is None:
        sonuc["durum"] = "ZATEN"
        return bitir(sonuc, 4)
    if zaten_inv:
        raise SystemExit("HATA: envanterde dijital var ama aciklamada yok; elle incele. DUR.")
    body = D.plan(inv)
    rows = D.diff(inv, body)
    say = {d: sum(1 for r in rows if r["durum"] == d) for d in ("YENI", "AYNI", "DEGISTI", "SILINDI")}
    sonuc["plan"] = say
    if say != {"YENI": 5, "AYNI": 80, "DEGISTI": 0, "SILINDI": 0}:
        sonuc["durum"] = "FAIL plan"
        return bitir(sonuc, 1)
    v_once = P.v_renk_haritasi(inv, vi)
    kis_once = {k: L.get(k) for k in KISISEL}
    log(f"plan PASS {say}; renk->gorsel {len(v_once)}; aciklama +{len(desc2) - len(L.get('description') or '')} karakter; kota {api.remaining}")
    if not yaz:
        (OUT / f"DIJ_{lid}_ACIKLAMA_YENI.txt").write_text(desc2)
        sonuc["durum"] = "KURU PASS"
        return bitir(sonuc, 0)

    # 1) envanter
    api.put_json(f"/listings/{lid}/inventory", body)
    inv2 = api.get(f"/listings/{lid}/inventory") or {}
    bek, oku = beklenen(body), okunan(inv2)
    fark = [(k, bek.get(k), oku.get(k)) for k in set(bek) | set(oku) if bek.get(k) != oku.get(k)]
    if fark:
        sonuc["durum"] = f"FAIL envanter geri okuma: {len(fark)} fark {fark[:3]}"
        return bitir(sonuc, 1)
    log("envanter PASS: 85 urun beklenenle ayni")
    # 2) renk -> gorsel
    vi2 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    v_sonra = P.v_renk_haritasi(inv2, vi2)
    sonuc["renk_gorsel"] = "gerekmedi"
    if v_sonra != v_once:
        pid, vid = None, {}
        for pr in inv2.get("products") or []:
            pv = P.pv_of(pr, "primary color") or P.pv_of(pr, "color")
            if pv and pv.get("value_ids"):
                pid = pid or pv.get("property_id")
                vid.setdefault((pv.get("values") or [""])[0], pv["value_ids"][0])
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                      {"variation_images": [{"property_id": pid, "value_id": vid[c], "image_id": int(img)}
                                            for c, img in v_once.items()]})
        vi3 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        if P.v_renk_haritasi(inv2, vi3) != v_once:
            sonuc["durum"] = "FAIL renk->gorsel onarilamadi"
            return bitir(sonuc, 1)
        sonuc["renk_gorsel"] = "POST ile geri yazildi"
    # 3) aciklama (ilan active; yalniz description)
    api.patch(f"/shops/{shop}/listings/{lid}", {"description": desc2})
    L2 = api.get(f"/listings/{lid}") or {}
    (OUT / f"DIJ_{lid}_SONRA.json").write_text(json.dumps({"listing": L2, "inventory": inv2}, ensure_ascii=False))
    hata = []
    if (L2.get("description") or "").strip() != desc2.strip():
        hata.append("aciklama geri okuma farkli")
    if L2.get("state") != "active":
        hata.append(f"state {L2.get('state')}")
    if {k: L2.get(k) for k in KISISEL} != kis_once:
        hata.append("kisisellestirme degisti")
    if hata:
        sonuc["durum"] = "FAIL " + "; ".join(hata)
        return bitir(sonuc, 1)
    sonuc["durum"] = "PASS"
    sonuc["kota"] = api.remaining
    return bitir(sonuc, 0)


def bitir(sonuc, rc):
    (OUT / "DIJITAL_TEK_SONUC.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    log("SONUC " + json.dumps(sonuc, ensure_ascii=False))
    sys.exit(rc)


if __name__ == "__main__":
    main()
