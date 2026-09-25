#!/usr/bin/env python3
"""Kisisellestirmeli POD siparisi: cevaplari cikar, dogrula, siparis karti yaz (saf fonksiyonlar, ag yok).

Serdar karari 25 Eyl 2026: kisisellestirme cevabi olan POD siparisi Prodigi'ye GONDERILMEZ; STATE
"ISIM_BEKLIYOR" olur ve Drive TEMP/SIPARIS_ISIM/<receipt_id>.md karti hazirlanir. Musteri mesaji
yalniz HAZIRLANIR, gonderilmez. Baski dosyasi uretimi bu modulde YOK.

Dogrulama kurallari: kisisel-v1 dalindaki scripts/kisisel/giris_dogrula.py (21 Eyl) + 25 Eyl ekleri:
  - isim: en fazla 11 harf; yalniz Latin harf, bosluk, tire, kesme; BUYUK harfe cevrilir.
  - Kiril (ve diger Latin disi) isim -> ELLE KONTROL (Cinzel basamaz).
  - emoji / sembol (orn. ♥) -> ELLE KONTROL (isim fontu da mesaj fontu da basamaz).
  - mesaj: en fazla 35 karakter; Latin ya da Kiril (RU aciklama: "можно на русском").
Font dosyasi (assets/fonts, kisisel-v1) bu dalda yoksa font kapsami ayrica olculmez; kartta yazilir.
"""
import re
import unicodedata
from pathlib import Path

ISIM_AZAMI = 11
MESAJ_AZAMI = 35
KESME = "'’ʼ"
ISIM_AYIRICI = " -" + KESME
RU_ULKE = {"RU", "BY", "KZ"}
TR_ULKE = {"TR"}
TR_ISARET = set("ıİşŞğĞ")        # Turkceye OZGU harfler (ç/ö/ü baska dillerde de var)
SORU_RE = re.compile(r"^\s*(name under (?P<burc>[a-z]+)|(?P<yon>left|right) name|your message|personali[sz]ation)\s*$", re.I)
KISISEL_PROPERTY = {54}          # Etsy eski tek alanli model: "Personalization" varyasyon property_id

ED_AD = {"MIDNIGHT_BLUE": "Midnight Blue", "DEEP_BLACK": "Deep Black", "WARM_PARCHMENT": "Warm Parchment",
         "CHAMPAGNE_IVORY": "Champagne Ivory", "PURE_WHITE": "Pure White"}

# Sorun -> musteri mesaji sablonu (Serdar 25 Eyl, Drive TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md):
#   1 yazim kontrolu: HER sipariste (sorun yoksa tek basina)   2 Kiril / Latin disi harfli isim
#   3 mesajda emoji / ♥ / fontta olmayan karakter               4 isim > 11 harf ya da mesaj > 35 karakter
#   5 kisisellestirme eksik/bos                                 6 2 gun cevap yoksa hatirlatma (kartta tarih notu)
# Birden cok sorun varsa ilgili sablonlarin hepsi kartta listelenir.
SABLON_ISIM = {"KIRIL_ISIM": 2, "ALFABE_ISIM": 2, "UZUN_ISIM": 4, "BOS": 5}
SABLON_MESAJ = {"EMOJI": 3, "KARAKTER": 3, "UZUN_MESAJ": 4, "BOS": 5}
SABLON_AD = {1: "yazim kontrolu", 2: "Kiril / Latin disi isim", 3: "mesajda emoji / fontta olmayan karakter",
             4: "metin cok uzun", 5: "kisisellestirme eksik", 6: "2 gun cevap yok (hatirlatma)"}
HATIRLATMA_GUN = 2

BURC_RU = {"ARIES": "Овна", "TAURUS": "Тельца", "GEMINI": "Близнецов", "CANCER": "Рака", "LEO": "Льва",
           "VIRGO": "Девы", "LIBRA": "Весов", "SCORPIO": "Скорпиона", "SAGITTARIUS": "Стрельца",
           "CAPRICORN": "Козерога", "AQUARIUS": "Водолея", "PISCES": "Рыб"}   # sablonlarda "под знаком X" (ilgi hali)
KIRIL_LATIN = {"А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E", "Ж": "ZH", "З": "Z", "И": "I",
               "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
               "У": "U", "Ф": "F", "Х": "KH", "Ц": "TS", "Ч": "CH", "Ш": "SH", "Щ": "SHCH", "Ъ": "", "Ы": "Y",
               "Ь": "", "Э": "E", "Ю": "YU", "Я": "YA", "І": "I", "Ї": "YI", "Є": "YE", "Ў": "U", "Ґ": "G"}


