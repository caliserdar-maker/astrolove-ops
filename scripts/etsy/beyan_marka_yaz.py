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
Kota: etsy_common esigi (genel 481/430, CLAUDE.md 23 Eki) + yerel taban 10 (esik pasifse). Yanit govdeleri yalniz hata mesaji. Cikti: <out>/...; log'a ozet."""
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
ONAY_TOPLU = "SERDAR_BEYAN_TOPLU"
KOTA_TABAN = 10
BEKLE_SN = 10


class Dur(Exception):
    pass


def kota(api):
    if api.remaining is None or int(api.remaining) < KOTA_TABAN:
        raise Dur(f"kota {api.remaining} < {KOTA_TABAN} (ya da x-remaining-today okunamadi)")


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
    if aile in ("poster", "kupa") and not d.strip():
        raise Dur("RU ceviri var ama RU aciklama bos (beyan yeri yok)")
    if aile in ("poster", "kupa"):
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


def teklif_imza(inv):
    """Satilabilir teklifin tam imzasi (urun, teklif, fiyat, acik, stok var): sayi esit kalip icerik degisirse yakalanir."""
    return sorted((p.get("product_id"), o.get("offering_id"), json.dumps(o.get("price"), sort_keys=True), bool(o.get("is_enabled")),
                   int(o.get("quantity") or 0) >= 1, bool(o.get("is_deleted")))
                  for p in (inv or {}).get("products") or [] for o in p.get("offerings") or [])


def satilabilir(inv):
    return sum(1 for p in (inv or {}).get("products") or [] for o in p.get("offerings") or []
               if o.get("is_enabled") and int(o.get("quantity") or 0) >= 1)


KISISEL_ALAN = ("is_personalizable", "personalization_is_required", "personalization_char_count_max", "personalization_instructions")


def ru_gercek(ru):
    """translations/ru tekil GET'i ceviri yokken de bos bir kayit donebiliyor (23 Eki yil donumu 4595350971): baslik ya da aciklama
    yoksa RU YOK sayilir."""
    return ru if isinstance(ru, dict) and (norm(ru.get("title")).strip() or norm(ru.get("description")).strip()) else {}


def ortak(L):
    """Uretim ortaklari (id, ad, konum); None = API yanitinda alan yok (burc_gift_yaz.partner_ids ile ayni ayrim)."""
    if "production_partners" not in L:
        return None
    return sorted((p.get("production_partner_id"), p.get("partner_name"), p.get("location")) for p in L.get("production_partners") or [])


def korunan(L):
    """Yazimda DEGISMEMESI gereken ilan alanlari (Serdar 23 Eki kapi 1b)."""
    k = dict(title=norm(L.get("title")), tags=list(L.get("tags") or []), price=L.get("price"), quantity=L.get("quantity"),
             state=L.get("state"), listing_type=L.get("listing_type"), shipping_profile_id=L.get("shipping_profile_id"),
             return_policy_id=L.get("return_policy_id"), uretim_ortagi=ortak(L))
    k.update({a: L.get(a) for a in KISISEL_ALAN})
    return k


