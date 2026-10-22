#!/usr/bin/env python3
"""
DRIVE-TABANLI DENETIM (SALT OKUR): Etsy'ye DOKUNMAZ. 78 cift icin 6
boyutlu PASS/FAIL matrisi (kapsamli denetimin 1-6. maddeleri):

  c1_wp_sample   1248 wallpaper'dan rastgele N ornek: dosya/klasor adi
                 ile OCR (metin blogundan cift adi) eslesiyor mu.
                 Yalniz orneklenen ciftlerde deger var (digerleri NA).
  c2_pair_match  6 galeri gorseli + video ilk karesi: imza eslestirme
                 ile GERCEKTE dogru cift mi (verify_listing yontemi).
  c3_text        OCR TAM STRING karsilastirmasi (video + 6 galeri SET):
                 baska ciftten kalinti metin veya bozuk birlesme var mi.
  c4_aspect      EMEKLI (4 Eyl 2026) -> her zaman NA. Eski olcut kalibrasyon
                 quad'inin oranini kaynak wallpaper orani ile karsilastiriyordu;
                 bu esitlik yalniz stretch-to-fill'de zorunluydu. Crop-to-fill'e
                 gecildikten sonra quad orani ile kaynak oraninin farkli olmasi
                 BEKLENEN durumdur, kusur degil. Yerine gecen piksel tabanli
                 olcum: scripts/etsy/wp_audit_crop.py (doluluk + kirpma yuzdesi
                 + kirpilan alana oge girip girmedigi).
  c5_zip         4 edisyon ZIP (Drive/DELIVERY): icerik+sayim+isim.
  c6_integrity   Video acilip oynuyor mu (ffprobe), gorsel bozuk mu (PIL
                 verify), ZIP gercekten aciliyor mu (testzip).

Kullanim:
  wp_audit_drive.py --pairs-file pairs.txt --wp-samples _work/wp_samples
      --mock-dir _work/mock --video-dir _work/video --zip-dir _work/zip
      --calib _work/calib --out AUDIT_DRIVE.csv
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import DEVICES, EDITIONS, GALLERY_ORDER, SCENES, imread, log, warp_full  # noqa: E402
from verify_listing import signature, set_code  # noqa: E402
from wp_zip import ZIP_DEVICES  # noqa: E402

SIGNS = ["AQUARIUS", "ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA",
         "SCORPIO", "SAGITTARIUS", "CAPRICORN", "PISCES"]
# WP_LAYOUT_SPEC.md bolum 3 (DB, tum edisyonlarda ayni afin yerlesim, bolum 7.1):
# Metin blogu (isim+tagline) l,t,r,b. Watch: metin yok (B93).
TEXT_BOX = {"Phone": (107, 1724, 1357, 2658), "Tablet": (152, 1725, 1930, 2700),
            "Desktop": (285, 1245, 3603, 2154)}
VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_DUR = 1800, 1350, 30.0, 11.5
ASPECT_TOL = 0.03


def ocr(img_bgr, psm=6):
    tmp = Path(tempfile.mkstemp(suffix=".png")[1])
    try:
        cv2.imwrite(str(tmp), img_bgr)
        r = subprocess.run(["tesseract", str(tmp), "-", "--psm", str(psm)],
                           capture_output=True, text=True, timeout=30)
        return (r.stdout or "").upper()
    except (subprocess.TimeoutExpired, OSError):
        return ""
    finally:
        tmp.unlink(missing_ok=True)


def signs_in_text(text):
    return {s for s in SIGNS if s in text}


def fuzzy_garbled(text):
    """Herhangi bir burc adindan turemis ama tam eslesmeyen (bozuk birlesim) token
    var mi - hem beklenen ciftin hem yabanci bir ciftin adi bozulmus olabilir,
    ikisi de gercek bir kusurdur."""
    tokens = re.findall(r"[A-Z]{5,}", text)
    hits = []
    for t in tokens:
        if t in SIGNS:
            continue
        for s in SIGNS:
            if len(t) > len(s) and (s in t or t[:len(s)] == s):
                hits.append(t)
                break
    return hits


def text_check(img_bgr, box, expected_signs, label):
    """OCR + kalinti/bozuk metin tespiti. Donus: (ok, detail)."""
    l, t, r, b = box
    h, w = img_bgr.shape[:2]
    l, t, r, b = max(0, l), max(0, t), min(w, r), min(h, b)
    if r <= l or b <= t:
        return False, f"{label}: gecersiz kutu"
    crop = img_bgr[t:b, l:r]
    text = ocr(crop)
    found = signs_in_text(text)
    missing = expected_signs - found
    foreign = found - expected_signs
    garbled = fuzzy_garbled(text)
    ok = not missing and not foreign and not garbled
    detail = []
    if missing:
        detail.append(f"eksik {sorted(missing)}")
    if foreign:
        detail.append(f"YABANCI CIFT KALINTISI {sorted(foreign)}")
    if garbled:
        detail.append(f"BOZUK BIRLESIM {garbled}")
    return ok, (f"{label}: " + "; ".join(detail)) if detail else ""


def wallpaper_sample_check(path, pair):
    up = pair.upper()
    s1, s2 = up.split("_", 1)
    expected = {s1, s2}
    dev = next((d for d in DEVICES if f"_{d}." in path.name), None)
    if dev is None or dev == "Watch":
        return True, "" if dev == "Watch" else "cihaz turu belirlenemedi"
    try:
        img = imread(path)
    except FileNotFoundError:
        return False, "dosya okunamadi"
    box = TEXT_BOX[dev]
    ok, detail = text_check(img, box, expected, f"{path.name}")
    dims_ok = (img.shape[1], img.shape[0]) == DEVICES[dev]
    if not dims_ok:
        ok = False
        detail = (detail + "; " if detail else "") + f"olcu {img.shape[1]}x{img.shape[0]} (beklenen {DEVICES[dev]})"
    return ok, detail


def dewarp_screen(scene_img, quad, H, wp_w, wp_h):
    Hm = np.asarray(H, np.float64)
    Hinv = np.linalg.inv(Hm)
    return cv2.warpPerspective(scene_img, Hinv, (wp_w, wp_h), flags=cv2.INTER_CUBIC)


def aspect_of_quad(quad):
    q = np.asarray(quad, np.float32)
    top = np.linalg.norm(q[1] - q[0]); bottom = np.linalg.norm(q[2] - q[3])
    left = np.linalg.norm(q[3] - q[0]); right = np.linalg.norm(q[2] - q[1])
    w = (top + bottom) / 2; h = (left + right) / 2
    return w / h if h else 0.0


def check_gallery_pair_text_aspect(mock_dir, pair, calib, mock_refs):
    """c2 (imza), c3 (metin), c4 (oran) - galeri icin. Donus: dict per-scene."""
    up = pair.upper()
    s1, s2 = up.split("_", 1)
    expected = {s1, s2}
    out = {"c2_ok": True, "c2_detail": [], "c3_ok": True, "c3_detail": [],
           "c4_ok": None, "c4_detail": [], "c6_ok": True, "c6_detail": []}
    for scene in GALLERY_ORDER:
        name = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(scene=scene, pair=pair)
        p = Path(mock_dir) / up / name
        if not p.exists():
            out["c2_ok"] = out["c3_ok"] = out["c6_ok"] = False
            out["c2_detail"].append(f"{scene}: dosya yok")
            continue
        try:
            img = imread(p)
            Image.open(p).verify()
        except Exception as e:
            out["c6_ok"] = False; out["c6_detail"].append(f"{scene}: bozuk ({e})")
            continue
        # c2: imza eslesmesi (mevcut referans bankasi)
        sig = signature(p.read_bytes())
        cands = {pp: s for (pp, sc), s in mock_refs.items() if sc == scene}
        if cands:
            score, matched = max(((float(np.sum(sig * s)), pp) for pp, s in cands.items()))
            if matched.strip().lower() != pair.strip().lower() or score < 0.5:
                out["c2_ok"] = False
                out["c2_detail"].append(f"{scene}: eslesme {matched} (skor {score:.3f})")
        for s in calib["scenes"][scene]["screens"]:
            quad = s["quad"]; dev = s["device"]
            # c4 EMEKLI: quad orani vs kaynak orani karsilastirmasi crop-to-fill'de
            # anlamsiz (bkz. dosya basi). Olculmez, NA doner; yerine wp_audit_crop.py.
            # c3: dewarp + metin
            if dev == "Watch":
                continue
            wp_w, wp_h = DEVICES[dev]
            dew = dewarp_screen(img, quad, s["H"], wp_w, wp_h)
            box = TEXT_BOX.get(dev)
            if box:
                ok, detail = text_check(dew, box, expected, f"{scene}/{s['id']}")
                if not ok:
                    out["c3_ok"] = False
                    out["c3_detail"].append(detail)
    return out


def check_video(video_dir, pair, video_refs, calib):
    up = pair.upper()
    s1, s2 = up.split("_", 1)
    expected = {s1, s2}
    p = Path(video_dir) / up / f"WA_WP_VIDEO_{up}.mp4"
    if not p.exists():
        return dict(c2_ok=False, c2_detail="video yok", c3_ok=False, c3_detail="video yok",
                    c4_ok=False, c4_detail="video yok", c6_ok=False, c6_detail="video yok")
    probe = ffprobe(p)
    if not probe:
        return dict(c2_ok=False, c2_detail="", c3_ok=False, c3_detail="",
                    c4_ok=False, c4_detail="", c6_ok=False, c6_detail="ffprobe basarisiz/bozuk")
    w, h, fps, dur = probe
    c6_ok = w > 0 and h > 0
    c4_ok = abs(w - VIDEO_W) < 2 and abs(h - VIDEO_H) < 2 and abs(fps - VIDEO_FPS) < 0.5 and abs(dur - VIDEO_DUR) < 1.0
    c4_detail = "" if c4_ok else f"olcu {w}x{h} {fps:.1f}fps {dur:.1f}sn (beklenen {VIDEO_W}x{VIDEO_H} {VIDEO_FPS}fps {VIDEO_DUR}sn)"
    frame = ffmpeg_frame(p)
    c2_ok, c2_detail, c3_ok, c3_detail = True, "", True, ""
    if frame is not None and video_refs:
        sig = signature(cv2.imencode(".jpg", frame)[1].tobytes())
        score, matched = max(((float(np.sum(sig * s)), pp) for pp, s in video_refs.items()))
        if matched.strip().lower() != pair.strip().lower() or score < 0.5:
            c2_ok = False
            c2_detail = f"eslesme {matched} (skor {score:.3f})"
        for s in calib["scenes"]["SET01"]["screens"]:
            dev = s["device"]
            if dev == "Watch":
                continue
            quad = np.asarray(s["quad"], np.float32) * (frame.shape[1] / 3000.0)
            wp_w, wp_h = DEVICES[dev]
            Hm = cv2.getPerspectiveTransform(
                np.float32([[0, 0], [wp_w, 0], [wp_w, wp_h], [0, wp_h]]), quad)
            dew = dewarp_screen(frame, quad, Hm, wp_w, wp_h)
            box = TEXT_BOX.get(dev)
            if box:
                ok, detail = text_check(dew, box, expected, f"video/{s['id']}")
                if not ok:
                    c3_ok = False
                    c3_detail = detail
    elif frame is None:
        c6_ok = False
    return dict(c2_ok=c2_ok, c2_detail=c2_detail, c3_ok=c3_ok, c3_detail=c3_detail,
                c4_ok=c4_ok, c4_detail=c4_detail, c6_ok=c6_ok, c6_detail="")


def ffprobe(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                            "-of", "default=noprint_wrappers=1", str(path)],
                           timeout=60, capture_output=True, text=True)
        vals = dict(line.split("=", 1) for line in r.stdout.strip().splitlines() if "=" in line)
        w = int(vals.get("width", 0)); h = int(vals.get("height", 0))
        dur = float(vals.get("duration", 0))
        fr = vals.get("r_frame_rate", "0/1")
        num, den = fr.split("/") if "/" in fr else (fr, "1")
        fps = float(num) / float(den) if float(den) else 0.0
        return (w, h, fps, dur) if w and h else None
    except (subprocess.TimeoutExpired, OSError, ValueError, ZeroDivisionError):
        return None


def ffmpeg_frame(path):
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
                            "-vframes", "1", str(tmp)], timeout=60)
        if r.returncode != 0 or not tmp.exists():
            return None
        return cv2.imread(str(tmp))
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        tmp.unlink(missing_ok=True)


def check_zip(zip_dir, pair):
    up = pair.upper()
    ok, details = True, []
    for ed in EDITIONS:
        p = Path(zip_dir) / up / f"AstroLove_{pair}_{ed}.zip"
        if not p.exists():
            ok = False; details.append(f"{ed}: yok"); continue
        try:
            with zipfile.ZipFile(p) as zf:
                bad = zf.testzip()
                if bad:
                    ok = False; details.append(f"{ed}: bozuk uye {bad}"); continue
                want = sorted([f"AstroLove_{pair}_{ed}_{dev}.jpg" for dev in ZIP_DEVICES] + ["LICENSE.txt"])
                got = sorted(zf.namelist())
                if got != want:
                    ok = False; details.append(f"{ed}: icerik {got}")
                for dev in ZIP_DEVICES:
                    data = zf.read(f"AstroLove_{pair}_{ed}_{dev}.jpg")
                    im = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                    if im is None or (im.shape[1], im.shape[0]) != DEVICES[dev]:
                        ok = False; details.append(f"{ed}/{dev}: olcu/bozuk")
        except zipfile.BadZipFile:
            ok = False; details.append(f"{ed}: ZIP acilamiyor")
    return ok, "; ".join(details)


def load_mock_refs(mock_dir):
    out = {}
    for d in sorted(Path(mock_dir).iterdir()):
        if not d.is_dir():
            continue
        for f in d.glob("WA_MOCKUP_V2_*_FINAL.jpg"):
            out[(d.name, set_code(f.name))] = signature(f.read_bytes())
    return out


def load_video_refs(video_dir):
    out = {}
    for d in sorted(Path(video_dir).iterdir()):
        if not d.is_dir():
            continue
        vids = list(d.glob("WA_WP_VIDEO_*.mp4"))
        if not vids:
            continue
        frame = ffmpeg_frame(vids[0])
        if frame is not None:
            out[d.name] = signature(cv2.imencode(".jpg", frame)[1].tobytes())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--wp-samples", required=True, help="20 orneklenen wallpaper (duz klasor)")
    ap.add_argument("--mock-dir", required=True)
    ap.add_argument("--video-dir", default="", help="--no-video ile bos birakilabilir")
    ap.add_argument("--no-video", action="store_true",
                    help="video maddelerini atla (4 Eyl 2026: 78 ilan videosuz yayinlanacak)")
    ap.add_argument("--zip-dir", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pairs = [p.strip() for p in Path(a.pairs_file).read_text().split() if p.strip()]
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    log(f"{len(pairs)} cift denetlenecek")

    log("referans bankalari yukleniyor...")
    mock_refs = load_mock_refs(a.mock_dir)
    video_refs = {} if a.no_video else load_video_refs(a.video_dir)
    log(f"galeri referans: {len(mock_refs)}, video referans: "
        + ("ATLANDI (--no-video)" if a.no_video else str(len(video_refs))))

    sample_files = {p.name: p for p in Path(a.wp_samples).glob("*.jpg")}
    sample_by_pair = {}
    for name, p in sample_files.items():
        m = re.match(r"AstroLove_([A-Za-z]+_[A-Za-z]+)_", name)
        if m:
            sample_by_pair.setdefault(m.group(1), []).append(p)
    log(f"wallpaper ornegi: {len(sample_files)} dosya, {len(sample_by_pair)} cift")

    rows = []
    t0 = time.time()
    for i, pair in enumerate(pairs):
        row = dict(pair=pair)
        c1_vals = []
        for p in sample_by_pair.get(pair, []):
            ok, detail = wallpaper_sample_check(p, pair)
            c1_vals.append((ok, detail))
        if c1_vals:
            row["c1_wp_sample"] = "PASS" if all(v[0] for v in c1_vals) else "FAIL"
            row["c1_detail"] = "; ".join(d for ok, d in c1_vals if d)
        else:
            row["c1_wp_sample"], row["c1_detail"] = "NA", ""

        g = check_gallery_pair_text_aspect(a.mock_dir, pair, calib, mock_refs)
        # --no-video: video maddeleri denetim disi; notr (True) doner ki galeri
        # sonuclari degismesin. Kapsam disi olan sey FAIL sayilmaz.
        v = (dict(c2_ok=True, c2_detail="", c3_ok=True, c3_detail="",
                  c4_ok=True, c4_detail="", c6_ok=True, c6_detail="")
             if a.no_video else check_video(a.video_dir, pair, video_refs, calib))
        z_ok, z_detail = check_zip(a.zip_dir, pair)

        row["c2_pair_match"] = "PASS" if (g["c2_ok"] and v["c2_ok"]) else "FAIL"
        row["c3_text"] = "PASS" if (g["c3_ok"] and v["c3_ok"]) else "FAIL"
        row["c4_aspect"] = "NA"          # emekli olcut; yerine wp_audit_crop.py
        row["c5_zip"] = "PASS" if z_ok else "FAIL"
        row["c6_integrity"] = "PASS" if (g["c6_ok"] and v["c6_ok"]) else "FAIL"
        row["detail"] = "; ".join(x for x in [
            "; ".join(g["c2_detail"]), v.get("c2_detail", ""), "; ".join(g["c3_detail"]),
            v.get("c3_detail", ""), "; ".join(g["c4_detail"]), v.get("c4_detail", ""),
            z_detail, "; ".join(g["c6_detail"]), v.get("c6_detail", "")] if x)
        rows.append(row)
        el = time.time() - t0
        overall = "PASS" if all(row[c] in ("PASS", "NA") for c in
                                 ["c1_wp_sample", "c2_pair_match", "c3_text", "c4_aspect", "c5_zip", "c6_integrity"]) else "FAIL"
        log(f"[{i+1}/{len(pairs)}] {pair}: {overall}" + (f" | {row['detail'][:200]}" if row["detail"] else "")
            + f" | gecen {el/60:.1f} dk kalan {el/(i+1)*(len(pairs)-i-1)/60:.1f} dk")

    cols = ["pair", "c1_wp_sample", "c2_pair_match", "c3_text", "c4_aspect", "c5_zip", "c6_integrity", "detail"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])

    for c in cols[1:-1]:
        n_pass = sum(1 for r in rows if r[c] == "PASS")
        n_na = sum(1 for r in rows if r[c] == "NA")
        log(f"  {c}: {n_pass}/{len(rows)} PASS" + (f" ({n_na} NA)" if n_na else ""))
    n_fail = sum(1 for r in rows if any(r[c] == "FAIL" for c in cols[1:-1]))
    log(f"SONUC drive denetimi: {len(rows)-n_fail}/{len(rows)} tum kolonlar temiz")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## drive denetimi (1-6): {len(rows)-n_fail}/{len(rows)} tum kolonlar temiz\n\n")
            fh.write("| pair | " + " | ".join(cols[1:-1]) + " |\n|" + "---|" * (len(cols) - 1) + "\n")
            for r in rows:
                if any(r[c] == "FAIL" for c in cols[1:-1]):
                    fh.write("| " + " | ".join(str(r.get(c, "")) for c in cols[:-1]) + f" | {r['detail'][:300]} |\n")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
