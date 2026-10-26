// Chat, salon General (bloc 3, étape 2 — 26/10/2026) — test navigateur (Playwright + serveurs réels, copie des données).
//   node outils/site/test_chat.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Deux serveurs : 8142 avec GC_CHAT=on, 8143 sans (chat coupé : ni bouton, ni panneau, ni appel /api/chat, page légale et
// /admin/chat inchangés). Chat allumé : point « nouveau » sur le bouton Chat ; panneau (dialogue, Échap le ferme et rend
// le focus) ; un invité lit et se voit proposer un compte ; un compte écrit (Entrée), un second navigateur reçoit le
// message ; un message « <img onerror> » reste du texte ; mot masqué ; lien refusé avec un message clair ; signaler
// (motif), masquer une personne (puis tout réafficher), effacer son message (disparu chez l'autre) ; l'administrateur
// masque un message (retiré chez les lecteurs, motif montré à l'auteur) depuis la page /admin/chat ; ouvrir un match
// ferme le panneau ; téléphone 390 px : bouton dans la barre du haut, panneau plein écran, page dessous inerte, aucun
// défilement horizontal ; page légale avec les règles du chat ; aucune erreur JS. Indépendant de l'heure : l'âge des
// comptes est reculé dans la base. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn,execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const ON=8142, OFF=8143, KEY='une-cle-admin-assez-longue-pour-le-test';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-chat-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_CHAT:'',GC_ADMIN_KEY:KEY},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; return p; } }catch(e){} await pause(250); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api`+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
/* comptes « anciens » : l'âge minimal (10 min) ne dépend pas de l'heure du test */
const vieillir=data=>execFileSync('python3',['-c','import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("UPDATE players SET acct_at=0");c.commit()',path.join(data,'gamecenter.db')]);
const ouvrir=async(b,port,opts,player)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:950}},opts||{}));
  if(player) await ctx.addInitScript(pl=>localStorage.setItem('gc-player-v1',JSON.stringify(pl)),player);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message)); p.calls=[];
  p.on('request',r=>{ if(r.url().includes('/api/chat')) p.calls.push(r.url()); });
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000});
  await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p; };
const textes=p=>p.$$eval('#chatLog .chat-msg:not([hidden]) .chat-b',x=>x.map(e=>e.textContent));
const attendre=async(p,fn,arg,ms=9000)=>{ try{ await p.waitForFunction(fn,arg,{timeout:ms}); return true; }catch(e){ return false; } };
const ouvrirChat=async p=>{ await p.click('.rail-btn[data-chat]'); await p.waitForSelector('#chatPanel.open',{timeout:5000}); await pause(400); };

