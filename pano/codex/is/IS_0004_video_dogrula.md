# Codex IS 0004 - ortak VIDEO ICERIK DOGRULAYICI (kod yaz, yeni dosya)
AGENTS.md kurallari. Etsy/Drive yok. Yeni dosyalar: scripts/etsy/video_dogrula.py + scripts/etsy/test_video_dogrula.py (mevcut dosyalara dokunma).
Amac: medya (yukleme sonrasi) ve pod (canli QC) ayni fonksiyonu kullansin. Senin RAPOR_0010/0012 bulgularin: kontrol yalniz sayi/sureye bakiyordu, eski video PASS oldu.
API: dogrula(canli_mp4, beklenen_mp4, tuzak_mp4=None, poster_png=None) -> dict(pass, sure_fark, kare_fark_list, tuzak_orani, eski_slogan, neden)
1. En az 8 esit aralikli kare + ilk/son kare; 256 px gri + ayrica burc bolgesi (poster_png'den ya da ust %60) farki.
2. Tuzak (baska cift ya da eski video) verilirse canli-beklenen farki, canli-tuzak farkinin en az 3 kati kucuk olmali.
3. Eski slogan "TWO SOULS" / "ONE BOND" OCR (pytesseract varsa; yoksa atla ve neden'e yaz) -> FAIL.
4. ffmpeg/ffprobe yoksa acik hata (sessiz PASS yok). Bos/bozuk dosya -> FAIL.
5. Testler: sentetik videolar (ffmpeg ile renk bloklari + metin) - ayni video PASS, farkli cift FAIL, eski slogan FAIL, bos dosya FAIL.
