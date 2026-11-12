#!/usr/bin/env python3
"""ETSY SHARED SECRET GECISI (Serdar 12 Kas 2026; plan C1-C12 + Genel Merkez ek sartlari E1-E7). Yalniz
.github/workflows/etsy-secret-gecis.yml icinden, mod basina ayri Serdar onayiyla kosar. Mod ayrintisi: docs/SECRETS.md.

CIKTI KURALI: yalniz sabit metin + EVET / HAYIR / DOLU / BOS / VAR / YOK / HTTP kodu. Sir degeri, parcasi, uzunlugu, ozeti
YAZILMAZ (tek istisna: olc modunda "secret en az 12 karakter: EVET / HAYIR"). Dosyadan okunan alanlar okunur okunmaz
"::add-mask::" ile maskelenir. Her cikti satiri bilinen sir degerlerinden suzulur (suz). Deger komut satiri argumani olmaz.

ETSY ISTEKLERI: yalniz GET /openapi-ping, GET /users/me (OAuth'lu salt okuma) ve TokenStore.refresh (kilit altinda, standart
geri yazim). x-api-key basligini betik, modun sinadigi HEDEF secret'la kendisi kurar (E7); TokenStore'un sectigi degere
birakilmaz. 401'de kendiliginden yenileme YOK. Yanlis secret'la token yenileme DENENMEZ. Her istekten once kota tabani 10.

KANIT UCU (E6): hangi istegin secret'i dogruladigi olculmedi. KANIT_UCU varsayilani AYARSIZ (None); olcumden sonra ayri commit
ve incelemeyle "ping" ya da "oauth" yapilir. Ayarsizken yedek_dogrula, degistir, dogrula, tamam_kontrol, geri_al,
geri_dogrula, temizle, temizle_drive DUR verir. Bu modlar once 5 rastgele secret'la negatif kontrol yapar: biri 200 ya da
401 / 403 disinda kod donerse DUR. OAuth ucunda access token suresi dolmussa DUR (kanitlanmamis secret'la yenileme yok).

KILIT / SIPARIS: kosu olusturuldugu andan itibaren Etsy kilit sirasindadir; siparis-* icin beklenmez (is akisi: --dk 0, hemen DUR).

Kullanim: secret_gecis.py <mod>   (ortam: MOD, ONAY, GITHUB_REF, GITHUB_RUN_ATTEMPT ve moda gore sirlar; bkz. is akisi)"""
import glob
import hmac
import json
import os
import re
import secrets as _rastgele
import socket
import string
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(KOK / "scripts" / "common"))

KANIT_UCU = None                      # None (AYARSIZ) | "ping" | "oauth"; olcum kosusundan sonra ayri commit + inceleme (E6 b)
REPO_AD = "astrolove-ops"
CANLI_AD, YEDEK_AD, YENI_AD = "ETSY_SHARED_SECRET", "ETSY_SHARED_SECRET_YEDEK", "ETSY_SHARED_SECRET_YENI"
DENEME_AD, PROVA_AD, KOD_AD = "ETSY_SECRET_DENEME", "ETSY_SECRET_PROVA", "SIPARIS_KOD_ANAHTARI"
TOKEN_UZAK = "gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json"
UCUNCU_UZAK = "gdrive:ASTROLOVE/ETSY_TOKEN.json"                  # dijital-donusum-uygula.yml:64, :81
YEDEK_KOK = "gdrive:ASTROLOVE/TEMP/SECRET_GECIS_YEDEK"            # bu betigin tarihli token yedekleri
ONCEKI_KOK = "gdrive:ASTROLOVE/TEMP"                              # etsy-yetki.yml:165 ETSY_TOKEN_ONCEKI_*.json (yalniz listelenir)
DEGISKEN = "ETSY_GECIS_KAPATILAN"                                 # kapat modunun kapattigi is akislari (repo degiskeni)
PROVA_WF = "etsy-quota-probe.yml"                                 # prova: kapatma / acma yetkisi bununla olculur
# K3 (Serdar 12 Kas): sir sizdirabilen 18 is akisi; liste Dayanak 1 ile birebir
KAPAT = ("gorsel-denetim", "wp-pdf-probe", "wp-saat80-ornek", "wp-share-mockups", "by-taslak-hazirlik", "etsy-ai-scan",
         "etsy-quota-probe", "etsy-ru-probe", "etsy-state-probe", "ig-ilan-dogrula", "pw-ru-probe", "urun-gorsel-cl", "gorsel02",
         "gorsel19", "seo51", "pin-v6", "dijital-donusum-uygula", "pod-arac-v4")
# mod -> Etsy'ye en cok istek (GET + token yenileme); docs/SECRETS.md'de ayni tablo
MODLAR = {"olc": 15, "yedek": 0, "yedek_dogrula": 6, "prova": 0, "kapat": 0, "ac": 0, "kod_anahtari": 0, "alan_sil": 1, "alan_geri": 0,
          "degistir": 6, "dogrula": 7, "tamam_kapisi": 0, "tamam_kontrol": 9, "geri_al": 6, "geri_dogrula": 6, "temizle": 7,
          "temizle_drive": 6}
KONTROL_BOY = (10, 12, 16, 24, 32)    # negatif kontrol: bu uzunluklarda rastgele harf-rakam secret (gercek degerden turetilmez)
ALFABE = string.ascii_letters + string.digits
KANITLI = ("yedek_dogrula", "degistir", "dogrula", "tamam_kontrol", "geri_al", "geri_dogrula", "temizle", "temizle_drive")
AKTIF = ("queued", "in_progress", "waiting", "pending", "requested")
PING, BEN = "/openapi-ping", "/users/me"
ARALIK_SN = 0.25           # ardisik Etsy istekleri arasi bekleme (emsal etsy_common.py: 5 QPS sinirinin altinda)
PAY_DK = 5                 # tamam_kapisi: canli secret yazimindan sonraki bu kadar dakikada baslayan kosu da "eski" sayilir

SIRLAR = []                 # ciktidan suzulecek degerler
SAYAC = {"etsy": 0, "ok": 0}
KOTA = {"kalan": None, "son": None}
IS = {"dizin": None, "depo": None}


class Dur(Exception):
    """Kapi FAIL: sabit metinli DUR (deger tasimaz)."""


# ------------------------------------------------------------------ cikti
def sir_ekle(*degerler):
    for v in degerler:
        if isinstance(v, str) and len(v) >= 4 and v not in SIRLAR:
            SIRLAR.append(v)


def suz(metin):
    m = str(metin)
    for v in sorted(SIRLAR, key=len, reverse=True):
        m = m.replace(v, "***")
    return m


def yaz(metin):
    print(suz(metin), flush=True)


