// Créer un compte et choisir sa franchise (BD-2 bis, section 132, 20/11/2026) — test navigateur (Playwright + serveur).
//   node outils/site/test_compte.js          (depuis « gamecenter_serveur (1) »)
//   SHOTS=<dossier> node outils/site/test_compte.js     (captures)
// Vérifie : un invité voit « Sign up » dans la barre du haut (pas un compte) ; la fenêtre « Join Snapline » s'ouvre,
// garde le focus (Tab ne sort pas), se ferme avec Échap et rend le focus ; erreurs (pseudo trop court, mot de passe) ;
// création du compte sur la clé d'invité (son pari reste) ; 2e écran : les 24 franchises, « Follow … », la franchise
// enregistrée (API) ; 3e écran puis My team ouvert sur elle ; « Sign up » disparaît ; Settings d'un invité : deux boutons
// qui ouvrent la fenêtre (plus de formulaire) ; « Sign in » depuis la fenêtre ; « Skip for now » ; les invitations
// (My team, classement de la saison) ouvrent la fenêtre ; téléphone 390 px (feuille en bas, sans défilement horizontal) ;
// aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const DEMO=new Date(Date.parse(REG[Math.floor(REG.length*0.5)].kickoff)-5*60e3).toISOString();

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-compte-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:DEMO},env||{}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api${u}`,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
const ouvrir=async(b,port,opts,init)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  if(init) await ctx.addInitScript(init[0],init[1]);
  await p.goto(`http://localhost:${port}/`,{timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p; };
const shot=async(p,nom,el)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.waitForTimeout(700);
  if(el){ const h=await p.$(el); if(h){ await h.screenshot({path:path.join(SHOTS,nom)}); return; } } await p.screenshot({path:path.join(SHOTS,nom)}); } };
const vue=async(p,v)=>{ const b=await p.$(`.rail-btn[data-view="${v}"]`); if(b&&await b.isVisible()) await b.click(); else await p.evaluate(v=>document.querySelector(`.rail-btn[data-view="${v}"]`).click(),v); };
const ouverte=p=>p.$eval('#join',e=>!e.hidden).catch(()=>false);

