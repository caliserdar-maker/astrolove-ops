#!/usr/bin/env python3
"""Drive'da 'baglantiya sahip herkes' (anyone/domain) paylasimini KAPATIR (Serdar 21 Eki karar 1).
Hedef: kimligi sha256 ilk 12 hanesi --hedef ile verilen klasor + tum alt ogeleri (kimlik loga/girdiye yazilmaz).
Ayrica Drive genelinde sahibin herkese/alana acik tum ogeleri SAYILIR ve kaydedilir (degistirilmez).
Sira: once izinleri oku ve kaydet -> kapat -> geri oku, dogrula. Hedef disinda hicbir izne dokunmaz.
Loga yalniz sayi yazilir; kimlik/ad yalniz --cikti klasorundeki JSON'a (Drive'a sahip-yalniz yuklenir).
Ortam: DRIVE_TOKEN (OAuth access token). Cikis: 0 = hedefte anyone/domain izni kalmadi, 1 = kaldi ya da hata."""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/drive/v3"
ACIK = ("anyone", "domain")


def istek(yontem, yol, params=None, deneme=6):
    url = API + yol + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(deneme):
        req = urllib.request.Request(url, method=yontem, headers={"Authorization": "Bearer " + os.environ["DRIVE_TOKEN"]})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                govde = r.read()
                return json.loads(govde) if govde else {}
        except urllib.error.HTTPError as e:
            if (e.code in (429, 500, 502, 503) or (e.code == 403 and b"ateLimit" in (e.read() or b""))) and i < deneme - 1:
                time.sleep(2 ** (i + 1))
                continue
            raise


def liste(q, alanlar="id,name,mimeType,permissions(id,type,role)"):
    cikti, sayfa = [], None
    while True:
        p = {"q": q, "fields": f"nextPageToken,files({alanlar})", "pageSize": 1000, "supportsAllDrives": "true"}
        if sayfa:
            p["pageToken"] = sayfa
        d = istek("GET", "/files", p)
        cikti += d.get("files", [])
        sayfa = d.get("nextPageToken")
        if not sayfa:
            return cikti


def klasor_bul(ad, ust):
    q = f"name = '{ad}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{ust}' in parents"
    f = liste(q, "id,name")
    if len(f) != 1:
        raise SystemExit(f"HATA: '{ad}' klasoru {len(f)} kez bulundu (1 bekleniyor)")
    return f[0]["id"]


def alt_agac(kok_id):
    """kok dahil tum ogeler (BFS)."""
    kok = istek("GET", f"/files/{kok_id}", {"fields": "id,name,mimeType,permissions(id,type,role)"})
    hepsi, kuyruk = [kok], [kok_id]
    while kuyruk:
        k = kuyruk.pop()
        for f in liste(f"'{k}' in parents and trashed = false"):
            hepsi.append(f)
            if f["mimeType"] == "application/vnd.google-apps.folder":
                kuyruk.append(f["id"])
    return hepsi


def acik_izinler(f):
    return [p for p in f.get("permissions") or [] if p.get("type") in ACIK]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kuru", "uygula"], required=True)
    ap.add_argument("--hedef", required=True, help="hedef klasor kimliginin sha256 ilk 12 hanesi")
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    acik_tum = liste("(visibility = 'anyoneWithLink' or visibility = 'anyoneCanFind' or visibility = 'domainWithLink' "
                     "or visibility = 'domainCanFind') and trashed = false and 'me' in owners", "id,name,mimeType,parents,permissions(id,type,role)")
    sayim = {"drive_geneli_acik": [{"id": f["id"], "ad": f["name"], "tur": f["mimeType"].split(".")[-1], "ust": f.get("parents"),
                                    "izin": acik_izinler(f)} for f in acik_tum]}
    hedef = [f for f in acik_tum if hashlib.sha256(f["id"].encode()).hexdigest()[:12] == a.hedef]
    print(f"Drive geneli herkese/alan acik oge: {len(acik_tum)}")
    if len(hedef) != 1:
        json.dump({"tarama": sayim}, open(f"{a.cikti}/PAYLASIM_ONCE.json", "w"), ensure_ascii=False, indent=1)
        raise SystemExit(f"HATA: hedef acik ogeler arasinda {len(hedef)} kez (1 beklenir; zaten kapali olabilir)")
    hedef_ogeler = alt_agac(hedef[0]["id"])
    once = [{"id": f["id"], "ad": f["name"], "izin": f.get("permissions")} for f in hedef_ogeler]
    json.dump({"hedef_once": once, "tarama": sayim}, open(f"{a.cikti}/PAYLASIM_ONCE.json", "w"), ensure_ascii=False, indent=1)
    print(f"hedef: oge {len(once)}, anyone/domain izinli {sum(1 for f in hedef_ogeler if acik_izinler(f))}")
    if a.mod == "kuru":
        print("KURU: izin degismedi")
        return 0
    silinen, hata = 0, 0
    for tur in range(2):  # once klasor (miras biter), sonra kalan dogrudan izinler
        if tur:
            time.sleep(5)
        for f in hedef_ogeler if tur else hedef_ogeler[:1]:
            guncel = istek("GET", f"/files/{f['id']}", {"fields": "permissions(id,type,role,permissionDetails)"})
            for p in acik_izinler(guncel):
                miras = all(d.get("inherited") for d in p.get("permissionDetails") or [{}])
                if tur and miras and p.get("permissionDetails"):
                    continue
                try:
                    istek("DELETE", f"/files/{f['id']}/permissions/{p['id']}")
                    silinen += 1
                except urllib.error.HTTPError as e:
                    hata += 1
                    print(f"silme hatasi HTTP {e.code}")
    time.sleep(3)
    sonra = [{"id": f["id"], "ad": f["name"],
              "izin": istek("GET", f"/files/{f['id']}", {"fields": "permissions(id,type,role)"}).get("permissions")} for f in hedef_ogeler]
    kalan = sum(1 for f in sonra if any(p.get("type") in ACIK for p in f["izin"] or []))
    json.dump({"hedef_sonra": sonra, "silinen": silinen, "hata": hata, "kalan_acik": kalan},
              open(f"{a.cikti}/PAYLASIM_SONRA.json", "w"), ensure_ascii=False, indent=1)
    print(f"UYGULA: silinen izin {silinen}, hata {hata}, geri okuma: anyone/domain izinli oge {kalan}/{len(sonra)}")
    print("SONUC:", "PASS" if kalan == 0 else "FAIL")
    return 0 if kalan == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
