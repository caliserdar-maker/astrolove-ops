#!/usr/bin/env python3
"""POSTER aciklama YAZICISI, YALNIZ P1 KIPI (Etsy'ye YAZAR: yalniz EN aciklama + RU aciklama). Serdar 4 Kas PLAN_P1.md "A"
(dal p1-poster-yanitsiz docs/p1/PLAN_P1.md §3-§7), P1-K "A" (kota 20 + 10), P1-RU onayli (Serdar + Lena). 3 Kas yolu (POSTER_KURU_
20261103_220036, poster_metin_kuru.plan_ilan + DEG, YEDEK.json, 3 Kas geri alma) CIKARILDI.
Kuru plan: Drive TEMP/P1_KURU_20261104_1255 (kosu 41833440548): ONCE_SONRA.json + FARK.csv; sha256 SABIT (PLAN §6), farkliysa Etsy
isteginden ONCE DUR. Onayli metin = ONCE_SONRA "sonra"; onay ozeti = onay_ozet (FARK ile ayni olmali); yedek = ONCE_SONRA "yedek".
Ilan basina sira:
 1 kota: ilan baslamadan kalan >= ISTEK_ILAN (20) + KOTA_SINIRI (10) (Serdar P1-K "A"); her istekte etsy_common sert taban
 2 GET ilan; kalan okunamazsa DUR; state active degilse DUR (updateListing taslagi yayina alir)
 3 GET envanter + GET RU (/shops/{shop}/listings/{id}/translations/ru; beyan_marka_yaz.ru_gercek ile p1_poster_oku ayni)
 4 canli EN + RU (norm) = hedef -> ZATEN_YENI (yazim yok; son okuma ayni okumayla)
 5 canli ne kaynak ne hedef -> DUR (bayat / YARIM; EN ve RU ayri hedef / kaynak / farkli); baslik / etiket / malzeme / RU baslik /
   RU etiket yedekten farkli ya da RU baslik / etiket bos -> DUR
 6 uyarlayici: canli L / ru / envanterden p1_poster_oku ile ayni HAM kaydi kurulur -> p1_poster_kuru.plan_ilan; PLAN degilse ya da
   detay yoksa DUR; onay_ozet kuru ile birebir; yeniden kurulan metin = hedef. plan_ilan yan etkileri BILINCLI korunur:
   E.METIN_UYARI.clear() (metin kapisi sayaci ilan basina sifirlanir) ve R.izin_ver (RU_POSTER_IZIN; ru_yaz ayni metinle yeniden verir)
 7 DEGISIKLIK.csv'ye EN_BASLADI satiri (append + flush; iptal / zaman asiminda da kayit kalir) -> PATCH EN -> geri okuma (3 deneme)
 8 PUT RU (canli RU baslik + yeni aciklama + canli RU etiket; izin_ver + ru_yazim_kapisi) -> geri okuma (3 deneme)
 9 RU basarisiz -> canli RU okunur: yeni ise EN'ye dokunulmaz (TAMAM_HATALI); degilse EN yazimdan onceki metne geri yazilir, DUR
10 son okuma (PLAN §6): GET ilan + GET RU; tam metin = hedef, onay_ozet, baslik / etiket / malzeme / RU baslik / RU etiket = yedek,
   state active. DUR'da da (yazim denendiyse) kosar; EN ve RU ayri "hedef / kaynak / farkli" raporlar.
11 DEGISIKLIK.csv sonuc satiri. Parti: PARTI_BOYU 20 (77 ilan -> 20 / 20 / 20 / 17); parti sonunda tek satir rapor.
--geri-al (P1): EN = en_once, RU = ru_geri (= kur(EN once)); yalniz Serdar onayiyla (onay P1-METIN-GERI-<ids>).
Onay: --onay P1-METIN-<KURU|YAZ|GERI>-<ids> birebir; ids zorunlu. Herhangi DUR: sonraki ilan yazilmaz.
Kullanim: poster_metin_yaz.py --kuru DIR --ids 4570165628 --onay P1-METIN-YAZ-4570165628 --out DIR [--uygula] [--geri-al]"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
import poster_metin_kuru as P  # noqa: E402
import p1_poster_kuru as K  # noqa: E402
from beyan_marka_yaz import ru_gercek  # noqa: E402

ISTEK_ILAN = 20          # ilan basi butce (Serdar P1-K "A": kalan >= 20 + KOTA_SINIRI). Tipik 9 (sahte Etsy testi olcumu): 3 okuma + PATCH
#                          + 1 geri okuma + PUT + 1 geri okuma + son okuma 2. En kotu 20: 3 okuma + EN (PATCH + 3) + RU (PUT + 3) + RU basarisiz
#                          yolu (RU yeniden okuma en fazla 3 + EN geri PATCH + 3) + son okuma 2. etsy_common 5xx/429 yeniden gonderimleri
#                          (x3) ve 401 yenilemesi haric. Not: p1_poster_kuru ISTEK_TIPIK 7 / FARK tahmini_istek 7 geri okuma + son okumayi saymaz.
PARTI_BOYU = 20          # 77 ilan -> 20 / 20 / 20 / 17 (PLAN §3)
BEKLE_SN = 3
KURU_SHA = {"ONCE_SONRA.json": "56d86efaf7b32e7eec2ce7d1e44782eaac5d12cd3a36badf07e894af03843f9b",
            "FARK.csv": "c622807dc40f84b2cdcc9788f43f36b4073fa73806f0cd7732d5fdef2af7f065"}   # PLAN §6 (dal fa1fbcb0)
ALAN = ["listing_id", "parti", "url", "sonuc", "en_utc", "ru_utc", "geri_utc", "last_modified_timestamp", "son_okuma", "neden"]


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
    return ru_gercek(api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})


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


def durum(c, hedef, kaynak):
    return "hedef" if c == hedef else ("kaynak" if c == kaynak else "farkli")


def kota_kapisi(api, lid, kalan_istek=ISTEK_ILAN):
    api.kota_kapisi(f"ilan {lid}")
    if api.remaining is not None and int(api.remaining) < kalan_istek + E.KOTA_SINIRI:
        raise Dur(f"kota (yazim baslamadi): {lid} kalan {api.remaining} < {kalan_istek} + {E.KOTA_SINIRI}")


def hedefler(kp, geri):
    if geri:
        return (norm(kp["en_once"]), norm(kp["ru_geri"])), (norm(kp["en_sonra"]), norm(kp["ru_sonra"]))
    return (norm(kp["en_sonra"]), norm(kp["ru_sonra"])), (norm(kp["en_once"]), norm(kp["ru_once"]))


def son_okuma(L, ru, kp, geri):
    """PLAN §6 -> (PASS?, rapor). L / ru canli okuma."""
    (he, hr), (ke, kr) = hedefler(kp, geri)
    en_c, ru_c = norm(L.get("description")), norm(ru.get("description"))
    sorun = []
    de, dr = durum(en_c, he, ke), durum(ru_c, hr, kr)
    if de != "hedef":
        sorun.append(f"EN {de}")
    if dr != "hedef":
        sorun.append(f"RU {dr}")
    if R.onay_ozet(en_c, ru_c) != kp["once_ozet" if geri else "onay_ozet"]:   # PLAN §6: kuru (FARK) onay ozeti; geri-al: once_ozet
        sorun.append("onay ozeti kuru plandan farkli")
    sorun += ust_ayni(L, ru, kp["yedek"])
    if L.get("state") != "active":
        sorun.append(f"state {L.get('state')}")
    return not sorun, f"EN {de} / RU {dr}" + (f" | {'; '.join(sorun)}" if sorun else " | PASS")


def son_okuma_canli(api, shop, lid, kp, geri):
    L = api.get(f"/listings/{lid}") or {}
    return son_okuma(L, ru_oku(api, shop, lid), kp, geri), L


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


def uyarlayici(lid, L, ru, inv, shop):
    """Canli okumadan p1_poster_oku HAM kaydi (p1_poster_oku.py:105-110 ile ayni alanlar) -> p1_poster_kuru.plan_ilan."""
    kayit = dict(listing_id=lid,
                 listing={k: L.get(k) for k in ("listing_id", "state", "title", "description", "tags", "materials",
                                                 "last_modified_timestamp")},
                 inventory=inv, ru={k: ru.get(k) for k in ("title", "description", "tags")} if ru else None,
                 ru_durum="var" if ru else "yok")
    return K.plan_ilan(kayit, shop)


def isle(api, shop, lid, kuru, uygula, geri, kaydet):
    """-> kayit dict. Dur: kosu durur. kaydet(satir): DEGISIKLIK.csv'ye hemen ekler."""
    r = dict(listing_id=lid, url=f"https://www.etsy.com/listing/{lid}", sonuc="", en_utc="", ru_utc="", geri_utc="",
             last_modified_timestamp="", son_okuma="", neden="")
    if lid not in kuru:
        raise Dur(f"{lid}: kuru plan yok", dict(r, sonuc="DUR", neden="kuru plan yok"))
    kp = kuru[lid]
    kota_kapisi(api, lid)
    L = api.get(f"/listings/{lid}") or {}
    if api.remaining is None:   # ilk istekten once kalan bilinmez; ilk okumadan sonra kapi yeniden
        raise Dur(f"{lid}: x-remaining-today okunamadi; kota kapisi uygulanamaz")
    kota_kapisi(api, lid, ISTEK_ILAN - 1)
    if L.get("state") != "active":
        raise Dur(f"{lid}: state {L.get('state')} (active degil)")
    inv = api.get(f"/listings/{lid}/inventory") or {}
    ru = ru_oku(api, shop, lid)
    en_c, ru_c = norm(L.get("description")), norm(ru.get("description"))
    (he, hr), (ke, kr) = hedefler(kp, geri)
    if (en_c, ru_c) == (he, hr):
        ok, rap = son_okuma(L, ru, kp, geri)
        r.update(sonuc=("ZATEN_ESKI" if geri else "ZATEN_YENI") if ok else "DUR", son_okuma=rap,
                 last_modified_timestamp=L.get("last_modified_timestamp"))
        if not ok:
            raise Dur(f"{lid}: metin hedefte ama son okuma FAIL: {rap}", r)
        return r
    if (en_c, ru_c) != (ke, kr):
        de, dr = durum(en_c, he, ke), durum(ru_c, hr, kr)
        if "farkli" not in (de, dr):
            raise Dur(f"{lid}: YARIM durum (EN {de}, RU {dr}): onceki yazim yarim kalmis; bu arac toparlamaz, elle bakilir")
        raise Dur(f"{lid}: canli metin ne kuru 'once' ne 'sonra' (bayat): EN {de}, RU {dr}")
    if not ru.get("tags") or not norm(ru.get("title")):
        raise Dur(f"{lid}: canli RU baslik / etiket bos (PUT bunlari silebilir)")
    s = ust_ayni(L, ru, kp["yedek"])
    if s:
        raise Dur(f"{lid}: {s}")
    if geri:
        ru_k, kr_ = R.kur(he, {"boy": P.boylar(inv)})
        if not kr_.get("pass_") or norm(ru_k) != hr:
            raise Dur(f"{lid}: geri alma RU'su kur(EN once) ile kurulamiyor")
        yeni_en, yeni_ru, ru_kontrol = he, ru_k, kr_
    else:
        sat, d = uyarlayici(lid, L, ru, inv, shop)
        if sat.get("durum") != "PLAN" or d is None:
            raise Dur(f"{lid}: uyarlayici (p1_poster_kuru.plan_ilan) {sat.get('durum')}: {sat.get('neden')}")
        if d["onay_ozet"] != kp["onay_ozet"]:
            raise Dur(f"{lid}: onay ozeti farkli (Serdar onayli metin degil)")
        if (norm(d["en_sonra"]), norm(d["ru_sonra"])) != (he, hr):
            raise Dur(f"{lid}: yeniden kurulan metin kuru 'sonra' ile ayni degil")
        yeni_en, yeni_ru = d["en_sonra"], d["ru_sonra"]
        ru_kontrol = R.kur(yeni_en, {"boy": P.boylar(inv)})[1]
    if not uygula:
        r.update(sonuc="KURU"); return r
    kota_kapisi(api, lid, ISTEK_ILAN - 3)   # yazimdan hemen once (3 okuma yapildi)
    r["en_utc"] = simdi()
    kaydet(dict(r, sonuc="EN_BASLADI", neden="EN PATCH oncesi; sonuc satiri yoksa yazim yarim kalmis olabilir"))
    try:
        L1 = en_yaz(api, shop, lid, yeni_en, L)
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001  PATCH islenmis olabilir; kayit ilanla yazilir
        r.update(sonuc="FAIL", neden=f"EN yazimi / geri okuma hatasi ({type(e).__name__}: {str(e)[:150]}); EN yazilmis olabilir, RU "
                                     f"yazilmadi; ELLE BAKILMALI")
        raise Dur(f"{lid}: {r['neden']}", r) from e
    try:
        ru_yaz(api, shop, lid, yeni_ru, ru_kontrol, ru)
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001  RU basarisiz: canli RU yeniden okunur (plan §3.9)
        r["sonuc"] = "FAIL"
        r["neden"], lm, r["geri_utc"] = ru_basarisiz(api, shop, lid, e, L, ru, yeni_ru, P.norm(L.get("description")))
        r["last_modified_timestamp"] = lm or L1.get("last_modified_timestamp")
        if r["neden"].startswith("TAMAM_HATALI"):
            r.update(sonuc="TAMAM_HATALI", ru_utc=simdi())
        raise Dur(f"{lid}: {r['neden']}", r) from e
    r["ru_utc"] = simdi()
    try:
        (ok, rap), L2 = son_okuma_canli(api, shop, lid, kp, geri)
    except (SystemExit, Exception) as e:   # noqa: BLE001  EN + RU yazildi; son okuma yapilamadi
        r.update(sonuc="FAIL", son_okuma=f"okunamadi ({type(e).__name__})",
                 neden=f"EN + RU yazildi, son okuma yapilamadi ({str(e)[:150]}); ELLE BAKILMALI")
        raise Dur(f"{lid}: {r['neden']}", r) from e
    r.update(son_okuma=rap, last_modified_timestamp=L2.get("last_modified_timestamp") or L1.get("last_modified_timestamp"))
    if not ok:
        r.update(sonuc="FAIL", neden=f"son okuma FAIL: {rap}")
        raise Dur(f"{lid}: {r['neden']}", r)
    r["sonuc"] = "GERI_ALINDI" if geri else "PASS"
    return r


