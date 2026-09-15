#!/usr/bin/env python3
"""77 POD listelemesi icin hero kirpma + video eslemesi + Etsy degisimi (Mo 14 Eyl 2026).

Onaylanan tek-ilan akisinin (Aquarius-Aquarius) aynisi, cift basina:
  uret : 5 hero -> hero_crop.py (iki gecis, 0.80+-0.02, kaciklik <=%0.5)
         video  -> video_match.py (o ciftin kendi hero_MB olcumunu tutturur, sapma <=%0.2)
         cikti Drive TEMP/POD_HERO_CROP/<PAIR>/, durum CSV'ye
  etsy : uretimi PASS olan ciftlerde yedek + 5 hero (kendi rank/varyasyon) + video
         (pod_hero_swap.py). PASS degilse ETSY'DE ATLANIR, kosu surer.

ETA sayaci her ciftte; kota tabani asilirsa etsy modunda DURULUR.
Kullanim:
  pod_crop_batch.py --mode uret|etsy --pod-state POD.csv --out OUT --state S.csv
      [--shard i --shards n] [--skip 4570110121] [--limit N] [--quota-min 400] [--force]
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "etsy"))
from etsy_common import mask  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parent
EDS = {"MB": "MIDNIGHT_BLUE", "DB": "DEEP_BLACK", "WP": "WARM_PARCHMENT",
       "CI": "CHAMPAGNE_IVORY", "PW": "PURE_WHITE"}
GDRIVE = "gdrive:ASTROLOVE"
HERO_DRV = GDRIVE + "/TEMP/POD_GALLERY/{pair}/{ed}/01.jpg"
HERO_ALT = GDRIVE + "/WALL_ART/LISTING_MEDIA/ETSY_UPLOAD_SETS/{ed}/{pair}"
POSTER_DRV = GDRIVE + "/WALL_ART/POSTERS/ORIGINAL_HIGH_RES/{ed}/{oran}/{pair}.jpg"
VIDEO_DRV = (GDRIVE + "/WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/01_EXPORTS/"
             "MIDNIGHT_BLUE/WA_VIDEO_V01_{pair}_MIDNIGHT_BLUE.mp4")
CIKTI_DRV = GDRIVE + "/TEMP/POD_HERO_CROP/{pair}"
SUTUN = ["pair", "listing_id", "edisyon", "sonuc", "oran", "kaciklik_x", "kaciklik_y",
         "gecis", "etsy_sonuc", "not", "ts_utc"]


def log(m):
    print(m, flush=True)


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rclone(*args, sessiz=True):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if r.returncode != 0 and not sessiz:
        raise RuntimeError(f"rclone {' '.join(args[:2])}: {r.stderr.strip()[-200:]}")
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def pod_state(path, skip, shard, shards, limit):
    ciftler = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                if r["listing_id"] in skip:
                    continue
                ciftler.append((r["pair"], r["listing_id"]))
    ciftler.sort()
    if shards > 1:
        ciftler = [c for i, c in enumerate(ciftler) if i % shards == shard]
    return ciftler[:limit] if limit else ciftler


def state_oku(path):
    if not pathlib.Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def state_yaz(path, satirlar):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN)
        w.writeheader()
        for s in satirlar:
            w.writerow({k: s.get(k, "") for k in SUTUN})


def eta(i, toplam, t0):
    gecen = time.time() - t0
    kalan = gecen / i * (toplam - i) if i else 0
    return (f"[{i}/{toplam} %{i/toplam*100:.0f}] gecen {gecen/60:.1f} dk, "
            f"kalan ~{kalan/60:.1f} dk")


# ------------------------------------------------------------------ URETIM
def kaynak_indir(pair, is_dir):
    """Hero'lar, 3X4 baskilar ve video. Donus: (heroes, posters, video) ya da None + sebep."""
    h, p = is_dir / "heroes", is_dir / "posters"
    h.mkdir(parents=True, exist_ok=True)
    p.mkdir(parents=True, exist_ok=True)
    heroes, posters = {}, {}
    for kisa, ed in EDS.items():
        hy = h / f"{ed}.jpg"
        ok, _ = rclone("copyto", HERO_DRV.format(pair=pair, ed=ed), str(hy))
        if not ok:
            ok2, ls = rclone("lsf", HERO_ALT.format(pair=pair, ed=ed), "--include", "01_*")
            ad = (ls.splitlines() or [""])[0].strip() if ok2 else ""
            if not ad:
                return None, f"{ed}: hero yok"
            ok, _ = rclone("copyto", HERO_ALT.format(pair=pair, ed=ed) + "/" + ad, str(hy))
            if not ok:
                return None, f"{ed}: hero indirilemedi"
        heroes[kisa] = hy
        py = p / f"{ed}_3X4.jpg"
        ok, _ = rclone("copyto", POSTER_DRV.format(pair=pair, ed=ed, oran="3X4"), str(py))
        if not ok:
            py = p / f"{ed}_2X3.jpg"
            ok, _ = rclone("copyto", POSTER_DRV.format(pair=pair, ed=ed, oran="2X3"), str(py))
            if not ok:
                return None, f"{ed}: baski dosyasi yok"
        posters[kisa] = py
    vy = is_dir / "video.mp4"
    ok, _ = rclone("copyto", VIDEO_DRV.format(pair=pair), str(vy))
    return (heroes, posters, vy if ok else None), ""


