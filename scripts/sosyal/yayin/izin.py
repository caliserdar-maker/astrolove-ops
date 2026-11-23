#!/usr/bin/env python3
"""Ilk baglanti (plan 4.5; kurulum S7). Sir ya da izin kodu is akisi GIRDISI olmaz.
  link  <platform>   izin ekrani linki + state Drive TEMP'e yazilir (loga YAZILMAZ); Serdar donus sayfasinda state'i karsilastirir
  cevir <platform>   OAUTH_KOD_<IG|FB|THREADS|YT> (GitHub Secret, ortam degiskeni) -> uzun omurlu token -> Drive TEMP;
                     sonra kod sirri GitHub'dan silinir (OPS_ADMIN_TOKEN). Token ve kod loga yazilmaz.
Donus adresi tek: DONUS (astrolove-media app/oauth.html)."""
import json
import os
import secrets
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import Hata, Http, drive_oku, drive_yaz, gizle, log  # noqa: E402
import kimlik  # noqa: E402

DONUS = "https://caliserdar-maker.github.io/astrolove-media/app/oauth.html"
KISA = {"instagram": "IG", "facebook": "FB", "threads": "THREADS", "youtube": "YT"}
IG_G = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/")
FB_G = os.environ.get("FB_GRAPH_BASE", "https://graph.facebook.com").rstrip("/") + "/" + os.environ.get("FB_API_VERSION", "v21.0")
TH_G = os.environ.get("TH_GRAPH_BASE", "https://graph.threads.net").rstrip("/")
IG_OAUTH = os.environ.get("IG_OAUTH_BASE", "https://api.instagram.com").rstrip("/")
GOOGLE_TOKEN = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
GH_API = os.environ.get("GH_API", "https://api.github.com").rstrip("/")
REPO = os.environ.get("GITHUB_REPOSITORY", "caliserdar-maker/astrolove-ops")


def _env(ad):
    v = os.environ.get(ad, "").strip()
    if not v:
        raise Hata(f"{ad} tanimli degil")
    return v


def istemci(p):
    on = {"instagram": "IG_APP", "facebook": "META_APP", "threads": "THREADS_APP"}.get(p)
    cid, csec = (_env(f"{on}_ID"), _env(f"{on}_SECRET")) if on else (_env("YT_CLIENT_ID"), _env("YT_CLIENT_SECRET"))
    gizle(csec)
    return cid, csec


def state_yolu(p):
    return f"{kimlik.KOK}/SOSYAL_IZIN_STATE_{p.upper()}.json"


def link(p, simdi=None):
    cid = istemci(p)[0]
    st = secrets.token_urlsafe(12)
    q = {"client_id": cid, "redirect_uri": DONUS, "response_type": "code", "state": st}
    if p == "instagram":
        u = "https://www.instagram.com/oauth/authorize"
        q["scope"] = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights"
    elif p == "facebook":
        u = "https://www.facebook.com/" + os.environ.get("FB_API_VERSION", "v21.0") + "/dialog/oauth"
        cfg = os.environ.get("FB_CONFIG_ID", "").strip()
        if cfg:  # Facebook Login for Business: yapilandirma kimligi scope'un yerine gecer (izinler yapilandirmada)
            q["config_id"] = cfg
        else:  # business_management: isletme portfoyune bagli Sayfa icin (23 Kas: /me/accounts bos dondu)
            q["scope"] = "pages_show_list,pages_read_engagement,pages_manage_posts,read_insights,business_management"
    elif p == "threads":
        u = "https://threads.net/oauth/authorize"
        q["scope"] = "threads_basic,threads_content_publish,threads_manage_insights"
    else:
        u = "https://accounts.google.com/o/oauth2/v2/auth"
        q.update(scope="https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
                 access_type="offline", prompt="consent")
    simdi = simdi or datetime.now(timezone.utc)
    drive_yaz(state_yolu(p), json.dumps({"state": st, "olusturma": simdi.isoformat()}))
    adres = u + "?" + urllib.parse.urlencode(q)
    # Link ve state herkese acik loga yazilmaz (state CSRF degeridir); Merkez Drive'dan okuyup Serdar'a verir.
    drive_yaz(f"{kimlik.KOK}/SOSYAL_IZIN_LINK_{p.upper()}.txt", f"{adres}\nSTATE={st}\n")
    log(f"izin linki Drive'a yazildi: {kimlik.KOK}/SOSYAL_IZIN_LINK_{p.upper()}.txt")
    return adres, st


