#!/usr/bin/env python3
"""K3 TikTok profil linki uygunlugu (19 Eki 2026). SALT OKUMA: Metricool'a ve TikTok'a YAZMA YOK, yalniz GET.
1) Metricool (data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json):
   GET /admin/simpleProfiles                    kendi blog: tiktok, tiktokAccountType (+ diger tiktok* alanlari)
   GET /v2/settings/brands/{blogId}             networksData.tiktok (TikTokData: username, accountType, profileURL ...)
   GET /v2/scheduler/catalogs/tiktok/creator-info   TikTokCreatorInfo: creatorUsername, creatorNickname ...
   Metricool bio / website alani vermiyorsa "erisilemedi".
2) Herkese acik profil https://www.tiktok.com/@astroloveart (GET, gomulu JSON: signature, bioLink, followerCount).
3) TikTok yardim sayfalari (GET): website linki kosulu cumleleri.
Token / oturum alanlari (token, secret, auth, refresh, password, cookie) yazilmadan once '***' yapilir.
Cikti: K3_PROFIL.md + HAM_K3_*.json. Kullanim: tiktok_profil.py TOKEN.json CIKTI_DIR"""
import html
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

YOK = 'erisilemedi'
PROFIL = 'https://www.tiktok.com/@astroloveart'
YARDIM = ['https://support.tiktok.com/en/getting-started/setting-up-your-profile/linking-another-social-media-account',
          'https://support.tiktok.com/en/using-tiktok/growing-your-audience/switching-to-a-creator-or-business-account',
          'https://support.tiktok.com/en/getting-started/setting-up-your-profile']
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')
GIZLI = re.compile(r'token|secret|auth|refresh|password|cookie|session', re.I)


