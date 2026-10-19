#!/usr/bin/env python3
"""Poster video v4 QC (19 Eki): canli kupa ilan videosu (4598525642) ile karsilastirma. Tek script, PASS/FAIL.
1) Kanit: canli dosya ile depodaki adaylarin ciktisi kare kare (ortalama mutlak fark, ayni olcu). Aday: kupa-orchard
   video6b.py (cift.py Cancer Libra Emily James ile yeniden uretilen ORCHARD_Cancer_Libra_video_6sn.mp4). video_kupa.py
   (kupa-printful-sonuc) imzasi: 6,3 sn / 189 kare; canli kare sayisiyla karsilastirilir.
2) Canlidan olculenler: sure, fps, kare, ses; sabit kareler (ilk kareyle fark < 1.5); silinme (0,3 sn) ve olusma egrisi;
   toz yogunlugu ve rengi. Ayni olcum yeni poster videosunda; ikisi ayni tabloda.
   Olcum (iki videoya ayni): olc() aciklamasi.
3) KARSILASTIRMA_KONTAK.jpg: ust satir canli kupa, alt satir poster v4; 0 / 0,5 / 1 / 2 / 3 / 4 / 5 sn / son.
Kapilar: sure / kare / fps canliyla ayni, 1440x1080, ses yok, ilk/son kare ve 150-179 kareler = kapak (4:2:0 tabani + 0.2/0.3),
murekkep olusumu (toz kapali kopyalar, video6b formulu) kupa ile en fazla 0.05 fark, tam olusma karesi +-3; canli = video6b
ciktisi (kare farki ort < 2.0). Tozlu gorunen olusma ve toz yogunlugu tabloda (kupada sembol 2303 px, toz ayni 5200 parcacik:
kucuk sembolu yogun ortuyor, gorunen egri farki bundan).
Kullanim: v4_karsilastir.py <canli.mp4> <poster_v4.mp4> <kapak.jpg> <cikti_dir> <cift.py video/ klasoru> [kupa_tozsuz.mp4 v4_tozsuz.mp4]"""
import json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

CANLI, V4, KAPAK, OUT, KUPA_VD = sys.argv[1:6]      # KUPA_VD: cift.py video/ klasoru (k_mask_nosym.png, k_beyaz.png, mp4)
KUPA_TOZSUZ, V4_TOZSUZ = (sys.argv[6], sys.argv[7]) if len(sys.argv) > 7 else (None, None)   # QC: toz kapali kopyalar
YEN = next((os.path.join(KUPA_VD, f) for f in sorted(os.listdir(KUPA_VD)) if f.endswith('_video_6sn.mp4')), None)
os.makedirs(OUT, exist_ok=True)
SN = [0, 0.5, 1, 2, 3, 4, 5, 'son']
TAB = [0, 0.3, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 'son']


def probe(v):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', v],
                                  capture_output=True, text=True, check=True).stdout)
    vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    return {'olcu': f"{vs['width']}x{vs['height']}", 'kare': int(vs['nb_read_frames']), 'fps': vs['r_frame_rate'],
            'sure_sn': round(float(j['format']['duration']), 3), 'codec': vs['codec_name'], 'pix_fmt': vs.get('pix_fmt'),
            'ses_akisi': any(s['codec_type'] == 'audio' for s in j['streams']), 'boyut_mb': round(os.path.getsize(v) / 1e6, 2),
            'bit_hizi_kbps': round(int(j['format'].get('bit_rate', 0)) / 1000)}


def kareler(v):
    p = probe(v); w, h = map(int, p['olcu'].split('x'))
    d = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(d, np.uint8).reshape(-1, h, w, 3), p


def idx(F, t, fps=30):
    return len(F) - 1 if t == 'son' else min(len(F) - 1, int(round(t * fps)))


