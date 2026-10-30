#!/usr/bin/env python3
"""galeri_karsilastir sentetik testi (ag yok, Etsy yok, Drive yok). Senaryolar: ayni / gorsel degisti (kapak) / ilan eksik /
renk bagi degisti / video degisti / alt_text degisti / state degisti / yalniz last_modified_timestamp + URL degisti = AYNI /
bos ONCE = FAIL / bozuk SONRA = EKSIK / workflow sozlesmesi (Etsy token ve kilit yok, girdi kapisi, --immutable)."""
import copy
import csv
import json
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "kapak78")); sys.path.insert(0, str(KOK / "scripts" / "etsy"))
import galeri_karsilastir as G  # noqa: E402
import kilit_bekle  # noqa: E402

SONUC = []
RENK = ("Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment")
SIRA = (1, 6, 7, 8, 9)


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def galeri(lid, cift, t=1000):
    g = [dict(rank=r, listing_image_id=int(lid) * 10 + r, alt_text=f"alt {r}", url_fullxfull=f"https://i.example/{lid}/{r}?t={t}",
              full_width=2000, full_height=2500) for r in range(1, 10)]
    b = [dict(property_id=200, value_id=500 + i, value=v, image_id=int(lid) * 10 + s) for i, (v, s) in enumerate(zip(RENK, SIRA))]
    v = [dict(video_id=int(lid) + 7, video_url=f"https://v.example/{lid}?t={t}", thumbnail_url=f"https://v.example/{lid}.jpg?t={t}",
              width=1080, height=1350, video_state="active")]
    return dict(listing_id=str(lid), cift=cift, ilan=dict(state="active", title=f"{cift} poster", last_modified_timestamp=t),
                gorseller=g, baglar=b, videolar=v)


def yaz(kok, veri):
    for y in veri:
        d = Path(kok) / f"{y['listing_id']}_{y['cift']}"; d.mkdir(parents=True, exist_ok=True)
        (d / "GALERI.json").write_text(json.dumps(y, ensure_ascii=False, indent=1), encoding="utf-8")


def kos(tmp, ad, once, sonra):
    o, s, out = Path(tmp) / ad / "o", Path(tmp) / ad / "s", Path(tmp) / ad / "out"
    o.mkdir(parents=True); s.mkdir(parents=True)
    yaz(o, once); yaz(s, sonra)
    rc = G.calistir(str(o), str(s), str(out))
    rows = list(csv.DictReader(open(out / "KARSILASTIR.csv", encoding="utf-8"))) if (out / "KARSILASTIR.csv").exists() else []
    return rc, {r["listing_id"]: r for r in rows}, (out / "OZET.md").read_text(encoding="utf-8") if (out / "OZET.md").exists() else ""


