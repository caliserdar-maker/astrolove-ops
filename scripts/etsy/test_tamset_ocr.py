"""Sentetik OCR ciktilariyla ``tamset_qc.yazi_denetle`` regresyon testleri."""

from unittest.mock import patch

import pytest

import tamset_qc


def okuma(*kelimeler):
    """Kelimeleri yuksek guvenli, tesseract-benzeri bir okumaya cevir."""
    return " ".join(kelimeler), [(kelime, 95.0) for kelime in kelimeler]


def denetle(ref_okumalari, aday_okumalari, a="SCORPIO", b="CANCER"):
    ref = {i: okuma(*kelimeler) for i, kelimeler in enumerate(ref_okumalari, 1)}
    with patch.object(tamset_qc, "ocr", side_effect=[okuma(*x) for x in aday_okumalari]):
        return tamset_qc.yazi_denetle(object(), ref, a, b)


@pytest.mark.xfail(reason="tamset_qc PR — NT parcalanmasini henuz PRINT olarak birlestirmiyor")
def test_print_parcalanmasi_ve_tire_yanlis_alarm_degildir():
    sonuc = denetle(
        [("PRINT",), ("PRINT",), ("PRINT",)],
        [("PR", "—", "NT"), ("PR", "—", "NT"), ("PR", "—", "NT")],
    )

    assert sonuc["eksik"] == []
    assert sonuc["tire"] == []


@pytest.mark.parametrize("kirpik", ["ITH", "STROLOVE"])
def test_referans_kelimesinin_kirpigi_fazla_sayilmaz(kirpik):
    tam = {"ITH": "WITH", "STROLOVE": "ASTROLOVE"}[kirpik]
    sonuc = denetle(
        [(tam,), (tam,), (tam,)],
        [(kirpik,), (kirpik,), (kirpik,)],
    )

    assert sonuc["fazla"] == []


def test_warm_parchment_tutarsiz_okunursa_eksik_sayilmaz():
    sonuc = denetle(
        [("WARM", "PARCHMENT"), ("WARM", "PARCHMENT"), ("WARM", "PARCHMENT")],
        [("CARD",), ("WARM", "PARCHMENT", "CARD"), ("CARD",)],
    )

    assert sonuc["eksik"] == []


def test_yanlis_burc_yakalanir():
    sonuc = denetle(
        [("CANCER",), ("CANCER",), ("CANCER",)],
        [("LIBRA",), ("LIBRA",), ("LIBRA",)],
    )

    assert sonuc["yanlis_burc"] == ["LIBRA"]
    assert sonuc["eksik_burc"] == ["SCORPIO"]


def test_fulfilment_yazim_hatasi_yakalanir():
    sonuc = denetle(
        [("FULFILLMENT",), ("FULFILLMENT",), ("FULFILLMENT",)],
        [("FULFILMENT",), ("FULFILMENT",), ("FULFILMENT",)],
    )

    assert sonuc["eksik"] == ["FULFILLMENT"]
    assert sonuc["fazla"] == ["FULFILMENT"]


@pytest.mark.parametrize("eski_slogan", [("TWO", "SOULS"), ("ONE", "BOND")])
def test_eski_slogan_yakalanir(eski_slogan):
    sonuc = denetle(
        [("LOVE", "WRITTEN", "STARS"), ("LOVE", "WRITTEN", "STARS"), ("LOVE", "WRITTEN", "STARS")],
        [eski_slogan, eski_slogan, eski_slogan],
    )

    assert set(sonuc["fazla"]) == set(eski_slogan)


def test_eksik_satir_yakalanir():
    sonuc = denetle(
        [("MADE", "FOR", "YOUR", "STORY"), ("MADE", "FOR", "YOUR", "STORY"), ("MADE", "FOR", "YOUR", "STORY")],
        [("MADE", "FOR"), ("MADE", "FOR"), ("MADE", "FOR")],
    )

    assert sonuc["eksik"] == ["STORY", "YOUR"]
