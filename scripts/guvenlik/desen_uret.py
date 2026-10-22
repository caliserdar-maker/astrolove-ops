#!/usr/bin/env python3
"""DESEN YENIDEN URETIM + TARAMA (SALT OKUMA; PLAN.md KAYIT 22 Eki yontemi). Etsy'ye / Drive'a yazma YOK (cikti klasoru haric).
Musteri desen listesi kaynaktan yeniden uretilir; DEGERLER HICBIR YERE YAZILMAZ: her desen yalniz tuzlu sha256 olarak
<out>/HASH.txt'ye (Drive sahip-ozel TEMP) gider, log'a yalniz tur basina sayi.
Kaynaklar: Etsy getShopReceipts (tum makbuzlar) -> receipt_id, alici adi (+ parcalar), kisisellestirme cevaplari
(kisisel_siparis._kisisel_alanlar: "Name under <Burc>", "Left/Right name", "Your message", "Personalization", property 54,
transaction'daki personaliz* alanlari; + satir / virgul parcalari), message_from_buyer, gift_message, shipments tracking_code;
turetilmis SIPARIS_<son4>, isim cifti "A / B", "A_B" (iki sira, BUYUK ve Title). Drive: --drive-json (rclone lsjson
ciktilari) -> musteri klasoru kimlikleri. Test makbuzlari disarida.
Tuz: --tuz verilmezse rastgele uretilir, ::add-mask:: ile maskelenir, yalniz <out>/TUZ.txt'ye yazilir (Serdar 22 Eki 6a).
--tara DIR: DIR'deki git izli dosyalar BELLEKTE desen listesiyle taranir (FAZ 1 kabul taramasi yolu; Serdar 22 Eki).
<out>/TARAMA.json yalniz yer (dosya, satir) + desen turu + desen sira no; deger ve satir icerigi YOK. Log'a yalniz sayi.
Ek kaynaklar (Serdar 22 Eki): makbuz buyer_email, first_line/second_line/city/zip, gift_sender; --ozet: siparis girdisi
OZET*.json (isim1/isim2/mesaj/tagline; Latin cevirisi, '&' <-> 'and'); mesajlarda 3+ kelimelik gruplar (icerme). --izin: Serdar
onayli izin listesi (kelime / konum), eslesme "izinli" isaretlenir. Tarama ayrica HEAD commit mesajlarini da tarar.
Kullanim: desen_uret.py --out OUT [--tuz HEX] [--drive-json a.json,b.json] [--ozet DIR] [--tara DIR] [--izin IZIN.json]"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
from collections import Counter

KOK = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
sys.path.insert(0, str(KOK / "prodigi"))
from kisisel_siparis import KIRIL_LATIN, _kisisel_alanlar  # noqa: E402

TEST = re.compile(r"^(9000000\d{3}|999001|900000000\d|99000\d{5}|4000000001|1000000001)$")
MESAJ_SORU = re.compile(r"^\s*your message\s*$", re.I)
KOTA_TABAN = 10                  # CLAUDE.md (Serdar 15 Eki): x-remaining-today < 10 ise DUR
TARA_AZAMI = 3_000_000           # bayt; daha buyuk dosya taranmaz (sayilir)
ADRES_ALAN = ("first_line", "second_line", "city", "zip")
OZET_ALAN = {"isim1": "isim", "isim2": "isim", "isim": "isim", "mesaj": "mesaj", "tagline": "mesaj"}


def norm(v):
    return " ".join(str(v or "").split()).casefold()


def parcalar(v, kelime=True):
    """Tum deger + satir / virgul parcalari; kelime=True ise 3+ harfli kelimeler de (ad icin). Mesajda kelime YOK:
    "ever", "love" gibi genel kelimeler taramada sahte eslesme uretir."""
    v = str(v or "")
    out = {v}
    for ayirici in ("\n", ",", ";"):
        out |= {p for p in v.split(ayirici)}
    if kelime:
        out |= {w for w in re.split(r"[^\w']+", v) if len(w) >= 3}
    return {p.strip() for p in out if len(p.strip()) >= 3}


def mesaj_bicimleri(v):
    """Mesaj + donusmus bicimleri (uretim hatti: '&' <-> 'and') ve 3+ kelimelik ardisik kelime gruplari (icerme kontrolu:
    tagline daha uzun bir mesajin icinde olabilir). Tek kelime YOK (genel kelime sahte eslesmesi)."""
    v = str(v or "")
    out = set()
    for b in {v, v.replace("&", " and "), re.sub(r"(?i)\band\b", "&", v)}:
        out |= parcalar(b, kelime=False)
        k = re.findall(r"[\w'&]+", b)
        out |= {" ".join(k[i:j]) for i in range(len(k)) for j in range(i + 3, len(k) + 1)}
    return out


def latin(v):
    return "".join(KIRIL_LATIN.get(c, c) for c in str(v).upper())


def ozet_oku(kok):
    """Drive SIPARIS_ISIM/DIJITAL kopyasindaki siparis JSON'lari -> dosya basina [(tur, deger)]; test makbuzu disarida."""
    hepsi = []

    def gez(x, out):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in OZET_ALAN and isinstance(v, str) and v.strip():
                    out.append((OZET_ALAN[k], v.strip()))
                else:
                    gez(v, out)
        elif isinstance(x, list):
            for v in x:
                gez(v, out)
    for f in sorted(pathlib.Path(kok).rglob("*.json")) if kok else []:
        if any(TEST.match(p) for p in f.parts):
            continue
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if TEST.match(str(j.get("receipt") or "") if isinstance(j, dict) else ""):
            continue
        out = []
        gez(j, out)
        if out:
            hepsi.append(out)
    return hepsi


