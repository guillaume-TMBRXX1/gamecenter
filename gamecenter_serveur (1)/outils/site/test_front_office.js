// Front office FO-4 (My team › Front office : le vote des supporters) — test navigateur (Playwright + serveur réel,
// copie des deux dernières semaines, horloge réglée par GC_DEMO_AT).
//   node outils/site/test_front_office.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Les semaines publiées n'ont pas encore de question (le moteur l'écrit à partir de la semaine du 16/11) : la copie de la
// semaine en cours reçoit une question (fan_vote, 4e essai) et un choix appliqué (fans), la semaine d'avant la question
// qui a décidé de cette semaine (course / passe, 6 votes de supporters de CTX en base) ; un match reçoit game.fans_plan.
// Écrans validés sur l'iPad (11/11). Vérifie, jeudi soir (vote ouvert) :
//   - invité : invitation à créer un compte (qui parle du vote) ;
//   - compte de VEC : rappel « Vote now » sur Overview ;
//   - compte de CTX : onglets Overview / Front office ; écran de vote par défaut : « Fan vote · for week N », titre avec
//     le nom du coordinateur, trois cartes (« AI default » sur Coordinator's call, projection par match), les chiffres
//     de la semaine (Faced / Went for it / Converted / League avg), le compte à rebours, aucune part du vote avant le
//     verrou ; colonne « How it works » et « In effect this week » (More passing · 67 %, 6 votes, part des courses
//     avant → maintenant) ; « Cast my vote » puis « Change my vote » (enregistrés sur le serveur) ; « See the vote » :
//     la révélation (« The … fans have decided », barres triées, prochain match, cotes et « Fans' plan »), « Vote » y
//     ramène ;
//   - compte qui a changé de franchise cette semaine : options désactivées, raison affichée ;
//   - page Teams : le choix des supporters de chaque franchise, en lecture seule ; Match centre : la ligne du levier ;
//   - téléphone 390 px : options l'une sous l'autre, pas de défilement horizontal, marge pour le bouton « Bet slip » ;
// lundi matin : la révélation s'affiche d'abord ; après le verrou : « The … fans have decided » pour la semaine
// suivante (1 vote : le coordinateur décide), « Your vote », plus de bouton de vote ; interrupteur GC_FRONT_OFFICE=off :
// ni onglets ni ligne sur Teams. Aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn, spawnSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8183, URL0=`http://localhost:${PORT}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const CAP=process.env.FO_CAPTURES||'';            // dossier : captures des écrans (validation), facultatif
const capture=async(p,nom,sel)=>{ if(!CAP) return; fs.mkdirSync(CAP,{recursive:true}); await p.waitForTimeout(400);
  const el=sel?await p.$(sel):null; await (el||p).screenshot({path:path.join(CAP,nom+'.png'),...(el?{}:{fullPage:false})}); };
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

/* ---- les données : copie des deux dernières semaines, une question posée ---- */
const NOMS=fs.readdirSync(WEEKS).filter(n=>n.startsWith('week_')).sort().slice(-2);
const DATA=fs.mkdtempSync(path.join(os.tmpdir(),'gc-fo4-'));
process.on('exit',()=>{ try{ fs.rmSync(DATA,{recursive:true,force:true}); }catch(e){} });
for(const n of NOMS) fs.cpSync(path.join(WEEKS,n),path.join(DATA,'weeks',n),{recursive:true});
const [PREV,CUR]=NOMS.map(n=>path.join(DATA,'weeks',n,'week.json'));
const W=JSON.parse(fs.readFileSync(CUR,'utf8')), P=JSON.parse(fs.readFileSync(PREV,'utf8'));
const LUNDI=W.week.start, SUIVANT=new Date(Date.parse(LUNDI+'T12:00:00Z')+7*864e5).toISOString().slice(0,10);
const TEAMS=Object.keys(W.teams);
const question=(week,index,lever,label,q,opts)=>({version:'supporters-1',index,week,lever,label,question:q,side:'offense',setting:'x',
  options:opts.map(([id,l])=>({id,label:l})),teams:Object.fromEntries(TEAMS.map(a=>[a,{current:2,bands:[1,3],values:{}}]))});
