// Histoire de la ligue, records et carrières (bloc 2, étape 5 — 12/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_histoire.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Serveur sur une copie des données, horloge (GC_DEMO_AT) 2 h après le premier coup d'envoi de la dernière semaine :
// les semaines d'avant sont terminées, la dernière a quelques matchs terminés. Vérifie : API (champions = week.json, semaine
// en cours sans champion, records seulement de matchs terminés), onglet History (Seasons, Franchises, Records et ses trois
// listes), section Career de la fiche joueur (une ligne par semaine, total, rang de toujours), réglage « Hide scores »
// (semaines terminées seulement), mobile 390 px sans défilement horizontal, aucune erreur JS.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8136;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const weeks=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort();
const ALL=weeks.map(w=>JSON.parse(fs.readFileSync(path.join(WEEKS,w,'week.json'),'utf8')));
const DOCS=ALL.filter(d=>d.week.index>=2);   /* l'histoire part de la semaine 2 (semaine 1 : 4 franchises seulement) */
const W=DOCS[DOCS.length-1];
const ko0=Math.min(...W.schedule.map(g=>Date.parse(g.kickoff)));
const AT=new Date(ko0+2*3600e3+5*60e3).toISOString();

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-histoire-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const get=async u=>(await fetch(`http://localhost:${PORT}/api${u}`)).json();
const ouvrir=async p=>{ await p.click('.rail-btn[data-view="history"]'); await p.waitForSelector('#viewHistory [data-hist]',{timeout:30000});
  await p.click('[data-hist="seasons"]'); await p.waitForSelector('#viewHistory .hs-row,#viewHistory .st-empty',{timeout:30000}); };

