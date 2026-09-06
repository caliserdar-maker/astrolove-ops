#!/usr/bin/env python3
"""
C ASAMASI - ETSY 78 ILAN: 4 ZIP + SET07 DEGISIMI (5 Eyl 2026, Mo gorevi). ETSY'YE YAZAR.

Ilan basina:
  1) 4 teslim ZIP'i (AstroLove_<Cift>_<Ed>.zip): her biri icin eskisini SIL -> yenisini
     ayni rank ile YUKLE -> geri oku (size_bytes = Drive bayti; URL varsa sha256 birebir).
     Dosya sayisi hic 5'i asmaz, 4'un altina dusmez. PDF'e (5. dosya) DOKUNULMAZ.
  2) SET07 galeri gorseli: yenisi rank 5'e YUKLENIR -> eskisi SILINIR; sira
     SET01,SET03,SET04,SET06,SET07,SET10Y korunur. Diger 5 gorsele dokunulmaz.
  3) Geri okuma: dosya 5 (PDF id ayni, 4 ZIP bayt = Drive), gorsel 6 + sira (Etsy'den
     indirilen her gorsel Drive kaynagiyla piksel duzeyinde), state ACTIVE degismemis.
     Tutmazsa o ilanda DUR, kalanlara gecilmez.
Kota: her istekten sonra x-remaining-today loglanir; < 400 ise DUR (STATE'ten devam).
STATE: --state-out CSV ilan basi aninda; --resume ile PASS olanlar atlanir.
Varsayilan DRY-RUN (--apply yoksa yazma yok). --pairs ZORUNLU (bos verilmez).
"""
import argparse
import csv
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_media_upload import GALLERY_ORDER, mock_name  # noqa: E402
from wp_mockup_common import EDITIONS  # noqa: E402

SET07_IDX = GALLERY_ORDER.index("SET07")   # 4 -> rank 5
READBACK_WAIT = 4      # 6 Eyl 2026 (Mo onayi): 8 -> 4 sn; Actions dakikasi ve kota tasarrufu
READBACK_TRIES = 5
QUOTA_STOP = 400
PIX_MAD_MAX = 6.0


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, tries=3, timeout=180):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def compare(url, src_path):
    data = fetch(url, timeout=90)
    if data is None:
        return dict(sonuc="INDIRILEMEDI")
    a = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return dict(sonuc="OKUNAMADI")
    ah, aw = a.shape[:2]
    if (aw, ah) != (b.shape[1], b.shape[0]):
        b = cv2.resize(b, (aw, ah), interpolation=cv2.INTER_AREA)
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    mad, p99 = float(d.mean()), float(np.percentile(d, 99))
    return dict(sonuc="ESLESIYOR" if mad <= PIX_MAD_MAX else "FARKLI", etsy_olcu=f"{aw}x{ah}",
                fark_ort=round(mad, 3), fark_p99=round(p99, 1))


class Ilan:
    def __init__(self, api, shop):
        self.api, self.shop = api, shop

    def state(self, lid):
        return (self.api.get(f"/listings/{lid}", ok404=True) or {}).get("state", "?")

    def files(self, lid):
        return (self.api.get(f"/shops/{self.shop}/listings/{lid}/files", ok404=True) or {}).get("results", [])

    def images(self, lid):
        r = self.api.get(f"/listings/{lid}/images", ok404=True) or {}
        return sorted(({"rank": x.get("rank") or 0, "id": x.get("listing_image_id"), "url": x.get("url_fullxfull") or ""}
                       for x in r.get("results", [])), key=lambda t: t["rank"])

    def stable(self, fn, lid, want):
        """Beklenen kosul (want) saglanan ILK okumada doner (6 Eyl 2026, Mo onayi:
        "iki ozdes okuma" sarti kaldirildi; ilan sonu geri okuma + piksel kiyasi
        asil kapidir). Saglanmazsa READBACK_TRIES kez 4 sn arayla tekrar dener."""
        cur = None
        for _ in range(READBACK_TRIES):
            time.sleep(READBACK_WAIT)
            cur = fn(lid)
            if want(cur):
                return cur
        return cur

    @staticmethod
    def _key(cur):
        return [(x.get("listing_file_id") or x.get("id"), x.get("rank"), x.get("size_bytes")) for x in cur]

    def upload_file(self, lid, path, rank):
        with open(path, "rb") as fh:
            return self.api.post_file(f"/shops/{self.shop}/listings/{lid}/files",
                                      files={"file": (Path(path).name, fh, "application/zip")},
                                      data={"name": Path(path).name, "rank": str(rank)})

    def delete_file(self, lid, fid):
        self.api.delete(f"/shops/{self.shop}/listings/{lid}/files/{fid}")

    def upload_image(self, lid, path, rank):
        with open(path, "rb") as fh:
            r = self.api.post_file(f"/shops/{self.shop}/listings/{lid}/images",
                                   files={"image": (Path(path).name, fh, "image/jpeg")}, data={"rank": str(rank)})
        return r.get("listing_image_id")

    def delete_image(self, lid, iid):
        self.api.delete(f"/shops/{self.shop}/listings/{lid}/images/{iid}")


