#!/usr/bin/env python3
"""Poster video v7b: 78 PASS videoyu tek klasorde birlestirir (Merkez 26 Eki; Etsy yok).
Girdi: --klasorler A,B,... (yerel kopyalar; her biri <CIFT>.mp4 + QC/<CIFT>_QC.json, poster-video-v7-78 ciktisi) verilen
sirada; bir cift icin QC 'sonuc' PASS olan SON klasor secilir (sonraki kosu = yeni kod). FAIL / eksik surumler kopyalanmaz.
Kontrol (QC probe): 1440x1080, 180 kare, 30/1, 6,0 sn, h264, ses akisi yok; mp4 sha256 QC'deki dosyayla ayni klasorden.
Cikti --out: <CIFT>.mp4 (78), QC/<CIFT>_QC.json, MANIFEST.csv (cift, ilan, dosya, kaynak_klasor, qc_sonuc, hayalet_R_B, olcu,
kare, sure_sn, ses_akisi, boyut_mb, sha256, pass_klasorleri), OZET.md. 78 cift ve tekil sha256 degilse cikis 1."""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
ALAN = ["cift", "ilan", "dosya", "kaynak_klasor", "qc_sonuc", "hayalet_R_B", "olcu", "kare", "sure_sn", "ses_akisi", "boyut_mb",
        "sha256", "pass_klasorleri"]


def qc_ok(q):
    p = q.get("probe") or {}
    return (q.get("sonuc") == "PASS" and p.get("olcu") == "1440x1080" and p.get("kare") == 180 and p.get("fps") == "30/1"
            and abs(float(p.get("sure_sn") or 0) - 6.0) <= 0.05 and p.get("codec") == "h264" and p.get("ses_akisi") is False)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--klasorler", required=True, help="virgullu yerel klasorler (eskiden yeniye)")
    ap.add_argument("--adlar", required=True, help="virgullu Drive damga adlari (klasorlerle ayni sira)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    a = ap.parse_args(argv)
    kl = [Path(x) for x in a.klasorler.split(",") if x]
    adlar = [x for x in a.adlar.split(",") if x]
    if len(kl) != len(adlar):
        print("FAIL: klasor / ad sayisi farkli"); return 2
    ilan = {r["cift"]: r["listing_id"] for r in csv.DictReader(open(a.ids, encoding="utf-8"))}
    out = Path(a.out); (out / "QC").mkdir(parents=True, exist_ok=True)
    rows, sorun = [], []
    for c in sorted(ilan):
        aday = []
        for k, ad in zip(kl, adlar):
            qp, vp = k / "QC" / f"{c}_QC.json", k / f"{c}.mp4"
            if qp.is_file() and vp.is_file():
                q = json.loads(qp.read_text(encoding="utf-8"))
                if qc_ok(q):
                    aday.append((k, ad, q, qp, vp))
        if not aday:
            sorun.append(f"{c}: PASS surum yok"); continue
        k, ad, q, qp, vp = aday[-1]
        h = hashlib.sha256(vp.read_bytes()).hexdigest()
        shutil.copyfile(vp, out / f"{c}.mp4"); shutil.copyfile(qp, out / "QC" / f"{c}_QC.json")
        p = q["probe"]
        rows.append(dict(cift=c, ilan=ilan[c], dosya=f"{c}.mp4", kaynak_klasor=ad, qc_sonuc=q["sonuc"],
                         hayalet_R_B=q["kontrol"]["silinme_hayalet"]["deger"]["fark_R_B"], olcu=p["olcu"], kare=p["kare"],
                         sure_sn=p["sure_sn"], ses_akisi=p["ses_akisi"], boyut_mb=round(vp.stat().st_size / 1e6, 2), sha256=h,
                         pass_klasorleri=" ".join(x[1] for x in aday)))
    shas = [r["sha256"] for r in rows]
    if len(set(shas)) != len(shas):
        sorun.append(f"sha256 tekil degil ({len(shas) - len(set(shas))} tekrar)")
    with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN); w.writeheader(); w.writerows(rows)
    say = {ad: sum(1 for r in rows if r["kaynak_klasor"] == ad) for ad in adlar}
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Poster video v7b BIRLESIK\n\nPASS video {len(rows)} / {len(ilan)} | tekil sha256 {len(set(shas))} | sorun {len(sorun)}\n\n"
                + "Kaynak: " + ", ".join(f"{ad} {n}" for ad, n in say.items()) + "\n\n"
                + ("## Sorun\n" + "".join(f"- {s}\n" for s in sorun) if sorun else ""))
    print(f"BIRLESIK: {len(rows)}/{len(ilan)} | tekil sha {len(set(shas))} | kaynak {say} | sorun {sorun[:5]}")
    return 0 if len(rows) == len(ilan) and not sorun else 1


if __name__ == "__main__":
    sys.exit(main())
