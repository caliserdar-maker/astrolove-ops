#!/usr/bin/env python3
"""Receipt log kapisi (IP adim 0 c, 17 Kas 2026; bagimsiz inceleme 1. tur sonrasi v2). Depo HERKESE ACIK: Actions loglari acik.

Siparis no tasiyan workflow_dispatch girdileri (TASIYICI + EK) loga ACIK yazilmamali. Runner bir adimin `run` metnini
(${{ }} acilmis hali), adimin `env` / `with` degerlerini ve is (job) duzeyi `env` degerlerini adim basliginda loga basar;
::add-mask:: ile kaydedilen deger ise o isin SONRAKI satirlarinda *** olur (maske is basinadir, isler arasi tasinmaz).

Kurallar (her biri bulgu = FAIL):
  R0 butun olay: tasiyici girdili workflow'da `toJSON(inputs)`, `toJSON(github.event.inputs)`, `inputs[...]` bicimi (if: disi),
     olay dosyasinin butununu okuyan adim (`cat $GITHUB_EVENT_PATH`, `jq . $GITHUB_EVENT_PATH`, Python `GITHUB_EVENT_PATH`)
     ve tasiyici okuyan iste `set -x` / `set -o xtrace` / `bash -x` yasak.
  R1 ifade : tasiyici `${{ inputs.X }}` / `${{ github.event.inputs.X }}` ile `if:` DISINDA hicbir yerde kullanilmaz.
  R2 maske : bir is X'i olay dosyasindan okuyorsa, X'i okuyan ILK adim X'i bir degiskene atar ve degiskenin atamadan
             sonraki ILK kullanimi kosulsuz maskedir: `echo "::add-mask::$d"`, `[ -z "$d" ] || echo ...` ya da
             `[ ${#d} -lt N ] || echo ...` (liste girdisi: ilk kullanim, govdesi her ogeyi maskeleyen for / while dongusu).
  R3 sinif : aciklamasinda receipt / siparis no / fis gecen her girdi ya TASIYICI ya da KAPSAM_DISI (gerekceli) olmali.
Ciktida yalniz workflow adi, is, adim no ve kural yazilir; hicbir girdi degeri yazilmaz.
"""
import glob
import os
import re
import sys

import yaml

TASIYICI = ("receipt", "receipt_id", "siparis_no", "siparis_ref", "fisler")
LISTE = ("fisler", "siparis_alici", "taban")   # birden cok deger (virgullu receipt / 'ad|adres|...'): her oge ayri maskelenir
# Yalniz o workflow'da tasiyici olan girdiler
EK = {"pod-arac-v4.yml": ("confirm", "siparis_alici"),   # siparis_gonder'de confirm = siparis ref; alici adi/adresi
      "pod-order-router.yml": ("submit",),                # Prodigi'ye gonderilecek receipt
      "a3-esit-kiyas.yml": ("eski", "yeni", "taban")}     # poster kiyasinda receipt (kupa: klasor yolu)
# Aciklamasi receipt gecen ama siparis no TASIMAYAN girdiler (R3)
KAPSAM_DISI = {"test_receipt": "depodaki sahte receipt dosya yolu", "sahte_receipt": "depodaki sahte receipt dosya yolu",
               "receipt_pages": "sayfa sayisi", "since_days": "gun sayisi", "sadece_test": "evet/hayir",
               "son4": "son 4 hane (tam no degil)", "beklenen": "dosya sayisi", "expect_order": "SET kimligi", "yaz": "evet/hayir"}
SINIF = re.compile(r"receipt|sipari[sş]\s*no|\bfi[sş]", re.I)


def _on(d):
    return d.get(True, d.get("on")) or {}


def _ins(d):
    on = _on(d)
    if not isinstance(on, dict):
        return {}
    wd = on.get("workflow_dispatch")
    return ((wd or {}).get("inputs") if isinstance(wd, dict) else None) or {}


def _girdiler(d, ad=""):
    return [k for k in _ins(d) if k in TASIYICI or k in EK.get(ad, ())]


def _ifade_re(x):
    return re.compile(r"\$\{\{[^}]*\b(?:github\.event\.)?inputs\.%s\b[^}]*\}\}" % re.escape(x))