def maskele(v):
    """Dosyadan okunan deger runner'da kendiliginden maskelenmez: hemen maskele (emsal etsy_common.py:59-62). Cok satirli
    degerde her satir ayri maskelenir (add-mask tek satir alir)."""
    if isinstance(v, str) and v:
        sir_ekle(v)
        for satir in v.splitlines():
            if satir.strip():
                sir_ekle(satir)
                print(f"::add-mask::{satir}", flush=True)


def esit(a, b):
    return bool(a) and bool(b) and hmac.compare_digest(str(a).encode(), str(b).encode())


def en(b):
    return "EVET" if b else "HAYIR"


def ortam(ad, zorunlu=True):
    v = os.environ.get(ad) or ""
    if zorunlu and not v:
        raise Dur(f"ortamda {ad} yok")
    sir_ekle(v)
    return v


# ------------------------------------------------------------------ kapi
def onay_sozcugu(mod):
    return "SERDAR_SECRET_" + mod.upper()


def kapi(mod=None):
    """Ortak kapi: ref main, GITHUB_RUN_ATTEMPT 1, mod listede, moda ozel onay sozcugu."""
    mod = mod if mod is not None else (os.environ.get("MOD") or "")
    if mod not in MODLAR:
        raise Dur("mod listede degil")
    if (os.environ.get("GITHUB_REF") or "") != "refs/heads/main":
        raise Dur("ref refs/heads/main degil")
    if (os.environ.get("GITHUB_RUN_ATTEMPT") or "") != "1":
        raise Dur("GITHUB_RUN_ATTEMPT 1 degil (yeniden kosu yok; yeni kosu ayri onay)")
    onay = os.environ.get("ONAY") or ""
    if not onay or not hmac.compare_digest(onay, onay_sozcugu(mod)):
        raise Dur(f"onay sozcugu yok ya da baska modun sozcugu (beklenen: {onay_sozcugu(mod)})")
    return mod


