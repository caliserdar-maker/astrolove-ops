#!/usr/bin/env python3
"""Kendi paylasim sistemi sahte testi. AG KAPALI: socket bastan engellenir; HTTP sahte oturum, rclone PATH'te sahte arac
(Drive = gecici klasor). Bilinen PASS: IG reel / karusel, Threads metin, FB reel + gorsel, YT short, kuru kosu (yazim 0),
onayla (ONAY + ozet + genel medya), izin cevir (token Drive'a, kod sirri silinir), token yenileme.
Bilinen FAIL: onaysiz, ozet farkli, medya farkli, media_publish 500 (tek deneme, BELIRSIZ), BEKLIYOR, 6 saat gec (KACTI),
anahtar kapali, son an DURUM dolu, sir sorguda, hata metninde token, yenileme hatasi uyari. Mutasyon: onay kapisi bozulunca test FAIL."""
import hashlib
import io
import json
import os
import shutil
import socket
import stat
import sys
import tempfile
import contextlib
import csv
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
TMP = Path(tempfile.mkdtemp(prefix="yayin_test_"))
DRIVE = TMP / "drive"
BIN = TMP / "bin"
DRIVE.mkdir()
BIN.mkdir()
(BIN / "rclone").write_text(f"""#!{sys.executable}
import sys, shutil, os
D = {str(DRIVE)!r}
k, a = sys.argv[1], sys.argv[2:]
yol = lambda r: os.path.join(D, r.split(':', 1)[1])
if k == 'cat':
    p = yol(a[0])
    if not os.path.exists(p): sys.stderr.write('not found'); sys.exit(3)
    sys.stdout.write(open(p).read())
elif k == 'rcat':
    p = yol(a[0]); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w').write(sys.stdin.read())
elif k == 'copyto':
    p = yol(a[0])
    if not os.path.exists(p): sys.stderr.write('not found'); sys.exit(3)
    shutil.copyfile(p, a[1])
else:
    sys.exit(9)
""")
(BIN / "rclone").chmod(0o755)
os.environ["PATH"] = f"{BIN}:{os.environ['PATH']}"
CONF = TMP / "rclone.conf"
CONF.write_text('[gdrive]\ntype = drive\nclient_id = cid\nclient_secret = GSECRET0123456789\ntoken = {"refresh_token": "GREFRESH0123456789"}\n')
os.environ.update(RCLONE_CONFIG=str(CONF), SOSYAL_TAKVIM_ID="SHEET1", GITHUB_ACTIONS="", OPS_ADMIN_TOKEN="ghADMIN0123456789",
                  YT_CLIENT_ID="ytcid", YT_CLIENT_SECRET="YTSECRET0123456789", IG_APP_ID="igapp", IG_APP_SECRET="IGSECRET0123456789")
VAYAR = TMP / "video_kaynak.json"
VAYAR.write_text(json.dumps({"klasor": "SOSYAL", "ad_kalibi": "{a}-and-{b}-pin-video.mp4", "onay": "SERDAR_20261126"}))
os.environ["SOSYAL_VIDEO_KAYNAK"] = str(VAYAR)
for k in ("RCLONE_CONFIG_GDRIVE_CLIENT_ID", "RCLONE_CONFIG_GDRIVE_CLIENT_SECRET"):
    os.environ.pop(k, None)

import ortak  # noqa: E402
import calis  # noqa: E402
import izin  # noqa: E402
import secim  # noqa: E402
import token_yenile  # noqa: E402

TOK = {"instagram": "IGTOKEN_SAHTE_0123456789", "threads": "THTOKEN_SAHTE_0123456789",
       "facebook": "FBPAGETOKEN_SAHTE_0123456789", "youtube": "YTREFRESH_SAHTE_0123456789"}
SIRLAR = list(TOK.values()) + ["GSECRET0123456789", "GREFRESH0123456789", "ghADMIN0123456789", "YTSECRET0123456789",
                               "IGSECRET0123456789", "METASECRET0123456", "FBKISA_SAHTE_0001", "FBUZUN_SAHTE_0002", "GACCESS_SAHTE_99", "YTACCESS_SAHTE_99", "KODSAHTE123456", "IGYENI_SAHTE_0123456789"]
MEDIA = {}  # genel url -> bayt
SIMDI = datetime(2026, 12, 8, 10, 0, tzinfo=secim.TZ)
KANAL = {"instagram": ("ig_id", "1784"), "threads": ("th_id", "2555"), "facebook": ("page_id", "9001"),
         "youtube": ("kanal_id", "UCabc")}


class Y:
    def __init__(self, kod=200, j=None, basliklar=None, icerik=b""):
        self.status_code, self._j, self.headers, self.content = kod, j, basliklar or {}, icerik
        self.text = json.dumps(j) if j is not None else ""

    def json(self):
        if self._j is None:
            raise ValueError("bos")
        return self._j


