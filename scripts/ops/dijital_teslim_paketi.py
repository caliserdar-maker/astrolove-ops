#!/usr/bin/env python3
"""Onayli dijital dosyalari Etsy'ye elle yukleme paketi olarak hazirla."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

from siparis_onay import OnayHatasi, kimlik_dogrula, onay_kapisi

AZAMI_DOSYA = 5
AZAMI_BAYT = 20 * 1024 * 1024
UZANTILAR = {".jpg", ".png"}


def _ad_parcasi(deger: str, alan: str) -> str:
    temiz = re.sub(r"[^A-Za-z0-9]+", "_", deger.strip()).strip("_")
    if not temiz:
        raise OnayHatasi(f"PAKET RED: {alan} gecersiz")
    return temiz


def dosya_girdisi(deger: str) -> tuple[str, Path]:
    """CLI'daki ``BOY=YOL`` degerini ayir."""
    if "=" not in deger:
        raise argparse.ArgumentTypeError("dosya BOY=YOL biciminde olmali")
    boy, yol = deger.split("=", 1)
    if not boy.strip() or not yol.strip():
        raise argparse.ArgumentTypeError("dosya BOY=YOL biciminde olmali")
    return boy, Path(yol)


def paket_hazirla(kimlik: str, girdiler: list[tuple[str, Path]], onaylar: Path,
                   kok: Path, *, cift: str, urun: str) -> Path:
    """Onay kapisi aciksa atomik olarak son teslim dizinini olustur."""
    kimlik = kimlik_dogrula(kimlik)
    if not girdiler or len(girdiler) > AZAMI_DOSYA:
        raise OnayHatasi("PAKET RED: Etsy en fazla 5 dosya kabul eder")
    kaynaklar = [Path(yol) for _, yol in girdiler]
    onay_kapisi(kimlik, kaynaklar, onaylar)

    cift_ad = _ad_parcasi(cift, "cift").upper()
    urun_ad = _ad_parcasi(urun, "urun")
    hedef_adlar: list[str] = []
    for boy, kaynak in girdiler:
        if kaynak.suffix.casefold() not in UZANTILAR:
            raise OnayHatasi("PAKET RED: yalniz JPG ve PNG desteklenir")
        if kaynak.stat().st_size > AZAMI_BAYT:
            raise OnayHatasi("PAKET RED: bir dosya 20 MB sinirini asiyor")
        hedef_adlar.append(
            f"AstroLove_{cift_ad}_{urun_ad}_{_ad_parcasi(boy, 'boy')}{kaynak.suffix.lower()}"
        )
    if len(set(ad.casefold() for ad in hedef_adlar)) != len(hedef_adlar):
        raise OnayHatasi("PAKET RED: son dosya adlari cakismali")

    kok = Path(kok)
    kok.mkdir(parents=True, exist_ok=True)
    hedef = kok / kimlik
    gecici = Path(tempfile.mkdtemp(prefix=f".{kimlik}-", dir=kok))
    try:
        for kaynak, ad in zip(kaynaklar, hedef_adlar):
            shutil.copy2(kaynak, gecici / ad)
        (gecici / "TALIMAT.txt").write_text(
            "1. Tablette Chrome'u acin; etsy.com adresine girip Orders & Shipping sayfasini acin.\n"
            "2. Ilgili siparisi acin ve bu klasordeki JPG/PNG dosyalarini yukleyin.\n"
            "3. Dosya adlarini ve onizlemeyi kontrol edip Etsy'deki teslim islemini tamamlayin.\n",
            encoding="utf-8",
        )
        if hedef.exists():
            shutil.rmtree(hedef)
        gecici.replace(hedef)
    except Exception:
        shutil.rmtree(gecici, ignore_errors=True)
        raise
    return hedef


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kimlik", required=True)
    ap.add_argument("--onaylar", required=True, type=Path)
    ap.add_argument("--kok", type=Path, default=Path("TEMP/DIJITAL_TESLIM"))
    ap.add_argument("--cift", required=True)
    ap.add_argument("--urun", required=True)
    ap.add_argument("--dosya", action="append", required=True, type=dosya_girdisi,
                    metavar="BOY=YOL")
    args = ap.parse_args(argv)
    try:
        paket_hazirla(args.kimlik, args.dosya, args.onaylar, args.kok,
                       cift=args.cift, urun=args.urun)
    except (OnayHatasi, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
