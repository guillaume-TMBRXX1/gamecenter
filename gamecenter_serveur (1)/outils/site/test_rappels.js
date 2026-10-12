// Rappels 10 min avant le coup d'envoi (bloc 2, étape 6 — 12/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_rappels.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn/pywebpush, Playwright)
// Serveur sur une copie des données, envois simulés (GC_PUSH_FAKE=1 : rien ne part sur le réseau, le serveur les note),
// horloge (GC_DEMO_AT) 20 s avant la fenêtre de rappel d'un créneau de la dernière semaine. Le service de notification du
// navigateur est remplacé par un abonnement factice (le réseau des tests n'atteint pas les vrais services).
// Vérifie : service worker, manifeste et icônes servis ; Réglages → Notifications (activer, « Send a test », « My team's
// games » pour un compte avec une équipe) ; cloche d'un match du calendrier ; rappels envoyés par le serveur dans la
// fenêtre (équipe favorite + cloche, une fois chacun, sans score, lien ?watch=) ; ?watch= ouvre le match (en direct ou
// terminé) ; désactiver ; mobile 390 px ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8139, URL0=`http://localhost:${PORT}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const reg=W.schedule.filter(g=>g.phase==='regular'), SLOT=6;
const slot=reg.filter(g=>g.slot===SLOT), KO=Date.parse(slot[0].kickoff);
const G1=slot[0], G2=slot[1];                                   // G1 : équipe favorite · G2 : cloche
const AT=new Date(KO-10*60e3-20e3).toISOString();

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-rappels-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT,GC_PUSH_FAKE:'1',GC_PUSH_TICK:'2'}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(URL0+'/api/time'); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(u,body)=>{ const r=await fetch(URL0+'/api'+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}); return {status:r.status,json:await r.json().catch(()=>null)}; };
/* abonnement factice : PushManager et la permission, comme sur un appareil qui accepte */
const FAUX=()=>{
  const sub=n=>({endpoint:'https://push.example/'+n,expirationTime:null,toJSON(){ return {endpoint:this.endpoint,keys:{p256dh:'BTestKey_'+n,auth:'authKey_'+n}}; },unsubscribe:async()=>{ window.__sub=null; return true; }});
  window.__sub=null;
  PushManager.prototype.getSubscription=async function(){ return window.__sub; };
  PushManager.prototype.subscribe=async function(){ window.__sub=sub(Math.random().toString(36).slice(2,10)); return window.__sub; };
  Object.defineProperty(Notification,'permission',{get:()=>'granted'});
  Notification.requestPermission=async()=>'granted';
};
const ouvrir=async(b,opts,q='')=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  await ctx.addInitScript(FAUX); const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(URL0+'/'+q); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); return p; };

