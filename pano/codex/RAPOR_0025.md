# RAPOR 0025
- `getListingsByListingIds`, `findAllActiveListingsByShop`, `getListingImages`, `getListingVariationImages`, `getListingInventory`: yalniz `x-api-key`; [Etsy v3 referansi](https://developers.etsy.com/documentation/reference/).
- `getShop`, `getShopSections`: yalniz `x-api-key`; [Etsy v3 referansi](https://developers.etsy.com/documentation/reference/).
- `getShopShippingProfiles`, profil ayrintisi/upgrades ve `getListingFiles`: OAuth gerekir; bu denetimler mevcut token kilidini korudu.
- Varyasyon ve gorsel denetimleri OAuth dosyasi/yenilemesi ile `etsy-token` kuyrugundan cikarildi; Etsy'ye yazma eklenmedi.
- Iki kilitsiz denetimin ana Python ciktisi pipefail+tee ile, hata kuyrugu ve adim ozeti Drive `TEMP/LOGS` yolu ile kaydedildi; workflow testi eklendi.
