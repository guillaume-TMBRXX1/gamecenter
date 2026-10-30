// Combinés sur un même match et pari rapide depuis l'écran d'un match (section 86, 30/10/2026) — test navigateur
// (Playwright + serveur réel).   node outils/site/test_pari_rapide.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT). Vérifie : deux prix d'un match à venir (panneau du
// Schedule) annoncent un Same Game Combo à sa cote ; « Bet it as one » passe le bulletin en combiné ; le serveur
// l'accepte à la même cote (key « sgp ») ; une paire qui n'ajoute rien (victoire + spread du même favori) est refusée
// dans la page ; sur le grand écran d'un match en direct, un prix cliqué apparaît dans la barre de pari rapide, une mise
// et « Place bet » le placent sans fermer le match ; en « Bigger field » la barre flotte en haut à droite, dans
// l'écran ; téléphone 390 px sans défilement horizontal ; GC_SAME_GAME=off et GC_PARI_RAPIDE=off : la page d'avant ;
// aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CAP=process.env.GC_CAPTURES||'';            // dossier : captures des écrans (pour la revue)
const cap=async(p,nom)=>{ if(CAP) await p.screenshot({path:path.join(CAP,nom+'.png')}); };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const T0=Date.parse(REG[Math.floor(REG.length*0.5)].kickoff)+60e3, DEMO=new Date(T0).toISOString();

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-rapide-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks')); fs.symlinkSync(path.join(WEEKS,DERNIERE),path.join(data,'weeks',DERNIERE));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:DEMO},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const ouvrir=async(b,port,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000});
  return p; };
const slip=p=>p.evaluate(()=>window.__gc.season.bets.slip());
const paris=p=>p.evaluate(()=>window.__gc.season.bets.wallet().bets.map(b=>({key:b.key,dec:b.dec,stake:b.stake,legs:(b.legs||[]).map(l=>l.key)})));
const regarder=(p,gid)=>p.evaluate(gid=>{ const x=document.createElement('button'); x.dataset.sched=gid; document.body.appendChild(x); x.click(); x.remove(); },gid);

