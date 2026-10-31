// Transformation après un touchdown (bloc 2, étape 3 — 12/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_transformation.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match avec transformations : le dernier match de data/weeks qui en a, sinon
// (semaines calculées avant les transformations) un match réel où chaque touchdown est suivi d'une transformation ajoutée
// au GameFeed (point réussi, 2 points réussis, point raté, 2 points ratés, à tour de rôle ; scores recalculés).
// Vérifie : chaque transformation est jouée (bannière, texte de l'action, « EXTRA POINT » / « 2-PT TRY » à la place de
// l'essai), le score suit le GameFeed, aucune pause entre le touchdown et la transformation (try_follows), Match centre
// (lignes « Extra points » / « 2-pt conversions », kicker XP) = décompte du GameFeed, score final, aucune erreur JS.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8134;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CONV=['pat_good','pat_missed','two_point_good','two_point_failed'];

/* un match avec transformations : réel s'il y en a, sinon un match réel complété (scores recalculés) */
function feedAvecTransformations(){
  const weeks=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse();
  for(const w of weeks){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()){
      const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
      const kinds=new Set(F.plays.filter(P=>P.conversion).map(P=>P.result));
      if(kinds.has('pat_good')&&(kinds.has('two_point_good')||kinds.has('two_point_failed'))) return {F,src:`${w}/${f} (réel)`};
    }
  }
  const w=weeks[0], dir=path.join(WEEKS,w,'games');
  const f=fs.readdirSync(dir).sort().find(f=>JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')).plays.filter(P=>P.result==='touchdown').length>=4);
  const F=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')), plays=[], adj={home:0,away:0};
  const add=(s)=>({home:s.home+adj.home,away:s.away+adj.away});
  let k=0;
  for(const P of F.plays){
    if(P.result!=='touchdown'){ plays.push(Object.assign({},P,{after:Object.assign({},P.after,{score:add(P.after.score)})})); continue; }
    const kind=CONV[k++%4], o=P.offense, pts={pat_good:1,pat_missed:0,two_point_good:2,two_point_failed:0}[kind];
    const td=Object.assign({},P,{try_follows:true,after:Object.assign({},P.after,{status:'live',score:add(P.after.score)})});
    td.after.score[o]-=1;                                   /* le touchdown vaut 6, la transformation suit */
    const two=kind.startsWith('two'), goal=o==='home'?110:10, los=goal+(o==='home'?-1:1)*(two?2:15);
    td.after=Object.assign(td.after,{offense:o,los_x:los,down:null,to_go:null});
    plays.push(td);
    adj[o]+=pts-1;
    plays.push({seq:0,quarter:P.quarter,clock_start:P.clock_end,clock_end:P.clock_end,offense:o,los_x:los,ball_y:26.65,down:null,to_go:null,
      call:{type:two?'two_point':'extra_point',play_id:null,concept:null,formation:null,defense:{concept:null,formation:null}},
      result:kind,gain:kind==='two_point_good'?2:0,spot:{x:kind==='two_point_good'?goal:los,y:26.65},possession_change:'score',
      text:{pat_good:'Extra point good',pat_missed:'Extra point no good',two_point_good:'2-pt conversion good',two_point_failed:'2-pt try failed · pass incomplete'}[kind],
      highlight:null,players:{carrier:{id:null,name:null},defender:{name:null,credit:null}},
      after:Object.assign({},P.after,{score:add(P.after.score)}),win_prob_home:P.win_prob_home,odds:P.odds,tracks:null,
      conversion:{choice:two?'two_point':'extra_point',reason:'test',play:two?(k%2?'pass':'run'):'kick',good:pts>0,points:pts,p:two?.47:.94}});
  }
  plays.forEach((P,i)=>P.seq=i+1);
  F.plays=plays; F.game.final_score=Object.assign({},plays[plays.length-1].after.score);
  return {F,src:`${w}/${f} (transformations ajoutées)`};
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-transfo-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:'auto'}),stdio:'ignore'});   /* lundi 12:45 : page légère (≈ 85 Mo le vendredi soir) */
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecTransformations();
  const conv=F.plays.filter(P=>P.conversion);
  console.log(`${src} · ${F.plays.length} actions · ${conv.length} transformations (${CONV.map(k=>k+' '+conv.filter(P=>P.result===k).length).join(', ')})`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const seen={}, out={conv:[],brkAfterTd:[],scores:[]};
      for(let i=0;i<80000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05);
        const P=g.cur; if(!P) continue;
        if(P.conversion&&!seen[P.seq]){ seen[P.seq]={}; G.updateGameUI(g);
          const dd=[...document.querySelectorAll('#modal [data-f="dd"]')].map(e=>e.textContent).join('|');
          seen[P.seq].dd=dd; seen[P.seq].brk=g.brk?g.brk.kind:null; }
        if(P.conversion&&seen[P.seq]&&!seen[P.seq].done&&g.idx===g.plays.indexOf(P)&&g.phase!=='presnap'&&g.chip&&g.chip.t&&/POINT|2-PT/.test(g.chip.t)){
          seen[P.seq].done=true; out.conv.push({seq:P.seq,result:P.result,chip:g.chip.t,text:g.lastText,hs:g.hs,as:g.as,want:P.after.score,dd:seen[P.seq].dd,brk:seen[P.seq].brk}); }
        if(P.try_follows&&g.brk) out.brkAfterTd.push(P.seq);
      }
      const st=G.computeStats(g,g.plays.length).team, kick=G.computeStats(g,g.plays.length).pl;
      let xpa=0,xpm=0; for(const s of ['home','away']) for(const k in kick[s]){ const q=kick[s][k].kick; if(q){ xpa+=q.xa||0; xpm+=q.xm||0; } }
      return {out,status:g.status,hs:g.hs,as:g.as,team:{xpa:st.home.xpa+st.away.xpa,xpm:st.home.xpm+st.away.xpm,c2a:st.home.c2a+st.away.c2a,c2m:st.home.c2m+st.away.c2m},kick:{xpa,xpm}};
    },F);
    const C=R.out.conv, chipOf={pat_good:'EXTRA POINT · GOOD',pat_missed:'EXTRA POINT · NO GOOD',two_point_good:'2-PT CONVERSION',two_point_failed:'2-PT TRY FAILED'};
    console.log('   ',JSON.stringify(C.slice(0,3)).slice(0,400));
    check(C.length===conv.length,`toutes les transformations jouées (${C.length} / ${conv.length})`);
    check(C.every(c=>c.chip===chipOf[c.result]),'bannière de chaque transformation');
    check(C.every(c=>c.hs===c.want.home&&c.as===c.want.away),'score après chaque transformation = GameFeed');
    check(C.every(c=>c.text&&c.text===F.plays[c.seq-1].text),'texte de l\'action affiché');
    check(R.out.brkAfterTd.length===0,'aucune pause entre un touchdown et sa transformation');
    const n=k=>conv.filter(P=>P.result===k).length;
    check(R.team.xpa===n('pat_good')+n('pat_missed')&&R.team.xpm===n('pat_good'),`Match centre : extra points ${R.team.xpm}/${R.team.xpa}`);
    check(R.team.c2a===n('two_point_good')+n('two_point_failed')&&R.team.c2m===n('two_point_good'),`Match centre : 2-pt conversions ${R.team.c2m}/${R.team.c2a}`);
    const real=conv.some(P=>P.players&&P.players.carrier&&P.players.carrier.name);
    if(real) check(R.kick.xpa===R.team.xpa&&R.kick.xpm===R.team.xpm,`kicker : XP ${R.kick.xpm}/${R.kick.xpa}`);
    check(R.status==='final'&&R.hs===F.game.final_score.home&&R.as===F.game.final_score.away,`score final ${R.as}-${R.hs} = GameFeed`);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