# ------------------------------------------------------------------ GitHub
def gh(yontem, yol, token, govde=None):
    """-> (HTTP kodu, json). Hata govdesi okunmaz / yazilmaz."""
    url = f"https://api.github.com/repos/{os.environ.get('GITHUB_REPOSITORY', 'caliserdar-maker/' + REPO_AD)}{yol}"
    veri = json.dumps(govde).encode() if govde is not None else None
    req = urllib.request.Request(url, data=veri, method=yontem, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ham = r.read()
            return r.status, (json.loads(ham) if ham else {})
    except urllib.error.HTTPError as e:
        return e.code, {}


def gs():
    import gh_secrets
    return gh_secrets


def meta(ad, token):
    """-> updated_at ya da None (secret yok ya da alan donmedi). Varlik icin var_mi kullanilir."""
    m = gs().secret_meta(REPO_AD, ad, token)
    return (m or {}).get("updated_at") if m else None


def var_mi(ad, token):
    return gs().secret_meta(REPO_AD, ad, token) is not None


def secret_yaz(ad, deger, token):
    """Yazar ve updated_at'in yazimdan once olmadigini dogrular."""
    t0 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    once = meta(ad, token)
    gs().set_secret(REPO_AD, ad, deger, token)
    u = meta(ad, token)
    # yeni kayit, ya da updated_at ilerledi, ya da yazim anindan sonra (runner / GitHub saat kaymasina dayanikli)
    if not u or not (once is None or u > once or u >= t0):
        raise Dur(f"{ad} yazildi ama updated_at dogrulanamadi")
    yaz(f"{ad} yazildi: updated_at kapisi PASS")


def wf_durum(dosya, token):
    kod, j = gh("GET", f"/actions/workflows/{dosya}", token)
    if kod != 200:
        raise Dur(f"is akisi durumu okunamadi: {dosya} (HTTP {kod})")
    return j.get("state") or ""


def wf_ayarla(dosya, etkin, token):
    kod, _ = gh("PUT", f"/actions/workflows/{dosya}/{'enable' if etkin else 'disable'}", token)
    return kod == 204


def degisken_oku(token):
    kod, j = gh("GET", f"/actions/variables/{DEGISKEN}", token)
    if kod == 404:
        return []
    if kod != 200:
        raise Dur(f"repo degiskeni okunamadi (HTTP {kod})")
    return [x for x in str(j.get("value") or "").split(",") if x in KAPAT]


def degisken_yaz(adlar, token):
    gs().set_variable(REPO_AD, DEGISKEN, ",".join(a for a in KAPAT if a in adlar) or "-", token)


def aktif_kosular(token):
    """Aktif durumdaki tum kosular (durum basina tek GET; emsal scripts/common/siparis_bekle.py). Tek sayfaya sigmiyorsa DUR."""
    out, kendi = {}, str(os.environ.get("GITHUB_RUN_ID") or "")
    for st in AKTIF:
        kod, j = gh("GET", f"/actions/runs?status={st}&per_page=100", token)
        if kod != 200:
            raise Dur(f"kosu listesi okunamadi (HTTP {kod})")
        kosular = j.get("workflow_runs") or []
        if int(j.get("total_count") or 0) > len(kosular):
            raise Dur("aktif kosu listesi tek sayfaya sigmiyor (100'den fazla): kapi guvenle okunamaz")
        for k in kosular:
            if str(k.get("id")) != kendi:
                out[str(k.get("id"))] = k
    return list(out.values())


def wf_yolu(kosu):
    return str(kosu.get("path") or "").split("@", 1)[0]


def etsy_kumesi():
    """Kilit kumesi + secrets.ETSY_* ya da ETSY_TOKEN.json iceren her yml (emsal etsy-kota.yml:55-58)."""
    import kilit_bekle
    kume = set(kilit_bekle.kilit_kumesi(str(KOK), "etsy"))
    for f in glob.glob(str(KOK / ".github/workflows/*.y*ml")):
        if re.search(r"secrets\.ETSY_|ETSY_TOKEN\.json", Path(f).read_text(encoding="utf-8", errors="replace")):
            kume.add(".github/workflows/" + os.path.basename(f))
    return kume


# ------------------------------------------------------------------ Drive (rclone)
def alt_ortam():
    """Alt surece (rclone, token_geri_yaz.sh) yalniz gereken ortam: sirlar (OPS_ADMIN_TOKEN, ETSY_*) DEVREDILMEZ."""
    return {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL") or k.startswith("RCLONE_")}


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True, env=alt_ortam())          # cikti yazdirilmaz


def is_dizini():
    if IS["dizin"] is None:
        os.umask(0o077)
        IS["dizin"] = tempfile.mkdtemp(prefix="secret_gecis_")
    return IS["dizin"]


def token_indir(uzak=TOKEN_UZAK, ad="token.json"):
    """-> (yerel yol ya da None, sozluk ya da None). Dosya yoksa (None, None). Alanlar okunur okunmaz maskelenir."""
    yol = os.path.join(is_dizini(), ad)
    if os.path.exists(yol):
        os.remove(yol)
    r = rclone("copyto", uzak, yol)
    if r.returncode in (3, 4) or (r.returncode == 0 and not os.path.exists(yol)):
        return None, None
    if r.returncode != 0:
        raise Dur(f"token dosyasi indirilemedi (rclone cikis {r.returncode})")
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    for k in ("refresh_token", "access_token", "shared_secret", "keystring"):
        maskele(d.get(k))
    return yol, d


def alan_durumu(d, canli, ad="shared_secret"):
    v = (d or {}).get(ad) or ""
    return ("BOS", None) if not v else ("DOLU", esit(v, canli))


def token_metni(d, ham):
    guzel = "\n" in ham.strip()                                       # TokenStore.write ile ayni bicim (etsy_common.py:136-142)
    return json.dumps(d, indent=2 if guzel else None, ensure_ascii=False) + ("\n" if guzel else "")


def alan_yaz(yeni):
    """TEMP token dosyasinda YALNIZ shared_secret alanini degistirir (yeni None = kaldir). Tarihli Drive yedegi -> yaz -> yukle ->
    geri oku: yalniz o alan degisti, refresh_token ayni. Cagiran kilit altindadir."""
    yol, d0 = token_indir(ad="alan.json")                             # TokenStore'un dosyasindan (token.json) ayri kopya
    if d0 is None:
        raise Dur("TEMP token dosyasi yok")
    IS["depo"] = None                                                 # sonraki depo() Drive'daki yeni hali indirir
    ham = Path(yol).read_text(encoding="utf-8")
    damga = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if rclone("copyto", yol, f"{YEDEK_KOK}/ETSY_TOKEN_{damga}.json").returncode != 0:
        raise Dur("tarihli Drive yedegi yazilamadi (token dosyasina dokunulmadi)")
    yaz(f"tarihli Drive yedegi: ETSY_TOKEN_{damga}.json")
    d1 = dict(d0)
    if yeni is None:
        d1.pop("shared_secret", None)
    else:
        d1["shared_secret"] = yeni
    _, simdiki = token_indir(ad="yukleme_oncesi.json")                 # baska bir kosu bu arada dosyayi yazdiysa ustune yazma
    if simdiki != d0:
        raise Dur("token dosyasi indirme ile yukleme arasinda degisti: yazilmadi (yeni kosu ayri onay)")
    Path(yol).write_text(token_metni(d1, ham), encoding="utf-8")
    if not any(rclone("copyto", yol, TOKEN_UZAK).returncode == 0 for _ in range(3)):
        raise Dur("token dosyasi Drive'a YAZILAMADI (3 deneme); yedek duruyor, Merkez'e bildir")
    _, d2 = token_indir(ad="geri_oku.json")
    diger0 = {k: v for k, v in d0.items() if k != "shared_secret"}
    diger2 = {k: v for k, v in (d2 or {}).items() if k != "shared_secret"}
    if d2 != d1 or diger0 != diger2 or not esit((d2 or {}).get("refresh_token"), d0.get("refresh_token")):
        raise Dur("geri okuma FAIL: hedef alan disinda fark ya da refresh_token degisti; yedek duruyor, Merkez'e bildir")
    yaz("token dosyasi: yalniz shared_secret alani degisti, refresh_token ayni: PASS")


# ------------------------------------------------------------------ Etsy
def http_get(url, basliklar):
    import requests
    return requests.get(url, headers=basliklar, timeout=30)


def kota_kapisi():
    import etsy_common as E
    if KOTA["kalan"] is not None and KOTA["kalan"] < E.KOTA_SINIRI:
        raise Dur("kota sert tabani: kalan istek sinirin altinda")
    if KOTA["kalan"] is None and SAYAC["ok"] >= 1:
        raise Dur("kota basligi (x-remaining-today) okunamadi")
    if SAYAC["etsy"] >= MODLAR.get(os.environ.get("MOD") or "", 0):
        raise Dur("mod basina Etsy istek siniri asildi")


def etsy_get(yol, hedef, bearer=None):
    """Tek GET; x-api-key = ortamdaki keystring : HEDEF secret (E7). -> HTTP kodu. 401'de yenileme YOK."""
    import etsy_common as E
    if yol not in (PING, BEN) or (yol == BEN) != bool(bearer):
        raise Dur("izinsiz Etsy istegi")
    kota_kapisi()
    if SAYAC["etsy"]:
        time.sleep(ARALIK_SN)                                         # ardisik isteklerde saniyelik sinirin altinda kal
    b = {"x-api-key": f"{ortam('ETSY_API_KEY')}:{hedef}"}
    if bearer:
        b["Authorization"] = f"Bearer {bearer}"
    SAYAC["etsy"] += 1
    r = http_get(E.API + yol, b)
    kalan = str(r.headers.get("x-remaining-today") or "")
    if kalan.isdigit():
        KOTA["kalan"] = KOTA["son"] = int(kalan)
    if r.status_code == 200:
        SAYAC["ok"] += 1
    return int(r.status_code)


def depo(canli):
    """TokenStore (TEMP token dosyasi); kosu basina TEK ornek (yenilenen token baska ornekte bayatlamasin). Kurulum alanlari
    maskeler (etsy_common.py:59-62)."""
    import etsy_common as E
    if IS["depo"] is None:
        yol, d = token_indir()
        if d is None:
            raise Dur("TEMP token dosyasi yok")
        IS["depo"] = E.TokenStore(yol, ortam("ETSY_API_KEY"), canli)
    return IS["depo"]


def yenile(st, canli):
    """Token yenileme: yalniz TokenStore.refresh + standart geri yazim (scripts/etsy/token_geri_yaz.sh). -> 200 ya da DUR.
    TokenStore dosyadaki alani ortamin onune koyar (etsy_common.py:63-64): alan canliya esit degilse yenileme DENENMEZ."""
    if not esit(st.shared_secret, canli) or not esit(st.keystring, ortam("ETSY_API_KEY")):
        raise Dur("token dosyasindaki alan canliya esit degil: yanlis secret'la token yenileme denenmez")
    kota_kapisi()
    SAYAC["etsy"] += 1
    try:
        st.refresh()
    except SystemExit as e:
        m = re.search(r"token yenileme (\d{3})", str(e))
        raise Dur(f"token yenileme basarisiz (HTTP {m.group(1) if m else '?'})")
    sir_ekle(st.data.get("access_token"), st.data.get("refresh_token"))
    r = subprocess.run(["bash", str(KOK / "scripts/etsy/token_geri_yaz.sh"), str(st.path), TOKEN_UZAK], capture_output=True, text=True,
                       env=alt_ortam())
    if r.returncode != 0:
        raise Dur("YENILENEN TOKEN DRIVE'A GERI YAZILAMADI; Etsy kosulari baslatma, Merkez'e bildir")
    yaz("zincir testi: token yenileme 200, standart geri yazim PASS")
    return 200


def bearer_al(canli, st=None):
    st = st or depo(canli)
    if st.needs_refresh():
        yenile(st, canli)
    return st.access_token, st


def kanit(hedef, canli, st=None):
    """Kanit ucuna HEDEF secret'la tek istek -> HTTP kodu. OAuth ucunda access token suresi dolmussa DUR: canlinin gecerli oldugu
    kanitlanmadan token yenileme DENENMEZ (taze token: olc modu ya da herhangi bir Etsy okuma kosusu yeniler)."""
    if KANIT_UCU == "ping":
        return etsy_get(PING, hedef)
    if KANIT_UCU == "oauth":
        st = st or depo(canli)
        if st.needs_refresh():
            raise Dur("OAuth kanit ucu: access token suresi dolmus; kanittan once token yenileme denenmez (once herhangi bir Etsy okuma "
                      "kosusu token'i tazeler; sonra yeni kosu, ayri onay)")
        return etsy_get(BEN, hedef, bearer=st.access_token)
    raise Dur("kanit ucu AYARSIZ (olcum sonrasi ayri commit ve incelemeyle ayarlanir)")


def rastgele_secretler(*gercek):
    """Negatif kontrol degerleri: KONTROL_BOY uzunluklarinda rastgele harf-rakam. Gercek degerden turetilmez (secrets modulu)."""
    out = []
    for n in KONTROL_BOY:
        while True:
            r = "".join(_rastgele.choice(ALFABE) for _ in range(n))
            if not any(esit(r, g) for g in gercek if g):
                break
        sir_ekle(r)
        out.append(r)
    return out


def ret_ozeti(kodlar):
    """Negatif kontrol sonucu: yalniz 'hepsi reddedildi mi' (kod dagilimi YAZILMAZ: uzunluga gore farkli kod, gercek secret'in
    bicimi hakkinda ipucu olurdu)."""
    hepsi = all(k in (401, 403) for k in kodlar)
    return f"hepsi reddedildi (401 / 403): {en(hepsi)}" + ("" if hepsi else f"; 200 donen var: {en(200 in kodlar)}")


def kanit_kapisi(canli, *gercek):
    """Negatif kontrol: kanit ucu rastgele secret'lari REDDEDIYOR (hepsi 401 / 403); degilse DUR. Cagiran once pozitif istegi atar
    (ilk 200 yaniti kotayi bildirir; negatifler kota bilinmeden gitmez)."""
    if KANIT_UCU not in ("ping", "oauth"):
        raise Dur("kanit ucu AYARSIZ (olcum sonrasi ayri commit ve incelemeyle ayarlanir)")
    kodlar = [kanit(r, canli) for r in rastgele_secretler(canli, *gercek)]
    yaz(f"kanit ucu ({KANIT_UCU}) {len(kodlar)} rastgele secret: {ret_ozeti(kodlar)}")
    if any(k not in (401, 403) for k in kodlar):                      # 200: uc secret'i dogrulamiyor; 429 / 5xx: ret sayilmaz
        raise Dur("kanit ucu rastgele secret'la 200 dondu: bu uc secret'i dogrulamiyor" if 200 in kodlar else
                  "kanit ucu rastgele secret'a 401 / 403 disinda kod dondu (429 / 5xx olabilir): sonuc belirsiz")


def beklenen_200(ad, kod):
    yaz(f"kanit ucu {ad}: HTTP {kod}")
    if kod != 200:
        raise Dur(f"kanit ucu {ad} ile 200 degil")


# ------------------------------------------------------------------ modlar
def m_olc():
    canli = ortam(CANLI_AD)
    yaz(f"secret en az 12 karakter: {en(len(canli) >= 12)}")
    alan = None
    for ad, uzak in (("TEMP token dosyasi", TOKEN_UZAK), ("ucuncu dosya (ASTROLOVE/ETSY_TOKEN.json)", UCUNCU_UZAK)):
        _, d = token_indir(uzak, ad="olc.json")
        yaz(f"{ad}: {'VAR' if d is not None else 'YOK'}")
        if d is None:
            continue
        for a, ort in (("shared_secret", canli), ("keystring", ortam("ETSY_API_KEY"))):
            durum, ayni = alan_durumu(d, ort, a)
            yaz(f"{ad}: {a} alani {durum}" + (f"; alan == ortam: {en(ayni)}" if durum == "DOLU" else ""))
            if a == "shared_secret" and uzak == TOKEN_UZAK and durum == "DOLU" and not ayni:
                alan = d.get("shared_secret")
    rastlar = rastgele_secretler(canli, alan)
    st = depo(canli)
    sonuc = {}
    for uc, yol in (("oauth", BEN), ("ping", PING)):                   # once OAuth'lu GET: kota basligi bilinen yanit
        if yol == BEN and alan and st.needs_refresh():
            yaz("SONUC oauth: OLCULMEDI (alan != ortam ve token suresi dolmus; hangi secret'in dogru oldugu bilinmeden yenileme yok)")
            sonuc[uc] = False
            continue
        tok = bearer_al(canli, st)[0] if yol == BEN else None
        KOTA["son"] = None
        kodlar = {"ortam": etsy_get(yol, canli, tok)}
        yaz(f"{uc} yaniti kota basligi (x-remaining-today) tasiyor: {en(KOTA['son'] is not None)}")
        if alan:
            kodlar["alan"] = etsy_get(yol, alan, tok)
        rk = [etsy_get(yol, r, tok) for r in rastlar]
        for k, v in kodlar.items():
            yaz(f"{uc} {k} degeriyle: HTTP {v}")
        yaz(f"{uc} {len(rk)} rastgele secret: {ret_ozeti(rk)}")
        sonuc[uc] = kodlar["ortam"] == 200 and all(k in (401, 403) for k in rk)
        yaz(f"SONUC {uc}: kanit ucu sayilir mi: {en(sonuc[uc])}" + ("" if sonuc[uc] else " (rastgele secret 401 / 403 disinda kod aldi ya da ortamla 200 degil)"))
    yaz("SONUC: " + ("kanit ucu adayi: " + ", ".join(k for k in ("ping", "oauth") if sonuc.get(k)) if any(sonuc.values()) else "KANIT UCU YOK"))


def m_yedek():
    """canli -> YEDEK. YEDEK VARSA uzerine YAZILMAZ: gecis icinde yeniden kosulursa eski degerin tek kopyasini ezerdi."""
    canli, yeni, tok = ortam(CANLI_AD), ortam(YENI_AD, zorunlu=False), ortam("OPS_ADMIN_TOKEN")
    if var_mi(YEDEK_AD, tok):
        raise Dur(f"{YEDEK_AD} zaten VAR: uzerine yazilmaz (yedek_dogrula ile sinanir; yeni gecis icin once temizle)")
    if yeni and esit(canli, yeni):
        raise Dur("canli == YENI: gecis icinde yedek alinmaz")
    secret_yaz(YEDEK_AD, canli, tok)


def m_yedek_dogrula():
    canli, yedek = ortam(CANLI_AD), ortam(YEDEK_AD)
    ayni = esit(yedek, canli)
    yaz(f"YEDEK == canli: {en(ayni)}")
    if not ayni:
        raise Dur("YEDEK canliya esit degil (Etsy istegi atilmadi)")
    beklenen_200("YEDEK", kanit(yedek, canli))
    yaz(f"kanit ucu yaniti kota basligi (x-remaining-today) tasiyor: {en(KOTA['kalan'] is not None)}")
    if KOTA["kalan"] is None:      # dogrula / tamam_kontrol 200'den sonra istek atar; baslik yoksa gecis ortasinda DUR olurdu
        raise Dur("kanit ucu yaniti kota basligi tasimiyor: bu kanit ucuyla dogrula ve tamam_kontrol kosamaz; gecise BASLANMAZ")
    kanit_kapisi(canli, yedek)


def prova_dosyasi():
    return os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "secret_gecis_prova.json")


