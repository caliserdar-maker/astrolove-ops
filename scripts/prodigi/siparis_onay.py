#!/usr/bin/env python3
"""Kisisellestirilmis siparis ONAY akisi (Serdar, 25 Eyl 2026). CANLIYA ALINMADI (siparis-onay dali).

Akis:
 1 router yeni siparisi okur; kisisellestirme cevabi olan her kalem icin 3 alan ayristirilir (kisisel_siparis).
 2 on kontrol: Kiril / Latin disi isim, emoji / kalp, uzunluk (11/11/35), eksik alan. Sorun varsa tabloda
   "MUSTERIYE MESAJ GEREKLI" + sablon no; musteriye mesaj GONDERILMEZ, dosya URETILMEZ.
 3 temizse siparis_dosyasi.py (siparis-baski-v1) bu siparis icin calisir (workflow adimi); KONTROL paketi
   Drive TEMP/SIPARIS/<receipt>/ klasorune tasinir (`uretildi` modu tabloyu gunceller).
 4 Drive'da SIPARIS_ONAY tablosu (Google Sheets; Sheets API kapaliysa Drive CSV-donusumlu tablo): receipt, urun,
   renk/boy, isimler, mesaj, on kontrol, KONTROL linkleri, ONAY kutusu, durum.
 5 bildirim: mevcut altyapi = kosu basarisiz + ::error satiri (GitHub e-postasi). Satirda YALNIZ opak kod +
   Drive linkleri (x3 isim/mesaj bandi, tam cozunurluk, tablo satiri) vardir; gorsel e-postaya gomulemez.
 6 onay izleyici (router her kosuda): ONAY isaretli + ONAY_BEKLIYOR satir ->
     POD: Prodigi siparisi (router submit_package: gecici, tahmin edilemez Drive linki; indirilince kapanir).
     DIJITAL / DUVAR_KAGIDI: durum "CHATGPT_YUKLEME_BEKLIYOR" + bildirim.
 7 idempotent: STATE + tablo durumu + Prodigi idempotencyKey (etsy-<receipt>). Hata -> DUR + bildirim.
 8 musteri verisi (isim, mesaj, adres, receipt) repoya / loga / issue'ya YAZILMAZ; loglarda yalniz opak kod
   (S-xxxxxxxx, anahtarli ozet) gecer. Tablo ve dosyalar yalniz Drive'dadir.
"""
import csv
import hashlib
import hmac
import io
import json
import os
import pathlib
import subprocess
import sys
import time

KOLON = ["KOD", "RECEIPT", "TARIH_UTC", "URUN", "CIFT", "RENK", "BOY", "ISIM1", "ISIM2", "MESAJ", "ULKE",
         "ON_KONTROL", "SABLON", "KONTROL_KLASOR", "BASKI", "ISIM_x3", "MESAJ_x3", "KARTPOSTAL", "FIYAT", "KARGO", "NET_KAR", "KAR_UYARI",
         "ONAY", "DURUM", "PRODIGI", "NOT"]
D_MESAJ = "MUSTERIYE_MESAJ_GEREKLI"
D_DOSYA = "DOSYA_URETILIYOR"
D_ONAY = "ONAY_BEKLIYOR"
D_PRODIGI = "PRODIGI_GONDERILDI"
D_CHATGPT = "CHATGPT_YUKLEME_BEKLIYOR"
D_HATA = "HATA"
DRIVE_KOK = "gdrive:ASTROLOVE/TEMP/SIPARIS"
TABLO_AD = "SIPARIS_ONAY"
# kisiye ozel kartpostal (Serdar 25 Eyl): kaynak kart + ciftin POSTER_AM'i + Cinzel; Prodigi branding.postcard.url
KART_KAYNAK = "gdrive:ASTROLOVE/BRAND/INSERTS/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg"
A1_77 = "gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77"
KART_AD = "KARTPOSTAL_A6.jpg"
EVET = {"TRUE", "EVET", "X", "YES", "1", "✓", "✔"}
ETSY_SABIT, ETSY_ORAN = 0.582, 0.176     # Etsy kesintisi = 0.582 x adet + 0.176 x fiyat (Serdar, 25 Eyl 2026)
ZARAR = "🔴 ZARAR"
# Paket ekstralari (kartpostal + 2 sticker; hesap ayari, her pakette - Serdar 25 Eyl). Prodigi Quote API bunlari
# FIYATLAMIYOR (7 Eyl kosu 34115064337). Tesis teklifteki shipments[].fulfillmentLocation'dan gelir.
# Dogrulanmis tesis: GERCEK FATURA tutari (Serdar karari 25 Eyl). Dogrulanmamis tesis: Prodigi fiyat tablosu
# (kartpostal 2.00 GBP + 2 x sticker 1.00 GBP) x ECB kuru + "dogrulanmadi" notu. Tahminle "basilmiyor" isaretlenmez.
EKSTRA_GBP = 4.00
KUR_GBP_USD, KUR_TARIH = 1.3252, "2026-09-25"     # ECB referans kuru (prodigi-quote ekstra_tesis, kosu 36162621950)
EKSTRA_KAYNAK = "Prodigi fiyat tablosu"
# labCode -> (USD, kaynak). Canli faturalar (kosu 36162621950, salt okuma). Router yeni tesisin ilk faturasindan
# ogrenir ve Drive EKSTRA_REMOTE'a yazar (ekstra_ogren); kosu basinda ekstra_tablo_yukle ile birlesir.
EKSTRA_DOGRULANMIS = {"prodigi_us": (5.00, "fatura ord_14538276"),
                      "prodigi_eu": (5.73, "fatura ord_72296317183912448")}
