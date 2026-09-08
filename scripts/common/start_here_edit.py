#!/usr/bin/env python3
"""
START_HERE dokumaninda yazilmis bir kaydin ICINDE duzenleme (Google Docs API).

Islem listesi (JSON) sirayla uygulanir; her adimda dokuman yeniden okunur, boylece
indeks kaymasi olmaz. Desteklenen islemler:
  {"op":"replace_line",  "find":"<satir>", "text":"<yeni satir>"}
  {"op":"insert_after",  "anchor":"<satir>", "text_file":"<dosya>"}
  {"op":"replace_block", "from":"<ilk satir>", "to":"<son satir>", "text_file":"<dosya>"}

Guvenlik: her capa TEK eslesmeli (aksi halde DUR), indeksler API'nin paragraf
indekslerinden alinir (UTF-16 kaymasi yok), yazim sonrasi geri okunup dogrulanir,
token loga yazilmaz.

  python scripts/common/start_here_edit.py --ops docs/start_here/B99_ops2.json [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from start_here_insert import DOCS, DOC_ID, access_token, doc_text, runs  # noqa: E402


def log(m):
    print(m, flush=True)


def get_doc(s):
    r = s.get(f"{DOCS}/{DOC_ID}", timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: Docs GET {r.status_code}: {r.text[:300]}")
    return r.json()


def find_run(doc, needle, label):
    """Metni iceren TEK paragraf parcasini dondurur: (startIndex, endIndex, metin)."""
    hits = [(st, en, t) for st, en, t in runs(doc) if needle in t]
    if not hits:
        sys.exit(f"HATA: {label} bulunamadi: {needle!r}")
    if len(hits) > 1:
        for st, en, t in hits:
            log(f"  index {st}-{en}: {t.strip()[:80]}")
        sys.exit(f"HATA: {label} {len(hits)} yerde geciyor (tek eslesme sart): {needle!r}")
    return hits[0]


def payload_text(op):
    if "text_file" in op:
        return open(op["text_file"], encoding="utf-8").read().strip("\n") + "\n"
    return op["text"]


def plan(doc, op):
    """(silinecek_aralik | None, ekleme_indeksi, metin, aciklama)"""
    kind = op["op"]
    if kind == "replace_line":
        st, en, t = find_run(doc, op["find"], "find")
        nl = "\n" if t.endswith("\n") else ""
        return (st, en), st, op["text"] + nl, f"satir degistir: {t.strip()[:60]!r}"
    if kind == "insert_after":
        st, en, t = find_run(doc, op["anchor"], "anchor")
        text = payload_text(op)
        return None, en, (text if t.endswith("\n") else "\n" + text), \
            f"ardina ekle: {t.strip()[:60]!r}"
    if kind == "replace_block":
        st1, en1, t1 = find_run(doc, op["from"], "from")
        st2, en2, t2 = find_run(doc, op["to"], "to")
        if st2 < st1:
            sys.exit("HATA: 'to' capasi 'from' capasindan once geliyor")
        return (st1, en2), st1, payload_text(op), \
            f"blok degistir: {t1.strip()[:40]!r} .. {t2.strip()[:40]!r} ({en2 - st1} karakter)"
    sys.exit(f"HATA: bilinmeyen op: {kind}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ops", required=True, help="islem listesi (JSON)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ops = json.loads(open(a.ops, encoding="utf-8").read())

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {access_token()}"
    done = 0
    for i, op in enumerate(ops, 1):
        doc = get_doc(s)
        rng, ins_at, text, desc = plan(doc, op)
        log(f"[{i}/{len(ops)}] {desc}")
        log(f"          aralik {rng} -> indeks {ins_at}, {len(text)} karakter")
        if a.dry_run:
            continue
        reqs = []
        if rng:
            reqs.append({"deleteContentRange": {"range": {"startIndex": rng[0], "endIndex": rng[1]}}})
        reqs.append({"insertText": {"location": {"index": ins_at}, "text": text}})
        r = s.post(f"{DOCS}/{DOC_ID}:batchUpdate", json={"requests": reqs}, timeout=60)
        if r.status_code != 200:
            sys.exit(f"HATA: batchUpdate {r.status_code}: {r.text[:300]}")
        done += 1

    if a.dry_run:
        log(f"dry-run: yazilmadi ({len(ops)} islem plani yukarida, capalar tek eslesme)")
        return
    body = doc_text(get_doc(s))
    ok = True
    for op in ops:                                        # geri okuma dogrulamasi
        want = (op.get("text") or payload_text(op)).strip().splitlines()[0].strip()
        gone = op.get("find") if op["op"] == "replace_line" else (
            op.get("from") if op["op"] == "replace_block" else None)
        if want not in body:
            log(f"DOGRULAMA FAIL: yok -> {want[:70]!r}")
            ok = False
        # yeni metin de ayni satirla basliyorsa (blok basi korunuyorsa) silinme kontrolu yapilmaz
        if gone and gone in (op.get("text") or payload_text(op)):
            gone = None
        if gone and gone in body:
            log(f"DOGRULAMA FAIL: silinmemis -> {gone[:70]!r}")
            ok = False
    log(f"uygulanan islem: {done}; dogrulama {'PASS' if ok else 'FAIL'}")
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(f"## START_HERE duzenleme: {done} islem, {'PASS' if ok else 'FAIL'}\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
