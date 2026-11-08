#!/usr/bin/env python3
"""YAYINA HAZIR KONTROLU (SALT OKUMA; Serdar 8 Kas sistem onerisi 2, "hepsi"). Etsy'ye yazma YOK.
Urun ayar dosyasindaki (SPEC, ornek docs/ornament/ORN_YAYIN_SPEC.json) beklenen degerlerle ilanlari karsilastirir;
Serdar'a linkli liste uretir: YAYINDA / YAYINDA (EKSIK VAR) / YAYINA HAZIR / HENUZ YAYINLAMAYIN (neden) / DURUM ...
Etsy (salt okuma): GET /shops/{shop} (kota) + GET /shops/{shop}/production-partners (ortak adi -> tek id) +
GET /listings/batch?includes=images,videos,translations,personalization (100'luk parca basina 1; kucuk harf: emsal marka_tara.py)
+ SPEC'te nitelik varsa ilan basina GET .../properties (--nitelik-yok ile kapatilirsa sonuc "olculemedi").
mod=olc    : TUM ilanlar tek batch'te (1 istek / 100) -> donen / istenen sayisi state'e gore; ornek olarak 1 draft + 1 active
             ilanin alan adlari ve turleri (deger yazilmaz) + properties alanlari + magaza uretim ortaklari (id, ad, konum)
             -> OLCUM.json. Donmeyen ilan varsa ya da ornek yoksa kosu FAIL (cikti yine yazilir).
mod=kontrol: tum ilanlar -> YAYINA_HAZIR.json + YAYINA_HAZIR.md; her 10 ilanda ara cikti ("YARIM: devam ediyor n/N");
             DUR / hata / iptal sinyalinde yarim cikti isaretli kalir. Ilan basina beklenmeyen veri o ilanda "olculemedi".
Kontroller (SPEC beklenen): state, kargo profili, uretim ortagi (ad + magazadaki tek id), fiyat, kisisellestirme acik,
gorsel sayisi + rank tekrarsiz ve artan + rank sirasiyla TUM alt metinler (alt_metin_kaynagi) + eski gorsel id yok,
video sayisi + video_state active + eski video id yok (ilan dosyasindaki eski id'ler, ornament YEDEK9 gorsel/video),
aciklamada zorunlu ifadeler, baslik + aciklama + etiketlerde yasak desenler, RU baslik + aciklama (CSV ile tam),
nitelik degerleri. Beklenen kod kumesi (RU CSV) ile ilan dosyasi karsilastirilir: eksik kod "DURUM ilan dosyasinda yok".
SPEC'te zorunlu anahtar eksik ya da bilinmeyen anahtar varsa DUR (yanlis adli anahtar kontrolu sessizce kaldirmasin).
Bir alan yanitta YOKSA sonuc "olculemedi" (PASS sayilmaz). Uygulanan ve EDILMEYEN kontroller rapor basligina yazilir.
"""
import argparse
import csv
import hashlib
import html
import importlib
import json
import os
import re
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10
LINK = "https://www.etsy.com/your/shops/me/listing-editor/edit/{}"
ZAYIF = " (ZAYIF KONTROL)"
SINIF_SIRA = ("YAYINDA (EKSIK VAR)", "HENUZ YAYINLAMAYIN", "YAYINA HAZIR", "YAYINA HAZIR" + ZAYIF, "YAYINDA", "YAYINDA" + ZAYIF)
INCLUDES = "images,videos,translations,personalization"
# Zorunlu anahtar SPEC'te BULUNMALI; kontrol istenmiyorsa acikca bos / null yazilir ([] / null / false) ve rapor "YOK" der,
# sinif "(ZAYIF KONTROL)" olur (inceleme 3. tur: silinen anahtar kontrolu sessizce kaldirmasin).
B_ZORUNLU = {"shipping_profile_id", "uretim_ortagi_id", "uretim_ortagi_konum", "fiyat", "kisisellestirme", "gorsel_sayisi", "video_sayisi", "aciklama_yasak",
             "aciklama_zorunlu", "nitelikler"}
