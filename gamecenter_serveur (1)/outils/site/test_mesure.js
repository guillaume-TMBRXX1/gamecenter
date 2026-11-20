// Mesure de l'audience (promotion, étape 9.1 — 28/10/2026) — test navigateur (Playwright + serveurs réels, copie des
// semaines). node outils/site/test_mesure.js     (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Deux serveurs : 8150 avec GC_MESURE=1, 8151 sans (liens courts et /admin/stats en 404, page légale inchangée).
// Mesure allumée : /tt redirige vers l'accueil (302) et compte le clic ; l'accueil ouvert depuis TikTok compte une visite
// « tiktok », un robot ne compte pas ; /admin/stats : clé refusée, puis tableau (tuiles, semaines, sources, liens courts,
// ligne du bilan), session gardée dans l'onglet et fermée ; téléphone 390 px sans défilement horizontal, mode sombre ;
// page légale avec la phrase sur les totaux ; section 131 : personnes et retours (cases envoyées une fois par semaine,
// dates seules dans le navigateur, match ouvert, appareil exclu depuis /admin/stats) ; aucune erreur JS. SHOTS=<dossier> : captures du tableau de bord.
// Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const ON=8150, OFF=8151, KEY='une-cle-admin-assez-longue-pour-le-test', SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));
/* Chromium sans écran s'annonce « HeadlessChrome » (compté robot, comme voulu) : un vrai navigateur pour le test */
const UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-mesure-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_MESURE:'',GC_ADMIN_KEY:KEY},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; return p; } }catch(e){} await pause(250); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const stats=async()=>(await fetch(`http://localhost:${ON}/api/admin/stats`,{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({key:KEY,semaines:2})})).json();
const shot=async(p,nom)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.screenshot({path:path.join(SHOTS,nom),fullPage:true}); } };

