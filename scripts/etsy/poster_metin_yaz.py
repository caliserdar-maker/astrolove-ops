#!/usr/bin/env python3
"""POSTER aciklama YAZICISI (Etsy'ye YAZAR: yalniz EN aciklama + RU aciklama). Serdar 4 Kas "a": PLAN_POSTER_YAZIM.md onayli
(Drive TEMP/POSTER_KURU_20261103_220036; onayli metin = ONCE_SONRA.json "sonra", onay ozetleri = onay_ozet).
Tek kaynak: poster_metin_kuru.plan_ilan (yeni EN + RU + kapilar). Plan §3 ilan basina sira:
 1 kota: ilan baslamadan kalan >= ISTEK_ILAN (20; plan 13'ten SIKILASTIRILDI, inceleme 4 Kas) + KOTA_SINIRI; her istekte sert taban
 2 GET ilan; state active degilse DUR (updateListing taslagi yayina alir)
 3 GET envanter + GET RU (/shops/{shop}/listings/{id}/translations/ru)
 4 canli EN + RU (norm) = kuru "sonra" -> ZATEN_YENI (yazim yok)
 5 canli ne "once" ne "sonra" -> DUR (bayat); EN baslik/etiket/malzeme + RU baslik/etiket yedekle (YEDEK.json) ayni degilse DUR
 6 plan_ilan(canli) PASS + onay_ozet kuru (Serdar onayli) ile birebir; degilse DUR
 7 PATCH EN description -> geri okuma (3 deneme, norm) birebir + baslik/etiket/malzeme/state ayni
 8 PUT RU (canli RU baslik + yeni aciklama + canli RU etiket; izin_ver + ru_yazim_kapisi) -> geri okuma (norm) birebir
 9 RU basarisiz -> canli RU okunur: yeni ise EN'ye dokunulmaz (TAMAM_HATALI, tutarli); degilse EN yazimdan onceki metne geri
   yazilir + geri okuma, sonra DUR (plan §3.9). RU'ya ek geri yazma YOK (planda yok); RU ne yeni ne eski ise "ELLE BAKILMALI".
10 DEGISIKLIK.csv: ilan, EN UTC, RU UTC, last_modified_timestamp (Soru 13 A)
--geri-al: EN "once" + RU ru_geri (= ru_poster.kur(EN once); izin_ver bu metne) yazilir; canli zaten "once" ise ZATEN_ESKI.
Herhangi DUR: sonraki ilan yazilmaz. Kullanim: poster_metin_yaz.py --kuru DIR --ids 4570143815 --out DIR [--uygula] [--geri-al]"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
import poster_metin_kuru as P  # noqa: E402

ISTEK_ILAN = 20          # en kotu (inceleme 4 Kas): 3 okuma + EN (PATCH + 3 geri okuma) + RU (PUT + 3) = 11; RU basarisiz yolu: RU yeniden
#                          okuma 1 + EN geri yazma (PATCH + 3) = 5 -> 16; pay ile 20 (plan 13'ten sikilastirma). 5xx yeniden gonderimleri haric.
BEKLE_SN = 3


class Dur(Exception):
    def __init__(self, msg, kayit=None):
        super().__init__(msg); self.kayit = kayit


def norm(t):
    return P.norm(t).strip()


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tekrar_oku(fn, kosul, n=3):
    x = None
    for i in range(n):
        x = fn()
        if kosul(x):
            return x, True
        if i < n - 1:
            time.sleep(BEKLE_SN)
    return x, False


def ru_oku(api, shop, lid):
    return api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}


def ust_ayni(x, ru, y):
    """EN baslik/etiket/malzeme + RU baslik/etiket yedekle ayni mi -> sorun listesi"""
    s = []
    if x.get("title") != y.get("title"):
        s.append("EN baslik yedekten farkli")
    if sorted(x.get("tags") or []) != sorted(y.get("tags") or []):
        s.append("EN etiket yedekten farkli")
    if sorted(x.get("materials") or []) != sorted(y.get("materials") or []):
        s.append("EN malzeme yedekten farkli")
    yr = y.get("ru") or {}
    if norm(ru.get("title")) != norm(yr.get("title")):
        s.append("RU baslik yedekten farkli")
    if sorted(ru.get("tags") or []) != sorted(yr.get("tags") or []):
        s.append("RU etiket yedekten farkli")
    return s


def kota_kapisi(api, lid, kalan_istek=ISTEK_ILAN):
    api.kota_kapisi(f"ilan {lid}")
    if api.remaining is not None and int(api.remaining) < kalan_istek + E.KOTA_SINIRI:
        raise Dur(f"kota (yazim baslamadi): {lid} kalan {api.remaining} < {kalan_istek} + {E.KOTA_SINIRI}")


def en_yaz(api, shop, lid, metin, L0):
    api.patch(f"/shops/{shop}/listings/{lid}", {"description": metin})
    L1, ok = tekrar_oku(lambda: api.get(f"/listings/{lid}") or {}, lambda x: norm(x.get("description")) == norm(metin))
    if not ok:
        raise Dur("EN geri okuma plandan farkli")
    s = [k for k in ("title", "state") if L1.get(k) != L0.get(k)]
    s += [k for k in ("tags", "materials") if sorted(L1.get(k) or []) != sorted(L0.get(k) or [])]
    if s:
        raise Dur(f"EN yazimi sonrasi degisen alan: {s}")
    return L1


def ru_yaz(api, shop, lid, ru_metin, ru_kontrol, ru0):
    """izin_ver + kapi + PUT + geri okuma. Basarisizsa Dur."""
    R.izin_ver(lid, ru_metin, dict(ru_kontrol, sorunlar=""))
    govde = {"title": norm(ru0.get("title")), "description": ru_metin, "tags": ",".join(ru0.get("tags") or [])}
    E.ru_yazim_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru", data=govde)
    api.put(f"/shops/{shop}/listings/{lid}/translations/ru", govde)
    hedef = (norm(ru_metin), norm(ru0.get("title")), sorted(ru0.get("tags") or []))
    _, ok = tekrar_oku(lambda: ru_oku(api, shop, lid),
                       lambda x: (norm(x.get("description")), norm(x.get("title")), sorted(x.get("tags") or [])) == hedef)
    if not ok:
        raise Dur("RU geri okuma plandan farkli")


def isle(api, shop, lid, kuru, yedek, uygula, geri):
    """-> kayit dict. Dur: koşu durur."""
    r = dict(listing_id=lid, url=f"https://www.etsy.com/listing/{lid}", sonuc="", en_utc="", ru_utc="", geri_utc="", last_modified_timestamp="", neden="")
    if lid not in kuru or lid not in yedek:
        raise Dur(f"{lid}: kuru plan / yedek yok")
    kp, y = kuru[lid], yedek[lid]
    kota_kapisi(api, lid)
    L = api.get(f"/listings/{lid}") or {}
    if api.remaining is None:   # inceleme 4 Kas: ilk istekten once kalan bilinmez; ilk okumadan sonra kapi yeniden
        raise Dur(f"{lid}: x-remaining-today okunamadi; kota kapisi uygulanamaz")
    kota_kapisi(api, lid, ISTEK_ILAN - 1)
    if L.get("state") != "active":
        raise Dur(f"{lid}: state {L.get('state')} (active degil)")
    inv = api.get(f"/listings/{lid}/inventory") or {}
    ru = ru_oku(api, shop, lid)
    en_c, ru_c = norm(L.get("description")), norm(ru.get("description"))
    hedef_en, hedef_ru = (norm(kp["en_once"]), norm(kp["ru_geri"])) if geri else (norm(kp["en_sonra"]), norm(kp["ru_sonra"]))
    kaynak_en, kaynak_ru = (norm(kp["en_sonra"]), norm(kp["ru_sonra"])) if geri else (norm(kp["en_once"]), norm(kp["ru_once"]))
    if (en_c, ru_c) == (hedef_en, hedef_ru):
        r.update(sonuc="ZATEN_ESKI" if geri else "ZATEN_YENI", last_modified_timestamp=L.get("last_modified_timestamp"))
        return r
    if (en_c, ru_c) != (kaynak_en, kaynak_ru):
        dur = lambda c, h, kk: "hedef" if c == h else ("kaynak" if c == kk else "farkli")   # noqa: E731
        de, dr = dur(en_c, hedef_en, kaynak_en), dur(ru_c, hedef_ru, kaynak_ru)
        if "farkli" not in (de, dr):
            raise Dur(f"{lid}: YARIM durum (EN {de}, RU {dr}): onceki yazim yarim kalmis; bu arac toparlamaz, elle bakilir")
        raise Dur(f"{lid}: canli metin ne kuru 'once' ne 'sonra' (bayat): EN {de}, RU {dr}")
    if not ru.get("tags") or not norm(ru.get("title")):
        raise Dur(f"{lid}: canli RU baslik / etiket bos (PUT bunlari silebilir)")
    s = ust_ayni(L, ru, y)
    if s:
        raise Dur(f"{lid}: {s}")
    if geri:
        ru_k, kr = R.kur(hedef_en, {"boy": P.boylar(inv)})
        if not kr.get("pass_") or norm(ru_k) != hedef_ru:
            raise Dur(f"{lid}: geri alma RU'su kur(EN once) ile kurulamiyor")
        yeni_en, yeni_ru, ru_kontrol = hedef_en, ru_k, kr
    else:
        k, hata = P.plan_ilan(lid, L, ru, inv, shop)
        if hata:
            raise Dur(f"{lid}: plan_ilan FAIL: {hata}")
        if k["onay_ozet"] != kp["onay_ozet"]:
            raise Dur(f"{lid}: onay ozeti farkli (Serdar onayli metin degil)")
        if (norm(k["en_sonra"]), norm(k["ru_sonra"])) != (hedef_en, hedef_ru):
            raise Dur(f"{lid}: yeniden kurulan metin kuru 'sonra' ile ayni degil")
        yeni_en, yeni_ru = k["en_sonra"], k["ru_sonra"]
        ru_kontrol = R.kur(yeni_en, {"boy": P.boylar(inv)})[1]
    if not uygula:
        r.update(sonuc="KURU"); return r
    kota_kapisi(api, lid, ISTEK_ILAN - 3)   # yazimdan hemen once (3 okuma yapildi)
    r["en_utc"] = simdi()
    try:
        L1 = en_yaz(api, shop, lid, yeni_en, L)
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001  inceleme 2. tur: PATCH islenmis olabilir; kayit ilanla yazilir
        r.update(sonuc="FAIL", neden=f"EN yazimi / geri okuma hatasi ({type(e).__name__}: {str(e)[:150]}); EN yazilmis olabilir, RU "
                                     f"yazilmadi; ELLE BAKILMALI")
        raise Dur(f"{lid}: {r['neden']}", r) from e
    try:
        ru_yaz(api, shop, lid, yeni_ru, ru_kontrol, ru)
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001  RU basarisiz (inceleme 4 Kas KRITIK 2): canli RU yeniden okunur
        r["sonuc"] = "FAIL"
        r["neden"], lm, r["geri_utc"] = ru_basarisiz(api, shop, lid, e, L, ru, yeni_ru, P.norm(L.get("description")))
        r["last_modified_timestamp"] = lm or L1.get("last_modified_timestamp")
        if r["neden"].startswith("TAMAM_HATALI"):
            r.update(sonuc="TAMAM_HATALI", ru_utc=simdi())
        raise Dur(f"{lid}: {r['neden']}", r) from e
    r["ru_utc"] = simdi()
    r.update(sonuc="GERI_ALINDI" if geri else "PASS", last_modified_timestamp=L1.get("last_modified_timestamp"))
    return r


def ru_basarisiz(api, shop, lid, e, L, ru0, yeni_ru, eski_en):
    """RU yazimi hata verdi (plan §3.9). Canli RU okunur: yeni ise (PUT islenmis) EN'ye dokunulmaz (EN + RU yeni, tutarli);
    degilse EN yazimdan onceki metne geri yazilir. RU'ya ek yazim YOK. -> (neden, last_modified, geri_utc)"""
    hata = f"{type(e).__name__}: {str(e)[:150]}"
    try:
        c = ru_oku(api, shop, lid)
    except (SystemExit, Exception) as e1:   # noqa: BLE001
        return f"RU basarisiz ({hata}); RU yeniden okunamadi ({str(e1)[:80]}); EN'ye dokunulmadi, ELLE BAKILMALI", "", ""
    ru_ust = norm(c.get("title")) == norm(ru0.get("title")) and sorted(c.get("tags") or []) == sorted(ru0.get("tags") or [])
    if norm(c.get("description")) == norm(yeni_ru) and ru_ust:
        return f"TAMAM_HATALI: RU hata verdi ({hata}) ama canli RU yeni; EN + RU yeni ve tutarli, geri yazma yok", "", ""
    ru_durum = "RU yazimdan onceki metinde" if norm(c.get("description")) == norm(ru0.get("description")) and ru_ust \
        else "RU ne yeni ne eski: ELLE BAKILMALI"
    try:
        L2 = en_yaz(api, shop, lid, eski_en, L)
    except (Dur, SystemExit, Exception) as e2:   # noqa: BLE001
        return f"RU basarisiz ({hata}); {ru_durum}; EN GERI YAZMA BASARISIZ ({str(e2)[:120]}); ELLE BAKILMALI", "", ""
    return f"RU basarisiz ({hata}); {ru_durum}; EN yazimdan onceki metne geri yazildi", L2.get("last_modified_timestamp"), simdi()