def zip_adi(pair, ed):
    return f"AstroLove_{pair}_{ed}.zip"


def on_kontrol(files, pair):
    """5 dosya: 4 ZIP (her ad tam 1 kez) + 1 PDF. Donus (hata_listesi, pdf_kaydi)."""
    det = []
    if len(files) != 5:
        det.append(f"dosya sayisi {len(files)} != 5")
    adlar = [str(f.get("filename") or "") for f in files]
    for ed in EDITIONS:
        if adlar.count(zip_adi(pair, ed)) != 1:
            det.append(f"{zip_adi(pair, ed)} {adlar.count(zip_adi(pair, ed))} kez")
    pdf = [f for f in files if str(f.get("filename") or "").lower().endswith(".pdf")]
    if len(pdf) != 1:
        det.append(f"PDF {len(pdf)} kez")
    return det, (pdf[0] if len(pdf) == 1 else None)


def zip_degistir(il, lid, pair, ed, yerel, apply_):
    """Tek ZIP: sil -> yukle -> geri oku. Donus (durum, detay, yeni_kayit)."""
    veri = yerel.read_bytes(); boy, sha = len(veri), sha256(veri)
    ad = yerel.name
    once = il.files(lid)
    hedef = [f for f in once if f.get("filename") == ad]
    if len(hedef) != 1 or len(once) != 5:
        return "FAIL", f"{ad}: hedef {len(hedef)} kez, dosya {len(once)}", None
    hedef = hedef[0]
    eski_boy = int(hedef.get("size_bytes") or 0)
    url = hedef.get("url") or hedef.get("download_url") or ""
    if eski_boy == boy and url:
        d = fetch(url)
        if d is not None and sha256(d) == sha:
            log(f"    {ad}: Etsy zaten birebir (sha256) -> atlandi")
            return "PASS", "zaten birebir", hedef
    if not apply_:
        return "DRY", f"{ad}: {eski_boy} -> {boy} bayt", hedef
    rank = hedef.get("rank") or 1
    digerleri = sorted(str(f.get("listing_file_id")) for f in once if f is not hedef)
    log(f"    {ad}: sil {hedef.get('listing_file_id')} ({eski_boy} b, rank {rank})")
    il.delete_file(lid, hedef.get("listing_file_id"))
    cur = il.stable(il.files, lid, want=lambda c: len(c) == 4 and ad not in {f.get("filename") for f in c})
    if len(cur) != 4:
        return "FAIL", f"{ad}: silme sonrasi dosya {len(cur)} != 4", None
    log(f"    {ad}: yukle {boy} b rank {rank}")
    r = il.upload_file(lid, yerel, rank)
    cur = il.stable(il.files, lid, want=lambda c: len(c) == 5 and ad in {f.get("filename") for f in c})
    yeni = [f for f in cur if f.get("filename") == ad]
    det = []
    if len(cur) != 5:
        det.append(f"dosya {len(cur)} != 5")
    if sorted(str(f.get("listing_file_id")) for f in cur if f.get("filename") != ad) != digerleri:
        det.append("diger dosyalarin id kumesi degisti")
    if len(yeni) != 1:
        det.append(f"yeni {len(yeni)} kez")
    else:
        yb = int(yeni[0].get("size_bytes") or 0)
        if yb != boy:
            det.append(f"size_bytes {yb} != Drive {boy}")
        u = yeni[0].get("url") or yeni[0].get("download_url") or ""
        if u:
            d = fetch(u)
            if d is None or sha256(d) != sha:
                det.append("sha256 Etsy != Drive")
    return ("PASS" if not det else "FAIL"), f"{ad}: " + ("; ".join(det) if det else f"{boy} b OK (id {r.get('listing_file_id')})"), (yeni[0] if yeni else None)