def _emoji_mi(c):
    o = ord(c)
    return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0xFE00 <= o <= 0xFE0F
            or o == 0x200D or 0x1F1E6 <= o <= 0x1F1FF or 0x2190 <= o <= 0x21FF or 0x2300 <= o <= 0x23FF)


def _sembol_mi(c):
    """Harf/rakam/noktalama/bosluk disi (♥ ★ © vb.): So/Sk/Sm kategorileri."""
    return unicodedata.category(c) in ("So", "Sk", "Sm") or _emoji_mi(c)


def _alfabe(c):
    try:
        ad = unicodedata.name(c)
    except ValueError:
        return "BILINMEYEN"
    for a in ("LATIN", "CYRILLIC", "GREEK", "ARABIC", "HEBREW", "CJK", "HIRAGANA", "KATAKANA", "HANGUL"):
        if ad.startswith(a):
            return a
    return ad.split(" ")[0]


def buyut(s, ulke=""):
    """Basilacak hal. Varsayilan standart buyuk harf (Ali -> ALI). Turkce buyuk harf (i -> İ) YALNIZ alici
    ulkesi TR ise ya da isimde Turkceye ozgu harf (ı İ ş ğ) varsa (Serdar 25 Eyl). Kart basilacak hali gosterir;
    musteri sablon 1 ile onaylar."""
    s = unicodedata.normalize("NFC", s).replace("i̇", "İ")
    turkce = (ulke or "").upper() in TR_ULKE or bool(TR_ISARET & set(s))
    if turkce:
        s = s.translate(str.maketrans({"i": "İ", "ı": "I"}))
    return unicodedata.normalize("NFC", s.upper())


def isim_dogrula(ham, ulke=""):
    """-> (durum, basilacak, [(kod, aciklama)])"""
    s = unicodedata.normalize("NFC", (ham or "").strip())
    if not s:
        return "ELLE KONTROL", "", [("BOS", "isim bos")]
    sorun = []
    if any(_sembol_mi(c) for c in s):
        sorun.append(("EMOJI", "emoji/sembol var (isim fontu Cinzel basamaz)"))
    alf = {_alfabe(c) for c in s if c.isalpha()}
    if "CYRILLIC" in alf:
        sorun.append(("KIRIL_ISIM", "Kiril harf (Cinzel basamaz; isim Latin harfle yazilmali)"))
    if alf - {"LATIN", "CYRILLIC"}:
        sorun.append(("ALFABE_ISIM", "desteklenmeyen alfabe: " + ", ".join(sorted(alf - {"LATIN", "CYRILLIC"}))))
    diger = {c for c in s if not c.isalpha() and c not in ISIM_AYIRICI and not _sembol_mi(c)}
    if diger:
        sorun.append(("KARAKTER", "izin verilmeyen karakter: " + " ".join(sorted(diger))))
    n = sum(1 for c in s if c.isalpha())
    if n > ISIM_AZAMI:
        sorun.append(("UZUN_ISIM", f"{n} harf (azami {ISIM_AZAMI})"))
    return ("ELLE KONTROL" if sorun else "TAMAM"), buyut(s, ulke), sorun


def mesaj_dogrula(ham):
    s = unicodedata.normalize("NFC", (ham or "").strip())
    if not s:
        return "ELLE KONTROL", "", [("BOS", "mesaj bos")]
    sorun = []
    if any(_sembol_mi(c) for c in s):
        sorun.append(("EMOJI", "emoji/sembol var (mesaj fontu da isim fontu da basamaz)"))
    alf = {_alfabe(c) for c in s if c.isalpha()}
    if alf - {"LATIN", "CYRILLIC"}:
        sorun.append(("KARAKTER", "desteklenmeyen alfabe: " + ", ".join(sorted(alf - {"LATIN", "CYRILLIC"}))))
    if len(s) > MESAJ_AZAMI:
        sorun.append(("UZUN_MESAJ", f"{len(s)} karakter (azami {MESAJ_AZAMI})"))
    return ("ELLE KONTROL" if sorun else "TAMAM"), s, sorun


