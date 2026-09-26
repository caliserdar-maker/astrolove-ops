# Codex IS 0012 - kisisel siparis baski dosyasi: olcek ve leke kapilari neden FAIL (dal siparis-baski-v1)
AGENTS.md kurallari. Ag YOK. Salt inceleme + gerekirse duzeltme diff'i.
Bulgu (kisisel_RAPOR_0004a): TEST_A DEEP_BLACK 30x40 9000x12000 300 dpi uretildi; kalinti/temiz_ara_zemin/sembol/boy_siniri/font_kapsami OK, olcek ve leke BASARISIZ. Bu iki kapi 25 Eyl'de plate yoluna gecerken yeniden tanimlandi, canli kosulmadi.
Is: 1) scripts/medya_v1/siparis_dosyasi.py ve kapilari bul; olcek ve leke kapisinin neyi neyle karsilastirdigini, hangi olcekte ve hangi referansla yaptigini cikar. 2) Kapi mi yanlis (referans boyu/oran/esik birimi uyumsuz) yoksa cikti mi bozuk: koddan kanit (dosya:satir). 3) Kapi yanlissa duzeltme diff'i + sentetik test (dogru cikti PASS, bilincli leke/olcek hatasi FAIL). Esik gevsetme YOK.
Teslim: yanit yorumunun sonuna TAM unified diff (tek ```diff blogu, taban siparis-baski-v1) ya da diff yoksa gerekceli rapor. pano/codex/RAPOR_0012.md 6 satir.
