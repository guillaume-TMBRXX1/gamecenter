"""Pages des franchises (AdSense, 29/10/2026) : /teams (les 24 franchises) et /teams/<nom> (une page par franchise).

Google AdSense a refusé le site pour « contenu à faible valeur informative » : tout le site est une seule page dessinée
en JavaScript. Ces pages sont rendues par le serveur, en HTML lisible sans JavaScript, avec un texte écrit pour
chaque franchise (TEXTES, en anglais comme le site) et les données de la semaine en cours : coordinateurs, notes des
unités, titulaires (effectif du début de semaine : rien d'un match pas encore joué), et l'histoire de la franchise
sur les semaines TERMINÉES seulement (pas de spoiler, comme le réglage « Hide scores »). Style : celui de /legal.
"""
import html
import re

# couleurs des franchises (les mêmes que DA_TEAM dans gamecenter_source.html)
COULEURS = {"CTX": "#B38332", "VEC": "#16858A", "AEG": "#315A87", "MNL": "#9E3B3F", "AXM": "#2E8A5E", "GLT": "#6B4FA8",
            "CPH": "#C4672B", "NVA": "#B03A78", "PLS": "#1C8FC0", "ONX": "#3E4A59", "FRG": "#7A4E2D", "MRD": "#6E7F2A",
            "APX": "#D63A3A", "LTC": "#4049A8", "ZPH": "#C9A21B", "BST": "#5B2C6F", "GRZ": "#7D838F", "MRG": "#E2667A",
            "GMB": "#0FA3A3", "PRM": "#7DB82E", "SPK": "#FF8A3D", "CTD": "#264653", "TDL": "#9B5DE5", "CMT": "#F15BB5"}

# style et identité en anglais (les mêmes que STYLE_EN dans gamecenter_source.html)
STYLE_EN = {
    "CTX": ("Balanced, adaptive, versatile", "intelligence, instinct, adaptation"),
    "VEC": ("Offensive, aggressive, pass-first", "precision, calculation, risk-taking"),
    "AEG": ("Defensive, methodical, controlled", "protection, anticipation, discipline"),
    "MNL": ("Physical, run-first, power", "brute force, efficiency, dominance"),
    "AXM": ("Precise, efficient, technical (West Coast)", "execution, timing, efficiency"),
    "GLT": ("Aggressive, disruptive, unpredictable (blitz)", "pressure, chaos, takeaways"),
    "CPH": ("Dynamic, elusive, deceptive (option)", "mobility, reads, deception"),
    "NVA": ("Explosive, vertical, high-risk (big play)", "explosiveness, arm talent, shot plays"),
    "PLS": ("Tempo, no-huddle, relentless rhythm", "speed, rhythm, wearing the defense down"),
    "ONX": ("Opportunistic ball-hawk defense", "instinct, reading the QB, takeaways"),
    "FRG": ("Physical, dominant in the trenches", "line play, power, pocket control"),
    "MRD": ("Strategic, territorial, patient", "field position, special teams, discipline"),
    "APX": ("Clinical red-zone finishers", "finishing, compressed space, situational calls"),
    "LTC": ("Modern spread and RPO", "spacing, numbers, make every defender choose"),
    "ZPH": ("Air raid, passing volume", "vision, distribution, insistence"),
    "BST": ("Lockdown coverage defense", "secondary, discipline, deny the first option"),
    "GRZ": ("Run-erasing defense, balanced offense", "gap discipline, tackling, pursuit"),
    "MRG": ("Play-action and misdirection", "fakes, motion, manipulating the defense"),
    "GMB": ("Bold fourth-down decision makers", "calculated risk, situations, momentum"),
    "PRM": ("Positionless, matchup hunters", "versatility, motion, pre-snap reads"),
    "SPK": ("Young, fast and rising", "potential, speed, daring"),
    "CTD": ("Veteran, poised, mistake-free", "experience, reading, composure"),
    "TDL": ("Wide zone and bootleg", "outside zone, movement play-action, rhythm"),
    "CMT": ("Special teams and speed", "returns, coverage, long field goals"),
}

