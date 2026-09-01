# Sirlar (Secrets)

Bu dosya yalnizca **gereken sirlarin listesini** icerir. Hicbir gercek deger
buraya yazilmaz. Degerler GitHub reposunda
`Settings > Secrets and variables > Actions` altinda, lokalde ise
versiyonlanmayan bir `.env` dosyasinda tutulur.

| Sir | Aciklama |
| --- | --- |
| `ETSY_API_KEY` | Etsy uygulamasinin genel API anahtari (keystring); API isteklerini uygulamaya baglar. |
| `ETSY_SHARED_SECRET` | Etsy uygulamasinin gizli anahtari; OAuth token degisimi ve imzalama icin kullanilir. |
| `ETSY_REFRESH_TOKEN` | Etsy OAuth2 yenileme tokeni; suresi dolan erisim tokenini yenilemek icin kullanilir. |
| `ETSY_SHOP_ID` | Islem yapilacak Etsy magazasinin sayisal kimligi. |
| `RCLONE_CONF_B64` | Base64 ile kodlanmis `rclone.conf` icerigi; uzak depolama baglantisini calisma aninda olusturur. |
| `GDRIVE_ROOT_FOLDER_ID` | Dosyalarin yazilacagi Google Drive kok klasorunun kimligi. |

## Kurallar

- Gercek degerler asla depoya commit edilmez; `.gitignore` `.env`,
  `rclone.conf` ve `*.json` token dosyalarini haric tutar.
- Sir degeri degistiginde once GitHub Secrets guncellenir, sonra ilgili
  workflow yeniden calistirilir.
- Yeni bir sir eklendiginde bu tabloya tek satirlik aciklamasiyla eklenir.
