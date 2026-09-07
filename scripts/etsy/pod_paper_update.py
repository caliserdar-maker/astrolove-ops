#!/usr/bin/env python3
"""
POD ilanlarina kagit/eko maddeleri + lab cumlesi duzeltmesi (Mo 7 Eyl 2026). EN + RU.

Dort degisiklik (hepsi birebir metin; capalar TAM SATIR eslesmesiyle bulunur):
  1. EN "✦ MUSEUM-QUALITY MATERIALS" listesinde altin murekkep maddesinin ALTINA 2 madde.
  2. RU "✦ МАТЕРИАЛЫ МУЗЕЙНОГО КАЧЕСТВА" listesinde ayni yere 2 madde.
  3. EN/RU "MADE TO ORDER & SHIPPING" icindeki lab cumlesi yeni haliyle degistirilir.
  4. EN "✦ PLEASE NOTE" / RU "✦ ОБРАТИТЕ ВНИМАНИЕ" listesinin SONUNA matte siyah maddesi
     (ICC soft-proof olcumu: matte pamuk kagitta maksimum siyah L=53; beklenti yonetimi).
Capalar bulunmazsa ilan ATLANIR (metin uydurulmaz). Ilan state=active degilse KOSU DURUR.
RU yazmasinda title/tags GET'ten birebir geri gonderilir (etiket kaybi yok). Baslik, etiket,
gorsel, fiyat, varyant degismez. Kota --quota-min altina inince ilanlar arasinda durur; islenenler
STATE'e yazilir (resume). ETA sayaci her ilanda.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_paper_update.py --pod-state STATE.csv --state PAPER.csv --out OUT --dry-run|--apply
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

EN = {
    "anchor": "- Gold tones are printed as flat golden ink, not metallic foil",
    "add": ["- Vegan-certified paper, natural white tone",
            "- Sustainably sourced fibres, plastic-free packaging, printed at the lab nearest you"],
    "old_lab": "US orders are printed in the US; EU and UK orders are printed at our UK/EU lab for faster delivery.",
    "new_lab": "US orders are printed in the US; EU and UK orders at our UK/EU lab; orders elsewhere at the nearest available lab.",
    "note_head": "✦ PLEASE NOTE",
    "note_add": "- On matte cotton paper, deep blacks print as a rich charcoal rather than screen black \u2014 this is the "
                "natural character of fine art paper.",
}
RU = {
    "anchor": "- Золотые тона печатаются плоской золотистой краской, не металлической фольгой",
    "add": ["- Веганская сертифицированная бумага, натуральный белый тон",
            "- Сырьё из устойчивых источников, упаковка без пластика, печать в ближайшей к вам лаборатории"],
    "old_lab": "Заказы из США печатаются в США; заказы из ЕС и Великобритании — в нашей лаборатории в Великобритании/ЕС "
               "для более быстрой доставки.",
    "new_lab": "Заказы из США печатаются в США; заказы из ЕС и Великобритании — в нашей лаборатории в Великобритании/ЕС; "
               "остальные заказы — в ближайшей доступной лаборатории.",
    "note_head": "✦ ОБРАТИТЕ ВНИМАНИЕ",
    "note_add": "- На матовой хлопковой бумаге глубокий чёрный печатается как насыщенный угольный, а не как чёрный "
                "на экране — это естественное свойство художественной бумаги.",
}


def read_pod_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


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
    cols = ["listing_id", "pair", "durum", "not", "ts_utc"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def note_blok_sonu(lines, spec):
    """PLEASE NOTE basliginin indeksi ve listesinin bittigi indeks. (i, j) veya (None, hata)."""
    head = spec["note_head"]
    if sum(1 for l in lines if l.strip() == head) != 1:
        return None, "PLEASE NOTE capasi bulunamadi/birden fazla"
    i = next(k for k, l in enumerate(lines) if l.strip() == head)
    j = i + 1
    while j < len(lines) and lines[j].strip().startswith("- "):
        j += 1
    if j == i + 1:
        return None, "PLEASE NOTE listesi bos"
    return i, j


def note_insert(lines, spec):
    """Matte siyah maddesini PLEASE NOTE listesinin SONUNA ekler. (yeni_lines, hata)."""
    i, j = note_blok_sonu(lines, spec)
    if i is None:
        return None, j
    if spec["note_add"] in [l.strip() for l in lines[i + 1:j]]:
        return lines, ""
    return lines[:j] + [spec["note_add"]] + lines[j:], ""


def transform(text, spec):
    """(yeni_metin, hata). Iki madde capanin altina, lab cumlesi degisir, matte maddesi PLEASE NOTE sonuna."""
    t = norm(text)
    if not t.strip():
        return None, "metin bos"
    lines = t.split("\n")
    if sum(1 for l in lines if l.strip() == spec["anchor"]) != 1:
        return None, "capa (altin murekkep maddesi) bulunamadi/birden fazla"
    i = next(k for k, l in enumerate(lines) if l.strip() == spec["anchor"])
    var = [l.strip() for l in lines[i + 1:i + 3]] == spec["add"]
    yeni = lines if var else lines[:i + 1] + list(spec["add"]) + lines[i + 1:]
    yeni, err = note_insert(yeni, spec)
    if err:
        return None, err
    x = "\n".join(yeni)
    if spec["old_lab"] in x:
        x = x.replace(spec["old_lab"], spec["new_lab"])
    elif spec["new_lab"] not in x:
        return None, "lab cumlesi bulunamadi"
    return x.strip(), ""


def base(t, spec):
    """Karsilastirma tabani: eklenen 2 madde cikarilir, yeni lab cumlesi eskiye cevrilir."""
    atilacak = set(spec["add"]) | {spec["note_add"]}
    lines = [l for l in norm(t).split("\n") if l.strip() not in atilacak]
    return "\n".join(lines).replace(spec["new_lab"], spec["old_lab"]).strip()


def check(old, new, spec):
    sorun = []
    if base(old, spec) != base(new, spec):
        sorun.append("bu uc degisiklik disinda metin degismis")
    lines = [l.strip() for l in norm(new).split("\n")]
    for m in spec["add"]:
        if lines.count(m) != 1:
            sorun.append(f"madde {lines.count(m)} kez: {m[:40]}")
    if spec["anchor"] in lines:
        i = lines.index(spec["anchor"])
        if lines[i + 1:i + 3] != spec["add"]:
            sorun.append("maddeler capanin hemen altinda degil")
    else:
        sorun.append("capa kayboldu")
    if spec["old_lab"] in norm(new):
        sorun.append("eski lab cumlesi duruyor")
    if spec["new_lab"] not in norm(new):
        sorun.append("yeni lab cumlesi yok")
    if lines.count(spec["note_add"]) != 1:
        sorun.append(f"matte siyah maddesi {lines.count(spec['note_add'])} kez")
    else:
        i, j = note_blok_sonu(norm(new).split("\n"), spec)
        if i is None:
            sorun.append(f"PLEASE NOTE: {j}")
        elif norm(new).split("\n")[j - 1].strip() != spec["note_add"]:
            sorun.append("matte siyah maddesi PLEASE NOTE listesinin sonunda degil")
    return not sorun, sorun


def diff_text(old, new):
    return "\n".join(difflib.unified_diff(norm(old).split("\n"), norm(new).split("\n"), "eski", "yeni", lineterm="", n=1))


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
    kalanlar = [(p, l) for p, l in pod if (done.get(l) or {}).get("durum") not in ("PASS", "DEGISIM YOK")]
    todo = kalanlar[:a.limit] if a.limit else kalanlar

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    q0, res, rows, ornek, stopped, t0 = None, [], [], None, None, time.time()
    log(f"POD ilan {len(pod)} | islenecek {len(todo)}")

    for n, (pair, lid) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = lid
            log(f"KOTA {rem} < {a.quota_min}: {lid} ve sonrasi islenmedi")
            break
        L = api.get(f"/listings/{lid}") or {}
        if q0 is None:
            q0 = api.remaining
        if L.get("state") != "active":
            raise SystemExit(f"DUR: {pair} {lid} state={L.get('state')} (active degil); hicbir yazma yapilmadi")
        tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        new_en, err_en = transform(L.get("description") or "", EN)
        if err_en:
            res.append((lid, pair, "ATLANDI", f"EN: {err_en}"))
            log(f"[{n}/{len(todo)}] {lid} {pair} ATLANDI EN: {err_en}")
            continue
        ok_en, s_en = check(L.get("description"), new_en, EN)
        if not ok_en:
            res.append((lid, pair, "SIRA DISI", f"EN: {', '.join(s_en)}"))
            continue
        new_ru, ru_note = None, "RU cevirisi yok"
        if (tru.get("description") or "").strip():
            new_ru, err_ru = transform(tru["description"], RU)
            if err_ru:
                res.append((lid, pair, "ATLANDI", f"RU: {err_ru}"))
                log(f"[{n}/{len(todo)}] {lid} {pair} ATLANDI RU: {err_ru}")
                continue
            ok_ru, s_ru = check(tru["description"], new_ru, RU)
            if not ok_ru:
                res.append((lid, pair, "SIRA DISI", f"RU: {', '.join(s_ru)}"))
                continue
            ru_note = "RU guncellenecek"
        en_ayni = norm(L.get("description")) == norm(new_en)
        ru_ayni = new_ru is None or norm(tru.get("description")) == norm(new_ru)
        if en_ayni and ru_ayni:
            res.append((lid, pair, "DEGISIM YOK", ru_note))
            rows.append({"listing_id": lid, "pair": pair, "durum": "DEGISIM YOK", "not": ru_note,
                         "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
            continue
        if ornek is None:
            ornek = (pair, diff_text(L.get("description"), new_en), diff_text(tru.get("description"), new_ru) if new_ru else "(RU yok)")
        if a.dry_run:
            res.append((lid, pair, "HAZIR", ru_note))
            log(f"[{n}/{len(todo)}] {lid} {pair} HAZIR | {ru_note}")
            continue
        r = api.patch(f"/shops/{shop}/listings/{lid}", {"description": new_en})
        back_en = r if isinstance(r, dict) and r.get("description") else (api.get(f"/listings/{lid}") or {})
        p_en = norm(back_en.get("description")) == norm(new_en)
        p_ru, meta = True, "RU yok"
        if new_ru is not None:
            t_old, tags_old = tru.get("title") or "", [t.strip() for t in (tru.get("tags") or [])]
            r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                        {"title": t_old, "description": new_ru, "tags": ",".join(tags_old)})
            back_ru = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
            tags_new = [t.strip() for t in (back_ru.get("tags") or [])]
            p_ru = norm(back_ru.get("description")) == norm(new_ru)
            ok_meta = back_ru.get("title") == t_old and tags_new == tags_old
            p_ru = p_ru and ok_meta
            meta = f"RU baslik/etiket {'korundu' if ok_meta else 'DEGISTI'} ({len(tags_new)} etiket)"
        durum = "PASS" if (p_en and p_ru) else "FAIL"
        notu = f"EN {'PASS' if p_en else 'FAIL'} | {meta}"
        res.append((lid, pair, durum, notu))
        rows.append({"listing_id": lid, "pair": pair, "durum": durum, "not": notu,
                     "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {lid} {pair} {durum} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s "
            f"%{100 * n // len(todo)} | kota {api.remaining}")

    if a.apply and rows:
        birlesik = {k: dict(v) for k, v in done.items()}
        for r in rows:
            birlesik[r["listing_id"]] = r
        write_done(a.state, list(birlesik.values()))
    islenen = [r for r in res if r[2] in ("PASS", "HAZIR")]
    bad = [r for r in res if r[2] in ("FAIL", "ATLANDI", "SIRA DISI")]
    kalan = len(kalanlar) - len(res)
    md = [f"## POD kagit/eko maddeleri + lab cumlesi ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- POD ilan {len(pod)}; islenen {len(res)}; guncellenen {len(islenen)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; atlanan/sorunlu {len(bad)}; kalan {kalan}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    if ornek:
        md += [f"### Ornek diff ({ornek[0]}) — EN", "", "```diff", ornek[1], "```", "", "### RU", "", "```diff", ornek[2], "```", ""]
    md += ["| listing_id | cift | durum | not |", "|---|---|---|---|"]
    md += [f"| {l} | {p} | {s} | {d} |" for l, p, s, d in res]
    md += ["", f"- Kota once {q0} / sonra {api.remaining}"]
    text = "\n".join(md)
    log(text)
    (out / "PAPER_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "paper_result.json").write_text(json.dumps({"rows": res, "kalan": kalan, "quota": [q0, api.remaining]},
                                                      indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
