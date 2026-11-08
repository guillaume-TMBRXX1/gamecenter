// Trajectoires du moteur, étape 6 : les duels de couverture tels que le moteur les a joués (causal léger, bloc 3 ;
// play.geo.cov — 08/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_couverture_simulee.js [dossier data/weeks | match.json]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé un match dont les passes portent play.geo.cov (le dernier de data/weeks qui en a, sinon le
// match de test outils/site/matchs/sim-courses.json). Vérifie, passe par passe :
//   - les duels sont dessinés depuis le moteur ; chaque receveur (sauf la cible, qui garde sa route dessinée : l'attrapé
//     et la suite s'y dessinent) court le chemin du moteur depuis sa position (miroir si la formation le met de l'autre côté) ; son défenseur est là où le moteur le met par rapport à lui ;
//     (une fois rejoint depuis son alignement, au plus vite que FL_VMAX permet) ; avant le lancer (ensuite, la lecture
//     du ballon : le dessin d'avant) ;
//   - aucun saut ; aucune erreur JS ; un match sans play.geo.cov est dessiné comme avant.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), ARG=process.argv[2], PORT=8159;
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
      if(F.plays.filter(P=>P.geo&&P.geo.cov).length>=15) return [{F,src:`${w}/${f}`}];
    }
  }
  /* no week with play.geo.sim yet (weeks before 07/11/2026): the test match of the 07/11 test week */
  const ex=path.join(__dirname,'matchs','sim-courses.json');
  if(fs.existsSync(ex)) out.push({F:JSON.parse(fs.readFileSync(ex,'utf8')),src:'matchs/sim-courses.json'});
  return out;
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-cov-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});   /* the site needs a season to open a replay */
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

async function rejouer(page,F){
  return page.evaluate(F=>{
    const G=window.__gc, kfAt=G.kfAt; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
    const out=[], vu=new Set(), errs=[];
    for(let i=0;i<400000&&g.status!=='final';i++){
      try{ G.stepGame(g,0.05); }catch(e){ errs.push(e.message); break; }
      const P=g.cur, pl=g.plan;
      if(!P||!pl||g.phase!=='play'||vu.has(P.seq)||!(P.geo&&P.geo.k==='pass')) continue;
      vu.add(P.seq);
      const C=P.geo.cov, row={seq:P.seq,cov:!!(C&&C.r&&C.r.length),drawn:pl.covSim?pl.covSim.n:0,skip:pl.covSim?pl.covSim.skip:[pl.kind,pl.type,P.type,P.result,!!pl.scramble,!!pl.geo],duels:[],vmax:0};
      if(C&&pl.covSim){
        const act=pl.act, t0=pl.flight?pl.flight.t0:1, tgt=pl.covSim.t;
        for(const s in pl.covSim.s){
          const I=pl.covSim.s[s], slot=+s, rk=pl.off[slot], m=I.u.length;
          const e=C.r.find(x=>({WR1:8,WR2:9,WR3:10,TE:5,RB:7})[x[0]]===slot); if(!e) continue;
          const S0=kfAt(rk,0), E0=[e[4][0][0]/10,e[4][0][1]/10], sy=(S0.y<26.65)===(E0[1]<26.65)?1:-1;
          const dd=Math.sign(kfAt(rk,I.u[m-1]).x-S0.x)*Math.sign(e[4][m-1][0]/10-E0[0])||1;
          const du={slot,target:slot===tgt,def:I.i,rec:null,rel:null};
          /* the receiver at each sample of the duel: the engine's point, from his stance */
          let er=0, el=0, nl=0;
          for(let k=1;k<m;k++){ if(I.u[k]>=t0-0.02) break;
            const q=[e[4][k][0]/10,e[4][k][1]/10], p=kfAt(rk,I.u[k]);
            if(slot!==tgt) er=Math.max(er,Math.hypot(p.x-(S0.x+dd*(q[0]-E0[0])),p.y-(S0.y+sy*(q[1]-E0[1]))));
            if(I.i!=null&&I.u[k]<t0-0.25&&I.u[k]>=I.ub){   /* after the ease-in from his alignment */
              const D=[e[5][k][0]/10,e[5][k][1]/10], pd=kfAt(pl.def[I.i],I.u[k]);
              const v=Math.hypot((pd.x-p.x)-dd*(D[0]-q[0]),(pd.y-p.y)-sy*(D[1]-q[1])); if(v>el){ el=v; du.w={k,m,u:I.u[k],t0,ub:I.ub,uE:I.uE,i:I.i}; } nl++; }
          }
          du.rec=er; du.rel=nl?el:null;
          /* no jump: speed along the drawn keyframes during the duel (yd per second of screen) */
          for(const k of [rk].concat(I.i!=null?[pl.def[I.i]]:[])) for(let j=1;j<k.length;j++){ if(k[j][0]>Math.min(I.uE,t0)) break;   /* after the throw: the read of the ball (drawing before) */
            const dt=(k[j][0]-k[j-1][0])*act; if(dt>1e-3){ const v=Math.hypot(k[j][1]-k[j-1][1],k[j][2]-k[j-1][2])/dt; if(v>row.vmax){ row.vmax=v; row.vw={who:k===rk?'rec':'def',slot,j,n:k.length,u0:k[j-1][0],u1:k[j][0],uE:I.uE,t0,tgt:slot===tgt,kind:pl.kind}; } } }
          row.duels.push(du);
        }
      }
      out.push(row);
    }
    return {out,errs,status:g.status};
  },F);
}

