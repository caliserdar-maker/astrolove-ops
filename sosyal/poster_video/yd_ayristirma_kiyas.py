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


def referans(satir, yerlesim=None):
    """AYNI ciftlerden burca gore medyan kutular. yerlesim verilirse yalniz ayni alt yerlesimdeki (names_row kutusu ayni) ciftler
    (inceleme E bulgu 3: 78 kapakta iki alt yerlesim var, medyan karisiyordu); o yerlesimde hic AYNI cift yoksa tumu."""
    import numpy as np
    ayni = [d for d in satir if d["durum"] == "AYNI"]
    if yerlesim is not None and any(list(d["yeni"]["names_row"]) == list(yerlesim) for d in ayni):
        ayni = [d for d in ayni if list(d["yeni"]["names_row"]) == list(yerlesim)]
    ra, rb = {}, {}
    for d in ayni:
        a, b = d["cift"].split("_")
        ra.setdefault(a, []).append(d["yeni"]["sign_a"]); rb.setdefault(b, []).append(d["yeni"]["sign_b"])
    med = lambda L: [int(round(v)) for v in np.median(np.array(L), 0)]  # noqa: E731
    ortak = {k: med([d["yeni"][k] for d in ayni]) for k in ("names_row", "msg_row")} if ayni else {}
    return {k: med(v) for k, v in ra.items()}, {k: med(v) for k, v in rb.items()}, ortak


def main():
    arg = sys.argv[1:]
    if "--oztest" in arg:
        return oztest()
    ters = "--ters" in arg or "--ters-kapi" in arg
    ters_kapi = "--ters-kapi" in arg          # aralik kapisi ACIK: yer degisimi "YD kapi" hatasi olarak yakalanmali
    beklenen = int(arg[arg.index("--beklenen") + 1]) if "--beklenen" in arg else None
    liste = Path(arg[arg.index("--beklenen-liste") + 1]).read_text().split() if "--beklenen-liste" in arg else None
    deger = {str(beklenen)} | ({arg[arg.index("--beklenen-liste") + 1]} if liste is not None else set())
    eski, yeni, dizin, cik = [x for x in arg if not x.startswith("--") and x not in deger][:4]
    eski_k = str(Path(cik).with_name("_yd_video_eski_kiyas.py"))
    hazirla_eski(eski, eski_k)
    if ters:   # bilinen fark: yeni surumun kopyasinda sign_a / sign_b yer degistirir
        yeni_t = str(Path(cik).with_name("_yd_video_ters.py"))
        s = Path(yeni).read_text(encoding="utf-8")
        k = "self.sign_a, self.sign_b = self._union(left), self._union(right)"
        assert s.count(k) == 1, "ters kontrol: hedef satir yok"
        s = s.replace(k, "self.sign_a, self.sign_b = self._union(right), self._union(left)")
        if not ters_kapi:
            assert s.count("KUTU_PAY = 15") == 1 and s.count("YERLESIM_PAY = 5") == 1, "ters kontrol: kapi satirlari yok"
            s = s.replace("KUTU_PAY = 15", "KUTU_PAY = 10 ** 6").replace("YERLESIM_PAY = 5", "YERLESIM_PAY = 10 ** 6")  # kapi kapali: farki kiyas yakalamali
        Path(yeni_t).write_text(s, encoding="utf-8")
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
    sayi_tamam = (beklenen is None or len(kapaklar) == beklenen) and (liste is None or sorted(liste) == sorted(d["cift"] for d in satir))
    if ters:
        if ters_kapi:
            bulunamayan = [d["cift"] for d in satir if not (d["durum"] == "YENI_HATA" and "YD kapi" in " ".join(d["yeni_hata"] or []))]
        else:
            bulunamayan = [d["cift"] for d in satir if d["durum"] != "FARK" and d["cift"].split("_")[0] != d["cift"].split("_")[1]]
        ozet = dict(mod="ters_kapi" if ters_kapi else "ters", toplam=len(satir), fark_bulunan=len(fark), fark_bulunamayan=bulunamayan, sayi_tamam=sayi_tamam)
        json.dump(dict(ozet=ozet, ciftler=satir), open(cik, "w"), indent=1)
        print("OZET", json.dumps(ozet))
        return 0 if (not bulunamayan and (fark or ters_kapi) and sayi_tamam) else 1
    sapma, ref_fail = {}, []
    for d in satir:
        if not d["yeni"]:
            continue
        ra, rb, ortak = referans(satir, d["yeni"]["names_row"])
        ga, gb, _ = referans(satir)              # alt yerlesimde ayni burc yoksa tum yerlesimler (kaynak d["referans_kaynak"])
        a, b = d["cift"].split("_")
        ref = dict(sign_a=ra.get(a) or ga.get(a), sign_b=rb.get(b) or gb.get(b), **ortak)
        d["referans_kaynak"] = dict(sign_a="alt_yerlesim" if ra.get(a) else "tum", sign_b="alt_yerlesim" if rb.get(b) else "tum")
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


def oztest():
    """referans kapisinin sentetik oz testi (inceleme E bulgu 2c): AYNI ciftler + bir ONCE_HATA cifti; kutu 7 px kayinca
    referans_fail, 3 px kayinca gecer olmali."""
    ref = dict(sign_a=[546, 1616, 191, 188], sign_b=[1281, 1615, 187, 189], names_row=[457, 1867, 1126, 108], msg_row=[692, 2090, 629, 310])
    def satirlar(kay):
        S = [dict(cift=f"LIBRA_{b}", durum="AYNI", yeni=dict(ref)) for b in ("PISCES", "VIRGO")]
        S += [dict(cift=f"{a}_LIBRA", durum="AYNI", yeni=dict(ref)) for a in ("AQUARIUS", "CANCER")]
        y = {k: list(v) for k, v in ref.items()}; y["sign_a"][0] += kay
        return S + [dict(cift="LIBRA_LIBRA", durum="ONCE_HATA_SIMDI_TAMAM", yeni=y)]
    sonuc = {}
    for kay in (3, 7):
        S = satirlar(kay); ra, rb, ortak = referans(S, S[-1]["yeni"]["names_row"])
        m = max(max(abs(x - z) for x, z in zip(S[-1]["yeni"][k], dict(sign_a=ra["LIBRA"], sign_b=rb["LIBRA"], **ortak)[k])) for k in ANAHTAR)
        sonuc[kay] = m > REF_PAY
    print("OZTEST", json.dumps({"3px_fail": sonuc[3], "7px_fail": sonuc[7]}))
    return 0 if (not sonuc[3] and sonuc[7]) else 1


if __name__ == "__main__":
    sys.exit(main())
