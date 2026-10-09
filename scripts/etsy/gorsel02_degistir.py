#!/usr/bin/env python3
"""Ilan gorseli 02 (Choose your format) yeni Digital File metni (Serdar 9 Eki onayi). ETSY'YE YAZAR.

Mod ciftler (77 ilan): ilan basina YALNIZ 2. gorsel degisir.
  yedek (manifest + tum canli gorseller, Drive'a kopya + rclone check) -> on kosul (active, 17 gorsel, 2. gorsel renk bagli degil)
  -> uploadListingImage(rank = 2. gorselin rank'i, overwrite=true, ayni alt metin)
  -> geri okuma: 17 gorsel, 2. gorsel YENI id ve yeni kartla NCC >= 0.995, diger 16 gorsel id + sira ayni, alt metinler ayni,
     renk baglari ayni, state/baslik/etiket/aciklama/envanter/video/kisisellestirme ayni. Ilk FAIL'de DUR.
  overwrite eski gorseli silmezse (18 gorsel, yeni 2., eski 3.): eski 2. gorsel silinir ve geri okuma yinelenir (rapora yazilir).
Mod cl (4570143815): yedek -> cl_galeri_degistir.uygula ile 17'lik set (77 ilanla ayni sira, alt metin, renk baglari);
  sonra 1. gorsel = secilen kapak, 2. gorsel = yeni kart NCC kontrolu + kisisellestirme ayni.
Kullanim: gorsel02_degistir.py ciftler --tablo TABLO.csv --yeni YENI_DIR --out OUT --yedek-drive gdrive:... --confirm GORSEL02 [--limit N]
          gorsel02_degistir.py cl --kaynak CL17_DIR --alt ALT.csv --out OUT --yedek-drive gdrive:... --confirm GORSEL02
"""
import argparse, csv, io, json, os, subprocess, sys, time
from pathlib import Path
import numpy as np, requests
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

CL = "4570143815"
KISI = ("is_personalizable", "personalization_is_required", "personalization_char_count_max", "personalization_instructions")


def log(m): print(m, flush=True)


def drive_kopya(yerel, hedef):
    r = subprocess.run(["rclone", "copy", str(yerel), hedef, "-q"], capture_output=True, text=True)
    c = subprocess.run(["rclone", "check", str(yerel), hedef, "--one-way", "-q"], capture_output=True, text=True)
    if r.returncode or c.returncode:
        raise SystemExit(f"HATA: yedek Drive'a yazilamadi/dogrulanamadi ({hedef}). YAZMA YOK. DUR.")


def gri(b):
    im = Image.open(io.BytesIO(b) if isinstance(b, bytes) else b).convert("L")
    return np.asarray(im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)).astype(np.float32)


def ncc(a, b):
    if a.shape != b.shape: return -1.0
    a, b = a - a.mean(), b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def cdn_ncc(url, yerel):
    r = requests.get(url, timeout=120); r.raise_for_status(); return round(ncc(gri(r.content), gri(yerel)), 5)


BANT = (60, 1500, 940, 1700)   # Digital File metin bandi (kart 3000x2250); tum kart NCC'si eski/yeni ayirmaz (0.9956), bant ayirir (0.21 / 1.0)


def bant_ncc(url, yerel):
    r = requests.get(url, timeout=120); r.raise_for_status()
    Y = Image.open(yerel).convert("L"); C = Image.open(io.BytesIO(r.content)).convert("L")
    if C.size != Y.size: C = C.resize(Y.size, Image.LANCZOS)
    return round(ncc(np.asarray(C.crop(BANT)).astype(np.float32), np.asarray(Y.crop(BANT)).astype(np.float32)), 4)