(async()=>{
  console.log(`${week} · créneau ${SLOT} (${G1.away}@${G1.home}, ${G2.away}@${G2.home}) · horloge ${AT}`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    /* ---- fichiers de l'application ---- */
    for(const [u,type] of [['/sw.js','javascript'],['/manifest.webmanifest','manifest+json'],['/icons/icon-192.png','image/png'],['/icons/icon-512.png','image/png'],['/icons/icon-180.png','image/png']]){
      const r=await fetch(URL0+u); check(r.ok&&(r.headers.get('content-type')||'').includes(type),`${u} servi (${r.status}, ${r.headers.get('content-type')})`); }
    check((await fetch(URL0+'/icons/../serveur.py')).status===404,'icônes : rien d\'autre n\'est servi');
    const k=await api('/push/key'); check(k.json.enabled&&k.json.minutes===10,'API : rappels actifs, 10 minutes');

    /* ---- compte avec équipe favorite (G1.home) ---- */
    const r=await api('/account/register',{pseudo:'RappelTest',password:'motdepasse1'});
    await api('/account/team',{token:r.json.token,team:G1.home});
    const p=await ouvrir(b);
    await p.evaluate(([t,team])=>{ localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:'RappelTest',account:true,fav_team:team})); },[r.json.token,G1.home]);
    await p.reload(); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
    await p.click('.rail-btn[data-view="settings"]');
    await p.waitForSelector('#pushCard [data-push="on"]:not([disabled])',{timeout:15000}).catch(async e=>{ console.log('   carte :',await p.$eval('#pushCard',x=>x.textContent).catch(()=>'absente'),p.errs); throw e; });
    check(await p.$eval('[data-set="spoil"]',()=>true),'Réglages : carte Notifications');
    await p.click('#pushCard [data-push="on"]');
    await p.waitForSelector('#pushCard [data-push="off"][aria-checked="true"]',{timeout:10000});
    check(await p.getAttribute('#pushCard [data-push="fav"]','aria-checked')==='true',"« My team's games » coché (compte avec équipe)");
    await p.click('#pushCard [data-push="test"]'); await p.waitForTimeout(800);
    let log=(await api('/push/_log')).json.sent;
    check(log.some(x=>x.tag==='test'&&x.endpoint.startsWith('https://push.example/')),'« Send a test » : une notification envoyée à cet appareil');

    /* ---- cloche sur G2 dans le calendrier ---- */
    await p.click('.rail-btn[data-view="schedule"]'); await p.waitForSelector(`[data-bell="${G2.id}"]`,{timeout:10000});
    await p.click(`[data-bell="${G2.id}"]`); await p.waitForSelector(`[data-bell="${G2.id}"][aria-pressed="true"]`,{timeout:10000});
    check(true,`cloche posée sur ${G2.away}@${G2.home}`);
    const bells=(await api('/push/bells?token='+encodeURIComponent(r.json.token))).json.games;
    check(bells.includes(G2.id),'cloche gardée par le serveur');

    /* ---- les rappels partent dans la fenêtre ---- */
    let mine=[];
    for(let i=0;i<30&&mine.length<2;i++){ await new Promise(x=>setTimeout(x,1000)); log=(await api('/push/_log')).json.sent;
      mine=log.filter(x=>x.url===`/?watch=${G1.id}`||x.url===`/?watch=${G2.id}`); }
    console.log('   rappels :',JSON.stringify(mine.map(x=>x.title)));
    check(mine.some(x=>x.url===`/?watch=${G1.id}`)&&mine.some(x=>x.url===`/?watch=${G2.id}`),'rappels envoyés : équipe favorite et cloche');
    check(mine.every(x=>/kickoff in (10|9) min/.test(x.title)),'« kickoff in 10 min »');
    const res=[G1,G2].map(g=>`${g.result.away}-${g.result.home}`);
    check(mine.every(x=>!res.some(s=>(x.title+x.body).includes(s))),'aucun score dans un rappel');
    await new Promise(x=>setTimeout(x,5000));
    log=(await api('/push/_log')).json.sent;
    check(log.filter(x=>x.url===`/?watch=${G1.id}`).length===1&&log.filter(x=>x.url===`/?watch=${G2.id}`).length===1,'une seule fois chacun');

    /* ---- ?watch= : le match s'ouvre ---- */
    const st=(await api('/delta')).json.state.schedule, live=st.find(g=>g.status==='live'), fin=st.filter(g=>g.status==='final').pop();
    const u=await ouvrir(b,{},'?watch='+G1.id);
    await u.waitForTimeout(1200);
    const toastTxt=await u.evaluate(()=>document.getElementById('toast').textContent);
    check(/kickoff at/.test(toastTxt)&&await u.evaluate(()=>!document.getElementById('viewLive').hidden)&&!/watch=/.test(await u.evaluate(()=>location.search)),
      `?watch=${G1.id} (à venir) : « ${toastTxt.trim()} », il s'ouvrira au coup d'envoi`);
    const q=live?await ouvrir(b,{},'?watch='+live.id):null;
    if(q){ await q.waitForFunction(()=>!document.getElementById('modal').hidden,null,{timeout:15000}).catch(()=>{});
      check(await q.evaluate(()=>!document.getElementById('modal').hidden),`?watch=${live.id} (en direct) : le match s'ouvre sur le grand écran`); }
    else console.log('   (aucun match en direct à cette heure : cas « en direct » non rejoué)');
    const f=await ouvrir(b,{},'?watch='+fin.id);
    await f.waitForTimeout(1500);
    check(await f.evaluate(()=>!document.getElementById('modal').hidden),`?watch=${fin.id} (terminé) : le replay s'ouvre`);
    errs.push(...u.errs,...(q?q.errs:[]),...f.errs);

    /* ---- désactiver ---- */
    await p.click('.rail-btn[data-view="settings"]'); await p.click('#pushCard [data-push="off"]');
    await p.waitForSelector('#pushCard [data-push="on"][aria-checked="false"]',{timeout:10000});
    check(true,'rappels désactivés sur cet appareil');
    errs.push(...p.errs);

    /* ---- mobile ---- */
    const m=await ouvrir(b,{viewport:{width:390,height:844},isMobile:true});
    await m.evaluate(()=>window.__gc.season.setView('settings')); await m.waitForSelector('#pushCard',{timeout:15000});
    check(await m.evaluate(()=>document.documentElement.scrollWidth)<=390,'mobile 390 px, Réglages : pas de défilement horizontal');
    await m.evaluate(()=>window.__gc.season.setView('schedule')); await m.waitForSelector('.sch-bell',{timeout:15000});
    check(await m.evaluate(()=>document.documentElement.scrollWidth)<=390,'mobile 390 px, calendrier avec cloches : pas de défilement horizontal');
    errs.push(...m.errs);
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
