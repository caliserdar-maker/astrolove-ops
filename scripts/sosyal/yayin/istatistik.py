#!/usr/bin/env python3
"""Gunluk istatistik geri okuma (plan 4.8): takvimdeki TAMAM satirlarinin gonderi sayilari platform API'lerinden,
Drive <SOSYAL_OLCUM_KLASOR>/SOSYAL_OLCUM_<YYYYMMDD>.csv. Salt okuma (platforma yazim yok).
Metrik adlari resmi belgelerden kuru kosuda dogrulanir (plan 4.8 notu); okunamayan metrik HATA hucresi olur, kosu surer."""
import csv
import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import Hata, Http, drive_yaz, log  # noqa: E402
import kimlik  # noqa: E402
import secim  # noqa: E402
import takvim as T  # noqa: E402
from kanal import facebook, instagram, threads, youtube  # noqa: E402

KLASOR = os.environ.get("SOSYAL_OLCUM_KLASOR", "ASTROLOVE/SOSYAL/OLCUM")
METRIK = {
    "instagram": os.environ.get("IG_METRIK", "views,reach,likes,comments,saved,shares"),
    "threads": os.environ.get("TH_METRIK", "views,likes,replies,reposts,quotes"),
    "facebook": os.environ.get("FB_METRIK", "blue_reels_play_count,post_impressions_unique"),
}


def _insights(http, url, token, metrik):
    j, _ = http.iste("GET", url, token=token, params={"metric": metrik})
    out = {}
    for d in j.get("data", []):
        v = d.get("values", [{}])
        out[d.get("name")] = d.get("total_value", {}).get("value", v[0].get("value") if v else "")
    return out


def oku(http, s, k):
    p, no = s["platform"], s["sonuc_no"].strip()
    if p == "instagram":
        return _insights(http, f"{instagram.BASE}/{no}/insights", k["token"], METRIK[p])
    if p == "threads":
        return _insights(http, f"{threads.BASE}/{no}/insights", k["token"], METRIK[p])
    if p == "facebook":
        return _insights(http, f"{facebook.BASE}/{no}/video_insights", k["token"], METRIK[p])
    t = youtube.erisim(http, k)
    j, _ = http.iste("GET", f"{youtube.API}/youtube/v3/videos", token=t, params={"part": "statistics", "id": no})
    it = j.get("items", [])
    return it[0].get("statistics", {}) if it else {}


def main(argv=None, http=None, simdi=None):
    http = http or Http()
    simdi = simdi or datetime.now(secim.TZ)
    try:
        tk = T.Takvim(http, T.google_token(http))
        satirlar = [s for s in tk.oku() if (s.get("DURUM") or "").startswith("TAMAM") and (s.get("sonuc_no") or "").strip()]
    except Hata as e:
        log(f"DUR: {e}")
        return 2
    kim, kayit, hata = {}, [], 0
    for s in satirlar:
        p = s["platform"]
        try:
            if p not in kim:
                kim[p] = kimlik.oku(p)
            m = oku(http, s, kim[p])
            for ad, v in m.items():
                kayit.append([simdi.strftime("%Y-%m-%d"), s["satir_no"], p, s["tur"], s["sonuc_no"], ad, v])
        except Hata as e:
            kayit.append([simdi.strftime("%Y-%m-%d"), s["satir_no"], p, s["tur"], s["sonuc_no"], "HATA", str(e)[:120]])
            hata = 1
    b = io.StringIO()
    w = csv.writer(b)
    w.writerow(["tarih", "satir_no", "platform", "tur", "sonuc_no", "metrik", "deger"])
    w.writerows(kayit)
    drive_yaz(f"{KLASOR}/SOSYAL_OLCUM_{simdi.strftime('%Y%m%d')}.csv", b.getvalue())
    log(f"olcum: {len(satirlar)} gonderi, {len(kayit)} satir, hata={hata}")
    return hata


if __name__ == "__main__":
    sys.exit(main())
