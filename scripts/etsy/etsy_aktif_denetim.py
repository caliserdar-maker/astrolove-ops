#!/usr/bin/env python3
"""
AKTIF ILAN DENETIMI (SALT OKUR) - 5 Eyl 2026 Mo gorevi.

Magazadaki YAYINDA (state=active) olan TUM ilanlari Etsy Open API v3'ten
okur ve her ilan icin hata/eksik arar. Etsy'ye hicbir yazma cagrisi yoktur;
tek "yazma" OAuth token yenilemesidir (Drive'a geri yazilir).

Kaynaklar (ilan basi): listing, images, videos, files (dijital), inventory,
RU cevirisi (varsa), genel sayfa (https://www.etsy.com/listing/<id>) HTTP
durumu, gorsellerin gercek indirilmis olcusu, dijital dosyalarin indirilip
acilabildigi (ZIP testzip, PDF imzasi).

Kurallar - HATA (ilan FAIL) / UYARI (ilan PASS ama not):
  HATA : state != active; baslik bos ya da >140; tag >13 ya da tag >20 kr
         ya da tekrar; aciklama bos/<200 kr ya da yer tutucu (TODO/XXX/{...});
         fiyat <=0 ya da envanter fiyati != ilan fiyati; adet <=0; gorsel 0;
         gorsel indirilemedi; dijital ilanda dosya 0 / boyut 0 / indirilemedi /
         ZIP acilamadi / PDF imzasi yok; ayni baslik iki aktif ilanda;
         who_made/when_made/taxonomy bos.
  UYARI: tag <13; bolum yok; malzeme yok; auto-renew kapali; gorsel uzun
         kenar <2000 px; video var (WP ilanlarinda 0 beklenir); genel sayfa
         200 donmedi (bot engeli olabilir); RU ceviri yok; kisa baslik (<40).
WP (duvar kagidi) ilanlari - WA_WP_DRAFTS_STATE.csv'de listing_id eslesen
ciftler - icin ek HATA: fiyat 3.99, bolum 60120017, dosya 5 (4 ZIP adi
AstroLove_<Pair>_<Ed>.zip + HOW_TO_SET_YOUR_WALLPAPER.pdf), galeri 6 gorsel
SET01->SET03->SET04->SET06->SET07->SET10Y ve her biri Drive'daki kaynakla
piksel eslesmesi (ort fark <= 6), baslik sablonu, tag 13, aciklamada cift adi,
RU ceviri 13 tag.

Kullanim (Actions):
  etsy_aktif_denetim.py --drafts _work/drafts.csv --mock-root _work/mock
      --out _work/ETSY_AKTIF_DENETIM.csv [--rclone-remote gdrive:ASTROLOVE/WALLPAPER/MOCKUP_V2]
"""
import argparse
import csv
import io
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, TIMEOUT, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS, GALLERY_ORDER  # noqa: E402
from wp_media_upload import mock_name  # noqa: E402
from wp_verify_all import PILOT_PAIR, PRICE, SECTION, PDF_NAME, TITLE_TPL, money  # noqa: E402

TITLE_MAX, TAG_MAX, TAG_LEN, DESC_MIN, TITLE_MIN = 140, 13, 20, 200, 40
IMG_MIN_LONG = 2000
PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_0-9]+\}|\[[A-Z _]{3,}\]|\bTODO\b|\bXXX\b|lorem ipsum", re.I)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"}


def fetch(url, tries=3, timeout=120):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=timeout, headers=UA)
            if r.status_code == 200:
                return r.content, 200
            last = r.status_code
        except requests.RequestException:
            last = -1
        time.sleep(2 * (k + 1))
    return None, last


def img_boyut(data):
    try:
        import numpy as np, cv2
        a = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if a is None:
            return None
        return a.shape[1], a.shape[0]
    except Exception:
        return None