def kisisel_sorular(api, shop, lid, L):
    """Kisisellestirme sorulari: /listings/{id}/personalization (burc_gift_yaz.kisisel), yoksa ilan alani (ayar77_kuru.sorular_of),
    yoksa /shops/{shop}/listings/{id}/personalization (ayar77_kuru.py:295). Hicbiri yoksa None."""
    q = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions")
    if not isinstance(q, list):
        q = L.get("personalization_questions")
        p = L.get("personalization")
        if not isinstance(q, list) and isinstance(p, dict):
            q = p.get("personalization_questions")
    if not isinstance(q, list):
        q = (api.get(f"/shops/{shop}/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions")
    return q if isinstance(q, list) else None


def ru_tekil(api, shop, lid):
    """RU ceviri: tekil GET (yazim ve geri okuma ile ayni kaynak; batch'e guvenilmez, inceleme 23 Eki A1)."""
    return ru_gercek(api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})


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
    satir, oz, ortaklar = [], {}, {}
    for L in ilan:
        d = norm(L.get("description"))
        b = bolum.get(str(L.get("shop_section_id")), "?")
        aile = BOLUM_AILE.get(b, "?")
        if aile in ("poster", "kupa"):   # RU yazimla ayni kaynaktan (tekil GET); batch ceviri ile uyusmazlik sayilir
            ru = ru_tekil(api, shop, str(L["listing_id"])); kota(api)
            ru_batch_uyusmaz = bool(ru) != bool(ru_gercek(ru_ceviri(L)))
        else:
            ru, ru_batch_uyusmaz = ru_gercek(ru_ceviri(L)), False
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
                 ru_etiket_marka=sum(len(MARKA.findall(t)) for t in ru.get("tags") or []), uretim_ortagi=ortak(L),
                 kisisel={k: L.get(k) for k in KISISEL_ALAN}, ru_batch_uyusmaz=ru_batch_uyusmaz)
        satir.append(x)
        po = ortaklar.setdefault(aile, {})
        anahtar = "ALAN YOK" if x["uretim_ortagi"] is None else (" | ".join(f"{i} {n} ({c})" for i, n, c in x["uretim_ortagi"]) or "BOS")
        po[anahtar] = po.get(anahtar, 0) + 1
        o = oz.setdefault(aile, dict(ilan=0, en_ekle=0, en_var=0, en_dur=0, eski_beyan=0, ru_yok=0, ru_yaz=0, ru_dur=0,
                                     ru_marka_ilan=0, ru_marka_toplam=0, ru_beyan_var=0, en_marka=0, ru_baslik_marka=0,
                                     ru_etiket_marka=0, state_disi=0, ru_batch_uyusmaz=0, kisisel_acik=0))
        o["ilan"] += 1
        o["en_ekle"] += en == "ekle"; o["en_var"] += en == "var"; o["en_dur"] += en.startswith("DUR")
        o["eski_beyan"] += x["eski_beyan"] > 0
        o["ru_yok"] += rus == "RU yok"; o["ru_yaz"] += rus == "yaz"; o["ru_dur"] += rus.startswith("DUR")
        o["ru_marka_ilan"] += rp[1] > 0; o["ru_marka_toplam"] += rp[1]; o["ru_beyan_var"] += x["ru_beyan"] > 0
        o["en_marka"] += x["en_marka"] > 0
        o["ru_baslik_marka"] += x["ru_baslik_marka"]; o["ru_etiket_marka"] += x["ru_etiket_marka"]
        o["state_disi"] += L.get("state") != "active"
        o["ru_batch_uyusmaz"] += ru_batch_uyusmaz; o["kisisel_acik"] += bool(L.get("is_personalizable"))
    (out / "BEYAN_KURU.json").write_text(json.dumps(dict(ozet=oz, uretim_ortagi=ortaklar, ilanlar=satir), ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"AKTIF {len(ilan)} ilan (liste {len(ids)})", flush=True)
    for b, o in sorted(oz.items()):
        print(f"AILE {b}: {json.dumps(o, ensure_ascii=False)}", flush=True)
        print(f"ORTAK {b}: {json.dumps(ortaklar.get(b), ensure_ascii=False)}", flush=True)
    for x in satir:
        if x["en_plan"].startswith("DUR") or x["ru_plan"].startswith("DUR"):
            print(f"DUR ilan {x['listing_id']} ({x['aile']}): EN {x['en_plan']} | RU {x['ru_plan']}", flush=True)
    for lid in a.ilan:
        L = next((x for x in ilan if str(x.get("listing_id")) == lid), None)
        if not L:
            print(f"PLAN {lid}: aktif listede yok", flush=True); continue
        d = norm(L.get("description"))
        aile = BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id"))), "?")
        ru = ru_tekil(api, shop, lid) if aile in ("poster", "kupa") else ru_gercek(ru_ceviri(L))
        soru = kisisel_sorular(api, shop, lid, L); kota(api)
        rapor = [f"ILAN {lid} | state {L.get('state')} | aile {aile} | kisisellestirme acik {L.get('is_personalizable')} | "
                 f"soru {'okunamadi' if soru is None else len(soru)} | ortak {ortak(L)}"]
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
        if getattr(a, "ru_yeniden", False) and aile == "poster":   # Serdar 23 Eki: poster RU canli EN + envanterden (yalniz plan)
            import difflib
            import ru_olcum
            import ru_poster
            inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
            kota(api)
            env = ru_olcum.envanter_ozet(inv)
            try:
                en1 = en_plan(d, aile)[0] or d
            except Dur as e:
                en1 = None; rapor += [f"RU yeniden: EN plani DUR ({e})"]
            if en1:
                ru1, k = ru_poster.kur(en1, env)
                olc = ru_olcum.analiz_bir(dict(listing_id=lid, aile=aile, en=en1, ru=ru1, envanter=env, ortak=ortak(L)))
                k.update(sorunlar=olc["sorunlar"], pass_=k["pass_"] and not olc["sorunlar"], envanter=env,
                         ru_baslik=(ru or {}).get("title"), ru_etiket=(ru or {}).get("tags"))
                (out / f"YENI_EN_{lid}.txt").write_text(en1 + "\n", encoding="utf-8")
                (out / f"YENI_RU_{lid}.txt").write_text(ru1 + "\n", encoding="utf-8")
                (out / f"EN_FARK_{lid}.txt").write_text("".join(difflib.unified_diff(
                    (d + "\n").splitlines(True), (en1 + "\n").splitlines(True), "EN canli", "EN yeni")), encoding="utf-8")
                (out / f"KONTROL_{lid}.json").write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")
                rapor += [f"RU yeniden: kontrol {'PASS' if k['pass_'] else 'FAIL'} | paragraf EN {k['paragraf_en']} RU {k['paragraf_ru']} | "
                          f"hata {k['hata']} | olcum sorunlari [{olc['sorunlar']}] (YENI_EN/YENI_RU/EN_FARK/KONTROL_{lid})"]
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


def yaz(api, shop, lid, out, bolum=None):
    """Tek ilan: yedek -> plan -> yazim -> geri okuma + kapi (1b). Donus R (sonuc PASS / ATLA / FAIL). Kapi farkinda Dur."""
    L = api.get(f"/listings/{lid}", {"includes": "Translations"}) or {}
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    ru = ru_tekil(api, shop, lid)
    soru0 = kisisel_sorular(api, shop, lid, L)
    kota(api)
    (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(ilan=L, ru=ru, envanter=inv, kisisel_sorular=soru0), ensure_ascii=False,
                                                      indent=1), encoding="utf-8")
    if L.get("state") != "active":
        raise Dur(f"{lid}: state {L.get('state')} (active degil): updateListing cagrilmaz")
    if ortak(L) is None:
        raise Dur(f"{lid}: production_partners okunamadi; kapi 1b karsilastiramaz, yazim yok")
    # 23 Eki olcumu (kosu 39939437623, 4570031205): Etsy'nin coklu soru modelinde personalization_is_required / _char_count_max /
    # _instructions yanitta YOK, sorular /listings/{id}/personalization'da. Kapi: is_personalizable zorunlu; eski alanlar varsa
    # korunan() ile once/sonra kiyaslanir (yoksa ikisi de None); sorular (soru0) yazim sonrasi birebir kiyaslanir.
    if "is_personalizable" not in L:
        raise Dur(f"{lid}: kisisellestirme alanlari API yanitinda yok; kapi 1b karsilastiramaz, yazim yok")
    if L.get("is_personalizable") and not soru0:
        raise Dur(f"{lid}: kisisellestirme acik ama sorular okunamadi; kapi 1b karsilastiramaz, yazim yok")
    if bolum is None:
        bolum = {str(s["shop_section_id"]): s.get("title") for s in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    aile = BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id"))), "?")
    en_yeni, en_not = en_plan(L.get("description"), aile)
    ru_yeni, ru_n, ru_not = ru_plan(ru.get("description"), aile) if ru else (None, 0, "RU yok")
    R = dict(ilan=lid, aile=aile, en=en_not, ru=ru_not, ru_marka_once=ru_n, ru_ceviri="var" if ru else "yok", yazildi=[])
    if not en_yeni and not ru_yeni:   # yeniden baslatilabilirlik (Serdar 23 Eki 1c): beyan zaten var
        R.update(sonuc="ATLA", hata=[], istek=api.calls, kota=api.remaining)
        (out / f"SONUC_{lid}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
        print("SONUC", json.dumps(R, ensure_ascii=False), flush=True)
        return R
    for yeni_, eski_ in ((en_yeni, L.get("description")), (ru_yeni, ru.get("description"))):
        if yeni_ and len(TIRE.findall(yeni_)) > len(TIRE.findall(norm(eski_))):
            raise Dur(f"{lid}: yazim uzun/orta tire ekliyor")
    kota(api)   # taban 10 (CLAUDE.md); baska taban Serdar onayi olmadan konmaz
    k0, sat0, imza0 = korunan(L), satilabilir(inv), teklif_imza(inv)
    try:
        return _yaz_dogrula(api, shop, lid, out, L, ru, soru0, en_yeni, ru_yeni, R, k0, sat0, imza0)
    except (Exception, SystemExit) as e:   # yazim sonrasi HTTP/ag hatasi: kayit birakilir, toplu kosu DURur (inceleme A5)
        R.update(sonuc="FAIL", hata=[f"istisna (yazim/geri okuma): {str(e)[:300]}"], istek=api.calls, kota=api.remaining)
        (out / f"SONUC_{lid}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
        print("SONUC", json.dumps(R, ensure_ascii=False), flush=True)
        return R


def _yaz_dogrula(api, shop, lid, out, L, ru, soru0, en_yeni, ru_yeni, R, k0, sat0, imza0):
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
        yru = ru_tekil(api, shop, lid)
        if norm(y.get("description")) == bek_en and (not ru or norm(yru.get("description")) == bek_ru):
            break
        time.sleep(BEKLE_SN)
    inv1 = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    soru1 = kisisel_sorular(api, shop, lid, y)
    hata = [f"RU PUT hata: {R['ru_hata']}"] if R.get("ru_hata") else []
    if norm(y.get("description")) != bek_en:
        hata.append("EN aciklama beklenenle ayni degil")
    if ru and norm(yru.get("description")) != bek_ru:
        hata.append("RU aciklama beklenenle ayni degil")
    if bool(ru) != bool(yru):
        hata.append(f"RU ceviri varligi degisti ({bool(ru)} -> {bool(yru)})")
    k1 = korunan(y)
    hata += [f"{k}: {k0[k]} -> {k1[k]}" for k in k0 if k0[k] != k1[k]]
    if soru0 != soru1:
        hata.append("kisisellestirme sorulari degisti")
    if ru and (norm(yru.get("title")) != norm(ru.get("title")) or list(yru.get("tags") or []) != list(ru.get("tags") or [])):
        hata.append("RU baslik/etiket degisti")
    if satilabilir(inv1) != sat0:
        hata.append(f"satilabilir teklif {sat0} -> {satilabilir(inv1)}")
    elif teklif_imza(inv1) != imza0:
        hata.append("teklif icerigi (fiyat/acik/stok) degisti")
    d1, r1 = norm(y.get("description")), norm(yru.get("description"))
    R["sonra"] = dict(state=y.get("state"), beyan=d1.count(BEYAN), eski_beyan=d1.count(ESKI_BEYAN), ru_beyan=r1.count(RU_BEYAN),
                      en_marka=len(MARKA.findall(d1)), ru_marka=len(MARKA.findall(r1)), satilabilir=satilabilir(inv1),
                      tire=len(TIRE.findall(d1)), uretim_ortagi=k1["uretim_ortagi"])
    R["hata"], R["sonuc"] = hata, ("FAIL" if hata else "PASS")
    R["istek"], R["kota"] = api.calls, api.remaining
    (out / f"SONRA_{lid}.json").write_text(json.dumps(dict(ilan=y, ru=yru, kisisel_sorular=soru1), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    (out / f"SONUC_{lid}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SONUC", json.dumps(R, ensure_ascii=False), flush=True)
    return R


def toplu(api, shop, a, out):
    """Aile aile toplu yazim (Serdar 23 Eki 4): aktif ilanlar (bolumden aile), --ilan verilirse yalniz onlar; beyani zaten tam
    olanlar ATLA (istek: yalniz plan okumasi). Her ilanda kapi 1b; ilk FAIL ya da Dur'da tum kosu DUR. --limit yazilan ilan sayisi."""
    bolum = {str(s["shop_section_id"]): s.get("title") for s in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    ids = a.ilan or aktif_idler(api, shop)
    ilan = []
    for k in range(0, len(ids), 100):
        ilan += (api.get("/listings/batch", {"listing_ids": ",".join(ids[k:k + 100]), "includes": "Translations"}) or {}).get("results") or []
        kota(api)
    aday = []
    for L in sorted(ilan, key=lambda x: int(x["listing_id"])):
        if BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id")))) != a.aile:
            continue
        lid = str(L["listing_id"])
        try:
            yap = bool(en_plan(L.get("description"), a.aile)[0])
            if not yap and a.aile in ("poster", "kupa"):   # EN tamam: RU'yu yazimla ayni kaynaktan (tekil GET) oku
                ru = ru_tekil(api, shop, lid); kota(api)
                if not ru:
                    raise Dur("poster/kupa ilaninda RU ceviri yok")
                yap = bool(ru_plan(ru.get("description"), a.aile)[0])
        except Dur as e:
            raise Dur(f"{lid}: plan DUR ({e}); yazim yok")
        if yap:
            aday.append(lid)
    print(f"TOPLU aile {a.aile}: aday {len(aday)} (zaten tam olan atlandi) | limit {a.limit}", flush=True)
    sonuc, dur = [], None
    for n, lid in enumerate(aday[:a.limit], 1):
        try:
            if hasattr(api, "kota_kapisi"):   # Serdar 23 Eki 2b esigi (config aktifse): ilana baslamadan
                api.kota_kapisi(f"ilan {lid}")
            R = yaz(api, shop, lid, out, bolum)
        except (Dur, Exception, SystemExit) as e:   # yazimdan ONCE durdu (state, kota, okuma hatasi): yazma yok
            dur = str(e)[:300]; sonuc.append(dict(ilan=lid, sonuc="DUR", hata=[dur], yazildi=[]))
            print(f"[{n}] {lid} DUR: {dur}", flush=True); break
        sonuc.append({k: R.get(k) for k in ("ilan", "sonuc", "hata", "yazildi")})
        print(f"[{n}/{min(len(aday), a.limit)}] {lid} {R['sonuc']} | kota {api.remaining}", flush=True)
        if R["sonuc"] == "FAIL":
            break
    oz = dict(aile=a.aile, aday=len(aday), islenen=len(sonuc), pass_=sum(x["sonuc"] == "PASS" for x in sonuc),
              atla=sum(x["sonuc"] == "ATLA" for x in sonuc), fail=[x for x in sonuc if x["sonuc"] in ("FAIL", "DUR")],
              kota=api.remaining)
    (out / "TOPLU_OZET.json").write_text(json.dumps(dict(ozet=oz, ilanlar=sonuc), ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOPLU_OZET", json.dumps(oz, ensure_ascii=False), flush=True)
    if dur:
        raise Dur(dur)
    return not oz["fail"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kuru", "yaz", "toplu"], default="kuru")
    ap.add_argument("--ilan", default="", help="virgullu ilan kimlikleri (yaz: tam 1; toplu: istege bagli alt kume)")
    ap.add_argument("--aile", choices=sorted(set(BOLUM_AILE.values())), default=None)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--onay", default="")
    ap.add_argument("--gorsel-indir", action="store_true")
    ap.add_argument("--ru-yeniden", action="store_true", help="kuru --ilan: poster RU'sunu canli EN + envanterden kur (yazim yok)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    a.ilan = [x for x in a.ilan.replace(" ", "").split(",") if x]
    if not all(x.isdigit() for x in a.ilan):
        raise SystemExit("DUR: --ilan yalniz rakam")
    if a.mod == "yaz" and (a.onay != ONAY or len(a.ilan) != 1):
        raise SystemExit(f"DUR: yaz icin --onay {ONAY} ve tam 1 ilan")
    if a.mod == "toplu" and (a.onay != ONAY_TOPLU or not a.aile or not 1 <= a.limit <= 300):
        raise SystemExit(f"DUR: toplu icin --onay {ONAY_TOPLU}, --aile ve 1 <= --limit <= 300")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    try:
        if a.mod == "kuru":
            kuru(api, shop, a, out)
            print(f"KURU: yazma yok | istek {api.calls} | kota {api.remaining}", flush=True)
            return
        ok = (yaz(api, shop, a.ilan[0], out)["sonuc"] != "FAIL") if a.mod == "yaz" else toplu(api, shop, a, out)
    except Dur as e:
        print(f"DUR: {e} | istek {api.calls} | kota {api.remaining}", flush=True)
        sys.exit(3)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
