#!/usr/bin/env python3
"""WALLPAPER V3: murekkep kaynagi = kisisel'in SIPARIS URETICISI (Serdar 25 Eyl 2026).

KARAR: poster + MEDIAN yolu birakildi (dokulu edisyonda ham fark maskesi
isim satirini ayirt edemedi - Warm_Parchment, run 36158458249).

Yeni yol:
  baski   = kisisel'in urettigi ISIMLI 24x32 (3:4, 7200x9600) dosya, edisyonda
  plate   = kisisel PLATE (TEMP/SIPARIS_ISIM/PLATES/<EDISYON>_24X32.png)
  murekkep= baski - plate                      ESIK YOK, ham doku farki YOK
  zemin   = WP_PLATES/CLEAN/PLATE_<ED>_<DEV>_CLEAN.png
  yerlesim= wp_v2 / wp_build_pair afin yolu (WP_LAYOUT_SPEC 7.1) + GEOM
  kapilar = wp_v2'nin 10 kapisi (5 + EK 5)

Aktarim iki bicimde olculebilir (--aktarim):
  fark  (varsayilan): out = CLEAN + place(baski - plate). Premultiply oldugu
        icin glif kenarlarinda kisisel PLATE zemini SIZMAZ; plate ile CLEAN
        ayni oldugu her yerde sonuc tam dogru blend'dir.
  maske             : out = A*place(baski) + (1-A)*CLEAN. Kenar pikselleri
        kisisel PLATE zeminini tasir (hale riski); karsilastirma icin durur.
Iki bicimin farki ve hale olcusu raporlanir; secim olcumle yapilir.
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
import importlib.util                                                         # noqa: E402
_s = importlib.util.spec_from_file_location("wp_v2", Path(__file__).resolve().parent / "wp_v2.py")
V2 = importlib.util.module_from_spec(_s); _s.loader.exec_module(V2)            # noqa: E402
from wp_mockup_common import DEVICES, imread                                   # noqa: E402
import wp_build_pair as WBP                                                    # noqa: E402
from wp_plate_pilot import BOX_NAMES, REF_TAGLINE                              # noqa: E402

Image.MAX_IMAGE_PIXELS = None
POSTER_W, POSTER_H = V2.POSTER_W, V2.POSTER_H
# Mesaj arama bandi: REF_TAGLINE'in SATIRLARI, tam genislik. Kisisellestirilmis
# mesaj eski slogandan uzun olabilir; x-araligiyla kirpilirsa kutu yanlis olculur
# (yerel olcum 25 Eyl: kutu tam REF_TAGLINE sinirina oturdu, ortalama 2,5 px kaydi).
MESAJ_BANT = (0, REF_TAGLINE[1] - 120, POSTER_W, REF_TAGLINE[3] + 120)
EDISYONLAR, CIHAZLAR = V2.EDISYONLAR, V2.CIHAZLAR
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ girdi
def dosya_bul(kok, desen, ne):
    """Tek eslesme bekler; 0 veya >1 eslesmede DURur (tahmin yok)."""
    d = sorted(Path(kok).glob(desen))
    if len(d) != 1:
        raise SystemExit(f"HATA: {ne} icin {desen} -> {len(d)} eslesme: {[x.name for x in d]}")
    return d[0]


def kaynak_oku(baski_kok, plate_kok, ed):
    b = dosya_bul(baski_kok, f"*{ed.upper()}*", f"{ed} baski")
    p = dosya_bul(plate_kok, f"{ed.upper()}_24X32.*", f"{ed} plate")
    baski, plate = imread(b), imread(p)
    for ad, im in ((b.name, baski), (p.name, plate)):
        if (im.shape[1], im.shape[0]) != (POSTER_W, POSTER_H):
            raise SystemExit(f"HATA: {ad} {im.shape[1]}x{im.shape[0]}, beklenen {POSTER_W}x{POSTER_H}")
    return baski, plate, b.name, p.name


# ------------------------------------------------------------------ murekkep
def murekkep(baski, plate):
    """ESIK YOK: fark = baski - plate (isaretli), alfa = fark != 0."""
    fark = baski.astype(np.float32) - plate.astype(np.float32)
    alfa = (np.abs(fark).max(2) > 0).astype(np.float32)
    return fark, alfa


def kutular_olc(alfa):
    """Isim satiri (sol / ∞ / sag) ve mesaj kutusu - OLCULEN maskeden, poster px.

    Maske tam (esiksiz) oldugu icin kume ayrimi doku gurultusune bagli degil;
    isim/∞ ayrimi wp_v2'nin "en buyuk iki bosluk" kuralidir.
    """
    m = alfa > 0
    satir = m & (V2.kutu_maske(alfa.shape, BOX_NAMES) > 0)
    mesaj = m & (V2.kutu_maske(alfa.shape, MESAJ_BANT) > 0)
    for ad, x in (("isim satiri", satir), ("mesaj", mesaj)):
        if not x.any():
            raise SystemExit(f"HATA: {ad} murekkebi bulunamadi (baski - plate bos)")
    sol, orta, sag, bilgi = V2.uc_grup(V2.sutun_kumeleri(satir))
    ix = np.arange(alfa.shape[1])
    kutu = {}
    for ad, (x0, x1) in (("sol", sol), ("sonsuz", orta), ("sag", sag)):
        sub = satir & (ix >= x0) & (ix < x1)
        ys = np.nonzero(sub.any(1))[0]
        kutu[ad] = [int(x0), int(ys.min()), int(x1), int(ys.max()) + 1]
    kutu["mesaj"] = list(V2.bbox(mesaj))
    # PLATE'in SABIT ogeleri (halka, fuzyon sembolu) ICERMEDIGI dogrulanir:
    # wallpaper CLEAN plakasinda da yoklar, aktarilmazlarsa kapi 2 duser.
    say = {ad: int((m & (V2.kutu_maske(alfa.shape, kt) > 0)).sum())
           for ad, kt in (("halka", V2.BOX_SYMBOL_RING), ("sembol", V2.BOX_SYMBOL_CORE))}
    bos = [ad for ad, n in say.items() if n == 0]
    if bos:
        raise SystemExit(f"HATA: murekkepte {bos} yok ({say}). kisisel PLATE sabit ogeleri "
                         f"iceriyor olabilir; CLEAN plakada da yoklar, kapi 2 duser.")
    bilgi["sabit_oge_px"] = say
    return kutu, bilgi


# ------------------------------------------------------------------ uretim
def uret(ed, baski, plate, fark, alfa, temiz, plakalar, cikti, cift, kutu, aktarim, urun, rapor):
    for dev in CIHAZLAR:
        yol_p = Path(temiz) / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"
        clean = imread(yol_p)
        W, H = DEVICES[dev]
        if (clean.shape[1], clean.shape[0]) != (W, H):
            raise SystemExit(f"HATA: CLEAN plaka {yol_p.name} {clean.shape[1]}x{clean.shape[0]}, beklenen {W}x{H}")
        geom = WBP.load_geom(plakalar, ed, dev)
        A = WBP.place(alfa, dev, clean.shape, geom)[..., None]
        C = clean.astype(np.float32)
        if aktarim == "fark":
            out_f = C + WBP.place(fark, dev, clean.shape, geom)
        else:
            out_f = A * WBP.place(baski.astype(np.float32), dev, clean.shape, geom) + (1 - A) * C
        out = np.clip(np.round(out_f), 0, 255).astype(np.uint8)
        ad = f"AstroLove_{cift}_{ed}_{dev}.jpg"
        Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).save(Path(cikti) / ad, "JPEG",
                                                                   quality=95, subsampling=0)
        geri = imread(Path(cikti) / ad)
        dis = A[..., 0] <= 0
        d_out = np.abs(out.astype(np.int16) - clean.astype(np.int16)).max(2)
        k1 = {"gecti": bool(d_out[dis].max() == 0), "maks_fark": int(d_out[dis].max()),
              "jpeg_sonrasi": int(np.abs(geri.astype(np.int16) - clean.astype(np.int16)).max(2)[dis].max()),
              "piksel": int(dis.sum())}
        mb = V2.kirp(V2.cihaz_kutusu(kutu["mesaj"], dev, geom), W, H, 4)
        b0, b1 = max(mb[1] - 8, 0), min(mb[3] + 8, H)
        bd = d_out[b0:b1][dis[b0:b1]]
        ek5 = {"bant": [int(b0), int(b1)], "murekkep_disi_maks_fark": int(bd.max()) if bd.size else 0,
               "piksel": int(bd.size), "gecti": bool((bd.max() if bd.size else 0) == 0)}
        # TANI (kapi degil): kisisel PLATE ile CLEAN plaka ne kadar ayri -> hale riski
        PL = WBP.place(plate.astype(np.float32), dev, clean.shape, geom)
        ring = (A[..., 0] > 0) & (A[..., 0] < 1)
        if ring.any():
            hv = np.abs(PL - C).max(2)[ring]
            halo = {"medyan": round(float(np.median(hv)), 1), "p99": round(float(np.percentile(hv, 99)), 1),
                    "maks": round(float(hv.max()), 1), "px": int(hv.size)}
        else:
            halo = {"medyan": 0.0, "p99": 0.0, "maks": 0.0, "px": 0}
        urun[(ed, dev)] = dict(yol=str(Path(cikti) / ad), plaka=str(yol_p), geom=geom, kapi1=k1, ek5=ek5)
        rapor.append({"edisyon": ed, "cihaz": dev, "dosya": ad, "aktarim": aktarim,
                      "kapi1_maske_disi": k1, "ek5_mesaj_bandi": ek5,
                      "tani_plate_clean_kenar_farki": halo, "kutular": kutu})
        log(f"{ed} {dev}: maske disi {k1['maks_fark']} (JPEG {k1['jpeg_sonrasi']}) | "
            f"mesaj bandi {ek5['murekkep_disi_maks_fark']} | tani hale medyan {halo['medyan']} p99 {halo['p99']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--baski", required=True, help="kisisel ISIMLI 24x32 baski dosyalari (edisyon basina 1)")
    ap.add_argument("--plate", required=True, help="kisisel PLATE: <EDISYON>_24X32.png")
    ap.add_argument("--temiz", required=True, help="PLATE_<ED>_<DEV>_CLEAN.png")
    ap.add_argument("--plakalar", default="", help="GEOM_<ED>_<DEV>.json (yoksa birim)")
    ap.add_argument("--orijinal", default="", help="kapi 2 icin canli wallpaper'lar")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--cift", default="Aries_Leo")
    ap.add_argument("--aktarim", choices=("fark", "maske"), default="fark")
    ap.add_argument("--edisyonlar", default=",".join(EDISYONLAR))
    ap.add_argument("--sadece-olcum", action="store_true")
    a = ap.parse_args(argv)
    ed_list = [e.strip() for e in a.edisyonlar.split(",") if e.strip()]
    cikti = Path(a.cikti); cikti.mkdir(parents=True, exist_ok=True)

    # --- 1. ASAMA: tum edisyonlar once OLCULUR (uretim yok) --------------
    olcum = {}
    for ed in ed_list:
        baski, plate, bn, pn = kaynak_oku(a.baski, a.plate, ed)
        fark, alfa = murekkep(baski, plate)
        kutu, bilgi = kutular_olc(alfa)
        olcum[ed] = {"baski": bn, "plate": pn, "kutular": kutu, "kume": bilgi,
                     "murekkep_px": int((alfa > 0).sum())}
        log(f"OLCUM {ed}: kume={json.dumps(bilgi)}")
        log(f"       kutular={json.dumps(kutu)} murekkep_px={olcum[ed]['murekkep_px']}")
        del baski, plate, fark, alfa
    (cikti / "WP_SIPARIS_OLCUM.json").write_text(json.dumps(olcum, indent=1))
    if len(ed_list) > 1:
        sap = {k: int(np.abs(np.asarray([olcum[e]["kutular"][k] for e in ed_list]) -
                             np.asarray(olcum[ed_list[0]]["kutular"][k])).max())
               for k in ("sol", "sonsuz", "sag", "mesaj")}
        log(f"edisyonlar arasi kutu sapmasi (px): {json.dumps(sap)}")
    if a.sadece_olcum:
        log("SADECE OLCUM: uretim yapilmadi")
        return olcum, [], {}

    # --- 2. ASAMA: URETIM ------------------------------------------------
    urun, rapor = {}, []
    for ed in ed_list:
        baski, plate, _, _ = kaynak_oku(a.baski, a.plate, ed)
        fark, alfa = murekkep(baski, plate)
        uret(ed, baski, plate, fark, alfa, a.temiz, a.plakalar or a.temiz, cikti, a.cift,
             olcum[ed]["kutular"], a.aktarim, urun, rapor)
        del baski, plate, fark, alfa
    (cikti / "WP_SIPARIS_URETIM.json").write_text(json.dumps(rapor, indent=1))
    return olcum, rapor, urun


if __name__ == "__main__":
    olcum, rapor, urun = main()
    if not rapor:
        sys.exit(0)
    import sys as _s
    _a = _s.argv
    cikti = _a[_a.index("--cikti") + 1]
    orij = _a[_a.index("--orijinal") + 1] if "--orijinal" in _a else ""
    cift = _a[_a.index("--cift") + 1] if "--cift" in _a else "Aries_Leo"
    duzen = {"kutular": olcum[list(olcum)[0]]["kutular"]}
    K = V2.kapilar(urun, None, duzen, orij, cift, cikti)
    log(f"KAPILAR gecti={K['gecti']}")
    for ad in ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
               "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
        kot = [x for x in K[ad] if not x["gecti"]]
        log(f"  {ad}: {len(K[ad]) - len(kot)}/{len(K[ad])} gecti" + (f" | KALAN {kot[:3]}" if kot else ""))
    log(f"  metin_4renk: {json.dumps(K['metin_4renk'])}")
    log(f"  ek4_harf_yuksekligi: {json.dumps(K['ek4_harf_yuksekligi'])}")
    s = V2.sayfalar(urun, orij, cift, cikti)
    log(f"sayfa: {len(s)} dosya")
    _s.exit(0 if K["gecti"] else 1)
