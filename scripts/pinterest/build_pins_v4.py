#!/usr/bin/env python3
"""
Pinterest pin gorselleri V4 - TOPLU URETIM (KARAR 2 Eyl 2026: filigran YOK,
mockup YOK; posterin kendisi, yalnizca kucultme).

Kaynak : WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/<EDISYON>/2X3/
         WA_POSTER_<PAIR>_<EDISYON>_2X3.jpg (78 cift)
Cikti  : WALL_ART/LISTING_MEDIA/PIN_MEDIA_V2/<EDISYON>/WA_PIN_<PAIR>_<EDISYON>.jpg
         1000x1500, LANCZOS, JPG kalite 85, 4:4:4. Kirpma yok; kaynak 2:3 degilse
         dosya uretilmez ve raporlanir.
Izin   : PIN_MEDIA_V2 klasoru anyone:reader + miras kapali (idempotent), her
         kosuda dogrulanir: klasor, 3 rastgele dosya, 1 dosya anonim HTTP.
Durum  : TEMP/PIN_UPLOAD_STATE_V2.csv (pair, edition, file_id, webContentLink);
         edisyonun satirlari her kosuda yenilenir, diger edisyonlar korunur.
Kontak : TEMP/PIN_KONTAK_V2/PIN_KONTAK_V2_<EDISYON>.jpg (78 kucuk resim).
Eski PIN_MEDIA'ya DOKUNULMAZ. Pinterest'e dokunmaz. Edisyon basina bir kosu.
"""

import argparse
import csv
import io
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pin_media_perms as perms  # noqa: E402  (access_token, Drive, anyone_perms, roles)

Image.MAX_IMAGE_PIXELS = None

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
ROOT = os.environ.get("DRIVE_ROOT", "ASTROLOVE")
POSTER_DIR = f"{ROOT}/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION"
MEDIA_PARENT = f"{ROOT}/WALL_ART/LISTING_MEDIA"
MEDIA_DIR = f"{MEDIA_PARENT}/PIN_MEDIA_V2"
STATE_PATH = f"{ROOT}/TEMP/PIN_UPLOAD_STATE_V2.csv"
KONTAK_DIR = f"{ROOT}/TEMP/PIN_KONTAK_V2"
EDITIONS = ("WARM_PARCHMENT", "MIDNIGHT_BLUE", "DEEP_BLACK", "CHAMPAGNE_IVORY", "PURE_WHITE")
OUT_W, OUT_H = 1000, 1500
JPEG_OPTS = dict(quality=85, subsampling=0, optimize=True, dpi=(72, 72))
STATE_COLS = ["pair", "edition", "file_id", "webContentLink"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ rclone
def rclone(*args, check=True):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): rclone {' '.join(args)}\n{r.stderr.strip()}")
    return r


def lsjson(remote_path, *extra):
    r = rclone("lsjson", f"{REMOTE}:{remote_path}", *extra)
    return json.loads(r.stdout) if r.stdout.strip() else []


def folder_id(remote_dir):
    parent, name = remote_dir.rsplit("/", 1)
    for it in lsjson(parent, "--dirs-only"):
        if it["Name"] == name:
            return it["ID"]
    raise FileNotFoundError(f"klasor yok: {remote_dir}")


# ------------------------------------------------------------------- uretim
def pair_of(name, edition):
    m = re.match(rf"WA_POSTER_([A-Z]+_[A-Z]+)_{edition}_2X3\.jpg$", name)
    return m.group(1) if m else None


