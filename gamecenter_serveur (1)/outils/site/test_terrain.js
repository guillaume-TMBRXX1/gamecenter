// Le terrain d'abord (section 127, phase 1 de la relance — 18/11/2026) — test navigateur (Playwright + serveurs réels).
//   node outils/site/test_terrain.js        (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Deux serveurs pendant un créneau (GC_DEMO_AT) : 8240 avec GC_ACCUEIL_TERRAIN=off (la page d'avant : aucun script
// spect-boot, solde et ticket pour tous), 8241 par défaut, avec le bandeau d'accueil (GC_ACCUEIL=1).
// Vérifie : un nouveau venu n'a ni solde ni ticket (ordinateur : colonne de droite absente, la grille des matchs plus
// large ; téléphone : ni pastille « Balance » ni bouton « Bet slip ») dès la 1re image ; sur téléphone 390 × 844, le
// terrain du match vedette tient dans le premier écran, sans défilement horizontal ; toucher une cote remet le ticket,
// pour de bon (gc-bettor, après rechargement) ; qui a déjà parié (gc-bettor) ou a un compte le voit dès la 1re image ;
// décalages de mise en page (CLS) < 0,1 ; aucune erreur JS. SHOTS=<dossier> : captures. Lancé par tests_navigateur.sh.
let chromium, devices; try{ ({chromium,devices}=require('playwright')); }catch(e){ ({chromium,devices}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const reg=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const LIVE=new Date(Date.parse(reg.find(g=>g.slot===3).kickoff)+90e3).toISOString();        // pendant le 3e créneau

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-terrain-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:LIVE},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; break; } }catch(e){} await pause(250); }
  if(!p.data){ p.kill(); throw new Error('le serveur ne démarre pas'); }
  await (await fetch(`http://localhost:${port}/`)).text();          // 1re page d'un serveur neuf : lente (semaines à lire)
  return p;
}
/* décalages de mise en page (hors gestes) ; html.spect au premier dessin de la grille des matchs */
const OBS=()=>{ window.__ls=0; window.__first=null; new PerformanceObserver(l=>{ for(const e of l.getEntries()) if(!e.hadRecentInput) window.__ls+=e.value; }).observe({type:'layout-shift',buffered:true});
  new MutationObserver((m,o)=>{ if(document.getElementById('liveGrid')&&window.__first===null){ window.__first=document.documentElement.classList.contains('spect'); o.disconnect(); } })
    .observe(document,{childList:true,subtree:true}); };
const PHONE=Object.assign({},devices['iPhone 13']);
async function ouvrir(b,port,opts,init){
  const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:900}},opts||{}));
  await ctx.addInitScript(OBS);
  if(init) await ctx.addInitScript(init);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000});
  await p.waitForFunction(()=>window.__gc&&window.__gc.season&&document.querySelector('.tile.feat .field'),null,{timeout:90000});
  await pause(2500);
  return p;
}
const shot=async(p,nom)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.screenshot({path:path.join(SHOTS,nom)}); } };
const etat=p=>p.evaluate(()=>{ const d=e=>e?getComputedStyle(e).display:'absent', r=s=>{ const e=document.querySelector(s); return e?e.getBoundingClientRect():null; };
  return {spect:document.documentElement.classList.contains('spect'), first:window.__first, cls:window.__ls,
    slip:d(document.getElementById('slipCol')), fab:d(document.getElementById('fab')), pill:d(document.querySelector('.wallet-pill')),
    grid:(r('#liveGrid')||{}).width||0, field:r('.tile.feat .field'), tab:r('#tabbar'), vh:innerHeight,
    hscroll:document.documentElement.scrollWidth>innerWidth+1, bettor:localStorage.getItem('gc-bettor'),
    /* en cas d'échec : où commence chaque bloc au-dessus du terrain (polices, retours à la ligne) */
    blocs:['.topbar','#welcome','#welcome h2','.live-head','#liveGrid','.tile.feat'].map(s=>{ const b=r(s); return s+' '+(b&&b.height?Math.round(b.top)+'+'+Math.round(b.height):'—'); }).join(' · ')}; });
async function toucherCote(p){
  const o=await p.$('#liveGrid .odd:not(:disabled):not([aria-pressed="true"])');
  if(!o) return false;
  await o.click(); await pause(800); return true;
}