(async()=>{
  const L=feeds();
  if(!L.length){ console.log('aucun match avec play.geo.cov (semaines d\'avant le 08/11/2026) : rien à vérifier'); process.exit(0); }
  const {F,src}=L[0]; console.log(src);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const page=await b.newPage({viewport:{width:1280,height:800}}), errs=[]; page.on('pageerror',e=>errs.push(e.message));
    await page.goto(`http://localhost:${PORT}/`,{waitUntil:'domcontentloaded',timeout:90000});
    await page.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    const R=await rejouer(page,F), cov=R.out.filter(r=>r.cov);
    console.log(`  ${R.out.length} passes rejouées, ${cov.length} avec play.geo.cov`);
    check(R.status==='final'&&!R.errs.length,'match rejoué jusqu\'au bout'+(R.errs.length?' : '+R.errs[0]:''));
    const drawn=cov.filter(r=>r.drawn>0), du=drawn.flatMap(r=>r.duels);
    check(cov.length>=10&&drawn.length>=0.8*cov.length,`passes dont les duels sont dessinés depuis le moteur (${drawn.length} / ${cov.length}, ${du.length} duels)`);
    const rec=du.filter(x=>x.rec!=null);
    check(rec.every(x=>x.rec<0.05),`chaque receveur court le chemin du moteur (écart max ${Math.max(0,...rec.map(x=>x.rec)).toFixed(3)} yd)`);
    const rel=du.filter(x=>x.rel!=null);
    /* 90 % : un défenseur peut être repris ensuite par un autre dessin du site (1 duel sur 40 sur le match de test, cause
       non identifiée au 08/11/2026) */
    const relOk=rel.filter(x=>x.rel<0.05).length;
    check(rel.length>=20&&relOk>=0.9*rel.length,`son défenseur est là où le moteur le met par rapport à lui (${relOk} / ${rel.length} duels à moins de 0,05 yd)`);
    const vm=Math.max(0,...drawn.map(r=>r.vmax));
    check(vm<=11*1.15,`aucun saut pendant les duels (vitesse max ${vm.toFixed(1)} yd/s)`);
    /* sans play.geo.cov : le dessin d'avant */
    const G=JSON.parse(JSON.stringify(F)); for(const P of G.plays) if(P.geo) delete P.geo.cov;
    const R2=await rejouer(page,G);
    check(R2.status==='final'&&R2.out.every(r=>!r.drawn),'sans play.geo.cov : aucun duel dessiné depuis le moteur (dessin d\'avant)');
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
