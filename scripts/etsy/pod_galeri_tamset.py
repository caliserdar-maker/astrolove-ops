#!/usr/bin/env python3
"""GOREV 0008 (Serdar onayi 26 Eyl 2026): onayli TAM SET galerilerini POD ilanlarina yukler.

Kaynak: Drive A1_77/<CIFT>/TAM_SET (13 foto + SET.json; video SET.json['video']['yol']).
Sira ve alt metin: canli Cancer-Libra referans ilani (4570143815); foto n -> referans CL n karesinin
alt metni, burc adlari ciftinkiyle degistirilir. Video Etsy'de her zaman 2. sirada (Etsy sabit).
Renk varyasyon gorselleri: SET.json renk_gorselleri (renk adi -> dosya) ile yeni gorsel id'lerine baglanir.

Modlar:
  oku    : SALT OKUMA. Referans + hedef ilanlar (state, foto/video sayisi, varyasyon baglantisi) ve cagri tahmini.
  yukle  : ETSY'YE YAZAR. --ciftler ile verilen ciftler (pilot: 1 cift). Ilan basina:
           once yukle (sinir izin verdikce), sonra eski sil; varyasyon baglantisi; video (eski silinir, yenisi yuklenir);
           geri okuma: foto 13, sira ve alt metin, video 1, state DEGISMEDI, varyasyonlar yeni gorsellerde.
           Geri okuma tutmazsa DUR. updateListing (PATCH) cagrisi YOK; state'e dokunulmaz.
Butce: --butce (Etsy cagrisi, bu kosu). Ilan baslamadan once tahmini cagri butceyi asacaksa DUR, kalanlar raporlanir.
Cikti: out/GALERI_TAMSET.json (+ .md). Sirlar loga yazilmaz.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import hashlib
import io
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

REF_ID = "4570143815"
REF_CIFT = ("Cancer", "Libra")
A77 = "gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77"
IMG_LIMIT = 20                 # Etsy ilan basina gorsel siniri (referans 14 foto tutuyor; oku modunda dogrulanir)
KOTA_TABAN = 300
OKUMA_TEKRAR, OKUMA_BEKLE = 8, 4
OUT = Path("out")
ESIK = 0.001                   # icerik farki: 256px gri ortalama mutlak fark (0-1). Etsy ayni dosyayi tekillestirip eski id'yi
                               # tutabiliyor (ARIES_LEO pilotu); sira bu yuzden id'ye degil icerige gore dogrulanir.
BURC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
        "Aquarius", "Pisces"]


def rc(*a):
    return subprocess.run(["rclone", *a], check=True, capture_output=True, text=True).stdout


def cift_anahtar(metin):
    """'Aries + Leo' / 'ARIES_LEO' -> 'ARIES_LEO' (alfabetik, A1_77 klasor adi)."""
    ad = [b.upper() for b in re.findall(r"[A-Za-z]+", metin or "") if b.capitalize() in BURC]
    return "_".join(sorted(ad)) if len(ad) == 2 else ("_".join(ad * 2) if len(ad) == 1 else "")


def burclar(anahtar):
    a, b = anahtar.split("_")
    return a.capitalize(), b.capitalize()


def alt_uyarla(metin, a, b):
    """Referans alt metnindeki Cancer/Libra -> cift burclari (sira korunur)."""
    s = re.sub(r"\bCancer\b", "\x00A", metin or "")
    s = re.sub(r"\bLibra\b", "\x00B", s)
    return s.replace("\x00A", a).replace("\x00B", b)


def kararli(fn, kosul=None):
    onceki = None
    for _ in range(OKUMA_TEKRAR):
        simdi = fn()
        if onceki is not None and simdi == onceki and (kosul is None or kosul(simdi)):
            return simdi
        onceki = simdi
        time.sleep(OKUMA_BEKLE)
    return onceki


def galeri(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return sorted(r.get("results") or [], key=lambda x: x.get("rank") or 0)


def videolar(api, lid):
    return (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []


def var_img(api, shop, lid):
    return (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []


_CDN = {}


def cdn(url):
    """Etsy CDN gorseli (API cagrisi DEGIL); kosu icinde url basina bir kez indirilir."""
    if url not in _CDN:
        if len(_CDN) > 60:
            _CDN.clear()
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        _CDN[url] = r.content
    return _CDN[url]


def gri(kaynak, boyut=None):
    im = Image.open(io.BytesIO(kaynak) if isinstance(kaynak, bytes) else kaynak).convert("L")
    return np.asarray(im.resize(boyut, Image.BILINEAR) if boyut else im, dtype=float)


def fark(url, yol):
    """Etsy CDN gorseli ile set dosyasi arasindaki tum-goruntu icerik farki; hata -> None.
    NOT: cift karisikligini YAKALAYAMAZ (yalniz burc yazisi farkli iki kart ~0.00003, Codex RAPOR_0004);
    cift icin cift_olc kullanilir."""
    try:
        g = [gri(k, (256, 256)) for k in (cdn(url), yol)]
        return round(float(np.abs(g[0] - g[1]).mean() / 255), 4)
    except Exception as e:  # noqa: BLE001
        log(f"      fark hata: {type(e).__name__}")
        return None


def icerik(g, foto, sadece=None):
    """rank -> fark (galerideki gorsel vs ayni siradaki set dosyasi)."""
    yol = {n: p for n, p, _ in foto}
    return {x.get("rank"): fark(x.get("url_fullxfull"), yol[x.get("rank")]) for x in g
            if x.get("rank") in yol and (sadece is None or x.get("rank") in sadece)}


def esit(v):
    return v is not None and v <= ESIK


CIFT_PIKSEL = 25   # beklenen vs tuzak (baska cift, ayni kart) piksel farki esigi (0-255) -> cifte ozel bolge maskesi
CIFT_MIN = 200     # maske bundan az pikselse kart ortak (cifte ozel degil)
CIFT_ORAN = 3.0    # maskede: canli-tuzak farki >= 3 x canli-beklenen farki (en az 1 gri seviye) olmali


def cift_olc(url, yol, tuzak):
    """Cifte ozel bolgede (burc adi/sembol: beklenen ile tuzak dosyanin farkli oldugu pikseller) bolge bazli fark.
    Canli gorsel beklenen dosyaya, tuzak ciftin dosyasindan belirgin daha yakin olmali."""
    try:
        canli = gri(cdn(url))
        H, W = canli.shape
        e, t = gri(yol, (W, H)), gri(tuzak, (W, H))
    except Exception as ex:  # noqa: BLE001
        return {"hata": type(ex).__name__, "ok": False}
    m = np.abs(e - t) > CIFT_PIKSEL
    n = int(m.sum())
    if n < CIFT_MIN:
        return {"ortak": True, "maske": n, "ok": True}
    ys, xs = np.where(m)
    de, dt = float(np.abs(canli - e)[m].mean()), float(np.abs(canli - t)[m].mean())
    return {"maske": n, "bolge": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "d_beklenen": round(de, 2), "d_tuzak": round(dt, 2), "ok": dt >= CIFT_ORAN * max(de, 1.0)}


def cift_denetle(g, foto, tfoto):
    """rank -> cift_olc (tfoto: tuzak ciftin ayni sira dosyalari)."""
    yol, tyol = {n: p for n, p, _ in foto}, {n: p for n, p, _ in tfoto}
    return {x.get("rank"): cift_olc(x.get("url_fullxfull"), yol[x.get("rank")], tyol[x.get("rank")])
            for x in g if x.get("rank") in yol and x.get("rank") in tyol}


def tuzak_sec(c, setli):
    """Iki burcu da c'den farkli ilk cift (yoksa herhangi baska cift)."""
    b = set(c.split("_"))
    return next((x for x in setli if x != c and not b & set(x.split("_"))), next(x for x in setli if x != c))


