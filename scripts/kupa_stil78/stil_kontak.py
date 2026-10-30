#!/usr/bin/env python3
"""Kupa stil gorselleri (galeri 7-14) kontrol paftasi. ETSY API YOK, ag yok; yalniz yerel klasor okunur.
Girdi: klasorde KUPA_STIL_<CIFT>_<NN>_<STIL>.jpg (kupa_orchard/kapak_el/kod/stil78.py ciktisi ya da kucuk kopyalari).
Stil basina tek sayfa (KONTAK_<NN>_<STIL>.jpg): 78 cift alfabetik, her hucrede 'CIFT NN STIL' etiketi
(pafta(): scripts/kapak78/yd_kontak.py). Cikti ayrica OZET.md. Cikis 0 = 78 x 8 = 624 dosya tam, 1 = eksik / fazla."""
import argparse
import itertools
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kapak78"))
from yd_kontak import pafta  # noqa: E402

BURCLAR = ("ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO",
           "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES")
STILLER = (("07", "ORANGE"), ("08", "FIG"), ("09", "OLIVE"), ("10", "POMEGRANATE"),
           ("11", "ALMOND"), ("12", "LEMON"), ("13", "GRAPE"), ("14", "LOQUAT"))   # stil78.py STILLER sirasi
AD = re.compile(r"^KUPA_STIL_([A-Z]+_[A-Z]+)_(\d\d)_([A-Z]+)\.jpg$")


def ciftler():
    c = sorted({"_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2)})
    assert len(c) == 78
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hucre", type=int, default=440)
    ap.add_argument("--kaynak", default="")
    a = ap.parse_args(argv)
    d, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tum = ciftler()
    beklenen = {f"KUPA_STIL_{c}_{no}_{s}.jpg" for c in tum for no, s in STILLER}
    var = {p.name for p in d.glob("KUPA_STIL_*.jpg")}
    tanimsiz = sorted(n for n in var if not AD.match(n) or n not in beklenen)
    sonuc = []
    for n, (no, s) in enumerate(STILLER, 1):
        og = [(f"{c} {no} {s}", d / f"KUPA_STIL_{c}_{no}_{s}.jpg") for c in tum]
        sonuc.append(pafta(og, out / f"KONTAK_{no}_{s}.jpg", a.hucre, 10, f"KUPA STIL {no} {s} | 78 cift | {a.kaynak}"))
        print(f"[{n}/{len(STILLER)}] KONTAK_{no}_{s} eksik {len(sonuc[-1]['eksik'])}", flush=True)
    eksik = sum(len(s["eksik"]) for s in sonuc)
    say = len(var & beklenen)
    ok = say == 624 and not eksik and not tanimsiz
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Kupa stil kontrol paftasi\n\n{'PASS' if ok else 'FAIL'} | dosya {say}/624 | eksik {eksik} | "
                f"tanimsiz {len(tanimsiz)} | pafta {len(sonuc)}\nkaynak: {a.kaynak or a.dir}; hucre {a.hucre} px. Etsy istegi yok.\n\n"
                "| pafta | hucre | boyut | eksik |\n|---|---|---|---|\n")
        f.writelines(f"| {s['dosya']} | {s['hucre']} | {s['boyut']} | {', '.join(s['eksik']) or '-'} |\n" for s in sonuc)
        if tanimsiz:
            f.write("\nTanimsiz dosyalar: " + ", ".join(tanimsiz[:50]) + "\n")
    print(f"KONTAK OZET: {'PASS' if ok else 'FAIL'} dosya {say}/624 eksik {eksik} tanimsiz {len(tanimsiz)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
