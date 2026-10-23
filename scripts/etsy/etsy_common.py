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
        mask(keystring)
        mask(shared_secret)
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


class APIKeyStore:
    """Public GET endpoints need only ``x-api-key``; never reads OAuth data."""

    def __init__(self, keystring, shared_secret):
        if not keystring or not shared_secret:
            raise SystemExit("HATA: ETSY_API_KEY/ETSY_SHARED_SECRET eksik.")
        mask(keystring)
        mask(shared_secret)
        self.keystring = keystring
        self.shared_secret = shared_secret
        self.access_token = None

    @property
    def api_key_header(self):
        return f"{self.keystring}:{self.shared_secret}"

    def refresh(self):
        raise SystemExit("HATA: Bu is OAuth kullanmaz; public uc 401 dondurdu.")


# ------------------------------------------------------------------ kota esigi
# Serdar 23 Eki: genel isler kalan < taban + 2R + M ise baslamaz / ilana baslamaz (her istekte sert taban taban + 2R);
# pod-audit taban + 2R + P; siparis rolu (kupa-siparis, takip-denetim) yalniz sert taban taban + R; router muaf (kendi
# --quota-min 400). Rakamlar ve "aktif" config/etsy_kota_esik.json'da; dosya yoksa / aktif degilse / bozuksa etkisiz.
KOTA_ESIK_DOSYA = Path(__file__).resolve().parents[2] / "config" / "etsy_kota_esik.json"


def kota_esigi(rol=None, dosya=None):
    """-> (esik, sert_taban) ya da (None, None). rol (ETSY_KOTA_ROL, varsayilan genel):
      genel     : esik taban + 2R + M (kosu ve ilan baslangici), sert taban taban + 2R (her istekten once)
      pod-audit : esik taban + 2R + P, sert taban taban + 2R
      siparis   : (kupa-siparis, takip-denetim; Serdar 23 Eki) baslangic esigi yok, sert taban taban + R
      router    : muaf (kendi --quota-min 400)
    aktif false ise sessizce etkisiz. Dosya yoksa, aktif true/false disinda bir degerse (ya da yoksa), dosya okunamaz ya da
    alan eksikse UYARI + PASIF (Serdar 23 Eki: bozuk config hicbir kosuyu durdurmaz, ama sessizce de kapanmaz)."""
    p = Path(dosya or KOTA_ESIK_DOSYA)
    if not p.exists():
        log(f"::warning::KOTA ESIGI PASIF: {p.name} yok; hicbir kosu durdurulmaz")
        return None, None
    try:
        c = json.loads(p.read_text(encoding="utf-8"))
        aktif = c.get("aktif", "(yok)")
        if aktif is False:
            return None, None
        if aktif is not True:
            log(f"::warning::KOTA ESIGI PASIF: {p.name} aktif alani true/false degil ({str(aktif)[:20]!r}); "
                "hicbir kosu durdurulmaz")
            return None, None
        say = [c[k] for k in ("taban", "R", "M", "P")]
        if not all(type(v) is int and 0 <= v < 5000 for v in say):
            raise ValueError("taban/R/M/P 0-4999 arasi tamsayi olmali")
        taban, r, m, pp = say
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log(f"::warning::KOTA ESIGI PASIF: {p.name} okunamadi ya da eksik ({type(e).__name__}); hicbir kosu durdurulmaz")
        return None, None
    rol = rol or os.environ.get("ETSY_KOTA_ROL", "genel")
    if rol not in ("genel", "pod-audit", "siparis", "router"):
        log(f"::warning::ETSY_KOTA_ROL bilinmiyor ({rol}); siparis tabani (taban + R) uygulanir, siparis isi durmasin")
        rol = "siparis"
    if rol == "router":
        return None, None
    if rol == "siparis":
        return None, taban + r
    return taban + 2 * r + (pp if rol == "pod-audit" else m), taban + 2 * r


