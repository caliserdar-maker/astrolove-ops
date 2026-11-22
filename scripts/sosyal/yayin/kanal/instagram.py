"""Instagram (Instagram Login, graph.instagram.com). Iki adim: kapsayici -> media_publish (plan R1).
media_publish ASLA yeniden denenmez (Http POST tek deneme). Kimlik: {"token", "ig_id"}."""
import os
import time

from ortak import Hata

BASE = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/") + "/" + os.environ.get("IG_API_VERSION", "v21.0")
BEKLE_ADIM, BEKLE_EN_COK = 5, 300


def kimlik_dogrula(http, k):
    j, _ = http.iste("GET", f"{BASE}/me", token=k["token"], params={"fields": "user_id,username"})
    if str(j.get("user_id") or j.get("id")) != str(k["ig_id"]):
        raise Hata("Instagram token baska hesaba ait")
    return j.get("username", "")


def _kap(http, k, uyku, **alan):
    j, _ = http.iste("POST", f"{BASE}/{k['ig_id']}/media", token=k["token"], data=alan)
    cid = j.get("id")
    if not cid:
        raise Hata("kapsayici no donmedi")
    return cid


def _hazir(http, k, cid, uyku):
    t = 0
    while t <= BEKLE_EN_COK:
        j, _ = http.iste("GET", f"{BASE}/{cid}", token=k["token"], params={"fields": "status_code"})
        st = j.get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise Hata(f"kapsayici {st}")
        uyku(BEKLE_ADIM)
        t += BEKLE_ADIM
    raise Hata("kapsayici zamaninda hazir olmadi")


def yayinla(http, k, satir, medya, uyku=time.sleep):
    tur, metin = satir["tur"], satir.get("metin", "")
    if any(not m.get("url") for m in medya):
        raise Hata("Instagram herkese acik medya adresi ister")
    if tur == "reel":
        cid = _kap(http, k, uyku, media_type="REELS", video_url=medya[0]["url"], caption=metin)
    elif tur == "hikaye":
        m = medya[0]
        alan = {"media_type": "STORIES", ("video_url" if m["tip"] == "video" else "image_url"): m["url"]}
        cid = _kap(http, k, uyku, **alan)
    elif tur == "gorsel":
        cid = _kap(http, k, uyku, image_url=medya[0]["url"], caption=metin)
    elif tur == "karusel":
        cocuk = []
        for m in medya:
            alan = {"is_carousel_item": "true", ("video_url" if m["tip"] == "video" else "image_url"): m["url"]}
            if m["tip"] == "video":
                alan["media_type"] = "VIDEO"
            c = _kap(http, k, uyku, **alan)
            _hazir(http, k, c, uyku)
            cocuk.append(c)
        cid = _kap(http, k, uyku, media_type="CAROUSEL", children=",".join(cocuk), caption=metin)
    else:
        raise Hata(f"instagram tur desteklenmiyor: {tur}")
    _hazir(http, k, cid, uyku)
    j, _ = http.iste("POST", f"{BASE}/{k['ig_id']}/media_publish", token=k["token"], data={"creation_id": cid})
    if not j.get("id"):
        raise Hata("media_publish no donmedi", belirsiz=True)
    return j["id"]
