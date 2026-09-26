#!/usr/bin/env python3
"""Siparis dosyalari icin SHA-256 tabanli, fail-closed onay kapisi.

Modul ag islemi yapmaz. Drive'dan senkronlanan ``ONAYLAR.json`` ile fiziksel
ve dijital teslim dosyalarina ayni kurali uygular. Onay sayfasi musteri
bilgisini yalniz hedef dizinde tutar; log ve donus degerlerine tasimaz.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class OnayHatasi(RuntimeError):
    """Onay kapisi kapaliyken uretilen guvenli hata."""


def dosya_sha256(yol):
    p = Path(yol)
    if not p.is_file():
        raise OnayHatasi("ONAY RED: teslim dosyasi eksik")
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for parca in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(parca)
    return h.hexdigest()


def paket_sha256(dosyalar):
    """Dosya adi ve icerik ozetlerinden siradan bagimsiz paket ozeti."""
    yollar = [Path(x) for x in dosyalar]
    if not yollar:
        raise OnayHatasi("ONAY RED: pakette teslim dosyasi yok")
    h = hashlib.sha256()
    for p in sorted(yollar, key=lambda x: x.name):
        ozet = dosya_sha256(p)
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        h.update(ozet.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def onaylari_oku(yol):
    p = Path(yol)
    if not p.is_file():
        raise OnayHatasi("ONAY RED: ONAYLAR.json bulunamadi")
    try:
        veri = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OnayHatasi("ONAY RED: ONAYLAR.json okunamadi") from exc
    if not isinstance(veri, dict):
        raise OnayHatasi("ONAY RED: ONAYLAR.json bicimi gecersiz")
    return veri


def onay_kapisi(kimlik, dosyalar, onaylar_yolu):
    """Guncel paket ozeti kayitli onayla ayniysa ozeti dondurur."""
    ozet = paket_sha256(dosyalar)
    kayit = onaylari_oku(onaylar_yolu).get(str(kimlik))
    if not isinstance(kayit, dict) or not kayit.get("onay_zamani"):
        raise OnayHatasi("ONAY RED: paket icin Serdar onayi yok")
    if kayit.get("sha256") != ozet:
        raise OnayHatasi("ONAY RED: dosya SHA256 onay kaydiyla eslesmiyor")
    return ozet


def onay_paketi_hazirla(kimlik, dosyalar, kok, *, isim_mesaj="", boy="", renk=""):
    """Tam cozunurluk dosyalari ve yerel yakinlastirma sayfasini hazirlar."""
    kaynaklar = [Path(x) for x in dosyalar]
    ozet = paket_sha256(kaynaklar)  # kopyalamadan once eksikleri fail-closed yakala
    hedef = Path(kok) / str(kimlik)
    hedef.mkdir(parents=True, exist_ok=True)
    satirlar = []
    for kaynak in kaynaklar:
        kopya = hedef / kaynak.name
        shutil.copy2(kaynak, kopya)
        satirlar.append(
            f'<section><h2>{html.escape(kaynak.name)}</h2>'
            f'<p>SHA256: <code>{dosya_sha256(kopya)}</code></p>'
            f'<img src="{html.escape(kaynak.name)}" alt="siparis dosyasi"></section>'
        )
    bilgi = " | ".join(x for x in (isim_mesaj, boy, renk) if x)
    sayfa = ("<!doctype html><meta charset=\"utf-8\"><title>Siparis onayi</title>"
             "<style>body{font-family:sans-serif}img{max-width:none;cursor:zoom-in}"
             "section{overflow:auto;border:1px solid #999;margin:1rem;padding:1rem}</style>"
             f"<h1>ONAY_BEKLIYOR</h1><p>{html.escape(bilgi)}</p>"
             f"<p>Paket SHA256: <code>{ozet}</code></p>{''.join(satirlar)}")
    (hedef / "onay.html").write_text(sayfa, encoding="utf-8")
    kayit = {"kimlik": str(kimlik), "durum": "ONAY_BEKLIYOR", "sha256": ozet,
             "hazirlama_zamani": datetime.now(timezone.utc).isoformat()}
    (hedef / "kayit.json").write_text(json.dumps(kayit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return kayit


def dijital_teslim_kapisi(kimlik, dosyalar, onaylar_yolu):
    """Dijital yukleme katmaninin Etsy'ye yazmadan once cagiracagi ortak kapi."""
    return onay_kapisi(kimlik, dosyalar, onaylar_yolu)
