#!/usr/bin/env python3
"""Kapak videosu v2: isim + tagline dongusu, Serdar onayli v5 sablonu (video-v1 dali, 25 Eyl 2026; video_cift.py / qc_video78.py).
Varyantlar (qc_video78.py BEKLENEN; baskasi yok), her biri 11x14 gercek hat baskisi (siparis_dosyasi.py, degistirilmeden):
  EJ EMILY/JAMES      'It Began With a Kiss in the Rain' (TEMP/POD_KAPAK_V3/SIPARIS onbellegi)
  IN ISABELLA/NOAH    "I'd Choose You in Every Lifetime"
  AM ALEXANDER/MIA    'You Feel Like Home'
AM tagline kurali (v5): EJ ve AM tagline tabani baskida olculur (tagline_olc.py yontemi: R-B>40 altin maske, en buyuk yatay
bilesen, %50 profil son satiri; bant = EJ/AM farkinin en alt metin satiri). Fark > 3 px ise v5 kaydirmasi: AM tagline murekkebi
EJ tabanina kaydirilir, zemin uc baskidan piksel bazinda en az murekkepli olan. Poster/isim/tagline yeniden cizilmez.
Her varyant kapak_v8_kur.py ile v9 sahnesine oturur (ilk kare = EJ kapagi). Zoom yok, sabit kadraj.
Zamanlama v5 (video_cift.py): 30 fps, EJ -> IN -> AM, 3 tur, gecis 12 kare (v2 referans egrisi), sabit 30 kare,
ilk gorunur gecis 0.20 sn, 378 kare = 12.6 sn. 2880x2160, sessiz, < 100 MB.
QC: 378 kare / 12.6 sn / 30 fps / 2880x2160 / ses yok / < 100 MB; ilk kare = EJ kapagi NCC >= 0.99; her varyantin sabit
karesinde poster NCC >= 0.99 (o varyantin baskisiyla, sigma1); gecis anlari (gorunur baslangiclar) plan ile +-1 kare. FAIL -> cikis 1.
ETA sayaci: islenen/toplam, gecen, kalan, yuzde.
Toplu kosu (video-77 duzeni): 8 paralel parca, her biri ciftlerin [parca::8]'i; her cift biter bitmez Drive'a yazilir.
Durum TEMP/POD_VIDEO_V2/SON_V5: PASS olan cift sonraki kosuda yeniden uretilmez (video + QC + IN karesi damgaya kopyalanir).
Birlestirme: damgadaki QC_*.json -> OZET.md (cift basina 1 satir) + ONIZLEME.jpg (her ciftten IN karesi).
Kullanim: video_v2_toplu.py uret SB_DIZIN DAMGA PARCA TOPLAM (HEPSI | CIFT [CIFT ...])
          video_v2_toplu.py birlestir DAMGA (HEPSI | CIFT [CIFT ...])
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

KOK = Path(__file__).resolve().parents[2]
OUT = Path('_out')
W = Path('_work')
SAHNE = W / 'sahne_1213.png'
SB = None

V1_SIP = 'gdrive:ASTROLOVE/TEMP/POD_KAPAK_V3/SIPARIS'
V23_SIP = 'gdrive:ASTROLOVE/TEMP/POD_VIDEO_V2/SIPARIS'
KOK_D = 'gdrive:ASTROLOVE/TEMP/POD_VIDEO_V2'
SON = f'{KOK_D}/SON_V5'
VARYANT = {'EJ': ('EMILY', 'JAMES', 'It Began With a Kiss in the Rain'),
           'IN': ('ISABELLA', 'NOAH', "I'd Choose You in Every Lifetime"),
           'AM': ('ALEXANDER', 'MIA', 'You Feel Like Home')}
SIRA = ['EJ', 'IN', 'AM']
RENK, BOY = 'MIDNIGHT_BLUE', '11x14'
FPS, BAS, GECIS, SABIT, TUR = 30, 4, 12, 30, 3            # v5 (video_cift.py)
VW, VH = 2880, 2160
KAP_ARG = (295, 30, 919, 880)                              # kapak_v8_kur.py BX0 BY0 BX1 TABAN (1213x910 sahne)
TAG_ESIK = 3                                               # AM-EJ tagline taban farki (px, baski) > 3 -> kaydir


def rc(*a, kontrol=True):
    return subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                          capture_output=True, text=True, check=kontrol)


def v1_kapi_gecti(rec):
    """V1 onbellegindeki baskinin hat kapilari (KAPI_RAPORU.json): kapi FAIL baski kullanilmaz (28 Eyl: AQUARIUS_LIBRA
    EJ baskisi sembol kapisi FAIL iken onbellege alinmisti)."""
    r = rc('cat', f'{V1_SIP}/{rec}/KAPI_RAPORU.json', kontrol=False)
    try:
        return r.returncode == 0 and bool(json.loads(r.stdout).get('kapilar_gecti'))
    except ValueError:
        return False


def baski_al(cift, i1, i2, mesaj, v1):
    if v1 and not v1_kapi_gecti(f'{cift}_{RENK}_{BOY}'):
        print(f'{cift}: V1 onbellek baskisi kapi FAIL/raporsuz -> hattan yeniden', flush=True)
        v1 = False                                            # V23 onbellegi / hat (kapilar gecmezse hat cikis 1)
    rec = f'{cift}_{RENK}_{BOY}' if v1 else f'{cift}_{i1}_{i2}'
    yer = W / 'baski' / rec / f'BASKI_{BOY}.jpg'
    yer.parent.mkdir(parents=True, exist_ok=True)
    kaynak = V1_SIP if v1 else V23_SIP
    if rc('copyto', f'{kaynak}/{rec}/BASKI_{BOY}.jpg', str(yer), kontrol=False).returncode == 0 and yer.exists():
        return yer
    if v1:
        raise SystemExit(f'HATA: V1 onbellekte yok: {rec}. DUR.')
    args = ['--cift', cift, '--renk', RENK, '--boy', BOY, '--isim1', i1, '--isim2', i2,
            '--mesaj-b64', base64.b64encode(mesaj.encode()).decode()]
    kod = ("import sys; sys.path.insert(0, 'scripts/medya_v1'); import siparis_dosyasi as s; "
           f"s.SIP = {V23_SIP!r}; sys.argv = ['siparis_dosyasi.py'] + {args!r}; s.main()")
    subprocess.run([sys.executable, '-c', kod], cwd=SB, check=True)
    hat_cikti = SB / '_siparis' / f'{cift}_{RENK}_{BOY}' / f'BASKI_{BOY}.jpg'
    if not hat_cikti.exists():
        raise SystemExit(f'HATA: hat ciktisi yok: {hat_cikti}. DUR.')
    hat_cikti.replace(yer)
    rc('copyto', str(yer), f'{V23_SIP}/{rec}/BASKI_{BOY}.jpg', kontrol=False)
    return yer


def _rgb(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32)


def tagline_bandi(ej, am):
    """EJ ve AM baskilari yalniz isim + tagline'da farklidir; farkin en alt metin satiri = tagline bandi (satir araligi)."""
    d = np.abs(ej - am).max(2) > 60
    d = ndimage.binary_opening(d, structure=np.ones((3, 3)))
    satir = ndimage.binary_closing(d.any(1), structure=np.ones(25))
    lab, n = ndimage.label(satir)
    if n == 0:
        raise SystemExit('HATA: EJ/AM baskilari arasinda fark yok. DUR.')
    ys = np.where(lab == n)[0]
    return int(ys[0]), int(ys[-1])


