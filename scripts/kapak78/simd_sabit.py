#!/usr/bin/env python3
"""Kart / gorunum uretiminde SIMD yolunu sabitler (Serdar 31 Eki karar 8a). Kok neden (olcum, kart-determinizm kosulari 41186253130 /
41187364930 + yerel): NumPy AVX512 (X86_V4) olan islemcide arcsin / cos / us (**) icin farkli kod yolu secer, sonuc bit duzeyinde degisir;
fark gorunum -> GrabCut maskesi zincirinde buyur (kart farki en cok 237 / 255). AMD EPYC 7763 (AVX512 yok, ubuntu-24.04) gorunumleri
AVX512'li Intel 8573C / AMD 9V74 / 9V45 / yerel ile farkli; AVX512 kapatilinca yerel sonuc AVX2 yoluyla birebir (ayni olcum dizisi sha
e8794ab836, numpy 2.1.3 ve 2.5.3).
ayarla(env): NumPy (surume gore ozellik adlari) ve OpenCV AVX512 yolunu kapatan ortam degiskenlerini env'e yazar (numpy import edilmeden
once). prob(python, env): o python + env ile olcum dizisinin sha'si; REF ile esit degilse uretim DUR (kapi).
IMAJ: kart is akislari ubuntu-24.04'e sabit (Ubuntu 26.04 / glibc 2.43 koşucusunda AVX512 kapaliyken bile gorunum farkli cikti,
kart-determinizm 41188852196); olcum dizisi ust / us / exp icerdigi icin libm farki da kapida yakalanir."""
import json
import os
import subprocess
import sys

# numpy surumu -> dagitilan AVX512 hedefleri. DIKKAT (inceleme 31 Eki): baska surumun adi HATA VERMEZ, yalniz uyari basar ve ozellik
# acik kalir; bu yuzden kapi ayrica __cpu_features__ ile bu adlarin KAPALI oldugunu dogrular (ozellik_kapisi).
NPY = {"2.1": "AVX512F AVX512CD AVX512_KNL AVX512_KNM AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL",
       "2.5": "X86_V4 AVX512_ICL AVX512_SPR"}
OPENCV = "AVX512-SKX"      # cv2.getCPUFeaturesLine adi (4.10 ve 5.0); kapaninca satirda 'AVX512-SKX?' gorunur
BLAS = "Haswell"           # OpenBLAS cekirdegi sabit: Intel varsayilani SkylakeX, AMD Zen = Haswell cekirdegi; zemin (a @ v) farki
                           # yerel Intel SkylakeX 42291882 / Haswell 68ccab78 = AMD 7763 ubuntu-24.04 68ccab78 (z_stil_almond, 31 Eki)
# olcum dizisi: arcsin / cos / us / exp + float32 matris-vektor (BLAS); AVX512 kapali, Haswell, glibc 2.39 (ubuntu-24.04) yerel olcum 31 Eki
REF = "e8794ab836-a38ffcf3ae-8c8af32bc5-d25123e70c-8d81ca0f2b"
PROB = ("import numpy as np, hashlib\n"
        "x = np.linspace(-0.999, 0.999, 2_000_003)\n"
        "h = lambda a: hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:10]\n"
        "m = (np.arange(3_000_000, dtype=np.float32).reshape(-1, 3) % 251) @ np.float32([0.299, 0.587, 0.114])\n"
        "print('-'.join([h(np.arcsin(x)), h(np.cos(np.arcsin(x))), h(np.clip(x, 0, 1) ** 0.6), h(np.exp(x)), h(m)]))")


def numpy_surum(python):
    e = {k: v for k, v in os.environ.items() if k != "NPY_DISABLE_CPU_FEATURES"}
    r = subprocess.run([python, "-c", "import importlib.metadata as m; print(m.version('numpy'))"], capture_output=True, text=True,
                       env=e)
    if r.returncode:
        raise SystemExit(f"DUR: {python} numpy surumu okunamadi: {r.stderr[-200:]}")
    return ".".join(r.stdout.strip().split(".")[:2])


def ayarla(env, python=sys.executable):
    s = numpy_surum(python)
    if s not in NPY:
        raise SystemExit(f"DUR: numpy {s} icin AVX512 ozellik listesi tanimsiz (simd_sabit.NPY); olcmeden eklenmez")
    env["NPY_DISABLE_CPU_FEATURES"] = NPY[s]
    env["OPENCV_CPU_DISABLE"] = OPENCV
    env["OPENBLAS_CORETYPE"] = BLAS
    return env


def prob(python, env):
    r = subprocess.run([python, "-c", PROB], capture_output=True, text=True, env=env)
    return r.stdout.strip() if r.returncode == 0 else f"HATA {r.stderr.strip()[-200:]}"


OZ = ("import json, re\n"
      "from numpy._core._multiarray_umath import __cpu_features__ as f\n"
      "import os\n"
      "acik = [k for k in os.environ.get('NPY_DISABLE_CPU_FEATURES', '').split() if f.get(k)]\n"
      "try:\n"
      "    import cv2; cv = [t for t in cv2.getCPUFeaturesLine().split() if 'AVX512' in t and not t.endswith('?')]\n"
      "except ImportError:\n"
      "    cv = None\n"
      "print(json.dumps(dict(npy_acik=acik, cv_acik=cv)))")


def ozellik_kapisi(python, env, ad):
    """inceleme 31 Eki: (1) env'deki NPY_DISABLE_CPU_FEATURES adlarinin o python'daki numpy'de GERCEKTEN kapali oldugu (__cpu_features__),
    (2) OpenCV kuruluysa AVX512 ozelliginin '?' (kapali) oldugu (getCPUFeaturesLine). prob() OpenCV'yi olcmuyordu."""
    r = subprocess.run([python, "-c", OZ], capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"DUR: SIMD ozellik kapisi {ad}: {r.stderr.strip()[-200:]}")
    o = json.loads(r.stdout.strip().splitlines()[-1])
    if o["npy_acik"] or o["cv_acik"]:
        raise SystemExit(f"DUR: SIMD ozellik kapisi {ad}: acik kalan numpy {o['npy_acik']} / opencv {o['cv_acik']}")
    return o


def surec_ici(ad):
    """calisan surecte (numpy / cv2 zaten yuklu) ayni denetim."""
    from numpy._core._multiarray_umath import __cpu_features__ as f
    acik = [k for k in os.environ.get("NPY_DISABLE_CPU_FEATURES", "").split() if f.get(k)]
    cv = []
    if "cv2" in sys.modules:
        cv = [t for t in sys.modules["cv2"].getCPUFeaturesLine().split() if "AVX512" in t and not t.endswith("?")]
    if acik or cv or not os.environ.get("NPY_DISABLE_CPU_FEATURES"):
        raise SystemExit(f"DUR: SIMD surec ici kapi {ad}: numpy acik {acik} / opencv acik {cv}")
    return dict(npy_kapali=os.environ["NPY_DISABLE_CPU_FEATURES"].split())


def kapi(python, env, ad):
    p = prob(python, env)
    if p != REF:
        raise SystemExit(f"DUR: SIMD kapisi {ad}: olcum {p} != {REF} (AVX512 yolu kapali degil ya da ortam farkli)")
    ozellik_kapisi(python, env, ad)
    return p


if __name__ == "__main__":
    for py in sys.argv[1:] or [sys.executable]:
        e = ayarla(dict(os.environ), py)
        print(py, numpy_surum(py), "acik:", prob(py, {k: v for k, v in os.environ.items() if k != "NPY_DISABLE_CPU_FEATURES"}),
              "kapali:", prob(py, e), "REF", REF)
