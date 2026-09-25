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
TR_ISARET = set("çğıöşüÇĞİÖŞÜ")
SORU_RE = re.compile(r"^\s*(name under (?P<burc>[a-z]+)|(?P<yon>left|right) name|your message|personali[sz]ation)\s*$", re.I)
KISISEL_PROPERTY = {54}          # Etsy eski tek alanli model: "Personalization" varyasyon property_id

ED_AD = {"MIDNIGHT_BLUE": "Midnight Blue", "DEEP_BLACK": "Deep Black", "WARM_PARCHMENT": "Warm Parchment",
         "CHAMPAGNE_IVORY": "Champagne Ivory", "PURE_WHITE": "Pure White"}

# Sorun -> musteri mesaji sablon numarasi. ONAY BEKLIYOR: sablon dosyasi (AstroLove_Kisisel_Musteri_
# Mesajlari_20260925.md) bu oturumda okunamadi; numaralar Serdar'in talimatindaki siraya gore varsayildi.
SABLON_SORUN = {"UZUN_ISIM": 2, "KIRIL_ISIM": 3, "ALFABE_ISIM": 3, "KARAKTER": 3, "EMOJI": 4, "UZUN_MESAJ": 5}


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
    s = unicodedata.normalize("NFC", s).replace("i̇", "İ")
    turkce = (ulke or "").upper() in TR_ULKE if ulke else bool(TR_ISARET & set(s))
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
    """'## ... <N> ...' basliklari -> {(N, 'EN'|'RU'): metin}. Dosya yoksa {}."""
    p = Path(yol) if yol else None
    if not p or not p.exists():
        return {}
    out, anahtar, satir = {}, None, []
    for ln in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,3}\s.*?(\d)\b(.*)$", ln)
        if m:
            if anahtar:
                out[anahtar] = "\n".join(satir).strip()
            dil = "RU" if re.search(r"\bRU\b|РУС|русск", ln, re.I) else "EN"
            anahtar, satir = (int(m.group(1)), dil), []
        elif anahtar:
            satir.append(ln)
    if anahtar:
        out[anahtar] = "\n".join(satir).strip()
    return out


def sablon_doldur(metin, degerler):
    for k, v in degerler.items():
        metin = re.sub(r"\{\{?\s*" + re.escape(k) + r"\s*\}?\}", str(v), metin, flags=re.I)
    return metin


def kart(receipt, kalemler, sablonlar, kanal_notu=""):
    """-> (markdown, ozet_sorun_kodlari)"""
    rid = receipt.get("receipt_id")
    ulke = (receipt.get("country_iso") or "").upper()
    dil = "RU" if ulke in RU_ULKE else "EN"
    alici_ad = ((receipt.get("name") or "").split() or [""])[0]
    md = [f"# Siparis {rid} — ISIM BEKLIYOR", "",
          f"- Durum: Prodigi'ye GONDERILMEDI (kisisellestirme cevabi var). Baski dosyasi bu adimda uretilmez.",
          f"- Ulke: {ulke or '?'} | mesaj dili: {dil}"]
    if kanal_notu:
        md.append(f"- **KANAL:** {kanal_notu}")
    tum_kod = []
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
    no = next((SABLON_SORUN[c] for c in ("UZUN_ISIM", "KIRIL_ISIM", "ALFABE_ISIM", "KARAKTER", "EMOJI", "UZUN_MESAJ")
               if c in tum_kod), 1)
    ilk = eslestir(kalemler[0]) if kalemler else {"isim1": "", "isim2": "", "mesaj": ""}
    deg = {"isim1": ilk["isim1"], "isim2": ilk["isim2"], "mesaj": ilk["mesaj"], "name1": ilk["isim1"],
           "name2": ilk["isim2"], "message": ilk["mesaj"], "ad": alici_ad, "name": alici_ad, "buyer": alici_ad,
           "siparis": rid, "order": rid}
    metin = sablonlar.get((no, dil)) or (sablonlar.get((no, "EN")) if dil == "RU" else None)
    md += ["", f"## Musteri mesaji (GONDERILMEDI) — sablon {no} ({dil})", ""]
    if metin:
        md += ["```", sablon_doldur(metin, deg), "```"]
    else:
        md += [f"Sablon dosyasi yok ya da sablon {no}/{dil} bulunamadi: Drive TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md "
               "(AstroLove_Kisisel_Musteri_Mesajlari_20260925.md) konmali."]
    return "\n".join(md) + "\n", sorted(set(tum_kod))
