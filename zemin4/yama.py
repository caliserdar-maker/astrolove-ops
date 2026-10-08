# Zemin deneme 4 (8 Eki 2026, Serdar onayi): motor_gpt/uret_tam.py'nin YAMALI kopyasi. siparis-gpt koduna dokunmaz.
# Ayni kosuda iki zemin: REFERANS (mevcut ayar, birebir) + YENI (isima 0, golge/temas ofseti olculen isik yonunun tersine).
# Oge renkleri (yansima, oge yuzeyine dusen isima dahil) referanstaki gibi; yeni zemin farki yalniz oge GECIRGENLIGI (1-A) kadar
# eklenir
# -> oge ici ve kenar keskinligi referansla ayni.
# Ortam: Z4_GOLGE="dx,dy,tdx,tdy" (golge ve temas ofseti), Z4_CIKTI=yeni SV png, Z4_TABAN=golgesiz/ogesiz zemin png (olcum).
# Z4_GOLGE yoksa yamali dosya referansla ayni yolu calistirir (yerelde bit bit dogrulanir).
# Kullanim: python yama.py KAYNAK_uret_tam.py HEDEF_uret_tam.py
import sys
src = open(sys.argv[1]).read()

def degistir(eski, yeni):
    global src
    assert src.count(eski) == 1, f'yama capasi {src.count(eski)} kez: {eski[:60]!r}'
    src = src.replace(eski, yeni)

degistir("zemin *= (1 - g[..., None]); del g\n", """DZ = None
if os.environ.get('Z4_GOLGE'):                                       # zemin-4: yeni golge (ayni sigma/opaklik, yeni yon)
    dx4, dy4, tdx4, tdy4 = [float(v) for v in os.environ['Z4_GOLGE'].split(',')]
    g4 = cv2.warpAffine(cv2.GaussianBlur(Atum, (0, 0), P['golge_sigma']), np.float32([[1, 0, dx4], [0, 1, dy4]]), (W, H)) * P['golge_opak']
    if P['temas']:
        gt = cv2.warpAffine(cv2.GaussianBlur(Atum, (0, 0), 4.0), np.float32([[1, 0, tdx4], [0, 1, tdy4]]), (W, H)) * P['temas']
        g4 = 1 - (1 - g4) * (1 - gt); del gt
    DZ = np.empty((H, W, 3), np.float16)                             # yeni - referans zemin farki (lineer)
    TR = np.ones((H, W), np.float16)                                 # oge gecirgenligi (1-A carpimi): isima yalniz zeminden silinir
    for y0_ in range(0, H, 600):
        DZ[y0_:y0_ + 600] = zemin[y0_:y0_ + 600] * (g[y0_:y0_ + 600] - g4[y0_:y0_ + 600])[..., None]
    del g4
    if os.environ.get('Z4_TABAN'):                                   # golgesiz, ogesiz zemin (sRGB 8 bit): parlama olcumu tabani
        tb = np.empty((H, W, 3), np.uint8)
        for y0_ in range(0, H, 600):
            tb[y0_:y0_ + 600] = np.clip(np.round(srgb(zemin[y0_:y0_ + 600]) * 255), 0, 255).astype(np.uint8)
        Image.fromarray(tb).save(os.environ['Z4_TABAN'], compress_level=1); del tb
    log('Z4 golge', os.environ['Z4_GOLGE'])
zemin *= (1 - g[..., None]); del g
""")
degistir("    sl[:] = sl * (1 - A[..., None]) + rgb * A[..., None]\n", """    sl[:] = sl * (1 - A[..., None]) + rgb * A[..., None]
    if DZ is not None:                                              # zemin farki oge arkasinda gecirgenlik kadar kalir
        dz_ = DZ[y:y + A.shape[0], x:x + A.shape[1]]; dz_[:] = dz_ * (1 - A[..., None])
        tr_ = TR[y:y + A.shape[0], x:x + A.shape[1]]; tr_[:] = tr_ * (1 - A)
""")
degistir("        zemin[y0_:y1_] += bl[y0_ - a0 * 4:y1_ - a0 * 4] * P['isima']\n", """        zemin[y0_:y1_] += bl[y0_ - a0 * 4:y1_ - a0 * 4] * P['isima']
        if DZ is not None:                                          # yeni: zeminde isima 0 (oge yuzeyindeki referansla ayni kalir)
            DZ[y0_:y1_] -= bl[y0_ - a0 * 4:y1_ - a0 * 4] * P['isima'] * TR[y0_:y1_, :, None]
""")
degistir("del zemin\nim = Image.fromarray(out)\n", "if DZ is None: del zemin\nim = Image.fromarray(out)\n")
degistir("log('kaydedildi')\n", """log('kaydedildi')
if DZ is not None:                                                   # yeni zemin: ayni titresim/gren tohumu (oge ici ayni kalir)
    assert not P['renk_ayar'] and not P['kararma']
    del out, im
    rs = np.random.default_rng(11)
    out = np.empty((H, W, 3), np.uint8)
    for y0 in range(0, H, 600):
        zb = zemin[y0:y0 + 600] + DZ[y0:y0 + 600]
        b = srgb(zb) * 255
        b += rs.random(b.shape, np.float32) - rs.random(b.shape, np.float32)
        if P['gren']:
            gn = cv2.GaussianBlur(rs.standard_normal(b.shape[:2]).astype(np.float32), (0, 0), 0.8)
            b += (gn / 0.35 * P['gren'])[..., None]
        out[y0:y0 + 600] = np.clip(np.round(b), 0, 255).astype(np.uint8)
    del zemin, DZ, TR
    Image.fromarray(out).save(os.environ['Z4_CIKTI'], optimize=False, compress_level=3)
    log('Z4 yeni zemin kaydedildi')
""")
open(sys.argv[2], 'w').write(src)
print('yama tamam')
