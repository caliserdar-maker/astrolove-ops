#!/usr/bin/env python3
"""IG / FB / YouTube 78 cift yayin plani (KURU; Serdar 25 Kas karari, Merkez iletimi). YAZMA YOK: yalniz CSV + ozet.
Cift basina 4 icerik (Pinterest seti gibi): poster, kart, altin yakin cekim (gorsel) + video (v5).
  Instagram: 3 gorsel gonderi + 1 Reel; Facebook Sayfasi: 3 gorsel + 1 Reel; YouTube: yalniz video Short
  (YouTube topluluk/gorsel gonderi API'si pilot, genel erisim yok). 78 x 9 = 702 satir.
Metin: Pinterest pin metni (surum=genel; sezonluk ifade yok) baslik + aciklama + Etsy linki (astroloveart.etsy.com/listing/<id>).
Sira: pin78_takvim.ONCELIK + data/sosyal/pinterest/SIRA_78.csv; 4 tur, her turda her cift 1 kez, turler karisik
(pin78_takvim gibi; ayni cift ayni platformda >= 7 gun arayla). Saatler ve gunluk sayi parametre (Merkez karari; varsayilan oneri A).
Kapilar (PASS/FAIL): 702 satir, cift basina platform/tur tam, gunluk sinir, ayni cift >= 7 gun, sezon/yasak ifade yok,
uzun tire yok, "AstroLove" yalniz yok, YouTube basligi <= 100, Threads yok, link bicimi. Medya kaynagi yoksa satir
'kaynak yok' (bilgi; plan yine yazilir, onayla bu satirlari kabul etmez).
Cikis: 0 kapi PASS + metin/medya tam; 3 kapi PASS ama eksik (takvime yazilmaz); 1 kapi FAIL; 2 DUR.
Kullanim: plan78.py --metin M.csv --baslangic 2026-12-13 --cikti PLAN.csv --ilk-no 101 --mevcut-en-buyuk 2 [--ig 2 --fb 2 --yt 1]"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secim  # noqa: E402
import video_kaynak  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ONCELIK = ['CANCER_LEO', 'SCORPIO_TAURUS', 'PISCES_VIRGO', 'CANCER_LIBRA']   # pin78_takvim.py ile ayni
TURLER = ('poster', 'kart', 'altin', 'video')
TR, ET = ZoneInfo("Europe/Istanbul"), ZoneInfo("America/New_York")
# ABD denetimi (Serdar 25 Kas): IG/FB hafta ici 10:00-12:00 ET (Istanbul 18:00-20:00; 14 Mar 2027'den sonra 17:00-19:00,
# zoneinfo ile otomatik). YouTube icin ayri kural yok: oneri her gun 11:00 ET.
SAAT_ET = {"instagram": ["10:00", "11:00", "11:40"], "facebook": ["10:30", "11:20", "11:50"], "youtube": ["11:00", "11:45"]}
YALNIZ_HAFTA_ICI = {"instagram", "facebook"}
YT_KALIP = ["{A} + {B} as One Symbol? Zodiac Couple Gift Idea",
            "What {A} and {B} Look Like as One Sign | Couple Gift for Him or Her",
            "{A} and {B} Combined Zodiac Symbol | Personalized Gift for Couples",
            "One Symbol for {A} + {B}? Zodiac Gift for Boyfriend or Girlfriend",
            "{A} x {B}: Two Signs, One Symbol | Anniversary Gift Idea"]
IG_ALICI = "A personalized zodiac gift for your boyfriend, girlfriend, husband or wife, with both names and your message."
IG_LINK = "Tap the link in our bio to make yours on Etsy."
FB_LINK = "Link in the first comment."
YT_LINK = "Shop link is on our channel page."
SINIR = {"instagram": 25, "facebook": 25, "youtube": 6}   # guvenli ust sinir (IG 50/24s, FB Reel 30/24s, YT kota; tahmin pay)


def _etsy_yasak():
    """Tek kaynak etsy_common.METIN_KESIN + METIN_BAGLAM; modul calistirilmadan (ag/requests yok) sabit olarak okunur."""
    import ast
    agac = ast.parse(open(os.path.join(KOK, "scripts/etsy/etsy_common.py"), encoding="utf-8").read())
    d = {}
    for n in agac.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], "id", "") in ("METIN_KESIN", "METIN_BAGLAM"):
            d[n.targets[0].id] = ast.literal_eval(n.value)
    if set(d) != {"METIN_KESIN", "METIN_BAGLAM"} or not d["METIN_KESIN"]:
        raise SystemExit("DUR: etsy_common METIN_KESIN / METIN_BAGLAM okunamadi")
    return d["METIN_KESIN"] + d["METIN_BAGLAM"]


SEZON = (r"\bvalentine(?:'s|\u2019s|s)?\b|\bchristmas\b|\bxmas\b|\bholidays?\b|\bblack\s+friday\b|\bcyber\s+monday\b|"
         r"\bmother(?:'s|\u2019s|s)?\s+day\b|\bfather(?:'s|\u2019s|s)?\s+day\b|\bhalloween\b|\beaster\b|\bnew\s+year\b|"
         r"\b14\s*(?:th\s+)?(?:of\s+)?feb(?:ruary)?\b|\bfeb(?:ruary)?\s+14\b|(?<![/\d])\b20\d\d\b")
YASAK = [("sezonluk", re.compile(SEZON, re.I)), ("AstroLove (Art'siz)", re.compile(r"(?i)astrolove(?!art)"))] + \
        [(ad, re.compile(rx, re.I)) for ad, rx in _etsy_yasak()]


def yasak_bul(t):
    for ad, rx in YASAK:
        m = rx.search(t)
        if m:
            return f"{ad} '{m.group(0)}'"
    return ""


def ayar():
    p = os.environ.get("SOSYAL_PIN78_KAYNAK", os.path.join(KOK, "config/sosyal_pin78_kaynak.json"))
    try:
        d = json.load(open(p))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def sira():
    s = [r["cift"] for r in sorted(csv.DictReader(open(os.path.join(KOK, "data/sosyal/pinterest/SIRA_78.csv"), encoding="utf-8")),
                                   key=lambda r: int(r["sira"]))]
    return ONCELIK + [c for c in s if c not in ONCELIK]


def metinler(yol):
    out = {}
    for r in csv.DictReader(open(yol, encoding="utf-8")):
        if (r.get("surum") or "").strip() == "genel":
            k = (r["cift"].strip(), r["konsept"].strip())
            if k in out:
                raise ValueError(f"metin dosyasinda tekrar: {k}")
            out[k] = r
    return out


def medya(cift, tur, platform, a):
    a_, b_ = cift.lower().split("_", 1)
    if tur == "video":
        try:
            return video_kaynak.yol(cift)
        except ValueError:
            return ""
    k, d = ("ig_gorsel_klasor", "ig_gorsel_dosya") if platform == "instagram" else ("gorsel_klasor", "gorsel_dosya")
    if not a.get(k) or not (a.get(d) or {}).get(tur):
        return ""
    return f"{a[k].rstrip('/')}/{a[d][tur].format(CIFT=cift, a=a_, b=b_)}"


def etiketler(cift, platform):
    a, b = [x.lower() for x in cift.split("_", 1)]
    burc = [f"#{a}"] + ([f"#{b}"] if b != a else [])
    if platform == "youtube":   # en cok 3, burc adlari dahil
        return burc + ["#zodiaccouple"]
    return burc + ["#zodiaccouple", "#astrologygift", "#personalizedgift"]   # instagram: en cok 5, ikisi burc


def metin_kur(platform, m, link, cift, i):
    b, ac = m["baslik"].strip(), m["aciklama"].strip()
    A, B = [x.capitalize() for x in cift.split("_", 1)]
    if platform == "youtube":
        baslik = YT_KALIP[i % len(YT_KALIP)].format(A=A, B=B)
        return f"{baslik}\n{ac}\n\n{YT_LINK}\n\n{' '.join(etiketler(cift, platform))}"
    if platform == "instagram":
        return f"{b}\n\n{ac}\n\n{IG_ALICI} {IG_LINK}\n\n{' '.join(etiketler(cift, platform))}"
    return f"{b}\n\n{ac}\n\n{FB_LINK}"   # facebook: link ilk yorumda (satirin link sutunu)


def slot_uret(bas, platform, n):
    """bas gununden itibaren (Istanbul tarihi) ET saatlerine gore yayin anlari; IG/FB yalniz hafta ici (ET gunu)."""
    g = 0
    while True:
        gun = bas + timedelta(days=g)
        g += 1
        if platform in YALNIZ_HAFTA_ICI and gun.weekday() >= 5:
            continue
        for hh in SAAT_ET[platform][:n]:
            t = datetime.combine(gun, datetime.strptime(hh, "%H:%M").time(), tzinfo=ET)
            yield t.astimezone(TR)


def plan(metin_yolu, bas, gunluk, ilk_no=1):
    a, mt = ayar(), metinler(metin_yolu)
    ids = {r["cift"]: r["listing_id"] for r in csv.DictReader(open(os.path.join(KOK, "data/pod/pod78_ids.csv"), encoding="utf-8"))}
    ciftler = sira()
    satirlar, eksik = [], Counter()
    for platform, turler in (("instagram", TURLER), ("facebook", TURLER), ("youtube", ("video",))):
        sl = slot_uret(bas, platform, gunluk[platform])
        # tur karisimi (pin78_takvim ile ayni): k. turda cift i -> turler[(i + k) % len]; her turda her cift 1 kez
        sira_pt = [(c, turler[(i + k) % len(turler)], i) for k in range(len(turler)) for i, c in enumerate(ciftler)]
        for c, t, i in sira_pt:
            zaman = next(sl).strftime("%Y-%m-%d %H:%M")
            link = f"https://astroloveart.etsy.com/listing/{ids[c]}"
            m = mt.get((c, t))
            md = medya(c, t, platform, a)
            if not m:
                eksik["metin"] += 1
            if not md:
                eksik["medya"] += 1
            gorsel = t != "video"
            satirlar.append({"tarih_saat_TR": zaman, "platform": platform,
                             "tur": {"video": "short" if platform == "youtube" else "reel"}.get(t, "gorsel"),
                             "medya": md, "metin": metin_kur(platform, m, link, c, i) if m else "", "link": link, "pano": "",
                             "yz_beyani": "hayir", "gorunurluk": "public" if platform == "youtube" else "",
                             "alt_metin": (m or {}).get("alt_metin", "").strip() if (gorsel and platform == "instagram") else "",
                             "ONAY": "", "ONAY_OZET": "", "DURUM": "", "sonuc_no": "", "not": f"PLAN78 {c} {t}",
                             "_cift": c, "_konsept": t})
    satirlar.sort(key=lambda s: (s["tarih_saat_TR"], s["platform"]))
    for k, s in enumerate(satirlar):
        s["satir_no"] = str(ilk_no + k)
    return satirlar, eksik


def kapilar(satirlar, gunluk):
    h = []
    if len(satirlar) != 78 * 9:
        h.append(f"satir sayisi {len(satirlar)} != 702")
    say = Counter((s["_cift"], s["platform"], s["_konsept"]) for s in satirlar)
    if any(v != 1 for v in say.values()) or len(say) != 78 * 9:
        h.append("cift/platform/tur tekrar ya da eksik")
    gunp = Counter((s["tarih_saat_TR"][:10], s["platform"]) for s in satirlar)
    for (g, p), v in gunp.items():
        if v > min(gunluk[p], SINIR[p]):
            h.append(f"{g} {p}: {v} gonderi > {gunluk[p]}")
    son = defaultdict(list)
    for s in satirlar:
        son[(s["_cift"], s["platform"])].append(datetime.strptime(s["tarih_saat_TR"], "%Y-%m-%d %H:%M"))
    for k, ts in son.items():
        ts.sort()
        for x, y in zip(ts, ts[1:]):
            if y - x < timedelta(days=7):
                h.append(f"{k}: ayni cift 7 gunden yakin ({x:%d.%m} {y:%d.%m})")
                break
    for s in satirlar:
        t = s["metin"]
        y = yasak_bul(t) if t else ""
        if y:
            h.append(f"satir {s['satir_no']}: yasak/sezonluk ifade {y}")
        if s["platform"] == "youtube" and t and re.search(r"[<>]", t.splitlines()[0]):
            h.append(f"satir {s['satir_no']}: YouTube basliginda < ya da >")
        n = s["satir_no"]
        if not re.fullmatch(r"https://astroloveart\.etsy\.com/listing/\d+", s["link"]):
            h.append(f"satir {n}: link bicimi")
        if t and re.search(r"https?://", t):
            h.append(f"satir {n}: metinde adres var (IG bio, FB ilk yorum, YT kanal sayfasi)")
        if t and re.search(r"(?i)link in (?:the )?bio", t) and s["platform"] != "instagram":
            h.append(f"satir {n}: 'link in bio' yalniz Instagram'da")
        etk = re.findall(r"#\w+", t)
        a_, b_ = [x.lower() for x in s["_cift"].split("_", 1)]
        if t and s["platform"] in ("instagram", "youtube"):
            sinir = 5 if s["platform"] == "instagram" else 3
            if len(etk) > sinir or f"#{a_}" not in etk or f"#{b_}" not in etk:
                h.append(f"satir {n}: hashtag kurali ({s['platform']} <= {sinir}, burc adlari)")
        if t and s["platform"] == "facebook" and (etk or FB_LINK not in t):
            h.append(f"satir {n}: Facebook metni ilk yorum cumlesi / hashtag")
        if s["platform"] == "youtube" and t and len(t.splitlines()[0]) > 100:
            h.append(f"satir {n}: YouTube basligi > 100")
        if s["platform"] in YALNIZ_HAFTA_ICI:
            et = datetime.strptime(s["tarih_saat_TR"], "%Y-%m-%d %H:%M").replace(tzinfo=TR).astimezone(ET)
            if et.weekday() >= 5 or not (10 <= et.hour < 12):
                h.append(f"satir {n}: {s['platform']} saati hafta ici 10:00-12:00 ET disinda ({et:%a %H:%M} ET)")
        if s["platform"] == "instagram" and s["tur"] == "gorsel" and t and not s.get("alt_metin"):
            h.append(f"satir {n}: Instagram gorselinde alt metin yok")
        if s["platform"] not in ("instagram", "facebook", "youtube"):
            h.append(f"satir {s['satir_no']}: platform {s['platform']}")
    yt = [s["metin"].splitlines()[0] for s in satirlar if s["platform"] == "youtube" and s["metin"]]
    if len(yt) >= 4 and len({re.sub(r"\b(?:" + "|".join(video_kaynak.BURCLAR) + r")\b", "", x, flags=re.I) for x in yt}) < 4:
        h.append("YouTube basliklarinda 4'ten az farkli kalip")
    return h


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--metin", required=True)
    ap.add_argument("--baslangic", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ig", type=int, default=2)
    ap.add_argument("--fb", type=int, default=2)
    ap.add_argument("--yt", type=int, default=1)
    ap.add_argument("--ilk-no", type=int, required=True, help="takvimdeki en buyuk satir_no'dan buyuk olmali")
    ap.add_argument("--mevcut-en-buyuk", type=int, required=True, help="takvimdeki en buyuk satir_no (cakisma kapisi)")
    x = ap.parse_args(argv)
    gunluk = {"instagram": x.ig, "facebook": x.fb, "youtube": x.yt}
    for p, n in gunluk.items():
        if not 1 <= n <= min(len(SAAT_ET[p]), SINIR[p]):
            print(f"DUR: {p} gunluk {n} desteklenmiyor (1-{min(len(SAAT_ET[p]), SINIR[p])})")
            return 2
    if x.ilk_no <= x.mevcut_en_buyuk:
        print(f"DUR: --ilk-no {x.ilk_no} takvimdeki en buyuk satir_no {x.mevcut_en_buyuk} ile cakisir")
        return 2
    try:
        satirlar, eksik = plan(x.metin, date.fromisoformat(x.baslangic), gunluk, x.ilk_no)
    except ValueError as e:
        print(f"DUR: {e}")
        return 2
    h = kapilar(satirlar, gunluk)
    hazir = not eksik["metin"] and not eksik["medya"]
    kok, uz = os.path.splitext(x.cikti)
    yol = x.cikti if (not h and hazir) else f"{kok}_{'FAIL' if h else 'EKSIK'}{uz}"   # takvime yapistirilmasin
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=secim.SUTUNLAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)
    son = {p: max(s["tarih_saat_TR"] for s in satirlar if s["platform"] == p) for p in gunluk}
    print(f"PLAN78 satir {len(satirlar)} | IG {gunluk['instagram']}/gun FB {gunluk['facebook']}/gun YT {gunluk['youtube']}/gun | "
          f"bitis IG {son['instagram'][:10]} FB {son['facebook'][:10]} YT {son['youtube'][:10]}")
    print(f"PLAN78 eksik: metin {eksik['metin']} satir, medya kaynagi {eksik['medya']} satir (bilgi)")
    for e in h[:20]:
        print(f"FAIL {e}")
    print("KAPI " + ("PASS" if not h else f"FAIL ({len(h)})"))
    print(f"PLAN78 dosya {yol}")
    print("HAZIRLIK " + ("TAMAM" if hazir else f"EKSIK (metin {eksik['metin']}, medya {eksik['medya']}): takvime YAZILMAZ"))
    if h:
        return 1
    return 0 if hazir else 3


if __name__ == "__main__":
    sys.exit(main())
