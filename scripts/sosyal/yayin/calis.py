#!/usr/bin/env python3
"""Kendi paylasim sistemi: ana yurutucu (plan 4.1-4.7).

Modlar:
  yayin  [--kuru]                      zamani gelmis + ONAY'li + DURUM'u bos satirlari paylasir (kuru: hicbir sey yazmaz)
  onayla --satirlar 3,4 --onay SERDAR_YYYYMMDD --asama hazirla|yaz [--plan F] [--kuru]
                                       Serdar onayindan sonra Merkez kosar. hazirla: dogrula, medya indir, IG/Threads
                                       medyasini --medya-kok altina koy, plan yaz. yaz: (medya push'undan sonra) ONAY + ONAY_OZET
  kontrol                              acik platformlarin kimligini salt okuma ile dogrular (yazim yok)
Anahtarlar: SOSYAL_YAYIN_ACIK=true ve YAYIN_IG / YAYIN_FB / YAYIN_THREADS / YAYIN_YT = true (yoksa o platform KAPALI).
Hata ya da KACTI: Drive <SOSYAL_UYARI_KLASOR>/SOSYAL_HATA_<YYYYMMDD>.md (token yok). Cikis 1 = en az bir HATA/KACTI."""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
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


def _bekliyor_eski(s, simdi):
    """BEKLIYOR 1 saatten eskiyse ve daha once uyarilmadiysa True (yarim kalmis kosu; tek uyari, isaret `not` hucresinde)."""
    p = (s.get("DURUM") or "").split()
    if not p or p[0] != "BEKLIYOR" or len(p) < 2:
        return False
    try:
        t = datetime.strptime(p[1], "%Y-%m-%dT%H:%M%z")
    except ValueError:
        return False
    return simdi - t >= timedelta(hours=1) and "UYARILDI" not in (s.get("not") or "")


GIZLI = {"youtube": "private", "facebook": "taslak"}


def yayin(http, tk, simdi, kuru, uyku=None, gizli_test=""):
    acik = acik_platformlar()
    satirlar = tk.oku()
    if gizli_test:
        # Gizli test (Merkez 25 Kas): yalniz bu satir; yalniz YouTube private / Facebook taslak. Ana anahtar ACILMAZ;
        # bu kosuda yalniz satirin platformu acik sayilir. Onay kapisi (ONAY + ONAY_OZET) aynen gecerli.
        sec = [s for s in satirlar if (s.get("satir_no") or "").strip() == gizli_test]
        if len(sec) != 1:
            raise Hata(f"gizli test: satir {gizli_test} takvimde tek degil ({len(sec)})")
        s0 = sec[0]
        p0 = (s0.get("platform") or "").strip()
        if GIZLI.get(p0) != (s0.get("gorunurluk") or "").strip():
            raise Hata(f"gizli test: yalniz youtube+private ya da facebook+taslak satiri (satir {gizli_test}: {p0}/{s0.get('gorunurluk')})")
        satirlar, acik = sec, {p0}
        log(f"GIZLI TEST satir {gizli_test} {p0}/{GIZLI[p0]}")
    uyari, ozet_say = [], {}
    kimlikler = {}
    with tempfile.TemporaryDirectory() as td:
        for s in satirlar:
            etiket = f"satir {s.get('satir_no')} {s.get('platform')}/{s.get('tur')}"
            kod, neden = secim.karar(s, simdi, acik if not kuru else set(MODUL))
            if kod == "ATLA" and _bekliyor_eski(s, simdi):
                uyari.append(f"{etiket}: BEKLIYOR 1 saatten eski (kosu yarim kalmis olabilir; platformda elle bakin, satiri elle duzeltin)")
                if not kuru:
                    try:
                        tk.tazele(s)
                        tk.yaz(s, **{"not": ((s.get("not") or "") + " UYARILDI").strip()})
                    except Exception as e:
                        uyari.append(f"DUR {etiket}: {temizle(e)}")
                        break
            if kod == "YAYINLA":
                try:
                    md = M.indir(s, Path(td) / s["satir_no"])
                    kod, neden = secim.karar(s, simdi, acik if not kuru else set(MODUL), [m["md5"] for m in md])
                    if kod == "YAYINLA":
                        M.genel_dogrula(http, md)
                except Hata as e:
                    kod, neden = "MEDYA", str(e)
            ozet_say[kod] = ozet_say.get(kod, 0) + 1
            if gizli_test and kod not in ("YAYINLA",):
                uyari.append(f"GIZLI TEST {etiket}: yayinlanmadi ({kod} {neden})")
                log(f"GIZLI TEST {etiket}: yayinlanmadi ({kod} {neden})")
                if kod != "KACTI":
                    continue
            if kod in ("BEKLE", "ATLA", "ONAYSIZ", "KAPALI"):
                continue
            if kod in ("GECERSIZ", "OZET_FARKLI", "MEDYA"):
                log(f"{etiket}: {kod} {neden}")
                uyari.append(f"{etiket}: {kod} {neden}")
                continue
            if kod == "KACTI":
                log(f"{etiket}: KACTI")
                uyari.append(f"{etiket}: KACTI ({neden})")
                if not kuru:
                    try:
                        tk.tazele(s)
                        tk.yaz(s, DURUM=f"KACTI {ts(simdi)}")
                    except Exception as e:
                        uyari.append(f"DUR {etiket}: {temizle(e)}")
                        break
                continue
            # YAYINLA
            if kuru:
                log(f"{etiket}: KURU yayinlanirdi ({len(md)} medya)")
                continue
            try:
                taze = tk.tazele(s)  # satir kaymasi: satir_no + ONAY_OZET ayni yerde mi
            except Hata as e:
                uyari.append(f"DUR {etiket}: {e}")
                log(f"DUR {etiket}: {e}")
                break
            if (taze.get("DURUM") or "").strip():
                log(f"{etiket}: ATLA (DURUM baska kosuca yazilmis)")
                continue
            tk.yaz(s, DURUM=f"BEKLIYOR {ts(simdi)}")
            try:
                if s["platform"] not in kimlikler:
                    kimlikler[s["platform"]] = kimlik.oku(s["platform"])
                arg = {} if uyku is None else {"uyku": uyku}
                no = MODUL[s["platform"]].yayinla(http, kimlikler[s["platform"]], s, md, **arg)
            except Hata as e:
                _hata_yaz(tk, s, simdi, ("BELIRSIZ " if e.belirsiz else "") + str(e)[:200], uyari)
                uyari.append(f"{etiket}: HATA {'(belirsiz: platformda elle bak) ' if e.belirsiz else ''}{e}")
                log(f"{etiket}: HATA {e}")
                continue
            except Exception as e:  # beklenmeyen: metin temizlenir, satir HATA kalir (yeniden deneme yok)
                _hata_yaz(tk, s, simdi, f"BELIRSIZ {type(e).__name__}", uyari)
                uyari.append(f"{etiket}: HATA (belirsiz) {type(e).__name__} {temizle(e)}")
                continue
            # YAYINLANDI: bundan sonraki her hata "yayinlandi" diye raporlanir, HATA yazilmaz (yeniden paylasim riski)
            try:
                tk.tazele(s)
                tk.yaz(s, DURUM=f"TAMAM {ts(simdi)}", sonuc_no=str(no))
                log(f"{etiket}: TAMAM {no}")
            except Exception as e:
                uyari.append(f"{etiket}: YAYINLANDI no={no} ama takvime TAMAM yazilamadi ({temizle(e)}); satiri elle TAMAM {no} yapin")
                log(f"DUR {etiket}: YAYINLANDI no={no}, TAMAM yazilamadi")
                break
    log("OZET " + " ".join(f"{k}={v}" for k, v in sorted(ozet_say.items())) + f" | acik={','.join(sorted(acik)) or '-'} | kuru={kuru}")
    if not kuru:
        uyari_yaz(uyari, simdi)
    return 1 if uyari else 0