def taban(P, y0, y1):
    """tagline_olc.py yontemi: altin maske R-B>40, en buyuk yatay bilesen (yildizlar ayiklanir), %50 profil son satiri."""
    b = P[y0:y1]; m = (b[..., 0] - b[..., 2]) > 40
    lab, n = ndimage.label(ndimage.binary_dilation(m, structure=np.ones((5, 101))))
    m &= lab == (np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1)
    pr = m.sum(1).astype(float)
    return y0 + int(np.where(pr > 0.5 * pr.max())[0][-1])


def am_tagline(baskilar, cikis):
    """v5 kurali: AM tagline tabani EJ'den > TAG_ESIK px farkliysa AM murekkebi EJ tabanina kaydirilir."""
    P = {k: _rgb(baskilar[k]) for k in SIRA}
    r0, r1 = tagline_bandi(P['EJ'], P['AM'])
    M = 60
    y0, y1 = max(r0 - M, 0), min(r1 + M, P['EJ'].shape[0])
    tb_ej, tb_am = taban(P['EJ'], y0, y1), taban(P['AM'], y0, y1)
    dy = tb_am - tb_ej
    kayit = {'tagline_bandi': [r0, r1], 'taban_EJ': tb_ej, 'taban_AM_once': tb_am, 'fark_px': dy, 'esik_px': TAG_ESIK,
             'kaydirma_px': dy if abs(dy) > TAG_ESIK else 0}
    if abs(dy) <= TAG_ESIK:
        return baskilar['AM'], kayit
    if abs(dy) >= M:
        raise SystemExit(f'HATA: AM tagline farki {dy} px, bant payi {M} px. DUR.')
    bant = {k: P[k][y0:y1] for k in SIRA}
    rb = np.stack([bant[k][..., 0] - bant[k][..., 2] for k in SIRA]); sec = np.argmin(rb, 0)
    zemin = np.choose(sec[..., None], [bant[k] for k in SIRA])
    w = np.clip((rb[2] - 20) / 60, 0, 1)[..., None]            # AM murekkep agirligi
    ks = lambda X: np.roll(X, -dy, axis=0)
    yeni = P['AM'].copy(); yeni[y0:y1] = zemin * (1 - ks(w)) + ks(bant['AM']) * ks(w)
    Image.fromarray(np.clip(np.rint(yeni), 0, 255).astype(np.uint8)).save(cikis)
    kayit['taban_AM_sonra'] = taban(yeni, y0, y1)
    return cikis, kayit


