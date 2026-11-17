#!/usr/bin/env python3
"""Veriden gelen siparis no maskesi testi (IP adim 0 c, 17 Kas 2026). Ag kapali (CLAUDE.md TEST AGI); dis cagri yok.
scripts/etsy/ilan_satis_oku.py satis_satiri / maskele ve scripts/prodigi/siparis_oku.py siparis_satiri: log satirinda
10-12 haneli siparis no ve merchantReference (etsy-<no>-<boy>) ACIK GECMEZ, yerine opak kod (S-xxxxxxxx) gelir.
Bilinen FAIL: maskesiz eski bicim satiri ayni denetimden gecemez. Sahte no: 9000000123 (CLAUDE.md test serisi)."""
import os
import re
import socket
import sys
import urllib.request
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = Path(__file__).resolve().parents[2]
for p in ("scripts/etsy", "scripts/prodigi", "scripts/guvenlik"):
    sys.path.insert(0, str(KOK / p))
os.environ.pop("SIPARIS_KOD_ANAHTARI", None)
os.environ.pop("ETSY_SHARED_SECRET", None)
import ilan_satis_oku as I  # noqa: E402
import siparis_oku as SO  # noqa: E402
import order_router as R  # noqa: E402

SAHTE = "9000000123"
HATA = []
ACIK = re.compile(r"(?<!\d)\d{10,12}(?!\d)")


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def temiz(satir):
    """Denetim: satirda acik 10-12 haneli sayi yok (ord_ Prodigi kimligi haric, receipt_desen.ROUTER ile ayni kural)."""
    return not [m for m in ACIK.finditer(satir) if not satir[:m.start()].endswith("ord_")]


t = {"created_timestamp": 1794900000, "quantity": 1, "price": {"amount": 2900, "divisor": 100, "currency_code": "USD"},
     "variations": [{"formatted_name": "Size", "formatted_value": "8x10"}], "receipt_id": int(SAHTE), "sku": "POD-CAN_LIB-MB-8x10",
     "shipped_timestamp": None}
s = I.satis_satiri(t)
kontrol("ilan_satis_oku: satirda acik siparis no yok", temiz(s) and SAHTE not in s)
kontrol("ilan_satis_oku: opak kod order_router.receipt_kod ile ayni", "receipt " + R.receipt_kod(SAHTE) in s)
kontrol("ilan_satis_oku: diger alanlar kaldi (adet, fiyat, sku, varyasyon)", "adet 1" in s and "29.0 USD" in s
        and "sku POD-CAN_LIB-MB-8x10" in s and "Size=8x10" in s and s.startswith("::warning::SATIS "))
kontrol("ilan_satis_oku: ilk satir (ilan id) maskeli", temiz(I.maskele(f"::warning::SATIS CANCER_LIBRA 4570110641: toplam 3 islem")))
eski = (f"::warning::SATIS x | adet 1 | 29.0 USD | Size=8x10 | receipt {SAHTE} | sku POD | gonderim yok")
kontrol("bilinen FAIL: maskesiz eski bicim denetimden gecmez", not temiz(eski))
kontrol("::add-mask:: satiri degismez (receipt_desen.satir_satir)", I.maskele("::add-mask::" + SAHTE) == "::add-mask::" + SAHTE)

z = {"id": "ord_1234567890", "created": "2026-11-17", "merchantReference": f"etsy-{SAHTE}-8x10", "receipt_eslesme": True,
     "stage": "InProgress", "details": {"status": "ok"}, "issues": [], "eylemler": {"cancel": False},
     "kalem": [{"sku": "GLOBAL-HPR-8x10", "adet": 1, "durum": "Ok", "asset": [{"kaynak": "drive", "durum": "Complete"}]}]}
s2 = SO.siparis_satiri(z)
kontrol("siparis_oku: merchantReference maskeli (etsy-S-...-8x10)", temiz(s2) and SAHTE not in s2
        and f"etsy-{R.receipt_kod(SAHTE)}-8x10" in s2)
kontrol("siparis_oku: Prodigi kimligi (ord_) ve diger alanlar kaldi", s2.startswith("ord_1234567890 | 2026-11-17 | ")
        and "GLOBAL-HPR-8x10x1 Ok [drive Complete]" in s2)
eski2 = f"ord_1 | x | etsy-{SAHTE}-8x10 | eslesme True"
kontrol("bilinen FAIL: maskesiz merchantReference denetimden gecmez", not temiz(eski2))

# kaynak denetimi: iki betikte print edilen her satir maskeleyen fonksiyondan gecer (eski dogrudan f-string print yok)
for yol, izinli in (("scripts/etsy/ilan_satis_oku.py", ("print(maskele(", "print(satis_satiri(", 'print(f"::warning::BITTI')),
                    ("scripts/prodigi/siparis_oku.py", ("print(siparis_satiri(",))):
    satirlar = [x.strip() for x in (KOK / yol).read_text().splitlines() if "print(" in x]
    kontrol(f"{yol}: her print maskeli yol ({len(satirlar)} print)", satirlar and all(x.startswith(izinli) for x in satirlar))

print("veri maske testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
