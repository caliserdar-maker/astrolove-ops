import subprocess, sys
from pathlib import Path

B = Path(__file__).with_name("log_suz.py")
ORNEK = """aciklama PATCH: KAPALI
::add-mask::abcDEF1234567890secretkey
::add-mask::zzzSharedSecret99
{"access_token": "123456.ABCDEFGHIJKLMNOP", "refresh_token": "123456.QRSTUVWXYZ"}
x-api-key: abcdefgh12345:secretpart
Authorization: Bearer abc.def.ghi-123
OZET 4570143815: {"state": "active"}
HATA: PUT /listings/4570143815/inventory -> 400
"""


def run(args, text):
    return subprocess.run([sys.executable, str(B), *args], input=text, capture_output=True, text=True)


def test_suzulmus_logda_sifir_eslesme():
    temiz = run([], ORNEK).stdout
    assert "::add-mask::" not in temiz and "abcDEF" not in temiz and "ABCDEFGHIJ" not in temiz
    assert "secretpart" not in temiz and "abc.def.ghi" not in temiz
    assert "OZET 4570143815" in temiz and "-> 400" in temiz
    r = run(["--say"], temiz)
    assert r.stdout.strip() == "0" and r.returncode == 0


def test_ham_logda_eslesme_var():
    r = run(["--say"], ORNEK)
    assert int(r.stdout) >= 5 and r.returncode == 1
