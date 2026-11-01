#!/usr/bin/env python3
"""YD (1st Anniversary) 1. ASAMA: 78 ilanda yalniz KAPAK (rank 1 = Y01) + VIDEO (Serdar 1 Kas). Galeri, SKU, boyut, aciklama YOK.
updateListing YOK (CLAUDE.md 7 Eyl). Silme yalniz: (a) eski VIDEO, yeni video active okununca; (b) overwrite=true eski kapagi
DEGISTIRMEYIP 1. siraya ekleyip kaydirdiysa planin eski kapak gorseli (gorsel02_degistir.py ile ayni cozum). Kota tabani 10.
Is akisi YALNIZ dal yd-asama1 uzerinden kosar (Serdar 1 Kas: arac main'e alinmaz; main'de yalniz yml).

oku   (Etsy SALT OKUMA, kilit altinda): 78 ilan toplu getListingsByListingIds (includes=Images,Videos; 100'luk paket = 1 istek)
      -> <out>/HAM_ASAMA1.json. Yazma cagrisi YASAK.
plan  (ETSY YOK, kilitsiz): HAM + yedek (CDN; rank 1 + video) + Y01 klasorleri (MANIFEST.csv sha256 + 3000x2250) + VIDEO_ESLEME.csv
      (onayli sha256 ESLEME_SHA) + videolar (ffprobe: 1440x1080, 5-15 sn, < 100 MB, ses yok) -> PLAN.json/.csv/.md + PLAN_DAMGA.txt.
      Kapak AYNI (yalniz video) YALNIZ Serdar'in elle degistirdigi ilk 5 ilanda (yd78_ids sira 1-5) ve blok olcutuyle: 256x192 gri mutlak
      farkin 8x8 blok ortalamalarinin EN BUYUGU <= KAPAK_AYNI_BLOK (tahmin); digerleri DEGISTIR. Galeri sayisi GALERI_N degilse BLOK.
      Yeni kapak alt metni: yd_liste_uret.alt_metin (Serdar 26 Eki ALT_SABLON) + yasak / HTML / 250 kapisi.
uygula (Etsy YAZAR, kilit altinda; --confirm YD_ASAMA1 + --plan + --plan-damga; --sadece pilot): ilan basina, ilk FAIL / ATLA'da DUR:
      0) kota: kalan >= KOTA_SINIRI + ILAN_UST degilse ilana BASLANMAZ (cikis 4, kaldigi yerden); --bitis gectiyse cikis 5.
         canli okuma: state active, galeri kimlikleri ve video kimlikleri PLAN ile ayni; degilse ATLA ve DUR (cikis 1).
      1) kapak DEGISTIR: Y01 uploadListingImage rank=1 overwrite=true alt_text (TEK gonderim; hata yanitinda ilan okunur).
         Gorseller okunur (/listings/{id}/images): yer degistirme (sayi ayni, 2..n ayni) ya da ekleme (sayi +1, 2. sira eski kapak:
         eski kapak silinir, tekrar okunur). Yeni rank 1 boyutu 3000x2250. Eski kapaga bagli Style bagi varsa tam liste yeni kimlikle.
      2) video: TEK gonderim; hata yanitinda ilan okunur (eski kumede olmayan TEK video = yuklenmis); active + url okunana dek beklenir;
         sonra plandaki eski video(lar) silinir; ilanda yalniz yeni video kalana dek okunur.
      3) son kontrol: state active, rank 1 = yeni (ya da AYNI), gorsel sayisi = plan, yalniz yeni video. SONUC.json her ilandan sonra.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE (oku / uygula)."""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ONAY = "YD_ASAMA1"