def yukle(d):
    d = pathlib.Path(d)
    return json.loads((d / "ONCE_SONRA.json").read_text()), json.loads((d / "YEDEK.json").read_text())


def calis(api, shop, ids, kuru, yedek, out, uygula, geri):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    sonuc, hata = [], None
    try:
        for n, lid in enumerate(ids, 1):
            r = isle(api, shop, lid, kuru, yedek, uygula, geri)
            sonuc.append(r)
            print(f"[{n}/{len(ids)}] {lid} {r['sonuc']} | kota {api.remaining}", flush=True)
    except Dur as e:
        hata = str(e)
        sonuc.append(e.kayit or dict(listing_id="", sonuc="DUR", neden=hata))
    except SystemExit as e:   # etsy_common kota tabani / HTTP hatasi / kapi
        hata = f"SystemExit: {e}"
        sonuc.append(dict(listing_id="", sonuc="DUR", neden=hata))
    except Exception as e:   # noqa: BLE001  inceleme 4 Kas ORTA 5: ag hatasi vb.; kayit yine yazilir
        hata = f"{type(e).__name__}: {str(e)[:300]}"
        sonuc.append(dict(listing_id="", sonuc="DUR", neden=hata + " (EN yazilmis olabilir; canli okunmali)"))
    with open(out / "DEGISIKLIK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "url", "sonuc", "en_utc", "ru_utc", "geri_utc", "last_modified_timestamp", "neden"],
                           lineterminator="\n", extrasaction="ignore", restval="")
        w.writeheader(); w.writerows(sonuc)
    print(f"::notice title=POSTER-YAZ::{'GERI-AL ' if geri else ''}{'UYGULA' if uygula else 'KURU'} | islenen {len(sonuc)} | "
          f"istek {api.calls} kota {api.remaining}" + (f" | DUR {hata}" if hata else ""), flush=True)
    if hata:
        raise SystemExit(f"DUR: {hata}")
    return sonuc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", required=True); ap.add_argument("--ids", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--uygula", action="store_true"); ap.add_argument("--geri-al", action="store_true")
    a = ap.parse_args(argv)
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    kuru, yedek = yukle(a.kuru)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    calis(E.Etsy(store), os.environ["ETSY_SHOP_ID"], ids, kuru, yedek, a.out, a.uygula, a.geri_al)


if __name__ == "__main__":
    main()