(async()=>{
  const on=await server(ON,{GC_MESURE:'1'}), off=await server(OFF,{}), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    /* ---- mesure coupée : rien ---- */
    console.log('— mesure coupée (GC_MESURE absent)');
    for(const u of ['/tt','/ig','/yt','/r/hn','/admin/stats'])
      check((await fetch(`http://localhost:${OFF}${u}`,{redirect:'manual'})).status===404,`${u} : 404`);
    check((await fetch(`http://localhost:${OFF}/api/admin/stats`,{method:'POST',body:'{}'})).status===404,'/api/admin/stats : 404');
    check(!(await (await fetch(`http://localhost:${OFF}/legal`)).text()).includes('short links'),'page légale inchangée');

    /* ---- liens courts et visites ---- */
    console.log('— mesure allumée (GC_MESURE=1)');
    const r=await fetch(`http://localhost:${ON}/tt`,{redirect:'manual',headers:{'User-Agent':'Mozilla/5.0 (iPhone) Mobile'}});
    check(r.status===302&&r.headers.get('location')==='/','/tt → 302 vers l’accueil');
    await fetch(`http://localhost:${ON}/`,{headers:{'User-Agent':'Mozilla/5.0 (compatible; Googlebot/2.1)'}});
    const ctx=await b.newContext({viewport:{width:1440,height:950},userAgent:UA}), p=await ctx.newPage();
    p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${ON}/ig`,{waitUntil:'domcontentloaded',timeout:90000});
    check(new URL(p.url()).pathname==='/','/ig ouvre l’accueil');
    await p.goto(`http://localhost:${ON}/`,{waitUntil:'domcontentloaded',timeout:90000,referer:'https://www.tiktok.com/@snapline.live'});
    await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    const s=(await stats()).semaines[0];
    check(s.liens.tt===1&&s.liens.ig===1,`clics comptés (tt ${s.liens.tt}, ig ${s.liens.ig})`);
    check(s.sources.tiktok===1,'visite venue de TikTok comptée « tiktok »');
    check(s.robots===1,'le robot compté à part');
    check(s.visites===2,`visites (${s.visites}) : /ig puis TikTok ; le robot n’y est pas`);

    /* ---- tableau de bord ---- */
    await p.goto(`http://localhost:${ON}/admin/stats`,{waitUntil:'domcontentloaded'});
    await p.fill('#key','mauvaise-cle'); await p.click('#keyForm button');
    await p.waitForFunction(()=>document.getElementById('out').textContent.length>0);
    check((await p.textContent('#out'))==='Clé refusée.','mauvaise clé refusée');
    check(await p.isHidden('#app'),'tableau caché sans la clé');
    await p.fill('#key',KEY); await p.click('#keyForm button');
    await p.waitForSelector('#app:not([hidden])',{timeout:5000});
    check((await p.$$('#tiles .tile')).length===9,'9 tuiles (dont personnes, revenues, matchs : section 131)');
    check((await p.$$('#weeks tbody tr')).length===12,'12 semaines');
    const src=await p.$$eval('#sources tbody tr td:first-child',x=>x.map(e=>e.textContent));
    check(src.includes('tiktok'),`sources : ${src.join(', ')}`);
    const lk=await p.$$eval('#links tbody tr td:first-child',x=>x.map(e=>e.textContent));
    check(lk.includes('/tt')&&lk.includes('/ig'),`liens courts : ${lk.join(', ')}`);
    const bil=await p.inputValue('#bilan');
    check(/^\| \d\d\/\d\d \|( \|){4} \d+ \| \d+ \| \d+ \/ \d+ \/ \d+ \| \d+ \| \d+ \| \d+ \| \|$/.test(bil),`ligne du bilan : ${bil}`);
    await shot(p,'admin_stats_ordinateur.png');
    await p.reload({waitUntil:'domcontentloaded'});
    await p.waitForSelector('#app:not([hidden])',{timeout:5000});
    check(true,'session gardée après rechargement');
    await p.click('#logout');
    check(await p.isVisible('#login')&&await p.isHidden('#app'),'session fermée');
    check(!(await p.evaluate(()=>sessionStorage.getItem('gc-admin-stats-key'))),'clé effacée de l’onglet');
    await ctx.close();

    /* ---- téléphone, mode sombre ---- */
    const m=await b.newContext({viewport:{width:390,height:844},deviceScaleFactor:2,colorScheme:'dark'}), q=await m.newPage();
    q.on('pageerror',e=>errs.push(e.message));
    await q.goto(`http://localhost:${ON}/admin/stats`,{waitUntil:'domcontentloaded'});
    await q.fill('#key',KEY); await q.click('#keyForm button');
    await q.waitForSelector('#app:not([hidden])',{timeout:5000});
    check(await q.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'390 px : pas de défilement horizontal');
    check(await q.evaluate(()=>document.documentElement.getAttribute('data-theme'))==='dark','mode sombre');
    await shot(q,'admin_stats_telephone.png');
    await m.close();

    /* ---- section 131 : des personnes, et des personnes qui reviennent ---- */
    console.log('— personnes et retours (section 131)');
    const env=[];   /* les cases envoyées par la page */
    const P=await b.newContext({viewport:{width:1280,height:900},userAgent:UA});
    P.on('request',r=>{ if(r.url().endsWith('/api/m')){ try{ env.push(JSON.parse(r.postData()).k.join(',')); }catch(e){} } });
    const pp=await P.newPage(); pp.on('pageerror',e=>errs.push(e.message));
    const avant=(await stats()).semaines[0];
    const charger=async()=>{ await pp.goto(`http://localhost:${ON}/`,{waitUntil:'domcontentloaded',timeout:90000});
      await pp.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); await pause(1500); };
    await charger();
    check(env[0]==='p:vu,p:nouveau','première visite : « p:vu, p:nouveau » (une personne, nouvelle)');
    const st=await pp.evaluate(()=>JSON.parse(localStorage.getItem('gc-m-v1')||'{}'));
    check(st.first&&st.seen===st.first&&Object.keys(st).every(k=>['first','seen','match'].includes(k))&&/^\d{4}-\d{2}-\d{2}$/.test(st.seen),
      `le navigateur ne garde que des dates de semaine (${JSON.stringify(st)})`);
    await charger();
    check(env.length===1,'rechargée la même semaine : rien de plus');
    await pp.evaluate(()=>{ const s=JSON.parse(localStorage.getItem('gc-m-v1')); const w=d=>{ const u=new Date(s.seen+'T00:00:00Z'); u.setUTCDate(u.getUTCDate()-d); return u.toISOString().slice(0,10); };
      s.first=w(21); s.seen=w(7); delete s.match; localStorage.setItem('gc-m-v1',JSON.stringify(s)); });
    await charger();
    check(env[1]==='p:vu,p:revenu,p:retenu','venue la semaine d’avant : « p:vu, p:revenu, p:retenu »');
    await pp.evaluate(()=>{ const b=document.querySelector('[data-open]'); if(b) b.click(); }); await pause(1200);
    check(env[2]==='p:match','un match ouvert : « p:match », une fois');
    await pp.keyboard.press('Escape'); await pause(300);
    await pp.evaluate(()=>{ const b=document.querySelector('[data-open]'); if(b) b.click(); }); await pause(800);
    check(env.length===3,'un second match la même semaine : rien de plus');
    const apres=(await stats()).semaines[0];
    check(apres.personnes-avant.personnes===2&&apres.nouveaux-avant.nouveaux===1&&apres.revenus-avant.revenus===1&&apres.retenus-avant.retenus===1&&apres.matchs-avant.matchs===1,
      'le tableau de bord les additionne (personnes +2, nouvelles +1, revenues +1, dont la semaine d’avant +1, matchs +1)');
    /* l'administrateur exclut son appareil depuis /admin/stats */
    const ad=await P.newPage(); await ad.goto(`http://localhost:${ON}/admin/stats`);
    await ad.fill('#key',KEY); await ad.click('#keyForm button'); await ad.waitForSelector('#people tbody tr',{timeout:10000});
    check((await ad.textContent('#meBtn')).includes('Ne plus compter'),'« Cet appareil » : compté au départ');
    await ad.click('#meBtn');
    check((await ad.textContent('#meTxt')).includes("n'est pas compté")&&(await P.cookies()).some(c=>c.name==='gc_moi'&&c.value==='1'),'« Ne plus compter cet appareil » : cookie gc_moi posé');
    await pp.evaluate(()=>localStorage.removeItem('gc-m-v1'));
    const v0=(await stats()).semaines[0].visites;
    await charger();
    check(env.length===3,'appareil exclu : la page n’envoie rien');
    check((await stats()).semaines[0].visites===v0,'appareil exclu : l’accueil ouvert n’est pas compté');
    await ad.click('#meBtn');
    check(!(await P.cookies()).some(c=>c.name==='gc_moi'),'« Compter de nouveau » : cookie retiré');
    await P.close();

    /* ---- page légale ---- */
    const lg=await (await fetch(`http://localhost:${ON}/legal`)).text();
    check(lg.includes('short links')&&lg.includes('no IP address or identifier is kept'),'page légale : la phrase sur les totaux');
    check(lg.includes('three dates in its own storage'),'page légale : la phrase sur les dates gardées par le navigateur');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.log('  ✗ '+(e.stack||e)); fail++; }
  finally{
    await b.close(); for(const s of [on,off]){ s.kill(); try{ fs.rmSync(s.data,{recursive:true,force:true}); }catch(e){} }
  }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
