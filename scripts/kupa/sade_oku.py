#!/usr/bin/env python3
"""Gorev G-OKU (Merkez 1 Kas): sade kupa 12 ilan, yayin sonrasi SALT OKUMA kontrolu. Etsy'ye YAZMA YOK (yalniz GET; baska her istek
DUR). 4607523667'ye istek yok. Kaynak: kupa-orchard <metin_ref> SADE12_SEO_ONERI.csv (alt metinler), SADE12_METIN.csv (kisisellestirme
talimati); sade_taslak.STILLER / BOYLAR (fiyat, varyasyon, stil gorseli sirasi); nitelikler: ARIES 4607613712 (Serdar onayli sablon,
ayni kosuda okunur) + Occasion = Birthday; kartlar: KART_KLASOR (Merkez 1 Kas tablosu, 31 Eki kart kosusu; 12 x 5 = 60 kart).
Cikti: OUT/OKU.csv (ilan, madde, beklenen, okunan, sonuc) + OUT/OKU_OZET.json + OUT/HAM_<id>.json.
Kullanim: sade_oku.py --confirm OKU12   (env: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, SEO_CSV, METIN_CSV,
          IMG_ROOT (<burc>/<kart dosyalari>), OUT)"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import sade_taslak as ST  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ILAN = {"ARIES": 4607613712, "TAURUS": 4607630788, "GEMINI": 4607611649, "CANCER": 4607612021, "LEO": 4607612403,
        "VIRGO": 4607612763, "LIBRA": 4607613155, "SCORPIO": 4607613471, "SAGITTARIUS": 4607711144, "CAPRICORN": 4607711484,
        "AQUARIUS": 4607711814, "PISCES": 4607712202}
KOTA_BASLA = 300           # Merkez 1 Kas: kalan kota 300'un altindaysa baslama
AI_KALIP = re.compile(r"(^|_)ai(_|$)|ai_generated|how_it|made_by|creation_method|production_method|is_ai", re.I)


class Salt(Etsy):
    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        if re.search(rf"/listings/{ST.ESKI_KOPYA}(/|$)", path):
            raise SystemExit(f"YASAK: {ST.ESKI_KOPYA} (Serdar: dokunma)")
        return super()._call(method, path, params=params, data=data, ok404=ok404, json_body=json_body)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def piksel_fark(a_bayt, b_yol):
    try:
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(io.BytesIO(a_bayt)).convert("RGB")).astype(np.int16)
        b = np.asarray(Image.open(b_yol).convert("RGB")).astype(np.int16)
        if a.shape != b.shape:
            return f"boyut farkli {a.shape[1]}x{a.shape[0]} / {b.shape[1]}x{b.shape[0]}"
        d = np.abs(a - b)
        return f"ayni boyut {a.shape[1]}x{a.shape[0]}; piksel fark ort {d.mean():.3f}, p99 {np.percentile(d, 99):.0f}, max {d.max()}"
    except Exception as e:  # noqa: BLE001
        return f"piksel karsilastirma yapilamadi {type(e).__name__}"


def nitelik(props):
    return sorted((p.get("property_id"), p.get("property_name"), tuple(p.get("values") or [])) for p in props)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", default="")
    ap.add_argument("--burclar", default="TUMU")
    a = ap.parse_args()
    if a.confirm != "OKU12":
        raise SystemExit("DUR: --confirm OKU12 yok")
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    bl = list(ILAN) if a.burclar == "TUMU" else [b.strip().upper() for b in a.burclar.split(",")]
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Salt(store)
    shop = os.environ["ETSY_SHOP_ID"]
    satirlar, ozet = [], dict(baslangic=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def yaz(ilan, madde, bek, oku, ok):
        satirlar.append(dict(ilan=ilan, madde=madde, beklenen=str(bek)[:600], okunan=str(oku)[:600],
                             sonuc="BILGI" if ok is None else ("PASS" if ok else "FAIL")))

    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    ozet["kota_once"] = api.remaining; ozet["kota_once_not"] = "ilk istegin (getShopSections) x-remaining-today basligi"
    if api.remaining is None or int(api.remaining) < KOTA_BASLA:
        ozet["dur"] = f"kalan kota {api.remaining} < {KOTA_BASLA}: baslamadi"
        json.dump(ozet, open(out / "OKU_OZET.json", "w"), indent=1, ensure_ascii=False)
        print(ozet["dur"]); return 5
    bolum_ad = {x.get("shop_section_id"): x.get("title") for x in secs}
    ozet["bolumler"] = [(x.get("shop_section_id"), x.get("title"), x.get("active_listing_count")) for x in secs]

    # sablon nitelikleri (ARIES, Serdar onayli)
    sablon_props = (api.get(f"/shops/{shop}/listings/{ST.SABLON}/properties") or {}).get("results") or []
    bek_nitelik = nitelik(sablon_props)
    occ = [v for (_, ad, v) in bek_nitelik if (ad or "").strip().lower() == "occasion"]
    stil_ad = [x[0] for x in ST.STILLER]
    boy_fiyat = dict(ST.BOYLAR)
    bolumler = {}
    ai_alanlar = {}
    for b in bl:
        lid = ILAN[b]; il = f"{b} {lid}"
        L = api.get(f"/listings/{lid}", params={"includes": "Images,Videos"}) or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
        try:
            per = api.get(f"/listings/{lid}/personalization", ok404=True) or {}
        except SystemExit as e:
            per = {"okunamadi": str(e)[:200]}
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
        json.dump(dict(listing=L, inventory=inv, properties=props, personalization=per, variation_images=vi),
                  open(out / f"HAM_{lid}.json", "w"), indent=1, ensure_ascii=False, default=str)
        m = ST.metin(b)
        # 1 state / fiyat / varyasyon / stil gorseli
        yaz(il, "1a state", "active", L.get("state"), L.get("state") == "active")
        urun = inv.get("products") or []
        tablo, fiyat_hata = [], []
        for p in urun:
            pv = {(v.get("property_name") or "").strip().lower(): (v.get("values") or [None])[0] for v in p.get("property_values") or []}
            of = (p.get("offerings") or [{}])[0]
            fy = ST.para(of.get("price"))
            tablo.append((pv.get("style"), pv.get("size"), fy, of.get("is_enabled")))
            if boy_fiyat.get(pv.get("size")) != fy or not of.get("is_enabled"):
                fiyat_hata.append((pv.get("style"), pv.get("size"), fy, of.get("is_enabled")))
        yaz(il, "1b fiyat (11 oz 12.90, 15 oz 16.90; tum urunler acik)", "16 urun, hata 0", f"{len(urun)} urun, hata {fiyat_hata}",
            len(urun) == ST.N_URUN and not fiyat_hata)
        stiller = sorted({t[0] for t in tablo}); boylar = sorted({t[1] for t in tablo})
        yaz(il, "1c varyasyon Stil x Boy", f"{len(stil_ad)} stil {sorted(stil_ad)} x {sorted(boy_fiyat)}",
            f"{len(stiller)} stil {stiller} x {boylar}", stiller == sorted(stil_ad) and boylar == sorted(boy_fiyat)
            and len({(t[0], t[1]) for t in tablo}) == ST.N_URUN)
        rank = {im.get("listing_image_id"): im.get("rank") for im in L.get("images") or []}
        bag = {v.get("value"): rank.get(v.get("image_id")) for v in vi}
        bek_bag = {ad: r for ad, _, r in ST.STILLER}
        yaz(il, "1d stil gorseli baglari (stil -> gorsel sirasi)", bek_bag, bag, bag == bek_bag)
        # 2 kisisellestirme
        q = (per.get("personalization_questions") if isinstance(per, dict) else None) or []
        q0 = q[0] if len(q) == 1 else {}
        yaz(il, "2a kisisellestirme acik", True, L.get("is_personalizable"), L.get("is_personalizable") is True and len(q) == 1)
        yaz(il, "2b kisisellestirme zorunlu", True, q0.get("required"), q0.get("required") is True)
        yaz(il, "2c talimat metni birebir", m["inst"], q0.get("instructions"), q0.get("instructions") == m["inst"])
        # 3 nitelikler
        ok3 = nitelik(props)
        yaz(il, "3 nitelikler (ARIES sablonu, Occasion Birthday)", bek_nitelik, ok3,
            ok3 == bek_nitelik and occ == [(ST.OCCASION,)])
        # 4 bolum
        sid = L.get("shop_section_id"); bolumler[b] = (sid, bolum_ad.get(sid))
        yaz(il, "4 magaza bolumu (id, ad)", f"ad '{ST.BOLUM_AD}'", f"{sid} '{bolum_ad.get(sid)}'", bolum_ad.get(sid) == ST.BOLUM_AD)
        # 5 alt metinler
        ims = sorted(L.get("images") or [], key=lambda x: x.get("rank") or 0)
        yaz(il, "5a gorsel sayisi (+ video)", f"{ST.N_GORSEL} gorsel + 1 video", f"{len(ims)} gorsel + {len(L.get('videos') or [])} video",
            len(ims) == ST.N_GORSEL and len(L.get("videos") or []) == 1)
        for im in ims:
            r_ = im.get("rank"); bek = m["alt"].get(r_); oku = im.get("alt_text")
            yaz(il, f"5b alt metin sira {r_}", bek, oku, oku == bek and oku is not None and len(oku) <= ST.ALT_MAX)
        # 6 kartlar (sha + piksel bilgi)
        gl, _ = ST.dosyalar(b)
        kok = Path(os.environ["IMG_ROOT"]) / b
        for i, ad in enumerate(gl, start=1):
            if "_K0" not in ad:
                continue
            im = next((x for x in ims if x.get("rank") == i), None)
            yerel = kok / ad
            if im is None or not yerel.is_file():
                yaz(il, f"6 kart {ad} (sira {i}) sha", "60 kart setindeki dosya", f"ilan gorseli {'yok' if im is None else 'var'}, "
                    f"yerel {'var' if yerel.is_file() else 'yok'}", False); continue
            try:
                rr = requests.get(im.get("url_fullxfull"), timeout=60); rr.raise_for_status(); bayt = rr.content
            except Exception as e:  # noqa: BLE001  (CDN; Etsy API kotasi degil)
                yaz(il, f"6 kart {ad} (sira {i}) sha", "indirme", f"CDN indirilemedi {type(e).__name__}", False); continue
            s_y, s_e = sha(yerel.read_bytes()), sha(bayt)
            yaz(il, f"6 kart {ad} (sira {i}) sha", s_y[:16], f"{s_e[:16]} ({piksel_fark(bayt, yerel)}; Etsy {len(bayt)} bayt / yerel "
                f"{yerel.stat().st_size} bayt)", s_y == s_e)
        # 7 AI / How it's made
        ai = {kk: vv for kk, vv in L.items() if AI_KALIP.search(kk)}
        ai_alanlar[b] = ai
        yaz(il, "7 AI / How it's made alani (API)", "alan var mi; deger", json.dumps(ai, ensure_ascii=False) if ai else
            f"API'de yok (listing anahtarlari: {len(L)}; ai/how_it/made_by kalibina uyan 0)", None)
        print(f"{b} tamam, istek {api.calls}, kalan {api.remaining}", flush=True)
    # 4b: 12 ilan ayni bolumde mi
    tek = sorted({v for v in bolumler.values()}, key=str)
    yaz("TUM", "4b 12 ilan ayni bolum", f"tek bolum '{ST.BOLUM_AD}'", tek, len(tek) == 1 and tek[0][1] == ST.BOLUM_AD)
    ozet.update(kota_sonra=api.remaining, istek=api.calls, bitis=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                pass_=sum(r["sonuc"] == "PASS" for r in satirlar), fail=sum(r["sonuc"] == "FAIL" for r in satirlar),
                fail_madde=sorted({r["madde"].split(" ")[0] for r in satirlar if r["sonuc"] == "FAIL"}), bolumler_ilan=bolumler,
                ai_alanlar=ai_alanlar, nitelik_kaynak=f"ARIES {ST.SABLON} (ayni kosuda okundu)", kart_kaynak="KART_KLASOR (Merkez 1 Kas tablosu)")
    with open(out / "OKU.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ilan", "madde", "beklenen", "okunan", "sonuc"]); w.writeheader(); w.writerows(satirlar)
    json.dump(ozet, open(out / "OKU_OZET.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps({k_: ozet[k_] for k_ in ("istek", "kota_once", "kota_sonra", "pass_", "fail", "fail_madde")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
