"""« Interface motion » (README sections 119, 120 et 121) : animations de l'interface au choix du spectateur, coupées par
défaut (Settings › Display). Section 121 : onglets en 180 ms, terrain qui grandit depuis sa vignette, score qui bascule
sur un touchdown, « Bet placed » à la place du bouton, célébration aux couleurs de l'équipe, cascade une fois par
visite, silhouettes des cartes au premier chargement. Les visuels de match des sections 118 et 119 (3D players, Ball flight, Slow motion on big
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
        self.assertIn('if(s&&s.motion===true&&!(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches))'
                      '{var h=document.documentElement;h.setAttribute("data-mo","1");h.classList.add("mo-boot");', amorce)
        # les silhouettes ne restent jamais : retirées au premier dessin de la grille, sinon 1,5 s après DOMContentLoaded
        self.assertIn('document.addEventListener("DOMContentLoaded",function(){setTimeout(function(){h.classList.remove("mo-boot")},1500)})', amorce)
        self.assertIn("document.documentElement.classList.remove('gc-boot','mo-boot');", self.html)

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
                self.assertTrue("body.mo-on" in sel or "html.mo-boot" in sel, ligne.strip()[:80])
        # les fonctions de l'interface ne font rien sans le réglage
        self.assertIn("const moOn=()=>UI_MO&&!REDUCED;", self.html)
        for f in ("moView", "moOpen", "moFly", "moWin", "moChart"):
            corps = self.html[self.html.index(f"function {f}("):]
            self.assertIn("if(!moOn()", corps[:520], f)   # moView retire d'abord les classes d'une cascade finie (section 121)
        self.assertIn("if(!moOn()||el._mv==null", self.html)      # moRoll : sans le réglage, la valeur est posée d'un coup

    def style(self):
        st = self.html[self.html.index('<style id="mo-fx">'):]
        return st[:st.index("</style>")]

    def corps(self, f, n=1600):
        return self.html[self.html.index(f"function {f}("):][:n]

    def test_onglets_courts(self):
        # section 121 : fondu-glissé de 180 ms (150 à 200 ms demandés), retards entre blocs plafonnés à 60 ms
        st = self.style()
        self.assertIn("body.mo-on .mo-in>*{animation:moIn .18s ", st)
        self.assertNotIn(".26s", st)
        retards = [float(x) for x in re.findall(r"\.mo-in>\*:nth-child\([^)]*\)\{animation-delay:([.\d]+)s\}", st)]
        self.assertTrue(retards and max(retards) <= 0.06, retards)

    def test_cascade_une_fois_par_visite(self):
        st = self.style()
        self.assertIn("animation-delay:calc(var(--mo-i,0)*30ms + 40ms)", st)
        self.assertIn("const MO_ITEMS={viewSchedule:'.sch-game',viewNews:'.nw-grid>*'}", self.html)
        items = self.corps("moItems", 700)
        self.assertIn("MO_SEEN.has(el.id)", items)
        self.assertIn("sessionStorage.setItem('gc-mo-seen'", items)
        self.assertIn("sessionStorage.getItem('gc-mo-seen')", self.html)

    def test_score_bascule_sur_un_touchdown(self):
        sc = self.corps("setScore", 500)
        # la valeur est écrite tout de suite ; seule la classe d'animation change (6 à 8 points d'un coup)
        self.assertIn("flip=moOn()&&d>=6&&d<=8&&!document.hidden", sc)
        self.assertLess(sc.index("el.textContent=s;"), sc.index("el.classList.add(flip?'mo-flip':'bump')"))
        self.assertIn("body.mo-on .sc.mo-flip{", self.style())

    def test_pari_pose(self):
        pp = self.corps("moPlaced", 900)
        self.assertIn("if(!UI_MO) return;", pp)
        self.assertIn("navigator.vibrate(15)", pp)
        self.assertIn("b.classList.add('mo-ok')", pp)
        self.assertIn("},1300);", pp)
        self.assertIn('body.mo-on .cta.mo-ok::after{content:"\\2713\\00a0 Bet placed"', self.style())
        # les deux chemins de pose (simple et combiné, local et serveur) le déclenchent
        self.assertGreaterEqual(self.html.count("moPlaced();"), 4)
        # le pied du bulletin reste visible pendant la validation, rien d'autre
        self.assertEqual(self.html.count("document.getElementById('slipFoot').hidden=!onSlip&&!moHeld();"), 2)

    def test_celebration_aux_couleurs_de_l_equipe(self):
        self.assertIn("if(pl>0) moWin(fresh.filter(r=>r.st==='won'));", self.html)
        tm = self.corps("moTeams", 600)
        self.assertIn("if(x==='home'||x==='away') add(s[x]); else { add(s.home); add(s.away); }", tm)
        w = self.corps("moWin", 2200)
        self.assertIn("cols=tm.length?tm.map(a=>DA_TEAM[a]):[FIELD.cyan]", w)
        self.assertIn("radial-gradient(closest-side,${hexA(cols[0],.7)}", w)

    def test_ouverture_depuis_la_vignette(self):
        o = self.corps("moOpen", 2200)
        self.assertIn("const f=p.querySelector('.field')", o)
        self.assertIn("k=a.width/c.width", o)
        self.assertIn("clipPath:ins", o)

    def test_silhouettes_du_chargement(self):
        grille = re.search(r'<section class="live-grid" id="liveGrid" aria-label="Live games">(.*?)</section>', self.html).group(1)
        self.assertEqual(grille.count('class="mo-skt'), 4)
        self.assertEqual(grille.count('aria-hidden="true"'), 4)
        st = self.style()
        self.assertIn(".mo-skt{display:none}", st)
        self.assertIn("html.mo-boot #liveGrid>.mo-skt{display:flex;", st)

    def test_affichage_seulement(self):
        # le rouleau a sa propre horloge, borné entre 0 et 1 : jamais de valeur hors de l'intervalle
        self.assertIn("u=clamp((performance.now()-t0)/d,0,1)", self.html)
        # aucune fonction d'animation n'écrit dans un match, un pari ou l'horloge
        for f in ("moRoll", "moItems", "moView", "moOpen", "moFly", "moPlaced", "moTeams", "moWin", "moChart"):
            c = self.corps(f, 2400)
            c = c[:c.index("\n}\n") if "\n}\n" in c else len(c)]
            for interdit in ("g.hs=", "g.as=", "WAL.bets", "slip.picks=", "CLOCK.", "setClock(", "balance="):
                self.assertNotIn(interdit, c, f"{f} : {interdit}")

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
