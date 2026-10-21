// La poche et la ligne offensive (moteur 12.2 vicies ter, étape 7.1 — 21/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_poche.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Prend le dernier match de data/weeks (ou une exhibition) dont les passes portent play.pocket (QB qui monte, qui sort et
// lance en courant, sack) ; sinon un match réel qui en reçoit à tour de rôle. Ne dépend pas de l'heure.
// Vérifie, sur le plan de chaque action (g.plan) : la ligne recule en fer à cheval (tackles plus profonds que le centre) ;
// poche propre : le QB reste à son drop ; step up : il avance ; escape : il sort de plusieurs yards sur le côté et le
// ballon part après sa sortie ; sack : c'est le rusher du duel perdu qui fait le sack ; play-by-play (« steps up »,
// « flushed …, throws on the run », « X beats Y ») ; stats d'équipe (« Throws on the run ») et des joueurs (duels de
// protection, pressions) ; commentateur ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8155;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pk=P=>P.pocket||{};
const num=v=>typeof v==='number'&&isFinite(v)?v:0;

function feeds(){
  const all=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  const ex=path.join(ROOT,'data','exhibitions');
  if(fs.existsSync(ex)) for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort().reverse()) all.push({file:path.join(ex,f),src:`exhibitions/${f}`});
  return all;
}
const duels=(o,d)=>{ const r=(i,pos)=>({id:`${d}_${pos}${i}`,name:`Rusher${pos}${i} ${pos==='EDGE'?'Edge':'Tackle'}${i}`,pos});
  const b=pos=>({id:`${o}_${pos}`,name:`Blocker ${pos}Man`,pos});
  return [{rusher:r(1,'EDGE'),blocker:b('LT'),side:'left',type:'edge',margin:4,free:false,double:false,t:2.4},
          {rusher:r(2,'EDGE'),blocker:b('RT'),side:'right',type:'edge',margin:-2,free:false,double:false,t:3.6},
          {rusher:r(1,'DT'),blocker:b('LG'),side:'left',type:'interior',margin:1,free:false,double:false,t:4.1},
          {rusher:r(2,'DT'),blocker:b('RG'),side:'right',type:'interior',margin:-8,free:false,double:true,t:5.0}]; };
