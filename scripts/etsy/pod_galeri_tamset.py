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


def kur(api, shop, c, lid, foto, alt, g, k):
    """GUVENLI GALERI KURULUMU (GOREV 0015). Rank'a EKLEME yapilmaz (Etsy'nin dolu siraya ekleme davranisi
    5-12 sira kaymasina yol aciyordu); yalniz SONA eklenir:
      1) dogru on-ek (ilk k sira) korunur, gerisi silinir; k == 0 ise bir eski gorsel sona kadar tutulur
         (aktif ilan hicbir an 0 fotoda kalmaz),
      2) eksik dosyalar k+1..13 SIRAYLA sona eklenir (rank = mevcut sayi + 1; 20 siniri asilmaz),
      3) tutulan eski silinir -> yeni fotolar 1..13'e kayar.
    Her fazdan sonra getListingImages okunur; beklenmeyen sayi -> SystemExit (ilan FAIL)."""
    yol = {n: p for n, p, _ in foto}
    sil = [x.get("listing_image_id") for x in g[k:]]
    tut = sil.pop(0) if k == 0 and sil else None
    for i in sil:
        api.delete(f"/shops/{shop}/listings/{lid}/images/{i}")
    g1 = galeri(api, lid)
    beklenen = k + (1 if tut else 0)
    log(f"{c} kur faz1 sil {len(sil)} | galeri {len(g1)} (beklenen {beklenen}) sira {[x.get('rank') for x in g1]}")
    if len(g1) != beklenen:
        raise SystemExit(f"HATA: {c} silme sonrasi galeri {len(g1)} != {beklenen}")
    if len(g1) + (13 - k) > IMG_LIMIT:
        raise SystemExit(f"HATA: {c} 20 foto siniri asilir ({len(g1)} + {13 - k})")
    for n in range(k + 1, 14):
        with open(yol[n], "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (yol[n].name, fh, "image/jpeg")},
                          data={"rank": str(len(g1) + n - k), "alt_text": alt[n]})
    g2 = galeri(api, lid)
    log(f"{c} kur faz2 eklendi {13 - k} | galeri {len(g2)} sira {[x.get('rank') for x in g2]}")
    if len(g2) != len(g1) + 13 - k:
        raise SystemExit(f"HATA: {c} ekleme sonrasi galeri {len(g2)} != {len(g1) + 13 - k}")
    if tut:
        api.delete(f"/shops/{shop}/listings/{lid}/images/{tut}")
    g3 = sirali(api, lid)
    log(f"{c} kur faz3 | galeri {len(g3)} sira {[x.get('rank') for x in g3]}")
    if [x.get("rank") for x in g3] != list(range(1, 14)):
        raise SystemExit(f"HATA: {c} galeri sirasi 1..13'e oturmadi: {[x.get('rank') for x in g3]}")
    return g3


def sirali(api, lid):
    """Silmeden sonra Etsy sirayi gecikmeli sikistiriyor (AQUARIUS_CAPRICORN pilotu: 1,3..14). 13 foto ve sira
    1..13 olana kadar (en fazla OKUMA_TEKRAR) okunur; varyasyonlar ancak ondan sonra siraya gore baglanir."""
    return kararli(lambda: galeri(api, lid),
                   lambda x: len(x) == 13 and [y.get("rank") for y in x] == list(range(1, 14))) or []


def yeniden_kodla(yol, hedef):
    """Ayni gorsel, farkli bayt (JPEG q95 yeniden kodlama; Etsy tekillestirmesini asmak icin). Fark > ESIK ise None."""
    Image.open(yol).convert("RGB").save(hedef, "JPEG", quality=95)
    f = float(np.abs(gri(yol, (256, 256)) - gri(hedef, (256, 256))).mean() / 255)
    return hedef if f <= ESIK else None


