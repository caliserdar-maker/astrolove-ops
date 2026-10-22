#!/usr/bin/env python3
"""
HALKAYI KOMSU TELEFONDAN KOPYALA - 5 Eyl 2026 (Mo). Yalniz verilen ekranlarda.

Kaynak telefonun (ayni model, temiz) eski quad'inin disindaki 0-DISARI px bant
(siyah ic kenar + metal cerceve) iki eski quad arasindaki homografi ile hedef
telefonun geometrisine oturtulur ve hedef master KOPYASINDA halkanin
[(eski quad + DISARI) EKSI B deligi] ustune yazilir. Dis kenarda GECIS px
yumusak gecis, ic kenar yeni delik siniri. Inpaint yok, renk kurali yok.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, expand_quad, hole_shape, imread, log, poly_mask_aa  # noqa: E402


def kalinlik(img, quad, kenar, uzun=45):
    """Ekran kenarinin ortasindan disari dogru profil: L<35 (siyah ic kenar) ve
    duvara (L, cerceve+15) gecene kadarki toplam bant px."""
    q = np.asarray(quad, np.float64)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32) * 100 / 255
    if kenar == "ust":
        cx, cy, dx, dy = (q[0][0] + q[1][0]) / 2, (q[0][1] + q[1][1]) / 2, 0, -1
    else:
        cx, cy, dx, dy = (q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2, -1, 0
    prof = np.array([lab[int(round(cy + dy * t)), int(round(cx + dx * t))] for t in range(0, uzun)])
    siyah = int((prof < 35).sum())
    dis = float(np.median(prof[-8:]))
    ic = np.where(prof > dis - 8)[0]
    bant = int(ic[0]) if ic.size else uzun
    return siyah, bant, [round(float(v)) for v in prof[:32]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--calib-b", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--hedef", action="append", default=[], help="SAHNE:HEDEF_EKRAN:KAYNAK_EKRAN")
    ap.add_argument("--disari", type=int, default=30)
    ap.add_argument("--gecis", type=int, default=5)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--kanit-dir", required=True)
    ap.add_argument("--boy", type=int, default=240)
    ap.add_argument("--hedef-quad", default="eski", choices=("eski", "yeni"),
                    help="kaynak ekran kenari hedefin ESKI quad'ina mi (1. deneme) YENI (B, Mo'nun kirmizisi) quad'ina mi otursun")
    a = ap.parse_args()
    c0 = json.loads((Path(a.calib) / "calib.json").read_text())
    cb = json.loads(Path(a.calib_b).read_text())
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
        q_h = np.asarray(ekr[int(tid)]["quad"], np.float32)      # hedef eski quad
        q_k = np.asarray(ekr[int(sid)]["quad"], np.float32)      # kaynak eski quad
        sb = next(x for x in cb["scenes"][src]["screens"] if int(x["id"]) == int(tid))
        q_b = np.asarray(sb["quad"], np.float32)
        yaricap = (sb.get("frame_top") or {}).get("yaricap")
        soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{tid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        delik, _, _ = hole_shape(soft, q_b, inset=0.0, yaricap=yaricap)
        # 2. deneme (5 Eyl 2026): kaynak ekran kenari hedefin YENI (kirmizi) quad'ina oturur; eski
        # quad'a oturtunca delik ile eski quad arasindaki 14-16 px serit kaynagin ekran iciyle doluyordu.
        q_ref = q_b if a.hedef_quad == "yeni" else q_h
        H = cv2.getPerspectiveTransform(q_k, q_ref)               # kaynak -> hedef
        kaynak_w = cv2.warpPerspective(master, H, (master.shape[1], master.shape[0]), flags=cv2.INTER_CUBIC)
        dis = (poly_mask_aa(master.shape, expand_quad(q_ref, a.disari)) >= 0.5).astype(np.uint8)
        ic = (delik >= 0.5).astype(np.uint8)
        halka = dis & (1 - ic)
        d = cv2.distanceTransform(dis, cv2.DIST_L2, 5)             # dis kenara uzaklik
        w = np.clip(d / float(a.gecis), 0.0, 1.0) * halka
        w3 = w[..., None].astype(np.float32)
        temiz = (temiz.astype(np.float32) * (1 - w3) + kaynak_w.astype(np.float32) * w3).round().clip(0, 255).astype(np.uint8)
        olcek = np.sqrt(abs(np.linalg.det(H[:2, :2])))
        log(f"{scene}: hedef ekran {tid} ({ekr[int(tid)]['edition']}) <- kaynak ekran {sid} ({ekr[int(sid)]['edition']}) | "
            f"homografi olcek {olcek:.4f} | halka {int(halka.sum())} px ({a.hedef_quad} quad+{a.disari} EKSI B deligi), dis gecis {a.gecis} px")
        cv2.imwrite(str(yol), temiz, [cv2.IMWRITE_JPEG_QUALITY, 97])
        # kalinlik olcumu: hedef (sonra, yeni delik kenarindan) ve kaynak (kendi quad'indan)
        for kenar in ("ust", "sol"):
            s_h, b_h, p_h = kalinlik(temiz, q_b, kenar)
            s_k, b_k, p_k = kalinlik(master, q_k, kenar)
            log(f"  {kenar} kenar ortasi, ekran kenarindan disari: HEDEF siyah {s_h} px / bant {b_h} px | KAYNAK siyah {s_k} px / bant {b_k} px")
            log(f"     L profili hedef {p_h}")
            log(f"     L profili kaynak {p_k}")
        # kanit: ust satir hedef (sonra) 4 kose, alt satir kaynak 4 kose; ayni buyutme
        b = a.boy
        satir = []
        for img, q in ((temiz, q_h), (master, q_k)):
            kare = []
            for (x, y) in q:
                x0 = int(round(x)) - b // 2; y0 = int(round(y)) - b // 2
                x0 = max(0, min(x0, img.shape[1] - b)); y0 = max(0, min(y0, img.shape[0] - b))
                kare.append(img[y0:y0 + b, x0:x0 + b])
            satir.append(np.hstack(kare))
        panel = np.vstack([satir[0], np.full((6, satir[0].shape[1], 3), (0, 0, 255), np.uint8), satir[1]])
        kp = Path(a.kanit_dir) / f"K04_{scene}_S{tid}_HEDEF_vs_S{sid}_KAYNAK.jpg"
        cv2.imwrite(str(kp), panel, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {kp.name} (ust: hedef sonra, alt: kaynak; TL TR BR BL, 1:1)")
    for p in Path(a.masters).glob("*_FINAL.jpg"):
        hh = Path(a.out_dir) / p.name
        if not hh.exists():
            hh.write_bytes(p.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