BUTUN = (re.compile(r"\$\{\{[^}]*toJSON\(\s*(github\.event\.)?inputs\s*\)"), re.compile(r"\$\{\{[^}]*\b(github\.event\.)?inputs\s*\["))
OLAY_BUTUN = (re.compile(r"\bcat\b[^\n|;]*GITHUB_EVENT_PATH"), re.compile(r"\bjq\b[^\n|;]*'\s*\.\s*'[^\n|;]*GITHUB_EVENT_PATH"),
              re.compile(r"\bjq\b\s+\.\s+[^\n|;]*GITHUB_EVENT_PATH"), re.compile(r"os\.environ[^\n]*GITHUB_EVENT_PATH"),
              re.compile(r"getenv\([^\n]*GITHUB_EVENT_PATH"))
XTRACE = re.compile(r"(^|[\s;])set\s+(-[a-wyz]*x|-o\s+xtrace)|\bbash\s+-[a-z]*x")


def _gez(o, yol=()):
    """(yol, metin) ciftleri; anahtar 'if' olan dallar atlanir."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "if":
                continue
            yield from _gez(v, yol + (str(k),))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _gez(v, yol + (str(i),))
    elif isinstance(o, str):
        yield yol, o


def _okur(metin, x):
    """Adim metni X'i olay dosyasindan okuyor mu: '.inputs.X' ya da '.inputs | {... X ...}' bicimi."""
    if re.search(r"\.inputs\.%s\b" % re.escape(x), metin):
        return True
    return bool(re.search(r"\.inputs\s*\|[^\n]*\b%s\b" % re.escape(x), metin))


def _kullanim(d):
    return re.compile(r"\$\{?#?%s\b" % re.escape(d))


KOSULSUZ = r"(?:^\s*|;\s*|\bdo\s+)echo\s+\"?::add-mask::\$\{?%s\b"   # dongu govdesinde kosulsuz (koruma: KORUMA)
KORUMA = r"\[\s*(?:-z\s+\"?\$\{?%s\}?\"?|\$\{#%s\}\s+-lt\s+\d+)\s*\]\s*\|\|\s*echo\s+\"?::add-mask::\$\{?%s\b"


def _kapanis(metin, i):
    """metin[i] '$(' sonrasindan baslayarak eslesen ')' konumu (tek / cift tirnak icindeki parantez sayilmaz)."""
    derin, tek, cift = 1, False, False
    while i < len(metin):
        c = metin[i]
        if c == "'" and not cift:
            tek = not tek
        elif c == '"' and not tek:
            cift = not cift
        elif not tek and not cift:
            if c == "(":
                derin += 1
            elif c == ")":
                derin -= 1
                if derin == 0:
                    return i
        i += 1
    return -1


def _ilk_kullanim_maske(metin, d, liste, atama):
    """d atamadan sonraki ILK kullanimi kosulsuz maske mi (liste: o satir, govdesi her ogeyi maskeleyen dongu)."""
    if not atama:
        return False
    son = _kapanis(metin, atama.end())
    if son < 0:
        return False
    kalan = metin[son + 1:]
    m = _kullanim(d).search(kalan)
    if not m:
        return False
    satir_basi = kalan.rfind("\n", 0, m.start()) + 1
    satir_sonu = kalan.find("\n", m.start())
    satir = kalan[satir_basi:satir_sonu if satir_sonu >= 0 else len(kalan)]
    on = kalan[satir_basi:m.start()]
    if liste:
        for dongu in (re.compile(r"for\s+(\w+)\s+in\s+([^;\n]*);\s*do([^\n]*?)done"),
                      re.compile(r"while[^\n]*?read\s+-r\s+(\w+);\s*do([^\n]*?)done\s*<\s*<\(([^\n]*)\)")):
            for mm in dongu.finditer(satir):
                o = mm.group(1)
                govde, liste_metni = (mm.group(3), mm.group(2)) if mm.re.pattern.startswith("for") else (mm.group(2), mm.group(3))
                ilk = m.start() - satir_basi
                if mm.start() <= ilk < mm.end() and _kullanim(d).search(liste_metni) and \
                        (re.search(KOSULSUZ % o, govde) or re.search(KORUMA % (o, o, o), govde)):
                    return True
        return False
    nokta = on.rfind(";")
    ifade = satir[nokta + 1:] if nokta >= 0 else satir           # kullanimi iceren deyim (';' ile ayrilmis)
    on_ifade = on[nokta + 1:] if nokta >= 0 else on
    if "&&" in on_ifade or re.search(r"\b(if|while|until|case)\b", on_ifade):
        return False                                            # kosullu maske (calismayabilir)
    return bool(re.match(r"\s*" + KORUMA % (d, d, d), ifade) or re.match(r"\s*echo\s+\"?::add-mask::\$\{?%s\b" % d, ifade))


