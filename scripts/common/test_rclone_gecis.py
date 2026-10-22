#!/usr/bin/env python3
"""rclone_gecis sahte testi (ag yok, gercek rclone yok): bekle / takas / dogrula senaryolari."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rclone_gecis as r  # noqa: E402

KOD = "4/0AbCdEfGhIjKlMnOpQrStUvWxYz012345"
CID = "test-client.apps.googleusercontent.com"


class SahteRclone:
    """kok dizini = Drive klasoru; silme_bozuk: deletefile basarisiz; uyari: shared client_id uyarisi basar"""
    def __init__(self, kok, silme_bozuk=False, uyari=False, yenile=False):
        self.kok, self.silme_bozuk, self.uyari, self.yenile, self.tur = pathlib.Path(kok), silme_bozuk, uyari, yenile, 0

    def __call__(self, *arg, conf=None):
        k = arg[0]
        if k == "lsf" and arg[1] == "gdrive:ASTROLOVE":
            if self.yenile and conf:
                p = pathlib.Path(conf); t = p.read_text()
                p.write_text(t.replace('"expiry":"2026-10-22T10:00:00Z"', '"expiry":"2026-10-22T20:00:00Z"'))
            return types.SimpleNamespace(returncode=0, stdout="TEMP/\nSOSYAL/\n",
                                         stderr="NOTICE: gdrive: This remote uses rclone's shared Google Drive client_id" if self.uyari else "")
        if k == "lsf":
            self.tur += 1
            return types.SimpleNamespace(returncode=0, stdout="\n".join(x.name for x in self.kok.iterdir()), stderr="")
        if k == "cat":
            return types.SimpleNamespace(returncode=0, stdout=(self.kok / arg[1].split("/")[-1]).read_text(), stderr="")
        if k == "deletefile":
            if self.silme_bozuk:
                return types.SimpleNamespace(returncode=1, stdout="", stderr="x")
            (self.kok / arg[1].split("/")[-1]).unlink()
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(arg)


def kos(fn, argv):
    sys.argv = ["x", *argv]
    try:
        fn(); return 0
    except SystemExit as e:
        return e.code


def main():
    r.time.sleep = lambda s: None
    os.environ.update(CLIENT_ID=CID, GOOGLE_CLIENT_SECRET="GOCSPX-sahte")
    td = pathlib.Path(tempfile.mkdtemp())
    sonuc = []

    # bekle: dosya 2. turda gelir (adresin tamami), okunur, silinir
    kok = td / "drive"; kok.mkdir()
    sr = SahteRclone(kok); r.rclone = sr
    orig = sr.__call__
    def gec(*a, conf=None):
        if a[0] == "lsf" and sr.tur == 1 and not (kok / "RCLONE_KOD.txt").exists():
            (kok / "RCLONE_KOD.txt").write_text(f"http://localhost:53682/?state=s123&code={KOD}&scope=x\n")
        return orig(*a, conf=conf)
    r.rclone = gec
    kod_f = td / "kod"
    k = kos(r.main, ["bekle", "--kok", "gdrive:T", "--ad", "RCLONE_KOD", "--dk", "1", "--durum", "s123", "--cikti", str(kod_f)])
    sonuc.append(("bekle: okundu + silindi + kod dosyasi 0600", k == 0 and not (kok / "RCLONE_KOD.txt").exists()
                  and kod_f.read_text() == KOD and oct(kod_f.stat().st_mode)[-3:] == "600"))
    # bekle: state uyusmuyor -> FAIL, dosya yine silinir
    (kok / "RCLONE_KOD.txt").write_text(f"http://localhost:53682/?state=BASKA&code={KOD}")
    r.rclone = SahteRclone(kok)
    k = kos(r.main, ["bekle", "--kok", "gdrive:T", "--ad", "RCLONE_KOD", "--dk", "1", "--durum", "s123", "--cikti", str(td / "k2")])
    sonuc.append(("bekle: state uyusmazligi FAIL (dosya silinmis)", isinstance(k, str) and "state" in k and not (kok / "RCLONE_KOD.txt").exists()))
    # bekle: silinemezse takas yok
    (kok / "RCLONE_KOD.txt").write_text(KOD)
    r.rclone = SahteRclone(kok, silme_bozuk=True)
    k = kos(r.main, ["bekle", "--kok", "gdrive:T", "--ad", "RCLONE_KOD", "--dk", "1", "--cikti", str(td / "k3")])
    sonuc.append(("bekle: silinemezse FAIL, kod dosyasi yok", isinstance(k, str) and "silinemedi" in k and not (td / "k3").exists()))
    (kok / "RCLONE_KOD.txt").unlink()
    # bekle: zaman asimi
    r.rclone = SahteRclone(kok)
    r.time.time = iter([0, 0] + [i * 100 for i in range(1, 100)]).__next__
    k = kos(r.main, ["bekle", "--kok", "gdrive:T", "--ad", "RCLONE_KOD", "--dk", "1", "--cikti", str(td / "k4")])
    import time as _t; r.time.time = _t.time
    sonuc.append(("bekle: zaman asimi FAIL", isinstance(k, str) and "gelmedi" in k))

    # takas: PASS ve refresh_token yok -> FAIL
    r.post = lambda url, v: ({"access_token": "ya29.sahte-access-token-xxxxxxxx", "refresh_token": "1//sahte-refresh-token-xxxxxxxx",
                              "expires_in": 3599, "scope": " ".join(r.KAPSAM)}, None) if v.get("code") == KOD else (None, "invalid_grant")
    conf = td / "new.conf"
    k = kos(r.main, ["takas", "--kod-dosyasi", str(kod_f), "--conf-cikti", str(conf)])
    t = conf.read_text() if conf.exists() else ""
    sonuc.append(("takas: conf yazildi, client_id + refresh var, kod dosyasi silindi", k == 0 and f"client_id = {CID}" in t
                  and "refresh_token" in t and not kod_f.exists() and oct(conf.stat().st_mode)[-3:] == "600"))
    (td / "kx").write_text("4/0YanlisKodYanlisKodYanlisKod");
    k = kos(r.main, ["takas", "--kod-dosyasi", str(td / "kx"), "--conf-cikti", str(td / "c2")])
    sonuc.append(("takas: gecersiz kod FAIL, conf yok", isinstance(k, str) and "invalid_grant" in k and not (td / "c2").exists()))
    r.post = lambda url, v: ({"access_token": "ya29.sahte-access-token-xxxxxxxx", "expires_in": 3599}, None)
    (td / "ky").write_text(KOD)
    k = kos(r.main, ["takas", "--kod-dosyasi", str(td / "ky"), "--conf-cikti", str(td / "c3")])
    sonuc.append(("takas: refresh_token yok FAIL", isinstance(k, str) and "refresh_token" in k))

    # dogrula
    def sahte_get(url, tok, aud=CID, kap=" ".join(r.KAPSAM), docs=200):
        if "tokeninfo" in url:
            return 200, {"aud": aud, "scope": kap}
        return (docs if "docs" in url else 200), {}
    r.rclone = SahteRclone(kok)
    r.get = sahte_get
    arg = ["dogrula", "--conf", str(conf), "--doc", "D", "--sheet", "S"]
    sonuc.append(("dogrula: hepsi PASS", kos(r.main, arg) == 0))
    r.get = lambda u, t: sahte_get(u, t, aud="202264815644.apps.googleusercontent.com")
    sonuc.append(("dogrula: aud eski istemci -> FAIL", kos(r.main, arg) == 1))
    r.get = lambda u, t: sahte_get(u, t, kap="https://www.googleapis.com/auth/drive")
    sonuc.append(("dogrula: yalniz drive kapsami -> FAIL", kos(r.main, arg) == 1))
    r.get = lambda u, t: sahte_get(u, t, docs=403)
    sonuc.append(("dogrula: Docs 403 -> FAIL", kos(r.main, arg) == 1))
    r.get = sahte_get; r.rclone = SahteRclone(kok, uyari=True)
    sonuc.append(("dogrula: shared client_id uyarisi -> FAIL", kos(r.main, arg) == 1))
    # yenileme testi (adim 7): conf'taki expiry gecmiste, rclone yeniler
    c7 = td / "c7.conf"
    c7.write_text(conf.read_text().split("token = ")[0] + 'token = {"access_token":"ya29.x-eski-access-token-xxxx","refresh_token":"1//r-refresh-token-xxxxx","expiry":"2026-10-22T10:00:00Z"}\n')
    r.rclone = SahteRclone(kok, yenile=True)
    sonuc.append(("dogrula --yenileme-bekle: dolmus + yenilendi PASS", kos(r.main, ["dogrula", "--conf", str(c7), "--yenileme-bekle"]) == 0))
    c7.write_text(c7.read_text().replace("20:00:00Z", "10:00:00Z"))
    r.rclone = SahteRclone(kok, yenile=False)
    sonuc.append(("dogrula --yenileme-bekle: yenilenmedi FAIL", kos(r.main, ["dogrula", "--conf", str(c7), "--yenileme-bekle"]) == 1))

    for ad, ok in sonuc:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in sonuc)
    print(f"rclone_gecis testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