def ru_basarisiz(api, shop, lid, e, L, ru0, yeni_ru, eski_en):
    """RU yazimi hata verdi (plan §3.9). Canli RU okunur: yeni ise (PUT islenmis) EN'ye dokunulmaz (EN + RU yeni, tutarli);
    degilse EN yazimdan onceki metne geri yazilir. RU'ya ek yazim YOK. -> (neden, last_modified, geri_utc)"""
    hata = f"{type(e).__name__}: {str(e)[:150]}"
    ru_ust0 = (norm(ru0.get("title")), sorted(ru0.get("tags") or []))
    try:   # inceleme ORTA-2: Etsy geri okumasi gecikebilir; yeni RU en fazla 3 kez daha aranir (yanlislikla EN geri alinmasin)
        c, _ = tekrar_oku(lambda: ru_oku(api, shop, lid), lambda x: norm(x.get("description")) == norm(yeni_ru)
                          and (norm(x.get("title")), sorted(x.get("tags") or [])) == ru_ust0)
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


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def yukle(d, beklenen=None):
    """Kuru plan: ONCE_SONRA.json + FARK.csv; sha256 PLAN §6 sabitleriyle (ayri ayri) ayni degilse SystemExit (Etsy istegi yok).
    FARK onay_ozet = ONCE_SONRA onay_ozet olmali. -> {lid: kp} (kp["yedek"] dahil)"""
    d, bek = pathlib.Path(d), beklenen or KURU_SHA
    for ad, h in bek.items():
        f = d / ad
        if not f.is_file():
            raise SystemExit(f"DUR: kuru plan dosyasi yok: {ad}")
        g = sha(f)
        print(f"kuru plan {ad} sha256 {g}", flush=True)
        if g != h:
            raise SystemExit(f"DUR: {ad} sha256 farkli (beklenen {h[:12]}..., okunan {g[:12]}...); Etsy istegi yok")
    kuru = json.loads((d / "ONCE_SONRA.json").read_text(encoding="utf-8"))
    fark = {r["listing_id"]: r for r in csv.DictReader(open(d / "FARK.csv", encoding="utf-8"))}
    for lid, kp in kuru.items():
        f = fark.get(lid) or {}
        if f.get("onay_ozet") != kp.get("onay_ozet") or f.get("durum") != "PLAN" or "yedek" not in kp:
            raise SystemExit(f"DUR: kuru plan tutarsiz: {lid} (FARK onay_ozet / yedek)")
    return kuru


