#!/usr/bin/env python3
"""ayar77_kuru yerel oz-testi (sahte Etsy, 60 sn alti). Yazma cagrisi yapilirsa FAIL.
Senaryolar: CL + normal cift (eski yapi) + ayni burc cifti + taslak ilan + zaten CL gibi olan ilan."""
import copy
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar77_kuru as A  # noqa: E402
import metin_78_uret as M  # noqa: E402

FORMATS = ["Digital File", "Print", "Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"]
RENK = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
BOY = ["8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2", "18x24", "20x30", "24x30", "24x36"]
EK = {"Digital File": "-DIGITAL", "Print": "", "Antique Gold Frame": "-FGO", "Black Frame": "-FBK",
      "White Frame": "-FWH", "Natural Frame": "-FNA"}


def cl_inv(onek="POD-CAN_LIB-"):
    ps = []
    for f in FORMATS:
        for r in RENK:
            for b in BOY:
                ps.append({"sku": f"{onek}{b}{EK[f]}", "property_values": [
                    {"property_id": 514, "property_name": "Digital File, Print or Framed?", "values": [f]},
                    {"property_id": 200, "property_name": "Primary color", "values": [r], "value_ids": [1]},
                    {"property_id": 513, "property_name": "Size", "values": [b]}],
                    "offerings": [{"price": {"amount": 999 if f == "Digital File" else 4799, "divisor": 100},
                                   "quantity": 999, "is_enabled": True, "readiness_state_id": 77}]})
    return {"products": ps, "price_on_property": [514, 200, 513], "sku_on_property": [514, 200, 513],
            "quantity_on_property": []}


def eski_inv(onek):
    return {"products": [{"sku": f"{onek}MB-8x10", "property_values": [
        {"property_id": 200, "property_name": "Primary color", "values": ["Midnight Blue"]},
        {"property_id": 513, "property_name": "Size", "values": ["8x10"]}],
        "offerings": [{"price": {"amount": 3099, "divisor": 100}, "quantity": 999, "is_enabled": True}]}] * 65,
        "price_on_property": [513], "sku_on_property": [200, 513]}


def sorular(a, b):
    l = ("Left name", "Right name") if a == b else (f"Name under {a}", f"Name under {b}")
    return [{"question_text": l[0], "question_type": "text", "required": True, "max_allowed_characters": 11, "instruction": "x"},
            {"question_text": l[1], "question_type": "text", "required": True, "max_allowed_characters": 11, "instruction": "x"},
            {"question_text": "Your message", "question_type": "text", "required": True, "max_allowed_characters": 35, "instruction": "y"}]


class Fake:
    def __init__(self, ilanlar):
        self.remaining = "5000"; self.ilanlar = ilanlar; self.calls = 0

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path == "/listings/batch":
            ids = params["listing_ids"].split(",")
            return {"results": [copy.deepcopy(self.ilanlar[i]["L"]) for i in ids if i in self.ilanlar]}
        lid = next(p for p in path.split("/") if p.isdigit() and len(p) == 10)
        I = self.ilanlar[lid]
        if path.endswith("/inventory"):
            return copy.deepcopy(I["inv"])
        if path.endswith("/properties"):
            return {"results": copy.deepcopy(I["props"])}
        if path.endswith("/translations/ru"):
            return None
        if path.endswith("/personalization"):
            return {"personalization_questions": I["q"]}
        return copy.deepcopy(I["L"])

    def _yazma(self, *a, **k):
        raise AssertionError("KURU KOSUDA YAZMA CAGRISI")
    put = patch = post = delete = put_json = post_json = post_file = _yazma


def ilan(lid, a, b, cift, inv, desc, state="active", q=None, ayar=None, props=None):
    L = {"listing_id": int(lid), "state": state, "title": f"{a} and {b} T", "tags": ["t"], "description": desc,
         "is_personalizable": True, "personalization_is_required": True, "personalization_char_count_max": 256,
         "personalization_instructions": "", "shipping_profile_id": 1, "return_policy_id": 2, "shop_section_id": 3,
         "taxonomy_id": 121, "who_made": "i_did", "when_made": "made_to_order", "is_supply": False,
         "personalization_questions": q if q is not None else sorular(a, b)}
    L.update(ayar or {})
    return {"L": L, "inv": inv, "q": L["personalization_questions"],
            "props": props if props is not None else [{"property_id": 1, "property_name": "Orientation", "values": ["Vertical"], "value_ids": [5]}]}


