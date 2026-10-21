// Résultats du jour en cours seulement (21/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_jour.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Ne dépend pas de l'heure : le serveur est réglé (GC_DEMO_AT) sur le 3e jour de la dernière semaine des données, à
// 07:30 (avant le premier coup d'envoi du jour) puis 2 h après le premier coup d'envoi du jour.
// Vérifie : tableau Live (tuiles des matchs terminés, compteur « Results », bandeau, Big plays) : seulement les matchs
// du jour ; le matin, aucun résultat de la veille (bandeau : « Today's results appear here ») ; calendrier : un onglet
// par jour, aujourd'hui ouvert (« TODAY »), les autres fermés ; un jour passé s'ouvre d'un toucher et le reste ; aucune
// erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8153;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const TZ='Europe/Brussels', jour=ms=>new Intl.DateTimeFormat('en-CA',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms));

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const kos=W.schedule.map(g=>Date.parse(g.kickoff)).sort((a,b)=>a-b);
const jours=[...new Set(kos.map(jour))];
const J=jours[Math.min(2,jours.length-1)];                       // le 3e jour de la semaine
const ko0=kos.find(k=>jour(k)===J);
const MATIN=ko0-150*60e3, APRES=ko0+120*60e3;                    // 07:30 · 2 h après le premier coup d'envoi
const abbr=a=>W.teams[a]?W.teams[a].abbr:a;
const duJour=new Set(W.schedule.filter(g=>jour(Date.parse(g.kickoff))===J).map(g=>abbr(g.away)+'@'+abbr(g.home)));

async function server(at){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-jour-'));
  fs.cpSync(path.join(WEEKS,week),path.join(data,'weeks',week),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:new Date(at).toISOString()}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const etat=p=>p.evaluate(()=>{
  const G=window.__gc, grp=document.querySelector('#tkTrack .tk-group');
  const tk=grp?[...grp.querySelectorAll('.tk')].map(e=>{ const a=e.querySelectorAll('.abbr');
    return {final:/FINAL/.test(e.textContent),m:a.length>1?a[0].textContent+'@'+a[1].textContent:null,txt:e.textContent.replace(/\s+/g,' ').trim()}; }):[];
  const tiles=[...document.querySelectorAll('#liveGrid .tile[data-gid]')].map(t=>{ const g=G.byId[t.dataset.gid]; return g?{mode:g.mode,ko:g.sched.ko}:null; }).filter(Boolean);
  const cnt=[...document.querySelectorAll('.live-head .seg .cnt')].map(c=>+c.textContent);
  const mo=[...document.querySelectorAll('#moments .mo')].map(e=>e.textContent);
  return {tk,tiles,cnt,mo};
});
const calendrier=p=>p.evaluate(()=>[...document.querySelectorAll('#viewSchedule details.sch-day')].map(d=>({day:d.dataset.day,open:d.open,today:!!d.querySelector('.sch-today'),rows:d.querySelectorAll('.sch-row').length,sum:d.querySelector('.sch-sum').textContent})));

(async()=>{
  console.log(`${week} · jour testé ${J} (${duJour.size} matchs) · matin ${new Date(MATIN).toISOString()} · après-midi ${new Date(APRES).toISOString()}`);
  const b=await chromium.launch({executablePath:EXE});
  try{
    // ---- le matin, avant le premier coup d'envoi du jour ----
    let srv=await server(MATIN);
    try{
      const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
      await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); await p.waitForTimeout(1200);
      const s=await etat(p);
      check(s.cnt[2]===0,`le matin : « Results 0 » (${s.cnt[2]})`);
      check(!s.tiles.some(t=>t.mode==='replay'),`le matin : aucune tuile de match terminé la veille (${s.tiles.map(t=>t.mode).join(', ')})`);
      check(!s.tk.some(x=>x.final)&&s.tk.some(x=>/Today's results appear here/.test(x.txt)),`le matin : bandeau sans résultat de la veille (« ${s.tk.map(x=>x.txt).join(' | ')} »)`);
      check(s.mo.length===0,`le matin : pas de Big plays de la veille (${s.mo.length})`);
      await p.evaluate(()=>document.querySelector('[data-seg="results"]').click()); await p.waitForTimeout(600);
      const c=await calendrier(p);
      const td=c.find(d=>d.today);
      check(td&&td.open&&/No results yet/.test(td.sum),`calendrier, Results : aujourd'hui ouvert, « No results yet » (${td&&td.sum})`);
      check(c.filter(d=>!d.today).length>=1&&c.filter(d=>!d.today).every(d=>!d.open),`calendrier : les jours passés sont fermés (${c.filter(d=>!d.today).length})`);
      check(!errs.length,'le matin : aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
      await p.close();
    } finally { srv.kill(); await new Promise(r=>setTimeout(r,800)); }
    // ---- l'après-midi : des matchs du jour sont terminés ----
    srv=await server(APRES);
    try{
      const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
      await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); await p.waitForTimeout(1200);
      const s=await etat(p);
      const finJour=W.schedule.filter(g=>jour(Date.parse(g.kickoff))===J&&g.result).length;
      const replays=s.tiles.filter(t=>t.mode==='replay');
      check(replays.length>=1&&replays.every(t=>jour(t.ko)===J),`tuiles des matchs terminés : seulement ceux du jour (${replays.length})`);
      check(s.cnt[2]>0&&s.cnt[2]<finJour+1,`« Results » compte les résultats du jour (${s.cnt[2]})`);
      const fins=s.tk.filter(x=>x.final);
      check(fins.length>=1&&fins.every(x=>duJour.has(x.m)),`bandeau : seulement des résultats du jour (${fins.map(x=>x.m).join(', ')})`);
      check(s.mo.every(t=>[...duJour].some(m=>t.includes(m))),`Big plays : seulement des matchs du jour (${s.mo.length})`);
      await p.evaluate(()=>document.querySelector('.rail-btn[data-view="schedule"]').click()); await p.waitForTimeout(600);
      let c=await calendrier(p);
      const td=c.find(d=>d.today), passe=c.find(d=>!d.today);
      check(td&&td.open&&td.rows>0,`calendrier : aujourd'hui ouvert (${td&&td.rows} matchs) avec « TODAY »`);
      check(passe&&!passe.open&&c.filter(d=>!d.today&&d.open).length===0,'calendrier : les autres jours sont fermés');
      await p.evaluate(d=>document.querySelector(`#viewSchedule details.sch-day[data-day="${d}"] > summary`).click(),passe.day); await p.waitForTimeout(300);
      await p.evaluate(()=>window.__gc.season.setView('schedule')); await p.waitForTimeout(400);   // nouveau rendu
      c=await calendrier(p);
      check(c.find(d=>d.day===passe.day).open&&c.find(d=>d.day===passe.day).rows>0,`un toucher ouvre ${passe.day}, et il reste ouvert après un nouveau rendu`);
      check(!errs.length,"l'après-midi : aucune erreur JS"+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
      await p.close();
    } finally { srv.kill(); }
  } finally { await b.close(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
