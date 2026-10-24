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
  1. on kosul: canli gorsel kimlikleri = LISTE'deki simdi_id kumesi (KORU + ALT + CIKAR); degilse DUR. Yedek manifesti (CDN
     indirmesi workflow'da kilitten ONCE yapilir; KILIT SURESI kurali).
  2. degisim, tek tek: renk bagli olmayan CIKAR silinir -> galeri okunur; DEGISTIR yuklenir (overwrite YOK, rank verilmez,
     alt metinle) -> galeri okunur. Gorsel sayisi en fazla baslangic + 1 (IMG_LIMIT 20 asilmaz).
  3. renk baglari TEK cagrida (variation-images tum seti degistirir): 5 renk -> nihai kimlik (KORU/ALT ise canli id, DEGISTIR ise
     yeni id). Geri okuma. Sonra bagdan cikan CIKAR gorselleri silinir.
  4. sira + alt metin: her hedef sira icin listing_image_id + rank + alt_text yeniden POST (kapak_yukle_78 ile ayni cagri).
  5. geri okuma: 17 gorsel, kimlik sirasi = hedef, rank'ler 1..17 tekil ve artan, alt metinler = hedef, renk baglari 5 ve hedefle
     ayni, korunanlar (state, baslik, etiket, aciklama, envanter, video) degismemis. SONRA_<ilan>.json (gorsel URL'leri):
     yuklenen gorsellerin CDN NCC kontrolu kilitsiz ayri is akisinda yapilir (galeri_ornek.py ile).
Devam: DEVAM_<ilan>.json varsa tamamlanan adimlar atlanir; canli galeri kayittaki son durumla ayni degilse DUR.
Kullanim: eski78_gorsel_yukle.py --ilan ID --liste LISTE.csv --hedef-dir DIR --manifest manifest.json --out OUT
          --confirm ESKI23_GALERI [--kuru]"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ONAY = "ESKI23_GALERI"
HEDEF_N = 17


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


def bir_ilan(api, shop, lid, liste, hedef_dir, manifest, out, kuru=False):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    hedef, cikar = liste_oku(liste)
    man = json.loads(Path(manifest).read_text())
    if str(man.get("listing_id")) != str(lid):
        raise Dur(f"manifest baska ilana ait ({man.get('listing_id')})")
    if hasattr(api, "kota_kapisi"):
        api.kota_kapisi(f"ilan {lid}")
    kor0 = G.korunanlar(api, shop, lid)
    if kor0["state"] != "active":
        raise Dur(f"state {kor0['state']} (active degil)")
    K = Kayit(out, lid)
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
    plan = dict(ilan=lid, cikar=cikar, cikar_bagli=sorted(set(cikar) & bagli0), yukle=[r["hedef_gorsel"] for r in yukle],
                baglar={k: h_id[s] for k, s in hbag.items()}, baslangic=len(g0))
    (out / f"PLAN_{lid}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    log(f"PLAN {lid}: cikar {len(cikar)} (bagli {len(plan['cikar_bagli'])}) | yukle {len(yukle)} | baglar 5 | basta {len(g0)} gorsel")
    if kuru:
        return dict(ilan=lid, sonuc="KURU", plan=plan)
    ids = set(canli)
    simdi_bos = [c for c in cikar if c not in bagli0 and c not in K.d["silinen"]]
    sirali = list(yukle)
    while simdi_bos or any(r["hedef_gorsel"] not in K.d["yuklenen"] for r in sirali):
        if simdi_bos:
            c = simdi_bos.pop(0)
            G.gorsel_sil(api, shop, lid, c); K.d["silinen"].append(c); ids.discard(c)
            g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
            if set(ids_of(g)) != ids:
                K.yaz(ids_of(g)); raise Dur(f"silme sonrasi galeri beklenen degil ({c})")
            K.yaz(ids); log(f"  sil {c} -> {len(ids)} gorsel | kota {api.remaining}")
        r = next((r for r in sirali if r["hedef_gorsel"] not in K.d["yuklenen"]), None)
        if r is None:
            continue
        if len(ids) + 1 > G.IMG_LIMIT:
            raise Dur(f"yukleme {G.IMG_LIMIT} siniri asar ({len(ids)})")
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
        K.yaz(ids); log(f"  yukle {r['hedef_gorsel']} -> {yid} | {len(ids)} gorsel | kota {api.remaining}")
    son = {}
    for r in hedef:
        s = int(r["hedef_sira"])
        son[s] = int(r["simdi_id"]) if r["islem"] in ("KORU", "ALT") else K.d["yuklenen"][r["hedef_gorsel"]]
    if not K.d["baglar"]:
        vi = [{"property_id": rv[ad][0], "value_id": rv[ad][1], "image_id": son[s]} for ad, s in sorted(hbag.items())]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        hedef_bag = {ad: son[s] for ad, s in hbag.items()}

        def bag_ok(vm):
            vm = {v.get("value"): v.get("image_id") for v in vm}
            return len(vm) == 5 and all(vm.get(k) == v for k, v in hedef_bag.items())
        v1 = G.kararli(lambda: G.var_img(api, shop, lid), bag_ok)
        if not bag_ok(v1):
            raise Dur(f"renk baglari dogrulanamadi: {[(v.get('value'), v.get('image_id')) for v in v1]}")
        K.d["baglar"] = True; K.yaz(ids); log("  renk baglari 5/5")
    for c in [c for c in cikar if c not in K.d["silinen"]]:   # bagdan cikanlar
        G.gorsel_sil(api, shop, lid, c); K.d["silinen"].append(c); ids.discard(c)
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: set(ids_of(g)) == ids)
        if set(ids_of(g)) != ids:
            K.yaz(ids_of(g)); raise Dur(f"silme sonrasi galeri beklenen degil ({c})")
        K.yaz(ids)
    if set(son.values()) != ids or len(ids) != HEDEF_N:
        raise Dur(f"sira oncesi galeri {len(ids)} gorsel, hedef kumesi ile ayni degil")
    alt = {int(r["hedef_sira"]): r["hedef_alt"] for r in hedef}
    if not K.d["sira"]:
        for s in range(1, HEDEF_N + 1):
            api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"listing_image_id": (None, str(son[s])), "rank": (None, str(s)), "alt_text": (None, alt[s])})
        K.d["sira"] = True; K.yaz(ids)
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
    bag1 = {v.get("value"): v.get("image_id") for v in G.var_img(api, shop, lid)}
    if bag1 != {ad: son[s] for ad, s in hbag.items()}:
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ilan", required=True); ap.add_argument("--liste", required=True); ap.add_argument("--hedef-dir", required=True)
    ap.add_argument("--manifest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--kuru", action="store_true")
    a = ap.parse_args()
    if not a.ilan.isdigit():
        raise SystemExit("DUR: --ilan yalniz rakam")
    if not a.kuru and a.confirm != ONAY:
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY}")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    try:
        R = bir_ilan(api, shop, a.ilan, a.liste, a.hedef_dir, a.manifest, a.out, kuru=a.kuru)
    except (Dur, SystemExit) as e:
        R = dict(ilan=a.ilan, sonuc="DUR", sorun=[str(e)[:500]], kota=api.remaining)
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"DUR_{a.ilan}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print("ESKI23_GALERI", json.dumps({k: R.get(k) for k in ("ilan", "sonuc", "sorun", "gorsel", "istek", "kota")}, ensure_ascii=False),
          flush=True)
    return 0 if R["sonuc"] in ("PASS", "KURU") else 1


if __name__ == "__main__":
    sys.exit(main())
