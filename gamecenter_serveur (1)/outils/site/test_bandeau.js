// Scores des matchs terminés (bloc 2, étape 2 — 11/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_bandeau.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Serveur sur une copie des données, horloge (GC_DEMO_AT) 2 h après le premier coup d'envoi de la dernière semaine :
// plusieurs matchs terminés. Par défaut : bandeau = score de chaque match terminé (celui du moteur), tuiles des matchs
// terminés avec leur score, Big plays présents. Réglages → « Hide scores » : plus aucun score de match non regardé
// (bandeau, tuiles), Big plays vides ; le réglage survit au rechargement ; désactivé : les scores reviennent.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8133;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const MINUS='−';

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const ko0=Math.min(...W.schedule.map(g=>Date.parse(g.kickoff)));
const AT=new Date(ko0+2*3600e3+5*60e3).toISOString();
const final={}; for(const g of W.schedule) if(g.result) final[`${W.teams[g.away]?W.teams[g.away].abbr:g.away}@${W.teams[g.home]?W.teams[g.home].abbr:g.home}`]=g;

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-bandeau-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* état affiché : éléments FINAL du bandeau (1re copie), tuiles des matchs terminés, Big plays */
const etat=p=>p.evaluate(()=>{
  const grp=document.querySelector('#tkTrack .tk-group');
  const tk=grp?[...grp.querySelectorAll('.tk')].filter(e=>/FINAL/.test(e.textContent)).map(e=>{ const a=e.querySelectorAll('.abbr'), s=e.querySelectorAll('.sc');
    return {m:a[0].textContent+'@'+a[1].textContent, away:s[0].textContent, home:s[1].textContent}; }):[];
  const tiles=[...document.querySelectorAll('#liveGrid .tile[data-gid]')].map(t=>{ const g=window.__gc.byId?window.__gc.byId[t.dataset.gid]:null;
    return {replay:!!(g&&g.mode==='replay'), sc:[...t.querySelectorAll('.sc')].map(e=>e.textContent.trim())}; }).filter(t=>t.replay);
  return {tk, tiles, mo:document.querySelectorAll('#moments .mo').length};
});
const ouvrirReglages=async p=>{ await p.click('.rail-btn[data-view="settings"]'); await p.waitForSelector('[data-set="spoil"]'); };
const basculer=async p=>{ await ouvrirReglages(p); await p.click('[data-set="spoil"]'); await p.waitForTimeout(300);
  const v=await p.getAttribute('[data-set="spoil"]','aria-checked'); await p.click('.rail-btn[data-view="live"]'); await p.waitForTimeout(800); return v; };

(async()=>{
  console.log(`${week} · horloge ${AT} · ${Object.keys(final).length} matchs avec résultat dans la semaine`);
  const srv=await server();
  const b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    await p.waitForTimeout(1500);
    let e=await etat(p);
    console.log('   par défaut :',JSON.stringify(e).slice(0,300));
    check(e.tk.length>0,`bandeau : ${e.tk.length} matchs terminés`);
    check(e.tk.every(x=>/^\d+$/.test(x.away)&&/^\d+$/.test(x.home)),'bandeau : un score pour chaque match terminé, sans réglage');
    check(e.tk.every(x=>{ const g=final[x.m]; return g&&+x.home===g.result.home&&+x.away===g.result.away; }),'bandeau : score = celui du moteur');
    check(e.tiles.length>0&&e.tiles.every(t=>t.sc.length&&t.sc.every(s=>s!==MINUS)),`tuiles des matchs terminés avec leur score (${e.tiles.length})`);
    check(e.mo>0,`Big plays des matchs terminés (${e.mo})`);
    await ouvrirReglages(p);
    check(await p.getAttribute('[data-set="spoil"]','aria-checked')==='false','réglage « Hide scores » désactivé par défaut');
    await p.click('.rail-btn[data-view="live"]');

    check(await basculer(p)==='true','« Hide scores » activé');
    e=await etat(p);
    console.log('   masqués :',JSON.stringify(e).slice(0,300));
    check(e.tk.length>0&&e.tk.every(x=>x.away===MINUS&&x.home===MINUS),'bandeau : aucun score de match non regardé');
    check(e.tiles.every(t=>t.sc.every(s=>s===MINUS)),'tuiles : aucun score de match non regardé');
    check(e.mo===0,'Big plays : rien des matchs non regardés');

    await p.reload(); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); await p.waitForTimeout(1500);
    e=await etat(p);
    check(e.tk.length>0&&e.tk.every(x=>x.away===MINUS),'réglage gardé après rechargement');

    check(await basculer(p)==='false','« Hide scores » désactivé');
    e=await etat(p);
    check(e.tk.length>0&&e.tk.every(x=>/^\d+$/.test(x.away)),'les scores reviennent');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