def alt_yenile(api, shop, c, lid, n, yol, alt, eski_id):
    """Alt metni tutmayan sira: ayni gorsel yeniden kodlanip dogru alt metinle AYNI siraya yeni foto olarak yuklenir,
    eski kayit silinir (GOREV 0015 md. 3)."""
    h = yeniden_kodla(yol, yol.with_name(f"_alt_{n:02d}.jpg"))
    if not h:
        raise SystemExit(f"HATA: {c} sira {n} yeniden kodlama farki esigi asti")
    with open(h, "rb") as fh:
        y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (yol.name, fh, "image/jpeg")},
                          data={"rank": str(n), "alt_text": alt})
    yeni_id = (y or {}).get("listing_image_id")
    if not yeni_id or yeni_id == eski_id:            # Etsy tekillestirdi: eski SILINMEZ (sira bos kalmasin) - GOREV 0017
        raise SystemExit(f"HATA: {c} sira {n} yeni id yok/eskiyle ayni ({yeni_id}); eski {eski_id} silinmedi")
    x = next((z for z in galeri(api, lid) if z.get("listing_image_id") == yeni_id), None)
    f = fark(x.get("url_fullxfull"), yol) if x else None
    if not x or x.get("rank") != n or not esit(f):
        raise SystemExit(f"HATA: {c} yeni foto {yeni_id} sira {x and x.get('rank')} (beklenen {n}) fark {f}; "
                         f"eski {eski_id} silinmedi")
    api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
    log(f"{c} alt metin: sira {n} yeni foto {yeni_id} (fark {f}) dogrulandi, eski {eski_id} silindi")


def baglan(api, shop, lid, SET, g):
    """Renk varyasyonlari: renk -> SET renk dosyasi -> o siradaki gorsel id. Tutmayan varsa yazar; son durumu doner."""
    rid = {x.get("rank"): x.get("listing_image_id") for x in g}
    renk_dosya = SET.get("renk_gorselleri") or {}
    dosya_sira = {x["dosya"]: x["sira"] for x in SET["galeri"]}
    vimg = var_img(api, shop, lid)
    vi = [{"property_id": v.get("property_id"), "value_id": v.get("value_id"),
           "image_id": rid.get(dosya_sira.get(renk_dosya.get(v.get("value"))))} for v in vimg]
    if any(v.get("image_id") != x["image_id"] for v, x in zip(vimg, vi)):
        if not all(x["image_id"] for x in vi):
            raise SystemExit(f"HATA: varyasyon rengi eslesmedi: {[v.get('value') for v, x in zip(vimg, vi) if not x['image_id']]}")
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        vimg = var_img(api, shop, lid)
    return all(v.get("image_id") == rid.get(dosya_sira.get(renk_dosya.get(v.get("value")))) for v in vimg)


