# Printful ornament urunleri (salt okuma)

Kaynak: Printful API (v1 + v2), ham yanitlar `ham/`. Son istek: API vermedi. Istek: 0 (GET 0, POST 0: yok).
Olcu cm = inch x 2.54 (hesap). Fiyat: v1 `variants[].price` (USD, kargo haric); v2 `prices?currency=` (USD/EUR).
Kargo: 1 adet, ornek adres (baskent/merkez posta kodu), en ucuz secenek (v1 /shipping/rates). Cikis ulkesi: v2 /v2/shipping-rates `shipments[].departure_country`. Takip: API'de takip alani yoksa "API vermedi".

## 1. Urunler

| urun | sekil/olcu | yuz | fiyat USD (v1) | uretim yeri (cikis, v2) | satilabildigi bolgeler (v1) | baski dosyasi piksel |
|---|---|---|---|---|---|---|

## 2. Kargo ucreti (USD, 1 adet, en ucuz yontem; hucre: ucret (yontem id, min-max gun))

| urun | US | CA | GB | DE | FR | IT | ES | NL | AU |
|---|---|---|---|---|---|---|---|---|---|

Yontem adlari (v1 `name`, ilk varyant):


## 3. Urun ayrintilari

