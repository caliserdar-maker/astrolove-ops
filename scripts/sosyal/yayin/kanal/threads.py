"""Threads (graph.threads.net). Iki adim; yayindan once kapsayici FINISHED beklenir (plan R6: ~30 sn).
Kimlik: {"token", "th_id"}."""
import os
import time

from ortak import Hata

BASE = os.environ.get("TH_GRAPH_BASE", "https://graph.threads.net").rstrip("/") + "/v1.0"
BEKLE_ADIM, BEKLE_EN_COK = 10, 300


def kimlik_dogrula(http, k):
    j, _ = http.iste("GET", f"{BASE}/me", token=k["token"], params={"fields": "id,username"})
    if str(j.get("id")) != str(k["th_id"]):
        raise Hata("Threads token baska hesaba ait")
    return j.get("username", "")


def _kap(http, k, **alan):
    alan = {a: v for a, v in alan.items() if v not in (None, "")}
    j, _ = http.iste("POST", f"{BASE}/{k['th_id']}/threads", token=k["token"], data=alan)
    if not j.get("id"):
        raise Hata("kapsayici no donmedi")
    return j["id"]


def _hazir(http, k, cid, uyku):
    t = 0
    while t <= BEKLE_EN_COK:
        uyku(BEKLE_ADIM)
        t += BEKLE_ADIM
        j, _ = http.iste("GET", f"{BASE}/{cid}", token=k["token"], params={"fields": "status,error_message"})
        st = j.get("status")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise Hata(f"kapsayici {st} {j.get('error_message', '')}")
    raise Hata("kapsayici zamaninda hazir olmadi")


def yayinla(http, k, satir, medya, uyku=time.sleep):
    tur, metin = satir["tur"], satir.get("metin", "")
    etiket = (satir.get("pano") or "").strip()  # konu etiketi (topic_tag, gonderi basina 1; resmi Threads Posts)
    if any(not m.get("url") for m in medya):
        raise Hata("Threads herkese acik medya adresi ister")
    if tur == "metin":
        cid = _kap(http, k, media_type="TEXT", text=metin, topic_tag=etiket)
    elif tur in ("gorsel", "video"):
        m = medya[0]
        tip = "VIDEO" if m["tip"] == "video" else "IMAGE"
        cid = _kap(http, k, media_type=tip, text=metin, topic_tag=etiket, **{("video_url" if tip == "VIDEO" else "image_url"): m["url"]})
    elif tur == "karusel":
        cocuk = []
        for m in medya:
            tip = "VIDEO" if m["tip"] == "video" else "IMAGE"
            c = _kap(http, k, media_type=tip, is_carousel_item="true",
                     **{("video_url" if tip == "VIDEO" else "image_url"): m["url"]})
            _hazir(http, k, c, uyku)
            cocuk.append(c)
        cid = _kap(http, k, media_type="CAROUSEL", children=",".join(cocuk), text=metin, topic_tag=etiket)
    else:
        raise Hata(f"threads tur desteklenmiyor: {tur}")
    _hazir(http, k, cid, uyku)
    j, _ = http.iste("POST", f"{BASE}/{k['th_id']}/threads_publish", token=k["token"], data={"creation_id": cid})
    if not j.get("id"):
        raise Hata("threads_publish no donmedi", belirsiz=True)
    return j["id"]
