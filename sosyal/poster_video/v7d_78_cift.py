#!/usr/bin/env python3
"""v7d 78 toplu uretim, cift satiri (Merkez 28 Eki: mesaj tam silinir, soldan saga yazilir; Etsy yok).
Kullanim: v7d_78_cift.py <video.mp4> <QC.json> <eski_test.json|-> <uretim.log> <out> <CIFT> <deneme>
Yazar: <out>/satir/<CIFT>.json (9 kapi + mesaj_isim ayrintisi + eski TAM78 dogruluk testi) ve <out>/kontrol/<CIFT>.jpg:
isim + mesaj bandi yakin plani (video olcegi 2x), 0 / 0,25 / 0,4 sn, yazimin ortasi (cephe mesajin ortasinda) ve son kare."""
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_mesaj_qc as MQ  # noqa: E402
import v7_qc as Q  # noqa: E402


def font(n):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", n)
    except OSError:
        return ImageFont.load_default()


def main():
    v, qcj, eskij, log, out, c, deneme = sys.argv[1:8]
    os.makedirs(f"{out}/satir", exist_ok=True); os.makedirs(f"{out}/kontrol", exist_ok=True)
    q = json.load(open(qcj)) if os.path.exists(qcj) else {}
    K = q.get("kontrol") or {}
    s = dict(cift=c, sonuc=q.get("sonuc", "FAIL"), deneme=int(deneme), kapilar={k: bool(x.get("gecti")) for k, x in K.items()},
             gecen=sum(1 for x in K.values() if x.get("gecti")), kapi_sayisi=len(K))
    g = lambda k, a: (K.get(k) or {}).get("deger", {}).get(a)
    s.update(artik=g("silme_artik", "artik"), halka_artik=g("silme_halka_ici", "artik"), hayalet=g("silinme_hayalet", "fark_R_B"))
    mq = (K.get("mesaj_isim") or {}).get("deger", {})
    if mq:
        s.update(mesaj_bant=mq.get("bant"), mesaj_murekkep_px=mq.get("murekkep_px"), a_piksel=mq.get("a", {}).get("en_cok_piksel"),
                 a_bant_fazla_max=mq.get("a", {}).get("sag_bant_fazla_max"), b_taban=mq.get("b", {}).get("taban"),
                 b_en_buyuk=mq.get("b", {}).get("en_buyuk"), b_asan=mq.get("b", {}).get("asan_piksel"),
                 c_ham=(mq.get("c") or {}).get("ham_kutu_fark_max"))
        for k in ("isim", "sign_a", "sign_b"):
            x = (mq.get("c") or {}).get(k) or {}
            s.update({f"c_{k}_taban": x.get("taban"), f"c_{k}_en_buyuk": x.get("en_buyuk"), f"c_{k}_asan": x.get("asan_piksel")})
    lg = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
    m = re.search(r"^mesaj: bant \[([\d, ]+)\].*murekkep (\d+) px, (\d+) parca", lg, re.M)
    if m:
        s.update(motor_bant=m.group(1), motor_murekkep_px=int(m.group(2)), motor_parca=int(m.group(3)))
    if eskij != "-" and os.path.exists(eskij):
        e = json.load(open(eskij))["deger"]
        s.update(eski_a_gecti=e.get("a_gecti"), eski_a_piksel=e.get("a", {}).get("en_cok_piksel"))
    if os.path.exists(v) and os.path.exists(v + ".ic.json"):
        F, _ = Q.kareler(v); ic = json.load(open(v + ".ic.json")); d, y = ic["donusum"], ic["yazim"]
        ix0, iy0, ix1, _ = MQ.kutu_v(d, y["isim_poster"])
        b = mq.get("bant") or [ix0, iy0, ix1, iy0 + 60]
        x0, y0, x1, y1 = min(ix0, b[0]) - 12, iy0 - 10, max(ix1, b[2]) + 12, b[3] + 10
        ort = int(round((y["nB"] - 1) * 0.5))   # ease(0,5) = 0,5: cephe mesajin ortasinda
        kr = [(0, "0 sn"), (int(round(0.25 * 30)), "0,25 sn"), (int(round(0.4 * 30)), "0,4 sn"), (ort, f"yazim ortasi {ort / 30:.1f} sn".replace(".", ",")),
              (len(F) - 1, "son kare")]
        w, h = (x1 - x0) * 2, (y1 - y0) * 2
        im = Image.new("RGB", (len(kr) * (w + 6), h + 60), (255, 255, 255)); dr = ImageDraw.Draw(im)
        dr.text((4, 2), f"{c}  {s['sonuc']}  mesaj a {s.get('a_piksel')} px | eski TAM78 a {'PASS' if s.get('eski_a_gecti') else 'FAIL'} "
                f"({s.get('eski_a_piksel')} px)", fill=(0, 0, 0) if s["sonuc"] == "PASS" else (200, 0, 0), font=font(18))
        for j, (i, ad) in enumerate(kr):
            dr.text((j * (w + 6) + 4, 30), ad, fill=(0, 0, 0), font=font(16))
            im.paste(Image.fromarray(F[i][y0:y1, x0:x1]).resize((w, h), Image.LANCZOS), (j * (w + 6), 54))
        im.save(f"{out}/kontrol/{c}.jpg", quality=88)
    json.dump(s, open(f"{out}/satir/{c}.json", "w"), ensure_ascii=False)
    print("SATIR", json.dumps(s, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
