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
Devam / kurtarma: DEVAM_<ilan>.json (her yazimdan once ve hemen sonra yerel + Drive; LISTE sha256 + uretim kosusu kimligi) varsa
kayitli plan kullanilir; canli galeri iki ardisik ayni okumaya kadar okunur ve durum_uzlas tamamlanan adimlari bulur (kayitli
yukleme kimlikleri once; bizim alt metinli gorsel asla yeniden yuklenmez; belirsiz yukleme bulunamazsa DUR). Kota tabani durmasi
kendiliginden devam eder; kota disi hata "hata" kaydi yazar ve yalniz --kurtar ile surdurulur.
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
HEDEF_N = 17       # varsayilan hedef gorsel sayisi (eski 23 / 78 duzeni); v10 galeri 9 (Merkez 26 Eki, Serdar onayi)
ONAY_V10, HEDEF_V10 = "GALERI_V10", 9
YUKLE_DENEME = 2   # yukleme: en fazla 2 gonderim; ikincisi YALNIZ 429 (hiz siniri) sonrasi (Serdar 24 Eki madde 5)
BEKLE_429 = 15     # sn
SIRA_TEKRAR = 3    # sira / kapak rank POST'u: post_file varsayilan tekrar (ayni govde, idempotent)


def alt_norm(s):
    """Alt metin karsilastirmasi: bas/son ve ic bosluklar tek bosluk (Etsy'nin olasi bosluk duzeltmesi)."""
    return " ".join((s or "").split())


def istek_en_kotu(adimlar, basla=0, ilk=True, n=HEDEF_N):
    """Ilan basi istek tahmini, EN KOTU durum (Serdar 24 Eki: "tahmini istek + 10" kurali; baslangicta kalan - tahmin < sert
    taban ise ilan baslamaz). Koddaki her yol, yazma tekrarlari dahil:
      sil   = DELETE (etsy_common 5xx tekrari, en fazla 3) + kararli galeri (OKUMA_TEKRAR)
      yukle = 1. deneme (POST + 401 yenilemesiyle 2. POST + 1 galeri, 429) + 2. deneme (2 POST + OKUMA_TEKRAR galeri) + kararli
      kapak = rank POST (SIRA_TEKRAR) + kararli galeri;  sira = 2 gecis x (n POST x SIRA_TEKRAR + kararli galeri), n = hedef sayi
      bag   = POST (5xx tekrari 3) + kararli var_img
      on okuma: ilk kosu 7 (korunanlar 3, galeri, var_img x2, envanter); devam / kurtarma 5 + kararli galeri (OKUMA_TEKRAR)
      son okuma = galeri + var_img kararli + korunanlar 3.
    DAHIL DEGIL: GET okumalarinin etsy_common 5xx / 429 kisa tekrarlari. O durumda sert taban (10) istek gondermeden durdurur;
    devam / kurtarma kosusu kayitli plan + canli galeriyle kaldigi yerden surer. basla: tamamlanan adimlar sayilmaz."""
    O = G.OKUMA_TEKRAR
    birim = {"sil": 3 + O, "yukle": (2 + 1) + (2 + O) + O, "kapak": SIRA_TEKRAR + O, "sira": 2 * (n * SIRA_TEKRAR + O),
             "bag": 3 + O}
    return (7 if ilk else 5 + O) + sum(birim[a[0]] for a in adimlar[basla:]) + 2 * O + 3


def istek_en_az(adimlar, basla=0, ilk=True, n=HEDEF_N):
    """Ilan basi istek, EN AZ durum (tekrar yok, her okuma ilk seferde oturur): sil / yukle / kapak / bag = 1 yazim + 1 okuma;
    sira = n POST + 1 galeri; on okuma ilk kosu 7 (devam 5 + 1); son okuma 5."""
    birim = {"sil": 2, "yukle": 2, "kapak": 2, "sira": n + 1, "bag": 2}
    return (7 if ilk else 6) + sum(birim[a[0]] for a in adimlar[basla:]) + 5


def istek_yalin_en_kotu(adimlar, basla=0, ilk=True, n=HEDEF_N):
    """YALIN plan (galeri v11, Merkez 29 Eki karar 3) EN KOTU istek: adim arasi galeri okumasi yok.
      sil = DELETE (5xx tekrari 3); yukle = 2 deneme x (POST + 401 yenilemesi) + hata sonrasi kararli galeri (OKUMA_TEKRAR);
      bag = POST (3) + kararli var_img (silmeden ONCE dogrulanir; 29 Eki inceleme Y2);
      sira_kontrol = kararli galeri + oturmazsa 2 gecis x (n POST x SIRA_TEKRAR + kararli galeri) + sira POST'u bagi siler
      (19 Eyl olcumu, pod_rank3_onar.py) -> bag yeniden POST (3) + kararli var_img (29 Eki inceleme Y1);
      on okuma ilk kosu 1 (videolar; ilan / envanter / galeri / var_img kapi okumasindan onbellekte), devam 5 + kararli galeri;
      son = kararli galeri (sira POST'u olduysa) + kararli var_img + korunanlar 3."""
    O = G.OKUMA_TEKRAR
    birim = {"sil": 3, "yukle": (2 + 1) + (2 + O), "bag": 3 + O, "sira_kontrol": O + 2 * (n * SIRA_TEKRAR + O) + (3 + O) + O}
    return (1 if ilk else 5 + O) + sum(birim[a[0]] for a in adimlar[basla:]) + O + 3


def istek_yalin_en_az(adimlar, basla=0, ilk=True, n=HEDEF_N):
    """YALIN plan EN AZ: her yazim 1 istek, bag + 1 var_img dogrulama, sira_kontrol 1 galeri (oturdu), son var_img 1 + korunanlar 3;
    on okuma ilk 1 (devam 6)."""
    return (1 if ilk else 6) + sum(2 if a[0] == "bag" else 1 for a in adimlar[basla:]) + 4


