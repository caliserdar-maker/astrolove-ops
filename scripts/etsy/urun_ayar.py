#!/usr/bin/env python3
"""URUN AYAR dosyasi + yazim kapisi (plan plan/urun-ayar docs/plan/URUN_AYAR_PLAN.md 2-4; Serdar 8 Kas gece "Hepsi oneriyle", Onay 3b).
Etsy istegi YOK; yalniz dosya okur. Etsy'ye yazan betik (bugun yalniz ornament_taslak) her yazimdan ONCE, html_coz SONRASI son govdeyi
yazim_kapisi'na verir; kapi mevcut kapilarin (izin, AI beyan, RU yazim, yayin beyan, metin yasak, kota) ONUNE eklenir, yerine gecmez.

yukle(urun, yol=None) : docs/urun/<urun>/URUN_AYAR.json -> sema dogrulama (zorunlu alan bos, bilinmeyen anahtar, tip) -> DUR listesi.
yazim_kapisi(A, method, path, data, json_body, onay_yolu, metin_yolu) : yazim yok + neden listesi (SystemExit) su durumlarda:
  kilit.kilitli false | ayar sha'si kilit.ayar_sha256'dan farkli | onay kaydi (YEREL yol; Drive'daki ONAY_<URUN>.json) yok ya da sha'si
  kilit.onay_sha256'dan farkli ya da kaydin ayar_sha256 / urun alani farkli | panel on isi yapilmadi ya da kanitsiz | GPSR beyani baska
  urun / baska uretim ortagi id'si / Serdar disi | GPSR disinda beyanla gecen panel isi (S3) | olculmedi alani var | EN metin CSV sha'si
  farkli ya da createDraftListing baslik/aciklama/etiket o CSV satiri degil | SPEC "beklenen" ile ayar
  farki | govdede state (yayin panelde Serdar'da, S14) | uca ozgu govde ayardan farkli (createDraftListing ve envanter: anahtar kumesi
  tam, SKU = sku_kodu; nitelik PUT; stil gorselleri; gorsel rank; kisisellestirme kapaliyken personalization) | herhangi bir metin
  alaninda (baslik, aciklama, etiket, alt metin, kisisellestirme) aciklama_yasak eslesmesi | aciklamada aciklama_zorunlu eksik.
"""
import hashlib
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
SHA_RX = re.compile(r"^[0-9a-f]{64}$")
PANEL_ZORUNLU = ("uretim_ortagi_kaydi", "kargo_profili", "gpsr")
PANEL_KIMLIK = {"uretim_ortagi_kaydi": "production_partner_id", "kargo_profili": "shipping_profile_id"}   # olcum kanitinin bagli oldugu ayar
TARIH_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
METIN_ALAN = ("title", "description", "tags", "alt_text", "materials", "question_text", "instructions")   # aciklama_yasak taranan alanlar

