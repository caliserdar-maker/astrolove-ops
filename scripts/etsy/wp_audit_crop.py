#!/usr/bin/env python3
"""
DENETIM KAPANISI (SALT OKUR, DUZELTME YOK) - 4 Eyl 2026 Mo gorevi.

Uc is tek gecistedir; hicbir uretim dosyasi degistirilmez, Etsy'ye dokunulmaz:

  MADDE 1  Tek FAIL alan ciftin (varsayilan Cancer_Leo) 16 wallpaper'inin
           TAMAMI denetlenir (ozgun kosunun rastgele ornegi log'a yazilmadigi
           icin geri getirilemez; tam tarama onun yerine gecer ve
           tekrarlanabilir). FAIL alan dosyanin metin blogundan TAM
           COZUNURLUKTE (yeniden orneklemesiz) kirpma uretilir.

  MADDE 3  6 galeri sahnesinin her ekraninda OCR tam-string kontrolu IKI
           dewarp ile yapilir ve ikisi de raporlanir (karar verilmez):
             eski = inv(kalibrasyon H)   -> stretch-to-fill varsayimi
             yeni = inv(cover H)         -> crop-to-fill (render'in gercegi)
           Bayrak alan her ekranin ad/metin bolgesinden AYRI dosya olarak
           tam cozunurluklu kirpma uretilir (sahne JPEG'inden dogrudan,
           yeniden ornekleme yok).

  MADDE 4  Eski olcut (quad orani vs kaynak orani) crop-to-fill'de anlamsiz
           oldugu icin EMEKLI edildi (wp_audit_drive.py c4 -> NA). Yerine
           RENDER EDILMIS PIKSELE bakan olcut:
             a) ekran quad'i tamamen dolu mu  - kaynak wallpaper cover ile ayni
                quad'a yeniden yerlestirilir; ic bolge ve kenar bandinda ortalama
                mutlak fark olculur (bosluk/yanlis olcek once kenar bandinda
                farki buyutur). NCC referans olarak birlikte raporlanir.
             b) kaynagin yuzde kaci kirpildi, hangi kenardan
             c) kirpilan alana tasarim ogesi giriyor mu - halka, sembol,
                metin blogu (WP_LAYOUT_SPEC.md bolum 3, DB olcumu; ayni afin
                yerlesim tum edisyonlarda gecerli kabul edilir)
           78 cift x 6 sahne x tum ekranlar kosar.

Kullanim:
  wp_audit_crop.py --pairs-file pairs.txt --mock-dir _work/mock --calib _work/calib
      --m01-pair Cancer_Leo --m01-wp-dir _work/wp_m01
      --out-m04 M04.csv --out-m03 M03.csv --crop-dir _work/crops
  wp_audit_crop.py --selftest        # dosyasiz sentetik geometri dogrulamasi
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import (DEVICES, GALLERY_ORDER, SCENES, aspect_of_quad,  # noqa: E402
                              cover_homography, cover_src_rect, imread, log,
                              poly_mask, warp_cover)
from wp_audit_drive import TEXT_BOX, ocr, signs_in_text, fuzzy_garbled  # noqa: E402

# WP_LAYOUT_SPEC.md bolum 3: Deep Black uzerinde OLCULEN oge kutulari
# (l,t,r,b; kaynak wallpaper piksel koordinati). Bolum 7.1'e gore yerlesim
# tum edisyonlarda ayni afin duzendedir; kirpma testi bu kutulari kullanir.
ELEMENTS = {
    "Phone": {"halka": (183, 868, 1257, 1746), "sembol": (386, 1269, 1035, 1553),
              "metin": (107, 1724, 1357, 2658)},
    "Tablet": {"halka": (260, 507, 1788, 1755), "sembol": (549, 1078, 1472, 1481),
               "metin": (152, 1725, 1930, 2700)},
    "Desktop": {"halka": (1207, 107, 2633, 1271), "sembol": (1476, 640, 2338, 1016),
                "metin": (285, 1245, 3603, 2154)},
    "Watch": {"sembol": (106, 236, 895, 976)},
}

# Doluluk olcutu: ic bolge = quad'in %6 icine cekilmis hali (yuvarlak koseler
# ve Dynamic Island disarida kalsin); kenar bandi = %1.5 ile %6 arasi serit,
# kose kareleri (%15) haric. Bosluk/tasma once kenar bandinda gorunur.
INSET_IC = 0.06
INSET_KENAR = 0.015
CORNER_FRAC = 0.15
# Doluluk hukmu ORTALAMA MUTLAK FARK ile verilir: NCC duz zeminli edisyonlarda
# (DB = saf siyah kenar) varyans sifira indigi icin tanimsiz olur. MAD esikleri
# kalibrasyonun kendi olcumunden gelir (calib.json inside_mean 0.8-4.1, Watch
# relight 7.9 / p95 19.3). NCC yine hesaplanir, referans olarak raporlanir.
MAD_MAX = 12.0
MAD_MAX_RELIGHT = 25.0
CROP_MARGIN = 14   # kirpmalarda kenar payi (px, tam cozunurluk korunur)
CROP_LIMIT = 250   # emniyet siniri: kirpma sayisi kacmasin


# ------------------------------------------------------------------ geometri
def crop_geometry(device, quad):
    """cover (crop-to-fill) kirpmasinin OLCUMU. Piksel gerektirmez; quad ve
    cihaz tuvalinden turer, bu yuzden ciftler arasi degismez."""
    W0, H0 = DEVICES[device]
    a_q = aspect_of_quad(quad)
    a_src = W0 / H0
    src = cover_src_rect(W0, H0, a_q)
    x0, y0 = float(src[0][0]), float(src[0][1])
    x1, y1 = float(src[2][0]), float(src[2][1])
    kept = (x1 - x0) * (y1 - y0)
    pct = 100.0 * (1.0 - kept / (W0 * H0))
    edges = []
    if x0 > 0.5 or W0 - x1 > 0.5:
        edges.append(f"sol {x0:.0f}px sag {W0 - x1:.0f}px")
    if y0 > 0.5 or H0 - y1 > 0.5:
        edges.append(f"ust {y0:.0f}px alt {H0 - y1:.0f}px")
    clipped = []
    for name, (l, t, r, b) in ELEMENTS.get(device, {}).items():
        over = {"sol": x0 - l, "sag": r - x1, "ust": y0 - t, "alt": b - y1}
        hit = [f"{k} {v:.0f}px" for k, v in over.items() if v > 0.5]
        if hit:
            clipped.append(f"{name}({', '.join(hit)})")
    return dict(quad_aspect=a_q, src_aspect=a_src, kept=(x0, y0, x1, y1),
                crop_pct=pct, edges="; ".join(edges) or "yok",
                clipped="; ".join(clipped) or "yok", clipped_any=bool(clipped))


def inset_quad(quad, frac):
    q = np.asarray(quad, np.float32)
    c = q.mean(axis=0)
    return c + (q - c) * (1.0 - frac)


def corner_block_mask(shape, quad):
    """Quad koselerindeki kare bloklar (yuvarlak kose / cerceve etkisi disarida
    kalsin diye kenar bandindan cikarilir)."""
    q = np.asarray(quad, np.float32)
    side = float(min(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[3] - q[0]))) * CORNER_FRAC
    m = np.zeros(shape[:2], np.uint8)
    for p in q:
        cv2.rectangle(m, (int(p[0] - side), int(p[1] - side)),
                      (int(p[0] + side), int(p[1] + side)), 255, -1)
    return m


def stats(a, b, sel):
    """Secili piksellerde (ortalama mutlak fark, NCC). Varyans sifirsa NCC nan."""
    x = a[sel].astype(np.float64)
    y = b[sel].astype(np.float64)
    if x.size < 200:
        return float("nan"), float("nan")
    mad = float(np.abs(x - y).mean())
    xc, yc = x - x.mean(), y - y.mean()
    d = float(np.sqrt((xc * xc).sum()) * np.sqrt((yc * yc).sum()))
    return mad, (float((xc * yc).sum() / d) if d > 0 else float("nan"))


def fill_check(scene, wp, quad):
    """Render edilmis pikselde doluluk: kaynak wallpaper cover ile ayni quad'a
    yeniden yerlestirilir; ic bolge ve kenar bandinda fark olculur. Bosluk
    (wallpaper quad'i doldurmuyor) veya yanlis olcek once kenar bandinda
    farki buyutur. Donus: (mad_ic, mad_kenar, ncc_ic, ncc_kenar, n_ic, n_kenar)."""
    wn = warp_cover(wp, quad, scene.shape)
    g1 = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(wn, cv2.COLOR_BGR2GRAY)
    m_ic = poly_mask(scene.shape, inset_quad(quad, INSET_IC)) > 0
    m_out = poly_mask(scene.shape, inset_quad(quad, INSET_KENAR)) > 0
    m_kenar = m_out & ~m_ic & ~(corner_block_mask(scene.shape, quad) > 0)
    mad_ic, ncc_ic = stats(g1, g2, m_ic)
    mad_kn, ncc_kn = stats(g1, g2, m_kenar)
    return mad_ic, mad_kn, ncc_ic, ncc_kn, int(m_ic.sum()), int(m_kenar.sum())


# ------------------------------------------------------------------ kirpma
def crop_native(img, box, margin=CROP_MARGIN):
    """Tam cozunurlukte (yeniden ornekleme YOK) eksen-hizali kirpma."""
    h, w = img.shape[:2]
    l, t, r, b = box
    l = max(0, int(np.floor(l)) - margin); t = max(0, int(np.floor(t)) - margin)
    r = min(w, int(np.ceil(r)) + margin); b = min(h, int(np.ceil(b)) + margin)
    return img[t:b, l:r] if r > l and b > t else None


def project_box(box, H):
    l, t, r, b = box
    pts = np.float32([[l, t], [r, t], [r, b], [l, b]]).reshape(-1, 1, 2)
    p = cv2.perspectiveTransform(pts, np.asarray(H, np.float64)).reshape(-1, 2)
    return float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()), float(p[:, 1].max())


def save_crop(path, img):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 97])
    return f"{img.shape[1]}x{img.shape[0]}"


# ------------------------------------------------------------------ madde 1
def madde1(pair, wp_dir, crop_dir):
    """Ciftin 16 wallpaper'inin TAMAMI: OCR tam metni + PASS/FAIL + FAIL'de kirpma."""
    up = pair.upper()
    s1, s2 = up.split("_", 1)
    expected = {s1, s2}
    rows = []
    files = sorted(Path(wp_dir).glob(f"AstroLove_{pair}_*.jpg"))
    log(f"[madde 1] {pair}: {len(files)} dosya taraniyor (beklenen 16)")
    for p in files:
        dev = next((d for d in DEVICES if f"_{d}." in p.name), None)
        row = dict(dosya=p.name, cihaz=dev or "?", sonuc="NA", ocr="", detay="")
        if dev is None:
            row["detay"] = "cihaz turu belirlenemedi"; rows.append(row); continue
        img = imread(p)
        boyut_ok = (img.shape[1], img.shape[0]) == DEVICES[dev]
        if dev == "Watch":
            # B93: Watch'ta metin yok - OCR maddesi kapsam disi, yalniz olcu.
            row["sonuc"] = "PASS" if boyut_ok else "FAIL"
            row["detay"] = "" if boyut_ok else f"olcu {img.shape[1]}x{img.shape[0]}"
            row["ocr"] = "(Watch: metin yok, OCR kapsam disi)"
            rows.append(row); continue
        box = TEXT_BOX[dev]
        text = ocr(img[box[1]:box[3], box[0]:box[2]])
        flat = " ".join(text.split())
        found = signs_in_text(text)
        missing = sorted(expected - found)
        foreign = sorted(found - expected)
        garbled = fuzzy_garbled(text)
        ok = boyut_ok and not missing and not foreign and not garbled
        det = []
        if not boyut_ok:
            det.append(f"olcu {img.shape[1]}x{img.shape[0]} (beklenen {DEVICES[dev]})")
        if missing:
            det.append(f"eksik {missing}")
        if foreign:
            det.append(f"YABANCI {foreign}")
        if garbled:
            det.append(f"BOZUK BIRLESIM {garbled}")
        row["sonuc"] = "PASS" if ok else "FAIL"
        row["ocr"] = flat[:300]
        row["detay"] = "; ".join(det)
        if not ok:
            c = crop_native(img, box)
            if c is not None:
                name = f"M01_{p.stem}_METIN.jpg"
                row["kirpma"] = f"{name} ({save_crop(Path(crop_dir) / name, c)})"
        log(f"  {p.name}: {row['sonuc']} | OCR='{flat[:110]}'"
            + (f" | {row['detay']}" if row["detay"] else ""))
        rows.append(row)
    return rows


# ------------------------------------------------------------------ ana dongu
def screen_text(scene_img, quad, H_stored, device, expected):
    """Iki dewarp ile OCR: (eski_ok, eski_detay, eski_metin, yeni_ok, yeni_detay, yeni_metin)."""
    W0, H0 = DEVICES[device]
    box = TEXT_BOX[device]
    Hc, _ = cover_homography((H0, W0, 3), quad)
    out = []
    for H in (np.asarray(H_stored, np.float64), Hc.astype(np.float64)):
        dew = cv2.warpPerspective(scene_img, np.linalg.inv(H), (W0, H0), flags=cv2.INTER_CUBIC)
        text = ocr(dew[box[1]:box[3], box[0]:box[2]])
        found = signs_in_text(text)
        missing = sorted(expected - found)
        foreign = sorted(found - expected)
        garbled = fuzzy_garbled(text)
        det = []
        if missing:
            det.append(f"eksik {missing}")
        if foreign:
            det.append(f"YABANCI {foreign}")
        if garbled:
            det.append(f"BOZUK BIRLESIM {garbled}")
        out += [not det, "; ".join(det), " ".join(text.split())[:200]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pairs-file")
    ap.add_argument("--mock-dir")
    ap.add_argument("--calib")
    ap.add_argument("--wp-dir", default="", help="cover doluluk olcumu icin wallpaper koku (<CIFT>/ altinda)")
    ap.add_argument("--m01-pair", default="Cancer_Leo")
    ap.add_argument("--m01-wp-dir", default="")
    ap.add_argument("--crop-dir", default="_crops")
    ap.add_argument("--out-m04", default="M04.csv")
    ap.add_argument("--out-m03", default="M03.csv")
    ap.add_argument("--out-m01", default="M01.csv")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    pairs = [p.strip() for p in Path(a.pairs_file).read_text().split() if p.strip()]
    if a.limit:
        pairs = pairs[:a.limit]

    # --- madde 4 (a): cift-degismez kirpma geometrisi, bir kez raporlanir
    geo = {}
    log("=== MADDE 4: kirpma geometrisi (quad + tuvalden turer, ciftler arasi ayni) ===")
    for scene in GALLERY_ORDER:
        for s in calib["scenes"][scene]["screens"]:
            g = crop_geometry(s["device"], s["quad"])
            geo[(scene, s["id"])] = g
            log(f"  {scene}/{s['id']} {s['device']:<7} oran {g['quad_aspect']:.4f} "
                f"(kaynak {g['src_aspect']:.4f}) kirpma %{g['crop_pct']:.2f} [{g['edges']}] "
                f"OGE: {g['clipped']}")

    # --- madde 1
    m01_rows = []
    if a.m01_wp_dir and Path(a.m01_wp_dir).exists():
        m01_rows = madde1(a.m01_pair, a.m01_wp_dir, a.crop_dir)

    # --- madde 3 + 4 (b): 78 cift x 6 sahne
    m04_rows, m03_rows = [], []
    t0 = time.time()
    total = len(pairs)
    for i, pair in enumerate(pairs):
        up = pair.upper()
        s1, s2 = up.split("_", 1)
        expected = {s1, s2}
        for scene in GALLERY_ORDER:
            name = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
                scene=scene, pair=pair)
            p = Path(a.mock_dir) / up / name
            if not p.exists():
                m04_rows.append(dict(pair=pair, scene=scene, screen="-", device="-",
                                     verdict="FAIL", detail="sahne dosyasi yok"))
                continue
            scene_img = imread(p)
            for s in calib["scenes"][scene]["screens"]:
                dev, sid, quad = s["device"], s["id"], s["quad"]
                g = geo[(scene, sid)]
                row = dict(pair=pair, scene=scene, screen=sid, device=dev,
                           edition=s.get("edition", ""), mode=s.get("mode", ""),
                           quad_aspect=f"{g['quad_aspect']:.4f}",
                           src_aspect=f"{g['src_aspect']:.4f}",
                           crop_pct=f"{g['crop_pct']:.2f}", crop_edges=g["edges"],
                           clipped=g["clipped"], mad_ic="", mad_kenar="",
                           ncc_ic="", ncc_kenar="", verdict="", detail="")
                # doluluk (piksel): kaynak wallpaper varsa
                wp_p = Path(a.wp_dir) / up / f"AstroLove_{pair}_{s.get('edition')}_{dev}.jpg" \
                    if a.wp_dir else None
                if wp_p is not None and wp_p.exists():
                    try:
                        d_ic, d_kn, n_ic, n_kn, _, _ = fill_check(scene_img, imread(wp_p), quad)
                        lim = MAD_MAX_RELIGHT if s.get("mode") == "relight" else MAD_MAX
                        row["mad_ic"] = f"{d_ic:.2f}"; row["mad_kenar"] = f"{d_kn:.2f}"
                        row["ncc_ic"] = f"{n_ic:.4f}"; row["ncc_kenar"] = f"{n_kn:.4f}"
                        dolu = (d_ic <= lim and d_kn <= lim)
                        row["verdict"] = "PASS" if dolu else "FAIL"
                        if not dolu:
                            row["detail"] = (f"doluluk: ic fark {d_ic:.1f} kenar fark {d_kn:.1f} "
                                             f"(esik {lim}, NCC ic {n_ic:.3f} kenar {n_kn:.3f})")
                    except Exception as e:                       # olcum kurtarilir, kosu durmaz
                        row["verdict"] = "NA"; row["detail"] = f"doluluk olculemedi: {e}"
                else:
                    row["verdict"] = "NA"; row["detail"] = "kaynak wallpaper yok (doluluk olculmedi)"
                m04_rows.append(row)

                # madde 3: metin (Watch'ta metin yok)
                if dev == "Watch":
                    continue
                (ok_o, det_o, txt_o, ok_n, det_n, txt_n) = screen_text(
                    scene_img, quad, s["H"], dev, expected)
                if not ok_o or not ok_n:
                    cname = ""
                    # Kirpma YALNIZ ozgun bulgu icin (eski dewarp bayragi) - Mo'nun
                    # istedigi "bulgu alan 30 cift" kumesi budur; yeni dewarp sonucu
                    # ayni satirda sayi olarak raporlanir, kirpma uretmez.
                    if not ok_o and len(m03_rows) < CROP_LIMIT:
                        Hc, _ = cover_homography((DEVICES[dev][1], DEVICES[dev][0], 3), quad)
                        c = crop_native(scene_img, project_box(TEXT_BOX[dev], Hc))
                        if c is not None:
                            cname = f"M03_{pair}_{scene}_s{sid}_{dev}.jpg"
                            save_crop(Path(a.crop_dir) / cname, c)
                    m03_rows.append(dict(pair=pair, scene=scene, screen=sid, device=dev,
                                         eski_sonuc="PASS" if ok_o else "FAIL", eski_detay=det_o,
                                         eski_ocr=txt_o,
                                         yeni_sonuc="PASS" if ok_n else "FAIL", yeni_detay=det_n,
                                         yeni_ocr=txt_n, kirpma=cname))
        el = time.time() - t0
        log(f"[{i+1}/{total}] {pair} | gecen {el/60:.1f} dk "
            f"kalan {el/(i+1)*(total-i-1)/60:.1f} dk | %{100*(i+1)/total:.0f}")

    write_csv(a.out_m04, m04_rows)
    write_csv(a.out_m03, m03_rows)
    write_csv(a.out_m01, m01_rows)
    summary(m01_rows, m03_rows, m04_rows, geo)
    return 0


def write_csv(path, rows):
    if not rows:
        log(f"{path}: satir yok, yazilmadi")
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"{path}: {len(rows)} satir")


def summary(m01, m03, m04, geo):
    lines = ["## denetim kapanisi (madde 1 / 3 / 4)", ""]
    lines.append(f"- madde 1: {sum(1 for r in m01 if r['sonuc'] == 'PASS')} PASS / "
                 f"{sum(1 for r in m01 if r['sonuc'] == 'FAIL')} FAIL / {len(m01)} dosya")
    v = [r.get("verdict") for r in m04]
    lines.append(f"- madde 4 (yeni, piksel): {v.count('PASS')} PASS / {v.count('FAIL')} FAIL / "
                 f"{v.count('NA')} NA / {len(m04)} ekran")
    lines.append(f"- madde 3: {len(m03)} bayrakli ekran "
                 f"(eski dewarp FAIL {sum(1 for r in m03 if r['eski_sonuc'] == 'FAIL')}, "
                 f"yeni dewarp FAIL {sum(1 for r in m03 if r['yeni_sonuc'] == 'FAIL')})")
    lines += ["", "### madde 4a: kirpma geometrisi (ciftler arasi degismez)", "",
              "| sahne/ekran | cihaz | quad orani | kaynak orani | kirpma % | kenar | KIRPILAN OGE |",
              "|---|---|---|---|---|---|---|"]
    for (scene, sid), g in geo.items():
        lines.append(f"| {scene}/{sid} | - | {g['quad_aspect']:.4f} | {g['src_aspect']:.4f} | "
                     f"{g['crop_pct']:.2f} | {g['edges']} | {g['clipped']} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


# ------------------------------------------------------------------ selftest
def selftest():
    """Dosyasiz sentetik dogrulama: kirpma geometrisi, oge kesisimi ve doluluk
    olcutu (bilerek bosluk birakilan sahnede kenar bandi dusmeli)."""
    ok = True

    # 1) cover_src_rect yonu ve oran
    src = cover_src_rect(3840, 2160, 1.536)           # kaynak genis -> yanlardan
    assert src[0][1] == 0 and src[2][1] == 2160, src
    w = float(src[1][0] - src[0][0])
    ok &= abs(w / 2160 - 1.536) < 1e-3
    log(f"selftest cover Desktop: kept_w={w:.0f} oran={w/2160:.4f} x0={src[0][0]:.0f}")
    src = cover_src_rect(1440, 3200, 0.479)           # kaynak dar -> ust/alttan
    assert src[0][0] == 0 and src[1][0] == 1440, src
    h = float(src[2][1] - src[0][1])
    ok &= abs(1440 / h - 0.479) < 1e-3
    log(f"selftest cover Phone: kept_h={h:.0f} oran={1440/h:.4f} y0={src[0][1]:.0f}")

    # 2) oge kesisimi - Desktop 1.536 metin blogu saga tasar mi
    q = np.float32([[0, 0], [1536, 0], [1536, 1000], [0, 1000]])
    g = crop_geometry("Desktop", q)
    log(f"selftest Desktop 1.536: kirpma %{g['crop_pct']:.2f} [{g['edges']}] OGE {g['clipped']}")
    ok &= g["crop_pct"] > 0
    q = np.float32([[0, 0], [479, 0], [479, 1000], [0, 1000]])
    g = crop_geometry("Phone", q)
    log(f"selftest Phone 0.479: kirpma %{g['crop_pct']:.2f} [{g['edges']}] OGE {g['clipped']}")

    # 3) doluluk olcutu: dogru yerlesim ~1.0, bosluklu yerlesim kenarda duser
    rng = np.random.default_rng(7)
    wp = rng.integers(0, 255, (800, 360, 3), dtype=np.uint8)
    wp = cv2.GaussianBlur(wp, (0, 0), 1.2)
    quad = np.float32([[100, 60], [420, 62], [418, 780], [98, 778]])
    scene = np.full((900, 600, 3), 30, np.uint8)
    wn = warp_cover(wp, quad, scene.shape)
    m = poly_mask(scene.shape, quad) > 0
    scene[m] = wn[m]
    d_ic, d_kn, n_ic, n_kn, a_ic, a_kn = fill_check(scene, wp, quad)
    log(f"selftest doluluk (dogru): fark ic {d_ic:.2f} kenar {d_kn:.2f} | "
        f"NCC ic {n_ic:.4f} kenar {n_kn:.4f} | piksel {a_ic}/{a_kn}")
    ok &= d_ic <= MAD_MAX and d_kn <= MAD_MAX
    # bosluk: wallpaper quad'in %88'ine sigdirilir -> kenar bandi zemin kalir
    scene2 = np.full((900, 600, 3), 30, np.uint8)
    small = inset_quad(quad, 0.12)
    wn2 = warp_cover(wp, small, scene2.shape)
    m2 = poly_mask(scene2.shape, small) > 0
    scene2[m2] = wn2[m2]
    d_ic2, d_kn2, n_ic2, n_kn2, _, _ = fill_check(scene2, wp, quad)
    log(f"selftest doluluk (bosluklu): fark ic {d_ic2:.2f} kenar {d_kn2:.2f} | "
        f"NCC ic {n_ic2:.4f} kenar {n_kn2:.4f}")
    ok &= d_kn2 > MAD_MAX
    # 4) duz siyah zemin (DB): NCC tanimsiz olur, MAD yine dogru hukmu vermeli
    wp3 = np.zeros((800, 360, 3), np.uint8)
    cv2.circle(wp3, (180, 300), 90, (220, 165, 48), 8)
    scene3 = np.full((900, 600, 3), 30, np.uint8)
    wn3 = warp_cover(wp3, quad, scene3.shape)
    m3 = poly_mask(scene3.shape, quad) > 0
    scene3[m3] = wn3[m3]
    d_ic3, d_kn3, n_ic3, n_kn3, _, _ = fill_check(scene3, wp3, quad)
    log(f"selftest duz zemin (DB benzeri): fark ic {d_ic3:.2f} kenar {d_kn3:.2f} | "
        f"NCC ic {n_ic3:.4f} kenar {n_kn3:.4f}")
    ok &= d_ic3 <= MAD_MAX and d_kn3 <= MAD_MAX
    log("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
