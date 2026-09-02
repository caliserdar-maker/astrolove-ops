#!/usr/bin/env python3
"""
PIN_MEDIA klasor agacinda "anyone" (linki olan herkes) iznini READER'a ceker.

Neden: B88 kosusu klasoru "herkese acik" yaparken rol writer kalmis; linki
olan herkes pin gorsellerini degistirebilir veya silebilir (2 Eyl 2026
tespiti). Pinterest'in gorseli cekmesi icin reader yeterlidir.

Erisim: rclone.conf'taki OAuth token ile Drive REST API (rclone'un kendisi
izin yonetemez). Once herhangi bir rclone komutu kosulur ki token tazelensin,
sonra `rclone config dump` ile access token okunur. Token loga yazilmaz.

  --dry-run  : yalniz sayim/rapor (varsayilan)
  --apply    : degistir; sonra 3 rastgele dosyanin iznini yeniden okuyup dogrula
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time

import requests

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
# WALL_ART/LISTING_MEDIA/PIN_MEDIA (B88, 29 Agu 2026)
DEFAULT_FOLDER_ID = "1vFPNTyyLWqnkn0tfGP3hvNh0nlTLBNPs"
API = "https://www.googleapis.com/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"
TARGET_ROLE = "reader"


def log(msg):
    print(msg, flush=True)


def access_token():
    # Token'i tazele (rclone gerekirse yeniler ve conf'a geri yazar).
    r = subprocess.run(["rclone", "lsd", f"{REMOTE}:", "--max-depth", "1"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone lsd hata: {r.stderr.strip()}")
    r = subprocess.run(["rclone", "config", "dump"], capture_output=True, text=True, check=True)
    conf = json.loads(r.stdout)
    tok = json.loads(conf[REMOTE]["token"])["access_token"]
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::add-mask::{tok}", flush=True)
    return tok


class Drive:
    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def _call(self, method, path, **kw):
        for attempt in range(5):
            r = self.s.request(method, f"{API}{path}", timeout=60, **kw)
            if r.status_code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Drive {method} {path} -> {r.status_code}: {r.text[:300]}")
            return r.json() if r.text else {}
        raise RuntimeError("Drive: tekrar siniri")

    def get(self, file_id):
        return self._call("GET", f"/files/{file_id}",
                          params={"fields": "id,name,mimeType,permissions(id,type,role,view)"})

    def children(self, folder_id):
        items, token = [], None
        while True:
            params = {"q": f"'{folder_id}' in parents and trashed = false", "pageSize": 1000,
                      "fields": "nextPageToken,files(id,name,mimeType,permissions(id,type,role,view))"}
            if token:
                params["pageToken"] = token
            data = self._call("GET", "/files", params=params)
            items += data.get("files", [])
            token = data.get("nextPageToken")
            if not token:
                return items

    def set_role(self, file_id, perm_id, role):
        """Rolu dusur. Izin ust klasorden miras ise Drive PATCH'i 403 ile
        reddeder ("less than the inherited access"); o durumda miras izni
        silinip oge "sinirli erisim"e cekilir ve ayni tipte yeni izin
        istenen rolle olusturulur (limited access)."""
        try:
            return self._call("PATCH", f"/files/{file_id}/permissions/{perm_id}",
                              params={"fields": "id,type,role"}, json={"role": role})
        except RuntimeError as e:
            if "403" not in str(e) or "inherited" not in str(e):
                raise
        # Sinirli erisim: ust klasorden miras kapatilir, oge yalniz kendi
        # izinleriyle kalir; sonra "anyone" dogrudan istenen rolle verilir.
        self._call("PATCH", f"/files/{file_id}", params={"fields": "id,inheritedPermissionsDisabled"},
                   json={"inheritedPermissionsDisabled": True})
        log(f"miras kapatildi: {file_id}")
        direct = anyone_perms(self.get(file_id))
        if direct:
            return self._call("PATCH", f"/files/{file_id}/permissions/{direct[0]['id']}",
                              params={"fields": "id,type,role"}, json={"role": role})
        return self._call("POST", f"/files/{file_id}/permissions",
                          params={"fields": "id,type,role"},
                          json={"type": "anyone", "role": role})


def walk(drive, folder_id):
    root = drive.get(folder_id)
    out = [root]
    stack = [folder_id]
    while stack:
        fid = stack.pop()
        for it in drive.children(fid):
            out.append(it)
            if it["mimeType"] == FOLDER_MIME:
                stack.append(it["id"])
    return out


def anyone_perms(item):
    # "view" alanli kayitlar (metadata/published gorunumu) gercek erisim izni
    # degildir; sayilmaz ve dokunulmaz.
    return [p for p in item.get("permissions", []) if p.get("type") == "anyone" and not p.get("view")]


def tally(items):
    counts = {}
    for it in items:
        for p in anyone_perms(it):
            counts[p["role"]] = counts.get(p["role"], 0) + 1
        if not anyone_perms(it):
            counts["(yok)"] = counts.get("(yok)", 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder-id", default=DEFAULT_FOLDER_ID, help="PIN_MEDIA klasor ID")
    ap.add_argument("--apply", action="store_true", help="degisiklikleri uygula (yoksa dry-run)")
    ap.add_argument("--sample", type=int, default=3, help="dogrulama icin rastgele dosya sayisi")
    a = ap.parse_args()

    drive = Drive(access_token())
    items = walk(drive, a.folder_id)
    folders = [i for i in items if i["mimeType"] == FOLDER_MIME]
    files = [i for i in items if i["mimeType"] != FOLDER_MIME]
    log(f"agac: {len(folders)} klasor, {len(files)} dosya (kok: {items[0]['name']})")
    before = tally(items)
    log(f"ONCE anyone rolleri: {before}")

    todo = [(it, p) for it in items for p in anyone_perms(it) if p["role"] != TARGET_ROLE]
    log(f"degistirilecek izin: {len(todo)}")
    if not a.apply:
        log("dry-run: degisiklik yapilmadi (--apply ile uygula)")
        write_summary(items[0]["name"], before, None, [], a.apply)
        return

    changed = 0
    # Once kok klasor (Drive rolu altina yayar), sonra yeniden tarayip kalanlar.
    for p in anyone_perms(items[0]):
        if p["role"] != TARGET_ROLE:
            drive.set_role(items[0]["id"], p["id"], TARGET_ROLE)
            changed += 1
    if not anyone_perms(drive.get(items[0]["id"])):
        # Kokte hic "anyone" izni yok (or. miras kapatilmis): dogrudan reader ver.
        drive._call("POST", f"/files/{items[0]['id']}/permissions", params={"fields": "id,type,role"},
                    json={"type": "anyone", "role": TARGET_ROLE})
        log("kok: anyone:reader eklendi")
        changed += 1
    rest = [(it, p) for it in walk(drive, a.folder_id)[1:] for p in anyone_perms(it) if p["role"] != TARGET_ROLE]
    log(f"kok sonrasi kalan: {len(rest)}")
    rest.sort(key=lambda t: 0 if t[0]["mimeType"] == FOLDER_MIME else 1)
    for it, p in rest:
        drive.set_role(it["id"], p["id"], TARGET_ROLE)
        changed += 1
    log(f"guncellenen izin: {changed}")

    # Yeniden tara ve dogrula (Drive kok iznini alta birkac saniyede yayar).
    time.sleep(20)
    items2 = walk(drive, a.folder_id)
    after = tally(items2)
    log(f"SONRA anyone rolleri: {after}")
    leftover = [it["name"] for it in items2 for p in anyone_perms(it) if p["role"] != TARGET_ROLE]
    if leftover:
        log(f"HATA: hala {TARGET_ROLE} olmayan {len(leftover)} oge: {leftover[:5]}")

    files2 = [i for i in items2 if i["mimeType"] != FOLDER_MIME]
    sample = random.sample(files2, min(a.sample, len(files2)))
    checks = []
    for f in sample:
        fresh = drive.get(f["id"])
        roles = sorted({p["role"] for p in anyone_perms(fresh)}) or ["(yok)"]
        checks.append((fresh["name"], fresh["id"], ",".join(roles)))
        log(f"dogrulama: {fresh['name']} -> anyone:{','.join(roles)}")
    write_summary(items[0]["name"], before, after, checks, a.apply)
    bad = [c for c in checks if c[2] != TARGET_ROLE]
    sys.exit(1 if (leftover or bad) else 0)


def write_summary(root, before, after, checks, applied):
    lines = [f"## PIN_MEDIA izin ({'UYGULANDI' if applied else 'dry-run'}) - {root}", "",
             f"- Once: `{before}`"]
    if after is not None:
        lines.append(f"- Sonra: `{after}`")
    if checks:
        lines += ["", "| Rastgele dosya | anyone rolu |", "| --- | --- |"]
        lines += [f"| {n} | {r} |" for n, _, r in checks]
    text = "\n".join(lines)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