def m_prova():
    """Sayactan once; canli secret'a DOKUNMAZ. Olcer: Serdar'in deneme girisi (E4), OPS_ADMIN_TOKEN secret yazma / silme, is akisi
    kapatma / acma yetkisi. Ikinci adim (prova_son): adim ortami yeni degeri goruyor mu + geri alma."""
    tok = ortam("OPS_ADMIN_TOKEN")
    onceki = wf_durum(PROVA_WF, tok)
    if onceki not in ("active", "disabled_manually"):      # disabled_inactivity vb. geri getirilemez: hic dokunma
        raise Dur(f"{PROVA_WF} durumu active / disabled_manually degil: prova bu is akisina dokunmaz")
    sonuc = {}
    sonuc["Serdar deneme girisi (ETSY_SECRET_DENEME) VAR"] = var_mi(DENEME_AD, tok)
    if sonuc["Serdar deneme girisi (ETSY_SECRET_DENEME) VAR"]:
        gs().delete_secret(REPO_AD, DENEME_AD, tok)
        sonuc["ETSY_SECRET_DENEME silindi"] = not var_mi(DENEME_AD, tok)
    r1, r2 = _rastgele.token_urlsafe(24), _rastgele.token_urlsafe(24)
    sir_ekle(r1, r2)
    secret_yaz(PROVA_AD, r1, tok)
    u1 = meta(PROVA_AD, tok)
    time.sleep(2)
    secret_yaz(PROVA_AD, r2, tok)
    sonuc["OPS_ADMIN_TOKEN secret yazabiliyor (iki yazim, updated_at ilerledi)"] = bool(u1) and (meta(PROVA_AD, tok) or "") > u1
    os.umask(0o077)
    Path(prova_dosyasi()).write_text(json.dumps({"r2": r2, "onceki": onceki}), encoding="utf-8")
    etkin = onceki == "active"
    sonuc["is akisi kapatma / acma yetkisi"] = wf_ayarla(PROVA_WF, not etkin, tok) and (wf_durum(PROVA_WF, tok) == "active") == (not etkin)
    for k, v in sonuc.items():
        yaz(f"{k}: {en(v)}")
    if not all(sonuc.values()):
        raise Dur("prova: en az bir olcum HAYIR")