# alan -> (tip, zorunlu, bos_olabilir). tip: type ya da tuple; "liste:<tip>" listedeki ogelerin tipi.
SEMA = {
    "urun": (str, True, False), "surum": (int, True, False), "spec": (str, True, False), "kaynak": (dict, True, False),
    "olculmedi": ("liste:str", True, True), "ilan": (dict, True, False), "uretim_ortagi_konum": (str, True, False),
    "varyasyon": (dict, True, False), "envanter": (dict, True, False), "metin": (dict, True, False),
    "aciklama_zorunlu": ("liste:str", True, False), "aciklama_yasak": ("liste:str", True, False),
    "kisisellestirme": (dict, True, False), "taslak": (dict, True, False), "beklenen": (dict, True, False),
    "panel_on_isleri": ("liste:dict", True, False), "kilit": (dict, True, False),
}
ALT = {
    "ilan": {"taxonomy_id": (int, True, False), "who_made": (str, True, False), "when_made": (str, True, False),
             "is_supply": (str, True, False), "type": (str, True, False), "shipping_profile_id": (int, True, False),
             "return_policy_id": (int, True, False), "readiness_state_id": (int, True, False), "shop_section_id": (int, True, False),
             "production_partner_id": (int, True, False), "materials": ("liste:str", True, False), "should_auto_renew": (str, True, False),
             "quantity": (int, True, False), "fiyat": ((int, float), True, False)},
    "varyasyon": {"property_id": (int, True, False), "property_name": (str, True, False), "menu": ("liste:dict", True, False)},
    "envanter": {k: ("liste:int", True, True) for k in ("price_on_property", "quantity_on_property", "sku_on_property",
                                                         "readiness_state_on_property")},
    "metin": {"en": (dict, True, False), "ru": (dict, True, False)},
    "kisisellestirme": {"acik": (bool, True, False)},
    "taslak": {"galeri": ("liste:str", True, False), "nitelikler": ("liste:dict", True, False)},
    "kilit": {"kilitli": (bool, True, False), "ayar_sha256": ((str, type(None)), True, True), "onay_sha256": ((str, type(None)), True, True)},
}
MENU = {"ad": (str, True, False), "sku_kodu": (str, True, False), "gorsel_sira": (int, True, False)}
METIN = {"csv": (str, True, False), "sha256": (str, True, False), "anahtar": (str, True, False)}
NITELIK = {"property_id": (int, True, False), "ad": (str, True, False), "value_ids": ("liste:int", True, False),
           "values": ("liste:str", True, False), "scale_id": ((int, type(None)), True, True)}
PANEL = {"ad": (str, True, False), "durum": (str, True, False), "dogrulama": (str, True, False), "kanit": ((dict, type(None)), True, True)}


def _bos(v):
    return v is None or v == "" or v == [] or v == {}


def _tip_ok(v, tip):
    if isinstance(v, bool) and tip is not bool:                    # bool int sayilmaz (scale_id=True, quantity=True)
        return False
    if isinstance(tip, str) and tip.startswith("liste:"):
        it = {"str": str, "int": int, "dict": dict}[tip[6:]]
        return isinstance(v, list) and all(isinstance(x, it) and not isinstance(x, bool) for x in v)
    if tip is int or tip == (int, float):
        return isinstance(v, tip) and not isinstance(v, bool)
    return isinstance(v, tip)


def _sema(d, S, on, hata):
    if not isinstance(d, dict):
        hata.append(f"{on or 'kok'}: sozluk degil"); return
    for k in sorted(set(d) - set(S)):
        hata.append(f"{on}{k}: bilinmeyen anahtar")
    for k, (tip, zor, bos_ok) in S.items():
        if k not in d:
            if zor:
                hata.append(f"{on}{k}: yok")
            continue
        v = d[k]
        if _bos(v) and not bos_ok:
            hata.append(f"{on}{k}: bos")
        elif v is None and not (isinstance(tip, tuple) and type(None) in tip):
            hata.append(f"{on}{k}: tip None")                        # null yalniz tipinde None olan alanda (scale_id, kilit sha)
        elif v is not None and not _tip_ok(v, tip):                 # bos olabilen alanda da tip ({} liste yerine, [] str yerine)
            hata.append(f"{on}{k}: tip {type(v).__name__}")


