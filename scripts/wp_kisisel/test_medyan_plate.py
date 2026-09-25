#!/usr/bin/env python3
"""kisisel PLATE = 78 ciftin MEDYANI durumunun yerel testi (Actions yok, Drive yok).

Mo notu (25 Eyl): medyanda HALKA, muhtemelen ∞ ve ESKI SLOGAN plate'te KALIR.
Sonuc: "baski - plate" farkinda
  (a) HALKA YOK      -> halka halkali gece plakasindan alinmali
                        (WP_PLATES/PLATE_<ED>_<DEV>.png - ..._CLEAN.png, halka bandi)
  (b) ∞ ve MESAJ CIFT -> eski konum NEGATIF, yeni konum POZITIF.
                        Negatif aktarilirsa CLEAN plakaya hayalet (leke) basilir.

Test iki kosu yapar:
  gecir : duzeltme YOK  -> hayalet OLCULEBILIR olmali (aksi halde test degersiz)
  birak : duzeltme VAR  -> hayalet bolgesinde cikti = CLEAN (fark 0), halka var
"""
import importlib.util, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
_t = importlib.util.spec_from_file_location("test_siparis", KOK / "wp_kisisel" / "test_siparis.py")
TS = importlib.util.module_from_spec(_t); _t.loader.exec_module(TS)
SP, V2 = TS.SP, TS.V2
import wp_build_pair as WBP                                                   # noqa: E402
from wp_mockup_common import DEVICES                                          # noqa: E402
from wp_plate_pilot import (BOX_NAMES, INK_RGB, REF_TAGLINE, RING_ELLIPSE,    # noqa: E402
                            RING_LINE_PX, RING_TIP_Y)
Image.MAX_IMAGE_PIXELS = None
W, H = SP.POSTER_W, SP.POSTER_H
DX_ESKI = -197          # eski ∞ konumu (yeni konuma gore), olculen kaydirmayla ayni buyukluk
W_INF, G, CAP = 605, 424, 266