def yalin_plan(cikar, yukle, hedef_n=HEDEF_N, koru=()):
    """YALIN adim plani (Merkez 29 Eki karar 3: yalniz degisen gorsel, alt metin ve sira yukleme isteginde, okuma tekrari yok):
      1. hedef gorseller hedef sirasinda yuklenir (rank = hedef sira, alt metin ayni istekte): kapak ilk yuklemeyle 1. sirada,
         yeni gorseller 1..n'de, eskiler arkada (gorsel sayisi en fazla canli + n, IMG_LIMIT altinda olmali).
      2. renk baglari TEK variation-images cagrisi (yeni renk kartlarina), eski gorseller silinmeden ONCE okunup dogrulanir.
      3. eski gorseller silinir (bagsiz; 404 = zaten silinmis, kimlik kumesi sira_kontrol'de dogrulanir).
      4. sira_kontrol: tek galeri okumasi; kimlik sirasi / rank / alt metin hedefle ayni degilse sira + alt metin POST'u (2 gecis)
         ve ardindan renk baglari YENIDEN yazilip dogrulanir (rank yazimi bagi siler, 19 Eyl olcumu; Serdar 24 Eki: bag en sonda).
    koru: yerinde kalan (KORU / ALT) hedef satirlari (galeri v11b, Serdar 29 Eki: eski MB kapak kalir); yalniz DEGISTIR yuklenir,
    sira_kontrol KORU gorsellerini de hedef sirasina ve alt metnine getirir.
    -> (adimlar, en fazla gorsel sayisi = canli (koru + cikar) + yukleme)"""
    yk = sorted(yukle, key=lambda r: int(r["hedef_sira"]))
    sira = sorted([int(r["hedef_sira"]) for r in yk] + [int(r["hedef_sira"]) for r in koru])
    if sira != list(range(1, hedef_n + 1)):
        raise Dur(f"yalin plan: yukleme + yerinde kalan hedef siralari 1..{hedef_n} degil ({sira})")
    adim = [("yukle", r["hedef_gorsel"]) for r in yk] + [("bag",)] + [("sil", c) for c in cikar] + [("sira_kontrol",)]
    return adim, len(cikar) + len(koru) + len(yk)


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


def stabil_galeri(api, lid, tekrar=None):
    """Canli galeri, ardisik iki okuma (kimlik, rank, alt metin) ayni cikana kadar okunur (Serdar 24 Eki madde 1). Olmazsa DUR."""
    onceki = None
    for i in range(tekrar or G.OKUMA_TEKRAR):
        if i:
            G.time.sleep(G.OKUMA_BEKLE)
        g = G.galeri(api, lid)
        imza = [(x.get("listing_image_id"), x.get("rank"), alt_norm(x.get("alt_text"))) for x in g]
        if imza == onceki:
            return g
        onceki = imza
    raise Dur("canli galeri okumasi kararli degil (ardisik iki okuma ayni cikmadi); yazim yok")


def yukle_guvenli(api, shop, lid, yol, ad, alt_text, ids, gonderilmedi=None, rank=None):
    """Tek gorsel yukleme, cift yukleme yok (Serdar 24 Eki madde 2 ve 5). post_file tekrar=1: hata yanitinda yeniden gondermez.
    Hata ya da kimliksiz yanit -> galeri okunur: bilinen kumede olmayan TEK yeni gorsel ve alt metni bu gorselinki ise yukleme olmus
    sayilir. Yeni gorsel baska alt metinli ya da birden fazlaysa DUR. Galeride yeni gorsel yoksa: YALNIZ 429'da BEKLE_429 sn bekleyip
    bir kez daha gonderilir; diger 4xx, 5xx, zaman asimi, baglanti hatasi, kimliksiz yanit -> OKUMA_TEKRAR kez okunur, gorsel yine
    yoksa DUR (yukleme yok). gonderilmedi: kota tabani istegi GONDERMEDEN durdurursa cagrilir (belirsizlik kaydi silinir).
    -> (listing_image_id, deneme)"""
    son_hata = ""
    for deneme in range(1, YUKLE_DENEME + 1):
        kod = None
        try:
            with open(yol, "rb") as fh:
                y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (ad, fh, "image/jpeg")},
                                  data={"alt_text": alt_text, **({"rank": str(rank)} if rank else {})}, tekrar=1)
            yid = (y or {}).get("listing_image_id")
            if yid and yid not in ids:
                return yid, deneme
            son_hata = f"yanit kimligi {yid}"
        except SystemExit as e:
            if str(e.code).startswith("DUR: kota"):   # istek gonderilmeden durdu (post_file _istek_oncesi)
                if gonderilmedi:
                    gonderilmedi()
                raise
            son_hata = str(e.code)[:200]
            m = re.search(r"-> (\d{3})", son_hata)
            kod = int(m.group(1)) if m else None
        except Exception as e:   # noqa: BLE001 zaman asimi / baglanti: yukleme olmus olabilir
            son_hata = str(e)[:200]
        hiz = kod == 429
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: bool(set(ids_of(g)) - ids), tekrar=1 if hiz else G.OKUMA_TEKRAR)
        yeni = [x for x in g if x.get("listing_image_id") not in ids]
        if len(yeni) == 1 and alt_norm(yeni[0].get("alt_text")) == alt_norm(alt_text):
            log(f"    yukleme hatasi ({son_hata[:100]}) ama galeride yeni gorsel {yeni[0]['listing_image_id']} (alt metin ayni): "
                "yuklenmis sayildi, tekrar yok")
            return yeni[0]["listing_image_id"], deneme
        if yeni:
            raise Dur(f"yukleme sonrasi galeride {len(yeni)} yeni gorsel / alt metin farkli "
                      f"({[(x.get('listing_image_id'), (x.get('alt_text') or '')[:30]) for x in yeni]}); elle bakilmali")
        if not hiz:
            raise Dur(f"yukleme hatasi ({son_hata[:100]}); galeride yeni gorsel yok; tekrar gonderilmedi (yalniz 429 tekrar edilir), "
                      "kurtarma ile ya da elle bakilmali")
        log(f"    yukleme 429 (hiz siniri); galeride yeni gorsel yok, {BEKLE_429} sn sonra bir kez daha (deneme {deneme}/{YUKLE_DENEME})")
        G.time.sleep(BEKLE_429)
    raise Dur(f"yukleme {YUKLE_DENEME} denemede olmadi ({ad}): {son_hata[:120]}")


