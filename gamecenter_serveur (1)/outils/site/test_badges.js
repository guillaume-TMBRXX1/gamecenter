// Badges sur le site (BD-3, programme/Badges_plan.md, README section 134) — test navigateur (Playwright + serveur).
//   node outils/site/test_badges.js          (depuis « gamecenter_serveur (1) »)
//   SHOTS=<dossier> node outils/site/test_badges.js     (captures)
// Vérifie : un compte qui ouvre la page reçoit un seul toast pour ses badges déjà mérités (rétroactifs) ; le bouton
// « Badges » de la rail et sa vue (compteur, cartes gagnées en couleur, à gagner en pointillés avec la progression) ;
// choix du badge mis en avant (API, toast), puis puce à côté du pseudo dans le classement (semaine et saison), la ligue
// et un message du chat ; « None » le retire ; invité : progression et « Create an account to keep them » qui ouvre la
// fenêtre « Join Snapline », sans choix ; téléphone 390 px (pas de défilement horizontal, bouton dans « More ») ;
// mode sombre ; GC_BADGES=off : ni bouton ni puce ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const DEMO=new Date(Date.parse(REG[Math.floor(REG.length*0.5)].kickoff)-5*60e3).toISOString();

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-badges-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:DEMO,GC_CHAT:'on'},env||{}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api${u}`,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
const ouvrir=async(b,port,opts,init)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  if(init) await ctx.addInitScript(init[0],init[1]);
  await p.goto(`http://localhost:${port}/`,{timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p; };
const shot=async(p,nom,el)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.waitForTimeout(700);
  if(el){ const h=await p.$(el); if(h){ await h.screenshot({path:path.join(SHOTS,nom)}); return; } } await p.screenshot({path:path.join(SHOTS,nom),fullPage:false}); } };
const vue=async(p,v)=>{ const b=await p.$(`.rail-btn[data-view="${v}"]`); if(b&&await b.isVisible()) await b.click(); else await p.evaluate(v=>document.querySelector(`.rail-btn[data-view="${v}"]`).click(),v); };
const joueur=(t,n,acct)=>[([t,n,a])=>localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:n,account:a})),[t,n,acct]];
async function parier(port,tok){
  const g=REG[Math.floor(REG.length*0.5)], key=`${g.id}:ml:home`;
  let bet=(await api(port,'/bets',{token:tok,picks:[{key,price_dec:2.0,line:null,stake:10,title:'x'}],combos:[]})).json;
  const q=bet&&bet.rejected&&bet.rejected[0];
  if(q&&q.reason==='price') bet=(await api(port,'/bets',{token:tok,picks:[{key,price_dec:q.price_dec,line:q.line,stake:10,title:'x'}],combos:[]})).json;
  return bet&&bet.accepted&&bet.accepted.length===1;
}

