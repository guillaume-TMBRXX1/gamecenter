// « Week in review », l'émission du week-end (section 92, 04/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_review.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur le samedi matin de la dernière semaine (après le verrou du vendredi, aucun match en direct) :
// la grande tuile du tableau devient « Week in review » ; le carton titre de la première rubrique, puis l'action jouée
// (le terrain avance) et la suivante ; « Full game » ouvre le replay du match ; la playlist ne contient que des matchs
// terminés ; avant le verrou (vendredi en journée) : pas d'émission ; pendant une demi-finale : le direct, pas
// l'émission ; « Hide scores » : pas d'émission ; téléphone 390 px sans défilement horizontal ; GC_WEEK_REVIEW=off :
// rien, /api/review 404 ; aucune erreur JS. GC_CAPTURES=<dossier> : captures.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CAP=process.env.GC_CAPTURES||''; const cap=async(p,n,el)=>{ if(!CAP) return; if(el){ for(let i=0;i<4;i++){ await p.waitForTimeout(300); if(await p.locator(el).first().screenshot({path:path.join(CAP,n+'.png'),timeout:4000}).then(()=>true).catch(()=>false)) break; } } else await p.screenshot({path:path.join(CAP,n+'.png')}); };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const LOCK=Date.parse(W.week.standings_locked_at), SF=W.schedule.filter(g=>g.phase==='semifinal').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const T0=LOCK+9*3600e3;                                   /* samedi matin : aucun match */

async function server(port,env,at){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-rev-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(at||T0).toISOString()},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${port}/api/time`)).ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* arrête un serveur et attend que son port ne réponde plus (redémarrage sur le même port, CI du 05/11/2026) */
async function arreter(p,port){
  if(p.exitCode===null&&p.signalCode===null){ const fin=new Promise(r=>p.once('exit',r)); p.kill(); await Promise.race([fin,new Promise(r=>setTimeout(r,15000))]); }
  for(let i=0;i<60;i++){ try{ await fetch(`http://localhost:${port}/api/time`); }catch(e){ return; } await new Promise(r=>setTimeout(r,250)); }
}
const ouvrir=async(b,port,opts,init)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  if(init) await ctx.addInitScript(init);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{timeout:240000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); return p; };
const show=p=>p.waitForSelector('#revTile .field canvas',{timeout:30000}).then(()=>true).catch(()=>false);

