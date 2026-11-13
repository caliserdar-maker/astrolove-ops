#!/usr/bin/env python3
"""S13 (Serdar 8 Kas gece "hepsi oneriyle", 9 Kas "ok", 13 Kas gorev metni): data/pod/ORNAMENT78_METIN.csv aciklama sutunu
CANLIDAN guncellenir (SALT OKUMA; Etsy'ye yazma YOK). Yeni EN metin yazilmaz: canli aciklama tam() ile alinir
(html.unescape, \\r\\n -> \\n, bas / son bosluk kirpilir; emsal yayina_hazir.py tam, aktif_metin_oku.py). Diger 19 sutun, satir
sayisi ve kod sirasi birebir kalir; yazim csv.DictWriter varsayilani (uretec ornament_metin.py ile ayni ayar).

Etsy (yalniz GET, SaltOkur; GET disi istek SystemExit): GET /shops/{shop} (kota) + GET /listings/batch (100'luk).
Tahmini istek = 1 + batch sayisi; baslangic kapisi: kalan >= tahmin + KOTA_MIN (10); sert taban Etsy sinifinda.

DUR (CSV yazilmaz; OZET.json + FARK.md yazilir, cikis 1):
  CSV 78 satir / 20 sutun / kod tekil degil; ilan listesinde kod kumesi CSV'den farkli; listing_id yok; ayni kod iki kez;
  batch yanitinda ilan yok; ilan active degil; description yok; kota yetmez;
  yeni aciklamalarda (78 ilanin hepsinde) SPEC yasak deseni var, SPEC zorunlu cumle yok, ornament_taslak.metin_kontrol hatasi,
  AI beyani yok (etsy_common.beyan_var en).
Cikti (--out): ORNAMENT78_METIN.csv (yalniz kapilar PASS ise), OZET.json, FARK.md. Ilan kimligi ciktilara YAZILMAZ.
Kullanim: python3 ornament_metin_canli.py --ilanlar ILANLAR.json --csv data/pod/ORNAMENT78_METIN.csv --spec SPEC.json --out _out
          python3 ornament_metin_canli.py sir-say _out   (cikis 0 temiz / 3 sir gecti / 4 ortam degeri bos)
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE."""
import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, beyan_var, mask  # noqa: E402
import ornament_taslak  # noqa: E402  (metin_kontrol: depodaki kuralin kendisi; kopya yok)

KOTA_MIN = 10
SUTUN = ["kod", "baslik", "etiketler", "aciklama"] + [f"alt_{i:02d}" for i in range(1, 12)] + \
        ["soru1", "soru2", "soru3", "talimat_isim", "talimat_tarih"]
N_SATIR = 78
TIRE = re.compile("[–—]")


class SaltOkur(Etsy):
    """Calisma aninda GET disi istek yasak (emsal yayina_hazir.SaltOkur)."""
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r


class Dur(SystemExit):
    pass


def tam(t):
    return html.unescape(str(t or "")).replace("\r\n", "\n").strip()


def norm(t):
    return " ".join(html.unescape(str(t or "")).split())


def blob_sha(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _tekil_cift(cifts):
    """json.load object_pairs_hook: ayni anahtar iki kez -> DUR (sessizce sonuncusu alinmasin)."""
    d = {}
    for k, v in cifts:
        if k in d:
            raise Dur(f"DUR: ilan listesinde tekrar eden kod {k}")
        d[k] = v
    return d


def csv_oku(yol):
    ham = Path(yol).read_bytes()
    r = csv.DictReader(io.StringIO(ham.decode("utf-8"), newline=""))
    rows = list(r)
    if r.fieldnames != SUTUN:
        raise Dur(f"DUR: CSV sutunlari beklenen 20 sutun degil ({len(r.fieldnames or [])} sutun)")
    kodlar = [x["kod"] for x in rows]
    if len(rows) != N_SATIR or len(set(kodlar)) != N_SATIR:
        raise Dur(f"DUR: CSV {len(rows)} satir, tekil kod {len(set(kodlar))} (beklenen {N_SATIR})")
    return ham, rows


def csv_yaz(rows):
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=SUTUN)
    w.writeheader(); w.writerows(rows)
    return s.getvalue().encode("utf-8")


