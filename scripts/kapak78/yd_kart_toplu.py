#!/usr/bin/env python3
"""YD 10'lu galeri: kodla uretilen kartlarin 78 cift TOPLU uretimi (Serdar onayi 27 Eki, ornek 20261027_134934 "Cok guzel"; Merkez).
ETSY API YOK, Canva yok, Etsy'ye yukleme yok. Kart cizimi ve kart kapilari scripts/kapak78/yd_kart_ornek.py (onayli kod, ayni kapilar:
renk, punto, metin / Title Case, yasak karakter / sozcuk) cift basina aynen kosulur.
Girdi: adim 5 yedegi (--yedek: <ilan>_<CIFT>/GALERI.json + r<rank>_<id>.jpg), data/pod/yd78_ids.csv.
  cift basina: r2 = eski sembol karti (rank 2), Botanical ve Timeless = GALERI.json Style (513) baglarinin gorseli.
Ek kapilar (cift basina; biri tutmazsa o cift FAIL, dosyalari yazilmaz):
  R2_KAPI   : eski r2'nin baslik bandi ("Your two signs, one shared symbol.", 78 ciftte ayni metin) referans ciftin (CANCER_LIBRA)
              bandiyla NCC >= R2_ESIK (yanlis rank 2 karti / baska kart secilmesin).
  POSTER_NCC: Y03 / Y05 poster bolgesi (teslim JPEG) o ciftin kendi Botanical / Timeless kirpimiyla NCC >= POSTER_ESIK ve 78 ciftin
              kaynaklari icinde en yakin kendi cifti (1/8 olcek).
              Ayrica Y03 kendi Botanical'ina, Y05 kendi Timeless'ina digerinden en az 0.05 daha yakin (stil karismasi).
  sha256 tekil (tasima kurali: iki adda ayni sha FAIL). ORTAK_Y04 referans cift (CANCER_LIBRA) kosusunda uretilir.
Cikti (--out, Drive TEMP/YD_KAPAK_V1/<damga>/ olarak yazilir): <CIFT>_Y02.jpg, <CIFT>_Y03.jpg, <CIFT>_Y05.jpg (78 x 3) + ORTAK_Y04.jpg,
  MANIFEST.csv (galeri_tasi.py ALAN bicimi: ad, cift, kart_no, design_id = KOD_<commit>, boyut, sha256, durum YENI; sonraki Canva
  tasimasi ayni damgaya eklenince bu dosyalar MEVCUT olur, design_id korunur), KART_TOPLU.json, OZET.md, KONTAK_78.jpg
  (78 cift x Y02 / Y03 / Y05 kucuk, < 300 KB).
Kullanim: yd_kart_toplu.py --yedek DIR --ciftler data/pod/yd78_ids.csv --out DIR --kod-ref <commit> [--sadece CIFT,CIFT]"""
import argparse
import contextlib
import csv
import hashlib
import io
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

ALAN = ["ad", "cift", "kart_no", "design_id", "boyut", "sha256", "durum"]      # galeri_tasi.py MANIFEST
REF_CIFT = "CANCER_LIBRA"
R2_BANT = (0.10, 0.05, 0.90, 0.20)        # eski r2 baslik bandi (genislik / yukseklik orani)
R2_ESIK = 0.90
POSTER_ESIK = 0.95
KONTAK_KB = 300


