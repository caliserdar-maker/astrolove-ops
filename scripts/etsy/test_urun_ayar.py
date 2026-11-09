#!/usr/bin/env python3
"""urun_ayar + ornament_taslak ayar kapisi sahte testi (ag yok, token yok, Etsy istegi yok). Her DUR kosulu icin bilinen FAIL, mutlu yol
icin bilinen PASS; sabit kimlik taramasi (ayardan gelen deger ornament_taslak yazim yolunda sabit yazilmaz).
sahte_ortam(): SAHTE kilitli ayar kopyasi + SAHTE onay kaydi + SAHTE metin CSV (78 satir; "free shipping" cumlesi SPEC zorunlu
[ SHIPPING ] cumlesiyle degistirilmis, AI beyan aynen) -> URUN_AYAR / ONAY_YOLU / METIN_CSV ortam degiskenleri. Gercek dosyalara dokunmaz."""
import ast
import copy
import inspect
import json
import os
import pathlib
import sys
import re
import tempfile
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import urun_ayar as UA  # noqa: E402

KOK = UA.KOK
SHOP = "39729443"
GERCEK_CSV = KOK / "data" / "pod" / "ORNAMENT78_METIN.csv"
ESKI = b"[ SHIPPING ]\nMade and shipped by our production partner, with free shipping. You can see the estimated delivery time for your country at checkout."
YENI = b"[ SHIPPING ]\nMade and shipped by our production partner. You can see the shipping cost and estimated delivery time for your country on this page and at checkout."


def sahte_csv(hedef):
    b = GERCEK_CSV.read_bytes()
    if b.count(ESKI) != 78:
        raise SystemExit(f"DUR: sahte CSV kurulamadi (kargo blogu {b.count(ESKI)}/78)")
    pathlib.Path(hedef).write_bytes(b.replace(ESKI, YENI))
    return pathlib.Path(hedef)


def kilitle(A, d, onay_ad="ONAY_ornament78_SAHTE.json"):
    """A'yi (yerinde) SAHTE onay kaydiyla kilitler; ayar + onay dosyasini d'ye yazar -> (ayar_yolu, onay_yolu)."""
    A["kilit"] = {"kilitli": True, "ayar_sha256": UA.ayar_sha(A), "onay_sha256": None}
    onay = pathlib.Path(d) / onay_ad
    onay.write_text(json.dumps({"urun": A["urun"], "ayar_sha256": A["kilit"]["ayar_sha256"], "onay_sozu": "SAHTE (test)",
                                "tarih": "2026-11-09"}, ensure_ascii=False), encoding="utf-8")
    A["kilit"]["onay_sha256"] = UA.dosya_sha(onay)
    ay = pathlib.Path(d) / "URUN_AYAR_SAHTE.json"
    ay.write_text(json.dumps(A, ensure_ascii=False, indent=1), encoding="utf-8")
    return ay, onay


def sahte_ayar(d, csv_yol):
    A = UA.yukle("ornament78")
    A["metin"]["en"]["csv"] = "SAHTE/ORNAMENT78_METIN_SAHTE.csv"
    A["metin"]["en"]["sha256"] = UA.dosya_sha(csv_yol)
    I = A["ilan"]
    A["olculmedi"] = []                    # SAHTE: O1 olcumu yapilmis varsayilir
    kim = {"uretim_ortagi_kaydi": I["production_partner_id"], "kargo_profili": I["shipping_profile_id"]}
    for p in A["panel_on_isleri"]:
        p["durum"] = "yapildi"
        p["kanit"] = ({"tur": "beyan", "kimden": "Serdar", "soz": "SAHTE (test)", "tarih": "2026-11-09", "urun": A["urun"],
                       "uretim_ortagi_id": I["production_partner_id"]}
                      if p["ad"] == "gpsr" else {"tur": "olcum", "tarih": "2026-11-09", "kosu": "SAHTE", "kimlik": kim[p["ad"]]})
    return A


def sahte_ortam(d=None):
    """Ortami SAHTE kilitli ayara kurar (test ve kuru koşum 2). -> dict(ayar, onay, csv, A)."""
    d = pathlib.Path(d or tempfile.mkdtemp(prefix="urun_ayar_sahte_"))
    csv_yol = sahte_csv(d / "ORNAMENT78_METIN_SAHTE.csv")
    A = sahte_ayar(d, csv_yol)
    ay, onay = kilitle(A, d)
    os.environ.update(URUN_AYAR=str(ay), ONAY_YOLU=str(onay), METIN_CSV=str(csv_yol))
    return dict(ayar=ay, onay=onay, csv=csv_yol, A=A, dir=d)


def dur(f, *a, **k):
    """-> DUR metni (SystemExit) ya da None (gecti)."""
    try:
        f(*a, **k)
    except SystemExit as e:
        return str(e.code)
    return None


