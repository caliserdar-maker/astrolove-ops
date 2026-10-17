#!/usr/bin/env python3
"""Printful mockup generator: urun 19 (beyaz kupa) 11 oz varyanti, tum gorunum secenekleri.
Yalniz okuma + mockup gorevi. Siparis/urun olusturmaz.
Kullanim: python mockup.py <gorsel_url> <cikti_klasoru>   (env: PRINTFUL_TOKEN)"""
import json, os, pathlib, sys, time, urllib.error, urllib.request

API = "https://api.printful.com"
TOKEN = os.environ["PRINTFUL_TOKEN"]
URL, OUT = sys.argv[1], pathlib.Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
URUN = 19
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops")


def istek(yol, veri=None):
    req = urllib.request.Request(
        API + yol, data=json.dumps(veri).encode() if veri is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": UA, "Accept": "application/json"},
        method="POST" if veri is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print("OZET HATA", yol, e.code, e.read().decode()[:2000])
        raise


def indir(u, hedef):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        hedef.write_bytes(r.read())


def kaydet(ad, veri):
    (OUT / ad).write_text(json.dumps(veri, indent=2, ensure_ascii=False))


# 1) urun ve 11 oz varyanti
urun = istek(f"/products/{URUN}")
kaydet("urun_19.json", urun)
varyantlar = urun["result"]["variants"]
for v in varyantlar:
    print("OZET varyant", v["id"], v.get("name"), v.get("size"))
vid = next(v["id"] for v in varyantlar if "11" in f"{v.get('size', '')} {v.get('name', '')}")
print("OZET secilen_varyant", vid)

# 2) baski dosyasi olculeri ve sablonlar
pf = istek(f"/mockup-generator/printfiles/{URUN}")
kaydet("printfiles_19.json", pf)
tm = istek(f"/mockup-generator/templates/{URUN}")
kaydet("templates_19.json", tm)
res = pf["result"]
yerlesimler = list(res.get("available_placements", {}).keys())
print("OZET yerlesimler", yerlesimler)
print("OZET option_groups", res.get("option_groups"))
print("OZET options", res.get("options"))

vpf = next(x for x in res["variant_printfiles"] if x["variant_id"] == vid)
yerlesim = yerlesimler[0]
pf_id = vpf["placements"][yerlesim]
pfile = next(p for p in res["printfiles"] if p["printfile_id"] == pf_id)
print("OZET printfile", json.dumps(pfile))

sablon_idler = set()
for m in tm["result"].get("variant_mapping", []):
    if m.get("variant_id") == vid:
        sablon_idler |= {x.get("template_id") for x in m.get("templates", [])}
for t in tm["result"].get("templates", []):
    if t.get("template_id") in sablon_idler:
        alanlar = ("template_id", "image_url", "background_url", "template_width", "template_height",
                   "print_area_width", "print_area_height", "print_area_top", "print_area_left", "orientation")
        print("OZET template", json.dumps({k: t.get(k) for k in alanlar}))

# 3) mockup gorevi: dosya tum baski alanini kaplar
W, H = pfile["width"], pfile["height"]
govde = {
    "variant_ids": [vid],
    "format": "png",
    "option_groups": res.get("option_groups", []),
    "files": [{"placement": yerlesim, "image_url": URL,
               "position": {"area_width": W, "area_height": H, "width": W, "height": H, "top": 0, "left": 0}}],
}
kaydet("istek.json", govde)
gorev = istek(f"/mockup-generator/create-task/{URUN}", govde)
anahtar = gorev["result"]["task_key"]
print("OZET task_key", anahtar)

t0 = time.time()
durum = None
for i in range(1, 31):
    time.sleep(10)
    durum = istek(f"/mockup-generator/task?task_key={anahtar}")
    st = durum["result"]["status"]
    g = time.time() - t0
    print(f"{i}/30 durum={st} gecen={g:.0f} sn kalan<= {max(0, 300 - g):.0f} sn %{100 * i // 30}", flush=True)
    if st != "pending":
        break
kaydet("gorev_sonuc.json", durum)
if durum["result"]["status"] != "completed":
    print("OZET HATA gorev", json.dumps(durum["result"])[:2000])
    sys.exit(1)

# 4) mockup gorsellerini indir
n = 0
for m in durum["result"]["mockups"]:
    parcalar = [(m.get("placement", "ana"), m["mockup_url"])]
    parcalar += [(e.get("title") or e.get("option") or "ek", e["url"]) for e in m.get("extra", [])]
    for ad, u in parcalar:
        n += 1
        hedef = OUT / f"{n:02d}_{str(ad).replace(' ', '_').replace('/', '-')}.png"
        indir(u, hedef)
        print("OZET mockup", hedef.name)
print("OZET toplam_mockup", n)