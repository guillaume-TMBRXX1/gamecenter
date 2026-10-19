// Fumbles gardés par l'attaque (moteur 12.2 vicies, play.fumble — 19/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_fumbles.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Rejoue en temps simulé un match dont des actions portent play.fumble (lost: false) : le dernier de data/weeks qui en a
// au moins 2 ; sinon un match réel dont des courses et des sacks reçoivent un fumble gardé à tour de rôle (par le
// porteur lui-même, par un coéquipier).
// Vérifie, action par action : le ballon échappe au porteur puis reste à l'attaque (le porteur le récupère lui-même, ou
// un coéquipier) — jamais à un défenseur ; la puce « FUMBLE · RECOVERED » ; le play-by-play (« fumble, recovered » et qui l'a récupéré)
// et le commentateur racontent le fumble gardé ; un fumble perdu reste une perte de balle ; le match va au bout, sans
// erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8143;
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
function feedAvecFumbles(){
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    if(F.plays.filter(P=>P.fumble&&P.fumble.lost===false).length>=2) return {F,src:src+' (réel)'};
  }
  const {file,src}=all.find(x=>JSON.parse(fs.readFileSync(x.file,'utf8')).plays.some(P=>P.show))||all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  let k=0;
  for(const P of F.plays){
    if((P.result!=='run'&&P.result!=='sack')||P.conversion||!P.show||P.call.play_id==='KNEEL'||(P.decision&&P.decision.action==='SCRAMBLE')) continue;
    if(k%5===0){
      const self=(k/5)%2===0, team=F.game[P.offense].abbr;
      const who=(P.players&&(P.players.carrier||P.players.passer)||{}).name||'Test Carrier';
      P.fumble={lost:false,by:who,recovered_by:self?'self':'team',team};
      P.text=(who+' fumble, recovered, '+(num(P.gain)>=0?'+':'−')+Math.abs(Math.round(num(P.gain)))).slice(0,40);
    }
    k++;
  }
  return {F,src:src+' (play.fumble ajouté)'};
}

function num(v,d){ return typeof v==='number'&&isFinite(v)?v:(d||0); }

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-fumbles-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecFumbles();
  const K=F.plays.filter(P=>P.fumble&&P.fumble.lost===false), L=F.plays.filter(P=>P.result==='fumble_lost');
  console.log(`${src} · ${F.plays.length} actions · ${K.length} fumbles gardés (${K.filter(P=>P.fumble.recovered_by==='self').length} par le porteur), ${L.length} perdus`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const out={}, texts=[], lines=[]; let lastF=null;
      for(let i=0;i<90000&&!(g.status==='final'&&g.paused);i++){
        const ph=g.phase;
        G.stepGame(g,0.05);
        if(g.feed&&g.feed[0]&&g.feed[0]!==lastF){ lastF=g.feed[0]; texts.push(String(lastF.text||'')); }
        const P=g.cur;
        if(!P||!(P.fumble||P.result==='fumble_lost')) continue;
        if(ph==='presnap'&&g.phase==='play'&&g.plan){
          const c=g.plan.carrier, last=c[c.length-1], first=c.find(x=>x[2]===c[0][2]);
          out[P.seq]={seq:P.seq,kept:!!(P.fumble&&P.fumble.lost===false),self:!!(P.fumble&&P.fumble.recovered_by==='self'),
                      n:c.length,side:last[2],idx:last[3],idx0:c[c.length-2]?c[c.length-2][3]:null,flag:g.plan.fumble};
          const l=G.playLine(g,P); if(l) lines.push({seq:P.seq,kept:out[P.seq].kept,text:l.text});
        }
        if(ph==='play'&&g.phase!=='play'&&out[P.seq]) out[P.seq].chip=g.chip&&g.chip.t;
      }
      return {out:Object.values(out),status:g.status,feed:texts,lines};
    },F);
    const O=R.out.filter(o=>o.kept), Lo=R.out.filter(o=>!o.kept);
    console.log(`   ${O.length} fumbles gardés et ${Lo.length} perdus rejoués`);
    check(O.length>=Math.min(2,K.length)&&O.length>0,'les fumbles gardés sont joués');
    const offKo=O.filter(o=>o.side!=='off'||o.flag!=='kept'||o.n<2);
    if(offKo.length) console.log('   porteurs :',JSON.stringify(offKo.slice(0,4)));
    check(!offKo.length,`le ballon échappe au porteur puis reste à l'attaque (${O.length-offKo.length} / ${O.length})`);
    const selfKo=O.filter(o=>o.self&&o.idx!==o.idx0), mateKo=O.filter(o=>!o.self&&o.idx===o.idx0);
    check(!selfKo.length,`récupéré par le porteur lui-même : c'est lui qui retombe dessus (${O.filter(o=>o.self).length-selfKo.length} / ${O.filter(o=>o.self).length})`);
    check(!mateKo.length,`récupéré par un coéquipier : un autre joueur de l'attaque (${O.filter(o=>!o.self).length-mateKo.length} / ${O.filter(o=>!o.self).length})`);
    const chKo=O.filter(o=>o.chip!=='FUMBLE · RECOVERED');
    check(!chKo.length,`puce « FUMBLE · RECOVERED » (${O.length-chKo.length} / ${O.length})`);
    if(Lo.length) check(Lo.every(o=>o.side==='def'),'un fumble perdu reste une perte de balle : la défense a le ballon');
    const txt=R.feed.join('\n');
    check(/fumble, recovered.* · (recovered by [A-Z]{2,4}|he recovers it himself)/.test(txt),'play-by-play : le fumble gardé');
    const lk=R.lines.filter(l=>l.kept), lkKo=lk.filter(l=>!/Fumble|loose|fumble/.test(l.text)||/undefined|null|NaN/.test(l.text));
    if(lkKo.length) console.log('   commentaire :',JSON.stringify(lkKo.slice(0,3)));
    check(lk.length>0&&!lkKo.length,`commentateur : le fumble gardé est raconté (${lk.length-lkKo.length} / ${lk.length})`);
    check(R.status==='final','match rejoué jusqu\'au bout');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