class Oturum:
    def __init__(self, satirlar):
        self.baslik = secim.SUTUNLAR
        self.satirlar = [[r.get(c, "") for c in self.baslik] for r in satirlar]
        self.cagri = []
        self.publish_500 = False
        self.son_an_durum = False
        self.hata_tokenli = False
        self.yenile_hata = False
        self.kaydir = False
        self.fb = {"hesaplar": [], "hedef": ["9001"], "sayfa_token": True, "gecerli": True, "liste_hedef": None}
        self.tamam_yaz_hata = False

    def _hucre(self, rng):
        a1 = rng.split("!")[1]
        col = "".join(ch for ch in a1 if ch.isalpha())
        row = int("".join(ch for ch in a1 if ch.isdigit()))
        ci = 0
        for ch in col:
            ci = ci * 26 + ord(ch) - 64
        return row - 2, ci - 1

    def request(self, m, url, params=None, data=None, json=None, files=None, headers=None, timeout=None):
        self.cagri.append((m, url, dict(params or {}), data if isinstance(data, dict) else None, dict(headers or {}), json))
        auth = (headers or {}).get("Authorization", "")
        if url.startswith("https://oauth2.googleapis.com/token"):
            if data.get("refresh_token") == "GREFRESH0123456789":
                return Y(j={"access_token": "GACCESS_SAHTE_99"})
            if data.get("grant_type") == "authorization_code":
                return Y(j={"refresh_token": TOK["youtube"], "access_token": "YTACCESS_SAHTE_99"})
            return Y(j={"access_token": "YTACCESS_SAHTE_99"})
        if url.startswith("https://sheets.googleapis.com"):
            assert auth == "Bearer GACCESS_SAHTE_99"
            if m == "GET" and "!" not in url:
                return Y(j={"values": [self.baslik] + self.satirlar})
            if m == "GET" and ":" in url.rsplit("/", 1)[1]:
                r, _ = self._hucre(url.rsplit("/", 1)[1].split(":")[0])
                row = list(self.satirlar[r])
                if self.kaydir:
                    row[0] = "999"
                if self.son_an_durum:
                    row[self.baslik.index("DURUM")] = "BEKLIYOR baska"
                return Y(j={"values": [row]})
            if m == "GET":
                r, c = self._hucre(url.rsplit("/", 1)[1])
                v = self.satirlar[r][c] if c < len(self.satirlar[r]) else ""
                if self.son_an_durum:
                    v = "BEKLIYOR baska"
                return Y(j={"values": [[v]]} if v else {})
            if self.tamam_yaz_hata and any(str(d["values"][0][0]).startswith("TAMAM") for d in json["data"]):
                return Y(500, {"error": {"message": "backend"}})
            for d in json["data"]:
                r, c = self._hucre(d["range"])
                self.satirlar[r][c] = d["values"][0][0]
            return Y(j={"totalUpdatedCells": len(json["data"])})
        if url in MEDIA:
            return Y(icerik=MEDIA[url])
        if "graph.instagram.com" in url:
            if url.endswith("/refresh_access_token"):
                if self.yenile_hata:
                    return Y(400, {"error": {"message": f"bad token {params['access_token']} at {url}?access_token={params['access_token']}"}})
                return Y(j={"access_token": "IGYENI_SAHTE_0123456789", "expires_in": 5184000})
            if url.endswith("/access_token"):
                return Y(j={"access_token": TOK["instagram"], "expires_in": 5184000})
            assert auth.startswith("Bearer "), url
            if url.endswith("/me"):
                return Y(j={"user_id": "1784", "username": "astroloveart"})
            if url.endswith("/insights"):
                return Y(j={"data": [{"name": "views", "values": [{"value": 321}]}, {"name": "likes", "total_value": {"value": 7}}]})
            if url.endswith("/media_publish"):
                if self.publish_500:
                    return Y(500, {"error": {"message": f"oops {auth} {url}?access_token={TOK['instagram']}"}})
                return Y(j={"id": "IGMEDIA77"})
            if url.endswith("/media"):
                n = sum(1 for c in self.cagri if c[1].endswith("/media"))
                return Y(j={"id": f"C{n}"})
            return Y(j={"status_code": "FINISHED"})
        if url.startswith("https://api.instagram.com/oauth/access_token"):
            assert data["code"] == "KODSAHTE123456", data["code"]
            return Y(j={"access_token": "IGKISA_SAHTE_000111", "user_id": 5})
        if "graph.threads.net" in url:
            if url.endswith("/threads_publish"):
                return Y(j={"id": "THPOST1"})
            if url.endswith("/threads"):
                assert "access_token" not in (data or {})
                return Y(j={"id": "THC1"})
            return Y(j={"status": "FINISHED"})
        if "rupload.facebook.com" in url:
            assert auth.startswith("OAuth ")
            return Y(j={"success": True})
        if "graph.facebook.com" in url and (url.endswith("/oauth/access_token") or url.endswith("/me/accounts")
                                            or url.endswith("/debug_token") or url.endswith(("/9001", "/9002", "/7777"))):
            if url.endswith("/oauth/access_token"):
                if params.get("grant_type") == "fb_exchange_token":
                    assert params["fb_exchange_token"] == "FBKISA_SAHTE_0001"
                    return Y(j={"access_token": "FBUZUN_SAHTE_0002"})
                assert params["code"] == "KODSAHTE123456"
                return Y(j={"access_token": "FBKISA_SAHTE_0001"})
            if url.endswith("/me/accounts"):
                assert auth == "Bearer FBUZUN_SAHTE_0002"
                return Y(j={"data": self.fb["hesaplar"]})
            if url.endswith("/debug_token"):
                assert params["input_token"] == "FBUZUN_SAHTE_0002" and params["access_token"] == "1609743017476204|METASECRET0123456"
                if not self.fb["gecerli"]:
                    return Y(j={"data": {"is_valid": False, "error": {"message": "Session has expired"}}})
                gs = [{"scope": "pages_show_list", "target_ids": self.fb["liste_hedef"] or self.fb["hedef"]}]
                if self.fb["hedef"] is not None:
                    gs.append({"scope": "pages_manage_posts", **({"target_ids": self.fb["hedef"]} if self.fb["hedef"] else {})})
                sc = ["pages_show_list"] + (["pages_manage_posts"] if self.fb["hedef"] is not None else [])
                return Y(j={"data": {"is_valid": True, "scopes": sc, "granular_scopes": gs, "data_access_expires_at": 1790000000}})
            assert auth == "Bearer FBUZUN_SAHTE_0002" and "access_token" in params["fields"].split(",")
            pid = url.rsplit("/", 1)[1]
            return Y(j={"id": pid, "name": "AstroLoveArt", **({"access_token": TOK["facebook"]} if self.fb["sayfa_token"] else {})})
        if "graph.facebook.com" in url and url.endswith("/me"):
            return Y(j={"id": "9001", "name": "AstroLoveArt"})
        if "graph.facebook.com" in url:
            if url.endswith("/video_reels"):
                return Y(j={"video_id": "FBV1"} if data["upload_phase"] == "start" else {"success": True})
            if url.endswith("/photos"):
                assert files and "source" in files
                return Y(j={"id": "PH1", "post_id": "9001_55"})
        if "googleapis.com/upload/youtube" in url and m == "POST":
            assert params["uploadType"] == "resumable"
            return Y(j={}, basliklar={"Location": "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=SAHTEUP"})
        if url.startswith("https://www.googleapis.com/upload/youtube/v3/videos?upload_id="):
            return Y(j={"id": "YTVID1"})
        if url.startswith("https://api.github.com/repos/") and m == "DELETE":
            assert auth == "Bearer ghADMIN0123456789"
            return Y(204)
        raise AssertionError(f"beklenmeyen istek {m} {url}")


def drive_koy(yol, bayt):
    p = DRIVE / yol
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(bayt)


def kimlikleri_koy():
    for p, t in TOK.items():
        alan, deger = KANAL[p]
        sir = "refresh_token" if p == "youtube" else "token"
        drive_koy(f"ASTROLOVE/TEMP/SOSYAL_{p.upper()}_TOKEN.json", json.dumps({sir: t, alan: deger}).encode())


