#!/usr/bin/env python3
"""Kupa bilgi kartlari, 78 Orchard kupa cifti, galeri 2-6 (Serdar gece istisnasi 30 Eki). ETSY API YOK, Canva yok, Drive'a burada yazilmaz.
Kart cizimi, metin / Title Case / yasak / renk / yerlesim / zemin kapilari: wa_kupa_kart_ornek.kart_isle (28 Eki onayli kod, AYNEN; paylasilan
dosyalara dokunulmaz). Yalniz 5 kupa karti (WA ve YD kartlari yok):
  galeri 2 K02 sembol, 3 K03 kisisellestirme, 4 K05 boyut, 5 K07 surec, 6 K04 stil genel bakis.
Gorunumler wa-kupa-kart-ornek.yml mod=uret yoluyla ayni: orchard_gorunum.py (_v12 ortami, temiz/kupa-orchard 0196e37) + kupa_zemin
(kart ortami; ayni esitle / _isle fonksiyonu, yalniz kartlarin kullandigi 11 sahne: tek_on, tek_arka, m15, stil_*; ML / MJ sahneleri
kartlarda kullanilmaz). Sembol kupa-printful-sonuc ac9aa71.
AYNI BURC CIFTLERI (12, orn. LEO_LEO; Serdar 30 Eki): K03 etiketleri "Name Under X" cifti yerine "First Name" / "Second Name". Yalniz bu
sarmalayicida: K03 cizime giden etiketler ve metin kapisinin beklenen listesi birlikte degisir (diger satirlar W.beklenen'den aynen).
AYNI BURC K02 (Serdar 31 Eki karar 2b): alt baslik "<A> and <A> joined in an original AstroLoveArt design" yerine galeri alt metniyle
harfi harfine ayni cumle (data/pod/kupa_galeri78_alt.csv sira 2 alt_ayni_burc, <A> yerine burc). Yalniz o satir degisir (cizim yeri,
punto, renk ayni; K.yaz tek satir, sigmazsa DUR); metin kapisinin beklenen listesi birlikte degisir.
ISTISNA (Serdar 31 Eki karar 1a): yalniz GEMINI_SCORPIO K05 kopuk ton kapisi; olcum BIREBIR (3 px, parca [2393, 1489, 20, 10, 3], en buyuk
fark 4/255) ise kapi gecer ve istisna SONUC / MANIFEST / OZET'e yazilir. Olcum farkliysa kapi aynen FAIL. Kapi kurali ve ortak kod degismez.
Her cift try/except: bir kart FAIL ise ciftin HICBIR karti yazilmaz; neden SONUC_<CIFT>.json'a yazilir.
Kullanim:
  kupa_kart78.py uret --ciftler <dosya, satir basina CIFT> --ko <kupa_orchard> --sembol-kok <kupa_uretim/sembol> --v12 <python> --is <dir> --out <dir>
  kupa_kart78.py topla --dir <SONUC + jpg> --ciftler-csv data/pod/yd78_ids.csv --secim <dosya> --out <dir> [--ref <28 Eki ornek dir>] [--kaynak T]
Cikis: 0 = tum ciftler PASS (ve kiyas PASS), 1 = FAIL var."""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

KARTLAR = (("K02", 2, "K02_SEMBOL"), ("K03", 3, "K03_KISISEL"), ("K05", 4, "K05_BOYUT"), ("K07", 5, "K07_SUREC"), ("K04", 6, "K04_STIL"))
GALERI = {k: g for k, g, _ in KARTLAR}
ZEMIN_SAHNE = ("tek_on", "tek_arka", "m15") + tuple(f"stil_{s}" for s in ("orange", "fig", "olive", "pomegranate", "almond", "lemon",
                                                                             "grape", "loquat"))
AYNI_ETIKET = ("First Name", "Second Name")
KIYAS_ORT, KIYAS_MAX = 1.0, 16          # gorev: sha farkliysa ortalama mutlak fark <= 1,0 ve en buyuk fark <= 16
MANIFEST_ALAN = ["cift", "kart", "galeri_no", "dosya", "sha256", "durum", "neden", "istisna"]
KOK = HERE.parents[1]
GALERI_ALT = KOK / "data/pod/kupa_galeri78_alt.csv"
ISTISNA = {("GEMINI_SCORPIO", "K05"): dict(kapi="kopuk_ton", px=3, parca=[[2393, 1489, 20, 10, 3]], max_fark=4,
                                           karar="Serdar 31 Eki karar 1a: yalniz bu cift + kart; olculen 3 px, en buyuk fark 4/255")}


