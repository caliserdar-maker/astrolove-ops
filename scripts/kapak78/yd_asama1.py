#!/usr/bin/env python3
"""YD (1st Anniversary) 1. ASAMA: 78 ilanda yalniz KAPAK (rank 1 = Y01) + VIDEO (Serdar 1 Kas). Galeri, SKU, boyut, aciklama YOK.
updateListing YOK (CLAUDE.md 7 Eyl); silme yalniz eski VIDEO (yeni video active okununca). Kota tabani 10 (etsy_common.KOTA_SINIRI).

oku   (Etsy SALT OKUMA, kilit altinda): 78 ilan toplu getListingsByListingIds (includes=Images,Videos; 100'luk paket = 1 istek)
      -> <out>/HAM_ASAMA1.json (state, gorseller: id/rank/url/alt/boyut, videolar: id/url/state). Yazma cagrisi YASAK.
plan  (ETSY YOK, kilitsiz): HAM + yedek klasoru (is akisi CDN'den indirir: <yedek>/<lid>_<image_id>.jpg rank 1, <lid>_<video_id>.mp4)
      + Y01 klasorleri (<CIFT>_Y01.jpg) + VIDEO_ESLEME.csv + video klasoru + eski kapak listesi -> PLAN.json + PLAN.csv + PLAN.md.
      Ilan basina: kapak DEGISTIR | AYNI (canli rank 1 ile Y01 256 px gri ortalama mutlak fark <= KAPAK_AYNI_ESIK: elle degistirilmis
      kapak, yalniz video) ; video DEGISTIR | YUKLE ; BLOK (neden). Plan sha256 = plan_damga (uygula ayni plani ister).
uygula (Etsy YAZAR, kilit altinda; --confirm YD_ASAMA1 + --plan + --plan-damga; --sadece pilot): ilan basina, ilk FAIL'de DUR:
      0) kota kapisi + canli okuma: state active, canli rank 1 / video kimlikleri PLAN ile ayni (degilse ATLA, DEGISTI).
      1) kapak DEGISTIR: variation-images okunur; Y01 uploadListingImage rank=1 overwrite=true alt_text=eski alt (TEK gonderim);
         gorseller okunur: rank 1 yeni id, sayi ayni, 2..n ayni sira; eski kapaga bag varsa tam liste yeni id ile geri gonderilir + okunur.
      2) video: yeni video TEK gonderim; active + url dolu okunana dek beklenir; sonra plandaki eski video(lar) silinir; okunur.
      3) son okuma: state active, rank 1 = beklenen, ilanda yalniz yeni video. SONUC.json her ilandan sonra yazilir.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE (oku / uygula)."""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

KAPAK_AYNI_ESIK = 3.0     # TAHMIN (olcumle dogrulanacak): 256 px gri ortalama mutlak fark (0-255); Etsy yeniden kodlamasi < 3 beklenir
ONAY = "YD_ASAMA1"
VIDEO_DENEME, VIDEO_BEKLE = 12, 10       # yeni video active olana dek ~2 dk (video_yukle_78 v7 ile ayni)
ILAN_UST = 25            # ilan basina en cok istek (kapak 5 + bag 2 + video 1 + active okuma 12 + silme 1-2 + son 1; video_yukle_78 ILAN_CAGRI_UST
#                          ile ayni yaklasim): ilan basinda kalan < KOTA_SINIRI + ILAN_UST ise o ilana BASLANMAZ (yarim ilan birakilmaz), DUR
GORSEL_DENEME, GORSEL_BEKLE = 4, 8


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ids_oku(p):
    return [(r["listing_id"], r["cift"]) for r in csv.DictReader(open(p, encoding="utf-8"))]


