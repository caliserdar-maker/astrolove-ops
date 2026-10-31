#!/usr/bin/env python3
"""Kupa 78 (Orchard) galeri yukleyicisi: 14 gorsel + 1 video + Style bagi; ayni burc ciftlerinde (12) metin "First Name" / "Second Name".
Serdar gece istisnasi 30 Eki. KOSTURMA AYRI ONAYLA (kuru da). Poster yukleyicilerinin kanitli parcalari: eski78_gorsel_yukle
(yukle_guvenli: cift yukleme yok, stabil galeri, Kayit DEVAM), galeri_ci11 (plan kilidi, canli == plan, sadece / haric, geri alma),
video_yukle_78 v7 (tek gonderim, yeni video active olmadan eski silinmez).
Hedef galeri: 1 kapak (KUPA_GALERI_KAYNAK/<damga>/kapak/KUPA_KAPAK_<CIFT>.jpg), 2-6 kartlar (KUPA_KART78/<damga>/<CIFT>_K0N.jpg,
MANIFEST.csv galeri_no: K02=2 K03=3 K05=4 K07=5 K04=6, durum PASS, sha256), 7-14 stiller (KUPA_STIL78/<damga>/
KUPA_STIL_<CIFT>_<NN>_<KISA>.jpg: 7 Orange Blossom ... 14 Golden Loquat), video KUPA_GALERI_KAYNAK/<damga>/video/KUPA_VIDEO_<CIFT>.mp4.
Style (property 513) degerleri -> sira 7-14 (TEK variation-images POST'u, tum seti degistirir).
Modlar (alt komut):
  kaynak : ETSY YOK. Kaynak dosyalari (sha256, bayt, JPEG / MP4 imzasi, kart MANIFEST, kapak KAYIT.tsv) -> KAYNAK.csv.
  kuru   : ETSY SALT OKUMA (yd_envanter_oku.salt_okur). Ilan basina 6 GET (ilan, galeri, video, Style baglari, envanter,
           kisisellestirme) + ayni burcta RU ceviri okumasi (yalniz bilgi). HAZIR ilanlar PLAN_KUPA78.json; plan sha256 -> plan_damga.
  yedek  : ETSY YOK (yalniz etsystatic CDN). Plandaki eski gorseller + video indirilir; <ilan>_<CIFT>/YEDEK.json (kimlik, rank, alt
           metin, Style baglari (ad + value_id + image_id + rank), video, ayni burcta eski aciklama + kisisellestirme, dosya sha256 +
           md5). ZAMAN DAMGASIZ (ayni plan -> ayni bayt; --immutable devam kosusunda da gecer); kosu zamani --out/YEDEK_OZET.csv.
           Bayt imzasi (JPEG FFD8FF / MP4 ftyp) tutmayan indirme FAIL (HTML hata sayfasi yedek sayilmaz). --yedek-liste (lsjson -R
           --hash) + --yedek-var-dir (Drive'daki YEDEK.json'lar): Drive'da tam ve hash'i tutan yedegi olan ilan ATLANIR (VAR, CDN'e
           gidilmez; islenmis ilanin eski adresi 404 olabilir). Ayri is akisi kupa-galeri78-hazir (KILITSIZ, Etsy token yok).
  parti  : ETSY YOK. Plan + DEVAM (ilan basina DEVAM_<ilan>.json dahil) + ILERLEME -> bu kosunun ilanlari (--azami-ilan, varsayilan
           15) ve yalniz onlarin dosya listeleri (is akisi yalniz partinin dosyalarini indirir).
  yaz    : ETSY'YE YAZAR (--confirm KUPA_GALERI78 + --plan + --plan-damga + alt metin ONAYLI). Ilan basina: kota (kalan - en kotu
           istek >= KOTA_SINIRI 10; ilk ilandan once tek ucuz GET ile kalan okunur) -> 6 GET -> canli == plan (DEVAM'da uzlasma) ->
           YEDEK KAPISI (YEDEK.json + Drive lsjson --hash'te her dosya ayni boyut + md5 / sha256; yoksa yazim yok) -> galeri (sil / yukle 20 siniri, Style bagi yeni 7-14'e, eski bagli gorseller bag
           kurulduktan SONRA silinir, sira kontrolu) -> video (yeni active olmadan eski silinmez) -> metin (state active okunur,
           PATCH description + kisisellestirme POST) -> son geri okuma. Tutmazsa GERI ALMA (YEDEK'ten: eski gorseller ayni sira ve alt
           metinle, Style baglari ada gore, eski video, eski metin). Kota tabani durmasi geri alma yapmaz (DEVAM + kota_durdu
           kaydi; sonraki kosu surdurur ya da geri_al modu geri alir). DEVAM_<ilan>.json her yukleme oncesi / sonrasi Drive'a
           (--devam-hedef-kok): kosu ilan ortasinda olse de yeni gorsel kimlikleri kayitta (devam ve geri_al --devam-ilan-dir ile okur).
           Ilk PASS / ZATEN olmayan ilanda kosu durur (sonrakiler KALAN).
  geri_al: ETSY'YE YAZAR (--confirm KUPA_GALERI78_GERI + --sadece). Ayni geri alma yolu, elle (YEDEK.json + dosyalar).
METIN (aciklama + kisisellestirme) VARSAYILAN KAPALI (--metin-yaz): kupa icin onayli RU kurucusu yok; EN "First Name" olur RU eski
kalirsa CLAUDE.md "RU = EN" kurali bozulur. Galeri isi metinden ayri. Metin acikken: yasak ifade kapisi pod_5x7_kuru.YASAK_EN +
etsy_common.RU_YASAK (metin_kurali.py main'de yok), kisisellestirme canli okunur, tek soru degilse BLOK, question_id korunur.
updateListing yalniz state active okunduktan sonra (CLAUDE.md 7 Eyl: taslagi yayina alir).
Istek tahmini: istek_tahmini() (kod yollarindan sayim; GET 5xx / 429 kisa tekrarlari dahil degil, sert taban her istekten once)."""
import argparse
import copy
import csv
import hashlib
import html
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
import toplu_oku as TO  # noqa: E402  (Serdar 31 Eki 1a: toplu kapi okumasi, ortak)
from etsy_common import KOTA_SINIRI, RU_YASAK  # noqa: E402  (Serdar 15 ve 24 Eki: 10; degistirilmez)
from pod_5x7_kuru import YASAK_EN  # noqa: E402  (urun metni yasaklari; metin_kurali.py main'de yok)

KOK = HERE.parents[1]
ONAY, ONAY_GERI = "KUPA_GALERI78", "KUPA_GALERI78_GERI"
PLAN_AD = "PLAN_KUPA78.json"
BOLUM = 60980873                    # "Zodiac Couple Mugs"
DOKUNMA = {"4597843405"}            # eski 7 stil taslagi (kupa_fiyat / kupa_taslak)
P_STYLE = 513
N = 14
LIMIT = G.IMG_LIMIT                 # Etsy 20 gorsel
STILLER = [("Orange Blossom", 7, "ORANGE"), ("Purple Fig", 8, "FIG"), ("Olive Breeze", 9, "OLIVE"),
           ("Pomegranate Bloom", 10, "POMEGRANATE"), ("Almond Blossom", 11, "ALMOND"), ("Lemon Grove", 12, "LEMON"),
           ("Blue Grape", 13, "GRAPE"), ("Golden Loquat", 14, "LOQUAT")]
