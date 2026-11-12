"""Navigation du site (README section 112, 11/11/2026) : barre d'onglets du téléphone, panneau « More », rail à la
hauteur vraiment visible (iPad paysage). Lit gamecenter_source.html tel quel : pas de serveur ni de navigateur.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import re
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(ICI, "..", "..", "gamecenter_source.html"))


class TestNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PAGE, encoding="utf-8") as f:
            cls.html = f.read()

    def test_barre_et_panneau_presents(self):
        for bout in ('<nav class="tabbar" id="tabbar" aria-label="Main navigation">', 'id="moreSheet" role="dialog"',
                     'aria-modal="true"', 'id="moreGrid"', 'id="moreClose"', 'id="moreScrim"'):
            self.assertIn(bout, self.html)

    def test_onglets_principaux_existent_dans_la_rail(self):
        # avec News (section 115, bouton ajouté par newsInit) et sans (GC_NEWS=off)
        avec, sans = re.search(r"const NAV_TABS=NEWS_ON\?\[([^\]]*)\]:\[([^\]]*)\]", self.html).groups()
        for liste in (avec, sans):
            vues = re.findall(r"'(\w+)'", liste)
            self.assertEqual(len(vues), 4, "4 onglets + More : 5 cases sur un téléphone")
            for v in vues:
                self.assertTrue(f'class="rail-btn" type="button" data-view="{v}"' in self.html, v)

    def test_rail_hauteur_visible_et_sans_coupure(self):
        regle = re.search(r"\n  \.rail\{[^}]*\}", self.html).group(0)
        self.assertIn("height:calc(100dvh - 70px)", regle)
        self.assertIn("overflow-y:auto", regle)
        self.assertNotIn("min-height:500px", regle)
        self.assertIn(".rail>*{flex-shrink:0}", self.html)

    def test_flottants_au_dessus_de_la_barre(self):
        # en fin de feuille (après les règles d'origine du bouton Bet slip), sinon elles l'emportent
        bloc = self.html.index(".fab{bottom:calc(76px + env(safe-area-inset-bottom,0px))}")
        self.assertGreater(bloc, self.html.index(".fab{display:none;position:fixed"))
        self.assertLess(bloc, self.html.index('<div class="ticker"'))

    def test_vues_synchronisees(self):
        self.assertIn("  navSync();\n", self.html[self.html.index("function setView("):self.html.index("function setView(") + 2000])
        self.assertIn("navInit();", self.html)


if __name__ == "__main__":
    unittest.main()