def m_prova_son():
    """always() adimi: ETSY_SECRET_PROVA'yi siler, is akisini onceki durumuna dondurur, adim ortamini olcer. Iki geri alma ayri
    denenir (biri hata verse de digeri yapilir); kayit dosyasi en son silinir."""
    tok = ortam("OPS_ADMIN_TOKEN")
    p = prova_dosyasi()
    kayit = json.loads(Path(p).read_text(encoding="utf-8")) if os.path.exists(p) else {}
    sir_ekle(kayit.get("r2"))
    ortamdaki = os.environ.get("PROVA_DEGERI") or ""
    sir_ekle(ortamdaki)
    yaz("sonraki adimin ortamindaki secret: " + ("BOS (deger is basinda sabitlenmis)" if not ortamdaki else
                                                 "yazilan son degere esit: " + en(esit(ortamdaki, kayit.get("r2")))))
    try:
        if var_mi(PROVA_AD, tok):
            gs().delete_secret(REPO_AD, PROVA_AD, tok)
        silindi = not var_mi(PROVA_AD, tok)
    except Exception:  # noqa: BLE001  silme yetkisi yoksa da is akisi geri alinir
        silindi = False
    yaz(f"OPS_ADMIN_TOKEN secret silebiliyor (ETSY_SECRET_PROVA silindi): {en(silindi)}")
    geri = True
    if kayit.get("onceki"):
        try:
            wf_ayarla(PROVA_WF, kayit["onceki"] == "active", tok)
            geri = wf_durum(PROVA_WF, tok) == kayit["onceki"]
        except Exception:  # noqa: BLE001
            geri = False
        yaz(f"{PROVA_WF} onceki durumuna dondu: {en(geri)}")
    if os.path.exists(p):
        os.remove(p)
    if not geri or not silindi:
        raise Dur("prova_son: geri alma ya da silme FAIL")


def m_kapat():
    tok = ortam("OPS_ADMIN_TOKEN")
    etkin = [a for a in KAPAT if wf_durum(a + ".yml", tok) == "active"]
    degisken_yaz(set(degisken_oku(tok)) | set(etkin), tok)          # once kayit (ikinci kapat kaydi ezmez), sonra kapatma
    for a in etkin:
        wf_ayarla(a + ".yml", False, tok)
    kapali = {a: wf_durum(a + ".yml", tok) != "active" for a in KAPAT}
    for a in KAPAT:
        yaz(f"{a}: kapali {en(kapali[a])}" + (" (bu kosuda kapatildi)" if a in etkin else " (onceden kapaliydi)"))
    if not all(kapali.values()):
        raise Dur("kapat: en az bir is akisi hala etkin")