def kapak(baski, cikis):
    r = subprocess.run([sys.executable, str(KOK / 'scripts/pod/kapak_v8_kur.py'), str(SAHNE), str(baski),
                        str(KOK / 'data/pod/cila_cerceve_kaynak.png'), str(cikis), *map(str, KAP_ARG)],
                       capture_output=True, text=True)
    son = (r.stdout.strip().splitlines() or ['?'])[-1]
    if son != 'PASS':
        raise SystemExit(f'HATA: kapak FAIL {baski}\n{r.stdout}\n{r.stderr}')


def plan_kur():
    """v5 plani (video_cift.py / qc_video78.py plan_kur ile ayni)."""
    v2 = json.load(open(KOK / 'data/pod/video_v5_v2_meta.json'))
    Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
    egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
    n = TUR * len(SIRA) * (SABIT + GECIS); plan, k = [('EJ', 'EJ', 0.0)] * BAS, 0
    while len(plan) < n:
        x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
        plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
    return plan[:n]


def durum(kapak_yolu):
    return np.asarray(Image.open(kapak_yolu).convert('RGB').resize((VW, VH), Image.LANCZOS)).astype(np.float32)


def video(kapaklar, cikis):
    ST = {k: durum(kapaklar[k]) for k in SIRA}
    plan = plan_kur(); n = len(plan)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', f'{VW}x{VH}',
           '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'medium',
           '-crf', '18', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(cikis)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for x, y, w in plan:
        pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
    pr.stdin.close()
    if pr.wait() != 0:
        raise SystemExit('HATA: ffmpeg. DUR.')


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def poster_ncc(kare, baski):
    """kapak_v8_kur.py QC'si videoda: baski (5 mm kirpma) poster boyutuna, 30 px kenar atilir, iki taraf sigma1 Gauss,
    kare icinde en iyi hizada NCC (matchTemplate TM_CCOEFF_NORMED)."""
    bx0, by0, bx1, tb = KAP_ARG
    ph = round((tb - by0) * 1007 / 1053); pw = round(ph * 11 / 14)
    s = VW / round(910 * 4 / 3)
    B = Image.open(baski).convert('RGB')
    kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
    P = np.asarray(B.crop((kx, ky, B.width - kx, B.height - ky)).resize((round(pw * s), round(ph * s)), Image.LANCZOS))
    P = cv2.GaussianBlur(P.astype(np.float32)[30:-30, 30:-30].mean(2), (0, 0), 1.0)
    K = cv2.GaussianBlur(kare.astype(np.float32).mean(2), (0, 0), 1.0)
    return float(cv2.minMaxLoc(cv2.matchTemplate(K, P, cv2.TM_CCOEFF_NORMED))[1])


