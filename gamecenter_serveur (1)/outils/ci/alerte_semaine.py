"""Alerte et relance du calcul du samedi (workflow « Semaine suivante », job « suivi »).

Lancé par GitHub Actions après le job « produire », avec le jeton de l'exécution (GITHUB_TOKEN) ; Python seul.

    python outils/ci/alerte_semaine.py analyser     # étape fautive, catégorie, relance permise → $GITHUB_OUTPUT
    python outils/ci/alerte_semaine.py signaler     # ouvre (ou commente) l'issue « calcul-semaine »
    python outils/ci/alerte_semaine.py relancer     # relance unique du workflow (relance=oui)
    python outils/ci/alerte_semaine.py cloturer     # calcul réussi : commente et ferme l'issue ouverte

Catégories d'échec (étape fautive du job « produire ») :
    push     → la semaine calculée est repoussée par le job « suivi » (artefact), sans recalcul ;
    machine  → panne de la machine GitHub (checkout, installation, machine perdue) : une relance du workflow ;
    tests / calcul / audit → pas de relance (même résultat) : alerte seulement.
Une seule relance : jamais depuis une exécution déjà relancée (relance=oui) ni depuis une 2e tentative.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

ETIQUETTE = "calcul-semaine"
TITRE = "Semaine suivante : échec du calcul du samedi"
WORKFLOW = "semaine.yml"
JOB = "produire"
LIGNES_LOG = 60

# début du nom de l'étape (tel que l'API GitHub le renvoie) → catégorie
ETAPES = [
    ("Set up job", "machine"),
    ("Run actions/", "machine"),
    ("Installer le moteur", "machine"),
    ("Tester les modules du moteur", "tests"),
    ("Calculer la semaine", "calcul"),
    ("Contrôler le moteur", "audit"),
    ("Ajouter la semaine au dépôt", "push"),
    ("Post ", "machine"),
    ("Complete job", "machine"),
]
LIBELLES = {
    "machine": "panne de la machine GitHub",
    "tests": "tests du moteur",
    "calcul": "calcul de la semaine (notebook)",
    "audit": "audit du moteur",
    "push": "ajout de la semaine au dépôt (push)",
}


def categorie_etape(nom):
    for debut, cat in ETAPES:
        if nom.startswith(debut):
            return cat
    return "machine"


def classer(job, relance=False, tentative=1):
    """Étape fautive du job « produire » → {etape, categorie, depassement, relancer}.

    relancer : « push » (le job suivi repousse la semaine calculée), « workflow » (nouvelle exécution) ou « ».
    Un job annulé (dépassement des 75 min ou annulation à la main) n'est jamais relancé."""
    annule = job.get("conclusion") in ("cancelled", "timed_out")
    fautive = None
    for s in job.get("steps") or []:
        if s.get("conclusion") in ("failure", "cancelled", "timed_out") or (annule and s.get("status") == "in_progress"):
            fautive = s
            break
    if fautive is None:                    # aucune étape en échec : machine perdue en route
        etape, cat = "(aucune étape en échec : machine perdue ?)", "machine"
    else:
        etape, cat = fautive["name"], categorie_etape(fautive["name"])
    if annule:
        relancer = ""
    elif cat == "push":
        relancer = "push"                  # même exécution, sans recalcul : permis à chaque fois
    elif cat == "machine" and not relance and int(tentative) == 1:
        relancer = "workflow"
    else:
        relancer = ""
    return {"etape": etape, "categorie": cat, "depassement": annule, "relancer": relancer}


def fin_du_log(texte, n=LIGNES_LOG):
    """Fin du log de l'étape fautive : sans horodatage, couleurs, variables d'environnement ni nettoyage du job."""
    texte = re.sub(r"\x1b\[[0-9;]*m", "", texte.replace("\r", ""))
    lignes = [l.split(" ", 1)[1] if l[:4].isdigit() and "T" in l[:11] and " " in l else l
              for l in texte.splitlines()]
    if "Post job cleanup." in lignes:
        lignes = lignes[:lignes.index("Post job cleanup.")]
    erreur = next((i for i, l in enumerate(lignes) if l.startswith("##[error]")), len(lignes))
    debuts = [i for i, l in enumerate(lignes[:erreur]) if l.startswith("##[group]Run ")]
    if debuts:                             # depuis le début de l'étape qui a produit la première erreur
        lignes = lignes[debuts[-1]:]
    garde, env = [], False
    for l in lignes:
        if l == "env:":
            env = True
        elif env and l.startswith("##[endgroup]"):
            env = False
        elif not env and not l.startswith(("[command]", "##[endgroup]", "shell: ")):
            garde.append(l)
    return "\n".join(garde[-n:]).replace("```", "ʼʼʼ")


def corps_issue(info, run_url, numero, evenement, relance_txt, log, test=""):
    cat = info["categorie"]
    lignes = [
        f"@{os.environ.get('GITHUB_REPOSITORY_OWNER', '')} le calcul « Semaine suivante » a échoué"
        + (" — **essai simulé** (`test_echec=%s`), rien à corriger" % test if test else "") + ".",
        "",
        f"- Exécution : [n° {numero}]({run_url}) ({evenement})",
        f"- Étape fautive : **{info['etape']}** — {LIBELLES.get(cat, cat)}"
        + (" — job annulé (dépassement des 75 min ou annulation à la main)" if info["depassement"] else ""),
        f"- Relance automatique : {relance_txt}",
        "",
        "<details><summary>Fin du log</summary>",
        "",
        "```",
        log or "(log indisponible)",
        "```",
        "</details>",
        "",
        "Cette issue se ferme toute seule au prochain calcul réussi (relance, secours du dimanche ou lancement à la main).",
    ]
    return "\n".join(lignes)