def m_ac():
    tok = ortam("OPS_ADMIN_TOKEN")
    kayitli = degisken_oku(tok)
    for a in kayitli:
        wf_ayarla(a + ".yml", True, tok)
    acik = {a: wf_durum(a + ".yml", tok) == "active" for a in kayitli}
    for a in KAPAT:
        yaz(f"{a}: " + (f"acildi {en(acik[a])}" if a in acik else "kayitta yok, dokunulmadi"))
    degisken_yaz({a for a, ok in acik.items() if not ok}, tok)
    if not all(acik.values()):
        raise Dur("ac: en az bir is akisi acilamadi")


def m_kod_anahtari():
    tok = ortam("OPS_ADMIN_TOKEN")
    if var_mi(KOD_AD, tok):
        yaz(f"{KOD_AD}: VAR, dokunulmadi")
        return
    deger = _rastgele.token_urlsafe(48)                               # 48 bayt rastgele; gercek degerden turetilmez
    sir_ekle(deger)
    secret_yaz(KOD_AD, deger, tok)


def m_alan_sil():
    canli = ortam(CANLI_AD)
    _, d = token_indir()
    if d is None:
        raise Dur("TEMP token dosyasi yok")
    durum, ayni = alan_durumu(d, canli)
    yaz(f"shared_secret alani: {durum}")
    if durum == "BOS":
        yaz("alan zaten yok: PASS")
        return
    yaz(f"alan == canli: {en(ayni)}")
    if not ayni:
        raise Dur("alan canliya esit degil: alan_sil uygulanmaz (once hangisinin dogru oldugu cozulur)")
    alan_yaz(None)
    if KANIT_UCU == "ping" or (KANIT_UCU == "oauth" and not depo(canli).needs_refresh()):
        beklenen_200("canli (alan silindikten sonra)", kanit(canli, canli))
    else:
        yaz("alan sonrasi kanit istegi atlandi (kanit ucu AYARSIZ ya da OAuth token suresi dolmus)")


def m_alan_geri():
    canli, yedek = ortam(CANLI_AD), ortam(YEDEK_AD, zorunlu=False)
    _, d = token_indir()
    if d is None:
        raise Dur("TEMP token dosyasi yok")
    durum, ayni = alan_durumu(d, canli)
    yaz(f"shared_secret alani: {durum}")
    if durum == "DOLU":
        if not ayni:
            raise Dur("alan dolu ve canliya esit degil")
        yaz("alan zaten var ve canliya esit: PASS")
        return
    if yedek and not esit(yedek, canli):
        raise Dur("canli YEDEK'e esit degil: alan_geri yalniz gecisten once ya da geri_al'dan sonra")
    alan_yaz(canli)


def dosya_plani(d, eski, yeni):
    """TEMP token dosyasindaki alan icin karar: 'yok' (BOS) | 'ayni' (zaten yeni) | 'guncelle' (eski -> yeni) | DUR."""
    v = (d or {}).get("shared_secret") or ""
    if not v:
        return "yok"
    if esit(v, yeni):
        return "ayni"
    if esit(v, eski):
        return "guncelle"
    raise Dur("token dosyasindaki alan ne eski ne yeni degere esit")


def takas(hedef_ad, hedef, eski_ad, eski):
    """degistir (hedef YENI, eski YEDEK) ve geri_al (hedef YEDEK, eski YENI) ortak govdesi. Butun kapilar ve kanit yazimdan ONCE;
    kanit PASS olmadan ne secret ne dosya yazilir. geri_al'da canli ve dosya alani uyelik kapisi YOK (geri donus yolu gereksiz DUR
    vermesin): kanit YEDEK ile 200 sarttir; alan YEDEK degilse (YENI, onceki canli ya da taninmayan) kanitlanmis YEDEK'e cekilir."""
    ileri = hedef_ad == YENI_AD
    kisa = hedef_ad.replace("ETSY_SHARED_SECRET_", "")
    canli, tok = ortam(CANLI_AD), ortam("OPS_ADMIN_TOKEN")
    if not hedef or re.search(r"\s", hedef):
        raise Dur(f"{hedef_ad} bos ya da bosluk iceriyor")
    if ileri and not eski:
        raise Dur(f"{eski_ad} yok")
    if eski and esit(hedef, eski):
        raise Dur("YENI == YEDEK" + ("" if ileri else ": geri alinacak eski deger YEDEK'te yok; Serdar 'Cancel' DEMEZ"))
    if ileri and not (esit(canli, hedef) or esit(canli, eski)):
        raise Dur("canli ne YEDEK'e ne YENI'ye esit")
    if ileri:
        etkin = sorted({os.path.basename(wf_yolu(k)) for k in aktif_kosular(ortam("GH_TOKEN"))} & {a + ".yml" for a in KAPAT})
        yaz(f"18 is akisinda aktif kosu: {'VAR' if etkin else 'YOK'}" + (f" ({', '.join(etkin)})" if etkin else ""))
        if etkin:
            raise Dur("sir sizdirabilen is akislarinda aktif kosu var")
        _, u = token_indir(UCUNCU_UZAK, ad="ucuncu.json")              # hicbir mod bu dosyayi guncellemez; dogrula onu sart kosar
        if u is not None and (u.get("shared_secret") or "") and not esit(u.get("shared_secret"), hedef):
            raise Dur("ucuncu dosyada (ASTROLOVE/ETSY_TOKEN.json) shared_secret alani DOLU ve YENI'ye esit degil: once cozulur")
    _, d = token_indir()
    if d is None:
        raise Dur("TEMP token dosyasi yok")
    try:
        plan = dosya_plani(d, eski, hedef)
    except Dur:
        if ileri:
            raise
        plan = "guncelle"                                              # geri_al: alan ne olursa olsun kanitlanmis YEDEK'e cekilir
        yaz("token dosyasi alani YEDEK'e ya da YENI'ye esit degil: geri alirken YEDEK yazilacak (onceki hali tarihli yedekte kalir)")
    beklenen_200(kisa, kanit(hedef, canli))                            # once pozitif istek: ilk 200 kotayi bildirir
    kanit_kapisi(canli, hedef, eski)
    yaz("KAPILAR PASS")
    if esit(canli, hedef):
        yaz(f"canli zaten {kisa} degerinde: secret yazimi atlandi")
    else:
        secret_yaz(CANLI_AD, hedef, tok)
    if plan == "guncelle":
        alan_yaz(hedef)
    else:
        yaz("token dosyasi: " + ("alan BOS, dokunulmadi" if plan == "yok" else "alan zaten hedef degerde, dokunulmadi"))


def m_degistir():
    takas(YENI_AD, ortam(YENI_AD, zorunlu=False), YEDEK_AD, ortam(YEDEK_AD, zorunlu=False))


def m_geri_al():
    takas(YEDEK_AD, ortam(YEDEK_AD, zorunlu=False), YENI_AD, ortam(YENI_AD, zorunlu=False))