def piksel_kiyas(data, src_path):
    """Etsy'den inen gorsel vs Drive kaynagi: ortalama mutlak fark (Etsy yeniden kodlar)."""
    import numpy as np, cv2
    a = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return None
    if a.shape[:2] != b.shape[:2]:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def kucuk_imza(data):
    import numpy as np, cv2
    a = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    if a is None:
        return None
    return cv2.resize(a, (16, 16), interpolation=cv2.INTER_AREA).astype(np.int16)


# ------------------------------------------------------------------ toplama
def aktif_ilanlar(api, shop):
    out, offset = [], 0
    while True:
        r = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": offset}) or {}
        res = r.get("results", [])
        out += res
        if len(res) < 100:
            break
        offset += 100
    # capraz kontrol: yetkili uc (state=active)
    out2, offset = [], 0
    while True:
        r = api.get(f"/shops/{shop}/listings", params={"state": "active", "limit": 100, "offset": offset}) or {}
        res = r.get("results", [])
        out2 += res
        if len(res) < 100:
            break
        offset += 100
    return out, out2


def topla(api, shop, lid):
    d = {}
    d["listing"] = api.get(f"/listings/{lid}", ok404=True) or {}
    d["images"] = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", []),
                         key=lambda x: x.get("rank") or 0)
    d["videos"] = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
    d["files"] = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results", [])
    d["inventory"] = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    d["ru"] = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True)
    return d


def mock_getir(mock_root, remote, pair):
    """WP ciftinin galeri kaynaklarini Drive'dan (rclone) gerektiginde getirir."""
    up = pair.upper()
    hedef = Path(mock_root) / up
    if not hedef.exists() and remote:
        kaynak = f"{remote}/_CANDIDATE/{up}" if pair == PILOT_PAIR else f"{remote}/{up}"
        subprocess.run(["rclone", "copy", kaynak, str(hedef), "--include", "WA_MOCKUP_V2_*_FINAL.jpg"],
                       check=False, capture_output=True)
    return hedef