def main():
    kotu = []
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        ids = [("4570143815", "CANCER_LIBRA", "Cancer", "Libra")] + [(str(4570200000 + i), f"X{i}", "", "") for i in range(77)]
        ids[1] = ("4570200001", "ARIES_LEO", "Aries", "Leo")
        ids[2] = ("4570200002", "LEO_LEO", "Leo", "Leo")
        ids[3] = ("4570200003", "PISCES_VIRGO", "Pisces", "Virgo")
        ids[4] = ("4570200004", "TAURUS_VIRGO", "Taurus", "Virgo")
        for n in range(5, 78):
            ids[n] = (str(4570200000 + n), "GEMINI_LIBRA", "Gemini", "Libra")
        with open(td / "ids.csv", "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["listing_id", "cift", "a", "b"]); w.writerows(ids)
        il = {"4570143815": ilan("4570143815", "Cancer", "Libra", "CANCER_LIBRA", cl_inv(), M.uret("CANCER_LIBRA"))}
        il["4570200001"] = ilan("4570200001", "Aries", "Leo", "ARIES_LEO", eski_inv("POD-ARI_LEO-"), "eski metin",
                               q=sorular("Leo", "Aries")[:2], ayar={"shop_section_id": 9})
        il["4570200002"] = ilan("4570200002", "Leo", "Leo", "LEO_LEO", eski_inv("POD-LEO_LEO-"), "eski")
        il["4570200003"] = ilan("4570200003", "Pisces", "Virgo", "PISCES_VIRGO", eski_inv("POD-PIS_VIR-"), "eski", state="draft")
        il["4570200004"] = ilan("4570200004", "Taurus", "Virgo", "TAURUS_VIRGO", cl_inv("POD-TAU_VIR-"), M.uret("TAURUS_VIRGO"))
        for n in range(5, 78):
            il[ids[n][0]] = ilan(ids[n][0], "Gemini", "Libra", "GEMINI_LIBRA", cl_inv("POD-GEM_LIB-"), M.uret("GEMINI_LIBRA"),
                                 props=[])
        api = Fake(il)
        satir, ref, say = A.calis(api, "39729443", td / "ids.csv", td / "out")
        S = {s["listing_id"]: s for s in satir}
        if len(satir) != 77: kotu.append("77 satir")
        if ref["urun"] != 390: kotu.append("CL urun 390")
        if ref["bulgu"]: kotu.append(f"CL bulgu {ref['bulgu']}")
        s1 = S["4570200001"]
        if s1["envanter"] != "65 -> 390 urun" or s1["aciklama"] != "DEGISECEK" or s1["kisisel"] != "DEGISECEK" \
                or "shop_section_id" not in s1["ayar_fark"]:
            kotu.append(f"normal cift {s1}")
        if "Name under Aries" not in s1["kisisel_fark"]: kotu.append("soru etiketi Aries")
        s2 = S["4570200002"]
        if "Left name" in s2["kisisel_fark"] or s2["kisisel"] != "AYNI": kotu.append(f"ayni burc sorular {s2['kisisel_fark']}")
        if "tarih satiri iki kez" not in s2["aciklama_not"]: kotu.append("ayni burc tarih bayragi")
        if S["4570200003"]["yazilabilir"] != "HAYIR (active degil)": kotu.append("draft")
        s4 = S["4570200004"]
        if (s4["envanter"], s4["aciklama"], s4["kisisel"], s4["ayar"], s4["nitelik"]) != ("AYNI", "AYNI", "AYNI", "AYNI", "AYNI"):
            kotu.append(f"zaten CL gibi {s4}")
        if S["4570200005"]["nitelik"] != "DEGISECEK": kotu.append("nitelik farki")
        if len(list((td / "out/ACIKLAMA").glob("*.txt"))) < 4 or not (td / "out/FARK.csv").exists(): kotu.append("cikti")
        if any(s["aciklama_not"].startswith("CL'den ad/tarih disi") for s in satir): kotu.append("sablon disi fark")
    print("SELFTEST:", "PASS" if not kotu else "FAIL " + "; ".join(kotu))
    raise SystemExit(0 if not kotu else 2)


if __name__ == "__main__":
    main()