def ilan_listesi(Y, kodlar):
    if not isinstance(Y, dict):
        raise Dur("DUR: ilan listesi sozluk degil")
    eksik, fazla = sorted(set(kodlar) - set(Y)), sorted(set(Y) - set(kodlar))
    if eksik or fazla:
        raise Dur(f"DUR: kod kumesi farkli (eksik {len(eksik)}: {eksik[:5]}, fazla {len(fazla)}: {fazla[:5]})")
    ids = {}
    for k in kodlar:
        v = Y[k]
        if not (isinstance(v, dict) and str(v.get("listing_id", "")).isdigit()):
            raise Dur(f"DUR: {k} listing_id yok")
        ids[k] = int(v["listing_id"])
    if len(set(ids.values())) != len(ids):
        raise Dur("DUR: ayni listing_id iki koda bagli")
    return ids


def batch(api, ids):
    res, n = [], 0
    for i in range(0, len(ids), 100):
        r = api.get("/listings/batch", params={"listing_ids": ",".join(str(x) for x in ids[i:i + 100])}) or {}
        res += r.get("results") or []
        n += 1
    return {int(x["listing_id"]): x for x in res if str(x.get("listing_id", "")).isdigit()}, n


def kapilar(rows_yeni, spec):
    b = spec["beklenen"]
    zorunlu, yasak = b.get("aciklama_zorunlu") or [], b.get("aciklama_yasak") or []
    if not zorunlu or not yasak:
        raise Dur("DUR: SPEC aciklama_zorunlu / aciklama_yasak bos")
    K = {"yasak_desen": 0, "zorunlu_cumle": 0, "metin_kontrol_hata": 0, "ai_beyan": 0, "tire": 0}
    hata = {}
    for r in rows_yeni:
        a = r["aciklama"]
        h = []
        if any(re.search(y, a, re.I) for y in yasak):
            K["yasak_desen"] += 1; h.append("yasak desen")
        if all(norm(z) in norm(a) for z in zorunlu):
            K["zorunlu_cumle"] += 1
        else:
            h.append("zorunlu cumle yok")
        mk = ornament_taslak.metin_kontrol(r)[-1]
        if mk:
            K["metin_kontrol_hata"] += 1; h.append("metin_kontrol: " + "; ".join(str(x)[:80] for x in mk))
        if beyan_var(a, "en"):
            K["ai_beyan"] += 1
        else:
            h.append("AI beyani yok")
        K["tire"] += len(TIRE.findall(a))
        if h:
            hata[r["kod"]] = h
    return K, hata


def fark_md(degisen, O):
    out = ["# ORNAMENT78_METIN aciklama farki (canli -> CSV)", "",
           f"Degisen {O['degisen']} / degismeyen {O['degismeyen']}. Ilan kimligi bu dosyaya yazilmaz.", ""]
    for kod, eski, yeni in degisen:
        i = next((j for j in range(min(len(eski), len(yeni))) if eski[j] != yeni[j]), min(len(eski), len(yeni)))
        out += [f"## {kod}", f"- ilk farkli konum: {i} (eski {len(eski)} kr, yeni {len(yeni)} kr)",
                f"- eski: {json.dumps(eski[i:i + 120], ensure_ascii=False)}", f"- yeni: {json.dumps(yeni[i:i + 120], ensure_ascii=False)}", ""]
    if O.get("kapi_hata"):
        out += ["## KAPI HATALARI", ""] + [f"- {k}: {'; '.join(v)}" for k, v in sorted(O["kapi_hata"].items())]
    return "\n".join(out) + "\n"