BAG_HEDEF = {ad: s for ad, s, _ in STILLER}
KART = {2: "K02", 3: "K03", 4: "K05", 5: "K07", 6: "K04"}
URUN_N = 16                         # 8 stil x 2 boy
BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
CIFTLER = sorted("_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2))
ALT_CSV = KOK / "data" / "pod" / "kupa_galeri78_alt.csv"
YASAK_LISTE = (YASAK_EN, RU_YASAK, re.compile(r"AstroLove(?!Art)"))   # tire, Hahnemuhle, Printful, OBA, cotton, museum, omur yili
KAPI_OKUMA = 6                      # ilan, galeri, video, Style baglari, envanter, kisisellestirme
VIDEO_DENEME, VIDEO_BEKLE = 12, 10  # video_yukle_78 v7 (yeni video active olana dek ~2 dk)
VIDEO_MB = 100
CDN = ("https://i.etsystatic.com/", "https://v.etsystatic.com/")
SORU_ALAN = ("question_text", "question_type", "required", "max_allowed_characters", "instructions", "options")
ISTEK_ALAN = ("en_az", "en_kotu")   # bilgi: kod surumuyle degisir; canli = plan karsilastirmasina girmez


def log(m):
    Y.log(m)


def yasak_bul(t):
    return sorted({m.group(0) for r in YASAK_LISTE for m in r.finditer(t or "")})


def jdump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha_metin(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


class Geri(Exception):
    """yazim sonrasi tutarsizlik: geri alma gerekir"""


# ---------------------------------------------------------------- istek tahmini
def istek_tahmini(n_yukle=N, n_sil=N, metin=False, n_rank=N):
    """Kod yollarindan sayim (O = G.OKUMA_TEKRAR). Yazim en kotu: etsy_common 3 gonderim (5xx) + 401 yenilemesi = 4;
    post_file tekrar=1 + 401 = 2 / deneme, yukle_guvenli 2 deneme + hata sonrasi kararli galeri (O); sira POST post_file tekrar=3 + 401 = 4.
      kapi       : 6 GET (ilan, galeri, video, bag, envanter, kisisellestirme)
      yukle      : en az 1 | en kotu (2 + 1) + (2 + O)
      sil        : en az 1 | en kotu 4
      bag        : en az 2 (POST + var_img) | en kotu 4 + O   (SIRALI plan, Serdar 31 Eki 1a: EN SONDA TEK KEZ)
      sira       : en az 1 (galeri, oturdu) | en kotu O + 2 x (n_rank x 4 + O)   (sira gecisi bagi ayrica yazmaz; bag sonda)
      video      : en az 5 (video okuma, POST, active okuma, DELETE, son video okuma) | en kotu 1 + (2 + O) + VIDEO_DENEME + 4 + O
      metin      : en az 4 (ilan GET, kisisellestirme GET, PATCH, POST) | en kotu 2 + 4 + 4
      son okuma  : en az 6 (galeri, bag, video, ilan, envanter, kisisellestirme) | en kotu 3 x O + 3
      geri alma  : kapi 6 + n_sil yeniden yukleme (ilanin GERCEK eski gorsel sayisi; en kotu hepsi silinmis) + n_yukle sil + bag +
                   sira (n_sil gorsel) + video + metin + son okuma (en kotu; FAIL yolunda bir kez)
    n_sil = plandaki eski gorsel sayisi (14 sabiti DEGIL; inceleme 30 Eki madde 5). -> dict(en_az, en_kotu_geri_almasiz, geri_alma, en_kotu)"""
    O = G.OKUMA_TEKRAR
    yk_az, yk_k = 1, (2 + 1) + (2 + O)
    bag_az, bag_k = 2, 4 + O
    sira_az, sira_k = 1, O + 2 * (n_rank * 4 + O)
    vid_az, vid_k = 5, 1 + (2 + O) + VIDEO_DENEME + 4 + O
    met_az, met_k = (4, 10) if metin else (0, 0)
    son_az, son_k = 6, 3 * O + 3
    az = KAPI_OKUMA + n_yukle * yk_az + n_sil * 1 + bag_az + sira_az + vid_az + met_az + son_az
    kotu = KAPI_OKUMA + n_yukle * yk_k + n_sil * 4 + bag_k + sira_k + vid_k + met_k + son_k
    geri_sira_k = O + 2 * (n_sil * 4 + O)
    geri = KAPI_OKUMA + n_sil * yk_k + n_yukle * 4 + bag_k + geri_sira_k + vid_k + met_k + son_k
    return dict(en_az=az, en_kotu_geri_almasiz=kotu, geri_alma=geri, en_kotu=kotu + geri, okuma_tekrar=O)


# ---------------------------------------------------------------- liste, kapsam, alt metin
def ad_burc(b):
    return b.capitalize()


def liste_oku(yol):
    rows = [dict(cift=r["cift"].strip(), listing_id=str(r["listing_id"]).strip())
            for r in csv.DictReader(open(yol, encoding="utf-8-sig")) if (r.get("listing_id") or "").strip()]
    if len(rows) != 78 or sorted(r["cift"] for r in rows) != CIFTLER or len({r["listing_id"] for r in rows}) != 78:
        raise SystemExit(f"DUR: kupa listesi {len(rows)} satir / cift kumesi 78 Orchard ciftiyle ayni degil")
    if any(not r["listing_id"].isdigit() for r in rows):
        raise SystemExit("DUR: kupa listesinde rakam disi listing_id")
    if {r["listing_id"] for r in rows} & DOKUNMA:
        raise SystemExit("DUR: kupa listesinde DOKUNMA ilani (eski taslak)")
    for r in rows:
        a, b = r["cift"].split("_")
        r.update(a=ad_burc(a), b=ad_burc(b))
    return rows


def kapsam(rows, sadece, haric):
    sa = {x.strip() for x in (sadece or "").split(",") if x.strip()}
    ha = {x.strip() for x in (haric or "").split(",") if x.strip()}
    bilinmeyen = (sa | ha) - {r["listing_id"] for r in rows}
    if bilinmeyen:
        raise SystemExit(f"DUR: sadece / haric listesinde 78 disi ilan: {sorted(bilinmeyen)}")
    return [r for r in rows if (not sa or r["listing_id"] in sa) and r["listing_id"] not in ha]


def alt_oku(yol):
    rows = {int(r["sira"]): r for r in csv.DictReader(open(yol, encoding="utf-8-sig"))}
    if sorted(rows) != list(range(1, N + 1)):
        raise SystemExit(f"DUR: alt metin sablonu {yol}: sira 1..{N} degil")
    return rows


def alt_onayli(alt):
    return all((r.get("durum") or "").strip() == "ONAYLI" for r in alt.values())


def alt_metin(r, a, b):
    ayni = a.lower() == b.lower()
    t = (r.get("alt_ayni_burc") or "").strip() if ayni else ""
    return " ".join((t or r["alt"]).replace("<A>", a).replace("<B>", b).split())


def alt_gecerli(t):
    return 0 < len(t or "") <= 250 and not Y.YASAK_ALT.search(t) and not yasak_bul(t) and "<" not in t


# ---------------------------------------------------------------- kaynak dosyalar (ETSY YOK)
def kaynak_yollari(cift):
    d = {1: f"kapak/KUPA_KAPAK_{cift}.jpg"}
    d.update({s: f"kart/{cift}_{k}.jpg" for s, k in KART.items()})
    d.update({s: f"stil/KUPA_STIL_{cift}_{s:02d}_{kisa}.jpg" for _, s, kisa in STILLER})
    d["video"] = f"video/KUPA_VIDEO_{cift}.mp4"
    return d


def imza_ok(p, video):
    with open(p, "rb") as f:
        b = f.read(12)
    return b[4:8] == b"ftyp" if video else b[:3] == b"\xff\xd8\xff"


def kaynak_kur(rows, kok, kart_manifest, kapak_kayit):
    """-> KAYNAK satirlari (listing_id, cift, sira, dosya, sha256, bayt, durum, neden)"""
    kok = Path(kok)
    man = {}
    for r in csv.DictReader(open(kart_manifest, encoding="utf-8-sig")):
        man[(r.get("cift"), r.get("kart"))] = r
    kayit = {ln.split("\t")[0].split(" ")[0].strip() for ln in Path(kapak_kayit).read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.startswith("#")}
    out = []
    for r in rows:
        for sira, rel in kaynak_yollari(r["cift"]).items():
            p, neden = kok / rel, []
            s = dict(listing_id=r["listing_id"], cift=r["cift"], sira=sira, dosya=rel, sha256="", bayt=0)
            if not p.is_file():
                neden.append("dosya yok")
            else:
                s.update(sha256=Y.sha256(p), bayt=p.stat().st_size)
                if not s["bayt"] or not imza_ok(p, sira == "video"):
                    neden.append("bos / imza JPEG-MP4 degil")
                if sira == "video" and s["bayt"] > VIDEO_MB * 1024 * 1024:
                    neden.append(f"video > {VIDEO_MB} MB")
            if sira in KART:
                m = man.get((r["cift"], KART[sira]))
                if not m or (m.get("durum") or "").strip() != "PASS" or str(m.get("galeri_no")).strip() != str(sira) \
                        or Path(m.get("dosya") or "").name != Path(rel).name:
                    neden.append(f"kart MANIFEST satiri yok / PASS degil / galeri_no {sira} degil ({KART[sira]})")
                elif s["sha256"] and m.get("sha256") != s["sha256"]:
                    neden.append("kart sha256 MANIFEST'ten farkli")
            if sira == 1 and r["cift"] not in kayit:
                neden.append("kapak KAYIT.tsv'de cift yok")
            s.update(durum="FAIL" if neden else "PASS", neden="; ".join(neden))
            out.append(s)
    return out


KAYNAK_ALAN = ["listing_id", "cift", "sira", "dosya", "sha256", "bayt", "durum", "neden"]


def kaynak_oku(yol):
    d = {}
    for r in csv.DictReader(open(yol, encoding="utf-8")):
        d.setdefault(r["listing_id"], {})[r["sira"]] = r
    return d


def hedef_kur(r, kaynak, alt):
    """-> (hedef [[sira, dosya, sha256, alt]], video [dosya, sha256], neden)"""
    k = kaynak.get(r["listing_id"]) or {}
    neden, hedef = [], []
    for s in range(1, N + 1):
        x = k.get(str(s))
        t = alt_metin(alt[s], r["a"], r["b"])
        if not x or x.get("durum") != "PASS" or x.get("cift") != r["cift"]:
            neden.append(f"kaynak sira {s}: {(x or {}).get('neden') or 'satir yok'}")
        if not alt_gecerli(t):
            neden.append(f"alt metin sira {s} gecersiz")
        hedef.append([s, (x or {}).get("dosya", ""), (x or {}).get("sha256", ""), t])
    v = k.get("video")
    if not v or v.get("durum") != "PASS":
        neden.append(f"kaynak video: {(v or {}).get('neden') or 'satir yok'}")
    if len({h[3] for h in hedef}) != N:
        neden.append("alt metinler tekil degil (yukleme tanima alt metinle)")
    return hedef, [(v or {}).get("dosya", ""), (v or {}).get("sha256", "")], neden


# ---------------------------------------------------------------- ayni burc metni
def isim_degistir(metin, burc):
    """ "Name Under <Burc>" ciftleri ya da canli "Left name" / "Right name" (Serdar 31 Eki 7a; 12 ilanin canli talimati, kupa-yd-oku
    41183072842) -> "First Name" / "Second Name" (sirayla). -> (yeni, durum DEGISTI | ZATEN | YOK | TEK)"""
    metin = metin or ""
    m = list(re.finditer(rf"\bName\s+Under\s+{re.escape(burc)}\b", metin, re.I))
    if not m:
        sol = list(re.finditer(r"\bLeft name\b", metin, re.I)); sag = list(re.finditer(r"\bRight name\b", metin, re.I))
        if sol or sag:
            if len(sol) != len(sag) or any(x.start() > y.start() for x, y in zip(sol, sag)):
                return metin, "TEK"
            yeni = re.sub(r"\bRight name\b", "Second Name", re.sub(r"\bLeft name\b", "First Name", metin, flags=re.I), flags=re.I)
            return yeni, "DEGISTI"
        return metin, ("ZATEN" if "First Name" in metin and "Second Name" in metin else "YOK")
    if len(m) % 2:
        return metin, "TEK"
    par, i = [], 0
    for k, x in enumerate(m):
        par += [metin[i:x.start()], "First Name" if k % 2 == 0 else "Second Name"]
        i = x.end()
    return "".join(par + [metin[i:]]), "DEGISTI"


def soru_norm(q):
    return {k: q.get(k) for k in SORU_ALAN if q.get(k) not in (None, [], "") or k in ("instructions", "required")}


def hedef_en(d0, a, b):
    """Aciklama hedefi TEK KAYNAK ru_kupa (inceleme 31 Eki): metinde foto atfi (eski numarali ya da yeni gorsel adi) varsa galeri_en
    (idempotan; gorsel adi, numara yok, Latin harf notu; Serdar 31 Eki 2a / 6a) + ru_kupa.hedef_kapisi; kapi hatasi = yazim yok.
    Ayni burcta isim satirlari. Foto atfi hic olmayan metin (kupa kalibi disi) galeriye dokunulmadan isim adimina gecer.
    -> (yeni, durum, hata[])."""
    import ru_kupa as RK
    deg = []
    if re.search(r"See (?:photos? |the [a-z]+(?: [a-z]+)* photos?)", d0):
        try:
            d0, deg = RK.galeri_en(d0)
        except ValueError as e:
            return d0, "TEK", [f"metin: galeri foto / Latin kalibi beklenen degil ({e}); yazim yok"]
        h = [f"metin: hedef kapisi: {x}; yazim yok" for x in RK.hedef_kapisi(d0)]
        if h:
            return d0, "TEK", h
    if a.lower() == b.lower():
        d1, dd = isim_degistir(d0, a)
    else:
        d1, dd = d0, "YOK"
    return d1, ("DEGISTI" if deg and dd != "TEK" else dd), []


def metin_plani(L, per, a, b):
    """-> dict(yaz, desc_once, desc_sonra, pers_once, pers_sonra, durum, hata). Aciklama: hedef_en (78 ilan; foto + Latin + ayni burcta
    isim). Kisisellestirme talimati yalniz ayni burcta (isim satirlari)."""
    d0 = html.unescape(L.get("description") or "")
    if a.lower() != b.lower():
        d1, dd, h = hedef_en(d0, a, b)
        h += [f"metin: yeni aciklamada yasak ifade / tire {yasak_bul(d1)[:5]}; yazim yok"] if dd == "DEGISTI" and yasak_bul(d1) else []
        return dict(yaz=dd == "DEGISTI" and not h, durum="FARKLI_BURC" + ("+DEGISTI" if dd == "DEGISTI" else ""), hata=h,
                    desc_once=d0, desc_sonra=d1 if dd == "DEGISTI" else None, pers_once=None, pers_sonra=None)
    d1, dd, h0 = hedef_en(d0, a, b)
    q0 = [soru_norm(q) for q in per or []]
    q1, qd = copy.deepcopy(q0), []
    for q in q1:
        for k in ("question_text", "instructions"):
            q[k], s = isim_degistir(q.get(k) or "", a) if q.get(k) is not None else (q.get(k), "YOK")
            qd.append(s)
    durum = [dd] + qd
    hata = list(h0)
    if "TEK" in durum:
        hata.append("metin: 'Name Under' tek sayida ya da Left / Right name cifti bozuk (cift degil); yazim yok")
    yaz = "DEGISTI" in durum
    if not yaz and "ZATEN" not in durum:
        hata.append("metin: ayni burc ama 'Name Under' / 'Left name - Right name' kalibi da 'First Name / Second Name' de yok; elle bakilmali")
    if not per:
        hata.append("metin: kisisellestirme sorusu okunamadi (0 soru)")
    if len(per or []) > 1:
        hata.append(f"metin: {len(per)} kisisellestirme sorusu (tek soru beklenir; POST tum seti degistirir); BLOK")
    if dd == "DEGISTI" and yasak_bul(d1):
        hata.append(f"metin: yeni aciklamada yasak ifade / tire {yasak_bul(d1)[:5]}; yazim yok")
    yq = yasak_bul(" ".join(str(q.get(k) or "") for q in q1 for k in ("question_text", "instructions")))
    if yq and q1 != q0:
        hata.append(f"metin: yeni kisisellestirmede yasak ifade / tire {yq[:5]}; yazim yok")
    return dict(yaz=yaz, durum="+".join(sorted(set(durum))), hata=hata,
                desc_once=d0, desc_sonra=d1 if dd == "DEGISTI" else None,
                pers_once=q0, pers_sonra=q1 if q1 != q0 else None)


# ---------------------------------------------------------------- canli okuma ve kapilar
def canli_oku(api, shop, lid, onb=None):
    """onb: toplu_oku.toplu sonucu (kapi okumasi); yoksa / ilan yoksa tekil okuma (6 GET). Style baglari her zaman tekil (toplu uc yok)."""
    t = (onb or {}).pop(str(lid), None)
    if t:
        L, g, v, inv, per = t["L"], t["galeri"], t["video"], t["inv"], t["per"]
        vi = G.var_img(api, shop, lid)
    else:
        L = api.get(f"/listings/{lid}") or {}
        g = G.galeri(api, lid)
        v = G.videolar(api, lid)
        vi = G.var_img(api, shop, lid)
        inv = api.get(f"/listings/{lid}/inventory") or {}
        per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    stil, urun = {}, []
    for pr in inv.get("products") or []:
        if pr.get("is_deleted"):
            continue
        urun.append((pr.get("sku"), jdump(pr.get("offerings")), jdump(pr.get("property_values"))))
        for pv in pr.get("property_values") or []:
            if pv.get("property_id") == P_STYLE:
                for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                    stil.setdefault(val, vid)
    return dict(L=L, galeri=g, video=v, bag=vi, stil=stil, urun_n=len(urun), inv_sha=sha_metin(jdump(sorted(urun))), per=per)


TOPLU_ILAN = 2   # ilan basina taze toplu okuma: /listings/batch + /listings/batch/inventory


def toplu_tekil_fark(a, b):
    """canli_ozet alanlari + aciklama / baslik / etiket / kisisellestirme ham karsilastirmasi; -> farkli alan adlari"""
    x, y = canli_ozet(a), canli_ozet(b)
    fk = [k for k in x if x[k] != y.get(k)]
    for k in ("description", "title", "tags", "materials", "state", "shop_section_id", "shipping_profile_id"):
        if a["L"].get(k) != b["L"].get(k):
            fk.append("L." + k)
    if [soru_norm(q) for q in a["per"]] != [soru_norm(q) for q in b["per"]]:
        fk.append("per")
    return sorted(set(fk))


def canli_ozet(c):
    L = c["L"]
    return dict(state=L.get("state"), bolum=L.get("shop_section_id"), title_sha=sha_metin(L.get("title")), tags=list(L.get("tags") or []),
                desc_sha=sha_metin(html.unescape(L.get("description") or "")),
                galeri=[[x.get("rank"), x.get("listing_image_id"), x.get("alt_text") or "", x.get("url_fullxfull") or ""] for x in c["galeri"]],
                video=[[str(x.get("video_id")), x.get("video_url") or x.get("url") or ""] for x in c["video"]],
                bag=sorted([int(x.get("property_id") or 0), int(x.get("value_id") or 0), int(x.get("image_id") or 0)] for x in c["bag"]),
                stil=sorted([k, v] for k, v in c["stil"].items()), urun_n=c["urun_n"], inv_sha=c["inv_sha"],
                per_sha=sha_metin(jdump([soru_norm(q) for q in c["per"]])))


def kapilar(c, lid):
    L, neden = c["L"], []
    if str(lid) in DOKUNMA:
        neden.append("DOKUNMA ilani")
    if L.get("state") != "active":
        neden.append(f"state {L.get('state')} (active degil; updateListing taslagi yayina alir)")
    if L.get("shop_section_id") != BOLUM:
        neden.append(f"bolum {L.get('shop_section_id')} (kupa bolumu {BOLUM} degil)")
    n = len(c["galeri"])
    if not n or n > LIMIT:
        neden.append(f"canli galeri {n} gorsel")
    if len(c["video"]) > 1:
        neden.append(f"canli video {len(c['video'])} (en fazla 1)")
    if sorted(c["stil"]) != sorted(BAG_HEDEF) or c["urun_n"] != URUN_N:
        neden.append(f"envanter Style degerleri {sorted(c['stil'])} / urun {c['urun_n']} (8 Orchard stili x 2 boy beklenir)")
    ids = {x.get("listing_image_id") for x in c["galeri"]}
    vids = set(c["stil"].values())
    b = c["bag"]
    if any(int(x.get("property_id") or 0) != P_STYLE for x in b):
        neden.append("Style disi variation-images bagi var")
    if any(x.get("value_id") not in vids for x in b) or len({x.get("value_id") for x in b}) != len(b):
        neden.append("bag value_id envanter Style degerlerinde yok / tekrar")
    if any(x.get("image_id") not in ids for x in b):
        neden.append("bagli gorsel canli galeride yok")
    return neden


def bag_ad(c):
    """canli Style baglari {ad: image_id}"""
    ad = {v: k for k, v in c["stil"].items()}
    return {ad.get(x.get("value_id"), f"?{x.get('value_id')}"): x.get("image_id") for x in c["bag"]}


def zaten_durum(c, gd_hedef, mp, kayit):
    """ZATEN | KAYITSIZ (hedef galeri var ama ILERLEME kaydi yok / farkli) | None"""
    g = c["galeri"]
    if len(g) != N or [x.get("rank") for x in g] != list(range(1, N + 1)):
        return None
    if [Y.alt_norm(x.get("alt_text")) for x in g] != [Y.alt_norm(h[3]) for h in gd_hedef]:
        return None
    ids = [x.get("listing_image_id") for x in g]
    rk = {x.get("listing_image_id"): x.get("rank") for x in g}
    bag_ok = {k: rk.get(v) for k, v in bag_ad(c).items()} == BAG_HEDEF
    vid = [str(x.get("video_id")) for x in c["video"]]
    k = kayit or {}
    if not (k.get("durum") == "PASS" and k.get("son_ids") == ids and k.get("video") == vid and bag_ok and not mp.get("yaz")):
        return "KAYITSIZ"
    return "ZATEN"


# ---------------------------------------------------------------- adim plani (durum tabanli; devam ayni yoldan)
def adim_kur(n_canli, sil, bagli, eksik, bag_siralar, bag_gerekli, limit=LIMIT, n_hedef=N, esnek=False):
    """SIRALI plan (Merkez / Serdar 31 Eki "1a", Etsy istek azaltma madde 1): n_canli: galerideki gorsel; sil: cikacak kimlikler (canli
    sirasinda); eksik: yuklenecek hedef siralari; bag_gerekli: Style bagi yazilmali mi. Kural:
      1. eski gorseller ONCE silinir; galeride en az 1 gorsel kalir (aktif ilan gorselsiz olamaz): yerinde kalan hedef gorsel yoksa
         cikarlarin SONUNCUSU ilk yuklemeden hemen sonra silinir;
      2. yeni gorseller 1..n hedef sirasinda (rank + alt metin ayni istekte) yuklenir: eski gorsel sonradan silinmedigi icin rank
         boslugu olusmaz (v11b 40925894166: araya serpistirilen silmeler her ilanda sira gecisini tetikliyordu, ilan basina ~13 fazla);
      3. sira_kontrol: tek galeri okumasi, sira gecisi YALNIZ bozuksa;
      4. Style bagi EN SON tek kez (rank yazimi bagi siler, 19 Eyl olcumu). Bagli eski gorsel silinince o stil son bag yazilana kadar
         gorselsiz kalir (Serdar 31 Eki 1a ile kabul; bagli gorsel silme canlida olculmedi: reddedilirse HATA -> geri alma).
    bagli / bag_siralar / esnek: eski cagrilarla uyum icin (siralamayi etkilemez). -> (adimlar, en fazla gorsel)"""
    sira = sorted(set(eksik))
    sil = list(dict.fromkeys(sil))
    yerinde = n_canli - len(sil)
    bekle = [sil[-1]] if (sira and sil and yerinde == 0) else []
    adim = [("sil", c) for c in sil if c not in bekle]
    n, mx = n_canli - len(adim), n_canli
    for i, s in enumerate(sira):
        adim.append(("yukle", s)); n += 1; mx = max(mx, n)
        if i == 0 and bekle:
            adim.append(("sil", bekle[0])); n -= 1
    adim.append(("sira_kontrol",))
    if bag_gerekli:
        adim.append(("bag",))
    if n != n_hedef:
        raise Y.Dur(f"plan sonu {n} gorsel ({n_hedef} beklenir)")
    if mx > limit:
        raise Y.Dur(f"plan: {mx} gorsel (> {limit})")
    return adim, mx


def ileri_plan(c, gd_hedef=None):
    ids = [x.get("listing_image_id") for x in c["galeri"]]
    bagli = {x.get("image_id") for x in c["bag"]}
    return adim_kur(len(ids), ids, bagli, list(range(1, N + 1)), BAG_HEDEF.values(), True)


# ---------------------------------------------------------------- plan
def plan_girdisi(r, c, hedef, video, mp):
    adim, mx = ileri_plan(c)
    t = istek_tahmini(n_yukle=N, n_sil=len(c["galeri"]), metin=mp.get("yaz", False))
    m = dict(yaz=mp.get("yaz", False), durum=mp.get("durum"))
    if mp.get("yaz"):
        m.update(desc_once=mp["desc_once"], desc_sonra=mp["desc_sonra"], pers_once=mp["pers_once"], pers_sonra=mp["pers_sonra"])
    return dict(ilan=r["listing_id"], cift=r["cift"], canli=canli_ozet(c), hedef=hedef, video=video, stil_vid=dict(sorted(c["stil"].items())),
                metin=m, adimlar=[list(a) for a in adim], en_fazla=mx, en_az=t["en_az"], en_kotu=t["en_kotu"])


def plan_sha(girdiler):
    return hashlib.sha256(jdump(girdiler).encode()).hexdigest()


def plan_yukle(yol, damga):
    p = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+_[0-9a-f]{12}", damga or ""):
        raise SystemExit("DUR: plan_damga bicimi <kuru_kosu>_<sha256 ilk 12>")
    if p.get("plan_damga") != damga or plan_sha(p.get("girdiler") or {})[:12] != damga.split("_", 1)[1]:
        raise SystemExit(f"DUR: {PLAN_AD} plan_damga / sha256 ile ayni degil; yazma yok")
    return p


def _karsilastir(g):
    """canli == plan: istek tahmini ve CDN adresleri haric (video adresi imzali / degisken olabilir; kimlik, sira, alt metin kalir)"""
    g = {k: copy.deepcopy(v) for k, v in g.items() if k not in ISTEK_ALAN}
    g["canli"]["galeri"] = [x[:3] for x in g["canli"]["galeri"]]
    g["canli"]["video"] = [x[:1] for x in g["canli"]["video"]]
    return g


def esit(a, b):
    return _karsilastir(a) == _karsilastir(b)


# ---------------------------------------------------------------- yedek (ETSY YOK; CDN)
def imza_bayt(b, video):
    """JPEG FFD8FF / MP4 ftyp (inceleme 30 Eki madde 6: 16 bayt HTML yedek sayilmisti)"""
    return bool(b) and (b[4:8] == b"ftyp" if video else b[:3] == b"\xff\xd8\xff")


def md5_dosya(yol):
    h = hashlib.md5()
    with open(yol, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def yedek_kur(gd, plan_damga, kok, indir=None):
    """Plan girdisinden (yazimda canli == plan kapisi bunu canliya baglar) eski gorsel + video indirme + YEDEK.json.
    YEDEK.json zaman damgasiz ve anahtar sirali: ayni plan -> ayni bayt (devam kosusunda rclone --immutable gecer). Hata olursa ilanin
    yerel klasoru silinir (yarim yedek Drive'a gitmez)."""
    indir = indir or Y.cdn_indir
    d = Path(kok) / f"{gd['ilan']}_{gd['cift']}"
    c = gd["canli"]
    rk = {i: r for r, i, _, _ in c["galeri"]}
    vad = {v: k for k, v in gd["stil_vid"].items()}
    Yd = dict(ilan=gd["ilan"], cift=gd["cift"], plan_damga=plan_damga,
              galeri=[], baglar=[dict(stil=vad.get(v), property_id=p, value_id=v, image_id=i, rank=rk.get(i)) for p, v, i in c["bag"]],
              video=[], metin=gd["metin"] if gd["metin"].get("yaz") else dict(yaz=False, desc_sha=c["desc_sha"]))
    try:
        d.mkdir(parents=True, exist_ok=True)
        for r, i, alt, u in c["galeri"]:
            if not str(u).startswith(CDN):
                raise Y.Dur(f"yedek: {i} CDN disi adres")
            b = indir(u)
            if not imza_bayt(b, False):
                raise Y.Dur(f"yedek: gorsel {i} JPEG imzasi yok ({len(b or b'')} bayt; hata sayfasi?)")
            p = d / f"r{r:02d}_{i}.jpg"; p.write_bytes(b)
            Yd["galeri"].append(dict(rank=r, listing_image_id=i, alt_text=alt, url=u, dosya=p.name, sha256=Y.sha256(p), md5=md5_dosya(p),
                                     bayt=p.stat().st_size))
        for vid, u in c["video"]:
            if not str(u).startswith(CDN):
                raise Y.Dur(f"yedek: video {vid} CDN disi adres")
            b = indir(u)
            if not imza_bayt(b, True):
                raise Y.Dur(f"yedek: video {vid} MP4 imzasi yok ({len(b or b'')} bayt; hata sayfasi?)")
            p = d / f"video_{vid}.mp4"; p.write_bytes(b)
            Yd["video"].append(dict(video_id=vid, url=u, dosya=p.name, sha256=Y.sha256(p), md5=md5_dosya(p), bayt=p.stat().st_size))
        (d / "YEDEK.json").write_text(json.dumps(Yd, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    return Yd


def drive_liste_oku(yol):
    """rclone lsjson -R --hash -> {Path: dict(Size, Hashes)}"""
    if not yol or not Path(yol).exists():
        return {}
    return {x["Path"]: dict(Size=x.get("Size"), Hashes={k.lower(): v for k, v in (x.get("Hashes") or {}).items() if v})
            for x in json.loads(Path(yol).read_text(encoding="utf-8") or "[]") if not x.get("IsDir")}


def drive_dosya_ok(drive, yol, bayt, md5=None, sha=None):
    """Drive kaydi: boyut ayni + ortak hash turlerinin (md5 / sha256) hepsi ayni; ortak hash yoksa FAIL (boyut tek basina yetmez)."""
    x = drive.get(yol)
    if not x or x.get("Size") != bayt:
        return False
    h = x.get("Hashes") or {}
    ortak = [(h[k], v) for k, v in (("md5", md5), ("sha256", sha)) if h.get(k) and v]
    return bool(ortak) and all(a == b for a, b in ortak)


def yedek_drive_eksik(yd, alt, drive, yd_yol=None):
    """YEDEK.json'daki her dosya (ve verilirse YEDEK.json'un kendisi) Drive'da ayni boyut + hash ile var mi -> eksik dosya adlari"""
    eksik = [x["dosya"] for x in (yd.get("galeri") or []) + (yd.get("video") or [])
             if not drive_dosya_ok(drive, f"{alt}/{x['dosya']}", x.get("bayt"), x.get("md5"), x.get("sha256"))]
    if yd_yol is not None and not drive_dosya_ok(drive, f"{alt}/YEDEK.json", Path(yd_yol).stat().st_size, md5_dosya(yd_yol),
                                                 Y.sha256(yd_yol)):
        eksik.append("YEDEK.json")
    return eksik


def yerel_drive_eksik(yedek_dir, drive):
    """yuklemeden sonra: yereldeki her yedek dosyasi Drive'da ayni boyut + hash ile -> eksik / farkli yollar"""
    y = Path(yedek_dir)
    return [str(p.relative_to(y)) for p in sorted(y.rglob("*")) if p.is_file()
            and not drive_dosya_ok(drive, str(p.relative_to(y)), p.stat().st_size, md5_dosya(p), Y.sha256(p))]


def yedek_plana_uygun(yd, gd, plan_damga):
    neden = []
    if yd.get("plan_damga") != plan_damga:
        neden.append("yedek baska plan damgasiyla")
    c = gd["canli"]
    if [[x["rank"], x["listing_image_id"]] for x in yd.get("galeri") or []] != [[r, i] for r, i, _, _ in c["galeri"]]:
        neden.append("yedek galeri kimlikleri plandan farkli")
    if [x["video_id"] for x in yd.get("video") or []] != [v for v, _ in c["video"]]:
        neden.append("yedek video kimlikleri plandan farkli")
    if yd.get("metin", {}).get("yaz") != gd["metin"].get("yaz"):
        neden.append("yedek metin kaydi plandan farkli")
    return neden


def yedek_kapisi(gd, plan_damga, yedek_dir, drive):
    """YEDEK.json yerelde (Drive'dan inmis) + Drive lsjson --hash'te YEDEK.json ve her dosya ayni boyut + md5 / sha256. -> (yedek, neden)"""
    alt = f"{gd['ilan']}_{gd['cift']}"
    p = Path(yedek_dir) / alt / "YEDEK.json"
    if not p.exists():
        return None, ["yedek: YEDEK.json yok; yazim yok"]
    yd = json.loads(p.read_text(encoding="utf-8"))
    neden = yedek_plana_uygun(yd, gd, plan_damga)
    neden += [f"yedek: {x} Drive'da yok ya da boyut / hash farkli" for x in yedek_drive_eksik(yd, alt, drive, p)]
    return yd, neden


def yedek_dosya(yedek_dir, alt, x, uzak=""):
    """Geri alma icin yedek dosyasi: yerelde yoksa (yazim isinde yalniz YEDEK.json iner) Drive'dan rclone ile; sha256 YEDEK ile ayni."""
    p = Path(yedek_dir) / alt / x["dosya"]
    if not p.exists() and uzak:
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([os.environ.get("RCLONE", "rclone"), "copyto", f"{uzak}/{alt}/{x['dosya']}", str(p), "-q"],
                       capture_output=True, timeout=300)
    if not p.exists() or Y.sha256(p) != x["sha256"]:
        raise Y.Dur(f"geri alma: yedek dosyasi {alt}/{x['dosya']} yok ya da sha256 farkli")
    return p


class Kayit(Y.Kayit):
    """DEVAM_<ilan>.json; uzak=True yazimlar Drive'a da (RCLONE ortam degiskeni; testte sahte). drive_ok: son uzak yazim basarili mi.
    Uzak yazim: ilan basi, her yukleme oncesi (belirsiz) / sonrasi (yeni kimlik), video oncesi / sonrasi, durum degisimleri
    (inceleme 30 Eki madde 2: kosu ilan ortasinda olurse yeni gorseller kayitsiz kalmasin). Silme / sira adimlari yalniz yerel
    (canli galeriden yeniden kurulur)."""
    drive_ok = True

    def yaz(self, ids=None, uzak=True):
        if ids is not None:
            self.d["son_ids"] = sorted(ids)
        self.p.write_text(json.dumps(self.d, indent=1, ensure_ascii=False))
        if not (self.drive and uzak):
            return
        for _ in range(2):
            try:
                if subprocess.run([os.environ.get("RCLONE", "rclone"), "copyto", str(self.p), self.drive, "-q"],
                                  capture_output=True, timeout=90).returncode == 0:
                    self.drive_ok = True
                    return
            except Exception:   # noqa: BLE001
                pass
        self.drive_ok = False
        log(f"  UYARI: DEVAM Drive'a yazilamadi ({self.drive})")


def devam_ilan_oku(d, plan_damga):
    """Drive'dan inen DEVAM_<ilan>.json'lar (ilan basina, her yuklemede yazilir) -> {ilan: kayit}; yalniz bu plan_damga"""
    out = {}
    for p in (sorted(Path(d).glob("DEVAM_*.json")) if d and Path(d).is_dir() else []):
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            raise SystemExit(f"DUR: {p.name} okunamadi (bozuk JSON); elle bakilmali")
        if x.get("plan_damga") == plan_damga:
            out[p.stem.split("_", 1)[1]] = x
    return out


def json_oku(yol):
    return json.loads(Path(yol).read_text(encoding="utf-8")) if yol and Path(yol).exists() else {"ilanlar": {}}


# ---------------------------------------------------------------- yazim motoru (ileri ve geri alma ayni yol)
def galeri_sorun(g, son, alt):
    s = []
    if [x.get("listing_image_id") for x in g] != [son[k] for k in sorted(son)]:
        s.append(f"sira / kimlik {[x.get('listing_image_id') for x in g]}")
    if [x.get("rank") for x in g] != list(range(1, len(son) + 1)):
        s.append(f"rank {[x.get('rank') for x in g]}")
    if [Y.alt_norm(x.get("alt_text")) for x in g] != [Y.alt_norm(alt[k]) for k in sorted(alt)]:
        s.append("alt metin")
    return s


def say_yazim(K):
    K.d["yazim"] = int(K.d.get("yazim") or 0) + 1


def bag_yaz(api, shop, lid, son, bag_sira, stil_vid, K):
    hb = {stil_vid[ad]: son[s] for ad, s in bag_sira.items()}
    say_yazim(K); K.yaz(uzak=False)
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": [
        {"property_id": P_STYLE, "value_id": v, "image_id": i} for v, i in sorted(hb.items())]})
    K.d["bag_yazildi"] = True

    def ok(vm):
        return {x.get("value_id"): x.get("image_id") for x in vm} == hb and all(int(x.get("property_id") or 0) == P_STYLE for x in vm)
    vm = G.kararli(lambda: G.var_img(api, shop, lid), ok)
    if not ok(vm):
        raise Geri(f"Style bag geri okumasi {len(vm)} kayit, hedef {len(hb)} ile ayni degil")
    log(f"  bag {len(hb)}/{len(hb)} | kota {api.remaining}")


def galeri_kur(api, shop, lid, c, hedef, sil, bag_sira, stil_vid, K, anahtar, esnek=False):
    """hedef {sira: dict(alt, id (yerinde kalan) | yol + ad (yuklenecek))}. K.d[anahtar] = {ad: yuklenen id} (devam / geri alma).
    -> son {sira: id}"""
    ids = {x.get("listing_image_id") for x in c["galeri"]}
    yk = K.d.setdefault(anahtar, {})
    son = {}
    for s, h in hedef.items():
        son[s] = h["id"] if h.get("id") in ids else (yk.get(h.get("ad")) if yk.get(h.get("ad")) in ids else None)
    eksik = [s for s, v in son.items() if v is None]
    if any(hedef[s].get("yol") is None for s in eksik):
        raise Y.Dur(f"galeri: yuklenecek dosyasi olmayan sira {[s for s in eksik if hedef[s].get('yol') is None]}")
    sil = [i for i in sil if i in ids]
    bagli = {x.get("image_id") for x in c["bag"]}
    simdi = {x.get("value_id"): x.get("image_id") for x in c["bag"]}
    bag_gerekli = any(v is None for v in son.values()) or simdi != {stil_vid[a]: son[s] for a, s in bag_sira.items()}
    adim, mx = adim_kur(len(ids), sil, bagli, eksik, bag_sira.values(), bag_gerekli, n_hedef=len(hedef), esnek=esnek)
    if mx > LIMIT:
        raise Y.Dur(f"plan {mx} gorsel (> {LIMIT})")
    alt = {s: h["alt"] for s, h in hedef.items()}
    log(f"  plan {anahtar}: {sum(a[0] == 'yukle' for a in adim)} yukle, {sum(a[0] == 'sil' for a in adim)} sil, bag "
        f"{'var' if bag_gerekli else 'yok'}, en fazla {mx} gorsel")
    for n, a in enumerate(adim, 1):
        K.d["bekleyen"] = list(a); K.yaz(ids, uzak=False)
        if a[0] == "sil":
            say_yazim(K); K.yaz(ids, uzak=False)
            api.delete(f"/shops/{shop}/listings/{lid}/images/{a[1]}", ok404=True)
            K.d.setdefault("silinen", []).append(a[1]); ids.discard(a[1])
            log(f"  [{n}/{len(adim)}] sil {a[1]} -> {len(ids)} gorsel | kota {api.remaining}")
        elif a[0] == "yukle":
            h = hedef[a[1]]
            K.d["belirsiz"] = h["ad"]; say_yazim(K); K.yaz(ids)
            yid, dn = Y.yukle_guvenli(api, shop, lid, h["yol"], h["ad"], h["alt"], set(ids),
                                      gonderilmedi=lambda: K.d.pop("belirsiz", None), rank=a[1])
            yk[h["ad"]] = yid; son[a[1]] = yid; ids.add(yid); K.d.pop("belirsiz", None)
            log(f"  [{n}/{len(adim)}] yukle {h['ad']} -> {yid} (rank {a[1]}, deneme {dn}) | {len(ids)} gorsel | kota {api.remaining}")
        elif a[0] == "bag":   # sirali plan: tum yukleme / silme / sira yazimlarindan SONRA tek kez
            bag_yaz(api, shop, lid, son, bag_sira, stil_vid, K); K.d.pop("sira_post", None)
        elif a[0] == "sira_kontrol":
            bek = set(son.values())
            g = G.kararli(lambda: G.galeri(api, lid), lambda g: {x.get("listing_image_id") for x in g} == bek)
            if {x.get("listing_image_id") for x in g} != bek:
                raise Geri(f"sira kontrolu: galeri kimlik kumesi beklenen degil (+{sorted({x.get('listing_image_id') for x in g} - bek)} "
                           f"-{sorted(bek - {x.get('listing_image_id') for x in g})})")
            if galeri_sorun(g, son, alt):
                K.d["sira_post"] = True; K.yaz(ids, uzak=False)   # rank yazimi bagi siler: bag sonda yeniden (asagida)
                for gecis in (1, 2):
                    for s in sorted(son):
                        say_yazim(K)
                        api.post_file(f"/shops/{shop}/listings/{lid}/images", files={
                            "listing_image_id": (None, str(son[s])), "rank": (None, str(s)), "alt_text": (None, alt[s])})
                    g = G.kararli(lambda: G.galeri(api, lid), lambda g: not galeri_sorun(g, son, alt))
                    if not galeri_sorun(g, son, alt):
                        break
                    log(f"  sira gecis {gecis} oturmadi: {galeri_sorun(g, son, alt)[:2]}")
                if galeri_sorun(g, son, alt):
                    raise Geri(f"sira 2 geciste oturmadi: {galeri_sorun(g, son, alt)[:2]}")
            log(f"  [{n}/{len(adim)}] sira + alt metin tamam | kota {api.remaining}")
        K.d["bekleyen"] = None; K.yaz(ids, uzak=a[0] == "yukle")   # yeni kimlik Drive'daki DEVAM'a hemen
    if K.d.pop("sira_post", False) and not any(a[0] == "bag" for a in adim):   # bag gerekmiyordu ama sira yazimi bagi sildi
        bag_yaz(api, shop, lid, son, bag_sira, stil_vid, K)
    return son


def video_yukle_tek(api, shop, lid, yol, eski):
    """video_yukle_78.yukle_tek ile ayni kural: tek gonderim; hata / kimliksiz yanitta ilan okunur, eski kumede olmayan TEK video ->
    yuklenmis; yoksa DUR (eski SILINMEZ)."""
    hata = ""
    try:
        with open(yol, "rb") as fh:
            y = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (Path(yol).name, fh, "video/mp4")},
                              data={"name": Path(yol).name}, tekrar=1)
        v = str((y or {}).get("video_id") or "")
        if v and v not in eski:
            return v
        hata = f"yanit kimligi {v or 'bos'}"
    except SystemExit as e:
        if str(e.code).startswith("DUR: kota"):
            raise
        hata = str(e.code)[:150]
    except Exception as e:   # noqa: BLE001
        hata = str(e)[:150]
    vs = G.kararli(lambda: G.videolar(api, lid), lambda vs: bool({str(x.get("video_id")) for x in vs} - set(eski)))
    yeni = sorted({str(x.get("video_id")) for x in vs} - set(eski))
    if len(yeni) == 1:
        log(f"    video yukleme hatasi ({hata}) ama ilanda yeni video {yeni[0]}: yuklenmis sayildi")
        return yeni[0]
    raise Y.Dur(f"video yukleme hatasi ({hata}); ilanda yeni video {yeni or 'yok'}; tekrar gonderilmedi, eski SILINMEDI")


