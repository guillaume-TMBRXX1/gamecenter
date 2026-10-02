"""Produit une semaine pour le serveur en exécutant le notebook (section 15.1) sans l'ouvrir.

    python generer_semaine.py --lundi 2026-10-12            # reprend la semaine précédente si elle existe
    python generer_semaine.py --lundi 2026-10-05 --premiere # semaine 1 (staffs de départ)

Variables : GC_NOTEBOOK (chemin du notebook, défaut ./NFL_Sim_GameCenter.ipynb), GC_DATA (défaut ./data).
Durée : l'exécution complète du notebook, ≈ 15 à 20 minutes (tests et démonstrations compris).
"""
import argparse, os, sys, tempfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.environ.get("GC_NOTEBOOK", os.path.join(HERE, "NFL_Sim_GameCenter.ipynb"))
DATA = os.environ.get("GC_DATA", os.path.join(HERE, "data"))
TZ = ZoneInfo("Europe/Brussels")


def run_notebook(monday, weeks_dir, prev_week_json=None, notebook=NOTEBOOK, timeout=3600):
    import nbformat
    from nbclient import NotebookClient
    os.makedirs(weeks_dir, exist_ok=True)
    env = {"GC_WEEK_START": str(monday), "GC_OUT": os.path.abspath(weeks_dir), "GC_PREV_WEEK": os.path.abspath(prev_week_json) if prev_week_json else ""}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)                        # le noyau hérite de l'environnement
    try:
        nb = nbformat.read(notebook, as_version=4)
        with tempfile.TemporaryDirectory() as tmp:
            NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": tmp}}).execute()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    out = os.path.join(weeks_dir, f"week_{monday}", "week.json")
    if not os.path.exists(out):
        raise RuntimeError(f"le notebook n'a pas écrit {out}")
    return out


def _weeks(weeks_dir):
    return sorted(n[5:] for n in os.listdir(weeks_dir) if n.startswith("week_") and os.path.exists(os.path.join(weeks_dir, n, "week.json"))) if os.path.isdir(weeks_dir) else []


def generate_next(weeks_dir, now_ms, lead_hours=48):
    """Si la dernière semaine se termine dans moins de `lead_hours` et que la suivante manque, on la produit."""
    ws = _weeks(weeks_dir)
    if not ws:
        return None
    last = date.fromisoformat(ws[-1])
    nxt = last + timedelta(days=7)
    today = datetime.fromtimestamp(now_ms / 1000, TZ).date()
    this_monday = today - timedelta(days=today.weekday())
    if nxt < this_monday:          # serveur resté éteint plusieurs semaines : on saute à la semaine en cours
        nxt = this_monday          # (staffs repris de la dernière semaine jouée)
    reset = datetime(nxt.year, nxt.month, nxt.day, tzinfo=TZ).timestamp() * 1000
    if reset - now_ms > lead_hours * 3600 * 1000:
        return None
    return run_notebook(nxt, weeks_dir, os.path.join(weeks_dir, f"week_{last}", "week.json"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lundi", help="lundi de la semaine (AAAA-MM-JJ)")
    ap.add_argument("--suivante", action="store_true",
                    help="mode automatique (GitHub) : produit la semaine qui suit la dernière de data/weeks, "
                         "seulement si elle commence dans moins de 72 h ; sinon ne fait rien")
    ap.add_argument("--premiere", action="store_true", help="semaine 1 : ne pas reprendre la semaine précédente")
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--notebook", default=NOTEBOOK)
    a = ap.parse_args()
    if a.suivante:
        import time
        weeks_dir = os.path.join(a.data, "weeks")
        out = generate_next(weeks_dir, int(time.time() * 1000), lead_hours=72)
        print("écrit :", out) if out else print("Rien à faire : la semaine suivante n'est pas encore à produire "
                                               f"(semaines présentes : {', '.join(_weeks(weeks_dir)) or 'aucune'}).")
        sys.exit(0)
    if not a.lundi:
        sys.exit("indiquez --lundi AAAA-MM-JJ (ou --suivante)")
    monday = date.fromisoformat(a.lundi)
    if monday.weekday() != 0:
        sys.exit("--lundi doit être un lundi")
    weeks_dir = os.path.join(a.data, "weeks")
    prev = os.path.join(weeks_dir, f"week_{monday - timedelta(days=7)}", "week.json")
    prev = None if a.premiere or not os.path.exists(prev) else prev
    print("Semaine", monday, "· reprise de", prev or "staffs de départ", "· notebook", a.notebook)
    print("écrit :", run_notebook(monday, weeks_dir, prev, a.notebook))
