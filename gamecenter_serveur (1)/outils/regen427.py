"""Cellule 427 du notebook (site embarqué, NGS_TEMPLATE) : reporte les changements de gamecenter_source.html.

Le Game Center du notebook est une copie allégée du site (sans serveur, recherche, paris en ligne, exhibitions…),
retouchée à la main. On ne la régénère pas d'un bloc : on y reporte les changements du site depuis la dernière
synchronisation (commit noté dans la cellule), bloc par bloc. Un bloc est appliqué s'il retrouve son code UNE fois dans
la cellule (n'importe où : les sections n'y sont pas dans le même ordre), au besoin avec moins de contexte. Les autres
sont refusés et listés : code absent de la cellule (partie du site seulement : on l'ignore) ou présent mais modifié
(à reporter à la main, puis relancer). Recréé le 11/10/2026 (bloc 1, étape 4) : l'ancien outil, hors dépôt, est perdu.

    python outils/regen427.py                      essai : blocs appliqués / refusés, rien n'est écrit
    python outils/regen427.py --ecrire             écrit la cellule et note le commit du site comme référence
    python outils/regen427.py --base 20fc0db       référence à utiliser si la cellule n'en note pas encore
    python outils/regen427.py --historique         rejoue les synchronisations passées (contrôle de l'outil)

Depuis « gamecenter_serveur (1) » ; il faut git et l'historique du dépôt.
"""
import argparse
import ast
import difflib
import json
import os
import re
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.dirname(ICI)
NB = os.path.join(SERVEUR, "NFL_Sim_GameCenter.ipynb")
SRC = os.path.join(SERVEUR, "gamecenter_source.html")
MARQUE = "# Synchronisé avec gamecenter_source.html @ "
FUZZ = 3                                    # lignes de contexte qu'on peut retirer de chaque côté d'un bloc


def git(*args):
    return subprocess.run(["git", "-C", SERVEUR, *args], capture_output=True, text=True, check=True).stdout


def rel(p):
    return os.path.relpath(p, git("rev-parse", "--show-toplevel").strip())


# ------------------------------------------------------------------ notebook
def cellule_427(nb):
    for i, c in enumerate(nb["cells"]):
        s = "".join(c["source"])
        if c["cell_type"] == "code" and "NGS_TEMPLATE = r'''" in s and "def render_ngs_gamecenter" in s:
            return i, s
    raise SystemExit("cellule du Game Center (NGS_TEMPLATE) introuvable")


def modele(s):
    n = next(n for n in ast.parse(s).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "NGS_TEMPLATE")
    return n.value.value


def remplacer_modele(s, nouveau, ref):
    if "'''" in nouveau or nouveau.endswith("\\"):
        raise SystemExit("le modèle ne peut pas contenir ''' ni finir par une barre oblique (chaîne r'''…''')")
    a = s.index("NGS_TEMPLATE = r'''") + len("NGS_TEMPLATE = r'''")
    b = s.index("'''", a)
    s = s[:a] + nouveau + s[b:]
    ligne = MARQUE + ref + " (outils/regen427.py)\n"
    if MARQUE in s:
        s = re.sub(re.escape(MARQUE) + r".*\n", lambda m: ligne, s, count=1)
    else:                                   # sous l'en-tête « # ===…\n# NFL SIM … 09.4 …\n# ===… »
        k = s.index("\n", s.index("\n", s.index("\n") + 1) + 1) + 1
        s = s[:k] + ligne + s[k:]
    return s


def lire_nb(rev=None):
    txt = git("show", f"{rev}:{rel(NB)}") if rev else open(NB, encoding="utf-8").read()
    return json.loads(txt)


def ecrire_nb(nb):
    with open(NB, "w", encoding="utf-8") as f:
        f.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ report des blocs
def blocs(avant, apres):
    """Blocs (ancien, nouveau) du diff unifié avant -> après, 3 lignes de contexte."""
    a, b = avant.splitlines(keepends=True), apres.splitlines(keepends=True)
    out = []
    for grp in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(3):
        vieux, neuf = [], []
        for tag, i1, i2, j1, j2 in grp:
            if tag == "equal":
                vieux += [(" ", x) for x in a[i1:i2]]; neuf += [(" ", x) for x in a[i1:i2]]
            else:
                vieux += [("-", x) for x in a[i1:i2]]; neuf += [("+", x) for x in b[j1:j2]]
        out.append((vieux, neuf))
    return out


def _trouver(lignes, motif):
    n = len(motif)
    return [i for i in range(len(lignes) - n + 1) if lignes[i] == motif[0] and lignes[i:i + n] == motif]


