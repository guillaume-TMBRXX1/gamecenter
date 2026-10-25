// Les pénalités pendant l'action (moteur 12.2 vicies quater, étape 7.2 — 21/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_penalites.js [dossier data/weeks] [gamefeed.json]     (depuis « gamecenter_serveur (1) »)
// Prend le dernier match de data/weeks (ou le GameFeed donné) dont des actions portent play.penalty ; sinon un match réel
// où des drapeaux sont ajoutés (holding sur une course, interférence sur une passe incomplète, roughing après une passe
// complétée, drapeau refusé). Ne dépend pas de l'heure.
// Vérifie : l'action annulée est dessinée comme elle a été jouée (pas de gain sous le nom du porteur) ; le drapeau jaune
// part au moment de la faute, sur le joueur qui l'a commise, et la puce « FLAG » s'allume ; puis l'appel de l'arbitre
// (puce, play-by-play « PENALTY on … — no play », « Flag: … — declined ») ; stats (« Penalties (yards) », fiche joueur,
// l'action annulée ne compte pas) ; commentateur ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), FEED=process.argv[3], PORT=8157;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  const all=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  return all;
}
const NOMS={offensive_holding:'Offensive holding',defensive_holding:'Defensive holding',defensive_pass_interference:'Pass interference',
  roughing_the_passer:'Roughing the passer'};
