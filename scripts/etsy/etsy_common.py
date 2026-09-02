#!/usr/bin/env python3
"""
Ortak Etsy v3 istemcisi (token deposu + GET/PATCH sarmali).

- TokenStore: Drive'dan kopyalanmis ETSY_TOKEN.json'i okur, gerekirse
  yeniler, yeni refresh token'i ayni dosyaya geri yazar ve yaninda
  ".updated" isaret dosyasi birakir (workflow bunu gorunce Drive'a yazar).
- Etsy: x-api-key = keystring:shared_secret, Bearer access token; 401'de
  bir kez yenileyip tekrar dener; 429'da temiz cikar; x-remaining-today
  basligini takip eder.

Hicbir sir loga yazilmaz; okunan her token degeri ::add-mask:: ile
maskelenir.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://openapi.etsy.com/v3/application"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
TIMEOUT = 60


def mask(value):
    if value:
        print(f"::add-mask::{value}", flush=True)


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ token
class TokenStore:
    """ETSY_TOKEN.json okur/yeniler/geri yazar. Alan adlari B61'de kayitli:
    keystring, shared_secret, refresh_token, access_token, obtained_at
    (tarih METNI, epoch degil - B66), token_type, expires_in, scope."""

    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, path, keystring, shared_secret):
        self.path = Path(path)
        raw = self.path.read_text(encoding="utf-8")
        self.pretty = "\n" in raw.strip()
        self.data = json.loads(raw)
        for k in ("refresh_token", "access_token", "shared_secret", "keystring"):
            mask(self.data.get(k))
        self.keystring = self.data.get("keystring") or keystring
        self.shared_secret = self.data.get("shared_secret") or shared_secret
        if not self.keystring or not self.shared_secret:
            raise SystemExit("HATA: keystring/shared_secret ne dosyada ne ortamda.")
        if not self.data.get("refresh_token"):
            raise SystemExit("HATA: token dosyasinda refresh_token yok.")
        self.updated = False

    @property
    def api_key_header(self):
        return f"{self.keystring}:{self.shared_secret}"

    @property
    def access_token(self):
        return self.data.get("access_token")

    def age_seconds(self):
        raw = self.data.get("obtained_at")
        if raw is None:
            return None
        try:
            if isinstance(raw, (int, float)):
                obtained = datetime.fromtimestamp(float(raw), tz=timezone.utc)
            else:
                obtained = datetime.strptime(str(raw).strip(), self.DATE_FMT).replace(
                    tzinfo=timezone.utc
                )
        except (ValueError, OverflowError):
            return None
        return (datetime.now(timezone.utc) - obtained).total_seconds()

    def needs_refresh(self, margin=300):
        if not self.access_token:
            return True
        age = self.age_seconds()
        if age is None:
            return True
        try:
            ttl = int(self.data.get("expires_in") or 3600)
        except (TypeError, ValueError):
            ttl = 3600
        return age > (ttl - margin)

    def refresh(self):
        log("Token yenileniyor (refresh_token -> yeni access + refresh)...")
        r = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": self.keystring,
                "refresh_token": self.data["refresh_token"],
            },
            headers={"x-api-key": self.api_key_header},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            # Govde token icermez; hata metni guvenle basilabilir.
            raise SystemExit(f"HATA: token yenileme {r.status_code}: {r.text[:300]}")
        body = r.json()
        for k in ("access_token", "refresh_token"):
            if not body.get(k):
                raise SystemExit(f"HATA: token cevabinda {k} yok.")
            mask(body[k])
        self.data["access_token"] = body["access_token"]
        self.data["refresh_token"] = body["refresh_token"]
        self.data["obtained_at"] = datetime.now(timezone.utc).strftime(self.DATE_FMT)
        if body.get("expires_in") is not None:
            self.data["expires_in"] = body["expires_in"]
        if body.get("token_type"):
            self.data["token_type"] = body["token_type"]
        self.write()
        log("Token yenilendi ve dosyaya geri yazildi.")

    def write(self):
        text = json.dumps(self.data, indent=2 if self.pretty else None, ensure_ascii=False)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(text + ("\n" if self.pretty else ""), encoding="utf-8")
        os.replace(tmp, self.path)
        self.updated = True
        Path(str(self.path) + ".updated").write_text("1")


# ------------------------------------------------------------------ api
class Etsy:
    def __init__(self, store):
        self.store = store
        self.calls = 0
        self.remaining = None
        self.pace = 0.25  # sn; 5 QPS sinirinin altinda kalir

    def _headers(self):
        return {
            "x-api-key": self.store.api_key_header,
            "Authorization": f"Bearer {self.store.access_token}",
        }

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params=params, ok404=ok404)

    def patch(self, path, data):
        """updateListing gibi form-encoded PATCH. Yazma cagrisi; onay kapisi
        cagiranin sorumlulugundadir."""
        return self._call("PATCH", path, data=data)

    def put(self, path, data):
        return self._call("PUT", path, data=data)

    def post(self, path, data):
        return self._call("POST", path, data=data)

    def _call(self, method, path, params=None, data=None, ok404=False):
        for attempt in range(3):
            self.calls += 1
            time.sleep(self.pace)
            r = requests.request(method, API + path, params=params, data=data,
                                 headers=self._headers(), timeout=TIMEOUT)
            rem = r.headers.get("x-remaining-today")
            if rem is not None:
                self.remaining = rem
            if r.status_code == 401 and attempt == 0:
                log("401 alindi, token yenilenip tekrar denenecek.")
                self.store.refresh()
                continue
            if r.status_code == 404 and ok404:
                return None
            if r.status_code == 429:
                # Kisa retry-after = saniyelik hiz siniri (5 QPS): bekle, tekrar dene.
                # Uzun retry-after = gunluk kota: temiz cik (B61 dersi).
                try:
                    wait = float(r.headers.get("retry-after") or 0)
                except ValueError:
                    wait = 0
                if 0 < wait <= 60 and attempt < 2:
                    time.sleep(wait + 0.5)
                    continue
                raise SystemExit(
                    f"HATA: 429 kota. retry-after={r.headers.get('retry-after')}"
                )
            if r.status_code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise SystemExit(f"HATA: {method} {path} -> {r.status_code}: {r.text[:300]}")
            return r.json()
        raise SystemExit(f"HATA: {method} {path} tekrarlar tukendi.")


