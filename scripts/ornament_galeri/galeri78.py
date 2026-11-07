#!/usr/bin/env python3
"""Ornament galeri toplu uretimi (Serdar 6 Kas: 3 ek cift ornegi "cok guzel", 78 toplu uretim "basla" + yol "A" = GitHub paralel).
Cift basina 12 dosya: 01 kapak (RUBY, "PERSONALIZED ORNAMENT"), 02-06 bilgi kartlari, 07-11 stil gorselleri ("<STIL> STYLE"), video.
Motorlar onayli yerel ornek motorlarinin aynisi (kapak/kapak_ornek.py + uret3.sh, kart/ornament_kart.py, video/katman.py + video_orn.py).
Etsy / Printful API YOK; yalniz dosya uretir. Hata veren cift FAIL yazilir, digerleri surer; sonda FAIL varsa cikis 1.

Kullanim: galeri78.py --ciftler A_B,C_D,... --kaynak DIR(<CIFT>_<STIL>_954.png) --sembol DIR(<CIFT>/sol.png ...) --is DIR --cikti DIR
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

KOK = Path(__file__).resolve().parent
STILLER = [("RUBY", "07_RUBY", "RUBY STYLE"), ("SAPPHIRE", "08_SAPPHIRE", "SAPPHIRE STYLE"), ("EMERALD", "09_EMERALD", "EMERALD STYLE"),
           ("SADE", "10_WHITE", "WHITE STYLE"), ("FILDISI", "11_IVORY", "IVORY STYLE")]
KARTLAR = [("K02_SEMBOL", "02_SEMBOL"), ("K03_KISISEL", "03_KISISEL"), ("K04_BOYUT", "04_BOYUT"), ("K05_SUREC", "05_SUREC"), ("K06_STIL", "06_STIL")]
BASKI_ADI = {"RUBY": "RUBY", "SAPPHIRE": "SAPPHIRE", "EMERALD": "EMERALD", "SADE": "SADE_ALTIN", "FILDISI": "FILDISI"}
VIDEO_ENV = {"V_SS": "4", "V_YOGX": "6", "V_KAZANC": "8"}                 # onayli v7 (Serdar "cok guzel")


def kos(cmd, env=None, log=None):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(cmd, env=e, capture_output=True, text=True)
    if log is not None:
        log.write(f"$ {' '.join(map(str, cmd))}\n{r.stdout[-4000:]}{r.stderr[-4000:]}\n")
    if r.returncode != 0:
        raise RuntimeError(f"{Path(str(cmd[1] if cmd[0] in ('python3', 'bash') else cmd[0])).name} cikis {r.returncode}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r


def kapak(cift, stil, alt, cikti, baski=None, log=None, bol=None, boy=None):
    a, b = cift.split("_")
    cmd = ["bash", str(KOK / "kapak" / "uret3.sh"), cift, stil, f"{a} & {b}", alt, str(cikti)] + ([str(baski)] if baski else [])
    kos(cmd, env={"V_BOL": "" if bol is None else str(bol), "V_BOY": "" if boy is None else str(boy)}, log=log)
    j = json.load(open(str(cikti) + ".json"))
    if j.get("uyari"):
        raise RuntimeError(f"kapak uyari {stil}: {j['uyari']}")
    # 6 Kas inceleme ORTA: motorun kendi olcumleri (onayli LEO: kapi_a_8bit 1, baslik_4x5 ve disk_4x5 true)
    k_ = dict(kapi_a_8bit=j.get("kapi_a_8bit_max_fark"), baslik_4x5=j.get("baslik_4x5_icinde"), disk_4x5=(j.get("disk") or {}).get("disk_4x5_icinde"))
    if not (isinstance(k_["kapi_a_8bit"], (int, float)) and k_["kapi_a_8bit"] <= 1 and k_["baslik_4x5"] is True and k_["disk_4x5"] is True):
        raise RuntimeError(f"kapak kapisi {stil}: {k_}")
    return j


def kare(mp4, ss=None, son=False):
    cmd = (["ffmpeg", "-loglevel", "error", "-y"] + (["-sseof", "-0.04"] if son else []) + (["-ss", str(ss)] if ss is not None else [])
           + ["-i", str(mp4), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"])
    import io
    r = subprocess.run(cmd, capture_output=True, check=True)
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def video_kontrol(mp4, kapak_jpg):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                                    "stream=width,height,r_frame_rate,nb_read_frames,codec_name", "-show_entries", "format=duration",
                                    "-of", "json", str(mp4)], capture_output=True, text=True, check=True).stdout)
    s = pr["streams"][0]
    k = Image.open(kapak_jpg).convert("RGB")
    fark = []
    for son in (False, True):
        a = np.asarray(kare(mp4, son=son), np.float32)
        b = np.asarray(ImageOps.fit(k, (a.shape[1], a.shape[0])), np.float32)
        fark.append(round(float(np.abs(a - b).mean()), 2))
    # ara kareler (6 Kas inceleme ORTA: ilk / son kare tanim geregi kapak): disk bolgesinde 1,5 sn animasyon var (kapaktan fark >= 4),
    # 4,9 sn sembol tamam (fark <= 3), hicbir ornek kare tek renk degil (std > 40). Esikler onayli 3 cift olcumunden (1,5 sn 7,5-8,7; 4,9 sn 1,98-2,0; std ~70)
    b0 = np.asarray(ImageOps.fit(k, (1440, 1080)), np.float32)
    yy, xx = np.mgrid[:1080, :1440]; dm = np.hypot(xx - 720, yy - 763) < 230
    ara = {}
    for t_ in (0.5, 1.5, 2.5, 3.5, 4.9):
        a_ = np.asarray(kare(mp4, ss=t_), np.float32)
        ara[str(t_)] = dict(disk_fark=round(float(np.abs(a_ - b0)[dm].mean()), 2), std=round(float(a_.std()), 1))
    ara_ok = ara["1.5"]["disk_fark"] >= 4.0 and ara["4.9"]["disk_fark"] <= 3.0 and min(v["std"] for v in ara.values()) > 40
    ok = ((s["width"], s["height"], s["r_frame_rate"], int(s["nb_read_frames"]), s["codec_name"]) == (1440, 1080, "30/1", 180, "h264")
          and max(fark) < 3.0 and ara_ok)
    return dict(ok=ok, genislik=s["width"], yukseklik=s["height"], fps=s["r_frame_rate"], kare=int(s["nb_read_frames"]),
                sure=float(pr["format"]["duration"]), ilk_son_kapak_fark=fark, ara=ara,
                esik="kare 180, 1440x1080, 30/1, h264, ilk/son kare fark < 3, 1,5 sn disk farki >= 4, 4,9 sn <= 3, std > 40")


def katman_kontrol(baski, maske_npz):
    import cv2
    p = np.asarray(Image.open(baski).convert("RGB"))
    h = cv2.cvtColor(p, cv2.COLOR_RGB2HSV)
    g = (h[..., 0] >= 10) & (h[..., 0] <= 36) & (h[..., 1] > 60) & (h[..., 2] > 70)
    m = np.load(maske_npz)
    ata = (m["halka"] | m["sembol"] | m["sol"] | m["sag"]) > 0
    un = g & ~ata; un[640:, :] = False                                       # isim + tarih (y >= 640) katman disi, kapakta kalir
    say = {k: int(m[k].sum()) for k in ("halka", "sembol", "sol", "sag")}
    return dict(ok=int(un.sum()) == 0 and all(v > 0 for v in say.values()), atanmamis_altin_y640_ustu=int(un.sum()), maske_px=say)


REFERANS = {}


def referans_kontrol(cift, O, ref):
    """Onayli yerel ciktilarin sha256'si (GALERI78.json referans_sha; LEO_LEO 12 dosya). Runner ortami yerelden farkliysa (SIMD, x264, font) DUR."""
    if cift not in ref:
        return dict(ok=True, kapsam="referans cifti degil")
    import hashlib
    fark = {f: "eksik" if not (O / f).exists() else "farkli" for f, h in ref[cift].items()
            if not (O / f).exists() or hashlib.sha256((O / f).read_bytes()).hexdigest() != h}
    return dict(ok=not fark, kapsam=f"{len(ref[cift])} dosya onayli sha256", fark=fark)


