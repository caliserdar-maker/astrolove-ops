#!/usr/bin/env python3
"""Videoyu HERO ile ayni kadraja getirir (Mo 14 Eyl 2026).

Video kendi tespitine gore degil, HERO'da OLCULEN uc degeri tutturacak sekilde
kirpilir:
    cerceve/kadraj orani,  merkez kacikligi x,  merkez kacikligi y
Kutu = cerceve yuksekligi / oran (4:5), merkez cerceve merkezinden kaciklik
kadar kaydirilmis. Tespit yalniz cerceveyi bulmak icin kullanilir (sablon
esleme, hero_crop ile ayni); kadrajin kendisi hero'nun olcumlerinden gelir.

Iki gecis: 1) hedef kutuyla kirp, 2) ciktida olculen kenarlari kaynaga geri
haritalayip kutuyu duzelt. Son sapma = hero ile fark (oran, dx, dy icinde en
buyugu); esigi asarsa cikis kodu 1 (Etsy'ye yazilmaz).

Kullanim:
  video_match.py --video V.mp4 --video-poster P.jpg --hero hero_MB.jpg
                 --hero-poster P.jpg --out OUT [--tol 0.002]
"""
import argparse
import json
import pathlib
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hero_crop as HC  # noqa: E402

VID_W, VID_H = 1080, 1350


def olc(yol, poster_yollari):
    """Bir goruntude cerceveyi bul ve BAGIMSIZ kenar olcumuyle oran/kaciklik dondur."""
    kutu, bilgi = HC.cerceve_bul(yol, poster_yollari)
    g = HC.gri(yol)
    H, W = g.shape
    k = HC.kenar_olc(g, tuple(int(round(v)) for v in kutu))
    if not k:
        raise SystemExit(f"HATA: {yol}: kenarlar olculemedi - DUR")
    sol, ust, sag, alt = k
    return {"cerceve_px": [round(v, 1) for v in kutu], "tespit": bilgi,
            "olculen_kenarlar": [round(v, 1) for v in k],
            "oran": round((alt - ust) / H, 4),
            "dx": round(((sol + sag) / 2 - W / 2) / W, 4),
            "dy": round(((ust + alt) / 2 - H / 2) / H, 4),
            "boyut": [W, H]}


