# RAPOR 0029
- Ham magaza/batch JSON girdisinden yalniz dijital ilanlari okuyan cevrimdisi plan araci eklendi.
- Baslik, etiket ve ic ice SKU alanlarindan 78 burc cifti eslemesi; cakisma ve eslesmeyen listeleri uretiliyor.
- Cift basina satis, favori ve goruntulenme onceligiyle; metrik yoksa en eski ilan seciliyor.
- Her dijital ilan icin `TUT_VE_DONUSTUR`, `TASLAGA_AL` veya `ARSIV` eylemi `PLAN.csv` dosyasina yaziliyor.
- Taslak kazananlar, `updateListing` yayin riski nedeniyle planda ayrica isaretleniyor; Etsy yazma kodu eklenmedi.
