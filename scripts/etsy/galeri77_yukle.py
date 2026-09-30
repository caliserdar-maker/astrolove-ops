#!/usr/bin/env python3
"""77 cift galerisi Etsy yuklemesi (Serdar karari 30 Eyl; CL yontemi = cl_galeri_degistir.uygula). ETSY'YE YAZAR.
Girdi: HAZIR.csv (gorsel oturumu: cift,listing_id,...,set) + her cift icin paket dizini <paket>/<CIFT>/ (NN_*.jpg + ALT_METIN.csv).
set=19: 19 gorsel (CL gibi). set=17: 05 ve 19 yok, 17 gorsel CL sirasiyla, 4 renk bagi (Warm Parchment karti sonra).
Ilan basina: paket sayisi = set mi -> YEDEK (galeri manifest + tum eski gorseller, --yedek-drive'a kopyalanir ve dogrulanir)
-> uygula (capa akisi, geri okuma: sira, alt metin, renk baglari, state/baslik/etiket/aciklama/envanter/video ayni).
Ilk FAIL'de DUR. Kota (x-remaining-today) < --kota-taban + ILAN_UST ise yeni ilana baslanmaz (ertesi kosu devam).
Ilerleme --ilerleme JSON: {ilanlar: {listing_id: {cift, set, durum}}}; PASS olan ayni set tekrar yuklenmez;
PASS set=17 iken satir set=19 olursa TAMAMLA_BEKLIYOR (05/19 ekleme ayri adim; bu kosu dokunmaz).
Kullanim: galeri77_yukle.py --hazir HAZIR.csv --paket DIR --out OUT --ilerleme ILERLEME.json --confirm GALERI77
          [--yedek-drive gdrive:...] [--kota-taban 150] [--limit N]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402

CL_ID = "4570143815"
ILAN_UST = 90           # ilan basi ust sinir cagri (13 sil + 17-19 yukle + bag + capa + geri okumalar)


def log(m):
    print(m, flush=True)


def drive_kopya(yerel, hedef):
    r = subprocess.run(["rclone", "copy", str(yerel), hedef, "-q"], capture_output=True, text=True)
    c = subprocess.run(["rclone", "check", str(yerel), hedef, "--one-way", "-q"], capture_output=True, text=True)
    if r.returncode or c.returncode:
        raise SystemExit(f"HATA: yedek Drive'a yazilamadi/dogrulanamadi ({hedef}). YAZMA YOK. DUR.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hazir", required=True); ap.add_argument("--paket", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ilerleme", required=True); ap.add_argument("--confirm", default="")
    ap.add_argument("--yedek-drive", default=""); ap.add_argument("--kota-taban", type=int, default=150)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.confirm != "GALERI77":
        raise SystemExit("HATA: --confirm GALERI77 gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = json.loads(Path(a.ilerleme).read_text()) if Path(a.ilerleme).exists() else {"ilanlar": {}}
    R.setdefault("ilanlar", {})
    satir = [r for r in csv.DictReader(open(a.hazir, encoding="utf-8")) if (r.get("listing_id") or "").strip()]
    is_, t0, durdu, n = [], time.time(), "", 0
    for r in satir:
        lid, cift, st_ = r["listing_id"].strip(), r["cift"].strip(), int(r.get("set") or 19)
        onceki = R["ilanlar"].get(lid) or {}
        if lid == CL_ID:
            continue
        if onceki.get("durum") == "PASS" and int(onceki.get("set") or 0) == st_:
            continue
        if onceki.get("durum") == "PASS" and int(onceki.get("set") or 0) == 17 and st_ == 19:
            R["ilanlar"][lid]["durum_19"] = "TAMAMLA_BEKLIYOR"; continue
        is_.append((lid, cift, st_))
    log(f"HAZIR {len(satir)} satir | islenecek {len(is_)} | kota {api.remaining}")

    def kaydet():
        Path(a.ilerleme).write_text(json.dumps(R, ensure_ascii=False, indent=1))
    try:
        for i, (lid, cift, st_) in enumerate(is_, 1):
            if a.limit and n >= a.limit:
                durdu = f"limit {a.limit}"; break
            api.get(f"/listings/{lid}", ok404=True)          # kotayi tazele
            q = api.remaining
            if q is not None and str(q).isdigit() and int(q) < a.kota_taban + ILAN_UST:
                durdu = f"kota {q} < {a.kota_taban}+{ILAN_UST}; {i - 1}/{len(is_)} ilandan sonra (sonraki kosu devam)"; break
            kaynak = Path(a.paket) / cift
            yol = G.kaynak_dosyalar(kaynak)
            if len(yol) != st_:
                R["ilanlar"][lid] = {"cift": cift, "set": st_, "durum": "FAIL", "not": f"paket {len(yol)} gorsel != set {st_}"}
                durdu = f"FAIL {cift}: paket sayisi"; break
            o = out / lid; o.mkdir(parents=True, exist_ok=True)
            G.yedek_al(api, shop, lid, o)
            if a.yedek_drive:
                # onceki kosu FAIL ise ilk (asil) yedek korunur; yeni yedek ayri klasore (30 Eyl)
                ek = f"_devam_{time.strftime('%Y%m%d_%H%M', time.gmtime())}" if (R["ilanlar"].get(lid) or {}).get("durum") == "FAIL" else ""
                drive_kopya(o / "yedek", f"{a.yedek_drive}/{lid}_{cift}{ek}")
            try:
                rap = G.uygula(api, shop, lid, kaynak, kaynak / "ALT_METIN.csv", o, a.kota_taban)
                R["ilanlar"][lid] = {"cift": cift, "set": st_, "durum": rap["sonuc"], "ts": time.strftime("%Y-%m-%d %H:%M", time.gmtime())}
            except SystemExit as e:
                R["ilanlar"][lid] = {"cift": cift, "set": st_, "durum": "FAIL", "not": str(e)[:300]}
            kaydet(); n += 1
            g = time.time() - t0
            log(f"[{i}/{len(is_)} %{i * 100 // len(is_)}] {lid} {cift} set={st_}: {R['ilanlar'][lid]['durum']} | gecen {g:.0f}s "
                f"kalan ~{g / i * (len(is_) - i):.0f}s | kota {api.remaining}")
            if R["ilanlar"][lid]["durum"] != "PASS":
                durdu = f"ilk FAIL {lid} {cift}: {R['ilanlar'][lid].get('not', '')}"; break
    finally:
        kaydet()
        say = {}
        for v in R["ilanlar"].values():
            say[v["durum"]] = say.get(v["durum"], 0) + 1
        md = [f"# GALERI 77 YUKLEME {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "",
              f"- HAZIR satir {len(satir)} | bu kosu {n} ilan | toplam durum {say}",
              f"- TAMAMLA_BEKLIYOR (17 -> 19): {sum(1 for v in R['ilanlar'].values() if v.get('durum_19') == 'TAMAMLA_BEKLIYOR')}",
              f"- Durdu: {durdu or 'hayir'} | Etsy cagrisi {api.calls} | kota son {api.remaining}"]
        (out / "RAPOR.md").write_text("\n".join(md) + "\n")
        log("\n".join(md))
    if durdu.startswith(("ilk FAIL", "FAIL")):
        raise SystemExit(f"DUR: {durdu}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
