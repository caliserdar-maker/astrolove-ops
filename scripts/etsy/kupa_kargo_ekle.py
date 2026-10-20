#!/usr/bin/env python3
""""Kupa Free US UK EU" kargo profiline (318301958420) Kanada ve Avustralya hedefi ekler (Serdar onayi 20 Eki 2026).
Mevcut US / GB / eu hedefleri, profil alanlari (ad, cikis, hazirlik suresi), ilanlar, baslik, fiyat, etiket DEGISMEZ.
Yeni hedef: ucret, ikinci urun ucreti, shipping_carrier_id ve mail_class mevcut 3 hedeften kopyalanir (3'u ayni degilse DUR);
teslim gunu --ca / --au (MIN-MAX, is gunu; Etsy'de hazirlik suresi profilde ayri, degismez).
  --mod kuru : SALT OKUMA. Kota, profil, 78 kupa ilaninin profili (1 batch), plan. YEDEK.json yazilir.
  --mod yaz  : ETSY'YE YAZAR (--confirm KUPA_CA_AU). Profil yeniden okunur, YEDEK_YAZ_ONCE.json (Drive'da boyut dogrulanir)
               -> on kosullar (yalniz US/GB/eu, CA/AU yok, kuru YEDEK'ten beri degismemis) -> POST destinations x2
               -> geri okuma: 5 hedef, eski 3 hedef imzasi birebir, CA/AU beklenen degerler, profil alanlari ayni,
               78 ilan hala bu profilde. Ilk FAIL'de DUR (geri alma: eklenen hedef DELETE, elle/onayla).
Kota tabani 10, cagri siniri 20. Cikti: OUT/YEDEK.json (kuru) | YEDEK_YAZ_ONCE.json + SONRA.json (yaz), OUT/OZET.txt
Kullanim: kupa_kargo_ekle.py --mod kuru|yaz --liste KUPA_TASLAK_LISTE.csv --ca 4-7 --au 5-9 --out OUT
          [--confirm KUPA_CA_AU] [--kuru-yedek YEDEK.json] [--yedek-drive gdrive:...]"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PID = 318301958420
AD = "Kupa Free US UK EU"
KOTA_TABAN, CAGRI_SINIRI = 10, 20
ESKI = {"US", "GB", "EU"}
YENI = ("CA", "AU")
PROFIL_ALAN = ("title", "origin_country_iso", "origin_postal_code", "min_processing_days", "max_processing_days",
               "processing_days_display_label", "domestic_handling_fee", "international_handling_fee")


def anahtar(x):
    cc = (x.get("destination_country_iso") or "").upper()
    return cc or ((x.get("destination_region") or "none").upper())


def para(v):
    if isinstance(v, dict):
        return round(v.get("amount", 0) / (v.get("divisor") or 1), 2)
    return v


def imza(x):
    return (anahtar(x), para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"),
            x.get("max_delivery_days"), x.get("shipping_carrier_id"), x.get("mail_class"), x.get("shipping_profile_destination_id"))


def aralik(s):
    a, b = (int(v) for v in s.split("-"))
    if not 1 <= a <= b <= 45:
        raise SystemExit(f"HATA: teslim gunu {s} (1 <= min <= max <= 45)")
    return a, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["kuru", "yaz"]); ap.add_argument("--out", required=True)
    ap.add_argument("--liste", required=True); ap.add_argument("--ca", required=True); ap.add_argument("--au", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--kuru-yedek", default=""); ap.add_argument("--yedek-drive", default="")
    ap.add_argument("--sahte", default="", help="yerel test: sahte API modulu yolu")
    a = ap.parse_args()
    gun = {"CA": aralik(a.ca), "AU": aralik(a.au)}
    yaz = a.mod == "yaz"
    if yaz and a.confirm != "KUPA_CA_AU":
        raise SystemExit("HATA: --mod yaz icin --confirm KUPA_CA_AU gerekir. YAZMA YOK.")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    O = [f"KUPA KARGO CA + AU ({a.mod}) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} | profil {PID} '{AD}'"]

    def log(m):
        print(m, flush=True); O.append(m)

    def bitir(kod=0, neden=""):
        if neden:
            log(neden)
        log(f"Etsy cagrisi {api.calls} | kota son {api.remaining}")
        (out / "OZET.txt").write_text("\n".join(O) + "\n")
        if kod:
            raise SystemExit(neden or "DUR")
        return 0

    if a.sahte:
        import importlib.util
        sp = importlib.util.spec_from_file_location("sahte", a.sahte); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        api, shop = m.Sahte(), "1"
    else:
        from etsy_common import Etsy, TokenStore, mask
        k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(k); mask(s)
        st = TokenStore(os.environ["TOKEN_FILE"], k, s)
        if st.needs_refresh():
            st.refresh()
        api, shop = Etsy(st), os.environ["ETSY_SHOP_ID"]

    def kota():
        if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
            bitir(1, f"DUR: kota {api.remaining} < {KOTA_TABAN}")
        if api.calls >= CAGRI_SINIRI:
            bitir(1, f"DUR: cagri siniri {CAGRI_SINIRI}")

    ids = [r["listing_id"].strip() for r in csv.DictReader(open(a.liste, encoding="utf-8-sig")) if r.get("listing_id", "").strip()]
    if len(ids) != 78:
        bitir(1, f"DUR: kupa listesinde {len(ids)} ilan (78 bekleniyordu)")
    api.get(f"/shops/{shop}"); log(f"kota basta {api.remaining} | taban {KOTA_TABAN} | cagri siniri {CAGRI_SINIRI}"); kota()

    def profil():
        kota(); return api.get(f"/shops/{shop}/shipping-profiles/{PID}") or {}

    def ilanlar():
        kota(); R = (api.get("/listings/batch", params={"listing_ids": ",".join(ids)}) or {}).get("results") or []
        return {str(x["listing_id"]): x for x in R}

    P0 = profil()
    (out / ("YEDEK_YAZ_ONCE.json" if yaz else "YEDEK.json")).write_text(json.dumps(P0, ensure_ascii=False, indent=1))
    H0 = P0.get("shipping_profile_destinations") or []
    log(f"Profil: '{P0.get('title')}' cikis {P0.get('origin_country_iso')} {P0.get('origin_postal_code')} | hazirlik "
        f"{P0.get('min_processing_days')}-{P0.get('max_processing_days')} ({P0.get('processing_days_display_label')})")
    for x in H0:
        log(f"  hedef {anahtar(x)}: ucret {para(x.get('primary_cost'))}/{para(x.get('secondary_cost'))} | teslim "
            f"{x.get('min_delivery_days')}-{x.get('max_delivery_days')} gun | carrier {x.get('shipping_carrier_id')} | mail_class {x.get('mail_class')}")
    L0 = ilanlar()
    bu = [i for i in ids if str((L0.get(i) or {}).get("shipping_profile_id")) == str(PID)]
    log(f"78 kupa ilani: okunan {len(L0)}, bu profilde {len(bu)}; durum {sorted({(L0.get(i) or {}).get('state') for i in ids} - {None})}")

    sorun = []
    if P0.get("title") != AD:
        sorun.append(f"profil adi '{P0.get('title')}'")
    var = {anahtar(x) for x in H0}
    if var != ESKI:
        sorun.append(f"mevcut hedefler {sorted(var)} (beklenen {sorted(ESKI)})")
    tas = {(para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("shipping_carrier_id"), x.get("mail_class")) for x in H0}
    if len(tas) != 1:
        sorun.append(f"mevcut hedeflerin ucret/tasiyici bilgisi farkli: {tas}")
    if len(bu) != 78:
        sorun.append(f"bu profilde {len(bu)}/78 kupa ilani")
    if a.kuru_yedek and os.path.exists(a.kuru_yedek):
        K = json.load(open(a.kuru_yedek))
        if sorted(imza(x) for x in K.get("shipping_profile_destinations") or []) != sorted(imza(x) for x in H0) or \
                any(K.get(f) != P0.get(f) for f in PROFIL_ALAN):
            sorun.append("profil kuru yedekten (YEDEK.json) sonra degismis")
    ucret1, ucret2, car, mc = next(iter(tas)) if len(tas) == 1 else (None, None, None, None)
    plan = []
    for cc in YENI:
        b = {"destination_country_iso": cc, "primary_cost": ucret1, "secondary_cost": ucret2,
             "min_delivery_days": gun[cc][0], "max_delivery_days": gun[cc][1]}
        if car is not None:
            b["shipping_carrier_id"] = car
        if mc:
            b["mail_class"] = mc
        plan.append(b)
        log(f"PLAN {cc}: {json.dumps(b)}")
    if sorun:
        bitir(1, "DUR (on kosul): " + "; ".join(sorun) + ". YAZMA YOK.")
    if not yaz:
        log("KURU: Etsy'ye yazma yok. On kosullar PASS.")
        return bitir()

    if a.yedek_drive:
        f = out / "YEDEK_YAZ_ONCE.json"
        r = subprocess.run(["rclone", "copyto", str(f), f"{a.yedek_drive}/{f.name}"], capture_output=True, text=True)
        c = subprocess.run(["rclone", "size", "--json", f"{a.yedek_drive}/{f.name}"], capture_output=True, text=True)
        if r.returncode or c.returncode or json.loads(c.stdout or "{}").get("bytes") != f.stat().st_size:
            bitir(1, "DUR: yedek Drive'da dogrulanamadi. YAZMA YOK.")
        log(f"yedek Drive'da dogrulandi: {a.yedek_drive}/{f.name}")
    eski_imza = sorted(imza(x) for x in H0)
    for b in plan:
        kota()
        r = api.post(f"/shops/{shop}/shipping-profiles/{PID}/destinations", b) or {}
        log(f"POST {b['destination_country_iso']}: destination_id {r.get('shipping_profile_destination_id')}")
    P1 = {}
    for _ in range(3):
        time.sleep(3)
        P1 = profil()
        if {anahtar(x) for x in P1.get("shipping_profile_destinations") or []} >= ESKI | set(YENI):
            break
    (out / "SONRA.json").write_text(json.dumps(P1, ensure_ascii=False, indent=1))
    H1 = P1.get("shipping_profile_destinations") or []
    k = []
    if sorted(anahtar(x) for x in H1) != sorted(ESKI | set(YENI)):
        k.append(f"hedefler {sorted(anahtar(x) for x in H1)}")
    if sorted(imza(x) for x in H1 if anahtar(x) in ESKI) != eski_imza:
        k.append("eski US/GB/EU hedefleri degisti")
    for cc in YENI:
        y = [x for x in H1 if anahtar(x) == cc]
        bek = (cc, ucret1, ucret2, gun[cc][0], gun[cc][1], car, mc)
        if len(y) != 1 or imza(y[0])[:7] != bek:
            k.append(f"{cc} beklenen {bek}, okunan {[imza(x)[:7] for x in y]}")
    for f in PROFIL_ALAN:
        if P1.get(f) != P0.get(f):
            k.append(f"profil alani degisti: {f}")
    L1 = ilanlar()
    bu1 = [i for i in ids if str((L1.get(i) or {}).get("shipping_profile_id")) == str(PID)]
    if len(bu1) != 78:
        k.append(f"bu profilde {len(bu1)}/78 kupa ilani")
    degisen = [i for i in ids if any((L0.get(i) or {}).get(f) != (L1.get(i) or {}).get(f) for f in ("title", "tags", "price", "state"))]
    if degisen:
        k.append(f"ilan baslik/etiket/fiyat/durum degisti: {degisen[:5]}")
    log("GERI OKUMA: " + ("PASS (5 hedef; US/GB/EU birebir ayni; CA/AU beklenen; profil alanlari ayni; 78/78 ilan bu profilde; "
                          "baslik/etiket/fiyat/durum degismedi)" if not k else "FAIL " + "; ".join(k)))
    for x in H1:
        log(f"  SONRA {anahtar(x)}: ucret {para(x.get('primary_cost'))}/{para(x.get('secondary_cost'))} | teslim "
            f"{x.get('min_delivery_days')}-{x.get('max_delivery_days')} | carrier {x.get('shipping_carrier_id')} | mail_class {x.get('mail_class')}")
    return bitir(1 if k else 0, "DUR: geri okuma FAIL" if k else "")


if __name__ == "__main__":
    sys.exit(main())
