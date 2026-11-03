#!/usr/bin/env python3
"""Bekleyen (yayinlanmamis) Metricool gonderilerinde yasak / baglam ifade sayimi (Serdar 3 Kas cevap 3; Metricool'a YAZMA YOK,
API cagrisi YOK: donem_olcum kosusunun HAM/scheduler_posts.json dokumu okunur). Desen tek kaynak: etsy_common.METIN_KESIN +
METIN_BAGLAM (+ YD izinleri METIN_IZIN: yd78 ilanina baglanan gonderide "free preview" ayrica sayilir, izinli sutununda).
Bekleyen = provider status PENDING ve yayin > --okuma (Istanbul). Taranan alanlar: text, firstCommentText, mediaAltText, pinterestData.pinTitle,
youtubeData.title, tiktokData.title ve diger tum metin alanlari (URL disi).
Kullanim: bekleyen_metin_tara.py scheduler_posts.json CIKTI_DIR --okuma 2026-11-03T23:26"""
import argparse, csv, json, os, re, sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "etsy"))
import etsy_common as E  # noqa: E402

IST = ZoneInfo("Europe/Istanbul")
URL = re.compile(r"^https?://")
LID = re.compile(r"etsy\.com/listing/(\d+)")


def metinler(g, yol=""):
    if isinstance(g, dict):
        return [x for k, v in g.items() for x in metinler(v, f"{yol}.{k}" if yol else k)]
    if isinstance(g, list):
        return [x for i, v in enumerate(g) for x in metinler(v, yol)]
    if isinstance(g, str) and g.strip() and not URL.match(g.strip()) and yol not in ("media", "uuid", "creatorUserMail"):
        return [(yol, g)]
    return []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dok"); ap.add_argument("cikti"); ap.add_argument("--okuma", required=True)
    a = ap.parse_args(); os.makedirs(a.cikti, exist_ok=True)
    okuma = datetime.fromisoformat(a.okuma).replace(tzinfo=IST)
    ps = json.load(open(a.dok, encoding="utf-8"))
    satir, say, gon = [], Counter(), Counter()
    for p in ps:
        pd = p.get("publicationDate") or {}
        try:
            z = datetime.fromisoformat(str(pd.get("dateTime"))[:19]).replace(tzinfo=ZoneInfo(pd.get("timezone") or "Europe/Istanbul"))
        except ValueError:
            continue
        aglar = [(pr.get("network") or "").lower() for pr in p.get("providers") or [] if pr.get("status") == "PENDING"]
        if z <= okuma or not aglar:
            continue
        link = json.dumps(p.get("pinterestData") or {}) + " " + (p.get("text") or "")
        m = LID.search(link)
        grup = E.ilan_grubu(m.group(1)) if m else ""
        for ag in aglar:
            gon[ag] += 1
        bul = Counter()
        for yol, t in metinler({k: v for k, v in p.items() if k not in ("providers", "publicationDate", "creationDate")}):
            for ad, sinif, rx in E._METIN_RX:
                for mm in rx.finditer(t):
                    izin = sinif == "BAGLAM" and ad.startswith("free preview") and grup == "yd78"
                    bul[(sinif, ad.split(" (")[0], "izinli (YD)" if izin else "")] += 1
        for (sinif, ad, izin), n in bul.items():
            for ag in aglar:
                say[(ag, sinif, ad, izin)] += 1   # gonderi sayisi (ifade gecen gonderi)
                satir.append(dict(yayin=f"{z.astimezone(IST):%Y-%m-%d %H:%M}", ag=ag, gonderi_id=p.get("id"), grup=grup or "diger",
                                  sinif=sinif, ifade=ad, adet=n, izin=izin))
    with open(os.path.join(a.cikti, "BEKLEYEN_METIN.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["yayin", "ag", "gonderi_id", "grup", "sinif", "ifade", "adet", "izin"], lineterminator="\n")
        w.writeheader(); w.writerows(sorted(satir, key=lambda r: (r["ag"], r["yayin"])))
    with open(os.path.join(a.cikti, "BEKLEYEN_METIN_OZET.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["ag", "bekleyen_gonderi", "sinif", "ifade", "izin", "ifade_gecen_gonderi"])
        for ag in sorted(gon):
            r = [(k, n) for k, n in say.items() if k[0] == ag]
            if not r:
                w.writerow([ag, gon[ag], "", "yok", "", 0])
            for (ag_, s, ad, iz), n in sorted(r):
                w.writerow([ag, gon[ag], s, ad, iz, n])
    print(f"bekleyen gonderi (ag): {dict(gon)}; ifade: {dict(say)}")


if __name__ == "__main__":
    main()
