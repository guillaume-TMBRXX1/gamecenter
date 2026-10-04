// Audio System V0.3 — tests de la foule et des effets enregistrés
//   python3 outils/audio/generer_audio.py --placeholder --cat stade --audio-dir /tmp/gc-audio   (sons de test, sans ElevenLabs)
//   GC_TEST_HOOK=1 GC_AUDIO_DIR=/tmp/gc-audio uvicorn serveur:app --port 8106
//   node outils/audio/test_stade_v03.js data/weeks 8106
// 1. règles de la foule (point de vue HOME), sans navigateur
// 2. navigateur : packs chargés, fonds en boucle, effets et réactions joués sur toute une semaine rejouée en accéléré,
//    jamais plus de 6 effets / 2 réactions à la fois, tout est libéré après (pas de fuite), son coupé → fonds arrêtés
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), vm=require('vm');
const HERE=path.resolve(__dirname,'..','..'), DATA=process.argv[2]||path.join(HERE,'data/weeks'), PORT=process.argv[3]||8106;
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
// ---------- 1 ----------
const ctx={window:{}}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(HERE,'static/audio/CrowdManager.js'),'utf8'),ctx);
const R=ctx.window.GCAudioLib.CrowdManager.reactions, mood=ctx.window.GCAudioLib.CrowdManager.mood;
const c=(o)=>Object.assign({offense:'home',importance:.5,down:1,gain:5,score:{home:7,away:0},isCloseGame:true,isLateGame:false},o);
const k=(x)=>x.map(r=>r[0]).join('+');
console.log('1. règles de la foule');
check(k(R(c({}),['TOUCHDOWN']))==='react_td','TD de l\'équipe à domicile → le stade explose');
check(k(R(c({offense:'away',importance:.6}),['TOUCHDOWN']))==='boo','TD des visiteurs (moment important) → huées');
check(k(R(c({offense:'away',importance:.3}),['TOUCHDOWN']))==='disappointment','TD des visiteurs (sans enjeu) → déception');
check(k(R(c({offense:'away'}),['INTERCEPTION','TURNOVER']))==='react_int','interception par la défense à domicile → réaction');
check(k(R(c({offense:'home'}),['FUMBLE','TURNOVER']))==='disappointment','fumble perdu à domicile → déception');
check(k(R(c({offense:'away'}),['SACK']))==='cheer_medium','sack par la défense à domicile → acclamation');
check(k(R(c({importance:.2}),['RUN']))==='','course ordinaire → rien (pas d\'arcade)');
check(k(R(c({}),['PASS_COMPLETE','FIRST_DOWN']))==='cheer_small','premier down à domicile → applaudissements polis');
check(k(R(c({}),['TOUCHDOWN','GAME_END','VICTORY']))==='react_victory','victoire → célébration (couvre la dernière action)');
check(k(R(c({isCloseGame:false}),['GAME_END','DEFEAT']))==='boo','défaite large → huées');
check(mood(c({}),['SNAP','THIRD_DOWN'])==='anticipation'&&mood(c({}),['SNAP'])==='idle','fond : anticipation sur 3e down, calme sinon');
// ---------- 2 ----------
const feeds=[]; for(const w of fs.readdirSync(DATA)) for(const f of fs.readdirSync(path.join(DATA,w,'games'))) feeds.push(JSON.parse(fs.readFileSync(path.join(DATA,w,'games',f))));
(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--autoplay-policy=no-user-gesture-required']});
  const p=await b.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(`http://localhost:${PORT}/`); await p.waitForTimeout(1200);
  console.log('2. navigateur');
  const r=await p.evaluate(async({feeds})=>{
    const A=window.__gc.audio; A.setSound(true); const M=A.manager();
    for(let i=0;i<100&&!(M.crowd.ready()&&M.sfxRec.ready()&&M.assets.stats().pending===0&&M.assets.stats().entries>20);i++) await new Promise(r=>setTimeout(r,100));
    const SET=window.__gc.season.bets.SET; SET.voiceSrc='device'; SET.talk='off';
    const ready={crowd:M.crowd.ready(),sfx:M.sfxRec.ready(),cache:M.assets.stats()};
    await new Promise(r=>setTimeout(r,600)); const beds=M.crowd.stats().beds;
    let maxSfx=0, maxLive=0, crowd={}, rec={}, proc=0;
    for(const f of feeds.slice(0,6)){ const G=f.game, g={id:'t3-'+G.id,home:G.home.abbr,away:G.away.abbr,hs:0,as:0,hist:[],idx:0,mode:'live',speed:1,plays:f.plays,qs:G.quarter_seconds,cur:f.plays[0]};
      A.setFocus(g);
      for(let i=0;i<f.plays.length;i++){ const P=f.plays[i]; g.idx=i; g.cur=P; A.log.length=0;
        A.snap(g); g.hs=P.after.score.home; g.as=P.after.score.away; A.resolve(g); g.hist.push(P.win_prob_home);
        for(const e of A.log){ if(e.kind==='crowd') crowd[e.name]=(crowd[e.name]||0)+1; if(e.kind==='sfx'&&!e.muted){ if(e.rec) rec[e.rec]=(rec[e.rec]||0)+1; else proc++; } }
        const s=M.stats(); maxSfx=Math.max(maxSfx,s.sfx.active); maxLive=Math.max(maxLive,s.crowd.live);
        if(i%25===0) await new Promise(r=>setTimeout(r,30)); } }
    /* le match à l'antenne continue de jouer sur la page : on le fait taire pendant la mesure (sinon il relance des sons) */
    const sv=[M.snap,M.resolve]; M.snap=M.resolve=()=>{};
    await new Promise(r=>setTimeout(r,10000));
    const after=M.stats(); [M.snap,M.resolve]=sv;
    A.setSound(false); await new Promise(r=>setTimeout(r,3500)); const off=M.stats();
    return {ready,beds,crowd,rec,proc,maxSfx,maxLive,after:{sfx:after.sfx.active,live:after.crowd.live,cache:after.cache},off:off.crowd};
  },{feeds});
  console.log('   ',JSON.stringify(r));
  check(r.ready.crowd&&r.ready.sfx,'packs foule et effets chargés');
  check(r.beds.idle&&r.beds.idle.on&&r.beds.idle.srcs>=1,'fond de foule en boucle');
  check(Object.keys(r.rec).length>=6,`effets enregistrés joués (${Object.keys(r.rec).join(', ')})`);
  check((r.crowd.react_td||0)+(r.crowd.boo||0)+(r.crowd.disappointment||0)>0&&(r.crowd.cheer_small||0)>0,'réactions de la foule jouées');
  check(r.maxSfx<=6&&r.maxLive<=2,`limites respectées (effets ≤ 6 : ${r.maxSfx}, réactions ≤ 2 : ${r.maxLive})`);
  check(r.after.sfx===0&&r.after.live===0,'tout est libéré après coup (aucune source qui traîne)');
  check(r.after.cache.bytes<=r.after.cache.budget,'cache décodé sous le budget mémoire');
  check(!r.off.beds.idle.on&&r.off.beds.idle.srcs===0,'son coupé → fonds arrêtés et libérés');
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  await b.close(); console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
