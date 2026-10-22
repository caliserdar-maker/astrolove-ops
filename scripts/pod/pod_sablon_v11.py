#!/usr/bin/env python3
"""POD sablon V11 - panel ici, ciftin V01 MB videosundan REFERANSIN donusumuyle.

Tarif (olculdu): canli referans 843084674 = [oda: referansin baytlari] +
[panel ici: V01 <cift> MIDNIGHT_BLUE videosu; olcek 1.1607, tx -106.6,
ty -3.9, donme 0]. Panel ici MAE 1.82 (Aquarius+Gemini).

Kompozit ham yuv420p duzleminde yapilir: panel disi referansin baytlari
degismez; panel ici, warpAffine ile hizalanan V01 karesidir. Cerceve ic
kenarinda 2 px yumusak gecis.

Etsy'ye yazma yok.
"""
import argparse
import json
import pathlib
import sys
import time

import cv2
import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_cover_gold_b_transform import build_candidate, load_luts  # noqa: E402
from pod_sablon_v4 import (KAPAK, kareleri_ac, rgb_yuv_doseme,  # noqa: E402
                           yuv_ac, yuv_video_yaz)

# referansin donusumu: ORB+RANSAC (kare 60) + Y-duzleminde ince ayar
# (kodlanmis Y ile olculdu: 2.93 -> 2.28)
OLCEK, TX, TY = 1.1607, -106.1, -4.4
M = np.array([[OLCEK, 0.0, TX], [0.0, OLCEK, TY]], dtype=np.float32)
# canli referansta cerceve ic kenari (1024x1280 uzayi)
PANEL = {"ust": 176, "sol": 158, "alt": 1123, "sag": 887}
RAMPA = 2.0
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:6.1f}s] {m}")


def gecis_alfa(ph, pw, rampa=RAMPA):
    """Panel ici 1.0, ic kenarda `rampa` px dogrusal gecis."""
    yy = np.minimum(np.arange(ph), np.arange(ph)[::-1])[:, None]
    xx = np.minimum(np.arange(pw), np.arange(pw)[::-1])[None, :]
    d = np.minimum(yy, xx).astype(np.float32)
    return np.clip((d + 0.5) / rampa, 0.0, 1.0)


def rgb_yuv_709(rgb):
    """RGB -> BT.709 sinirli aralik Y,U,V (U/V yari cozunurluk).

    Referans video BT.709 etiketli; BT.601 katsayilari ~1 birim sistematik Y
    hatasi veriyordu (olculdu: panel ici MAE 2.96 -> 709 ile asagida).
    """
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Y = np.clip(16.0 + 219.0 * y / 255.0, 16, 235)
    U = np.clip(128.0 + 224.0 * (b - y) / (1.8556 * 255.0), 16, 240)
    V = np.clip(128.0 + 224.0 * (r - y) / (1.5748 * 255.0), 16, 240)
    return (np.rint(Y).astype(np.uint8), np.rint(U[::2, ::2]).astype(np.uint8),
            np.rint(V[::2, ::2]).astype(np.uint8))


def kareler(yol):
    m = probe(yol)["streams"][0]
    w, h = int(m["width"]), int(m["height"])
    import subprocess
    ham = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(yol), "-f",
                          "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, np.uint8).reshape(-1, h, w, 3)


def y_duzlem(rgb):
    f = rgb.astype(np.float32)
    return 0.257 * f[..., 0] + 0.504 * f[..., 1] + 0.098 * f[..., 2] + 16


def panel_y(veri, kare_bayt, i, kutu, w, h):
    y = np.frombuffer(veri[i * kare_bayt:i * kare_bayt + w * h],
                      dtype=np.uint8).reshape(h, w)
    return y[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]


