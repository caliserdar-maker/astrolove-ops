#!/usr/bin/env python3
"""78 kupa ilani: hedef EN + RU aciklama (ru_kupa.kur), Serdar 31 Eki karar 3b. ETSY YOK, YAZIM YOK.
Girdi --canli: kupa-yd-oku KUPA_CANLI.json (Etsy salt okuma: listing_id, cift, state, description, ru).
Cikti --out: KUPA_RU_78.csv (cift, listing_id, state, en_degisim, durum, hata, paragraf), KUPA_RU_78.json (en_canli, en_hedef,
ru_yeni, ru_canli), ORNEK_YANYANA.html (--ornek ciftleri, paragraf paragraf EN | RU), OZET.md. Cikis 0 yalniz 78/78 PASS."""
import argparse
import csv
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ru_kupa as R  # noqa: E402


def yanyana(kayitlar):
    h = ["<html><head><meta charset='utf-8'><title>Kupa EN RU ornek</title></head><body>",
         "<h1>Kupa aciklamasi: hedef EN ve yeni RU (yan yana)</h1>",
         "<p>Kaynak: canli EN (Etsy salt okuma, kupa-yd-oku). RU: scripts/etsy/ru_kupa.py. Etsy'ye yazilmadi; "
         "Serdar ve Lena onayi bekler.</p>"]
    for k in kayitlar:
        en = [p for p in k["en_hedef"].split("\n\n") if p.strip()]
        ru = [p for p in k["ru_yeni"].split("\n\n") if p.strip()]
        h.append(f"<h2>{html.escape(k['cift'])} (ilan {html.escape(k['listing_id'])}; EN degisim: {k['en_degisim']}; "
                 f"kontrol {k['durum']})</h2>")
        h.append("<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%'><tr><th>#</th><th>EN</th><th>RU</th></tr>")
        for i in range(max(len(en), len(ru))):
            e = html.escape(en[i] if i < len(en) else "").replace("\n", "<br>")
            r = html.escape(ru[i] if i < len(ru) else "").replace("\n", "<br>")
            h.append(f"<tr><td>{i + 1}</td><td style='width:48%;vertical-align:top'>{e}</td>"
                     f"<td style='width:48%;vertical-align:top'>{r}</td></tr>")
        h.append("</table>")
    h.append("</body></html>")
    return "\n".join(h)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--canli", required=True)
    ap.add_argument("--ornek", default="CANCER_LIBRA,LEO_LEO")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    canli = json.loads(open(a.canli, encoding="utf-8").read())
    satir, tam = [], []
    for x in sorted(canli, key=lambda y: y["cift"]):
        c = x["cift"]
        try:
            b1, b2 = (s.title() for s in c.split("_"))
        except ValueError:
            b1 = b2 = None
        hata = []
        if not b1:
            hata.append(f"cift adi {c!r}")
            en, deg, ru, kon = R.norm(x.get("description")), "?", "", dict(pass_=False, hata=[], paragraf_en=0, paragraf_ru=0)
        else:
            en, deg = R.kupa_en(x.get("description"), b1, b2)
            if b1 == b2 and deg == "YOK":
                hata.append("ayni burc: isim satiri cevrilemedi (Left / Right ya da Name Under bulunmadi)")
            ru, kon = R.kur(en)
            if kon.get("burc") != [b1, b2]:
                hata.append(f"EN burclari {kon.get('burc')} != cift {c}")
        if x.get("state") != "active":
            hata.append(f"state {x.get('state')}")
        hata += kon["hata"]
        durum = "PASS" if kon["pass_"] and not hata else "FAIL"
        satir.append(dict(cift=c, listing_id=x["listing_id"], state=x.get("state"), en_degisim=deg, durum=durum,
                          paragraf=f"{kon['paragraf_en']}/{kon['paragraf_ru']}", hata=" | ".join(hata)))
        tam.append(dict(cift=c, listing_id=x["listing_id"], en_degisim=deg, durum=durum, en_canli=R.norm(x.get("description")),
                        en_hedef=en, ru_yeni=ru, ru_canli=R.norm((x.get("ru") or {}).get("description"))))
    with open(out / "KUPA_RU_78.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0])); w.writeheader(); w.writerows(satir)
    (out / "KUPA_RU_78.json").write_text(json.dumps(tam, ensure_ascii=False, indent=1), encoding="utf-8")
    sec = [t for t in tam if t["cift"] in a.ornek.split(",")]
    (out / "ORNEK_YANYANA.html").write_text(yanyana(sec), encoding="utf-8")
    n_pass = sum(s["durum"] == "PASS" for s in satir)
    ayni = [s for s in satir if s["cift"].split("_")[0] == s["cift"].split("_")[-1]]
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Kupa RU aciklama 78 (Etsy'ye yazilmadi)\n\nkaynak: {a.canli} (kupa-yd-oku, Etsy salt okuma)\n"
                f"ilan {len(satir)} | PASS {n_pass} | FAIL {len(satir) - n_pass} | ayni burc {len(ayni)} "
                f"(EN isim satiri DEGISTI {sum(s['en_degisim'] == 'DEGISTI' for s in ayni)})\n"
                f"RU canliyla ayni: {sum(t['ru_yeni'] == t['ru_canli'] for t in tam)} / {len(tam)}\n\n")
        for s in satir:
            if s["durum"] != "PASS":
                f.write(f"- FAIL {s['cift']}: {s['hata']}\n")
        f.write("\nAyni burcta hedef EN: isim satirlari Left name / Right name -> First Name / Second Name (Serdar 30 Eki). "
                "EN ve RU yazimi Serdar + Lena onayindan sonra, ayri onayla.\n")
    print(f"KUPA RU 78: PASS {n_pass}/{len(satir)}")
    return 0 if n_pass == len(satir) == 78 else 1


if __name__ == "__main__":
    sys.exit(main())