function feedAvecPoche(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8')), P=F.plays.filter(p=>p.pocket&&!p.presnap);
    if(P.some(p=>pk(p).reaction==='step_up')&&P.some(p=>pk(p).on_run)&&P.some(p=>p.result==='sack'&&pk(p).beaten!=null)) return {F,src:src+' (réel)'};
  }
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show&&P.decision))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8')), H=F.game.home.abbr, A=F.game.away.abbr;
  let k=0;
  for(const P of F.plays){
    delete P.pocket;
    if(!P.call||P.call.type!=='pass'||P.presnap||P.conversion||!P.show||!P.decision||P.call.concept==='BOOT') continue;
    const o=P.offense==='home'?H:A, d=P.offense==='home'?A:H;
    const base={version:'poche-1',ttp:2.4,duels:duels(o,d)};
    if(P.result==='sack'){ P.pocket=Object.assign(base,{shape:'edge',beaten:0,reaction:'none',on_run:false}); }
    else if((P.result==='complete'||P.result==='incomplete')&&P.decision.action==='LANCER'&&num(P.decision.throw_time)>=2.3){   /* la poche ne cède qu'avant un lancer tardif */
      const m=k%3;
      P.pocket= m===0 ? Object.assign(base,{shape:'clean'})
              : m===1 ? Object.assign(base,{shape:'edge',beaten:0,reaction:'step_up',on_run:false})
                      : Object.assign(base,{shape:'collapse',beaten:0,reaction:'escape',side:'right',on_run:true});
      k++;
    }
  }
  F.game.pocket_model='poche-1';
  return {F,src:src+' (play.pocket ajouté)'};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-poche-'));
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecPoche();
  const K=F.plays.map((P,k)=>[P,k]).filter(([P])=>P.pocket);
  console.log(`${src} · ${K.length} passes avec la poche · step up ${K.filter(([P])=>pk(P).reaction==='step_up').length} · en courant ${K.filter(([P])=>pk(P).on_run).length} · sacks ${K.filter(([P])=>P.result==='sack'&&pk(P).beaten!=null).length}`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame();
      const at=(k,u)=>{ if(u<=k[0][0]) return {x:k[0][1],y:k[0][2]}; for(let i=1;i<k.length;i++){ const a=k[i-1],b=k[i]; if(u<=b[0]){ const t=(u-a[0])/((b[0]-a[0])||1); return {x:a[1]+(b[1]-a[1])*t,y:a[2]+(b[2]-a[2])*t}; } } const l=k[k.length-1]; return {x:l[1],y:l[2]}; };
      const out=[];
      F.plays.forEach((P,k)=>{ if(!P.pocket||P.presnap) return;
        G.rpSeek(g,k); g.paused=false; for(let i=0;i<5000;i++){ G.stepGame(g,0.01); if(g.phase==='play') break; }
        const pl=g.plan, d=g.poss==='home'?1:-1, L=g.los;
        const depth=i=>(L-at(pl.off[i],0.45).x)*d;
        const ol=[0,1,2,3,4].sort((a,b)=>pl.off[a][0][2]-pl.off[b][0][2]);
        const u0=pl.pocket?pl.pocket.u:0.42, q1=at(pl.off[6],Math.max(0.3,u0-0.01)), q2=at(pl.off[6],0.97);
        out.push({k,seq:P.seq,drawn:!!pl.pocket,pa:/PLAY_ACTION|BOOT|POP|^PA_/.test(String(P.call.concept||'')),shape:P.pocket.shape,reac:P.pocket.reaction||null,run:!!P.pocket.on_run,result:P.result,
          cup:Math.min(depth(ol[0]),depth(ol[4]))-depth(ol[2]),
          fwd:(q2.x-q1.x)*d, lat:Math.abs(q2.y-q1.y), release:pl.flight?pl.flight.t0:null, qbMoveU:pl.pocket&&pl.pocket.qbMove?pl.pocket.qbMove.u:null,
          sacker:pl.sacker!=null?pl.sacker:null, beatenSlot:pl.pocket?pl.pocket.beaten:null,
          text:G.rpFeedItem(g,P).text, line:(G.playLine(Object.assign({},g,{idx:k}),P)||{}).text||''});
      });
      const st=G.computeStats(g,F.plays.length);
      const pl=[...Object.values(st.pl.home),...Object.values(st.pl.away)];
      return {out,runs:F.plays.filter(P=>P.pocket&&P.pocket.on_run&&P.call&&P.call.type==='pass').length,ot:st.team.home.ot+st.team.away.ot,pb:pl.filter(x=>x.pb).length,prs:pl.filter(x=>x.prs).length};
    },F);
    const O=R.out, kind=f=>O.filter(f);
    const pass=kind(x=>x.result!=='sack'&&x.drawn);   /* BOOT : roulé dessiné à part, sans poche */
    check(pass.length&&pass.every(x=>x.cup>1.2),`la ligne forme un fer à cheval : tackles plus profonds que le centre (${pass.length}, min ${Math.min(...pass.map(x=>x.cup)).toFixed(1)} yd)`);
    const clean=kind(x=>x.shape==='clean'&&x.drawn&&!x.pa&&x.result!=='sack');   /* sack « rapide » de la résolution : dessiné comme avant */   /* play action : le QB fait son pas de côté */
    if(clean.some(x=>!(Math.abs(x.fwd)<1.0&&x.lat<1.0))) console.log('   ',JSON.stringify(clean.filter(x=>!(Math.abs(x.fwd)<1.0&&x.lat<1.0)).map(x=>({fwd:+x.fwd.toFixed(2),lat:+x.lat.toFixed(2),r:x.result,seq:x.seq}))));
    check(clean.length&&clean.every(x=>Math.abs(x.fwd)<1.0&&x.lat<1.0),`poche propre : le QB reste à son drop (${clean.length})`);
    const tot=kind(x=>(x.reac==='step_up'||x.run)&&x.result!=='sack'), tard=tot.filter(x=>x.qbMoveU!=null);   /* réception très précoce : pas le temps de bouger */
    check(tard.length>=tot.length/2,`le QB a le temps de réagir sur la plupart des passes (${tard.length}/${tot.length})`);
    const su=kind(x=>x.reac==='step_up'&&x.result!=='sack'&&x.qbMoveU!=null);
    if(su.some(x=>!(x.fwd>1.2))) console.log('   ',JSON.stringify(su.map(x=>({fwd:+x.fwd.toFixed(2),u:x.qbMoveU,rel:x.release}))));
    check(su.length&&su.every(x=>x.fwd>1.2),`step up : le QB avance dans la poche (${su.length})`);
    const es=kind(x=>x.run&&x.qbMoveU!=null);
    if(es.some(x=>!(x.lat>4&&x.release!=null&&x.release>=x.qbMoveU-0.03))) console.log('   ',JSON.stringify(es.map(x=>({lat:+x.lat.toFixed(1),rel:x.release,u:x.qbMoveU,res:x.result}))));
    check(es.length&&es.every(x=>x.lat>4&&x.release!=null&&x.release>=x.qbMoveU-0.03),`escape : le QB sort sur le côté, le ballon part après sa sortie (${es.length})`);
    const sk=kind(x=>x.result==='sack'&&x.shape!=='clean');
    check(sk.length&&sk.every(x=>x.sacker!=null&&x.sacker===x.beatenSlot),`sack : le rusher du duel perdu fait le sack (${sk.length})`);
    check(su.every(x=>/steps up in the pocket/.test(x.text))&&es.every(x=>/flushed (left|right), throws on the run/.test(x.text))&&sk.every(x=>/beats .*|collapses|unblocked/.test(x.text)),
      'play-by-play : « steps up », « flushed …, throws on the run », « X beats Y »');
    check(clean.every(x=>!/steps up|flushed|beats/.test(x.text)),'play-by-play : rien sur une poche propre');
    check(R.ot===R.runs&&R.pb>0&&R.prs>0,`stats : « Throws on the run » ${R.ot}, duels de protection (${R.pb} joueurs), pressions (${R.prs} joueurs)`);
    check(sk.every(x=>/gets home|untouched|collapses|brings him down|can't hold/.test(x.line))&&es.filter(x=>x.result==='complete'||x.result==='incomplete').every(x=>/on the run|on the move/.test(x.line)),
      'commentateur : le duel du sack, le lancer en courant');
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
