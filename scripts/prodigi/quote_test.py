#!/usr/bin/env python3
"""Router ile TEK test teklifi (yalniz POST /quotes; siparis ACMAZ, Etsy yok). order_router.Prodigi.quote() kullanilir
(29 Eyl sizing duzeltmesi dogrulamasi). HTTP 200 + maliyet -> PASS (exit 0), aksi FAIL (exit 1)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import order_router as R

p = R.Prodigi(R.load_prodigi_key("live"), "live")
kayit = []
asil = p.call
def call(m, yol, b=None):
    assert (m, yol) == ("POST", "/quotes"), f"yalniz /quotes: {m} {yol}"
    st, d = asil(m, yol, b); kayit.append((st, d)); return st, d
p.call = call
maliyet, hata, ayr = p.quote([{"prodigi_sku": "GLOBAL-HPR-8x10", "qty": 1, "attributes": {}}], "US")
st = kayit[-1][0] if kayit else None
ok = st == 200 and maliyet is not None
print(f"TEST TEKLIF (router Prodigi.quote, GLOBAL-HPR-8x10, US, {p.shipping_method if hasattr(p, 'shipping_method') else R.DEFAULT_SHIPPING_METHOD}): "
      f"HTTP {st} | maliyet+ekler {maliyet} | {hata or 'hata yok'} | {'PASS' if ok else 'FAIL'}"
      + ("" if ok else f" | {str(kayit[-1][1])[:300] if kayit else ''}"), flush=True)
sys.exit(0 if ok else 1)
