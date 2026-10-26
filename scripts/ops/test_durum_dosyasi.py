#!/usr/bin/env python3
"""durum_dosyasi.py yerel testi: sahte rclone (gdrive: -> gecici dizin). Gercek Drive / gercek durum dosyasi YOK.
Akislar (gercek yazici fonksiyonlariyla): pod-order-router POD_ORDERS_STATE.csv (order_router.upd/write_state),
kupa-siparis STATE.csv (kupa_siparis.state_yaz), drive-satir-ekle TEMP/*.md (is akisindaki ekleme kodu),
galeri-77-yukle ILERLEME.json (galeri77_yukle kayit bicimi). Her akista: normal, okuma hatasi (lsjson / copyto),
liste bos ama dosya var, bozuk ve bos dosya, okumadan sonra uzak degisti, geri okuma tutmuyor, ilk kayit, kayit azalmasi,
degisiklik yok (yazma yok), yedek 30 siniri (31. yedekte en eski silinir; YEDEK/ disi ve baska dosyanin yedegi korunur)."""
import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "prodigi")); sys.path.insert(0, str(HERE.parent / "kupa_siparis"))
import durum_dosyasi as DD  # noqa: E402
import order_router as R  # noqa: E402
import kupa_siparis as K  # noqa: E402

SAHTE = HERE / "sahte_rclone.py"


def router_ilk():
    st = {}
    R.write_state(_GEC, st)
    for rid, stg in (("4100000001", "tracked"), ("4100000002", "atlandi"), ("_META", "meta")):
        st[rid] = {"receipt_id": rid, "stage": stg, "ts_utc": "2026-09-21 07:39:51", "note": "a,\"b\"\nc"}
    R.write_state(_GEC, st)
    return Path(_GEC).read_bytes()


def router_degis(p):                                  # gercek upd: yeni receipt + mevcut satirin guncellenmesi
    st = R.read_state(p)
    R.upd(st, p, "4100000003", stage="bekliyor", items="POD-X")
    R.upd(st, p, "4100000002", alarm_kosu=1)


def router_sil(p):
    st = R.read_state(p); st.pop("4100000001"); R.write_state(p, st)


def kupa_ilk():
    st = {t: {"transaction_id": t, "receipt_id": "4100000009", "sku": "KUPA-X", "durum": "PASS", "zaman": "2026-10-20 10:00:00"}
          for t in ("5000000001", "5000000002")}
    K.state_yaz(_GEC, st)
    return Path(_GEC).read_bytes()


def kupa_degis(p):
    st = K.state_oku(p)
    st["5000000003"] = {"transaction_id": "5000000003", "receipt_id": "4100000010", "sku": "KUPA-Y", "durum": "GOZ", "zaman": "z"}
    K.state_yaz(p, st)


def kupa_sil(p):
    st = K.state_oku(p); st.pop("5000000001"); K.state_yaz(p, st)


def md_ekle(p, satir="- 26 Eki yeni satir"):        # drive-satir-ekle.yml'deki ekleme kodu (birebir)
    s = open(p, encoding="utf-8").read().split('\n')
    s = [] if s == [''] else s
    i = next((k for k, x in enumerate(s) if x.startswith('## ')), None)
    if i is None:
        while s and not s[-1].strip():          # sondaki bos satirlar: notlar arasinda bos satir olmasin
            s.pop()
        s = [x for x in s] + [satir]
    else:
        j = i
        while j > 0 and not s[j - 1].strip():
            j -= 1
        s = s[:j] + [satir] + s[j:]
    open(p, 'w', encoding='utf-8').write('\n'.join(s).rstrip('\n') + '\n')


def md_sil(p):
    s = open(p, encoding="utf-8").read().split("\n"); s.pop(1); open(p, "w", encoding="utf-8").write("\n".join(s))


def il_degis(p):
    v = json.loads(Path(p).read_text())
    v["ilanlar"]["4570000003"] = {"cift": "LEO_LEO", "set": 19, "durum": "PASS", "ts": "t"}
    v["ilanlar"].setdefault("4570000001", {"cift": "A_A", "set": 17})["durum"] = "PASS"
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=1))


def il_sil(p):
    v = json.loads(Path(p).read_text()); v["ilanlar"].pop("4570000002"); Path(p).write_text(json.dumps(v))


