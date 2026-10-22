#!/usr/bin/env python3
"""GitHub Actions kullanim olcumu (SALT OKUMA, GOREV 0005): son N gunde bu reponun workflow kosulari.
Kaynak: GET /repos/{repo}/actions/runs?created=<gun> (gun gun; API filtreli sorguda 1000 sonuc siniri var).
Sure = GET /repos/{repo}/actions/runs/{id}/timing -> run_duration_ms (GitHub'in olctugu kosu suresi; updated_at
KULLANILMAZ: log silme vb. sonradan guncelliyor, iter 1'de sisirdi). Faturalanan dakika her JOB icin ayri yukari
yuvarlanir; kosu bazli yuvarlama ALT SINIRDIR. timing.billable (private repo icin dolu) de toplanir.
Cikti: yalniz sayilar (workflow adi, kosu sayisi, dakika)."""
import datetime as dt
import math
import os
import sys
import time
from collections import defaultdict

FATURA = defaultdict(float)                          # timing.billable: os -> dakika (public repoda bos/0)

import requests

API = "https://api.github.com"
REPO = os.environ["GITHUB_REPOSITORY"]
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                  "X-GitHub-Api-Version": "2022-11-28"})


def get(url, **kw):
    for i in range(6):
        r = S.get(API + url, timeout=60, **kw)
        if r.status_code in (403, 429) and r.headers.get("X-RateLimit-Remaining") == "0":
            time.sleep(max(5, int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - int(time.time()) + 5)); continue
        if r.status_code >= 500:
            time.sleep(2 ** i); continue
        return r
    return r


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main(gun=30):
    bugun = dt.datetime.now(dt.timezone.utc).date()
    wf = defaultdict(lambda: [0, 0.0, 0])            # ad -> [kosu, dakika_ham, dakika_kosu_yukari]
    toplam_kosu = 0
    for i in range(gun):
        d = (bugun - dt.timedelta(days=i)).isoformat()
        sayfa = 1
        while True:
            r = get(f"/repos/{REPO}/actions/runs", params={"created": d, "per_page": 100, "page": sayfa})
            runs = (r.json() or {}).get("workflow_runs") or []
            for k in runs:
                if k.get("status") != "completed" or not k.get("run_started_at"):
                    continue
                t = get(f"/repos/{REPO}/actions/runs/{k['id']}/timing")
                tj = t.json() if t.status_code == 200 else {}
                dk = (tj.get("run_duration_ms") or 0) / 60000
                for osad, b in (tj.get("billable") or {}).items():
                    FATURA[osad] += (b.get("total_ms") or 0) / 60000
                w = wf[k.get("name") or "?"]
                w[0] += 1; w[1] += dk; w[2] += max(1, math.ceil(dk))
                toplam_kosu += 1
            if len(runs) < 100:
                break
            sayfa += 1
    ham = sum(v[1] for v in wf.values()); yuk = sum(v[2] for v in wf.values())
    print(f"DONEM: son {gun} gun ({bugun - dt.timedelta(days=gun - 1)} .. {bugun}) | tamamlanan kosu {toplam_kosu}")
    print(f"TOPLAM dakika: ham {ham:.0f} | kosu basina yukari yuvarlanmis {yuk} (faturalama job bazli: bu ALT SINIR)")
    print(f"timing.billable (public repo icin beklenen 0): {dict((k, round(v)) for k, v in FATURA.items()) or 0}")
    for ad, (n, h, y) in sorted(wf.items(), key=lambda x: -x[1][2])[:15]:
        print(f"  {ad}: {n} kosu | ham {h:.0f} dk | yuvarlanmis {y} dk")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
