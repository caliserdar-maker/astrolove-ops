"""DIKIS KAPISI (taslak, uygulanmadi): metin bandinda yatay renk dikisi.
Murekkep ICI (zeminden |L| farki; kenara uzaklik >= max(3, %1.5 x yukseklik) px) satir medyani v(y); trend = v'nin W satirlik medyani;
dikis = max_kanal |v - trend| (RGB; bant uclarindaki W/2 satir haric). Ust hat = bandin ilk %20'si, alt hat = baseline cevresi (son %35 / kuyruk). PASS: dikis <= ESIK."""
import sys, json
import numpy as np, cv2
from PIL import Image
LUMA = np.array([0.299, 0.587, 0.114], np.float32)

def satirlar(rgb):
    a = np.asarray(rgb.convert('RGB')).astype(np.float32); L = a @ LUMA
    z = float(np.median(L)); d = np.abs(L - z)
    m = d > max(40.0, 0.5 * float(np.percentile(d, 99.5)))
    # IC piksel: glif kenarindan >= D px (kabartma golgesi / antialias kenarda; icerde renk yalniz satira bagli)
    rows = np.nonzero(m.sum(1) >= 3)[0]; Hm = (rows[-1] - rows[0] + 1) if len(rows) else 1
    D = max(3.0, 0.015 * Hm)
    c = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) >= D
    n = c.sum(1); ys = np.nonzero(n >= 12)[0]
    # taban (baseline): alt yarida murekkep sayisinin en sert dustugu satir (govdeler biter, kuyruklar kalir)
    mm = m.sum(1).astype(np.float32); y0, y1 = rows[0], rows[-1]; yy = np.arange(len(mm))
    dd = np.diff(mm); alt = (yy[:-1] > y0 + 0.5 * (y1 - y0)) & (yy[:-1] < y1)
    taban = int(np.argmin(np.where(alt, dd, 0))) if alt.any() else int(y1)
    v = np.array([np.median(a[y][c[y]], 0) for y in ys], np.float32)      # satir medyani RGB
    return ys, v, n, taban

def dikis(rgb, w_oran=0.03):
    ys, v, n, taban = satirlar(rgb)
    if len(ys) < 10: return {'hata': 'murekkep yok'}
    H = ys[-1] - ys[0] + 1; W = max(5, 2 * int(round(w_oran * H / 2)) + 1)
    pad = W // 2; vp = np.pad(v, ((pad, pad), (0, 0)), mode='edge')
    tr = np.array([np.median(vp[i:i + W], 0) for i in range(len(v))])
    r = np.abs(v - tr).max(1)                                              # en kotu kanal
    ic = (ys >= ys[0] + pad) & (ys <= ys[-1] - pad)                        # bant uclari (pencere yarisi) disarida
    r = np.where(ic, r, 0.0)
    ust = ys < ys[0] + 0.20 * H
    alt = np.abs(ys - taban) <= 0.12 * H                                   # taban cevresi (alt hat)
    gov = ~ust & ~alt
    i = int(np.argmax(r)); mx = lambda q: round(float(r[q].max()), 1) if q.any() else 0.0
    return {'dikis': round(float(r.max()), 1), 'dikis_ust': mx(ust), 'dikis_alt': mx(alt), 'dikis_govde': mx(gov),
            'en_kotu_satir': int(ys[i]), 'taban': taban, 'pencere': W, 'satir': [int(ys[0]), int(ys[-1])]}

if __name__ == '__main__':
    esik = float(sys.argv[1]); sonuc = {}
    for f in sys.argv[2:]:
        d = dikis(Image.open(f)); d['gecti'] = d.get('dikis', 1e9) <= esik; sonuc[f.split('/')[-1]] = d
        print(f"{'PASS' if d['gecti'] else 'FAIL'} {f.split('/')[-1]} {json.dumps(d)}")