def k02_ayni_metin(a):
    """Ayni burc K02 alt basligi = galeri alt metni sira 2 alt_ayni_burc (tek kaynak)."""
    r = next(x for x in csv.DictReader(open(GALERI_ALT, encoding="utf-8")) if x["sira"] == "2")
    t = (r["alt_ayni_burc"] or "").strip()
    if not t.startswith("Two <A> signs joined"):
        raise SystemExit(f"DUR: galeri alt metni sira 2 alt_ayni_burc beklenen kalipta degil: {t!r}")
    return t.replace("<A>", a)


def ayni_burc(a, b):
    return a.casefold() == b.casefold()


def beklenen_cift(W, a, b):
    """W.beklenen + ayni burcta K03 etiketleri First Name / Second Name (yalniz o iki oge degisir)"""
    bek = W.beklenen(a, b)
    if ayni_burc(a, b):
        k2 = list(bek["K02_SEMBOL"])
        assert k2[1] == f"{a} and {b} joined in an original AstroLoveArt design", k2
        k2[1] = k02_ayni_metin(a)
        bek["K02_SEMBOL"] = k2
        k = list(bek["K03_KISISEL"])
        i = k.index(f"Name Under {a}")
        assert k[i + 1] == f"Name Under {b}", k
        k[i:i + 2] = AYNI_ETIKET
        bek["K03_KISISEL"] = k
    return bek


def k03_ayni(W, S, a, b, sd, bek):
    """W.k03 ile ayni cagri; etiket satirlari ve metinler beklenen listesinden (tek kaynak)"""
    k = bek["K03_KISISEL"]          # [baslik, et1, et2, metin1, et3, metin2, et4, metin3, alt not]
    (on, ko), (ar, ka) = W.sahne(sd, "tek_on"), W.sahne(sd, "tek_arka")
    im, o, kut = S.yan_kart(k[0], [on, ar], [(None, [k[1], k[2]], k[3]), (None, [k[4]], k[5]), (None, [k[6]], k[7])], k[8])
    return im, dict(o, kirpim=dict(tek_on=ko, tek_arka=ka)), kut


def sembol_ayni(S, K, a, b, sem, alt, yeni, olcu):
    """S.sembol_kart AYNEN; yalniz alt baslik satiri (K.yaz cagrisi) yeni metinle. Genislik olcusu olcu'ya yazilir."""
    eski, asil = f"{a} and {b} joined in an original AstroLoveArt design", K.yaz

    def yaz(d, st, satirlar, x, y, hiza="left", gen=None):
        if satirlar == [eski]:
            satirlar = [yeni]
            olcu.update(metin=yeni, genislik_px=round(K.genislik(st, yeni)), izin_px=round(gen) if gen else None, satir=1,
                        eski_genislik_px=round(K.genislik(st, eski)))
        return asil(d, st, satirlar, x, y, hiza, gen)
    K.yaz = yaz
    try:
        r = S.sembol_kart(a, b, sem, alt)
    finally:
        K.yaz = asil
    if olcu.get("metin") != yeni:
        raise SystemExit("DUR: K02 alt baslik satiri bulunamadi (kart_sablon degismis olabilir)")
    return r


