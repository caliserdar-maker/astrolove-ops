#!/usr/bin/env python3
"""secret_gecis sahte testi. AG KAPALI: socket bastan engellenir; GitHub (urllib.request.urlopen), Etsy (secret_gecis.http_get,
etsy_common.requests.post) ve nacl taklit; rclone / curl / sudo PATH'te sahte. Gercek fonksiyonlar kosar: secret_gecis.calis,
gh_secrets.set_secret / secret_meta / delete_secret, etsy_common.TokenStore.refresh, scripts/etsy/token_geri_yaz.sh, is akisi
adimlari (bash -e). Bilinen PASS + bilinen FAIL + sir ciktisi taramasi. Kullanim: python3 scripts/etsy/test_secret_gecis.py"""
import base64
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import types
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(KOK / "scripts" / "common"))


def _nacl_kur():
    """pynacl taklidi: muhur = b'MUHUR:' + deger (sahte GitHub cozer; gercek sifreleme testin konusu degil)."""
    nacl, enc, pub = types.ModuleType("nacl"), types.ModuleType("nacl.encoding"), types.ModuleType("nacl.public")

    class Base64Encoder:
        pass

    class PublicKey:
        def __init__(self, *a):
            pass

    class SealedBox:
        def __init__(self, pk):
            pass

        def encrypt(self, b):
            return b"MUHUR:" + b
    enc.Base64Encoder, pub.PublicKey, pub.SealedBox, nacl.encoding, nacl.public = Base64Encoder, PublicKey, SealedBox, enc, pub
    sys.modules.update({"nacl": nacl, "nacl.encoding": enc, "nacl.public": pub})


_nacl_kur()
import etsy_common as E  # noqa: E402
import gh_secrets as GS  # noqa: E402
import secret_gecis as SG  # noqa: E402

WF = KOK / ".github/workflows/etsy-secret-gecis.yml"
KEY, ESKI, YENI, FARKLI = "Kk3yStr1ngQ7w8e9", "Qz7mESKIx9Lp2Wv4", "Hn4tYENIb6Rc8Js1", "Vd2gFARKq5Tz7Mx3"
OPS, GHT, AT0, RT0 = "ghp_OpsAdm1nTok0123", "ghs_RunT0k456789ab", "at0-Aa11Bb22Cc33Dd", "rt0-Ee44Ff55Gg66Hh"
C, YD, YN = SG.CANLI_AD, SG.YEDEK_AD, SG.YENI_AD
CIKTI = []           # (ad, stdout + stderr) : sir ciktisi taramasi
SIR = set()          # taramada aranacak butun degerler (tam deger, sha256, base64)
SIR4 = set()         # ilk / son 4 karakteri de aranan degerler: yalniz bu testin SABIT degerleri. Betigin urettigi rastgele degerlerin
#                      4 karakterlik parcasi sabit metinle sans eseri cakisabilir (kararsiz test); onlarda tam deger / ozet aranir.
UYKU = []            # son kosuda secret_gecis.time.sleep cagrilari (istekler arasi bekleme)
_TMP = {"kok": None, "bin": None}


def tmp(on):
    """Bu testin butun gecici dizinleri tek kok altinda; sonda yalniz o kok silinir (baska surecin dizinine dokunulmaz)."""
    if _TMP["kok"] is None:
        _TMP["kok"] = tempfile.mkdtemp(prefix="sg_test_")
    return Path(tempfile.mkdtemp(prefix=on, dir=_TMP["kok"]))


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Yanit:
    def __init__(self, kod, govde=None, basliklar=None):
        self.status = self.status_code = kod
        self._g = govde if govde is not None else {}
        self.headers = basliklar or {}
        self.text = json.dumps(self._g)

    def read(self):
        return json.dumps(self._g).encode()

    def json(self):
        return self._g

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SahteGH:
    """GitHub REST taklidi: secrets (deger + updated_at), variables, workflows (state), runs."""
    def __init__(self, secretler=None, kapali=(), kosular=(), bayat_meta=False, yazma_yok=False, meta_eksik=False, toplam=None, silme_hata=()):
        self.silme_hata = set(silme_hata)
        self.s = {k: {"deger": v, "updated_at": "2026-11-01T00:00:00Z"} for k, v in (secretler or {}).items()}
        self.v, self.cagri, self.n = {}, [], 0
        self.wf = {a + ".yml": ("disabled_manually" if a in kapali else "active") for a in SG.KAPAT}
        self.kosular, self.bayat_meta, self.yazma_yok, self.meta_eksik, self.toplam = list(kosular), bayat_meta, yazma_yok, meta_eksik, toplam

    def saat(self):
        """Her yazimda 3 sn ilerleyen saat (GitHub updated_at saniye cozunurlugunde; ayni saniyede iki yazim ayirt edilemez)."""
        self.n += 3
        return (datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=self.n)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def hata(self, url, kod):
        return urllib.error.HTTPError(url, kod, "x", {}, io.BytesIO(b'{"message":"x"}'))

    def ac(self, req, timeout=None):
        url, y = req.full_url, req.get_method()
        yol = urllib.parse.urlparse(url).path.split("/actions/", 1)[1]
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        g = json.loads(req.data) if req.data else None
        self.cagri.append((y, yol))
        if yol == "secrets/public-key":
            return Yanit(200, {"key": base64.b64encode(b"k" * 32).decode(), "key_id": "1"})
        m = re.fullmatch(r"secrets/(\w+)", yol)
        if m:
            ad = m.group(1)
            if y == "PUT":
                if self.yazma_yok:
                    raise self.hata(url, 403)
                deger = base64.b64decode(g["encrypted_value"]).split(b"MUHUR:", 1)[1].decode()
                SIR.add(deger)
                yeni = ad not in self.s
                eski = (self.s.get(ad) or {}).get("updated_at")
                self.s[ad] = {"deger": deger, "updated_at": eski if (self.bayat_meta and eski) else self.saat()}
                return Yanit(201 if yeni else 204)
            if ad not in self.s:
                raise self.hata(url, 404)
            if y == "GET":
                return Yanit(200, {"name": ad, "created_at": "x"} if self.meta_eksik else {"name": ad, "updated_at": self.s[ad]["updated_at"], "created_at": "x"})
            if y == "DELETE":
                if ad in self.silme_hata:
                    raise self.hata(url, 403)
                del self.s[ad]
                return Yanit(204)
        m = re.fullmatch(r"workflows/([\w.-]+)(?:/(enable|disable))?", yol)
        if m:
            if m.group(1) not in self.wf:
                raise self.hata(url, 404)
            if m.group(2):
                assert y == "PUT"
                if self.yazma_yok:
                    raise self.hata(url, 403)
                self.wf[m.group(1)] = "active" if m.group(2) == "enable" else "disabled_manually"
                return Yanit(204)
            return Yanit(200, {"state": self.wf[m.group(1)]})
        m = re.fullmatch(r"variables(?:/(\w+))?", yol)
        if m:
            ad = m.group(1) or (g or {}).get("name")
            if y == "POST":
                self.v[ad] = g["value"]
                return Yanit(201)
            if ad not in self.v:
                raise self.hata(url, 404)
            if y == "PATCH":
                self.v[ad] = g["value"]
                return Yanit(204)
            return Yanit(200, {"name": ad, "value": self.v[ad]})
        if yol == "runs":
            sec = [k for k in self.kosular if not q.get("status") or k["status"] == q["status"]]
            return Yanit(200, {"total_count": len(sec) if self.toplam is None else self.toplam, "workflow_runs": sec})
        raise AssertionError(f"sahte GitHub: bilinmeyen {y} {yol}")


class SahteEtsy:
    def __init__(self, gecerli, ping_dogrular=True, oauth_dogrular=True, kalan=5000, yenileme_kodu=200, ping_baslik=True, red=403, red_baslik=True):
        self.red_baslik = red_baslik
        self.gecerli, self.ping_dogrular, self.oauth_dogrular, self.kalan = set(gecerli), ping_dogrular, oauth_dogrular, kalan
        self.ping_baslik, self.red = ping_baslik, red
        self.bearer, self.refresh, self.n, self.cagri, self.yenileme, self.yenileme_kodu = AT0, RT0, 0, [], [], yenileme_kodu

    def get(self, url, basliklar):
        sec = basliklar["x-api-key"].partition(":")[2]
        br = basliklar.get("Authorization", "")
        SIR.add(sec)
        self.cagri.append((url.split("/application", 1)[1], sec, bool(br)))
        assert basliklar["x-api-key"].startswith(KEY + ":"), "keystring ortamdan gelmeli"
        baslik = True
        if url.endswith("/openapi-ping"):
            ok, baslik = sec in self.gecerli or not self.ping_dogrular, self.ping_baslik
        elif url.endswith("/users/me"):
            if br != "Bearer " + self.bearer:
                return Yanit(401, {"error": "invalid_token"})
            ok = sec in self.gecerli or not self.oauth_dogrular
        else:
            raise AssertionError("izinsiz Etsy GET: " + url)
        baslik = baslik and (ok or self.red_baslik)
        return Yanit(200 if ok else self.red, {"x": 1}, {"x-remaining-today": str(self.kalan)} if (self.kalan is not None and baslik) else {})

    def post(self, url, data=None, headers=None, timeout=None, **k):
        assert url == E.TOKEN_URL and data["grant_type"] == "refresh_token", "POST yalniz token yenileme"
        self.yenileme.append(headers["x-api-key"].partition(":")[2])
        if self.yenileme[-1] not in self.gecerli:            # Etsy gecersiz anahtarla token vermez (varsayim; olculmedi)
            return Yanit(401, {"error": "invalid_api_key"})
        if self.yenileme_kodu != 200 or data["refresh_token"] != self.refresh:
            return Yanit(self.yenileme_kodu if self.yenileme_kodu != 200 else 400, {"error": "invalid_grant"})
        self.n += 1
        self.bearer, self.refresh = f"at{self.n}-Zz99Yy88Xx77Ww", f"rt{self.n}-Vv66Uu55Tt44Ss"
        SIR.update({self.bearer, self.refresh})
        SIR4.update({self.bearer, self.refresh})
        return Yanit(200, {"access_token": self.bearer, "refresh_token": self.refresh, "expires_in": 3600, "token_type": "Bearer"})


