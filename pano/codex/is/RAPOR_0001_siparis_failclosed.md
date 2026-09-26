# RAPOR 0001 — siparis yolu fail-closed

- 16 boy icin tek SKU/piksel haritasi eklendi; harita disi boylar gonderime kapanir.
- Plate onayi, dosya pikseli ve 300 DPI gonderimden once dogrulanir.
- Siparis Draft istenir ve geri okumada bekletme kanitlanamazsa yalniz alarm uretilir.
- Kisisellestirme karakter siniri ve ayni burc Left/Right davranisi test edildi.
- Yeni 7 test ve mevcut 81 test, toplam 88 test gecti.
- Etsy, Prodigi veya Drive'a yazma yapilmadi; testlerin tamami yerel/mock calisti.
