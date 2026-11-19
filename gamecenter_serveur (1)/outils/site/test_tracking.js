// Insights › Tracking (section 125, 18/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_tracking.js          (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
//   SHOTS=<dossier> node outils/site/test_tracking.js     (captures : ordinateur, téléphone, mode sombre)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT), GC_INSIGHTS_USERS=Analyste.
// Vérifie : onglet Tracking dans Insights ; sans accès (invité, compte hors liste) : stat du jour (gratuite, la même que
// pour un compte Pro), aperçu flouté inerte avec chiffres factices, l'API n'envoie aucun groupe ; avec accès : huit
// groupes, tableau = API (qualifiés, tri par défaut, moyenne de la ligue), tri par colonne (et retour), « Show all »,
// fiche joueur au clic, définitions ; Day recap : la stat du jour en tête ; téléphone 390 px sans défilement horizontal
// de la page ; GC_TRACKING=off : ni onglet ni API ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const DEMO=new Date(Date.parse(REG[Math.floor(REG.length*0.7)].kickoff)+60e3).toISOString();   /* ≈ jeudi */

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-tracking-'));
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
const rail=async p=>{ if(await p.$('#viewInsights:not([hidden])')) return;
  const b=await p.$('.rail-btn[data-view="insights"]');
  if(b&&await b.isVisible()) await b.click();
  else await p.evaluate(()=>document.querySelector('.rail-btn[data-view="insights"]').click()); };
const onglet=async(p,tab)=>{ await rail(p);
  await p.waitForSelector(`#viewInsights [data-ins-tab="${tab}"]`,{timeout:15000}); await p.click(`#viewInsights [data-ins-tab="${tab}"]`);
  await p.waitForFunction(t=>{ const b=document.querySelector(`#viewInsights [data-ins-tab="${t}"]`); return b&&b.getAttribute('aria-selected')==='true'&&!/Loading…/.test(document.getElementById('viewInsights').textContent); },tab,{timeout:30000}); };
const shot=async(p,nom,full)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.waitForTimeout(900); await p.screenshot({path:path.join(SHOTS,nom),fullPage:!!full}); } };
const colonne=(p,i)=>p.$$eval('#viewInsights table.trk tbody tr',(rs,i)=>rs.map(r=>r.children[i].textContent.trim()),i);

