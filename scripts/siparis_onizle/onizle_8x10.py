#!/usr/bin/env python3
"""Siparis 8x10 baski dosyasi -> cercevesiz onizleme + isim/mesaj bolgesi 1:1 kesit + kapilar (yalniz True / False ve sayi basar).
Deger (isim / mesaj) loga ve OZET'e YAZILMAZ. Cift, renk ve olcu KISISEL.json alan adlarindan okunur (sabit cift yok).
Kullanim: onizle_8x10.py URETIM_DIR KISISEL.json CIKTI_DIR [URETIM_KOSU_NO]   -> cikis 0 = PASS, 1 = FAIL
Kapilar: girdi (siparis.json == KISISEL.json, harf harf), teslim (ad, 2400x3000, 300 dpi, 4:4:4, < 20 MB), uretim (KAPI.json PASS),
kesit (alt %45, 1:1), OCR (bilgi; karar uretim kapisi d + goz kontrolu)."""
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ur, kis, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
kosu = sys.argv[4] if len(sys.argv) > 4 else ""
out.mkdir(parents=True, exist_ok=True)
kalem = json.load(open(kis, encoding="utf-8"))["kalemler"]
v = {x["ad"]: x["deger"] for x in kalem[0]["varyasyon"]}
ON = "Name under "
burc = sorted(k[len(ON):] for k in v if k.startswith(ON))
oz = dict(kalem_sayisi=len(kalem), burc_alani=len(burc))
if len(kalem) != 1 or len(burc) != 2:
    json.dump(dict(oz, PASS=False), open(out / "ONIZLE_OZET.json", "w"), indent=1)
    print("ONIZLE:", json.dumps(dict(oz, PASS=False)))
    sys.exit(1)
b1, b2 = burc                                                      # alfabetik: isim1 = ilk burcun altindaki isim (posterde solda)
i1, i2, m = v[ON + b1].strip(), v[ON + b2].strip(), v["Your message"].strip()
renk = "_".join(w.capitalize() for w in v.get("Color", "").split())
olcu = v.get("Size", "").replace("×", "x").replace("″", "").split(" ")[0]
kok = f"AstroLoveArt_{b1.capitalize()}_{b2.capitalize()}_{renk}_{olcu}"
oz.update(kok=kok, olcu=olcu)
baski = ur / f"{kok}.jpg"

# 1) girdi kapisi: uretim girdisi Etsy okumasiyla harf harf ayni (deger basilmaz)
s = json.load(open(ur / "siparis.json", encoding="utf-8")) if (ur / "siparis.json").exists() else {}
g = dict(siparis_json=bool(s), cift_ayni=s.get("cift") == f"{b1}_{b2}".upper(), isim1_ayni=s.get("isim1") == i1, isim2_ayni=s.get("isim2") == i2,
         mesaj_ayni=s.get("tagline") == m, olcu_ayni=s.get("siparis_olcu") == olcu == "8x10", renk_ayni=v.get("Color", "").upper().replace(" ", "_") in (s.get("renk") or {}),
         format_baski=v.get("Format") == "Print", mesaj_tek_satir="\n" not in m and "\r" not in m)
g["PASS"] = all(g.values()); oz["girdi"] = g

# 2) teslim kapisi
t = dict(dosya_var=baski.exists())
if baski.exists():
    ham = baski.read_bytes()
    im = Image.open(baski); dpi = im.info.get("dpi"); W, H = im.size
    alt = [c[1:3] for c in getattr(im, "layer", [])]              # JPEG bilesen ornekleme carpanlari; 4:4:4 = hepsi (1, 1)
    t.update(boyut=[W, H], dpi=[round(float(d)) for d in dpi] if dpi else None, olcu_ok=(W, H) == (2400, 3000),
             dpi_ok=bool(dpi) and all(round(float(d)) == 300 for d in dpi), ornekleme_444=im.mode == "RGB" and len(alt) == 3 and all(a == (1, 1) for a in alt),
             mb=round(len(ham) / 1e6, 2), boyut_ok=len(ham) < 20e6, sha256=hashlib.sha256(ham).hexdigest())
    im = im.convert("RGB")
t["PASS"] = all(t.get(a) for a in ("dosya_var", "olcu_ok", "dpi_ok", "ornekleme_444", "boyut_ok")); oz["teslim"] = t

# 3) uretim kapilari
kp = json.load(open(ur / "KAPI.json", encoding="utf-8")) if (ur / "KAPI.json").exists() else {}
RK = v.get("Color", "").upper().replace(" ", "_"); kr = kp.get(RK) if isinstance(kp.get(RK), dict) else {}
ko = kr.get(olcu) if isinstance(kr.get(olcu), dict) else {}
su = json.load(open(ur / "SURE.json", encoding="utf-8")) if (ur / "SURE.json").exists() else {}
u = dict(dosya_var=bool(kp), ust_pass=kp.get("PASS") is True, renk_pass=kr.get("PASS") is True, olcu_pass=ko.get("PASS") is True,
         alt_kapilar={a: x.get("PASS") is True for a, x in ko.items() if isinstance(x, dict)},
         leke_pass=(kr.get("L") or {}).get("PASS") is True, kesik_pass=(kr.get("K") or {}).get("PASS") is True,
         sure_kosu_ayni=bool(kosu) and str(su.get("kosu")) == kosu, kod_ref=su.get("gpt_ref"))
