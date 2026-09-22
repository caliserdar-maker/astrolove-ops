#!/usr/bin/env python3
"""
Siparis onizleme simulasyonu (Serdar, gece modu 21 Eyl 2026).

10 sahte siparis: giris dogrulama -> poster -> Serdar'in bakacagi onizleme
karti (poster + girilen metin + dogrulama sonucu + kapi sonuclari, tek gorsel).
Dogrulamayi gecemeyen siparisler "ELLE KONTROL" karti uretir; poster uretilmez.

ETSY'YE DOKUNMAZ. Onay mekanizmasi YOKTUR (Serdar'la ayrica konusulacak).
Cikti: Drive TEMP/KISISEL_PILOT/SIMULASYON/
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from kisisel_pilot import rc, DEST, FONT_DIR
from pilot6 import ISIM_FONT, ISIM_W
from pilot12 import OUT
import edisyon_uret as eu
import giris_dogrula as gd
from pilot16 import blok_kapisi, poster_kur

Image.MAX_IMAGE_PIXELS = None
YOL = OUT / "SIMULASYON"
DEST_S = DEST + "/SIMULASYON"
T0 = time.time()

# --- 10 sahte siparis (uc durumlar dahil) ---
SIPARISLER = [
    # (no, burc cifti, sol, sag, tagline, ulke, edisyon, oran, aciklama)
    (1,  "CANCER_LIBRA", "SERDAR", "LENA", "It Began With a Kiss in the Rain",
     "TR", "black", "4x5", "normal"),
    (2,  "CANCER_LIBRA", "CHRISTOPHER", "ANNA", "Written in the Stars",
     "US", "modern", "2x3", "11 harf (sinirda)"),
    (3,  "CANCER_LIBRA", "Deniz", "Elif", "Yagmurun Altindaki Ilk Opucuk",
     "TR", "pure_white", "3x4", "Turkce TR (i->I)"),
    (4,  "CANCER_LIBRA", "Christopher", "Ipek", "Two Souls One Bond",
     "DE", "black", "11x14", "TR harfsiz, ulke DE (i->I)"),
    (5,  "CANCER_LIBRA", "JACQUELINE", "QUINN", "Written in the Stars Long Before",
     "FR", "modern", "A", "J/Q inen harf"),
    (6,  "CANCER_LIBRA", "ANNA", "MARK", "Sonsuza Kadar Birlikte Kalacagiz Ask",
     "TR", "vintage", "4x5", "36 karakter tagline (sinir asimi)"),
    (7,  "CANCER_LIBRA", "Александр", "LENA", "Forever Us",
     "RU", "black", "4x5", "Kiril isim (desteklenmiyor)"),
    (8,  "CANCER_LIBRA", "ANNA", "MARK", "We love each other always ❤️",
     "US", "pure_white", "4x5", "emoji tagline"),
    (9,  "CANCER_LIBRA", "ABDURRAHMANOGLU", "LENA", "Two Souls",
     "TR", "modern", "4x5", "15 harf (sinir asimi)"),
    (10, "CANCER_LIBRA", "MARIE-CLAIRE", "JO", "Our First Kiss",
     "BE", "black", "3x4", "tireli isim, 2 harfli isim"),
]


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time()-T0:6.1f}s]",
          *a, flush=True)


def _font(b):
    from kisisel_pilot import font_yukle
    return font_yukle(FONT_DIR / ISIM_FONT, b, ISIM_W)


def kart(no, sip, dogru, poster, kapilar, sure):
    """Tek gorsel onizleme karti: poster + girilen metin + dogrulama + kapilar."""
    _, burc, sol, sag, tag, ulke, ed, oran, aciklama = sip
    W, H = 1100, 780
    ok = dogru["durum"] == "TAMAM"
    zemin = (244, 242, 237)
    out = Image.new("RGB", (W, H), zemin)
    d = ImageDraw.Draw(out)
    if poster is not None:
        pw = 360
        p = poster.resize((pw, int(pw * poster.height / poster.width)), Image.LANCZOS)
        out.paste(p, (24, 96))
    else:
        d.rectangle((24, 96, 384, 96 + 450), outline=(180, 60, 60), width=3)
        d.text((60, 300), "POSTER URETILMEDI", fill=(180, 60, 60), font=_font(26))

    bas = (20, 120, 60) if ok else (170, 40, 40)
    d.text((24, 22), f"SIPARIS #{no:02d}  -  {ed} {oran}  -  {burc}", fill=(30, 28, 25),
           font=_font(30))
    d.text((24, 60), f"{dogru['durum']}   ({aciklama})", fill=bas, font=_font(24))

    x, y = 420, 96
    f18, f16 = _font(19), _font(17)

    def satir(etiket, deger, renk=(40, 38, 34)):
        nonlocal y
        d.text((x, y), etiket, fill=(110, 105, 98), font=f16)
        d.text((x + 150, y), str(deger)[:60], fill=renk, font=f18)
        y += 30

    satir("GIRILEN isim 1", sol)
    satir("GIRILEN isim 2", sag)
    satir("GIRILEN tagline", tag)
    satir("teslimat ulkesi", ulke or "-")
    y += 8
    d.text((x, y), "DOGRULAMA", fill=(110, 105, 98), font=f16); y += 26
    for k, ad in (("sol", "isim 1"), ("sag", "isim 2"), ("tagline", "tagline")):
        v = dogru[k]
        renk = (20, 120, 60) if v["durum"] == "TAMAM" else (170, 40, 40)
        satir(f"  {ad}", f"{v['durum']}  ->  {v['deger']}", renk)
        for n in (v["notlar"] or [])[:2]:
            d.text((x + 150, y - 6), f"- {n}"[:70], fill=(150, 90, 30), font=f16)
            y += 22
    y += 8
    d.text((x, y), "KAPILAR", fill=(110, 105, 98), font=f16); y += 26
    if kapilar:
        for ad, v in kapilar.items():
            renk = (20, 120, 60) if v.get("gecti") else (170, 40, 40)
            ozet = v.get("ozet", "GECTI" if v.get("gecti") else "KALDI")
            satir(f"  {ad}", ozet, renk)
        satir("  uretim suresi", f"{sure:.2f} sn")
    else:
        sebep = ("hattin girdisi eksik: " + "; ".join(dogru.get("sistem", []))
                 if dogru["durum"] == "SISTEM HATASI"
                 else "uretim yapilmadi (ELLE KONTROL)")
        d.text((x + 10, y), sebep[:60], fill=(170, 40, 40), font=f18)
    d.text((24, H - 34), "ONAY BEKLIYOR - bu kart yalniz onizlemedir, Etsy'ye "
           "hicbir sey yazilmamistir.", fill=(120, 115, 108), font=f16)
    return out


_KURULUM = {}


def kurulum(ed, oran):
    """Edisyon x oran kurulumu: bir kez olculur, siparisler arasinda paylasilir.

    Kilit degerleri edisyonun KENDI 20/28/36/72 sayfalarindan burada olculur
    (edisyon_uret ile ayni yol). Boylece simulasyon, uretim kosusunun gecici
    checkout'una yazdigi ORAN_SABITLERI.json'a bagli olmaz.
    """
    if (ed, oran) in _KURULUM:
        return _KURULUM[(ed, oran)]
    ham = eu.YOL / ed / "ham" / f"{oran}_p{eu.REF_SAYFA}.jpg"
    zem = eu.YOL / ed / "zemin" / f"{oran}.png"
    if not ham.exists() or not zem.exists():
        eksik = [x for x, y in (("ham", ham), ("zemin", zem)) if not y.exists()]
        v = (None, f"{ed} {oran}: girdi yok ({', '.join(eksik)})")
    else:
        olcum, hata = eu.edisyon_olc(ed, oran)
        if not olcum:
            v = (None, f"{ed} {oran}: olcum yapilamadi "
                       f"({(hata or {}).get('sebep', '?')})")
        else:
            s, S = eu.oran_kur(ed, oran, olcum["kilit"], olcum["o28"])
            v = ((s, S, olcum["o28"]), None)
    _KURULUM[(ed, oran)] = v
    return v


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    eu.girdileri_indir(a.yerel)
    for ed, oran in sorted({(x[6], x[7]) for x in SIPARISLER}):
        _, e = kurulum(ed, oran)
        log(f"kurulum {ed} {oran}: {'hazir' if not e else e}")
    ozet = []
    for sip in SIPARISLER:
        no, burc, sol, sag, tag, ulke, ed, oran, aciklama = sip
        t0 = time.time()
        dogru = gd.siparis_dogrula(sol, sag, tag, ulke)
        poster, kapilar = None, None
        if dogru["durum"] == "TAMAM":
            kur, kur_hata = kurulum(ed, oran)
            if kur is None:
                # Musteri girisi degil, hattin girdisi eksik: ayri durum.
                dogru["durum"] = "SISTEM HATASI"
                dogru.setdefault("sistem", []).append(kur_hata)
            else:
                s, S, o28 = kur
                poster, bilgi, _, _, yeni_genis = poster_kur(
                    s, S, {"sol": dogru["sol"]["deger"],
                           "sag": dogru["sag"]["deger"]},
                    dogru["tagline"]["deger"])
                bk = blok_kapisi(poster, S, s, yeni_genis)
                gk = eu.geometri_kapisi(poster, o28, s, bilgi)
                dk = eu.doku_kapisi(poster, S["ref"], o28, s)
                kapilar = {
                    "blok kalinti": {"gecti": bk["gecti"],
                                     "ozet": f"{'GECTI' if bk['gecti'] else 'KALDI'}"
                                             f"  ort {bk['en_ort']} tepe {bk['en_tepe']}"},
                    "geometri": {"gecti": gk["gecti"],
                                 "ozet": ("GECTI" if gk["gecti"] else "KALDI")
                                         + f"  {gk.get('fark', {})}"[:44]},
                    "doku": {"gecti": dk["gecti"],
                             "ozet": f"{'GECTI' if dk['gecti'] else 'KALDI'}"
                                     f"  rgb {dk['ort_rgb_fark']} prof {dk['profil_fark']}"},
                    "punto/olcek": {"gecti": bilgi["olcek"] >= gd.ALT_SINIR,
                                    "ozet": f"punto {bilgi['punto']} olcek "
                                            f"%{bilgi['olcek']*100:.0f}"},
                }
        sure = time.time() - t0
        k = kart(no, sip, dogru, poster, kapilar, sure)
        k.save(YOL / f"SIPARIS_{no:02d}_{dogru['durum'].replace(' ', '_')}.jpg",
               quality=90)
        ozet.append({"no": no, "edisyon": ed, "oran": oran, "aciklama": aciklama,
                     "durum": dogru["durum"], "sure_sn": round(sure, 2),
                     "kapilar": {kk: vv["gecti"] for kk, vv in (kapilar or {}).items()},
                     "dogrulama": {kk: dogru[kk]["durum"]
                                   for kk in ("sol", "sag", "tagline")}})
        log(f"#{no:02d} {ed} {oran} {aciklama}: {dogru['durum']} ({sure:.2f} sn)")
    (YOL / "SIMULASYON.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    m = ["# SIPARIS ONIZLEME SIMULASYONU (10 sahte siparis)", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "Etsy'ye hicbir sey yazilmadi. Onay mekanizmasi YOK (Serdar'la "
         "ayrica konusulacak); bu kartlar yalniz onizlemedir.", "",
         "| # | edisyon | oran | uc durum | dogrulama | kapilar | sure (sn) |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for o in ozet:
        kp = ", ".join(f"{k}:{'OK' if v else 'X'}" for k, v in o["kapilar"].items()) or "-"
        m.append(f"| {o['no']:02d} | {o['edisyon']} | {o['oran']} | {o['aciklama']} | "
                 f"**{o['durum']}** | {kp} | {o['sure_sn']} |")
    m += ["", "Kartlar: SIPARIS_<no>_<durum>.jpg", ""]
    (YOL / "SIMULASYON.md").write_text("\n".join(m), encoding="utf-8")
    print("\n".join(m), flush=True)
    if not a.yerel:
        rc("copy", str(YOL), DEST_S, capture=False, timeout=600)
        log("simulasyon Drive'a yazildi")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    kos(ap.parse_args())
