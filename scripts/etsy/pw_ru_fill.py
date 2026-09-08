#!/usr/bin/env python3
"""
Pure White (PW) dijital ilanlarina RU cevirisi (Mo 8 Eyl 2026). YENI CEVIRI URETILMEZ.

Kaynak: ayni ciftin CANLI Champagne Ivory (CI) ilanindaki RU cevirisi. Olculen gercek
(run 34191071811, ARIES_LEO): dijital RU GOVDESI edisyondan bagimsiz — CI ve Midnight Blue
RU aciklamalari birebir ayni (1203 karakter), RU etiketleri ayni 13 genel etiket (renk yok);
edisyon adi yalniz BASLIKTA gecer ("... серия Champagne Ivory, ..."). Bu yuzden token
donusumu: baslikta edisyon adi CI -> PW; govde ve etiketler birebir kopyalanir.

Her ilan icin yazmadan once: PW state=active mi, CI RU govdesi dolu mu, capraz satis blogu
(baslik + ciftin POD linki) yerinde mi, AI maddesi kalmis mi, etiket sayisi 13 mu, kalinti
taramasi (Latin + Kiril: Champagne/Ivory ve diger edisyon adlari) temiz mi. Herhangi biri
saglanmazsa ilan ATLANIR ve raporlanir - metin uydurulmaz. Yalniz RU yazilir; EN'e DOKUNULMAZ.
Kota --quota-min altina inince ilanlar arasinda durur; islenenler STATE'e yazilir (resume).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pw_ru_fill.py --pod-state POD.csv --state PW_RU.csv --out OUT --dry-run|--apply
          [--limit N] [--quota-min 400]
"""
import argparse
import csv
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_listing_update import norm  # noqa: E402
from xsell_links import pair_rx, shop_listings  # noqa: E402

SRC_ED, DST_ED = "Champagne Ivory", "Pure White"
URL = "https://www.etsy.com/listing/{lid}"
XS_HEAD = "ХОТИТЕ ЕГО НА СТЕНЕ?"          # capraz satis blogu basligi (gece kosusunda eklendi)
NOTE_HEAD = "ОБРАТИТЕ ВНИМАНИЕ:"
N_TAGS = 13                                # 12 cekirdek RU etiketi + cift etiketi
AI_RX = re.compile(r"искусственн\w*\s+интеллект", re.I)
# Kaynakta kalmamasi gereken edisyon/renk izleri (Latin + Kiril)
KALINTI = ["Champagne", "Ivory", "Midnight Blue", "Warm Parchment", "Deep Black",
           "шампан", "слоновой кости", "кремов", "пергамент", "тёмно-син", "темно-син",
           "полноч", "чёрн", "черн"]
