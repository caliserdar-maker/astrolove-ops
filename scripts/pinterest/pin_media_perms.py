#!/usr/bin/env python3
"""
Drive klasor agacinda "anyone" (linki olan herkes) iznini duzenler.

  --mode fix     (varsayilan) agactaki anyone iznini READER'a ceker.
                 Neden: B88 kosusu PIN_MEDIA'yi "herkese acik" yaparken rol
                 writer kalmisti (2 Eyl 2026 tespiti). Ust klasordan miras
                 alinan izin dusurulemez; o durumda ogede miras kapatilir
                 (inheritedPermissionsDisabled) ve anyone:reader dogrudan verilir.
  --mode remove  agactaki anyone iznini TAMAMEN kaldirir (klasor ozel olur).
                 --keep-id altindaki agaca dokunmaz; onun anyone:reader izninin
                 mirastan bagimsiz oldugunu (miras kapali) dogrular. KARAR
                 (Mo, 2 Eyl 2026): ASTROLOVE koku ozel, PIN_MEDIA reader kalir.

Erisim: rclone.conf'taki OAuth token ile Drive REST API (rclone'un kendisi
izin yonetemez). Once bir rclone komutu kosulur ki token tazelensin, sonra
`rclone config dump` ile access token okunur. Token loga yazilmaz.

  --apply olmadan yalniz sayim/rapor (dry-run).
  --apply ile degistirir; sonra 3 rastgele dosyanin iznini yeniden okuyup
  dogrular. remove modunda ayrica keep agacindan bir dosyanin webContentLink'i
  ANONIM HTTP ile cekilir (Pinterest'in gordugu erisim).
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
FIELDS = "id,name,mimeType,parents,inheritedPermissionsDisabled,webContentLink,permissions(id,type,role,view)"
# remove modunda ozellikle raporlanacak ust klasorler
REPORT_NAMES = ("WALL_ART", "LISTING_MEDIA", "TEMP", "SCRIPTS", "WALLPAPER")


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
        for attempt in range(6):
            time.sleep(0.25)  # dakikalik sorgu kotasini zorlamamak icin
            r = self.s.request(method, f"{API}{path}", timeout=60, **kw)
            quota = r.status_code == 403 and ("uota" in r.text or "rateLimit" in r.text)
            if (r.status_code in (429, 500, 502, 503) or quota) and attempt < 5:
                wait = 65 if quota else 2 ** attempt
                log(f"Drive {r.status_code}, {wait} sn bekleyip tekrar ({attempt + 1}/5)")
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Drive {method} {path} -> {r.status_code}: {r.text[:300]}")
            return r.json() if r.text else {}
        raise RuntimeError("Drive: tekrar siniri")

    def get(self, file_id):
        return self._call("GET", f"/files/{file_id}", params={"fields": FIELDS})

    def children(self, folder_id):
        items, token = [], None
        while True:
            params = {"q": f"'{folder_id}' in parents and trashed = false", "pageSize": 1000,
                      "fields": f"nextPageToken,files({FIELDS})"}
            if token:
                params["pageToken"] = token
            data = self._call("GET", "/files", params=params)
            items += data.get("files", [])
            token = data.get("nextPageToken")
            if not token:
                return items

    def public_items(self):
        """Drive'da 'linki olan herkes' / 'herkes bulabilir' gorunurlugundeki ogeler."""
        items, token = [], None
        while True:
            params = {"q": "(visibility = 'anyoneWithLink' or visibility = 'anyoneCanFind') and trashed = false",
                      "pageSize": 1000, "fields": f"nextPageToken,files({FIELDS})"}
            if token:
                params["pageToken"] = token
            data = self._call("GET", "/files", params=params)
            items += data.get("files", [])
            token = data.get("nextPageToken")
            if not token:
                return items

    def create_anyone(self, file_id, role):
        return self._call("POST", f"/files/{file_id}/permissions",
                          params={"fields": "id,type,role"}, json={"type": "anyone", "role": role})

    def delete_perm(self, file_id, perm_id):
        self._call("DELETE", f"/files/{file_id}/permissions/{perm_id}")

    def set_role(self, file_id, perm_id, role):
        """Rolu dusur. Izin ust klasorden miras ise Drive PATCH'i 403 ile
        reddeder; o durumda ogede miras kapatilir (sinirli erisim) ve
        "anyone" dogrudan istenen rolle verilir."""
        try:
            return self._call("PATCH", f"/files/{file_id}/permissions/{perm_id}",
                              params={"fields": "id,type,role"}, json={"role": role})
        except RuntimeError as e:
            if "403" not in str(e) or "inherited" not in str(e):
                raise
        self._call("PATCH", f"/files/{file_id}", params={"fields": "id,inheritedPermissionsDisabled"},
                   json={"inheritedPermissionsDisabled": True})
        log(f"miras kapatildi: {file_id}")
        direct = anyone_perms(self.get(file_id))
        if direct:
            return self._call("PATCH", f"/files/{file_id}/permissions/{direct[0]['id']}",
                              params={"fields": "id,type,role"}, json={"role": role})
        return self.create_anyone(file_id, role)


