#!/usr/bin/env python3
"""v7c 78 toplu uretim raporu (Merkez 28 Eki). Girdi: v7c_78_cift.py ciktilari (satir/<CIFT>.json, kare/<CIFT>_04.jpg / _07.jpg).
Kullanim: v7c_78_rapor.py --satir DIR --kare DIR --out DIR
Cikti: QC.csv (78 satir, tum kapilar ve olcumler), OZET.md, KONTAK_04_<n>.jpg (her ciftin 0,4 sn karesi, 20 cift / sayfa),
ZOR5.jpg + ZOR5.md (ZOR ciftlerin kalinti degeri, 0,4 ve 0,7 sn tam kare + poster merkezi), VARSAYILAN30.txt (bos bant bulunamayan,
silme_d 30 px varsayilani kullanilan ciftler)."""
import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ZOR = ["ARIES_SCORPIO", "CANCER_SAGITTARIUS", "LIBRA_SAGITTARIUS", "CAPRICORN_CAPRICORN", "CAPRICORN_SAGITTARIUS"]
KAPI = ["a_bicim", "b_ilk_son_kare", "c_ihlal", "d_kutu_orani", "silinme_hayalet", "silme_artik", "e_kontak"]
ALAN = ["cift", "sonuc", "deneme", "gecen", "kapi_sayisi"] + KAPI + [
    "artik", "fazla_max", "zemin_max", "silme_d", "varsayilan_30", "sembol_px", "yakin_altin_px", "hayalet", "ihlal", "ilk_fark",
    "son_fark", "b_esik", "yeni_kare", "eski_kare", "yeni_sure", "eski_sure", "yeni_olcu", "eski_olcu", "yeni_mb",
    "isim_kutu_px", "isim_eski_fark_0", "isim_eski_fark_04", "isim_eski_fark_max", "isim_eski_fark_max_kare", "isim_eski_fark_ort",
    "isim_son_kapak_fark", "mesaj_kutu_px", "mesaj_eski_fark_0", "mesaj_eski_fark_04", "mesaj_eski_fark_max",
    "mesaj_eski_fark_max_kare", "mesaj_eski_fark_ort", "mesaj_son_kapak_fark"]


def font(n):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", n)
    except OSError:
        return ImageFont.load_default()


