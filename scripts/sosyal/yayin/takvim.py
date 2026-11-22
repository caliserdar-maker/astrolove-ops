"""SOSYAL_TAKVIM Google Sheet okuma/yazma (Sheets API v4, rclone.conf'daki Google kimligi; plan 4.2).
Sheet kimligi repo degiskeni SOSYAL_TAKVIM_ID (depoya yazilmaz). Sayfa adi SOSYAL_TAKVIM_SAYFA (varsayilan TAKVIM)."""
import configparser
import os
from pathlib import Path

from ortak import Hata, gizle
from secim import SUTUNLAR

API = "https://sheets.googleapis.com/v4/spreadsheets"


def google_token(http, conf=None, remote=None):
    conf = Path(conf or os.environ.get("RCLONE_CONFIG", Path.home() / ".config/rclone/rclone.conf"))
    remote = remote or os.environ.get("RCLONE_REMOTE", "gdrive")
    if not conf.exists():
        raise Hata("rclone.conf yok")
    cp = configparser.ConfigParser()
    cp.read(conf)
    if remote not in cp:
        raise Hata(f"rclone.conf icinde [{remote}] yok")
    import json
    sec = cp[remote]
    cid = os.environ.get("RCLONE_CONFIG_GDRIVE_CLIENT_ID") or sec.get("client_id", "")
    csec = os.environ.get("RCLONE_CONFIG_GDRIVE_CLIENT_SECRET") or sec.get("client_secret", "")
    rt = json.loads(sec.get("token", "{}")).get("refresh_token", "")
    if not (cid and csec and rt):
        raise Hata("rclone.conf: client_id / client_secret / refresh_token eksik")
    gizle(csec, rt)
    j, _ = http.iste("POST", "https://oauth2.googleapis.com/token",
                     data={"client_id": cid, "client_secret": csec, "refresh_token": rt, "grant_type": "refresh_token"})
    t = j.get("access_token", "")
    if not t:
        raise Hata("Google access_token alinamadi")
    gizle(t)
    return t


def _harf(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


class Takvim:
    def __init__(self, http, token, sheet_id=None, sayfa=None):
        self.http, self.token = http, token
        self.id = sheet_id or os.environ.get("SOSYAL_TAKVIM_ID", "")
        self.sayfa = sayfa or os.environ.get("SOSYAL_TAKVIM_SAYFA", "TAKVIM")
        if not self.id:
            raise Hata("SOSYAL_TAKVIM_ID tanimli degil")
        self.baslik = []

    def oku(self):
        j, _ = self.http.iste("GET", f"{API}/{self.id}/values/{self.sayfa}", token=self.token)
        rows = j.get("values", [])
        if not rows:
            raise Hata("takvim bos")
        self.baslik = [c.strip() for c in rows[0]]
        eksik = [c for c in SUTUNLAR if c not in self.baslik]
        if eksik:
            raise Hata(f"takvimde eksik sutun: {', '.join(eksik)}")
        out = []
        for i, r in enumerate(rows[1:], start=2):
            d = {c: (r[k] if k < len(r) else "") for k, c in enumerate(self.baslik)}
            if not any(str(v).strip() for v in d.values()):
                continue
            d["_sheet_satir"] = i
            out.append(d)
        nolar = [d["satir_no"] for d in out if d.get("satir_no")]
        if len(nolar) != len(set(nolar)):
            raise Hata("takvimde tekrarlanan satir_no var")
        return out

    def hucre(self, satir, sutun):
        return f"{self.sayfa}!{_harf(self.baslik.index(sutun))}{satir['_sheet_satir']}"

    def tazele(self, satir):
        """Satirin bulundugu yeri yeniden okur; satir_no ve ONAY_OZET ayni degilse Hata (siralama / satir ekleme kaymasi)."""
        son = _harf(len(self.baslik) - 1)
        n = satir["_sheet_satir"]
        j, _ = self.http.iste("GET", f"{API}/{self.id}/values/{self.sayfa}!A{n}:{son}{n}", token=self.token)
        r = (j.get("values") or [[]])[0]
        d = {c: (r[k] if k < len(r) else "") for k, c in enumerate(self.baslik)}
        for alan in ("satir_no", "ONAY_OZET"):
            if (d.get(alan) or "").strip() != (satir.get(alan) or "").strip():
                raise Hata(f"takvim satiri kaydi (Sheet satir {n}: {alan} degisti); kosu durdu")
        return d

    def durum_oku(self, satir):
        """Yazmadan hemen once DURUM'u tazeden okur (baska kosu yazdiysa bos degildir)."""
        j, _ = self.http.iste("GET", f"{API}/{self.id}/values/{self.hucre(satir, 'DURUM')}", token=self.token)
        v = j.get("values", [[""]])
        return (v[0][0] if v and v[0] else "").strip()

    def yaz(self, satir, **alanlar):
        veri = [{"range": self.hucre(satir, k), "values": [[v]]} for k, v in alanlar.items()]
        self.http.iste("POST", f"{API}/{self.id}/values:batchUpdate", token=self.token,
                       json_govde={"valueInputOption": "RAW", "data": veri})
        satir.update(alanlar)
