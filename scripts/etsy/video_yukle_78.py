#!/usr/bin/env python3
"""78 POD ilanina v5 kapak videosu yukleme: KURU KOSU (Etsy'ye YAZMA YOK) + APPLY (Serdar acik onayi, plana kilitli).
Video kaynagi TEK: Drive TEMP/POD_VIDEO_V2/<damga>/VIDEO_<CIFT>.mp4 + QC_<CIFT>.json (video_v2_toplu.py, v5 sablonu).

Ilan basina (yalniz GET):
  - state (active disi -> BLOK; updateListing taslagi yayina alir, video adimi updateListing CAGIRMAZ)
  - mevcut videolar (/listings/{id}/videos): Etsy ilan basina 1 video; varsa DEGISTIR (eski video indirilip
    --out/yedek/<listing_id>_<video_id>.mp4 olarak yedeklenir, apply'da once yeni yuklenir sonra eski silinir)
  - yerel video: QC_<CIFT>.json pass, mp4 acilir, 2880x2160, 5-15 sn (Etsy), < 100 MB, ses yok (QC'den)
Durum: YUKLE (videosu yok) | DEGISTIR (eski video var) | BLOK (neden yazilir).
Cikti: PLAN.json (sha256 kilitli) + PLAN.csv + report.md. ETA sayaci: islenen/toplam, gecen, kalan, yuzde.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kotasi: kuru kosu ilan basina 2 GET (listing + videos); rapor bas/son kota ve apply tahmini cagriyi yazar.
Kullanim: video_yukle_78.py --video-dir V --kaynak-bilgi K.json --out OUT [--haric CIFT,CIFT]

APPLY (Serdar onayi 28 Eyl: 75 ilan, kuru KURU_20260928_1359 PASS):
  video_yukle_78.py --video-dir V --out OUT --plan PLAN.json --yedek-liste Y.txt --apply --confirm VIDEO78_YUKLE
  - Plana kilitli: yalniz plandaki YUKLE/DEGISTIR satirlari; video sha256 plandakiyle ayni; canli state active;
    canli video id'leri plandaki eski videolarla birebir ayni; eski videonun yedegi Drive'da (Y.txt) var.
  - KOTA: her ilan BASINDA x-remaining-today >= ILAN_CAGRI_UST + quota-min; yetmezse o ilana HIC baslanmaz,
    o ve kalan ilanlar ATLANDI (yarim ilan birakilmaz).
  - Sira: uploadListingVideo -> geri okuma (yeni video ilanda) -> eski deleteListingVideo -> geri okuma
    (ilanda yalniz yeni video). updateListing CAGRILMAZ; musteriye bildirim yok.
  - Ilk FAIL'de DURUR; kalanlar ATLANDI. report.md: YUKLENDI / ATLANDI / FAIL.

--surum v7 (Merkez 26 Eki, poster video v7b; varsayilan v5 davranisi AYNEN):
  - kaynak TEMP/VIDEO_V7_78/BIRLESIK_<damga>/<CIFT>.mp4 + MANIFEST.csv (--manifest: qc_sonuc PASS, sha256 dosyayla ayni,
    ses akisi yok); 1440x1080; sure 5-15 sn, < 100 MB. Etsy sinirlari (26 Eki okundu): yardim sayfasi 3-15 sn, 100 MB
    (help.etsy.com/hc/en-us/articles/360053206073-How-to-Add-Listing-Videos), satici rehberi 5-15 sn
    (etsy.com/seller-handbook/article/how-to-take-listing-videos-with-your/821069114343); dar olan (5-15) kullanilir.
  - GALERI KAPISI (kuru + apply): --galeri-ilerleme (TEMP/POSTER_GALERI_V10_YUKLE/ILERLEME.json) ilan kaydi durum PASS, set >= hedef,
    canli galeri kimlik kumesi = kayittaki son_ids ve canli rank 1 = son_ids[0] (v10 kapak); degilse BLOK. Kuru +1 GET (images).
    Kuru SONUC PASS yalniz BLOK nedenleri galeri kapisindansa (galeri gruplar halinde biter); baska BLOK nedeni FAIL.
  - kuru eski videoyu INDIRMEZ (KILIT SURESI kurali: kilit altinda toplu indirme yok); URL plana yazilir. Yedek apply is akisinda
    Etsy kilidi ALINMADAN once plan URL'lerinden indirilir, Drive'a yazilir; apply <ilan>_<video_id>.mp4 yedegini listede arar.
  - BLOK satirli plan kullanilabilir (galeri gruplar halinde biter); yalniz YUKLE / DEGISTIR satirlarina dokunulur.
  - yukleme TEK gonderim (post_file tekrar=1); hata / kimliksiz yanitta yeniden gonderilmez: ilan videolari okunur, eski kumede
    olmayan TEK yeni video varsa yuklenmis sayilir, yoksa FAIL (eski video SILINMEZ). Onay kelimesi VIDEO_V7_YUKLE.
  - eski video YALNIZ yeni video video_state "active" ve video_url dolu okununca silinir (islenen / dusen video ilani videosuz
    birakmasin; API ListingVideo.video_state); sure dolarsa FAIL, eski kalir. DELETE 404 = zaten silinmis (son okuma dogrular).
  - SONUC.json her ilandan sonra yazilir (kosu kesilirse yarim ilan kaydi kalir). Sifir yazilacak satirli apply FAIL.
  - Kilit oncesi Drive indirmeleri (BIRLESIK, yedek) is akisinda kilit_bekle'den ONCE; kilit_bekle olusturma sirasina gore
    bekledigi icin sonradan acilan Etsy kosulari bu indirmeleri de bekler (bilinen; indirme ~1-2 dk).

--surum v7d (Serdar onayi 30 Eki; v7 kapilarinin hepsi AYNEN, yalniz kaynak ve galeri kapisi farkli):
  - kaynak TEMP/VIDEO_V7_DUZELTME/<damga>/TAM78/<CIFT>.mp4 (Serdar onayli v7d) + ayri klasordeki MANIFEST
    (TEMP/VIDEO_V7D_YUKLE_KAYNAK/<damga>/MANIFEST.csv; --manifest-uret ile, Etsy'siz). MANIFEST satiri ayrica listing_id, dosya,
    bayt, genislik, yukseklik ile de olcumle ayni olmali; MANIFEST cift / listing_id kumesi ilan listesiyle iki yonlu birebir.
  - plan kilidi: PLAN.json kaynak.klasor (TAM78 klasoru) + kaynak.manifest_sha256; apply ayni MANIFEST ister.
  - GALERI KAPISI: yalniz galeri v11 ILERLEME (TEMP/POSTER_GALERI_V11_YUKLE/ILERLEME.json) ilan kaydi: durum PASS, hedef 10,
    son_ids dolu (hedef kadar), set >= hedef; canli rank 1 = son_ids[0] ve canli kimlik kumesi = son_ids. v10 kaydi ve SONUC.csv
    kullanilmaz. Gecmeyen ilan BLOK "galeri bekliyor" (kuru SONUC'u bozmaz; apply'da ATLANDI).
  - --manifest-uret: Etsy'ye istek YOK (token okunmaz). --video-dir (TAM78 mp4), --qc-csv (TAM78/RAPOR/QC.csv), --ids ->
    <out>/MANIFEST.csv + OLCUM.md + OLCUM.json. mp4 adlari, QC.csv ve ilan listesi cift kumeleri birebir degilse, ya da
    1440x1080 / QC PASS / ses yok / 5-15 sn / < 100 MB disi video varsa MANIFEST YAZILMAZ (DUR, cikis 1).
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_cover_from_video import video_url, videos  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[2]
BEKLENEN = 78
VIDEO_BOYUT = (2880, 2160)
SURE_MIN, SURE_MAX = 5.0, 15.0     # Etsy ilan videosu
MB_MAX = 100.0
CAGRI_ILAN = 6                      # apply tahmini: state + video oku, yukle, geri oku, (eski sil + geri oku)
KURU_CAGRI_ILAN = 2                 # kuru: listing + videos (GET)
ONAY = "VIDEO78_YUKLE"
OKUMA_DENEME, OKUMA_BEKLE = 6, 5    # geri okuma: en fazla 6 x 5 sn
# ilan basina en kotu durum: 2 GET + 3 POST(file) denemesi + 6 okuma + 3 DELETE denemesi + 6 okuma
ILAN_CAGRI_UST = 2 + 3 + OKUMA_DENEME + 3 + OKUMA_DENEME
# v7: GET'ler (state, videos, images, hata sonrasi okuma, active bekleme, son okuma) _call icinde 5xx/429'da 3'e kadar denenir;
# POST 401 yenilemesiyle 2; DELETE 3. Tavan en kotu durumu sayar (ilan ortasinda kota sert tabani devreye girmesin).
OKUMA_DENEME_V7, OKUMA_BEKLE_V7 = 12, 10   # yeni video active olana dek ~2 dk (eski silinmeden once)
ILAN_CAGRI_UST_V7 = 3 * (3 + OKUMA_DENEME_V7 + OKUMA_DENEME_V7 + OKUMA_DENEME) + 2 + 3
PROFIL = {"v5": dict(boyut=VIDEO_BOYUT, ad="VIDEO_{c}.mp4", onay=ONAY, kuru_cagri=KURU_CAGRI_ILAN, ust=ILAN_CAGRI_UST),
          "v7": dict(boyut=(1440, 1080), ad="{c}.mp4", onay="VIDEO_V7_YUKLE", kuru_cagri=3, ust=ILAN_CAGRI_UST_V7),
          "v7d": dict(boyut=(1440, 1080), ad="{c}.mp4", onay="VIDEO_V7_YUKLE", kuru_cagri=3, ust=ILAN_CAGRI_UST_V7)}
V7 = ("v7", "v7d")                      # v7 yolu (tek gonderim, active bekleme, galeri kapisi); v7d yalniz kaynak + galeri v11
GALERI_AD = {"v7": "v10", "v7d": "v11"}
HEDEF_V11 = 10
MANIFEST_ALAN = ["cift", "listing_id", "dosya", "sha256", "bayt", "genislik", "yukseklik", "sure_sn", "fps", "qc_sonuc", "ses_akisi"]


def surum(a):
    return getattr(a, "surum", "v5") or "v5"


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def video_bilgi(p):
    import cv2
    v = cv2.VideoCapture(str(p))
    w, h = int(v.get(cv2.CAP_PROP_FRAME_WIDTH)), int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n, fps = int(v.get(cv2.CAP_PROP_FRAME_COUNT)), v.get(cv2.CAP_PROP_FPS)
    v.release()
    return {"w": w, "h": h, "kare": n, "fps": round(fps, 2), "sure": round(n / fps, 2) if fps else 0.0}


def yerel_kontrol(vdir, c, sr="v5", manifest=None, lid=None):
    """(bilgi, sorunlar) - yerel video + QC json (v5) ya da MANIFEST satiri (v7 BIRLESIK, v7d TAM78 kaynak MANIFEST)."""
    pr = PROFIL[sr]
    p, q = vdir / pr["ad"].format(c=c), vdir / f"QC_{c}.json"
    if not p.is_file():
        return {}, [f"video yok ({p.name})"]
    b = {"dosya": p.name, "bayt": p.stat().st_size, "mb": round(p.stat().st_size / 1e6, 2), "sha256": sha(p)}
    b.update(video_bilgi(p))
    sorun = []
    if sr in V7:
        m = (manifest or {}).get(c) or {}
        if m.get("qc_sonuc") != "PASS" or m.get("sha256") != b["sha256"] or str(m.get("ses_akisi")) != "False":
            sorun.append(f"MANIFEST: QC {m.get('qc_sonuc') or 'yok'} / sha256 {'ayni' if m.get('sha256') == b['sha256'] else 'farkli'} / "
                         f"ses {m.get('ses_akisi')}")
        if sr == "v7d":
            fark = [k for k, v in (("listing_id", lid), ("dosya", p.name), ("bayt", b["bayt"]), ("genislik", b["w"]),
                                   ("yukseklik", b["h"])) if str(m.get(k)) != str(v)]
            if fark:
                sorun.append(f"MANIFEST v7d alanlari olcumle farkli: {fark}")
    else:
        qc = json.loads(q.read_text()) if q.is_file() else {}
        if not qc.get("pass"):
            sorun.append(f"QC {'FAIL' if qc else 'yok'}: {str(qc.get('olcum', ''))[:120]}")
    if (b["w"], b["h"]) != pr["boyut"]:
        sorun.append(f"cozunurluk {b['w']}x{b['h']}")
    if not SURE_MIN <= b["sure"] <= SURE_MAX:
        sorun.append(f"sure {b['sure']} sn (Etsy {SURE_MIN:g}-{SURE_MAX:g})")
    if b["mb"] >= MB_MAX:
        sorun.append(f"{b['mb']} MB >= {MB_MAX:g}")
    return b, sorun


def kuru(a, api, out, satirlar):
    vdir = pathlib.Path(a.video_dir)
    yedek = out / "yedek"
    yedek.mkdir(parents=True, exist_ok=True)
    plan, t0, kota_bas = [], time.time(), None
    sr = surum(a)
    for i, s in enumerate(satirlar, 1):
        lid, c = str(s["listing_id"]), s["cift"]
        b, neden = yerel_kontrol(vdir, c, sr, getattr(a, "manifest_rows", None), lid)
        st = (api.get(f"/listings/{lid}", ok404=True) or {}).get("state")
        if kota_bas is None and api.remaining is not None:
            kota_bas = int(api.remaining) + 1
        vid = videos(api, lid)
        row = {"listing_id": lid, "cift": c, "state": st, "video": b, "eski_video": [
            {"video_id": v.get("video_id"), "state": v.get("video_state"), "url": video_url(v)} for v in vid],
            "durum": "DEGISTIR" if vid else "YUKLE", "neden": ""}
        if st != "active":
            neden.append(f"state {st}")
        if len(vid) > 1:
            neden.append(f"{len(vid)} video (beklenen en fazla 1)")
        if sr in V7:
            g_neden = []
            row["kapak_id"] = GALERI_KAPI[sr](api, lid, (a.galeri or {}).get(lid), g_neden)
            row["galeri_bekliyor"] = bool(g_neden) and not neden
            neden += g_neden
            for v in row["eski_video"]:
                if not v.get("url"):
                    neden.append(f"eski video {v['video_id']} URL yok (yedek alinamaz)")
                v["yedek"] = f"{lid}_{v['video_id']}.mp4"
        for v in ([] if sr in V7 else row["eski_video"]):
            yol = yedek / f"{lid}_{v['video_id']}.mp4"
            try:
                r = requests.get(v["url"], timeout=120)
                r.raise_for_status()
                yol.write_bytes(r.content)
                if yol.stat().st_size < 10000:
                    raise ValueError(f"{yol.stat().st_size} bayt")
                v.update({"yedek": yol.name, "bayt": yol.stat().st_size, "sha256": sha(yol)})
            except Exception as e:  # noqa: BLE001
                neden.append(f"eski video yedeklenemedi ({v['video_id']}): {e}")
                yol.unlink(missing_ok=True)
        if neden:
            row["durum"], row["neden"] = "BLOK", "; ".join(neden)
        plan.append(row)
        gec = time.time() - t0
        log(f"[{i}/{len(satirlar)}] {lid} {c} {row['durum']} {row['neden']} | eski video {len(vid)} | "
            f"gecen {gec:.0f}s | kalan ~{gec / i * (len(satirlar) - i):.0f}s | %{i * 100 // len(satirlar)} | kota {api.remaining}")

    say = {d: sum(r["durum"] == d for r in plan) for d in ("YUKLE", "DEGISTIR", "BLOK")}
    ok = say["BLOK"] == 0 and len(plan) == BEKLENEN - len(a.haric)
    if sr in V7:   # galeri gruplar halinde biter: yalniz galeri kapisi BLOK'u gecerli; baska BLOK nedeni FAIL
        say["GALERI_BEKLIYOR"] = sum(1 for r in plan if r["durum"] == "BLOK" and r.get("galeri_bekliyor"))
        ok = len(plan) == BEKLENEN - len(a.haric) and say["BLOK"] == say["GALERI_BEKLIYOR"]
    (out / "PLAN.json").write_text(json.dumps({"olusturma": simdi(), "surum": sr, "kaynak": a.kaynak, "satirlar": plan},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["listing_id", "cift", "durum", "neden", "state", "eski_video_id", "video", "mb", "sure", "sha256"])
        for r in plan:
            v = r["video"]
            wr.writerow([r["listing_id"], r["cift"], r["durum"], r["neden"], r["state"],
                         " ".join(str(x["video_id"]) for x in r["eski_video"]), v.get("dosya"), v.get("mb"),
                         v.get("sure"), v.get("sha256")])
    kota = int(api.remaining) if api.remaining is not None else None
    gerek = (say["YUKLE"] + say["DEGISTIR"]) * (CAGRI_ILAN + (1 if sr in V7 else 0))
    mbs = [r["video"]["mb"] for r in plan if r["video"]]
    kb = a.kaynak or {}
    sat = [f"# VIDEO78 yukleme: KURU KOSU ({simdi()}) - Etsy'ye yazma YOK", "",
           f"- YUKLE {say['YUKLE']} | DEGISTIR {say['DEGISTIR']} | BLOK {say['BLOK']}"
           f"{' (galeri ' + GALERI_AD[sr] + ' bekliyor ' + str(say['GALERI_BEKLIYOR']) + ', diger ' + str(say['BLOK'] - say['GALERI_BEKLIYOR']) + ')' if sr in V7 else ''}"
           f" | toplam {len(plan)} | "
           f"SONUC: {'PASS' if ok else 'FAIL'}",
           f"- Haric (Serdar): {', '.join(a.haric) or '-'} | Kaynak: {kb.get('klasor')} | {kb.get('ozet')} | video {len(mbs)} dosya, "
           f"{min(mbs, default=0)}-{max(mbs, default=0)} MB",
           f"- Etsy kota: kuru kosu basinda ~{kota_bas}, sonunda {kota} (kuru ~{PROFIL[sr]['kuru_cagri'] * len(plan)} cagri, "
           f"{PROFIL[sr]['kuru_cagri']}/ilan) | apply tahmini ~{gerek} cagri | ilan basi en kotu {PROFIL[sr]['ust']} | "
           f"{'yeterli' if kota is None or kota - gerek >= a.quota_min else 'YETERSIZ'}",
           (f"- Eski video yedegi: {sum(1 for r in plan for v in r['eski_video'] if v.get('yedek'))} dosya (out/yedek)" if sr == "v5" else
            f"- Eski video: {sum(len(r['eski_video']) for r in plan)} (kuru indirmez; apply is akisi Etsy kilidinden ONCE plan URL'lerinden "
            f"indirir)"),
           f"- Apply (ayri adim, Serdar onayi): uploadListingVideo (name={PROFIL[sr]['ad'].format(c='<CIFT>')}); DEGISTIR'de yeni yuklenip "
           "geri okunduktan sonra eski deleteListingVideo; updateListing CAGRILMAZ; musteriye bildirim yok.", ""]
    engel = [r for r in plan if r["durum"] == "BLOK"]
    if engel:
        sat += ["## BLOK", ""] + [f"- {r['listing_id']} {r['cift']}: {r['neden']}" for r in engel] + [""]
    sat += ["## Plan", "", "| # | listing_id | cift | durum | state | eski video | video | MB | sn |",
            "|---|---|---|---|---|---|---|---|---|"]
    sat += [f"| {j} | {r['listing_id']} | {r['cift']} | {r['durum']} | {r['state']} | "
            f"{' '.join(str(x['video_id']) for x in r['eski_video']) or '-'} | {r['video'].get('dosya', '-')} | "
            f"{r['video'].get('mb', '-')} | {r['video'].get('sure', '-')} |" for j, r in enumerate(plan, 1)]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat[2:7]:
        log(x)
    return ok


def galeri_kapisi(api, lid, kayit, neden):
    """v7: galeri v10 ILERLEME kaydi PASS ve canli rank 1 = kayittaki kapak (son_ids[0]). -> canli kapak id"""
    g = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [], key=lambda x: x.get("rank") or 0)
    ids = [str(x.get("listing_image_id")) for x in g]
    kapak = g[0].get("listing_image_id") if g else None
    k = kayit or {}
    son = [str(x) for x in k.get("son_ids") or []]
    if k.get("durum") != "PASS" or not son or int(k.get("set") or 0) < int(k.get("hedef") or 9):
        neden.append(f"galeri v10 kaydi PASS degil ({k.get('durum') or 'kayit yok'}, set {k.get('set')}/{k.get('hedef')})")
    elif str(kapak) != son[0]:
        neden.append(f"canli kapak {kapak} galeri v10 kapagi {son[0]} degil")
    elif set(ids) != set(son):
        neden.append(f"canli galeri ({len(ids)} gorsel) galeri v10 kaydindan farkli")
    return kapak


def galeri_kapisi_v11(api, lid, kayit, neden):
    """v7d: yalniz galeri v11 ILERLEME kaydi (durum PASS, hedef 10, son_ids hedef kadar, set >= hedef) + canli rank 1 = son_ids[0]
    + canli kimlik kumesi = son_ids. v10 kaydi / SONUC.csv kullanilmaz. -> canli kapak id"""
    g = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [], key=lambda x: x.get("rank") or 0)
    ids = [str(x.get("listing_image_id")) for x in g]
    kapak = g[0].get("listing_image_id") if g else None
    k = kayit or {}
    son = [str(x) for x in k.get("son_ids") or []]
    try:
        hedef, kset = int(k.get("hedef") or 0), int(k.get("set") or 0)
    except (TypeError, ValueError):
        hedef, kset = 0, 0
    if k.get("durum") != "PASS" or hedef != HEDEF_V11 or len(son) != hedef or kset < hedef:
        neden.append(f"galeri v11 kaydi PASS degil ({k.get('durum') or 'kayit yok'}, set {k.get('set')}/{k.get('hedef')}, "
                     f"son_ids {len(son)}; beklenen hedef {HEDEF_V11})")
    elif str(kapak) != son[0]:
        neden.append(f"canli kapak {kapak} galeri v11 kapagi {son[0]} degil")
    elif set(ids) != set(son):
        neden.append(f"canli galeri ({len(ids)} gorsel) galeri v11 kaydindan farkli")
    return kapak


GALERI_KAPI = {"v7": galeri_kapisi, "v7d": galeri_kapisi_v11}


def yukle_tek(api, shop, lid, p, eski):
    """v7: tek gonderim; hata / kimliksiz yanitta yeniden gonderilmez, ilan okunur: eski kumede olmayan TEK video -> yuklenmis."""
    try:
        with open(p, "rb") as fh:
            yv = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (p.name, fh, "video/mp4")},
                               data={"name": p.name}, tekrar=1)
        yeni = str((yv or {}).get("video_id") or "")
        if yeni and yeni not in eski:
            return yeni
        hata = f"yanit kimligi {yeni or 'bos'}"
    except SystemExit as e:
        if str(e.code).startswith("DUR: kota"):   # istek gonderilmedi
            raise
        hata = str(e.code)[:150]
    except Exception as e:  # noqa: BLE001 zaman asimi / baglanti: yukleme olmus olabilir
        hata = str(e)[:150]
    ids, _ = _bekle(api, lid, lambda x: bool(set(x) - set(eski)), OKUMA_DENEME_V7, OKUMA_BEKLE_V7)   # gec gorunen yukleme
    yeni = sorted(set(ids or []) - set(eski))
    if len(yeni) == 1:
        log(f"    yukleme hatasi ({hata}) ama ilanda yeni video {yeni[0]}: yuklenmis sayildi, tekrar yok")
        return yeni[0]
    raise RuntimeError(f"yukleme hatasi ({hata}); ilanda yeni video {yeni or 'yok'}; tekrar gonderilmedi, eski SILINMEDI")


def _vid_idler(api, lid):
    return sorted(str(v.get("video_id")) for v in videos(api, lid))


def _bekle(api, lid, kosul, deneme=None, bekle=None):
    deneme, bekle = deneme or OKUMA_DENEME, OKUMA_BEKLE if bekle is None else bekle
    ids = None
    for n in range(deneme):
        ids = _vid_idler(api, lid)
        if kosul(ids):
            return ids, True
        if n < deneme - 1:
            time.sleep(bekle)
    return ids, False


def _aktif(api, lid, yeni):
    """v7: yeni video listede, video_state active ve video_url dolu olana dek okur. -> (ids, ok, son durum)"""
    ids, durum = [], "yok"
    for n in range(OKUMA_DENEME_V7):
        vs = videos(api, lid)
        ids = sorted(str(v.get("video_id")) for v in vs)
        y = next((v for v in vs if str(v.get("video_id")) == yeni), None)
        durum = (y or {}).get("video_state") or "yok"
        if y and durum == "active" and video_url(y):
            return ids, True, durum
        if n < OKUMA_DENEME_V7 - 1:
            time.sleep(OKUMA_BEKLE_V7)
    return ids, False, durum


def kota(api):
    return int(api.remaining) if api.remaining is not None else None


def ses_akisi(p):
    """ffprobe ile ses akisi var mi (True / False). ffprobe yoksa ya da okunamazsa None (MANIFEST yazilmaz)."""
    import shutil
    import subprocess
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(p)], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return any(x.get("codec_type") == "audio" for x in json.loads(r.stdout).get("streams") or [])
    except ValueError:
        return None


def manifest_uret(a):
    """v7d kaynak MANIFEST'i (Etsy'ye istek YOK). Doner: cikis kodu (0 = MANIFEST yazildi)."""
    vdir, out = pathlib.Path(a.video_dir), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ilan = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    qc = list(csv.DictReader(open(a.qc_csv, encoding="utf-8")))
    mp4 = sorted(x.stem for x in vdir.glob("*.mp4"))
    k_ilan, k_qc = [r["cift"] for r in ilan], [r["cift"] for r in qc]
    lids = [str(r["listing_id"]) for r in ilan]
    dur = []
    for ad, kume in (("ilan listesi", k_ilan), ("QC.csv", k_qc), ("mp4", mp4)):
        if len(kume) != BEKLENEN or len(set(kume)) != len(kume):
            dur.append(f"{ad}: {len(kume)} kayit, tekil {len(set(kume))} (beklenen {BEKLENEN})")
    if len(set(lids)) != len(lids):
        dur.append("ilan listesinde tekrarlanan listing_id")
    for ad, kume in (("QC.csv", k_qc), ("mp4", mp4)):
        if set(kume) != set(k_ilan):
            dur.append(f"{ad} ile ilan listesi farkli: eksik {sorted(set(k_ilan) - set(kume))[:5]}, fazla {sorted(set(kume) - set(k_ilan))[:5]}")
    qcs = {r["cift"]: r for r in qc}
    rows, t0 = [], time.time()
    for i, r in enumerate(ilan, 1):
        c, p = r["cift"], vdir / f"{r['cift']}.mp4"
        if not p.is_file():
            continue
        b = video_bilgi(p)
        ses = ses_akisi(p)
        rows.append({"cift": c, "listing_id": str(r["listing_id"]), "dosya": p.name, "sha256": sha(p), "bayt": p.stat().st_size,
                     "genislik": b["w"], "yukseklik": b["h"], "sure_sn": b["sure"], "fps": b["fps"],
                     "qc_sonuc": (qcs.get(c) or {}).get("sonuc") or "yok", "ses_akisi": ses})
        gec = time.time() - t0
        if i % 13 == 0 or i == len(ilan):
            log(f"[{i}/{len(ilan)}] olcum | gecen {gec:.0f}s | kalan ~{gec / i * (len(ilan) - i):.0f}s | %{i * 100 // len(ilan)}")
    kotu = []
    for x in rows:
        n = []
        if (x["genislik"], x["yukseklik"]) != PROFIL["v7d"]["boyut"]:
            n.append(f"cozunurluk {x['genislik']}x{x['yukseklik']}")
        if x["qc_sonuc"] != "PASS":
            n.append(f"QC {x['qc_sonuc']}")
        if x["ses_akisi"] is not False:
            n.append(f"ses {x['ses_akisi']}")
        if not SURE_MIN <= x["sure_sn"] <= SURE_MAX:
            n.append(f"sure {x['sure_sn']}")
        if x["bayt"] / 1e6 >= MB_MAX:
            n.append(f"{x['bayt'] / 1e6:.2f} MB")
        if n:
            kotu.append(f"{x['cift']}: {', '.join(n)}")
    if len({x['sha256'] for x in rows}) != len(rows):
        dur.append("tekrarlanan sha256 (iki cift ayni video)")

    def dag(f):
        from collections import Counter
        return dict(sorted(Counter(str(f(x)) for x in rows).items()))
    bayt = sorted(x["bayt"] for x in rows)
    ozet = {"video": len(rows), "cozunurluk": dag(lambda x: f"{x['genislik']}x{x['yukseklik']}"),
            "sure_sn": dag(lambda x: x["sure_sn"]), "fps": dag(lambda x: x["fps"]), "qc_sonuc": dag(lambda x: x["qc_sonuc"]),
            "ses_akisi": dag(lambda x: x["ses_akisi"]),
            "bayt_min": bayt[0] if bayt else None, "bayt_medyan": bayt[len(bayt) // 2] if bayt else None,
            "bayt_max": bayt[-1] if bayt else None, "dur": dur, "kotu": kotu}
    ok = not dur and not kotu and len(rows) == BEKLENEN
    if ok:
        with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=MANIFEST_ALAN)
            w.writeheader()
            w.writerows(rows)
        yaz = list(csv.DictReader(open(out / "MANIFEST.csv", encoding="utf-8")))   # iki yonlu birebir: yazilan dosyayi geri oku
        if {(x["cift"], x["listing_id"]) for x in yaz} != {(r["cift"], str(r["listing_id"])) for r in ilan} or \
                {x["dosya"][:-4] for x in yaz} != set(mp4):
            (out / "MANIFEST.csv").unlink()
            ok, ozet["dur"] = False, ozet["dur"] + ["yazilan MANIFEST ilan listesi / mp4 adlariyla birebir degil"]
    ozet["sonuc"] = "PASS" if ok else "DUR"
    (out / "OLCUM.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sat = [f"PASS video {len(rows)} / {BEKLENEN} | MANIFEST {'yazildi' if ok else 'YAZILMADI (DUR)'}" if ok else
           f"DUR video {len(rows)} / {BEKLENEN} | MANIFEST YAZILMADI", "",
           f"- cozunurluk: {ozet['cozunurluk']}", f"- sure_sn: {ozet['sure_sn']}", f"- fps: {ozet['fps']}",
           f"- bayt: en az {ozet['bayt_min']}, medyan {ozet['bayt_medyan']}, en cok {ozet['bayt_max']}",
           f"- QC.csv sonuc: {ozet['qc_sonuc']}", f"- ses akisi (ffprobe): {ozet['ses_akisi']}",
           f"- DUR nedenleri: {'; '.join(dur) or 'yok'}", f"- kapi disi video: {'; '.join(kotu) or 'yok'}"]
    (out / "OLCUM.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat:
        log(x)
    return 0 if ok else 1


def apply(a, api, out, plan):
    """Plana kilitli yukleme. Doner: (sonuclar, sonuc_ok)."""
    shop = os.environ["ETSY_SHOP_ID"]
    vdir = pathlib.Path(a.video_dir)
    yedekler = set(pathlib.Path(a.yedek_liste).read_text().split()) if a.yedek_liste else set()
    satir = [r for r in plan["satirlar"] if r["durum"] in ("YUKLE", "DEGISTIR")]
    sr = surum(a)
    ust = PROFIL[sr]["ust"]
    esik = ust + a.quota_min
    if api.remaining is None:
        api.get(f"/shops/{shop}")                    # salt okur: kota basligini almak icin
    kota_bas = kota(api)
    sonuc, dur, t0 = [], "", time.time()
    dokunulmadi = [r for r in plan["satirlar"] if r["durum"] not in ("YUKLE", "DEGISTIR")]

    def sonuc_yaz():   # her ilandan sonra (kosu kesilirse yarim ilan kaydi kalir)
        (out / "SONUC.json").write_text(json.dumps({"bitis": simdi(), "plan": a.kaynak.get("plan", a.plan), "sonuc": sonuc,
                                                    "dokunulmadi": [[x["listing_id"], x["cift"], x["neden"]] for x in dokunulmadi]},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    for i, r in enumerate(satir, 1):
        lid, c = str(r["listing_id"]), r["cift"]
        eski = sorted(str(v["video_id"]) for v in r["eski_video"])
        rec = {"listing_id": lid, "cift": c, "eski_video": " ".join(eski) or "-", "yeni_video": "-",
               "sonuc": "", "neden": "", "kota": None}
        sonuc.append(rec)
        if dur:
            rec["sonuc"], rec["neden"] = "ATLANDI", dur
            continue
        k = kota(api)
        if k is not None and k < esik:
            dur = f"kota {k} < {esik} (ilan basi ust {ust} + taban {a.quota_min}); ilana baslanmadi"
            rec["sonuc"], rec["neden"] = "ATLANDI", dur
            continue
        try:
            neden = []
            if c in a.haric:
                neden.append("haric listesinde")
            p = vdir / PROFIL[sr]["ad"].format(c=c)
            if not p.is_file() or sha(p) != r["video"].get("sha256"):
                neden.append("yerel video yok ya da sha256 plandan farkli")
            for v in r["eski_video"]:
                if v.get("yedek") not in yedekler:
                    neden.append(f"eski video {v['video_id']} yedegi Drive'da yok")
            if not neden:
                st = (api.get(f"/listings/{lid}", ok404=True) or {}).get("state")
                if st != "active":
                    neden.append(f"state {st} (active degil)")
                canli = _vid_idler(api, lid)
                if canli != eski:
                    neden.append(f"canli video {canli} != plan {eski}")
                if sr in V7:
                    g_neden = []
                    kapak = GALERI_KAPI[sr](api, lid, (a.galeri or {}).get(lid), g_neden)
                    if g_neden or kapak != r.get("kapak_id"):
                        neden.append("galeri: " + ("; ".join(g_neden) or f"canli kapak {kapak} plandaki {r.get('kapak_id')} degil"))
                    if sr == "v7d" and g_neden and len(neden) == 1:   # yalniz galeri v11 kapisi: hata degil, galeri bekliyor
                        rec["sonuc"], rec["neden"] = "GALERI_BEKLIYOR", neden[0] + " (yazma yok)"
                        continue
            if neden:
                rec["sonuc"], rec["neden"] = "ATLANDI", "; ".join(neden) + " (yazma yok)"
                continue
            if sr in V7:
                yeni = yukle_tek(api, shop, lid, p, eski)
            else:
                with open(p, "rb") as fh:
                    yv = api.post_file(f"/shops/{shop}/listings/{lid}/videos",
                                       files={"video": (p.name, fh, "video/mp4")}, data={"name": p.name})
                yeni = str(yv.get("video_id") or "")
            if not yeni or yeni in eski:
                raise RuntimeError(f"yeni video id gecersiz ({yeni or 'bos'})")
            rec["yeni_video"] = yeni
            if sr in V7:
                ids, ok, vd = _aktif(api, lid, yeni)
                if not ok:
                    raise RuntimeError(f"yeni video {yeni} active olmadi (video_state {vd}, ilanda {ids}); eski SILINMEDI")
            else:
                ids, ok = _bekle(api, lid, lambda x: yeni in x)
                if not ok:
                    raise RuntimeError(f"yukleme geri okuma: yeni {yeni} ilanda yok {ids} (eski SILINMEDI)")
            for e in eski:
                if e in ids:
                    if sr in V7:
                        api.delete(f"/shops/{shop}/listings/{lid}/videos/{e}", ok404=True)
                    else:
                        api.delete(f"/shops/{shop}/listings/{lid}/videos/{e}")
            ids, ok = _bekle(api, lid, lambda x: x == [yeni])
            if not ok:
                raise RuntimeError(f"son okuma: ilanda {ids}, beklenen yalniz [{yeni}]")
            rec["sonuc"] = "YUKLENDI"
        except (Exception, SystemExit) as e:  # noqa: BLE001 - post_file/delete SystemExit atar
            rec["sonuc"], rec["neden"] = "FAIL", str(e)[:300]
            dur = f"{lid} {c} FAIL sonrasi durdu"
        finally:
            rec["kota"] = kota(api)
            sonuc_yaz()
            gec = time.time() - t0
            log(f"[{i}/{len(satir)}] {lid} {c} {rec['sonuc']} {rec['neden']} | gecen {gec:.0f}s | "
                f"kalan ~{gec / i * (len(satir) - i):.0f}s | %{i * 100 // len(satir)} | kota {rec['kota']}")

    say = {d: sum(x["sonuc"] == d for x in sonuc) for d in ("YUKLENDI", "ATLANDI", "FAIL", "GALERI_BEKLIYOR")}
    ok = say["YUKLENDI"] + say["GALERI_BEKLIYOR"] == len(satir) and (say["YUKLENDI"] > 0 or sr == "v5")   # yazilan yoksa PASS denmez
    sonuc_yaz()
    sat = [f"# VIDEO78 yukleme: APPLY ({simdi()})", "",
           f"- YUKLENDI {say['YUKLENDI']} | ATLANDI {say['ATLANDI']} | FAIL {say['FAIL']} | galeri bekliyor {say['GALERI_BEKLIYOR']} | toplam {len(satir)} | "
           f"SONUC: {'PASS' if ok else 'EKSIK'}",
           f"- Plan: {a.kaynak.get('plan', a.plan)} ({plan.get('olusturma')}) | Kaynak: {(plan.get('kaynak') or {}).get('klasor')} | "
           f"Haric: {', '.join(a.haric) or '-'}",
           f"- Etsy kota: basta {kota_bas}, sonda {kota(api)} | ilan basi esik {esik} (ust {ust} + taban "
           f"{a.quota_min}); kota yetmezse ilana baslanmaz",
           f"- Durma nedeni: {dur or '-'}",
           "- uploadListingVideo + (geri okuma sonrasi) eski deleteListingVideo; updateListing CAGRILMADI; "
           "musteriye bildirim yok. Eski video yedegi: TEMP/VIDEO78_YEDEK_<plan damgasi>/", "",
           "| # | listing_id | cift | sonuc | eski video | yeni video | kota | neden |", "|---|---|---|---|---|---|---|---|"]
    sat += [f"| {j} | {x['listing_id']} | {x['cift']} | {x['sonuc']} | {x['eski_video']} | {x['yeni_video']} | "
            f"{x['kota']} | {x['neden'] or '-'} |" for j, x in enumerate(sonuc, 1)]
    if dokunulmadi:
        sat += ["", f"## DOKUNULMADI (plan BLOK, {len(dokunulmadi)})", ""] + [f"- {x['listing_id']} {x['cift']}: {x['neden']}"
                                                                          for x in dokunulmadi]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat[2:6]:
        log(x)
    return sonuc, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--video-dir", required=True)
    ap.add_argument("--kaynak-bilgi", help="JSON: klasor, ozet")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=10)  # kota siniri 10 (Serdar 15 ve 24 Eki)
    ap.add_argument("--haric", default="", help="virgullu cift listesi (plana alinmaz / apply'da dokunulmaz)")
    ap.add_argument("--plan", help="apply: kuru kosunun PLAN.json'u")
    ap.add_argument("--yedek-liste", help="apply: Drive VIDEO78_YEDEK_<plan> dosya adlari (satir basi bir)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--surum", choices=sorted(PROFIL), default="v5",
                    help="v5 (varsayilan, 2880x2160) | v7 (1440x1080, BIRLESIK) | v7d (1440x1080, TAM78 + kaynak MANIFEST)")
    ap.add_argument("--manifest", help="v7: BIRLESIK MANIFEST.csv | v7d: TEMP/VIDEO_V7D_YUKLE_KAYNAK/<damga>/MANIFEST.csv")
    ap.add_argument("--galeri-ilerleme", help="v7: TEMP/POSTER_GALERI_V10_YUKLE/ILERLEME.json | v7d: TEMP/POSTER_GALERI_V11_YUKLE/ILERLEME.json")
    ap.add_argument("--manifest-uret", action="store_true", help="v7d kaynak MANIFEST'i uret (Etsy YOK); --qc-csv gerekli")
    ap.add_argument("--qc-csv", help="--manifest-uret: TAM78/RAPOR/QC.csv")
    a = ap.parse_args()
    if a.manifest_uret:                      # Etsy'ye istek yok: token okunmaz
        if not a.qc_csv:
            raise SystemExit("HATA: --manifest-uret icin --qc-csv gerekli. DUR.")
        sys.exit(manifest_uret(a))
    a.haric = sorted({x.strip() for x in a.haric.split(",") if x.strip()})
    onay = PROFIL[a.surum]["onay"]
    if a.apply and (a.confirm != onay or not a.plan or not a.yedek_liste):
        raise SystemExit(f"HATA: apply icin --confirm {onay}, --plan ve --yedek-liste gerekli. DUR.")
    if a.surum in V7:
        if not a.manifest or not a.galeri_ilerleme:
            raise SystemExit(f"HATA: {a.surum} icin --manifest ve --galeri-ilerleme gerekli. DUR.")
        m_satir = list(csv.DictReader(open(a.manifest, encoding="utf-8")))
        a.manifest_rows = {r["cift"]: r for r in m_satir}
        a.galeri = json.loads(pathlib.Path(a.galeri_ilerleme).read_text(encoding="utf-8")).get("ilanlar") or {}
    a.kaynak = json.loads(pathlib.Path(a.kaynak_bilgi).read_text()) if a.kaynak_bilgi else {}
    if a.surum == "v7d":
        a.kaynak["manifest_sha256"] = sha(a.manifest)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    satirlar = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    if len(satirlar) != BEKLENEN:
        raise SystemExit(f"HATA: ilan listesi {len(satirlar)} != {BEKLENEN}. DUR.")
    bilinmeyen = set(a.haric) - {s["cift"] for s in satirlar}
    if bilinmeyen:
        raise SystemExit(f"HATA: haric listesinde bilinmeyen cift: {sorted(bilinmeyen)}. DUR.")
    if a.surum == "v7d":   # MANIFEST (cift, listing_id) kumesi ilan listesiyle iki yonlu birebir; degilse Etsy'ye hic gidilmez
        m_k = [(r.get("cift"), str(r.get("listing_id"))) for r in m_satir]
        i_k = [(s_["cift"], str(s_["listing_id"])) for s_ in satirlar]
        if len(m_k) != len(set(m_k)) or set(m_k) != set(i_k):
            raise SystemExit(f"HATA: v7d MANIFEST ilan listesiyle birebir degil (MANIFEST {len(m_k)}, eksik "
                             f"{sorted(set(i_k) - set(m_k))[:3]}, fazla {sorted(set(m_k) - set(i_k))[:3]}). DUR.")
    satirlar = [s for s in satirlar if s["cift"] not in a.haric]
    plan = None
    if a.apply:   # plan kapilari token okunmadan ONCE (Etsy'ye hic gidilmeden DUR)
        plan = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))
        rows = plan.get("satirlar") or []
        blok = [r["cift"] for r in rows if r.get("durum") not in ("YUKLE", "DEGISTIR")]
        if (plan.get("surum") or "v5") != a.surum:
            raise SystemExit(f"HATA: plan surumu {plan.get('surum') or 'v5'} != --surum {a.surum}. DUR.")
        if a.surum == "v7d":   # plan kilidi: ayni TAM78 klasoru + ayni MANIFEST
            pk = plan.get("kaynak") or {}
            if pk.get("klasor") != a.kaynak.get("klasor") or pk.get("manifest_sha256") != a.kaynak.get("manifest_sha256"):
                raise SystemExit(f"HATA: v7d plan kaynagi ({pk.get('klasor')}, MANIFEST {str(pk.get('manifest_sha256'))[:12]}) != "
                                 f"verilen ({a.kaynak.get('klasor')}, {str(a.kaynak.get('manifest_sha256'))[:12]}). DUR.")
        if a.surum in V7:   # yalniz galeri kapisi BLOK'u (galeri bitmemis) olan plan kullanilir; baska BLOK = kuru FAIL -> DUR (inceleme 30 Eki)
            blok = [c for c in blok if not any(r["cift"] == c and r.get("durum") == "BLOK" and r.get("galeri_bekliyor") for r in rows)]
        bilinen = {(str(s["listing_id"]), s["cift"]) for s in satirlar}
        yabanci = [r["cift"] for r in rows if (str(r["listing_id"]), r["cift"]) not in bilinen]
        if blok or yabanci or not rows:
            raise SystemExit(f"HATA: plan kullanilamaz (BLOK {blok}, ilan listesi disi {yabanci}). DUR.")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    if a.apply:
        _, ok = apply(a, Etsy(store), out, plan)
        sys.exit(0 if ok else 1)
    sys.exit(0 if kuru(a, Etsy(store), out, satirlar) else 1)


if __name__ == "__main__":
    main()
