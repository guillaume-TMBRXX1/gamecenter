// Horloge continue, chrono des 40 s, temps morts (moteur/ecran.py, 14/10/2026) — test navigateur (Playwright, crochet de test).
//   node outils/site/test_horloge.js [GameFeed avec l'horloge réelle]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match de l'horloge réelle (par défaut : la dernière exhibition dont les
// actions portent play.clock) auquel moteur/ecran.py ajoute play.show s'il n'y est pas.
// Vérifie : avant un snap où l'horloge tournait, elle descend en continu de show.c0 à clock_start (jamais de saut) et le
// chrono des 40 s descend jusqu'à la valeur du snap ; horloge arrêtée : elle ne bouge pas avant le snap ; pendant
// l'action, elle s'écoule du temps de jeu ; temps morts : bannière TIMEOUT et un trait de moins sous l'équipe ; la durée
// rejouée = la somme des temps d'écran + les pauses (≈ 15 min) ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn,execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), PORT=8139;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  let file=process.argv[2];
  if(!file){ const ex=path.join(ROOT,'data','exhibitions');
    for(const f of fs.readdirSync(ex).filter(f=>f.startsWith('exh-')).sort().reverse()){
      const F=JSON.parse(fs.readFileSync(path.join(ex,f),'utf8')); if(F.plays.some(P=>P.clock&&P.clock.timeouts)){ file=path.join(ex,f); break; } } }
  if(!file) throw new Error('aucun GameFeed avec l\'horloge réelle');
  const out=execFileSync('python3',['-c',`import json,sys; sys.path.insert(0,'.'); from moteur import ecran
F=json.load(open(sys.argv[1]))
if not all(p.get('show') for p in F['plays']):
    for p,c in zip(F['plays'], ecran.chronologie(F['plays'])): p['show']=c
print(json.dumps(F))`,file],{cwd:ROOT,maxBuffer:64<<20}).toString();
  return {F:JSON.parse(out),src:path.relative(ROOT,file)};
}

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-horloge-'));
  fs.cpSync(path.join(ROOT,'data','weeks'),path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feed();
  const want=F.plays.reduce((a,P)=>a+P.show.sec,0);
  console.log(`${src} · ${F.plays.length} actions · temps d'écran ${(want/60).toFixed(2)} min (+ pauses)`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.route(`http://localhost:${PORT}/`,async r=>{ const res=await r.fetch(); let t=await res.text();
      t=t.replace('rpSeek,replayGame','rpSeek,clockNow,playClockNow,replayGame'); r.fulfill({response:res,body:t}); });
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const dt=0.05, per={}, tos=[], chips=[]; let T=0, lastPh=null, lastSeq=null;
      for(let i=0;i<60000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,dt); T+=dt;
        const P=g.cur; if(!P||!P.show) continue;
        const o=per[P.seq]||(per[P.seq]={seq:P.seq,pre:[],play:[],pc:[],snapPc:null});
        if(g.status==='live'&&g.phase==='presnap'){ o.pre.push(G.clockNow(g)); const v=G.playClockNow(g); if(v!=null) o.pc.push(v); }
        if(g.status==='live'&&g.phase==='play'){ o.play.push(G.clockNow(g)); if(o.snapPc==null) o.snapPc=G.playClockNow(g); }
        if(g.phase==='presnap'&&P.show.to&&!chips.includes(P.seq)&&g.chip&&/TIMEOUT/.test(g.chip.t)){ chips.push(P.seq);
          const el=document.querySelector(`[data-g="${g.id}"][data-f="${P.show.to==='home'?'toH':'toA'}"]`);
          tos.push({seq:P.seq,side:P.show.to,on:el?el.querySelectorAll('i.on').length:null,want:g.tos?g.tos[P.show.to]:null}); }
      }
      return {per:Object.values(per),T,status:g.status,chips,tos};
    },F);
    const by={}; for(const o of R.per) by[o.seq]=o;
    const runs=F.plays.filter(P=>P.show.c0>P.clock_start&&by[P.seq]&&by[P.seq].pre.length>3);
    const mono=runs.filter(P=>{ const a=by[P.seq].pre; return a.every((x,i)=>i===0||x<=a[i-1]+1e-9)&&Math.abs(a[0]-P.show.c0)<=2&&Math.abs(a[a.length-1]-P.clock_start)<=2; });
    check(runs.length>20&&mono.length===runs.length,`horloge qui tourne avant le snap : continue, de c0 au snap (${mono.length} / ${runs.length})`);
    const stops=F.plays.filter(P=>P.show.c0===P.clock_start&&by[P.seq]&&by[P.seq].pre.length>3);
    check(stops.length>20&&stops.every(P=>by[P.seq].pre.every(x=>Math.abs(x-P.clock_start)<1e-6)),`horloge arrêtée : immobile avant le snap (${stops.length} actions)`);
    const plays=F.plays.filter(P=>by[P.seq]&&by[P.seq].play.length>3&&P.show.pt>0);
    check(plays.every(P=>{ const a=by[P.seq].play; return a[0]<=P.clock_start+1e-6&&a[a.length-1]>=P.clock_start-P.show.pt-1e-6&&a.every((x,i)=>i===0||x<=a[i-1]+1e-9); }),
      `pendant l'action, l'horloge s'écoule du temps de jeu (${plays.length} actions)`);
    const pcs=F.plays.filter(P=>P.show.pc&&by[P.seq]&&by[P.seq].pc.length>3);
    check(pcs.length>50&&pcs.every(P=>{ const a=by[P.seq].pc; return a[0]<=P.show.pc[0]&&a[0]>=P.show.pc[0]-3&&a.every((x,i)=>i===0||x<=a[i-1])&&by[P.seq].snapPc===P.show.pc[1]; }),
      `chrono des 40 s : il descend jusqu'à la valeur du snap (${pcs.length} actions)`);
    const nTo=F.plays.filter(P=>P.show.to).length;
    check(R.chips.length===nTo,`temps morts : bannière TIMEOUT (${R.chips.length} / ${nTo})`);
    check(R.tos.every(x=>x.on===x.want),'temps morts restants sous l\'équipe = moteur'+(R.tos.length?` (ex. ${R.tos[0].side} ${R.tos[0].on})`:''));
    const brk=10*2+40, rejoue=R.T;
    console.log(`    rejoué en ${(rejoue/60).toFixed(2)} min (attendu ${((want+brk)/60).toFixed(2)} min, écran final compris)`);
    check(Math.abs(rejoue-(want+brk))<=30,'durée rejouée = temps d\'écran + pauses');
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
