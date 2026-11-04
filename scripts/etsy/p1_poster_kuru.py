#!/usr/bin/env python3
"""P1 KURU (Etsy istegi YOK; yerel, p1-poster-oku ham verisiyle). Serdar 4 Kas P1 "A": onizleme paragrafindan "yanit yoksa
basilir/gonderilir" sozu cikar, EN + RU birlikte; baslik / etiket / malzeme degismez. Yazim YOK (yazici ayri gorev).
poster_metin_kuru.DEG, pod_5x7_kuru.EN_DEGISIKLIK, seo/pod_changes_v3.json ve aciklama_v3_sablon.txt'e dokunulmaz.
Ilan basina siniflama (EN, norm; inceleme 4 Kas D-1: esnek desen GENEL_EN kesme isareti / bosluk varyantlarini da sayar):
  tam SIL_EN 1 ve GENEL_EN 1 -> PLAN adayi | eski soz -> DUR (eski varyant) | tam SIL_EN >= 2 -> DUR (neden "FAIL")
  GENEL_EN 0 -> ZATEN_YENI ancak RU'da GENEL_RU 0 + YENI_EN ve YENI_RU paragraflari birebir + state active; degilse DUR (yarim)
  GENEL_EN >= 1 ama tam SIL_EN ile ayni degil -> DUR (varyant)
DUR (plana girmez): state != active; RU yok / okunamadi; RU baslik bos; kur(EN once) != canli RU; kur(EN yeni) FAIL; yeni RU !=
canli RU eksi SIL_RU; EN / RU farki tam 1 paragraf degil; metin kapisi uyarisi; AI beyani eksik; suslu parantez.
Kullanim: p1_poster_kuru.py --ham DIR (HAM/ + AKTIF_SAYIM.csv) --out DIR"""
import argparse
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
import poster_metin_kuru as P  # noqa: E402

SIL_EN = (" If we don't hear from you within 24 hours of receiving the preview, we go ahead with the design as shown: we print your "
          "poster, or send your digital file as a download link in Etsy Messages.")
SIL_EN_ESKI = " If we don't hear from you within 24 hours of receiving the preview, we print the design as shown."
SIL_RU = (" Если в течение 24 часов после получения макета мы не получим от вас ответа, мы продолжим работу с дизайном в том виде, "
          "в каком он показан на макете: напечатаем постер или отправим цифровой файл в виде ссылки для скачивания в сообщениях "
          "Etsy.")
YENI_EN = ("YOUR PREVIEW\nWe send you a preview via Etsy Messages within 24 hours of your order. We print your poster or prepare your "
           "file as soon as you approve it.")
YENI_RU = ("ВАШ МАКЕТ\nМы отправляем вам макет через сообщения Etsy в течение 24 часов после заказа. Мы печатаем постер или готовим "
           "файл сразу после того, как вы одобрите макет.")
ISTEK_TIPIK = 7    # yazimda tipik: GET ilan, GET envanter, GET RU, PATCH, GET geri okuma, PUT RU, GET RU geri okuma
ISTEK_ILAN = 20    # yazici ilan basi kota butcesi (poster_metin_yaz.py:33 ISTEK_ILAN = 20; en kotu 11 + RU yeniden deneme)
GENEL_EN = re.compile(r"If\s+we\s+don[\u2019'`]?t\s+hear\s+from\s+you", re.I)
GENEL_RU = re.compile(r"Если\s+в\s+течение\s+24\s+часов\s+после\s+получения\s+макета", re.I)
SHOP = "39729443"


def sinif(en):
    """-> PLAN / DUR_ESKI / ZATEN_ADAY / FAIL / VARYANT (EN, norm edilmis metin)."""
    g, e, gen = en.count(SIL_EN), en.count(SIL_EN_ESKI), len(GENEL_EN.findall(en))
    if e:
        return "DUR_ESKI"
    if g >= 2:
        return "FAIL"
    if g == 1 and gen == 1:
        return "PLAN"
    if gen == 0:
        return "ZATEN_ADAY"
    return "VARYANT"


def paragraf_farki(a, b):
    pa, pb = a.split("\n\n"), b.split("\n\n")
    if len(pa) != len(pb):
        return None
    return [i for i, (x, y) in enumerate(zip(pa, pb)) if x != y]