def testler():  # noqa: C901
    import ornament_taslak as T
    T.time.sleep = lambda s: None
    s = []
    gercek = UA.yukle("ornament78")
    s.append(("PASS: gercek ayar sema temiz", isinstance(gercek, dict) and gercek["kilit"]["kilitli"] is False))
    # gercek ayar + gercek CSV: kilitli false ve aciklama_yasak (free shipping) -> DUR
    import csv as _csv
    row = next(r for r in _csv.DictReader(open(GERCEK_CSV, encoding="utf-8")) if r["kod"] == "CANCER_LIBRA")
    tags = [t.strip() for t in row["etiketler"].split(",")]
    g_body = T.taslak_govde(gercek, row["baslik"], row["aciklama"], tags)
    h = dur(UA.yazim_kapisi, gercek, "POST", f"/shops/{SHOP}/listings", g_body, metin_yolu=GERCEK_CSV, cift="CANCER_LIBRA")
    s.append(("FAIL: gercek ayar -> kilitli false + onay yok + panel + free shipping", h is not None and "kilitli false" in h
              and "onay kaydi yok" in h and "panel on isi yapilmadi" in h and "aciklama_yasak eslesmesi" in h
              and "aciklama_zorunlu yok" in h and "olculmedi alanlar var" in h))

    O = sahte_ortam()
    A, onay, csvy = O["A"], O["onay"], O["csv"]
    srow = T.metin_satiri("CANCER_LIBRA")
    stags = [t.strip() for t in srow["etiketler"].split(",")]
    body = T.taslak_govde(A, srow["baslik"], srow["aciklama"], stags)
    kp = dict(onay_yolu=onay, metin_yolu=csvy, cift="CANCER_LIBRA")
    P_C, P_I, P_N = f"/shops/{SHOP}/listings", "/listings/9000000001/inventory", f"/shops/{SHOP}/listings/9000000001/properties/"
    n0 = A["taslak"]["nitelikler"][0]
    nbody = {"value_ids": ",".join(map(str, n0["value_ids"])), "values": ",".join(n0["values"])}
    inv = T.envanter_govde(A, "CANCER_LIBRA")

    def kapi(A_=None, m="POST", p=P_C, d=None, j=None, **k):
        kw = dict(kp); kw.update(k)
        return dur(UA.yazim_kapisi, A_ if A_ is not None else A, m, p, d if d is not None or j is not None or p != P_C else body, j, **kw)

    s.append(("PASS: sahte kilitli createDraftListing", kapi() is None))
    s.append(("PASS: sahte kilitli envanter PUT", kapi(m="PUT", p=P_I, d=None, j=inv) is None))
    s.append(("PASS: sahte kilitli nitelik PUT", kapi(m="PUT", p=P_N + str(n0["property_id"]), d=nbody) is None))
    s.append(("PASS: sahte kilitli gorsel POST (diger uc)", kapi(p=f"/shops/{SHOP}/listings/9000000001/images", d={"rank": 1, "alt_text": "x"})
              is None))

    def kilitli_kopya(deg):
        B = copy.deepcopy(A); deg(B)
        d = tempfile.mkdtemp(); _, o = kilitle(B, d)
        return B, o

    # --- kilit / onay
    B = copy.deepcopy(A); B["kilit"]["kilitli"] = False
    s.append(("FAIL: kilit.kilitli false", "kilitli false" in (kapi(B) or "")))
    B = copy.deepcopy(A); B["ilan"]["quantity"] = 998
    s.append(("FAIL: kilit sonrasi ayar degisti (sha farki)", "kilit.ayar_sha256 ile farkli" in (kapi(B) or "")))
    s.append(("FAIL: onay kaydi yok", "onay kaydi yok" in (kapi(onay_yolu=None) or "")))
    s.append(("FAIL: onay yolu var, dosya yok", "onay kaydi yok" in (kapi(onay_yolu="/yok/ONAY.json") or "")))
    o2 = pathlib.Path(tempfile.mkdtemp()) / "O.json"; o2.write_text(onay.read_text() + " ", encoding="utf-8")
    s.append(("FAIL: onay kaydi sha farki", "onay_sha256 ile farkli" in (kapi(onay_yolu=o2) or "")))
    for alan, deger in (("urun", "kupa78"), ("ayar_sha256", "0" * 64), ("onay_sozu", ""), ("tarih", None)):
        Ox = json.loads(onay.read_text()); Ox[alan] = deger
        B = copy.deepcopy(A); d = pathlib.Path(tempfile.mkdtemp()); ox = d / "O.json"; ox.write_text(json.dumps(Ox), encoding="utf-8")
        B["kilit"]["onay_sha256"] = UA.dosya_sha(ox); B["kilit"]["ayar_sha256"] = UA.ayar_sha(B)
        s.append((f"FAIL: onay kaydi {alan} uyusmaz", "bu ayara ait degil" in (kapi(B, onay_yolu=ox) or "")))
    # --- panel on isleri (S3)
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][0].update(durum="yapilmadi", kanit=None))
    s.append(("FAIL: panel on isi yapilmadi", "yapilmadi: uretim_ortagi_kaydi" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][1].update(kanit=None))
    s.append(("FAIL: panel on isi kanitsiz", "kanitsiz: kargo_profili" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][1].update(kanit={"tur": "beyan", "tarih": "2026-11-09"}))
    s.append(("FAIL: GPSR disi beyan gecmez", "beyanla gecmez (yalniz GPSR): kargo_profili" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][0]["kanit"].pop("kosu"))
    s.append(("FAIL: olcum kanitinda kosu yok", "olcum + kosu degil" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][1]["kanit"].update(kimlik=319194887351))
    s.append(("FAIL: kargo olcumu baska profil icin", "olcumu bu kimlik icin degil: kargo_profili" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][0]["kanit"].update(kimlik=5817638))
    s.append(("FAIL: ortak kaydi olcumu baska ortak icin", "olcumu bu kimlik icin degil: uretim_ortagi_kaydi" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][0]["kanit"].update(tarih="x"))
    s.append(("FAIL: kanit tarihi bicimsiz", "YYYY-AA-GG" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][2]["kanit"].update(kimden="Merkez"))
    s.append(("FAIL: GPSR beyani Serdar disi", "GPSR beyani" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][2]["kanit"].update(soz=""))
    s.append(("FAIL: GPSR beyan sozu yok", "GPSR beyani" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B.update(olculmedi=None))
    s.append(("FAIL: olculmedi null (sema disi) kapida da DUR", "olculmedi alanlar var" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B.update(olculmedi=["ilan.return_policy_id"]))
    s.append(("FAIL: olculmedi alan varken yazim yok", "olculmedi alanlar var" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][2]["kanit"].update(urun="kupa78"))
    s.append(("FAIL: GPSR beyani baska urun", "GPSR beyani" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["panel_on_isleri"][2]["kanit"].update(uretim_ortagi_id=5817638))
    s.append(("FAIL: GPSR beyani baska uretim ortagi", "GPSR beyani" in (kapi(B, onay_yolu=o) or "")))
    B, o = kilitli_kopya(lambda B: B["ilan"].update(production_partner_id=5817638))
    h = kapi(B, onay_yolu=o) or ""
    s.append(("FAIL: uretim ortagi degisti -> GPSR beyani gecersiz + SPEC farki", "GPSR beyani" in h and "uretim_ortagi_id" in h))
    # --- metin CSV
    c2 = pathlib.Path(tempfile.mkdtemp()) / "C.csv"; c2.write_bytes(csvy.read_bytes() + b"\r\n")
    s.append(("FAIL: EN metin CSV sha farki", "EN metin CSV sha256" in (kapi(metin_yolu=c2) or "")))
    s.append(("FAIL: EN metin CSV yok", "EN metin CSV sha256" in (kapi(metin_yolu="/yok.csv") or "")))
    # --- SPEC farki (sahte SPEC kopyasi, gercek SPEC'e dokunulmaz)
    sk = pathlib.Path(tempfile.mkdtemp())
    spec = json.loads((KOK / A["spec"]).read_text(encoding="utf-8"))
    (sk / A["spec"]).parent.mkdir(parents=True)
    for alan, deger, ara in (("fiyat", 29.90, "SPEC farki fiyat"), ("shipping_profile_id", 319194887351, "SPEC farki shipping_profile_id"),
                             ("kisisellestirme", False, "SPEC farki kisisellestirme"), ("ek_alan", 1, "ayar.beklenen != SPEC.beklenen")):
        S2 = copy.deepcopy(spec); S2["beklenen"][alan] = deger
        (sk / A["spec"]).write_text(json.dumps(S2), encoding="utf-8")
        s.append((f"FAIL: SPEC farki {alan}", ara in (kapi(kok=sk) or "")))
    (sk / A["spec"]).unlink()
    s.append(("FAIL: SPEC dosyasi yok", "SPEC yok" in (kapi(kok=sk) or "")))
    # --- state (S14)
    s.append(("FAIL: createDraftListing govdesinde state", "state='active'" in (kapi(d=dict(body, state="active")) or "")))
    s.append(("FAIL: json govdede state", "state=" in (kapi(m="PUT", p=P_I, j=dict(inv, state="draft")) or "")))
    # --- createDraftListing govde = ayar
    for alan, deger in (("price", 29.90), ("shipping_profile_id", 319194887351), ("production_partner_ids", "5817638"),
                        ("taxonomy_id", 1), ("quantity", 1), ("who_made", "someone_else"), ("materials", "Glass"),
                        ("readiness_state_id", 1), ("return_policy_id", 1), ("shop_section_id", 1), ("is_supply", "true"),
                        ("when_made", "2020_2026"), ("type", "download"), ("should_auto_renew", "false")):
        s.append((f"FAIL: createDraftListing {alan} ayardan farkli", f"createDraftListing {alan}" in (kapi(d=dict(body, **{alan: deger})) or "")))
    b2 = dict(body); b2.pop("shipping_profile_id")
    s.append(("FAIL: createDraftListing alan eksik", "createDraftListing shipping_profile_id" in (kapi(d=b2) or "")))
    for fazla in ("is_personalizable", "image_ids", "item_weight", "state_x"):
        s.append((f"FAIL: createDraftListing fazla alan {fazla}", "ayarda olmayan alan" in (kapi(d=dict(body, **{fazla: "1"})) or "")))
    s.append(("FAIL: baslik CSV satirindan farkli", "baslik metin CSV satirindan" in (kapi(d=dict(body, title=body["title"] + " X")) or "")))
    s.append(("FAIL: cift verilmedi", "cift None" in (kapi(cift=None) or "")))
    arow = T.metin_satiri("ARIES_LEO")
    abody = T.taslak_govde(A, arow["baslik"], arow["aciklama"], [t.strip() for t in arow["etiketler"].split(",")])
    s.append(("FAIL: baska ciftin metni bu cift icin", "baslik metin CSV satirindan (bu cift)" in (kapi(d=abody) or "")))
    s.append(("PASS: ARIES_LEO kendi ciftiyle", kapi(d=abody, cift="ARIES_LEO") is None))
    s.append(("FAIL: baska ciftin envanteri (SKU)", "bu cift" in (kapi(m="PUT", p=P_I, j=T.envanter_govde(A, "ARIES_LEO")) or "")))
    s.append(("PASS: uzun cift adi SKU kisa bicim", UA.sku_onekleri("SAGITTARIUS_CAPRICORN") >= {"ORN-SAGITTARIUS_CAPRICORN", "ORN-SAG_CAP"}
              and kapi(m="PUT", p=P_I, j=T.envanter_govde(A, "SAGITTARIUS_CAPRICORN"), cift="SAGITTARIUS_CAPRICORN") is None))
    s.append(("FAIL: aciklama CSV satirindan farkli", "aciklama metin CSV" in (kapi(d=dict(body, description=body["description"] + " Extra.")) or "")))
    s.append(("FAIL: etiketler CSV satirindan farkli", "etiketler metin CSV" in (kapi(d=dict(body, tags=body["tags"] + ",extra")) or "")))
    for alan, deger in (("title", "Zodiac Ornament Free Shipping"), ("tags", body["tags"] + ",free shipping")):
        s.append((f"FAIL: aciklama_yasak {alan} alaninda", "aciklama_yasak eslesmesi (" + alan + ")" in (kapi(d=dict(body, **{alan: deger})) or "")))
    s.append(("FAIL: aciklama_yasak alt_text'te", "aciklama_yasak eslesmesi (alt_text)" in
              (kapi(p=f"/shops/{SHOP}/listings/9000000001/images", d={"rank": 2, "alt_text": "Ships free"}) or "")))
    s.append(("FAIL: aciklama_yasak kisisellestirmede", "aciklama_yasak eslesmesi" in (kapi(
        p=f"/shops/{SHOP}/listings/9000000001/personalization", j={"personalization_questions": [{"instructions": "free delivery"}]}) or "")))
    for rk in (0, 12, "x", None):
        s.append((f"FAIL: gorsel rank {rk!r}", "gorsel rank" in (kapi(p=f"/shops/{SHOP}/listings/9000000001/images", d={"rank": rk}) or "")))
    vi = {"variation_images": [dict(property_id=A["varyasyon"]["property_id"], value_id=5000 + i, image_id=800000 + m["gorsel_sira"])
                               for i, m in enumerate(A["varyasyon"]["menu"])]}
    P_V = f"/shops/{SHOP}/listings/9000000001/variation-images"
    SB = ({m["ad"]: 5000 + i for i, m in enumerate(A["varyasyon"]["menu"])}, {r_: 800000 + r_ for r_ in range(1, 12)})
    s.append(("PASS: stil gorselleri", kapi(p=P_V, j=vi, stil_baglam=SB) is None))
    v2 = copy.deepcopy(vi)
    for i, x in enumerate(v2["variation_images"]):
        x["image_id"] = 800001 + i                       # stiller galeri 1-5'e (ayar: 7-11)
    s.append(("FAIL: stil gorseli ayardaki gorsel_sira disinda", "gorsel_sira ile farkli" in (kapi(p=P_V, j=v2, stil_baglam=SB) or "")))
    v2 = copy.deepcopy(vi); a0, a1 = v2["variation_images"][0]["value_id"], v2["variation_images"][1]["value_id"]
    v2["variation_images"][0]["value_id"], v2["variation_images"][1]["value_id"] = a1, a0
    s.append(("FAIL: stil degerleri yer degistirmis", "gorsel_sira ile farkli" in (kapi(p=P_V, j=v2, stil_baglam=SB) or "")))
    s.append(("FAIL: stil gorseli eslem baglami yok", "eslem baglami" in (kapi(p=P_V, j=vi) or "")))
    v2 = copy.deepcopy(vi); v2["variation_images"][0]["property_id"] = 200
    s.append(("FAIL: stil gorseli property_id", "stil gorselleri" in (kapi(p=P_V, j=v2, stil_baglam=SB) or "")))
    v2 = copy.deepcopy(vi); v2["variation_images"].pop()
    s.append(("FAIL: stil gorseli eksik", "stil gorselleri" in (kapi(p=P_V, j=v2, stil_baglam=SB) or "")))
    v2 = copy.deepcopy(vi); v2["variation_images"][1]["image_id"] = v2["variation_images"][0]["image_id"]
    s.append(("FAIL: stil gorseli tekrarli", "stil gorselleri" in (kapi(p=P_V, j=v2, stil_baglam=SB) or "")))
    B, o = kilitli_kopya(lambda B: B["kisisellestirme"].update(acik=False))
    h = kapi(B, p=f"/shops/{SHOP}/listings/9000000001/personalization", j={"personalization_questions": []}, onay_yolu=o) or ""
    s.append(("FAIL: kisisellestirme kapaliyken personalization yok", "kisisellestirme ayarda kapali" in h))
    for yasak in ("Free shipping to the US.", "This ornament ships free.", "FREE   DELIVERY worldwide"):
        s.append((f"FAIL: aciklama_yasak {yasak[:16]!r}", "aciklama_yasak eslesmesi" in (kapi(d=dict(body, description=body["description"]
                                                                                                         + "\n" + yasak)) or "")))
    s.append(("FAIL: aciklama_zorunlu eksik", "aciklama_zorunlu yok" in
              (kapi(d=dict(body, description=body["description"].replace("on this page and at checkout", "at checkout"))) or "")))
    s.append(("PASS: zorunlu cumle bosluk farkiyla gecer (govde denetimi)", not any("aciklama_zorunlu" in x for x in UA._taslak_govde(
        A, dict(body, description=body["description"].replace("[ SHIPPING ]\nMade", "[ SHIPPING ]   \n  Made"))))))
    # --- envanter
    i2 = copy.deepcopy(inv); i2["products"] = i2["products"][:4]
    s.append(("FAIL: envanter urun sayisi", "urun sayisi" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    for ad, f in (("price", lambda o: o.update(price=29.9)), ("quantity", lambda o: o.update(quantity=1)),
                  ("readiness", lambda o: o.update(readiness_state_id=1)), ("is_enabled", lambda o: o.update(is_enabled=False))):
        i2 = copy.deepcopy(inv); f(i2["products"][2]["offerings"][0])
        s.append((f"FAIL: envanter offering {ad}", "envanter" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    i2 = copy.deepcopy(inv); i2["products"][0]["property_values"][0]["property_id"] = 200
    s.append(("FAIL: envanter property_id", "envanter: property" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    i2 = copy.deepcopy(inv); i2["products"][0]["property_values"][0]["values"] = ["Gold"]
    s.append(("FAIL: envanter menu degeri", "menu degerleri" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    i2 = copy.deepcopy(inv); i2["price_on_property"] = [513]
    s.append(("FAIL: envanter price_on_property", "price_on_property" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    i2 = copy.deepcopy(inv); i2["products"][1]["offerings"].append(dict(i2["products"][1]["offerings"][0]))
    s.append(("FAIL: envanter iki offering", "urun bicimi" in (kapi(m="PUT", p=P_I, j=i2) or "")))
    for ad, f, ara in (("SKU yanlis", lambda J: [x.update(sku="YANLIS-SKU") for x in J["products"]], "SKU"),
                       ("SKU kodu karisik", lambda J: J["products"][0].update(sku=J["products"][1]["sku"]), "SKU"),
                       ("SKU onek farkli", lambda J: J["products"][0].update(sku=J["products"][0]["sku"].replace("CANCER", "LEO")), "onekleri"),
                       ("iki deger", lambda J: J["products"][0]["property_values"][0].update(values=["Ruby", "Gold"]), "deger sayisi"),
                       ("fazla urun anahtari", lambda J: J["products"][0].update(fazla=1), "ayarda olmayan alan"),
                       ("fazla offering anahtari", lambda J: J["products"][0]["offerings"][0].update(fazla=1), "ayarda olmayan alan"),
                       ("fazla ust anahtar", lambda J: J.update(fazla=1), "ayarda olmayan alan")):
        i2 = copy.deepcopy(inv); f(i2)
        s.append((f"FAIL: envanter {ad}", ara in (kapi(m="PUT", p=P_I, j=i2) or "")))
    # --- nitelik
    s.append(("FAIL: nitelik ayarda yok", "ayarda yok" in (kapi(m="PUT", p=P_N + "999", d=nbody) or "")))
    s.append(("FAIL: nitelik deger farki", "nitelik" in (kapi(m="PUT", p=P_N + str(n0["property_id"]), d=dict(nbody, value_ids="84")) or "")))
    s.append(("FAIL: nitelik fazla alan", "nitelik" in (kapi(m="PUT", p=P_N + str(n0["property_id"]), d=dict(nbody, scale_id=3)) or "")))
    # --- sema (yukle)
    d = pathlib.Path(tempfile.mkdtemp())
    s.append(("FAIL: URUN_AYAR yok", "URUN_AYAR yok" in (dur(UA.yukle, "ornament78", d / "yok.json") or "")))
    (d / "b.json").write_text("{bozuk", encoding="utf-8")
    s.append(("FAIL: URUN_AYAR json bozuk", "json okunamadi" in (dur(UA.yukle, "ornament78", d / "b.json") or "")))

    def sema(deg, ara, urun="ornament78"):
        B = copy.deepcopy(gercek); deg(B)
        f = d / "s.json"; f.write_text(json.dumps(B), encoding="utf-8")
        h = dur(UA.yukle, urun, f) or ""
        return ara in h
    for ad, deg, ara in (
            ("bilinmeyen anahtar", lambda B: B.update(fazla=1), "fazla: bilinmeyen anahtar"),
            ("ust alan yok", lambda B: B.pop("beklenen"), "beklenen: yok"),
            ("zorunlu bos", lambda B: B["ilan"].update(who_made=""), "ilan.who_made: bos"),
            ("tip: bool int yerine", lambda B: B["ilan"].update(quantity=True), "ilan.quantity: tip"),
            ("tip: fiyat str", lambda B: B["ilan"].update(fiyat="19.90"), "ilan.fiyat: tip"),
            ("tip: materials liste degil", lambda B: B["ilan"].update(materials="Ceramic"), "ilan.materials: tip"),
            ("alt bilinmeyen anahtar", lambda B: B["ilan"].update(state="active"), "ilan.state: bilinmeyen anahtar"),
            ("menu alan yok", lambda B: B["varyasyon"]["menu"][0].pop("sku_kodu"), "menu[0].sku_kodu: yok"),
            ("menu tekrar", lambda B: B["varyasyon"]["menu"][1].update(ad="Ruby"), "tekrarli"),
            ("gorsel_sira galeri disi", lambda B: B["varyasyon"]["menu"][0].update(gorsel_sira=12), "galeri disinda"),
            ("metin sha hex degil", lambda B: B["metin"]["en"].update(sha256="abc"), "64 hane hex"),
            ("nitelik alan yok", lambda B: B["taslak"]["nitelikler"][0].pop("values"), "nitelikler[0].values: yok"),
            ("panel durum gecersiz", lambda B: B["panel_on_isleri"][0].update(durum="beyan"), "yapildi / yapilmadi"),
            ("panel zorunlu eksik", lambda B: B["panel_on_isleri"].pop(2), "gpsr tam 1 kez"),
            ("panel zorunlu tekrar", lambda B: B["panel_on_isleri"].append(dict(B["panel_on_isleri"][0])), "uretim_ortagi_kaydi tam 1 kez"),
            ("aciklama_yasak gecersiz desen", lambda B: B["aciklama_yasak"].append("free(("), "gecersiz desen"),
            ("kilit alan tipi", lambda B: B["kilit"].update(kilitli="true"), "kilit.kilitli: tip"),
            ("scale_id bool", lambda B: B["taslak"]["nitelikler"][0].update(scale_id=True), "scale_id: tip"),
            ("olculmedi sozluk", lambda B: B.update(olculmedi={}), "olculmedi: tip"),
            ("kilit sha liste", lambda B: B["kilit"].update(ayar_sha256=[]), "ayar_sha256: tip"),
            ("menu ogesi str", lambda B: B["varyasyon"].update(menu=["Ruby"]), "varyasyon.menu: tip"),
            ("olculmedi null", lambda B: B.update(olculmedi=None), "olculmedi: tip None"),
            ("on_property null", lambda B: B["envanter"].update(price_on_property=None), "price_on_property: tip None"),
            ("kisisellestirme null", lambda B: B["kisisellestirme"].update(acik=None), "kisisellestirme.acik: bos")):
        s.append((f"FAIL: sema {ad}", sema(deg, ara)))
    s.append(("FAIL: sema urun adi farkli", sema(lambda B: None, "urun ornament78 != kupa78", urun="kupa78")))

    # --- ornament_taslak baglantisi: Kilitli._ayar_kapi html_coz SONRASI govdeyi denetler; ozgun govde gonderilir
    T_ = T
    k = object.__new__(T_.Kilitli); k.lid = 9000000001; k.remaining = None; k.A = T_.ayar(); k.cift = "CANCER_LIBRA"
    h = dur(k._ayar_kapi, "POST", P_C, dict(body, description=body["description"] + "\nfr&#101;e shipping"))
    s.append(("FAIL: HTML varlikli 'fr&#101;e shipping' html_coz sonrasi yakalanir", h is not None and "aciklama_yasak" in h))
    h = dur(k._ayar_kapi, "POST", P_C, dict(body, description=body["description"] + "\nfree&nbsp;shipping"))
    s.append(("FAIL: 'free&nbsp;shipping' yakalanir", h is not None and "aciklama_yasak" in h))
    h = dur(k._ayar_kapi, "POST", f"/shops/{SHOP}/listings/9000000001/images", {"rank": 1, "alt_text": "Printful ornament"})
    s.append(("FAIL: metin yasak ENGEL (S9) ayar kapisinda", h is not None))
    s.append(("PASS: acil PATCH inactive ayar kapisina takilmaz", k._ayar_kapi("PATCH", f"/shops/{SHOP}/listings/9000000001",
                                                                                {"state": "inactive"}) is None))
    yak = {}
    gercek_call = T_.Etsy._call
    T_.Etsy._call = lambda self, m, p, **kw: yak.setdefault("kw", kw) and {}
    try:
        k._call("PUT", P_N + str(n0["property_id"]), data=dict(nbody))
        h = dur(k._call, "POST", f"/shops/{SHOP}/listings/9000000001/images", data={"rank": 1, "alt_text": "A &amp;amp; B"})
    finally:
        T_.Etsy._call = gercek_call
    s.append(("PASS: _call ozgun govdeyi Etsy._call'a verir (tek cozme orada)", h is None and yak.get("kw", {}).get("data") == dict(nbody)))
    yak.clear()
    T_.Etsy._call = lambda self, m, p, **kw: yak.update(kw=kw) or {}
    try:
        h = dur(k._call, "POST", f"/shops/{SHOP}/listings/9000000001/images", data={"rank": 1, "alt_text": "A &amp;amp; B"})
    finally:
        T_.Etsy._call = gercek_call
    s.append(("PASS: alt_text '&amp;amp;' cift cozulmez (ozgun gider)", h is None and yak["kw"]["data"]["alt_text"] == "A &amp;amp; B"))
    h = dur(k._call, "PATCH", f"/shops/{SHOP}/listings/9000000001", data={"state": "active"})
    s.append(("FAIL: PATCH state=active yasak", h is not None and "YASAK" in h))
    h = dur(k._call, "PATCH", f"/shops/{SHOP}/listings/9000000001", data={"state": "inactive"}, json_body={"state": "active"})
    s.append(("FAIL: acil PATCH yanina json govde eklenemez", h is not None and "YASAK" in h))
    s.append(("FAIL: acil PATCH istisnasi json govdeyle kapiyi atlamaz", k._ayar_kapi("PATCH", f"/shops/{SHOP}/listings/9000000001",
              {"state": "inactive"}, {"title": "x"}) is not None if dur(k._ayar_kapi, "PATCH", f"/shops/{SHOP}/listings/9000000001",
                                                                     {"state": "inactive"}, {"title": "x"}) is None else True))
    h = dur(k._call, "PUT", P_I, json_body=dict(inv, products=inv["products"][:1]))
    s.append(("FAIL: Kilitli._call envanter ayardan farkli -> istek yok", h is not None and "urun sayisi" in h))
    # tek gonderim yolu: gonderilen govde html_coz'lu (bir kez), kapilar ayni dizi
    gonder = {}

    class Yak:
        status_code = 201
        headers = {}
        text = ""

        @staticmethod
        def json():
            return {"listing_id": 9000000001}
    k2 = object.__new__(T_.Kilitli); k2.lid = None; k2.remaining = None; k2.A = k.A; k2.cift = "CANCER_LIBRA"
    k2._kalan_yaz, k2._istek_oncesi, k2._bekle, k2._headers = (lambda *a: None), (lambda: None), (lambda: 1), (lambda: {})
    gp = T_.requests.post
    T_.requests.post = lambda url, data=None, **kw: gonder.update(data=data) or Yak()
    # gercek akis: CSV basligi "&amp;amp;" tasir, govde ham CSV basligidir; html_coz BIR kez -> "&amp;" gider (iki kez cozulse "&").
    # Kapi CSV alanini ayni cozumle (html.unescape) karsilastirir -> yanlis DUR yok.
    c3 = pathlib.Path(tempfile.mkdtemp()) / "C3.csv"
    eski_b = srow["baslik"].encode("utf-8")
    c3.write_bytes(csvy.read_bytes().replace(eski_b, eski_b.replace(b" ", b" &amp;amp; ", 1), 1))
    B3, o3 = kilitli_kopya(lambda B: B["metin"]["en"].update(sha256=UA.dosya_sha(c3)))
    eski_env = {x: os.environ[x] for x in ("METIN_CSV", "ONAY_YOLU")}
    try:
        os.environ.update(METIN_CSV=str(c3), ONAY_YOLU=str(o3)); k2.A = B3
        b3 = dict(body, title=srow["baslik"].replace(" ", " &amp;amp; ", 1))
        kod, js, _ = k2.taslak_olustur(SHOP, b3)
        os.environ.update(eski_env); k2.A = k.A
        h = dur(k2.taslak_olustur, SHOP, dict(body, price=29.90))
        gonder2 = dict(gonder)
    finally:
        T_.requests.post = gp
        os.environ.update(eski_env); k2.A = k.A
    s.append(("PASS: taslak_olustur cozulmus govdeyi BIR kez gonderir (varlikli CSV basligi, yanlis DUR yok)", kod == 201
              and " &amp; " in gonder["data"]["title"] and "&amp;amp;" not in gonder["data"]["title"]))
    s.append(("FAIL: taslak_olustur fiyat ayardan farkli -> istek yok", h is not None and "price" in h and gonder2 == gonder))
    h = dur(k2.taslak_kapi, SHOP, dict(body, description=body["description"] + " ships free"))
    s.append(("FAIL: taslak_kapi aciklama_yasak", h is not None and "aciklama_yasak" in h))
    # Kilitli.post_file: ayar kapisi + metin ENGEL, Etsy.post_file'dan ONCE
    pf = {}
    gercek_pf = T_.Etsy.post_file
    T_.Etsy.post_file = lambda self, path, files, data=None, tekrar=3: pf.update(n=pf.get("n", 0) + 1) or {}
    try:
        h1 = dur(k.post_file, f"/shops/{SHOP}/listings/9000000001/images", {}, {"rank": 1, "alt_text": "Printful ornament"})
        kB = object.__new__(T_.Kilitli); kB.lid = 9000000001; kB.remaining = None; kB.A = gercek
        h2 = dur(kB.post_file, f"/shops/{SHOP}/listings/9000000001/images", {}, {"rank": 1, "alt_text": "x"})
        h3 = dur(k.post_file, f"/shops/{SHOP}/listings/9000000001/images", {}, {"rank": 1, "alt_text": "x"})
    finally:
        T_.Etsy.post_file = gercek_pf
    s.append(("FAIL: Kilitli.post_file metin ENGEL -> yukleme yok", h1 is not None and "tedarikci" in h1))
    s.append(("FAIL: Kilitli.post_file kilitsiz ayar -> yukleme yok", h2 is not None and "kilitli false" in h2))
    s.append(("PASS: Kilitli.post_file sahte kilitli -> 1 yukleme", h3 is None and pf.get("n") == 1))
    # Kuru: ayni kapi (kuru kaydi gercek yazimla ayni kapidan gecer)
    kr = T_.Kuru(SHOP); kr.lid = 9000000001; kr.cift = "CANCER_LIBRA"
    s.append(("FAIL: Kuru._call envanter ayardan farkli", "urun sayisi" in (dur(kr._call, "PUT", P_I, json_body=dict(inv, products=[]))
                                                                       or "") and kr.kayit == []))
    kr2 = T_.Kuru(SHOP); kr2.lid = 9000000001; kr2.A = gercek
    s.append(("FAIL: Kuru.post_file kilitsiz ayar -> kayit yok", "kilitli false" in (dur(kr2.post_file, f"/shops/{SHOP}/listings/9000000001/images",
                                                                                      {}, {"rank": 1, "alt_text": "x"}) or "") and kr2.kayit == []))
    kr3 = T_.Kuru(SHOP); kr3.cift = "CANCER_LIBRA"
    s.append(("FAIL: Kuru.taslak_olustur fiyat farki -> kayit yok", "price" in (dur(kr3.taslak_olustur, SHOP, dict(body, price=29.9)) or "")
              and kr3.kayit == []))
    # tek gonderim yolu mevcut kapilari korur (kapanan kapi yok): AI beyan ve kota
    beyansiz = dict(body, description=body["description"].replace("We use AI tools to help create the artwork, and ", ""))
    c4 = pathlib.Path(tempfile.mkdtemp()) / "C4.csv"           # SAHTE CSV: bu satirda AI beyani yok (ayar kapisi gecsin, AI kapisi yakalasin)
    eski_d = srow["aciklama"].replace("\n", "\r\n") if srow["aciklama"].encode() not in csvy.read_bytes() else srow["aciklama"]
    c4.write_bytes(csvy.read_bytes().replace(eski_d.encode(), eski_d.replace("We use AI tools to help create the artwork, and ", "").encode(), 1))
    B4, o4 = kilitli_kopya(lambda B: B["metin"]["en"].update(sha256=UA.dosya_sha(c4)))
    import etsy_common as E
    n_hata = len(E.BEYAN_HATA)
    eski_env = {x: os.environ[x] for x in ("METIN_CSV", "ONAY_YOLU")}
    try:
        os.environ.update(METIN_CSV=str(c4), ONAY_YOLU=str(o4)); k2.A = B4
        h = dur(k2.taslak_kapi, SHOP, beyansiz)
    finally:
        os.environ.update(eski_env); k2.A = k.A
    beyan_kaydi = len(E.BEYAN_HATA) == n_hata + 1
    E.BEYAN_HATA.clear()               # bilinen FAIL testin kendi kaydi: cikis kancasi (os._exit(1)) test paketini dusurmesin
    s.append(("FAIL: tek yol AI beyan kapisi (beyansiz aciklama)", h is not None and beyan_kaydi and "ayar kapisi" not in h))
    k2.remaining = "9"
    h = dur(k2.taslak_kapi, SHOP, body)
    k2.remaining = None
    s.append(("FAIL: tek yol kota kapisi (9 < 10)", h is not None and "kota 9" in h))
    # yaz() modunda (METIN_CSV yok) metin yolu ayardaki metin.en.csv
    m_csv = os.environ.pop("METIN_CSV")
    try:
        B = copy.deepcopy(gercek); B["metin"]["en"]["csv"] = "data/pod/BASKA.csv"
        ok_y = T_.metin_yolu(B) == KOK / "data/pod/BASKA.csv" and T_.metin_yolu(gercek) == KOK / gercek["metin"]["en"]["csv"]
    finally:
        os.environ["METIN_CSV"] = m_csv
    s.append(("Metin yolu ayardan (metin.en.csv), METIN_CSV yokken", ok_y))
    k3 = object.__new__(T_.Kilitli); k3.lid = 1; k3.remaining = None
    s.append(("FAIL: ayar yuklenmeden yazim yok", "URUN_AYAR yuklenmedi" in (dur(k3._ayar_kapi, "POST", P_C, body) or "")))
    # metin_kontrol galeri kadar alt sutun ister
    r2 = dict(srow); r2.pop("alt_11")
    s.append(("FAIL: metin CSV'de galeri kadar alt sutun yok", "alt metin sutunu yok" in (dur(T_.metin_kontrol, r2, k.A) or "")))
    # yaz modunda URUN_AYAR ortam yolu yasak
    os.environ.update(TOKEN_FILE="/yok", ETSY_SHOP_ID=SHOP, OUT=tempfile.mkdtemp())
    eski_argv, eski_ts = sys.argv, T_.TokenStore
    sys.argv = ["ornament_taslak.py", "--mod", "yaz"]

    class TS:
        def __init__(self, *a): pass
        def needs_refresh(self): return False
    T_.TokenStore = TS
    try:
        m_csv = os.environ.pop("METIN_CSV")
        h = dur(T_.main)
        os.environ["METIN_CSV"] = m_csv
    finally:
        sys.argv, T_.TokenStore = eski_argv, eski_ts
        os.environ.pop("TOKEN_FILE", None); os.environ.pop("OUT", None)
    s.append(("FAIL: yaz modunda URUN_AYAR yasak", h is not None and "URUN_AYAR yasak" in h))

    # --- sabit kimlik taramasi: yazim yolunda ayardan gelen deger sabit yazilmaz
    yasak_deger = set()

    def topla(v):
        if isinstance(v, dict):
            for x in v.values():
                topla(x)
        elif isinstance(v, list):
            for x in v:
                topla(x)
        elif isinstance(v, bool) or v is None:
            return
        elif isinstance(v, (int, float)) and abs(v) >= 100 or isinstance(v, float):
            yasak_deger.add(v)
        elif isinstance(v, str) and len(v) >= 4:
            yasak_deger.add(v)
    for alan in ("ilan", "varyasyon", "envanter", "taslak", "uretim_ortagi_konum"):
        topla(gercek[alan])
    yasak_deger |= {29.9, 29.90, 319194887351, 5817638}       # ORN_ETSY_AYAR celisen eski degerler
    yasak_deger |= {m["sku_kodu"] for m in gercek["varyasyon"]["menu"]}   # 2 harfli SKU kodlari
    hit = []
    modul = ast.parse(inspect.getsource(T_))
    for n in modul.body:                                      # modul duzeyi atamalar (P_SABIT = 513 gibi)
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            for c in ast.walk(n):
                if isinstance(c, ast.Constant) and not isinstance(c.value, bool) and c.value in yasak_deger:
                    hit.append(("modul", c.value))
    for ad in ("yaz", "Kilitli", "metin_kontrol", "medya", "sku", "taslak_govde", "envanter_govde", "stiller", "galeri", "yaz_dongu"):
        agac = ast.parse(textwrap.dedent(inspect.getsource(getattr(T_, ad))))
        for n in ast.walk(agac):
            if isinstance(n, ast.Constant) and not isinstance(n.value, bool) and n.value in yasak_deger:
                hit.append((ad, n.value))
    s.append((f"Sabit kimlik taramasi: yazim yolunda ayar degeri sabiti yok {hit[:6]}", hit == []))
    # bilinen FAIL: tarama gercekten yakalar
    kaynak = "def f():\n    return {'shipping_profile_id': 319230731837, 'who_made': 'i_did'}\n"
    s.append(("FAIL: tarama sabit kimligi yakalar (oz test)", sum(isinstance(n, ast.Constant) and n.value in yasak_deger
                                                                for n in ast.walk(ast.parse(kaynak))) == 2))
    # ornament_kargo uyum adlari ayardan
    s.append(("Ice aktarmada ayar yuklenmez (kur / oku ayar bozukken calisir)", "_A0" not in vars(T_) and not any(
        isinstance(n, ast.Assign) and any(isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "yukle" for c in ast.walk(n))
        for n in modul.body)))
    gy = UA.yukle
    UA.yukle = lambda *a, **k: (_ for _ in ()).throw(SystemExit("DUR: URUN_AYAR (sahte bozuk)"))
    try:
        ok_kur = T_.cift_listesi("CANCER_LIBRA") == ["CANCER_LIBRA"] and callable(T_.kur) and callable(T_.oku)
        h = dur(lambda: T_.STILLER)
    finally:
        UA.yukle = gy
    s.append(("Ayar bozukken cift_listesi / kur / oku erisilir, OT.STILLER DUR verir", ok_kur and h is not None and "sahte bozuk" in h))
    s.append(("PASS: OT.P_STYLE / STILLER / STOK / GALERI ayardan", T_.P_STYLE == gercek["varyasyon"]["property_id"]
              and [x[0] for x in T_.STILLER] == [m["ad"] for m in gercek["varyasyon"]["menu"]] and T_.STOK == gercek["ilan"]["quantity"]
              and T_.GALERI == gercek["taslak"]["galeri"]))
    s.append(("Gercek URUN_AYAR'da gercek ilan kimligi yok (10 hane, 900000000N disi)",
              not re.search(r"(?<!\d)(?!9000000)\d{10}(?!\d)", (KOK / "docs/urun/ornament78/URUN_AYAR.json").read_text())))
    return s


def main():
    s = testler()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"urun_ayar testleri TOPLAM: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