# texte de chaque franchise : devise, présentation (paragraphes), points forts, points faibles
TEXTES = {
    "CTX": {
        "motto": "Read. Adapt. Exploit.",
        "about": [
            "The Cortex Foxes are the league's chameleons. Where most franchises are built around one dominant idea, the "
            "Foxes are built around the absence of one: their AI coaching staff studies each opponent and writes a new "
            "game plan every week, in the spirit of the opponent-specific plans that made Bill Belichick's New England "
            "teams so hard to prepare for.",
            "On offense that means a genuinely balanced menu. The Foxes will run inside zone against a light box, then "
            "spread the field with three receivers when a defense loads up against the run. Their quarterback is asked to "
            "manage the game more than to win it alone: take what is open, avoid the drive-killing mistake, keep the "
            "chains moving. Defensively the approach is the same: moderate pressure, sound coverage, few gambles.",
            "Watching the Foxes is about watching adjustments. A first quarter that looks ordinary is often the staff "
            "gathering information; the second half is where the plan changes. They rarely blow anyone out, and they "
            "rarely beat themselves.",
        ],
        "strengths": ["Few weaknesses for an opponent to target", "Second-half adjustments", "Low turnover rate"],
        "weaknesses": ["No single elite unit to lean on", "Can be out-muscled by a team that simply imposes its style"],
    },
    "VEC": {
        "motto": "Attack first. Attack again.",
        "about": [
            "The Vector Strikers believe the best defense is a scoreboard that keeps moving. Their offense descends from "
            "the Run and Shoot of Mouse Davis and June Jones and from the vertical spread of Mike Martz's “Greatest "
            "Show on Turf”: four receivers, routes that adjust to the coverage after the snap, and a quarterback "
            "trusted to throw into tight windows.",
            "Expect passes on early downs, when most teams run. The Strikers stretch the field horizontally and "
            "vertically at the same time, forcing safeties to choose between helping deep and stopping the catch-and-run "
            "underneath. When it works, drives last four or five plays. When it does not, the Strikers accept the "
            "punt and the occasional interception as the price of explosiveness.",
            "Their defense is built to hold on rather than to dominate: it needs the offense to keep scoring. Games "
            "involving Vector tend to be high-scoring, with momentum swinging on a single deep ball.",
        ],
        "strengths": ["Explosive passing game", "Scores quickly from anywhere on the field", "Puts trailing teams under pressure"],
        "weaknesses": ["Turnovers that come with aggressive throws", "Defense depends on the offense keeping pace"],
    },
    "AEG": {
        "motto": "Protect. Anticipate. Control.",
        "about": [
            "The Aegis Sentinels win the way Bill Parcells liked to win: control the ball, shorten the game, trust the "
            "defense. Their defensive coordinator borrows from the match-quarters coverage that Nick Saban made famous, "
            "a system in which every defender reads the receivers in front of him and turns zone into man coverage "
            "as the routes declare themselves.",
            "On offense the Sentinels are patient. They prefer a ten-play drive that ends in a field goal to a risky "
            "throw that could hand the ball back. Running backs carry the load, the quarterback plays within structure, "
            "and the special teams unit is among the most reliable in the league, which matters in close games that "
            "the Sentinels deliberately keep close.",
            "The result is a team that is rarely out of a game. Opponents who want to beat the Sentinels have to "
            "string together long, mistake-free drives against a defense that has usually seen the play before.",
        ],
        "strengths": ["One of the league's best defenses", "Strong special teams", "Disciplined, low-penalty football"],
        "weaknesses": ["Limited big-play ability on offense", "Can struggle to come back from a two-score deficit"],
    },
    "MNL": {
        "motto": "Impose the run. Wear them down.",
        "about": [
            "The Monolith Rhinos play football the old way. Their offense lines up under center in the I formation, "
            "with a fullback and often a second tight end, in the tradition of Nebraska's power-I and the gap-blocking "
            "schemes of Greg Roman. The message is simple: we will tell you where we are running and you still will not "
            "stop it.",
            "Power, counter and lead plays make up the core of the playbook. In short yardage and at the goal line the "
            "Rhinos bring in jumbo and heavy packages with extra linemen. Play-action comes off that running game and "
            "is most dangerous in the fourth quarter, when tired linebackers bite on the fake.",
            "Rhinos games are physical and often low on possessions. The longer the game goes, the more their size tells. "
            "Their weakness is the scoreboard: when they fall behind early, their offense is not built to catch up fast.",
        ],
        "strengths": ["Dominant running game", "Short-yardage and goal-line power", "Controls the clock with a lead"],
        "weaknesses": ["Slow to come back from behind", "Predictable formations invite eight-man boxes"],
    },
    "AXM": {
        "motto": "Execute. On time. Every time.",
        "about": [
            "The Axiom Falcons run the West Coast offense in its purest form. Built on Bill Walsh's ideas, it treats the "
            "short pass as an extension of the running game: quick, precise throws timed to the quarterback's drop, "
            "receivers who catch the ball in stride and gain yards after the catch.",
            "Motion is everywhere. Nearly half of the Falcons' snaps start with a receiver or back moving across the "
            "formation, which helps the quarterback identify the coverage before the snap and creates favourable "
            "matchups. Slants, drags, curls and flat routes are thrown on rhythm; when the defense starts jumping the "
            "short stuff, the double moves arrive.",
            "The Falcons win by efficiency rather than by explosive plays. Their games often feel controlled: long "
            "drives, few sacks, high completion rates. Teams that can press their receivers at the line and disrupt "
            "the timing give them the most trouble.",
        ],
        "strengths": ["High completion rate", "Pre-snap motion that reveals coverage", "Yards after the catch"],
        "weaknesses": ["Vulnerable to physical press coverage", "Fewer deep shots than most offenses"],
    },
    "GLT": {
        "motto": "Pressure. Chaos. Takeaways.",
        "about": [
            "The Glitch Hornets want the opposing quarterback uncomfortable on every snap. Their defense draws on Buddy "
            "Ryan's “46” and the creative blitz packages of Jim Johnson: linebackers and defensive backs "
            "showing pressure, dropping out, and arriving from angles the protection did not account for.",
            "The plan is to create negative plays, then turnovers. Sacks, hurried throws and tipped balls are the "
            "Hornets' currency. The risk is real: when a blitz is picked up, there are fewer defenders in coverage and "
            "a single missed tackle can become a long touchdown.",
            "The offense is built to complement the defense with screens and play-action, using a mobile quarterback "
            "who can extend plays outside the pocket. On first down the Hornets like to take a shot after a run fake. "
            "Their games are rarely boring: they swing on takeaways at both ends.",
        ],
        "strengths": ["Sacks and pressure", "Turnovers created by the defense", "Mobile quarterback"],
        "weaknesses": ["Big plays allowed when the blitz is picked up", "Offense less consistent than the defense"],
    },
    "CPH": {
        "motto": "Make them guess. Make them wrong.",
        "about": [
            "The Cipher Lynx run an offense built on deception and quarterback mobility. Their roots are Chris Ault's "
            "Pistol formation and Urban Meyer's spread option: a quarterback a few yards behind the center, a back "
            "directly behind him, and every play offering two or three possible ball carriers.",
            "Read-option, jet sweeps and orbit motion force defenders to stay disciplined in their assignment. A "
            "linebacker who crashes on the running back leaves the quarterback free to keep the ball; an end who waits "
            "for the quarterback lets the back run past. Nearly half of their snaps feature motion.",
            "On defense the Lynx are solid without being spectacular. Their identity lives on offense, where they "
            "ask opponents to be patient and perfect. Against undisciplined defenses, the Lynx can rack up rushing "
            "yards from the quarterback position alone.",
        ],
        "strengths": ["Quarterback running game", "Misdirection and motion", "Difficult to prepare for"],
        "weaknesses": ["Exposes the quarterback to hits", "Less effective when forced to throw from behind"],
    },
    "NVA": {
        "motto": "One throw can change everything.",
        "about": [
            "The Nova Raptors are the league's home-run hitters. Their passing game follows the Air Coryell tradition of "
            "Don Coryell and the modern version popularised by Bruce Arians: take shots downfield, and protect long "
            "enough for the deep routes to develop.",
            "Unlike the spread passing of the Vector Strikers, the Raptors build their big plays on play-action. A run "
            "fake on first down pulls the safeties forward, extra blockers stay in to protect, and the quarterback "
            "looks for a post or a double-post behind the defense. The offense accepts a lower completion rate in "
            "exchange for much bigger gains when the ball does connect.",
            "That profile makes the Raptors streaky. They can look stuck for a quarter, then score twice in three "
            "minutes. Their defense is good enough to keep them in games while they wait for the shot to land.",
        ],
        "strengths": ["Explosive play-action shots", "Big gains per completion", "Can erase a deficit quickly"],
        "weaknesses": ["Lower completion rate", "Stalls when the deep ball is taken away"],
    },
    "PLS": {
        "motto": "No huddle. No rest.",
        "about": [
            "The Pulse Jackals play fast. Their offense follows the tempo philosophy of Chip Kelly's Oregon teams: no "
            "huddle, a small set of plays, and a snap as soon as the ball is spotted. The goal is not complexity but "
            "speed: a defense that cannot substitute or communicate starts to make mistakes.",
            "The playbook is deliberately narrow. The Jackals run the same handful of concepts again and again, with "
            "small variations, betting that perfect execution of a few plays at high speed beats average execution of "
            "many. Over four quarters the effect is cumulative: by the second half, opposing linemen are tired and "
            "missed tackles multiply.",
            "Tempo cuts both ways. Fast three-and-outs leave the Jackals' own defense on the field longer, and games "
            "against them feature more snaps than most. They are at their best when the score is close and the clock "
            "is not yet a factor.",
        ],
        "strengths": ["Tempo that tires defenses", "Simple, well-drilled play menu", "Strong in the second half"],
        "weaknesses": ["Short possessions put pressure on their defense", "Small menu can become predictable"],
    },
    "ONX": {
        "motto": "Read the eyes. Take the ball.",
        "about": [
            "The Onyx Hawks are defined by their defense, and their defense is defined by the football. Built on the "
            "Tampa 2 of Tony Dungy and Monte Kiffin and on Lovie Smith's Chicago defenses, the Hawks play zone "
            "coverage with defenders who read the quarterback's eyes and break on the throw.",
            "The Hawks do not blitz much. They prefer to keep everything in front of them, tackle the catch, and wait for "
            "the mistake: the forced throw over the middle, the ball carried loosely in traffic. Interceptions and "
            "forced fumbles are the measure of a good week.",
            "Their offense is conservative by design: protect the ball, use the short field the defense creates, and "
            "do not hand the opponent the kind of gift the Hawks are hunting for. Low-scoring games suit them perfectly.",
        ],
        "strengths": ["Takeaways", "Disciplined zone coverage", "Short fields for the offense"],
        "weaknesses": ["Offense lacks firepower", "Patient offenses can move the ball underneath"],
    },
    "FRG": {
        "motto": "Win the line. Win the game.",
        "about": [
            "The Forge Bison believe games are decided in the trenches. Their model is Wisconsin football: big offensive "
            "linemen, inside zone and duo runs, and play-action out of two-tight-end sets. On defense, the push comes "
            "from the middle of the line rather than from blitzing linebackers.",
            "The Bison run the ball to set up everything else. Duo, a downhill run where double-teams move defensive "
            "tackles off the ball, is the signature play. Once safeties creep forward, the quarterback fakes the "
            "handoff and finds a tight end or receiver behind them. Their mobile quarterback adds a scrambling "
            "threat when protection breaks down.",
            "Bison games are about attrition. Expect long drives, a strong pocket for their passer and steady pressure "
            "up the middle on the other side. Teams with smaller lines find their afternoons getting longer.",
        ],
        "strengths": ["Offensive line play", "Interior pass rush", "Play-action off a credible run game"],
        "weaknesses": ["Fewer explosive plays", "Can be out-paced by spread offenses"],
    },
    "MRD": {
        "motto": "Win the field. Then win the game.",
        "about": [
            "The Meridian Owls play the long game. Their philosophy echoes Jim Tressel's “Tresselball”: "
            "field position first, the clock second, and no unnecessary risk. A punt pinned inside the opponent's "
            "ten-yard line is, for the Owls, a good play.",
            "Their special teams unit is among the very best in the league and a genuine weapon: long, precise punts, "
            "reliable kicks and coverage that rarely gives up returns. On offense the Owls favour runs, screens and "
            "draws on long downs instead of forcing throws; on defense they play a bend-but-don't-break Cover 2 and "
            "Cover 3 that gives up yards between the twenties and tightens near the goal line.",
            "The Owls rarely put up big numbers, and they do not need to. Their best games look quiet in the box score: "
            "the opponent starts every drive deep in its own territory and runs out of field before it runs out of downs.",
        ],
        "strengths": ["Elite special teams", "Field position", "Red-zone defense"],
        "weaknesses": ["Low-scoring offense", "Struggles in a shoot-out"],
    },
    "APX": {
        "motto": "Twenty yards. Seven points.",
        "about": [
            "The Apex Vipers are specialists of the hardest part of the field. Inside the opponent's twenty, space "
            "shrinks and defenses tighten; that is where the Vipers' staff has invested most of its creativity, with "
            "red-zone concepts borrowed from the Erhardt-Perkins system that New England used to finish drives.",
            "Bunch and stacked receiver sets create natural picks against man coverage. Mesh-wheel, spot and snag "
            "concepts flood a small area with more receivers than defenders, and RPOs and quarterback draws punish "
            "defenses that drop too many players into coverage. Motion is used to confirm whether the defense is in "
            "man or zone before the snap.",
            "Between the twenties the Vipers are a sound but ordinary offense. Their difference shows up in "
            "touchdown percentage: the whole plan is to turn trips inside the red zone into seven points instead of "
            "three.",
        ],
        "strengths": ["Red-zone touchdown rate", "Creative goal-line play calls", "Beats man coverage with picks"],
        "weaknesses": ["Ordinary between the twenties", "Relies on getting into scoring range first"],
    },
    "LTC": {
        "motto": "Every defender has to choose.",
        "about": [
            "The Lattice Wolves run the modern spread built on run-pass options, in the style of the 2017 Philadelphia "
            "offense designed by Doug Pederson and Frank Reich. On many plays the line blocks a run while the "
            "quarterback reads one defender: if he plays the run, the ball goes out to a receiver; if he drops into "
            "coverage, the back gets the handoff.",
            "Bubble screens, tunnel screens and quick throws to the perimeter spread the defense horizontally, and "
            "zone runs attack the space that opens in the middle. The aim is to create numerical advantages: if the "
            "defense puts six players in the box, the Wolves block six and throw outside; if it puts seven, they "
            "throw.",
            "The Wolves are hard to stop on early downs and rarely face long third downs. Defenses that disguise their "
            "intentions after the snap, rather than showing them before, can slow the reads down.",
        ],
        "strengths": ["Efficient on early downs", "Creates numerical advantages", "Few long third downs"],
        "weaknesses": ["Disguised defenses complicate the reads", "Fewer deep shots"],
    },
    "ZPH": {
        "motto": "Spread them out. Throw it again.",
        "about": [
            "The Zephyr Condors are the league's purest passing team. Their offense is Hal Mumme and Mike Leach's Air "
            "Raid: four receivers on most snaps, a short list of concepts drilled to perfection, and a quarterback "
            "who distributes the ball to whoever is open.",
            "Mesh, Y-cross, stick and four verticals form the backbone of the playbook. In spread formations the Condors "
            "even replace their tight end with a fourth wide receiver. On short-yardage downs they keep throwing: "
            "a quick stick or slant is, for them, the equivalent of a running play.",
            "The Condors pile up passing yards and completions. The question each week is whether their defense, a "
            "middle-of-the-pack unit, can get enough stops to let the volume turn into wins.",
        ],
        "strengths": ["Passing volume and completions", "Four-receiver spread sets", "Simple, repeatable concepts"],
        "weaknesses": ["Very little running game", "Defense is average"],
    },
    "BST": {
        "motto": "Nothing open. Nowhere to throw.",
        "about": [
            "The Bastion Panthers build everything around their secondary. Their defense is inspired by the press-man "
            "coverage of Rex Ryan's New York Jets and their shutdown corner Darrelle Revis: cornerbacks who jam "
            "receivers at the line and follow them all over the field, in Cover 1 and Cover 6 shells.",
            "Unlike the Glitch Hornets, the Panthers blitz rarely. They trust their four-man rush and bet that the "
            "quarterback's first read will not be open. Sacks often come late in the down, when the ball has nowhere "
            "to go. Their special teams are also among the strongest in the league.",
            "On offense the Panthers play a measured passing game led by a pocket distributor. They rarely need many "
            "points: a Panthers game is usually a test of how long an opposing offense can stay patient.",
        ],
        "strengths": ["Elite man coverage", "Coverage sacks", "Strong special teams"],
        "weaknesses": ["Offense lacks explosiveness", "Mobile quarterbacks can escape man coverage"],
    },
    "GRZ": {
        "motto": "No room to run.",
        "about": [
            "The Granite Grizzlies are built to erase the running game. Their defense takes after the 2000 Baltimore "
            "defense: disciplined gap control, sure tackling and relentless pursuit, with every defender responsible "
            "for one gap and eleven players running to the ball.",
            "Teams that rely on the run often find themselves in second-and-long against the Grizzlies, which is exactly "
            "where the Grizzlies want them. Their defense is rated among the league's very best and gives up very "
            "few long runs.",
            "The offense is balanced and built around two tight ends, in the image of New England's 2011 attack: "
            "play-action from heavy sets, seam routes and matchups against linebackers. It is not flashy, but it fits "
            "a team that wants to win close games on the strength of its defense.",
        ],
        "strengths": ["Run defense", "Tackling and pursuit", "Two-tight-end offense"],
        "weaknesses": ["Can be stretched by spread passing teams", "Offense rarely produces big numbers"],
    },
    "MRG": {
        "motto": "Nothing is what it seems.",
        "about": [
            "The Mirage Cobras build their offense on illusion. Inspired by the schemes of Kyle Shanahan and Sean "
            "McVay, they make every play look the same before and just after the snap: the same formation, the same "
            "motion, the same first steps by the line, whether the ball is run, faked or thrown.",
            "Jet motion crosses the formation on half of their snaps. Bootlegs move the quarterback away from the "
            "flow of the play, reverses punish defenders who chase too quickly, and the play-action passes are among "
            "the most effective in the league because the runs look identical.",
            "The Cobras' offense is rated among the better units in the league; their defense is more ordinary. When the Cobras "
            "are on, defenders spend the afternoon tackling the wrong man.",
        ],
        "strengths": ["Play-action and bootlegs", "Pre-snap motion", "Reverses and trick plays"],
        "weaknesses": ["Average defense", "Disciplined defenses that stay home limit the misdirection"],
    },
    "GMB": {
        "motto": "Go for it.",
        "about": [
            "The Gambit Stallions have made aggressive decision-making their identity. Taking a cue from the 2017 "
            "Philadelphia team and Dan Campbell's Detroit Lions, they go for it on fourth down far more often than "
            "the rest of the league, convinced that the expected points favour boldness.",
            "That philosophy shapes their play calls. On short-yardage downs the Stallions have a dedicated menu of "
            "bunch formations, quick slants, mesh concepts and RPOs designed to gain one or two yards reliably. On "
            "long downs they take more shots downfield than a conservative team would.",
            "Their games are full of decisive moments. A failed fourth down near midfield gives the opponent a short "
            "field; a successful one keeps a drive alive that most teams would have punted away. The Stallions accept "
            "the variance, and their solid defense helps absorb the misses.",
        ],
        "strengths": ["Fourth-down conversions", "Short-yardage play menu", "Momentum swings"],
        "weaknesses": ["Failed attempts hand opponents short fields", "High variance from game to game"],
    },
    "PRM": {
        "motto": "Find the mismatch.",
        "about": [
            "The Prism Chameleons treat positions as suggestions. Their offense follows Andy Reid's Kansas City "
            "approach: shifts and motions on most snaps, hybrid formations where a running back lines up wide or a "
            "receiver in the backfield, and a constant search for the matchup the defense cannot handle.",
            "Before the snap the Chameleons move players around until the defense shows its hand. A linebacker "
            "following a back out wide signals man coverage; a safety rotating late hints at zone. The quarterback "
            "uses that information to pick the best target before the ball is even snapped.",
            "Their defense is similarly flexible, with multiple fronts and disguised coverages. The Chameleons are "
            "rarely the most talented team on the field, but they are often the hardest to prepare for.",
        ],
        "strengths": ["Pre-snap motion and shifts", "Creates mismatches", "Versatile personnel"],
        "weaknesses": ["Complexity can lead to execution errors", "No dominant unit"],
    },
    "SPK": {
        "motto": "Young. Fast. Fearless.",
        "about": [
            "The Spark Kestrels are the league's youngest and most promising franchise. Their roster is full of players "
            "with room to grow, and their offense reflects that energy: an Air Raid variation in the style of Lincoln "
            "Riley's Oklahoma teams, with vertical routes, jet sweeps and a mobile quarterback.",
            "The Kestrels play with speed everywhere on the field. They test defenses deep early in games and use jet "
            "motion to get the ball to their fastest players in space. Mistakes come with youth: penalties, forced "
            "throws and missed assignments happen more often than with veteran teams.",
            "Following the Kestrels is following a project. Their ratings are not yet among the league's best, but "
            "their players develop week after week, and on their good days they can beat anyone.",
        ],
        "strengths": ["Speed at the skill positions", "Player development", "Vertical passing and jet sweeps"],
        "weaknesses": ["Youthful mistakes", "Inconsistent from week to week"],
    },
    "CTD": {
        "motto": "Composure wins.",
        "about": [
            "The Citadel Rams are the experienced team of the league. Their offense recalls the Indianapolis attack of "
            "Peyton Manning and Tom Moore: few formations, a small number of concepts run to perfection, timing "
            "routes and classic play-action, with a veteran quarterback who reads the defense at the line.",
            "On long downs the Rams lean on the intermediate passing game: curls, dig routes, levels concepts that "
            "attack the area just beyond the sticks. They rarely panic and rarely turn the ball over. Before the snap the "
            "quarterback often changes the play or the protection after reading the defense, the way Manning did "
            "at the line of scrimmage.",
            "The Rams are balanced across offense, defense and special teams, without a glaring weakness. Their games "
            "tend to be decided late, by the team that makes fewer mistakes, which is usually them.",
        ],
        "strengths": ["Composure in close games", "Few turnovers", "Intermediate passing on long downs"],
        "weaknesses": ["Limited athletic upside", "Not built for comebacks from far behind"],
    },
    "TDL": {
        "motto": "Stretch, cut, boot.",
        "about": [
            "The Tidal Herons run the wide zone system that Mike Shanahan made famous in Denver. Offensive linemen step "
            "in unison toward the sideline, the running back reads the first defender to commit and cuts behind the "
            "flow, and the whole offense moves with the rhythm of a wave.",
            "Everything comes off that motion. The bootleg looks exactly like the wide zone at the snap, until the "
            "quarterback keeps the ball and rolls the other way with receivers crossing in front of him. Jet motion "
            "adds a threat to the perimeter and keeps linebackers honest.",
            "The Herons' mobile quarterback is essential to the scheme, and their balanced ratings make them a steady "
            "team. Defenses that stay disciplined on the backside are the ones that slow them down.",
        ],
        "strengths": ["Outside zone running", "Bootleg play-action", "Mobile quarterback"],
        "weaknesses": ["Disciplined backside defenders take away the cutback", "Few deep shots"],
    },
    "CMT": {
        "motto": "Every snap is a chance to score.",
        "about": [
            "The Comet Stingrays believe special teams are a third of the game, not an afterthought. Their model is "
            "“Beamer Ball”, the approach Frank Beamer built at Virginia Tech, where the best athletes play "
            "on kick coverage and returns and the kicking game is coached like the offense.",
            "The Stingrays have one of the highest-rated special teams units in the league: dangerous returners, coverage "
            "units that pin opponents deep, and a kicker trusted from long range. Field goals that other teams would "
            "not attempt are part of their plan.",
            "On offense and defense the Stingrays rely on speed: jet sweeps, quick throws to fast receivers, and an "
            "active defense. They change field position like few others, and a return touchdown can tilt any game in "
            "their favour.",
        ],
        "strengths": ["Elite special teams", "Return game", "Long field goals"],
        "weaknesses": ["Offense and defense are average", "Depends on hidden yardage"],
    },
}

