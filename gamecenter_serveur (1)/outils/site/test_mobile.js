// Netteté du terrain, page allégée, redémarrage signalé (section 90, 03/11/2026) — test navigateur (Playwright + serveur).
//   node outils/site/test_mobile.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur au milieu de la dernière semaine (GC_DEMO_AT), écran de densité 2. Vérifie : un match ouvert reste
// net (canevas = 2 × sa taille) tant que le dessin est rapide, même à 30 images/s ; quand le calcul devient lent
// (processeur bridé ×20) la résolution baisse, puis remonte une fois le processeur libéré ; GC_NETTETE=off : la règle
// d'avant (écart entre deux images) ; la page allégée ne porte plus la poche du QB, le pré-snap ni le scouting des matchs
// terminés anciens, et leur replay se charge et se joue ; une page rechargée avec un match ouvert envoie « restart » au
// serveur (/api/diag) ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const DERNIERE=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,DERNIERE,'week.json'),'utf8'));
const REG=W.schedule.filter(g=>g.phase==='regular').sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
const LIVE=REG[Math.floor(REG.length*0.45)], T0=Date.parse(LIVE.kickoff)+60e3;

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-mob-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks'));
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_'))) fs.symlinkSync(path.join(WEEKS,w),path.join(data,'weeks',w));
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(T0).toISOString()},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${port}/api/time`)).ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* netteté : petite fenêtre (le navigateur sans écran dessine en logiciel : ≈ 4,7 ms à 1180 × 820, trop près du seuil de
   remontée de 5 ms ; la règle elle-même est vérifiée, pas la vitesse de la machine) */
const ouvrir=async(b,port,vp)=>{ const ctx=await b.newContext({viewport:vp||{width:1180,height:820},deviceScaleFactor:2});
  const p=await ctx.newPage(); p.errs=[]; p.diag=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await ctx.route('**/api/diag',async rt=>{ try{ const r=rt.request(), raw=r.postDataBuffer(); p.diag.push(...JSON.parse(raw?raw.toString('utf8'):'{}').e||[]); }catch(e){} await rt.continue(); });
  await p.goto(`http://localhost:${port}/`,{timeout:240000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); return p; };
const grandEcran=async(p,gid)=>{ await p.evaluate(gid=>{ const x=document.createElement('button'); x.dataset.sched=gid; document.body.appendChild(x); x.click(); x.remove(); },gid);
  await p.waitForSelector('#modal:not([hidden]) .field canvas',{timeout:30000}); };
const ratio=p=>p.evaluate(()=>{ const c=document.querySelector('#modal .field canvas'); return c?Math.round(c.width/parseFloat(c.style.width)*100)/100:0; });

