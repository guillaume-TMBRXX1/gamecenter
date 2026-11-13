// « Interface motion » (README sections 119 et 120) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_effets.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Un réglage de Settings › Display, coupé par défaut. Les visuels de match des sections 118 et 119 ont été retirés
// (section 120) : le test vérifie aussi que leurs interrupteurs n'existent plus.
//   · sans rien toucher : interrupteur éteint, pas de classe d'animation, aucun des cinq réglages retirés ;
//   · après un vrai clic : réglage enregistré ; un onglet ouvert arrive en cascade ; une cote cliquée vole vers le
//     bulletin et le gain potentiel roule jusqu'à sa valeur ; le grand écran d'un match s'ouvre sans erreur ;
//   · après rechargement : réglage gardé ; un clic le recoupe ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8187;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const NOMS=['motion'], RETIRES=['pawn','arc','slow','routes','club'];
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()[0], dir=path.join(WEEKS,w,'games');
  const f=fs.readdirSync(dir).sort()[0];
  return {F:JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')),src:`${w}/${f}`};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-effets-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:'auto'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const etat=p=>p.evaluate(N=>{ const o={}; let d={}; try{ d=JSON.parse(localStorage.getItem('gc-settings-v1')||'{}'); }catch(e){}
  for(const n of N){ const b=document.querySelector(`#viewSettings .switch[data-set="${n}"]`); o[n]=b?b.getAttribute('aria-checked'):null; o['ls_'+n]=d[n]; }
  o.body=document.body.classList.contains('mo-on'); o.html=document.documentElement.hasAttribute('data-mo'); return o; },NOMS);
const ouvrir=async p=>{ await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="motion"]'); };
const versSettings=async p=>{ await p.keyboard.press('Escape'); await p.waitForFunction(()=>!window.__gc.getModalView(),null,{timeout:10000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="motion"]'); };

(async()=>{
  const {F,src}=feed();
  console.log(`${src} · ${F.plays.length} actions`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await ouvrir(p);
    let R=await etat(p);
    check(NOMS.every(n=>R[n]==='false'&&R['ls_'+n]!==true),'« Interface motion » est présent et éteint par défaut');
    check(!R.body&&!R.html,'pas de classe d\'animation sur la page');
    const reste=await p.evaluate(N=>N.filter(n=>document.querySelector(`#viewSettings [data-set="${n}"]`)).concat(/Match visuals/.test(document.getElementById('viewSettings').textContent)?['Match visuals']:[]),RETIRES);
    check(!reste.length,'les cinq visuels de match retirés ne sont plus dans Settings'+(reste.length?' : '+reste:''));
    const ret0=await p.evaluate(()=>document.getElementById('tRet').textContent);

    for(const n of NOMS) await p.click(`#viewSettings .switch[data-set="${n}"]`);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='true'&&R['ls_'+n]===true),'un clic : interrupteur allumé, réglage enregistré');
    check(R.body&&R.html,'la page porte la classe d\'animation');

    /* interface : un onglet ouvert arrive en cascade */
    const V=await p.evaluate(()=>{ window.__gc.season.setView('schedule'); const el=document.getElementById('viewSchedule');
      return {in:el.classList.contains('mo-in'),it:el.querySelectorAll('.mo-it').length,an:getComputedStyle(el.firstElementChild).animationName}; });
    check(V.in&&V.it>=3&&V.an==='moIn',`onglet Schedule : arrivée en fondu-glissé, ${V.it} lignes en cascade`);
    await p.waitForFunction(()=>!document.getElementById('viewSchedule').classList.contains('mo-in'),null,{timeout:5000});
    /* interface : une cote cliquée vole vers le bulletin, le gain potentiel roule */
    const odd=p.locator('#viewSchedule .odd[data-key]:not([disabled])').first();
    if(await odd.count()){
      await odd.scrollIntoViewIfNeeded(); await odd.click();
      const vol=await p.evaluate(()=>!![...document.querySelectorAll('body>.odd[aria-hidden="true"]')].length);
      const mid=await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(document.getElementById('tRet').textContent)))));
      await p.waitForTimeout(1300);
      const fin=await p.evaluate(()=>({ret:document.getElementById('tRet').textContent,reste:document.querySelectorAll('body>.odd[aria-hidden="true"]').length,
        attendu:document.querySelector('#slipList')?document.getElementById('fabR').textContent:null}));
      check(vol,'la cote cliquée s\'envole vers le bulletin (copie posée au-dessus de la page)');
      check(fin.reste===0,'et la copie est retirée à l\'arrivée');
      check(fin.ret!==ret0&&fin.ret===fin.attendu,`le gain potentiel finit sur sa vraie valeur (${fin.ret})`);
      check(mid!==fin.ret,`en passant par des valeurs intermédiaires (${mid})`);
    } else check(false,'une cote ouverte dans Schedule');

    /* le grand écran d'un match s'ouvre (il grandit depuis sa tuile ou monte), sa courbe se dessine */
    const M=await p.evaluate(F=>{ const G=window.__gc; G.season.setView('live'); G.openReplayFeed(F); const g=G.replayGame(); g.paused=true;
      const pn=document.querySelector('#modal .m-panel'), ch=document.querySelector('#modal [data-f="wpchart"] svg');
      return {open:!!G.getModalView(),panel:pn?pn.getAnimations().length:0,curve:ch?ch.getAnimations().length:0}; },F);
    check(M.open&&M.panel>=1,'grand écran : ouverture animée');
    check(M.curve>=1,'grand écran : la courbe de probabilité se dessine');
    await p.keyboard.press('Escape'); await p.waitForFunction(()=>!window.__gc.getModalView(),null,{timeout:10000});

    await ouvrir(p);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='true')&&R.body&&R.html,'après rechargement : le réglage est gardé');
    for(const n of NOMS) await p.click(`#viewSettings .switch[data-set="${n}"]`);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='false'&&R['ls_'+n]===false)&&!R.body&&!R.html,'un clic le recoupe, la classe d\'animation est retirée');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
