#!/usr/bin/env python3
"""GameCenter — musique originale du broadcast (Audio System V0.4), composée par ce script.

Libre de droits par construction : tout est synthétisé ici (aucun échantillon, aucun morceau existant) et placé
dans le domaine public (CC0). Huit pièces, ré mineur, 120 BPM, style habillage sportif TV, mixées pour passer
SOUS le commentaire et la foule :
  boucles : pregame · gameplay · close_game · red_zone · final_drive · overtime   (8 mesures = 16 s, bouclables)
  jingles : victory · defeat                                                       (une fois)
Une boucle est rendue sur trois périodes puis découpée au milieu (pré-roll 0,5 s + 16 s + 1 s de queue) : le
lecteur boucle sur [0,5 s ; 16,5 s], parfaitement périodique, même avec le décalage d'un décodeur MP3.

    pip install numpy ; python3 outils/audio/composer_musique.py [--audio-dir audio]
Écrit audio/music/<id>.<empreinte>.mp3 et les entrées « music » de audio/manifest.json.
Pour remplacer une pièce par un autre morceau libre de droits : même id, mêmes champs dans le manifeste.
"""
import argparse, hashlib, json, os, subprocess, tempfile, wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
LOOP_BARS = 8
L = LOOP_BARS * BAR            # 16 s
PRE, TAIL = 0.5, 1.0
VERSION = "m3"                 # m3 : plus de médiums (audible sur haut-parleur de tablette / téléphone)                 # changer si la composition change
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


N = {"D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "Bb": 70, "C": 72}
CHORDS = {  # notes MIDI (octave du milieu)
    "Dm": [62, 65, 69], "Bb": [58, 62, 65], "F": [60, 65, 69], "C": [60, 64, 67], "A": [61, 64, 69],
    "Gm": [62, 67, 70], "D": [62, 66, 69], "G": [62, 67, 71], "Am": [60, 64, 69],
}


class Track:
    def __init__(self, dur):
        self.n = int(dur * SR)
        self.buf = np.zeros((2, self.n))

    def add(self, t0, sig, gain=1.0, pan=0.0):
        """sig : mono (n,) ou stéréo (2, n) ; pan −1..1"""
        i = int(t0 * SR)
        if i >= self.n:
            return
        if sig.ndim == 1:
            l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            sig = np.vstack([sig * l, sig * r]) * 1.4142
        m = min(sig.shape[1], self.n - i)
        self.buf[:, i:i + m] += sig[:, :m] * gain


def env_adsr(n, a, d, s, r, hold=None):
    t = np.arange(n) / SR
    hold = hold if hold is not None else n / SR - r
    e = np.where(t < a, t / max(a, 1e-4), 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where((t >= a + d) & (t < hold), s, e)
    e = np.where(t >= hold, s * np.clip(1 - (t - hold) / max(r, 1e-4), 0, 1), e)
    return e


def additive(freq, dur, nh, tilt=1.0, odd=False, detune=0.0, bright=None):
    """onde riche par addition d'harmoniques (filtre « naturel » : moins d'harmoniques = plus sombre)"""
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    f = freq * 2 ** (detune / 1200)
    for k in range(1, nh + 1):
        if odd and k % 2 == 0:
            continue
        if f * k > SR / 2.2:
            break
        amp = 1.0 / k ** tilt
        if bright is not None:          # brillance qui varie dans le temps (enveloppe de filtre)
            amp = amp * np.exp(-k * (1.0 - bright) * 0.45)
        out += amp * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 2 * np.pi))
    return out


# ------------------------------------------------------------------ instruments
def pad(tr, t0, chord, dur, gain=0.05, nh=8, octave=0):
    nh = max(nh, 10)
    for i, m in enumerate(CHORDS[chord]):
        f = hz(m + 12 * octave)
        for side, det in ((-0.6, -7), (0.6, 7)):
            s = additive(f, dur + 0.8, nh, tilt=1.15, detune=det)
            s *= env_adsr(len(s), 0.45, 0.3, 0.85, 0.8, hold=dur)
            tr.add(t0, s, gain, pan=side * (0.5 + 0.2 * i))


