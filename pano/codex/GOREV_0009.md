# Codex GOREV 0009 (Claude, 26 Eyl 2026) - ACIL: galeri yuklemesinde sira 5-12 neden yanlis?

AGENTS.md kurallari. KOD DEGISTIRME, yalniz rapor. Etsy yok (dokuman internetten okunabilir). ONEM yaz.

Kod: scripts/etsy/pod_galeri_tamset.py (main 6af443a).
Gozlem (medya oturumu, canli):
- AQUARIUS_CANCER ve ARIES_LEO pilotunda 13 fotodan sira 1-4 ve 13 dogru, 5-12 yanlis siraya dusuyor. SET.json dosyalari sira duzeninde (kontrol edildi).
- Onarimda galeri kisa sure 14 foto oldu, kod KeyError ile coktu; AQUARIUS_CANCER'da sira 13 bos, 14. yerde eski foto, Warm Parchment varyasyonu yanlis foto.
- Alt metin icin listing_image_id ile yeniden iliskilendirme (dosyasiz multipart) 200 dondu ama alt metin degismedi.
- Onceki bulgu: Etsy ayni dosyayi tekillestiriyor (ayni bayt -> ayni listing_image_id), rank parametresi o durumda yok sayiliyor olabilir.

Istenen:
1. Sira 5-12 hatasinin en olasi kok nedeni (satir numarasiyla): yukle-sonra-sil rank kaymasi, tekillestirme, rank parametresinin gonderilme bicimi, max 20 foto siniri, vs.
2. Etsy Open API v3 uploadListingImage / deleteListingImage / getListingImages dokumanina gore dogru akis: aktif ilan HICBIR AN 0 fotoda kalmadan 13 fotoyu dogru sirayla koymanin guvenli yolu (20 foto siniri dahil).
3. Alt metni degistirmenin calisan yolu (dokumanda alt_text ile listing_image_id birlikte davranisi). Olmuyorsa: ayni gorseli birkac bayt farkli yeniden kodlayip yeni foto olarak yukleme gibi alternatif.
4. 14 foto durumunda KeyError satiri ve dayanikli hale getirme onerisi.
Somut sozde kod ver (kod degistirme yok).

RAPOR: pano/codex/RAPOR_0009.md, PR ile. Hizli: once 1 ve 2.
