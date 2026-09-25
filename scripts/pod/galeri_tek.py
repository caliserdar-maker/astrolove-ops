#!/usr/bin/env python3
"""TEK GALERI GECISI (Serdar, 25 Eyl 2026). 77 ilan (Cancer-Libra 4570143815 HARIC), medya + video ciktilari
gelince TEK seferde yazilir. Bu dosya plan + yazma kodunu tasir; yazma yalniz --confirm GALERI_TEK ile.

Hedef sira (en fazla 20 gorsel + 1 video; onerilen, Serdar onayi bekler):
   1 KAPAK            medya A1_77/<CIFT>/KAPAK.jpg (mevcut kapagin YERINE; eski kapak silinir)
   2 GENEL_1          kisisellestirme karti
   3 KART3            video ciktisi karti (yeni)
   4 KART09           isimli poster, medya A1_77/<CIFT>/KART09.jpg
   5-6 sahne 02, 03   mevcut oda sahneleri (korunur)
   7 Symbol Story     mevcut (korunur)
   8 Crafted Detail   mevcut (korunur)
   9-13 5 renk        mevcut MB/DB/WP/CI/PW hero, renk bagi KORUNUR (hic silinmez, yeniden yuklenmez)
  14-16 GENEL_2/3/4   olcu / kagit / siparis
  video               video oturumunun <CIFT> videosu (mevcut videonun YERINE)
  Toplam 16 gorsel. Eski 6/7/8 (kagit / olcu / teslimat) silinir.

Ilan tipleri: 'yeni' (13 gorsel, eski 6/7/8 duruyor) ve 'genel_var' (galeri_genel ile 4 kart almis 5 ilan:
kapak, kart 3, kart 09, video eklenir; G1..G4 korunur).

Modlar:
  plan : SALT OKUMA, Etsy API KOTASI HARCAMAZ. GALERI_PLAN.json (ilk durum id'leri + renk baglari) + METIN_78.csv
         (ilan -> cift) + Drive girdi listeleri (rclone lsf) -> TEK_PLAN.json + RAPOR; ilan basina cagri sayisi,
         eksik girdi, 20 siniri. --oas verilirse statik Etsy OAS ile uclar dogrulanir.
  yaz  : --listing (virgullu) ya da --hepsi, --confirm GALERI_TEK, --kota-alt. Her ilan: canli okuma -> kapilar
         (state active, id kumesi plandaki durumlardan biriyle AYNI, silinecek gorsel renge bagli degil, 20 siniri)
         -> sil / yukle / video / image_ids PATCH -> tam geri okuma (sira, renk baglari, state, video).
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
# GALERI_PLAN once_ids (rank sirasi, 13): 1 kapak | 2-3 sahne | 4 symbol | 5 crafted | 6-8 eski kart | 9-13 renk
ROL_ILK = ["kapak_eski", "sahne02", "sahne03", "symbol", "crafted", "eski6", "eski7", "eski8",
           "renk1", "renk2", "renk3", "renk4", "renk5"]
KORUNAN = ["sahne02", "sahne03", "symbol", "crafted", "renk1", "renk2", "renk3", "renk4", "renk5"]
SILINEN = ["kapak_eski", "eski6", "eski7", "eski8"]
HEDEF_SIRA = ["KAPAK", "GENEL_1", "KART3", "KART09", "sahne02", "sahne03", "symbol", "crafted",
              "renk1", "renk2", "renk3", "renk4", "renk5", "GENEL_2", "GENEL_3", "GENEL_4"]
GENEL_DOSYA = {"GENEL_1": "GENEL_1_kisisellestirme.jpg", "GENEL_2": "GENEL_2_olcu.jpg",
               "GENEL_3": "GENEL_3_kagit.jpg", "GENEL_4": "GENEL_4_siparis.jpg"}
csv.field_size_limit(10 ** 8)


def log(m):
    print(m, flush=True)


# ------------------------------------------------------------------ saf fonksiyonlar (yerel test)
def roller(p, mevcut_ids):
    """GALERI_PLAN kaydi + canli (ya da yedek) id sirasi -> (tip, {rol: id}, hatalar).
    tip 'yeni': mevcut == once_ids (13). tip 'genel_var': once_ids - sil_ids korunmus + 4 fazla kart
    (G1 kapaktan hemen sonra, G2..G4 sonda; galeri_genel yaz sirasi)."""
    once = [int(x) for x in p["once_ids"]]
    sil = {int(x) for x in p["sil_ids"]}
    mevcut = [int(x) for x in mevcut_ids]
    h = []
    if len(once) != len(ROL_ILK):
        return None, {}, [f"ilk durum {len(once)} gorsel (13 beklenir)"]
    rol = {r: i for r, i in zip(ROL_ILK, once)}
    if [rol[r] for r in ("eski6", "eski7", "eski8")] != [int(x) for x in p["sil_ids"]]:
        h.append("planin sil_ids'i 6/7/8 ile ayni degil")
    if mevcut == once:
        return "yeni", rol, h
    kalan = [x for x in once if x not in sil]
    fazla = [x for x in mevcut if x not in once]
    if [x for x in mevcut if x in once] == kalan and len(fazla) == 4 and len(mevcut) == len(once) - len(sil) + 4 \
            and mevcut[1] == fazla[0] and mevcut[-3:] == fazla[1:]:
        for r in ("eski6", "eski7", "eski8"):
            rol.pop(r)
        rol.update({"GENEL_1": fazla[0], "GENEL_2": fazla[1], "GENEL_3": fazla[2], "GENEL_4": fazla[3]})
        return "genel_var", rol, h
    return None, rol, h + [f"gorseller plandaki iki durumdan da farkli ({len(mevcut)} gorsel)"]


def islem_plani(tip, rol, bagli_ids, video_var=True):
    """-> dict: silinecek id'ler, yuklenecek roller, video islemi, sonuc sayisi, cagri sayisi, kapilar."""
    sil = [rol[r] for r in SILINEN if r in rol]
    yukle = [r for r in HEDEF_SIRA if r not in KORUNAN and not (tip == "genel_var" and r.startswith("GENEL_"))]
    bagli = {int(x) for x in bagli_ids}
    h = []
    if set(sil) & bagli:
        h.append("silinecek gorsel renge bagli")
    if {rol[r] for r in ("renk1", "renk2", "renk3", "renk4", "renk5")} != bagli:
        h.append("renk bagli 5 gorsel 9-13 ile ayni degil")
    sonuc = len(HEDEF_SIRA)
    if sonuc > AZAMI_GORSEL:
        h.append(f"{sonuc} gorsel > {AZAMI_GORSEL}")
    cagri = {"oku (ilan+gorsel+video, varyasyon-gorsel)": 2, "gorsel sil": len(sil), "gorsel yukle": len(yukle),
             "video sil": 1 if video_var else 0, "video yukle": 1, "sira PATCH": 1, "geri okuma": 2}
    return {"tip": tip, "sil": sil, "yukle": yukle, "sonuc_sayi": sonuc, "cagri": cagri,
            "cagri_toplam": sum(cagri.values()), "kapi": h}