EKSTRA_BASILMAYAN = set()                         # kanitla (fatura/dokuman) basilmadigi gosterilen tesis; tahmin YOK
EKSTRA_REMOTE = "gdrive:ASTROLOVE/TEMP/PRODIGI/EKSTRA_TESIS.json"
NOT_EKSTRA_YOK = "Bu tesiste kartpostal/sticker eklenmiyor"


def ekstra_usd():
    return round(EKSTRA_GBP * KUR_GBP_USD, 2)


def ekstra(lab):
    """tesis -> (USD, kaynak, not)."""
    lab = (lab or "").split("/")[-1].strip()
    if lab in EKSTRA_BASILMAYAN:
        return 0.0, f"tesis {lab}", NOT_EKSTRA_YOK
    if lab in EKSTRA_DOGRULANMIS:
        usd, kaynak = EKSTRA_DOGRULANMIS[lab]
        return float(usd), kaynak, ""
    return (ekstra_usd(), f"{EKSTRA_KAYNAK} ({EKSTRA_GBP:.2f} GBP, ECB {KUR_TARIH} kuru {KUR_GBP_USD})",
            f"tesis {lab or '?'} icin ekstra dogrulanmadi ({ekstra_usd():.2f} fiyat tablosundan)")


def _rclone_oku(yol):
    try:
        r = subprocess.run(["rclone", "cat", yol], capture_output=True, text=True)
    except OSError:
        return ""
    return r.stdout if r.returncode == 0 else ""


def _rclone_yaz(yol, metin):
    try:
        return subprocess.run(["rclone", "rcat", yol], input=metin, capture_output=True, text=True).returncode == 0
    except OSError:
        return False


def ekstra_tablo_yukle(oku=_rclone_oku):
    """Drive EKSTRA_TESIS.json {lab: {usd, kaynak, tarih}} -> EKSTRA_DOGRULANMIS (kod sabitleri korunur)."""
    try:
        d = json.loads(oku(EKSTRA_REMOTE) or "{}")
    except ValueError:
        return 0
    n = 0
    for lab, v in d.items():
        if lab not in EKSTRA_DOGRULANMIS and isinstance(v, dict) and v.get("usd") is not None:
            EKSTRA_DOGRULANMIS[lab] = (float(v["usd"]), str(v.get("kaynak") or "fatura"))
            n += 1
    return n


def ekstra_ogren(order, oku=_rclone_oku, yaz=_rclone_yaz):
    """Dogrulanmamis tesisin ILK faturalanan siparisi: ekstra tutari faturadan (SKU/tutar eslesmesi) okunur,
    tabloya eklenir, Drive'a yazilir. -> (lab, usd) ya da None."""
    from prodigi_ekstra_tesis import ekstra_faturadan
    ek = ekstra_faturadan(order or {})
    if not ek:
        return None
    lab = ek["tesis"].split("/")[-1]
    if lab in EKSTRA_DOGRULANMIS:
        return None
    try:
        d = json.loads(oku(EKSTRA_REMOTE) or "{}")
    except ValueError:
        d = {}
    d[lab] = {"usd": ek["usd"], "kaynak": f"fatura {order.get('id')}", "tarih": str(order.get("created") or "")[:10],
              "kalemler": ek["kalemler"], "yontem": ek["yontem"]}
    yaz(EKSTRA_REMOTE, json.dumps(d, indent=1))
    EKSTRA_DOGRULANMIS[lab] = (ek["usd"], f"fatura {order.get('id')}")
    return lab, ek["usd"]


def kod(rid):
    """Loglarda receipt yerine gecen opak kod. Anahtar gizli (ETSY_SHARED_SECRET / SIPARIS_KOD_ANAHTARI)."""
    anahtar = (os.environ.get("SIPARIS_KOD_ANAHTARI") or os.environ.get("ETSY_SHARED_SECRET") or "astrolove").encode()
    return "S-" + hmac.new(anahtar, str(rid).encode(), hashlib.sha256).hexdigest()[:8]