def onsetler(seri, esik):
    return [i for i in range(1, len(seri)) if seri[i] > esik and seri[i - 1] <= esik]


def qc(cikis, kapaklar, baskilar):
    plan = plan_kur(); n_bek = len(plan)
    v = cv2.VideoCapture(str(cikis))
    w, h = int(v.get(cv2.CAP_PROP_FRAME_WIDTH)), int(v.get(cv2.CAP_PROP_FRAME_HEIGHT)); fps = v.get(cv2.CAP_PROP_FPS)
    ST = {k: durum(kapaklar[k]) for k in SIRA}
    kucuk = lambda X: cv2.resize(X.astype(np.float32).mean(2), (720, 540), interpolation=cv2.INTER_AREA)
    SK = {k: kucuk(ST[k]) for k in SIRA}
    fark = [np.abs(SK[a] - SK[b]) for a, b in (('EJ', 'IN'), ('IN', 'AM'), ('AM', 'EJ'))]
    maske = np.maximum.reduce(fark) > 8                         # varyantlarin farkli oldugu yer (isim + tagline)
    esik = 0.04 * min(float(f[maske].mean()) for f in fark)     # ~ agirlik adimi 0.04
    sabit_i = {}
    for i, (x, y, ww) in enumerate(plan):                        # her varyantin ilk tur sabit bolumunun ortasi
        if x == y and x not in sabit_i and i >= BAS and plan[i - 1][:2] != (x, x):
            sabit_i[x] = i + SABIT // 2
    sabit_i.setdefault('EJ', BAS // 2)
    olc_d, onceki, n, ilk, pncc, in_kare = [], None, 0, None, {}, None
    while True:
        ok, kare = v.read()
        if not ok:
            break
        rgb = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)
        if n == 0:
            ilk = rgb
        for k, i in sabit_i.items():
            if n == i:
                pncc[k] = round(poster_ncc(rgb, baskilar[k]), 4)
                if k == 'IN':
                    in_kare = rgb
        g = kucuk(rgb)
        olc_d.append(0.0 if onceki is None else float(np.abs(g - onceki)[maske].mean()))
        onceki = g; n += 1
    v.release()
    bek_d, onceki = [], None
    for x, y, ww in plan:
        g = SK[x] * (1 - ww) + SK[y] * ww
        bek_d.append(0.0 if onceki is None else float(np.abs(g - onceki)[maske].mean())); onceki = g
    o_olc, o_bek = onsetler(olc_d, esik), onsetler(bek_d, esik)
    gecis_ok = len(o_olc) == len(o_bek) and all(abs(a - b) <= 1 for a, b in zip(o_olc, o_bek))
    ref = np.asarray(Image.open(kapaklar['EJ']).convert('RGB').resize((w, h), Image.LANCZOS)).astype(np.float32).mean(2)
    ncc_ilk = ncc(ilk.astype(np.float32).mean(2), ref)
    mb = os.path.getsize(cikis) / 1e6
    ses = 'Audio:' in subprocess.run(['ffmpeg', '-hide_banner', '-i', str(cikis)], capture_output=True, text=True).stderr
    sure = n / fps
    ok = ((w, h) == (VW, VH) and n == n_bek and round(fps) == FPS and abs(sure - n_bek / FPS) < 0.01 and not ses and mb < 100
          and ncc_ilk >= 0.99 and len(pncc) == 3 and min(pncc.values()) >= 0.99 and gecis_ok)
    olcum = (f'{w}x{h} | {n} kare {sure:.2f} sn | {mb:.1f} MB | ses {"VAR" if ses else "yok"} | ilk kare NCC {ncc_ilk:.4f} | '
             f'poster NCC {pncc} | gecis {len(o_olc)}/{len(o_bek)} ilk {o_olc[:1]} ({o_olc[0] / FPS if o_olc else -1:.2f} sn) '
             f'{"+-1 OK" if gecis_ok else "FARKLI"}')
    return ok, olcum, {'onset_olculen': o_olc, 'onset_plan': o_bek, 'poster_ncc': pncc, 'ilk_kare_ncc': round(ncc_ilk, 4),
                       'kare': n, 'mb': round(mb, 2)}, in_kare


