#!/usr/bin/env python3
"""Kendi paylasim sistemi: ana yurutucu (plan 4.1-4.7).

Modlar:
  yayin  [--kuru]                      zamani gelmis + ONAY'li + DURUM'u bos satirlari paylasir (kuru: hicbir sey yazmaz)
  onayla --satirlar 3,4 --onay SERDAR_YYYYMMDD [--kuru]
                                       Serdar onayindan sonra Merkez kosar: satir dogrulanir, medya indirilir,
                                       ONAY + ONAY_OZET yazilir, IG/Threads medyasi --medya-kok altina konur
  kontrol                              acik platformlarin kimligini salt okuma ile dogrular (yazim yok)
Anahtarlar: SOSYAL_YAYIN_ACIK=true ve YAYIN_IG / YAYIN_FB / YAYIN_THREADS / YAYIN_YT = true (yoksa o platform KAPALI).
Hata ya da KACTI: Drive <SOSYAL_UYARI_KLASOR>/SOSYAL_HATA_<YYYYMMDD>.md (token yok). Cikis 1 = en az bir HATA/KACTI."""
import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import Hata, Http, drive_oku, drive_yaz, log, temizle  # noqa: E402
import kimlik  # noqa: E402
import medya as M  # noqa: E402
import secim  # noqa: E402
import takvim as T  # noqa: E402
from kanal import facebook, instagram, threads, youtube  # noqa: E402

MODUL = {"instagram": instagram, "facebook": facebook, "threads": threads, "youtube": youtube}
ANAHTAR = {"instagram": "YAYIN_IG", "facebook": "YAYIN_FB", "threads": "YAYIN_THREADS", "youtube": "YAYIN_YT"}
UYARI_KLASOR = os.environ.get("SOSYAL_UYARI_KLASOR", "OFIS")


def acik_platformlar():
    if os.environ.get("SOSYAL_YAYIN_ACIK") != "true":
        return set()
    return {p for p, a in ANAHTAR.items() if os.environ.get(a) == "true"}


def ts(simdi):
    return simdi.strftime("%Y-%m-%dT%H:%M%z")


def uyari_yaz(satirlar, simdi):
    if not satirlar:
        return
    yol = f"{UYARI_KLASOR}/SOSYAL_HATA_{simdi.strftime('%Y%m%d')}.md"
    try:
        eski = drive_oku(yol)
    except Hata:
        eski = f"# SOSYAL_HATA {simdi.strftime('%Y-%m-%d')} (sosyal-yayin; token yok)\n"
    drive_yaz(yol, eski + "".join(f"- {ts(simdi)} {temizle(s)}\n" for s in satirlar))