def kartlar(W, S, K, c, a, b, sem, sd, kayit=None):
    """-> {kart: jpeg bayt}, rapor. kart_isle kapilarindan biri FAIL ise SystemExit (hicbir kart donmez)"""
    import numpy as np
    kayit = {} if kayit is None else kayit
    bek = beklenen_cift(W, a, b)
    yok = lambda f: (lambda: (*f(), ()))
    k03 = (lambda: k03_ayni(W, S, a, b, sd, bek)) if ayni_burc(a, b) else (lambda: W.k03(a, b, sd))
    alt = bek["K02_SEMBOL"][-1]
    k02o = {}
    k02 = (lambda: sembol_ayni(S, K, a, b, sem, alt, bek["K02_SEMBOL"][1], k02o)) if ayni_burc(a, b) else (lambda: S.sembol_kart(a, b, sem, alt))
    islem = [(f"KUPA_{c}_K02_SEMBOL.jpg", "K02_SEMBOL", k02),
             (f"KUPA_{c}_K03_KISISEL.jpg", "K03_KISISEL", yok(k03)),
             (f"KUPA_{c}_K05_BOYUT.jpg", "K05_BOYUT", yok(lambda: W.k05(sd))),
             (f"KUPA_{c}_K07_SUREC.jpg", "K07_SUREC", yok(lambda: W.k07(sd))),
             (f"KUPA_{c}_K04_STIL.jpg", "K04_STIL", yok(lambda: W.k04(sd)))]      # ad "KUPA_" ile baslar: kart_isle zemin kapisi
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()
    simdi, istisna, asil = {}, [], W.kopuk_ton
    islem = [(ad, an, (lambda f, k: (lambda: (simdi.update(kart=k), f())[1]))(fn, ad.split("_")[-2])) for ad, an, fn in islem]

    def kopuk(im, kutular, **kw):                       # yalniz ISTISNA'daki cift + kart + birebir olcum
        n, liste = asil(im, kutular, **kw)
        ist = ISTISNA.get((c, simdi.get("kart")))
        if ist and n == ist["px"] and liste == ist["parca"]:
            x, y, w_, h, _ = liste[0]
            f = np.abs(np.asarray(im.convert("RGB")).astype(np.int16)[y:y + h, x:x + w_] - np.int16(K.rgb(K.ZEMIN))).max()
            if int(f) <= ist["max_fark"]:
                istisna.append(dict(kart=simdi["kart"], kapi=ist["kapi"], px=n, parca=liste, max_fark=int(f), karar=ist["karar"]))
                return 0, []
        return n, liste
    W.kopuk_ton = kopuk
    try:
        _, rapor, jb = W.kart_isle(islem, bek)
    finally:
        W.kopuk_ton = asil
    eksik = [k for (cc, k) in ISTISNA if cc == c and k not in {i["kart"] for i in istisna}]
    if eksik:   # istisna tanimli ama olcum farkli: kapi zaten FAIL verirdi; burada yalniz bilgi
        kayit["istisna_kullanilmadi"] = eksik
    kayit["istisna"] = istisna
    if k02o:
        kayit["k02_ayni_burc"] = k02o
    return {ad.split("_")[-2]: v for ad, v in jb.items()}, rapor


def zemin(sahne_dir, cikti):
    import kupa_zemin as Z
    g, o = Path(sahne_dir), Path(cikti)
    o.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        return dict(ex.map(Z._isle, [g] * len(ZEMIN_SAHNE), [o] * len(ZEMIN_SAHNE), ZEMIN_SAHNE))


