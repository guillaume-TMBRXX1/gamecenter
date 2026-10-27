// Appel de jeu qui apprend (moteur 12.2 vicies semel, play.scout — 19/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_scouting.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match dont les actions portent play.scout : une exhibition ou le dernier
// match de data/weeks qui a au moins 3 lectures et 1 cassure ; sinon un match réel qui en reçoit à tour de rôle
// (lecture juste et fausse, de la course et de la passe, tendance cassée par un play action et par une course).
// Ne dépend pas de l'heure : le match est rejoué de bout en bout, quel que soit le match à l'antenne.
// Vérifie, action par action : « KEY · RUN / PASS » au-dessus d'un défenseur dans la boîte pendant l'avant-snap d'une
// lecture (jamais sans lecture) ; « BREAK · … » au-dessus du QB quand l'attaque casse sa tendance (sauf pendant son
// CHECK) ; la puce du résultat (« · READ », « · BURNED », « · BROKE TENDENCY ») ; le play-by-play (lecture et sa preuve,
// « read it » / « burned » …, cassure) ; le commentateur (journal play.adjust et fin d'action) ; le match va au bout,
// sans erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8149;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const num=(v,d)=>typeof v==='number'&&isFinite(v)?v:(d||0);

function feeds(){
  const all=[];
  const ex=path.join(ROOT,'data','exhibitions');
  if(fs.existsSync(ex)) for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort().reverse()) all.push({file:path.join(ex,f),src:`exhibitions/${f}`});
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  return all;
}
function feedAvecScouting(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    const S=F.plays.filter(P=>P.scout);
    if(S.filter(P=>P.scout.def).length>=3&&S.some(P=>P.scout.off&&P.scout.off.broke)) return {F,src:src+' (réel)'};
  }
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  let k=0;
  for(const P of F.plays){
    const t=P.call&&P.call.type;
    if((t!=='run'&&t!=='pass')||P.conversion||!P.show||P.call.play_id==='KNEEL'||P.call.play_id==='SPIKE'||P.presnap) continue;
    if(P.decision&&P.decision.action==='SCRAMBLE') continue;
    if(k%3===0){
      const dt=P.offense==='home'?'away':'home', right=(k/3)%2===0, key=right?t:(t==='run'?'pass':'run');
      P.scout={version:'scouting-1',def:{team:dt,key,family:null,conf:0.75,why:`6 of 7 ${key}s on 1st down`,right}};
      if((k/3)%4===1) P.scout.off={team:P.offense,tendency:t==='run'?'pass':'run',played:t,broke:true,
        kind:t==='pass'?'pa':'pass_down_run',same_formation:false,why:'5 of 6 on 1st down'};
    }
    k++;
  }
  const P0=F.plays.find(P=>P.scout&&P.scout.def);
  if(P0) P0.adjust=(P0.adjust||[]).concat([{team:P0.scout.def.team,side:'defense',kind:'scout_key',label:P0.scout.def.key.toUpperCase(),
    text:'Keys on the '+P0.scout.def.key,reason:P0.scout.def.why}]);
  return {F,src:src+' (play.scout ajouté)'};
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-scouting-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecScouting();
  const K=F.plays.filter(P=>P.scout);
  console.log(`${src} · ${F.plays.length} actions · ${K.filter(P=>P.scout.def).length} lectures, `+
              `${K.filter(P=>P.scout.off&&P.scout.off.broke).length} cassures`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const out={};
      for(let i=0;i<150000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05); const P=g.cur; if(!P) continue;
        const o=out[P.seq]||(out[P.seq]={seq:P.seq,sc:P.scout||null,key:0,keyBox:0,brk:0,brkQb:0,chk:0,other:0});
        if(g.phase==='presnap'){
          for(const x of G.scBubbles(g)){
            if(x.side==='def'){ o.key++; const q=g.def[x.i], dx=(q.x-g.los)*(g.cur.offense==='home'?1:-1);
              if(dx>=2.5&&dx<=8&&x.text==='KEY · '+(P.scout.def.key==='run'?'RUN':'PASS')) o.keyBox++; }
            else { o.brk++; if(x.i===6&&/^BREAK · /.test(x.text)) o.brkQb++; }
          }
          if(G.psBubble(g)) o.chk++;
        }
      }
      const plays=g.plays||[];
      const lignes=plays.filter(P=>P.scout).map(P=>({seq:P.seq,sc:P.scout,chip:G.rpChip(P).t,feed:G.rpFeedItem(g,P).text,
        play:(G.playLine(g,P)||{}).text||'',adj:(G.adjLine(g,P)||{}).text||'',adjust:(P.adjust||[]).map(a=>a.kind),
        ok:(()=>{ const r=P.result; if(r==='touchdown') return true; if(['interception','fumble_lost','sack','incomplete'].includes(r)) return false;
          if(/1st down/i.test(String(P.text||''))) return true; const tg=Number(P.to_go)||10; return (Number(P.gain)||0)>=tg*(P.down===1?0.4:P.down===2?0.6:1); })(),
        res:P.result}));
      return {out:Object.values(out),lignes,status:g.status};
    },F);
    const O=R.out.filter(o=>o.sc);
    const kd=O.filter(o=>o.sc.def), kdKo=kd.filter(o=>o.key<5||o.keyBox<o.key*0.9);
    if(kdKo.length) console.log('   lectures :',JSON.stringify(kdKo.slice(0,4)));
    check(kd.length>=3&&kdKo.length<=Math.floor(kd.length*0.1),`lecture : « KEY · RUN / PASS » au-dessus d'un défenseur de la boîte pendant l'avant-snap (${kd.length-kdKo.length} / ${kd.length})`);
    check(!R.out.some(o=>!(o.sc&&o.sc.def)&&o.key>0),'pas de « KEY » sans lecture');
    const br=O.filter(o=>o.sc.off&&o.sc.off.broke&&!o.chk), brKo=br.filter(o=>o.brk<3||o.brkQb<o.brk);
    check(br.length>=1&&!brKo.length,`cassure : « BREAK » au-dessus du QB avant le snap (${br.length-brKo.length} / ${br.length})`);
    check(!R.out.some(o=>!(o.sc&&o.sc.off&&o.sc.off.broke)&&o.brk>0),'pas de « BREAK » sans cassure');
    check(!R.out.some(o=>o.chk&&o.brk&&o.sc&&o.sc.off),'le CHECK du QB garde la priorité sur « BREAK »');
    const L=R.lignes;
    const chipKo=L.filter(l=>{ const d=l.sc.def, o=l.sc.off;
      if(!/RUN|PASS|1ST DOWN|SACK|INCOMPLETE|TOUCHDOWN|INTERCEPTED|FUMBLE/.test(l.chip.replace(/ · (READ|BURNED|BROKE TENDENCY)$/,''))) return false;
      const want=d&&d.right&&!l.ok?' · READ':d&&!d.right&&l.ok?' · BURNED':o&&o.broke&&l.ok?' · BROKE TENDENCY':'';
      return want?!l.chip.endsWith(want):/ · (READ|BURNED|BROKE TENDENCY)$/.test(l.chip); });
    if(chipKo.length) console.log('   puces :',JSON.stringify(chipKo.slice(0,4).map(l=>({seq:l.seq,chip:l.chip,ok:l.ok,sc:l.sc}))));
    check(!chipKo.length,`puce du résultat : « READ », « BURNED », « BROKE TENDENCY » (${L.length-chipKo.length} / ${L.length})`);
    const fd=L.filter(l=>l.sc.def), fdKo=fd.filter(l=>{ const d=l.sc.def;
      const pr=`keyed on the ${d.key==='run'?'run':'pass'} (${d.why}`, i=l.feed.indexOf(pr);   /* + « incl. N of their own » (film) */
      return i<0||!/^( incl\. \d+ of their own)?\)/.test(l.feed.slice(i+pr.length))||
        !l.feed.includes(d.right?(l.ok?'right guess, beaten anyway':'read it'):(l.ok?'burned':'wrong guess')); });
    if(fdKo.length) console.log('   play-by-play :',JSON.stringify(fdKo.slice(0,3).map(l=>l.feed)));
    check(fd.length>0&&!fdKo.length,`play-by-play : la lecture, sa preuve et son issue (${fd.length-fdKo.length} / ${fd.length})`);
    const fb=L.filter(l=>l.sc.off&&l.sc.off.broke&&!l.adjust.includes('scout_break'));
    check(fb.every(l=>/ break their tendency \(/.test(l.feed)),`play-by-play : la tendance cassée (${fb.length})`);
    const ak=L.filter(l=>l.adjust.includes('scout_key')||l.adjust.includes('scout_break'));
    check(ak.length>0&&ak.every(l=>/keying on the|know what's coming|break their tendency|Tendency breaker/.test(l.adj)),`commentateur : lecture et cassure du journal (${ak.length})`);
    const bu=L.filter(l=>l.sc.def&&!l.sc.def.right&&l.ok&&l.res!=='touchdown');
    if(bu.length) check(bu.every(l=>/got burned|Wrong guess/.test(l.play)),`commentateur : la défense trompée (${bu.length})`);
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
