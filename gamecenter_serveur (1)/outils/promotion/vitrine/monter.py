"""Vidéo « vitrine » (promotion, 04/11/2026) : images du tournage (tourner.js) + carton (carton.js) → MP4.
   python3 monter.py <L|P> <out_dir> <end_dir> <musique.mp3> <sortie.mp4>
Caméra sous-pixel (le cadre filmé est recadré exactement), transitions floues en fondu avec un léger zoom (comme la
vidéo de référence), ouverture depuis le noir, son : musique du site + « whoosh » aux transitions + clic."""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageFilter

F, OUT, END, MUSIC, DEST = sys.argv[1:6]
OW, OH = (1920, 1080) if F == 'L' else (1080, 1920)
FPS, DPR = 30, 3
meta = json.load(open(os.path.join(OUT, 'frames.json')))
frames = meta['frames']
BG = (6, 10, 19)

# scènes dans l'ordre, avec leurs images
scenes = []
for m in frames:
    if not scenes or scenes[-1]['name'] != m['scene']:
        scenes.append({'name': m['scene'], 'frames': []})
    scenes[-1]['frames'].append(m)
ends = sorted(f for f in os.listdir(END) if f.endswith('.png'))
scenes.append({'name': 'end', 'frames': [{'end': os.path.join(END, f)} for f in ends]})

OV = 10                        # chevauchement d'une transition (images)
NO_CUT = set()
TRIM = {'home': 118}           # la fenêtre du match s'ouvre au clic (3,62 s) : on coupe juste après
for sc in scenes:
    if sc['name'] in TRIM:
        sc['frames'] = sc['frames'][:TRIM[sc['name']]]


def render(m, k=1.0):
    """une image de la scène → image de sortie ; k < 1 : zoom avant (pour les transitions)"""
    if 'end' in m:
        im = Image.open(m['end']).convert('RGB')
        if im.size != (OW, OH):
            im = im.resize((OW, OH), Image.LANCZOS)
        if k != 1.0:
            w, h = OW * k, OH * k
            im = im.transform((OW, OH), Image.EXTENT, ((OW - w) / 2, (OH - h) / 2, (OW + w) / 2, (OH + h) / 2), Image.BICUBIC)
        return im
    im = Image.open(os.path.join(OUT, 'f%05d.jpg' % m['f'])).convert('RGB')
    x, y, w, h = m['cam']
    s = min(1.0, OW / w * 1.08 / DPR) * DPR
    cx, cy = x + w / 2, y + h / 2
    w, h = w * k, h * k
    x0, y0 = m['clip']
    box = ((cx - w / 2 - x0) * s, (cy - h / 2 - y0) * s, (cx + w / 2 - x0) * s, (cy + h / 2 - y0) * s)
    return im.transform((OW, OH), Image.EXTENT, box, Image.BICUBIC, fillcolor=BG)


def blur(im, r):
    return im.filter(ImageFilter.GaussianBlur(r)) if r > 0.3 else im


ease = lambda q: q * q * (3 - 2 * q)

# le plan de montage : liste d'images de sortie = [(scène A, i, k, poids, flou), (scène B, …)]
plan, events = [], []
t = 0
for si, sc in enumerate(scenes):
    n = len(sc['frames'])
    nxt = scenes[si + 1] if si + 1 < len(scenes) else None
    cut_in = si > 0 and (scenes[si - 1]['name'], sc['name']) not in NO_CUT
    cut_out = nxt is not None and (sc['name'], nxt['name']) not in NO_CUT
    start = OV if cut_in else 0
    stop = n - OV if cut_out else n
    for i in range(start, stop):
        plan.append([(sc, i, 1.0, 1.0, 0.0)])
    if cut_out:
        events.append(('whoosh', len(plan) / FPS))
        for j in range(OV):
            q = (j + .5) / OV
            a = (sc, n - OV + j, 1 - .10 * ease(q), 1 - ease(q), 22 * math.sin(math.pi * q))
            b = (nxt, j, 1.08 - .08 * ease(q), ease(q), 22 * math.sin(math.pi * q))
            plan.append([a, b])
    if sc['name'] == 'home':
        events.append(('click', 3.5))
total = len(plan)
print(F, 'images de sortie :', total, '=', round(total / FPS, 2), 's')

# image
tmp_v = DEST + '.video.mp4'
ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                       '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp_v],
                      stdin=subprocess.PIPE)
INTRO = 14
for o, layers in enumerate(plan):
    out = None
    for (sc, i, k, wgt, r) in layers:
        m = sc['frames'][i]
        if o < INTRO:                       # ouverture : du noir, flou → net, léger recul
            q = ease((o + 1) / INTRO)
            k = k * (0.92 + 0.08 * q)
            r = max(r, 18 * (1 - q))
        im = blur(render(m, k), r)
        if o < INTRO:
            im = Image.blend(Image.new('RGB', (OW, OH), BG), im, ease((o + 1) / INTRO))
        out = im if out is None else Image.blend(out, im, wgt)
    ff.stdin.write(out.tobytes())
    if o % 60 == 0:
        print(F, o, '/', total)
ff.stdin.close(); ff.wait()

# son : la musique du site + effets synthétisés
SR = 48000
dur = total / FPS
fx = np.zeros(int(SR * dur) + SR, dtype=np.float32)
rng = np.random.default_rng(7)
for kind, at in events:
    i0 = int(at * SR)
    if kind == 'whoosh':
        L = int(.55 * SR); tt = np.arange(L) / SR
        noise = rng.standard_normal(L).astype(np.float32)
        # bruit filtré dont la fréquence monte puis redescend (filtre passe-bas variable, 1 pôle)
        fc = 400 + 3200 * np.sin(np.pi * tt / tt[-1]) ** 2
        a = np.exp(-2 * np.pi * fc / SR); y = np.zeros(L, np.float32); prev = 0.0
        for j in range(L):
            prev = (1 - a[j]) * noise[j] + a[j] * prev; y[j] = prev
        env = np.sin(np.pi * tt / tt[-1]) ** 1.5
        seg = .55 * y * env / (np.abs(y).max() + 1e-6)
        s0 = max(0, i0 - L // 2)
        fx[s0:s0 + L] += seg[:len(fx) - s0]
    else:
        L = int(.06 * SR); tt = np.arange(L) / SR
        seg = .35 * np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 90) + .25 * rng.standard_normal(L) * np.exp(-tt * 260)
        fx[i0:i0 + L] += seg.astype(np.float32)
fx = np.clip(fx[:int(SR * dur)], -1, 1)
fxw = DEST + '.fx.wav'
with wave.open(fxw, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((fx * 32767).astype('<i2').tobytes())
fade = max(0, dur - 1.2)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp_v, '-stream_loop', '-1', '-i', MUSIC, '-i', fxw,
                '-filter_complex',
                f'[1:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,volume=1.6,afade=t=in:d=0.3,afade=t=out:st={fade:.3f}:d=1.2[m];'
                f'[2:a]aresample=48000,volume=0.9[f];[m][f]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]',
                '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DEST],
               check=True)
os.remove(tmp_v); os.remove(fxw)
print('écrit', DEST)
