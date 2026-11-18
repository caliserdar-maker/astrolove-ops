#!/usr/bin/env python3
"""Receipt log kapisi v3 (IP adim 0 c, 17 Kas 2026; 2 bagimsiz inceleme turu sonrasi IZIN LISTESI). Depo HERKESE ACIK.

Bu bir SEZGISEL REGRESYON KONTROLUDUR, kanit degildir: bilinen sizinti bicimlerini ve onayli okuma/maske kaliplarinin
disina cikan her satiri FAIL eder. Siparis no tasiyan girdiler (TASIYICI + EK) icin kurallar (her biri bulgu = FAIL):
  R1 ifade   : `${{ }}` icinde inputs.X, github.event.inputs, toJSON(inputs|github...), inputs[...], github.event (butun),
               format(...inputs...) -> `if:` DISINDA yasak (run, env, with, name, run-name, concurrency, outputs ...).
  R2 kalip   : tasiyici okuyan HER satir su kaliplardan biri olmali:
               MASKE    D=$(jq -r '<.inputs.X ...>' "$GITHUB_EVENT_PATH"|"$E"); [<koruma>] echo "::add-mask::$D"  (ayni satir)
               MASKE2   D=$(jq ...) ve HEMEN sonraki satir kosulsuz maske (`echo "::add-mask::$D"`, `[ -z "$D" ] ||`,
                        `[ ${#D} -lt N ] ||`); liste girdisi icin sonraki (ya da ayni) satir her ogeyi maskeleyen
                        `while IFS= read -r o; do ... echo "::add-mask::$o"; done < <(tr .. <<< "$D")` dongusu
               DOGRULA  `jq -re '...inputs.X...' ... >/dev/null` (cikti atilir)
               YENIDEN  ayni iste daha once (if:'siz bir adimda ya da ayni adimin onceki satirinda) X maskelendiyse okuma
               Maske satiri blok icinde olamaz (if/case/for/while/fonksiyon/heredoc; onceki satir &&, ||, |, \\ ile bitemez).
  R0 butun   : olay dosyasinin butunu (jq ., jq -c ., .inputs |, .inputs[, to_entries, cat/grep/head/sed/< olay, Python /
               github-script / baska dil) yasak. Istisnalar: ONAYLI_BUTUN (dosyaya yonlendirme, maskeden sonra) ve
               ONAYLI_PYTHON (metin sha256 ile birebir onayli adim).
  R0 xtrace  : tasiyici workflow'da set -x / -o xtrace / bash -x, shell: ...-x..., defaults shell -x, SHELLOPTS xtrace yasak.
  R3 sinif   : aciklamasi siparis no / order id / receipt / fis / merchant ref anlatan her girdi (workflow_dispatch ve
               workflow_call) TASIYICI ya da KAPSAM_DISI olmali.
Ciktida yalniz workflow adi, is, adim no ve kural yazilir; hicbir girdi degeri yazilmaz.
"""
import glob
import hashlib
import os
import re
import sys

import yaml

TASIYICI = ("receipt", "receipt_id", "siparis_no", "siparis_ref", "fisler")
LISTE = ("fisler", "siparis_alici", "taban", "skus")
EK = {"pod-arac-v4.yml": ("confirm", "siparis_alici"),
      "pod-order-router.yml": ("submit",),
      "a3-esit-kiyas.yml": ("eski", "yeni", "taban"),
      "prodigi-quote.yml": ("skus",)}                     # siparis_oku modunda 'order_id,merchantReference'

KAPSAM_DISI = {"test_receipt": "depodaki sahte receipt dosya yolu", "sahte_receipt": "depodaki sahte receipt dosya yolu",
               "receipt_pages": "sayfa sayisi", "since_days": "gun sayisi", "sadece_test": "evet/hayir",
               "son4": "son 4 hane (tam no degil)", "beklenen": "dosya sayisi", "expect_order": "SET kimligi", "yaz": "evet/hayir"}
SINIF = re.compile(r"receipt|sipari[sş]\s*(no|numara)|\border\s*(id|no|number)|\bfi[sş]\b|merchant.?ref", re.I)
# by-siparis-ornek "Musteri metnini maskele" adimi (isim/tarih/satir + siparis_no maskesi); metin degisirse yeniden onay
ONAYLI_PYTHON = {"by-siparis-ornek.yml": "6d17062617c0a9fc97a81f086a5458bb778f573a1edab78e4565c0defd45a9d2"}
# Ciplak nokta iceren ama yalniz belirli anahtari okuyan onayli jq filtreleri (birebir metin)
ONAYLI_FILTRE = {'(.inputs.siparis_ref // "") | if . == "" then "etsy-1000000001-8x10" else . end'}   # pod-arac-v4 varsayilan
# siparis-giris 'yeni' isi: girdiler maskeden SONRA dosyaya yazilir (stdout'a degil)
ONAYLI_BUTUN = re.compile(r"""^\s*jq\s+'\.inputs\s*\|\s*\{[a-z0-9_, ]+\}'\s+"\$E"\s*>\s*/tmp/[a-z_]+\.json\s*$""")