def hedef_ids(rol, yeni):
    """rol -> id (korunan) + yeni yuklenen {rol: id} -> PATCH image_ids sirasi."""
    tum = dict(rol)
    tum.update(yeni)
    return [tum[r] for r in HEDEF_SIRA]


def girdi_yollari(cift, a):
    return {"KAPAK": f"{a.medya}/{cift}/KAPAK.jpg", "KART09": f"{a.medya}/{cift}/KART09.jpg",
            "KART3": a.kart3.replace("{CIFT}", cift), "VIDEO": a.video.replace("{CIFT}", cift)}


def eksik_girdi(cift, a, var):
    """var: medya (A1_77) ve video kokunun rclone lsf -R satirlari. --kart3 / --video bu koklere GORELI
    {CIFT} sablonudur (orn. '{CIFT}/KART3.jpg'); bos ise yol henuz belirlenmemistir."""
    e = [k for k in ("KAPAK", "KART09") if f"{cift}/{k}.jpg" not in var]
    for k, sablon in (("KART3", a.kart3), ("VIDEO", a.video)):
        if not sablon:
            e.append(f"{k} (yol henuz yok)")
        elif sablon.replace("{CIFT}", cift) not in var:
            e.append(k)
    return e


def oas_dogrula(yol):
    """Statik Etsy OAS: uclar + includes=Videos + image_ids alani."""
    d = json.loads(pathlib.Path(yol).read_text(encoding="utf-8"))
    ops = {}
    for pth, v in (d.get("paths") or {}).items():
        for m, o in v.items():
            if isinstance(o, dict) and o.get("operationId"):
                ops[o["operationId"]] = (m.upper(), pth, o)
    sonuc = {}
    for op in ("getListing", "getListingImages", "uploadListingImage", "deleteListingImage", "updateListing",
               "getListingVideos", "uploadListingVideo", "deleteListingVideo", "getListingVariationImages"):
        sonuc[op] = f"{ops[op][0]} {ops[op][1]}" if op in ops else "YOK"
    inc = []
    if "getListing" in ops:
        for prm in ops["getListing"][2].get("parameters") or []:
            if prm.get("name") == "includes":
                sch = prm.get("schema") or {}
                inc = (sch.get("items") or {}).get("enum") or sch.get("enum") or []
    sonuc["getListing includes"] = inc
    if "updateListing" in ops:
        body = json.dumps(ops["updateListing"][2].get("requestBody") or {})
        sonuc["updateListing image_ids"] = "image_ids" in body or "var ($ref)"
    if "uploadListingVideo" in ops:
        sonuc["uploadListingVideo govde"] = json.dumps(ops["uploadListingVideo"][2].get("requestBody") or {})[:400]
    return sonuc


