#!/usr/bin/env python3
"""
START_HERE dokumaninin (Drive Docs) sonuna bir B-kaydi ekler (Google Docs API).

Erisim: rclone.conf'taki OAuth token (drive kapsami Docs API'de gecerlidir).
Guvenlik: kayit dosyasinin ilk satirindaki "Bnn" etiketi dokumanda zaten
varsa (ayni numarali kayit onceden yazilmissa) HICBIR SEY yazmaz, cikis 1.
Token loga yazilmaz.

  python scripts/common/start_here_append.py --file docs/start_here/B94.txt
"""

import argparse
import json
import os
import re
import subprocess
import sys

import requests

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
DOC_ID = os.environ.get("START_HERE_DOC_ID", "1-Blmw9sjMUQa5NdE2sL9wosyY_YRAkYMJ5sfv95jQWQ")
DOCS = "https://docs.googleapis.com/v1/documents"


def log(msg):
    print(msg, flush=True)


def access_token():
    r = subprocess.run(["rclone", "lsd", f"{REMOTE}:", "--max-depth", "1"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone lsd hata: {r.stderr.strip()}")
    r = subprocess.run(["rclone", "config", "dump"], capture_output=True, text=True, check=True)
    tok = json.loads(json.loads(r.stdout)[REMOTE]["token"])["access_token"]
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::add-mask::{tok}", flush=True)
    return tok


def doc_text(doc):
    out = []
    for el in doc["body"]["content"]:
        for pe in el.get("paragraph", {}).get("elements", []):
            out.append(pe.get("textRun", {}).get("content", ""))
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="eklenecek kayit metni (UTF-8)")
    ap.add_argument("--dry-run", action="store_true", help="yazma, yalniz kontrol et")
    a = ap.parse_args()

    text = open(a.file, encoding="utf-8").read().rstrip("\n") + "\n"
    m = re.search(r"^\s*(B\d+)\b", text, re.M)
    if not m:
        sys.exit("HATA: kayit metninde 'Bnn' etiketi yok")
    tag = m.group(1)

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {access_token()}"
    r = s.get(f"{DOCS}/{DOC_ID}", timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: Docs GET {r.status_code}: {r.text[:300]}")
    doc = r.json()
    body = doc_text(doc)
    if re.search(rf"^\s*{tag}\s*-", body, re.M):
        sys.exit(f"HATA: {tag} dokumanda zaten var; yazilmadi")
    last = re.findall(r"^\s*(B\d+)\s*-", body, re.M)
    end = doc["body"]["content"][-1]["endIndex"]
    log(f"dokuman: {len(body)} karakter, son kayit {last[-1] if last else '-'}, ekleme indeksi {end - 1}")
    if a.dry_run:
        log("dry-run: yazilmadi")
        return
    req = {"requests": [{"insertText": {"location": {"index": end - 1}, "text": "\n" + text}}]}
    r = s.post(f"{DOCS}/{DOC_ID}:batchUpdate", json=req, timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: Docs batchUpdate {r.status_code}: {r.text[:300]}")
    # Geri oku ve dogrula.
    body2 = doc_text(s.get(f"{DOCS}/{DOC_ID}", timeout=60).json())
    ok = re.search(rf"^\s*{tag}\s*-", body2, re.M) is not None and body2.rstrip().endswith(text.strip().splitlines()[-1])
    log(f"yazildi: {tag}, {len(text)} karakter; dogrulama {'PASS' if ok else 'FAIL'}")
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(f"## START_HERE {tag}: {'yazildi' if ok else 'DOGRULAMA FAIL'} ({len(text)} karakter)\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
