#!/usr/bin/env python3
"""Drive temizligi (Serdar 25 Kas 2026, oturumdaki dogrudan onay): 22 Kas envanterine gore Cop kutusuna / ARCHIVE'e tasima.

Isler (kapsam disi her sey dokunulmaz):
  J1 TRASH       envanter category=TRASH                                      -> Cop kutusu
  J2 TEST        adi tam olarak 900000000N (N=1..9) olan klasor, SIPARIS* ya   -> Cop kutusu
                 da ASTROLOVE/TEMP altinda (canli arama; 9000000000 = gercek siparis ornegi, ASLA)
  J3 SORU_TEMP   category=SERDAR_QUESTION, group --j3-grup ile ayni,           -> Cop kutusu
                 ASTROLOVE/TEMP altinda, POD_PRINT* haric (grup verilmezse J3 yalniz olculur)
  J4 SCRIPT      kokteki "Adsiz proje" Apps Script: yalniz olculur (tetikleyici Drive API'de gorulmez -> ATLA)
  J5 ARSIV       category=ARCHIVE                                             -> ASTROLOVE/ARCHIVE/<eski yol>

Kurallar: kalici silme YOK (istemci yalniz GET, trashed=true PATCH, ebeveyn degistirme PATCH ve klasor olusturma POST'una
izin verir). Her birim canli okunur; envanterden sonra degisen, son 14 gunde degisen/acilan/olusturulan, envanterde olmayan,
paylasilmis ya da sahibi baskasi olan, birden fazla ebeveynli, koruma desenine uyan (gercek receipt numarasi dahil), adi ya
da ata adi otomasyon kodunda (tum dallar) gecen, koddaki bir Drive kimliginin alt agacinda/atasinda olan oge ATLANIR;
klasorde boyle bir alt oge varsa klasor bolunur. uygula her birimin alt agacini yeniden okur ve kuru agacla birebir
karsilastirir. Loga yalniz sayi yazilir; ad/kimlik yalniz --cikti klasorune (Drive OFIS'e sahip-yalniz yuklenir).
Ortam: DRIVE_TOKEN_KOMUT (token basan komut), YUKLE_KOMUT (uygula: kayit dosyasini Drive'a yukleyen komut; $1 = dosya)."""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

API = "https://www.googleapis.com/drive/v3"
KLASOR = "application/vnd.google-apps.folder"
SCRIPT = "application/vnd.google-apps.script"
ALAN = ("id,name,mimeType,parents,size,modifiedTime,viewedByMeTime,createdTime,trashed,shared,ownedByMe,"
        "capabilities(canTrash,canMoveItemWithinDrive)")
GUN14 = 14
PARTI = 200
PARCA_BEKLENEN = 15
SURE_BUTCE_DK = 290

# ---- koruma desenleri (tam yol uzerinde; buyuk/kucuk harf duyarsiz) ----
KORUMA_HER_IS = [
    r"astrolove_kayit", r"el_yapimi", r"telif", r"legacy_components", r"ana_sembol", r"(^|/)brand(/|$)",
    r"token", r"secret", r"credential", r"parola", r"password", r"sifre", r"key", r"anahtar", r"gizli", r"\.env$",
    r"\.pem$", r"\.p12$", r"\.pfx$", r"service_?account", r"rclone", r"oauth", r"cookie",
    r"\.(psd|ai|svg|eps|indd|afdesign|afphoto|xcf|ttf|otf|woff2?)$", r"font", r"zemin", r"sablon", r"template",
    r"sembol", r"symbol", r"\[gizlendi\]", r"devir", r"karar", r"start_here", r"yapilacak", r"kayit", r"kayd",
    r"merkez", r"oturum", r"gunluk", r"(^|[^a-z])ders",
]
KORUMA_YEDEK = [r"yedek", r"duplicate", r"backup"]          # J5'te yalniz POD_PRINT_YEDEK_ izinli
KORUMA_SIPARIS = [r"siparis", r"musteri", r"kisisel", r"(^|/|_)isim(/|_|$)", r"teslim", r"receipt", r"order"]
KORUMA_RAPOR = [r"rapor", r"soru"]                          # J5'te izinli (14 gun kurali ve OFIS/kok korumasi ayrica)
TEST_AD = re.compile(r"^900000000[1-9]$")
GERCEK_RECEIPT = re.compile(r"(?<!\d)[1-9]\d{9}(?!\d)")     # 10 haneli; test numaralari ayrica dislanir
KOD_ONEK_E = r"/[A-Za-z][A-Za-z0-9_]{3,}(\$\{|\$[A-Za-z_]|\{[A-Za-z_]|[\"'][[:space:]]*\+|%s|%\()"
KOD_ONEK = re.compile(r"/([A-Za-z][A-Za-z0-9_]{3,})(?:\$\{|\$[A-Za-z_]|\{[A-Za-z_]|[\"']\s*\+|%s|%\()")
GENEL_ATA = {"ASTROLOVE", "TEMP", "OFIS"}
# J3 envanterinde klasor satirlari ayri grupta; bu gruptaki TEMP klasorleri J3 koku olabilir (icerik oge oge kontrol edilir)
J3_KLASOR_GRUP = "Klasor (tum icerik ayni kategori)"
KURU_BUTCE_DK = 270


def _eslesir(desenler, metin):
    m = metin.lower()
    return next((d for d in desenler if re.search(d, m)), None)


def gercek_receipt_var(tam):
    return any(not TEST_AD.match(x) for x in GERCEK_RECEIPT.findall(tam))


