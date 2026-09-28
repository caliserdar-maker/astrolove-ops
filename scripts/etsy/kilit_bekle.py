#!/usr/bin/env python3
"""Etsy kilidi - gercek sira (Serdar onayi 28 Eyl 2026). GitHub 'concurrency: etsy-token' yerine.

Kilit kumesi: .github/workflows/*.yml icinde 'kilit_bekle.py' ya da eski 'group: etsy-token' gecen TUM
workflow'lar (depodan her kosuda yeniden cikarilir; eski concurrency'li suren kosular da kumede gorulur).
GitHub API (GET /repos/{repo}/actions/runs, tek cagri/tur) ile kumedeki AKTIF kosular okunur
(queued / in_progress / waiting / requested / pending). Bu kosudan ONCE olusturulmus aktif kosu varsa
20 sn arayla beklenir; log: sira, ondekiler, gecen sure. Zaman asimi 120 dk -> temiz FAIL (cikis 1).
Hicbir kosu iptal edilmez.
  --mod bekle (varsayilan): onde aktif kosu kalmayinca cikis 0.
  --mod atla (zamanlanmis router): kumede BASKA aktif kosu varsa beklemeden atla=true (cikis 0), yoksa atla=false.
Cikti: GITHUB_OUTPUT'a atla=true|false. Sir kullanmaz/basmaz (GH_TOKEN yalniz baslikta).
Ortam: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_RUN_ID, (GITHUB_API_URL).
"""
import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AKTIF = {"queued", "in_progress", "waiting", "requested", "pending"}
ARALIK = 20
ZAMAN_ASIMI_DK = 120
HATA_SINIRI = 6


def log(m):
    print(m, flush=True)


def kilit_kumesi(kok="."):
    kume = set()
    for f in glob.glob(os.path.join(kok, ".github/workflows/*.yml")) + glob.glob(os.path.join(kok, ".github/workflows/*.yaml")):
        t = Path(f).read_text(encoding="utf-8", errors="replace")
        if "kilit_bekle.py" in t or "group: etsy-token" in t:
            kume.add(".github/workflows/" + os.path.basename(f))
    return kume


def api_kosular():
    """Depodaki son 100 kosu (tek cagri). Aktif kosular her zaman en yenilerin icindedir."""
    repo = os.environ["GITHUB_REPOSITORY"]
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/repos/{repo}/actions/runs?per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                                               "Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("workflow_runs") or []


def ondekiler(kosular, kume, benim_id, benim_olusturma=None):
    """(benim kaydim, bu kosudan once olusturulmus aktif kume kosulari, tum diger aktif kume kosulari)."""
    ben = next((k for k in kosular if int(k.get("id")) == int(benim_id)), None)
    olus = benim_olusturma or (ben or {}).get("created_at") or "9999"
    aktif = [k for k in kosular if k.get("path") in kume and k.get("status") in AKTIF and int(k.get("id")) != int(benim_id)]
    anahtar = lambda k: (k.get("created_at") or "", int(k.get("id")))   # noqa: E731
    once = sorted([k for k in aktif if anahtar(k) < (olus, int(benim_id))], key=anahtar)
    return ben, once, sorted(aktif, key=anahtar)


def ozet(k):
    return f"{os.path.basename(k.get('path') or '?')}#{k.get('id')} {k.get('status')} {k.get('created_at')}"


def cikti(atla):
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(f"atla={'true' if atla else 'false'}\n")


def calis(mod="bekle", kok=".", getir=api_kosular, uyku=time.sleep, saat=time.monotonic,
          aralik=ARALIK, zaman_asimi_dk=ZAMAN_ASIMI_DK):
    kume = kilit_kumesi(kok)
    benim = os.environ["GITHUB_RUN_ID"]
    log(f"kilit kumesi: {len(kume)} workflow | bu kosu {os.environ.get('GITHUB_WORKFLOW', '?')}#{benim} | mod {mod}")
    t0, hata, benim_olus = saat(), 0, None
    while True:
        try:
            kosular = getir()
            hata = 0
        except (urllib.error.URLError, OSError, ValueError) as e:
            hata += 1
            log(f"GitHub API hatasi ({hata}/{HATA_SINIRI}): {str(e)[:120]}")
            if hata >= HATA_SINIRI:
                log("FAIL: kilit durumu okunamadi; kilitsiz devam EDILMEZ.")
                return 1
            uyku(aralik)
            continue
        ben, once, tum = ondekiler(kosular, kume, benim, benim_olus)
        if ben and not benim_olus:
            benim_olus = ben.get("created_at")
        gecen = saat() - t0
        if mod == "atla":
            if tum:
                log(f"ATLA: kilit kumesinde baska aktif kosu var ({len(tum)}): " + "; ".join(ozet(k) for k in tum[:5]))
                cikti(True)
            else:
                log("kilit bos: normal calisma")
                cikti(False)
            return 0
        if not once:
            log(f"KILIT ALINDI: onde aktif kosu yok | bekleme {gecen:.0f} sn")
            cikti(False)
            return 0
        log(f"BEKLIYOR: sira {len(once) + 1} | ondekiler: " + "; ".join(ozet(k) for k in once[:5])
            + f" | gecen {gecen / 60:.1f} dk")
        if gecen >= zaman_asimi_dk * 60:
            log(f"FAIL: {zaman_asimi_dk} dk zaman asimi; kilit alinamadi, is yapilmadi.")
            return 1
        uyku(aralik)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", choices=["bekle", "atla"], default="bekle")
    ap.add_argument("--zaman-asimi-dk", type=int, default=ZAMAN_ASIMI_DK)
    ap.add_argument("--kok", default=".", help="kilit kumesinin okunacagi depo koku (.github/workflows)")
    a = ap.parse_args()
    if not os.environ.get("GH_TOKEN"):
        log("FAIL: GH_TOKEN yok (workflow permissions: actions: read + env GH_TOKEN gerekli).")
        sys.exit(1)
    sys.exit(calis(a.mod, kok=a.kok, zaman_asimi_dk=a.zaman_asimi_dk))


if __name__ == "__main__":
    main()
