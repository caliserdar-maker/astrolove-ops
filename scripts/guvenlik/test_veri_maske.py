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
kontrol("ilan_satis_oku: opak kod order_router.receipt_kod ile ayni (anahtar yokken)", "receipt " + R.receipt_kod(SAHTE) in s)
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

# --- C2 (CEO karari 23:50): takip_kuru / siparis_kiyas / prodigi_siparis_oku cikti maskesi, varyasyon degeri, \r, kapali anahtar
import ast  # noqa: E402
import subprocess  # noqa: E402


def main_ilk_cagri(kaynak):
    """main() govdesindeki ilk ifadeler arasinda maskeli_cikti_kur() cagrisi var mi (argparse / Api'den once)."""
    m = next(n for n in ast.parse(kaynak).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    for n in m.body[:3]:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and getattr(n.value.func, "attr", "") == "maskeli_cikti_kur":
            return True
    return False


for yol in ("scripts/prodigi/takip_kuru.py", "scripts/prodigi/siparis_kiyas.py", "scripts/prodigi/prodigi_siparis_oku.py"):
    kaynak = (KOK / yol).read_text()
    kontrol(f"{yol}: main() basinda stdout/stderr maskesi", main_ilk_cagri(kaynak))
    kontrol(f"{yol}: bilinen FAIL: maskesiz main denetimden gecmez",
            not main_ilk_cagri(kaynak.replace("R.maskeli_cikti_kur()", "pass")))
    ozet = [x.strip() for x in kaynak.splitlines() if "fh.write(" in x]
    kontrol(f"{yol}: adim ozetine yazan her satir maskeli ({len(ozet)})", all("maskeli_metin_tam(" in x for x in ozet))
# calisma zamani: _MaskeliCikti ile stdout ve stderr (R.log ve print) maskeli; maskesiz hal bilinen FAIL
kod = ("import sys; sys.path[:0] = [%r, %r, %r]\nimport order_router as R\n%s"
       "R.log('| %s | etsy-%s-8x10 | ord_1234567890 |')\nprint('stderr %s', file=sys.stderr)\nsys.stdout.flush(); sys.stderr.flush()\n")
for kur, ad in (("R.maskeli_cikti_kur()\n", "maskeli"), ("", "maskesiz (bilinen FAIL)")):
    r = subprocess.run([sys.executable, "-I", "-c", kod % (str(KOK / "scripts/prodigi"), str(KOK / "scripts/etsy"),
                        str(KOK / "scripts/guvenlik"), kur, SAHTE, SAHTE, SAHTE)], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ.get("PATH", ""), "ETSY_SHARED_SECRET": "k"})
    cikti = r.stdout + r.stderr
    if kur:
        kontrol("_MaskeliCikti: stdout + stderr'de siparis no yok, ord_ son 4", r.returncode == 0 and SAHTE not in cikti
                and "etsy-S-" in cikti and "ord_1234567890" not in cikti)
    else:
        kontrol("bilinen FAIL: maskesiz cikti siparis noyu basar", SAHTE in cikti)
kontrol("maskeli_metin_tam (adim ozeti): siparis no ve ord_ tam kimlik yok",
        SAHTE not in R.maskeli_metin_tam(f"receipt {SAHTE} ord_1234567890") and "ord_1234567890" not in R.maskeli_metin_tam("ord_1234567890"))
# varyasyon: kisisellestirme gizli, urun secenegi kalir; \r / \n alan icinde yeni satir dogurmaz
t2 = dict(t, variations=[{"property_id": 54, "formatted_name": "Personalization", "formatted_value": "Emily\nJames"},
                         {"formatted_name": "Names", "formatted_value": "Ada Lovelace"},
                         {"formatted_name": "Color", "formatted_value": "Champagne Ivory"}],
          sku="X\r::add-mask::y\n::warning::%s" % SAHTE)
s3 = I.satis_satiri(t2)
kontrol("varyasyon: Personalization ve bilinmeyen ozellik gizli, Color kalir", "Personalization=***" in s3 and "Names=***" in s3
        and "Ada" not in s3 and "Emily" not in s3 and "Color=Champagne Ivory" in s3)
kontrol("\\r / \\n: alan tek satirda kalir, yeni ::add-mask:: / ::warning:: satiri dogmaz, numara maskeli",
        "\r" not in s3 and "\n" not in s3 and s3.count("::warning::") == 2 and temiz(s3))
eski3 = "::warning::SATIS x | Personalization=Emily\nJames"
kontrol("bilinen FAIL: eski bicimde isim ve satir sonu gecer", "Emily" in eski3 and "\n" in eski3)
# kapali anahtar
os.environ.pop("ETSY_SHARED_SECRET", None)
os.environ.pop("SIPARIS_KOD_ANAHTARI", None)
kontrol("anahtar yok: receipt_kod 'S-gizli' (order_router ve ilan_satis_oku), sabit anahtar yok",
        R.receipt_kod(SAHTE) == I.receipt_kod(SAHTE) == "S-gizli")
os.environ["ETSY_SHARED_SECRET"] = "k"
kontrol("anahtar var: opak kod S- + 8 hane, iki islev ayni", re.fullmatch(r"S-[0-9a-f]{8}", I.receipt_kod(SAHTE)) is not None
        and I.receipt_kod(SAHTE) == R.receipt_kod(SAHTE))
os.environ.pop("ETSY_SHARED_SECRET", None)

print("veri maske testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
