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
import atexit
import hashlib
import html
import posixpath
import urllib.parse
import json
import os
import re
import sys
import threading
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


# ------------------------------------------------------------------ kota siniri
# Serdar 15 ve 24 Eki (kesin): Etsy API kota siniri 10, tek deger. Kosu/ilan baslangic esigi ve her istekten once sert taban
# ayni: kalan < 10 ise DUR. 23 Eki esikleri (genel 481/430, pod-audit 2068, router 400, siparis 415, ihtiyac kapisi 430) ve
# config/etsy_kota_esik.json KALDIRILDI. Serdar acikca soylemeden degistirilmez; yeni esik onerilmez.
KOTA_SINIRI = 10


def kota_esigi(rol=None, dosya=None):
    """-> (esik, sert_taban) = (KOTA_SINIRI, KOTA_SINIRI), her rol icin (genel, pod-audit, siparis, router). rol ve dosya
    geriye uyumluluk icin kabul edilir, etkisi yoktur."""
    return KOTA_SINIRI, KOTA_SINIRI


# ------------------------------------------------------------------ RU yazim kapisi
# Serdar 23 Eki madde 4: poster RU yalniz yeni sablon kurucusundan (ru_poster.kur + ru_poster.izin_ver) yazilir. Tum betikler
# Etsy._call'dan gectigi icin kapi burada: (1) her RU ceviri yaziminda kagit/tedarikci/Art'siz marka ifadesi -> yazim yok;
# (2) 78 poster ilaninda (data/pod/pod78_ids.csv) aciklama ru_poster'in onayladigi metinle birebir degilse -> yazim yok.
RU_YASAK = re.compile(r"Hahnem|Ханем|Photo\s*Rag|Prodigi|хлоп(?:к|ок)|cotton|музе|museum|ISO\s*9706|жикле|gicl|"
                      r"\d{3}\s*(?:г/м|g/m|gsm)|\bOBA\b|bright\s*white|12[\s-]*colou?r|\d+\s*(?:years|лет)|AstroLove(?!Art)", re.I)
RU_POSTER_IZIN = {}   # listing_id -> sha256(aciklama); yalniz ru_poster.izin_ver() doldurur
POSTER_IDS_YOL = Path(__file__).resolve().parents[2] / "data" / "pod" / "pod78_ids.csv"
_RU_YOL = re.compile(r"/listings/0*(\d+)/translations/ru(?:[-_][a-z]{2})?$")   # kanonik (kucuk harf) yol uzerinde


