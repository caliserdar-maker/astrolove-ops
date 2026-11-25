#!/usr/bin/env python3
"""Drive temizligi (Serdar 25 Kas 2026, oturumdaki dogrudan onay): 22 Kas envanterine gore Cop kutusuna / ARCHIVE'e tasima.

Isler (kapsam disi her sey dokunulmaz):
  J1 TRASH       envanter category=TRASH                          -> Cop kutusu
  J2 TEST        adinda test receipt (9000 + 6 hane) olan klasor,  -> Cop kutusu
                 SIPARIS ya da ASTROLOVE/TEMP altinda (canli arama)
  J3 SORU_TEMP   category=SERDAR_QUESTION, ASTROLOVE/TEMP altinda, -> Cop kutusu
                 POD_PRINT* ve siparis/musteri/kisisel desenleri haric
  J4 SCRIPT      kokteki tek "Adsiz proje" Apps Script dosyasi     -> Cop kutusu
  J5 ARSIV       category=ARCHIVE                                  -> ASTROLOVE/ARCHIVE/<eski yol> (silme yok)

Kurallar: kalici silme YOK (DELETE ve emptyTrash istemcide engelli; yalniz trashed=true PATCH). Her birim canli yeniden
kontrol edilir; envanterden sonra degismis / son 14 gunde degismis ya da acilmis / envanterde olmayan (yeni) / koruma
desenine uyan / adi otomasyon kodunda gecen oge ATLANIR; klasorde boyle bir alt oge varsa klasor bolunur (yalniz temiz
alt agaclar islenir). Loga yalniz sayi yazilir; ad/kimlik yalniz --cikti klasorune (Drive OFIS'e sahip-yalniz yuklenir).

Modlar:
  kuru    --envanter DIR (ENVANTER_PARCA_*.csv) --depo DIR --cikti DIR  -> plan.json, KURU_*.csv, KURU_*.md
  uygula  --plan plan.json --cikti DIR [--onay TASI]                    -> uygula.json, partiler + geri okuma
Ortam: DRIVE_TOKEN_KOMUT (token basan kabuk komutu; ~40 dk'da bir yeniden cagrilir)."""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

API = "https://www.googleapis.com/drive/v3"
KLASOR = "application/vnd.google-apps.folder"
SCRIPT = "application/vnd.google-apps.script"
ALAN = "id,name,mimeType,parents,size,modifiedTime,viewedByMeTime,trashed,capabilities(canTrash,canMoveItemWithinDrive)"
GUN14 = 14
PARTI = 200

# ---- koruma desenleri (ad ya da yol bileseni; buyuk/kucuk harf duyarsiz) ----
KORUMA_HER_IS = [
    r"astrolove_kayit", r"el_yapimi", r"telif", r"legacy_components", r"ana_sembol", r"(^|/)brand(/|$)",
    r"token", r"secret", r"credential", r"parola", r"password", r"sifre", r"(^|[^a-z])key([^a-z]|$)", r"\.env$",
    r"rclone", r"oauth", r"\.(psd|ai|svg|ttf|otf|woff2?)$", r"(^|/)fonts?(/|$)", r"zemin", r"sablon", r"template",
    r"sembol", r"symbol", r"\[gizlendi\]", r"devir", r"karar", r"start_here", r"yapilacak",
]
KORUMA_YEDEK = [r"yedek", r"duplicate", r"backup"]          # J5'te yalniz POD_PRINT_YEDEK_ izinli
KORUMA_SIPARIS = [r"siparis", r"musteri", r"kisisel", r"(^|/|_)isim(/|_|$)", r"teslim", r"receipt", r"order"]
KORUMA_RAPOR = [r"rapor", r"soru"]                          # J5'te 14 gunden eski ve OFIS koku disi izinli
TEST_RECEIPT = re.compile(r"(?<!\d)9000\d{6}(?!\d)")


def _eslesir(desenler, metin):
    m = metin.lower()
    return next((d for d in desenler if re.search(d, m)), None)