# ------------------------------------------------------------------ cevaplari cikar
def _kisisel_alanlar(t):
    """Transaction'dan (soru, cevap) listesi. Iki yol olculur:
    1) variations[] icinde formatted_name bir kisisellestirme sorusu (ya da property_id 54) olanlar;
    2) transaction'da adinda 'personaliz' gecen alan (liste/sozluk/metin)."""
    out = []
    for v in t.get("variations") or []:
        ad = (v.get("formatted_name") or "").strip()
        if SORU_RE.match(ad) or v.get("property_id") in KISISEL_PROPERTY:
            out.append((ad or "Personalization", (v.get("formatted_value") or "").strip()))
    for k, val in t.items():
        if "personaliz" not in k.lower() or not val or isinstance(val, bool):
            continue
        if isinstance(val, str):
            out.append(("Personalization", val.strip()))
        elif isinstance(val, list):
            for q in val:
                if isinstance(q, dict):
                    out.append(((q.get("question_text") or q.get("question") or q.get("name") or "Personalization").strip(),
                                str(q.get("answer") or q.get("value") or q.get("formatted_value") or "").strip()))
    tekil, gor = [], set()
    for s, c in out:
        if (s.lower(), c) not in gor:
            gor.add((s.lower(), c))
            tekil.append((s, c))
    return tekil


def cevaplar(receipt, parse_sku):
    """POD kalemleri icin [{transaction_id, sku, pair, ed, size, alanlar:[(soru, cevap)]}] (cevabi olanlar)."""
    out = []
    for t in receipt.get("transactions") or []:
        p = parse_sku((t.get("sku") or "").strip())
        if not p:
            continue
        alan = _kisisel_alanlar(t)
        if alan:
            out.append({"transaction_id": t.get("transaction_id"), "sku": t.get("sku"), "pair": p[0], "ed": p[1],
                        "size": p[2], "qty": int(t.get("quantity") or 1), "alanlar": alan})
    return out


def eslestir(kalem):
    """Soru adlarindan isim1/isim2/mesaj. Isim1 = ciftin ILK burcu (SKU cifti sirasi)."""
    a, b = kalem["pair"].split("_", 1)
    isim = {}
    mesaj, digeri = "", []
    for soru, cevap in kalem["alanlar"]:
        m = SORU_RE.match(soru or "")
        if not m:
            digeri.append((soru, cevap)); continue
        if m.group("burc"):
            isim[m.group("burc").upper()] = (soru, cevap)
        elif m.group("yon"):
            isim[m.group("yon").upper()] = (soru, cevap)
        elif soru.lower().startswith("your message"):
            mesaj = cevap
        else:
            digeri.append((soru, cevap))
    if a == b:
        i1, i2 = isim.get("LEFT"), isim.get("RIGHT")
        yer1, yer2 = f"sol ({a.title()})", f"sag ({b.title()})"
    else:
        i1, i2 = isim.get(a), isim.get(b)
        yer1, yer2 = f"{a.title()} altinda", f"{b.title()} altinda"
    return {"isim1": (i1 or ("", ""))[1], "isim1_yer": yer1, "isim2": (i2 or ("", ""))[1], "isim2_yer": yer2,
            "mesaj": mesaj, "eslesmeyen": digeri, "eksik_soru": [x for x, v in (("isim1", i1), ("isim2", i2)) if not v]}


# ------------------------------------------------------------------ sablonlar + kart
def sablon_oku(yol):
    """MUSTERI_MESAJLARI.md: '## N. baslik', altinda 'EN' / 'RU' satiri ve ``` blogu -> {(N, dil): metin}.
    Dosya yoksa {}."""
    p = Path(yol) if yol else None
    if not p or not p.exists():
        return {}
    out, no, dil, blok, icerde = {}, None, None, [], False
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.strip().startswith("```"):
            if icerde and no is not None and dil:
                out[(no, dil)] = "\n".join(blok).strip()
            icerde, blok = not icerde, []
            continue
        if icerde:
            blok.append(ln); continue
        m = re.match(r"^#{2,3}\s*(\d+)\b", ln)
        if m:
            no, dil = int(m.group(1)), None
        elif ln.strip().upper() in ("EN", "RU"):
            dil = ln.strip().upper()
    return out


def sablon_doldur(metin, degerler):
    """[Yer tutucu] -> deger (buyuk/kucuk harf AYRI: [NAME 1] basilacak isim, [Name 1] gelen isim).
    Degeri bos olan yer tutucu oldugu gibi kalir (Serdar doldurur)."""
    for k, v in degerler.items():
        if v not in (None, ""):
            metin = metin.replace(f"[{k}]", str(v))
    return metin


def latinle(s):
    return "".join(KIRIL_LATIN.get(c, c) for c in buyut(s))


