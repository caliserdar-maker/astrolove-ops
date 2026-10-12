"""ADAY_09 final v3: the 'burst' at the wall scene is a bright cymbal swell (energy above ~1 kHz jumps +15-25 dB at
16.8-18.6 s while the overall RMS hardly moves). Pull down only the bright bands, only there, with slow smooth gains."""
import numpy as np, soundfile as sf, librosa, subprocess, re
from scipy.ndimage import gaussian_filter1d, minimum_filter1d
S = '/tmp/claude-0/-home-claude/b27d1999-de9e-588b-b6f9-3ab0fbf52d0b/scratchpad'
y, sr = sf.read(S + '/_m2_yeni_raw.wav'); y = y.T
nfft, hop = 2048, 256
Z = [librosa.stft(y[c], n_fft=nfft, hop_length=hop) for c in range(y.shape[0])]
P = sum(np.abs(z) ** 2 for z in Z)
fr = librosa.fft_frequencies(sr=sr, n_fft=nfft); tt = librosa.frames_to_time(np.arange(P.shape[1]), sr=sr, hop_length=hop)
bands = [(1000, 3000), (3000, sr / 2)]
G = np.zeros_like(P)                                     # gain in dB per bin and frame
dt = hop / sr
for lo, hi in bands:
    sel = (fr >= lo) & (fr < hi)
    lev = 10 * np.log10(P[sel].sum(0) + 1e-12)
    lev = gaussian_filter1d(lev, 0.08 / dt)
    ref = np.median(lev[(tt > 10) & (tt < 16)])
    g = np.minimum(0, ref + 2.0 - lev)
    g = np.where((tt > 15.5) & (tt < 21.0), g, 0)        # only around the wall scene
    g = gaussian_filter1d(minimum_filter1d(g, int(0.4 / dt)), 0.15 / dt)
    w = np.clip((fr - lo * 0.7) / (lo * 0.3), 0, 1) * (fr < hi * 1.0 + (hi == sr / 2) * 1e9)   # soft lower edge
    G += w[:, None] * g[None, :]
    print(f'{lo}-{int(hi)} Hz: ref {ref:.1f} dB, max cut {g.min():.1f} dB')
G = np.maximum(G, -22)
out = np.stack([librosa.istft(z * 10 ** (G / 20), hop_length=hop, length=y.shape[1]) for z in Z])
sf.write(S + '/_m2_v3_raw.wav', out.T, sr, subtype='FLOAT')

def lufs(f):
    e = subprocess.run(['ffmpeg', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)[-1])
gdb = 0.0
for it in range(5):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', S + '/_m2_v3_raw.wav', '-af',
                    f'volume={gdb:.2f}dB,alimiter=limit=0.8:attack=5:release=80:level=false,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', '-t', '24', S + '/_m2_v3.m4a'], check=True)
    I, Pk = lufs(S + '/_m2_v3.m4a')
    if abs(I + 16) < 0.2: break
    gdb += -16 - I
print(f'{I:.1f} LUFS, true peak {Pk:.1f}')
