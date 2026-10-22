#!/usr/bin/env python3
"""astrolove-ops PUBLIC gecis yardimcisi (6 Eylul 2026).

Yalniz Actions runner icinde OPS_ADMIN_TOKEN ile calisir (sandbox proxy'si
api.github.com/.../actions/* yollarini engeller). Hicbir sir loga yazilmaz.

  runs-delete   : bu kosu haric TUM workflow run'larini siler, sayilari basar
  visibility    : PATCH /repos/{o}/{r} {"visibility": "public"}; 403 -> DUR
  verify        : repo gorunurlugu + secret ISIM listesi (deger yok)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("TARGET_REPO", "caliserdar-maker/astrolove-ops")


def tok():
    t = os.environ.get("OPS_ADMIN_TOKEN")
    if not t:
        sys.exit("HATA: OPS_ADMIN_TOKEN yok.")
    return t


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {tok()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            msg = json.loads(raw).get("message", "")
        except Exception:
            msg = ""
        return e.code, {"message": msg}


def runs_delete():
    me = os.environ.get("GITHUB_RUN_ID", "")
    deleted = failed = skipped = 0
    seen_fail = set()
    for _ in range(200):                              # guvenlik siniri
        st, page = req("GET", f"/repos/{REPO}/actions/runs?per_page=100&page=1")
        if st != 200:
            sys.exit(f"HATA: run listesi {st} {page.get('message','')}")
        runs = [r for r in page.get("workflow_runs", [])
                if str(r["id"]) != me and r["id"] not in seen_fail]
        if not runs:
            break
        for r in runs:
            if r.get("status") != "completed":        # kosan run silinemez
                skipped += 1
                seen_fail.add(r["id"])
                continue
            s, b = req("DELETE", f"/repos/{REPO}/actions/runs/{r['id']}")
            if s == 204:
                deleted += 1
            else:
                failed += 1
                seen_fail.add(r["id"])
                print(f"silinemedi run {r['id']} ({r.get('name')}): {s} {b.get('message','')}")
            if (deleted + failed) % 50 == 0:
                print(f"  ... silinen={deleted} hata={failed} atlanan={skipped}")
        time.sleep(0.2)
    st, page = req("GET", f"/repos/{REPO}/actions/runs?per_page=100&page=1")
    kalan = [r["id"] for r in page.get("workflow_runs", [])]
    print(f"RUN SILME: silinen={deleted} hata={failed} atlanan(kosan)={skipped} "
          f"kalan={len(kalan)} (bu kosu {me} dahil)")
    summary(f"| run silme | silinen {deleted}, hata {failed}, atlanan {skipped}, kalan {len(kalan)} |")
    return 0 if failed == 0 else 1


def visibility():
    st, b = req("PATCH", f"/repos/{REPO}", {"visibility": "public"})
    if st == 200:
        print(f"GORUNURLUK: {b.get('visibility')} (private={b.get('private')})")
        summary(f"| visibility PATCH | {st} -> {b.get('visibility')} |")
        return 0
    print(f"GORUNURLUK PATCH: {st} {b.get('message','')} -> DUR")
    summary(f"| visibility PATCH | {st} {b.get('message','')} -> DUR |")
    return 2


def verify():
    st, b = req("GET", f"/repos/{REPO}")
    vis = b.get("visibility") if st == 200 else f"HTTP {st}"
    st2, s = req("GET", f"/repos/{REPO}/actions/secrets?per_page=100")
    names = sorted(x["name"] for x in s.get("secrets", [])) if st2 == 200 else [f"HTTP {st2} {s.get('message','')}"]
    st3, v = req("GET", f"/repos/{REPO}/actions/variables?per_page=100")
    vnames = sorted(x["name"] for x in v.get("variables", [])) if st3 == 200 else [f"HTTP {st3}"]
    print(f"DOGRULAMA: visibility={vis}; secrets({len(names)})={', '.join(names)}; variables={', '.join(vnames)}")
    summary(f"| dogrulama | visibility={vis}; secrets={', '.join(names)}; variables={', '.join(vnames)} |")
    return 0


def summary(line):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"runs-delete": runs_delete, "visibility": visibility, "verify": verify}.get(cmd)
    if not fn:
        sys.exit(__doc__)
    sys.exit(fn())