(async()=>{
  const P1=8175;
  const srv=await server(P1), b=await chromium.launch({executablePath:EXE});
  try{
    console.log(`   semaine ${DERNIERE}, horloge ${DEMO}`);
    /* un invité qui a déjà parié : sa clé et son pari */
    const inv=(await api(P1,'/players',{name:'Invité Test'})).json;
    const g=REG[Math.floor(REG.length*0.5)], key=`${g.id}:ml:home`;
    let bet=(await api(P1,'/bets',{token:inv.token,picks:[{key,price_dec:2.0,line:null,stake:10,title:'x'}],combos:[]})).json;
    const q=bet&&bet.rejected&&bet.rejected[0];                    /* cote du moment, renvoyée avec le refus */
    if(q&&q.reason==='price') bet=(await api(P1,'/bets',{token:inv.token,picks:[{key,price_dec:q.price_dec,line:q.line,stake:10,title:'x'}],combos:[]})).json;
    check(bet&&bet.accepted&&bet.accepted.length===1,'invité : un pari posé avant de créer son compte');
    const p=await ouvrir(b,P1,null,[([t])=>localStorage.setItem('gc-player-v1',JSON.stringify({token:t,name:'Invité Test',account:false})),[inv.token]]);
    check(await p.$eval('#joinBtn',e=>!e.hidden&&e.getClientRects().length>0),'invité : « Sign up » dans la barre du haut');
    await shot(p,'compte-barre-du-haut.png','.topbar');
    await p.click('#joinBtn');
    await p.waitForSelector('#joinForm');
    check(await ouverte(p)&&/Join Snapline/.test(await p.textContent('#join')),'la fenêtre « Join Snapline » s\'ouvre');
    check(await p.evaluate(()=>document.querySelector('#join .join-card').contains(document.activeElement)),'le focus est dans la fenêtre');
    for(let i=0;i<12;i++) await p.keyboard.press('Tab');
    check(await p.evaluate(()=>document.querySelector('#join .join-card').contains(document.activeElement)),'Tab ne sort pas de la fenêtre');
    await shot(p,'compte-1-creer.png','#join .join-card');
    await p.keyboard.press('Escape');
    check(!(await ouverte(p))&&await p.evaluate(()=>document.activeElement&&document.activeElement.id==='joinBtn'),'Échap ferme et rend le focus au bouton');
    await p.click('#joinBtn'); await p.waitForSelector('#joinForm');
    await p.fill('#jnPseudo','ab'); await p.fill('#jnPw','motdepasse1'); await p.click('#jnGo');
    check(/3 to 24 characters/.test(await p.textContent('#jnErr')),'pseudo trop court : le message le dit');
    await p.fill('#jnPseudo','Nouveau Fan'); await p.fill('#jnPw','court'); await p.click('#jnGo');
    check(/at least 8 characters/.test(await p.textContent('#jnErr')),'mot de passe trop court : le message le dit');
    await p.fill('#jnPw','motdepasse1'); await p.click('#jnGo');
    await p.waitForSelector('#join [data-jteam]',{timeout:15000});
    const n=await p.$$eval('#join [data-jteam]',x=>x.length);
    check(n===Object.keys(W.teams).length,`2e écran : les ${n} franchises`);
    const me=(await api(P1,'/me?token='+inv.token)).json;
    check(me&&me.account&&me.name==='Nouveau Fan'&&me.bets.length===1,'le compte est posé sur la clé d\'invité : son pari reste');
    check(await p.$eval('#jnTeam',e=>e.disabled),'« Pick a team » tant qu\'aucune franchise n\'est choisie');
    const T=Object.keys(W.teams).sort()[3];
    await p.click(`#join [data-jteam="${T}"]`);
    check(new RegExp('Follow '+W.teams[T].name).test(await p.textContent('#jnTeam')),`« Follow ${W.teams[T].name} »`);
    await shot(p,'compte-2-franchise.png','#join .join-card');
    await p.click('#jnTeam');
    await p.waitForSelector('#join [data-joingo="myteam"]',{timeout:15000});
    check((await api(P1,'/me?token='+inv.token)).json.fav_team===T,'la franchise est enregistrée sur le compte');
    await shot(p,'compte-3-fini.png','#join .join-card');
    await p.click('#join [data-joingo="myteam"]');
    await p.waitForFunction(t=>{ const v=document.getElementById('viewMyteam'); return v&&!v.hidden&&v.textContent.includes(t); },W.teams[T].name,{timeout:15000});
    check(!(await ouverte(p))&&await p.$eval('#joinBtn',e=>getComputedStyle(e).display==='none'),'My team ouvert sur la franchise ; « Sign up » disparaît');
    check(!p.errs.length,'aucune erreur JS'+(p.errs.length?' : '+p.errs.join(' | '):''));

    /* un nouveau visiteur : Settings, « Sign in », « Skip for now », les invitations */
    const v=await ouvrir(b,P1);
    await vue(v,'settings');
    await v.waitForSelector('#viewSettings [data-join="register"]',{timeout:15000});
    check(!(await v.$('#acForm')),'Settings d\'un invité : plus de formulaire, deux boutons');
    await v.click('#viewSettings [data-join="login"]'); await v.waitForSelector('#joinForm');
    check(/Sign in/.test(await v.textContent('#joinTitle')),'« Sign in » ouvre la fenêtre en connexion');
    await v.fill('#jnPseudo','Nouveau Fan'); await v.fill('#jnPw','motdepasse1'); await v.click('#jnGo');
    await v.waitForFunction(()=>document.getElementById('join').hidden,null,{timeout:15000});
    check(await v.evaluate(()=>{ const p=JSON.parse(localStorage.getItem('gc-player-v1')); return p.account&&p.fav_team; })!==null,'connexion : la franchise déjà choisie, la fenêtre se ferme');
    const w2=await ouvrir(b,P1);
    await w2.click('#joinBtn'); await w2.waitForSelector('#joinForm');
    await w2.fill('#jnPseudo','Sans Equipe'); await w2.fill('#jnPw','motdepasse1'); await w2.click('#jnGo');
    await w2.waitForSelector('#join [data-joinskip]',{timeout:15000}); await w2.click('#join [data-joinskip]');
    check(/Pick a team any time/.test(await w2.textContent('#join')),'« Skip for now » : la franchise plus tard');
    await w2.click('#join [data-joingo]');
    const w3=await ouvrir(b,P1);
    await vue(w3,'myteam');
    await w3.waitForSelector('#viewMyteam [data-join]',{timeout:15000}); await w3.click('#viewMyteam [data-join]');
    check(await ouverte(w3),'My team d\'un invité : l\'invitation ouvre la fenêtre');
    check(!v.errs.length&&!w2.errs.length&&!w3.errs.length,'aucune erreur JS (Settings, Skip, My team)');

    /* téléphone */
    const m=await ouvrir(b,P1,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true});
    check(await m.$eval('#joinBtn',e=>!e.hidden&&e.getClientRects().length>0),'téléphone : « Sign up » visible');
    const ov=await m.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    check(ov<=1,`téléphone : pas de défilement horizontal (${ov} px)`);
    await shot(m,'compte-telephone-accueil.png');
    await m.click('#joinBtn'); await m.waitForSelector('#joinForm'); await m.waitForTimeout(400);   /* l'entrée de la feuille (0,18 s) */
    const r=await m.$eval('#join .join-card',e=>{ const b=e.getBoundingClientRect(); return {bottom:Math.round(b.bottom),h:innerHeight,w:Math.round(b.width)}; });
    check(r.bottom>=r.h-2&&r.w===390,`téléphone : la fenêtre est une feuille en bas de l'écran (${r.w} px, bas ${r.bottom} / ${r.h})`);
    await shot(m,'compte-telephone-1.png');
    await m.fill('#jnPseudo','Fan Mobile'); await m.fill('#jnPw','motdepasse1'); await m.click('#jnGo');
    await m.waitForSelector('#join [data-jteam]',{timeout:15000});
    await shot(m,'compte-telephone-2.png');
    check(!m.errs.length,'aucune erreur JS (téléphone)'+(m.errs.length?' : '+m.errs.join(' | '):''));
  }catch(e){ console.log('  ✗ exception : '+(e&&e.stack||e)); fail++; }
  finally{ await b.close(); srv.kill(); }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon.');
  process.exit(fail?1:0);
})();
