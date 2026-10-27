// Ligues privées (bloc 2, étape 7 — 12/10/2026) — test navigateur (Playwright + serveur réel, copie des données).
//   node outils/site/test_ligues.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Vérifie : onglet Leagues (sans compte : invitation à en créer un) ; un compte crée une ligue (code, lien, classement) ;
// un ami ouvre le lien /?join=CODE sans compte, crée son compte et rejoint tout seul ; classement à deux ; le créateur
// renomme, change le code (l'ancien ne marche plus) et retire l'ami ; l'ami rejoint avec le nouveau code puis quitte ;
// mobile 390 px sans défilement horizontal ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8141, URL0=`http://localhost:${PORT}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-ligues-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0'}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(URL0+'/api/time'); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(u,body)=>{ const r=await fetch(URL0+'/api'+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}); return {status:r.status,json:await r.json().catch(()=>null)}; };
const ouvrir=async(b,q='',opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(URL0+'/'+q); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); return p; };
const connecter=async(p,tok,name)=>{ await p.evaluate(([t,n])=>localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:n,account:true})),[tok,name]);
  await p.reload(); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); };
const lignes=p=>p.$$eval('#viewLeagues tbody tr',rs=>rs.map(r=>r.querySelector('th').textContent.trim()));

(async()=>{
  const srv=await server(), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    const A=(await api('/account/register',{pseudo:'Capitaine',password:'motdepasse1'})).json;
    /* ---- sans compte ---- */
    const g=await ouvrir(b);
    await g.click('.rail-btn[data-view="leagues"]'); await g.waitForSelector('#viewLeagues .st-empty',{timeout:10000});
    check(/Create a free account/.test(await g.textContent('#viewLeagues')),'sans compte : invitation à créer un compte');
    errs.push(...g.errs);

    /* ---- le créateur ---- */
    const p=await ouvrir(b); await connecter(p,A.token,A.name);
    await p.click('.rail-btn[data-view="leagues"]'); await p.waitForSelector('#viewLeagues [data-lgform="create"]',{timeout:10000});
    await p.fill('#viewLeagues [data-lgform="create"] input','Les potes'); await p.click('#viewLeagues [data-lgform="create"] button');
    await p.waitForSelector('#viewLeagues .lg-code',{timeout:10000}).catch(async e=>{ console.log('   vue :',(await p.textContent('#viewLeagues')).replace(/\s+/g,' ').slice(0,400),p.errs); throw e; }); await p.waitForSelector('#viewLeagues tbody tr',{timeout:10000});
    const code=(await p.textContent('#viewLeagues .lg-code')).trim();
    check(/^[A-HJ-NP-Z2-9]{6}$/.test(code),`ligue créée, code ${code}`);
    check((await lignes(p)).length===1&&(await lignes(p))[0].includes('Capitaine'),'classement : le créateur seul');

    /* ---- l'ami : lien d'invitation sans compte, crée son compte, rejoint tout seul ---- */
    const f=await ouvrir(b,'?join='+code.toLowerCase());
    await f.waitForSelector('#viewLeagues .lg-invite',{timeout:10000});
    await f.waitForFunction(()=>/Les potes/.test(document.querySelector('#viewLeagues .lg-invite').textContent),null,{timeout:10000});
    const inv=await f.textContent('#viewLeagues .lg-invite');
    check(/Join Les potes/.test(inv)&&/created by Capitaine/.test(inv)&&/1 member/.test(inv),`lien d'invitation : « ${inv.replace(/\s+/g,' ').trim().slice(0,80)} »`);
    check(!/join=/.test(await f.evaluate(()=>location.search)),'le code ne reste pas dans l\'adresse');
    await f.click('#viewLeagues .lg-invite [data-view-go="settings"]'); await f.waitForSelector('#acForm',{timeout:10000});
    await f.fill('#acPseudo','Matelot'); await f.fill('#acPw','motdepasse2'); await f.click('#acGo');
    let B=null;
    for(let i=0;i<40&&!B;i++){ await f.waitForTimeout(250); B=await f.evaluate(()=>{ try{ return JSON.parse(localStorage.getItem('gc-player-v1')); }catch(e){ return null; } }); if(B&&!B.account) B=null; }
    let mesB=null; for(let i=0;i<20;i++){ mesB=(await api('/leagues?token='+B.token)).json; if(mesB.leagues.length) break; await f.waitForTimeout(250); }
    check(mesB.leagues.length===1&&mesB.leagues[0].name==='Les potes'&&!mesB.leagues[0].owner,'compte créé, ligue rejointe tout seul');
    await f.click('.rail-btn[data-view="leagues"]'); await f.waitForFunction(()=>document.querySelectorAll('#viewLeagues tbody tr').length===2,null,{timeout:10000});
    check(!(await f.$('#viewLeagues .lg-invite')),'invitation utilisée : elle disparaît');
    await f.click('#viewLeagues [data-lg="scope"][data-arg="season"]');
    await f.waitForFunction(()=>/Net P\/L/.test((document.querySelector('#viewLeagues thead')||{}).textContent||''),null,{timeout:10000});
    check((await lignes(f)).length===2,'classement de la saison : 2 membres');

    /* ---- droits du créateur ---- */
    await p.evaluate(()=>{ window.__gc.season.setView('live'); }); await p.click('.rail-btn[data-view="leagues"]');
    await p.click('#viewLeagues [data-lg="sel"]'); await p.waitForFunction(()=>document.querySelectorAll('#viewLeagues tbody tr').length===2,null,{timeout:15000});
    check(true,'le créateur voit l\'ami au classement');
    await p.fill('#viewLeagues [data-lgform="rename"] input','Les pirates'); await p.click('#viewLeagues [data-lgform="rename"] button');
    await p.waitForFunction(()=>/Les pirates/.test(document.querySelector('#viewLeagues .card-h h2:not(:first-child)')?.textContent||document.querySelector('#viewLeagues').textContent),null,{timeout:10000});
    check(/Les pirates/.test(await p.textContent('#viewLeagues')),'ligue renommée');
    await p.click('#viewLeagues [data-lg="confirm"][data-arg="code"]'); await p.click('#viewLeagues [data-lg="code"]');
    await p.waitForFunction(c=>document.querySelector('#viewLeagues .lg-code').textContent.trim()!==c,code,{timeout:10000});
    const code2=(await p.textContent('#viewLeagues .lg-code')).trim();
    check(code2!==code,`nouveau code ${code2}`);
    const kick=await p.$('#viewLeagues tbody tr .lg-x'); await kick.click();
    await p.click('#viewLeagues tbody tr .lg-x[data-lg="kick"]');
    await p.waitForFunction(()=>document.querySelectorAll('#viewLeagues tbody tr').length===1,null,{timeout:10000});
    check((await api('/leagues?token='+B.token)).json.leagues.length===0,'l\'ami retiré');

    /* ---- l'ami : ancien code refusé, nouveau code accepté, puis il quitte ---- */
    await f.evaluate(()=>window.__gc.season.setView('live')); await f.click('.rail-btn[data-view="leagues"]');
    await f.waitForSelector('#viewLeagues [data-lgform="join"]',{timeout:10000});
    await f.fill('#viewLeagues [data-lgform="join"] input',code); await f.click('#viewLeagues [data-lgform="join"] button');
    await f.waitForFunction(()=>/No league has this code/.test(document.querySelector('#viewLeagues .lg-err').textContent),null,{timeout:10000});
    check(true,'ancien code refusé (« No league has this code »)');
    await f.fill('#viewLeagues [data-lgform="join"] input',code2); await f.click('#viewLeagues [data-lgform="join"] button');
    await f.waitForFunction(()=>document.querySelectorAll('#viewLeagues tbody tr').length===2,null,{timeout:10000});
    check(/Les pirates/.test(await f.textContent('#viewLeagues')),'nouveau code : l\'ami revient');
    await f.click('#viewLeagues [data-lg="confirm"][data-arg="leave"]'); await f.click('#viewLeagues [data-lg="leave"]');
    await f.waitForFunction(()=>/No league yet/.test(document.querySelector('#viewLeagues').textContent),null,{timeout:10000});
    check((await api('/leagues?token='+B.token)).json.leagues.length===0,'l\'ami quitte la ligue');
    errs.push(...p.errs,...f.errs);

    /* ---- mobile ---- */
    const m=await ouvrir(b,'',{viewport:{width:390,height:844},isMobile:true}); await connecter(m,A.token,A.name);
    await m.evaluate(()=>window.__gc.season.setView('leagues')); await m.waitForSelector('#viewLeagues tbody tr',{timeout:15000});
    check(await m.evaluate(()=>document.documentElement.scrollWidth)<=390,'mobile 390 px : pas de défilement horizontal');
    errs.push(...m.errs);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
