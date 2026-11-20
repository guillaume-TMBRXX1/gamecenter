// Tracking, NGS-6 (section 129, 19/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_tracking_ngs6.js          (depuis « gamecenter_serveur (1) »)
//   SHOTS=<dossier> node outils/site/test_tracking_ngs6.js     (captures)
// Horloge du serveur après le dernier match de la dernière semaine (GC_DEMO_AT), GC_INSIGHTS_USERS=Analyste.
// Vérifie : récompenses de la semaine dans Insights › Tracking, pour tous (= l'API, la semaine finie) ; fiche d'un QB
// (compte Pro) — la grille des passes (= l'API, cases de complétion), les couloirs de course d'un porteur, la stat phare
// semaine par semaine (une ligne par semaine de l'API) ; rien de tout cela pour un invité (cadenas) ; téléphone 390 px ;
// aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const KO=W.schedule.map(g=>Date.parse(g.kickoff)).sort((a,b)=>a-b);
const DEMO=new Date(KO[KO.length-1]+3*3600e3).toISOString();   /* la Grand Final jouée : la semaine est finie */

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-ngs6-'));
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
const fiche=async(p,team,pid)=>{ await p.evaluate(([t,id])=>window.__gc.trk.openRosterCard(t,id,500,400),[team,pid]);
  await p.waitForFunction(()=>{ const e=document.querySelector('.pcard .pc-trk'); return e&&!/Loading…/.test(e.textContent); },null,{timeout:60000}); };
const onglet=async(p,tab)=>{ await vue(p,'insights');
  await p.waitForSelector(`#viewInsights [data-ins-tab="${tab}"]`,{timeout:15000}); await p.click(`#viewInsights [data-ins-tab="${tab}"]`);
  await p.waitForFunction(t=>{ const b=document.querySelector(`#viewInsights [data-ins-tab="${t}"]`); return b&&b.getAttribute('aria-selected')==='true'&&!/Loading…/.test(document.getElementById('viewInsights').textContent); },tab,{timeout:60000}); };

(async()=>{
  const P1=8174;
  const srv=await server(P1,{GC_INSIGHTS_USERS:'Analyste'}), b=await chromium.launch({executablePath:EXE});
  try{
    const pro=(await api(P1,'/account/register',{pseudo:'Analyste',password:'motdepasse1'})).json;
    const ouvert=(await api(P1,'/tracking')).json;
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO} : ${ouvert.final} matchs terminés`);
    check(Array.isArray(ouvert.awards)&&ouvert.awards.length===7,`API : les ${ouvert.awards?ouvert.awards.length:0} récompenses de la semaine finie, pour tous`);
    const rbAw=ouvert.awards.find(a=>a.group==='rushing');
    /* un QB titulaire avec au moins deux semaines d'historique (même joueur au même poste du roster) */
    let qbAw=null, QB=null;
    for(const t of Object.keys(W.teams).sort()){ const d=(await api(P1,`/tracking/player?id=${t}_QB1&token=${pro.token}`)).json;
      if(d&&d.history&&d.history.length>=2&&d.charts&&d.charts.pass){ QB=d; qbAw={id:`${t}_QB1`,team:t,name:`${t}_QB1`}; break; } }
    if(!QB){ qbAw=ouvert.awards.find(a=>a.group==='passing'); QB=(await api(P1,`/tracking/player?id=${qbAw.id}&token=${pro.token}`)).json; }
    const RB=(await api(P1,`/tracking/player?id=${rbAw.id}&token=${pro.token}`)).json;
    check(QB.charts&&QB.charts.pass&&QB.league_charts&&QB.history&&QB.history.length>=1,`API Pro : cartes, repères de la ligue, ${QB.history.length} semaine(s) d'historique`);
    const libre=(await api(P1,`/tracking/player?id=${qbAw.id}`)).json;
    check(!('charts' in libre)&&!('history' in libre),'API invité : ni cartes ni historique');

    /* ---- invité : les récompenses, gratuites ---- */
    const g=await ouvrir(b,P1);
    await onglet(g,'tracking');
    const aw=await g.$$eval('#viewInsights .trk-aw .rc-item',x=>x.map(e=>e.textContent));
    check(aw.length===7&&ouvert.awards.every((a,i)=>aw[i].includes(a.name)&&aw[i].includes(a.title)),'invité : les 7 récompenses de la semaine (= l\'API)');
    await shot(g,'recompenses-invite.png','#viewInsights .trk-aw');
    await g.evaluate(([t,id])=>window.__gc.trk.openRosterCard(t,id,500,400),[qbAw.team,qbAw.id]);
    await g.waitForFunction(()=>{ const e=document.querySelector('.pcard .pc-trk'); return e&&!/Loading…/.test(e.textContent); },null,{timeout:60000});
    check(!(await g.$('.pcard .trk-pch'))&&/charts/.test(await g.textContent('.pcard .pc-trk')),'invité : pas de carte dans la fiche, le cadenas les annonce');
    await g.keyboard.press('Escape');

    /* ---- compte Pro : cartes et historique ---- */
    const q=await ouvrir(b,P1,null,pro.token,'Analyste');
    await fiche(q,qbAw.team,qbAw.id);
    const cells=await q.$$eval('.pcard .trk-pch .c:not(.e)',x=>x.length);
    check(cells===QB.charts.pass.length,`Pro : grille des passes de ${qbAw.name} — ${cells} cases remplies (= l'API)`);
    const cell=QB.charts.pass[0], txt=await q.$eval('.pcard .trk-pch',e=>e.textContent);
    check(txt.includes(`${cell[3]}/${cell[2]}`),`Pro : une case dit ses passes complétées / tentées (${cell[3]}/${cell[2]})`);
    const weeks=await q.$$eval('.pcard .pc-trk .pc-line span',x=>x.map(e=>e.textContent).filter(t=>/^Week \d+$/.test(t)));
    check(QB.history.length<2?weeks.length===0:weeks.length===QB.history.length,`Pro : semaine par semaine — ${weeks.join(', ')||'une seule semaine, rien à comparer'}`);
    await q.$eval('.pcard .trk-pch',e=>e.scrollIntoView({block:'center'}));
    await shot(q,'carte-passes-qb.png','.pcard');
    await q.keyboard.press('Escape');
    await fiche(q,rbAw.team,rbAw.id);
    const lanes=await q.$$eval('.pcard .trk-lane',x=>x.length);
    check(lanes===4&&RB.charts.run.length>0,`Pro : couloirs de course de ${rbAw.name} (4 couloirs)`);
    await q.$eval('.pcard .trk-lane',e=>e.scrollIntoView({block:'center'}));
    await shot(q,'couloirs-course-rb.png','.pcard');
    check(!q.errs.length&&!g.errs.length,'aucune erreur JS'+(q.errs.concat(g.errs).length?' : '+q.errs.concat(g.errs).join(' | '):''));

    /* ---- téléphone ---- */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,colorScheme:'dark'},pro.token,'Analyste');
    await onglet(m,'tracking');
    const ov=await m.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    check(ov<=1,`téléphone : Tracking sans défilement horizontal (${ov} px)`);
    await fiche(m,qbAw.team,qbAw.id);
    await m.$eval('.pcard .trk-pch',e=>e.scrollIntoView({block:'center'}));
    await shot(m,'carte-passes-telephone.png','.pcard');
    check(!m.errs.length,'aucune erreur JS (téléphone)'+(m.errs.length?' : '+m.errs.join(' | '):''));
  }catch(e){ console.log('  ✗ exception : '+(e&&e.stack||e)); fail++; }
  finally{ await b.close(); srv.kill(); }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
