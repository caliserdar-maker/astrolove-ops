#!/usr/bin/env python3
"""eski78-pilot-yolu kuru/yukle kodu (Serdar 26 Eki onayi). 1059b773'teki eski78_gorsel_yukle.py'nin (canlida kanitli, 22 ilan)
birebir kopyasi; iki fark:
  A. sira + alt metin adiminin HEMEN ARDINDAN renk baglari ikinci kez TEK variation-images cagrisiyla yazilir (son bag). Rank
     yazimi o gorselin renk bagini siler (19 Eyl olcumu, scripts/pod/pod_rank3_onar.py; 25 Eki kosu 40232676309: adim 11'de 5/5,
     sira sonrasi {}); 1059b773 sonda bag yazmadigi icin 22 ilanin hepsi ayri bag kosusu istedi. Erken bag kalir: eski bagli
     gorseller silinirken renkler yeni gorsellere bagli olur; bagsiz sure yalniz sira adimi (17 rank cagrisi) kadardir. Son geri
     okuma renk baglarini tekrarli okur (var_img gecici bos donebilir; 45233945 bag/oku ile ayni).
  B. girdi kapisi: --liste / --manifest dosya degilse ya da bossa, --hedef-dir klasor degilse ya da devam kaydi (--out icindeki
     DEVAM_<ilan>.json) dosya degilse token yenilemesinden ve Etsy'ye HICBIR istekten ONCE DUR (DUR_<ilan>.json).
23 ESKI galerili poster ilani: galeriyi hedef duzene (55 yeni galerili ilanla ayni 17 gorsel) getirir. ETSY'YE YAZAR
(Serdar onayi gerekir; once yalniz pilot 4570155846, gorsel onayindan sonra). Serdar 24 Eki B4: 17 Eki surumunun yerine.
Eski surum (17 Eki) sabit 18 gorsel + uretim galeri.json esitligi + rank overwrite ile calisiyordu; 21 Eki sonrasi galeriler 16-17
gorsel, cift kapakli ve rank'leri bozuk (rank 1 iki kez, rank 12 yok) oldugu icin kullanilamaz (overwrite KORU gorselini silerdi).
Girdi (ilan basina):
  --liste LISTE_<ilan>.csv (galeri_ornek.py: hedef_sira, hedef_gorsel, hedef_alt, islem KORU|ALT|DEGISTIR|CIKAR, simdi_id)
  --hedef-dir: DEGISTIR satirlarinin yuklenecek dosyalari (hedef_gorsel adiyla; kart_nokta_marka.py ciktisi varsa o)
  --manifest: hedef galeri manifesti (variation_images: renk adi -> hedef image_id; hedef_gorsel adindaki id ile eslenir)
Sira (her adim tek deneme, ilk sorunda DUR; her adimdan sonra galeri okunur ve DEVAM_<ilan>.json yazilir):
  0. kota kapisi (api.kota_kapisi, ilan basina; etsy_common esigi). state active degilse DUR (updateListing hic cagrilmaz).
  1. on kosul: canli gorsel kimlikleri = LISTE'deki simdi_id kumesi (KORU + ALT + CIKAR); degilse DUR. Yedek manifesti (CDN
     indirmesi workflow'da kilitten ONCE yapilir; KILIT SURESI kurali).
  2. adim plani YAZMADAN once kurulur (PLAN_<ilan>.json): her yuklemeden once bagsiz bir CIKAR silinir; renk kartlari once
     yuklenir; 5 hedef renk gorseli var olunca renk baglari TEK cagrida (variation-images tum seti degistirir) kurulur; sonra bagdan
     cikan CIKAR'lar silinir. Planin en fazla gorsel sayisi IMG_LIMIT (20) asarsa yazma yok. Yukleme overwrite YOK, rank yok,
     yalniz alt metinle; her adimdan sonra galeri okunur. Kota: kalan - tahmini istek < sert taban ise yazma yok (--kota-ihtiyac).
  3. (2 icinde) renk baglari geri okunur.
  4. sira + alt metin: her hedef sira icin listing_image_id + rank + alt_text yeniden POST (kapak_yukle_78 ile ayni cagri); oturmazsa
     bir gecis daha, sonra geri okuma.
  5. geri okuma: 17 gorsel, kimlik sirasi = hedef, rank'ler 1..17 tekil ve artan, alt metinler = hedef, renk baglari 5 ve hedefle
     ayni, korunanlar (state, baslik, etiket, aciklama, envanter, video) degismemis. SONRA_<ilan>.json (gorsel URL'leri):
     yuklenen gorsellerin CDN NCC kontrolu kilitsiz ayri is akisinda yapilir (galeri_ornek.py ile).
Devam: DEVAM_<ilan>.json (is akisi onceki kosudan indirir) varsa tamamlanan adimlar atlanir; canli galeri kayittaki son durumla
ayni degilse DUR. Yazimin olup olmadigi belirsiz hata (HTTP/ag, beklenmeyen galeri) kayda "hata" yazar: otomatik devam YOK (cift
yukleme riski; etsy_common post_file 5xx'te ayni istegi tekrarlar). Yalniz kota tabani (istek gonderilmeden) durmasi devam eder.
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
ISTEK_ADIM, ISTEK_SABIT = 4, 60   # istek tahmini: sil/yukle basina 1 yazma + galeri okumasi (kararli, cogu 1-2) + pay; sabit: on okuma,
                                  # baglar, 17 sira + 17 ikinci gecis payi degil, son okuma (24 Eki inceleme: pilot en az 95 istek)
YASAK_ALT = re.compile(r"[\u2014\u2013]|AstroLove(?!Art)|hahnem|photo\s*rag|gicl[eé]e|prodigi|cotton|museum|\b308\b", re.I)


def adim_plani(n0, cikar, bagli0, yukle, renk_siralari):
    """Adim listesi + en fazla gorsel sayisi. Renk kartlari once yuklenir; 5 hedef renk gorseli var olunca TEK cagriyla baglanir;
    sonra bagdan cikan CIKAR'lar silinir. Bos CIKAR her yuklemeden once silinir (sayi n0 civarinda kalir)."""
    from collections import deque
    bos = deque(c for c in cikar if c not in bagli0); bagli = [c for c in cikar if c in bagli0]
    renk_yuk = [r for r in yukle if int(r["hedef_sira"]) in renk_siralari]
    diger = [r for r in yukle if int(r["hedef_sira"]) not in renk_siralari]
    adim, n, mx, kalan_renk = [], n0, n0, len(renk_yuk)
    bag = False
    for r in renk_yuk + diger:
        if bos:
            adim.append(("sil", bos.popleft())); n -= 1
        adim.append(("yukle", r["hedef_gorsel"])); n += 1; mx = max(mx, n)
        if int(r["hedef_sira"]) in renk_siralari:
            kalan_renk -= 1
        if not bag and kalan_renk == 0:
            adim.append(("bag",)); bag = True; bos.extend(bagli)
    if not bag:
        adim.append(("bag",)); bos.extend(bagli)
    while bos:
        adim.append(("sil", bos.popleft())); n -= 1
    adim.append(("sira",))
    adim.append(("bag",))   # rank yazimi renk bagini siler (19 Eyl olcumu; 40232676309): sira ardindan son bag
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
    if K.d["son_ids"] is None:
        if canli != simdi:
            raise Dur(f"canli galeri LISTE ile ayni degil: +{sorted(canli - simdi)} -{sorted(simdi - canli)}")
        (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(galeri=g0, variation_images=G.var_img(api, shop, lid), korunan=kor0),
                                                          indent=1, ensure_ascii=False))
        K.d["korunan0"] = kor0
    elif sorted(canli) != K.d["son_ids"]:
        raise Dur("devam: canli galeri son kayittan farkli; elle bakilmali")
    else:
        kor0 = K.d["korunan0"]
    rv = G.renk_degerleri(api, lid)
    if len(rv) != 5:
        raise Dur(f"envanterde 5 renk yok ({sorted(rv)})")
    h_id = {int(r["hedef_sira"]): hedef_id(r["hedef_gorsel"]) for r in hedef}
    sira_h = {v: k for k, v in h_id.items()}
    hbag = {}
    for v in man.get("variation_images") or []:
        ad = v.get("value"); hid = v.get("image_id")
        if ad not in rv or hid not in sira_h:
            raise Dur(f"hedef renk bagi eslenemedi ({ad} -> {hid})")
        hbag[ad] = sira_h[hid]
    if len(hbag) != 5:
        raise Dur(f"hedef manifestte {len(hbag)} renk bagi (5 beklenir)")
    yukle = [r for r in hedef if r["islem"] == "DEGISTIR"]
    for r in yukle:
        if not (Path(hedef_dir) / r["hedef_gorsel"]).exists():
            raise Dur(f"yuklenecek dosya yok: {r['hedef_gorsel']}")
    bagli0 = {v.get("image_id") for v in G.var_img(api, shop, lid)}
    adimlar, enfazla = adim_plani(len(g0), cikar, bagli0, yukle, set(hbag.values()))
    tahmin = ISTEK_ADIM * sum(a[0] in ("sil", "yukle") for a in adimlar) + ISTEK_SABIT
    plan = dict(ilan=lid, cikar=cikar, cikar_bagli=sorted(set(cikar) & bagli0), yukle=[r["hedef_gorsel"] for r in yukle],
                baglar={k: h_id[s] for k, s in hbag.items()}, baslangic=len(g0), en_fazla_gorsel=enfazla, adimlar=adimlar,
                tahmini_istek=tahmin)
    (out / f"PLAN_{lid}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    log(f"PLAN {lid}: cikar {len(cikar)} (bagli {len(plan['cikar_bagli'])}) | yukle {len(yukle)} | baglar 5 | basta {len(g0)} | "
        f"en fazla {enfazla} gorsel | tahmini istek {tahmin}")
    if enfazla > G.IMG_LIMIT:
        raise Dur(f"plan {G.IMG_LIMIT} gorsel sinirini asiyor (en fazla {enfazla}); yazma yok")
    if kuru:
        return dict(ilan=lid, sonuc="KURU", plan=plan)
    taban = getattr(api, "sert_taban", None)
    if kota_ihtiyac and taban is not None and api.remaining is not None and int(api.remaining) - tahmin < int(taban):
        raise Dur(f"kota yetmez: kalan {api.remaining} - tahmini {tahmin} < sert taban {taban} (ilan yarida kalirdi); yazma yok")
    ids = set(canli)
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
            if a[0] == "sil":
                c = a[1]
                G.gorsel_sil(api, shop, lid, c); K.d["silinen"].append(c); ids.discard(c)
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                if set(ids_of(g)) != ids:
                    K.yaz(ids_of(g)); raise Dur(f"silme sonrasi galeri beklenen degil ({c})")
                log(f"  [{n + 1}/{len(adimlar)}] sil {c} -> {len(ids)} gorsel | kota {api.remaining}")
            elif a[0] == "yukle":
                r = yol[a[1]]
                with open(Path(hedef_dir) / r["hedef_gorsel"], "rb") as fh:
                    y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (r["hedef_gorsel"], fh, "image/jpeg")},
                                      data={"alt_text": r["hedef_alt"]})
                yid = (y or {}).get("listing_image_id")
                if not yid or yid in ids:
                    raise Dur(f"yukleme kimligi {yid} ({r['hedef_gorsel']})")
                K.d["yuklenen"][r["hedef_gorsel"]] = yid; ids.add(yid)
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
                if set(ids_of(g)) != ids:
                    K.yaz(ids_of(g)); raise Dur(f"yukleme sonrasi galeri beklenen degil ({r['hedef_gorsel']} -> {yid})")
                log(f"  [{n + 1}/{len(adimlar)}] yukle {r['hedef_gorsel']} -> {yid} | {len(ids)} gorsel | kota {api.remaining}")
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
                for gecis in (1, 2):   # kapak_yukle_78 (28 Eyl): rank cagrisi bazen oturmuyor; bir kez daha, sonra DUR
                    for s in range(1, HEDEF_N + 1):
                        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                                      files={"listing_image_id": (None, str(son[s])), "rank": (None, str(s)), "alt_text": (None, alt[s])})
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: ids_of(g) == bek and [x.get("rank") for x in g] ==
                                  list(range(1, HEDEF_N + 1)))
                    if ids_of(g) == bek and [x.get("rank") for x in g] == list(range(1, HEDEF_N + 1)):
                        break
                    log(f"  sira gecis {gecis} oturmadi: {[x.get('rank') for x in g]}")
                log(f"  [{n + 1}/{len(adimlar)}] sira + alt metin")
            K.d["adim"] = n + 1; K.yaz(ids)
    except SystemExit as e:   # etsy_common "DUR: kota ...": istek GONDERILMEDEN durur (adim yapilmadi, devam guvenli)
        if not str(e.code).startswith("DUR: kota"):
            K.d["hata"] = str(e.code)[:300]
        K.p.write_text(json.dumps(K.d, indent=1)); raise Dur(str(e.code)[:300])
    except Exception as e:   # noqa: BLE001 Dur, HTTP / ag hatasi: yazimin olup olmadigi belirsiz -> otomatik devam yok
        K.d["hata"] = str(e)[:300]; K.p.write_text(json.dumps(K.d, indent=1)); raise Dur(str(e)[:300])
    son_kur()
    bek = [son[s] for s in range(1, HEDEF_N + 1)]
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: ids_of(g) == bek)
    sorun = []
    if ids_of(g) != bek:
        sorun.append(f"sira {ids_of(g)}")
    rk = [x.get("rank") for x in g]
    if rk != list(range(1, HEDEF_N + 1)):
        sorun.append(f"rank 1..{HEDEF_N} tekil/artan degil: {rk}")
    alt_son = [x.get("alt_text") or "" for x in g]
    if alt_son != [alt[s] for s in range(1, HEDEF_N + 1)]:
        sorun.append("alt metin: " + "; ".join(f"r{i + 1}" for i, (a_, b_) in enumerate(zip(alt_son, [alt[s] for s in
                                                                                                     range(1, HEDEF_N + 1)])) if a_ != b_))
    bag_hedef = {ad: son[s] for ad, s in hbag.items()}
    bag1 = {v.get("value"): v.get("image_id") for v in G.kararli(lambda: G.var_img(api, shop, lid),
                                                                lambda vm: {v.get("value"): v.get("image_id") for v in vm} == bag_hedef)}
    if bag1 != bag_hedef:
        sorun.append(f"renk baglari {bag1}")
    kor1 = G.korunanlar(api, shop, lid)
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if kor1.get(k) != kor0.get(k):
            sorun.append(f"korunan {k}")
    R = dict(ilan=lid, sonuc="FAIL" if sorun else "PASS", sorun=sorun, gorsel=len(g), yuklenen=K.d["yuklenen"],
             silinen=K.d["silinen"], baglar=bag1, istek=api.calls, kota=api.remaining,
             galeri=[dict(rank=x.get("rank"), listing_image_id=x.get("listing_image_id"), alt_text=x.get("alt_text"),
                          url_fullxfull=x.get("url_fullxfull")) for x in g])
    (out / f"SONRA_{lid}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    return R


def girdi_kapisi(lid, liste, hedef_dir, manifest, out):
    """Etsy'ye istek gitmeden girdi denetimi; sorun listesi (bos = gecti)."""
    sorun = []
    for ad, yol in (("--liste", liste), ("--manifest", manifest)):
        p = Path(yol or "")
        if not str(yol or "").strip() or not p.is_file():
            sorun.append(f"DUR: girdi {ad} dosya degil ({'bos' if not str(yol or '').strip() else ('klasor' if p.is_dir() else 'yok')}): "
                         f"{yol!r}; Etsy'ye istek yok")
        elif p.stat().st_size == 0:
            sorun.append(f"DUR: girdi {ad} bos dosya: {yol!r}; Etsy'ye istek yok")
    if not str(hedef_dir or "").strip() or not Path(hedef_dir).is_dir():
        sorun.append(f"DUR: girdi --hedef-dir klasor degil: {hedef_dir!r}; Etsy'ye istek yok")
    dv = Path(out or ".") / f"DEVAM_{lid}.json"
    if dv.exists() and (not dv.is_file() or dv.stat().st_size == 0):
        sorun.append(f"DUR: devam kaydi {dv} dosya degil ya da bos; Etsy'ye istek yok")
    return sorun


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ilan", required=True); ap.add_argument("--liste", required=True); ap.add_argument("--hedef-dir", required=True)
    ap.add_argument("--manifest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--kota-ihtiyac", type=int, default=1, help="1: kalan - tahmini istek < sert taban ise yazmadan DUR (varsayilan)")
    a = ap.parse_args()
    if not a.ilan.isdigit():
        raise SystemExit("DUR: --ilan yalniz rakam")
    if not a.kuru and a.confirm != ONAY:
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY}")
    gk = girdi_kapisi(a.ilan, a.liste, a.hedef_dir, a.manifest, a.out)
    if gk:   # 26 Eki: bos / klasor girdi IsADirectoryError ile cokmeden, token yenilemesi ve Etsy istegi OLMADAN durur
        R = dict(ilan=a.ilan, sonuc="DUR", sorun=gk, istek=0, kota=None)
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"DUR_{a.ilan}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
        print("ESKI23_GALERI", json.dumps({k_: R.get(k_) for k_ in ("ilan", "sonuc", "sorun", "gorsel", "istek", "kota")},
                                          ensure_ascii=False), flush=True)
        return 1
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    try:
        R = bir_ilan(api, shop, a.ilan, a.liste, a.hedef_dir, a.manifest, a.out, kuru=a.kuru, kota_ihtiyac=bool(a.kota_ihtiyac))
    except (Dur, SystemExit, Exception) as e:   # noqa: BLE001 (requests zaman asimi / baglanti hatasi dahil)
        R = dict(ilan=a.ilan, sonuc="DUR", sorun=[str(e)[:500]], kota=api.remaining)
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"DUR_{a.ilan}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print("ESKI23_GALERI", json.dumps({k: R.get(k) for k in ("ilan", "sonuc", "sorun", "gorsel", "istek", "kota")}, ensure_ascii=False),
          flush=True)
    return 0 if R["sonuc"] in ("PASS", "KURU") else 1


if __name__ == "__main__":
    sys.exit(main())