def main():
    ilan = [("4570110121", "AQUARIUS_AQUARIUS"), ("4570110641", "AQUARIUS_ARIES"), ("4570111111", "ARIES_ARIES")]
    once = [galeri(l, c) for l, c in ilan]
    with tempfile.TemporaryDirectory() as tmp:
        rc, r, oz = kos(tmp, "ayni", once, copy.deepcopy(once))
        kontrol("ayni: rc 0, 3 AYNI, OZET PASS", rc == 0 and [x["durum"] for x in r.values()] == ["AYNI"] * 3 and "SONUC: PASS" in oz)

        s = copy.deepcopy(once)
        for y in s:   # yalniz zaman damgasi + URL'ler degisir
            y["ilan"]["last_modified_timestamp"] = 2000
            for g in y["gorseller"]:
                g["url_fullxfull"] += "&yeni=1"
            for v in y["videolar"]:
                v["video_url"] += "&yeni=1"; v["thumbnail_url"] += "&yeni=1"
        rc, r, _ = kos(tmp, "damga", once, s)
        kontrol("yalniz last_modified_timestamp + URL degisti: AYNI, rc 0", rc == 0 and all(x["durum"] == "AYNI" for x in r.values()))

        s = copy.deepcopy(once); s[0]["gorseller"][0]["listing_image_id"] = 999
        rc, r, oz = kos(tmp, "gorsel", once, s)
        kontrol("kapak gorseli degisti: FARKLI, rank 1 (kapak) farkta, rc 1",
                rc == 1 and r["4570110121"]["durum"] == "FARKLI" and "rank 1 (kapak) 45701101211->999" in r["4570110121"]["fark"]
                and r["4570110641"]["durum"] == "AYNI" and "SONUC: FAIL" in oz and "gorsel 1" in oz)

        s = copy.deepcopy(once); s[1]["gorseller"].pop()
        rc, r, _ = kos(tmp, "sayi", once, s)
        kontrol("gorsel sayisi 9->8: FARKLI", rc == 1 and "gorsel sayisi 9->8" in r["4570110641"]["fark"])

        s = copy.deepcopy(once); s[1]["gorseller"][0], s[1]["gorseller"][1] = s[1]["gorseller"][1], s[1]["gorseller"][0]
        s[1]["gorseller"][0]["rank"], s[1]["gorseller"][1]["rank"] = 1, 2
        rc, r, _ = kos(tmp, "sira", once, s)
        kontrol("rank 1/2 yer degisti: FARKLI", rc == 1 and r["4570110641"]["durum"] == "FARKLI" and "rank 2" in r["4570110641"]["fark"])

        rc, r, oz = kos(tmp, "eksik", once, copy.deepcopy(once[:2]))
        kontrol("SONRA'da ilan eksik: EKSIK, rc 1", rc == 1 and r["4570111111"]["durum"] == "EKSIK" and "| EKSIK | 1 |" in oz)

        s = copy.deepcopy(once); s[2]["baglar"][1]["image_id"] = s[2]["gorseller"][1]["listing_image_id"]
        rc, r, _ = kos(tmp, "bag", once, s)
        kontrol("renk bagi degisti (Deep Black image_id): FARKLI", rc == 1 and r["4570111111"]["durum"] == "FARKLI"
                and r["4570111111"]["fark"].startswith("bag -200:Deep Black:45701111116 +200:Deep Black:45701111112"))

        s = copy.deepcopy(once); s[2]["baglar"][0]["value_id"] = 1   # value_id karsilastirma disi
        rc, r, _ = kos(tmp, "valueid", once, s)
        kontrol("yalniz value_id degisti: AYNI (property_id, value, image_id karsilastirilir)", rc == 0)

        s = copy.deepcopy(once); s[0]["videolar"][0]["video_id"] = 1
        rc, r, _ = kos(tmp, "video", once, s)
        kontrol("video degisti: FARKLI", rc == 1 and r["4570110121"]["fark"] == "video 4570110128->1")

        s = copy.deepcopy(once); s[0]["videolar"] = []
        rc, r, _ = kos(tmp, "video0", once, s)
        kontrol("video silindi: FARKLI", rc == 1 and r["4570110121"]["fark"] == "video 4570110128->yok")

        s = copy.deepcopy(once); s[0]["gorseller"][4]["alt_text"] = "yeni"
        rc, r, _ = kos(tmp, "alt", once, s)
        kontrol("alt_text degisti: FARKLI", rc == 1 and r["4570110121"]["fark"] == "alt_text rank 5")

        s = copy.deepcopy(once); s[0]["ilan"]["state"] = "draft"; s[1]["ilan"]["title"] = "baska"
        rc, r, _ = kos(tmp, "state", once, s)
        kontrol("state / title degisti: FARKLI", rc == 1 and r["4570110121"]["fark"] == "state 'active'->'draft'"
                and r["4570110641"]["fark"].startswith("title "))

        rc, r, oz = kos(tmp, "fazla", once[:2], copy.deepcopy(once))
        kontrol("yalniz SONRA'da ilan: rc 0, OZET'te sayilir", rc == 0 and len(r) == 2 and "| yalniz SONRA'da | 1 |" in oz)

        rc, r, oz = kos(tmp, "bos", [], copy.deepcopy(once))
        kontrol("bos ONCE: rc 1 (bos PASS yok)", rc == 1 and "SONUC: FAIL" in oz)

        o, s_, out = Path(tmp) / "bozuk" / "o", Path(tmp) / "bozuk" / "s", Path(tmp) / "bozuk" / "out"
        yaz(o, once); yaz(s_, once)
        (s_ / "4570110121_AQUARIUS_AQUARIUS" / "GALERI.json").write_text("{bozuk", encoding="utf-8")
        rc = G.calistir(str(o), str(s_), str(out))
        rr = {x["listing_id"]: x for x in csv.DictReader(open(out / "KARSILASTIR.csv", encoding="utf-8"))}
        kontrol("bozuk SONRA JSON: EKSIK, rc 1", rc == 1 and rr["4570110121"]["durum"] == "EKSIK")
        (o / "4570110121_AQUARIUS_AQUARIUS" / "GALERI.json").write_text("{bozuk", encoding="utf-8")
        kontrol("bozuk ONCE JSON: rc 2", G.calistir(str(o), str(s_), str(Path(tmp) / "bozuk" / "out2")) == 2)

    wf = (KOK / ".github/workflows/galeri-karsilastir.yml").read_text(encoding="utf-8")
    kontrol("workflow: Etsy token / kilit / Etsy sirri yok", "ETSY_TOKEN" not in wf and "kilit_bekle" not in wf and "ETSY_API_KEY" not in wf
            and ".github/workflows/galeri-karsilastir.yml" not in kilit_bekle.kilit_kumesi(str(KOK)))
    kontrol("workflow: girdiler + damga kapisi + --immutable + notice",
            "once_damga:" in wf and "sonra_damga:" in wf and wf.count("^[0-9]{8}_[0-9]{6}$") == 2 and "--immutable" in wf
            and "TEMP/GALERI_KARSILASTIR/${S}_${GITHUB_RUN_ID}" in wf and "::notice" in wf and '--include "*/GALERI.json"' in wf)

    gec = sum(ok for _, ok in SONUC)
    print(f"{'PASS' if gec == len(SONUC) else 'FAIL'}: {gec}/{len(SONUC)}")
    return 0 if gec == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
