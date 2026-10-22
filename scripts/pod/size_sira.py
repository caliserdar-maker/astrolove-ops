#!/usr/bin/env python3
"""78 POD ilaninda Size menusu SIRASI (Serdar genel onayi 28 Eyl 2026). Yalniz products dizisinin sirasi degisir.
Hedef sira: 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36, A4, A3, A2
(once inc boylari ucuzdan pahaliya, sonra A serisi ucuzdan pahaliya).

  --mod kuru : SALT OKUMA (ilan basina 1 envanter GET). Her ilanda: canli Size degerleri = hedef 13 boy mu; Print
               fiyatlari (her boyda renkler arasi ayni) hedef sirada inc ve A serisi icinde azalmiyor mu. Uymayan -> DUR/rapor.
  --mod yaz  : ETSY'YE YAZAR (--confirm SIZESIRA). Ilan basina: tam okuma (listing, envanter, renk-gorsel, gorsel, video,
               kisisellestirme, nitelik) -> state active degilse dokunulmaz -> kuru kontroller -> YEDEK (yerel + --yedek-drive
               ile Drive'a, dogrulanir) -> PUT envanter (ayni urunler, ayni SKU/fiyat/stok/readiness, yalniz sira) ->
               geri okuma: urun imzasi birebir, *_on_property ayni, Size ilk gorulme sirasi = hedef, Format ve Color sirasi
               ayni -> renk-gorsel baglari degistiyse ayni gorsellere yeniden baglanir -> son tam okuma: baslik, etiket, state,
               gorseller, video, kisisellestirme, nitelikler, ayar alanlari ayni. Ilk FAIL'de DUR. Kota tabaninda temiz dur.
Siralama: urunlerin mevcut ic ice duzeni (hangi ozellik yavas/hizli degisiyor) korunur; yalniz Size indeksi hedefle degisir.
Kullanim: size_sira.py --mod kuru|yaz --out OUT [--yalniz id,id] [--haric id,id] [--confirm SIZESIRA] [--yedek-drive gdrive:...]
          [--ilerleme ILERLEME.json]
"""
import argparse
import csv
import itertools
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/pod")); sys.path.insert(0, str(KOK / "scripts/etsy"))
import ayar77_kuru as K  # noqa: E402
import ayar77_yaz as Y  # noqa: E402
import fiyat_kar as F  # noqa: E402

HEDEF = ["8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x30", "24x36", "A4", "A3", "A2"]
INC, ASERI = HEDEF[:10], HEDEF[10:]
KOTA_TABAN = 150
CL_ID = "4570143815"
MALIYET = None
FIYAT_RX = re.compile(r"(\$ ?\d+(?:\.\d{2})?|\b\d+\.99\b|\bUSD ?\d+|\b\d+ ?USD\b)")


def maliyet():
    global MALIYET
    if MALIYET is None:
        MALIYET = F.Maliyet()
    return MALIYET


def fiyat_donustur(inv):
    """.99 fiyatlari asagi yuvarlanmis kopya (beklenen envanter)."""
    import copy
    x = copy.deepcopy(inv)
    for p in x.get("products") or []:
        for o in p.get("offerings") or []:
            eski = K.money(o.get("price"))
            y = F.yeni_fiyat(eski)
            if y is not None:
                o["price"] = {"amount": int(round(y * 100)), "divisor": 100, "currency_code": "USD"}
    return x


def log(m):
    print(m, flush=True)


def boy_kodu(deger):
    t = str(deger or "").replace("×", "x").replace("X", "x")
    m = re.search(r"\b(A[2-4])\b", t)
    if m:
        return m.group(1)
    m = re.search(r"(\d+)[\s\"'″]*x[\s\"'″]*(\d+)", t)
    return f"{m.group(1)}x{m.group(2)}" if m else None


def ozellik_adlari(inv):
    """{rol: property_id} rol = size (adinda 'size') | color (200 / adinda 'color') | format (kalan tek ozellik)."""
    pids = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            pids.setdefault(v.get("property_id"), (v.get("property_name") or "").lower())
    rol = {}
    for pid, ad in pids.items():
        if "size" in ad:
            rol["size"] = pid
        elif pid == Y.RENK_PID or "color" in ad or "colour" in ad:
            rol["color"] = pid
    kalan = [pid for pid in pids if pid not in rol.values()]
    if len(kalan) == 1:
        rol["format"] = kalan[0]
    return rol