def gizle(metin, receiptler):
    """Log / Actions ozeti icin: verilen receipt'ler opak kodla degisir (Drive'daki rapor tam kalir)."""
    import re
    for rid in sorted({str(x) for x in receiptler if x}, key=len, reverse=True):
        metin = re.sub(rf"(?<!\d){re.escape(rid)}(?!\d)", kod(rid), metin)
    return metin


def onayli(v):
    return str(v or "").strip().upper() in EVET


# ------------------------------------------------------------------ tablo arka uclari
class YerelTablo:
    """Test / yerel: CSV dosyasi (ayni kolonlar)."""
    tur = "yerel"

    def __init__(self, yol):
        self.yol = pathlib.Path(yol)
        self.link = f"file://{self.yol}"
        if not self.yol.exists():
            self._yaz([])

    def _yaz(self, rows):
        with self.yol.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=KOLON)
            w.writeheader()
            w.writerows(rows)

    def satirlar(self):
        with self.yol.open(newline="", encoding="utf-8") as fh:
            return [dict(r, _no=i + 2) for i, r in enumerate(csv.DictReader(fh))]

    def ekle(self, d):
        rows = [{k: r.get(k, "") for k in KOLON} for r in self.satirlar()]
        rows.append({k: d.get(k, "") for k in KOLON})
        self._yaz(rows)
        return len(rows) + 1

    def guncelle(self, no, d):
        rows = [{k: r.get(k, "") for k in KOLON} for r in self.satirlar()]
        rows[no - 2].update({k: v for k, v in d.items() if k in KOLON})
        self._yaz(rows)

    def satir_link(self, no):
        return f"{self.link}#satir={no}"


def _harf(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class SheetsTablo:
    """Google Sheets API v4 (rclone OAuth token'i, drive kapsami). ONAY kolonu onay kutusu (BOOLEAN)."""
    tur = "sheets"
    API = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self, sheet_id, token):
        import requests
        self.id = sheet_id
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        self.link = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        self.son = _harf(len(KOLON))

    def _c(self, method, yol, **kw):
        for i in range(5):
            r = self.s.request(method, f"{self.API}/{self.id}{yol}", timeout=60, **kw)
            if r.status_code in (429, 500, 502, 503) and i < 4:
                time.sleep(2 ** i + 1)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Sheets {method} -> {r.status_code}: {r.text[:200]}")
            return r.json() if r.text else {}
        raise RuntimeError("Sheets: tekrar siniri")

    def hazirla(self):
        v = self._c("GET", f"/values/A1:{self.son}1").get("values") or []
        if not v or v[0][:len(KOLON)] != KOLON:
            self._c("PUT", f"/values/A1:{self.son}1", params={"valueInputOption": "RAW"}, json={"values": [KOLON]})
        return self

    def satirlar(self):
        v = self._c("GET", f"/values/A2:{self.son}", params={"valueRenderOption": "FORMATTED_VALUE"}).get("values") or []
        return [dict({k: (r[i] if i < len(r) else "") for i, k in enumerate(KOLON)}, _no=n + 2) for n, r in enumerate(v)]

    def ekle(self, d):
        no = len(self.satirlar()) + 2
        self._c("PUT", f"/values/A{no}:{self.son}{no}", params={"valueInputOption": "RAW"},
                json={"values": [[d.get(k, "") if k != "ONAY" else False for k in KOLON]]})
        onay_kol = KOLON.index("ONAY")
        self._c("POST", ":batchUpdate", json={"requests": [{"setDataValidation": {
            "range": {"sheetId": 0, "startRowIndex": no - 1, "endRowIndex": no,
                      "startColumnIndex": onay_kol, "endColumnIndex": onay_kol + 1},
            "rule": {"condition": {"type": "BOOLEAN"}, "strict": True}}}]})
        return no

    def guncelle(self, no, d):
        data = [{"range": f"{_harf(KOLON.index(k) + 1)}{no}", "values": [[v]]} for k, v in d.items() if k in KOLON]
        if data:
            self._c("POST", "/values:batchUpdate", json={"valueInputOption": "RAW", "data": data})

    def satir_link(self, no):
        return f"{self.link}#gid=0&range=A{no}"


