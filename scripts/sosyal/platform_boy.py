"""Platform boylari + mobil onizleme benzetimi + okunurluk kapisi (Serdar 25 Kas karari, Merkez aktarimi).
Girdi: ayni ciftin 2:3 pinleri (1000x1500: poster, kart, altin) ve 9:16 videosu (1080x1920).
Cikti:
  - 4:5 gonderi (Instagram / Facebook / Threads) 1080x1350: pin uc banda bolunur; ust bant (0-257: baslik + alt baslik) ve alt bant
    (1330-1500: "Add your names") 1.08 olcekle AYNEN, orta bant (gorsel) kalan yukseklige kuculur ve ortalanir. Ust/alt satir kirpilmaz.
  - Onizleme paftasi: Pinterest akis (2 sutun), IG akis 4:5, IG profil izgarasi (3:4 kirpma), FB akis, Reels/Shorts arayuz katmani.
Kapi (PASS/FAIL), olculen murekkep kutularindan:
  - ust (baslik) ve alt ("Add your names") satir: her gorunumde gorunur alanin icinde (kirpma / arayuz disi) ve
    yazi boyu >= 11 CSS pt (buyuk harf yuksekligi / 0.69; 0.69 = Pagella buyuk harf / punto, olcum). 11 pt: iOS en kucuk metin
    stillerinden Caption 2 (Apple HIG, 3. taraf ozetlerinde; dogrulanmadi) yerine onceki kapimiz (168 px akista 11 CSS px).
  - video: altin/acik yazi murekkebi ust %14 ve alt %20 arayuz alanina girmez (Merkez karari). Bilgi: Google'in resmi dikey
    REKLAM guvenli alan sablonu ust %15 (288 px), alt %35 (672 px), sag 192 px (support.google.com / services.google.com
    universalsafezones-youtube.pdf); organik Reels/Shorts icin resmi piksel degeri bulunamadi. Bilgi olarak %35 alt ve sag sutun
    (x > 888) cakismasi da olculur.
Kullanim: python3 platform_boy.py --poster P.jpg --kart K.jpg --altin A.jpg --video V.mp4 --out DIR [--slug cancer-and-leo] [--oz-test]
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (244, 239, 233)
W45, H45 = 1080, 1350
UST, ALT = 257, 1330                 # 2:3 pin bantlari (v6 olcum: alt baslik y172-244, poster+golge y258-1323, alt satir y1377-1463)
OL = W45 / 1000                      # 1.08
CAP_PT = 0.69                        # Pagella buyuk harf yuksekligi / punto (olcum: 104.5 px -> 76 px ~ 0.727; italik 'A' ~0.69; alt sinir)
MIN_PT = 11.0
TEL_PT = 390                         # telefon genisligi (pt): iPhone 12-15 (390 pt, Apple belge degerleri; 3. taraf ozet)
PIN_SUTUN_PT = (TEL_PT - 3 * 8) / 2  # Pinterest akis: 2 sutun, 8 pt bosluk (tahmin, ekran goruntusu olcumu yok)
IZGARA_PT = (TEL_PT - 2) / 3         # IG profil izgarasi: 3 sutun, 1 pt cizgi
UI_UST, UI_ALT = 0.14, 0.20          # Merkez karari (Reels/Shorts)
RESMI_ALT, RESMI_SAG = 0.35, 888     # Google dikey reklam sablonu (bilgi)


def dorde_bes(pin):
    im = Image.open(pin).convert('RGB')
    if im.size != (1000, 1500):
        raise SystemExit(f'DUR: pin boyu {im.size}')
    ust = im.crop((0, 0, 1000, UST)).resize((W45, round(UST * OL)), Image.LANCZOS)
    alt = im.crop((0, ALT, 1000, 1500)).resize((W45, round((1500 - ALT) * OL)), Image.LANCZOS)
    kalan = H45 - ust.size[1] - alt.size[1]
    orta = im.crop((0, UST, 1000, ALT))
    k = kalan / orta.size[1]
    orta = orta.resize((round(1000 * k), kalan), Image.LANCZOS)
    out = Image.new('RGB', (W45, H45), BG)
    out.paste(ust, (0, 0)); out.paste(orta, ((W45 - orta.size[0]) // 2, ust.size[1])); out.paste(alt, (0, H45 - alt.size[1]))
    return out, {'orta_olcek': round(k * 1.0, 4), 'ust_h': ust.size[1], 'alt_y': H45 - alt.size[1]}


def murekkep(a, y0, y1, esik=60):
    """krem zemin uzerindeki koyu yazi (lacivert baslik / alt satir) kutusu."""
    d = np.abs(a[y0:y1].astype(int) - np.array(BG)).sum(2) > esik
    ys, xs = np.where(d)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min() + y0), int(xs.max()), int(ys.max() + y0)]


def satirlar(a, ust_h, alt_y):
    """baslik: ust bant icindeki ilk yazi satiri; alt satir: alt bant icindeki yazi. Buyuk harf yuksekligi icin 'baslik' satirinin
    ust-alt murekkebi (alt uzanti yoksa) kullanilir; olcum muhafazakar: alt uzantili harf satiri buyutur, bu yuzden ayrica
    satir profili ile ana govde yuksekligi (en yogun ardisik satirlar) alinir."""
    H = a.shape[0]
    d = np.abs(a.astype(int) - np.array(BG)).sum(2) > 60
    def govde(y0, y1):
        r = d[y0:y1].sum(1); on = np.where(r > 0)[0]
        if len(on) == 0:
            return None
        # ardisik bloklar; ilk blok = satir
        bl = []; s = on[0]; p = on[0]
        for y in on[1:]:
            if y != p + 1:
                bl.append((s, p)); s = y
            p = y
        bl.append((s, p))
        return [(b0 + y0, b1 + y0) for b0, b1 in bl]
    s_ = ust_h / UST                       # 2:3 -> 1.0, 4:5 -> 1.08
    ub = govde(round(30 * s_), round(153 * s_)); ab = govde(alt_y, H)   # baslik penceresi y30-153 (v6; alt baslik 172-244 disarida)
    out = {}
    if ub:
        y0, y1 = ub[0]; xs = np.where(d[y0:y1 + 1].any(0))[0]
        out['baslik'] = [int(xs.min()), int(y0), int(xs.max()), int(y1)]
    if ab:
        y0, y1 = ab[0]; xs = np.where(d[y0:y1 + 1].any(0))[0]
        out['alt_satir'] = [int(xs.min()), int(y0), int(xs.max()), int(y1)]
    return out


def pt(px_h, img_w, gorunum_pt):
    """murekkep yuksekligi (px) -> punto (pt) bu gorunumde."""
    return px_h / CAP_PT * gorunum_pt / img_w


def kontrol_gorsel(ad, a, ust_h, alt_y, S, gorunumler):
    """gorunumler: [(gorunum adi, genislik_pt, kirpma (x0, y0, x1, y1) goruntu px)]"""
    st = satirlar(a, ust_h, alt_y)
    for s in ('baslik', 'alt_satir'):
        if s not in st:
            S.append((f'{ad} {s} bulundu', False, 'yok')); continue
        x0, y0, x1, y1 = st[s]
        # buyuk harf yuksekligi ~ satir yuksekligi (baslik buyuk harf; alt satir italik 'A' + alt uzanti 'y': muhafazakar olarak x0.7)
        h = (y1 - y0 + 1) * (1.0 if s == 'baslik' else 0.7)
        for g, wpt, (cx0, cy0, cx1, cy1) in gorunumler:
            icinde = x0 >= cx0 + 4 and x1 <= cx1 - 4 and y0 >= cy0 + 4 and y1 <= cy1 - 4
            S.append((f'{ad} | {g} | {s} tam gorunur', icinde, f'kutu {st[s]} gorunur {[cx0, cy0, cx1, cy1]}'))
            p = pt(h, cx1 - cx0, wpt)
            S.append((f'{ad} | {g} | {s} >= {MIN_PT} pt', p >= MIN_PT, round(p, 1)))
    return st


def kareler(video, adim=0.25):
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', video],
                                   capture_output=True, text=True, check=True).stdout)
    W = pr['streams'][0]['width']; H = pr['streams'][0]['height']; dur = float(pr['format']['duration'])
    w2, h2 = W // 2, H // 2                 # yari cozunurluk (hiz; 1 px yazi cizgisi 2 px'te korunur)
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vf', f'fps={1 / adim},scale={w2}:{h2}:flags=area', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    n = len(r.stdout) // (w2 * h2 * 3)
    return np.frombuffer(r.stdout[:n * w2 * h2 * 3], np.uint8).reshape(n, h2, w2, 3), W, H, dur


def yazi_maske(f):
    """koyu zemin uzerindeki altin yazi/sembol: altin piksel (R > 120, R - B > 95; altin yazi p50 136) VE 7 px icinde koyu piksel
    (toplam < 90). Duvar sahnesindeki ahsap raf altin renge yakin (R - B 70-100+) ama yaninda koyu zemin yok (olcum 25 Kas)."""
    from PIL import ImageFilter
    f = f.astype(int)
    altin = (f[..., 0] > 120) & (f[..., 0] - f[..., 2] > 95)
    koyu = Image.fromarray(((f.sum(2) < 90) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))   # yari cozunurlukte ~7 px
    return altin & (np.asarray(koyu) > 0)


def kontrol_video(video, S):
    K, W, H, dur = kareler(video)
    bilgi = {'kare': len(K), 'boy': [W, H], 'sure': dur}
    S.append(('video 1080x1920', (W, H) == (1080, 1920), [W, H]))
    h2, w2 = K.shape[1:3]
    ust = int(h2 * UI_UST); alt = int(h2 * (1 - UI_ALT)); r_alt = int(h2 * (1 - RESMI_ALT)); sag = RESMI_SAG * w2 // W
    ihlal = []; bilgi_alt35 = []; bilgi_sag = []
    for i, f in enumerate(K):
        m = yazi_maske(f)
        if m[:ust].sum() > 8 or m[alt:].sum() > 8:
            ihlal.append(round(i * 0.25, 2))
        if m[r_alt:alt].sum() > 8:
            bilgi_alt35.append(round(i * 0.25, 2))
        if m[ust:alt, sag:].sum() > 8:
            bilgi_sag.append(round(i * 0.25, 2))
    S.append((f'video: yazi/sembol ust %{int(UI_UST * 100)} ve alt %{int(UI_ALT * 100)} arayuz alaninda yok (0.25 sn adim)', not ihlal,
              f'ihlal kareleri {ihlal[:12]}'))
    bilgi['bilgi_resmi_reklam_alt35_cakisma_sn'] = bilgi_alt35
    bilgi['bilgi_resmi_reklam_sag_sutun_cakisma_sn'] = bilgi_sag
    return K, bilgi


def telefon(icerik, bas, ui=None):
    """1170 px genis (390 pt @3x) telefon cercevesi + baslik cubugu."""
    w = 1170; h = 2532
    c = Image.new('RGB', (w + 60, h + 110), (30, 30, 30))
    ekran = Image.new('RGB', (w, h), (255, 255, 255))
    ekran.paste(icerik, (0, 0))
    c.paste(ekran, (30, 30))
    d = ImageDraw.Draw(c)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
    except OSError:
        f = ImageFont.load_default()
    d.text((40, h + 45), bas, fill=(255, 255, 255), font=f)
    return c


def pafta(pinler45, pinler23, K, out, slug):
    S3 = 3
    sayfa = []
    # 1) Pinterest akis: 2 sutun, sutun 183 pt = 549 px @3x
    ekr = Image.new('RGB', (1170, 2532), (255, 255, 255)); col = round(PIN_SUTUN_PT * S3); x = [24, 24 + col + 24]
    yy = [140, 140]
    for i, p in enumerate(pinler23 + pinler23[:1]):
        im = Image.open(p).convert('RGB').resize((col, round(col * 1.5)), Image.LANCZOS); j = i % 2
        ekr.paste(im, (x[j], yy[j])); yy[j] += im.size[1] + 90
    sayfa.append(telefon(ekr, 'Pinterest akis (2 sutun, 183 pt)'))
    # 2) IG akis 4:5 ve 4) FB akis: tam genislik
    for ad_, ust_bar in (('Instagram akis 4:5', 160), ('Facebook akis 4:5', 220)):
        ekr = Image.new('RGB', (1170, 2532), (255, 255, 255)); d = ImageDraw.Draw(ekr)
        d.rectangle((0, 0, 1170, ust_bar - 10), fill=(250, 250, 250))
        im = Image.open(pinler45[0]).convert('RGB').resize((1170, round(1170 * 1.25)), Image.LANCZOS)
        ekr.paste(im, (0, ust_bar)); sayfa.append(telefon(ekr, ad_ + ' (390 pt)'))
    # 3) IG profil izgarasi 3:4 kirpma
    ekr = Image.new('RGB', (1170, 2532), (255, 255, 255)); tw = round(IZGARA_PT * S3); th = round(tw * 4 / 3)
    for i, p in enumerate((pinler45 * 3)[:9]):
        im = Image.open(p).convert('RGB'); cw = round(im.size[1] * 3 / 4); x0 = (im.size[0] - cw) // 2
        im = im.crop((x0, 0, x0 + cw, im.size[1])).resize((tw, th), Image.LANCZOS)
        ekr.paste(im, ((i % 3) * (tw + 3), 600 + (i // 3) * (th + 3)))
    sayfa.append(telefon(ekr, 'Instagram profil izgarasi (3:4 kirpma)'))
    # 5) Reels/Shorts: kapak karesi, orta kare, son kart + arayuz alanlari
    for t_ in (0, len(K) // 2, len(K) - 6):
        f = Image.fromarray(K[t_]).resize((1170, 2080), Image.LANCZOS)   # onizleme yari cozunurluk kareden
        ekr = Image.new('RGB', (1170, 2532), (0, 0, 0)); ekr.paste(f, (0, 226))
        ov = Image.new('RGBA', ekr.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        d.rectangle((0, 226, 1170, 226 + int(2080 * UI_UST)), fill=(255, 0, 0, 70))
        d.rectangle((0, 226 + int(2080 * (1 - UI_ALT)), 1170, 226 + 2080), fill=(255, 0, 0, 70))
        d.rectangle((round(RESMI_SAG / 1080 * 1170), 226 + int(2080 * UI_UST), 1170, 226 + int(2080 * (1 - UI_ALT))), outline=(255, 200, 0, 160), width=4)
        ekr = Image.alpha_composite(ekr.convert('RGBA'), ov).convert('RGB')
        sayfa.append(telefon(ekr, f'Reels/Shorts kare {t_ * 0.25:.2f} sn (kirmizi: arayuz, sari: resmi rekl. sag sutun)'))
    w = sayfa[0].size[0]; h = sayfa[0].size[1]
    P = Image.new('RGB', (4 * (w + 40) + 40, 2 * (h + 40) + 40), (255, 255, 255))
    for i, s in enumerate(sayfa[:8]):
        P.paste(s, (40 + (i % 4) * (w + 40), 40 + (i // 4) * (h + 40)))
    P = P.resize((P.size[0] // 2, P.size[1] // 2), Image.LANCZOS)
    yol = os.path.join(out, f'ONIZLEME_PAFTA_{slug}.jpg'); P.save(yol, quality=88)
    return yol


def calis(g):
    os.makedirs(g.out, exist_ok=True)
    S = []; bilgi = {}
    p45 = []
    for tur, p in (('poster', g.poster), ('kart', g.kart), ('altin', g.altin)):
        im, b = dorde_bes(p); y = os.path.join(g.out, f'{g.slug}-{tur}-4x5.jpg'); im.save(y, quality=95); p45.append(y); bilgi[tur] = b
        a23 = np.asarray(Image.open(p).convert('RGB')); a45 = np.asarray(Image.open(y).convert('RGB'))
        kontrol_gorsel(f'{tur} 2:3', a23, UST, ALT, S, [('Pinterest akis', PIN_SUTUN_PT, (0, 0, 1000, 1500))])
        cw = round(H45 * 3 / 4); x0 = (W45 - cw) // 2
        kontrol_gorsel(f'{tur} 4:5', a45, b['ust_h'], b['alt_y'], S,
                       [('IG akis', TEL_PT, (0, 0, W45, H45)), ('FB akis', TEL_PT, (0, 0, W45, H45)),
                        ('IG profil izgarasi 3:4', IZGARA_PT, (x0, 0, x0 + cw, H45))])
    K = None
    if g.video:
        K, bv = kontrol_video(g.video, S); bilgi['video'] = bv
    yol = pafta(p45, [g.poster, g.kart, g.altin], K, g.out, g.slug) if K is not None else None
    ok = all(s[1] for s in S)
    json.dump({'sonuc': 'PASS' if ok else 'FAIL', 'bilgi': bilgi, 'kapilar': [[s[0], s[1], str(s[2])] for s in S], 'pafta': yol},
              open(os.path.join(g.out, f'QC_PLATFORM_{g.slug}.json'), 'w'), ensure_ascii=False, indent=1)
    return ok, S


def main():
    ap = argparse.ArgumentParser()
    for x in ('poster', 'kart', 'altin', 'out'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--video'); ap.add_argument('--slug', default='cift'); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    if g.oz_test:
        import tempfile, copy
        R = []
        with tempfile.TemporaryDirectory() as t:
            g1 = copy.copy(g); g1.out = os.path.join(t, 'a'); ok, _ = calis(g1)
            R.append(('bilinen PASS (verilen pinler)', ok))
            # FAIL 1: baslik kirpilmis 4:5 (ust bant tasiyor): pin ustune 40 px koyu bant -> IG izgara/akis gorunur alan disi degil ama
            # baslik satiri yok -> FAIL; FAIL 2: alt satir cok kucuk (pin alt bandi 0.3 olcekle yeniden)
            im = Image.open(g.poster).convert('RGB'); d = ImageDraw.Draw(im); d.rectangle((0, 30, 1000, 152), fill=BG)
            im.save(os.path.join(t, 'f1.jpg'), quality=95)
            g2 = copy.copy(g); g2.poster = os.path.join(t, 'f1.jpg'); g2.out = os.path.join(t, 'b'); g2.video = None
            ok2, S2 = calis(g2); R.append(('FAIL: baslik yok', not ok2))
            im = Image.open(g.poster).convert('RGB'); alt = im.crop((0, ALT, 1000, 1500))
            k = alt.resize((300, 51), Image.LANCZOS); im.paste(Image.new('RGB', (1000, 170), BG), (0, ALT)); im.paste(k, (350, ALT + 60))
            im.save(os.path.join(t, 'f2.jpg'), quality=95)
            g3 = copy.copy(g); g3.poster = os.path.join(t, 'f2.jpg'); g3.out = os.path.join(t, 'c'); g3.video = None
            ok3, S3 = calis(g3); R.append(('FAIL: alt satir kucuk', not ok3 and any((not s[1]) and 'alt_satir >=' in s[0] for s in S3)))
            im = Image.open(g.poster).convert('RGB'); im2 = Image.new('RGB', (1000, 1500), BG); im2.paste(im.crop((0, 0, 1000, 1500)), (0, 0))
            d = ImageDraw.Draw(im2); d.rectangle((0, 0, 1000, 152), fill=BG); f = ImageFont.truetype('/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-regular.otf', 104)
            d.text((-60, 40), 'CANCER & LEO AND MORE', font=f, fill=(22, 38, 65)); im2.save(os.path.join(t, 'f3.jpg'), quality=95)
            g4 = copy.copy(g); g4.poster = os.path.join(t, 'f3.jpg'); g4.out = os.path.join(t, 'd'); g4.video = None
            ok4, S4 = calis(g4); R.append(('FAIL: baslik kenardan tasiyor (kirpilir)', not ok4 and any((not s[1]) and 'tam gorunur' in s[0] for s in S4)))
            if g.video:
                # FAIL 4: videoya alt %20 alanina altin yazi
                v2 = os.path.join(t, 'v2.mp4')
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', g.video, '-t', '2', '-vf', 'drawbox=x=300:y=1700:w=400:h=80:color=0xE0B040:t=fill',
                                '-an', v2], check=True)
                S5 = []; kontrol_video(v2, S5); R.append(('FAIL: video alt arayuz alaninda yazi', not all(s[1] for s in S5)))
        for ad_, v in R:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad_)
        sys.exit(0 if all(v for _, v in R) else 1)
    ok, S = calis(g)
    for s in S:
        print(('PASS' if s[1] else 'FAIL') + f' {s[0]} | {s[2]}')
    print('SONUC', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
