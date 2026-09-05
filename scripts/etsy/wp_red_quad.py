#!/usr/bin/env python3
"""
KIRMIZI ISARETTEN QUAD OKUMA - 5 Eyl 2026 (Mo karari).

Olcum yapilmaz. Mo'nun mockup gorseli uzerine KIRMIZI ile cizdigi ekran
siniri tek kaynaktir: saf kirmizi pikseller (R yuksek, G/B dusuk) bulunur,
kontur cikarilir, dort kose okunur ve calib KOPYASINA yazilir. Orijinal
calib.json'a dokunulmaz.

Cizgi kalinligi icin: konturun disi ve (varsa) ici ayri okunur, iki quad'in
ortalamasi cizginin ORTA hatti sayilir.

Isaretli gorsel ekran goruntusu olabilir (kucultulmus VE kirpilmis). Bu yuzden
olcek/ofset gorsel boyutundan degil, SAHNENIN KENDISINDEN cikarilir: kirmizi
pikseller disarida birakilarak isaret ile master arasinda ozellik eslemesi
yapilir, RANSAC ile homografi kurulur ve kirmizi koseler master koordinatina
o homografi ile tasinir. Esleme tutmazsa tam kare olcegi yedek yoldur.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, log  # noqa: E402

R_MIN = 100          # kirmizi sayilmak icin en az R
FARK_MIN = 45        # R - max(G,B)
KAPAT = 5            # morfolojik kapatma cekirdegi
KUCUK_KAYMA = 6.0    # kose kaymasi bunun altindaysa DUR (Mo: 4-5 px yanlis)
EN_BUYUK = 1600      # esleme icin kucultulecek en buyuk kenar
EN_AZ_ICERIDE = 15   # RANSAC ic nokta alt siniri


def _kucult(img, en_buyuk=EN_BUYUK):
    s = min(1.0, en_buyuk / max(img.shape[:2]))
    if s >= 1.0:
        return img, 1.0
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s


def hizala_sablon(isaret, master, kirmizi):
    """Olcek+ofset'i sahnenin kendisinden bul: isaret, master icinde aranan sablondur.

    Isaretli dosya saate yakinlasmis bir kirpma olabilir; bu yol donme
    varsaymaz, coklu olcekte en yuksek korelasyonu arar."""
    yok = cv2.dilate(kirmizi, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    temiz = cv2.inpaint(isaret, yok, 3, cv2.INPAINT_TELEA)
    g_i = cv2.cvtColor(temiz, cv2.COLOR_BGR2GRAY)
    g_m = cv2.cvtColor(master, cv2.COLOR_BGR2GRAY)
    m2 = cv2.resize(g_m, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

    def ara(kaynak, hedef, olcekler):
        en = None
        for s in olcekler:
            t_ = cv2.resize(kaynak, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            if min(t_.shape[:2]) < 24 or t_.shape[0] > hedef.shape[0] or t_.shape[1] > hedef.shape[1]:
                continue
            r = cv2.matchTemplate(hedef, t_, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if en is None or mx > en[0]:
                en = (float(mx), float(s), float(loc[0]), float(loc[1]))
        return en

    def dene(kaynak, kx, ky):
        kaba = ara(kaynak, m2, np.geomspace(0.05, 2.0, 30))
        if kaba is None:
            return None
        ince = ara(kaynak, m2, np.linspace(kaba[1] * 0.88, kaba[1] * 1.12, 25))
        en = ince if ince and ince[0] >= kaba[0] else kaba
        kor, s2, x2, y2 = en
        olc = s2 / 0.5                  # isaret -> master tam cozunurluk olcegi
        ox, oy = 2.0 * x2 - olc * kx, 2.0 * y2 - olc * ky
        return kor, olc, ox, oy

    en_iyi = dene(g_i, 0.0, 0.0)
    if en_iyi is None:
        log("  sablon: uygun olcek yok")
        return None, 0.0
    if en_iyi[0] < 0.6:                 # ekran goruntusunde arayuz seridi olabilir
        h, w = g_i.shape[:2]
        kx, ky = int(w * 0.2), int(h * 0.2)
        orta = dene(g_i[ky:h - ky, kx:w - kx], kx, ky)
        if orta and orta[0] > en_iyi[0]:
            log(f"  sablon: orta kirpma daha iyi ({orta[0]:.3f} > {en_iyi[0]:.3f})")
            en_iyi = orta
    korelasyon, olc, ox, oy = en_iyi
    log(f"  sablon eslemesi: olcek {olc:.4f}, ofset ({ox:.1f}, {oy:.1f}), korelasyon {korelasyon:.3f}")
    H = np.array([[olc, 0.0, ox], [0.0, olc, oy], [0.0, 0.0, 1.0]], np.float64)
    return H, korelasyon


def homografi(isaret, master, kirmizi):
    """isaret -> master donusumu (sahne icerigine gore, gorsel boyutuna gore degil)."""
    yok = cv2.dilate(kirmizi, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    m_isaret = cv2.bitwise_not(yok)
    a, sa = _kucult(cv2.cvtColor(isaret, cv2.COLOR_BGR2GRAY))
    b, sb = _kucult(cv2.cvtColor(master, cv2.COLOR_BGR2GRAY))
    ma = cv2.resize(m_isaret, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST)
    try:
        det = cv2.SIFT_create(nfeatures=6000)
    except AttributeError:
        det = cv2.ORB_create(nfeatures=6000)
    ka, da = det.detectAndCompute(a, ma)
    kb, db = det.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 10 or len(kb) < 10:
        log("  esleme: yeterli ozellik yok")
        return None, 0
    norm = cv2.NORM_L2 if da.dtype == np.float32 else cv2.NORM_HAMMING
    esler = cv2.BFMatcher(norm).knnMatch(da, db, k=2)
    iyi = [m for m, n in (e for e in esler if len(e) == 2) if m.distance < 0.75 * n.distance]
    log(f"  esleme: {len(ka)} + {len(kb)} nokta, {len(iyi)} iyi es")
    if len(iyi) < EN_AZ_ICERIDE:
        return None, len(iyi)
    src = np.float32([ka[m.queryIdx].pt for m in iyi]).reshape(-1, 1, 2) / sa
    dst = np.float32([kb[m.trainIdx].pt for m in iyi]).reshape(-1, 1, 2) / sb
    H, ic = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    n_ic = int(ic.sum()) if ic is not None else 0
    log(f"  homografi ic nokta: {n_ic}")
    if H is None or n_ic < EN_AZ_ICERIDE:
        return None, n_ic
    return H, n_ic


def renk_maske(img, renk="kirmizi"):
    """kirmizi: R yuksek, G/B dusuk. yesil: G yuksek, R dusuk (turkuaz dahil)."""
    b, g, r = (img[..., i].astype(np.int16) for i in range(3))
    if renk == "kirmizi":
        m = (r >= R_MIN) & ((r - np.maximum(g, b)) >= FARK_MIN)
    else:
        m = (g >= 90) & ((g - r) >= FARK_MIN)
    m = m.astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KAPAT, KAPAT))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)


def kirmizi_maske(img):
    return renk_maske(img, "kirmizi")


def quad_oku(maske, ad):
    """Cizginin ORTA hattini veren dort kose (dis ve ic konturun ortalamasi)."""
    say = int((maske > 0).sum())
    log(f"{ad} piksel: {say}")
    if say < 200:
        return None
    cnts, hier = cv2.findContours(maske, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        log(f"  {ad}: kontur yok")
        return None
    dis_i = max(range(len(cnts)), key=lambda i: cv2.contourArea(cnts[i]))
    q_dis, yon_dis = dort_kose(cnts[dis_i])
    log(f"  {ad} dis kontur alani {cv2.contourArea(cnts[dis_i]):.0f} px ({yon_dis})")
    cocuklar = [i for i in range(len(cnts)) if hier[0][i][3] == dis_i]
    if cocuklar:
        ic_i = max(cocuklar, key=lambda i: cv2.contourArea(cnts[i]))
        q_ic, yon_ic = dort_kose(cnts[ic_i])
        log(f"  {ad} ic kontur alani {cv2.contourArea(cnts[ic_i]):.0f} px ({yon_ic}) -> orta hat")
        return (sirala(q_dis) + sirala(q_ic)) / 2.0
    log(f"  {ad}: ic kontur yok -> dis kontur")
    return sirala(q_dis)


def dikdortgen(q):
    """Yamuklugu duzelt: merkezi ve boyu koruyarak eksene otur."""
    q = np.asarray(q, np.float64)
    x0 = (q[0][0] + q[3][0]) / 2.0
    x1 = (q[1][0] + q[2][0]) / 2.0
    y0 = (q[0][1] + q[1][1]) / 2.0
    y1 = (q[2][1] + q[3][1]) / 2.0
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)


def yaz_quad(ad, q):
    log(f"  {ad}: {[[round(float(x), 1), round(float(y), 1)] for x, y in q]}")


def kaymalar(q1, q2):
    return [round(math.hypot(q1[i][0] - q2[i][0], q1[i][1] - q2[i][1]), 2) for i in range(4)]


def dort_kose(cnt):
    cev = cv2.arcLength(cnt, True)
    for eps in np.arange(0.005, 0.12, 0.005):
        ap = cv2.approxPolyDP(cnt, eps * cev, True)
        if len(ap) == 4:
            return ap.reshape(4, 2).astype(np.float64), f"approxPolyDP eps={eps:.3f}"
    kutu = cv2.boxPoints(cv2.minAreaRect(cnt))
    return kutu.astype(np.float64), "minAreaRect"


def sirala(p):
    p = np.asarray(p, np.float64)
    s, d = p.sum(1), (p[:, 0] - p[:, 1])
    return np.array([p[np.argmin(s)], p[np.argmax(d)], p[np.argmax(s)], p[np.argmin(d)]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--isaret", required=True, help="Mo'nun kirmizi isaretli gorseli")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True, help="calib ekran id")
    ap.add_argument("--out-calib", required=True)
    ap.add_argument("--kanit", default="", help="isaretli quad ciziminin yazilacagi jpg")
    ap.add_argument("--dik", action="store_true", help="yamuklugu duzelt: quad'i eksene otur (merkez/boy korunur)")
    ap.add_argument("--frame-top-quad", type=int, default=-1,
                    help="verilirse ekrana cerceve-ustte + delik=quad bayragi yazilir (deger: disari px)")
    ap.add_argument("--calib-json", default="", help="taban calib dosyasi (bos: <calib>/calib.json)")
    a = ap.parse_args()

    cfg = SCENES[a.scene]
    src = cfg.get("calib_from", a.scene)
    master = imread(Path(a.masters) / cfg["master"])
    im = imread(Path(a.isaret))
    mh, mw = master.shape[:2]
    ih, iw = im.shape[:2]
    log(f"isaret {iw}x{ih}, master {mw}x{mh}")

    m = kirmizi_maske(im)
    say = int((m > 0).sum())
    log(f"kirmizi piksel: {say}")
    if say < 200:
        log("DUR: kirmizi cizgi bulunamadi")
        return 3

    cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        log("DUR: kontur yok")
        return 3
    dis_i = max(range(len(cnts)), key=lambda i: cv2.contourArea(cnts[i]))
    q_dis, yon_dis = dort_kose(cnts[dis_i])
    log(f"dis kontur alani {cv2.contourArea(cnts[dis_i]):.0f} px ({yon_dis})")
    cocuklar = [i for i in range(len(cnts)) if hier[0][i][3] == dis_i]
    if cocuklar:
        ic_i = max(cocuklar, key=lambda i: cv2.contourArea(cnts[i]))
        q_ic, yon_ic = dort_kose(cnts[ic_i])
        log(f"ic kontur alani {cv2.contourArea(cnts[ic_i]):.0f} px ({yon_ic}) -> orta hat")
        quad = (sirala(q_dis) + sirala(q_ic)) / 2.0
    else:
        log("ic kontur yok -> dis kontur kullanildi")
        quad = sirala(q_dis)

    log(f"  isaret koordinatinda quad: {[[round(float(x),1), round(float(y),1)] for x, y in quad]}")
    H, n_ic = homografi(im, master, m)
    kor = 0.0
    if H is None:
        H, kor = hizala_sablon(im, master, m)
        if H is not None and kor < 0.45:
            log(f"DUR: sablon korelasyonu dusuk ({kor:.3f}), hizalama guvenilir degil")
            H = None
    if H is not None:
        quad = cv2.perspectiveTransform(quad.reshape(-1, 1, 2).astype(np.float64), H).reshape(4, 2)
        olc = math.sqrt(abs(np.linalg.det(H[:2, :2])))
        nasil = f"ozellik eslemesi (ic nokta {n_ic})" if n_ic >= EN_AZ_ICERIDE else f"sablon eslemesi (korelasyon {kor:.3f})"
        log(f"  hizalama: {nasil}, ortalama olcek {olc:.4f}")
    else:
        sx, sy = mw / iw, mh / ih
        if abs(sx - sy) / max(sx, sy) > 0.01:
            log("DUR: sahne eslemesi kurulamadi ve en-boy orani master ile uyusmuyor")
            return 3
        quad = np.array([[float(x) * sx, float(y) * sy] for x, y in quad])
        log(f"  hizalama: YEDEK YOL - tam kare olcegi {sx:.4f}")
    if a.dik:
        yamuk = quad.copy()
        quad = dikdortgen(quad)
        log(f"  yamuk quad: {[[round(float(x), 1), round(float(y), 1)] for x, y in yamuk]}")
        log(f"  dik quad  : {[[round(float(x), 1), round(float(y), 1)] for x, y in quad]} "
            f"(yamuk->dik kose kaymasi {kaymalar(yamuk, quad)} px)")
    quad_r = [[round(float(x), 1), round(float(y), 1)] for x, y in quad]

    calib = json.loads(Path(a.calib_json or (Path(a.calib) / "calib.json")).read_text())
    ekranlar = calib["scenes"][src]["screens"]
    hedef = next((s for s in ekranlar if int(s["id"]) == a.screen), None)
    if hedef is None:
        log(f"DUR: {src} sahnesinde {a.screen} numarali ekran yok")
        return 3
    eski = np.asarray(hedef["quad"], np.float64)
    kayma = [round(math.hypot(quad[i][0] - eski[i][0], quad[i][1] - eski[i][1]), 2) for i in range(4)]
    log(f"\n{a.scene}/{a.screen} {hedef['device']}")
    log(f"  eski quad : {[[round(float(x),1), round(float(y),1)] for x, y in eski]}")
    log(f"  yeni quad : {quad_r}")
    log(f"  kose kaymasi (TL,TR,BR,BL): {kayma} px | en buyuk {max(kayma)} px")

    if a.kanit:
        kan = master.copy()
        cv2.polylines(kan, [np.int32(eski)], True, (255, 0, 0), 3)
        cv2.polylines(kan, [np.int32(quad)], True, (0, 0, 255), 3)
        cv2.imwrite(a.kanit, kan, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {a.kanit} (mavi eski, kirmizi yeni)")

    if max(kayma) < KUCUK_KAYMA:
        log(f"\nDUR: en buyuk kose kaymasi {max(kayma)} px (< {KUCUK_KAYMA}). "
            "Kirmizi kontur eski quad ile ayni yeri gosteriyor, bir sey yanlis.")
        return 4

    hedef["quad"] = quad_r
    if a.frame_top_quad >= 0:
        hedef["frame_top"] = {"disari": a.frame_top_quad, "delik": "quad"}
        log(f"  frame_top: disari {a.frame_top_quad} px, delik = quad (yalniz bu ekran)")
    Path(a.out_calib).write_text(json.dumps(calib, indent=1))
    log(f"\n{a.out_calib}: {a.scene}/{a.screen} quad'i guncellendi (orijinale dokunulmadi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