def deger(p, pid):
    for v in p.get("property_values") or []:
        if v.get("property_id") == pid:
            return (v.get("values") or [""])[0]
    return None


def ilk_sira(inv, pid):
    s = []
    for p in inv.get("products") or []:
        d = deger(p, pid)
        if d is not None and d not in s:
            s.append(d)
    return s


def fiyat(p):
    o = [o for o in p.get("offerings") or [] if not o.get("is_deleted")]
    return K.money(o[0].get("price")) if o else None


def kontrol(inv):
    """-> (sorunlar, bilgi). Boy kumesi + Print fiyat sirasi."""
    rol = ozellik_adlari(inv)
    if set(rol) != {"size", "format", "color"}:
        return [f"ozellikler bulunamadi: {rol}"], {}
    sz = ilk_sira(inv, rol["size"])
    kod = {d: boy_kodu(d) for d in sz}
    sorun = []
    if sorted(kod.values(), key=str) != sorted(HEDEF) or len(set(kod.values())) != len(sz):
        sorun.append(f"Size degerleri hedef 13 boy degil: {sz}")
        return sorun, {"size": sz}
    fiy = {}
    for p in inv.get("products") or []:
        if "print" in str(deger(p, rol["format"]) or "").lower() and "frame" not in str(deger(p, rol["format"])).lower():
            fiy.setdefault(kod[deger(p, rol["size"])], set()).add(fiyat(p))
    if sorted(fiy) != sorted(HEDEF):
        sorun.append(f"Print fiyati olmayan boy: {sorted(set(HEDEF) - set(fiy))}")
        return sorun, {"size": sz}
    cok = {b: sorted(v) for b, v in fiy.items() if len(v) != 1}
    if cok:
        sorun.append(f"Print fiyati renklere gore farkli: {cok}")
    f1 = {b: min(v) for b, v in fiy.items()}
    esit = []
    for grup in (INC, ASERI):
        for x, y in zip(grup, grup[1:]):
            if f1[y] < f1[x]:
                sorun.append(f"fiyat sirasi bozuk: {x} {f1[x]} > {y} {f1[y]}")
            elif f1[y] == f1[x]:
                esit.append(f"{x}={y} {f1[x]}")
    return sorun, {"size": sz, "kod": kod, "print": f1, "esit": esit, "rol": rol}


def yeni_sira(inv, rol, kod):
    """Mevcut ic ice duzeni bulur (orijinal sira hangi ozellik permutasyonuyla sozluk sirali), Size'i hedefle degistirir."""
    P = inv.get("products") or []
    pids = [rol["format"], rol["color"], rol["size"]]
    once = {pid: {d: i for i, d in enumerate(ilk_sira(inv, pid))} for pid in pids}
    hedef_i = {d: HEDEF.index(k) for d, k in kod.items()}
    duzen = None
    for perm in itertools.permutations(pids):
        anah = [tuple(once[q][deger(p, q)] for q in perm) for p in P]
        if anah == sorted(anah):
            duzen = perm; break
    if duzen is None:
        raise SystemExit("HATA: mevcut urun sirasi hicbir ozellik duzenine uymuyor; guvenli yeniden siralama yok. DUR.")
    idx = {q: (hedef_i if q == rol["size"] else once[q]) for q in pids}
    return sorted(P, key=lambda p: tuple(idx[q][deger(p, q)] for q in duzen)), duzen


