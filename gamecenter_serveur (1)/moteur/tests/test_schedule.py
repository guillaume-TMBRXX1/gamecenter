"""Schedule : filtre par franchise et paris sous un match (README section 84). Le site fait tout ; le serveur ne porte
que l'interrupteur GC_SCHEDULE_PLUS (off : #gf-server.schedule_plus = false, le calendrier d'avant).
Le comportement est testé dans le navigateur : outils/site/test_schedule.js.

    python -m unittest moteur.tests.test_schedule        (depuis « gamecenter_serveur (1) »)
"""
import os
import unittest
from unittest import mock

from moteur.tests import test_serveur as ts


class Interrupteur(ts.Base):
    def test_interrupteur(self):
        ts.a_l_heure(self.reg[0]["ko"] - 3600_000)
        for v in ("", "on"):
            with mock.patch.dict(os.environ, {"GC_SCHEDULE_PLUS": v}):
                self.assertNotIn('"schedule_plus"', ts.serveur.page().body.decode())
        for v in ("off", "0", "OFF"):
            with mock.patch.dict(os.environ, {"GC_SCHEDULE_PLUS": v}):
                self.assertIn('"schedule_plus":false', ts.serveur.page().body.decode())


if __name__ == "__main__":
    unittest.main()
