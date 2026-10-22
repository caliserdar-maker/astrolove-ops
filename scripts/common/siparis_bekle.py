#!/usr/bin/env python3
"""Adi 'siparis' ile baslayan is akislarindan aktif (queued / in_progress / waiting / pending) kosu varsa 30 sn arayla bekler
(RCLONE gecisi: Serdar 22 Eki "siparis-* in_progress yoksa"). Zaman asimi --dk -> FAIL (cikis 1). Hicbir kosu iptal edilmez.
Ortam: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_RUN_ID."""
import argparse
import json
import os
import sys
import time
import urllib.request

AKTIF = ("queued", "in_progress", "waiting", "pending", "requested")


def aktif_siparis():
    repo, kendi = os.environ["GITHUB_REPOSITORY"], os.environ.get("GITHUB_RUN_ID", "")
    out = []
    for st in AKTIF:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/runs?status={st}&per_page=100",
                                     headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                                              "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for k in json.load(r).get("workflow_runs") or []:
                if str(k.get("id")) != kendi and (k.get("name") or "").startswith("siparis"):
                    out.append(f"{k.get('name')}#{k.get('id')}({st})")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dk", type=int, default=60)
    a = ap.parse_args()
    t0 = time.time()
    while True:
        k = aktif_siparis()
        if not k:
            print(f"SIPARIS KILIDI: aktif siparis kosusu yok | bekleme {time.time() - t0:.0f} sn", flush=True)
            return
        if time.time() - t0 > a.dk * 60:
            print(f"FAIL: {a.dk} dk icinde siparis kosulari bitmedi: {k}", flush=True)
            sys.exit(1)
        print(f"[bekliyor] aktif siparis kosusu: {k} | gecen {(time.time() - t0) / 60:.1f} dk", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
