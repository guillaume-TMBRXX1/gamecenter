// Empreinte de jeu (section 89, 03/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_empreinte.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT). Vérifie : invité, fiche d'une franchise (Teams) :
// la forme du radar seulement (un polygone, aucune barre ni chiffre, cadenas), et l'API ne lui donne aucun chiffre ; grand
// écran d'un match en direct, invité : aperçu flouté verrouillé ; compte Insights : fiche avec le petit radar et 8 barres
// (passes / courses, moyenne de la ligue), grand écran avec les deux empreintes superposées, Head-to-head avec la carte
// « Play fingerprint » ; téléphone 390 px sans défilement horizontal ; GC_EMPREINTE=off : rien de tout ça, /api/fingerprint
// 404 ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site). GC_CAPTURES=<dossier> : captures.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CAP=process.env.GC_CAPTURES||''; const cap=async(p,n,el)=>{ if(!CAP) return; if(el){ for(let i=0;i<4;i++){ await p.waitForTimeout(300); if(await p.locator(el).first().screenshot({path:path.join(CAP,n+'.png'),timeout:4000}).then(()=>true).catch(()=>false)) break; } } else await p.screenshot({path:path.join(CAP,n+'.png')}); };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const LIVE=REG[Math.floor(REG.length*0.55)], T0=Date.parse(LIVE.kickoff)+60e3;
const EQ='MNL';

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-fp-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(T0).toISOString()},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${port}/api/time`)).ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api${u}`,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
const ouvrir=async(b,port,opts,tok,name,theme)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000},colorScheme:theme||'light'},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  if(tok) await ctx.addInitScript(([t,n])=>localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:n,account:true})),[tok,name]);
  await p.goto(`http://localhost:${port}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000}); return p; };
const fiche=async(p,t)=>{ await p.evaluate(()=>window.__gc.season.setView('teams')); await p.waitForTimeout(300);
  await p.click(`[data-team="${t}"]`).catch(()=>{});
  await p.waitForFunction(()=>{ const e=document.querySelector('[data-fp="team"]'); return e&&e.querySelector('svg.fp-r'); },null,{timeout:20000}).catch(()=>{}); };
const grandEcran=async(p,gid)=>{ await p.evaluate(gid=>{ const x=document.createElement('button'); x.dataset.sched=gid; document.body.appendChild(x); x.click(); x.remove(); },gid);
  await p.waitForFunction(()=>{ const e=document.querySelector('#modal [data-fp="game"]'); return e&&e.querySelector('svg.fp-r'); },null,{timeout:20000}).catch(()=>{}); };

(async()=>{
  const P1=8191, P2=8192; const srv=await server(P1,{GC_INSIGHTS_USERS:'Analyste'}), b=await chromium.launch({executablePath:EXE}), errs=[]; let srv2=null;
  try{
    console.log(`   horloge : ${new Date(T0).toISOString()} · en direct : ${LIVE.away} @ ${LIVE.home}`);
    const pro=(await api(P1,'/account/register',{pseudo:'Analyste',password:'motdepasse1'})).json;
    const ouvert=(await api(P1,'/fingerprint?team='+EQ)).json, complet=(await api(P1,`/fingerprint?team=${EQ}&token=${pro.token}`)).json;
    const x0=ouvert.teams[0];
    check(!ouvert.pro&&!ouvert.league&&Object.keys(x0).sort().join()==='games,shape,team'&&x0.shape&&x0.shape.length===8,`API, invité : la forme seulement (${x0.games} matchs)`);
    check(complet.pro&&complet.league&&complet.teams[0].values&&complet.teams[0].values.power>0,'API, compte Insights : chiffres et ligue');
    check((await api(P1,`/fingerprint?a=${LIVE.away}&b=${LIVE.home}`)).status===403,'API : deux franchises sans compte Insights → 403');

    /* ---- invité ---- */
    const p=await ouvrir(b,P1);
    await fiche(p,EQ);
    const inv=await p.$eval('[data-fp="team"]',e=>({sh:e.querySelectorAll('.sh').length,bars:e.querySelectorAll('.fp-b').length,avg:e.querySelectorAll('.avg').length,txt:e.textContent})).catch(()=>null);
    check(inv&&inv.sh===1&&!inv.bars&&!inv.avg&&!/\d+%/.test(inv.txt)&&/Insights · Pro/.test(inv.txt),`invité, fiche ${EQ} : la forme seulement, cadenas`);
    await cap(p,'1_fiche_invite','[data-fp="team"]');
    await grandEcran(p,LIVE.id);
    const tz=await p.$eval('#modal [data-fp="game"]',e=>({tease:!!e.querySelector('.fp-tease'),txt:e.textContent})).catch(()=>null);
    check(tz&&tz.tease&&/Insights Pro/.test(tz.txt),'invité, grand écran : aperçu flouté verrouillé');
    await cap(p,'2_grand_ecran_invite','#modal .m-side');
    errs.push(...p.errs);

    /* ---- compte Insights ---- */
    const q=await ouvrir(b,P1,null,pro.token,pro.name);
    await fiche(q,EQ);
    await q.waitForFunction(()=>document.querySelectorAll('[data-fp="team"] .fp-b').length===8,null,{timeout:20000}).catch(()=>{});
    const pb=await q.$eval('[data-fp="team"]',e=>({sh:e.querySelectorAll('.sh').length,bars:e.querySelectorAll('.fp-b').length,ticks:e.querySelectorAll('.fp-b u').length,first:e.querySelector('.fp-b em')&&e.querySelector('.fp-b em').textContent})).catch(()=>null);
    const v=complet.teams[0].values.pass;
    check(pb&&pb.sh===1&&pb.bars===8&&pb.ticks===8&&pb.first===`${Math.round(v*100)} / ${Math.round((1-v)*100)}`,`compte Insights, fiche ${EQ} : radar + 8 barres, « ${pb&&pb.first} »`);
    await cap(q,'3_fiche_pro','[data-fp="team"]');
    await grandEcran(q,LIVE.id);
    await q.waitForFunction(()=>document.querySelectorAll('#modal [data-fp="game"] .sh').length===2,null,{timeout:20000}).catch(()=>{});
    const ge=await q.$eval('#modal [data-fp="game"]',e=>({sh:e.querySelectorAll('.sh').length,lg:e.querySelector('.fp-lg')&&e.querySelector('.fp-lg').textContent})).catch(()=>null);
    check(ge&&ge.sh===2&&/pass\/run/.test(ge.lg||''),`compte Insights, grand écran : deux empreintes superposées (« ${ge&&ge.lg} »)`);
    await cap(q,'4_grand_ecran_pro','#modal .m-side');
    await q.evaluate(()=>{ const c=document.querySelector('#modal [data-close]'); if(c) c.click(); });
    await q.evaluate(()=>window.__gc.season.setView('insights'));
    await q.waitForSelector('#viewInsights [data-ins-tab="h2h"]',{timeout:20000}); await q.click('#viewInsights [data-ins-tab="h2h"]');
    await q.waitForFunction(()=>document.querySelectorAll('#viewInsights [data-fp="h2h"] .sh').length===2,null,{timeout:20000}).catch(()=>{});
    const h=await q.$$eval('#viewInsights [data-fp="h2h"] .sh',x=>x.length).catch(()=>0);
    check(h===2,'Head-to-head : carte « Play fingerprint », deux empreintes');
    await cap(q,'5_h2h','#viewInsights [data-fp="h2h"]');
    errs.push(...q.errs);

    /* ---- sombre et téléphone ---- */
    const d=await ouvrir(b,P1,null,pro.token,pro.name,'dark');
    await fiche(d,EQ); await d.waitForTimeout(800);
    await cap(d,'6_fiche_sombre','[data-fp="team"]');
    errs.push(...d.errs);
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true},pro.token,pro.name);
    await fiche(m,EQ); await m.waitForTimeout(800);
    const w=await m.evaluate(()=>document.documentElement.scrollWidth);
    check(w<=390,`téléphone : pas de défilement horizontal (${w} px)`);
    await cap(m,'7_telephone','[data-fp="team"]');
    errs.push(...m.errs);

    /* ---- interrupteur ---- */
    srv2=await server(P2,{GC_EMPREINTE:'off'});
    const off=await ouvrir(b,P2);
    await off.evaluate(()=>window.__gc.season.setView('teams')); await off.waitForTimeout(300); await off.click(`[data-team="${EQ}"]`).catch(()=>{}); await off.waitForTimeout(800);
    await grandEcran(off,LIVE.id);
    const r404=await off.evaluate(async t=>(await fetch('/api/fingerprint?team='+t)).status,EQ);
    check(!(await off.$('[data-fp]'))&&!/Play fingerprint/.test(await off.innerText('body'))&&r404===404,'GC_EMPREINTE=off : rien, /api/fingerprint 404');
    errs.push(...off.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
