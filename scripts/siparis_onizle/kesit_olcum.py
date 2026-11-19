#!/usr/bin/env python3
"""GECICI YARDIMCI (main'e alinmaz; 18 Kas: dal claude/upbeat-hopper-fjsaii, gecici/kesit-yardimci 330970c8 tabanli): poster teslim dosyasindan 1:1 kesit. YALNIZ KESER: teslim dosyasi ve uretim kodu degismez
(dosya salt okunur acilir, sha256 once / sonra karsilastirilir). Bant SABIT DEGIL, goruntuden OLCULUR: altin murekkep (R - B > 60)
satir profilinden anlamli bantlar bulunur; beklenen sira ana sembol, kucuk semboller, isim satiri, mesaj. Kesit = kucuk semboller
ustunden mesaj altina, pay ile, tam genislik, olcekleme yok.
Ek kapilar (deger YAZILMAZ, yalniz True / False ve sayi): uretim girdisi (siparis.json) Etsy okumasiyla (KISISEL.json) harf harf ayni;
dosya adi, piksel, dpi, 4:4:4, < 20 MB; uretim kapilari (KAPI.json).
18 Kas (Merkez STEP 2, siparis baski): Format "Print" kabul (Digital File da); kirmizi nokta taramasi: teslim dosyasinin 4 kenarinda 10 px serit,
R - G > 60 ve R - B > 60 olan piksel varsa FAIL (13 Kas Deep Black sag kenar 3x2 px nokta dersi; altin murekkep R - G < 60 oldugu icin sayilmaz).
Kullanim: kesit_olcum.py URETIM_DIR KISISEL.json CIKTI_DIR   -> cikis 0 = hepsi PASS, 1 = FAIL (kesit yine yazilir, OZET'te neden)"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, JpegImagePlugin

Image.MAX_IMAGE_PIXELS = None
ESIK_RB = 60            # altin: R - B > 60 (zemin mavi: R < B; beyaz yildiz: R ~ B). Ornek olcum: yazi bandi >= 32e-4 W^2, leke <= 0.7e-4 W^2
ESIK_MUREKKEP = 3e-4    # bant murekkebi / W^2
KENAR_PX = 10           # kirmizi nokta taramasi: kenar seridi genisligi (px)
ESIK_KIRMIZI = 60       # kirmizi: R - G > 60 ve R - B > 60
FORMATLAR = ("Digital File", "Print")
BEKLENEN_FORMAT = os.environ.get("BEKLENEN_FORMAT", "Print")   # siparis turu: baski siparisinde yalniz "Print" gecer (inceleme LOW 6)
URETIM_KOSU = os.environ.get("URETIM_KOSU", "")                # verilirse SURE.json kosu no ayni olmali (eski klasor dosyasi karismasin)


def boyut_siniri(fmt):
    """19 Kas Serdar karar 1: baski (Print) dosyasi < 100 MB (Printful JPEG/PNG siniri), dijital teslim < 20 MB (Etsy). Bilinmeyen = 20 MB."""
    return 100_000_000 if fmt == "Print" else 20_000_000


def olcu_oku(deger):
    """Etsy Size degeri -> '11x14' (11x14 in, 11″ × 14″, 11 x 14 ... bicimleri); bulunmazsa ''."""
    m = re.match(r"\s*(A\d)\b", deger or "")
    if m:
        return m.group(1)
    m = re.search(r"(?<![\d.])(\d+)\s*[″\"]?\s*[x×X]\s*(\d+)(?![\d.])", deger or "")
    return f"{m.group(1)}x{m.group(2)}" if m else ""
INC = {"5x7": (5, 7), "8x10": (8, 10), "11x14": (11, 14), "12x16": (12, 16), "12x18": (12, 18), "16x20": (16, 20), "16x24": (16, 24),
       "18x24": (18, 24), "20x30": (20, 30), "24x30": (24, 30), "24x36": (24, 36)}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bantlar(m):
    """Altin maskesinden anlamli yatay bantlar: [(y0, y1, murekkep, x0, x1)] yukaridan asagi."""
    H, W = m.shape
    satir = m.sum(1)
    ham, bas = [], None
    for y in range(H):
        if satir[y] and bas is None:
            bas = y
        if not satir[y] and bas is not None:
            ham.append([bas, y]); bas = None
    if bas is not None:
        ham.append([bas, H])
    bir = []
    for b0, b1 in ham:                                    # bitisik parcalar (bosluk < W/250) tek bant
        if bir and b0 - bir[-1][1] < max(4, W // 250):
            bir[-1][1] = b1
        else:
            bir.append([b0, b1])
    out = []
    for b0, b1 in bir:
        blok = m[b0:b1]
        mu = int(blok.sum())
        if mu >= ESIK_MUREKKEP * W * W and b1 - b0 >= W // 100:
            xs = np.where(blok.any(0))[0]
            out.append((b0, b1, mu, int(xs.min()), int(xs.max()) + 1))
    return out


def kirmizi_tara(im):
    """Teslim dosyasinin 4 kenar seridinde (KENAR_PX) kirmizi piksel: sayi + kutular (x0, y0, x1, y1). PASS = hic yok."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    H, W = a.shape[:2]
    m = ((a[..., 0] - a[..., 1]) > ESIK_KIRMIZI) & ((a[..., 0] - a[..., 2]) > ESIK_KIRMIZI)
    k = KENAR_PX
    seritler = {"sol": (0, 0, k, H), "sag": (W - k, 0, W, H), "ust": (0, 0, W, k), "alt": (0, H - k, W, H)}
    o = {"serit_px": k, "esik": ESIK_KIRMIZI}
    toplam = 0
    for ad, (x0, y0, x1, y1) in seritler.items():
        s = m[y0:y1, x0:x1]
        n = int(s.sum()); toplam += n
        kutu = None
        if n:
            ys, xs = np.nonzero(s)
            kutu = [int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0 + 1, int(ys.max()) + y0 + 1]
        o[ad] = dict(piksel=n, kutu=kutu)
    o["tum_goruntu_piksel"] = int(m.sum())          # bilgi: kenar disi kirmizi (karar yalniz kenar seritlerinden)
    o["PASS"] = toplam == 0
    return o


