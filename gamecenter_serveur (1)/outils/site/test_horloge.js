// Horloge, chrono d'avant-snap de 10 s, temps morts (moteur/ecran.py ecran-3 du 16/10/2026 : rythme rapide, < 25 min ;
// ecran-2 du 15/10 : temps réel ; ecran-1 : 14/10)
// — test navigateur (Playwright, crochet de test).
//   node outils/site/test_horloge.js [GameFeed avec l'horloge réelle]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé, sur le grand écran, un match de l'horloge réelle (par défaut : le dernier match de test (outils/site/matchs) dont les
// actions portent play.clock) auquel moteur/ecran.py ajoute play.show s'il n'y est pas.
// Vérifie : avant un snap où l'horloge tournait, elle descend en continu de show.c0 à clock_start (jamais de saut) et le
// chrono des 40 s descend jusqu'à la valeur du snap ; horloge arrêtée : elle ne bouge pas avant le snap ; pendant
// l'action, elle s'écoule du temps de jeu ; TEMPS RÉEL : quand elle tourne, elle perd 1 s par seconde rejouée ; chrono
// des 10 s ; sortie du terrain : l'action finit sur la touche ; temps morts : bannière TIMEOUT, décompte « TO :15 » à la place du chrono et un trait de moins sous
// l'équipe ; la durée rejouée = la somme des temps d'écran + les pauses (< 30 min) ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn,execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), PORT=8139;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  let file=process.argv[2];
  if(!file){ const ex=path.join(__dirname,'matchs');
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
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(path.join(ROOT,'data','weeks'),path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:'auto'}),stdio:'ignore'});   /* lundi 12:45 : page légère (le vendredi soir, ≈ 85 Mo, le navigateur tombe en réécrivant la page) */
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
      const dt=0.05, per={}, tos=[], chips=[], rates=[], ends=[]; let T=0, last=null;
      for(let i=0;i<60000&&!(g.status==='final'&&g.paused);i++){
        const ph0=g.phase, P0=g.cur;
        G.stepGame(g,dt); T+=dt;
        if(ph0==='play'&&g.phase==='post'&&P0&&(P0.result==='complete'||P0.result==='run'))   /* where the play ends */
          ends.push({seq:P0.seq,oob:!!(P0.clock&&P0.clock.oob),y:g.ball.y});
        const P=g.cur; if(!P||!P.show) continue;
        if(g.status==='live'&&g.pause<=0){ const c=G.clockNow(g), k=P.seq+'|'+g.phase;   /* the clock's rate, inside a phase */
          if(last&&last.k===k&&last.c>c) rates.push((last.c-c)/dt); last={k,c}; } else last=null;
        const o=per[P.seq]||(per[P.seq]={seq:P.seq,pre:[],play:[],pc:[],snapPc:null});
        if(g.status==='live'&&g.phase==='presnap'){ o.pre.push(G.clockNow(g)); const v=G.playClockNow(g); if(v!=null) o.pc.push(v); }
        if(g.status==='live'&&g.phase==='play'){ o.play.push(G.clockNow(g)); if(o.snapPc==null) o.snapPc=G.playClockNow(g); }
        if(g.phase==='presnap'&&P.show.to&&!chips.includes(P.seq)&&g.chip&&/TIMEOUT/.test(g.chip.t)){ chips.push(P.seq);
          const el=document.querySelector(`[data-g="${g.id}"][data-f="${P.show.to==='home'?'toH':'toA'}"]`);
          const pc=document.querySelector(`[data-g="${g.id}"][data-f="pc"]`);
          tos.push({seq:P.seq,side:P.show.to,on:el?el.querySelectorAll('i.on').length:null,want:g.tos?g.tos[P.show.to]:null,pc:pc?pc.textContent:null}); }
      }
      return {per:Object.values(per),T,status:g.status,chips,tos,rates,ends};
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
      `chrono d'avant-snap : il descend jusqu'à la valeur du snap (${pcs.length} actions)`);
    const nTo=F.plays.filter(P=>P.show.to).length;
    check(R.chips.length===nTo,`temps morts : bannière TIMEOUT (${R.chips.length} / ${nTo})`);
    check(R.tos.every(x=>x.on===x.want),'temps morts restants sous l\'équipe = moteur'+(R.tos.length?` (ex. ${R.tos[0].side} ${R.tos[0].on})`:''));
    const rt=F.plays.every(P=>P.show.rt===1), v3=((F.game||{}).broadcast||{}).version==='ecran-3';
    if(v3){   /* ecran-3 (16/10/2026): fast rhythm, the clock may run faster than real time but not too fast */
      check(R.tos.length>0&&R.tos.every(x=>/^TO :1[45]$/.test(x.pc||'')),`temps mort : décompte de 15 s à la place du chrono (${R.tos.map(x=>x.pc).slice(0,3).join(', ')})`);
      const fast=R.rates.filter(r=>r>3.2), med=R.rates.slice().sort((a,b)=>a-b)[R.rates.length>>1];
      check(R.rates.length>500&&!fast.length&&med<=2.2,`l'horloge n'accélère pas trop : ${med.toFixed(2)} s de match par seconde (médiane), ${fast.length} pas au-delà de 3,2`);
      check(F.plays.every(P=>!P.show.pc||P.show.pc[0]===10),'chrono d\'avant-snap de 10 s');
      const ob=R.ends.filter(e=>e.oob), out=ob.filter(e=>e.y<0.8||e.y>52.5);
      check(ob.length>0&&out.length>=Math.ceil(ob.length*0.8),`sortie du terrain : le porteur / receveur finit sur la touche (${out.length} / ${ob.length})`);
    }
    if(rt){
      check(R.tos.length>0&&R.tos.every(x=>/^TO :1[45]$/.test(x.pc||'')),`temps mort : décompte de 15 s à la place du chrono (${R.tos.map(x=>x.pc).slice(0,3).join(', ')})`);
      /* a step that ends a run of the clock (the play's time is up, the snap) loses less: at most one per phase */
      const ok=R.rates.filter(r=>Math.abs(r-1)<0.02), fast=R.rates.filter(r=>r>1.02);
      check(R.rates.length>1000&&!fast.length&&ok.length>=R.rates.length-2*F.plays.length,`temps réel : l'horloge perd 1 s par seconde quand elle tourne (${ok.length} / ${R.rates.length} pas, ${fast.length} trop rapides)`);
      check(F.plays.every(P=>!P.show.pc||P.show.pc[0]===10),'chrono d\'avant-snap de 10 s');
      const ob=R.ends.filter(e=>e.oob), out=ob.filter(e=>e.y<0.8||e.y>52.5);
      check(ob.length>0&&out.length>=Math.ceil(ob.length*0.8),`sortie du terrain : le porteur / receveur finit sur la touche (${out.length} / ${ob.length})`);
    }
    const brk=10*2+40, rejoue=R.T;
    console.log(`    rejoué en ${(rejoue/60).toFixed(2)} min (attendu ${((want+brk)/60).toFixed(2)} min, écran final compris)`);
    check(Math.abs(rejoue-(want+brk))<=30,'durée rejouée = temps d\'écran + pauses');
    if(rt) check(rejoue<30*60,'match rejoué en moins de 30 min');
    if(v3) check(rejoue<25*60,'match rejoué en moins de 25 min');
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
