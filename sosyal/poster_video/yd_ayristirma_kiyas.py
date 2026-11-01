#!/usr/bin/env python3
"""Denetim 20261101D: yd_video.py ayristirma kiyasi (duzeltme oncesi / sonrasi). Her kapak icin iki surum YD_AYRISTIR_JSON ile kosulur
(video uretilmez); sign_a, sign_b, names_row, msg_row kutulari BIREBIR karsilastirilir (merged = ortak sembol kutusu, ayrica yazilir).
Eski surum main'deki dosyadir; ayni JSON dokumu bu betik tarafindan eski dosyanin kopyasina eklenir (eski davranis degismez).
Kullanim: yd_ayristirma_kiyas.py <eski_yd_video.py> <yeni_yd_video.py> <kapak_dizini> <cikti.json>
Cikis kodu: 0 = beklenen disi fark yok (yalniz onceden hata veren ciftler degisebilir), 1 = fark var / yeni surumde hata."""
import json
import os
import subprocess
import sys
from pathlib import Path

ANAHTAR = ("sign_a", "sign_b", "names_row", "msg_row")
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


def main():
    eski, yeni, dizin, cik = sys.argv[1:5]
    eski_k = str(Path(cik).with_name("_yd_video_eski_kiyas.py"))
    hazirla_eski(eski, eski_k)
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
    ozet = dict(toplam=len(satir), ayni=sum(d["durum"] == "AYNI" for d in satir), fark=fark, yeni_hata=hata,
                once_hata_simdi_tamam=[d["cift"] for d in satir if d["durum"] == "ONCE_HATA_SIMDI_TAMAM"])
    json.dump(dict(ozet=ozet, ciftler=satir), open(cik, "w"), indent=1)
    print("OZET", json.dumps(ozet))
    return 1 if fark or hata else 0


if __name__ == "__main__":
    sys.exit(main())