def put_govdesi(inv, urunler, fiyat99=False):
    """Canli envanter -> PUT govdesi (ayni SKU/fiyat/stok/etkin/readiness; renk value_ids korunur)."""
    out = []
    for p in urunler:
        pvs = []
        for pv in p.get("property_values") or []:
            x = {"property_id": pv.get("property_id"), "property_name": pv.get("property_name"), "values": list(pv.get("values") or [])}
            if pv.get("scale_id") is not None:
                x["scale_id"] = pv["scale_id"]
            if pv.get("property_id") == Y.RENK_PID and pv.get("value_ids"):
                x["value_ids"] = list(pv["value_ids"])
            pvs.append(x)
        offs = []
        for o in p.get("offerings") or []:
            if o.get("is_deleted"):
                continue
            f = K.money(o.get("price"))
            f = (F.yeni_fiyat(f) or f) if fiyat99 else f
            y = {"price": f, "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id") is not None:
                y["readiness_state_id"] = o["readiness_state_id"]
            offs.append(y)
        out.append({"sku": p.get("sku") or "", "property_values": pvs, "offerings": offs})
    g = {"products": out}
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if inv.get(k) is not None:
            g[k] = list(inv[k])
    return g


def drive_yedek(yerel, hedef):
    r = subprocess.run(["rclone", "copyto", str(yerel), hedef], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"HATA: yedek Drive'a yazilamadi ({hedef}): {r.stderr[:200]}. YAZMA YOK. DUR.")
    r = subprocess.run(["rclone", "size", "--json", hedef], capture_output=True, text=True)
    if r.returncode != 0 or json.loads(r.stdout or "{}").get("bytes") != Path(yerel).stat().st_size:
        raise SystemExit(f"HATA: Drive yedegi dogrulanamadi ({hedef}). YAZMA YOK. DUR.")


