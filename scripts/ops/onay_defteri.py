#!/usr/bin/env python3
"""Siparis onay defteri (ONAYLAR.json) okuma/yazma kapilari (26 Eki 2026, Serdar onayi).

Mantik scripts/ops/durum_dosyasi.py'de (tur "onay"); bu betik siparis-onay-yaz.yml'in komut satirini korur.
  oku: lsjson hatasi FAIL; listede varsa copyto ZORUNLU, boyut ve JSON nesnesi kontrolu; ilk kayit yalniz defter listede
       yok + yedek yok (YEDEK/ONAYLAR_* ya da kokteki eski ONAYLAR_YEDEK_*) + dogrudan okunamiyorsa.
  yaz: azalmama (yalniz bu kimlik eklenir/guncellenir), okumadan beri uzak degismedi, yedek
       <klasor>/YEDEK/ONAYLAR_<damga>_<run>.json (son 30 tutulur; kokteki eski ONAYLAR_YEDEK_* tasinmaz/silinmez),
       yazim sonrasi sha256 geri okuma."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import durum_dosyasi as DD  # noqa: E402

AD = "ONAYLAR.json"
DefterHatasi = DD.DurumHatasi


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["oku", "yaz"])
    ap.add_argument("--uzak", required=True, help="defter klasoru (or. gdrive:ASTROLOVE/TEMP/SIPARIS_ONAY)")
    ap.add_argument("--dizin", required=True, help="yerel defter klasoru (ONAYLAR.json burada)")
    ap.add_argument("--durum", required=True, help="okuma anindaki defter kopyasi klasoru")
    ap.add_argument("--kimlik", default="")
    a = ap.parse_args(argv)
    if a.komut == "yaz" and not a.kimlik:
        print("::error::ONAY DEFTERI FAIL: yaz icin --kimlik gerekli", flush=True)
        return 1
    d = DD.Dosya(f"{a.uzak.rstrip('/')}/{AD}", "onay", kimlik=a.kimlik, eski_yedek="ONAYLAR_YEDEK_*.json")
    return DD.calistir(a.komut, d, Path(a.dizin) / AD, a.durum)


if __name__ == "__main__":
    sys.exit(main())
