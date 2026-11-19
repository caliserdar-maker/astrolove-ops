#!/usr/bin/env python3
"""Halka kapisi FAIL nedeni (19 Kas aksam, GOREV HALKA_KALICI_3 inceleme D ORTA 1). siparis-giris Kapilar adimi her tur icin halka_kapi
ciktisini ayri log'a yazar (h_baski.log, h_onizleme.log); bu betik o log'lardaki 'HALKA_KAPI {json}' satirini okuyup tek satir neden basar:
  TAVAN      mutlak halka bandi > tavan: kaynakta (kodlama oncesi) halka var -> Merkez cifti elle duzeltir.
  KODLAMA    kodlama bandi > esik: son kodlamanin ekledigi halka -> kod / kodlama incelenir (cifti duzeltmek care degil).
  HATA       kapi kendi hata alanini doldurdu (tur / boyut / kaynak boyutu).
  COKTU      HALKA_KAPI satiri yok (istisna, bellek, eksik _REF dosyasi): kapi sonuc vermedi.
Yalniz sayi ve sabit metin basar (dosya / cift / isim basmaz). Her zaman cikis 0 (neden yazimi isi durdurmaz; karar HALKA_RC'de)."""
import json
import sys
from pathlib import Path


def neden(yol):
    tur = Path(yol).stem.replace("h_", "", 1)
    try:
        satir = [s for s in Path(yol).read_text(errors="replace").splitlines() if s.startswith("HALKA_KAPI {")]
    except OSError:
        satir = []
    if not satir:
        return f"{tur}: COKTU (kapi sonuc vermedi; istisna / bellek / eksik kaynak)"
    try:
        r = json.loads(satir[-1][len("HALKA_KAPI "):])
    except ValueError:
        return f"{tur}: COKTU (kapi ciktisi okunamadi)"
    if r.get("PASS") is True:
        return f"{tur}: PASS"
    if r.get("hata"):
        return f"{tur}: HATA (kapi: {str(r['hata'])[:120]})"
    p = []
    hb, tv, kb, ke = r.get("halka_bant"), r.get("tavan"), r.get("kodlama_bant"), r.get("kodlama_esik")
    if hb is None:
        p.append("TAVAN olculemedi (mutlak halka bandi yok)")
    elif tv is not None and hb > tv:
        p.append(f"TAVAN (mutlak halka {hb} > {tv}; kaynak halkasi, Merkez cifti elle duzeltir)")
    if kb is None:
        p.append("KODLAMA olculemedi (kaynak yok ya da bant yok)")
    elif ke is not None and kb > ke:
        p.append(f"KODLAMA (kodlama bandi {kb} > {ke}; kodlama hatasi, kod incelenir)")
    return f"{tur}: " + (" + ".join(p) if p else "FAIL (neden siniflanamadi)")


if __name__ == "__main__":
    print("; ".join(neden(y) for y in sys.argv[1:]) or "neden yok")