# ordre des postes dans la page (titulaires) et libellés
POSTES = (("QB", "Quarterback"), ("RB", "Running back"), ("WR", "Wide receiver"), ("TE", "Tight end"),
          ("LT", "Left tackle"), ("LG", "Left guard"), ("C", "Center"), ("RG", "Right guard"), ("RT", "Right tackle"),
          ("EDGE", "Edge rusher"), ("DT", "Defensive tackle"), ("LB", "Linebacker"), ("CB", "Cornerback"),
          ("S", "Safety"), ("K", "Kicker"), ("P", "Punter"))
UNITES = (("pass_off", "Passing offense"), ("run_off", "Running offense"), ("pass_def", "Pass defense"),
          ("run_def", "Run defense"), ("special_teams", "Special teams"))

STYLE = """<style>
  :root{--bg:#F4F6FA;--card:#fff;--ink:#121726;--ink-2:#4A5468;--line:#DDE3EE;--accent:#1E5C78}
  :root[data-theme="dark"]{--bg:#0B0E1A;--card:#141A2B;--ink:#EEF2FA;--ink-2:#AEB8CC;--line:#262F45;--accent:#2EE6FF}
  html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
  main{max-width:760px;margin:0 auto;padding:28px 16px 64px}
  a{color:var(--accent)}
  .back{display:inline-block;margin:0 16px 18px 0;font-weight:600;text-decoration:none}
  h1{font-size:30px;line-height:1.15;margin:0 0 6px}
  .lead{color:var(--ink-2);margin:0 0 24px}
  section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:0 0 16px}
  h2{font-size:20px;margin:0 0 8px}
  h3{font-size:16px;margin:14px 0 4px}
  p,li{color:var(--ink-2)}
  ul{padding-left:20px;margin:6px 0}
  .head{display:flex;gap:14px;align-items:center;margin:0 0 6px}
  .badge{flex-shrink:0;display:inline-grid;place-items:center;width:52px;height:52px;border-radius:12px;color:#fff;
    font-weight:800;letter-spacing:.04em;background:var(--tc)}
  .badge.sm{width:38px;height:38px;border-radius:9px;font-size:13px}
  .motto{font-weight:700;color:var(--ink);margin:0 0 10px}
  table{width:100%;border-collapse:collapse;font-size:15px}
  th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
  th{color:var(--ink-2);font-weight:600}
  td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
  .bar{display:inline-block;height:8px;border-radius:4px;background:var(--tc);vertical-align:middle;margin-left:8px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:0 0 16px}
  .tm{display:flex;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;
    padding:12px 14px;text-decoration:none;color:var(--ink)}
  .tm b{display:block}
  .tm small{color:var(--ink-2);line-height:1.35}
  .pm{display:inline-block;font-weight:700;letter-spacing:.04em;padding:6px 12px;border-radius:999px;border:1px solid var(--line);color:var(--ink)}
  footer{color:var(--ink-2);font-size:14px;margin-top:24px}
</style>"""

