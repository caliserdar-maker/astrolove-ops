#!/usr/bin/env python3
"""ORNAMENT SIPARIS GIRDISI dogrulama ve bicimleme (Serdar 6 Kas gece, plan claude/AstroLove_ORNAMENT_SIPARIS_PLAN_20261105.md 2.2;
KARARLAR_20261106 N4 gece varsayimlari). Merkez yerelde ve Actions'ta AYNI kod. Saf Python, ag yok, dosyaya yazmaz.

Kurallar (bagli kararlar):
- Isim: karakter denetimi HAM metinde, yalniz [A-Za-z'-]; en az 1 harf; sonra buyuk harf (str.upper, Turkce donusum yok).
  Tire ve duz kesme izinli (KARARLAR_20261104_2, 4 Kas aksam: MARY-JANE, O'NEIL).
  Kivrik kesme, bosluk, aksanli harf, rakam, emoji, Kiril ve diger her karakter: DUR_SERDAR (gece varsayimi; genel kural Serdar karari K3).
  Bos / eksik isim: DUR_SERDAR (ANA_2 7.1: tahmini isim kullanilmaz).
- Tarih: ay adi (tam ya da 3 harf kisaltma; Sept da kabul), gun (1-31, 'st/nd/rd/th' eki atilir), 4 haneli yil; sira serbest.
  Cikti "JUNE 14, 2025" (KARARLAR_20261104_2, 4 Kas aksam). Ay adi yoksa: DUR_GIRDI rakamla_tarih (karar).
  Gun yok, yil 4 hane degil, takvimde olmayan gun, fazla / eksik parca: DUR_SERDAR (kararda yok; K9 gece varsayimi).
- Musteri verisi bu modulden LOGA YAZILMAZ: hata nesneleri yalniz kod ve alan adi tasir, degeri tasimaz.
Kullanim (Actions): python siparis_girdi.py GIRDI.json CIKTI.json  -> cikis 0 PASS, 3 DUR_GIRDI, 4 DUR_SERDAR, 5 bicim hatasi.
  CIKTI.json: {durum, kod, alan, isim1, isim2, tarih, cift, stil} (degerler yalniz PASS'te; Drive'a gider, loga gitmez)."""
import calendar
import json
import re
import sys
from pathlib import Path

BURCLAR = ('AQUARIUS', 'ARIES', 'CANCER', 'CAPRICORN', 'GEMINI', 'LEO', 'LIBRA', 'PISCES', 'SAGITTARIUS', 'SCORPIO', 'TAURUS', 'VIRGO')
STILLER = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
# gece varsayimi N4 / plan K7: goz onayli kapi istisnasi yalniz kendi kosusu icin gecerli (toplama78.py _istisna_kontrol); sipariste uretim yok
ISTISNA_DUR = ('GEMINI_VIRGO', 'GEMINI_GEMINI', 'PISCES_PISCES', 'GEMINI_SAGITTARIUS')
AYLAR = {m.upper(): i for i, m in enumerate(calendar.month_name) if m}
AYLAR.update({m.upper(): i for i, m in enumerate(calendar.month_abbr) if m})
AYLAR['SEPT'] = 9
ISIM_DESEN = re.compile(r"[A-Za-z'\-]+", re.ASCII)
HARF = re.compile(r'[A-Za-z]', re.ASCII)
YIL_ARALIK = (1900, 2100)                                                     # disi DUR_SERDAR (0025 gibi yazim hatasi)


class Dur(Exception):
    """kod: DUR_GIRDI (onayli musteri sorusu var) ya da DUR_SERDAR (Serdar karar verir). neden: kisa kod. alan: alan adi. Deger tasimaz."""

    def __init__(self, kod, neden, alan):
        super().__init__(f'{kod}:{neden}:{alan}')
        self.kod, self.neden, self.alan = kod, neden, alan


def isim_bicimle(ham, alan):
    if not isinstance(ham, str):
        raise Dur('DUR_SERDAR', 'eksik_alan', alan)
    s = ham.strip()
    if not s:
        raise Dur('DUR_SERDAR', 'eksik_alan', alan)
    if not ISIM_DESEN.fullmatch(s):                                          # once ham metin (ß, ı, ’, bosluk, aksan buradan doner)
        raise Dur('DUR_SERDAR', 'izinsiz_karakter', alan)
    if not HARF.search(s):
        raise Dur('DUR_SERDAR', 'harf_yok', alan)
    if s[0] in "'-" or s[-1] in "'-" or '--' in s or "''" in s:              # bas / son ya da cift isaret (-A-, MARY--JANE): Serdar'a
        raise Dur('DUR_SERDAR', 'kenar_isaret', alan)
    u = s.upper()
    if not ISIM_DESEN.fullmatch(u) or len(u) != len(s):                     # upper sonrasi da yalniz ASCII (savunma)
        raise Dur('DUR_SERDAR', 'izinsiz_karakter', alan)
    return u