# ------------------------------------------------------------------ kurallar
def kurallar(d, pair, mock_dir=None, net=True):
    """Donus: (hata[], uyari[], bilgi{})"""
    L, imgs, vids, files, inv, ru = d["listing"], d["images"], d["videos"], d["files"], d["inventory"], d["ru"]
    hata, uyari, bilgi = [], [], {}
    lid = L.get("listing_id")

    # --- durum / metin
    if L.get("state") != "active":
        hata.append(f"state {L.get('state')} (aktif degil)")
    title = (L.get("title") or "").strip()
    if not title:
        hata.append("baslik bos")
    elif len(title) > TITLE_MAX:
        hata.append(f"baslik {len(title)} kr > {TITLE_MAX}")
    elif len(title) < TITLE_MIN:
        uyari.append(f"baslik kisa ({len(title)} kr)")
    if "  " in title:
        uyari.append("baslikta cift bosluk")
    tags = [str(t) for t in (L.get("tags") or [])]
    if len(tags) > TAG_MAX:
        hata.append(f"tag {len(tags)} > {TAG_MAX}")
    elif len(tags) < TAG_MAX:
        (hata if pair else uyari).append(f"tag {len(tags)} < {TAG_MAX}")
    uzun = [t for t in tags if len(t) > TAG_LEN]
    if uzun:
        hata.append(f"tag >{TAG_LEN} kr: {uzun}")
    if len({t.lower() for t in tags}) != len(tags):
        hata.append("tekrarlanan tag")
    desc = L.get("description") or ""
    if len(desc.strip()) < DESC_MIN:
        hata.append(f"aciklama {len(desc.strip())} kr < {DESC_MIN}")
    m = PLACEHOLDER_RE.search(desc) or PLACEHOLDER_RE.search(title)
    if m:
        hata.append(f"yer tutucu kalintisi: '{m.group(0)}'")
    if not (L.get("materials") or []):
        uyari.append("malzeme bos")
    if not L.get("shop_section_id"):
        uyari.append("bolum yok")
    for k in ("who_made", "when_made"):
        if not L.get(k):
            hata.append(f"{k} bos")
    if not L.get("taxonomy_id"):
        hata.append("taxonomy bos")
    if L.get("should_auto_renew") is False:
        uyari.append("auto-renew kapali")
    if L.get("is_private"):
        hata.append("is_private = true")

    # --- fiyat / adet / envanter
    fiyat = money(L.get("price"))
    bilgi["fiyat"] = fiyat
    try:
        fv = float(fiyat)
    except (TypeError, ValueError):
        fv = 0.0
    if fv <= 0:
        hata.append(f"fiyat {fiyat}")
    q = L.get("quantity")
    bilgi["adet"] = q
    if not q or int(q) <= 0:
        hata.append(f"adet {q}")
    try:
        for p in inv.get("products", []):
            for o in p.get("offerings", []):
                ip = money(o.get("price"))
                if ip and fiyat and abs(float(ip) - fv) > 0.005:
                    hata.append(f"envanter fiyati {ip} != {fiyat}")
                if o.get("is_enabled") is False:
                    uyari.append("envanterde kapali teklif")
                if (o.get("quantity") or 0) <= 0:
                    hata.append("envanter adedi 0")
    except (AttributeError, TypeError):
        pass

    # --- gorseller
    bilgi["gorsel"] = len(imgs)
    if not imgs:
        hata.append("gorsel yok")
    ilk_imza = None
    for im in imgs:
        r = im.get("rank")
        w, h = im.get("full_width") or 0, im.get("full_height") or 0
        if max(w, h) and max(w, h) < IMG_MIN_LONG:
            uyari.append(f"rank {r} kucuk ({w}x{h})")
        url = im.get("url_fullxfull") or ""
        if net and url:
            data, st = fetch(url)
            if data is None:
                hata.append(f"rank {r} gorsel indirilemedi ({st})")
                continue
            bh = img_boyut(data)
            if bh is None:
                hata.append(f"rank {r} gorsel cozulemedi")
                continue
            if ilk_imza is None:
                ilk_imza = kucuk_imza(data)
            if pair and mock_dir is not None:
                k = imgs.index(im)
                if k < len(GALLERY_ORDER):
                    src = Path(mock_dir) / mock_name(GALLERY_ORDER[k], pair)
                    if src.exists():
                        f = piksel_kiyas(data, src)
                        if f is None or f > 6.0:
                            hata.append(f"rank {r} {GALLERY_ORDER[k]} kaynakla eslesmiyor (fark {f})")
                    else:
                        uyari.append(f"rank {r} kaynak gorsel Drive'da yok: {src.name}")
        elif not url:
            hata.append(f"rank {r} url yok")
    bilgi["ilk_imza"] = ilk_imza

    # --- video
    bilgi["video"] = len(vids)
    if pair and vids:
        uyari.append(f"video {len(vids)} (WP ilaninda 0 beklenir)")
    for v in vids:
        if v.get("video_state") not in (None, "active"):
            uyari.append(f"video durumu {v.get('video_state')}")

    # --- dijital dosyalar
    bilgi["dosya"] = len(files)
    dijital = (L.get("listing_type") == "download") or bool(L.get("file_data")) or bool(files)
    if dijital and not files:
        hata.append("dijital ilan, dosya yok")
    for f in files:
        ad = str(f.get("filename") or "")
        sz = int(f.get("size_bytes") or f.get("filesize") or 0)
        if sz <= 0 and "size" in str(f):
            hata.append(f"dosya {ad}: boyut 0")
        url = f.get("url") or f.get("download_url") or ""
        if net and url:
            data, st = fetch(url, timeout=180)
            if data is None:
                hata.append(f"dosya {ad}: indirilemedi ({st})")
                continue
            if len(data) == 0:
                hata.append(f"dosya {ad}: 0 bayt")
            if ad.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        kotu = zf.testzip()
                        if kotu:
                            hata.append(f"dosya {ad}: ZIP bozuk ({kotu})")
                        bilgi.setdefault("zip_icerik", {})[ad] = len(zf.namelist())
                except zipfile.BadZipFile:
                    hata.append(f"dosya {ad}: ZIP acilamadi")
            elif ad.lower().endswith(".pdf") and not data.startswith(b"%PDF"):
                hata.append(f"dosya {ad}: PDF imzasi yok")

    # --- WP'ye ozel
    if pair:
        s1, s2 = pair.split("_", 1)
        if fiyat != PRICE:
            hata.append(f"WP fiyat {fiyat} != {PRICE}")
        if int(L.get("shop_section_id") or 0) != SECTION:
            hata.append(f"WP bolum {L.get('shop_section_id')} != {SECTION}")
        adlar = sorted(str(f.get("filename") or "") for f in files)
        bekl = sorted([f"AstroLove_{pair}_{e}.zip" for e in EDITIONS] + [PDF_NAME])
        if adlar != bekl:
            hata.append(f"WP dosyalar {adlar} != beklenen {bekl}")
        if len(imgs) != len(GALLERY_ORDER):
            hata.append(f"WP gorsel {len(imgs)} != {len(GALLERY_ORDER)}")
        if title != TITLE_TPL.format(Sign1=s1, Sign2=s2):
            hata.append("WP baslik sablona uymuyor")
        if not ((f"{s1} & {s2}" in desc) or (f"{s1} and {s2}" in desc)):
            hata.append("WP aciklamada cift adi yok")
        if not ru:
            hata.append("WP RU ceviri yok")
        elif len(ru.get("tags") or []) != TAG_MAX:
            hata.append(f"WP RU tag {len(ru.get('tags') or [])}")
    elif ru is None:
        uyari.append("RU ceviri yok")

    # --- genel sayfa
    if net and lid:
        try:
            r = requests.get(f"https://www.etsy.com/listing/{lid}", headers=UA, timeout=60, allow_redirects=True)
            bilgi["sayfa"] = r.status_code
            if r.status_code != 200:
                uyari.append(f"genel sayfa {r.status_code}")
            elif title and title[:40].lower() not in r.text.lower():
                uyari.append("genel sayfada baslik gorulmedi")
        except requests.RequestException as e:
            uyari.append(f"genel sayfa erisilemedi: {e.__class__.__name__}")
    return hata, uyari, bilgi


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", default="", help="WA_WP_DRAFTS_STATE.csv (pair,listing_id) - WP ilanlarini tanimak icin")
    ap.add_argument("--mock-root", default="", help="WP galeri kaynaklari (cift basi klasor)")
    ap.add_argument("--rclone-remote", default="", help="gerekirse kaynak getirme: gdrive:ASTROLOVE/WALLPAPER/MOCKUP_V2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    pair_of = {}
    if a.drafts and Path(a.drafts).exists():
        with open(a.drafts, newline="", encoding="utf-8") as fh:
            for raw in csv.reader(fh):
                if len(raw) >= 2 and raw[1].strip().isdigit():
                    pair_of[raw[1].strip()] = raw[0].strip()

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    shopinfo = api.get(f"/shops/{shop}", ok404=True) or {}
    log(f"magaza: aktif ilan sayisi (shop) {shopinfo.get('listing_active_count')}, "
        f"diller {shopinfo.get('languages')}")
    aktif, aktif2 = aktif_ilanlar(api, shop)
    ids1 = [str(x.get("listing_id")) for x in aktif]
    ids2 = [str(x.get("listing_id")) for x in aktif2]
    genel_hata = []
    if sorted(ids1) != sorted(ids2):
        genel_hata.append(f"aktif liste tutarsiz: genel uc {len(ids1)}, yetkili uc {len(ids2)} "
                          f"(fark {sorted(set(ids1) ^ set(ids2))})")
    ids = sorted(set(ids1) | set(ids2), key=lambda s: ids1.index(s) if s in ids1 else 10**9)
    if a.limit:
        ids = ids[:a.limit]
    log(f"{len(ids)} aktif ilan denetlenecek (WP eslesen: {sum(1 for i in ids if i in pair_of)})")

    rows, imzalar, basliklar = [], {}, {}
    t0 = time.time()
    for i, lid in enumerate(ids, 1):
        pair = pair_of.get(lid, "")
        d = topla(api, shop, lid)
        mock_dir = mock_getir(a.mock_root, a.rclone_remote, pair) if (pair and a.mock_root) else None
        hata, uyari, bilgi = kurallar(d, pair, mock_dir, net=True)
        title = (d["listing"].get("title") or "").strip()
        basliklar.setdefault(title.lower(), []).append(lid)
        if bilgi.get("ilk_imza") is not None:
            imzalar[lid] = bilgi["ilk_imza"]
        rows.append(dict(listing_id=lid, cift=pair, baslik=title[:80], state=d["listing"].get("state"),
                         fiyat=bilgi.get("fiyat"), adet=bilgi.get("adet"), gorsel=bilgi.get("gorsel"),
                         video=bilgi.get("video"), dosya=bilgi.get("dosya"), tag=len(d["listing"].get("tags") or []),
                         sayfa=bilgi.get("sayfa"), hata=hata, uyari=uyari))
        el = time.time() - t0
        log(f"[{i}/{len(ids)}] {lid} {pair or '-'}: {'FAIL' if hata else 'PASS'} | hata {len(hata)} uyari {len(uyari)} "
            f"| kota {api.remaining} | gecen {el/60:.1f} dk kalan {el/i*(len(ids)-i)/60:.1f} dk")
        for h in hata:
            log(f"    HATA : {h}")
        for u in uyari:
            log(f"    UYARI: {u}")

    # --- ilanlar arasi
    for t, ls in basliklar.items():
        if t and len(ls) > 1:
            for l in ls:
                next(r for r in rows if r["listing_id"] == l)["hata"].append(f"ayni baslik: {ls}")
    try:
        import numpy as np
        ks = list(imzalar)
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                if float(np.abs(imzalar[ks[x]] - imzalar[ks[y]]).mean()) < 3.0:
                    for l in (ks[x], ks[y]):
                        next(r for r in rows if r["listing_id"] == l)["uyari"].append(f"ilk gorsel benzer: {ks[x]}/{ks[y]}")
    except Exception:
        pass

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "cift", "baslik", "state", "fiyat", "adet", "gorsel", "video", "dosya", "tag",
                    "sayfa", "sonuc", "n_hata", "n_uyari", "hata", "uyari"])
        for r in rows:
            w.writerow([r["listing_id"], r["cift"], r["baslik"], r["state"], r["fiyat"], r["adet"], r["gorsel"],
                        r["video"], r["dosya"], r["tag"], r["sayfa"], "FAIL" if r["hata"] else "PASS",
                        len(r["hata"]), len(r["uyari"]), " | ".join(r["hata"]), " | ".join(r["uyari"])])

    n_fail = sum(1 for r in rows if r["hata"])
    lines = [f"## aktif ilan denetimi: {len(rows)} aktif ilan, FAIL {n_fail}, PASS {len(rows) - n_fail}"
             + (f" | GENEL HATA: {'; '.join(genel_hata)}" if genel_hata else ""), "",
             "| listing | cift | sonuc | fiyat | adet | gorsel | video | dosya | tag | sayfa | hata | uyari |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['listing_id']} | {r['cift'] or '-'} | {'FAIL' if r['hata'] else 'PASS'} | {r['fiyat']} | "
                     f"{r['adet']} | {r['gorsel']} | {r['video']} | {r['dosya']} | {r['tag']} | {r['sayfa']} | "
                     f"{' / '.join(r['hata'])[:300]} | {' / '.join(r['uyari'])[:300]} |")
    lines.append(f"\nSONUC {'FAIL' if (n_fail or genel_hata) else 'PASS'}")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 1 if (n_fail or genel_hata) else 0


if __name__ == "__main__":
    sys.exit(main())
