#!/usr/bin/env python3
"""Receipt log kapisi (IP adim 0 c, 17 Kas 2026). Depo HERKESE ACIK: Actions loglari herkese acik.

Siparis no tasiyan workflow_dispatch girdileri (TASIYICI) loga ACIK yazilmamali. Runner bir adimin `run` metnini
(${{ }} acilmis hali), adimin `env` / `with` degerlerini ve is (job) duzeyi `env` degerlerini adim basliginda loga basar;
::add-mask:: ile kaydedilen deger ise o isin SONRAKI satirlarinda *** olur (maske is basinadir, isler arasi tasinmaz).

Kurallar (her biri bulgu = FAIL):
  R1 ifade : TASIYICI girdi `${{ inputs.X }}` / `${{ github.event.inputs.X }}` ile `if:` DISINDA hicbir yerde
             kullanilmaz (run, env, with, name, run-name, outputs, concurrency ...). Girdi olay dosyasindan okunur
             ($GITHUB_EVENT_PATH, jq) ki run metni ve adim basligi degeri tasimasin.
  R2 maske : bir is X'i olay dosyasindan okuyorsa, X'i okuyan ILK adim X'i ::add-mask:: ile kaydeder
             (deger bir degiskene atanir ve `::add-mask::$deg` yazilir; liste girdisi (fisler) icin her oge ayri:
             `for o in ...; do echo "::add-mask::$o"`). Ondan once X'i okuyan adim olamaz.
Kapsam disi (bilerek): sahte_receipt / test_receipt (dosya yolu), receipt_pages (sayi), expect_order (SET kimligi).
Ciktida yalniz workflow adi, is, adim no ve kural yazilir; hicbir girdi degeri yazilmaz.
"""
import glob
import os
import re
import sys

import yaml

TASIYICI = ("receipt", "receipt_id", "siparis_no", "siparis_ref", "fisler")
LISTE = ("fisler", "siparis_alici")   # birden cok deger (virgullu receipt / 'ad|adres|...' alici): her oge ayri maskelenir
# Yalniz o workflow'da tasiyici olan girdiler: pod-arac-v4 siparis_gonder'de confirm = siparis ref; siparis_alici = alici adi/adresi
EK = {"pod-arac-v4.yml": ("confirm", "siparis_alici")}


def _girdiler(d, ad=""):
    on = d.get(True, d.get("on")) or {}
    if not isinstance(on, dict):
        return []
    wd = on.get("workflow_dispatch")
    ins = (wd or {}).get("inputs") if isinstance(wd, dict) else None
    return [k for k in (ins or {}) if k in TASIYICI or k in EK.get(ad, ())]


def _ifade_re(x):
    return re.compile(r"\$\{\{[^}]*\b(?:github\.event\.)?inputs\.%s\b[^}]*\}\}" % re.escape(x))


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


def _maskeler(metin, x):
    """Adim X'in degerini ::add-mask:: ile kaydediyor mu (degiskene atanmis deger ya da dogrudan jq ifadesi)."""
    degiskenler = set(re.findall(r"\b([A-Za-z_]\w*)=\$\([^\n]*\b%s\b" % re.escape(x), metin))
    if x in LISTE:
        # liste: for <o> in <...$DEG...>; do ... ::add-mask::$<o>   ya da   while ... read -r <o>; do ... done < <(...$DEG...)
        for m in re.finditer(r"for\s+(\w+)\s+in\s+([^;\n]*);\s*do([^\n]*)", metin):
            o, liste, govde = m.group(1), m.group(2), m.group(3)
            if any(re.search(r"\$\{?%s\b" % v, liste) for v in degiskenler) and \
                    re.search(r"::add-mask::\$\{?%s\b" % o, govde):
                return True
        for m in re.finditer(r"while[^\n]*?read\s+-r\s+(\w+);\s*do([^\n]*?)done\s*<\s*<\(([^\n]*)\)", metin):
            o, govde, liste = m.group(1), m.group(2), m.group(3)
            if any(re.search(r"\$\{?%s\b" % v, liste) for v in degiskenler) and \
                    re.search(r"::add-mask::\$\{?%s\b" % o, govde):
                return True
        return False
    for satir in metin.splitlines():
        if "::add-mask::" not in satir:
            continue
        ek = satir.split("::add-mask::", 1)[1]
        if any(re.match(r"\$\{?%s\b" % v, ek) for v in degiskenler):
            return True
        if re.match(r"\$\(jq[^)]*\b%s\b" % re.escape(x), ek):
            return True
    return False


def denetle_veri(d, ad="?"):
    bulgular = []
    girdiler = _girdiler(d, ad)
    if not girdiler:
        return bulgular
    for x in girdiler:
        rx = _ifade_re(x)
        for yol, metin in _gez(d):
            if rx.search(metin):
                bulgular.append(f"{ad}: R1 ifade: '{x}' ${{{{ }}}} ile kullaniliyor ({'/'.join(yol[:4])})")
    for is_adi, is_ in ((d.get("jobs") or {}).items()):
        adimlar = (is_ or {}).get("steps") or []
        for x in girdiler:
            for i, adim in enumerate(adimlar):
                metin = str((adim or {}).get("run") or "")
                if not _okur(metin, x):
                    continue
                if not _maskeler(metin, x):
                    bulgular.append(f"{ad}: R2 maske: is '{is_adi}' adim {i + 1}: '{x}' okunuyor, ::add-mask:: yok")
                break   # yalniz ILK okuyan adim
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
