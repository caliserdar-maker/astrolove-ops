import sys
sys.argv=[sys.argv[0]]
exec(open("mock_surec_lib.py").read())
kart("Made for You, Step by Step", Image.open("k07_kupa.png").convert("RGB"), [
    ("01", ["Your Preview"], "For every order, we send a preview of your mug via Etsy Messages"),
    ("02", ["Your Approval"], "We print your mug once you approve the preview"),
    ("03", ["Made to Order"], "Printed on both sides, glossy white ceramic, white inside"),
    ("04", ["Easy Care"], "Dishwasher safe and microwave safe")],
    "Original zodiac fusion symbols designed by AstroLoveArt", "K07_surec_sablon.jpg")
