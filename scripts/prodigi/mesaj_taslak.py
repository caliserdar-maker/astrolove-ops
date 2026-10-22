#!/usr/bin/env python3
"""order_router JSON durumundan Etsy musteri mesaji taslaklari uretir.

Bu arac hicbir uzak servise baglanmaz ve mesaj gondermez. Alici bilgileri
yalnizca kullanicinin belirttigi cikti dizinindeki taslaklara yazilir.
"""

import argparse
import csv
import json
import re
from pathlib import Path


SABLONLAR = {
    1: '''Hi {buyer_first_name},

Thank you for your order! The name "{submitted_name}" is either longer than 11 letters or includes a character our name font does not support. We suggest printing it as "{suggested_name}".

Could you please confirm this spelling, or send us another version with up to 11 letters?

Lena & Serdar
AstroLoveArt
''',
    2: '''Hi {buyer_first_name},

Thank you for your order! Your message is longer than the 35-character limit. We suggest shortening it to:

"{suggested_message}"

Please confirm this version, or send us another message with up to 35 characters.

Lena & Serdar
AstroLoveArt
''',
    3: '''Hi {buyer_first_name},

Thank you for your order! We still need the personalization details for your {sign_a} and {sign_b} print. Please send us:

Name for {sign_a}: {name_a}
Name for {sign_b}: {name_b}
Message, up to 35 characters: {message}

Once we receive these details, we can continue preparing your order.

Lena & Serdar
AstroLoveArt
''',
    4: '''Hi {buyer_first_name},

Thank you for your order! Since both sides feature {zodiac_sign}, we would like to confirm the name placement before we prepare your print:

Left: {left_name}
Right: {right_name}

Please reply "OK" if this is correct, or tell us which names to switch.

Lena & Serdar
AstroLoveArt
''',
    5: '''Hi {buyer_first_name},

We wanted to let you know that we are doing an extra file check before your order goes to print. This will cause a short delay, and the new estimated date is {date}.

Thank you for your patience. We will keep you updated if anything changes.

Lena & Serdar
AstroLoveArt
''',
    6: '''Hi {buyer_first_name},

Good news, your order has shipped! Your tracking number is {tracking_number} with {carrier}.

You can follow it here: {tracking_url}

Please allow a little time for the first tracking update to appear.

Lena & Serdar
AstroLoveArt
''',
}

ISIM_NEDENLERI = {"UZUN_ISIM", "EMOJI", "KARAKTER", "KIRIL_ISIM", "ALFABE_ISIM"}
BOS_NEDENLERI = {"BOS", "EKSIK_SORU"}
UZUN_TIRE = re.compile("[\u2013\u2014]")
YER_TUTUCU = re.compile(r"\{([a-zA-Z0-9_]+)\}")
GUVENLI_RECEIPT = re.compile(r"[A-Za-z0-9_.-]+")


class TaslakHatasi(ValueError):
    """Girdi veya guvenlik kurali ihlali."""


def kayitlari_oku(yol):
    veri = json.loads(Path(yol).read_text(encoding="utf-8"))
    if isinstance(veri, list):
        kayitlar = veri
    elif isinstance(veri, dict) and isinstance(veri.get("orders"), list):
        kayitlar = veri["orders"]
    elif isinstance(veri, dict):
        kayitlar = []
        for anahtar, deger in veri.items():
            if not isinstance(deger, dict):
                continue
            kayit = dict(deger)
            kayit.setdefault("receipt_id", anahtar)
            kayitlar.append(kayit)
    else:
        raise TaslakHatasi("STATE JSON bir liste veya nesne olmali")
    if not all(isinstance(kayit, dict) for kayit in kayitlar):
        raise TaslakHatasi("Her STATE kaydi bir nesne olmali")
    return kayitlar


def _neden_metni(kayit):
    return str(kayit.get("neden") or kayit.get("reason") or kayit.get("note") or "")


def sablon_sec(kayit):
    """Dokumandaki order_router esleme tablosuna gore sablon numarasi."""
    stage = str(kayit.get("stage") or "")
    neden = _neden_metni(kayit).upper()
    kodlar = set(re.findall(r"[A-Z_]+", neden))
    if stage == "shipped" and (kayit.get("tracking_number") or kayit.get("tracking")):
        return 6
    if stage not in {"ISIM_BEKLIYOR", "atlandi", "error"}:
        return None
    if "MANUAL_FILE_CHECK" in kodlar or "FILE_REVIEW_DELAY" in kodlar:
        return 5
    if stage != "ISIM_BEKLIYOR":
        return None
    if "AYNI_BURC" in kodlar or "SAME_SIGN" in kodlar:
        return 4
    if kayit.get("sign_a") and kayit.get("sign_a") == kayit.get("sign_b"):
        return 4
    if kodlar & BOS_NEDENLERI:
        return 3
    if "UZUN_MESAJ" in kodlar:
        return 2
    if kodlar & ISIM_NEDENLERI:
        return 1
    return None


def _alanlar(kayit):
    alanlar = dict(kayit)
    ek = kayit.get("fields")
    if isinstance(ek, dict):
        alanlar.update(ek)
    if "tracking_number" not in alanlar and alanlar.get("tracking"):
        alanlar["tracking_number"] = alanlar["tracking"]
    return alanlar


def taslagi_doldur(sablon_no, kayit):
    alanlar = _alanlar(kayit)

    def yerine_koy(eslesme):
        ad = eslesme.group(1)
        deger = alanlar.get(ad)
        return str(deger) if deger is not None and str(deger) != "" else f"[DOLDUR: {ad}]"

    taslak = YER_TUTUCU.sub(yerine_koy, SABLONLAR[sablon_no])
    if UZUN_TIRE.search(taslak):
        raise TaslakHatasi("Taslak uzun veya orta tire iceriyor")
    return taslak


def uret(state_yolu, cikti_yolu):
    cikti = Path(cikti_yolu)
    cikti.mkdir(parents=True, exist_ok=True)
    ozet = []
    for kayit in kayitlari_oku(state_yolu):
        receipt = str(kayit.get("receipt_id") or "")
        if not receipt or not GUVENLI_RECEIPT.fullmatch(receipt):
            raise TaslakHatasi("Eksik veya guvensiz receipt_id")
        stage = str(kayit.get("stage") or "")
        neden = _neden_metni(kayit)
        sablon_no = sablon_sec(kayit)
        ozet.append((receipt, stage, neden, str(sablon_no) if sablon_no else "SABLON_YOK"))
        if sablon_no:
            (cikti / f"{receipt}.txt").write_text(taslagi_doldur(sablon_no, kayit), encoding="utf-8")
    with (cikti / "OZET.csv").open("w", encoding="utf-8", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow(("receipt", "stage", "neden", "sablon_no"))
        yazici.writerows(ozet)
    return len(ozet), sum(sablon != "SABLON_YOK" for *_, sablon in ozet)


def main():
    parser = argparse.ArgumentParser(description="order_router STATE JSON dosyasindan mesaj taslagi uret")
    parser.add_argument("--state", required=True, help="STATE JSON yolu")
    parser.add_argument("--cikti", required=True, help="Taslak cikti dizini")
    args = parser.parse_args()
    toplam, yazilan = uret(args.state, args.cikti)
    print(f"TAMAM: {toplam} kayit islendi, {yazilan} taslak yazildi")


if __name__ == "__main__":
    main()
