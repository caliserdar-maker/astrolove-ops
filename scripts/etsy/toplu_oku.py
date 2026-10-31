#!/usr/bin/env python3
"""Toplu kapi okumasi (Serdar 31 Eki 1a, Etsy istek azaltma madde 3-4). YALNIZ GET.
toplu(api, ilanlar): 100'luk parcada 2 istek: GET /listings/batch?listing_ids=..&includes=Images,Videos,Personalization,Translations
  (getListingsByListingIds) + GET /listings/batch/inventory?listing_ids=.. (Etsy dokumani, Merkez 31 Eki: en fazla 100 ilan; Inventory /
  Shipping includes'tan kaldirildi). Yanit sekli 31 Eki yoklamasiyla olculdu (TEMP/TOPLU_OKU_YOKLA, 4598525642 + 4595350971):
  results[] ilan nesnesi; images / videos listesi; personalization.personalization_questions (question_id); translations[dil] (yoksa
  None); batch/inventory results[].inventory (tekil getListingInventory ile ayni sekil: products / offerings / property_values).
  Style variation-images toplu uc yok: ilan basina tekil GET.
  -> {ilan (str): dict(L (ilan nesnesi, images / videos / inventory / translations / personalization disinda), galeri (rank sirali),
     video, inv, per, ru)}; yanitta eksik / bicimsiz ilan sozlukte yoktur (cagiran tekil okumaya duser).
Tohumlu(api, shop, kayit): tekil GET'leri (ilan, galeri, video, envanter) toplu yanittan veren istemci sarmalayicisi; ayni GET ikinci kez
  onbellekten (variation-images ilk okumadan sonra). ILK YAZIM cagrisinda onbellek kapanir: yazim sonrasi her okuma CANLI
  (dogrulama / geri alma kararlari tekil okumayla; Merkez 31 Eki madde 4)."""
import copy
import json

TOPLU_N = 100
TOPLU_INCLUDES = "Images,Videos,Personalization,Translations"
L_DISI = ("images", "videos", "inventory", "translations", "personalization")


def toplu(api, ilanlar):
    out = {}
    ids = [str(x) for x in dict.fromkeys(ilanlar)]
    for i in range(0, len(ids), TOPLU_N):
        p = ids[i:i + TOPLU_N]
        L = {str(x.get("listing_id")): x for x in (api.get("/listings/batch", params={"listing_ids": ",".join(p), "includes": TOPLU_INCLUDES})
                                                   or {}).get("results") or []}
        V = {str(x.get("listing_id")): x.get("inventory") for x in (api.get("/listings/batch/inventory", params={"listing_ids": ",".join(p)})
                                                                     or {}).get("results") or []}
        for lid in p:
            x = L.get(lid)
            if not x or not isinstance(V.get(lid), dict) or not isinstance(x.get("images"), list) or not isinstance(x.get("videos"), list):
                continue
            out[lid] = dict(L={k: v for k, v in x.items() if k not in L_DISI},
                            galeri=sorted(x["images"], key=lambda g: g.get("rank") or 0), video=list(x["videos"]), inv=V[lid],
                            per=list((x.get("personalization") or {}).get("personalization_questions") or []),
                            ru=(x.get("translations") or {}).get("ru") or {})
    return out


def _anahtar(path, params, ok404):
    return (path, json.dumps(params, sort_keys=True, ensure_ascii=False), bool(ok404))


class Tohumlu:
    """Tek ilan icin: toplu yanit ile tohumlanmis GET onbellegi; ilk yazimda kapanir. Diger ozellikler asil istemciden."""
    def __init__(self, api, lid, kayit):
        self._a, self._c, self.acik, self.tohum = api, {}, True, bool(kayit)
        if kayit:
            lid = str(lid)
            for ok in (False, True):   # ayni uc farkli ok404 ile cagrilabilir
                self._c[_anahtar(f"/listings/{lid}", None, ok)] = copy.deepcopy(kayit["L"])
                self._c[_anahtar(f"/listings/{lid}/images", None, ok)] = {"count": len(kayit["galeri"]), "results": copy.deepcopy(kayit["galeri"])}
                self._c[_anahtar(f"/listings/{lid}/videos", None, ok)] = {"count": len(kayit["video"]), "results": copy.deepcopy(kayit["video"])}
                self._c[_anahtar(f"/listings/{lid}/inventory", None, ok)] = copy.deepcopy(kayit["inv"])

    def __getattr__(self, k):
        return getattr(self._a, k)

    def get(self, path, params=None, ok404=False):
        k = _anahtar(path, params, ok404)
        if self.acik and k in self._c:
            return copy.deepcopy(self._c[k])
        r = self._a.get(path, params, ok404)
        if self.acik:
            self._c[k] = copy.deepcopy(r)
        return r

    def kapat(self):
        self.acik = False; self._c.clear()

    def _yaz(self, ad, *a, **k):
        self.kapat(); return getattr(self._a, ad)(*a, **k)

    def post(self, *a, **k):
        return self._yaz("post", *a, **k)

    def put(self, *a, **k):
        return self._yaz("put", *a, **k)

    def patch(self, *a, **k):
        return self._yaz("patch", *a, **k)

    def delete(self, *a, **k):
        return self._yaz("delete", *a, **k)

    def post_file(self, *a, **k):
        return self._yaz("post_file", *a, **k)

    def post_json(self, *a, **k):
        return self._yaz("post_json", *a, **k)

    def put_json(self, *a, **k):
        return self._yaz("put_json", *a, **k)