def video_kur(api, shop, lid, yol, korunacak, K, anahtar):
    """korunacak: zaten ilanda olmasi istenen video kimlikleri (geri alma: yedekteki eski video hala ilandaysa). Yoksa yol yuklenir,
    active olmadan eski silinmez. -> son video kimligi listesi"""
    canli = [str(x.get("video_id")) for x in G.videolar(api, lid)]
    hedef = next((v for v in korunacak if v in canli), None) or (K.d.get(anahtar) if K.d.get(anahtar) in canli else None)
    if hedef is None:
        if yol is None:
            hedef = None
        else:
            K.d[anahtar + "_belirsiz"] = True; say_yazim(K); K.yaz()
            hedef = video_yukle_tek(api, shop, lid, yol, canli)
            K.d[anahtar] = hedef; K.d.pop(anahtar + "_belirsiz", None); K.yaz()
            canli.append(hedef)
            log(f"  video yuklendi {hedef} | kota {api.remaining}")
    if hedef is not None:
        for i in range(VIDEO_DENEME):
            if i:
                G.time.sleep(VIDEO_BEKLE)
            vs = G.videolar(api, lid)
            y = next((x for x in vs if str(x.get("video_id")) == hedef), None)
            if y and y.get("video_state") == "active":
                canli = [str(x.get("video_id")) for x in vs]
                break
        else:
            raise Geri(f"video {hedef} active olmadi; eski video SILINMEDI")
    for v in [v for v in canli if v != hedef]:
        say_yazim(K); K.yaz(uzak=False)
        api.delete(f"/shops/{shop}/listings/{lid}/videos/{v}", ok404=True)
        K.d.setdefault("silinen_video", []).append(v)
    bek = [hedef] if hedef else []
    vs = G.kararli(lambda: G.videolar(api, lid), lambda vs: [str(x.get("video_id")) for x in vs] == bek)
    if [str(x.get("video_id")) for x in vs] != bek:
        raise Geri(f"video son okuma {[str(x.get('video_id')) for x in vs]} (beklenen {bek})")
    return bek


