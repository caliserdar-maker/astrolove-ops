#!/usr/bin/env python3
"""
KOMSU TELEFONUN TUM KASASINI KOPYALA - 5 Eyl 2026 (Mo). Yalniz verilen ekranlarda.

1) Kaynak telefonun kasasi: ekran quad'inin disindan telefonun dis siluetine
   kadar. Siluet, kaynak fotograftan segmentlenir: quad disindaki 0-BANT px
   bolgede duvar rengine (BANT..BANT+20 px halkasinin medyani) Lab uzakligi
   ESIK'i asan pikseller (metal/siyah), quad'a bagli en buyuk bilesen.
2) Kasa iki ESKI quad arasindaki homografiyle hedefe tasinir.
3) Hedef master KOPYASINDA hedef telefonun kasasi tamamen degistirilir:
   tasinan siluet icinde tasinan kasa (dis siluette GECIS px yumusak gecis),
   hedefin kendi siluetinden artan kisim duvardan inpaint.
4) Delik: hedefin eski quad kenarlari + kaynagin kendi ekran maskesinden
   olculen kose yaricaplari (homografi olcegiyle) -> calib kopyasina
   frame_top {delik: sekil, yaricap}.
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


def siluet(img, quad, bant, shape):
    """quad disindaki kasa (metal+siyah) maskesi ve duvar referans rengi."""
    lab = lab_of(img)
    q_ic = (poly_mask_aa(shape, quad) >= 0.5).astype(np.uint8)
    q_bant = (poly_mask_aa(shape, expand_quad(quad, bant)) >= 0.5).astype(np.uint8)
    q_duvar = (poly_mask_aa(shape, expand_quad(quad, bant + 20)) >= 0.5).astype(np.uint8) & (1 - q_bant)
    duvar = np.median(lab[q_duvar > 0], axis=0)
    d = np.linalg.norm(lab - duvar, axis=2)
    aday = ((d > ESIK).astype(np.uint8) & q_bant & (1 - q_ic))
    aday = cv2.morphologyEx(aday, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    # quad'a bagli bilesen: quad'i 3 px genisletip birlestir, en buyuk bileseni al
    birlesik = aday | (poly_mask_aa(shape, expand_quad(quad, 3)) >= 0.5).astype(np.uint8)
    n, lab_c, st, _ = cv2.connectedComponentsWithStats(birlesik, 8)
    en = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else 0
    kasa = ((lab_c == en).astype(np.uint8)) & (1 - q_ic)
    # ic delikleri doldur
    cnts, _ = cv2.findContours(kasa | q_ic, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dolu = np.zeros_like(kasa)
    cv2.drawContours(dolu, cnts, -1, 1, -1)
    kasa = dolu & (1 - q_ic)
    return kasa, duvar


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
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--out-calib", required=True)
    ap.add_argument("--kanit-dir", required=True)
    ap.add_argument("--boy", type=int, default=300)
    a = ap.parse_args()
    c0 = json.loads((Path(a.calib) / "calib.json").read_text())
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    Path(a.kanit_dir).mkdir(parents=True, exist_ok=True)
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
        kasa_k, duvar_k = siluet(master, q_k, a.bant, shape)
        kasa_h, duvar_h = siluet(master, q_h, a.bant, shape)
        H = cv2.getPerspectiveTransform(q_k, q_h)
        olcek = float(np.sqrt(abs(np.linalg.det(H[:2, :2]))))
        # kaynak maskesinden kose yaricapi
        soft_k = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{sid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        W = int(round((np.linalg.norm(q_k[1] - q_k[0]) + np.linalg.norm(q_k[2] - q_k[3])) / 2))
        Hh = int(round((np.linalg.norm(q_k[3] - q_k[0]) + np.linalg.norm(q_k[2] - q_k[1])) / 2))
        Hl = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, Hh], [0, Hh]]), q_k)
        yerel = cv2.warpPerspective(soft_k, np.linalg.inv(Hl.astype(np.float64)), (W, Hh), flags=cv2.INTER_LINEAR)
        r_med, rs = _kose_yaricapi(yerel)
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
        # tasi
        kasa_w = cv2.warpPerspective(master if abs(dL) <= L_ESIK else kaynak_img, H, (shape[1], shape[0]), flags=cv2.INTER_CUBIC)
        sil_w = cv2.warpPerspective(kasa_k.astype(np.float32), H, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
        sil_w = (sil_w >= 0.5).astype(np.uint8)
        q_ic_h = (poly_mask_aa(shape, q_h) >= 0.5).astype(np.uint8)
        # delik (hedef eski quad + kaynak yaricaplari) - master'da ic bolge oldugu gibi kalir
        soft_h = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{tid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        delik, _, _ = hole_shape(soft_h, q_h, inset=0.0, yaricap=rs, ic_cikar=False)
        ic = (delik >= 0.5).astype(np.uint8)
        # 1) hedefin kendi siluetinden tasinan siluetin disinda kalan artik -> duvardan inpaint
        artik = (kasa_h | q_ic_h) & (1 - sil_w) & (1 - ic)
        if artik.sum():
            temiz = cv2.inpaint(temiz, (artik * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA)
        # 2) tasinan kasa: siluet ici, delik disi; dis siluette GECIS px gecis
        dd = cv2.distanceTransform(sil_w, cv2.DIST_L2, 5)
        w = np.clip(dd / float(a.gecis), 0, 1) * (sil_w & (1 - ic))
        w3 = w[..., None].astype(np.float32)
        temiz = (temiz.astype(np.float32) * (1 - w3) + kasa_w.astype(np.float32) * w3).round().clip(0, 255).astype(np.uint8)
        cv2.imwrite(str(yol), temiz, [cv2.IMWRITE_JPEG_QUALITY, 97])
        L_yeni = float(lab_of(temiz)[..., 0][(sil_w & (1 - ic)) > 0].mean()) * 100 / 255
        log(f"{scene}: hedef {tid} ({ekr[int(tid)]['edition']}) <- kaynak {sid} ({ekr[int(sid)]['edition']}) | olcek {olcek:.4f} | "
            f"kaynak kasa {int(kasa_k.sum())} px, hedef kasa {int(kasa_h.sum())} px, tasinan {int(sil_w.sum())} px, artik inpaint {int(artik.sum())} px")
        log(f"  kose yaricapi (kaynak maskesi, TL,TR,BL,BR) {rs} px | kasa L kaynak {L_k:.1f} hedef(eski) {L_h:.1f} fark {dL:+.1f} "
            f"-> {'L/2 kaydirildi' if abs(dL) > L_ESIK else 'ayar yok'} | yeni kasa L {L_yeni:.1f}")
        # calib kopyasi: hedef ekran frame_top (delik = eski quad + kaynak yaricaplari)
        for s in calib["scenes"][src]["screens"]:
            if int(s["id"]) == int(tid):
                s["frame_top"] = {"disari": 4, "delik": "sekil", "delik_px": 0, "yaricap": rs}
        # kanit: sahnedeki TUM telefonlarin sol ust kosesi + ust kenar kalinligi/rengi
        b = a.boy
        kare, satir = [], []
        for pid in sorted(ekr):
            if ekr[pid]["device"] != "Phone":
                continue
            q = np.asarray(ekr[pid]["quad"], np.float32)
            x0 = int(round(q[0][0])) - b // 2; y0 = int(round(q[0][1])) - b // 2
            x0 = max(0, min(x0, shape[1] - b)); y0 = max(0, min(y0, shape[0] - b))
            kare.append(temiz[y0:y0 + b, x0:x0 + b])
            ks, _ = siluet(temiz, q, a.bant, shape)
            labt = lab_of(temiz)
            Lm = float(labt[..., 0][ks > 0].mean()) * 100 / 255
            am = float(labt[..., 1][ks > 0].mean()) - 128; bm = float(labt[..., 2][ks > 0].mean()) - 128
            siyah, prof = kalinlik(temiz, q, "ust")
            etiket = "HEDEF" if pid == int(tid) else ("KAYNAK" if pid == int(sid) else "")
            satir.append(f"  ekran {pid} {ekr[pid]['edition']:<16} {etiket:<6} kasa {int(ks.sum()):6d} px, L {Lm:.1f} a {am:+.1f} b {bm:+.1f} | ust: siyah {siyah} px, L profili {prof[:26]}")
        log("  KASA KARSILASTIRMASI (temiz master):")
        for s_ in satir:
            log(s_)
        panel = np.hstack(kare)
        kp = Path(a.kanit_dir) / f"K05_{scene}_KASALAR_SOLUST.jpg"
        cv2.imwrite(str(kp), panel, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {kp.name} ({panel.shape[1]}x{panel.shape[0]}, soldan saga ekran id sirasi, 1:1)")
    Path(a.out_calib).write_text(json.dumps(calib, indent=1))
    for p in Path(a.masters).glob("*_FINAL.jpg"):
        hh = Path(a.out_dir) / p.name
        if not hh.exists():
            hh.write_bytes(p.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