def ciftler_coz(arg):
    if arg != ['HEPSI']:
        return sorted(arg)
    r = rc('lsf', V1_SIP, '--dirs-only')
    return sorted(d.rstrip('/').removesuffix(f'_{RENK}_{BOY}') for d in r.stdout.split() if d.rstrip('/').endswith(f'_{RENK}_{BOY}'))


def cift_uret(c, hedef):
    """tek cift: onceki PASS varsa kopyala; yoksa uret + QC, dosyalari damgaya (PASS ise SON'a da) yaz. -> (ok, satir)"""
    onceki = rc('cat', f'{SON}/QC_{c}.json', kontrol=False)
    if onceki.returncode == 0 and json.loads(onceki.stdout or '{}').get('pass'):
        if all(rc('copyto', f'{SON}/{f}', f'{hedef}/{f}', kontrol=False).returncode == 0
               for f in (f'VIDEO_{c}.mp4', f'IN_{c}.jpg', f'QC_{c}.json')):
            return True, 'atlandi (onceki PASS)'
    cw = W / c; (cw / 'baski').mkdir(parents=True, exist_ok=True)
    kayit = {'cift': c, 'pass': False, 'hat_yama': os.environ.get('HAT_YAMA') == 'true'}
    try:
        baskilar = {k: baski_al(c, *VARYANT[k], v1=(k == 'EJ')) for k in SIRA}
        baskilar['AM'], kayit['am_tagline'] = am_tagline(baskilar, cw / 'BASKI_AM_kaydirilmis.png')
        kapaklar = {k: cw / f'KAP_{k}.jpg' for k in SIRA}
        for k in SIRA:
            kapak(baskilar[k], kapaklar[k])
        cikis = OUT / f'VIDEO_{c}.mp4'
        video(kapaklar, cikis)
        ok, olcum, ayrinti, in_kare = qc(cikis, kapaklar, baskilar)
        tag = kayit['am_tagline']
        kayit.update({'pass': ok, 'qc': ayrinti,
                      'olcum': f'{olcum} | AM tagline fark {tag["fark_px"]} px, kaydirma {tag["kaydirma_px"]} px'
                               + (' | hat yamasi' if kayit['hat_yama'] else '')})
        Image.fromarray(in_kare).resize((720, 540), Image.LANCZOS).save(OUT / f'IN_{c}.jpg', quality=90)
    except (Exception, SystemExit) as e:                        # cift FAIL, parca devam eder
        kayit['olcum'] = f'HATA: {type(e).__name__}: {str(e).strip()[-300:]}'
    (OUT / f'QC_{c}.json').write_text(json.dumps(kayit, indent=1))
    dosyalar = [f for f in (f'VIDEO_{c}.mp4', f'QC_{c}.json', f'IN_{c}.jpg') if (OUT / f).exists()]
    for f in dosyalar:
        rc('copyto', str(OUT / f), f'{hedef}/{f}', kontrol=False)
    if kayit['pass']:                                           # QC en son: yarim kopya PASS sayilmaz
        for f in sorted(dosyalar, key=lambda f: f.startswith('QC_')):
            rc('copyto', str(OUT / f), f'{SON}/{f}', kontrol=False)
    return kayit['pass'], kayit['olcum']


