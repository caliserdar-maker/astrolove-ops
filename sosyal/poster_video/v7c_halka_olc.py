#!/usr/bin/env python3
"""v7c 78 dogrulama (inceleme 28 Eki bulgu 1 ve 3). Etsy yok.
Cift basina (yeni = TAM78, eski = BIRLESIK): 0,4 sn karesinde v7_silme_artik.halka_ici (maskeden bagimsiz halka ici kalinti; poster
kutusu TAM78 uretim logundan, eski video icin ayni kapak); isim ve mesaj SATIR BANDI (poster kutusu genisligi, satir kutusu y +-6 px)
icinde yeni - eski kare basina ortalama mutlak fark (0-255) dizisinin 0. kare (kodlama tabani), 0,4 sn ve en buyuk degeri.
Kullanim: v7c_halka_olc.py <poster_video_v7.py> <kapak.jpg> <yeni.mp4> <eski.mp4> <yeni_uretim.log> <out_dir> <CIFT>  -> <out>/<CIFT>.json"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_qc as Q  # noqa: E402
import v7_silme_artik as SA  # noqa: E402


def main():
    pv, kapak, yeni, eski, log, out, c = sys.argv[1:8]
    os.makedirs(out, exist_ok=True)
    F, _ = Q.kareler(yeni); E, _ = Q.kareler(eski)
    pk = SA.poster_kutusu(log, Image.open(kapak).size[0], F.shape[2])
    i4 = int(round(SA.KARE_SN * 30))
    R = dict(cift=c, poster_kutusu=pk,
             yeni=SA.halka_ici(F[i4].astype(np.float32), pk), eski=SA.halka_ici(E[i4].astype(np.float32), pk))
    g = SA.ayristir(pv, kapak)
    n = min(len(F), len(E))
    for ad, k in (("isim", "names_row"), ("mesaj", "msg_row")):
        km = SA.kutu_maske(g, (k,))
        ys = np.where(km.any(1))[0]
        bant = np.zeros(km.shape, bool)
        bant[max(0, ys.min() - 6):ys.max() + 7, pk[0]:pk[2]] = True
        d = [float(np.abs(F[i][bant].astype(np.float32) - E[i][bant].astype(np.float32)).mean()) for i in range(n)]
        R[ad] = dict(bant_y=[int(max(0, ys.min() - 6)), int(ys.max() + 6)], px=int(bant.sum()), fark_0=round(d[0], 3),
                     fark_04=round(d[i4], 3), fark_max=round(max(d), 3), fark_max_kare=int(np.argmax(d)))
    json.dump(R, open(f"{out}/{c}.json", "w"))
    print(c, "halka yeni", R["yeni"].get("artik"), R["yeni"].get("fazla_max"), "eski", R["eski"].get("artik"),
          "| isim", R["isim"]["fark_0"], R["isim"]["fark_max"], "| mesaj", R["mesaj"]["fark_0"], R["mesaj"]["fark_max"], flush=True)


if __name__ == "__main__":
    main()