def satir(no, platform, tur, medya="", metin="Hello stars", saat=-1, onay=True, durum="", gorunurluk="", md5ler=None):
    s = {"satir_no": str(no), "tarih_saat_TR": (SIMDI + timedelta(hours=saat)).strftime("%Y-%m-%d %H:%M"),
         "platform": platform, "tur": tur, "medya": medya, "metin": metin, "link": "", "pano": "", "yz_beyani": "hayir",
         "gorunurluk": gorunurluk, "DURUM": durum, "sonuc_no": "", "not": ""}
    if onay:
        s["ONAY"] = "SERDAR_20261207"
        s["ONAY_OZET"] = secim.ozet(s, md5ler if md5ler is not None else
                                    [hashlib.md5((DRIVE / m).read_bytes()).hexdigest() for m in medya.split(";") if m])
    return s


def genel(no, i, ext, bayt, ay="202612"):
    MEDIA[f"https://caliserdar-maker.github.io/astrolove-media/yayin/{ay}/{no}_{i}{ext}"] = bayt


def kos(otr, *arg):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = calis.main(list(arg), http=ortak.Http(otr, uyku=lambda *_: None), simdi=SIMDI, uyku=lambda *_: None)
    return rc, out.getvalue()


def satir_al(otr, no):
    for r in otr.satirlar:
        if r[0] == str(no):
            return dict(zip(otr.baslik, r))


SONUC = []


def kontrol(ad, kosul):
    SONUC.append((ad, bool(kosul)))
    print(("PASS " if kosul else "FAIL ") + ad)


def sizinti_yok(*metinler):
    hepsi = "\n".join(metinler) + "".join(p.read_text(errors="ignore") for p in DRIVE.rglob("SOSYAL_HATA_*"))
    return not any(s in hepsi for s in SIRLAR)


def acik(**k):
    os.environ["SOSYAL_YAYIN_ACIK"] = "true"
    for a in calis.ANAHTAR.values():
        os.environ[a] = "true" if a in k.get("hepsi", calis.ANAHTAR.values()) else ""


def sifirla():
    shutil.rmtree(DRIVE)
    DRIVE.mkdir()
    MEDIA.clear()
    kimlikleri_koy()
    drive_koy("SOSYAL/cancer-and-libra-pin-video.mp4", b"REEL")
    drive_koy("SOSYAL/a.jpg", b"JPG-A")
    drive_koy("SOSYAL/b.jpg", b"JPG-B")
    drive_koy("SOSYAL/aries-and-leo-pin-video.mp4", b"SHORT")
    genel(1, 1, ".mp4", b"REEL")
    genel(2, 1, ".jpg", b"JPG-A")
    genel(2, 2, ".jpg", b"JPG-B")


