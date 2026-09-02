#!/usr/bin/env python3
"""
Instagram gunluk yayin scripti (REEL / CAROUSEL / STORY).

Plan: Drive'daki WA_IG_PLAN sheet'i (Sheets API, rclone.conf'daki OAuth
kimligiyle). Bugunun (Europe/Istanbul) satiri bulunur; uc tur birbirinden
bagimsiz islenir:

  REEL      REEL_URL  + CAPTION_REEL      durum sutunu ST_REEL
  CAROUSEL  carousel_v2/D<NN>/slide_1..5  + CAPTION_CAROUSEL   ST_CAR
  STORY     STORY_URL (caption yok)                            ST_STORY

Durum makinesi (tekrar yayin korumasi):
  bos                         -> yayinla
  PENDING <ts> [container]    -> ATLA + uyari (cokme sonrasi elle bak)
  OK <media_id> <ts>          -> atla
  ERR <sebep> <ts>            -> atla (otomatik retry yok)
  SKIP_DUP <gun> <ts>         -> atla

Yazma sirasi: once PENDING, sonra container, sonra publish, sonra OK.
media_publish ASLA yeniden denenmez; belirsiz sonuc ERR olarak kalir.

Ayni cift + ayni medya daha erken bir gunde OK ise (or. D79 = D01) o tur
yayinlanmaz, SKIP_DUP <erken gun> yazilir.

Kullanim:
  publish.py --dry-run            # hicbir sey yazmaz/yayinlamaz
  publish.py --date 2026-09-07    # baska gun (test)
  publish.py --only reel,story
"""
import argparse
import configparser
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ----------------------------------------------------------------- ayarlar
SHEET_ID = os.environ.get("IG_PLAN_SHEET_ID", "1Cg--wybFqdCON9XCE-xF3F9FTiE5n6gIDnzJcpFdYhY")
MEDIA_BASE = os.environ.get("MEDIA_BASE", "https://caliserdar-maker.github.io/astrolove-media").rstrip("/")
GRAPH_BASE = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/")
API_VER = os.environ.get("IG_API_VERSION", "v21.0")
TZ = ZoneInfo("Europe/Istanbul")
RCLONE_CONF = Path(os.environ.get("RCLONE_CONFIG", Path.home() / ".config/rclone/rclone.conf"))
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")

CAPTION_MAX = 2200
N_SLIDES = 5
POLL_EVERY, POLL_MAX = 5, 300           # video container hazirlik yoklamasi (sn)
HTTP_TIMEOUT = 60

# tur -> (durum sutunu, caption sutunu)
KINDS = {
    "REEL":     ("ST_REEL",  "CAPTION_REEL"),
    "CAROUSEL": ("ST_CAR",   "CAPTION_CAROUSEL"),
    "STORY":    ("ST_STORY", None),
}


def log(msg):
    print(msg, flush=True)


def now_ts():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short(reason, n=60):
    return re.sub(r"\s+", "_", str(reason).strip())[:n]