SAHTE_RCLONE = r'''#!/usr/bin/env python3
import json, os, shutil, sys
a = [x for x in sys.argv[1:] if not x.startswith("--")]
D = os.environ["RCLONE_SAHTE_DRIVE"]
os.makedirs(D, exist_ok=True)
with open(os.path.join(D, "_ortam_adlari"), "a") as fh: fh.write(" ".join(sorted(os.environ)) + "\n")   # alt surece devredilen ortam ADLARI
def y(p): return os.path.join(D, p.split(":", 1)[1]) if p.startswith("gdrive:") else p
hata = os.environ.get("RCLONE_SAHTE_HATA", "")
if a[0] == "copyto":
    k, h = y(a[1]), y(a[2])
    if not os.path.isfile(k): sys.exit(3)
    if hata and a[2].startswith("gdrive:") and hata in a[2]: sys.exit(1)
    os.makedirs(os.path.dirname(h) or ".", exist_ok=True); shutil.copyfile(k, h); sys.exit(0)
if a[0] == "lsjson":
    if os.environ.get("RCLONE_SAHTE_LS_HATA"): sys.exit(1)
    k = y(a[1])
    if not os.path.isdir(k): sys.exit(3)
    print(json.dumps([{"Name": f, "Size": os.path.getsize(os.path.join(k, f)), "ModTime": "2026-11-12T00:00:00Z"}
                      for f in sorted(os.listdir(k)) if os.path.isfile(os.path.join(k, f))])); sys.exit(0)
if a[0] == "deletefile":
    if os.environ.get("RCLONE_SAHTE_SIL_HATA"): sys.exit(1)
    k = y(a[1])
    if not os.path.isfile(k): sys.exit(4)
    os.remove(k); sys.exit(0)
sys.exit(9)
'''


def araclar():
    if _TMP["bin"] is not None:
        return _TMP["bin"]
    d = _TMP["bin"] = tmp("bin_")
    (d / "rclone").write_text(SAHTE_RCLONE)
    (d / "curl").write_text("#!/bin/bash\necho 'echo sahte kurulum'\n")
    (d / "sudo").write_text("#!/bin/bash\nexec \"$@\"\n")
    for f in d.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return d


def drive(alan=ESKI, taze=True, ucuncu=None, keystring=KEY):
    """Sahte Drive: TEMP/ETSY_TOKEN.json (alan None = alan yok); ucuncu = ASTROLOVE/ETSY_TOKEN.json'daki alan (None = dosya yok)."""
    d = tmp("drive_")
    t = datetime.now(timezone.utc) - (timedelta(minutes=1) if taze else timedelta(hours=3))
    tok = {"keystring": keystring, "refresh_token": RT0, "access_token": AT0, "obtained_at": t.strftime("%Y-%m-%d %H:%M:%S"),
           "token_type": "Bearer", "expires_in": 3600, "scope": "listings_r"}
    if alan:
        tok = dict({"keystring": keystring, "shared_secret": alan}, **tok)
    (d / "ASTROLOVE/TEMP").mkdir(parents=True)
    (d / "ASTROLOVE/TEMP/ETSY_TOKEN.json").write_text(json.dumps(tok, indent=2) + "\n")
    if ucuncu is not None:
        (d / "ASTROLOVE/ETSY_TOKEN.json").write_text(json.dumps(dict(tok, shared_secret=ucuncu) if ucuncu else tok))
    return d


def tok_oku(d, yol="ASTROLOVE/TEMP/ETSY_TOKEN.json"):
    return json.loads((d / yol).read_text())


def kos(mod, gh, etsy=None, dr=None, onay=None, komut=None, ref="refs/heads/main", deneme="1", kanit="ping", ek=None, ad=None):
    """Tek 'kosu': secret'lar kosu basinda sahte GitHub'dan ortama alinir (is basinda sabitlenir). -> (cikis kodu, cikti)."""
    etsy = etsy or SahteEtsy({ESKI})
    SG.KANIT_UCU = kanit
    SG.SIRLAR.clear()
    SG.SAYAC.update(etsy=0, ok=0)
    SG.KOTA.update(kalan=None, son=None)
    UYKU.clear()
    SG.IS.update(dizin=None, depo=None)
    env = {"PATH": f"{araclar()}:{os.environ['PATH']}", "HOME": os.environ.get("HOME", "/tmp"), "MOD": mod,
           "ONAY": SG.onay_sozcugu(mod) if onay is None else onay, "GITHUB_REF": ref, "GITHUB_RUN_ATTEMPT": deneme,
           "GITHUB_REPOSITORY": "caliserdar-maker/astrolove-ops", "GITHUB_RUN_ID": "999", "RUNNER_TEMP": str(tmp("rt_")),
           "RCLONE_SAHTE_DRIVE": str(dr or drive()), "OPS_ADMIN_TOKEN": OPS, "GH_TOKEN": GHT, "ETSY_API_KEY": KEY}
    env.update({k: v["deger"] for k, v in gh.s.items() if k in (C, YD, YN)})
    env.update(ek or {})
    cikti = io.StringIO()
    with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(urllib.request, "urlopen", gh.ac), \
            mock.patch.object(SG, "http_get", etsy.get), mock.patch.object(E.requests, "post", etsy.post), \
            mock.patch.object(E.requests, "get", _ag_yok), mock.patch.object(E.requests, "put", _ag_yok), \
            mock.patch.object(E.requests, "request", _ag_yok), mock.patch.object(SG.time, "sleep", UYKU.append), \
            contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(cikti):
        rc = SG.calis([komut or mod])
    CIKTI.append((ad or mod, cikti.getvalue()))
    return rc, cikti.getvalue()


def gh3(canli=ESKI, yedek=ESKI, yeni=YENI, **k):
    s = {C: canli}
    if yedek:
        s[YD] = yedek
    if yeni:
        s[YN] = yeni
    return SahteGH(s, **k)


def kosu(dosya, durum="in_progress", olusturma="2026-11-01T00:00:00Z", no=5):
    return {"id": no, "status": durum, "path": f".github/workflows/{dosya}", "created_at": olusturma, "name": dosya}


def adim(ad):
    """Is akisindan adimin run govdesi (girinti kaldirilmis)."""
    sat = WF.read_text(encoding="utf-8").splitlines()
    i = next(k for k, x in enumerate(sat) if x.strip().startswith(f"- name: {ad}"))
    j = next(k for k in range(i + 1, len(sat)) if sat[k].strip().startswith("run:"))
    if sat[j].strip() != "run: |":
        return sat[j].strip()[5:] + "\n"
    g = len(sat[j]) - len(sat[j].lstrip())
    govde = []
    for x in sat[j + 1:]:
        if x.strip() and len(x) - len(x.lstrip()) <= g:
            break
        govde.append(x[g + 2:])
    return "\n".join(govde) + "\n"


def kabuk(ad, env):
    """Is akisi adimini GitHub'in kabuguyla (bash -e) ve alt surecte ag kapali + sahte GitHub ile kosar."""
    d = tmp("alt_")
    (d / "sitecustomize.py").write_text(
        f"import sys\nsys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\nimport test_secret_gecis as T\nT.alt_surec()\n")
    e = dict({"PATH": f"{araclar()}:{os.environ['PATH']}", "HOME": str(d), "PYTHONPATH": str(d), "GITHUB_REPOSITORY": "caliserdar-maker/astrolove-ops",
              "GITHUB_RUN_ID": "999", "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ENV": str(d / "_env"),
              "GITHUB_OUTPUT": str(d / "_out"), "GITHUB_WORKFLOW": "etsy-secret-gecis", "RUNNER_TEMP": str(d), "TMPDIR": str(d), "PYTHONDONTWRITEBYTECODE": "1",
              "RCLONE_SAHTE_DRIVE": str(d / "_drive")}, **env)
    r = subprocess.run(["bash", "-e", "-c", adim(ad)], cwd=KOK, env=e, capture_output=True, text=True, timeout=120)
    CIKTI.append((f"kabuk:{ad}", r.stdout + r.stderr))
    return r, d


def alt_surec():
    """sitecustomize ile alt surecte: ag zaten kapali (modul basi); GitHub taklidi (bos kosu listesi, 18 is akisi etkin)."""
    urllib.request.urlopen = SahteGH({C: ESKI}, kosular=[kosu(x) for x in (os.environ.get("SG_SAHTE_KOSU") or "").split(",") if x]).ac


def sizinti_bul(ciktilar):
    """'::add-mask::' satirlari disinda: bilinen degerlerin kendisi, ilk / son 4 karakteri, sha256, base64 bicimi; suzgecin izi (***);
    uzunluk / bayt bildiren satir. -> [(kosu adi, bicim)]"""
    out = []
    for ad, c in ciktilar:
        govde = "\n".join(x for x in c.splitlines() if not x.startswith("::add-mask::"))
        if "***" in govde:
            out.append((ad, "suzulmus deger"))
        if re.search(r"\d+ (bayt|karakter)\b|uzunlu", govde.replace("en az 12 karakter", "")):
            out.append((ad, "uzunluk"))
        if not ad.startswith("kabuk:") and re.search(rf"(?<![\w.:-]){len(ESKI)}(?![\w.:-])", govde):   # sabit test secret'larinin boyu (16) ciplak sayi olarak
            out.append((ad, "uzunluk (ciplak sayi)"))
        for v in SIR:
            if len(v) < 8:
                continue
            for bicim, x in (("deger", v), ("sha256", hashlib.sha256(v.encode()).hexdigest()), ("base64", base64.b64encode(v.encode()).decode())) + \
                    ((("ilk4", v[:4]), ("son4", v[-4:])) if v in SIR4 else ()):
                if x in govde:
                    out.append((ad, bicim))
    return out