def _bitis(sn, simdi):
    return (simdi + timedelta(seconds=int(sn or 0))).isoformat() if sn else ""


def _fb_sayfa(http, cid, csec, uzun):
    """Sayfa token'i. 1) /me/accounts. 2) Bossa (Facebook Login for Business + isletme portfoyune bagli Sayfa;
    23 Kas olcumu kosu 45142527416): debug_token granular_scopes target_ids (secilen Sayfa) ya da FB_PAGE_ID ->
    GET /{sayfa}?fields=id,name,access_token. 3) O da token vermezse DUR (yapilandirmaya business_management)."""
    hedef = os.environ.get("FB_PAGE_ID", "").strip()
    s, _ = http.iste("GET", f"{FB_G}/me/accounts", token=uzun, params={"fields": "id,name,access_token"})
    sayfalar = s.get("data", [])
    for x in sayfalar:
        gizle(x.get("access_token", ""))
    if sayfalar:
        sec = [x for x in sayfalar if not hedef or x.get("id") == hedef]
        if len(sec) != 1 or not sec[0].get("access_token"):
            raise Hata(f"Sayfa secilemedi ({len(sayfalar)} sayfa; FB_PAGE_ID ile secin): "
                       + ", ".join(f"{x.get('name')}={x.get('id')}" for x in sayfalar))
        x = sec[0]
        log("facebook: Sayfa /me/accounts ile bulundu")
        return {"token": x["access_token"], "page_id": x["id"], "hesap": x.get("name", ""), "bitis": ""}
    # 2) secilen Sayfa kimligi (yalniz paylasim izni verilen Sayfalar: pages_manage_posts hedefleri)
    d, _ = http.iste("GET", f"{FB_G}/debug_token", sorgu_sirri=True,
                     params={"input_token": uzun, "access_token": f"{cid}|{csec}"})
    veri = d.get("data", {})
    if not veri.get("is_valid"):
        raise Hata(f"debug_token: token gecersiz ({(veri.get('error') or {}).get('message', 'neden yok')})")
    izinler = sorted(veri.get("scopes", []))
    paylasim = [g for g in veri.get("granular_scopes", []) if g.get("scope") == "pages_manage_posts"]
    log(f"facebook: /me/accounts bos; izinler {','.join(izinler)}")
    if "pages_manage_posts" not in izinler:
        raise Hata("pages_manage_posts izni verilmemis; izni yeniden verin")
    hedefler = {str(t) for g in paylasim for t in g.get("target_ids", [])}
    hepsi = bool(paylasim) and not hedefler  # belge: izin tum varliklara gecerliyse target_ids gosterilmez
    log(f"facebook: paylasim izinli Sayfa sayisi {len(hedefler) if not hepsi else 'tum'}")
    if hedef:
        if not hepsi and hedef not in hedefler:
            raise Hata("FB_PAGE_ID paylasim izni verilen Sayfalar arasinda degil")
        aday = hedef
    elif len(hedefler) == 1:
        aday = next(iter(hedefler))
    else:
        raise Hata(f"Sayfa secilemedi (/me/accounts bos, paylasim izinli Sayfa {len(hedefler) if not hepsi else 'tum'}; FB_PAGE_ID ile secin)")
    x, _ = http.iste("GET", f"{FB_G}/{aday}", token=uzun, params={"fields": "id,name,access_token"})
    gizle(x.get("access_token", ""))
    if not x.get("access_token") or str(x.get("id")) != aday:
        raise Hata("Sayfa token'i alinamadi; yapilandirmaya business_management izni ekleyip izni yeniden verin")
    log("facebook: Sayfa secilen Sayfa kimligiyle bulundu")
    k = {"token": x["access_token"], "page_id": aday, "hesap": x.get("name", ""), "bitis": ""}
    if veri.get("data_access_expires_at"):
        k["veri_erisim_bitis"] = str(veri["data_access_expires_at"])
    return k


