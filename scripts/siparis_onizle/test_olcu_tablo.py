"""olcu_tablo testi (21 Kas, GOREV SIPARIS_HATTI_DIJITAL 4). Ag YOK.
1) docs/OLCU_TABLOSU.md == olcu_tablo.belge() (belge elle bozulursa FAIL; bilinen FAIL: bir piksel degistirilmis kopya).
2) zemin_duzelt.OLCU (halka_kapi'nin kullandigi ikinci kopya) == olcu_tablo.PX (kaynak).
3) siparis-giris.yml olcu secenekleri (musteriye satilan olculer) == PX anahtarlari; her biri kesit_olcum.PX'te ve olcu_oku ile okunur
   (21 Kas hatasi: kesit_olcum.INC'de A4/A3/A2 yoktu -> KeyError; bilinen FAIL: eski INC sozlugu A3'u bilmez)."""
import ast
import socket
import sys
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/siparis_onizle"))


def _ag_yok(*a, **k):
    raise OSError("test: ag kapali")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok

import olcu_tablo as OT  # noqa: E402
import kesit_olcum as K  # noqa: E402

SONUC = []


def kontrol(ad, ok, ek=""):
    SONUC.append(bool(ok)); print(("PASS " if ok else "FAIL ") + ad + (f" [{ek}]" if ek and not ok else ""))


belge = (KOK / "docs/OLCU_TABLOSU.md").read_text(encoding="utf-8")
kontrol("1 belge == kaynak", belge == OT.belge())
bozuk = belge.replace("4800 x 6000", "6000 x 7500")
kontrol("1b bilinen FAIL: piksel degistirilmis belge kaynakla tutmaz", bozuk != OT.belge() and bozuk != belge)
zd = next(ast.literal_eval(d.value) for d in ast.parse((KOK / "scripts/siparis_onizle/zemin_duzelt.py").read_text()).body
          if isinstance(d, ast.Assign) and any(getattr(t, "id", "") == "OLCU" for t in d.targets))
kontrol("2 zemin_duzelt.OLCU == olcu.py OLCU", {k: tuple(v) for k, v in zd.items()} == OT.PX, str(set(zd) ^ set(OT.PX)))
kontrol("2b 16x20 = 4800x6000 (STEP 1 duzeltmesi: 6000x7500 degil)", OT.PX["16x20"] == (4800, 6000))
gir = yaml.safe_load((KOK / ".github/workflows/siparis-giris.yml").read_text())
secenek = gir[True]["workflow_dispatch"]["inputs"]["olcu"]["options"] if True in gir else gir["on"]["workflow_dispatch"]["inputs"]["olcu"]["options"]
kontrol("3 siparis-giris olcu secenekleri == olcu.py OLCU anahtarlari", set(secenek) == set(OT.PX), str(set(secenek) ^ set(OT.PX)))
kontrol("3b her satilan olcu kesit_olcum.PX'te", all(o in K.PX for o in secenek), str([o for o in secenek if o not in K.PX]))
etiket = {o: (f"{o} in" if o[0].isdigit() else o) for o in secenek}
kontrol("3c olcu_oku her olcuyu okur", all(K.olcu_oku(e) == o for o, e in etiket.items()), str({o: K.olcu_oku(e) for o, e in etiket.items()}))
ESKI_INC = {"5x7": (5, 7), "8x10": (8, 10), "11x14": (11, 14), "12x16": (12, 16), "12x18": (12, 18), "16x20": (16, 20), "16x24": (16, 24),
            "18x24": (18, 24), "20x30": (20, 30), "24x30": (24, 30), "24x36": (24, 36)}
kontrol("3d bilinen FAIL: eski INC sozlugu A4/A3/A2'yi bilmezdi", [o for o in secenek if o not in ESKI_INC] == ["A4", "A3", "A2"]
        or sorted(o for o in secenek if o not in ESKI_INC) == ["A2", "A3", "A4"])
print(f"SONUC: {sum(SONUC)}/{len(SONUC)} PASS")
sys.exit(0 if all(SONUC) else 1)