THEME = ('<script>(function(){var p="auto";try{p=localStorage.getItem("gc-theme")||"auto"}catch(e){}var d=p==="dark"||'
         '(p==="auto"&&window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches);'
         'document.documentElement.setAttribute("data-theme",d?"dark":"light")})();</script>')

PIED = ('<footer><p class="pm">Play money · No real winnings · 18+</p><p>Snapline is an American football simulation: '
        'the teams and players are fictional and every game is played by a computer engine. '
        '<a href="/">Watch the games live</a> · <a href="/teams">All franchises</a> · <a href="/games">Results &amp; recaps</a> · '
        '<a href="/legal">Rules, privacy &amp; legal</a></p></footer>')

e = html.escape


def slug(nom):
    """« Cortex Foxes » → « cortex-foxes »."""
    return re.sub(r"[^a-z0-9]+", "-", (nom or "").lower()).strip("-")


def _page(titre, description, chemin, corps, origine, tete=""):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"<title>{e(titre)}</title>\n<meta name=\"description\" content=\"{e(description)}\">\n"
            f'<link rel="canonical" href="{e(origine + chemin)}">\n'
            f'<meta property="og:type" content="website">\n<meta property="og:site_name" content="Snapline">\n'
            f'<meta property="og:title" content="{e(titre)}">\n<meta property="og:description" content="{e(description)}">\n'
            f'<meta property="og:url" content="{e(origine + chemin)}">\n<meta property="og:image" content="{e(origine)}/og.png">\n'
            '<link rel="icon" href="/favicon.ico" sizes="48x48">\n<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">\n'
            f"{THEME}\n{STYLE}\n{tete}</head>\n<body>\n<main>\n{corps}\n{PIED}\n</main>\n</body>\n</html>\n")


