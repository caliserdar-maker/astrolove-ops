#!/usr/bin/env python3
"""Kanada cerceveli zarar secenekleri RAPORU (SALT OKUMA; Etsy'ye/Prodigi'ye yazma yok, yalniz GET + POST /quotes).
Fiyatlar: CL canli envanteri (tur x boy tekil; .99 -> tam yuvarlanmis YENI fiyat). Net = fiyat - (0.698 + 0.2062 x fiyat) - maliyet.
 a) Prodigi CA kargo yontemleri (Budget/Standard/Express/Overnight) canli /quotes: cerceveli (4 renk) + baski, net tablo.
 b) Etsy kargo profili CA ek ucreti S: cerceveli net >= 0 icin gereken S (boy basina ve tek duz tutar, en ucuz yontemle);
    S'nin CA baski netine etkisi (S x 0.7938 eklenir; Etsy kesintisi kargo dahil tutara).
 c) CA kargo profilinden cikarilirsa: CA satis 0 (kayip = son 90 gun CA siparisleri).
 Son 90 gun CA siparis sayisi (Etsy receipts; yalniz ulke + POD/dijital sayimi; kisisel veri yazilmaz).
Kullanim: kanada_rapor.py --out OUT
"""
import argparse
import math
import os
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/pod")); sys.path.insert(0, str(KOK / "scripts/prodigi")); sys.path.insert(0, str(KOK / "scripts/etsy"))
import fiyat_kar as F  # noqa: E402

YONTEMLER = ["Budget", "Standard", "Express", "Overnight"]
ORAN = 1 - F.UCRET_ORAN