def olc(F, SM):
    """Iki videoya ayni olcum. SM = cekirdek sembol pikselleri (kupa: video6b maske('nosym') > 0.95, yeniden uretilen hattin
    k_mask_nosym/k_beyaz katmanindan; poster: poster_video_v4 MS > 0.95). olusma(t) = 1 - ort|f_t - f_son|_SM / ort|f_9 - f_son|_SM
    (0 = silik, 1 = kapak; f_son = son kare = kapak). E = 0,3 sn karesinde ilk kareden farki > 30 olan pikseller (silinen sembol
    ve mesaj); toz(t) = E disinda farki > 20 olan piksel yuzdesi; renk = bu piksellerin ortalamasi.
    Hareketsiz kare = bir onceki kareyle ortalama mutlak fark < 0.15."""
    f0 = F[0].astype(np.int16); fs = F[-1].astype(np.float32)
    fark = lambda f: np.abs(f.astype(np.int16) - f0).max(-1)
    E = fark(F[9]) > 30
    Ed = cv2.dilate(E.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    ref = float(np.abs(F[9].astype(np.float32) - fs)[SM].mean())
    o = {'silinen_piksel': int(E.sum()), 'sembol_piksel': int(SM.sum()), 'hareketsiz_bloklar': []}
    egri, b = [], None
    for i in range(len(F)):
        if i and np.abs(F[i].astype(np.float32) - F[i - 1]).mean() < 0.15:
            if b and i == b[1] + 1:
                b[1] = i
            else:
                b = [i, i]; o['hareketsiz_bloklar'].append(b)
        d = fark(F[i])
        egri.append((round(1 - float(np.abs(F[i].astype(np.float32) - fs)[SM].mean()) / ref, 4), float(((d > 20) & ~Ed).mean())))
    tab = {}
    for t in TAB:
        i = idx(F, t); d = fark(F[i]); tz = (d > 20) & ~Ed
        col = F[i][tz].mean(0).round().astype(int).tolist() if tz.sum() > 50 else None
        tab[str(t)] = {'kare': i, 'olusma': round(egri[i][0], 3), 'toz_yuzde': round(100 * egri[i][1], 3), 'toz_rengi': col}
    o['tablo'] = tab
    o['sembol_tam_kare'] = next((i for i in range(10, len(F)) if all(e[0] >= 0.95 for e in egri[i:])), None)
    o['toz_ilk_kare'] = next((i for i in range(1, len(F)) if egri[i][1] > 0.0002), None)
    o['toz_son_kare'] = max((i for i in range(len(F)) if egri[i][1] > 0.0002), default=None)
    o['silinme_tam_kare'] = next((i for i in range(1, 30) if egri[i][0] < 0.03), None)
    o['toz_yuzde_en_buyuk'] = round(100 * max(e[1] for e in egri), 3)
    return o, egri


R = {}
FC, pc = kareler(CANLI); FV, pv = kareler(V4)
R['canli'] = {'probe': pc}; R['poster_v4'] = {'probe': pv}
# 1) kanit
kanit = {'video_kupa_imzasi': {'beklenen': '6,3 sn / 189 kare', 'canli': f"{pc['sure_sn']} sn / {pc['kare']} kare",
                               'eslesir': pc['kare'] == 189}}
if YEN:
    FY, py = kareler(YEN)
    n = min(len(FY), len(FC))
    if FY.shape[1:] != FC.shape[1:]:
        FY = np.stack([cv2.resize(f, (FC.shape[2], FC.shape[1]), interpolation=cv2.INTER_AREA) for f in FY])
    df = [float(np.abs(FC[i].astype(np.float32) - FY[i]).mean()) for i in range(n)]
    kanit['video6b'] = {'yeniden_uretilen': py, 'kare_farki_ort': round(float(np.mean(df)), 3), 'kare_farki_en_buyuk': round(max(df), 3),
                        'en_buyuk_fark_kare': int(np.argmax(df)), 'kare_sayisi_ayni': len(FY) == len(FC),
                        'karefark_0_5_10_30_60_90_120_150_179': [round(df[i], 3) for i in (0, 5, 10, 30, 60, 90, 120, 150, min(179, n - 1))]}
R['kanit'] = kanit
# 2) olcum
oku = lambda p_: cv2.resize(np.asarray(Image.open(p_).convert('RGB')).astype(np.float32), (FC.shape[2], FC.shape[1]), interpolation=cv2.INTER_AREA)
SMK = np.clip((1 - oku(os.path.join(KUPA_VD, 'k_mask_nosym.png')).mean(-1) / np.maximum(oku(os.path.join(KUPA_VD, 'k_beyaz.png')).mean(-1), 1)) * 1.4, 0, 1) > 0.95   # cekirdek sembol pikselleri (yumusak kenar haric)
SMP = np.asarray(Image.open(V4 + '.sembol_maske.png')) > 127
oc, ec = olc(FC, SMK); ov, ev = olc(FV, SMP)
R['canli'].update(oc); R['poster_v4'].update(ov)
R['ayni_tablo'] = {str(t): {'canli_olusma': oc['tablo'][str(t)]['olusma'], 'v4_olusma': ov['tablo'][str(t)]['olusma'],
                            'canli_toz_yuzde': oc['tablo'][str(t)]['toz_yuzde'], 'v4_toz_yuzde': ov['tablo'][str(t)]['toz_yuzde'],
                            'canli_toz_rengi': oc['tablo'][str(t)]['toz_rengi'], 'v4_toz_rengi': ov['tablo'][str(t)]['toz_rengi']}
                   for t in TAB}
if KUPA_TOZSUZ:   # murekkep olusumu (toz kapali): formul ayni mi
    ok_, _ = olc(kareler(KUPA_TOZSUZ)[0], SMK); ov_, _ = olc(kareler(V4_TOZSUZ)[0], SMP)
    R['murekkep_olusumu_tozsuz'] = {str(t): {'kupa': ok_['tablo'][str(t)]['olusma'], 'v4': ov_['tablo'][str(t)]['olusma']} for t in TAB}
    R['murekkep_olusumu_en_buyuk_fark'] = round(max(abs(v['kupa'] - v['v4']) for v in R['murekkep_olusumu_tozsuz'].values()), 3)
    R['murekkep_tam_kare'] = {'kupa': ok_['sembol_tam_kare'], 'v4': ov_['sembol_tam_kare']}
R['toz_parcacik_basina_sembol_pikseli'] = {'kupa': round(int(SMK.sum()) / 5200, 2), 'v4': round(int(SMP.sum()) / 5200, 2)}
n = min(len(ec), len(ev))
R['olusma_egrisi_en_buyuk_fark'] = round(max(abs(ec[i][0] - ev[i][0]) for i in range(n)), 3)
# ilk/son kare = kapak (4:2:0 tabanina gore)
kap = cv2.resize(np.asarray(Image.open(KAPAK).convert('RGB')), (FV.shape[2], FV.shape[1]), interpolation=cv2.INTER_AREA)
tb = os.path.join(OUT, '_t.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{kap.shape[1]}x{kap.shape[0]}', '-r', '30',
                '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=kap.tobytes(), check=True)
tf = kareler(tb)[0][0]; os.remove(tb)
fk = lambda a, b: round(float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()), 3)
R['poster_v4'].update(ilk_kare_fark=fk(FV[0], kap), son_kare_fark=fk(FV[-1], kap), taban_420=fk(tf, kap))
kapi = {'sure_ayni': abs(pv['sure_sn'] - pc['sure_sn']) < 0.05, 'kare_ayni': pv['kare'] == pc['kare'], 'fps_ayni': pv['fps'] == pc['fps'],
        'olcu_1440x1080': pv['olcu'] == '1440x1080', 'ses_yok': not pv['ses_akisi'],

        'ilk_kare_kapak': R['poster_v4']['ilk_kare_fark'] <= R['poster_v4']['taban_420'] + 0.2,
        'son_kare_kapak': R['poster_v4']['son_kare_fark'] <= R['poster_v4']['taban_420'] + 0.2,
        'son_30_kare_kapak': all(fk(FV[i], kap) <= R['poster_v4']['taban_420'] + 0.3 for i in range(150, len(FV)))}
if KUPA_TOZSUZ:
    kapi['murekkep_olusumu_ayni'] = R['murekkep_olusumu_en_buyuk_fark'] <= 0.05
    kapi['murekkep_tam_kare_ayni'] = None not in R['murekkep_tam_kare'].values() and abs(R['murekkep_tam_kare']['kupa'] - R['murekkep_tam_kare']['v4']) <= 3
if YEN:
    kapi['canli_video6b_ile_ayni'] = kanit['video6b']['kare_sayisi_ayni'] and kanit['video6b']['kare_farki_ort'] < 2.0
R['kapi'] = kapi; R['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL'
json.dump(R, open(os.path.join(OUT, 'QC.json'), 'w'), indent=1, default=str)
# 3) kontak
th, ust, sol = 300, 34, 150
wc, wv = round(FC.shape[2] * th / FC.shape[1]), round(FV.shape[2] * th / FV.shape[1])
tw = max(wc, wv)
K = Image.new('RGB', (sol + len(SN) * (tw + 8), ust + 2 * (th + 8)), (245, 245, 245)); dr = ImageDraw.Draw(K)
try:
    fo = ImageFont.truetype('DejaVuSans-Bold.ttf', 22)
except OSError:
    fo = ImageFont.load_default()
for j, t in enumerate(SN):
    dr.text((sol + j * (tw + 8) + 6, 6), f'{t} sn' if t != 'son' else 'son kare', fill=(0, 0, 0), font=fo)
for r_, (ad, F, w_) in enumerate((('CANLI KUPA', FC, wc), ('POSTER v4', FV, wv))):
    y = ust + r_ * (th + 8); dr.text((8, y + th // 2 - 12), ad, fill=(0, 0, 0), font=fo)
    for j, t in enumerate(SN):
        K.paste(Image.fromarray(F[idx(F, t)]).resize((w_, th), Image.LANCZOS), (sol + j * (tw + 8) + (tw - w_) // 2, y))
K.save(os.path.join(OUT, 'KARSILASTIRMA_KONTAK.jpg'), quality=92)
print(json.dumps({k: R[k] for k in ('kanit', 'kapi', 'sonuc', 'olusma_egrisi_en_buyuk_fark')}, default=str))
for t, v in R['ayni_tablo'].items():
    print('TABLO', t, v)
print('CANLI', {k: oc[k] for k in ('hareketsiz_bloklar', 'silinme_tam_kare', 'toz_ilk_kare', 'toz_son_kare', 'sembol_tam_kare')})
print('V4', {k: ov[k] for k in ('hareketsiz_bloklar', 'silinme_tam_kare', 'toz_ilk_kare', 'toz_son_kare', 'sembol_tam_kare')})
print('SONUC', R['sonuc'])
sys.exit(0 if R['sonuc'] == 'PASS' else 1)
