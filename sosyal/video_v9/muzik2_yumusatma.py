"""ADAY_09 final v2: (1) tame the loud swell at the wall scene (17.5-19.5 s) with a slow look-ahead gain,
(2) let the last chord ring on with a soft reverb tail and glide down smoothly so the music closes exactly at 24.0 s."""
import numpy as np, soundfile as sf, subprocess, re
from scipy.ndimage import gaussian_filter1d, minimum_filter1d
from scipy.signal import fftconvolve
S = '/tmp/claude-0/-home-claude/b27d1999-de9e-588b-b6f9-3ab0fbf52d0b/scratchpad'
x, sr = sf.read(S + '/muzik2/ADAY_09_ozel.wav'); x = x.T if x.ndim == 2 else x[None]
DUR = 24.0; N = int(DUR * sr)
hop = int(0.01 * sr)

def env_db(sig, win_s=0.4):
    m = sig.mean(0); win = int(win_s * sr)
    pw = np.convolve(m ** 2, np.ones(win) / win, mode='same')
    d = 10 * np.log10(pw[::hop] + 1e-12); return np.arange(len(d)) * hop / sr, d

# 1) reverb tail from the final chord so the sound does not die before the end card is over
rng = np.random.default_rng(3); L = int(3.0 * sr)
ir = rng.normal(0, 1, L) * np.exp(-np.linspace(0, 4.5, L)); ir /= np.sqrt((ir ** 2).sum())
a0, a1 = int(21.0 * sr), int(22.8 * sr)
src = x[:, a0:a1] * np.hanning(2 * (a1 - a0))[None, a1 - a0:] ** 0.5 * 0 + x[:, a0:a1] * np.linspace(1, 0.6, a1 - a0)[None]
tail = np.stack([fftconvolve(src[c], ir)[: N - a0] for c in range(x.shape[0])])
y = np.zeros((x.shape[0], N)); y[:, :x.shape[1]] = x[:, :N]
y[:, a0:a0 + tail.shape[1]] += 0.55 * tail

# 2) gain curve: cap the swell at the body level, then a smooth glide to silence at 24.0 s
t, d = env_db(y, 0.2)
ref = np.median(d[(t > 8) & (t < 15)])
g = np.minimum(0, ref + 1.5 - d)
g = gaussian_filter1d(minimum_filter1d(g, int(0.5 / 0.01)), 0.22 / 0.01)
g = np.minimum(g, gaussian_filter1d(np.minimum(0, ref + 1.5 - d), 0.05 / 0.01))   # never let a quick hit through
t_g = np.arange(len(g)) * 0.01
y1 = y * 10 ** (np.interp(np.arange(N) / sr, t_g, g) / 20)[None]
t, d = env_db(y1, 0.3)
start = float(np.interp(20.0, t, d))
s = np.clip((t - 20.0) / 4.0, 0, 1)
target = start + (-62 - start) * (1 - np.cos(np.pi * s / 2) ** 1.0) ** 1.6       # slow at first, then down to silence
corr = np.where(t >= 20.0, np.clip(target - d, -60, 10), 0)
corr = gaussian_filter1d(corr, 0.25 / 0.01)
y2 = y1 * 10 ** (np.interp(np.arange(N) / sr, t, corr) / 20)[None]
fe = int(0.35 * sr); y2[:, -fe:] *= np.cos(np.linspace(0, np.pi / 2, fe))[None]
sf.write(S + '/_m2_yeni_raw.wav', y2.T, sr, subtype='FLOAT')

def lufs(f):
    e = subprocess.run(['ffmpeg', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)[-1])

gdb = 0.0
for it in range(5):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', S + '/_m2_yeni_raw.wav', '-af',
                    f'volume={gdb:.2f}dB,alimiter=limit=0.8:attack=5:release=80:level=false,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', '-t', '24', S + '/_m2_yeni.m4a'], check=True)
    I, P = lufs(S + '/_m2_yeni.m4a')
    if abs(I + 16) < 0.2: break
    gdb += -16 - I
print(f'{I:.1f} LUFS, true peak {P:.1f} dBTP, body ref {ref:.1f}, max swell pull {g.min():.1f} dB')
