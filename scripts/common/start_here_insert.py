#!/usr/bin/env python3
"""
START_HERE dokumaninda BELIRLI BIR SATIRIN ARDINA metin ekler (Google Docs API).

Sonuna ekleme icin start_here_append.py kullanilir; bu script yazilmis bir
kaydin ici duzeltilecegi zaman (or. B99'un bir bolumune satir eklemek) icindir.

Guvenlik:
 - Ekleme indeksi API'nin kendi paragraf indekslerinden alinir (UTF-16 kaymasi
   olmaz), metin arama ile hesaplanmaz.
 - Capa metni birden cok yerde geciyorsa DUR (--occurrence ile secilebilir).
 - Eklenecek metin dokumanda zaten varsa DUR (tekrar yazmaz).
 - Yazim sonrasi geri okunur ve dogrulanir. Token loga yazilmaz.

  python scripts/common/start_here_insert.py --anchor "workflow pw-ru-fill.yml." \\
      --text-file docs/start_here/B99_ek1.txt [--dry-run]
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


def runs(doc):
    """[(startIndex, endIndex, metin)] - dokumandaki tum metin parcalari."""
    out = []
    for el in doc["body"]["content"]:
        for pe in el.get("paragraph", {}).get("elements", []):
            tr = pe.get("textRun")
            if tr:
                out.append((pe["startIndex"], pe["endIndex"], tr.get("content", "")))
    return out


def doc_text(doc):
    return "".join(t for _, _, t in runs(doc))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor", required=True, help="ardina eklenecek satirin (bir parcasinin) metni")
    ap.add_argument("--text-file", required=True, help="eklenecek metin (UTF-8)")
    ap.add_argument("--occurrence", default="tek", choices=["tek", "ilk", "son"],
                    help="capa birden cok geciyorsa: tek = DUR (varsayilan)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    text = open(a.text_file, encoding="utf-8").read().strip("\n")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {access_token()}"
    r = s.get(f"{DOCS}/{DOC_ID}", timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: Docs GET {r.status_code}: {r.text[:300]}")
    doc = r.json()
    body = doc_text(doc)
    if text.strip() and text.strip().splitlines()[0].strip() in body:
        sys.exit("HATA: eklenecek metnin ilk satiri dokumanda zaten var; yazilmadi")

    hits = [(st, en, t) for st, en, t in runs(doc) if a.anchor in t]
    log(f"dokuman: {len(body)} karakter, capa eslesmesi: {len(hits)}")
    if not hits:
        sys.exit(f"HATA: capa bulunamadi: {a.anchor!r}")
    if len(hits) > 1 and a.occurrence == "tek":
        for st, en, t in hits:
            log(f"  index {st}-{en}: {t.strip()[:80]}")
        sys.exit("HATA: capa birden cok yerde geciyor; --occurrence ilk|son verin")
    st, en, t = hits[0] if a.occurrence != "son" else hits[-1]
    # Capanin satiri satir sonuyla bitiyorsa oradan, degilse satir sonu ekleyerek yaz.
    ins_at = en if t.endswith("\n") else en
    payload = (text + "\n") if t.endswith("\n") else ("\n" + text)
    log(f"capa: {t.strip()[:90]!r} (index {st}-{en}) -> ekleme indeksi {ins_at}")
    log(f"eklenecek {len(payload)} karakter, {payload.count(chr(10))} satir")
    if a.dry_run:
        log("dry-run: yazilmadi")
        return

    req = {"requests": [{"insertText": {"location": {"index": ins_at}, "text": payload}}]}
    r = s.post(f"{DOCS}/{DOC_ID}:batchUpdate", json=req, timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: Docs batchUpdate {r.status_code}: {r.text[:300]}")
    body2 = doc_text(s.get(f"{DOCS}/{DOC_ID}", timeout=60).json())
    idx_a, idx_t = body2.find(a.anchor), body2.find(text.splitlines()[0].strip())
    ok = idx_t > idx_a > -1 and (idx_t - idx_a) < len(a.anchor) + 120
    log(f"yazildi: {len(payload)} karakter; dogrulama {'PASS' if ok else 'FAIL'} "
        f"(capa {idx_a}, yeni metin {idx_t})")
    if ok:
        j = body2.find(a.anchor)
        log("----- capa cevresi -----")
        log(body2[j:j + len(a.anchor) + len(text) + 40].rstrip())
        log("----- son -----")
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(f"## START_HERE ekleme: {'PASS' if ok else 'FAIL'} ({len(payload)} karakter)\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