def ort(o):
    if isinstance(o, dict):
        return {k: ('***' if GIZLI.search(k) and v not in (None, '', False) else ort(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [ort(x) for x in o]
    return o


def ham(out, ad, veri):
    json.dump(ort(veri), open(os.path.join(out, f'HAM_K3_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def mc_get(mc, out, ad, yol):
    try:
        j = mc.istek('GET', yol)
    except SystemExit as e:
        j = {'_hata': str(e)[:300]}
    ham(out, ad, j)
    print(f'{ad}: {"HATA " + j["_hata"][:150] if isinstance(j, dict) and "_hata" in j else "ok"}')
    return j


def web(url):
    r = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9',
                                             'Accept': 'text/html,application/xhtml+xml'})
    try:
        with urllib.request.urlopen(r, timeout=30) as y:
            return y.status, y.geturl(), y.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode('utf-8', 'replace')
    except Exception as e:  # DNS, TLS, zaman asimi
        return None, url, f'{type(e).__name__}: {e}'


def bul(o, anahtar):
    """ic ice yapida ilk 'anahtar' degeri."""
    if isinstance(o, dict):
        if anahtar in o:
            return o[anahtar]
        for v in o.values():
            r = bul(v, anahtar)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = bul(v, anahtar)
            if r is not None:
                return r
    return None


def d(v):
    return YOK if v in (None, '') else v


def main():
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'OKUMA ANI (UTC): {okuma}')
    md = [f'# K3 TikTok profil linki uygunlugu (SALT OKUMA)', '', f'Okuma ani (UTC): {okuma}. Metricool userId/blogId: Drive METRICOOL_TOKEN.json.', '']

    # 1) Metricool
    sp_ = mc_get(mc, out, 'simpleProfiles', '/admin/simpleProfiles')
    blog = next((b for b in (sp_ if isinstance(sp_, list) else mpb.veri(sp_) if isinstance(mpb.veri(sp_), list) else [])
                 if str(b.get('id')) == mc.b), {})
    tt_sp = {k: v for k, v in ort(blog).items() if 'tiktok' in k.lower()}
    print(f'simpleProfiles tiktok alanlari: {tt_sp}')
    br = mc_get(mc, out, 'brand', f'/v2/settings/brands/{mc.b}')
    nd = (mpb.veri(br) or {}).get('networksData', {}) if isinstance(br, dict) else {}
    tt_br = ort(next((v for k, v in (nd or {}).items() if k.lower() == 'tiktok'), None) or {})
    print(f'brand networksData.tiktok alanlari: {sorted(tt_br) if isinstance(tt_br, dict) else tt_br}')
    ci = mc_get(mc, out, 'creator_info', '/v2/scheduler/catalogs/tiktok/creator-info')
    ci_d = ort(mpb.veri(ci)) if isinstance(ci, dict) and '_hata' not in ci else {}
    if isinstance(ci_d, dict):
        ci_d.pop('creatorAvatarUrl', None)
    print(f'creator-info: {ci_d if ci_d else ci}')
    tb = tt_br if isinstance(tt_br, dict) else {}
    bio_mc = next((tb[k] for k in tb if re.search(r'bio|signature|description', k, re.I)), None)
    web_mc = next((tb[k] for k in tb if re.search(r'website|bioLink|link', k, re.I) and k != 'profileURL'), None)
    md += ['## 1. Metricool baglanti bilgisi', '', '| Bilgi | Deger | Uc | Alan |', '|---|---|---|---|',
           f'| Hesap turu | {d(tt_sp.get("tiktokAccountType"))} | /admin/simpleProfiles | tiktokAccountType |',
           f'| Hesap turu | {d(tb.get("accountType"))} | /v2/settings/brands/{{blogId}} | networksData.tiktok.accountType |',
           f'| Kullanici adi | {d(tt_sp.get("tiktok"))} | /admin/simpleProfiles | tiktok |',
           f'| Kullanici adi | {d(tb.get("username"))} | /v2/settings/brands/{{blogId}} | networksData.tiktok.username |',
           f'| Profil URL | {d(tb.get("profileURL"))} | /v2/settings/brands/{{blogId}} | networksData.tiktok.profileURL |',
           f'| Profil adi (nickname) | {d(ci_d.get("creatorNickname") if isinstance(ci_d, dict) else None)} | /v2/scheduler/catalogs/tiktok/creator-info | creatorNickname |',
           f'| Kullanici adi | {d(ci_d.get("creatorUsername") if isinstance(ci_d, dict) else None)} | /v2/scheduler/catalogs/tiktok/creator-info | creatorUsername |',
           f'| Bio | {d(bio_mc)} | Metricool (3 uc) | {"alan var" if bio_mc else "alan yok"} |',
           f'| Website | {d(web_mc)} | Metricool (3 uc) | {"alan var" if web_mc else "alan yok"} |', '',
           f'simpleProfiles tiktok* alanlari: `{json.dumps(tt_sp, ensure_ascii=False)}`', '',
           f'brand networksData.tiktok alanlari: `{json.dumps(tb, ensure_ascii=False)}`', '',
           f'creator-info: `{json.dumps(ci_d if ci_d else ort(ci), ensure_ascii=False)[:600]}`', '']

    # 2) herkese acik profil
    st, son_url, govde = web(PROFIL)
    print(f'PROFIL GET: status {st}, son url {son_url}, uzunluk {len(govde)}')
    pr = {'status': st, 'son_url': son_url, 'uzunluk': len(govde)}
    m = re.search(r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', govde, re.S)
    user, stats = {}, {}
    if m:
        try:
            j = json.loads(m.group(1))
            ui = bul(j, 'userInfo') or {}
            user, stats = ui.get('user') or {}, ui.get('stats') or {}
            pr['user_detail_statusCode'] = bul(j.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {}), 'statusCode')
        except ValueError as e:
            pr['json_hata'] = str(e)[:200]
    og = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"', govde)
    pr.update({'gomulu_json': bool(m), 'uniqueId': user.get('uniqueId'), 'nickname': user.get('nickname'),
               'signature': user.get('signature'), 'bioLink': user.get('bioLink'), 'commerceUserInfo': user.get('commerceUserInfo'),
               'ttSeller': user.get('ttSeller'), 'privateAccount': user.get('privateAccount'), 'stats': stats,
               'og_description': html.unescape(og.group(1)) if og else None,
               'govde_basi': govde[:300] if not m else None})
    ham(out, 'profil_sayfa', pr)
    print(f'PROFIL: {json.dumps({k: v for k, v in pr.items() if k != "govde_basi"}, ensure_ascii=False)[:800]}')
    bl = user.get('bioLink') or {}
    md += ['## 2. Herkese acik profil sayfasi', '', f'GET {PROFIL} -> HTTP {d(st)}, son URL {son_url}, {len(govde)} bayt, '
           f'gomulu JSON (__UNIVERSAL_DATA_FOR_REHYDRATION__) {"var" if m else "yok"}'
           + (f'; hata: {govde[:150]}' if st is None else '') + '.', '',
           '| Bilgi | Deger | Alan |', '|---|---|---|',
           f'| Kullanici adi | {d(user.get("uniqueId"))} | userInfo.user.uniqueId |',
           f'| Profil adi | {d(user.get("nickname"))} | userInfo.user.nickname |',
           f'| Bio | {d((user.get("signature") or "").replace(chr(10), " / ") or None)} | userInfo.user.signature |',
           f'| Website / bio linki | {d(bl.get("link") if isinstance(bl, dict) else bl)} | userInfo.user.bioLink.link |',
           f'| Takipci | {d(stats.get("followerCount"))} | userInfo.stats.followerCount |',
           f'| Video | {d(stats.get("videoCount"))} | userInfo.stats.videoCount |',
           f'| Begeni (toplam) | {d(stats.get("heartCount") or stats.get("heart"))} | userInfo.stats.heartCount |',
           f'| commerceUserInfo | {d(json.dumps(user.get("commerceUserInfo"), ensure_ascii=False) if user.get("commerceUserInfo") else None)} | userInfo.user.commerceUserInfo |',
           f'| og:description | {d(pr["og_description"])} | meta og:description |', '']

    # 3) yardim sayfalari
    md += ['## 3. TikTok yardim sayfasi: profilde website linki kosulu', '']
    yr = []
    for u in YARDIM:
        st, son_url, govde = web(u)
        metin = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>', ' ', govde))))
        baslik = re.search(r'<title>(.*?)</title>', govde, re.S)
        cumle = sorted({c.strip() for c in re.split(r'(?<=[.!?])\s+', metin)
                        if re.search(r'website|web site|link in bio|bio link', c, re.I) and len(c) < 400})
        yr.append({'url': u, 'status': st, 'son_url': son_url, 'baslik': baslik.group(1).strip() if baslik else None,
                   'uzunluk': len(govde), 'website_cumleleri': cumle[:30], 'govde_basi': govde[:200] if not cumle else None})
        print(f'YARDIM {u}: status {st}, {len(cumle)} cumle')
        for c in cumle[:12]:
            print('   ', c[:300])
        md += [f'- {u} (GET {okuma}, HTTP {d(st)}, baslik: {d(yr[-1]["baslik"])}'
               + (f', hata: {govde[:150]}' if st is None else '') + ')']
        md += [f'  - "{c}"' for c in cumle[:12]] or ['  - website cumlesi: erisilemedi']
    ham(out, 'yardim', yr)
    md += ['']
    open(os.path.join(out, 'K3_PROFIL.md'), 'w').write('\n'.join(md) + '\n')
    print('K3_PROFIL.md yazildi')


if __name__ == '__main__':
    main()