def drive_var(hedef):
    r = subprocess.run(["rclone", "lsf", hedef], capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def kisi(api, lid):
    L = api.get(f"/listings/{lid}") or {}
    return {k: L.get(k) for k in KISI}


def ozet(api, shop, lid):
    g = G.galeri(api, lid)
    return dict(ids=[x.get("listing_image_id") for x in g], rank=[x.get("rank") for x in g], alt=[(x.get("alt_text") or "") for x in g],
                url=[x.get("url_fullxfull") for x in g],
                bag=sorted((v.get("value"), v.get("image_id")) for v in G.var_img(api, shop, lid)),
                kor=G.korunanlar(api, shop, lid), kisi=kisi(api, lid))


def bir_ilan(api, shop, lid, cift, yeni, out, yedek_drive):
    o = Path(out) / f"{lid}_{cift}"; o.mkdir(parents=True, exist_ok=True)
    g0 = G.galeri(api, lid)
    if len(g0) > 1 and bant_ncc(g0[1]["url_fullxfull"], yeni) >= 0.95:     # yedekten ONCE: zaten yeni kartsa dokunma
        raise SystemExit(f"DUR {cift}: canli 2. gorsel zaten yeni kart")
    man = G.yedek_al(api, shop, lid, o)
    if yedek_drive:
        h = f"{yedek_drive}/{lid}_{cift}"
        if drive_var(h): h += time.strftime("_tekrar_%Y%m%d_%H%M%S", time.gmtime())     # ilk yedegin ustune YAZILMAZ
        drive_kopya(o / "yedek", h)
    once = ozet(api, shop, lid)
    if once["kor"]["state"] != "active": raise SystemExit(f"DUR {cift}: state {once['kor']['state']}")
    if len(once["ids"]) != 17: raise SystemExit(f"DUR {cift}: {len(once['ids'])} gorsel (17 bekleniyordu)")
    if once["ids"] != [x["listing_image_id"] for x in man["galeri"]]: raise SystemExit(f"DUR {cift}: yedek sonrasi galeri degisti")
    eski2 = once["ids"][1]
    if eski2 in {i for _, i in once["bag"]}: raise SystemExit(f"DUR {cift}: 2. gorsel renk bagli")
    n_eski = cdn_ncc(once["url"][1], yeni); b_eski = bant_ncc(once["url"][1], yeni)
    if b_eski >= 0.95: raise SystemExit(f"DUR {cift}: canli 2. gorsel zaten yeni kart (bant {b_eski})")
    with open(yeni, "rb") as fh:
        r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": ("02_format.jpg", fh, "image/jpeg")},
                          data={"rank": str(once["rank"][1]), "overwrite": "true", "alt_text": once["alt"][1]})
    yid = r.get("listing_image_id")
    if not yid or yid in once["ids"]: raise SystemExit(f"DUR {cift}: yukleme id {yid}")
    beklenen = once["ids"][:1] + [yid] + once["ids"][2:]
    def ok(s): return s["ids"] == beklenen and all(b > a for a, b in zip(s["rank"], s["rank"][1:]))
    son = G.kararli(lambda: ozet(api, shop, lid), ok)
    yol = "overwrite"
    if not ok(son) and son["ids"] == once["ids"][:1] + [yid] + once["ids"][1:]:
        G.gorsel_sil(api, shop, lid, eski2); yol = "overwrite eskiyi silmedi -> eski 2. gorsel silindi"
        son = G.kararli(lambda: ozet(api, shop, lid), ok)
    sorun = []
    if not ok(son): sorun.append(f"sira/id {son['ids']}")
    if son["alt"] != once["alt"]: sorun.append("alt metin")
    if son["bag"] != once["bag"]: sorun.append("renk baglari")
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if son["kor"].get(k) != once["kor"].get(k): sorun.append(f"korunan {k}")
    if son["kisi"] != once["kisi"]: sorun.append("kisisellestirme")
    n_yeni = cdn_ncc(son["url"][1], yeni) if len(son["url"]) > 1 else -1
    b_yeni = bant_ncc(son["url"][1], yeni) if len(son["url"]) > 1 else -1
    if n_yeni < 0.9995 or b_yeni < 0.95: sorun.append(f"2. gorsel NCC {n_yeni} bant {b_yeni}")
    rap = dict(cift=cift, listing_id=lid, sonuc="PASS" if not sorun else "FAIL", sorun=sorun, yol=yol, eski_id=eski2, yeni_id=yid,
               ncc_eski_canli_vs_yeni=n_eski, bant_eski=b_eski, ncc_yeni_canli=n_yeni, bant_yeni=b_yeni, gorsel=len(son["ids"]), renk_bagi=len(son["bag"]),
               video=len(son["kor"]["video_ids"]), kota=api.remaining)
    (o / "rapor.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    return rap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["ciftler", "cl"]); ap.add_argument("--tablo"); ap.add_argument("--yeni"); ap.add_argument("--kaynak")
    ap.add_argument("--alt"); ap.add_argument("--kapak-sec", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--yedek-drive", default=""); ap.add_argument("--confirm", default=""); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kota-taban", type=int, default=300)
    a = ap.parse_args()
    if a.confirm != "GORSEL02": raise SystemExit("HATA: --confirm GORSEL02 gerekir.")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh(): st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]; out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    if a.mod == "ciftler":
        T = [r for r in csv.DictReader(open(a.tablo, encoding="utf-8")) if r["listing_id"] != CL]
        if any(r["PASS"] != "True" for r in T): raise SystemExit("DUR: TABLO'da PASS olmayan cift var")
        tamam = {p.parent.name.split("_", 1)[0] for p in out.glob("*/rapor.json") if json.loads(p.read_text())["sonuc"] == "PASS"}
        log(f"onceki PASS (atlanir): {sorted(tamam)}")
        is_ = [r for r in T if r["listing_id"] not in tamam]
        if a.limit: is_ = is_[:a.limit]
        t0 = time.time()
        for i, r in enumerate(is_, 1):
            api.get(f"/listings/{r['listing_id']}")
            if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < a.kota_taban:
                log(f"DUR: kota {api.remaining} < {a.kota_taban}"); break
            rap = bir_ilan(api, shop, r["listing_id"], r["cift"], Path(a.yeni) / r["cift"] / "02_format.jpg", out, a.yedek_drive)
            rows.append(rap); g = time.time() - t0
            log(f"[{i}/{len(is_)}] {r['cift']} {rap['sonuc']} {rap['sorun'] or ''} ncc {rap['ncc_yeni_canli']} | gecen {g/60:.1f} dk | "
                f"kalan ~{g/i*(len(is_)-i)/60:.1f} dk | %{100*i//len(is_)} | kota {api.remaining}")
            if rap["sonuc"] != "PASS": break
    else:
        o = out / f"{CL}_CANCER_LIBRA"; o.mkdir(parents=True, exist_ok=True)
        man = G.yedek_al(api, shop, CL, o)
        if a.yedek_drive:
            h = f"{a.yedek_drive}/{CL}_CANCER_LIBRA"
            if drive_var(h): h += time.strftime("_tekrar_%Y%m%d_%H%M%S", time.gmtime())
            drive_kopya(o / "yedek", h)
        k0 = kisi(api, CL)
        # 1. gorsel adayi: canli 1. gorsele en yakin kapak (kaynak dizinine 01_kapak.jpg olarak yazilir); < 0.995 ise DUR
        canli1 = man["galeri"][0]["url"]
        aday = [p for p in a.kapak_sec.split(",") if p]
        sk = sorted(((cdn_ncc(canli1, p), p) for p in aday), reverse=True)
        log(f"kapak adaylari: {sk}")
        if not sk or sk[0][0] < 0.995: raise SystemExit(f"DUR: canli kapaga uyan kapak dosyasi yok {sk}")
        hedef1 = Path(a.kaynak) / "01_kapak.jpg"
        if Path(sk[0][1]).resolve() != hedef1.resolve():
            import shutil; shutil.copyfile(sk[0][1], hedef1)          # dosya bayt bayt (yeniden sikistirma yok)
        rap = G.uygula(api, shop, CL, Path(a.kaynak), Path(a.alt), o, 150)
        g = G.galeri(api, CL); sorun = list(rap.get("sorun") or [])
        n1 = cdn_ncc(g[0]["url_fullxfull"], Path(a.kaynak) / "01_kapak.jpg"); n2 = cdn_ncc(g[1]["url_fullxfull"], Path(a.kaynak) / "02_format.jpg")
        if n1 < 0.995: sorun.append(f"1. gorsel NCC {n1}")
        b2 = bant_ncc(g[1]["url_fullxfull"], Path(a.kaynak) / "02_format.jpg")
        if n2 < 0.9995 or b2 < 0.95: sorun.append(f"2. gorsel NCC {n2} bant {b2}")
        if kisi(api, CL) != k0: sorun.append("kisisellestirme")
        bag = sorted((v.get("value"), v.get("image_id")) for v in G.var_img(api, shop, CL))
        sira = {x.get("listing_image_id"): i + 1 for i, x in enumerate(g)}
        rows.append(dict(cift="CANCER_LIBRA", listing_id=CL, sonuc="PASS" if not sorun else "FAIL", sorun=sorun, gorsel=len(g),
                         kapak=os.path.basename(sk[0][1]), ncc_kapak=n1, ncc_yeni_canli=n2, renk_bagi=[(v, sira.get(i)) for v, i in bag],
                         video=len(rap["korunan_sonra"]["video_ids"]), eski_gorsel=len(man["galeri"]), kota=api.remaining))
        (o / "rapor_gorsel02.json").write_text(json.dumps(rows[-1], indent=1, ensure_ascii=False))
    with open(out / f"SONUC_{a.mod}.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in rows: w.writerow([r["cift"], r["listing_id"], r["sonuc"], ";".join(r["sorun"]), r.get("ncc_yeni_canli"), r.get("gorsel"), r.get("yol", "")])
    n = sum(1 for r in rows if r["sonuc"] == "PASS")
    log(f"OZET {a.mod}: {n}/{len(rows)} PASS | kota {api.remaining}")
    return 0 if n == len(rows) and rows else 1


if __name__ == "__main__":
    sys.exit(main())
