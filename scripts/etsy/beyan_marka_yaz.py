#!/usr/bin/env python3
"""AI beyani + marka adi (RU aciklama) ilan yazimi (Serdar 22 Eki karari; 22 Eki gece B-1/B-2: yeni cumleler, uc aile).

EN beyan (aynen, B-1): BEYAN; eski poster cumlesi ESKI_BEYAN varsa kaldirilir (paragraf olarak). Yer (aileye gore, AILE):
  poster: 1. paragraftan sonra (1. paragraf CAPA["poster"] icermeli); kupa: 1. paragraftan sonra (1. paragraf CAPA["kupa"]);
  yil donumu: CAPA["yil"] iceren paragraftan sonra (tam 1 olmali). Kosul tutmazsa DUR. Zaten varsa eklenmez (idempotans).
RU beyan (aynen, B-2): RU_BEYAN, poster ve kupa RU aciklamasinda 1. paragraftan sonra (yil donumunde RU ceviri yok).
Marka: RU aciklamada Art'siz "AstroLove" -> "AstroLoveArt" (RU baslik ve etiketlere dokunulmaz; sayilari raporlanir).
Aile, ilanin magaza bolumunden (BOLUM_AILE).

Modlar:
  kuru (varsayilan, SALT OKUMA): tum aktif ilanlar (sayfali + /listings/batch Translations) -> aile basina plan sayilari
       (BEYAN_KURU.json). --ilan verilirse o ilanlarin EN/RU plani PLAN_<id>.txt. --gorsel-indir: --ilan galeri gorselleri
       (Etsy CDN, kota harcamaz) GORSEL_<id>/<rank>.jpg.
  yaz (--onay SERDAR_BEYAN_PILOT, yalniz 1 ilan): GET -> state active degilse DUR (CLAUDE.md 7 Eyl: updateListing taslagi yayina
       alir) -> yedek (ilan + RU ceviri + envanter) -> PATCH description (EN) -> PUT translations/ru (baslik ve etiketler aynen)
       -> geri okuma (en fazla 3 deneme, 10 sn): EN/RU beklenenle esit (html.unescape), state active, baslik/etiket/fiyat/adet ve
       RU baslik/etiket ayni, satilabilir teklif sayisi ayni -> PASS.
Kota tabani 10 (CLAUDE.md). Yanit govdeleri yalniz hata mesaji. Cikti: <out>/...; log'a ozet."""
import argparse
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

BEYAN = ("Every fusion symbol begins as an original AstroLoveArt design. We use AI tools to help create the artwork, "
         "and every design is reviewed and finished by us.")
ESKI_BEYAN = ("Each fusion symbol is an original AstroLoveArt design. We use AI tools to help render the gold surface finish, "
              "and every piece is reviewed and finished by us.")
RU_BEYAN = ("Каждый символ, объединяющий два знака зодиака, создаётся на основе оригинального дизайна AstroLoveArt. "
            "При создании изображений мы используем инструменты искусственного интеллекта, а затем сами проверяем и "
            "дорабатываем каждую работу.")
BOLUM_AILE = {"Zodiac Couple Posters": "poster", "Zodiac Couple Mugs": "kupa", "1st Anniversary Gifts": "yil"}
CAPA = {"poster": "Our original design joins your two zodiac symbols",
        "kupa": "your two zodiac symbols join into one original fusion symbol",
        "yil": "Every AstroLoveArt design merges two zodiac signs into one shared symbol"}
MARKA = re.compile(r"AstroLove(?!Art)")
TIRE = re.compile("[—–]")
ONAY = "SERDAR_BEYAN_PILOT"
KOTA_TABAN = 10
BEKLE_SN = 10


class Dur(Exception):
    pass