class DriveCsvTablo(YerelTablo):
    """Sheets API kapaliysa: Drive'da Google Sheets dosyasi, Drive API ile CSV olarak disa/ice aktarilir
    (yazmadan hemen once son hali okunur, yalniz ilgili hucreler degisir; ONAY kolonuna 'EVET' yazilir)."""
    tur = "drive_csv"

    def __init__(self, sheet_id, token):
        import requests
        self.id = sheet_id
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        self.link = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

    def _oku(self):
        r = self.s.get(f"https://www.googleapis.com/drive/v3/files/{self.id}/export", params={"mimeType": "text/csv"}, timeout=60)
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8"))))
        return [{k: x.get(k, "") for k in KOLON} for x in rows]

    def _yaz(self, rows):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=KOLON)
        w.writeheader()
        w.writerows(rows)
        r = self.s.patch(f"https://www.googleapis.com/upload/drive/v3/files/{self.id}", params={"uploadType": "media"},
                         data=buf.getvalue().encode("utf-8"), headers={"Content-Type": "text/csv"}, timeout=60)
        r.raise_for_status()

    def hazirla(self):
        try:
            self._oku()
        except Exception:                                    # noqa: BLE001 - bos dosya
            self._yaz([])
        return self

    def satirlar(self):
        return [dict(r, _no=i + 2) for i, r in enumerate(self._oku())]

    def ekle(self, d):
        rows = self._oku()
        rows.append({k: d.get(k, "") for k in KOLON})
        self._yaz(rows)
        return len(rows) + 1

    def guncelle(self, no, d):
        rows = self._oku()
        rows[no - 2].update({k: v for k, v in d.items() if k in KOLON})
        self._yaz(rows)

    def satir_link(self, no):
        return f"{self.link}#gid=0&range=A{no}"


def _drive_klasor_id(tok, yol):
    """gdrive:ASTROLOVE/TEMP/SIPARIS -> klasor id (rclone mkdir + lsjson)."""
    subprocess.run(["rclone", "mkdir", yol], check=True, capture_output=True)
    ust, ad = yol.rsplit("/", 1)
    r = subprocess.run(["rclone", "lsjson", ust, "--dirs-only"], check=True, capture_output=True, text=True)
    return next(x["ID"] for x in json.loads(r.stdout) if x["Name"] == ad)


def tablo_ac(spec):
    """'yerel:<csv>' | 'csv:<ad>' (Drive CSV-donusumlu tablo; Serdar karari 25 Eyl) | 'sheets:<ad>'
    (Drive TEMP/SIPARIS altinda; yoksa olusturulur) -> tablo."""
    tur, _, deger = spec.partition(":")
    if tur == "yerel":
        return YerelTablo(deger)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pinterest"))
    import requests
    from pin_media_perms import access_token
    tok = access_token()
    klasor = _drive_klasor_id(tok, DRIVE_KOK)
    h = {"Authorization": f"Bearer {tok}"}
    q = f"name = '{deger or TABLO_AD}' and '{klasor}' in parents and trashed = false"
    r = requests.get("https://www.googleapis.com/drive/v3/files", params={"q": q, "fields": "files(id,mimeType)"}, headers=h, timeout=60)
    r.raise_for_status()
    f = (r.json().get("files") or [None])[0]
    if not f:
        r = requests.post("https://www.googleapis.com/drive/v3/files", headers=h, timeout=60,
                          json={"name": deger or TABLO_AD, "parents": [klasor], "mimeType": "application/vnd.google-apps.spreadsheet"})
        r.raise_for_status()
        f = r.json()
    if tur == "csv":
        return DriveCsvTablo(f["id"], tok).hazirla()
    try:
        return SheetsTablo(f["id"], tok).hazirla()
    except RuntimeError as e:
        if "403" in str(e) or "SERVICE_DISABLED" in str(e):
            print("::warning::Sheets API kullanilamadi (403); Drive CSV-donusumlu tablo kullaniliyor", flush=True)
            return DriveCsvTablo(f["id"], tok).hazirla()
        raise


# ------------------------------------------------------------------ kargo secimi + net kar (Serdar, 25 Eyl 2026)
def kargo_sec(secenekler):
    """Prodigi teklif secenekleri [{yontem, kalem, kargo, vergi, lab}] -> EN UCUZ (kalem + kargo + vergi + tesisin ekstrasi).
    Ulke bazli sabit secim YOK: TR'de Budget, CA'da Standard pahali cikabilir."""
    ok = [x for x in secenekler or [] if x.get("kalem") is not None and x.get("kargo") is not None]
    if not ok:
        return None
    return min(ok, key=lambda x: round(float(x["kalem"]) + float(x["kargo"]) + float(x.get("vergi") or 0)
                                       + ekstra(x.get("lab"))[0], 2))


def net_kar(fiyat, urun, kargo, vergi, offsite=0.0, adet=1, ekstra_usd=0.0):
    """net = fiyat - (0.582 x adet + 0.176 x fiyat) - urun - kargo - Prodigi vergisi - Offsite Ads kesintisi
    - paket ekstralari (kartpostal + 2 sticker)."""
    return round(float(fiyat) - (ETSY_SABIT * adet + ETSY_ORAN * float(fiyat)) - float(urun) - float(kargo)
                 - float(vergi or 0) - float(offsite or 0) - float(ekstra_usd or 0), 2)