ESLEME_SHA = "74d2ee6012de376681cb3cf668d244d8babe79e50654b114a8a7d418d51a30bc"   # Serdar 1 Kas onayli VIDEO_ESLEME.csv (20261101_143705)
MANUEL_N = 5               # Serdar elle degistirdi: yd78_ids.csv sira 1-5 (Serdar 1 Kas)
KAPAK_AYNI_BLOK = 6.0      # TAHMIN: 8x8 blok ortalama mutlak farkin en buyugu (0-255); yeniden kodlama blok farki bunun cok altinda
#                            beklenir, %1'lik gorunur degisim blokta >> 6 (inceleme sentetik olcumu: rozet %1,2 -> p99 178). Plan dagilimi raporlar.
GALERI_N = 13              # YD canli galeri (YD_OZET 13); farkliysa BLOK (elle degisimde eski kapak galeride kalmis olabilir)
Y01_BOYUT = (3000, 2250)
ILAN_UST = 105             # ilan basina en kotu istek 35 (canli 1 + bag 2 + kapak 1 + gorsel okuma 4 + eski gorsel sil 1 + okuma 4 + video 1 +
#                            active okuma 12 + silme 2 + son okuma 4 + 3) x 3 (etsy_common._call 5xx / 429 tekrari; video_yukle_78
#                            ILAN_CAGRI_UST_V7 ile ayni yaklasim; yeni kota esigi DEGIL, taban KOTA_SINIRI 10 aynen)
VIDEO_DENEME, VIDEO_BEKLE = 12, 10
GORSEL_DENEME, GORSEL_BEKLE = 4, 8


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ids_oku(p):
    return [(r["listing_id"], r["cift"], r.get("a", ""), r.get("b", "")) for r in csv.DictReader(open(p, encoding="utf-8"))]


# ------------------------------------------------------------------ oku
def oku(api, ids, out):
    R = {}
    lids = [x[0] for x in ids]
    for i in range(0, len(lids), 100):
        js = api.get("/listings/batch", params={"listing_ids": ",".join(lids[i:i + 100]), "includes": "Images,Videos"}) or {}
        for x in js.get("results") or []:
            R[str(x["listing_id"])] = dict(
                state=x.get("state"),
                gorseller=[dict(id=str(g.get("listing_image_id")), rank=g.get("rank"), url=g.get("url_fullxfull"), alt=g.get("alt_text"),
                                w=g.get("full_width"), h=g.get("full_height")) for g in sorted(x.get("images") or [], key=lambda g: g.get("rank") or 0)],
                videolar=[dict(id=str(v.get("video_id")), url=v.get("video_url"), state=v.get("video_state")) for v in x.get("videos") or []])
    eksik = [l for l in lids if l not in R]
    with open(Path(out) / "HAM_ASAMA1.json", "w") as fh:
        json.dump(dict(ilanlar=R, eksik=eksik, istek=api.calls, kota=api.remaining), fh, indent=1)
    print(f"OKU: {len(R)}/{len(lids)} ilan | eksik {eksik} | istek {api.calls} | kota {api.remaining}")
    return 0 if not eksik else 1


# ------------------------------------------------------------------ plan
def gri(p):
    return np.asarray(Image.open(p).convert("L").resize((256, 192), Image.BILINEAR), dtype=np.float32)


def blok_fark(a, b):
    d = np.abs(gri(a) - gri(b)).reshape(24, 8, 32, 8).mean(axis=(1, 3))
    return float(d.max()), float(np.abs(gri(a) - gri(b)).mean())


def manifest_sha(d):
    """Y01 klasorundeki MANIFEST.csv: cift -> sha256 (kart_no 1)."""
    m = Path(d) / "MANIFEST.csv"
    if not m.exists():
        return None
    out = {}
    for r in csv.DictReader(open(m, encoding="utf-8-sig")):
        if str(r.get("kart_no", "")).strip() in ("1", "01") and r.get("sha256"):
            out[r.get("cift")] = r["sha256"].strip().lower()
    return out


def video_olc(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True, timeout=120)
    j = json.loads(r.stdout or "{}")
    st = j.get("streams") or []
    v = next((s for s in st if s.get("codec_type") == "video"), {})
    return dict(w=v.get("width"), h=v.get("height"), sure=float((j.get("format") or {}).get("duration") or 0),
                ses=any(s.get("codec_type") == "audio" for s in st), bayt=Path(p).stat().st_size)