def cevir(p, http, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    ad = f"OAUTH_KOD_{KISA[p]}"
    kod = _env(ad)
    kod = kod[:-2] if kod.endswith("#_") else kod
    gizle(kod)
    cid, csec = istemci(p)
    if p == "instagram":
        j, _ = http.iste("POST", f"{IG_OAUTH}/oauth/access_token", data={"client_id": cid, "client_secret": csec,
                         "grant_type": "authorization_code", "redirect_uri": DONUS, "code": kod})
        j = (j.get("data") or [j])[0] if isinstance(j.get("data"), list) else j
        kisa = j.get("access_token") or ""
        gizle(kisa)
        u, _ = http.iste("GET", f"{IG_G}/access_token", sorgu_sirri=True,
                         params={"grant_type": "ig_exchange_token", "client_secret": csec, "access_token": kisa})
        tok = u.get("access_token") or ""
        gizle(tok)
        me, _ = http.iste("GET", f"{IG_G}/" + os.environ.get("IG_API_VERSION", "v21.0") + "/me", token=tok,
                          params={"fields": "user_id,username"})
        k = {"token": tok, "ig_id": str(me.get("user_id") or ""), "hesap": me.get("username", ""),
             "bitis": _bitis(u.get("expires_in"), simdi)}
    elif p == "threads":
        j, _ = http.iste("POST", f"{TH_G}/oauth/access_token", data={"client_id": cid, "client_secret": csec,
                         "grant_type": "authorization_code", "redirect_uri": DONUS, "code": kod})
        kisa = j.get("access_token") or ""
        gizle(kisa)
        u, _ = http.iste("GET", f"{TH_G}/access_token", sorgu_sirri=True,
                         params={"grant_type": "th_exchange_token", "client_secret": csec, "access_token": kisa})
        tok = u.get("access_token") or ""
        gizle(tok)
        k = {"token": tok, "th_id": str(j.get("user_id") or ""), "bitis": _bitis(u.get("expires_in"), simdi)}
    elif p == "facebook":
        j, _ = http.iste("GET", f"{FB_G}/oauth/access_token", sorgu_sirri=True,
                         params={"client_id": cid, "redirect_uri": DONUS, "client_secret": csec, "code": kod})
        kisa = j.get("access_token") or ""
        gizle(kisa)
        u, _ = http.iste("GET", f"{FB_G}/oauth/access_token", sorgu_sirri=True,
                         params={"grant_type": "fb_exchange_token", "client_id": cid, "client_secret": csec,
                                 "fb_exchange_token": kisa})
        uzun = u.get("access_token") or ""
        gizle(uzun)
        k = _fb_sayfa(http, cid, csec, uzun)
    else:
        j, _ = http.iste("POST", GOOGLE_TOKEN, data={"code": kod, "client_id": cid, "client_secret": csec,
                         "redirect_uri": DONUS, "grant_type": "authorization_code"})
        rt, at = j.get("refresh_token") or "", j.get("access_token") or ""
        gizle(rt, at)
        if not rt:
            raise Hata("refresh_token donmedi (izin ekrani prompt=consent ile yeniden acilmali)")
        c, _ = http.iste("GET", os.environ.get("YT_API_BASE", "https://www.googleapis.com").rstrip("/") + "/youtube/v3/channels",
                         token=at, params={"part": "id,snippet", "mine": "true"})
        kan = c.get("items", [])
        hedef = os.environ.get("YT_KANAL_ID", "").strip()
        sec = [x for x in kan if not hedef or x.get("id") == hedef]
        if len(sec) != 1:
            raise Hata(f"kanal secilemedi ({len(kan)} kanal; YT_KANAL_ID ile secin)")
        k = {"refresh_token": rt, "kanal_id": sec[0]["id"], "hesap": sec[0].get("snippet", {}).get("title", ""), "bitis": ""}
    sir, hesap = kimlik.ALAN[p]
    if not (k.get(sir) and k.get(hesap)):
        raise Hata(f"{p}: token ya da hesap kimligi eksik dondu")
    k["olusturma"] = simdi.isoformat()
    kimlik.yaz(p, k)
    log(f"{p}: token Drive'a yazildi (hesap {k.get('hesap') or k[hesap]}, bitis {k.get('bitis') or '-'})")
    adm = os.environ.get("OPS_ADMIN_TOKEN", "")
    if adm:
        gizle(adm)
        http.iste("DELETE", f"{GH_API}/repos/{REPO}/actions/secrets/{ad}", token=adm,
                  basliklar={"Accept": "application/vnd.github+json"}, beklenen=(204, 404))
        log(f"{ad} sirri silindi")
    else:
        log(f"UYARI: OPS_ADMIN_TOKEN yok; {ad} sirrini elle silin")
    return k


def main(argv=None, http=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("link", "cevir") or argv[1] not in KISA:
        log("kullanim: izin.py link|cevir instagram|facebook|threads|youtube")
        return 2
    try:
        if argv[0] == "link":
            link(argv[1])
        else:
            cevir(argv[1], http or Http())
        return 0
    except Hata as e:
        log(f"DUR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