def mesaj_temizle(s):
    return re.sub(r"\s{2,}", " ", "".join(c for c in (s or "") if not _sembol_mi(c))).strip()


def _sure_notu(receipt):
    ts = receipt.get("created_timestamp") or receipt.get("create_timestamp")
    if not ts:
        return f"siparisten {HATIRLATMA_GUN} gun sonra"
    import time as _t
    return _t.strftime("%Y-%m-%d %H:%M UTC", _t.gmtime(float(ts) + HATIRLATMA_GUN * 86400))


def kalem_kontrol(kalem, ulke=""):
    """Tek kalemin on kontrolu (siparis onay akisi, 25 Eyl). -> dict: isim1/isim2/mesaj (gelen), bas1/bas2
    (basilacak), kodlar (sorun), sablonlar (1 disindaki sorun sablonlari), elle (sablonu olmayan sorun), temiz."""
    ulke = (ulke or "").upper()
    e = eslestir(kalem)
    _, b1, s1 = isim_dogrula(e["isim1"], ulke)
    _, b2, s2 = isim_dogrula(e["isim2"], ulke)
    _, bm, sm = mesaj_dogrula(e["mesaj"])
    kodlar = [c for c, _ in s1 + s2 + sm] + (["EKSIK_SORU"] if e["eksik_soru"] else [])
    nolar = {SABLON_ISIM[c] for c, _ in s1 + s2 if c in SABLON_ISIM} | {SABLON_MESAJ[c] for c, _ in sm if c in SABLON_MESAJ}
    if e["eksik_soru"]:
        nolar.add(5)
    elle = [x for c, x in s1 + s2 if c not in SABLON_ISIM]
    if e["eslesmeyen"]:
        elle.append(f"taninmayan alan: {[q for q, _ in e['eslesmeyen']]}")
    return {"isim1": e["isim1"], "isim2": e["isim2"], "mesaj": e["mesaj"], "bas1": b1, "bas2": b2, "bas_mesaj": bm,
            "kodlar": kodlar, "sablonlar": sorted(nolar), "elle": elle, "temiz": not kodlar and not elle}


def uretim_girdisi(kalem, kk, urun="pod"):
    """siparis_dosyasi.py kart_oku() bicimi ('anahtar: deger'); kartin EN SONUNA yazilir (onceki satirlari ezer)."""
    return ["", "## Uretim girdisi (siparis_dosyasi.py)", "",
            f"- cift: {kalem['pair']}", f"- renk: {kalem.get('ed') or 'MIDNIGHT_BLUE'}", f"- boy: {kalem.get('size') or '-'}",
            f"- isim1: {kk['bas1']}", f"- isim2: {kk['bas2']}", f"- mesaj: {kk['bas_mesaj']}", f"- urun: {urun}"]


