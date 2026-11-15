#!/usr/bin/env python3
"""Magaza metin alaninda tek parca ya da tam metin degisimi. ETSY'YE YAZAR: tek updateShop, yalniz o isin alani.
Kaynak: duyuru_framed_yaz.py (claude/keen-curie-2hza60, 21 Eki; duyuru ve sale_message yazimlari PASS). Isler:
  duyuru_marka (Serdar 22 Eki, marka adi): announcement "Each original AstroLove design" -> "Each original AstroLoveArt design".
  duyuru_noel (Serdar 15 Kas "Evet", duyuru v7): announcement TAM degisim; yeni metin dosyadan (--metin, varsayilan
  docs/magaza/DUYURU_NOEL_20261115.txt; dosya sonundaki satir sonu yazilmaz).
sale_message (21 Eki): "Print or framed print:" -> "Print:". API metni "don&#39;t" HTML varligi iceriyor: yazilan deger html.unescape
  edilmis hali ("don't"; gorunur metin ayni, cift kacis onlenir). Geri okuma: API bicimi beklenenle birebir -> PASS; yalniz kacis
  bicimi farkli (unescape esit) -> PASS_GORUNUR; aksi FAIL. &#39; disinda HTML varligi varsa DUR.

Parca islerinde baska karakter degismez.
On kosul, parca isi (biri tutmazsa yazma yok, DUR): parca canli duyuruda tam 1 kez; metinde HTML varligi (&#, &amp;) yok (cift kacis
  riski); yeni metinde uzun/orta tire yok; yeni metin = eski metinden yalniz bu parca farkli (uzunluk farki tutarli).
On kosul, tam degisim (duyuru_noel; biri tutmazsa yazma yok, DUR): canli metin normallestirilince (html.unescape, \\r\\n -> \\n) yeni
  metne esit -> "zaten yazili"; bosluklar tek bosluga indirilince esit -> "zaten yazili (satir sonu farkli)" (SATIR_SONU sonrasi
  ikinci yazim yok; geri yazim ayri onay); yeni metnin ilk 60 harf/rakami (varlik tekrarli cozulur, etiket atilir) canlida ->
  "onceki yazim izi" (FAIL sonrasi ikinci yazim yok); varsayilan dosya sha256 onayli degere esit (degilse istek yok); yeni metinde uzun/orta tire, AstroLove(?!Art), HTML varligi yok; ilk GET sonrasi kota
  >= KOTA_SINIRI + 2 (PUT + GET + sert taban); PUT'tan hemen once AYNI fonksiyonda (tam_yaz) metin_yasak_kapisi(mod="ENGEL").
Yazma: PUT /shops/{id} yalniz o alan. Geri okuma: GET /shops/{id}; diger tum metin alanlari (title, sale_message,
  digital_sale_message, policy_*, vb.) yazmadan onceki ile ayni olmali.
  Parca: announcement == beklenen (birebir) -> PASS.
  Tam: html.unescape(yeni).replace("\\r\\n", "\\n") == dosya metni -> PASS (cikis 0); tam esit degil ama bosluklar tek bosluga
  indirilince esit -> SATIR_SONU (cikis 2; tek \\r sayisi raporda); <br> varsa FAIL (cikis 2); aksi FAIL (cikis 2).
Kota: on kosul KOTA_ON_KOSUL = KOTA_SINIRI + 2 = 12 (iki is); her istekten once sert taban etsy_common KOTA_SINIRI 10 (5xx yeniden
  denemeleri dahil). Cikti: OUT/DUYURU_YEDEK.json (parca) ya da OUT/DUYURU_YEDEK_<UTC>.json (tam; on kosullardan ONCE),
  OUT/DUYURU_GERI_OKUMA.txt (eski metin tam), OUT/DUYURU_SONRA.json.
Kullanim: magaza_parca_yaz.py --is duyuru_marka --out OUT --confirm DUYURU_MARKA
          magaza_parca_yaz.py --is duyuru_noel --out OUT --confirm DUYURU_NOEL [--metin DOSYA]
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys

BURA = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BURA))
from etsy_common import KOTA_SINIRI, Etsy, TokenStore, log, mask, metin_yasak_kapisi  # noqa: E402

KOTA_ON_KOSUL = KOTA_SINIRI + 2      # PUT + GET + sert taban (Serdar 15 Kas gorev metni); KOTA_SINIRI degismez
# is -> (alan, eski parca, yeni parca, onay sozcugu)
ISLER = {"duyuru_marka": ("announcement", "Each original AstroLove design", "Each original AstroLoveArt design", "DUYURU_MARKA")}
# tam degisim isleri: is -> (alan, varsayilan metin dosyasi, onay sozcugu, varsayilan dosyanin onayli sha256'si)
TAM_ISLER = {"duyuru_noel": ("announcement", BURA.parents[1] / "docs" / "magaza" / "DUYURU_NOEL_20261115.txt", "DUYURU_NOEL",
                             "99c8738a2e3e5f05cbe2e23d91eaebe24eda1a6255be664e1c9d4c7fc4cc9f7e")}   # Serdar 15 Kas duyuru v7, 1080 bayt
IZ_UZUNLUK = 60      # yeni metnin ilk 60 harf/rakami (temizlenmis) canlida varsa onceki yazim izi: ikinci yazim yok
IZINLI_VARLIK = {"&#39;"}
TIRE = re.compile("[—–]")
MARKA_EKSIK = re.compile(r"AstroLove(?!Art)")
VARLIK = re.compile(r"&#?\w+;")


def metin_alanlari(shop):
    return {k: v for k, v in (shop or {}).items() if isinstance(v, str)}


def norm(t):
    """API bicimi -> gorunur metin: HTML varligi cozulur, \\r\\n -> \\n."""
    return html.unescape(t or "").replace("\r\n", "\n")


def bosluk(t):
    return re.sub(r"\s+", " ", t or "").strip()


def temiz(t):
    """Iz karsilastirmasi: HTML varligi degismeyene kadar cozulur (cift kacis), etiket atilir, yalniz harf ve rakam kalir
    (tirnak / kesme benzerleri, bosluk ve noktalama farki izi gizlemez)."""
    t = t or ""
    for _ in range(5):
        u = html.unescape(t)
        if u == t:
            break
        t = u
    return re.sub(r"[^0-9a-z]", "", re.sub(r"<[^>]*>", " ", t).lower())


def yaz_rapor(out, rapor, kod):
    (out / "DUYURU_GERI_OKUMA.txt").write_text("\n".join(rapor) + "\n", encoding="utf-8")
    for x in rapor:
        log(x)
    sys.exit(kod)


def tam_on_kosul(eski, yeni, kalan):
    """Tam degisim on kosullari -> sorun listesi (bos = yazilabilir)."""
    sorun = []
    if norm(eski) == yeni:
        sorun.append("zaten yazili (canli metin yeni metne esit)")
    elif bosluk(norm(eski)) == bosluk(yeni):
        sorun.append("zaten yazili (satir sonu farkli; SATIR_SONU sonrasi ikinci yazim yok, geri yazim ayri onay)")
    elif yeni.strip() and temiz(yeni)[:IZ_UZUNLUK] in temiz(eski):
        sorun.append("canlida onceki yazim izi var (yeni metnin basi canlida; FAIL / SATIR_SONU sonrasi ikinci yazim yok, geri yazim ayri onay)")
    if not yeni.strip():
        sorun.append("yeni metin bos")
    if TIRE.search(yeni):
        sorun.append("yeni metinde uzun/orta tire")
    if MARKA_EKSIK.search(yeni):
        sorun.append(f"yeni metinde 'AstroLove' (Art'siz) {len(MARKA_EKSIK.findall(yeni))} kez")
    if VARLIK.search(yeni):
        sorun.append(f"yeni metinde HTML varligi {sorted(set(VARLIK.findall(yeni)))}")
    if kalan is None:
        sorun.append("kota okunamadi (ilk GET sonrasi x-remaining-today yok)")
    elif int(kalan) < KOTA_ON_KOSUL:
        sorun.append(f"kota {kalan} < {KOTA_ON_KOSUL}")
    return sorun


def tam_yaz(api, shop_id, alan, gonder, out, rapor):
    """Yasak sozcuk kapisi (ENGEL) ve PUT ayni fonksiyonda; kapi SystemExit verirse yazim yok, neden rapora, DUR (cikis 3)."""
    try:
        metin_yasak_kapisi("PUT", f"/shops/{shop_id}", {alan: gonder}, mod="ENGEL")
    except SystemExit as e:
        yaz_rapor(out, rapor + [f"SONUC: DUR, yazma yapilmadi: {e}"], 3)
    api.put(f"/shops/{shop_id}", {alan: gonder})


def tam_degisim(a, api, shop_id):
    alan, varsayilan, _, sha_onay = TAM_ISLER[a.is_]
    out = pathlib.Path(a.out)
    yol = pathlib.Path(a.metin) if a.metin else varsayilan
    ham = yol.read_bytes()
    sha = hashlib.sha256(ham).hexdigest()
    if not a.metin and sha != sha_onay:      # is akisi --metin vermez: yalniz onayli dosya yazilir (istek yok, DUR)
        raise SystemExit(f"DUR: {yol.name} sha256 {sha} onayli degerden farkli ({sha_onay}); Etsy istegi yok.")
    yeni = ham.decode("utf-8").rstrip("\n")
    once = metin_alanlari(api.get(f"/shops/{shop_id}"))
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out / f"DUYURU_YEDEK_{ts}.json").write_text(json.dumps(once, ensure_ascii=False, indent=1), encoding="utf-8")
    kota0 = api.remaining
    eski = once.get(alan) or ""
    rapor = [f"{alan.upper()} TAM DEGISIM (is {a.is_}) | metin {yol.name} sha256 {sha} | kota ilk GET sonrasi {kota0}",
             "--- ONCE (API, tam) ---", eski, "--- YENI (dosya) ---", yeni]
    sorun = tam_on_kosul(eski, yeni, kota0)
    if sorun:
        yaz_rapor(out, rapor + ["SONUC: DUR, yazma yapilmadi: " + "; ".join(sorun)], 3)
    try:
        tam_yaz(api, shop_id, alan, yeni, out, rapor)
        sonra = metin_alanlari(api.get(f"/shops/{shop_id}"))
    except SystemExit as e:
        if e.code in (0, 3):      # tam_yaz icindeki ENGEL DUR'u (rapor yazildi)
            raise
        yaz_rapor(out, rapor + [f"SONUC: HATA (PUT oncesi kapi/kota, PUT ya da geri okuma GET): {e} | PUT gitmis olabilir; ikinci kosu yok, canli once salt okumayla kontrol edilir"], 1)
    except Exception as e:      # requests zaman asimi / baglanti / JSON hatasi (etsy_common SystemExit'e cevirmez)
        yaz_rapor(out, rapor + [f"SONUC: HATA (PUT ya da geri okuma GET istisnasi {type(e).__name__}): {e} | PUT gitmis olabilir; ikinci kosu yok, canli once salt okumayla kontrol edilir"], 1)
    geri = sonra.get(alan) or ""
    degisen = sorted(k for k in set(once) | set(sonra) if k != alan and once.get(k) != sonra.get(k))
    g = norm(geri)
    tek_cr = len(re.findall(r"\r(?!\n)", geri))
    br = len(re.findall(r"<br\s*/?>", geri, re.I))
    if g == yeni and not degisen:
        sonuc, kod = "PASS", 0
    elif bosluk(g) == bosluk(yeni) and not degisen:      # <br> bosluk farki olarak FAIL'e duser
        sonuc, kod = "SATIR_SONU", 2
    else:
        sonuc, kod = "FAIL", 2
    rapor += ["--- SONRA (API geri okuma) ---", geri,
              f"normallestirilmis esit: {g == yeni} | bosluk normal esit: {bosluk(g) == bosluk(yeni)} | API'de \\r\\n {geri.count(chr(13) + chr(10))} | "
              f"tek \\r {tek_cr} | <br> {br} | diger metin alanlarinda degisen: {degisen or 'yok'} | "
              f"AstroLove (Art'siz) {len(MARKA_EKSIK.findall(g))} | uzun/orta tire {len(TIRE.findall(g))}",
              f"SONUC: {sonuc} | updateShop 1, GET {api.calls - 1} | kota sonda {api.remaining}"]
    if kod:
        rapor.append("NOT: ikinci kosu yok; geri yazim ayri Serdar onayi (DUYURU_YEDEK_*.json).")
    (out / "DUYURU_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1), encoding="utf-8")
    yaz_rapor(out, rapor, kod)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is", dest="is_", required=True, choices=sorted(set(ISLER) | set(TAM_ISLER)))
    ap.add_argument("--metin", default="", help="tam degisim metin dosyasi (yalniz TAM_ISLER; varsayilan isin dosyasi)")
    a = ap.parse_args()
    onay = TAM_ISLER[a.is_][2] if a.is_ in TAM_ISLER else ISLER[a.is_][3]
    if a.confirm != onay:
        raise SystemExit(f"HATA: --confirm {onay} gerekli. DUR.")
    if a.metin and a.is_ not in TAM_ISLER:
        raise SystemExit("HATA: --metin yalniz tam degisim islerinde. DUR.")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop_id = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    if a.is_ in TAM_ISLER:
        tam_degisim(a, api, shop_id)
        return
    alan, ESKI, YENI, _ = ISLER[a.is_]
    once = metin_alanlari(api.get(f"/shops/{shop_id}"))
    (out / "DUYURU_YEDEK.json").write_text(json.dumps(once, ensure_ascii=False, indent=1), encoding="utf-8")
    kota0 = api.remaining
    eski = once.get(alan) or ""
    beklenen = eski.replace(ESKI, YENI)
    sorun = []
    if api.remaining is not None and int(api.remaining) < KOTA_ON_KOSUL:
        sorun.append(f"kota {api.remaining} < {KOTA_ON_KOSUL}")
    if eski.count(ESKI) != 1:
        sorun.append(f"parca {eski.count(ESKI)} kez (1 olmali)")
    varliklar = set(re.findall(r"&#?\w+;", eski))
    if varliklar - IZINLI_VARLIK:
        sorun.append(f"metinde izinsiz HTML varligi {sorted(varliklar - IZINLI_VARLIK)} (cift kacis riski)")
    gonder = html.unescape(beklenen)
    if TIRE.search(beklenen):
        sorun.append("yeni metinde uzun/orta tire")
    if len(eski) - len(beklenen) != len(ESKI) - len(YENI):
        sorun.append("uzunluk farki beklenmedik")
    rapor = [f"{alan.upper()} YAZMA (is {a.is_}) | kota ilk GET sonrasi {kota0}", "--- ONCE (API) ---", eski,
             "--- BEKLENEN (API bicimi) ---", beklenen]
    if gonder != beklenen:
        rapor.append(f"gonderilen deger html.unescape edildi: {sorted(varliklar)} -> karakter (gorunur metin ayni)")
    if sorun:
        rapor += ["SONUC: DUR, yazma yapilmadi: " + "; ".join(sorun)]
        (out / "DUYURU_GERI_OKUMA.txt").write_text("\n".join(rapor) + "\n", encoding="utf-8")
        for x in rapor:
            log(x)
        sys.exit(3)
    api.put(f"/shops/{shop_id}", {alan: gonder})
    sonra = metin_alanlari(api.get(f"/shops/{shop_id}"))
    yeni = sonra.get(alan) or ""
    degisen = sorted(k for k in set(once) | set(sonra) if k != alan and once.get(k) != sonra.get(k))
    birebir = yeni == beklenen
    gorunur = html.unescape(yeni) == html.unescape(beklenen) and "&amp;" not in yeni
    ok = (birebir or gorunur) and not degisen
    rapor += ["--- SONRA (API geri okuma) ---", yeni,
              f"birebir beklenen ile ayni: {birebir} | gorunur metin ayni (unescape): {gorunur} | "
              f"diger metin alanlarinda degisen: {degisen or 'yok'} | "
              f"yeni parca {yeni.count(YENI)} | eski parca (Art'siz) {len(re.findall(re.escape(ESKI) + r'(?!Art)', yeni))} | uzun/orta tire {len(TIRE.findall(yeni))}",
              f"SONUC: {('PASS' if birebir else 'PASS_GORUNUR') if ok else 'FAIL'} | updateShop 1, GET {api.calls - 1} | kota sonda {api.remaining}"]
    (out / "DUYURU_GERI_OKUMA.txt").write_text("\n".join(rapor) + "\n", encoding="utf-8")
    (out / "DUYURU_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in rapor:
        log(x)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
