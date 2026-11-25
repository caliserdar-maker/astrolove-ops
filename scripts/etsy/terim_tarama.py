#!/usr/bin/env python3
"""DIJITAL ARASTIRMA: TERIM TARAMASI (huni Asama 1; Serdar 26 Kas "Evet derhal basla", KARARLAR_20261126_1 ve _2).
SALT OKUMA: yalniz GET (dijital_arastirma.SaltOkur), yalniz API anahtari (OAuth token yok). Yorum cagrisi YOK.

Terim basina en cok TERIM_ISTEK_AZAMI = 6 mantiksal cagri (cagri sutunu; etsy_common'un 5xx / kisa 429 yeniden denemeleri
gercek istek sayisini artirabilir, istek sutunu ve sayac gercek istegi sayar):
  1) findAllListingsActive keywords=terim, sort_on=score, limit=100 (ilk sayfa)
  2) listing_type == "download" ilan sayisi DL_MIN (30) altindaysa ve sayfa doluysa en cok EK_SAYFA (2) sayfa daha
  3) getListingsByListingIds (/listings/batch, includes=Shop, 100'luk): YALNIZ magazasi henuz okunmamis (ya da okumasi
     MAGAZA_TAZE_GUN'den eski) magazalarin her biri icin tek temsilci ilan (ilan alanlari 1. adimin yanitinda zaten var;
     API_OLCUM 25 Kas: original_creation_timestamp / num_favorers / price / listing_type 200/200 dolu).
Olcutler indirilebilir ilan kumesi (taranan sayfalardaki listing_type == download) uzerindedir; "ilk100_*" yalniz 1. sayfa
(terimler arasi karsilastirma icin: taranan sayfa sayisi terime gore 1-3 degisir). az_veri = download_n < AZ_VERI_N.
Magaza payi = magazanin indirilebilir ilan sayisi / indirilebilir ilan sayisi. Genc magaza = create_date bugunden 365 gunden yeni.

Kota kapisi: kosu basinda (/openapi-ping, istemci uzerinden) ve her terimden once x-remaining-today; kalan < --kota-alt ya da baslik
okunamazsa temiz DUR (cikis 3); kalan terimler terim_durum.json'da, yeniden kosu kaldigi terimden surer. --kota-alt VARSAYILANI
etsy_common.KOTA_SINIRI (10): CLAUDE.md KOTA SINIRI kurali "tum betik / is akisi varsayilanlari 10, yeni esik onerilmez" (gorev metnindeki
1.200, Serdar acikca onaylarsa kosu girdisi olarak verilir). Terim yarim kalirsa (istek arasinda kota / sure / yol verme) o terim
yazilmaz, sonraki kosuda bastan okunur. Okunamayan terim sona alinir; TERIM_HATA_DENEME (2) kosuda okunamazsa durum 'hata' yazilir.
Cikti (yalniz --out; is akisi gizli Drive'a yazar): TERIM_TARAMA.csv (terim basina tek satir), TERIM_ILAN.csv, TERIM_MAGAZA.csv,
terim_durum.json (toplam istek sayaci, zaman damgasi, kosu kayitlari, kalan terim).
Log: yalniz sayilar (terim sayisi, istek, kalan kota); terim / baslik / magaza adi / fiyat loga yazilmaz (KimlikSuz da acik).
Cikis: 0 = temiz (bitti ya da sure doldu; durum.json 'durum'), 3 = kota, 4 = yol verildi, 1 = hata.
"""
import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import dijital_arastirma as D  # noqa: E402

