#!/usr/bin/env python3
"""drive_temizlik sahte Drive testi. AG KAPALI: socket bastan engellenir; urllib.request.urlopen bellek ici sahte Drive'a
yonlenir (gercek kod yolu, istemci kapilari dahil calisir). git grep yerel gecici depoda kosar (ag yok).
Bilinen PASS: temiz klasor tek birim; son 14 gunde degisen / envanterde olmayan alt oge klasoru boler; kodda gecen ad,
yol farki, envanterden sonra degisen, koruma deseni, kisisel ".", siparis deseni, POD_PRINT atlanir; J2 yalniz SIPARIS/TEMP
altindaki test klasoru; J4 tek eski kok Apps Script; J5 ARCHIVE/<eski yol> altina tasinir, ara klasor kurulur;
uygula: Cop'e tasir + geri okur, kuru sonrasi degisen birim atlanir.
Bilinen FAIL: DELETE / emptyTrash / farkli PATCH govdesi reddedilir; onay yoksa DUR; envanter basligi farkliysa DUR;
kalici 500 hatasinda parti DUR + cikis 1."""
import contextlib
import csv
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_temizlik as M  # noqa: E402

M.time.sleep = lambda *_: None
KL, SC = M.KLASOR, M.SCRIPT
SIMDI = datetime.now(timezone.utc)
ESKI = (SIMDI - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
YAKIN = (SIMDI - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
HATALI = set()  # bu id'lere PATCH kalici 500


class Sahte:
    def __init__(self):
        self.f = {}
        self.n = 0
        self.yaz = []  # (yontem, yol)

    def ekle(self, fid, ad, ust, mime="text/plain", size=100, mod=ESKI, view=None):
        self.f[fid] = dict(id=fid, name=ad, mimeType=mime, parents=[ust] if ust else [], size=str(size), modifiedTime=mod,
                           viewedByMeTime=view, trashed=False, capabilities=dict(canTrash=True, canMoveItemWithinDrive=True))
        return fid

    def cevap(self, req):
        u = urllib.parse.urlparse(req.full_url)
        q = dict(urllib.parse.parse_qsl(u.query))
        yol = u.path.replace("/drive/v3", "")
        m = req.get_method()
        if not req.headers.get("Authorization", "").startswith("Bearer SAHTE"):
            raise AssertionError("token yok")
        if m == "GET" and yol == "/files":
            return {"files": [dict(o) for o in self.f.values() if self.esles(q["q"], o)]}
        if m == "GET" and yol.startswith("/files/"):
            fid = yol.split("/")[2]
            if fid == "root":
                return {"id": "ROOT", "name": "Drive", "parents": []}
            if fid not in self.f:
                raise urllib.error.HTTPError(req.full_url, 404, "yok", {}, io.BytesIO(b""))
            return dict(self.f[fid])
        if m == "PATCH":
            fid = yol.split("/")[2]
            self.yaz.append((m, fid))
            if fid in HATALI:
                raise urllib.error.HTTPError(req.full_url, 500, "x", {}, io.BytesIO(b""))
            if "addParents" in q:
                o = self.f[fid]
                assert o["parents"] == [q["removeParents"]]
                o["parents"] = [q["addParents"]]
                return {"id": fid, "parents": o["parents"]}
            g = json.loads(req.data)
            assert g == {"trashed": True}
            self.f[fid]["trashed"] = True
            return {"id": fid, "trashed": True}
        if m == "POST" and yol == "/files":
            g = json.loads(req.data)
            self.n += 1
            fid = f"YENI{self.n}"
            self.ekle(fid, g["name"], g["parents"][0], KL, 0, mod=SIMDI.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            self.yaz.append((m, fid))
            return {"id": fid}
        raise AssertionError(f"beklenmeyen istek {m} {yol}")

    def esles(self, q, o):
        if "trashed = false" in q and o["trashed"]:
            return False
        r = re.search(r"'([^']+)' in parents", q)
        if r:
            p = "ROOT" if r.group(1) == "root" else r.group(1)
            if p == "ROOT":
                if o["parents"] != ["ROOT"]:
                    return False
            elif p not in o["parents"]:
                return False
        r = re.search(r"name contains '([^']+)'", q)
        if r and r.group(1) not in o["name"]:
            return False
        r = re.search(r"name = '((?:[^'\\]|\\.)+)'", q)
        if r and o["name"] != r.group(1).replace("\\'", "'"):
            return False
        r = re.search(r"mimeType = '([^']+)'", q)
        if r and o["mimeType"] != r.group(1):
            return False
        r = re.search(r"modifiedTime > '([^']+)'", q)
        if r:
            t = r.group(1) + "Z"
            if not ((o["modifiedTime"] or "") > t or (o["viewedByMeTime"] or "") > t):
                return False
        return True


S = Sahte()


class _Yanit:
    def __init__(self, v):
        self.b = json.dumps(v).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


urllib.request.urlopen = lambda req, timeout=None: _Yanit(S.cevap(req))
HATA = []


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def kur(tmp):
    e = S.ekle
    e("AST", "ASTROLOVE", "ROOT", KL, 0)
    e("TEMP", "TEMP", "AST", KL, 0)
    e("ARC", "ARCHIVE", "AST", KL, 0)
    e("OFIS", "OFIS", "ROOT", KL, 0)
    e("SIP", "SIPARIS", "ROOT", KL, 0)
    e("NOK", ".", "ROOT", KL, 0)
    # J1: temiz klasor
    e("T1", "VIDEO_V9_X", "TEMP", KL, 0); e("T1a", "a.mp4", "T1", size=1000); e("T1b", "b.mp4", "T1", size=2000)
    # J1: icinde yakin tarihli dosya olan klasor -> bolunur
    e("T2", "GALERI_BAKIR", "TEMP", KL, 0); e("T2s", "ALT_TEMIZ", "T2", KL, 0); e("T2s1", "x.jpg", "T2s", size=10)
    e("T2y", "yeni.jpg", "T2", size=10, mod=YAKIN); e("T2e", "eski.jpg", "T2", size=10)
    # J1: envanterde olmayan dosya iceren klasor
    e("T3", "WA_HERO_ZOOM", "TEMP", KL, 0); e("T3a", "eski_resim.png", "T3"); e("T3n", "envantersiz.png", "T3")
    # J1: kodda gecen ad
    e("T4", "KODDA_GECEN_KLASOR", "TEMP", KL, 0); e("T4a", "a.txt", "T4")
    # J1: yolu degismis (envanterde baska yol)
    e("T5", "TASINMIS_KLASOR", "AST", KL, 0)
    # J1: envanterden sonra degismis (14 gunden eski ama envanterdekinden farkli)
    e("T6", "DEGISMIS.json", "TEMP", mod=(SIMDI - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    # J1: koruma deseni
    e("T7", "ETSY_TOKEN_eski.json", "TEMP")
    # J1: son 14 gunde acilmis
    e("T8", "ACILMIS_DOSYA.png", "TEMP", view=YAKIN)
    # J3: SQ TEMP (POD_GALLERY temiz, POD_PRINT kalir, SIPARIS_ISIM atlanir), kisisel nokta
    e("Q1", "POD_GALLERY", "TEMP", KL, 0); e("Q1a", "g.png", "Q1", size=500)
    e("Q2", "POD_PRINT", "TEMP", KL, 0); e("Q2a", "p.tif", "Q2", size=900)
    e("Q3", "SIPARIS_ISIM", "TEMP", KL, 0); e("Q3a", "f.pdf", "Q3")
    e("Q4", "aile.jpg", "NOK")
    # J2: test klasorleri
    e("S1", "9000000001", "SIP", KL, 0); e("S1a", "KAPI_RAPORU_DB.json", "S1"); e("S1b", "AstroLoveArt_X.pdf", "S1")
    e("S2", "3123456789", "SIP", KL, 0); e("S2a", "gercek.pdf", "S2")
    e("S3", "9000000002", "OFIS", KL, 0)
    e("S5", "9000000003", "Q3", KL, 0); e("S5a", "t.pdf", "S5")
    # J4: kok Apps Script
    e("A1", "Adsız proje", "ROOT", SC, 0)
    # J5: arsiv
    e("R1", "BASKI_DUZELT_1", "TEMP", KL, 0); e("R1a", "b.tif", "R1", size=300)
    e("R2", "POD_PRINT_YEDEK_1", "TEMP", KL, 0); e("R2a", "c.tif", "R2", size=400)
    # envanter
    kat = {"T1": "TRASH", "T1a": "TRASH", "T1b": "TRASH", "T2": "TRASH", "T2s": "TRASH", "T2s1": "TRASH", "T2y": "TRASH",
           "T2e": "TRASH", "T3": "TRASH", "T3a": "TRASH", "T4": "TRASH", "T4a": "TRASH", "T5": "TRASH", "T6": "TRASH",
           "T7": "TRASH", "T8": "TRASH", "Q1": "SERDAR_QUESTION", "Q1a": "SERDAR_QUESTION", "Q2": "SERDAR_QUESTION",
           "Q2a": "SERDAR_QUESTION", "Q3": "SERDAR_QUESTION", "Q3a": "SERDAR_QUESTION", "Q4": "SERDAR_QUESTION",
           "NOK": "SERDAR_QUESTION", "R1": "ARCHIVE", "R1a": "ARCHIVE", "R2": "ARCHIVE", "R2a": "ARCHIVE",
           "S1": "PROTECTED", "S1a": "PROTECTED", "S1b": "PROTECTED", "S2": "PROTECTED", "S2a": "PROTECTED",
           "AST": "KEEP", "TEMP": "KEEP", "SIP": "PROTECTED", "OFIS": "PROTECTED"}
    yollar = M.Yollar.__new__(M.Yollar)

    def yol(fid):
        o = S.f[fid]
        p = o["parents"][0]
        return "" if p == "ROOT" else (yol(p) + "/" + S.f[p]["name"]).lstrip("/")
    envd = os.path.join(tmp, "env"); os.makedirs(envd)
    with open(os.path.join(envd, "ENVANTER_PARCA_01A.csv"), "w", encoding="utf-8-sig", newline="") as h:
        w = csv.writer(h)
        w.writerow(["id", "title", "path", "mimeType", "size", "created", "modified", "category", "reason", "group",
                    "isFolder", "fileCount"])
        for fid, k in kat.items():
            o = S.f[fid]
            p = yol(fid)
            mod = o["modifiedTime"]
            if fid == "T5":
                p = "ASTROLOVE/TEMP"
            if fid == "T6":
                mod = ESKI
            w.writerow([fid, o["name"], p, o["mimeType"], o["size"], ESKI, mod, k, "r", "g", int(o["mimeType"] == KL), ""])
    depo = os.path.join(tmp, "depo"); os.makedirs(depo)
    Path(depo, "a.yml").write_text("girdi: gdrive:ASTROLOVE/TEMP/KODDA_GECEN_KLASOR/x\n")
    for c in (["init", "-q"], ["add", "."], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "t"]):
        subprocess.run(["git", "-C", depo] + c, check=True, capture_output=True)
    return envd, depo


def kos(argv):
    sys.argv = ["drive_temizlik.py"] + argv
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            rc = M.main()
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue()


def main():
    os.environ["DRIVE_TOKEN_KOMUT"] = "echo SAHTE_TOKEN"
    with tempfile.TemporaryDirectory() as tmp:
        envd, depo = kur(tmp)
        out = os.path.join(tmp, "out")
        rc, log = kos(["--mod", "kuru", "--envanter", envd, "--depo", depo, "--cikti", out, "--ts", "20261125_1200"])
        kontrol("kuru cikis 0", rc == 0)
        kontrol("kuru Drive'a yazmadi", S.yaz == [])
        kontrol("log'da ad/kimlik yok", not re.search(r"VIDEO_V9|GALERI|T1a|aile|9000000001", log))
        plan = json.load(open(os.path.join(out, "plan.json")))
        b = {x["id"]: x for x in plan["birim"]}
        at = {x["id"]: x["neden"] for x in plan["atla"]}
        kontrol("J1 temiz klasor tek birim", "T1" in b and b["T1"]["dosya"] == 2 and b["T1"]["bayt"] == 3000 and "T1a" not in b)
        kontrol("J1 yakin dosya klasoru boler", "T2" not in b and "T2s" in b and "T2e" in b and at.get("T2y") == "son14_degisti")
        kontrol("J1 envantersiz oge klasoru boler", "T3" not in b and "T3a" in b and at.get("T3n") == "envanterde_yok")
        kontrol("J1 kodda gecen ad atlanir", "T4" not in b and at.get("T4") == "kodda_geciyor")
        kontrol("J1 yolu degisen atlanir", "T5" not in b and at.get("T5") == "yol_farkli")
        kontrol("J1 envanterden sonra degisen atlanir", at.get("T6") == "envanterden_sonra_degisti")
        kontrol("J1 koruma deseni (token)", at.get("T7", "").startswith("koruma:"))
        kontrol("J1 son 14 gunde acilan atlanir", at.get("T8") == "son14_acildi")
        kontrol("J3 POD_GALLERY birim", "Q1" in b and b["Q1"]["is_"] == "J3")
        kontrol("J3 POD_PRINT secilmez", "Q2" not in b and "Q2a" not in b and "Q2" not in at)
        kontrol("J3 siparis deseni atlanir", "Q3" not in b and at.get("Q3") == "siparis_deseni")
        kontrol("kisisel nokta hicbir birimde yok", not any(x["yol"].startswith(".") for x in plan["birim"]))
        kontrol("J2 SIPARIS test klasoru tam birim", "S1" in b and b["S1"]["is_"] == "J2" and b["S1"]["dosya"] == 2)
        kontrol("J2 gercek receipt secilmez", "S2" not in b and "S2a" not in b)
        kontrol("J2 OFIS altindaki test secilmez", "S3" not in b)
        kontrol("J2 TEMP siparis altindaki test secilir", "S5" in b and b["S5"]["is_"] == "J2")
        kontrol("J4 kok script birim", "A1" in b and b["A1"]["is_"] == "J4")
        kontrol("J5 arsiv hedefi", b.get("R1", {}).get("hedef") == "ASTROLOVE/ARCHIVE/TEMP")
        kontrol("J5 POD_PRINT_YEDEK izinli", "R2" in b)
        kontrol("md ve csv yazildi", os.path.exists(os.path.join(out, "KURU_DRIVE_TRASH_20261125_1200.md"))
                and os.path.exists(os.path.join(out, "KURU_DRIVE_TRASH_20261125_1200.csv")))
        # uygula: onaysiz DUR
        rc, _ = kos(["--mod", "uygula", "--plan", os.path.join(out, "plan.json"), "--cikti", out])
        kontrol("onaysiz uygula DUR", rc not in (0, None) and S.yaz == [])
        # kuru sonrasi degisen: Q1a degisti -> Q1 atlanir
        S.f["Q1a"]["modifiedTime"] = (SIMDI + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # birimin kendi modifiedTime'i farkli (daha eski deger: sorgu yakalamaz, yalniz birim karsilastirmasi)
        S.f["T2e"]["modifiedTime"] = (SIMDI - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        rc, log = kos(["--mod", "uygula", "--plan", os.path.join(out, "plan.json"), "--cikti", out, "--onay", "TASI"])
        u = {r["id"]: r for r in json.load(open(os.path.join(out, "uygula.json")))["sonuc"]}
        kontrol("uygula cikis 0", rc == 0)
        kontrol("J1 Cop'e tasindi + geri okuma", u["T1"]["durum"] == "COPE_TASINDI" and S.f["T1"]["trashed"])
        kontrol("kuru sonrasi degisen birim atlandi", u["Q1"]["durum"] == "ATLANDI" and not S.f["Q1"]["trashed"])
        kontrol("birim modifiedTime farkli -> atlandi", u["T2e"]["durum"] == "ATLANDI" and not S.f["T2e"]["trashed"])
        kontrol("J5 ARCHIVE/TEMP altina tasindi", u["R1"]["durum"] == "ARSIVE_TASINDI"
                and S.f[S.f["R1"]["parents"][0]]["name"] == "TEMP" and S.f[S.f["R1"]["parents"][0]]["parents"] == ["ARC"])
        kontrol("J5 tek ara klasor kuruldu", sum(1 for m, _ in S.yaz if m == "POST") == 1)
        kontrol("J5 cop'e gitmedi", not S.f["R1"]["trashed"] and not S.f["R2"]["trashed"])
        kontrol("atlananlara dokunulmadi", not S.f["T2y"]["trashed"] and not S.f["T4"]["trashed"] and not S.f["Q2"]["trashed"]
                and not S.f["S2"]["trashed"])
        # ikinci uygula: zaten copte -> atlanir, yeni yazim yok
        n = len(S.yaz)
        rc, _ = kos(["--mod", "uygula", "--plan", os.path.join(out, "plan.json"), "--cikti", out, "--onay", "TASI",
                     "--isler", "J1"])
        kontrol("tekrar uygula yazim yapmaz", len(S.yaz) == n)
        # kalici 500 -> DUR, cikis 1
        S.f["T1"]["trashed"] = False
        HATALI.add("T1")
        rc, log = kos(["--mod", "uygula", "--plan", os.path.join(out, "plan.json"), "--cikti", out, "--onay", "TASI",
                       "--isler", "J1"])
        kontrol("kalici 500 FAIL cikis 1", rc == 1 and "DUR" in log)
        # koruma desenleri (dogrudan)
        kontrol("kisisel nokta korunur (J1/J3/J5)", all(M.koruma_nedeni(j, ".", "aile.jpg") == "kisisel_nokta"
                                                        for j in ("J1", "J3", "J5")))
        kontrol("kisisel nokta koku korunur", M.koruma_nedeni("J1", "", ".") == "kisisel_nokta")
        kontrol("yedek deseni J1'de korunur", M.koruma_nedeni("J1", "ARCHIVE", "MOCKUP_V2_YEDEK_X") == "yedek_deseni")
        kontrol("ofis koku J5'te korunur", M.koruma_nedeni("J5", "OFIS", "x.md") == "ofis_koku")
        kontrol("temiz ad korunmaz", M.koruma_nedeni("J1", "ASTROLOVE/TEMP", "VIDEO_V9") is None)
        # istemci kapilari
        d = M.Drive("echo SAHTE_TOKEN")
        for ad, cagri in [("DELETE reddedilir", lambda: d.istek("DELETE", "/files/T1")),
                          ("emptyTrash reddedilir", lambda: d.istek("GET", "/files/trash/emptyTrash")),
                          ("PATCH baska govde reddedilir", lambda: d.istek("PATCH", "/files/T1", {"fields": "id"}, {"name": "x"})),
                          ("PATCH trashed=false reddedilir", lambda: d.istek("PATCH", "/files/T1", None, {"trashed": False})),
                          ("POST istek() ile reddedilir", lambda: d.istek("POST", "/files", None, {"name": "x"})),
                          ("POST klasor disi reddedilir", lambda: d.istek_post_klasor({"name": "x", "mimeType": "text/plain",
                                                                                         "parents": ["A"]}))]:
            try:
                cagri()
                kontrol(ad, False)
            except SystemExit:
                kontrol(ad, True)
        # envanter basligi farkli
        bad = os.path.join(tmp, "bad"); os.makedirs(bad)
        Path(bad, "ENVANTER_PARCA_01A.csv").write_text("id,title\nx,y\n")
        rc, _ = kos(["--mod", "kuru", "--envanter", bad, "--depo", depo, "--cikti", out])
        kontrol("farkli baslik DUR", rc not in (0, None))
    print("SONUC:", "PASS" if not HATA else f"FAIL ({len(HATA)})")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