(async()=>{
  const P1=8171, P2=8172;
  const srv=await server(P1,{GC_INSIGHTS_USERS:'Analyste'}), b=await chromium.launch({executablePath:EXE});
  let srv2=null;
  try{
    const pro=(await api(P1,'/account/register',{pseudo:'Analyste',password:'motdepasse1'})).json;
    const autre=(await api(P1,'/account/register',{pseudo:'Curieux',password:'motdepasse1'})).json;
    const ouvert=(await api(P1,'/tracking')).json, complet=(await api(P1,'/tracking?token='+pro.token)).json;
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO} : ${ouvert.final} matchs terminés`);
    check(ouvert.pro===false&&!('groups' in ouvert)&&ouvert.today&&ouvert.today.name,'API invité : la stat du jour seulement, aucun groupe');
    check(complet.pro===true&&complet.groups.length===8&&JSON.stringify(complet.today)===JSON.stringify(ouvert.today),'API Pro : huit groupes, la même stat du jour');
    const c2=(await api(P1,'/tracking?token='+autre.token)).json;
    check(c2.pro===false&&!('groups' in c2),'API compte hors liste : verrouillée');

    /* ---- invité ---- */
    const g=await ouvrir(b,P1);
    await onglet(g,'tracking');
    const today=await g.textContent('#viewInsights .trk-today');
    check(today.includes(ouvert.today.name)&&today.includes(ouvert.today.title)&&/free/i.test(today),`invité : stat du jour gratuite (${ouvert.today.title} · ${ouvert.today.name})`);
    const pay=await g.textContent('#viewInsights .ins-pay');
    check(/Tracking · Pro/.test(pay)&&/€4\.99/.test(pay)&&/stat of the day stays free/.test(pay),'invité : aperçu verrouillé (€4.99, stat du jour gratuite)');
    check(await g.$eval('#viewInsights .ins-blur',e=>e.hasAttribute('inert')&&e.getAttribute('aria-hidden')==='true'),'aperçu flouté inerte');
    const factices=await g.$$eval('#viewInsights .ins-blur table.trk tbody th',ts=>ts.map(t=>t.textContent));
    check(factices.length>0&&factices.every(t=>/Sample Player/.test(t)),'aperçu : joueurs factices, aucun vrai nom');
    await shot(g,'tracking-invite-ordinateur.png');
    await g.click('#viewInsights [data-ins-pl]');
    check(await g.waitForSelector('.pcard',{timeout:5000}).then(()=>true).catch(()=>false),'stat du jour : le nom ouvre la fiche du joueur');
    await g.keyboard.press('Escape');
    await onglet(g,'recap');
    check((await g.textContent('#viewInsights')).includes(ouvert.today.title),'Day recap : la stat du jour en tête');
    await shot(g,'tracking-recap-stat-du-jour.png');

    /* ---- compte Pro ---- */
    const q=await ouvrir(b,P1,null,pro.token,'Analyste');
    await onglet(q,'tracking');
    const grp=await q.$$eval('#viewInsights [data-trk-g]',bs=>bs.map(b=>b.textContent.trim()));
    check(grp.join(',')==='Passing,Receiving,Rushing,Pass rush,Coverage,Tackling,Blocking,Teams',`Pro : huit groupes (${grp.join(', ')})`);
    check(!(await q.$('#viewInsights .ins-lock')),'Pro : pas de cadenas');
    const G0=complet.groups[0];
    const noms=await q.$$eval('#viewInsights table.trk tbody th',ts=>ts.map(t=>t.querySelector('span:nth-of-type(2)').textContent));
    check(noms.length===Math.min(25,G0.rows.length)&&noms[0]===G0.rows[0].name,`Passing : ${noms.length} QB, en tête ${noms[0]} (API : ${G0.rows[0].name}, tri ${G0.sort})`);
    const foot=await q.$eval('#viewInsights table.trk tfoot',t=>t.textContent);
    check(/League average/.test(foot),'moyenne de la ligue en pied de tableau');
    check((await q.$$('#viewInsights .trk-help div')).length===G0.cols.length,'une définition par statistique');
    await shot(q,'tracking-pro-passing-ordinateur.png');
    /* tri par une colonne (temps de lancer, colonne 3), puis l'inverse */
    await q.click('#viewInsights [data-trk-s="tt"]');
    let tt=(await colonne(q,2)).map(Number);
    check(tt.every((v,i)=>!i||tt[i-1]>=v),'tri : temps de lancer décroissant');
    await q.click('#viewInsights [data-trk-s="tt"]');
    tt=(await colonne(q,2)).map(Number);
    check(tt.every((v,i)=>!i||tt[i-1]<=v)&&await q.$eval('#viewInsights th[aria-sort]',t=>t.getAttribute('aria-sort'))==='ascending','tri : et croissant au 2e clic (aria-sort)');
    /* receveurs : plus de 25 qualifiés -> Show all */
    await q.click('#viewInsights [data-trk-g="receiving"]');
    await q.waitForFunction(()=>/Receiving/.test(document.querySelector('#viewInsights .card-h h2').textContent));
    const R=complet.groups.find(x=>x.key==='receiving');
    let n=(await q.$$('#viewInsights table.trk tbody tr')).length;
    check(n===Math.min(25,R.rows.length),`Receiving : ${n} lignes d'abord (${R.rows.length} qualifiés)`);
    await shot(q,'tracking-pro-receiving-ordinateur.png');
    if(R.rows.length>25){ await q.click('#viewInsights [data-trk-all]');
      n=(await q.$$('#viewInsights table.trk tbody tr')).length; check(n===R.rows.length,`Show all : ${n} lignes`); }
    await q.click('#viewInsights table.trk .trk-pl');
    check(await q.waitForSelector('.pcard',{timeout:5000}).then(()=>true).catch(()=>false),'un nom ouvre la fiche du joueur');
    await q.keyboard.press('Escape');
    for(const k of ['rushing','passrush','teams']){
      await q.click(`#viewInsights [data-trk-g="${k}"]`);
      const G=complet.groups.find(x=>x.key===k);
      await q.waitForFunction(l=>document.querySelector('#viewInsights .card-h h2').textContent===l,G.label);
      const m=(await q.$$('#viewInsights table.trk tbody tr')).length;
      check(m===Math.min(25,G.rows.length),`${G.label} : ${m} lignes`);
      if(k==='rushing'||k==='teams') await shot(q,`tracking-pro-${k}-ordinateur.png`);
    }
    check(!q.errs.length&&!g.errs.length,'aucune erreur JS (ordinateur)'+(q.errs.concat(g.errs).length?' : '+q.errs.concat(g.errs).join(' | '):''));

    /* ---- téléphone 390 px, mode sombre ---- */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,colorScheme:'dark'},pro.token,'Analyste');
    await onglet(m,'tracking');
    await m.click('#viewInsights [data-trk-g="passing"]');
    const ov=await m.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    check(ov<=1,`téléphone : pas de défilement horizontal de la page (${ov} px)`);
    const sticky=await m.$eval('#viewInsights table.trk tbody th',t=>getComputedStyle(t).position);
    check(sticky==='sticky','téléphone : la colonne des noms reste visible quand le tableau défile');
    await shot(m,'tracking-pro-telephone-sombre.png');
    const mg=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true});
    await onglet(mg,'tracking');
    const ov2=await mg.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    check(ov2<=1,`téléphone, invité : pas de défilement horizontal (${ov2} px)`);
    await shot(mg,'tracking-invite-telephone.png');
    check(!m.errs.length&&!mg.errs.length,'aucune erreur JS (téléphone)'+(m.errs.concat(mg.errs).length?' : '+m.errs.concat(mg.errs).join(' | '):''));

    /* ---- interrupteur ---- */
    srv2=await server(P2,{GC_TRACKING:'off',GC_INSIGHTS_USERS:'Analyste'});
    check((await api(P2,'/tracking')).status===404,'GC_TRACKING=off : /api/tracking → 404');
    const o=await ouvrir(b,P2);
    await rail(o); await o.waitForSelector('#viewInsights [data-ins-tab="week"]',{timeout:15000});
    check(!(await o.$('#viewInsights [data-ins-tab="tracking"]')),'GC_TRACKING=off : pas d\'onglet Tracking');
    check(!o.errs.length,'aucune erreur JS (interrupteur)');
  }catch(e){ console.log('  ✗ exception : '+(e&&e.stack||e)); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
