#!/usr/bin/env python3
"""Eski 78 poster (Print, Hahnemuhle Photo Rag GLOBAL-HPR-<boy>) dunya kargo + net (SALT OKUMA, 15 Eki 2026, Serdar EK).
Yalniz POST /v4.0/quotes (siparis OLUSTURMAZ). Etsy cagrisi YOK.
13 boy x 16 ulke (AU + "everywhere else" ornekleri). Yanittaki tum yontemler; takip sinifi tasiyici adindan:
  'untrack'/'untrak' -> takipsiz; 'track', courier/express (DHL, FedEx (P2P degil), UPS, DPD, ECI, Australia Post Express) -> takipli;
  digerleri -> belirsiz. En ucuz TAKIPLI (yoksa en ucuz belirsiz, isaretli) secilir.
Net = fiyat + F - (0.698 + 0.2062 x (fiyat + F)) - (urun + kargo + vergi)  [Etsy kesintisi KDV dahil, docs/REFERANS_ILAN_CL.md].
Paket eki (kartpostal + sticker, 5 USD) DAHIL DEGIL (ayri sutun: net - 5).
Secenek a: everywhere else tek ucret X: (1) en buyuk boyda (24x36) tum ulkelerde net >= 0 icin en kucuk tam dolar X;
  (2) tum boy x ulke net >= 0 icin X; her X'te 8x10 net (en kotu ulke).
Cikti: DUNYA_BOY.csv (her teklif satiri), DUNYA_BOY_NET.md (boy x ulke net tablosu + secenekler) -> TEMP/PRODIGI/DUNYA_BOY_20261015/
"""
import argparse
import csv
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_maliyet_api import ayikla  # noqa: E402
from prodigi_pilot_quote import Api, leak_check, load_key, log  # noqa: E402

# canli eski CL envanteri (cerceve denetimi 15 Eki): Print fiyatlari
FIYAT = {"8x10": 47, "A4": 48, "11x14": 51, "12x16": 53, "A3": 56, "12x18": 57, "16x20": 60, "16x24": 61, "A2": 62,
         "18x24": 66, "20x30": 84, "24x30": 94, "24x36": 109}
ULKE = ["AU", "CA", "TR", "JP", "MX", "BR", "ZA", "IL", "NZ", "KR", "SG", "HK", "AE", "IN", "NO", "CH"]
SABIT, ORAN = 0.698, 0.2062


def takip(ad):
    a = (ad or "").lower()
    if "untrack" in a or "untrak" in a:
        return "takipsiz"
    if "track" in a or any(k in a for k in ("dhl", "ups ", "dpd", "eci", "express", "courier")) or ("fedex" in a and "p2p" not in a):
        return "takipli"
    return "belirsiz"


def tasiyicilar(q):
    out = {}
    for qu in (q or {}).get("quotes") or []:
        y = (qu.get("shipmentMethod") or "").replace(" ", "").lower()
        c = [f"{(sh.get('carrier') or {}).get('name', '')} {(sh.get('carrier') or {}).get('service', '')}".strip() for sh in qu.get("shipments") or []]
        out[y] = " / ".join(dict.fromkeys(x for x in c if x))
    return out