def kar_alanlari(fiyat, secenekler, offsite=None, adet=1, ulke=""):
    """Tablo alanlari: FIYAT, KARGO (secilen + digerleri + ekstra), NET_KAR, KAR_UYARI. offsite None = okunamadi.
    NET_KAR ekstralar DUSULMUS haldedir."""
    sec = kargo_sec(secenekler)
    ek, ek_kaynak, ek_not = ekstra((sec or {}).get("lab"))
    if not sec:
        return {"FIYAT": f"{float(fiyat):.2f}", "KARGO": "", "NET_KAR": "",
                "KAR_UYARI": "TEKLIF ALINAMADI (net hesaplanmadi)"}, None
    net = net_kar(fiyat, sec["kalem"], sec["kargo"], sec.get("vergi"), offsite or 0, adet, ek)
    digerleri = ", ".join(f"{x['yontem']} {float(x['kalem']) + float(x['kargo']) + float(x.get('vergi') or 0):.2f}"
                          for x in secenekler if x is not sec)
    uyari = [ZARAR] if net < 0 else []
    if offsite is None:
        uyari.append("Offsite Ads okunamadi (dusulmedi)")
    if ek_not:
        uyari.append(ek_not)
    return {"FIYAT": f"{float(fiyat):.2f}",
            "KARGO": f"{sec['yontem']} {float(sec['kargo']):.2f} (urun {float(sec['kalem']):.2f}, vergi "
                     f"{float(sec.get('vergi') or 0):.2f}, ekstra {ek:.2f} [{ek_kaynak}], tesis {sec.get('lab') or '?'})"
                     + (f" | diger: {digerleri}" if digerleri else ""),
            "NET_KAR": f"{net:.2f}" + (f" (offsite -{float(offsite):.2f})" if offsite else ""),
            "KAR_UYARI": "; ".join(uyari)}, sec


def kar_metni(satir):
    """Bildirim satiri icin: 'net 12.34 USD' ya da '🔴 ZARAR: net -1.28 USD'."""
    net = str(satir.get("NET_KAR") or "").split(" ")[0]
    if not net:
        return f"net kar: {satir.get('KAR_UYARI') or 'hesaplanmadi'}"
    uy = satir.get("KAR_UYARI") or ""
    ek = ((f" | {NOT_EKSTRA_YOK}" if NOT_EKSTRA_YOK in uy else " (kartpostal+sticker dusulmus)")
          + f" | kargo {str(satir.get('KARGO') or '').split(' (')[0]}")
    return (f"{ZARAR}: net {net} USD" if ZARAR in uy else f"net kar {net} USD") + ek


# ------------------------------------------------------------------ bildirim (yalniz kod + link)
BILDIRIMLER = []           # bu kosudaki bildirimler (kod); varsa kosu bilincli basarisiz biter -> e-posta


def bildir(baslik, k, metin, linkler=None):
    """GitHub ::error satiri -> kosu basarisiz e-postasi. Musteri verisi YOK: opak kod + Drive linkleri."""
    BILDIRIMLER.append(k)
    ek = " | ".join(f"{a}: {b}" for a, b in (linkler or {}).items() if b)
    print(f"::error title={baslik} {k}::{metin}" + (f" | {ek}" if ek else ""), flush=True)


# ------------------------------------------------------------------ 1-2: kayit ac (router koruma blogundan)
def kayit_ac(tablo, rid, receipt, kalemler, urun="POD"):
    """Tabloda satir yoksa acar. -> (kod, durum, uretilecek_mi). Tekrar cagrida mevcut satiri dondurur."""
    import kisisel_siparis as K
    k = kod(rid)
    for r in tablo.satirlar():
        if r.get("KOD") == k:
            return k, r.get("DURUM"), False
    ulke = (receipt.get("country_iso") or "").upper()
    kl = kalemler[0]
    kk = K.kalem_kontrol(kl, ulke)
    coklu = len(kalemler) > 1
    temiz = kk["temiz"] and not coklu
    sablon = kk["sablonlar"] + ([] if temiz else [1])
    on = "TAMAM" if temiz else ("ELLE: birden cok kisisel kalem" if coklu else
                                "MUSTERIYE MESAJ GEREKLI: " + ",".join(kk["kodlar"] + (["ELLE"] if kk["elle"] else [])))
    tablo.ekle({"KOD": k, "RECEIPT": str(rid), "TARIH_UTC": time.strftime("%Y-%m-%d %H:%M", time.gmtime()),
                "URUN": urun, "CIFT": kl.get("pair", ""), "RENK": kl.get("ed", ""), "BOY": kl.get("size", ""),
                "ISIM1": kk["bas1"] or kk["isim1"], "ISIM2": kk["bas2"] or kk["isim2"], "MESAJ": kk["mesaj"], "ULKE": ulke,
                "ON_KONTROL": on, "SABLON": ",".join(str(x) for x in sorted(set(sablon))) if not temiz else "1",
                "ONAY": "", "DURUM": D_DOSYA if temiz else D_MESAJ,
                "NOT": "; ".join(kk["elle"])[:200]})
    return k, (D_DOSYA if temiz else D_MESAJ), temiz