def soru_govde(Q):
    return [{k: q[k] for k in SORU_ALAN if k in q and q[k] is not None} for q in Q]


def metin_kur(api, shop, lid, desc, pers, K):
    """desc / pers None ise yazilmaz. State active okunmadan yazim yok (updateListing taslagi yayina alir)."""
    if desc is None and pers is None:
        return
    L = api.get(f"/listings/{lid}") or {}
    if L.get("state") != "active":
        raise Y.Dur(f"metin: state {L.get('state')} (active degil); updateListing cagrilmadi")
    if desc is not None and html.unescape(L.get("description") or "") != desc:
        say_yazim(K); K.d["metin_yazim"] = True; K.yaz()
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": desc})
        log(f"  aciklama PATCH | kota {api.remaining}")
    if pers is not None:
        # POST tum soru setini degistirir: canli set once okunur; tek soru degilse yazim yok, question_id korunur (inceleme 30 Eki 8)
        canli = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
        if len(canli) != 1 or len(pers) != 1:
            raise Y.Dur(f"metin: canli kisisellestirme {len(canli)} soru / hedef {len(pers)} (tek soru beklenir); POST yok")
        if soru_norm(canli[0]) != soru_norm(pers[0]):
            govde = soru_govde(pers)
            if canli[0].get("question_id") is not None:
                govde[0]["question_id"] = canli[0]["question_id"]
            say_yazim(K); K.d["metin_yazim"] = True; K.yaz()
            api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": govde})
            log(f"  kisisellestirme POST | kota {api.remaining}")