def _hata_yaz(tk, s, simdi, notu, uyari):
    try:
        tk.yaz(s, DURUM=f"HATA {ts(simdi)}", **{"not": notu})
    except Exception as e:
        uyari.append(f"satir {s.get('satir_no')}: HATA takvime yazilamadi ({temizle(e)}); DURUM BEKLIYOR kaldi")


def onayla(http, tk, nolar, onay, medya_kok, kuru, plan_yolu, asama):
    """Iki asama (inceleme bulgusu: ONAY, medya yayina girmeden yazilmaz).
    hazirla: satir dogrulanir, medya indirilir, IG/Threads medyasi --medya-kok altina konur, plan JSON yazilir (takvime yazim yok).
    yaz:     (is akisi medyayi push ettikten sonra) plan okunur; satir hala ayniysa (ozet, kayitli md5 ile) ONAY + ONAY_OZET yazilir."""
    if not secim.ONAY_RX.match(onay):
        raise Hata("onay bicimi SERDAR_YYYYMMDD degil")
    satirlar = {s["satir_no"].strip(): s for s in tk.oku()}
    eksik = [n for n in nolar if n not in satirlar]
    if eksik:
        raise Hata(f"takvimde yok: {','.join(eksik)}")
    hata = 0
    if asama == "yaz":
        plan = json.loads(Path(plan_yolu).read_text())
        if plan.get("onay") != onay:
            raise Hata("plan onayi girdiyle ayni degil")
        for n in nolar:
            if n not in plan["satirlar"]:
                log(f"satir {n}: ONAYLANMADI (hazirla asamasinda gecmedi)")
                hata = 1
                continue
            s, p = satirlar[n], plan["satirlar"][n]
            oz = secim.ozet(s, p["md5"])
            if oz != p["ozet"] or (s.get("DURUM") or "").strip():
                log(f"satir {n}: ONAYLANMADI (hazirliktan sonra satir degisti)")
                hata = 1
                continue
            tk.yaz(s, ONAY=onay, ONAY_OZET=oz)
            log(f"satir {n}: ONAY {onay} ozet={oz}")
        return hata
    plan = {"onay": onay, "satirlar": {}}
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
            plan["satirlar"][n] = {"ozet": oz, "md5": [m["md5"] for m in md]}
            log(f"satir {n}: hazir ozet={oz} (ONAY medya push'undan sonra yazilir)")
    if not kuru:
        Path(plan_yolu).write_text(json.dumps(plan))
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
    ap.add_argument("--asama", choices=["hazirla", "yaz"], default="hazirla")
    ap.add_argument("--plan", default="_onay_plan.json")
    ap.add_argument("--gizli-test", default="", help="yalniz bu satir_no; youtube private / facebook taslak")
    a = ap.parse_args(argv)
    http = http or Http()
    simdi = simdi or datetime.now(secim.TZ)
    try:
        if a.mod == "kontrol":
            return kontrol(http)
        tk = T.Takvim(http, T.google_token(http))
        if a.mod == "yayin":
            if a.gizli_test and not a.gizli_test.isdigit():
                raise Hata("--gizli-test sayi olmali")
            return yayin(http, tk, simdi, a.kuru, uyku, a.gizli_test)
        nolar = [x.strip() for x in a.satirlar.split(",") if x.strip()]
        if not nolar:
            raise Hata("--satirlar bos")
        return onayla(http, tk, nolar, a.onay.strip(), a.medya_kok, a.kuru, a.plan, a.asama)
    except Hata as e:
        log(f"DUR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
