"""YouTube Shorts (YouTube Data API v3, videos.insert resumable; plan R8). Ayri Google projesi (Merkez 22 Kas karari).
Kimlik: {"refresh_token", "kanal_id"}; istemci YT_CLIENT_ID / YT_CLIENT_SECRET (GitHub Secrets).
Gorunurluk satirdan (public / private / unlisted); yapay zeka beyani status.containsSyntheticMedia (plan R12, dogrulanacak)."""
import os

from ortak import Hata, gizle

TOKEN_URL = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
API = os.environ.get("YT_API_BASE", "https://www.googleapis.com").rstrip("/")


def erisim(http, k):
    cid, csec = os.environ.get("YT_CLIENT_ID", ""), os.environ.get("YT_CLIENT_SECRET", "")
    if not (cid and csec and k.get("refresh_token")):
        raise Hata("YouTube istemci ya da refresh_token eksik")
    gizle(csec, k["refresh_token"])
    j, _ = http.iste("POST", TOKEN_URL, data={"client_id": cid, "client_secret": csec,
                                              "refresh_token": k["refresh_token"], "grant_type": "refresh_token"})
    t = j.get("access_token")
    if not t:
        raise Hata("YouTube access_token alinamadi")
    gizle(t)
    return t


def kimlik_dogrula(http, k):
    t = erisim(http, k)
    j, _ = http.iste("GET", f"{API}/youtube/v3/channels", token=t, params={"part": "id,snippet", "mine": "true"})
    ids = [c.get("id") for c in j.get("items", [])]
    if k["kanal_id"] not in ids:
        raise Hata("YouTube token beklenen kanala ait degil")
    return next(c["snippet"].get("title", "") for c in j["items"] if c["id"] == k["kanal_id"])


def yayinla(http, k, satir, medya, uyku=None):
    if satir["tur"] != "short":
        raise Hata(f"youtube tur desteklenmiyor: {satir['tur']}")
    t = erisim(http, k)
    metin = satir.get("metin", "")
    baslik = (metin.splitlines() or [""])[0][:100].strip()
    if not baslik:
        raise Hata("YouTube basligi bos (metnin ilk satiri)")
    govde = {"snippet": {"title": baslik, "description": metin[:5000], "categoryId": "22"},
             "status": {"privacyStatus": satir["gorunurluk"].strip(), "selfDeclaredMadeForKids": False,
                        "containsSyntheticMedia": satir.get("yz_beyani") == "evet"}}
    veri = medya[0]["yerel"].read_bytes()
    _, r = http.iste("POST", f"{API}/upload/youtube/v3/videos", token=t,
                     params={"uploadType": "resumable", "part": "snippet,status"}, json_govde=govde,
                     basliklar={"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(veri))})
    yer = r.headers.get("Location") or r.headers.get("location")
    if not yer:
        raise Hata("yukleme adresi donmedi")
    j, _ = http.iste("PUT", yer, token=t, govde=veri, basliklar={"Content-Type": "video/mp4"}, beklenen=(200, 201))
    if not j.get("id"):
        raise Hata("video no donmedi", belirsiz=True)
    return j["id"]
