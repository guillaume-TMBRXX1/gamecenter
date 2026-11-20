"""Badges (programme/Badges_plan.md, BD-1) : le catalogue et les règles, sans base de données ni fichier.

Le serveur rassemble les données d'un compte (jours de visite, paris réglés, votes, ligues, classements) et appelle
evaluer(D) ; le module rend, pour chaque badge du catalogue, le palier gagné et la progression vers le suivant. Tout est
déterministe : mêmes données, mêmes badges. Un badge gagné ne se retire jamais (le serveur le garde dans player_badges ;
ici, on ne fait que dire ce qui est dû).

Décisions de Guillaume (20/11/2026) : comptes seulement ; tous les badges du plan, y compris ceux de « lecture du jeu »
(Upset caller, Perfect day, Combo, Top of the league, Top 10) ; Founding fan jusqu'au 31/12/2026 ; un badge Insights
Pro. Aucun badge pour la mise, le volume de paris, les pertes, les recharges ou le solde ; aucun avantage de jeu.

Données attendues (D) — tout est facultatif sauf "account" :
  account        bool : un compte (pseudo + mot de passe) ; un invité ne gagne rien (progression seulement)
  acct_at        ms : création du compte (Founding fan)
  fav_team_at    ms : depuis quand la franchise favorite est la même (True fan) ; now : ms
  days           ["AAAA-MM-JJ", …] jours de visite (heure de Bruxelles)
  weeks          [{"start": lundi "AAAA-MM-JJ", "final_day": jour de la Grand Final}, …] semaines de la ligue, dans l'ordre
  bets           [{"week", "day", "status": won|lost|push|cashed|open, "price_dec", "kind": ml|sp|tot|fut|combo|sgp,
                   "legs": nombre de sélections}, …]
  fan_votes      [{"week", "majority": bool|None}, …] un vote des supporters par semaine (majority : son choix a été retenu)
  draft_votes    [{"week", "picked": bool}, …] (picked : le prospect qu'il a choisi a été drafté)
  news_votes     nombre de réponses aux questions des articles
  leagues_owned  [nombre de membres, …] des ligues qu'il a créées (lui compris)
  league_wins    nombre de semaines finies en tête d'une ligue privée de 3 membres ou plus
  top10_weeks    nombre de semaines finies dans les 10 premiers du classement de la saison (semaines où TOP10_MIN comptes
                 au moins sont classés : sinon le top 10 ne veut rien dire)
  pro            bool : compte Insights Pro
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

VERSION = "badges-1"
TZ = ZoneInfo("Europe/Brussels")
FOUNDING_AVANT = datetime(2027, 1, 1, tzinfo=TZ)          # Founding fan : compte créé au plus tard le 31/12/2026
UPSET_COTE = 3.0                                          # +200 en cote américaine = 3,0 en cote décimale
PERFECT_MIN = 3                                           # Perfect day : 3 paris réglés au moins, tous gagnés
COMBO_MIN = 3                                             # Combo : 3 sélections au moins
LIGUE_MIN = 3                                             # ligue comptée à partir de 3 membres
TOP10_MIN = 30                                            # Top 10 : seulement une semaine où 30 comptes au moins sont classés
SEMAINE_MS = 7 * 24 * 3600 * 1000

PALIERS = ("bronze", "silver", "gold", "legend")

# (clé, nom, catégorie, seuils des paliers — un seul seuil : badge unique —, description anglaise, unité de progression)
CATALOGUE = [
    ("founding_fan", "Founding fan", "loyalty", (1,), "Created an account before 2027.", None),
    ("season_ticket", "Season ticket", "loyalty", (4, 12, 24, 52), "Active weeks (a visit, a bet or a vote).", "weeks"),
    ("streak", "On a streak", "loyalty", (3, 8, 16), "Active weeks in a row.", "weeks in a row"),
    ("every_day", "Every day this week", "loyalty", (5,), "On Snapline 5 days of the same week.", "days"),
    ("opening_day", "Opening day", "loyalty", (1,), "On Snapline on the Monday a new week opens.", None),
    ("final_night", "Grand Final night", "loyalty", (1,), "On Snapline on Grand Final day.", None),
    ("true_fan", "True fan", "supporter", (4, 12, 24), "Weeks with the same favorite team.", "weeks"),
    ("front_office", "Front office regular", "supporter", (4, 12, 24), "Weeks you voted in the fans' vote.", "votes"),
    ("draft_day", "Draft day", "supporter", (1,), "Voted in a draft.", None),
    ("scouts_pick", "Scout's pick", "supporter", (1,), "Your prospect was drafted.", None),
    ("called_vote", "Called the vote", "supporter", (5,), "Your choice was the fans' pick.", "times"),
    ("upset_caller", "Upset caller", "reader", (1,), "Won a moneyline bet at +200 or longer.", None),
    ("perfect_day", "Perfect day", "reader", (1,), "Every bet of a day won (3 or more).", None),
    ("combo", "Combo", "reader", (1,), "Won a combo of 3 picks or more.", None),
    ("top_league", "Top of the league", "reader", (1,), "Finished a week first in a private league (3+ members).", None),
    ("top10", "Top 10", "reader", (1,), "Finished a week in the season's top 10 (30 players or more ranked).", None),
    ("league_founder", "League founder", "community", (1,), "Created a private league with 3 members or more.", None),
    ("recruiter", "Recruiter", "community", (5,), "Members who joined your leagues.", "members"),
    ("newsroom", "Newsroom", "community", (10, 50, 150), "Answers to the questions under the news.", "answers"),
    ("insights_pro", "Insights Pro", "pro", (1,), "Supports Snapline with Insights Pro.", None),
]
PAR_CLE = {c[0]: c for c in CATALOGUE}
CATEGORIES = ("loyalty", "supporter", "reader", "community", "pro")


def _jour(s):
    return date.fromisoformat(s[:10])


def _lundi(d):
    return d - timedelta(days=d.weekday())


def semaines_actives(D):
    """Les lundis des semaines actives : une visite, un pari ou un vote cette semaine-là (les paris et les votes rendent
    la fidélité rétroactive : elle ne commence pas au jour où les visites ont été enregistrées)."""
    s = {_lundi(_jour(d)) for d in D.get("days") or []}
    for b in D.get("bets") or []:
        if b.get("week"):
            s.add(_jour(b["week"]))
    for v in (D.get("fan_votes") or []) + (D.get("draft_votes") or []):
        if v.get("week"):
            s.add(_lundi(_jour(v["week"])))
    return s


def plus_longue_serie(lundis):
    """Le plus grand nombre de semaines consécutives dans un ensemble de lundis."""
    best = cur = 0
    prev = None
    for d in sorted(lundis):
        cur = cur + 1 if prev is not None and d - prev == timedelta(days=7) else 1
        best = max(best, cur)
        prev = d
    return best


def _valeurs(D):
    """La valeur de chaque badge pour ce compte (nombre ou booléen)."""
    days = sorted({_jour(d) for d in D.get("days") or []})
    actives = semaines_actives(D)
    par_semaine = {}
    for d in days:
        par_semaine.setdefault(_lundi(d), set()).add(d)
    finales = {_jour(w["final_day"]) for w in D.get("weeks") or [] if w.get("final_day")}
    lundis = {_jour(w["start"]) for w in D.get("weeks") or [] if w.get("start")}
    bet_days = {_jour(b["day"]) for b in D.get("bets") or [] if b.get("day")}
    presents = set(days) | bet_days
    bets = D.get("bets") or []
    jours = {}
    for b in bets:
        if b.get("day") and b.get("status") in ("won", "lost", "push", "cashed"):
            jours.setdefault(b["day"][:10], []).append(b["status"])
    perfect = any(len(st) >= PERFECT_MIN and all(x == "won" for x in st) for st in jours.values())
    acct = D.get("acct_at")
    fav = D.get("fav_team_at")
    now = D.get("now")
    owned = [int(n) for n in D.get("leagues_owned") or []]
    return {
        "founding_fan": bool(acct) and datetime.fromtimestamp(acct / 1000, TZ) < FOUNDING_AVANT,
        "season_ticket": len(actives),
        "streak": plus_longue_serie(actives),
        "every_day": max((len(v) for v in par_semaine.values()), default=0),
        "opening_day": bool(presents & lundis),
        "final_night": bool(presents & finales),
        "true_fan": int((now - fav) // SEMAINE_MS) if fav and now and now >= fav else 0,
        "front_office": len({v["week"] for v in D.get("fan_votes") or [] if v.get("week")}),
        "draft_day": bool(D.get("draft_votes")),
        "scouts_pick": any(v.get("picked") for v in D.get("draft_votes") or []),
        "called_vote": sum(1 for v in D.get("fan_votes") or [] if v.get("majority")),
        "upset_caller": any(b.get("status") == "won" and b.get("kind") == "ml" and (b.get("price_dec") or 0) >= UPSET_COTE
                            for b in bets),
        "perfect_day": perfect,
        "combo": any(b.get("status") == "won" and b.get("kind") in ("combo", "sgp") and (b.get("legs") or 0) >= COMBO_MIN
                     for b in bets),
        "top_league": int(D.get("league_wins") or 0),
        "top10": int(D.get("top10_weeks") or 0),
        "league_founder": any(n >= LIGUE_MIN for n in owned),
        "recruiter": sum(max(0, n - 1) for n in owned),
        "newsroom": int(D.get("news_votes") or 0),
        "insights_pro": bool(D.get("pro")),
    }


def evaluer(D):
    """Pour chaque badge du catalogue : {"key", "name", "category", "description", "tier" (palier gagné : 1, 2… ; 0
    sinon), "tier_name", "tiers", "value", "next" (seuil du palier suivant, None au dernier), "unit", "earned"}.
    Un invité (account faux) n'a aucun palier gagné : seulement la progression."""
    v = _valeurs(D)
    compte = bool(D.get("account"))
    out = []
    for cle, nom, cat, seuils, desc, unite in CATALOGUE:
        x = v[cle]
        n = int(x) if not isinstance(x, bool) else int(x)
        palier = sum(1 for s in seuils if n >= s) if compte else 0
        suivant = seuils[palier] if palier < len(seuils) else None
        out.append({"key": cle, "name": nom, "category": cat, "description": desc, "tiers": list(seuils), "unit": unite,
                    "value": n, "tier": palier, "earned": palier > 0,
                    "tier_name": (PALIERS[palier - 1] if len(seuils) > 1 else "") if palier else "",
                    "next": suivant})
    return out


def gagnes(D):
    """{clé: palier} des badges gagnés (le serveur les écrit dans player_badges s'ils sont nouveaux ou plus hauts)."""
    return {b["key"]: b["tier"] for b in evaluer(D) if b["earned"]}


def nouveaux(deja, maintenant):
    """Les badges à écrire : ceux qui n'étaient pas gagnés, ou gagnés à un palier plus bas (jamais une baisse)."""
    return {k: t for k, t in maintenant.items() if t > int(deja.get(k, 0))}