def gri(im, olcek=1):
    g = im.convert("L")
    if olcek != 1:
        g = g.resize((max(1, round(g.width / olcek)), max(1, round(g.height / olcek))), Image.BILINEAR)
    return np.asarray(g, dtype=np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d else 0.0


B2, B8 = (450, 562), (112, 140)           # poster karsilastirma boyutlari (1/2 ve 1/8; poster kutusu 900x1125)


def kucult(im):
    g = im.convert("L")
    return np.asarray(g.resize(B2, Image.LANCZOS), np.float32), np.asarray(g.resize(B8, Image.BILINEAR), np.float32)


def bant(im):
    w, h = im.size
    return gri(im.crop((round(R2_BANT[0] * w), round(R2_BANT[1] * h), round(R2_BANT[2] * w), round(R2_BANT[3] * h))), 4)


def girdiler(d):
    """<ilan>_<CIFT> klasoru -> (r2, botanical, timeless) yollari"""
    g = json.loads((d / "GALERI.json").read_text(encoding="utf-8"))
    rk = {x["listing_image_id"]: x["rank"] for x in g["gorseller"]}
    r2 = [x for x in g["gorseller"] if x["rank"] == 2]
    if len(r2) != 1:
        raise SystemExit("rank 2 gorseli yok / birden fazla")
    bag = {b["value"]: b["image_id"] for b in g["baglar"] if b.get("property_id") == 513}
    if "Botanical" not in bag or "Timeless" not in bag:
        raise SystemExit("Botanical / Timeless bagi yok")
    yol = lambda iid: d / f"r{rk[iid]}_{iid}.jpg"   # noqa: E731
    p = (d / f"r2_{r2[0]['listing_image_id']}.jpg", yol(bag["Botanical"]), yol(bag["Timeless"]))
    eksik = [x.name for x in p if not x.exists()]
    if eksik:
        raise SystemExit(f"yedekte dosya yok: {eksik}")
    return p


def kontak(satirlar, hedef):
    """KONTAK_78.jpg: 6 cift / satir, cift basina Y02 / Y03 / Y05 (144x108), ad + durum; < 300 KB"""
    tw, th, et = 144, 108, 18
    blok = 3 * tw + 12
    sut = 6; sat = (len(satirlar) + sut - 1) // sut
    T = Image.new("RGB", (sut * blok + 12, sat * (th + et + 8) + 8), "white"); d = ImageDraw.Draw(T)
    try:
        f = ImageFont.load_default(size=12)
    except TypeError:
        f = ImageFont.load_default()
    for i, s in enumerate(satirlar):
        r, c = divmod(i, sut); x0, y0 = 12 + c * blok, 8 + r * (th + et + 8)
        d.text((x0, y0), f"{s['cift']} {s['durum']}", fill=(0, 0, 0) if s["durum"] == "PASS" else (180, 0, 0), font=f)
        for j, p in enumerate(s.get("kucuk", [])):
            T.paste(p, (x0 + j * tw, y0 + et))
    for q in (70, 60, 50, 40, 32):
        b = io.BytesIO(); T.save(b, "JPEG", quality=q)
        if b.tell() < KONTAK_KB * 1024:
            hedef.write_bytes(b.getvalue()); return dict(boyut=list(T.size), kalite=q, kb=round(b.tell() / 1024, 1))
    raise SystemExit(f"DUR: KONTAK_78.jpg {b.tell() / 1024:.0f} KB (>= {KONTAK_KB})")


def cift_uret(is_):
    """tek cift (ayri islem): girdiler, R2_KAPI, kart betigi (ayni kapilar), POSTER_NCC kendi kaynagi. -> durum sozlugu"""
    r, d, hd, ortak, ref_bant = is_
    c = r["cift"]; s = dict(cift=c, listing_id=r["listing_id"], durum="FAIL", neden=[], dosyalar=[])
    try:
        r2, pb, pt = girdiler(d)
        nb = ncc(bant(Image.open(r2)), ref_bant); s["r2_bant_ncc"] = round(nb, 4)
        if nb < R2_ESIK:
            raise SystemExit(f"R2_KAPI: eski r2 baslik bandi NCC {nb:.3f} < {R2_ESIK} (sembol karti degil?)")
        arg = ["--cift", c, "--a", r["a"], "--b", r["b"], "--eski-r2", str(r2), "--botanical", str(pb), "--timeless", str(pt), "--out", str(hd)]
        with contextlib.redirect_stdout(io.StringIO()):
            K.main(arg + (["--ortak"] if ortak else []))
        oz = json.loads((hd / "KART_OZET.json").read_text(encoding="utf-8"))
        kk = {3: kucult(K.poster_kirp(Image.open(pb))[0])[0], 5: kucult(K.poster_kirp(Image.open(pt))[0])[0]}
        for k in (3, 5):                                   # POSTER_NCC: teslim JPEG poster bolgesi vs kendi kaynak kirpimi
            ad = f"{c}_Y{k:02d}.jpg"; pk = oz["olcu"][ad]["poster_kutu"][0]
            b2, b8 = kucult(Image.open(hd / ad).crop(pk))
            kendi, diger = ncc(b2, kk[k]), ncc(b2, kk[8 - k])   # stil karismasi: Y03 Botanical'a, Y05 Timeless'a daha yakin
            s[f"y{k:02d}_poster_ncc"] = round(kendi, 4); s[f"y{k:02d}_diger_stil_ncc"] = round(diger, 4); s[f"_b8_{k}"] = b8
            if kendi < POSTER_ESIK:
                raise SystemExit(f"POSTER_NCC: {ad} {kendi:.3f} < {POSTER_ESIK}")
            if diger > kendi - 0.05:
                raise SystemExit(f"POSTER_NCC: {ad} diger stile ({'Timeless' if k == 3 else 'Botanical'}) {diger:.3f} yakin (stil karismasi)")
        s["dosyalar"] = list(oz["dosyalar"]); s["durum"] = "PASS"
    except SystemExit as e:
        s["neden"].append(str(e)[:300])
    except Exception as e:  # noqa: BLE001
        s["neden"].append(f"{type(e).__name__}: {e}"[:300])
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yedek", required=True); ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--kod-ref", required=True, help="kodun commit'i (MANIFEST design_id = KOD_<ilk 8>)")
    ap.add_argument("--sadece", default="", help="yerel test: virgullu cift listesi")
    ap.add_argument("--is-sayisi", type=int, default=4, help="paralel islem (runner 4 cekirdek)")
    a = ap.parse_args(argv)
    yedek, out = Path(a.yedek), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_cift"; shutil.rmtree(tmp, ignore_errors=True)
    rows = list(csv.DictReader(open(a.ciftler, encoding="utf-8-sig")))
    if a.sadece:
        sa = set(a.sadece.split(",")); rows = [r for r in rows if r["cift"] in sa]
    klasor = {r["cift"]: yedek / f"{r['listing_id']}_{r['cift']}" for r in rows}
    ref_d = next(iter(sorted(yedek.glob(f"*_{REF_CIFT}"))), None)
    if not ref_d:
        raise SystemExit(f"DUR: referans cift {REF_CIFT} yedekte yok")
    ref_bant = bant(Image.open(girdiler(ref_d)[0]))
    kod = f"KOD_{a.kod_ref[:8]}"
    sonuc, t0, man, kaynak8 = [], time.time(), [], {}
    # 1/8 kaynak kirpimlari (en yakin kapisi icin): cift -> {kart: dizi}
    for r in rows:
        try:
            _, pb, pt = girdiler(klasor[r["cift"]])
            kaynak8[r["cift"]] = {3: kucult(K.poster_kirp(Image.open(pb))[0]), 5: kucult(K.poster_kirp(Image.open(pt))[0])}
        except SystemExit:
            pass
    if REF_CIFT not in klasor:
        raise SystemExit(f"DUR: ORTAK_Y04 referans ciftle ({REF_CIFT}) uretilir; listede yok")
    isler = [(r, klasor[r["cift"]], tmp / r["cift"], r["cift"] == REF_CIFT, ref_bant) for r in rows]   # ORTAK_Y04 referans ciftte
    with ProcessPoolExecutor(max_workers=a.is_sayisi) as ex:
        for n, s in enumerate(ex.map(cift_uret, isler), 1):
            c = s["cift"]
            if s["durum"] == "PASS":                           # POSTER_NCC en yakin: 78 ciftin kaynaklari icinde kendi cifti
                for k in (3, 5):
                    b8 = s.pop(f"_b8_{k}")
                    skor = {cc: ncc(b8, v[k][1]) for cc, v in kaynak8.items()}
                    yakin = max(skor, key=skor.get); s[f"y{k:02d}_en_yakin"] = yakin
                    if yakin != c:
                        s["durum"] = "FAIL"; s["neden"].append(f"POSTER_NCC: Y{k:02d} poster bolgesi en cok {yakin} kaynagina benziyor")
            else:
                s.pop("_b8_3", None); s.pop("_b8_5", None)
            if s["durum"] == "PASS":
                for ad in s["dosyalar"]:
                    shutil.copyfile(tmp / c / ad, out / ad)
                s["kucuk"] = [Image.open(out / f"{c}_Y{k:02d}.jpg").resize((144, 108), Image.LANCZOS) for k in (2, 3, 5)]
            sonuc.append(s)
            gecen = time.time() - t0; kalan = gecen / n * (len(rows) - n)
            print(f"[{n}/{len(rows)}] %{100 * n // len(rows)} gecen {gecen:.0f} sn kalan ~{kalan:.0f} sn | {c} {s['durum']}"
                  + (f" | {s['neden'][0]}" if s["neden"] else ""), flush=True)
    ortak_yaz = not (out / "ORTAK_Y04.jpg").exists()
    shutil.rmtree(tmp, ignore_errors=True)
    if ortak_yaz:
        print("::error::ORTAK_Y04 uretilemedi (hic PASS cift yok)")
    sha_ad = {}
    for p in sorted(out.glob("*.jpg")):
        sha_ad.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), []).append(p.name)
    cift_sha = [v for v in sha_ad.values() if len(v) > 1]
    for p in sorted(out.glob("*_Y0[2-5].jpg")):
        h = hashlib.sha256(p.read_bytes()).hexdigest(); bt = Image.open(p).size
        c = "ORTAK" if p.name.startswith("ORTAK_") else p.name[:-8]
        man.append(dict(ad=p.name, cift=c, kart_no=str(int(p.name[-6:-4])), design_id=kod, boyut=f"{bt[0]}x{bt[1]}", sha256=h,
                        durum="YENI" if len(sha_ad[h]) == 1 else f"FAIL sha256 {len(sha_ad[h])} adda ayni"))
    with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALAN, lineterminator="\n"); w.writeheader(); w.writerows(man)
    ko = kontak(sonuc, out / "KONTAK_78.jpg")
    for s in sonuc:
        s.pop("kucuk", None)
    pas = [s for s in sonuc if s["durum"] == "PASS"]; fail = [s for s in sonuc if s["durum"] != "PASS"]
    beklenen_dosya = 3 * len(rows) + 1
    (out / "KART_TOPLU.json").write_text(json.dumps(dict(kod_ref=a.kod_ref, design_id=kod, pillow=K.SURUM, esik=dict(r2=R2_ESIK, poster=POSTER_ESIK),
                                                         pass_=len(pas), fail=len(fail), dosya=len(man), beklenen_dosya=beklenen_dosya,
                                                         ayni_sha=cift_sha, kontak=ko, ciftler=sonuc), indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "OZET.md", "w", encoding="utf-8") as fh:
        fh.write(f"# YD kod kartlari toplu (Y02 / Y03 / Y05 + ORTAK_Y04)\n\nPASS {len(pas)} / {len(rows)} | dosya {len(man)} / {beklenen_dosya} | "
                 f"ayni sha {len(cift_sha)} | kod {kod}\n\n")
        fh.write("## FAIL\n" + ("".join(f"- {s['cift']}: {'; '.join(s['neden'])}\n" for s in fail) or "- yok\n"))
        fh.write("\n| cift | durum | r2 bant | Y03 poster | Y05 poster |\n|---|---|---|---|---|\n"
                 + "".join(f"| {s['cift']} | {s['durum']} | {s.get('r2_bant_ncc', '-')} | {s.get('y03_poster_ncc', '-')} | "
                           f"{s.get('y05_poster_ncc', '-')} |\n" for s in sonuc))
    print(f"OZET: PASS {len(pas)}/{len(rows)} | dosya {len(man)}/{beklenen_dosya} | ayni sha {len(cift_sha)} | kontak {ko}")
    return 0 if not fail and not cift_sha and len(man) == beklenen_dosya else 1


if __name__ == "__main__":
    sys.exit(main())
