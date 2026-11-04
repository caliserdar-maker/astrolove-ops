#!/usr/bin/env python3
"""Sikilastirma dogrulama kosusu (Serdar 4 Kas, O2 / O3 / O4 + O1 tamamlama): BEKLENEN_SONUC.json. Her beklenti PASS/FAIL, kaynagi yazili.
Beklentiler:
  cl_kontrol            CANCER_LIBRA onayli 5 stile <= 1 seviye / 10 px (OLCUM kontrol_pass)
  kova_onayli_kiyas     AQUARIUS_PISCES RUBY / SAPPHIRE / EMERALD onayli Kova kosusu (41817771849) dosyalarina ayni tolerans (OLCUM onayli_kiyas)
  o2_sha_esit_<CIFT>    SADE_ALTIN sha256 == ayni ciftin SADE_1_ALTIN_TONU sha256 (FILDISI girdisi ayni dosya) [AQUARIUS_PISCES, GEMINI_VIRGO]
  o2_kati_aqu           AQUARIUS_PISCES SADE kati (ham) 2 haneye yuvarlaninca 1,35 (1f24d49 OLCUM koyulasma_oncesi_kati)
  o2_bilinen_fail       AQUARIUS_PISCES SADE_ALTIN sha256 != eski koyulastirilmis b8dba3d7... (1f24d49 OLCUM png_sha256)
  o2_cl_zayif           bilgi: CANCER_LIBRA SADE kiyasi O2 icin zayif test (CL'de carpan 1,0; eski SADE_KOYU = SADE_1)
  kapi_onarimsiz_iddia  KOVA_KAPI_TESTI gercek aquarius mod_kapali.onarimsiz_kapi_iddia gecti (olculen > 0)
  kova_onarimsiz_neden  AQUARIUS_PISCES onarimsiz motor cikis 1 ve nedeni leke_a_kaynak_0 (OLCUM kenar_onarimsiz_neden)
  gv_varsayilan         GEMINI_VIRGO varsayilan sinir (2) ile tum sert kapilar gecti (beklenti 2202 olcumunden: 2 px, gecer; dogrulanmadi)
  gv_sinir1             GV sinir 1 adimi: ornek78 cikis 1, GV tek sert FAIL koyu_kucultme_le_sinir, 5 stil 954 PNG ve gercek boy var
  genel_cikis           ana ornek78 cikis 0
  listeler              OLCUM dusuk_kontrast, kucultme, kenar_onarim_uyari var
  gercek_boy            GERCEK_BOY_KONTROL tum dosyalar PASS
Cikis: 0 tum beklentiler PASS, 1 en az biri FAIL, 2 cokus."""
import argparse
import json
import sys
from pathlib import Path

ESKI_SADE_AQU = 'b8dba3d7259fa00330101590513389eb09eb184c204f30c3d3a69a53decd9da8'   # 1f24d49 OLCUM png_sha256 AQUARIUS_PISCES_SADE_ALTIN_954.png
AQU_KATI_ONCE = 1.35                                                                  # 1f24d49 OLCUM cift.AQUARIUS_PISCES.sade.koyulasma_oncesi_kati
STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')