def build_edition(edition, work, out_dir):
    src_dir = f"{POSTER_DIR}/{edition}/2X3"
    names = sorted(it["Name"] for it in lsjson(src_dir, "--files-only"))
    pairs = [(n, pair_of(n, edition)) for n in names]
    bad = [n for n, p in pairs if not p]
    if bad:
        log(f"UYARI: ad kalibina uymayan {len(bad)} dosya atlandi: {bad[:5]}")
    pairs = [(n, p) for n, p in pairs if p]
    log(f"{edition}: {len(pairs)} kaynak poster")

    local_src = work / "src" / edition
    local_src.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rclone("copy", f"{REMOTE}:{src_dir}", str(local_src), "--transfers", "8")
    log(f"indirildi: {len(pairs)} dosya, {time.time()-t0:.0f} sn")

    out_dir.mkdir(parents=True, exist_ok=True)
    made, errors = [], []
    for n, pair in pairs:
        try:
            im = Image.open(local_src / n)
            ratio = im.width / im.height
            if abs(ratio - 2 / 3) > 0.003:
                errors.append(f"{pair}: kaynak orani {ratio:.4f} != 2:3 (kirpma yok, uretilmedi)")
                continue
            if im.width < OUT_W:
                errors.append(f"{pair}: kaynak {im.size} ciktidan kucuk")
                continue
            im = im.convert("RGB").resize((OUT_W, OUT_H), Image.LANCZOS)
            out_name = f"WA_PIN_{pair}_{edition}.jpg"
            im.save(out_dir / out_name, "JPEG", **JPEG_OPTS)
            made.append((pair, out_name))
        except Exception as e:
            errors.append(f"{pair}: {type(e).__name__}: {e}")
    log(f"uretildi: {len(made)}, hata: {len(errors)}")
    return made, errors


def contact_sheet(out_dir, made, edition):
    cols, tw, th, band = 13, 100, 150, 16
    rows = (len(made) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 4), rows * (th + band + 4) + 30), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 11)
    d.text((6, 6), f"PIN_MEDIA_V2 · {edition} · {len(made)} pin · 1000x1500 q85", font=f, fill=(20, 20, 20))
    for i, (pair, name) in enumerate(made):
        x, y = (i % cols) * (tw + 4), 30 + (i // cols) * (th + band + 4)
        sheet.paste(Image.open(out_dir / name).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 2, y + th + 2), pair.replace("_", "-").title()[:18], font=f, fill=(40, 40, 40))
    return sheet


# --------------------------------------------------------------------- izin
def ensure_public_reader(drive, fid):
    """Klasor: miras kapali + anyone:reader (idempotent). Dondurur: (miras_kapali, roller)."""
    it = drive.get(fid)
    if not it.get("inheritedPermissionsDisabled"):
        drive._call("PATCH", f"/files/{fid}", params={"fields": "id,inheritedPermissionsDisabled"},
                    json={"inheritedPermissionsDisabled": True})
        log("PIN_MEDIA_V2: miras kapatildi")
    cur = perms.anyone_perms(it)
    if not cur:
        drive.create_anyone(fid, "reader")
        log("PIN_MEDIA_V2: anyone:reader eklendi")
    else:
        for p in cur:
            if p["role"] != "reader":
                drive.set_role(fid, p["id"], "reader")
                log(f"PIN_MEDIA_V2: anyone:{p['role']} -> reader")
    it = drive.get(fid)
    return bool(it.get("inheritedPermissionsDisabled")), perms.roles(it)


def anon_fetch(url):
    try:
        r = requests.get(url, timeout=60, stream=True, allow_redirects=True)
        size = 0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                break
        return r.status_code, r.headers.get("content-type", ""), size
    except requests.RequestException as e:
        return -1, str(e)[:80], 0


# -------------------------------------------------------------------- durum
def load_state(work):
    local = work / "PIN_UPLOAD_STATE_V2.csv"
    r = rclone("copyto", f"{REMOTE}:{STATE_PATH}", str(local), check=False)
    if r.returncode != 0 or not local.exists():
        return []
    with open(local, encoding="utf-8-sig", newline="") as f:
        return [dict(x) for x in csv.DictReader(f)]


