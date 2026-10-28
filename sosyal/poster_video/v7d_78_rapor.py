#!/usr/bin/env python3
"""v7d 78 toplu uretim raporu (Merkez 28 Eki). Girdi: v7d_78_cift.py ciktilari (satir/<CIFT>.json, kontrol/<CIFT>.jpg).
Kullanim: v7d_78_rapor.py --satir DIR --kontrol DIR --out DIR
Cikti: QC.csv (78 satir, 9 kapi + mesaj_isim ayrintisi + eski TAM78 dogruluk testi), OZET.md, KONTROL_<n>.jpg (13 cift / sayfa)."""
import argparse
import csv
import json
from pathlib import Path

from PIL import Image

ON19 = ["AQUARIUS_CAPRICORN", "AQUARIUS_GEMINI", "AQUARIUS_PISCES", "AQUARIUS_VIRGO", "ARIES_GEMINI", "ARIES_LIBRA", "ARIES_SAGITTARIUS",
        "ARIES_TAURUS", "AQUARIUS_CANCER", "AQUARIUS_TAURUS", "ARIES_CAPRICORN", "ARIES_PISCES", "ARIES_SCORPIO", "ARIES_VIRGO",
        "ARIES_SCORPIO", "CANCER_SAGITTARIUS", "CAPRICORN_CAPRICORN", "CAPRICORN_SAGITTARIUS", "LIBRA_SAGITTARIUS"]   # Merkez listesi (ARIES_SCORPIO iki kez)
KAPI = ["a_bicim", "b_ilk_son_kare", "c_ihlal", "d_kutu_orani", "silinme_hayalet", "silme_artik", "silme_halka_ici", "mesaj_isim", "e_kontak"]
ALAN = ["cift", "sonuc", "deneme", "gecen", "kapi_sayisi"] + KAPI + [
    "artik", "halka_artik", "hayalet", "motor_bant", "motor_murekkep_px", "motor_parca", "mesaj_bant", "mesaj_murekkep_px", "a_piksel",
    "a_bant_fazla_max", "a_hayalet", "a_sol", "a_pencere", "a_kapsam_disi", "b_taban", "b_en_buyuk", "b_asan", "b_sicrama", "b_sicrama_asan", "c_ham", "c_isim_taban", "c_isim_en_buyuk", "c_isim_asan", "c_sign_a_taban",
    "c_sign_a_en_buyuk", "c_sign_a_asan", "c_sign_b_taban", "c_sign_b_en_buyuk", "c_sign_b_asan", "eski_a_gecti", "eski_a_piksel"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--satir", required=True); ap.add_argument("--kontrol", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
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
    num = lambda k: [r[k] for r in rows if isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool)]
    mx = lambda k: max(num(k)) if num(k) else None
    eski_olc = [r for r in rows if r.get("eski_a_gecti") is not None]
    eski_pass = [r["cift"] for r in eski_olc if r["eski_a_gecti"]]
    on19 = sorted(set(ON19))
    on19_pass = [c for c in on19 if any(r["cift"] == c and r.get("eski_a_gecti") for r in rows)]
    on19_yok = [c for c in on19 if not any(r["cift"] == c and r.get("eski_a_gecti") is not None for r in rows)]
    md = ["# Poster video v7d: mesaj tam silme, 78 toplu uretim", "",
          f"PASS {say['PASS']} / 78 | FAIL {say['FAIL']} | eksik {say['EKSIK']}",
          f"- 2. denemede PASS: {', '.join(r['cift'] for r in rows if r.get('deneme') == 2 and r['sonuc'] == 'PASS') or 'yok'}",
          f"- PASS olmayan: {', '.join(r['cift'] + ' ' + r['sonuc'] + ' (' + ','.join(k for k in KAPI if r.get(k) is False) + ')' for r in rows if r['sonuc'] != 'PASS') or 'yok'}",
          f"- DOGRULUK TESTI (eski TAM78 videolari, mesaj_isim a): olculen {len(eski_olc)}, FAIL {len(eski_olc) - len(eski_pass)}, PASS {len(eski_pass)} {eski_pass or ''}",
          f"- Merkez listesi ({len(ON19)} kayit, {len(on19)} farkli cift; ARIES_SCORPIO iki kez): PASS veren {on19_pass or 'yok'}; olculemeyen {on19_yok or 'yok'}"
          + ("  -> KAPI HATALI, DUR" if on19_pass else ""),
          f"- yeni mesaj_isim: a en cok piksel {mx('a_piksel')}, a bant |fazla| en buyuk {mx('a_bant_fazla_max')} (leke esigi 25); "
          f"hayalet ort en buyuk {mx('a_hayalet')} (esik 3); cephe solu fark en buyuk {mx('a_sol')}, pencere {mx('a_pencere')} (esik 10); "
          f"kapsam disi px en cok {mx('a_kapsam_disi')}; b (kare 149 - kapak) asan piksel en cok {mx('b_asan')}, 149->150 sicrama en buyuk "
          f"{mx('b_sicrama')}; c ham kutu farki en buyuk {mx('c_ham')}; c asan piksel en cok "
          f"{max([mx('c_isim_asan') or 0, mx('c_sign_a_asan') or 0, mx('c_sign_b_asan') or 0])}",
          f"- c en buyuk - taban (kodlama payi 10): isim {max([r['c_isim_en_buyuk'] - r['c_isim_taban'] for r in rows if isinstance(r.get('c_isim_taban'), int)], default=None)}, "
          f"sol glif {max([r['c_sign_a_en_buyuk'] - r['c_sign_a_taban'] for r in rows if isinstance(r.get('c_sign_a_taban'), int)], default=None)}, "
          f"sag glif {max([r['c_sign_b_en_buyuk'] - r['c_sign_b_taban'] for r in rows if isinstance(r.get('c_sign_b_taban'), int)], default=None)}",
          f"- sembol kalintisi (silme_artik) en buyuk {mx('artik')}; halka ici en buyuk {mx('halka_artik')}",
          f"- motor mesaj murekkebi px: en kucuk {min(num('motor_murekkep_px'), default=None)}, en buyuk {mx('motor_murekkep_px')}"]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    kd = Path(a.kontrol)
    ks = [kd / f"{r['cift']}.jpg" for r in rows if (kd / f"{r['cift']}.jpg").exists()]
    for n in range(0, len(ks), 13):
        ims = [Image.open(p).convert("RGB") for p in ks[n:n + 13]]
        ims = [i.resize((int(i.width * 0.6), int(i.height * 0.6)), Image.LANCZOS) for i in ims]
        W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
        pg = Image.new("RGB", (W, H), (255, 255, 255)); y = 0
        for i in ims:
            pg.paste(i, (0, y)); y += i.height + 6
        pg.save(out / f"KONTROL_{n // 13 + 1}.jpg", quality=85)
    print("\n".join(md))
    return 0 if say["PASS"] == 78 and not on19_pass and not on19_yok else 1


if __name__ == "__main__":
    raise SystemExit(main())
