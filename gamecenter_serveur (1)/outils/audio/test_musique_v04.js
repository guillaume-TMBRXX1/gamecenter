// Audio System V0.4 — tests de la musique
//   GC_TEST_HOOK=1 uvicorn serveur:app --port 8108      (audio/ du dépôt : la musique composée y est)
//   node outils/audio/test_musique_v04.js 8108
// 1. règles d'état (sans navigateur) · 2. navigateur : pregame au démarrage, montée immédiate en tension,
//    retour seulement après 20 s, jingle de fin selon HOME, jamais plus de 2 sources (fondu), muet → arrêt
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), vm=require('vm');
const HERE=path.resolve(__dirname,'..','..'), PORT=process.argv[2]||8108;
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const ctx={window:{}}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(HERE,'static/audio/MusicManager.js'),'utf8'),ctx);
const F=ctx.window.GCAudioLib.MusicManager.stateFor;
const c=o=>Object.assign({offense:'home',score:{home:7,away:7},quarter:2,isLateGame:false,isCloseGame:true,isOvertime:false,isRedZone:false,callType:'pass',status:'live'},o);
console.log('1. règles');
check(F(c({}),['SNAP'])==='gameplay','jeu ordinaire (1re mi-temps) → gameplay');
check(F(c({isRedZone:true}),['SNAP','RED_ZONE'])==='red_zone','zone rouge → red_zone');
check(F(c({quarter:3}),['SNAP'])==='close_game','serré en 2e mi-temps → close_game');
check(F(c({quarter:4,isLateGame:true,score:{home:17,away:21}}),['SNAP'])==='final_drive','fin de match, l\'attaque est menée → final_drive');
check(F(c({quarter:4,isLateGame:true,score:{home:24,away:21}}),['SNAP'])==='close_game','fin de match, l\'attaque mène → close_game');
check(F(c({quarter:5,isOvertime:true}),['SNAP'])==='overtime','prolongation → overtime');
check(F(c({status:'half'}),['HALFTIME'])==='pregame','mi-temps → pregame');
check(F(c({}),['GAME_END','VICTORY'])==='victory'&&F(c({}),['GAME_END','DEFEAT'])==='defeat','fin : victory / defeat (point de vue HOME)');
(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--autoplay-policy=no-user-gesture-required']});
  const p=await b.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(`http://localhost:${PORT}/`); await p.waitForTimeout(1200);
  console.log('2. navigateur');
  const r=await p.evaluate(async()=>{
    const A=window.__gc.audio, M=A.manager(), wait=ms=>new Promise(r=>setTimeout(r,ms));
    A.setSound(true); for(let i=0;i<80&&!M.music.ready();i++) await wait(100);
    await wait(2500); const start=M.stats().music;
    const mm=M.music, out={start};
    mm.request('red_zone'); await wait(400); out.up=mm.stats();
    mm.request('gameplay'); await wait(400); out.down=mm.stats();            /* < 20 s : attend */
    mm.since-=21; mm.tick(); await wait(3600); out.later=mm.stats();         /* 20 s plus tard : redescend */
    let maxSrc=0; for(const st of ['close_game','final_drive','overtime','red_zone']){ mm.request(st,true); for(let i=0;i<6;i++){ await wait(150); maxSrc=Math.max(maxSrc,mm.stats().sources); } }
    out.maxSrc=maxSrc;
    mm.request('victory'); await wait(500); out.victory=mm.stats();
    const S=window.__gc.season.bets.SET; S.mixMute.music=true; A.manager().apply(); await wait(1600); out.muted=mm.stats();
    S.mixMute.music=false; A.manager().apply(); await wait(1500); out.unmuted=mm.stats();
    return out; });
  console.log('   ',JSON.stringify(r));
  check(r.start.pieces===8&&r.start.playing&&['pregame','gameplay','close_game','red_zone','final_drive','overtime'].includes(r.start.state),`8 pièces, musique dès le son allumé (${r.start.state} : le match à l'antenne décide)`);
  check(r.up.state==='red_zone','la tension monte tout de suite');
  check(r.down.state==='red_zone'&&r.down.want==='gameplay','redescente différée (pas de va-et-vient)');
  check(r.later.state==='gameplay','redescend après 20 s');
  check(r.maxSrc<=2,`fondus enchaînés : 2 sources au plus (${r.maxSrc})`);
  check(r.victory.state==='victory','jingle de victoire');
  check(!r.muted.playing&&r.muted.sources===0,'musique coupée → arrêtée et libérée');
  check(r.unmuted.playing,'musique rallumée → reprend');
  check(errs.length===0,'aucune erreur JS'+(errs[0]?' : '+errs[0]:''));
  await b.close(); console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