def dogrula(A):
    hata = []
    _sema(A, SEMA, "", hata)
    if hata:
        return hata
    for alan, S in ALT.items():
        _sema(A[alan], S, f"{alan}.", hata)
    if hata:                                                           # alt sema bozuksa ic ice denetim AttributeError vermesin
        return hata
    for i, m in enumerate(A["varyasyon"].get("menu") or []):
        _sema(m, MENU, f"varyasyon.menu[{i}].", hata)
    for dil in ("en", "ru"):
        if isinstance(A["metin"].get(dil), dict):
            _sema(A["metin"][dil], METIN, f"metin.{dil}.", hata)
            if not SHA_RX.match(str(A["metin"][dil].get("sha256") or "")):
                hata.append(f"metin.{dil}.sha256: 64 hane hex degil")
    for i, n in enumerate(A["taslak"].get("nitelikler") or []):
        _sema(n, NITELIK, f"taslak.nitelikler[{i}].", hata)
    for i, p in enumerate(A["panel_on_isleri"]):
        _sema(p, PANEL, f"panel_on_isleri[{i}].", hata)
        if p.get("durum") not in ("yapildi", "yapilmadi"):
            hata.append(f"panel_on_isleri[{i}].durum: yapildi / yapilmadi degil")
    adlar = [p.get("ad") for p in A["panel_on_isleri"]]
    for z in PANEL_ZORUNLU:
        if adlar.count(z) != 1:
            hata.append(f"panel_on_isleri: {z} tam 1 kez olmali ({adlar.count(z)})")
    for y in A["aciklama_yasak"]:
        try:
            re.compile(y)
        except re.error:
            hata.append(f"aciklama_yasak: gecersiz desen {y!r}")
    menu = A["varyasyon"].get("menu") or []
    if len({m.get("ad") for m in menu}) != len(menu) or len({m.get("sku_kodu") for m in menu}) != len(menu):
        hata.append("varyasyon.menu: ad / sku_kodu tekrarli")
    g = A["taslak"].get("galeri") or []
    if any(not isinstance(m.get("gorsel_sira"), int) or not 1 <= m["gorsel_sira"] <= len(g) for m in menu):
        hata.append("varyasyon.menu: gorsel_sira galeri disinda")
    return hata


def yukle(urun, yol=None):
    yol = Path(yol) if yol else KOK / "docs" / "urun" / urun / "URUN_AYAR.json"
    if not yol.is_file():
        raise SystemExit(f"DUR: URUN_AYAR yok ({urun})")
    try:
        A = json.loads(yol.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"DUR: URUN_AYAR json okunamadi ({urun}): {e}") from None
    hata = dogrula(A)
    if not hata and A["urun"] != urun:
        hata.append(f"urun {A['urun']} != {urun}")
    if hata:
        raise SystemExit(f"DUR: URUN_AYAR ({urun}) sema: " + "; ".join(hata))
    return A