def koruma_nedeni(is_, yol, ad, mime=""):
    """None = korunmuyor; aksi halde neden. yol = ust yol ('' = Drive koku), ad = oge adi."""
    tam = (yol + "/" + ad) if yol else ad
    parca = tam.split("/")
    if "." in parca:
        return "kisisel_nokta"
    if "/" in ad:
        return "adda_bolu"
    if yol == "" and is_ in ("J1", "J3"):
        return "drive_koku"
    if yol == "OFIS" or tam == "OFIS":
        return "ofis_koku"
    if gercek_receipt_var(tam):
        return "gercek_receipt"
    d = _eslesir(KORUMA_HER_IS, tam)
    if d:
        return "koruma:" + d
    if is_ != "J2" and _eslesir(KORUMA_SIPARIS, tam):
        return "siparis_deseni"
    if _eslesir(KORUMA_YEDEK, tam) and not (is_ == "J5" and re.search(r"pod_print_yedek_", tam.lower())):
        return "yedek_deseni"
    if is_ not in ("J2", "J5") and _eslesir(KORUMA_RAPOR, tam):
        return "rapor_deseni"
    if mime == SCRIPT and is_ != "J4":
        return "apps_script"
    return None


class _Atla(Exception):
    pass


class _Hata(Exception):
    pass


