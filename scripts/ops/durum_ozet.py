#!/usr/bin/env python3
"""Yerel QC kayitlarindan 78 burc cifti icin tek bir durum tablosu uretir."""

import argparse
import csv
import json
from datetime import datetime, timezone
from itertools import combinations_with_replacement
from pathlib import Path


BURCLAR = (
    "ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO",
    "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES",
)
ALANLAR = ("cift", "tamset_var", "galeri_sonuc", "video_sonuc", "varyasyon_ok", "son_guncelleme")


def cift_anahtari(deger):
    """Farkli yaygin cift yazimlarini repo anahtarina cevirir."""
    metin = (deger or "").upper()
    bulunan = [b for b in BURCLAR if b in metin]
    if len(bulunan) == 1 and metin.count(bulunan[0]) >= 2:
        bulunan.append(bulunan[0])
    if len(bulunan) != 2:
        return ""
    return "_".join(sorted(bulunan))


def kanonik_ciftler():
    return sorted({"_".join(sorted(c)) for c in combinations_with_replacement(BURCLAR, 2)})


def liste_oku(yol):
    if not yol:
        return kanonik_ciftler()
    with Path(yol).open(encoding="utf-8-sig", newline="") as fh:
        okuyucu = csv.DictReader(fh)
        if not okuyucu.fieldnames or "cift" not in okuyucu.fieldnames:
            raise ValueError("liste CSV dosyasinda 'cift' kolonu bulunmali")
        sonuc = []
        for satir in okuyucu:
            cift = cift_anahtari(satir.get("cift"))
            if not cift:
                raise ValueError(f"gecersiz cift: {satir.get('cift', '')!r}")
            if cift not in sonuc:
                sonuc.append(cift)
        return sonuc


def dosya_zamani(yol):
    return datetime.fromtimestamp(Path(yol).stat().st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sonuc_birlestir(degerler):
    """Bir ciftin birden cok kontrol satirini kayipsiz tek sonuca indirger."""
    degerler = [str(x).strip().upper() for x in degerler if str(x).strip()]
    if not degerler:
        return "?"
    if "FAIL" in degerler:
        return "FAIL"
    if all(x == "PASS" for x in degerler):
        return "PASS"
    return degerler[-1]


def csv_sonuclari(yol):
    if not yol:
        return {}, None
    gruplar = {}
    with Path(yol).open(encoding="utf-8-sig", newline="") as fh:
        for satir in csv.DictReader(fh):
            cift = cift_anahtari(satir.get("cift"))
            if cift:
                gruplar.setdefault(cift, []).append(satir.get("sonuc", ""))
    return {c: sonuc_birlestir(v) for c, v in gruplar.items()}, dosya_zamani(yol)


def galeri_oku(yol):
    if not yol:
        return {}, None
    veri = json.loads(Path(yol).read_text(encoding="utf-8"))
    ilanlar = veri.get("ilan") or {}
    sonuc = {}
    for ham_cift, kayit in ilanlar.items():
        cift = cift_anahtari(ham_cift)
        if not cift or not isinstance(kayit, dict):
            continue
        kontrol = kayit.get("kontrol") or {}
        varyasyon = kontrol.get("varyasyon", "?")
        sonuc[cift] = {
            "sonuc": str(kayit.get("sonuc") or "?").upper(),
            "varyasyon": "PASS" if varyasyon is True else "FAIL" if varyasyon is False else "?",
        }
    return sonuc, dosya_zamani(yol)


def uret(galeri=None, tamset_qc=None, video_qc=None, liste=None):
    ciftler = liste_oku(liste)
    galeriler, gz = galeri_oku(galeri)
    tamsetler, tz = csv_sonuclari(tamset_qc)
    videolar, vz = csv_sonuclari(video_qc)
    satirlar = []
    for cift in ciftler:
        zamanlar = []
        if cift in galeriler:
            zamanlar.append(gz)
        if cift in tamsetler:
            zamanlar.append(tz)
        if cift in videolar:
            zamanlar.append(vz)
        g = galeriler.get(cift, {})
        satirlar.append({
            "cift": cift,
            "tamset_var": "EVET" if cift in tamsetler else "?",
            "galeri_sonuc": g.get("sonuc", "?"),
            "video_sonuc": videolar.get(cift, "?"),
            "varyasyon_ok": g.get("varyasyon", "?"),
            "son_guncelleme": max(zamanlar) if zamanlar else "?",
        })
    return satirlar


def ozet_yaz(satirlar):
    print(f"Toplam cift: {len(satirlar)}")
    print(f"TAMSET bulunan: {sum(x['tamset_var'] == 'EVET' for x in satirlar)}")
    print(f"Galeri PASS: {sum(x['galeri_sonuc'] == 'PASS' for x in satirlar)}")
    print(f"Video PASS: {sum(x['video_sonuc'] == 'PASS' for x in satirlar)}")
    print(f"Varyasyon PASS: {sum(x['varyasyon_ok'] == 'PASS' for x in satirlar)}")
    print(f"Tum verisi eksik: {sum(all(x[a] == '?' for a in ALANLAR[1:]) for x in satirlar)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--galeri")
    ap.add_argument("--tamset-qc")
    ap.add_argument("--video-qc")
    ap.add_argument("--liste")
    ap.add_argument("--cikti", default="DURUM_78.csv")
    a = ap.parse_args(argv)
    satirlar = uret(a.galeri, a.tamset_qc, a.video_qc, a.liste)
    with Path(a.cikti).open("w", encoding="utf-8", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=ALANLAR)
        yazici.writeheader()
        yazici.writerows(satirlar)
    ozet_yaz(satirlar)


if __name__ == "__main__":
    main()
