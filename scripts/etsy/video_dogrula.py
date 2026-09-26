#!/usr/bin/env python3
"""Yuklenmis bir videoyu beklenen video ve istege bagli tuzakla karsilastir."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


KARE_SAYISI = 10  # ilk/son kare ve aradaki sekiz esit aralikli kare


def _sonuc(neden: str) -> dict:
    return {
        "pass": False,
        "sure_fark": None,
        "kare_fark_list": [],
        "tuzak_orani": None,
        "eski_slogan": False,
        "neden": neden,
    }


def _araclari_dogrula() -> None:
    eksik = [ad for ad in ("ffmpeg", "ffprobe") if shutil.which(ad) is None]
    if eksik:
        raise RuntimeError("gerekli arac bulunamadi: " + ", ".join(eksik))


def _sure(path: Path) -> float:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"bos veya bulunamayan video: {path}")
    komut = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]
    sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=30)
    if sonuc.returncode:
        raise ValueError(f"ffprobe videoyu okuyamadi: {path}")
    try:
        sure = float(json.loads(sonuc.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"gecersiz video suresi: {path}") from exc
    if sure <= 0:
        raise ValueError(f"gecersiz video suresi: {path}")
    return sure


def _kareler(path: Path, sure: float) -> list[np.ndarray]:
    # Son zaman damgasini kapsayici sinirin hemen onunde tutar.
    zamanlar = np.linspace(0.0, max(0.0, sure - 0.02), KARE_SAYISI)
    kareler = []
    for zaman in zamanlar:
        komut = [
            "ffmpeg", "-v", "error", "-ss", f"{zaman:.6f}", "-i", str(path),
            "-frames:v", "1", "-vf", "scale=256:256,format=gray", "-f",
            "rawvideo", "-pix_fmt", "gray", "pipe:1",
        ]
        sonuc = subprocess.run(komut, capture_output=True, timeout=30)
        if sonuc.returncode or len(sonuc.stdout) != 256 * 256:
            raise ValueError(f"video karesi okunamadi ({zaman:.3f}s): {path}")
        kareler.append(np.frombuffer(sonuc.stdout, dtype=np.uint8).reshape(256, 256))
    return kareler


def _burc_dilimi(poster_png: str | Path | None) -> tuple[slice, slice]:
    if poster_png is None:
        return slice(0, 154), slice(0, 256)
    poster = Path(poster_png)
    if not poster.is_file() or poster.stat().st_size == 0:
        raise ValueError(f"poster okunamadi: {poster}")
    with Image.open(poster) as resim:
        gri = np.asarray(resim.convert("L").resize((256, 256)), dtype=np.uint8)
    # Poster kenarinin medyani arka plan kabul edilerek belirgin icerigin kutusu bulunur.
    kenar = np.concatenate((gri[0], gri[-1], gri[:, 0], gri[:, -1]))
    maske = np.abs(gri.astype(np.int16) - int(np.median(kenar))) > 18
    ys, xs = np.where(maske)
    if len(xs) < 64:
        return slice(0, 154), slice(0, 256)
    pay = 4
    return (
        slice(max(0, int(ys.min()) - pay), min(256, int(ys.max()) + pay + 1)),
        slice(max(0, int(xs.min()) - pay), min(256, int(xs.max()) + pay + 1)),
    )


def _farklar(a: list[np.ndarray], b: list[np.ndarray], bolge: tuple[slice, slice]) -> list[dict]:
    sonuc = []
    for no, (sol, sag) in enumerate(zip(a, b)):
        fark = np.abs(sol.astype(np.int16) - sag.astype(np.int16))
        sonuc.append({
            "kare": no,
            "genel": round(float(fark.mean()), 4),
            "burc": round(float(fark[bolge].mean()), 4),
        })
    return sonuc


def _ortalama(farklar: list[dict]) -> float:
    return float(np.mean([(x["genel"] + x["burc"]) / 2 for x in farklar]))


def _ocr_eski_slogan(kareler: list[np.ndarray]) -> tuple[bool, str | None]:
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract yok; eski slogan OCR atlandi"
    if shutil.which("tesseract") is None:
        return False, "tesseract yok; eski slogan OCR atlandi"
    for kare in kareler:
        metin = " ".join(pytesseract.image_to_string(Image.fromarray(kare)).upper().split())
        if "TWO SOULS" in metin or "ONE BOND" in metin:
            return True, None
    return False, None


def dogrula(canli_mp4, beklenen_mp4, tuzak_mp4=None, poster_png=None) -> dict:
    """Video icerigini karsilastirip makinece okunabilir bir sonuc dondurur."""
    sonuc = _sonuc("")
    try:
        _araclari_dogrula()
        canli, beklenen = Path(canli_mp4), Path(beklenen_mp4)
        canli_sure, beklenen_sure = _sure(canli), _sure(beklenen)
        sonuc["sure_fark"] = round(abs(canli_sure - beklenen_sure), 4)
        canli_kare = _kareler(canli, canli_sure)
        beklenen_kare = _kareler(beklenen, beklenen_sure)
        bolge = _burc_dilimi(poster_png)
        sonuc["kare_fark_list"] = _farklar(canli_kare, beklenen_kare, bolge)
        beklenen_farki = _ortalama(sonuc["kare_fark_list"])

        nedenler = []
        # Sikistirma farkina izin verirken belirgin icerik farkini reddeder.
        if sonuc["sure_fark"] > 0.25:
            nedenler.append("sure farki 0.25 saniyeyi asti")
        if beklenen_farki > 3.0:
            nedenler.append("kare icerigi beklenenden farkli")

        if tuzak_mp4 is not None:
            tuzak = Path(tuzak_mp4)
            tuzak_sure = _sure(tuzak)
            tuzak_farki = _ortalama(_farklar(canli_kare, _kareler(tuzak, tuzak_sure), bolge))
            sonuc["tuzak_orani"] = round(
                beklenen_farki / tuzak_farki if tuzak_farki else float("inf"), 6
            )
            if beklenen_farki * 3 >= tuzak_farki:
                nedenler.append("beklenen farki tuzak farkindan en az 3 kat kucuk degil")

        sonuc["eski_slogan"], ocr_notu = _ocr_eski_slogan(canli_kare)
        if sonuc["eski_slogan"]:
            nedenler.append("eski slogan bulundu")
        if ocr_notu:
            nedenler.append(ocr_notu)

        asil_hata = [n for n in nedenler if "OCR atlandi" not in n]
        sonuc["pass"] = not asil_hata
        sonuc["neden"] = "; ".join(nedenler) if nedenler else "video icerigi dogrulandi"
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        sonuc["neden"] = str(exc)
    return sonuc


__all__ = ["dogrula"]