def koruma_nedeni(is_, yol, ad, mime=""):
    """None = korunmuyor; aksi halde neden (desen). yol = ust yol, ad = oge adi."""
    tam = (yol + "/" + ad) if yol else ad
    ilk = tam.split("/")[0]
    if ilk == ".":
        return "kisisel_nokta"
    if ilk == "OFIS" and "/" not in tam[len("OFIS/"):] and tam != "OFIS" and is_ != "J1":
        return "ofis_koku"
    if ilk == "OFIS" and is_ == "J1" and _eslesir(KORUMA_RAPOR, ad):
        return "ofis_rapor"
    d = _eslesir(KORUMA_HER_IS, tam)
    if d:
        return "koruma:" + d
    if is_ != "J2":
        if _eslesir(KORUMA_SIPARIS, tam):
            return "siparis_deseni"
    if _eslesir(KORUMA_YEDEK, tam) and not (is_ == "J5" and re.search(r"pod_print_yedek_", tam.lower())):
        return "yedek_deseni"
    if is_ not in ("J2", "J5") and _eslesir(KORUMA_RAPOR, tam):
        return "rapor_deseni"
    if is_ == "J5" and _eslesir(KORUMA_RAPOR, tam) and ilk == "OFIS" and tam.count("/") == 1:
        return "ofis_koku_rapor"
    if mime == SCRIPT and is_ != "J4":
        return "apps_script"
    return None


