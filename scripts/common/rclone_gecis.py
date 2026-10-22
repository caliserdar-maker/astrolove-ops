#!/usr/bin/env python3
"""rclone gdrive remote'unu kendi OAuth istemcimize gecirme (RCLONE_PLAN adim 4-7, Serdar 22 Eki). DEGER LOGA YAZILMAZ.

Alt komutlar:
  bekle   --kok REMOTE_YOL --ad ADI_ONEKI --dk N --durum STATE --cikti KOD_DOSYASI
          Eski conf ile Drive klasorunu 10 sn arayla okur; ADI_ONEKI ile baslayan dosya gelince icerigini okur
          (Google Doku olarak yazilmissa txt'ye aktarilir), dosyayi KALICI siler (cop kutusu yok), silindigini dogrular.
          Icerik: donus adresinin tamami (http://localhost:53682/?state=..&code=..&scope=..) ya da yalniz code degeri.
          Adreste state varsa STATE ile ayni olmali. Kod ::add-mask:: ile maskelenir, 0600 dosyaya yazilir.
  takas   --kod-dosyasi F --conf-cikti C   Kodu token'a cevirir (CLIENT_ID + GOOGLE_CLIENT_SECRET, redirect_uri
          localhost:53682); access/refresh token maskelenir; yeni rclone.conf (0600) yazilir. Kod dosyasi silinir.
  dogrula --conf C [--doc ID] [--sheet ID] [--etiket E]   Adim 6/7 kapilari, her biri PASS/FAIL:
          tokeninfo aud == CLIENT_ID, kapsam drive+documents+spreadsheets, expiry dolu + refresh_token var,
          rclone lsf gdrive:ASTROLOVE > 0 ve "shared client_id" uyarisi yok, Docs GET 200, Sheets GET 200.
          --yenileme-bekle: conf'taki access token suresi dolmus olmali ve rclone yeniledikten sonra expiry ileri gitmeli.
Ortam: CLIENT_ID, GOOGLE_CLIENT_SECRET (takas/dogrula), RCLONE_CONFIG (bekle: eski conf)."""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REDIRECT = "http://localhost:53682/"
KAPSAM = ("https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents",
          "https://www.googleapis.com/auth/spreadsheets")
PAYLASIMLI = "shared Google Drive client_id"


def maske(*degerler):
    for d in degerler:
        if d:
            print(f"::add-mask::{d}", flush=True)


def rclone(*arg, conf=None):
    env = dict(os.environ)
    if conf:
        env["RCLONE_CONFIG"] = str(conf)
        env.pop("RCLONE_CONFIG_GDRIVE_CLIENT_SECRET", None)   # yeni conf kendi secret'ini tasir
    return subprocess.run(["rclone", *arg], capture_output=True, text=True, env=env, timeout=300)


def kod_coz(icerik, durum):
    """-> (kod, hata). Adresin tamami ya da yalniz kod."""
    s = icerik.strip().strip('"').strip()
    if s.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s).query)
        if q.get("error"):
            return None, f"donus adresinde hata: {q['error'][0]}"
        st = (q.get("state") or [""])[0]
        if durum and st and st != durum:
            return None, "state uyusmuyor"
        kod = (q.get("code") or [""])[0]
    else:
        kod = s
    if not re.fullmatch(r"[0-9A-Za-z/_.\-]{20,}", kod or ""):
        return None, "kod bicimi gecersiz"
    return kod, None


def bekle(a):
    son = time.time() + a.dk * 60
    t0 = time.time()
    n = 0
    while time.time() < son:
        n += 1
        r = rclone("lsf", a.kok, "--files-only", "--max-depth", "1", "--drive-export-formats", "txt")
        adlar = [x for x in r.stdout.splitlines() if x.startswith(a.ad)]
        if adlar:
            ad = adlar[0]
            c = rclone("cat", f"{a.kok}/{ad}", "--drive-export-formats", "txt")
            icerik = c.stdout
            maske(*[t for t in re.split(r"[?&=\s]", icerik) if len(t) >= 20])
            d = rclone("deletefile", f"{a.kok}/{ad}", "--drive-use-trash=false", "--drive-export-formats", "txt")
            kalan = [x for x in rclone("lsf", a.kok, "--files-only", "--max-depth", "1", "--drive-export-formats", "txt").stdout.splitlines()
                     if x.startswith(a.ad)]
            print(f"DOSYA bulundu ({n}. tur, {time.time() - t0:.0f} sn) | okundu {'EVET' if c.returncode == 0 else 'HAYIR'} | "
                  f"silindi {'EVET' if d.returncode == 0 and not kalan else 'HAYIR'}", flush=True)
            if c.returncode != 0:
                raise SystemExit("FAIL: dosya okunamadi")
            if kalan:
                raise SystemExit("FAIL: dosya silinemedi; takas yapilmadi")
            kod, hata = kod_coz(icerik, a.durum)
            if hata:
                raise SystemExit(f"FAIL: {hata}")
            maske(kod)
            p = pathlib.Path(a.cikti)
            p.write_text(kod)
            p.chmod(0o600)
            print("KOD alindi (deger yazilmadi)", flush=True)
            return
        if n % 6 == 1:
            g = time.time() - t0
            print(f"[bekliyor] {g / 60:.1f} dk gecti, kalan {(son - time.time()) / 60:.1f} dk", flush=True)
        time.sleep(10)
    raise SystemExit(f"FAIL: {a.dk} dk icinde dosya gelmedi")