def onay_kontrol(onay, ids_metin, uygula, geri):
    """-> ids listesi; onay P1-METIN-<KURU|YAZ|GERI>-<ids> birebir, ids zorunlu; degilse SystemExit (Etsy istegi yok)."""
    if not re.fullmatch(r"[0-9]+(,[0-9]+)*", ids_metin or ""):
        raise SystemExit("DUR: ids bos ya da bicim hatali (virgullu rakam)")
    kip = "GERI" if (uygula and geri) else ("YAZ" if uygula else "KURU")
    if onay != f"P1-METIN-{kip}-{ids_metin}":
        raise SystemExit(f"DUR: onay girdisi P1-METIN-{kip}-<ids> degil")
    return ids_metin.split(",")


def calis(api, shop, ids, kuru, out, uygula, geri):
    eksik = [x for x in ids if x not in kuru]
    if eksik or len(set(ids)) != len(ids):   # inceleme D2: Etsy isteginden ONCE (77'lik listede k. id hatasi k-1 yazim birakmasin)
        raise SystemExit(f"DUR: ids kuru planda yok {eksik[:5]} ya da yinelenen id var; Etsy istegi yok")
    t0 = time.time()
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    yol = out / "DEGISIKLIK.csv"
    fh = open(yol, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, fieldnames=ALAN, lineterminator="\n", extrasaction="ignore", restval="")
    w.writeheader(); fh.flush()
    parti_n = (len(ids) + PARTI_BOYU - 1) // PARTI_BOYU
    sayac = dict(islenen=0, sonuc={})

    def kaydet(sat):
        w.writerow(sat); fh.flush(); os.fsync(fh.fileno())

    def parti_rapor(p, son=False):
        print(f"::notice title=P1-PARTI {p}/{parti_n}::islenen {sayac['islenen']}/{len(ids)} | "
              + " ".join(f"{k} {v}" for k, v in sorted(sayac["sonuc"].items())) + f" | istek {api.calls} kota {api.remaining}"
              + (" | DUR" if son else ""), flush=True)

    hata, lid, parti = None, "", 1
    try:
        for n, lid in enumerate(ids, 1):
            parti = (n - 1) // PARTI_BOYU + 1
            yazim = False
            try:
                r = isle(api, shop, lid, kuru, uygula, geri, lambda s: (kaydet(dict(s, parti=parti)), None)[1])
            except Dur as e:
                yazim = bool(e.kayit and e.kayit.get("en_utc"))
                kay = dict(e.kayit or dict(listing_id=lid, sonuc="DUR", neden=str(e)), parti=parti)
                if yazim and not kay.get("son_okuma"):   # DUR'da da son okuma (EN / RU ayri)
                    try:
                        (_, rap), _ = son_okuma_canli(api, shop, lid, kuru[lid], geri)
                        kay["son_okuma"] = rap
                    except (SystemExit, Exception) as e2:   # noqa: BLE001
                        kay["son_okuma"] = f"okunamadi ({type(e2).__name__})"
                kaydet(kay); sayac["islenen"] += 1
                sayac["sonuc"][kay.get("sonuc", "DUR")] = sayac["sonuc"].get(kay.get("sonuc", "DUR"), 0) + 1
                raise
            kaydet(dict(r, parti=parti)); sayac["islenen"] += 1
            sayac["sonuc"][r["sonuc"]] = sayac["sonuc"].get(r["sonuc"], 0) + 1
            gec = time.time() - t0; kal = gec / n * (len(ids) - n)
            print(f"[{n}/{len(ids)} %{100 * n // len(ids)} gecen {gec:.0f} sn kalan ~{kal:.0f} sn] parti {parti} {lid} {r['sonuc']} | "
                  f"{r.get('son_okuma', '')} | kota {api.remaining}", flush=True)
            if n % PARTI_BOYU == 0 or n == len(ids):
                parti_rapor(parti)
    except Dur as e:
        hata = str(e)
    except SystemExit as e:   # etsy_common kota tabani / HTTP hatasi / kapi
        hata = f"SystemExit: {e}"
        kaydet(dict(listing_id=lid, parti=parti, sonuc="DUR", neden=hata))
    except Exception as e:   # noqa: BLE001  ag hatasi vb.; kayit yine yazilir
        hata = f"{type(e).__name__}: {str(e)[:300]}"
        kaydet(dict(listing_id=lid, parti=parti, sonuc="DUR", neden=hata + " (EN yazilmis olabilir; canli okunmali)"))
    finally:
        fh.close()
    if hata:
        parti_rapor(parti, son=True)
    print(f"::notice title=P1-YAZ::{'GERI-AL ' if geri else ''}{'UYGULA' if uygula else 'KURU'} | islenen {sayac['islenen']} | "
          f"istek {api.calls} kota {api.remaining}" + (f" | DUR {hata}" if hata else ""), flush=True)
    if hata:
        raise SystemExit(f"DUR: {hata}")
    return list(csv.DictReader(open(yol, encoding="utf-8")))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", required=True); ap.add_argument("--ids", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--onay", required=True)
    ap.add_argument("--uygula", action="store_true"); ap.add_argument("--geri-al", action="store_true")
    a = ap.parse_args(argv)
    ids = onay_kontrol(a.onay, a.ids, a.uygula, a.geri_al)
    kuru = yukle(a.kuru)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    calis(E.Etsy(store), os.environ["ETSY_SHOP_ID"], ids, kuru, a.out, a.uygula, a.geri_al)


if __name__ == "__main__":
    main()