def plan(a):
    H = json.load(open(a.ham))["ilanlar"]
    ids = ids_oku(a.ids)
    import yd_liste_uret as L
    if sha(a.esleme) != ESLEME_SHA:
        raise SystemExit(f"DUR: VIDEO_ESLEME.csv sha256 onayli dosya degil ({sha(a.esleme)[:12]} != {ESLEME_SHA[:12]})")
    ves = {r["cift"]: r for r in csv.DictReader(open(a.esleme, encoding="utf-8"))}
    eski = L.eski_kapak_oku(Path(a.eski_kapak)) if a.eski_kapak else L.eski_kapak_oku()
    mans = [(Path(d), manifest_sha(d)) for d in a.y01]
    manuel = {x[0] for x in ids[:MANUEL_N]}
    satir = []
    for lid, c, ad_a, ad_b in ids:
        P = dict(listing_id=lid, cift=c, neden=[], manuel=lid in manuel)
        h = H.get(lid)
        if not h:
            P.update(durum="BLOK"); P["neden"].append("canli okuma yok"); satir.append(P); continue
        if h["state"] != "active":
            P["neden"].append(f"state {h['state']} (active degil)")
        g = h["gorseller"]
        if not g or g[0]["rank"] != 1:
            P["neden"].append("rank 1 gorsel yok")
        if len(g) != GALERI_N:
            P["neden"].append(f"galeri {len(g)} gorsel (beklenen {GALERI_N}; elle degisimde eski kapak kalmis olabilir)")
        y01, man = next(((d / f"{c}_Y01.jpg", m) for d, m in mans if (d / f"{c}_Y01.jpg").exists()), (None, None))
        if not y01:
            P["neden"].append("Y01 dosyasi yok")
        else:
            ys = sha(y01)
            if man is None:
                P["neden"].append(f"{y01.parent.name}: MANIFEST.csv yok")
            elif man.get(c) != ys:
                P["neden"].append(f"Y01 sha256 MANIFEST ile ayni degil ({ys[:12]} / {str(man.get(c))[:12]})")
            if Image.open(y01).size != Y01_BOYUT:
                P["neden"].append(f"Y01 boyutu {Image.open(y01).size} (beklenen {Y01_BOYUT})")
            P["neden"] += L.eski_kapak_neden(c, ys, eski)
            alt = L.alt_metin(ad_a, ad_b)
            if not alt or len(alt) > 250 or L.Y.YASAK_ALT.search(alt) or L.RU_YASAK.search(alt) or L.HTML_KAR.search(alt):
                P["neden"].append("yeni alt metin gecersiz")
            P["kapak"] = dict(dosya=str(y01), sha256=ys, alt=alt)
        v = ves.get(c)
        vp = Path(a.video_kok) / v["dosya"] if v else None
        if not v or v.get("durum") != "OK" or str(v.get("listing_id")) != lid:
            P["neden"].append("video esleme satiri yok / OK degil / ilan no farkli")
        elif not vp.exists() or sha(vp) != v["sha256"]:
            P["neden"].append("video dosyasi yok ya da sha256 esleme tablosundan farkli")
        else:
            m = video_olc(vp)
            if (m["w"], m["h"]) != (1440, 1080) or not (5 <= m["sure"] <= 15) or m["bayt"] >= 100 * 1024 * 1024 or m["ses"]:
                P["neden"].append(f"video ozelligi {m} (1440x1080, 5-15 sn, < 100 MB, ses yok beklenir)")
            P["video"] = dict(dosya=str(vp), sha256=v["sha256"], damga=v["damga"], kosu=v["kosu"], olcu=m,
                              eski=[x["id"] for x in h["videolar"]], islem="DEGISTIR" if h["videolar"] else "YUKLE")
        if g and y01 and "kapak" in P:
            r1 = g[0]
            yed = Path(a.yedek) / f"{lid}_{r1['id']}.jpg"
            if not yed.exists() or yed.stat().st_size < 10000:
                P["neden"].append(f"canli rank 1 yedegi yok / kucuk ({yed.name})")
            else:
                try:
                    bm, ort = blok_fark(yed, y01)
                except Exception as e:  # noqa: BLE001 bozuk indirme
                    bm, ort = None, None; P["neden"].append(f"rank 1 yedegi acilamadi: {e}")
                # inceleme tur 2: AYNI yalniz alt metin de ALT_SABLON ise (elle yuklemede alt bos / eski olabilir; degilse ayni Y01 dogru alt ile)
                ayni = P["manuel"] and bm is not None and bm <= KAPAK_AYNI_BLOK and (r1.get("alt") or "") == P["kapak"]["alt"]
                P["kapak"].update(eski_id=r1["id"], eski_alt=r1.get("alt") or "", blok_fark=None if bm is None else round(bm, 3),
                                  ort_fark=None if ort is None else round(ort, 3), islem="AYNI" if ayni else "DEGISTIR",
                                  gorsel_sira=[x["id"] for x in g])
            for x in h["videolar"]:
                yv = Path(a.yedek) / f"{lid}_{x['id']}.mp4"
                if not yv.exists() or yv.stat().st_size < 10000:
                    P["neden"].append(f"eski video yedegi yok / kucuk ({yv.name})")
        P["durum"] = "BLOK" if P["neden"] else "PLAN"
        satir.append(P)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    govde = dict(surum=2, esik_kapak_ayni_blok=KAPAK_AYNI_BLOK, galeri_n=GALERI_N, esleme_sha=ESLEME_SHA, ilanlar=satir)
    b = json.dumps(govde, indent=1, ensure_ascii=False, sort_keys=True).encode()
    (out / "PLAN.json").write_bytes(b)
    damga = hashlib.sha256(b).hexdigest()[:16]
    (out / "PLAN_DAMGA.txt").write_text(damga + "\n")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "cift", "durum", "manuel", "kapak", "blok_fark", "ort_fark", "eski_alt", "yeni_alt", "video", "eski_video", "neden"])
        for P in satir:
            k, v = P.get("kapak") or {}, P.get("video") or {}
            w.writerow([P["listing_id"], P["cift"], P["durum"], P["manuel"], k.get("islem", ""), k.get("blok_fark", ""), k.get("ort_fark", ""),
                        k.get("eski_alt", ""), k.get("alt", ""), v.get("islem", ""), " ".join(v.get("eski") or []), "; ".join(P["neden"])])
    say = {}
    for P in satir:
        k_ = P["durum"] if P["durum"] == "BLOK" else f"{(P.get('kapak') or {}).get('islem')}+{(P.get('video') or {}).get('islem')}"
        say[k_] = say.get(k_, 0) + 1
    mf = [(P["cift"], (P.get("kapak") or {}).get("blok_fark"), (P.get("kapak") or {}).get("eski_alt")) for P in satir if P["manuel"]]
    df = sorted((P["kapak"]["blok_fark"], P["cift"]) for P in satir if not P["manuel"] and (P.get("kapak") or {}).get("blok_fark") is not None)
    md = [f"# YD 1. asama PLAN (damga {damga})", "", f"Durum: {say}",
          f"Istek: en kotu {sum(ILAN_UST for P in satir if P['durum'] == 'PLAN')} (ILAN_UST {ILAN_UST} x PLAN); tipik ~10-14/ilan (tahmin)",
          f"Kapak AYNI: blok esigi {KAPAK_AYNI_BLOK} (TAHMIN) VE canli alt metin = ALT_SABLON, yalniz elle degisen 5 ilanda. "
          f"Elle degisen 5 (cift, blok fark, canli alt): {mf}",
          f"Digerlerinde en kucuk 5 blok fark: {df[:5]} (eski kapak ile Y01; AYNI esiginden buyuk olmali)", "",
          "| ilan | cift | durum | manuel | kapak (blok / ort) | video | neden |", "|---|---|---|---|---|---|---|"]
    md += [f"| {P['listing_id']} | {P['cift']} | {P['durum']} | {'evet' if P['manuel'] else ''} | {(P.get('kapak') or {}).get('islem', '')} "
           f"({(P.get('kapak') or {}).get('blok_fark', '')} / {(P.get('kapak') or {}).get('ort_fark', '')}) | {(P.get('video') or {}).get('islem', '')} | "
           f"{'; '.join(P['neden'])} |" for P in satir]
    (out / "PLAN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"PLAN {damga}: {say}")
    return 0 if all(P["durum"] == "PLAN" for P in satir) else 1


# ------------------------------------------------------------------ uygula
class Yazar:
    """Izinli yazmalar yalniz plandaki ilanlarda: rank 1 gorsel yukleme, planin eski kapak gorselini silme (ekleme durumunda),
    Style varyasyon gorseli, video yukleme, plandaki ESKI video silme."""

    def __init__(self, api, shop, plan_ids, eski_videolar, eski_kapak):
        self.api, self.shop, self.ids, self.eski_v, self.eski_k = api, shop, set(plan_ids), eski_videolar, eski_kapak

    def _ilan(self, lid):
        if str(lid) not in self.ids:
            raise SystemExit(f"YASAK: plan disi ilan {lid}")

    def gorsel(self, lid, p, alt):
        self._ilan(lid)
        with open(p, "rb") as fh:
            return self.api.post_file(f"/shops/{self.shop}/listings/{lid}/images", files={"image": (Path(p).name, fh, "image/jpeg")},
                                      data={"rank": "1", "overwrite": "true", "alt_text": alt}, tekrar=1)

    def gorsel_sil(self, lid, iid):
        self._ilan(lid)
        if str(iid) != self.eski_k.get(str(lid)):
            raise SystemExit(f"YASAK: plandaki eski kapak olmayan gorsel silme {lid}/{iid}")
        return self.api.delete(f"/shops/{self.shop}/listings/{lid}/images/{iid}", ok404=True)

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
    return x.get("state"), [str(i.get("listing_image_id")) for i in g], [str(v.get("video_id")) for v in x.get("videos") or []]


def gorseller(api, lid):
    g = sorted((api.get(f"/listings/{lid}/images") or {}).get("results") or [], key=lambda g: g.get("rank") or 0)
    return [str(i.get("listing_image_id")) for i in g], g


def videolar(api, lid):
    return (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []


def _kapak(api, Y, shop, lid, k, gids):
    """-> yeni rank 1 kimligi. Yer degistirme ya da ekleme + eski kapak silme; boyut kapisi; Style bagi tasima."""
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    hata = None
    try:
        Y.gorsel(lid, k["dosya"], k["alt"])
    except SystemExit as e:
        if str(e.code).startswith("DUR: kota"):
            raise
        hata = str(e.code)[:200]
    except Exception as e:  # noqa: BLE001 zaman asimi: yukleme olmus olabilir
        hata = str(e)[:200]
    son = None
    for _ in range(GORSEL_DENEME):
        ids2, g2 = gorseller(api, lid)
        son = ids2
        if ids2 and ids2[0] != k["eski_id"] and ids2[0] not in gids:
            if len(ids2) == len(gids) and ids2[1:] == gids[1:]:
                break                                                   # yer degistirdi
            if len(ids2) == len(gids) + 1 and ids2[1:] == gids:
                Y.gorsel_sil(lid, k["eski_id"])                         # ekledi: eski kapak 2. sirada -> sil
                for _ in range(GORSEL_DENEME):
                    ids3, g2 = gorseller(api, lid)
                    if ids3 == [ids2[0]] + gids[1:]:
                        ids2 = ids3; break
                    time.sleep(GORSEL_BEKLE)
                else:
                    raise RuntimeError(f"eski kapak silindi ama galeri beklenen degil: {ids3}")
                break
        time.sleep(GORSEL_BEKLE)
    else:
        raise RuntimeError(f"kapak geri okuma beklenen degil (yukleme hatasi {hata}): {son[:3] if son else son}, sayi "
                           f"{len(son or [])}/{len(gids)}")
    yeni = ids2[0]
    y = next((x for x in g2 if str(x.get("listing_image_id")) == yeni), {})
    if (y.get("full_width"), y.get("full_height")) != Y01_BOYUT:
        raise RuntimeError(f"yeni rank 1 boyutu {(y.get('full_width'), y.get('full_height'))} (beklenen {Y01_BOYUT})")
    eski_bag = [v for v in vi if str(v.get("image_id")) == k["eski_id"]]
    if eski_bag:
        liste = [dict(property_id=v["property_id"], value_id=v["value_id"],
                      image_id=int(yeni) if str(v.get("image_id")) == k["eski_id"] else v["image_id"]) for v in vi]
        Y.bag(lid, liste)
        vi2 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        if sorted((v["property_id"], v["value_id"], str(v["image_id"])) for v in vi2) != \
                sorted((v["property_id"], v["value_id"], str(v["image_id"])) for v in liste):
            raise RuntimeError("varyasyon bagi geri okuma farkli")
    return yeni, bool(eski_bag)


def _video(api, Y, lid, Pv):
    eski = set(Pv["eski"])
    hata = None
    try:
        Y.video(lid, Pv["dosya"])
    except SystemExit as e:
        if str(e.code).startswith("DUR: kota"):
            raise
        hata = str(e.code)[:200]
    except Exception as e:  # noqa: BLE001
        hata = str(e)[:200]
    yeni = None
    for _ in range(VIDEO_DENEME):
        vs = videolar(api, lid)
        ys = [v for v in vs if str(v.get("video_id")) not in eski]
        if len(ys) > 1:
            raise RuntimeError(f"ilanda birden fazla yeni video {[v.get('video_id') for v in ys]}; eski SILINMEDI")
        if ys and ys[0].get("video_state") == "active" and ys[0].get("video_url"):
            yeni = str(ys[0]["video_id"]); break
        time.sleep(VIDEO_BEKLE)
    if not yeni:
        raise RuntimeError(f"yeni video active okunmadi (yukleme hatasi {hata}); eski SILINMEDI")
    for e in Pv["eski"]:
        Y.video_sil(lid, e)
    for _ in range(GORSEL_DENEME):
        if [str(v.get("video_id")) for v in videolar(api, lid)] == [yeni]:
            return yeni
        time.sleep(GORSEL_BEKLE)
    raise RuntimeError("eski video silindikten sonra ilanda yalniz yeni video okunmadi")


def uygula(a, api, shop):
    from etsy_common import KOTA_SINIRI
    b = Path(a.plan).read_bytes()
    if hashlib.sha256(b).hexdigest()[:16] != a.plan_damga or a.confirm != ONAY:
        raise SystemExit("DUR: plan_damga / confirm uyusmuyor; yazma yok")
    PL = json.loads(b)
    sec = [P for P in PL["ilanlar"] if P["durum"] == "PLAN" and (not a.sadece or P["listing_id"] in a.sadece.split(","))]
    if a.sadece and len(sec) != len(a.sadece.split(",")):
        raise SystemExit(f"DUR: --sadece ilanlarindan PLAN durumunda olmayan var ({a.sadece})")
    for P in sec:
        if P["kapak"]["islem"] == "DEGISTIR" and sha(P["kapak"]["dosya"]) != P["kapak"]["sha256"]:
            raise SystemExit(f"DUR: {P['cift']} Y01 sha256 plandan farkli")
        if sha(P["video"]["dosya"]) != P["video"]["sha256"]:
            raise SystemExit(f"DUR: {P['cift']} video sha256 plandan farkli")
    Y = Yazar(api, shop, [P["listing_id"] for P in sec], {P["listing_id"]: set(P["video"]["eski"]) for P in sec},
              {P["listing_id"]: P["kapak"]["eski_id"] for P in sec})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    S = json.load(open(out / "SONUC.json")) if (out / "SONUC.json").exists() else {}

    def kaydet():
        with open(out / "SONUC.json", "w") as fh:
            json.dump(S, fh, indent=1, ensure_ascii=False)
    def pay_yok():
        return api.remaining is not None and int(api.remaining) < KOTA_SINIRI + ILAN_UST
    try:
        api.get(f"/shops/{shop}")              # inceleme tur 2: kalan kota ilk ilandan ONCE okunur (remaining None iken pay kapisi bos gecerdi)
    except SystemExit as e:
        if "kota" in str(e.code):
            print(f"::warning::KOTA: {e.code}"); return 4
        raise
    t0 = time.time()
    for i, P in enumerate(sec, 1):
        lid, c, k = P["listing_id"], P["cift"], P["kapak"]
        if S.get(lid, {}).get("durum") == "PASS":
            continue
        if a.bitis and time.time() > a.bitis:
            print(f"::warning::SURE: kilit butcesi doldu; {c} ve sonrasi baslamadi (onceki kosu ile surdur)")
            return 5
        try:
            api.kota_kapisi(f"ilan {lid}")
        except SystemExit as e:
            print(f"::warning::KOTA: {e.code}"); return 4
        if api.remaining is None or pay_yok():
            print(f"::warning::KOTA: kalan {api.remaining} < {KOTA_SINIRI} + {ILAN_UST}; {c} ve sonrasi baslamadi (kota acilinca surdur)")
            return 4
        R = S[lid] = dict(cift=c, adim=[], durum="BASLADI", istek_bas=api.calls)
        st, gids, vids = canli(api, lid)
        if pay_yok():                          # canli okumadan sonra, ilk yazmadan once tekrar
            S.pop(lid, None); kaydet()
            print(f"::warning::KOTA: kalan {api.remaining}; {c} yazilmadan birakildi"); return 4
        if st != "active" or gids != k["gorsel_sira"] or sorted(vids) != sorted(P["video"]["eski"]):
            R.update(durum="ATLA", neden=f"canli plandan farkli (state {st}, gorsel {len(gids)}, video {vids})"); kaydet()
            print(f"::error::{c} ATLA: canli plandan farkli; DUR (once ilani incele)")
            return 1
        try:
            r1 = gids[0]
            if k["islem"] == "DEGISTIR":
                r1, bag = _kapak(api, Y, shop, lid, k, gids)
                R["adim"].append(("kapak", r1, "bag" if bag else ""))
            yv = _video(api, Y, lid, P["video"])
            R["adim"].append(("video", yv))
            st, gids3, vids3 = canli(api, lid)
            K = {"state active": st == "active", "rank 1 beklenen": bool(gids3) and gids3[0] == r1,
                 "gorsel sayisi plan": len(gids3) == len(gids), "yalniz yeni video": vids3 == [yv]}
            R.update(kontrol=K, durum="PASS" if all(K.values()) else "FAIL")
        except BaseException as e:   # noqa: BLE001
            R.update(durum="FAIL", hata=f"{type(e).__name__}: {e}"[:500])
        R.update(istek=api.calls - R.pop("istek_bas"), kota=api.remaining)
        kaydet()
        g_ = time.time() - t0
        print(f"[{i}/{len(sec)}] {c} {R['durum']} | istek {R['istek']} | kota {api.remaining} | gecen {g_:.0f} sn | "
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
    ap.add_argument("--sadece", default=""); ap.add_argument("--bitis", type=float, default=0.0, help="epoch sn: sonrasinda yeni ilana baslanmaz")
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
        def yasak(*x, **y):
            raise SystemExit("YASAK: salt okuma")
        api.post = api.put = api.patch = api.delete = api.post_json = api.put_json = api.post_file = yasak
        sys.exit(oku(api, ids_oku(a.ids), a.out))
    sys.exit(uygula(a, api, os.environ["ETSY_SHOP_ID"]))


if __name__ == "__main__":
    main()
