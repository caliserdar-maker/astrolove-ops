#!/usr/bin/env python3
"""V01 hattini yerelde yeniden uretir (WA_VIDEO_V01_BATCH_V5.py ile).

Orijinal betigin YALNIZ iki sabiti degisir: DRIVE_ROOT (yerel agac) ve
EDITION (MIDNIGHT_BLUE). Uretim fonksiyonu `uret` oldugu gibi calistirilir
(seed 20260816, 88000 parcacik, KESIM 15-152, CRF 12 preset slow).

Alt komutlar:
  kesif    : mockup poster kutulari + canli video vs V01 ciktisi kiyasi
  uret     : bir cift icin V01 videosu uret (yerel agac)
  kiyas    : uretilen video vs orijinal V01 ciktisi, kare basina Y MAE
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

ED = "MIDNIGHT_BLUE"
VERI = pathlib.Path("_veri/v01")
AGAC = pathlib.Path("_veri/v01_agac")
BETIK = VERI / "WA_VIDEO_V01_BATCH_V5.py"
KESME = "# ================== ADIM 1: KALITE KAPISI"


def agac_kur(ciftler):
    """Colab Drive duzenini yerelde kurar (sembolik bag)."""
    src = AGAC / "TEMP" / "WA_HERO_ZOOM_V4" / ED
    pos = AGAC / "WALL_ART" / "POSTERS" / "OPTIMIZED_FOR_PRODUCTION" / ED / "3X4"
    exp = AGAC / "WALL_ART" / "LISTING_MEDIA" / "VIDEOS" / "V01_FIREFLY_STORY" / "01_EXPORTS"
    for d in (src, pos, exp, AGAC / "TEMP"):
        d.mkdir(parents=True, exist_ok=True)
    for c in ciftler:
        for kaynak, hedef in (
                (VERI / f"mockup_{c}.png", src / f"WA_06_MOCKUP_{c}_{ED}_ZOOM60.png"),
                (VERI / f"poster_{c}.jpg", pos / f"WA_POSTER_{c}_{ED}_3X4.jpg")):
            if not kaynak.is_file():
                raise SystemExit(f"HATA: kaynak yok {kaynak}")
            if hedef.is_symlink() or hedef.exists():
                hedef.unlink()
            hedef.symlink_to(kaynak.resolve())
    return AGAC


def betik_yukle(ciftler):
    """Betigin AYAR+ARACLAR+URETIM bolumunu (KOSU'dan onceki kismi) yukler."""
    agac_kur(ciftler)
    kaynak = BETIK.read_text(encoding="utf-8")
    bas = kaynak[:kaynak.index(KESME)]
    bas = bas.replace("DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'",
                      f"DRIVE_ROOT = {str(AGAC.resolve())!r}")
    bas = bas.replace("EDITION    = 'PURE_WHITE'", f"EDITION    = {ED!r}")
    ns = {"__name__": "wa_v01_batch"}
    exec(compile(bas, str(BETIK), "exec"), ns)
    return ns


def kareler(yol, n=None):
    """Videonun RGB karelerini (liste) dondurur."""
    import json as _j
    m = _j.loads(subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(yol)],
        capture_output=True, text=True, check=True).stdout)["streams"][0]
    w, h = int(m["width"]), int(m["height"])
    ham = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(yol), "-f",
                          "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(ham, np.uint8).reshape(-1, h, w, 3)
    return a if n is None else a[:n]


def y_duzlem(rgb):
    f = rgb.astype(np.float32)
    return 0.257 * f[..., 0] + 0.504 * f[..., 1] + 0.098 * f[..., 2] + 16


def olcekle(kare, w, h):
    return np.asarray(Image.fromarray(kare).resize((w, h), Image.LANCZOS))


def kaydir_ara(ref_y, yeni_y, en_cok=140):
    """En iyi dikey kaydirmayi ve o kaydirmadaki MAE'yi bulur."""
    en = None
    for dy in range(0, en_cok + 1, 2):
        h = ref_y.shape[0] - dy
        d = float(np.abs(ref_y[dy:] - yeni_y[:h]).mean())
        if en is None or d < en[1]:
            en = (dy, d)
    return en