def durum_uzlas(K, g, adimlar, alt_ad, ara_tekrar=False):
    """Devam ve kurtarma (Serdar 24 Eki madde 1-2): kayitli plan + kararli canli galeri -> tamamlanmis adimlar. Kural:
      sil c   : c galeride yoksa (ya da c bizim kayitli yuklememizin kimligiyse, Etsy kimligi yeniden verdi) olmus.
      yukle ad: kayitli kimlik galerideyse olmus; kayitli kimlik galeride yoksa DUR. Kayit yoksa (yanit kayda gecmeden kesildi):
                ilk galeride olmayan, kayitsiz ve alt metni bu gorselinki olan TEK gorsel bizimdir (asla yeniden yuklenmez);
                birden fazlaysa DUR. Belirsiz kalan yukleme (hata kaydi) bulunamazsa DUR (yukleme yok).
      kapak / sira / bag: tekrarlanir (ayni govde).
    Tamamlanan sil/yukle adimlari plan sirasinda bir onek olmali; galeride planla aciklanamayan gorsel kalmamali; sonra canli kume
    = ilk galeri - silinenler + yuklenenler olmali. Degilse DUR. -> (ids, sonraki adim indeksi)
    ara_tekrar=True (v10, inceleme 26 Eki): devam son TAMAMLANAN sil/yukle adimindan sonra baslar; aradaki kapak / bag adimlari
    tekrarlanir (yoksa erken bag atlanir, bagli eski renk kartlari bag kurulmadan silinir ve renk baglari sona kadar 0 kalir).
    Varsayilan False: 17 hedefli eski davranis aynen."""
    canli = {x.get("listing_image_id"): x for x in g}
    ids0 = set(K.d["ids0"]); yk = K.d["yuklenen"]; kayitli = {v for v in yk.values() if v is not None}
    for ad, i in yk.items():
        if i is not None and i not in canli:
            raise Dur(f"kurtarma/devam: kayitli yukleme {ad} -> {i} canli galeride yok; elle bakilmali")
    bilinmeyen = {i: x for i, x in canli.items() if i not in ids0 and i not in kayitli}
    olmus = []
    for a in adimlar:
        if a[0] == "sil":
            olmus.append(a[1] not in canli or a[1] in kayitli)
        elif a[0] == "yukle":
            ad = a[1]
            if yk.get(ad) is not None:
                olmus.append(True); continue
            aday = [i for i, x in bilinmeyen.items() if alt_norm(x.get("alt_text")) == alt_norm(alt_ad[ad])]
            aday += [c for c in K.d.get("silinen", []) if c in canli and c not in kayitli
                     and alt_norm(canli[c].get("alt_text")) == alt_norm(alt_ad[ad])]   # yeniden verilen kimlik
            aday = sorted(set(aday))
            if len(aday) > 1:
                raise Dur(f"kurtarma/devam: {ad} icin galeride {len(aday)} aday gorsel ({aday}); cift yukleme olabilir, elle bakilmali")
            if aday:
                yk[ad] = aday[0]; kayitli.add(aday[0]); bilinmeyen.pop(aday[0], None)
                log(f"  kurtarma/devam: {ad} kayitsiz ama galeride -> {aday[0]} (alt metin ayni), yeniden yuklenmez")
                olmus.append(True)
            elif K.d.get("belirsiz") == ad:
                raise Dur(f"kurtarma/devam: belirsiz yukleme {ad} galeride bulunamadi; yukleme yapilmadi. --kurtar bunu ACAMAZ: "
                          f"gorselin olusmadigi elle dogrulanip DEVAM kaydindaki 'belirsiz' alani elle silinmeli (cift yukleme riski)")
            else:
                olmus.append(False)
        else:
            olmus.append(None)
    if bilinmeyen:
        raise Dur(f"kurtarma/devam: galeride planla aciklanamayan gorsel {sorted(bilinmeyen)}; elle bakilmali")
    sy = [(n, o) for n, o in enumerate(olmus) if o is not None]
    ilk_eksik = next((n for n, o in sy if not o), None)
    if ilk_eksik is not None and any(o for n, o in sy if n > ilk_eksik):
        raise Dur("kurtarma/devam: tamamlanan adimlar plan sirasinda degil; elle bakilmali")
    if ilk_eksik is None:
        son_sy = max((n for n, _ in sy), default=-1)
        ilk_eksik = son_sy + 1
    if ara_tekrar:
        ilk_eksik = min(ilk_eksik, max((n for n, o in sy if o), default=-1) + 1)
    silinen = [a[1] for a, o in zip(adimlar, olmus) if a[0] == "sil" and o]
    yuklenen_ids = {yk[a[1]] for a, o in zip(adimlar, olmus) if a[0] == "yukle" and o}
    bek = (ids0 - set(silinen)) | yuklenen_ids
    if set(canli) != bek:
        raise Dur(f"kurtarma/devam: canli galeri beklenen kume degil (+{sorted(set(canli) - bek)} -{sorted(bek - set(canli))}); "
                  "elle bakilmali")
    K.d["silinen"] = silinen; K.d["adim"] = ilk_eksik; K.d["bekleyen"] = None; K.d.pop("belirsiz", None)
    return set(canli), ilk_eksik


