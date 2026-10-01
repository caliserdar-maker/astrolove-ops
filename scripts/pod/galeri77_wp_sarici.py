#!/usr/bin/env python3
"""WP siparisi (siparis_dosyasi.py, kilitli kod) icin ayni argumanlarla calistirici; piksel degistirmez.
wp_ornek.cift_boy donusundeki QC ayrintisini (f_kabartma, g_kontrast, a-e, hedef gecmisi) <cik>/WP_QC_AYRINTI.json'a
yazar (KAPI_RAPORU yalniz true/false tasiyor; WP_TANI icin ayrinti gerekli). cwd = WP dali kok dizini.

wp_pod_kod=v1 (siparis-dijital 36cb82d ile ayni yontem): cwd = siparis-baski-v1 + kilitli WP dosyalari. v1'in
siparis_dosyasi'nda wp_bakir_uret yok -> asagidaki kopya (wp-katman 8569cce wp_bakir_uret'in AYNISI, dikis kapisi
dahil) WARM_PARCHMENT POD siparisine baglanir; duz renk (CI/MB) baskisi v1 pod_uret ile (olcek ikinci denemesi)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'scripts' / 'medya_v1'))
sys.argv[0] = str(Path.cwd() / 'scripts' / 'medya_v1' / 'siparis_dosyasi.py')
import siparis_dosyasi as sd  # noqa: E402
import wp_ornek as wo  # noqa: E402

_cift_boy = wo.cift_boy


def cift_boy(*a, **k):
    R, WP = _cift_boy(*a, **k)
    cik = Path(a[5] if len(a) > 5 else k['cik'])
    try:
        d = {x: v for x, v in R.items() if not x.startswith('_')}
        (cik / 'WP_QC_AYRINTI.json').write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str))
    except Exception as e:  # noqa: BLE001  (ayrinti yazilamazsa uretim etkilenmez)
        print('WP_QC_AYRINTI yazilamadi:', type(e).__name__, e, flush=True)
    return R, WP


wo.cift_boy = cift_boy

if not hasattr(sd, 'wp_bakir_uret'):
    WP_KAPILAR = ('a_renk', 'b_tasma', 'c_iz', 'e_kagit', 'f_kabartma', 'g_kontrast')

    def wp_bakir_uret(sip, P_blue, P_ed, cik):
        R, WP = wo.cift_boy(sip['cift'], sip['boy'], P_ed, P_blue, {sip['cift']: sip['sayfa']}, cik,
                            isim=(sip['isim1'], sip['isim2']), mesaj=sip.get('mesaj') or '', siparis=True)
        ozet = {a: R.get(a) for a in ('durum', 'duz_renk', 'plate_gecti', 'zemin_birebir', 'eski_iz', 'serdar_dikis')}
        if WP is None:
            return {**sip, 'durum': R.get('durum'), 'wp_bakir': ozet, 'kapilar_gecti': False}
        ad = f'BASKI_{sip["boy"]}.jpg'
        wo.kaydet_jpg(WP, cik / ad, 95)
        q = R['qc']
        bpx = [int(WP.shape[1]), int(WP.shape[0])]
        kapilar = {'duz_renk_siparis': bool(R['siparis_duz_renk_kapilar'].get('kapilar_gecti')),
                   **{a: bool(q[a]['gecti']) for a in WP_KAPILAR},
                   'plate': bool(R['plate_gecti']), 'zemin_birebir': bool(R['zemin_birebir']['gecti']),
                   'eski_iz': bool(R['eski_iz']['gecti']), 'boy': bpx == list(sip['hedef_px'])}
        import wp_dikis_kapisi as dk
        dikis = dk.siparis_kapisi(WP, sip['cift'], sip['boy'], R.get('bantlar'))
        kapilar['dikis'] = bool(dikis['gecti'])
        return {**sip, 'durum': 'URETILDI', 'yontem': 'WP_BAKIR', 'baski_px': bpx,
                'dosya_MB': round((cik / ad).stat().st_size / 1e6, 2), 'kapilar': kapilar,
                'kapilar_gecti': all(kapilar.values()), 'dikis_kapisi': dikis, 'bilgi_d_dikis': q['d_dikis'],
                'wp_bakir': ozet}

    _pod_uret = sd.pod_uret

    def pod_uret(sip, kaynak_bayt, P_blue, P_ed, cik):
        if sip.get('renk') == 'WARM_PARCHMENT' and sip.get('urun') == 'POD':
            return wp_bakir_uret(sip, P_blue, P_ed, cik)
        return _pod_uret(sip, kaynak_bayt, P_blue, P_ed, cik)       # duz renk (wp_ornek.baski) ve diger renkler

    sd.wp_bakir_uret = wp_bakir_uret
    sd.pod_uret = pod_uret
    print('WP_POD_KOD v1: siparis-baski-v1 pod_uret + kilitli WP dosyalari', flush=True)
sd.main()
