// Dessin naturel des actions (section 83 du README, 30/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_actions.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé (60 images par seconde d'écran), sur le grand écran, trois matchs de la dernière semaine qui
// ont une interception, et mesure ce que voit le spectateur :
//   - passes : le ballon quitte le QB avant l'attrapé et reste en l'air FL_MIN s d'écran au moins ;
//   - après la réception (hors sortie en touche) : le receveur file droit (écart latéral / yards vers l'avant) ;
//   - interception : le retour ne part pas vers le centre du terrain sans raison ;
//   - réception de 20 yards et plus : un défenseur est sur le receveur quand il s'arrête ;
//   - aucun saut : vitesse d'un joueur d'une image à l'autre ;
//   - interrupteur (GC_JEU_FLUIDE=0, ici par le crochet de test) : le dessin d'avant revient ;
//   - aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8165;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop(), dir=path.join(WEEKS,w,'games'), out=[];
  for(const f of fs.readdirSync(dir).sort()){
    const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
    if(F.plays.length&&F.plays.some(P=>P.result==='interception')) out.push({F,src:`${w}/${f}`});
    if(out.length===3) break;
  }
  return out;
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-actions-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

/* in the page: replay a whole feed and measure every scrimmage play */
function measure([F,on]){
  const G=window.__gc; G.fluide(on); G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
  const MIDY=26.65, H=1/60, out=[]; let rec=null;
  const fin=()=>{ if(!rec) return; const r=rec; rec=null; const P=r.P, pl=r.plan;
    if(!pl||pl.frames||pl.type==='kick') return;
    const o={seq:P.seq,res:P.result,kind:pl.kind,gain:P.gain,oob:!!(P.clock&&P.clock.oob)}, d=P.offense==='home'?1:-1;
    if(pl.flight) o.flight=(pl.flight.t1-pl.flight.t0)*r.dur;
    const last=pl.carrier[pl.carrier.length-1];
    if(last){ const side=last[2], idx=last[3], sd=side==='off'?d:-d;
      const pts=r.fr.filter(z=>z.t>=last[0]*r.dur-1e-9).map(z=>{ const c=z[side][idx]; return {x:c.x,y:c.y,opp:Math.min(...z[side==='off'?'def':'off'].map(q=>Math.hypot(q.x-c.x,q.y-c.y)))}; });
      if(pts.length>2){ const A=pts[0], Z=pts[pts.length-1]; let ks=pts.length-1; while(ks>0&&Math.hypot(pts[ks-1].x-Z.x,pts[ks-1].y-Z.y)<0.25) ks--;
        const S=pts[ks]; o.fwd=(S.x-A.x)*sd; o.lat=S.y-A.y; o.mid=Math.abs(A.y-MIDY)-Math.abs(S.y-MIDY); o.opp=S.opp; } }
    let v=0; for(let i=1;i<r.fr.length;i++){ const a=r.fr[i-1], b=r.fr[i], dt=b.t-a.t||H;
      for(const s of ['off','def']) for(let k=0;k<11;k++) v=Math.max(v,Math.hypot(b[s][k].x-a[s][k].x,b[s][k].y-a[s][k].y)/dt); }
    o.vmax=v; out.push(o); };
  for(let i=0;i<400000&&!(g.status==='final'&&g.paused)&&g.phase!=='done';i++){
    const ph=g.phase; G.stepGame(g,ph==='play'?H:(g.pause>0?0.5:0.1));
    if(ph!=='play'&&g.phase==='play'){ fin(); rec={P:g.cur,plan:g.plan,dur:g.dur,fr:[]}; }
    if(g.phase==='play'&&rec) rec.fr.push({t:g.t,off:g.off.map(p=>({x:p.x,y:p.y})),def:g.def.map(p=>({x:p.x,y:p.y}))});
    if(ph==='play'&&g.phase!=='play') fin();
  }
  fin(); G.fluide(true);
  return {plays:out,status:g.status};
}

(async()=>{
  const L=feeds();
  if(!L.length){ console.log('aucun match avec une interception dans la dernière semaine'); process.exit(1); }
  console.log(L.map(x=>x.src).join(' · '));
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1280,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
    check(await p.evaluate(()=>window.__gc.fluide())===true,'dessin naturel actif par défaut');
    const on=[], off=[];
    for(const {F} of L){ const a=await p.evaluate(measure,[F,true]); on.push(...a.plays); check(a.status==='final','match rejoué jusqu\'au bout');
                         const z=await p.evaluate(measure,[F,false]); off.push(...z.plays); }
    const fl=on.filter(o=>o.flight!=null&&['comp','inc','int'].includes(o.kind));
    console.log(`   ${on.length} actions, ${fl.length} passes`);
    const minF=Math.min(...fl.map(o=>o.flight));
    check(fl.length>20&&minF>=0.3,`chaque passe se voit partir : vol le plus court ${minF.toFixed(2)} s (≥ 0,3 s ; 0,42 s visé)`);
    const C=on.filter(o=>o.kind==='comp'&&o.res==='complete'&&!o.oob&&o.fwd>=4);
    const r=C.map(o=>Math.abs(o.lat)/o.fwd).sort((a,b)=>a-b), r90=r.length?r[Math.floor(r.length*0.9)]:0;
    check(C.length>5&&r90<=0.3,`après la réception, le receveur file droit : écart latéral / yards vers l'avant ${r90.toFixed(2)} (90e centile, ≤ 0,3) sur ${C.length} réceptions`);
    const I=on.filter(o=>o.kind==='int'&&o.fwd!=null), Im=I.filter(o=>o.mid>3&&Math.abs(o.lat)>o.fwd*0.6);
    check(I.length>0&&Im.length<=Math.ceil(I.length*0.25),`interception : retour vers l'en-but adverse, pas vers le centre (${I.length-Im.length} / ${I.length})`);
    const Lg=on.filter(o=>o.kind==='comp'&&o.res==='complete'&&!o.oob&&o.gain>=15&&o.opp!=null), Lk=Lg.filter(o=>o.opp>3);
    check(!Lg.length||Lk.length<=Math.ceil(Lg.length*0.25),`réception de 15 yards et plus : un défenseur sur le receveur à l'arrêt (${Lg.length-Lk.length} / ${Lg.length})`);
    const V=on.map(o=>o.vmax).sort((a,b)=>a-b), v99=V[Math.floor(V.length*0.99)], vmx=V[V.length-1];
    check(v99<=40&&vmx<=120,`aucun saut : vitesse d'un joueur ${v99.toFixed(1)} yd/s au 99e centile (≤ 40), ${vmx.toFixed(1)} au plus (≤ 120)`);
    const flOff=off.filter(o=>o.flight!=null&&['comp','inc','int'].includes(o.kind)), bad=flOff.filter(o=>o.flight<=0).length;
    check(off.length===on.length&&(bad>0||Math.min(...flOff.map(o=>o.flight))<0.3),`interrupteur coupé : le dessin d'avant (${bad} passes attrapées avant le lancer, comme avant)`);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
