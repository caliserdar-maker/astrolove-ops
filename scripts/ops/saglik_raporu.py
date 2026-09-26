#!/usr/bin/env python3
"""Drive TEMP denetim CSV'lerinden tek sayfalik magaza saglik raporu uretir."""
from __future__ import annotations

import argparse
import base64
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Kaynak:
    dosya: str
    ilan_alanlari: tuple[str, ...]
    kural_alanlari: tuple[str, ...]


KAYNAKLAR = (
    Kaynak("MAGAZA_DENETIM.csv", ("ilan",), ("kural",)),
    Kaynak("FIYAT_SKU.csv", ("ilan_id", "ilan", "listing_id"), ("kural", "neden", "sorun")),
    Kaynak("GORSEL_DENETIM.csv", ("ilan_id",), ("neden",)),
    Kaynak("KISISEL_UYUM.csv", ("ilan_id",), ("neden",)),
    Kaynak("VARYASYON_CANLI.csv", ("ilan",), ("neden",)),
    Kaynak("CANLI_METIN.csv", ("ilan_id",), ("neden",)),
    Kaynak("MAGAZA_AYAR.csv", ("nesne_id",), ("kural",)),
)
OLUMSUZ = {"FAIL", "HATA", "ERROR", "UYARI", "BELIRSIZ"}
ISARET = "SAGLIK_ISSUES_V1:"


def _alan(satir: dict[str, str], adaylar: tuple[str, ...]) -> str:
    return next((str(satir.get(ad, "")).strip() for ad in adaylar if str(satir.get(ad, "")).strip()), "?")


def _kurallar(satir: dict[str, str], kaynak: Kaynak) -> list[str]:
    ham = _alan(satir, kaynak.kural_alanlari)
    if ham in {"", "-", "?"}:
        return ["belirtilmemis_sorun"]
    return [parca.strip() for parca in ham.replace("|", ";").split(";") if parca.strip()]


def _durum(satir: dict[str, str]) -> str:
    for alan in ("durum", "sonuc", "status"):
        if satir.get(alan):
            return str(satir[alan]).strip().upper()
    return "?"


def _onceki(yol: Path | None) -> set[str]:
    if not yol or not yol.is_file():
        return set()
    for satir in yol.read_text(encoding="utf-8").splitlines():
        if satir.startswith(f"<!-- {ISARET}"):
            try:
                kod = satir.removeprefix(f"<!-- {ISARET}").removesuffix(" -->").strip()
                return set(json.loads(base64.b64decode(kod).decode("utf-8")))
            except (ValueError, json.JSONDecodeError):
                return set()
    return set()


def rapor_uret(girdi: Path, onceki: Path | None = None, tarih: str | None = None) -> str:
    sorunlar: dict[str, tuple[str, str, str]] = {}
    ilan_durumlari: dict[str, list[str]] = defaultdict(list)
    kaynak_ozeti: list[tuple[str, str, int, int]] = []
    kural_sayaci: Counter[tuple[str, str]] = Counter()

    for kaynak in KAYNAKLAR:
        yol = girdi / kaynak.dosya
        if not yol.is_file():
            kaynak_ozeti.append((kaynak.dosya, "?", 0, 0))
            continue
        with yol.open(encoding="utf-8-sig", newline="") as fh:
            satirlar = list(csv.DictReader(fh))
        hatalar = 0
        for no, satir in enumerate(satirlar, 2):
            durum, ilan = _durum(satir), _alan(satir, kaynak.ilan_alanlari)
            # Magaza geneli nesneleri ilan sayisina katma.
            gercek_ilan = ilan.isdigit()
            if gercek_ilan:
                ilan_durumlari[ilan].append(durum)
            if durum not in OLUMSUZ:
                continue
            hatalar += 1
            for kural in _kurallar(satir, kaynak):
                anahtar = f"{kaynak.dosya}|{ilan}|{kural}"
                sorunlar[anahtar] = (kaynak.dosya, ilan, kural)
                kural_sayaci[(kaynak.dosya, kural)] += 1
        kaynak_ozeti.append((kaynak.dosya, "OK", len(satirlar), hatalar))

    toplam = len(ilan_durumlari)
    temiz = sum(all(durum == "PASS" for durum in durumlar) for durumlar in ilan_durumlari.values())
    oran = f"%{temiz * 100 / toplam:.1f}" if toplam else "?"
    kritik = [f"{kural} ({adet})" for (_, kural), adet in kural_sayaci.most_common(5)]
    eski, yeni = _onceki(onceki), set(sorunlar)
    duzelen, eklenen = sorted(eski - yeni), sorted(yeni - eski)
    gun = tarih or date.today().isoformat()

    satirlar = [
        f"# Magaza saglik raporu - {gun}",
        f"- Toplam ilan: {toplam if toplam else '?'}",
        f"- Hatasiz ilan: {temiz if toplam else '?'}/{toplam if toplam else '?'} ({oran})",
        f"- En kritik 5 sorun: {', '.join(kritik) if kritik else '-'}",
        f"- Onceki rapora gore: {len(duzelen)} duzelen, {len(eklenen)} yeni sorun",
        "",
        "## Kaynak durumu",
        "| Kaynak | Durum | Satir | Sorunlu satir |",
        "|---|---:|---:|---:|",
    ]
    satirlar += [f"| {ad} | {durum} | {adet if durum != '?' else '?'} | {hata if durum != '?' else '?'} |"
                 for ad, durum, adet, hata in kaynak_ozeti]
    satirlar += ["", "## Kural bazinda sorunlar", "| Kaynak | Kural | Adet |", "|---|---|---:|"]
    satirlar += [f"| {kaynak} | {kural} | {adet} |" for (kaynak, kural), adet in kural_sayaci.most_common()]
    if not kural_sayaci:
        satirlar.append("| - | - | 0 |")

    satirlar += ["", "## Sorunlu ilanlar", "| Ilan | Kaynak | Kural |", "|---|---|---|"]
    for _, (kaynak, ilan, kural) in sorted(sorunlar.items(), key=lambda x: (x[1][1], x[1][0], x[1][2])):
        baglanti = f"[{ilan}](https://www.etsy.com/listing/{ilan})" if ilan.isdigit() else ilan
        satirlar.append(f"| {baglanti} | {kaynak} | {kural} |")
    if not sorunlar:
        satirlar.append("| - | - | - |")

    def fark_bolumu(baslik: str, anahtarlar: list[str]) -> list[str]:
        sonuc = ["", f"### {baslik} ({len(anahtarlar)})"]
        sonuc += [f"- {deger}" for deger in anahtarlar] or ["- -"]
        return sonuc

    satirlar += ["", "## Onceki raporla fark"]
    satirlar += fark_bolumu("Duzelen", duzelen) + fark_bolumu("Yeni", eklenen)
    kod = base64.b64encode(json.dumps(sorted(yeni), ensure_ascii=False).encode()).decode()
    satirlar += ["", f"<!-- {ISARET} {kod} -->"]
    return "\n".join(satirlar) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--girdi", type=Path, default=Path("TEMP"))
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--onceki", type=Path)
    ap.add_argument("--tarih", default=date.today().isoformat())
    args = ap.parse_args(argv)
    cikti = args.cikti or args.girdi / f"SAGLIK_{args.tarih}.md"
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(rapor_uret(args.girdi, args.onceki, args.tarih), encoding="utf-8")
    print(cikti)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