KOTA_ALT = E.KOTA_SINIRI   # varsayilan esik = 10 (CLAUDE.md KOTA SINIRI); daha yuksegi yalniz --kota-alt girdisiyle
SAYFA_N = 100              # findAllListingsActive limit en cok 100
DL_MIN = 30                # bundan az indirilebilir ilan -> ek sayfa
EK_SAYFA = 2
TERIM_ISTEK_AZAMI = 6
BATCH_N = 100              # getListingsByListingIds cagri basina kimlik
GENC_GUN = 365
MAGAZA_TAZE_GUN = 7        # bu kadar gunden eski magaza okumasi yeniden okunur
AY_SN = 30.4375 * 86400
ARDISIK_HATA_AZAMI = 3
TERIM_HATA_DENEME = 2      # bu kadar kosuda okunamayan terim 'hata' olarak kapanir (--yeniden ile yeniden olculur)
AZ_VERI_N = 10
VARSAYILAN_LISTE = Path(__file__).resolve().parents[2] / "config" / "dijital_terimler.txt"

TARAMA_ALAN = ["terim", "durum", "toplam_sonuc_api", "ilk100_ilan", "ilk100_download_n", "ilk100_download_oran", "sayfa",
               "download_n", "az_veri", "farkli_magaza", "en_buyuk_magaza_payi", "ilk3_magaza_payi", "ilk100_farkli_magaza",
               "ilk100_en_buyuk_magaza_payi", "magaza_bilinen_n",
               "magaza_yasi_medyan_ay", "genc_magaza_n", "genc_magaza_payi", "genc_satis100_n", "genc_satis100_satis_medyan",
               "magaza_satis_medyan", "ilan_yasi_medyan_ay", "ilan_yasi_bilinen_n", "favori_medyan", "fiyat_medyan_usd",
               "fiyat_usd_n", "fiyat_usd_disi_n", "fiyat_yok_n", "cagri", "istek", "olcum_utc"]
ILAN_ALAN = ["terim", "sayfa", "sira", "listing_id", "shop_id", "listing_type", "is_personalizable", "title", "price",
             "currency", "num_favorers", "original_creation_timestamp", "created_timestamp", "taxonomy_id", "url"]
MAGAZA_ALAN = ["shop_id", "shop_name", "url", "create_date", "created_timestamp", "transaction_sold_count", "review_count",
               "review_average", "listing_active_count", "digital_listing_count", "num_favorers", "is_vacation", "okuma_ts"]


class TerimHata(Exception):
    pass


def log(m):
    print(m, flush=True)


