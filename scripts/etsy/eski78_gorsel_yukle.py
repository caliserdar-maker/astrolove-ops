#!/usr/bin/env python3
"""23 ESKI galerili poster ilani: galeriyi hedef duzene (55 yeni galerili ilanla ayni 17 gorsel) getirir. ETSY'YE YAZAR
(Serdar onayi gerekir; once yalniz pilot 4570155846, gorsel onayindan sonra). Serdar 24 Eki B4: 17 Eki surumunun yerine.
Eski surum (17 Eki) sabit 18 gorsel + uretim galeri.json esitligi + rank overwrite ile calisiyordu; 21 Eki sonrasi galeriler 16-17
gorsel, cift kapakli ve rank'leri bozuk (rank 1 iki kez, rank 12 yok) oldugu icin kullanilamaz (overwrite KORU gorselini silerdi).
Girdi (ilan basina):
  --liste LISTE_<ilan>.csv (galeri_ornek.py: hedef_sira, hedef_gorsel, hedef_alt, islem KORU|ALT|DEGISTIR|CIKAR, simdi_id)
  --hedef-dir: DEGISTIR satirlarinin yuklenecek dosyalari (hedef_gorsel adiyla; kart_nokta_marka.py ciktisi varsa o)
  --manifest: hedef galeri manifesti (variation_images: renk adi -> hedef image_id; hedef_gorsel adindaki id ile eslenir)
Sira (her adim tek deneme, ilk sorunda DUR; her adimdan sonra galeri okunur ve DEVAM_<ilan>.json yazilir):
  0. kota kapisi (api.kota_kapisi, ilan basina; etsy_common esigi). state active degilse DUR (updateListing hic cagrilmaz).
  1. on kosul: canli gorsel kimlikleri = LISTE'deki simdi_id kumesi (KORU + ALT + CIKAR); degilse DUR. Yedek manifesti +
     CDN tam boy yedegi (YEDEK_CDN/, bu kosunun galeri okumasindan, ilk yazimdan once; inmezse yazim yok).
  2. adim plani YAZMADAN once kurulur (PLAN_<ilan>.json): her yuklemeden once bir CIKAR silinir (once bagsizlar); renk kartlari
     once yuklenir; kalan CIKAR'lar silinir. Planin en fazla gorsel sayisi IMG_LIMIT (20) asarsa yazma yok. Yukleme overwrite YOK,
     rank yok, yalniz alt metinle; her adimdan sonra galeri okunur. Kota: kalan - EN KOTU durum istek tahmini < sert taban ise
     yazma yok (istek_en_kotu). Yukleme hatasinda yeniden gondermeden once galeri okunur (yukle_guvenli, cift yukleme yok);
     yuklenen her dosyanin sha256'si + Etsy gorsel kimligi SONRA'da (yukleme_kaydi).
  3. sira + alt metin: her hedef sira icin listing_image_id + rank + alt_text yeniden POST (kapak_yukle_78 ile ayni cagri); oturmazsa
     (kimlik sirasi, rank 1..17, alt metin) bir gecis daha; ikincisinde de oturmazsa DUR, renk bagi yazilmaz.
  4. renk baglari EN SONDA (Serdar 24 Eki): TEK variation-images cagrisi (tum seti degistirir), geri okunur; bos / eksikse DUR.
     Bu cagridan sonra gorsellere baska yazim yok.
  5. geri okuma: 17 gorsel, kimlik sirasi = hedef, rank'ler 1..17 tekil ve artan, alt metinler = hedef, renk baglari 5 ve hedefle
     ayni, korunanlar (state, baslik, etiket, aciklama, envanter, video) degismemis. SONRA_<ilan>.json (gorsel URL'leri):
     yuklenen gorsellerin CDN NCC kontrolu kilitsiz ayri is akisinda yapilir (galeri_ornek.py ile).
Devam: DEVAM_<ilan>.json (is akisi onceki kosudan indirir) varsa ilk plan kullanilir, tamamlanan adimlar atlanir. Her yazimdan
once bekleyen adim kayda yazilir; kota tabaninda durulduysa bekleyen adim canli galeriyle kapatilir (devam_uzlas), sonra canli
galeri kayitla ayni degilse DUR. Yazimin olup olmadigi belirsiz hata (HTTP/ag, beklenmeyen galeri, belirsiz yukleme) kayda "hata"
yazar: otomatik devam YOK. Yalniz kota tabani (istek gonderilmeden) durmasi devam eder.
Kullanim: eski78_gorsel_yukle.py --ilan ID --liste LISTE.csv --hedef-dir DIR --manifest manifest.json --out OUT
          --confirm ESKI23_GALERI [--kuru]"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ONAY = "ESKI23_GALERI"
HEDEF_N = 17
YUKLE_DENEME = 2   # yukleme: en fazla 2 gonderim; ikincisi yalniz KESIN 4xx (gorsel olusmadi) yanitindan sonra
SIRA_TEKRAR = 3    # sira / alt metin POST'u: post_file varsayilan tekrar (ayni govde, idempotent)


def istek_en_kotu(adimlar, basla=0, ilk=True):
    """Ilan basi istek tahmini, EN KOTU durum (Serdar 24 Eki: tahmin formulu duzeltmesi, yeni esik degil; baslangicta
    kalan - tahmin < sert taban ise ilan baslamaz). Koddaki her yol, yazma tekrarlari dahil:
      sil   = DELETE (etsy_common 5xx tekrari, en fazla 3) + kararli galeri (OKUMA_TEKRAR)
      yukle = 1. deneme (POST + 401 yenilemesiyle 2. POST + 1 galeri, kesin 4xx) + 2. deneme (2 POST + OKUMA_TEKRAR galeri)
              + adim sonu kararli galeri
      sira  = 2 gecis x (17 POST x SIRA_TEKRAR + kararli galeri)
      bag   = POST (5xx tekrari 3) + kararli var_img
      on okuma 7 (korunanlar 3, galeri, var_img x2, envanter; devamda 6), son okuma = galeri + var_img kararli + korunanlar 3.
    DAHIL DEGIL: GET okumalarinin etsy_common 5xx / 429 kisa tekrarlari (her okuma 3'e katlanirdi). Bu durumda sert taban (10)
    istek gondermeden durdurur; bekleyen adim DEVAM kaydinda, devam kosusu canli galeriyle uzlastirip kaldigi yerden surer.
    basla: devam kosusunda tamamlanan adimlar sayilmaz."""
    O = G.OKUMA_TEKRAR
    birim = {"sil": 3 + O, "yukle": (2 + 1) + (2 + O) + O, "sira": 2 * (HEDEF_N * SIRA_TEKRAR + O), "bag": 3 + O}
    return (7 if ilk else 6) + sum(birim[a[0]] for a in adimlar[basla:]) + 2 * O + 3


def sha256(yol):
    import hashlib
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cdn_indir(url):
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        return r.read()


def cdn_yedek(g0, hedef):
    """Canli galerinin tam boy yedegi, betigin kendi Etsy okumasindan (g0, url_fullxfull), ilk yazimdan ONCE (Serdar 24 Eki madde 4:
    eski kart kaydina bagli degil). Bir dosya inmezse yazim yok."""
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    for x in g0:
        u = x.get("url_fullxfull")
        if not u:
            raise Dur(f"CDN yedek: {x.get('listing_image_id')} url_fullxfull yok; yazim yok")
        try:
            (hedef / f"{int(x.get('rank') or 0):02d}_{x.get('listing_image_id')}.jpg").write_bytes(cdn_indir(u))
        except Exception as e:   # noqa: BLE001
            raise Dur(f"CDN yedek indirilemedi ({x.get('listing_image_id')}): {str(e)[:100]}; yazim yok")
    return len(g0)


def yukle_guvenli(api, shop, lid, yol, ad, alt_text, ids):
    """Tek gorsel yukleme, cift yukleme onlemeli (Serdar 24 Eki madde 2). post_file tekrar=1: hata yanitinda yeniden gondermez.
    Hata ya da kimliksiz yanit -> galeri okunur. Bilinen kumede olmayan TEK yeni gorsel ve alt metni bu gorselinki ise yukleme olmus
    sayilir (tekrar yok); yeni gorsel baska alt metinli ya da birden fazlaysa DUR. Galeride yeni gorsel yoksa: yalniz KESIN 4xx
    yanitindan sonra bir kez daha gonderilir; 5xx / zaman asimi / baglanti hatasi / kimliksiz yanitta (Etsy islemeyi surdurebilir)
    OKUMA_TEKRAR kez okunur, gorsel yine yoksa DUR (tekrar gonderilmez). -> (listing_image_id, deneme)"""
    son_hata = ""
    for deneme in range(1, YUKLE_DENEME + 1):
        kod = None
        try:
            with open(yol, "rb") as fh:
                y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (ad, fh, "image/jpeg")},
                                  data={"alt_text": alt_text}, tekrar=1)
            yid = (y or {}).get("listing_image_id")
            if yid and yid not in ids:
                return yid, deneme
            son_hata = f"yanit kimligi {yid}"
        except SystemExit as e:
            if str(e.code).startswith("DUR: kota"):   # istek gonderilmeden durdu
                raise
            son_hata = str(e.code)[:200]
            m = re.search(r"-> (\d{3})", son_hata)
            kod = int(m.group(1)) if m else None
        except Exception as e:   # noqa: BLE001 zaman asimi / baglanti: yukleme olmus olabilir
            son_hata = str(e)[:200]
        kesin = kod is not None and 400 <= kod < 500
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: bool(set(ids_of(g)) - ids), tekrar=1 if kesin else G.OKUMA_TEKRAR)
        yeni = [x for x in g if x.get("listing_image_id") not in ids]
        if len(yeni) == 1 and (yeni[0].get("alt_text") or "") == alt_text:
            log(f"    yukleme hatasi ({son_hata[:100]}) ama galeride yeni gorsel {yeni[0]['listing_image_id']} (alt metin ayni): "
                "yuklenmis sayildi, tekrar yok")
            return yeni[0]["listing_image_id"], deneme
        if yeni:
            raise Dur(f"yukleme sonrasi galeride {len(yeni)} yeni gorsel / alt metin farkli "
                      f"({[(x.get('listing_image_id'), (x.get('alt_text') or '')[:30]) for x in yeni]}); elle bakilmali")
        if not kesin:
            raise Dur(f"yukleme sonucu belirsiz ({son_hata[:100]}); galeride yeni gorsel yok; cift yukleme riski nedeniyle tekrar "
                      "gonderilmedi, elle bakilmali")
        log(f"    yukleme {kod} ({son_hata[:80]}); galeride yeni gorsel yok, bir kez daha (deneme {deneme}/{YUKLE_DENEME})")
    raise Dur(f"yukleme {YUKLE_DENEME} denemede olmadi ({ad}): {son_hata[:120]}")


def devam_uzlas(K, g0, alt_ad):
    """Devam (Serdar 24 Eki inceleme Y1): her yazimdan ONCE bekleyen adim kayda yazilir. Kosu yazimdan sonra (ornegin okuma
    sirasinda kota tabani) durduysa bekleyen adim canli galeriyle kapatilir: silinen gorsel galeride yoksa silme olmus; yuklemede
    galeride tek yeni gorsel ve alt metni ayniysa yukleme olmus. Sonra canli galeri kayitla birebir ayni olmali, degilse DUR."""
    ids = set(K.d["son_ids"]); b = K.d.get("bekleyen")
    canli = {x.get("listing_image_id"): x for x in g0}
    if b and b[0] == "sil" and b[1] not in canli:
        ids.discard(b[1]); K.d["silinen"].append(b[1]); K.d["adim"] = K.d.get("adim", 0) + 1
        log(f"  devam: bekleyen silme {b[1]} olmus")
    elif b and b[0] == "yukle":
        yeni = [x for i, x in canli.items() if i not in ids]
        if len(yeni) == 1 and (yeni[0].get("alt_text") or "") == alt_ad.get(b[1]):
            ids.add(yeni[0]["listing_image_id"]); K.d["yuklenen"][b[1]] = yeni[0]["listing_image_id"]
            K.d["adim"] = K.d.get("adim", 0) + 1
            log(f"  devam: bekleyen yukleme {b[1]} olmus -> {yeni[0]['listing_image_id']}")
        elif yeni:
            raise Dur(f"devam: bekleyen yukleme {b[1]} icin galeride {len(yeni)} yeni gorsel / alt metin farkli; elle bakilmali")
    K.d["bekleyen"] = None
    if set(canli) != ids:
        raise Dur(f"devam: canli galeri son kayittan farkli (+{sorted(set(canli) - ids)} -{sorted(ids - set(canli))}); elle bakilmali")
    K.d["son_ids"] = sorted(ids)


YASAK_ALT = re.compile(r"[\u2014\u2013]|AstroLove(?!Art)|hahnem|photo\s*rag|gicl[eé]e|prodigi|cotton|museum|\b308\b", re.I)


def adim_plani(n0, cikar, bagli0, yukle, renk_siralari):
    """Adim listesi + en fazla gorsel sayisi. Her yuklemeden once bir CIKAR silinir (sayi n0 civarinda kalir); kalan CIKAR'lar
    sonra silinir; sira + alt metin; renk baglari EN SONDA tek cagriyla (Serdar 24 Eki: kosu 40091265199'da baglar sira adimindan
    sonra bos okundu). Bagli CIKAR silinince bag gecici cozulur (cl_galeri_degistir faz1 ile ayni). bagli0 / renk_siralari
    plan sirasini artik degistirmez (imza uyumu); renk kartlari yine once yuklenir."""
    from collections import deque
    bos = deque([c for c in cikar if c not in bagli0] + [c for c in cikar if c in bagli0])
    renk_yuk = [r for r in yukle if int(r["hedef_sira"]) in renk_siralari]
    diger = [r for r in yukle if int(r["hedef_sira"]) not in renk_siralari]
    adim, n, mx = [], n0, n0
    for r in renk_yuk + diger:
        if bos:
            adim.append(("sil", bos.popleft())); n -= 1
        adim.append(("yukle", r["hedef_gorsel"])); n += 1; mx = max(mx, n)
    while bos:
        adim.append(("sil", bos.popleft())); n -= 1
    adim.append(("sira",)); adim.append(("bag",))
    if n != HEDEF_N:
        raise Dur(f"plan sonu {n} gorsel ({HEDEF_N} beklenir)")
    return adim, mx


class Dur(Exception):
    pass


def log(m):
    print(m, flush=True)


def liste_oku(yol):
    rows = list(csv.DictReader(open(yol, encoding="utf-8")))
    hedef = sorted((r for r in rows if r["hedef_sira"]), key=lambda r: int(r["hedef_sira"]))
    cikar = [int(r["simdi_id"]) for r in rows if r["islem"] == "CIKAR"]
    if [int(r["hedef_sira"]) for r in hedef] != list(range(1, HEDEF_N + 1)):
        raise Dur(f"LISTE hedef siralari 1..{HEDEF_N} degil")
    for r in hedef:
        if r["islem"] not in ("KORU", "ALT", "DEGISTIR"):
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} islem {r['islem']}")
        if r["islem"] in ("KORU", "ALT") and not r["simdi_id"]:
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} {r['islem']} ama simdi_id yok")
        if not r["hedef_alt"] or len(r["hedef_alt"]) > 250:
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} alt metin bos ya da 250'den uzun")
        if YASAK_ALT.search(r["hedef_alt"]):
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} alt metninde yasak ifade / tire / Art'siz marka: {r['hedef_alt'][:80]!r}")
    return hedef, cikar


def hedef_id(ad):
    """NN_<id>.jpg -> id"""
    return int(Path(ad).stem.split("_", 1)[1])


class Kayit:
    def __init__(self, out, lid):
        self.p = Path(out) / f"DEVAM_{lid}.json"
        self.d = json.loads(self.p.read_text()) if self.p.exists() else dict(silinen=[], yuklenen={}, baglar=False, sira=False,
                                                                             son_ids=None)

    def yaz(self, ids):
        self.d["son_ids"] = sorted(ids); self.p.write_text(json.dumps(self.d, indent=1))


def ids_of(g):
    return [x.get("listing_image_id") for x in g]


def renk_sira(man, hedef, rv):
    """manifest variation_images (renk -> hedef image_id) -> {renk: hedef_sira}; 5 degilse DUR."""
    sira_h = {hedef_id(r["hedef_gorsel"]): int(r["hedef_sira"]) for r in hedef}
    hbag = {}
    for v in man.get("variation_images") or []:
        ad = v.get("value"); hid = v.get("image_id")
        if ad not in rv or hid not in sira_h:
            raise Dur(f"hedef renk bagi eslenemedi ({ad} -> {hid})")
        hbag[ad] = sira_h[hid]
    if len(hbag) != 5:
        raise Dur(f"hedef manifestte {len(hbag)} renk bagi (5 beklenir)")
    return hbag


def galeri_sorun(g, son, alt):
    """canli galeri (rank sirali) hedefle: kimlik sirasi, rank 1..17, alt metin. -> sorun listesi"""
    bek = [son[s] for s in range(1, HEDEF_N + 1)]
    sorun = []
    if len(g) != HEDEF_N:
        sorun.append(f"gorsel sayisi {len(g)} ({HEDEF_N} beklenir)")
    if ids_of(g) != bek:
        sorun.append(f"sira {ids_of(g)}")
    rk = [x.get("rank") for x in g]
    if rk != list(range(1, HEDEF_N + 1)):
        sorun.append(f"rank 1..{HEDEF_N} tekil/artan degil: {rk}")
    alt_son = [x.get("alt_text") or "" for x in g]
    alt_bek = [alt.get(s) for s in range(1, HEDEF_N + 1)]
    if alt_son != alt_bek:
        sorun.append("alt metin: " + "; ".join(f"r{i + 1}" for i, (a_, b_) in enumerate(zip(alt_son, alt_bek)) if a_ != b_))
    return sorun


BAG_ISTEK = 30   # yalniz bag modu istek tahmini: korunanlar 2x(3-4), renk 1, galeri 2, var_img 1 + kararli <= 8, POST 1 (+5xx tekrar 2)
                 # (etsy_common _call 5xx'te ayni govdeyi en fazla 2 kez yeniden gonderir; variation-images tum seti degistirir)
ONAY_BAG = "ESKI23_BAG"


def bag_kur(api, shop, lid, liste, manifest, devam, out, bag_arg=None, yaz=False):
    """Serdar 24 Eki: yukleme bittikten sonra bos kalan renk baglarini TEK variation-images cagrisiyla kurar (yaz=True) ya da
    yalniz okur (yaz=False). Gorsellere hicbir yazim yok. Beklenen galeri: LISTE KORU/ALT simdi_id + DEVAM_<ilan>.json yuklenen.
    Yazmadan once canli galeri 17 / sira / alt metin hedefle ayni olmali; degilse DUR. Bag geri okumasi tutmazsa yeniden yazma YOK."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    hedef, _ = liste_oku(liste)
    man = json.loads(Path(manifest).read_text())
    if str(man.get("listing_id")) != str(lid):
        raise Dur(f"manifest baska ilana ait ({man.get('listing_id')})")
    dv = json.loads(Path(devam).read_text())
    son = {int(r["hedef_sira"]): int(r["simdi_id"]) if r["islem"] in ("KORU", "ALT") else dv["yuklenen"].get(r["hedef_gorsel"])
           for r in hedef}
    if any(v is None for v in son.values()):
        raise Dur("DEVAM kaydinda yuklenen gorsel eksik")
    alt = {int(r["hedef_sira"]): r["hedef_alt"] for r in hedef}
    kor0 = G.korunanlar(api, shop, lid)
    if hasattr(api, "kota_kapisi"):
        api.kota_kapisi(f"ilan {lid}")
    if kor0["state"] != "active":
        raise Dur(f"state {kor0['state']} (active degil)")
    rv = G.renk_degerleri(api, lid)
    if len(rv) != 5:
        raise Dur(f"envanterde 5 renk yok ({sorted(rv)})")
    hbag = renk_sira(man, hedef, rv)
    hedef_bag = {ad: son[s] for ad, s in hbag.items()}
    if bag_arg is not None and bag_arg != hedef_bag:
        raise Dur(f"verilen baglar LISTE/manifest/DEVAM ile ayni degil: verilen {bag_arg} | hesaplanan {hedef_bag}")
    g0 = G.galeri(api, lid)
    s0 = galeri_sorun(g0, son, alt)
    v0 = {v.get("value"): v.get("image_id") for v in G.var_img(api, shop, lid)}
    log(f"ONCE {lid}: {len(g0)} gorsel, galeri sorunu {len(s0)}, renk baglari {len(v0)} | kota {api.remaining}")
    if s0:
        raise Dur(f"galeri hedefle ayni degil, bag yazilmaz: {s0}")
    yazildi = False
    if yaz and v0 != hedef_bag:
        taban = getattr(api, "sert_taban", None)
        if taban is not None and api.remaining is not None and int(api.remaining) - BAG_ISTEK < int(taban):
            raise Dur(f"kota yetmez: kalan {api.remaining} - tahmini {BAG_ISTEK} < sert taban {taban}; yazma yok")
        vi = [{"property_id": rv[ad][0], "value_id": rv[ad][1], "image_id": hedef_bag[ad]} for ad in sorted(hedef_bag)]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})   # TEK cagri, tekrar yok
        yazildi = True
        log(f"  variation-images POST (5 bag) | kota {api.remaining}")
    v1l = G.kararli(lambda: G.var_img(api, shop, lid), lambda vm: {v.get("value"): v.get("image_id") for v in vm} == hedef_bag)
    v1 = {v.get("value"): v.get("image_id") for v in v1l}
    g1 = G.galeri(api, lid)
    sorun = galeri_sorun(g1, son, alt)
    if v1 != hedef_bag:
        sorun.append(f"renk baglari {v1}" + (" (BOS)" if not v1 else "") + (" -> yeniden yazma YOK, DUR" if yazildi else ""))
    kor1 = G.korunanlar(api, shop, lid)
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if kor1.get(k) != kor0.get(k):
            sorun.append(f"korunan {k}")
    R = dict(ilan=lid, mod="bag" if yaz else "oku", yazildi=yazildi, sonuc="FAIL" if sorun else "PASS", sorun=sorun, gorsel=len(g1),
             bag_once=v0, baglar=v1, bag_hedef=hedef_bag, bag_sayisi=sum(v1.get(k) == v for k, v in hedef_bag.items()),
             istek=api.calls, kota=api.remaining,
             galeri=[dict(rank=x.get("rank"), listing_image_id=x.get("listing_image_id"), alt_text=x.get("alt_text"),
                          url_fullxfull=x.get("url_fullxfull")) for x in g1])
    (out / f"{'BAG' if yaz else 'OKU'}_{lid}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    return R


def bir_ilan(api, shop, lid, liste, hedef_dir, manifest, out, kuru=False, kota_ihtiyac=True):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    hedef, cikar = liste_oku(liste)
    man = json.loads(Path(manifest).read_text())
    if str(man.get("listing_id")) != str(lid):
        raise Dur(f"manifest baska ilana ait ({man.get('listing_id')})")
    kor0 = G.korunanlar(api, shop, lid)
    if hasattr(api, "kota_kapisi"):   # ilk yanittan SONRA (remaining okunmadan kapi etkisizdi; 24 Eki inceleme)
        api.kota_kapisi(f"ilan {lid}")
    if kor0["state"] != "active":
        raise Dur(f"state {kor0['state']} (active degil)")
    K = Kayit(out, lid)
    if K.d.get("hata"):
        raise Dur(f"onceki kosu hatayla durdu ({K.d['hata'][:120]}); otomatik devam yok, elle bakilmali")
    g0 = G.galeri(api, lid); canli = set(ids_of(g0))
    simdi = {int(r["simdi_id"]) for r in hedef if r["simdi_id"]} | set(cikar)
    ilk = True
    if K.d["son_ids"] is None:
        if canli != simdi:
            raise Dur(f"canli galeri LISTE ile ayni degil: +{sorted(canli - simdi)} -{sorted(simdi - canli)}")
        (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(galeri=g0, variation_images=G.var_img(api, shop, lid), korunan=kor0),
                                                          indent=1, ensure_ascii=False))
        K.d["korunan0"] = kor0
    else:
        ilk = False
        devam_uzlas(K, g0, {r["hedef_gorsel"]: r["hedef_alt"] for r in hedef})
        kor0 = K.d["korunan0"]
    rv = G.renk_degerleri(api, lid)
    if len(rv) != 5:
        raise Dur(f"envanterde 5 renk yok ({sorted(rv)})")
    h_id = {int(r["hedef_sira"]): hedef_id(r["hedef_gorsel"]) for r in hedef}
    hbag = renk_sira(man, hedef, rv)
    yukle = [r for r in hedef if r["islem"] == "DEGISTIR"]
    for r in yukle:
        if not (Path(hedef_dir) / r["hedef_gorsel"]).exists():
            raise Dur(f"yuklenecek dosya yok: {r['hedef_gorsel']}")
    bagli0 = {v.get("image_id") for v in G.var_img(api, shop, lid)}
    if K.d.get("plan"):   # devam: ilk plan kullanilir (yeniden kurulmaz; 24 Eki inceleme Y1)
        adimlar = [tuple(x) for x in K.d["plan"]]; enfazla = K.d.get("en_fazla", 0)
    else:
        adimlar, enfazla = adim_plani(len(g0), cikar, bagli0, yukle, set(hbag.values()))
        K.d["plan"] = [list(x) for x in adimlar]; K.d["en_fazla"] = enfazla
    tahmin = istek_en_kotu(adimlar, K.d.get("adim", 0), ilk=ilk)
    plan = dict(ilan=lid, cikar=cikar, cikar_bagli=sorted(set(cikar) & bagli0), yukle=[r["hedef_gorsel"] for r in yukle],
                baglar={k: h_id[s] for k, s in hbag.items()}, baslangic=len(g0), en_fazla_gorsel=enfazla, adimlar=adimlar,
                tahmini_istek=tahmin, tahmin_yontemi="en kotu durum (istek_en_kotu)")
    (out / f"PLAN_{lid}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    log(f"PLAN {lid}: cikar {len(cikar)} (bagli {len(plan['cikar_bagli'])}) | yukle {len(yukle)} | baglar 5 | basta {len(g0)} | "
        f"en fazla {enfazla} gorsel | tahmini istek {tahmin}")
    if enfazla > G.IMG_LIMIT:
        raise Dur(f"plan {G.IMG_LIMIT} gorsel sinirini asiyor (en fazla {enfazla}); yazma yok")
    if kuru:
        return dict(ilan=lid, sonuc="KURU", plan=plan, istek=api.calls, kota=api.remaining)
    taban = getattr(api, "sert_taban", None)
    if kota_ihtiyac and taban is not None and api.remaining is not None and int(api.remaining) - tahmin < int(taban):
        raise Dur(f"kota yetmez: kalan {api.remaining} - tahmini {tahmin} < sert taban {taban} (ilan yarida kalirdi); yazma yok")
    if ilk and not K.d.get("cdn"):
        K.d["cdn"] = cdn_yedek(g0, out / "YEDEK_CDN")
        log(f"CDN yedek: {K.d['cdn']} gorsel (canli galeri, bu kosunun Etsy okumasi)")
    ids = set(K.d["son_ids"]) if K.d["son_ids"] is not None else set(canli)
    yol = {r["hedef_gorsel"]: r for r in yukle}
    son = {}

    def son_kur():
        for r in hedef:
            s = int(r["hedef_sira"])
            son[s] = int(r["simdi_id"]) if r["islem"] in ("KORU", "ALT") else K.d["yuklenen"].get(r["hedef_gorsel"])
    alt = {int(r["hedef_sira"]): r["hedef_alt"] for r in hedef}
    try:
        for n, a in enumerate(adimlar):
            if n < K.d.get("adim", 0):
                continue
            K.d["bekleyen"] = list(a); K.yaz(ids)   # yazimdan ONCE: kosu bu adimda durursa devam uzlastirir
            if a[0] == "sil":
                c = a[1]
                G.gorsel_sil(api, shop, lid, c); K.d["silinen"].append(c); ids.discard(c)
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                if set(ids_of(g)) != ids:
                    K.yaz(ids_of(g)); raise Dur(f"silme sonrasi galeri beklenen degil ({c})")
                log(f"  [{n + 1}/{len(adimlar)}] sil {c} -> {len(ids)} gorsel | kota {api.remaining}")
            elif a[0] == "yukle":
                r = yol[a[1]]
                dyol = Path(hedef_dir) / r["hedef_gorsel"]
                K.d.setdefault("sha", {})[r["hedef_gorsel"]] = sha256(dyol)   # icerik kaydi (Serdar 24 Eki madde 5)
                yid, deneme = yukle_guvenli(api, shop, lid, dyol, r["hedef_gorsel"], r["hedef_alt"], ids)
                K.d["yuklenen"][r["hedef_gorsel"]] = yid; ids.add(yid)
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                if set(ids_of(g)) != ids:
                    K.yaz(ids_of(g)); raise Dur(f"yukleme sonrasi galeri beklenen degil ({r['hedef_gorsel']} -> {yid})")
                log(f"  [{n + 1}/{len(adimlar)}] yukle {r['hedef_gorsel']} -> {yid} (deneme {deneme}) | {len(ids)} gorsel | kota {api.remaining}")
            elif a[0] == "bag":
                son_kur()
                vi = [{"property_id": rv[ad][0], "value_id": rv[ad][1], "image_id": son[s]} for ad, s in sorted(hbag.items())]
                if any(v["image_id"] is None for v in vi):
                    raise Dur("renk bagi icin hedef gorsel henuz yok (plan hatasi)")
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
                hedef_bag = {ad: son[s] for ad, s in hbag.items()}

                def bag_ok(vm):
                    vm = {v.get("value"): v.get("image_id") for v in vm}
                    return len(vm) == 5 and all(vm.get(k) == v for k, v in hedef_bag.items())
                v1 = G.kararli(lambda: G.var_img(api, shop, lid), bag_ok)
                if not bag_ok(v1):
                    raise Dur(f"renk baglari dogrulanamadi: {[(v.get('value'), v.get('image_id')) for v in v1]}")
                log(f"  [{n + 1}/{len(adimlar)}] renk baglari 5/5")
            elif a[0] == "sira":
                son_kur()
                if set(son.values()) != ids or len(ids) != HEDEF_N:
                    raise Dur(f"sira oncesi galeri {len(ids)} gorsel, hedef kumesi ile ayni degil")
                bek = [son[s] for s in range(1, HEDEF_N + 1)]
                oturdu = False
                for gecis in (1, 2):   # kapak_yukle_78 (28 Eyl): rank cagrisi bazen oturmuyor; bir kez daha, sonra DUR
                    for s in range(1, HEDEF_N + 1):
                        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                                      files={"listing_image_id": (None, str(son[s])), "rank": (None, str(s)), "alt_text": (None, alt[s])})
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: not galeri_sorun(g, son, alt))
                    if not galeri_sorun(g, son, alt):   # kimlik sirasi + rank 1..17 + alt metin (24 Eki inceleme O6)
                        oturdu = True; break
                    log(f"  sira gecis {gecis} oturmadi: {galeri_sorun(g, son, alt)[:2]}")
                if not oturdu:   # Serdar 24 Eki madde 3: renk bagi yazilmaz
                    K.yaz(ids_of(g)); raise Dur(f"sira 2 geciste oturmadi ({galeri_sorun(g, son, alt)[:2]}); renk bagi yazilmadi")
                log(f"  [{n + 1}/{len(adimlar)}] sira + alt metin")
            K.d["adim"] = n + 1; K.d["bekleyen"] = None; K.yaz(ids)
    except SystemExit as e:   # etsy_common "DUR: kota ...": o istek gonderilmeden durur; bekleyen adim kayitli, devam uzlastirir
        if not str(e.code).startswith("DUR: kota"):
            K.d["hata"] = str(e.code)[:300]
        K.p.write_text(json.dumps(K.d, indent=1)); raise Dur(str(e.code)[:300])   # son_ids: bekleyen adimdan onceki durum
    except Exception as e:   # noqa: BLE001 Dur, HTTP / ag hatasi: yazimin olup olmadigi belirsiz -> otomatik devam yok
        K.d["hata"] = str(e)[:300]; K.p.write_text(json.dumps(K.d, indent=1)); raise Dur(str(e)[:300])
    son_kur()
    bek = [son[s] for s in range(1, HEDEF_N + 1)]
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: ids_of(g) == bek)
    sorun = galeri_sorun(g, son, alt)
    hb = {ad: son[s] for ad, s in hbag.items()}   # tekrarli okuma: var_img 404'te de [] doner (24 Eki inceleme)
    bag1 = {v.get("value"): v.get("image_id") for v in G.kararli(lambda: G.var_img(api, shop, lid),
                                                                  lambda vm: {v.get("value"): v.get("image_id") for v in vm} == hb)}
    if bag1 != hb:
        sorun.append(f"renk baglari {bag1}" + (" (BOS)" if not bag1 else ""))
    kor1 = G.korunanlar(api, shop, lid)
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if kor1.get(k) != kor0.get(k):
            sorun.append(f"korunan {k}")
    kayit = [dict(hedef_sira=int(r["hedef_sira"]), hedef_gorsel=r["hedef_gorsel"], sha256=K.d.get("sha", {}).get(r["hedef_gorsel"]),
                  listing_image_id=K.d["yuklenen"].get(r["hedef_gorsel"])) for r in yukle]
    R = dict(ilan=lid, sonuc="FAIL" if sorun else "PASS", sorun=sorun, gorsel=len(g), yuklenen=K.d["yuklenen"], yukleme_kaydi=kayit,
             silinen=K.d["silinen"], baglar=bag1, istek=api.calls, kota=api.remaining,
             galeri=[dict(rank=x.get("rank"), listing_image_id=x.get("listing_image_id"), alt_text=x.get("alt_text"),
                          url_fullxfull=x.get("url_fullxfull")) for x in g])
    (out / f"SONRA_{lid}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    return R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ilan", required=True); ap.add_argument("--liste", required=True); ap.add_argument("--hedef-dir", required=True)
    ap.add_argument("--manifest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--kota-ihtiyac", type=int, default=1, help="1: kalan - tahmini istek < sert taban ise yazmadan DUR (varsayilan)")
    ap.add_argument("--mod", choices=("galeri", "bag", "oku"), default="galeri",
                    help="galeri: tam akis | bag: yalniz renk baglari (TEK cagri, --confirm ESKI23_BAG) | oku: salt okuma")
    ap.add_argument("--devam", default="", help="bag/oku: DEVAM_<ilan>.json (yuklenen gorsel kimlikleri)")
    ap.add_argument("--bag", default="", help="bag/oku: 'Renk=image_id,...' beklenen 5 bag (hesaplananla ayni olmali)")
    a = ap.parse_args()
    if not a.ilan.isdigit():
        raise SystemExit("DUR: --ilan yalniz rakam")
    if a.mod == "bag" and a.confirm != ONAY_BAG:
        raise SystemExit(f"DUR: bag yazimi icin --confirm {ONAY_BAG}")
    if a.mod == "galeri" and not a.kuru and a.confirm != ONAY:
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY}")
    bag_arg = None
    if a.bag:
        bag_arg = {k.strip(): int(v) for k, v in (x.split("=") for x in a.bag.split(","))}
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    try:
        if a.mod == "galeri":
            R = bir_ilan(api, shop, a.ilan, a.liste, a.hedef_dir, a.manifest, a.out, kuru=a.kuru, kota_ihtiyac=bool(a.kota_ihtiyac))
        else:
            R = bag_kur(api, shop, a.ilan, a.liste, a.manifest, a.devam, a.out, bag_arg=bag_arg, yaz=a.mod == "bag")
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001 (requests zaman asimi / baglanti hatasi dahil)
        R = dict(ilan=a.ilan, sonuc="DUR", sorun=[str(e)[:500]], kota=api.remaining, istek=api.calls)
        dv = Path(a.out) / f"DEVAM_{a.ilan}.json"
        if dv.exists():   # kismi icerik kaydi (madde 5): yuklenen kimlik + sha256
            d = json.loads(dv.read_text())
            R.update(yuklenen=d.get("yuklenen"), sha256=d.get("sha"), adim=d.get("adim"), bekleyen=d.get("bekleyen"))
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"DUR_{a.ilan}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print("ESKI23_GALERI", json.dumps({k: R.get(k) for k in ("ilan", "mod", "sonuc", "sorun", "gorsel", "bag_sayisi", "istek",
                                                                                        "kota") if k in R}, ensure_ascii=False),
          flush=True)
    return 0 if R["sonuc"] in ("PASS", "KURU") else 1


if __name__ == "__main__":
    sys.exit(main())