# ------------------------------------------------------- Google (Sheets) kimligi
def google_access_token():
    """rclone.conf'daki gdrive remote'unun OAuth kimligiyle access token uretir."""
    if not RCLONE_CONF.exists():
        raise RuntimeError(f"rclone.conf yok: {RCLONE_CONF}")
    cp = configparser.ConfigParser()
    cp.read(RCLONE_CONF)
    if RCLONE_REMOTE not in cp:
        raise RuntimeError(f"rclone.conf icinde [{RCLONE_REMOTE}] yok")
    sec = cp[RCLONE_REMOTE]
    client_id = os.environ.get("RCLONE_CONFIG_GDRIVE_CLIENT_ID") or sec.get("client_id", "")
    client_secret = os.environ.get("RCLONE_CONFIG_GDRIVE_CLIENT_SECRET") or sec.get("client_secret", "")
    tok = json.loads(sec.get("token", "{}"))
    if not (client_id and client_secret and tok.get("refresh_token")):
        raise RuntimeError("rclone.conf: client_id / client_secret / refresh_token eksik")
    r = requests.post("https://oauth2.googleapis.com/token", timeout=HTTP_TIMEOUT, data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError(f"Google token yenileme basarisiz ({r.status_code}): {r.text[:200]}")
    return r.json()["access_token"]


class Sheet:
    """WA_IG_PLAN uzerinde okuma/yazma (Sheets API v4, REST)."""

    def __init__(self, access_token, sheet_id=SHEET_ID):
        self.h = {"Authorization": f"Bearer {access_token}"}
        self.base = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        meta = requests.get(self.base, headers=self.h, timeout=HTTP_TIMEOUT,
                            params={"fields": "sheets.properties.title"})
        meta.raise_for_status()
        self.tab = meta.json()["sheets"][0]["properties"]["title"]
        self.hdr_row = None      # 1 tabanli baslik satiri
        self.idx = {}            # sutun adi -> 0 tabanli indeks

    def load(self):
        r = requests.get(f"{self.base}/values/{self._q(self.tab)}!A1:ZZ500",
                         headers=self.h, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        rows = r.json().get("values", [])
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row]
            if "GUN" in cells and "PAIR" in cells:
                self.hdr_row = i + 1
                self.idx = {h: n for n, h in enumerate(cells) if h}
                body = rows[i + 1:]
                break
        else:
            raise RuntimeError("planda GUN/PAIR basligi yok")
        need = ["GUN", "TARIH", "PAIR", "EDITION", "CAROUSEL_EDITION", "REEL_URL", "STORY_URL",
                "CAPTION_REEL", "CAPTION_CAROUSEL", "ST_REEL", "ST_CAR", "ST_STORY"]
        miss = [c for c in need if c not in self.idx]
        if miss:
            raise RuntimeError(f"planda eksik sutun: {miss}")
        out = []
        for off, row in enumerate(body):
            rec = {h: (row[n].strip() if n < len(row) else "") for h, n in self.idx.items()}
            if not rec["GUN"].isdigit():
                continue
            rec["_row"] = self.hdr_row + 1 + off       # 1 tabanli sheet satiri
            rec["GUN"] = int(rec["GUN"])
            out.append(rec)
        return out

    def write(self, row, col, value):
        a1 = f"{self._q(self.tab)}!{self._col(self.idx[col])}{row}"
        r = requests.put(f"{self.base}/values/{a1}", headers=self.h, timeout=HTTP_TIMEOUT,
                         params={"valueInputOption": "RAW"},
                         json={"range": a1, "values": [[value]]})
        r.raise_for_status()

    @staticmethod
    def _q(tab):
        return "'" + tab.replace("'", "''") + "'"

    @staticmethod
    def _col(i):
        s = ""
        i += 1
        while i:
            i, rem = divmod(i - 1, 26)
            s = chr(65 + rem) + s
        return s


# ------------------------------------------------------------ Instagram Graph
class Graph:
    def __init__(self, token, user_id):
        self.token, self.user = token, user_id
        self.base = f"{GRAPH_BASE}/{API_VER}"

    def _post(self, path, retry=3, **params):
        params["access_token"] = self.token
        for i in range(retry):
            r = requests.post(f"{self.base}/{path}", data=params, timeout=HTTP_TIMEOUT)
            if r.status_code < 500 and r.status_code != 429:
                break
            time.sleep(2 ** i)
        try:
            j = r.json()
        except ValueError:
            j = {"error": {"message": r.text[:200]}}
        if r.status_code != 200 or "error" in j:
            raise RuntimeError(j.get("error", {}).get("message", f"HTTP {r.status_code}"))
        return j

    def _get(self, path, **params):
        params["access_token"] = self.token
        for i in range(3):
            r = requests.get(f"{self.base}/{path}", params=params, timeout=HTTP_TIMEOUT)
            if r.status_code < 500 and r.status_code != 429:
                break
            time.sleep(2 ** i)
        r.raise_for_status()
        return r.json()

    def create_container(self, **params):
        return self._post(f"{self.user}/media", **params)["id"]

    def wait_ready(self, cid):
        t0 = time.time()
        while time.time() - t0 < POLL_MAX:
            st = self._get(cid, fields="status_code,status").get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {st}")
            time.sleep(POLL_EVERY)
        raise RuntimeError("container hazir olmadi (zaman asimi)")

    def publish(self, cid):
        # TEK deneme: yanit belirsizse ERR kalir, ikinci kez atilmaz.
        params = {"creation_id": cid, "access_token": self.token}
        r = requests.post(f"{self.base}/{self.user}/media_publish", data=params, timeout=HTTP_TIMEOUT)
        j = r.json() if r.content else {}
        if r.status_code != 200 or "id" not in j:
            raise RuntimeError(j.get("error", {}).get("message", f"publish HTTP {r.status_code}"))
        return j["id"]


# ------------------------------------------------------------------- yardimci
def carousel_urls(gun):
    return [f"{MEDIA_BASE}/carousel_v2/D{gun:02d}/slide_{i}.jpg" for i in range(1, N_SLIDES + 1)]


def head_ok(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
        if r.status_code == 405:                      # HEAD desteklenmiyorsa
            r = requests.get(url, stream=True, timeout=30)
        return r.status_code == 200, r.status_code
    except requests.RequestException as e:
        return False, type(e).__name__


def media_of(kind, rec):
    """Tur icin (medya tanimlayicisi, url listesi)."""
    if kind == "REEL":
        return rec["REEL_URL"], [rec["REEL_URL"]]
    if kind == "STORY":
        return rec["STORY_URL"], [rec["STORY_URL"]]
    return rec["CAROUSEL_EDITION"], carousel_urls(rec["GUN"])


def find_dup(kind, rec, plan):
    """Ayni cift + ayni medya daha erken bir gunde OK ise o gunu dondurur."""
    key = (rec["PAIR"], media_of(kind, rec)[0])
    st_col = KINDS[kind][0]
    for other in plan:
        if other["GUN"] >= rec["GUN"]:
            continue
        if (other["PAIR"], media_of(kind, other)[0]) == key and other[st_col].startswith("OK"):
            return other["GUN"]
    return None


def status_word(v):
    return v.split()[0] if v else ""


# --------------------------------------------------------------------- akis
def process_kind(kind, rec, plan, sheet, graph, dry):
    st_col, cap_col = KINDS[kind]
    row, cur = rec["_row"], rec[st_col]
    tag = f"D{rec['GUN']:02d} {kind:<8}"

    if cur:
        w = status_word(cur)
        if w == "PENDING":
            log(f"{tag} | ATLA  | {cur}  <-- PENDING kalmis, elle kontrol gerekiyor")
            return "PENDING"
        log(f"{tag} | atla  | {cur}")
        return w

    dup = find_dup(kind, rec, plan)
    if dup is not None:
        val = f"SKIP_DUP D{dup:02d} {now_ts()}"
        log(f"{tag} | {'(dry) ' if dry else ''}SKIP_DUP | ayni cift+medya D{dup:02d}'de zaten OK -> {val}")
        if not dry:
            sheet.write(row, st_col, val)
        return "SKIP_DUP"

    ident, urls = media_of(kind, rec)
    caption = rec[cap_col] if cap_col else ""
    problems = []
    if not ident:
        problems.append("medya alani bos")
    if cap_col and len(caption) > CAPTION_MAX:
        problems.append(f"caption {len(caption)} > {CAPTION_MAX}")
    if kind == "CAROUSEL" and rec.get("N_SLIDES") and rec["N_SLIDES"] != str(N_SLIDES):
        problems.append(f"N_SLIDES={rec['N_SLIDES']} != {N_SLIDES}")
    for u in urls:
        ok, code = head_ok(u)
        if not ok:
            problems.append(f"HEAD {code}: {u.rsplit('/', 2)[-2]}/{u.rsplit('/', 1)[-1]}")
    if problems:
        val = f"ERR {short('; '.join(problems))} {now_ts()}"
        log(f"{tag} | {'(dry) ' if dry else ''}ERR   | {'; '.join(problems)}")
        if not dry:
            sheet.write(row, st_col, val)
        return "ERR"

    if dry:
        log(f"{tag} | (dry) YAYINLANIR | {len(urls)} medya | caption {len(caption)} kr | {ident if kind != 'CAROUSEL' else 'carousel_v2/D%02d' % rec['GUN']}")
        return "DRY"

    # --- gercek yayin: once PENDING ---
    sheet.write(row, st_col, f"PENDING {now_ts()}")
    try:
        if kind == "REEL":
            cid = graph.create_container(media_type="REELS", video_url=urls[0], caption=caption)
            sheet.write(row, st_col, f"PENDING {now_ts()} {cid}")
            graph.wait_ready(cid)
        elif kind == "STORY":
            cid = graph.create_container(media_type="STORIES", video_url=urls[0])
            sheet.write(row, st_col, f"PENDING {now_ts()} {cid}")
            graph.wait_ready(cid)
        else:
            children = [graph.create_container(image_url=u, is_carousel_item="true") for u in urls]
            cid = graph.create_container(media_type="CAROUSEL", children=",".join(children), caption=caption)
            sheet.write(row, st_col, f"PENDING {now_ts()} {cid}")
            graph.wait_ready(cid)
        media_id = graph.publish(cid)
    except Exception as e:
        val = f"ERR {short(e)} {now_ts()}"
        sheet.write(row, st_col, val)
        log(f"{tag} | ERR   | {e}")
        return "ERR"
    sheet.write(row, st_col, f"OK {media_id} {now_ts()}")
    log(f"{tag} | OK    | media {media_id}")
    return "OK"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="sheet'e yazma, yayinlama; ne yapacagini goster")
    ap.add_argument("--date", help="YYYY-MM-DD (varsayilan: bugun, Europe/Istanbul)")
    ap.add_argument("--only", help="virgullu tur listesi: reel,carousel,story")
    a = ap.parse_args()

    today = a.date or dt.datetime.now(TZ).strftime("%Y-%m-%d")
    kinds = [k for k in KINDS if not a.only or k.lower() in a.only.lower().split(",")]
    log(f"tarih {today} (Europe/Istanbul) | turler {', '.join(kinds)} | {'DRY-RUN' if a.dry_run else 'GERCEK YAYIN'}")

    sheet = Sheet(google_access_token())
    plan = sheet.load()
    todays = [r for r in plan if r["TARIH"] == today]
    if not todays:
        log("bugun icin plan satiri yok, cikiliyor."); return
    if len(todays) > 1:
        log(f"UYARI: {today} icin {len(todays)} satir var, ilki kullaniliyor.")
    rec = todays[0]
    log(f"satir {rec['_row']}: D{rec['GUN']:02d} {rec['PAIR']} | reel/story {rec['EDITION']} | carousel {rec['CAROUSEL_EDITION']}")

    token, uid = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
    if not a.dry_run and not (token and uid):
        raise SystemExit("HATA: IG_TOKEN / IG_USER_ID yok (gercek yayin icin zorunlu).")
    if a.dry_run and not (token and uid):
        log("not: IG_TOKEN/IG_USER_ID tanimsiz; dry-run Graph API'ye dokunmaz.")
    graph = Graph(token, uid) if (token and uid) else None

    results = {k: process_kind(k, rec, plan, sheet, graph, a.dry_run) for k in kinds}
    log("-" * 60)
    log(" | ".join(f"{k}: {v}" for k, v in results.items()))

    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"## IG publish {today} — D{rec['GUN']:02d} {rec['PAIR']} ({'dry-run' if a.dry_run else 'yayin'})\n\n"
                    "| Tur | Sonuc |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in results.items()))
    if "PENDING" in results.values():
        log("UYARI: PENDING kalmis tur var; container_id ile Graph API'den durumu kontrol et.")
    if "ERR" in results.values() and not a.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