def ayar_sha(A):
    """kilit blogu HARIC kanonik JSON'un sha256'si (kilitleme bu sha'yi tasir)."""
    return hashlib.sha256(json.dumps({k: v for k, v in A.items() if k != "kilit"}, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def dosya_sha(yol):
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def norm(t):
    return " ".join(str(t or "").split())


def _uc(method, path):
    m = str(method or "").upper()
    if m == "POST" and re.match(r"^/shops/\d+/listings/\d+/variation-images$", path):
        return "stil_gorsel"
    if m == "POST" and re.match(r"^/shops/\d+/listings/\d+/personalization$", path):
        return "kisisellestirme"
    if m == "POST" and re.match(r"^/shops/\d+/listings/\d+/images$", path):
        return "gorsel"
    if m == "POST" and re.match(r"^/shops/\d+/listings$", path):
        return "createDraftListing"
    if m == "PUT" and re.match(r"^/listings/\d+/inventory$", path):
        return "envanter"
    if m == "PUT" and re.match(r"^/shops/\d+/listings/\d+/properties/\d+$", path):
        return "nitelik"
    return "diger"


def _sayi(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _spec_fark(A, kok):
    """Gecis donemi (plan 4. bolum): ayar ile SPEC (ORN_YAYIN_SPEC beklenen) ayni olmali; fark -> DUR. ayar.beklenen = SPEC.beklenen
    karsilastirmasi kilit sonrasi SPEC degisimini yakalar (ayar.beklenen kilit sha'sina girer). ASAMA FARKI (Serdar 8 Kas, Onay 3b):
    SPEC son hali (gorsel_sayisi 14, stil gorselleri 10-14, W/H/D nitelikleri) taslak asamasinda istenmez; taslak.galeri (11) ve
    taslak.nitelikler bu asamanin ayri blogudur, SPEC'le karsilastirilmaz (yayina_hazir, adim 4, SPEC son halini denetler)."""
    f = kok / A["spec"]
    if not f.is_file():
        return [f"SPEC yok ({A['spec']})"]
    S = json.loads(f.read_text(encoding="utf-8")).get("beklenen") or {}
    I, h = A["ilan"], []
    for ad, a, s in (("shipping_profile_id", I["shipping_profile_id"], S.get("shipping_profile_id")),
                     ("uretim_ortagi_id", I["production_partner_id"], S.get("uretim_ortagi_id")),
                     ("uretim_ortagi_konum", A["uretim_ortagi_konum"], S.get("uretim_ortagi_konum")),
                     ("fiyat", _sayi(I["fiyat"]), _sayi(S.get("fiyat"))),
                     ("kisisellestirme", A["kisisellestirme"]["acik"], S.get("kisisellestirme")),
                     ("aciklama_zorunlu", A["aciklama_zorunlu"], S.get("aciklama_zorunlu")),
                     ("aciklama_yasak", A["aciklama_yasak"], S.get("aciklama_yasak"))):
        if a != s:
            h.append(f"SPEC farki {ad}: ayar {a!r} / SPEC {s!r}")
    if A["beklenen"] != S:
        h.append("SPEC farki: ayar.beklenen != SPEC.beklenen")
    return h


def _kilit(A, onay_yolu):
    h = []
    K, sha = A["kilit"], ayar_sha(A)
    if K.get("kilitli") is not True:
        h.append("kilit.kilitli false (Serdar ayar onayi yok)")
    if K.get("ayar_sha256") != sha:
        h.append("ayar sha256 kilit.ayar_sha256 ile farkli")
    if not onay_yolu or not Path(onay_yolu).is_file():
        h.append("onay kaydi yok")
    else:
        if dosya_sha(onay_yolu) != K.get("onay_sha256"):
            h.append("onay kaydi sha256 kilit.onay_sha256 ile farkli")
        try:
            O = json.loads(Path(onay_yolu).read_text(encoding="utf-8"))
        except ValueError:
            O = {}
        if not isinstance(O, dict) or O.get("urun") != A["urun"] or O.get("ayar_sha256") != sha or _bos(O.get("onay_sozu")) \
                or _bos(O.get("tarih")):
            h.append("onay kaydi bu ayara ait degil (urun / ayar_sha256 / onay_sozu / tarih)")
    return h


def _panel(A):
    h = []
    for p in A["panel_on_isleri"]:
        ad, k = p["ad"], p.get("kanit")
        if p["durum"] != "yapildi":
            h.append(f"panel on isi yapilmadi: {ad}"); continue
        if not isinstance(k, dict) or _bos(k.get("tur")) or _bos(k.get("tarih")):
            h.append(f"panel on isi kanitsiz: {ad}"); continue
        if not TARIH_RX.match(str(k.get("tarih"))):
            h.append(f"panel on isi kanit tarihi YYYY-AA-GG degil: {ad}"); continue
        if ad == "gpsr":
            if k.get("tur") != "beyan" or k.get("kimden") != "Serdar" or _bos(k.get("soz")) or k.get("urun") != A["urun"] \
                    or k.get("uretim_ortagi_id") != A["ilan"]["production_partner_id"]:
                h.append("GPSR beyani bu urun / bu uretim ortagi icin Serdar beyani degil (kimden, soz, urun, ortak; ortak degisince gecersiz)")
        elif k.get("tur") == "beyan":
            h.append(f"panel on isi beyanla gecmez (yalniz GPSR): {ad}")
        elif k.get("tur") != "olcum" or _bos(k.get("kosu")):
            h.append(f"panel on isi kanit turu olcum + kosu degil: {ad}")
        elif ad in PANEL_KIMLIK and k.get("kimlik") != A["ilan"][PANEL_KIMLIK[ad]]:
            h.append(f"panel on isi olcumu bu kimlik icin degil: {ad} ({PANEL_KIMLIK[ad]})")
    return h


def _durum_yasak(data, js):
    for g in (data, js):
        if isinstance(g, dict) and "state" in g:
            return [f"govdede state={g.get('state')!r}: kod state yazmaz (yayin panelde Serdar'da, S14)"]
    return []


def _taslak_govde(A, data):
    I, h = A["ilan"], []
    bek = {"quantity": I["quantity"], "who_made": I["who_made"], "when_made": I["when_made"], "is_supply": I["is_supply"],
           "taxonomy_id": I["taxonomy_id"], "type": I["type"], "shipping_profile_id": I["shipping_profile_id"],
           "return_policy_id": I["return_policy_id"], "readiness_state_id": I["readiness_state_id"], "shop_section_id": I["shop_section_id"],
           "materials": ",".join(I["materials"]), "should_auto_renew": I["should_auto_renew"],
           "production_partner_ids": str(I["production_partner_id"])}
    data = data if isinstance(data, dict) else {}
    fazla = sorted(set(data) - set(bek) - {"title", "description", "tags", "price"})
    if fazla:
        h.append(f"createDraftListing ayarda olmayan alan {fazla}")
    for k, v in bek.items():
        if str(data.get(k)) != str(v):
            h.append(f"createDraftListing {k}: govde {data.get(k)!r} / ayar {v!r}")
    if _sayi(data.get("price")) != _sayi(I["fiyat"]):
        h.append(f"createDraftListing price: govde {data.get('price')!r} / ayar {I['fiyat']!r}")
    d = str(data.get("description") or "")
    for z in A["aciklama_zorunlu"]:
        if norm(z) not in norm(d):
            h.append(f"aciklama_zorunlu yok: {z[:40]!r}")
    return h


def sku_onekleri(cift):
    """ornament_taslak.sku ile ayni bicim: ORN-<CIFT> ya da (32 karakteri asarsa) ORN-<B1[:3]>_<B2[:3]>."""
    b = str(cift or "").split("_")
    return {f"ORN-{cift}"} | ({f"ORN-{b[0][:3]}_{b[1][:3]}"} if len(b) == 2 else set())


def _envanter(A, js, cift):
    V, I, E, h = A["varyasyon"], A["ilan"], A["envanter"], []
    js = js if isinstance(js, dict) else {}
    P = js.get("products")
    if not isinstance(P, list) or len(P) != len(V["menu"]):
        return [f"envanter: urun sayisi {len(P) if isinstance(P, list) else None} / menu {len(V['menu'])}"]
    gorulen, onekler = [], set()
    for p in P:
        pv = p.get("property_values") if isinstance(p, dict) else None
        of = p.get("offerings") if isinstance(p, dict) else None
        if not isinstance(pv, list) or len(pv) != 1 or not isinstance(of, list) or len(of) != 1:
            h.append("envanter: urun bicimi (1 property_value, 1 offering) degil"); continue
        v, o = pv[0], of[0]
        if set(p) != {"sku", "property_values", "offerings"} or set(v) != {"property_id", "property_name", "values"} \
                or set(o) != {"price", "quantity", "is_enabled", "readiness_state_id"}:
            h.append("envanter: ayarda olmayan alan (urun / deger / offering anahtarlari)")
        if not isinstance(v.get("values"), list) or len(v["values"]) != 1:
            h.append(f"envanter: deger sayisi 1 degil {v.get('values')!r}")
        kod = {m["ad"]: m["sku_kodu"] for m in V["menu"]}.get((v.get("values") or [None])[0])
        sk = str(p.get("sku") or "")
        if kod is None or not any(sk == f"{o}-{kod}" for o in sku_onekleri(cift)):
            h.append(f"envanter: SKU {sk!r} bu cift ({cift}) + ayardaki sku_kodu ile uyusmuyor")
        onekler.add(sk.rsplit("-", 1)[0])
        if v.get("property_id") != V["property_id"] or v.get("property_name") != V["property_name"]:
            h.append(f"envanter: property {v.get('property_id')} / ayar {V['property_id']}")
        gorulen.append((v.get("values") or [None])[0])
        if _sayi(o.get("price")) != _sayi(I["fiyat"]):
            h.append(f"envanter price {o.get('price')!r} / ayar {I['fiyat']!r}")
        if o.get("quantity") != I["quantity"] or o.get("readiness_state_id") != I["readiness_state_id"] or o.get("is_enabled") is not True:
            h.append(f"envanter offering (quantity / readiness / acik) ayardan farkli: {o.get('quantity')}, {o.get('readiness_state_id')}")
    if sorted(map(str, gorulen)) != sorted(m["ad"] for m in V["menu"]):
        h.append(f"envanter menu degerleri {sorted(map(str, gorulen))} / ayar {sorted(m['ad'] for m in V['menu'])}")
    if len(onekler) > 1:
        h.append(f"envanter: SKU onekleri farkli {sorted(onekler)}")
    fazla = sorted(set(js) - {"products"} - set(E))
    if fazla:
        h.append(f"envanter: ayarda olmayan alan {fazla}")
    for k in E:
        if js.get(k) != E[k]:
            h.append(f"envanter {k}: govde {js.get(k)!r} / ayar {E[k]!r}")
    return h


def _stil_gorsel(A, js, baglam):
    """variation-images: her menu degeri tam 1 kez, ayardaki property_id ile, gorseli ayardaki gorsel_sira'daki galeri gorseli.
    baglam = (vid: menu adi -> value_id, rank_id: galeri sirasi -> image_id), yaz() geri okumadan verir."""
    V = A["varyasyon"]
    if not baglam:
        return ["stil gorselleri: eslem baglami (value_id / image_id) verilmedi"]
    vid, rank_id = baglam
    bek = sorted((V["property_id"], vid.get(m["ad"]), rank_id.get(m["gorsel_sira"])) for m in V["menu"])
    vi = (js or {}).get("variation_images") if isinstance(js, dict) else None
    if not isinstance(vi, list) or len(vi) != len(V["menu"]) or set(js) != {"variation_images"}:
        return [f"stil gorselleri: {len(vi) if isinstance(vi, list) else None} kayit / menu {len(V['menu'])}"]
    if any(not isinstance(x, dict) or set(x) != {"property_id", "value_id", "image_id"} or x.get("property_id") != V["property_id"]
           for x in vi) or len({x.get("value_id") for x in vi}) != len(vi) or len({x.get("image_id") for x in vi}) != len(vi):
        return ["stil gorselleri: property_id ayardan farkli ya da deger / gorsel tekrarli"]
    if None in [x for t in bek for x in t] or sorted((x["property_id"], x["value_id"], x["image_id"]) for x in vi) != bek:
        return ["stil gorselleri: menu degeri -> gorsel eslemesi ayardaki gorsel_sira ile farkli"]
    return []


def _gorsel(A, data):
    rk = _sayi((data or {}).get("rank")) if isinstance(data, dict) else None
    n = len(A["taslak"]["galeri"])
    return [] if rk is not None and rk == int(rk) and 1 <= rk <= n else [f"gorsel rank {rk!r} taslak galerisi 1-{n} disinda"]


def _metin_yasak(A, data, js):
    """aciklama_yasak (adi tarihsel): musteriye gorunen TUM metin alanlarinda (baslik, aciklama, etiket, alt metin, kisisellestirme)."""
    h = []

    def gez(g, alan=None):
        if isinstance(g, dict):
            for k, v in g.items():
                gez(v, k if k in METIN_ALAN else alan)
        elif isinstance(g, (list, tuple)):
            for v in g:
                gez(v, alan)
        elif isinstance(g, str) and alan:
            for y in A["aciklama_yasak"]:
                m = re.search(y, g, re.I)
                if m:
                    h.append(f"aciklama_yasak eslesmesi ({alan}): {m.group(0)!r}")
    gez(data); gez(js)
    return h


def _csv_satiri(A, data, metin_yolu, cift):
    """createDraftListing baslik / aciklama / etiketler metin CSV'deki (sha'si ayarda kilitli) bir satirla birebir."""
    import csv
    import html
    data = data if isinstance(data, dict) else {}
    coz = html.unescape                    # govde html_coz SONRASI; CSV alani da ayni cozumle karsilastirilir
    try:
        rows = list(csv.DictReader(open(metin_yolu, encoding="utf-8")))
    except OSError:
        return ["metin CSV okunamadi"]
    r = [x for x in rows if x.get("kod") == cift]
    if len(r) != 1:
        return [f"createDraftListing cift {cift!r} metin CSV'de {len(r)} satirda (1 olmali)"]
    r, h = r[0], []
    if coz(r.get("baslik") or "") != data.get("title"):
        h.append("createDraftListing baslik metin CSV satirindan (bu cift) farkli")
    if coz(r.get("aciklama") or "") != data.get("description"):
        h.append("createDraftListing aciklama metin CSV satirindan farkli")
    if coz(",".join(t.strip() for t in str(r.get("etiketler") or "").split(","))) != data.get("tags"):
        h.append("createDraftListing etiketler metin CSV satirindan farkli")
    return h


def _nitelik(A, path, data):
    pid = int(path.rsplit("/", 1)[1])
    N = {n["property_id"]: n for n in A["taslak"]["nitelikler"]}
    if pid not in N:
        return [f"nitelik {pid}: ayarda yok"]
    n, data = N[pid], (data if isinstance(data, dict) else {})
    bek = {"value_ids": ",".join(str(i) for i in n["value_ids"]), "values": ",".join(n["values"])}
    if n.get("scale_id") is not None:                                 # yaz ile ayni kosul (is not None)
        bek["scale_id"] = n["scale_id"]
    return [f"nitelik {pid}: govde {data!r} / ayar {bek!r}"] if {k: data.get(k) for k in set(bek) | set(data)} != bek else []


def yazim_kapisi(A, method, path, data=None, json_body=None, onay_yolu=None, metin_yolu=None, kok=KOK, cift=None, stil_baglam=None):
    """Son (html_coz sonrasi) govde. Gecemezse SystemExit (yazim yok). -> uc adi. cift: createDraftListing / envanter icin zorunlu
    (CSV satiri ve SKU bu cifte bagli); stil_baglam: variation-images icin (vid, rank_id). metin_yolu verilmezse ayardaki metin.en.csv."""
    uc = _uc(method, path)
    h = _kilit(A, onay_yolu) + _panel(A)
    if A["olculmedi"] != []:
        h.append(f"olculmedi alanlar var (once O1 olcumu): {A['olculmedi']}")
    m = Path(metin_yolu) if metin_yolu else kok / A["metin"]["en"]["csv"]
    csv_ok = m.is_file() and dosya_sha(m) == A["metin"]["en"]["sha256"]
    if not csv_ok:
        h.append("EN metin CSV sha256 ayardan farkli")
    h += _spec_fark(A, kok) + _durum_yasak(data, json_body) + _metin_yasak(A, data, json_body)
    if uc == "createDraftListing":
        h += _taslak_govde(A, data) + (_csv_satiri(A, data, m, cift) if csv_ok else [])
    elif uc == "stil_gorsel":
        h += _stil_gorsel(A, json_body, stil_baglam)
    elif uc == "kisisellestirme" and A["kisisellestirme"]["acik"] is not True:
        h.append("kisisellestirme ayarda kapali: personalization yazilmaz")
    elif uc == "gorsel":
        h += _gorsel(A, data)
    elif uc == "envanter":
        h += _envanter(A, json_body, cift)
    elif uc == "nitelik":
        h += _nitelik(A, path, data)
    if h:
        raise SystemExit(f"DUR: ayar kapisi ({uc}): " + "; ".join(h))
    return uc