def alan_beklenen(canli, uzak, ad):
    """Alan BOS ya da canliya esit -> True. Dosya yoksa: TEMP icin False, ucuncu dosya icin True."""
    _, d = token_indir(uzak, ad="kontrol.json")
    if d is None:
        yaz(f"{ad}: YOK")
        return uzak != TOKEN_UZAK
    durum, ayni = alan_durumu(d, canli)
    yaz(f"{ad}: shared_secret alani {durum}" + (f"; alan == canli: {en(ayni)}" if durum == "DOLU" else ""))
    return durum == "BOS" or bool(ayni)


def m_dogrula():
    canli, yeni, yedek = ortam(CANLI_AD), ortam(YENI_AD), ortam(YEDEK_AD)
    s = {"canli == YENI": esit(canli, yeni), "canli != YEDEK": not esit(canli, yedek)}
    s["TEMP token dosyasi alani beklenen durumda"] = alan_beklenen(canli, TOKEN_UZAK, "TEMP token dosyasi")
    s["ucuncu dosya YOK ya da beklenen durumda"] = alan_beklenen(canli, UCUNCU_UZAK, "ucuncu dosya")
    for k, v in s.items():
        yaz(f"{k}: {en(v)}")
    if not all(s.values()):
        raise Dur("dogrula: en az bir satir HAYIR; Serdar 'completed' DEMEZ (Etsy istegi atilmadi)")
    st = depo(canli)
    beklenen_200("canli", kanit(canli, canli, st))
    kanit_kapisi(canli, yeni, yedek)
    yenile(st, canli)


def son_alan_yazimi():
    """Bu betigin en yeni token yedegi damgasi (= son alan yazimi ani) -> 'YYYY-mm-ddTHH:MM:SSZ' ya da '' (yedek yok)."""
    r = rclone("lsjson", YEDEK_KOK, "--files-only")
    if r.returncode == 3:
        return ""
    if r.returncode != 0:
        raise Dur(f"Drive yedek klasoru listelenemedi (rclone cikis {r.returncode})")
    damga = [m.group(1) for x in json.loads(r.stdout or "[]")
             for m in [re.fullmatch(r"ETSY_TOKEN_(\d{8}T\d{6}Z)\.json", str(x.get("Name") or ""))] if m]
    if not damga:
        return ""
    t = max(damga)
    return f"{t[:4]}-{t[4:6]}-{t[6:8]}T{t[9:11]}:{t[11:13]}:{t[13:15]}Z"


