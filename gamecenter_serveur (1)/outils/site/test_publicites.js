// Publicités (étape 7 de la feuille de route — 13/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_publicites.js          (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Deux serveurs sur une copie des données : sans variable AdSense (rien ne change : aucun script de régie, aucun
// emplacement, /ads.txt absent) et avec un faux identifiant (GC_ADSENSE_CLIENT, GC_ADSENSE_SLOTS). Le script de Google
// est remplacé par un bouchon local (le réseau des tests ne l'atteint pas) qui remplit chaque bloc à sa taille.
// Vérifie : balise et script dans le <head>, /ads.txt, emplacements accueil / onglets (728×90 ordinateur, 320×100
// mobile), aucun sur Live board pendant un autre onglet ni dans Settings / Bets, place réservée (aucun décalage de
// mise en page), mi-temps du grand écran (320×100) mais pas les fins de quart-temps ni le terrain pendant le jeu,
// bandeau « Play money · No real winnings · 18+ » partout, lien /legal, « Privacy choices », mode sombre, mobile 390 px,
// aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const CLIENT='ca-pub-1234567890123456', SLOTS='half=1111111,home=2222222,page=3333333';

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const reg=W.schedule.filter(g=>g.phase==='regular');
const G=reg.filter(g=>g.slot===1)[0];
const AT=new Date(Date.parse(reg.filter(g=>g.slot===3)[0].kickoff)+60e3).toISOString();
const FEED=JSON.parse(fs.readFileSync(path.join(WEEKS,week,G.feed),'utf8'));

async function server(port,env){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-pub-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT,GC_PUSH_LOOP:'0'},env),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* bouchon du script AdSense : chaque push remplit le prochain <ins> vide à sa taille, comme une vraie annonce */
const BOUCHON=`window.__adReq=[];(function(){var q=window.adsbygoogle||[];function fill(){var i=[].slice.call(document.querySelectorAll('ins.adsbygoogle')).filter(function(x){return !x.dataset.adsbygoogleStatus})[0];
  if(!i) return; i.dataset.adsbygoogleStatus='done'; window.__adReq.push(i.dataset.adSlot); var d=document.createElement('div'); d.className='fake-ad';
  d.style.cssText='width:'+i.style.width+';height:'+i.style.height+';background:#888'; i.appendChild(d);}
  window.adsbygoogle={push:function(){fill();}}; for(var k=0;k<q.length;k++) fill();})();`;
const ouvrir=async(b,base,opts,q='')=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  await ctx.route('**/pagead2.googlesyndication.com/**',r=>r.fulfill({status:200,contentType:'text/javascript',body:BOUCHON}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(base+'/'+q); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); await p.waitForTimeout(400); return p; };
const boite=(p,id)=>p.evaluate(id=>{ const b=document.getElementById(id); if(!b) return null; const i=b.querySelector('ins'), r=b.getBoundingClientRect();
  return {vis:!b.hidden&&r.height>0,w:i?parseInt(i.style.width):0,h:i?parseInt(i.style.height):0,filled:!!b.querySelector('.fake-ad'),slot:i&&i.dataset.adSlot,boxH:r.height,right:r.right}; },id);
const vue=async(p,v)=>{ await p.evaluate(v=>window.__gc.season.setView(v),v); await p.waitForTimeout(250); };

