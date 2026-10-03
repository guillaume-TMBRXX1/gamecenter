#!/usr/bin/env python3
"""GameCenter — génération HORS LIGNE du commentaire enregistré (Audio System V0.2).

Lit outils/audio/catalogue/commentary.json (les phrases) et outils/audio/catalogue/voix.json (la voix
ElevenLabs et ses réglages), génère seulement ce qui manque ou a changé, normalise avec ffmpeg
(mono 24 kHz, 48 kb/s, −16 LUFS, silences coupés), écrit audio/commentary/<id>.<empreinte>.mp3 et
met à jour audio/manifest.json. Le site ne parle JAMAIS à ElevenLabs : il lit ces fichiers.

Le plus simple : le workflow GitHub « Commentaire audio » (.github/workflows/audio.yml) lance ce script sur les
machines de GitHub — rien à installer. Clé API : secret GitHub ELEVENLABS_API_KEY (ou, en local, variable
d'environnement / fichier .env ignoré par Git). Voix : variable ELEVENLABS_VOICE_ID (ou voice_id dans voix.json).
Jamais dans le code, jamais sur Railway, jamais dans le navigateur.

    python3 outils/audio/generer_audio.py --dry-run        ce qui serait généré, nombre de caractères
    python3 outils/audio/generer_audio.py                  génère ce qui manque, met à jour le manifeste
    python3 outils/audio/generer_audio.py --only TOUCHDOWN filtre (cue ou id, sous-chaîne)
    python3 outils/audio/generer_audio.py --reject id1,id2 refaire ces prises (nouvelle graine) au prochain passage
    python3 outils/audio/generer_audio.py --prune          supprime les fichiers qui ne sont plus au catalogue
    python3 outils/audio/generer_audio.py --manifest-only  reconstruit le manifeste à partir des fichiers présents
    python3 outils/audio/generer_audio.py --placeholder --audio-dir /tmp/x   bips de test (sans ElevenLabs)
    python3 outils/audio/generer_audio.py --cat stade      seulement la foule et les effets (catalogue/stade.json, V0.3)
Ensuite : ouvrir outils/audio/ecoute.html pour écouter, rejeter ce qui ne va pas (--reject), commiter audio/.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))           # gamecenter_serveur (1)
CAT = os.path.join(HERE, "catalogue")
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format={fmt}"
API_SFX = "https://api.elevenlabs.io/v1/sound-generation?output_format={fmt}"      # foule et effets (V0.3)
SFX_POST_VERSION = "sv1"
POST_VERSION = "pv1"                                               # changer si le traitement ffmpeg change


def load_json(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(p, o):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(o, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, p)


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if k:
        return k
    for p in (os.path.join(HERE, ".env"), os.path.join(ROOT, ".env"), os.path.join(ROOT, "..", ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                if line.strip().startswith("ELEVENLABS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def settings_for(voix, tier):
    s = dict(voix.get("voice_settings", {}))
    s.update(voix.get("tiers", {}).get(tier, {}).get("voice_settings", {}))
    return s


def take_of(line, voix, rejets):
    """Everything that defines a take; its hash names the file, so any change makes a new file."""
    tier = voix.get("tiers", {}).get(line["tier"], {})
    text = (tier.get("prefix", "") + line["text"]) if voix.get("model_id", "").startswith("eleven_v3") else line["text"]
    t = {"text": text, "voice_id": voix["voice_id"], "model_id": voix["model_id"], "settings": settings_for(voix, line["tier"]),
         "seed": int(voix.get("seed", 1)) + int(rejets.get(line["id"], 0)), "fmt": voix.get("output_format", "mp3_44100_128"), "post": POST_VERSION}
    h = hashlib.sha1(json.dumps(t, sort_keys=True).encode()).hexdigest()[:8]
    return t, h


def tts(key, take):
    body = json.dumps({"text": take["text"], "model_id": take["model_id"], "voice_settings": take["settings"], "seed": take["seed"]}).encode()
    req = urllib.request.Request(API.format(voice=take["voice_id"], fmt=take["fmt"]), data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** (attempt + 1)); continue
            raise SystemExit(f"ElevenLabs a répondu {e.code} : {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1)); continue
            raise SystemExit(f"Réseau : {e}")


def ffmpeg_ok():
    return shutil.which("ffmpeg") is not None


def post_process(src_bytes, dst):
    """mono 24 kHz, 48 kb/s, silences de début / fin coupés, volume −16 LUFS (voix broadcast)"""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(src_bytes); src = fh.name
    try:
        af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
              "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
              "loudnorm=I=-16:TP=-1.5:LRA=7")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ac", "1", "-ar", "24000", "-b:a", "48k", dst], check=True)
    finally:
        os.unlink(src)


def duration(p):
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True, check=True).stdout
        return round(float(out.strip()), 2)
    except Exception:
        return None


def placeholder(line, dst):
    """bip de test (sans ElevenLabs) : durée ~ longueur du texte, hauteur selon le ton"""
    f = {"calm": 440, "excited": 660, "huge": 880}.get(line["tier"], 440)
    d = max(0.6, min(3.0, len(line["text"]) / 16))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={f}:duration={d}", "-af", "volume=0.25",
                    "-ac", "1", "-ar", "24000", "-b:a", "48k", dst], check=True)


def build_manifest(audio_dir, lines, hashes):
    mf_path = os.path.join(audio_dir, "manifest.json")
    mf = load_json(mf_path, {}) or {}
    keep = [a for a in mf.get("assets", []) if a.get("cat") != "commentary"]
    com = []
    for l in lines:
        fn = f"{l['id']}.{hashes[l['id']]}.mp3"; p = os.path.join(audio_dir, "commentary", fn)
        if os.path.exists(p):
            com.append({"id": "c:" + l["id"], "cat": "commentary", "cue": l["cue"], "tier": l["tier"], "tags": l["tags"],
                        "file": "commentary/" + fn, "text": l["text"], "dur": duration(p), "bytes": os.path.getsize(p)})
    assets = keep + com
    ver = hashlib.sha1(json.dumps(assets, sort_keys=True).encode()).hexdigest()[:10] if assets else 0
    doc = {"schema": "gc-audio-manifest/1", "version": ver,
           "note": "Généré par outils/audio/generer_audio.py — ne pas éditer à la main. Fichiers pré-générés hors ligne (ElevenLabs).",
           "assets": assets}
    save_json(mf_path, doc)
    return com


def write_listen_page(audio_dir, com):
    rel = os.path.relpath(audio_dir, HERE).replace(os.sep, "/")
    rows = "\n".join(f'<tr><td>{a["cue"]}</td><td>{a["tier"]}</td><td>{" ".join(a["tags"])}</td><td>{a["id"][2:]}</td><td>{a["text"]}</td>'
                     f'<td><audio controls preload="none" src="{rel}/{a["file"]}"></audio></td></tr>' for a in com)
    html = ("<!doctype html><meta charset=utf-8><title>GameCenter — écoute du commentaire</title>"
            "<style>body{font:14px system-ui;margin:24px}td{padding:4px 8px;border-bottom:1px solid #ddd}audio{height:28px}</style>"
            f"<h1>Commentaire enregistré · {len(com)} prises</h1><p>Une prise à refaire : <code>python3 outils/audio/generer_audio.py --reject &lt;id&gt;</code> puis relancer.</p>"
            f"<table><tr><th>cue</th><th>ton</th><th>tags</th><th>id</th><th>texte</th><th></th></tr>{rows}</table>")
    with open(os.path.join(HERE, "ecoute.html"), "w", encoding="utf-8") as fh:
        fh.write(html)


# ------------------------------------------------------------------ foule et effets (V0.3)
def take_of_sfx(a, rejets, fmt):
    t = {"prompt": a["prompt"], "duration": a["duration"], "loop": bool(a.get("loop")), "influence": a.get("influence", 0.45),
         "fmt": fmt, "take": int(rejets.get(a["id"], 0)), "post": SFX_POST_VERSION}
    return t, hashlib.sha1(json.dumps(t, sort_keys=True).encode()).hexdigest()[:8]


def sound_generation(key, take):
    body = {"text": take["prompt"], "duration_seconds": take["duration"], "prompt_influence": take["influence"]}
    if take["loop"]:
        body["loop"] = True
    for attempt in range(4):
        req = urllib.request.Request(API_SFX.format(fmt=take["fmt"]), data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code in (400, 422) and "loop" in body:          # option boucle refusée : la boucle se fait dans le navigateur
                body.pop("loop"); continue
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** (attempt + 1)); continue
            raise SystemExit(f"ElevenLabs (sound-generation) a répondu {e.code} : {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1)); continue
            raise SystemExit(f"Réseau : {e}")


def post_process_sfx(src_bytes, a, dst):
    """mono 32 kHz 64 kb/s ; niveaux : fonds −27 LUFS, réactions −21, effets −20 ; fondus contre les clics
    (pas de fondu sur les fonds en boucle : le navigateur les enchaîne en fondu)"""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(src_bytes); src = fh.name
    try:
        bed = a["kind"].startswith("bed_"); sfx = a["cat"] == "sfx"; d = float(a["duration"])
        target = -27 if bed else (-20 if sfx else -21)
        chain = []
        if sfx:
            chain.append("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.01")
        chain.append(f"loudnorm=I={target}:TP=-2:LRA=11")
        if not bed:
            fo = 0.02 if sfx else 0.15
            chain += [f"afade=t=in:d={0.005 if sfx else 0.08}", f"areverse,afade=t=in:d={fo},areverse"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", ",".join(chain), "-ac", "1", "-ar", "32000", "-b:a", "64k", dst], check=True)
    finally:
        os.unlink(src)


def placeholder_sfx(a, dst):
    d = max(0.3, float(a["duration"]))
    src = (f"anoisesrc=color=pink:duration={d}:amplitude=0.3" if a["cat"] == "crowd" else f"sine=frequency=180:duration={min(d, 0.4)}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-ac", "1", "-ar", "32000", "-b:a", "64k", dst], check=True)


def build_manifest_sfx(audio_dir, assets, hashes):
    mf_path = os.path.join(audio_dir, "manifest.json")
    mf = load_json(mf_path, {}) or {}
    keep = [x for x in mf.get("assets", []) if x.get("cat") not in ("crowd", "sfx")]
    out = []
    for a in assets:
        fn = f"{a['id']}.{hashes[a['id']]}.mp3"; p = os.path.join(audio_dir, a["cat"], fn)
        if os.path.exists(p):
            out.append({"id": ("w:" if a["cat"] == "crowd" else "s:") + a["id"], "cat": a["cat"], "kind": a["kind"], "loop": bool(a.get("loop")),
                        "gain": a.get("gain", 1.0), "file": f"{a['cat']}/{fn}", "text": a["prompt"], "dur": duration(p), "bytes": os.path.getsize(p)})
    allx = keep + out
    ver = hashlib.sha1(json.dumps(allx, sort_keys=True).encode()).hexdigest()[:10] if allx else 0
    save_json(mf_path, {"schema": "gc-audio-manifest/1", "version": ver,
                        "note": "Généré par outils/audio/generer_audio.py — ne pas éditer à la main. Fichiers pré-générés hors ligne (ElevenLabs).",
                        "assets": allx})
    return out


def run_stade(a, rejets, key):
    cat = load_json(os.path.join(CAT, "stade.json"))
    assets, fmt = cat["assets"], "mp3_44100_128"
    hashes, todo = {}, []
    for x in assets:
        take, h = take_of_sfx(x, rejets, fmt); hashes[x["id"]] = h
        os.makedirs(os.path.join(a.audio_dir, x["cat"]), exist_ok=True)
        if a.only and a.only.lower() not in (x["kind"] + " " + x["id"]).lower():
            continue
        if not os.path.exists(os.path.join(a.audio_dir, x["cat"], f"{x['id']}.{h}.mp3")):
            todo.append((x, take, h))
    if a.dry_run:
        print(f"Stade : {len(todo)} son(s) à générer · {round(sum(x['duration'] for x, _, _ in todo), 1)} s d'audio")
        for x, _, _ in todo[:50]:
            print(f"  {x['id']:<22} {x['duration']:>4} s  {x['prompt'][:70]}")
        return
    if todo and not a.manifest_only:
        if not a.placeholder and not key:
            raise SystemExit("ELEVENLABS_API_KEY absente.")
        for n, (x, take, h) in enumerate(todo, 1):
            dst = os.path.join(a.audio_dir, x["cat"], f"{x['id']}.{h}.mp3")
            if a.placeholder:
                placeholder_sfx(x, dst)
            else:
                raw = sound_generation(key, take)
                if ffmpeg_ok():
                    post_process_sfx(raw, x, dst)
                else:
                    with open(dst, "wb") as fh:
                        fh.write(raw)
                time.sleep(0.3)
            print(f"[stade {n}/{len(todo)}] {x['id']}")
    if a.prune:
        for c in ("crowd", "sfx"):
            wanted = {f"{x['id']}.{hashes[x['id']]}.mp3" for x in assets if x["cat"] == c}
            d = os.path.join(a.audio_dir, c)
            for fn in os.listdir(d):
                if fn.endswith(".mp3") and fn not in wanted:
                    os.unlink(os.path.join(d, fn)); print("supprimé", c + "/" + fn)
    out = build_manifest_sfx(a.audio_dir, assets, hashes)
    print(f"Stade : {len(out)}/{len(assets)} sons · {sum(x['bytes'] for x in out)//1024} Ko.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--only", default="")
    ap.add_argument("--reject", default=""); ap.add_argument("--prune", action="store_true")
    ap.add_argument("--manifest-only", action="store_true"); ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--audio-dir", default=os.path.join(ROOT, "audio"))
    ap.add_argument("--cat", default="all", choices=["all", "commentary", "stade"])
    a = ap.parse_args()

    cat = load_json(os.path.join(CAT, "commentary.json"))
    voix = load_json(os.path.join(CAT, "voix.json"))
    rej_path = os.path.join(CAT, "rejets.json"); rejets = load_json(rej_path, {}) or {}
    lines = cat["lines"]
    if a.reject:
        ids = {l["id"] for l in lines} | {x["id"] for x in (load_json(os.path.join(CAT, "stade.json"), {}) or {}).get("assets", [])}
        for i in a.reject.split(","):
            i = i.strip()
            if i not in ids:
                raise SystemExit(f"id inconnu : {i}")
            rejets[i] = int(rejets.get(i, 0)) + 1
        save_json(rej_path, rejets); print(f"{len(a.reject.split(','))} prise(s) à refaire au prochain passage."); return

    if a.cat in ("all", "stade"):
        run_stade(a, rejets, "" if (a.placeholder or a.dry_run) else api_key())
    if a.cat == "stade":
        return
    if os.environ.get("ELEVENLABS_VOICE_ID", "").strip():
        voix = dict(voix, voice_id=os.environ["ELEVENLABS_VOICE_ID"].strip())
    if a.placeholder:
        voix = dict(voix, voice_id="placeholder", model_id="placeholder")
    elif not voix.get("voice_id"):
        raise SystemExit("Voix du commentateur absente : variable ELEVENLABS_VOICE_ID (GitHub → Settings → Secrets and variables → Actions → Variables) ou voice_id dans outils/audio/catalogue/voix.json.")
    out_dir = os.path.join(a.audio_dir, "commentary"); os.makedirs(out_dir, exist_ok=True)
    hashes, todo = {}, []
    for l in lines:
        take, h = take_of(l, voix, rejets); hashes[l["id"]] = h
        if a.only and a.only.lower() not in (l["cue"] + " " + l["id"]).lower():
            continue
        if not os.path.exists(os.path.join(out_dir, f"{l['id']}.{h}.mp3")):
            todo.append((l, take, h))

    if a.dry_run:
        print(f"{len(todo)} prise(s) à générer · {sum(len(t['text']) for _, t, _ in todo)} caractères")
        for l, t, h in todo[:40]:
            print(f"  {l['id']:<34} {t['text']}")
        return
    if todo and not a.manifest_only:
        key = "" if a.placeholder else api_key()
        if not a.placeholder and not key:
            raise SystemExit("ELEVENLABS_API_KEY absente (variable d'environnement ou fichier .env ignoré par Git).")
        if not ffmpeg_ok():
            if a.placeholder:
                raise SystemExit("ffmpeg est nécessaire pour --placeholder.")
            print("ffmpeg absent : fichiers gardés tels que reçus (pas de normalisation).", file=sys.stderr)
        for n, (l, take, h) in enumerate(todo, 1):
            dst = os.path.join(out_dir, f"{l['id']}.{h}.mp3")
            if a.placeholder:
                placeholder(l, dst)
            else:
                raw = tts(key, take)
                if ffmpeg_ok():
                    post_process(raw, dst)
                else:
                    with open(dst, "wb") as fh:
                        fh.write(raw)
                time.sleep(0.2)
            print(f"[{n}/{len(todo)}] {l['id']}")
    if a.prune:
        wanted = {f"{l['id']}.{hashes[l['id']]}.mp3" for l in lines}
        for fn in os.listdir(out_dir):
            if fn.endswith(".mp3") and fn not in wanted:
                os.unlink(os.path.join(out_dir, fn)); print("supprimé", fn)
    com = build_manifest(a.audio_dir, lines, hashes)
    if not a.placeholder:
        write_listen_page(a.audio_dir, com)
    print(f"Manifeste : {len(com)}/{len(lines)} phrases enregistrées · {sum(x['bytes'] for x in com)//1024} Ko.")


if __name__ == "__main__":
    main()