# ---------------------------------------------------------------------------------------------- API GitHub
def _api(methode, chemin, donnees=None, brut=False):
    url = chemin if chemin.startswith("http") else f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}{chemin}"
    req = urllib.request.Request(url, method=methode, data=json.dumps(donnees).encode() if donnees is not None else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    # pas transmis à l'adresse de redirection (stockage des logs)
    req.add_unredirected_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=60) as r:
        contenu = r.read()
    if brut:
        return contenu.decode("utf-8", "replace")
    return json.loads(contenu) if contenu else None


def _depot():
    return f"/repos/{os.environ['GITHUB_REPOSITORY']}"


def _job_produire():
    run, tentative = os.environ["GITHUB_RUN_ID"], os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    jobs = _api("GET", f"{_depot()}/actions/runs/{run}/attempts/{tentative}/jobs?per_page=100")["jobs"]
    for j in jobs:
        if j["name"] == JOB:
            return j
    raise SystemExit(f"job « {JOB} » introuvable dans l'exécution {run}")


def _sortie(**valeurs):
    chemin = os.environ.get("GITHUB_OUTPUT")
    for k, v in valeurs.items():
        print(f"{k}={v}")
        if chemin:
            with open(chemin, "a", encoding="utf-8") as f:
                f.write(f"{k}={v}\n")


def _issue_ouverte():
    issues = _api("GET", f"{_depot()}/issues?state=open&labels={ETIQUETTE}&per_page=10")
    issues = [i for i in issues if "pull_request" not in i]
    return issues[0] if issues else None


def _etiquette():
    try:
        _api("GET", f"{_depot()}/labels/{ETIQUETTE}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _api("POST", f"{_depot()}/labels",
             {"name": ETIQUETTE, "color": "d73a4a", "description": "Échec du calcul « Semaine suivante »"})


def _url_run():
    return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}" \
           f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"


# ---------------------------------------------------------------------------------------------- commandes
def analyser():
    job = _job_produire()
    info = classer(job, relance=os.environ.get("RELANCE") == "oui",
                   tentative=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    _sortie(categorie=info["categorie"], relancer=info["relancer"], job_id=job["id"])
    with open(os.environ.get("ALERTE_INFO", "alerte_info.json"), "w", encoding="utf-8") as f:
        json.dump(dict(info, job_id=job["id"]), f, ensure_ascii=False)


def signaler():
    with open(os.environ.get("ALERTE_INFO", "alerte_info.json"), encoding="utf-8") as f:
        info = json.load(f)
    try:
        log = fin_du_log(_api("GET", f"{_depot()}/actions/jobs/{info['job_id']}/logs", brut=True))
    except Exception as e:                 # le log peut tarder : l'alerte part quand même
        log = f"(log indisponible : {e})"
    issue_relance = os.environ.get("ISSUE_RELANCE", "")   # résultat de la relance, écrit par le workflow
    relance_txt = {
        "push-ok": "✅ semaine repoussée depuis l'artefact (sans recalcul)",
        "push-echec": "❌ le nouveau push a échoué aussi — voir le job « suivi »",
        "workflow-ok": "🔁 nouvelle exécution lancée (relance=oui) ; elle fermera cette issue si elle réussit",
        "workflow-echec": "❌ impossible de lancer la nouvelle exécution — voir le job « suivi »",
    }.get(issue_relance, "aucune (" + ("job annulé" if info["depassement"]
                                       else "déjà une relance" if info["categorie"] == "machine"
                                       else "relancer donnerait le même résultat") + ")")
    corps = corps_issue(info, _url_run(), os.environ.get("GITHUB_RUN_NUMBER", "?"),
                        os.environ.get("GITHUB_EVENT_NAME", "?"), relance_txt, log, os.environ.get("TEST_ECHEC", ""))
    _etiquette()
    ouverte = _issue_ouverte()
    if ouverte:
        _api("POST", f"{_depot()}/issues/{ouverte['number']}/comments", {"body": corps})
        numero = ouverte["number"]
        print(f"issue #{numero} commentée")
    else:
        numero = _api("POST", f"{_depot()}/issues", {"title": TITRE, "body": corps, "labels": [ETIQUETTE]})["number"]
        print(f"issue #{numero} ouverte")
    if issue_relance == "push-ok":         # rien ne reste à faire : l'issue informe puis se ferme
        _fermer(numero, "✅ Semaine repoussée par le job « suivi » : rien d'autre à faire.")


def relancer():
    ref = os.environ.get("GITHUB_REF_NAME", "main")
    _api("POST", f"{_depot()}/actions/workflows/{WORKFLOW}/dispatches",
         {"ref": ref, "inputs": {"relance": "oui"}})
    print(f"relance lancée sur {ref}")


def _fermer(numero, texte):
    _api("POST", f"{_depot()}/issues/{numero}/comments", {"body": texte})
    _api("PATCH", f"{_depot()}/issues/{numero}", {"state": "closed", "state_reason": "completed"})
    print(f"issue #{numero} fermée")


def cloturer():
    ouverte = _issue_ouverte()
    if not ouverte:
        print("aucune issue ouverte")
        return
    _fermer(ouverte["number"], f"✅ Résolu par l'exécution [n° {os.environ.get('GITHUB_RUN_NUMBER', '?')}]"
                               f"({_url_run()}) ({os.environ.get('GITHUB_EVENT_NAME', '?')}) : calcul réussi.")


if __name__ == "__main__":
    commandes = {"analyser": analyser, "signaler": signaler, "relancer": relancer, "cloturer": cloturer}
    if len(sys.argv) != 2 or sys.argv[1] not in commandes:
        sys.exit(__doc__)
    commandes[sys.argv[1]]()
