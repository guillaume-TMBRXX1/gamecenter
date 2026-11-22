"""Vidéo « vitrine » : le compte de démonstration filmé (serveur local de faire_vitrine.sh, jamais la production).
   python3 compte_demo.py <url du serveur> <base gamecenter.db> <pseudo>    → écrit {"token", "name"} sur la sortie
Crée le compte (pseudo + mot de passe), lui donne un passé de fidèle — jours de visite des six dernières semaines, une
franchise favorite depuis cinq semaines, quatre votes des supporters — pour que la vue Badges montre des badges gagnés
de fidélité et de supporter (jamais ceux de « lecture du jeu », liés aux paris), et met « Season ticket » en avant à côté
du pseudo. L'accès Insights Pro vient de GC_INSIGHTS_USERS (le serveur est lancé avec ce pseudo)."""
import json, sqlite3, sys, time, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

URL, BASE, PSEUDO = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
TZ = ZoneInfo("Europe/Brussels")


def api(chemin, corps=None):
    req = urllib.request.Request(URL + "/api" + chemin, data=json.dumps(corps).encode() if corps is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


now = api("/time")["now"]
compte = api("/account/register", {"pseudo": PSEUDO, "password": "vitrine-demo-1"})
tok = compte["token"]
jour = datetime.fromtimestamp(now / 1000, TZ).date()
lundi = jour - timedelta(days=jour.weekday())
jours = []
for s in range(6):                                   # six semaines actives d'affilée ; cette semaine, du lundi à aujourd'hui
    l = lundi - timedelta(weeks=s)
    n = (jour - l).days + 1 if s == 0 else (5 if s == 1 else 2)
    jours += [(l + timedelta(days=d)).isoformat() for d in range(min(n, 7))]
con = sqlite3.connect(BASE, timeout=30)
pid = con.execute("SELECT id FROM players WHERE token=?", (tok,)).fetchone()[0]
con.executemany("INSERT OR IGNORE INTO player_days(player, day) VALUES(?,?)", [(pid, d) for d in jours])
equipe = "MRD"
con.execute("UPDATE players SET fav_team=?, fav_team_at=? WHERE id=?", (equipe, now - 5 * 7 * 24 * 3600 * 1000 - 3600e3, pid))
for s in range(1, 5):
    l = (lundi - timedelta(weeks=s)).isoformat()
    con.execute("INSERT OR IGNORE INTO fan_votes(player, week, team, lever, choice, at) VALUES(?,?,?,?,?,?)",
                (pid, l, equipe, "vitrine", "a", now - s * 7 * 24 * 3600 * 1000))
con.commit(); con.close()
b = api("/badges?token=" + tok)
api("/badges/featured", {"token": tok, "badge": "season_ticket"})
print(json.dumps({"token": tok, "name": PSEUDO, "earned": b["earned"]}))
time.sleep(0.1)