def sayfa(cift, O, dosyalar, mp4):
    from PIL import ImageDraw
    w, h = 500, 375
    sh = Image.new("RGB", (4 * w + 30, 3 * h + 20), "white"); d = ImageDraw.Draw(sh)
    ims = [Image.open(O / f).convert("RGB") for f in dosyalar] + [kare(mp4, ss=3.0)]
    for i, im in enumerate(ims):
        x, y = (i % 4) * (w + 10), (i // 4) * (h + 10)
        sh.paste(im.resize((w, h), Image.LANCZOS), (x, y)); d.text((x + 8, y + 6), f"{i + 1:02d}", fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    sh.save(O / f"{cift}_SAYFA.jpg", quality=86)


AYNI_BURC_BOL = 1     # 7 Kas: ayni burc ciftlerinde iki bosluk ipe esit uzak (yazi-tura); sabit kural "& sonrasi" ("LEO & | LEO", Serdar'in onayladigi LEO duzeni)
SOL_TOL_PX = 8        # bolme kapisi: ipin solundaki baslik genisligi kapaktan en fazla bu kadar farkli (bolme degisirse ~kelime genisligi kadar fark eder)


def bolme_kapisi(kap):
    """Bagimsiz olcum: her karede baslik puntosu kapakla ayni ve ipin solundaki baslik genisligi (ip_x - baslik_ust_kutu sol kenari, cizilen
    piksellerden) kapaktan en fazla SOL_TOL_PX farkli. Motorun bol_secilen degeri yalniz bilgi (zorlandigi icin kendi kendini dogrular)."""
    k0 = kap.get("01_KAPAK") or {}
    def sol(v):
        u = v.get("baslik_ust_kutu"); x = v.get("ip_x_baslik")
        return None if (not u or x is None) else round(float(x) - float(u[0]), 1)
    s0, b0 = sol(k0), k0.get("baslik_boy")
    sat = {k: dict(boy=v.get("baslik_boy"), sol=sol(v), bol=v.get("bol_secilen")) for k, v in kap.items()}
    hata = [k for k, v in sat.items() if s0 is None or v["sol"] is None or v["boy"] != b0 or abs(v["sol"] - s0) > SOL_TOL_PX]
    return dict(ok=not hata and s0 is not None, hata=hata, kareler=sat, tol_px=SOL_TOL_PX)


def cift_uret(cift, kaynak, sembol, is_kok, cikti_kok, log):
    W = is_kok / cift; O = cikti_kok / cift
    shutil.rmtree(W, ignore_errors=True); shutil.rmtree(O, ignore_errors=True)
    W.mkdir(parents=True); O.mkdir(parents=True)
    os.environ["ORN_KAYNAK"] = str(kaynak)
    for st in BASKI_ADI.values():
        if not (kaynak / f"{cift}_{st}_954.png").exists():
            raise RuntimeError(f"baski yok: {cift}_{st}_954.png")
    for f in ("sol.png", "sag.png", "ana.png"):
        if not (sembol / cift / f).exists():
            raise RuntimeError(f"sembol yok: {cift}/{f}")
    olc = {"cift": cift, "kapak": {}, "zaman_sn": {}}
    t = time.time()
    a_, b_ = cift.split("_")
    j = kapak(cift, "RUBY", "PERSONALIZED ORNAMENT", O / f"{cift}_01_KAPAK.jpg", log=log, bol=AYNI_BURC_BOL if a_ == b_ else None)
    BK = ("baslik_boy", "baslik_kutu", "baslik_ust_kutu", "ip_x_baslik", "uyari", "kapi_a_8bit_max_fark", "baslik_4x5_icinde", "bol_dogal", "bol_secilen")
    olc["kapak"]["01_KAPAK"] = {k: j.get(k) for k in BK + ("disk",)}
    bol = j.get("bol_secilen")                     # 7 Kas Serdar "A": ip bolmesi kapakta secilir, stillere ve video karelerine aynen verilir
    boy = j.get("baslik_boy")                      # punto da aynen (zorlanan bolme sigmazsa motor DUR verir; 7 Kas inceleme: SAG_SAG White 109/111)
    for stil, ad, alt in STILLER:
        y = W / f"{cift}_STIL_{stil}.jpg"
        j = kapak(cift, stil, alt, y, log=log, bol=bol, boy=boy)
        shutil.copy(y, O / f"{cift}_{ad}.jpg")
        olc["kapak"][ad] = {k: j.get(k) for k in BK}
    # kapi: baslik bolmesi ve puntosu her karede ayni (ayni burc ciftlerinde Ivory farkli bolunuyordu; 6 Kas gorsel inceleme)
    olc["zaman_sn"]["kapak_stil"] = round(time.time() - t); t = time.time()
    kos(["python3", str(KOK / "kart" / "ornament_kart.py"), cift],
        env={"ORN_KAPAK_DIR": str(W), "ORN_SEMBOL_DIR": str(sembol), "ORN_OUT": str(W / "kart")}, log=log)
    for k, ad in KARTLAR:
        shutil.copy(W / "kart" / f"ORN_{cift}_{k}.jpg", O / f"{cift}_{ad}.jpg")
    olc["kart"] = json.load(open(W / "kart" / f"RAPOR_{cift}.json"))
    olc["zaman_sn"]["kart"] = round(time.time() - t); t = time.time()
    V = W / "v"; V.mkdir()
    rb = kaynak / f"{cift}_RUBY_954.png"
    kos(["python3", str(KOK / "video" / "katman.py"), str(rb), str(V)], log=log)
    olc["katman"] = katman_kontrol(rb, V / "maske954.npz")
    shutil.copy(O / f"{cift}_01_KAPAK.jpg", V / "KAPAK_tam.jpg"); shutil.copy(str(O / f"{cift}_01_KAPAK.jpg") + ".json", V / "KAPAK_tam.json")
    for k in ("semsiz", "bos"):
        jv = kapak(cift, "RUBY", "PERSONALIZED ORNAMENT", V / f"KAPAK_{k}.jpg", baski=V / f"baski_{k}.png", log=log, bol=bol, boy=boy)
        olc["kapak"][f"video_{k}"] = {k2: jv.get(k2) for k2 in BK}
    olc["bolme"] = bolme_kapisi(olc["kapak"])
    olc["bolme"]["dogal_farkli"] = [k for k, v in olc["kapak"].items() if v.get("bol_dogal") != v.get("bol_secilen")]
    mp4 = O / f"{cift}_VIDEO.mp4"
    r = kos(["python3", str(KOK / "video" / "video_orn.py"), str(V), str(mp4)], env=VIDEO_ENV, log=log)
    try:
        olc["video_motor"] = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        olc["video_motor"] = None
    olc["video"] = video_kontrol(mp4, O / f"{cift}_01_KAPAK.jpg")
    vm = olc["video_motor"] or {}
    if not all(int(vm.get(k_, 0) or 0) > 0 for k_ in ("N", "NH", "NS")):
        olc["video"]["ok"] = False; olc["video"]["motor_hata"] = "N / NH / NS sifir ya da okunamadi"
    olc["zaman_sn"]["video"] = round(time.time() - t)
    # dosya kapisi
    beklenen = [f"{cift}_01_KAPAK.jpg"] + [f"{cift}_{ad}.jpg" for _, ad in KARTLAR] + [f"{cift}_{ad}.jpg" for _, ad, _ in STILLER]
    boyut = {f: Image.open(O / f).size for f in beklenen}
    olc["dosya"] = dict(ok=all(v == (3000, 2250) for v in boyut.values()) and mp4.exists(), adet=len(beklenen) + 1,
                        hatali_boyut={f: v for f, v in boyut.items() if v != (3000, 2250)})
    sayfa(cift, O, beklenen, mp4)                                          # inceleme icin tek sayfa (11 gorsel + video 3. sn karesi)
    for f in O.glob("*.jpg.json"):                                        # olcum OLCUM.json'da; jpg yanindaki ham json Drive'a gitmez
        f.unlink()
    olc["referans"] = referans_kontrol(cift, O, REFERANS)
    olc["sonuc"] = "PASS" if (olc["katman"]["ok"] and olc["video"]["ok"] and olc["dosya"]["ok"] and olc["referans"]["ok"]
                              and olc["bolme"]["ok"]) else "FAIL"
    json.dump(olc, open(O / f"{cift}_OLCUM.json", "w"), ensure_ascii=False, indent=1)
    shutil.rmtree(W, ignore_errors=True)
    return olc["sonuc"], olc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ciftler", required=True); ap.add_argument("--kaynak", required=True); ap.add_argument("--sembol", required=True)
    ap.add_argument("--is", dest="is_", required=True); ap.add_argument("--cikti", required=True); ap.add_argument("--etiket", default="")
    ap.add_argument("--referans", default="", help="GALERI78.json (referans_sha alani)")
    ap.add_argument("--kontrol", default="", help="parca basinda once uretilen kontrol cifti (referans_sha'da olmali); FAIL = parca DUR")
    a = ap.parse_args()
    if a.referans:
        REFERANS.update(json.load(open(a.referans)).get("referans_sha", {}))
    ciftler = [c for c in a.ciftler.split(",") if c]
    kaynak, sembol, is_kok, cikti = (Path(p).resolve() for p in (a.kaynak, a.sembol, a.is_, a.cikti))
    cikti.mkdir(parents=True, exist_ok=True); is_kok.mkdir(parents=True, exist_ok=True)
    log = open(cikti / f"LOG{a.etiket}.txt", "a")
    sonuc = {}; t0 = time.time()
    if a.kontrol:                                  # etsy-yayin-hatti 4: her parcada kontrol cifti; kontrol FAIL = parca DUR (ortam farki)
        if a.kontrol not in REFERANS:
            raise SystemExit(f"DUR: kontrol cifti {a.kontrol} referans_sha'da yok")
        kd = is_kok / "_kontrol_cikti"
        try:
            ks, ko = cift_uret(a.kontrol, kaynak, sembol, is_kok, kd, log)
        except Exception as e:
            ks, ko = "FAIL", {"neden": str(e)[-500:]}
        json.dump({"kontrol": a.kontrol, "sonuc": ks, "referans": ko.get("referans"), "neden": ko.get("neden", "")},
                  open(cikti / f"KONTROL{a.etiket}.json", "w"), ensure_ascii=False, indent=1)
        print(f"KONTROL {a.kontrol} {ks} {round(time.time() - t0)} sn | referans {ko.get('referans')}", flush=True)
        shutil.rmtree(kd, ignore_errors=True)
        if ks != "PASS":
            print("DUR: kontrol cifti FAIL, parca uretim yapmadi", flush=True); sys.exit(2)
    for i, c in enumerate(ciftler, 1):
        t = time.time()
        try:
            s, o = cift_uret(c, kaynak, sembol, is_kok, cikti, log)
            sonuc[c] = {"sonuc": s, "sn": round(time.time() - t), "neden": "" if s == "PASS" else "olcum kapisi (OLCUM.json)"}
        except Exception as e:
            sonuc[c] = {"sonuc": "FAIL", "sn": round(time.time() - t), "neden": str(e)[-500:]}
        log.flush()
        json.dump(sonuc, open(cikti / f"SONUC{a.etiket}.json", "w"), ensure_ascii=False, indent=1)   # her ciftten sonra (cokmede kayip olmasin)
        gecen = time.time() - t0; kalan = gecen / i * (len(ciftler) - i)
        print(f"[{i}/{len(ciftler)}] {c} {sonuc[c]['sonuc']} {sonuc[c]['sn']} sn | gecen {gecen/60:.1f} dk | kalan ~{kalan/60:.1f} dk | %{100*i/len(ciftler):.0f}"
              + (f" | {sonuc[c]['neden']}" if sonuc[c]["sonuc"] != "PASS" else ""), flush=True)
    json.dump(sonuc, open(cikti / f"SONUC{a.etiket}.json", "w"), ensure_ascii=False, indent=1)
    n = sum(v["sonuc"] == "PASS" for v in sonuc.values())
    print(f"TOPLAM PASS={n} FAIL={len(sonuc) - n}")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
