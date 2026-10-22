#!/usr/bin/env python3
"""TEK GALERI GECISI — TAM YENI SET (Serdar, 25 Eyl 2026). 77 ilan (Cancer-Libra 4570143815 HARIC).

Karar: galeri Cancer-Libra ile birebir ayni yapida TAMAMEN YENI setle degisir. Eski gorsellerin HEPSI silinir
(kapak, sahneler, Symbol Story, Crafted, renk gorselleri, GENEL_1..4 dahil). GENEL_1 kisisellestirme karti
galeriye GIRMEZ (setinde olan cift reddedilir). Renk baglari (variation images) yeni renk gorsellerine TASINIR.
Video mevcut videonun yerine gecer. Etsy'ye yazma yalniz --confirm GALERI_TEK ile.

Girdiler:
  REFERANS_SIRA.json  Cancer-Libra'nin canli yapisi (mod 'referans', 3 GET): [{rank, renk|null}], video var mi.
  <yerel>/<CIFT>/SET.json  medyanin cift basina seti: {"gorseller": [{"dosya": "01_KAPAK.jpg", "renk": null},
                       ..., {"dosya": "09_MB.jpg", "renk": "Midnight Blue"}], "video": "VIDEO.mp4"}
                       Sira = galeri sirasi; renk = o gorselin baglanacagi renk secenegi (envanterdeki ad).

Yazma sirasi (ilan hep en az 5 renk gorselli, 20 siniri hicbir anda asilmaz, renk bagi hic bosta kalmaz):
  1 oku: ilan (Images,Videos) + variation-images + envanter            3 cagri
  2 renge BAGLI OLMAYAN eski gorselleri sil                             eski - renk
  3 yeni RENK gorsellerini yukle                                        renk
  4 variation-images: renk -> yeni gorsel (tek POST, tumu)              1
  5 eski renk gorsellerini sil                                          renk
  6 kalan yeni gorselleri yukle                                         yeni - renk
  7 sira: updateListing image_ids (SET sirasi)                          1
  8 video: eskiyi sil + yeniyi yukle                                    0-1 + 1
  9 geri okuma: ilan + variation-images                                 2
  Toplam = eski + yeni + 8 + (eski video varsa 1). 13 eski + 13 yeni + video: 35 cagri.

Modlar:
  referans : Cancer-Libra canli okuma (3 GET, yazma yok) -> REFERANS_SIRA.json
  plan     : SALT OKUMA, Etsy kotasi HARCAMAZ. REFERANS + SET.json'lar + GALERI_PLAN/SONUC (eski sayi) ->
             ilan basina kapilar ve cagri sayisi, TEK_PLAN.json + rapor.
  yaz      : --listing (virgullu) ya da bos (77 ilan), --confirm GALERI_TEK, --kota-alt.
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))

REF = "4570143815"
ONAY = "GALERI_TEK"
AZAMI_GORSEL = 20
GENEL_VAR = ["4570110641", "4570113157", "4570114301", "4570224058", "4570160260"]
YASAK_AD = ("GENEL_1", "KISISELLESTIRME", "PERSONALIZ")      # GENEL_1 galeriden cikti (Serdar 25 Eyl)
csv.field_size_limit(10 ** 8)


def log(m):
    print(m, flush=True)


def ad_norm(s):
    return "".join(c for c in (s or "").upper() if c.isalnum())


# ------------------------------------------------------------------ saf fonksiyonlar (yerel test)
def set_dogrula(setj, referans, klasor=None):
    """SET.json -> hatalar. Referans: ayni gorsel sayisi, renkli ranklar ayni yerde ve ayni renkte, <= 20,
    GENEL_1 yok, dosyalar var, video var."""
    h = []
    g = setj.get("gorseller") or []
    if not g:
        return ["SET bos"]
    if len(g) > AZAMI_GORSEL:
        h.append(f"{len(g)} gorsel > {AZAMI_GORSEL}")
    for x in g:
        if any(y in ad_norm(x.get("dosya")) for y in map(ad_norm, YASAK_AD)):
            h.append(f"GENEL_1/kisisellestirme karti sette: {x.get('dosya')}")
    renkler = [ad_norm(x.get("renk")) for x in g if x.get("renk")]
    if len(renkler) != len(set(renkler)):
        h.append("ayni renk iki gorselde")
    if referans:
        rs = referans.get("sira") or []
        if len(rs) != len(g):
            h.append(f"gorsel sayisi {len(g)} != referans {len(rs)}")
        else:
            fark = [i + 1 for i, (a, b) in enumerate(zip(rs, g)) if ad_norm(a.get("renk")) != ad_norm(b.get("renk"))]
            if fark:
                h.append(f"renk yerlesimi referanstan farkli (rank {fark})")
        if referans.get("video") and not setj.get("video"):
            h.append("video yok (referansta var)")
    if klasor is not None:
        eksik = [x["dosya"] for x in g if not (klasor / x["dosya"]).exists()]
        if setj.get("video") and not (klasor / setj["video"]).exists():
            eksik.append(setj["video"])
        if eksik:
            h.append(f"dosya yok: {eksik[:4]}")
    return h


def renk_haritasi(inventory):
    """envanter -> (property_id, {renk_norm: value_id})."""
    pid, vid = None, {}
    for pr in (inventory or {}).get("products") or []:
        for pv in pr.get("property_values") or []:
            if (pv.get("property_name") or "").lower() in ("primary color", "color"):
                pid = pid or pv.get("property_id")
                for v_id, ad in zip(pv.get("value_ids") or [], pv.get("values") or []):
                    vid.setdefault(ad_norm(ad), v_id)
    return pid, vid


def islem_plani(eski_ids, bagli_ids, setj, video_var, renk_vid):
    """-> dict: adimlar (silinecek bagsiz/bagli, yuklenecek renk/diger), cagri sayisi, kapilar."""
    bagli = [i for i in eski_ids if i in set(bagli_ids)]
    bagsiz = [i for i in eski_ids if i not in set(bagli_ids)]
    g = setj.get("gorseller") or []
    renkli = [x for x in g if x.get("renk")]
    diger = [x for x in g if not x.get("renk")]
    h = []
    if len(bagli) != len(bagli_ids):
        h.append("renk bagli gorsel ilanda yok")
    eksik_renk = [x["renk"] for x in renkli if ad_norm(x["renk"]) not in renk_vid]
    if eksik_renk:
        h.append(f"envanterde olmayan renk: {eksik_renk}")
    if len(renkli) < len(bagli_ids):
        h.append(f"yeni sette {len(renkli)} renk gorseli < mevcut bag {len(bagli_ids)} (renk bagsiz kalir)")
    # 20 siniri: en kalabalik an = bagli eski + yeni renk
    if len(bagli) + len(renkli) > AZAMI_GORSEL or len(g) > AZAMI_GORSEL:
        h.append("20 gorsel siniri asilir")
    cagri = {"oku": 3, "bagsiz eski sil": len(bagsiz), "renk yukle": len(renkli), "renk bagi POST": 1,
             "bagli eski sil": len(bagli), "diger yukle": len(diger), "sira PATCH": 1,
             "video sil": 1 if video_var else 0, "video yukle": 1 if setj.get("video") else 0, "geri okuma": 2}
    return {"bagsiz": bagsiz, "bagli": bagli, "renkli": renkli, "diger": diger, "cagri": cagri,
            "cagri_toplam": sum(cagri.values()), "kapi": h}


def cagri_tahmini(eski_sayi, yeni_sayi, video_var=True, video_yeni=True):
    return 3 + eski_sayi + yeni_sayi + 1 + 1 + (1 if video_var else 0) + (1 if video_yeni else 0) + 2


# ------------------------------------------------------------------ Etsy okuma
def anlik(api, shop, lid):
    L = api.get(f"/listings/{lid}", params={"includes": "Images,Videos"}) or {}
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    inv = api.get(f"/listings/{lid}/inventory") or {}
    imgs = sorted(L.get("images") or [], key=lambda x: x.get("rank") or 0)
    return L.get("state"), [x.get("listing_image_id") for x in imgs], L.get("videos") or [], vi, inv


def api_kur():
    from etsy_common import Etsy, TokenStore
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    return Etsy(store), os.environ["ETSY_SHOP_ID"]


def referans(a, api=None, shop=None):
    """Cancer-Libra canli yapisi (salt okuma, 3 GET)."""
    if api is None:
        api, shop = api_kur()
    st, ids, vids, vi, inv = anlik(api, shop, REF)
    renk_ad = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            if (pv.get("property_name") or "").lower() in ("primary color", "color"):
                renk_ad.update(dict(zip(pv.get("value_ids") or [], pv.get("values") or [])))
    bag = {v.get("image_id"): renk_ad.get(v.get("value_id"), str(v.get("value_id"))) for v in vi}
    R = {"ilan": REF, "state": st, "sira": [{"rank": i, "image_id": x, "renk": bag.get(x)} for i, x in enumerate(ids, 1)],
         "video": bool(vids), "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "REFERANS_SIRA.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"REFERANS {REF}: {len(ids)} gorsel, renkli rank {[s['rank'] for s in R['sira'] if s['renk']]}, video {R['video']} "
        f"| kota {getattr(api, 'remaining', '?')}")
    return 0


# ------------------------------------------------------------------ plan (kotasiz)
def plan(a):
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(a.csv, encoding="utf-8") as fh:
        cift = {r["ilan_id"]: r["cift"] for r in csv.DictReader(fh)}
    R = json.loads(pathlib.Path(a.referans).read_text(encoding="utf-8")) if a.referans and pathlib.Path(a.referans).exists() else None
    P = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))["plan"] if pathlib.Path(a.plan).exists() else {}
    yeni_sayi = len(R["sira"]) if R else a.varsayilan_sayi
    kayit, toplam, hatali = {}, 0, 0
    for lid in [k for k in cift if k != REF]:
        eski = 14 if lid in GENEL_VAR else len((P.get(lid) or {}).get("once_ids") or []) or 13
        klasor = pathlib.Path(a.yerel) / cift[lid]
        sj = klasor / "SET.json"
        h = set_dogrula(json.loads(sj.read_text(encoding="utf-8")), R) if sj.exists() else ["SET.json yok"]   # dosya varligi: yaz
        n = cagri_tahmini(eski, yeni_sayi)
        kayit[lid] = {"cift": cift[lid], "eski_sayi": eski, "cagri": n, "hata": h}
        toplam += n
        hatali += bool(h)
    (out / "TEK_PLAN.json").write_text(json.dumps({"referans": R, "ilan": kayit}, indent=1, ensure_ascii=False), encoding="utf-8")
    metin = "\n".join([
        f"# Tek galeri gecisi (tam yeni set) — PLAN, Etsy kotasi harcanmadi — {time.strftime('%Y-%m-%d %H:%M')} UTC", "",
        f"- referans: {'Cancer-Libra ' + str(len(R['sira'])) + ' gorsel, video ' + str(R['video']) if R else f'YOK (yeni set {yeni_sayi} varsayildi)'}",
        f"- ilan: {len(kayit)} | hazir olmayan (SET/kapi): {hatali}",
        f"- cagri/ilan: eski + yeni + 9 (13 eski: {cagri_tahmini(13, yeni_sayi)}, 14 eski: {cagri_tahmini(14, yeni_sayi)})",
        f"- toplam tahmini cagri: {toplam}", ""] + [f"- {k}: {v['hata']}" for k, v in list(kayit.items())[:10] if v["hata"]])
    (out / "RAPOR_galeri_tek_plan.md").write_text(metin + "\n", encoding="utf-8")
    log(metin)
    return 0


# ------------------------------------------------------------------ yaz
def yaz(a, api=None, shop=None):
    if a.confirm != ONAY:
        sys.exit(f"HATA: yaz --confirm {ONAY} ister")
    out = pathlib.Path(a.out)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    with open(a.csv, encoding="utf-8") as fh:
        cift = {r["ilan_id"]: r["cift"] for r in csv.DictReader(fh)}
    R = json.loads(pathlib.Path(a.referans).read_text(encoding="utf-8"))
    if api is None:
        api, shop = api_kur()
    hedef = [x.strip() for x in a.listing.split(",") if x.strip()] if a.listing else [k for k in cift if k != REF]
    sonuc, t0 = [], time.time()
    for i, lid in enumerate(hedef, 1):
        try:
            kota = int(api.remaining or 99999)
        except ValueError:
            kota = 99999
        if kota < a.kota_alt:
            sonuc.append((lid, "DURDU", f"kota {api.remaining} < {a.kota_alt}"))
            break
        if lid == REF or lid not in cift:
            sonuc.append((lid, "ATLANDI", "kapsam disi"))
            continue
        klasor = pathlib.Path(a.yerel) / cift[lid]
        sj = klasor / "SET.json"
        setj = json.loads(sj.read_text(encoding="utf-8")) if sj.exists() else {}
        h = set_dogrula(setj, R, klasor) if setj else ["SET.json yok"]
        if h:
            sonuc.append((lid, "ATLANDI", "; ".join(h)))
            continue
        c0 = getattr(api, "calls", 0)
        st0, ids0, vid0, vi0, inv0 = anlik(api, shop, lid)
        (out / "YEDEK" / f"{lid}_TEK_ONCE.json").write_text(json.dumps(
            {"state": st0, "images": ids0, "videos": vid0, "variation_images": vi0}, indent=1), encoding="utf-8")
        pid, renk_vid = renk_haritasi(inv0)
        bagli0 = [v.get("image_id") for v in vi0]
        ip = islem_plani(ids0, bagli0, setj, bool(vid0), renk_vid)
        h = list(ip["kapi"])
        if st0 != "active":
            h.append(f"state {st0} (updateListing taslagi yayina alir)")
        if pid is None:
            h.append("envanterde renk ozelligi yok")
        if h:
            sonuc.append((lid, "ATLANDI", "; ".join(h)))
            continue
        adim = "baslangic"
        try:
            def yukle(x):
                p = klasor / x["dosya"]
                with open(p, "rb") as fh:
                    return api.post_file(f"/shops/{shop}/listings/{lid}/images", {"image": (p.name, fh, "image/jpeg")}).get("listing_image_id")
            adim = "bagsiz eski sil"
            for iid in ip["bagsiz"]:
                api.delete(f"/shops/{shop}/listings/{lid}/images/{iid}")
            adim = "renk yukle"
            yeni = {id(x): yukle(x) for x in ip["renkli"]}
            adim = "renk bagi tasi"
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                          {"variation_images": [{"property_id": pid, "value_id": renk_vid[ad_norm(x["renk"])], "image_id": int(yeni[id(x)])}
                                                for x in ip["renkli"]]})
            adim = "bagli eski sil"
            for iid in ip["bagli"]:
                api.delete(f"/shops/{shop}/listings/{lid}/images/{iid}")
            adim = "diger yukle"
            yeni.update({id(x): yukle(x) for x in ip["diger"]})
            adim = "sira"
            bek = [int(yeni[id(x)]) for x in setj["gorseller"]]
            api.patch(f"/shops/{shop}/listings/{lid}", {"image_ids": ",".join(str(x) for x in bek)})
            adim = "video"
            for v in vid0:
                api.delete(f"/shops/{shop}/listings/{lid}/videos/{v.get('video_id')}")
            if setj.get("video"):
                vp = klasor / setj["video"]
                with open(vp, "rb") as fh:
                    api.post_file(f"/shops/{shop}/listings/{lid}/videos", {"video": (f"AstroLove_{cift[lid]}.mp4", fh, "video/mp4")},
                                  {"name": f"AstroLove_{cift[lid]}.mp4"})
        except (SystemExit, Exception) as e:
            sonuc.append((lid, "FAIL", f"'{adim}' adiminda hata: {str(e)[:160]} (yedek YEDEK/{lid}_TEK_ONCE.json)"))
            break
        L1 = api.get(f"/listings/{lid}", params={"includes": "Images,Videos"}) or {}
        vi1 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        ids1 = [x.get("listing_image_id") for x in sorted(L1.get("images") or [], key=lambda x: x.get("rank") or 0)]
        bag1 = {v.get("value_id"): v.get("image_id") for v in vi1}
        bek_bag = {renk_vid[ad_norm(x["renk"])]: int(yeni[id(x)]) for x in ip["renkli"]}
        hh = []
        if ids1 != bek:
            hh.append("sira SET'ten farkli")
        if bag1 != bek_bag:
            hh.append("renk baglari yeni gorsellerde degil")
        if L1.get("state") != st0:
            hh.append(f"state {st0} -> {L1.get('state')}")
        if setj.get("video") and len(L1.get("videos") or []) != 1:
            hh.append(f"video sayisi {len(L1.get('videos') or [])}")
        if set(ids0) & set(ids1):
            hh.append("eski gorsel kaldi")
        n = getattr(api, "calls", 0) - c0
        sonuc.append((lid, "PASS" if not hh else "FAIL", ("geri okuma temiz" if not hh else "; ".join(hh)) + f" | cagri {n}"))
        g = time.time() - t0
        log(f"  [{i}/{len(hedef)}] {lid} {sonuc[-1][1]} | gecen {g / 60:.1f} dk | kalan {g / i * (len(hedef) - i) / 60:.1f} dk "
            f"| %{i * 100 // len(hedef)} | kota {api.remaining}")
        if hh:
            break
    with (out / "SONUC_GALERI_TEK.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ilan", "sonuc", "not"])
        w.writerows(sonuc)
    ok = sum(1 for s in sonuc if s[1] == "PASS")
    log(f"PASS {ok}/{len(hedef)} | kota sonda {api.remaining}")
    return 0 if ok == len(hedef) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=["referans", "plan", "yaz"])
    ap.add_argument("--csv", default="_work/METIN_78.csv")
    ap.add_argument("--plan", default="_work/GALERI_PLAN.json")
    ap.add_argument("--referans", default="_work/REFERANS_SIRA.json")
    ap.add_argument("--varsayilan-sayi", type=int, default=13, help="referans yokken plan icin yeni set gorsel sayisi")
    ap.add_argument("--yerel", default="_work/tek", help="<CIFT>/SET.json + dosyalar")
    ap.add_argument("--out", default="_out/galeri_tek")
    ap.add_argument("--listing", default="")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--kota-alt", type=int, default=230)
    a = ap.parse_args()
    sys.exit({"referans": referans, "plan": plan, "yaz": yaz}[a.mod](a))


if __name__ == "__main__":
    main()
