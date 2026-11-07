// Rivalités, bilans des confrontations et mémoire (section 88, 02/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_rivalites.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur 1 min après le coup d'envoi d'un match de rivalité de la dernière semaine (GC_DEMO_AT). Vérifie :
// marqueur « Rivalry » dans le Schedule et sur la tuile du match en direct (nom du trophée) ; le panneau d'un match de
// rivalité à venir : trophée, détenteur, bilan, derniers résultats ; un match ordinaire : bilan sans trophée ; le grand
// écran : « Before kickoff » avec le trophée ; le commentateur à la fin d'un match de rivalité (« keep » / « take ») ; la
// fiche d'une franchise (Teams) : son rival ; téléphone 390 px sans défilement horizontal ; GC_RIVALITES=off : rien de
// tout ça et /api/rivalry répond 404 ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CAP=process.env.GC_CAPTURES||''; const cap=async(p,n,el)=>{ if(!CAP) return; if(el){ for(let i=0;i<4;i++){ await p.waitForTimeout(300); if(await p.locator(el).first().screenshot({path:path.join(CAP,n+'.png'),timeout:4000}).then(()=>true).catch(()=>false)) break; } } else await p.screenshot({path:path.join(CAP,n+'.png')}); };

const RIV=[['MNL','ZPH'],['AXM','ONX'],['MRG','CTD'],['VEC','APX'],['GRZ','LTC'],['CPH','MRD'],['CTX','PRM'],['FRG','BST'],['PLS','CMT'],['AEG','GLT'],['NVA','SPK'],['GMB','TDL']];
const isRiv=g=>RIV.some(([a,b])=>(g.home===a&&g.away===b)||(g.home===b&&g.away===a));
const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const RG=REG.filter(isRiv), LIVE=RG[Math.floor(RG.length/3)], T0=Date.parse(LIVE.kickoff)+60e3;
const UP=RG.find(g=>Date.parse(g.kickoff)>T0+3600e3), ORD=REG.find(g=>!isRiv(g)&&Date.parse(g.kickoff)>T0+3600e3);
const FIN=RG.filter(g=>Date.parse(g.kickoff)<T0-40*60e3).pop();

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-riv-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(T0).toISOString()},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${port}/api/time`)).ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const ouvrir=async(b,port,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p; };   /* like the other tests: the page, not every resource (slow runner) */
const sched=async(p,f)=>{ await p.evaluate(()=>window.__gc.season.setView('schedule')); await p.waitForSelector('#viewSchedule .sch'); await p.click(`[data-schf="${f}"]`); await p.waitForTimeout(250); };

(async()=>{
  const P1=8181, P2=8182; const srv=await server(P1,{}), b=await chromium.launch({executablePath:EXE}), errs=[]; let srv2=null;
  try{
    console.log(`   en direct : ${LIVE.away} @ ${LIVE.home} · à venir : ${UP.away} @ ${UP.home} · ordinaire : ${ORD.away} @ ${ORD.home}`);
    const p=await ouvrir(b,P1);
    await p.waitForSelector(`#liveGrid .tile[data-gid="s-${LIVE.id}"]`);
    const tuile=await p.$eval(`#liveGrid .tile[data-gid="s-${LIVE.id}"]`,x=>x.textContent.replace(/\s+/g,' '));
    check(/Rivalry|The |Lightspeed|Starfall/.test(tuile)&&/(Rivalry)|(Trophy|Talon|Fang|Den|Riddle|Masks|Anvil|Lightspeed|Firewall|Starfall|Wager|Cup)/.test(tuile),'tuile du match de rivalité en direct : marqueur (trophée ou « Rivalry »)');
    await cap(p,'1_tableau');
    await sched(p,'upcoming');
    const pill=await p.$eval(`[data-schbet="${UP.id}"]`,x=>/Rivalry/.test(x.textContent)).catch(()=>false);
    const pill0=await p.$eval(`[data-schbet="${ORD.id}"]`,x=>/Rivalry/.test(x.textContent)).catch(()=>true);
    check(pill&&!pill0,'Schedule : « Rivalry » sur la rivalité, rien sur un match ordinaire');
    await p.click(`[data-schteam="${UP.home}"]`); await p.waitForTimeout(250);   /* the filter opens every day of the team */
    await p.click(`[data-schbet="${UP.id}"]`); await p.waitForFunction(id=>{ const e=document.querySelector(`[data-riv="${id}"]`); return e&&/Series|First meeting|leads|tied/.test(e.textContent); },UP.id,{timeout:15000});
    const box=await p.$eval(`[data-riv="${UP.id}"]`,x=>x.textContent.replace(/\s+/g,' ').trim());
    check(/Rivalry/.test(box)&&/(held by|never won)/.test(box)&&/(leads|tied|First meeting)/.test(box),`panneau de la rivalité à venir : « ${box.slice(0,110)} »`);
    await cap(p,'2_schedule_rivalite',`.sch-game[data-g="${UP.id}"]`);
    await p.click(`[data-schteam="${ORD.home}"]`); await p.waitForTimeout(250);
    await p.click(`[data-schbet="${ORD.id}"]`); await p.waitForFunction(id=>{ const e=document.querySelector(`[data-riv="${id}"]`); return e&&e.textContent.trim().length>3; },ORD.id,{timeout:15000});
    const box0=await p.$eval(`[data-riv="${ORD.id}"]`,x=>x.textContent.replace(/\s+/g,' ').trim());
    check(!/Rivalry/.test(box0)&&/(leads|tied|First meeting)/.test(box0),`match ordinaire : bilan sans trophée (« ${box0.slice(0,80)} »)`);
    // grand écran du match en direct
    await p.evaluate(gid=>{ const x=document.createElement('button'); x.dataset.sched=gid; document.body.appendChild(x); x.click(); x.remove(); },LIVE.id);
    await p.waitForFunction(id=>{ const e=document.querySelector(`#modal [data-riv="${id}"]`); return e&&/(leads|tied|First meeting)/.test(e.textContent); },LIVE.id,{timeout:15000});
    const big=await p.$eval(`#modal [data-riv="${LIVE.id}"]`,x=>x.closest('.panel').textContent.replace(/\s+/g,' ').trim());
    check(/Before kickoff/.test(big)&&/Rivalry/.test(big),`grand écran : « ${big.slice(0,100)} »`);
    await cap(p,'3_grand_ecran','#modal .m-side');
    await p.evaluate(()=>{ const c=document.querySelector('#modal [data-close]'); if(c) c.click(); });
    // le commentateur, fin d'un match de rivalité déjà joué
    /* its replay on the big screen loads its pre-game series (the trophy holder before that game) */
    await p.evaluate(gid=>{ const x=document.createElement('button'); x.dataset.sched=gid; document.body.appendChild(x); x.click(); x.remove(); },FIN.id);
    await p.waitForFunction(id=>{ const e=document.querySelector(`#modal [data-riv="${id}"]`); return e&&/(leads|tied|First meeting)/.test(e.textContent); },FIN.id,{timeout:30000});
    const line=await p.evaluate(async gid=>{ const G=window.__gc, s=G.season.SCHED.find(x=>x.id===gid);
      const rr=await (await fetch('/api/rivalry?game='+gid)).json();
      const g={id:'t',home:s.home,away:s.away,hs:s.result.home,as:s.result.away,sched:s,plays:[],hist:[],mode:'replay'};
      const P={seq:999,quarter:4,result:'run',gain:1,text:'',offense:'home',players:{},call:{type:'run'},after:{status:'final',score:{home:g.hs,away:g.as}}};
      const L=G.playLine(g,P); return {rr:rr.rivalry,txt:L&&L.text,hs:g.hs,as:g.as,home:s.home,away:s.away}; },FIN.id);
    await p.evaluate(()=>{ const c=document.querySelector('#modal [data-close]'); if(c) c.click(); });
    const exp=line.rr&&line.hs!==line.as?((line.hs>line.as?line.home:line.away)===line.rr.holder?'keep':'take'):'stays';
    check(line.rr&&new RegExp(exp+' '+line.rr.trophy.replace(/[&]/g,'.')).test(line.txt||''),`commentateur, fin de ${FIN.away} @ ${FIN.home} : « ${(line.txt||'').slice(-90)} »`);
    // la fiche d'une franchise (Teams)
    await p.evaluate(()=>window.__gc.season.setView('teams')); await p.waitForTimeout(300);
    await p.click(`[data-team="${UP.home}"]`).catch(()=>{});
    await p.waitForFunction(()=>{ const e=document.querySelector('[data-riv-k="team"]'); return e&&/(leads|tied|First meeting)/.test(e.textContent); },null,{timeout:15000}).catch(()=>{});
    const tm=await p.$eval('[data-riv-k="team"]',x=>x.closest('.panel').textContent.replace(/\s+/g,' ').trim()).catch(()=>'');
    check(/Rival ·/.test(tm)&&/Rivalry/.test(tm),`fiche ${UP.home} : « ${tm.slice(0,110)} »`);
    if(tm) await cap(p,'4_fiche_equipe','[data-riv-k="team"]');
    errs.push(...p.errs);
    const mo=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await sched(mo,'upcoming'); await mo.click(`[data-schteam="${UP.home}"]`); await mo.waitForTimeout(250); await mo.click(`[data-schbet="${UP.id}"]`); await mo.waitForTimeout(1500);
    const w=await mo.evaluate(()=>document.documentElement.scrollWidth);
    check(w<=390,`téléphone : pas de défilement horizontal (${w} px)`);
    await cap(mo,'5_telephone');
    errs.push(...mo.errs);
    srv2=await server(P2,{GC_RIVALITES:'off'});
    const off=await ouvrir(b,P2);
    await sched(off,'upcoming'); await off.click(`[data-schteam="${UP.home}"]`); await off.waitForTimeout(250); await off.click(`[data-schbet="${UP.id}"]`); await off.waitForTimeout(800);
    const r404=await off.evaluate(async gid=>(await fetch('/api/rivalry?game='+gid)).status,UP.id);
    check(!(await off.$('.riv-pill'))&&!(await off.$('[data-riv]'))&&r404===404,'GC_RIVALITES=off : ni marqueur ni bilan, /api/rivalry 404');
    errs.push(...off.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
