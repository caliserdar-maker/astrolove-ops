#!/usr/bin/env python3
"""
KOMSU TELEFONUN TUM KASASINI KOPYALA - 5 Eyl 2026 (Mo). Yalniz verilen ekranlarda.

1) Kasa kalinligi OLCULUR (deneme 2): her kenarda quad'dan disari dogru
   9 cizgi boyunca Lab profili; duvar referansi ayni cizginin BANT-15..BANT
   ucu (kenar bazinda, raf/duvar farki sorun olmaz). Kalinlik = duvar
   referansindan ESIK'ten uzak SON piksel (medyan). Siluet = quad'in
   kenar bazinda kalinlik kadar disari otelenmisi, dis koseler ic yaricap +
   kalinlik ile yuvarlak. (Deneme 1'deki Lab-esik bolgesi duvar golgesini de
   kasa sayip 60 px'lik bandi tasiyordu -> hedefte acik dikdortgen hale.)
2) Kasa iki ESKI quad arasindaki homografiyle hedefe tasinir.
3) Hedef master KOPYASINDA hedef siluet ici tamamen degistirilir: tasinan
   siluet ici tasinan kasa (dis siluette GECIS px yumusak gecis), hedefin
   kendi siluetinden artan kisim duvardan inpaint.
4) Delik (deneme 2): kaynagin KENDI ekran maskesi homografiyle tasinir ve
   calib kopyasinda hedef ekranin maskesi olarak yazilir; render
   frame_top {delik: maske} ile deligi bu maskeden acar -> kopyalanan
   cercevenin ic kenari ile delik ayni sinir, kosede bosluk/cift kenar yok.
5) Isik: kaynak ve hedef kasa L ortalamasi; fark > L_ESIK ise tasinan kasanin
   L'si farkin yarisi kadar hedefe dogru kaydirilir (hafif).
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, _kose_yaricapi, expand_quad, hole_shape, imread, log, poly_mask_aa  # noqa: E402

ESIK = 14.0
L_ESIK = 10.0


def lab_of(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32)


def _yerel(quad):
    q = np.asarray(quad, np.float32)
    W = int(round((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2))
    H = int(round((np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2))
    Hl = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, H], [0, H]]), q)
    return W, H, Hl


def kalinlik_olc(img, quad, bant, n=9, ref=15):
    """Kenar bazinda kasa kalinligi (ust, sag, alt, sol) px ve profil ozeti.
    Her kenarda n cizgi: quad kenarindan disari normal boyunca Lab profili.
    Duvar referansi = ayni cizginin [bant-ref, bant] ucunun medyani.
    Kalinlik = referanstan uzakligi ESIK'i asan son indeks + 1; cizgilerin medyani."""
    lab = lab_of(img)
    q = np.asarray(quad, np.float64)
    c = q.mean(axis=0)
    sonuc, detay = [], []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        d = b - a; L = float(np.linalg.norm(d)) or 1.0
        nrm = np.array([d[1], -d[0]]) / L
        if np.dot((a + b) / 2 - c, nrm) < 0:
            nrm = -nrm
        ks = []
        for f in np.linspace(0.2, 0.8, n):
            p = a + d * f
            prof = []
            for t in range(0, bant + 1):
                x = int(round(p[0] + nrm[0] * t)); y = int(round(p[1] + nrm[1] * t))
                if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
                    prof.append(lab[y, x])
            prof = np.asarray(prof)
            if len(prof) < bant:
                continue
            duvar = np.median(prof[bant - ref:], axis=0)
            uzak = np.linalg.norm(prof - duvar, axis=1) > ESIK
            idx = np.where(uzak[:bant - ref])[0]
            ks.append(int(idx[-1]) + 1 if len(idx) else 0)
        k = int(round(float(np.median(ks)))) if ks else 0
        sonuc.append(k); detay.append(sorted(ks))
    return sonuc, detay


