#!/usr/bin/env python3
"""ornament_taslak sahte testi (ag yok, token yok). Bagimsiz kod incelemesi (6 Kas gece) bulgulari icin bilinen PASS + bilinen FAIL:
geri okuma farki -> DUR (sonraki cift acilmaz), active -> acil inactive + kod 2, PATCH hatasinda da kod 2, createDraftListing
belirsiz / 5xx -> DURUM "BELIRSIZ" + DUR, BELIRSIZ yeniden kosu (bulursa devam, bulamazsa DUR), var olan ilan draft degil / baslik
uyusmuyor -> dokunmadan DUR, ag oncesi DUR-ON -> sonraki cift, parti siniri, ilan basi kota kapisi, onceki videoda ikinci video yok,
POST listings yalniz taslak_olustur, baglanti hatasi -> BELIRSIZ.
URUN_AYAR (9 Kas): testler test_urun_ayar.sahte_ortam() ile SAHTE kilitli ayar + SAHTE onay + SAHTE metin CSV uzerinde kosar (gercek ayar
kilitli degil ve gercek metin "free shipping" tasir: ayar kapisi DUR verir; o yol test_urun_ayar'da)."""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ornament_taslak as T  # noqa: E402
import test_urun_ayar as UT  # noqa: E402

UT.sahte_ortam()

T.time.sleep = lambda s: None
SHOP = "39729443"
CIFTLER = ["ARIES_ARIES", "CANCER_LIBRA", "LEO_LEO"]


def medya_kur(kok, ciftler=CIFTLER, eksik=()):
    for c in ciftler:
        d = pathlib.Path(kok) / c; d.mkdir(parents=True, exist_ok=True)
        for g in T.GALERI:
            if c in eksik and g == "05_SUREC":
                continue
            (d / f"{c}_{g}.jpg").write_bytes(b"jpg")
        (d / f"{c}_VIDEO.mp4").write_bytes(b"mp4")


class Sahte(T.Kuru):
    """Kuru taklidi + senaryo kancalari."""
    olustur_kod = None          # ("BELIRSIZ" | int) -> taslak_olustur bu kodu dondurur
    active_adim = None          # bu yolun POST'undan sonra listing active olur
    patch_hata = False
    alt_boz = False
    shop_listeler = ()          # GET /shops/{s}/listings sonucu (ayni_baslik)
    var_olan = None             # GET /listings/{id} (var olan ilan) sonucu
    kalan = None

    def __init__(self, shop):
        super().__init__(shop)
        self.olusturma = 0
        self.patchler = []
        if self.kalan is not None:
            self.remaining = str(self.kalan)

    def taslak_olustur(self, shop, body):
        self.olusturma += 1
        if self.olustur_kod is not None:
            self._olustur = True
            try:
                self._izin("POST", f"/shops/{shop}/listings")
            finally:
                self._olustur = False
            return self.olustur_kod, None, "sahte"
        return super().taslak_olustur(shop, body)

    def _sim(self, method, path, params, data, ok404, js):
        s, lid = self.shop, self.lid
        if method == "PATCH":
            self.patchler.append(path)
            if self.patch_hata:
                raise SystemExit(f"HATA: PATCH {path} -> 400: sahte")
        if method == "GET" and path == f"/shops/{s}/listings":
            st = (params or {}).get("state")
            r = [x for x in self.shop_listeler if x.get("state") == st]
            return dict(results=r, count=len(r))
        if method == "GET" and self.var_olan is not None and self.L is None and path == f"/listings/{lid}":
            return self.var_olan
        if method == "GET" and self.alt_boz and path == f"/listings/{lid}/images":
            return dict(results=[dict(x, alt_text=("BOZUK" if x["rank"] == 3 else x["alt_text"])) for x in self.ims])
        r = super()._sim(method, path, params, data, ok404, js)
        if self.active_adim and method != "GET" and path.endswith(self.active_adim):
            self.L["state"] = "active"
        return r