def set07_degistir(il, lid, pair, mock_dir, apply_, rapor):
    """Yeni SET07 rank 5'e yukle -> eski rank-5 gorselini sil -> 6 gorsel + sira piksel dogrulamasi."""
    up = pair.upper()
    kaynak = [Path(mock_dir) / up / mock_name(s, pair) for s in GALLERY_ORDER]
    eksik = [p.name for p in kaynak if not p.exists()]
    if eksik:
        return "FAIL", f"eksik kaynak gorsel {eksik}"
    once = il.images(lid)
    if len(once) != 6:
        return "FAIL", f"gorsel {len(once)} != 6"
    eski = once[SET07_IDX]
    if not apply_:
        return "DRY", f"SET07: eski id {eski['id']} rank {eski['rank']} degisecek"
    # Etsy rank'lari ardisik olmayabilir (Leo_Pisces: SET07 rank 6); yeni gorsel eskinin rank'ina girer,
    # eski bir alta kayar, silinince sira korunur. Dogrulama: 6 gorselin piksel kiyasi.
    rank = eski["rank"] or (SET07_IDX + 1)
    log(f"    SET07: yukle rank {rank} (eski id {eski['id']} rank {eski['rank']})")
    yeni_id = il.upload_image(lid, kaynak[SET07_IDX], rank)
    cur = il.stable(il.images, lid, want=lambda c: len(c) == 7)
    if len(cur) != 7:
        return "FAIL", f"SET07 yukleme sonrasi gorsel {len(cur)} != 7"
    log(f"    SET07: eski sil {eski['id']}")
    il.delete_image(lid, eski["id"])
    cur = il.stable(il.images, lid, want=lambda c: len(c) == 6)
    if len(cur) != 6:
        return "FAIL", f"SET07 silme sonrasi gorsel {len(cur)} != 6"
    ids = [x["id"] for x in cur]
    det = []
    if yeni_id not in ids:
        det.append("yeni SET07 listede yok")
    if eski["id"] in ids:
        det.append("eski SET07 hala listede")
    for k, x in enumerate(cur):
        c = compare(x["url"], kaynak[k]) if x["url"] else dict(sonuc="URL_YOK")
        c.update(pair=pair, listing_id=lid, rank=x["rank"], sahne=GALLERY_ORDER[k], image_id=x["id"])
        rapor.append(c)
        log(f"    rank {x['rank']} {GALLERY_ORDER[k]}: {c['sonuc']} fark {c.get('fark_ort', '-')} p99 {c.get('fark_p99', '-')}")
        if c["sonuc"] != "ESLESIYOR":
            det.append(f"rank {x['rank']} {GALLERY_ORDER[k]} {c['sonuc']}")
    return ("PASS" if not det else "FAIL"), ("; ".join(det) if det else f"6 gorsel sirali, yeni id {yeni_id}")


def ilan_isle(il, pair, lid, zip_dir, mock_dir, apply_, rapor):
    up = pair.upper()
    st = il.state(lid)
    # kota kapisi ilan BASINDA (1 GET sonrasi): 400'un altina hic inilmez, yazma yapilmadan durulur
    rem = il.api.remaining
    if rem is not None and str(rem).isdigit() and int(rem) < QUOTA_STOP:
        return "KOTA", f"kota {rem} < {QUOTA_STOP}; ilana dokunulmadi"
    if st != "active":
        return "FAIL", f"state {st} != active (dokunulmadi)"
    once = il.files(lid)
    det, pdf = on_kontrol(once, pair)
    if det:
        return "FAIL", "on-kontrol: " + "; ".join(det)
    pdf_id = str(pdf.get("listing_file_id"))
    log(f"  once: dosya 5 (PDF id {pdf_id}), state active")
    zipler = {ed: Path(zip_dir) / up / zip_adi(pair, ed) for ed in EDITIONS}
    eksik = [p.name for p in zipler.values() if not p.exists()]
    if eksik:
        return "FAIL", f"Drive ZIP eksik: {eksik}"
    sonuc = []
    for ed in EDITIONS:
        d, detay, _ = zip_degistir(il, lid, pair, ed, zipler[ed], apply_)
        sonuc.append(f"{ed}:{d}")
        log(f"    -> {d} {detay}")
        if d == "FAIL":
            return "FAIL", detay
    d, detay = set07_degistir(il, lid, pair, mock_dir, apply_, rapor)
    log(f"    -> {d} {detay}")
    if d == "FAIL":
        return "FAIL", detay
    if not apply_:
        return "DRY", "; ".join(sonuc) + "; " + detay
    # son geri okuma
    son = il.files(lid)
    det, pdf2 = on_kontrol(son, pair)
    if pdf2 is None or str(pdf2.get("listing_file_id")) != pdf_id:
        det.append("PDF id degisti")
    for ed in EDITIONS:
        f = [x for x in son if x.get("filename") == zip_adi(pair, ed)]
        if f and int(f[0].get("size_bytes") or 0) != zipler[ed].stat().st_size:
            det.append(f"{ed} bayt {f[0].get('size_bytes')} != {zipler[ed].stat().st_size}")
    if il.state(lid) != "active":
        det.append("state active degil")
    return ("PASS" if not det else "FAIL"), ("; ".join(det) if det else f"dosya 5 (PDF {pdf_id} sabit, 4 ZIP bayt = Drive), gorsel 6 sirali, active")


