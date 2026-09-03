#!/usr/bin/env python3
"""
wp-night c) Ilan videosu: pilot master videosunun (WA_WP_VIDEO_TOZ_V3.mp4, SET01
sahnesi, 1800x1350, 11.5 sn, 30 fps, iki telefon MB + CI) ekran icerigini yeni
ciftin FINAL_V2 Phone wallpaper'lariyla degistirir.

YONTEM (3 Eyl 2026 karari - DOGRUDAN DEGISTIRME): pilot murekkebi hic isin
icine katilmaz. Her karede ekran bolgesi dogrudan yenisiyle doldurulur:

    out = kare * (1 - M) + M * (warp_cover(yeni) * G)

  M = yumusak ekran maskesi (soft_mask, kenar gecisli)
  warp_cover = oran-koruyan (crop-to-fill) yerlestirme, wp_mockup_common
  G = kare-bazli dusuk frekansli parlaklik eslemesi: o karenin ekran
      bolgesindeki blur(kare)/blur(yeni) orani (sigma 25) - sahnenin isik/
      pozlama degisimini tasir, metin kenarlarina DOKUNMAZ.

Neden cikarma birakildi: onceki "out = kare + M*L*(warp(yeni) - warp(pilot))"
fark modu, pilot murekkebini ancak MUKEMMEL hizalamada iptal edebilirdi; keskin
metin kenarlarinda alt-piksel kalinti bile gorunur hayalet cift-baski birakti
(3 iterasyon, gorsel kanit). Dogrudan degistirmede pilot murekkebi denklemde
hic yer almadigi icin iptal edilecek bir sey yoktur.

Toz/hareket: toz katmani ekranin USTUNDE degil (maske disinda) oldugu icin
dokunulmaz; maske disi pikseller aynen kareden gelir.

Kalibrasyon: sahne durgun (yalniz toz hareket eder), bu yuzden ekran dortgeni
BIR kez olculur: SET01 kalibrasyonundaki dortgenler video olcegine (1800/3000)
indirilir ve ECC ile rafine edilir.

QC (PASS/FAIL - SAYISAL, gorsel dogrulamanin YERINE GECMEZ):
  a) ekran disi: |out - kare| = 0 (maske disi hic dokunulmaz);
  b) ekran ici murekkep degisimi: yeni murekkep bolgesinde ort |out - kare| > 5;
  c) olcu/fps/kare sayisi master ile ayni.
Gorsel kontrol icin kare 0 / orta / son PNG olarak yazilir.
Kullanim:
  wp_video_render.py --master WA_WP_VIDEO_TOZ_V3.mp4 --scene-master SET01.jpg
      --calib <dir> --pilot <dir> --wallpapers <dir> --pair Aries_Leo --out <dir>
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import cover_homography, imread, ink_mask, log, warp_cover, warp_mask

SCENE = "SET01"
INK_CHANGE_MIN = 5.0
FPS_TOL = 0.01
LIGHT_SIGMA = 25.0    # kare-bazli parlaklik eslemesi icin dusuk gecirgen yaricap (piksel)
GAIN_LIMITS = (0.2, 3.0)


def scaled_screens(calib, scale):
    return [dict(id=s["id"], device=s["device"], edition=s["edition"],
                 quad=np.asarray(s["quad"], np.float32) * scale)
            for s in calib["scenes"][SCENE]["screens"]]


def refine(frame, master_img, screens):
    """Master mockup'in video olcegine indirilmisi ile kare arasindaki TAM geometrik
    kayit (ECC homografi: donme/olcek/kesme dahil, sadece oteleme degil). Fotograf
    (kalibrasyon) ile video ayri cekim/render olduklarindan aralarinda oteleme-disi
    fark kalabilir; bu fark duzeltilmezse pilot ekran icerigi tam iptal edilmez ve
    hayalet cift-baski gorulur (bkz. render()'daki L yorumu). Homografi yakinsamazsa
    eski oteleme-sadece davranisina duser.

    ONEMLI (yerel sentetik testle sayisal dogrulandi): cv2.findTransformECC(template=g2,
    input=g1, ...) dondurdugu warp, g1(master)'i degil g2(frame)'i g1 uzayina tasir
    (yani warp: FRAME -> MASTER). quad'lar MASTER uzayinda olculdugu (calib.json) icin
    FRAME'e tasimak icin warp'in TERSI uygulanmali (once bu koddaki "+dx,+dy" / duz
    warp uygulamasi bu tersi yapmiyordu - gercek kaymayi duzeltmek yerine 2 katina
    cikariyordu; SADECE Cift=Pilot oz-uretim QC'sinde kayma zaten ~0 oldugundan bu
    isaret hatasi o testte hic gorunmuyordu)."""
    ms = cv2.resize(master_img, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_AREA)
    g1 = cv2.cvtColor(ms, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    warp = np.eye(3, 3, dtype=np.float32)
    try:
        cv2.findTransformECC(g2, g1, warp, cv2.MOTION_HOMOGRAPHY, criteria, None, 5)
    except cv2.error:
        log("  ECC homografi basarisiz; oteleme-sadece rafine denenecek")
        warp2 = np.eye(2, 3, dtype=np.float32)
        try:
            cv2.findTransformECC(g2, g1, warp2, cv2.MOTION_TRANSLATION, criteria, None, 5)
        except cv2.error:
            log("  ECC oteleme de basarisiz; kaydirma 0 alinir")
            return screens, (0.0, 0.0)
        dx, dy = float(warp2[0, 2]), float(warp2[1, 2])  # frame->master kaymasi; master->frame icin ters isaret
        out = [dict(s, quad=s["quad"] - np.float32([dx, dy])) for s in screens]
        return out, (-dx, -dy)
    Hcorr = np.linalg.inv(warp.astype(np.float64)).astype(np.float32)  # frame->master'in tersi = master->frame
    out = []
    for s in screens:
        q = cv2.perspectiveTransform(s["quad"].reshape(-1, 1, 2).astype(np.float32), Hcorr).reshape(-1, 2)
        out.append(dict(s, quad=q.astype(np.float32)))
    shift = (float(Hcorr[0, 2]), float(Hcorr[1, 2]))
    log(f"  ECC homografi rafine basarili (kayma bileseni ~{shift[0]:+.2f},{shift[1]:+.2f})")
    return out, shift


def soft_mask(shape, quad, feather=1.5, inset=1.0):
    """Dortgen ici yumusak maske (kenardan inset px iceri, feather px gecis)."""
    m = np.zeros(shape[:2], np.float32)
    c = quad.mean(axis=0)
    v = quad - c
    q = quad - v / np.linalg.norm(v, axis=1, keepdims=True) * inset
    cv2.fillPoly(m, [np.round(q * 16).astype(np.int32)], 1.0, cv2.LINE_AA, shift=4)
    return cv2.GaussianBlur(m, (0, 0), feather)


def render(master_path, calib, master_img, wp_dir, pair, pilot_pair, out_path, max_frames=0, encode=True):
    cap = cv2.VideoCapture(str(master_path))
    if not cap.isOpened():
        raise SystemExit(f"HATA: video acilamadi {master_path}")
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)); n_master = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, frame0 = cap.read()
    if not ok:
        raise SystemExit("HATA: ilk kare okunamadi")
    screens, shift = refine(frame0, master_img, scaled_screens(calib, W / master_img.shape[1]))
    log(f"  video {W}x{H} {fps:.3f} fps {n_master} kare; ECC kaydirma {shift[0]:+.2f},{shift[1]:+.2f}")
    # Ekran katmanlari: yeni wallpaper oran-korunarak (crop-to-fill) bir kez yerlestirilir;
    # kare-bazli degisen tek sey parlaklik eslemesi (asagida, dongude).
    layers = []
    msum = np.zeros((H, W), np.float32)
    ink = np.zeros((H, W), bool)
    for s in screens:
        wp_n = imread(Path(wp_dir) / f"AstroLove_{pair}_{s['edition']}_{s['device']}.jpg")
        m = soft_mask((H, W), s["quad"])
        wn = warp_cover(wp_n, s["quad"], (H, W, 3)).astype(np.float32)
        Hc, _ = cover_homography(wp_n.shape, s["quad"])
        layers.append(dict(mask=m, wn=wn, wn_low=cv2.GaussianBlur(wn * m[..., None], (0, 0), LIGHT_SIGMA)))
        ink |= warp_mask(ink_mask(wp_n), Hc, (H, W, 3)) > 0
        msum += m
    # Dogrudan degistirmede maskenin SIFIR OLMADIGI her piksel harmanlanir; "dokunulmadi"
    # kontrolu bu yuzden m == 0 uzerinden yapilir (eski fark modundaki 0.05 esigi,
    # katkinin maske agirligiyla orantili kucuk oldugu varsayimina dayaniyordu).
    inside = msum > 0
    export = {0, n_master // 2, max(0, n_master - 1)}      # gorsel kontrol kareleri (PNG, kayipsiz)
    tmp = Path(tempfile.mkdtemp()) / "frames.raw"
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    acc_ink = acc_self = self_max = out_max = 0.0
    i = 0
    with open(tmp, "wb") as fh:
        while True:
            ok, fr = cap.read()
            if not ok or (max_frames and i >= max_frames):
                break
            out = fr.astype(np.float32)
            for lay in layers:
                m = lay["mask"]
                # G: bu KARENIN ekran bolgesindeki dusuk frekansli parlakligi yeni icerige tasir
                # (pozlama/isik kare-kare degisebilir). Sigma 25 blur oldugu icin metin
                # kenarlarini bulandirmaz, yalniz genel parlaklik/renk seviyesini esler.
                fr_low = cv2.GaussianBlur(fr.astype(np.float32) * m[..., None], (0, 0), LIGHT_SIGMA)
                g = np.clip(fr_low / np.maximum(lay["wn_low"], 1.0), *GAIN_LIMITS)
                mm = m[..., None]
                out = (1 - mm) * out + mm * (lay["wn"] * g)
            outf = np.clip(np.round(out), 0, 255).astype(np.uint8)
            if i in export:
                cv2.imwrite(str(Path(out_path).parent / f"frame_{pair}_{i:03d}.png"), outf)
            d = np.abs(outf.astype(np.int16) - fr.astype(np.int16)).max(axis=2)
            if (~inside).any():
                out_max = max(out_max, float(d[~inside].max()))
            if ink.any():
                acc_ink += float(d[ink].mean())
            if pair == pilot_pair:
                acc_self += float(d[inside].mean()); self_max = max(self_max, float(d[inside].max()))
            fh.write(outf.tobytes())
            i += 1
            if i % 60 == 0:
                log(f"    kare {i}/{n_master} (%{100 * i / max(n_master, 1):.0f})")
    cap.release()
    n = i
    if not encode:      # yerel test (ffmpeg yok): yalniz olcum + ornek kare sayfasi
        tmp.unlink(missing_ok=True)
        return dict(pair=pair, frames=n, outside_max=out_max, ink_change_mean=acc_ink / max(n, 1),
                    self_mean=(acc_self / max(n, 1)) if pair == pilot_pair else None,
                    self_max=self_max if pair == pilot_pair else None, encoded=False,
                    master_frames=n_master, master_fps=fps, ecc_shift=[shift[0], shift[1]],
                    ok=bool(out_max == 0.0 and (pair == pilot_pair or acc_ink / max(n, 1) > INK_CHANGE_MIN)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                    "-s", f"{W}x{H}", "-r", f"{fps:.6f}", "-i", str(tmp),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out_path)], check=True)
    tmp.unlink(missing_ok=True)
    cap2 = cv2.VideoCapture(str(out_path))
    qc = dict(pair=pair, frames=n, outside_max=out_max, ink_change_mean=acc_ink / max(n, 1),
              self_mean=(acc_self / max(n, 1)) if pair == pilot_pair else None,
              self_max=self_max if pair == pilot_pair else None,
              out_frames=int(cap2.get(cv2.CAP_PROP_FRAME_COUNT)), out_fps=float(cap2.get(cv2.CAP_PROP_FPS)),
              out_w=int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH)), out_h=int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT)),
              master_frames=n_master, master_fps=fps, size_bytes=Path(out_path).stat().st_size,
              ecc_shift=[shift[0], shift[1]])
    cap2.release()
    qc["duration_s"] = qc["out_frames"] / qc["out_fps"] if qc["out_fps"] else 0
    qc["ok"] = bool(qc["out_w"] == W and qc["out_h"] == H and abs(qc["out_fps"] - fps) < FPS_TOL
                    and qc["out_frames"] == n and out_max == 0.0
                    and (pair == pilot_pair or qc["ink_change_mean"] > INK_CHANGE_MIN))
    return qc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    ap.add_argument("--scene-master", required=True, help="WA_MOCKUP_V2_SET01_<pilot>_FINAL.jpg")
    ap.add_argument("--calib", required=True)
    ap.add_argument("--pilot", required=True, help="pilot wallpaper klasoru (dogrudan degistirme yonteminde okunmaz)")
    ap.add_argument("--wallpapers", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=0, help="0 = hepsi (test icin kisalt)")
    ap.add_argument("--no-encode", action="store_true", help="ffmpeg yok: yalniz olcum + ornek kareler")
    a = ap.parse_args()
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"WA_WP_VIDEO_{a.pair.upper()}.mp4"
    qc = render(a.master, calib, imread(a.scene_master), a.wallpapers, a.pair,
                calib["pilot_pair"], out_path, a.frames, encode=not a.no_encode)
    (out_dir / f"video_{a.pair}.json").write_text(json.dumps(qc, indent=1))
    if a.no_encode:
        log(f"OLCUM video {a.pair} (kodlama yok): {'PASS' if qc['ok'] else 'FAIL'} | kare {qc['frames']} | "
            f"ekran disi maks {qc['outside_max']:.0f} | murekkep degisimi {qc['ink_change_mean']:.1f}"
            + (f" | kendini uretme ort {qc['self_mean']:.2f} maks {qc['self_max']:.0f}" if qc.get("self_mean") is not None else ""))
        raise SystemExit(0 if qc["ok"] else 2)
    log(f"SONUC video {a.pair}: {'PASS' if qc['ok'] else 'FAIL'} | {qc['out_w']}x{qc['out_h']} "
        f"{qc['out_fps']:.2f} fps {qc['out_frames']} kare {qc['duration_s']:.2f} sn {qc['size_bytes'] / 1e6:.2f} MB | "
        f"ekran disi maks {qc['outside_max']:.0f} | murekkep degisimi {qc['ink_change_mean']:.1f}"
        + (f" | kendini uretme ort {qc['self_mean']:.2f} maks {qc['self_max']:.0f}" if qc.get("self_mean") is not None else ""))
    if not qc["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