def kos(sinif, ciftler, durum=None, eksik=(), **kw):
    tmp = tempfile.mkdtemp()
    out = pathlib.Path(tmp) / "out"; out.mkdir()
    img = pathlib.Path(tmp) / "img"; medya_kur(img, eksik=eksik)
    os.environ["IMG_ROOT"] = str(img)
    if durum is not None:
        json.dump(durum, open(out / "DURUM.json", "w"))
    api = sinif(SHOP)
    hata = None
    try:
        T.yaz_dongu(api, SHOP, out, ciftler, **kw)
    except BaseException as e:  # noqa: BLE001 (TypeError vb. de o testin FAIL'i olur, paket dusmez)
        hata = e if isinstance(e, SystemExit) else SystemExit(f"BEKLENMEYEN {type(e).__name__}: {e}")
    D = json.load(open(out / "DURUM.json")) if (out / "DURUM.json").exists() else {}
    return api, hata, D, out


def baslik(c):
    return T.metin_satiri(c)["baslik"]


def testler():
    s = []
    # 1 bilinen PASS: iki cift, 13/13, iki tamam
    api, h, D, _ = kos(Sahte, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("PASS: 2 cift tamam, hata yok", h is None and D.get("tamam") == ["ARIES_ARIES", "CANCER_LIBRA"] and api.olusturma == 2))

    # 2 geri okuma farki -> DUR, 2. cift acilmaz
    class AltBoz(Sahte):
        alt_boz = True
    api, h, D, _ = kos(AltBoz, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: alt metin farki DUR, sonraki cift acilmadi", h is not None and "alt metinler" in str(h.code) and api.olusturma == 1
              and not D.get("tamam")))

    # 3 active -> acil inactive, kod 2, sonraki cift yok
    class Act(Sahte):
        active_adim = "/variation-images"
    api, h, D, _ = kos(Act, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: active -> PATCH inactive + kod 2", h is not None and h.code == 2 and len(api.patchler) == 1
              and api.L["state"] == "inactive" and api.olusturma == 1))

    # 4 PATCH hatasi -> yine kod 2, sonraki cift yok
    class ActPF(Act):
        patch_hata = True
    api, h, D, _ = kos(ActPF, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: PATCH hatasinda da kod 2, 2. ilan acilmadi", h is not None and h.code == 2 and api.olusturma == 1))

    # 5 belirsiz olusturma -> DURUM BELIRSIZ + DUR
    class Bel(Sahte):
        olustur_kod = "BELIRSIZ"
    api, h, D, _ = kos(Bel, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: belirsiz olusturma -> BELIRSIZ + DUR", h is not None and D["ciftler"].get("ARIES_ARIES") == "BELIRSIZ"
              and api.olusturma == 1))

    # 6 5xx -> BELIRSIZ; 4xx -> BELIRSIZ yok; ikisi de DUR
    class K500(Sahte):
        olustur_kod = 503
    api, h, D, _ = kos(K500, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: 503 -> BELIRSIZ + DUR", h is not None and D["ciftler"].get("ARIES_ARIES") == "BELIRSIZ" and api.olusturma == 1))

    class K400(Sahte):
        olustur_kod = 400
    api, h, D, _ = kos(K400, ["ARIES_ARIES", "CANCER_LIBRA"])
    s.append(("FAIL: 400 -> DUR, BELIRSIZ yazilmaz", h is not None and "ARIES_ARIES" not in D.get("ciftler", {}) and api.olusturma == 1))

    # 7 BELIRSIZ yeniden kosu: ilan bulunursa ona devam (yeni ilan yok)
    class BelBul(Sahte):
        shop_listeler = [dict(listing_id=9000000001, state="draft", title=baslik("ARIES_ARIES"))]
        var_olan = dict(listing_id=9000000001, state="draft", title=baslik("ARIES_ARIES"), taxonomy_id=T.ayar()["ilan"]["taxonomy_id"])
    api, h, D, _ = kos(BelBul, ["ARIES_ARIES"], durum={"ciftler": {"ARIES_ARIES": "BELIRSIZ"}})
    s.append(("BELIRSIZ + bulunan ilan: yeni ilan acilmadi, kimlik DURUM'a", api.olusturma == 0 and D["ciftler"]["ARIES_ARIES"] == 9000000001))

    # 8 BELIRSIZ yeniden kosu: bulunamazsa DUR
    api, h, D, _ = kos(Sahte, ["ARIES_ARIES"], durum={"ciftler": {"ARIES_ARIES": "BELIRSIZ"}})
    s.append(("FAIL: BELIRSIZ bulunamadi -> DUR, ilan acilmadi", h is not None and "BELIRSIZ" in str(h.code) and api.olusturma == 0))

    # 9 var olan ilan active -> dokunmadan DUR (PATCH yok)
    class VarAct(Sahte):
        var_olan = dict(listing_id=777, state="active", title=baslik("ARIES_ARIES"), taxonomy_id=T.ayar()["ilan"]["taxonomy_id"])
    api, h, D, _ = kos(VarAct, ["ARIES_ARIES"], durum={"ciftler": {"ARIES_ARIES": 777}})
    s.append(("FAIL: var olan active -> DUR, PATCH yok", h is not None and "draft degil" in str(h.code) and api.patchler == []
              and api.olusturma == 0))

    # 10 var olan baslik uyusmuyor -> DUR
    class VarBas(Sahte):
        var_olan = dict(listing_id=778, state="draft", title="Zodiac Mug", taxonomy_id=T.ayar()["ilan"]["taxonomy_id"])
    api, h, D, _ = kos(VarBas, ["ARIES_ARIES"], durum={"ciftler": {"ARIES_ARIES": 778}})
    s.append(("FAIL: var olan baslik farkli -> DUR", h is not None and "uyusmuyor" in str(h.code) and len(api.kayit) <= 3))

    # 11 ag oncesi DUR-ON (eksik medya) -> o cift atlanir, sonraki yazilir
    api, h, D, _ = kos(Sahte, ["ARIES_ARIES", "CANCER_LIBRA"], eksik=("ARIES_ARIES",))
    s.append(("DUR-ON: eksik medyali cift atlandi, sonraki tamam", h is None and D.get("tamam") == ["CANCER_LIBRA"] and api.olusturma == 1))

    # 12 parti siniri
    api, h, D, _ = kos(Sahte, ["ARIES_ARIES", "CANCER_LIBRA", "LEO_LEO"], parti_max=2)
    s.append(("Parti siniri 2: 3. cift bu kosuda yok", h is None and D.get("tamam") == ["ARIES_ARIES", "CANCER_LIBRA"] and api.olusturma == 2))

    # 13 ilan basi kota kapisi
    class Az(Sahte):
        kalan = 50
    api, h, D, _ = kos(Az, ["ARIES_ARIES"])
    s.append(("FAIL: kota 50 < 70 -> ilan acilmadan DUR", h is not None and "kota" in str(h.code) and api.olusturma == 0))

    # 14 onceki kosuda video yuklendi, gorunmuyor -> ikinci video yok, DUR
    class VidYok(Sahte):
        var_olan = dict(listing_id=779, state="draft", title=baslik("ARIES_ARIES"), taxonomy_id=T.ayar()["ilan"]["taxonomy_id"])

        def _sim(self, method, path, params, data, ok404, js):
            if self.L is None and method == "GET" and path == "/listings/779":
                self.L = dict(self.var_olan, who_made="i_did")
            return super()._sim(method, path, params, data, ok404, js)
    api, h, D, _ = kos(VidYok, ["ARIES_ARIES"], durum={"ciftler": {"ARIES_ARIES": 779}, "video": {"ARIES_ARIES": 779}})
    s.append(("FAIL: onceki video gorunmuyor -> ikinci video yuklenmedi", h is not None and "video" in str(h.code)
              and not any(k["url"].endswith("/videos") and k["yazma"] for k in api.kayit)))

    # 15 POST listings genel yoldan yasak; taslak_olustur baglanti hatasinda BELIRSIZ
    k = object.__new__(T.Kilitli)
    k.lid = None
    k.A = T.ayar(); k.cift = "ARIES_ARIES"
    try:
        k._izin("POST", f"/shops/{SHOP}/listings"); ok = False
    except SystemExit as e:
        ok = "YASAK" in str(e.code)
    s.append(("POST /listings yalniz taslak_olustur icinde", ok and k._olustur is False))

    class Hata:
        @staticmethod
        def post(*a, **kw):
            raise T.requests.ConnectionError("sahte kopma")
    k.remaining, k._kalan_yaz, k._istek_oncesi, k._bekle, k._headers = None, lambda *a: None, lambda: None, lambda: 1, lambda: {}
    gercek = T.requests.post
    T.requests.post = Hata.post
    try:
        row = T.metin_satiri("ARIES_ARIES")
        kod, js, _ = k.taslak_olustur(SHOP, T.taslak_govde(k.A, row["baslik"], row["aciklama"],
                                                           [t.strip() for t in row["etiketler"].split(",")]))
    finally:
        T.requests.post = gercek
    s.append(("Baglanti hatasi -> BELIRSIZ (tek gonderim)", kod == "BELIRSIZ" and js is None))
    # 16 sure siniri (KILIT_T0'dan 61 dk sonra yeni cift yok)
    os.environ["KILIT_T0"] = str(T.time.time() - 61 * 60)
    try:
        api, h, D, _ = kos(Sahte, ["ARIES_ARIES"])
    finally:
        os.environ.pop("KILIT_T0", None)
    s.append(("Sure siniri: 61 dk sonra yeni cift acilmadi", h is None and api.olusturma == 0 and not D.get("tamam")))

    # 17 ayni baslikli 2 ilan -> DUR, PATCH yok
    class Iki(Sahte):
        shop_listeler = [dict(listing_id=1, state="draft", title=baslik("ARIES_ARIES")),
                         dict(listing_id=2, state="inactive", title=baslik("ARIES_ARIES"))]
    api, h, D, _ = kos(Iki, ["ARIES_ARIES"])
    s.append(("FAIL: ayni baslikli 2 ilan -> DUR", h is not None and "ayni baslikli 2" in str(h.code) and api.olusturma == 0 and api.patchler == []))

    # 18 yeni cift icin active ilan bulunur -> dokunmadan DUR
    class ActBul(Sahte):
        shop_listeler = [dict(listing_id=5, state="active", title=baslik("ARIES_ARIES"))]
        var_olan = dict(listing_id=5, state="active", title=baslik("ARIES_ARIES"), taxonomy_id=T.ayar()["ilan"]["taxonomy_id"])
    api, h, D, _ = kos(ActBul, ["ARIES_ARIES"])
    s.append(("FAIL: yayindaki ayni baslik -> DUR, PATCH yok, ilan acilmadi", h is not None and "draft degil" in str(h.code)
              and api.patchler == [] and api.olusturma == 0))

    # 19 POST sirasinda iptal (KeyboardInterrupt) -> DURUM'da BELIRSIZ kalir
    class Iptal(Sahte):
        def taslak_olustur(self, shop, body):
            self.olusturma += 1
            raise KeyboardInterrupt
    api, h, D, _ = kos(Iptal, ["ARIES_ARIES"])
    s.append(("Iptal: POST oncesi BELIRSIZ isareti kalir", D.get("ciftler", {}).get("ARIES_ARIES") == "BELIRSIZ"))

    # 20 video yuklemesi koparsa isaret yine yazili (ikinci video yok)
    class VidKop(Sahte):
        def post_file(self, path, files, data=None):
            if path.endswith("/videos"):
                raise SystemExit("HATA: POST(file) videos -> 503")
            return super().post_file(path, files, data)
    api, h, D, _ = kos(VidKop, ["ARIES_ARIES"])
    s.append(("Video 503: video isareti yuklemeden once yazili", h is not None and D.get("video", {}).get("ARIES_ARIES") == 9000000001))

    # 21 Kilitli.post_file tekrar=1 (5xx'te yeniden gondermez)
    yakala = {}
    gercek_pf = T.Etsy.post_file
    T.Etsy.post_file = lambda self, path, files, data=None, tekrar=3: yakala.setdefault("tekrar", tekrar) and {}
    try:
        k2 = object.__new__(T.Kilitli); k2.lid = 42; k2.remaining = None; k2.A = T.ayar()
        k2.post_file(f"/shops/{SHOP}/listings/42/images", files={}, data={"rank": 1})   # rank: ayar kapisi (galeri 1-N)
    finally:
        T.Etsy.post_file = gercek_pf
    s.append(("Kilitli.post_file tekrar=1", yakala.get("tekrar") == 1))
    return s


def main():
    s = testler()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"ornament_taslak testleri TOPLAM: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