(async()=>{
  const P1=8211, P2=8212; const srv=await server(P1,{}), b=await chromium.launch({executablePath:EXE}), errs=[]; let srv2=null;
  try{
    console.log(`   horloge : ${new Date(T0).toISOString()} · en direct : ${LIVE.away} @ ${LIVE.home}`);
    /* ---- page allégée ---- */
    const page=await (await fetch(`http://localhost:${P1}/`)).text();
    const wk=JSON.parse(page.split('<script type="application/json" id="gf-week">')[1].split('</script>')[0].replace(/<\\\//g,'</'));
    const leg=Object.entries(wk.feeds).filter(([,f])=>f.light);
    const lourd=leg.some(([,f])=>f.plays.some(x=>'pocket' in x||'presnap' in x||'scout' in x));
    check(leg.length>0&&!lourd,`page : ${leg.length} matchs terminés allégés, sans poche, pré-snap ni scouting (${Math.round(page.length/1e6)} Mo)`);

    /* ---- netteté : rapide = net, même à 30 images/s ---- */
    const p=await ouvrir(b,P1,{width:760,height:620});
    await grandEcran(p,LIVE.id);
    await p.evaluate(()=>{ const raf=window.requestAnimationFrame.bind(window); let last=0;   /* 30 images/s, comme un iPhone en économie d'énergie */
      window.requestAnimationFrame=cb=>raf(function tick(t){ if(t-last<32){ raf(tick); return; } last=t; cb(t); }); });
    await p.waitForTimeout(14000);
    const r1=await ratio(p);
    check(r1===2,`match ouvert, 30 images/s, dessin rapide : le terrain reste net (×${r1})`);
    /* ---- calcul lent : la résolution baisse, puis remonte ---- */
    const cdp=await p.context().newCDPSession(p);
    await cdp.send('Emulation.setCPUThrottlingRate',{rate:20});
    let r2=r1; for(let i=0;i<45&&r2>=2;i++){ await p.waitForTimeout(1000); r2=await ratio(p); }
    check(r2<2,`processeur bridé ×20 : la résolution baisse (×${r2})`);
    await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});
    let r3=r2; for(let i=0;i<100&&r3<=r2;i++){ await p.waitForTimeout(1000); r3=await ratio(p); }
    check(r3>r2,`processeur libéré : la résolution remonte (×${r2} → ×${r3})`);
    for(let i=0;i<10&&!(p.diag.some(e=>e.k==='perf')&&p.diag.some(e=>e.k==='perf-up'));i++) await p.waitForTimeout(1000);   /* envoyé toutes les 4 s */
    const ev=p.diag.map(e=>e.k);
    check(ev.includes('perf')&&ev.includes('perf-up'),`diagnostic : « perf » puis « perf-up » envoyés au serveur`);
    /* ---- redémarrage signalé ---- */
    await p.waitForTimeout(4500);
    p.diag.length=0;
    await p.reload({timeout:240000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000});
    for(let i=0;i<20&&!p.diag.some(e=>e.k==='restart');i++) await p.waitForTimeout(1000);
    const rs=p.diag.find(e=>e.k==='restart');
    check(rs&&rs.was===`s-${LIVE.id}`&&rs.nav==='reload',`page rechargée pendant un match : « restart » (${rs?rs.was+', '+rs.nav+', '+rs.gap+' s':'rien'})`);
    errs.push(...p.errs);

    /* ---- replay d'un match allégé ---- */
    const q=await ouvrir(b,P1);
    const gid=leg[leg.length-1][0];
    await grandEcran(q,gid);
    await q.waitForFunction(()=>document.querySelectorAll('#modal .feed li').length>=2,null,{timeout:90000}).catch(()=>{});   /* ≈ 16 s avant la 1re action (chargement, présentation), puis 6,5 s par action */
    const li=await q.$$eval('#modal .feed li',x=>x.length);
    check(li>=2,`replay d'un match allégé (${gid}) : rechargé et joué (${li} actions dans le play-by-play)`);
    errs.push(...q.errs);

    /* ---- interrupteur GC_NETTETE=off : la règle d'avant ---- */
    srv2=await server(P2,{GC_NETTETE:'off',GC_PAGE_LEGERE:'off'});
    const o=await ouvrir(b,P2);
    const srvj=await o.evaluate(()=>JSON.parse(document.getElementById('gf-server').textContent));
    await grandEcran(o,LIVE.id);
    await o.evaluate(()=>{ const raf=window.requestAnimationFrame.bind(window); let last=0;
      window.requestAnimationFrame=cb=>raf(function tick(t){ if(t-last<32){ raf(tick); return; } last=t; cb(t); }); });
    let r4=2; for(let i=0;i<45&&r4>=2;i++){ await o.waitForTimeout(1000); r4=await ratio(o); }
    const page2=await (await fetch(`http://localhost:${P2}/`)).text();
    check(srvj.nettete_off===true&&r4<2&&/"pocket"/.test(page2),`GC_NETTETE=off, GC_PAGE_LEGERE=off : la règle d'avant (×${r4} à 30 images/s), la page d'avant`);
    errs.push(...o.errs);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); if(srv2) srv2.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