def ilan_yaz(api, shop, lid, out, yedek_drive, fiyat99=False):
    S0 = Y.oku(api, shop, lid)
    if S0["listing"].get("state") != "active":
        return "ATLANDI", f"state={S0['listing'].get('state')} (active degil, dokunulmadi)"
    inv0 = S0["inventory"]
    sorun, b = kontrol(inv0)
    if sorun:
        return "FAIL", "; ".join(sorun)
    fiy_not = ""
    if fiyat99:
        kalem, dok, ks = F.envanter_kar(inv0, maliyet())
        if ks:
            return "FAIL", "kar kapisi: " + "; ".join(ks[:5]) + (f" (+{len(ks) - 5})" if len(ks) > 5 else "")
        n99 = sum(1 for t, bo, e, y, k in kalem if y != e)
        fiy_not = f"; .99 -> tam: {n99} fiyat" + (f"; .99 olmayan (dokunulmadi) {len(dok)}" if dok else "")
    beklenen = fiyat_donustur(inv0) if fiyat99 else inv0
    if ilk_sira(inv0, b["rol"]["size"]) == sorted(b["kod"], key=lambda d: HEDEF.index(b["kod"][d])) \
            and K.imza(beklenen) == K.imza(inv0):
        return "ZATEN", "Size sirasi zaten hedef" + (", .99 fiyat yok" if fiyat99 else "")
    urunler, duzen = yeni_sira(inv0, b["rol"], b["kod"])
    govde = put_govdesi(inv0, urunler, fiyat99)
    yd = Path(out) / "YEDEK"; yd.mkdir(parents=True, exist_ok=True)
    (yd / f"{lid}.json").write_text(json.dumps(S0, ensure_ascii=False, indent=1, default=str))
    if yedek_drive:
        drive_yedek(yd / f"{lid}.json", f"{yedek_drive}/{lid}.json")
    sabit0, rg0 = Y.sabit_imza(S0), Y.renk_gorsel(inv0, S0["variation_images"])
    fmt0, col0 = ilk_sira(inv0, b["rol"]["format"]), ilk_sira(inv0, b["rol"]["color"])
    hedef_sz = sorted(b["kod"], key=lambda d: HEDEF.index(b["kod"][d]))
    try:
        api.put_json(f"/listings/{lid}/inventory?max_variations_supported=3", govde)
    except SystemExit as e:
        return "FAIL", f"envanter PUT reddedildi (ilan degismedi): {str(e)[:200]}"

    def inv_ok(x):
        return K.imza(x) == K.imza(beklenen) and ilk_sira(x, b["rol"]["size"]) == hedef_sz
    inv1 = Y.kararli(lambda: api.get(f"/listings/{lid}/inventory") or {}, inv_ok)
    sorun = []
    if K.imza(inv1) != K.imza(beklenen):
        sorun.append("urun imzasi (fiyat/SKU/stok/etkin/readiness)")
    if K.on_prop(inv1) != K.on_prop(inv0):
        sorun.append("*_on_property")
    if ilk_sira(inv1, b["rol"]["size"]) != hedef_sz:
        sorun.append(f"Size sirasi {ilk_sira(inv1, b['rol']['size'])}")
    if ilk_sira(inv1, b["rol"]["format"]) != fmt0:
        sorun.append("Format sirasi")
    if ilk_sira(inv1, b["rol"]["color"]) != col0:
        sorun.append("Color sirasi")
    if sorun:
        return "FAIL", f"envanter geri okuma: {sorun}"
    rg1 = Y.renk_gorsel(inv1, (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [])
    yeniden = rg1 != rg0
    if yeniden:
        rp = Y.renk_propu(inv1)
        istek = [{"property_id": Y.RENK_PID, "value_id": rp[r]["value_ids"][0], "image_id": int(img)} for r, img in rg0.items() if r in rp]
        if len(istek) != len(rg0):
            return "FAIL", f"renk-gorsel eslemesi kurulamadi ({len(istek)}/{len(rg0)})"
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
    S2 = Y.kararli(lambda: Y.oku(api, shop, lid),
                   lambda s: Y.renk_gorsel(s["inventory"], s["variation_images"]) == rg0 and inv_ok(s["inventory"]))
    sorun = []
    if Y.renk_gorsel(S2["inventory"], S2["variation_images"]) != rg0:
        sorun.append("renk-gorsel baglari")
    if not inv_ok(S2["inventory"]):
        sorun.append("envanter (son okuma)")
    s2 = Y.sabit_imza(S2)
    sorun += [f"degisti:{k}" for k in sabit0 if sabit0[k] != s2[k]]
    (Path(out) / "SONRA").mkdir(parents=True, exist_ok=True)
    (Path(out) / "SONRA" / f"{lid}.json").write_text(json.dumps(S2, ensure_ascii=False, indent=1, default=str))
    if sorun:
        return "FAIL", f"son geri okuma: {sorun}"
    return "YAZILDI", (f"Size sirasi hedefte (duzen {'>'.join(str(q) for q in duzen)}), {len(govde['products'])} urun birebir, "
                       f"renk-gorsel {'yeniden baglandi' if yeniden else 'korundu'}, sabitler ayni"
                       + (f"; esit fiyat {b['esit']}" if b["esit"] else "") + fiy_not)


def metin_fiyat(api, shop, ids):
    """Aciklamalarda (batch) ve magaza metinlerinde fiyat gecen yerler (salt okuma, 2 cagri)."""
    import html
    sat = []
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            for m in FIYAT_RX.finditer(html.unescape(x.get("description") or "")):
                t = html.unescape(x.get("description") or "")
                sat.append(f"- ilan {x.get('listing_id')}: '{m.group(0)}' ... {t[max(0, m.start() - 40):m.end() + 40]!r}")
    S = api.get(f"/shops/{shop}") or {}
    for k in ("announcement", "sale_message", "digital_sale_message", "policy_welcome", "policy_payment", "policy_shipping",
              "policy_refunds", "policy_additional", "title"):
        for m in FIYAT_RX.finditer(str(S.get(k) or "")):
            sat.append(f"- magaza {k}: '{m.group(0)}'")
    return sat or ["- yok (78 aciklama + magaza metinleri)"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["kuru", "yaz"]); ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--yalniz", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--confirm", default=""); ap.add_argument("--yedek-drive", default="")
    ap.add_argument("--ilerleme", default=""); ap.add_argument("--kota-taban", type=int, default=KOTA_TABAN)
    ap.add_argument("--fiyat99", action="store_true", help=".99 fiyatlari ayni yazimda asagi yuvarla (kar kapisi ile)")
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    if yaz and a.confirm != "SIZESIRA":
        raise SystemExit("HATA: --mod yaz icin --confirm SIZESIRA gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    if len(rows) != 78:
        raise SystemExit(f"HATA: 78 hedef bekleniyordu ({len(rows)}). DUR.")
    rows.sort(key=lambda r: r["listing_id"] != CL_ID)          # once CL
    if a.yalniz:
        rows = [r for r in rows if r["listing_id"] in a.yalniz.split(",")]
    if a.haric:
        rows = [r for r in rows if r["listing_id"] not in a.haric.split(",")]
    R = json.loads(Path(a.ilerleme).read_text()) if yaz and a.ilerleme and Path(a.ilerleme).exists() else {"ilanlar": {}}
    kalan = [r for r in rows if R["ilanlar"].get(r["listing_id"], {}).get("durum") not in ("YAZILDI", "ZATEN")]
    t0, durdu = time.time(), ""
    tum_kalem, tum_dok = {}, []

    def kaydet():
        (out / "ILERLEME.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))
    try:
        for n, r in enumerate(kalan, 1):
            q = api.remaining
            if q is not None and str(q).isdigit() and int(q) < a.kota_taban:
                durdu = f"kota {q} < {a.kota_taban}; {n - 1}/{len(kalan)} ilandan sonra (ILERLEME.json ile devam)"; break
            lid = r["listing_id"]
            if yaz:
                durum, not_ = ilan_yaz(api, shop, lid, out, a.yedek_drive, a.fiyat99)
            else:
                inv = api.get(f"/listings/{lid}/inventory") or {}
                sorun, b = kontrol(inv)
                if a.fiyat99 and not sorun:
                    kalem, dok, ks = F.envanter_kar(inv, maliyet())
                    sorun += ks
                    tum_dok += [(lid, sk, f) for sk, f in dok]
                    for x in kalem:
                        tum_kalem.setdefault(x[:3], x)
                durum = "FAIL" if sorun else "PLAN"
                pr = b.get("print") or {}
                not_ = ("; ".join(sorun[:6]) + (f" (+{len(sorun) - 6})" if len(sorun) > 6 else "")) if sorun else ("Print " + ", ".join(f"{x} {pr[x]}" for x in HEDEF)
                                                        + (f" | esit {b['esit']}" if b["esit"] else ""))
            R["ilanlar"][lid] = {"cift": r["cift"], "durum": durum, "not": not_}
            kaydet()
            g = time.time() - t0
            log(f"[{n}/{len(kalan)} %{n * 100 // len(kalan)}] {lid} {r['cift']}: {durum} | gecen {g:.0f}s "
                f"kalan ~{g / n * (len(kalan) - n):.0f}s | kota {api.remaining}")
            if durum == "FAIL":
                durdu = f"ilk FAIL {lid} {r['cift']}: {not_}"
                if yaz or lid == CL_ID:
                    break
    finally:
        kaydet()
        say = {}
        for v in R["ilanlar"].values():
            say[v["durum"]] = say.get(v["durum"], 0) + 1
        md = [f"# SIZE SIRASI ({a.mod}) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "",
              f"- Hedef: {', '.join(HEDEF)}", f"- Sonuc: {say} / {len(rows)}", f"- Durdu: {durdu or 'hayir'}",
              f"- API cagrisi {api.calls} | kota son {api.remaining}", "", "| listing_id | cift | durum | not |", "|---|---|---|---|"]
        md += [f"| {k} | {v['cift']} | {v['durum']} | {v['not'][:300]} |" for k, v in R["ilanlar"].items()
               if v["durum"] not in ("YAZILDI", "ZATEN") or k == CL_ID]
        if a.fiyat99 and not yaz:
            md += ["", "## .99 -> tam fiyat ve net kar (Etsy kesintisi 0.698 + 0.2062 x fiyat; Prodigi canli teklif + ekler)", ""]
            md += F.kar_md(list(tum_kalem.values()))
            md += ["", f"## .99 ile bitmeyen fiyatlar (DEGISTIRILMEZ): {len(tum_dok)}", ""]
            md += [f"- {l} {sk} {f}" for l, sk, f in tum_dok[:200]]
            md += ["", "## Metinlerde fiyat (aciklama + magaza)", ""] + metin_fiyat(api, shop, [r["listing_id"] for r in rows])
        (out / "RAPOR.md").write_text("\n".join(md) + "\n")
        log("\n".join(md[:6]))
    if any(v["durum"] == "FAIL" for v in R["ilanlar"].values()):
        raise SystemExit(f"DUR: {durdu or 'FAIL var (RAPOR.md)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