(async()=>{
  const off=await server(8240,{GC_ACCUEIL:'1',GC_ACCUEIL_TERRAIN:'off'}), on=await server(8241,{GC_ACCUEIL:'1'});
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    /* ---- GC_ACCUEIL_TERRAIN=off : la page d'avant ---- */
    console.log('— GC_ACCUEIL_TERRAIN=off');
    const h0=await (await fetch('http://localhost:8240/')).text();
    check(!h0.includes('id="spect-boot"'),'aucun script spect-boot dans le HTML');
    const z=await ouvrir(b,8240); let e=await etat(z);
    check(!e.spect&&e.first===false,'nouveau venu : pas de mode spectateur, dès la 1re image');
    check(e.slip!=='none','ordinateur : la colonne solde et ticket est là');
    errs.push(...z.errs); await z.context().close();

    /* ---- par défaut, nouveau venu sur ordinateur ---- */
    console.log('— nouveau venu, ordinateur 1440 × 900');
    const h1=await (await fetch('http://localhost:8241/')).text();
    check(h1.includes('id="spect-boot"'),'script spect-boot dans le <head>');
    const a=await ouvrir(b,8241); e=await etat(a);
    check(e.spect&&e.first===true,'mode spectateur dès la 1re image');
    check(e.slip==='none'&&e.pill==='none','ni colonne solde et ticket, ni pastille « Balance »');
    const gridSpect=e.grid;
    check(e.cls<0.1,`CLS ${e.cls.toFixed(3)} < 0,1`);
    await shot(a,'terrain-ordinateur.png');
    check(await toucherCote(a),'une cote sous un match se touche');
    e=await etat(a);
    check(!e.spect&&e.bettor==='1','la cote touchée remet le ticket (gc-bettor posé)');
    check(e.slip!=='none','la colonne solde et ticket revient');
    check(gridSpect>e.grid+200,`la grille des matchs était plus large sans la colonne (${Math.round(gridSpect)} > ${Math.round(e.grid)} px)`);
    await a.reload({waitUntil:'domcontentloaded'}); await a.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); await pause(1500);
    e=await etat(a);
    check(!e.spect&&e.first===false,'après rechargement : ticket dès la 1re image');
    errs.push(...a.errs); await a.context().close();

    /* ---- par défaut, nouveau venu sur téléphone ---- */
    console.log('— nouveau venu, téléphone 390 × 844');
    const m=await ouvrir(b,8241,PHONE); e=await etat(m);
    check(e.spect&&e.first===true,'mode spectateur dès la 1re image');
    check(e.fab==='none'&&e.pill==='none','ni bouton « Bet slip » ni pastille « Balance »');
    const bas=e.tab&&e.tab.height?e.tab.top:e.vh;
    check(!!e.field&&e.field.top>=0&&e.field.bottom<=bas+1,`le terrain du match vedette tient dans le premier écran (${e.field?Math.round(e.field.top)+'–'+Math.round(e.field.bottom):'—'} px, écran utile ${Math.round(bas)} px)`);
    console.log('    '+e.blocs);
    check(!e.hscroll,'aucun défilement horizontal');
    check(e.cls<0.1,`CLS ${e.cls.toFixed(3)} < 0,1`);
    await shot(m,'terrain-telephone.png');
    check(await toucherCote(m),'une cote sous un match se touche');
    e=await etat(m);
    check(!e.spect&&e.fab!=='none','la cote touchée fait apparaître le bouton « Bet slip »');
    errs.push(...m.errs); await m.context().close();

    /* ---- qui a déjà parié ou a un compte : le ticket dès la 1re image ---- */
    console.log('— déjà venu');
    const p1=await ouvrir(b,8241,null,()=>{ try{ localStorage.setItem('gc-bettor','1'); }catch(e){} }); e=await etat(p1);
    check(!e.spect&&e.first===false&&e.slip!=='none','gc-bettor : solde et ticket dès la 1re image');
    errs.push(...p1.errs); await p1.context().close();
    const p2=await ouvrir(b,8241,null,()=>{ try{ localStorage.setItem('gc-player-v1',JSON.stringify({token:'x',name:'Test',account:true})); }catch(e){} }); e=await etat(p2);
    check(!e.spect&&e.first===false,'compte connu (gc-player-v1, account) : solde et ticket dès la 1re image');
    errs.push(...p2.errs.filter(x=>!/401|token/i.test(x))); await p2.context().close();

    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(err){ console.error(err); fail++; }
  finally{
    await b.close();
    for(const s of [off,on]){ s.kill(); try{ fs.rmSync(s.data,{recursive:true,force:true}); }catch(e){} }
  }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon');
  process.exit(fail?1:0);
})();