def uret(cift, v01_yol, ref_video, ref_kareler, ref_veri, kare_bayt, adet,
         vw, vh, fps, sure, out, luts, crf=12):
    """Bir cift icin kompozit video + kapak. Donus: kontrol sayilari."""
    src = kareler(v01_yol)
    n = min(adet, len(src), len(ref_kareler))
    u, a, s, g = PANEL["ust"], PANEL["alt"], PANEL["sol"], PANEL["sag"]
    ph, pw = a - u + 1, g - s + 1
    alfa = gecis_alfa(ph, pw)[..., None]
    ham = out / "_is" / f"{cift}.yuv"
    ham.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(ham, "wb") as fh:
        for i in range(n):
            warp = cv2.warpAffine(src[i], M, (vw, vh), flags=cv2.INTER_LANCZOS4)
            yeni = warp[u:a + 1, s:g + 1].astype(np.float32)
            eski = ref_kareler[i][u:a + 1, s:g + 1].astype(np.float32)
            kare = np.clip(eski * (1 - alfa) + yeni * alfa, 0, 255)
            Y, U, V = rgb_yuv_709(np.rint(kare).astype(np.uint8))
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            yy = blok[:vw * vh].reshape(vh, vw)
            uu = blok[vw * vh:vw * vh + vw * vh // 4].reshape(vh // 2, vw // 2)
            vv = blok[vw * vh + vw * vh // 4:].reshape(vh // 2, vw // 2)
            yy[u:u + ph, s:s + pw] = Y
            uu[u // 2:u // 2 + ph // 2, s // 2:s // 2 + pw // 2] = U
            vv[u // 2:u // 2 + ph // 2, s // 2:s // 2 + pw // 2] = V
            blok.tofile(fh)
            if i and i % 40 == 0:
                gec = time.time() - t0
                ilerle(f"{cift} kompozit {i}/{n} (%{100 * i / n:.0f}) gecen "
                       f"{gec:.0f}sn kalan ~{gec / i * (n - i):.0f}sn")
    video = out / f"{cift}_V11.mp4"
    yuv_video_yaz(ham, video, vw, vh, fps, n / fps, crf=crf)
    k0 = out / "_is" / f"{cift}_kare0.png"
    extract_frame(video, k0, 0)
    with Image.open(k0) as im:
        taban = np.asarray(im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS),
                           dtype=np.uint8)
    kapak, _ = build_candidate(taban, luts)
    kapak_yol = out / f"{cift}_kapak_V11.png"
    Image.fromarray(kapak).save(kapak_yol)

    yeni_veri, _, yeni_adet = yuv_ac(video, out / "_is" / f"{cift}_geri.yuv", vw, vh)
    ic, dis = [], []
    m = min(yeni_adet, adet)
    maske = np.zeros((vh, vw), bool)
    maske[u:a + 1, s:g + 1] = True
    for i in range(m):
        ry = np.frombuffer(ref_veri[i * kare_bayt:i * kare_bayt + vw * vh],
                           np.uint8).reshape(vh, vw).astype(np.float32)
        ny = np.frombuffer(yeni_veri[i * kare_bayt:i * kare_bayt + vw * vh],
                           np.uint8).reshape(vh, vw).astype(np.float32)
        d = np.abs(ry - ny)
        ic.append(float(d[maske].mean()))
        dis.append(float(d[~maske].mean()))
    ilerle(f"{cift}: panel ici MAE ort {np.mean(ic):.2f} | panel disi MAE ort "
           f"{np.mean(dis):.4f} en cok {np.max(dis):.4f}")
    return {"cift": cift, "kare": int(m), "video": video.name,
            "kapak": kapak_yol.name,
            "panel_ici_mae_ort": round(float(np.mean(ic)), 3),
            "panel_ici_mae_20plus": round(float(np.mean(ic[20:])), 3),
            "panel_ici_mae_en_kotu": round(float(np.max(ic)), 3),
            "panel_disi_mae_ort": round(float(np.mean(dis)), 4),
            "panel_disi_mae_en_kotu": round(float(np.max(dis)), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-video", default="_veri/v01/canli_AQUARIUS_GEMINI.mp4")
    ap.add_argument("--v01-dizin", default="_veri/v11")
    ap.add_argument("--ciftler", required=True, help="virgulle ayrilmis")
    ap.add_argument("--luts", default="config/pod_cover_gold_b_luts.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crf", type=int, default=12)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)
    ref_video = pathlib.Path(a.ref_video)
    meta = probe(ref_video)["streams"][0]
    vw, vh = int(meta["width"]), int(meta["height"])
    p, q = (meta.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = round(float(p) / float(q), 3)
    ref_veri, kare_bayt, adet = yuv_ac(ref_video, out / "_is" / "ref.yuv", vw, vh)
    ref_rgb = kareler(ref_video)
    luts = load_luts(pathlib.Path(a.luts))
    ilerle(f"referans {vw}x{vh} {adet} kare {fps} fps | donusum olcek {OLCEK} "
           f"tx {TX} ty {TY} | panel {PANEL}")
    sonuc = []
    ciftler = [c for c in a.ciftler.split(",") if c]
    for j, cift in enumerate(ciftler, start=1):
        v01 = pathlib.Path(a.v01_dizin) / f"v01_{cift}.mp4"
        if not v01.is_file():
            raise SystemExit(f"HATA: {v01} yok")
        ilerle(f"({j}/{len(ciftler)}) {cift} basliyor")
        sonuc.append(uret(cift, v01, ref_video, ref_rgb, ref_veri, kare_bayt,
                          adet, vw, vh, fps, adet / fps, out, luts, a.crf))
    (out / "KONTROL.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    ilerle("bitti")
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