B_SECMELI = {"uretim_ortagi", "gorsel2_alt_icerir"}   # uretim_ortagi: panel ic adi, bilgi (API acik adi dondurur)
S_ZORUNLU = {"urun", "kaynak", "beklenen", "kontrol_edilmeyen", "eski_medya", "alt_metin_kaynagi", "ru"}
S_SECMELI = set()


class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r


def tam(t):
    return html.unescape(str(t or "")).replace("\r\n", "\n").strip()


def norm(t):
    """ornament_galeri9 geri okumasiyla ayni: html cozulur, bosluklar tek."""
    return " ".join(html.unescape(str(t or "")).split())


def sayi(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def tamsayi(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def fiyat(p):
    if isinstance(p, dict) and p.get("amount") is not None and p.get("divisor"):
        try:
            return round(float(p["amount"]) / float(p["divisor"]), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    return sayi(p)


def spec_yukle(yol):
    b = open(yol, "rb").read()
    s = json.loads(b)
    eksik = sorted((S_ZORUNLU - set(s)) | {f"beklenen.{k}" for k in B_ZORUNLU - set(s.get("beklenen") or {})})
    bilinmeyen = sorted((set(s) - S_ZORUNLU - S_SECMELI) | {f"beklenen.{k}" for k in set(s.get("beklenen") or {}) - B_ZORUNLU - B_SECMELI})
    if eksik or bilinmeyen:
        raise SystemExit(f"DUR: SPEC anahtar hatasi: eksik {eksik}, bilinmeyen {bilinmeyen}")
    em = s["eski_medya"]
    if em not in (None, False) and not (isinstance(em, dict) and sorted(em) == ["gorsel_sayisi", "video_sayisi"]
                                         and all(isinstance(em[x], int) and not isinstance(em[x], bool) for x in em)):
        raise SystemExit(f"DUR: SPEC eski_medya null/false ya da {{gorsel_sayisi: int, video_sayisi: int}} olmali: {em!r}")
    s["_sha"] = hashlib.sha256(b).hexdigest()
    return s


def uygulanan(spec):
    b = spec["beklenen"]
    u = ["state", "kargo profili", f"uretim ortagi (id {b['uretim_ortagi_id']} + konum {b['uretim_ortagi_konum']}, magazada var)",
         "fiyat (ilan duzeyi)", "kisisellestirme acik" if b["kisisellestirme"] else "kisisellestirme kapali",
         f"{b['gorsel_sayisi']} gorsel, rank tekrarsiz ve artan",
         "tum alt metinler sirasiyla" if spec.get("alt_metin_kaynagi") else
         ("yalniz 2. gorsel alt metni (ZAYIF: sira kontrol edilmez)" if b.get("gorsel2_alt_icerir") else "alt metin YOK (ZAYIF)"),
         f"{b['video_sayisi']} video, video_state active",
         ("eski gorsel / video id yok (yedek yapisi {gorsel_sayisi} gorsel, {video_sayisi} video)".format(**spec["eski_medya"])
          if spec["eski_medya"] else "eski medya kontrolu YOK"),
         "aciklama zorunlu ifade" if b.get("aciklama_zorunlu") else "aciklama zorunlu ifade YOK",
         "baslik + aciklama + etiket yasak desen" if b["aciklama_yasak"] else "yasak desen YOK", "RU baslik + aciklama" if spec.get("ru") else "RU YOK",
         "nitelikler" if b.get("nitelikler") else "nitelik YOK", "beklenen kod kumesi (RU CSV)" if spec.get("ru") else "kod kumesi YOK"]
    return u


def zayif_mi(spec):
    return any("YOK" in u or "ZAYIF" in u for u in uygulanan(spec))


def ru_csv(spec):
    r = spec.get("ru")
    if not r:
        return None
    b = open(KOK / r["csv"], "rb").read()
    if hashlib.sha256(b).hexdigest() != r["sha256"]:
        raise SystemExit("DUR: RU CSV sha256 SPEC ile ayni degil")
    return {x[r.get("anahtar", "kod")]: x for x in csv.DictReader(open(KOK / r["csv"], encoding="utf-8"))}


def alt_kaynak(spec):
    """SPEC alt_metin_kaynagi 'modul:fonksiyon' -> f(kod) = (alt listesi, baslik, hata listesi). Yoksa None."""
    k = spec.get("alt_metin_kaynagi")
    if not k:
        return None
    m, f = k.split(":")
    return getattr(importlib.import_module(m), f)


def alan_turleri(d, on="", derin=0):
    """Alan adi -> tur. dict'ler ve listelerin ilk ogesi acilir (deger yazilmaz)."""
    out = {}
    if isinstance(d, list):
        out[on.rstrip(".") or "_"] = f"list[{len(d)}]"
        if d and derin < 3:
            out.update(alan_turleri(d[0], on.rstrip(".") + "[0].", derin + 1))
        return out
    if not isinstance(d, dict):
        out[on.rstrip(".") or "_"] = type(d).__name__
        return out
    for k, v in d.items():
        if isinstance(v, (dict, list)) and derin < 3:
            out.update(alan_turleri(v, f"{on}{k}.", derin + 1))
        else:
            out[on + k] = type(v).__name__
    return out


def batch(api, ids):
    res, n = [], 0
    for i in range(0, len(ids), 100):
        r = api.get("/listings/batch", params={"listing_ids": ",".join(str(x) for x in ids[i:i + 100]), "includes": INCLUDES}) or {}
        res += r.get("results") or []
        n += 1
    return {int(x["listing_id"]): x for x in res if str(x.get("listing_id", "")).isdigit()}, n


def ru_bul(L):
    """includes=translations yaniti. Emsal beyan_marka_yaz.ru_ceviri: batch'te dict {dil: ceviri}; liste de kabul.
    -> None (alan yok) | {} (RU yok) | RU kaydi."""
    t = L.get("translations")
    if t is None:
        return None
    if isinstance(t, dict):
        if isinstance(t.get("ru"), dict):
            return t["ru"]
        t = list(t.values())
    for x in t or []:
        if isinstance(x, dict) and str(x.get("language", "")).lower().startswith("ru"):
            return x
    return {}


def eski_idler(kayit, yapi=None):
    """Ilan dosyasi kaydindaki eski medya id'leri (ornament YEDEK9: gorsel[].id, video[].id). None = kayitta liste yok ya da
    yedek yapisi (SPEC eski_medya: gorsel_sayisi, video_sayisi) tutmuyor (bos liste yanlis PASS vermesin; inceleme 3. tur)."""
    if not isinstance(kayit, dict) or not isinstance(kayit.get("gorsel"), list) or not isinstance(kayit.get("video"), list):
        return None
    if yapi and (len(kayit["gorsel"]) != yapi.get("gorsel_sayisi") or len(kayit["video"]) != yapi.get("video_sayisi")
                 or any(not isinstance(x, dict) or x.get("id") is None for x in kayit["gorsel"] + kayit["video"])):
        return None
    return ({str(x.get("id")) for x in kayit["gorsel"] if isinstance(x, dict) and x.get("id") is not None},
            {str(x.get("id")) for x in kayit["video"] if isinstance(x, dict) and x.get("id") is not None})


def gorsel_kontrol(b, ims, alt_beklenen, eski_g):
    ims = sorted(ims, key=lambda x: (x.get("rank") is None, x.get("rank") or 0))
    r = [x.get("rank") for x in ims]
    if None in r or len(set(r)) != len(r):
        return f"FAIL: rank eksik ya da tekrarli {r}"
    if len(ims) != b["gorsel_sayisi"]:
        return f"FAIL: {len(ims)} gorsel (beklenen {b['gorsel_sayisi']}), rank {r}"
    if eski_g is not None:
        if any(x.get("listing_image_id") is None for x in ims):
            return "olculemedi: listing_image_id yok (eski gorsel kontrolu)"
        eski = [x.get("rank") for x in ims if str(x.get("listing_image_id")) in eski_g]
        if eski:
            return f"FAIL: eski gorsel (rank {eski})"
    gelen = [norm(x.get("alt_text")) for x in ims]
    if alt_beklenen is not None:
        bek = [norm(a) for a in alt_beklenen]
        if len(bek) != len(gelen):
            return f"olculemedi: beklenen alt metin sayisi {len(bek)}"
        fark = [i + 1 for i, (g, e) in enumerate(zip(gelen, bek)) if g != e]
        return "PASS" if not fark else f"FAIL: alt metin / sira farkli, sira {fark} (rank {r})"
    k2 = b.get("gorsel2_alt_icerir")
    if k2 and (len(gelen) < 2 or k2.lower() not in gelen[1].lower()):
        return f"FAIL: 2. gorsel alt metni '{k2}' icermiyor"
    return "PASS"


def video_kontrol(b, vs, eski_v):
    if len(vs) != b["video_sayisi"]:
        return f"FAIL: {len(vs)} video"
    if any("video_state" not in v for v in vs):
        return "olculemedi: video_state yok"
    kotu = [v.get("video_state") for v in vs if v.get("video_state") != "active"]
    if kotu:
        return f"FAIL: video_state {kotu}"
    if eski_v is not None:
        if any(v.get("video_id") is None for v in vs):
            return "olculemedi: video_id yok (eski video kontrolu)"
        if any(str(v.get("video_id")) in eski_v for v in vs):
            return "FAIL: eski video"
    return "PASS"


def kontrol_et(spec, kod, L, ru_harita, props=None, alt_f=None, eski=None, ortak_id=None):
    """ru_harita: None = RU kontrolu yok; dict = {kod: CSV satiri}. props: None = nitelik okunmadi.
    eski: (eski gorsel id kumesi, eski video id kumesi) ya da None. ortak_id: magazada bulunan SPEC ortagi id'si (yoksa None).
    Olcum (olc 42486805159, 8 Kas): API partner_name panel ic adini degil acik adi ("Printing and Fulfillment Partner") dondurur,
    iki ortak ayni adli; ayirt eden id ve location (Latvia 5870733, United States 5817638).
    -> sonuclar dict ad -> 'PASS' | 'FAIL: ...' | 'olculemedi: ...'"""
    S = {}
    b = spec["beklenen"]
    v = L.get("shipping_profile_id")
    S["kargo profili"] = ("olculemedi: alan yok" if v is None else
                          ("PASS" if tamsayi(v) is not None and tamsayi(v) == int(b["shipping_profile_id"]) else f"FAIL: {v}"))
    if "production_partners" not in L or not isinstance(L.get("production_partners") or [], list):
        S["uretim ortagi"] = "olculemedi: alan yok"
    else:
        pp = [p for p in L.get("production_partners") or [] if isinstance(p, dict)]
        idler = [str(p.get("production_partner_id")) for p in pp]
        ok = (ortak_id is not None and idler == [str(b["uretim_ortagi_id"])] and str(ortak_id) == str(b["uretim_ortagi_id"])
              and [str(p.get("location")) for p in pp] == [b["uretim_ortagi_konum"]])
        S["uretim ortagi"] = "PASS" if ok else f"FAIL: {[(p.get('production_partner_id'), p.get('location')) for p in pp]}"
    f = fiyat(L.get("price"))
    S["fiyat"] = "olculemedi: alan yok" if f is None else ("PASS" if abs(f - float(b["fiyat"])) < 0.005 else f"FAIL: {f}")
    if "is_personalizable" not in L:
        S["kisisellestirme"] = "olculemedi: alan yok"
    elif not isinstance(L.get("is_personalizable"), bool):   # "false" metni yanlis PASS vermesin (inceleme 3. tur)
        S["kisisellestirme"] = f"olculemedi: beklenmeyen tur {type(L.get('is_personalizable')).__name__}"
    else:
        S["kisisellestirme"] = "PASS" if bool(L.get("is_personalizable")) == bool(b["kisisellestirme"]) else f"FAIL: {L.get('is_personalizable')}"
    eg, ev = eski if eski is not None else (None, None)
    if spec["eski_medya"] and eski is None:
        S["eski medya"] = "olculemedi: ilan dosyasinda eski id listesi yok ya da yedek yapisi farkli"
    ims = L.get("images")
    if not isinstance(ims, list):
        S["gorsel"] = "olculemedi: alan yok"
    else:
        alt_bek = None
        if alt_f is not None:
            try:
                alt_bek, _, hata = alt_f(kod)
            except Exception as e:  # noqa: BLE001 (kaynak hatasi -> olculemedi, PASS degil; Etsy istegi yok)
                alt_bek, hata = None, [f"{type(e).__name__}: {e}"]
            except SystemExit as e:   # yalniz kaynagin kendi DUR'u (DUR-ON); sinyal / kota DUR yukari gider (inceleme 4. tur)
                if not str(e.code).startswith("DUR-ON"):
                    raise
                alt_bek, hata = None, [f"SystemExit: {e.code}"]
            if hata:
                S["gorsel"] = f"olculemedi: beklenen alt metin uretilemedi {hata}"
        if "gorsel" not in S:
            S["gorsel"] = gorsel_kontrol(b, ims, alt_bek, eg)
    vs = L.get("videos")
    S["video"] = "olculemedi: alan yok" if not isinstance(vs, list) else video_kontrol(b, vs, ev)
    if "description" not in L or "title" not in L or "tags" not in L:
        S["metin"] = "olculemedi: baslik / aciklama / etiket alani yok"
    else:
        d = norm(L.get("description"))
        hepsi = " | ".join([norm(L.get("title")), d] + [norm(t) for t in L.get("tags") or []])   # etiket uclari birlesmesin
        for z in b.get("aciklama_zorunlu", []):
            S[f"aciklama zorunlu: {z[:30]}"] = "PASS" if norm(z) in d else "FAIL: yok"
        for y in b["aciklama_yasak"]:
            m = re.search(y, hepsi, re.I)
            S[f"yasak: {y}"] = "PASS" if not m else f"FAIL: '{m.group(0)}'"
    if ru_harita is not None:
        bek = ru_harita.get(kod)
        ru = ru_bul(L)
        if bek is None:
            S["RU"] = "FAIL: RU CSV'de kod yok"
        elif ru is None:
            S["RU"] = "olculemedi: translations alani yok"
        else:
            ok = tam(ru.get("title")) == tam(bek["baslik_ru"]) and tam(ru.get("description")) == tam(bek["aciklama_ru"])
            S["RU"] = "PASS" if ok else ("FAIL: RU yok" if not tam(ru.get("title")) else "FAIL: RU farkli")
    if b.get("nitelikler"):
        if props is None:
            S["nitelik"] = "olculemedi: nitelik okunmadi"
        else:
            have = {tamsayi(p.get("property_id")): p for p in props if isinstance(p, dict) and tamsayi(p.get("property_id")) is not None}
            for o in b["nitelikler"]:
                p = have.get(int(o["property_id"]))
                if p is None:
                    S[f"nitelik {o['ad']}"] = "FAIL: yok"
                    continue
                a = [sayi(x) for x in p.get("values") or []]
                e = [sayi(x) for x in o["values"]]
                ok = None not in a and len(a) == len(e) and all(abs(x - y) < 1e-6 for x, y in zip(a, e)) and p.get("scale_id") == o.get("scale_id")
                S[f"nitelik {o['ad']}"] = "PASS" if ok else f"FAIL: {p.get('values')} scale {p.get('scale_id')}"
    return S


def siniflandir(L, S, zayif=False):
    st = L.get("state")
    kotu = {k: v for k, v in S.items() if v != "PASS"}
    ek = ZAYIF if zayif else ""
    if st == "active":
        return ("YAYINDA" + ek if not kotu else "YAYINDA (EKSIK VAR)"), kotu
    if st != "draft":
        return f"DURUM {st}", kotu
    return ("YAYINA HAZIR" + ek if not kotu else "HENUZ YAYINLAMAYIN"), kotu


def sayim(R):
    say = {}
    for x in R["ilanlar"].values():
        say[x["sinif"]] = say.get(x["sinif"], 0) + 1
    return say


def md(R, spec):
    g = {}
    for kod, x in sorted(R["ilanlar"].items()):
        g.setdefault(x["sinif"], []).append((kod, x))
    say = sayim(R)
    ke = ", ".join(spec.get("kontrol_edilmeyen") or []) or "yok"
    out = [f"# Yayına hazır kontrolü: {spec.get('urun')} ({R['zaman']})", ""]
    if R.get("yarim"):
        out += [f"YARIM ÇIKTI (sonuç eksik): {R['yarim']}", ""]
    out += [f"SPEC sha {spec['_sha'][:12]}; kota {R.get('kota_bas')} -> {R.get('kota_son')}; çağrı {R.get('cagri')} (bizim veri, salt okuma).",
            f"Toplam {len(R['ilanlar'])}" + (f" / beklenen {R['beklenen_sayi']}" if R.get("beklenen_sayi") else "") + ": "
            + ", ".join(f"{k} {v}" for k, v in sorted(say.items())) + ".",
            "Uygulanan kontroller: " + "; ".join(uygulanan(spec)) + ".",
            f"Kontrol EDİLMEYEN: {ke}.", ""]
    for s in SINIF_SIRA:
        if s in g:
            temiz = s.startswith(("YAYINA HAZIR", "YAYINDA")) and s != "YAYINDA (EKSIK VAR)"
            out.append(f"## {s}: {len(g[s])}" + (f" (kontrol edilmeyen: {ke})" if temiz else ""))
            for kod, x in g[s]:
                ek = "" if not x["eksik"] else " | " + "; ".join(f"{k}: {v}" for k, v in x["eksik"].items())
                out.append(f"- [{kod}]({LINK.format(x['listing_id'])}){ek}")
            out.append("")
    for s, v in sorted(g.items()):
        if s not in SINIF_SIRA:
            out.append(f"## {s}: {len(v)}")
            out += [f"- {kod} {x['listing_id']} | " + "; ".join(f"{k}: {w}" for k, w in x["eksik"].items()) for kod, x in v] + [""]
    return "\n".join(out)


def ilan_listesi(Y):
    """-> (ids {kod: lid}, okunamayan {kod: neden}). listing_id'siz kayit sessizce atlanmaz."""
    ids, kotu = {}, {}
    for k, v in Y.items():
        if isinstance(v, dict) and str(v.get("listing_id", "")).isdigit():
            ids[k] = int(v["listing_id"])
        else:
            kotu[k] = f"listing id yok ({(v or {}).get('hata') if isinstance(v, dict) else type(v).__name__})"
    return ids, kotu


def yaz(out, R, spec):
    """Once md, sonra JSON (inceleme 3. tur: kesintide ikisi celismesin; JSON son yazilir)."""
    m = md(R, spec)
    open(out / "YAYINA_HAZIR.md", "w").write(m)
    json.dump(R, open(out / "YAYINA_HAZIR.json", "w"), indent=1, ensure_ascii=False)
    return m


def ortak_bul(api, shop, oid, konum):
    """Magazadaki uretim ortaklari; SPEC id'si TEK kayit ve konumu SPEC ile ayni olmali, yoksa DUR."""
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    liste = [(p.get("production_partner_id"), p.get("partner_name"), p.get("location")) for p in pp]
    es = [x for x in liste if str(x[0]) == str(oid)]
    if len(es) != 1 or str(es[0][2]) != str(konum):
        raise SystemExit(f"DUR: magazada uretim ortagi id {oid} / konum {konum} bulunamadi ya da farkli: {liste}")
    return es[0][0], liste


SINYAL = []   # gelen sinyal; ic except bloklari (ornament_galeri9.alt_metinler) SystemExit'i yutsa da dongu her ilandan sonra bakar


def _sinyal(signum, frame):
    SINYAL.append(signum)
    raise SystemExit(f"DUR: sinyal {signum} (iptal / zaman asimi)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["olc", "kontrol"], required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--ilanlar", required=True, help="JSON: {KOD: {listing_id, gorsel[{id}], video[{id}]}} (ornament YEDEK9.json)")
    ap.add_argument("--nitelik-yok", action="store_true", help="nitelik okunmaz; SPEC'te nitelik varsa sonuc 'olculemedi'")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, _sinyal)
    spec = spec_yukle(a.spec)
    Y = json.load(open(a.ilanlar))
    ids, okunamayan = ilan_listesi(Y)
    if not ids:
        raise SystemExit("DUR: ilan listesi bos")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    RU = ru_csv(spec)
    alt_f = alt_kaynak(spec) if a.mod == "kontrol" else None
    nitelik = bool(spec["beklenen"].get("nitelikler")) and not a.nitelik_yok
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = SaltOkur(store)
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    api.get(f"/shops/{shop}")
    kota_bas, cagri = api.remaining, 1
    sec = sorted(ids.items())
    nb = (len(sec) + 99) // 100
    tahmin = 1 + nb + (2 if a.mod == "olc" else (len(sec) if nitelik else 0))
    if str(kota_bas).isdigit() and int(kota_bas) < tahmin + KOTA_MIN:
        raise SystemExit(f"DUR: kota {kota_bas} < tahmini istek {tahmin} + {KOTA_MIN} (okuma baslamadi)")
    print(f"ilan {len(sec)} | okunamayan {len(okunamayan)} | nitelik {nitelik} | tahmini istek {tahmin} | kota {kota_bas}", flush=True)
    if a.mod == "olc":
        B, n = batch(api, [v for _, v in sec]); cagri += n
        st = {}
        for L in B.values():
            st[str(L.get("state"))] = st.get(str(L.get("state")), 0) + 1
        eksik = [kod for kod, v in sec if v not in B]
        O = {"istenen": len(sec), "donen": len(B), "state": st, "donmeyen": eksik, "uretim_ortaklari": None, "ornek": {}}

        def olc_yaz():
            O["_kota"] = [kota_bas, api.remaining]; O["_cagri"] = cagri
            json.dump(O, open(out / "OLCUM.json", "w"), indent=1, ensure_ascii=False)
        olc_yaz()                                  # batch olcumu hemen kaydedilir (sonraki hata onu kaybettirmesin)
        try:
            try:
                O["uretim_ortaklari"] = [(p.get("production_partner_id"), p.get("partner_name"), p.get("location"))
                                         for p in (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []]
            except SystemExit as e:                # kota DUR ve sinyal yukari; ucun kendi hatasi kaydedilir, kosu sonda FAIL
                if str(e.code).startswith(("DUR: kota", "DUR: sinyal")):
                    raise
                O["uretim_ortaklari"] = f"okunamadi: {str(e.code)[:200]}"
            cagri += 1
            for durum in ("draft", "active"):
                kod_lid = next(((kod, v) for kod, v in sec if v in B and B[v].get("state") == durum), None)
                if kod_lid is None:
                    continue
                kod, v = kod_lid
                L = B[v]
                props = (api.get(f"/shops/{shop}/listings/{v}/properties") or {}).get("results") or []; cagri += 1
                O["ornek"][durum] = {"kod": kod, "batch_alanlar": alan_turleri(L), "properties_alanlar": alan_turleri(props),
                                     "translations_tur": type(L.get("translations")).__name__,
                                     "translations_anahtar": sorted(L["translations"]) if isinstance(L.get("translations"), dict) else None,
                                     "ru_var": ru_bul(L) not in (None, {}),
                                     "production_partners": [(p.get("production_partner_id"), p.get("partner_name"), p.get("location"))
                                                             for p in L.get("production_partners") or [] if isinstance(p, dict)],
                                     "gorsel_rank": [x.get("rank") for x in L.get("images") or [] if isinstance(x, dict)],
                                     "video_state": [x.get("video_state") for x in L.get("videos") or [] if isinstance(x, dict)],
                                     "is_personalizable": L.get("is_personalizable"),
                                     "is_personalizable_tur": type(L.get("is_personalizable")).__name__,
                                     "nitelik_id": [p.get("property_id") for p in props if isinstance(p, dict)]}
            if SINYAL:
                raise SystemExit(f"DUR: sinyal {SINYAL[0]} (iptal / zaman asimi)")
        except BaseException as e:
            O["hata"] = f"{type(e).__name__}: {str(getattr(e, 'code', e))[:300]} (olcum yarim)"
            raise
        finally:
            olc_yaz()
        print(json.dumps(O, ensure_ascii=False)[:8000])
        if eksik or not O["ornek"] or not isinstance(O["uretim_ortaklari"], list):
            raise SystemExit(f"DUR: olc eksik: donen {len(B)} / {len(sec)}, donmeyen {eksik[:10]}, ornek {sorted(O['ornek'])}, "
                             f"uretim ortaklari {O['uretim_ortaklari'] if not isinstance(O['uretim_ortaklari'], list) else 'tamam'}")
        return
    R = {"ilanlar": {}, "zaman": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "kota_bas": kota_bas, "spec_sha": spec["_sha"],
         "yarim": f"devam ediyor 0/{len(sec)}"}
    if RU is not None:
        R["beklenen_sayi"] = len(RU)
        for kod in sorted(set(RU) - set(Y)):
            R["ilanlar"][kod] = {"listing_id": None, "sinif": "DURUM ilan dosyasinda yok", "eksik": {"okuma": "beklenen kod, ilan dosyasinda yok"}}
        for kod in sorted(set(Y) - set(RU)):
            R["ilanlar"][kod] = {"listing_id": ids.get(kod), "sinif": "DURUM beklenmeyen kod", "eksik": {"okuma": "RU CSV'de yok"}}
    for kod, neden in okunamayan.items():
        R["ilanlar"].setdefault(kod, {"listing_id": None, "sinif": "DURUM okunamadi", "eksik": {"okuma": neden}})
    sec = [(kod, v) for kod, v in sec if kod not in R["ilanlar"]]
    t0 = time.time()
    zayif = zayif_mi(spec)
    try:
        ortak_id, R["uretim_ortaklari"] = ortak_bul(api, shop, spec["beklenen"]["uretim_ortagi_id"], spec["beklenen"]["uretim_ortagi_konum"]); cagri += 1
        B, n = batch(api, [v for _, v in sec]); cagri += n
        for i, (kod, lid) in enumerate(sec, 1):
            L = B.get(lid)
            if L is None:
                R["ilanlar"][kod] = {"listing_id": lid, "sinif": "DURUM okunamadi", "eksik": {"okuma": "batch yanitinda yok"}}
                continue
            try:
                props = None
                if nitelik and L.get("state") in ("draft", "active"):
                    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []; cagri += 1
                S = kontrol_et(spec, kod, L, RU, props, alt_f, eski_idler(Y.get(kod), spec["eski_medya"] or None), ortak_id)
                sinif, kotu = siniflandir(L, S, zayif)
                R["ilanlar"][kod] = {"listing_id": lid, "state": L.get("state"), "sinif": sinif, "eksik": kotu, "sonuc": S}
            except Exception as e:  # noqa: BLE001 (beklenmeyen veri tek ilanda kalir; kota DUR SystemExit'i yukari gider)
                R["ilanlar"][kod] = {"listing_id": lid, "state": L.get("state"), "sinif": "DURUM olculemedi",
                                     "eksik": {"hata": f"olculemedi: {type(e).__name__}: {str(e)[:200]}"}}
            if SINYAL:
                raise SystemExit(f"DUR: sinyal {SINYAL[0]} (iptal / zaman asimi; ic blokta yakalanmisti)")
            g = time.time() - t0
            print(f"[{i}/{len(sec)}] {kod} {R['ilanlar'][kod]['sinif']} | gecen {g:.0f} sn | kalan ~{g / i * (len(sec) - i):.0f} sn | "
                  f"%{100 * i // len(sec)} | kota {api.remaining}", flush=True)
            if i % 10 == 0:
                R.update(kota_son=api.remaining, cagri=cagri, yarim=f"devam ediyor {i}/{len(sec)}")
                yaz(out, R, spec)
        R.pop("yarim", None)
        R.update(kota_son=api.remaining, cagri=cagri)
        m = yaz(out, R, spec)
    except BaseException as e:
        R.update(kota_son=api.remaining, cagri=cagri, yarim=f"{type(e).__name__}: {str(getattr(e, 'code', e))[:300]}")
        yaz(out, R, spec)
        raise
    print(f"::notice::yayina_hazir {spec.get('urun')} | {sayim(R)} | cagri {cagri} | kota {kota_bas} -> {api.remaining}")
    print(m[:6000])


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
