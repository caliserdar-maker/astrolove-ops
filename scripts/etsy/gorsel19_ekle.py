#!/usr/bin/env python3
"""C2 (Serdar 10 Eki onayi): WP 19 ilan karti (Warm Parchment renk gorseli) 78 ilana 18. gorsel olarak eklenir.

Mod yedek (SALT OKUMA): 78 ilanin canli galerisi (id + sira + rank + alt metin + url), renk baglari, video, korunan alanlar
  (state, baslik, etiket, aciklama sha, envanter sha), kisisellestirme -> OUT/YEDEK_78.json. Etsy'ye yazmaz.
Mod ekle (ETSY'YE YAZAR, --confirm GORSEL19): ilan basina
  tam yedek (manifest + tum canli gorseller, Drive'a kopya + rclone check; ilk yedegin ustune yazilmaz)
  -> on kosul: state active, tam 17 gorsel, canli hicbir gorsel yeni kartla ayni degil (NCC < 0.95), kart 3000x2250
  -> uploadListingImage(rank = 18, overwrite yok, alt metin = galeri alt metni 19. satir)
  -> geri okuma: 18 gorsel; ilk 17 id + sira AYNI, 18. = yeni id ve yerel kartla NCC >= 0.9995; ilk 17 alt metin ayni;
     renk baglari, video, state/baslik/etiket/aciklama/envanter, kisisellestirme AYNI.
  Geri okuma FAIL ise yeni gorsel silinir (ilan eski haline doner, galeri tekrar okunur), ilan FAIL raporlanir ve atlanir.
  On kosul FAIL = yazma yok, ilan atlanir. Yalniz geri alma dogrulanamazsa kosu DURUR.
  Renk bagi (Warm Parchment varyasyonu) EKLENMEZ (Serdar: baska alan degismez).
Kullanim: gorsel19_ekle.py yedek --ids pod78_ids.csv --out OUT
          gorsel19_ekle.py ekle --ids pod78_ids.csv --kartlar SON78_DIR --tablo TABLO_78.csv --alt ALT.csv --out OUT
                           --yedek-drive gdrive:... --confirm GORSEL19 [--cift A,B | --limit N]
"""
import argparse, csv, json, os, subprocess, sys, time
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
from gorsel02_degistir import cdn_ncc, drive_kopya, drive_var, kisi  # noqa: E402

KART = "19_renk_warm_parchment.jpg"
ONCE_N = 17


def log(m): print(m, flush=True)


def ozet(api, shop, lid):
    g = G.galeri(api, lid)
    return dict(ids=[x.get("listing_image_id") for x in g], rank=[x.get("rank") for x in g], alt=[(x.get("alt_text") or "") for x in g],
                url=[x.get("url_fullxfull") for x in g],
                bag=sorted((v.get("value"), v.get("image_id")) for v in G.var_img(api, shop, lid)),
                kor=G.korunanlar(api, shop, lid), kisi=kisi(api, lid))


def alt19(alt_csv):
    for r in csv.reader(open(alt_csv, encoding="utf-8")):
        if r and r[0].strip() == "19":
            return r[1].strip()
    raise SystemExit("HATA: alt metin 19 yok")