def olc(im):
    """-> (kesit kutusu ya da None, olcum sozlugu)."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    H, W = a.shape[:2]
    m = (a[..., 0] - a[..., 2]) > ESIK_RB
    b = bantlar(m)
    o = {"bant_sayisi": len(b), "bantlar": [dict(y0=x[0], y1=x[1], yukseklik=x[1] - x[0], murekkep_e4W2=round(x[2] / W / W * 1e4, 2)) for x in b]}
    if len(b) != 4:
        o["hata"] = "beklenen 4 bant (ana, kucuk semboller, isim satiri, mesaj) bulunamadi"
        return None, o
    ana, kucuk, isim, mesaj = b
    def kumeler(bt):                                      # bandin yatay kumeleri (bosluk >= W/50 ayirir): [(x0, x1)]
        dolu = m[bt[0]:bt[1]].any(0)
        out, bas, son = [], None, None
        for x in np.where(dolu)[0]:
            if bas is None:
                bas = son = x
            elif x - son >= W // 50:
                out.append((int(bas), int(son) + 1)); bas = son = x
            else:
                son = x
        if bas is not None:
            out.append((int(bas), int(son) + 1))
        return [k for k in out if m[bt[0]:bt[1], k[0]:k[1]].sum() >= ESIK_MUREKKEP * W * W / 10]      # yildiz lekesi kume sayilmaz
    kk, ik = kumeler(kucuk), kumeler(isim)
    pay = max(20, round(W * 0.03))
    y0 = max(kucuk[0] - pay, (ana[1] + kucuk[0]) // 2)   # ana sembole tasma
    y1 = min(H, mesaj[1] + pay)
    o.update(kucuk_kume=len(kk), isim_kume=len(ik),
             kucuk_iki_yanda=bool(len(kk) >= 2 and (kk[0][0] + kk[0][1]) / 2 < W / 2 < (kk[-1][0] + kk[-1][1]) / 2),   # sembol parcali olabilir
             isim_iki_yanda=bool(len(ik) >= 3 and (ik[0][0] + ik[0][1]) / 2 < W / 2 < (ik[-1][0] + ik[-1][1]) / 2),   # isim1, sonsuz, isim2
             mesaj_merkez_sapma_W=round(abs((mesaj[3] + mesaj[4]) / 2 - W / 2) / W, 3),
             ana_en_buyuk=bool(ana[1] - ana[0] > 3 * max(kucuk[1] - kucuk[0], isim[1] - isim[0], mesaj[1] - mesaj[0])),
             kutu=[0, int(y0), W, int(y1)], pay_px=pay)
    o["kesit_isim_ve_mesaji_kapsiyor"] = bool(y0 <= kucuk[0] and y0 <= isim[0] and y1 >= mesaj[1] and y0 >= ana[1])
    o["PASS"] = bool(o["kucuk_iki_yanda"] and o["isim_iki_yanda"] and o["mesaj_merkez_sapma_W"] <= 0.15 and o["ana_en_buyuk"]
                     and o["kesit_isim_ve_mesaji_kapsiyor"])
    return (0, int(y0), W, int(y1)), o


def onizleme_yap(teslim, mo, uzun=2000, seed=7):
    """Musteri onizlemesi (18 Kas V2B): 8 bit LANCZOS + q92 kucultme koyu mavi zeminde es merkezli kuantalama halkasi yapiyordu
    (olculdu: duzeltilmis 11x14'ten bile). Kayan noktada alan ortalamasi (BOX, kanal basina) + TPDF + Gauss sigma 1.0 titresim, sonra
    JPEG luma q95 tablosu, kroma tablosu tum 1 (kroma nicemlemesi mavi halka yapiyordu), 4:4:4, 300 dpi."""
    with Image.open(teslim) as it:
        rgb = it.convert("RGB"); tw, th = rgb.size; k = uzun / max(tw, th); hw = (round(tw * k), round(th * k))
        kan = [np.asarray(c.convert("F").resize(hw, Image.BOX), np.float32) for c in rgb.split()]
    F = np.stack(kan, -1); r = np.random.default_rng(seed)
    n = r.random(F.shape, dtype=np.float32) - r.random(F.shape, dtype=np.float32) + r.standard_normal(F.shape, dtype=np.float32)
    U = Image.fromarray(np.clip(np.round(F + n), 0, 255).astype(np.uint8))
    import io
    b = io.BytesIO(); U.save(b, "JPEG", quality=95, subsampling=0); luma = list(Image.open(b).quantization[0])
    U.save(mo, "JPEG", qtables=[luma, [1] * 64], subsampling=0, dpi=(300, 300), optimize=True)


def onizleme_denetle(teslim, mo, esik=4.0):
    """Musteri onizlemesi denetimi (18 Kas V2B; ORTA bulgu: onceki denetim kendi urettigi dosyayi olcuyordu, dusemezdi). Bagimsiz olcu:
    uzun kenar 2000, en-boy orani teslimle ayni (0.002), ICERIK: teslim dosyasi onizleme boyutuna BOX ile indirilip ortalama mutlak fark
    (0-255) < esik. Yanlis kaynak (2:3 ana kopya, baska poster), yanlis boy ya da bos dosya FAIL verir."""
    with Image.open(teslim) as a, Image.open(mo) as b:
        tw, th = a.size; pb = list(b.size)
        oran = abs(pb[0] / pb[1] - tw / th) < 0.002
        fark = None
        if oran:
            ref = np.asarray(a.convert("RGB").resize(tuple(pb), Image.BOX), np.float32)
            fark = round(float(np.abs(ref - np.asarray(b.convert("RGB"), np.float32)).mean()), 3)
    d = dict(musteri=Path(mo).name, musteri_boyut=pb, musteri_kaynak="teslim", musteri_oran_ayni=oran, musteri_uzun_kenar=max(pb),
             musteri_icerik_fark=fark, musteri_icerik_esik=esik)
    d["musteri_PASS"] = bool(oran and max(pb) == 2000 and fark is not None and fark < esik)
    return d


def main():
    ur, kis, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    s = json.load(open(ur / "siparis.json", encoding="utf-8"))
    b1, b2 = s["cift"].split("_")
    renk = "_".join(x.capitalize() for x in s.get("renk_secim", "MIDNIGHT_BLUE").split("_"))
    kok = f"AstroLoveArt_{b1.capitalize()}_{b2.capitalize()}_{renk}"
    teslim = ur / f"{kok}_{s['olcu']}.jpg"
    oz = {"kok": kok, "olcu": s["olcu"], "dosyalar": sorted(p.name for p in ur.iterdir())}
    # 1) uretim girdisi == Etsy okumasi (harf harf; degerler yazilmaz)
    k = json.load(open(kis, encoding="utf-8"))["kalemler"]
    v = {x["ad"]: x["deger"] for x in k[0]["varyasyon"]}
    oz["girdi"] = dict(kalem_sayisi=len(k), cift_alfabetik=[b1, b2] == sorted([b1, b2]),
                       isim1_ayni=s["isim1"].strip() == v.get(f"Name under {b1.capitalize()}", "").strip() != "",
                       isim2_ayni=s["isim2"].strip() == v.get(f"Name under {b2.capitalize()}", "").strip() != "",
                       mesaj_ayni=s["tagline"].strip() == v.get("Your message", "").strip() != "",
                       renk_ayni=v.get("Color", "").strip().upper().replace(" ", "_") == s.get("renk_secim"),
                       olcu_ayni=olcu_oku(v.get("Size", "")) == s["olcu"],
                       format_gecerli=v.get("Format") in FORMATLAR and v.get("Format") == BEKLENEN_FORMAT)
    oz["girdi"]["format"] = {"Digital File": "dijital", "Print": "baski"}.get(v.get("Format"), "bilinmiyor")
    oz["girdi"]["PASS"] = bool(oz["girdi"]["kalem_sayisi"] == 1 and all(x for q, x in oz["girdi"].items() if q not in ("kalem_sayisi", "format")))
    # 2) teslim dosyasi: ad, piksel, dpi, 4:4:4, bayt
    d = {"var": teslim.exists(), "ad": teslim.name}
    kutu = None
    if teslim.exists():
        h0 = sha(teslim)
        im = Image.open(teslim)
        w, h = INC[s["olcu"]]
        d.update(boyut=list(im.size), hedef=[w * 300, h * 300], dpi=[round(float(x)) for x in im.info.get("dpi", (0, 0))],
                 ornekleme_444=JpegImagePlugin.get_sampling(im) == 0, bayt=teslim.stat().st_size, bicim=im.format)
        d["sinir_bayt"] = boyut_siniri(BEKLENEN_FORMAT)
        d["PASS"] = bool(d["boyut"] == d["hedef"] and d["dpi"] == [300, 300] and d["ornekleme_444"] and d["bayt"] < d["sinir_bayt"] and d["bicim"] == "JPEG")
        oz["kirmizi_nokta"] = kirmizi_tara(im)
        kutu, oz["kesit"] = olc(im)
        if kutu:
            kes = im.convert("RGB").crop(kutu)
            kes.save(out / f"KESIT_1x1_{kok}_{s['olcu']}.jpg", quality=95, subsampling=0, dpi=(300, 300))
            oz["kesit"]["dosya"] = f"KESIT_1x1_{kok}_{s['olcu']}.jpg"
            oz["kesit"]["boyut"] = list(kes.size)
            oz["kesit"]["olcek"] = "1:1 (olcekleme yok)"
        im.close()
        d["sha256_degismedi"] = sha(teslim) == h0
        d["PASS"] = bool(d["PASS"] and d["sha256_degismedi"])
    else:
        d["PASS"] = False
        oz["kesit"] = {"PASS": False, "hata": "teslim dosyasi yok"}
        oz["kirmizi_nokta"] = {"PASS": False, "hata": "teslim dosyasi yok"}
    oz["teslim"] = d
    # 3) uretim kapilari (KAPI.json) + onizleme dosyasi
    kp = json.load(open(ur / "KAPI.json", encoding="utf-8")) if (ur / "KAPI.json").exists() else {}
    oz["uretim_kapilari"] = {a: bool(x.get("PASS")) for a, x in kp.items() if isinstance(x, dict)}
    g = kp.get("g") if isinstance(kp.get("g"), dict) else {}
    su = json.load(open(ur / "SURE.json", encoding="utf-8")) if (ur / "SURE.json").exists() else {}
    oz["uretim_kapilari"]["kapi_bu_dosyanin"] = bool(teslim.exists() and g.get("bayt") == teslim.stat().st_size and g.get("olcu") == s["olcu"])
    oz["uretim_kapilari"]["kosu_ayni"] = (str(su.get("kosu")) == URETIM_KOSU) if URETIM_KOSU else None
    oz["uretim_kapilari"]["PASS"] = bool(kp.get("PASS") is True and oz["uretim_kapilari"]["kapi_bu_dosyanin"]
                                         and oz["uretim_kapilari"]["kosu_ayni"] is not False)
    oni = ur / f"{kok}_2000.jpg"
    oz["onizleme"] = {"ad": oni.name, "var": oni.exists(), "boyut": list(Image.open(oni).size) if oni.exists() else None}
    # 18 Kas (Merkez REAL GO): musteri onizlemesi 11x14 TESLIM dosyasindan, uzun kenar 2000 px (2:3 ana kopyadan degil)
    mo = out / f"{kok}_{s['olcu']}_Preview.jpg"
    hazir = ur / mo.name                                                 # 19 Kas: uretim (HALKA_DUZELT) onizlemeyi kendisi yazar; varsa o kullanilir
    if teslim.exists() and hazir.exists():
        import shutil
        shutil.copy2(hazir, mo); oz["onizleme"]["musteri_kaynagi"] = "uretim"
    if teslim.exists():
        if not hazir.exists():
            onizleme_yap(teslim, mo)
        oz["onizleme"].update(onizleme_denetle(teslim, mo))
        oz["onizleme"]["PASS"] = bool(oni.exists() and oz["onizleme"]["musteri_PASS"])
    else:
        oz["onizleme"]["PASS"] = False
    oz["PASS"] = bool(all(oz[a].get("PASS") for a in ("girdi", "teslim", "kesit", "kirmizi_nokta", "uretim_kapilari", "onizleme")))
    json.dump(oz, open(out / "KESIT_OZET.json", "w", encoding="utf-8"), indent=1)
    print("KESIT:", json.dumps(oz))
    return 0 if oz["PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