(async()=>{
  const P1=8177, P2=8178;
  const srv=await server(P1,{}), b=await chromium.launch({executablePath:EXE}), errs=[];
  let srv2=null;
  try{
    const p=await ouvrir(b,P1);
    await p.evaluate(()=>window.__gc.season.setView('schedule')); await p.waitForSelector('#viewSchedule .sch');
    await p.click('[data-schf="upcoming"]'); await p.waitForTimeout(200);
    const gid=await p.$eval('#viewSchedule [data-schbet]',x=>x.dataset.schbet), g=W.schedule.find(x=>x.id===gid);
    await p.click(`[data-schbet="${gid}"]`); await p.waitForTimeout(450);
    const fav=g.odds.spread_home<0?'home':'away', dog=fav==='home'?'away':'home';
    await p.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:ml:${fav}"]`);
    await p.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:tot:over"]`); await p.waitForTimeout(300);
    const hint=await p.$eval(`[data-sgp="${gid}"]`,x=>x.textContent);
    check(/Same Game Combo · 2 legs at/.test(hint),`panneau du Schedule : « ${hint.trim()} »`);
    await cap(p,'1_schedule_sgp');
    await p.click(`[data-sgp="${gid}"] [data-sgpgo]`); await p.waitForTimeout(300);
    const card=await p.$eval('#slipList .pk.combo',x=>x.textContent);
    check(/2-leg Same Game Combo/.test(card)&&/Priced together/.test(card),'« Bet it as one » : le bulletin passe en Same Game Combo');
    await cap(p,'2_bulletin_sgp');
    const vu=await p.evaluate(()=>window.__gc.season.bets.slip().picks.length);
    await p.click('#place'); await p.waitForTimeout(1200);
    let B=await paris(p);
    const sgp=B.find(x=>x.key==='sgp');
    check(vu===2&&!!sgp&&sgp.legs.length===2,`le serveur accepte le Same Game Combo (key sgp, cote ${sgp&&sgp.dec})`);
    // victoire et spread du même favori : n'ajoute rien
    await p.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:ml:${fav}"]`);
    await p.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:sp:${fav}"]`); await p.waitForTimeout(300);
    await p.evaluate(()=>{ const s=window.__gc.season.bets.slip(); s.mode='combo'; }); await p.click(`[data-sgp="${gid}"]`).catch(()=>{});
    await p.evaluate(()=>window.__gc.season.bets.toggle(window.__gc.season.bets.slip().picks[0].key)); await p.evaluate(k=>window.__gc.season.bets.toggle(k),`${gid}:ml:${fav}`);
    await p.waitForTimeout(300);
    const red=await p.$eval(`[data-sgp="${gid}"]`,x=>x.textContent), pl=await p.$eval('#place',x=>({d:x.disabled,t:x.textContent}));
    check(/add nothing/.test(red)&&pl.d,`victoire + spread du favori : refusé dans la page (« ${red.trim()} », bouton « ${pl.t} »)`);
    // pari rapide sur le grand écran d'un match en direct
    for(const k of (await slip(p)).picks.map(x=>x.key)) await p.evaluate(k=>window.__gc.season.bets.toggle(k),k);
    const live=REG.find(x=>Date.parse(x.kickoff)<=T0&&Date.parse(x.kickoff)+20*60e3>T0);
    await regarder(p,live.id); await p.waitForSelector('#modal:not([hidden]) .m-side .odd'); await p.waitForTimeout(600);
    check(await p.$eval('#qb',x=>x.hidden),'grand écran : pas de barre tant que le bulletin est vide');
    const odd=await p.$('#modal .m-side .odd[data-key$=":ml:away"]:not([disabled])')||await p.$('#modal .m-side .odd[data-key$=":ml:home"]:not([disabled])');
    await odd.click(); await p.waitForTimeout(400);
    const qb=await p.$eval('#qb',x=>({h:x.hidden,txt:x.textContent,r:x.getBoundingClientRect()}));
    check(!qb.h&&/Your slip 1 pick/.test(qb.txt)&&qb.r.bottom<=1000+1,`un prix cliqué : barre de pari rapide sous le match (« ${qb.txt.replace(/\s+/g,' ').trim().slice(0,70)} »)`);
    await p.fill('#qbStake','15'); await p.waitForTimeout(200);
    const lab=await p.$eval('#qb [data-qbplace]',x=>x.textContent);
    check(/Place bet · \$15/.test(lab),`mise dans la barre : « ${lab} »`);
    await cap(p,'3_grand_ecran_barre');
    const n0=(await paris(p)).length;
    for(let i=0;i<4&&(await paris(p)).length===n0;i++){       /* en direct, le prix peut bouger entre deux actions : on accepte */
      await p.click('#qb [data-qbplace]'); await p.waitForTimeout(1000); }
    B=await paris(p);
    check(B.length===n0+1&&B[B.length-1].stake===15,'« Place bet » dans la barre : pari placé');
    check(await p.$eval('#modal',x=>!x.hidden)&&await p.$eval('#qb',x=>x.hidden),'le match reste ouvert, la barre se replie (bulletin vide)');
    // Bigger field
    await p.click('#modal [data-theater]'); await p.waitForTimeout(500);
    await p.evaluate(k=>window.__gc.season.bets.toggle(k),`${gid}:ml:${dog}`); await p.waitForTimeout(400);
    const th=await p.$eval('#qb',x=>{ const r=x.getBoundingClientRect(); return {h:x.hidden,r:{t:r.top,l:r.left,rt:r.right,b:r.bottom},w:innerWidth}; });
    check(!th.h&&th.r.t<80&&th.r.rt<=th.w&&th.r.l>th.w/2-200,`« Bigger field » : la barre flotte en haut à droite (${Math.round(th.r.l)}–${Math.round(th.r.rt)} px)`);
    await cap(p,'4_bigger_field_barre');
    await p.click('#modal [data-theater]'); await p.waitForTimeout(300);
    errs.push(...p.errs);

    const mo=await ouvrir(b,P1,{viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await mo.evaluate(k=>window.__gc.season.bets.toggle(k),`${gid}:tot:under`);
    await regarder(mo,live.id); await mo.waitForTimeout(800);
    const mw=await mo.evaluate(()=>({w:document.documentElement.scrollWidth,m:document.querySelector('#modal .m-panel').scrollWidth,qb:!document.getElementById('qb').hidden}));
    check(mw.qb&&mw.w<=390&&mw.m<=392,`téléphone : barre visible, pas de défilement horizontal (${mw.w} / ${mw.m} px)`);
    await cap(mo,'5_telephone_barre');
    errs.push(...mo.errs);

    srv2=await server(P2,{GC_SAME_GAME:'off',GC_PARI_RAPIDE:'off'});
    const off=await ouvrir(b,P2);
    await off.evaluate(()=>window.__gc.season.setView('schedule')); await off.waitForSelector('#viewSchedule .sch');
    await off.click('[data-schf="upcoming"]'); await off.click(`[data-schbet="${gid}"]`); await off.waitForTimeout(400);
    await off.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:ml:${fav}"]`); await off.click(`.sch-game[data-g="${gid}"] .odd[data-key="${gid}:tot:over"]`);
    await off.evaluate(()=>{ window.__gc.season.bets.slip().mode='combo'; }); await off.click('[data-schf="upcoming"]'); await off.waitForTimeout(300);
    const t2=await off.evaluate(()=>{ document.querySelector('[data-slipmode="combo"]')&&document.querySelector('[data-slipmode="combo"]').click(); return document.getElementById('place').textContent; });
    check(!(await off.$('[data-sgp]'))&&/One pick per game/.test(t2),`GC_SAME_GAME=off : pas d'annonce, combiné d'un même match refusé comme avant (« ${t2} »)`);
    await regarder(off,live.id); await off.waitForTimeout(600);
    check(!(await off.$('#qb')),'GC_PARI_RAPIDE=off : pas de barre sur le grand écran');
    errs.push(...off.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