def kisisel(t):
    """-> (isimler, mesajlar) bir transaction icin; soru metni kisisel_siparis.SORU_RE ile."""
    isim, mesaj = [], []
    for soru, cevap in _kisisel_alanlar(t):
        if not cevap:
            continue
        if MESAJ_SORU.match(soru):
            mesaj.append(cevap)
        else:
            isim += [x.strip() for x in re.split(r"[\n,;]", cevap) if x.strip()]
    return isim, mesaj


def isim_ekle(ekle, tur, isim):
    """Ad parcalari + Latin harfe cevrilmis bicim + iki sirali isim ciftleri (BUYUK ve Title)."""
    tum = []
    for v in isim:
        for b in {v, latin(v)}:
            tum.append(b)
            for p in parcalar(b):
                ekle(tur, p)
    for i, a1 in enumerate(tum):
        for a2 in tum[i + 1:]:
            if norm(a1) == norm(a2):
                continue
            for x, y in ((a1, a2), (a2, a1)):
                for f in (str.upper, str.title):
                    ekle("isim_cifti", f"{f(x)} / {f(y)}"); ekle("isim_cifti", f"{f(x)}_{f(y)}")


def desen_uret(api, shop, drive_json, ozet_dir=""):
    """-> {norm(desen): tur}. Degerler yalniz bellekte."""
    desen, tur = {}, Counter()

    def ekle(t, v):
        n = norm(v)
        if len(n) >= 3 and n not in desen:
            desen[n] = t; tur[t] += 1

    ofs, makbuz, test = 0, 0, 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"limit": 100, "offset": ofs}) or {}
        if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
            raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")
        r = d.get("results") or []
        for rc in r:
            rid = str(rc.get("receipt_id") or "")
            if TEST.match(rid):
                test += 1
                continue
            makbuz += 1
            ekle("receipt", rid); ekle("siparis_klasor", f"SIPARIS_{rid[-4:]}")
            for alan in ("name", "gift_sender"):
                for p in parcalar(rc.get(alan)):
                    ekle("alici_adi", p)
            ekle("eposta", rc.get("buyer_email"))
            for alan in ADRES_ALAN:
                ekle("adres", rc.get(alan))
            for alan in ("message_from_buyer", "gift_message"):
                for p in mesaj_bicimleri(rc.get(alan)):
                    ekle("mesaj", p)
            for sh in rc.get("shipments") or []:
                ekle("takip", sh.get("tracking_code"))
            for t in rc.get("transactions") or []:
                isim, mesaj = kisisel(t)
                for v in mesaj:
                    for p in mesaj_bicimleri(v):
                        ekle("mesaj", p)
                isim_ekle(ekle, "kisisellestirme", isim)
        ofs += len(r)
        if not r or ofs >= (d.get("count") or 0):
            break
    for jf in [x for x in drive_json.split(",") if x]:
        for e in json.load(open(jf)):
            if e.get("IsDir") and e.get("ID"):
                ekle("drive_kimlik", e["ID"])
    oz = ozet_oku(ozet_dir)
    for dosya in oz:
        for _, v in [x for x in dosya if x[0] == "mesaj"]:
            for p in mesaj_bicimleri(v):
                ekle("siparis_mesaj", p)
        isim_ekle(ekle, "siparis_isim", list(dict.fromkeys(v for t_, v in dosya if t_ == "isim")))
    return desen, dict(makbuz=makbuz, test=test, ozet_dosya=len(oz), tur=dict(tur))


def izin_oku(yol):
    """Serdar onayli izin listesi (Drive, sahip-ozel): {"kelimeler": [{"kelime", "gerekce"}], "konumlar": [{"dosya", "satir",
    "gerekce"}]}. Kelime: yaygin kod/sozluk kelimesi (her yerde izinli); konum: tek dosya satiri. -> (kelime kumesi, konum kumesi)"""
    if not yol or not os.path.exists(yol):
        return set(), set()
    j = json.load(open(yol, encoding="utf-8"))
    return ({norm(k["kelime"]) for k in j.get("kelimeler") or []},
            {(k["dosya"], int(k["satir"])) for k in j.get("konumlar") or []})