def yukle(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:                                                          # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    for k in ('olcum', 'kapi', 'k', 'gv1_olcum', 'gv1_k', 'gv1_png', 'gv1_rapor', 'gb', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    R_ = yukle(a.olcum) or {}; C = R_.get('cift', {}); T = yukle(a.kapi) or {}; G1 = yukle(a.gv1_olcum) or {}; GB = yukle(a.gb) or []
    B = []

    def b(ad, gecti, olculen, kaynak, not_=None):
        B.append(dict(beklenti=ad, gecti=bool(gecti), olculen=olculen, kaynak=kaynak, not_=not_))

    b('cl_kontrol', R_.get('kontrol_pass') is True, R_.get('kontrol'), 'OLCUM.json kontrol (onayli 6daab364 5 stil)')
    ok_ = (C.get('AQUARIUS_PISCES') or {}).get('onayli_kiyas') or {}
    b('kova_onayli_kiyas', len(ok_) == 3 and all(v.get('tolerans_icinde') for v in ok_.values()), ok_,
      'OLCUM cift.AQUARIUS_PISCES.onayli_kiyas (onayli: Drive ORNAMENT_KOVA_DUZELTME_20261104_1058_41817771849)')
    sha = R_.get('png_sha256', {})
    for c in ('AQUARIUS_PISCES', 'GEMINI_VIRGO'):
        s1 = ((C.get(c) or {}).get('sade') or {}).get('sade1_sha256'); sa = sha.get(f'{c}_SADE_ALTIN_954.png')
        fi = ((C.get(c) or {}).get('fildisi') or {}).get('girdi_sha256')
        b(f'o2_sha_esit_{c}', s1 is not None and s1 == sa == fi, dict(sade_altin=sa, sade1=s1, fildisi_girdi=fi), 'OLCUM png_sha256 + sade.sade1_sha256 + fildisi.girdi_sha256',
          'zayif test (KALITE 3): uc deger ayni SADE_1 dosyasindan, yapisi geregi esit; O2 kaniti o2_kati_aqu + o2_bilinen_fail')
    kh = ((C.get('AQUARIUS_PISCES') or {}).get('sade') or {}).get('kati_ham')
    b('o2_kati_aqu', kh is not None and round(kh, 2) == AQU_KATI_ONCE, kh, f'OLCUM sade.kati_ham; beklenen {AQU_KATI_ONCE} (1f24d49 koyulasma_oncesi_kati)')
    sa = sha.get('AQUARIUS_PISCES_SADE_ALTIN_954.png')
    b('o2_bilinen_fail', sa is not None and sa != ESKI_SADE_AQU, dict(yeni=sa, eski=ESKI_SADE_AQU), 'eski koyulastirilmis dosya sha (1f24d49 OLCUM)')
    B.append(dict(beklenti='o2_cl_zayif', gecti=True, olculen=None, kaynak='bilgi',
                  not_='CANCER_LIBRA SADE kiyasi O2 icin zayif test (CL carpan 1,0: eski SADE_KOYU = SADE_1); kanit AQUARIUS_PISCES ve GEMINI_VIRGO'))
    iddia = None
    for t in T.get('kaynaklar', []):
        if t.get('kaynak', '').startswith('aquarius'):
            iddia = (t.get('mod_kapali') or {}).get('onarimsiz_kapi_iddia')
    b('kapi_onarimsiz_iddia', bool(iddia and iddia.get('gecti') and iddia.get('olculen', 0) > 0), iddia, 'KOVA_KAPI_TESTI.json (gercek aquarius)')
    kn = (C.get('AQUARIUS_PISCES') or {}).get('kenar_onarimsiz_neden')
    b('kova_onarimsiz_neden', bool(kn and kn.get('gecti')), kn, 'OLCUM cift.AQUARIUS_PISCES.kenar_onarimsiz_neden (onarimsiz motor OLCUM)')
    gv = C.get('GEMINI_VIRGO') or {}
    gs = (gv.get('kapi') or {}).get('sert') or {}
    b('gv_varsayilan', bool(gs) and all(gs.values()) and not gv.get('eksik'), dict(fail=[k for k, v in gs.items() if not v], kucultme=gv.get('kucultme')),
      'OLCUM cift.GEMINI_VIRGO', 'beklenti 2202 olcumunden (2 px, gecer; kenar onarimi yok); kenar_onar oncesi olcum, dogrulanmadi')
    g1 = (G1.get('cift') or {}).get('GEMINI_VIRGO') or {}
    g1s = (g1.get('kapi') or {}).get('sert') or {}
    g1f = [k for k, v in g1s.items() if not v]
    png = [s for s in STIL if (Path(a.gv1_png) / f'GEMINI_VIRGO_{s}_954.png').exists()]
    gbf = Path(a.gv1_rapor) / 'GERCEK_BOY_GEMINI_VIRGO_5STIL_300dpi.png'
    b('gv_sinir1', str(a.gv1_k) == '1' and g1f == ['koyu_kucultme_le_sinir'] and len(png) == 5 and gbf.exists(),
      dict(cikis=a.gv1_k, sert_fail=g1f, png=png, gercek_boy=gbf.exists(), kucultme=g1.get('kucultme')), 'GV_SINIR1 OLCUM.json + dosyalar (ORN_KUCULT_SINIR_PX=1)')
    b('genel_cikis', str(a.k) == '0', a.k, 'ornek78 cikis (ana adim)')
    b('listeler', all(k in R_ for k in ('dusuk_kontrast', 'kucultme', 'kenar_onarim_uyari')),
      dict(dusuk_kontrast=R_.get('dusuk_kontrast'), kucultme=R_.get('kucultme'), kenar_onarim_uyari=R_.get('kenar_onarim_uyari')), 'OLCUM.json')
    b('gercek_boy', bool(GB) and all(g.get('gecti') for g in GB), [(Path(g['dosya']).name, g['gecti']) for g in GB], 'GERCEK_BOY_KONTROL.json')
    out = dict(beklentiler=B, hepsi_gecti=all(x['gecti'] for x in B))
    Path(a.cikti).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    for x in B:
        print('PASS' if x['gecti'] else 'FAIL', x['beklenti'], '|', json.dumps(x['olculen'], ensure_ascii=False, default=str)[:220], flush=True)
    print('BEKLENEN', 'PASS' if out['hepsi_gecti'] else 'FAIL', flush=True)
    return 0 if out['hepsi_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