def bir_ilan(api, shop, lid, cift, kart, alt, out, yedek_drive):
    o = Path(out) / f"{lid}_{cift}"; o.mkdir(parents=True, exist_ok=True)
    if Image.open(kart).size != (3000, 2250): raise SystemExit(f"DUR {cift}: kart boyutu {Image.open(kart).size}")
    g0 = G.galeri(api, lid)
    ayni = [round(cdn_ncc(x["url_fullxfull"], kart), 4) for x in g0]
    if ayni and max(ayni) >= 0.95: raise SystemExit(f"DUR {cift}: canli galeride kart zaten var (NCC {max(ayni)})")
    man = G.yedek_al(api, shop, lid, o)
    if yedek_drive:
        h = f"{yedek_drive}/{lid}_{cift}"
        if drive_var(h): h += time.strftime("_tekrar_%Y%m%d_%H%M%S", time.gmtime())
        drive_kopya(o / "yedek", h)
    once = ozet(api, shop, lid)
    if once["kor"]["state"] != "active": raise SystemExit(f"DUR {cift}: state {once['kor']['state']}")
    if len(once["ids"]) != ONCE_N: raise SystemExit(f"DUR {cift}: {len(once['ids'])} gorsel ({ONCE_N} bekleniyordu)")
    if once["ids"] != [x["listing_image_id"] for x in man["galeri"]]: raise SystemExit(f"DUR {cift}: yedek sonrasi galeri degisti")
    with open(kart, "rb") as fh:
        r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (KART, fh, "image/jpeg")},
                          data={"rank": str(ONCE_N + 1), "alt_text": alt})
    yid = r.get("listing_image_id")
    if not yid or yid in once["ids"]: raise SystemExit(f"DUR {cift}: yukleme id {yid}")
    beklenen = once["ids"] + [yid]
    def ok(s): return s["ids"] == beklenen and all(b > a for a, b in zip(s["rank"], s["rank"][1:]))
    son = G.kararli(lambda: ozet(api, shop, lid), ok)
    sorun = []
    if not ok(son): sorun.append(f"sira/id {son['ids']}")
    if son["alt"][:ONCE_N] != once["alt"]: sorun.append("alt metin (ilk 17)")
    if len(son["alt"]) > ONCE_N and son["alt"][ONCE_N] != alt: sorun.append("alt metin (18)")
    if son["bag"] != once["bag"]: sorun.append("renk baglari")
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if son["kor"].get(k) != once["kor"].get(k): sorun.append(f"korunan {k}")
    if son["kisi"] != once["kisi"]: sorun.append("kisisellestirme")
    n_yeni = cdn_ncc(son["url"][ONCE_N], kart) if len(son["url"]) > ONCE_N and son["ids"][ONCE_N] == yid else -1
    if n_yeni < 0.9995: sorun.append(f"18. gorsel NCC {n_yeni}")
    geri = ""
    if sorun and yid in son["ids"]:
        G.gorsel_sil(api, shop, lid, yid)
        g2 = G.kararli(lambda: ozet(api, shop, lid), lambda s: s["ids"] == once["ids"])
        geri = "yeni gorsel silindi, galeri eski hal" if g2["ids"] == once["ids"] else f"GERI ALMA DOGRULANAMADI {g2['ids']}"
    rap = dict(cift=cift, listing_id=lid, sonuc="PASS" if not sorun else "FAIL", sorun=sorun, geri_alma=geri, yeni_id=yid,
               ncc_yeni_canli=n_yeni, gorsel=len(son["ids"]), sira_ilk17_ayni=son["ids"][:ONCE_N] == once["ids"],
               renk_bagi=len(son["bag"]), video=len(son["kor"]["video_ids"]), kota=api.remaining,
               link=f"https://www.etsy.com/listing/{lid}")
    (o / "rapor.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    return rap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["yedek", "ekle"]); ap.add_argument("--ids", required=True); ap.add_argument("--kartlar")
    ap.add_argument("--tablo"); ap.add_argument("--alt"); ap.add_argument("--out", required=True)
    ap.add_argument("--yedek-drive", default=""); ap.add_argument("--confirm", default=""); ap.add_argument("--cift", default="")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--kota-taban", type=int, default=300)
    a = ap.parse_args()
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh(): st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]; out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ids = [(r["listing_id"].strip(), r["cift"].strip()) for r in csv.DictReader(open(a.ids, encoding="utf-8"))]
    if len(ids) != 78: raise SystemExit(f"HATA: {len(ids)} ilan (78 bekleniyordu)")
    t0 = time.time()
    if a.mod == "yedek":
        Y = {}
        for i, (lid, c) in enumerate(ids, 1):
            z = ozet(api, shop, lid); Y[c] = dict(listing_id=lid, **{q: z[q] for q in ("ids", "rank", "alt", "url", "bag", "kor", "kisi")})
            g = time.time() - t0
            log(f"[{i}/78] {c} {len(z['ids'])} gorsel, {len(z['bag'])} renk bagi, {z['kor']['state']} | gecen {g:.0f}s | kalan ~{g/i*(78-i):.0f}s | %{100*i//78}")
        (out / "YEDEK_78.json").write_text(json.dumps(Y, indent=1, ensure_ascii=False))
        n17 = sum(1 for v in Y.values() if len(v["ids"]) == ONCE_N and v["kor"]["state"] == "active")
        log(f"OZET yedek: 78 ilan | 17 gorsel + active: {n17} | digerleri: "
            f"{[(c, len(v['ids']), v['kor']['state']) for c, v in Y.items() if not (len(v['ids']) == ONCE_N and v['kor']['state'] == 'active')]} | kota {api.remaining}")
        return 0
    if a.confirm != "GORSEL19": raise SystemExit("HATA: --confirm GORSEL19 gerekir.")
    T = list(csv.DictReader(open(a.tablo, encoding="utf-8")))
    if len(T) != 78 or any(r["SONUC"] != "PASS" for r in T): raise SystemExit("DUR: TABLO_78 78 satir PASS degil")
    alt = alt19(a.alt)
    tamam = {p.parent.name.split("_", 1)[0] for p in out.glob("*/rapor.json") if json.loads(p.read_text())["sonuc"] == "PASS"}
    log(f"onceki PASS (atlanir): {len(tamam)}")
    is_ = [(lid, c) for lid, c in ids if lid not in tamam]
    if a.cift: is_ = [(lid, c) for lid, c in is_ if c in a.cift.split(",")]
    if a.limit: is_ = is_[:a.limit]
    rows = []
    for i, (lid, c) in enumerate(is_, 1):
        api.get(f"/listings/{lid}")
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < a.kota_taban:
            log(f"DUR: kota {api.remaining} < {a.kota_taban}"); break
        try:
            rap = bir_ilan(api, shop, lid, c, Path(a.kartlar) / c / KART, alt, out, a.yedek_drive)
        except SystemExit as e:                      # on kosul DUR: Etsy'ye yazilmadi -> ilan atlanir, raporlanir
            if not str(e).startswith("DUR"): raise
            rap = dict(cift=c, listing_id=lid, sonuc="FAIL", sorun=[str(e)], geri_alma="yazma yok (on kosul)", ncc_yeni_canli=-1,
                       gorsel=-1, link=f"https://www.etsy.com/listing/{lid}")
            (out / f"{lid}_{c}").mkdir(parents=True, exist_ok=True)
            (out / f"{lid}_{c}" / "rapor.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
        rows.append(rap); g = time.time() - t0
        log(f"[{i}/{len(is_)}] {c} {rap['sonuc']} {rap['sorun'] or ''} {rap['geri_alma']} ncc {rap['ncc_yeni_canli']} gorsel {rap['gorsel']} | "
            f"gecen {g/60:.1f} dk | kalan ~{g/i*(len(is_)-i)/60:.1f} dk | %{100*i//len(is_)} | kota {api.remaining} | {rap['link']}")
        if rap["sonuc"] != "PASS" and rap["geri_alma"] not in ("yazma yok (on kosul)", "yeni gorsel silindi, galeri eski hal"):
            log(f"DUR: {c} geri alma dogrulanamadi"); break        # ilan eski haline donmediyse kosu durur
    with open(out / "SONUC_ekle.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in rows: w.writerow([r["cift"], r["listing_id"], r["sonuc"], ";".join(r["sorun"]), r["geri_alma"], r["ncc_yeni_canli"], r["gorsel"]])
    n = sum(1 for r in rows if r["sonuc"] == "PASS")
    log(f"OZET ekle: {n}/{len(rows)} PASS | kota {api.remaining}")
    return 0 if n == len(rows) and rows else 1


if __name__ == "__main__":
    sys.exit(main())
