import io
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prodigi"))
import kargo_maske as K  # noqa: E402

# Sahte veri: gercek siparis/takip numarasi degildir.
SAHTE = {"order": "ord_99990000001234", "receipt": "***5678", "gonderi": [
    {"tasiyici": "USPS", "numara": "92000000000000000000001111",
     "prodigi_url": "https://tracking.example.invalid/packageID/92000000000000000000001111"},
    {"tasiyici": "Spring", "numara": "LX000000022NL", "prodigi_url": "https://t.example.invalid/?tn=LX000000022NL?"},
    {"tasiyici": "Spring", "numara": "PRO0000NL00000003333",
     "prodigi_url": "https://t.example.invalid/?MyFICNumber=PRO0000NL00000003333"},
    {"tasiyici": "UPS", "numara": "1Z999AA10000004444"},
    {"tasiyici": "USPS", "numara": "420123459200000000000000005555"}]}
TAM = ["ord_99990000001234", "92000000000000000000001111", "LX000000022NL", "PRO0000NL00000003333",
       "1Z999AA10000004444", "420123459200000000000000005555"]
KALIR = ["ilan 4552211376", "run 36415376008", "S-a089c099", "GLOBAL-HPR-16X20", "2026-09-28T11:24:46.4281935Z",
         "sha c0c4c197dcfc95e2679c3e73b284b652fff3e351927a32cdc35a77c9cef4269b", "kota 4512", "ETSY_SHOP_ID: ***"]


def test_tam_degerler_loga_dusmez_son4_kalir():
    out = K.maskele(json.dumps(SAHTE) + "\n")
    for t in TAM:
        assert t not in out, t
    for s4 in ["ord_***1234", "***1111", "***22NL", "***3333", "***4444", "***5555"]:
        assert s4 in out, s4


def test_diger_kimlikler_degismez():
    for s in KALIR:
        assert K.maskele(s) == s, s


def test_add_mask_satiri_degismez():
    s = "::add-mask::92000000000000000000001111\n"
    assert K.maskele(s) == s


def test_akis_sarmalayici():
    b = io.StringIO()
    a = K.MaskeliAkis(b)
    print("TAKIP KORUMASI ord_72000000000000009999: kayitli takip UPS 92000000000000000000001111", file=a)
    assert b.getvalue() == "TAKIP KORUMASI ord_***9999: kayitli takip UPS ***1111\n"


def test_router_ciktisi_receipt_ve_takip():
    kod = ("import sys; sys.argv=['x']; import order_router as R; "
           "sys.stdout = R._MaskeliCikti(sys.stdout); "
           "print('receipt 4000000001 ord_13900000 takip 92000000000000000000001111')")
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True,
                       cwd=Path(__file__).resolve().parents[1] / "prodigi", env={"SIPARIS_KOD_ANAHTARI": "t", "PATH": ""})
    assert r.returncode == 0, r.stderr
    o = r.stdout
    assert "4000000001" not in o and "S-" in o
    assert "ord_***0000" in o and "***1111" in o and "92000000000000000000001111" not in o