def _bilan(f):
    return f"{f['w']}-{f['l']}" + (f"-{f['t']}" if f.get("t") else "")


def page_index(teams, league, origine, tete=""):
    """/teams : les franchises par conférence et division, avec leur style et un lien vers leur page."""
    parts = ['<a class="back" href="/">← Back to Snapline</a>', "<h1>The 24 franchises</h1>",
             '<p class="lead">Snapline\'s league has 24 fictional franchises, each coached by an AI staff with its own '
             "football philosophy. They are split into two conferences of two divisions, and every week they play a "
             "full season: a regular season in which every team plays all 23 others once, two conference finals and the "
                 "Grand Final. Pick a team to read its "
             "profile, its coaching staff, its starters and its history.</p>"]
    for conf, divs in (league or {}).items():
        parts.append(f"<h2>{e(conf)} Conference</h2>")
        for div, abbrs in divs.items():
            parts.append(f"<h3>{e(div)} Division</h3>\n<div class=\"grid\">")
            for a in abbrs:
                t = teams.get(a)
                if not t:
                    continue
                parts.append(f'<a class="tm" href="/teams/{slug(t["name"])}" style="--tc:{COULEURS.get(a, "#1E5C78")}">'
                             f'<span class="badge sm">{e(a)}</span><span><b>{e(t["name"])}</b>'
                             f"<small>{e(STYLE_EN.get(a, (t.get('style', ''),))[0])}</small></span></a>")
            parts.append("</div>")
    parts.append('<section><h2>How the league works</h2><p>Every franchise has an offensive and a defensive coordinator. '
                 "These AI coaches call every play: they choose formations and concepts from their team's playbook, "
                 "read the down, the distance, the score and the clock, and adjust to what the opponent does. Players "
                 "have ratings that change from week to week with form, age, experience and injuries, so rosters "
                 "evolve over time.</p><p>Each week is a new season. Games kick off every 30 minutes from Monday to "
                 "Friday, the playoffs are played over the weekend, and the Grand Final crowns the week's champion. "
                 "Every game can be watched live, snap by snap, or replayed once it is over.</p></section>")
    return _page("The 24 franchises · Snapline", "Meet the 24 fictional American football franchises of Snapline: "
                 "their coaching philosophies, conferences and divisions.", "/teams", "\n".join(parts), origine, tete)