def onar(api, shop, a, c, lid, r, ref_alt, tfoto):
    """Onarim (GOREV 0015): dogru on-ek (sira 1..k: icerik <= ESIK ve cift PASS) korunur, gerisi kur() ile
    sona ekleyerek yeniden kurulur; alt metni tutmayan sira alt_yenile(); varyasyonlar baglan(); geri okunur."""
    SET, d, foto = set_indir(a.setler, c)
    A_, B_ = burclar(c)
    alt = {n: alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250].rstrip() for n, _, cl in foto}
    yol = {n: p for n, p, _ in foto}
    g = galeri(api, lid)
    fk = icerik(g, foto)
    ck = cift_denetle(g, foto, tfoto)
    k = 0
    while (k < len(g) and k < 13 and g[k].get("rank") == k + 1 and esit(fk.get(k + 1))
           and (ck.get(k + 1) or {}).get("ok")):
        k += 1
    log(f"{c} onar: galeri {len(g)} sira {[x.get('rank') for x in g]} | dogru on-ek {k} | icerik {fk} | "
        f"cift {json.dumps(ck)}")
    r["icerik_fark_once"], r["cift_once"], r["dogru_onek"] = fk, ck, k
    if k < 13 or len(g) != 13:
        g = kur(api, shop, c, lid, foto, alt, g, k)
    alt_yanlis = [x for x in g if x.get("rank") in alt and (x.get("alt_text") or "") != alt[x.get("rank")]]
    for x in alt_yanlis:
        alt_yenile(api, shop, c, lid, x.get("rank"), yol[x.get("rank")], alt[x.get("rank")], x.get("listing_image_id"))
    r["alt_duzeltilen"] = [x.get("rank") for x in alt_yanlis]
    if alt_yanlis:
        g = sirali(api, lid)
    var_ok = baglan(api, shop, lid, SET, g)
    rid = {x.get("rank"): x.get("listing_image_id") for x in g}
    fk2 = icerik(g, foto)
    ck2 = cift_denetle(g, foto, tfoto)
    kontrol = dict(r.get("kontrol") or {})
    kontrol.update(foto_13=len(g) == 13,
                   sira=sorted(rid) == list(range(1, 14)) and len(fk2) == 13 and all(esit(v) for v in fk2.values()),
                   cift=len(ck2) == 13 and all(v.get("ok") for v in ck2.values()),
                   alt_metin=all((x.get("alt_text") or "") == alt.get(x.get("rank")) for x in g),
                   varyasyon=var_ok)
    alt_fark = {x.get("rank"): {"canli": x.get("alt_text"), "beklenen": alt.get(x.get("rank"))} for x in g
                if (x.get("alt_text") or "") != alt.get(x.get("rank"))}
    if alt_fark:
        log(f"{c} alt metin farki: {json.dumps(alt_fark, ensure_ascii=False)}")
    r.update(kontrol=kontrol, icerik_fark=fk2, cift=ck2, alt_fark=alt_fark, sonuc="PASS" if all(kontrol.values()) else "FAIL")
    if r["sonuc"] == "PASS":
        r.pop("onar_gerek", None); r.pop("hata", None)
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
    ap.add_argument("--onar", default="", help="yukle: once hedefli onarim yapilacak virgullu CIFT listesi (GOREV 0015)")
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
    acik = {x for x in a.ciftler.split(",") if x}
    hedef = [c for c in setli if c in ilan and (ilan[c] != REF_ID or c in acik)]   # CL yalniz acikca --ciftler ile (GOREV 0017)
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
            alt = {n: alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250].rstrip() for n, _, cl in foto}
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
    zorla = [x for x in a.onar.split(",") if x]
    for c in zorla:                                              # durumda kaydi olmayan (kosu cokmesi) ilan da onarilir
        rapor["ilan"].setdefault(c, {"ilan_id": ilan.get(c), "sonuc": "FAIL", "kontrol": {"video_1": True, "state_degismedi": True}})
    for c, x in list(rapor["ilan"].items()):   # yalniz 'sira' tutmayan onceki ilanlar: icerik + onarim
        k = x.get("kontrol") or {}
        fk0 = x.get("icerik_fark") or {}
        yeniden = x.get("sonuc") == "PASS" and (len(fk0) < 13 or not all(esit(v) for v in fk0.values())
                                                 or "cift" not in k)          # cift olcutu yokken PASS olanlar
        onarilir = x.get("sonuc") == "FAIL" and all(k.get(n2) for n2 in ("foto_13", "video_1", "state_degismedi"))
        onarilir = onarilir or c in zorla or bool(x.get("onar_gerek"))
        if c in hedef and (yeniden or onarilir):
            bitti.discard(c)
            try:
                tamam = onar(api, shop, a, c, ilan[c], rapor["ilan"][c], ref_alt, tuzak_foto(c))
            except (SystemExit, Exception) as e:                     # GOREV 0017: HTTP/I-O/Pillow hatalari da ilan FAIL
                if "429" in str(e):
                    raise
                rapor["ilan"][c].update(sonuc="FAIL", hata=f"{type(e).__name__}: {str(e)[:300]}", onar_gerek=True)
                tamam = False
            if not tamam:
                log(f"{c} onarim tutmadi -> FAIL listesine")         # Serdar 26 Eyl: tek ilan FAIL hepsini durdurmaz
            bitti.add(c)                                             # bu kosuda tekrar yuklenmez
            (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
            try:
                rc("copy", str(OUT / "GALERI_TAMSET.json"), f"{A77}/_galeri")
            except subprocess.CalledProcessError:
                log("durum Drive'a yazilamadi")
    secim = [c for c in secim if c in hedef and c not in bitti]
    log(f"yuklenecek {len(secim)} ilan (seti olan {len(setli)}, onceden PASS {len(bitti)}) | kota {kota(api)}")
    ardisik = 0                                                  # art arda FAIL; 3 olursa sistematik hata: DUR
    for sira, c in enumerate(secim, 1):
        try:
            lid = ilan[c]; X = L.get(lid) or {}
            eski = sorted(X.get("images") or [], key=lambda x: x.get("rank") or 0)
            eski_vid = X.get("videos") or []
            gerek = tahmin(len(eski), bool(eski_vid))
            if api.calls - harcanan0 + gerek + 25 > a.butce:                # +25: olasi tek onarim
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
                log(f"[{sira}/{len(secim)}] {c} set eksik -> FAIL listesine")
                ardisik += 1
                if ardisik >= 3:
                    log("DUR: art arda 3 ilan FAIL - sistematik hata olabilir"); break
                continue
            t0 = time.time(); c0 = api.calls
            vimg_once = var_img(api, shop, lid)
            renk_dosya = SET.get("renk_gorselleri") or {}
            dosya_sira = {g["dosya"]: g["sira"] for g in SET["galeri"]}
            eksik_renk = [v.get("value") for v in vimg_once if dosya_sira.get(renk_dosya.get(v.get("value"))) is None]
            if eksik_renk:                                       # yazmadan once: renk eslesmesi yoksa ilana dokunma
                r.update(sonuc="FAIL", hata=f"varyasyon rengi eslesmedi: {eksik_renk} (ilana dokunulmadi)")
                log(f"[{sira}/{len(secim)}] {c} {r['hata']} -> FAIL listesine")
                ardisik += 1
                if ardisik >= 3:
                    log("DUR: art arda 3 ilan FAIL - sistematik hata olabilir"); break
                continue
            alt = {n: alt_uyarla(ref_alt.get(cl, ""), A_, B_)[:250].rstrip() for n, _, cl in foto}
            g3 = kur(api, shop, c, lid, foto, alt, galeri(api, lid), 0)   # guvenli akis: yalniz sona ekleme
            baglan(api, shop, lid, SET, g3)
            for v in eski_vid:
                api.delete(f"/shops/{shop}/listings/{lid}/videos/{v.get('video_id')}")
            with open(vpath, "rb") as fh:
                rv = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (f"{c}.mp4", fh, "video/mp4")},
                                   data={"name": f"{c}.mp4"})
            # geri okuma
            g2 = sirali(api, lid)
            if [x.get("rank") for x in g2] == list(range(1, 14)):
                baglan(api, shop, lid, SET, g2)      # video sonrasi varyasyon bagini dogrula (tutmuyorsa bir kez daha yaz)
            rid = {x.get("rank"): x.get("listing_image_id") for x in g2}
            fk = icerik(g2, foto)                                             # 13 foto olculur, rapora yazilir
            tfoto = tuzak_foto(c)
            ck = cift_denetle(g2, foto, tfoto)
            v2 = kararli(lambda: [x.get("video_id") for x in videolar(api, lid)], lambda v: len(v) == 1)
            vm2 = {x.get("value"): x.get("image_id") for x in var_img(api, shop, lid)}
            L2 = api.get(f"/listings/{lid}") or {}
            kontrol = {
                "foto_13": len(g2 or []) == 13,
                "sira": sorted(rid) == list(range(1, 14)) and len(fk) == 13 and all(esit(v) for v in fk.values()),
                "cift": len(ck) == 13 and all(v.get("ok") for v in ck.values()),
                "alt_metin": all((x.get("alt_text") or "") == alt_uyarla(ref_alt.get(foto[x.get("rank") - 1][2], ""), A_, B_)[:250].rstrip()
                                 for x in g2),
                "video_1": len(v2 or []) == 1,
                "varyasyon": all(vm2.get(v.get("value")) == rid.get(dosya_sira[renk_dosya[v.get("value")]]) for v in vimg_once),
                "state_degismedi": L2.get("state") == X.get("state"),
            }
            r.update(icerik_fark=fk, cift=ck)
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
                ardisik += 1
                log(f"{c} FAIL (1 onarim denendi) -> FAIL listesine, siradaki")
                if ardisik >= 3:
                    log("DUR: art arda 3 ilan FAIL - sistematik hata olabilir"); break
            else:
                ardisik = 0
        except (SystemExit, Exception) as e:                     # tek ilanin hatasi kosuyu durdurmaz (429 haric; GOREV 0017)
            if "429" in str(e):
                raise
            r0 = rapor["ilan"].setdefault(c, {"ilan_id": ilan[c]})
            r0.update(sonuc="FAIL", hata=f"{type(e).__name__}: {str(e)[:300]}", onar_gerek=True)
            log(f"[{sira}/{len(secim)}] {c} hata -> FAIL listesine: {type(e).__name__}: {str(e)[:200]}")
            (OUT / "GALERI_TAMSET.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
            try:
                rc("copy", str(OUT / "GALERI_TAMSET.json"), f"{A77}/_galeri")   # durum kaydi (sonraki kosu onarir)
            except subprocess.CalledProcessError:
                log("durum Drive'a yazilamadi")
            ardisik += 1
            if ardisik >= 3:
                log("DUR: art arda 3 ilan FAIL - sistematik hata olabilir"); break

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