def uret(pair, lid, is_dir, cikti):
    """Donus: (satirlar, pass_mi)."""
    kay, sebep = kaynak_indir(pair, is_dir)
    ts = simdi()
    if kay is None:
        return [{"pair": pair, "listing_id": lid, "edisyon": "-", "sonuc": "FAIL",
                 "not": f"kaynak: {sebep}", "ts_utc": ts}], False
    heroes, posters, video = kay
    cikti.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(KOK / "hero_crop.py"),
                        "--heroes", ",".join(f"{k}={v}" for k, v in heroes.items()),
                        "--posters", ",".join(f"{k}={v}" for k, v in posters.items()),
                        "--out", str(cikti), "--ratio", "0.80"], capture_output=True, text=True)
    log(r.stdout[-1500:] + r.stderr[-500:])
    satirlar, hepsi = [], True
    kutu = cikti / "crop_box.json"
    if not kutu.exists():
        return [{"pair": pair, "listing_id": lid, "edisyon": "-", "sonuc": "FAIL",
                 "not": "hero_crop cikti uretmedi", "ts_utc": ts}], False
    d = json.loads(kutu.read_text(encoding="utf-8"))
    for ed, v in d.get("edisyonlar", {}).items():
        dog = v.get("dogrulama") or {}
        kac = dog.get("merkez_kacikligi") or {}
        s = v.get("sonuc", "FAIL")
        hepsi = hepsi and s == "PASS"
        satirlar.append({"pair": pair, "listing_id": lid, "edisyon": ed, "sonuc": s,
                         "oran": dog.get("olculen_cerceve_orani"), "kaciklik_x": kac.get("x"),
                         "kaciklik_y": kac.get("y"), "gecis": len(v.get("gecisler") or []),
                         "not": "; ".join(x for x in (v.get("ocr_eksik") and
                                                      f"OCR eksik {v['ocr_eksik']}" or "",) if x),
                         "ts_utc": ts})
    # video
    vs = {"pair": pair, "listing_id": lid, "edisyon": "VIDEO", "ts_utc": ts}
    if not video or not video.exists():
        vs.update({"sonuc": "FAIL", "not": "video kaynagi yok"})
        hepsi = False
    elif not (cikti / "hero_MB.jpg").exists():
        vs.update({"sonuc": "FAIL", "not": "hero_MB uretilemedi"})
        hepsi = False
    else:
        rv = subprocess.run([sys.executable, str(KOK / "video_match.py"),
                             "--video", str(video), "--video-poster", str(posters["MB"]),
                             "--hero", str(cikti / "hero_MB.jpg"), "--hero-poster", str(posters["MB"]),
                             "--out", str(cikti), "--tol", "0.002"], capture_output=True, text=True)
        log(rv.stdout[-800:] + rv.stderr[-400:])
        vj = cikti / "video_match.json"
        if vj.exists():
            dv = json.loads(vj.read_text(encoding="utf-8"))
            o = dv.get("olcum") or {}
            vs.update({"sonuc": dv.get("sonuc", "FAIL"), "oran": o.get("oran"),
                       "kaciklik_x": o.get("dx"), "kaciklik_y": o.get("dy"),
                       "gecis": len(dv.get("gecisler") or []), "not": f"sapma {o.get('sapma')}"})
        else:
            vs.update({"sonuc": "FAIL", "not": "video_match cikti uretmedi"})
        hepsi = hepsi and vs["sonuc"] == "PASS"
    satirlar.append(vs)
    rclone("copy", str(cikti), CIKTI_DRV.format(pair=pair), "--exclude", "_*", "-q")
    return satirlar, hepsi


# ------------------------------------------------------------------ ETSY
def sirlari_maskele(token_file):
    """Alt surecin ciktisi kirpildigi icin maskeyi UST surecte kaydet."""
    for ad in ("ETSY_API_KEY", "ETSY_SHARED_SECRET"):
        mask(os.environ.get(ad))
    try:
        d = json.loads(pathlib.Path(token_file).read_text(encoding="utf-8"))
    except Exception:
        return
    for k in ("refresh_token", "access_token", "shared_secret", "keystring"):
        mask(d.get(k))


