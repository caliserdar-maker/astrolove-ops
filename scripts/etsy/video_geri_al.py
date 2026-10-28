#!/usr/bin/env python3
"""Tek ilan video GERI ALMA (Merkez 28 Eki; Serdar onayi: yalniz 4570110121, v7 pilotu 40648877262 geri alinir). ETSY'YE YAZAR.
Sira (video_yukle_78 v7 yolu): on kosul (ilanda TAM OLARAK --sil-video var, state active) -> yedek mp4 TEK gonderim (yukle_tek,
tekrar yok) -> geri okuma: yeni video active + url -> --sil-video DELETE -> geri okuma: ilanda yalniz yeni video.
updateListing YOK, state degisikligi YOK. Kota tabani etsy_common.KOTA_SINIRI (10).
Dogrulama: ilandaki son video indirilir, yedekle kare sayisi / boyut / kare farki (0, orta, son kare; ortalama mutlak fark 0-255,
Etsy yeniden kodlayabilir) olculur; ayrica silinen pilot videoya (--pilot-mp4, BIRLESIK kaynagi) uzaklik: yedege daha yakin olmali.
Kullanim: video_geri_al.py --lid 4570110121 --yedek Y.mp4 --sil-video 850571467 --pilot-mp4 P.mp4 --confirm VIDEO_GERI_AL --out OUT"""
import argparse
import json
import os
import pathlib
import sys

import cv2
import numpy as np
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_cover_from_video import video_url, videos  # noqa: E402
import video_yukle_78 as V  # noqa: E402

ONAY = "VIDEO_GERI_AL"


def kareler(p):
    c = cv2.VideoCapture(str(p)); F = []
    while True:
        ok, f = c.read()
        if not ok:
            break
        F.append(f)
    fps = c.get(cv2.CAP_PROP_FPS); c.release()
    return F, fps


def fark(a, b):
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    return round(float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()), 3)


def karsilastir(ref, son, pilot=None):
    A, fa = kareler(ref); B, fb = kareler(son)
    R = dict(ref_kare=len(A), son_kare=len(B), ref_fps=round(fa, 3), son_fps=round(fb, 3),
             ref_boyut=list(A[0].shape[:2]) if A else None, son_boyut=list(B[0].shape[:2]) if B else None)
    if not A or not B:
        R["hata"] = "kare okunamadi"; return R
    idx = [0, len(A) // 2, len(A) - 1]
    R["kare_fark"] = [fark(A[i], B[min(i, len(B) - 1)]) for i in idx]
    if pilot:
        P, _ = kareler(pilot)
        if P:
            R["pilot_fark"] = [fark(P[min(i, len(P) - 1)], B[min(i, len(B) - 1)]) for i in idx]
    return R


def main():
    ap = argparse.ArgumentParser()
    for k in ("--lid", "--yedek", "--sil-video", "--confirm", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--pilot-mp4", default="")
    a = ap.parse_args()
    if a.confirm != ONAY:
        raise SystemExit(f"DUR: confirm {ONAY} olmali")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    y = pathlib.Path(a.yedek); b = y.read_bytes()
    if len(b) < 10000 or b[4:8] != b"ftyp":
        raise SystemExit(f"DUR: yedek mp4 degil ({len(b)} bayt)")
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k_); mask(s_)
    st = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]; lid = str(a.lid); sil = str(a.sil_video)
    R = dict(ilan=lid, yedek=y.name, yedek_bayt=len(b), sil_video=sil, adimlar=[])

    def kaydet(sonuc):
        R["sonuc"] = sonuc; R["kota"] = api.remaining; R["istek"] = api.calls
        (out / "GERI_AL.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
        log(f"SONUC {sonuc} | kota {api.remaining} | istek {api.calls}")

    api.kota_kapisi("geri alma")
    L = api.get(f"/listings/{lid}") or {}
    once = V._vid_idler(api, lid)
    R["once"] = dict(state=L.get("state"), videolar=once)
    log(f"once: state {L.get('state')} videolar {once}")
    if L.get("state") != "active" or once != [sil]:
        kaydet(f"DUR: on kosul tutmadi (state {L.get('state')}, videolar {once}, beklenen [{sil}]); yazma yok")
        return 1
    try:
        yeni = V.yukle_tek(api, shop, lid, y, [sil]); R["yeni_video"] = yeni; R["adimlar"].append(f"yuklendi {yeni}")
        ids, ok, vd = V._aktif(api, lid, yeni)
        R["adimlar"].append(f"geri okuma: {ids}, yeni video_state {vd}")
        if not ok:
            raise RuntimeError(f"yeni video {yeni} active olmadi ({vd}); pilot video SILINMEDI")
        api.delete(f"/shops/{shop}/listings/{lid}/videos/{sil}", ok404=True); R["adimlar"].append(f"silindi {sil}")
        ids, ok = V._bekle(api, lid, lambda x: x == [yeni], V.OKUMA_DENEME_V7, V.OKUMA_BEKLE_V7)
        R["adimlar"].append(f"son okuma: {ids}")
        if not ok:
            raise RuntimeError(f"son okuma: ilanda {ids}, beklenen yalniz [{yeni}]")
    except (Exception, SystemExit) as e:  # noqa: BLE001 post_file / delete SystemExit atar
        R["hata"] = str(e)[:300]
        kaydet("FAIL"); return 1
    vs = videos(api, lid); v = next((x for x in vs if str(x.get("video_id")) == yeni), {})
    R["son_video"] = {k: v.get(k) for k in ("video_id", "video_state", "height", "width", "thumbnail_url")}
    u = video_url(v)
    if u:
        try:
            g = requests.get(u, timeout=120); g.raise_for_status()
            (out / f"{lid}_{yeni}_canli.mp4").write_bytes(g.content)
            R["karsilastirma"] = karsilastir(y, out / f"{lid}_{yeni}_canli.mp4", a.pilot_mp4 or None)
        except Exception as e:  # noqa: BLE001 dogrulama indirmesi; yazim tamamlandi
            R["karsilastirma"] = dict(hata=str(e)[:200])
    kaydet("PASS")
    log(json.dumps(R.get("karsilastirma"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
