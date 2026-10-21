// Mémoire d'une semaine à l'autre (moteur 12.2 vicies bis, idée 6 — 21/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_memoire.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Prend le dernier match de data/weeks (ou une exhibition) dont des lectures viennent du film (play.scout.def.film) avec
// une cassure « on tape » et un rapport d'avant-match (game.scout_film) ; sinon un match réel qui en reçoit à tour de rôle.
// Ne dépend pas de l'heure : le match est rejoué de bout en bout, quel que soit le match à l'antenne.
// Vérifie : bulle « KEY · … » avec la seconde ligne « SCOUTED · N GAMES » seulement quand la lecture vient surtout du
// film ; « ON TAPE » sous « BREAK » seulement pour une cassure « on tape » ; play-by-play « film: … , N games incl. k of
// their own », jamais « &amp; » ; onglet Game plan : « Scouting report » (matchs sur le film, tendances), absent sans
// rapport ; commentateur : rapport au coup d'envoi, lecture « on tape » ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8151;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const filmDe=P=>P.scout&&P.scout.def&&P.scout.def.film&&P.scout.def.film.part>=0.5&&P.scout.def.film.games>=1;

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
function feedAvecFilm(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    if(F.game.scout_film&&F.plays.filter(filmDe).length>=2&&F.plays.some(P=>P.scout&&P.scout.off&&P.scout.off.broke&&P.scout.off.on_tape)
       &&F.plays.some(P=>P.scout&&P.scout.def&&!filmDe(P))) return {F,src:src+' (réel)'};
  }
  // aucune semaine avec la mémoire : on ajoute play.scout (film) et le rapport à un match réel
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  let k=0;
  for(const P of F.plays){
    const t=P.call&&P.call.type;
    delete P.scout;
    if((t!=='run'&&t!=='pass')||P.conversion||!P.show||P.call.play_id==='KNEEL'||P.call.play_id==='SPIKE'||P.presnap) continue;
    if(P.decision&&P.decision.action==='SCRAMBLE') continue;
    if(k%3===0){
      const dt=P.offense==='home'?'away':'home', film=(k/3)%2===0;
      P.scout={version:'scouting-2',def:{team:dt,key:t,family:null,conf:0.75,right:true,
        why:film?`film: 41 of 52 ${t==='run'?'runs':'passes'} on 2nd & long from Trips, 19 games`:`6 of 7 ${t}s on 1st down`}};
      if(film) P.scout.def.film={games:19,own:1,part:0.9};
      if((k/3)%4===1) P.scout.off={team:P.offense,tendency:t==='run'?'pass':'run',played:t,broke:true,kind:'same_formation',
        same_formation:true,why:'film: 30 of 34 on 1st down, 19 games',on_tape:true};
    }
    k++;
  }
  F.game.scout_model='scouting-2';
  F.game.scout_memory={film:'film-1',weeks:3,source:'week'};
  F.game.scout_film={home:{games:19,own:1,top:[{dd:'1',formation:'I_FORM',key:'run',vu:31,sur:35,text:'on 1st down from I-formation'}]},
                     away:{games:18,own:1,top:[{dd:'3-long',formation:'EMPTY',key:'pass',vu:22,sur:22,text:'on 3rd & long from empty'}]}};
  const P0=F.plays.find(filmDe);
  if(P0) P0.adjust=(P0.adjust||[]).concat([{team:P0.scout.def.team,side:'defense',kind:'scout_key',label:P0.scout.def.key.toUpperCase(),
    text:'Keys on the '+P0.scout.def.key,reason:P0.scout.def.why}]);
  return {F,src:src+' (film ajouté)'};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-memoire-'));
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecFilm();
  const nF=F.plays.filter(filmDe).length, nT=F.plays.filter(P=>P.scout&&P.scout.off&&P.scout.off.broke&&P.scout.off.on_tape).length;
  console.log(`${src} · ${F.plays.length} actions · ${nF} lectures sur le film, ${nT} cassures « on tape »`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const out={};
      for(let i=0;i<150000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05); const P=g.cur; if(!P||g.phase!=='presnap') continue;
        const o=out[P.seq]||(out[P.seq]={seq:P.seq,keySub:new Set(),brkSub:new Set()});
        for(const x of G.scBubbles(g)||[]) (x.side==='def'?o.keySub:o.brkSub).add(x.sub||'');
      }
      const res=Object.values(out).map(o=>({seq:o.seq,keySub:[...o.keySub],brkSub:[...o.brkSub]}));
      const pbp=F.plays.filter(P=>P.scout&&P.scout.def).map(P=>({seq:P.seq,film:!!(P.scout.def.film&&P.scout.def.film.part>=0.5),own:P.scout.def.film?P.scout.def.film.own:0,text:G.rpFeedItem(g,P).text}));
      const com=[G.playLine(Object.assign({},g,{idx:0}),F.plays[0])];
      const P0=F.plays.find(P=>Array.isArray(P.adjust)&&P.adjust.some(a=>a.kind==='scout_key'&&/^film: /.test(String(a.reason||''))));
      const adj=P0?G.adjLine(g,P0):null;
      return {final:g.status==='final',res,pbp,com:com.map(x=>x&&x.text),adj:adj&&adj.text};
    },F);
    const bySeq={}; for(const P of F.plays) bySeq[P.seq]=P;
    const keyF=R.res.filter(o=>{ const P=bySeq[o.seq]; return P&&filmDe(P); });
    const keyM=R.res.filter(o=>{ const P=bySeq[o.seq]; return P&&P.scout&&P.scout.def&&!filmDe(P); });
    check(keyF.length>=1&&keyF.every(o=>o.keySub.some(s=>/^SCOUTED · \d+ GAMES?$/.test(s)&&+s.match(/\d+/)[0]===Math.round(bySeq[o.seq].scout.def.film.games))),
      `lecture sur le film : « KEY » + « SCOUTED · N GAMES » (${keyF.length})`);
    check(keyM.every(o=>o.keySub.every(s=>s==='')),`lecture du match : pas de seconde ligne (${keyM.length})`);
    const brk=R.res.filter(o=>{ const P=bySeq[o.seq]; return P&&P.scout&&P.scout.off&&P.scout.off.broke; });
    check(brk.filter(o=>bySeq[o.seq].scout.off.on_tape).every(o=>o.brkSub.includes('ON TAPE'))&&brk.filter(o=>!bySeq[o.seq].scout.off.on_tape).every(o=>!o.brkSub.includes('ON TAPE')),
      `cassure « on tape » : « ON TAPE » sous « BREAK », jamais ailleurs (${brk.length})`);
    const pf=R.pbp.filter(x=>x.film);
    check(pf.length>=1&&pf.every(x=>/keyed on the (run|pass) \(film: \d+ of \d+ .*, \d+ games/.test(x.text)&&(x.own>=1?/incl\. \d+ of their own\)/.test(x.text):!/of their own/.test(x.text))),
      `play-by-play : la lecture sur le film et ses matchs (${pf.length})`);
    check(R.pbp.every(x=>!/&amp;|&lt;|&gt;/.test(x.text)),'play-by-play : texte jamais échappé deux fois (« 2nd & long »)');
    check(R.com[0]&&/(games of .* film|games on tape)/.test(R.com[0]),`commentateur : rapport de scouting au coup d'envoi (« ${R.com[0]} »)`);
    check(R.adj&&/(homework|on tape)/.test(R.adj),`commentateur : lecture tirée du film (« ${R.adj} »)`);
    check(R.final,"match rejoué jusqu'au bout");
    // onglet Game plan : « Scouting report »
    await p.evaluate(()=>{ const t=document.querySelector('#modal [data-st="plan"]'); t&&t.click(); });
    await p.waitForTimeout(500);
    const gp=await p.evaluate(()=>{ const s=document.querySelector('#modal [data-f="stats"]'); return s?s.innerText:''; });
    const top=[].concat(...['home','away'].map(k=>((F.game.scout_film[k]||{}).top||[])));
    check(/Scouting report/i.test(gp)&&/On film/.test(gp)&&top.every(x=>gp.includes(`${x.vu} of ${x.sur}`)),'Game plan : « Scouting report » (matchs sur le film, tendances)');
    // sans rapport : pas de section
    const F2=JSON.parse(JSON.stringify(F)); delete F2.game.scout_film; F2.game.id=F.game.id+'-x';
    await p.evaluate(F2=>{ const G=window.__gc; G.openReplayFeed(F2); },F2); await p.waitForTimeout(400);
    await p.evaluate(()=>{ const t=document.querySelector('#modal [data-st="plan"]'); t&&t.click(); }); await p.waitForTimeout(400);
    const gp2=await p.evaluate(()=>{ const s=document.querySelector('#modal [data-f="stats"]'); return s?s.innerText:''; });
    check(!/Scouting report/i.test(gp2),'Game plan : pas de « Scouting report » sans game.scout_film');
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