def _append_state(path, row):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists() or p.stat().st_size == 0
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["pair", "listing_id", "status", "ts_utc", "detail", "kota_kalan"])
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="pair,listing_id CSV (WA_WP_DRAFTS_STATE.csv)")
    ap.add_argument("--pairs", required=True, help="ZORUNLU: cift listesi (virgullu, sirali)")
    ap.add_argument("--zip-dir", required=True, help="<UP>/AstroLove_<Cift>_<Ed>.zip (DELIVERY_SAAT80)")
    ap.add_argument("--mock-dir", required=True, help="<UP>/6 galeri gorseli (SET07 yeni)")
    ap.add_argument("--state-out", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--sync-cmd", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cmp-out", default="")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    ilanlar = {}
    with open(a.state, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                ilanlar[raw[0].strip()] = raw[1].strip()
    sec = [p.strip() for p in a.pairs.split(",") if p.strip()]
    if not sec:
        raise SystemExit("HATA: --pairs bos verilemez")
    yok = [p for p in sec if p not in ilanlar]
    if yok:
        raise SystemExit(f"HATA: STATE'te olmayan cift: {yok}")
    if len(set(sec)) != len(sec):
        raise SystemExit("HATA: cift tekrar ediyor")
    hedefler = [(p, ilanlar[p]) for p in sec]
    done = {}
    if Path(a.state_out).exists():
        with open(a.state_out, newline="", encoding="utf-8") as fh:
            for r in csv.reader(fh):
                if len(r) >= 3 and r[0] != "pair":
                    done[r[0]] = r[2]
    if a.resume:
        atla = [h[0] for h in hedefler if done.get(h[0]) == "PASS"]
        hedefler = [h for h in hedefler if done.get(h[0]) != "PASS"]
        log(f"resume: {len(atla)} ilan zaten PASS; kalan {len(hedefler)}")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store); api.verbose_quota = True
    il = Ilan(api, os.environ.get("ETSY_SHOP_ID", ""))
    log(f"{'UYGULA' if a.apply else 'DRY-RUN'} | {len(hedefler)} ilan")

    rows, rapor, durdu = [], [], ""
    t0 = time.time(); n = len(hedefler)
    for i, (pair, lid) in enumerate(hedefler):
        log(f"\n[{i + 1}/{n}] {pair} {lid}")
        try:
            status, detail = ilan_isle(il, pair, lid, a.zip_dir, a.mock_dir, a.apply, rapor)
        except SystemExit as e:
            status, detail = "FAIL", str(e)[:300]
        rows.append([pair, lid, status, utc(), detail, api.remaining])
        _append_state(a.state_out, rows[-1])
        if a.sync_cmd:
            subprocess.run(a.sync_cmd, shell=True, check=False)
        el = time.time() - t0
        log(f"[{i + 1}/{n} %{100 * (i + 1) / n:.0f}] {pair}: {status} | {detail} | kota {api.remaining} | "
            f"gecen {el / 60:.1f} dk kalan {el / (i + 1) * (n - i - 1) / 60:.1f} dk")
        if status == "KOTA":
            durdu = f"kota {api.remaining} < {QUOTA_STOP}; {pair} dahil kalan {n - i} ilan STATE'ten devam eder"
            log(f"DURDU: {durdu}"); break
        if status == "FAIL":
            durdu = f"{pair} ({lid}) FAIL -> kalan {n - i - 1} ilana GECILMEDI"
            log(f"DURDU: {durdu}"); break
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < QUOTA_STOP:
            durdu = f"kota {api.remaining} < {QUOTA_STOP}; kalan {n - i - 1} ilan STATE'ten devam eder"
            log(f"DURDU: {durdu}"); break

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["pair", "listing_id", "status", "ts_utc", "detail", "kota_kalan"]); w.writerows(rows)
    if a.cmp_out and rapor:
        cols = list(dict.fromkeys(k for r in rapor for k in r))
        with open(a.cmp_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rapor)
    n_pass = sum(1 for r in rows if r[2] == "PASS"); n_once = sum(1 for v in done.values() if v == "PASS")
    lines = [f"## C etsy ({'uygulandi' if a.apply else 'DRY-RUN'}): bu kosu {n_pass}/{len(rows)} PASS; onceki PASS {n_once}; "
             f"toplam PASS {n_pass + n_once}/{len(sec)} | kota {api.remaining}", "",
             "| pair | listing_id | sonuc | detay |", "|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[4][:160]} |" for r in rows]
    if durdu:
        lines += ["", f"**DURDU:** {durdu}"]
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0 if (not durdu or durdu.startswith("kota")) and all(r[2] in ("PASS", "DRY", "KOTA") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