# ------------------------------------------------------------------ oku
def oku(api, ids, out):
    R = {}
    lids = [l for l, _ in ids]
    for i in range(0, len(lids), 100):
        js = api.get("/listings/batch", params={"listing_ids": ",".join(lids[i:i + 100]), "includes": "Images,Videos"}) or {}
        for x in js.get("results") or []:
            R[str(x["listing_id"])] = dict(
                state=x.get("state"),
                gorseller=[dict(id=str(g.get("listing_image_id")), rank=g.get("rank"), url=g.get("url_fullxfull"), alt=g.get("alt_text"),
                                w=g.get("full_width"), h=g.get("full_height")) for g in sorted(x.get("images") or [], key=lambda g: g.get("rank") or 0)],
                videolar=[dict(id=str(v.get("video_id")), url=v.get("video_url"), state=v.get("video_state")) for v in x.get("videos") or []])
    eksik = [l for l in lids if l not in R]
    json.dump(dict(ilanlar=R, eksik=eksik, istek=api.calls, kota=api.remaining), open(Path(out) / "HAM_ASAMA1.json", "w"), indent=1)
    print(f"OKU: {len(R)}/{len(lids)} ilan | eksik {eksik} | istek {api.calls} | kota {api.remaining}")
    return 0 if not eksik else 1


# ------------------------------------------------------------------ plan
def gri(p):
    return np.asarray(Image.open(p).convert("L").resize((256, 192), Image.BILINEAR), dtype=np.float32)