def senaryo_ana():
    sifirla()
    acik()
    rows = [satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4"), satir(2, "instagram", "karusel", "SOSYAL/a.jpg;SOSYAL/b.jpg"),
            satir(3, "threads", "metin"), satir(4, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4"),
            satir(5, "facebook", "gorsel", "SOSYAL/a.jpg"), satir(6, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="private"),
            satir(7, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", onay=False),
            satir(8, "threads", "metin", durum="BEKLIYOR 2026-12-08T09:00"),
            satir(9, "threads", "metin", saat=-7), satir(10, "threads", "metin", saat=+2)]
    r11 = satir(11, "threads", "metin")
    r11["metin"] = "degisti"
    rows.append(r11)
    otr = Oturum(rows)
    rc, out = kos(otr, "yayin")
    d = {n: satir_al(otr, n) for n in range(1, 12)}
    kontrol("IG reel TAMAM", d[1]["DURUM"].startswith("TAMAM") and d[1]["sonuc_no"] == "IGMEDIA77")
    kontrol("IG karusel TAMAM", d[2]["DURUM"].startswith("TAMAM"))
    kontrol("Threads metin TAMAM", d[3]["DURUM"].startswith("TAMAM") and d[3]["sonuc_no"] == "THPOST1")
    kontrol("FB reel TAMAM", d[4]["DURUM"].startswith("TAMAM") and d[4]["sonuc_no"] == "FBV1")
    kontrol("FB gorsel TAMAM", d[5]["DURUM"].startswith("TAMAM") and d[5]["sonuc_no"] == "9001_55")
    kontrol("YT short TAMAM", d[6]["DURUM"].startswith("TAMAM") and d[6]["sonuc_no"] == "YTVID1")
    yt = [c for c in otr.cagri if "upload/youtube" in c[1] and c[0] == "POST"]
    kontrol("YT gorunurluk private gitti", len(yt) == 1 and yt[0][5]["status"]["privacyStatus"] == "private")
    kontrol("FAIL onaysiz yayinlanmadi", d[7]["DURUM"] == "")
    kontrol("FAIL BEKLIYOR atlandi", d[8]["DURUM"].startswith("BEKLIYOR 2026-12-08T09:00"))
    kontrol("FAIL 7 saat gec KACTI", d[9]["DURUM"].startswith("KACTI"))
    kontrol("zamani gelmeyen bekler", d[10]["DURUM"] == "")
    kontrol("FAIL onaydan sonra degisen satir yayinlanmadi", d[11]["DURUM"] == "")
    pub = [c for c in otr.cagri if c[1].endswith("/media_publish")]
    kontrol("media_publish tam 2 kez (2 IG satiri)", len(pub) == 2)
    kontrol("sorguda token yok (yayin)", all(not any(s in json.dumps(c[2]) + c[1] for s in SIRLAR) for c in otr.cagri))
    kontrol("cikis 1 (KACTI + OZET_FARKLI uyarisi)", rc == 1)
    uy = list(DRIVE.rglob("SOSYAL_HATA_*"))
    kontrol("uyari dosyasi yazildi", uy and "KACTI" in uy[0].read_text() and "OZET_FARKLI" in uy[0].read_text())
    kontrol("sizinti yok (ana)", sizinti_yok(out, json.dumps(otr.satirlar)))
    return otr


def senaryo_kuru():
    sifirla()
    acik(hepsi=[])
    otr = Oturum([satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4"), satir(9, "threads", "metin", saat=-7)])
    rc, out = kos(otr, "yayin", "--kuru")
    yazim = [c for c in otr.cagri if c[0] != "GET" and "oauth2" not in c[1]]
    kontrol("kuru: yazim 0", not yazim and not list(DRIVE.rglob("SOSYAL_HATA_*")))
    kontrol("kuru: 'yayinlanirdi' yazdi", "KURU yayinlanirdi" in out)


def senaryo_kapali():
    sifirla()
    acik(hepsi=["YAYIN_FB"])
    otr = Oturum([satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4")])
    kos(otr, "yayin")
    kontrol("FAIL anahtar kapali: yayin yok", satir_al(otr, 1)["DURUM"] == "" and not any("/media" in c[1] for c in otr.cagri))
    os.environ["SOSYAL_YAYIN_ACIK"] = ""
    acik_bos = calis.acik_platformlar()
    kontrol("ana anahtar kapali: platform 0", acik_bos == set())


def senaryo_medya_farkli():
    sifirla()
    acik()
    genel(1, 1, ".mp4", b"BASKA")
    otr = Oturum([satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4")])
    rc, out = kos(otr, "yayin")
    kontrol("FAIL genel medya farkli: yayin yok", satir_al(otr, 1)["DURUM"] == "" and rc == 1 and "MEDYA" in out)


def senaryo_publish_500():
    sifirla()
    acik()
    otr = Oturum([satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4")])
    otr.publish_500 = True
    rc, out = kos(otr, "yayin")
    d = satir_al(otr, 1)
    pub = [c for c in otr.cagri if c[1].endswith("/media_publish")]
    kontrol("FAIL publish 500: tek deneme", len(pub) == 1)
    kontrol("FAIL publish 500: HATA + BELIRSIZ", d["DURUM"].startswith("HATA") and d["not"].startswith("BELIRSIZ") and rc == 1)
    kontrol("FAIL publish 500: hata metninde token yok", sizinti_yok(out, json.dumps(otr.satirlar)))


def senaryo_son_an():
    sifirla()
    acik()
    otr = Oturum([satir(3, "threads", "metin")])
    otr.son_an_durum = True
    kos(otr, "yayin")
    kontrol("FAIL son an DURUM dolu: yayin yok", not any(c[1].endswith("/threads") for c in otr.cagri))


def senaryo_onayla():
    sifirla()
    s = satir(2, "instagram", "karusel", "SOSYAL/a.jpg;SOSYAL/b.jpg", onay=False)
    bozuk = satir(5, "instagram", "reel", "SOSYAL/yok.mp4", onay=False)
    otr = Oturum([s, bozuk])
    mk, plan = TMP / "media", TMP / "plan.json"
    rc, out = kos(otr, "onayla", "--satirlar", "2,5", "--onay", "SERDAR_20261207", "--medya-kok", str(mk),
                  "--asama", "hazirla", "--plan", str(plan))
    kontrol("onayla hazirla: takvime ONAY yazilmadi", satir_al(otr, 2)["ONAY"] == "" and plan.exists())
    kontrol("onayla hazirla: genel medya konuldu", (mk / "yayin/202612/2_2.jpg").read_bytes() == b"JPG-B")
    kontrol("FAIL onayla: medyasi olmayan satir hazirlanmadi", rc == 1 and "5" not in json.loads(plan.read_text())["satirlar"])
    rc, out = kos(otr, "onayla", "--satirlar", "2,5", "--onay", "SERDAR_20261207", "--asama", "yaz", "--plan", str(plan))
    d = satir_al(otr, 2)
    md5 = [hashlib.md5(b"JPG-A").hexdigest(), hashlib.md5(b"JPG-B").hexdigest()]
    kontrol("onayla yaz: ONAY + ozet", d["ONAY"] == "SERDAR_20261207" and d["ONAY_OZET"] == secim.ozet(d, md5))
    kontrol("FAIL onayla yaz: hazirlanmayan satir onaylanmadi", satir_al(otr, 5)["ONAY"] == "" and rc == 1)
    otr2 = Oturum([satir(2, "instagram", "karusel", "SOSYAL/a.jpg;SOSYAL/b.jpg", onay=False, metin="sonradan degisti")])
    rc, _ = kos(otr2, "onayla", "--satirlar", "2", "--onay", "SERDAR_20261207", "--asama", "yaz", "--plan", str(plan))
    kontrol("FAIL onayla yaz: hazirliktan sonra degisen satir onaylanmadi", satir_al(otr2, 2)["ONAY"] == "" and rc == 1)
    rc2, _ = kos(otr, "onayla", "--satirlar", "2", "--onay", "serdar")
    kontrol("FAIL onayla: onay bicimi", rc2 == 2)


def senaryo_inceleme_bulgulari():
    sifirla()
    acik()
    otr = Oturum([satir(3, "threads", "metin")])
    otr.kaydir = True
    rc, out = kos(otr, "yayin")
    kontrol("FAIL satir kaymasi: yayin yok + DUR uyarisi", not any(c[1].endswith("/threads") for c in otr.cagri) and rc == 1
            and "kaydi" in "".join(p.read_text() for p in DRIVE.rglob("SOSYAL_HATA_*")))
    sifirla()
    otr = Oturum([satir(3, "threads", "metin"), satir(4, "threads", "metin")])
    otr.tamam_yaz_hata = True
    rc, out = kos(otr, "yayin")
    uy = "".join(p.read_text() for p in DRIVE.rglob("SOSYAL_HATA_*"))
    d3 = satir_al(otr, 3)
    kontrol("FAIL TAMAM yazilamadi: HATA yazilmaz, YAYINLANDI uyarisi, kosu durur",
            d3["DURUM"].startswith("BEKLIYOR") and "YAYINLANDI no=THPOST1" in uy and satir_al(otr, 4)["DURUM"] == ""
            and sum(1 for c in otr.cagri if c[1].endswith("/threads_publish")) == 1)
    sifirla()
    eski = (SIMDI - timedelta(minutes=70)).strftime("%Y-%m-%dT%H:%M%z")
    otr = Oturum([satir(3, "threads", "metin", durum=f"BEKLIYOR {eski}")])
    rc, _ = kos(otr, "yayin")
    kontrol("FAIL eski BEKLIYOR: uyari, yayin yok", rc == 1 and "BEKLIYOR 1 saatten eski" in
            "".join(p.read_text() for p in DRIVE.rglob("SOSYAL_HATA_*")) and not any(c[1].endswith("/threads") for c in otr.cagri))
    kontrol("eski BEKLIYOR: UYARILDI isareti", "UYARILDI" in satir_al(otr, 3)["not"])
    rc2, _ = kos(otr, "yayin")
    kontrol("eski BEKLIYOR: ikinci kosuda tekrar uyari yok", rc2 == 0)
    sifirla()
    cok = (SIMDI - timedelta(minutes=150)).strftime("%Y-%m-%dT%H:%M%z")
    otr = Oturum([satir(3, "threads", "metin", durum=f"BEKLIYOR {cok}")])
    rc, _ = kos(otr, "yayin")
    kontrol("FAIL 150 dk eski BEKLIYOR da uyarir (zaman asimi boslugu yok)", rc == 1)
    sifirla()
    otr = Oturum([satir(3, "threads", "metin", saat=+5, onay=False)])
    otr.satirlar[0][otr.baslik.index("yz_beyani")] = ""
    rc, _ = kos(otr, "yayin")
    kontrol("gelecek tarihli eksik taslak uyari vermez", rc == 0 and not list(DRIVE.rglob("SOSYAL_HATA_*")))
    sifirla()
    genel(12, 1, ".jpg", b"JPG-A")
    genel(13, 1, ".jpg", b"JPG-A")
    otr = Oturum([satir(12, "threads", "gorsel", "SOSYAL/a.jpg"), satir(13, "instagram", "hikaye", "SOSYAL/a.jpg")])
    rc, _ = kos(otr, "yayin")
    th = [c for c in otr.cagri if c[1].endswith("/threads") and c[0] == "POST"]
    ig = [c for c in otr.cagri if c[1].endswith("/media") and c[0] == "POST"]
    kontrol("Threads gorsel: IMAGE + image_url", rc == 0 and th and th[0][3]["media_type"] == "IMAGE" and th[0][3]["image_url"].endswith("/yayin/202612/12_1.jpg"))
    kontrol("IG hikaye: STORIES + image_url", ig and ig[0][3]["media_type"] == "STORIES" and "image_url" in ig[0][3])
    ortak.gizle("XYZTOKEN98765")
    t = ortak.temizle('{"access_token": "ABCDEF123456789", "refresh_token":"QWERTY987654321", "upload_url": "https://x/y"}')
    kontrol("temizle JSON anahtarlari", "ABCDEF123456789" not in t and "QWERTY987654321" not in t and "https://x/y" not in t)
    try:
        ortak.Http(type("O", (), {"request": lambda *a, **k: Y(418, {"weird": "LEAKVALUE123"})})()).iste("GET", "https://a.b/c")
    except ortak.Hata as e:
        kontrol("FAIL bilinmeyen hata govdesi metne girmez", "LEAKVALUE123" not in str(e))
    out = io.StringIO()
    os.environ["YT_CLIENT_ID"] = "ytcid"
    with contextlib.redirect_stdout(out):
        izin.main(["link", "youtube"])
    st = json.loads((DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_STATE_YOUTUBE.json").read_text())["state"]
    kontrol("izin link: link ve state loga yazilmaz, Drive'da", st not in out.getvalue() and "accounts.google.com" not in out.getvalue()
            and st in (DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_LINK_YOUTUBE.txt").read_text())


def senaryo_gizli_test():
    sifirla()
    os.environ["SOSYAL_YAYIN_ACIK"] = ""
    for x in calis.ANAHTAR.values():
        os.environ[x] = ""
    rows = [satir(20, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="private"),
            satir(21, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", gorunurluk="taslak"),
            satir(24, "facebook", "gorsel", "SOSYAL/a.jpg", gorunurluk="taslak"),
            satir(22, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4"),
            satir(23, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="public"),
            satir(25, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4")]
    genel(22, 1, ".mp4", b"REEL")
    otr = Oturum(rows)
    rc, out = kos(otr, "yayin", "--gizli-test", "20")
    yt = [c for c in otr.cagri if "upload/youtube" in c[1] and c[0] == "POST"]
    kontrol("gizli test YT: private yuklendi, ana anahtar kapaliyken", rc == 0 and satir_al(otr, 20)["DURUM"].startswith("TAMAM")
            and len(yt) == 1 and yt[0][5]["status"]["privacyStatus"] == "private")
    kontrol("gizli test YT: diger onayli satirlara dokunulmadi", all(satir_al(otr, n)["DURUM"] == "" for n in (21, 22, 23, 24, 25))
            and not any(c[1].endswith("/media") for c in otr.cagri))
    rc, out = kos(otr, "yayin", "--gizli-test", "21")
    fin = [c for c in otr.cagri if c[1].endswith("/video_reels") and (c[3] or {}).get("upload_phase") == "finish"]
    kontrol("gizli test FB reel: video_state=DRAFT", rc == 0 and len(fin) == 1 and fin[0][3]["video_state"] == "DRAFT")
    rc, out = kos(otr, "yayin", "--gizli-test", "24")
    ph = [c for c in otr.cagri if c[1].endswith("/photos")]
    kontrol("gizli test FB gorsel: published=false", rc == 0 and len(ph) == 1 and ph[0][3]["published"] == "false")
    for n, ad in (("23", "youtube public"), ("22", "instagram"), ("25", "facebook bos gorunurluk"), ("99", "olmayan satir")):
        once = len(otr.cagri)
        rc, out = kos(otr, "yayin", "--gizli-test", n)
        yazim = [c for c in otr.cagri[once:] if c[0] != "GET" and "oauth2" not in c[1]]
        kontrol(f"FAIL gizli test {ad}: DUR, yazim yok", rc == 2 and not yazim and "DUR" in out)
    otr2 = Oturum([satir(28, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="private", onay=False),
                   satir(29, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="private", saat=+3)])
    for n, ad in (("28", "onaysiz"), ("29", "zamani gelmemis")):
        rc, out = kos(otr2, "yayin", "--gizli-test", n)
        kontrol(f"FAIL gizli test {ad}: cikis 1 + 'yayinlanmadi'", rc == 1 and "yayinlanmadi" in out
                and not any("upload/youtube" in c[1] for c in otr2.cagri))
    sifirla()
    acik()
    otr = Oturum([satir(26, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4")])
    kos(otr, "yayin")
    fin = [c for c in otr.cagri if c[1].endswith("/video_reels") and (c[3] or {}).get("upload_phase") == "finish"]
    kontrol("FB normal satir: PUBLISHED (gizli kip yalniz taslakta)", fin and fin[0][3]["video_state"] == "PUBLISHED")
    otr = Oturum([satir(27, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", gorunurluk="gizli")])
    rc, _ = kos(otr, "yayin")
    kontrol("FAIL FB gecersiz gorunurluk: GECERSIZ, yayin yok", rc == 1 and not any(c[1].endswith("/video_reels") for c in otr.cagri))


def senaryo_video_kaynak():
    import video_kaynak as V
    sifirla()
    eski = VAYAR.read_text()
    tam = json.loads(eski)
    kontrol("video kaynagi: dogru yol gecer", V.medya_hatasi("SOSYAL/cancer-and-libra-pin-video.mp4") == "")
    kontrol("video kaynagi: yol yardimcisi", V.yol("CANCER_LIBRA") == "SOSYAL/cancer-and-libra-pin-video.mp4")
    kontrol("video kaynagi: ayni burc cifti gecer", V.medya_hatasi("SOSYAL/leo-and-leo-pin-video.mp4") == "")
    kontrol("video kaynagi: JPEG kontrol disi", V.medya_hatasi("BASKA/a.jpg") == "")
    for yol, ad in (("ASTROLOVE/TEMP/SOSYAL_VIDEO_P_78_20261020/cancer-and-libra-astroloveart-reel.mp4", "eski mockup videosu"),
                    ("BASKA/cancer-and-libra-pin-video.mp4", "yanlis klasor"), ("SOSYAL/libra-and-cancer-pin-video.mp4", "alfabetik degil"),
                    ("SOSYAL/cancer-and-dragon-pin-video.mp4", "gecersiz burc"), ("SOSYAL/sub/cancer-and-libra-pin-video.mp4", "alt klasor"),
                    ("X/old-reel.mp4/", "sonda /"), ("SOSYAL/CANCER-and-libra-pin-video.MP4", "buyuk harf"), ("X/eski.mp4 ", "sonda bosluk")):
        kontrol(f"FAIL video kaynagi: {ad}", V.medya_hatasi(yol) != "")
    for bozuk, ad in (({**tam, "onay": ""}, "onay bos"), ({**tam, "klasor": ""}, "klasor bos"), ({**tam, "onay": "serdar"}, "onay bicimi"),
                      ({**tam, "ad_kalibi": ""}, "kalip bos"), ([1], "JSON nesne degil"), ("{bozuk", "JSON bozuk")):
        VAYAR.write_text(bozuk if isinstance(bozuk, str) else json.dumps(bozuk))
        kontrol(f"FAIL video kaynagi ayari {ad}: hicbir mp4 gecmez", V.medya_hatasi("SOSYAL/cancer-and-libra-pin-video.mp4") != "")
    VAYAR.write_text(json.dumps({**tam, "onay": ""}))
    acik()
    otr = Oturum([satir(30, "youtube", "short", "SOSYAL/aries-and-leo-pin-video.mp4", gorunurluk="private")])
    rc, _ = kos(otr, "yayin")
    kontrol("FAIL ayar onaysizken onayli video satiri yayinlanmaz (GECERSIZ)", rc == 1 and satir_al(otr, 30)["DURUM"] == ""
            and not any("upload/youtube" in c[1] for c in otr.cagri))
    otr = Oturum([satir(31, "facebook", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", onay=False)])
    rc, _ = kos(otr, "onayla", "--satirlar", "31", "--onay", "SERDAR_20261207", "--asama", "hazirla", "--plan", str(TMP / "p31.json"))
    kontrol("FAIL ayar onaysizken onayla video satirini hazirlamaz", rc == 1 and "31" not in json.loads((TMP / "p31.json").read_text())["satirlar"])
    VAYAR.write_text(eski)
    gercek = json.loads((KOK.parents[2] / "config/sosyal_video_kaynak.json").read_text())
    kontrol("depodaki ayar: klasor ve onay BOS (video B onayina kadar yayin yok)", gercek.get("klasor") == "" and gercek.get("onay") == ""
            and gercek.get("ad_kalibi") == "{a}-and-{b}-pin-video.mp4")


def senaryo_plan78():
    import plan78
    yol = KOK.parents[2] / "data/sosyal/pinterest/pin78/ORNEK_METIN_CANCER_LEO.csv"
    out = TMP / "plan.csv"
    with contextlib.redirect_stdout(io.StringIO()) as o:
        rc = plan78.main(["--metin", str(yol), "--baslangic", "2026-12-13", "--cikti", str(out)])
    r = list(csv.DictReader(open(out)))
    leo = [x for x in r if "CANCER_LEO" in x["not"]]
    kontrol("plan78: 702 satir, kapi PASS", rc == 0 and len(r) == 702 and "KAPI PASS" in o.getvalue())
    kontrol("plan78: cift basina 9 (IG 4, FB 4, YT 1)", Counter(x["platform"] for x in leo) == Counter(instagram=4, facebook=4, youtube=1))
    kontrol("plan78: YT yalniz short, IG/FB 3 gorsel + 1 reel", {x["tur"] for x in r if x["platform"] == "youtube"} == {"short"}
            and Counter(x["tur"] for x in leo if x["platform"] == "instagram") == Counter(gorsel=3, reel=1))
    kontrol("plan78: ilk gun video da var (tur karisimi)", any(x["tur"] in ("reel", "short") for x in r if x["tarih_saat_TR"].startswith("2026-12-13")))
    kontrol("plan78: ONAY/DURUM bos, metin genel surum + Etsy linki", all(x["ONAY"] == "" and x["DURUM"] == "" for x in r)
            and all(x["metin"].endswith("https://astroloveart.etsy.com/listing/4570143387") for x in leo) and not any("Valentine" in x["metin"] for x in r))
    bozuk = TMP / "bozuk.csv"
    rows = list(csv.DictReader(open(yol)))
    for x in rows:
        if x["surum"] == "genel" and x["konsept"] == "kart":
            x["aciklama"] += " A perfect Valentine gift — 2027."
    with open(bozuk, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    with contextlib.redirect_stdout(io.StringIO()) as o:
        rc = plan78.main(["--metin", str(bozuk), "--baslangic", "2026-12-13", "--cikti", str(TMP / "p2.csv")])
    kontrol("FAIL plan78: sezonluk/uzun tire/yil ifadesi kapida", rc == 1 and "yasak/sezonluk" in o.getvalue())
    with contextlib.redirect_stdout(io.StringIO()) as o:
        rc = plan78.main(["--metin", str(yol), "--baslangic", "2026-12-13", "--cikti", str(TMP / "p3.csv"), "--yt", "9"])
    kontrol("FAIL plan78: desteklenmeyen gunluk sayi DUR", rc == 2)


def senaryo_yml():
    import yaml
    w = KOK.parents[2] / ".github/workflows"
    d = yaml.safe_load((w / "sosyal-yayin.yml").read_text())
    j, o = d["jobs"]["yayin"], d["jobs"]["onayla"]
    kontrol("yml: zamanli kosu anahtara bagli", "vars.SOSYAL_YAYIN_ACIK == 'true'" in j["if"] and "schedule" in j["if"])
    kontrol("yml: yayin isi onayla calistirmaz", "inputs.mod != 'onayla'" in j["if"] and "onayla" not in j["steps"][-1]["run"])
    kontrol("yml: onayla isi environment kapili, zamanli kosuda yok", o.get("environment") == "sosyal-onay"
            and "schedule" not in o["if"] and o["steps"][0]["name"] == "Onay kapisi var mi" and "SOSYAL_ONAY_KAPISI" in str(o["steps"][0]))
    kontrol("yml: ayri kilit gruplari", j["concurrency"]["group"] != o["concurrency"]["group"] and "concurrency" not in d)
    kontrol("yml: elle kuru varsayilan acik", d[True]["workflow_dispatch"]["inputs"]["kuru"]["default"] is True)
    kontrol("yml: gizli test girdisi bos varsayilan, yalniz dispatch", d[True]["workflow_dispatch"]["inputs"]["gizli_test_satir"]["default"] == ""
            and "workflow_dispatch" in str(j["steps"][-1]["env"]["GIZLI"]))
    adim = [x.get("name") for x in o["steps"]]
    kontrol("yml: ONAY yazimi medya push'undan sonra", adim.index("ONAY yaz (yalniz onayla, medya push'undan sonra)") > adim.index("Medya push (yalniz onayla)"))
    for f in ("sosyal-izin.yml", "sosyal-token-yenile.yml", "sosyal-olcum-kendi.yml", "sosyal-yayin.yml"):
        y = yaml.safe_load((w / f).read_text())
        girdiler = (y[True].get("workflow_dispatch") or {}).get("inputs") or {}
        kontrol(f"yml {f}: sir girdi degil", not any(k.upper().startswith(("OAUTH", "TOKEN", "SECRET", "KOD")) for k in girdiler))


def senaryo_http_kurali():
    h = ortak.Http(Oturum([]))
    try:
        h.iste("GET", "https://graph.instagram.com/v21.0/me", params={"access_token": "x" * 10})
        kontrol("FAIL sir sorguda reddedilir", False)
    except ortak.Hata:
        kontrol("FAIL sir sorguda reddedilir", True)
    ortak.gizle("SIRSIR123456")
    t = ortak.temizle("x https://a.b/c?access_token=SIRSIR123456&y=1 Bearer abcdefghijkl SIRSIR123456 code=ZZZ")
    kontrol("temizle: adres sorgusu, Bearer, sir, code", "SIRSIR123456" not in t and "abcdefghijkl" not in t and "ZZZ" not in t)


def senaryo_izin():
    sifirla()
    os.environ["OAUTH_KOD_IG"] = "KODSAHTE123456#_"
    otr = Oturum([])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = izin.main(["cevir", "instagram"], http=ortak.Http(otr))
    k = json.loads((DRIVE / "ASTROLOVE/TEMP/SOSYAL_INSTAGRAM_TOKEN.json").read_text())
    kontrol("izin cevir IG: token + hesap Drive'da", rc == 0 and k["token"] == TOK["instagram"] and k["ig_id"] == "1784")
    kontrol("izin cevir IG: kod sirri silindi", any(c[0] == "DELETE" and c[1].endswith("/OAUTH_KOD_IG") for c in otr.cagri))
    kontrol("izin cevir IG: logda kod/token yok", sizinti_yok(out.getvalue()))
    os.environ.pop("OAUTH_KOD_IG")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = izin.main(["link", "youtube"])
    lk = (DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_LINK_YOUTUBE.txt")
    kontrol("izin link YT: link + state Drive'da, sir yok", rc == 0 and lk.exists() and lk.read_text().startswith("https://accounts.google.com")
            and "redirect_uri=https%3A%2F%2Fcaliserdar-maker.github.io%2Fastrolove-media%2Fapp%2Foauth.html" in lk.read_text()
            and "YTSECRET" not in lk.read_text() + out.getvalue())
    with contextlib.redirect_stdout(io.StringIO()):
        rc = izin.main(["cevir", "instagram"], http=ortak.Http(Oturum([])))
    kontrol("FAIL izin cevir: kod sirri yok", rc == 1)


def senaryo_fb_cevir():
    os.environ.update(META_APP_ID="1609743017476204", META_APP_SECRET="METASECRET0123456")

    def kos_fb(hesaplar, hedef, sayfa_token=True, page_id="", gecerli=True, liste_hedef=None):
        sifirla()
        (DRIVE / "ASTROLOVE/TEMP/SOSYAL_FACEBOOK_TOKEN.json").unlink()
        os.environ["OAUTH_KOD_FB"] = "KODSAHTE123456"
        os.environ["FB_PAGE_ID"] = page_id
        otr = Oturum([])
        otr.fb = {"hesaplar": hesaplar, "hedef": hedef, "sayfa_token": sayfa_token, "gecerli": gecerli, "liste_hedef": liste_hedef}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = izin.main(["cevir", "facebook"], http=ortak.Http(otr))
        f = DRIVE / "ASTROLOVE/TEMP/SOSYAL_FACEBOOK_TOKEN.json"
        k = json.loads(f.read_text()) if f.exists() else {}
        os.environ.pop("OAUTH_KOD_FB", None)
        os.environ["FB_PAGE_ID"] = ""
        return rc, k, out.getvalue(), otr

    rc, k, out, _ = kos_fb([{"id": "9001", "name": "AstroLoveArt", "access_token": TOK["facebook"]}], [])
    kontrol("FB cevir: /me/accounts dolu -> Sayfa token", rc == 0 and k.get("page_id") == "9001" and k.get("token") == TOK["facebook"])
    rc, k, out, otr = kos_fb([], ["9001"])
    kontrol("FB cevir: /me/accounts BOS -> debug_token secilen Sayfa -> Sayfa token (23 Kas FAIL senaryosu)",
            rc == 0 and k.get("page_id") == "9001" and k.get("token") == TOK["facebook"] and any(c[1].endswith("/debug_token") for c in otr.cagri))
    kontrol("FB cevir: logda sir yok", sizinti_yok(out))
    kontrol("FB cevir: veri erisim bitisi kaydedildi", k.get("veri_erisim_bitis") == "1790000000")
    rc, k, out, _ = kos_fb([], [], page_id="9001")
    kontrol("FB cevir: izin tum Sayfalara (target yok) + FB_PAGE_ID -> Sayfa token", rc == 0 and k.get("page_id") == "9001")
    rc, k, out, _ = kos_fb([], ["9001", "9002"], page_id="9002")
    kontrol("FB cevir: birden cok izinli Sayfa icinden FB_PAGE_ID", rc == 0 and k.get("page_id") == "9002")
    ciktilar = []
    for ad, arg in (("Sayfa token vermezse DUR (business_management onerisi)", dict(hesaplar=[], hedef=["9001"], sayfa_token=False)),
                    ("izin verilmeyen FB_PAGE_ID reddedilir", dict(hesaplar=[], hedef=["9001"], page_id="7777")),
                    ("birden cok izinli Sayfa + FB_PAGE_ID yok -> DUR", dict(hesaplar=[], hedef=["9001", "9002"])),
                    ("debug_token is_valid=false -> DUR", dict(hesaplar=[], hedef=["9001"], gecerli=False)),
                    ("yalniz pages_show_list hedefi olan Sayfa secilmez", dict(hesaplar=[], hedef=["9001"], liste_hedef=["7777"], page_id="7777")),
                    ("pages_manage_posts izni yok -> DUR", dict(hesaplar=[], hedef=None, liste_hedef=["9001"]))):
        rc, k, out, _ = kos_fb(**arg)
        ciktilar.append(out)
        kontrol(f"FAIL FB cevir: {ad}, Drive'a yazim yok", rc == 1 and not k and (not ad.startswith("Sayfa token") or "business_management" in out))
    kontrol("FB cevir: DUR ciktilarinda sir yok", sizinti_yok(*ciktilar))
    sifirla()
    os.environ["FB_CONFIG_ID"] = "CFG123"
    with contextlib.redirect_stdout(io.StringIO()):
        izin.main(["link", "facebook"])
    lk1 = (DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_LINK_FACEBOOK.txt").read_text()
    os.environ["FB_CONFIG_ID"] = ""
    with contextlib.redirect_stdout(io.StringIO()):
        izin.main(["link", "facebook"])
    lk2 = (DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_LINK_FACEBOOK.txt").read_text()
    kontrol("FB link: FB_CONFIG_ID varsa config_id, scope yok", "config_id=CFG123" in lk1 and "scope=" not in lk1)
    kontrol("FB link: config yoksa scope, business_management YOK (varsayilan)", "scope=" in lk2 and "business_management" not in lk2 and "config_id" not in lk2)
    os.environ["FB_ISLETME_IZNI"] = "true"
    with contextlib.redirect_stdout(io.StringIO()):
        izin.main(["link", "facebook"])
    os.environ["FB_ISLETME_IZNI"] = ""
    kontrol("FB link: FB_ISLETME_IZNI=true ise business_management", "business_management" in (DRIVE / "ASTROLOVE/TEMP/SOSYAL_IZIN_LINK_FACEBOOK.txt").read_text())
    for gun, beklenen in ((5, 1), (40, 0)):
        sifirla()
        bit = int((datetime.now(secim.TZ) + timedelta(days=gun)).timestamp())
        drive_koy("ASTROLOVE/TEMP/SOSYAL_FACEBOOK_TOKEN.json", json.dumps({"token": TOK["facebook"], "page_id": "9001", "veri_erisim_bitis": str(bit)}).encode())
        otr = Oturum([])
        with contextlib.redirect_stdout(io.StringIO()):
            rc = token_yenile.main(["facebook"], http=ortak.Http(otr))
        kontrol(f"{'FAIL ' if beklenen else ''}yenile FB: veri erisimi {gun} gun kala -> cikis {beklenen}", rc == beklenen)


def senaryo_yenile():
    sifirla()
    otr = Oturum([])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = token_yenile.main(["instagram"], http=ortak.Http(otr))
    k = json.loads((DRIVE / "ASTROLOVE/TEMP/SOSYAL_INSTAGRAM_TOKEN.json").read_text())
    kontrol("yenile IG: yeni token Drive'a geri yazildi", rc == 0 and k["token"] == "IGYENI_SAHTE_0123456789" and k.get("bitis"))
    sifirla()
    otr = Oturum([])
    otr.yenile_hata = True
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = token_yenile.main(["instagram"], http=ortak.Http(otr))
    uy = list(DRIVE.rglob("SOSYAL_HATA_*"))
    kontrol("FAIL yenile hata: uyari + cikis 1", rc == 1 and uy)
    kontrol("FAIL yenile hata: token sizmadi", sizinti_yok(out.getvalue()))


def senaryo_istatistik_kontrol():
    import istatistik
    sifirla()
    r = satir(1, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", durum="TAMAM 2026-12-08T09:00")
    r["sonuc_no"] = "IGMEDIA77"
    otr = Oturum([r, satir(2, "threads", "metin")])
    with contextlib.redirect_stdout(io.StringIO()):
        rc = istatistik.main(http=ortak.Http(otr), simdi=SIMDI)
    csvs = list(DRIVE.rglob("SOSYAL_OLCUM_*.csv"))
    metin = csvs[0].read_text() if csvs else ""
    kontrol("istatistik: TAMAM satiri CSV'de (views 321, likes 7)", rc == 0 and "IGMEDIA77,views,321" in metin and ",likes,7" in metin)
    kontrol("istatistik: yazim yok (yalniz GET)", all(c[0] == "GET" or "oauth2" in c[1] for c in otr.cagri))
    acik(hepsi=["YAYIN_IG"])
    with contextlib.redirect_stdout(io.StringIO()):
        rc = calis.main(["kontrol"], http=ortak.Http(Oturum([])))
    kontrol("kontrol IG: kimlik PASS", rc == 0)
    drive_koy("ASTROLOVE/TEMP/SOSYAL_INSTAGRAM_TOKEN.json", json.dumps({"token": TOK["instagram"], "ig_id": "999"}).encode())
    with contextlib.redirect_stdout(io.StringIO()):
        rc = calis.main(["kontrol"], http=ortak.Http(Oturum([])))
    kontrol("FAIL kontrol: token baska hesaba ait", rc == 1)


def mutasyon():
    """Onay kapisi bozulunca (ONAY_RX her seyi kabul) 'onaysiz yayinlanmadi' kontrolu FAIL vermeli."""
    import re
    eski = secim.ONAY_RX
    secim.ONAY_RX = re.compile(r".*")
    sifirla()
    acik()
    otr = Oturum([satir(7, "instagram", "reel", "SOSYAL/cancer-and-libra-pin-video.mp4", onay=False)])
    genel(7, 1, ".mp4", b"REEL")
    otr.satirlar[0][otr.baslik.index("ONAY_OZET")] = secim.ozet(satir_al(otr, 7), [hashlib.md5(b"REEL").hexdigest()])
    kos(otr, "yayin")
    secim.ONAY_RX = eski
    yakalandi = satir_al(otr, 7)["DURUM"] != ""
    kontrol("mutasyon: bozuk onay kapisi test tarafindan yakalanir", yakalandi)


if __name__ == "__main__":
    try:
        for f in (senaryo_ana, senaryo_kuru, senaryo_kapali, senaryo_medya_farkli, senaryo_publish_500, senaryo_son_an,
                  senaryo_onayla, senaryo_inceleme_bulgulari, senaryo_gizli_test, senaryo_video_kaynak, senaryo_plan78, senaryo_yml, senaryo_http_kurali, senaryo_izin, senaryo_fb_cevir, senaryo_yenile, senaryo_istatistik_kontrol, mutasyon):
            try:
                f()
            except Exception as e:
                kontrol(f"{f.__name__} istisna {type(e).__name__}: {e}", False)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    bad = [a for a, ok in SONUC if not ok]
    print(f"\n{len(SONUC) - len(bad)}/{len(SONUC)} PASS")
    sys.exit(1 if bad else 0)
