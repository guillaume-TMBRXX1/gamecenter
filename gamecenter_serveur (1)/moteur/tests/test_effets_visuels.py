"""« Interface motion » (README sections 119 et 120) : animations de l'interface au choix du spectateur, coupées par
défaut (Settings › Display). Les visuels de match des sections 118 et 119 (3D players, Ball flight, Slow motion on big
plays, Routes before the snap, Club colours on the field) ont été retirés le 13/11/2026 (section 120) : ce test vérifie
aussi qu'il n'en reste rien. Lit gamecenter_source.html tel quel : pas de serveur ni de navigateur (le rendu est
vérifié par outils/site/test_effets.js).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import re
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(ICI, "..", "..", "gamecenter_source.html"))


class TestInterfaceMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PAGE, encoding="utf-8") as f:
            cls.html = f.read()

    def test_coupe_par_defaut(self):
        self.assertIn("let UI_MO=false;", self.html)
        self.assertIn("motion:d.motion===true,", self.html)
        # l'amorce de la page ne pose data-mo (silhouette du premier chargement) que pour un « true » enregistré
        amorce = self.html[self.html.index('<script id="da-theme-boot">'):self.html.index("</script>")]
        self.assertIn('if(s&&s.motion===true)document.documentElement.setAttribute("data-mo","1")', amorce)

    def test_reglage_dans_display(self):
        self.assertTrue(re.search(r'<span class="set-l" id="setMotionL">Interface motion<small>[^<]+</small></span>\s*'
                                  r'<button type="button" class="switch" role="switch" data-set="motion"', self.html))
        affichage = self.html[self.html.index("<h2>Display</h2>"):self.html.index("${soundCard()}")]
        self.assertLess(affichage.index('data-set="fx"'), affichage.index('data-set="motion"'))

    def test_reglage_applique(self):
        appliquer = self.html[self.html.index("function applySettings(){"):]
        appliquer = appliquer[:appliquer.index("\n}")]
        self.assertIn("UI_MO=!!SET.motion;", appliquer)
        self.assertIn("document.body.classList.toggle('mo-on',UI_MO);", appliquer)

    def test_interface_seulement_avec_le_reglage(self):
        style = self.html[self.html.index('<style id="mo-fx">'):]
        style = style[:style.index("</style>")]
        # chaque règle d'animation de l'interface dépend de body.mo-on ou de html[data-mo], et de « pas de mouvement réduit »
        self.assertIn("@media (prefers-reduced-motion:no-preference){", style)
        for ligne in style.splitlines():
            if "animation:" in ligne and "{" in ligne.split("animation:")[0]:
                sel = ligne.split("{")[0]
                self.assertTrue("body.mo-on" in sel or "html[data-mo]" in sel, ligne.strip()[:80])
        # les fonctions de l'interface ne font rien sans le réglage
        self.assertIn("const moOn=()=>UI_MO&&!REDUCED;", self.html)
        for f in ("moView", "moOpen", "moFly", "moWin", "moChart"):
            corps = self.html[self.html.index(f"function {f}("):]
            self.assertIn("if(!moOn()", corps[:260], f)
        self.assertIn("if(!moOn()||el._mv==null", self.html)      # moRoll : sans le réglage, la valeur est posée d'un coup

    def test_visuels_de_match_retires(self):
        # section 120 : plus aucun des cinq réglages, ni leur code de dessin
        for bout in ("FX_PAWN", "FX_ARC", "FX_SLOW", "FX_ROUTES", "FX_CLUB", "Match visuals", "3D players", "Ball flight",
                     "Slow motion on big plays", "Routes before the snap", "Club colours on the field", "slowSpan",
                     "prePlan", "ballArc", "slow-tag", 'data-set="pawn"', 'data-set="arc"', 'data-set="slow"',
                     'data-set="routes"', 'data-set="club"'):
            self.assertNotIn(bout, self.html, bout)
        # le dessin d'origine du terrain
        self.assertIn("    if(g.t>=g.dur){ rpSnap(g); onSnap(g); }", self.html)
        self.assertIn("c.fillStyle=hexA(FIELD.violet,.16); c.fillRect(X(xs),0,10*s,H);", self.html)
        self.assertIn("c.translate(bx,by-b.h*s*0.55);", self.html)
        self.assertIn("xPath(g.def); c.stroke();", self.html)


if __name__ == "__main__":
    unittest.main()
