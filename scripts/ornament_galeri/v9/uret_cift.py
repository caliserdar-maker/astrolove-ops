#!/usr/bin/env python3
"""Ornament galeri v9 (Serdar 7-8 Kas): cift basina 14 gorsel + video. Onayli CANCER_LIBRA setinin (GALERI_FINAL + 5 stil) kodu.

Sahneler (AI, baskisiz disk; fal nano-banana-2/edit, Kling arka plan) SAHNE klasorunden; urun baskisi kodla birebir (ANA_1 2.1).
Baskilar: BASKI/<CIFT>_<RUBY|SAPPHIRE|EMERALD|SADE_ALTIN|FILDISI>_954.png (Drive TEMP/ORNAMENT_78_TOPLAMA_...).
Cikti: CIKTI/<CIFT>/<CIFT>_01_KAPAK.jpg ... _14_IVORY.jpg (+ _15_SEMBOL_KARTI.jpg, --maske ile), <CIFT>_VIDEO.mp4, <CIFT>_OLCUM.json (kapi sonucu).
Sira (Serdar 7 Kas galeri + 8 Kas stil gorselleri): 01 kapak, 02 agac, 03 eller, 04 stiller (K06), 05 K03, 06 K02, 07 K04, 08 K05,
09 yil boyu, 10-14 stil (Ruby, Sapphire, Emerald, White, Ivory; kapak sahnesi + "<STIL> STYLE").
kullanim: python uret_cift.py --ciftler CANCER_LIBRA,LEO_LEO --sahne DIR --baski DIR --is DIR --cikti DIR [--ref REF.json]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

KOD = Path(__file__).resolve().parent
OLC = KOD / "olc"
PY = sys.executable
PY_YAZI = os.environ.get("PY_YAZI", sys.executable)   # onayli set: yazi adimlari ve K06 zinciri Pillow 11.0.0 / numpy 2.1.3 ortaminda uretildi (8 Kas olcum)
STIL = [("RUBY", "RUBY", None), ("SAPPHIRE", "SAPPHIRE", "kapak_SAPPHIRE"), ("EMERALD", "EMERALD", "kapak_EMERALD"),
        ("WHITE", "SADE_ALTIN", "kapak_WHITE"), ("IVORY", "FILDISI", "kapak_IVORY")]
SAHNE_TEK = [("02_AGAC", "agac3"), ("03_ELLER", "eller3"), ("09_YILBOYU", "yilboyu")]
KARTLAR = [("05_KISISEL", "kart_kisisel3", "K03", {}), ("06_SEMBOL", "kart_sembol", "K02", {}),
           ("07_BOYUT", "kart_boyut", "K04", {}), ("08_SUREC", "kart_surec5", "K05", {"NESNE": "renk"})]
DOSYALAR = ["01_KAPAK", "02_AGAC", "03_ELLER", "04_STILLER", "05_KISISEL", "06_SEMBOL", "07_BOYUT", "08_SUREC", "09_YILBOYU",
            "10_RUBY", "11_SAPPHIRE", "12_EMERALD", "13_WHITE", "14_IVORY"]


KART = {}          # --maske verilirse 15. gorsel (sembol karti)


def ad(burc):
    return burc.capitalize()


def kos(arg, cwd, env=None, log=None, py=None):
    e = dict(os.environ, **(env or {}))
    p = subprocess.run([py or PY, *arg], cwd=cwd, env=e, capture_output=True, text=True)
    if log is not None:
        log.write(f"$ {' '.join(map(str, arg))} {env or ''}\n{p.stdout[-3000:]}{p.stderr[-3000:]}\n")
    if p.returncode != 0:
        raise RuntimeError(f"{arg[0]} cikis {p.returncode}: {p.stderr[-800:]}")
    return p.stdout


def son_json(cikti):
    return [l for l in cikti.strip().splitlines() if l.startswith("{")][-1]


def set_json(yol):
    return json.load(open(yol))


def olc_tasi(i):
    """stil_zincir.sh: d1-d4 olcumu onceki 3000x2250 cikisa ayni donusumle tasinir (k=W'/W, PAD)"""
    o = json.load(open(OLC / f"kart_stil.d{i}.olc.json")); k = 3000 / o["W"]; p = (2250 - round(o["H"] * k)) // 2
    o.update(W=3000, H=2250, cx=o["cx"] * k, cy=o["cy"] * k + p, A=o["A"] * k, B=o["B"] * k,
             delik=[o["delik"][0] * k, o["delik"][1] * k + p, o["delik"][2] * k])
    return o


def cift_uret(cift, sahne, baski, isk, cikti, log):
    a, b = cift.split("_")
    A, B = ad(a), ad(b)
    w = Path(isk) / cift; w.mkdir(parents=True, exist_ok=True)
    o = Path(cikti) / cift; o.mkdir(parents=True, exist_ok=True)
    bp = {s: str(Path(baski) / f"{cift}_{d}_954.png") for s, d, _ in STIL}
    eksik = [p for p in bp.values() if not Path(p).exists()]
    if eksik:
        raise RuntimeError(f"baski eksik {eksik}")
    olcum = dict(cift=cift, A=A, B=B, set={}, yazi={})
    S = lambda n: str(Path(sahne) / f"{n}.png")
    # 01 kapak + 10 Ruby (ayni SET, farkli alt satir) + video katmani
    j = son_json(kos([KOD / "set_yerlestir.py", "kapak", S("kapak"), OLC / "kapak.olc.json"], w, {"BASKI": bp["RUBY"]}, log))
    olcum["set"]["kapak"] = set_json(w / "SET_kapak.json")
    baslik = f"{A} & {B}"
    t = kos([KOD / "kapak_yazi.py", "SET_kapak.jpg", "SET_kapak.json", "K01.jpg"], w, {"BASLIK": baslik, "KATMAN": str(w / "katman.npz")}, log, PY_YAZI)
    olcum["yazi"]["01_KAPAK"] = son_json(t)
    t = kos([KOD / "kapak_yazi.py", "SET_kapak.jpg", "SET_kapak.json", "K10.jpg"], w, {"BASLIK": baslik, "ALT": "RUBY STYLE"}, log, PY_YAZI)
    olcum["yazi"]["10_RUBY"] = son_json(t)
    shutil.copy(w / "K01.jpg", o / f"{cift}_01_KAPAK.jpg"); shutil.copy(w / "K10.jpg", o / f"{cift}_10_RUBY.jpg")
    # 11-14 stil (kapak sahnesi, stilin duz diski)
    for no, (s, _, sh) in zip((11, 12, 13, 14), STIL[1:]):
        kos([KOD / "set_yerlestir.py", f"st_{s}", S(sh), OLC / f"{sh}.olc.json"], w, {"BASKI": bp[s]}, log)
        olcum["set"][f"st_{s}"] = set_json(w / f"SET_st_{s}.json")
        t = kos([KOD / "kapak_yazi.py", f"SET_st_{s}.jpg", f"SET_st_{s}.json", f"K{no}.jpg"], w, {"BASLIK": baslik, "ALT": f"{s} STYLE"}, log, PY_YAZI)
        olcum["yazi"][f"{no}_{s}"] = son_json(t)
        shutil.copy(w / f"K{no}.jpg", o / f"{cift}_{no}_{s}.jpg")
    # 02, 03, 09 yasam sahneleri (Ruby)
    for dad, sh in SAHNE_TEK:
        kos([KOD / "set_yerlestir.py", sh, S(sh), OLC / f"{sh}.olc.json"], w, {"BASKI": bp["RUBY"]}, log)
        olcum["set"][sh] = set_json(w / f"SET_{sh}.json")
        shutil.copy(w / f"SET_{sh}.jpg", o / f"{cift}_{dad}.jpg")
    # 05-08 kartlar (Ruby baski + kodla yazi)
    for dad, sh, kart, ek in KARTLAR:
        kos([KOD / "set_yerlestir.py", sh, S(sh), OLC / f"{sh}.olc.json"], w, {"BASKI": bp["RUBY"]}, log)
        olcum["set"][sh] = set_json(w / f"SET_{sh}.json")
        t = kos([KOD / "kart_yazi.py", f"SET_{sh}.jpg", f"{dad}.jpg", kart], w, {"A": A, "B": B, **ek}, log, PY_YAZI)
        olcum["yazi"][dad] = t.strip().splitlines()[-1]
        shutil.copy(w / f"{dad}.jpg", o / f"{cift}_{dad}.jpg")
    # 04 stiller (K06): 5 diske sirayla kendi stil baskisi (stil_zincir.sh)
    gir = S("kart_stil")
    for i, (s, _, _) in enumerate(STIL):
        if i == 0:
            ol = OLC / "kart_stil.d0.olc.json"
        else:
            ol = w / f"stil_d{i}.json"; json.dump(olc_tasi(i), open(ol, "w"))
        kos([KOD / "set_yerlestir.py", f"kart_stil_d{i}", gir, ol], w, {"BASKI": bp[s], "CIKIS_PNG": str(w / f"stil_ara{i}.png")}, log, PY_YAZI)
        olcum["set"][f"kart_stil_d{i}"] = set_json(w / f"SET_kart_stil_d{i}.json")
        gir = str(w / f"stil_ara{i}.png")
    t = kos([KOD / "stil_yazi.py", gir, "04_STILLER.jpg"], w, None, log, PY_YAZI)
    olcum["yazi"]["04_STILLER"] = t.strip().splitlines()[-1]
    shutil.copy(w / "04_STILLER.jpg", o / f"{cift}_04_STILLER.jpg")
    # video (Kling arka plan + kodla toz olusumu; ilk ve son kare 01 kapak)
    t = kos([KOD / "kapak_video.py", str(Path(sahne) / "kling.mp4"), str(o / f"{cift}_VIDEO.mp4")], w,
            {"V_SET": str(w / "SET_kapak.jpg"), "V_OLC": str(OLC / "kapak.olc.json"), "V_JSON": str(w / "SET_kapak.json"),
             "V_KATMAN": str(w / "katman.npz"), "V_SON": str(w / "K01.jpg")}, log)
    olcum["video"] = t.strip().splitlines()[-1]
    # 15 sembol karti (Serdar 8 Kas: yayindaki "Two Signs, One Shared Symbol" karti, yeni set zemini, hazir altin dosyalar aynen)
    if KART.get("maske"):
        t = kos([KOD / "sembol_karti.py", cift, KART["zemin"], KART["maske"], KART["altin"], str(o / f"{cift}_15_SEMBOL_KARTI.jpg")], w,
                {"KART_DIR": KART["kart_dir"]}, log, PY_YAZI)
        olcum["yazi"]["15_SEMBOL_KARTI"] = t.strip().splitlines()[-1]
    return olcum


def kapi(cift, olcum, cikti, ref):
    """Otomatik kapi: dosya sayisi/boyutu, video, sahne olcumleri referansla (CANCER_LIBRA onayli), yazi bant icinde."""
    from PIL import Image
    h = []
    o = Path(cikti) / cift
    for d in DOSYALAR + (["15_SEMBOL_KARTI"] if KART.get("maske") else []):
        p = o / f"{cift}_{d}.jpg"
        if not p.exists():
            h.append(f"yok {d}"); continue
        im = Image.open(p)
        if im.size != (3000, 2250) or im.format != "JPEG":
            h.append(f"boyut {d} {im.size}")
    v = o / f"{cift}_VIDEO.mp4"
    if not v.exists():
        h.append("video yok")
    else:
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                             "stream=width,height,nb_read_frames", "-of", "json", str(v)], capture_output=True, text=True)
        st = json.loads(pr.stdout or "{}").get("streams", [{}])[0]
        if (st.get("width"), st.get("height"), str(st.get("nb_read_frames"))) != (1440, 1080, "270"):
            h.append(f"video {st}")
    for k, s in olcum["set"].items():
        r = (ref or {}).get(k)
        if not r:
            continue
        # sahneye bagli olcumler cift degisse de AYNI olmali (delik, R, ip kayma); ip ve isik baskiyla az degisir
        for a in ("R", "delik_bizim", "delik_ai", "ip_kayma", "delik_olcek"):
            x, y = s.get(a), r.get(a)
            x, y = (x if isinstance(x, list) else [x]), (y if isinstance(y, list) else [y])
            if len(x) != len(y) or any(abs(float(p) - float(q)) > 0.6 for p, q in zip(x, y)):
                h.append(f"{k} {a} {s.get(a)} != ref {r.get(a)}")
        if not (0.75 * r["ip_px"] <= s["ip_px"] <= 1.25 * r["ip_px"]):
            h.append(f"{k} ip_px {s['ip_px']} (ref {r['ip_px']})")
        if s["Sm_min"] < r["Sm_min"] - 0.08:
            h.append(f"{k} Sm_min {s['Sm_min']} (ref {r['Sm_min']})")
    for k, y in olcum["yazi"].items():
        if k[:2] in ("01", "10", "11", "12", "13", "14"):
            kutu = eval(y, {"np": __import__("numpy")}).get("kutu")     # kapak_yazi.py kendi ciktisi (dict repr)
            if kutu[0] < 800 or kutu[2] > 2200:
                h.append(f"{k} yazi bant disi {kutu}")
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ciftler", required=True)
    ap.add_argument("--sahne", required=True)
    ap.add_argument("--baski", required=True)
    ap.add_argument("--is", dest="isk", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ref", default=str(KOD / "REF_CANCER_LIBRA.json"))
    ap.add_argument("--etiket", default="")
    ap.add_argument("--maske", default="", help="sembol karti: kupa_uretim/sembol (cift alt klasorleri)")
    ap.add_argument("--altin", default="", help="sembol karti: <burc>_symbol_gold.png + <CIFT>_ana.png")
    ap.add_argument("--zemin", default="", help="sembol karti zemini (GALERI9.json sahneler sembol_zemin.png)")
    ap.add_argument("--kart-dir", default=str(KOD.parent / "kart"))
    a = ap.parse_args()
    if a.maske:
        KART.update(maske=a.maske, altin=a.altin, zemin=a.zemin, kart_dir=a.kart_dir)
    ref = json.load(open(a.ref))["set"] if Path(a.ref).exists() else None
    L = [c for c in a.ciftler.split(",") if c]
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    log = open(Path(a.cikti) / f"LOG{a.etiket}.txt", "w")
    sonuc = {}
    t0 = time.time()
    for n, c in enumerate(L, 1):
        try:
            olc = cift_uret(c, a.sahne, a.baski, a.isk, a.cikti, log)
            h = kapi(c, olc, a.cikti, ref)
            olc["kapi"] = h; olc["sonuc"] = "PASS" if not h else "FAIL"
            json.dump(olc, open(Path(a.cikti) / c / f"{c}_OLCUM.json", "w"), indent=1, default=str)
            sonuc[c] = dict(sonuc=olc["sonuc"], neden=h[:10])
        except Exception as e:  # noqa: BLE001
            sonuc[c] = dict(sonuc="FAIL", neden=[f"hata {e}"[:600]])
        shutil.rmtree(Path(a.isk) / c, ignore_errors=True)
        g = time.time() - t0
        print(f"[{n}/{len(L)}] {c} {sonuc[c]['sonuc']} | gecen {g/60:.1f} dk | kalan ~{g/n*(len(L)-n)/60:.1f} dk | %{100*n//len(L)}", flush=True)
        log.flush()
    json.dump(sonuc, open(Path(a.cikti) / f"SONUC{a.etiket}.json", "w"), indent=1)
    sys.exit(0 if all(v["sonuc"] == "PASS" for v in sonuc.values()) else 1)


if __name__ == "__main__":
    main()