def appliquer(modele_txt, avant, apres):
    """Reporte les blocs du site dans le modèle. Renvoie (nouveau modèle, appliqués, refusés)."""
    lignes = modele_txt.splitlines(keepends=True)
    ok, refus = [], []
    for k, (vieux, neuf) in enumerate(blocs(avant, apres), 1):
        fait = False
        for f in range(FUZZ + 1):
            def coupe(x):
                d = 0
                while d < f and d < len(x) and x[d][0] == " ":
                    d += 1
                e = len(x)
                while len(x) - e < f and e > d and x[e - 1][0] == " ":
                    e -= 1
                return x[d:e]
            v, n = coupe(vieux), coupe(neuf)
            v_txt = [x for _, x in v]
            if not v_txt:
                break
            pos = _trouver(lignes, v_txt)
            if len(pos) == 1:
                lignes[pos[0]:pos[0] + len(v_txt)] = [x for _, x in n]
                ok.append((k, f)); fait = True
                break
            if len(pos) > 1:
                continue                     # ambigu : pas avec moins de contexte
        if not fait:
            refus.append((k, vieux, neuf))
    return "".join(lignes), ok, refus


def decrire_refus(modele_txt, refus):
    presentes = {l.strip() for l in modele_txt.splitlines() if l.strip()}
    out = []
    for k, vieux, neuf in refus:
        anc = [x.strip() for t, x in vieux if x.strip()]
        part = sum(1 for x in anc if x in presentes) / max(1, len(anc))
        etat = "à reporter à la main" if part >= 0.5 else "partie du site seulement (ignorée)"
        exemple = next((x.strip() for t, x in neuf if t == "+" and x.strip()), next((x.strip() for t, x in vieux if t == "-"), ""))
        out.append(f"  bloc {k:3d} · {etat:36s} · {exemple[:100]}")
    return out


# ------------------------------------------------------------------ commandes
def reference(s, base):
    m = re.search(re.escape(MARQUE) + r"(\w+)", s)
    if m:
        return m.group(1)
    if base:
        return base
    raise SystemExit("la cellule ne note pas de commit de référence : indiquez --base <commit du site>")


def historique():
    """Rejoue chaque synchronisation passée : modèle n + changements du site entre n et n+1 -> modèle n+1 ?"""
    revs = git("log", "--format=%h", "--", os.path.basename(NB)).split()[::-1]
    syncs, prec = [], None
    for r in revs:
        try:
            m = modele(cellule_427(lire_nb(r))[1])
        except (SystemExit, StopIteration, json.JSONDecodeError, subprocess.CalledProcessError):
            continue
        if m != prec:
            syncs.append((r, m)); prec = m
    for (a, ma), (b, mb) in zip(syncs, syncs[1:]):
        try:
            sa, sb = git("show", f"{a}:{rel(SRC)}"), git("show", f"{b}:{rel(SRC)}")
        except subprocess.CalledProcessError:
            continue
        res, ok, refus = appliquer(ma, sa, sb)
        ecart = sum(1 for l in difflib.unified_diff(res.splitlines(), mb.splitlines(), n=0, lineterm="")
                    if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        print(f"{a} -> {b} : {len(ok)} blocs appliqués, {len(refus)} refusés · écart avec la cellule réelle : {ecart} lignes")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ecrire", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--historique", action="store_true")
    a = ap.parse_args()
    if a.historique:
        return historique()
    nb = lire_nb()
    i, s = cellule_427(nb)
    ref = reference(s, a.base)
    avant = git("show", f"{ref}:{rel(SRC)}")
    apres = open(SRC, encoding="utf-8").read()
    cible = git("log", "-1", "--format=%h", "--", os.path.basename(SRC)).strip()
    if git("status", "--porcelain", "--", os.path.basename(SRC)).strip():
        cible += "+modifié"
    res, ok, refus = appliquer(modele(s), avant, apres)
    print(f"cellule {i} · site {ref} -> {cible} : {len(ok)} blocs appliqués, {len(refus)} refusés")
    for l in decrire_refus(modele(s), refus):
        print(l)
    if a.ecrire:
        lignes = remplacer_modele(s, res, cible).splitlines(keepends=True)
        nb["cells"][i]["source"] = lignes
        ecrire_nb(nb)
        print(f"cellule {i} écrite (référence {cible}). Reporter à la main les blocs « à reporter » puis vérifier.")


if __name__ == "__main__":
    sys.exit(main())