def son_kontrol(api, shop, lid, son, alt, bag_sira, stil_vid, video, gd_canli, desc, pers):
    """son geri okuma -> sorun listesi"""
    s = []
    bek = [son[k] for k in sorted(son)]
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == bek)
    s += [f"galeri: {x}" for x in galeri_sorun(g, son, alt)]
    hb = {stil_vid[ad]: son[k] for ad, k in bag_sira.items()}
    vm = G.kararli(lambda: G.var_img(api, shop, lid), lambda vm: {x.get("value_id"): x.get("image_id") for x in vm} == hb)
    if {x.get("value_id"): x.get("image_id") for x in vm} != hb:
        s.append(f"Style baglari {len(vm)} kayit, hedefle ayni degil")
    vs = [str(x.get("video_id")) for x in G.videolar(api, lid)]
    if vs != list(video):
        s.append(f"video {vs} (beklenen {list(video)})")
    c = canli_oku_hafif(api, lid)
    if c["state"] != "active":
        s.append(f"state {c['state']}")
    if c["title_sha"] != gd_canli["title_sha"] or c["tags"] != gd_canli["tags"]:
        s.append("korunan baslik / etiket degisti")
    if c["inv_sha"] != gd_canli["inv_sha"]:
        s.append("korunan envanter degisti")
    if desc is not None and c["desc"] != desc:
        s.append("aciklama hedef metin degil")
    if desc is None and sha_metin(c["desc"]) != gd_canli["desc_sha"]:
        s.append("korunan aciklama degisti")
    if pers is not None and c["per"] != [soru_norm(q) for q in pers]:
        s.append("kisisellestirme hedef metin degil")
    return s


def canli_oku_hafif(api, lid):
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    urun = sorted((pr.get("sku"), jdump(pr.get("offerings")), jdump(pr.get("property_values")))
                  for pr in inv.get("products") or [] if not pr.get("is_deleted"))
    return dict(state=L.get("state"), title_sha=sha_metin(L.get("title")), tags=list(L.get("tags") or []), inv_sha=sha_metin(jdump(urun)),
                desc=html.unescape(L.get("description") or ""), per=[soru_norm(q) for q in per])


def ileri(api, shop, lid, gd, c, dosya_dir, K):
    hedef = {}
    for s, dosya, sha, alt in gd["hedef"]:
        p = Path(dosya_dir) / dosya
        if not p.exists() or Y.sha256(p) != sha:
            raise Y.Dur(f"hedef dosya {dosya} yok ya da sha256 plandan farkli")
        hedef[s] = dict(alt=alt, yol=p, ad=Path(dosya).name)
    vp = Path(dosya_dir) / gd["video"][0]
    if not vp.exists() or Y.sha256(vp) != gd["video"][1]:
        raise Y.Dur(f"hedef video {gd['video'][0]} yok ya da sha256 plandan farkli")
    eski = [i for _, i, _, _ in gd["canli"]["galeri"]]
    son = galeri_kur(api, shop, lid, c, hedef, eski, BAG_HEDEF, gd["stil_vid"], K, "yuklenen")
    vid = video_kur(api, shop, lid, vp, [], K, "video_yeni")
    m = gd["metin"]
    metin_kur(api, shop, lid, m.get("desc_sonra") if m.get("yaz") else None, m.get("pers_sonra") if m.get("yaz") else None, K)
    s = son_kontrol(api, shop, lid, son, {k: h["alt"] for k, h in hedef.items()}, BAG_HEDEF, gd["stil_vid"], vid, gd["canli"],
                    m.get("desc_sonra") if m.get("yaz") else None, m.get("pers_sonra") if m.get("yaz") else None)
    return son, vid, s