(async()=>{
  const s0=await server(8145,{}), s1=await server(8146,{GC_ADSENSE_CLIENT:CLIENT,GC_ADSENSE_SLOTS:SLOTS}); let b;
  const A='http://localhost:8145', B='http://localhost:8146';
  try{
    console.log(`Publicités — ${week}`);
    b=await chromium.launch({executablePath:EXE});
    /* 1. sans variable : rien ne change */
    check((await fetch(A+'/ads.txt')).status===404,'sans AdSense : /ads.txt absent');
    const p0=await ouvrir(b,A);
    const r0=await p0.evaluate(()=>({script:!!document.querySelector('script[src*="googlesyndication"]'),meta:!!document.querySelector('meta[name="google-adsense-account"]'),
      ins:document.querySelectorAll('ins.adsbygoogle').length,home:document.getElementById('adHome').hidden,page:document.getElementById('adPage').hidden,
      foot:(document.querySelector('.site-foot')||{}).textContent||'',priv:document.getElementById('privacyBtn').hidden,
      legal:!!document.querySelector('.site-foot a[href="/legal"]')&&!!document.querySelector('#about a[href="/legal"]')}));
    check(!r0.script&&!r0.meta&&!r0.ins&&r0.home&&r0.page,'sans AdSense : aucun script, aucune balise, aucun emplacement');
    check(/Play money · No real winnings · 18\+/.test(r0.foot)&&r0.legal&&r0.priv,'bandeau « Play money · No real winnings · 18+ » et lien /legal (accueil et pied de page), pas de « Privacy choices »');
    await vue(p0,'schedule');
    check(await p0.evaluate(()=>document.getElementById('adPage').hidden&&!!document.querySelector('.site-foot').offsetParent),'sans AdSense : Schedule sans emplacement, bandeau visible');
    const lg=await fetch(A+'/legal'), lt=await lg.text();
    check(lg.ok&&/18\+ only/.test(lt)&&/Privacy policy/.test(lt)&&/Legal notice/.test(lt)&&/Advertising is currently <b>off<\/b>/.test(lt),'/legal : règles, confidentialité, mentions légales');

    /* 2. avec AdSense */
    const at=await (await fetch(B+'/ads.txt')).text();
    check(at==='google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n','/ads.txt : '+at.trim());
    check(/<loc>[^<]*\/legal<\/loc>/.test(await (await fetch(B+'/sitemap.xml')).text()),'plan du site : /legal');
    const p1=await ouvrir(b,B);
    const h1=await p1.evaluate(()=>({src:(document.querySelector('script[src*="googlesyndication"]')||{}).src||'',meta:(document.querySelector('meta[name="google-adsense-account"]')||{}).content,priv:!document.getElementById('privacyBtn').hidden}));
    check(h1.src.includes('client='+CLIENT)&&h1.meta===CLIENT,'<head> : script AdSense et balise google-adsense-account');
    check(h1.priv,'« Privacy choices » dans le pied de page');
    let x=await boite(p1,'adHome');
    check(x&&x.vis&&x.filled&&x.w===728&&x.h===90&&x.slot==='2222222','accueil : bloc 728×90 (home) rempli');
    const vide=await p1.evaluate(()=>{ const b=document.getElementById('adHome'), f=b.querySelector('.fake-ad'), y0=document.getElementById('about').getBoundingClientRect().top;
      f.remove(); const h=b.getBoundingClientRect().height, y1=document.getElementById('about').getBoundingClientRect().top; b.querySelector('ins').appendChild(f); return {h,dy:y1-y0}; });
    check(Math.abs(vide.h-x.boxH)<0.5&&Math.abs(vide.dy)<0.5,`accueil : place réservée, rien ne bouge à l'arrivée de l'annonce (${x.boxH.toFixed(0)} px avant et après)`);
    const field=await p1.evaluate(()=>document.querySelectorAll('.field ins, .slip-col ins, .live-grid ins').length);
    check(field===0,'rien sur les terrains, les tuiles ni le bulletin');
    for(const v of ['schedule','standings','teams','history']){
      await vue(p1,v); const y=await boite(p1,'adPage'), h=await boite(p1,'adHome');
      check(y.vis&&y.filled&&y.slot==='3333333'&&!h.vis,`${v} : bloc en bas de l'onglet (page), pas celui de l'accueil`);
    }
    for(const v of ['settings','bets','leagues','myteam']){ await vue(p1,v); const y=await boite(p1,'adPage'); check(!y.vis,`${v} : aucun bloc`); }
    await vue(p1,'live');
    const req=await p1.evaluate(()=>window.__adReq.slice());
    check(req.filter(s=>s==='2222222').length===1&&req.filter(s=>s==='3333333').length===1,`une seule demande par emplacement en changeant d'onglet (${req.join(',')})`);

    /* 3. mi-temps du grand écran : bloc 320×100 ; pas aux fins de quart-temps, rien sur le terrain pendant le jeu */
    const R=await p1.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false;
      const out={q:null,half:null,during:0}; let seen=null;
      for(let i=0;i<80000&&!(g.status==='final');i++){
        G.stepGame(g,0.05); const k=g.brk?g.brk.kind:null;
        if(k!==seen){ seen=k; if(!k){ G.updateGameUI(g); await new Promise(r=>setTimeout(r,600)); }   /* transition de sortie (450 ms) */
          if(k){ G.updateGameUI(g); await new Promise(r=>setTimeout(r,30));
          const el=document.querySelector('.field.big .brk'), ins=el&&!el.hidden?el.querySelector('.brk-slot ins'):null;
          const info={ins:!!ins,w:ins?parseInt(ins.style.width):0,h:ins?parseInt(ins.style.height):0,filled:!!(ins&&ins.querySelector('.fake-ad')),label:!!(el&&el.querySelector('.brk-slot .ad-l'))};
          if(k==='q'&&!out.q) out.q=info; if(k==='half'&&!out.half) out.half=info; } }
        if(!k&&i%200===0){ G.updateGameUI(g); out.during+=document.querySelectorAll('.field.big .brk:not([hidden]) ins, .field.big > ins').length; }
        if(out.half&&out.q&&!k&&i%200===0&&g.cur&&g.cur.quarter>=3) break;
      }
      return out;
    },FEED);
    check(R.half&&R.half.ins&&R.half.filled&&R.half.w===320&&R.half.h===100&&R.half.label,'mi-temps du grand écran : bloc 320×100 « Advertisement »');
    check(R.q&&!R.q.ins,'fin de quart-temps : aucun bloc');
    check(R.during===0,'pendant le jeu : rien sur le terrain');
    await p1.keyboard.press('Escape'); await p1.waitForTimeout(300);

    /* 4. mobile 390 px, mode sombre */
    const m=await ouvrir(b,B,{viewport:{width:390,height:844},isMobile:true,hasTouch:true,colorScheme:'dark'});
    const mx=await boite(m,'adHome');
    check(mx.vis&&mx.w===320&&mx.h===100&&mx.right<=390,'mobile : bloc 320×100 dans l\'écran');
    check(await m.evaluate(()=>document.documentElement.scrollWidth<=390),'mobile : pas de défilement horizontal');
    const dk=await m.evaluate(()=>({th:document.documentElement.dataset.theme,c:getComputedStyle(document.querySelector('.ad-l')).color,bg:getComputedStyle(document.body).backgroundColor}));
    check(dk.th==='dark'&&dk.c!==dk.bg,`mode sombre : libellé lisible (${dk.c} sur ${dk.bg})`);

    /* 5. la page /legal suit le thème et marche sur mobile */
    const lp=await m.context().newPage(); await lp.goto(B+'/legal');
    const L=await lp.evaluate(()=>({th:document.documentElement.dataset.theme,w:document.documentElement.scrollWidth,ads:/currently on/.test(document.body.textContent)}));
    check(L.th==='dark'&&L.w<=390&&L.ads,'/legal : mode sombre, mobile, « Advertising is currently on »');

    const errs=[...p0.errs,...p1.errs,...m.errs];
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.error(e); fail++; }
  finally{ if(b) await b.close(); s0.kill(); s1.kill(); }
  console.log(fail?`ÉCHEC : ${fail}`:'OK'); process.exit(fail?1:0);
})();
