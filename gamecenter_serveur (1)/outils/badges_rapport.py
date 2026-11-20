"""Badges (BD-1) : combien de comptes auraient chaque badge, sur une COPIE de la base (l'original n'est pas ouvert en
écriture), pour régler les seuils avant d'afficher quoi que ce soit (programme/Badges_plan.md).

    python outils/badges_rapport.py --base <chemin de gamecenter.db> [--weeks data/weeks] [--at 2026-11-23T12:00]

La base de production se récupère sur Railway (volume du service, data/gamecenter.db) ; ne jamais lancer ce rapport en
pointant GC_DATA sur data/ du dépôt. Les semaines sont lues dans --weeks (défaut : data/weeks du dépôt), en lecture seule.
Rapport : comptes, invités, puis pour chaque badge le nombre de comptes à chaque palier et la médiane de la progression.
Depuis « gamecenter_serveur (1) ».
"""
import argparse
import os
import shutil
import statistics
import sys
import tempfile
from datetime import datetime

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="gamecenter.db à analyser (copié, jamais modifié)")
    ap.add_argument("--weeks", default=os.path.join(RACINE, "data", "weeks"))
    ap.add_argument("--at", help="instant du calcul (ISO, heure de Bruxelles) ; défaut : maintenant")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="gc-badges-")
    try:
        shutil.copy2(a.base, os.path.join(tmp, "gamecenter.db"))
        os.mkdir(os.path.join(tmp, "weeks"))
        for w in sorted(os.listdir(a.weeks)):
            if w.startswith("week_"):
                os.symlink(os.path.abspath(os.path.join(a.weeks, w)), os.path.join(tmp, "weeks", w))
        os.environ["GC_DATA"] = tmp
        os.environ.setdefault("GC_PUSH_LOOP", "0")
        sys.path.insert(0, RACINE)
        import serveur                                       # noqa: E402  (après GC_DATA : la copie)
        from moteur import badges as B                       # noqa: E402
        serveur.load_weeks()
        if a.at:
            t = int(datetime.fromisoformat(a.at).replace(tzinfo=B.TZ).timestamp() * 1000)
        else:
            t = serveur.now_ms()
        with serveur.db() as c:
            joueurs = [dict(r) for r in c.execute("SELECT * FROM players")]
        comptes = [p for p in joueurs if p.get("login")]
        print(f"{len(joueurs)} joueurs, {len(comptes)} comptes, {len(joueurs) - len(comptes)} invités · "
              f"instant {datetime.fromtimestamp(t / 1000, B.TZ):%Y-%m-%d %H:%M}")
        par = {c[0]: {"tiers": [0] * len(c[3]), "values": []} for c in B.CATALOGUE}
        for p in comptes:
            for b in B.evaluer(serveur.badges_donnees(p, t)):
                x = par[b["key"]]
                if b["tier"]:
                    x["tiers"][b["tier"] - 1] += 1
                x["values"].append(b["value"])
        print(f"\n{'badge':<22} {'paliers (seuils : comptes)':<46} médiane")
        for cle, nom, cat, seuils, desc, unite in B.CATALOGUE:
            x = par[cle]
            pal = " · ".join(f"{s}: {n}" for s, n in zip(seuils, x["tiers"])) if len(seuils) > 1 else f"{x['tiers'][0]}"
            med = statistics.median(x["values"]) if x["values"] else 0
            print(f"{nom:<22} {pal:<46} {med:g}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
