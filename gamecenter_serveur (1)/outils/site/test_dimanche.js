// Le programme du dimanche (section 93, 04/11/2026) : « Sunday Classic » et « Road to the Final » — test navigateur.
//   node outils/site/test_dimanche.js          (depuis « gamecenter_serveur (1) »)
// Heures comptées depuis le coup d'envoi de la Grand Final (F) : Classic 1 à F − 3 h, Classic 2 à F − 2 h 15,
// « Road to the Final » de F − 1 h 30 à F. Vérifie : F − 2 h 50 (10 min de Classic 1), la tuile « Sunday Classic » joue
// le match d'origine à l'action que donne l'horloge (même calcul qu'un direct) et le programme de l'après-midi ;
// « Watch » ouvre le grand écran à cette action ; F − 2 h 05 : Classic 2, un autre match ; F − 45 min : « Road to the
// Final », panneaux (l'affiche et ses cotes, les actions des demi-finales sur le terrain, le face-à-face, les joueurs à
// suivre), compte à rebours ; un clic sur un panneau y saute ; téléphone 390 px ; aucune erreur JS.
// GC_CAPTURES=<dossier> : captures.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CAP=process.env.GC_CAPTURES||''; const cap=async(p,n,el)=>{ if(!CAP) return; if(el){ for(let i=0;i<4;i++){ await p.waitForTimeout(300); if(await p.locator(el).first().screenshot({path:path.join(CAP,n+'.png'),timeout:4000}).then(()=>true).catch(()=>false)) break; } } else await p.screenshot({path:path.join(CAP,n+'.png')}); };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const F=Date.parse(W.schedule.find(g=>g.phase==='ai_bowl').kickoff), H=3600e3, M=60e3;