u["PASS"] = all(u[a] for a in ("dosya_var", "ust_pass", "renk_pass", "olcu_pass", "leke_pass", "kesik_pass", "sure_kosu_ayni")) and all(u["alt_kapilar"].values())
oz["uretim_kapilari"] = u

ocr = dict(calisti=False)
if t["PASS"]:
    # 4) 1:1 kesit: alt %45 (isimler, sonsuz, kucuk isaretler, mesaj); piksel olcegi 1:1
    y0 = int(H * 0.55)
    kes = im.crop((0, y0, W, H))
    kes.save(out / f"{kok}_KESIT_1x1.jpg", quality=95, dpi=(300, 300), subsampling=0)
    # altin murekkep satir bantlari (R - B > 60): kesit icindeki bant sayisi ve kesit ust kenarinin bir yazi bandini kesip kesmedigi
    a = np.asarray(im, dtype=np.int16); murekkep = (a[:, :, 0] - a[:, :, 2]) > 60; satir = murekkep.sum(axis=1) >= W // 100
    bant, bas = [], None
    for y, d in enumerate(satir):
        if d and bas is None: bas = y
        if not d and bas is not None:
            if bant and bas - bant[-1][1] <= W // 250: bant[-1][1] = y
            else: bant.append([bas, y])
            bas = None
    if bas is not None: bant.append([bas, H])
    bant = [x for x in bant if x[1] - x[0] >= 6]
    ic = [x for x in bant if x[0] >= y0]
    oz["kesit"] = dict(kutu=[0, y0, W, H], olcek="1:1", boyut=[W, H - y0], bant_toplam=len(bant), bant_kesitte=len(ic),
                       ust_kenar_bant_kesiyor=any(x[0] < y0 < x[1] and x[1] - x[0] < H // 8 for x in bant), PASS=len(ic) >= 3)
    # cercevesiz baski onizleme (gercek oran 8:10) acik duvar zemininde, hafif golge
    dw, dh = 1800, 2200; pw, ph = 1040, 1300
    zemin = Image.new("RGB", (dw, dh), (236, 233, 228))
    x, y = (dw - pw) // 2, (dh - ph) // 2 - 40
    gl = Image.new("L", (dw, dh), 0); gl.paste(150, (x + 14, y + 22, x + pw + 14, y + ph + 22)); gl = gl.filter(ImageFilter.GaussianBlur(22))
    zemin = Image.composite(Image.new("RGB", (dw, dh), (150, 146, 140)), zemin, gl)
    zemin.paste(im.resize((pw, ph), Image.LANCZOS), (x, y))
    zemin.save(out / f"{kok}_Preview.jpg", quality=92, dpi=(300, 300))
    oz["onizleme"] = dict(dosya=f"{kok}_Preview.jpg", boyut=[dw, dh], PASS=True)
    # OCR (tesseract varsa): metin degerleri basilmaz, yalniz sonuc. BILGI: karar degil.
    try:
        g2 = Image.fromarray(np.where(murekkep[y0:], 0, 255).astype(np.uint8))
        g2.save("/tmp/ocr_in.png")
        tx = subprocess.run(["tesseract", "/tmp/ocr_in.png", "-", "--psm", "6"], capture_output=True, text=True, timeout=120).stdout
        sat = [re.sub(r"\s+", " ", q).strip() for q in tx.splitlines() if q.strip()]
        tok = [w for w in re.findall(r"[A-Za-z]+", tx)]
        en_iyi = max((difflib.SequenceMatcher(None, q.lower(), m.lower()).ratio() for q in sat), default=0.0)
        k1 = [n for n, w in enumerate(tok) if w.upper() == i1.upper()]; k2 = [n for n, w in enumerate(tok) if w.upper() == i2.upper()]
        ocr = dict(calisti=True, isim1_bulundu=bool(k1), isim2_bulundu=bool(k2), isim1_isim2den_once=bool(k1 and k2) and min(k1) < min(k2),
                   mesaj_tam_satir=any(q == m for q in sat), mesaj_benzerlik=round(en_iyi, 3), satir_sayisi=len(sat))
    except Exception as e:                                         # OCR bilgi; deger basilmaz, yalniz hata turu
        ocr = dict(calisti=False, hata=type(e).__name__)
    finally:
        Path("/tmp/ocr_in.png").unlink(missing_ok=True)
else:
    oz["kesit"] = dict(PASS=False); oz["onizleme"] = dict(PASS=False)
oz["ocr"] = ocr
oz["icerik_goz_kontrolu_gerekli"] = True                             # PASS = kayit + bicim; gorseldeki yazi 1:1 kesitte gozle dogrulanir
oz["PASS"] = bool(all(oz[a].get("PASS") for a in ("girdi", "teslim", "uretim_kapilari", "kesit", "onizleme")))
json.dump(oz, open(out / "ONIZLE_OZET.json", "w"), indent=1)
print("ONIZLE:", json.dumps(oz))
sys.exit(0 if oz["PASS"] else 1)
