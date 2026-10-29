// Onglet Insights (section 78, 28/10/2026) et retrait d'Exhibition — test navigateur (Playwright + serveur réel).
//   node outils/site/test_insights.js          (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT), GC_INSIGHTS_USERS=Analyste.
// Vérifie : plus d'Exhibition (barre latérale, /api/exhibitions) ; sans accès (invité, compte hors liste) : cadenas,
// aperçu flouté avec chiffres factices (l'API ne renvoie ni tableau ni indices), récap du jour ouvert (jours joués
// seulement, surprises = celles de l'API, Replay ouvre le match) ; avec accès : pas de cadenas, tableau des 24 franchises
// (bilans = matchs terminés), indices, face-à-face (deux équipes changées autant de fois qu'on veut, une équipe ne se
// choisit pas contre elle-même, leur match de la semaine) ; téléphone 390 px sans défilement horizontal ; GC_INSIGHTS=off :
// ni bouton ni vue ni API ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const DEMO=new Date(Date.parse(REG[Math.floor(REG.length*0.7)].kickoff)+60e3).toISOString();   /* ≈ jeudi : des matchs finis, d'autres à venir */

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-insights-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks')); fs.symlinkSync(path.join(WEEKS,DERNIERE),path.join(data,'weeks',DERNIERE));
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
  await p.goto(`http://localhost:${port}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); return p; };
const onglet=async(p,tab)=>{ if(!(await p.$('#viewInsights:not([hidden])'))){ await p.click('.rail-btn[data-view="insights"]'); }
  await p.waitForSelector(`#viewInsights [data-ins-tab="${tab}"]`,{timeout:15000}); await p.click(`#viewInsights [data-ins-tab="${tab}"]`);
  await p.waitForFunction(t=>{ const b=document.querySelector(`#viewInsights [data-ins-tab="${t}"]`); return b&&b.getAttribute('aria-selected')==='true'&&!/Loading…/.test(document.getElementById('viewInsights').textContent); },tab,{timeout:15000}); };
const lockVisible=p=>p.$eval('.rail-btn[data-view="insights"] .ins-lkw',e=>!e.hidden&&e.getClientRects().length>0);