def walk(drive, folder_id, skip_id=None):
    """Kok dahil agac; ust ogeler alt ogelerden once gelir. skip_id agaci atlanir."""
    root = drive.get(folder_id)
    out = [root]
    stack = [folder_id]
    while stack:
        fid = stack.pop(0)
        for it in drive.children(fid):
            if it["id"] == skip_id:
                continue
            out.append(it)
            if it["mimeType"] == FOLDER_MIME:
                stack.append(it["id"])
    return out


def ancestry_filter(drive, root_id):
    """item -> kok klasorun altinda mi (parents zinciri, onbellekli)."""
    cache = {root_id: True}

    def under(item):
        seen = []
        cur = item
        while True:
            pid = (cur.get("parents") or [None])[0]
            if pid is None:
                result = False
                break
            if pid in cache:
                result = cache[pid]
                break
            seen.append(pid)
            cur = drive.get(pid)
        for i in seen:
            cache[i] = result
        return result

    return under


def anyone_perms(item):
    # "view" alanli kayitlar (metadata/published gorunumu) gercek erisim izni
    # degildir; sayilmaz ve dokunulmaz.
    return [p for p in item.get("permissions", []) if p.get("type") == "anyone" and not p.get("view")]


def roles(item):
    return ",".join(sorted({p["role"] for p in anyone_perms(item)})) or "(yok)"


def tally(items):
    counts = {}
    for it in items:
        for p in anyone_perms(it):
            counts[p["role"]] = counts.get(p["role"], 0) + 1
        if not anyone_perms(it):
            counts["(yok)"] = counts.get("(yok)", 0) + 1
    return counts


def summary_lines(title, before, after, checks):
    lines = [f"## {title}", "", f"- Once: `{before}`"]
    if after is not None:
        lines.append(f"- Sonra: `{after}`")
    if checks:
        lines += ["", "| Kontrol | Sonuc |", "| --- | --- |"]
        lines += [f"| {n} | {r} |" for n, r in checks]
    return lines


def write_summary(lines):
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")


