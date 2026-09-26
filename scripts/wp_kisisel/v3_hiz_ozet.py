#!/usr/bin/env python3
"""GOREV_0014 dogrulama ozeti: duzeltmeler PASS/FAIL + once/sonra sure.

Bu betik KAPI GEVSETMEZ. Kapi 2 (halka/sembol) bilinen ve COZULMEMIS blokerdir
(RAPOR_0010: baski dosyasi 18x24'ten buyutuldugu icin; kisisel'in CANVA 24x32
plate'leri bekleniyor). Burada yalniz GOREV_0014'te istenen duzeltmeler
degerlendirilir; kapi 2'nin sonucu OLDUGU GIBI yazilir ve onceki olcumle
karsilastirilir - gecti sayilmaz.
"""
import argparse, json, sys
from pathlib import Path

KAPI2_TEMEL = {("BLUE", "Phone", "halka"): 13.0, ("BLUE", "Phone", "sembol"): 8.0,
               ("BLUE", "Tablet", "halka"): 125.8}      # RAPOR_0010, kosu 36233184110


def kapi_json(kok):
    y = sorted(Path(kok).rglob("WP_V2_KAPILAR.json"))
    if not y:
        raise SystemExit(f"HATA: {kok} altinda WP_V2_KAPILAR.json yok.")
    return [(p, json.loads(p.read_text())) for p in y]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yeni", required=True, help="yeni kodun cikti klasoru")
    ap.add_argument("--bekle-dosya", type=int, required=True)
    ap.add_argument("--once-sn", type=float, default=0.0)
    ap.add_argument("--sonra-sn", type=float, default=0.0)
    a = ap.parse_args()
    hata = []
    jpg = sorted(Path(a.yeni).rglob("AstroLove_*.jpg"))
    print(f"uretilen wallpaper: {len(jpg)} (beklenen {a.bekle_dosya})")
    if len(jpg) != a.bekle_dosya:
        hata.append(f"dosya sayisi {len(jpg)} != {a.bekle_dosya}")
    for p, K in kapi_json(a.yeni):
        ad = p.parent.name
        print(f"--- {ad}: gecti={K['gecti']}")
        bos = [x["kapi"] for x in K.get("bos_kapi", [])]
        if "halka_sembol" in bos and K.get("halka_sembol_atlanan"):
            # kapi 2 referansi (orijinal wallpaper) yok -> kapi 2 FAIL kalir (gevsetilmez);
            # bu GOREV_0014 duzeltmesinin hatasi degil, bilinen kapi 2 blokerinin parcasi
            bos.remove("halka_sembol")
            print(f"    KAPI 2 referansi yok -> kapi 2 FAIL (bos kapi artik gecti sayilmiyor): "
                  f"{len(K['halka_sembol_atlanan'])} cihaz")
        if bos:
            hata.append(f"{ad}: BOS KAPI {bos}")
        if K.get("eksik_dosya"):
            hata.append(f"{ad}: eksik/beklenmeyen dosya {len(K['eksik_dosya'])}")
        gp = K.get("geometri_paylasim", [])
        if not gp:
            hata.append(f"{ad}: geometri_paylasim olcumu yok")
        kot_gp = [x for x in gp if not x["gecti"]]
        print(f"    geometri_paylasim: {len(gp) - len(kot_gp)}/{len(gp)} gecti")
        if kot_gp:
            hata.append(f"{ad}: geometri paylasilmadi {kot_gp[:3]}")
        for k in ("ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz", "ek3_esit_bosluk",
                  "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
            kot = [x for x in K.get(k, []) if not x["gecti"]]
            print(f"    {k}: {len(K.get(k, [])) - len(kot)}/{len(K.get(k, []))} gecti")
            if kot:
                hata.append(f"{ad}: {k} FAIL {kot[:2]}")
        # KAPI 2: bilinen bloker - GEVSETILMEZ, oldugu gibi yazilir ve kiyaslanir
        k2 = K.get("halka_sembol", [])
        kot2 = [x for x in k2 if not x["gecti"]]
        print(f"    KAPI 2 (halka/sembol) - BILINEN BLOKER, COZULMEDI: "
              f"{len(k2) - len(kot2)}/{len(k2)} gecti")
        for x in kot2:
            anahtar = (x["edisyon"], x["cihaz"], x["oge"])
            temel = KAPI2_TEMEL.get(anahtar)
            dnm = "" if temel is None else f" (RAPOR_0010: {temel})"
            print(f"      {anahtar}: sapma {x['sapma_px']} px{dnm}")
            if temel is not None and abs(x["sapma_px"] - temel) > 0.1:
                print(f"      NOT: sapma degisti ({temel} -> {x['sapma_px']}) - raporlanacak")
    if a.once_sn and a.sonra_sn:
        print(f"SURE: once {a.once_sn:.0f} s, sonra {a.sonra_sn:.0f} s, "
              f"kazanc {100 * (1 - a.sonra_sn / a.once_sn):.0f}% "
              f"({a.once_sn / max(a.sonra_sn, 1e-9):.2f}x)")
    print(("### GOREV_0014 duzeltmeleri: PASS" if not hata
           else "### GOREV_0014 duzeltmeleri: FAIL"))
    for h in hata:
        print(f"  - {h}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