def testler():  # noqa: C901
    t = []

    def ek(ad, kosul):
        t.append((ad, bool(kosul)))

    # ---------------- ortak kapi
    for ad, kw in (("onay yok", dict(onay="")), ("baska modun sozcugu", dict(onay="SERDAR_SECRET_YEDEK")), ("ref main degil", dict(ref="refs/heads/x")),
                   ("RUN_ATTEMPT 2", dict(deneme="2"))):
        g = gh3()
        rc, c = kos("degistir", g, **kw)
        ek(f"FAIL: kapi: {ad} -> DUR, canli degismedi", rc == 1 and "DUR" in c and g.s[C]["deger"] == ESKI and not [x for x in g.cagri if x[0] == "PUT"])
    rc, c = kos("yok_mod", gh3(), onay="SERDAR_SECRET_YOK_MOD", komut="kapi")
    ek("FAIL: kapi: mod listede degil", rc == 1 and "mod listede degil" in c)
    rc, c = kos("degistir", gh3(), komut="kapi")
    ek("PASS: kapi komutu", rc == 0 and "KAPI PASS: mod degistir" in c)
    rc, c = kos("degistir", gh3(), komut="dogrula")
    ek("FAIL: mod / komut uyusmuyor", rc == 1 and "uyusmuyor" in c)
    # ---------------- kanit ucu ayarsiz
    for mod in SG.KANITLI:
        g, e_ = gh3(), SahteEtsy({ESKI, YENI})
        rc, c = kos(mod, g, e_, kanit=None)
        ek(f"FAIL: kanit ucu AYARSIZ -> {mod} DUR, istek ve yazim yok", rc == 1 and "AYARSIZ" in c and not e_.cagri and not [x for x in g.cagri if x[0] != "GET"])
    ek("PASS: KANIT_UCU varsayilani kaynakta None", re.search(r"^KANIT_UCU = None\b", (KOK / "scripts/etsy/secret_gecis.py").read_text(), re.M) is not None)
    # ---------------- olc (E6 a)
    for ad, kw, bek in (("ikisi de dogruluyor", {}, "kanit ucu adayi: ping, oauth"), ("ping dogrulamiyor", dict(ping_dogrular=False), "kanit ucu adayi: oauth"),
                        ("hicbiri dogrulamiyor", dict(ping_dogrular=False, oauth_dogrular=False), "KANIT UCU YOK")):
        e_ = SahteEtsy({ESKI}, **kw)
        rc, c = kos("olc", gh3(), e_, kanit=None)
        ek(f"PASS: olc {ad}: sonuc satiri, cikis 0 (rastgele 200 FAIL degil)", rc == 0 and bek in c and "shared_secret alani DOLU; alan == ortam: EVET" in c
           and "secret en az 12 karakter: EVET" in c and "ucuncu dosya (ASTROLOVE/ETSY_TOKEN.json): YOK" in c and len(e_.cagri) == 12 and not e_.yenileme
           and "oauth yaniti kota basligi (x-remaining-today) tasiyor: EVET" in c and e_.cagri[0][0] == "/users/me")
    e_ = SahteEtsy({ESKI, FARKLI})
    rc, c = kos("olc", gh3(), e_, drive(alan=FARKLI, ucuncu=ESKI), kanit=None)
    ek("PASS: olc alan != ortam: HAYIR satiri + alan degeriyle ayri istek + ucuncu dosya VAR", rc == 0 and "alan == ortam: HAYIR" in c
       and "ping alan degeriyle: HTTP 200" in c and "ucuncu dosya (ASTROLOVE/ETSY_TOKEN.json): VAR" in c and len(e_.cagri) == 14
       and "5 rastgele secret: hepsi reddedildi (401 / 403): EVET" in c)
    e_ = SahteEtsy({ESKI}, ping_baslik=False)
    rc, c = kos("olc", gh3(), e_, kanit=None, ad="olc ping basliksiz")
    ek("PASS: olc: ping yaniti kota basligi tasimiyor -> satir HAYIR, olcum yine tamamlanir (once OAuth'lu GET)", rc == 0
       and "ping yaniti kota basligi (x-remaining-today) tasiyor: HAYIR" in c and "oauth yaniti kota basligi (x-remaining-today) tasiyor: EVET" in c)
    e_ = SahteEtsy({ESKI}, red=429)
    rc, c = kos("olc", gh3(), e_, kanit=None, ad="olc 429")
    ek("PASS: olc: rastgele secret 429 aliyor -> kanit ucu SAYILMAZ (401 / 403 disi kod ret degildir)", rc == 0 and "KANIT UCU YOK" in c
       and "hepsi reddedildi (401 / 403): HAYIR; 200 donen var: HAYIR" in c and "429" not in c)
    e_ = SahteEtsy({ESKI})
    d_ = drive(taze=False)
    rc, c = kos("olc", gh3(), e_, d_, kanit=None)
    ek("PASS: olc suresi dolmus token: tek yenileme + standart geri yazim", rc == 0 and len(e_.yenileme) == 1 and tok_oku(d_)["refresh_token"] == e_.refresh
       and tok_oku(d_).get("shared_secret") == ESKI)
    e_ = SahteEtsy({ESKI}, kalan=5)
    rc, c = kos("olc", gh3(), e_, kanit=None)
    ek("FAIL: kota tabani 10: kalan 5 -> ikinci istekten once DUR", rc == 1 and "kota sert tabani" in c and len(e_.cagri) == 1)
    e_ = SahteEtsy({ESKI}, kalan=None)
    rc, c = kos("olc", gh3(), e_, kanit=None, ad="olc kota basligi yok")
    ek("FAIL: kota basligi okunamiyor -> ikinci istekten once DUR", rc == 1 and "kota basligi" in c and len(e_.cagri) == 1)
    # ---------------- yedek / yedek_dogrula (E2)
    g = SahteGH({C: ESKI})
    rc, c = kos("yedek", g)
    ek("PASS: yedek: YEDEK = canli, updated_at kapisi", rc == 0 and g.s[YD]["deger"] == ESKI and g.s[C]["deger"] == ESKI)
    g = gh3(canli=YENI)                                # gecis icinde (degistir PASS sonrasi) yedek yeniden kosulursa
    rc, c = kos("yedek", g)
    ek("FAIL: yedek: YEDEK zaten VAR -> DUR, eski degerin kopyasi EZILMEDI", rc == 1 and "zaten VAR" in c and g.s[YD]["deger"] == ESKI
       and not [x for x in g.cagri if x[0] != "GET"])
    g = SahteGH({C: YENI, YN: YENI})
    rc, c = kos("yedek", g)
    ek("FAIL: yedek: canli == YENI (gecis icinde) -> DUR, YEDEK yazilmadi", rc == 1 and "canli == YENI" in c and YD not in g.s)
    g = gh3(bayat_meta=True)
    rc, c = kos("degistir", g, SahteEtsy({ESKI, YENI}), drive(alan=None), ad="degistir updated_at ilerlemedi")
    ek("FAIL: secret yazimi: updated_at ilerlemedi -> DUR (yazim dogrulanamadi)", rc == 1 and "updated_at dogrulanamadi" in c)
    g = SahteGH({C: ESKI}, meta_eksik=True)
    g.s[SG.KOD_AD] = {"deger": "onceki-kod-anahtari-00", "updated_at": "x"}
    rc, c = kos("kod_anahtari", g, ad="kod_anahtari meta eksik")
    ek("PASS: varlik updated_at'e bagli degil: meta alani donmese de VAR olan kod anahtari EZILMEZ", rc == 0 and "dokunulmadi" in c
       and g.s[SG.KOD_AD]["deger"] == "onceki-kod-anahtari-00")
    e_ = SahteEtsy({ESKI})
    rc, c = kos("yedek_dogrula", gh3(), e_)
    ek("PASS: yedek_dogrula: YEDEK == canli EVET + ONCE kanit YEDEK ile 200 (hedef secret) + 5 rastgele ret; istekler arasi 0,25 sn", rc == 0
       and "YEDEK == canli: EVET" in c and e_.cagri[0][1] == ESKI and len(e_.cagri) == 6 and UYKU == [SG.ARALIK_SN] * 5
       and "5 rastgele secret: hepsi reddedildi (401 / 403): EVET" in c)
    e_ = SahteEtsy({ESKI, YENI}, kalan=5, red_baslik=False)
    g = gh3()
    rc, c = kos("degistir", g, e_, drive(alan=None), ad="degistir kota 5, ret basliksiz")
    ek("FAIL: kota: ret yanitlari baslik tasimasa da ilk (pozitif) istek kotayi bildirir -> kalan 5 ise negatifler GITMEZ, canli degismez", rc == 1
       and "kota sert tabani" in c and len(e_.cagri) == 1 and g.s[C]["deger"] == ESKI)
    e_ = SahteEtsy({ESKI}, ping_baslik=False)
    rc, c = kos("yedek_dogrula", gh3(), e_, ad="yedek_dogrula ping basliksiz")
    ek("FAIL: yedek_dogrula: kanit ucu yaniti kota basligi tasimiyor -> DUR (gecise baslanmaz; dogrula ortada kalmaz)", rc == 1
       and "kota basligi tasimiyor" in c)
    e_ = SahteEtsy({ESKI}, red=429)
    rc, c = kos("yedek_dogrula", gh3(), e_, ad="yedek_dogrula 429")
    ek("FAIL: negatif kontrol: rastgele secret 401 / 403 disinda kod (429) aliyor -> DUR (belirsiz sonuc ret sayilmaz)", rc == 1 and "sonuc belirsiz" in c)
    kayit = []
    with mock.patch.object(SG._rastgele, "choice", lambda alfabe: (kayit.append(alfabe), "a")[1]):
        r = SG.rastgele_secretler(ESKI)
    ek("PASS: negatif kontroller: sabit uzunluklar, yalniz harf-rakam, secrets modulunden (gercek degerden turetilmez)",
       [len(x) for x in r] == list(SG.KONTROL_BOY) == [10, 12, 16, 24, 32] and set(kayit) == {SG.ALFABE} and SG.ALFABE.isalnum())
    rc, c = kos("yedek_dogrula", gh3(yedek=FARKLI), SahteEtsy({ESKI}))
    ek("FAIL: yedek_dogrula: YEDEK != canli", rc == 1 and "YEDEK == canli: HAYIR" in c)
    rc, c = kos("yedek_dogrula", SahteGH({C: ESKI}))
    ek("FAIL: yedek_dogrula: YEDEK yok", rc == 1 and "ortamda ETSY_SHARED_SECRET_YEDEK yok" in c)
    # ---------------- degistir
    g, e_, d_ = gh3(), SahteEtsy({ESKI, YENI}), drive()
    rc, c = kos("degistir", g, e_, d_)
    once = tok_oku(d_)
    ek("PASS: degistir: canli := YENI; dosya alani DOLU -> YENI; yalniz o alan degisti; kanit HEDEF (YENI) ile", rc == 0 and g.s[C]["deger"] == YENI
       and once["shared_secret"] == YENI and once["refresh_token"] == RT0 and e_.cagri[0][1] == YENI and not e_.yenileme
       and len(list((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir())) == 1)
    yedek_dosya = next((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir())
    ek("PASS: tarihli Drive yedegi eski alani tasiyor", json.loads(yedek_dosya.read_text())["shared_secret"] == ESKI)
    rc, c = kos("degistir", g, e_, d_)                 # yeni kosu: canli artik YENI
    ek("PASS: degistir yeniden kosu (canli zaten YENI, alan zaten YENI): ayni sonuc, yazim yok", rc == 0 and "secret yazimi atlandi" in c
       and "alan zaten hedef degerde" in c and g.s[C]["deger"] == YENI and tok_oku(d_) == once)
    g, e_, d_ = gh3(), SahteEtsy({ESKI, YENI}), drive()
    rc, c = kos("degistir", g, e_, d_, ek={"RCLONE_SAHTE_HATA": "TEMP/ETSY_TOKEN.json"})
    ek("FAIL: degistir kismi basari: secret yazildi, Drive yazimi dustu -> DUR", rc == 1 and g.s[C]["deger"] == YENI and tok_oku(d_)["shared_secret"] == ESKI
       and "YAZILAMADI" in c)
    rc, c = kos("degistir", g, e_, d_)
    ek("PASS: kismi basaridan sonra yeniden kosu ayni sonuca varir (kanit PASS, sonra dosya tamamlanir)", rc == 0 and g.s[C]["deger"] == YENI
       and tok_oku(d_)["shared_secret"] == YENI)
    for mod, g, e_, d_, alan in (("degistir", gh3(canli=YENI), SahteEtsy({ESKI}), drive(alan=ESKI), ESKI),      # YENI Etsy'de gecersiz (sira disi Cancel)
                                 ("geri_al", gh3(), SahteEtsy({YENI}), drive(alan=YENI), YENI)):               # YEDEK Etsy'de gecersiz (sira disi completed)
        rc, c = kos(mod, g, e_, d_, ad=f"{mod} kismi durum + hedef gecersiz")
        ek(f"FAIL: {mod}: canli zaten hedefte, dosya alani calisan degerde, hedef Etsy'de GECERSIZ -> DUR; dosya alani gecersiz degere CEKILMEZ",
           rc == 1 and tok_oku(d_)["shared_secret"] == alan and len(e_.cagri) == 1 and not (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").exists())
    g, e_, d_ = gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=ESKI, taze=False)
    rc, c = kos("degistir", g, e_, d_, kanit="oauth", ad="degistir oauth kismi basari + suresi dolmus")
    ek("FAIL: OAuth ucu + kismi basari + suresi dolmus token -> DUR; kanitsiz ne yenileme ne dosya yazimi", rc == 1 and tok_oku(d_)["shared_secret"] == ESKI
       and "access token suresi dolmus" in c and not e_.yenileme and not e_.cagri)
    x = tok_oku(d_)                                             # baska bir Etsy kosusu token'i (dosyadaki eski alanla) tazeledi
    x["obtained_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN.json").write_text(json.dumps(x, indent=2) + "\n")
    rc, c = kos("degistir", g, e_, d_, kanit="oauth", ad="degistir oauth kismi basari + taze token")
    ek("PASS: ... token tazelendikten sonra yeniden kosu: kanit PASS, dosya alani YENI (cikmaz yok)", rc == 0 and tok_oku(d_)["shared_secret"] == YENI)
    adlar = (d_ / "_ortam_adlari").read_text().split()
    ek("PASS: alt surece (rclone) sir ortami DEVREDILMEZ (OPS_ADMIN_TOKEN, GH_TOKEN, ETSY_* yok)", adlar and "PATH" in adlar
       and not [a for a in adlar if a in ("OPS_ADMIN_TOKEN", "GH_TOKEN", "ONAY") or a.startswith("ETSY_")])
    g, d_ = gh3(), drive(alan=None)
    rc, c = kos("degistir", g, SahteEtsy({ESKI, YENI}), d_)
    ek("PASS: degistir: alan BOS -> dosyaya dokunulmaz", rc == 0 and g.s[C]["deger"] == YENI and "alan BOS, dokunulmadi" in c
       and not (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").exists())
    for uc in ("ping", "oauth"):
        e_ = SahteEtsy({ESKI, YENI, FARKLI})
        rc, c = kos("yedek_dogrula", gh3(), e_, drive(alan=FARKLI), kanit=uc, ad=f"E7 {uc}")
        ek(f"PASS: E7 ({uc}): dosya alani farkliyken kanit istegi HEDEF secret'la gider (alan degeri hic gonderilmez)", rc == 0 and e_.cagri
           and e_.cagri[0][1] == ESKI and FARKLI not in [x[1] for x in e_.cagri] and not e_.yenileme)
    for ad, g, e_, d_, kanit in (
            ("YENI bos", gh3(yeni=None), None, None, "ping"), ("YENI bosluklu", gh3(yeni="Hn4t YENIb6Rc"), None, None, "ping"),
            ("YENI == YEDEK", gh3(yeni=ESKI), None, None, "ping"), ("YEDEK yok", gh3(yedek=None), None, None, "ping"),
            ("canli ne YEDEK ne YENI", gh3(canli=FARKLI), SahteEtsy({ESKI, YENI, FARKLI}), None, "ping"),
            ("kanit ucu rastgele secret'la 200", gh3(), SahteEtsy({ESKI, YENI}, ping_dogrular=False), None, "ping"),
            ("YENI Etsy'de gecersiz (kanit 200 degil)", gh3(), SahteEtsy({ESKI}), None, "ping"),
            ("dosya alani ne eski ne yeni", gh3(), SahteEtsy({ESKI, YENI}), drive(alan=FARKLI), "ping"),
            ("18'den birinde aktif kosu", gh3(kosular=[kosu("seo51.yml")]), SahteEtsy({ESKI, YENI}), None, "ping"),
            ("aktif kosu listesi tek sayfaya sigmiyor", gh3(toplam=150), SahteEtsy({ESKI, YENI}), None, "ping"),
            ("ucuncu dosyada alan DOLU (eski)", gh3(), SahteEtsy({ESKI, YENI}), drive(alan=None, ucuncu=ESKI), "ping"),
            ("rastgele secret 429 aliyor", gh3(), SahteEtsy({ESKI, YENI}, red=429), None, "ping"),
            ("OAuth kanit ucu, access token suresi dolmus", gh3(), SahteEtsy({ESKI, YENI}), drive(taze=False), "oauth"),
            ("OAuth kanit ucu: 401 (bearer gecersiz)", gh3(), SahteEtsy({ESKI, YENI}), None, "oauth401")):
        e_ = e_ or SahteEtsy({ESKI, YENI})
        d_ = d_ or drive()
        if kanit == "oauth401":
            e_.bearer, kanit = "baska-bearer-000000", "oauth"
        once = (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN.json").read_text()
        rc, c = kos("degistir", g, e_, d_, kanit=kanit, ad=f"degistir FAIL {ad}")
        ek(f"FAIL: degistir: {ad} -> DUR; canli ve token dosyasi degismedi; yenileme yok", rc == 1 and "DUR" in c and g.s[C]["deger"] != YENI
           and (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN.json").read_text() == once and not [x for x in g.cagri if x[0] == "PUT"] and not e_.yenileme)
    # ---------------- alan disi degisiklik / refresh_token kapilari (geri okuma)
    for ad, bozucu in (("baska alan degisti", lambda d: d.update(scope="baska")), ("refresh_token degisti", lambda d: d.update(refresh_token="rtX-Qq11Ww22Ee33Rr"))):
        g, d_ = gh3(), drive()
        gercek = SG.rclone

        def bozan(*a, _b=bozucu, _d=d_):
            r = gercek(*a)
            if a[0] == "copyto" and a[2] == SG.TOKEN_UZAK:           # yuklemeden hemen sonra "baska bir kosu" dosyayi degistirir
                x = tok_oku(_d)
                _b(x)
                (_d / "ASTROLOVE/TEMP/ETSY_TOKEN.json").write_text(json.dumps(x))
            return r
        with mock.patch.object(SG, "rclone", bozan):
            rc, c = kos("degistir", g, SahteEtsy({ESKI, YENI}), d_, ad=f"degistir {ad}")
        ek(f"FAIL: geri okuma: {ad} -> DUR", rc == 1 and "geri okuma FAIL" in c)
    # ---------------- dogrula / tamam_kapisi / tamam_kontrol
    g, e_, d_ = gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=YENI)
    rc, c = kos("dogrula", g, e_, d_)
    ek("PASS: dogrula: esitlik satirlari EVET + kanit canli 200 + zincir testi (1 yenileme, geri yazim)", rc == 0 and ": HAYIR" not in c and "canli == YENI: EVET" in c
       and "canli != YEDEK: EVET" in c and "kanit ucu canli: HTTP 200" in c and len(e_.yenileme) == 1
       and tok_oku(d_)["refresh_token"] == e_.refresh and tok_oku(d_)["shared_secret"] == YENI)
    for ad, g, d_ in (("canli != YENI", gh3(), drive(alan=None)), ("dosya alani eski", gh3(canli=YENI), drive(alan=ESKI)),
                      ("ucuncu dosya eski alanli", gh3(canli=YENI), drive(alan=None, ucuncu=ESKI))):
        e_ = SahteEtsy({ESKI, YENI})
        rc, c = kos("dogrula", g, e_, d_, ad=f"dogrula FAIL {ad}")
        ek(f"FAIL: dogrula: {ad} -> DUR, Etsy istegi ve yenileme yok", rc == 1 and ": HAYIR" in c and not e_.cagri and not e_.yenileme)
    e_ = SahteEtsy({ESKI, YENI}, yenileme_kodu=401)
    rc, c = kos("dogrula", gh3(canli=YENI), e_, drive(alan=None))
    ek("FAIL: dogrula: token yenileme 401 -> DUR (govde yazilmaz)", rc == 1 and "token yenileme basarisiz (HTTP 401)" in c and "invalid_grant" not in c)
    e_ = SahteEtsy({ESKI, YENI})
    e_.bearer = "baska-bearer-000000"
    rc, c = kos("dogrula", gh3(canli=YENI), e_, drive(alan=None), kanit="oauth")
    ek("FAIL: 401'de kendiliginden yenileme yok (sonuc 401 yazilir)", rc == 1 and "HTTP 401" in c and not e_.yenileme)
    yazim = "2026-11-12T10:00:00Z"
    for ad, kosular, bek in (("aktif eski kosu yok", [], 0), ("kilitsiz Etsy is akisinda (etsy-kota) aktif eski kosu", [kosu("etsy-kota.yml", olusturma="2026-11-12T09:59:00Z")], 1),
                             ("aktif ama yazimdan 6 dk SONRA baslamis", [kosu("etsy-kota.yml", olusturma="2026-11-12T10:06:00Z")], 0),
                             ("aktif, yazimdan 3 dk sonra baslamis (5 dk pay icinde)", [kosu("etsy-kota.yml", olusturma="2026-11-12T10:03:00Z")], 1),
                             ("yol sonunda @ref olan aktif eski kosu", [dict(kosu("etsy-kota.yml", olusturma="2026-11-12T09:00:00Z"),
                                                                           path=".github/workflows/etsy-kota.yml@refs/heads/main")], 1),
                             ("Etsy'siz is akisi aktif", [kosu("ig-publish.yml", olusturma="2026-11-12T09:00:00Z")], 0)):
        g = gh3(canli=YENI, kosular=kosular)
        g.s[C]["updated_at"] = yazim
        rc, c = kos("tamam_kapisi", g, None, drive(alan=None), ad=f"tamam_kapisi {ad}")
        ek(f"{'FAIL' if bek else 'PASS'}: tamam_kapisi: {ad}", rc == bek and ("kosusu YOK: HAYIR (etsy-kota.yml)" in c) == bool(bek))
    g, d_ = gh3(canli=YENI, kosular=[kosu("etsy-kota.yml", olusturma="2026-11-12T10:17:00Z")]), drive(alan=YENI)
    g.s[C]["updated_at"] = yazim
    (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").mkdir()
    (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK/ETSY_TOKEN_20261112T101500Z.json").write_text("{}")
    rc, c = kos("tamam_kapisi", g, None, d_, ad="tamam_kapisi gec alan yazimi")
    ek("FAIL: tamam_kapisi: dosya alani gec yazilmis (10:15), arada baslamis (10:17) aktif kosu ESKI sayilir", rc == 1 and "(etsy-kota.yml)" in c)
    g = gh3(canli=YENI)
    rc, c = kos("tamam_kapisi", g, None, drive(alan=ESKI))
    ek("FAIL: tamam_kapisi: dosya alani eski (yaris)", rc == 1 and "alani beklenen durumda: HAYIR" in c)
    e_, d_ = SahteEtsy({YENI}), drive(alan=None)
    rc, c = kos("tamam_kontrol", gh3(canli=YENI), e_, d_)
    ek("PASS: tamam_kontrol: eski reddediliyor, canli 200, zincir, OAuth GET 200", rc == 0 and "YEDEK (eski): HTTP 403" in c and len(e_.yenileme) == 1
       and e_.cagri[-1] == ("/users/me", YENI, True))
    e_ = SahteEtsy({ESKI, YENI})
    rc, c = kos("tamam_kontrol", gh3(canli=YENI), e_, drive(alan=None))
    ek("FAIL: tamam_kontrol: eski hala 200 -> DUR, TEK okuma (bekleme yok), yenileme yok", rc == 1 and "eski secret hala 200" in c and not e_.yenileme
       and len(e_.cagri) == 2 and [x[1] for x in e_.cagri] == [YENI, ESKI])
    for ad, g, d_ in (("dosya alani eski (yanlis secret'la yenileme olurdu)", gh3(canli=YENI), drive(alan=ESKI)), ("canli == YEDEK", gh3(), drive(alan=None))):
        e_ = SahteEtsy({ESKI, YENI})
        rc, c = kos("tamam_kontrol", g, e_, d_, ad=f"tamam_kontrol FAIL {ad}")
        ek(f"FAIL: tamam_kontrol: {ad} -> DUR, Etsy istegi ve yenileme yok", rc == 1 and not e_.cagri and not e_.yenileme)
    # ---------------- yanlis secret'la token yenileme denenmez
    e_, d_ = SahteEtsy({ESKI, FARKLI}), drive(alan=FARKLI, taze=False)
    rc, c = kos("olc", gh3(), e_, d_, kanit=None, ad="olc alan != ortam + suresi dolmus")
    ek("PASS: olc: alan != ortam ve token suresi dolmus -> oauth OLCULMEDI, yenileme YOK, ping olculdu", rc == 0 and "SONUC oauth: OLCULMEDI" in c
       and not e_.yenileme and {x[0] for x in e_.cagri} == {"/openapi-ping"} and tok_oku(d_)["refresh_token"] == RT0)
    e_, d_ = SahteEtsy({ESKI, YENI}), drive(alan=FARKLI, taze=False)
    rc, c = kos("yedek_dogrula", gh3(), e_, d_, kanit="oauth", ad="oauth kanit: alan != canli + suresi dolmus")
    ek("FAIL: OAuth kanit ucu: dosya alani != canli ve token suresi dolmus -> DUR, yenileme istegi GITMEZ", rc == 1 and "yenileme denenmez" in c
       and not e_.yenileme and not e_.cagri)
    e_, d_ = SahteEtsy({ESKI, YENI}), drive(alan=ESKI)
    rc, c = kos("dogrula", gh3(canli=YENI), e_, drive(alan=None), ad="dogrula zincir oncesi")
    try:
        with mock.patch.dict(os.environ, {"ETSY_API_KEY": KEY, "MOD": "dogrula", "PATH": f"{araclar()}:{os.environ['PATH']}", "RCLONE_SAHTE_DRIVE": str(d_)}), \
                mock.patch.object(E.requests, "post", e_.post), contextlib.redirect_stdout(io.StringIO()):
            SG.IS.update(dizin=None, depo=None)
            SG.yenile(SG.depo(YENI), YENI)                  # dosya alani ESKI, canli YENI: TokenStore ESKI'yi secerdi
        sonuc = False
    except SG.Dur as e:
        sonuc = "yenileme denenmez" in str(e) and len(e_.yenileme) == 1      # 1 = yukaridaki dogrula'nin zincir testi; bu cagri istek atmadi
    finally:
        if SG.IS["dizin"]:
            shutil.rmtree(SG.IS["dizin"], ignore_errors=True)
            SG.IS.update(dizin=None, depo=None)
    ek("FAIL: yenile(): TokenStore'un sececegi secret canliya esit degil -> DUR, istek gitmez", sonuc)
    for mod, g, e_, d_, bek in (
            ("yedek_dogrula", gh3(), SahteEtsy({ESKI}), drive(), 6),
            ("degistir", gh3(), SahteEtsy({ESKI, YENI}), drive(), 6),
            ("dogrula", gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=YENI), 7),
            ("tamam_kontrol", gh3(canli=YENI), SahteEtsy({YENI}), drive(alan=None), 8),
            ("geri_al", gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=YENI), 6),
            ("geri_dogrula", gh3(), SahteEtsy({ESKI, YENI}), drive(), 6),
            ("temizle", gh3(canli=YENI), SahteEtsy({YENI}), drive(alan=None), 7),
            ("temizle_drive", SahteGH({C: YENI}), SahteEtsy({YENI}), drive(alan=None), 6)):
        rc, c = kos(mod, g, e_, d_, kanit="oauth", ad=f"oauth {mod}")
        n = len(e_.cagri) + len(e_.yenileme)
        ek(f"PASS: OAuth kanit ucu: {mod} PASS, Etsy istegi {bek} (sinir {SG.MODLAR[mod]})", rc == 0 and n == bek <= SG.MODLAR[mod]
           and all(x[0] == "/users/me" and x[2] for x in e_.cagri) and f"Etsy istegi {bek}" in c)
    for mod, g, e_, d_ in (("yedek_dogrula", gh3(), SahteEtsy({ESKI}), drive()), ("degistir", gh3(), SahteEtsy({ESKI, YENI}), drive()),
                           ("dogrula", gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=YENI)), ("tamam_kontrol", gh3(canli=YENI), SahteEtsy({YENI}), drive(alan=None)),
                           ("temizle", gh3(canli=YENI), SahteEtsy({YENI}), drive(alan=None))):
        rc, c = kos(mod, g, e_, d_, ad=f"ping {mod} sinir")
        n = len(e_.cagri) + len(e_.yenileme)
        ek(f"PASS: ping kanit ucu: {mod} PASS, Etsy istegi mod siniri icinde ({n} <= {SG.MODLAR[mod]})", rc == 0 and n <= SG.MODLAR[mod])
    for mod, g, e_ in (("tamam_kontrol", gh3(canli=YENI), SahteEtsy({ESKI})), ("geri_dogrula", gh3(), SahteEtsy({YENI}))):
        d_ = drive(alan=None, taze=False)                   # canli Etsy'de GECERSIZ (panelde yanlislikla Cancel / completed) + suresi dolmus token
        rc, c = kos(mod, g, e_, d_, kanit="oauth", ad=f"oauth {mod} gecersiz canli")
        ek(f"FAIL: OAuth ucu: {mod}, canli gecersiz ve token suresi dolmus -> DUR; gecerliligi kanitlanmamis secret'la yenileme GITMEZ", rc == 1
           and not e_.yenileme and "access token suresi dolmus" in c)
    # ---------------- alan yazimi: indirme ile yukleme arasinda dosya degisti
    g, d_ = gh3(), drive()
    gercek = SG.rclone
    durum = {"n": 0}

    def araya_giren(*a, _d=d_):
        if a[0] == "copyto" and a[1] == SG.TOKEN_UZAK and a[2].endswith("yukleme_oncesi.json"):
            x = tok_oku(_d)
            x.update(refresh_token="rtY-baska-kosu-yazdi-11", access_token="atY-baska-kosu-yazdi-11")
            (_d / "ASTROLOVE/TEMP/ETSY_TOKEN.json").write_text(json.dumps(x))
            durum["n"] += 1
        return gercek(*a)
    SIR.update({"rtY-baska-kosu-yazdi-11", "atY-baska-kosu-yazdi-11"})
    with mock.patch.object(SG, "rclone", araya_giren):
        rc, c = kos("degistir", g, SahteEtsy({ESKI, YENI}), d_, ad="degistir araya giren kosu")
    ek("FAIL: alan yazimi: indirme ile yukleme arasinda baska kosu dosyayi yazdi -> DUR, onun yazdigi token EZILMEDI", rc == 1 and durum["n"] == 1
       and "arasinda degisti" in c and tok_oku(d_)["refresh_token"] == "rtY-baska-kosu-yazdi-11" and tok_oku(d_)["shared_secret"] == ESKI)
    # ---------------- geri al / geri dogrulama (E1)
    g, e_, d_ = gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=YENI)
    rc, c = kos("geri_al", g, e_, d_)
    ek("PASS: geri_al: canli := YEDEK; dosya alani YENI -> YEDEK; kanit YEDEK ile", rc == 0 and g.s[C]["deger"] == ESKI and tok_oku(d_)["shared_secret"] == ESKI
       and e_.cagri[0][1] == ESKI)
    rc, c = kos("geri_dogrula", g, e_, d_)
    ek("PASS: geri_dogrula: canli == YEDEK EVET, alan beklenen, kanit YEDEK 200", rc == 0 and "canli == YEDEK: EVET" in c)
    g, e_ = gh3(canli=YENI), SahteEtsy({YENI})
    rc, c = kos("geri_al", g, e_, drive(alan=None))
    ek("FAIL: geri_al: YEDEK Etsy'de artik gecersiz -> DUR, canli degismedi", rc == 1 and g.s[C]["deger"] == YENI)
    for mod in ("geri_al", "geri_dogrula"):                 # YUKSEK 1: yedek gecis icinde ezilmisse geri donus "PASS" DEMEZ
        g, e_ = gh3(canli=YENI, yedek=YENI), SahteEtsy({ESKI, YENI})
        rc, c = kos(mod, g, e_, drive(alan=None), ad=f"{mod} YEDEK == YENI")
        ek(f"FAIL: {mod}: YEDEK == YENI (eski deger YEDEK'te yok) -> DUR, Etsy istegi yok", rc == 1 and not e_.cagri and g.s[C]["deger"] == YENI
           and ("YENI == YEDEK" in c or "YEDEK != YENI (YEDEK eski degeri tasiyor): HAYIR" in c))
    g, e_, d_ = SahteGH({C: YENI, YD: ESKI}), SahteEtsy({ESKI, YENI}), drive(alan=None)
    rc, c = kos("geri_al", g, e_, d_, ad="geri_al YENI silinmis")
    ek("PASS: geri_al: YENI secret'i silinmis / yeniden girilmis olsa da canli := YEDEK (geri donus yolu gereksiz DUR vermez)", rc == 0
       and g.s[C]["deger"] == ESKI and e_.cagri[0][1] == ESKI)
    for ad, alan in (("onceki canli (YENI secret'i silinmis)", YENI), ("taninmayan deger", FARKLI)):
        g, e_, d_ = SahteGH({C: YENI, YD: ESKI}), SahteEtsy({ESKI, YENI}), drive(alan=alan)
        rc, c = kos("geri_al", g, e_, d_, ad=f"geri_al alan {ad}")
        yedek_dosya = list((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir())
        rc2, c2 = kos("geri_dogrula", g, e_, d_, ad=f"geri_dogrula alan {ad}")
        ek(f"PASS: geri_al: dosya alani {ad} -> canli ve alan kanitlanmis YEDEK'e alinir (onceki hali yedekte); geri_dogrula PASS (cikmaz yok)",
           rc == 0 and g.s[C]["deger"] == ESKI and tok_oku(d_)["shared_secret"] == ESKI and len(yedek_dosya) == 1
           and json.loads(yedek_dosya[0].read_text())["shared_secret"] == alan and rc2 == 0)
    for ad, g, d_ in (("canli != YEDEK", gh3(canli=YENI), drive(alan=None)), ("dosya alani beklenmeyen durumda", gh3(), drive(alan=YENI))):
        e_ = SahteEtsy({ESKI, YENI})
        rc, c = kos("geri_dogrula", g, e_, d_, ad=f"geri_dogrula FAIL {ad}")
        ek(f"FAIL: geri_dogrula: {ad} -> DUR, Etsy istegi yok", rc == 1 and ": HAYIR" in c and not e_.cagri)
    # ---------------- alan_sil / alan_geri
    d_ = drive()
    rc, c = kos("alan_sil", gh3(), SahteEtsy({ESKI}), d_)
    ek("PASS: alan_sil: alan == canli -> kaldirildi, refresh_token ayni, yedek alindi", rc == 0 and "shared_secret" not in tok_oku(d_) and tok_oku(d_)["refresh_token"] == RT0
       and len(list((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir())) == 1)
    rc, c = kos("alan_sil", gh3(), SahteEtsy({ESKI}), d_)
    ek("PASS: alan_sil 'zaten yok'", rc == 0 and "alan zaten yok: PASS" in c and len(list((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir())) == 1)
    rc, c = kos("alan_geri", gh3(), SahteEtsy({ESKI}), d_)
    ek("PASS: alan_geri: alan canli degerle geri kondu", rc == 0 and tok_oku(d_)["shared_secret"] == ESKI)
    d_ = drive(alan=FARKLI)
    once = (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN.json").read_text()
    rc, c = kos("alan_sil", gh3(), SahteEtsy({ESKI}), d_)
    ek("FAIL: alan != canli iken alan_sil -> DUR, dosya degismedi", rc == 1 and "alan == canli: HAYIR" in c and (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN.json").read_text() == once)
    rc, c = kos("alan_geri", gh3(canli=YENI), SahteEtsy({ESKI, YENI}), drive(alan=None))
    ek("FAIL: alan_geri: canli != YEDEK (gecis icinde) -> DUR", rc == 1 and "canli YEDEK'e esit degil" in c)
    # ---------------- kapat / ac (K3)
    ek("PASS: kapat listesi = 18 ad (Dayanak 1)", SG.KAPAT == ("gorsel-denetim", "wp-pdf-probe", "wp-saat80-ornek", "wp-share-mockups", "by-taslak-hazirlik",
       "etsy-ai-scan", "etsy-quota-probe", "etsy-ru-probe", "etsy-state-probe", "ig-ilan-dogrula", "pw-ru-probe", "urun-gorsel-cl", "gorsel02", "gorsel19",
       "seo51", "pin-v6", "dijital-donusum-uygula", "pod-arac-v4") and all((KOK / f".github/workflows/{a}.yml").exists() for a in SG.KAPAT))
    g = SahteGH({C: ESKI}, kapali=("seo51",))
    rc, c = kos("kapat", g)
    ek("PASS: kapat: 17 etkin kapatildi, onceden kapali kayda girmedi", rc == 0 and all(v != "active" for v in g.wf.values())
       and len(g.v[SG.DEGISKEN].split(",")) == 17 and "seo51" not in g.v[SG.DEGISKEN].split(","))
    kayit = g.v[SG.DEGISKEN]
    rc, c = kos("kapat", g)
    ek("PASS: ikinci kapat kaydi ezmez", rc == 0 and g.v[SG.DEGISKEN] == kayit)
    rc, c = kos("ac", g)
    ek("PASS: ac: yalniz kayittakiler acildi; onceden kapali is akisi ACILMADI", rc == 0 and g.wf["seo51.yml"] == "disabled_manually"
       and sum(v == "active" for v in g.wf.values()) == 17 and g.v[SG.DEGISKEN] == "-")
    rc, c = kos("ac", g, onay="SERDAR_SECRET_KAPAT")
    ek("FAIL: ac kapat'in sozcuguyle kosmaz", rc == 1)
    g = SahteGH({C: ESKI}, yazma_yok=True)
    rc, c = kos("kapat", g)
    ek("FAIL: kapat: yetki yok -> DUR", rc == 1 and "hala etkin" in c)
    # ---------------- kod anahtari (K2)
    g = SahteGH({C: ESKI})
    rc, c = kos("kod_anahtari", g)
    anahtar = g.s.get(SG.KOD_AD, {}).get("deger", "")
    ek("PASS: kod_anahtari: yokken rastgele (>= 32 bayt) yazildi, gercek degerden turetilmedi", rc == 0 and len(base64.urlsafe_b64decode(anahtar + "=" * (-len(anahtar) % 4))) >= 32
       and ESKI not in anahtar)
    rc, c = kos("kod_anahtari", g)
    ek("PASS: kod_anahtari VARKEN uzerine yazilmaz", rc == 0 and "dokunulmadi" in c and g.s[SG.KOD_AD]["deger"] == anahtar)
    # ---------------- prova (E3, E4)
    g = SahteGH({C: ESKI, SG.DENEME_AD: "anlamsiz-deneme-1"})
    rt = str(tmp("prova_"))
    rc, c = kos("prova", g, ek={"RUNNER_TEMP": rt})
    ek("PASS: prova: deneme girisi VAR ve silindi; iki yazim; is akisi kapatma yetkisi; canli DEGISMEDI", rc == 0 and SG.DENEME_AD not in g.s
       and SG.PROVA_AD in g.s and g.s[C]["deger"] == ESKI and g.wf[SG.PROVA_WF] == "disabled_manually" and ("PUT", f"secrets/{C}") not in g.cagri
       and g.cagri.count(("PUT", f"secrets/{SG.PROVA_AD}")) == 2)
    rc, c = kos("prova", g, komut="prova_son", ek={"RUNNER_TEMP": rt}, ad="prova_son")
    ek("PASS: prova_son: is akisi onceki durumuna dondu, ETSY_SECRET_PROVA silindi, adim ortami BOS", rc == 0 and g.wf[SG.PROVA_WF] == "active"
       and SG.PROVA_AD not in g.s and "BOS (deger is basinda sabitlenmis)" in c and not os.path.exists(os.path.join(rt, "secret_gecis_prova.json")))
    rc, c = kos("prova", SahteGH({C: ESKI}))
    ek("FAIL: prova: Serdar'in deneme girisi YOK -> DUR", rc == 1 and "ETSY_SECRET_DENEME) VAR: HAYIR" in c)
    g = SahteGH({C: ESKI, SG.DENEME_AD: "anlamsiz-deneme-4"})
    rt = str(tmp("prova_"))
    rc, c = kos("prova", g, ek={"RUNNER_TEMP": rt}, ad="prova (silme hatasi oncesi)")
    g.silme_hata.add(SG.PROVA_AD)
    rc2, c2 = kos("prova", g, komut="prova_son", ek={"RUNNER_TEMP": rt}, ad="prova_son silme hatasi")
    ek("FAIL: prova_son: secret silme hata verse de is akisi onceki durumuna DONER; kayit dosyasi silinir; cikis 1", rc == 0 and rc2 == 1
       and g.wf[SG.PROVA_WF] == "active" and "silindi): HAYIR" in c2 and not os.path.exists(os.path.join(rt, "secret_gecis_prova.json")))
    g = SahteGH({C: ESKI, SG.DENEME_AD: "anlamsiz-deneme-2"}, bayat_meta=True)
    g.s[SG.PROVA_AD] = {"deger": "eski-prova-artik-00", "updated_at": "2026-11-01T00:00:00Z"}
    rc, c = kos("prova", g, ad="prova updated_at ilerlemiyor")
    ek("FAIL: prova: updated_at ilerlemiyor -> DUR (yazma yetkisi kanitlanmadi)", rc == 1)
    g = SahteGH({C: ESKI, SG.DENEME_AD: "anlamsiz-deneme-3"})
    g.wf[SG.PROVA_WF] = "disabled_inactivity"
    rt = str(tmp("prova_"))
    rc, c = kos("prova", g, ek={"RUNNER_TEMP": rt}, ad="prova disabled_inactivity")
    rc2, c2 = kos("prova", g, komut="prova_son", ek={"RUNNER_TEMP": rt}, ad="prova_son disabled_inactivity")
    ek("FAIL: prova: is akisi durumu active / disabled_manually degil -> hic dokunmadan DUR; prova_son temiz biter", rc == 1 and rc2 == 0
       and g.wf[SG.PROVA_WF] == "disabled_inactivity" and not [x for x in g.cagri if x[0] != "GET"] and SG.DENEME_AD in g.s)
    # ---------------- temizle
    g, e_, d_ = gh3(canli=YENI), SahteEtsy({YENI}), drive(alan=None)
    (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").mkdir()
    (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK/ETSY_TOKEN_20261112T100000Z.json").write_text("{}")
    (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN_ONCEKI_20261101_1000.json").write_text("{}")
    g.s[SG.DENEME_AD] = {"deger": "x-deneme-000", "updated_at": "x"}
    rc, c = kos("temizle", g, e_, d_)
    ek("PASS: temizle: YEDEK / YENI / DENEME silindi, canli duruyor, Drive yedekleri yalniz LISTELENDI (bayt YAZILMAZ)", rc == 0 and set(g.s) == {C}
       and c.count("yalniz liste") == 2 and "bayt" not in c and (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK/ETSY_TOKEN_20261112T100000Z.json").exists())
    for ad, g, e_, ek_ in (("canli == YEDEK ama YENI Etsy'de hala gecerli (Cancel denmemis)", gh3(), SahteEtsy({ESKI, YENI}), None),
                           ("canli == YEDEK ama canli Etsy'de gecersiz", gh3(), SahteEtsy({YENI}), None),
                           ("Drive listesi okunamiyor", gh3(canli=YENI), SahteEtsy({YENI}), {"RCLONE_SAHTE_LS_HATA": "1"})):
        rc, c = kos("temizle", g, e_, drive(alan=None), ek=ek_, ad=f"temizle FAIL {ad}")
        ek(f"FAIL: temizle: {ad} -> DUR, hicbir sey silinmedi", rc == 1 and YD in g.s and YN in g.s and not [x for x in g.cagri if x[0] == "DELETE"])
    g, e_, d2 = gh3(), SahteEtsy({ESKI}), drive(alan=None)             # geri donus tamam: canli == YEDEK, YENI panelde iptal edilmis
    rc, c = kos("temizle", g, e_, d2, ad="temizle geri donus dali")
    rc2, c2 = kos("temizle_drive", g, e_, d2, ad="temizle_drive geri donus sonrasi")
    ek("PASS: temizle: geri donus dali (canli == YEDEK 200, YENI reddediliyor) -> gecici secret'lar silinir; temizle_drive kosabilir (cikmaz yok)",
       rc == 0 and set(g.s) == {C} and "geri donus dali" in c and len(e_.cagri) - 6 == 7 and rc2 == 0)
    g = gh3(canli=YENI, silme_hata={YN})
    rc, c = kos("temizle", g, SahteEtsy({YENI}), drive(alan=None), ad="temizle YENI silinemiyor")
    g.silme_hata.clear()
    rc2, c2 = kos("temizle", g, SahteEtsy({YENI}), drive(alan=None), ad="temizle yeniden kosu")
    ek("FAIL: temizle: bir gecici secret silinemedi -> DUR ve YEDEK DURUR (en son silinir); yeniden kosu tamamlar", rc == 1 and rc2 == 0 and set(g.s) == {C}
       and "ETSY_SHARED_SECRET_YEDEK: silinmedi" in c)
    for ad, g, ek_ in (("YEDEK secret'i duruyor (gecis bitmemis)", gh3(canli=YENI), None), ("Drive listesi okunamiyor", SahteGH({C: YENI}), {"RCLONE_SAHTE_LS_HATA": "1"}),
                       ("silme basarisiz", SahteGH({C: YENI}), {"RCLONE_SAHTE_SIL_HATA": "1"})):
        rc, c = kos("temizle_drive", g, SahteEtsy({YENI}), d_, ek=ek_, ad=f"temizle_drive FAIL {ad}")
        ek(f"FAIL: temizle_drive: {ad} -> DUR (PASS degil), yedek duruyor", rc == 1
           and (d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK/ETSY_TOKEN_20261112T100000Z.json").exists())
    g = gh3(canli=YENI)
    rc, c = kos("temizle", g, SahteEtsy({ESKI, YENI}), drive(alan=None))
    ek("FAIL: temizle tamam kontrol PASS degilken (eski hala 200) hicbir sey silmez", rc == 1 and set(g.s) == {C, YD, YN} and not [x for x in g.cagri if x[0] == "DELETE"])
    rc, c = kos("temizle_drive", SahteGH({C: YENI}), SahteEtsy({YENI}), d_)
    ek("PASS: temizle_drive: yalniz bu betigin yedek klasoru kalici silindi; ONCEKI yalniz listelendi", rc == 0
       and not list((d_ / "ASTROLOVE/TEMP/SECRET_GECIS_YEDEK").iterdir()) and (d_ / "ASTROLOVE/TEMP/ETSY_TOKEN_ONCEKI_20261101_1000.json").exists())
    # ---------------- gh_secrets: silme izin listesi
    for ad in ("ETSY_SHARED_SECRET", "SIPARIS_KOD_ANAHTARI", "OPS_ADMIN_TOKEN"):
        g = SahteGH({ad: "x"})
        try:
            with mock.patch.object(urllib.request, "urlopen", g.ac):
                GS.delete_secret("astrolove-ops", ad, OPS)
            sonuc = False
        except ValueError:
            sonuc = ad in g.s and not g.cagri
        ek(f"FAIL: izin listesi disi adin silinmesi ({ad}) -> ValueError, istek yok", sonuc)
    ek("PASS: silinebilir liste tam 4 ad", set(GS.SILINEBILIR) == {YD, YN, SG.DENEME_AD, SG.PROVA_AD})
    # ---------------- Etsy'ye GET ve token yenileme disi istek
    for yol, bearer in (("/shops/1/listings", None), ("/users/me", None), ("/openapi-ping", "x")):
        try:
            with mock.patch.dict(os.environ, {"ETSY_API_KEY": KEY, "MOD": "olc"}), mock.patch.object(SG, "http_get", _ag_yok):
                SG.etsy_get(yol, ESKI, bearer=bearer)
            sonuc = False
        except SG.Dur as e:
            sonuc = "izinsiz Etsy istegi" in str(e)
        except AssertionError:                      # kapi yoksa istek aga cikmaya calisir
            sonuc = False
        ek(f"FAIL: izinsiz Etsy istegi ({yol}, bearer {bool(bearer)}) -> DUR, ag yok", sonuc)
    kaynak = (KOK / "scripts/etsy/secret_gecis.py").read_text()
    ek("PASS: kaynak taramasi: requests yalniz http_get icinde GET; Etsy istemcisi (E.Etsy) ve yazma yontemi yok",
       kaynak.count("requests.") == 1 and "requests.get(url, headers=basliklar, timeout=30)" in kaynak
       and not re.search(r"E\.Etsy\(|\.(put|patch|delete|post)\(|post_file|set -x", kaynak))
    try:
        with mock.patch.dict(os.environ, {"ETSY_API_KEY": KEY, "MOD": "yedek"}), mock.patch.object(SG, "http_get", SahteEtsy({ESKI}).get):
            SG.SAYAC.update(etsy=0, ok=0)
            SG.etsy_get("/openapi-ping", ESKI)
        sonuc = False
    except SG.Dur as e:
        sonuc = "istek siniri" in str(e)
    ek("FAIL: mod basina Etsy istek siniri (yedek: 0) asilamaz", sonuc)
    # ---------------- sir ciktisi taramasi
    SIR.update({KEY, ESKI, YENI, FARKLI, OPS, GHT, AT0, RT0})
    SIR4.update({KEY, ESKI, YENI, FARKLI, OPS, GHT, AT0, RT0})
    sizinti = sizinti_bul(CIKTI)
    ek(f"FAIL: sir ciktisi: {len(CIKTI)} kosu ciktisinda {len(SIR)} degerin kendisi / ilk-son 4 / sha256 / base64 bicimi ve suzulmus deger (***) YOK",
       not sizinti and len(CIKTI) > 100)
    if sizinti:
        print("SIZINTI:", sorted(set(sizinti))[:10])
    for ad, satir in (("ham deger", f"canli == YENI: EVET {ESKI}"), ("suzulmus deger (***)", "canli == YENI: EVET ***"), ("ilk 4 karakter", f"x {ESKI[:4]}"),
                      ("son 4 karakter", f"x {YENI[-4:]}"), ("sha256", hashlib.sha256(ESKI.encode()).hexdigest()),
                      ("base64", base64.b64encode(YENI.encode()).decode()), ("uzunluk", f"secret uzunlugu {len(ESKI)} karakter"), ("ciplak uzunluk sayisi", f"canli == YENI: EVET boy={len(ESKI)}"),
                      ("bayt", "ETSY_TOKEN_x.json | 271 bayt")):
        ek(f"FAIL: tarama kontrolu: cikti satirinda {ad} olsa tarama YAKALAR", sizinti_bul([("kontrol", satir + "\n")]))
    ek("PASS: tarama kontrolu: add-mask satiri ve sabit metin temiz sayilir", not sizinti_bul([("kontrol", f"::add-mask::{ESKI}\nkanit ucu canli: HTTP 200\n")]))
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti):
        SG.maskele("satir-bir-Aa11Bb22\nsatir-iki-Cc33Dd44")
    ek("PASS: maskele: cok satirli degerde her satir ayri add-mask alir", cikti.getvalue().splitlines() == ["::add-mask::satir-bir-Aa11Bb22", "::add-mask::satir-iki-Cc33Dd44"])
    # ---------------- is akisi: kabuk adimlari (bash -e) + yapisal sartlar
    r, d = kabuk("Ortak kapi", {"MOD": "olc", "ONAY": "SERDAR_SECRET_OLC"})
    ek("PASS: kabuk: ortak kapi PASS", r.returncode == 0 and "KAPI PASS: mod olc" in r.stdout)
    for ad, env in (("onay bos", {"MOD": "olc", "ONAY": ""}), ("baska mod sozcugu", {"MOD": "degistir", "ONAY": "SERDAR_SECRET_OLC"}),
                    ("ref main degil", {"MOD": "olc", "ONAY": "SERDAR_SECRET_OLC", "GITHUB_REF": "refs/heads/dal"}),
                    ("RUN_ATTEMPT 2", {"MOD": "olc", "ONAY": "SERDAR_SECRET_OLC", "GITHUB_RUN_ATTEMPT": "2"}), ("mod bos", {"MOD": "", "ONAY": "x"})):
        r, d = kabuk("Ortak kapi", env)
        ek(f"FAIL: kabuk: ortak kapi {ad} -> cikis 1", r.returncode == 1 and "DUR" in r.stdout)
    r, d = kabuk("Kilit", {"GH_TOKEN": GHT})
    ek("PASS: kabuk: kilit adimi (kilit_bekle) sahte GitHub ile", r.returncode == 0 and "KILIT ALINDI" in r.stdout and (d / "_out").read_text().strip() == "atla=false")
    for ad in ("Siparis kontrol 1", "Siparis kontrol 2"):
        r, d = kabuk(ad, {"GH_TOKEN": GHT})
        ek(f"PASS: kabuk: {ad}: aktif siparis kosusu yok -> gecer", r.returncode == 0 and "aktif siparis kosusu yok" in r.stdout)
        r, d = kabuk(ad, {"GH_TOKEN": GHT, "SG_SAHTE_KOSU": "siparis-kisisel-oku.yml"})
        ek(f"FAIL: kabuk: {ad}: aktif siparis-* kosusu var -> BEKLEMEDEN cikis 1 (karsilikli bekleme yok)", r.returncode == 1 and "[bekliyor]" not in r.stdout)
    ek("PASS: is akisi: siparis-* icin bekleme yok (--dk 0), kilit iki kontrolun arasinda", WF.read_text().count("siparis_bekle.py --dk 0") == 2
       and "--dk 60" not in WF.read_text())
    conf = base64.b64encode(b"[gdrive]\ntype = drive\nclient_id = abc\n").decode()
    r, d = kabuk("rclone + conf", {"RCLONE_CONF_B64": conf, "GOOGLE_CLIENT_SECRET": "gcs-Secret-9988-xy"})
    ek("PASS: kabuk: rclone conf adimi; GITHUB_ENV'e yalniz rclone ayar satiri", r.returncode == 0
       and (d / "_env").read_text().strip() == "RCLONE_CONFIG_GDRIVE_CLIENT_SECRET=gcs-Secret-9988-xy" and (d / ".config/rclone/rclone.conf").exists())
    r, d = kabuk("kapat", {"MOD": "kapat", "ONAY": "SERDAR_SECRET_KAPAT", "OPS_ADMIN_TOKEN": OPS})
    ek("PASS: kabuk: kapat adimi (env adi + betik + sahte GitHub)", r.returncode == 0 and r.stdout.count("kapali EVET") == 18 and "kapat: PASS" in r.stdout)
    r, d = kabuk("degistir", {"MOD": "degistir", "ONAY": "SERDAR_SECRET_DEGISTIR", "OPS_ADMIN_TOKEN": OPS, "GH_TOKEN": GHT, "ETSY_API_KEY": KEY,
                              C: ESKI, YD: ESKI, YN: YENI})
    ek("FAIL: kabuk: degistir adimi kanit ucu AYARSIZ iken cikis 1 (pipefail / bash -e)", r.returncode == 1 and "kanit ucu AYARSIZ" in r.stdout)
    y = WF.read_text(encoding="utf-8")
    ek("PASS: is akisi: her mod icin bir adim ve dogru komut", all(f"python3 scripts/etsy/secret_gecis.py {m}\n" in y and f"inputs.mod == '{m}'" in y for m in SG.MODLAR))
    ek("PASS: is akisi: secret'lar yalniz adim env'inde (is / is akisi env'inde secrets yok)", "secrets." not in y.split("jobs:")[0]
       and not re.search(r"^    env:", y, re.M))
    # ---------------- docs/SECRETS.md: mod tablosu, K3 listesi, ISTISNA 2 (birebir)
    doc = (KOK / "docs/SECRETS.md").read_text(encoding="utf-8")
    tablo = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\| `(\w+)` \|.*\| (\d+) \|$", doc, re.M)}
    ek("PASS: docs/SECRETS.md mod tablosu = secret_gecis.MODLAR (mod ve mod basina Etsy istek siniri)", tablo == SG.MODLAR)
    ek("PASS: docs/SECRETS.md K3 listesi = secret_gecis.KAPAT (sira dahil)", ", ".join(SG.KAPAT) + "." in " ".join(doc.split()))
    istisna2 = ("- ISTISNA 2 (KARAR, 12 Kasim 2026): Etsy shared secret yenilemesinde Serdar tarayicidan iki giris yapar: (1) gecisten once, "
                "erisimi olcmek icin anlamsiz bir degerle `ETSY_SECRET_DENEME` adina deneme girisi; (2) Etsy panelinden kopyalanan yeni degerin "
                "`ETSY_SHARED_SECRET_YENI` adina girisi (kapi FAIL verirse yeniden girilir). Canli `ETSY_SHARED_SECRET`'i yalniz `etsy-secret-gecis` "
                "is akisi yazar. Deger sohbete, is akisi girdisine ve Drive'a yazilmaz.")
    ek("PASS: docs/SECRETS.md ISTISNA 2 metni birebir (tek satir)", istisna2 in doc.splitlines() and "SERDAR_SECRET_<MOD buyuk harf>" in doc
       and "ve `ETSY_SHARED_SECRET` sabittir" not in doc)
    return t


def main():
    t = testler()
    for ad, ok in t:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in t)
    print(f"secret_gecis testleri TOPLAM: {n}/{len(t)} PASS")
    if _TMP["kok"]:
        shutil.rmtree(_TMP["kok"], ignore_errors=True)
    sys.exit(0 if n == len(t) else 1)


if __name__ == "__main__":
    main()
