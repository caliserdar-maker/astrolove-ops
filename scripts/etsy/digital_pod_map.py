#!/usr/bin/env python3
"""
DIJITAL -> POD ESLEME + RENK CUMLESI CIKARIMI - SALT OKUR (Mo 14 Eyl 2026).
Etsy'ye hicbir yazma yok; yalniz GET /listings/{id}.

1) Her dijital ilan icin capraz satis linkindeki POD ilan no'su ("PREFER IT READY
   TO HANG?" blogundaki etsy.com/listing/<id>) ile POD_LISTINGS_STATE.csv'deki
   cift -> POD esleme karsilastirilir. Celiski varsa HAKEM: baglanti verilen POD
   ilaninin KENDI BASLIGI okunur; basliktaki iki burc hangi kaynagi dogruluyorsa
   o kaynak dogru sayilir (baslik = Etsy'deki gercek durum).
2) Her ilanin "THE ARTWORK" blogundaki renk tarifi cumlesi ("This is the <Edition>
   edition, ...") oldugu gibi cikarilir; edisyon basina farkli varyantlar sayilir.

Kullanim:
  digital_pod_map.py --dfile-state D.csv --pod-state P.csv --out OUT [--limit N]
      [--quota-min 200]
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
LINK_RX = re.compile(r"etsy\.com/listing/(\d+)")
BASLIK_RX = re.compile(r"PREFER IT READY TO HANG", re.I)
SUTUN = ["digital_id", "pair", "edisyon", "baslik", "pod_state", "pod_link", "link_url",
         "eslesme", "hakem", "renk_cumlesi", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def oku_csv(path, kosul=None):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if kosul is None or kosul(r)]


def burc_seti(metin):
    """Metindeki burc adlari (buyuk/kucuk duyarsiz) -> Counter."""
    c = Counter()
    for b in BURCLAR:
        c[b] = len(re.findall(rf"\b{b}\b", metin, re.I))
    return Counter({k: v for k, v in c.items() if v})


def cift_seti(pair):
    a, b = pair.split("_", 1)
    return Counter([a.capitalize(), b.capitalize()])


def link_bul(desc):
    """'PREFER IT READY TO HANG' bloguna EN YAKIN etsy listing linki -> (id, url)."""
    m = BASLIK_RX.search(desc)
    aday = LINK_RX.search(desc, m.end()) if m else LINK_RX.search(desc)
    if not aday:
        return None, None
    url = re.search(r"https?://[^\s<]+", desc[max(0, aday.start() - 60):aday.end() + 120])
    return aday.group(1), (url.group(0).rstrip(".,") if url else f"etsy.com/listing/{aday.group(1)}")


def renk_cumlesi(desc, edisyon):
    """'This is the <Edition> edition, ...' cumlesi; bulunamazsa edisyon adi ve
    'background' gecen ilk cumle. Cumle sinirlari: nokta + bosluk/satir sonu."""
    duz = html.unescape(desc).replace("\r\n", "\n")
    # once satirlara (basliklar kendi satirinda), sonra cumlelere bol
    cumleler = [c.strip() for satir in duz.split("\n")
                for c in re.split(r"(?<=\.)\s+", satir) if c.strip()]
    for c in cumleler:
        if re.search(rf"This is the\s+{re.escape(edisyon)}\s+edition\b", c, re.I):
            return c.strip(), "capa"
    for c in cumleler:
        if re.search(r"\bIt features\b.*\bbackground\b", c, re.I):
            return c.strip(), "features"
    for c in cumleler:
        if re.search(r"\bbackground\b.*\bartwork\b", c, re.I) or \
           re.search(r"\bbackground with\b", c, re.I):
            return c.strip(), "background"
    for c in cumleler:
        if re.search(r"This is the\s+\w[\w ]*?\s+edition\b", c, re.I):
            return c.strip(), "capa_farkli_edisyon"
    for c in cumleler:
        if re.search(re.escape(edisyon), c, re.I) and re.search(r"background", c, re.I):
            return c.strip(), "yedek"
    return "", "bulunamadi"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dfile-state", required=True)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=200)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    dij = [r for r in oku_csv(a.dfile_state) if (r.get("listing_id") or "").isdigit()]
    gorulen, sirali = set(), []
    for r in dij:
        if r["listing_id"] not in gorulen:
            gorulen.add(r["listing_id"])
            sirali.append(r)
    dij = sirali[:a.limit] if a.limit else sirali
    pod = {r["pair"]: r["listing_id"] for r in oku_csv(a.pod_state)
           if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit()}
    log(f"dijital ilan {len(dij)} | POD state {len(pod)} cift | kota {api.remaining}")

    satirlar, t0, durdu = [], time.time(), None
    for i, r in enumerate(dij, 1):
        rem = api.remaining
        if rem is not None and str(rem).isdigit() and int(rem) < a.quota_min:
            durdu = f"kota {rem} < {a.quota_min}, {i-1}/{len(dij)} ilanda durdu"
            log(f"DUR: {durdu}")
            break
        lid, pair, ed = r["listing_id"], r.get("pair", ""), r.get("edisyon", "")
        L = api.get(f"/listings/{lid}", ok404=True) or {}
        desc = L.get("description") or ""
        baslik = L.get("title") or ""
        link_id, url = link_bul(desc)
        cumle, kaynak = renk_cumlesi(desc, ed)
        state_id = pod.get(pair, "")
        if not desc:
            eslesme = "ILAN_OKUNAMADI"
        elif not link_id:
            eslesme = "LINK_YOK"
        elif not state_id:
            eslesme = "STATE_YOK"
        elif link_id == state_id:
            eslesme = "AYNI"
        else:
            eslesme = "CELISKI"
        satirlar.append({"digital_id": lid, "pair": pair, "edisyon": ed, "baslik": baslik,
                         "pod_state": state_id, "pod_link": link_id or "", "link_url": url or "",
                         "eslesme": eslesme, "hakem": "", "renk_cumlesi": cumle,
                         "not": kaynak if kaynak != "capa" else ""})
        if i % 25 == 0 or i == len(dij):
            gecen = (time.time() - t0) / 60
            log(f"  [{i}/{len(dij)} %{round(100*i/len(dij))}] gecen {gecen:.1f} dk, "
                f"kalan ~{gecen/i*(len(dij)-i):.1f} dk | kota {api.remaining}")

    # HAKEM: celiskili satirlarda baglanti verilen POD ilaninin kendi basligi okunur
    celiski = [x for x in satirlar if x["eslesme"] == "CELISKI"]
    pod_baslik = {}
    for x in celiski:
        for pid in (x["pod_link"], x["pod_state"]):
            if pid and pid not in pod_baslik:
                P = api.get(f"/listings/{pid}", ok404=True) or {}
                pod_baslik[pid] = P.get("title") or ""
    for x in celiski:
        bekl = cift_seti(x["pair"])
        skor = {}
        for etiket, pid in (("link", x["pod_link"]), ("state", x["pod_state"])):
            b = burc_seti(pod_baslik.get(pid, ""))
            skor[etiket] = (b and all(b.get(s, 0) >= n for s, n in bekl.items()))
        if skor.get("link") and not skor.get("state"):
            x["hakem"] = "link dogru"
        elif skor.get("state") and not skor.get("link"):
            x["hakem"] = "state dogru"
        elif skor.get("link") and skor.get("state"):
            x["hakem"] = "ikisi de cifte uyuyor"
        else:
            x["hakem"] = "ikisi de uymuyor"
        x["not"] = (x["not"] + f" | link_baslik={pod_baslik.get(x['pod_link'],'')[:60]} "
                    f"| state_baslik={pod_baslik.get(x['pod_state'],'')[:60]}").strip(" |")

    # renk cumlesi ozeti
    renk = defaultdict(Counter)
    ornek = defaultdict(dict)
    for x in satirlar:
        renk[x["edisyon"]][x["renk_cumlesi"]] += 1
        ornek[x["edisyon"]].setdefault(x["renk_cumlesi"], x["digital_id"])

    with open(out / "DIGITAL_POD_MAP.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)
    with open(out / "EDITION_COLOR_SENTENCES.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["edisyon", "ilan_sayisi", "cumle", "ornek_ilan"])
        for ed in EDISYONLAR + [e for e in renk if e not in EDISYONLAR]:
            for cumle, n in renk.get(ed, Counter()).most_common():
                w.writerow([ed, n, cumle, ornek[ed][cumle]])

    say = Counter(x["eslesme"] for x in satirlar)
    log(f"ESLESME: {dict(say)}")
    for ed in EDISYONLAR:
        varyant = renk.get(ed, Counter())
        log(f"RENK {ed}: {len(varyant)} varyant / {sum(varyant.values())} ilan")
        for cumle, n in varyant.most_common():
            log(f"    ({n}) {cumle[:200]}")
    for x in satirlar:
        if x["eslesme"] != "AYNI":
            log(f"  {x['eslesme']}: {x['digital_id']} {x['pair']} {x['edisyon']} | "
                f"state={x['pod_state']} link={x['pod_link']} | {x['hakem']}")
    rapor = {
        "ts_utc": simdi(), "dijital_ilan": len(satirlar), "eslesme": dict(say),
        "durdu": durdu, "kota": api.remaining, "api_cagrisi": api.calls,
        "renk_varyant": {ed: [{"cumle": c, "ilan": n, "ornek": ornek[ed][c]}
                              for c, n in renk.get(ed, Counter()).most_common()]
                         for ed in EDISYONLAR},
        "celiskiler": [{k: x[k] for k in ("digital_id", "pair", "edisyon", "pod_state",
                                          "pod_link", "hakem", "not")} for x in celiski],
    }
    (out / "DIGITAL_POD_MAP.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    log(f"OZET: {json.dumps({'ilan': len(satirlar), 'eslesme': dict(say), 'kota': api.remaining, 'cagri': api.calls}, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
