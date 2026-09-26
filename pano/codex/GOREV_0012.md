# Codex GOREV 0012 (Claude, 26 Eyl 2026 10:45 UTC) - "eski video yeni sayildi" hatasinin kontrol kodlarinda aranmasi

AGENTS.md kurallari. KOD DEGISTIRME, yalniz rapor + onerilen tam diff (yanit yorumunun sonunda tek ```diff blogu). ONEM yaz.
Olay: Serdar canli AQUARIUS_SCORPIO ilaninda ESKI video ve ESKI kapak gordu. Galeri yuklemesi o ilanda yarida kalmisti (FAIL), ama genel sorun: yukleme kontrolu "video_1" yalniz video SAYISINA bakiyor; AQUARIUS_CANCER PASS sayildi ama videosu hic yenilenmedi.
Incele (main):
1. scripts/etsy/pod_galeri_tamset.py: video yukleme ve dogrulama yolu. Eski video kalip PASS verilebilecek tum yollar (satir no). Icerik tabanli dogrulama icin en ucuz saglam yol (ornek: canli video id bu kosuda donen id mi + ilk/son kare hash'i beklenen VIDEO.mp4 ile).
2. scripts/etsy/canli_qc.py K5: eski videoyu yakalar mi? (eski ve yeni videolar ayni sure 12.6 sn olabilir; kare farki esigi 0.02 eski/yeni ayrimina yeter mi?)
3. scripts/etsy/tamset_qc.py (pod, 78 TAM_SET denetimi): yanlis PASS riskleri, ozellikle eski slogan "Two Souls · One Bond" iceren kare/kapak yakalanir mi.
RAPOR: pano/codex/RAPOR_0012.md, PR ile. Yanit yorumunda YUKSEK bulgulari dosya:satir ile listele ve diff'i ekle.