_GEC = None
AKIS = {
    "router": dict(uzak="gdrive:ASTROLOVE/TEMP/POD_ORDERS_STATE.csv", tur="csv", anahtar="receipt_id",
                   korunan=("stage", "prodigi_order_id", "tracking"), ilk_izin=False,
                   ilk=router_ilk, degis=router_degis, sil=router_sil, bozuk=b"stage,country\nx,y\n"),
    "kupa": dict(uzak="gdrive:ASTROLOVE/KUPA_SIPARIS/STATE.csv", tur="csv", anahtar="transaction_id",
                 korunan=("durum",), ilk_izin=False,
                 ilk=kupa_ilk, degis=kupa_degis, sil=kupa_sil, bozuk=b"receipt_id,sku\n1,2\n"),
    "md": dict(uzak="gdrive:ASTROLOVE/TEMP/OTURUM_NOTLARI.md", tur="md", anahtar="", korunan=(), ilk_izin=True,
               ilk=lambda: b"# OTURUM NOTLARI\n- 25 Eki satir\n\n## Tablo\n| a | b |\n", degis=md_ekle, sil=md_sil, bozuk=b"\xff\xfe\x00"),
    "galeri": dict(uzak="gdrive:ASTROLOVE/TEMP/GALERI_YAYIN/ILERLEME.json", tur="json-ilanlar", anahtar="", korunan=(), ilk_izin=False,
                   ilk=lambda: json.dumps({"ilanlar": {"4570000001": {"cift": "A_A", "set": 17, "durum": "FAIL"},
                                                      "4570000002": {"cift": "B_B", "set": 19, "durum": "PASS"}}}).encode(),
                   degis=il_degis, sil=il_sil, bozuk=b'{"ilanlar": [1, 2]}'),
}