# ------------------------------------------------------------------ 3: uretim sonucu (workflow adimi)
def drive_link(yol, klasor=False):
    r = subprocess.run(["rclone", "lsjson", yol] + (["--dirs-only"] if klasor else []), capture_output=True, text=True)
    if r.returncode:
        return ""
    if klasor:
        ust = subprocess.run(["rclone", "lsjson", yol.rsplit("/", 1)[0], "--dirs-only"], capture_output=True, text=True)
        f = next((x for x in json.loads(ust.stdout or "[]") if x["Name"] == yol.rsplit("/", 1)[1]), None)
        return f"https://drive.google.com/drive/folders/{f['ID']}" if f else ""
    f = (json.loads(r.stdout or "[]") or [None])[0]
    return f"https://drive.google.com/file/d/{f['ID']}/view" if f else ""


def uretildi(tablo, rid, rapor, link=drive_link, kok=DRIVE_KOK):
    """KAPI_RAPORU.json (siparis_dosyasi.py) -> tablo: linkler + ONAY_BEKLIYOR ya da HATA; bildirim."""
    k = kod(rid)
    satir = next((r for r in tablo.satirlar() if r.get("KOD") == k), None)
    if not satir:
        bildir("SIPARIS HATA", k, "uretim sonucu var ama tabloda satir yok")
        return D_HATA
    if satir.get("DURUM") != D_DOSYA:
        return satir.get("DURUM")                       # tekrar: dokunma
    urun = rapor.get("urun") or satir.get("URUN")
    boy = rapor.get("boy") or satir.get("BOY")
    ok = rapor.get("durum") in ("URETILDI", "BEKLIYOR") and rapor.get("kapilar_gecti") is not False and not rapor.get("hata")
    base = f"{kok}/{rid}"
    L = {"KONTROL_KLASOR": link(f"{base}/KONTROL", klasor=True),
         "BASKI": link(f"{base}/BASKI_{boy}.jpg") if urun == "POD" else link(base, klasor=True),
         "ISIM_x3": link(f"{base}/KONTROL/ISIM_BANDI_x3.jpg"), "MESAJ_x3": link(f"{base}/KONTROL/MESAJ_BANDI_x3.jpg")}
    kp = rapor.get("kartpostal") or {}
    kart_not = ""
    if urun == "POD":
        if kp.get("PASS"):
            L["KARTPOSTAL"] = link(f"{base}/KONTROL/{KART_AD}")
        else:
            kart_not = f"KARTPOSTAL YOK ({kp.get('neden') or 'uretilmedi'}): Prodigi'ye panel karti gider"
    durum = D_ONAY if ok else D_HATA
    tablo.guncelle(satir["_no"], {**L, "DURUM": durum,
                                  "NOT": "; ".join(x for x in ([] if ok else [f"uretim: {rapor.get('durum')} kapi={rapor.get('kapilar')} {str(rapor.get('hata') or '')[:120]}"]) + [kart_not] if x)})
    ozet = f"{urun} {satir.get('RENK', '')} {boy}".strip()
    linkler = {"isim x3": L["ISIM_x3"], "mesaj x3": L["MESAJ_x3"], "tam cozunurluk": L["BASKI"],
               "kartpostal": L.get("KARTPOSTAL", ""), "KONTROL": L["KONTROL_KLASOR"], "tablo satiri": tablo.satir_link(satir["_no"])}
    if ok:
        zarar = ZARAR in (satir.get("KAR_UYARI") or "")
        bildir("ONAY BEKLIYOR - ZARAR" if zarar else "ONAY BEKLIYOR", k,
               f"{ozet}: {kar_metni(satir)} | baski dosyasi" + (" + kisiye ozel kartpostal" if L.get("KARTPOSTAL") else "")
               + " hazir, kontrol edip ONAY sutununa EVET yazin" + (f" | {kart_not}" if kart_not else "")
               + (" (ZARARINA SIPARIS: otomatik gonderim yok, karar Serdar'in)" if zarar else ""), linkler)
    else:
        bildir("SIPARIS HATA", k, f"{ozet}: baski dosyasi uretilemedi / kapi gecilmedi (DUR)", linkler)
    return durum


