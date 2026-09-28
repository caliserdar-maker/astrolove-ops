#!/usr/bin/env python3
"""78 POD ilanina v5 kapak videosu yukleme: KURU KOSU (Etsy'ye YAZMA YOK; uygulama Serdar acik onayiyla, ayri adim).
Video kaynagi TEK: Drive TEMP/POD_VIDEO_V2/<damga>/VIDEO_<CIFT>.mp4 + QC_<CIFT>.json (video_v2_toplu.py, v5 sablonu).

Ilan basina (yalniz GET):
  - state (active disi -> BLOK; updateListing taslagi yayina alir, video adimi updateListing CAGIRMAZ)
  - mevcut videolar (/listings/{id}/videos): Etsy ilan basina 1 video; varsa DEGISTIR (eski video indirilip
    --out/yedek/<listing_id>_<video_id>.mp4 olarak yedeklenir, apply'da once yeni yuklenir sonra eski silinir)
  - yerel video: QC_<CIFT>.json pass, mp4 acilir, 2880x2160, 5-15 sn (Etsy), < 100 MB, ses yok (QC'den)
Durum: YUKLE (videosu yok) | DEGISTIR (eski video var) | BLOK (neden yazilir).
Cikti: PLAN.json (sha256 kilitli) + PLAN.csv + report.md. ETA sayaci: islenen/toplam, gecen, kalan, yuzde.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kotasi: kuru kosu ilan basina 2 GET (listing + videos); rapor bas/son kota ve apply tahmini cagriyi yazar.
Kullanim: video_yukle_78.py --video-dir V --kaynak-bilgi K.json --out OUT [--haric CIFT,CIFT]
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_cover_from_video import video_url, videos  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[2]
BEKLENEN = 78
VIDEO_BOYUT = (2880, 2160)
SURE_MIN, SURE_MAX = 5.0, 15.0     # Etsy ilan videosu
MB_MAX = 100.0
CAGRI_ILAN = 6                      # apply tahmini: state + video oku, yukle, geri oku, (eski sil + geri oku)
KURU_CAGRI_ILAN = 2                 # kuru: listing + videos (GET)


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def video_bilgi(p):
    import cv2
    v = cv2.VideoCapture(str(p))
    w, h = int(v.get(cv2.CAP_PROP_FRAME_WIDTH)), int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n, fps = int(v.get(cv2.CAP_PROP_FRAME_COUNT)), v.get(cv2.CAP_PROP_FPS)
    v.release()
    return {"w": w, "h": h, "kare": n, "fps": round(fps, 2), "sure": round(n / fps, 2) if fps else 0.0}


def yerel_kontrol(vdir, c):
    """(bilgi, sorunlar) - yerel video + QC json."""
    p, q = vdir / f"VIDEO_{c}.mp4", vdir / f"QC_{c}.json"
    if not p.is_file():
        return {}, [f"video yok ({p.name})"]
    b = {"dosya": p.name, "bayt": p.stat().st_size, "mb": round(p.stat().st_size / 1e6, 2), "sha256": sha(p)}
    b.update(video_bilgi(p))
    sorun = []
    qc = json.loads(q.read_text()) if q.is_file() else {}
    if not qc.get("pass"):
        sorun.append(f"QC {'FAIL' if qc else 'yok'}: {str(qc.get('olcum', ''))[:120]}")
    if (b["w"], b["h"]) != VIDEO_BOYUT:
        sorun.append(f"cozunurluk {b['w']}x{b['h']}")
    if not SURE_MIN <= b["sure"] <= SURE_MAX:
        sorun.append(f"sure {b['sure']} sn (Etsy {SURE_MIN:g}-{SURE_MAX:g})")
    if b["mb"] >= MB_MAX:
        sorun.append(f"{b['mb']} MB >= {MB_MAX:g}")
    return b, sorun


def kuru(a, api, out, satirlar):
    vdir = pathlib.Path(a.video_dir)
    yedek = out / "yedek"
    yedek.mkdir(parents=True, exist_ok=True)
    plan, t0, kota_bas = [], time.time(), None
    for i, s in enumerate(satirlar, 1):
        lid, c = str(s["listing_id"]), s["cift"]
        b, neden = yerel_kontrol(vdir, c)
        st = (api.get(f"/listings/{lid}", ok404=True) or {}).get("state")
        if kota_bas is None and api.remaining is not None:
            kota_bas = int(api.remaining) + 1
        vid = videos(api, lid)
        row = {"listing_id": lid, "cift": c, "state": st, "video": b, "eski_video": [
            {"video_id": v.get("video_id"), "state": v.get("video_state"), "url": video_url(v)} for v in vid],
            "durum": "DEGISTIR" if vid else "YUKLE", "neden": ""}
        if st != "active":
            neden.append(f"state {st}")
        if len(vid) > 1:
            neden.append(f"{len(vid)} video (beklenen en fazla 1)")
        for v in row["eski_video"]:
            yol = yedek / f"{lid}_{v['video_id']}.mp4"
            try:
                r = requests.get(v["url"], timeout=120)
                r.raise_for_status()
                yol.write_bytes(r.content)
                if yol.stat().st_size < 10000:
                    raise ValueError(f"{yol.stat().st_size} bayt")
                v.update({"yedek": yol.name, "bayt": yol.stat().st_size, "sha256": sha(yol)})
            except Exception as e:  # noqa: BLE001
                neden.append(f"eski video yedeklenemedi ({v['video_id']}): {e}")
                yol.unlink(missing_ok=True)
        if neden:
            row["durum"], row["neden"] = "BLOK", "; ".join(neden)
        plan.append(row)
        gec = time.time() - t0
        log(f"[{i}/{len(satirlar)}] {lid} {c} {row['durum']} {row['neden']} | eski video {len(vid)} | "
            f"gecen {gec:.0f}s | kalan ~{gec / i * (len(satirlar) - i):.0f}s | %{i * 100 // len(satirlar)} | kota {api.remaining}")

    say = {d: sum(r["durum"] == d for r in plan) for d in ("YUKLE", "DEGISTIR", "BLOK")}
    ok = say["BLOK"] == 0 and len(plan) == BEKLENEN - len(a.haric)
    (out / "PLAN.json").write_text(json.dumps({"olusturma": simdi(), "kaynak": a.kaynak, "satirlar": plan},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["listing_id", "cift", "durum", "neden", "state", "eski_video_id", "video", "mb", "sure", "sha256"])
        for r in plan:
            v = r["video"]
            wr.writerow([r["listing_id"], r["cift"], r["durum"], r["neden"], r["state"],
                         " ".join(str(x["video_id"]) for x in r["eski_video"]), v.get("dosya"), v.get("mb"),
                         v.get("sure"), v.get("sha256")])
    kota = int(api.remaining) if api.remaining is not None else None
    gerek = (say["YUKLE"] + say["DEGISTIR"]) * CAGRI_ILAN
    mbs = [r["video"]["mb"] for r in plan if r["video"]]
    kb = a.kaynak or {}
    sat = [f"# VIDEO78 yukleme: KURU KOSU ({simdi()}) - Etsy'ye yazma YOK", "",
           f"- YUKLE {say['YUKLE']} | DEGISTIR {say['DEGISTIR']} | BLOK {say['BLOK']} | toplam {len(plan)} | "
           f"SONUC: {'PASS' if ok else 'FAIL'}",
           f"- Haric (Serdar): {', '.join(a.haric) or '-'} | Kaynak: {kb.get('klasor')} | {kb.get('ozet')} | video {len(mbs)} dosya, "
           f"{min(mbs, default=0)}-{max(mbs, default=0)} MB",
           f"- Etsy kota: kuru kosu basinda ~{kota_bas}, sonunda {kota} (kuru ~{KURU_CAGRI_ILAN * len(plan)} cagri, "
           f"{KURU_CAGRI_ILAN}/ilan) | apply tahmini ~{gerek} cagri ({CAGRI_ILAN}/ilan) | "
           f"{'yeterli' if kota is None or kota - gerek >= a.quota_min else 'YETERSIZ'}",
           f"- Eski video yedegi: {sum(1 for r in plan for v in r['eski_video'] if v.get('yedek'))} dosya (out/yedek)",
           "- Apply (ayri adim, Serdar onayi): uploadListingVideo (name=VIDEO_<CIFT>.mp4); DEGISTIR'de yeni yuklenip "
           "geri okunduktan sonra eski deleteListingVideo; updateListing CAGRILMAZ; musteriye bildirim yok.", ""]
    engel = [r for r in plan if r["durum"] == "BLOK"]
    if engel:
        sat += ["## BLOK", ""] + [f"- {r['listing_id']} {r['cift']}: {r['neden']}" for r in engel] + [""]
    sat += ["## Plan", "", "| # | listing_id | cift | durum | state | eski video | video | MB | sn |",
            "|---|---|---|---|---|---|---|---|---|"]
    sat += [f"| {j} | {r['listing_id']} | {r['cift']} | {r['durum']} | {r['state']} | "
            f"{' '.join(str(x['video_id']) for x in r['eski_video']) or '-'} | {r['video'].get('dosya', '-')} | "
            f"{r['video'].get('mb', '-')} | {r['video'].get('sure', '-')} |" for j, r in enumerate(plan, 1)]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat[2:7]:
        log(x)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--video-dir", required=True)
    ap.add_argument("--kaynak-bilgi", help="JSON: klasor, ozet")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=60)
    ap.add_argument("--haric", default="", help="virgullu cift listesi (plana alinmaz)")
    a = ap.parse_args()
    a.haric = sorted({x.strip() for x in a.haric.split(",") if x.strip()})
    a.kaynak = json.loads(pathlib.Path(a.kaynak_bilgi).read_text()) if a.kaynak_bilgi else {}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    satirlar = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    if len(satirlar) != BEKLENEN:
        raise SystemExit(f"HATA: ilan listesi {len(satirlar)} != {BEKLENEN}. DUR.")
    bilinmeyen = set(a.haric) - {s["cift"] for s in satirlar}
    if bilinmeyen:
        raise SystemExit(f"HATA: haric listesinde bilinmeyen cift: {sorted(bilinmeyen)}. DUR.")
    satirlar = [s for s in satirlar if s["cift"] not in a.haric]
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    sys.exit(0 if kuru(a, Etsy(store), out, satirlar) else 1)


if __name__ == "__main__":
    main()