OLAY = r'"?\$\{?(?:GITHUB_EVENT_PATH|E)\}?"?'
XTRACE = re.compile(r"(^|[\s;])set\s+(-[a-wyz]*x|-o\s+xtrace)|\bbash\s+-[a-z]*x|\bsh\s+-[a-z]*x")
IFADE = re.compile(r"\$\{\{(.*?)\}\}", re.S)


def _on(d):
    return d.get(True, d.get("on")) or {}


def _ins(d):
    on = _on(d)
    if not isinstance(on, dict):
        return {}
    out = {}
    for tur in ("workflow_dispatch", "workflow_call"):
        w = on.get(tur)
        out.update(((w or {}).get("inputs") if isinstance(w, dict) else None) or {})
    return out


def _girdiler(d, ad=""):
    return [k for k in _ins(d) if k in TASIYICI or k in EK.get(ad, ())]


def _gez(o, yol=()):
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


def _ifade_yasak(ic, girdiler):
    ic = re.sub(r"'[^']*'", "''", ic)                       # format('{0}', ...) gibi sabitler
    if re.search(r"\bgithub\.event\.inputs\b(?!\.\w)|\binputs\s*\[|\btoJSON\s*\(\s*(inputs|github)\b|\bgithub\.event\s*(\)|$|\s|,)", ic):
        return True
    return any(re.search(r"\binputs\.%s\b" % re.escape(x), ic) for x in girdiler)


def _tasiyici_okur(satir, x):
    return bool(re.search(r"\.inputs\.%s\b" % re.escape(x), satir) or
                re.search(r"""\.inputs\s*\[\s*["']%s["']""" % re.escape(x), satir))


def _tirnaksiz(s):
    return re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", s)


def _parcala(satir):
    """Komut parcalari: tirnak disindaki |, ||, &&, ;, `, (, ) ile ve $( / <( ile bolunur; $( icinde tirnak durumu yeniden
    baslar (kabuk kurali), kapaninca dis durum geri gelir."""
    out, cur, i = [], "", 0
    yigin = [[False, False]]                                   # [tek, cift] her $( duzeyi icin
    while i < len(satir):
        c = satir[i]
        tek, cift = yigin[-1]
        if c == "'" and not cift:
            yigin[-1][0] = not tek
        elif c == '"' and not tek:
            yigin[-1][1] = not cift
        elif not tek:
            if satir.startswith("$(", i) or satir.startswith("<(", i):
                out.append(cur); cur = ""; yigin.append([False, False]); i += 2; continue
            if c == ")" and not cift and len(yigin) > 1:
                out.append(cur); cur = ""; yigin.pop(); i += 1; continue
            if not cift and (c in "|;`()" or satir.startswith("&&", i)):
                out.append(cur); cur = ""; i += 2 if satir.startswith("&&", i) else 1; continue
        cur += c
        i += 1
    out.append(cur)
    return out


def _butun_okur(satir, e_olay, girdiler):
    """Satirda olay dosyasini (GITHUB_EVENT_PATH ya da E="$GITHUB_EVENT_PATH" ise $E) OKUYAN her komut parcasi jq olmali ve
    belirli bir anahtari okumali. $ olmadan GITHUB_EVENT_PATH (Python os.environ vb.) = betik dili erisimi (ayri kural)."""
    ref = r"\$\{?GITHUB_EVENT_PATH\}?" + (r"|\$\{?E\}?(?!\w)" if e_olay else "")
    if not re.search(ref, satir):
        return False
    if re.search(r"<\s*\"?(%s)" % ref, satir):
        return True
    for parca in _parcala(satir):
        if not re.search(ref, parca):
            continue
        kel = [w for w in re.findall(r"""(?:'[^']*'|"(?:\\.|[^"\\])*"|\S)+""", parca) if not re.match(r"^\w+=", w)]
        while kel and kel[0] in ("do", "then", "else", "elif", "!", "{", "if", "while", "until"):
            kel = kel[1:]                                    # kabuk anahtar kelimesi: komut sonraki kelime
        if not kel:
            continue                                          # yalniz atama: E="$GITHUB_EVENT_PATH"
        if kel[0] in ("[", "[[", "test"):
            continue
        if kel[0] != "jq":
            return True
        filtre, j = "", 1
        while j < len(kel):
            if kel[j] in ("--arg", "--argjson"):
                j += 3
                continue
            if not kel[j].startswith("-") and not re.match(r'^"?\$', kel[j]):
                filtre = kel[j]
                break
            j += 1
        f = filtre.strip("'\"")
        if f in ONAYLI_FILTRE:
            continue
        if re.search(r"(^|[\s|(])\.\s*($|[\s|)])", " " + _tirnaksiz(f) + " ") or re.search(r"\.inputs\s*($|[\s|)\]])|to_entries|\.\[\]|\bpaths\b|tostream|\.\.|\bkeys\b|\$__loc__|input_filename", f):
            return True
        if re.search(r"\.inputs(\.\$|\[\s*\$)", f):           # degiskenli anahtar: dongu listesinde tasiyici olamaz
            liste = " ".join(re.findall(r"for\s+\w+\s+in\s+([^;]*);", satir))
            if any(re.search(r"\b%s\b" % re.escape(x), liste) for x in girdiler) or not liste:
                return True
        elif not re.search(r"\.inputs(\.\w+|\[\s*\"\w+\"\s*\])", f):
            return True
    return False