def set_indir(setler, c, video=True):
    d = Path(setler) / c / "TAM_SET"
    SET = json.loads((d / "SET.json").read_text())
    try:                                                 # set dosyalari + onayli video (Drive) bu ilan icin indirilir
        rc("copy", f"{A77}/{c}/TAM_SET", str(d), "--include", "[01][0-9]_*.jpg")
        if video and (SET.get("video") or {}).get("yol"):
            rc("copyto", SET["video"]["yol"], str(d / "VIDEO.mp4"))
    except subprocess.CalledProcessError as e:
        log(f"{c}: Drive indirme hatasi {e.stderr[-200:] if e.stderr else e}")
    return SET, d, [(g["sira"], d / g["dosya"], g["cl_karsiligi"]) for g in SET["galeri"]]


def onar(api, shop, a, c, lid, r, ref_alt, tfoto):
    """Galerisi 13 foto olup sira/alt/varyasyon/cift tutmayan ilan: her sira icerik (tum goruntu) ve cift (bolge)
    olcutuyle, alt metinle denetlenir; tutmayan siralar yeniden yuklenir (eski o siradaki gorsel silinir),
    renk varyasyonlari siraya gore yeniden baglanir, geri okunur."""
    SET, d, foto = set_indir(a.setler, c)
    A_, B_ = burclar(c)
    alt = {n: alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250] for n, _, cl in foto}
    g = galeri(api, lid)
    fk = icerik(g, foto)
    ck = cift_denetle(g, foto, tfoto)
    altk = {x.get("rank"): (x.get("alt_text") or "") == alt.get(x.get("rank")) for x in g}
    farkli = sorted(n for n in range(1, 14)
                    if not esit(fk.get(n)) or not (ck.get(n) or {}).get("ok") or not altk.get(n))
    log(f"{c} onar: icerik farki {fk} | cift {json.dumps(ck)} | alt {altk} | yeniden yuklenecek sira {farkli}")
    r["icerik_fark_once"], r["cift_once"] = fk, ck
    r["onar_sira"] = farkli
    if farkli:
        eski = {x.get("rank"): x.get("listing_image_id") for x in g}
        yol = {n: p for n, p, _ in foto}
        for n in farkli:
            with open(yol[n], "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (yol[n].name, fh, "image/jpeg")},
                              data={"rank": str(n), "alt_text": alt[n]})
            if eski.get(n):
                api.delete(f"/shops/{shop}/listings/{lid}/images/{eski[n]}")
    g2 = kararli(lambda: galeri(api, lid), lambda x: len(x) == 13)
    rid = {x.get("rank"): x.get("listing_image_id") for x in g2 or []}
    renk_dosya = SET.get("renk_gorselleri") or {}
    dosya_sira = {x["dosya"]: x["sira"] for x in SET["galeri"]}
    vimg = var_img(api, shop, lid)
    vi = [{"property_id": v.get("property_id"), "value_id": v.get("value_id"),
           "image_id": rid.get(dosya_sira.get(renk_dosya.get(v.get("value")))) } for v in vimg]
    if farkli and all(x["image_id"] for x in vi):
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        vimg = var_img(api, shop, lid)
    fk2 = icerik(g2 or [], foto)
    ck2 = cift_denetle(g2 or [], foto, tfoto)
    kontrol = dict(r.get("kontrol") or {})
    kontrol.update(foto_13=len(g2 or []) == 13,
                   sira=sorted(rid) == list(range(1, 14)) and len(fk2) == 13 and all(esit(v) for v in fk2.values()),
                   cift=len(ck2) == 13 and all(v.get("ok") for v in ck2.values()),
                   alt_metin=all((x.get("alt_text") or "") == alt.get(x.get("rank")) for x in g2 or []),
                   varyasyon=all(v.get("image_id") == rid.get(dosya_sira.get(renk_dosya.get(v.get("value"))))
                                 for v in vimg))
    r.update(kontrol=kontrol, icerik_fark=fk2, cift=ck2, sonuc="PASS" if all(kontrol.values()) else "FAIL")
    r.pop("sira_gercek", None); r.pop("sira_beklenen", None)
    log(f"{c} onar {r['sonuc']} | {json.dumps(kontrol)} | fark {fk2} | cift {json.dumps(ck2)}")
    return r["sonuc"] == "PASS"


