// Schedule : filtre par franchise et paris sous un match (section 84, 30/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_schedule.js          (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT). Vérifie : une puce par franchise, à sa couleur ; un
// clic n'affiche que ses matchs (Upcoming, All games, Results), un second clic ou « All teams » remet tout ; un match à
// venir s'ouvre d'un clic (panneau : chance de victoire, moneyline, spread, total aux prix du moteur), un seul à la fois,
// se referme au second clic ; un prix du panneau va au bulletin et le panneau reste ouvert ; téléphone 390 px sans
// défilement horizontal ; GC_SCHEDULE_PLUS=off : ni puces ni panneau (le calendrier d'avant) ; aucune erreur JS.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const T0=Date.parse(REG[Math.floor(REG.length*0.5)].kickoff)+60e3, DEMO=new Date(T0).toISOString();

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-schedule-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks')); fs.symlinkSync(path.join(WEEKS,DERNIERE),path.join(data,'weeks',DERNIERE));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:DEMO},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const ouvrir=async(b,port,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
  await p.evaluate(()=>window.__gc.season.setView('schedule')); await p.waitForSelector('#viewSchedule .sch'); return p; };
const matchs=p=>p.$$eval('#viewSchedule .sch-row',rs=>rs.map(r=>r.querySelector('.sch-m').textContent.replace(/\s+/g,' ').trim()));
const ouverts=p=>p.$$eval('#viewSchedule .sch-game.open',x=>x.map(e=>e.dataset.g));

(async()=>{
  const P1=8169, P2=8170;
  const srv=await server(P1,{}), b=await chromium.launch({executablePath:EXE}), errs=[];
  let srv2=null;
  try{
    const p=await ouvrir(b,P1);
    const puces=await p.$$eval('#viewSchedule [data-schteam]',bs=>bs.map(x=>({t:x.dataset.schteam,tm:x.dataset.tm||'',c:getComputedStyle(x).borderTopColor})));
    check(puces.length===Object.keys(W.teams).length+1&&puces[0].t==='',`une puce « All teams » et une par franchise (${puces.length-1})`);
    check(puces.slice(1).every(x=>x.tm===x.t)&&new Set(puces.slice(1).map(x=>x.c)).size>=20,'chaque puce à la couleur de sa franchise');

    await p.click('[data-schf="upcoming"]'); await p.waitForTimeout(200);
    const tous=(await matchs(p)).length;
    const team=REG.filter(g=>Date.parse(g.kickoff)>T0)[0].home, nom=W.teams[team].name;
    await p.click(`[data-schteam="${team}"]`); await p.waitForTimeout(200);
    const aVenir=W.schedule.filter(g=>Date.parse(g.kickoff)>T0+1e3&&(g.home===team||g.away===team)&&g.phase==='regular').length;
    let m=await matchs(p);
    check(m.length===aVenir&&m.every(x=>x.includes(nom)),`Upcoming filtré sur ${team} : ${m.length} matchs à venir, tous les siens (${tous} sans filtre)`);
    check(await p.$eval(`[data-schteam="${team}"]`,x=>x.getAttribute('aria-pressed')==='true'),'puce choisie marquée');
    await p.click('[data-schf="results"]'); await p.waitForTimeout(200); m=await matchs(p);
    check(m.length>0&&m.every(x=>x.includes(nom)),`Results filtré aussi (${m.length})`);
    await p.click('[data-schf="upcoming"]'); await p.click(`[data-schteam="${team}"]`); await p.waitForTimeout(200);
    check((await matchs(p)).length===tous,'second clic sur la même puce : tout revient');
    await p.click(`[data-schteam="${team}"]`); await p.click('[data-schteam=""]'); await p.waitForTimeout(200);
    check((await matchs(p)).length===tous,'« All teams » : tout revient');

    await p.click(`[data-schteam="${team}"]`); await p.waitForTimeout(200);
    const ids=await p.$$eval('#viewSchedule [data-schbet]',bs=>bs.map(x=>x.dataset.schbet));
    await p.click(`[data-schbet="${ids[0]}"]`); await p.waitForTimeout(450);
    check(JSON.stringify(await ouverts(p))===JSON.stringify([ids[0]]),'un clic sur le match ouvre son panneau');
    const g=W.schedule.find(x=>x.id===ids[0]), o=g.odds;
    const pan=await p.$eval(`.sch-game[data-g="${ids[0]}"] .sch-drop`,d=>({h:d.getBoundingClientRect().height,n:d.querySelectorAll('.odd').length,on:d.querySelectorAll('.odd:not([disabled])').length,txt:d.textContent,inert:d.inert}));
    check(pan.h>60&&pan.n===6&&pan.on===6&&!pan.inert,`panneau visible : 6 prix ouverts (moneyline, spread, total)`);
    const ligne=Math.abs(o.spread_home).toFixed(1), tot=o.total.toFixed(1);
    check(pan.txt.includes(ligne)&&pan.txt.includes(tot)&&/Engine win chance/.test(pan.txt),`lignes du moteur : spread ${ligne}, total ${tot}`);
    if(ids.length>1){ await p.click(`[data-schbet="${ids[1]}"]`); await p.waitForTimeout(450);
      check(JSON.stringify(await ouverts(p))===JSON.stringify([ids[1]]),'un autre match : le premier se referme (un seul ouvert)');
      await p.click(`[data-schbet="${ids[0]}"]`); await p.waitForTimeout(450); }
    await p.click(`.sch-game[data-g="${ids[0]}"] .sch-drop .odd[data-key$=":tot:over"]`); await p.waitForTimeout(400);
    const slip=await p.evaluate(()=>window.__gc.season.bets.slip().picks.map(x=>x.key));
    check(slip.includes(`${ids[0]}:tot:over`),'un prix du panneau va au bulletin');
    check(JSON.stringify(await ouverts(p))===JSON.stringify([ids[0]]),'le panneau reste ouvert après l\'ajout');
    await p.click(`[data-schbet="${ids[0]}"]`); await p.waitForTimeout(450);
    check(!(await ouverts(p)).length&&await p.$eval(`.sch-game[data-g="${ids[0]}"] .sch-drop`,d=>d.inert&&d.getBoundingClientRect().height<2),'second clic : le panneau se referme');
    errs.push(...p.errs);

    const mo=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await mo.click('[data-schf="upcoming"]'); await mo.click(`[data-schteam="${team}"]`); await mo.click('[data-schbet]'); await mo.waitForTimeout(450);
    const w=await mo.evaluate(()=>document.documentElement.scrollWidth);
    check(w<=390,`téléphone : pas de défilement horizontal (${w} px)`);
    errs.push(...mo.errs);

    srv2=await server(P2,{GC_SCHEDULE_PLUS:'off'});
    const off=await ouvrir(b,P2);
    check(!(await off.$('#viewSchedule [data-schteam]'))&&!(await off.$('#viewSchedule [data-schbet]'))&&!(await off.$('.sch-drop')),'GC_SCHEDULE_PLUS=off : ni puces ni panneau');
    errs.push(...off.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