def siluet(img, quad, bant, shape, soft=None, kal=None, up=4):
    """Kasa siluet maskesi (quad disi): kenar bazinda olculen kalinlik kadar
    disari otelenmis, dis koseleri (ic yaricap + kalinlik) yuvarlak dikdortgen.
    Donus: (kasa maskesi uint8, kalinliklar [ust,sag,alt,sol], dis yaricaplar)."""
    if kal is None:
        kal, _ = kalinlik_olc(img, quad, bant)
    kal = [max(1, min(int(k), bant)) for k in kal]
    W, H, Hl = _yerel(quad)
    if soft is not None:
        yerel = cv2.warpPerspective(soft, np.linalg.inv(Hl.astype(np.float64)), (W, H), flags=cv2.INTER_LINEAR)
        _, ric = _kose_yaricapi(yerel)
    else:
        ric = [0.0, 0.0, 0.0, 0.0]
    ku, ksag, ka, ksol = kal
    Wd, Hd = W + ksol + ksag, H + ku + ka
    rs = [ric[0] + (ku + ksol) / 2, ric[1] + (ku + ksag) / 2, ric[2] + (ka + ksol) / 2, ric[3] + (ka + ksag) / 2]
    buyuk = np.zeros((Hd * up, Wd * up), np.uint8)
    cv2.rectangle(buyuk, (0, 0), (Wd * up - 1, Hd * up - 1), 255, -1)
    sinir = min(Wd * up // 2, Hd * up // 2)
    for r, kose in zip(rs, ("TL", "TR", "BL", "BR")):
        R = max(0, min(int(round(r * up)), sinir))
        if R <= 0:
            continue
        x0, y0, x1, y1 = 0, 0, Wd * up, Hd * up
        if kose == "TL":
            cx, cy, sy, sx = x0 + R, y0 + R, slice(y0, y0 + R), slice(x0, x0 + R)
        elif kose == "TR":
            cx, cy, sy, sx = x1 - R, y0 + R, slice(y0, y0 + R), slice(x1 - R, x1)
        elif kose == "BL":
            cx, cy, sy, sx = x0 + R, y1 - R, slice(y1 - R, y1), slice(x0, x0 + R)
        else:
            cx, cy, sy, sx = x1 - R, y1 - R, slice(y1 - R, y1), slice(x1 - R, x1)
        buyuk[sy, sx] = 0
        cv2.circle(buyuk, (cx, cy), R, 255, -1)
    sekil = cv2.resize(buyuk, (Wd, Hd), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    T = np.array([[1, 0, -ksol], [0, 1, -ku], [0, 0, 1]], np.float64)   # genis yerel -> quad yerel
    dis = cv2.warpPerspective(sekil, Hl.astype(np.float64) @ T, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
    q_ic = (poly_mask_aa(shape, quad) >= 0.5).astype(np.uint8)
    kasa = ((dis >= 0.5).astype(np.uint8)) & (1 - q_ic)
    return kasa, kal, [round(float(r), 1) for r in rs]


def kalinlik(img, quad, kenar, uzun=60):
    q = np.asarray(quad, np.float64)
    L = lab_of(img)[..., 0] * 100 / 255
    if kenar == "ust":
        cx, cy, dx, dy = (q[0][0] + q[1][0]) / 2, (q[0][1] + q[1][1]) / 2, 0, -1
    else:
        cx, cy, dx, dy = (q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2, -1, 0
    prof = np.array([L[int(round(cy + dy * t)), int(round(cx + dx * t))] for t in range(0, uzun)])
    return int((prof[:30] < 35).sum()), [round(float(v)) for v in prof[:40]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--hedef", action="append", default=[], help="SAHNE:HEDEF_EKRAN:KAYNAK_EKRAN")
    ap.add_argument("--bant", type=int, default=60)
    ap.add_argument("--gecis", type=int, default=4)
    ap.add_argument("--delik", default="maske", choices=("maske", "sekil"),
                    help="maske: kaynak ekran maskesi tasinir (varsayilan); sekil: eski quad + kaynak yaricaplari")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--out-calib", required=True)
    ap.add_argument("--kanit-dir", required=True)
    ap.add_argument("--boy", type=int, default=300)
    a = ap.parse_args()
    c0 = json.loads((Path(a.calib) / "calib.json").read_text())
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    Path(a.kanit_dir).mkdir(parents=True, exist_ok=True)
    maske_dir = Path(a.out_calib).parent / "masks"
    maske_dir.mkdir(parents=True, exist_ok=True)
    for h in a.hedef:
        scene, tid, sid = h.split(":")
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        yol = Path(a.out_dir) / cfg["master"]
        temiz = imread(yol) if yol.exists() else master.copy()
        ekr = {int(s["id"]): s for s in c0["scenes"][src]["screens"]}
        q_h = np.asarray(ekr[int(tid)]["quad"], np.float32)
        q_k = np.asarray(ekr[int(sid)]["quad"], np.float32)
        shape = master.shape
        soft_k = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{sid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        soft_h = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{tid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        kal_k, det_k = kalinlik_olc(master, q_k, a.bant)
        kal_h, det_h = kalinlik_olc(master, q_h, a.bant)
        kasa_k, kal_k, rs_k = siluet(master, q_k, a.bant, shape, soft=soft_k, kal=kal_k)
        kasa_h, kal_h, rs_h = siluet(master, q_h, a.bant, shape, soft=soft_h, kal=kal_h)
        H = cv2.getPerspectiveTransform(q_k, q_h)
        olcek = float(np.sqrt(abs(np.linalg.det(H[:2, :2]))))
        # kaynak maskesinden ic kose yaricapi (rapor icin)
        W, Hh, Hl = _yerel(q_k)
        yerel = cv2.warpPerspective(soft_k, np.linalg.inv(Hl.astype(np.float64)), (W, Hh), flags=cv2.INTER_LINEAR)
        _, rs = _kose_yaricapi(yerel)
        rs = [round(float(r) * olcek, 1) for r in rs]
        # isik farki (kasa bandi L)
        lab_m = lab_of(master)
        L_k = float(lab_m[..., 0][kasa_k > 0].mean()) * 100 / 255
        L_h = float(lab_m[..., 0][kasa_h > 0].mean()) * 100 / 255
        kaynak_img = master.copy()
        dL = L_h - L_k
        if abs(dL) > L_ESIK:
            lab_k = lab_m.copy()
            lab_k[..., 0] = np.clip(lab_k[..., 0] + (dL / 2) * 255 / 100, 0, 255)
            kaynak_img = cv2.cvtColor(lab_k.astype(np.uint8), cv2.COLOR_Lab2BGR)
        # tasi: kaynak telefonun TAMAMI (kasa + ekran ici) hedefe; dis siluette GECIS px gecis
        kasa_w = cv2.warpPerspective(master if abs(dL) <= L_ESIK else kaynak_img, H, (shape[1], shape[0]), flags=cv2.INTER_CUBIC)
        q_ic_k = (poly_mask_aa(shape, q_k) >= 0.5).astype(np.uint8)
        q_ic_h = (poly_mask_aa(shape, q_h) >= 0.5).astype(np.uint8)
        sil_w = cv2.warpPerspective(kasa_k.astype(np.float32), H, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
        sil_w = (sil_w >= 0.5).astype(np.uint8)
        tam_w = cv2.warpPerspective((kasa_k | q_ic_k).astype(np.float32), H, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
        tam_w = (tam_w >= 0.5).astype(np.uint8)
        # 1) hedefin kendi siluetinden tasinan telefonun disinda kalan artik -> duvardan inpaint
        artik = (kasa_h | q_ic_h) & (1 - tam_w)
        if artik.sum():
            temiz = cv2.inpaint(temiz, (artik * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA)
        dd = cv2.distanceTransform(tam_w, cv2.DIST_L2, 5)
        w = np.clip(dd / float(a.gecis), 0, 1) * tam_w
        w3 = w[..., None].astype(np.float32)
        temiz = (temiz.astype(np.float32) * (1 - w3) + kasa_w.astype(np.float32) * w3).round().clip(0, 255).astype(np.uint8)
        # delik: kopyalanan telefonun EKRANI, fotograftan olculur (acik ekran: L esigi ile
        # siyah cerceve ic kenarina kadar; koyu ekranda olcum olmaz -> tasinan kaynak
        # maskesine oturtulmus yuvarlak dikdortgen; aradaki bosluk zaten siyah ekran).
        delik_w = np.clip(cv2.warpPerspective(soft_k, H, (shape[1], shape[0]), flags=cv2.INTER_LINEAR), 0, 1)
        Lt = lab_of(temiz)[..., 0] * 100 / 255
        aday = ((Lt > 45).astype(np.uint8)) & (poly_mask_aa(shape, expand_quad(q_h, 8)) >= 0.5).astype(np.uint8)
        aday = cv2.morphologyEx(aday, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        n, lab_c, st, _ = cv2.connectedComponentsWithStats(aday, 8)
        olc = np.zeros(shape[:2], np.uint8)
        if n > 1:
            en = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            cnts, _ = cv2.findContours((lab_c == en).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(olc, cnts, -1, 1, -1)
            olc = cv2.morphologyEx(olc, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        oran = float(olc.sum()) / max(1.0, float((delik_w >= 0.5).sum()))
        if a.delik == "maske" and 0.9 <= oran <= 1.15:
            delik = cv2.GaussianBlur(olc.astype(np.float32), (0, 0), 0.8)
            delik_yol = f"fotograftan olculdu (L>45), alan orani {oran:.3f} (olculen / tasinan maske)"
        elif a.delik == "maske":
            delik, r_d, rs_d = hole_shape(delik_w, q_h, inset=0.0, ic_cikar=False)
            delik_yol = f"koyu ekran, olcum yok (oran {oran:.3f}) -> tasinan maskeye oturtulmus yuvarlak dikdortgen, yaricap {rs_d}"
        else:
            delik, _, _ = hole_shape(soft_h, q_h, inset=0.0, yaricap=rs, ic_cikar=False)
            delik_yol = "eski quad + kaynak yaricaplari"
        delik = np.clip(delik, 0, 1).astype(np.float32)
        if a.delik == "maske":
            cv2.imwrite(str(maske_dir / f"{src}_{tid}.png"), (delik * 255).round().astype(np.uint8))
        ic = (delik >= 0.5).astype(np.uint8)
        cv2.imwrite(str(yol), temiz, [cv2.IMWRITE_JPEG_QUALITY, 97])
        L_yeni = float(lab_of(temiz)[..., 0][(sil_w & (1 - ic)) > 0].mean()) * 100 / 255
        log(f"{scene}: hedef {tid} ({ekr[int(tid)]['edition']}) <- kaynak {sid} ({ekr[int(sid)]['edition']}) | olcek {olcek:.4f} | delik={a.delik}")
        log(f"  kasa kalinligi (ust,sag,alt,sol) kaynak {kal_k} px  hedef {kal_h} px | 9 cizgi kaynak {det_k}")
        log(f"  kaynak kasa {int(kasa_k.sum())} px, hedef kasa {int(kasa_h.sum())} px, tasinan telefon {int(tam_w.sum())} px, artik inpaint {int(artik.sum())} px")
        log(f"  delik: {delik_yol} | delik {int(ic.sum())} px, hedef eski maske {int((soft_h >= 0.5).sum())} px")
        log(f"  ic kose yaricapi (kaynak maskesi, TL,TR,BL,BR) {rs} px | dis yaricap kaynak {rs_k} | kasa L kaynak {L_k:.1f} hedef(eski) {L_h:.1f} fark {dL:+.1f} "
            f"-> {'L/2 kaydirildi' if abs(dL) > L_ESIK else 'ayar yok'} | yeni kasa L {L_yeni:.1f}")
        # calib kopyasi: hedef ekran frame_top
        for s in calib["scenes"][src]["screens"]:
            if int(s["id"]) == int(tid):
                if a.delik == "maske":
                    s["frame_top"] = {"disari": 12, "delik": "maske", "delik_px": 0}
                else:
                    s["frame_top"] = {"disari": 4, "delik": "sekil", "delik_px": 0, "yaricap": rs}
        # kanit: sahnedeki TUM telefonlarin sol ust + sag alt kosesi, ust kenar kalinligi/rengi
        b = a.boy
        ust, alt, satir = [], [], []
        for pid in sorted(ekr):
            if ekr[pid]["device"] != "Phone":
                continue
            q = np.asarray(ekr[pid]["quad"], np.float32)
            for (px, py), kare in ((q[0], ust), (q[2], alt)):
                x0 = int(round(px)) - b // 2; y0 = int(round(py)) - b // 2
                x0 = max(0, min(x0, shape[1] - b)); y0 = max(0, min(y0, shape[0] - b))
                kare.append(temiz[y0:y0 + b, x0:x0 + b])
            kal_p, _ = kalinlik_olc(temiz, q, a.bant)
            ks, _, _ = siluet(temiz, q, a.bant, shape, kal=kal_p)
            labt = lab_of(temiz)
            Lm = float(labt[..., 0][ks > 0].mean()) * 100 / 255
            am = float(labt[..., 1][ks > 0].mean()) - 128; bm = float(labt[..., 2][ks > 0].mean()) - 128
            siyah, prof = kalinlik(temiz, q, "ust")
            etiket = "HEDEF" if pid == int(tid) else ("KAYNAK" if pid == int(sid) else "")
            satir.append(f"  ekran {pid} {ekr[pid]['edition']:<16} {etiket:<6} kalinlik {kal_p} px, kasa {int(ks.sum()):6d} px, L {Lm:.1f} a {am:+.1f} b {bm:+.1f} | ust: siyah {siyah} px, L profili {prof[:30]}")
        log("  KASA KARSILASTIRMASI (temiz master):")
        for s_ in satir:
            log(s_)
        panel = np.vstack([np.hstack(ust), np.hstack(alt)])
        kp = Path(a.kanit_dir) / f"K05_{scene}_KASALAR.jpg"
        cv2.imwrite(str(kp), panel, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {kp.name} ({panel.shape[1]}x{panel.shape[0]}, ust satir sol-ust kose, alt satir sag-alt kose; soldan saga ekran id sirasi, 1:1)")
    Path(a.out_calib).write_text(json.dumps(calib, indent=1))
    for p in Path(a.masters).glob("*_FINAL.jpg"):
        hh = Path(a.out_dir) / p.name
        if not hh.exists():
            hh.write_bytes(p.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
