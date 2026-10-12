"""Rappels avant le coup d'envoi (bloc 2, étape 6 — Web Push, serveur.py).

Vérifie, sur la dernière semaine de data/weeks : la règle d'envoi (équipe favorite, cloches, fenêtre de 10 minutes, rien
avant que les équipes d'un match de playoffs soient connues, aucun doublon), un tour complet de la boucle (envois notés,
second tour vide), l'oubli d'un abonnement refusé (404 / 410), le texte (équipes et heure, jamais de score), la
validation d'un abonnement. Les envois sont simulés (GC_PUSH_FAKE=1) : rien ne part sur le réseau.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import os
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-rappels-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception as e:                  # pragma: no cover
    serveur = None


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou pas de semaine")
class TestRappels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nom = os.path.basename(SEMAINES[-1])
        cls.lien = os.path.join(serveur.WEEKS_DIR, cls.nom)
        cls.ajoute = not os.path.exists(cls.lien)
        if cls.ajoute:
            os.symlink(SEMAINES[-1], cls.lien)
        cls.w = serveur.load_weeks()[cls.nom[5:]]
        cls.g = cls.w.reg[5]                                         # un match de saison régulière
        cls.semi = cls.w.semis[0]
        os.environ["GC_PUSH_FAKE"] = "1"
        cls.boucle = os.environ.get("GC_PUSH_LOOP")
        os.environ["GC_PUSH_LOOP"] = "0"                             # la boucle d'envoi du serveur ne tourne pas ici

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("GC_PUSH_FAKE", None)
        if cls.boucle is None:
            os.environ.pop("GC_PUSH_LOOP", None)
        else:
            os.environ["GC_PUSH_LOOP"] = cls.boucle
        if cls.ajoute:
            os.unlink(cls.lien)
            serveur._WEEKS.pop(cls.nom[5:], None)

    def setUp(self):
        with serveur._db_lock, serveur.db() as c:
            for t in ("push_subs", "push_bells", "push_sent"):
                c.execute(f"DELETE FROM {t}")
        serveur.PUSH_LOG.clear()

    def sub(self, ep="https://push.example/a", fav=1, fav_team=None, player="p1"):
        return {"endpoint": ep, "player": player, "fav": fav, "fav_team": fav_team or self.g["home"]}

    def dus(self, t, subs, bells=(), sent=()):
        return [(s["endpoint"], w.start, g["id"]) for s, w, g in serveur.rappels_dus(t, subs, set(bells), set(sent))
                if g["id"] in (self.g["id"], self.semi["id"])]

    def test_fenetre_de_dix_minutes(self):
        ko, s = self.g["ko"], [self.sub()]
        self.assertEqual(self.dus(ko - 11 * 60000, s), [])
        self.assertEqual(len(self.dus(ko - 10 * 60000, s)), 1)
        self.assertEqual(len(self.dus(ko - 60000, s)), 1)
        self.assertEqual(self.dus(ko, s), [])                        # coup d'envoi passé : plus de rappel

    def test_equipe_favorite_et_cloches(self):
        t = self.g["ko"] - 5 * 60000
        autre = next(a for a in self.w.doc["teams"] if a not in (self.g["home"], self.g["away"]))
        self.assertEqual(self.dus(t, [self.sub(fav=0)]), [])         # « My team's games » décoché
        self.assertEqual(self.dus(t, [self.sub(fav_team=autre)]), [])
        self.assertEqual(len(self.dus(t, [self.sub(fav_team=self.g["away"])])), 1)
        bell = ("p1", self.w.start, self.g["id"])
        self.assertEqual(len(self.dus(t, [self.sub(fav=0, fav_team=autre)], bells=[bell])), 1)
        self.assertEqual(self.dus(t, [self.sub()], sent=[("https://push.example/a", self.w.start, self.g["id"])]), [])

    def test_playoffs_equipes_connues_seulement(self):
        ko = self.semi["ko"]
        s = [self.sub(fav_team=self.semi["home"])]
        self.assertGreaterEqual(ko - 5 * 60000, self.w.lock)       # les demi-finales sont connues au verrouillage
        self.assertEqual(len(self.dus(ko - 5 * 60000, s)), 1)
        old = self.w.lock
        try:
            self.w.lock = ko                                         # verrouillage pas encore passé : équipes cachées
            self.assertEqual(self.dus(ko - 5 * 60000, s), [])
        finally:
            self.w.lock = old

    def test_tour_complet_sans_doublon(self):
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, fav_team) VALUES('p1','tok-p1','A',0,?)",
                      (self.g["home"],))
            c.execute("INSERT INTO push_subs VALUES('https://push.example/a','p1','BKey_test_value','auth_test1',1,0)")
        try:
            t = self.g["ko"] - 9 * 60000
            n = serveur.push_tour(t)
            mien = [x for x in serveur.PUSH_LOG if x["url"] == f"/?watch={self.g['id']}"]
            self.assertGreaterEqual(n, 1)
            self.assertEqual(len(mien), 1)
            self.assertIn("kickoff in 9 min", mien[0]["title"])
            self.assertEqual(serveur.push_tour(t + 30000), 0)        # déjà envoyé : rien au tour suivant
        finally:
            with serveur._db_lock, serveur.db() as c:
                c.execute("DELETE FROM players WHERE id='p1'")

    def test_abonnement_refuse_oublie(self):
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO push_subs VALUES('https://push.example/gone','p2','BKey_test_value','auth_test1',0,0)")
            c.execute("INSERT INTO push_bells VALUES('p2',?,?)", (self.w.start, self.g["id"]))
        envoi = serveur._push_envoyer
        serveur._push_envoyer = lambda sub, data: False              # le service de notification répond 410
        try:
            self.assertEqual(serveur.push_tour(self.g["ko"] - 60000), 0)
        finally:
            serveur._push_envoyer = envoi
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM push_subs").fetchone()[0], 0)

    def test_texte_sans_score(self):
        d = serveur.rappel_texte(self.w, self.g, self.g["ko"] - 10 * 60000)
        self.assertEqual(d["title"], f"{self.g['away']} @ {self.g['home']} · kickoff in 10 min")
        self.assertEqual(d["url"], f"/?watch={self.g['id']}")
        res = self.g["result"]
        self.assertNotIn(f"{res['away']}-{res['home']}", d["body"] + d["title"])
        self.assertIn("Regular season", d["body"])

    def test_validation_abonnement(self):
        ok = {"subscription": {"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "BKey_test_value", "auth": "auth_test1"}}}
        self.assertEqual(serveur._push_sub_from(ok)[0], "https://fcm.googleapis.com/x")
        for mauvais in ({"subscription": {"endpoint": "http://x", "keys": ok["subscription"]["keys"]}},
                        {"subscription": {"endpoint": "https://x", "keys": {"p256dh": "a b", "auth": "c"}}}, {}):
            with self.assertRaises(HTTPException):
                serveur._push_sub_from(mauvais)


if __name__ == "__main__":
    unittest.main()