def etsy(pair, lid, is_dir, out_dir, qmin):
    """Donus: (durum, not, kalan_kota)."""
    d = is_dir / "medya"
    d.mkdir(parents=True, exist_ok=True)
    ok, _ = rclone("copy", CIKTI_DRV.format(pair=pair), str(d), "--include", "hero_*.jpg",
                   "--include", "video_MB_cropped.mp4", "-q")
    eksik = [f for f in ("hero_MB.jpg", "hero_DB.jpg", "hero_WP.jpg", "hero_CI.jpg",
                         "hero_PW.jpg", "video_MB_cropped.mp4") if not (d / f).exists()]
    if eksik:
        return "ATLANDI", f"medya eksik: {eksik}", None
    hedef = out_dir / pair
    r = subprocess.run([sys.executable, str(KOK.parent / "etsy" / "pod_hero_swap.py"),
                        "--listing-id", lid, "--out", str(hedef), "--apply", "--quota-min", str(qmin),
                        "--heroes", ",".join(f"{k}={d}/hero_{k}.jpg" for k in EDS),
                        "--video", str(d / "video_MB_cropped.mp4")], capture_output=True, text=True)
    log(r.stdout[-2500:] + r.stderr[-800:])
    rj = hedef / "swap_result.json"
    if not rj.exists():
        return "ATLANDI", "swap ciktisi yok", None
    dj = json.loads(rj.read_text(encoding="utf-8"))
    rclone("copy", str(hedef), CIKTI_DRV.format(pair=pair) + "/ETSY_SWAP", "-q")
    return dj.get("sonuc", "FAIL"), f"yedek {dj.get('yedek')}", dj.get("kota_sonra")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["uret", "etsy"])
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--skip", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pairs", default="", help="yalniz bu ciftler (virgullu)")
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "etsy":
        sirlari_maskele(os.environ.get("TOKEN_FILE", ""))
    skip = {x for x in a.skip.split(",") if x}
    ciftler = pod_state(a.pod_state, skip, a.shard, a.shards, a.limit)
    if a.pairs:
        sec = {x.strip() for x in a.pairs.split(",") if x.strip()}
        ciftler = [c for c in ciftler if c[0] in sec]
    satirlar = state_oku(a.state)
    log(f"MOD {a.mode}: {len(ciftler)} cift (shard {a.shard}/{a.shards}), "
        f"mevcut durum satiri {len(satirlar)}")
    t0 = time.time()
    bitti = {r["pair"] for r in satirlar if r.get("edisyon") == "VIDEO"} if a.mode == "uret" else \
            {r["pair"] for r in satirlar if r.get("etsy_sonuc")}

    for i, (pair, lid) in enumerate(ciftler, 1):
        if pair in bitti and not a.force:
            log(f"{eta(i, len(ciftler), t0)} {pair}: zaten islenmis, atlandi")
            continue
        is_dir = out / "_is" / pair
        is_dir.mkdir(parents=True, exist_ok=True)
        try:
            if a.mode == "uret":
                yeni, gecti = uret(pair, lid, is_dir, out / pair)
                satirlar = [r for r in satirlar if r["pair"] != pair] + yeni
                log(f"{eta(i, len(ciftler), t0)} {pair}: uretim {'PASS' if gecti else 'FAIL'}")
            else:
                pr = [r for r in satirlar if r["pair"] == pair]
                gecti = bool(pr) and all(r.get("sonuc") == "PASS" for r in pr)
                if not gecti:
                    durum, notu, kalan = "ATLANDI", "uretim PASS degil", None
                else:
                    durum, notu, kalan = etsy(pair, lid, is_dir, out / "_etsy", a.quota_min)
                for r in satirlar:
                    if r["pair"] == pair:
                        r["etsy_sonuc"], r["not"] = durum, (r.get("not") or "") or notu
                log(f"{eta(i, len(ciftler), t0)} {pair}: ETSY {durum} ({notu}) kota {kalan}")
                if kalan is not None and str(kalan).isdigit() and int(kalan) < a.quota_min:
                    log(f"DUR: kota {kalan} < {a.quota_min}. Kalan ciftler islenmedi.")
                    state_yaz(a.state, satirlar)
                    break
        except Exception as ex:                                  # bir cift kosuyu durdurmaz
            log(f"HATA {pair}: {type(ex).__name__}: {ex}")
            if a.mode == "uret":
                satirlar = [r for r in satirlar if r["pair"] != pair] + [
                    {"pair": pair, "listing_id": lid, "edisyon": "-", "sonuc": "FAIL",
                     "not": f"{type(ex).__name__}: {str(ex)[:120]}", "ts_utc": simdi()}]
            else:
                for r in satirlar:
                    if r["pair"] == pair:
                        r["etsy_sonuc"] = "ATLANDI"
        finally:
            subprocess.run(["rm", "-rf", str(is_dir)])
            state_yaz(a.state, satirlar)
            rclone("copyto", a.state, f"{GDRIVE}/TEMP/POD_HERO_CROP/_STATE/"
                   f"{pathlib.Path(a.state).name}", "-q")

    state_yaz(a.state, satirlar)
    ozet = {"mod": a.mode, "cift": len(ciftler),
            "uretim_pass": len({r["pair"] for r in satirlar
                                if r.get("edisyon") == "VIDEO" and r.get("sonuc") == "PASS"}),
            "etsy_pass": len({r["pair"] for r in satirlar if r.get("etsy_sonuc") == "PASS"}),
            "etsy_atlandi": sorted({r["pair"] for r in satirlar
                                    if r.get("etsy_sonuc") in ("ATLANDI", "FAIL")})}
    log("OZET: " + json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