def kesif(a):
    ciftler = ["AQUARIUS_GEMINI", "AQUARIUS_ARIES", "SCORPIO_TAURUS"]
    ns = betik_yukle(ciftler)
    rapor = {"zoom60_envanter": (VERI / "zoom60_envanter.txt").read_text().splitlines()[0],
             "v01_export_adet": len((VERI / "v01_export_envanter.txt").read_text().split()),
             "mockup": {}, "canli_vs_v01": {}}
    for c in ciftler:
        hero = np.array(Image.open(VERI / f"mockup_{c}.png").convert("RGB"))
        pb, skor = ns["kutu_olc"](hero, str(VERI / f"poster_{c}.jpg"))
        KX = (hero.shape[1] - int(hero.shape[0] * 0.8)) // 2
        rapor["mockup"][c] = {"mockup_boyut": list(hero.shape[:2]),
                              "poster_kutusu_tam": list(map(int, pb)),
                              "kirpim_KX": int(KX),
                              "poster_kutusu_4x5": [int(pb[0] - KX), int(pb[1]),
                                                    int(pb[2] - KX), int(pb[3])],
                              "kutu_skor": round(float(skor), 4)}
        log(f"{c}: kutu {rapor['mockup'][c]['poster_kutusu_tam']} skor {skor:.4f}")
    for c in ciftler:
        canli = kareler(VERI / f"canli_{c}.mp4")
        v01 = kareler(VERI / f"v01_{c}.mp4")
        ch, cw = canli.shape[1:3]
        satir = {"canli": [int(canli.shape[0]), cw, ch],
                 "v01": [int(v01.shape[0]), int(v01.shape[3 - 2]), int(v01.shape[1])]}
        for ad, i in (("kare_0", 0), ("kare_60", 60), ("kare_120", 120)):
            ry = y_duzlem(canli[i])
            ny = y_duzlem(olcekle(v01[i], cw, ch))
            dy, d = kaydir_ara(ry, ny)
            satir[ad] = {"en_iyi_dy": dy, "mae": round(d, 3),
                         "mae_dy0": round(float(np.abs(ry - ny).mean()), 3)}
        rapor["canli_vs_v01"][c] = satir
        log(f"{c}: canli vs v01 {satir}")
    pathlib.Path(a.out).write_text(json.dumps(rapor, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    return 0


def uret(a):
    ns = betik_yukle([a.cift])
    r = ns["uret"](a.cift, ED)
    log(f"uretim sonucu: {r['sonuc']} | {r.get('fail_test', '')}")
    r.pop("testler", None)
    pathlib.Path(a.out).write_text(json.dumps(r, ensure_ascii=False, indent=1,
                                              default=str), encoding="utf-8")
    log(f"dosya: {r['yol']}")
    return 0


def kiyas(a):
    yeni = kareler(a.yeni)
    esk = kareler(a.orijinal)
    n = min(len(yeni), len(esk))
    mae = [float(np.abs(y_duzlem(yeni[i]) - y_duzlem(esk[i])).mean()) for i in range(n)]
    cikti = {"kare": n, "y_mae_ort": round(float(np.mean(mae)), 4),
             "y_mae_en_cok": round(float(np.max(mae)), 4),
             "y_mae_kare0": round(mae[0], 4),
             "en_kotu_kare": int(np.argmax(mae))}
    log(f"kiyas: {cikti}")
    pathlib.Path(a.out).write_text(json.dumps(cikti, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    return 0


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kesif"); k.add_argument("--out", required=True)
    u = alt.add_parser("uret"); u.add_argument("--cift", required=True)
    u.add_argument("--out", required=True)
    q = alt.add_parser("kiyas"); q.add_argument("--yeni", required=True)
    q.add_argument("--orijinal", required=True); q.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"kesif": kesif, "uret": uret, "kiyas": kiyas}[a.komut](a)


if __name__ == "__main__":
    sys.exit(main())
