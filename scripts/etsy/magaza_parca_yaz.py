#!/usr/bin/env python3
"""Magaza metin alaninda tek parca degisimi. ETSY'YE YAZAR: tek updateShop, yalniz o isin alani.
Kaynak: duyuru_framed_yaz.py (claude/keen-curie-2hza60, 21 Eki; duyuru ve sale_message yazimlari PASS). Isler:
  duyuru_marka (Serdar 22 Eki, marka adi): announcement "Each original AstroLove design" -> "Each original AstroLoveArt design".
sale_message (21 Eki): "Print or framed print:" -> "Print:". API metni "don&#39;t" HTML varligi iceriyor: yazilan deger html.unescape
  edilmis hali ("don't"; gorunur metin ayni, cift kacis onlenir). Geri okuma: API bicimi beklenenle birebir -> PASS; yalniz kacis
  bicimi farkli (unescape esit) -> PASS_GORUNUR; aksi FAIL. &#39; disinda HTML varligi varsa DUR.

Baska karakter degismez.
On kosul (biri tutmazsa yazma yok, DUR): parca canli duyuruda tam 1 kez; metinde HTML varligi (&#, &amp;) yok (cift kacis riski);
  yeni metinde uzun/orta tire yok; yeni metin = eski metinden yalniz bu parca farkli (uzunluk farki tutarli).
Yazma: PUT /shops/{id} yalniz announcement alani. Geri okuma: GET /shops/{id}; announcement == beklenen (birebir) ve diger tum
  metin alanlari (title, sale_message, digital_sale_message, policy_*, vb.) yazmadan onceki ile ayni -> PASS.
Kota tabani 10 (CLAUDE.md). Cikti: OUT/DUYURU_YEDEK.json (yazmadan onceki tum metin alanlari), OUT/DUYURU_GERI_OKUMA.txt
Kullanim: magaza_parca_yaz.py --is duyuru_marka --out OUT --confirm DUYURU_MARKA
"""
import argparse
import html
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

KOTA_TABAN = 10
# is -> (alan, eski parca, yeni parca, onay sozcugu)
ISLER = {"duyuru_marka": ("announcement", "Each original AstroLove design", "Each original AstroLoveArt design", "DUYURU_MARKA")}
IZINLI_VARLIK = {"&#39;"}
TIRE = re.compile("[—–]")


def metin_alanlari(shop):
    return {k: v for k, v in (shop or {}).items() if isinstance(v, str)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is", dest="is_", required=True, choices=sorted(ISLER))
    a = ap.parse_args()
    alan, ESKI, YENI, onay = ISLER[a.is_]
    if a.confirm != onay:
        raise SystemExit(f"HATA: --confirm {onay} gerekli. DUR.")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop_id = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    once = metin_alanlari(api.get(f"/shops/{shop_id}"))
    (out / "DUYURU_YEDEK.json").write_text(json.dumps(once, ensure_ascii=False, indent=1), encoding="utf-8")
    kota0 = api.remaining
    eski = once.get(alan) or ""
    beklenen = eski.replace(ESKI, YENI)
    sorun = []
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        sorun.append(f"kota {api.remaining} < {KOTA_TABAN}")
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