def bass(tr, t0, m, dur, gain=0.16, nh=7):
    nh = max(nh, 14)          # harmoniques 150-1000 Hz : la basse s'entend aussi sur un petit haut-parleur
    s = additive(hz(m - 24), dur + 0.05, nh, tilt=0.85)
    s *= env_adsr(len(s), 0.005, 0.12, 0.6, 0.05, hold=dur)
    tr.add(t0, s, gain)


def pluck(tr, t0, m, gain=0.05, pan=0.0):
    s = additive(hz(m + 12), 0.35, 9, odd=True, tilt=1.3)
    s *= np.exp(-np.arange(len(s)) / SR / 0.09)
    tr.add(t0, s, gain, pan)


def stab(tr, t0, chord, gain=0.07, dur=0.45, octave=0):
    for i, m in enumerate(CHORDS[chord]):
        n = int((dur + 0.3) * SR); t = np.arange(n) / SR
        bright = np.clip(np.minimum(t / 0.04, 1) * np.exp(-t / 0.35), 0, 1)
        s = additive(hz(m + 12 * octave), dur + 0.3, 14, tilt=1.0, bright=bright, detune=rng.uniform(-5, 5))
        s *= env_adsr(n, 0.02, 0.15, 0.7, 0.25, hold=dur)
        tr.add(t0, s, gain, pan=(i - 1) * 0.35)


def kick(tr, t0, gain=0.5):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t / 0.045)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    s[:200] += rng.normal(0, 0.3, 200) * np.linspace(1, 0, 200)
    tr.add(t0, s, gain)


def snare(tr, t0, gain=0.22):
    n = int(0.3 * SR); t = np.arange(n) / SR
    nz = np.diff(rng.normal(0, 1, n + 1)) * 0.5
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    tr.add(t0, (nz * np.exp(-t / 0.09) + body * 0.6), gain)


def hat(tr, t0, gain=0.05, open_=False, pan=0.25):
    n = int((0.25 if open_ else 0.06) * SR); t = np.arange(n) / SR
    nz = np.diff(np.diff(rng.normal(0, 1, n + 2)))
    tr.add(t0, nz * np.exp(-t / (0.08 if open_ else 0.018)) * 0.35, gain, pan)


def tom(tr, t0, m=45, gain=0.32):
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = hz(m) * (1 + 0.6 * np.exp(-t / 0.06))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25)
    tr.add(t0, s, gain)


def crash(tr, t0, gain=0.05, dur=2.5):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.diff(rng.normal(0, 1, (2, n + 1)), axis=1)
    tr.add(t0, nz * np.exp(-t / (dur / 3)), gain)


def riser(tr, t0, dur, gain=0.03):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.diff(rng.normal(0, 1, n + 1))
    tr.add(t0, nz * (t / dur) ** 2, gain)


# ------------------------------------------------------------------ pièces (une période de 16 s, rendue 3 fois)
PROG = ["Dm", "Dm", "Bb", "Bb", "F", "F", "C", "C"]
ROOT_OF = {"Dm": 62, "Bb": 58, "F": 65, "C": 60, "A": 57, "Gm": 55, "D": 62, "G": 55, "Am": 57}