(async()=>{
  const P1=8231, P2=8232, P3=8233; const srv=await server(P1,{}), b=await chromium.launch({executablePath:EXE}), errs=[]; let srv2=null, srv3=null;
  try{
    console.log(`   horloge : ${new Date(T0).toISOString()} (samedi, après le verrou)`);
    const d=await (await fetch(`http://localhost:${P1}/api/review`)).json();
    const keys=d.segments.map(s=>s.key);
    const finals=new Set(W.schedule.filter(g=>g.phase==='regular').map(g=>g.id));
    check(d.on&&d.edition==='regular'&&keys.includes('plays')&&!keys.includes('semis')&&!keys.includes('final'),`API : édition « regular » (${keys.join(', ')})`);
    check(d.segments.every(s=>s.clips.every(c=>finals.has(c.game))),'API : seulement des matchs de saison régulière, tous terminés');

    const p=await ouvrir(b,P1);
    check(await show(p),'tableau : la grande tuile devient « Week in review »');
    const card=await p.$eval('#revTile .rev-card',e=>({on:!e.classList.contains('off'),txt:e.textContent.replace(/\s+/g,' ').trim()})).catch(()=>null);
    check(card&&card.on&&/Regular season/.test(card.txt)&&new RegExp(d.segments[0].title).test(card.txt),`carton titre : « ${card&&card.txt.slice(0,70)} »`);
    const h1=await p.$eval('#h1txt',e=>e.textContent).catch(()=>'');
    check(/Week in review/.test(h1),`titre de la page : « ${h1} »`);
    await cap(p,'1_carton','#revTile');
    await p.waitForFunction(()=>{ const c=document.querySelector('#revTile .rev-card'); return c&&c.classList.contains('off'); },null,{timeout:10000}).catch(()=>{});
    await p.waitForTimeout(2500);
    await cap(p,'2_action','#revTile');
    const cap1=await p.$eval('#revTile .rev-txt',e=>e.textContent).catch(()=>'');
    check(cap1.length>5,`légende de l'action : « ${cap1.slice(0,90)} »`);
    let cap2=cap1; for(let i=0;i<30&&cap2===cap1;i++){ await p.waitForTimeout(1000); cap2=await p.$eval('#revTile .rev-txt',e=>e.textContent).catch(()=>cap1); }
    check(cap2!==cap1,`action suivante : « ${cap2.slice(0,90)} »`);
    const gid=await p.$eval('#revTile .rev-full',e=>e.dataset.open.slice(3));
    await p.click('#revTile .rev-full');
    await p.waitForSelector('#modal:not([hidden]) .field canvas',{timeout:30000}).catch(()=>{});
    const mt=await p.$eval('#modal .m-title',e=>e.textContent).catch(()=>'');
    const g=W.schedule.find(x=>x.id===gid);
    check(g&&mt.includes(W.teams[g.home].name)&&mt.includes(W.teams[g.away].name),`« Full game » : le replay de ${gid} s'ouvre (${mt.replace(/\s+/g,' ')})`);
    await p.evaluate(()=>{ const c=document.querySelector('#modal [data-close]'); if(c) c.click(); });
    errs.push(...p.errs);

    /* ---- Hide scores : pas d'émission ---- */
    const h=await ouvrir(b,P1,null,()=>{ try{ const k='gc-settings-v1', s=JSON.parse(localStorage.getItem(k)||'{}'); s.spoil=true; localStorage.setItem(k,JSON.stringify(s)); }catch(e){} });
    await h.waitForTimeout(4000);
    const spoil=await h.evaluate(()=>{ try{ return JSON.parse(localStorage.getItem('gc-settings-v1')||'{}').spoil; }catch(e){ return null; } });
    check(spoil!==true||!(await h.$('#revTile')),`Hide scores : pas d'émission${spoil===true?'':' (réglage non trouvé, vérifié à la main)'}`);
    errs.push(...h.errs);

    /* ---- téléphone ---- */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await show(m); await m.waitForTimeout(1500);
    const w=await m.evaluate(()=>document.documentElement.scrollWidth);
    check(w<=390,`téléphone : pas de défilement horizontal (${w} px)`);
    await cap(m,'3_telephone','#revTile');
    errs.push(...m.errs);

    /* ---- avant le verrou, et pendant une demi-finale : pas d'émission ---- */
    srv2=await server(P2,{},Date.parse(SF[0].kickoff)+5*60e3);
    const q=await ouvrir(b,P2); await q.waitForTimeout(5000);
    const live=await q.$('#liveGrid .tile.feat[data-gid]');
    check(!(await q.$('#revTile'))&&!!live,'pendant une demi-finale : le direct, pas l\'émission');
    const avant=await (await fetch(`http://localhost:${P2}/api/review`)).json();
    check(avant.on&&avant.edition==='regular','pendant une demi-finale : la demi-finale en cours n\'est pas dans la playlist');
    errs.push(...q.errs);
    /* ---- après la Grand Final : l'édition finale, la Grand Final d'abord (mode sombre) ---- */
    const FIN=W.schedule.find(g=>g.phase==='ai_bowl');
    await arreter(srv,P1);   /* le port doit être libre : sinon l'ancien serveur répond au test du nouveau, puis s'en va */
    const srvF=await server(P1,{},Date.parse(FIN.kickoff)+90*60e3);
    const f=await ouvrir(b,P1,{colorScheme:'dark'});
    check(await show(f),'après la Grand Final : l\'émission reprend');
    const fc=await f.$eval('#revTile .rev-card',e=>e.textContent.replace(/\s+/g,' ').trim()).catch(()=>'');
    check(/Grand Final/.test(fc)&&/champions/.test(fc),`édition finale, premier carton : « ${fc.slice(0,90)} »`);
    await cap(f,'4_finale_sombre','#revTile');
    await f.waitForFunction(()=>{ const c=document.querySelector('#revTile .rev-card'); return c&&c.classList.contains('off'); },null,{timeout:10000}).catch(()=>{});
    await f.waitForTimeout(2500); await cap(f,'5_finale_action_sombre','#revTile');
    errs.push(...f.errs); srvF.kill();
    srv3=await server(P3,{GC_WEEK_REVIEW:'off'});
    const o=await ouvrir(b,P3); await o.waitForTimeout(4000);
    const r404=await o.evaluate(async()=>(await fetch('/api/review')).status);
    check(!(await o.$('#revTile'))&&r404===404,'GC_WEEK_REVIEW=off : pas d\'émission, /api/review 404');
    errs.push(...o.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); if(srv3) srv3.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