def ozet(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def poster_idler():
    try:
        return {x.split(",")[0].strip() for x in POSTER_IDS_YOL.read_text(encoding="utf-8").splitlines()[1:] if x.strip()}
    except OSError as e:   # liste okunamazsa kapi kapali kalir (poster mi bilinemez)
        raise SystemExit(f"DUR: RU yazim kapisi: poster listesi okunamadi ({e})")


def _kanonik_yol(path):
    """Serdar 23 Eki 2c (inceleme 2. tur): coklu yuzde kodlama, sorgu/parca/;param, //, ./ ve ../, buyuk harf ile kapi atlanamaz."""
    p = str(path or "")
    for _ in range(5):
        q = urllib.parse.unquote(p)
        if q == p:
            break
        p = q
    p = re.split(r"[?#;]", p.replace("\\", "/"))[0]
    return posixpath.normpath("/" + p).lower()


def _govde(g):
    """Istek govdesini sozluge cevirir; cevrilemezse None (RU yaziminda kapi kapali kalir)."""
    if g is None:
        return {}
    if isinstance(g, dict):
        return g
    if isinstance(g, (bytes, str)):
        g = g.decode("utf-8", "replace") if isinstance(g, bytes) else g
        return {k: ",".join(v) for k, v in urllib.parse.parse_qs(g, keep_blank_values=True).items()}
    try:
        return dict(g)
    except (TypeError, ValueError):
        return None


def ru_yazim_kapisi(method, path, data=None, json_body=None):
    """RU ceviri yazimindan once (GET/HEAD/OPTIONS disi her yontem, .../translations/ru). Uygun degilse SystemExit; istek gonderilmez."""
    m = _RU_YOL.search(_kanonik_yol(path))
    if str(method or "").upper() in ("GET", "HEAD", "OPTIONS") or not m:
        return
    lid = str(int(m.group(1)))
    g1, g2 = _govde(data), _govde(json_body)
    if g1 is None or g2 is None:
        raise SystemExit(f"DUR: RU yazim kapisi: ilan {lid} istek govdesi okunamadi; yazim yok")
    g = {**g2, **g1}
    if g1 and g2 and any(g1.get(k) != g2.get(k) for k in set(g1) & set(g2)):
        raise SystemExit(f"DUR: RU yazim kapisi: ilan {lid} data ve json govdesi celisiyor; yazim yok")
    metin = " ".join(str(v or "") for v in g.values())
    yasak = sorted({x.group(0) for x in RU_YASAK.finditer(metin)})
    if yasak:
        raise SystemExit(f"DUR: RU yazim kapisi: ilan {lid} RU metninde yasak ifade {yasak}; yazim yok")
    if lid in {str(int(x)) for x in poster_idler()} and RU_POSTER_IZIN.get(lid) != ozet(g.get("description")):
        raise SystemExit(f"DUR: RU yazim kapisi: poster ilan {lid} RU aciklamasi ru_poster sablon kurucusundan gelmiyor; yazim yok")



# AI BEYAN KAPISI (Merkez 31 Eki, Serdar "ok"): Etsy kurali "Sellers must disclose within their listing description if an item is created
# with the use of AI." Aciklama (description) yazan HER istek (updateListing PATCH/PUT, createDraftListing POST, ceviri PUT/POST) gondermeden
# once SON metinde beyan cumlesi aranir; tum betikler Etsy._call'dan gectigi icin kapi tek yerde (kopya kod yok). description anahtari
# olmayan kismi yazim (yalniz baslik / etiket / fiyat) aciklamayi degistirmez, kapiya takilmaz. Beyan yoksa: o ilan YAZILMAZ (istek
# gonderilmez, BeyanYok = SystemExit, mesajda ilan id), ilan BEYAN_HATA listesine girer ve surec cikisinda kosu FAIL olur (betik
# SystemExit'i ilan bazinda yakalayip devam etse bile; cikis kodu 1, "::error::" satirinda ilan id'leri).
AI_BEYAN = {"en": "We use AI tools to help create the artwork",
            "ru": "При создании изображений мы используем инструменты искусственного интеллекта"}   # beyan_marka_yaz.RU_BEYAN ile ayni
_BEYAN_ILAN = re.compile(r"/shops/[^/]+/listings(?:/0*(\d+))?$")                    # updateListing / createDraftListing (kanonik yol)
_BEYAN_CEVIRI = re.compile(r"/listings/0*(\d+)/translations/([a-z]{2,3})(?:[-_][a-z0-9]{2,4})?$")   # rus / zh-hant da yakalanir (tanimsiz dil FAIL)
BEYAN_HATA = []          # [(ilan, dil, neden)] bu surecte beyan kapisina takilan yazimlar


class BeyanYok(SystemExit):
    pass


def _beyan_norm(t):
    return re.sub(r"\s+", " ", html.unescape(str(t or ""))).strip()


def beyan_var(metin, dil):
    """Son aciklama metninde o dilin beyan cumlesi var mi (bosluk / satir sonu ve HTML varligi normalize)."""
    c = AI_BEYAN.get(dil)
    return bool(c) and _beyan_norm(c) in _beyan_norm(metin)


def _beyan_aciklamalar(g, alan="description"):
    """Govdedeki TUM description degerleri (inceleme 31 Eki madde 7: tekrarli anahtar, tuple listesi, JSON dizesi, None). None = okunamadi."""
    if g is None:
        return []
    if isinstance(g, (bytes, str)):
        t = g.decode("utf-8", "replace") if isinstance(g, bytes) else g
        if t.lstrip().startswith("{"):
            try:
                return _beyan_aciklamalar(json.loads(t), alan)
            except ValueError:
                return None
        return list(urllib.parse.parse_qs(t, keep_blank_values=True).get(alan) or [])
    if isinstance(g, dict):
        v = g.get(alan)
        if v is None:
            return []                                    # yok ya da None (requests None alani gondermez)
        return [str(x) for x in v] if isinstance(v, (list, tuple)) else [v]
    if isinstance(g, (list, tuple)):
        try:
            return [v for k, v in g if k == alan and v is not None]
        except (TypeError, ValueError):
            return None
    return None                                          # generator / dosya nesnesi: okunamadi, guvenli taraf FAIL


# KARARLAR (Serdar 1 Kas, Denetim 20261101A):
# 2  GERI ALMA: beyansiz eski metne donus yalniz yedekteki metne BIREBIR (sha) donuste; cagiran geri_alma_izni(ilan, metin, yedek_sha)
#    ile izin kaydeder (sha uyusmazsa DUR). Baska metin yine durur.
# 4  RU: aciklamaya DOKUNMAYAN ceviri yazimi (gonderilen RU aciklama = canli RU aciklama; yalniz baslik / etiket degisir) eski RU
#    aciklamasi beyansizsa da gecer; ilan RU_BEYANSIZ listesine girer (listing_id, burc cifti, tarih; cikista Drive
#    TEMP/RU_BEYANSIZ/). Aciklamaya dokunan RU yaziminda kural aynen.
# 1  YAYINA ALMA: Etsy.yayin_beyan_kontrol (Etsy._call icinde): aciklamasiz updateListing (state=active / taslak guncelleme) once
#    canli ilani HER SEFER taze okur (+1 GET); canli TASLAK ya da active olmayan ilana state=active ise canli aciklamada beyan zorunlu.
GERI_IZIN = {}           # (ilan, dil) -> {sha}: geri_alma_izni ile kaydedilen, yedekteki metnin sha'si
GERI_ISTISNA = []        # [(ilan, dil, sha12)] bu surecte geri alma istisnasiyla gecen yazimlar
RU_BEYANSIZ = []         # [dict(listing_id, cift, tarih, neden)]


def geri_alma_izni(ilan, metin, yedek_sha, dil="en"):
    """Geri almada eski metne donus izni: metin, yedek alinirken kaydedilen sha ile birebir ayni olmali; degilse DUR (yazim yok)."""
    ilan = str(int(ilan)); s_ = ozet(metin)
    if not yedek_sha or s_ != str(yedek_sha):
        raise SystemExit(f"DUR: geri alma izni: ilan {ilan} {dil.upper()} metni yedekteki ile birebir degil "
                         f"(sha {s_[:12]} != {str(yedek_sha or '-')[:12]}); yazim yok")
    GERI_IZIN.setdefault((ilan, dil), set()).add(s_)
    return s_


def beyan_on_kontrol(en_yeni=None, ru_yeni=None, ru_canli=None):
    """Karar 3 (Serdar 1 Kas): EN + RU yazan ilanda yazimdan ONCE iki yeni metin birlikte denetlenir. None = o dil yazilmayacak.
    RU: beyanli olmali ya da canli RU aciklamasiyla ayni (karar 4: aciklamaya dokunulmuyor). Donus: neden listesi (bos = yazilabilir).
    Bos degilse cagiran HICBIR metni yazmaz; ilan ATLANDI + neden (FAIL degil)."""
    neden = []
    if en_yeni is not None and not beyan_var(en_yeni, "en"):
        neden.append(f"EN yeni aciklamada AI beyani yok (\"{AI_BEYAN['en']}\")")
    if ru_yeni is not None and not beyan_var(ru_yeni, "ru") and not (ru_canli is not None and _beyan_norm(ru_canli) == _beyan_norm(ru_yeni)):
        neden.append(f"RU yeni aciklamada AI beyani yok (\"{AI_BEYAN['ru']}\")")
    return neden


_BURC = ("Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo", "Libra", "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo")
_CIFT_TABLO = None


def cift_bul(ilan, baslik=None):
    """Burc cifti: data/pod pod78_ids / yd78_ids; yoksa baslikta gecen burclar (alfabetik, CLAUDE.md cift anahtari); yoksa '?'."""
    global _CIFT_TABLO
    if _CIFT_TABLO is None:
        _CIFT_TABLO = {}
        for ad in ("pod78_ids.csv", "yd78_ids.csv"):
            try:
                for x in (POSTER_IDS_YOL.parent / ad).read_text(encoding="utf-8").splitlines()[1:]:
                    c = x.split(",")
                    if len(c) > 1 and c[0].strip():
                        _CIFT_TABLO[str(int(c[0]))] = c[1].strip()
            except (OSError, ValueError):
                pass
    if str(ilan) in _CIFT_TABLO:
        return _CIFT_TABLO[str(ilan)]
    t = str(baslik or "")
    bul = {b: len(re.findall(rf"\b{b}\b", t, re.I)) for b in _BURC}
    bul = {b: n for b, n in bul.items() if n}
    if len(bul) == 2:
        return "_".join(x.upper() for x in sorted(bul))
    if len(bul) == 1 and max(bul.values()) >= 2:          # "Leo and Leo"
        b = next(iter(bul)).upper(); return f"{b}_{b}"
    return "?"                                            # tek gecen / 3+ burc: uydurulmaz (inceleme madde 12)


def ai_beyan_kapisi(method, path, data=None, json_body=None, params=None, canli_ceviri=None, baslik=None):  # noqa: C901
    """Aciklama yazimindan once (GET/HEAD/OPTIONS disi). description yoksa gecer; varsa son metinde dilin beyan cumlesi zorunlu.
    canli_ceviri: (yalniz Etsy._call) ceviri yolunda canli aciklamayi donduren cagri (karar 4); baslik: RU_BEYANSIZ cifti icin."""
    if str(method or "").upper() in ("GET", "HEAD", "OPTIONS"):
        return
    yol = _kanonik_yol(path)
    m_c, m_i = _BEYAN_CEVIRI.search(yol), _BEYAN_ILAN.search(yol)
    if not (m_c or m_i):
        return
    ilan = str(int(m_c.group(1))) if m_c else (str(int(m_i.group(1))) if m_i.group(1) else "yeni ilan (createDraftListing)")
    dil = m_c.group(2) if m_c else "en"
    sorgu = str(path or "").split("?", 1)[1].split("#")[0] if "?" in str(path or "") else ""   # yol sorgu dizesi de gonderilir
    govdeler = [_beyan_aciklamalar(x) for x in (data, json_body, params, sorgu)]
    if any(g is None for g in govdeler):
        neden = "istek govdesi okunamadi"
    else:
        aciklamalar = [x for g in govdeler for x in g]
        if not aciklamalar:
            return                                                       # kismi yazim: aciklama degismiyor
        if len({_beyan_norm(x) for x in aciklamalar}) > 1:
            neden = "data / json / params / sorgu aciklamalari celisiyor (ya da description tekrarli)"
        elif dil not in AI_BEYAN:
            neden = f"'{dil}' dili icin beyan cumlesi tanimli degil"
        elif beyan_var(aciklamalar[0], dil):
            return
        else:
            a0 = aciklamalar[0]
            if all(x == a0 for x in aciklamalar) and ozet(a0) in GERI_IZIN.get((ilan, dil), ()):
                GERI_ISTISNA.append((ilan, dil, ozet(a0)[:12]))                       # karar 2: yedekteki metne birebir donus
                log(f"AI beyan kapisi: ilan {ilan} {dil.upper()} geri alma istisnasi (yedek sha {ozet(a0)[:12]}, beyansiz eski metin)")
                return
            if m_c and canli_ceviri is not None:                                        # karar 4: aciklamaya dokunmayan ceviri yazimi
                canli = canli_ceviri()
                if canli is not None and _beyan_norm(canli) == _beyan_norm(a0):
                    _ru_beyansiz_ekle(dict(listing_id=ilan, dil=dil, cift=cift_bul(ilan, baslik), tarih=time.strftime("%Y-%m-%d", time.gmtime()),
                                           neden="eski ceviri aciklamasi beyansiz; aciklama degismedi (yalniz baslik / etiket)"))
                    log(f"AI beyan kapisi: ilan {ilan} {dil.upper()} aciklama degismiyor, eski metin beyansiz -> yazim izinli, RU_BEYANSIZ listesine eklendi")
                    return
            neden = f"aciklamada AI beyani yok ({dil.upper()}: \"{AI_BEYAN[dil]}\")"
    BEYAN_HATA.append((ilan, dil, neden))
    raise BeyanYok(f"HATA: AI beyan kapisi: ilan {ilan} {dil.upper()} {neden}; yazim yok")


_RU_YAZILAN = set()


def _ru_beyansiz_yol():
    return Path(os.environ.get("RU_BEYANSIZ_CSV") or "RU_BEYANSIZ.csv")


def _ru_beyansiz_ekle(x):
    """Satir ANINDA yerel CSV'ye eklenir (inceleme madde 12: timeout / kill'de kaybolmasin); Drive'a cikista. Ilan / dil basina tek satir."""
    RU_BEYANSIZ.append(x)
    if (x["listing_id"], x["dil"]) in _RU_YAZILAN:
        return
    _RU_YAZILAN.add((x["listing_id"], x["dil"]))
    import csv
    try:
        yol = _ru_beyansiz_yol(); yeni = not yol.exists()
        with open(yol, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["listing_id", "cift", "dil", "tarih", "kosu", "neden"])
            if yeni:
                w.writeheader()
            w.writerow(dict(x, kosu=os.environ.get("GITHUB_RUN_ID", "yerel")))
            fh.flush()
    except OSError as e:
        print(f"::warning::RU_BEYANSIZ yerel CSV yazilamadi ({type(e).__name__})", file=sys.stderr, flush=True)


def _ru_beyansiz_yaz():
    """Cikista: RU_BEYANSIZ yerel CSV'si (RU_BEYANSIZ_CSV, varsayilan RU_BEYANSIZ.csv) Drive TEMP/RU_BEYANSIZ/RU_BEYANSIZ_<kosu>_<pid>.csv'ye
    (rclone varsa; RU_BEYANSIZ_DRIVE=0 kapatir). Sir yok: yalniz ilan no, cift, tarih."""
    if not RU_BEYANSIZ:
        return
    import shutil
    import subprocess
    yol = _ru_beyansiz_yol()
    try:
        print(f"::warning::RU_BEYANSIZ: {len({x['listing_id'] for x in RU_BEYANSIZ})} ilan (eski RU aciklamasi beyansiz, aciklamaya dokunulmadi): "
              + ", ".join(sorted({f"{x['listing_id']} {x['cift']}" for x in RU_BEYANSIZ})[:20]), file=sys.stderr, flush=True)
        if os.environ.get("RU_BEYANSIZ_DRIVE", "1") != "0" and shutil.which("rclone"):
            hedef = f"gdrive:ASTROLOVE/TEMP/RU_BEYANSIZ/RU_BEYANSIZ_{os.environ.get('GITHUB_RUN_ID', 'yerel')}_{os.getpid()}.csv"
            p_ = subprocess.run(["rclone", "copyto", str(yol), hedef, "-q"], capture_output=True, text=True, timeout=120)
            if p_.returncode:
                print("::warning::RU_BEYANSIZ Drive'a yazilamadi (yerel CSV ve bu log satiri kaynak)", file=sys.stderr, flush=True)
    except Exception as e:   # noqa: BLE001
        print(f"::warning::RU_BEYANSIZ yazilamadi ({type(e).__name__})", file=sys.stderr, flush=True)


def _beyan_cikis():
    if BEYAN_HATA:
        try:
            sys.stdout.flush()
        except Exception:   # noqa: BLE001
            pass
        print("::error::AI beyan kapisi: aciklamasi beyansiz oldugu icin YAZILMAYAN ilanlar: "
              + "; ".join(f"{i} {d.upper()} ({n})" for i, d, n in BEYAN_HATA), file=sys.stderr, flush=True)
        try:
            import logging
            logging.shutdown()
        except Exception:   # noqa: BLE001
            pass
        os._exit(1)        # betik SystemExit'i yakalayip 0 ile bitse de kosu FAIL (token aninda yazilir, atexit kullanan baska kod yok)


atexit.register(_beyan_cikis)
atexit.register(_ru_beyansiz_yaz)     # LIFO: _beyan_cikis'in os._exit'inden ONCE calisir

# ------------------------------------------------------------------ api
class Etsy:
    """Is parcacigi guvenli (Serdar 29 Eki hiz: galeri yukleyici --isci N ayni istemciyi paylasir): tempo TUM iscilere ortak tek
    kilitli saat (istek baslangiclari en az pace sn arayla = en fazla 4 istek/sn), calls / remaining kilitli, token yenileme kilitli ve
    TEK sefer (401 alan isci, kullandigi token hala gecerli token ise yeniler; baska isci yenilemisse yalniz yeni tokenla tekrar dener).
    yerel_calls: bu is parcacigindan giden istek sayisi (ilan basina istek)."""
    def __init__(self, store):
        self.store = store
        self.calls = 0
        self.remaining = None
        self._kilit = threading.Lock()          # sayac / kalan / tempo saati
        self._yenile_kilit = threading.Lock()   # token yenileme (refresh token doner; iki yenileme token bozar)
        self._son = 0.0
        self._sira = 0                          # istek sira no (kalan kota: yalniz en yeni baslayan istegin basligi kabul)
        self._kabul = 0
        self._yanit = 0                         # alinan yanit sayisi (kota basligi denetimi; paralelde calls ilk yanittan once artar)
        self._yerel = threading.local()
        self.esik, self.sert_taban = kota_esigi()
        self._kapi_bakildi = False
        if self.sert_taban is not None:
            log(f"KOTA SINIRI {self.sert_taban} (kosu/ilan baslangici ve her istek; Serdar 15 ve 24 Eki)")
        self.pace = 0.25  # sn; 5 QPS sinirinin altinda kalir
        self.verbose_quota = False  # True: her istekten sonra x-remaining-today loglanir (C gorevi, 5 Eyl 2026)
        self._ilan_bel = {}          # ilan -> (t, state, description, title): bu kosunun okudugu / yazdigi ilanlar (karar 1)
        self._ceviri_bel = {}        # (ilan, dil) -> (t, description)
        self._bel_kilit = threading.Lock()
        self.yayin_okuma = 0         # karar 1 icin yapilan ek GET sayisi

    def _bel_hazir(self):
        """__new__ ile kurulan (testler) nesnede de bellek alanlari olsun."""
        if "_bel_kilit" not in self.__dict__:
            self.__dict__.update(_ilan_bel={}, _ceviri_bel={}, _bel_kilit=threading.Lock(), yayin_okuma=0)
        if "_kilit" not in self.__dict__:
            self._kilit = threading.Lock()

    def _belle(self, method, path, j):
        """Basarili GET / PATCH / PUT yanitindaki ilan ve ceviri alanlarini bellege yazar (karar 1 / 4 icin; hata sessiz)."""
        try:
            self._bel_hazir()
            if str(method).upper() not in ("GET", "PATCH", "PUT") or not isinstance(j, dict):
                return
            yol, t = _kanonik_yol(path), time.monotonic()
            m = _BEYAN_CEVIRI.search(yol)
            if m:
                if "description" in j:
                    with self._bel_kilit:
                        self._ceviri_bel[(str(int(m.group(1))), m.group(2))] = (t, j.get("description"))
                return
            satirlar = j["results"] if isinstance(j.get("results"), list) else [j]
            with self._bel_kilit:
                for L in satirlar:
                    if isinstance(L, dict) and L.get("listing_id") and "state" in L and "description" in L:
                        self._ilan_bel[str(int(L["listing_id"]))] = (t, L.get("state"), L.get("description"), L.get("title"))
        except Exception:   # noqa: BLE001
            pass

    def canli_ilan(self, ilan):
        """(state, description, title): HER cagrida 1 taze GET (karar 1 "canli aciklamayi 1 kez oku"; inceleme 1 Kas madde 6: bellek
        dogrudan requests / panel degisikliginde bayatlar). yayin_okuma += 1."""
        ilan = str(int(ilan))
        self._bel_hazir()
        with self._kilit:
            self.yayin_okuma += 1
        self._call("GET", f"/listings/{ilan}")
        with self._bel_kilit:
            b = self._ilan_bel.get(ilan)
        if not b:
            raise SystemExit(f"DUR: yayin beyan kontrolu: ilan {ilan} canli okunamadi (state / description yok); yazim yok")
        return b[1:]

    def _baslik(self, path):
        m = _BEYAN_CEVIRI.search(_kanonik_yol(path))
        self._bel_hazir()
        b = self._ilan_bel.get(str(int(m.group(1)))) if m else None
        return b[3] if b else None

    def _canli_ceviri(self, path):
        """Karar 4: ceviri yolunun canli aciklamasi; ayni yola 1 taze GET (ceviri yoksa None)."""
        m = _BEYAN_CEVIRI.search(_kanonik_yol(path))
        if not m:
            return None
        self._bel_hazir()                                  # taze okuma (bellek kullanilmaz; inceleme 1 Kas madde 6)
        with self._kilit:
            self.yayin_okuma += 1
        j = self._call("GET", str(path).split("?", 1)[0], ok404=True)
        return (j or {}).get("description") if isinstance(j, dict) else None

    def yayin_beyan_kontrol(self, method, path, data=None, json_body=None, params=None):
        """Karar 1: aciklama gondermeyen updateListing (PATCH / PUT /shops/x/listings/<id>) taslagi yayina alabilir (CLAUDE.md 7 Eyl)
        ya da state=active ile yayina alir: canli ilan active degilse canli aciklamada EN beyan zorunlu. Aciklamali yazimi
        ai_beyan_kapisi denetler."""
        if str(method or "").upper() not in ("PATCH", "PUT"):
            return
        m = _BEYAN_ILAN.search(_kanonik_yol(path))
        if not (m and m.group(1)):
            return
        sorgu = str(path or "").split("?", 1)[1].split("#")[0] if "?" in str(path or "") else ""
        g = [_beyan_aciklamalar(x) for x in (data, json_body, params, sorgu)]
        if any(x is None for x in g) or any(g):
            return
        st = [str(x).lower() for x in sum((_beyan_aciklamalar(x, "state") or [] for x in (data, json_body, params, sorgu)), [])]
        if st and all(x != "active" for x in st):
            return                                        # acikca inactive / draft: yayina almaz
        ilan = str(int(m.group(1)))
        state, desc, _ = self.canli_ilan(ilan)
        # yayina alan yazim: canli TASLAK (updateListing taslagi yayina alir, CLAUDE.md 7 Eyl) ya da active olmayan ilana state=active.
        # inactive / sold_out / expired ilanda state'siz kismi yazim yayina almaz -> denetlenmez (karar yalniz taslak; inceleme madde 6).
        # Geri alma izni (karar 2) burada GECERSIZ: geri donus yazimina izin verir, yayina almaya degil (inceleme madde 5).
        if state == "active" or not (state == "draft" or "active" in st) or beyan_var(desc, "en"):
            return
        neden = f"yayina alma / taslak guncelleme: canli ilan {state}, canli aciklamada AI beyani yok (EN: \"{AI_BEYAN['en']}\")"
        BEYAN_HATA.append((ilan, "en", neden))
        raise BeyanYok(f"HATA: AI beyan kapisi: ilan {ilan} EN {neden}; yazim yok")

    def kota_kapisi(self, ne="is"):
        """Ise / ilana baslamadan cagrilir: kalan < esik ise SystemExit (kosu kirmizi, GitHub e-postasi). Esik pasifse etkisiz."""
        if self.esik is not None and self.remaining is not None and int(self.remaining) < self.esik:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < {self.esik} ({ne} baslamadi)")

    def _istek_oncesi(self):
        """Ilk yanittan sonra kosu kapisi bir kez; sert taban (KOTA_SINIRI) HER istekten once.
        SystemExit'i yakalayip devam eden betiklerde de sonraki her istek yine durur (payin altina inilmez)."""
        if self.sert_taban is None:
            return
        if self.remaining is None:
            if self._yanit:
                raise SystemExit("DUR: kota esigi aktif ama x-remaining-today basligi okunamadi")
            return
        with self._kilit:
            ilk, self._kapi_bakildi = not self._kapi_bakildi, True
        if ilk:
            self.kota_kapisi("kosu")
        if int(self.remaining) < self.sert_taban:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < {self.sert_taban}")

    def _headers(self, token=None):
        headers = {"x-api-key": self.store.api_key_header}
        tok = token or self.store.access_token
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return headers

    @property
    def yerel_calls(self):
        return getattr(self._yerel, "n", 0)

    def _bekle(self):
        """Ortak tempo: istek sayaci + bu istegin baslama zamani kilit altinda ayrilir, uyku kilit disinda. -> istek sira no.
        Token suresi dolmak uzereyse (10 dk) istekten ONCE tek isci yeniler (29 Eki inceleme: kosu ortasinda 401, yazim yarida)."""
        self._erken_yenile()
        with self._kilit:
            self.calls += 1
            self._sira += 1; sira = self._sira
            self._yerel.n = getattr(self._yerel, "n", 0) + 1
            simdi = time.monotonic()
            t = max(simdi, self._son + self.pace)
            self._son = t
        if t > simdi:
            time.sleep(t - simdi)
        return sira

    def _erken_yenile(self):
        nr = getattr(self.store, "needs_refresh", None)
        if nr is None:
            return
        try:
            if not nr(600):
                return
        except Exception:   # noqa: BLE001 token yasi okunamazsa 401 yolu yine yeniler
            return
        with self._yenile_kilit:
            if nr(600):     # baska isci kilit beklerken yenilediyse tekrar yok
                self.store.refresh()

    def _kalan_yaz(self, rem, sira=None):
        """x-remaining-today: yalniz bundan once kabul edilenden SONRA baslamis istegin basligi (yavas yukleme yaniti kalani geri
        yukseltmez; 29 Eki inceleme)."""
        with self._kilit:
            self._yanit += 1
            if rem is not None and (sira is None or sira > self._kabul):
                self.remaining = rem
                if sira is not None:
                    self._kabul = sira

    def _yenile(self, kullanilan):
        """401: kullanilan token hala gecerliyse TEK isci yeniler; baskasi yenilediyse yeniden yenileme yok."""
        with self._yenile_kilit:
            if self.store.access_token == kullanilan:
                self.store.refresh()

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

    def delete(self, path, ok404=False):
        """ok404=True: 404 -> None (5xx sonrasi yeniden denemede ilk istek islenmis olabilir; cagiran geri okur)."""
        return self._call("DELETE", path, ok404=ok404)

    def post_json(self, path, body):
        """JSON govdeli POST (ic ice dizi gerektiren uclar). Yazma cagrisi."""
        return self._call("POST", path, json_body=body)

    def put_json(self, path, body):
        """JSON govdeli PUT (updateListingInventory, updateVariationImages). Yazma cagrisi."""
        return self._call("PUT", path, json_body=body)

    def post_file(self, path, files, data=None, tekrar=3):
        """Multipart yukleme (gorsel/dosya). Ilk denemede 400 normal olabilir
        (B37); 3 deneme. tekrar=1 (eski78_gorsel_yukle, Serdar 24 Eki): hata yanitinda yeniden GONDERMEZ (cift yukleme
        riski); cagiran galeriyi okuyup karar verir. 401 token yenilemesi her durumda bir kez yapilir."""
        ai_beyan_kapisi("POST", path, data)   # multipart createDraftListing da kapidan gecer (gorsel / video yolu eslesmez, gecer)
        self._istek_oncesi()
        attempt, yenilendi = 0, False
        while True:   # 401 (istek islenmedi) bir kez, hangi denemede gelirse gelsin: yenile + tekrar (deneme sayilmaz)
            sira = self._bekle()
            for f in files.values():
                try:
                    f[1].seek(0)
                except Exception:
                    pass
            tok = self.store.access_token
            r = requests.post(API + path, files=files, data=data, headers=self._headers(tok), timeout=180)
            rem = r.headers.get("x-remaining-today")
            self._kalan_yaz(rem, sira)
            if self.verbose_quota:
                log(f"      kota {rem} | POST(file) {path} -> {r.status_code}")
            if r.status_code == 401 and not yenilendi:
                yenilendi = True
                self._yenile(tok)
                continue
            if r.status_code in (200, 201):
                return r.json()
            if attempt < tekrar - 1:
                time.sleep(2 * (attempt + 1))
                attempt += 1
                continue
            raise SystemExit(f"HATA: POST(file) {path} -> {r.status_code}: {r.text[:300]}")

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        ru_yazim_kapisi(method, path, data, json_body)
        ai_beyan_kapisi(method, path, data, json_body, params, canli_ceviri=lambda: self._canli_ceviri(path), baslik=self._baslik(path))
        self.yayin_beyan_kontrol(method, path, data, json_body, params)
        self._istek_oncesi()
        attempt, yenilendi = 0, False
        while True:   # en fazla 3 gonderim (5xx / kisa 429); 401 (istek islenmedi) bir kez, hangi denemede gelirse gelsin, sayilmaz
            sira = self._bekle()
            tok = self.store.access_token
            r = requests.request(method, API + path, params=params, data=data, json=json_body,
                                 headers=self._headers(tok), timeout=TIMEOUT)
            rem = r.headers.get("x-remaining-today")
            self._kalan_yaz(rem, sira)
            if self.verbose_quota:
                log(f"      kota {rem} | {method} {path} -> {r.status_code}")
            if r.status_code == 401 and not yenilendi:
                log("401 alindi, token yenilenip tekrar denenecek.")
                yenilendi = True
                self._yenile(tok)
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
                    attempt += 1
                    continue
                raise SystemExit(
                    f"HATA: 429 kota. retry-after={r.headers.get('retry-after')}"
                )
            if r.status_code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                attempt += 1
                continue
            if r.status_code == 204:
                return {}
            if r.status_code not in (200, 201):          # 201: createShopShippingProfileDestination gibi olusturma uclari (6 Eyl)
                raise SystemExit(f"HATA: {method} {path} -> {r.status_code}: {r.text[:300]}")
            j = r.json()
            self._belle(method, path, j)
            return j