def period(name, tr, t0):
    global rng
    rng = np.random.default_rng(sum(map(ord, name)))   # même graine à chaque période : boucle sans couture
    if name == "pregame":
        for b, ch in enumerate(PROG):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.045, nh=9)
            for k in range(8):
                pluck(tr, tb + k * BEAT / 2, CHORDS[ch][k % 3] + (12 if k % 4 == 3 else 0), 0.035, pan=0.4 if k % 2 else -0.4)
                hat(tr, tb + k * BEAT / 2, 0.03)
            kick(tr, tb, 0.35); kick(tr, tb + 2 * BEAT, 0.3)
            bass(tr, tb, ROOT_OF[ch], BAR * 0.9, 0.12)
        crash(tr, t0, 0.035)
    elif name == "gameplay":
        for b, ch in enumerate(PROG):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.035, nh=5)
            for k in range(8):
                bass(tr, tb + k * BEAT / 2, ROOT_OF[ch], BEAT * 0.4, 0.07, nh=5)
            for k in range(4):
                hat(tr, tb + k * BEAT, 0.022)
                pluck(tr, tb + k * BEAT, CHORDS[ch][k % 3] + (12 if k == 3 else 0), 0.04, pan=-0.3 if k % 2 else 0.3)
            kick(tr, tb, 0.22)
    elif name == "close_game":
        prog = ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A"]
        for b, ch in enumerate(prog):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.04, nh=6, octave=-1)
            r = ROOT_OF[ch]
            for k in range(16):
                bass(tr, tb + k * BEAT / 4, r + (7 if k % 4 == 2 else 0), BEAT * 0.2, 0.06, nh=6)
            tom(tr, tb + 3 * BEAT, 43, 0.22); tom(tr, tb + 3.5 * BEAT, 40, 0.18)
            kick(tr, tb, 0.3)
    elif name == "red_zone":
        for b, ch in enumerate(PROG):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.035, nh=7)
            for k in range(4):
                kick(tr, tb + k * BEAT, 0.38)
                hat(tr, tb + k * BEAT + BEAT / 2, 0.035, open_=True)
            snare(tr, tb + BEAT, 0.18); snare(tr, tb + 3 * BEAT, 0.18)
            for k in range(8):
                bass(tr, tb + k * BEAT / 2, ROOT_OF[ch] + (12 if k % 2 else 0), BEAT * 0.35, 0.1)
            stab(tr, tb, ch, 0.05)
    elif name == "final_drive":
        for b, ch in enumerate(PROG):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.04, nh=9)
            for k in range(4):
                kick(tr, tb + k * BEAT, 0.4)
            snare(tr, tb + BEAT, 0.2); snare(tr, tb + 3 * BEAT, 0.2)
            for k in range(16):
                hat(tr, tb + k * BEAT / 4, 0.025 + 0.012 * (k % 2 == 0), pan=0.3 if k % 2 else -0.1)
            for k in range(8):
                bass(tr, tb + k * BEAT / 2, ROOT_OF[ch] + (12 if k % 2 else 0), BEAT * 0.35, 0.11)
            stab(tr, tb, ch, 0.055); stab(tr, tb + 2.5 * BEAT, ch, 0.04)
        riser(tr, t0 + 6 * BAR, 2 * BAR, 0.02)
        for k in range(8):
            tom(tr, t0 + 7 * BAR + 2 * BEAT + k * BEAT / 4, 48 - k, 0.18)
    elif name == "overtime":
        prog = ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A"]
        for b, ch in enumerate(prog):
            tb = t0 + b * BAR
            if b % 2 == 0:
                pad(tr, tb, ch, 2 * BAR, 0.045, nh=8, octave=-1)
                stab(tr, tb, ch, 0.07, dur=0.8)
            tom(tr, tb, 40, 0.36); tom(tr, tb + 1.5 * BEAT, 43, 0.3); tom(tr, tb + 2 * BEAT, 40, 0.34)
            kick(tr, tb, 0.35)
            for k in range(4):
                bass(tr, tb + k * BEAT, ROOT_OF[ch], BEAT * 0.8, 0.12)
            if b % 4 == 0:
                crash(tr, tb, 0.04)


def room(buf):
    """salle légère (échos 45 / 70 ms) — appliquée AVANT découpe, pour que la boucle reste périodique"""
    out = buf.copy()
    for ch, d, g in ((0, 0.045, 0.18), (1, 0.070, 0.16), (0, 0.110, 0.08), (1, 0.135, 0.07)):
        k = int(d * SR); out[ch, k:] += buf[1 - ch, :-k] * g
    return out


def render_loop(name):
    tr = Track(3 * L + 2)
    for p in range(3):
        period(name, tr, p * L)
    a, b = int((L - PRE) * SR), int((2 * L + TAIL) * SR)
    return room(tr.buf)[:, a:b]