# ---- Drive istemcisi ----
class Drive:
    def __init__(self, token_komut):
        self.komut, self.tok, self.t = token_komut, None, 0
        self.istek_say = 0

    def token(self):
        if not self.tok or time.time() - self.t > 40 * 60:
            out = subprocess.run(["bash", "-c", self.komut], capture_output=True, text=True, timeout=120)
            tok = out.stdout.strip()
            if out.returncode != 0 or not tok or tok == "null":
                raise SystemExit("HATA: Drive token alinamadi")
            self.tok, self.t = tok, time.time()
        return self.tok

    def istek(self, yontem, yol, params=None, govde=None, deneme=6):
        if yontem not in ("GET", "PATCH", "POST"):
            raise SystemExit(f"HATA: {yontem} yasak (kalici silme yok)")
        if "emptyTrash" in yol or yontem == "POST":
            raise SystemExit("HATA: izinsiz yazim yolu")
        if yontem == "PATCH" and (govde != {"trashed": True} or set(params or {}) - {"fields"}):
            raise SystemExit("HATA: PATCH yalniz trashed=true")
        url = API + yol + ("?" + urllib.parse.urlencode(params) if params else "")
        veri = json.dumps(govde).encode() if govde is not None else None
        for i in range(deneme):
            self.istek_say += 1
            req = urllib.request.Request(url, data=veri, method=yontem, headers={
                "Authorization": "Bearer " + self.token(), "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    b = r.read()
                    return json.loads(b) if b else {}
            except urllib.error.HTTPError as e:
                ic = e.read() or b""
                if e.code == 401 and i < deneme - 1:
                    self.tok = None
                    continue
                if (e.code in (429, 500, 502, 503) or (e.code == 403 and b"ateLimit" in ic)) and i < deneme - 1:
                    time.sleep(2 ** (i + 1))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                if i < deneme - 1:
                    time.sleep(2 ** (i + 1))
                    continue
                raise

    def get(self, fid):
        return self.istek("GET", f"/files/{fid}", {"fields": ALAN, "supportsAllDrives": "true"})

    def liste(self, q, alan=ALAN):
        cikti, sayfa = [], None
        while True:
            p = {"q": q, "fields": f"nextPageToken,files({alan})", "pageSize": 1000}
            if sayfa:
                p["pageToken"] = sayfa
            d = self.istek("GET", "/files", p)
            cikti += d.get("files", [])
            sayfa = d.get("nextPageToken")
            if not sayfa:
                return cikti

    def cocuklar(self, fid):
        return self.liste(f"'{fid}' in parents and trashed = false")


# ---- envanter ----
def envanter_oku(klasor):
    dosyalar = sorted(glob.glob(os.path.join(klasor, "ENVANTER_PARCA_*.csv")))
    if not dosyalar:
        raise SystemExit("HATA: envanter parcasi yok")
    beklenen = ["id", "title", "path", "mimeType", "size", "created", "modified", "category", "reason", "group",
                "isFolder", "fileCount"]
    inv = {}
    for f in dosyalar:
        with open(f, encoding="utf-8-sig", newline="") as h:
            r = csv.DictReader(h)
            if r.fieldnames != beklenen:
                raise SystemExit("HATA: envanter basligi beklenenden farkli (DUR)")
            for s in r:
                if s["id"] in inv:
                    continue
                s["klasor"] = s["mimeType"] == KLASOR
                s["boyut"] = int(s["size"] or 0)
                inv[s["id"]] = s
    return inv, len(dosyalar)


def tam_yol(s):
    return (s["path"] + "/" + s["title"]) if s["path"] else s["title"]


def uygun_satir(is_, s):
    """envanter satiri bu isin kapsaminda mi (koruma ayri bakilir)."""
    k, yol = s["category"], tam_yol(s)
    if is_ == "J1":
        return k == "TRASH"
    if is_ == "J3":
        if k != "SERDAR_QUESTION" or not yol.startswith("ASTROLOVE/TEMP/"):
            return False
        return not any(p.upper().startswith("POD_PRINT") for p in yol.split("/"))
    if is_ == "J5":
        return k == "ARCHIVE" and not yol.startswith("ASTROLOVE/ARCHIVE/") and yol != "ASTROLOVE/ARCHIVE"
    return False


# ---- canli yol ----
class Yollar:
    def __init__(self, drive):
        self.d, self.on = drive, {}
        kok = drive.get("root")
        self.kok = kok["id"]

    def ust_yol(self, oge):
        """ogenin ust klasor yolu (kok = ''); birden fazla ebeveyn -> None."""
        p = oge.get("parents") or []
        if len(p) != 1:
            return None
        return self.yol(p[0])

    def yol(self, fid):
        if fid == self.kok:
            return ""
        if fid not in self.on:
            o = self.d.get(fid)
            u = self.ust_yol(o)
            self.on[fid] = None if u is None else ((u + "/" + o["name"]) if u else o["name"])
        return self.on[fid]


def _tarih(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None


class Kuru:
    def __init__(self, drive, inv, depo, simdi):
        self.d, self.inv, self.depo = drive, inv, depo
        self.simdi = simdi
        self.esik14 = simdi - timedelta(days=GUN14)
        self.env_t = max(_tarih(s["modified"]) for s in inv.values() if s["modified"])
        self.yollar = Yollar(drive)
        self.birim, self.atla = [], []

    # bir canli ogenin "temiz" olup olmadigi; temiz degilse neden
    def oge_neden(self, is_, o, ust):
        if o.get("trashed"):
            return "zaten_copte"
        m, v = _tarih(o.get("modifiedTime")), _tarih(o.get("viewedByMeTime"))
        if m and m >= self.esik14:
            return "son14_degisti"
        if v and v >= self.esik14:
            return "son14_acildi"
        n = koruma_nedeni(is_, ust, o["name"], o.get("mimeType", ""))
        if n:
            return n
        if is_ in ("J1", "J3", "J5"):
            s = self.inv.get(o["id"])
            if s is None:
                return "envanterde_yok"
            if not uygun_satir(is_, s):
                return "kategori_farkli"
            if s["modified"] and m and abs((m - _tarih(s["modified"])).total_seconds()) > 1:
                return "envanterden_sonra_degisti"
            if tam_yol(s) != ((ust + "/" + o["name"]) if ust else o["name"]):
                return "yol_farkli"
        return None

    def agac(self, kok):
        """kok dahil canli alt agac: {id: oge}, cocuk listesi. Paralel BFS."""
        ogeler, cocuk = {kok["id"]: kok}, {kok["id"]: []}
        seviye = [kok["id"]] if kok["mimeType"] == KLASOR else []
        with ThreadPoolExecutor(8) as ex:
            while seviye:
                sonuc = list(ex.map(self.d.cocuklar, seviye))
                yeni = []
                for fid, cs in zip(seviye, sonuc):
                    for c in cs:
                        if c["id"] in ogeler:
                            continue
                        ogeler[c["id"]] = c
                        cocuk[fid].append(c["id"])
                        cocuk[c["id"]] = []
                        if c["mimeType"] == KLASOR:
                            yeni.append(c["id"])
                seviye = yeni
        return ogeler, cocuk

    def bol(self, is_, kok, ust_yol, hedef=None):
        """kok birimini canli kontrol et; temizse tek birim, degilse temiz alt agaclara bol."""
        ogeler, cocuk = self.agac(kok)
        neden, temiz, boy, say = {}, {}, {}, {}

        # ust yol haritasi
        ust = {kok["id"]: ust_yol}
        sira = [kok["id"]]
        for fid in sira:
            o = ogeler[fid]
            ad_yol = (ust[fid] + "/" + o["name"]) if ust[fid] else o["name"]
            for c in cocuk[fid]:
                ust[c] = ad_yol
                sira.append(c)
        for fid in reversed(sira):
            o = ogeler[fid]
            neden[fid] = self.oge_neden(is_, o, ust[fid])
            if o["mimeType"] == KLASOR:
                boy[fid] = sum(boy[c] for c in cocuk[fid])
                say[fid] = sum(say[c] for c in cocuk[fid])
                temiz[fid] = neden[fid] is None and all(temiz[c] for c in cocuk[fid])
            else:
                boy[fid] = int(o.get("size") or 0)
                say[fid] = 1
                temiz[fid] = neden[fid] is None

        def topla(fid):
            o = ogeler[fid]
            yol = (ust[fid] + "/" + o["name"]) if ust[fid] else o["name"]
            if temiz[fid]:
                cap = o.get("capabilities") or {}
                if not cap.get("canMoveItemWithinDrive" if is_ == "J5" else "canTrash", False):
                    self.atla.append(dict(is_=is_, id=fid, yol=yol, neden="drive_izin_yok", dosya=say[fid], bayt=boy[fid]))
                    return
                self.birim.append(dict(is_=is_, id=fid, yol=yol, ust_id=(o.get("parents") or [None])[0],
                                       klasor=o["mimeType"] == KLASOR, dosya=say[fid], bayt=boy[fid],
                                       modifiedTime=o.get("modifiedTime"), ad=o["name"]))
                return
            if neden[fid] is not None or o["mimeType"] != KLASOR:
                self.atla.append(dict(is_=is_, id=fid, yol=yol, neden=neden[fid] or "?", dosya=say[fid], bayt=boy[fid]))
                return
            for c in cocuk[fid]:
                topla(c)
            # klasorun kendisi kalir (icinde atlanan var); bunu ayri saymiyoruz (dosya 0)

        topla(kok["id"])

    def kokler(self, is_):
        uyg = {i: s for i, s in self.inv.items() if uygun_satir(is_, s)}
        klasor_yol = {}
        for s in uyg.values():
            if s["klasor"]:
                klasor_yol.setdefault(tam_yol(s), 0)
        return [s for s in uyg.values() if s["path"] not in klasor_yol]

    def is_env(self, is_):
        kok = self.kokler(is_)
        print(f"{is_}: envanter kok birim {len(kok)}")
        for n, s in enumerate(kok, 1):
            try:
                o = self.d.get(s["id"])
            except urllib.error.HTTPError as e:
                self.atla.append(dict(is_=is_, id=s["id"], yol=tam_yol(s), neden=f"okunamadi_{e.code}", dosya=0, bayt=0))
                continue
            u = self.yollar.ust_yol(o)
            if u is None:
                self.atla.append(dict(is_=is_, id=s["id"], yol=tam_yol(s), neden="ebeveyn_belirsiz", dosya=0, bayt=0))
                continue
            self.bol(is_, o, u)
            if n % 50 == 0:
                print(f"  {is_} {n}/{len(kok)} kok islendi")

    def is_test(self):
        aday = self.d.liste(f"name contains '9000' and mimeType = '{KLASOR}' and trashed = false")
        aday = [o for o in aday if TEST_RECEIPT.search(o["name"])]
        secilen = []
        for o in aday:
            u = self.yollar.ust_yol(o)
            if u is None:
                continue
            if not (u == "SIPARIS" or u.startswith("SIPARIS/") or u == "ASTROLOVE/SIPARIS"
                    or u.startswith("ASTROLOVE/SIPARIS/") or u.startswith("ASTROLOVE/TEMP/") or u == "ASTROLOVE/TEMP"):
                continue
            if any(TEST_RECEIPT.search(p) for p in u.split("/")):
                continue  # ust klasoru zaten test klasoru: ust birim kapsar
            secilen.append((o, u))
        print(f"J2: test klasoru {len(secilen)} (aday {len(aday)})")
        for o, u in secilen:
            self.bol("J2", o, u)

    def is_script(self):
        aday = self.d.liste(f"mimeType = '{SCRIPT}' and 'root' in parents and trashed = false")
        aday = [o for o in aday if o["name"].strip().lower() in ("adsız proje", "adsiz proje", "untitled project")]
        print(f"J4: kokte adsiz Apps Script {len(aday)}")
        if len(aday) != 1:
            for o in aday:
                self.atla.append(dict(is_="J4", id=o["id"], yol=o["name"], neden=f"birden_fazla_{len(aday)}", dosya=1, bayt=0))
            return
        o = aday[0]
        n = self.oge_neden("J4", o, "")
        if n:
            self.atla.append(dict(is_="J4", id=o["id"], yol=o["name"], neden=n, dosya=1, bayt=0))
        else:
            self.birim.append(dict(is_="J4", id=o["id"], yol=o["name"], ust_id=(o.get("parents") or [None])[0], klasor=False,
                                   dosya=1, bayt=0, modifiedTime=o.get("modifiedTime"), ad=o["name"],
                                   not_="tetikleyici Drive API ile gorulemez"))

    def kod_kontrol(self):
        """birim adlari otomasyon kodunda geciyor mu (git grep -F); gecen birim ATLANIR."""
        adlar = sorted({b["ad"] for b in self.birim if b["is_"] in ("J1", "J3", "J5")})
        if not adlar:
            return 0
        desen = os.path.abspath(os.path.join(self.depo, "..", "_drive_adlar.txt"))
        with open(desen, "w") as h:
            h.write("\n".join(adlar) + "\n")
        r = subprocess.run(["git", "-C", self.depo, "grep", "-F", "-o", "-h", "-I", "-f", desen, "--", "."],
                           capture_output=True, text=True)
        os.unlink(desen)
        if r.returncode not in (0, 1):
            raise SystemExit("HATA: git grep")
        bulunan = set(r.stdout.split("\n")) - {""}
        kalan, atilan = [], 0
        for b in self.birim:
            if b["is_"] in ("J1", "J3", "J5") and (b["ad"] in bulunan or len(b["ad"]) < 6):
                self.atla.append(dict(b, neden="kodda_geciyor" if b["ad"] in bulunan else "ad_kisa_kontrol_edilemez"))
                atilan += 1
            else:
                kalan.append(b)
        self.birim = kalan
        return atilan


def arsiv_hedef(yol):
    """J5 hedef ust yolu: ASTROLOVE/ARCHIVE/<eski ust yol, ASTROLOVE/ oneki olmadan>."""
    ust = yol.rsplit("/", 1)[0] if "/" in yol else ""
    if ust.startswith("ASTROLOVE/"):
        ust = ust[len("ASTROLOVE/"):]
    elif ust == "ASTROLOVE":
        ust = ""
    return "ASTROLOVE/ARCHIVE" + ("/" + ust if ust else "")


def gb(b):
    return f"{b / 1e9:.2f}".replace(".", ",")


def kuru(a):
    inv, parca = envanter_oku(a.envanter)
    kat = {}
    for s in inv.values():
        k = kat.setdefault(s["category"], [0, 0, 0])
        if s["klasor"]:
            k[2] += 1
        else:
            k[0] += 1
            k[1] += s["boyut"]
    print(f"envanter: parca {parca}, kayit {len(inv)}")
    for k, v in sorted(kat.items()):
        print(f"  {k}: dosya {v[0]}, {gb(v[1])} GB, klasor {v[2]}")
    d = Drive(os.environ["DRIVE_TOKEN_KOMUT"])
    simdi = datetime.now(timezone.utc)
    k = Kuru(d, inv, a.depo, simdi)
    for is_ in a.isler.split(","):
        if is_ in ("J1", "J3", "J5"):
            k.is_env(is_)
        elif is_ == "J2":
            k.is_test()
        elif is_ == "J4":
            k.is_script()
        else:
            raise SystemExit("HATA: is")
    kodda = k.kod_kontrol()
    for b in k.birim:
        if b["is_"] == "J5":
            b["hedef"] = arsiv_hedef(b["yol"])
    # cakisma kapisi: ayni id iki birimde ya da bir birim digerinin alt agacinda olamaz
    ids = [b["id"] for b in k.birim]
    if len(ids) != len(set(ids)):
        raise SystemExit("HATA: ayni oge iki birimde (DUR)")
    yollar = sorted(b["yol"] for b in k.birim)
    for x, y in zip(yollar, yollar[1:]):
        if y.startswith(x + "/"):
            raise SystemExit("HATA: ic ice birim (DUR)")
    os.makedirs(a.cikti, exist_ok=True)
    plan = dict(surum=1, kuru_t=simdi.isoformat(), esik14=k.esik14.isoformat(), birim=k.birim, atla=k.atla)
    json.dump(plan, open(os.path.join(a.cikti, "plan.json"), "w"), ensure_ascii=False, indent=0)
    ts = a.ts
    with open(os.path.join(a.cikti, f"KURU_DRIVE_TRASH_{ts}.csv"), "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["durum", "is", "id", "yol", "klasor", "dosya", "bayt", "neden_ya_da_hedef"])
        for b in k.birim:
            w.writerow(["TASINACAK", b["is_"], b["id"], b["yol"], int(b["klasor"]), b["dosya"], b["bayt"], b.get("hedef", "COP")])
        for b in k.atla:
            w.writerow(["ATLANDI", b["is_"], b["id"], b["yol"], "", b["dosya"], b["bayt"], b["neden"]])
    ozet = ozet_tablo(k.birim, k.atla)
    md = [f"# Kuru kosu: Drive temizligi ({ts})", "", "Salt okuma. Drive'da hicbir sey degismedi.", "",
          f"Envanter: {len(inv)} kayit, {parca} parca (22 Kas). Canli kontrol: {simdi.isoformat()[:16]} UTC. "
          f"14 gun esigi: {k.esik14.isoformat()[:10]}. Drive istek: {d.istek_say}.", "",
          "| Is | Tasinacak birim | Dosya | GB | Atlanan dosya | Atlanan GB |", "|---|---|---|---|---|---|"]
    for is_, v in sorted(ozet["is"].items()):
        md.append(f"| {is_} | {v[0]} | {v[1]} | {gb(v[2])} | {v[3]} | {gb(v[4])} |")
    md += ["", "Atlama nedenleri (dosya sayisi):", ""]
    for n, v in sorted(ozet["neden"].items(), key=lambda x: -x[1][0]):
        md.append(f"- {n}: {v[0]} dosya, {gb(v[1])} GB, {v[2]} kayit")
    md += ["", f"Kodda gecen ya da kisa adli (atlanan) birim: {kodda}.",
           "J4 not: Apps Script tetikleyicisi Drive API ile gorulemez; tetikleyici kontrolu yapilamadi.",
           "Liste: ayni klasordeki KURU_DRIVE_TRASH_" + ts + ".csv"]
    open(os.path.join(a.cikti, f"KURU_DRIVE_TRASH_{ts}.md"), "w").write("\n".join(md) + "\n")
    for is_, v in sorted(ozet["is"].items()):
        print(f"{is_}: tasinacak birim {v[0]}, dosya {v[1]}, {gb(v[2])} GB | atlanan dosya {v[3]}, {gb(v[4])} GB")
    print(f"Drive istek: {d.istek_say}")
    return 0


def ozet_tablo(birim, atla):
    o = {"is": {}, "neden": {}}
    for b in birim:
        v = o["is"].setdefault(b["is_"], [0, 0, 0, 0, 0])
        v[0] += 1; v[1] += b["dosya"]; v[2] += b["bayt"]
    for b in atla:
        v = o["is"].setdefault(b["is_"], [0, 0, 0, 0, 0])
        v[3] += b["dosya"]; v[4] += b["bayt"]
        n = o["neden"].setdefault(b["is_"] + ":" + b["neden"].split(":")[0], [0, 0, 0])
        n[0] += b["dosya"]; n[1] += b["bayt"]; n[2] += 1
    return o


# ---- uygula ----
def klasor_yolu_kur(d, yollar, hedef, onbellek):
    """ASTROLOVE/ARCHIVE/... yolunu bul/kur; her seviyede tam 1 klasor beklenir (2+ -> None)."""
    if hedef in onbellek:
        return onbellek[hedef]
    ust_ad, _, ad = hedef.rpartition("/")
    if not ust_ad:
        q = f"name = '{_kacis(ad)}' and mimeType = '{KLASOR}' and 'root' in parents and trashed = false"
        f = d.liste(q, "id,name")
        if len(f) != 1:
            onbellek[hedef] = None
            return None
        onbellek[hedef] = f[0]["id"]
        return f[0]["id"]
    ust = klasor_yolu_kur(d, yollar, ust_ad, onbellek)
    if ust is None:
        onbellek[hedef] = None
        return None
    f = d.liste(f"name = '{_kacis(ad)}' and mimeType = '{KLASOR}' and '{ust}' in parents and trashed = false", "id,name")
    if len(f) > 1:
        onbellek[hedef] = None
        return None
    if f:
        onbellek[hedef] = f[0]["id"]
    else:
        onbellek[hedef] = d.istek_post_klasor({"name": ad, "mimeType": KLASOR, "parents": [ust]})
    return onbellek[hedef]


def _kacis(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _post_klasor(self, govde):
    if set(govde) != {"name", "mimeType", "parents"} or govde["mimeType"] != KLASOR:
        raise SystemExit("HATA: POST yalniz klasor")
    url = API + "/files?fields=id"
    req = urllib.request.Request(url, data=json.dumps(govde).encode(), method="POST", headers={
        "Authorization": "Bearer " + self.token(), "Content-Type": "application/json"})
    self.istek_say += 1
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["id"]


Drive.istek_post_klasor = _post_klasor


def tasi(d, fid, ekle, cikar):
    """J5: ebeveyn degistir (addParents/removeParents); govde yok."""
    url = API + f"/files/{fid}?" + urllib.parse.urlencode({"addParents": ekle, "removeParents": cikar, "fields": "id,parents"})
    for i in range(6):
        d.istek_say += 1
        req = urllib.request.Request(url, data=b"{}", method="PATCH", headers={
            "Authorization": "Bearer " + d.token(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < 5:
                time.sleep(2 ** (i + 1))
                continue
            raise


def uygula(a):
    if a.onay != "TASI":
        raise SystemExit("HATA: uygula icin --onay TASI")
    plan = json.load(open(a.plan))
    if plan.get("surum") != 1:
        raise SystemExit("HATA: plan surumu")
    d = Drive(os.environ["DRIVE_TOKEN_KOMUT"])
    yollar = Yollar(d)
    birim = [b for b in plan["birim"] if b["is_"] in a.isler.split(",")]
    # kuru kosudan sonra degisen/acilan ogeler: atalari birim ise birim atlanir
    t = datetime.fromisoformat(plan["kuru_t"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    yeni = d.liste(f"(modifiedTime > '{t}' or viewedByMeTime > '{t}') and trashed = false", "id,parents")
    birim_ids = {b["id"] for b in birim}
    kirli = set()
    ata_on = {}

    def atalar(fid, derin=0):
        if fid in ata_on:
            return ata_on[fid]
        if derin > 60 or fid == yollar.kok:
            return set()
        try:
            o = d.istek("GET", f"/files/{fid}", {"fields": "id,parents"})
        except urllib.error.HTTPError:
            return set()
        s = set()
        for p in o.get("parents") or []:
            s |= {p} | atalar(p, derin + 1)
        ata_on[fid] = s
        return s

    for o in yeni:
        s = {o["id"]}
        for p in o.get("parents") or []:
            s |= {p} | atalar(p)
        kirli |= s & birim_ids
    print(f"uygula: plan birim {len(birim)}, kuru kosudan sonra degisen oge {len(yeni)}, etkilenen birim {len(kirli)}")
    sonuc, hedef_on = [], {}
    t0 = time.time()
    partiler = [birim[i:i + PARTI] for i in range(0, len(birim), PARTI)]
    toplam_hata = 0
    for pn, parti in enumerate(partiler, 1):
        ok = atl = hata = 0
        pdosya = pbayt = 0
        for b in parti:
            r = dict(is_=b["is_"], id=b["id"], yol=b["yol"], dosya=b["dosya"], bayt=b["bayt"], eski_ust=b["ust_id"])
            try:
                if b["id"] in kirli:
                    raise _Atla("kuru_sonrasi_degisti")
                o = d.get(b["id"])
                if o.get("trashed"):
                    raise _Atla("zaten_copte")
                if (o.get("parents") or [None]) != [b["ust_id"]]:
                    raise _Atla("ebeveyn_degisti")
                if o.get("modifiedTime") != b["modifiedTime"]:
                    raise _Atla("kuru_sonrasi_degisti")
                if b["is_"] == "J5":
                    hid = klasor_yolu_kur(d, yollar, b["hedef"], hedef_on)
                    if hid is None:
                        raise _Atla("hedef_klasor_belirsiz")
                    tasi(d, b["id"], hid, b["ust_id"])
                    g = d.get(b["id"])
                    if (g.get("parents") or []) != [hid]:
                        raise _Hata("geri_okuma_ebeveyn")
                    r.update(durum="ARSIVE_TASINDI", yeni_ust=hid)
                else:
                    d.istek("PATCH", f"/files/{b['id']}", {"fields": "id,trashed"}, {"trashed": True})
                    g = d.get(b["id"])
                    if g.get("trashed") is not True:
                        raise _Hata("geri_okuma_trashed")
                    r.update(durum="COPE_TASINDI")
                ok += 1; pdosya += b["dosya"]; pbayt += b["bayt"]
            except _Atla as e:
                r.update(durum="ATLANDI", neden=str(e)); atl += 1
            except (_Hata, urllib.error.HTTPError, urllib.error.URLError) as e:
                r.update(durum="HATA", neden=getattr(e, "code", None) or str(e)); hata += 1
            sonuc.append(r)
        toplam_hata += hata
        gecen = time.time() - t0
        kalan = gecen / pn * (len(partiler) - pn)
        print(f"parti {pn}/{len(partiler)} ({100 * pn // len(partiler)}%): birim {len(parti)}, tasinan {ok} "
              f"({pdosya} dosya, {gb(pbayt)} GB), atlanan {atl}, hata {hata} | gecen {gecen / 60:.1f} dk, kalan ~{kalan / 60:.1f} dk")
        json.dump(dict(plan_kuru_t=plan["kuru_t"], sonuc=sonuc), open(os.path.join(a.cikti, "uygula.json"), "w"),
                  ensure_ascii=False, indent=0)
        if hata:
            print("DUR: partide hata var; kalan partiler islenmedi")
            break
    say = {}
    for r in sonuc:
        v = say.setdefault((r["is_"], r["durum"]), [0, 0, 0])
        v[0] += 1; v[1] += r["dosya"]; v[2] += r["bayt"]
    for (is_, durum), v in sorted(say.items()):
        print(f"{is_} {durum}: birim {v[0]}, dosya {v[1]}, {gb(v[2])} GB")
    islenmeyen = len(birim) - len(sonuc)
    print(f"islenmeyen birim {islenmeyen}; Drive istek {d.istek_say}")
    print("SONUC:", "PASS" if toplam_hata == 0 and islenmeyen == 0 else "FAIL")
    return 0 if toplam_hata == 0 and islenmeyen == 0 else 1


class _Atla(Exception):
    pass


class _Hata(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kuru", "uygula"], required=True)
    ap.add_argument("--isler", default="J1,J2,J3,J4,J5")
    ap.add_argument("--envanter")
    ap.add_argument("--depo")
    ap.add_argument("--plan")
    ap.add_argument("--onay", default="")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ts", default=datetime.now(timezone(timedelta(hours=3))).strftime("%Y%m%d_%H%M"))
    a = ap.parse_args()
    if not set(a.isler.split(",")) <= {"J1", "J2", "J3", "J4", "J5"}:
        raise SystemExit("HATA: isler")
    os.makedirs(a.cikti, exist_ok=True)
    if a.mod == "kuru":
        if not (a.envanter and a.depo):
            raise SystemExit("HATA: kuru icin --envanter ve --depo")
        return kuru(a)
    if not a.plan:
        raise SystemExit("HATA: uygula icin --plan")
    return uygula(a)


if __name__ == "__main__":
    sys.exit(main())
