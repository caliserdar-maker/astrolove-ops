#!/usr/bin/env python3
"""Printful mockup generator: urun 19 (beyaz parlak kupa), boya gore varyant, tum gorunum secenekleri.
Yalniz okuma + mockup gorevi. Siparis/urun/magaza kaydi olusturmaz.
Kullanim: python mockup.py <gorsel_url> <cikti_klasoru>
Ortam: PRINTFUL_TOKEN (zorunlu), BOY = 11 | 15 (verilmezse 11).
  11 -> varyant 1320, beklenen printfile 43 (2700x1050)
  15 -> varyant 4830, beklenen printfile 44 (2700x1140)
Varyant ID ile secilir (addaki metne bakilmaz). Printfile ID/olcu API'den okunur; beklenenden farkliysa
ya da gorsel olcusu printfile'a esit degilse DUR (cikis 2), mockup gorevi acilmaz.
Cikti dosya adlari boy ekli (ornek 03_Front_view_15oz.png, printfiles_19_15oz.json); 11 oz'un eski
eksiz dosyalarinin ustune yazilmaz."""
import json
import os
import pathlib
import re
import struct
import sys
import time
import urllib.error
import urllib.request

API = "https://api.printful.com"
URUN = 19
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops")
BOYLAR = {
    "11": {"varyant": 1320, "printfile": 43, "w": 2700, "h": 1050},
    "15": {"varyant": 4830, "printfile": 44, "w": 2700, "h": 1140},
}


def istek(yol, token, veri=None, deneme=6):
    """429 (TooManyRequests) gelirse mesajdaki sure + 5 sn beklenip en fazla `deneme` kez tekrar denenir."""
    for i in range(1, deneme + 1):
        req = urllib.request.Request(
            API + yol, data=json.dumps(veri).encode() if veri is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                     "User-Agent": UA, "Accept": "application/json"},
            method="POST" if veri is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            govde = e.read().decode()[:2000]
            if e.code == 429 and i < deneme:
                sn = re.search(r"after (\d+) seconds", govde)
                bekle = (int(sn.group(1)) if sn else 60) + 5
                print(f"OZET 429 {yol} deneme {i}/{deneme}, {bekle} sn bekleniyor", flush=True)
                time.sleep(bekle)
                continue
            print("OZET HATA", yol, e.code, govde)
            raise


def indir(u, hedef):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        hedef.write_bytes(r.read())


def png_olcu(u):
    """Gorselin ilk 32 baytindan PNG genislik/yukseklik (IHDR)."""
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Range": "bytes=0-31"})
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read(32)
    if b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", b[16:24])


def dur(mesaj):
    print("OZET DUR", mesaj)
    sys.exit(2)


def varyant_sec(urun, boy):
    """Varyant ID ile secim; ID urunde yoksa DUR."""
    b = BOYLAR[boy]
    varyantlar = urun["result"]["variants"]
    for v in varyantlar:
        print("OZET varyant", v["id"], v.get("name"), v.get("size"))
    v = next((x for x in varyantlar if x["id"] == b["varyant"]), None)
    if v is None:
        dur(f"varyant {b['varyant']} urun {URUN} icinde yok")
    print("OZET secilen_varyant", v["id"], v.get("name"), v.get("size"), f"(BOY={boy})")
    return v["id"]


def printfile_sec(res, vid, boy):
    """API'den printfile ID ve olcusu; beklenenle karsilastirir, farkliysa DUR."""
    b = BOYLAR[boy]
    yerlesimler = list(res.get("available_placements", {}).keys())
    vpf = next((x for x in res["variant_printfiles"] if x["variant_id"] == vid), None)
    if vpf is None:
        dur(f"varyant {vid} icin printfile kaydi yok")
    yerlesim = yerlesimler[0]
    pf_id = vpf["placements"][yerlesim]
    pfile = next(p for p in res["printfiles"] if p["printfile_id"] == pf_id)
    print("OZET printfile", json.dumps(pfile), "yerlesim", yerlesim)
    print(f"OZET printfile_kontrol boy={boy} varyant={vid} printfile={pf_id} olcu={pfile['width']}x{pfile['height']} "
          f"dpi={pfile.get('dpi')} beklenen={b['printfile']} {b['w']}x{b['h']}")
    if (pf_id, pfile["width"], pfile["height"]) != (b["printfile"], b["w"], b["h"]):
        dur(f"printfile beklenenden farkli: {pf_id} {pfile['width']}x{pfile['height']} "
            f"(beklenen {b['printfile']} {b['w']}x{b['h']})")
    return yerlesim, pfile


