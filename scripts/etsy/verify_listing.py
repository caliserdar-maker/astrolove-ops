#!/usr/bin/env python3
"""
Etsy listing dogrulama (SALT OKUR).

Tek bir listing'i Etsy Open API v3 uzerinden okur ve durumunu CSV + Markdown
olarak yazar. Etsy'ye hicbir yazma cagrisi yapmaz. Tek "yazma" isi OAuth
token yenilemesidir: access token suresi dolmussa refresh token ile yenilenir
ve donen YENI refresh token ayni dosyaya geri yazilir (Etsy her yenilemede
eskisini gecersiz kilar; dosya token zincirinin tek kaynagidir).

Okunanlar:
  state, fiyat, gorsel sayisi + rank sirasi (+ Drive'daki beklenen dosyalarla
  imza eslestirmesi), video sayisi, dijital dosya sayisi ve adlari.

Ortam degiskenleri:
  ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID   (GitHub Secrets)
  TOKEN_FILE      Drive'dan kopyalanmis ETSY_TOKEN.json yolu
  LISTING_ID      okunacak listing
  OUT_CSV         CSV cikti yolu
  EXPECT_DIR      (istege bagli) beklenen galeri gorsellerinin klasoru
  EXPECT_ORDER    (istege bagli) virgullu beklenen sira, or. SET01,SET03,...
  GITHUB_STEP_SUMMARY  varsa Markdown ozet buraya eklenir

Hicbir sir loga yazilmaz; okunan her token degeri once ::add-mask:: ile
maskelenir.
"""
import csv
import io
import json
import os
import sys
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

    def _headers(self):
        return {
            "x-api-key": self.store.api_key_header,
            "Authorization": f"Bearer {self.store.access_token}",
        }

    def get(self, path, params=None, ok404=False):
        for attempt in range(3):
            self.calls += 1
            r = requests.get(API + path, params=params, headers=self._headers(), timeout=TIMEOUT)
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
                raise SystemExit(
                    f"HATA: 429 kota. retry-after={r.headers.get('retry-after')}"
                )
            if r.status_code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise SystemExit(f"HATA: GET {path} -> {r.status_code}: {r.text[:300]}")
            return r.json()
        raise SystemExit(f"HATA: GET {path} tekrarlar tukendi.")


def find_listing(api, shop_id, listing_id):
    """Once dogrudan; taslaklarda 404 gelirse magaza taslak listesinden."""
    data = api.get(f"/listings/{listing_id}", params={"includes": "Images,Videos"}, ok404=True)
    if data:
        return data, "listings/{id}"
    for state in ("draft", "inactive", "active", "expired", "sold_out"):
        offset = 0
        while True:
            page = api.get(
                f"/shops/{shop_id}/listings",
                params={"state": state, "limit": 100, "offset": offset},
            )
            for it in page.get("results", []):
                if int(it.get("listing_id", 0)) == int(listing_id):
                    return it, f"shops/{{shop}}/listings?state={state}"
            offset += 100
            if offset >= int(page.get("count", 0)):
                break
    raise SystemExit(f"HATA: listing {listing_id} hicbir state'te bulunamadi.")


def money(obj):
    if not isinstance(obj, dict):
        return ""
    amt, div = obj.get("amount"), obj.get("divisor") or 1
    if amt is None:
        return ""
    return f"{amt / div:.2f} {obj.get('currency_code', '')}".strip()


# ------------------------------------------------------------------ imza
def signature(img_bytes):
    from PIL import Image
    import numpy as np

    im = Image.open(io.BytesIO(img_bytes)).convert("L").resize((96, 72), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64)
    a -= a.mean()
    n = np.linalg.norm(a)
    return a / n if n else a


def load_expected(expect_dir):
    from pathlib import Path

    out = {}
    if not expect_dir or not Path(expect_dir).is_dir():
        return out
    for p in sorted(Path(expect_dir).glob("*.jp*g")):
        out[p.name] = signature(p.read_bytes())
    return out


def match_image(url, expected):
    import numpy as np

    r = requests.get(url, timeout=TIMEOUT)
    if r.status_code != 200 or not expected:
        return "", 0.0, ""
    sig = signature(r.content)
    scores = sorted(
        ((float(np.sum(sig * e)), name) for name, e in expected.items()), reverse=True
    )
    best_score, best = scores[0]
    second = scores[1][0] if len(scores) > 1 else 0.0
    return best, best_score, f"{second:.3f}"


def set_code(filename):
    """WA_MOCKUP_V2_SET10_YAZILI_Cancer_Libra_FINAL.jpg -> SET10Y, SET04 -> SET04"""
    import re

    m = re.search(r"(SET\d{2})(_YAZILI)?", filename)
    if not m:
        return filename
    return m.group(1) + ("Y" if m.group(2) else "")


