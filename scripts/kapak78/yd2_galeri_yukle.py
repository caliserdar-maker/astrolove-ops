#!/usr/bin/env python3
"""YD (1st Anniversary) 2. ASAMA galeri yukleyicisi (Merkez / Serdar 1 Kas gece hazirligi). KOSTURMA AYRI SERDAR ONAYIYLA.
galeri_v10_yukle.py'nin yd2 profili (profil_kur("yd2")): eski78 bir_ilan YALIN yolu (galeri v11 ile ayni; Merkez 29 Eki karar 3):
  sira 1 = 1. asamanin canli kapagi DOKUNMA (silinmez, yeniden yuklenmez, alt metni / sirasi yazilmaz; dokunma_kontrol rank 1'i dogrular),
  2-10 Y02-Y10 DEGISTIR (rank + alt metin yukleme isteginde), kalan 12 canli gorsel CIKAR, Style (513) baglari Starlit 6 / Timeless 7 /
  First Page 8 / Layers 9 / Botanical 10 TEK variation-images cagrisi (silmeden ONCE dogrulanir), sira_kontrol. Kota kapisi KOTA_SINIRI 10.
Liste: yd_liste_uret.py liste --profil yd2 ciktisi (LISTE_<ilan>.csv sira 1 DOKUNMA; manifest profil yd2, dokunma_id).
Ek kapilar (ilan basina, canli okumayla; BLOK = yazma yok):
  yapi : envanterde Size (516) boy sayisi 14 olmali (yeni ilan yapisi yd_yapi_yaz once yazilmis). Serdar 30 Eki: galeri yeni yapiya
         gecmeden yuklenmez. Degilse BLOK.
  kapak: canli rank 1 kimligi = manifest dokunma_id (liste kosusundaki 1. asama kapagi). Degilse BLOK.
  profil: manifest profil yd2 degilse BLOK.
Kullanim: galeri_v10_yukle.py ile ayni argumanlar (--hazir, --out, --kuru | --confirm YD_GALERI_V2 --plan --plan-damga, ...)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy"))
import galeri_v10_yukle as V  # noqa: E402

BOY_SAYISI = 14   # yeni yapi: Style x Format x Size (14 boy; yd_yapi_kuru.BOYLAR)


def ek_kapi(c, man):
    """(BLOK nedenleri, notlar)"""
    neden, notlar = [], []
    if man.get("profil") != "yd2":
        neden.append(f"manifest profili {man.get('profil')} (yd2 beklenir; yd_liste_uret --profil yd2)")
    if c.get("boy_sayisi") != BOY_SAYISI:
        neden.append(f"envanter Size (516) boy sayisi {c.get('boy_sayisi')} ({BOY_SAYISI} beklenir): yeni ilan yapisi once "
                     "(Serdar 30 Eki: galeri yeni yapidan once yuklenmez)")
    g = c.get("galeri") or []
    r1 = g[0].get("listing_image_id") if g else None
    if man.get("dokunma_id") is None or r1 != man.get("dokunma_id"):
        neden.append(f"canli rank 1 {r1} != liste kosusundaki 1. asama kapagi {man.get('dokunma_id')} (DOKUNMA kapagi degismis)")
    return neden, notlar


def on_kapi(a):
    """Etsy istemcisi kurulmadan: liste profili yd2 olmali (yd_liste_uret --profil yd2)."""
    oz = json.loads((Path(a.hazir) / "LISTE_OZET.json").read_text(encoding="utf-8"))
    if oz.get("profil") != "yd2":
        raise SystemExit(f"DUR: liste profili {oz.get('profil')}, kosu profili yd2 (yd_liste_uret.py liste --profil yd2); Etsy istegi yok")


def main(argv=None):
    V.profil_kur("yd2", ek_kapi)
    on_kapi(V.arg(argv))
    return V.main(argv)


if __name__ == "__main__":
    sys.exit(main())