# ------------------------------------------------------------------ 6-7: onay izleyici (router her kosuda)
def onay_izle(tablo, st, submit, upd, gizli_rapor, dry_run=False):
    """ONAY isaretli + ONAY_BEKLIYOR satirlar. submit(rid) -> (ok, hata, prodigi_id). -> hata listesi (yalniz kod).
    Idempotent: STATE ordered/shipped/tracked ya da tablo PRODIGI dolu -> tekrar gonderilmez."""
    hatalar = []
    for r in tablo.satirlar():
        if r.get("DURUM") != D_ONAY or not onayli(r.get("ONAY")):
            continue
        rid, k = r.get("RECEIPT"), r.get("KOD")
        row = st.get(str(rid)) or {}
        if (r.get("URUN") or "POD") == "POD":
            if row.get("stage") in ("ordered", "shipped", "tracked") or r.get("PRODIGI"):
                tablo.guncelle(r["_no"], {"DURUM": D_PRODIGI, "PRODIGI": r.get("PRODIGI") or row.get("prodigi_order_id", "")})
                gizli_rapor.append(f"- {rid}: zaten gonderilmis (tekrar yok)")
                continue
            if dry_run:
                gizli_rapor.append(f"- {rid}: (kuru) ONAY var, Prodigi'ye gonderilmedi")
                continue
            ok, hata, oid = submit(str(rid))
            if ok:
                tablo.guncelle(r["_no"], {"DURUM": D_PRODIGI, "PRODIGI": oid, "NOT": ""})
                bildir("PRODIGI GONDERILDI", k, f"onayli POD siparisi Prodigi'de (pause: elle serbest birakilir) | {kar_metni(r)}",
                       {"tablo satiri": tablo.satir_link(r["_no"])})
            else:
                tablo.guncelle(r["_no"], {"DURUM": D_HATA, "NOT": f"Prodigi: {str(hata)[:180]}"})
                bildir("SIPARIS HATA", k, "onayli siparis Prodigi'ye GONDERILEMEDI (DUR)", {"tablo satiri": tablo.satir_link(r["_no"])})
                hatalar.append(k)
                break                                        # hata -> DUR
        else:
            if row.get("stage") == "dijital_bekliyor":
                continue
            if not dry_run:
                upd(st, str(rid), stage="dijital_bekliyor", note="onayli; ChatGPT yukleme bekliyor")
            tablo.guncelle(r["_no"], {"DURUM": D_CHATGPT})
            bildir("CHATGPT YUKLEME BEKLIYOR", k, f"onayli {r.get('URUN')} siparisi: dosya ChatGPT uzerinden yuklenecek",
                   {"KONTROL": r.get("KONTROL_KLASOR"), "tablo satiri": tablo.satir_link(r["_no"])})
    return hatalar


# ------------------------------------------------------------------ dijital siparis kalemleri
BURCLAR = ["AQUARIUS", "PISCES", "ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO",
           "SAGITTARIUS", "CAPRICORN"]


def dijital_kalemler(receipt):
    """POD disi (is_digital) kisisellestirilmis kalemler; cift SKU yoksa basliktaki iki burc adindan (siraya gore).
    urun: baslikta 'wallpaper' geciyorsa DUVAR_KAGIDI, degilse DIJITAL."""
    import re
    import kisisel_siparis as K
    out = []
    for t in receipt.get("transactions") or []:
        if not t.get("is_digital"):
            continue
        alan = K._kisisel_alanlar(t)
        if not alan:
            continue
        baslik = (t.get("title") or "").upper()
        bul = sorted(((m.start(), b) for b in BURCLAR for m in re.finditer(rf"\b{b}\b", baslik)))
        burc = [b for _, b in bul]
        if len(burc) == 1:
            burc = burc * 2
        if len(burc) < 2:
            continue
        out.append({"transaction_id": t.get("transaction_id"), "sku": t.get("sku") or "DIJITAL", "pair": f"{burc[0]}_{burc[1]}",
                    "ed": "", "size": "-", "qty": int(t.get("quantity") or 1), "alanlar": alan,
                    "urun": "DUVAR_KAGIDI" if "WALLPAPER" in baslik else "DIJITAL"})
    return out


# ------------------------------------------------------------------ kisiye ozel kartpostal (uretim isi)
def uretim_girdisi(md):
    """Siparis kartindaki '## Uretim girdisi' blogu -> {cift, renk, boy, isim1, isim2, mesaj, urun}."""
    d, ic = {}, False
    for satir in md.splitlines():
        if satir.startswith("## "):
            ic = satir.strip().lower().startswith("## uretim girdisi")
            continue
        if ic and satir.startswith("- ") and ":" in satir:
            k, _, v = satir[2:].partition(":")
            d[k.strip().lower()] = v.strip()
    return d