def calis(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    O = {"durum": "BASLADI", "istek": 0, "kota_bas": None, "kota_son": None}
    degisen = []

    def kaydet():
        json.dump(O, open(out / "OZET.json", "w"), indent=1, ensure_ascii=False)
        (out / "FARK.md").write_text(fark_md(degisen, dict(O, degisen=O.get("degisen"), degismeyen=O.get("degismeyen"))), encoding="utf-8")

    api = None
    try:
        spec = json.load(open(a.spec, encoding="utf-8"))
        ham, rows = csv_oku(a.csv)
        O.update(csv_satir=len(rows), csv_sha256_eski=hashlib.sha256(ham).hexdigest(), csv_blob_eski=blob_sha(ham))
        Y = json.load(open(a.ilanlar, encoding="utf-8"), object_pairs_hook=_tekil_cift)
        ids = ilan_listesi(Y, [r["kod"] for r in rows])
        k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(k); mask(s)
        store = TokenStore(os.environ["TOKEN_FILE"], k, s)
        if store.needs_refresh():
            store.refresh()
        api = SaltOkur(store)
        shop = os.environ.get("ETSY_SHOP_ID", "39729443")
        api.get(f"/shops/{shop}")
        O["kota_bas"] = api.remaining
        nb = (len(ids) + 99) // 100
        tahmin = 1 + nb
        O["tahmini_istek"] = tahmin
        if not str(api.remaining).isdigit() or int(api.remaining) < tahmin + KOTA_MIN:
            raise Dur(f"DUR: kota {api.remaining} < tahmini istek {tahmin} + {KOTA_MIN} (okuma baslamadi)")
        B, _ = batch(api, [ids[r["kod"]] for r in rows])
        yok = [r["kod"] for r in rows if ids[r["kod"]] not in B]
        if yok:
            raise Dur(f"DUR: batch yanitinda {len(yok)} ilan yok ({yok[:5]})")
        sayac = dict(ham_cr=0, bas_son_bosluk=0, yasak_once=0, baslik_farkli=0, etiket_farkli=0, taslak593_esit=0)
        yasak = spec["beklenen"]["aciklama_yasak"]
        rows_yeni = []
        for r in rows:
            L = B[ids[r["kod"]]]
            if L.get("state") != "active":
                raise Dur(f"DUR: {r['kod']} active degil ({L.get('state')})")
            d = L.get("description")
            if not isinstance(d, str) or not d.strip():
                raise Dur(f"DUR: {r['kod']} description yok")
            sayac["ham_cr"] += d.count("\r")
            sayac["bas_son_bosluk"] += int(d != d.strip())
            sayac["yasak_once"] += int(any(re.search(y, r["aciklama"], re.I) for y in yasak))
            sayac["baslik_farkli"] += int(norm(r["baslik"]) != norm(L.get("title")))
            sayac["etiket_farkli"] += int({t.strip() for t in r["etiketler"].split(",")} != {str(t).strip() for t in L.get("tags") or []})
            esit593 = html.unescape(d).strip() == r["aciklama"].strip()   # ornament_taslak.py:593 olcutu: esitse eski deger kalir
            sayac["taslak593_esit"] += int(esit593)
            yeni = tam(d)
            r2 = dict(r)
            if not esit593 and yeni != r["aciklama"]:                    # yalniz \r\n farki (tam() sonrasi ayni) degisiklik sayilmaz
                if "\r" in yeni:
                    raise Dur(f"DUR: {r['kod']} yeni aciklamada CR kaldi (yalniz \\r\\n -> \\n cevrilir; CSV yazilmadi)")
                r2["aciklama"] = yeni
                degisen.append((r["kod"], r["aciklama"], yeni))
            rows_yeni.append(r2)
        O.update(sayac)
        O["degisen"], O["degismeyen"] = len(degisen), len(rows) - len(degisen)
        K, hata = kapilar(rows_yeni, spec)
        O.update({f"yeni_{k}": v for k, v in K.items()})
        O["kapi_hata"] = hata
        if hata or K["yasak_desen"] or K["zorunlu_cumle"] != N_SATIR or K["metin_kontrol_hata"] or K["ai_beyan"] != N_SATIR:
            raise Dur(f"DUR: kapi FAIL ({len(hata)} ilan; CSV yazilmadi)")
        yeni_ham = csv_yaz(rows_yeni)
        if not degisen and yeni_ham != ham:
            raise Dur("DUR: degisiklik yokken yeniden yazilan CSV bayt bayt ayni degil (yazim ayari farki)")
        geri = csv.DictReader(io.StringIO(yeni_ham.decode("utf-8"), newline=""))   # yazilacak bayt yeniden okunur (bellek kopyasi degil)
        R = list(geri)
        if (geri.fieldnames != SUTUN or len(R) != len(rows) or [x["kod"] for x in R] != [x["kod"] for x in rows]
                or any(a_[c] != b_[c] for a_, b_ in zip(rows, R) for c in SUTUN if c != "aciklama")
                or any(a_["aciklama"] != b_["aciklama"] for a_, b_ in zip(rows_yeni, R)) or any("\r" in x["aciklama"] for x in R)):
            raise Dur("DUR: yeniden okunan CSV'de aciklama disinda sutun / sira degisti ya da alan icinde CR var")
        (out / "ORNAMENT78_METIN.csv").write_bytes(yeni_ham)
        O.update(csv_sha256_yeni=hashlib.sha256(yeni_ham).hexdigest(), csv_blob_yeni=blob_sha(yeni_ham), durum="PASS")
        return 0
    except SystemExit as e:
        O["durum"] = str(e.code)[:300]
        return 1
    except Exception as e:                    # noqa: BLE001 beklenmeyen hata: yalniz tur adi (deger / izleme yazilmaz), CSV yazilmaz
        O["durum"] = f"HATA: {type(e).__name__}"
        return 1
    finally:
        if api is not None:
            O["istek"], O["kota_son"] = api.calls, api.remaining
        kaydet()


def sir_say(kok):
    """Ciktilarda (log dahil) ortamdaki ETSY_SHARED_SECRET ve ETSY_API_KEY degerlerinin gecme SAYISI (deger, uzunluk, ozet yazilmaz).
    -> 0 temiz, 3 sayi > 0 (Drive ve dal yazimi yok), 4 deger bos (kontrol yapilamadi; CLAUDE.md:122). Gorev metni 13 Kas, Genel Merkez eki:
    sir_koru yalniz 12+ karakteri sayar; kisa shared secret icin ayri sayim. Bilinen sinir: kisa degerde rastlantisal eslesme olabilir."""
    degerler = [os.environ.get("ETSY_SHARED_SECRET", ""), os.environ.get("ETSY_API_KEY", "")]
    if not all(degerler):
        print("SIR SAYIMI: kontrol yapilamadi (ortam degeri bos)", flush=True)
        return 4
    toplam = 0
    for f in sorted(p for p in Path(kok).rglob("*") if p.is_file()):
        b = f.read_bytes()
        n = sum(b.count(v.encode("utf-8")) for v in degerler)
        if n:
            print(f"SIR SAYIMI: {f.name}: {n}", flush=True)
            toplam += n
    print(f"SIR SAYIMI: toplam {toplam}", flush=True)
    return 3 if toplam else 0


def _sinyal(signum, frame):
    raise Dur(f"DUR: sinyal {signum} (iptal / zaman asimi)")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["sir-say"]:
        return sir_say(argv[1] if len(argv) > 1 else "_out")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ilanlar", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default="_out")
    a = ap.parse_args(argv)
    signal.signal(signal.SIGTERM, _sinyal)
    rc = calis(a)
    O = json.load(open(Path(a.out) / "OZET.json"))
    print(f"durum: {O['durum']} | degisen {O.get('degisen')} | degismeyen {O.get('degismeyen')} | istek {O['istek']} "
          f"| kota bas {O['kota_bas']} son {O['kota_son']}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
