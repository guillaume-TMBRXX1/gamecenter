// Vidéo « vitrine » (promotion ; v1 04/11/2026, v2 21/11/2026) : tournage image par image du site réel, caméra virtuelle.
//   node tourner.js <L|P> <dossier> [url]      (lancé par faire_vitrine.sh)
// L = 16:9 (fenêtre 1440×810), P = 9:16 (fenêtre 810×1440), dessin × 3. Pour chaque image : le cadre de la caméra
// (élargi d'un pixel) est capturé, à peine plus grand que la vidéo ; frames.json donne l'origine du cadre et le
// rectangle exact de la caméra (px CSS) : monter.py recadre au sous-pixel. L'horloge de la page (page.clock) et les
// animations CSS (document.getAnimations, figées puis avancées de 1/30 s) suivent l'image : rendu régulier, quelle que
// soit la vitesse de la machine.
// v2 (demande de Guillaume, 21/11 : plans plus longs pour lire, post Reddit, fonctionnalités récentes) : connecté avec le
// compte de démonstration (VITRINE_COMPTE, fichier JSON {token, name} de compte_demo.py : Insights Pro, badges) ;
// l'horloge du site est calée pour que le plan du match tombe sur une décision du coach IA (VITRINE_T0 : heure du site,
// en ms, au début du premier plan ; la page s'ouvre 30 s avant, puis l'horloge pilotée la mène à VITRINE_T0) ; la
// réponse de /api/delta perd son heure (sinon le site se recale sur l'horloge du serveur, qui file plus vite que le
// tournage, et le match saute). Scènes : Live Now → le match Prime Time (carte « AI coach ») → clic → grand écran ;
// Standings ; Ranking ; Insights › Tracking (stat du jour, tableau Passing) → clic sur le n° 1 → sa fiche (Tracking,
// carte des passes) ; Teams ; Badges ; retour à Live Now. Jamais de paris à l'image (HIDE, nettoyer).
// DRY=1 : essai à sec (aucune capture, une image sur 10) pour vérifier les sélecteurs en quelques minutes.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const F=process.argv[2]||'L', OUT=process.argv[3]||'tournage_'+F, URL=process.argv[4]||'http://localhost:8170/';
const OW=F==='L'?1920:1080, VW=F==='L'?1440:810, VH=F==='L'?810:1440, AR=F==='L'?16/9:9/16, DPR=3, FPS=30, DT=1000/FPS;
const COMPTE=process.env.VITRINE_COMPTE?JSON.parse(fs.readFileSync(process.env.VITRINE_COMPTE,'utf8')):null;
const T0=+process.env.VITRINE_T0||0;
const PLEIN=process.env.VITRINE_ZOOM!=='1';   /* écran entier (demande de Guillaume, 22/11) : la caméra ne zoome jamais, elle suit seulement le défilement ; VITRINE_ZOOM=1 : cadrages serrés (v2) */
const SCENES=process.env.VITRINE_SCENES?process.env.VITRINE_SCENES.split(','):null;   /* refaire seulement ces scènes (les autres : gestes sans images) */
fs.mkdirSync(OUT,{recursive:true});

const HIDE=`#slipCol,#fab,.wallet-pill,.markets,.odds-row,.rp-note,[data-view=bets],.srv-pill,.tk .mk,.tk [data-tf=mv],.toast,#onAir,#qb,
  #viewBadges .bd-cat[aria-label="Reading the game"],.gc-hide{display:none!important}
  @media (min-width:1100px){.app{grid-template-columns:72px 1fr!important}}
  html{scrollbar-width:none} ::-webkit-scrollbar{display:none} .pcard{scrollbar-width:none}
  #pcur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;will-change:transform;filter:drop-shadow(0 2px 4px rgba(0,0,0,.55))}
  #pring{position:fixed;left:0;top:0;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;z-index:2147483646;pointer-events:none;
    border:2px solid rgba(255,255,255,.9);opacity:0;background:rgba(255,255,255,.12)}`;
const CURSOR=`<svg viewBox="0 0 26 26"><path d="M5 2.5v19.2l4.9-4.7 3.2 7.2 3.3-1.5-3.1-7.1h6.8z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>`;