def post(url, veri):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(veri).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        try:
            return None, (json.loads(e.read() or b"{}").get("error") or f"HTTP {e.code}")
        except Exception:  # noqa: BLE001
            return None, f"HTTP {e.code}"


def takas(a):
    cid, cs = os.environ["CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"]
    kp = pathlib.Path(a.kod_dosyasi)
    kod = kp.read_text().strip()
    maske(kod)
    tok, hata = post("https://oauth2.googleapis.com/token", {"code": kod, "client_id": cid, "client_secret": cs,
                                                            "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    kp.unlink()
    if hata:
        raise SystemExit(f"FAIL: token alinamadi (hata kodu: {hata})")
    maske(tok.get("access_token"), tok.get("refresh_token"))
    if not tok.get("refresh_token"):
        raise SystemExit("FAIL: yanitta refresh_token yok (baglanti prompt=consent ile acilmali)")
    exp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat().replace("+00:00", "Z")
    token = json.dumps({"access_token": tok["access_token"], "token_type": tok.get("token_type", "Bearer"),
                        "refresh_token": tok["refresh_token"], "expiry": exp}, separators=(",", ":"))
    conf = f"[gdrive]\ntype = drive\nclient_id = {cid}\nclient_secret = {cs}\nscope = drive\ntoken = {token}\n"
    p = pathlib.Path(a.conf_cikti)
    p.write_text(conf)
    p.chmod(0o600)
    print(f"TAKAS PASS | refresh_token var | expiry dolu | verilen kapsam sayisi {len((tok.get('scope') or '').split())}", flush=True)


def zaman(s):
    """rclone expiry ('2026-10-22T18:00:00.123456789+03:00' / '...Z') -> aware datetime; bos/bozuk -> None"""
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?(Z|[+-]\d\d:\d\d)?$", s or "")
    if not m:
        return None
    return dt.datetime.fromisoformat(m.group(1) + ("+00:00" if m.group(2) in (None, "Z") else m.group(2)))


def conf_token(conf):
    m = re.search(r"^token\s*=\s*(\{.*\})\s*$", pathlib.Path(conf).read_text(), re.M)
    return json.loads(m.group(1)) if m else {}


def get(url, tok):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {}


def dogrula(a):
    cid = os.environ["CLIENT_ID"]
    sonuc = []
    once = conf_token(a.conf)
    maske(once.get("access_token"), once.get("refresh_token"))
    if a.yenileme_bekle:
        e0 = zaman(once.get("expiry", ""))
        sonuc.append(("yenileme oncesi access token suresi dolmus", e0 is not None and e0 < dt.datetime.now(dt.timezone.utc)))
    r = rclone("lsf", "gdrive:ASTROLOVE", "--max-depth", "1", conf=a.conf)
    n = len([x for x in r.stdout.splitlines() if x.strip()])
    sonuc.append((f"rclone lsf gdrive:ASTROLOVE > 0 (oge {n})", r.returncode == 0 and n > 0))
    sonuc.append(("'shared client_id' uyarisi yok", PAYLASIMLI not in (r.stderr + r.stdout)))
    sonra = conf_token(a.conf)   # rclone gerekirse yeniler ve conf'a yazar
    maske(sonra.get("access_token"), sonra.get("refresh_token"))
    if a.yenileme_bekle:
        e0, e1 = zaman(once.get("expiry", "")), zaman(sonra.get("expiry", ""))
        sonuc.append(("rclone yeniledi (expiry ileri gitti)", e0 is not None and e1 is not None and e1 > e0))
    sonuc.append(("expiry dolu + refresh_token var", bool(sonra.get("expiry")) and bool(sonra.get("refresh_token"))))
    at = sonra.get("access_token", "")
    _, ti = get("https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"access_token": at}), at)
    sonuc.append(("tokeninfo aud = yeni client_id", ti.get("aud") == cid))
    kap = set((ti.get("scope") or "").split())
    sonuc.append(("kapsam drive + documents + spreadsheets", all(k in kap for k in KAPSAM)))
    if a.doc:
        k, _ = get(f"https://docs.googleapis.com/v1/documents/{a.doc}?fields=title", at)
        sonuc.append((f"Docs GET {k}", k == 200))
    if a.sheet:
        k, _ = get(f"https://sheets.googleapis.com/v4/spreadsheets/{a.sheet}?fields=properties.title", at)
        sonuc.append((f"Sheets GET {k}", k == 200))
    for ad, ok in sonuc:
        print(f"{'PASS' if ok else 'FAIL'} {ad}", flush=True)
    hepsi = all(ok for _, ok in sonuc)
    print(f"DOGRULA {a.etiket}: {'PASS' if hepsi else 'FAIL'} ({sum(ok for _, ok in sonuc)}/{len(sonuc)})", flush=True)
    sys.exit(0 if hepsi else 1)


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    b = alt.add_parser("bekle")
    b.add_argument("--kok", required=True); b.add_argument("--ad", required=True); b.add_argument("--dk", type=int, default=30)
    b.add_argument("--durum", default=""); b.add_argument("--cikti", required=True)
    t = alt.add_parser("takas"); t.add_argument("--kod-dosyasi", required=True); t.add_argument("--conf-cikti", required=True)
    d = alt.add_parser("dogrula"); d.add_argument("--conf", required=True); d.add_argument("--doc", default="")
    d.add_argument("--sheet", default=""); d.add_argument("--etiket", default="adim6")
    d.add_argument("--yenileme-bekle", action="store_true")
    a = ap.parse_args()
    {"bekle": bekle, "takas": takas, "dogrula": dogrula}[a.komut](a)


if __name__ == "__main__":
    main()
