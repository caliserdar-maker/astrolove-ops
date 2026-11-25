# Codex IS 0003 (Claude, 26 Eyl 2026 11:12 UTC) - RAPOR_0013 bulgularini KODDA duzelt (canli ilana dokunmaz)

AGENTS.md kurallari. KOD YAZMA isi. Etsy/Drive yok. Canli ilanlar zaten onayli basligi tasiyor; bu is repodaki sablon/uretici kodu onayli kararlara hizalar ki ileride yeniden uretimde eski sablon canliya gitmesin.
1. scripts/etsy/pod_listing_create.py: baslik "{A} and {B} Zodiac Wall Art, Personalized Couple Print with Names and Message, Unframed"; 3 zorunlu kisisellestirme alani (Name under {A} / Name under {B}: "Up to 11 letters. Printed in capitals."; Your message: "Up to 35 characters, including spaces. Printed as you type it."); ayni burc Left name / Right name; burc sirasi alani YOK. Eksikse fail-closed (hata ver, yayinlama).
2. Rusca ceviri payload'inda etiketler INGILIZCE kalsin (pod_listing_create.py:157-163,240-255,749-754).
3. scripts/etsy/seo/pod_seo_v2_build.py: baslik uretimini onayli sablona hizala VEYA dosyanin basina "ESKI - kullanma" kilidi (calistirilinca SystemExit) koy; hangisi daha guvenliyse onu sec ve gerekcesini yaz.
4. scripts/etsy/pod_referans_kiyas.py: kanon = onayli sabit sema (canli referans ilan degil).
5. docs/POD_LISTING_TEMPLATE.md: uzun/orta tireleri kaldir; izinli metin listesi disindaki iddialari isaretle (silme, yorum olarak isaretle).
6. Her kural icin birim testi; mevcut testler bozulmasin.
TESLIM: yanit yorumunun SONUNA tam unified diff (tek ```diff blogu, kisaltma yok).
