// Audio System V0.2 — tests du commentaire enregistré (navigateur)
//   python3 outils/audio/generer_audio.py --placeholder --audio-dir /tmp/gc-audio     (bips de test, sans ElevenLabs)
//   GC_TEST_HOOK=1 GC_AUDIO_DIR=/tmp/gc-audio uvicorn serveur:app --port 8104
//   node outils/audio/test_commentaire_v02.js data/weeks 8104
// 1. couverture : chaque moment commenté par la page (ligne écrite) a une prise enregistrée
// 2. variantes : pas deux fois de suite la même prise pour un même cue dans un match
// 3. direct : 25 s de match à l'antenne → des prises jouées, pas d'erreur
// 4. repli : fichiers inaccessibles → la voix de l'appareil prend le relais (log 'voice' fallback)
// 5. priorité : une ligne de priorité 3 coupe la prise en cours
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const DATA=process.argv[2], PORT=process.argv[3]||8104, EXE=process.env.CHROMIUM_PATH||undefined;
const feeds=[]; for(const w of fs.readdirSync(DATA)) for(const f of fs.readdirSync(path.join(DATA,w,'games'))) feeds.push(JSON.parse(fs.readFileSync(path.join(DATA,w,'games',f))));
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--autoplay-policy=no-user-gesture-required']});
  const open=async(block)=>{ const p=await b.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    if(block) await p.route('**/audio/commentary/**',r=>r.abort());
    await p.goto(`http://localhost:${PORT}/`); await p.waitForTimeout(1200);
    await p.evaluate(async()=>{ const A=window.__gc.audio; A.setSound(true); for(let i=0;i<60&&!(A.manager()&&A.manager().recordedPack());i++) await new Promise(r=>setTimeout(r,50)); });
    return {p,errs}; };
  // 1 + 2
  { const {p,errs}=await open(false);
    const r=await p.evaluate(({feeds})=>{
      const A=window.__gc.audio, M=A.manager(), Lb=A.lib, CC=Lb.CommentaryCues, map=Lb.AudioEventMapper, pk=new CC.CuePicker(); pk.index(M.assets.manifest.assets);
      let moments=0, missing={}, repeats=0, picks=0; const used={};
      for(const f of feeds){ const G=f.game, g={id:G.id,home:G.home.abbr,away:G.away.abbr,hs:0,as:0,hist:[],idx:0,mode:'live',speed:1,plays:f.plays,qs:G.quarter_seconds}; let prev={quarter:0,seq:-1}; const lastId={};
        f.plays.forEach((P,i)=>{ g.idx=i; g.cur=P;
          const s=map.mapSnap(g,P,prev), sl=A.snapLine(g,P), al=A.adjLine(g,P);
          const reqs=[]; if(s.ctx.quarterChanged) reqs.push([CC.quarterCue(s.ctx.quarter),s.ctx.importance]);
          if(sl||al) reqs.push(...CC.snapCues(s.ctx,P).map(c=>[c,s.ctx.importance]));
          g.hs=P.after.score.home; g.as=P.after.score.away;
          const r=map.mapResolve(g,P,g.hist.length?g.hist[g.hist.length-1]:null), pl=A.playLine(g,P);
          if(pl) reqs.push(...CC.resolveCues(r.ctx,P,g).map(c=>[c,r.ctx.importance]));
          for(const [c,imp] of reqs){ moments++; const a=pk.pick(g.id,P.seq,c,imp,true); if(!a){ const k=c.cue+'/'+(c.tags||[]).join(','); missing[k]=(missing[k]||0)+1; continue; }
            picks++; used[a.id]=1; if(lastId[c.cue]===a.id) repeats++; lastId[c.cue]=a.id; }
          g.hist.push(P.win_prob_home); prev={quarter:s.ctx.quarter,seq:P.seq}; }); }
      const unused=[...new Set(M.assets.manifest.assets.filter(a=>a.cat==='commentary'&&!used[a.id]).map(a=>a.cue))];
      return {moments,picks,missing,repeats,distinct:Object.keys(used).length,total:M.assets.manifest.assets.filter(a=>a.cat==='commentary').length,unused};
    },{feeds});
    console.log('1-2. couverture et variantes', JSON.stringify(r));
    check(Object.keys(r.missing).length===0,`toutes les cues ont une prise (${r.picks}/${r.moments} moments)`);
    check(r.repeats===0,'aucune prise répétée deux fois de suite pour un même cue');
    /* jamais entendues sur ces semaines : ajustements de coordinateurs (semaines V21, à partir du 12/10), intro / test (hors jeu), prolongation (1 seule) */
    const rare=new Set(['ADJ_HURRY','ADJ_CLOCK','ADJ_SHELVE','ADJ_SHELVE_FORM','ADJ_D_DEEP','ADJ_D_HEAT','ADJ_D_RUN','ADJ_D_PRESS','ADJ_D_NOBLITZ','ADJ_D_PREVENT','ADJ_D_ATTACK','INTRO_LIVE','INTRO_JOIN','INTRO_REPLAY','TEST','OVERTIME']);
    console.log('   prises jamais choisies, par cue :',r.unused.join(' '));
    check(r.distinct>=r.total*0.7&&r.unused.every(c=>rare.has(c)||['TOUCHDOWN','VICTORY','DEFEAT','FIELD_GOAL_GOOD','FIELD_GOAL_MISS','INTERCEPTION','FUMBLE','BIG_PLAY'].includes(c)),`${r.distinct}/${r.total} prises utilisées sur la saison, les autres sont des cas rares`);
    check(errs.length===0,'aucune erreur JS'); await p.close(); }
  // 3 + 5
  { const {p,errs}=await open(false);
    await p.locator('.tile.feat .field-hit').first().click(); await p.waitForTimeout(25000);
    const r=await p.evaluate(()=>{ const L=window.__gc.audio.log, M=window.__gc.audio.manager(); return {clips:L.filter(e=>e.kind==='clip').length,fallback:L.filter(e=>e.kind==='voice').length,says:L.filter(e=>e.kind==='say').length,cache:M.assets.stats(),sample:L.filter(e=>e.kind==='clip').slice(-4).map(e=>e.name)}; });
    console.log('3. direct 25 s', JSON.stringify(r));
    check(r.clips>0,'des prises enregistrées jouées en direct'); check(r.cache.bytes<=r.cache.budget,'cache décodé sous le budget mémoire');
    const pr=await p.evaluate(async()=>{ const M=window.__gc.audio.manager(), L=window.__gc.audio.log; L.length=0;
      M.say('low',1,null,{cues:[{cue:'RUN',tags:[]}],imp:.1,seq:1}); await new Promise(r=>setTimeout(r,30));
      M.say('big',3,null,{cues:[{cue:'TOUCHDOWN',tags:[]}],imp:.9,seq:2}); await new Promise(r=>setTimeout(r,1500));
      return L.filter(e=>e.kind==='clip'||e.kind==='clip-cut').map(e=>e.kind==='clip'?e.name+'@'+e.prio:'CUT'); });
    console.log('5. priorité', JSON.stringify(pr));
    check(/touchdown/.test(pr[pr.length-1])&&(pr.length===1||pr[pr.length-2]==='CUT'),'la priorité 3 coupe la prise en cours, puis le TD est dit');
    check(errs.length===0,'aucune erreur JS'); await p.close(); }
  // 4
  { const {p,errs}=await open(true);
    const r=await p.evaluate(async()=>{ const M=window.__gc.audio.manager(), L=window.__gc.audio.log; L.length=0;
      M.say('Touchdown fallback test',3,null,{cues:[{cue:'TOUCHDOWN',tags:[]}],imp:.9,seq:3}); await new Promise(r=>setTimeout(r,900));
      return {voice:L.filter(e=>e.kind==='voice').length,clips:L.filter(e=>e.kind==='clip').length}; });
    console.log('4. repli', JSON.stringify(r));
    check(r.voice===1&&r.clips===0,'fichier inaccessible → voix de l\'appareil');
    check(errs.length===0,'aucune erreur JS'); await p.close(); }
  await b.close(); console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