# ------------------------------------------------------------------ plan
def plan(a):
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(a.csv, encoding="utf-8") as fh:
        cift = {r["ilan_id"]: r["cift"] for r in csv.DictReader(fh)}
    P = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))["plan"]
    var = set()
    for f in (a.girdiler or "").split(","):
        if f and pathlib.Path(f).exists():
            var |= {x.strip().rstrip("/") for x in pathlib.Path(f).read_text(encoding="utf-8").splitlines() if x.strip()}
    sonra = {}                                           # galeri_genel yaz sonrasi sira (5 ilan)
    for f in (a.sonuc or "").split(","):
        if f and pathlib.Path(f).exists():
            for r in csv.DictReader(open(f, encoding="utf-8")):
                if r.get("sonuc") == "PASS" and r.get("sonra_sira"):
                    sonra[r["ilan"]] = [int(x) for x in r["sonra_sira"].split(",")]
    kayit, top = {}, {"yeni": 0, "genel_var": 0, "HATA": 0}
    for lid in [k for k in cift if k != REF]:
        p = P.get(lid)
        if not p:
            kayit[lid] = {"hata": ["GALERI_PLAN'da yok"]}
            top["HATA"] += 1
            continue
        durum = sonra.get(lid) or (None if lid in GENEL_VAR else [int(x) for x in p["once_ids"]])
        if durum is None:                                # 4 kartli ilanin sonrasi bilinmiyor: yazmada canli okunur
            kayit[lid] = {"cift": cift[lid], "tip": "genel_var", "not": "sonra_sira yok; yazmada canli okunur",
                          "cagri_toplam": 11}
            top["genel_var"] += 1
            continue
        tip, rol, h = roller(p, durum)
        if not tip:
            kayit[lid] = {"cift": cift[lid], "hata": h}
            top["HATA"] += 1
            continue
        ip = islem_plani(tip, rol, p.get("bagli_ids") or [])
        g = girdi_yollari(cift[lid], a)
        eksik = eksik_girdi(cift[lid], a, var)
        ip.update({"cift": cift[lid], "roller": rol, "girdi": g, "eksik_girdi": eksik,
                   "hata": h + ip["kapi"]})
        kayit[lid] = ip
        top["HATA" if ip["hata"] else tip] += 1
    toplam_cagri = sum(v.get("cagri_toplam", 0) for v in kayit.values())
    oas = oas_dogrula(a.oas) if a.oas and pathlib.Path(a.oas).exists() else {}
    (out / "TEK_PLAN.json").write_text(json.dumps({"hedef_sira": HEDEF_SIRA, "ilan": kayit, "oas": oas},
                                                  indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    ornek = next((v for v in kayit.values() if v.get("tip") == "yeni" and "cagri" in v), {})
    ornek5 = next((v for v in kayit.values() if v.get("tip") == "genel_var" and "cagri" in v), {})
    rapor = [f"# Tek galeri gecisi — PLAN (salt okuma, Etsy kotasi harcanmadi) — {time.strftime('%Y-%m-%d %H:%M')} UTC", "",
             f"- ilan: {len(kayit)} | yeni (13 gorsel): {top['yeni']} | 4 kartli: {top['genel_var']} | hata: {top['HATA']}",
             f"- hedef sira ({len(HEDEF_SIRA)} gorsel + video): " + " | ".join(f"{i}:{r}" for i, r in enumerate(HEDEF_SIRA, 1)),
             f"- cagri/ilan yeni: {ornek.get('cagri_toplam')} {ornek.get('cagri')}",
             f"- cagri/ilan 4 kartli: {ornek5.get('cagri_toplam', 11)} {ornek5.get('cagri', '')}",
             f"- toplam tahmini cagri (yuklemede tekrar deneme haric): {toplam_cagri}",
             f"- eksik girdili ilan: {sum(1 for v in kayit.values() if isinstance(v.get('eksik_girdi'), list) and v['eksik_girdi'])}",
             "", "## OAS", ""] + [f"- {k}: {v}" for k, v in oas.items()] + \
            ["", "## Hatalar", ""] + ([f"- {k}: {v['hata']}" for k, v in kayit.items() if v.get("hata")] or ["- yok"])
    metin = "\n".join(rapor)
    (out / "RAPOR_galeri_tek_plan.md").write_text(metin + "\n", encoding="utf-8")
    log(metin)
    return 1 if top["HATA"] else 0


# ------------------------------------------------------------------ yaz
def yaz(a, api=None, shop=None):
    if a.confirm != ONAY:
        sys.exit(f"HATA: yaz --confirm {ONAY} ister")
    out = pathlib.Path(a.out)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    with open(a.csv, encoding="utf-8") as fh:
        cift = {r["ilan_id"]: r["cift"] for r in csv.DictReader(fh)}
    P = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))["plan"]
    kart = pathlib.Path(a.kartlar)
    if api is None:
        from etsy_common import Etsy, TokenStore
        store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
        if store.needs_refresh():
            store.refresh()
        api = Etsy(store)
        shop = os.environ["ETSY_SHOP_ID"]
    hedef = [x.strip() for x in a.listing.split(",") if x.strip()] if a.listing else [k for k in cift if k != REF]
    sonuc, t0 = [], time.time()

    def anlik(lid):
        L = api.get(f"/listings/{lid}", params={"includes": "Images,Videos"}) or {}
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        imgs = sorted(L.get("images") or [], key=lambda x: x.get("rank") or 0)
        return L.get("state"), [x.get("listing_image_id") for x in imgs], L.get("videos") or [], \
            {v.get("value_id"): v.get("image_id") for v in vi}

    for i, lid in enumerate(hedef, 1):
        try:
            kota = int(api.remaining or 99999)
        except ValueError:
            kota = 99999
        if kota < a.kota_alt:
            sonuc.append((lid, "DURDU", f"kota {api.remaining} < {a.kota_alt}"))
            break
        if lid == REF or lid not in P or lid not in cift:
            sonuc.append((lid, "ATLANDI", "kapsam/plan disi"))
            continue
        c0 = getattr(api, "calls", 0)
        st0, ids0, vid0, vb0 = anlik(lid)
        (out / "YEDEK" / f"{lid}_TEK_ONCE.json").write_text(json.dumps({"state": st0, "images": ids0, "videos": vid0, "var": vb0}, indent=1), encoding="utf-8")
        tip, rol, h = roller(P[lid], ids0)
        g = girdi_yollari(cift[lid], a)
        dosya = {"KAPAK": pathlib.Path(a.yerel) / cift[lid] / "KAPAK.jpg", "KART09": pathlib.Path(a.yerel) / cift[lid] / "KART09.jpg",
                 "KART3": pathlib.Path(a.yerel) / cift[lid] / "KART3.jpg", "VIDEO": pathlib.Path(a.yerel) / cift[lid] / "VIDEO.mp4"}
        dosya.update({k: kart / v for k, v in GENEL_DOSYA.items()})
        if tip:
            ip = islem_plani(tip, rol, list(vb0.values()), video_var=bool(vid0))
            h += ip["kapi"]
            h += [f"dosya yok: {k}" for k in ip["yukle"] + ["VIDEO"] if not dosya[k].exists()]
        if st0 != "active":
            h.append(f"state {st0} (updateListing taslagi yayina alir)")
        if not tip or h:
            sonuc.append((lid, "ATLANDI", "; ".join(h) or "tip yok"))
            continue
        try:
            for iid in ip["sil"]:
                api.delete(f"/shops/{shop}/listings/{lid}/images/{iid}")
            yeni = {}
            for r in ip["yukle"]:
                with open(dosya[r], "rb") as fh:
                    res = api.post_file(f"/shops/{shop}/listings/{lid}/images", {"image": (dosya[r].name, fh, "image/jpeg")},
                                        {"rank": str(HEDEF_SIRA.index(r) + 1)})
                yeni[r] = res.get("listing_image_id")
            for v in vid0:
                api.delete(f"/shops/{shop}/listings/{lid}/videos/{v.get('video_id')}")
            with open(dosya["VIDEO"], "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/videos", {"video": (f"AstroLove_{cift[lid]}.mp4", fh, "video/mp4")},
                              {"name": f"AstroLove_{cift[lid]}.mp4"})
            bek = hedef_ids(rol, yeni)
            api.patch(f"/shops/{shop}/listings/{lid}", {"image_ids": ",".join(str(x) for x in bek)})
        except SystemExit as e:
            sonuc.append((lid, "FAIL", f"yazma hatasi: {str(e)[:200]}"))
            break
        st1, ids1, vid1, vb1 = anlik(lid)
        hh = []
        if ids1 != bek:
            hh.append("sira beklenenden farkli")
        if len(ids1) > AZAMI_GORSEL:
            hh.append(f"{len(ids1)} gorsel")
        if vb1 != vb0:
            hh.append("renk baglari degisti")
        if st1 != st0:
            hh.append(f"state {st0} -> {st1}")
        if len(vid1) != 1:
            hh.append(f"video sayisi {len(vid1)}")
        cagri = getattr(api, "calls", 0) - c0
        sonuc.append((lid, "PASS" if not hh else "FAIL", ("geri okuma temiz" if not hh else "; ".join(hh)) + f" | cagri {cagri}"))
        gg = time.time() - t0
        log(f"  [{i}/{len(hedef)}] {lid} {sonuc[-1][1]} | gecen {gg / 60:.1f} dk | kalan {gg / i * (len(hedef) - i) / 60:.1f} dk "
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
    ap.add_argument("mod", choices=["plan", "yaz"])
    ap.add_argument("--csv", default="_work/METIN_78.csv")
    ap.add_argument("--plan", default="_work/GALERI_PLAN.json")
    ap.add_argument("--sonuc", default="", help="galeri_genel SONUC_GALERI.csv (virgullu)")
    ap.add_argument("--girdiler", default="", help="rclone lsf -R ciktilari (virgullu)")
    ap.add_argument("--oas", default="")
    ap.add_argument("--medya", default="gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77")
    ap.add_argument("--kart3", default="", help="kart 3 yolu, {CIFT} yer tutuculu (video oturumu belirleyecek)")
    ap.add_argument("--video", default="", help="video yolu, {CIFT} yer tutuculu (video oturumu belirleyecek)")
    ap.add_argument("--yerel", default="_work/tek", help="yazmada indirilen <CIFT>/KAPAK|KART09|KART3|VIDEO")
    ap.add_argument("--kartlar", default="_work/kartlar")
    ap.add_argument("--out", default="_out/galeri_tek")
    ap.add_argument("--listing", default="")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--kota-alt", type=int, default=230)
    a = ap.parse_args()
    sys.exit(plan(a) if a.mod == "plan" else yaz(a))


if __name__ == "__main__":
    main()