# POD ilanlarina 7 Eyl'de eklenen kagit/eko maddeleri (dijital metinde BEKLENMEZ; raporlanir)
PAPER_RU = ["Веганская сертифицированная бумага", "Сырьё из устойчивых источников",
            "ближайшей доступной лаборатории", "насыщенный угольный"]


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
    cols = ["listing_id", "pair", "ci_id", "durum", "not", "ts_utc"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def edition_ids(listings, pair):
    """(pw_id, ci_id, hata) - baslik uzerinden eslesme; belirsizse hata."""
    rx = pair_rx(pair)
    aday = [x for x in listings if rx.search(x["title"]) and not re.search(r"wallpaper", x["title"], re.I)]
    out = {}
    for ed in (DST_ED, SRC_ED):
        hits = [x for x in aday if ed.lower() in x["title"].lower()]
        if len(hits) != 1:
            return None, None, f"{ed}: {len(hits)} aday ilan"
        out[ed] = hits[0]["listing_id"]
    return out[DST_ED], out[SRC_ED], ""


def kalinti(*metinler):
    """Kaynakta/ciktida kalmamasi gereken edisyon-renk izleri."""
    hep = "\n".join(m for m in metinler if m)
    return [k for k in KALINTI if k.lower() in hep.lower() and k != DST_ED]


def build(ci_title, ci_desc, ci_tags, pod_id):
    """CI RU -> PW RU. (title, desc, tags, hata)."""
    t, d = (ci_title or "").strip(), norm(ci_desc or "")
    tags = [x.strip() for x in (ci_tags or []) if x.strip()]
    if not d:
        return None, None, None, "CI RU govdesi bos"
    if t.count(SRC_ED) != 1:
        return None, None, None, f"CI RU basliginda '{SRC_ED}' {t.count(SRC_ED)} kez"
    lines = [l.strip() for l in d.split("\n")]
    if XS_HEAD not in lines:
        return None, None, None, "capraz satis blogu (RU) yok"
    i = lines.index(XS_HEAD)
    url = URL.format(lid=pod_id)
    if url not in lines[i:i + 4]:
        return None, None, None, "capraz satis blogunda ciftin POD linki yok"
    if NOTE_HEAD not in lines:
        return None, None, None, f"'{NOTE_HEAD}' basligi yok"
    if AI_RX.search(d):
        return None, None, None, "kaynakta AI maddesi duruyor"
    if len(tags) != N_TAGS:
        return None, None, None, f"CI RU etiket sayisi {len(tags)} (beklenen {N_TAGS})"
    kal = kalinti(t.replace(SRC_ED, ""), d, " ".join(tags))
    if kal:
        return None, None, None, f"kaynakta renk/edisyon izi: {', '.join(kal)}"
    return t.replace(SRC_ED, DST_ED), d, tags, ""


def check(title, desc, tags, ci_title, ci_desc, ci_tags, pod_id):
    """Yazilacak (ya da geri okunan) RU dogrulamasi -> (ok, sorunlar)."""
    s = []
    if SRC_ED not in (ci_title or "") or DST_ED not in (title or ""):
        s.append("baslikta edisyon donusumu yok")
    if (title or "") != (ci_title or "").replace(SRC_ED, DST_ED):
        s.append("baslik kaynakla (edisyon disinda) ayni degil")
    if norm(desc or "") != norm(ci_desc or ""):
        s.append("govde kaynakla birebir ayni degil")
    if [x.strip() for x in (tags or [])] != [x.strip() for x in (ci_tags or [])]:
        s.append("etiketler kaynakla ayni degil")
    if len(tags or []) != N_TAGS:
        s.append(f"etiket sayisi {len(tags or [])}")
    kal = kalinti(title, desc, " ".join(tags or []))
    if kal:
        s.append(f"kalinti: {', '.join(kal)}")
    if URL.format(lid=pod_id) not in (desc or ""):
        s.append("POD linki yok")
    if AI_RX.search(desc or ""):
        s.append("AI maddesi var")
    return not s, s


def paper_notu(d):
    var = [p for p in PAPER_RU if p in (d or "")]
    return f"kagit/eko maddesi {len(var)}/4"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=400)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

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
    log(f"aktif ilan {len(listings)} | POD cift {len(pod)} | kota {q0}")

    hedef, esles_hata = [], []
    for pair in sorted(pod):
        pw, ci, err = edition_ids(listings, pair)
        if err:
            esles_hata.append((pair, err))
        else:
            hedef.append((pair, pw, ci))
    kalanlar = [h for h in hedef if (done.get(h[1]) or {}).get("durum") not in ("PASS", "DEGISIM YOK")]
    todo = kalanlar[:a.limit] if a.limit else kalanlar
    log(f"eslesen {len(hedef)} | eslesmeyen {len(esles_hata)} | islenecek {len(todo)}")

    res, rows, ornek, stopped, t0 = [], [], None, None, time.time()
    for n, (pair, pw, ci) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except (TypeError, ValueError):
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = pw
            log(f"KOTA {rem} < {a.quota_min}: {pw} ve sonrasi islenmedi")
            break
        L = api.get(f"/listings/{pw}") or {}
        if L.get("state") != "active":
            res.append((pw, pair, "ATLANDI", f"PW state={L.get('state')} (active degil)"))
            log(f"[{n}/{len(todo)}] {pw} {pair} ATLANDI state={L.get('state')}")
            continue
        cru = api.get(f"/shops/{shop}/listings/{ci}/translations/ru", ok404=True) or {}
        title, desc, tags, err = build(cru.get("title"), cru.get("description"), cru.get("tags"), pod[pair])
        if err:
            res.append((pw, pair, "ATLANDI", f"kaynak CI {ci}: {err}"))
            log(f"[{n}/{len(todo)}] {pw} {pair} ATLANDI {err}")
            continue
        ok, sorun = check(title, desc, tags, cru.get("title"), cru.get("description"), cru.get("tags"), pod[pair])
        if not ok:
            res.append((pw, pair, "SIRA DISI", "; ".join(sorun)))
            continue
        pru = api.get(f"/shops/{shop}/listings/{pw}/translations/ru", ok404=True) or {}
        var_t, var_d = (pru.get("title") or "").strip(), norm(pru.get("description") or "")
        var_g = [x.strip() for x in (pru.get("tags") or [])]
        if var_d and (var_t, var_d, var_g) == (title, desc, tags):
            res.append((pw, pair, "DEGISIM YOK", paper_notu(desc)))
            rows.append({"listing_id": pw, "pair": pair, "ci_id": ci, "durum": "DEGISIM YOK",
                         "not": paper_notu(desc), "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
            continue
        if var_d:
            res.append((pw, pair, "ATLANDI", "PW RU zaten dolu ve farkli (elle bakilmali)"))
            continue
        if ornek is None:
            ornek = (pair, pw, ci, cru.get("title"), title,
                     "\n".join(difflib.unified_diff([], desc.split("\n"), "eski (bos)", "yeni", lineterm="", n=0)),
                     tags)
        if a.dry_run:
            res.append((pw, pair, "HAZIR", f"kaynak CI {ci} | {paper_notu(desc)}"))
            log(f"[{n}/{len(todo)}] {pw} {pair} HAZIR | kaynak {ci}")
            continue
        r = api.put(f"/shops/{shop}/listings/{pw}/translations/ru",
                    {"title": title, "description": desc, "tags": ",".join(tags)})
        back = r if isinstance(r, dict) and r.get("description") else \
            (api.get(f"/shops/{shop}/listings/{pw}/translations/ru", ok404=True) or {})
        b_tags = [x.strip() for x in (back.get("tags") or [])]
        ok2, sorun2 = check(back.get("title"), back.get("description"), b_tags,
                            cru.get("title"), cru.get("description"), cru.get("tags"), pod[pair])
        L2 = api.get(f"/listings/{pw}") or {}
        if L2.get("state") != "active":
            ok2, sorun2 = False, sorun2 + [f"PW state {L2.get('state')} oldu"]
        durum = "PASS" if ok2 else "FAIL"
        notu = f"kaynak CI {ci} | {len(b_tags)} etiket | {paper_notu(desc)}" if ok2 else "; ".join(sorun2)
        res.append((pw, pair, durum, notu))
        rows.append({"listing_id": pw, "pair": pair, "ci_id": ci, "durum": durum, "not": notu,
                     "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {pw} {pair} {durum} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s "
            f"%{100 * n // len(todo)} | kota {api.remaining}")

    if a.apply and rows:
        birlesik = {kk: dict(vv) for kk, vv in done.items()}
        for r in rows:
            birlesik[r["listing_id"]] = r
        write_done(a.state, list(birlesik.values()))

    islenen = [r for r in res if r[2] in ("PASS", "HAZIR")]
    bad = [r for r in res if r[2] in ("FAIL", "ATLANDI", "SIRA DISI")]
    kalan = len(kalanlar) - len(res)
    md = [f"## Pure White RU cevirisi ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- cift {len(pod)}; eslesen {len(hedef)}; islenen {len(res)}; yazilan/hazir {len(islenen)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; atlanan/sorunlu {len(bad)}; kalan {kalan}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    if esles_hata:
        md += ["### Eslesmeyen cift", "", "| cift | neden |", "|---|---|"] + \
              [f"| {p} | {e} |" for p, e in esles_hata] + [""]
    if ornek:
        md += [f"### Ornek ({ornek[0]}) — PW {ornek[1]} <- CI {ornek[2]}", "",
               f"- RU baslik kaynak: `{ornek[3]}`", f"- RU baslik yeni:   `{ornek[4]}`",
               f"- RU etiket ({len(ornek[6])}): {ornek[6]}", "", "```diff", ornek[5], "```", ""]
    md += ["### Sonuc", "", "| listing_id | cift | durum | not |", "|---|---|---|---|"]
    md += [f"| {l} | {p} | {d} | {nt} |" for l, p, d, nt in res]
    md += ["", f"- Kota once {q0} / sonra {api.remaining}"]
    text = "\n".join(md)
    log(text)
    (out / "PW_RU_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "pw_ru_result.json").write_text(
        json.dumps({"rows": res, "eslesmeyen": esles_hata, "kalan": kalan, "quota": [q0, api.remaining]},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