# ------------------------------------------------------------------ fix
def mode_fix(drive, a):
    items = walk(drive, a.folder_id)
    folders = [i for i in items if i["mimeType"] == FOLDER_MIME]
    files = [i for i in items if i["mimeType"] != FOLDER_MIME]
    log(f"agac: {len(folders)} klasor, {len(files)} dosya (kok: {items[0]['name']})")
    before = tally(items)
    log(f"ONCE anyone rolleri: {before}")
    todo = [(it, p) for it in items for p in anyone_perms(it) if p["role"] != TARGET_ROLE]
    log(f"degistirilecek izin: {len(todo)}")
    title = f"izin fix ({'UYGULANDI' if a.apply else 'dry-run'}) - {items[0]['name']}"
    if not a.apply:
        log("dry-run: degisiklik yapilmadi (--apply ile uygula)")
        write_summary(summary_lines(title, before, None, []))
        return 0

    changed = 0
    # Once kok klasor (Drive rolu altina yayar), sonra yeniden tarayip kalanlar.
    for p in anyone_perms(items[0]):
        if p["role"] != TARGET_ROLE:
            drive.set_role(items[0]["id"], p["id"], TARGET_ROLE)
            changed += 1
    if not anyone_perms(drive.get(items[0]["id"])):
        drive.create_anyone(items[0]["id"], TARGET_ROLE)
        log("kok: anyone:reader eklendi")
        changed += 1
    rest = [(it, p) for it in walk(drive, a.folder_id)[1:] for p in anyone_perms(it) if p["role"] != TARGET_ROLE]
    log(f"kok sonrasi kalan: {len(rest)}")
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
    checks = sample_checks(drive, items2, a.sample)
    write_summary(summary_lines(title, before, after, checks))
    bad = [c for c in checks if c[1] != f"anyone:{TARGET_ROLE}"]
    return 1 if (leftover or bad) else 0


def sample_checks(drive, items, n):
    files = [i for i in items if i["mimeType"] != FOLDER_MIME]
    checks = []
    for f in random.sample(files, min(n, len(files))):
        fresh = drive.get(f["id"])
        checks.append((fresh["name"], f"anyone:{roles(fresh)}"))
        log(f"dogrulama: {fresh['name']} -> anyone:{roles(fresh)}")
    return checks


# ------------------------------------------------------------------ remove
def anon_fetch(url):
    """Kimliksiz HTTP GET; Pinterest'in gorecegi erisim. (durum, icerik tipi, bayt)."""
    try:
        r = requests.get(url, timeout=60, stream=True, allow_redirects=True)
        ctype = r.headers.get("content-type", "")
        size = 0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                break
        return r.status_code, ctype, size
    except requests.RequestException as e:
        return -1, str(e)[:80], 0


