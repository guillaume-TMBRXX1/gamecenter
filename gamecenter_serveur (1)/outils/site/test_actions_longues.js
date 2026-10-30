// Actions longues et retours d'interception (section 85, 30/10/2026) — test navigateur (Playwright, crochet de test).
//   node outils/site/test_actions_longues.js          (depuis « gamecenter_serveur (1) »)
// Rejoue sur le grand écran deux matchs de la semaine d'essai du 02/11 (outils/site/matchs/longues-*.json) : un pick-six
// (play.int_return.td) et un long retour d'interception. Vérifie : bandeau « PICK-SIX · TOUCHDOWN » et effet
// « Pick six » (pas « Interception »), score de la défense +6 dès l'action, le défenseur qui intercepte finit dans
// l'en-but ; long retour : bandeau « INTERCEPTED · N-YD RETURN », le défenseur finit au point d'arrivée (play.spot) ;
// commentaire de l'action ; temps d'écran allongé (ecran-4) ; aucune erreur JS. Lancé par tests_navigateur.sh.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8176;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-longues-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  const w=fs.readdirSync(WEEKS).filter(x=>x.startsWith('week_')).sort().pop();
  fs.mkdirSync(path.join(data,'weeks')); fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0'}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const srv=await server(), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    for(const [fichier,six] of [['longues-pick-six.json',true],['longues-retour-int.json',false]]){
      const F=JSON.parse(fs.readFileSync(path.join(__dirname,'matchs',fichier),'utf8'));
      const P=F.plays.find(x=>x.result==='interception'&&x.int_return&&!!x.int_return.td===six&&(six||x.int_return.return>=30));
      const prev=F.plays[P.seq-2];
      console.log(`   ${fichier} : action ${P.seq} · ${P.text} · retour ${P.int_return.return} yds · écran ${P.show.act} s`);
      check(P.show.act>=5,`${six?'pick-six':'long retour'} : temps d'animation allongé (${P.show.act} s)`);
      const p=await b.newPage({viewport:{width:1280,height:900}}); p.on('pageerror',e=>errs.push(e.message));
      await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
      const r=await p.evaluate(({F,seq})=>{
        const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
        let vu=null, chip=null, flash=null, fin=null, txt=null;
        for(let i=0;i<400000;i++){
          G.stepGame(g,0.05);
          if(g.cur&&g.cur.seq===seq){
            if(g.phase==='play'&&g.carrier){ const c=g.carrier; vu=c; }
            if(g.phase!=='play'&&g.phase!=='presnap'&&!fin){ fin={x:g.ball?g.ball.x:null}; chip=g.chip&&g.chip.t; flash=g.tdFlash||g.toFlash||null; txt=g.lastText; }
          }
          if(g.cur&&g.cur.seq>seq) break;
        }
        return {chip,flash,txt,hs:g.hs,as:g.as,bx:fin&&fin.x};
      },{F,seq:P.seq});
      if(six){
        check(r.chip==='PICK-SIX · TOUCHDOWN','bandeau « PICK-SIX · TOUCHDOWN »'+(r.chip?` (${r.chip})`:''));
        const de=P.offense==='home'?'away':'home';
        check(P.after.score[de]-prev.after.score[de]===6&&P.try_follows,'score de la défense +6 dès l\'action, transformation à suivre');
        check(P.spot.x===(P.offense==='home'?10:110),'point d\'arrivée dans l\'en-but de l\'attaque');
      } else {
        check(new RegExp(`INTERCEPTED · ${P.int_return.return}-YD RETURN`).test(r.chip||''),`bandeau du long retour (${r.chip})`);
      }
      await p.close();
    }
    /* le commentaire d'une interception ramenée en touchdown */
    const p=await b.newPage(); p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    const F=JSON.parse(fs.readFileSync(path.join(__dirname,'matchs','longues-pick-six.json'),'utf8'));
    const P=F.plays.find(x=>x.int_return&&x.int_return.td);
    const line=await p.evaluate(({F,seq})=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); G.rpSeek(g,seq-1); const l=G.playLine(g,g.plays[seq-1]); return l&&l.text; },{F,seq:P.seq});
    check(/pick-six|Pick-six/i.test(line||''),`commentaire du pick-six : « ${String(line).slice(0,90)} »`);
    await p.close();
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
