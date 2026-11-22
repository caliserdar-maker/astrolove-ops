#!/usr/bin/env python3
"""Haftalik token yenileme (plan 4.9). Instagram ig_refresh_token, Threads th_refresh_token (60 gun);
Facebook Sayfa token'i ve YouTube refresh token'i salt okuma ile dogrulanir. Yenilenen token Drive'a GERI yazilir.
Bitise 10 gunden az kaldiysa (yenileme sonrasi) ya da hata varsa Drive uyari dosyasi. Cikis 1 = uyari var."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import Hata, Http, gizle, log  # noqa: E402
import calis  # noqa: E402
import kimlik  # noqa: E402
from kanal import facebook, instagram, threads, youtube  # noqa: E402

IG_G = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/")
TH_G = os.environ.get("TH_GRAPH_BASE", "https://graph.threads.net").rstrip("/")
UYARI_GUN = 10
YENILE = {"instagram": (IG_G, "ig_refresh_token"), "threads": (TH_G, "th_refresh_token")}
DOGRULA = {"facebook": facebook, "youtube": youtube, "instagram": instagram, "threads": threads}


def yenile(http, platformlar, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    uyari = []
    for p in platformlar:
        try:
            k = kimlik.oku(p)
        except Hata as e:
            uyari.append(f"token {p}: {e}")
            log(f"{p}: FAIL {e}")
            continue
        try:
            if p in YENILE:
                base, grant = YENILE[p]
                j, _ = http.iste("GET", f"{base}/refresh_access_token", sorgu_sirri=True,
                                 params={"grant_type": grant, "access_token": k["token"]})
                yeni = j.get("access_token") or ""
                if not yeni:
                    raise Hata("yenileme token donmedi")
                gizle(yeni)
                k["token"] = yeni
                if j.get("expires_in"):
                    k["bitis"] = (simdi + timedelta(seconds=int(j["expires_in"]))).isoformat()
                k["yenileme"] = simdi.isoformat()
                kimlik.yaz(p, k)
            DOGRULA[p].kimlik_dogrula(http, k)
            b = k.get("bitis") or ""
            if b:
                kalan = datetime.fromisoformat(b) - simdi
                if kalan < timedelta(days=UYARI_GUN):
                    uyari.append(f"token {p}: bitise {kalan.days} gun")
            log(f"{p}: PASS (bitis {b or '-'})")
        except Hata as e:
            uyari.append(f"token {p}: {e}")
            log(f"{p}: FAIL {e}")
    if uyari:
        calis.uyari_yaz(uyari, simdi.astimezone(calis.secim.TZ))
    return 1 if uyari else 0


def main(argv=None, http=None):
    argv = sys.argv[1:] if argv is None else argv
    pl = [p for p in (argv or sorted(calis.acik_platformlar())) if p in DOGRULA]
    if not pl:
        log("acik platform yok; is yok")
        return 0
    return yenile(http or Http(), pl)


if __name__ == "__main__":
    sys.exit(main())