def net(fiyat, maliyet):
    return round(fiyat - F.ucret(fiyat) - maliyet, 2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--listing", default="4570143815")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    # fiyatlar (CL canli)
    fiy = {}
    for p in (api.get(f"/listings/{a.listing}/inventory") or {}).get("products") or []:
        tur, boy = F.tur_boy(p.get("sku"))
        o = [o for o in p.get("offerings") or [] if not o.get("is_deleted")]
        if tur and o:
            e = F.K.money(o[0]["price"]) if hasattr(F, "K") else round(float(o[0]["price"]["amount"]) / float(o[0]["price"]["divisor"]), 2)
            fiy[(tur, boy)] = F.yeni_fiyat(e) or e
    boylar = sorted({b for _, b in fiy}, key=lambda b: (b.startswith("A"), -int(b[1]) if b.startswith("A") else int(b.split("x")[0]) * int(b.split("x")[1])))
    # maliyetler: yontem x (baski, cerceve siyah) -- cerceve 4 renk ayni fiyat (27 Eyl katalog) -> siyah temsil
    M = F.Maliyet()
    ek = M.R.EKLER_USD
    mal = {}
    for y in YONTEMLER:
        M.prod.shipping_method = y
        for tur in ("PRINT", "FBK"):
            for b in boylar:
                item = {"prodigi_sku": M.sku("HPR" if tur == "PRINT" else "CFP", b), "qty": 1,
                        "attributes": {} if tur == "PRINT" else M.cer[(b, "BK")]["attributes"]}
                c, h = M.teklif(item, "CA")
                mal[(y, tur, b)] = c
    # siparisler (son 90 gun)
    t0 = int(time.time()) - 90 * 86400
    say = {"toplam": 0, "CA": 0, "CA_pod": 0, "CA_dijital": 0}
    off = 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"min_created": t0, "limit": 100, "offset": off}) or {}
        R = d.get("results") or []
        for r in R:
            say["toplam"] += 1
            if (r.get("country_iso") or "").upper() == "CA":
                say["CA"] += 1
                skus = [t.get("sku") or "" for t in r.get("transactions") or []]
                if any(x.startswith("POD-") and not x.endswith("-DIGITAL") for x in skus):
                    say["CA_pod"] += 1
                else:
                    say["CA_dijital"] += 1
        off += len(R)
        if len(R) < 100 or off >= 2000:
            break
    # rapor
    md = [f"# KANADA CERCEVELI ZARAR SECENEKLERI (salt okuma) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "",
          f"- Fiyatlar: CL canli envanteri, .99 -> tam YENI fiyat. Net = fiyat - (0.698 + 0.2062 x fiyat) - Prodigi (urun + kargo + ekler {ek:.2f}).",
          f"- Son 90 gun siparis: toplam {say['toplam']} | Kanada {say['CA']} (POD fiziksel {say['CA_pod']}, dijital/diger {say['CA_dijital']})",
          "", "## a) Prodigi CA kargo yontemleri (canli /quotes) - net kar", ""]
    md += ["| tur | boy | fiyat | " + " | ".join(f"{y} maliyet / net" for y in YONTEMLER) + " |", "|---|---|---|" + "---|" * len(YONTEMLER)]
    for tur, ad in (("FBK", "cerceveli"), ("PRINT", "baski")):
        for b in boylar:
            p = fiy.get((tur, b))
            if p is None:
                continue
            md.append(f"| {ad} | {b} | {p:.2f} | " + " | ".join(
                (f"{mal[(y, tur, b)]:.2f} / {net(p, mal[(y, tur, b)]):.2f}" if mal.get((y, tur, b)) is not None else "yok") for y in YONTEMLER) + " |")
    # b) ek ucret
    en_ucuz = {(tur, b): min([(mal[(y, tur, b)], y) for y in YONTEMLER if mal.get((y, tur, b)) is not None], default=(None, None))
               for tur in ("FBK", "PRINT") for b in boylar}
    gerek = {}
    for b in boylar:
        c, y = en_ucuz[("FBK", b)]
        p = fiy.get(("FBK", b))
        if c is None or p is None:
            continue
        gerek[b] = max(0.0, (c + F.UCRET_SABIT) / ORAN - p)
    duz = math.ceil(max(gerek.values())) if gerek else 0
    md += ["", "## b) Etsy kargo profili: Kanada'ya ek ucret", "",
           "Etsy kesintisi kargo dahil tutara uygulanir (0.2062); ek ucret S icin net artisi = S x 0.7938. Ayni kargo profili baski ve cerceveliyi "
           "birlikte kapsar (ilan basina tek profil), S ikisine de eklenir.", "",
           "| boy | cerceveli fiyat | en ucuz yontem | gereken S (net=0) |", "|---|---|---|---|"]
    md += [f"| {b} | {fiy[('FBK', b)]:.2f} | {en_ucuz[('FBK', b)][1]} {en_ucuz[('FBK', b)][0]:.2f} | {gerek[b]:.2f} |" for b in boylar if b in gerek]
    md += ["", f"- Tek duz CA ek ucreti (tum cerceveliler net >= 0): **{duz} USD**", "",
           f"| boy | baski fiyat | baski net (en ucuz yontem) | + S={duz} ile baski net | cerceveli net + S |", "|---|---|---|---|---|"]
    for b in boylar:
        cp, yp = en_ucuz[("PRINT", b)]
        cf, _ = en_ucuz[("FBK", b)]
        pp, pf = fiy.get(("PRINT", b)), fiy.get(("FBK", b))
        if None in (cp, cf, pp, pf):
            continue
        np_, nf = net(pp, cp), net(pf, cf)
        md.append(f"| {b} | {pp:.2f} | {np_:.2f} ({yp}) | {np_ + duz * ORAN:.2f} | {nf + duz * ORAN:.2f} |")
    md += ["", "## c) Kanada'yi kargo profilinden cikarmak", "",
           f"- CA'ya fiziksel satis kapanir: CA net 0 (zarar da kar da yok). Son 90 gunde CA POD fiziksel siparis: {say['CA_pod']}; "
           f"dijital CA satislari etkilenmez (kargo profili yok).",
           f"- Kayip: CA baski siparislerinin net kari (yukaridaki 'baski net' sutunu; siparis basina ~{min(net(fiy[('PRINT', b)], en_ucuz[('PRINT', b)][0]) for b in boylar if fiy.get(('PRINT', b)) and en_ucuz[('PRINT', b)][0]):.2f}"
           f"-{max(net(fiy[('PRINT', b)], en_ucuz[('PRINT', b)][0]) for b in boylar if fiy.get(('PRINT', b)) and en_ucuz[('PRINT', b)][0]):.2f} USD).",
           "", f"- Etsy API cagrisi {api.calls} | kota son {api.remaining} | Prodigi yalniz GET /products + POST /quotes"]
    (out / "KANADA.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:5]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
