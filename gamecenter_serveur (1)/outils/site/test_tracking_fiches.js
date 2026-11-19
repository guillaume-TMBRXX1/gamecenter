// Tracking dans les fiches (NGS-5, section 126, 18/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_tracking_fiches.js          (depuis « gamecenter_serveur (1) »)
//   SHOTS=<dossier> node outils/site/test_tracking_fiches.js     (captures)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT), GC_INSIGHTS_USERS=Analyste.
// Vérifie : fiche joueur — la stat phare de son poste pour tous (= l'API), le reste et les rangs pour un compte Pro,
// un cadenas sinon ; page d'une franchise (Teams) — profil de suivi classé pour un compte Pro, cadenas sinon ;
// Insights › Head-to-head — les deux profils côte à côte ; Match centre d'un match terminé — rien avant d'avoir vu la
// fin (pas de spoiler), puis le suivi du match (= l'API) ; téléphone 390 px sans défilement horizontal ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const DEMO=new Date(Date.parse(REG[Math.floor(REG.length*0.7)].kickoff)+60e3).toISOString();
const FINI=REG[3];                                   /* un match du lundi : terminé à l'heure du test */

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-trkf-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:DEMO},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api${u}`,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
const ouvrir=async(b,port,opts,tok,name)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  if(tok) await ctx.addInitScript(([t,n])=>localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:n,account:true})),[tok,name]);
  await p.goto(`http://localhost:${port}/`,{timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p; };
const shot=async(p,nom,el)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.waitForTimeout(900);
  if(el){ const h=await p.$(el); if(h){ await h.screenshot({path:path.join(SHOTS,nom)}); return; } } await p.screenshot({path:path.join(SHOTS,nom)}); } };
const vue=async(p,v)=>{ const b=await p.$(`.rail-btn[data-view="${v}"]`); if(b&&await b.isVisible()) await b.click(); else await p.evaluate(v=>document.querySelector(`.rail-btn[data-view="${v}"]`).click(),v); };
/* la fiche d'un joueur, ouverte comme un clic sur son nom */
const fiche=async(p,team,pid)=>{ await p.evaluate(([t,id])=>window.__gc.trk.openRosterCard(t,id,500,400),[team,pid]);
  await p.waitForFunction(()=>{ const e=document.querySelector('.pcard .pc-trk'); return e&&!/Loading…/.test(e.textContent); },null,{timeout:30000}); };

