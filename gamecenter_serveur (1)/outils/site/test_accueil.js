// Première visite (promotion, étape 9.3 — 29/10/2026) — test navigateur (Playwright + serveurs réels, copie des semaines).
//   node outils/site/test_accueil.js        (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Trois serveurs, l'horloge fixée par GC_DEMO_AT : 8160 sans GC_ACCUEIL (la page d'avant : bandeau caché, aucun script,
// aucun bloc retenu), 8161 avec, un mardi à 6 h (aucun match en direct : « Watch a full game » ouvre un replay, l'heure
// du prochain coup d'envoi est donnée), 8162 avec, pendant un créneau (« Watch live now » ouvre le match en direct).
// Vérifie : bandeau visible dès la 1re image pour un nouveau venu, caché pour qui est déjà venu (gc-player-v1) ; fermé,
// il ne revient pas ; « How it works » mène à « What is Snapline? » ; décalages de mise en page (CLS) < 0,1 sur
// ordinateur et téléphone ; blocs sous la grille rendus après son 1er dessin ; téléphone 390 px sans défilement
// horizontal, mode sombre ; aucune erreur JS. SHOTS=<dossier> : captures. Lancé par tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const reg=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const LIVE=new Date(Date.parse(reg.find(g=>g.slot===3).kickoff)+90e3).toISOString();        // pendant le 3e créneau
const NUIT=new Date(Date.parse(reg[0].kickoff)+20*3600e3).toISOString();                    // le lendemain à 6 h

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-accueil-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_ACCUEIL:''},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; break; } }catch(e){} await pause(250); }
  if(!p.data){ p.kill(); throw new Error('le serveur ne démarre pas'); }
  await (await fetch(`http://localhost:${port}/`)).text();          // 1re page d'un serveur neuf : lente (semaines à lire)
  return p;
}
/* décalages de mise en page depuis le chargement (hors gestes de l'utilisateur) */
const CLS=()=>{ window.__ls=0; window.__first=null; new PerformanceObserver(l=>{ for(const e of l.getEntries()) if(!e.hadRecentInput) window.__ls+=e.value; }).observe({type:'layout-shift',buffered:true});
  new MutationObserver((m,o)=>{ const w=document.getElementById('welcome'); if(w&&window.__first===null){ window.__first=getComputedStyle(w).display!=='none'&&!w.hidden; o.disconnect(); } })
    .observe(document,{childList:true,subtree:true}); };
async function ouvrir(b,port,opts,init){
  const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:900}},opts||{}));
  await ctx.addInitScript(CLS);
  if(init) await ctx.addInitScript(init);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000});
  await p.waitForFunction(()=>window.__gc&&window.__gc.season&&!document.documentElement.classList.contains('gc-boot'),null,{timeout:90000});
  await pause(2500);
  return p;
}
const shot=async(p,nom)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.screenshot({path:path.join(SHOTS,nom)}); } };
const visible=p=>p.evaluate(()=>{ const w=document.getElementById('welcome'); return !!w&&!w.hidden&&getComputedStyle(w).display!=='none'; });

