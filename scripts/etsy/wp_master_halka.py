#!/usr/bin/env python3
"""
MASTER HALKA TEMIZLIGI - 5 Eyl 2026 (Mo). Yalniz verilen ekranlarda.

Halka = (eski quad + DISARI px) EKSI (Mo'nun kirmizisindan gelen yuvarlak delik).
Bu halka, master'a gomulu pilot parsomeninin tam yeridir. Halkanin HEMEN
DISINDAKI SERIT px'lik seritten renk orneklenir ve halka cv2.inpaint (TELEA)
ile doldurulur; dolgunun icerideki parsomenden beslenmemesi icin delik ici
gecici olarak serit medyaniyla boyanir, sonra geri konur. Renk kurali yok;
geometri bellidir. Temiz master AYRI kopyaya yazilir.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, expand_quad, hole_shape, imread, log, poly_mask_aa  # noqa: E402


def L_ort(img, m):
    if m.sum() == 0:
        return float("nan")
    return float(cv2.cvtColor(img, cv2.COLOR_BGR2Lab)[..., 0][m > 0].mean()) * 100.0 / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True, help="uretim calib (eski quad + maskeler)")
    ap.add_argument("--calib-b", required=True, help="yeni quad + yaricap (B) calib.json")
    ap.add_argument("--masters", required=True)
    ap.add_argument("--ekran", action="append", default=[], help="SAHNE:EKRAN")
    ap.add_argument("--disari", type=int, default=10)
    ap.add_argument("--serit", type=int, default=6)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--kanit-dir", required=True)
    ap.add_argument("--boy", type=int, default=260)
    ap.add_argument("--dis-yuvarlak", action="store_true",
                    help="halkanin dis siniri eski quad+disari (kare kose) yerine delikle es merkezli "
                         "yuvarlak dikdortgen (yeni quad+disari, yaricap r+disari) olsun")
    a = ap.parse_args()

    c0 = json.loads((Path(a.calib) / "calib.json").read_text())
    cb = json.loads(Path(a.calib_b).read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    Path(a.kanit_dir).mkdir(parents=True, exist_ok=True)
    for e in a.ekran:
        scene, eid = e.split(":")
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        temiz_yol = Path(a.out_dir) / cfg["master"]
        temiz = imread(temiz_yol) if temiz_yol.exists() else master.copy()   # ayni sahnede birden cok ekran
        s0 = next(x for x in c0["scenes"][src]["screens"] if int(x["id"]) == int(eid))
        sb = next(x for x in cb["scenes"][src]["screens"] if int(x["id"]) == int(eid))
        eski = np.asarray(s0["quad"], np.float32)
        yeni = np.asarray(sb["quad"], np.float32)
        ft = sb.get("frame_top") or {}
        yaricap = ft.get("yaricap")
        soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{eid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        delik, _, rs = hole_shape(soft, yeni, inset=0.0, yaricap=yaricap)
        ic = (delik >= 0.5).astype(np.uint8)
        if a.dis_yuvarlak:
            # 2. deneme (5 Eyl 2026): kare koseli dis sinir cerceve kosesini ve duvari halkaya
            # aliyordu; dis sinir artik delikle es merkezli yuvarlak dikdortgen.
            dis_r = [float(v) + a.disari for v in yaricap] if yaricap else None
            dis_delik, _, _ = hole_shape(soft, expand_quad(yeni, a.disari), inset=0.0, yaricap=dis_r, ic_cikar=False)
            genis = (dis_delik >= 0.5).astype(np.uint8)
        else:
            genis = (poly_mask_aa(master.shape, expand_quad(eski, a.disari)) >= 0.5).astype(np.uint8)
        halka = genis & (1 - ic)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.serit + 1, 2 * a.serit + 1))
        serit = cv2.dilate(genis, k) & (1 - genis)                     # halkanin hemen disi (cerceve)
        L_once, L_serit = L_ort(master, halka), L_ort(master, serit)
        ref = np.median(temiz[serit > 0].reshape(-1, 3), axis=0).astype(np.uint8)
        calis = temiz.copy()
        calis[ic > 0] = ref                                            # dolgu iceriden beslenmesin
        dolgu = cv2.inpaint(calis, (halka * 255).astype(np.uint8), 7, cv2.INPAINT_TELEA)
        temiz[halka > 0] = dolgu[halka > 0]
        L_sonra = L_ort(temiz, halka)
        dis_ad = f"yeni quad+{a.disari} px yuvarlak (r+{a.disari})" if a.dis_yuvarlak else f"eski quad+{a.disari} px"
        log(f"{scene}/{eid} {s0['device']} ({s0['edition']}): {dis_ad} EKSI yuvarlak delik "
            f"(yaricap {yaricap}) -> halka {int(halka.sum())} px, genislik ort {halka.sum() / max(1, cv2.arcLength(np.int32(eski).reshape(-1,1,2), True)):.1f} px | "
            f"L halka once {L_once:.1f} sonra {L_sonra:.1f} | cerceve seridi ({a.serit} px, {int(serit.sum())} px) L {L_serit:.1f}")
        cv2.imwrite(str(temiz_yol), temiz, [cv2.IMWRITE_JPEG_QUALITY, 97])
        # kanit: 4 kose, ustte once altta sonra, tam cozunurluk
        b = a.boy
        satir = []
        for img in (master, temiz):
            kare = []
            for (x, y) in eski:
                x0 = int(round(x)) - b // 2; y0 = int(round(y)) - b // 2
                x0 = max(0, min(x0, img.shape[1] - b)); y0 = max(0, min(y0, img.shape[0] - b))
                kare.append(img[y0:y0 + b, x0:x0 + b])
            satir.append(np.hstack(kare))
        panel = np.vstack([satir[0], np.full((6, satir[0].shape[1], 3), (0, 0, 255), np.uint8), satir[1]])
        kp = Path(a.kanit_dir) / f"K03_{scene}_S{eid}_HALKA_ONCE_SONRA.jpg"
        cv2.imwrite(str(kp), panel, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {kp.name} ({panel.shape[1]}x{panel.shape[0]}, ust once / alt sonra, TL TR BR BL)")
    # diger masterlar oldugu gibi kopyalanir
    for p in Path(a.masters).glob("*_FINAL.jpg"):
        h = Path(a.out_dir) / p.name
        if not h.exists():
            h.write_bytes(p.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