def katman(ed, ogeler, P12=None, P6=None, P7=None, kp=None, isimler=None, mesaj=None):
    """Istenen ogelerden antialias RGBA murekkep katmani kurar."""
    r, g, b = INK_RGB[ed]
    L = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(L)
    if "halka" in ogeler:
        cx, cy, ax, ay = RING_ELLIPSE
        d.ellipse([cx - ax, cy - ay, cx + ax, cy + ay], outline=255, width=int(RING_LINE_PX))
    if "sembol" in ogeler:
        d.ellipse([2600, 3000, 4600, 4800], outline=255, width=40)
        d.ellipse([2900, 5900, 3300, 6300], outline=255, width=30)
        d.ellipse([3900, 5900, 4300, 6300], outline=255, width=30)
    a = np.asarray(L).copy()
    a[RING_TIP_Y + 1:, :] = 0 if "halka" in ogeler and "sembol" not in ogeler else a[RING_TIP_Y + 1:, :]
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = r, g, b
    rgba[..., 3] = a
    out = Image.fromarray(rgba, "RGBA")
    prof = np.tile(np.array([[r, g, b]], np.float32), (400, 1))
    ymid = (BOX_NAMES[1] + BOX_NAMES[3]) // 2

    def inf_ciz(x):
        inf = Image.new("RGBA", (W_INF, 190), (0, 0, 0, 0))
        di = ImageDraw.Draw(inf)
        di.ellipse([5, 15, 300, 175], outline=(r, g, b, 255), width=34)
        di.ellipse([305, 15, 600, 175], outline=(r, g, b, 255), width=34)
        out.alpha_composite(inf, (x, ymid - 95))

    pl = {k: P12.plaka(isimler[k], prof, CAP, 1.0)[0] for k in ("sol", "sag")} if "isim" in ogeler else {}
    if "isim" in ogeler:
        ws = {k: (lambda t: t[1] - t[0])(V2.plaka_murekkep(pl[k])) for k in pl}
        x = int(round(W / 2 - (ws["sol"] + G + W_INF + G + ws["sag"]) / 2))
        m0, m1 = V2.plaka_murekkep(pl["sol"])
        out.alpha_composite(pl["sol"].crop((m0, 0, m1, pl["sol"].height)), (x, ymid - pl["sol"].height // 2))
        x_inf = x + ws["sol"] + G
        x2 = x_inf + W_INF + G
        m0, m1 = V2.plaka_murekkep(pl["sag"])
        out.alpha_composite(pl["sag"].crop((m0, 0, m1, pl["sag"].height)), (x2, ymid - pl["sag"].height // 2))
    else:
        x_inf = int(round(W / 2 - W_INF / 2))
    if "inf_yeni" in ogeler:
        inf_ciz(x_inf)
    if "inf_eski" in ogeler:
        inf_ciz(x_inf + DX_ESKI)
    for ad, metin in (("mesaj", mesaj), ("slogan", "Two Souls · One Bond")):
        if ad not in ogeler:
            continue
        fp = kp.FONT_DIR / P6.TAG_FONT
        punto = P6.cap_punto(fp, P6.TAG_W, 219)
        cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, metin)
        p1, _ = P7.kuyruk_duzlestir(prof)
        tg = P7.altin_sekil(cr, p1, (cu, ct))
        ty = (REF_TAGLINE[1] + REF_TAGLINE[3]) // 2 - tg.height // 2
        out.alpha_composite(tg, (int(round(W / 2 - tg.width / 2)), ty))
    return out, (x_inf if "inf_yeni" in ogeler or "inf_eski" in ogeler else None)


def kur(T, ed, kis):
    P6, P7, P12, kp = V2.kisisel_kur(kis)
    isimler, mesaj = {"sol": "EMILY", "sag": "JAMES"}, "It Began With a Kiss in the Rain"
    zemin = TS.zemin_uret(ed, 100)
    # kisisel PLATE (78 ciftin medyani): halka + ESKI ∞ + ESKI SLOGAN
    mk_plate, _ = katman(ed, {"halka", "inf_eski", "slogan"}, P12, P6, P7, kp, isimler, mesaj)
    # baski: halka + sembol + glifler + YENI ∞ + isimler + YENI MESAJ
    mk_baski, x_inf = katman(ed, {"halka", "sembol", "isim", "inf_yeni", "mesaj"},
                             P12, P6, P7, kp, isimler, mesaj)
    # yalniz halka (gece plakasi icin) ve isimsiz murekkep (orijinal referans)
    mk_halka, _ = katman(ed, {"halka"}, P12, P6, P7, kp, isimler, mesaj)
    mk_ref, _ = katman(ed, {"halka", "sembol"}, P12, P6, P7, kp, isimler, mesaj)
    for d in ("baski", "plate", "temiz", "gece", "geom", "orijinal", "out_gecir", "out_birak"):
        (T / d).mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(T / "plate" / f"{ed.upper()}_24X32.png"), TS.bindir(zemin, mk_plate))
    cv2.imwrite(str(T / "baski" / f"SIPARIS_ARIES_LEO_{ed.upper()}_24X32.png"), TS.bindir(zemin, mk_baski))
    for dev in SP.CIHAZLAR:
        dw, dh = DEVICES[dev]
        clean = TS.zemin_uret(ed, 500, dw, dh, 90)
        cv2.imwrite(str(T / "temiz" / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"), clean)
        for ad, mk in (("gece", mk_halka), ("orijinal", mk_ref)):
            f = np.asarray(mk).astype(np.float32)
            A = WBP.place((f[..., 3] / 255.0).astype(np.float32), dev, clean.shape, None)[..., None]
            P = WBP.place((f[..., :3][..., ::-1] * (f[..., 3:4] / 255.0)).astype(np.float32),
                          dev, clean.shape, None)
            o = np.clip(np.round(P + (1 - A) * clean.astype(np.float32)), 0, 255).astype(np.uint8)
            if ad == "gece":
                cv2.imwrite(str(T / "gece" / f"PLATE_{ed.upper()}_{dev.upper()}.png"), o)
            else:
                Image.fromarray(cv2.cvtColor(o, cv2.COLOR_BGR2RGB)).save(
                    T / "orijinal" / f"AstroLove_Aries_Leo_{ed}_{dev}.jpg", "JPEG", quality=95, subsampling=0)
    return x_inf


def hayalet_kutusu(x_inf):
    """Eski ∞'nin YENI ∞ ile ORTUSMEYEN kismi (hayalet burada olculur).

    Eski ve yeni ∞ kutulari DX_ESKI kadar kaydik; ortusen bolgede YENI murekkep
    mesru olarak CLEAN'den farklidir, oraya bakmak olcumu gecersiz kilar.
    """
    ymid = (BOX_NAMES[1] + BOX_NAMES[3]) // 2
    x0 = x_inf + DX_ESKI
    return {"eski_sonsuz": [x0, ymid - 95, x_inf, ymid + 95],       # yalniz ortusmeyen sol parca
            "eski_slogan": list(SP.MESAJ_BANT)}


def olc_hayalet(T, alt, ed, kutular):
    """Eski ∞ kutusunda, YENI murekkebin disinda kalan bolgede cikti != CLEAN mi?"""
    sonuc = []
    for dev in SP.CIHAZLAR:
        im = cv2.imread(str(T / alt / f"AstroLove_Aries_Leo_{ed}_{dev}.jpg"))
        clean = cv2.imread(str(T / "temiz" / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"))
        kd = V2.kirp(V2.cihaz_kutusu(kutular["eski_sonsuz"], dev, None), *DEVICES[dev][::1], 0)
        x0, y0, x1, y1 = kd
        d = np.abs(im[y0:y1, x0:x1].astype(np.int16) - clean[y0:y1, x0:x1].astype(np.int16)).max(2)
        sonuc.append({"cihaz": dev, "kutu": kd, "maks_fark": int(d.max()), "px_fark": int((d > 8).sum())})
    return sonuc


def main():
    t0 = time.time()
    kis = sys.argv[1] if len(sys.argv) > 1 else "."
    T = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/wp_medyan_test")
    ed = "Midnight_Blue"
    x_inf = kur(T, ed, kis)
    kutular = hayalet_kutusu(x_inf)
    print(f"[kur {time.time() - t0:.1f}s] eski ∞ kutusu (poster): {kutular['eski_sonsuz']}")

    ortak = ["--baski", str(T / "baski"), "--plate", str(T / "plate"), "--temiz", str(T / "temiz"),
             "--plakalar", str(T / "geom"), "--orijinal", str(T / "orijinal"),
             "--cift", "Aries_Leo", "--edisyonlar", ed, "--halka", str(T / "gece")]
    rapor = {}
    for mod, alt in (("gecir", "out_gecir"), ("birak", "out_birak")):
        olcum, rap, urun = SP.main(ortak + ["--cikti", str(T / alt), "--hayalet", mod])
        h = olc_hayalet(T, alt, ed, kutular)
        rapor[mod] = {"tani": olcum[ed]["tani_murekkep"], "hayalet": h,
                      "halka_px": [r["halka_px"] for r in rap],
                      "kapi1": [r["kapi1_maske_disi"]["maks_fark"] for r in rap]}
        K = V2.kapilar(urun, None, {"kutular": olcum[ed]["kutular"]}, str(T / "orijinal"),
                       "Aries_Leo", str(T / alt))
        rapor[mod]["halka_sembol"] = K["halka_sembol"]
        rapor[mod]["kapilar_gecti"] = K["gecti"]

    print("\n--- TANI (baski - plate isaret ayrimi) ---")
    print(json.dumps(rapor["birak"]["tani"], ensure_ascii=False))
    print("\n--- ESKI ∞ KUTUSUNDA CIKTI vs CLEAN ---")
    for mod in ("gecir", "birak"):
        for h in rapor[mod]["hayalet"]:
            print(f"  hayalet={mod:6s} {h['cihaz']:8s} maks_fark={h['maks_fark']:4d} "
                  f"fark_px(>8)={h['px_fark']}")
    print("\n--- HALKA ---")
    for mod in ("gecir", "birak"):
        hs = [x for x in rapor[mod]["halka_sembol"] if x["oge"] == "halka"]
        print(f"  hayalet={mod:6s} halka_px={rapor[mod]['halka_px']} | "
              f"kapi2 halka: {[(x['cihaz'], x['sapma_px'], x['gecti']) for x in hs]}")
    print(f"\n  kapi1 maks fark: gecir={rapor['gecir']['kapi1']} birak={rapor['birak']['kapi1']}")
    g = rapor["gecir"]["hayalet"]; b = rapor["birak"]["hayalet"]
    ok_gecir = all(x["px_fark"] > 0 for x in g)          # duzeltmesiz hayalet GORUNMELI
    ok_birak = all(x["maks_fark"] == 0 for x in b)       # duzeltmeyle hayalet YOK
    ok_halka = all(x["gecti"] for x in rapor["birak"]["halka_sembol"] if x["oge"] == "halka")
    print(f"\n  A) duzeltmesiz hayalet olculebiliyor: {ok_gecir}")
    print(f"  B) duzeltmeyle hayalet yok (fark 0)  : {ok_birak}")
    print(f"  C) halka gece plakasindan, kapi 2 ok : {ok_halka}")
    print(f"  toplam {time.time() - t0:.1f}s")
    return 0 if (ok_gecir and ok_birak and ok_halka) else 1


if __name__ == "__main__":
    sys.exit(main())
