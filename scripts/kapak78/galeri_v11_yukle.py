#!/usr/bin/env python3
"""Poster 78 galeri v11 yukleyicisi (Merkez 29 Eki, plan v2 adim 5d-e; Serdar K1: 10 gorsel TEK SEFERDE). KOSTURMA AYRI ONAYLA.
galeri_v10_yukle.py'nin v11 profili (profil_kur("v11")): kanitli yol aynen (eski78 bir_ilan: adim_plani, yukle_guvenli, stabil_galeri,
durum_uzlas, DEVAM / --kurtar, erken bag + son bag, istek_en_kotu; kota_kapisi KOTA_SINIRI 10). Farklar:
  hedef 10 / canli 9 (B1 yedegi = canli kapisi), renk baglari CI->1 MB->7 DB->8 PW->9 WP->10, onay GALERI_V11, PLAN_V11.json,
  liste galeri_v11_liste.py ciktisi (profil v11 zorunlu).
Ek kapilar (ilan basina, canli okumayla; BLOK = yazma yok):
  aciklama: "Frames shown in photos are for display only and are not included." alt dizesi (html coz + bosluk tekle) yoksa BLOK
            (DUR, Serdar'a sorulur; updateListing YOK).
  boy: envanter boy sayisi = format karti boy sayisi (kart manifesti format_boy_sayisi). Alan yoksa "UYGULANAMAZ" notu (BLOK degil;
       bilgi kartlari yokken liste zaten BLOK). Serdar 29 Eki (once galeri, 5x7 hemen ardindan): envanter = format - 1 ve eksik olan
       5x7 ise BLOK DEGIL, UYARI notu "5x7 bekliyor (galeriden sonraki is)"; baska her fark BLOK.
  bes_x7: v10 kapisi aynen (--bes-x7).
Alt metin: LISTE_OZET alt_sablon_durum ONAYLI degilse (TASLAK satir varsa) yukleyici Etsy istegi gondermeden DUR (kuru dahil).
Kullanim: galeri_v10_yukle.py ile ayni argumanlar (--hazir, --out, --kuru | --confirm GALERI_V11 --plan --plan-damga, ...)."""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy"))
import galeri_v10_yukle as V  # noqa: E402

CERCEVE_SATIRI = "Frames shown in photos are for display only and are not included."
UYARI_5X7 = "UYARI: 5x7 bekliyor (galeriden sonraki is); W04 canlida 5x7 eklenene kadar 1 boy fazla gosterir"


def norm(t):
    return " ".join(html.unescape(t or "").split())


def ek_kapi(c, man):
    """-> (BLOK nedenleri, notlar)"""
    neden, notlar = [], []
    if norm(CERCEVE_SATIRI) not in norm(c.get("aciklama")):
        neden.append("aciklamada cerceve satiri yok (\"Frames shown in photos are for display only and are not included.\"); "
                     "DUR, Serdar'a sor (updateListing yok)")
    fb = man.get("format_boy_sayisi")
    if fb is None:
        notlar.append("boy kapisi UYGULANAMAZ (kart manifestinde format_boy_sayisi yok; bilgi kartlari cikinca)")
    elif c.get("boy_sayisi") == fb - 1 and not c.get("bes_x7"):
        notlar.append(UYARI_5X7)
    elif c.get("boy_sayisi") != fb:
        neden.append(f"envanter boy sayisi {c.get('boy_sayisi')} != format karti {fb}")
    elif not c.get("bes_x7"):   # format kartinda 5x7 var; sayi tutup 5x7 yoksa baska bir boy fazla
        neden.append(f"envanter {fb} boy ama 5x7 yok (format karti 5x7 iceriyor)")
    return neden, notlar


def on_kapi(a):
    """Etsy istemcisi kurulmadan: liste profili v11 ve alt metin sablonu ONAYLI."""
    oz = json.loads((Path(a.hazir) / "LISTE_OZET.json").read_text(encoding="utf-8"))
    if oz.get("profil") != "v11":
        raise SystemExit(f"DUR: liste profili {oz.get('profil')} (galeri_v11_liste.py ciktisi beklenir); Etsy istegi yok")
    if oz.get("alt_sablon_durum") != ["ONAYLI"]:
        raise SystemExit(f"DUR: alt metin sablonu ONAYLI degil ({oz.get('alt_sablon_durum')}); TASLAK satir varken yukleyici calismaz")


def main(argv=None):
    V.profil_kur("v11", ek_kapi)
    a = V.arg(argv)
    on_kapi(a)
    import os
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    if a.kuru:
        from yd_envanter_oku import salt_okur
        salt_okur(api)
    return V.sonlandir(api, shop, a)


if __name__ == "__main__":
    sys.exit(main())
