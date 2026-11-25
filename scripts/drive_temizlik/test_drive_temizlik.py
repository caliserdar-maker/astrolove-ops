#!/usr/bin/env python3
"""drive_temizlik sahte Drive testi. AG KAPALI: socket bastan engellenir; urllib.request.urlopen bellek ici sahte Drive'a
yonlenir (gercek kod yolu ve istemci kapilari calisir). Sahte Drive: 'name contains' ONEK eslestirir (Drive v3 belgesi),
liste sonuclari 2'lik sayfalara bolunur (nextPageToken), istenirse bir kez 401 verir. git grep yerel gecici depoda kosar.
Bilinen PASS ve bilinen FAIL ornekleri her kapi icin asagida (kontrol adlari)."""
import contextlib
import csv
import hashlib
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


def zt(**k):
    return (SIMDI + timedelta(**k)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


ESKI, YAKIN = zt(days=-40), zt(days=-3)
KOD_KIMLIK = "1" + "K" * 32          # depoda gecen Drive kimligi (sahte)
HATALI = set()
ILK401 = {"kalan": 0, "kotu": None}


class Sahte:
    def __init__(self):
        self.f, self.n, self.yaz = {}, 0, []

    def ekle(self, fid, ad, ust, mime="text/plain", size=100, mod=ESKI, view=None, olus=ESKI, shared=False):
        self.f[fid] = dict(id=fid, name=ad, mimeType=mime, parents=[ust] if ust else [], size=str(size), modifiedTime=mod,
                           viewedByMeTime=view, createdTime=olus, trashed=False, shared=shared, ownedByMe=True,
                           capabilities=dict(canTrash=True, canMoveItemWithinDrive=True))
        return fid

    def cevap(self, req):
        u = urllib.parse.urlparse(req.full_url)
        q = dict(urllib.parse.parse_qsl(u.query))
        yol = u.path.replace("/drive/v3", "")
        m = req.get_method()
        tok = req.headers.get("Authorization", "")
        if ILK401["kalan"] > 0 and m != "GET":
            ILK401["kalan"] -= 1
            ILK401["kotu"] = tok
        if ILK401["kotu"] and tok == ILK401["kotu"]:   # suresi dolan token yenilenmeden kabul edilmez
            raise urllib.error.HTTPError(req.full_url, 401, "exp", {}, io.BytesIO(b""))
        if not req.headers.get("Authorization", "").startswith("Bearer SAHTE"):
            raise AssertionError("token yok")
        if m == "GET" and yol == "/files":
            hepsi = sorted((o for o in self.f.values() if self.esles(q["q"], o)), key=lambda o: o["id"])
            bas = int(q.get("pageToken", "0"))
            c = {"files": [dict(o) for o in hepsi[bas:bas + 2]]}
            if bas + 2 < len(hepsi):
                c["nextPageToken"] = str(bas + 2)
            return c
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
            assert json.loads(req.data) == {"trashed": True}
            self.f[fid]["trashed"] = True
            return {"id": fid, "trashed": True}
        if m == "POST" and yol == "/files":
            g = json.loads(req.data)
            self.n += 1
            fid = f"YENI{self.n}"
            self.ekle(fid, g["name"], g["parents"][0], KL, 0, mod=zt(), olus=zt())
            self.yaz.append((m, fid))
            return {"id": fid}
        raise AssertionError(f"beklenmeyen istek {m} {yol}")

    def esles(self, q, o):
        if "trashed = false" in q and o["trashed"]:
            return False
        r = re.search(r"'([^']+)' in parents", q)
        if r:
            p = "ROOT" if r.group(1) == "root" else r.group(1)
            if p not in o["parents"]:
                return False
        r = re.search(r"name contains '([^']+)'", q)
        if r and not o["name"].startswith(r.group(1)):   # Drive v3: onek
            return False
        r = re.search(r"name = '((?:[^'\\]|\\.)+)'", q)
        if r and o["name"] != r.group(1).replace("\\'", "'"):
            return False
        r = re.search(r"mimeType = '([^']+)'", q)
        if r and o["mimeType"] != r.group(1):
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


def yol(fid):
    p = S.f[fid]["parents"][0]
    return "" if p == "ROOT" else (yol(p) + "/" + S.f[p]["name"]).lstrip("/")


def kur(tmp):
    e = S.ekle
    e("OFIS", "OFIS", "ROOT", KL, 0); e("AST", "ASTROLOVE", "ROOT", KL, 0); e("TEMP", "TEMP", "AST", KL, 0)
    e("ARC", "ARCHIVE", "AST", KL, 0); e("SIP", "SIPARIS", "ROOT", KL, 0); e("NOK", ".", "ROOT", KL, 0)
    e("WP", "WALLPAPER", "AST", KL, 0)
    # J1
    e("T1", "VIDEO_V9_X", "TEMP", KL, 0); e("T1a", "a_video.mp4", "T1", size=1000); e("T1b", "b_video.mp4", "T1", size=2000)
    e("T2", "GALERI_BAKIR", "TEMP", KL, 0); e("T2s", "ALT_TEMIZ", "T2", KL, 0); e("T2s1", "resim_x.jpg", "T2s", size=10)
    e("T2y", "yeni_resim.jpg", "T2", size=10, mod=YAKIN); e("T2e", "eski_resim.jpg", "T2", size=10)
    e("T3", "WA_HERO_ZOOM", "TEMP", KL, 0); e("T3a", "eski_resim.png", "T3"); e("T3n", "envantersiz.png", "T3")
    e("T4", "KODDA_GECEN_KLASOR", "TEMP", KL, 0); e("T4a", "dosya_a.txt", "T4")
    e("T5", "TASINMIS_KLASOR", "AST", KL, 0)
    e("T6", "DEGISMIS.json", "TEMP", mod=zt(days=-20))
    e("T7", "ETSY_TOKEN_eski.json", "TEMP")
    e("T8", "ACILMIS_DOSYA.png", "TEMP", view=YAKIN)
    e("T9", "MERKEZ_OTURUM_KAYDI.md", "OFIS")
    e("T10", "Adsız site", "ROOT")
    e("T11", "LISTE_4123456789", "TEMP", KL, 0); e("T11a", "veri_ham.json", "T11")
    e(KOD_KIMLIK, "KOD_ATASI", "TEMP", KL, 0); e("T12a", "cocuk_dosya.bin", KOD_KIMLIK)
    e("T13", "BANNER_20261001", "TEMP", KL, 0); e("T13a", "banner_a.png", "T13")
    e("T14", "PAYLASILMIS_DOSYA.pdf", "TEMP", shared=True)
    e("T15", "YENI_OLUSAN.png", "TEMP", olus=YAKIN)
    e("T16", "UST_OKUNAN", "TEMP", KL, 0); e("T16s", "ALT_KLASOR_X", "T16", KL, 0); e("T16x", "cocuk_x.png", "T16s")
    e("T16y", "yakin_y.png", "T16", mod=YAKIN)
    e("T17", "TASIMA_SONRASI_KL", "TEMP", KL, 0); e("T17a", "ilk_dosya.png", "T17")
    e("T18", "ICERIDEN_MOCKUP_V2_YEDEK", "WP", KL, 0)
    e("T19", "ALT_NOKTA", "AST", KL, 0); e("T19n", ".", "T19", KL, 0); e("T19a", "aile_foto.jpg", "T19n")
    # J3
    e("Q1", "POD_GALLERY", "TEMP", KL, 0); e("Q1a", "galeri_g.png", "Q1", size=500)
    e("Q2", "POD_PRINT", "TEMP", KL, 0); e("Q2a", "baski_p.tif", "Q2", size=900)
    e("Q3", "SIPARIS_ISIM", "TEMP", KL, 0); e("Q3a", "dosya_f.pdf", "Q3")
    e("Q5", "BASKA_GRUP_KL", "TEMP", KL, 0); e("Q5a", "baska_g.png", "Q5")
    e("Q4", "aile.jpg", "NOK")
    # J2
    e("S1", "9000000001", "SIP", KL, 0); e("S1a", "KAPI_RAPORU_DB.json", "S1"); e("S1b", "AstroLoveArt_X.pdf", "S1")
    e("S2", "3123456789", "SIP", KL, 0); e("S2a", "gercek.pdf", "S2")
    e("S3", "9000000002", "OFIS", KL, 0)
    e("S5", "9000000003", "Q3", KL, 0); e("S5a", "test_t.pdf", "S5")
    e("S6", "9000000000", "Q3", KL, 0); e("S6a", "musteri.pdf", "S6")
    e("S7", "KUPA_SIPARIS_TEST_9000000005", "TEMP", KL, 0)
    e("S8", "9000000006", "SIP", KL, 0); e("S8r", "4123456789", "S8", KL, 0); e("S8a", "test_ok.pdf", "S8")
    # J4
    e("A1", "Adsız proje", "ROOT", SC, 0)
    # J5
    e("R1", "BASKI_DUZELT_1", "TEMP", KL, 0); e("R1a", "duzelt_b.tif", "R1", size=300)
    e("R2", "POD_PRINT_YEDEK_1", "TEMP", KL, 0); e("R2a", "yedek_c.tif", "R2", size=400)
    e("R3", "POD_77_Onay_Hazirligi", "ROOT", KL, 0); e("R3a", "onay_a.png", "R3")
    e("R4", "ESKI_RAPOR_20261001.md", "AST")
    kat = {fid: "KEEP" for fid in S.f}
    for fid in ["T1", "T1a", "T1b", "T2", "T2s", "T2s1", "T2y", "T2e", "T3", "T3a", "T4", "T4a", "T5", "T6", "T7", "T8",
                "T9", "T10", "T11", "T11a", KOD_KIMLIK, "T12a", "T13", "T13a", "T14", "T15", "T16", "T16s", "T16x", "T16y",
                "T17", "T17a", "T18", "T19", "T19n", "T19a", "S7"]:
        kat[fid] = "TRASH"
    for fid in ["Q1", "Q1a", "Q2", "Q2a", "Q3", "Q3a", "Q4", "NOK", "Q5", "Q5a"]:
        kat[fid] = "SERDAR_QUESTION"
    for fid in ["R1", "R1a", "R2", "R2a", "R3", "R3a", "R4"]:
        kat[fid] = "ARCHIVE"
    for fid in ["S1", "S1a", "S1b", "S2", "S2a", "SIP", "OFIS", "S6", "S6a", "S8", "S8r", "S8a"]:
        kat[fid] = "PROTECTED"
    envd = os.path.join(tmp, "env"); os.makedirs(envd)
    sat = []
    for fid, k in kat.items():
        if fid in ("T3n", "S3", "S5", "S5a", "A1"):
            continue  # envanterde yok
        o = S.f[fid]
        p = yol(fid)
        mod = o["modifiedTime"]
        if fid == "T5":
            p = "ASTROLOVE/TEMP"
        if fid == "T6":
            mod = ESKI
        g = "Baska" if fid.startswith("Q5") else "Eski is akisi girdisi"
        sat.append([fid, o["name"], p, o["mimeType"], o["size"], ESKI, mod, k, "r", g, int(o["mimeType"] == KL), ""])
    for i in range(15):
        with open(os.path.join(envd, f"ENVANTER_PARCA_{i:02d}A.csv"), "w", encoding="utf-8-sig", newline="") as h:
            w = csv.writer(h)
            w.writerow(M.BASLIK)
            for s in sat[i::15]:
                w.writerow(s)
    depo = os.path.join(tmp, "depo"); os.makedirs(depo)
    Path(depo, "a.yml").write_text("girdi: gdrive:ASTROLOVE/TEMP/KODDA_GECEN_KLASOR/x\nb: TEMP/BANNER_${damga}\n"
                                   f"root_folder_id={KOD_KIMLIK}\nc: TEMP/UST_OKUNAN/\nd: TEMP/POD_GALLERY/\n")
    g = ["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t"]
    for c in (["init", "-q"], ["add", "."], ["commit", "-qm", "t"], ["checkout", "-qb", "eski"]):
        subprocess.run(g + c, check=True, capture_output=True)
    Path(depo, "b.yml").write_text("x: TEMP/eski_resim.png\n")   # yalniz 'eski' dalinda gecen ad
    for c in (["add", "."], ["commit", "-qm", "e"], ["checkout", "-q", "-"]):
        subprocess.run(g + c, check=True, capture_output=True)
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
        rc, log = kos(["--mod", "kuru", "--envanter", envd, "--depo", depo, "--cikti", out, "--ts", "T0", "--isler", "J3"])
        p0 = json.load(open(os.path.join(out, "plan.json")))
        kontrol("J3 grupsuz: birim yok, olcum var", rc == 0 and p0["birim"] == [] and "SQ-TEMP grup #" in log)
        rc, log = kos(["--mod", "kuru", "--envanter", envd, "--depo", depo, "--cikti", out, "--ts", "T1",
                       "--refler", "HEAD,eski", "--j3-grup", "Eski is akisi girdisi"])
        kontrol("kuru cikis 0", rc == 0)
        kontrol("kuru Drive'a yazmadi", S.yaz == [])
        kontrol("log'da ad/kimlik yok", not re.search(r"VIDEO_V9|GALERI|T1a|aile|9000000001|Eski is akisi|KKKK", log))
        pj = os.path.join(out, "plan.json")
        plan = json.load(open(pj))
        sha = hashlib.sha256(open(pj, "rb").read()).hexdigest()
        kontrol("sha logda", f"plan sha256: {sha}" in log)
        b = {x["id"]: x for x in plan["birim"]}
        at = {x["id"]: x["neden"] for x in plan["atla"]}
        hep = set(b)
        kontrol("J1 temiz klasor tek birim", "T1" in b and b["T1"]["dosya"] == 2 and b["T1"]["bayt"] == 3000 and "T1a" not in b)
        kontrol("J1 yakin dosya klasoru boler", "T2" not in b and "T2s" in b and "T2e" in b and at.get("T2y") == "son14_degisti")
        kontrol("J1 envantersiz oge boler", "T3" not in b and at.get("T3n") == "envanterde_yok")
        kontrol("J1 kodda gecen ad (HEAD)", at.get("T4") == "kodda_geciyor")
        kontrol("J1 yalniz baska dalda gecen ad", at.get("T3a") == "kodda_geciyor")
        kontrol("J1 yol farkli", at.get("T5") == "yol_farkli")
        kontrol("J1 envanterden sonra degisen", at.get("T6") == "envanterden_sonra_degisti")
        kontrol("J1 token deseni", at.get("T7", "").startswith("koruma:"))
        kontrol("J1 son 14 gun acilan", at.get("T8") == "son14_acildi")
        kontrol("J1 OFIS koku korunur", "T9" not in hep and at.get("T9") == "ofis_koku")
        kontrol("J1 Drive koku korunur", "T10" not in hep and at.get("T10") == "drive_koku")
        kontrol("gercek receipt yolu korunur", "T11" not in hep and "T11a" not in hep and at.get("T11") == "gercek_receipt")
        kontrol("koddaki kimlik atlanir", KOD_KIMLIK not in hep and "T12a" not in hep and at.get(KOD_KIMLIK) == "kodda_kimlik")
        kontrol("dinamik onek atlanir", "T13" not in hep and at.get("T13") == "kodda_dinamik_onek")
        kontrol("paylasimli atlanir", at.get("T14") == "paylasimli_ya_da_baskasinin")
        kontrol("yeni olusturulan atlanir", at.get("T15") == "son14_olusturuldu")
        kontrol("bolunen klasorun ata adi kodda: cocuk atlanir", "T16s" not in hep and at.get("T16s") == "kodda_geciyor")
        kontrol("yedek deseni atlanir", "T18" not in hep and at.get("T18") == "yedek_deseni")
        kontrol("ic '.' klasoru korunur", "T19" not in hep and "T19a" not in hep and at.get("T19n") == "kisisel_nokta")
        kontrol("J3 secili grup birim + girdisiz listesi", "Q1" in b and b["Q1"]["is_"] == "J3" and "POD_GALLERY" in plan["girdisiz"])
        kontrol("J3 baska grup secilmez", "Q5" not in hep and "Q5" not in at)
        kontrol("J3 POD_PRINT secilmez", "Q2" not in hep and "Q2a" not in hep)
        kontrol("J3 siparis deseni", at.get("Q3") == "siparis_deseni")
        kontrol("J2 test klasoru tam birim", "S1" in b and b["S1"]["is_"] == "J2" and b["S1"]["dosya"] == 2)
        kontrol("J2 9000000000 ASLA", "S6" not in hep and "S6a" not in hep)
        kontrol("J2 gercek receipt secilmez", "S2" not in hep and "S2a" not in hep)
        kontrol("J2 OFIS altindaki test secilmez", "S3" not in hep)
        kontrol("J2 TEMP siparis altindaki test", "S5" in b and b["S5"]["is_"] == "J2")
        kontrol("J2 adi tam test olmayan J2'ye girmez", "S7" not in hep or b["S7"]["is_"] != "J2")
        kontrol("J2 icinde gercek receipt: bolunur", "S8" not in hep and "S8a" in b and at.get("S8r") == "gercek_receipt")
        kontrol("J4 tasinmaz (tetikleyici)", "A1" not in hep and at.get("A1", "").startswith("tetikleyici_dogrulanamadi"))
        kontrol("J5 hedef TEMP", b.get("R1", {}).get("hedef") == "ASTROLOVE/ARCHIVE/TEMP")
        kontrol("J5 kok ogesi _KOK", b.get("R3", {}).get("hedef") == "ASTROLOVE/ARCHIVE/_KOK")
        kontrol("J5 POD_PRINT_YEDEK izinli", "R2" in b)
        kontrol("J5 eski RAPOR izinli", "R4" in b and b["R4"]["hedef"] == "ASTROLOVE/ARCHIVE")
        kontrol("md/csv yazildi", all(os.path.exists(os.path.join(out, f"KURU_DRIVE_TRASH_T1.{x}")) for x in ("md", "csv")))
        md = open(os.path.join(out, "KURU_DRIVE_TRASH_T1.md")).read()
        kontrol("md: sha ve grup tablosu", sha in md and "Eski is akisi girdisi" in md)
        kontrol("ic ice kapisi (kume)", len(M.ic_ice_temizle([dict(id="a", yol="A/X"), dict(id="b", yol="A/X-2"),
                                                              dict(id="c", yol="A/X/c")], [])) == 2)
        U = ["--mod", "uygula", "--plan", pj, "--cikti", out]
        rc, _ = kos(U + ["--plan-sha", sha])
        kontrol("onaysiz DUR", rc not in (0, None) and S.yaz == [])
        rc, _ = kos(U + ["--onay", "TASI", "--plan-sha", "0" * 64])
        kontrol("yanlis sha DUR", rc not in (0, None) and S.yaz == [])
        S.f["Q1a"]["modifiedTime"] = zt(minutes=5)
        S.f["T2e"]["modifiedTime"] = zt(days=-60)
        S.ekle("T17n", "sonradan.png", "T17", mod=ESKI)
        S.ekle("ARCdup", "ESKI_RAPOR_20261001.md", "ARC")             # J5 hedefte ayni ad
        ILK401["kalan"] = 1
        os.environ["DRIVE_TOKEN_KOMUT"] = "echo SAHTE_TOKEN_$RANDOM"
        rc, log = kos(U + ["--onay", "TASI", "--plan-sha", sha, "--ts", "U1"])
        sat = [json.loads(x) for x in open(os.path.join(out, "uygula.jsonl"))]
        u = {r["id"]: r for r in sat}
        kontrol("uygula cikis 0", rc == 0)
        kontrol("401 sonrasi yenilenip yazildi", ILK401["kalan"] == 0 and u["T1"]["durum"] == "COPE_TASINDI")
        kontrol("J1 Cop + geri okuma", S.f["T1"]["trashed"])
        kontrol("alt oge degisti -> atlandi", u["Q1"]["durum"] == "ATLANDI" and not S.f["Q1"]["trashed"])
        kontrol("birim mtime farkli -> atlandi", u["T2e"]["durum"] == "ATLANDI" and not S.f["T2e"]["trashed"])
        kontrol("eski mtime ile eklenen cocuk -> atlandi", u["T17"]["durum"] == "ATLANDI" and not S.f["T17"]["trashed"])
        kontrol("J5 ARCHIVE/TEMP", u["R1"]["durum"] == "ARSIVE_TASINDI" and S.f[S.f["R1"]["parents"][0]]["parents"] == ["ARC"])
        kontrol("J5 hedefte ayni ad -> atlandi", u["R4"]["durum"] == "ATLANDI" and S.f["R4"]["parents"] == ["AST"])
        kontrol("J5 _KOK kuruldu", S.f[S.f["R3"]["parents"][0]]["name"] == "_KOK")
        kontrol("J5 cop'e gitmedi", not S.f["R1"]["trashed"])
        kontrol("atlananlara dokunulmadi", not any(S.f[x]["trashed"] for x in ("T2y", "T4", "Q2", "S2", "S6", "S6a", "T9",
                                                                              "T10", "T11", "A1", "T19a")))
        kontrol("rapor md", os.path.exists(os.path.join(out, "RAPOR_DRIVE_TRASH_U1.md")))
        n = len(S.yaz)
        rc, _ = kos(U + ["--onay", "TASI", "--plan-sha", sha, "--isler", "J1"])
        kontrol("tekrar uygula yazim yapmaz", len(S.yaz) == n)
        S.f["T1"]["trashed"] = False
        HATALI.add("T1")
        rc, log = kos(U + ["--onay", "TASI", "--plan-sha", sha, "--isler", "J1"])
        kontrol("kalici 500 -> DUR, cikis 1", rc == 1 and "DUR" in log)
        kn = M.koruma_nedeni
        kontrol("kisisel ic nokta", kn("J1", "ASTROLOVE/.", "aile.jpg") == "kisisel_nokta")
        kontrol("apikey/anahtar/font/pem korunur", all(kn("J1", "ASTROLOVE/TEMP", x) for x in
                                                       ("apikey.txt", "API_ANAHTAR.json", "FONTLAR", "x.pem")))
        kontrol("temiz ad korunmaz", kn("J1", "ASTROLOVE/TEMP", "VIDEO_V9") is None)
        kontrol("test receipt gercek sayilmaz", not M.gercek_receipt_var("SIPARIS/9000000003"))
        kontrol("9000000000 gercek sayilir", M.gercek_receipt_var("SIPARIS/9000000000"))
        d = M.Drive("echo SAHTE_TOKEN")
        for ad, cagri in [("DELETE reddedilir", lambda: d.istek("DELETE", "/files/T1")),
                          ("emptyTrash reddedilir", lambda: d.istek("PATCH", "/files/trash/emptyTrash", None, {"trashed": True})),
                          ("PATCH baska govde", lambda: d.istek("PATCH", "/files/T1", {"fields": "id"}, {"name": "x"})),
                          ("PATCH trashed=false", lambda: d.istek("PATCH", "/files/T1", None, {"trashed": False})),
                          ("PATCH ebeveyn + govde", lambda: d.istek("PATCH", "/files/T1", {"addParents": "a",
                                                                    "removeParents": "b", "fields": "id"}, {"trashed": True})),
                          ("POST klasor disi", lambda: d.istek("POST", "/files", None, {"name": "x", "mimeType": "text/plain",
                                                                                         "parents": ["A"]})),
                          ("POST baska yol", lambda: d.istek("POST", "/files/T1/copy", None, {}))]:
            try:
                cagri()
                kontrol(ad, False)
            except SystemExit:
                kontrol(ad, True)
        bad = os.path.join(tmp, "bad"); os.makedirs(bad)
        Path(bad, "ENVANTER_PARCA_01A.csv").write_text("id,title\nx,y\n")
        rc, _ = kos(["--mod", "kuru", "--envanter", bad, "--depo", depo, "--cikti", out])
        kontrol("eksik parca / baslik DUR", rc not in (0, None))
    print("SONUC:", "PASS" if not HATA else f"FAIL ({len(HATA)})")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
