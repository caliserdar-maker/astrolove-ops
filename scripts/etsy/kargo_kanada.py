#!/usr/bin/env python3
"""78 POD ilaninin bagli kargo profil(ler)inden KANADA hedefini cikarir (Serdar karari 30 Eyl). Diger hedefler degismez.
  --mod kuru : SALT OKUMA. 78 ilanin shipping_profile_id'leri (batch) -> profil basina hedefler; CA hedefi var mi;
               profilde "everywhere else" hedefi varsa CA silinince Kanada o hedefe duser (Kanada kapanmaz) -> BLOK.
               Profili kullanan POD disi ilan sayisi (magaza ilanlari taranir; dijital ilanlarda profil yok).
  --mod yaz  : ETSY'YE YAZAR (--confirm KANADA). Profil basina: tam profil YEDEK (yerel + --yedek-drive, dogrulanir) ->
               yalniz CA hedefi DELETE -> geri okuma: CA yok, diger hedefler (ulke/bolge, ucret, gun) birebir ayni.
               Ilk FAIL'de DUR. Ilan, dijital ilan ve diger profil alanlarina dokunulmaz.
  --confirm KANADA_VE_DIGER (Serdar onayi 30 Eyl): CA ile birlikte "everywhere else" hedefi de silinir (BLOK kalkar);
               kalan hedefler (US, GB, eu, AU...) birebir ayni kalmali, US hedefi zorunlu.
Kullanim: kargo_kanada.py --mod kuru|yaz --out OUT [--confirm KANADA|KANADA_VE_DIGER] [--yedek-drive gdrive:...]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy"))
BEKLE, TEKRAR = 4, 5


def log(m):
    print(m, flush=True)


def hedef_imza(x):
    return (x.get("destination_country_iso") or "", x.get("destination_region") or "", str(x.get("primary_cost")),
            str(x.get("secondary_cost")), x.get("min_delivery_days"), x.get("max_delivery_days"), x.get("shipping_carrier_id"),
            x.get("mail_class"))


def hedefler(P):
    return P.get("shipping_profile_destinations") or []


def everywhere(P):
    return [x for x in hedefler(P) if not x.get("destination_country_iso") and (x.get("destination_region") or "none") == "none"]


def ca(P):
    return [x for x in hedefler(P) if (x.get("destination_country_iso") or "").upper() == "CA"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["kuru", "yaz"]); ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--yedek-drive", default="")
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    ew_sil = a.confirm == "KANADA_VE_DIGER"
    if yaz and a.confirm not in ("KANADA", "KANADA_VE_DIGER"):
        raise SystemExit("HATA: --mod yaz icin --confirm KANADA veya KANADA_VE_DIGER gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ids = [r["listing_id"] for r in csv.DictReader(open(a.ids, encoding="utf-8"))]
    if len(ids) != 78:
        raise SystemExit(f"HATA: 78 ilan bekleniyordu ({len(ids)}). DUR.")
    L = {}
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    pids = {}
    for lid in ids:
        pids.setdefault(str((L.get(lid) or {}).get("shipping_profile_id")), []).append(lid)
    # profili kullanan diger ilanlar (POD disi)
    diger = {p: 0 for p in pids}
    for state in ("active", "inactive", "draft", "expired", "sold_out"):
        off = 0
        while True:
            d = api.get(f"/shops/{shop}/listings", params={"state": state, "limit": 100, "offset": off}) or {}
            R = d.get("results") or []
            for x in R:
                p = str(x.get("shipping_profile_id"))
                if p in diger and str(x["listing_id"]) not in ids:
                    diger[p] += 1
            off += len(R)
            if len(R) < 100:
                break
    md = [f"# KARGO PROFILI: KANADA CIKARMA ({a.mod}) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", ""]
    sonuc, blok = {}, []
    for pid, lids in pids.items():
        if pid in ("None", ""):
            blok.append(f"{len(lids)} ilanda kargo profili yok: {lids[:5]}"); continue
        P0 = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
        c, e = ca(P0), everywhere(P0)
        md.append(f"- Profil {pid} '{P0.get('title')}': {len(lids)} POD ilan, POD disi {diger[pid]} ilan | hedefler: "
                  + ", ".join(sorted((x.get('destination_country_iso') or x.get('destination_region') or 'none') for x in hedefler(P0)))
                  + f" | CA hedefi {len(c)} | everywhere-else {len(e)}")
        if e and not ew_sil:
            blok.append(f"profil {pid}: 'everywhere else' hedefi var; CA silinirse Kanada o hedefe duser (kapanmaz)")
        if not c and not (e and ew_sil):
            sonuc[pid] = "ZATEN (CA hedefi yok)" if not e else "BLOK"
            continue
        sonuc[pid] = "PLAN" + (" (CA + everywhere else silinecek)" if ew_sil else "")
    # yazma: ONCE tum profiller kontrol edildi; BLOK varsa hicbir profile yazilmaz
    for pid in [p for p, v in sonuc.items() if v.startswith("PLAN")] if (yaz and not blok) else []:
        P0 = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
        c = ca(P0) + (everywhere(P0) if ew_sil else [])
        if (everywhere(P0) and not ew_sil) or not c:
            sonuc[pid] = "FAIL canli profil kontrolden sonra degisti"; break
        kalan0 = [x for x in hedefler(P0) if x not in c]
        if not any((x.get("destination_country_iso") or "").upper() == "US" for x in kalan0):
            sonuc[pid] = "FAIL silme sonrasi US hedefi kalmiyor"; break
        # yedek
        yd = out / "YEDEK"; yd.mkdir(parents=True, exist_ok=True)
        f = yd / f"profil_{pid}.json"
        f.write_text(json.dumps(P0, ensure_ascii=False, indent=1))
        if a.yedek_drive:
            r = subprocess.run(["rclone", "copyto", str(f), f"{a.yedek_drive}/{f.name}"], capture_output=True, text=True)
            chk = subprocess.run(["rclone", "size", "--json", f"{a.yedek_drive}/{f.name}"], capture_output=True, text=True)
            if r.returncode or chk.returncode or json.loads(chk.stdout or "{}").get("bytes") != f.stat().st_size:
                raise SystemExit(f"HATA: profil {pid} yedegi Drive'da dogrulanamadi. YAZMA YOK. DUR.")
        digerleri0 = sorted(hedef_imza(x) for x in hedefler(P0) if x not in c)
        for x in c:
            api.delete(f"/shops/{shop}/shipping-profiles/{pid}/destinations/{x['shipping_profile_destination_id']}")
        P1 = None
        for _ in range(TEKRAR):
            time.sleep(BEKLE)
            P1 = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
            if not ca(P1) and not (ew_sil and everywhere(P1)):
                break
        sorun = []
        if ca(P1):
            sorun.append("CA hedefi hala var")
        if ew_sil and everywhere(P1):
            sorun.append("everywhere else hedefi hala var")
        if sorted(hedef_imza(x) for x in hedefler(P1)) != digerleri0:
            sorun.append("diger hedefler degisti")
        for alan in ("title", "origin_country_iso", "origin_postal_code", "min_processing_days", "max_processing_days"):
            if P1.get(alan) != P0.get(alan):
                sorun.append(f"degisti:{alan}")
        (out / f"SONRA_profil_{pid}.json").write_text(json.dumps(P1, ensure_ascii=False, indent=1))
        if sorun:
            sonuc[pid] = f"FAIL {sorun}"
            md.append(f"- Profil {pid}: FAIL {sorun}")
            break
        sonuc[pid] = "YAZILDI (CA" + (" + everywhere else" if ew_sil else "") + " silindi, diger hedefler birebir ayni)"
    md += ["", f"- Sonuc: {sonuc}", f"- BLOK: {blok or 'yok'}", f"- Etsy cagrisi {api.calls} | kota son {api.remaining}"]
    (out / "RAPOR.md").write_text("\n".join(md) + "\n")
    log("\n".join(md))
    if blok or any(str(v).startswith("FAIL") for v in sonuc.values()):
        raise SystemExit("DUR: BLOK/FAIL (RAPOR.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