def _maskeler(metin, x):
    """X'i okuyan ILK atama (degisken=$( ... .inputs ... X ... )) bulunur; o degiskenin ilk kullanimi kosulsuz maske olmali."""
    for m in re.finditer(r"\b([A-Za-z_]\w*)=\$\(", metin):
        son = _kapanis(metin, m.end())
        ic = metin[m.end():son] if son >= 0 else ""
        if ".inputs" in ic and re.search(r"\b%s\b" % re.escape(x), ic):
            return _ilk_kullanim_maske(metin, m.group(1), x in LISTE, m)
    return False


def denetle_veri(d, ad="?"):
    bulgular = []
    ins = _ins(d)
    for k, v in ins.items():
        aciklama = str((v or {}).get("description", "")) if isinstance(v, dict) else ""
        if SINIF.search(aciklama) and k not in TASIYICI and k not in EK.get(ad, ()) and k not in KAPSAM_DISI:
            bulgular.append(f"{ad}: R3 sinif: '{k}' aciklamasi siparis no anlatiyor, TASIYICI / KAPSAM_DISI degil")
    girdiler = _girdiler(d, ad)
    if not girdiler:
        return bulgular
    for yol, metin in _gez(d):
        for rx in BUTUN:
            if rx.search(metin):
                bulgular.append(f"{ad}: R0 butun girdi ifadesi ({'/'.join(yol[:4])})")
    for x in girdiler:
        rx = _ifade_re(x)
        for yol, metin in _gez(d):
            if rx.search(metin):
                bulgular.append(f"{ad}: R1 ifade: '{x}' ${{{{ }}}} ile kullaniliyor ({'/'.join(yol[:4])})")
    for is_adi, is_ in ((d.get("jobs") or {}).items()):
        adimlar = (is_ or {}).get("steps") or []
        metinler = [str((a or {}).get("run") or "") for a in adimlar]
        for i, metin in enumerate(metinler):
            if any(rx.search(metin) for rx in OLAY_BUTUN[:3]):
                bulgular.append(f"{ad}: R0 olay dosyasinin butunu okunuyor: is '{is_adi}' adim {i + 1}")
            elif any(rx.search(metin) for rx in OLAY_BUTUN[3:]) and not (
                    "::add-mask::" in metin and all(re.search(r"['\"]%s['\"]" % re.escape(x), metin) for x in girdiler)):
                # Python ile olay okuma: yalniz ayni adim her tasiyiciyi adiyla maskeliyorsa (by-siparis-ornek deseni)
                bulgular.append(f"{ad}: R0 olay dosyasi Python ile okunuyor, tasiyici maskesi yok: is '{is_adi}' adim {i + 1}")
        okuyan = False
        for x in girdiler:
            for i, metin in enumerate(metinler):
                if not _okur(metin, x):
                    continue
                okuyan = True
                if not _maskeler(metin, x):
                    bulgular.append(f"{ad}: R2 maske: is '{is_adi}' adim {i + 1}: '{x}' okunuyor, ilk kullanim kosulsuz maske degil")
                break   # yalniz ILK okuyan adim
        if okuyan and any(XTRACE.search(m) for m in metinler):
            bulgular.append(f"{ad}: R0 set -x: is '{is_adi}' tasiyici okuyor")
    return bulgular


def denetle(yol):
    with open(yol, encoding="utf-8") as f:
        return denetle_veri(yaml.safe_load(f), os.path.basename(yol))


def main(argv):
    kok = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    dosyalar = sorted(glob.glob(os.path.join(kok, ".github", "workflows", "*.yml")))
    tum = []
    kapsam = 0
    for p in dosyalar:
        with open(p, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        if _girdiler(d, os.path.basename(p)):
            kapsam += 1
        tum += denetle_veri(d, os.path.basename(p))
    for b in tum:
        print(b)
    print(f"receipt log kapisi: {len(dosyalar)} workflow, {kapsam} tasiyici girdili, {len(tum)} bulgu -> "
          f"{'PASS' if not tum else 'FAIL'}")
    return 0 if not tum else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
