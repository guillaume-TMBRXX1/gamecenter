// Fin de match dans le grand écran (14/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_fin_de_match.js       (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Le match « Prime Time » de l'accueil (replay en boucle sur sa tuile), ouvert en grand écran et joué jusqu'au coup de
// sifflet final : l'écran final (résultat, statistiques) reste, le replay ne recommence pas (avant : reprise à zéro
// après 12 s) ; une fois le grand écran fermé, la tuile reprend sa boucle. Le direct et les replays du calendrier
// restaient déjà sur l'écran final (test_pauses.js).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fails=0; const ok=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c){ fails++; process.exitCode=1; } };

async function server(at,port){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-fin-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:at,GC_PUSH_LOOP:'0'}),stdio:'ignore'});
  for(let i=0;i<80;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('server did not start');
}

(async()=>{
  /* une heure où des matchs de la dernière semaine sont finis et aucun n'est en direct : la tuile Prime Time est un replay */
  const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
  const at=W.week.start+'T23:30:00+02:00';
  const srv=await server(at,8133), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto('http://localhost:8133/'); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:20000});
    const tuile=await p.evaluate(()=>{ const g=window.__gc.games[0]; return g&&{id:g.id,mode:g.mode,loop:g.loop}; });
    console.log(`${week} · ${at} · tuile Prime Time ${JSON.stringify(tuile)}`);
    ok(tuile&&tuile.mode==='replay'&&tuile.loop,'la tuile Prime Time est un replay en boucle');
    await p.click(`#liveGrid [data-open="${tuile.id}"]`);
    await p.waitForFunction(()=>!document.getElementById('modal').hidden&&window.__gc.getModalView());
    /* temps simulé : la dernière action, puis 60 s (l'écran final durait 12 s avant la reprise à zéro) */
    const r=await p.evaluate(()=>{ const G=window.__gc, g=G.getModalView().g, n=g.plays.length;
      G.rpSeek(g,n-1); g.paused=false; g.speed=1; let fin=null;
      for(let t=0;t<120;t+=0.1){ G.stepGame(g,0.1); G.updateGameUI(g); if(fin===null&&g.status==='final') fin=t; if(fin!==null&&t-fin>=60) break; }
      const el=document.querySelector('#modal .field.big .brk');
      return {n,idx:g.idx,status:g.status,paused:g.paused,fin,brk:!!(el&&!el.hidden&&!el.classList.contains('out')),
              titre:el&&el.querySelector('.brk-k')&&el.querySelector('.brk-k').textContent,
              cartes:el?el.querySelectorAll('.brk-card').length:0}; });
    console.log('    '+JSON.stringify(r));
    ok(r.status==='final'&&r.idx===r.n-1,'60 s après le coup de sifflet final : toujours la fin du match (pas de reprise à zéro)');
    ok(r.brk&&/final/i.test(r.titre||''),'écran final affiché (« '+r.titre+' »)');
    ok(r.cartes>0,'statistiques du match affichées ('+r.cartes+' cartes)');
    ok(r.paused,'replay arrêté sur l\'écran final');
    /* le grand écran fermé : la tuile reprend sa boucle */
    await p.keyboard.press('Escape');
    await p.waitForFunction(()=>document.getElementById('modal').hidden);
    const t=await p.evaluate(id=>{ const G=window.__gc, g=G.games.find(x=>x.id===id); if(!g) return null;
      for(let k=0;k<30;k++) G.stepGame(g,0.1); return {idx:g.idx,paused:g.paused,status:g.status}; },tuile.id);
    console.log('    tuile après fermeture '+JSON.stringify(t));
    ok(t&&!t.paused&&t.status!=='final'&&t.idx<5,'grand écran fermé : la tuile Prime Time reprend sa boucle au début');
    ok(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fails?fails+' échec(s)':'OK');
})().catch(e=>{ console.error(e); process.exit(1); });