def kartpostal_hazirla(rid, md, cikti_kok, font, indir):
    """POD siparisi icin kart: cikti_kok/<rid>/KARTPOSTAL_A6.jpg + KARTPOSTAL_qc.json (isim YOK).
    indir(uzak, yerel) -> bool. -> qc dict {PASS, neden, kapilar}."""
    import kartpostal as KP
    g = uretim_girdisi(md)
    hedef = pathlib.Path(cikti_kok) / str(rid)
    hedef.mkdir(parents=True, exist_ok=True)
    if (g.get("urun") or "pod").lower() != "pod":
        qc = {"PASS": False, "neden": "POD degil"}
    elif not g.get("cift") or not g.get("isim1"):
        qc = {"PASS": False, "neden": "uretim girdisi eksik (cift/isim)"}
    else:
        poster, kaynak = hedef / "_POSTER_AM.png", hedef / "_KART_KAYNAK.jpg"
        if not indir(f"{A1_77}/{g['cift']}/POSTER_AM.png", poster):
            qc = {"PASS": False, "neden": f"POSTER_AM yok ({g['cift']})"}
        elif not indir(KART_KAYNAK, kaynak):
            qc = {"PASS": False, "neden": "kaynak kart yok"}
        else:
            try:
                qc = KP.kartpostal_uret(kaynak, poster, font, KP.kart_metni(g["isim1"], g.get("isim2")), hedef / KART_AD)
                qc["neden"] = "" if qc["PASS"] else "QC FAIL: " + ",".join(k for k, v in qc["kapilar"].items() if not v)
            except Exception as e:                       # noqa: BLE001 - kart yoksa siparis durmaz, bildirimde yazar
                qc = {"PASS": False, "neden": f"uretim hatasi {type(e).__name__}"}
        for f in (poster, kaynak):
            f.unlink(missing_ok=True)
    (hedef / "KARTPOSTAL_qc.json").write_text(json.dumps(qc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return qc


def _rclone_indir(uzak, yerel):
    try:
        return subprocess.run(["rclone", "copyto", uzak, str(yerel)], capture_output=True).returncode == 0 \
            and pathlib.Path(yerel).exists()
    except OSError:
        return False


# ------------------------------------------------------------------ CLI (workflow adimlari)
def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=["uretildi", "kartpostal"])
    ap.add_argument("--font", default="_work/Cinzel.ttf")
    ap.add_argument("--tablo", default=f"csv:{TABLO_AD}")
    ap.add_argument("--rid-dosya", required=True, help="uretilen receipt listesi (satir basina bir)")
    ap.add_argument("--rapor-kok", required=True, help="yerel: <kok>/<rid>/KAPI_RAPORU.json")
    ap.add_argument("--drive-kok", default=DRIVE_KOK)
    a = ap.parse_args()
    if a.mod == "kartpostal":                            # Drive: SIPARIS_ISIM/<rid>.md -> SIPARIS/<rid>/KARTPOSTAL_A6.jpg (+ KONTROL)
        for rid in [x.strip() for x in pathlib.Path(a.rid_dosya).read_text().split() if x.strip()]:
            r = subprocess.run(["rclone", "cat", f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{rid}.md"], capture_output=True, text=True)
            qc = kartpostal_hazirla(rid, r.stdout if r.returncode == 0 else "", a.rapor_kok, a.font, _rclone_indir)
            if qc.get("PASS"):
                yerel = pathlib.Path(a.rapor_kok) / rid / KART_AD
                for uzak in (f"{a.drive_kok}/{rid}/{KART_AD}", f"{a.drive_kok}/{rid}/KONTROL/{KART_AD}"):
                    subprocess.run(["rclone", "copyto", str(yerel), uzak, "-q"], check=False)
            print(f"{kod(rid)}: kartpostal {'PASS' if qc.get('PASS') else 'YOK - ' + str(qc.get('neden'))}", flush=True)
        sys.exit(0)
    tablo = tablo_ac(a.tablo)
    hata = 0
    for rid in [x.strip() for x in pathlib.Path(a.rid_dosya).read_text().split() if x.strip()]:
        p = pathlib.Path(a.rapor_kok) / rid / "KAPI_RAPORU.json"
        rapor = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"durum": "HATA", "hata": "KAPI_RAPORU yok"}
        kq = pathlib.Path(a.rapor_kok) / rid / "KARTPOSTAL_qc.json"
        if kq.exists():
            rapor["kartpostal"] = json.loads(kq.read_text(encoding="utf-8"))
        d = uretildi(tablo, rid, rapor, kok=a.drive_kok)
        print(f"{kod(rid)}: {d}", flush=True)
        hata += d == D_HATA
    sys.exit(1 if hata or BILDIRIMLER else 0)       # bildirim varsa bilincli basarisiz (e-posta)


if __name__ == "__main__":
    main()
