#!/usr/bin/env python3
"""Etsy yeniden yetkilendirme (PKCE) — TEK LINK uretir, kodu token'a cevirir.

Neden: yonlendiricinin siparisleri okuyabilmesi icin token'da `transactions_r` kapsami
gerekiyor (7 Eyl olcumu: GET /shops/{id}/receipts -> 403 "requires scope: transactions_r").

  link     : PKCE dogrulayici + yetkilendirme baglantisi uretir. Baglanti ve dogrulayici
             Drive'a yazilir (sohbete/loga yazilmaz). Serdar baglantiyi telefonda acar,
             "Allow Access" der, adres cubugundaki `code` degerini iletir.
  degistir : --code ile token alir, ETSY_TOKEN.json'i (Drive) YENILER. Eski zincir kapanir.

Kullanim:
  etsy_yetki.py link --redirect "https://<kayitli-redirect-uri>"
  etsy_yetki.py degistir --code "..." --redirect "https://<ayni-uri>"
Ortam: ETSY_API_KEY (keystring). Anahtar hicbir loga yazilmaz (::add-mask::).
"""
import argparse
import base64
import hashlib
import json
import os
import pathlib
import secrets
import subprocess
import sys
import time

import requests

AUTH = "https://www.etsy.com/oauth/connect"
TOKEN = "https://api.etsy.com/v3/public/oauth/token"
DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
TOKEN_DRV = "gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json"
# Mevcut kapsamlar + yonlendiricinin siparis okumasi icin transactions_r
KAPSAM = ["listings_r", "listings_w", "shops_r", "shops_w", "transactions_r"]


def log(m):
    print(m, flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def keystring():
    k = os.environ.get("ETSY_API_KEY")
    if not k:
        raw = rclone("cat", TOKEN_DRV).stdout
        k = json.loads(raw).get("keystring")
    if not k:
        raise SystemExit("HATA: keystring yok")
    print(f"::add-mask::{k}", flush=True)
    return k


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["link", "degistir"])
    ap.add_argument("--redirect", required=True, help="Etsy uygulamasinda KAYITLI redirect URI")
    ap.add_argument("--code", default="")
    ap.add_argument("--is-dizin", default="_work/yetki")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    key = keystring()

    if a.mod == "link":
        dogrulayici = b64u(secrets.token_bytes(48))
        challenge = b64u(hashlib.sha256(dogrulayici.encode()).digest())
        state = b64u(secrets.token_bytes(12))
        url = (f"{AUTH}?response_type=code&redirect_uri={requests.utils.quote(a.redirect, safe='')}"
               f"&scope={requests.utils.quote(' '.join(KAPSAM))}&client_id={key}"
               f"&state={state}&code_challenge={challenge}&code_challenge_method=S256")
        (isd / "ETSY_YETKI_LINK.txt").write_text(
            "Etsy yeniden yetkilendirme baglantisi (telefonda ac, Allow Access, adres cubugundaki "
            "code degerini ilet):\n" + url + "\n", encoding="utf-8")
        (isd / "ETSY_YETKI_PKCE.json").write_text(json.dumps(
            {"state": state, "code_verifier": dogrulayici, "redirect": a.redirect,
             "kapsam": KAPSAM, "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(isd / "ETSY_YETKI_LINK.txt"), f"{DRV}/ETSY_YETKI_LINK.txt")
        rclone("copyto", str(isd / "ETSY_YETKI_PKCE.json"), f"{DRV}/ETSY_YETKI_PKCE.json")
        log(f"baglanti ve PKCE Drive'a yazildi: {DRV}/ETSY_YETKI_LINK.txt (kapsam: {' '.join(KAPSAM)})")
        return 0

    if not a.code:
        raise SystemExit("HATA: degistir icin --code gerekir")
    rclone("copyto", f"{DRV}/ETSY_YETKI_PKCE.json", str(isd / "pkce.json"))
    pkce = json.loads((isd / "pkce.json").read_text(encoding="utf-8"))
    r = requests.post(TOKEN, data={"grant_type": "authorization_code", "client_id": key,
                                   "redirect_uri": pkce["redirect"], "code": a.code,
                                   "code_verifier": pkce["code_verifier"]}, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"HATA: token degisimi {r.status_code}: {r.text[:200]}")
    d = r.json()
    rclone("copyto", TOKEN_DRV, str(isd / "ETSY_TOKEN.json"))
    tok = json.loads((isd / "ETSY_TOKEN.json").read_text(encoding="utf-8"))
    tok.update({"access_token": d["access_token"], "refresh_token": d["refresh_token"],
                "obtained_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                "expires_in": d.get("expires_in"), "token_type": d.get("token_type"),
                "scope": " ".join(KAPSAM)})
    (isd / "ETSY_TOKEN.json").write_text(json.dumps(tok, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(isd / "ETSY_TOKEN.json"), TOKEN_DRV)
    log("yeni token Drive'a yazildi (kapsam: " + " ".join(KAPSAM) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