const ease=q=>q<.5?4*q*q*q:1-Math.pow(-2*q+2,3)/2;
const lerp=(a,b,q)=>a+(b-a)*q;
/* une suite d'images clés {t, …} → la valeur à l'instant t (interpolation douce) */
function at(keys,t,mix){ if(t<=keys[0].t) return keys[0]; for(let i=1;i<keys.length;i++){ const a=keys[i-1], b=keys[i];
  if(t<=b.t){ const q=(b.ease===false?x=>x:ease)((t-a.t)/(b.t-a.t)); return mix(a,b,q); } } return keys[keys.length-1]; }
const camMix=(a,b,q)=>({cx:lerp(a.cx,b.cx,q),cy:lerp(a.cy,b.cy,q),w:Math.exp(lerp(Math.log(a.w),Math.log(b.w),q))});
const ptMix=(a,b,q)=>({x:lerp(a.x,b.x,q),y:lerp(a.y,b.y,q)});
const vMix=(a,b,q)=>({v:lerp(a.v,b.v,q)});

(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--force-device-scale-factor='+DPR,'--hide-scrollbars']});
  const ctx=await b.newContext({viewport:{width:VW,height:VH},deviceScaleFactor:DPR,colorScheme:'dark'});
  const p=await ctx.newPage(); const cdp=await ctx.newCDPSession(p); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(a=>{ try{ localStorage.setItem('gc-theme','dark'); localStorage.setItem('gc-muted','1');
    if(a) localStorage.setItem('gc-player-v1',JSON.stringify({token:a.token,name:a.name,account:true})); }catch(e){} },COMPTE);
  /* la page s'ouvre 30 s avant VITRINE_T0 ; /api/delta sans heure : le site garde l'horloge pilotée */
  if(T0) await p.route(u=>u.pathname==='/',async route=>{ const r=await route.fetch(); const h=Object.assign({},r.headers());
    delete h['content-encoding']; delete h['content-length'];
    const body=(await r.text()).replace(/(id="gf-server">\{"api":"\/api","now":)\d+/,(m,a)=>a+(T0-30000));
    await route.fulfill({status:r.status(),headers:h,body}); });
  await p.route('**/api/delta*',async route=>{ try{ const r=await route.fetch(); const j=await r.json(); delete j.now;
    await route.fulfill({status:r.status(),contentType:'application/json',body:JSON.stringify(j)}); }catch(e){ await route.abort().catch(()=>{}); } });
  await p.clock.install(); await p.clock.pauseAt(Date.now()+1000);
  const run=ms=>p.clock.runFor(ms);
  await p.goto(URL,{timeout:180000});
  for(let k=0;!(await p.evaluate(()=>!!(document.querySelector('.field-hit')&&window.__gc&&window.__gc.season))) ;k++){ if(k>900) throw new Error('le site ne démarre pas'); await run(100); }
  await p.addStyleTag({content:HIDE});
  await p.evaluate(C=>{
    const c=document.createElement('div'); c.id='pcur'; c.innerHTML=C; document.body.appendChild(c);
    const r=document.createElement('div'); r.id='pring'; document.body.appendChild(r);
    /* animations et transitions CSS sur l'horloge pilotée : chacune est figée puis avancée de 1/30 s par image */
    const seen=new WeakMap();
    window.__step=dt=>{ for(const a of document.getAnimations()){ if(!seen.has(a)){ seen.set(a,+a.currentTime||0); try{ a.pause(); }catch(e){} }
        else { const t=seen.get(a)+dt; seen.set(a,t); try{ a.pause(); a.currentTime=t; }catch(e){} } } };
    /* jamais de paris dans la promo : les phrases qui en parlent sont retirées ou raccourcies */
    const TX=[[/ · play money only$/,''],[/ · no points, no advantage, nothing for the size of a bet$/,' · no points, no advantage'],[/a visit, a bet or a vote/,'a visit or a vote']];
    window.__clean=()=>{ document.querySelectorAll('#modal p, #modal div').forEach(e=>{ if(e.children.length<3&&/^(Moneyline|Both play fingerprints)/.test(e.textContent.trim())) e.classList.add('gc-hide'); });
      document.querySelectorAll('#viewInsights .view-head .eyebrow, #viewBadges .view-head .eyebrow, #viewBadges .bd-card p, #viewBadges .bd-card span, #viewBadges .bd-card small').forEach(e=>{
        if(e.children.length) return; let s=e.textContent; for(const [re,to] of TX) s=s.replace(re,to); if(s!==e.textContent) e.textContent=s; }); };
    /* les vues qui se redessinent (Insights à chaque image) : nettoyées dès que le DOM change, avant l'affichage */
    let busy=false; new MutationObserver(()=>{ if(busy) return; busy=true; try{ window.__clean(); }finally{ busy=false; } })
      .observe(document.body,{subtree:true,childList:true,characterData:true});
  },CURSOR);
  await p.evaluate(()=>Promise.all(["900 44px 'Big Shoulders Display'","800 10px Manrope","600 12px Manrope"].map(f=>document.fonts.load(f))).then(()=>document.fonts.ready));
  await run(1500);
  if(T0){ const now=await p.evaluate(()=>window.__gc.season.nowMs());
    if(now>T0) throw new Error(`la page est déjà après VITRINE_T0 (${new Date(now).toISOString()})`);
    const d=await p.evaluate(()=>Date.now()); await p.clock.pauseAt(d+(T0-now)); await run(DT);
    console.log(F,'heure du site',new Date(await p.evaluate(()=>window.__gc.season.nowMs())).toISOString()); }

  /* mesures (coordonnées document : viewport + défilement) */
  const box=(sel,i=0)=>p.evaluate(([sel,i])=>{ const els=[...document.querySelectorAll(sel)].filter(e=>e.offsetParent!==null||getComputedStyle(e).position==='fixed');
      const e=els[i]; if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height}; },[sel,i]);
  const boxes=(sel,n)=>p.evaluate(([sel,n])=>[...document.querySelectorAll(sel)].filter(e=>e.offsetParent).slice(0,n).map(e=>{ const r=e.getBoundingClientRect(); return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height}; }),[sel,n]);
  const fit=(r,pad=0,minW=0)=>{ let w=Math.max(r.w+2*pad,(r.h+2*pad)*AR,minW); w=Math.min(w,VW); return {cx:r.x+r.w/2,cy:r.y+r.h/2,w}; };
  const full=(cy)=>({cx:VW/2,cy:cy===undefined?VH/2:cy,w:VW});
  const union=l=>{ const x=Math.min(...l.map(c=>c.x)), y=Math.min(...l.map(c=>c.y)); return {x,y,w:Math.max(...l.map(c=>c.x+c.w))-x,h:Math.max(...l.map(c=>c.y+c.h))-y}; };
  const docH=()=>p.evaluate(()=>document.scrollingElement.scrollHeight);
  const attendre=async(js,max=200)=>{ for(let k=0;k<max;k++){ if(await p.evaluate(js)) return true; await run(100); await new Promise(r=>setTimeout(r,100)); } return false; };   /* aussi en temps réel : une API lente (Tracking, 1er calcul) a le temps de répondre */

  const meta=[]; let n=0;
  /* une scène : dur (s), cam [{t,cx,cy,w}] (document), cur [{t,x,y}], ev [{t,fn}], fixed (caméra en coordonnées de la
     fenêtre), sc {sel, keys:[{t,v}]} (défilement d'un élément, par exemple la fiche d'un joueur) */
  async function scene(name,S){
    if(SCENES&&!SCENES.includes(name)){ for(const e of (S.ev||[]).slice().sort((a,b)=>a.t-b.t)) await e.fn(); await run(500); return S; }   /* scène non filmée : ses gestes seulement */
    const frames=Math.round(S.dur*FPS); const ev=(S.ev||[]).slice().sort((a,b)=>a.t-b.t); let ei=0, scroll=await p.evaluate(()=>scrollY);
    const H=await docH();
    const stepF=process.env.DRY?10:1;
    for(let f=0;f<frames;f+=stepF){
      const t=f/FPS;
      while(ei<ev.length&&ev[ei].t<=t){ await ev[ei].fn(); ei++; }
      const c0=at(S.cam,t,camMix), c=PLEIN?{cx:VW/2,cy:c0.cy,w:VW}:c0; const ch=c.w/AR;
      /* la caméra suit le défilement : la page défile juste ce qu'il faut pour que le cadre soit dans la fenêtre */
      if(!S.fixed){ let want=Math.min(Math.max(scroll,c.cy+ch/2-VH),c.cy-ch/2); want=Math.max(0,Math.min(want,H-VH));
        if(Math.abs(want-scroll)>0.01){ scroll=await p.evaluate(y=>{ window.scrollTo(0,y); return scrollY; },want); } }
      if(S.sc){ const v=at(S.sc.keys,t,vMix).v; await p.evaluate(([s,v])=>{ const e=document.querySelector(s); if(e) e.scrollTop=v; },[S.sc.sel,v]); }
      const oy=S.fixed?0:scroll;
      const cw=Math.min(c.w,VW), chh=cw/AR;
      const cam={x:Math.max(0,Math.min(VW-cw,c.cx-cw/2)),y:Math.max(0,Math.min(VH-chh,c.cy-chh/2-oy)),w:cw,h:chh};
      if(S.cur){ const q=at(S.cur,t,ptMix); const vx=q.x, vy=q.y-oy;
        await p.mouse.move(vx,vy);
        await p.evaluate(([x,y])=>{ document.getElementById('pcur').style.transform=`translate(${x-5}px,${y-2.5}px)`; },[vx,vy]); }
      else await p.evaluate(()=>{ document.getElementById('pcur').style.transform='translate(-100px,-100px)'; });
      await run(DT*stepF); await p.evaluate(dt=>{ window.__step(dt); window.__clean(); },DT*stepF);
      const x0=Math.max(0,Math.floor(cam.x)-1), y0=Math.max(0,Math.floor(cam.y)-1);
      const x1=Math.min(VW,Math.ceil(cam.x+cam.w)+1), y1=Math.min(VH,Math.ceil(cam.y+cam.h)+1);
      if(process.env.DRY){ if(f%60===0||f+stepF>=frames) await p.screenshot({path:path.join(OUT,`${name}_${String(f).padStart(3,'0')}.png`)});
        meta.push({f:n,scene:name}); n++; continue; }
      const file=path.join(OUT,`f${String(n).padStart(5,'0')}.jpg`);
      const sc=Math.min(1,OW/cam.w*1.08/DPR);
      /* la zone de capture de Chrome est en coordonnées du document : on ajoute le défilement réel de la page (sinon, page
         défilée, le cadre filmé remonte d'autant et le haut de l'image est noir) */
      const sy=await p.evaluate(()=>window.scrollY);
      const r=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:93,optimizeForSpeed:true,clip:{x:x0,y:y0+sy,width:x1-x0,height:y1-y0,scale:sc}});
      fs.writeFileSync(file,Buffer.from(r.data,'base64'));
      meta.push({f:n,scene:name,clip:[x0,y0],cam:[cam.x,cam.y,cam.w,cam.h]}); n++;
      if(n%60===0) console.log(F,name,n);
    }
    fs.writeFileSync(path.join(OUT,'frames.json'),JSON.stringify({F,VW,VH,DPR,FPS,frames:meta}));
    console.log(F,'scène',name,'finie, heure du site',new Date(await p.evaluate(()=>window.__gc.season.nowMs())).toISOString());
    return S;
  }
  /* le clic : l'anneau se resserre, puis l'action */
  const ring=(x,y)=>p.evaluate(([x,y])=>{ const r=document.getElementById('pring'); const t0=performance.now();
      const f=()=>{ const q=Math.min(1,(performance.now()-t0)/420); r.style.transform=`translate(${x}px,${y}px) scale(${1.25-.55*q})`; r.style.opacity=q<1?String(.9*(1-q)):'0'; if(q<1) requestAnimationFrame(f); }; f(); },[x,y]);
  const setView=async v=>{ await p.evaluate(v=>document.querySelector(`[data-view=${v}]`).click(),v); await run(1200); await p.evaluate(()=>window.scrollTo(0,0)); await run(300); await p.evaluate(dt=>window.__step(2000),0); };
  const L=F==='L';

  /* ── 1. Live Now → le match Prime Time : la carte du coach IA → clic → le grand écran ── */
  await p.evaluate(()=>window.scrollTo(0,0)); await run(DT);
  const fh=await box('.field-hit');
  const fhc={x:fh.x+fh.w*.5,y:fh.y+fh.h*.62}, zf=fit(fh,L?22:12);
  await scene('home',{dur:7.4,fixed:true,cam:[
      {t:0,...full()},{t:1.8,...full()},
      {t:4.0,...zf},{t:7.4,...zf,w:zf.w*.94}],
    cur:[{t:0,x:VW*.94,y:VH*.97},{t:1.6,x:VW*.8,y:VH*.85},{t:4.2,x:fhc.x+fh.w*.22,y:fhc.y+30},{t:6.2,x:fhc.x+fh.w*.12,y:fhc.y+10},{t:7.0,x:fhc.x,y:fhc.y}],
    ev:[{t:7.0,fn:()=>ring(fhc.x,fhc.y)},{t:7.12,fn:()=>p.evaluate(()=>document.querySelector('.field-hit').click())}]});
  await p.evaluate(()=>window.__clean());
  const big=await p.evaluate(()=>{ const r=document.querySelector('#modal .field.big').getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; });
  const zb=fit(big,L?14:6);
  await scene('board',{dur:11.5,fixed:true,cam:[
      {t:0,...zb,w:zb.w*.8},{t:1.4,...zb},{t:11.5,...zb,w:zb.w*.95}],
    cur:[{t:0,x:fhc.x,y:Math.min(VH-40,big.y+big.h*.7)},{t:2,x:big.x+big.w*.9,y:big.y+big.h*1.05},{t:11.5,x:big.x+big.w*.92,y:big.y+big.h*1.08}]});

  /* ── 2. Standings ── */
  await p.keyboard.press('Escape'); await run(600);
  await setView('standings');
  const rows=await boxes('main tbody tr',10);
  const r0=rows[0], r7=rows[Math.min(7,rows.length-1)];
  const sw=L?VW*.62:VW*.8;
  await scene('standings',{dur:5.5,cam:[
      {t:0,cx:r0.x-24+sw*.45,cy:r0.y-30,w:sw*.9},{t:1.2,cx:r0.x-24+sw*.45,cy:r0.y-30,w:sw*.9},
      {t:5.5,cx:r0.x-24+sw*.525,cy:r7.y,w:sw*1.05}],
    cur:[{t:0,x:r0.x+r0.w*.35,y:r0.y+r0.h/2+30},{t:1.6,x:r0.x+r0.w*.3,y:rows[1].y+rows[1].h/2},{t:3.2,x:r0.x+r0.w*.38,y:rows[4].y+rows[4].h/2},{t:5.5,x:r0.x+r0.w*.42,y:r7.y+r7.h/2}]});

  /* ── 3. Ranking : les leaders, zoom sur le n° 1 ── */
  await setView('ranking');
  const rk=await boxes('main tbody tr',6);
  const k0=rk[0], k2=rk[2];
  const yds=await p.evaluate(()=>{ const e=[...document.querySelectorAll('main th, main thead *')].find(x=>x.offsetParent&&/^yds$/i.test(x.textContent.trim())); if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left,w:r.width}; }) || {x:k0.x+k0.w*.62,w:40};
  const rL=k0.x-14, rW=Math.max(yds.x+yds.w+36-rL,L?420:300);
  await scene('ranking',{dur:5,cam:[
      {t:0,cx:VW/2,cy:Math.max(VH/2*(L?1:.7),k0.y+40),w:VW},{t:1.0,cx:VW/2,cy:Math.max(VH/2*(L?1:.7),k0.y+40),w:VW},
      {t:3.0,cx:rL+rW/2,cy:(k0.y+k2.y+k2.h)/2,w:rW},
      {t:5,cx:rL+rW*.48,cy:(k0.y+k2.y+k2.h)/2,w:rW*.94}],
    cur:[{t:0,x:VW*.75,y:k0.y+200},{t:2.8,x:k0.x+k0.w*.42,y:k0.y+k0.h/2+2},{t:5,x:k0.x+k0.w*.6,y:k0.y+k0.h/2+4}]});

  /* ── 4. Insights › Tracking : la stat du jour, le tableau Passing → clic sur le n° 1 ── */
  await setView('insights');
  await p.evaluate(()=>document.querySelector('#viewInsights [data-ins-tab="tracking"]').click());
  if(!await attendre(()=>!!document.querySelector('#viewInsights table.trk tbody tr .trk-pl'),300)) throw new Error('Tracking : pas de tableau (compte Pro ?)');
  await run(800); await p.evaluate(()=>{ window.scrollTo(0,0); window.__step(2000); window.__clean(); });
  const today=await box('#viewInsights .trk-today'), tb=await box('#viewInsights table.trk');
  const ths=await p.evaluate(()=>[...document.querySelectorAll('#viewInsights table.trk thead th')].map(h=>{ const r=h.getBoundingClientRect(); return {x:r.left,w:r.width,t:h.textContent.trim()}; }));
  const tr=await boxes('#viewInsights table.trk tbody tr',6), pl=await box('#viewInsights table.trk tbody tr .trk-pl');
  const cpoe=ths.find(h=>/^CPOE/.test(h.t))||ths[4], comp=ths.find(h=>/^Comp %/.test(h.t))||ths[5];
  const tR=Math.min(VW-8,(ths[Math.min(L?8:6,ths.length-1)]||comp).x+(L?60:40)), tL=tb.x-16, tW=tR-tL;
  const tCam={cx:tL+tW/2,cy:tb.y+(tW/AR)/2-26,w:tW};
  const plc={x:pl.x+Math.min(pl.w*.45,90),y:pl.y+pl.h/2};
  await scene('insights',{dur:8.4,cam:[
      {t:0,...fit(today,L?26:14)},{t:3.0,...fit(today,L?26:14),w:fit(today,L?26:14).w*.96},
      {t:4.8,...tCam},{t:8.4,...tCam,w:tCam.w*.97}],
    cur:[{t:0,x:today.x+today.w*.7,y:today.y+today.h*.8},{t:2.6,x:today.x+today.w*.82,y:today.y+today.h*.45},
         {t:5.2,x:cpoe.x+cpoe.w/2,y:tb.y+20},{t:6.4,x:cpoe.x+cpoe.w/2,y:tr[2].y+tr[2].h/2},{t:7.6,...plc}],
    ev:[{t:7.6,fn:async()=>{ const sy=await p.evaluate(()=>scrollY); await ring(plc.x,plc.y-sy); }}]});   /* le clic s'entend et se voit ici ; la fiche s'ouvre au plan suivant */

  /* ── 5. La fiche du joueur : Tracking · this week, carte des passes ── */
  /* la fiche dessine sa partie Tracking quand elle devient visible : on la fait défiler une fois avant de mesurer */
  /* la fiche verrouille le défilement de la page : rouverte page remontée en haut, sinon le cadre filmé est décalé */
  await p.evaluate(()=>window.scrollTo(0,0)); await run(300);
  await p.evaluate(()=>document.querySelector('#viewInsights table.trk tbody tr .trk-pl').click()); await run(300);
  if(!await attendre(()=>!!document.querySelector('.pcard'),100)) throw new Error('la fiche ne s\'ouvre pas');
  await p.evaluate(()=>{ const c=document.querySelector('.pcard'); c.scrollTop=c.scrollHeight; }); await run(400);
  const PCH="document.querySelector('.pcard .trk-pch')||[...document.querySelectorAll('.pcard .trk-gl')].find(e=>/where he throws/i.test(e.textContent))";
  if(!await attendre(new Function('return !!('+PCH+')'),900)) throw new Error('fiche : pas de carte des passes');
  await run(600); await p.evaluate(()=>{ window.__step(2000); const c=document.querySelector('.pcard'); if(c) c.scrollTop=0; });
  const pc=await p.evaluate(()=>{ const c=document.querySelector('.pcard'), r=c.getBoundingClientRect(), s=c.scrollTop;
    const lab=[...c.querySelectorAll('.label')].find(e=>/Tracking · this week/.test(e.textContent)), ch=c.querySelector('.trk-pch')||[...c.querySelectorAll('.trk-gl')].find(e=>/where he throws/i.test(e.textContent));
    const y=e=>e.getBoundingClientRect().top-r.top+s;
    return {x:r.left,y:r.top,w:r.width,h:r.height,trk:lab?y(lab):600,pch:ch?y(ch):900,pchH:ch?(ch.classList.contains('trk-pch')?ch.getBoundingClientRect().height:250):180}; });
  const cw=L?Math.max(pc.w+300,700):Math.min(VW,pc.w+44), chh=cw/AR;
  const ccy=L?pc.y+pc.h/2:pc.y+Math.min(pc.h,chh)/2;
  const top=ccy-chh/2-pc.y;                                  /* haut du cadre, dans la fiche */
  const s1=Math.max(0,pc.trk-top-24), s2=Math.max(s1,pc.pch+pc.pchH/2-(top+chh/2));
  console.log(F,'fiche',JSON.stringify({pc,top,chh,s1,s2}));
  await scene('card',{dur:8,fixed:true,cam:[
      {t:0,cx:pc.x+pc.w/2,cy:ccy,w:cw*1.08},{t:1.2,cx:pc.x+pc.w/2,cy:ccy,w:cw},{t:8,cx:pc.x+pc.w/2,cy:ccy,w:cw*.97}],
    sc:{sel:'.pcard',keys:[{t:0,v:0},{t:2.2,v:0},{t:3.8,v:s1},{t:5.4,v:s1},{t:7.0,v:s2},{t:8,v:s2}]},
    cur:[{t:0,x:pc.x+pc.w*.6,y:pc.y+60},{t:3,x:pc.x+pc.w*.7,y:ccy},{t:8,x:pc.x+pc.w*.62,y:ccy+chh*.2}]});

  /* ── 6. Teams : la grille des 24 franchises ── */
  await p.keyboard.press('Escape'); await run(400);
  await setView('teams');
  const cards=await boxes('main .team-card',12);
  if(cards.length<8) throw new Error('cartes des équipes : '+cards.length);
  const c0=cards[0], cAll=union(cards.slice(0,L?8:6));
  const gw=L?VW*.55:VW*.78;
  const cc=i=>({x:cards[i].x+cards[i].w*.5,y:cards[i].y+cards[i].h*.55});
  await scene('teams',{dur:5,cam:[
      {t:0,cx:c0.x+c0.w*.9,cy:c0.y+c0.h*.9,w:gw*.75},{t:0.8,cx:c0.x+c0.w*.9,cy:c0.y+c0.h*.9,w:gw*.75},
      {t:5,...fit(cAll,L?50:24)}],
    cur:[{t:0,x:cc(0).x,y:cc(0).y+30},{t:1.4,...cc(1)},{t:2.8,...cc(L?5:3)},{t:5,...cc(L?6:4)}]});

  /* ── 7. Badges ── */
  await setView('badges');
  await attendre(()=>!!document.querySelector('#viewBadges .bd-card'),300);
  await run(600); await p.evaluate(()=>{ window.scrollTo(0,0); window.__step(2000); window.__clean(); });
  const bh=await box('#viewBadges .view-head'), bs=await box('#viewBadges .bd-sum')||bh;
  const cats=await boxes('#viewBadges .bd-cat',2), bcards=await boxes('#viewBadges .bd-cat:first-child .bd-card',6);
  const bTop=union([bh,bs]);
  const bc=i=>bcards[Math.min(i,bcards.length-1)];
  await scene('badges',{dur:7.5,cam:[
      {t:0,...fit(bTop,L?24:14)},{t:2.6,...fit(bTop,L?24:14),w:fit(bTop,L?24:14).w*.97},
      {t:4.6,...fit(cats[0],L?24:14)},{t:6.0,...fit(cats[0],L?24:14)},
      {t:7.5,...fit(cats[1]||cats[0],L?24:14)}],
    cur:[{t:0,x:bs.x+bs.w*.3,y:bs.y+bs.h*.5},{t:2.4,x:bs.x+bs.w*.45,y:bs.y+bs.h*.75},
         {t:4.6,x:bc(1).x+bc(1).w*.5,y:bc(1).y+bc(1).h*.5},{t:6.0,x:bc(2).x+bc(2).w*.5,y:bc(2).y+bc(2).h*.5},{t:7.5,x:bc(3).x+bc(3).w*.5,y:bc(3).y+bc(3).h*.9}]});

  /* ── 8. Retour à Live Now, plan large ── */
  await setView('live');
  const ttl=await box('main h1, main .h-title, main header h1')||{x:120,y:150,w:200,h:60};
  await scene('outro',{dur:3.6,cam:[
      {t:0,cx:ttl.x+(L?260:200),cy:ttl.y+ttl.h/2+(L?60:120),w:L?VW*.48:VW*.62},
      {t:2.6,...full()},{t:3.6,...full()}],
    cur:[{t:0,x:ttl.x+300,y:ttl.y+140},{t:3.6,x:VW*.7,y:VH*.6}]});

  fs.writeFileSync(path.join(OUT,'frames.json'),JSON.stringify({F,VW,VH,DPR,FPS,frames:meta}));
  if(errs.length) console.log('erreurs JS :',errs.slice(0,5));
  console.log(F,'images :',n);
  await b.close();
})().catch(e=>{ console.error(e); process.exit(1); });