const Q4=[['prudent','Play it safe'],['coordinateur',"Coordinator's call"],['agressif','Go for it']];
const RP=[['plus_course','More runs'],['coordinateur',"Coordinator's call"],['plus_passe','More passes']];
W.fan_vote=question(SUIVANT,W.week.index+1,'quatrieme','4th down','How bold should we be on fourth down?',Q4);
W.fans={version:'supporters-1',lever:'course_passe',label:'Run or pass',side:'offense',setting:'pass_shift',file:'x',file_read:true,
  applied:Object.fromEntries(TEAMS.map(a=>[a,a==='CTX'?{choice:'plus_passe',source:'fans',votes:6}:{choice:'coordinateur',source:'coordinators',votes:0}]))};
P.fan_vote=question(LUNDI,P.week.index+1,'course_passe','Run or pass','Should we lean on the run or the pass?',RP);
fs.writeFileSync(CUR,JSON.stringify(W)); fs.writeFileSync(PREV,JSON.stringify(P));
/* un match terminé jeudi soir reçoit le choix des supporters (Match centre) */
const G=W.schedule.find(g=>g.phase==='regular'&&(g.home==='CTX'||g.away==='CTX'))||W.schedule[0];
const gf=path.join(DATA,'weeks',NOMS[1],G.feed), F=JSON.parse(fs.readFileSync(gf,'utf8'));
F.game.fans_plan={lever:'course_passe',label:'Run or pass',side:'offense',home:{choice:G.home==='CTX'?'plus_passe':'coordinateur',source:G.home==='CTX'?'fans':'coordinators',votes:G.home==='CTX'?6:0},
  away:{choice:G.away==='CTX'?'plus_passe':'coordinateur',source:G.away==='CTX'?'fans':'coordinators',votes:G.away==='CTX'?6:0}};
fs.writeFileSync(gf,JSON.stringify(F));
const LOCK=Date.parse(W.week.standings_locked_at);
const iso=ms=>new Date(ms).toISOString();

async function server(at,extra){
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:DATA,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:at},extra||{}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(URL0+'/api/time'); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const arreter=async p=>{ while(OUVERTES.length) await OUVERTES.pop().close().catch(()=>{});   // pages fermées : plus d'animation
  await new Promise(r=>{ p.on('exit',r); p.kill(); }); };
const api=async(u,body)=>{ const r=await fetch(URL0+'/api'+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}); return {status:r.status,json:await r.json().catch(()=>null)}; };
const sql=(q)=>{ const r=spawnSync('python3',['-c',`import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(sys.argv[2]); c.commit()`,path.join(DATA,'gamecenter.db'),q]); if(r.status) throw new Error(String(r.stderr)); };
const OUVERTES=[];
const ouvrir=async(b,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message)); OUVERTES.push(ctx);
  await p.goto(URL0+'/',{timeout:120000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); return p; };
