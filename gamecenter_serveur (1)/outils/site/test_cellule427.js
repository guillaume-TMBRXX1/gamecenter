// Game Center du notebook (cellule 427, NGS_TEMPLATE) — test navigateur (Playwright, sans serveur).
//   node outils/site/test_cellule427.js [notebook] [dossier data/weeks]
// Le modèle est lu dans le notebook, rempli comme render_gamefeed (match réel de la dernière semaine) et ouvert dans
// Chromium. Le replay est déroulé en temps simulé (stepReplay par pas de 0,1 s) jusqu'au coup de sifflet final :
// toutes les actions jouées, score final = celui du moteur, mi-temps ≈ RP_HALF (4 s, comme avant les pauses du site),
// aucun arrêt en fin de Q1 / Q3 (pas d'écran de pause dans le notebook), saut dans le replay, aucune erreur JS.
// Lancé par outils/site/tests_navigateur.sh (groupe site) ; après outils/regen427.py.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const HERE=path.resolve(__dirname,'..','..');
const NB=process.argv[2]||path.join(HERE,'NFL_Sim_GameCenter.ipynb'), DATA=process.argv[3]||path.join(HERE,'data/weeks');
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const nb=JSON.parse(fs.readFileSync(NB,'utf8'));
const cell=nb.cells.map(c=>c.source.join('')).find(s=>s.includes("NGS_TEMPLATE = r'''")&&s.includes('def render_ngs_gamecenter'));
const a=cell.indexOf("NGS_TEMPLATE = r'''")+"NGS_TEMPLATE = r'''".length, TPL=cell.slice(a,cell.indexOf("'''",a));
const week=fs.readdirSync(DATA).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(DATA,week,'week.json'),'utf8'));
const G=W.schedule.find(g=>g.phase==='regular'), feed=JSON.parse(fs.readFileSync(path.join(DATA,week,G.feed),'utf8'));
const js=o=>JSON.stringify(o).replace(/<\//g,'<\\/');            /* comme _gc_json */
const doc=TPL.replace(/__UID__/g,'gcxtest').replace('__BET__','null').replace('__FEED__',js(feed));
(async()=>{
  console.log(`${path.basename(NB)} · modèle ${TPL.length} caractères · ${week} ${G.id} (${feed.plays.length} actions)`);
  const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
  const p=await b.newPage({viewport:{width:1280,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.route(/^https?:\/\//,r=>r.abort());                  /* polices en ligne : sans réseau, comme hors ligne */
  await p.setContent(doc,{waitUntil:'load'}); await p.waitForFunction(()=>window.__gcx&&window.__gcx.g,null,{timeout:20000});
  const r=await p.evaluate(()=>{
    const X=window.__gcx, g=X.g; g.speed=1; let t=0, half=0; const pauses={};
    for(let i=0;i<400000&&g.status!=='final';i++){
      X.stepReplay(g,0.1); t+=0.1;
      if(g.status==='half') half+=0.1;
      if(g.pause>0&&g.status!=='final') pauses[g.idx]=(pauses[g.idx]||0)+0.1;   /* temps passé en pause après l'action idx */
    }
    const fin={status:g.status,idx:g.idx,score:[g.hs,g.as]}, last=g.plays[g.plays.length-1].after.score;
    X.rpSeek(g,Math.floor(g.plays.length/2)); X.rpAfterSeek(g);
    const longues=Object.entries(pauses).filter(([i,s])=>s>=3).map(([i,s])=>[+i,+s.toFixed(1),g.plays[+i].quarter,(g.plays[+i].after||{}).status]);
    return {status:fin.status,idx:fin.idx,n:g.plays.length,score:fin.score,last:[last.home,last.away],half:+half.toFixed(1),t:Math.round(t),longues,
            brk:typeof window.BRK_SEC,bug:(document.querySelector('.bug')||{}).textContent||''};
  });
  console.log('   ',JSON.stringify(r).slice(0,400));
  check(r.status==='final','replay déroulé jusqu\'au coup de sifflet final');
  check(r.score[0]===r.last[0]&&r.score[1]===r.last[1]&&r.last[0]===feed.game.final_score.home&&r.last[1]===feed.game.final_score.away,
    `score final = celui du moteur (${feed.game.final_score.home}-${feed.game.final_score.away})`);
  check(r.half>=3&&r.half<=6&&r.longues.length===1,`mi-temps ≈ 4 s comme avant (${r.half} s)`);
  check(r.longues.every(([i,s,q,st])=>st==='half'),'aucun arrêt de 10 s en fin de Q1 / Q3 (pas d\'écran de pause dans le notebook)');
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  await b.close(); console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
