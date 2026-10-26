// Chat d'un match et anti-spoiler (bloc 3, étape 3 — 26/10/2026) — test navigateur (Playwright + serveurs réels).
//   node outils/site/test_chat_match.js      (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Indépendant de l'heure : l'horloge des serveurs est posée (GC_DEMO_AT) 3 h après le premier coup d'envoi de la dernière
// semaine du dépôt (son premier match est alors terminé) ; l'âge des comptes est reculé dans la base.
// Vérifie : bouton « Match chat » dans le grand écran d'un match de la semaine (pas pour un match hors calendrier, pas
// chat coupé) ; replay arrêté à l'action 10 : les messages écrits jusque-là sont là, ceux d'après attendent ; avancer
// à l'action 45 les fait apparaître ; revenir à 5 les retire ; un message écrit dans le replay porte sa position, un score
// qui n'est pas celui de ce moment est renvoyé à la fin (et l'auteur est prévenu) ; Échap ferme le chat puis le match ;
// « Bigger field » : bouton visible, tiroir dans le panneau, sur ordinateur et sur un téléphone tenu droit (champ encore
// visible, rien hors de l'écran) ; General : un message qui ressemble au score d'un match commencé et pas vu jusqu'au bout
// est replié (« Possible spoiler »), un toucher le montre ; le réglage « Chat spoiler shield » le coupe ; un match vu
// jusqu'au bout ne replie plus ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn,execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), WEEK=fs.readdirSync(WEEKS).filter(d=>d.startsWith('week_')).sort().pop();
const DOC=JSON.parse(fs.readFileSync(path.join(WEEKS,WEEK,'week.json'))), G=DOC.schedule[0];
const F=JSON.parse(fs.readFileSync(path.join(WEEKS,WEEK,G.feed))), N=F.plays.length;
const AT=new Date(Date.parse(G.kickoff)+3*3600e3).toISOString();
const ON=8144, OFF=8145, KEY='une-cle-admin-assez-longue-pour-le-test', ROOM=`m:${DOC.week.start}:${G.id}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-chat-match-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_CHAT:'',GC_ADMIN_KEY:KEY,GC_DEMO_AT:AT},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; return p; } }catch(e){} await pause(250); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const api=async(port,u,body)=>{ const r=await fetch(`http://localhost:${port}/api`+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  return {status:r.status,json:await r.json().catch(()=>null)}; };
const vieillir=data=>execFileSync('python3',['-c','import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("UPDATE players SET acct_at=0");c.commit()',path.join(data,'gamecenter.db')]);
async function ouvrir(b,port,opts,player,init){
  const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:950}},opts||{}));
  await ctx.addInitScript(([pl,init])=>{ try{ localStorage.setItem('gc-theater-v1','0'); if(pl) localStorage.setItem('gc-player-v1',JSON.stringify(pl)); for(const k in init||{}) localStorage.setItem(k,init[k]); }catch(e){} },[player,init]);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000});
  await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); return p;
}
/* the replay of game G on the big screen, stopped at play k (k plays seen) */
const replayA=async(p,k,feed)=>p.evaluate(([F,k])=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); G.rpSeek(g,k); g.paused=true; },[feed||F,k]);
const seek=(p,k)=>p.evaluate(k=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,k); g.paused=true; },k);
const finir=p=>p.evaluate(()=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,g.plays.length-1); g.paused=false; g.speed=1;
  for(let i=0;i<20000&&g.status!=='final';i++) G.stepGame(g,0.05); g.paused=true; return g.status; });
const textes=p=>p.$$eval('#mChatLog .chat-msg:not([hidden]) .chat-b',x=>x.map(e=>e.textContent));
const attendre=async(p,fn,arg,ms=8000)=>{ try{ await p.waitForFunction(fn,arg,{timeout:ms}); return true; }catch(e){ return false; } };

