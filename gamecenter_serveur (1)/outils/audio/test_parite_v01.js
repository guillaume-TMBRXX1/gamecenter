// Audio System V0.1 — test de parité (navigateur)
//   GC_TEST_HOOK=1 uvicorn serveur:app --port 8103   puis   node outils/audio/test_parite_v01.js data/weeks 8103
// Rejoue chaque action de toutes les semaines sur le match « à l'antenne », avec le son allumé, une fois avec
// l'Audio System et une fois avec l'ancien code (?audio=legacy) : chaque effet (nom, délai, arguments), chaque
// phrase (texte, priorité) et chaque blocage doivent être identiques. Playwright requis (npm i playwright).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const EXE=process.env.CHROMIUM_PATH||undefined;
const fs=require('fs'), path=require('path');
const DATA=process.argv[2], PORT=process.argv[3]||8103;
const feeds=[]; for(const w of fs.readdirSync(DATA)) for(const f of fs.readdirSync(path.join(DATA,w,'games'))) feeds.push(JSON.parse(fs.readFileSync(path.join(DATA,w,'games',f))));
async function run(q, opts={}){
  const b=await chromium.launch({executablePath:EXE,args:['--autoplay-policy=no-user-gesture-required']});
  const p=await b.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(`http://localhost:${PORT}/${q}`); await p.waitForTimeout(1500);
  const out=await p.evaluate(async ({feeds,opts})=>{
    const A=window.__gc.audio; A.setSound(true); for(let i=0;i<50&&A.ctx()!=='running';i++) await new Promise(r=>setTimeout(r,50));
    const SET=window.__gc.season.bets.SET; Object.assign(SET,{voiceSrc:'device'},opts);   /* the recorded voice plays asynchronously: compare the decisions with the device voice */
    const log=[], events={};
    const M=A.manager(); if(M) M.onEvent(b=>{ for(const e of b.events) events[e]=(events[e]||0)+1; });
    for(const f of feeds){
      const G=f.game, g={id:'pt-'+G.id,home:G.home.abbr,away:G.away.abbr,hs:0,as:0,hist:[],idx:0,mode:'live',speed:1,plays:f.plays,qs:G.quarter_seconds,cur:f.plays[0]};
      A.setFocus(g); g.cur=null;
      f.plays.forEach((P,i)=>{ g.idx=i; g.cur=P; A.log.length=0; const st=0;
        A.snap(g); g.hs=P.after.score.home; g.as=P.after.score.away; A.resolve(g);
        for(const e of A.log.slice(st)) if(!['music','crowd','clip','clip-cut','voice'].includes(e.kind)) log.push([e.kind,e.name,JSON.stringify(e.args),e.prio,!!e.muted,e.game].join('|'));
        g.hist.push(P.win_prob_home); });
    }
    return {n:log.length, log, mode:A.mode(), ctx:A.ctx(), events};
  },{feeds,opts});
  await b.close(); return {...out,errs};
}
(async()=>{
  for(const [label,opts] of [['default',{}],['sfx off + crowd off + talk big',{sfx:false,crowd:false,talk:'big'}]]){
    const sys=await run('',opts), leg=await run('?audio=legacy',opts);
    let diff=-1; for(let i=0;i<Math.max(sys.log.length,leg.log.length);i++) if(sys.log[i]!==leg.log[i]){ diff=i; break; }
    console.log(`[${label}] system(${sys.mode},${sys.ctx}) ${sys.n} entries · legacy(${leg.mode},${leg.ctx}) ${leg.n} entries · ${diff<0?'IDENTICAL':'FIRST DIFF at '+diff+'\n  sys: '+sys.log[diff]+'\n  leg: '+leg.log[diff]} · errors: ${JSON.stringify(sys.errs.concat(leg.errs))}`);
    if(label==='default') console.log('events mapped:', JSON.stringify(sys.events));
    if(diff>=0||sys.errs.length||leg.errs.length) process.exitCode=1;
  }
})();