YASAK_ALT = re.compile(r"[\u2014\u2013]|AstroLove(?!Art)|hahnem|photo\s*rag|gicl[eé]e|prodigi|cotton|museum|\b308\b", re.I)


def adim_plani(n0, cikar, bagli0, yukle, renk_siralari, kapak_degisir=None, hedef_n=HEDEF_N):
    """Adim listesi + en fazla gorsel sayisi (Serdar 24 Eki madde 4: musterinin yanlis kapak ve bagsiz galeri gordugu sure en az).
      1. kapak: hedef kapak yeni yuklenecekse ILK yuklenir; hemen rank 1 yapilir ("kapak" adimi). KORU kapak ise yalniz rank 1.
      2. renk kartlari: her birinden once bagSIZ bir CIKAR silinir (bagli eski renk kartlari yerinde kalir, renk secen musteri
         eski karti gorur ama bossuz kalmaz); 5 renk hedefi var olunca renk baglari HEMEN kurulur (erken "bag").
      3. diger yuklemeler: her birinden once bir CIKAR silinir (once bagsizlar, sonra artik bagdan cikmis eski renk kartlari).
      4. kalan CIKAR'lar silinir; sira + alt metin; renk baglari EN SONDA yeniden (son "bag"; 40091265199'da baglar sonda bos
         okunmustu, nedeni olculmedi).
    Gorsel sayisi en fazla n0 + 1 (kapak yuklemesi), IMG_LIMIT asilirsa bir_ilan yazmaz. kapak_degisir: hedef kapak satiri (DEGISTIR)
    ya da None. hedef_n: plan sonu beklenen gorsel sayisi."""
    from collections import deque
    bagsiz = deque(c for c in cikar if c not in bagli0); bagli = [c for c in cikar if c in bagli0]
    kapak = kapak_degisir
    renk_yuk = [r for r in yukle if int(r["hedef_sira"]) in renk_siralari and r is not kapak]
    diger = [r for r in yukle if int(r["hedef_sira"]) not in renk_siralari and r is not kapak]
    adim, n, mx = [], n0, n0
    if kapak is not None:
        adim.append(("yukle", kapak["hedef_gorsel"])); n += 1; mx = max(mx, n)
    adim.append(("kapak",))
    for r in renk_yuk:
        if bagsiz:
            adim.append(("sil", bagsiz.popleft())); n -= 1
        adim.append(("yukle", r["hedef_gorsel"])); n += 1; mx = max(mx, n)
    adim.append(("bag",))
    kalan = deque(list(bagsiz) + bagli)
    for r in diger:
        if kalan:
            adim.append(("sil", kalan.popleft())); n -= 1
        adim.append(("yukle", r["hedef_gorsel"])); n += 1; mx = max(mx, n)
    while kalan:
        adim.append(("sil", kalan.popleft())); n -= 1
    adim.append(("sira",)); adim.append(("bag",))
    if n != hedef_n:
        raise Dur(f"plan sonu {n} gorsel ({hedef_n} beklenir)")
    return adim, mx


class Dur(Exception):
    pass


def log(m):
    print(m, flush=True)


def liste_oku(yol, n=HEDEF_N):
    rows = list(csv.DictReader(open(yol, encoding="utf-8")))
    hedef = sorted((r for r in rows if r["hedef_sira"]), key=lambda r: int(r["hedef_sira"]))
    cikar = [int(r["simdi_id"]) for r in rows if r["islem"] == "CIKAR"]
    if [int(r["hedef_sira"]) for r in hedef] != list(range(1, n + 1)):
        raise Dur(f"LISTE hedef siralari 1..{n} degil")
    for r in hedef:
        if r["islem"] not in ("KORU", "ALT", "DEGISTIR", "DOKUNMA"):
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} islem {r['islem']}")
        if r["islem"] in ("KORU", "ALT", "DOKUNMA") and not r["simdi_id"]:
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} {r['islem']} ama simdi_id yok")
        if r["islem"] == "DOKUNMA":   # galeri v11b sira 1 canli MB kapak (Serdar 29 Eki): hicbir yazim yok; alt metin canlidaki
            continue                  # metin (yalniz karsilastirma), yasak ifade kapisi yazilan metinler icindir
        if not r["hedef_alt"] or len(r["hedef_alt"]) > 250:
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} alt metin bos ya da 250'den uzun")
        if YASAK_ALT.search(r["hedef_alt"]):
            raise Dur(f"LISTE hedef sira {r['hedef_sira']} alt metninde yasak ifade / tire / Art'siz marka: {r['hedef_alt'][:80]!r}")
    return hedef, cikar


def hedef_id(ad):
    """NN_<id>.jpg -> id"""
    return int(Path(ad).stem.split("_", 1)[1])


class Kayit:
    """DEVAM_<ilan>.json. Her yaz() yerel dosya + (DEVAM_HEDEF ortam degiskeni varsa) Drive'a rclone copyto (Serdar 24 Eki madde 3:
    runner kaybinda kayit kaybolmasin). Drive yazimi olmazsa bir kez daha denenir, yine olmazsa uyari (yerel kayit kosu sonunda
    Drive'a yine yazilir)."""
    def __init__(self, out, lid):
        self.p = Path(out) / f"DEVAM_{lid}.json"
        self.drive = os.environ.get("DEVAM_HEDEF") or ""
        self.d = json.loads(self.p.read_text()) if self.p.exists() else dict(silinen=[], yuklenen={}, son_ids=None)

    def yaz(self, ids=None):
        if ids is not None:
            self.d["son_ids"] = sorted(ids)
        self.p.write_text(json.dumps(self.d, indent=1))
        if self.drive:
            import subprocess
            for _ in range(2):
                try:
                    if subprocess.run(["rclone", "copyto", str(self.p), self.drive, "-q"], capture_output=True, timeout=90).returncode == 0:
                        return
                except Exception:   # noqa: BLE001
                    pass
            log(f"  UYARI: DEVAM Drive'a yazilamadi ({self.drive}); yerel kayit kosu sonunda yazilir")


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
    bek = int(man.get("renk_bag_sayisi") or 5)   # galeri v11b: 4 (Champagne Ivory bagsiz, Serdar 29 Eki)
    if len(hbag) != bek or len(hbag) != len(man.get("variation_images") or []):
        raise Dur(f"hedef manifestte {len(hbag)} renk bagi ({bek} beklenir)")
    return hbag


