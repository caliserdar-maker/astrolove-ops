# ChatGPT AJANI GÖREV METNİ: Etsy arama verisi (iki kaynak + çapraz kontrol)

```
ARAÇ: ChatGPT agent (tarayıcı). OTURUM: etsy-arama (Claude: https://claude.ai/code/session_01S8oeNuGz5F26LSAUgZCtZe)
GÖREV: YALNIZ OKUMA. 167 aday arama terimini iki kaynaktan oku, CSV'ye yaz; 78 ilanın eRank audit puanını oku. DUR.

KESİN KURALLAR
- Hiçbir ayar değişmez, hiçbir şey yayınlanmaz, hiçbir ilan/etiket/fiyat/reklam düzenlenmez, kimseye mesaj gitmez.
- Giriş (login), şifre, 2 adımlı doğrulama, ödeme, abonelik, deneme süresi ya da kart ekranı çıkarsa DUR, Serdar'a yaz.
  eRank hesabını ve ödemesini Serdar açar; sen yalnız açık oturumda okursun.
- Listede olmayan terim sorgulanmaz (eRank sorgu hakkı sınırlı). Bir terim bir kez sorgulanır.
- Rakam ekranda nasıl görünüyorsa öyle yazılır (örn. 1.2k, 77,5 bin). Tahmin, yuvarlama, yorum yok.
- eRank tek başına kanıt değildir. Karar Marketplace insights (MI) verisine göre verilir.

a) OKU (5 dk)
   Drive ASTROLOVE/TEMP/ETSY_ARAMA_20261010/: 1_TESHIS.md, 3_UYGULAMA_PLANI.md, 5_CAPRAZ_KONTROL.csv (167 terim).

b) HAZIRLIK
   5_CAPRAZ_KONTROL.csv'nin kopyasını yerelde aç. Sütunlar değişmez:
   terim | MI arama/30g | MI rekabet | eRank hacim | eRank rekabet | fark oranı | not
   "fark oranı" sütununu BOŞ bırak (Claude script ile doldurur). "not" sütunundaki mevcut metni silme, sonuna ekle.

c) VERİ TOPLA: ÖNCE Marketplace insights, SONRA eRank
   c1. Kaynak 1 (ANA): Etsy Shop Manager > Stats > Marketplace insights. Son 30 gün.
       Her terim için: arama sayısı -> "MI arama/30g"; rekabet / sonuç sayısı -> "MI rekabet".
       "not" sonuna: "MI benzer: <ilk 3 benzer terim>; MI üst: <o aramada üstteki ilk 3 ilanın mağaza adı>".
       MI terimi göstermezse (veri yok) iki MI hücresine "yok" yaz.
   c2. Kaynak 2 (yardımcı): eRank Keyword Explorer. Her terim için: hacim -> "eRank hacim"; rekabet -> "eRank rekabet";
       "not" sonuna: "eRank trend: <artıyor/azalıyor/sabit, ekranda yazdığı gibi>".
   c3. eRank Listing Audit: 78 ilan (liste: 2_ETSY_ARAMA_78_ONERI.csv, listing_id sırası). Ayrı dosya
       7_ERANK_AUDIT.csv sütunları: listing_id | cift | eRank puan | eRank ilk 3 uyarı (ekrandaki metin).

   GÜN PLANI (eRank Basic: Keyword Explorer 100 sorgu/gün, Listing Audit 50/gün)
   | Gün | MI | eRank Keyword Explorer | eRank Listing Audit |
   | 1 | 167 terimin hepsi (MI'da sorgu sınırı / doğrulama ekranı çıkarsa DUR) | CSV satır 1-100 (G1, G2, G3'ün başı) | ilan 1-50 |
   | 2 | (gün 1'de bitmediyse kalan) | CSV satır 101-167 | ilan 51-78 |
   eRank günlük hakkı erken biterse dur, kaldığın satır numarasını yaz; ertesi gün oradan devam.

d) TESLİM ve DUR
   - Drive ASTROLOVE/TEMP/ETSY_ARAMA_20261010/ altına: 5_CAPRAZ_KONTROL_DOLU.csv ve 7_ERANK_AUDIT.csv (yeni dosya;
     eski dosyaların üzerine yazma).
   - Serdar'a en fazla 6 satır: kaç terim MI dolu, kaç terim eRank dolu, kaç ilan audit, eksik satırlar, karşılaşılan engel.
   - DUR. Fark oranı ve "çelişkili" işaretini Claude hesaplar (scripts/etsy/arama_capraz.py, eşik 2 kat; karar MI'ya göre).
```

Not (Claude): terim grupları CSV "not" sütununda: G1 mevcut 12 ortak etiket (giclee print dahil); G2 16 aday genel terim; G3 76 mevcut çift adı etiketi; G4 63 faz 2 aday çift etiketi. Eski MI değerleri (6 Ağu / 23 Eyl) devir dosyalarından geldi, doğrulanmadı; yalnız karşılaştırma için.
