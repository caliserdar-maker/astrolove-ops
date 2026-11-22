"""Ortak: sir maskeleme, temiz hata metni, guvenli HTTP, rclone, log.

Kurallar (plan 4.5): token URL'de gitmez (Authorization basligi ya da form govdesi); zorunlu olarak sorguda
giden uclar (token yenileme / degisim) icin `sorgu_sirri=True` verilir, hata metninden adres ve sir silinir.
Yazan (POST) istekler ASLA otomatik yeniden denenmez (cift paylasim riski); yalniz GET 5xx/429'da 2 kez.
Hicbir hata metni ham istisna olarak disari cikmaz: Hata(temiz metin)."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

_SIRLAR = set()
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
HTTP_TIMEOUT = 120


def log(msg):
    print(temizle(str(msg)), flush=True)


def gizle(*degerler):
    """Degeri sir olarak kaydeder; Actions'ta ::add-mask:: basar (deger yalniz runner'a gider)."""
    for d in degerler:
        if isinstance(d, str) and len(d) >= 6 and d not in _SIRLAR:
            _SIRLAR.add(d)
            if os.environ.get("GITHUB_ACTIONS") == "true":
                sys.stdout.write(f"::add-mask::{d}\n")
                sys.stdout.flush()


_URL = re.compile(r"https?://[^\s'\"<>]+")
_ANAHTAR = re.compile(r"(?i)\b(access_token|client_secret|refresh_token|fb_exchange_token|code|token|th_exchange_token|ig_exchange_token)=[^&\s'\"]+")
_JSON_ANAHTAR = re.compile(r"(?i)([\"']?(?:access_token|client_secret|refresh_token|id_token|token|code|upload_url)[\"']?\s*[:=]\s*[\"'])[^\"']+")


def temizle(metin):
    t = str(metin)
    for s in sorted(_SIRLAR, key=len, reverse=True):
        t = t.replace(s, "***")
    t = _ANAHTAR.sub(lambda m: m.group(1) + "=***", t)
    t = _JSON_ANAHTAR.sub(lambda m: m.group(1) + "***", t)
    t = _URL.sub(lambda m: m.group(0).split("?", 1)[0] + ("?***" if "?" in m.group(0) else ""), t)
    t = re.sub(r"(?i)(bearer|oauth)\s+[A-Za-z0-9._\-|]{8,}", r"\1 ***", t)
    return t


class Hata(Exception):
    """Metni temizlenmis hata. `belirsiz=True`: istek gitmis olabilir (yazim sonucu bilinmiyor)."""

    def __init__(self, metin, belirsiz=False, kod=None):
        super().__init__(temizle(metin)[:300])
        self.belirsiz = belirsiz
        self.kod = kod


class Http:
    """requests.Session sarmalayicisi. `oturum` testte sahte nesnedir."""

    def __init__(self, oturum=None, uyku=time.sleep):
        if oturum is None:
            import requests
            oturum = requests.Session()
        self.o = oturum
        self.uyku = uyku

    def iste(self, yontem, url, *, token=None, sema="Bearer", sorgu_sirri=False, params=None, data=None,
             json_govde=None, govde=None, dosyalar=None, basliklar=None, beklenen=(200,)):
        yontem = yontem.upper()
        h = dict(basliklar or {})
        if token:
            gizle(token)
            h["Authorization"] = f"{sema} {token}"
        if params and not sorgu_sirri:
            for k in params:
                if re.search(r"(?i)token|secret", k):
                    raise Hata(f"sir sorguda gonderilemez: {k}")
        deneme = 3 if yontem == "GET" else 1
        son = None
        for i in range(deneme):
            try:
                r = self.o.request(yontem, url, params=params, data=data if govde is None else govde,
                                   json=json_govde, files=dosyalar, headers=h, timeout=HTTP_TIMEOUT)
            except Exception as e:  # baglanti / zaman asimi: yazimda sonuc belirsiz
                son = Hata(f"{yontem} {url}: {type(e).__name__} {e}", belirsiz=(yontem != "GET"))
                if yontem == "GET" and i + 1 < deneme:
                    self.uyku(2 ** i)
                    continue
                raise son
            if yontem == "GET" and (r.status_code >= 500 or r.status_code == 429) and i + 1 < deneme:
                self.uyku(2 ** i)
                continue
            break
        try:
            j = r.json()
        except Exception:
            j = {"_metin": (getattr(r, "text", "") or "")[:200]}
        if r.status_code not in beklenen or (isinstance(j, dict) and "error" in j):
            msg = j.get("error") if isinstance(j, dict) else None
            if isinstance(msg, dict):
                msg = msg.get("message") or msg.get("error_user_msg") or json.dumps(msg)[:200]
            if not isinstance(msg, str):  # ham govde hata metnine girmez (bilinmeyen alanlarda sir olabilir)
                msg = "govde gizlendi"
            raise Hata(f"{yontem} {url}: HTTP {r.status_code} {msg}", belirsiz=(yontem != "GET" and r.status_code >= 500),
                       kod=r.status_code)
        return j, r


def rclone(*arg, girdi=None):
    r = subprocess.run(["rclone", *arg], input=girdi, capture_output=True, text=True)
    if r.returncode != 0:
        raise Hata(f"rclone {arg[0]}: {r.stderr.strip()[:200]}")
    return r.stdout


def drive_oku(yol):
    return rclone("cat", f"{RCLONE_REMOTE}:{yol}")


def drive_yaz(yol, metin):
    rclone("rcat", f"{RCLONE_REMOTE}:{yol}", girdi=metin)


def drive_indir(yol, hedef):
    rclone("copyto", f"{RCLONE_REMOTE}:{yol}", str(hedef))


def md5_dosya(yol):
    h = hashlib.md5()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1 << 20), b""):
            h.update(p)
    return h.hexdigest()
