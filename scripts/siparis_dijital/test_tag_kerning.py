#!/usr/bin/env python3
"""tag_kerning + surucu.kerning_kur testleri (Serdar 5 Kas "A"). Bilinen PASS + bilinen FAIL. Sentetik metin; musteri verisi yok.
Font ve pilot12 kisisel-v1 dalindan (surucu/siparis_dosyasi.kisisel_hazirla ile ayni kaynak): KISISEL_KOK ortam degiskeni verilirse
oradan, yoksa 'git fetch --depth 1 origin kisisel-v1' + git archive gecici klasore.
Kullanim: python3 scripts/siparis_dijital/test_tag_kerning.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

BURA = Path(__file__).resolve().parent
KOK = BURA.parents[1]
sys.path.insert(0, str(BURA))
sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"), flush=True)


def kisisel_kok():
    if os.environ.get("KISISEL_KOK"):
        return Path(os.environ["KISISEL_KOK"])
    d = Path(tempfile.mkdtemp(prefix="kisisel_"))
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "kisisel-v1"], cwd=KOK, check=True)
    arc = subprocess.run(["git", "archive", "FETCH_HEAD", "scripts/kisisel", "assets"], cwd=KOK, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(d)], input=arc, check=True)
    return d


KK = kisisel_kok()
sys.path.insert(0, str(KK / "scripts" / "kisisel"))
import pilot6  # noqa: E402
import pilot12  # noqa: E402
import kisisel_pilot  # noqa: E402
import amp_eski  # noqa: E402
import tag_kerning as T  # noqa: E402

FP, W = kisisel_pilot.FONT_DIR / pilot6.TAG_FONT, pilot6.TAG_W
PUNTO = 247                       # 5 Kas CI A2 uretimi (OZET amp.punto)
ORJ = pilot12.ciz_cap
k("kurulum: pilot12.ciz_cap = pilot6.ciz_cap (kisisel-v1, harf harf: kerning yok)", ORJ is pilot6.ciz_cap)


def wa(L):
    """En dar yatay bosluk: soldan ilk iki murekkep bileseni (W, a) arasi, satir basina min (px)."""
    m = (np.asarray(L) > 40).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    c = sorted([i for i in range(1, n) if st[i, 4] > 50], key=lambda i: st[i, 0])
    g = []
    for y in range(m.shape[0]):
        xa, xb = np.nonzero(lab[y] == c[0])[0], np.nonzero(lab[y] == c[1])[0]
        if len(xa) and len(xb):
            g.append(int(xb.min() - xa.max() - 1))
    return min(g)


def surucu_kerning(deger):
    """surucu.kerning_kur'u temiz pilot12 ile cagirir; (sonuc, hata) doner."""
    pilot12.ciz_cap = ORJ
    if deger is None:
        os.environ.pop("TAG_KERNING", None)
    else:
        os.environ["TAG_KERNING"] = deger
    import surucu
    importlib.reload(surucu)
    try:
        return surucu.kerning_kur(), None
    except SystemExit as e:
        return None, str(e)


# ---------- 1 bilinen PASS: kapali -> hicbir sey degismez (piksel piksel)
r, h = surucu_kerning(None)
k("kapali (TAG_KERNING yok): kerning_kur None, pilot12.ciz_cap AYNI nesne", r is None and h is None and pilot12.ciz_cap is ORJ, (r, h))
r, h = surucu_kerning("kapali")
k("kapali (TAG_KERNING=kapali): pilot12.ciz_cap AYNI nesne", r is None and h is None and pilot12.ciz_cap is ORJ, (r, h))
import surucu as SR  # noqa: E402
for metin in ("Fire & Water", "Forever Yours", "Water"):
    pilot12.ciz_cap = ORJ; os.environ.pop("TAG_KERNING", None)
    SR.amp_kur({"mesaj": metin})                                      # gercek surucu yolu: kerning_kur (kapali) -> amp_eski.kur
    a = pilot12.ciz_cap(FP, W, PUNTO, metin)
    pilot12.ciz_cap = ORJ; amp_eski.kur(pilot12)
    b = pilot12.ciz_cap(FP, W, PUNTO, metin)
    k(f"kapali: '{metin}' maske + cap/taban kerning kodu yokken ile piksel piksel ayni",
      np.array_equal(np.asarray(a[0]), np.asarray(b[0])) and a[1:] == b[1:])
pilot12.ciz_cap = ORJ

# ---------- 2 bilinen FAIL (eski davranis) ve hedef (acik)
w_basic = wa(ORJ(FP, W, PUNTO, "Water")[0])
k(f"bilinen FAIL: harf harf (kerningsiz) 'Water' W-a {w_basic} px > 90 (kapi bunu FAIL sayar)", w_basic > 90, w_basic)
w_raqm = wa(T.ciz_cap_raqm(FP, W, PUNTO, "Water")[0])
k(f"acik: RAQM 'Water' W-a {w_raqm} px <= 90 ve font kerning'i 62 +-5 (57-67)", 57 <= w_raqm <= 67, w_raqm)
for metin in ("Fire", "ater", "T", "Forever"):                       # kerning cifti olmayan metin: harf harf ile ayni ya da +-4 px
    a, b = ORJ(FP, W, PUNTO, metin), T.ciz_cap_raqm(FP, W, PUNTO, metin)
    k(f"acik: '{metin}' kerning ciftsiz, yukseklik ve cap/taban ayni, genislik farki <= 4 px",
      a[0].size[1] == b[0].size[1] and a[1:] == b[1:] and abs(a[0].size[0] - b[0].size[0]) <= 4, (a[0].size, b[0].size, a[1:], b[1:]))

