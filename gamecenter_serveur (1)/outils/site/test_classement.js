// Onglet Ranking (classement des joueurs de la semaine en cours, poste par poste — 14/10/2026) — test navigateur
// (Playwright + serveur réel).   node outils/site/test_classement.js   (depuis « gamecenter_serveur (1) »)
// Serveur sur une copie des données, horloge (GC_DEMO_AT) 2 h après le premier coup d'envoi de la dernière semaine :
// quelques matchs terminés. Vérifie : bouton dans la barre latérale, un onglet par poste, rangs 1..n et stat clé
// décroissante, meilleur QB = meneur « Pass yds » de la semaine dans History (calcul serveur indépendant), compteur de
// matchs terminés = serveur, fiche joueur « Season rank » = même rang, recherche « ranking », mobile 390 px sans
// défilement horizontal, barre latérale entière à l'écran, aucune erreur JS.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8137;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const weeks=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,weeks[weeks.length-1],'week.json'),'utf8'));
const ko0=Math.min(...W.schedule.map(g=>Date.parse(g.kickoff)));
const AT=new Date(ko0+2*3600e3+5*60e3).toISOString();
const POS=['QB','RB','WR','TE','EDGE','DT','LB','CB','S','K'];

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-classement-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const get=async u=>(await fetch(`http://localhost:${PORT}/api${u}`)).json();
const table=p=>p.$$eval('#viewRanking tbody tr',rs=>rs.map(r=>{ const td=[...r.querySelectorAll('td')]; const k=td.findIndex(x=>x.classList.contains('lead'));
  return {id:r.dataset.pl,rk:td[0].textContent.trim(),name:r.querySelector('th').textContent,key:k<0?null:+td[k].textContent}; }));

(async()=>{
  console.log(`${weeks.length} semaines · horloge ${AT}`);
  const srv=await server();
  const b=await chromium.launch({executablePath:EXE});
  try{
    const H=await get('/league/history'), cur=H.seasons[H.seasons.length-1];
    const delta=await get('/delta'), nFin=delta.state.schedule.filter(g=>g.status==='final').length;

    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const rail=await p.evaluate(()=>{ const bs=[...document.querySelectorAll('.rail-btn')].filter(x=>!x.hidden); return {n:bs.length,bottom:Math.max(...bs.map(x=>x.getBoundingClientRect().bottom)),h:innerHeight}; });
    check(rail.bottom<=rail.h,`barre latérale : ${rail.n} boutons, tous à l'écran (${Math.round(rail.bottom)} ≤ ${rail.h})`);
    await p.click('.rail-btn[data-view="ranking"]'); await p.waitForSelector('#viewRanking [data-rkpos]',{timeout:15000});
    check(await p.evaluate(()=>!document.getElementById('viewRanking').hidden&&document.querySelector('.rail-btn[data-view="ranking"]').getAttribute('aria-current')==='page'),'Ranking : vue affichée, bouton actif');
    const tabs=await p.$$eval('#viewRanking [data-rkpos]',bs=>bs.map(x=>x.dataset.rkpos));
    check(JSON.stringify(tabs)===JSON.stringify(POS),`un onglet par poste (${tabs.join(' ')})`);
    const head=await p.$eval('#viewRanking .eyebrow',e=>e.textContent);
    check(head.includes(`Week ${W.week.index} only`)&&head.includes(`${nFin} of ${W.schedule.length} games final`),`semaine ${W.week.index} seulement, ${nFin} matchs terminés (serveur)`);

    const tops={};
    for(const pos of POS){
      await p.click(`[data-rkpos="${pos}"]`); await p.waitForTimeout(150);
      const R=await table(p), ranked=R.filter(r=>r.rk!=='—');
      tops[pos]=ranked[0];
      const ok=ranked.every((r,i)=>r.rk===String(i+1)&&r.key>0&&(i===0||ranked[i-1].key>=r.key))&&R.slice(ranked.length).every(r=>!(r.key>0));
      check(ranked.length>0&&ok,`${pos} : ${ranked.length} classés (rangs 1..n, stat clé décroissante)${ranked[0]?` · #1 ${ranked[0].name} ${ranked[0].key}`:''}`);
    }
    const L=cur.leaders.pyd;
    check(L&&tops.QB&&tops.QB.key===L.value&&tops.QB.name.includes(L.name),`meilleur QB = meneur « Pass yds » de la semaine dans History (${L&&L.name} ${L&&L.value})`);

    /* fiche joueur : même rang que l'onglet */
    await p.click('[data-rkpos="RB"]'); await p.waitForTimeout(150);
    const RB=(await table(p)).filter(r=>r.rk!=='—'), x=RB[Math.min(1,RB.length-1)];
    await p.click(`#viewRanking tr[data-pl="${x.id}"]`); await p.waitForSelector('.pcard .pc-season',{timeout:10000});
    const sr=await p.$eval('.pcard .pc-season',e=>e.textContent);
    check(sr.includes('Rushing yards · RB')&&sr.includes(`#${x.rk} of ${RB.length} · ${x.key}`),`fiche joueur : « Season rank » #${x.rk} of ${RB.length} · ${x.key} (${sr.replace(/\s+/g,' ').trim()})`);
    await p.keyboard.press('Escape');

    /* recherche */
    await p.fill('#search',''); await p.type('#search','ranking'); await p.waitForTimeout(100);
    check(await p.$$eval('#searchList li',l=>l.some(x=>x.textContent.trim().startsWith('Ranking'))),'recherche « ranking » → page Ranking');
    await p.keyboard.press('Escape');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));

    /* mobile */
    const m=await b.newPage({viewport:{width:390,height:844},isMobile:true}); const merr=[]; m.on('pageerror',e=>merr.push(e.message));
    await m.goto(`http://localhost:${PORT}/`); await m.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    await m.evaluate(()=>window.__gc.season.setView('ranking'));
    await m.waitForSelector('#viewRanking tbody tr',{timeout:15000});
    for(const pos of ['QB','EDGE','K']){ await m.click(`[data-rkpos="${pos}"]`); await m.waitForTimeout(150);
      const w=await m.evaluate(()=>document.documentElement.scrollWidth); check(w<=390,`mobile 390 px, ${pos} : pas de défilement horizontal (${w})`); }
    check(merr.length===0,'mobile : aucune erreur JS'+(merr.length?' : '+merr[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
