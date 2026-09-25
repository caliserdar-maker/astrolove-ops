#!/usr/bin/env python3
"""CANLI Prodigi guvenli test (Serdar onayi 25 Eyl 2026): TEK sahte siparis -> oku -> HEMEN iptal -> dogrula.

On kosul: Prodigi Preferences > Order edit window = "Pause indefinitely, until manually released" (Serdar ekran
goruntusuyle dogruladi, 25 Eyl 20:09; API'de hesap ayari ucu yok - hesap_oku kosusu 36165026408, 0/13).
Siparis: Aries+Leo, Deep Black, 8x10, isimler EMILY/JAMES + mesaj (sahte, e2e ile ayni), kisiye ozel kartpostal (branding.postcard.url).
Alici: Serdar'in kendi adresi, Drive TEMP/PRODIGI_TEST_ADRES.json ({name, line1, line2?, postalOrZipCode,
townOrCity, stateOrCounty?, countryCode}). Dosya yoksa SIPARIS VERILMEZ. Adres loga YAZILMAZ.
Adimlar: 1 adres  2 kart (uretim girdisi) + gercek baski uretec (siparis-baski-v1)  3 kartpostal_uret
4 gecici Drive linkleri  5 POST /orders (merchantReference guvenli-test-<damga>, etsy- DEGIL)  6 durum/issues/branding
7 iptal + "Cancelled" dogrulamasi  8 ucret (charges)  9 izinler kapanir, gecici dosyalar silinir.
Cikis: 0 = iptal dogrulandi | 2 = on kosul/uretim (siparis YOK) | 3 = IPTAL BASARISIZ (Serdar'a e-posta).
Loga: yalniz kodlar/durumlar; isim, adres, link yazilmaz.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy")); sys.path.insert(0, str(HERE.parent / "pinterest"))

ADRES_REMOTE = "gdrive:ASTROLOVE/TEMP/PRODIGI_TEST_ADRES.json"
KOK = "gdrive:ASTROLOVE/TEMP/SIPARIS_TEST"
DAMGA = time.strftime("%m%d%H%M", time.gmtime())
RID = f"95{DAMGA}"                                    # sahte receipt (gercek Etsy receipt 4x/41x ile carpismaz)
REF = f"guvenli-test-{DAMGA}"
T0 = time.time()
W = ROOT / "_guvenli"; W.mkdir(exist_ok=True)
RAPOR = {"ref": REF}


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def rc(*a, **kw):
    return subprocess.run(list(a), capture_output=True, text=True, **kw)


def bitir(kod, neden):
    RAPOR.update(cikis=kod, neden=neden, sure_sn=round(time.time() - T0))
    (W / "GUVENLI_TEST_RAPOR.json").write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False))
    rc("rclone", "copyto", str(W / "GUVENLI_TEST_RAPOR.json"), f"{KOK}/_GUVENLI_{DAMGA}/GUVENLI_TEST_RAPOR.json")
    print("SONUC " + json.dumps({k: v for k, v in RAPOR.items() if k != "adres"}, ensure_ascii=False), flush=True)
    sys.exit(kod)


def main():
    import order_router as R
    import siparis_onay as O
    import kisisel_siparis as K
    from pod_sku import parse_sku
    O.DRIVE_KOK = KOK

    # 1) adres (Drive; loga yazilmaz)
    r = rc("rclone", "cat", ADRES_REMOTE)
    try:
        adres = json.loads(r.stdout) if r.returncode == 0 else {}
    except ValueError:
        adres = {}
    eksik = [k for k in ("name", "line1", "postalOrZipCode", "townOrCity", "countryCode") if not adres.get(k)]
    if eksik:
        bitir(2, f"ADRES YOK/EKSIK ({ADRES_REMOTE}: {','.join(eksik)}) - siparis VERILMEDI")
    log(f"adres okundu (ulke {adres['countryCode']})")

    # 2) sahte kisisel siparis karti + gercek baski uretec
    # kart girdisi ulkesi US: isim buyuk harf kurali EMILY (TR kurali EMILY'yi noktali I ile basardi); alici adresi ayri
    rec = {"receipt_id": int(RID), "country_iso": "US", "is_shipped": False,
           "transactions": [{"transaction_id": int(RID) + 1, "sku": "POD-ARI_LEO-DB-8x10", "quantity": 1,
                             "price": {"amount": 3499, "divisor": 100}, "title": "Aries Leo",
                             "variations": [{"formatted_name": "Name under Aries", "formatted_value": "Emily"},
                                            {"formatted_name": "Name under Leo", "formatted_value": "James"},
                                            {"formatted_name": "Your message", "formatted_value": "It Began With a Kiss in the Rain"}]}]}
    rc("rclone", "copyto", "gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md", str(W / "MM.md"))
    kis = K.cevaplar(rec, parse_sku)
    md, _ = K.kart(rec, kis, K.sablon_oku(str(W / "MM.md")), "")
    (W / f"{RID}.md").write_text(md, encoding="utf-8")
    rc("rclone", "copyto", str(W / f"{RID}.md"), f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{RID}.md", check=True)
    sb = W / "sb"; sb.mkdir(exist_ok=True)
    rc("git", "fetch", "-q", "--depth", "1", "origin", "siparis-baski-v1", check=True)
    arc = subprocess.run(["git", "archive", "FETCH_HEAD", "scripts/medya_v1"], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(sb)], input=arc, check=True)
    log("baski uretec basliyor (gercek, siparis-baski-v1)")
    with (W / "uretim.log").open("w") as fh:
        p = subprocess.run([sys.executable, str(sb / "scripts/medya_v1/siparis_dosyasi.py"), "--kart", f"{RID}.md"],
                           stdout=fh, stderr=subprocess.STDOUT, timeout=1800, cwd=ROOT)
    rc("rclone", "move", f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{RID}", f"{KOK}/{RID}")
    rc("rclone", "copyto", str(W / "uretim.log"), f"{KOK}/{RID}/URETIM.log")
    kapi = ROOT / "_siparis" / RID / "KAPI_RAPORU.json"
    kr = json.loads(kapi.read_text()) if kapi.exists() else {}
    RAPOR["uretim"] = {"cikis": p.returncode, "durum": kr.get("durum"), "kapilar_gecti": kr.get("kapilar_gecti")}
    log(f"uretim: cikis {p.returncode} durum {kr.get('durum')} kapilar {kr.get('kapilar_gecti')}")
    if kr.get("durum") not in ("URETILDI", "BEKLIYOR") or kr.get("kapilar_gecti") is False \
            or rc("rclone", "lsf", f"{KOK}/{RID}/BASKI_8x10.jpg").returncode:
        bitir(2, "baski dosyasi uretilemedi - siparis VERILMEDI")

    # 3) kisiye ozel kartpostal
    font = W / "Cinzel.ttf"
    rc("git", "fetch", "-q", "--depth", "1", "origin", "kisisel-v1", check=True)
    font.write_bytes(subprocess.run(["git", "show", "FETCH_HEAD:assets/fonts/Cinzel.ttf"], capture_output=True, check=True).stdout)
    kq = O.kartpostal_hazirla(RID, md, W / "kart", font, O._rclone_indir)
    RAPOR["kartpostal_qc"] = {"PASS": kq.get("PASS"), "neden": kq.get("neden"), "kapilar": kq.get("kapilar")}
    log(f"kartpostal QC {'PASS' if kq.get('PASS') else 'FAIL ' + str(kq.get('neden'))}")
    if not kq.get("PASS"):
        bitir(2, "kartpostal uretilemedi - siparis VERILMEDI")
    kart_remote = f"{KOK}/{RID}/{O.KART_AD}"
    rc("rclone", "copyto", str(W / "kart" / RID / O.KART_AD), kart_remote, check=True)

    # 4-5) gecici linkler + CANLI siparis
    prod = R.Prodigi(R.load_prodigi_key("live"), "live")
    harita, _ = R.sku_haritasi(prod, ["8x10"])
    dl = R.DriveLinks()
    perms = []
    try:
        fid, pid, url = dl.open(f"{KOK}/{RID}/BASKI_8x10.jpg"); perms.append([fid, pid])
        kfid, kpid, kurl = dl.open(kart_remote); perms.append([kfid, kpid])
        body = {"merchantReference": REF, "idempotencyKey": REF, "shippingMethod": "Budget",
                "recipient": {"name": adres["name"], "address": {k: adres.get(k) or None for k in
                              ("line1", "line2", "postalOrZipCode", "countryCode", "townOrCity", "stateOrCounty")}},
                "items": [{"merchantReference": f"{REF}-1", "sku": harita.get("8x10", "GLOBAL-HPR-8x10"), "copies": 1,
                           "sizing": "fillPrintArea", "assets": [{"printArea": "default", "url": url}]}],
                "branding": {"postcard": {"url": kurl}}}
        log("CANLI siparis olusturuluyor (Pause indefinitely acik)")
        st, d = prod.create_order(body)
        o = d.get("order") or {}
        oid = o.get("id")
        RAPOR["olustur"] = {"http": st, "outcome": d.get("outcome"), "order_id": oid}
        log(f"olustur: HTTP {st} outcome {d.get('outcome')} id {oid}")
        if not oid:
            f = d.get("failures") or {}                  # yalniz alan adi + hata kodu (girilen deger yazilmaz)
            RAPOR["olustur"]["hata"] = {k: [x.get("code") if isinstance(x, dict) else str(x)[:40] for x in v] if isinstance(v, list)
                                        else str(v)[:40] for k, v in f.items()} if isinstance(f, dict) else str(f)[:120]
            RAPOR["olustur"]["statusText"] = str(d.get("statusText") or "")[:120]
            bitir(2, "siparis olusturulamadi (Prodigi reddetti) - iptal gerekmedi")

        # 6) durum / issues / branding: kisa gozlem (en fazla ~90 sn; pause acik -> uretim yok)
        def oku():
            _, dd = prod.get_order(oid)
            return dd.get("order") or {}
        for _ in range(6):
            o = oku()
            det = (o.get("status") or {}).get("details") or {}
            if str(det.get("downloadAssets", "")).lower() in ("complete", "error") or (o.get("status") or {}).get("issues"):
                break
            time.sleep(15)
        br = o.get("branding") or {}
        RAPOR["durum_iptal_oncesi"] = {
            "stage": (o.get("status") or {}).get("stage"), "details": (o.get("status") or {}).get("details"),
            "issues": [f"{i.get('errorCode')}:{str(i.get('description') or '')[:200]}" for i in (o.get("status") or {}).get("issues") or []],
            "branding": {k: ({kk: vv for kk, vv in (v or {}).items() if kk != "url"} if isinstance(v, dict) else v) for k, v in br.items()},
            "branding_anahtar": sorted(br), "siparis_alanlari": sorted(o),
            "iptal_edilebilir": ((o.get("actions") or {}).get("cancel") or {}).get("isAvailable"),
            "charges": [{"toplam": (c.get("totalCost") or {}).get("amount"), "para": (c.get("totalCost") or {}).get("currency"),
                         "fatura_no_var": bool(c.get("prodigiInvoiceNumber")),
                         "kalemler": [(it.get("cost") or {}).get("amount") for it in c.get("items") or []]} for c in o.get("charges") or []]}
        log("iptal oncesi: " + json.dumps(RAPOR["durum_iptal_oncesi"], ensure_ascii=False)[:1500])

        # 7) HEMEN iptal + dogrulama
        ok, aciklama = prod.iptal(oid)
        o2 = oku()
        RAPOR["iptal"] = {"ok": ok, "aciklama": aciklama, "stage": (o2.get("status") or {}).get("stage")}
        # 8) ucret: iptal sonrasi charges
        RAPOR["charges_iptal_sonrasi"] = [{"toplam": (c.get("totalCost") or {}).get("amount"), "para": (c.get("totalCost") or {}).get("currency"),
                                           "fatura_no_var": bool(c.get("prodigiInvoiceNumber"))} for c in o2.get("charges") or []]
        log(f"iptal: {aciklama}")
        if not ok or str(RAPOR["iptal"]["stage"]).lower() != "cancelled":
            print(f"::error title=GUVENLI TEST IPTAL BASARISIZ::{oid} iptal edilemedi ({aciklama}) - SERDAR PANELDEN IPTAL ETMELI", flush=True)
            bitir(3, f"IPTAL BASARISIZ {oid}")
    finally:
        for fid, pid in perms:                        # 9) gecici linkler kapanir
            try:
                dl.close(fid, pid)
            except Exception as e:                    # noqa: BLE001
                log(f"izin kapatma hatasi {type(e).__name__}")
        RAPOR["izin_kapatildi"] = len(perms)
        rc("rclone", "deletefile", f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{RID}.md")
    bitir(0, f"iptal dogrulandi ({RAPOR['iptal']['stage']})")


if __name__ == "__main__":
    main()
