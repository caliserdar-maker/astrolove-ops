#!/usr/bin/env python3
"""wp_siparis.py yerel testi (Actions yok, Drive yok).

kisisel'in 80 plate'i ve 6 testi bitene kadar gercek baski/plate dosyalari yok.
Bu test onlarin YERINE, ayni sozlesmeyi saglayan sentetik kaynak uretir:
  PLATE  = yalniz zemin (doku + yildiz), sabit oge YOK
  BASKI  = PLATE + antialias murekkep (halka, fuzyon sembolu, 2 glif, ∞,
           GERCEK kisisel-v1 render ile isimler ve mesaj)
Boylece olculen sey kodun kendisidir: maske = baski - plate (esiksiz),
kutu olcumu, afin yerlesim, 10 kapi.
"""
import importlib.util, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
_s = importlib.util.spec_from_file_location("wp_siparis", KOK / "wp_kisisel" / "wp_siparis.py")
SP = importlib.util.module_from_spec(_s); _s.loader.exec_module(SP)
V2 = SP.V2
from wp_mockup_common import DEVICES                                          # noqa: E402
from wp_plate_pilot import (BOX_NAMES, INK_RGB, REF_TAGLINE, RING_ELLIPSE,    # noqa: E402
                            RING_LINE_PX, RING_TIP_Y)
Image.MAX_IMAGE_PIXELS = None
W, H = SP.POSTER_W, SP.POSTER_H
ZEMIN = {"Midnight_Blue": (12, 22, 48), "Deep_Black": (10, 10, 12),
         "Champagne_Ivory": (238, 230, 214), "Warm_Parchment": (232, 214, 184)}