def utc(ts=None):
    return datetime.fromtimestamp(ts if ts is not None else time.time(), timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ terimler (dijital_arastirma ile ortak)
terimler_oku = D.terimler_oku
secim_coz = D.secim_coz


# ------------------------------------------------------------------ olcutler (ag yok)
def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def medyan(xs, nd=2):
    xs = [x for x in xs if x is not None]
    return round(float(statistics.median(xs)), nd) if xs else ""   # hep float: CSV bicimi tek tip


def oran(a, b, nd=3):
    return round(a / b, nd) if b else ""


def magaza_kurulus(m):
    return _int(m.get("create_date")) or _int(m.get("created_timestamp"))


def metrikler(ilk100, dl, magaza, simdi):
    """ilk100: 1. sayfa ilanlari; dl: taranan sayfalardaki tekil indirilebilir ilanlar; magaza: shop_id(str) -> satir."""
    n = len(dl)
    say = Counter(str(L.get("shop_id")) for L in dl)
    sirali = sorted(say.values(), reverse=True)
    bilinen = [magaza[s] for s in say if s in magaza]
    yas, genc, satis = [], [], []
    for m in bilinen:
        k = magaza_kurulus(m)
        sat = _int(m.get("transaction_sold_count"))
        satis.append(sat)
        if k is None:
            continue
        yas.append((simdi - k) / AY_SN)
        if simdi - k < GENC_GUN * 86400:
            genc.append(sat)
    genc100 = [x for x in genc if x is not None and x >= 100]
    ilan_yas = [(simdi - t) / AY_SN for t in (_int(L.get("original_creation_timestamp")) for L in dl) if t]
    usd, usd_disi, fiyat_yok = [], 0, 0
    for L in dl:
        f, c = D.fiyat(L.get("price") or {})
        if f == "" or not c:
            fiyat_yok += 1
        elif c == "USD":
            usd.append(f)
        else:
            usd_disi += 1
    ilk_dl_l = [L for L in ilk100 if L.get("listing_type") == "download"]
    ilk_dl = len(ilk_dl_l)
    ilk_say = sorted(Counter(str(L.get("shop_id")) for L in ilk_dl_l).values(), reverse=True)
    return {
        "ilk100_ilan": len(ilk100), "ilk100_download_n": ilk_dl, "ilk100_download_oran": oran(ilk_dl, len(ilk100)),
        "download_n": n, "az_veri": "evet" if n < AZ_VERI_N else "", "farkli_magaza": len(say),
        "en_buyuk_magaza_payi": oran(sirali[0], n) if sirali else "", "ilk3_magaza_payi": oran(sum(sirali[:3]), n) if sirali else "",
        "ilk100_farkli_magaza": len(ilk_say), "ilk100_en_buyuk_magaza_payi": oran(ilk_say[0], ilk_dl) if ilk_say else "",
        "magaza_bilinen_n": len(bilinen), "magaza_yasi_medyan_ay": medyan(yas, 1),
        "genc_magaza_n": len(genc), "genc_magaza_payi": oran(len(genc), len(yas)),
        "genc_satis100_n": len(genc100), "genc_satis100_satis_medyan": medyan(genc100, 1),
        "magaza_satis_medyan": medyan(satis, 1), "ilan_yasi_medyan_ay": medyan(ilan_yas, 1), "ilan_yasi_bilinen_n": len(ilan_yas),
        "favori_medyan": medyan([_int(L.get("num_favorers")) for L in dl], 1),
        "fiyat_medyan_usd": medyan(usd), "fiyat_usd_n": len(usd), "fiyat_usd_disi_n": usd_disi, "fiyat_yok_n": fiyat_yok,
    }


# ------------------------------------------------------------------ durum
class Depo:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        p = self.out / "terim_durum.json"
        self.d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"kosu": 0, "istek_toplam": 0, "kosular": []}
        self.tarama = {r["terim"]: r for r in D.oku_csv(self.out / "TERIM_TARAMA.csv")}
        self.ilan = D.oku_csv(self.out / "TERIM_ILAN.csv")
        self.magaza = {r["shop_id"]: r for r in D.oku_csv(self.out / "TERIM_MAGAZA.csv")}

    def bitti(self, terim):
        return (self.tarama.get(terim) or {}).get("durum") in ("tamam", "hata")

    def kaydet(self):
        """TERIM_TARAMA ('tamam' isareti) EN SON: arada kesilirse terim tamam gorunmez, sonraki kosu yeniden okur."""
        D.yaz_csv(self.out / "TERIM_ILAN.csv", ILAN_ALAN, self.ilan)
        D.yaz_csv(self.out / "TERIM_MAGAZA.csv", MAGAZA_ALAN, self.magaza.values())
        D.yaz_csv(self.out / "TERIM_TARAMA.csv", TARAMA_ALAN, self.tarama.values())
        # durum (yeniden_bekleyen, sayac) EN SON: TARAMA'dan once kesilirse terim yeniden olculur (zararsiz), tersi olmaz
        self.d["son_guncelleme_utc"] = utc()
        tmp = self.out / "terim_durum.json.tmp"
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.out / "terim_durum.json")


def taze_magaza(dp, sid, simdi):
    m = dp.magaza.get(sid)
    return bool(m) and (_int(m.get("okuma_ts")) or 0) >= simdi - MAGAZA_TAZE_GUN * 86400


# ------------------------------------------------------------------ terim
def kota_kapisi(api, alt):
    if api.remaining is None:
        raise D.KotaDur()
    if int(api.remaining) < alt:
        raise D.KotaDur()


def tekil_ekle(tum, gorulen, res, sayfa):
    """Sayfalar arasi tekillestirme (score sirasi kayabilir: ayni ilan iki sayfada)."""
    for i, L in enumerate(res):
        lid = str(L.get("listing_id"))
        if lid in gorulen:
            continue
        gorulen.add(lid)
        tum.append((sayfa, i + 1, L))


