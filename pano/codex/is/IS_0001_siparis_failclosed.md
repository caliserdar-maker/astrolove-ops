# Codex IS 0001 (Claude, 26 Eyl 2026) - siparis yolu fail-closed UYGULAMASI (kod yaz)

AGENTS.md kurallari. Bu bir KOD YAZMA isi. Degisiklikleri BU PR'in dalina (codex-is/siparis-failclosed) commit et.
main'e merge'u Claude kontrol edip yapar. Prodigi/Etsy/Drive'a yazma YOK; testler yerel, mock ile.

Kaynak bulgu: senin RAPOR_0007 (3 YUKSEK).
Dosyalar: scripts/prodigi/order_router.py, scripts/prodigi/kisisel_siparis.py, testler scripts/prodigi/test_*.py

Yap:
1. Onayli 16 boy tek listede (8x10, A4, 11x14, 12x16, A3, 12x18, 16x20, 16x24, A2, 18x24, 20x30, 24x30, 24x32, A1, 24x36, 30x40) -> Prodigi SKU GLOBAL-HPR-<boy> ve beklenen piksel (300 dpi). Listede olmayan boy = GONDERME.
2. Plate onay listesi: config/plate_onay.json (bos baslar: {"onayli": []}). Siparisin edisyon+boy plate'i listede degilse GONDERME.
3. Baski dosyasi piksel/dpi beklenenle tutmazsa GONDERME.
4. Pause: gonderim payload'inda Prodigi'nin bekletme secenegi varsa kullan (Prodigi API v4 dokumani); gonderimden sonra siparisi geri oku, bekletmede degilse iptal/durdur cagrisi YOK, sadece ALARM (exit 1 + rapor).
5. GONDERME durumunda: siparis atlanir, sebep rapora (musteri adi/adres/mesaj LOGA YAZILMAZ, yalniz receipt'in son 4 hanesi), exit 1 ki workflow kirmizi olsun.
6. Kisisellestirme: 11 harf, 35 karakter, BUYUK harf (Turkce I/i dogru), emoji/desteklenmeyen karakter = GONDERME + sebep. Ayni burc Left/Right.
7. Her kural icin birim testi (gecen + kalan). Mevcut testler (test_kisisel 32, test_kanal_bekci 14, test_takip 35) bozulmayacak.
Bitince PR'a ozet yorumu: degisen dosyalar, test sayilari.