def kart(receipt, kalemler, sablonlar, kanal_notu="", urun="pod"):
    """-> (markdown, ozet_sorun_kodlari). Tek ve temiz kalemde sonda uretim girdisi bolumu olur."""
    rid = receipt.get("receipt_id")
    ulke = (receipt.get("country_iso") or "").upper()
    dil = "RU" if ulke in RU_ULKE else "EN"
    alici_ad = ((receipt.get("name") or "").split() or [""])[0]
    md = [f"# Siparis {rid} — ISIM BEKLIYOR", "",
          f"- Durum: Prodigi'ye GONDERILMEDI (kisisellestirme cevabi var). Baski dosyasi bu adimda uretilmez.",
          f"- Ulke: {ulke or '?'} | mesaj dili: {dil}"]
    if kanal_notu:
        md.append(f"- **KANAL:** {kanal_notu}")
    tum_kod, secilen, elle = [], {}, []          # secilen: sablon no -> degerler (ilk tetikleyen kalemden)
    for k in kalemler:
        e = eslestir(k)
        d1, b1, s1 = isim_dogrula(e["isim1"], ulke)
        d2, b2, s2 = isim_dogrula(e["isim2"], ulke)
        dm, bm, sm = mesaj_dogrula(e["mesaj"])
        kodlar = [c for c, _ in s1 + s2 + sm]
        if e["eksik_soru"]:
            kodlar.append("EKSIK_SORU")
        tum_kod += kodlar
        a, b = k["pair"].split("_", 1)
        kiril = [x for x, s_ in ((e["isim1"], s1), (e["isim2"], s2)) if any(c in ("KIRIL_ISIM", "ALFABE_ISIM") for c, _ in s_)]
        ve = " и " if dil == "RU" else " and "
        oneri = [latinle(x) for x in kiril if not any(ord(c) > 0x24F and not ("Ѐ" <= c <= "ӿ") for c in x if c.isalpha())]
        deg = {"Buyer name": alici_ad, "Sign A": BURC_RU.get(a, a.title()) if dil == "RU" else a.title(),
               "Sign B": BURC_RU.get(b, b.title()) if dil == "RU" else b.title(),
               "NAME 1": b1, "NAME 2": b2, "Message": e["mesaj"], "Name 1": ve.join(kiril),
               "Suggested spelling": ve.join(oneri) if len(oneri) == len(kiril) else "",
               "Suggested message": mesaj_temizle(e["mesaj"]), "Suggested shorter version": ""}
        nolar = {SABLON_ISIM[c] for c, _ in s1 + s2 if c in SABLON_ISIM} | {SABLON_MESAJ[c] for c, _ in sm if c in SABLON_MESAJ}
        if e["eksik_soru"]:
            nolar.add(5)
        for c, x in s1 + s2:
            if c not in SABLON_ISIM:
                elle.append(f"isimde {x}: uygun sablon yok, Serdar elle yazar")
        for n_ in sorted(nolar) + [1, 6]:
            secilen.setdefault(n_, deg)
        md += ["", f"## Kalem {k['sku']} x{k['qty']}", "",
               f"| alan | deger |", "|---|---|",
               f"| cift | {a.title()} + {b.title()} |", f"| renk | {ED_AD.get(k['ed'], k['ed'])} |", f"| boy | {k['size']} |",
               f"| isim 1 ({e['isim1_yer']}) | `{e['isim1']}` -> basilacak `{b1}` — {d1} |",
               f"| isim 2 ({e['isim2_yer']}) | `{e['isim2']}` -> basilacak `{b2}` — {d2} |",
               f"| mesaj | `{e['mesaj']}` ({len(e['mesaj'])} kar.) — {dm} |", ""]
        sorunlar = [f"isim 1: {x}" for _, x in s1] + [f"isim 2: {x}" for _, x in s2] + [f"mesaj: {x}" for _, x in sm]
        if e["eksik_soru"]:
            sorunlar.append(f"eksik soru cevabi: {e['eksik_soru']}")
        if e["eslesmeyen"]:
            sorunlar.append(f"taninmayan alan: {e['eslesmeyen']}")
        md += ["**Dogrulama:** " + ("TAMAM (3 alan)" if not sorunlar else "ELLE KONTROL"), ""] + [f"- {x}" for x in sorunlar]
        md += ["", "- Font kapsami: assets/fonts (Cinzel / EB Garamond) bu dalda yok; alfabe + emoji kurali uygulandi."]
    sorun_no = sorted(n_ for n_ in secilen if n_ not in (1, 6))
    liste = sorun_no + [1]
    md += ["", "## Musteri mesajlari (GONDERILMEDI, yalniz hazirlandi)", "",
           "- Sablonlar: " + ", ".join(f"{n_} ({SABLON_AD[n_]})" for n_ in liste)
           + ("" if sorun_no else " — sorun yok, yalniz yazim kontrolu"),
           f"- **Sablon 6 (hatirlatma):** {_sure_notu(receipt)} tarihine kadar cevap yoksa gonderilir."]
    md += [f"- {x}" for x in dict.fromkeys(elle)]
    if not sablonlar:
        md += ["", "Sablon dosyasi okunamadi: Drive TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md"]
    for n_ in liste + [6]:
        metin = sablonlar.get((n_, dil)) or sablonlar.get((n_, "EN"))
        md += ["", f"### Sablon {n_}: {SABLON_AD[n_]} ({dil})"
               + (" — sorunlar cozulunce son hal ile" if n_ == 1 and sorun_no else "")
               + (f" — {_sure_notu(receipt)} sonrasi" if n_ == 6 else ""), ""]
        if metin:
            dolu = sablon_doldur(metin, secilen[n_])
            md += ["```", dolu, "```"]
            kalan = sorted(set(re.findall(r"\[[^\]\n]+\]", dolu)))
            if kalan:
                md.append(f"- Doldurulmadi (Serdar yazar): {', '.join(kalan)}")
        else:
            md.append(f"Sablon {n_}/{dil} dosyada bulunamadi.")
    if len(kalemler) == 1:
        kk = kalem_kontrol(kalemler[0], ulke)
        if kk["temiz"]:
            md += uretim_girdisi(kalemler[0], kk, urun)
    return "\n".join(md) + "\n", sorted(set(tum_kod))