(async()=>{
  const off=await server(8160,{GC_DEMO_AT:NUIT}), nuit=await server(8161,{GC_ACCUEIL:'1',GC_DEMO_AT:NUIT}), live=await server(8162,{GC_ACCUEIL:'1',GC_DEMO_AT:LIVE});
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    /* ---- sans GC_ACCUEIL : la page d'avant ---- */
    console.log('— sans GC_ACCUEIL');
    const html=await (await fetch('http://localhost:8160/')).text();
    check(html.includes('id="welcome" aria-labelledby="welcomeTitle" hidden>'),'bandeau caché dans le HTML');
    check(!html.includes("classList.add('gc-boot')"),'aucun script de première visite');
    const z=await ouvrir(b,8160);
    check(!(await visible(z)),'aucun bandeau à l’écran');
    check(await z.evaluate(()=>!document.documentElement.classList.contains('gc-seen')&&!!document.querySelector('#about')&&getComputedStyle(document.querySelector('#about')).display!=='none'),'« What is Snapline? » affiché');
    errs.push(...z.errs); await z.context().close();

    /* ---- nouveau venu, la nuit : un replay ---- */
    console.log('— nouveau venu, aucun match en direct');
    const p=await ouvrir(b,8161);
    check(await p.evaluate(()=>window.__first===true),'bandeau visible dès la 1re image');
    check(await visible(p),'bandeau affiché');
    check((await p.textContent('#welcomeTitle'))==='24 AI coaches. Every game played live.','titre');
    check((await p.textContent('#welcomeWatch'))==='Watch a full game','bouton : « Watch a full game »');
    const nx=await p.textContent('#welcomeNext');
    check(/^No game live right now · next kickoff .+ Brussels, in \d/.test(nx),`prochain coup d’envoi : ${nx}`);
    const cls=await p.evaluate(()=>window.__ls);
    check(cls<0.1,`ordinateur : CLS ${cls.toFixed(3)} < 0,1`);
    check(await p.evaluate(()=>getComputedStyle(document.getElementById('about')).display!=='none'&&document.querySelectorAll('#liveGrid .tile').length>0),'grille dessinée, puis « What is Snapline? »');
    await shot(p,'accueil_ordinateur_nuit.png');
    await p.click('#welcomeMore'); await pause(600);
    check(await p.evaluate(()=>{ const r=document.getElementById('about').getBoundingClientRect(); return r.top<innerHeight&&r.bottom>0; }),'« How it works » mène à « What is Snapline? »');
    await p.evaluate(()=>scrollTo(0,0));
    await p.click('#welcomeWatch');
    await p.waitForFunction(()=>document.getElementById('modal')&&document.getElementById('modal').classList.contains('open'),null,{timeout:10000}).catch(()=>{});
    check(await p.evaluate(()=>!!window.__gc.replayGame()),'un match terminé s’ouvre en replay sur le grand écran');
    check(await p.evaluate(()=>localStorage.getItem('gc-welcome-v1')==='1'),'le bandeau ne reviendra pas');
    await p.reload({waitUntil:'domcontentloaded'});
    await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); await pause(1000);
    check(!(await visible(p))&&await p.evaluate(()=>window.__first===false),'rechargée : plus de bandeau, dès la 1re image');
    errs.push(...p.errs); await p.context().close();

    /* ---- fermé à la croix ---- */
    const q=await ouvrir(b,8161);
    await q.click('#welcomeClose');
    check(!(await visible(q)),'fermé à la croix');
    check(await q.evaluate(()=>document.activeElement&&document.activeElement.matches('.live-head h1')),'le focus passe au titre de la page');
    errs.push(...q.errs); await q.context().close();

    /* ---- déjà venu (clé de joueur dans le navigateur) ---- */
    const r=await ouvrir(b,8161,null,()=>localStorage.setItem('gc-player-v1',JSON.stringify({token:'x',name:'Guest'})));
    check(await r.evaluate(()=>window.__first===false)&&!(await visible(r)),'déjà venu : pas de bandeau, dès la 1re image');
    errs.push(...r.errs.filter(e=>!/401|token/i.test(e))); await r.context().close();

    /* ---- pendant un créneau : le direct ---- */
    console.log('— nouveau venu, matchs en direct');
    const L=await ouvrir(b,8162);
    check((await L.textContent('#welcomeWatch'))==='Watch live now','bouton : « Watch live now »');
    check(/ vs .+ · on the field right now$/.test(await L.textContent('#welcomeNext')),'le match en direct est nommé');
    await L.click('#welcomeWatch');
    await L.waitForFunction(()=>{ const m=window.__gc.getModalView&&window.__gc.getModalView(); return !!m; },null,{timeout:15000}).catch(()=>{});
    check(await L.evaluate(()=>!!window.__gc.getModalView()),'le match en direct s’ouvre sur le grand écran');
    errs.push(...L.errs); await L.context().close();

    /* ---- téléphone, mode sombre ---- */
    const m=await ouvrir(b,8161,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,colorScheme:'dark'});
    const clsM=await m.evaluate(()=>window.__ls);
    check(clsM<0.1,`téléphone : CLS ${clsM.toFixed(3)} < 0,1`);
    check(await m.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'390 px : pas de défilement horizontal');
    const bw=await m.evaluate(()=>{ const r=document.getElementById('welcomeWatch').getBoundingClientRect(); return [r.width,r.height]; });
    check(bw[0]>=300&&bw[1]>=44,`bouton pleine largeur, assez haut (${bw.map(Math.round).join('×')})`);
    await shot(m,'accueil_telephone_sombre.png');
    errs.push(...m.errs); await m.context().close();

    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.log('  ✗ '+(e.stack||e)); fail++; }
  finally{
    await b.close(); for(const s of [off,nuit,live]){ s.kill(); try{ fs.rmSync(s.data,{recursive:true,force:true}); }catch(e){} }
  }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
