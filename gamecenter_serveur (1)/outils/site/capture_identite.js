// Captures de la refonte des playbooks (étape 2) : une action de chaque sorte demandée, rejouée sur le grand écran.
//   node outils/site/capture_identite.js <dossier de GameFeed> <dossier de sortie>     (depuis « gamecenter_serveur (1) »)
// Cherche dans les GameFeed (semaine de test de outils/moteur/semaine_identite.py --garder) : un SALEM (GRZ / CTD), une
// action de ZPH en 10 personnel, un play exclusif ; rejoue le match jusqu'au milieu de l'action et enregistre l'écran.
// Vérifie au passage : routes de SALEM dessinées, aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), FEEDS=path.resolve(process.argv[2]), OUT=path.resolve(process.argv[3]||'.'), PORT=8139;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function chercher(test){
  for(const f of fs.readdirSync(FEEDS).filter(f=>f.endsWith('.json')).sort()){
    const F=JSON.parse(fs.readFileSync(path.join(FEEDS,f),'utf8'));
    const i=F.plays.findIndex((P,k)=>k>0&&test(P,F)&&F.plays[k-1].offense===P.offense&&
                                    ['run','complete','incomplete'].includes(F.plays[k-1].result));   /* pas de bannière d'avant */
    if(i>=0) return {F,i,f};
  }
  return null;
}
const equipe=(P,F)=>F.game[P.offense].abbr;

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-capid-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(path.join(ROOT,'data','weeks'),path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const cas=[
    ['salem', chercher((P,F)=>P.call&&P.call.concept==='SALEM'&&P.result==='complete')],
    ['zph_10_personnel', chercher((P,F)=>equipe(P,F)==='ZPH'&&P.call&&P.call.personnel==='10'&&P.call.type==='pass'&&P.result==='complete')],
    ['exclusif_mnl', chercher((P,F)=>P.call&&/^MNL_/.test(P.call.play_id||'')&&P.call.type==='run')],
  ];
  fs.mkdirSync(OUT,{recursive:true});
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    for(const [nom,c] of cas){
      if(!c){ check(false,`${nom} : aucune action trouvée`); continue; }
      const P=c.F.plays[c.i];
      console.log(`${nom} : ${c.f}, action ${P.seq} — ${equipe(P,c.F)} ${P.call.personnel||''} ${P.call.formation} ${P.call.concept} (${P.call.play_id}) · ${P.text}`);
      const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
      await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
      const r=await p.evaluate(({F,seq})=>{
        const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
        let t=0;
        for(let i=0;i<200000;i++){
          G.stepGame(g,0.05);
          if(g.cur&&g.cur.seq===seq&&g.phase==='play'){ t+=0.05; if(t>=1.6) break; }
        }
        g.paused=true;
        return {seq:g.cur&&g.cur.seq,phase:g.phase,routes:(g.routes||[]).length};
      },{F:c.F,seq:P.seq});
      await p.waitForTimeout(5000);          /* les bannières des actions rejouées en accéléré (temps réel) s'effacent */
      await p.screenshot({path:path.join(OUT,`identite_${nom}.png`)});
      check(r.seq===P.seq&&r.phase==='play',`${nom} : action ${P.seq} en cours sur l'écran`);
      check(errs.length===0,`${nom} : aucune erreur JS`+(errs.length?' : '+errs[0]:''));
      await p.close();
    }
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
