#!/usr/bin/env python3
"""GECICI DAL (main'e alinmaz): dijital poster teslim dosyasindan 1:1 kesit. YALNIZ KESER: teslim dosyasi ve uretim kodu degismez
(dosya salt okunur acilir, sha256 once / sonra karsilastirilir). Bant SABIT DEGIL, goruntuden OLCULUR: altin murekkep (R - B > 60)
satir profilinden anlamli bantlar bulunur; beklenen sira ana sembol, kucuk semboller, isim satiri, mesaj. Kesit = kucuk semboller
ustunden mesaj altina, pay ile, tam genislik, olcekleme yok.
Ek kapilar (deger YAZILMAZ, yalniz True / False ve sayi): uretim girdisi (siparis.json) Etsy okumasiyla (KISISEL.json) harf harf ayni;
dosya adi, piksel, dpi, 4:4:4, < 20 MB; uretim kapilari (KAPI.json).
Kullanim: kesit_olcum.py URETIM_DIR KISISEL.json CIKTI_DIR   -> cikis 0 = hepsi PASS, 1 = FAIL (kesit yine yazilir, OZET'te neden)"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, JpegImagePlugin

Image.MAX_IMAGE_PIXELS = None
ESIK_RB = 60            # altin: R - B > 60 (zemin mavi: R < B; beyaz yildiz: R ~ B). Ornek olcum: yazi bandi >= 32e-4 W^2, leke <= 0.7e-4 W^2
ESIK_MUREKKEP = 3e-4    # bant murekkebi / W^2
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
                       isim1_ayni=s["isim1"] == v.get(f"Name under {b1.capitalize()}", "").strip(),
                       isim2_ayni=s["isim2"] == v.get(f"Name under {b2.capitalize()}", "").strip(),
                       mesaj_ayni=s["tagline"] == v.get("Your message", "").strip(),
                       renk_ayni=v.get("Color", "").upper().replace(" ", "_") == s.get("renk_secim"),
                       olcu_ayni=v.get("Size", "").replace("×", "x").replace("″", "").split(" ")[0] == s["olcu"],
                       format_dijital=v.get("Format") == "Digital File")
    oz["girdi"]["PASS"] = bool(oz["girdi"]["kalem_sayisi"] == 1 and all(x for q, x in oz["girdi"].items() if q != "kalem_sayisi"))
    # 2) teslim dosyasi: ad, piksel, dpi, 4:4:4, bayt
    d = {"var": teslim.exists(), "ad": teslim.name}
    kutu = None
    if teslim.exists():
        h0 = sha(teslim)
        im = Image.open(teslim)
        w, h = INC[s["olcu"]]
        d.update(boyut=list(im.size), hedef=[w * 300, h * 300], dpi=[round(float(x)) for x in im.info.get("dpi", (0, 0))],
                 ornekleme_444=JpegImagePlugin.get_sampling(im) == 0, bayt=teslim.stat().st_size, bicim=im.format)
        d["PASS"] = bool(d["boyut"] == d["hedef"] and d["dpi"] == [300, 300] and d["ornekleme_444"] and d["bayt"] < 20_000_000 and d["bicim"] == "JPEG")
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
    oz["teslim"] = d
    # 3) uretim kapilari (KAPI.json) + onizleme dosyasi
    kp = json.load(open(ur / "KAPI.json", encoding="utf-8")) if (ur / "KAPI.json").exists() else {}
    oz["uretim_kapilari"] = {a: bool(x.get("PASS")) for a, x in kp.items() if isinstance(x, dict)}
    oz["uretim_kapilari"]["PASS"] = bool(kp.get("PASS"))
    oni = ur / f"{kok}_2000.jpg"
    oz["onizleme"] = {"ad": oni.name, "var": oni.exists(), "boyut": list(Image.open(oni).size) if oni.exists() else None}
    oz["onizleme"]["PASS"] = oni.exists()
    oz["PASS"] = bool(all(oz[a].get("PASS") for a in ("girdi", "teslim", "kesit", "uretim_kapilari", "onizleme")))
    json.dump(oz, open(out / "KESIT_OZET.json", "w", encoding="utf-8"), indent=1)
    print("KESIT:", json.dumps(oz))
    return 0 if oz["PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