def _blok_derinligi(satirlar):
    """Her satir icin: blok icinde mi (if/case/for/while/fonksiyon/heredoc) ya da onceki satira bagli mi."""
    derin, heredoc, sonuc, onceki = 0, None, [], ""
    for s in satirlar:
        t = s.strip()
        if heredoc:
            sonuc.append(True)
            if t == heredoc:
                heredoc = None
            continue
        bagli = bool(re.search(r"(&&|\|\||\||\\)\s*$", onceki))
        sonuc.append(derin > 0 or bagli)
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_]+)['\"]?", t)
        if m and not re.search(r"<<<", t):
            heredoc = m.group(1)
        u = _tirnaksiz(t)
        acilis = len(re.findall(r"(^|[;\s])(if|case|for|while|until)\s", " " + u)) + len(re.findall(r"\(\)\s*\{\s*$|^\{\s*$", u))
        kapanis = len(re.findall(r"(^|[;\s])(fi|esac|done)(\s|;|$)", " " + u)) + (1 if re.match(r"^\}\s*$", u) else 0)
        derin = max(0, derin + acilis - kapanis)
        onceki = t
    return sonuc


def _koruma(d):
    return r'(?:\[\s*-z\s+"\$%s"\s*\]\s*\|\|\s*|\[\s*\$\{#%s\}\s+-lt\s+\d+\s*\]\s*\|\|\s*)?' % (d, d)


def _maske_satiri(satir, d):
    return bool(re.match(r'^\s*' + _koruma(d) + r'echo\s+"::add-mask::\$%s"' % d, satir))


def _liste_maske(satir, d):
    m = re.search(r'while\s+IFS=\s+read\s+-r\s+(\w+);\s*do\s+(?:\[\s*-z\s+"\$(\w+)"\s*\]\s*\|\|\s*|\[\s*\$\{#(\w+)\}\s+-lt\s+\d+\s*\]\s*\|\|\s*)'
                  r'echo\s+"::add-mask::\$(\w+)";\s*done\s*<\s*<\(tr\s+\S+\s+\S+\s+<<<\s+"\$%s"\)' % d, satir)
    return bool(m) and len({m.group(1), m.group(2) or m.group(3), m.group(4)}) == 1


def _adim_denetle(metin, girdiler, maskeli, ad, yer):
    """metin: adimin run metni; maskeli: bu iste once maskelenmis tasiyicilar (guncellenir). Bulgu listesi doner."""
    b = []
    satirlar = metin.split("\n")
    blokta = _blok_derinligi(satirlar)
    e_tanimli = any(re.match(r'^\s*E="\$GITHUB_EVENT_PATH"\s*$', s) for s in satirlar)
    for i, s in enumerate(satirlar):
        if re.search(r"(?<![\${])\bGITHUB_EVENT_PATH\b", s):
            b.append(f"{ad}: R0 olay dosyasi betik diliyle okunuyor, onayli degil ({yer} satir {i + 1})")
            continue
        if _butun_okur(s, e_tanimli, girdiler) and not (ONAYLI_BUTUN.match(s) and maskeli):
            b.append(f"{ad}: R0 olay dosyasinin butunu okunuyor ({yer} satir {i + 1})")
            continue
        for x in girdiler:
            if not _tasiyici_okur(s, x):
                continue
            if re.search(r"jq\s+-re\s+'[^']*\.inputs\.%s\b[^']*'\s+%s\s*>\s*/dev/null" % (re.escape(x), OLAY), s):
                continue                                     # DOGRULA
            m = re.match(r"""^\s*(\w+)=\$\(jq\s+-r\s+'[^']*\.inputs\.%s\b[^']*'\s+%s\)(.*)$""" % (re.escape(x), OLAY), s)
            if m and not blokta[i]:
                d, kalan = m.group(1), m.group(2)
                sonraki = satirlar[i + 1] if i + 1 < len(satirlar) else ""
                kalan_ifade = re.sub(r"^\s*;\s*", "", kalan)
                bos = not re.sub(r"#.*$", "", kalan).strip()
                if x in LISTE:
                    if _liste_maske(kalan_ifade, d) or (bos and _liste_maske(sonraki, d) and not blokta[i + 1]):
                        maskeli.add(x)
                        continue
                elif _maske_satiri(kalan_ifade, d) or (bos and _maske_satiri(sonraki, d) and not blokta[i + 1]):
                    maskeli.add(x)
                    continue
            if x in maskeli:
                continue                                     # YENIDEN (maske ayni iste daha once kaydedildi)
            b.append(f"{ad}: R2 kalip: '{x}' onayli okuma/maske kalibinin disinda okunuyor ({yer} satir {i + 1})")
    return b


def denetle_veri(d, ad="?"):
    bulgular = []
    ins = _ins(d)
    for k, v in ins.items():
        aciklama = str((v or {}).get("description", "")) if isinstance(v, dict) else ""
        secenek = (v or {}).get("options") if isinstance(v, dict) else None
        if isinstance(secenek, list):
            # secim (choice) girdisi yalniz listelenen degerleri alir: siparis no tasiyamaz; secenekler sayi icermemeli
            if any(re.search(r"(?<!\d)\d{10,12}(?!\d)", str(o)) for o in secenek):
                bulgular.append(f"{ad}: R3 sinif: '{k}' secim girdisinin seceneginde 10-12 haneli sayi var")
            continue
        if SINIF.search(aciklama) and k not in TASIYICI and k not in EK.get(ad, ()) and k not in KAPSAM_DISI \
                and (ad, k) not in KAPSAM_DISI:
            bulgular.append(f"{ad}: R3 sinif: '{k}' aciklamasi siparis no anlatiyor, TASIYICI / KAPSAM_DISI degil")
    girdiler = _girdiler(d, ad)
    if not girdiler:
        return bulgular
    for yol, metin in _gez(d):
        for m in IFADE.finditer(metin):
            if _ifade_yasak(m.group(1), girdiler):
                bulgular.append(f"{ad}: R1 ifade: tasiyici / butun girdi ${{{{ }}}} ile kullaniliyor ({'/'.join(yol[:4])})")
    kab = str(((d.get("defaults") or {}).get("run") or {}).get("shell", ""))
    if XTRACE.search(" " + kab) or re.search(r"xtrace", str(d.get("env") or {})):
        bulgular.append(f"{ad}: R0 xtrace (defaults / env)")
    for is_adi, is_ in ((d.get("jobs") or {}).items()):
        is_ = is_ or {}
        js = str(((is_.get("defaults") or {}).get("run") or {}).get("shell", ""))
        if XTRACE.search(" " + js) or re.search(r"xtrace", str(is_.get("env") or {})):
            bulgular.append(f"{ad}: R0 xtrace (is '{is_adi}')")
        maskeli = set()
        for i, adim in enumerate(is_.get("steps") or []):
            adim = adim or {}
            yer = f"is '{is_adi}' adim {i + 1}"
            metin = str(adim.get("run") or "")
            if str(adim.get("uses", "")).startswith("actions/github-script"):
                bulgular.append(f"{ad}: R0 github-script tasiyici workflow'da ({yer})")
            if XTRACE.search(" " + str(adim.get("shell", ""))) or XTRACE.search(metin) or re.search(r"xtrace", str(adim.get("env") or {})):
                bulgular.append(f"{ad}: R0 xtrace ({yer})")
            if re.search(r"(?<![\${])\bGITHUB_EVENT_PATH\b", metin) and \
                    ONAYLI_PYTHON.get(ad) == hashlib.sha256(metin.encode()).hexdigest():
                if adim.get("if") is None:
                    maskeli.update(girdiler)                 # onayli Python maske adimi (metni birebir)
                continue
            onceki = set(maskeli)
            b = _adim_denetle(metin, girdiler, maskeli, ad, yer)
            bulgular += b
            if adim.get("if") is not None:
                maskeli.intersection_update(onceki)          # if:'li adimin maskesi sonraki adimlar icin sayilmaz
    return bulgular


def denetle(yol):
    with open(yol, encoding="utf-8") as f:
        return denetle_veri(yaml.safe_load(f), os.path.basename(yol))


def main(argv):
    kok = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    dosyalar = sorted(glob.glob(os.path.join(kok, ".github", "workflows", "*.yml")))
    tum, kapsam = [], 0
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
