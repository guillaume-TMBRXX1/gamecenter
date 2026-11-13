"""Effets visuels au choix du spectateur (README section 119, 13/11/2026) : ralenti des grosses actions, tracés avant le
snap, terrain aux couleurs du club (Settings › Match visuals) et « Interface motion » (Settings › Display). Tous coupés
par défaut. Lit gamecenter_source.html tel quel : pas de serveur ni de navigateur (le rendu est vérifié par
outils/site/test_effets.js).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import re
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(ICI, "..", "..", "gamecenter_source.html"))
REGLAGES = (("slow", "Slow motion on big plays"), ("routes", "Routes before the snap"), ("club", "Club colours on the field"),
            ("motion", "Interface motion"))


class TestEffetsVisuels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PAGE, encoding="utf-8") as f:
            cls.html = f.read()

    def test_coupes_par_defaut(self):
        self.assertIn("let FX_SLOW=false, FX_ROUTES=false, FX_CLUB=false, UI_MO=false;", self.html)
        self.assertIn("slow:d.slow===true, routes:d.routes===true, club:d.club===true, motion:d.motion===true,", self.html)
        # l'amorce de la page ne pose data-mo (silhouette du premier chargement) que pour un « true » enregistré
        amorce = self.html[self.html.index('<script id="da-theme-boot">'):self.html.index("</script>")]
        self.assertIn('if(s&&s.motion===true)document.documentElement.setAttribute("data-mo","1")', amorce)

    def test_reglages_dans_settings(self):
        for nom, titre in REGLAGES:
            self.assertTrue(re.search(r'<span class="set-l" id="set\w+L">' + titre + r"<small>[^<]+</small></span>\s*"
                                      r'<button type="button" class="switch" role="switch" data-set="' + nom + '"', self.html), titre)
        visuels = self.html[self.html.index("<h2>Match visuals</h2>"):self.html.index("${soundCard()}")]
        for nom in ("pawn", "arc", "slow", "routes", "club"):
            self.assertIn(f'data-set="{nom}"', visuels)
        affichage = self.html[self.html.index("<h2>Display</h2>"):self.html.index("<h2>Match visuals</h2>")]
        self.assertIn('data-set="motion"', affichage)

    def test_reglages_appliques(self):
        appliquer = self.html[self.html.index("function applySettings(){"):]
        appliquer = appliquer[:appliquer.index("\n}")]
        self.assertIn("FX_SLOW=!!SET.slow; FX_ROUTES=!!SET.routes; FX_CLUB=!!SET.club; UI_MO=!!SET.motion;", appliquer)
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

    def test_ralenti_ne_change_pas_la_duree(self):
        # la déformation du temps va de 0 à 1 : l'action finit à l'heure
        self.assertIn("if(tau>=1) return 1; if(tau<=0) return 0;", self.html)
        self.assertIn("g.slow=FX_SLOW&&!REDUCED?slowSpan(g,P,g.plan):null;", self.html)
        # sans ralenti, le pas de temps d'origine
        self.assertIn("else { g.t+=dt; if(g.slowOn) g.slowOn=false; }", self.html)

    def test_traces_caches_quand_le_pari_action_suivante_est_ouvert(self):
        pre = self.html[self.html.index("function prePlan(g){"):]
        pre = pre[:pre.index("\n}")]
        self.assertIn("(g.odds&&g.odds.np)) return null;", pre)
        self.assertIn("planFromFeed(Object.assign({},g),P)", pre)      # sur une copie : le match n'est pas touché

    def test_terrain_d_origine_garde(self):
        self.assertIn("c.fillStyle=club?hexA(club,.5):hexA(FIELD.violet,.16);", self.html)
        self.assertIn("else { c.lineWidth=Math.max(1,s*0.08); c.strokeStyle=hexA(FIELD.ink,.4); c.strokeText(T.name.toUpperCase(),0,0); }", self.html)


if __name__ == "__main__":
    unittest.main()
