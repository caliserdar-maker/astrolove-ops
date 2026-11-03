#!/usr/bin/env python3
"""SALT OKUMA, Etsy istegi YOK (Merkez 4 Kas C): 78 poster son okuma ozet kontrolu.
Girdi: premium-tara HAM/<ilan>.json (canli EN + RU, API), kuru FARK.csv (onay_ozet), ONCE_SONRA.json (onayli "sonra"),
YEDEK.json (yazim oncesi baslik/etiket/malzeme, RU baslik/etiket).
Her ilan: ru_poster.onay_ozet(P.norm(canli EN), P.norm(canli RU)) == FARK onay_ozet (kuru ile ayni tanim);
canli norm == ONCE_SONRA sonra; baslik/etiket/malzeme/RU baslik/RU etiket == YEDEK; yasak ifade sayimi.
Cikti: --out SON_OZET_78.csv + OZET.json. Herhangi bir FAIL -> cikis 1."""
import argparse, csv, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import poster_metin_kuru as P  # noqa: E402
import ru_poster as R  # noqa: E402

YASAK = [("premium", re.compile(r"\bpremium\b", re.I)), ("long-lasting", re.compile(r"\blong[\s-]?lasting\b", re.I)),
         ("free preview", re.compile(r"\bfree\s+preview\b", re.I)), ("премиум", re.compile(r"преми(?:ал|ум)\w*", re.I)),
         ("стойк", re.compile(r"стойк\w*", re.I)), ("долговеч", re.compile(r"долговеч\w*", re.I)),
         ("бесплатн макет", re.compile(r"бесплатн\w*\s+макет", re.I))]


def kontrol(ids, ham, fark, os_, yedek):
    satir, fail = [], 0
    for lid in ids:
        h, y, k = ham.get(lid), yedek.get(lid) or {}, os_.get(lid) or {}
        if h is None:
            satir.append(dict(listing_id=lid, sonuc="FAIL", neden="HAM yok")); fail += 1; continue
        en, ru = P.norm(h.get("description")), P.norm((h.get("ru") or {}).get("description"))
        oz = R.onay_ozet(en, ru)
        yr, hr = y.get("ru") or {}, h.get("ru") or {}
        c = dict(listing_id=lid, cift=h.get("cift", ""), state=h.get("state"), canli_ozet=oz, fark_ozet=fark.get(lid, ""),
                 ozet_esit=oz == fark.get(lid),
                 sonra_esit=(en, ru) == (P.norm(k.get("en_sonra")), P.norm(k.get("ru_sonra"))),
                 baslik_ayni=h.get("title") == y.get("title"),
                 etiket_ayni=sorted(h.get("tags") or []) == sorted(y.get("tags") or []),
                 malzeme_ayni=sorted(h.get("materials") or []) == sorted(y.get("materials") or []),
                 ru_baslik_ayni=P.norm(hr.get("title")).strip() == P.norm(yr.get("title")).strip(),
                 ru_etiket_ayni=sorted(hr.get("tags") or []) == sorted(yr.get("tags") or []))
        c["yasak"] = ";".join(f"{a}:{len(rx.findall(en + chr(10) + ru))}" for a, rx in YASAK if rx.findall(en + "\n" + ru))
        ok = c["state"] == "active" and all(c[x] for x in ("ozet_esit", "sonra_esit", "baslik_ayni", "etiket_ayni",
                                                             "malzeme_ayni", "ru_baslik_ayni", "ru_etiket_ayni")) and not c["yasak"]
        c["sonuc"] = "PASS" if ok else "FAIL"
        fail += not ok
        satir.append(c)
    return satir, fail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True); ap.add_argument("--ham", required=True); ap.add_argument("--kuru", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ids = [r["listing_id"].strip() for r in csv.DictReader(open(a.ids, encoding="utf-8-sig"))]
    ham = {p.stem: json.loads(p.read_text()) for p in pathlib.Path(a.ham).glob("*.json")}
    kd = pathlib.Path(a.kuru)
    fark = {r["listing_id"]: r["onay_ozet"] for r in csv.DictReader(open(kd / "FARK.csv", encoding="utf-8"))}
    os_, yedek = json.loads((kd / "ONCE_SONRA.json").read_text()), json.loads((kd / "YEDEK.json").read_text())
    satir, fail = kontrol(ids, ham, fark, os_, yedek)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    alan = ["listing_id", "cift", "state", "sonuc", "canli_ozet", "fark_ozet", "ozet_esit", "sonra_esit", "baslik_ayni",
            "etiket_ayni", "malzeme_ayni", "ru_baslik_ayni", "ru_etiket_ayni", "yasak", "neden"]
    with open(out / "SON_OZET_78.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(satir)
    oz = dict(ilan=len(ids), pass_=len(ids) - fail, fail=fail, ham=len(ham))
    (out / "OZET.json").write_text(json.dumps(oz, indent=1))
    print(f"SON OZET: {oz}", flush=True)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
