// Noms des joueurs sur le terrain (19/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_noms.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé un match de la dernière semaine sur le grand écran et vérifie, action par action :
// avant le snap, numéro et nom sous les WR, le TE et le RB (jamais le QB ni la ligne), pendant 1,8 s au plus, effacés
// avant le snap ; pendant l'action, le nom suit le porteur du ballon (remise ou réception) ; à la fin, le porteur avec
// son gain et le défenseur auteur de l'action (TACKLE, SACK, INT, PASS DEFENDED) ; rien sur les coups de pied ; rien sur
// les tuiles de l'accueil ni sur les transformations à 2 points ; le match va au bout, sans erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8147;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop(), dir=path.join(WEEKS,w,'games');
  for(const f of fs.readdirSync(dir).sort()){ const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
    const cr=new Set(F.plays.map(P=>P.players&&P.players.defender&&P.players.defender.credit).filter(Boolean));
    if(cr.has('INTERCEPTION')&&cr.has('SACK')&&cr.has('TACKLE')) return {F,src:`${w}/${f}`}; }
  const f=fs.readdirSync(dir).sort()[0]; return {F:JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')),src:`${w}/${f}`};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-noms-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feed(); console.log(`${src} · ${F.plays.length} actions`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const tuiles=await p.evaluate(()=>{ const G=window.__gc; let n=0; for(const v of G.views){ if(v.g&&v.g.plays) n++; } return n; });
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const pre={}, play={}, post={}, kick=[];
      for(let i=0;i<120000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05); const P=g.cur; if(!P) continue;
        const T=G.nameTags(g), k=P.seq;
        if(g.special){ if(T.length) kick.push(k); continue; }
        if(g.phase==='presnap'){ const o=pre[k]||(pre[k]={conv:!!P.conversion,max:0,qb:false,line:false,late:false,t0:null,t1:null,dur:g.dur,kn:P.call&&P.call.play_id});
          const r=T.filter(t=>t.kind==='roster'); o.max=Math.max(o.max,r.length);
          if(r.some(t=>t.idx===6)) o.qb=true; if(r.some(t=>t.idx<5)) o.line=true;
          if(r.length){ if(o.t0==null) o.t0=g.t; o.t1=g.t; if(g.t>g.dur-0.2) o.late=true; } }
        if(g.phase==='play'&&g.carrier&&g.carrier.side==='off'){ const o=play[k]||(play[k]={n:0,ok:0,res:P.result,conv:!!P.conversion});
          if(g.carrier.idx!==6){ o.n++; if(T.some(t=>t.kind==='ball'&&t.idx===g.carrier.idx)) o.ok++; } }
        if(g.phase==='post'&&!post[k]) post[k]={res:P.result,gain:P.gain,credit:P.players&&P.players.defender&&P.players.defender.credit,
          def:T.find(t=>t.kind==='def')||null,ball:T.find(t=>t.kind==='ball')||null};
      }
      return {pre:Object.values(pre),play:Object.values(play),post:Object.values(post),kick,status:g.status};
    },F);
    const pr=R.pre.filter(o=>!o.conv&&o.kn!=='KNEEL'&&o.kn!=='SPIKE'&&o.dur>1.2);
    if(!pr.every(o=>o.max>=3)) console.log('   ',JSON.stringify(pr.filter(o=>o.max<3)));
    check(pr.length>20&&pr.every(o=>o.max>=3),`avant le snap : noms sous les WR, le TE et le RB (${pr.filter(o=>o.max>=3).length} / ${pr.length} avant-snaps)`);
    check(!R.pre.some(o=>o.qb||o.line),'jamais le QB ni la ligne offensive');
    check(!R.pre.some(o=>o.late),'effacés avant le snap');
    check(pr.every(o=>o.t1==null||o.t1-o.t0<=1.85),'affichés 1,8 s au plus');
    const pl=R.play.filter(o=>o.n>5&&!o.conv), plKo=pl.filter(o=>o.ok<o.n*0.95);
    if(plKo.length) console.log('   ',JSON.stringify(plKo));
    check(pl.length>20&&!plKo.length,`pendant l'action : le nom suit le porteur du ballon (${pl.length-plKo.length} / ${pl.length})`);
    const cp=R.post.filter(o=>o.res==='complete'||o.res==='run'), cpKo=cp.filter(o=>!o.ball||!/^[+−]\d+$/.test(o.ball.sub));
    check(cp.length>20&&cpKo.length<=cp.length*0.05,`fin d'action : le porteur avec son gain (${cp.length-cpKo.length} / ${cp.length})`);
    const lab={TACKLE:'TACKLE',SACK:'SACK',INTERCEPTION:'INT',PASS_DEFENDED:'PASS DEFENDED'};
    for(const [cr,l] of Object.entries(lab)){ const x=R.post.filter(o=>o.credit===cr), ko=x.filter(o=>!o.def||o.def.sub!==l);
      if(x.length) check(ko.length<=x.length*0.05,`fin d'action : « ${l} » et le nom du défenseur (${x.length-ko.length} / ${x.length})`); }
    const td=R.post.filter(o=>o.res==='touchdown'&&o.ball); if(td.length) check(td.every(o=>o.ball.sub==='TD'),'touchdown : « TD » à côté du nom');
    check(!R.kick.length,'rien sur les coups de pied');
    check(tuiles>0,`tuiles de l'accueil présentes (${tuiles}) — les noms n'y sont dessinés que sur le grand écran (this===modalView)`);
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
