// Trajectoires du moteur, étape 4 : la course après le contact telle que le moteur l'a simulée (causal léger, bloc 1 ;
// play.geo.sim — 07/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_courses_simulees.js [dossier data/weeks | match.json]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match dont les courses portent play.geo.sim (le dernier de data/weeks
// qui en a ; sinon le fichier donné). Vérifie, course par course :
//   - la course est dessinée depuis la simulation (presque toutes : sauf celles que le dessin d'avant garde, course
//     bloquée ou feed trop loin de la simulation) ;
//   - après le contact, le porteur suit le chemin simulé : au milieu de la simulation, il est là où elle le met (mise à
//     l'échelle sur les yards du feed, dérive en travers ramenée au point d'arrivée) ;
//   - il finit sur le point du feed ; chaque plaquage manqué de la simulation a son éclat blanc, sur un défenseur de la
//     simulation ; celui qui l'arrête a l'anneau rouge (pas sur un touchdown) ;
//   - aucune erreur JS ; un match sans play.geo.sim est dessiné comme avant (aucune course « simulée »).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), ARG=process.argv[2], PORT=8151;
const WEEKS=ARG&&fs.existsSync(ARG)&&fs.statSync(ARG).isDirectory()?path.resolve(ARG):path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  if(ARG&&fs.existsSync(ARG)&&fs.statSync(ARG).isFile()) return [{F:JSON.parse(fs.readFileSync(ARG,'utf8')),src:path.basename(ARG)}];
  const out=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games'); if(!fs.existsSync(dir)) continue;
    for(const f of fs.readdirSync(dir).filter(f=>/^w\d+-r\d+\.json$/.test(f)).sort()){
      const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
      if(F.plays.filter(P=>P.geo&&P.geo.sim).length>=15) return [{F,src:`${w}/${f}`}];
    }
  }
  return out;
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-sim-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

async function rejouer(page,F){
  return page.evaluate(F=>{
    const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
    const out=[], vu=new Set(), errs=[];
    for(let i=0;i<400000&&g.status!=='final';i++){
      try{ G.stepGame(g,0.05); }catch(e){ errs.push(e.message); break; }
      const P=g.cur, pl=g.plan;
      if(!P||!pl||g.phase!=='play'||vu.has(P.seq)||P.result!=='run'||!(P.geo&&P.geo.k==='run')) continue;
      vu.add(P.seq);
      const S=P.geo.sim, row={seq:P.seq,sim:!!S,drawn:!!pl.sim,td:P.result==='touchdown'};
      if(S){
        const cs=pl.carrier.length?pl.carrier[pl.carrier.length-1][3]:7, k=pl.off[cs];
        const end=kfAt(k,0.99); row.end=Math.hypot(end.x-pl.spot.x,end.y-pl.spot.y);
        row.missExp=S.ev.filter(e=>!e[2]).length; row.miss=(pl.miss||[]).length;
        row.missOk=(pl.miss||[]).every(m=>S.d.some(q=>q[0]&&pl.def[m.i]));
        row.tackle=S.ev.some(e=>e[2]); row.stop=!!pl.stop;
        if(pl.sim){   /* the carrier at the middle of the simulation: where the scaled, shifted simulated path puts him */
          const n=S.c.length, j=Math.floor((n-1)/2);
          row.mid=null;
          /* the keyframes after the contact are the simulation's samples, in order: the j-th from the end of the list */
          const after=k.slice(k.length-n-1, k.length-1);   /* [u0 point, samples 1..n-1 (last = spot)] */
          if(after.length===n){ const q=after[j], p=kfAt(k,q[0]); row.mid=Math.hypot(p.x-q[1],p.y-q[2]);
            /* after the contact he gains ground toward the spot when the simulation does (the field's direction aside) */
            const dx=after[n-1][1]-after[0][1], sx=S.c[n-1][0]-S.c[0][0], to=pl.spot.x-after[0][1];
            row.sens=Math.abs(sx)<0.6||Math.abs(dx)<0.6||Math.sign(dx)===Math.sign(to); }
        }
      }
      out.push(row);
    }
    return {out,errs,status:g.status};
  },F);
}

(async()=>{
  const L=feeds();
  if(!L.length){ console.log('aucun match avec play.geo.sim (semaines d\'avant le 07/11/2026) : rien à vérifier'); process.exit(0); }
  const {F,src}=L[0]; console.log(src);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const page=await b.newPage({viewport:{width:1280,height:800}}), errs=[]; page.on('pageerror',e=>errs.push(e.message));
    await page.goto(`http://localhost:${PORT}/`,{waitUntil:'domcontentloaded',timeout:90000});
    await page.waitForFunction(()=>window.__gc&&window.__gc.openReplayFeed,null,{timeout:90000});
    const R=await rejouer(page,F), runs=R.out.filter(r=>r.sim);
    console.log(`  ${R.out.length} courses du bloc F rejouées, ${runs.length} avec play.geo.sim`);
    check(R.status==='final'&&!R.errs.length,'match rejoué jusqu\'au bout'+(R.errs.length?' : '+R.errs[0]:''));
    const drawn=runs.filter(r=>r.drawn);
    check(runs.length>=10&&drawn.length>=0.7*runs.length,`courses dessinées depuis la simulation (${drawn.length} / ${runs.length})`);
    const mid=drawn.filter(r=>r.mid!=null);
    check(mid.length>=0.9*drawn.length&&mid.every(r=>r.mid<0.05),`au milieu de la simulation, le porteur est là où elle le met (${mid.length} courses, écart max ${Math.max(0,...mid.map(r=>r.mid)).toFixed(3)} yd)`);
    check(mid.every(r=>r.sens),'il avance dans le sens de la simulation');
    check(runs.every(r=>r.end<1.2),`il finit sur le point du feed (écart max ${Math.max(0,...runs.map(r=>r.end)).toFixed(2)} yd)`);
    const mt=drawn.reduce((a,r)=>a+r.missExp,0), md=drawn.reduce((a,r)=>a+r.miss,0);
    check(md<=mt&&md>=0.8*mt&&drawn.every(r=>r.missOk),`plaquages manqués : un éclat blanc chacun (${md} / ${mt}), sur un défenseur de la simulation`);
    const tk=drawn.filter(r=>r.tackle&&!r.td);
    check(tk.every(r=>r.stop),`le plaqueur de la simulation a l'anneau rouge (${tk.filter(r=>r.stop).length} / ${tk.length})`);
    /* sans play.geo.sim : le dessin d'avant */
    const G=JSON.parse(JSON.stringify(F)); for(const P of G.plays) if(P.geo) delete P.geo.sim;
    const R2=await rejouer(page,G);
    check(R2.status==='final'&&R2.out.every(r=>!r.drawn),'sans play.geo.sim : aucune course dessinée depuis la simulation (dessin d\'avant)');
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
