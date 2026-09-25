#!/usr/bin/env python3
"""Musteri verisi sizintisi temizligi (ACIL, 25 Eyl 2026). Ciktida YALNIZ SAYILAR vardir: hicbir arama terimi,
artifact icerigi ya da log satiri yazdirilmaz.

Arama terimleri (Drive'dan; yalniz bellekte): POD_ORDERS_STATE.csv receipt'leri, TEMP/POD_ORDERS/*.json paketlerindeki
receipt / alici adi / adres satiri / e-posta, TEMP/SIPARIS_ISIM/<receipt>.md adlari + receipt bicimli sayi deseni.

tara: riskli artifact sayisi; riskli workflow kosularinin loglarinda terim VAR/YOK sayisi.
sil : riskli artifact'lar SILINIR (icerik acilmaz); terim bulunan kosularin loglari SILINIR.
"""
import argparse
import csv
import glob
import io
import json
import os
import re
import sys
import time
import zipfile

import requests

API = "https://api.github.com"
REPO = os.environ["GITHUB_REPOSITORY"]
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                  "X-GitHub-Api-Version": "2022-11-28"})
RISKLI_ARTIFACT = {"pod-order-router"}                 # _out/ (kart, adresli paket, rapor) + state.csv
RISKLI_WF = ["pod-order-router.yml", "pod-sablon-v4.yml", "kisisel-pilot.yml"]
RECEIPT_DESEN = re.compile(rb"(?<!\d)4[01]\d{8}(?!\d)")   # Etsy receipt bicimi (ilan id'leri 45..., gorsel 8...)


def c(method, url, **kw):
    for i in range(8):
        r = S.request(method, url if url.startswith("http") else API + url, timeout=120, **kw)
        if r.status_code in (403, 429) and r.headers.get("X-RateLimit-Remaining") == "0":
            bekle = max(5, int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - int(time.time()) + 5)
            print(f"  hiz siniri: {bekle} sn bekleniyor", flush=True)
            time.sleep(min(bekle, 1800))
            continue
        if r.status_code >= 500 and i < 7:
            time.sleep(2 ** i)
            continue
        return r
    return r


def terimler(kok):
    t = set()
    p = os.path.join(kok, "state.csv")
    if os.path.exists(p):
        for row in csv.DictReader(open(p, encoding="utf-8")):
            if (row.get("receipt_id") or "").isdigit():
                t.add(row["receipt_id"])
    for f in glob.glob(os.path.join(kok, "paket", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:                                  # noqa: BLE001
            continue
        o = d.get("order") or {}
        rc = o.get("recipient") or {}
        ad = rc.get("address") or {}
        for v in (str(d.get("receipt_id") or ""), d.get("recipient_name"), rc.get("name"), rc.get("email"), ad.get("line1")):
            if v and len(str(v).strip()) >= 5:
                t.add(str(v).strip())
    for f in glob.glob(os.path.join(kok, "kart", "*.md")):
        n = os.path.basename(f)[:-3]
        if n.isdigit():
            t.add(n)
    return [x.encode("utf-8") for x in t]


def artifactlar():
    out, sayfa = [], 1
    while True:
        r = c("GET", f"/repos/{REPO}/actions/artifacts", params={"per_page": 100, "page": sayfa})
        a = r.json().get("artifacts") or []
        out += a
        if len(a) < 100:
            return out
        sayfa += 1


def kosular(wf):
    out, sayfa = [], 1
    while True:
        r = c("GET", f"/repos/{REPO}/actions/workflows/{wf}/runs", params={"per_page": 100, "page": sayfa})
        if r.status_code == 404:
            return out
        k = r.json().get("workflow_runs") or []
        out += k
        if len(k) < 100:
            return out
        sayfa += 1


def log_var(run_id, T):
    r = c("GET", f"/repos/{REPO}/actions/runs/{run_id}/logs", allow_redirects=True)
    if r.status_code in (404, 410):
        return None                                        # log yok / silinmis
    if r.status_code != 200:
        return "hata"
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile:
        return "hata"
    for n in z.namelist():
        b = z.read(n)
        if RECEIPT_DESEN.search(b) or any(t in b for t in T):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["tara", "sil"])
    ap.add_argument("--terim-kok", default="_gizli")
    a = ap.parse_args()
    T = terimler(a.terim_kok)
    print(f"arama terimi: {len(T)} adet (+ receipt deseni)", flush=True)

    A = artifactlar()
    risk = [x for x in A if x.get("name") in RISKLI_ARTIFACT and not x.get("expired")]
    print(f"artifact: toplam {len(A)} | riskli (router _out/state) {len(risk)}", flush=True)
    silinen_a = 0
    if a.mod == "sil":
        for x in risk:
            r = c("DELETE", f"/repos/{REPO}/actions/artifacts/{x['id']}")
            silinen_a += r.status_code == 204
        print(f"artifact SILINDI: {silinen_a}/{len(risk)}", flush=True)

    ozet = {}
    for wf in RISKLI_WF:
        K = [k for k in kosular(wf) if k.get("status") == "completed"]
        var = yok = logsuz = hata = sil = 0
        t0 = time.time()
        for i, k in enumerate(K, 1):
            v = log_var(k["id"], T)
            if v is None:
                logsuz += 1
            elif v == "hata":
                hata += 1
            elif v:
                var += 1
                if a.mod == "sil":
                    r = c("DELETE", f"/repos/{REPO}/actions/runs/{k['id']}/logs")
                    sil += r.status_code == 204
            else:
                yok += 1
            if i % 50 == 0 or i == len(K):
                g = time.time() - t0
                print(f"  {wf}: {i}/{len(K)} %{i * 100 // len(K)} | gecen {g / 60:.1f} dk | kalan {g / i * (len(K) - i) / 60:.1f} dk", flush=True)
        ozet[wf] = {"kosu": len(K), "VAR": var, "YOK": yok, "log_yok": logsuz, "okunamadi": hata, "log_silindi": sil}
        print(f"{wf}: {ozet[wf]}", flush=True)
    rapor = {"mod": a.mod, "artifact_toplam": len(A), "artifact_riskli": len(risk), "artifact_silindi": silinen_a, "log": ozet}
    with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as fh:
        fh.write("```\n" + json.dumps(rapor, indent=1) + "\n```\n")
    print(json.dumps(rapor), flush=True)


if __name__ == "__main__":
    main()