def tarih_bicimle(ham, alan='tarih'):
    if not isinstance(ham, str) or not ham.strip():
        raise Dur('DUR_SERDAR', 'eksik_alan', alan)
    s = ham.strip()
    if not s.isascii():                                                       # tam genislikli rakam, Unicode bosluk vb.
        raise Dur('DUR_SERDAR', 'gecersiz_tarih', alan)
    parca = [p for p in re.split(r'[\s,./\-]+', s) if p]
    harfli = [p for p in parca if re.search(r'[A-Za-z]', p)]
    if not harfli:
        if re.search(r'[0-9]', s):
            raise Dur('DUR_GIRDI', 'rakamla_tarih', alan)
        raise Dur('DUR_SERDAR', 'gecersiz_tarih', alan)
    ay = None
    gun = yil = None
    kalan = []
    for p in parca:
        pu = p.upper()
        if pu in AYLAR and ay is None:
            ay = AYLAR[pu]
            continue
        m = re.fullmatch(r'([0-9]{1,2})(ST|ND|RD|TH)?', pu)
        if m and gun is None and len(p) <= 4:
            gun = int(m.group(1)); continue
        if re.fullmatch(r'[0-9]{4}', p) and yil is None:
            yil = int(p); continue
        kalan.append(p)
    if ay is None:
        raise Dur('DUR_SERDAR', 'ay_okunamadi', alan)
    if kalan or gun is None or yil is None or not YIL_ARALIK[0] <= yil <= YIL_ARALIK[1]:
        raise Dur('DUR_SERDAR', 'gecersiz_tarih', alan)
    if not 1 <= gun <= calendar.monthrange(yil, ay)[1]:
        raise Dur('DUR_SERDAR', 'gecersiz_tarih', alan)
    return f'{calendar.month_name[ay].upper()} {gun}, {yil}'


def cift_dogrula(cift):
    if not isinstance(cift, str):
        raise Dur('DUR_SERDAR', 'cift_gecersiz', 'cift')
    c = cift.strip().upper()
    p = c.split('_')
    if len(p) != 2 or any(b not in BURCLAR for b in p) or '_'.join(sorted(p)) != c:
        raise Dur('DUR_SERDAR', 'cift_gecersiz', 'cift')
    if c in ISTISNA_DUR:
        raise Dur('DUR_SERDAR', 'istisna_cifti_K7', 'cift')
    return c


def stil_dogrula(stil):
    s = (stil or '').strip().upper().replace(' ', '_')
    if s not in STILLER:
        raise Dur('DUR_SERDAR', 'stil_gecersiz', 'stil')
    return s


def dogrula(g):
    """g: dict(cift, stil, isim1, isim2, tarih, [sira]). Doner dict(durum='PASS', ...) ya da Dur firlatir."""
    if not isinstance(g, dict):
        raise Dur('DUR_SERDAR', 'bicim', 'girdi')
    if g.get('sira') not in (None, '', 'normal'):
        raise Dur('DUR_SERDAR', 'sira_ters_K5', 'sira')                    # plan K5: v1'de kod yolu yok
    cift = cift_dogrula(g.get('cift'))
    stil = stil_dogrula(g.get('stil'))
    i1 = isim_bicimle(g.get('isim1'), 'isim1')
    i2 = isim_bicimle(g.get('isim2'), 'isim2')
    t = tarih_bicimle(g.get('tarih'))
    return dict(durum='PASS', kod=None, alan=None, cift=cift, stil=stil, isim1=i1, isim2=i2, tarih=t)


def main(argv):
    if len(argv) != 3:
        print('kullanim: siparis_girdi.py GIRDI.json CIKTI.json', flush=True); return 5
    try:
        g = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    except Exception:                                                          # noqa: BLE001  (icerik loga yazilmaz)
        print('GIRDI bicim hatasi (icerik yazilmaz)', flush=True); return 5
    try:
        r = dogrula(g)
        kod = 0
    except Dur as d:
        r = dict(durum=d.kod, kod=d.neden, alan=d.alan)
        kod = 3 if d.kod == 'DUR_GIRDI' else 4
    Path(argv[2]).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
    print('GIRDI', r['durum'], r.get('kod') or '', r.get('alan') or '', flush=True)   # yalniz kod ve alan adi
    return kod


if __name__ == '__main__':
    sys.exit(main(sys.argv))
