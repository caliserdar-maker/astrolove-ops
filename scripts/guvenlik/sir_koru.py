#!/usr/bin/env python3
"""Sir koruyucu (14 Eki 2026, OZET.txt token sizintisi duzeltmesi). Uc komut:

  tee   [--sir-json F]... DOSYA...   stdin -> stdout AYNEN (runner '::add-mask::' komutlarini isler);
                                     dosyalara yalniz suzulmus satirlar eklenir: '::add-mask::' satiri YAZILMAZ,
                                     bilinen bir sir degeri iceren satir yerine '[SIR ICEREN SATIR ENGELLENDI]' yazilir
                                     ve sonunda cikis kodu 1 (is FAIL olur).
  tara  [--sir-json F]... YOL...     dosya/dizinleri tarar: '::add-mask::', bilinen sir degerleri, X-Amz-Signature,
                                     log_suz desenleri. Bulursa yalniz DOSYA ADI + sayi yazar (deger yazmaz), cikis 1.
  temizle [--sir-json F]... GIRIS CIKIS   ayni suzgecle temiz kopya yazar; kalan bulgu sayisini yazar.

Sir degerleri: --sir-json dosyalarindaki (token/secret/key/password adli) en az 12 karakterlik metin degerleri
+ akista gorulen '::add-mask::' degerleri. Degerler hicbir yere yazilmaz."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from log_suz import DESEN, MASK  # noqa: E402

ENGEL = '[SIR ICEREN SATIR ENGELLENDI]\n'
AMZ = re.compile(r'X-Amz-(Signature|Credential|Security-Token)=(?!\*\*\*)', re.I)


def sir_json(yol):
    out = set()
    try:
        d = json.load(open(yol))
    except Exception:
        return out

    def gez(x, ad=''):
        if isinstance(x, dict):
            for k, v in x.items():
                gez(v, k)
        elif isinstance(x, list):
            for v in x:
                gez(v, ad)
        elif isinstance(x, str) and len(x) >= 12 and re.search(r'token|secret|key|password|sifre', ad, re.I):
            out.add(x)
    gez(d)
    return out


def arg_ayir(argv):
    sirlar, kalan, i = set(), [], 0
    while i < len(argv):
        if argv[i] == '--sir-json':
            sirlar |= sir_json(argv[i + 1]); i += 2
        else:
            kalan.append(argv[i]); i += 1
    return sirlar, kalan


def bulgu(satir, sirlar):
    if MASK in satir:
        return 'add-mask'
    if any(s in satir for s in sirlar):
        return 'sir-degeri'
    if AMZ.search(satir):
        return 'presigned-url'
    if any(m.group(2) != '***' for m in DESEN.finditer(satir)):
        return 'anahtar-deseni'
    return ''


def tee(argv):
    sirlar, dosyalar = arg_ayir(argv)
    fh = [open(d, 'a', encoding='utf-8') for d in dosyalar]
    engel = 0
    for satir in sys.stdin:
        sys.stdout.write(satir); sys.stdout.flush()
        if MASK in satir:
            v = satir.split(MASK, 1)[1].strip()
            if len(v) >= 6:
                sirlar.add(v)
            continue
        b = bulgu(satir, sirlar)
        for f in fh:
            f.write(ENGEL if b else satir); f.flush()
        engel += bool(b)
    for f in fh:
        f.close()
    if engel:
        if os.environ.get('RUNNER_TEMP'):   # isin son adimi bu isaretle FAIL eder (pipefail olmayan adimlar icin)
            open(os.path.join(os.environ['RUNNER_TEMP'], 'SIR_ENGEL'), 'a').write(f'{engel}\n')
        print(f'::error::sir_koru: {engel} satir sir icerdigi icin dosyaya yazilmadi (is FAIL)', flush=True)
        sys.exit(1)


def dosyalar_(yollar):
    for y in yollar:
        if os.path.isdir(y):
            for kok, _, ds in os.walk(y):
                for d in ds:
                    yield os.path.join(kok, d)
        elif os.path.exists(y):
            yield y


def tara(argv):
    sirlar, yollar = arg_ayir(argv)
    toplam = 0
    for d in dosyalar_(yollar):
        try:
            metin = open(d, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        say = {}
        for s in metin.splitlines():
            b = bulgu(s, sirlar)
            if b:
                say[b] = say.get(b, 0) + 1
        if say:
            toplam += sum(say.values())
            print(f'SIR VAR: {d} {say}', flush=True)
    print('SIR TARAMA ' + ('TEMIZ' if not toplam else f'FAIL ({toplam} satir)'), flush=True)
    sys.exit(1 if toplam else 0)


def temizle(argv):
    sirlar, (gir, cik) = arg_ayir(argv)
    kalan = 0
    with open(gir, encoding='utf-8', errors='ignore') as f, open(cik, 'w', encoding='utf-8') as g:
        for s in f:
            if MASK in s:
                continue
            for v in sirlar:
                s = s.replace(v, '***')
            s = AMZ.sub(lambda m: m.group(0) + '***', s)
            s = DESEN.sub(lambda m: m.group(1) + '***', s)
            kalan += bool(bulgu(s, sirlar))
            g.write(s)
    print(f'TEMIZLENDI {os.path.basename(gir)}; kalan bulgu {kalan}', flush=True)
    sys.exit(1 if kalan else 0)


if __name__ == '__main__':
    komut, argv = sys.argv[1], sys.argv[2:]
    {'tee': tee, 'tara': tara, 'temizle': temizle}[komut](argv)
