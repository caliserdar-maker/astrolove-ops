import copy
import unittest

import fiyat_sku_denetim as D


def inventory():
    products = []
    for color in ("Blue", "Black", "Parchment", "Ivory", "White"):
        for index, size in enumerate(D.SIZES):
            products.append({"sku": f"GLOBAL-HPR-{size}", "property_values": [
                {"property_name": "Primary color", "values": [color]},
                {"property_name": "Size", "values": [D.SIZE_LABEL[size]]},
            ], "offerings": [{"price": {"amount": 3000 + index * 100, "divisor": 100},
                                "quantity": 999, "is_enabled": True}]})
    return {"products": products}


class AuditTest(unittest.TestCase):
    def assert_rule(self, data, rule):
        errors, _ = D.denetle_ilan("100", data)
        self.assertIn(rule, {row["kural"] for row in errors})

    def test_pass(self):
        self.assertEqual(D.denetle_ilan("100", inventory())[0], [])

    def test_missing_variant(self):
        data = inventory(); data["products"].pop()
        self.assert_rule(data, "varyasyon_sayisi")
        self.assert_rule(data, "varyasyon_matrisi")

    def test_sku(self):
        data = inventory(); data["products"][0]["sku"] = "WRONG"
        self.assert_rule(data, "sku")

    def test_color_price(self):
        data = inventory(); data["products"][0]["offerings"][0]["price"]["amount"] += 1
        self.assert_rule(data, "renk_fiyat_farki")

    def test_inventory(self):
        data = inventory(); data["products"][0]["offerings"][0]["quantity"] = 0
        self.assert_rule(data, "envanter")

    def test_property_names(self):
        data = inventory(); data["products"][0]["property_values"][0]["property_name"] = "Color"
        self.assert_rule(data, "property_adlari")

    def test_size_label(self):
        data = inventory(); data["products"][0]["property_values"][1]["values"] = ["8 x 10"]
        self.assert_rule(data, "boy_etiketi")

    def test_cross_listing_price(self):
        inventories = [(str(i), copy.deepcopy(inventory())) for i in range(78)]
        inventories[-1][1]["products"][0]["offerings"][0]["price"]["amount"] += 100
        errors, summary = D.denetle_tumu(inventories)
        self.assertEqual(summary["durum"], "FAIL")
        self.assertIn("ilanlar_arasi_fiyat", {row["kural"] for row in errors})


if __name__ == "__main__":
    unittest.main()
