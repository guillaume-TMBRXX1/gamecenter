// Les blessures (moteur 12.2 vicies sexies, étape 7.4 — 23/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_blessures.js [dossier data/weeks] [gamefeed.json]     (depuis « gamecenter_serveur (1) »)
// Prend le dernier match de data/weeks (ou le GameFeed donné) qui a une blessure de sortie (play.injury, severity
// « game » ou « weeks ») suivie de son remplacement (play.subs reason « injury ») ; sinon un match réel auquel on
// ajoute une blessure : le RB1 qui porte le ballon se blesse (côtes, sorti pour le match), le RB3 le remplace à la
// série suivante. Ne dépend pas de l'heure.
// Vérifie : le blessé n'est plus jamais aligné ; après l'action, son étiquette « INJURED » et la croix médicale sur le
// terrain ; play-by-play (« Injury: … will not return », puis « X comes in for the injured Y ») et commentateur ;
// la fiche en match (bandeau « Injured ») ; le tableau de profondeur et le rapport des blessures (absent « OUT ») ;
// aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), FEED=process.argv[3], PORT=8163;
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
const scrimmage=P=>P.call&&(P.call.type==='run'||P.call.type==='pass');
function feedAvecBlessure(){
  const reel=F=>{ const k=F.plays.findIndex(P=>P.injury&&P.injury.severity!=='minor'&&scrimmage(P));
    return k>=0&&F.game.rotation_model&&F.plays.slice(k+1).some(P=>(P.subs||[]).some(x=>x.reason==='injury'&&x.out===F.plays[k].injury.id)); };
  if(FEED){ const F=JSON.parse(fs.readFileSync(FEED,'utf8')); return {F,src:path.basename(FEED)+' (réel)'}; }
  const all=feeds();
  for(const {file,src} of all){ const F=JSON.parse(fs.readFileSync(file,'utf8')); if(reel(F)) return {F,src:src+' (réel)'}; }
  const {file,src}=all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  // une course du RB1 au 2e quart-temps : il se blesse ; le RB3 (ajouté au banc) le remplace à l'action suivante de son attaque
  const k=F.plays.findIndex(P=>scrimmage(P)&&P.call.type==='run'&&P.quarter===2&&P.players&&P.players.carrier&&/_RB1$/.test(P.players.carrier.id||''));
  const P=F.plays[k], side=P.offense, R=F.game[side].roster, rb1=P.players.carrier.id, ab=rb1.split('_')[0];
  const used=new Set(R.map(r=>r.number)), n=[...Array(30).keys()].map(x=>x+20).find(x=>!used.has(x));
  R.forEach(r=>{ if(r.depth==null){ r.depth=1; r.profile='starter'; } });
  const rb3={id:`${ab}_RB3`,name:`Bench RB3 ${ab}`,pos:'RB',number:n,ratings:Object.assign({},R.find(r=>r.id===rb1).ratings),archetype:null,depth:2,profile:'veteran',slot:'RB3',covers:['RB']};
  R.push(rb3);
  const nm=R.find(r=>r.id===rb1).name;
  P.injury={id:rb1,name:nm,team:side,pos:'RB',part:'ribs',severity:'game',weeks:0,returns:false};
  F.game.injuries=[{id:rb1,name:nm,team:side,pos:'RB',part:'ribs',severity:'game',weeks:0,seq:k,quarter:P.quarter}];
  R.find(r=>r.id===rb1).injury={part:'ribs',severity:'game',weeks:0,seq:k};
  F.game.injury_model='blessures-1'; F.game.rotation_model=F.game.rotation_model||'rotations-1';
  const nxt=F.plays.findIndex((Q,j)=>j>k&&scrimmage(Q)&&Q.offense===side);
  (F.plays[nxt].subs=F.plays[nxt].subs||[]).push({in:rb3.id,out:rb1,pos:'RB',reason:'injury',side:'off'});
  for(const Q of F.plays.slice(nxt)){ const pp=Q.players||{};      // après sa sortie, le RB3 porte le ballon à sa place
    if(pp.carrier&&pp.carrier.id===rb1) pp.carrier={id:rb3.id,name:rb3.name};
    for(const x of Q.subs||[]) if(x.in===rb1) x.in=rb3.id; }
  return {F,src:src+' (blessure ajoutée)'};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-blessures-'));
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecBlessure();
  const k=F.plays.findIndex(P=>P.injury&&P.injury.severity!=='minor'&&scrimmage(P)), B=F.plays[k].injury;
  console.log(`${src} · blessure à l'action ${k} : ${B.name} (${B.pos}), ${B.part}, ${B.severity}`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`,{waitUntil:'domcontentloaded',timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    const R=await p.evaluate(([F,k])=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(), B=F.plays[k].injury, out={};
      // le blessé n'est plus jamais aligné après l'action suivante de son équipe (le remplacement)
      const L=G.rotLineups(g), apres=[];
      F.plays.forEach((P,j)=>{ if(j<=k||!(P.call&&(P.call.type==='run'||P.call.type==='pass'))) return;
        const a=L.at[j], u=P.offense===B.team?'off':'def', v=Object.values(a[B.team][u]);
        if((P.subs||[]).length||j>k+1) apres.push(v.includes(B.id)?j:-1); });
      const sortie=apres.findIndex(x=>x===-1);
      out.retour=apres.slice(sortie<0?0:sortie).filter(x=>x>=0);
      // après l'action : étiquette INJURED et croix médicale
      G.rpSeek(g,k); g.paused=false; g.speed=1;
      for(let i=0;i<6000;i++){ G.stepGame(g,0.01); if(g.phase==='post') break; }
      for(let i=0;i<30;i++) G.stepGame(g,0.01);
      out.phase=g.phase; const T=G.nameTags(g)||[]; out.tag=T.filter(t=>t.kind==='inj').map(t=>t.text+' '+t.sub);
      out.spot=G.injSpot(g);
      out.card=out.spot?/pc-inj/.test(G.playerCardHTML(g,out.spot.side,out.spot.idx))&&/will not return/.test(G.playerCardHTML(g,out.spot.side,out.spot.idx)):false;
      // play-by-play et commentateur
      out.pbp=G.rpFeedItem(g,F.plays[k]).text;
      const nx=F.plays.findIndex((P,j)=>j>k&&(P.subs||[]).some(x=>x.reason==='injury'&&x.out===B.id));
      out.pbpNext=nx>=0?G.rpFeedItem(g,F.plays[nx]).text:'';
      out.line=(G.playLine(Object.assign({},g,{idx:k}),F.plays[k])||{}).text||'';
      out.lineNext=nx>=0?((G.playLine(Object.assign({},g,{idx:nx}),F.plays[nx])||{}).text||''):'';
      // tableau de profondeur et rapport des blessures : un absent de la semaine
      const RS=F.game[B.team].roster.map(r=>Object.assign({},r,{status:'active'})); RS[0]=Object.assign(RS[0],{status:'out',absence:{part:'knee',weeks_left:2}});
      const T2={abbr:F.game[B.team].abbr||'X',roster:RS}, box=document.createElement('div');
      box.innerHTML=G.depthChartHTML(T2)+G.injuryReportHTML(T2);
      out.depthOut=box.querySelectorAll('.dc-p.out').length; out.depthTxt=/OUT · knee/.test(box.innerHTML);
      out.report=box.querySelectorAll('table.inj tbody tr').length; out.reportTxt=/Out · 2 wks/.test(box.innerHTML);
      // blessé pendant la semaine (23/10) : une fois son action jouée, « out » jusqu'à la fin de la semaine, sans
      // changer les cotes — rapport et tableau de profondeur (injuries.in_week, envoyé par le serveur)
      const SW=G.season.sw(), g0=G.season.SCHED[0], r1=RS[1], keep=SW.injuries;
      SW.injuries=Object.assign({},keep||{},{in_week:[{team:T2.abbr,id:r1.id,name:r1.name,pos:r1.pos,part:'ankle',weeks:1,game:g0.id,seq:3}]});
      const box2=document.createElement('div'); box2.innerHTML=G.depthChartHTML(T2)+G.injuryReportHTML(T2);
      out.week={depthOut:box2.querySelectorAll('.dc-p.out').length,report:box2.querySelectorAll('table.inj tbody tr').length,
        txt:/Hurt \w{3} · out this week \+ 1 wk/.test(box2.innerHTML)};
      SW.injuries=keep;
      return out;
    },[F,k]);
    check(R.retour.length===0,`le blessé n'est plus aligné après son remplacement${R.retour.length?' (actions '+R.retour.slice(0,5).join(', ')+')':''}`);
    check(R.phase==='post'&&R.tag.length===1&&/INJURED/.test(R.tag[0]),`après l'action : étiquette « INJURED » (${R.tag.join(', ')})`);
    check(!!R.spot,'la croix médicale a son joueur sur le terrain (injSpot)');
    check(R.card,'fiche en match : bandeau « Injured … will not return »');
    check(/Injury: .* — will not return/.test(R.pbp),`play-by-play de l'action : « ${R.pbp.split(' · ').find(x=>/Injury/.test(x))} »`);
    check(/comes in for the injured/.test(R.pbpNext),`play-by-play du remplacement : « ${R.pbpNext.split(' · ').find(x=>/comes in/.test(x))} »`);
    check(/will not return|out for the game|done for the day/.test(R.line),'commentateur : il ne reviendra pas');
    check(/injured|With .* out/.test(R.lineNext),'commentateur : le remplaçant entre');
    check(R.depthOut===1&&R.depthTxt,`tableau de profondeur : l'absent « OUT · knee » (${R.depthOut})`);
    check(R.report===1&&R.reportTxt,`rapport des blessures : 1 absent, « Out · 2 wks » (${R.report})`);
    check(R.week.depthOut===2&&R.week.report===2&&R.week.txt,`blessé de la semaine : « out » au tableau de profondeur et au rapport, « Hurt … · out this week + 1 wk » (${JSON.stringify(R.week)})`);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