def zemin_uret(ed, tohum, w=W, h=H, yildiz=260):
    """Dokulu zemin + yildizlar (kisisel PLATE / CLEAN plaka yerine)."""
    rng = np.random.default_rng(tohum)
    r, g, b = ZEMIN[ed]
    im = np.empty((h, w, 3), np.uint8)
    dk = rng.normal(0, 4, (h // 8 + 1, w // 8 + 1, 3))
    dk = cv2.resize(dk.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    im[:] = np.clip(np.array([b, g, r], np.float32) + dk, 0, 255).astype(np.uint8)
    for _ in range(yildiz):
        x, y = int(rng.integers(20, w - 20)), int(rng.integers(20, h - 20))
        cv2.circle(im, (x, y), int(rng.integers(2, 5)), (235, 238, 245), -1, cv2.LINE_AA)
    return im


def murekkep_katmani(ed, P12, P6, P7, kp, isimler, mesaj, metin=True):
    """Antialias RGBA murekkep: halka + sembol + 2 glif + ∞ (+ isim/mesaj)."""
    r, g, b = INK_RGB[ed]
    L = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(L)
    cx, cy, ax, ay = RING_ELLIPSE
    d.ellipse([cx - ax, cy - ay, cx + ax, cy + ay], outline=255, width=int(RING_LINE_PX))
    d.ellipse([2600, 3000, 4600, 4800], outline=255, width=40)      # fuzyon sembolu
    d.ellipse([2900, 5900, 3300, 6300], outline=255, width=30)      # sol glif
    d.ellipse([3900, 5900, 4300, 6300], outline=255, width=30)      # sag glif
    a = np.asarray(L).copy()
    a[RING_TIP_Y + 1:, :] = np.minimum(a[RING_TIP_Y + 1:, :], 0)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = r, g, b
    rgba[..., 3] = a
    if not metin:
        return Image.fromarray(rgba, "RGBA")
    out = Image.fromarray(rgba, "RGBA")
    prof = np.tile(np.array([[r, g, b]], np.float32), (400, 1))
    cap, G, W_INF = 266, 424, 605
    pl = {k: P12.plaka(isimler[k], prof, cap, 1.0)[0] for k in ("sol", "sag")}
    ws = {k: (lambda t: t[1] - t[0])(V2.plaka_murekkep(pl[k])) for k in pl}
    toplam = ws["sol"] + G + W_INF + G + ws["sag"]
    x = int(round(W / 2 - toplam / 2))
    ymid = (BOX_NAMES[1] + BOX_NAMES[3]) // 2
    for k in ("sol", "inf", "sag"):
        if k == "inf":
            inf = Image.new("RGBA", (W_INF, 190), (0, 0, 0, 0))
            di = ImageDraw.Draw(inf)
            di.ellipse([5, 15, 300, 175], outline=(r, g, b, 255), width=34)
            di.ellipse([305, 15, 600, 175], outline=(r, g, b, 255), width=34)
            out.alpha_composite(inf, (x, ymid - 95)); x += W_INF + G
            continue
        m0, m1 = V2.plaka_murekkep(pl[k])
        out.alpha_composite(pl[k].crop((m0, 0, m1, pl[k].height)), (x, ymid - pl[k].height // 2))
        x += (m1 - m0) + G
    fp = kp.FONT_DIR / P6.TAG_FONT
    punto = P6.cap_punto(fp, P6.TAG_W, 219)
    cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, mesaj)
    p1, _ = P7.kuyruk_duzlestir(prof)
    tg = P7.altin_sekil(cr, p1, (cu, ct))
    ty = (REF_TAGLINE[1] + REF_TAGLINE[3]) // 2 - tg.height // 2
    out.alpha_composite(tg, (int(round(W / 2 - tg.width / 2)), ty))
    return out


def bindir(zemin_bgr, rgba):
    a = np.asarray(rgba).astype(np.float32)
    al = a[..., 3:4] / 255.0
    return np.clip(a[..., :3][..., ::-1] * al + zemin_bgr.astype(np.float32) * (1 - al), 0, 255).astype(np.uint8)


def main():
    t0 = time.time()
    kis = sys.argv[1] if len(sys.argv) > 1 else "."
    eds = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["Midnight_Blue"])
    T = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/wp_siparis_test")
    for d in ("baski", "plate", "temiz", "geom", "orijinal", "out"):
        (T / d).mkdir(parents=True, exist_ok=True)
    P6, P7, P12, kp = V2.kisisel_kur(kis)
    isimler = {"sol": "EMILY", "sag": "JAMES"}
    mesaj = "It Began With a Kiss in the Rain"
    for i, ed in enumerate(eds):
        plate = zemin_uret(ed, 100 + i)
        mk = murekkep_katmani(ed, P12, P6, P7, kp, isimler, mesaj, True)
        mk0 = murekkep_katmani(ed, P12, P6, P7, kp, isimler, mesaj, False)
        cv2.imwrite(str(T / "plate" / f"{ed.upper()}_24X32.png"), plate)
        cv2.imwrite(str(T / "baski" / f"SIPARIS_ARIES_LEO_{ed.upper()}_24X32.png"), bindir(plate, mk))
        for dev in SP.CIHAZLAR:
            dw, dh = DEVICES[dev]
            clean = zemin_uret(ed, 500 + i, dw, dh, 90)
            cv2.imwrite(str(T / "temiz" / f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"), clean)
            # "orijinal" wallpaper: ayni afin yolla, isimsiz murekkep (kapi 2 referansi)
            import wp_build_pair as WBP
            f0 = np.asarray(mk0).astype(np.float32)
            src = f0[..., :3][..., ::-1] * (f0[..., 3:4] / 255.0)
            A = WBP.place((f0[..., 3] / 255.0).astype(np.float32), dev, clean.shape, None)[..., None]
            P = WBP.place(src.astype(np.float32), dev, clean.shape, None)
            o = np.clip(np.round(P + (1 - A) * clean.astype(np.float32)), 0, 255).astype(np.uint8)
            Image.fromarray(cv2.cvtColor(o, cv2.COLOR_BGR2RGB)).save(
                T / "orijinal" / f"AstroLove_Aries_Leo_{ed}_{dev}.jpg", "JPEG", quality=95, subsampling=0)
        del plate, mk, mk0
    print(f"[kaynak {time.time() - t0:.1f}s] {len(eds)} edisyon sentetik baski+plate+CLEAN+orijinal hazir")

    argv = ["--baski", str(T / "baski"), "--plate", str(T / "plate"), "--temiz", str(T / "temiz"),
            "--plakalar", str(T / "geom"), "--orijinal", str(T / "orijinal"), "--cikti", str(T / "out"),
            "--cift", "Aries_Leo", "--edisyonlar", ",".join(eds), "--aktarim",
            sys.argv[4] if len(sys.argv) > 4 else "fark"]
    olcum, rapor, urun = SP.main(argv)
    if not rapor:
        return 0
    # olcum anahtari "<CIFT>|<EDISYON>", urun cift bazli (commit 1a6bda2)
    duzen = {"kutular": olcum[f"Aries_Leo|{eds[0]}"]["kutular"]}
    u = urun["Aries_Leo"] if "Aries_Leo" in urun else urun
    K = V2.kapilar(u, None, duzen, str(T / "orijinal"), "Aries_Leo", str(T / "out"), eds)
    for ad in ("halka_sembol", "ortalama", "kenar_payi", "ek1_mesaj_renk", "ek2_yildiz",
               "ek3_esit_bosluk", "ek4_mesaj_isimden_buyuk_degil", "ek5_mesaj_bandi"):
        kot = [x for x in K[ad] if not x["gecti"]]
        print(f"  {ad}: {len(K[ad]) - len(kot)}/{len(K[ad])} gecti" + (f" | KALAN {kot[:2]}" if kot else ""))
    print("  metin_4renk:", json.dumps(K["metin_4renk"]))
    print("  ek4_harf_yuksekligi:", json.dumps(K["ek4_harf_yuksekligi"]))
    print("  KAPILAR gecti =", K["gecti"], f"| toplam {time.time() - t0:.1f}s")
    return 0 if K["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