def kota(api):
    try:
        return int(api.remaining) if api.remaining is not None else None
    except ValueError:
        return None


def toplu_oku(api, ids):
    L = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,videos"}) or {}
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    return L


def tahmin(n_eski, video_var):
    """Ilan basina Etsy cagrisi: varyasyon oku 1 + 13 yukleme + eski silme + varyasyon yaz 1 + video (sil+yukle)
    + geri okuma (galeri/varyasyon/video/ilan, kararlilik icin ~2x)."""
    return 1 + 13 + n_eski + 1 + (1 if video_var else 0) + 1 + 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["oku", "denetle", "yukle"], required=True)
    ap.add_argument("--metin", required=True, help="METIN_78.csv (ilan_id, cift)")
    ap.add_argument("--setler", required=True, help="yerel dizin: <CIFT>/SET.json (oku) ya da tam set (yukle)")
    ap.add_argument("--ciftler", default="", help="yukle: virgullu CIFT listesi (bos = seti olan hepsi, referans haric)")
    ap.add_argument("--butce", type=int, default=1300)
    ap.add_argument("--durum", default="", help="onceki GALERI_TAMSET.json (PASS olanlar atlanir)")
    a = ap.parse_args()
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)

    satir = list(csv.DictReader(open(a.metin, encoding="utf-8")))
    ilan = {cift_anahtar(r.get("cift")): str(r["ilan_id"]) for r in satir if cift_anahtar(r.get("cift"))}
    setli = sorted(p.name for p in Path(a.setler).iterdir() if (p / "TAM_SET" / "SET.json").exists())
    ref_anahtar = cift_anahtar(" ".join(REF_CIFT))
    hedef = [c for c in setli if c in ilan and ilan[c] != REF_ID]
    eslesmeyen = [c for c in setli if c not in ilan]
    onceki = json.loads(Path(a.durum).read_text()) if a.durum and Path(a.durum).exists() else {}
    bitti = {c for c, r in (onceki.get("ilan") or {}).items() if r.get("sonuc") == "PASS"}

    L = toplu_oku(api, [REF_ID] + [ilan[c] for c in hedef])
    R = L.get(REF_ID) or {}
    ref_img = sorted(R.get("images") or [], key=lambda x: x.get("rank") or 0)
    ref_alt = {i + 1: (im.get("alt_text") or "") for i, im in enumerate(ref_img)}
    ref_vimg = var_img(api, shop, REF_ID)
    ref_id_rank = {im.get("listing_image_id"): i + 1 for i, im in enumerate(ref_img)}
    rapor = {"mod": a.mod, "referans": {"ilan": REF_ID, "state": R.get("state"), "foto": len(ref_img),
                                        "video": len(R.get("videos") or []),
                                        "varyasyon": [{"renk": v.get("value"), "ref_sira": ref_id_rank.get(v.get("image_id"))}
                                                      for v in ref_vimg]},
             "setli": len(setli), "hedef": len(hedef), "referans_cift_seti": ref_anahtar in setli,
             "eslesmeyen": eslesmeyen, "ilan": dict(onceki.get("ilan") or {}), "kota_bas": kota(api)}
    if len(ref_img) < 13:
        raise SystemExit(f"HATA: referans {len(ref_img)} foto; 13 fotoluk set Etsy sinirina sigmayabilir - DUR")

    if a.mod == "oku":
        top = 0
        for c in hedef:
            X = L.get(ilan[c]) or {}
            n, v = len(X.get("images") or []), len(X.get("videos") or [])
            t = tahmin(n, v > 0); top += t
            rapor["ilan"][c] = {"ilan_id": ilan[c], "state": X.get("state"), "foto": n, "video": v,
                                "video_ad": [x.get("name") for x in X.get("videos") or []], "tahmini_cagri": t,
                                "galeri": [[x.get("listing_image_id"), x.get("rank")]
                                           for x in sorted(X.get("images") or [], key=lambda x: x.get("rank") or 0)]}
        rapor["tahmini_toplam_cagri"] = top
        rapor["kota_son"], rapor["cagri"] = kota(api), api.calls
        (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
        log(json.dumps({k2: v2 for k2, v2 in rapor.items() if k2 != "ilan"}, ensure_ascii=False, indent=1))
        return

    def tuzak_foto(c):
        return set_indir(a.setler, tuzak_sec(c, setli), video=False)[2]

    if a.mod == "denetle":                               # SALT OKUMA: galeri + varyasyon okunur, CDN ile karsilastirilir
        rapor["denetle"] = {}
        for c in [x for x in a.ciftler.split(",") if x]:
            lid, t = ilan[c], tuzak_sec(c, setli)
            SET, d, foto = set_indir(a.setler, c, video=False)
            tfoto = set_indir(a.setler, t, video=False)[2]
            yol, tyol = {n: p for n, p, _ in foto}, {n: p for n, p, _ in tfoto}
            A_, B_ = burclar(c)
            alt = {n: alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250] for n, _, cl in foto}
            g = galeri(api, lid)
            fk, ck = icerik(g, foto), cift_denetle(g, foto, tfoto)
            satir = []
            for x in g:
                n = x.get("rank")
                s_ = {"sira": n, "id": x.get("listing_image_id"), "url": x.get("url_fullxfull"),
                      "beklenen": f"{A77}/{c}/TAM_SET/{yol[n].name}" if n in yol else None,
                      "beklenen_md5": hashlib.md5(yol[n].read_bytes()).hexdigest() if n in yol else None,
                      "tuzak": f"{A77}/{t}/TAM_SET/{tyol[n].name}" if n in tyol else None,
                      "tuzak_md5": hashlib.md5(tyol[n].read_bytes()).hexdigest() if n in tyol else None,
                      "fark": fk.get(n), "cift": ck.get(n), "alt_ok": (x.get("alt_text") or "") == alt.get(n)}
                satir.append(s_)
                log(f"{c} #{n} id {s_['id']} | {s_['beklenen']} | {s_['url']} | fark {s_['fark']} | cift {json.dumps(s_['cift'])}"
                    f" | alt {s_['alt_ok']}")
            dosya_sira = {x["dosya"]: x["sira"] for x in SET["galeri"]}
            rid = {x.get("rank"): x.get("listing_image_id") for x in g}
            renk = {v.get("value"): {"sira": dosya_sira.get((SET.get("renk_gorselleri") or {}).get(v.get("value"))),
                                     "image_id": v.get("image_id")} for v in var_img(api, shop, lid)}
            for v in renk.values():
                v["dogru"] = v["image_id"] == rid.get(v["sira"]) and bool((ck.get(v["sira"]) or {}).get("ok"))
            ozet = {"tuzak": t, "foto": len(g), "fark_esik_ustu": [n for n in range(1, 14) if not esit(fk.get(n))],
                    "cift_tutmayan": [n for n in range(1, 14) if not (ck.get(n) or {}).get("ok")],
                    "cifte_ozel_sira": [n for n, v in ck.items() if not v.get("ortak")],
                    "ayni_dosya_tuzakla": [x["sira"] for x in satir if x["beklenen_md5"] and x["beklenen_md5"] == x["tuzak_md5"]],
                    "alt_tutmayan": [x["sira"] for x in satir if not x["alt_ok"]],
                    "renk_tutmayan": [k2 for k2, v in renk.items() if not v["dogru"]]}
            rapor["denetle"][c] = {"ozet": ozet, "renk": renk, "foto": satir}
            log(f"{c} OZET {json.dumps(ozet)}")
        rapor["kota_son"], rapor["cagri"] = kota(api), api.calls
        (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
        return

    # ------------------------------------------------------------------ YUKLE
    secim = [x for x in a.ciftler.split(",") if x] or hedef
    harcanan0 = api.calls
    for c, x in list((onceki.get("ilan") or {}).items()):   # yalniz 'sira' tutmayan onceki ilanlar: icerik + onarim
        k = x.get("kontrol") or {}
        fk0 = x.get("icerik_fark") or {}
        yeniden = x.get("sonuc") == "PASS" and (len(fk0) < 13 or not all(esit(v) for v in fk0.values())
                                                 or "cift" not in k)          # cift olcutu yokken PASS olanlar
        onarilir = x.get("sonuc") == "FAIL" and all(k.get(n2) for n2 in ("foto_13", "video_1", "state_degismedi"))
        if c in hedef and (yeniden or onarilir):
            bitti.discard(c)
            if not onar(api, shop, a, c, ilan[c], rapor["ilan"][c], ref_alt, tuzak_foto(c)):
                (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
                raise SystemExit(f"DUR: {c} onarim tutmadi")
            bitti.add(c)
            (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
            try:
                rc("copy", str(OUT / "GALERI_TAMSET.json"), f"{A77}/_galeri")
            except subprocess.CalledProcessError:
                log("durum Drive'a yazilamadi")
    secim = [c for c in secim if c in hedef and c not in bitti]
    log(f"yuklenecek {len(secim)} ilan (seti olan {len(setli)}, onceden PASS {len(bitti)}) | kota {kota(api)}")
    for sira, c in enumerate(secim, 1):
        lid = ilan[c]; X = L.get(lid) or {}
        eski = sorted(X.get("images") or [], key=lambda x: x.get("rank") or 0)
        eski_vid = X.get("videos") or []
        gerek = tahmin(len(eski), bool(eski_vid))
        if api.calls - harcanan0 + gerek > a.butce:
            rapor["butce_bitti"] = {"kalan": secim[sira - 1:], "harcanan": api.calls - harcanan0}
            log(f"DUR: butce {a.butce} (harcanan {api.calls - harcanan0}, bu ilan ~{gerek})"); break
        q = kota(api)
        if q is not None and q < KOTA_TABAN + gerek:
            rapor["butce_bitti"] = {"kalan": secim[sira - 1:], "sebep": f"kota {q}"}
            log(f"DUR: kota {q}"); break
        SET, d, foto = set_indir(a.setler, c)
        A_, B_ = burclar(c)
        eksik = [str(p) for _, p, _ in foto if not p.exists()]
        vpath = d / "VIDEO.mp4"
        r = {"ilan_id": lid, "state_once": X.get("state"), "foto_once": len(eski), "video_once": len(eski_vid)}
        rapor["ilan"][c] = r
        if eksik or len(foto) != 13 or not vpath.exists():
            r.update(sonuc="FAIL", hata=f"set eksik: {eksik[:3]} foto {len(foto)} video {vpath.exists()}")
            log(f"[{sira}/{len(secim)}] {c} set eksik - DUR"); break
        t0 = time.time(); c0 = api.calls
        vimg_once = var_img(api, shop, lid)
        eski_ids = [im.get("listing_image_id") for im in eski]
        bagli = {v.get("image_id") for v in vimg_once}
        yeni = {}                                            # sira -> image_id
        mevcut = len(eski)
        silinecek = [i for i in eski_ids if i not in bagli] + [i for i in eski_ids if i in bagli]
        for srn, p, cl in foto:                              # once yukle; sinir doluysa once bagsiz eski sil
            while mevcut >= IMG_LIMIT and silinecek and silinecek[0] not in bagli:
                api.delete(f"/shops/{shop}/listings/{lid}/images/{silinecek.pop(0)}"); mevcut -= 1
            if mevcut >= IMG_LIMIT:
                r.update(sonuc="FAIL", hata="gorsel siniri: bagli eski gorseller yer birakmiyor"); break
            with open(p, "rb") as fh:
                y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")},
                                  data={"rank": str(srn), "alt_text": alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250]})
            yeni[srn] = y.get("listing_image_id"); mevcut += 1
        if r.get("sonuc") == "FAIL":
            log(f"[{sira}/{len(secim)}] {c} {r['hata']} - DUR"); break
        # varyasyon baglantisi: renk adi -> SET renk gorseli -> yeni id
        renk_dosya = SET.get("renk_gorselleri") or {}
        dosya_sira = {g["dosya"]: g["sira"] for g in SET["galeri"]}
        vi, eksik_renk = [], []
        for v in vimg_once:
            dosya = renk_dosya.get(v.get("value"))
            if not dosya or dosya_sira.get(dosya) not in yeni:
                eksik_renk.append(v.get("value")); continue
            vi.append({"property_id": v.get("property_id"), "value_id": v.get("value_id"), "image_id": yeni[dosya_sira[dosya]]})
        if eksik_renk:
            r.update(sonuc="FAIL", hata=f"varyasyon rengi eslesmedi: {eksik_renk} (eski gorseller silinmedi)")
            log(f"[{sira}/{len(secim)}] {c} {r['hata']} - DUR"); break
        if vi:
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        for i in silinecek:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
        for v in eski_vid:
            api.delete(f"/shops/{shop}/listings/{lid}/videos/{v.get('video_id')}")
        with open(vpath, "rb") as fh:
            rv = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (f"{c}.mp4", fh, "video/mp4")},
                               data={"name": f"{c}.mp4"})
        # geri okuma
        g2 = kararli(lambda: galeri(api, lid), lambda g: len(g) == 13) or []
        rid = {x.get("rank"): x.get("listing_image_id") for x in g2}
        idfarkli = [n for n in sorted(yeni) if rid.get(n) != yeni[n]]     # Etsy tekillestirmesi: icerikle dogrula
        fk = icerik(g2, foto)                                             # 13 foto olculur, rapora yazilir
        tfoto = tuzak_foto(c)
        ck = cift_denetle(g2, foto, tfoto)
        v2 = kararli(lambda: [x.get("video_id") for x in videolar(api, lid)], lambda v: len(v) == 1)
        vm2 = {x.get("value"): x.get("image_id") for x in var_img(api, shop, lid)}
        L2 = api.get(f"/listings/{lid}") or {}
        kontrol = {
            "foto_13": len(g2 or []) == 13,
            "sira": sorted(rid) == list(range(1, 14)) and all(esit(fk.get(n)) for n in idfarkli),
            "cift": len(ck) == 13 and all(v.get("ok") for v in ck.values()),
            "alt_metin": all((x.get("alt_text") or "") == alt_uyarla(ref_alt.get(foto[x.get("rank") - 1][2], ""), A_, B_)[:250]
                             for x in g2),
            "video_1": len(v2 or []) == 1,
            "varyasyon": all(vm2.get(v.get("value")) == rid.get(dosya_sira[renk_dosya[v.get("value")]]) for v in vimg_once),
            "state_degismedi": L2.get("state") == X.get("state"),
        }
        r.update(icerik_fark=fk, id_farkli=idfarkli, cift=ck)
        if not all(kontrol.values()) and all(kontrol[n2] for n2 in ("foto_13", "video_1", "state_degismedi")):
            log(f"{c}: tutmayan kontrol {[k2 for k2, v in kontrol.items() if not v]} -> onarim (yeniden yukleme)")
            r["kontrol"] = kontrol
            onar(api, shop, a, c, lid, r, ref_alt, tfoto)
            kontrol = r["kontrol"]
        r.update(sonuc="PASS" if all(kontrol.values()) else "FAIL", kontrol=kontrol, state_sonra=L2.get("state"),
                 yeni_video=rv.get("video_id"), cagri=api.calls - c0, sn=round(time.time() - t0, 1))
        log(f"[{sira}/{len(secim)}] {c} {r['sonuc']} cagri {r['cagri']} | toplam {api.calls - harcanan0}/{a.butce} "
            f"| kota {kota(api)} | {json.dumps(kontrol)}")
        (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
        try:
            rc("copy", str(OUT / "GALERI_TAMSET.json"), f"{A77}/_galeri")   # ilan basi durum (devam icin)
        except subprocess.CalledProcessError:
            log("durum Drive'a yazilamadi")
        if r["sonuc"] != "PASS":
            log("DUR: geri okuma tutmadi"); break
    rapor["kota_son"], rapor["cagri"] = kota(api), api.calls
    rapor["ozet"] = {"pass": sorted(c for c, x in rapor["ilan"].items() if x.get("sonuc") == "PASS"),
                     "fail": {c: x.get("hata") or x.get("kontrol") for c, x in rapor["ilan"].items() if x.get("sonuc") == "FAIL"}}
    (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
    log(json.dumps({"ozet": rapor["ozet"], "butce_bitti": rapor.get("butce_bitti"), "cagri": api.calls,
                    "kota_son": rapor["kota_son"]}, ensure_ascii=False, indent=1))
    if rapor["ozet"]["fail"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