def merkez(im):
    w, h = im.size   # poster merkezi (sembol), 4:3 (v7_silme_olc78.serit ile ayni kirpim)
    return im.crop((int(w * 0.30), int(h * 0.32), int(w * 0.70), int(h * 0.72)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--satir", required=True); ap.add_argument("--kare", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); kd = Path(a.kare)
    kok = Path(__file__).resolve().parents[2]
    tum = sorted(r["cift"] for r in csv.DictReader(open(kok / "data/pod/pod78_ids.csv")))
    S = {}
    for p in sorted(Path(a.satir).glob("*.json")):
        s = json.loads(p.read_text()); S[s["cift"]] = s
    rows = []
    for c in tum:
        s = dict(S.get(c) or dict(cift=c, sonuc="EKSIK"))
        for k in KAPI:
            s[k] = (s.get("kapilar") or {}).get(k, "")
        rows.append(s)
    with open(out / "QC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN, extrasaction="ignore"); w.writeheader(); w.writerows({k: r.get(k, "") for k in ALAN} for r in rows)
    say = {k: sum(1 for r in rows if r["sonuc"] == k) for k in ("PASS", "FAIL", "EKSIK")}
    v30 = [r["cift"] for r in rows if r.get("varsayilan_30")]
    (out / "VARSAYILAN30.txt").write_text("".join(c + "\n" for c in v30))
    kare_fark = [r["cift"] for r in rows if r["sonuc"] != "EKSIK" and (r.get("yeni_kare") != r.get("eski_kare") or r.get("yeni_sure") != r.get("eski_sure"))]
    mx = lambda k: max((r.get(k) for r in rows if isinstance(r.get(k), (int, float))), default=None)
    md = ["# Poster video v7c: 78 toplu uretim", "",
          f"PASS {say['PASS']} / 78 | FAIL {say['FAIL']} | eksik {say['EKSIK']}",
          f"- 2. denemede PASS: {', '.join(r['cift'] for r in rows if r.get('deneme') == 2 and r['sonuc'] == 'PASS') or 'yok'}",
          f"- PASS olmayan: {', '.join(r['cift'] + ' ' + r['sonuc'] + ' (' + ','.join(k for k in KAPI if r.get(k) is False) + ')' for r in rows if r['sonuc'] != 'PASS') or 'yok'}",
          f"- kalinti (silme_artik, esik R-B fazlasi > 15): artik > 0 olan {sum(1 for r in rows if (r.get('artik') or 0) > 0)}; fazla_max en buyuk {mx('fazla_max')}; zemin_max en buyuk {mx('zemin_max')}",
          f"- 30 px varsayilani (bos bant yok): {len(v30)} cift: {', '.join(v30) or 'yok'}",
          f"- kare sayisi / sure eski videodan farkli: {', '.join(kare_fark) or 'yok'} (yeni kare {sorted({r['yeni_kare'] for r in rows if r.get('yeni_kare') is not None})}, sure {sorted({r['yeni_sure'] for r in rows if r.get('yeni_sure') is not None})})",
          f"- isim kutusu yeni-eski fark (0-255) en buyuk {mx('isim_eski_fark_max')}, 0. kare tabani en buyuk {mx('isim_eski_fark_0')}; "
          f"mesaj kutusu en buyuk {mx('mesaj_eski_fark_max')}, taban en buyuk {mx('mesaj_eski_fark_0')}", "",
          "## Zor ciftler", "| cift | sonuc | artik | fazla_max | zemin_max | silme_d | varsayilan 30 | yakin altin px |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['cift']} | {r['sonuc']} | {r.get('artik')} | {r.get('fazla_max')} | {r.get('zemin_max')} | {r.get('silme_d')} | "
           f"{r.get('varsayilan_30')} | {r.get('yakin_altin_px')} |" for r in rows if r["cift"] in ZOR]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "ZOR5.md").write_text("\n".join(md[md.index("## Zor ciftler"):]) + "\n", encoding="utf-8")
    fn, fk = font(22), font(18)
    tw, th, ust = 480, 360, 30
    for n in range(0, len(rows), 20):
        grup = rows[n:n + 20]
        im = Image.new("RGB", (5 * (tw + 6), 4 * (th + ust)), (245, 245, 245)); d = ImageDraw.Draw(im)
        for i, r in enumerate(grup):
            x, y = (i % 5) * (tw + 6), (i // 5) * (th + ust)
            ok = r["sonuc"] == "PASS"
            d.text((x + 4, y + 4), f"{r['cift']} {r['sonuc']} artik {r.get('artik')}", fill=(0, 0, 0) if ok else (200, 0, 0), font=fk)
            p = kd / f"{r['cift']}_04.jpg"
            if p.exists():
                im.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y + ust))
        im.save(out / f"KONTAK_04_{n // 20 + 1}.jpg", quality=88)
    zr = [r for r in rows if r["cift"] in ZOR]
    im = Image.new("RGB", (4 * (tw + 6), len(zr) * (th + 2 * ust)), (245, 245, 245)); d = ImageDraw.Draw(im)
    for j, r in enumerate(zr):
        y = j * (th + 2 * ust)
        d.text((4, y + 4), f"{r['cift']} {r['sonuc']} | artik {r.get('artik')} fazla_max {r.get('fazla_max')} zemin_max {r.get('zemin_max')} "
               f"silme_d {r.get('silme_d')}", fill=(0, 0, 0), font=fn)
        for i, (t, kes) in enumerate([("04", False), ("04", True), ("07", False), ("07", True)]):
            x = i * (tw + 6)
            d.text((x + 4, y + ust + 2), f"{t[0]},{t[1]} sn" + (" merkez" if kes else ""), fill=(0, 0, 0), font=fk)
            p = kd / f"{r['cift']}_{t}.jpg"
            if p.exists():
                k = Image.open(p).convert("RGB")
                im.paste((merkez(k) if kes else k).resize((tw, th - ust), Image.LANCZOS), (x, y + 2 * ust))
    im.save(out / "ZOR5.jpg", quality=90)
    print("\n".join(md[:9]))
    return 0 if say["PASS"] == 78 else 1


if __name__ == "__main__":
    raise SystemExit(main())