def plan_ilan(kayit, shop=SHOP):
    """kayit = p1_poster_oku HAM/<id>.json -> satir (dict). Yazim yok."""
    lid = kayit["listing_id"]
    s = dict(listing_id=lid, durum="", neden=[], state="", en_go=0, en_eski=0, ru_durum=kayit.get("ru_durum"),
             kur_once_esit=False, kur_yeni_pass=False, ru_beklenen_esit=False, en_fark_par="", ru_fark_par="", kapi_uyari=0,
             tahmini_istek=ISTEK_TIPIK, istek_butce=ISTEK_ILAN)
    if kayit.get("ru_durum") == "okunamadi" or "listing" not in kayit:
        s.update(durum="DUR", neden=["ham okuma hatasi (okunamadi)"]); return s, None
    x, ru = kayit["listing"], kayit.get("ru") or {}
    en0, ru0 = P.norm(x.get("description")), P.norm(ru.get("description"))
    s.update(state=x.get("state"), en_go=en0.count(SIL_EN), en_eski=en0.count(SIL_EN_ESKI))
    sn = sinif(en0)
    if sn == "ZATEN_ADAY":   # inceleme 4 Kas D-1: yarim yazim / varyant ZATEN_YENI sayilmaz
        ok = (kayit.get("ru_durum") == "var" and not GENEL_RU.search(ru0) and YENI_EN in en0.split("\n\n")
              and YENI_RU in ru0.split("\n\n") and x.get("state") == "active")
        if ok:
            s.update(durum="ZATEN_YENI"); return s, None
        s.update(durum="DUR", neden=["EN'de soz yok ama yeni durum tam degil (RU eski / yeni paragraf yok / state / RU yok): yarim"])
        return s, None
    if sn != "PLAN":
        s["neden"].append({"DUR_ESKI": "eski varyant (we print the design as shown)", "FAIL": f"FAIL: soz {s['en_go']} kez",
                           "VARYANT": "soz var ama birebir varyant degil (kesme isareti / bosluk)"}[sn])
    if x.get("state") != "active":
        s["neden"].append(f"state {x.get('state')}")
    if kayit.get("ru_durum") != "var" or not ru0.strip():
        s["neden"].append(f"RU {kayit.get('ru_durum')}")
    if not P.norm(ru.get("title")).strip():   # poster_metin_kuru.py:86-87 (yazimda RU title zorunlu)
        s["neden"].append("RU baslik okunamadi / bos")
    by = P.boylar(kayit.get("inventory") or {})
    ru_kur0, k0 = R.kur(en0, {"boy": by})
    s["kur_once_esit"] = bool(k0.get("pass_")) and ru_kur0.strip() == ru0.strip()
    if not s["kur_once_esit"]:
        s["neden"].append("kur(EN once) != canli RU")
    en1 = en0.replace(SIL_EN, "") if sn == "PLAN" else en0
    ru1, k1 = R.kur(en1, {"boy": by})
    s["kur_yeni_pass"] = bool(k1.get("pass_"))
    if not s["kur_yeni_pass"]:
        s["neden"].append(f"kur(EN yeni) FAIL: {k1.get('hata')}")
    s["ru_beklenen_esit"] = ru0.count(SIL_RU) == 1 and ru1.strip() == ru0.replace(SIL_RU, "").strip()
    if not s["ru_beklenen_esit"]:
        s["neden"].append("yeni RU != canli RU eksi SIL_RU")
    fe, fr = paragraf_farki(en0.strip(), en1.strip()), paragraf_farki(ru0.strip(), ru1.strip())
    s.update(en_fark_par=fe, ru_fark_par=fr)
    if not (fe and len(fe) == 1 and en1.strip().split("\n\n")[fe[0]] == YENI_EN):
        s["neden"].append(f"EN fark paragraf {fe}")
    if not (fr and len(fr) == 1 and ru1.strip().split("\n\n")[fr[0]] == YENI_RU):
        s["neden"].append(f"RU fark paragraf {fr}")
    E.METIN_UYARI.clear()
    en_govde = E.html_coz({"description": en1})
    ru_govde = E.html_coz({"title": P.norm(ru.get("title")), "description": ru1, "tags": ",".join(ru.get("tags") or [])})
    kapi = E.metin_yasak_kapisi("PATCH", f"/shops/{shop}/listings/{lid}", data=en_govde)
    kapi += E.metin_yasak_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru", data=ru_govde)
    s["kapi_uyari"] = len(kapi)
    if kapi:
        s["neden"].append(f"metin kapisi uyari {len(kapi)}")
    if not (E.beyan_var(en1, "en") and E.beyan_var(ru1, "ru")):
        s["neden"].append("AI beyani eksik")
    if s["kur_yeni_pass"]:
        try:
            R.izin_ver(lid, ru1, dict(k1, sorunlar=""))
            E.ru_yazim_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru", data=ru_govde)
        except SystemExit as e:
            s["neden"].append(f"RU kapisi: {e}")
    if re.search(r"[{}]", en1 + ru1):   # poster_metin_kuru.py:94
        s["neden"].append("suslu parantez kaldi")
    s["durum"] = "DUR" if s["neden"] else "PLAN"
    detay = dict(listing_id=lid, en_once=en0, en_sonra=en1, ru_once=ru0, ru_sonra=ru1, ru_geri=ru_kur0,
                 onay_ozet=R.onay_ozet(en1, ru1), once_ozet=R.onay_ozet(en0, ru0), boylar=by,
                 yedek=dict(title=x.get("title"), tags=x.get("tags"), materials=x.get("materials"),
                            last_modified_timestamp=x.get("last_modified_timestamp"),
                            ru=dict(title=ru.get("title"), tags=ru.get("tags"))))
    return s, detay


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ham, out = pathlib.Path(a.ham), pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    kok = pathlib.Path(__file__).resolve().parents[2]
    ids = [r["listing_id"].strip() for r in csv.DictReader(open(kok / "data" / "pod" / "pod78_ids.csv", encoding="utf-8-sig"))]
    satir, detay = [], {}
    for lid in ids:
        f = ham / "HAM" / f"{lid}.json"
        if not f.exists():
            satir.append(dict(listing_id=lid, durum="DUR", neden=["ham dosya yok (okunmadi / kota)"])); continue
        s, d = plan_ilan(json.loads(f.read_text(encoding="utf-8")))
        satir.append(s)
        if d:
            detay[lid] = d
    alan = ["listing_id", "durum", "neden", "state", "en_go", "en_eski", "ru_durum", "kur_once_esit", "kur_yeni_pass",
            "ru_beklenen_esit", "en_fark_par", "ru_fark_par", "kapi_uyari", "tahmini_istek", "istek_butce", "onay_ozet"]
    for s in satir:
        s["neden"] = "; ".join(s.get("neden") or []); s["onay_ozet"] = (detay.get(s["listing_id"]) or {}).get("onay_ozet", "")
    with open(out / "FARK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader()
        w.writerows([s for s in satir if s["durum"] == "PLAN"])
    with open(out / "DUR.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader()
        w.writerows([s for s in satir if s["durum"] != "PLAN"])
    (out / "ONCE_SONRA.json").write_text(json.dumps(detay, ensure_ascii=False, indent=1), encoding="utf-8")
    diger = []
    sayim = ham / "AKTIF_SAYIM.csv"
    if sayim.exists():
        diger = [r for r in csv.DictReader(open(sayim, encoding="utf-8")) if r["grup"] != "poster78" and int(r["genel"] or 0) > 0]
    with open(out / "DIGER_URUNLER.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["listing_id", "grup", "genel", "go_ahead", "eski"], lineterminator="\n")
        w.writeheader(); w.writerows(diger)
    oz = dict(ilan=len(ids), plan=sum(s["durum"] == "PLAN" for s in satir), dur=sum(s["durum"] == "DUR" for s in satir),
              zaten_yeni=sum(s["durum"] == "ZATEN_YENI" for s in satir), kur_yeni_pass=sum(bool(s.get("kur_yeni_pass")) for s in satir),
              kapi_uyari_toplam=sum(int(s.get("kapi_uyari") or 0) for s in satir), diger_urun_eslesen=len(diger),
              tahmini_istek_yazim_tipik=ISTEK_TIPIK * sum(s["durum"] == "PLAN" for s in satir),
              istek_butce_yazim=ISTEK_ILAN * sum(s["durum"] == "PLAN" for s in satir))
    (out / "OZET.json").write_text(json.dumps(oz, indent=1), encoding="utf-8")
    print("P1 KURU:", json.dumps(oz), flush=True)
    return 0 if oz["plan"] + oz["dur"] + oz["zaten_yeni"] == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