(async()=>{
  const P1=8185, P2=8186;
  const srv=await server(P1), b=await chromium.launch({executablePath:EXE});
  try{
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO}`);
    const acc=(await api(P1,'/account/register',{pseudo:'Badge Fan',password:'motdepasse1'})).json;
    check(acc&&acc.token,'un compte créé (avant 2027 : Founding fan dû)');
    check(await parier(P1,acc.token),'le compte a parié (classements de la semaine et de la saison)');

    /* 1. compte : un seul toast pour les badges déjà mérités */
    const p=await ouvrir(b,P1,null,joueur(acc.token,'Badge Fan',true));
    await p.waitForFunction(()=>{ const t=document.getElementById('toast'); return t&&!t.hidden&&/already have \d+ badge/.test(t.textContent); },null,{timeout:15000}).catch(()=>{});
    check(/You already have \d+ badge/.test(await p.textContent('#toast')),'compte : un toast « You already have N badges » (rétroactifs, pas un par un)');
    check(await p.$('.rail-btn[data-view="badges"]')!==null,'le bouton « Badges » est dans la rail');

    /* 2. la vue */
    await vue(p,'badges');
    await p.waitForSelector('#viewBadges .bd-card',{timeout:15000});
    const n=await p.$$eval('#viewBadges .bd-card',l=>l.length), on=await p.$$eval('#viewBadges .bd-card:not(.off)',l=>l.length);
    check(n===20&&on>=1,`la vue montre les 20 badges, ${on} gagné(s) en couleur`);
    check(/of 20 earned/.test(await p.textContent('#viewBadges .bd-sum')),'compteur « N of 20 earned »');
    check(await p.$('#viewBadges .bd-card.off .bd-bar')!==null,'un badge à gagner montre sa barre de progression');
    check(await p.$$eval('#viewBadges .bd-feat [role="radio"]',l=>l.length)>=2,'choix du badge mis en avant (None + badges gagnés)');
    await shot(p,'badges-vue.png');

    /* 3. mis en avant */
    await p.click('#viewBadges [data-bd-feat="founding_fan"]');
    await p.waitForFunction(()=>/shown next to your name/.test(document.getElementById('toast').textContent),null,{timeout:8000}).catch(()=>{});
    check(/Founding fan · shown next to your name/.test(await p.textContent('#toast')),'toast « Founding fan · shown next to your name »');
    check((await api(P1,'/badges?token='+encodeURIComponent(acc.token))).json.featured==='founding_fan','enregistré (API : featured)');
    check(await p.$eval('#viewBadges [data-bd-feat="founding_fan"]',e=>e.getAttribute('aria-checked'))==='true','le bouton choisi est coché');

    /* 4. classement (semaine puis saison) */
    await vue(p,'bets');
    await p.waitForSelector('#lbBox .lb-me .bd-chip',{timeout:15000}).catch(()=>{});
    check(await p.$('#lbBox .lb-me .bd-chip')!==null,'classement de la semaine : la puce à côté de son pseudo');
    check(/Founding fan/.test(await p.$eval('#lbBox .lb-me .bd-chip',e=>e.getAttribute('aria-label')).catch(()=>'')),'la puce dit « Badge: Founding fan »');
    await p.click('[data-lbscope="season"]');
    await p.waitForSelector('#lbBox .lb-me .bd-chip',{timeout:15000}).catch(()=>{});
    check(await p.$('#lbBox .lb-me .bd-chip')!==null,'classement de la saison : la puce');
    await shot(p,'badges-classement.png','#lbBox');

    /* 5. ligue */
    const lg=(await api(P1,'/leagues/create',{token:acc.token,name:'Badge League'})).json;
    check(lg&&lg.league,'une ligue créée');
    const st=(await api(P1,`/leagues/${lg.league.id}/standings?token=${encodeURIComponent(acc.token)}`)).json;
    check(st&&st.rows.some(r=>r.badge&&r.badge.k==='founding_fan'),'ligue : le badge dans la ligne du membre (API)');
    await vue(p,'leagues');
    await p.waitForSelector('#viewLeagues .bd-chip',{timeout:15000}).catch(()=>{});
    if(!await p.$('#viewLeagues .bd-chip')){ const o=await p.$(`#viewLeagues [data-lg-open="${lg.league.id}"], #viewLeagues [data-lg="open"]`); if(o){ await o.click(); await p.waitForSelector('#viewLeagues .bd-chip',{timeout:10000}).catch(()=>{}); } }
    check(await p.$('#viewLeagues .bd-chip')!==null,'ligue : la puce à côté du pseudo');

    /* 6. chat : la puce dans un message (bd du serveur) */
    const html=await p.evaluate(()=>window.__gc.bd.chatNode({id:1,a:'x',n:'Badge Fan',b:'Hello',ts:Date.now(),bd:{k:'season_ticket',t:3}}).outerHTML);
    check(/bd-chip bd-t3/.test(html)&&/Season ticket · Gold/.test(html),'chat : « Season ticket · Gold » à côté du pseudo');
    check(!/bd-chip/.test(await p.evaluate(()=>window.__gc.bd.chatNode({id:2,a:'y',n:'X',b:'Hi',ts:Date.now(),bd:{k:'inconnu',t:1}}).outerHTML)),'chat : un badge inconnu ne montre rien');

    /* 7. None : retiré */
    await vue(p,'badges');
    await p.click('#viewBadges [data-bd-feat="none"]');
    await p.waitForFunction(()=>/No badge next to your name/.test(document.getElementById('toast').textContent),null,{timeout:8000}).catch(()=>{});
    check((await api(P1,'/badges?token='+encodeURIComponent(acc.token))).json.featured===null,'« None » retire le badge mis en avant');
    check(p.errs.length===0,'compte : aucune erreur JS'+(p.errs.length?' · '+p.errs.join(' | '):''));

    /* 8. mode sombre */
    await p.click('#viewBadges [data-bd-feat="founding_fan"]');
    const pd=await ouvrir(b,P1,{colorScheme:'dark'},joueur(acc.token,'Badge Fan',true));
    await vue(pd,'badges'); await pd.waitForSelector('#viewBadges .bd-card',{timeout:15000});
    check(await pd.evaluate(()=>document.documentElement.getAttribute('data-theme'))==='dark','mode sombre');
    await shot(pd,'badges-sombre.png');

    /* 9. invité */
    const inv=(await api(P1,'/players',{name:'Badge Guest'})).json;
    const pg=await ouvrir(b,P1,null,joueur(inv.token,'Badge Guest',false));
    await vue(pg,'badges'); await pg.waitForSelector('#viewBadges .bd-card',{timeout:15000});
    check(/Create an account to keep them/.test(await pg.textContent('#viewBadges')),'invité : « Create an account to keep them »');
    check(await pg.$$eval('#viewBadges .bd-card:not(.off)',l=>l.length)===0,'invité : aucun badge gagné');
    check(await pg.$('#viewBadges .bd-feat')===null,'invité : pas de choix du badge mis en avant');
    await shot(pg,'badges-invite.png');
    await pg.click('#viewBadges [data-join]');
    await pg.waitForFunction(()=>{ const j=document.getElementById('join'); return j&&!j.hidden; },null,{timeout:8000}).catch(()=>{});
    check(await pg.$eval('#join',e=>!e.hidden).catch(()=>false),'invité : le bouton ouvre la fenêtre « Join Snapline »');
    check(pg.errs.length===0,'invité : aucune erreur JS'+(pg.errs.length?' · '+pg.errs.join(' | '):''));

    /* 10. téléphone 390 px */
    const pp=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true},joueur(acc.token,'Badge Fan',true));
    await pp.click('#tabMore'); await pp.waitForTimeout(400);
    check(await pp.$('#moreGrid [data-more-view="badges"]')!==null,'téléphone : « Badges » dans « More »');
    await pp.click('#moreGrid [data-more-view="badges"]').catch(()=>vue(pp,'badges'));
    await pp.waitForSelector('#viewBadges .bd-card',{timeout:15000});
    check(await pp.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'téléphone : pas de défilement horizontal');
    await shot(pp,'badges-telephone.png');
    check(pp.errs.length===0,'téléphone : aucune erreur JS'+(pp.errs.length?' · '+pp.errs.join(' | '):''));
  } finally { await b.close().catch(()=>{}); srv.kill(); }

  /* 11. GC_BADGES=off */
  const srv2=await server(P2,{GC_BADGES:'off'}), b2=await chromium.launch({executablePath:EXE});
  try{
    const acc=(await api(P2,'/account/register',{pseudo:'Badge Off',password:'motdepasse1'})).json;
    const p=await ouvrir(b2,P2,null,joueur(acc.token,'Badge Off',true));
    await p.waitForTimeout(3500);
    check(await p.$('.rail-btn[data-view="badges"]')===null,'GC_BADGES=off : pas de bouton « Badges »');
    check(await p.evaluate(()=>window.__gc.bd.bdChip({k:'founding_fan',t:1}))==='','GC_BADGES=off : aucune puce');
    check(!/badge/i.test(await p.textContent('#toast').catch(()=>'')),'GC_BADGES=off : aucun toast de badge');
    check(p.errs.length===0,'GC_BADGES=off : aucune erreur JS'+(p.errs.length?' · '+p.errs.join(' | '):''));
  } finally { await b2.close().catch(()=>{}); srv2.kill(); }
  console.log(fail?`\n${fail} échec(s)`:'\nOK');
  process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
