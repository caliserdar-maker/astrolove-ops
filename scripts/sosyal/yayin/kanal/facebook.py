"""Facebook Sayfasi (graph.facebook.com). Reel: video_reels start -> rupload -> finish PUBLISHED (plan R4);
gorunurluk=taslak: reel video_state=DRAFT, gorsel published=false (gizli test; herkese acik degil);
gorsel: /{page}/photos (yerel dosya yuklenir). Kimlik: {"token" (Sayfa token'i), "page_id"}."""
import os
import time

from ortak import Hata

VER = os.environ.get("FB_API_VERSION", "v21.0")
BASE = os.environ.get("FB_GRAPH_BASE", "https://graph.facebook.com").rstrip("/") + "/" + VER
REEL_YORUM_BEKLE = 15   # sn; reel islenirken yorum reddedilebilir (inceleme, dogrulanmadi)
RUPLOAD = os.environ.get("FB_RUPLOAD_BASE", "https://rupload.facebook.com").rstrip("/") + "/video-upload/" + VER


def kimlik_dogrula(http, k):
    j, _ = http.iste("GET", f"{BASE}/me", token=k["token"], params={"fields": "id,name"})
    if str(j.get("id")) != str(k["page_id"]):
        raise Hata("Facebook token bu Sayfaya ait degil")
    return j.get("name", "")


def yayinla(http, k, satir, medya, uyku=time.sleep):
    tur, metin = satir["tur"], satir.get("metin", "")
    m = medya[0]
    taslak = (satir.get("gorunurluk") or "").strip() == "taslak"  # gizli test: herkese acik gonderi YOK
    if tur == "reel":
        j, _ = http.iste("POST", f"{BASE}/{k['page_id']}/video_reels", token=k["token"], data={"upload_phase": "start"})
        vid = j.get("video_id")
        if not vid:
            raise Hata("video_id donmedi")
        veri = m["yerel"].read_bytes()
        j, _ = http.iste("POST", f"{RUPLOAD}/{vid}", token=k["token"], sema="OAuth", govde=veri,
                         basliklar={"offset": "0", "file_size": str(len(veri))})
        if not j.get("success"):
            raise Hata("rupload basarisiz")
        j, _ = http.iste("POST", f"{BASE}/{k['page_id']}/video_reels", token=k["token"],
                         data={"upload_phase": "finish", "video_id": vid, "video_state": "DRAFT" if taslak else "PUBLISHED",
                               "description": metin})
        if not j.get("success"):
            raise Hata("reel finish basarisiz", belirsiz=True)
        return _ilk_yorum(http, k, vid, satir, taslak, uyku, bekle=REEL_YORUM_BEKLE)
    if tur == "gorsel":
        with open(m["yerel"], "rb") as f:
            j, _ = http.iste("POST", f"{BASE}/{k['page_id']}/photos", token=k["token"],
                             data={"message": metin, "published": "false" if taslak else "true"}, dosyalar={"source": f})
        no = j.get("post_id") or j.get("id")
        if not no:
            raise Hata("photos no donmedi", belirsiz=True)
        return _ilk_yorum(http, k, no, satir, taslak)
    raise Hata(f"facebook tur desteklenmiyor: {tur}")


def _ilk_yorum(http, k, no, satir, taslak, uyku=None, bekle=0):
    """ABD denetimi (Serdar 25 Kas): Etsy linki gonderinin ilk yorumu. Gonderi YAYINLANDI; yorum hatasi gonderiyi HATA yapmaz,
    (no, uyari) dondurulur (calis TAMAM yazar + uyari). Taslakta yorum yok."""
    link = (satir.get("link") or "").strip()
    if taslak or not link:
        return no
    if bekle and uyku:
        uyku(bekle)
    try:
        j, _ = http.iste("POST", f"{BASE}/{no}/comments", token=k["token"], data={"message": link})
        if not isinstance(j, dict) or not j.get("id"):
            return no, "ilk yorum no donmedi"
        return no
    except Hata as e:
        return no, f"ilk yorum yazilamadi: {e}"
    except Exception as e:  # gonderi yayinda: hicbir hata satiri HATA yapmamali
        return no, f"ilk yorum yazilamadi: {type(e).__name__}"
