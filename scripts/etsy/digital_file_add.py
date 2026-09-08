#!/usr/bin/env python3
"""
Dijital poster ilanlarina tesekkur PDF'i EKLER (Mo 8 Eyl 2026). Yalniz EKLEME; silme/degistirme YOK.

Kapsam: 78 cift x 5 edisyon = 390 poster dijital ilani (baslikta edisyon adi, "wallpaper" yok).
Wallpaper ilanlarina DOKUNULMAZ. Dosya tum ilanlara ayni: ASTROLOVE_DIGITAL_THANKYOU_EN.pdf.

Uc (OAS, run 34121615868): POST /shops/{shop_id}/listings/{listing_id}/files, multipart/form-data,
alanlar: file (ikili), name, rank (varsayilan 1) veya var olan listing_file_id; cevap 201 ->
listing_file_id, filename, filesize, filetype. Listeleme: GET .../files.

Her ilanda: (1) state okunur - active degilse ATLANIR, (2) mevcut dosyalar listelenir,
(3) ayni adli PDF varsa ATLANIR (idempotens), 5/5 doluysa ATLANIR ve raporlanir,
(4) PDF sona eklenir (rank = mevcut + 1), (5) dosyalar yeniden listelenir: onceki dosyalarin
listing_file_id ve size_bytes degerleri AYNEN duruyor mu (ZIP bozulmadi kaniti) ve PDF dogru
boyutta mi dogrulanir. --verify-state ile ekleme sonrasi ilan state'i de yeniden okunur.
Kota --quota-min altina inince ilanlar arasinda durur; islenenler STATE'e yazilir (resume).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: digital_file_add.py --pod-state POD.csv --state DFILE.csv --pdf X.pdf --out OUT
          --dry-run|--apply [--limit N] [--quota-min 400] [--verify-state]
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import DIGITAL_ORDER  # noqa: E402
from xsell_links import pair_rx, shop_listings  # noqa: E402

MAX_FILES = 5          # Etsy siniri: dijital ilana en fazla 5 dosya
MIME = "application/pdf"


def read_pod_state(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                out[r["pair"]] = r["listing_id"]
    return out


def read_done(path):
    done = {}
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                done[r["listing_id"]] = dict(r)
    return done


def write_done(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cols = ["listing_id", "pair", "edisyon", "durum", "not", "ts_utc"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def targets(listings, pairs, pod_ids):
    """-> ([(listing_id, pair, edisyon, baslik)], [(cift/edisyon, neden)])"""
    hedef, belirsiz = [], []
    for pair in sorted(pairs):
        rx = pair_rx(pair)
        aday = [x for x in listings if x["listing_id"] not in pod_ids and rx.search(x["title"])
                and not re.search(r"wallpaper", x["title"], re.I)]
        for ed in DIGITAL_ORDER:
            hits = [x for x in aday if ed.lower() in x["title"].lower()]
            if len(hits) == 1:
                hedef.append((hits[0]["listing_id"], pair, ed, hits[0]["title"]))
            else:
                belirsiz.append((f"{pair} / {ed}", f"{len(hits)} aday ilan"))
    return hedef, belirsiz


def ozet(files):
    """Dosya listesi -> karsilastirilabilir ozet (id, ad, boyut)."""
    out = []
    for f in files or []:
        out.append((str(f.get("listing_file_id")), f.get("filename") or "",
                    int(f.get("filesize") or f.get("size_bytes") or 0)))
    return sorted(out)


def plan(before, pdf_name):
    """(eylem, neden). eylem: 'ekle' | 'zaten var' | 'limit dolu'."""
    adlar = [f.get("filename") or "" for f in before or []]
    if pdf_name in adlar:
        return "zaten var", f"{len(adlar)} dosya: {', '.join(adlar)}"
    if len(adlar) >= MAX_FILES:
        return "limit dolu", f"{len(adlar)}/{MAX_FILES} dosya: {', '.join(adlar)}"
    return "ekle", f"mevcut {len(adlar)} dosya: {', '.join(adlar) or '(yok)'}"


def verify(before, after, pdf_name, pdf_size):
    """Ekleme sonrasi dogrulama -> (ok, sorunlar). Onceki dosyalar AYNEN durmali."""
    s = []
    o_b, o_a = ozet(before), ozet(after)
    eksik = [x for x in o_b if x not in o_a]
    if eksik:
        s.append(f"onceki dosya degisti/silindi: {eksik}")
    if len(o_a) != len(o_b) + 1:
        s.append(f"dosya sayisi {len(o_b)} -> {len(o_a)} (beklenen {len(o_b) + 1})")
    yeni = [x for x in o_a if x not in o_b]
    if len(yeni) != 1:
        s.append(f"eklenen dosya sayisi {len(yeni)}")
    else:
        _, ad, boy = yeni[0]
        if ad != pdf_name:
            s.append(f"eklenen dosya adi '{ad}' (beklenen '{pdf_name}')")
        if pdf_size and boy and abs(boy - pdf_size) > 0:
            s.append(f"eklenen dosya boyutu {boy} (yerel {pdf_size})")
    return not s, s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--verify-state", action="store_true", help="ekleme sonrasi ilan state'ini yeniden oku")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pdf = Path(a.pdf)
    if not pdf.is_file():
        raise SystemExit(f"HATA: PDF yok: {pdf}")
    pdf_size = pdf.stat().st_size
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
    log(f"PDF: {pdf.name} | {pdf_size} bayt | sha256:{pdf_sha}")

    pod = read_pod_state(a.pod_state)
    done = read_done(a.state)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    listings = shop_listings(api, shop)
    q0 = api.remaining
    hedef, belirsiz = targets(listings, pod, set(pod.values()))
    kalanlar = [h for h in hedef if (done.get(h[0]) or {}).get("durum") not in ("PASS", "ZATEN VAR")]
    todo = kalanlar[:a.limit] if a.limit else kalanlar
    log(f"aktif ilan {len(listings)} | hedef {len(hedef)} | belirsiz {len(belirsiz)} | islenecek {len(todo)} | kota {q0}")

    res, rows, stopped, t0 = [], [], None, time.time()
    for n, (lid, pair, ed, baslik) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except (TypeError, ValueError):
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = lid
            log(f"KOTA {rem} < {a.quota_min}: {lid} ve sonrasi islenmedi")
            break
        L = api.get(f"/listings/{lid}") or {}
        st = L.get("state")
        if st != "active":
            res.append((lid, f"{pair}/{ed}", "ATLANDI", f"state={st} (active degil)"))
            log(f"[{n}/{len(todo)}] {lid} {pair}/{ed} ATLANDI state={st}")
            continue
        before = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results") or []
        eylem, neden = plan(before, pdf.name)
        if eylem == "zaten var":
            res.append((lid, f"{pair}/{ed}", "ZATEN VAR", neden))
            rows.append({"listing_id": lid, "pair": pair, "edisyon": ed, "durum": "ZATEN VAR", "not": neden,
                         "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
            log(f"[{n}/{len(todo)}] {lid} {pair}/{ed} ZATEN VAR")
            continue
        if eylem == "limit dolu":
            res.append((lid, f"{pair}/{ed}", "ATLANDI", f"dosya limiti dolu - {neden}"))
            log(f"[{n}/{len(todo)}] {lid} {pair}/{ed} ATLANDI limit dolu")
            continue
        if a.dry_run:
            res.append((lid, f"{pair}/{ed}", "HAZIR", f"state={st}; {neden}; rank {len(before) + 1}"))
            log(f"[{n}/{len(todo)}] {lid} {pair}/{ed} HAZIR | {neden}")
            continue
        with open(pdf, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/files",
                          files={"file": (pdf.name, fh, MIME)},
                          data={"name": pdf.name, "rank": str(len(before) + 1)})
        after = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results") or []
        ok, sorun = verify(before, after, pdf.name, pdf_size)
        st2 = st
        if a.verify_state:
            st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            if st2 != st:
                ok, sorun = False, sorun + [f"state {st} -> {st2}"]
        durum = "PASS" if ok else "FAIL"
        notu = (f"dosya {len(before)} -> {len(after)}; ZIP korundu; state {st}"
                + (f" -> {st2}" if a.verify_state else "")) if ok else "; ".join(sorun)
        res.append((lid, f"{pair}/{ed}", durum, notu))
        rows.append({"listing_id": lid, "pair": pair, "edisyon": ed, "durum": durum, "not": notu,
                     "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {lid} {pair}/{ed} {durum} ({'eklendi' if ok else 'HATA'}) | "
            f"gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s %{100 * n // len(todo)} | kota {api.remaining}")

    if a.apply and rows:
        birlesik = {kk: dict(vv) for kk, vv in done.items()}
        for r in rows:
            birlesik[r["listing_id"]] = r
        write_done(a.state, list(birlesik.values()))

    islenen = [r for r in res if r[2] in ("PASS", "HAZIR")]
    zaten = [r for r in res if r[2] == "ZATEN VAR"]
    bad = [r for r in res if r[2] in ("FAIL", "ATLANDI")]
    kalan = len(kalanlar) - len(res)
    md = [f"## Dijital tesekkur PDF ekleme ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- PDF `{pdf.name}` {pdf_size} bayt (sha256:{pdf_sha})",
          f"- hedef {len(hedef)}; islenen {len(res)}; eklenen/hazir {len(islenen)}; zaten var {len(zaten)}; "
          f"atlanan/sorunlu {len(bad)}; kalan {kalan}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    if belirsiz:
        md += ["### Eslesmeyen", "", "| hedef | neden |", "|---|---|"] + \
              [f"| {p} | {e} |" for p, e in belirsiz] + [""]
    if bad:
        md += ["### Atlanan / sorunlu", "", "| listing_id | cift/edisyon | durum | neden |", "|---|---|---|---|"] + \
              [f"| {l} | {p} | {d} | {nt} |" for l, p, d, nt in bad] + [""]
    md += ["### Sonuc", "", "| listing_id | cift/edisyon | durum | not |", "|---|---|---|---|"]
    md += [f"| {l} | {p} | {d} | {nt} |" for l, p, d, nt in res]
    md += ["", f"- Kota once {q0} / sonra {api.remaining}"]
    text = "\n".join(md)
    log(text)
    (out / "DFILE_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "dfile_result.json").write_text(
        json.dumps({"rows": res, "belirsiz": belirsiz, "kalan": kalan, "quota": [q0, api.remaining],
                    "pdf": {"name": pdf.name, "size": pdf_size, "sha256_16": pdf_sha}},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
