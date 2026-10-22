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
Ek kaynaklar (Serdar 22 Eki): makbuz buyer_email (token'da email_r yok: bos gelir), first_line/second_line/city/zip,
gift_sender; mesajlarda 3+ kelimelik gruplar (noktalamasiz ve noktalamali; '&' <-> 'and'); isim cifti "A / B", "A_B", "A & B",
"A and B"; Kiril adin Latin bicimi. Siparis OZET dosyalari kapsam disi (isim/mesaj icermez). --izin: Serdar onayli izin listesi
(kelime / konum / e-posta). Tarama dosya icerigi + dosya yollari + HEAD commit mesajlari; "_" kelime siniridir. Eslesme
sinifi (Serdar 22 Eki secenek C): tek basina ad parcasi "bilgi", digerleri "engel"; genel e-posta kurali musteri_tara'dan.
Kullanim: desen_uret.py --out OUT [--tuz HEX] [--drive-json a.json,b.json] [--tara DIR] [--izin IZIN.json]"""
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
SINIR_ONCE, SINIR_SONRA = r"(?<![^\W_])", r"(?![^\W_])"   # harf/rakam degil; "_" SINIRDIR (AstroLoveArt_<Ad>_<Ad>)
TEK_AD_TUR = {"alici_adi", "kisisellestirme"}               # tek kelimelik ad parcasi -> "bilgi" (Serdar 22 Eki secenek C)
sys.path.insert(0, str(KOK / "guvenlik"))
import musteri_tara as mt  # noqa: E402  (genel e-posta kurali tek kaynak)


def norm(v):
    return " ".join(str(v or "").split()).casefold()


def parcalar(v, kelime=True):
    """Tum deger + satir / virgul parcalari; kelime=True ise 3+ harfli kelimeler de (ad icin). Mesajda kelime YOK ve
    parca en az 2 kelime: "ever", "love" gibi genel kelimeler taramada sahte eslesme uretir."""
    v = str(v or "")
    out = {v}
    for ayirici in ("\n", ",", ";"):
        out |= {p for p in v.split(ayirici) if kelime or len(p.split()) >= 2}
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
        for k in (re.findall(r"[\w'&]+", b), b.split()):   # noktalamasiz ve noktalamali (virgullu) kelime gruplari
            out |= {" ".join(k[i:j]) for i in range(len(k)) for j in range(i + 3, len(k) + 1)}
    return out


def latin(v):
    return "".join(KIRIL_LATIN.get(c, c) for c in str(v).upper())


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
                    for ara in (" / ", "_", " & ", " and ", " ve "):
                        ekle("isim_cifti", f"{f(x)}{ara}{f(y)}")


def desen_uret(api, shop, drive_json):
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
    return desen, dict(makbuz=makbuz, test=test, tur=dict(tur))


def izin_oku(yol):
    """Serdar onayli izin listesi (Drive, sahip-ozel): {"kelimeler": [{"kelime", "gerekce"}], "konumlar": [{"dosya", "satir",
    "gerekce"}], "epostalar": [{"adres", "gerekce"}]}. -> (kelime kumesi, konum kumesi, e-posta kumesi)"""
    if not yol or not os.path.exists(yol):
        return set(), set(), set()
    j = json.load(open(yol, encoding="utf-8"))
    return ({norm(k["kelime"]) for k in j.get("kelimeler") or []},
            {(k["dosya"], int(k["satir"])) for k in j.get("konumlar") or []},
            {k["adres"].lower() for k in j.get("epostalar") or []})


def sinif(n, tur, izin, yer=None):
    """-> "izinli" | "bilgi" | "engel". Serdar 22 Eki (secenek C): sozluk/kod kelimesiyle cakisabilen TEK BASINA ad parcasi
    engel degil, "bilgi"; isim cifti, mesaj, receipt, takip, adres, posta kodu, Drive kimligi, e-posta engeldir."""
    kelime, konum, _ = izin
    if n in kelime or (yer is not None and yer in konum):
        return "izinli"
    if tur in TEK_AD_TUR and " " not in n:
        return "bilgi"
    return "engel"


def eposta_bul(metin, izin):
    """musteri_tara genel e-posta kurali (ornek alan adlari + SAHIP_EPOSTA disi her adres) + izinli hizmet adresleri."""
    out = 0
    for m in mt.KALIP["eposta"].finditer(metin):
        e = m.group(0).lower()
        alan = e.split("@", 1)[1]
        if (hashlib.sha256(e.encode()).hexdigest() in mt.IZINLI_EPOSTA_SHA or mt.DOSYA_UZANTI.search(e)
                or mt.ORNEK_ALAN.search(alan) or e in izin[2]):
            continue
        out += 1
    return out


def dosya_listesi(kok):
    """git deposu/worktree ise izli dosyalar, degilse dizindeki tum dosyalar (.git haric)."""
    r = subprocess.run(["git", "-C", str(kok), "ls-files", "-z"], capture_output=True)
    if r.returncode == 0 and r.stdout:
        return [x for x in r.stdout.decode().split("\0") if x], True
    out = []
    for d, alt, fs in os.walk(kok):
        alt[:] = [a for a in alt if a != ".git"]
        out += [os.path.relpath(os.path.join(d, f), kok) for f in fs if f != ".git"]
    return sorted(out), False


def tara(kok, desen, izin=(set(), set(), set()), commit_tara=True):
    """git izli dosyalarin icerigi + DOSYA YOLLARI (satir 0) + HEAD commit mesajlarinda desen ara (BELLEKTE).
    -> (yerler, commitler, ozet). Deger/satir icerigi yok. Eslesme: casefold, bosluk dizisi esnek, iki yaninda harf/rakam yok
    ("_" sinir sayilir). Izin listesine uyan eslesme "izinli" isaretlenir."""
    sira = {n: i for i, n in enumerate(sorted(desen), 1)}
    alt = sorted(desen, key=len, reverse=True)
    rx = re.compile(SINIR_ONCE + "(" + "|".join(re.escape(n).replace(r"\ ", r"\s+") for n in alt) + ")" + SINIR_SONRA) if alt else None
    dosyalar, git_mi = dosya_listesi(kok)
    yer, atla = [], Counter()

    def kaydet(yol, no, metin, ham=""):
        for m in rx.finditer(metin) if rx else ():
            n = " ".join(m.group(1).split())
            t = desen.get(n, "?")
            yer.append(dict(dosya=yol, satir=no, tur=t, sira=sira.get(n, 0), sinif=sinif(n, t, izin, (yol, no))))
        for _ in range(eposta_bul(ham, izin) if ham else 0):
            yer.append(dict(dosya=yol, satir=no, tur="eposta_genel", sira=0, sinif="engel"))
    for yol in [x for x in dosyalar if x]:
        kaydet(yol, 0, yol.casefold())                    # dosya yolu / adi (satir 0)
        p = pathlib.Path(kok) / yol
        if not p.is_file():
            atla["yok"] += 1; continue
        if p.stat().st_size > TARA_AZAMI:
            atla["buyuk"] += 1; continue
        b = p.read_bytes()
        if b"\x00" in b[:8000]:
            atla["ikili"] += 1; continue
        for no, satir in enumerate(b.decode("utf-8", "replace").split("\n"), 1):
            kaydet(yol, no, satir.casefold(), satir)
    log = subprocess.run(["git", "-C", str(kok), "log", "--format=%H%x00%B%x01", "HEAD"], capture_output=True).stdout.decode(
        "utf-8", "replace") if (commit_tara and git_mi) else ""
    com, n_com = [], 0
    for kayit in log.split("\x01"):
        if "\x00" not in kayit:
            continue
        n_com += 1
        sha, msj = kayit.strip().split("\x00", 1)
        msj = msj.casefold()
        for m in rx.finditer(msj) if rx else ():
            n = " ".join(m.group(1).split())
            t = desen.get(n, "?")
            com.append(dict(commit=sha[:10], tur=t, sira=sira.get(n, 0), sinif=sinif(n, t, izin)))
    engel = [y for y in yer if y["sinif"] == "engel"]
    bilgi = [y for y in yer if y["sinif"] == "bilgi"]
    oz = dict(dosya=len({y["dosya"] for y in yer}), eslesme=len(yer), desen=len({y["sira"] for y in yer if y["sira"]}),
              tur=dict(Counter(y["tur"] for y in yer)), atlanan=dict(atla),
              engel=len(engel), engel_dosya=len({y["dosya"] for y in engel}), engel_tur=dict(Counter(y["tur"] for y in engel)),
              bilgi=len(bilgi), bilgi_dosya=len({y["dosya"] for y in bilgi}), bilgi_desen=len({y["sira"] for y in bilgi}),
              commit_taranan=n_com, commit_eslesme=len(com),
              commit_engel=len({c["commit"] for c in com if c["sinif"] == "engel"}),
              commit_bilgi=len({c["commit"] for c in com if c["sinif"] == "bilgi"}))
    return yer, com, oz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuz", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--drive-json", default="")
    ap.add_argument("--tara", default="")
    ap.add_argument("--izin", default="", help="Serdar onayli izin listesi JSON (Drive, sahip-ozel)")
    ap.add_argument("--tara-ek", default="", help="etiket=DIZIN,...: ek agaclar (P0.7 dallari, P0.5 OCR metinleri); ayri ozet")
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
    desen, bilgi = desen_uret(api, os.environ["ETSY_SHOP_ID"], a.drive_json)
    (out / "TUZ.txt").write_text(tuz + "\n")
    with open(out / "HASH.txt", "w") as f:
        for n in sorted(desen):
            f.write(hashlib.sha256((tuz + n).encode()).hexdigest() + "\n")
    print(f"DESEN_URET makbuz {bilgi['makbuz']} (test disarida {bilgi['test']}) | desen {len(desen)} | tur {bilgi['tur']} | "
          f"istek {api.calls} | kota {api.remaining}")
    if a.tara:
        izin = izin_oku(a.izin)
        yer, com, oz = tara(a.tara, desen, izin)
        (out / "TARAMA.json").write_text(json.dumps(dict(ozet=oz, yerler=yer, commitler=com), ensure_ascii=False, indent=1),
                                         encoding="utf-8")
        print(f"TARAMA dosya {oz['dosya']} | eslesme {oz['eslesme']} | farkli desen {oz['desen']} | tur {oz['tur']} | "
              f"atlanan {oz['atlanan']} | izin listesi {len(izin[0])} kelime + {len(izin[1])} konum + {len(izin[2])} e-posta")
        print(f"TARAMA ENGEL: eslesme {oz['engel']} | dosya {oz['engel_dosya']} | tur {oz['engel_tur']} -> "
              f"{'PASS' if oz['engel'] == 0 else 'FAIL'}")
        print(f"TARAMA bilgi (tek basina ad parcasi): eslesme {oz['bilgi']} | dosya {oz['bilgi_dosya']} | desen {oz['bilgi_desen']}")
        print(f"COMMIT mesaji (yalniz HEAD): taranan {oz['commit_taranan']} | eslesme {oz['commit_eslesme']} | "
              f"engel commit {oz['commit_engel']} | bilgi commit {oz['commit_bilgi']}")
    ek = {}
    for parca in [x for x in a.tara_ek.split(",") if x]:
        etiket, dizin = parca.split("=", 1)
        yer, com, oz = tara(dizin, desen, izin_oku(a.izin))
        ek[etiket] = dict(ozet=oz, yerler=yer, commitler=com)
        print(f"EK {etiket}: dosya {oz['dosya']} | ENGEL {oz['engel']} (tur {oz['engel_tur']}) -> {'PASS' if oz['engel'] == 0 else 'FAIL'} | "
              f"bilgi {oz['bilgi']} | atlanan {oz['atlanan']} | commit taranan {oz['commit_taranan']} engel {oz['commit_engel']}")
    if ek:
        (out / "TARAMA_EK.json").write_text(json.dumps(ek, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