def uret(sb, damga, parca, toplam, arg):
    global SB
    SB = Path(sb); OUT.mkdir(exist_ok=True); W.mkdir(exist_ok=True)
    Image.open(KOK / 'data/pod/kapak_sahne_v9.png').convert('RGB').resize((1213, 910), Image.LANCZOS).save(SAHNE)
    hepsi = ciftler_coz(arg)
    benim = hepsi[parca::toplam]
    hedef = f'{KOK_D}/{damga}'
    N = len(benim); fail = 0; t0 = time.time()
    print(f'parca {parca}/{toplam}: {N} / {len(hepsi)} cift: {" ".join(benim)}', flush=True)
    for i, c in enumerate(benim, 1):
        ok, satir = cift_uret(c, hedef)
        fail += not ok
        g = time.time() - t0
        print(f'[{i}/{N}] {c} {"PASS" if ok else "FAIL"} | {satir} | gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s | %{i / N * 100:.0f}', flush=True)
    print(f'parca {parca}: PASS {N - fail} / {N}')
    return 1 if fail else 0


def birlestir(damga, arg):
    from PIL import ImageDraw
    hepsi = ciftler_coz(arg)
    hedef = f'{KOK_D}/{damga}'
    yer = Path('_birlestir'); yer.mkdir(exist_ok=True)
    rc('copy', hedef, str(yer), '--include', 'QC_*.json', '--include', 'IN_*.jpg', kontrol=False)
    sat, npass, fail = [], 0, []
    TW, TH, SUT = 480, 360, 8
    sat_n = (len(hepsi) + SUT - 1) // SUT
    serit = Image.new('RGB', (SUT * TW, sat_n * (TH + 40)), (255, 255, 255)); d = ImageDraw.Draw(serit)
    for j, c in enumerate(hepsi):
        q = yer / f'QC_{c}.json'
        k = json.loads(q.read_text()) if q.exists() else {'pass': False, 'olcum': 'YOK: uretilmedi (parca dustu?)'}
        npass += bool(k['pass'])
        if not k['pass']:
            fail.append(c)
        sat.append(f'- {c}: {"PASS" if k["pass"] else "FAIL"} | {k.get("olcum", "")}')
        x, y = (j % SUT) * TW, (j // SUT) * (TH + 40)
        if (yer / f'IN_{c}.jpg').exists():
            serit.paste(Image.open(yer / f'IN_{c}.jpg').convert('RGB').resize((TW, TH), Image.LANCZOS), (x, y))
        d.text((x + 8, y + TH + 10), f'{c} {"PASS" if k["pass"] else "FAIL"}', fill=(0, 110, 0) if k['pass'] else (200, 0, 0))
    bas = ['# VIDEO V2 (v5 sablonu) ' + damga, f'Toplam: {len(hepsi)}', '']
    son = ['', f'PASS: {npass} / {len(hepsi)}', f'FAIL: {" ".join(fail) if fail else "-"}',
           'SONUC ' + ('PASS' if not fail else 'FAIL')]
    Path('_out').mkdir(exist_ok=True)
    Path('_out/OZET.md').write_text('\n'.join(bas + sat + son) + '\n')
    serit.save('_out/ONIZLEME.jpg', quality=85)
    for f in ('OZET.md', 'ONIZLEME.jpg'):
        rc('copyto', f'_out/{f}', f'{hedef}/{f}')
    print('\n'.join(son), flush=True)
    return 1 if fail else 0


if __name__ == '__main__':
    if sys.argv[1] == 'uret':
        sys.exit(uret(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6:]))
    if sys.argv[1] == 'birlestir':
        sys.exit(birlestir(sys.argv[2], sys.argv[3:]))
    raise SystemExit(__doc__)
