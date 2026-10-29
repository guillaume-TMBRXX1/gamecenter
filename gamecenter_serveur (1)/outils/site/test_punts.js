// Punts avec retour (moteur 12.2 sexdecies — 14/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_punts.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match avec punts retournés : le dernier match de data/weeks (ou des
// matchs de test, outils/site/matchs) qui a un retour et une autre issue (fair catch, ballon arrêté…) ; sinon (semaines calculées avant les
// retours de punt) un match réel dont les punts reçoivent une issue à tour de rôle (retour, fair catch, ballon arrêté,
// sortie, touchback, grand retour).
// Vérifie : chaque punt est joué (bannière PUNT · RETURN n YDS / FAIR CATCH / DOWNED / OUT OF BOUNDS / TOUCHBACK /
// BIG RETURN / PUNT RETURN TOUCHDOWN, texte de l'action), le ballon finit au point du GameFeed (porté par le retourneur
// ou qui roule), le score suit le GameFeed (touchdown sur retour compris), Match centre (retours par joueur = GameFeed,
// ligne « Punt return yards »), score final, aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8137;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  const out=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) out.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  const ex=path.join(__dirname,'matchs');
  if(fs.existsSync(ex)) for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort()) out.push({file:path.join(ex,f),src:`matchs/${f}`});
  return out;
}
function feedAvecPunts(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8')), K=F.plays.map(P=>P.punt_return).filter(Boolean);
    if(K.some(k=>k.result==='return')&&K.some(k=>k.result!=='return')) return {F,src:src+' (réel)'};
  }
  const {file,src}=all[0], F=JSON.parse(fs.readFileSync(file,'utf8'));
  const kinds=['return','fair_catch','downed','out_of_bounds','touchback','return'];
  let k=0;
  for(const P of F.plays) if(P.call.type==='punt'&&P.result==='punt'){
    const res=kinds[k%kinds.length], ret=res!=='return'?0:k%kinds.length===5?34:9; k++;
    const d=P.offense==='home'?1:-1, net=d*(num(P.spot.x)-num(P.los_x));
    P.punt_return={kick:Math.max(1,Math.round(net)+ret),landing:0,result:res,return:ret,td:false,catch:0,pinned:false,
                   returner:{id:null,name:res==='return'||res==='fair_catch'?'Test Returner':null}};
    P.text=res==='return'?`Punt ${P.punt_return.kick} yds · Test Returner returns ${ret}`:`Punt ${P.punt_return.kick} yds · `+
      {fair_catch:'fair catch Test Returner',downed:'downed',out_of_bounds:'out of bounds',touchback:'touchback'}[res];
  }
  return {F,src:src+' (issues ajoutées)'};
}
function num(v){ return typeof v==='number'&&isFinite(v)?v:0; }

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-punts-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecPunts();
  const K=F.plays.filter(P=>P.punt_return);
  const n=r=>K.filter(P=>P.punt_return.result===r).length;
  console.log(`${src} · ${F.plays.length} actions · ${K.length} punts (retours ${n('return')}, fair catches ${n('fair_catch')}, `+
              `arrêtés ${n('downed')}, sorties ${n('out_of_bounds')}, touchbacks ${n('touchback')}, touchdowns ${K.filter(P=>P.punt_return.td).length})`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const seen={}, out=[];
      for(let i=0;i<90000&&!(g.status==='final'&&g.paused);i++){
        const before=g.cur, ph=g.phase;
        G.stepGame(g,0.05);
        /* the ball at the end of the punt (last frame of the play, before the resolution) */
        if(before&&before.punt_return&&ph==='play'&&g.phase!=='play'&&!seen['b'+before.seq]){ seen['b'+before.seq]=1;
          out.push({seq:before.seq,ball:{x:g.ball.x,y:g.ball.y},spot:before.spot,kind:'ball'}); }
        const P=g.cur; if(!P||!P.punt_return||seen[P.seq]) continue;
        if(g.idx===g.plays.indexOf(P)&&g.phase!=='presnap'&&g.chip&&g.chip.t&&/PUNT|TOUCHBACK|RETURN/.test(g.chip.t)){
          seen[P.seq]=1; out.push({seq:P.seq,pr:P.punt_return,chip:g.chip.t,text:g.lastText,hs:g.hs,as:g.as,want:P.after.score,kind:'chip'}); }
      }
      const st=G.computeStats(g,g.plays.length), pl={};
      for(const s of ['home','away']) for(const k in st.pl[s]){ const x=st.pl[s][k]; if(x.pnr) pl[s+':'+x.name]=x.pnr; }
      return {out,status:g.status,hs:g.hs,as:g.as,team:{n:st.team.home.pnr+st.team.away.pnr,y:st.team.home.pnry+st.team.away.pnry},pl};
    },F);
    const C=R.out.filter(x=>x.kind==='chip'), B=R.out.filter(x=>x.kind==='ball');
    console.log('   ',JSON.stringify(C.slice(0,3)).slice(0,400));
    check(C.length===K.length,`tous les punts joués (${C.length} / ${K.length})`);
    const chip=x=>{ const r=x.pr, y=r.return;
      if(r.td) return 'PUNT RETURN TOUCHDOWN';
      if(r.result==='return') return y>=30?`BIG RETURN · ${y} YDS`:`PUNT · RETURN ${y} YDS`;
      return 'PUNT · '+{fair_catch:'FAIR CATCH',downed:'DOWNED',out_of_bounds:'OUT OF BOUNDS',touchback:'TOUCHBACK'}[r.result]; };
    const bad=C.filter(x=>x.chip!==chip(x));
    check(!bad.length,'bannière de chaque punt (retour, fair catch, arrêté, sortie, touchback, grand retour, touchdown)'+(bad.length?' : '+bad[0].chip+' ≠ '+chip(bad[0]):''));
    check(C.every(x=>x.text===F.plays[x.seq-1].text),'texte de l\'action affiché');
    check(C.every(x=>x.hs===x.want.home&&x.as===x.want.away),'score après chaque punt = GameFeed');
    const tb=new Set(K.filter(P=>P.punt_return.result==='touchback').map(P=>P.seq));   /* touchback: dead in the end zone, spotted at the 20 */
    const loin=B.filter(x=>!tb.has(x.seq)&&Math.abs(x.ball.x-x.spot.x)>2.5);
    check(B.length===K.length&&!loin.length,`le ballon finit au point du GameFeed (${B.length-tb.size} punts hors touchbacks)`+(loin.length?` : action ${loin[0].seq}, ${loin[0].ball.x.toFixed(1)} ≠ ${loin[0].spot.x}`:''));
    const ret=K.filter(P=>P.punt_return.result==='return');
    check(R.team.n===ret.length&&R.team.y===ret.reduce((a,P)=>a+P.punt_return.return,0),`Match centre : ${R.team.n} retours de punt, ${R.team.y} yards`);
    const byName={}; for(const P of ret){ const nm=(P.punt_return.returner||{}).name; if(nm){ const k=(P.offense==='home'?'away':'home')+':'+nm; byName[k]=(byName[k]||0)+P.punt_return.return; } }
    check(Object.keys(byName).length>0&&Object.entries(byName).every(([k,y])=>R.pl[k]&&R.pl[k].y===y),'retours par joueur = GameFeed (équipe qui reçoit)');
    check(R.status==='final'&&R.hs===F.game.final_score.home&&R.as===F.game.final_score.away,`score final ${R.as}-${R.hs} = GameFeed`);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
