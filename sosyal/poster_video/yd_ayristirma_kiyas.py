#!/usr/bin/env python3
"""Denetim 20261101D: yd_video.py ayristirma kiyasi (duzeltme oncesi / sonrasi). Her kapak icin iki surum YD_AYRISTIR_JSON ile kosulur
(video uretilmez); sign_a, sign_b, names_row, msg_row kutulari BIREBIR karsilastirilir (merged = ortak sembol kutusu, ayrica yazilir).
Eski surum main'deki dosyadir; ayni JSON dokumu bu betik tarafindan eski dosyanin kopyasina eklenir (eski davranis degismez).
Denetim 20261101E: (madde 2) ONCE_HATA_SIMDI_TAMAM ciftlerin kutulari REFERANSLA kiyaslanir: sign_a = ayni ilk burcun AYNI ciftlerdeki
medyani, sign_b = ayni ikinci burcun medyani, names_row / msg_row = tum AYNI ciftlerin medyani; en buyuk fark <= REF_PAY px (oneri).
Tum ciftler icin ayni sapma BILGI olarak yazilir. (madde 5) --beklenen N: kapak sayisi N degilse FAIL; --ters: bilinen fark (yeni
surumde sign_a / sign_b yer degistirir) ile kiyas her ciftte FARK bulmali, bulamazsa FAIL (ters kontrol).
Kullanim: yd_ayristirma_kiyas.py <eski_yd_video.py> <yeni_yd_video.py> <kapak_dizini> <cikti.json> [--beklenen N] [--ters]
Cikis kodu: 0 = beklenen disi fark yok, 1 = fark / yeni hata / referans sapmasi / sayi eksik (ters modda: FARK bulunamayan cift)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ANAHTAR = ("sign_a", "sign_b", "names_row", "msg_row")
REF_PAY = 6   # px (2000 px poster): referans kutudan en buyuk izinli fark (oneri; inceleme olcumu ARIES_LIBRA sign_a 3 px)
EK = '''if os.environ.get('YD_AYRISTIR_JSON'):
    import json
    json.dump(dict(sign_a=P.sign_a[1:5], sign_b=P.sign_b[1:5], names_row=P.names_row[1:5], msg_row=P.msg_row[1:5], merged=P.merged[1:5],
                   sembol_ek_bant=getattr(P, 'sembol_ek_bant', None)), open(os.environ['YD_AYRISTIR_JSON'], 'w'))
    sys.exit(0)
'''


def hazirla_eski(yol, hedef):
    s = Path(yol).read_text(encoding="utf-8")
    if "YD_AYRISTIR_JSON" not in s:
        k = "P = PosterYD(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC).astype(np.float32))\n"
        assert s.count(k) == 1, "eski dosyada P satiri bulunamadi"
        s = s.replace(k, k + EK)
    Path(hedef).write_text(s, encoding="utf-8")


def kos(py, kapak, js):
    if os.path.exists(js):
        os.remove(js)
    r = subprocess.run([sys.executable, "-I", py, kapak, "/dev/null"], env=dict(os.environ, YD_AYRISTIR_JSON=js),
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(js):
        return None, (r.stderr or r.stdout).strip().splitlines()[-1:] or ["?"]
    return json.load(open(js)), None


def referans(satir):
    """AYNI ciftlerden burca gore medyan kutular."""
    import numpy as np
    ayni = [d for d in satir if d["durum"] == "AYNI"]
    ra, rb = {}, {}
    for d in ayni:
        a, b = d["cift"].split("_")
        ra.setdefault(a, []).append(d["yeni"]["sign_a"]); rb.setdefault(b, []).append(d["yeni"]["sign_b"])
    med = lambda L: [int(round(v)) for v in np.median(np.array(L), 0)]  # noqa: E731
    ortak = {k: med([d["yeni"][k] for d in ayni]) for k in ("names_row", "msg_row")} if ayni else {}
    return {k: med(v) for k, v in ra.items()}, {k: med(v) for k, v in rb.items()}, ortak


def main():
    arg = sys.argv[1:]
    ters = "--ters" in arg
    beklenen = int(arg[arg.index("--beklenen") + 1]) if "--beklenen" in arg else None
    eski, yeni, dizin, cik = [x for x in arg if not x.startswith("--") and not (beklenen is not None and x == str(beklenen))][:4]
    eski_k = str(Path(cik).with_name("_yd_video_eski_kiyas.py"))
    hazirla_eski(eski, eski_k)
    if ters:   # bilinen fark: yeni surumun kopyasinda sign_a / sign_b yer degistirir
        yeni_t = str(Path(cik).with_name("_yd_video_ters.py"))
        s = Path(yeni).read_text(encoding="utf-8")
        k = "self.sign_a, self.sign_b = self._union(left), self._union(right)"
        assert s.count(k) == 1, "ters kontrol: hedef satir yok"
        Path(yeni_t).write_text(s.replace(k, "self.sign_a, self.sign_b = self._union(right), self._union(left)"), encoding="utf-8")
        yeni = yeni_t
    kapaklar = sorted(Path(dizin).glob("*_Y01.jpg"))
    satir, fark, hata = [], [], []
    for n, k in enumerate(kapaklar, 1):
        c = k.name[:-len("_Y01.jpg")]
        a, ea = kos(eski_k, str(k), f"/tmp/_ka_{c}.json")
        b, eb = kos(yeni, str(k), f"/tmp/_kb_{c}.json")
        d = dict(cift=c, eski=a, yeni=b, eski_hata=ea, yeni_hata=eb)
        if b is None:
            hata.append(c); d["durum"] = "YENI_HATA"
        elif a is None:
            d["durum"] = "ONCE_HATA_SIMDI_TAMAM"
        else:
            df = [x for x in ANAHTAR if list(a[x]) != list(b[x])]
            d["fark"] = df; d["merged_fark"] = list(a["merged"]) != list(b["merged"])
            d["durum"] = "FARK" if df or d["merged_fark"] else "AYNI"
            if df or d["merged_fark"]:
                fark.append(c)
        satir.append(d)
        print(f"[{n}/{len(kapaklar)}] {c}: {d['durum']}" + (f" {d.get('fark')}" if d.get("fark") else ""), flush=True)
    sayi_tamam = beklenen is None or len(kapaklar) == beklenen
    if ters:
        bulunamayan = [d["cift"] for d in satir if d["durum"] != "FARK" and d["cift"].split("_")[0] != d["cift"].split("_")[1]]
        ozet = dict(mod="ters", toplam=len(satir), fark_bulunan=len(fark), fark_bulunamayan=bulunamayan, sayi_tamam=sayi_tamam)
        json.dump(dict(ozet=ozet, ciftler=satir), open(cik, "w"), indent=1)
        print("OZET", json.dumps(ozet))
        return 0 if (not bulunamayan and fark and sayi_tamam) else 1
    ra, rb, ortak = referans(satir)
    sapma, ref_fail = {}, []
    for d in satir:
        if not d["yeni"]:
            continue
        a, b = d["cift"].split("_")
        ref = dict(sign_a=ra.get(a), sign_b=rb.get(b), **ortak)
        m = {k: (max(abs(x - y) for x, y in zip(d["yeni"][k], ref[k])) if ref.get(k) else None) for k in ANAHTAR}
        d["referans"] = ref; d["referans_fark"] = m
        sapma[d["cift"]] = max(v for v in m.values() if v is not None)
        if d["durum"] == "ONCE_HATA_SIMDI_TAMAM" and (any(v is None for v in m.values()) or max(m.values()) > REF_PAY):
            ref_fail.append(d["cift"])
    ozet = dict(toplam=len(satir), beklenen=beklenen, sayi_tamam=sayi_tamam, ayni=sum(d["durum"] == "AYNI" for d in satir), fark=fark,
                yeni_hata=hata, once_hata_simdi_tamam=[d["cift"] for d in satir if d["durum"] == "ONCE_HATA_SIMDI_TAMAM"],
                once_hata_referans_fark={d["cift"]: d.get("referans_fark") for d in satir if d["durum"] == "ONCE_HATA_SIMDI_TAMAM"},
                referans_fail=ref_fail, ref_pay=REF_PAY,
                tum_ciftler_en_buyuk_referans_sapma=sorted(sapma.items(), key=lambda x: -x[1])[:5])
    json.dump(dict(ozet=ozet, ciftler=satir), open(cik, "w"), indent=1)
    print("OZET", json.dumps(ozet))
    return 1 if fark or hata or ref_fail or not sayi_tamam else 0


if __name__ == "__main__":
    sys.exit(main())