(async()=>{
  console.log(`${weeks.length} semaines · horloge ${AT}`);
  const srv=await server();
  const b=await chromium.launch({executablePath:EXE});
  try{
    /* ---- API ---- */
    const H=await get('/league/history'), S=H.seasons, cur=S[S.length-1];
    const delta=await get('/delta'), st={}; for(const g of delta.state.schedule) st[g.id]=g.status;
    console.log('   saisons :',JSON.stringify(S.map(s=>[s.week,s.complete,s.games,s.champion])));
    check(S.length===DOCS.length,`une saison par semaine à partir de la semaine 2 (${S.length})`);
    const w1=[...Object.values(H.records.game.players),...Object.values(H.records.game.teams),...Object.values(H.records.season.players),...Object.values(H.records.season.teams)].flat().filter(x=>x.week<2);
    check(H.since_week===2&&S.every(s=>s.week>=2)&&w1.length===0,'semaine 1 exclue : ni saison ni record (since_week = 2)');
    const w1t=ALL.filter(d=>d.week.index<2).reduce((a,d)=>a+(d.champion?1:0),0);
    check(w1t===0||H.franchises.reduce((a,f)=>a+f.title_weeks.filter(w=>w<2).length,0)===0,'semaine 1 exclue : aucun titre de la semaine 1 dans Franchises');
    check(S.slice(0,-1).every((s,i)=>s.complete&&s.champion===DOCS[i].champion&&s.runner_up===DOCS[i].runner_up),'semaines terminées : champion et finaliste = week.json');
    const nFin=Object.values(st).filter(x=>x==='final').length;
    check(!cur.complete&&cur.champion===null&&cur.games===nFin&&nFin>0&&nFin<cur.games_total,`semaine en cours : pas de champion, ${cur.games} matchs terminés (serveur : ${nFin})`);
    const recG=[...Object.values(H.records.game.players),...Object.values(H.records.game.teams)].flat().filter(x=>x.week===W.week.index);
    check(recG.every(x=>st[x.game]==='final'),`records de la semaine en cours : seulement des matchs terminés (${recG.length})`);
    check(H.franchises.reduce((a,f)=>a+f.titles,0)===S.filter(s=>s.complete).length,'un titre par semaine terminée');
    const H2=await get('/league/history?finished_weeks=1');
    check(H2.seasons.length===DOCS.length-1&&H2.seasons.every(s=>s.complete),'« Hide scores » : semaines terminées seulement');

    /* ---- page ---- */
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    await ouvrir(p);
    const rows=await p.$$eval('#viewHistory .hs-row',r=>r.map(e=>e.textContent));
    check(rows.length===S.length,`Seasons : ${rows.length} lignes`);
    check(/In progress/.test(rows[0])&&rows[0].includes(`${cur.games} of ${cur.games_total} games`),'Seasons : la semaine en cours en premier, « In progress »');
    check(S.filter(s=>s.complete).every(s=>rows.some(r=>r.includes('W'+s.week)&&r.includes('Champion')&&r.includes(s.champion))),'Seasons : champion de chaque semaine terminée');
    await p.click('[data-hist="franchises"]'); await p.waitForTimeout(200);
    const fr=await p.$$eval('#viewHistory tbody tr',r=>r.length);
    check(fr===H.franchises.length,`Franchises : ${fr} équipes`);
    await p.click('[data-hist="records"]'); await p.waitForTimeout(200);
    const top=await p.$eval('#viewHistory .rc-card .rc-v',e=>+e.textContent);
    const k0=Object.keys(H.records.game.players)[0];
    check(top===H.records.game.players[k0][0].value,`Records · un match : ${H.records.labels[k0]} ${top}`);
    await p.click('[data-histrec="career"]'); await p.waitForTimeout(200);
    const car=await p.$$eval('#viewHistory .rc-card',c=>c.map(e=>e.querySelectorAll('.rc-row').length));
    const want=Object.values(H.records.career).map(l=>Math.min(10,l.length));
    check(car.length===want.length&&car.every((n,i)=>n===want[i])&&want.some(n=>n===10),`Records · carrière : ${car.length} classements (top 10 ; vides : ${want.filter(n=>!n).length})`);

    /* ---- fiche joueur : section Career ---- */
    const qb=H.records.career.pyd[0], team=qb.team;
    await p.click('.rail-btn[data-view="teams"]'); await p.click(`[data-team="${team}"]`); await p.waitForTimeout(300);
    await p.click(`#viewTeams tr[data-pl="${qb.id}"]`);
    await p.waitForFunction(()=>{ const e=document.querySelector('.pcard [data-career]'); return e&&e.querySelector('table'); },null,{timeout:15000});
    const C=(await get('/league/career/'+qb.id)).careers.find(c=>c.name===qb.name);
    const card=await p.$eval('.pcard [data-career]',e=>({rows:e.querySelectorAll('tbody tr').length,tot:!!e.querySelector('tr.car-tot'),txt:e.textContent}));
    console.log('   carrière :',qb.name,card.rows,'lignes ·',card.txt.slice(0,160));
    check(card.rows===C.seasons.length+(C.seasons.length>1?1:0)&&(C.seasons.length<2||card.tot),`Career : une ligne par semaine (${C.seasons.length}) et le total`);
    check(card.txt.includes(`#${C.ranks.pyd[0]} of ${C.ranks.pyd[1]}`)&&card.txt.includes(String(C.total.pyd)),`Career : rang de toujours #${C.ranks.pyd[0]} · ${C.total.pyd} yards`);
    check(C.seasons.every(x=>x.week>=2),`Career : rien de la semaine 1 (semaines ${C.seasons.map(x=>x.week).join(', ')})`);
    await p.keyboard.press('Escape');
    check(/counted from week 2 \(week 1 had only 4 franchises\)/.test(await p.$eval('#viewHistory .eyebrow',e=>e.textContent).catch(()=>'')),'History : « counted from week 2 » dans l\'en-tête');

    /* ---- Hide scores : semaines terminées seulement ---- */
    await p.click('.rail-btn[data-view="settings"]'); await p.waitForSelector('[data-set="spoil"]'); await p.click('[data-set="spoil"]'); await p.waitForTimeout(300);
    await ouvrir(p);
    await p.waitForFunction(n=>document.querySelectorAll('#viewHistory .hs-row').length===n,DOCS.length-1,{timeout:15000}).catch(()=>{});
    const rs=await p.$$eval('#viewHistory .hs-row',r=>r.map(e=>e.textContent));
    check(rs.length===DOCS.length-1&&!rs.some(r=>/In progress/.test(r)),'« Hide scores » : pas de semaine en cours dans History');

    /* ---- mobile ---- */
    const m=await b.newPage({viewport:{width:390,height:844},isMobile:true}); m.on('pageerror',e=>errs.push(e.message));
    await m.goto(`http://localhost:${PORT}/`); await m.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    for(const tab of ['seasons','franchises','records']){
      await m.evaluate(t=>{ window.__gc.season.setView('history'); },tab);
      await m.waitForSelector('#viewHistory [data-hist]',{timeout:15000});
      await m.click(`[data-hist="${tab}"]`); await m.waitForTimeout(300);
      const w=await m.evaluate(()=>document.documentElement.scrollWidth);
      check(w<=390,`mobile 390 px, ${tab} : pas de défilement horizontal (${w})`);
    }
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