def render_victory():
    tr = Track(9)
    seq = [("D", 0, 1.0), ("G", 1.0, 0.5), ("A", 1.5, 0.5), ("D", 2.0, 3.0)]
    for ch, t, d in seq:
        stab(tr, t, ch, 0.09, dur=d, octave=0); stab(tr, t, ch, 0.05, dur=d, octave=-1)
        pad(tr, t, ch, d, 0.04, nh=10)
        bass(tr, t, ROOT_OF[ch], d * 0.95, 0.15)
    for k in range(12):
        tom(tr, 1.5 + k * 0.042, 45, 0.12 + 0.015 * k)
    kick(tr, 0, 0.5); kick(tr, 2.0, 0.55); crash(tr, 2.0, 0.07, dur=4)
    fade = np.ones(tr.n); fl = int(2.5 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    return room(tr.buf * fade)


def render_defeat():
    tr = Track(8)
    for ch, t, d in [("Dm", 0, 2.4), ("Bb", 2.0, 2.4), ("Gm", 4.0, 3.5)]:
        pad(tr, t, ch, d, 0.05, nh=5, octave=-1)
        bass(tr, t, ROOT_OF[ch], d * 0.9, 0.08, nh=4)
    for i, m in enumerate([69, 67, 65, 62]):
        pluck(tr, 0.5 + i * 1.2, m, 0.03)
    fade = np.ones(tr.n); fl = int(3 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    return room(tr.buf * fade)


# ------------------------------------------------------------------ sortie
PIECES = {  # id: (kind, état, gain relatif dans le mix musical)
    "pregame": ("loop", "pregame", 0.9), "gameplay": ("loop", "gameplay", 0.7), "close_game": ("loop", "close_game", 0.75),
    "red_zone": ("loop", "red_zone", 0.8), "final_drive": ("loop", "final_drive", 0.85), "overtime": ("loop", "overtime", 0.85),
    "victory": ("stinger", "victory", 1.0), "defeat": ("stinger", "defeat", 0.9),
}


def _wav(buf, path):
    pcm = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.T.copy().tobytes())


def loudness(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    vals = [l for l in out.splitlines() if l.strip().startswith("I:")]
    return float(vals[-1].split()[1])


def write_mp3(buf, dst, target):
    """niveau par un gain FIXE (mesure EBU R128 puis gain) : un normaliseur dynamique casserait la boucle.
    Sous le commentaire : −20 LUFS les boucles, −18 les jingles ; crête ≤ −1 dBFS."""
    buf = buf / (np.max(np.abs(buf)) or 1.0) * 0.5
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        tmp = fh.name
    try:
        _wav(buf, tmp)
        g = 10 ** ((target - loudness(tmp)) / 20)
        g = min(g, 0.89 / np.max(np.abs(buf)))
        _wav(buf * g, tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ar", "44100", "-b:a", "112k", dst], check=True)
    finally:
        os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--audio-dir", default=os.path.join(ROOT, "audio")); a = ap.parse_args()
    out_dir = os.path.join(a.audio_dir, "music"); os.makedirs(out_dir, exist_ok=True)
    entries = []
    for pid, (kind, state, gain) in PIECES.items():
        h = hashlib.sha1(f"{pid}|{VERSION}|{SR}|{BPM}".encode()).hexdigest()[:8]
        fn = f"{pid}.{h}.mp3"; dst = os.path.join(out_dir, fn)
        if not os.path.exists(dst):
            buf = render_loop(pid) if kind == "loop" else (render_victory() if pid == "victory" else render_defeat())
            write_mp3(buf, dst, -20 if kind == "loop" else -18)
            print("composé", fn)
        e = {"id": "m:" + pid, "cat": "music", "kind": kind, "state": state, "gain": gain, "file": "music/" + fn,
             "text": f"Musique originale GameCenter « {pid} » (synthèse, CC0)", "bytes": os.path.getsize(dst), "license": "CC0 — composée par outils/audio/composer_musique.py"}
        if kind == "loop":
            e.update(loopStart=PRE, loopEnd=PRE + L)
        entries.append(e)
    for fn in os.listdir(out_dir):                     # anciennes versions
        if fn.endswith(".mp3") and fn not in {x["file"].split("/")[1] for x in entries}:
            os.unlink(os.path.join(out_dir, fn)); print("supprimé", fn)
    mp = os.path.join(a.audio_dir, "manifest.json")
    m = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"schema": "gc-audio-manifest/1", "assets": []}
    assets = [x for x in m.get("assets", []) if x.get("cat") != "music"] + entries
    m["assets"] = assets
    m["version"] = hashlib.sha1(json.dumps(assets, sort_keys=True).encode()).hexdigest()[:10]
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1); fh.write("\n")
    print(f"Musique : {len(entries)} pièces · {sum(x['bytes'] for x in entries)//1024} Ko")


if __name__ == "__main__":
    main()