def m_tamam_kapisi():
    canli, yeni, tok = ortam(CANLI_AD), ortam(YENI_AD), ortam("OPS_ADMIN_TOKEN")
    yazim = meta(CANLI_AD, tok)
    if not yazim:
        raise Dur("canli secret'in updated_at degeri okunamadi")
    kume = etsy_kumesi()
    # sinir = son yazim (secret ya da token dosyasi alani; alan gec bir yeniden kosuda yazilmis olabilir) + pay
    son = max(yazim, son_alan_yazimi())
    sinir = (datetime.strptime(son, "%Y-%m-%dT%H:%M:%SZ") + timedelta(minutes=PAY_DK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    eski = sorted({os.path.basename(wf_yolu(k)) for k in aktif_kosular(ortam("GH_TOKEN"))
                   if wf_yolu(k) in kume and (k.get("created_at") or "") <= sinir})
    s = {"canli == YENI": esit(canli, yeni),
         "son yazimdan (+5 dk pay) once baslamis aktif Etsy kosusu YOK": not eski,
         "TEMP token dosyasi alani beklenen durumda": alan_beklenen(canli, TOKEN_UZAK, "TEMP token dosyasi")}
    for k, v in s.items():
        yaz(f"{k}: {en(v)}" + (f" ({', '.join(eski)})" if k.startswith("son yazimdan") and eski else ""))
    if not all(s.values()):
        raise Dur("tamamlama kapisi FAIL; Serdar 'completed' DEMEZ")


def tamam_kapilari(canli, yedek, st=None):
    """Canli kabul ediliyor, eski secret reddediliyor (TEK okuma; bekleme dongusu yok), negatif kontrol."""
    beklenen_200("canli", kanit(canli, canli, st))
    kod = kanit(yedek, canli, st)
    yaz(f"kanit ucu YEDEK (eski): HTTP {kod}")
    if kod == 200:
        raise Dur("eski secret hala 200: gecis tamamlanmamis (yeniden kosu ayri onay)")
    kanit_kapisi(canli, yedek)


def m_tamam_kontrol():
    canli, yedek = ortam(CANLI_AD), ortam(YEDEK_AD)
    if esit(canli, yedek) or not alan_beklenen(canli, TOKEN_UZAK, "TEMP token dosyasi"):
        raise Dur("tamam kontrol: canli == YEDEK ya da token dosyasi alani beklenen durumda degil (Etsy istegi atilmadi)")
    st = depo(canli)
    tamam_kapilari(canli, yedek, st)
    yenile(st, canli)
    if KANIT_UCU != "oauth":
        kod = etsy_get(BEN, canli, bearer=st.access_token)
        yaz(f"OAuth'lu salt okuma GET (canli): HTTP {kod}")
        if kod != 200:
            raise Dur("OAuth'lu GET 200 degil")


def m_geri_dogrula():
    canli, yedek, yeni = ortam(CANLI_AD), ortam(YEDEK_AD), ortam(YENI_AD, zorunlu=False)
    s = {"canli == YEDEK": esit(canli, yedek),
         "YEDEK != YENI (YEDEK eski degeri tasiyor)": not (yeni and esit(yedek, yeni)),
         "TEMP token dosyasi alani beklenen durumda": alan_beklenen(canli, TOKEN_UZAK, "TEMP token dosyasi")}
    for k, v in s.items():
        yaz(f"{k}: {en(v)}")
    if not all(s.values()):
        raise Dur("geri dogrulama FAIL; Serdar 'Cancel' DEMEZ (Etsy istegi atilmadi)")
    beklenen_200("YEDEK", kanit(yedek, canli))
    kanit_kapisi(canli, yedek)


def drive_listesi():
    """Drive token yedekleri: yalniz ad ve tarih (icerik acilmaz; bayt YAZILMAZ: alanli / alansiz yedek farki uzunluk sizdirir)."""
    out = []
    for kok, suz_ in ((YEDEK_KOK, "ETSY_TOKEN_"), (ONCEKI_KOK, "ETSY_TOKEN_ONCEKI_")):
        r = rclone("lsjson", kok, "--files-only")
        if r.returncode == 3:
            continue
        if r.returncode != 0:
            raise Dur(f"Drive yedek listesi okunamadi (rclone cikis {r.returncode})")
        for x in json.loads(r.stdout or "[]"):
            if str(x.get("Name") or "").startswith(suz_):
                out.append((kok, x.get("Name"), str(x.get("ModTime") or "")[:19]))
    return out


def m_temizle():
    """Gecici secret'lari siler. Iki dal: (1) gecis TAMAM: canli != YEDEK, tamam kontrol kapilari. (2) geri donus TAMAM (ya da gecis
    hic baslamadi): canli == YEDEK, canli 200, YENI varsa Etsy'de REDDEDILIYOR (Serdar 'Cancel' demis). YEDEK en son silinir."""
    canli, yedek, yeni, tok = ortam(CANLI_AD), ortam(YEDEK_AD, zorunlu=False), ortam(YENI_AD, zorunlu=False), ortam("OPS_ADMIN_TOKEN")
    if not yedek:
        raise Dur("YEDEK yok: kapilar yeniden okunamaz, hicbir sey silinmedi")
    if esit(canli, yedek):
        yaz("canli == YEDEK: geri donus dali")
        beklenen_200("canli (= YEDEK)", kanit(canli, canli))
        if yeni:
            kod = kanit(yeni, canli)
            yaz(f"kanit ucu YENI (iptal edilmis olmali): HTTP {kod}")
            if kod not in (401, 403):
                raise Dur("YENI hala kabul ediliyor ya da sonuc belirsiz: geri donus tamamlanmamis, hicbir sey silinmedi")
        kanit_kapisi(canli, yedek, yeni)
    else:
        tamam_kapilari(canli, yedek)                                   # PASS degilse Dur: hicbir sey silinmez
    liste = drive_listesi()                                            # listeleme hatasi silmeden ONCE gorulur
    kalan = []
    for ad in (YENI_AD, DENEME_AD, PROVA_AD, YEDEK_AD):                # YEDEK en son: oncekiler silinemezse YEDEK durur, yeniden kosulabilir
        if ad == YEDEK_AD and kalan:
            yaz(f"{ad}: silinmedi (once digerleri silinmeli)")
            continue
        try:
            if var_mi(ad, tok):
                gs().delete_secret(REPO_AD, ad, tok)
            silindi = not var_mi(ad, tok)
        except Exception:  # noqa: BLE001
            silindi = False
        yaz(f"{ad}: silindi {en(silindi)}")
        if not silindi:
            kalan.append(ad)
    for kok, ad, tarih in liste:
        yaz(f"Drive token yedegi (yalniz liste): {kok.split(':', 1)[1]}/{ad} | {tarih}")
    if kalan:
        raise Dur("temizle: en az bir gecici secret silinemedi (YEDEK duruyor; yeniden kosu ayri onay)")


def m_temizle_drive():
    """Yalniz bu betigin yedek klasoru (YEDEK_KOK) kalici silinir; ETSY_TOKEN_ONCEKI_* yalniz listelenir. YEDEK secret'i
    dururken (gecis / geri donus bitmemis) KOSMAZ: Drive yedegi eski alanin tek kopyasi olabilir."""
    canli, tok = ortam(CANLI_AD), ortam("OPS_ADMIN_TOKEN")
    if var_mi(YEDEK_AD, tok):
        raise Dur(f"{YEDEK_AD} duruyor: once temizle (gecis bitmeden Drive yedekleri silinmez)")
    beklenen_200("canli", kanit(canli, canli))
    kanit_kapisi(canli)
    kalan = 0
    for kok, ad, tarih in drive_listesi():
        if kok != YEDEK_KOK:
            yaz(f"listelendi, silinmedi: {kok.split(':', 1)[1]}/{ad} | {tarih}")
            continue
        ok = rclone("deletefile", "--drive-use-trash=false", f"{kok}/{ad}").returncode == 0
        yaz(f"kalici silindi {en(ok)}: {kok.split(':', 1)[1]}/{ad}")
        kalan += not ok
    if kalan:
        raise Dur("temizle_drive: en az bir yedek silinemedi")


ISLEV = {"olc": m_olc, "yedek": m_yedek, "yedek_dogrula": m_yedek_dogrula, "prova": m_prova, "kapat": m_kapat, "ac": m_ac,
         "kod_anahtari": m_kod_anahtari, "alan_sil": m_alan_sil, "alan_geri": m_alan_geri, "degistir": m_degistir,
         "dogrula": m_dogrula, "tamam_kapisi": m_tamam_kapisi, "tamam_kontrol": m_tamam_kontrol, "geri_al": m_geri_al,
         "geri_dogrula": m_geri_dogrula, "temizle": m_temizle, "temizle_drive": m_temizle_drive}


def calis(argv):
    """-> cikis kodu. Hata yolunda yalniz sabit metin; istisna metni yazilmaz."""
    komut = argv[0] if argv else ""
    socket.setdefaulttimeout(30)          # gh_secrets'in zaman asimsiz cagrilari (set_secret / set_variable) kilit altinda asili kalmasin
    try:
        for ad in ("OPS_ADMIN_TOKEN", "GH_TOKEN", "ETSY_API_KEY", CANLI_AD, YEDEK_AD, YENI_AD, "PROVA_DEGERI"):
            sir_ekle(os.environ.get(ad) or "")
        if komut == "kapi":
            yaz(f"KAPI PASS: mod {kapi()}")
            return 0
        if komut == "prova_son":
            if kapi() != "prova":
                raise Dur("prova_son yalniz prova modunda")
            m_prova_son()
            return 0
        if komut not in ISLEV or kapi() != komut:
            raise Dur("mod / komut uyusmuyor")
        if komut in KANITLI and KANIT_UCU not in ("ping", "oauth"):
            raise Dur("kanit ucu AYARSIZ (olcum sonrasi ayri commit ve incelemeyle ayarlanir)")
        ISLEV[komut]()
        yaz(f"{komut}: PASS | Etsy istegi {SAYAC['etsy']}")
        return 0
    except Dur as e:
        yaz(f"DUR ({komut}): {e}")
        return 1
    except SystemExit:
        yaz(f"DUR ({komut}): alt modul durdu (SystemExit)")
        return 1
    except Exception as e:  # noqa: BLE001  istisna metni yazilmaz (deger tasiyabilir)
        yaz(f"DUR ({komut}): beklenmeyen hata ({type(e).__name__})")
        return 1
    finally:
        if IS["dizin"] and os.path.isdir(IS["dizin"]):
            for f in glob.glob(os.path.join(IS["dizin"], "*")):
                os.remove(f)
            os.rmdir(IS["dizin"])
            IS["dizin"], IS["depo"] = None, None


if __name__ == "__main__":
    sys.exit(calis(sys.argv[1:]))