const connecter=async(p,c)=>{ await p.evaluate(c=>localStorage.setItem('gc-player-v1',JSON.stringify({token:c.token,name:c.name,account:true,fav_team:c.fav})),c);
  await p.reload({timeout:120000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); };
const myteam=async p=>{ await p.click('.rail-btn[data-view="myteam"]'); await p.waitForSelector('#viewMyteam .mt-bar, #viewMyteam .st-empty',{timeout:15000}); };
const frontOffice=async p=>{ await p.click('#viewMyteam [data-mttab="fo"]'); await p.waitForSelector('#viewMyteam .fo-wrap',{timeout:15000}); };
const texte=async(p,s)=>((await p.textContent(s))||'').replace(/\s+/g,' ').trim();
const compte=async(pseudo,fav,changee)=>{ const c=(await api('/account/register',{pseudo,password:'motdepasse1'})).json;
  if(changee) await api('/account/team',{token:c.token,team:fav});               // franchise choisie cette semaine
  else sql(`UPDATE players SET fav_team='${fav}' WHERE token='${c.token}'`);     // tenue depuis avant le lundi
  return {token:c.token,name:c.name,fav}; };

(async()=>{
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  let srv=await server(iso(LOCK-28*3600e3));                                      // jeudi soir : vote ouvert
  try{
    /* la question qui a décidé de cette semaine : 6 votes de supporters de CTX (4 plus de passes, 2 plus de courses) */
    sql([...Array(6).keys()].map(i=>`INSERT INTO fan_votes(player,week,team,lever,choice,at) VALUES('v${i}','${LUNDI}','CTX','course_passe','${i<4?'plus_passe':'plus_course'}',0);`).join(''));
    const A=await compte('FanCTX','CTX'), B=await compte('FanVEC','VEC'), C=await compte('Transfuge','AEG',true);

    /* ---- invité ---- */
    const g=await ouvrir(b); await myteam(g);
    check(/fans vote each week/.test(await texte(g,'#viewMyteam')),'invité : invitation à créer un compte, qui parle du vote');
    errs.push(...g.errs); await g.context().close();

    /* ---- compte de VEC : le rappel « Vote now » sur Overview ---- */
    const pb=await ouvrir(b); await connecter(pb,B); await myteam(pb);
    await pb.waitForSelector('#viewMyteam .fo-teaser',{timeout:15000});
    await capture(pb,'3-overview-rappel','#viewMyteam .fo-teaser');
    check(/How bold should we be on fourth down\?/.test(await texte(pb,'#viewMyteam .fo-teaser')),'Overview : rappel « Vote now » tant que le compte n’a pas voté');
    errs.push(...pb.errs); await pb.context().close();

    /* ---- compte de CTX : Front office ---- */
    const p=await ouvrir(b); await connecter(p,A); await myteam(p);
    const tabs=await p.$$eval('#viewMyteam .mt-tabs [data-mttab]',bs=>bs.map(b=>b.textContent.trim()));
    check(tabs.join('|')==='Overview|Front office',`My team : onglets Overview / Front office (${tabs.join(' | ')})`);
    await frontOffice(p); await p.waitForSelector('#viewMyteam [data-fo="question"]',{timeout:15000});
    check(!!(await p.$('#viewMyteam [data-foscreen="vote"]')),'jeudi : l’écran de vote par défaut');
    const qtxt=await texte(p,'#viewMyteam [data-fo="question"]'), COORD=W.teams.CTX.coordinators.offense;
    check(new RegExp('Fan vote · for week '+(W.week.index+1),'i').test(qtxt),`« Fan vote · for week ${W.week.index+1} »`);
    check(qtxt.includes(`4th down next week: how bold should ${COORD} be?`),`titre avec le coordinateur offensif (${COORD})`);
    check((await p.$$('#viewMyteam [data-fochoice]')).length===3,'trois options');
    const coordTxt=await texte(p,'#viewMyteam [data-fochoice="coordinateur"]');
    check(/AI default/.test(coordTxt)&&coordTxt.includes(COORD.split(' ').slice(-1)[0]+'’s usual plan'),'« AI default » et le plan du coordinateur sur Coordinator’s call');
    const st=(await api('/fans?token='+A.token)).json.stats;
    if(st&&st.games){
      check(/per game, as this week/.test(coordTxt)&&/go-for-its per game/.test(await texte(p,'#viewMyteam [data-fochoice="agressif"]')),'projection par option (go-for-its par match)');
      const tiles=await p.$$eval('#viewMyteam .fo-tile span',e=>e.map(x=>x.textContent.trim().toLowerCase()));
      check(tiles.join('|')==='faced|went for it|converted|league avg / game',`chiffres de la semaine : ${tiles.join(' · ')}`);
      check(qtxt.includes(`on 4th down this week · ${st.games} game`),`« … on 4th down this week · ${st.games} games »`);
    } else check(/numbers appear after the first game/.test(qtxt),'pas encore de match : les chiffres viendront');
    check(/Closes \w{3} 23:30 · \d/.test(qtxt),'compte à rebours avant la fermeture (« Closes Fri 23:30 · … »)');
    check(!/%/.test(qtxt),'aucune part du vote avant le verrou');
    const inf=await texte(p,'#viewMyteam [data-fo="in-force"]');
    check(/In effect this week/.test(inf)&&/More passing · 67\s?%/.test(inf)&&/Votes\s?6/.test(inf)&&/Run share\s?\d+\s?% → \d+\s?%/.test(inf),`« In effect this week » : More passing · 67 %, 6 votes, part des courses (${inf.slice(0,90)})`);
    check(/How it works/.test(await texte(p,'#viewMyteam .fo-how')),'colonne « How it works »');
    await capture(p,'1-vote','#viewMyteam');
    const cast=await p.evaluate(()=>{ const c=document.querySelector('#viewMyteam [data-fovote]'); return {d:c.disabled,t:c.textContent}; });
    check(cast.d&&/Cast my vote/.test(cast.t),'« Cast my vote », désactivé tant qu’aucune option n’est choisie');
    await p.click('#viewMyteam [data-fochoice="agressif"]');
    check(await p.evaluate(()=>getComputedStyle(document.querySelector('#viewMyteam [data-fochoice="agressif"]')).color==='rgb(255, 255, 255)'),'option choisie : carte foncée, texte blanc');
    await p.click('#viewMyteam [data-fovote]');
    await p.waitForSelector('#viewMyteam .fo-msg.ok',{timeout:10000});
    check((await api('/fans?token='+A.token)).json.my_vote==='agressif','vote enregistré sur le serveur (« Go for it »)');
    await p.click('#viewMyteam [data-fochoice="prudent"]');
    check(/Change my vote/.test(await p.textContent('#viewMyteam [data-fovote]')),'« Change my vote » quand on choisit une autre option');
    await p.click('#viewMyteam [data-fovote]'); await p.waitForSelector('#viewMyteam .fo-msg.ok',{timeout:10000});
    check((await api('/fans?token='+A.token)).json.my_vote==='prudent','vote changé (« Play it safe »)');
    check(/Your vote/.test(await texte(p,'#viewMyteam [data-fochoice="prudent"]')),'« Your vote » sur l’option votée');
    await capture(p,'2-vote-enregistre','#viewMyteam [data-fo="question"]');
    /* la révélation du vote qui a décidé de cette semaine */
    await p.click('#viewMyteam [data-foview="reveal"]'); await p.waitForSelector('#viewMyteam [data-fo="result"]',{timeout:10000});
    const rev=await texte(p,'#viewMyteam .fo-rev'), res=await texte(p,'#viewMyteam [data-fo="result"]');
    check(rev.includes(`The ${W.teams.CTX.name} fans have decided`)&&new RegExp('Week '+W.week.index+' · results of the fan votes','i').test(rev),'révélation : « Week N · results of the fan votes », « The … fans have decided »');
    const bars=await p.$$eval('#viewMyteam [data-fo="result"] .fo-bar',e=>e.map(x=>x.textContent.replace(/\s+/g,' ').trim()));
    check(/^More passes\s?67\s?%/.test(bars[0])&&/^More runs\s?33\s?%/.test(bars[1])&&/0\s?%$/.test(bars[2]),`barres triées, la gagnante en tête (${bars.join(' | ')})`);
    check(/Run or pass · 6 votes/i.test(res)&&/In effect for every .* game this week/.test(res),'« Run or pass · 6 votes », « In effect for every … game this week »');
    const nx=await texte(p,'#viewMyteam .fo-nextc');
    if(await p.$('#viewMyteam .fo-match')){
      check(/Fans’ plan/.test(nx)&&/More passes · the odds include it/.test(nx)&&(await p.$$('#viewMyteam .fo-match .odd')).length===2,'prochain match : cotes et « Fans’ plan · More passes · the odds include it »');
    } else check(/No game left/.test(nx),'plus de match cette semaine');
    check(/New fan vote · for week/i.test(nx)&&/How bold on 4th down next week\?/.test(nx)&&/You voted Play it safe/.test(nx),'nouvelle question : « How bold on 4th down next week? », mon vote rappelé');
    await capture(p,'3-revelation','#viewMyteam');
    await p.click('#viewMyteam .fo-nextc [data-foview="vote"]'); await p.waitForSelector('#viewMyteam [data-foscreen="vote"]',{timeout:10000});
    check(true,'« Change » ramène à l’écran de vote');
    await p.click('#viewMyteam [data-mttab="overview"]'); await p.waitForSelector('#viewMyteam .team-page',{timeout:10000});
    check(!(await p.$('#viewMyteam .fo-teaser')),'Overview : plus de rappel une fois le vote fait');

    /* ---- page Teams et Match centre ---- */
    await p.click('.rail-btn[data-view="teams"]'); await p.click('#viewTeams [data-team="CTX"]');
    await p.waitForSelector('#viewTeams .fo-line',{timeout:10000});
    await capture(p,'5-teams-ctx','#viewTeams .team-page');
    check(/More passes/.test(await texte(p,'#viewTeams .fo-line'))&&/6 votes/.test(await texte(p,'#viewTeams .fo-line')),'Teams : le choix des supporters de CTX, en lecture seule');
    await p.click('#viewTeams [data-team="CTX"]'); await p.click('#viewTeams [data-team="VEC"]'); await p.waitForSelector('#viewTeams .fo-line',{timeout:10000});
    check(/Coordinator's call/.test(await texte(p,'#viewTeams .fo-line')),'Teams : VEC, le coordinateur');
    const row=await p.evaluate(([gid,F])=>{ const gm={id:gid,home:F.game.home.abbr,away:F.game.away.abbr,gf:F,plays:F.plays};
      return window.__gc.fo.foGameRow(gm,F.plays.length); },[G.id,F]);
    check(row&&/Run plays/.test(row[0])&&/Fans’ plan/.test(row[0])&&/%/.test(row[1])&&/More passes/.test(row[G.home==='CTX'?2:1]),`Match centre : ligne « Run plays » et « Fans’ plan » (${row?row.slice(1,3).join(' / ').replace(/<[^>]+>/g,''):'—'})`);
    errs.push(...p.errs);

    /* ---- compte qui a changé de franchise cette semaine ---- */
    const pc=await ouvrir(b); await connecter(pc,C); await myteam(pc); await frontOffice(pc);
    await pc.waitForSelector('#viewMyteam [data-fo="question"]',{timeout:15000});
    check(/your vote counts from Monday/.test(await texte(pc,'#viewMyteam [data-fo="question"]'))&&await pc.evaluate(()=>[...document.querySelectorAll('#viewMyteam [data-fochoice]')].every(b=>b.disabled)),'franchise changée cette semaine : raison affichée, options désactivées');
    errs.push(...pc.errs); await pc.context().close();

    /* ---- téléphone 390 px ---- */
    const ph=await ouvrir(b,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true}); await connecter(ph,A);
    await ph.evaluate(()=>window.__gc.season.setView('myteam')); await ph.waitForSelector('#viewMyteam .mt-bar',{timeout:15000});
    await frontOffice(ph); await ph.waitForSelector('#viewMyteam [data-fo="question"]',{timeout:15000});
    const lay=await ph.evaluate(()=>{ const o=[...document.querySelectorAll('#viewMyteam .fo-opt')].map(e=>e.getBoundingClientRect());
      return {sw:document.documentElement.scrollWidth, w:innerWidth, stacked:o.length===3&&o[1].top>o[0].bottom-1&&o[2].top>o[1].bottom-1,
        pad:parseFloat(getComputedStyle(document.querySelector('#viewMyteam .fo-wrap')).paddingBottom)}; });
    if(CAP){ await ph.waitForTimeout(400); await ph.screenshot({path:path.join(CAP,'6-telephone.png'),fullPage:true}); }
    check(lay.sw<=lay.w,`téléphone : pas de défilement horizontal (${lay.sw} px pour ${lay.w})`);
    check(lay.stacked,'téléphone : les trois options l’une sous l’autre');
    check(lay.pad>=60,`téléphone : marge en bas pour le bouton « Bet slip » (${lay.pad} px)`);
    errs.push(...ph.errs); await ph.context().close();
  }finally{ await arreter(srv); }

  /* ---- lundi matin : la révélation d'abord ---- */
  srv=await server(iso(Date.parse(LUNDI+'T09:00:00'+(W.week.standings_locked_at.match(/([+-]\d\d:\d\d|Z)$/)||['','Z'])[1])));
  try{
    const A=(await api('/account/login',{pseudo:'FanCTX',password:'motdepasse1'})).json;
    const p=await ouvrir(b); await connecter(p,{token:A.token,name:A.name,fav:'CTX'}); await myteam(p); await frontOffice(p);
    await p.waitForSelector('#viewMyteam [data-foscreen]',{timeout:15000});
    check(!!(await p.$('#viewMyteam [data-foscreen="reveal"]')),'lundi : la révélation s’affiche d’abord');
    check(/Vote|Change/.test(await texte(p,'#viewMyteam .fo-nextc [data-foview="vote"]')),'lundi : bouton vers la nouvelle question');
    errs.push(...p.errs);
  }finally{ await arreter(srv); }

  /* ---- après le verrou du vendredi ---- */
  srv=await server(iso(LOCK+10*3600e3));
  try{
    const A=(await api('/account/login',{pseudo:'FanCTX',password:'motdepasse1'})).json;
    const p=await ouvrir(b); await connecter(p,{token:A.token,name:A.name,fav:'CTX'}); await myteam(p); await frontOffice(p);
    await p.waitForSelector('#viewMyteam [data-fo="result"]',{timeout:15000});
    const res=await texte(p,'#viewMyteam [data-fo="result"]');
    check(/fans have decided/.test(await texte(p,'#viewMyteam .fo-rev'))&&/Applies next week/.test(res)&&/Fewer than 5 votes/.test(res),'après le verrou : résultat de la semaine suivante (1 vote : le coordinateur décide)');
    check(/✓ Your vote/.test(res),'après le verrou : « Your vote »');
    check(/Coordinator's call/.test(await texte(p,'#viewMyteam .fo-win'))&&/Coordinator's call/.test(await texte(p,'#viewMyteam .fo-bar.win')),'après le verrou : « Coordinator’s call » retenu (barre mise en avant)');
    check(/opens on Monday/.test(await texte(p,'#viewMyteam .fo-nextc')),'après le verrou : la prochaine question ouvre lundi');
    await capture(p,'4-apres-le-verrou','#viewMyteam');
    check(!(await p.$('#viewMyteam [data-fovote]')),'après le verrou : plus de bouton de vote');
    errs.push(...p.errs);
  }finally{ await arreter(srv); }

  /* ---- interrupteur coupé ---- */
  srv=await server(iso(LOCK-28*3600e3),{GC_FRONT_OFFICE:'off'});
  try{
    const A=(await api('/account/login',{pseudo:'FanCTX',password:'motdepasse1'})).json;
    const p=await ouvrir(b); await connecter(p,{token:A.token,name:A.name,fav:'CTX'}); await myteam(p);
    check(!(await p.$('#viewMyteam [data-mttab]'))&&!!(await p.$('#viewMyteam .team-page')),'GC_FRONT_OFFICE=off : My team comme avant (pas d’onglets)');
    await p.click('.rail-btn[data-view="teams"]'); await p.click('#viewTeams [data-team="CTX"]'); await p.waitForSelector('#viewTeams .team-page',{timeout:10000});
    check(!(await p.$('#viewTeams .fo-line')),'GC_FRONT_OFFICE=off : pas de ligne sur Teams');
    errs.push(...p.errs);
  }finally{ await arreter(srv); await b.close(); }
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
