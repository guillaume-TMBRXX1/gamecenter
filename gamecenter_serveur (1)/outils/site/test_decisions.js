// La décision du coach IA sur le terrain, et le grand écran sur téléphone (section 128 — 19/11/2026) — test navigateur.
//   node outils/site/test_decisions.js        (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Deux serveurs, l'horloge après la semaine (GC_DEMO_AT : tous les matchs sont terminés) : 8242 par défaut, 8243 avec
// GC_DECISIONS=off. Les décisions viennent des GameFeed de la dernière semaine : un 4e essai joué (« go »), un field goal
// choisi alors que « go » avait la meilleure chance de victoire (« Plays it safe »), une tentative à 2 points.
// Vérifie : la carte nomme le coach, la situation, la décision et chaque option avec sa chance de victoire (celle du
// moteur, arrondie), la retenue en avant ; « Plays it safe » quand le coach ne suit pas les chiffres ; la raison d'une
// tentative à 2 points en anglais ; à la fin de l'action, le résultat (✓ / ✗) d'après le GameFeed ; aucune carte sur une
// action ordinaire ni avec GC_DECISIONS=off. Téléphone 390 × 664 : le grand écran prend tout l'écran, l'en-tête tient
// sur une ligne (≤ 56 px, « ABR @ ABR »), le terrain bord à bord juste dessous, pas de défilement horizontal ; la carte
// tient dans le terrain. Aucune erreur JS. SHOTS=<dossier> : captures. Lancé par tests_navigateur.sh (groupe site-2).
let chromium, devices; try{ ({chromium,devices}=require('playwright')); }catch(e){ ({chromium,devices}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), SHOTS=process.env.SHOTS||'';
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const pause=ms=>new Promise(r=>setTimeout(r,ms));

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const APRES=new Date(Math.max(...W.schedule.map(g=>Date.parse(g.kickoff)))+4*3600e3).toISOString();   // semaine finie
const reg=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
/* les décisions à montrer, cherchées dans les GameFeed de la semaine */
let GO=null, SAFE=null, TWO=null, PLAIN=null;
for(const s of reg){
  const f=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'games',s.id+'.json'),'utf8')), P=f.plays;
  P.forEach((p,k)=>{ const d=p.fourth_down, c=p.conversion;
    if(!GO&&d&&d.choice==='go'&&d.wp) GO={gid:s.id,k,p};
    if(!SAFE&&d&&d.choice==='field_goal'&&d.wp&&d.wp.go>d.wp.field_goal+0.01) SAFE={gid:s.id,k,p};
    if(!TWO&&c&&c.choice==='two_point'&&/égaliser|points? d'avance|revenir à/.test(c.reason||'')) TWO={gid:s.id,k,p};
    if(!PLAIN&&k>3&&!d&&!c&&p.call&&p.call.type==='pass') PLAIN={gid:s.id,k,p}; });
  if(GO&&SAFE&&TWO&&PLAIN) break;
}

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-decisions-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,stdio:'ignore',
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:APRES},env)});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok){ p.data=data; break; } }catch(e){} await pause(250); }
  if(!p.data){ p.kill(); throw new Error('le serveur ne démarre pas'); }
  await (await fetch(`http://localhost:${port}/`)).text();
  return p;
}
async function ouvrir(b,port,opts){
  const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:900}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(`http://localhost:${port}/`,{waitUntil:'domcontentloaded',timeout:90000});
  await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000}); await pause(1500);
  return p;
}
const shot=async(p,nom)=>{ if(SHOTS){ fs.mkdirSync(SHOTS,{recursive:true}); await p.screenshot({path:path.join(SHOTS,nom)}); } };
/* le replay du match gid, posé sur l'action k (en lecture) */
async function surAction(p,gid,k){
  await p.evaluate(async([gid,k])=>{ const f=await (await fetch('/api/feed/'+gid)).json(); window.__gc.openReplayFeed(f);
    await new Promise(r=>setTimeout(r,500)); window.__gc.rpSeek(window.__gc.replayGame(),k); },[gid,k]);
  await pause(900);
}
const carte=p=>p.evaluate(()=>{ const e=document.querySelector('.modal [data-f="coach"]'); if(!e||e.hidden) return null;
  const f=e.closest('.field').getBoundingClientRect(), r=e.getBoundingClientRect();
  return {txt:e.innerText.replace(/\s+/g,' ').trim(), on:[...e.querySelectorAll('.co-wp li.on span')].map(x=>x.textContent),
    dedans:r.left>=f.left-1&&r.right<=f.right+1&&r.top>=f.top-1&&r.bottom<=f.bottom+1}; });
async function resultat(p){ for(let i=0;i<80;i++){ const t=await p.evaluate(()=>{ const e=document.querySelector('.modal [data-f="coach"] .co-res'); return e&&!e.hidden?e.textContent:''; }); if(t) return t; await pause(250); } return ''; }
const pct=v=>Math.round(v*100)+'%';
const fermer=async p=>{ await p.keyboard.press('Escape'); await pause(400); };

