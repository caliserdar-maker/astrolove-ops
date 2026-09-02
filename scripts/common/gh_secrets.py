#!/usr/bin/env python3
"""
GitHub Actions secret / variable yazan yardimci (libsodium sealed box).

Bundan sonra her secret bununla eklenir; kimseye elle GitHub islemi
yaptirilmaz. Yetki OPS_ADMIN_TOKEN'dan gelir (fine-grained PAT: astrolove-ops
+ astrolove-media, Secrets/Variables/Contents/Actions/Workflows RW).

Kullanim (kod icinden):
    from gh_secrets import set_secret, set_variable
    set_secret("astrolove-ops", "IG_TOKEN", value, admin_token)
    set_variable("astrolove-ops", "IG_PUBLISH_ENABLED", "true", admin_token)

Komut satiri (deger STDIN'den, sohbet/loga dusmesin):
    printf '%s' "$VALUE" | python gh_secrets.py secret astrolove-ops IG_TOKEN
    python gh_secrets.py variable astrolove-ops IG_PUBLISH_ENABLED true
Admin token: --token, yoksa OPS_ADMIN_TOKEN ortam degiskeni.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from nacl import encoding, public

OWNER = os.environ.get("GH_OWNER", "caliserdar-maker")
API = "https://api.github.com"


def _req(method, url, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')[:300]}")


def _seal(public_key_b64, value):
    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(value.encode())
    return base64.b64encode(sealed).decode()


def set_secret(repo, name, value, token):
    """repo: 'astrolove-ops' (owner otomatik). Deger sealed box ile sifrelenir."""
    base = f"{API}/repos/{OWNER}/{repo}/actions/secrets"
    _, key = _req("GET", f"{base}/public-key", token)
    st, _ = _req("PUT", f"{base}/{name}", token, {
        "encrypted_value": _seal(key["key"], value), "key_id": key["key_id"]})
    return st                                    # 201 olusturuldu, 204 guncellendi


def set_variable(repo, name, value, token):
    base = f"{API}/repos/{OWNER}/{repo}/actions/variables"
    try:                                         # once guncelle
        _req("PATCH", f"{base}/{name}", token, {"name": name, "value": value})
        return 204
    except RuntimeError:                         # yoksa olustur
        _req("POST", base, token, {"name": name, "value": value})
        return 201


def _token(arg):
    t = arg or os.environ.get("OPS_ADMIN_TOKEN")
    if not t:
        sys.exit("HATA: token yok (--token veya OPS_ADMIN_TOKEN).")
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["secret", "variable"])
    ap.add_argument("repo")
    ap.add_argument("name")
    ap.add_argument("value", nargs="?", help="variable icin deger; secret icin STDIN'den okunur")
    ap.add_argument("--token")
    a = ap.parse_args()
    tok = _token(a.token)
    if a.kind == "secret":
        value = a.value if a.value is not None else sys.stdin.read()
        if value.endswith("\n"):
            value = value[:-1]
        st = set_secret(a.repo, a.name, value, tok)
        print(f"secret {a.repo}/{a.name}: {'olusturuldu' if st == 201 else 'guncellendi'}")
    else:
        if a.value is None:
            sys.exit("HATA: variable icin deger gerekli.")
        st = set_variable(a.repo, a.name, a.value, tok)
        print(f"variable {a.repo}/{a.name}: {'olusturuldu' if st == 201 else 'guncellendi'}")


if __name__ == "__main__":
    main()
