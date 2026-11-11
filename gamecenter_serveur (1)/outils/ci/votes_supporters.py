#!/usr/bin/env python3
"""Front office FO-3 : récupère les votes des supporters avant le calcul du samedi (workflow semaine.yml).

    python outils/ci/votes_supporters.py --data data          # depuis « gamecenter_serveur (1) »

Variables : GC_SITE_URL (adresse du site, ex. https://snapline.live) et GC_ADMIN_KEY (la même clé que sur Railway),
secrets GitHub du dépôt.

1. La semaine à produire est celle que generer_semaine.py --suivante produira (même règle, week_to_produce) : rien à
   produire, rien à récupérer.
2. GET <site>/api/admin/fans?week=<lundi> (clé dans l'en-tête X-Admin-Key) → data/fans/fans_<lundi>.json, versé au
   dépôt avec la semaine (archive et rejouabilité) ; generer_semaine.py le passe au notebook (GC_FANS).
3. Jamais d'échec du workflow : secrets absents, serveur injoignable, vote pas encore fermé, réponse invalide…
   → annotation d'alerte (::warning::) et calcul normal, les coordinateurs décident (le moteur le note dans
   week.json → fans.file_read). Pas de question pour cette semaine (semaine calculée avant FO-1) : simple information.

Code de sortie : toujours 0 (sauf --strict, pour les tests : 1 si aucun fichier n'est écrit).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, SERVEUR)
import generer_semaine as gs            # noqa: E402

ESSAIS, PAUSE, DELAI = 3, 5.0, 30       # trois essais, 5 s puis 10 s d'attente, 30 s par requête


def annoter(niveau, msg):
    """Annotation GitHub Actions (warning / notice) ; lisible aussi hors de GitHub."""
    print(f"::{niveau}::Votes des supporters : {msg}", flush=True)


def valider(doc, lundi):
    """Le fichier attendu par le moteur (moteur/supporters.py) : None si valable, sinon la raison."""
    if not isinstance(doc, dict):
        return "réponse qui n'est pas un objet JSON"
    if str(doc.get("week")) != str(lundi):
        return f"semaine {doc.get('week')} au lieu de {lundi}"
    if not doc.get("lever") or not isinstance(doc.get("teams"), dict):
        return "levier ou franchises absents"
    return None


def recuperer(site, cle, lundi, essais=ESSAIS, pause=None, delai=DELAI):
    """(statut, document ou message) : « ok », « pas_de_question », « pas_ferme », « refus », « erreur »."""
    pause = PAUSE if pause is None else pause
    url = site.rstrip("/") + "/api/admin/fans?" + urllib.parse.urlencode({"week": str(lundi)})
    req = urllib.request.Request(url, headers={"X-Admin-Key": cle, "User-Agent": "gamecenter-semaine",
                                               "Accept": "application/json"})
    dernier = "?"
    for i in range(essais):
        try:
            with urllib.request.urlopen(req, timeout=delai) as r:
                return "ok", json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8")).get("detail")
            except Exception:                           # noqa: BLE001
                detail = None
            if e.code == 404 and detail == "no_question":
                return "pas_de_question", "aucune question posée pour cette semaine"
            if e.code == 409 and detail == "not_closed":
                return "pas_ferme", "le vote n'est pas encore fermé"
            if e.code in (401, 403, 404):
                return "refus", f"HTTP {e.code} ({detail or 'refusé'}) : clé ou adresse du site à vérifier"
            dernier = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            dernier = type(e).__name__ + (f" ({getattr(e, 'reason', '')})" if getattr(e, "reason", None) else "")
        if i + 1 < essais:
            time.sleep(pause * (i + 1))
    return "erreur", f"serveur injoignable après {essais} essais ({dernier})"


def main(argv=None, now_ms=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=os.environ.get("GC_DATA", os.path.join(SERVEUR, "data")))
    ap.add_argument("--lundi", help="lundi de la semaine à produire (défaut : celle de generer_semaine.py --suivante)")
    ap.add_argument("--strict", action="store_true", help="code de sortie 1 si aucun fichier n'est écrit (tests)")
    a = ap.parse_args(argv)
    weeks_dir = os.path.join(a.data, "weeks")
    lundi = a.lundi
    if not lundi:
        w = gs.week_to_produce(weeks_dir, int(time.time() * 1000) if now_ms is None else now_ms, lead_hours=72)
        if w is None:
            print("Votes des supporters : aucune semaine à produire, rien à récupérer.")
            return 1 if a.strict else 0
        lundi = w[0]
    site, cle = os.environ.get("GC_SITE_URL", "").strip(), os.environ.get("GC_ADMIN_KEY", "").strip()
    if not site or not cle:
        annoter("warning", f"secrets GC_SITE_URL / GC_ADMIN_KEY absents : semaine du {lundi} calculée sans les votes "
                           "(les coordinateurs décident)")
        return 1 if a.strict else 0
    statut, res = recuperer(site, cle, lundi)
    if statut == "pas_de_question":
        annoter("notice", f"{res} (semaine du {lundi}) : les coordinateurs décident")
        return 1 if a.strict else 0
    if statut != "ok":
        annoter("warning", f"{res} — semaine du {lundi} calculée sans les votes (les coordinateurs décident)")
        return 1 if a.strict else 0
    pb = valider(res, lundi)
    if pb:
        annoter("warning", f"fichier refusé ({pb}) — semaine du {lundi} calculée sans les votes")
        return 1 if a.strict else 0
    dossier = os.path.join(a.data, "fans")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, f"fans_{lundi}.json")
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    n = len(res["teams"])
    votes = sum(int(t.get("votes") or 0) for t in res["teams"].values() if isinstance(t, dict))
    print(f"Votes des supporters : {chemin} — levier {res['lever']}, {n} franchise(s), {votes} vote(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