(async()=>{
  const P1=8173;
  const srv=await server(P1,{GC_INSIGHTS_USERS:'Analyste'}), b=await chromium.launch({executablePath:EXE});
  try{
    const pro=(await api(P1,'/account/register',{pseudo:'Analyste',password:'motdepasse1'})).json;
    const QB=FINI.home+'_QB1', A=FINI.home, B=FINI.away;
    const libre=(await api(P1,'/tracking/player?id='+QB)).json, plein=(await api(P1,`/tracking/player?id=${QB}&token=${pro.token}`)).json;
    const prof=(await api(P1,`/tracking/team?team=${A}&b=${B}&token=${pro.token}`)).json;
    const gm=(await api(P1,`/tracking/game?id=${FINI.id}&token=${pro.token}`)).json;
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO} · ${QB} · match ${FINI.id} (${B} @ ${A})`);
    check(libre.headline&&!('groups' in libre)&&plein.groups.length>0,'API : stat phare pour tous, le détail pour un compte Pro');
    check((await api(P1,`/tracking/team?team=${A}`)).status===403&&(await api(P1,`/tracking/game?id=${FINI.id}`)).status===403,'API : profils d\'équipe et match verrouillés sans compte Pro');

    /* ---- invité ---- */
    const g=await ouvrir(b,P1);
    await fiche(g,A,QB);
    let t=await g.textContent('.pcard .pc-trk');
    check(t.includes(libre.headline.l)&&/Insights Pro/.test(t),`invité : fiche joueur — ${libre.headline.l} visible, le reste sous cadenas`);
    if(!(t.includes(libre.headline.l)&&/Insights Pro/.test(t))) console.log('     texte : '+t.replace(/\s+/g,' ').slice(0,300));
    check(!(await g.$('.pcard .pc-trk .trk-grp')),'invité : aucun groupe de suivi dans la fiche');
    await g.$eval('.pcard .pc-trk',e=>e.scrollIntoView({block:'center'})); await shot(g,'fiche-joueur-invite.png','.pcard');
    await g.keyboard.press('Escape');
    await vue(g,'teams'); await g.click(`[data-team="${A}"]`);
    await g.waitForSelector('.team-page [data-trkx="team"] .fp-lock',{timeout:30000});
    check(true,'invité : page de la franchise — profil de suivi sous cadenas');

    /* ---- compte Pro ---- */
    const q=await ouvrir(b,P1,null,pro.token,'Analyste');
    await fiche(q,A,QB);
    t=await q.textContent('.pcard .pc-trk');
    const nG=await q.$$eval('.pcard .pc-trk .trk-grp',x=>x.length);   /* 19/11 : les titres des cartes (NGS-6) sont aussi des .trk-gl */
    check(t.includes(plein.headline.l)&&nG===plein.groups.length&&!/Insights Pro/.test(t),`Pro : fiche joueur — stat phare et ${nG} groupe(s) classés`);
    check(plein.headline.qualified?/#\d+ of \d+/.test(t):/Not ranked yet/.test(t),'Pro : rang de la stat phare (ou « pas encore classé »)');
    await q.$eval('.pcard .pc-trk',e=>e.scrollIntoView({block:'center'})); await shot(q,'fiche-joueur-pro.png','.pcard');
    await q.keyboard.press('Escape');
    await vue(q,'teams'); await q.click(`[data-team="${A}"]`);
    await q.waitForSelector('.team-page [data-trkx="team"] .trk-tp',{timeout:30000});
    const tiles=await q.$$eval('.team-page [data-trkx="team"] .mt-st',x=>x.map(e=>e.textContent));
    check(tiles.length===prof.teams[0].stats.length&&tiles.every(x=>/#\d+ of 24|—/.test(x)),`Pro : page de la franchise — ${tiles.length} statistiques classées sur 24`);
    await shot(q,'equipe-pro.png','.team-page [data-trkx="team"]');
    /* Insights › Head-to-head */
    await vue(q,'insights');
    await q.waitForSelector('#viewInsights [data-ins-tab="h2h"]'); await q.click('#viewInsights [data-ins-tab="h2h"]');
    await q.waitForSelector('#viewInsights [data-trkx="h2h"] .trk-h2h',{timeout:30000});
    const n2=await q.$$eval('#viewInsights [data-trkx="h2h"] .trk-h2h',x=>x.length);
    check(n2===prof.teams[0].stats.length,`Pro : Head-to-head — ${n2} lignes de suivi côte à côte`);
    await shot(q,'h2h-tracking-pro.png','#viewInsights [data-trkx="h2h"]');
    /* Match centre d'un match terminé : rien avant la fin, puis le suivi */
    await q.evaluate(id=>window.__gc.trk.watchGame(id),FINI.id);
    await q.waitForSelector('.modal [data-st="tracking"]',{timeout:30000});
    await q.evaluate(()=>{ const G=window.__gc, g=G.trk.modalGame(); g.paused=true; G.rpSeek(g,2); G.trk.rpAfterSeek(g); });
    await q.click('.modal [data-st="tracking"]');
    await q.waitForSelector('.modal [data-trkx="game"]');
    t=await q.textContent('.modal [data-trkx="game"]');
    check(/At the final whistle/.test(t),'Match centre : avant la fin du replay, aucun chiffre (pas de spoiler)');
    const fin=await q.evaluate(()=>{ const G=window.__gc, g=G.trk.modalGame(); G.rpSeek(g,g.plays.length-1); g.paused=false;
      for(let i=0;i<20000&&!(g.status==='final'&&G.rpDone(g)>=g.plays.length);i++) G.stepGame(g,0.01);
      G.trk.renderStats(g); return {done:G.rpDone(g),n:g.plays.length}; });
    await q.waitForSelector('.modal [data-trkx="game"] table.tst',{timeout:30000});
    const vals=await q.$$eval('.modal [data-trkx="game"] table.tst tbody tr',rs=>rs.map(r=>r.children[0].textContent));
    check(fin.done===fin.n&&vals.length===gm.cols.length,`Match centre : à la fin, le suivi du match (${vals.length} lignes) et les joueurs marquants`);
    const kp=await q.$$eval('.modal [data-trkx="game"] .pst tbody tr',x=>x.length);
    check(kp===gm.teams.reduce((n,x)=>n+x.players.length,0),`Match centre : ${kp} joueurs marquants (= l'API)`);
    await q.waitForTimeout(1500); await shot(q,'match-centre-tracking-pro.png','.modal [data-f="stats"]');
    check(!q.errs.length&&!g.errs.length,'aucune erreur JS'+(q.errs.concat(g.errs).length?' : '+q.errs.concat(g.errs).join(' | '):''));

    /* ---- téléphone ---- */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,colorScheme:'dark'},pro.token,'Analyste');
    await vue(m,'teams'); await m.click(`[data-team="${A}"]`);
    await m.waitForSelector('.team-page [data-trkx="team"] .trk-tp',{timeout:30000});
    const ov=await m.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    check(ov<=1,`téléphone : page de la franchise sans défilement horizontal (${ov} px)`);
    await shot(m,'equipe-pro-telephone.png','.team-page [data-trkx="team"]');
    await fiche(m,A,QB);
    await m.$eval('.pcard .pc-trk',e=>e.scrollIntoView({block:'center'})); await shot(m,'fiche-joueur-pro-telephone.png','.pcard');
    check(!m.errs.length,'aucune erreur JS (téléphone)'+(m.errs.length?' : '+m.errs.join(' | '):''));
  }catch(e){ console.log('  ✗ exception : '+(e&&e.stack||e)); fail++; }
  finally{ await b.close(); srv.kill(); }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