# ---------- 2b ligatur YOK (inceleme bulgu 1): yalniz kern; fi / ff / fl ligaturu cizilmez
from PIL import ImageFont  # noqa: E402
for metin in ("official", "Effie", "fire", "Fifi"):
    hh = ORJ(FP, W, PUNTO, metin)[0].size[0]
    bz = T.ciz_cap_raqm(FP, W, PUNTO, metin)[0].size[0]
    ft = ImageFont.truetype(str(FP), PUNTO, layout_engine=ImageFont.Layout.RAQM)
    lg = int(ft.getbbox(metin)[2] - ft.getbbox(metin)[0])              # varsayilan RAQM (liga acik)
    k(f"ligatur yok: '{metin}' genislik {bz} px harf harf {hh} px'e, varsayilan RAQM (liga) {lg} px'ten yakin",
      abs(bz - hh) < abs(bz - lg), (bz, hh, lg))
ft = ImageFont.truetype(str(FP), PUNTO, layout_engine=ImageFont.Layout.RAQM)
lg = int(ft.getbbox("official")[2] - ft.getbbox("official")[0]); hh = ORJ(FP, W, PUNTO, "official")[0].size[0]
k(f"bilinen FAIL: varsayilan RAQM (liga acik) 'official' {lg} px, harf harf {hh} px'ten > 10 px dar (ligatur)", hh - lg > 10, (lg, hh))

# ---------- 2c harf_aralari (rapor olcumu, son JPG): sentetik sayfa
for ad, f in (("kerning", T.ciz_cap_raqm), ("harf harf", ORJ)):
    L = np.asarray(f(FP, W, PUNTO, "Water")[0])
    sayfa = np.full((L.shape[0] + 100, L.shape[1] + 100, 3), 235, np.uint8)
    sayfa[50:50 + L.shape[0], 50:50 + L.shape[1]] -= (L[..., None] > 40).astype(np.uint8) * 170
    ar = T.harf_aralari(sayfa, [{"tur": "metin", "kutu": [45, 45, L.shape[1] + 55, L.shape[0] + 55]}])
    k(f"harf_aralari ({ad}): ilk aralik W-a {ar[0][0] if ar and ar[0] else '-'} px = maske olcumu {wa(L)} (+-2)",
      ar and ar[0] and abs(ar[0][0] - wa(L)) <= 2, ar)

# ---------- 3 surucu: raqm acik, & yolu ve & kapisi ayni cizim
r, h = surucu_kerning("raqm")
k("acik: kerning_kur 'raqm', pilot12.ciz_cap = ciz_cap_raqm", r == "raqm" and pilot12.ciz_cap is T.ciz_cap_raqm, (r, h))
amp_eski.kur(pilot12)
k("acik + &: amp_eski 'eski' = ciz_cap_raqm (& parcalari kerning'li)", pilot12.ciz_cap.eski is T.ciz_cap_raqm)
k("acik + &: tek JPG & kapisinin cizimi (getattr(ciz_cap, 'eski')) = ciz_cap_raqm",
  getattr(pilot12.ciz_cap, "eski", pilot12.ciz_cap) is T.ciz_cap_raqm)
amp_eski.KAYIT.clear()
cr, cu, ct = pilot12.ciz_cap(FP, W, PUNTO, "Fire & Water")
el = amp_eski.KAYIT[-1]["elemanlar"] if amp_eski.KAYIT else []
k("acik + &: dizgi 3 eleman (metin, amp, metin)", [e[0] for e in el] == ["metin", "amp", "metin"], el)
son = np.asarray(cr)[:, el[2][1]:el[2][2]] if len(el) == 3 else None
k(f"acik + &: & sonrasi 'Water' parcasinda W-a {wa(son) if son is not None else '-'} px (57-67)",
  son is not None and 57 <= wa(son) <= 67)
pilot12.ciz_cap = ORJ; amp_eski.kur(pilot12)
try:
    T.kur(pilot12); h = None
except SystemExit as e:
    h = str(e)
k("bilinen FAIL: amp_eski.kur'dan SONRA tag_kerning.kur -> SystemExit (& parcalari BASIC kalirdi)", h and "SONRA" in h, h)
pilot12.ciz_cap = ORJ
T.kur(pilot12); T.kur(pilot12)
k("acik: kur iki kez -> tek sarma (idempotent)", pilot12.ciz_cap is T.ciz_cap_raqm)
k("isim satiri degismez: pilot12.ciz_metin = kisisel_pilot.ciz_metin", pilot12.ciz_metin is kisisel_pilot.ciz_metin)
pilot12.ciz_cap = ORJ

# ---------- 4 raqm yoksa FAIL (sessiz BASIC yok) ve gecersiz deger
eski_check = T.features.check
T.features.check = lambda ad: False if ad == "raqm" else eski_check(ad)
try:
    r, h = surucu_kerning("raqm")
finally:
    T.features.check = eski_check
k("bilinen FAIL: raqm yok + TAG_KERNING=raqm -> SystemExit, pilot12 BASIC'e sessiz dusmez (degismez)",
  h and "RAQM yok" in h and pilot12.ciz_cap is ORJ, (r, h))
r, h = surucu_kerning("evet")
k("bilinen FAIL: TAG_KERNING gecersiz deger -> SystemExit", h and "TAG_KERNING" in h, (r, h))
pilot12.ciz_cap = ORJ; os.environ.pop("TAG_KERNING", None)

print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
