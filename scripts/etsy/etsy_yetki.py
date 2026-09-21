#!/usr/bin/env python3
"""Etsy yeniden yetkilendirme (PKCE) — TEK LINK uretir, kodu token'a cevirir, dogrular.

Neden: yonlendiricinin siparisleri okuyabilmesi icin token'da `transactions_r` kapsami
gerekiyor (7 Eyl olcumu: GET /shops/{id}/receipts -> 403 "requires scope: transactions_r").

  link     : Mevcut token'in kapsamlarini okur, uzerine EKSIKLERI ekler (hicbiri dusmez),
             PKCE dogrulayici + yetkilendirme baglantisi uretir. Baglanti ve dogrulayici
             Drive'a yazilir (sohbete/loga yazilmaz). Serdar baglantiyi telefonda acar,
             "Allow Access" der, adres cubugundaki `code` degerini iletir.
  degistir : --code ile token alir, eski token'i YEDEK'e kopyalar, ETSY_TOKEN.json'i
             (Drive) YENILER, ardindan salt-okuma testini kosar. Eski zincir kapanir.
  test     : Salt okuma kaniti — getShop + getShopReceipts limit=1 (transactions_r).

Kullanim:
  etsy_yetki.py link --redirect "https://<kayitli-redirect-uri>"
  etsy_yetki.py degistir --code "..." --redirect "https://<ayni-uri>"
  etsy_yetki.py test
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

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

AUTH = "https://www.etsy.com/oauth/connect"
TOKEN = "https://api.etsy.com/v3/public/oauth/token"
DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
TOKEN_DRV = "gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json"
KOD_DRV = f"{DRV}/ETSY_YETKI_KOD.txt"  # tek kullanimlik authorization code (kosuda silinir)
# Taban: bilinen mevcut kapsamlar + yonlendiricinin siparis okumasi icin transactions_r.
# Gercek liste kosuda canli token'dan okunur; bu taban yalnizca alt sinirdir.
TABAN = ["listings_r", "listings_w", "shops_r", "shops_w"]
EKLENECEK = ["transactions_r", "transactions_w"]   # 21 Eyl: kargo takibini Etsy'ye yazmak icin


def log(m):
    print(m, flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def token_oku():
    return json.loads(rclone("cat", TOKEN_DRV).stdout)


def keystring(tok=None):
    k = os.environ.get("ETSY_API_KEY") or (tok or {}).get("keystring")
    if not k:
        raise SystemExit("HATA: keystring yok")
    print(f"::add-mask::{k}", flush=True)
    return k


def kapsamlar(tok):
    """(eski, yeni): canli token'in kapsamlari + eksikler. Hicbiri dusmez."""
    eski = [s for s in str(tok.get("scope") or "").split() if s]
    yeni = list(eski)
    for s in TABAN + EKLENECEK:
        if s not in yeni:
            yeni.append(s)
    return eski, yeni


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def salt_okuma_testi(isd):
    """getShop + getShopReceipts limit=1. Musteri verisi loga yazilmaz."""
    from etsy_common import Etsy, TokenStore  # noqa: E402
    rclone("copyto", TOKEN_DRV, str(isd / "ETSY_TOKEN.json"))
    st = TokenStore(str(isd / "ETSY_TOKEN.json"), os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop = os.environ.get("ETSY_SHOP_ID") or str(st.data.get("shop_id") or "")
    satir = [f"zaman_utc: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
             f"kapsam: {st.data.get('scope')}"]
    s = api.get(f"/shops/{shop}", ok404=True) or {}
    satir.append(f"getShop: {'OK' if s.get('shop_id') else 'FAIL'} ({s.get('shop_name', '-')})")
    try:
        r = api.get(f"/shops/{shop}/receipts", params={"limit": 1}) or {}
        satir.append(f"getShopReceipts: OK (count={r.get('count')}, donen={len(r.get('results') or [])})")
        gecti = True
    except SystemExit as ex:
        satir.append(f"getShopReceipts: FAIL ({str(ex)[:120]})")
        gecti = False
    satir.append(f"kota_kalan: {api.remaining}")
    satir.append("SONUC: " + ("PASS (transactions_r calisiyor)" if gecti and s.get("shop_id") else "FAIL"))
    if st.updated:  # refresh() dosyayi zaten yazdi; Drive tek kaynak olarak guncellenir
        rclone("copyto", str(isd / "ETSY_TOKEN.json"), TOKEN_DRV)
    metin = "\n".join(satir) + "\n"
    (isd / "ETSY_YETKI_TEST.txt").write_text(metin, encoding="utf-8")
    rclone("copyto", str(isd / "ETSY_YETKI_TEST.txt"), f"{DRV}/ETSY_YETKI_TEST.txt")
    log(metin)
    return 0 if gecti else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["link", "degistir", "test"])
    ap.add_argument("--redirect", default="", help="Etsy uygulamasinda KAYITLI redirect URI")
    ap.add_argument("--code", default="", help="bos birakilirsa Drive'daki KOD_DRV dosyasindan okunur")
    ap.add_argument("--state", default="", help="callback adresindeki state; PKCE dosyasiyla karsilastirilir")
    ap.add_argument("--is-dizin", default="_work/yetki")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)

    if a.mod == "test":
        keystring()
        return salt_okuma_testi(isd)

    if not a.redirect:
        raise SystemExit("HATA: --redirect gerekir")
    tok = token_oku()
    key = keystring(tok)
    eski, yeni = kapsamlar(tok)
    log(f"kapsam eski : {' '.join(eski) or '(yok)'}")
    log(f"kapsam yeni : {' '.join(yeni)}")

    if a.mod == "link":
        dogrulayici = b64u(secrets.token_bytes(48))
        challenge = b64u(hashlib.sha256(dogrulayici.encode()).digest())
        state = b64u(secrets.token_bytes(12))
        url = (f"{AUTH}?response_type=code&redirect_uri={requests.utils.quote(a.redirect, safe='')}"
               f"&scope={requests.utils.quote(' '.join(yeni))}&client_id={key}"
               f"&state={state}&code_challenge={challenge}&code_challenge_method=S256")
        (isd / "ETSY_YETKI_LINK.txt").write_text(
            "Etsy yeniden yetkilendirme baglantisi\n"
            "1) Bu baglantiyi telefonda/tarayicida ac, Etsy hesabinla giris yap.\n"
            "2) 'Allow Access' de.\n"
            "3) Adres cubugunda acilan https://astrolove.art/oauth/callback?code=...&state=... "
            "adresindeki code degerini ilet (sayfa bos/404 gorunse de adres cubugundaki code gecerlidir).\n"
            f"kapsam eski: {' '.join(eski)}\n"
            f"kapsam yeni: {' '.join(yeni)}\n"
            f"redirect   : {a.redirect}\n"
            f"state      : {state}\n\n" + url + "\n", encoding="utf-8")
        (isd / "ETSY_YETKI_PKCE.json").write_text(json.dumps(
            {"state": state, "code_verifier": dogrulayici, "redirect": a.redirect,
             "kapsam_eski": eski, "kapsam": yeni,
             "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(isd / "ETSY_YETKI_LINK.txt"), f"{DRV}/ETSY_YETKI_LINK.txt")
        rclone("copyto", str(isd / "ETSY_YETKI_PKCE.json"), f"{DRV}/ETSY_YETKI_PKCE.json")
        log(f"baglanti ve PKCE Drive'a yazildi: {DRV}/ETSY_YETKI_LINK.txt")
        return 0

    rclone("copyto", f"{DRV}/ETSY_YETKI_PKCE.json", str(isd / "pkce.json"))
    pkce = json.loads((isd / "pkce.json").read_text(encoding="utf-8"))
    if a.state and a.state != pkce.get("state"):
        raise SystemExit("HATA: state PKCE dosyasiyla uyusmuyor. DUR (kod kullanilmadi).")
    log(f"state dogrulandi: {'evet' if a.state else 'atlandi (--state verilmedi)'}")
    kod = a.code
    if not kod:  # kod GitHub loglarina girmesin diye Drive'dan okunur, sonra silinir
        kod = rclone("cat", KOD_DRV).stdout.strip()
    if not kod:
        raise SystemExit(f"HATA: kod yok (--code ya da {KOD_DRV})")
    print(f"::add-mask::{kod}", flush=True)
    try:
        r = requests.post(TOKEN, data={"grant_type": "authorization_code", "client_id": key,
                                       "redirect_uri": pkce["redirect"], "code": kod,
                                       "code_verifier": pkce["code_verifier"]}, timeout=60)
    finally:
        rclone("deletefile", KOD_DRV, sert=False)  # tek kullanimlik kod diskte kalmaz
    if r.status_code != 200:
        raise SystemExit(f"HATA: token degisimi {r.status_code}: {r.text[:200]}")
    d = r.json()
    donen = str(d.get("scope") or " ".join(pkce.get("kapsam") or yeni))
    eksik = [s for s in (pkce.get("kapsam") or yeni) if s not in donen.split()]
    if eksik:
        raise SystemExit(f"HATA: yeni token'da eksik kapsam: {' '.join(eksik)}. Eski token korundu.")
    yedek = f"{DRV}/YEDEK/ETSY_TOKEN_{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}.json"
    rclone("copyto", TOKEN_DRV, yedek)
    yeni_tok = dict(tok)
    yeni_tok.update({"access_token": d["access_token"], "refresh_token": d["refresh_token"],
                     "obtained_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                     "expires_in": d.get("expires_in"), "token_type": d.get("token_type"),
                     "scope": donen})
    (isd / "ETSY_TOKEN.json").write_text(json.dumps(yeni_tok, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(isd / "ETSY_TOKEN.json"), TOKEN_DRV)
    log(f"yeni token Drive'a yazildi (yedek: {yedek}) | kapsam: {donen}")
    return salt_okuma_testi(isd)


if __name__ == "__main__":
    sys.exit(main())
