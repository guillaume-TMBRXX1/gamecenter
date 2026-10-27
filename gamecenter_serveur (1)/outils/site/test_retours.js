// Coups d'envoi avec retour (bloc 2, étape 4 — 12/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_retours.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match avec retours de coups d'envoi : le dernier match de data/weeks qui
// a un touchback, un retour et si possible un touchdown sur retour ; sinon (semaines calculées avant les retours) un match
// réel dont les coups d'envoi reçoivent un retour (touchback, retour, grand retour, à tour de rôle).
// Vérifie : chaque coup d'envoi est joué (bannière TOUCHBACK / KICKOFF · RETURN n YDS / BIG RETURN, texte de l'action),
// touchdown sur retour (bannière, score = GameFeed), Match centre (retours par joueur = GameFeed, ligne « Kick return
// yards »), score final, aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8135;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feedAvecRetours(){
  const weeks=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse();
  let best=null;
  for(const w of weeks){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()){
      const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')), K=F.plays.map(P=>P.kick_return).filter(Boolean);
      if(!K.length) continue;
      const ok=K.some(k=>k.touchback)&&K.some(k=>!k.touchback&&!k.td);
      if(ok&&K.some(k=>k.td)) return {F,src:`${w}/${f} (réel, avec touchdown sur retour)`};
      if(ok&&!best) best={F,src:`${w}/${f} (réel)`};
    }
    if(best) return best;
  }
  const w=weeks[0], dir=path.join(WEEKS,w,'games'), f=fs.readdirSync(dir).sort()[0];
  const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
  let k=0;
  for(const P of F.plays) if(P.call.type==='kickoff'){
    const kind=k++%3, ret=kind===0?0:kind===1?24:47;
    P.kick_return={kick:66,landing:101,touchback:kind===0,return:ret,td:false};
    P.players=Object.assign({},P.players,{carrier:{id:null,name:kind===0?null:'Test Returner'}});
    P.text=kind===0?'Kickoff 66 yds · touchback':`Kickoff 66 yds · Test Returner returns ${ret}`;
  }
  return {F,src:`${w}/${f} (retours ajoutés)`};
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-retours-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecRetours();
  const K=F.plays.filter(P=>P.kick_return);
  console.log(`${src} · ${F.plays.length} actions · ${K.length} coups d'envoi (touchbacks ${K.filter(P=>P.kick_return.touchback).length}, touchdowns ${K.filter(P=>P.kick_return.td).length})`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const seen={}, out=[];
      for(let i=0;i<80000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05);
        const P=g.cur; if(!P||!P.kick_return||seen[P.seq]) continue;
        if(g.idx===g.plays.indexOf(P)&&g.phase!=='presnap'&&g.chip&&g.chip.t&&/KICKOFF|TOUCHBACK|RETURN|TOUCHDOWN/.test(g.chip.t)){
          seen[P.seq]=1; out.push({seq:P.seq,kr:P.kick_return,result:P.result,chip:g.chip.t,text:g.lastText,hs:g.hs,as:g.as,want:P.after.score}); }
      }
      const st=G.computeStats(g,g.plays.length), pl={};
      for(const s of ['home','away']) for(const k in st.pl[s]){ const x=st.pl[s][k]; if(x.kr) pl[s+':'+x.name]=x.kr; }
      return {out,status:g.status,hs:g.hs,as:g.as,team:{kr:st.team.home.kr+st.team.away.kr,kry:st.team.home.kry+st.team.away.kry},pl};
    },F);
    const C=R.out;
    console.log('   ',JSON.stringify(C.slice(0,3)).slice(0,400));
    check(C.length===K.length,`tous les coups d'envoi joués (${C.length} / ${K.length})`);
    const chip=x=>x.kr.td?'TOUCHDOWN':x.kr.touchback?'TOUCHBACK':x.kr.return>=40?`BIG RETURN · ${x.kr.return} YDS`:`KICKOFF · RETURN ${x.kr.return} YDS`;
    check(C.every(x=>x.chip===chip(x)),'bannière de chaque coup d\'envoi (touchback, retour, grand retour, touchdown)');
    check(C.every(x=>x.text===F.plays[x.seq-1].text),'texte de l\'action affiché');
    check(C.every(x=>x.hs===x.want.home&&x.as===x.want.away),'score après chaque coup d\'envoi = GameFeed');
    const ret=K.filter(P=>!P.kick_return.touchback);
    check(R.team.kr===ret.length&&R.team.kry===ret.reduce((a,P)=>a+P.kick_return.return,0),`Match centre : ${R.team.kr} retours, ${R.team.kry} yards`);
    const byName={}; for(const P of ret){ const n=(P.players.carrier||{}).name; if(n){ const k=P.offense+':'+n; byName[k]=(byName[k]||0)+P.kick_return.return; } }
    check(Object.keys(byName).length>0&&Object.entries(byName).every(([k,y])=>R.pl[k]&&R.pl[k].y===y),'retours par joueur = GameFeed');
    check(R.status==='final'&&R.hs===F.game.final_score.home&&R.as===F.game.final_score.away,`score final ${R.as}-${R.hs} = GameFeed`);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