def tara(kok, desen, izin=(set(), set())):
    """git izli dosyalarda + HEAD commit mesajlarinda desen ara (BELLEKTE). -> (yerler, commitler, ozet). Deger/satir icerigi
    yok. Eslesme: casefold, bosluk dizisi esnek, iki yaninda harf/rakam/_ yok. Izin listesindeki kelime/konum "izinli" isaretlenir."""
    sira = {n: i for i, n in enumerate(sorted(desen), 1)}
    alt = sorted(desen, key=len, reverse=True)
    rx = re.compile(r"(?<!\w)(" + "|".join(re.escape(n).replace(r"\ ", r"\s+") for n in alt) + r")(?!\w)") if alt else None
    kelime, konum = izin
    dosyalar = subprocess.run(["git", "-C", str(kok), "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    yer, atla = [], Counter()
    for yol in [x for x in dosyalar if x]:
        p = pathlib.Path(kok) / yol
        if not p.is_file():
            atla["yok"] += 1; continue
        if p.stat().st_size > TARA_AZAMI:
            atla["buyuk"] += 1; continue
        b = p.read_bytes()
        if b"\x00" in b[:8000]:
            atla["ikili"] += 1; continue
        for no, satir in enumerate(b.decode("utf-8", "replace").casefold().split("\n"), 1):
            for m in rx.finditer(satir) if rx else ():
                n = " ".join(m.group(1).split())
                yer.append(dict(dosya=yol, satir=no, tur=desen.get(n, "?"), sira=sira.get(n, 0),
                                izinli=n in kelime or (yol, no) in konum))
    log = subprocess.run(["git", "-C", str(kok), "log", "--format=%H%x00%B%x01", "HEAD"], capture_output=True).stdout.decode("utf-8", "replace")
    com, n_com = [], 0
    for kayit in log.split("\x01"):
        if "\x00" not in kayit:
            continue
        n_com += 1
        sha, msj = kayit.strip().split("\x00", 1)
        for m in rx.finditer(msj.casefold()) if rx else ():
            n = " ".join(m.group(1).split())
            com.append(dict(commit=sha[:10], tur=desen.get(n, "?"), sira=sira.get(n, 0), izinli=n in kelime))
    disi = [y for y in yer if not y["izinli"]]
    oz = dict(dosya=len({y["dosya"] for y in yer}), eslesme=len(yer), desen=len({y["sira"] for y in yer}),
              tur=dict(Counter(y["tur"] for y in yer)), atlanan=dict(atla), izin_disi=len(disi),
              izin_disi_dosya=len({y["dosya"] for y in disi}), izin_disi_tur=dict(Counter(y["tur"] for y in disi)),
              commit_taranan=n_com, commit_eslesme=len(com), commit_izin_disi=len({c["commit"] for c in com if not c["izinli"]}))
    return yer, com, oz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuz", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--drive-json", default="")
    ap.add_argument("--tara", default="")
    ap.add_argument("--ozet", default="", help="Drive SIPARIS_ISIM/DIJITAL OZET*.json kopyasi (dizin)")
    ap.add_argument("--izin", default="", help="Serdar onayli izin listesi JSON (Drive, sahip-ozel)")
    a = ap.parse_args()
    tuz = a.tuz or secrets.token_hex(24)
    print(f"::add-mask::{tuz}", flush=True)
    if not re.fullmatch(r"[0-9a-f]{16,64}", tuz):
        raise SystemExit("HATA: tuz hex olmali")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    desen, bilgi = desen_uret(api, os.environ["ETSY_SHOP_ID"], a.drive_json, a.ozet)
    (out / "TUZ.txt").write_text(tuz + "\n")
    with open(out / "HASH.txt", "w") as f:
        for n in sorted(desen):
            f.write(hashlib.sha256((tuz + n).encode()).hexdigest() + "\n")
    print(f"DESEN_URET makbuz {bilgi['makbuz']} (test disarida {bilgi['test']}) | siparis ozet dosyasi {bilgi['ozet_dosya']} | "
          f"desen {len(desen)} | tur {bilgi['tur']} | "
          f"istek {api.calls} | kota {api.remaining}")
    if a.tara:
        izin = izin_oku(a.izin)
        yer, com, oz = tara(a.tara, desen, izin)
        (out / "TARAMA.json").write_text(json.dumps(dict(ozet=oz, yerler=yer, commitler=com), ensure_ascii=False, indent=1),
                                         encoding="utf-8")
        print(f"TARAMA dosya {oz['dosya']} | eslesme {oz['eslesme']} | farkli desen {oz['desen']} | tur {oz['tur']} | "
              f"atlanan {oz['atlanan']} | izin listesi {len(izin[0])} kelime + {len(izin[1])} konum")
        print(f"TARAMA izin disi: eslesme {oz['izin_disi']} | dosya {oz['izin_disi_dosya']} | tur {oz['izin_disi_tur']}")
        print(f"COMMIT mesaji: taranan {oz['commit_taranan']} | eslesme {oz['commit_eslesme']} | izin disi commit {oz['commit_izin_disi']}")


if __name__ == "__main__":
    main()