def kota(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")


def norm(s):
    return html.unescape(s or "").replace("\r\n", "\n")


def en_plan(desc, aile):
    """(yeni aciklama | None = degisiklik yok, not). Yer kosulu tutmazsa Dur."""
    if aile not in CAPA:
        raise Dur(f"aile bilinmiyor ({aile})")
    d = norm(desc)
    par = d.split("\n\n")
    eski = sum(p.strip() == ESKI_BEYAN for p in par)
    if ESKI_BEYAN in d and not eski:
        raise Dur("eski beyan ayri paragraf degil")
    par = [p for p in par if p.strip() != ESKI_BEYAN]
    if BEYAN in d:
        if eski:
            return "\n\n".join(par), "beyan var; eski beyan kaldirildi"
        return None, "beyan zaten var"
    if aile == "yil":
        i = [k for k, p in enumerate(par) if CAPA[aile] in p]
        if len(i) != 1:
            raise Dur(f"capa paragrafi {len(i)} kez (1 olmali)")
        k = i[0]
    else:
        if CAPA[aile] not in par[0] or sum(CAPA[aile] in p for p in par) != 1:
            raise Dur("1. paragraf capa icermiyor ya da capa birden cok")
        k = 0
    par.insert(k + 1, BEYAN)
    return "\n\n".join(par), (f"{k + 1}. paragraftan sonra eklendi" + ("; eski beyan kaldirildi" if eski else ""))


def ru_plan(desc, aile):
    """(yeni RU aciklama | None, Art'siz marka sayisi, not). Beyan poster ve kupada 1. paragraftan sonra."""
    d = norm(desc)
    n = len(MARKA.findall(d))
    yeni = MARKA.sub("AstroLoveArt", d)
    notu = f"marka {n}"
    if aile in ("poster", "kupa") and d.strip():
        if RU_BEYAN in yeni:
            notu += "; RU beyan zaten var"
        else:
            par = yeni.split("\n\n")
            if len(par) < 2:
                raise Dur("RU aciklamada paragraf yok (tek blok)")
            par.insert(1, RU_BEYAN)
            yeni = "\n\n".join(par)
            notu += "; RU beyan 1. paragraftan sonra"
    return (yeni if yeni != d else None), n, notu


def ru_ceviri(L):
    tr = L.get("translations") or []
    if isinstance(tr, dict):   # batch yaniti: {dil: ceviri} (marka_tara.py ile ayni)
        tr = list(tr.values())
    return next((t for t in tr if isinstance(t, dict) and t.get("language") == "ru"), None)


def satilabilir(inv):
    return sum(1 for p in (inv or {}).get("products") or [] for o in p.get("offerings") or []
               if o.get("is_enabled") and int(o.get("quantity") or 0) >= 1)


def korunan(L):
    return dict(title=norm(L.get("title")), tags=list(L.get("tags") or []), price=L.get("price"), quantity=L.get("quantity"),
                state=L.get("state"), listing_type=L.get("listing_type"), shipping_profile_id=L.get("shipping_profile_id"))


def aktif_idler(api, shop):
    ids, off = [], 0
    while True:
        r = api.get(f"/shops/{shop}/listings", {"state": "active", "limit": 100, "offset": off}) or {}
        sayfa = r.get("results") or []
        ids += [str(x["listing_id"]) for x in sayfa]
        kota(api)
        off += len(sayfa)
        if not sayfa or off >= int(r.get("count") or 0):
            return ids


def kuru(api, shop, a, out):
    bolum = {str(s["shop_section_id"]): s.get("title") for s in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    ids = aktif_idler(api, shop)
    ilan = []
    for k in range(0, len(ids), 100):
        r = api.get("/listings/batch", {"listing_ids": ",".join(ids[k:k + 100]), "includes": "Translations"}) or {}
        ilan += r.get("results") or []
        kota(api)
    satir, oz = [], {}
    for L in ilan:
        d = norm(L.get("description"))
        ru = ru_ceviri(L) or {}
        b = bolum.get(str(L.get("shop_section_id")), "?")
        aile = BOLUM_AILE.get(b, "?")
        try:
            en = "ekle" if en_plan(d, aile)[0] else "var"
        except Dur as e:
            en = f"DUR ({e})"
        try:
            rp = ru_plan(ru.get("description"), aile) if ru else (None, 0, "RU yok")
            rus = "RU yok" if not ru else ("yaz" if rp[0] else "degisiklik yok")
        except Dur as e:
            rp, rus = (None, 0, ""), f"DUR ({e})"
        x = dict(listing_id=L.get("listing_id"), bolum=b, aile=aile, state=L.get("state"), en_plan=en, ru_plan=rus,
                 beyan=d.count(BEYAN), eski_beyan=d.count(ESKI_BEYAN), en_marka=len(MARKA.findall(d)),
                 ru_aciklama_marka=rp[1], ru_beyan=norm(ru.get("description")).count(RU_BEYAN),
                 ru_baslik_marka=len(MARKA.findall(norm(ru.get("title")))),
                 ru_etiket_marka=sum(len(MARKA.findall(t)) for t in ru.get("tags") or []))
        satir.append(x)
        o = oz.setdefault(aile, dict(ilan=0, en_ekle=0, en_var=0, en_dur=0, eski_beyan=0, ru_yok=0, ru_yaz=0, ru_dur=0,
                                     ru_marka_ilan=0, ru_marka_toplam=0, ru_beyan_var=0, en_marka=0, ru_baslik_marka=0,
                                     ru_etiket_marka=0, state_disi=0))
        o["ilan"] += 1
        o["en_ekle"] += en == "ekle"; o["en_var"] += en == "var"; o["en_dur"] += en.startswith("DUR")
        o["eski_beyan"] += x["eski_beyan"] > 0
        o["ru_yok"] += rus == "RU yok"; o["ru_yaz"] += rus == "yaz"; o["ru_dur"] += rus.startswith("DUR")
        o["ru_marka_ilan"] += rp[1] > 0; o["ru_marka_toplam"] += rp[1]; o["ru_beyan_var"] += x["ru_beyan"] > 0
        o["en_marka"] += x["en_marka"] > 0
        o["ru_baslik_marka"] += x["ru_baslik_marka"]; o["ru_etiket_marka"] += x["ru_etiket_marka"]
        o["state_disi"] += L.get("state") != "active"
    (out / "BEYAN_KURU.json").write_text(json.dumps(dict(ozet=oz, ilanlar=satir), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"AKTIF {len(ilan)} ilan (liste {len(ids)})", flush=True)
    for b, o in sorted(oz.items()):
        print(f"AILE {b}: {json.dumps(o, ensure_ascii=False)}", flush=True)
    for x in satir:
        if x["en_plan"].startswith("DUR") or x["ru_plan"].startswith("DUR"):
            print(f"DUR ilan {x['listing_id']} ({x['aile']}): EN {x['en_plan']} | RU {x['ru_plan']}", flush=True)
    for lid in a.ilan:
        L = next((x for x in ilan if str(x.get("listing_id")) == lid), None)
        if not L:
            print(f"PLAN {lid}: aktif listede yok", flush=True); continue
        d = norm(L.get("description")); ru = ru_ceviri(L) or {}
        aile = BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id"))), "?")
        rapor = [f"ILAN {lid} | state {L.get('state')} | aile {aile}"]
        try:
            yeni, notu = en_plan(d, aile)
            rapor += [f"EN: {notu}"]
            if yeni:
                par = yeni.split("\n\n"); k = par.index(BEYAN)
                rapor += ["--- EN baglam (onceki paragraf / EKLENEN / sonraki paragraf) ---", par[k - 1], ">>> " + par[k],
                          par[k + 1] if k + 1 < len(par) else "(son)"]
        except Dur as e:
            rapor += [f"EN: DUR ({e})"]
        if ru:
            try:
                ry, n, rnot = ru_plan(ru.get("description"), aile)
                rapor += [f"RU: {rnot}; RU baslik marka {len(MARKA.findall(norm(ru.get('title'))))}, "
                          f"RU etiket marka {sum(len(MARKA.findall(t)) for t in ru.get('tags') or [])} (dokunulmaz)"]
                if ry:
                    par = ry.split("\n\n")
                    rapor += ["--- RU yeni ilk 3 paragraf ---"] + par[:3]
            except Dur as e:
                rapor += [f"RU: DUR ({e})"]
        else:
            rapor += ["RU: ceviri yok"]
        (out / f"PLAN_{lid}.txt").write_text("\n".join(rapor) + "\n", encoding="utf-8")
        print("\n".join(rapor), flush=True)
        if a.gorsel_indir:
            imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
            kota(api)
            g = out / f"GORSEL_{lid}"; g.mkdir(exist_ok=True)
            for im in imgs:
                with urllib.request.urlopen(urllib.request.Request(im["url_fullxfull"], headers={"User-Agent": "Mozilla/5.0"}),
                                            timeout=60) as r:
                    (g / f"{int(im['rank']):02d}_{im['listing_image_id']}.jpg").write_bytes(r.read())
            (g / "GORSELLER.json").write_text(json.dumps([{k: im.get(k) for k in ("rank", "listing_image_id", "full_width",
                                                            "full_height", "alt_text")} for im in imgs], ensure_ascii=False, indent=1),
                                              encoding="utf-8")
            print(f"GORSEL {lid}: {len(imgs)} gorsel indirildi", flush=True)


def yaz(api, shop, lid, out):
    L = api.get(f"/listings/{lid}", {"includes": "Translations"}) or {}
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    ru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    kota(api)
    (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(ilan=L, ru=ru, envanter=inv), ensure_ascii=False, indent=1), encoding="utf-8")
    if L.get("state") != "active":
        raise Dur(f"state {L.get('state')} (active degil): updateListing cagrilmaz")
    bolum = {str(s["shop_section_id"]): s.get("title") for s in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    aile = BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id"))), "?")
    en_yeni, en_not = en_plan(L.get("description"), aile)
    ru_yeni, ru_n, ru_not = ru_plan(ru.get("description"), aile) if ru else (None, 0, "RU yok")
    for yeni_, eski_ in ((en_yeni, L.get("description")), (ru_yeni, ru.get("description"))):
        if yeni_ and len(TIRE.findall(yeni_)) > len(TIRE.findall(norm(eski_))):
            raise Dur("yazim uzun/orta tire ekliyor")
    kota(api)   # taban 10 (CLAUDE.md); baska taban Serdar onayi olmadan konmaz
    k0, sat0 = korunan(L), satilabilir(inv)
    R = dict(ilan=lid, aile=aile, en=en_not, ru=ru_not, ru_marka_once=ru_n, ru_ceviri="var" if ru else "YOK (RU yazilmadi)", yazildi=[])
    if en_yeni:
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": en_yeni}); R["yazildi"].append("EN description (PATCH)")
    if ru_yeni:
        try:
            api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                    {"title": norm(ru.get("title")), "description": ru_yeni, "tags": ",".join(ru.get("tags") or [])})
            R["yazildi"].append("RU description (PUT translations/ru)")
        except SystemExit as e:   # etsy_common hatayi SystemExit("HATA: ...") ile bildirir; EN yazildi, RU yazilamadi
            R["ru_hata"] = str(e)[:300]
    bek_en = en_yeni if en_yeni else norm(L.get("description"))
    bek_ru = ru_yeni if ru_yeni and not R.get("ru_hata") else norm(ru.get("description"))
    for _ in range(3):
        y = api.get(f"/listings/{lid}") or {}
        yru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        if norm(y.get("description")) == bek_en and (not ru or norm(yru.get("description")) == bek_ru):
            break
        time.sleep(BEKLE_SN)
    inv1 = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    hata = [f"RU PUT hata: {R['ru_hata']}"] if R.get("ru_hata") else []
    if norm(y.get("description")) != bek_en:
        hata.append("EN aciklama beklenenle ayni degil")
    if ru and norm(yru.get("description")) != bek_ru:
        hata.append("RU aciklama beklenenle ayni degil")
    k1 = korunan(y)
    hata += [f"{k}: {k0[k]} -> {k1[k]}" for k in k0 if k0[k] != k1[k]]
    if ru and (norm(yru.get("title")) != norm(ru.get("title")) or list(yru.get("tags") or []) != list(ru.get("tags") or [])):
        hata.append("RU baslik/etiket degisti")
    if satilabilir(inv1) != sat0:
        hata.append(f"satilabilir teklif {sat0} -> {satilabilir(inv1)}")
    d1, r1 = norm(y.get("description")), norm(yru.get("description"))
    R["sonra"] = dict(state=y.get("state"), beyan=d1.count(BEYAN), eski_beyan=d1.count(ESKI_BEYAN), ru_beyan=r1.count(RU_BEYAN),
                      en_marka=len(MARKA.findall(d1)),
                      ru_marka=len(MARKA.findall(r1)), ru_astroloveart=r1.count("AstroLoveArt"), satilabilir=satilabilir(inv1),
                      tire=len(TIRE.findall(d1)))
    R["hata"], R["sonuc"] = hata, ("FAIL" if hata else "PASS")
    R["istek"], R["kota"] = api.calls, api.remaining
    (out / f"SONRA_{lid}.json").write_text(json.dumps(dict(ilan=y, ru=yru), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"SONUC_{lid}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SONUC", json.dumps(R, ensure_ascii=False), flush=True)
    return not hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kuru", "yaz"], default="kuru")
    ap.add_argument("--ilan", default="", help="virgullu ilan kimlikleri (yaz: tam 1)")
    ap.add_argument("--onay", default="")
    ap.add_argument("--gorsel-indir", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    a.ilan = [x for x in a.ilan.replace(" ", "").split(",") if x]
    if not all(x.isdigit() for x in a.ilan):
        raise SystemExit("DUR: --ilan yalniz rakam")
    if a.mod == "yaz" and (a.onay != ONAY or len(a.ilan) != 1):
        raise SystemExit(f"DUR: yaz icin --onay {ONAY} ve tam 1 ilan")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    if a.mod == "kuru":
        kuru(api, shop, a, out)
        print(f"KURU: yazma yok | istek {api.calls} | kota {api.remaining}", flush=True)
        return
    try:
        ok = yaz(api, shop, a.ilan[0], out)
    except Dur as e:
        print(f"DUR: {e} | yazma yapilmadi | istek {api.calls} | kota {api.remaining}", flush=True)
        sys.exit(3)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