def save_state(work, rows):
    local = work / "PIN_UPLOAD_STATE_V2.csv"
    rows = sorted(rows, key=lambda r: (EDITIONS.index(r["edition"]) if r["edition"] in EDITIONS else 9, r["pair"]))
    with open(local, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STATE_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in STATE_COLS} for r in rows)
    rclone("copyto", str(local), f"{REMOTE}:{STATE_PATH}")
    return len(rows)


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edition", required=True, choices=EDITIONS)
    ap.add_argument("--work", default="_work")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    ed = a.edition
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    out_dir = Path(a.out) / "PIN_MEDIA_V2" / ed
    t0 = time.time()

    # 1) uret
    made, errors = build_edition(ed, work, out_dir)
    if not made:
        sys.exit("HATA: hic dosya uretilmedi")

    # 2) yukle
    rclone("copy", str(out_dir), f"{REMOTE}:{MEDIA_DIR}/{ed}", "--transfers", "8")
    log(f"yuklendi: {MEDIA_DIR}/{ed}/ ({len(made)} dosya)")

    # 3) kontak (TEMP, ozel)
    kdir = Path(a.out) / "PIN_KONTAK_V2"
    kdir.mkdir(parents=True, exist_ok=True)
    kname = f"PIN_KONTAK_V2_{ed}.jpg"
    contact_sheet(out_dir, made, ed).save(kdir / kname, "JPEG", quality=88)
    rclone("copyto", str(kdir / kname), f"{REMOTE}:{KONTAK_DIR}/{kname}")

    # 4) izin + dogrulama (Drive API)
    drive = perms.Drive(perms.access_token())
    root_id = folder_id(MEDIA_DIR)
    inh_off, root_roles = ensure_public_reader(drive, root_id)
    time.sleep(10)
    ed_id = folder_id(f"{MEDIA_DIR}/{ed}")
    files = [f for f in drive.children(ed_id) if f["mimeType"] != perms.FOLDER_MIME]
    by_name = {f["name"]: f for f in files}
    missing = [n for _, n in made if n not in by_name]
    if missing:
        log(f"HATA: Drive'da bulunamayan {len(missing)}: {missing[:5]}")
    sample = random.sample(files, min(3, len(files)))
    checks = [(f"PIN_MEDIA_V2 klasor", f"anyone:{root_roles} miras_kapali={inh_off}"),
              (f"{ed} klasor", f"anyone:{perms.roles(drive.get(ed_id))}")]
    for f in sample:
        fresh = drive.get(f["id"])
        checks.append((f["name"], f"anyone:{perms.roles(fresh)}"))
    probe = random.choice(files)
    link = probe.get("webContentLink") or f"https://drive.google.com/uc?export=download&id={probe['id']}"
    st, ct, sz = anon_fetch(link)
    checks.append((f"anonim HTTP {probe['name']}", f"HTTP {st}, {ct}, {sz} bayt"))
    ok = (inh_off and root_roles == "reader" and not missing
          and all(v == "anyone:reader" for k, v in checks[2:-1]) and st == 200 and ct.startswith("image/"))

    # 5) durum dosyasi
    state = [r for r in load_state(work) if r.get("edition") != ed]
    for pair, name in made:
        f = by_name.get(name)
        if f:
            state.append({"pair": pair, "edition": ed, "file_id": f["id"],
                          "webContentLink": f.get("webContentLink") or f"https://drive.google.com/uc?export=download&id={f['id']}"})
    total = save_state(work, state)
    log(f"durum: {STATE_PATH} ({total} satir, {ed}: {len(made)})")

    # 6) ozet
    lines = [f"## PIN_MEDIA_V2 {ed}: {len(made)} pin, {len(errors)} hata, {time.time()-t0:.0f} sn", "",
             f"- Cikti: `{MEDIA_DIR}/{ed}/`", f"- Kontak: `{KONTAK_DIR}/{kname}`",
             f"- Durum: `{STATE_PATH}` ({total} satir)", f"- Dogrulama: **{'PASS' if ok else 'FAIL'}**", "",
             "| Kontrol | Sonuc |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in checks]
    if errors:
        lines += ["", "Hatalar:"] + [f"- {e}" for e in errors]
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(0 if ok and not errors else 1)


if __name__ == "__main__":
    main()