(async()=>{
  const P1=8167, P2=8168;
  const srv=await server(P1,{GC_INSIGHTS_USERS:'Analyste'}), b=await chromium.launch({executablePath:EXE}), errs=[];
  let srv2=null;
  try{
    const pro=(await api(P1,'/account/register',{pseudo:'Analyste',password:'motdepasse1'})).json;
    const autre=(await api(P1,'/account/register',{pseudo:'Curieux',password:'motdepasse1'})).json;
    const ouvert=(await api(P1,'/insights')).json, complet=(await api(P1,'/insights?token='+pro.token)).json;
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO} : ${ouvert.final} matchs terminés sur ${ouvert.games}`);
    check((await api(P1,'/exhibitions')).status===404,'Exhibition retirée : /api/exhibitions → 404');

    /* ---- invité ---- */
    const g=await ouvrir(b,P1);
    check(!(await g.$('[data-exh-go]'))&&!/Exhibition/.test(await g.textContent('.rail')),'Exhibition retirée de la barre latérale');
    check(!!(await g.$('.rail-btn[data-view="insights"]')),'bouton Insights dans la barre latérale');
    let reponse=null; g.on('response',async r=>{ if(r.url().includes('/api/insights')) reponse=await r.json().catch(()=>null); });
    await onglet(g,'week');
    check(await lockVisible(g),'invité : cadenas sur le bouton');
    const pay=await g.textContent('#viewInsights .ins-pay');
    check(/€4\.99/.test(pay)&&/coming soon/i.test(pay)&&/Day recap stays free/.test(pay),'invité : aperçu verrouillé (€4.99, bientôt, récap gratuit)');
    check(await g.$eval('#viewInsights .ins-blur',e=>e.hasAttribute('inert')&&e.getAttribute('aria-hidden')==='true'),'aperçu flouté inerte (ni clavier ni lecteur d\'écran)');
    check(!!reponse&&reponse.pro===false&&!('rows' in reponse)&&!('hints' in reponse)&&!('league' in reponse),'invité : l\'API ne renvoie ni tableau, ni indices, ni chiffres de la ligue');
    const factices=await g.$$eval('#viewInsights .ins-blur table.ins tbody tr',rs=>rs.map(r=>r.querySelector('th .badge').textContent.trim()+' '+r.children[3].textContent.trim()+' '+r.children[4].textContent.trim()));
    const vrais=complet.rows.map(r=>`${r.team} ${r.w}-${r.l}${r.t?'-'+r.t:''} ${r.ppg}`);
    check(factices.length===24&&factices.filter(x=>vrais.includes(x)).length<=2,'aperçu : chiffres factices (pas ceux de la semaine)');
    await onglet(g,'h2h');
    check(!!(await g.$('#viewInsights .ins-lock .ins-pay')),'invité : face-à-face verrouillé aussi');
    await onglet(g,'recap');
    check(!(await g.$('#viewInsights .ins-lock')),'invité : récap du jour ouvert');
    const jours=await g.$$eval('#viewInsights [data-ins-day]',bs=>bs.map(b=>b.dataset.insDay));
    check(JSON.stringify(jours)===JSON.stringify(Object.keys(ouvert.recaps)),`récap : les jours joués seulement (${jours.length})`);
    const dernier=ouvert.recaps[jours[jours.length-1]];
    const kpi=await g.$$eval('#viewInsights .ins-kpi .mt-st b',bs=>bs.map(b=>b.textContent.trim()));
    check(kpi[0]===String(dernier.games)&&kpi[2]===String(dernier.n_upsets),`récap : ${kpi[0]} matchs, ${kpi[2]} surprises (API : ${dernier.games}, ${dernier.n_upsets})`);
    if(jours.length>1){ await g.click(`#viewInsights [data-ins-day="${jours[0]}"]`);
      await g.waitForFunction(d=>document.querySelector(`#viewInsights [data-ins-day="${d}"]`).getAttribute('aria-selected')==='true',jours[0]);
      const k0=await g.$eval('#viewInsights .ins-kpi .mt-st b',b=>b.textContent.trim());
      check(k0===String(ouvert.recaps[jours[0]].games),'récap : changement de jour'); }
    await g.click('#viewInsights [data-sched]');
    await g.waitForFunction(()=>{ const m=document.getElementById('modal'); return m&&!m.hidden; },null,{timeout:20000}).then(()=>check(true,'récap : Replay ouvre le match'),()=>check(false,'récap : Replay ouvre le match'));
    errs.push(...g.errs);

    /* ---- compte hors liste ---- */
    const c=await ouvrir(b,P1,null,autre.token,autre.name);
    await onglet(c,'week');
    check(!!(await c.$('#viewInsights .ins-lock'))&&await lockVisible(c),'compte hors de GC_INSIGHTS_USERS : verrouillé');
    errs.push(...c.errs);

    /* ---- compte avec accès ---- */
    const p=await ouvrir(b,P1,null,pro.token,pro.name);
    await onglet(p,'week');
    check(!(await p.$('#viewInsights .ins-lock'))&&!(await lockVisible(p)),'Analyste : tout ouvert, pas de cadenas');
    const lignes=await p.$$eval('#viewInsights table.ins tbody tr',rs=>rs.map(r=>({t:r.querySelector('th .badge').textContent.trim(),wl:r.children[3].textContent.trim()})));
    check(lignes.length===24,`tableau : ${lignes.length} franchises`);
    const ok=lignes.every((l,i)=>l.t===complet.rows[i].team&&l.wl.startsWith(`${complet.rows[i].w}-${complet.rows[i].l}`));
    const gp=complet.rows.reduce((s,r)=>s+r.gp,0);
    check(ok&&gp===2*complet.final,`tableau = API, ${gp/2} matchs comptés = ${complet.final} terminés`);
    const ind=await p.$$eval('#viewInsights .ins-angles .ins-hint',h=>h.length);
    check(ind===complet.hints.length&&ind<=6,`indices : ${ind}`);
    await onglet(p,'h2h');
    const equipes=complet.rows.map(r=>r.team).sort();
    let changes=0;
    for(const [k,t] of [['a',equipes[3]],['b',equipes[10]],['a',equipes[0]],['b',equipes[23]],['a',equipes[7]],['b',equipes[1]]]){
      await p.click(`#viewInsights [data-h2h="${k}"][data-t="${t}"]`);
      await p.waitForFunction(([k,t])=>document.querySelector(`#viewInsights [data-h2h="${k}"][data-t="${t}"]`).getAttribute('aria-pressed')==='true',[k,t]);
      const tetes=await p.$$eval('#viewInsights .h2h-head .badge',bs=>bs.map(b=>b.textContent.trim()));
      if(tetes[k==='a'?0:1]===t) changes++; }
    check(changes===6,`face-à-face : 6 changements d'équipe pris en compte (${changes})`);
    const [A,B]=await p.$$eval('#viewInsights .h2h-head .badge',bs=>bs.map(b=>b.textContent.trim()));
    check(await p.$eval(`#viewInsights [data-h2h="b"][data-t="${A}"]`,b=>b.disabled),'une équipe ne se choisit pas contre elle-même');
    check((await p.$$('#viewInsights .h2h-row')).length===14,'face-à-face : 14 lignes côte à côte');
    const rencontre=W.schedule.some(g=>g.phase==='regular'&&((g.home===A&&g.away===B)||(g.home===B&&g.away===A)));
    const meet=await p.$$('#viewInsights .h2h-meet');
    check(rencontre?meet.length>=1:/don't meet/.test(await p.textContent('#viewInsights')),`leur match de la semaine (${A}-${B} : ${rencontre?'oui':'non'})`);
    errs.push(...p.errs);

    /* ---- téléphone ---- */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true},pro.token,pro.name);
    await m.evaluate(()=>window.__gc.season.setView('insights'));
    for(const tab of ['week','h2h','recap']){ await m.click(`#viewInsights [data-ins-tab="${tab}"]`); await m.waitForTimeout(300);
      const w=await m.evaluate(()=>document.documentElement.scrollWidth);
      check(w<=390,`téléphone, ${tab} : pas de défilement horizontal (${w} px)`); }
    errs.push(...m.errs);

    /* ---- interrupteur ---- */
    srv2=await server(P2,{GC_INSIGHTS:'off'});
    const o=await ouvrir(b,P2);
    check(!(await o.$('.rail-btn[data-view="insights"]'))&&!(await o.$('#viewInsights')),'GC_INSIGHTS=off : ni bouton ni vue');
    check((await api(P2,'/insights')).status===404,'GC_INSIGHTS=off : /api/insights → 404');
    errs.push(...o.errs);

    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