def plan(a):
    H = json.load(open(a.ham))["ilanlar"]
    ids = ids_oku(a.ids)
    ves = {r["cift"]: r for r in csv.DictReader(open(a.esleme, encoding="utf-8"))}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import yd_liste_uret as L
    eski = L.eski_kapak_oku(Path(a.eski_kapak)) if a.eski_kapak else L.eski_kapak_oku()
    satir = []
    for lid, c in ids:
        P = dict(listing_id=lid, cift=c, neden=[])
        h = H.get(lid)
        if not h:
            P.update(durum="BLOK"); P["neden"].append("canli okuma yok"); satir.append(P); continue
        if h["state"] != "active":
            P["neden"].append(f"state {h['state']} (active degil; updateListing yok ama taslak/pasif ilana bu asamada yazilmaz)")
        g = h["gorseller"]
        if not g or g[0]["rank"] != 1:
            P["neden"].append("rank 1 gorsel yok")
        # Y01: once 3 yeni kapak klasoru, sonra ana set
        y01 = next((Path(d) / f"{c}_Y01.jpg" for d in a.y01 if (Path(d) / f"{c}_Y01.jpg").exists()), None)
        if not y01:
            P["neden"].append("Y01 dosyasi yok")
        else:
            ys = sha(y01)
            n = L.eski_kapak_neden(c, ys, eski)
            P["neden"] += n
            P["kapak"] = dict(dosya=str(y01), sha256=ys)
        v = ves.get(c)
        vp = Path(a.video_kok) / v["dosya"] if v else None
        if not v or v.get("durum") != "OK" or str(v.get("listing_id")) != lid:
            P["neden"].append("video esleme satiri yok / OK degil / ilan no farkli")
        elif not vp.exists() or sha(vp) != v["sha256"]:
            P["neden"].append("video dosyasi yok ya da sha256 esleme tablosundan farkli")
        else:
            P["video"] = dict(dosya=str(vp), sha256=v["sha256"], damga=v["damga"], kosu=v["kosu"],
                              eski=[x["id"] for x in h["videolar"]], islem="DEGISTIR" if h["videolar"] else "YUKLE")
        if g and y01 and not P["neden"]:
            r1 = g[0]
            yed = Path(a.yedek) / f"{lid}_{r1['id']}.jpg"
            if not yed.exists():
                P["neden"].append(f"canli rank 1 yedegi yok ({yed.name})")
            else:
                d = float(np.abs(gri(yed) - gri(y01)).mean())
                P["kapak"].update(eski_id=r1["id"], eski_alt=r1.get("alt") or "", fark=round(d, 3),
                                  islem="AYNI" if d <= KAPAK_AYNI_ESIK else "DEGISTIR", gorsel_sira=[x["id"] for x in g])
            for x in h["videolar"]:
                if not (Path(a.yedek) / f"{lid}_{x['id']}.mp4").exists():
                    P["neden"].append(f"eski video yedegi yok ({lid}_{x['id']}.mp4)")
        P["durum"] = "BLOK" if P["neden"] else "PLAN"
        satir.append(P)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    govde = dict(surum=1, esik_kapak_ayni=KAPAK_AYNI_ESIK, ilanlar=satir)
    b = json.dumps(govde, indent=1, ensure_ascii=False, sort_keys=True).encode()
    (out / "PLAN.json").write_bytes(b)
    damga = hashlib.sha256(b).hexdigest()[:16]
    (out / "PLAN_DAMGA.txt").write_text(damga + "\n")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "cift", "durum", "kapak", "kapak_fark", "video", "eski_video", "neden"])
        for P in satir:
            k, v = P.get("kapak") or {}, P.get("video") or {}
            w.writerow([P["listing_id"], P["cift"], P["durum"], k.get("islem", ""), k.get("fark", ""), v.get("islem", ""),
                        " ".join(v.get("eski") or []), "; ".join(P["neden"])])
    say = {}
    for P in satir:
        anahtar = P["durum"] if P["durum"] == "BLOK" else f"{(P.get('kapak') or {}).get('islem')}+{(P.get('video') or {}).get('islem')}"
        say[anahtar] = say.get(anahtar, 0) + 1
    farklar = sorted((P["kapak"]["fark"], P["cift"]) for P in satir if (P.get("kapak") or {}).get("fark") is not None)
    tahmin = sum(istek_tahmini(P) for P in satir if P["durum"] == "PLAN")
    md = [f"# YD 1. asama PLAN (damga {damga})", "", f"Durum: {say}", f"Istek tahmini (uygula, TAHMIN): {tahmin}",
          f"Kapak AYNI esigi {KAPAK_AYNI_ESIK} (TAHMIN). En kucuk 8 fark: {farklar[:8]}", f"En buyuk 3 fark: {farklar[-3:]}", "",
          "| ilan | cift | durum | kapak (fark) | video | neden |", "|---|---|---|---|---|---|"]
    md += [f"| {P['listing_id']} | {P['cift']} | {P['durum']} | {(P.get('kapak') or {}).get('islem', '')} ({(P.get('kapak') or {}).get('fark', '')}) | "
           f"{(P.get('video') or {}).get('islem', '')} | {'; '.join(P['neden'])} |" for P in satir]
    (out / "PLAN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"PLAN {damga}: {say} | istek tahmini {tahmin}")
    return 0 if all(P["durum"] == "PLAN" for P in satir) else 1


def istek_tahmini(P):
    """uygula ilan basina istek (TAHMIN): canli okuma 1 + kapak (varyasyon 1, yukleme 1, gorsel okuma 1, bag 0-2) + video (yukleme 1,
    active okuma 1-3, silme n, okuma 1) + son okuma 1."""
    n = 2
    if (P.get("kapak") or {}).get("islem") == "DEGISTIR":
        n += 3
    v = P.get("video") or {}
    n += 3 + len(v.get("eski") or [])
    return n


# ------------------------------------------------------------------ uygula
class Yazar:
    """Izinli yazmalar: yalniz plandaki ilanlarda rank 1 gorsel yukleme, varyasyon gorseli, video yukleme, ESKI video silme."""

    def __init__(self, api, shop, plan_ids, eski_videolar):
        self.api, self.shop, self.ids, self.eski_v = api, shop, set(plan_ids), eski_videolar

    def _ilan(self, lid):
        if str(lid) not in self.ids:
            raise SystemExit(f"YASAK: plan disi ilan {lid}")

    def gorsel(self, lid, p, alt):
        self._ilan(lid)
        with open(p, "rb") as fh:
            return self.api.post_file(f"/shops/{self.shop}/listings/{lid}/images", files={"image": (Path(p).name, fh, "image/jpeg")},
                                      data={"rank": "1", "overwrite": "true", "alt_text": alt}, tekrar=1)

    def bag(self, lid, liste):
        self._ilan(lid)
        return self.api.post_json(f"/shops/{self.shop}/listings/{lid}/variation-images", {"variation_images": liste})

    def video(self, lid, p):
        self._ilan(lid)
        with open(p, "rb") as fh:
            return self.api.post_file(f"/shops/{self.shop}/listings/{lid}/videos", files={"video": (Path(p).name, fh, "video/mp4")},
                                      data={"name": Path(p).name}, tekrar=1)

    def video_sil(self, lid, vid):
        self._ilan(lid)
        if str(vid) not in self.eski_v.get(str(lid), set()):
            raise SystemExit(f"YASAK: plandaki eski video olmayan silme {lid}/{vid}")
        return self.api.delete(f"/shops/{self.shop}/listings/{lid}/videos/{vid}", ok404=True)


def canli(api, lid):
    js = api.get("/listings/batch", params={"listing_ids": str(lid), "includes": "Images,Videos"}) or {}
    x = (js.get("results") or [{}])[0]
    g = sorted(x.get("images") or [], key=lambda g: g.get("rank") or 0)
    return x.get("state"), [str(i.get("listing_image_id")) for i in g], g, [str(v.get("video_id")) for v in x.get("videos") or []], x.get("videos") or []


def uygula(a, api, shop):
    b = Path(a.plan).read_bytes()
    if hashlib.sha256(b).hexdigest()[:16] != a.plan_damga or a.confirm != ONAY:
        raise SystemExit("DUR: plan_damga / confirm uyusmuyor; yazma yok")
    PL = json.loads(b)
    sec = [P for P in PL["ilanlar"] if P["durum"] == "PLAN" and (not a.sadece or P["listing_id"] in a.sadece.split(","))]
    if a.sadece and len(sec) != len(a.sadece.split(",")):
        raise SystemExit(f"DUR: --sadece ilanlarindan PLAN durumunda olmayan var ({a.sadece})")
    for P in sec:   # dosyalar plan ile ayni mi (yazmadan once, hepsi)
        if P["kapak"]["islem"] == "DEGISTIR" and sha(P["kapak"]["dosya"]) != P["kapak"]["sha256"]:
            raise SystemExit(f"DUR: {P['cift']} Y01 sha256 plandan farkli")
        if sha(P["video"]["dosya"]) != P["video"]["sha256"]:
            raise SystemExit(f"DUR: {P['cift']} video sha256 plandan farkli")
    Y = Yazar(api, shop, [P["listing_id"] for P in sec], {P["listing_id"]: set(P["video"]["eski"]) for P in sec})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    S = json.load(open(out / "SONUC.json")) if (out / "SONUC.json").exists() else {}
    t0 = time.time()
    for i, P in enumerate(sec, 1):
        lid, c = P["listing_id"], P["cift"]
        if S.get(lid, {}).get("durum") == "PASS":
            continue
        api.kota_kapisi(f"ilan {lid}")
        from etsy_common import KOTA_SINIRI
        if api.remaining is not None and int(api.remaining) < KOTA_SINIRI + ILAN_UST:
            print(f"::warning::KOTA: kalan {api.remaining} < {KOTA_SINIRI} + {ILAN_UST}; {c} ve sonrasi baslamadi (kota acilinca onceki={out.name} ile surdur)")
            return 4
        R = S[lid] = dict(cift=c, adim=[], durum="BASLADI", istek_bas=api.calls)

        def kaydet():
            json.dump(S, open(out / "SONUC.json", "w"), indent=1, ensure_ascii=False)
        st, gids, g, vids, _ = canli(api, lid)
        k = P["kapak"]
        bek_r1 = k["eski_id"]
        if st != "active" or gids != k["gorsel_sira"] or sorted(vids) != sorted(P["video"]["eski"]):
            R.update(durum="ATLA", neden=f"canli plandan farkli (state {st}, gorsel {len(gids)}, video {vids})"); kaydet()
            print(f"::warning::{c} ATLA (DEGISTI)"); continue
        try:
            if k["islem"] == "DEGISTIR":
                vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
                R["bag_once"] = vi
                yg = Y.gorsel(lid, k["dosya"], k["eski_alt"])
                yeni_id = str((yg or {}).get("listing_image_id") or "")
                ok = False
                for _ in range(GORSEL_DENEME):
                    st, gids2, g2, _, _ = canli(api, lid)
                    if gids2 and gids2[0] not in (bek_r1, "") and gids2[1:] == gids[1:] and len(gids2) == len(gids):
                        ok = True; break
                    time.sleep(GORSEL_BEKLE)
                if not ok:
                    raise RuntimeError(f"kapak geri okuma: rank1 {gids2[:1]} (eski {bek_r1}, yanit {yeni_id}), sayi {len(gids2)}/{len(gids)}")
                bek_r1 = gids2[0]
                R["adim"].append(("kapak", bek_r1))
                eski_bag = [v for v in vi if str(v.get("image_id")) == k["eski_id"]]
                if eski_bag:
                    yeni_liste = [dict(property_id=v["property_id"], value_id=v["value_id"],
                                       image_id=int(bek_r1) if str(v.get("image_id")) == k["eski_id"] else v["image_id"]) for v in vi]
                    Y.bag(lid, yeni_liste)
                    vi2 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
                    if sorted((v["property_id"], v["value_id"], str(v["image_id"])) for v in vi2) != \
                            sorted((v["property_id"], v["value_id"], str(v["image_id"])) for v in yeni_liste):
                        raise RuntimeError("varyasyon bagi geri okuma farkli")
                    R["adim"].append(("bag", len(eski_bag)))
            # video
            yv = Y.video(lid, P["video"]["dosya"])
            yeni_v = str((yv or {}).get("video_id") or "")
            aktif = False
            for _ in range(VIDEO_DENEME):
                _, _, _, vids2, vs = canli(api, lid)
                y = next((v for v in vs if str(v.get("video_id")) not in P["video"]["eski"]), None)
                if y and y.get("video_state") == "active" and y.get("video_url"):
                    yeni_v, aktif = str(y["video_id"]), True; break
                time.sleep(VIDEO_BEKLE)
            if not aktif:
                raise RuntimeError(f"yeni video active okunmadi (yanit {yeni_v}); eski video SILINMEDI")
            R["adim"].append(("video", yeni_v))
            for e in P["video"]["eski"]:
                Y.video_sil(lid, e)
            st, gids3, _, vids3, _ = canli(api, lid)
            K = {"state active": st == "active", "rank 1 beklenen": bool(gids3) and gids3[0] == bek_r1,
                 "gorsel sayisi ayni": len(gids3) == len(gids), "yalniz yeni video": vids3 == [yeni_v]}
            R.update(kontrol=K, durum="PASS" if all(K.values()) else "FAIL", istek=api.calls - R["istek_bas"], kota=api.remaining)
        except BaseException as e:   # noqa: BLE001
            R.update(durum="FAIL", hata=f"{type(e).__name__}: {e}"[:500], istek=api.calls - R["istek_bas"], kota=api.remaining)
        kaydet()
        g_ = time.time() - t0
        print(f"[{i}/{len(sec)}] {c} {R['durum']} | istek {R.get('istek')} | kota {api.remaining} | gecen {g_:.0f} sn | "
              f"kalan ~{g_ / i * (len(sec) - i):.0f} sn | %{100 * i // len(sec)}", flush=True)
        if R["durum"] != "PASS":
            print(f"::error::{c} FAIL: {R.get('hata') or R.get('kontrol')}; DUR (kalanlar baslamadi)")
            return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("adim", choices=["oku", "plan", "uygula"])
    ap.add_argument("--ids", default=str(KOK / "data/pod/yd78_ids.csv"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--ham"); ap.add_argument("--yedek"); ap.add_argument("--y01", action="append", default=[])
    ap.add_argument("--esleme"); ap.add_argument("--video-kok"); ap.add_argument("--eski-kapak")
    ap.add_argument("--plan"); ap.add_argument("--plan-damga", default=""); ap.add_argument("--confirm", default="")
    ap.add_argument("--sadece", default="")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    if a.adim == "plan":
        sys.exit(plan(a))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    if a.adim == "oku":
        api.post = api.put = api.patch = api.delete = api.post_json = api.put_json = api.post_file = \
            lambda *x, **y: (_ for _ in ()).throw(SystemExit("YASAK: salt okuma"))
        sys.exit(oku(api, ids_oku(a.ids), a.out))
    sys.exit(uygula(a, api, os.environ["ETSY_SHOP_ID"]))


if __name__ == "__main__":
    main()