def hedef_kutu(cerceve, kaynak_boyut, oran, dx, dy):
    """Cerceveyi verilen oran ve merkez kacikligiyla iceren 4:5 kutu (goreli)."""
    W, H = kaynak_boyut
    fx, fy, fw, fh = cerceve
    ch = fh / oran
    cw = ch * 0.8
    if ch > H or cw > W:
        raise SystemExit(f"HATA: hedef kadraj ({cw:.0f}x{ch:.0f}) kaynaktan ({W}x{H}) buyuk - DUR")
    # olculen kaciklik tanimi: (cerceve_merkezi - kadraj_merkezi) / kadraj_boyutu
    cx = fx + fw / 2 - dx * cw
    cy = fy + fh / 2 - dy * ch
    x0, y0 = cx - cw / 2, cy - ch / 2
    if x0 < 0 or y0 < 0 or x0 + cw > W or y0 + ch > H:
        raise SystemExit(f"HATA: hedef kadraj goruntu disina tasiyor "
                         f"(x0={x0:.0f} y0={y0:.0f} {cw:.0f}x{ch:.0f} / {W}x{H}) - DUR")
    return (x0 / W, y0 / H, cw / W, ch / H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--video-poster", required=True, help="video edisyonunun baski dosyalari (;)")
    ap.add_argument("--hero", required=True, help="hedefi belirleyen hero (kirpilmis)")
    ap.add_argument("--hero-poster", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tol", type=float, default=0.002, help="izin verilen sapma (oran/dx/dy)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vyol = pathlib.Path(a.video)
    vposter = [pathlib.Path(x) for x in a.video_poster.split(";") if x]
    hposter = [pathlib.Path(x) for x in a.hero_poster.split(";") if x]

    # 1) HEDEF: hero'da olculen uc deger
    HC.log(f"hero olcumu: {a.hero}")
    hedef = olc(pathlib.Path(a.hero), hposter)
    HC.log(f"  hedef oran={hedef['oran']} dx={hedef['dx']} dy={hedef['dy']}")

    # 2) VIDEO: kare 0'da cerceveyi bul, hedef kutuyu kur, kirp, olc, bir kez duzelt
    bilgi = HC.ffprobe(vyol)
    HC.log(f"video: {bilgi}")
    k0 = out / "_video_frame0.png"
    HC.kare0(vyol, k0)
    vcerceve, vtespit = HC.cerceve_bul(k0, vposter)
    hedefv = out / "video_MB_cropped.mp4"
    gecisler, olcum, crf, vboyut, goreli = [], {}, 0, 0, None
    for gecis in (1, 2):
        goreli = hedef_kutu(vcerceve, (bilgi["w"], bilgi["h"]), hedef["oran"], hedef["dx"], hedef["dy"])
        crf, vboyut = HC.video_kirp(vyol, (goreli[0] * bilgi["w"], goreli[1] * bilgi["h"],
                                           goreli[2] * bilgi["w"], goreli[3] * bilgi["h"]),
                                    bilgi, hedefv)
        kk = out / "_video_crop_frame0.png"
        k1 = HC.kare0(hedefv, kk)
        g = HC.gri(kk)
        H2, W2 = g.shape
        # beklenen kutu: hedefe gore ciktidaki yeri
        bh = hedef["oran"] * H2
        bw = bh * (vcerceve[2] / vcerceve[3])
        bx = W2 / 2 + hedef["dx"] * W2 - bw / 2
        by = H2 / 2 + hedef["dy"] * H2 - bh / 2
        k = HC.kenar_olc(g, (int(round(bx)), int(round(by)), int(round(bw)), int(round(bh))))
        if not k:
            raise SystemExit("HATA: video ciktisinda kenarlar olculemedi - DUR")
        sol, ust, sag, alt = k
        olcum = {"oran": round((alt - ust) / H2, 4),
                 "dx": round(((sol + sag) / 2 - W2 / 2) / W2, 4),
                 "dy": round(((ust + alt) / 2 - H2 / 2) / H2, 4),
                 "olculen_kenarlar": [round(v, 1) for v in k]}
        sapma = max(abs(olcum["oran"] - hedef["oran"]), abs(olcum["dx"] - hedef["dx"]),
                    abs(olcum["dy"] - hedef["dy"]))
        olcum["sapma"] = round(sapma, 4)
        gecisler.append({"gecis": gecis, "cerceve_px": [round(v, 1) for v in vcerceve], **olcum})
        HC.log(f"  gecis {gecis}: oran={olcum['oran']} dx={olcum['dx']} dy={olcum['dy']} "
               f"sapma=%{sapma*100:.2f}")
        if gecis == 2 or sapma <= a.tol:
            break
        vcerceve = HC.geri_haritala(goreli, (bilgi["w"], bilgi["h"]), k, (W2, H2))

    # 3) KARSILASTIRMA GORSELI
    pad, ust_b = 12, 34
    k1 = Image.open(out / "_video_crop_frame0.png").convert("RGB")
    cmp_im = Image.new("RGB", (2 * VID_W + 3 * pad, VID_H + ust_b + 2 * pad), (250, 250, 252))
    cmp_im.paste(Image.open(a.hero).resize((VID_W, VID_H), Image.LANCZOS), (pad, ust_b + pad))
    cmp_im.paste(k1.resize((VID_W, VID_H), Image.LANCZOS), (2 * pad + VID_W, ust_b + pad))
    d = ImageDraw.Draw(cmp_im)
    d.text((pad + 4, 8), f"hero_MB.jpg  oran {hedef['oran']}  dx {hedef['dx']*100:+.2f}%  "
                         f"dy {hedef['dy']*100:+.2f}%", font=HC.font(24), fill=(30, 30, 40))
    d.text((2 * pad + VID_W + 4, 8), f"video kare 0  oran {olcum['oran']}  dx {olcum['dx']*100:+.2f}%  "
                                     f"dy {olcum['dy']*100:+.2f}%  |  sapma %{olcum['sapma']*100:.2f}",
           font=HC.font(24), fill=(20, 110, 60) if olcum["sapma"] <= a.tol else (170, 30, 30))
    cmp_im.save(out / "compare_hero_vs_video.png")

    yeni = HC.ffprobe(hedefv)
    rapor = {"yontem": "video kadraji HERO'da olculen oran/dx/dy'yi tutturur (kendi tespiti degil)",
             "hedef_hero": {"dosya": pathlib.Path(a.hero).name, **hedef},
             "video_kaynak": bilgi, "video_tespit": vtespit,
             "goreli_kutu": {k: round(v, 6) for k, v in zip("xywh", goreli)},
             "gecisler": gecisler, "olcum": olcum, "tol": a.tol,
             "cikti": {**yeni, "crf": crf},
             "sonuc": "PASS" if olcum["sapma"] <= a.tol else "FAIL"}
    (out / "video_match.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    HC.log(json.dumps(rapor, ensure_ascii=False, indent=1))
    HC.log(f"SONUC: {rapor['sonuc']} (sapma %{olcum['sapma']*100:.2f}, esik %{a.tol*100:.1f})")
    if rapor["sonuc"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