# ------------------------------------------------------------------ main
def main():
    keystring = os.environ.get("ETSY_API_KEY", "")
    shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring)
    mask(shared)
    token_file = os.environ["TOKEN_FILE"]
    listing_id = os.environ["LISTING_ID"]
    out_csv = os.environ.get("OUT_CSV", "verify.csv")
    expect_dir = os.environ.get("EXPECT_DIR", "")
    expect_order = [s.strip() for s in os.environ.get("EXPECT_ORDER", "").split(",") if s.strip()]
    if not shop_id:
        raise SystemExit("HATA: ETSY_SHOP_ID tanimli degil.")

    store = TokenStore(token_file, keystring, shared)
    age = store.age_seconds()
    log(f"Token yasi: {'bilinmiyor' if age is None else f'{age/60:.1f} dk'}; "
        f"yenileme gerekli: {store.needs_refresh()}")
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    listing, via = find_listing(api, shop_id, listing_id)
    images = api.get(f"/listings/{listing_id}/images", ok404=True)
    if images is None:
        images = api.get(f"/shops/{shop_id}/listings/{listing_id}/images", ok404=True) or {}
    videos = api.get(f"/listings/{listing_id}/videos", ok404=True) or {}
    files = api.get(f"/shops/{shop_id}/listings/{listing_id}/files", ok404=True) or {}
    inventory = api.get(f"/listings/{listing_id}/inventory", ok404=True) or {}

    inv_price = ""
    try:
        inv_price = money(inventory["products"][0]["offerings"][0]["price"])
    except (KeyError, IndexError, TypeError):
        pass

    img_rows = sorted(images.get("results", []), key=lambda x: x.get("rank", 0))
    expected = load_expected(expect_dir)
    if expected:
        log(f"Beklenen galeri gorseli: {len(expected)} dosya ({expect_dir}).")
    matched = []
    for im in img_rows:
        url = im.get("url_570xN") or im.get("url_fullxfull")
        best, score, second = ("", 0.0, "") if not expected else match_image(url, expected)
        matched.append(
            dict(
                rank=im.get("rank"),
                image_id=im.get("listing_image_id"),
                w=im.get("full_width"),
                h=im.get("full_height"),
                match=set_code(best) if best else "",
                match_file=best,
                score=f"{score:.3f}",
                second=second,
            )
        )
    actual_order = [m["match"] for m in matched]
    order_ok = ""
    if expect_order and expected:
        order_ok = "PASS" if actual_order == expect_order else "FAIL"

    file_rows = files.get("results", [])
    video_rows = videos.get("results", [])

    fields = [
        ("listing_id", listing.get("listing_id")),
        ("bulundu_via", via),
        ("state", listing.get("state")),
        ("title", listing.get("title")),
        ("price_listing", money(listing.get("price"))),
        ("price_inventory", inv_price),
        ("quantity", listing.get("quantity")),
        ("shop_section_id", listing.get("shop_section_id")),
        ("listing_type", listing.get("listing_type")),
        ("num_images", len(img_rows)),
        ("image_order", "-".join(a or "?" for a in actual_order) if expected else "(imza yok)"),
        ("expected_order", "-".join(expect_order)),
        ("order_check", order_ok),
        ("num_videos", len(video_rows)),
        ("video_ids", ";".join(str(v.get("video_id")) for v in video_rows)),
        ("num_files", len(file_rows)),
        ("file_names", ";".join(str(f.get("filename")) for f in file_rows)),
        ("file_sizes", ";".join(str(f.get("size_bytes")) for f in file_rows)),
        ("api_calls", api.calls),
        ("x_remaining_today", api.remaining),
        ("token_refreshed", store.updated),
        ("checked_at_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    ]

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["alan", "deger"])
        for k, v in fields:
            w.writerow([k, v])
        w.writerow([])
        w.writerow(["rank", "image_id", "w", "h", "match", "score", "second_best", "match_file"])
        for m in matched:
            w.writerow([m["rank"], m["image_id"], m["w"], m["h"], m["match"], m["score"],
                        m["second"], m["match_file"]])

    md = [f"## Etsy listing {listing_id} dogrulama (salt okur)", "",
          "| alan | deger |", "|---|---|"]
    for k, v in fields:
        md.append(f"| {k} | {v} |")
    md += ["", "| rank | image_id | boyut | eslesme | skor | 2. aday |", "|---|---|---|---|---|---|"]
    for m in matched:
        md.append(f"| {m['rank']} | {m['image_id']} | {m['w']}x{m['h']} | {m['match']} | "
                  f"{m['score']} | {m['second']} |")
    md_text = "\n".join(md)
    log(md_text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(md_text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