def net(fiyat, maliyet, f=0.0):
    return round(fiyat + f - (SABIT + ORAN * (fiyat + f)) - maliyet, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    isler = [(b, u) for b in FIYAT for u in ULKE]

    def sor(it):
        b, u = it
        q, err = api.quote(f"GLOBAL-HPR-{b}", {}, dest=u)
        return b, u, q, err
    rows, sec = [], {}
    with ThreadPoolExecutor(6) as ex:
        for i, (b, u, q, err) in enumerate(ex.map(sor, isler), 1):
            m = ayikla(q) if q else {}
            tc = tasiyicilar(q)
            aday = []
            for y, v in m.items():
                if None in (v["urun"], v["kargo"]):
                    continue
                mal = round(v["urun"] + v["kargo"] + (v["vergi"] or 0), 2)
                t = takip(tc.get(y, ""))
                rows.append(dict(boy=b, ulke=u, yontem=y, urun=v["urun"], kargo=v["kargo"], vergi=v["vergi"] or 0, maliyet=mal,
                                 tasiyici=tc.get(y, ""), takip=t, lab=v["lab"], hata=""))
                aday.append((0 if t == "takipli" else 1 if t == "belirsiz" else 2, mal, y, t, tc.get(y, "")))
            if not m:
                rows.append(dict(boy=b, ulke=u, yontem="", hata=err))
            secilen = sorted(x for x in aday if x[0] < 2)
            if secilen:
                sec[(b, u)] = secilen[0]
            if i % 40 == 0:
                log(f"{i}/{len(isler)} | %{i / len(isler) * 100:.0f}")
    with open(out / "DUNYA_BOY.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["boy", "ulke", "yontem", "urun", "kargo", "vergi", "maliyet", "tasiyici", "takip", "lab", "hata"], restval="")
        w.writeheader(); w.writerows(rows)

    md = ["# Eski 78 Print: boy x ulke NET (ucretsiz kargo, F=0) | en ucuz takipli kargo (b = takip belirsiz) | paket eki haric",
          "", "| boy | fiyat | " + " | ".join(ULKE) + " |", "|---|---|" + "---|" * len(ULKE)]
    for b, p in FIYAT.items():
        h = []
        for u in ULKE:
            s = sec.get((b, u))
            h.append("-" if not s else f"{net(p, s[1])}{'b' if s[3] == 'belirsiz' else ''}")
        md.append(f"| {b} | {p} | " + " | ".join(h) + " |")
    md += ["", "## Maliyet (urun + en ucuz takipli kargo + vergi)", "", "| boy | " + " | ".join(ULKE) + " |", "|---|" + "---|" * len(ULKE)]
    for b in FIYAT:
        md.append(f"| {b} | " + " | ".join(str(sec[(b, u)][1]) if (b, u) in sec else "-" for u in ULKE) + " |")

    ew = [u for u in ULKE if u != "AU"]

    def en_kucuk_x(boylar, ulkeler, hedef=0.0):
        need = 0.0
        for b in boylar:
            for u in ulkeler:
                if (b, u) in sec:
                    n0 = net(FIYAT[b], sec[(b, u)][1])
                    if n0 < hedef:
                        need = max(need, (hedef - n0) / (1 - ORAN))
        return math.ceil(need)
    sonuc = {}
    for ad, boylar, hedef in (("24x36_net0", ["24x36"], 0), ("tum_boy_net0", list(FIYAT), 0), ("tum_boy_net5", list(FIYAT), 5),
                              ("18x24_alti_net0", [b for b in FIYAT if FIYAT[b] < 66], 0)):
        x = en_kucuk_x(boylar, ew, hedef)
        k8 = min((net(47, sec[("8x10", u)][1], x), u) for u in ew if ("8x10", u) in sec)
        b8 = max((net(47, sec[("8x10", u)][1], x), u) for u in ew if ("8x10", u) in sec)
        kb = min((net(FIYAT[b], sec[(b, u)][1], x), b, u) for b in FIYAT for u in ew if (b, u) in sec)
        sonuc[ad] = dict(X=x, net_8x10_en_kotu=k8, net_8x10_en_iyi=b8, en_kotu_boy_ulke=kb)
    au = {b: net(p, sec[(b, "AU")][1]) for b, p in FIYAT.items() if (b, "AU") in sec}
    au_x = en_kucuk_x(list(FIYAT), ["AU"], 0)
    md += ["", "## Secenek a: everywhere else tek ucret X (AU haric)", ""]
    for ad, v in sonuc.items():
        md.append(f"- {ad}: X = {v['X']} USD | 8x10 net en kotu {v['net_8x10_en_kotu']} en iyi {v['net_8x10_en_iyi']} | en kotu boy/ulke {v['en_kotu_boy_ulke']}")
    md += [f"- AU ucretsiz net: {au}", f"- AU tum boylarda net >= 0 icin X = {au_x}",
           f"- eksik teklif (boy, ulke): {[k for k in isler if k not in sec]}"]
    (out / "DUNYA_BOY_NET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "DUNYA_BOY_SECENEK.json").write_text(json.dumps(dict(secenek=sonuc, au=au, au_x=au_x), indent=1, default=str))
    leak_check(out)
    print("\n".join(md))
    print(f"::warning::DUNYA BOY | teklif {len(isler)} | secilen {len(sec)} | " + " | ".join(f"{k} X={v['X']}" for k, v in sonuc.items()))


if __name__ == "__main__":
    main()