def main():
    token = os.environ["PRINTFUL_TOKEN"]
    boy = os.environ.get("BOY", "").strip() or "11"
    if boy not in BOYLAR:
        dur(f"BOY {boy!r} gecersiz (11 ya da 15)")
    ek = f"_{boy}oz"
    url, out = sys.argv[1], pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    def kaydet(ad, veri):
        (out / f"{ad}{ek}.json").write_text(json.dumps(veri, indent=2, ensure_ascii=False))

    print("OZET boy", boy, "gorsel", url)

    # 1) urun ve varyant (ID ile)
    urun = istek(f"/products/{URUN}", token)
    kaydet("urun_19", urun)
    vid = varyant_sec(urun, boy)

    # 2) printfile (API) + sablonlar
    pf = istek(f"/mockup-generator/printfiles/{URUN}", token)
    kaydet("printfiles_19", pf)
    tm = istek(f"/mockup-generator/templates/{URUN}", token)
    kaydet("templates_19", tm)
    res = pf["result"]
    print("OZET yerlesimler", list(res.get("available_placements", {}).keys()))
    print("OZET option_groups", res.get("option_groups"))
    print("OZET options", res.get("options"))
    yerlesim, pfile = printfile_sec(res, vid, boy)
    W, H = pfile["width"], pfile["height"]

    sablon_idler = set()
    for m in tm["result"].get("variant_mapping", []):
        if m.get("variant_id") == vid:
            sablon_idler |= {x.get("template_id") for x in m.get("templates", [])}
    alanlar = ("template_id", "image_url", "background_url", "template_width", "template_height",
               "print_area_width", "print_area_height", "print_area_top", "print_area_left", "orientation")
    for t in tm["result"].get("templates", []):
        if t.get("template_id") in sablon_idler:
            print("OZET template", json.dumps({k: t.get(k) for k in alanlar}))

    # 3) gorsel olcusu = printfile olcusu olmali (kirpma/olcekleme olmasin)
    olcu = png_olcu(url)
    print("OZET gorsel_olcu", olcu)
    if olcu != (W, H):
        dur(f"gorsel olcusu {olcu} printfile {W}x{H} ile ayni degil")

    # 4) mockup gorevi: dosya tum baski alanini kaplar
    govde = {
        "variant_ids": [vid],
        "format": "png",
        "option_groups": res.get("option_groups", []),
        "files": [{"placement": yerlesim, "image_url": url,
                   "position": {"area_width": W, "area_height": H, "width": W, "height": H, "top": 0, "left": 0}}],
    }
    kaydet("istek", govde)
    gorev = istek(f"/mockup-generator/create-task/{URUN}", token, govde)
    anahtar = gorev["result"]["task_key"]
    print("OZET task_key", anahtar)

    t0 = time.time()
    durum = None
    for i in range(1, 31):
        time.sleep(10)
        durum = istek(f"/mockup-generator/task?task_key={anahtar}", token)
        st = durum["result"]["status"]
        g = time.time() - t0
        print(f"{i}/30 durum={st} gecen={g:.0f} sn kalan<= {max(0, 300 - g):.0f} sn %{100 * i // 30}", flush=True)
        if st != "pending":
            break
    kaydet("gorev_sonuc", durum)
    if durum["result"]["status"] != "completed":
        print("OZET HATA gorev", json.dumps(durum["result"])[:2000])
        sys.exit(1)

    # 5) mockup gorsellerini indir (boy ekli adlar)
    n = 0
    for m in durum["result"]["mockups"]:
        parcalar = [(m.get("placement", "ana"), m["mockup_url"])]
        parcalar += [(e.get("title") or e.get("option") or "ek", e["url"]) for e in m.get("extra", [])]
        for ad, u in parcalar:
            n += 1
            hedef = out / f"{n:02d}_{str(ad).replace(' ', '_').replace('/', '-')}{ek}.png"
            indir(u, hedef)
            print("OZET mockup", hedef.name)
    print("OZET toplam_mockup", n)


if __name__ == "__main__":
    main()