def uret(a):
    # Serdar 31 Eki 8a: NumPy / OpenCV AVX512 yolu kapali; numpy bu surecte henuz yuklenmemis olmali (ortam degiskeni import aninda okunur)
    import simd_sabit
    if "numpy" in sys.modules:
        bek = simd_sabit.ayarla({})
        if any(os.environ.get(k) != v for k, v in bek.items()):
            raise SystemExit("DUR: numpy SIMD / BLAS ayarindan once yuklenmis (simd_sabit)")
    simd_sabit.ayarla(os.environ)
    simd_sabit.kapi(sys.executable, dict(os.environ), "kupa_kart78")
    import wa_kupa_kart_ornek as W
    import kart_sablon as S
    import yd_kart_ornek as K
    import cv2  # noqa: F401  (surec ici kapi OpenCV satirini da okusun)
    simd_sabit.surec_ici("kupa_kart78")
    satir = {r["cift"]: r for r in csv.DictReader(open(a.ciftler_csv, encoding="utf-8-sig"))}
    ciftler = [x.strip() for x in Path(a.ciftler).read_text().split() if x.strip()]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); fail = []
    for i, c in enumerate(ciftler, 1):
        t1 = time.time(); kayit = dict(cift=c, durum="FAIL", neden="", kartlar=[])
        try:
            r = satir[c]; A, B = r["a"], r["b"]
            sem = Path(a.sembol_kok) / c
            sd = Path(a.is_) / c
            p = subprocess.run([a.v12, "-I", str(HERE / "orchard_gorunum.py"), a.ko, str(sem), A, B, str(sd)], capture_output=True, text=True)
            if p.returncode:
                raise SystemExit(f"DUR: orchard_gorunum rc {p.returncode}: {(p.stdout + p.stderr)[-600:]}")
            kayit["zemin"] = zemin(sd / "gorunum", sd)
            jb, rapor = kartlar(W, S, K, c, A, B, sem, sd, kayit)
            for kart, _, _ in KARTLAR:                        # hepsi PASS: simdi yaz
                (out / f"{c}_{kart}.jpg").write_bytes(jb[kart])
            ist = {i["kart"]: f"{i['kapi']} {i['px']} px max {i['max_fark']}/255 ({i['karar']})" for i in kayit.get("istisna") or []}
            kayit.update(durum="PASS", kartlar=[dict(kart=k, galeri_no=GALERI[k], dosya=f"{c}_{k}.jpg",
                                                     sha256=hashlib.sha256(jb[k]).hexdigest(), istisna=ist.get(k, "")) for k, _, _ in KARTLAR],
                         ayni_burc=ayni_burc(A, B), surum=K.SURUM, simd=f"AVX512 kapali, olcum {simd_sabit.REF}",
                         olcu={ad.split("_")[-2]: {x: v for x, v in o.items() if x in ("olcek", "yerlesim", "zemin_kenar_p90_max",
                                                                                         "kopuk_ton_px", "kb")} for ad, o in rapor.items()})
        except (Exception, SystemExit) as e:                   # cift basina: FAIL cift dosya yazmaz
            kayit["neden"] = (str(e) or type(e).__name__)[:1500]
            for kart, _, _ in KARTLAR:
                (out / f"{c}_{kart}.jpg").unlink(missing_ok=True)
            fail.append(c)
        kayit["sure_sn"] = round(time.time() - t1, 1)
        (out / f"SONUC_{c}.json").write_text(json.dumps(kayit, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        if not a.sahne_tut:
            subprocess.run(["rm", "-rf", str(Path(a.is_) / c)])
        e = time.time() - t0
        print(f"ETA {i}/{len(ciftler)} ({100 * i // len(ciftler)}%) {c} {kayit['durum']} {kayit['sure_sn']}s | gecen {e:.0f}s, "
              f"kalan {e / i * (len(ciftler) - i):.0f}s {kayit['neden'][:300]}", flush=True)
    print(f"URET: {len(ciftler) - len(fail)} PASS, {len(fail)} FAIL {' '.join(fail)}")
    return 1 if fail else 0


def kiyas(yeni, ref):
    import numpy as np
    from PIL import Image
    hy, hr = hashlib.sha256(yeni.read_bytes()).hexdigest(), hashlib.sha256(ref.read_bytes()).hexdigest()
    x = np.asarray(Image.open(yeni).convert("RGB")).astype(np.int16)
    y = np.asarray(Image.open(ref).convert("RGB")).astype(np.int16)
    if x.shape != y.shape:
        return dict(sha_esit=False, boyut=[list(x.shape), list(y.shape)], durum="FAIL")
    d = np.abs(x - y)
    o, m = float(d.mean()), int(d.max())
    return dict(sha_esit=hy == hr, sha_yeni=hy, sha_ref=hr, ort=round(o, 4), max=m, fark_piksel_orani=round(float((d.max(2) > 0).mean()), 5),
                durum="PASS" if hy == hr or (o <= KIYAS_ORT and m <= KIYAS_MAX) else "FAIL")


REF_AD = {"K02": "SEMBOL", "K03": "KISISEL", "K05": "BOYUT", "K07": "SUREC", "K04": "STIL"}


def topla(a):
    import yd_kontak
    d, out = Path(a.dir), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ab = {r["cift"]: (r["a"], r["b"]) for r in csv.DictReader(open(a.ciftler_csv, encoding="utf-8-sig"))}
    tum = list(ab)
    secim = [x.strip() for x in Path(a.secim).read_text().split() if x.strip()]
    sira = [c for c in tum if c in set(secim)]
    satirlar, fail, pas = [], [], []
    for c in sira:
        f = d / f"SONUC_{c}.json"
        k = json.loads(f.read_text(encoding="utf-8")) if f.exists() else dict(cift=c, durum="FAIL", neden="SONUC yok (is kosmadi / coktu)")
        if k["durum"] == "PASS":
            for x in k["kartlar"]:
                p = d / x["dosya"]
                ok = p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == x["sha256"]
                satirlar.append(dict(cift=c, kart=x["kart"], galeri_no=x["galeri_no"], dosya=x["dosya"], sha256=x["sha256"],
                                     durum="PASS" if ok else "FAIL", neden="" if ok else "dosya yok / sha farkli", istisna=x.get("istisna", "")))
                if ok:
                    subprocess.run(["cp", str(p), str(out / x["dosya"])], check=True)
            (pas if all(s["durum"] == "PASS" for s in satirlar if s["cift"] == c) else fail).append(c)
        else:
            fail.append(c)
            satirlar += [dict(cift=c, kart=kk, galeri_no=g, dosya="", sha256="", durum="FAIL", neden=k.get("neden", "")[:400], istisna="")
                         for kk, g, _ in KARTLAR]
        if f.exists():
            subprocess.run(["cp", str(f), str(out / f.name)], check=True)
    ayni = [c for c in sira if ayni_burc(*ab[c])]
    degisim, deg_fail = [], []
    if a.onceki:   # gece MANIFEST'iyle sha kaniti (Serdar 31 Eki 1a/2b): yalniz izinli degisim (ayni burc K02 + gece FAIL olan cift).
        # Izinsiz farkta yeni uretim KULLANILMAZ: gece dosyasi aynen alinir (fotografli kartlar kosucuya gore bit duzeyinde farkli
        # cikabiliyor, 31 Eki kosu 41179645300), fark olculur ve raporlanir. Gece dosyasi yoksa / sha tutmazsa FAIL.
        once = {(r["cift"], r["kart"]): r for r in csv.DictReader(open(a.onceki, encoding="utf-8"))}
        gece_kart = {}
        gd = Path(a.onceki).parent
        for r in satirlar:
            o = once.get((r["cift"], r["kart"]))
            ayni_sha = bool(o) and o["durum"] == "PASS" and o["sha256"] == r["sha256"]
            izin = (r["kart"] == "K02" and r["cift"] in ayni) or (o is not None and o["durum"] != "PASS")
            tur, olc = ("AYNI" if ayni_sha else "IZINLI_DEGISIM" if izin else "GECE_DOSYASI"), {}
            if tur == "GECE_DOSYASI":
                g = gd / (o or {}).get("dosya", "-")
                if not g.is_file() or hashlib.sha256(g.read_bytes()).hexdigest() != (o or {}).get("sha256"):
                    tur = "IZINSIZ_DEGISIM"; deg_fail.append(f"{r['cift']} {r['kart']} gece dosyasi yok / sha farkli")
                else:
                    y = out / r["dosya"]
                    olc = kiyas(y, g) if y.is_file() else {}
                    subprocess.run(["cp", str(g), str(y)], check=True)
                    r["sha256"], r["neden"] = o["sha256"], (f"gece dosyasi (yeniden uretim farki ort {olc.get('ort')}, max {olc.get('max')})")
                    gece_kart.setdefault(r["cift"], {})[r["kart"]] = (o["sha256"], olc)
            if izin and r["kart"] == "K02" and r["cift"] in ayni and ayni_sha:
                deg_fail.append(f"{r['cift']} K02 degismedi")
            degisim.append(dict(cift=r["cift"], kart=r["kart"], once=(o or {}).get("sha256", ""), simdi=r["sha256"], tur=tur,
                                yeniden_ort=olc.get("ort", ""), yeniden_max=olc.get("max", "")))
        for c, kk in gece_kart.items():   # inceleme 31 Eki: SONUC sevk edilen (gece) dosyayla ayni sha'yi gostersin
            f = out / f"SONUC_{c}.json"
            if f.exists():
                k = json.loads(f.read_text(encoding="utf-8"))
                for x in k.get("kartlar") or []:
                    if x["kart"] in kk:
                        x["yeniden_sha256"], x["sha256"] = x["sha256"], kk[x["kart"]][0]
                        x["gece_dosyasi"], x["yeniden_fark"] = True, kk[x["kart"]][1]
                f.write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")
        yeni = [x.strip() for x in (Path(a.yeni).read_text().split() if a.yeni else []) if x.strip()]
        deg_fail += [f"{c} istendi ama 78 listesinde yok" for c in yeni if c not in sira]
        with open(out / "DEGISIM.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["cift", "kart", "once", "simdi", "tur", "yeniden_ort", "yeniden_max"])
            w.writeheader(); w.writerows(degisim)
    with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_ALAN); w.writeheader(); w.writerows(satirlar)
    kontak = []
    for kk, g, _ in KARTLAR:
        og = [(c, out / f"{c}_{kk}.jpg" if (out / f"{c}_{kk}.jpg").is_file() else None) for c in sira]
        kontak.append(dict(kart=kk, galeri_no=g, **yd_kontak.pafta(og, out / f"KONTAK_{kk}.jpg", 320, 10,
                                                                     f"KUPA {kk} galeri {g} | {len(sira)} cift | {a.kaynak}")))
        print(f"KONTAK_{kk}: hucre {kontak[-1]['hucre']} eksik {len(kontak[-1]['eksik'])}", flush=True)
    og = [(c, out / f"{c}_K02.jpg" if (out / f"{c}_K02.jpg").is_file() else None) for c in ayni]
    if og:   # Serdar 31 Eki karar 2b: ayni burc K02 (12 kart) ayri KONTAK
        k = yd_kontak.pafta(og, out / "KONTAK_K02_AYNI_BURC.jpg", 320, 6, f"KUPA K02 ayni burc {len(og)} cift | {a.kaynak}")
        kontak.append(dict(kart="K02 ayni burc", galeri_no=2, **k))
    kiy = {}
    if a.ref:
        for kk, _, _ in KARTLAR:
            y, r = out / f"CANCER_LIBRA_{kk}.jpg", Path(a.ref) / f"KUPA_CANCER_LIBRA_{kk}_{REF_AD[kk]}.jpg"
            kiy[kk] = kiyas(y, r) if y.is_file() and r.is_file() else dict(durum="FAIL", neden=f"dosya yok: yeni {y.is_file()} ref {r.is_file()}")
        (out / "KIYAS_CANCER_LIBRA.json").write_text(json.dumps(kiy, indent=1), encoding="utf-8")
    kiyas_ok = all(v["durum"] == "PASS" for v in kiy.values())
    durum = "PASS" if not fail and kiyas_ok and not deg_fail else "FAIL"
    istisnalar = [r for r in satirlar if r.get("istisna")]
    with open(out / "OZET.md", "w", encoding="utf-8") as fh:
        fh.write(f"# Kupa bilgi kartlari 78 (galeri 2-6)\n\n**{durum}** | cift {len(sira)} | PASS {len(pas)} | FAIL {len(fail)}\n\n"
                 f"Kaynak: {a.kaynak}. Etsy istegi yok. Kart: K02=2, K03=3, K05=4, K07=5, K04=6. Ayni burc K03: First Name / Second Name.\n"
                 f"Kapilar: wa_kupa_kart_ornek.kart_isle (metin, Title Case, yasak, renk cizim + JPEG, yerlesim, zemin, kopuk ton).\n\n")
        if fail:
            fh.write("## FAIL ciftler (kart yazilmadi)\n\n")
            fh.writelines(f"- {c}: {next((s['neden'] for s in satirlar if s['cift'] == c and s['neden']), '')[:300]}\n" for c in fail)
            fh.write("\n")
        fh.write("## Istisnalar (kapi kurali ve ortak kod degismedi)\n\n" + ("".join(f"- {r['cift']} {r['kart']}: {r['istisna']}\n"
                                                                                     for r in istisnalar) or "- yok\n") + "\n")
        if a.onceki:
            from collections import Counter
            say = Counter(d["tur"] for d in degisim)
            gm = [d for d in degisim if d["tur"] == "GECE_DOSYASI"]
            fh.write(f"## Gece kosusuyla sha kiyasi ({a.onceki_ad or a.onceki})\n\nBu kosuda yeniden uretilen ciftler ({len(yeni)}): "
                     f"{', '.join(yeni) or 'belirtilmedi'}. Digerleri gece dosyasi.\n\nAYNI {say['AYNI']} | IZINLI_DEGISIM {say['IZINLI_DEGISIM']} | "
                     f"GECE_DOSYASI {say['GECE_DOSYASI']} | IZINSIZ_DEGISIM {say['IZINSIZ_DEGISIM']}\n\n"
                     f"Izinsiz fark cikan {len(gm)} kartta yeni uretim kullanilmadi, gece dosyasi aynen alindi (MANIFEST sha = gece). Yeniden uretim "
                     f"farki en buyuk: ort {max([float(d['yeniden_ort'] or 0) for d in gm] or [0])}, max {max([int(d['yeniden_max'] or 0) for d in gm] or [0])}.\n\n"
                     + "".join(f"- {d['cift']} {d['kart']}: {d['tur']}" + (f" (yeniden uretim farki ort {d['yeniden_ort']}, max {d['yeniden_max']})"
                                                                          if d["tur"] == "GECE_DOSYASI" else "") + "\n"
                               for d in degisim if d["tur"] != "AYNI") + ("".join(f"- FAIL: {x}\n" for x in deg_fail)) + "\n")
        if ayni:
            fh.write("## Ayni burc K02 alt basligi (galeri alt metni sira 2)\n\n| cift | metin | genislik / izin px |\n|---|---|---|\n")
            for c in ayni:
                f = d / f"SONUC_{c}.json"
                k2 = (json.loads(f.read_text(encoding="utf-8")).get("k02_ayni_burc") or {}) if f.exists() else {}
                fh.write(f"| {c} | {k2.get('metin', '-')} | {k2.get('genislik_px', '-')} / {k2.get('izin_px', '-')} |\n")
            fh.write("\n")
        if kiy:
            fh.write(f"## CANCER_LIBRA kiyasi (28 Eki onayli ornek; esik ort <= {KIYAS_ORT}, max <= {KIYAS_MAX})\n\n"
                     "| kart | sha esit | ort | max | durum |\n|---|---|---|---|---|\n")
            fh.writelines(f"| {k} | {v.get('sha_esit')} | {v.get('ort')} | {v.get('max')} | {v['durum']} |\n" for k, v in kiy.items())
            fh.write("\n")
        fh.write("## KONTAK\n\n| dosya | galeri | hucre | boyut | eksik |\n|---|---|---|---|---|\n")
        fh.writelines(f"| {k['dosya']} | {k['galeri_no']} | {k['hucre']} | {k['boyut']} | {len(k['eksik'])} |\n" for k in kontak)
    print(f"TOPLA {durum}: cift {len(sira)} PASS {len(pas)} FAIL {len(fail)} {' '.join(fail)} | istisna {len(istisnalar)} | degisim FAIL "
          f"{deg_fail[:5]} | kiyas "
          + " ".join(f"{k}:{v['durum']}(ort {v.get('ort')}, max {v.get('max')}, sha {v.get('sha_esit')})" for k, v in kiy.items()))
    return 0 if durum == "PASS" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    u = alt.add_parser("uret")
    for k in ("--ciftler", "--ko", "--sembol-kok", "--v12", "--out"):
        u.add_argument(k, required=True)
    u.add_argument("--is", dest="is_", required=True)
    u.add_argument("--ciftler-csv", default="data/pod/yd78_ids.csv")
    u.add_argument("--sahne-tut", action="store_true")
    t = alt.add_parser("topla")
    for k in ("--dir", "--secim", "--out"):
        t.add_argument(k, required=True)
    t.add_argument("--ciftler-csv", default="data/pod/yd78_ids.csv")
    t.add_argument("--ref", default="")
    t.add_argument("--kaynak", default="")
    t.add_argument("--onceki", default="", help="gece MANIFEST.csv (sha kaniti)")
    t.add_argument("--onceki-ad", default="")
    t.add_argument("--yeni", default="", help="bu kosuda yeniden uretilmesi istenen ciftler (dosya); her biri icin taze SONUC zorunlu")
    a = ap.parse_args(argv)
    return uret(a) if a.komut == "uret" else topla(a)


if __name__ == "__main__":
    sys.exit(main())