(async()=>{
  const on=await server(ON,{GC_CHAT:'on'}), off=await server(OFF,{}), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    /* ---- chat coupé : rien ---- */
    console.log('— chat coupé (GC_CHAT absent)');
    const z=await ouvrir(b,OFF); await pause(4000);
    check(await z.$$eval('[data-chat],#chatPanel',x=>x.length)===0,'ni bouton Chat ni panneau');
    check(z.calls.length===0,'aucun appel /api/chat');
    check((await api(OFF,'/chat?room=general')).status===404,'/api/chat : 404');
    const lz=await (await fetch(`http://localhost:${OFF}/legal`)).text();
    check(!lz.includes('id="chat"')&&!lz.includes('Chat rules'),'page légale sans les règles du chat');
    check((await fetch(`http://localhost:${OFF}/admin/chat`)).status===404,'/admin/chat : 404');
    errs.push(...z.errs); await z.context().close();

    /* ---- comptes et un premier message de l'équipe ---- */
    const A=(await api(ON,'/account/register',{pseudo:'Fan Alpha',password:'motdepasse1'})).json;
    const B=(await api(ON,'/account/register',{pseudo:'Fan Bravo',password:'motdepasse2'})).json;
    vieillir(on.data);
    await api(ON,'/account/team',{token:A.token,team:Object.keys(JSON.parse(fs.readFileSync(path.join(WEEKS,fs.readdirSync(WEEKS).sort().pop(),'week.json'))).teams)[0]});
    const adm=await api(ON,'/admin/chat',{key:KEY,action:'post',room:'general',body:'Welcome to the Snapline chat!'});
    check(adm.status===200,'message de l’équipe publié (API d’administration)');

    /* ---- un invité ---- */
    console.log('— invité');
    const g=await ouvrir(b,ON);
    check(await attendre(g,()=>{ const d=document.querySelector('.rail-btn[data-chat] .chat-dot'); return d&&!d.hidden; }),'point « nouveau » sur le bouton Chat');
    check(await g.$eval('.chat-top',e=>getComputedStyle(e).display==='none'),'ordinateur : pas de bouton Chat dans la barre du haut');
    await ouvrirChat(g);
    check(await g.$eval('#chatPanel',e=>e.getAttribute('role')==='dialog'&&!e.inert),'panneau ouvert : un dialogue');
    check(await g.$eval('.rail-btn[data-chat]',e=>e.getAttribute('aria-expanded')==='true'),'bouton Chat : aria-expanded');
    check((await textes(g)).includes('Welcome to the Snapline chat!'),'l’invité lit les messages');
    check(await g.$eval('#chatLog .chat-msg .chat-adm',e=>e.textContent==='Snapline').catch(()=>false),'badge « Snapline » sur le message de l’équipe');
    check(/create a free account to chat/i.test(await g.textContent('#chatFoot')),'invité : invitation à créer un compte, pas de champ');
    check(await g.$eval('.rail-btn[data-chat] .chat-dot',e=>e.hidden),'point « nouveau » éteint une fois lu');
    await g.keyboard.press('Escape'); await pause(400);
    check(await g.$eval('#chatPanel',e=>!e.classList.contains('open')&&e.inert),'Échap ferme le panneau');
    check(await g.evaluate(()=>document.activeElement&&document.activeElement.matches('.rail-btn[data-chat]')),'le focus revient sur le bouton Chat');

    /* ---- deux comptes ---- */
    console.log('— deux comptes');
    const pa=await ouvrir(b,ON,null,{token:A.token,name:A.name,account:true}), pb=await ouvrir(b,ON,null,{token:B.token,name:B.name,account:true});
    await ouvrirChat(pa); await ouvrirChat(pb);
    check(await pa.$eval('label[for="chatInput"]',e=>/Message as\s*Fan Alpha/.test(e.textContent)).catch(()=>false),'champ avec un libellé visible (« Message as Fan Alpha »)');
    await pa.fill('#chatInput','Great drive by the offense'); await pa.press('#chatInput','Enter');
    check(await attendre(pa,()=>[...document.querySelectorAll('#chatLog .chat-b')].some(e=>e.textContent==='Great drive by the offense')),'A : son message affiché tout de suite');
    check(await pa.$eval('#chatLog .chat-msg:last-child .chat-you',e=>e.textContent==='you').catch(()=>false),'A : « you » sur son message');
    check(await pa.$eval('#chatLog .chat-msg:last-child .chat-t',e=>e.textContent.length>=2).catch(()=>false),'A : son équipe favorite à côté du pseudo');
    check(await attendre(pb,()=>[...document.querySelectorAll('#chatLog .chat-b')].some(e=>e.textContent==='Great drive by the offense')),'B : reçoit le message de A (≤ 3 s)');
    await pause(3200);
    await pa.fill('#chatInput','<img src=x onerror="window.__xss=1"> <b>bold</b>'); await pa.press('#chatInput','Enter');
    check(await attendre(pb,()=>[...document.querySelectorAll('#chatLog .chat-b')].some(e=>e.textContent.includes('<img src=x'))),'B : « <img onerror> » affiché comme du texte');
    check(await pb.evaluate(()=>!window.__xss&&!document.querySelector('#chatLog img, #chatLog .chat-b b')),'aucune balise interprétée (pas d’image, pas de gras)');
    await pause(3200);
    await pa.fill('#chatInput','what a fuuuck play'); await pa.press('#chatInput','Enter');
    check(await attendre(pa,()=>[...document.querySelectorAll('#chatLog .chat-b')].some(e=>e.textContent==='what a ****** play')),'mot masqué par le serveur');
    check(/Some words were hidden/.test(await pa.textContent('#chatLine')),'A : prévenu que des mots ont été masqués');
    await pause(3200);
    await pa.fill('#chatInput','free picks at www.example.com'); await pa.press('#chatInput','Enter');
    check(await attendre(pa,()=>/Links aren’t allowed/.test(document.getElementById('chatLine').textContent)),'lien refusé avec un message clair');
    check(await pa.$eval('#chatInput',e=>e.value==='free picks at www.example.com'),'le texte refusé reste dans le champ');
    await pa.fill('#chatInput','x'.repeat(281));
    check(await pa.$eval('#chatSendBtn',e=>e.disabled)&&/281 \/ 280/.test(await pa.textContent('#chatCount')),'compteur : 281 / 280, envoi bloqué');
    await pa.fill('#chatInput','');

    /* B signale et masque A */
    const idA=await pb.$eval('#chatLog .chat-msg:last-child',e=>+e.dataset.id);
    await pb.click(`#chatLog .chat-msg[data-id="${idA}"] .chat-more`);
    check(await pb.$eval(`.chat-msg[data-id="${idA}"] .chat-more`,e=>e.getAttribute('aria-expanded')==='true'),'menu du message ouvert (aria-expanded)');
    await pb.click(`.chat-msg[data-id="${idA}"] [data-chat-act="report"]`);
    await pb.click(`.chat-msg[data-id="${idA}"] [data-chat-act="report-yes"][data-arg="spam"]`);
    check(await attendre(pb,id=>/Thanks/.test((document.querySelector(`.chat-msg[data-id="${id}"] .chat-acts`)||{}).textContent||''),idA),'B : signalement envoyé (« Thanks… »)');
    const rep=await api(ON,'/admin/chat',{key:KEY,action:'reports'});
    check(rep.json.reports.some(m=>m.id===idA&&m.reports.spam===1),'le signalement arrive chez l’administrateur (motif spam)');
    await pb.click(`.chat-msg[data-id="${idA}"] .chat-more`); await pb.click(`.chat-msg[data-id="${idA}"] .chat-more`);
    await pb.click(`.chat-msg[data-id="${idA}"] [data-chat-act="mute"]`);
    check(await pb.$$eval('#chatLog .chat-msg',(x,a)=>x.filter(e=>e.dataset.a===a).every(e=>e.hidden),await pb.$eval(`.chat-msg[data-id="${idA}"]`,e=>e.dataset.a)),'B : les messages de A disparaissent (masqué sur cet appareil)');
    check(/1 person muted/.test(await pb.textContent('#chatFoot')),'B : « 1 person muted · Unmute all »');
    await pb.click('[data-chat-unmute]');
    check((await textes(pb)).includes('Great drive by the offense'),'B : tout réafficher');

    /* A efface son premier message : disparu chez B */
    const id1=await pa.$$eval('#chatLog .chat-msg',x=>+x.find(e=>e.querySelector('.chat-b').textContent==='Great drive by the offense').dataset.id);
    await pa.click(`.chat-msg[data-id="${id1}"] .chat-more`);
    check(await pa.$$eval(`.chat-msg[data-id="${id1}"] [data-chat-act]`,x=>x.map(e=>e.dataset.chatAct).join(','))==='del,close','A : sur son message, Delete (pas Report ni Mute)');
    await pa.click(`.chat-msg[data-id="${id1}"] [data-chat-act="del"]`); await pa.click(`.chat-msg[data-id="${id1}"] [data-chat-act="del-yes"]`);
    check(await attendre(pa,id=>!document.querySelector(`.chat-msg[data-id="${id}"]`),id1),'A : message effacé');
    check(await attendre(pb,id=>!document.querySelector(`.chat-msg[data-id="${id}"]`),id1),'B : le message effacé disparaît aussi');

    /* l'administrateur masque un message depuis /admin/chat */
    console.log('— administration');
    const ad=await (await b.newContext({viewport:{width:1100,height:900}})).newPage(); ad.errs=[]; ad.on('pageerror',e=>ad.errs.push(e.message));
    await ad.goto(`http://localhost:${ON}/admin/chat`);
    check(await ad.evaluate(()=>document.querySelector('meta[name="robots"]').content.includes('noindex')),'page d’administration non indexée');
    await ad.fill('#key','mauvaise-cle-mauvaise'); await ad.click('#keyForm button');
    check(await attendre(ad,()=>/Clé refusée/.test(document.getElementById('out').textContent)),'mauvaise clé refusée');
    await ad.fill('#key',KEY); await ad.click('#keyForm button');
    check(await attendre(ad,()=>!document.getElementById('app').hidden),'bonne clé : la liste s’ouvre');
    check(await attendre(ad,()=>/signalé : spam × 1/.test(document.getElementById('reports').textContent)),'le message signalé est dans « À revoir »');
    ad.once('dialog',d=>d.accept('Personal attack'));
    await ad.click('#reports .msg:first-child button.bad');      // « Masquer »
    check(await attendre(ad,()=>/Message masqué/.test(document.getElementById('out').textContent)),'masqué depuis la page');
    check(await attendre(pb,id=>!document.querySelector(`.chat-msg[data-id="${id}"]`),idA),'B : le message masqué disparaît');
    await pa.evaluate(()=>{ document.querySelector('[data-chat-close]').click(); }); await pause(300); await ouvrirChat(pa);
    check(await attendre(pa,()=>/Your message was hidden: .*Personal attack/.test(document.getElementById('chatNotes').textContent)),'A : voit son message masqué et le motif');
    errs.push(...ad.errs);

    /* ouvrir un match ferme le panneau */
    const F=JSON.parse(fs.readFileSync(path.join(WEEKS,fs.readdirSync(WEEKS).sort().pop(),'games',fs.readdirSync(path.join(WEEKS,fs.readdirSync(WEEKS).sort().pop(),'games')).sort()[0])));
    await pa.evaluate(F=>window.__gc.openReplayFeed(F),F); await pause(500);
    check(await pa.$eval('#chatPanel',e=>!e.classList.contains('open'))&&await pa.$('#modal:not([hidden])')!==null,'ouvrir un match ferme le panneau');
    errs.push(...g.errs,...pa.errs,...pb.errs);

    /* ---- téléphone ---- */
    console.log('— téléphone 390 × 844');
    const t=await ouvrir(b,ON,{viewport:{width:390,height:844},hasTouch:true,isMobile:true},{token:B.token,name:B.name,account:true});
    check(await t.$eval('.chat-top',e=>getComputedStyle(e).display!=='none'),'bouton Chat dans la barre du haut');
    await t.tap('.chat-top'); await t.waitForSelector('#chatPanel.open'); await pause(500);
    const w=await t.$eval('#chatPanel',e=>Math.round(e.getBoundingClientRect().width));
    check(w===390,`panneau plein écran (${w} px)`);
    check(await t.evaluate(()=>document.querySelector('.app').inert),'la page dessous est inerte');
    check(await t.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'aucun défilement horizontal');
    const hb=await t.$eval('.chat-x',e=>e.getBoundingClientRect().height);
    check(hb>=44,`bouton Fermer ≥ 44 px (${hb})`);
    await t.tap('.chat-x'); await pause(400);
    check(await t.evaluate(()=>!document.querySelector('.app').inert&&!document.getElementById('chatPanel').classList.contains('open')),'fermé : la page redevient utilisable');
    errs.push(...t.errs);

    /* ---- page légale ---- */
    const l=await (await fetch(`http://localhost:${ON}/legal`)).text();
    check(l.includes('<section id="chat">')&&l.includes('Chat rules')&&l.includes('deleted automatically after')&&l.includes('<b>Chat</b> (accounts only'),'page légale : règles du chat et données gardées');
    check(!l.includes('__DAYS__')&&l.includes('after 30 days'),'durée de conservation (30 jours)');

    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.log('  ✗ ERREUR',e.stack||e); fail++; }
  finally{ await b.close(); on.kill(); off.kill(); }
  console.log(fail?`${fail} FAILED`:'OK'); process.exit(fail?1:0);
})();