# ------------------------------------------------------------------ api
class Etsy:
    def __init__(self, store):
        self.store = store
        self.calls = 0
        self.remaining = None
        self.esik, self.sert_taban = kota_esigi()
        self._kapi_bakildi = False
        if self.sert_taban is not None:
            log(f"KOTA ESIGI aktif: kosu/ilan {self.esik if self.esik is not None else 'yok'}, sert taban (her istek) {self.sert_taban}")
        self.pace = 0.25  # sn; 5 QPS sinirinin altinda kalir
        self.verbose_quota = False  # True: her istekten sonra x-remaining-today loglanir (C gorevi, 5 Eyl 2026)

    def kota_kapisi(self, ne="is"):
        """Ise / ilana baslamadan cagrilir: kalan < esik ise SystemExit (kosu kirmizi, GitHub e-postasi). Esik pasifse etkisiz."""
        if self.esik is not None and self.remaining is not None and int(self.remaining) < self.esik:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < {self.esik} ({ne} baslamadi)")

    def _istek_oncesi(self):
        """Esik aktifken: ilk yanittan sonra kosu kapisi (esik) bir kez; sert taban (genel/pod-audit taban + 2R, siparis
        taban + R) HER istekten once.
        SystemExit'i yakalayip devam eden betiklerde de sonraki her istek yine durur (payin altina inilmez)."""
        if self.sert_taban is None:
            return
        if self.remaining is None:
            if self.calls:
                raise SystemExit("DUR: kota esigi aktif ama x-remaining-today basligi okunamadi")
            return
        if not self._kapi_bakildi:
            self._kapi_bakildi = True
            self.kota_kapisi("kosu")
        if int(self.remaining) < self.sert_taban:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < {self.sert_taban}")

    def _headers(self):
        headers = {"x-api-key": self.store.api_key_header}
        if self.store.access_token:
            headers["Authorization"] = f"Bearer {self.store.access_token}"
        return headers

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

    def delete(self, path):
        return self._call("DELETE", path)

    def post_json(self, path, body):
        """JSON govdeli POST (ic ice dizi gerektiren uclar). Yazma cagrisi."""
        return self._call("POST", path, json_body=body)

    def put_json(self, path, body):
        """JSON govdeli PUT (updateListingInventory, updateVariationImages). Yazma cagrisi."""
        return self._call("PUT", path, json_body=body)

    def post_file(self, path, files, data=None):
        """Multipart yukleme (gorsel/dosya). Ilk denemede 400 normal olabilir
        (B37); 3 deneme."""
        self._istek_oncesi()
        for attempt in range(3):
            self.calls += 1
            time.sleep(self.pace)
            for f in files.values():
                try:
                    f[1].seek(0)
                except Exception:
                    pass
            r = requests.post(API + path, files=files, data=data, headers=self._headers(), timeout=180)
            rem = r.headers.get("x-remaining-today")
            if rem is not None:
                self.remaining = rem
            if self.verbose_quota:
                log(f"      kota {rem} | POST(file) {path} -> {r.status_code}")
            if r.status_code == 401 and attempt == 0:
                self.store.refresh()
                continue
            if r.status_code in (200, 201):
                return r.json()
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise SystemExit(f"HATA: POST(file) {path} -> {r.status_code}: {r.text[:300]}")
        raise SystemExit(f"HATA: POST(file) {path} tekrarlar tukendi.")

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        self._istek_oncesi()
        for attempt in range(3):
            self.calls += 1
            time.sleep(self.pace)
            r = requests.request(method, API + path, params=params, data=data, json=json_body,
                                 headers=self._headers(), timeout=TIMEOUT)
            rem = r.headers.get("x-remaining-today")
            if rem is not None:
                self.remaining = rem
            if self.verbose_quota:
                log(f"      kota {rem} | {method} {path} -> {r.status_code}")
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
            if r.status_code == 204:
                return {}
            if r.status_code not in (200, 201):          # 201: createShopShippingProfileDestination gibi olusturma uclari (6 Eyl)
                raise SystemExit(f"HATA: {method} {path} -> {r.status_code}: {r.text[:300]}")
            return r.json()
        raise SystemExit(f"HATA: {method} {path} tekrarlar tukendi.")