def mode_remove(drive, a):
    root = drive.get(a.folder_id)
    keep = drive.get(a.keep_id)
    log(f"kok: {root['name']} anyone:{roles(root)}; korunan: {keep['name']} anyone:{roles(keep)} "
        f"miras_kapali={keep.get('inheritedPermissionsDisabled')}")
    top = {c["name"]: c for c in drive.children(a.folder_id)}
    before_rows = [(f"{root['name']} (kok)", f"anyone:{roles(root)}")]
    before_rows += [(n, f"anyone:{roles(top[n])}") for n in REPORT_NAMES if n in top]
    before_rows.append((f"{keep['name']} (korunan)", f"anyone:{roles(keep)} miras_kapali={keep.get('inheritedPermissionsDisabled')}"))
    for n, r in before_rows:
        log(f"ONCE {n}: {r}")

    # Guvenlik kapisi: korunan agacin izni mirastan bagimsiz olmali.
    if not (keep.get("inheritedPermissionsDisabled") and roles(keep) == TARGET_ROLE):
        log(f"HATA: {keep['name']} anyone:{TARGET_ROLE} dogrudan + miras kapali degil; once 'fix' modu kosulmali")
        return 1
    title = f"izin remove ({'UYGULANDI' if a.apply else 'dry-run'}) - {root['name']}"
    if not a.apply:
        log("dry-run: degisiklik yapilmadi (--apply ile uygula)")
        write_summary(summary_lines(title, dict(before_rows), None, []))
        return 0

    removed = 0
    for p in anyone_perms(root):
        drive.delete_perm(root["id"], p["id"])
        removed += 1
        log(f"kok: anyone:{p['role']} izni SILINDI")
    time.sleep(20)

    # Drive'da "linki olan herkes" gorunurlugundeki tum ogeleri tek sorguyla bul;
    # korunan agac disinda kalanlarin anyone iznini sil (tum agaci gezmek kota asiyor).
    keep_ids = {i["id"] for i in walk(drive, a.keep_id)}
    under = ancestry_filter(drive, a.folder_id)
    pub = drive.public_items()
    items = [i for i in pub if i["id"] not in keep_ids and i["id"] != a.folder_id and under(i)]
    outside = [i["name"] for i in pub if i["id"] not in keep_ids and not under(i)]
    log(f"herkese acik oge: {len(pub)}; kok altinda ve korunan disinda: {len(items)}; kok DISINDA (dokunulmaz): {len(outside)} {outside[:5]}")
    skipped = 0
    for it in items:
        for p in anyone_perms(it):
            try:
                drive.delete_perm(it["id"], p["id"])
                removed += 1
                log(f"silindi: {it['name']} anyone:{p['role']}")
            except RuntimeError as e:
                if "403" in str(e) or "404" in str(e):
                    skipped += 1
                    continue
                raise
    log(f"silinen izin: {removed}, atlanan (miras/yok): {skipped}")
    if skipped:
        time.sleep(20)

    # Dogrulama.
    root2 = drive.get(a.folder_id)
    top2 = {c["name"]: c for c in drive.children(a.folder_id)}
    keep2 = drive.get(a.keep_id)
    left = [i["name"] for i in drive.public_items() if i["id"] not in keep_ids and under(i) and anyone_perms(i)]
    checks = [(f"{root2['name']} (kok) anyone", roles(root2))]
    checks += [(f"{n} anyone", roles(top2[n])) for n in REPORT_NAMES if n in top2]
    checks.append((f"Drive'da kalan herkese-acik oge (korunan haric)", f"{len(left)} {left[:5] if left else ''}"))
    checks.append((f"{keep2['name']} anyone", f"{roles(keep2)} miras_kapali={keep2.get('inheritedPermissionsDisabled')}"))
    keep_items = walk(drive, a.keep_id)
    checks += [(f"korunan/{n}", r) for n, r in sample_checks(drive, keep_items, a.sample)]
    # Anonim HTTP: Pinterest'in gordugu erisim.
    f = random.choice([i for i in keep_items if i["mimeType"] != FOLDER_MIME])
    link = f.get("webContentLink") or f"https://drive.google.com/uc?export=download&id={f['id']}"
    st, ct, sz = anon_fetch(link)
    checks.append((f"anonim HTTP webContentLink ({f['name']})", f"HTTP {st}, {ct}, {sz} bayt"))
    log(f"anonim HTTP {f['name']}: {st} {ct} {sz} bayt")
    write_summary(summary_lines(title, dict(before_rows), None, checks))

    ok = (roles(root2) == "(yok)" and all(roles(top2[n]) == "(yok)" for n in REPORT_NAMES if n in top2)
          and not left and roles(keep2) == TARGET_ROLE and keep2.get("inheritedPermissionsDisabled")
          and all(r == f"anyone:{TARGET_ROLE}" for n, r in checks if n.startswith("korunan/"))
          and st == 200 and ct.startswith("image/"))
    log("DOGRULAMA " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("fix", "remove"), default="fix")
    ap.add_argument("--folder-id", default=DEFAULT_FOLDER_ID, help="hedef klasor ID (varsayilan PIN_MEDIA)")
    ap.add_argument("--keep-id", default=DEFAULT_FOLDER_ID, help="remove modunda korunacak agac (varsayilan PIN_MEDIA)")
    ap.add_argument("--apply", action="store_true", help="degisiklikleri uygula (yoksa dry-run)")
    ap.add_argument("--sample", type=int, default=3, help="dogrulama icin rastgele dosya sayisi")
    a = ap.parse_args()
    if a.mode == "remove" and a.folder_id == a.keep_id:
        sys.exit("HATA: remove modunda hedef klasor ile korunan klasor ayni olamaz")
    drive = Drive(access_token())
    sys.exit(mode_fix(drive, a) if a.mode == "fix" else mode_remove(drive, a))


if __name__ == "__main__":
    main()