def galeri_sorun(g, son, alt, n=HEDEF_N):
    """canli galeri (rank sirali) hedefle: kimlik sirasi, rank 1..n, alt metin. -> sorun listesi"""
    bek = [son[s] for s in range(1, n + 1)]
    sorun = []
    if len(g) != n:
        sorun.append(f"gorsel sayisi {len(g)} ({n} beklenir)")
    if ids_of(g) != bek:
        sorun.append(f"sira {ids_of(g)}")
    rk = [x.get("rank") for x in g]
    if rk != list(range(1, n + 1)):
        sorun.append(f"rank 1..{n} tekil/artan degil: {rk}")
    alt_son = [alt_norm(x.get("alt_text")) for x in g]
    alt_bek = [alt_norm(alt.get(s)) for s in range(1, n + 1)]
    if alt_son != alt_bek:
        sorun.append("alt metin: " + "; ".join(f"r{i + 1}" for i, (a_, b_) in enumerate(zip(alt_son, alt_bek)) if a_ != b_))
    return sorun


BAG_ISTEK = 30   # yalniz bag modu istek tahmini: korunanlar 2x(3-4), renk 1, galeri 2, var_img 1 + kararli <= 8, POST 1 (+5xx tekrar 2)
                 # (etsy_common _call 5xx'te ayni govdeyi en fazla 2 kez yeniden gonderir; variation-images tum seti degistirir)
ONAY_BAG = "ESKI23_BAG"


