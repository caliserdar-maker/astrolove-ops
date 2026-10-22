#!/usr/bin/env python3
"""YAYIN_DURUM.md (salt okuma): 78 POD ilani icin kapak / video / galeri / aciklama / hazirlik = OK | BEKLIYOR | FAIL.
Etsy: tek /listings/batch (includes Images,Videos) + readiness tanimi (2-3 cagri).
  kapak    : kapak-yukle SONUC.json kayitlarinda (TEMP/KAPAK78_YUKLE/*) ilanin son basarili yeni_id'si canli 1. sirada -> OK;
             son kayit FAIL -> FAIL; kayit yok -> BEKLIYOR
  video    : video-yukle SONUC.json (TEMP/VIDEO78_YUKLE/*) basarili kayit + canli video >= 1 -> OK; son kayit FAIL -> FAIL
  galeri   : galeri ilerleme kaydi (CL rapor.json + TEMP/GALERI_YAYIN/ILERLEME.json) PASS + canli 19 gorsel -> OK
  aciklama : canli aciklamada "within 7 business days" -> OK ("within 5" -> BEKLIYOR)
  hazirlik : ilan processing 4-7 -> OK
  envanter : envanter yazimi (Size sirasi + .99 fiyat) ilerleme kaydi YAZILDI/ZATEN -> OK (--envanter ILERLEME.json)
Cikti: onceki YAYIN_DURUM.md'nin gunluk ozet satirlari korunur + bugunun satiri + guncel tablo.
Kullanim: yayin_durum.py --kapak DIR --video DIR --galeri ILERLEME.json [--galeri ...] --onceki ESKI.md --out YENI.md
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy"))
BASARI = {"OK", "PASS", "ZATEN", "YAZILDI", "YUKLENDI", "TAMAM", "DONE"}
ENVANTER = {}
ALANLAR = ["kapak", "video", "galeri", "aciklama", "hazirlik", "envanter"]
SIZE_HEDEF = ["8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x30", "24x36", "A4", "A3", "A2"]


def boy_kodu(t):
    t = str(t or "").replace("×", "x").replace("X", "x")
    m = re.search(r"\b(A[2-4])\b", t) or re.search(r"(\d+)[\s\"'″]*x[\s\"'″]*(\d+)", t)
    return (m.group(1) if m.lastindex == 1 else f"{m.group(1)}x{m.group(2)}") if m else None


def kota_bolumu(yol, saat=36):
    """ETSY_KOTA.csv (saatlik ping) -> markdown: son olcumler, saatlik degisim, 24 saat sonra geri donecek harcama."""
    import email.utils
    if not yol or not Path(yol).exists():
        return []
    R = []
    for r in csv.DictReader(open(yol, encoding="utf-8")):
        try:
            t = email.utils.parsedate_to_datetime(r["utc"])
            R.append((t, int(r["x-remaining-today"]), r.get("x-limit-per-day") or ""))
        except (ValueError, TypeError, KeyError):
            continue
    R = R[-saat:]
    if not R:
        return []
    md = ["", f"## Etsy kota (limit {R[-1][2]}/gun, kayan 24 saat; saatlik olcum TEMP/ETSY_KOTA.csv)", "",
          f"- Son olcum {R[-1][0]:%Y-%m-%d %H:%M} UTC: kalan **{R[-1][1]}**", "",
          "| saat (UTC) | kalan | degisim | geri donus (+24 s) |", "|---|---|---|---|"]
    harcama = []
    for (t0, k0, _), (t1, k1, _) in zip([R[0]] + R[:-1], R):
        d = k1 - k0
        donus = (t1.replace(microsecond=0) + __import__("datetime").timedelta(hours=24))
        md.append(f"| {t1:%m-%d %H:%M} | {k1} | {d:+d} | {f'~{-d} cagri {donus:%m-%d %H:%M}' if d < -20 else ''} |")
        if d < -20:
            harcama.append((donus, -d))
    if harcama:
        md += ["", "- Beklenen buyuk donusler (net harcamanin 24 saat sonrasi, alt sinir): "
               + ", ".join(f"{t:%m-%d %H:%M} +{n}" for t, n in sorted(harcama)[:12])]
    return md


def kayitlar(dizin):
    """dizin altindaki tum SONUC.json: {lid: [(ts, kayit)]} (dosya mtime sirasina gore)."""
    K = {}
    for p in sorted(Path(dizin).rglob("SONUC.json"), key=lambda p: p.stat().st_mtime) if dizin and Path(dizin).exists() else []:
        try:
            veri = json.loads(p.read_text())
        except ValueError:
            continue
        for x in veri if isinstance(veri, list) else (veri.get("ilanlar") or veri.get("sonuc") or []):
            if isinstance(x, dict) and x.get("listing_id"):
                K.setdefault(str(x["listing_id"]), []).append(x)
    return K


def son_durum(liste):
    """-> ('OK', kayit) | ('FAIL', kayit) | ('BEKLIYOR', None). Basarili kayit varsa o esastir."""
    if not liste:
        return "BEKLIYOR", None
    iyi = [x for x in liste if str(x.get("sonuc") or x.get("durum") or "").upper() in BASARI]
    if iyi:
        return "OK", iyi[-1]
    return ("FAIL" if str(liste[-1].get("sonuc") or liste[-1].get("durum") or "").upper() in ("FAIL", "HATA") else "BEKLIYOR"), liste[-1]


def galeri_kaydi(yollar):
    G = {}
    for y in yollar:
        if not y or not Path(y).exists():
            continue
        d = json.loads(Path(y).read_text())
        if "ilanlar" in d:
            for lid, v in d["ilanlar"].items():
                G[str(lid)] = str(v.get("durum") or v.get("sonuc") or "").upper()
        elif d.get("listing_id") or d.get("sonuc"):
            G[str(d.get("listing_id") or "4570143815")] = str(d.get("sonuc")).upper()
    return G


def durumlar(L, kapak, video, galeri):
    lid = str(L.get("listing_id"))
    imgs = sorted(L.get("images") or [], key=lambda x: x.get("rank") or 99)
    d = {}
    s, k = son_durum(kapak.get(lid))
    if s == "OK" and k and k.get("yeni_id") and imgs and imgs[0].get("listing_image_id") != k.get("yeni_id"):
        s = "OK" if galeri.get(lid) in BASARI else "FAIL"      # galeri degistiyse kapak galeriyle yenilendi
    d["kapak"] = s
    s, _ = son_durum(video.get(lid))
    d["video"] = "OK" if s == "OK" and (L.get("videos") or []) else ("BEKLIYOR" if s == "OK" else s)
    g = galeri.get(lid, "")
    d["galeri"] = "OK" if g in BASARI and len(imgs) == 19 else ("FAIL" if g in ("FAIL", "HATA") else "BEKLIYOR")
    t = html.unescape(L.get("description") or "")
    d["aciklama"] = "OK" if "within 7 business days" in t else ("BEKLIYOR" if "within 5 business days" in t else "FAIL")
    d["hazirlik"] = "OK" if (L.get("processing_min"), L.get("processing_max")) == (4, 7) else "BEKLIYOR"
    z = str((ENVANTER.get(lid) or {}).get("durum") or "").upper()
    d["envanter"] = "OK" if z in BASARI else ("FAIL" if z == "FAIL" else "BEKLIYOR")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kapak", default=""); ap.add_argument("--video", default="")
    ap.add_argument("--galeri", action="append", default=[]); ap.add_argument("--onceki", default="")
    ap.add_argument("--envanter", default="")
    ap.add_argument("--kota", default="")
    ap.add_argument("--out", required=True); ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    a = ap.parse_args()
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    rows = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    L = {}
    ids = [r["listing_id"] for r in rows]
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "Images,Videos"}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    if a.envanter and Path(a.envanter).exists():
        ENVANTER.update(json.loads(Path(a.envanter).read_text()).get("ilanlar") or {})
    kapak, video, galeri = kayitlar(a.kapak), kayitlar(a.video), galeri_kaydi(a.galeri)
    tablo, say = [], {f: {} for f in ALANLAR}
    for r in rows:
        d = durumlar(L.get(r["listing_id"]) or {"listing_id": r["listing_id"]}, kapak, video, galeri)
        for f in ALANLAR:
            say[f][d[f]] = say[f].get(d[f], 0) + 1
        tablo.append(f"| {r['listing_id']} | {r['cift']} | " + " | ".join(d[f] for f in ALANLAR) + " |")
    gun = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    ozet = f"- {gun}: " + " | ".join(f"{f} OK {say[f].get('OK', 0)}/78" + (f" FAIL {say[f]['FAIL']}" if say[f].get("FAIL") else "")
                                     for f in ALANLAR)
    eski = []
    if a.onceki and Path(a.onceki).exists():
        t = Path(a.onceki).read_text().split("\n## Guncel durum")[0]
        eski = [x for x in t.splitlines() if x.startswith("- 20")]
    md = ["# YAYIN DURUMU (78 POD) - gunluk ozet", "", *eski, ozet, "", f"## Guncel durum ({gun})", "",
          "| listing_id | cift | " + " | ".join(ALANLAR) + " |", "|---|---|" + "---|" * len(ALANLAR), *tablo,
          *kota_bolumu(a.kota)]
    Path(a.out).write_text("\n".join(md) + "\n")
    print(ozet, f"| kota {api.remaining} | cagri {api.calls}", flush=True)


if __name__ == "__main__":
    main()