async function server(port,at){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-dim-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(at).toISOString()}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${port}/api/time`)).ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const ouvrir=async(b,port,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{timeout:240000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); return p; };
const tag=p=>p.$eval('#revTile .pt-tag',e=>e.textContent.trim()).catch(()=>'');

(async()=>{
  const b=await chromium.launch({executablePath:EXE}), errs=[]; let srv=null;
  try{
    /* ---- Classic 1 ---- */
    srv=await server(8261,F-2*H-50*M);
    const prog=(await (await fetch('http://localhost:8261/api/review')).json()).programme;
    const [c1,c2]=prog.classics;
    check(prog.classics.length===2&&c1.game!==c2.game&&c1.start===F-3*H&&c2.start===F-2*H-15*M,`programme : Classic 1 ${c1.game} (${c1.why}), Classic 2 ${c2.game} (${c2.why.slice(0,40)})`);
    const p=await ouvrir(b,8261);
    await p.waitForSelector('#revTile .field canvas',{timeout:30000}).catch(()=>{});
    check(/Sunday Classic/.test(await tag(p)),`tableau à F − 2 h 50 : « ${await tag(p)} »`);
    const idx=await p.evaluate(()=>{ const g=window.__gc.byId&&window.__gc.byId.rev; return g?g.idx:null; }).catch(()=>null);
    const ref=await p.evaluate(([gid,start])=>{ const G=window.__gc, s=Object.assign({},G.season.SCHED.find(x=>x.id===gid),{ko:start}); return G.brk.timelineAt(s,G.season.nowMs()).done; },[c1.game,c1.start]).catch(()=>null);
    check(idx!=null&&ref!=null&&Math.abs(idx-ref)<=2,`Classic 1 calé sur l'horloge : action ${idx}${ref!=null?' (horloge : '+ref+')':''}`);
    const progTxt=await p.$eval('#revTile .rev-list',e=>e.textContent.replace(/\s+/g,' ')).catch(()=>'');
    check(/Sunday Classic.*Sunday Classic.*Road to the Final.*Grand Final/.test(progTxt),'programme de l\'après-midi sous la tuile');
    await p.waitForTimeout(4000);
    await cap(p,'1_classic','#revTile');
    await p.click('#revTile [data-rev-watch]');
    await p.waitForSelector('#modal:not([hidden]) .field canvas',{timeout:30000}).catch(()=>{});
    const mi=await p.evaluate(()=>document.querySelector('#modal:not([hidden])')?1:0);
    const ri=await p.evaluate(()=>{ const g=window.__gc.replayGame(); return g?g.idx:null; });
    const mt=await p.$eval('#modal .m-title',e=>e.textContent).catch(()=>'');
    const g1=W.schedule.find(x=>x.id===c1.game);
    check(mi&&mt.includes(W.teams[g1.home].name)&&ri!=null&&Math.abs(ri-idx)<=3,`« Watch » : le grand écran s'ouvre sur ${g1.away} @ ${g1.home}, action ${ri}`);
    errs.push(...p.errs); srv.kill();

    /* ---- Classic 2 ---- */
    srv=await server(8262,F-2*H-5*M);
    const q=await ouvrir(b,8262); await q.waitForSelector('#revTile .field canvas',{timeout:30000}).catch(()=>{});
    const t2=await q.$eval('#revTile .rev-seg',e=>e.textContent).catch(()=>'');
    const g2=W.schedule.find(x=>x.id===c2.game);
    check(/Sunday Classic/.test(await tag(q))&&t2.includes(g2.home),`F − 2 h 05 : Classic 2 (${t2})`);
    errs.push(...q.errs); srv.kill();

    /* ---- Road to the Final ---- */
    srv=await server(8263,F-45*M);
    const r=await ouvrir(b,8263); await r.waitForSelector('#revTile .road-panel',{timeout:30000}).catch(()=>{});
    check(/Road to the Final/.test(await tag(r)),`F − 45 min : « ${await tag(r)} »`);
    const cd=await r.$eval('#revTile .rev-n',e=>e.textContent).catch(()=>'');
    check(/Kickoff in 0?:?4\d:\d\d|Kickoff in 4\d:\d\d/.test(cd),`compte à rebours : « ${cd} »`);
    const mu=await r.$eval('#revTile .road-matchup',e=>({txt:e.textContent.replace(/\s+/g,' '),odds:e.querySelectorAll('.odd,button[data-k],button').length})).catch(()=>null);
    const fin=W.schedule.find(g=>g.phase==='ai_bowl');
    check(mu&&mu.txt.includes(W.teams[fin.home].name)&&mu.txt.includes(W.teams[fin.away].name)&&mu.odds>=2,`l'affiche : ${fin.away} vs ${fin.home}, cotes`);
    await cap(r,'2_road_affiche','#revTile');
    const dots=await r.$$eval('#revTile [data-road-k]',x=>x.map(e=>e.textContent));
    check(dots.includes('Road to the Final')&&dots.includes('Players to watch'),`panneaux : ${dots.join(' · ')}`);
    await r.click(`#revTile [data-road-k="${dots.indexOf('Road to the Final')}"]`);
    await r.waitForSelector('#revTile .field canvas',{timeout:30000}).catch(()=>{});
    const pc=await r.$eval('#revTile .rev-match',e=>e.textContent).catch(()=>'');
    check(/Semi-final/.test(pc),`les actions des demi-finales sur le terrain (« ${pc} »)`);
    await r.waitForTimeout(3000); await cap(r,'3_road_parcours','#revTile');
    await r.click(`#revTile [data-road-k="${dots.indexOf('Players to watch')}"]`); await r.waitForTimeout(500);
    const pl=await r.$$eval('#revTile .road-p',x=>x.length).catch(()=>0);
    check(pl>=4,`joueurs à suivre : ${pl} lignes`);
    await cap(r,'4_road_joueurs','#revTile');
    if(dots.includes('Head-to-head')){ await r.click(`#revTile [data-road-k="${dots.indexOf('Head-to-head')}"]`);
      await r.waitForFunction(()=>{ const e=document.querySelector('#revTile .riv-box'); return e&&/(leads|tied|First meeting)/.test(e.textContent); },null,{timeout:15000}).catch(()=>{});
      const h=await r.$eval('#revTile .riv-box',e=>e.textContent.replace(/\s+/g,' ').trim()).catch(()=>'');
      check(/(leads|tied|First meeting)/.test(h),`face-à-face : « ${h.slice(0,80)} »`); await cap(r,'5_road_h2h','#revTile'); }
    errs.push(...r.errs);
    const m=await ouvrir(b,8263,{viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await m.waitForSelector('#revTile .road-panel',{timeout:30000}).catch(()=>{}); await m.waitForTimeout(800);
    const w=await m.evaluate(()=>document.documentElement.scrollWidth);
    check(w<=390,`téléphone : pas de défilement horizontal (${w} px)`);
    await cap(m,'6_telephone','#revTile');
    errs.push(...m.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); if(srv) srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
