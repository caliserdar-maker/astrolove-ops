#!/usr/bin/env python3
"""kisisel PLATE = 78 ciftin MEDYANI durumunun yerel testi (Actions yok, Drive yok).

kisisel OLCUMU (kisisel_RAPOR_0000, GOREV_0001/0002): plate'te ESKI SLOGAN VAR,
∞ YOK, DIS HALKA VAR, isim satiri temiz (%0,02 artik). Senaryo buna gore kurulur.
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


def isim_artigi(mk, ed, oran=0.0002, tohum=7):
    """Medyanin isim satirinda biraktigi zayif artik (kisisel olcumu: %0,02)."""
    a = np.asarray(mk).copy()
    rng = np.random.default_rng(tohum)
    x0, y0, x1, y1 = BOX_NAMES
    n = int(oran * (x1 - x0) * (y1 - y0))
    xs = rng.integers(x0, x1, n); ys = rng.integers(y0, y1, n)
    a[ys, xs, 3] = np.maximum(a[ys, xs, 3], rng.integers(8, 26, n).astype(np.uint8))
    return Image.fromarray(a, "RGBA")


def kur(T, ed, kis):
    """Olculen gercege gore: plate = zemin + HALKA + ESKI SLOGAN (+ isim artigi),
    baski = zemin + halka + sembol + glifler + ∞ + isimler + YENI MESAJ."""
    P6, P7, P12, kp = V2.kisisel_kur(kis)
    isimler, mesaj = {"sol": "EMILY", "sag": "JAMES"}, "It Began With a Kiss in the Rain"
    zemin = TS.zemin_uret(ed, 100)
    mk_plate, _ = katman(ed, {"halka", "slogan"}, P12, P6, P7, kp, isimler, mesaj)
    mk_plate = isim_artigi(mk_plate, ed)
    mk_baski, x_inf = katman(ed, {"halka", "sembol", "isim", "inf_yeni", "mesaj"},
                             P12, P6, P7, kp, isimler, mesaj)
    mk_halka, _ = katman(ed, {"halka"}, P12, P6, P7, kp, isimler, mesaj)
    mk_ref, _ = katman(ed, {"halka", "sembol"}, P12, P6, P7, kp, isimler, mesaj)
    for d in ("baski", "plate", "temiz", "gece", "geom", "orijinal",
              "out_uzaklik", "out_izdusum", "out_gecir"):
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
    # HAYALET YER GERCEGI: plate'te murekkep VAR, baskida YOK -> aktarilirsa leke
    hmask = ((np.asarray(mk_plate)[..., 3] > 0) & (np.asarray(mk_baski)[..., 3] == 0))
    return x_inf, hmask.astype(np.float32)


def hayalet_kutusu(x_inf):
    """Eski ∞'nin YENI ∞ ile ORTUSMEYEN kismi (hayalet burada olculur).

    Eski ve yeni ∞ kutulari DX_ESKI kadar kaydik; ortusen bolgede YENI murekkep
    mesru olarak CLEAN'den farklidir, oraya bakmak olcumu gecersiz kilar.
    """
    ymid = (BOX_NAMES[1] + BOX_NAMES[3]) // 2
    x0 = x_inf + DX_ESKI
    return {"eski_sonsuz": [x0, ymid - 95, x_inf, ymid + 95],       # yalniz ortusmeyen sol parca
            "eski_slogan": list(SP.MESAJ_BANT)}


def olc_hayalet(T, alt, ed, hmask):
    """Hayalet bolgesinde (plate'te murekkep, baskida yok) cikti CLEAN'den farkli mi?"""
    sonuc = []
    for dev in SP.CIHAZLAR:
        im = cv2.imread(str(T / alt / f"AstroLove_Aries_Leo_{ed}_{dev}.jpg"))
        clean = cv2.imread(str(T / "temiz" / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"))
        Ah = WBP.place(hmask, dev, clean.shape, None) > 0.5
        d = np.abs(im.astype(np.int16) - clean.astype(np.int16)).max(2)
        sonuc.append({"cihaz": dev, "bolge_px": int(Ah.sum()),
                      "maks_fark": int(d[Ah].max()) if Ah.any() else 0,
                      "px_fark": int((d[Ah] > 8).sum()) if Ah.any() else 0})
    return sonuc


def main():
    t0 = time.time()
    kis = sys.argv[1] if len(sys.argv) > 1 else "."
    T = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/wp_medyan_test")
    ed = "Midnight_Blue"
    x_inf, hmask = kur(T, ed, kis)
    print(f"[kur {time.time() - t0:.1f}s] hayalet yer gercegi: {int(hmask.sum())} poster px "
          f"(plate'te murekkep, baskida yok)")

    ortak = ["--baski", str(T / "baski"), "--plate", str(T / "plate"), "--temiz", str(T / "temiz"),
             "--plakalar", str(T / "geom"), "--orijinal", str(T / "orijinal"),
             "--cift", "Aries_Leo", "--edisyonlar", ed, "--halka", str(T / "gece")]
    kosular = [("uzaklik", "uzaklik", "birak"), ("izdusum", "izdusum", "birak"),
               ("gecir", "uzaklik", "gecir")]
    rapor = {}
    for alt, isaret, hay in kosular:
        olcum, rap, urun = SP.main(ortak + ["--cikti", str(T / f"out_{alt}"),
                                            "--isaret", isaret, "--hayalet", hay])
        # olcum anahtari "<CIFT>|<EDISYON>", urun ise cift bazli (--ciftler ile geldi,
        # commit 1a6bda2); bu test o degisiklikten beri KeyError veriyordu.
        ak = f"Aries_Leo|{ed}"
        u = urun["Aries_Leo"] if "Aries_Leo" in urun else urun
        K = V2.kapilar(u, None, {"kutular": olcum[ak]["kutular"]}, str(T / "orijinal"),
                       "Aries_Leo", str(T / f"out_{alt}"), [ed])
        rapor[alt] = {"tani": olcum[ak]["tani_murekkep"], "kume": olcum[ak]["kume"],
                      "kutular": olcum[ak]["kutular"],
                      "hayalet": olc_hayalet(T, f"out_{alt}", ed, hmask),
                      "halka_px": [r["halka_px"] for r in rap],
                      "kapi1": [r["kapi1_maske_disi"]["maks_fark"] for r in rap],
                      "kapilar": K}

    print("\n--- TANI (baski - plate ayrimi) ---")
    for alt in ("uzaklik", "izdusum"):
        print(f"  {alt:8s}: {json.dumps(rapor[alt]['tani'], ensure_ascii=False)}")
    print("\n--- HAYALET BOLGESINDE CIKTI vs CLEAN ---")
    for alt in ("gecir", "izdusum", "uzaklik"):
        for h in rapor[alt]["hayalet"]:
            print(f"  {alt:8s} {h['cihaz']:8s} bolge={h['bolge_px']:6d} px | "
                  f"maks_fark={h['maks_fark']:4d} | fark_px(>8)={h['px_fark']}")
    print("\n--- KUME / KUTU (uzaklik) ---")
    print("  ", json.dumps(rapor["uzaklik"]["kume"], ensure_ascii=False))
    print("  ", json.dumps(rapor["uzaklik"]["kutular"]))
    print("\n--- KAPILAR (uzaklik) ---")
    K = rapor["uzaklik"]["kapilar"]
    for ad in ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
               "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
        kot = [x for x in K[ad] if not x["gecti"]]
        print(f"  {ad}: {len(K[ad]) - len(kot)}/{len(K[ad])} gecti" + (f" | KALAN {kot[:2]}" if kot else ""))
    print(f"  kapi1 maks fark: {rapor['uzaklik']['kapi1']} | halka px: {rapor['uzaklik']['halka_px']}")
    print(f"  KAPILAR gecti = {K['gecti']}")

    ok_kontrol = all(h["px_fark"] > 0 for h in rapor["gecir"]["hayalet"])
    ok_uz = all(h["maks_fark"] == 0 for h in rapor["uzaklik"]["hayalet"])
    ok_iz = all(h["maks_fark"] == 0 for h in rapor["izdusum"]["hayalet"])
    ok_halka = all(x["gecti"] for x in K["halka_sembol"] if x["oge"] == "halka")
    print(f"\n  A) kontrol (hayalet gecirilince leke olculebiliyor): {ok_kontrol}")
    print(f"  B) 3B uzaklik ile hayalet YOK (fark 0)             : {ok_uz}")
    print(f"  C) eski 1B izdusum ile hayalet YOK                 : {ok_iz}")
    print(f"  D) halka gece plakasindan, kapi 2 PASS             : {ok_halka}")
    print(f"  toplam {time.time() - t0:.1f}s")
    return 0 if (ok_kontrol and ok_uz and ok_halka) else 1


if __name__ == "__main__":
    sys.exit(main())