(async()=>{
  check(GO&&SAFE&&TWO&&PLAIN,`décisions trouvées dans ${week} (go ${GO&&GO.gid+'#'+GO.k}, plays it safe ${SAFE&&SAFE.gid+'#'+SAFE.k}, 2 points ${TWO&&TWO.gid+'#'+TWO.k})`);
  if(!(GO&&SAFE&&TWO&&PLAIN)){ process.exit(1); }
  const on=await server(8242,{}), off=await server(8243,{GC_DECISIONS:'off'});
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    console.log('— ordinateur 1440 × 900');
    const a=await ouvrir(b,8242);
    await surAction(a,GO.gid,GO.k); let c=await carte(a);
    check(!!c,'4e essai joué : une carte sur le terrain');
    if(c){ const d=GO.p.fourth_down;
      check(/AI coach/i.test(c.txt)&&/4th &/i.test(c.txt)&&/goes for it/i.test(c.txt),`coach, situation, décision (« ${c.txt.slice(0,70)}… »)`);
      check(Object.keys(d.wp).every(k=>c.txt.includes(pct(d.wp[k]))),'chaque option avec sa chance de victoire du moteur');
      check(c.on.length===1&&c.on[0]==='Go for it','l’option retenue en avant');
      check(c.dedans,'la carte tient dans le terrain'); }
    await shot(a,'decision-ordinateur.png');
    const r1=await resultat(a), conv=GO.p.possession_change!=='downs';
    check(conv?/✓/.test(r1):/✗/.test(r1),`résultat à la fin de l’action d’après le GameFeed (« ${r1} »)`);
    await fermer(a);
    await surAction(a,SAFE.gid,SAFE.k); c=await carte(a);
    check(!!c&&/kicks the field goal/i.test(c.txt)&&/plays it safe/i.test(c.txt),'field goal alors que « go » était meilleur : « Plays it safe »');
    await fermer(a);
    await surAction(a,TWO.gid,TWO.k); c=await carte(a);
    check(!!c&&/goes for two/i.test(c.txt)&&/(tie the game|go up by|cut the gap)/i.test(c.txt),`2 points : la raison en anglais (« ${c?c.txt.slice(0,80):'—'} »)`);
    const r2=await resultat(a);
    check(TWO.p.conversion.good?/✓/.test(r2):/✗/.test(r2),`2 points : le résultat (« ${r2} »)`);
    await fermer(a);
    await surAction(a,PLAIN.gid,PLAIN.k);
    check(!(await carte(a)),'action ordinaire : aucune carte');
    await fermer(a);
    errs.push(...a.errs); await a.context().close();

    console.log('— téléphone 390 × 664');
    const m=await ouvrir(b,8242,devices['iPhone 13']);
    await surAction(m,SAFE.gid,SAFE.k);
    const L=await m.evaluate(()=>{ const q=s=>{ const e=document.querySelector(s); return e?e.getBoundingClientRect():null; };
      return {head:q('.modal .m-head'), field:q('.modal .field.big'), panel:q('.modal .m-panel'), w:innerWidth,
        abbr:(document.querySelector('.modal .m-ab')||{}).innerText||'', abbrOn:getComputedStyle(document.querySelector('.modal .m-ab')).display!=='none',
        hscroll:document.documentElement.scrollWidth>innerWidth+1}; });
    check(L.panel&&L.panel.left<=0.5&&L.panel.width>=L.w-1,'le grand écran prend toute la largeur');
    check(L.head&&L.head.height<=56,`en-tête sur une ligne (${L.head?Math.round(L.head.height):'—'} px)`);
    check(L.abbrOn&&/^[A-Z]{2,4}\s*@\s*[A-Z]{2,4}$/.test(L.abbr.trim()),`titre court (« ${L.abbr.trim()} »)`);
    check(L.field&&L.field.left<=0.5&&L.field.width>=L.w-1&&L.field.top<=L.head.bottom+2,`terrain bord à bord sous l’en-tête (${L.field?Math.round(L.field.top)+' px, '+Math.round(L.field.width)+' × '+Math.round(L.field.height):'—'})`);
    check(!L.hscroll,'aucun défilement horizontal');
    c=await carte(m);
    check(!!c&&c.dedans,'la carte tient dans le terrain');
    await shot(m,'decision-telephone.png');
    errs.push(...m.errs); await m.context().close();

    console.log('— GC_DECISIONS=off');
    const z=await ouvrir(b,8243);
    await surAction(z,GO.gid,GO.k);
    check(!(await carte(z)),'aucune carte');
    errs.push(...z.errs); await z.context().close();
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(err){ console.error(err); fail++; }
  finally{ await b.close(); for(const s of [on,off]){ s.kill(); try{ fs.rmSync(s.data,{recursive:true,force:true}); }catch(e){} } }
  console.log(fail?`\n${fail} échec(s)`:'\nTout est bon');
  process.exit(fail?1:0);
})();