class DurumTest(unittest.TestCase):
    def setUp(self):
        global _GEC
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name); self.t = t
        self.kok = t / "drive"; self.kok.mkdir()
        _GEC = str(t / "gecici.csv")
        os.environ.update(RCLONE=f"{sys.executable} {SAHTE}", FAKE_ROOT=str(self.kok), FAKE_HATA="")

    def tearDown(self):
        self.tmp.cleanup()

    # ---- yardimcilar
    def hazirla(self, ad, var=True):
        A = AKIS[ad]; self.A = A
        self.uzak_p = self.kok / A["uzak"][len("gdrive:"):]
        self.uzak_p.parent.mkdir(parents=True, exist_ok=True)
        os.environ["FAKE_ANA"] = self.uzak_p.name
        self.yerel, self.durum = self.t / f"_work/{ad}/{self.uzak_p.name}", self.t / f"_work/{ad}/DURUM"
        if var:
            self.uzak_p.write_bytes(A["ilk"]())
        return self.uzak_b()

    def uzak_b(self):
        return self.uzak_p.read_bytes() if self.uzak_p.exists() else None

    def kos(self, komut, hata="", ilk_izin=None):
        os.environ["FAKE_HATA"] = hata
        d = DD.Dosya(self.A["uzak"], self.A["tur"], self.A["anahtar"], korunan=self.A["korunan"],
                     ilk_izin=self.A["ilk_izin"] if ilk_izin is None else ilk_izin)
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = DD.calistir(komut, d, self.yerel, self.durum)
        return rc, o.getvalue()

    def akis(self, degis=None, hata_oku="", hata_yaz="", ilk_izin=None):
        rc, log = self.kos("oku", hata_oku, ilk_izin)
        if rc:
            return rc, log
        (degis or self.A["degis"])(str(self.yerel))
        rc2, log2 = self.kos("yaz", hata_yaz, ilk_izin)
        return rc2, log + log2

    def yedekler(self):
        d = self.uzak_p.parent / "YEDEK"
        return sorted(d.glob(f"{self.uzak_p.stem}_*{self.uzak_p.suffix}")) if d.is_dir() else []

    def her_akis(self):
        for ad in AKIS:
            with self.subTest(akis=ad):
                yield ad
            self.tearDown(); self.setUp()

    # ---- senaryolar
    def test_01_normal(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis()
            self.assertEqual(rc, 0, log)
            self.assertEqual(self.uzak_b(), self.yerel.read_bytes())
            self.assertNotEqual(self.uzak_b(), b)
            y = self.yedekler(); self.assertEqual(len(y), 1); self.assertEqual(y[0].read_bytes(), b)

    def test_02a_listeleme_hatasi(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(hata_oku="lsjson")
            self.assertEqual(rc, 1); self.assertIn("listeleme hatasi", log); self.assertEqual(self.uzak_b(), b); self.assertFalse(self.yedekler())

    def test_02b_indirme_hatasi(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(hata_oku="copyto_indir")
            self.assertEqual(rc, 1); self.assertIn("indirilemedi", log); self.assertEqual(self.uzak_b(), b)

    def test_02c_yazim_adimi_okumasiz(self):                # okuma FAIL'den sonra always() yazim adimi kosarsa
        for ad in self.her_akis():
            b = self.hazirla(ad)
            self.yerel.parent.mkdir(parents=True, exist_ok=True); self.yerel.write_bytes(b"")
            rc, log = self.kos("yaz")
            self.assertEqual(rc, 1); self.assertIn("okuma adimi tamamlanmamis", log); self.assertEqual(self.uzak_b(), b)

    def test_03_liste_bos_dosya_var(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(hata_oku="lsjson_bos")                       # is akisi ayariyla: FAIL (izinsiz ya da dogrudan okuma)
            self.assertEqual(rc, 1); self.assertEqual(self.uzak_b(), b)
            rc, log = self.akis(hata_oku="lsjson_bos", ilk_izin=True)        # en kotu durum: izin olsa bile dogrudan okuma kapisi
            self.assertEqual(rc, 1); self.assertIn("dogrudan okunabiliyor", log); self.assertEqual(self.uzak_b(), b)

    def test_03b_dosya_kayip_yedek_var(self):
        for ad in self.her_akis():
            self.hazirla(ad)
            self.assertEqual(self.akis()[0], 0)
            b = self.uzak_b()
            rc, log = self.akis(hata_oku="lsjson_bos_ana,cat", ilk_izin=True)
            self.assertEqual(rc, 1); self.assertIn("yedek var", log); self.assertEqual(self.uzak_b(), b)

    def test_04a_bozuk(self):
        for ad in self.her_akis():
            self.hazirla(ad); self.uzak_p.write_bytes(self.A["bozuk"]); b = self.uzak_b()
            rc, log = self.akis()
            self.assertEqual(rc, 1, log); self.assertEqual(self.uzak_b(), b)

    def test_04b_bos_dosya(self):
        for ad in self.her_akis():
            self.hazirla(ad); self.uzak_p.write_bytes(b"")
            rc, log = self.akis()
            self.assertEqual(rc, 1, log); self.assertEqual(self.uzak_b(), b"")

    def test_05_uzak_degisti(self):
        for ad in self.her_akis():
            self.hazirla(ad)
            self.assertEqual(self.kos("oku")[0], 0)
            self.A["degis"](str(self.yerel))
            self.uzak_p.write_bytes(self.uzak_b() + (b"\n" if ad != "galeri" else b" ")); b = self.uzak_b()
            rc, log = self.kos("yaz")
            self.assertEqual(rc, 1); self.assertIn("degismis", log); self.assertEqual(self.uzak_b(), b)

    def test_06_geri_okuma_tutmuyor(self):
        for ad in self.her_akis():
            self.hazirla(ad)
            rc, log = self.akis(hata_yaz="cat_bozuk_sonra")
            self.assertEqual(rc, 1); self.assertIn("geri okuma sha256", log)

    def test_07_ilk_kayit(self):                            # izinli: olusturur; is akisi ayari (router/kupa/galeri izinsiz): FAIL
        for ad in self.her_akis():
            self.hazirla(ad, var=False)
            if not self.A["ilk_izin"]:
                rc, log = self.akis()
                self.assertEqual(rc, 1); self.assertIn("ilk kayit izni yok", log); self.assertIsNone(self.uzak_b())
            rc, log = self.akis(ilk_izin=True)
            self.assertEqual(rc, 0, log); self.assertIn("ilk kayit", log)
            self.assertEqual(self.uzak_b(), self.yerel.read_bytes()); self.assertFalse(self.yedekler())

    def test_07b_klasor_yok(self):                          # hedef klasor Drive'da hic yok (ust klasor listelenir)
        for ad in self.her_akis():
            self.hazirla(ad, var=False)
            self.uzak_p.parent.rmdir()
            rc, log = self.akis(ilk_izin=True)
            self.assertEqual(rc, 0, log); self.assertIn("klasor Drive'da yok", log)
            rc, log = self.kos("oku", "lsjson")                 # listeleme hatasi yine FAIL
            self.assertEqual(rc, 1)

    def test_14_csv_tekrar_ya_da_bos_anahtar(self):
        for ad in ("router", "kupa"):
            with self.subTest(akis=ad):
                b = self.hazirla(ad)
                satir = b.decode().rstrip("\n").split("\n")
                for bozuk in ("\n".join(satir + [satir[1]]) + "\n", "\n".join(satir + ["," + satir[1].split(",", 1)[1]]) + "\n"):
                    self.uzak_p.write_text(bozuk); g = self.uzak_b()
                    rc, log = self.akis()
                    self.assertEqual(rc, 1, log); self.assertIn("CSV'de", log); self.assertEqual(self.uzak_b(), g)
            self.tearDown(); self.setUp()

    def test_15_md_crlf(self):
        self.hazirla("md"); self.uzak_p.write_bytes(b"# A\r\n- 25 Eki\r\n\r\n## T\r\n| a |\r\n")
        rc, log = self.akis()
        self.assertEqual(rc, 0, log); self.assertIn(b"26 Eki", self.uzak_b())

    def test_16_icerik_bosaltma(self):
        self.hazirla("galeri")
        def bosalt(p):
            v = json.loads(Path(p).read_text()); v["ilanlar"]["4570000002"] = {}; Path(p).write_text(json.dumps(v))
        def geri(p):
            v = json.loads(Path(p).read_text()); v["ilanlar"]["4570000002"]["durum"] = "FAIL"; Path(p).write_text(json.dumps(v))
        for f in (bosalt, geri):
            b = self.uzak_b(); rc, log = self.akis(degis=f)
            self.assertEqual(rc, 1, log); self.assertIn("korunmadi", log); self.assertEqual(self.uzak_b(), b)
        self.tearDown(); self.setUp(); self.hazirla("router")
        def stage_bos(p):
            st = R.read_state(p); st["4100000001"]["stage"] = ""; R.write_state(p, st)
        b = self.uzak_b(); rc, log = self.akis(degis=stage_bos)
        self.assertEqual(rc, 1, log); self.assertIn("korunan sutun", log); self.assertEqual(self.uzak_b(), b)
        def warn_bos(p):                                         # korunmayan sutun bosalabilir (router upd warn="" yazabilir)
            st = R.read_state(p); st["4100000001"]["note"] = ""; R.write_state(p, st)
        rc, log = self.akis(degis=warn_bos); self.assertEqual(rc, 0, log)

    def test_17_hedef_gorsel_sayisi(self):                 # galeri v10: PASS esigi kayittaki beklenen gorsel sayisi (9)
        self.hazirla("galeri")
        def v10(p):
            v = json.loads(Path(p).read_text()); v["ilanlar"]["4570000009"] = {"cift": "C_C", "set": 9, "hedef": 9, "durum": "PASS"}
            Path(p).write_text(json.dumps(v))
        rc, log = self.akis(degis=v10); self.assertEqual(rc, 0, log)
        def geri(p):
            v = json.loads(Path(p).read_text()); v["ilanlar"]["4570000009"]["durum"] = "DUR"; Path(p).write_text(json.dumps(v))
        b = self.uzak_b(); rc, log = self.akis(degis=geri)
        self.assertEqual(rc, 1, log); self.assertIn("PASS'tan geri donen ilan 1", log); self.assertEqual(self.uzak_b(), b)

    def test_08_kayit_azalmasi(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(degis=self.A["sil"])
            self.assertEqual(rc, 1, log); self.assertIn("korunmadi", log); self.assertEqual(self.uzak_b(), b); self.assertFalse(self.yedekler())

    def test_09_degisiklik_yok(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(degis=lambda p: None)
            self.assertEqual(rc, 0, log); self.assertIn("degismedi", log); self.assertEqual(self.uzak_b(), b); self.assertFalse(self.yedekler())

    def test_10_yedek_30_siniri(self):
        for ad in self.her_akis():
            self.hazirla(ad)
            st, uz = self.uzak_p.stem, self.uzak_p.suffix
            yd = self.uzak_p.parent / "YEDEK"; yd.mkdir()
            eski = [yd / f"{st}_202610{g:02d}T000000000000Z_{g}{uz}" for g in range(1, 31)]
            for p in eski:
                p.write_bytes(b"eski")
            yabanci = yd / f"BASKA_20261001T000000000000Z_1{uz}"; yabanci.write_bytes(b"x")
            elle = yd / f"{st}_elle_not{uz}"; elle.write_bytes(b"x")                # desene uymayan: dokunulmaz
            kokte = self.uzak_p.parent / f"{st}_20261001T000000000000Z_1{uz}"; kokte.write_bytes(b"x")   # YEDEK/ disi
            rc, log = self.akis()
            self.assertEqual(rc, 0, log); self.assertIn("1 eski yedek silindi", log)
            kalan = [p for p in self.yedekler() if p.name != elle.name]
            self.assertEqual(len(kalan), 30); self.assertFalse(eski[0].exists()); self.assertTrue(eski[1].exists())
            self.assertTrue(yabanci.exists() and elle.exists() and kokte.exists())

    def test_11_yedek_yazilamiyor(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(hata_yaz="copyto_yedek")
            self.assertEqual(rc, 1); self.assertIn("yedek yazilamadi", log); self.assertEqual(self.uzak_b(), b)

    def test_12_ayni_adli_iki_dosya(self):
        for ad in self.her_akis():
            b = self.hazirla(ad)
            rc, log = self.akis(hata_oku="lsjson_cift")
            self.assertEqual(rc, 1); self.assertIn("belirsiz", log); self.assertEqual(self.uzak_b(), b)

    def test_13_logda_kimlik_yok(self):
        for ad in self.her_akis():
            self.hazirla(ad)
            _, log = self.akis(degis=self.A["sil"])
            for gizli in ("4100000001", "5000000001", "4570000002"):
                self.assertNotIn(gizli, log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
