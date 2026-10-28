// Checks avant le snap (moteur 12.2 novodecies, play.presnap — 16/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_audibles.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match dont les actions portent play.presnap : le dernier de
// data/weeks ou des matchs de test (outils/site/matchs) qui en a au moins 3 audibles ; sinon un match réel qui reçoit des checks à tour de rôle
// (audible juste vers la course et vers la passe, mauvais audible contre une pression simulée, rotation cachée,
// motions avec rotation, « lock » en homme, « bump » en zone).
// Vérifie, action par action : le QB fait son check sur le terrain (« CHECK » au-dessus de lui pendant l'avant-snap) ;
// la défense montre d'abord sa boîte (boîte montrée), puis se décale jusqu'à la vraie au snap ; le joueur en motion
// traverse la formation avant le snap ; « lock » : un défenseur le suit ; le play-by-play raconte l'audible, le
// déguisement et la réponse à la motion ; une course qui sort du terrain part vers la touche dès le trou ; le match va
// au bout, sans erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8141;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  const all=[];
  const ex=path.join(__dirname,'matchs');
  if(fs.existsSync(ex)) for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort().reverse()) all.push({file:path.join(ex,f),src:`matchs/${f}`});
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  return all;
}
function feedAvecChecks(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    if(F.plays.filter(P=>P.presnap&&P.presnap.audible).length>=3&&F.plays.some(P=>P.presnap&&P.presnap.motion)) return {F,src:src+' (réel)'};
  }
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  const base={look:'neutral',box_shown:7,box_real:7,box_read:7,shell_shown:'1-high',shell_real:'1-high',read:null,audible:false,
              fooled:null,motion:null,motion_response:null,sec:0,clock:false};
  const S=[
    P=>({look:'loaded',box_shown:8,box_real:8,box_read:8,audible:true,sec:2,qb:'Test QB',from:{type:P.call.type==='run'?'pass':'run'},to:{type:P.call.type}}),
    P=>({look:'loaded',box_shown:9,box_real:7,box_read:9,read:'fooled',audible:true,fooled:'wrong_check',sec:2,qb:'Test QB',
         from:{type:P.call.type==='run'?'pass':'run'},to:{type:P.call.type}}),
    P=>({look:'neutral',box_shown:7,box_real:8,box_read:7,shell_shown:'2-high',read:'fooled',fooled:'missed_check'}),
    P=>({box_shown:8,box_real:8,box_read:8,motion:'jet',motion_response:'roll'}),
    P=>({motion:'jet',motion_response:'lock'}),
    P=>({motion:'orbit',motion_response:'bump'}),
  ];
  let k=0;
  for(const P of F.plays){
    const t=P.call&&P.call.type;
    if((t!=='run'&&t!=='pass')||P.conversion||!P.show||P.call.play_id==='KNEEL'||P.call.play_id==='SPIKE') continue;
    if(P.decision&&P.decision.action==='SCRAMBLE') continue;
    if(k%2===0){
      P.presnap=Object.assign({},base,S[(k/2)%S.length](P));
      if(P.run) P.run.box=P.presnap.box_real;               /* block F counts the same box */
      const pre=Math.max(num(P.show.pre),3.0); P.show.sec=+(P.show.sec+pre-P.show.pre).toFixed(2); P.show.pre=pre;
    }
    k++;
  }
  return {F,src:src+' (play.presnap ajouté)'};
}
function num(v,d){ return typeof v==='number'&&isFinite(v)?v:(d||0); }

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-audibles-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecChecks();
  const K=F.plays.filter(P=>P.presnap);
  console.log(`${src} · ${F.plays.length} actions · ${K.length} avec play.presnap (${K.filter(P=>P.presnap.audible).length} audibles, `+
              `${K.filter(P=>P.presnap.motion).length} motions)`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const out={}, oob=[], texts=[]; let lastF=null;
      const box=()=>{ const L=g.los, d=g.cur.offense==='home'?1:-1, by=g.bally; return g.def.filter(q=>(q.x-L)*d<7&&Math.abs(q.y-by)<=7.5).length; };
      for(let i=0;i<90000&&!(g.status==='final'&&g.paused);i++){
        const ph=g.phase, t0=g.t;
        G.stepGame(g,0.05);
        if(g.feed&&g.feed[0]&&g.feed[0]!==lastF){ lastF=g.feed[0]; texts.push(String(lastF.text||'')); }
        const P=g.cur;
        if(!P) continue;
        if(P.presnap&&g.phase==='presnap'&&g.ps){
          const o=out[P.seq]||(out[P.seq]={seq:P.seq,ps:P.presnap,dur:g.dur,bubble:0,shownBox:null,snapBox:null});
          if(G.psBubble(g)) o.bubble++;
          if(t0<0.9&&g.t>=0.9){ o.shownBox=box(); if(g.ps.mIdx!=null){ o.m0=g.off[g.ps.mIdx].y; if(g.ps.lock!=null) o.l0=g.def[g.ps.lock].y; } }
          if(g.t+0.05>=g.dur&&o.snapBox==null){ o.snapBox=box(); if(g.ps.mIdx!=null){ o.m1=g.off[g.ps.mIdx].y; if(g.ps.lock!=null) o.l1=g.def[g.ps.lock].y; } }
        }
        if(ph==='presnap'&&g.phase==='play'&&g.plan&&g.plan.type==='run'&&P.clock&&P.clock.oob&&P.result!=='touchdown'
           &&g.plan.carrier.some(c=>c[3]===7&&c[2]==='off')){
          const rb=g.plan.off[7], by=g.bally, ey=g.plan.spot.y, at=u=>{ for(let j=1;j<rb.length;j++) if(rb[j][0]>=u){ const a=rb[j-1], c=rb[j], v=(u-a[0])/Math.max(1e-6,c[0]-a[0]); return a[2]+(c[2]-a[2])*v; } return rb[rb.length-1][2]; };
          oob.push({seq:P.seq,by,ey,mid:at(0.6)});
        }
      }
      return {out:Object.values(out),oob,status:g.status,feed:texts};
    },F);
    const O=R.out;
    console.log(`   ${O.length} avant-snaps avec check rejoués`);
    check(O.length>=Math.min(6,K.length),'les avant-snaps avec check sont joués');
    const au=O.filter(o=>o.ps.audible), auKo=au.filter(o=>o.bubble<5);
    check(au.length>0&&!auKo.length,`audible : « CHECK » au-dessus du QB pendant l'avant-snap (${au.length-auKo.length} / ${au.length})`);
    const noAu=O.filter(o=>!o.ps.audible&&o.bubble>0);
    check(!noAu.length,'pas de « CHECK » sans audible');
    const dg=O.filter(o=>o.ps.box_shown!==o.ps.box_real||o.ps.motion_response==='roll');
    const want0=o=>o.ps.motion_response==='roll'?o.ps.box_real-1:o.ps.box_shown;
    const dgKo=dg.filter(o=>o.shownBox!==want0(o)||o.snapBox!==o.ps.box_real);
    if(dgKo.length) console.log('   boîtes :',JSON.stringify(dgKo.slice(0,6).map(o=>({seq:o.seq,montree:o.shownBox,veut:want0(o),snap:o.snapBox,reelle:o.ps.box_real,rep:o.ps.motion_response}))));
    check(dg.length>0&&dgKo.length<=Math.floor(dg.length*0.1),`la défense montre sa boîte puis se décale jusqu'à la vraie au snap (${dg.length-dgKo.length} / ${dg.length})`);
    const all=O.filter(o=>o.snapBox!=null&&o.ps.box_real), snKo=all.filter(o=>o.snapBox!==o.ps.box_real);
    check(snKo.length<=Math.floor(all.length*0.1),`au snap, autant de défenseurs dans la boîte que le moteur (${all.length-snKo.length} / ${all.length})`);
    const mo=O.filter(o=>o.ps.motion&&o.m0!=null&&o.m1!=null), moKo=mo.filter(o=>Math.abs(o.m1-o.m0)<5);
    check(mo.length>0&&!moKo.length,`motion : le joueur traverse la formation avant le snap (${mo.length-moKo.length} / ${mo.length})`);
    const lk=O.filter(o=>o.ps.motion_response==='lock'&&o.l0!=null), lkKo=lk.filter(o=>Math.abs(o.l1-o.l0)<4||Math.sign(o.l1-o.l0)!==Math.sign(o.m1-o.m0));
    check(!lk.length||!lkKo.length,`« lock » : un défenseur suit le joueur en motion (${lk.length-lkKo.length} / ${lk.length})`);
    const txt=R.feed.join('\n');
    check(/audible: .+ sees \d in the box and checks to a (run|pass)/.test(txt),'play-by-play : l\'audible du QB');
    if(K.some(P=>P.presnap.motion_response)) check(/(rolls a safety with the|travels with the|passes off the) \w+ motion/.test(txt),'play-by-play : la réponse à la motion');
    if(K.some(P=>P.presnap.fooled)) check(/(fooled: the defense showed|disguised: the defense showed) \d/.test(txt),'play-by-play : le déguisement qui a trompé le QB');
    const oKo=R.oob.filter(o=>Math.abs(o.mid-o.by)<0.3*Math.abs(o.ey-o.by)||Math.sign(o.mid-o.by)!==Math.sign(o.ey-o.by));
    if(oKo.length) console.log('   sorties :',JSON.stringify(oKo.slice(0,4)));
    check(!oKo.length,`course qui sort : le porteur part vers la touche dès le trou (${R.oob.length-oKo.length} / ${R.oob.length})`);
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