(async()=>{
  const on=await server(ON,{GC_CHAT:'on'}), off=await server(OFF,{}), b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    const d=(await api(ON,'/delta')).json, st=d.state.schedule.find(x=>x.id===G.id);
    check(st&&st.status==='final',`match ${G.id} terminé à l'heure posée (${AT})`);

    /* comptes et messages à différents moments du match */
    const U={}; for(const n of ['Viewer','Early','Middle','Spoiler','Fan']) U[n]=(await api(ON,'/account/register',{pseudo:n+' One',password:'motdepasse1'})).json;
    vieillir(on.data);
    const post=async(u,body,at,room=ROOM)=>(await api(ON,'/chat/post',{token:U[u].token,room,body,at})).json;
    const mEarly=await post('Early','Opening drive looks sharp',2);
    const mMid=await post('Middle','What a catch on that drive',40);
    const fin=G.result||{}, mSp=await post('Spoiler',`it ends ${fin.home}-${fin.away}, unreal`,3);
    check(mEarly.msg.at===2&&mMid.msg.at===40,'positions gardées par le serveur (2 et 40)');
    check(mSp.msg.at===N,`un score de fin écrit « à l'action 3 » est renvoyé à la fin (${mSp.msg&&mSp.msg.at} = ${N})`);

    /* ---- chat coupé : pas de bouton ---- */
    const z=await ouvrir(b,OFF); await replayA(z,10); await pause(400);
    check(!(await z.$('#modal .m-chat')),'chat coupé : pas de bouton « Match chat »');
    await z.evaluate(()=>document.querySelector('[data-close]').click()); await z.click('.rail-btn[data-view="settings"]'); await pause(400);
    check(!(await z.$('[data-set="chatShield"]')),'chat coupé : pas de réglage « Chat spoiler shield »');
    errs.push(...z.errs); await z.context().close();

    /* ---- le replay, arrêté à l'action 10 ---- */
    console.log('— replay à sa position');
    const v=await ouvrir(b,ON,null,{token:U.Viewer.token,name:U.Viewer.name,account:true});
    await replayA(v,10,Object.assign({},F,{game:Object.assign({},F.game,{id:'exh-test'})})); await pause(300);
    check(!(await v.$('#modal .m-chat')),'match hors calendrier : pas de chat');
    await v.evaluate(()=>document.querySelector('[data-close]').click());
    await replayA(v,10); await pause(300);
    check(!!(await v.$('#modal .m-chat')),'bouton « Match chat » dans l’en-tête du match');
    await v.click('#modal .m-chat');
    check(await attendre(v,()=>!!document.querySelector('#mChat')),'le tiroir du chat s’ouvre');
    check(await attendre(v,()=>[...document.querySelectorAll('#mChatLog .chat-b')].some(e=>e.textContent==='Opening drive looks sharp')),'action 10 : le message de l’action 2 est là');
    let t=await textes(v);
    check(!t.includes('What a catch on that drive'),'action 10 : le message de l’action 40 attend');
    check(!t.some(x=>x.startsWith('it ends')),'action 10 : le score final n’est pas montré');
    check(/Synced to your replay/.test(await v.textContent('#mChatSub')),'sous-titre : « Synced to your replay »');
    check(await v.evaluate(()=>['[data-close]','[data-theater]','.m-chat'].every(q=>{ const e=document.querySelector('#modal '+q), r=e.getBoundingClientRect();
      const h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return h&&(h===e||e.contains(h)); })),'chat ouvert : Fermer, Bigger field et le bouton du chat restent cliquables');
    await seek(v,45);
    check(await attendre(v,()=>[...document.querySelectorAll('#mChatLog .chat-b')].some(e=>e.textContent==='What a catch on that drive'),null,3000),'avancé à l’action 45 : le message de l’action 40 apparaît');
    check(!(await textes(v)).some(x=>x.startsWith('it ends')),'action 45 : toujours pas le score final');
    await seek(v,5);
    check(await attendre(v,()=>![...document.querySelectorAll('#mChatLog .chat-b')].some(e=>e.textContent==='What a catch on that drive'),null,4000),'revenu à l’action 5 : le message de l’action 40 repart');
    check((await textes(v)).includes('Opening drive looks sharp'),'action 5 : celui de l’action 2 reste');
    check(await finir(v)==='final','replay déroulé jusqu’au coup de sifflet final');
    check(await attendre(v,()=>[...document.querySelectorAll('#mChatLog .chat-b')].some(e=>e.textContent.startsWith('it ends')),null,4000),'fin du match : le score final apparaît');

    /* écrire depuis le replay */
    await seek(v,20); await pause(1200);
    await v.fill('#mChatInput','Nice blitz call here'); await v.press('#mChatInput','Enter');
    check(await attendre(v,()=>[...document.querySelectorAll('#mChatLog .chat-b')].some(e=>e.textContent==='Nice blitz call here')),'mon message apparaît tout de suite');
    let r=(await api(ON,`/chat?room=${encodeURIComponent(ROOM)}`)).json.msgs.find(m=>m.b==='Nice blitz call here');
    check(r&&r.at===20,`il porte ma position (${r&&r.at})`);
    await pause(3200);
    await v.fill('#mChatInput','this ends 99-0 lol'); await v.press('#mChatInput','Enter');
    check(await attendre(v,()=>/people watching a replay see it once they reach the live point/.test(document.getElementById('mChatLine').textContent)),'un score d’un autre moment : prévenu qu’il ira à la fin');
    r=(await api(ON,`/chat?room=${encodeURIComponent(ROOM)}`)).json.msgs.find(m=>m.b==='this ends 99-0 lol');
    check(r&&r.at===N,'… et le serveur l’a placé à la fin');

    /* Échap : le chat, puis le match */
    await v.focus('#mChatInput'); await v.keyboard.press('Escape'); await pause(300);
    check(!(await v.$('#mChat'))&&!(await v.$('#modal[hidden]')),'Échap ferme le chat, le match reste ouvert');
    check(await v.evaluate(()=>document.activeElement&&document.activeElement.matches('.m-chat')),'le focus revient sur le bouton « Match chat »');
    await v.keyboard.press('Escape'); await pause(300);
    check(!!(await v.$('#modal[hidden]')),'Échap une seconde fois ferme le match');

    /* « Bigger field » sur ordinateur */
    console.log('— Bigger field');
    await replayA(v,10); await v.click('#modal [data-theater]'); await pause(400);
    check(await v.$eval('#modal .m-chat',e=>getComputedStyle(e).display!=='none'),'plein écran : le bouton « Match chat » reste');
    await v.click('#modal .m-chat'); await pause(600);
    check(await v.$eval('#mChat',e=>e.parentElement.classList.contains('m-panel')),'plein écran : le tiroir est dans le panneau du match');
    const box=await v.$eval('#mChat',e=>{ const r=e.getBoundingClientRect(); return {l:r.left,w:r.width,r:r.right}; });
    check(box.r<=1441&&box.w<=1440*0.47,`plein écran : tiroir à droite, le terrain reste visible (${Math.round(box.w)} px)`);
    const fl=await v.$eval('#modal .m-main',e=>e.getBoundingClientRect().right);
    check(fl<=box.l+1,`plein écran : le terrain s’arrête au bord du tiroir (${Math.round(fl)} ≤ ${Math.round(box.l)})`);
    await v.click('#modal [data-theater]'); await pause(400);
    check(await v.$eval('#mChat',e=>e.parentElement.id==='modal'),'retour en vue normale : le tiroir suit');
    await v.evaluate(()=>document.querySelector('[data-close]').click()); await pause(200);
    check(!(await v.$('#mChat')),'fermer le match ferme son chat');
    errs.push(...v.errs);

    /* ---- téléphone tenu droit, plein écran (le match est tourné) ---- */
    const ph=await ouvrir(b,ON,{viewport:{width:390,height:844},isMobile:true,hasTouch:true},{token:U.Fan.token,name:U.Fan.name,account:true},{'gc-theater-v1':'1'});
    await replayA(ph,45); await pause(500);
    await ph.evaluate(()=>document.querySelector('#modal .m-chat').click()); await pause(800);
    const pr=await ph.$eval('#mChat',e=>{ const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; });
    check(pr.x>=-1&&pr.y>=-1&&pr.x+pr.w<=391&&pr.y+pr.h<=845,`téléphone : le tiroir tient dans l’écran (${pr.w|0} × ${pr.h|0})`);
    check(pr.h<844*0.6,'téléphone : le tiroir prend une partie du match tourné (le terrain reste visible)');
    check((await textes(ph)).includes('What a catch on that drive'),'téléphone : messages à la position (action 45)');
    errs.push(...ph.errs); await ph.context().close();

    /* ---- General : le bouclier anti-spoiler ---- */
    console.log('— General : bouclier');
    const abbr=G.home;
    await post('Fan',`${abbr} won ${fin.home}-${fin.away}!`,null,'general');
    await post('Middle','Anyone watching tonight?',null,'general');
    const gp=await ouvrir(b,ON,null,{token:U.Viewer.token,name:U.Viewer.name,account:true});
    await gp.click('.rail-btn[data-chat]'); await gp.waitForSelector('#chatPanel.open'); await pause(1200);
    check(await gp.$$eval('#chatLog .chat-spoil',x=>x.length)===1,'un message replié (« Possible spoiler »)');
    check(!(await gp.$$eval('#chatLog .chat-b',x=>x.map(e=>e.textContent))).some(s=>s.includes(' won ')),'son texte n’est pas dans la page');
    check(/Possible spoiler/.test(await gp.textContent('#chatLog .chat-spoil'))&&(await gp.textContent('#chatLog .chat-spoil')).includes(abbr),`le pli nomme l’équipe (${abbr})`);
    check((await gp.$$eval('#chatLog .chat-b',x=>x.map(e=>e.textContent))).includes('Anyone watching tonight?'),'les autres messages sont lisibles');
    await gp.click('#chatLog .chat-spoil');
    check((await gp.$$eval('#chatLog .chat-b',x=>x.map(e=>e.textContent))).some(s=>s.includes(' won ')),'un toucher le montre');
    await gp.click('[data-chat-close]'); await gp.click('.rail-btn[data-view="settings"]'); await pause(400);
    check(await gp.$eval('[data-set="chatShield"]',e=>e.getAttribute('aria-checked')==='true'),'réglage « Chat spoiler shield » allumé par défaut');
    /* tous les matchs de l'équipe déjà commencés (elle peut jouer deux fois dans la journée) */
    const vus=DOC.schedule.filter(x=>(x.home===abbr||x.away===abbr)&&Date.parse(x.kickoff)<=Date.parse(AT)).map(x=>x.id);
    await gp.evaluate(([w,ids])=>{ localStorage.setItem('gc-watched-v1',JSON.stringify({week:w,ids})); },[DOC.week.start,vus]);
    await gp.reload(); await gp.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    await gp.click('.rail-btn[data-chat]'); await gp.waitForSelector('#chatPanel.open'); await pause(1200);
    check(await gp.$$eval('#chatLog .chat-spoil',x=>x.length)===0,`matchs de l’équipe vus jusqu’au bout (${vus.join(', ')}) : plus replié`);
    await gp.evaluate(()=>localStorage.removeItem('gc-watched-v1')); await gp.reload(); await gp.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    await gp.click('.rail-btn[data-view="settings"]'); await pause(300); await gp.click('[data-set="chatShield"]');
    await gp.click('.rail-btn[data-chat]'); await gp.waitForSelector('#chatPanel.open'); await pause(1200);
    check(await gp.$$eval('#chatLog .chat-spoil',x=>x.length)===0,'réglage coupé : rien n’est replié');
    errs.push(...gp.errs);

    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.log('  ✗ ERREUR',e.stack||e); fail++; }
  finally{ await b.close(); on.kill(); off.kill(); }
  console.log(fail?`${fail} FAILED`:'OK'); process.exit(fail?1:0);
})();
