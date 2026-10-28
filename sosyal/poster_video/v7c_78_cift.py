#!/usr/bin/env python3
"""v7c 78 toplu uretim, cift satiri (Merkez 28 Eki; Serdar 3 ornegi gorsel onayladi). Etsy yok.
Kullanim: v7c_78_cift.py <poster_video_v7.py> <kapak.jpg> <yeni.mp4> <eski.mp4> <uretim.log> <QC.json> <out> <CIFT> <deneme>
Yazar: <out>/satir/<CIFT>.json, <out>/kare/<CIFT>_04.jpg ve _07.jpg (0,4 / 0,7 sn tam kare, 1440x1080).
Satir: QC kapilari (7) ve degerleri; uretim logundan silme_d ve 30 px varsayilani; eski video (BIRLESIK) ile kare sayisi / sure;
isim ve mesaj kutularinda (poster_video_v7 ayristirmasi, pay yok) yeni ile eski video arasindaki kare basina ortalama mutlak fark
(0-255; 0. kare = kodlama tabani, en buyuk kare ve 0,4 sn) ile son karede kutu ici yeni - kapak farki. Esik yok: bu alanlar inceleme icin olculur."""
import json
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_qc as Q  # noqa: E402
import v7_silme_artik as SA  # noqa: E402

KARELER = (0.4, 0.7)


def main():
    pv, kapak, yeni, eski, log, qcj, out, cift, deneme = sys.argv[1:10]
    os.makedirs(f"{out}/satir", exist_ok=True); os.makedirs(f"{out}/kare", exist_ok=True)
    q = json.load(open(qcj)) if os.path.exists(qcj) else {}
    K = q.get("kontrol") or {}
    lg = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
    m = re.search(r"silme: sembol maskesi (\d+) px \+ yakin altin (\d+) px .*sembole < (\d+) px", lg)
    s = dict(cift=cift, sonuc=q.get("sonuc", "FAIL"), deneme=int(deneme),
             kapilar={k: bool(v.get("gecti")) for k, v in K.items()},
             gecen=sum(1 for v in K.values() if v.get("gecti")), kapi_sayisi=len(K),
             silme_d=int(m.group(3)) if m else None, varsayilan_30="VARSAYILAN: bos bant yok" in lg,
             sembol_px=int(m.group(1)) if m else None, yakin_altin_px=int(m.group(2)) if m else None)
    g = lambda k, a: (K.get(k) or {}).get("deger", {}).get(a)
    s.update(artik=g("silme_artik", "artik"), fazla_max=g("silme_artik", "fazla_max"), zemin_max=g("silme_artik", "zemin_max"),
             hayalet=g("silinme_hayalet", "fark_R_B"), ihlal=g("c_ihlal", "ihlal_en_buyuk"),
             ilk_fark=g("b_ilk_son_kare", "ilk"), son_fark=g("b_ilk_son_kare", "son"), b_esik=g("b_ilk_son_kare", "esik"))
    if os.path.exists(yeni):
        F, p = Q.kareler(yeni)
        s.update(yeni_kare=p["kare"], yeni_sure=p["sure_sn"], yeni_olcu=p["olcu"], yeni_mb=p["boyut_mb"])
        for t in KARELER:
            Image.fromarray(F[int(round(t * 30))]).save(f"{out}/kare/{cift}_{str(t).replace('0.', '0')}.jpg", quality=92)
        if os.path.exists(eski):
            E, pe = Q.kareler(eski)
            s.update(eski_kare=pe["kare"], eski_sure=pe["sure_sn"], eski_olcu=pe["olcu"])
            gs = SA.ayristir(pv, kapak)
            kap = np.asarray(Image.open(kapak).convert("RGB"))
            kapv = cv2.resize(kap, (F.shape[2], F.shape[1]), interpolation=cv2.INTER_AREA).astype(np.float32)
            for ad, kt in (("isim", ("names_row",)), ("mesaj", ("msg_row",))):
                km = SA.kutu_maske(gs, kt)
                n = min(len(F), len(E))
                d = [float(np.abs(F[i][km].astype(np.float32) - E[i][km].astype(np.float32)).mean()) for i in range(n)]
                i4 = int(round(0.4 * 30))
                s[f"{ad}_kutu_px"] = int(km.sum())
                s[f"{ad}_eski_fark_max"] = round(max(d), 3); s[f"{ad}_eski_fark_max_kare"] = int(np.argmax(d))
                s[f"{ad}_eski_fark_0"] = round(d[0], 3)   # 0. kare iki videoda da kapak: kodlama gurultusu tabani
                s[f"{ad}_eski_fark_04"] = round(d[i4], 3); s[f"{ad}_eski_fark_ort"] = round(float(np.mean(d)), 3)
                s[f"{ad}_son_kapak_fark"] = round(float(np.abs(F[-1][km].astype(np.float32) - kapv[km]).mean()), 3)
    json.dump(s, open(f"{out}/satir/{cift}.json", "w"), ensure_ascii=False)
    print("SATIR", json.dumps(s, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