def geri_al(api, shop, lid, yd, yedek_dir, K, uzak=""):
    """YEDEK.json'dan eski hal: gorseller ayni sira ve alt metinle (yerinde kalan eski gorsel korunur, silinen yedek dosyasindan
    yeniden yuklenir), Style baglari ada gore eski siralara, eski video, ayni burcta eski metin. -> sorun listesi (bos = geri alindi)"""
    alt_d = f"{yd['ilan']}_{yd['cift']}"
    try:
        c = canli_oku(api, shop, lid)
        canli = {x.get("listing_image_id") for x in c["galeri"]}
        eski = sorted(yd["galeri"], key=lambda x: x["rank"])
        eski_ids = {x["listing_image_id"] for x in eski}
        bizim = set((K.d.get("yuklenen") or {}).values()) | set((K.d.get("geri_yuklenen") or {}).values())
        bilinmeyen = canli - eski_ids - bizim
        if bilinmeyen and K.d.get("belirsiz") and len(bilinmeyen) == 1:
            bizim |= bilinmeyen; bilinmeyen = set()     # yanit kayda gecmeden kesilen yukleme: bizim (geri alinir)
        if bilinmeyen:
            return [f"geri alma: galeride planla aciklanamayan gorsel {sorted(bilinmeyen)}; elle bakilmali"]
        hedef = {}
        for s, x in enumerate(eski, 1):
            h = dict(alt=x.get("alt_text") or "", ad=f"YEDEK_{x['dosya']}")
            if x["listing_image_id"] in canli:
                h["id"] = x["listing_image_id"]
            else:
                h["yol"] = yedek_dosya(yedek_dir, alt_d, x, uzak)
            hedef[s] = h
        sira_eski = {x["listing_image_id"]: s for s, x in enumerate(eski, 1)}
        bag_sira = {b["stil"]: sira_eski[b["image_id"]] for b in yd.get("baglar") or [] if b.get("image_id") in sira_eski}
        if len(bag_sira) != len(yd.get("baglar") or []) or not set(bag_sira) <= set(c["stil"]):
            return ["geri alma: yedek Style baglari canli envanterle eslenemedi; elle bakilmali"]
        geri_yk = set((K.d.get("geri_yuklenen") or {}).values())
        sil = sorted(canli - eski_ids - geri_yk)   # onceki geri almada yeniden yuklenen eski gorsel yerinde kalir (inceleme 31 Eki madde 2)
        son = galeri_kur(api, shop, lid, c, hedef, sil, bag_sira, c["stil"], K, "geri_yuklenen", esnek=True)
        ev = [x["video_id"] for x in yd.get("video") or []]
        vyol = yedek_dosya(yedek_dir, alt_d, yd["video"][0], uzak) if ev and ev[0] not in [str(x.get("video_id")) for x in c["video"]] else None
        vid = video_kur(api, shop, lid, vyol, ev, K, "video_geri")
        m = yd.get("metin") or {}
        desc = m.get("desc_once") if m.get("yaz") else None
        pers = m.get("pers_once") if m.get("yaz") else None
        metin_kur(api, shop, lid, desc, pers, K)
        s = []
        bek = [son[k] for k in sorted(son)]
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == bek)
        s += [f"geri alma galeri: {x}" for x in galeri_sorun(g, son, {k: h["alt"] for k, h in hedef.items()})]
        hb = {c["stil"][ad]: son[k] for ad, k in bag_sira.items()}
        vm = G.kararli(lambda: G.var_img(api, shop, lid), lambda vm: {x.get("value_id"): x.get("image_id") for x in vm} == hb)
        if {x.get("value_id"): x.get("image_id") for x in vm} != hb:
            s.append("geri alma: Style baglari eski siralara donmedi")
        if len(vid) != len(ev):
            s.append(f"geri alma: video {vid} (yedekte {len(ev)})")
        h = canli_oku_hafif(api, lid)
        if desc is not None and h["desc"] != desc:
            s.append("geri alma: aciklama eski metin degil")
        if pers is not None and h["per"] != [soru_norm(q) for q in pers]:
            s.append("geri alma: kisisellestirme eski metin degil")
        if h["state"] != "active":
            s.append(f"geri alma: state {h['state']}")
        return s
    except (Geri, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        return [f"geri alma hatasi: {str(getattr(e, 'code', None) or e)[:200]}"]


def yaz_ilan(api, shop, lid, gd, c, dosya_dir, yd, yedek_dir, K, out, uzak=""):
    """-> dict(sonuc PASS | FAIL (geri alindi) | DUR, sorun, son_ids, video)"""
    (Path(out) / f"YEDEK_CANLI_{lid}.json").write_text(json.dumps(canli_ozet(c), indent=1, ensure_ascii=False), encoding="utf-8")
    try:
        son, vid, s = ileri(api, shop, lid, gd, c, dosya_dir, K)
        if s:
            raise Geri("; ".join(s))
        K.d.update(durum="PASS", hata=None, son_sira=[son[k] for k in sorted(son)], video=vid); K.yaz()
        return dict(sonuc="PASS", sorun=[], son_ids=[son[k] for k in sorted(son)], video=vid)
    except (Geri, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        if m.startswith("DUR: kota"):        # istek gonderilmeden durdu: geri alma yok (kota yok), DEVAM sonraki kosuda surer
            K.d["kota_durdu"] = m; K.yaz()   # Drive'daki DEVAM_<ilan>.json: yuklenen kimlikler + adim; devam ya da geri_al modu
            return dict(sonuc="DUR", sorun=[m + " (ilan ortada; DEVAM_<ilan>.json Drive'da: ayni plan_damga ile yeniden kos ya da "
                                                "geri_al modu)" + ("" if K.drive_ok else " UYARI: DEVAM Drive'a yazilamadi")])
        if not int(K.d.get("yazim") or 0):
            K.yaz(); return dict(sonuc="DUR", sorun=[m + " (yazim gonderilmedi, ilan degismedi)"])
        K.d["hata"] = m; K.yaz()
        log(f"    {lid} HATA: {m[:160]} -> geri alma (yedekten)")
        gs = geri_al(api, shop, lid, yd, yedek_dir, K, uzak)
        if gs:
            K.d["geri_alma"] = "BASARISIZ"; K.yaz()
            return dict(sonuc="DUR", sorun=[m] + gs + ["elle bakilmali (geri_al modu ayni yedekle yeniden kosulabilir)"])
        K.d.update(geri_alma="TAMAM", durum="GERI_ALINDI"); K.yaz()
        return dict(sonuc="FAIL", sorun=[m, "GERI ALINDI (yedekteki eski galeri, baglar, video, metin)"])


# ---------------------------------------------------------------- kosu
def devam_uzlas(K, c, gd):
    """devam: canli galeride yalniz eski + bu planin yukledikleri olabilir; belirsiz yukleme alt metinle tek adayla eslenir."""
    canli = {x.get("listing_image_id"): x for x in c["galeri"]}
    eski = {i for _, i, _, _ in gd["canli"]["galeri"]}
    yk = K.d.setdefault("yuklenen", {})
    bilinmeyen = {i: x for i, x in canli.items() if i not in eski and i not in set(yk.values())}
    if K.d.get("belirsiz") and bilinmeyen:
        alt = {Path(d).name: a for _, d, _, a in gd["hedef"]}.get(K.d["belirsiz"])
        aday = [i for i, x in bilinmeyen.items() if Y.alt_norm(x.get("alt_text")) == Y.alt_norm(alt)]
        if len(aday) == 1:
            yk[K.d.pop("belirsiz")] = aday[0]; bilinmeyen.pop(aday[0])
    if bilinmeyen:
        raise Y.Dur(f"devam: galeride planla aciklanamayan gorsel {sorted(bilinmeyen)}; elle bakilmali")
    if K.d.get("video_yeni_belirsiz"):
        ev = {v for v, _ in gd["canli"]["video"]}
        yeni = [str(x.get("video_id")) for x in c["video"] if str(x.get("video_id")) not in ev]
        if len(yeni) > 1:
            raise Y.Dur("devam: birden fazla yeni video; elle bakilmali")
        if yeni:
            K.d["video_yeni"] = yeni[0]
        K.d.pop("video_yeni_belirsiz", None)


def kota_oku(api, shop):
    """Kalan kota bilinmeden ilk ilan kapisi atlanirdi (etsy_common: remaining None iken kapi yok; inceleme 30 Eki madde 3).
    Tek ucuz GET (/shops/<shop>) ile x-remaining-today okunur; okunamazsa DUR."""
    if api.remaining is None:
        api.get(f"/shops/{shop}")
    if api.remaining is None:
        raise SystemExit("DUR: x-remaining-today okunamadi; kota kapisi uygulanamaz, ilan baslamadi")
    log(f"kota: kalan {api.remaining} (kosu basi okuma)")


def ilan_tahmini(gd):
    """Ilan basi en kotu istek, GUNCEL kodla ve plandaki GERCEK eski gorsel sayisiyla (planin eski en_kotu degeri degil)."""
    return istek_tahmini(n_sil=len(gd["canli"]["galeri"]), metin=bool(gd["metin"].get("yaz")))


def devam_birlestir(a, devam):
    """Toplu DEVAM.json + Drive'daki ilan basina DEVAM_<ilan>.json (her yuklemede yazilir, daha yeni) -> {ilan: kayit}"""
    dvi = devam_ilan_oku(getattr(a, "devam_ilan_dir", ""), a.plan_damga)
    for lid, x in dvi.items():
        devam.setdefault("ilanlar", {})[lid] = dict(x, set=0, hedef=N)
    return {lid: x for lid, x in (devam.get("ilanlar") or {}).items() if x.get("plan_damga") == a.plan_damga}


def pass_kaydi(dv):
    """ILERLEME'ye gecmemis (kosu sonda oldu) ama DEVAM_<ilan>.json'da PASS olan ilan -> ILERLEME kaydi bicimi"""
    if dv.get("durum") == "PASS" and dv.get("son_sira"):
        return dict(durum="PASS", son_ids=dv["son_sira"], video=dv.get("video"), plan_damga=dv.get("plan_damga"))
    return None


def parti_sec(R, plan, dvs, ilerleme, plan_damga, azami):
    """Bu kosunun ilanlari: planda olan, PASS / GERI_ALINDI olmayan (DEVAM_<ilan> ya da ILERLEME), liste sirasiyla en fazla azami."""
    out = []
    for r in R:
        lid = r["listing_id"]
        dv = dvs.get(lid) or {}
        il = (ilerleme.get("ilanlar") or {}).get(lid) or {}
        if lid not in (plan.get("girdiler") or {}):
            continue
        if dv.get("durum") in ("PASS", "GERI_ALINDI") or (il.get("durum") == "PASS" and il.get("plan_damga") == plan_damga):
            continue
        out.append(r)
        if azami and len(out) >= azami:
            break
    return out


def parti_mod(a):
    """ETSY YOK: parti ilanlari + yalniz onlarin dosya listeleri (is akisi bunlari indirir)."""
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    plan = plan_yukle(a.plan, a.plan_damga)
    devam = json_oku(a.devam)
    dvs = devam_birlestir(a, devam)
    P = parti_sec(kapsam(liste_oku(a.liste), a.sadece, a.haric), plan, dvs, json_oku(a.ilerleme), a.plan_damga, a.azami_ilan)
    ad = {"kapak": [], "kart": [], "stil": [], "video": []}
    yedek = []
    for r in P:
        g = plan["girdiler"][r["listing_id"]]
        for d in [h[1] for h in g["hedef"]] + [g["video"][0]]:
            k, f = d.split("/", 1); ad[k].append(f)
        yedek.append(f"{g['ilan']}_{g['cift']}/YEDEK.json")
    for k, v in ad.items():
        (out / f"{k}.txt").write_text("".join(x + "\n" for x in v), encoding="utf-8")
    (out / "yedek.txt").write_text("".join(x + "\n" for x in yedek), encoding="utf-8")
    (out / "PARTI.txt").write_text(",".join(r["listing_id"] for r in P), encoding="utf-8")
    log(f"PARTI: {len(P)} ilan (azami {a.azami_ilan}): {','.join(r['listing_id'] for r in P)}")
    return 0


def calistir(api, shop, a):
    out = Path(a.out); ilan_out = out / "ilanlar"; ilan_out.mkdir(parents=True, exist_ok=True)
    yazim = a.mod == "yaz"
    alt = alt_oku(a.alt)
    if yazim and not alt_onayli(alt):
        raise SystemExit("DUR: kupa alt metin sablonu ONAYLI degil; yazim yok")
    plan = plan_yukle(a.plan, a.plan_damga) if yazim else None
    kaynak = kaynak_oku(a.kaynak)
    drive = drive_liste_oku(a.yedek_liste) if yazim else {}
    devam = json_oku(a.devam)
    dvs = devam_birlestir(a, devam) if yazim else {}
    ilerleme = json_oku(a.ilerleme)
    R = kapsam(liste_oku(a.liste), a.sadece, a.haric)
    satir, girdiler, dur, t0, baslayan = [], {}, None, time.time(), 0
    onb, ru_onb, esit_kalan = {}, {}, (a.toplu_esit_n if not yazim else 0)
    if R:
        kota_oku(api, shop)
    if R and not yazim:
        # KURU: koşu basi TOPLU okuma (100'luk parca 2 istek). YAZIM: ilan basina yazmadan HEMEN once taze toplu okuma (2 istek, asagida):
        # koşu basi anlik goruntu yazim kararinda kullanilmaz (inceleme 31 Eki madde 4: satis / elle duzenleme koşu sirasinda olur)
        oku_ids = [r["listing_id"] for r in R]
        if int(api.remaining) - 2 * (-(-len(oku_ids) // TO.TOPLU_N)) >= KOTA_SINIRI:
            c_t = api.calls
            try:
                onb = TO.toplu(api, oku_ids)
            except Exception as e:   # noqa: BLE001  toplu hata: tekil okumaya dus (inceleme madde 12), kota DUR'u yukari
                if "kota" in str(getattr(e, "code", None) or e).lower():
                    raise
                log(f"UYARI: toplu kapi okumasi hata ({str(e)[:120]}); tekil okuma"); onb = {}
            ru_onb = {k: v.get("ru") or {} for k, v in onb.items()}
            log(f"toplu kapi okumasi: {len(onb)}/{len(oku_ids)} ilan, {api.calls - c_t} istek | kota {api.remaining}")
    for n, r in enumerate(R, 1):
        lid, cift = r["listing_id"], r["cift"]
        s = dict(ilan=lid, cift=cift, durum="", neden=[], en_az=None, en_kotu=None, istek=None, metin="", ru="")
        satir.append(s)
        c0 = api.calls
        try:
            if dur:
                s.update(durum="KALAN", neden=[dur]); continue
            if yazim and a.azami_ilan and baslayan >= a.azami_ilan:
                s.update(durum="KALAN", neden=[f"parca siniri {a.azami_ilan} ilan"]); continue
            hedef, video, kneden = hedef_kur(r, kaynak, alt)
            pg = (plan.get("girdiler") or {}).get(lid) if yazim else None
            dv = dvs.get(lid) or {}
            bitmemis = yazim and dv.get("durum") not in ("PASS", "GERI_ALINDI", None)
            if yazim and pg is None and not bitmemis:   # kuru planda HAZIR olmayan (BLOK / ZATEN) ilan: okunmaz, yazilmaz
                s.update(durum="ATLA", neden=[f"kuru planda yok (kuru durum {(plan.get('durumlar') or {}).get(lid, '-')})"]); continue
            if yazim:
                if pg is None:
                    s.update(durum="BLOK", neden=["DEVAM kaydi var ama plan girdisi yok"]); continue
                # koddaki en kotu: taze toplu okuma 2 istek + (toplu yanitta ilan yoksa) tekil kapi okumasi 6 -> en kotu +2
                t = ilan_tahmini(pg)["en_kotu"] + TOPLU_ILAN
                if int(api.remaining) - t < KOTA_SINIRI:
                    dur = f"kota: kalan {api.remaining} - en kotu {t} < {KOTA_SINIRI}; ilan baslamadi"
                    s.update(durum="KALAN", neden=[dur]); continue
            elif int(api.remaining) - KAPI_OKUMA - 1 - (KAPI_OKUMA if esit_kalan else 0) < KOTA_SINIRI:
                dur = f"kota: kalan {api.remaining} - {KAPI_OKUMA + 1} okuma < {KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            api.kota_kapisi(f"ilan {lid}")
            if yazim:   # yazmadan hemen once taze toplu okuma (2 istek); yanitta yoksa canli_oku tekil okur
                onb = TO.toplu(api, [lid])
            esit_n = esit_kalan and str(lid) in onb
            c = canli_oku(api, shop, lid, onb)
            if esit_n:   # KURU: toplu == tekil olcumu (inceleme 31 Eki madde 5): plan toplu yanittan, son kontrol tekil okumayla kurulur
                esit_kalan -= 1
                fk = toplu_tekil_fark(c, canli_oku(api, shop, lid))
                s["toplu_tekil"] = "ESIT" if not fk else f"FARK {fk}"
                if fk:
                    s.update(durum="BLOK", neden=[f"toplu okuma tekil okumayla ayni degil: {fk}; toplu yol kullanilmaz"]); continue
            mp = metin_plani(c["L"], c["per"], r["a"], r["b"])
            if not a.metin_yaz:   # VARSAYILAN KAPALI: RU = EN kurali (kupa RU kurucusu yok); galeri metinden ayri
                mp = dict(yaz=False, durum=mp["durum"] if mp["durum"] == "FARKLI_BURC" else "KAPALI:" + mp["durum"], hata=[])
            s["metin"] = mp["durum"]
            if r["a"] == r["b"] and not yazim:
                ru = ru_onb[lid] if lid in ru_onb else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
                s["ru"] = ("RU_ACIK: RU aciklama var (" + sha_metin(html.unescape(ru.get("description") or ""))[:12] + "); kupa RU kurucusu yok, "
                           "RU YAZILMAZ") if ru.get("description") else "RU yok"
            kayit = (ilerleme.get("ilanlar") or {}).get(lid) or pass_kaydi(dv)
            if not bitmemis:
                z = zaten_durum(c, hedef, mp, kayit)
                if z == "ZATEN":
                    if yazim and lid not in (ilerleme.get("ilanlar") or {}):
                        ilerleme.setdefault("ilanlar", {})[lid] = dict(kayit, cift=cift, set=N, hedef=N, kosu=a.kosu, metin=False)
                    s.update(durum="ZATEN", neden=["14 gorsel + 8 bag + video + metin hedefte (ILERLEME / DEVAM kaydi ayni)"]); continue
                if z == "KAYITSIZ":
                    s.update(durum="BLOK", neden=["hedef galeri gorunuyor ama ILERLEME kaydi / video / bag / metin tutmuyor; elle bakilmali"]); continue
                neden = kapilar(c, lid) + kneden + mp["hata"]
                if neden:
                    s.update(durum="BLOK", neden=neden); continue
                gd = plan_girdisi(r, c, hedef, video, mp)
                s.update(en_az=gd["en_az"], en_kotu=gd["en_kotu"])
                if not yazim:
                    girdiler[lid] = gd
                    s.update(durum="PLAN", neden=[] if alt_onayli(alt) else ["alt metin sablonu ONAYLI degil (yazimdan once onay)"]); continue
                if not esit(pg, gd):
                    s.update(durum="BLOK", neden=["canli durum / dosyalar / metin kuru plandan farkli (canli != plan); yazma yok"]); continue
            else:
                gd = pg
                if dv.get("hata") and not a.kurtar:
                    s.update(durum="BLOK", neden=[f"onceki kosu hatayla durdu ({str(dv['hata'])[:100]}); --kurtar gerekir"]); continue
                if kapilar(c, lid):
                    s.update(durum="BLOK", neden=["devam: " + "; ".join(kapilar(c, lid))]); continue
            yd, yn = yedek_kapisi(gd, a.plan_damga, a.yedek_dir, drive)
            if yn:
                s.update(durum="BLOK", neden=yn); continue
            K = Kayit(ilan_out, lid, drive=a.devam_hedef_kok and f"{a.devam_hedef_kok}/DEVAM_{lid}.json" or "")
            if bitmemis:
                K.d = copy.deepcopy(dv)
                if a.kurtar and K.d.get("hata"):
                    K.d.setdefault("hata_gecmis", []).append(K.d.pop("hata"))
                if K.d.get("kota_durdu"):
                    K.d.setdefault("kota_gecmis", []).append(K.d.pop("kota_durdu"))
                devam_uzlas(K, c, gd)
            else:
                K.d = dict(plan_damga=a.plan_damga, cift=cift, set=0, hedef=N, durum="BASLADI", yuklenen={}, silinen=[], son_ids=None)
            K.yaz()
            if K.drive and not K.drive_ok:   # ilk yazimdan once DEVAM Drive'da olmali (kosu olurse kayit kalsin)
                s.update(durum="DUR", neden=["DEVAM_<ilan>.json Drive'a yazilamadi; yazim yok"]); dur = f"ilan {lid} DUR; kosu durdu"; continue
            baslayan += 1
            s.update(en_az=gd["en_az"], en_kotu=ilan_tahmini(gd)["en_kotu"])
            Rz = yaz_ilan(api, shop, lid, gd, c, a.dosya_dir, yd, a.yedek_dir, K, ilan_out, a.yedek_uzak)
            # DEVAM: set 0 (durum_dosyasi json-ilanlar: PASS + set >= hedef geri donmez kurali DEVAM'a uygulanmaz; geri alma kaydi yazilabilir)
            devam.setdefault("ilanlar", {})[lid] = dict(K.d, cift=cift, set=0, hedef=N, durum=K.d.get("durum") or Rz["sonuc"])
            s.update(durum=Rz["sonuc"], neden=Rz["sorun"])
            if Rz["sonuc"] == "PASS":
                ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=cift, set=N, hedef=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                               son_ids=Rz["son_ids"], video=Rz["video"], metin=gd["metin"].get("yaz"))
            else:
                dur = f"ilan {lid} {Rz['sonuc']}; kosu durdu"
        except (Y.Dur, Geri, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani / Etsy / ag hatasi (yazim oncesi okuma)
            m = str(getattr(e, "code", None) or e)[:300]
            s.update(durum="KALAN" if m.startswith("DUR: kota") else "DUR", neden=[m])
            dur = f"ilan {lid} {s['durum']}; kosu durdu"
        finally:
            s["istek"] = api.calls - c0
            e = time.time() - t0
            log(f"{lid} {cift} {s['durum']} | istek {s['istek']}" + (f" | {s['neden'][0][:140]}" if s["neden"] else "") + f" | kota {api.remaining}")
            log(f"ETA: {n}/{len(R)} ilan | gecen {e / 60:.1f} dk | kalan {e / n * (len(R) - n) / 60:.1f} dk | %{100 * n // len(R)}")
    return satir, girdiler, devam, ilerleme


def geri_al_kos(api, shop, a):
    """elle geri alma: --sadece ilanlar, YEDEK.json + dosyalar (yerel ya da --yedek-uzak) + DEVAM (toplu + Drive'daki DEVAM_<ilan>.json:
    kosu ilan ortasinda olduyse yeni gorsel / video kimlikleri buradan)."""
    out = Path(a.out) / "ilanlar"; out.mkdir(parents=True, exist_ok=True)
    R = kapsam(liste_oku(a.liste), a.sadece, a.haric)
    devam = json_oku(a.devam)
    dvs = devam_birlestir(a, devam)
    satir = []
    if R:
        kota_oku(api, shop)
    for r in R:
        lid = r["listing_id"]
        s = dict(ilan=lid, cift=r["cift"], durum="", neden=[], en_az=None, en_kotu=None, istek=None, metin="", ru="")
        satir.append(s); c0 = api.calls
        p = Path(a.yedek_dir) / f"{lid}_{r['cift']}" / "YEDEK.json"
        if not p.exists():
            s.update(durum="BLOK", neden=["YEDEK.json yok"]); continue
        yd = json.loads(p.read_text(encoding="utf-8"))
        if yd.get("plan_damga") != a.plan_damga:
            s.update(durum="BLOK", neden=["YEDEK baska plan damgasiyla"]); continue
        t = istek_tahmini(n_sil=len(yd.get("galeri") or []), metin=bool((yd.get("metin") or {}).get("yaz")))["geri_alma"]
        if int(api.remaining) - t < KOTA_SINIRI:
            s.update(durum="KALAN", neden=[f"kota: kalan {api.remaining} - geri alma en kotu {t} < {KOTA_SINIRI}"]); break
        K = Kayit(out, lid, drive=a.devam_hedef_kok and f"{a.devam_hedef_kok}/DEVAM_{lid}.json" or "")
        K.d = copy.deepcopy(dvs.get(lid) or dict(plan_damga=a.plan_damga, cift=r["cift"], yuklenen={}, silinen=[]))
        gs = geri_al(api, shop, lid, yd, a.yedek_dir, K, a.yedek_uzak)
        s.update(durum="PASS" if not gs else "DUR", neden=gs, istek=api.calls - c0)
        K.d.update(durum="GERI_ALINDI" if not gs else "DUR", geri_alma="TAMAM" if not gs else "BASARISIZ"); K.yaz()
        devam.setdefault("ilanlar", {})[lid] = dict(K.d, cift=r["cift"], set=0, hedef=N)
        if gs:
            break
    return satir, {}, devam, {"ilanlar": {}}


def rapor(satir, girdiler, a, api, out):
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    t0, t1 = istek_tahmini(metin=False), istek_tahmini(metin=True)
    plan_s = [s for s in satir if s["durum"] == "PLAN"]
    R = dict(mod=a.mod, kosu=a.kosu, sayilar=say, istek_tahmini=dict(farkli_burc=t0, ayni_burc=t1),
             plan_en_az=sum(s["en_az"] or 0 for s in plan_s), plan_en_kotu_geri_almasiz=sum(
                 (t1 if s["metin"] and s["metin"] != "FARKLI_BURC" else t0)["en_kotu_geri_almasiz"] for s in plan_s),
             istek=api.calls, kalan_kota=api.remaining, ilanlar=satir)
    if a.mod == "kuru":
        R["plan_damga"] = f"{a.kosu}_{plan_sha(girdiler)[:12]}"
        (out / PLAN_AD).write_text(json.dumps(dict(plan_damga=R["plan_damga"], kosu=a.kosu, girdiler=girdiler,
                                                   durumlar={s["ilan"]: s["durum"] for s in satir}), indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    (out / "RAPOR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# Kupa galeri 78 {a.mod} ({a.kosu})\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                + f"\n\nIstek (kod okumasi, istek_tahmini): ilan basina en az {t0['en_az']} (ayni burc {t1['en_az']}), en kotu geri almasiz "
                  f"{t0['en_kotu_geri_almasiz']} (ayni burc {t1['en_kotu_geri_almasiz']}), geri alma +{t1['geri_alma']}; PLAN {len(plan_s)} ilan "
                  f"toplam en az {R['plan_en_az']} / en kotu {R['plan_en_kotu_geri_almasiz']} | bu kosu istek {api.calls}, kalan kota {api.remaining}\n"
                + (f"plan_damga: {R.get('plan_damga')}\n" if a.mod == "kuru" else "") + "\n## Ilanlar\n"
                + "".join(f"- {s['ilan']} {s['cift']} {s['durum']} istek {s['istek']} metin {s['metin'] or '-'}"
                          + (f" {s['ru']}" if s["ru"] else "") + (f": {'; '.join(s['neden'])[:220]}" if s["neden"] else "") + "\n" for s in satir))
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "durum", "neden", "istek", "metin", "ru"], extrasaction="ignore")
        w.writeheader(); w.writerows(dict(s, neden="; ".join(s["neden"])[:300]) for s in satir)
    log(f"KUPA_GALERI78 {a.mod}: " + " ".join(f"{k}={v}" for k, v in sorted(say.items())) + f" | istek {api.calls} kalan kota {api.remaining}"
        + (f" | plan_damga {R['plan_damga']}" if a.mod == "kuru" else ""))
    return R


def arg(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=("kaynak", "kuru", "yedek", "parti", "yaz", "geri_al"))
    ap.add_argument("--liste", required=True, help="KUPA_TASLAK_LISTE.csv (cift, listing_id)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--kaynak", default="", help="KAYNAK.csv (kaynak modunun ciktisi)")
    ap.add_argument("--dosya-dir", default="", help="kaynak / yaz: kapak/ kart/ stil/ video/ alt klasorleri")
    ap.add_argument("--kart-manifest", default=""); ap.add_argument("--kapak-kayit", default="")
    ap.add_argument("--alt", default=str(ALT_CSV))
    ap.add_argument("--plan", default=""); ap.add_argument("--plan-damga", default=""); ap.add_argument("--confirm", default="")
    ap.add_argument("--yedek-dir", default="", help="yedek ciktisi / yazimda <ilan>_<CIFT>/YEDEK.json")
    ap.add_argument("--yedek-liste", default="", help="yaz / yedek: rclone lsjson -R --hash (Drive yedek klasoru)")
    ap.add_argument("--yedek-var-dir", default="", help="yedek: Drive'da zaten olan <ilan>_<CIFT>/YEDEK.json'lar (tam ise ilan ATLANIR)")
    ap.add_argument("--yedek-uzak", default="", help="geri alma: yedek dosyasi yerelde yoksa rclone kaynagi")
    ap.add_argument("--devam", default=""); ap.add_argument("--ilerleme", default="")
    ap.add_argument("--devam-hedef-kok", default="", help="her yukleme oncesi / sonrasi DEVAM_<ilan>.json kopyasi (rclone hedefi)")
    ap.add_argument("--devam-ilan-dir", default="", help="Drive'dan inen DEVAM_<ilan>.json'lar (devam / geri_al; toplu DEVAM'dan yeni)")
    ap.add_argument("--metin-yaz", action="store_true", help="aciklama + kisisellestirme yazimi (VARSAYILAN KAPALI: RU = EN kurali)")
    ap.add_argument("--kurtar", action="store_true", help="hata kaydi olan DEVAM'i surdur")
    ap.add_argument("--azami-ilan", type=int, default=15, help="yaz / parti: kosu basina en fazla ilan (0 = sinirsiz)")
    ap.add_argument("--toplu-esit-n", type=int, default=2, help="kuru: ilk N ilanda toplu okuma tekil okumayla karsilastirilir (fark -> BLOK)")
    ap.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    a = ap.parse_args(argv)
    if a.mod == "yaz" and (a.confirm != ONAY or not a.plan or not a.plan_damga or not a.dosya_dir or not a.yedek_dir or not a.yedek_liste):
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY} + --plan + --plan-damga + --dosya-dir + --yedek-dir + --yedek-liste")
    if a.mod == "geri_al" and (a.confirm != ONAY_GERI or not a.sadece or not a.yedek_dir or not a.plan_damga):
        raise SystemExit(f"DUR: geri alma icin --confirm {ONAY_GERI} + --sadece + --yedek-dir + --plan-damga")
    if a.mod in ("yedek", "parti") and (not a.plan or not a.plan_damga):
        raise SystemExit("DUR: yedek / parti icin --plan + --plan-damga")
    if a.mod in ("kuru", "yaz") and not a.kaynak:
        raise SystemExit("DUR: --kaynak KAYNAK.csv gerekli")
    return a


def kaynak_mod(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = kapsam(liste_oku(a.liste), a.sadece, a.haric)
    rows = kaynak_kur(R, a.dosya_dir, a.kart_manifest, a.kapak_kayit)
    with open(out / "KAYNAK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KAYNAK_ALAN); w.writeheader(); w.writerows(rows)
    fail = [r for r in rows if r["durum"] != "PASS"]
    log(f"KAYNAK: {len(R)} ilan, {len(rows)} dosya, FAIL {len(fail)}" + "".join(f"\n  {r['cift']} {r['sira']} {r['neden']}" for r in fail[:20]))
    return 1 if fail else 0


def yedek_mod(a, indir=None):
    """ETSY YOK: plan girdilerinden (kapsamdaki) eski medya + YEDEK.json. Drive'da (--yedek-liste lsjson --hash + --yedek-var-dir)
    tam ve hash'i tutan yedegi olan ilan VAR (CDN'e gidilmez). YEDEK_OZET.csv --out'a (yedek klasoru --immutable; zamanli dosya
    oraya konmaz)."""
    p = plan_yukle(a.plan, a.plan_damga)
    R = {r["listing_id"] for r in kapsam(liste_oku(a.liste), a.sadece, a.haric)}
    drive = drive_liste_oku(a.yedek_liste)
    ozet, t0 = [], time.time()
    gl = [(lid, gd) for lid, gd in sorted((p.get("girdiler") or {}).items()) if lid in R]
    for n, (lid, gd) in enumerate(gl, 1):
        alt = f"{lid}_{gd['cift']}"
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        vy = Path(a.yedek_var_dir or "/yok") / alt / "YEDEK.json"
        try:
            if f"{alt}/YEDEK.json" in drive and vy.exists():
                yv = json.loads(vy.read_text(encoding="utf-8"))
                ne = yedek_plana_uygun(yv, gd, a.plan_damga) + yedek_drive_eksik(yv, alt, drive, vy)
                if not ne:
                    ozet.append(dict(ilan=lid, cift=gd["cift"], gorsel=len(yv["galeri"]), video=len(yv["video"]), durum="VAR",
                                     neden="Drive'da tam (boyut + hash); CDN'e gidilmedi", ts_utc=ts))
                    continue
                log(f"  {alt}: Drive'daki yedek eksik / farkli ({ne[:3]}); yeniden kuruluyor (ayni bayt beklenir, --immutable denetler)")
            yd = yedek_kur(gd, a.plan_damga, a.yedek_dir, indir)
            ozet.append(dict(ilan=lid, cift=gd["cift"], gorsel=len(yd["galeri"]), video=len(yd["video"]), durum="PASS", neden="", ts_utc=ts))
        except Exception as e:   # noqa: BLE001
            ozet.append(dict(ilan=lid, cift=gd["cift"], gorsel=0, video=0, durum="FAIL", neden=str(e)[:200], ts_utc=ts))
        g = time.time() - t0
        log(f"ETA yedek: {n}/{len(gl)} | gecen {g:.0f} sn | kalan {g / n * (len(gl) - n):.0f} sn | %{100 * n // len(gl)}")
    Path(a.yedek_dir).mkdir(parents=True, exist_ok=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    with open(Path(a.out) / "YEDEK_OZET.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "gorsel", "video", "durum", "neden", "ts_utc"]); w.writeheader(); w.writerows(ozet)
    say = {}
    for x in ozet:
        say[x["durum"]] = say.get(x["durum"], 0) + 1
    log("YEDEK: " + " ".join(f"{k}={v}" for k, v in sorted(say.items())))
    return 1 if not ozet or any(x["durum"] == "FAIL" for x in ozet) else 0


def sonlandir(api, shop, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir, girdiler, devam, ilerleme = (geri_al_kos if a.mod == "geri_al" else calistir)(api, shop, a)
    rapor(satir, girdiler, a, api, out)
    if a.mod in ("yaz", "geri_al"):
        if a.devam:
            Path(a.devam).write_text(json.dumps(devam, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if a.ilerleme and a.mod == "yaz":
            Path(a.ilerleme).write_text(json.dumps(ilerleme, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return 1 if any(s["durum"] not in ("PASS", "ZATEN", "ATLA") for s in satir) else 0
    return 1 if any(s["durum"] in ("DUR", "FAIL") for s in satir) else 0


def main(argv=None):
    a = arg(argv)
    if a.mod == "kaynak":
        return kaynak_mod(a)
    if a.mod == "yedek":
        return yedek_mod(a)
    if a.mod == "parti":
        return parti_mod(a)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "kuru":
        from yd_envanter_oku import salt_okur
        salt_okur(api)
    return sonlandir(api, shop, a)


if __name__ == "__main__":
    sys.exit(main())