def yayin(http, tk, simdi, kuru, uyku=None):
    acik = acik_platformlar()
    satirlar = tk.oku()
    uyari, ozet_say = [], {}
    kimlikler = {}
    with tempfile.TemporaryDirectory() as td:
        for s in satirlar:
            kod, neden = secim.karar(s, simdi, acik if not kuru else set(MODUL))
            if kod == "YAYINLA":
                try:
                    md = M.indir(s, Path(td) / s["satir_no"])
                    kod, neden = secim.karar(s, simdi, acik if not kuru else set(MODUL), [m["md5"] for m in md])
                    if kod == "YAYINLA":
                        M.genel_dogrula(http, md)
                except Hata as e:
                    kod, neden = "MEDYA", str(e)
            ozet_say[kod] = ozet_say.get(kod, 0) + 1
            etiket = f"satir {s['satir_no']} {s.get('platform')}/{s.get('tur')}"
            if kod in ("BEKLE", "ATLA", "ONAYSIZ", "KAPALI"):
                continue
            if kod in ("GECERSIZ", "OZET_FARKLI", "MEDYA"):
                log(f"{etiket}: {kod} {neden}")
                uyari.append(f"{etiket}: {kod} {neden}")
                continue
            if kod == "KACTI":
                log(f"{etiket}: KACTI")
                if not kuru:
                    tk.yaz(s, DURUM=f"KACTI {ts(simdi)}")
                uyari.append(f"{etiket}: KACTI ({neden})")
                continue
            # YAYINLA
            if kuru:
                log(f"{etiket}: KURU yayinlanirdi ({len(md)} medya)")
                continue
            if tk.durum_oku(s):
                log(f"{etiket}: ATLA (DURUM baska kosuca yazilmis)")
                continue
            tk.yaz(s, DURUM=f"BEKLIYOR {ts(simdi)}")
            try:
                if s["platform"] not in kimlikler:
                    kimlikler[s["platform"]] = kimlik.oku(s["platform"])
                arg = {} if uyku is None else {"uyku": uyku}
                no = MODUL[s["platform"]].yayinla(http, kimlikler[s["platform"]], s, md, **arg)
                tk.yaz(s, DURUM=f"TAMAM {ts(simdi)}", sonuc_no=str(no))
                log(f"{etiket}: TAMAM {no}")
            except Hata as e:
                tk.yaz(s, DURUM=f"HATA {ts(simdi)}", **{"not": ("BELIRSIZ " if e.belirsiz else "") + str(e)[:200]})
                log(f"{etiket}: HATA {e}")
                uyari.append(f"{etiket}: HATA {'(belirsiz: platformda elle bak) ' if e.belirsiz else ''}{e}")
            except Exception as e:  # beklenmeyen: metin temizlenir, satir HATA kalir (yeniden deneme yok)
                tk.yaz(s, DURUM=f"HATA {ts(simdi)}", **{"not": f"BELIRSIZ {type(e).__name__}"})
                uyari.append(f"{etiket}: HATA (belirsiz) {type(e).__name__} {temizle(e)}")
    log("OZET " + " ".join(f"{k}={v}" for k, v in sorted(ozet_say.items())) + f" | acik={','.join(sorted(acik)) or '-'} | kuru={kuru}")
    if not kuru:
        uyari_yaz(uyari, simdi)
    return 1 if uyari else 0


def onayla(http, tk, nolar, onay, medya_kok, kuru):
    if not secim.ONAY_RX.match(onay):
        raise Hata("onay bicimi SERDAR_YYYYMMDD degil")
    satirlar = {s["satir_no"].strip(): s for s in tk.oku()}
    eksik = [n for n in nolar if n not in satirlar]
    if eksik:
        raise Hata(f"takvimde yok: {','.join(eksik)}")
    hata = 0
    with tempfile.TemporaryDirectory() as td:
        for n in nolar:
            s = satirlar[n]
            h = secim.dogrula(s)
            if (s.get("DURUM") or "").strip():
                h.append("DURUM bos degil")
            if h:
                log(f"satir {n}: ONAYLANMADI {'; '.join(h)}")
                hata = 1
                continue
            try:
                md = M.indir(s, Path(td) / n)
            except Hata as e:
                log(f"satir {n}: ONAYLANMADI {e}")
                hata = 1
                continue
            oz = secim.ozet(s, [m["md5"] for m in md])
            if kuru:
                log(f"satir {n}: KURU onaylanirdi ozet={oz}")
                continue
            M.genele_koy(md, medya_kok)
            tk.yaz(s, ONAY=onay, ONAY_OZET=oz)
            log(f"satir {n}: ONAY {onay} ozet={oz}")
    return hata


def kontrol(http):
    acik = acik_platformlar() or set(MODUL)
    hata = 0
    for p in sorted(acik):
        try:
            ad = MODUL[p].kimlik_dogrula(http, kimlik.oku(p))
            log(f"{p}: kimlik PASS ({ad})")
        except Hata as e:
            log(f"{p}: kimlik FAIL {e}")
            hata = 1
    return hata


def main(argv=None, http=None, simdi=None, uyku=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["yayin", "onayla", "kontrol"])
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--satirlar", default="")
    ap.add_argument("--onay", default="")
    ap.add_argument("--medya-kok", default="media")
    a = ap.parse_args(argv)
    http = http or Http()
    simdi = simdi or datetime.now(secim.TZ)
    try:
        if a.mod == "kontrol":
            return kontrol(http)
        tk = T.Takvim(http, T.google_token(http))
        if a.mod == "yayin":
            return yayin(http, tk, simdi, a.kuru, uyku)
        nolar = [x.strip() for x in a.satirlar.split(",") if x.strip()]
        if not nolar:
            raise Hata("--satirlar bos")
        return onayla(http, tk, nolar, a.onay.strip(), a.medya_kok, a.kuru)
    except Hata as e:
        log(f"DUR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