def terim_tara(dp, ok, terim, simdi):
    """-> (tarama satiri, ilan satirlari, yeni magazalar). Ag hatasi -> TerimHata; kota / sure / yol -> istisna yukari."""
    api = ok.api
    c0 = api.calls
    n = {"cagri": 0}           # mantiksal cagri (butce); api.calls 5xx / kisa 429 yeniden denemelerini de sayar

    def al(path, params):
        if n["cagri"] >= TERIM_ISTEK_AZAMI:
            raise SystemExit(f"HATA: terim istek butcesi ({TERIM_ISTEK_AZAMI}) asilacakti")
        n["cagri"] += 1
        return ok.get(path, params, hata_bos=True)

    sayfalar, gorulen, tum = [], set(), []
    j1 = al("/listings/active", {"keywords": terim, "sort_on": "score", "limit": SAYFA_N, "offset": 0})
    if j1 is None:
        raise TerimHata()
    ilk100 = j1.get("results") or []
    sayfalar.append(ilk100)

    tekil_ekle(tum, gorulen, ilk100, 1)

    def dl_say():
        return sum(1 for _, _, L in tum if L.get("listing_type") == "download")

    son = ilk100
    for k in range(EK_SAYFA):
        if dl_say() >= DL_MIN or len(son) < SAYFA_N:
            break
        j = al("/listings/active", {"keywords": terim, "sort_on": "score", "limit": SAYFA_N, "offset": SAYFA_N * (k + 1)})
        if j is None:
            raise TerimHata()
        son = j.get("results") or []
        sayfalar.append(son)
        tekil_ekle(tum, gorulen, son, k + 2)
    dl = [L for _, _, L in tum if L.get("listing_type") == "download"]
    # magaza: tek temsilci ilan, okunmamis / bayat magazalar, 100'luk parti; terim butcesi asilmaz
    temsil = {}
    for L in dl:
        sid = str(L.get("shop_id"))
        if sid not in temsil and not taze_magaza(dp, sid, simdi):
            temsil[sid] = str(L.get("listing_id"))
    ids = list(temsil.values())
    yeni = {}
    for i in range(0, len(ids), BATCH_N):
        if n["cagri"] >= TERIM_ISTEK_AZAMI:     # butce bitti: kalan magazalar bilinmeyen sayilir (magaza_bilinen_n)
            break
        jb = al("/listings/batch", {"listing_ids": ",".join(ids[i:i + BATCH_N]), "includes": "Shop"})
        if jb is None:
            raise TerimHata()
        for x in jb.get("results") or []:
            sh = x.get("shop") or {}
            if sh.get("shop_id"):
                r = {a: sh.get(a, "") for a in MAGAZA_ALAN}
                r["shop_id"] = str(sh["shop_id"])
                r["okuma_ts"] = simdi
                yeni[r["shop_id"]] = r
    istek = api.calls - c0
    magaza = dict(dp.magaza)
    magaza.update(yeni)
    satir = {"terim": terim, "durum": "tamam", "toplam_sonuc_api": j1.get("count", ""), "sayfa": len(sayfalar),
             "istek": istek, "cagri": n["cagri"], "olcum_utc": utc(simdi)}
    satir.update(metrikler(ilk100, dl, magaza, simdi))
    ilanlar = []
    for sayfa, sira, L in tum:
        f, c = D.fiyat(L.get("price") or {})
        ilanlar.append({"terim": terim, "sayfa": sayfa, "sira": sira, "listing_id": L.get("listing_id"),
                        "shop_id": L.get("shop_id"), "listing_type": L.get("listing_type", ""),
                        "is_personalizable": L.get("is_personalizable", ""), "title": L.get("title", ""), "price": f,
                        "currency": c, "num_favorers": L.get("num_favorers", ""),
                        "original_creation_timestamp": L.get("original_creation_timestamp", ""),
                        "created_timestamp": L.get("created_timestamp", ""), "taxonomy_id": L.get("taxonomy_id", ""),
                        "url": L.get("url", "")})
    return satir, ilanlar, yeni


