// Jeu de course dessiné (moteur bloc F, 12.2 quindecies — 14/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_courses.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match dont les courses portent play.run (box, side, hole, read,
// contact) : le dernier de data/weeks ou des exhibitions ; sinon un match réel dont les courses reçoivent un play.run à
// tour de rôle (8 et 9 dans la boîte, boîte légère, cutback, rebond, bloquée, plaquage cassé).
// Vérifie, course par course : au snap, autant de défenseurs dans la boîte (moins de 7 yards de la ligne, ± 7,5 yards du
// ballon) que le moteur ; le porteur passe par le côté choisi (gauche / droite de l'attaque) ; cutback : il finit de
// l'autre côté du trou ; rebond : il passe plus large que le trou ; le plaqueur (anneau rouge) est sur le porteur à la
// fin de l'action et il est du bon niveau (ligne, linebackers, secondaire) ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8138;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feedAvecCourses(){
  const all=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  const ex=path.join(ROOT,'data','exhibitions');
  if(fs.existsSync(ex)) for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort()) all.push({file:path.join(ex,f),src:`exhibitions/${f}`});
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    const K=F.plays.filter(P=>P.run&&P.call.side!=null);   /* feeds made before the lateral alignment (14/10) are skipped */
    const ok=K.filter(P=>P.call.side===(P.run.side==='left'?-1:1)*(P.offense==='home'?1:-1));
    if(K.length>=15&&ok.length===K.length) return {F,src:src+' (réel)'};
  }
  const {file,src}=all[0], F=JSON.parse(fs.readFileSync(file,'utf8'));
  const R=[{box:8,read:'designed',hole:'tight',contact:'second level'},{box:9,read:'stuffed',hole:'closed',contact:'line'},
           {box:6,read:'cutback',hole:'tight',contact:'secondary'},{box:7,read:'bounce',hole:'open',contact:'second level'},
           {box:7,read:'broken_tackle',hole:'closed',contact:'second level'}];
  let k=0;
  for(const P of F.plays) if(P.call.type==='run'&&(P.result==='run')&&!(P.decision&&P.decision.action==='SCRAMBLE')){
    const r=R[k%R.length]; k++;
    const d=P.offense==='home'?1:-1, cs=P.call.side===1||P.call.side===-1?P.call.side:(k%2?-1:1);
    P.call.side=cs;                                          /* the engine's side (11.6) = the block F side */
    P.run=Object.assign({side:cs*d<0?'left':'right',front:'OVER',tackler:null,key_block:null},r);
    const by=typeof P.ball_y==='number'?P.ball_y:26.65, off=Math.max(1.5,Math.abs(P.spot.y-by));
    P.spot.y=r.read==='cutback'?by-cs*off:by+cs*off;          /* cutback: the run ends on the other side */
  }
  return {F,src:src+' (play.run ajouté)'};
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-courses-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecCourses();
  const K=F.plays.filter(P=>P.run);
  console.log(`${src} · ${F.plays.length} actions · ${K.length} courses du bloc F`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const out={}, rec=P=>out[P.seq]||(out[P.seq]={seq:P.seq,run:P.run,td:P.result==='touchdown'});
      for(let i=0;i<90000&&!(g.status==='final'&&g.paused);i++){
        const P0=g.cur, ph=g.phase;
        G.stepGame(g,0.05);
        const P=g.cur;
        if(P&&P.run&&ph==='presnap'&&g.phase==='play'&&g.plan&&g.plan.type==='run'){   /* the snap */
          const o=rec(P), L=g.los, d=P.offense==='home'?1:-1, by=g.bally, pl=g.plan;
          o.box=g.def.filter(q=>(q.x-L)*d<7&&Math.abs(q.y-by)<=7.5).length;
          const rb=pl.off[7], at=t=>{ for(let j=1;j<rb.length;j++) if(rb[j][0]>=t) return rb[j]; return rb[rb.length-1]; };
          o.side=Math.sign(pl.hole-by)||0; o.by=by; o.hole=pl.hole;
          o.ys=rb.map(q=>q[2]); o.end=pl.spot; o.stop=pl.stop?{i:pl.stop.i,at:pl.stop.at}:null;
          o.carrier7=pl.carrier.some(c=>c[3]===7&&c[2]==='off'); o.dl=null;
        }
        if(P0&&P0.run&&ph==='play'&&g.phase!=='play'&&out[P0.seq]&&!out[P0.seq].fin){   /* the end of the play */
          const o=out[P0.seq], st=g.plan&&g.plan.stop;
          o.fin=true;
          if(o.stop){ const t=g.def[o.stop.i], c=g.plan.spot; o.dist=Math.hypot(t.x-c.x,t.y-c.y); }
        }
      }
      return {out:Object.values(out),status:g.status};
    },F);
    const C=R.out.filter(o=>o.box!=null&&o.carrier7);
    console.log(`   ${C.length} courses du porteur dessinées (sur ${K.length})`);
    check(C.length>=Math.min(10,K.length),'les courses sont jouées');
    const boxKo=C.filter(o=>o.box!==o.run.box);
    check(!boxKo.length,`défenseurs dans la boîte au snap = moteur`+(boxKo.length?` : ${boxKo.length} écarts (ex. ${boxKo[0].box} ≠ ${boxKo[0].run.box})`:''));
    const sideKo=C.filter(o=>{ const d=F.plays[o.seq-1].offense==='home'?1:-1, want=(o.run.side==='left'?-1:1)*d; return o.side!==want; });
    check(sideKo.length<=Math.ceil(C.length*0.05),`le trou est du côté choisi (gauche / droite de l'attaque) : ${C.length-sideKo.length} / ${C.length}`);
    const cb=C.filter(o=>o.run.read==='cutback'), cbKo=cb.filter(o=>Math.sign(o.end.y-o.by)===o.side&&Math.abs(o.end.y-o.by)>0.5);
    check(!cb.length||!cbKo.length,`cutback : le porteur finit de l'autre côté du trou (${cb.length-cbKo.length} / ${cb.length})`);
    const bo=C.filter(o=>o.run.read==='bounce'), boKo=bo.filter(o=>Math.max(...o.ys.map(y=>Math.abs(y-o.by)))<Math.abs(o.hole-o.by)+3&&!o.ys.some(y=>y<=3.5||y>=49.8))   /* or out to the touchline */;
    if(boKo.length) console.log('   rebond:',JSON.stringify(boKo.map(o=>({by:o.by,hole:o.hole,ys:o.ys.map(y=>+y.toFixed(1)),end:o.end}))));
    check(!bo.length||!boKo.length,`rebond : le porteur passe plus large que le trou (${bo.length-boKo.length} / ${bo.length})`);
    const tk=C.filter(o=>!o.td&&o.run.contact), tkKo=tk.filter(o=>!o.stop||o.dist==null||o.dist>2.5);
    check(tk.length>0&&tkKo.length<=Math.ceil(tk.length*0.05),`le plaqueur (anneau rouge) est sur le porteur à la fin : ${tk.length-tkKo.length} / ${tk.length}`);
    const lvl={line:[0,1,2,3,4,5,8],'second level':[4,5,8],secondary:[6,7,9,10]};
    const lvKo=tk.filter(o=>o.stop&&!lvl[o.run.contact].includes(o.stop.i));
    check(!lvKo.length,`le plaqueur est du bon niveau (ligne, linebackers, secondaire)`+(lvKo.length?` : ${lvKo.length} écarts`:''));
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
