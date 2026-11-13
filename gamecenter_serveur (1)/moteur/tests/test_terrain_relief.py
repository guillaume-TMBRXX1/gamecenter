"""Joueurs en relief et ballon en cloche (README section 118, 12/11/2026) : deux réglages de Settings › Display, coupés
par défaut ; le dessin d'origine du terrain reste celui du site tant qu'on ne les active pas. Lit gamecenter_source.html
tel quel : pas de serveur ni de navigateur (le rendu lui-même est vérifié par outils/site/test_relief.js).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import re
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(ICI, "..", "..", "gamecenter_source.html"))


class TestTerrainRelief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PAGE, encoding="utf-8") as f:
            cls.html = f.read()

    def test_coupes_par_defaut(self):
        # dans le rendu, et dans les réglages lus du navigateur : seul un « true » enregistré les active
        self.assertIn("let FX_PAWN=false, FX_ARC=false;", self.html)
        self.assertIn("pawn:d.pawn===true, arc:d.arc===true,", self.html)

    def test_reglages_dans_settings(self):
        for nom, titre in (("pawn", "3D players"), ("arc", "Ball flight")):
            m = re.search(r'<div class="set-row"><span class="set-l" id="set(\w+)L">' + titre + r"<small>[^<]+</small></span>\s*"
                          r'<button type="button" class="switch" role="switch" data-set="' + nom + r'" aria-checked="\$\{SET\.' + nom
                          + r'\}" aria-labelledby="set(\w+)L">', self.html)
            self.assertTrue(m, titre)
            self.assertEqual(m.group(1), m.group(2), "l'interrupteur porte le nom de sa ligne")
        # dans la carte « Match visuals » (section 119), après la carte Display
        carte = self.html[self.html.index("<h2>Match visuals</h2>"):self.html.index("${soundCard()}")]
        self.assertLess(self.html.index("<h2>Display</h2>"), self.html.index("<h2>Match visuals</h2>"))
        self.assertLess(carte.index('data-set="pawn"'), carte.index('data-set="arc"'))

    def test_reglages_appliques_au_rendu(self):
        appliquer = self.html[self.html.index("function applySettings(){"):]
        appliquer = appliquer[:appliquer.index("\n}")]
        self.assertIn("FX_PAWN=!!SET.pawn; FX_ARC=!!SET.arc;", appliquer)
        # l'image est redessinée dès qu'un réglage change (signature de l'image)
        sig = self.html[self.html.index("  sigOf(g,x0,y0,s,W,H){"):self.html.index("  endZone(xs,team,X,x0,x1){")]
        self.assertIn("g.down, FX_PAWN, FX_ARC,", sig)

    def test_dessin_d_origine_garde(self):
        dessin = self.html[self.html.index("  draw(dt,now){"):self.html.index("/*@core-end*/", self.html.index("  draw(dt,now){"))]
        # les O et les X : toujours là, sous « sans FX_PAWN »
        debut = dessin.index("if(!FX_PAWN){")
        for bout in ("xPath(g.def); c.stroke();", "c.arc(X(p.x),Y(p.y),r,0,Math.PI*2);", "/* facing chevrons (05/11/2026) */"):
            self.assertGreater(dessin.index(bout), debut, bout)
        # le ballon d'origine : toujours là, quand la cloche n'est pas demandée ou que le ballon n'est pas en l'air
        self.assertIn("const arc=FX_ARC&&g.phase==='play'&&g.plan&&g.plan.flight&&b.h>0.02?g.plan.flight:null;", dessin)
        self.assertIn("c.translate(bx,by-b.h*s*0.55);", dessin)
        # les joueurs debout passent après les marques au sol et avant les noms
        self.assertLess(dessin.index("drawFlag(c,g,fl,X,Y,s)"), dessin.index("if(FX_PAWN) this.pawns(g,X,Y,r,dCol);"))
        self.assertLess(dessin.index("if(FX_PAWN) this.pawns(g,X,Y,r,dCol);"), dessin.index("drawNameTags(c,T,X,Y,r,s,g,ru)"))

    def test_le_jeu_n_est_pas_touche(self):
        # les deux réglages ne sont lus que par le dessin (FieldView, clic sur un joueur) et posés par applySettings
        hors = self.html[:self.html.index("function pickPlayer(view,cx,cy){")] + self.html[self.html.index("const views=[];"):]
        hors = hors.replace("FX_PAWN=!!SET.pawn; FX_ARC=!!SET.arc;", "")
        self.assertNotIn("FX_PAWN", hors)
        self.assertNotIn("FX_ARC", hors)


if __name__ == "__main__":
    unittest.main()