function feedAvecDrapeaux(){
  if(FEED) return {F:JSON.parse(fs.readFileSync(FEED,'utf8')),src:path.basename(FEED)+' (réel)'};
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    if(F.plays.some(p=>p.penalty&&p.result==='penalty')&&F.plays.some(p=>p.penalty&&!p.penalty.accepted)) return {F,src:src+' (réel)'};
  }
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show&&P.decision))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  const R={}; for(const s of ['home','away']) R[s]=F.game[s].roster||[];
  const de=P=>P.offense==='home'?'away':'home';
  const joueur=(side,pos)=>{ const r=R[side].find(x=>x.pos===pos)||R[side][0]; return {id:r.id,name:r.name,pos:r.pos,number:r.number}; };
  const pen=(P,type,team,player,acc,extra)=>Object.assign({version:'penalites-1',type,name:NOMS[type],team,player,chooser:team==='offense'?'defense':'offense',
    accepted:acc,declined:!acc,wp:{accept:0.4,decline:0.5}},extra||{});
  const vus=new Set(); let n=0;
  for(const P of F.plays){
    if(!P.call||P.presnap||P.conversion||!P.show||P.after.status!=='live'||(P.down||0)<1) continue;
    const t=P.call.type, r=P.result, before={result:r,gain:P.gain,text:String(P.text||'').replace(' · 1st down','')};
    const yl=P.offense==='home'?P.los_x-10:110-P.los_x;
    if(t==='run'&&r==='run'&&P.gain>=4&&!vus.has('hold')&&n%4===0){
      P.penalty=pen(P,'offensive_holding','offense',joueur(P.offense,'LT'),true,{yards:10,nullified:true,auto_first:false,replay_down:true,after:{yl:yl-10,down:P.down,togo:P.to_go+10},play_before:before});
      P.result='penalty'; P.gain=-10; P.text='Holding, 10 yds'; P.highlight=null; vus.add('hold');
    } else if(t==='pass'&&r==='incomplete'&&P.decision&&P.decision.action==='LANCER'&&!vus.has('dpi')){
      const c=(P.decision.coverer)||joueur(de(P),'CB');
      P.penalty=pen(P,'defensive_pass_interference','defense',{id:c.id,name:c.name,pos:c.pos||'CB'},true,{yards:18,nullified:true,auto_first:true,replay_down:false,after:{yl:yl+18,down:1,togo:10},play_before:before});
      P.result='penalty'; P.gain=18; P.text='Pass interference, 18 yds'; vus.add('dpi');
    } else if(t==='pass'&&r==='complete'&&P.decision&&P.decision.action==='LANCER'&&P.gain>0&&!vus.has('rough')){
      P.penalty=pen(P,'roughing_the_passer','defense',joueur(de(P),'DT'),true,{yards:15,nullified:false,auto_first:true,replay_down:false,after:{yl:yl+P.gain+15,down:1,togo:10}});
      vus.add('rough');
    } else if(t==='pass'&&r==='complete'&&P.gain>0&&vus.has('rough')&&!vus.has('dec')){
      P.penalty=pen(P,'defensive_holding','defense',joueur(de(P),'S'),false); vus.add('dec');
    }
    n++;
  }
  F.game.penalty_model='penalites-1';
  return {F,src:src+' (play.penalty ajouté)'};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-pen-'));
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecDrapeaux();
  const K=F.plays.filter(P=>P.penalty);
  console.log(`${src} · ${K.length} drapeaux · acceptés ${K.filter(P=>P.penalty.accepted).length} · annulées ${K.filter(P=>P.result==='penalty').length} · refusés ${K.filter(P=>!P.penalty.accepted).length}`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame();
      const at=(k,u)=>{ if(!k||!k.length) return null; if(u<=k[0][0]) return {x:k[0][1],y:k[0][2]}; for(let i=1;i<k.length;i++){ const a=k[i-1],b=k[i]; if(u<=b[0]){ const t=(u-a[0])/((b[0]-a[0])||1); return {x:a[1]+(b[1]-a[1])*t,y:a[2]+(b[2]-a[2])*t}; } } const l=k[k.length-1]; return {x:l[1],y:l[2]}; };
      const out=[];
      F.plays.forEach((P,k)=>{ if(!P.penalty) return;
        G.rpSeek(g,k); g.paused=false; g.speed=1;
        for(let i=0;i<5000;i++){ G.stepGame(g,0.01); if(g.phase==='play') break; }
        const pl=g.plan, fl=pl&&pl.flag, o={k,seq:P.seq,type:P.penalty.type,acc:P.penalty.accepted,nul:P.result==='penalty',call:P.call.type,
          before:(P.penalty.play_before||{}).result||null,kind:pl&&pl.kind,flag:!!fl,at:fl?fl.at:null,side:fl?fl.side:null};
        if(fl){ let chipAt=null, pos=null;
          for(let i=0;i<8000;i++){ G.stepGame(g,0.01); if(g.phase!=='play') break;
            if(fl.shown&&chipAt==null){ chipAt=g.t/g.dur; const tr=(fl.side==='off'?pl.off:pl.def)[fl.idx]; pos=at(tr,fl.at); o.flagXY=[fl.x,fl.y]; } }
          o.chipAt=chipAt; o.chipMid=null; o.dist=pos&&o.flagXY?Math.hypot(o.flagXY[0]-pos.x,o.flagXY[1]-pos.y):null; }
        for(let i=0;i<5000&&g.phase==='play';i++) G.stepGame(g,0.01);
        for(let i=0;i<40;i++) G.stepGame(g,0.01);
        o.chip=g.chip?{t:g.chip.t,c:g.chip.c}:null;
        const tags=G.nameTags(g)||[], ball=tags.find(t=>t.kind==='ball');
        o.ballSub=ball?ball.sub:null;
        o.text=G.rpFeedItem(g,P).text; o.line=(G.playLine(Object.assign({},g,{idx:k}),P)||{}).text||'';
        out.push(o);
      });
      const st=G.computeStats(g,F.plays.length);
      const exp={home:{n:0,y:0},away:{n:0,y:0}};
      let runs=0, att=0;
      F.plays.forEach(P=>{ const q=P.penalty; if(q&&q.accepted){ const s=q.team==='offense'?P.offense:(P.offense==='home'?'away':'home'); exp[s].n++; exp[s].y+=q.yards; }
        if(P.result==='penalty'||P.conversion||!P.call) return; if(P.call.type==='run') runs++; if(P.call.type==='pass'&&P.result!=='sack') att++; });
      const plp=[...Object.values(st.pl.home),...Object.values(st.pl.away)].filter(x=>x.pen);
      return {out,team:{home:[st.team.home.pen,st.team.home.peny],away:[st.team.away.pen,st.team.away.peny]},exp,
        runs,att,rushAtt:st.team.home.rushAtt+st.team.away.rushAtt,passAtt:st.team.home.passAtt+st.team.away.passAtt,plp:plp.length};
    },F);
    const O=R.out, nul=O.filter(x=>x.nul), dec=O.filter(x=>!x.acc), add=O.filter(x=>x.acc&&!x.nul);
    check(nul.length>0&&dec.length>0,`des actions annulées (${nul.length}) et des drapeaux refusés (${dec.length})`);
    const kinds={run:['run','scramble'],incomplete:['inc'],complete:['comp'],sack:['sack'],touchdown:['comp','run','scramble']};
    check(nul.every(x=>!kinds[x.before]||kinds[x.before].includes(x.kind)),`l'action annulée est dessinée comme elle a été jouée (${nul.map(x=>x.before+'→'+x.kind).join(', ')})`);
    check(nul.every(x=>!x.ballSub),'action annulée : pas de gain sous le nom du porteur');
    const fl=O.filter(x=>x.flag);
    check(fl.length===O.length&&fl.every(x=>x.side===(/^offensive_/.test(x.type)?'off':'def')),`un drapeau par faute, du bon côté (${fl.length}/${O.length})`);
    check(fl.every(x=>x.chipAt!=null&&x.chipAt>=x.at-1e-6&&x.chipAt<x.at+0.05),'le drapeau part au moment de la faute (puce « FLAG »)');
    if(fl.some(x=>!(x.dist!=null&&x.dist<3.5))) console.log('   ',JSON.stringify(fl.map(x=>({t:x.type,d:x.dist&&+x.dist.toFixed(1)}))));
    check(fl.every(x=>x.dist!=null&&x.dist<3.5),'le drapeau tombe près du joueur qui a commis la faute');
    check(nul.every(x=>x.chip&&x.chip.c==='flag'&&/^FLAG · .+ · \d+ YDS · (REPEAT DOWN|1ST DOWN)$/.test(x.chip.t)),`puce : l'appel de l'arbitre (${nul.map(x=>x.chip&&x.chip.t).slice(0,2).join(' | ')})`);
    check(dec.every(x=>x.chip&&/FLAG DECLINED$/.test(x.chip.t))&&add.every(x=>x.chip&&x.chip.c==='flag'&&/\+\d+ ROUGHING THE PASSER$/.test(x.chip.t)),'puce : « FLAG DECLINED », « +15 ROUGHING THE PASSER »');
    check(nul.every(x=>/^PENALTY on \w+: .+, (offense|defense), .+(repeat (1st|2nd|3rd|4th) down|automatic first down) — no play/.test(x.text))
      &&dec.every(x=>/· Flag: .+ — declined/.test(x.text))&&add.every(x=>/^PENALTY on \w+: Roughing the passer, defense, .+ — /.test(x.text)),
      'play-by-play : « PENALTY on … — no play », « Flag: … — declined »');
    if(O.some(x=>!x.line)) console.log('   ',JSON.stringify(O.filter(x=>!x.line)));
    check(O.every(x=>x.line)&&nul.every(x=>/[Ff]lag|interference|roughing|holding|illegal contact/i.test(x.line))&&dec.every(x=>/declined/.test(x.line)),'commentateur : le drapeau, le refus');
    check(R.team.home[0]===R.exp.home.n&&R.team.away[0]===R.exp.away.n&&R.team.home[1]===R.exp.home.y&&R.team.away[1]===R.exp.away.y&&R.plp>0,
      `stats : « Penalties (yards) » ${R.team.away[0]} (${R.team.away[1]}) / ${R.team.home[0]} (${R.team.home[1]}), fiche joueur (${R.plp})`);
    check(R.rushAtt===R.runs&&R.passAtt===R.att,`stats : l'action annulée ne compte pas (courses ${R.rushAtt}/${R.runs}, passes ${R.passAtt}/${R.att})`);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