def bag_kur(api, shop, lid, liste, manifest, devam, out, bag_arg=None, yaz=False, hedef_n=HEDEF_N):
    """Serdar 24 Eki: yukleme bittikten sonra bos kalan renk baglarini TEK variation-images cagrisiyla kurar (yaz=True) ya da
    yalniz okur (yaz=False). Gorsellere hicbir yazim yok. Beklenen galeri: LISTE KORU/ALT simdi_id + DEVAM_<ilan>.json yuklenen.
    Yazmadan once canli galeri hedef_n (17; v10 9) / sira / alt metin hedefle ayni olmali; degilse DUR. Bag geri okumasi tutmazsa
    yeniden yazma YOK."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    hedef, _ = liste_oku(liste, hedef_n)
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
    s0 = galeri_sorun(g0, son, alt, hedef_n)
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
    sorun = galeri_sorun(g1, son, alt, hedef_n)
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


def bir_ilan(api, shop, lid, liste, hedef_dir, manifest, out, kuru=False, kota_ihtiyac=True, kurtar=False, uretim_kosu="",
             hedef_n=HEDEF_N, cdn=True, ara_tekrar=False, yalin=False):
    """hedef_n: hedef gorsel sayisi (17; v10 9). cdn=False: CDN yedegi alinmaz (v10: Drive yedegi var ve canli kimlik kumesi
    yedekle ayni oldugu kilit oncesi kapida dogrulanir; kilit altinda toplu indirme yok).
    yalin=True (galeri v11, Merkez 29 Eki karar 3): yalin_plan; adim arasi galeri okumasi yok (DEVAM kaydi yazimdan once / hemen
    sonra aynen; devamda durum_uzlas kararli galeriyle), yukleme rank + alt metinle, bag tek POST (dogrulama son okumada),
    sira yalniz sira_kontrol okumasi tutmazsa yazilir."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    c0 = api.calls   # bu ilanin istekleri (cok ilanli kosuda api.calls onceki ilanlari da sayar)
    hedef, cikar = liste_oku(liste, hedef_n)
    liste_sha = sha256(liste)
    man = json.loads(Path(manifest).read_text())
    if str(man.get("listing_id")) != str(lid):
        raise Dur(f"manifest baska ilana ait ({man.get('listing_id')})")
    kor0 = G.korunanlar(api, shop, lid)
    if hasattr(api, "kota_kapisi"):   # ilk yanittan SONRA (remaining okunmadan kapi etkisizdi; 24 Eki inceleme)
        api.kota_kapisi(f"ilan {lid}")
    if kor0["state"] != "active":
        raise Dur(f"state {kor0['state']} (active degil)")
    K = Kayit(out, lid)
    ilk = K.d.get("son_ids") is None
    if not ilk and not all(k in K.d for k in ("plan", "ids0", "liste_sha")):
        raise Dur("devam: DEVAM kaydi eski bicimde (plan / ids0 / liste_sha yok); yazim yok, elle bakilmali")
    if not ilk:   # devam / kurtarma: ayni LISTE ve ayni uretim kosusu (Serdar 24 Eki madde 3)
        if K.d.get("liste_sha") != liste_sha or str(K.d.get("uretim_kosu") or "") != str(uretim_kosu or ""):
            raise Dur(f"devam: kayit baska LISTE / uretim kosusuyla baslamis (kayit {K.d.get('uretim_kosu')} {str(K.d.get('liste_sha'))[:12]}, "
                      f"simdi {uretim_kosu} {liste_sha[:12]}); yazim yok")
    if K.d.get("hata"):
        if not kurtar:
            raise Dur(f"onceki kosu hatayla durdu ({K.d['hata'][:120]}); otomatik devam yok (kurtarma modu ile surdurulur)")
        K.d.setdefault("hata_gecmis", []).append(K.d.pop("hata")); log("KURTARMA: onceki hata kaydi arsivlendi")
    elif kurtar and ilk:
        raise Dur("kurtarma: DEVAM kaydi yok (devam_kosu gerekli)")
    alt_ad = {r["hedef_gorsel"]: r["hedef_alt"] for r in hedef}
    simdi = {int(r["simdi_id"]) for r in hedef if r["simdi_id"]} | set(cikar)
    if {int(r["simdi_id"]) for r in hedef if r["islem"] == "DOKUNMA"} & set(cikar):
        raise Dur("LISTE: dokunulmaz gorsel CIKAR listesinde; yazim yok")
    rv = G.renk_degerleri(api, lid)
    if len(rv) != 5:
        raise Dur(f"envanterde 5 renk yok ({sorted(rv)})")
    h_id = {int(r["hedef_sira"]): hedef_id(r["hedef_gorsel"]) for r in hedef}
    hbag = renk_sira(man, hedef, rv)
    yukle = [r for r in hedef if r["islem"] == "DEGISTIR"]
    for r in yukle:
        if not (Path(hedef_dir) / r["hedef_gorsel"]).exists():
            raise Dur(f"yuklenecek dosya yok: {r['hedef_gorsel']}")
        if not ilk and r["hedef_gorsel"] in K.d.get("sha", {}) and K.d["sha"][r["hedef_gorsel"]] != sha256(Path(hedef_dir) / r["hedef_gorsel"]):
            raise Dur(f"devam: {r['hedef_gorsel']} dosyasi kayittaki sha256 ile ayni degil; yazim yok")
    if ilk:
        g0 = G.galeri(api, lid); canli = set(ids_of(g0))
        if canli != simdi:
            raise Dur(f"canli galeri LISTE ile ayni degil: +{sorted(canli - simdi)} -{sorted(simdi - canli)}")
        (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(galeri=g0, variation_images=G.var_img(api, shop, lid), korunan=kor0),
                                                          indent=1, ensure_ascii=False))
        K.d.update(korunan0=kor0, ids0=sorted(canli), liste_sha=liste_sha, uretim_kosu=str(uretim_kosu or ""))
        bagli0 = {v.get("image_id") for v in G.var_img(api, shop, lid)}
        kapak = next((r for r in yukle if int(r["hedef_sira"]) == 1), None)
        if yalin:
            adimlar, enfazla = yalin_plan(cikar, yukle, hedef_n, koru=[r for r in hedef if r["islem"] != "DEGISTIR"])
        else:
            adimlar, enfazla = adim_plani(len(g0), cikar, bagli0, yukle, set(hbag.values()), kapak_degisir=kapak, hedef_n=hedef_n)
        K.d["plan"] = [list(x) for x in adimlar]; K.d["en_fazla"] = enfazla; K.d["adim"] = 0
        K.d["cikar_bagli"] = sorted(set(cikar) & bagli0)
        ids = set(canli)
    else:
        kor0 = K.d["korunan0"]
        adimlar = [tuple(x) for x in K.d["plan"]]; enfazla = K.d.get("en_fazla", 0)
        if hasattr(api, "kapat"):   # v11 Onbellek: devamda kapi okumalari canli olmali (stabil_galeri iki CANLI okuma; 29 Eki inceleme O3)
            api.kapat()
        g0 = stabil_galeri(api, lid)
        ids, _ = durum_uzlas(K, g0, adimlar, alt_ad, ara_tekrar=ara_tekrar)
    basla = K.d.get("adim", 0)
    tahmin = (istek_yalin_en_kotu if yalin else istek_en_kotu)(adimlar, basla, ilk=ilk, n=hedef_n)
    taban = getattr(api, "sert_taban", None)
    gerek = tahmin - (api.calls - c0) + int(taban or 0)   # tahmin ilanin tamami; bu ilanda harcanan on okumalar dusulur
    yeter = api.remaining is None or int(api.remaining) >= gerek
    kota_durum = f"yukleme icin kota {'yeterli' if yeter else 'yetersiz'} (kalan {api.remaining}, gereken {gerek})"
    plan = dict(ilan=lid, cikar=cikar, cikar_bagli=K.d.get("cikar_bagli", []), yukle=[r["hedef_gorsel"] for r in yukle], baglar={k: h_id[s] for k, s in hbag.items()},
                baslangic=len(K.d["ids0"]), en_fazla_gorsel=enfazla, adimlar=adimlar, basla=basla, tahmini_istek=tahmin,
                tahmin_yontemi="en kotu durum (" + ("istek_yalin_en_kotu" if yalin else "istek_en_kotu") + ")", kota_durum=kota_durum, uretim_kosu=str(uretim_kosu or ""),
                liste_sha=liste_sha, mod="kurtarma" if kurtar else ("devam" if not ilk else "ilk"))
    (out / f"PLAN_{lid}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    log(f"PLAN {lid} ({plan['mod']}): cikar {len(cikar)} | yukle {len(yukle)} | baglar 5 | basta {len(K.d['ids0'])} | "
        f"en fazla {enfazla} gorsel | adim {basla}/{len(adimlar)} | tahmini istek {tahmin} | {kota_durum}")
    if enfazla > G.IMG_LIMIT:
        raise Dur(f"plan {G.IMG_LIMIT} gorsel sinirini asiyor (en fazla {enfazla}); yazma yok")
    if kuru:
        return dict(ilan=lid, sonuc="KURU", plan=plan, istek=api.calls, kota=api.remaining, kota_durum=kota_durum)
    if kota_ihtiyac and not yeter:
        raise Dur(f"kota yetmez: {kota_durum} (ilan yarida kalirdi); yazma yok")
    if ilk and cdn and not K.d.get("cdn"):
        K.d["cdn"] = cdn_yedek(g0, out / "YEDEK_CDN")
        log(f"CDN yedek: {K.d['cdn']} gorsel (canli galeri, bu kosunun Etsy okumasi)")
    yol = {r["hedef_gorsel"]: r for r in yukle}
    son = {}
    son_g = [None]   # yalin: sira_kontrol okumasi (oturduysa son okumada yeniden kullanilir)

    def son_kur():
        for r in hedef:
            s = int(r["hedef_sira"])
            son[s] = int(r["simdi_id"]) if r["islem"] in ("KORU", "ALT", "DOKUNMA") else K.d["yuklenen"].get(r["hedef_gorsel"])
    alt = {int(r["hedef_sira"]): r["hedef_alt"] for r in hedef}
    dokun = {int(r["hedef_sira"]) for r in hedef if r["islem"] == "DOKUNMA"}

    def bag_yaz(n, dogrula=True):
        son_kur()
        vi = [{"property_id": rv[ad][0], "value_id": rv[ad][1], "image_id": son[s]} for ad, s in sorted(hbag.items())]
        if any(v["image_id"] is None for v in vi):
            raise Dur("renk bagi icin hedef gorsel henuz yok (plan hatasi)")
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        hedef_bag = {ad: son[s] for ad, s in hbag.items()}
        if not dogrula:   # yalin: dogrulama son okumada (kararli var_img)
            log(f"  [{n + 1}/{len(adimlar)}] renk baglari POST (5) | kota {api.remaining}"); return

        def bag_ok(vm):
            vm = {v.get("value"): v.get("image_id") for v in vm}
            return len(vm) == len(hedef_bag) and all(vm.get(k) == v for k, v in hedef_bag.items())
        v1 = G.kararli(lambda: G.var_img(api, shop, lid), bag_ok)
        if not bag_ok(v1):
            raise Dur(f"renk baglari dogrulanamadi: {[(v.get('value'), v.get('image_id')) for v in v1]}")
        log(f"  [{n + 1}/{len(adimlar)}] renk baglari {len(hedef_bag)}/{len(hedef_bag)}")
    try:
        for n, a in enumerate(adimlar):
            if n < K.d.get("adim", 0):
                continue
            K.d["bekleyen"] = list(a); K.yaz(ids)   # yazimdan ONCE: kosu bu adimda durursa devam / kurtarma uzlastirir
            if a[0] == "sil":
                c = a[1]
                if yalin:   # 5xx tekrari ilk istek islendiyse 404 doner (29 Eki inceleme D10); kimlik kumesi sira_kontrol'de
                    api.delete(f"/shops/{shop}/listings/{lid}/images/{c}", ok404=True)
                else:
                    G.gorsel_sil(api, shop, lid, c)
                K.d["silinen"].append(c); ids.discard(c); K.yaz(ids)   # yazimdan HEMEN sonra
                if not yalin:
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                    if set(ids_of(g)) != ids:
                        K.yaz(ids_of(g)); raise Dur(f"silme sonrasi galeri beklenen degil ({c})")
                log(f"  [{n + 1}/{len(adimlar)}] sil {c} -> {len(ids)} gorsel | kota {api.remaining}")
            elif a[0] == "yukle":
                r = yol[a[1]]
                dyol = Path(hedef_dir) / r["hedef_gorsel"]
                K.d.setdefault("sha", {})[r["hedef_gorsel"]] = sha256(dyol); K.d["belirsiz"] = r["hedef_gorsel"]; K.yaz(ids)
                yid, deneme = yukle_guvenli(api, shop, lid, dyol, r["hedef_gorsel"], r["hedef_alt"], ids,
                                            gonderilmedi=lambda: K.d.pop("belirsiz", None), rank=int(r["hedef_sira"]) if yalin else None)
                K.d["yuklenen"][r["hedef_gorsel"]] = yid; ids.add(yid); K.d.pop("belirsiz", None)
                K.yaz(ids)   # kimlik + sha256 yazimdan HEMEN sonra kayitta (Serdar 24 Eki madde 2)
                if not yalin:
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                    if set(ids_of(g)) != ids:
                        K.yaz(); raise Dur(f"yukleme sonrasi galeri beklenen degil ({r['hedef_gorsel']} -> {yid})")
                log(f"  [{n + 1}/{len(adimlar)}] yukle {r['hedef_gorsel']} -> {yid} (deneme {deneme}) | {len(ids)} gorsel | kota {api.remaining}")
            elif a[0] == "kapak":
                son_kur()
                if son[1] is None:
                    raise Dur("kapak gorseli henuz yok (plan hatasi)")
                api.post_file(f"/shops/{shop}/listings/{lid}/images",
                              files={"listing_image_id": (None, str(son[1])), "rank": (None, "1"), "alt_text": (None, alt[1])})
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: bool(g) and g[0].get("listing_image_id") == son[1])
                log(f"  [{n + 1}/{len(adimlar)}] kapak {son[1]} rank 1: {'oturdu' if g and g[0].get('listing_image_id') == son[1] else 'oturmadi (sira adimi duzeltir)'}")
            elif a[0] == "bag":
                bag_yaz(n)   # yalin dahil: eski gorseller silinmeden ONCE dogrulanir (29 Eki inceleme Y2)
            elif a[0] in ("sira", "sira_kontrol"):
                son_kur()
                if set(son.values()) != ids or len(ids) != hedef_n:
                    raise Dur(f"sira oncesi galeri {len(ids)} gorsel, hedef kumesi ile ayni degil")
                oturdu = False
                if a[0] == "sira_kontrol":   # yalin: once tek okuma; oturmussa sira POST'u yok
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                    if set(ids_of(g)) != ids:
                        raise Dur(f"sira kontrolu: galeri kimlik kumesi beklenen degil (+{sorted(set(ids_of(g)) - ids)} "
                                  f"-{sorted(ids - set(ids_of(g)))}); son renk bagi yazilmadi")
                    oturdu = not galeri_sorun(g, son, alt, hedef_n)
                    son_g[0] = g if oturdu else None
                    log(f"  [{n + 1}/{len(adimlar)}] sira kontrolu: {'oturdu (sira POST yok)' if oturdu else galeri_sorun(g, son, alt, hedef_n)[:2]}")
                if not oturdu:
                    K.d["sira_post"] = True; K.yaz(ids)   # devam bu adimi yeniden kosarsa bag yine yazilir
                for gecis in ((1, 2) if not oturdu else ()):   # kapak_yukle_78 (28 Eyl): rank cagrisi bazen oturmuyor; bir kez daha, sonra DUR
                    for s in range(1, hedef_n + 1):
                        if s in dokun:   # galeri v11b: canli MB kapak dokunulmaz (sira / alt metin yazilmaz); oturmazsa DUR
                            continue
                        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                                      files={"listing_image_id": (None, str(son[s])), "rank": (None, str(s)), "alt_text": (None, alt[s])})
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: not galeri_sorun(g, son, alt, hedef_n))
                    if not galeri_sorun(g, son, alt, hedef_n):   # kimlik sirasi + rank 1..n + alt metin (24 Eki inceleme O6)
                        oturdu = True; break
                    log(f"  sira gecis {gecis} oturmadi: {galeri_sorun(g, son, alt, hedef_n)[:2]}")
                if not oturdu:   # Serdar 24 Eki madde 3: son renk bagi yazilmaz
                    raise Dur(f"sira 2 geciste oturmadi ({galeri_sorun(g, son, alt, hedef_n)[:2]}); son renk bagi yazilmadi")
                if a[0] == "sira" or son_g[0] is None:
                    son_g[0] = None
                    log(f"  [{n + 1}/{len(adimlar)}] sira + alt metin")
                if a[0] == "sira_kontrol" and K.d.get("sira_post"):   # rank yazimi renk bagini siler (19 Eyl): bag EN SONDA yeniden
                    bag_yaz(n)
            K.d["adim"] = n + 1; K.d["bekleyen"] = None; K.yaz(ids)
    except SystemExit as e:   # etsy_common "DUR: kota ...": o istek gonderilmeden durur; devam kosusu uzlastirir
        if not str(e.code).startswith("DUR: kota"):
            K.d["hata"] = str(e.code)[:300]
        K.yaz(); raise Dur(str(e.code)[:300])
    except Exception as e:   # noqa: BLE001 Dur, HTTP / ag hatasi: otomatik devam yok, kurtarma modu ile surdurulur
        K.d["hata"] = str(e)[:300]; K.yaz(); raise Dur(str(e)[:300])
    son_kur()
    bek = [son[s] for s in range(1, hedef_n + 1)]
    g = son_g[0] if yalin else None   # yalin: sira_kontrol okumasi oturduysa galeri yeniden okunmaz
    if not g or ids_of(g) != bek:
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: ids_of(g) == bek)
    sorun = galeri_sorun(g, son, alt, hedef_n)
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
             son_ids=bek, baglar_hedef=hb,
             silinen=K.d["silinen"], baglar=bag1, istek=api.calls, kota=api.remaining, uretim_kosu=str(uretim_kosu or ""),
             liste_sha=liste_sha, hata_gecmis=K.d.get("hata_gecmis", []),
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
    ap.add_argument("--kurtar", action="store_true", help="galeri: kota disi DUR'dan sonra kayitli plan + canli galeriyle surdur")
    ap.add_argument("--uretim-kosu", default="", help="galeri: gorsellerin uretim kosusu (galeri23-duzelt); devamda ayni olmali")
    ap.add_argument("--hedef-n", type=int, choices=(HEDEF_N, HEDEF_V10), default=HEDEF_N,
                    help=f"hedef gorsel sayisi: {HEDEF_N} (varsayilan, --confirm {ONAY}) | {HEDEF_V10} (v10, --confirm {ONAY_V10})")
    a = ap.parse_args()
    onay = ONAY_V10 if a.hedef_n == HEDEF_V10 else ONAY
    if not a.ilan.isdigit():
        raise SystemExit("DUR: --ilan yalniz rakam")
    if a.mod == "bag" and a.confirm != ONAY_BAG:
        raise SystemExit(f"DUR: bag yazimi icin --confirm {ONAY_BAG}")
    if a.mod == "galeri" and not a.kuru and a.confirm != onay:
        raise SystemExit(f"DUR: yazim icin --confirm {onay}")
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
            R = bir_ilan(api, shop, a.ilan, a.liste, a.hedef_dir, a.manifest, a.out, kuru=a.kuru, kota_ihtiyac=bool(a.kota_ihtiyac),
                         kurtar=a.kurtar, uretim_kosu=a.uretim_kosu, hedef_n=a.hedef_n)
        else:
            R = bag_kur(api, shop, a.ilan, a.liste, a.manifest, a.devam, a.out, bag_arg=bag_arg, yaz=a.mod == "bag", hedef_n=a.hedef_n)
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001 (requests zaman asimi / baglanti hatasi dahil)
        R = dict(ilan=a.ilan, sonuc="DUR", sorun=[str(e)[:500]], kota=api.remaining, istek=api.calls)
        dv = Path(a.out) / f"DEVAM_{a.ilan}.json"
        if dv.exists():   # kismi icerik kaydi (madde 5): yuklenen kimlik + sha256
            d = json.loads(dv.read_text())
            R.update(yuklenen=d.get("yuklenen"), sha256=d.get("sha"), adim=d.get("adim"), bekleyen=d.get("bekleyen"))
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"DUR_{a.ilan}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print("ESKI23_GALERI", json.dumps({k: R.get(k) for k in ("ilan", "mod", "sonuc", "sorun", "gorsel", "bag_sayisi", "istek",
                                                                                        "kota", "kota_durum") if k in R}, ensure_ascii=False),
          flush=True)
    return 0 if R["sonuc"] in ("PASS", "KURU") else 1


if __name__ == "__main__":
    sys.exit(main())