# ---- Drive istemcisi: tek HTTP noktasi, yazim kapilari burada ----
class Drive:
    def __init__(self, token_komut):
        self.komut, self.tok = token_komut, None
        self.kilit = threading.Lock()
        self.istek_say = 0

    def token(self, eski=None):
        """eski = 401 alan token. Yalniz mevcut token hala o ise yenilenir (eszamanli 401'de tek yenileme)."""
        with self.kilit:
            if self.tok and (eski is None or self.tok != eski):
                return self.tok
            for i in range(5):
                out = subprocess.run(["bash", "-c", self.komut], capture_output=True, text=True, timeout=180)
                tok = out.stdout.strip()
                if out.returncode == 0 and tok and tok != "null" and (eski is None or tok != eski):
                    print("::add-mask::" + tok, flush=True)
                    self.tok = tok
                    return tok
                time.sleep(30)  # rclone tokeni yalniz suresi dolunca yeniler
            raise SystemExit("HATA: Drive token alinamadi/yenilenemedi")

    @staticmethod
    def kapi(yontem, yol, params, govde):
        p = set(params or {})
        if yontem == "GET":
            return
        if "emptyTrash" in yol or yontem not in ("PATCH", "POST"):
            raise SystemExit(f"HATA: {yontem} yasak (kalici silme yok)")
        if yontem == "PATCH":
            if not re.fullmatch(r"/files/[A-Za-z0-9_-]+", yol):
                raise SystemExit("HATA: PATCH yolu")
            if govde == {"trashed": True} and p <= {"fields"}:
                return
            if govde == {} and p == {"addParents", "removeParents", "fields"}:
                return
            raise SystemExit("HATA: PATCH yalniz trashed=true ya da ebeveyn degisimi")
        if yontem == "POST":
            if yol != "/files" or set(govde or {}) != {"name", "mimeType", "parents"} or govde["mimeType"] != KLASOR:
                raise SystemExit("HATA: POST yalniz klasor olusturma")

    def istek(self, yontem, yol, params=None, govde=None, deneme=6):
        self.kapi(yontem, yol, params, govde)
        url = API + yol + ("?" + urllib.parse.urlencode(params) if params else "")
        veri = json.dumps(govde).encode() if govde is not None else None
        for i in range(deneme):
            self.istek_say += 1
            kullanilan = self.token()
            req = urllib.request.Request(url, data=veri, method=yontem, headers={
                "Authorization": "Bearer " + kullanilan, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    b = r.read()
                    return json.loads(b) if b else {}
            except urllib.error.HTTPError as e:
                ic = e.read() or b""
                if e.code == 401 and i < deneme - 1:
                    self.token(eski=kullanilan)
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
        return self.istek("GET", f"/files/{fid}", {"fields": ALAN})

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

    def cope(self, fid):
        return self.istek("PATCH", f"/files/{fid}", {"fields": "id,trashed"}, {"trashed": True})

    def tasi(self, fid, ekle, cikar):
        return self.istek("PATCH", f"/files/{fid}", {"addParents": ekle, "removeParents": cikar, "fields": "id,parents"}, {})

    def klasor_kur(self, ad, ust):
        return self.istek("POST", "/files", {"fields": "id"}, {"name": ad, "mimeType": KLASOR, "parents": [ust]})["id"]


# ---- envanter ----
BASLIK = ["id", "title", "path", "mimeType", "size", "created", "modified", "category", "reason", "group", "isFolder",
          "fileCount"]


def envanter_oku(klasor):
    dosyalar = sorted(glob.glob(os.path.join(klasor, "ENVANTER_PARCA_*.csv")))
    if len(dosyalar) != PARCA_BEKLENEN:
        raise SystemExit(f"HATA: envanter parcasi {len(dosyalar)} (beklenen {PARCA_BEKLENEN}) (DUR)")
    inv = {}
    for f in dosyalar:
        with open(f, encoding="utf-8-sig", newline="") as h:
            r = csv.DictReader(h)
            if r.fieldnames != BASLIK:
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


def uygun_satir(is_, s, j3_grup):
    k, yol = s["category"], tam_yol(s)
    if is_ == "J1":
        return k == "TRASH"
    if is_ == "J3":
        if k != "SERDAR_QUESTION" or not yol.startswith("ASTROLOVE/TEMP/") or j3_grup is None:
            return False
        if not (s["group"] == j3_grup or (s["klasor"] and s["group"] == J3_KLASOR_GRUP)):
            return False
        return not any(p.upper().startswith("POD_PRINT") for p in yol.split("/"))
    if is_ == "J5":
        return k == "ARCHIVE" and not (yol + "/").startswith("ASTROLOVE/ARCHIVE/")
    return False


def _tarih(t):
    if not t:
        return None
    d = datetime.fromisoformat(t.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise SystemExit("HATA: saat dilimsiz tarih (DUR)")
    return d


# ---- canli yol ----
class Yollar:
    def __init__(self, drive):
        self.d, self.on, self.ata_on = drive, {}, {}
        self.kok = drive.get("root")["id"]

    def ust_yol(self, oge):
        p = oge.get("parents") or []
        if len(p) != 1:
            return None
        return self.yol(p[0])

    def yol(self, fid):
        if fid == self.kok:
            return ""
        if fid not in self.on:
            o = self.d.get(fid)
            p = o.get("parents") or []
            if len(p) != 1:
                self.on[fid], self.ata_on[fid] = None, None
            else:
                u = self.yol(p[0])
                pa = set() if p[0] == self.kok else self.ata_on.get(p[0])
                self.on[fid] = None if u is None else ((u + "/" + o["name"]) if u else o["name"])
                self.ata_on[fid] = None if (u is None or pa is None) else (pa | {p[0]})
        return self.on[fid]

    def atalar(self, fid):
        """fid'in ata kimlikleri (kok dahil); belirsizse None."""
        if fid == self.kok:
            return set()
        self.yol(fid)
        return self.ata_on.get(fid)


# ---- kod taramasi (tum dallar) ----
class Kod:
    def __init__(self, depo, refler, eksik_izin=()):
        """eksik_izin: depoda bilerek bulunmayan commit'ler (orn. silinmis musteri dali ucu); is akisinda gerekcesiyle verilir."""
        self.depo, self.refler = depo, list(refler)
        sabit = self.sabit_refler()
        eksik = [c for c in sabit if subprocess.run(["git", "-C", depo, "cat-file", "-e", c + "^{commit}"],
                                                     capture_output=True).returncode != 0]
        self.eksik_izinli = [c for c in eksik if any(i.startswith(c) or c.startswith(i) for i in eksik_izin if len(i) >= 7)]
        eksik = [c for c in eksik if c not in self.eksik_izinli]
        sabit = [c for c in sabit if c not in self.eksik_izinli]
        if eksik:
            raise SystemExit(f"HATA: is akislarinda sabit {len(eksik)} ref depoda yok (DUR)")
        self.refler += [c for c in sabit if c not in self.refler]

    def sabit_refler(self):
        """is akisi dosyalarinda sha/ref/commit satirlarindaki sabit commit kimlikleri (HEAD)."""
        r = subprocess.run(["git", "-C", self.depo, "grep", "-h", "-i", "-E", r"(sha|ref|commit)", "HEAD", "--",
                            ".github/workflows"], capture_output=True, text=True)
        if r.returncode not in (0, 1):
            raise SystemExit("HATA: git grep")
        out = set()
        for satir in r.stdout.split("\n"):
            satir = satir.split(":", 1)[1] if satir.startswith("HEAD:") else satir
            for m in re.findall(r"(?<![0-9A-Za-z_])([0-9a-f]{7,40})(?![0-9A-Za-z_])", satir):
                if re.search(r"[0-9]", m) and re.search(r"[a-f]", m):
                    out.add(m)
        return sorted(out)

    def _grep(self, args):
        r = subprocess.run(["git", "-C", self.depo, "grep", "-I", "-h", "-o"] + args + self.refler + ["--"],
                           capture_output=True, text=True)
        if r.returncode not in (0, 1):
            raise SystemExit("HATA: git grep")
        cikti = set()
        for s in r.stdout.split("\n"):
            if not s:
                continue
            for ref in self.refler:  # tree-ish grep "ref:" oneki koyabilir
                if s.startswith(ref + ":"):
                    s = s[len(ref) + 1:]
                    break
            cikti.add(s)
        return cikti

    def idler(self):
        """koddaki 25+ karakterli tum kimlik benzeri tokenler (Drive dosya 33, Docs/Sheets 44 karakter)."""
        return self._grep(["-E", "[A-Za-z0-9_-]{25,}"])

    def onekler(self):
        return {m for s in self._grep(["-E", KOD_ONEK_E]) for m in KOD_ONEK.findall(s)}

    def adlar(self, adlar, yol_dosya):
        adlar = sorted(a for a in adlar if a)
        if not adlar:
            return set()
        with open(yol_dosya, "w") as h:
            h.write("\n".join(adlar) + "\n")
        try:
            return self._grep(["-F", "-f", yol_dosya])
        finally:
            os.unlink(yol_dosya)


class Kuru:
    def __init__(self, drive, inv, kod, simdi, j3_grup):
        self.d, self.inv, self.kod = drive, inv, kod
        self.simdi, self.j3 = simdi, j3_grup
        self.esik14 = simdi - timedelta(days=GUN14)
        self.yollar = Yollar(drive)
        self.birim, self.atla = [], []
        self.t_bas = time.time()
        self.kod_id = kod.idler()
        self.kod_uzun = [t for t in self.kod_id if len(t) > 33]   # bitisik yazilmis kimlikler icin alt dizgi aramasi
        self.muaf_say = 0
        self.kismi = False
        self.kod_onek = {o for o in kod.onekler() if len(o) >= 4}
        print(f"kod taramasi: ref {len(kod.refler)}, Drive kimligi adayi {len(self.kod_id)}, dinamik onek {len(self.kod_onek)}")

    def muaf(self, *idler):
        """genel kap klasorlerinin kimligi kimlik kapisindan cikar (tam token ve onu iceren bitisik tokenler)."""
        once = len(self.kod_id)
        self.kod_id = {t for t in self.kod_id if not any(i in t for i in idler)}
        self.kod_uzun = [t for t in self.kod_uzun if not any(i in t for i in idler)]
        self.muaf_say = once - len(self.kod_id)
        print(f"kimlik muafiyeti: {len(idler)} genel klasor, cikarilan token {self.muaf_say}")

    def oge_neden(self, is_, o, ust):
        if o.get("trashed"):
            return "zaten_copte"
        if len(o.get("parents") or []) != 1:
            return "ebeveyn_sayisi"
        if o.get("shared") or o.get("ownedByMe") is False:
            return "paylasimli_ya_da_baskasinin"
        if o["id"] in self.kod_id or any(o["id"] in t for t in self.kod_uzun):
            return "kodda_kimlik"
        for alan, neden in (("modifiedTime", "son14_degisti"), ("viewedByMeTime", "son14_acildi"),
                            ("createdTime", "son14_olusturuldu")):
            t = _tarih(o.get(alan))
            if t and t >= self.esik14:
                return neden
        n = koruma_nedeni(is_, ust, o["name"], o.get("mimeType", ""))
        if n:
            return n
        if is_ in ("J1", "J3", "J5"):
            s = self.inv.get(o["id"])
            if s is None:
                return "envanterde_yok"
            if not uygun_satir(is_, s, self.j3):
                return "kategori_farkli"
            if not s["modified"]:
                return "envanter_tarihi_yok"
            m = _tarih(o.get("modifiedTime"))
            if not m or abs((m - _tarih(s["modified"])).total_seconds()) > 1:
                return "envanterden_sonra_degisti"
            if tam_yol(s) != ((ust + "/" + o["name"]) if ust else o["name"]):
                return "yol_farkli"
        return None

    def agac(self, kok):
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

    def bol(self, is_, kok, ust_yol):
        try:
            ogeler, cocuk = self.agac(kok)
        except urllib.error.HTTPError as e:
            self.atla.append(dict(is_=is_, id=kok["id"], yol=(ust_yol + "/" + kok["name"]).lstrip("/"),
                                  neden=f"agac_okunamadi_{e.code}", dosya=0, bayt=0))
            return
        neden, temiz, boy, say = {}, {}, {}, {}
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

        def altlar(fid):
            out, k = [], [fid]
            while k:
                x = k.pop()
                out.append(x)
                k += cocuk[x]
            return out

        def topla(fid):
            o = ogeler[fid]
            assert ust[fid] == ust_yol or ust[fid].startswith((ust_yol + "/") if ust_yol else "")
            yol = (ust[fid] + "/" + o["name"]) if ust[fid] else o["name"]
            if temiz[fid]:
                cap = o.get("capabilities") or {}
                if not cap.get("canMoveItemWithinDrive" if is_ == "J5" else "canTrash", False):
                    self.atla.append(dict(is_=is_, id=fid, yol=yol, neden="drive_izin_yok", dosya=say[fid], bayt=boy[fid]))
                    return
                alt = sorted(iz(ogeler[x]) for x in altlar(fid))
                self.birim.append(dict(is_=is_, id=fid, yol=yol, ust_id=o["parents"][0], klasor=o["mimeType"] == KLASOR,
                                       dosya=say[fid], bayt=boy[fid], modifiedTime=o.get("modifiedTime"), ad=o["name"],
                                       ata_adlar=[p for p in ust[fid].split("/") if p and p not in GENEL_ATA],
                                       alt_ozet=hashlib.sha256("\n".join(alt).encode()).hexdigest(), alt_say=len(alt)))
                return
            if neden[fid] is not None or o["mimeType"] != KLASOR:
                self.atla.append(dict(is_=is_, id=fid, yol=yol, neden=neden[fid] or "?", dosya=say[fid], bayt=boy[fid]))
                return
            for c in cocuk[fid]:
                topla(c)

        topla(kok["id"])

    def kokler(self, is_):
        uyg = {i: s for i, s in self.inv.items() if uygun_satir(is_, s, self.j3)}
        klasor_yol = {tam_yol(s) for s in uyg.values() if s["klasor"]}
        return [s for s in uyg.values() if s["path"] not in klasor_yol]

    def kok_kontrol(self, o, ust):
        """ata zincirinde koddaki kimlik var mi."""
        at = self.yollar.atalar(o["parents"][0]) if o.get("parents") else None
        if at is None:
            return "ebeveyn_belirsiz"
        zincir = at | {o["parents"][0]}
        if zincir & self.kod_id or any(z in t for z in zincir for t in self.kod_uzun):
            return "atasi_kodda_kimlik"
        return None

    def is_env(self, is_):
        kok = self.kokler(is_)
        print(f"{is_}: envanter kok birim {len(kok)}")
        t0 = time.time()
        for n, s in enumerate(kok, 1):
            if (time.time() - self.t_bas) / 60 > KURU_BUTCE_DK:
                for r in kok[n - 1:]:
                    self.atla.append(dict(is_=is_, id=r["id"], yol=tam_yol(r), neden="kuru_sure_doldu", dosya=0,
                                          bayt=r["boyut"]))
                self.kismi = True
                print(f"  {is_}: kuru sure butcesi ({KURU_BUTCE_DK} dk) doldu; kalan {len(kok) - n + 1} kok atlandi")
                break
            try:
                o = self.d.get(s["id"])
                u = self.yollar.ust_yol(o)
            except urllib.error.HTTPError as e:
                self.atla.append(dict(is_=is_, id=s["id"], yol=tam_yol(s), neden=f"okunamadi_{e.code}", dosya=0, bayt=0))
                continue
            k = "ebeveyn_belirsiz" if u is None else self.kok_kontrol(o, u)
            if k:
                self.atla.append(dict(is_=is_, id=s["id"], yol=tam_yol(s), neden=k, dosya=0, bayt=s["boyut"]))
                continue
            self.bol(is_, o, u)
            if n % 50 == 0 or n == len(kok):
                g = time.time() - t0
                print(f"  {is_} {n}/{len(kok)} ({100 * n // len(kok)}%) gecen {g / 60:.1f} dk, kalan ~{g / n * (len(kok) - n) / 60:.1f} dk")

    def is_test(self):
        aday = self.d.liste(f"name contains '900000000' and mimeType = '{KLASOR}' and trashed = false")
        print(f"J2: '900000000' onekli klasor {len(aday)}, tam test adi {sum(1 for o in aday if TEST_AD.match(o['name']))}")
        secilen = []
        for o in aday:
            if not TEST_AD.match(o["name"]):
                continue
            try:
                u = self.yollar.ust_yol(o)
            except urllib.error.HTTPError as e:
                self.atla.append(dict(is_="J2", id=o["id"], yol=o["name"], neden=f"okunamadi_{e.code}", dosya=0, bayt=0))
                continue
            if u is None:
                continue
            ilk = u.split("/")
            if not (ilk[0].upper().startswith("SIPARIS")
                    or (ilk[0] == "ASTROLOVE" and len(ilk) > 1 and (ilk[1] == "TEMP" or ilk[1].upper().startswith("SIPARIS")))):
                continue
            if any(TEST_AD.match(p) for p in ilk):
                continue
            k = self.kok_kontrol(o, u)
            if k:
                self.atla.append(dict(is_="J2", id=o["id"], yol=u + "/" + o["name"], neden=k, dosya=0, bayt=0))
                continue
            secilen.append((o, u))
        print(f"J2: secilen test klasoru {len(secilen)}")
        for o, u in secilen:
            self.bol("J2", o, u)

    def is_script(self):
        aday = self.d.liste(f"mimeType = '{SCRIPT}' and 'root' in parents and trashed = false")
        aday = [o for o in aday if o["name"].strip().lower() in ("adsız proje", "adsiz proje")]
        print(f"J4: kokte adsiz Apps Script {len(aday)} (tetikleyici gorulemedigi icin tasinmaz)")
        for o in aday:
            m = _tarih(o.get("modifiedTime"))
            self.atla.append(dict(is_="J4", id=o["id"], yol=o["name"], dosya=1, bayt=0,
                                  neden="tetikleyici_dogrulanamadi" + ("_son14_degisti" if m and m >= self.esik14 else "")))

    def kod_kontrol(self, gecici):
        """birim adi ya da ata adlari (>= 6 karakter, ASTROLOVE/TEMP/OFIS haric) taranan herhangi bir ref'te geciyorsa ya da
        koddaki dinamik onekle basliyorsa ATLANIR (tum isler; J3 istisnasi Serdar 25 Kas onayiyla kaldirildi).
        J2'de yalniz birimin kendi adi bakilir (ata klasorleri siparis hattinin yazdigi klasorler)."""
        adlar = set()
        for b in self.birim:
            adlar |= {a for a in [b["ad"]] + b["ata_adlar"] if len(a) >= 6}
        bulunan = self.kod.adlar(adlar, gecici)
        kalan, atilan = [], 0
        for b in self.birim:
            bak = [b["ad"]] if b["is_"] == "J2" else [b["ad"]] + b["ata_adlar"]
            gecen = [a for a in bak if a in bulunan]
            onek = any(a.startswith(o) for a in bak for o in self.kod_onek)
            if len(b["ad"]) < 6 and b["is_"] != "J2":
                self.atla.append(dict(b, neden="ad_kisa_kontrol_edilemez")); atilan += 1
            elif onek:
                self.atla.append(dict(b, neden="kodda_dinamik_onek")); atilan += 1
            elif gecen:
                self.atla.append(dict(b, neden="kodda_geciyor")); atilan += 1
            else:
                kalan.append(b)
        self.birim = kalan
        return atilan


def ic_ice_temizle(birim, atla):
    """ayni oge ya da ic ice birimler: icteki birim atlanir (kume tabanli). Isler arasi da gecerli."""
    kalan, gor, kalan_yol = [], set(), set()
    for b in sorted(birim, key=lambda x: x["yol"].count("/")):
        if b["id"] in gor:
            atla.append(dict(b, neden="cift_birim"))
            continue
        parca = b["yol"].split("/")
        if any("/".join(parca[:i]) in kalan_yol for i in range(1, len(parca) + 1)):
            atla.append(dict(b, neden="ic_ice_birim"))
            continue
        gor.add(b["id"])
        kalan_yol.add(b["yol"])
        kalan.append(b)
    return kalan


def arsiv_hedef(yol):
    """J5 hedef ust yolu: ASTROLOVE/... -> ASTROLOVE/ARCHIVE/...; kok ogesi -> ASTROLOVE/ARCHIVE/_KOK/..."""
    ust = yol.rsplit("/", 1)[0] if "/" in yol else ""
    if ust == "ASTROLOVE" or ust.startswith("ASTROLOVE/"):
        ic = ust[len("ASTROLOVE"):].lstrip("/")
        return "ASTROLOVE/ARCHIVE" + ("/" + ic if ic else "")
    return "ASTROLOVE/ARCHIVE/_KOK" + ("/" + ust if ust else "")


def gb(b):
    return f"{b / 1e9:.2f}".replace(".", ",")


SINIRLAR = ["viewedByMeTime yalniz kullanicinin acmasiyla degisir; API/rclone okumalari 'son 14 gunde acildi' kuralina yansimaz.",
            "Kod taramasi dal uclarini ve is akislarindaki sabit commit'leri kapsar; eski commit'te gecip silinmis adlar ve "
            "tamamen degiskenden kurulan yollar (orn. TEMP/${ON}_...) gorulemez.",
            "Repo degiskenleri (vars) ve secret'lardaki kimlik/ref'ler, betik icinde sabitlenmis SHA'lar ve os.path.join / "
            ".format ile kurulan yollar taranmaz.",
            "Kapsamdan bilerek dusenler: OFIS kokundeki Chrome kilit dosyalari (OFIS koku korunur), J1'deki KUPA_SIPARIS_TEST_* "
            "(siparis deseni), J4 Adsiz proje (tetikleyici dogrulanamadi), Drive kokundeki J1 dosyalari."]


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
    # J3 grup olcumu (TEMP altindaki SERDAR_QUESTION; POD_PRINT haric) -> yalniz md'ye ad, loga sira no
    grup = {}
    for s in inv.values():
        if s["category"] == "SERDAR_QUESTION" and tam_yol(s).startswith("ASTROLOVE/TEMP/"):
            pp = any(p.upper().startswith("POD_PRINT") for p in tam_yol(s).split("/"))
            g = grup.setdefault(s["group"], [0, 0, 0, 0, 0])
            if s["klasor"]:
                g[4] += 1
            elif pp:
                g[2] += 1; g[3] += s["boyut"]
            else:
                g[0] += 1; g[1] += s["boyut"]
    for i, (g, v) in enumerate(sorted(grup.items())):
        print(f"  SQ-TEMP grup #{i}: POD_PRINT disi {v[0]} dosya {gb(v[1])} GB | POD_PRINT {v[2]} dosya {gb(v[3])} GB | klasor {v[4]}")
    if a.j3_grup is not None and a.j3_grup not in grup:
        raise SystemExit("HATA: --j3-grup envanterde yok (DUR)")
    d = Drive(os.environ["DRIVE_TOKEN_KOMUT"])
    simdi = datetime.now(timezone.utc)
    refler = [r for r in a.refler.split(",") if r] if a.refler else ["HEAD"]
    k = Kuru(d, inv, Kod(a.depo, refler, [x for x in a.eksik_ref_izin.split(",") if x]), simdi, a.j3_grup)
    if k.kod.eksik_izinli:
        print(f"depoda olmayan izinli sabit ref: {len(k.kod.eksik_izinli)}")
    # kok dogrulamasi: envanterdeki OFIS satiri canli Drive kokundeki OFIS ile ayni olmali
    ofis = [s for s in inv.values() if s["title"] == "OFIS" and s["path"] == "" and s["klasor"]]
    canli = d.liste(f"name = 'OFIS' and mimeType = '{KLASOR}' and 'root' in parents and trashed = false", "id")
    if len(ofis) != 1 or len(canli) != 1 or ofis[0]["id"] != canli[0]["id"]:
        raise SystemExit("HATA: envanter koku ile canli Drive koku eslesmiyor (DUR)")
    # TEMP/OFIS kimlik muafiyeti (Serdar 25 Kas onayi): kodda rclone koku olarak gecen bu iki genel klasorun kimligi
    # kimlik kapisindan cikarilir; altlarindaki yollar adla taranmaya devam eder (GENEL_ATA ile ayni ilke)
    ast = d.liste(f"name = 'ASTROLOVE' and mimeType = '{KLASOR}' and 'root' in parents and trashed = false", "id")
    temp = [] if len(ast) != 1 else d.liste(f"name = 'TEMP' and mimeType = '{KLASOR}' and '{ast[0]['id']}' in parents "
                                             f"and trashed = false", "id")
    if len(temp) != 1:
        raise SystemExit("HATA: ASTROLOVE/TEMP tekil bulunamadi (DUR)")
    k.muaf(temp[0]["id"], canli[0]["id"])
    isler = a.isler.split(",")
    for is_ in isler:
        if is_ in ("J1", "J5") or (is_ == "J3" and a.j3_grup is not None):
            k.is_env(is_)
        elif is_ == "J3":
            print("J3: grup verilmedi; yalniz olculdu, birim yok")
        elif is_ == "J2":
            k.is_test()
        elif is_ == "J4":
            k.is_script()
    kodda = k.kod_kontrol(os.path.join(a.cikti, "_adlar.txt"))
    k.birim = ic_ice_temizle(k.birim, k.atla)
    for b in k.birim:
        if b["is_"] == "J5":
            b["hedef"] = arsiv_hedef(b["yol"])
            n = koruma_nedeni("J5", b["hedef"], b["ad"])
            if n and n != "ofis_koku":
                k.atla.append(dict(b, neden="hedef_korumali:" + n))
                b["sil"] = True
    k.birim = [b for b in k.birim if not b.get("sil")]
    os.makedirs(a.cikti, exist_ok=True)
    plan = dict(surum=2, kismi=k.kismi, kuru_t=simdi.isoformat(), esik14=k.esik14.isoformat(), j3_grup=a.j3_grup, isler=isler,
                birim=k.birim, atla=k.atla)
    pj = os.path.join(a.cikti, "plan.json")
    with open(pj, "w") as h:
        json.dump(plan, h, ensure_ascii=False, indent=0)
    sha = hashlib.sha256(open(pj, "rb").read()).hexdigest()
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
          f"14 gun esigi: {k.esik14.isoformat()[:10]}. Drive istek: {d.istek_say}. Plan sha256: {sha}",
          "", "PLAN KISMI: kuru sure butcesi doldu, kalan kokler atlandi (kuru_sure_doldu)." if k.kismi else "Plan tam.", "",
          "| Is | Tasinacak birim | Dosya | GB | Atlanan dosya | Atlanan GB |", "|---|---|---|---|---|---|"]
    for is_, v in sorted(ozet["is"].items()):
        md.append(f"| {is_} | {v[0]} | {v[1]} | {gb(v[2])} | {v[3]} | {gb(v[4])} |")
    md += ["", "Atlama nedenleri:", ""]
    for n, v in sorted(ozet["neden"].items(), key=lambda x: -x[1][0]):
        md.append(f"- {n}: {v[0]} dosya, {gb(v[1])} GB, {v[2]} kayit")
    md += ["", "SERDAR_QUESTION, ASTROLOVE/TEMP altindaki dosyalar, gruba gore (J3 icin --j3-grup secimi):", "",
           "| # | grup | POD_PRINT disi dosya | GB | POD_PRINT dosya | GB | klasor satiri |", "|---|---|---|---|---|---|---|"]
    for i, (g, v) in enumerate(sorted(grup.items())):
        md.append(f"| {i} | {g} | {v[0]} | {gb(v[1])} | {v[2]} | {gb(v[3])} | {v[4]} |")
    md += ["", f"Kodda gecen, dinamik onekli ya da kisa adli (atlanan) birim: {kodda}. Taranan ref: {len(k.kod.refler)}.",
           "", "Bilinen sinirlar:", ""] + [f"- {x}" for x in SINIRLAR]
    md += ["", "J4: Apps Script tetikleyicisi Drive API ile gorulemez; kural geregi TASINMADI.",
           f"Liste: OFIS/KURU_DRIVE_TRASH_{ts}.csv"]
    with open(os.path.join(a.cikti, f"KURU_DRIVE_TRASH_{ts}.md"), "w") as h:
        h.write("\n".join(md) + "\n")
    for is_, v in sorted(ozet["is"].items()):
        print(f"{is_}: tasinacak birim {v[0]}, dosya {v[1]}, {gb(v[2])} GB | atlanan dosya {v[3]}, {gb(v[4])} GB")
    print(f"Drive istek: {d.istek_say}")
    print(f"plan sha256: {sha}")
    return 0


# ---- uygula ----
def _kacis(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def klasor_yolu(d, hedef, onbellek):
    """ASTROLOVE/ARCHIVE mevcut olmali (kurulmaz); altindaki eksik seviyeler kurulur; her seviyede tam 1 klasor."""
    if hedef in onbellek:
        return onbellek[hedef]
    ust_ad, _, ad = hedef.rpartition("/")
    if hedef in ("ASTROLOVE", "ASTROLOVE/ARCHIVE"):
        ust = "root" if hedef == "ASTROLOVE" else klasor_yolu(d, "ASTROLOVE", onbellek)
        f = [] if ust is None else d.liste(f"name = '{_kacis(ad)}' and mimeType = '{KLASOR}' and '{ust}' in parents "
                                           f"and trashed = false", "id")
        onbellek[hedef] = f[0]["id"] if len(f) == 1 else None
        return onbellek[hedef]
    if not hedef.startswith("ASTROLOVE/ARCHIVE/"):
        raise SystemExit("HATA: hedef ARCHIVE disinda")
    ust = klasor_yolu(d, ust_ad, onbellek)
    if ust is None:
        onbellek[hedef] = None
        return None
    f = d.liste(f"name = '{_kacis(ad)}' and mimeType = '{KLASOR}' and '{ust}' in parents and trashed = false", "id")
    if len(f) > 1:
        onbellek[hedef] = None
    elif f:
        onbellek[hedef] = f[0]["id"]
    else:
        onbellek[hedef] = d.klasor_kur(ad, ust)
    return onbellek[hedef]


def iz(o):
    """alt agac ozeti icin oge izi: kimlik + degisim + acilma zamani."""
    return f"{o['id']}|{o.get('modifiedTime') or ''}|{o.get('viewedByMeTime') or ''}"


def alt_agac_iz(d, kok):
    izler, k = [iz(kok)], [kok["id"]] if kok["mimeType"] == KLASOR else []
    while k:
        x = k.pop()
        for c in d.cocuklar(x):
            izler.append(iz(c))
            if c["mimeType"] == KLASOR:
                k.append(c["id"])
    return izler


def uygula(a):
    if a.onay != "TASI":
        raise SystemExit("HATA: uygula icin --onay TASI")
    ham = open(a.plan, "rb").read()
    if not re.fullmatch(r"[0-9a-f]{64}", a.plan_sha or "") or hashlib.sha256(ham).hexdigest() != a.plan_sha:
        raise SystemExit("HATA: plan sha256 eslesmiyor (DUR)")
    plan = json.loads(ham)
    if plan.get("surum") != 2:
        raise SystemExit("HATA: plan surumu")
    kuru_t = datetime.fromisoformat(plan["kuru_t"])
    if datetime.now(timezone.utc) - kuru_t > timedelta(hours=48):
        raise SystemExit("HATA: plan 48 saatten eski (DUR; yeni kuru kosu)")
    d = Drive(os.environ["DRIVE_TOKEN_KOMUT"])
    yukle = os.environ.get("YUKLE_KOMUT")
    yollar = Yollar(d)
    istenen = a.isler.split(",")
    birim = [b for b in plan["birim"] if b["is_"] in istenen]
    esik14 = datetime.now(timezone.utc) - timedelta(days=GUN14)
    t0 = time.time()
    kayit = os.path.join(a.cikti, "uygula.jsonl")
    hedef_on = {}
    partiler = [birim[i:i + PARTI] for i in range(0, len(birim), PARTI)]
    toplam_hata, sonuc, sure_doldu = 0, [], False
    print(f"uygula: plan birim {len(birim)}, parti {len(partiler)}")
    with open(kayit, "a") as kh:
        for pn, parti in enumerate(partiler, 1):
            ok = atl = hata = 0
            pdosya = pbayt = 0
            yollar = Yollar(d)  # yol onbellegi her partide tazelenir
            for b in parti:
                if (time.time() - t0) / 60 > SURE_BUTCE_DK:
                    sure_doldu = True
                    break
                r = dict(t=datetime.now(timezone.utc).isoformat(), is_=b["is_"], id=b["id"], yol=b["yol"], dosya=b["dosya"],
                         bayt=b["bayt"], eski_ust=b["ust_id"])
                try:
                    o = d.get(b["id"])
                    if o.get("trashed"):
                        raise _Atla("zaten_copte")
                    if (o.get("parents") or []) != [b["ust_id"]]:
                        raise _Atla("ebeveyn_degisti")
                    if o.get("modifiedTime") != b["modifiedTime"]:
                        raise _Atla("kuru_sonrasi_degisti")
                    ust = yollar.yol(b["ust_id"])
                    if ust is None or ((ust + "/" + o["name"]) if ust else o["name"]) != b["yol"]:
                        raise _Atla("yol_degisti")
                    n = koruma_nedeni(b["is_"], ust, o["name"], o.get("mimeType", ""))
                    if n:
                        raise _Atla("koruma:" + n)
                    for alan in ("modifiedTime", "viewedByMeTime", "createdTime"):
                        t = _tarih(o.get(alan))
                        if t and t >= esik14:
                            raise _Atla("son14_" + alan)
                    ids = sorted(alt_agac_iz(d, o))
                    if len(ids) != b["alt_say"] or hashlib.sha256("\n".join(ids).encode()).hexdigest() != b["alt_ozet"]:
                        raise _Atla("alt_agac_degisti")
                    if b["is_"] == "J5":
                        hid = klasor_yolu(d, b["hedef"], hedef_on)
                        if hid is None:
                            raise _Atla("hedef_klasor_belirsiz")
                        ayni = d.liste(f"name = '{_kacis(o['name'])}' and '{hid}' in parents and trashed = false", "id")
                        if ayni:
                            raise _Atla("hedefte_ayni_ad")
                        d.tasi(b["id"], hid, b["ust_id"])
                        g = d.get(b["id"])
                        if (g.get("parents") or []) != [hid]:
                            raise _Hata("geri_okuma_ebeveyn")
                        r.update(durum="ARSIVE_TASINDI", yeni_ust=hid)
                    else:
                        d.cope(b["id"])
                        g = d.get(b["id"])
                        if g.get("trashed") is not True:
                            raise _Hata("geri_okuma_trashed")
                        r.update(durum="COPE_TASINDI")
                    ok += 1; pdosya += b["dosya"]; pbayt += b["bayt"]
                except _Atla as e:
                    r.update(durum="ATLANDI", neden=str(e)); atl += 1
                except SystemExit:
                    raise
                except Exception as e:  # noqa: BLE001  (HTTP, ag, beklenmeyen: hepsi HATA -> DUR)
                    r.update(durum="HATA", neden=str(getattr(e, "code", "")) or type(e).__name__); hata += 1
                sonuc.append(r)
                kh.write(json.dumps(r, ensure_ascii=False) + "\n")
                kh.flush()
            toplam_hata += hata
            gecen = time.time() - t0
            print(f"parti {pn}/{len(partiler)} ({100 * pn // len(partiler)}%): tasinan {ok} ({pdosya} dosya, {gb(pbayt)} GB), "
                  f"atlanan {atl}, hata {hata} | gecen {gecen / 60:.1f} dk, kalan ~{gecen / pn * (len(partiler) - pn) / 60:.1f} dk",
                  flush=True)
            if yukle:
                subprocess.run(["bash", "-c", yukle, kayit], timeout=300)
            if hata:
                print("DUR: partide hata var; kalan partiler islenmedi")
                break
            if sure_doldu:
                print(f"DUR: sure butcesi ({SURE_BUTCE_DK} dk) doldu; ayni planla yeniden uygula kaldigi yerden devam eder")
                break
    say = {}
    for r in sonuc:
        v = say.setdefault((r["is_"], r["durum"]), [0, 0, 0])
        v[0] += 1; v[1] += r["dosya"]; v[2] += r["bayt"]
    for (is_, durum), v in sorted(say.items()):
        print(f"{is_} {durum}: birim {v[0]}, dosya {v[1]}, {gb(v[2])} GB")
    islenmeyen = len(birim) - len(sonuc)
    print(f"islenmeyen birim {islenmeyen}; Drive istek {d.istek_say}")
    rapor(a, plan, sonuc, islenmeyen, say)
    if yukle:
        subprocess.run(["bash", "-c", yukle, kayit], timeout=300)
    basari = toplam_hata == 0 and islenmeyen == 0
    print("SONUC:", "PASS" if basari else "FAIL")
    return 0 if basari else 1


def rapor(a, plan, sonuc, islenmeyen, say):
    ts = a.ts
    md = [f"# Drive temizligi sonuc raporu ({ts})", "",
          f"Plan: kuru kosu {plan['kuru_t'][:16]} UTC, isler {','.join(plan['isler'])}. Kalici silme yapilmadi."
          + (" PLAN KISMIYDI (kuru sure butcesi doldu)." if plan.get("kismi") else ""), "",
          "| Is | Durum | Birim | Dosya | GB |", "|---|---|---|---|---|"]
    for (is_, durum), v in sorted(say.items()):
        md.append(f"| {is_} | {durum} | {v[0]} | {v[1]} | {gb(v[2])} |")
    md += ["", f"Islenmeyen birim: {islenmeyen}. Kuru kosuda atlananlar: {len(plan['atla'])} kayit (KURU_DRIVE_TRASH_*.csv).", "",
           "Hatalar:", ""]
    md += [f"- {r['is_']} {r['yol']}: {r.get('neden')}" for r in sonuc if r["durum"] == "HATA"] or ["- yok"]
    md += ["", "Geri alma:", "",
           "- Cop kutusu (J1-J3): Drive > Cop kutusu > oge > Geri yukle (30 gun). Klasoru geri yuklemek icindekileri de geri getirir.",
           "  Kimlik listesi: OFIS/DRIVE_TEMIZLIK_UYGULA_" + ts + ".jsonl (durum COPE_TASINDI).",
           "- ARCHIVE (J5): kayittaki eski_ust klasorune geri tasinir (Drive'da Tasi ya da API addParents=eski_ust, "
           "removeParents=yeni_ust).", "",
           "Girdisiz kalan is akisi: yok (adi ya da atasi herhangi bir dalda gecen klasor tasinmadi).", "",
           "Bilinen sinirlar:", ""] + [f"- {x}" for x in SINIRLAR]
    with open(os.path.join(a.cikti, f"RAPOR_DRIVE_TRASH_{ts}.md"), "w") as h:
        h.write("\n".join(md) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kuru", "uygula"], required=True)
    ap.add_argument("--isler", default="J1,J2,J3,J4,J5")
    ap.add_argument("--j3-grup", default=None)
    ap.add_argument("--envanter")
    ap.add_argument("--depo")
    ap.add_argument("--refler", default="")
    ap.add_argument("--eksik-ref-izin", default="")
    ap.add_argument("--plan")
    ap.add_argument("--plan-sha", default="")
    ap.add_argument("--onay", default="")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ts", default=datetime.now(timezone(timedelta(hours=3))).strftime("%Y%m%d_%H%M%S"))
    a = ap.parse_args()
    if not a.isler or not set(a.isler.split(",")) <= {"J1", "J2", "J3", "J4", "J5"}:
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
