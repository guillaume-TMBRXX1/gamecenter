// « Interface motion » (README sections 119, 120 et 121) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_effets.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Un réglage de Settings › Display, coupé par défaut. Les visuels de match des sections 118 et 119 ont été retirés
// (section 120) : le test vérifie aussi que leurs interrupteurs n'existent plus.
//   · sans rien toucher : interrupteur éteint, pas de classe d'animation, aucun des cinq réglages retirés ;
//   · après un vrai clic : réglage enregistré ; un onglet ouvert arrive en cascade ; une cote cliquée vole vers le
//     bulletin et le gain potentiel roule jusqu'à sa valeur ; le grand écran d'un match s'ouvre sans erreur ;
//   · section 121 : onglet en 180 ms ; cascade du Schedule une seule fois par visite (30 ms d'écart) ; « Bet placed »
//     à la place du bouton et vibration courte à la pose d'un pari, puis retour à l'état normal ; score qui bascule sur
//     un touchdown (6 points d'un coup) mais pas sur un field goal ; dernier point de la courbe qui bat à chaque action ;
//     silhouettes des cartes pendant un premier chargement bridé, retirées au premier dessin ;
//   · après rechargement : réglage gardé ; un clic le recoupe ; aucune erreur JS ;
//   · « réduire les animations » : réglage allumé mais aucune animation (ni silhouettes, ni cascade, ni bascule).
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
    const vue=()=>p.evaluate(()=>{ window.__gc.season.setView('schedule'); const el=document.getElementById('viewSchedule'), cs=getComputedStyle(el.firstElementChild);
      const it=[...el.querySelectorAll('.mo-it')]; return {in:el.classList.contains('mo-in'),it:it.length,an:cs.animationName,dur:cs.animationDuration,
        d:it.slice(0,3).map(x=>getComputedStyle(x).animationDelay)}; });
    const V=await vue();
    check(V.in&&V.it>=3&&V.an==='moIn'&&V.dur==='0.18s',`onglet Schedule : fondu-glissé de ${V.dur}, ${V.it} lignes en cascade`);
    check(V.d.join(' ')==='0.04s 0.07s 0.1s',`30 ms d'écart entre deux lignes (${V.d.join(' ')})`);
    await p.waitForFunction(()=>!document.getElementById('viewSchedule').classList.contains('mo-in'),null,{timeout:5000});
    await p.evaluate(()=>window.__gc.season.setView('live')); await p.waitForTimeout(300);
    const V2=await vue();
    check(V2.in&&V2.an==='moIn'&&V2.it===0,`rouvert : le fondu-glissé de l'onglet rejoue, mais plus la cascade (une fois par visite)`);
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
      /* le pari posé : « Bet placed » remplace le bouton, le téléphone vibre, puis tout revient */
      const P=await p.evaluate(()=>new Promise(r=>{ window.__vib=[]; navigator.vibrate=x=>{ window.__vib.push(x); return true; };
        const b=document.getElementById('place'); if(b.disabled) return r({dis:true}); b.click();
        setTimeout(()=>{ const s=getComputedStyle(b,'::after'); r({ok:b.classList.contains('mo-ok'),after:s.content,foot:!document.getElementById('slipFoot').hidden,vib:window.__vib.slice()}); },300); }));
      check(P.ok&&/Bet placed/.test(P.after||'')&&P.foot,`pari posé : « Bet placed » à la place du bouton (${P.dis?'bouton désactivé':P.after})`);
      check(P.vib&&P.vib.length===1&&P.vib[0]<=20,`vibration courte (${JSON.stringify(P.vib)})`);
      await p.waitForTimeout(1400);
      const P2=await p.evaluate(()=>({ok:document.querySelectorAll('.cta.mo-ok').length,open:document.querySelector('.slip-tabs [data-tab="open"]').getAttribute('aria-selected'),foot:document.getElementById('slipFoot').hidden}));
      check(!P2.ok&&P2.open==='true'&&P2.foot,'1,3 s plus tard : le bulletin revient à son état normal (paris ouverts)');
    } else check(false,'une cote ouverte dans Schedule');

    /* le grand écran d'un match s'ouvre (il grandit depuis sa tuile ou monte), sa courbe se dessine */
    const M=await p.evaluate(F=>{ const G=window.__gc; G.season.setView('live'); G.openReplayFeed(F); const g=G.replayGame(); g.paused=true;
      const pn=document.querySelector('#modal .m-panel'), ch=document.querySelector('#modal [data-f="wpchart"] svg');
      return {open:!!G.getModalView(),panel:pn?pn.getAnimations().length:0,curve:ch?ch.getAnimations().length:0}; },F);
    check(M.open&&M.panel>=1,'grand écran : ouverture animée');
    check(M.curve>=1,'grand écran : la courbe de probabilité se dessine');
    /* action suivante : le dernier point bat ; un touchdown fait basculer le score, un field goal non */
    const C=await p.evaluate(async()=>{ const G=window.__gc, g=G.replayGame(); await new Promise(r=>setTimeout(r,1100));
      const i0=g.idx; g.paused=false; for(let k=0;k<4000&&g.idx===i0;k++) G.stepGame(g,0.05); g.paused=true;   /* jusqu'à l'action suivante */
      const dot=document.querySelector('#modal [data-f="wpchart"] .wp-dot');
      const sc=document.querySelector('#modal .sc[data-f="hs"]'), hs=g.hs; const out={pulse:dot?dot.getAnimations().length:0};
      g.hs=hs+3; G.updateGameUI(g); out.fg=sc.classList.contains('mo-flip'); out.fgBump=sc.classList.contains('bump');
      g.hs=hs+9; G.updateGameUI(g); out.td=sc.classList.contains('mo-flip'); out.txt=sc.textContent; out.an=getComputedStyle(sc).animationName;
      g.hs=hs; G.updateGameUI(g); return out; });
    check(C.pulse>=1,'action suivante : le dernier point de la courbe bat');
    check(!C.fg&&C.fgBump,'field goal (3 points) : pas de bascule, l\'effet d\'origine');
    check(C.td&&C.an==='moFlip',`touchdown (6 points) : le score bascule, valeur affichée tout de suite (${C.txt})`);
    await p.keyboard.press('Escape'); await p.waitForFunction(()=>!window.__gc.getModalView(),null,{timeout:10000});

    await ouvrir(p);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='true')&&R.body&&R.html,'après rechargement : le réglage est gardé');
    for(const n of NOMS) await p.click(`#viewSettings .switch[data-set="${n}"]`);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='false'&&R['ls_'+n]===false)&&!R.body&&!R.html,'un clic le recoupe, la classe d\'animation est retirée');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));

    /* premier chargement bridé : silhouettes des cartes, retirées au premier dessin de la grille */
    const c2=await b.newContext({viewport:{width:390,height:844}}); const p2=await c2.newPage();
    await c2.addInitScript(()=>{ try{ localStorage.setItem('gc-settings-v1','{"motion":true}'); }catch(e){} });
    const cdp=await c2.newCDPSession(p2); await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:100,downloadThroughput:1024*1024,uploadThroughput:256*1024});
    p2.goto(`http://localhost:${PORT}/`,{timeout:180000}).catch(()=>{});
    const S1=await p2.waitForFunction(()=>{ const s=document.querySelector('#liveGrid .mo-skt'); return s&&document.documentElement.classList.contains('mo-boot')&&s.offsetHeight>100&&{n:[...document.querySelectorAll('#liveGrid .mo-skt')].filter(x=>x.offsetHeight).length}; },null,{timeout:60000,polling:50}).then(h=>h.jsonValue()).catch(()=>null);
    await p2.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:180000});
    const S2=await p2.evaluate(()=>({boot:document.documentElement.classList.contains('mo-boot'),sk:document.querySelectorAll('.mo-skt').length,tiles:document.querySelectorAll('#liveGrid .tile').length}));
    check(!!S1&&S1.n>=1,`connexion lente : silhouette de carte pendant le chargement (${S1?S1.n:0} à 390 px)`);
    check(!S2.boot&&S2.sk===0&&S2.tiles>0,'la grille dessinée remplace les silhouettes');
    await c2.close();

    /* « réduire les animations » : rien ne bouge, même réglage allumé */
    const c3=await b.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'}); const p3=await c3.newPage();
    await c3.addInitScript(()=>{ try{ localStorage.setItem('gc-settings-v1','{"motion":true}'); }catch(e){} });
    await p3.goto(`http://localhost:${PORT}/`); await p3.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    const RM=await p3.evaluate(F=>{ const G=window.__gc; const boot=document.documentElement.classList.contains('mo-boot');
      G.season.setView('schedule'); const el=document.getElementById('viewSchedule');
      const o={boot,it:el.querySelectorAll('.mo-it').length,anim:el.getAnimations({subtree:true}).filter(a=>a.animationName==='moIn').length};
      G.season.setView('live'); G.openReplayFeed(F); const g=G.replayGame(); g.paused=true; const sc=document.querySelector('#modal .sc[data-f="hs"]');
      g.hs+=7; G.updateGameUI(g); o.flip=sc.classList.contains('mo-flip'); o.panel=document.querySelector('#modal .m-panel').getAnimations().filter(a=>!a.animationName).length; g.hs-=7; return o; },F);
    check(!RM.boot&&RM.it===0&&RM.anim===0&&!RM.flip&&RM.panel===0,`réduire les animations : ni silhouettes, ni cascade, ni bascule, ni ouverture animée (${JSON.stringify(RM)})`);
    await c3.close();
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