def calis(out, dk, api, terimler, yeniden=False, yol_ver_fn=None, simdi_fn=time.time, kota_alt=KOTA_ALT):
    dk = max(0.0, min(float(dk), D.DK_AZAMI))
    kota_alt = max(int(kota_alt), E.KOTA_SINIRI)
    try:
        dp = Depo(out)
    except Exception as e:  # noqa: BLE001 icerik loga girmez
        log(f"HATA: durum okunamadi ({type(e).__name__})")
        return 1
    dp.d["kosu"] = dp.d.get("kosu", 0) + 1
    ok = D.Okuyucu(api, dk, yol_ver_fn)
    ok.limit_gun = None          # %20 payi yok; bu betigin kapisi kota_alt
    kayit = {"kosu": dp.d["kosu"], "bas_utc": utc(), "istek": 0, "kota_bas": None, "kota_son": None, "terim_tamam": 0}
    dp.d.setdefault("kosular", []).append(kayit)
    yb = set(dp.d.get("yeniden_bekleyen") or [])   # yarida kalan --yeniden kosusu sonraki kosuda da yeniden olcer
    th0 = dp.d.setdefault("terim_hata", {})
    if yeniden:
        yb |= set(terimler)
        for t in terimler:            # --yeniden: kapanmis hatali terime de tam deneme hakki
            th0.pop(t, None)
    dp.d["yeniden_bekleyen"] = sorted(yb)
    th = dp.d.setdefault("terim_hata", {})        # terim -> okunamadigi kosu sayisi
    sira = [t for t in terimler if t in yb or not dp.bitti(t)]
    sira.sort(key=lambda t: int(th.get(t, 0)))      # onceki kosuda okunamayan terim sona (kararli siralama)
    istek_bas = int(dp.d.get("istek_toplam") or 0)
    log(f"TERIM TARAMA kosu {dp.d['kosu']}: secili terim {len(terimler)} | bekleyen {len(sira)}")
    kod, hata_ardisik, hata_toplam, tamam = 0, 0, 0, 0
    c_bas = api.calls
    t0 = time.monotonic()
    try:
        ok.get("/openapi-ping")
        kayit["kota_bas"] = api.remaining
        for i, t in enumerate(sira):
            ok.kontrol()
            kota_kapisi(api, kota_alt)
            dp.d["kalan_terim"] = t
            simdi = int(simdi_fn())
            try:
                satir, ilanlar, yeni = terim_tara(dp, ok, t, simdi)
            except TerimHata:
                hata_ardisik += 1
                hata_toplam += 1
                th[t] = int(th.get(t, 0)) + 1
                if th[t] >= TERIM_HATA_DENEME:      # kalici hata: kapat (kosular takilmasin); --yeniden ile yeniden olculur
                    if (dp.tarama.get(t) or {}).get("durum") == "tamam":   # onceki gecerli olcum korunur (ham satirlarla tutarli)
                        dp.d.setdefault("yeniden_olculemedi", [])
                        if t not in dp.d["yeniden_olculemedi"]:
                            dp.d["yeniden_olculemedi"].append(t)
                    else:
                        dp.tarama[t] = {"terim": t, "durum": "hata", "olcum_utc": utc(simdi)}
                    yb.discard(t)
                    dp.d["yeniden_bekleyen"] = sorted(yb)
                dp.d["istek_toplam"] = istek_bas + (api.calls - c_bas)
                dp.kaydet()
                if hata_ardisik >= ARDISIK_HATA_AZAMI:
                    raise SystemExit(f"HATA: ardisik {hata_ardisik} terim okunamadi")
                continue
            hata_ardisik = 0
            # ayni adimda (arada istek yok): satir + ilanlar + magazalar + sayac
            dp.tarama[t] = satir
            dp.ilan = [r for r in dp.ilan if r["terim"] != t] + ilanlar
            dp.magaza.update(yeni)
            dp.d["istek_toplam"] = istek_bas + (api.calls - c_bas)
            yb.discard(t)
            dp.d["yeniden_bekleyen"] = sorted(yb)
            th.pop(t, None)
            tamam += 1
            kayit["terim_tamam"] = tamam
            kayit["istek"] = api.calls - c_bas
            kayit["kota_son"] = api.remaining
            dp.kaydet()
            if (i + 1) % 10 == 0 or i + 1 == len(sira):
                gec = time.monotonic() - t0
                kal = gec / (i + 1) * (len(sira) - i - 1)
                log(f"terim {i + 1}/{len(sira)} (%{100 * (i + 1) // len(sira)}) | gecen {gec / 60:.1f} dk | kalan ~{kal / 60:.1f} dk"
                    f" | istek {api.calls - c_bas} | kota {api.remaining}")
    except D.KotaDur:
        kod = 3
        log(f"DUR: kota (kalan {api.remaining}, alt sinir {kota_alt}); kaldigi terimden surer")
    except D.YolVer:
        kod = 4
        log("YOL VERILDI: baska Etsy kosusu aktif; durum kaydedildi")
    except D.SureDoldu:
        log("SURE DOLDU: durum kaydedildi")
    except SystemExit as e:
        kod = 1
        log(f"HATA: {D.kisa_hata(e)}")
    except Exception as e:  # noqa: BLE001
        kod = 1
        log(f"HATA: {type(e).__name__}")
    # sayac = bu kosunun TUM istekleri (ping, hatali ve yarim kalan terim dahil)
    dp.d["istek_toplam"] = istek_bas + (api.calls - c_bas)
    kayit["istek"] = api.calls - c_bas
    kayit["kota_son"] = api.remaining
    kayit["kod"] = kod
    kayit["bit_utc"] = utc()
    kalan = [t for t in terimler if (t in yb) or not dp.bitti(t)]
    dp.d["kalan_terim"] = kalan[0] if kalan else None
    dp.d["kalan_terim_n"] = len(kalan)
    dp.d["durum"] = "bitti" if not kalan else "devam"
    dp.d["hata_terim_n"] = sum(1 for t in terimler if (dp.tarama.get(t) or {}).get("durum") == "hata")
    try:
        dp.kaydet()
    except Exception as e:  # noqa: BLE001
        log(f"HATA (kaydet): {type(e).__name__}")
        return 1
    log(f"KOSU {dp.d['kosu']}: durum {dp.d['durum']} | terim tamam {tamam} | terim hata {hata_toplam} (kapanan {dp.d['hata_terim_n']})"
        f" | kalan terim {len(kalan)}"
        f" | istek {api.calls - c_bas} (toplam {dp.d['istek_toplam']}) | kota {kayit['kota_bas']} -> {api.remaining}")
    return kod


def main():
    sys.stdout = D.KimlikSuz(sys.stdout)
    sys.stderr = D.KimlikSuz(sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dk", type=float, default=30)
    ap.add_argument("--liste", default=str(VARSAYILAN_LISTE))
    ap.add_argument("--yalniz", default="", help="';' ile ayrilmis terimler (bos = listenin tamami)")
    ap.add_argument("--yeniden", action="store_true", help="secili terimler bitmis olsa da yeniden olculur")
    ap.add_argument("--kota-alt", type=int, default=KOTA_ALT, help=f"kalan < bu ise DUR (varsayilan {KOTA_ALT} = KOTA_SINIRI)")
    a = ap.parse_args()
    try:
        terimler = secim_coz(terimler_oku(a.liste), a.yalniz)
    except SystemExit as e:
        log(str(e))
        return 1
    st = E.APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    api = D.SaltOkur(st)
    yv = D.yol_ver_gh if os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_RUN_ID") else None
    return calis(a.out, a.dk, api, terimler, a.yeniden, yv, kota_alt=a.kota_alt)


if __name__ == "__main__":
    sys.exit(main())