def page_equipe(a, teams, league, histo, saisons, origine, tete="", recents=None):
    """/teams/<nom> : présentation écrite, identité, staff, notes des unités, titulaires, histoire et division."""
    t = teams[a]
    nom, tc = t["name"], COULEURS.get(a, "#1E5C78")
    txt = TEXTES.get(a, {})
    style, ident = STYLE_EN.get(a, (t.get("style", ""), t.get("identity", "")))
    conf, div = t.get("conference", ""), t.get("division", "")
    co = t.get("coordinators") or {}
    parts = ['<a class="back" href="/">← Back to Snapline</a><a class="back" href="/teams">All franchises</a>',
             f'<div class="head" style="--tc:{tc}"><span class="badge">{e(a)}</span><div><h1>{e(nom)}</h1></div></div>',
             f'<p class="lead">{e(conf)} Conference · {e(div)} Division · {e(style)}</p>']
    sec = [f'<section style="--tc:{tc}"><h2>Profile</h2>']
    if txt.get("motto"):
        sec.append(f'<p class="motto">“{e(txt["motto"])}”</p>')
    sec += [f"<p>{e(p)}</p>" for p in txt.get("about", [])]
    sec.append(f"<p><b>Identity:</b> {e(ident)}.</p>")
    if txt.get("strengths"):
        sec.append("<h3>Strengths</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in txt["strengths"]) + "</ul>")
    if txt.get("weaknesses"):
        sec.append("<h3>Weaknesses</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in txt["weaknesses"]) + "</ul>")
    parts.append("".join(sec) + "</section>")
    parts.append(f"<section><h2>Coaching staff</h2><p>The {e(nom)} are coached by two AI coordinators who call every "
                 "play of every game.</p><ul>"
                 f"<li><b>Offensive coordinator:</b> {e(co.get('offense', '—'))}</li>"
                 f"<li><b>Defensive coordinator:</b> {e(co.get('defense', '—'))}</li></ul></section>")
    u = t.get("units") or {}
    if u:
        rows = "".join(f'<tr><td>{lab}</td><td class="n">{u[k]:.1f}<span class="bar" style="width:{max(0, min(100, (u[k] - 60) * 2.5)):.0f}px"></span></td></tr>'
                       for k, lab in UNITES if isinstance(u.get(k), (int, float)))
        parts.append(f'<section style="--tc:{tc}"><h2>Unit ratings</h2><p>Ratings out of 100, at the start of this '
                     "week. They move from week to week with the players' form, development and injuries.</p>"
                     f'<table><thead><tr><th>Unit</th><th class="n">Rating</th></tr></thead><tbody>{rows}</tbody></table></section>')
    roster = [p for p in t.get("roster") or [] if p.get("depth") == 1]
    if roster:
        ordre = {k: i for i, (k, _) in enumerate(POSTES)}
        lab = dict(POSTES)
        roster.sort(key=lambda p: (ordre.get(p.get("pos"), 99), p.get("number") or 0))
        rows = "".join(f"<tr><td>{e(lab.get(p.get('pos'), p.get('pos', '')))}</td><td>{e(p.get('name', ''))}</td>"
                       f"<td class=\"n\">{e(str(p.get('number', '')))}</td>"
                       f"<td class=\"n\">{e(str((p.get('progression') or {}).get('age', '')))}</td>"
                       f"<td class=\"n\">{e(str((p.get('progression') or {}).get('ovr', '')))}</td></tr>" for p in roster)
        parts.append(f"<section><h2>Starters</h2><p>The {e(nom)} carry {len(t.get('roster') or [])} players. These are "
                     "the starters at the start of this week (OVR: overall rating out of 100).</p>"
                     '<table><thead><tr><th>Position</th><th>Player</th><th class="n">No.</th><th class="n">Age</th>'
                     f'<th class="n">OVR</th></tr></thead><tbody>{rows}</tbody></table></section>')
    if histo and histo.get("seasons"):
        f = histo
        tit = ", ".join(f"week {w}" for w in f.get("title_weeks") or [])
        lignes = [f"<li><b>Seasons played:</b> {f['seasons']}</li>",
                  f"<li><b>All-time record:</b> {_bilan(f)} (points for {f.get('pf', 0)}, against {f.get('pa', 0)})</li>",
                  f"<li><b>Playoff appearances:</b> {f.get('playoffs', 0)}</li>",
                  f"<li><b>Grand Final appearances:</b> {f.get('finals', 0)}</li>",
                  f"<li><b>Titles:</b> {f.get('titles', 0)}" + (f" ({e(tit)})" if tit else "") + "</li>"]
        parts.append("<section><h2>Franchise history</h2><p>Every Snapline week is a full season. Totals over the "
                     f"completed seasons only.</p><ul>{''.join(lignes)}</ul></section>")
    fin = [s for s in saisons or [] if s.get("complete") and a in (s.get("champion"), s.get("runner_up"))]
    if fin:
        li = []
        for s in fin[-6:]:
            adv = s["runner_up"] if s["champion"] == a else s["champion"]
            adv_n = teams.get(adv, {}).get("name", adv)
            res = "won" if s["champion"] == a else "lost"
            li.append(f"<li>Week {s['week']}: {res} the Grand Final against the {e(adv_n)}</li>")
        parts.append(f"<section><h2>Grand Finals</h2><ul>{''.join(li)}</ul></section>")
    if recents:                                      # derniers matchs terminés : liens vers les comptes rendus
        li = "".join(f'<li><a href="/games/{e(r["id"])}">{e(r["texte"])}</a></li>' for r in recents)
        parts.append(f"<section><h2>Latest games</h2><p>Written recaps of the {e(nom)}' most recent games.</p>"
                     f"<ul>{li}</ul></section>")
    rivaux = [x for x in ((league or {}).get(conf) or {}).get(div) or [] if x != a and x in teams]
    if rivaux:
        li = "".join(f'<li><a href="/teams/{slug(teams[x]["name"])}">{e(teams[x]["name"])}</a> — '
                     f"{e(STYLE_EN.get(x, (teams[x].get('style', ''),))[0])}</li>" for x in rivaux)
        parts.append(f"<section><h2>{e(div)} Division rivals</h2><p>The {e(nom)} meet every other franchise once in the "
                     f"regular season; these are the teams they share the {e(div)} Division with.</p><ul>{li}</ul></section>")
    parts.append(f'<section><h2>Watch the {e(nom)}</h2><p>Every game is played live on <a href="/">Snapline</a>, snap '
                 "by snap, with the score, win probability, play calls and commentary. Finished games can be replayed "
                 "on the big screen.</p></section>")
    desc = f"{nom}: {style.lower()}. Profile, coaching staff, ratings, starters and history of this Snapline franchise."
    return _page(f"{nom} · Snapline franchise", desc, f"/teams/{slug(nom)}", "\n".join(parts), origine, tete)
