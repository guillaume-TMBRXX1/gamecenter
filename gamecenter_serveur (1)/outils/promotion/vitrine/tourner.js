// Vidéo « vitrine » (promotion, 04/11/2026) : tournage image par image du site réel, caméra virtuelle.
//   node tourner.js <L|P> <dossier> [url]      (lancé par faire_vitrine.sh)
// L = 16:9 (fenêtre 1440×810), P = 9:16 (fenêtre 810×1440), dessin × 3. Pour chaque image : le cadre de la caméra
// (élargi d'un pixel) est capturé, à peine plus grand que la vidéo ; frames.json donne l'origine du cadre et le
// rectangle exact de la caméra (px CSS) : monter.py recadre au sous-pixel. L'horloge de la page (page.clock) et les
// animations CSS (document.getAnimations, figées puis avancées de 1/30 s) suivent l'image : rendu régulier, quelle que
// soit la vitesse de la machine. Scènes : Live Now → zoom sur le match Prime Time → clic → grand écran du match ;
// Standings ; Ranking (le n° 1) ; Teams ; retour à Live Now. Jamais de paris à l'image (HIDE).
// DRY=1 : essai à sec (aucune capture, une image sur 10) pour vérifier les sélecteurs en une minute.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const F=process.argv[2]||'L', OUT=process.argv[3]||'tournage_'+F, URL=process.argv[4]||'http://localhost:8170/';
const OW=F==='L'?1920:1080, VW=F==='L'?1440:810, VH=F==='L'?810:1440, AR=F==='L'?16/9:9/16, DPR=3, FPS=30, DT=1000/FPS;
fs.mkdirSync(OUT,{recursive:true});

const HIDE=`#slipCol,#fab,.wallet-pill,.markets,.odds-row,.rp-note,[data-view=bets],.srv-pill,.tk .mk,.tk [data-tf=mv],.toast,#onAir,
  .gc-hide{display:none!important}
  @media (min-width:1100px){.app{grid-template-columns:72px 1fr!important}}
  html{scrollbar-width:none} ::-webkit-scrollbar{display:none}
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

(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--force-device-scale-factor='+DPR,'--hide-scrollbars']});
  const ctx=await b.newContext({viewport:{width:VW,height:VH},deviceScaleFactor:DPR,colorScheme:'dark'});
  const p=await ctx.newPage(); const cdp=await ctx.newCDPSession(p); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(()=>{ try{ localStorage.setItem('gc-theme','dark'); localStorage.setItem('gc-muted','1'); }catch(e){} });
  await p.clock.install(); await p.clock.pauseAt(Date.now()+1000);
  const run=ms=>p.clock.runFor(ms);
  await p.goto(URL);
  for(let k=0;!(await p.evaluate(()=>!!(document.querySelector('.field-hit')))) ;k++){ if(k>900) throw new Error('le site ne démarre pas'); await run(100); }
  await p.addStyleTag({content:HIDE});
  await p.evaluate(C=>{
    const c=document.createElement('div'); c.id='pcur'; c.innerHTML=C; document.body.appendChild(c);
    const r=document.createElement('div'); r.id='pring'; document.body.appendChild(r);
    /* animations et transitions CSS sur l'horloge pilotée : chacune est figée puis avancée de 1/60 s par image */
    const seen=new WeakMap();
    window.__step=dt=>{ for(const a of document.getAnimations()){ if(!seen.has(a)){ seen.set(a,+a.currentTime||0); try{ a.pause(); }catch(e){} }
        else { const t=seen.get(a)+dt; seen.set(a,t); try{ a.pause(); a.currentTime=t; }catch(e){} } } };
    /* le texte « Moneyline, spread… » de la fenêtre du match : jamais de paris dans la promo */
    window.__clean=()=>{ document.querySelectorAll('#modal p, #modal div').forEach(e=>{ if(e.children.length<3&&/^(Moneyline|Both play fingerprints)/.test(e.textContent.trim())) e.classList.add('gc-hide'); }); };
  },CURSOR);
  await p.evaluate(()=>Promise.all(["900 44px 'Big Shoulders Display'","800 10px Manrope","600 12px Manrope"].map(f=>document.fonts.load(f))).then(()=>document.fonts.ready));
  await run(1500);

  /* mesures (coordonnées document : viewport + défilement) */
  const box=(sel,i=0,scope='document')=>p.evaluate(([sel,i])=>{ const els=[...document.querySelectorAll(sel)].filter(e=>e.offsetParent!==null||getComputedStyle(e).position==='fixed');
      const e=els[i]; if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height}; },[sel,i]);
  const fit=(r,pad=0,minW=0)=>{ let w=Math.max(r.w+2*pad,(r.h+2*pad)*AR,minW); w=Math.min(w,VW); return {cx:r.x+r.w/2,cy:r.y+r.h/2,w}; };
  const full=(cy)=>({cx:VW/2,cy:cy===undefined?VH/2:cy,w:VW});
  const textBox=(re,scope='main')=>p.evaluate(([re,scope])=>{ const R=new RegExp(re); const e=[...document.querySelectorAll(scope+' *')].find(x=>x.offsetParent&&x.children.length===0&&R.test(x.textContent.trim()));
      if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height}; },[re,scope]);
  const docH=()=>p.evaluate(()=>document.scrollingElement.scrollHeight);

  const meta=[]; let n=0;
  /* une scène : dur (s), cam [{t,cx,cy,w}] (document), cur [{t,x,y}], ev [{t,fn}], fixed (caméra en coordonnées de la fenêtre) */
  async function scene(name,S){
    const frames=Math.round(S.dur*FPS); const ev=(S.ev||[]).slice().sort((a,b)=>a.t-b.t); let ei=0, scroll=await p.evaluate(()=>scrollY);
    const H=await docH();
    const stepF=process.env.DRY?10:1;
    for(let f=0;f<frames;f+=stepF){
      const t=f/FPS;
      while(ei<ev.length&&ev[ei].t<=t){ await ev[ei].fn(); ei++; }
      const c=at(S.cam,t,camMix); const ch=c.w/AR;
      /* la caméra suit le défilement : la page défile juste ce qu'il faut pour que le cadre soit dans la fenêtre */
      if(!S.fixed){ let want=Math.min(Math.max(scroll,c.cy+ch/2-VH),c.cy-ch/2); want=Math.max(0,Math.min(want,H-VH));
        if(Math.abs(want-scroll)>0.01){ scroll=await p.evaluate(y=>{ window.scrollTo(0,y); return scrollY; },want); } }
      const oy=S.fixed?0:scroll;
      const cw=Math.min(c.w,VW), chh=cw/AR;
      const cam={x:Math.max(0,Math.min(VW-cw,c.cx-cw/2)),y:Math.max(0,Math.min(VH-chh,c.cy-chh/2-oy)),w:cw,h:chh};
      if(S.cur){ const q=at(S.cur,t,ptMix); const vx=q.x, vy=q.y-oy;
        await p.mouse.move(vx,vy);
        await p.evaluate(([x,y])=>{ document.getElementById('pcur').style.transform=`translate(${x-5}px,${y-2.5}px)`; },[vx,vy]); }
      else await p.evaluate(()=>{ document.getElementById('pcur').style.transform='translate(-100px,-100px)'; });
      await run(DT); await p.evaluate(dt=>{ window.__step(dt); window.__clean(); },DT);
      const x0=Math.max(0,Math.floor(cam.x)-1), y0=Math.max(0,Math.floor(cam.y)-1);
      const x1=Math.min(VW,Math.ceil(cam.x+cam.w)+1), y1=Math.min(VH,Math.ceil(cam.y+cam.h)+1);
      if(process.env.DRY){ meta.push({f:n,scene:name}); n++; continue; }
      const file=path.join(OUT,`f${String(n).padStart(5,'0')}.jpg`);
      const sc=Math.min(1,OW/cam.w*1.08/DPR);
      const r=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:93,optimizeForSpeed:true,clip:{x:x0,y:y0,width:x1-x0,height:y1-y0,scale:sc}});
      fs.writeFileSync(file,Buffer.from(r.data,'base64'));
      meta.push({f:n,scene:name,clip:[x0,y0],cam:[cam.x,cam.y,cam.w,cam.h]}); n++;
      if(n%60===0) console.log(F,name,n);
    }
    fs.writeFileSync(path.join(OUT,'frames.json'),JSON.stringify({F,VW,VH,DPR,FPS,frames:meta}));
    return S;
  }
  /* le clic : l'anneau se resserre, puis l'action */
  const ring=(x,y)=>p.evaluate(([x,y])=>{ const r=document.getElementById('pring'); const t0=performance.now();
      const f=()=>{ const q=Math.min(1,(performance.now()-t0)/420); r.style.transform=`translate(${x}px,${y}px) scale(${1.25-.55*q})`; r.style.opacity=q<1?String(.9*(1-q)):'0'; if(q<1) requestAnimationFrame(f); }; f(); },[x,y]);
  const setView=async v=>{ await p.evaluate(v=>document.querySelector(`[data-view=${v}]`).click(),v); await run(1200); await p.evaluate(()=>window.scrollTo(0,0)); await run(300); await p.evaluate(dt=>window.__step(2000),0); };

  /* ── 1. Live Now → zoom sur le match vedette → clic → le grand terrain ── */
  await p.evaluate(()=>window.scrollTo(0,0)); await run(200);
  const feat=await box('.tile.feat'), fh=await box('.field-hit'), title=await box('main h1, main h2');
  const L=F==='L';
  const wide=L?full(VH/2):full(VH/2);
  const fhc={x:fh.x+fh.w*.55,y:fh.y+fh.h*.5};
  const s1={dur:4.4,fixed:true,cam:[
      {t:0,...wide,w:VW*1.0},
      {t:1.2,...fit(feat,L?40:30),cy:fit(feat,L?40:30).cy-(L?60:120),w:Math.min(VW,fit(feat,L?40:30).w*1.25)},
      {t:2.6,...fit(fh,L?18:10)},
      {t:3.4,...fit(fh,L?18:10),w:fit(fh,L?18:10).w*.86},
      {t:4.4,...fit(fh,L?18:10),w:fit(fh,L?18:10).w*.8}],
    cur:[{t:0,x:VW*.92,y:VH*.98},{t:1.4,x:fhc.x+60,y:fhc.y+40},{t:2.7,x:fhc.x,y:fhc.y},{t:3.5,x:fhc.x-30,y:fhc.y-10}],
    ev:[{t:3.5,fn:async()=>{ await ring(fhc.x-30,fhc.y-10); }},
        {t:3.62,fn:async()=>{ await p.evaluate(()=>document.querySelector('.field-hit').click()); }}]};
  await scene('home',s1);
  // la fenêtre du match (position fixe) : caméra en coordonnées de la fenêtre
  await p.evaluate(()=>window.__clean());
  const big=await p.evaluate(()=>{ const r=document.querySelector('#modal .field.big').getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; });
  const bigc={x:big.x+big.w*.5,y:big.y+big.h*.55};
  await scene('board',{dur:2.6,fixed:true,cam:[
      {t:0,cx:bigc.x,cy:bigc.y,w:Math.min(VW,fit(big,0).w*.62)},
      {t:1.1,...fit(big,L?12:6)},
      {t:2.6,...fit(big,L?12:6),w:fit(big,L?12:6).w*.9}],
    cur:[{t:0,x:fhc.x-30,y:Math.min(VH-40,bigc.y+40)},{t:2.6,x:bigc.x+big.w*.18,y:bigc.y+big.h*.12}]});

  /* ── 2. Standings ── */
  await p.keyboard.press('Escape'); await run(600);
  await setView('standings');
  const st0=await box('main table, main .conf, main section',0), rows=await p.evaluate(()=>[...document.querySelectorAll('main tbody tr')].filter(r=>r.offsetParent).slice(0,9).map(r=>{const b=r.getBoundingClientRect(); return {x:b.left+scrollX,y:b.top+scrollY,w:b.width,h:b.height};}));
  const r0=rows[0], r6=rows[Math.min(6,rows.length-1)];
  const sw=L?VW*.62:VW*.8;
  await scene('standings',{dur:2.8,cam:[
      {t:0,cx:r0.x-24+sw*.45,cy:r0.y-20,w:sw*.9},
      {t:2.8,cx:r0.x-24+sw*.525,cy:r6.y,w:sw*1.05}],
    cur:[{t:0,x:r0.x+r0.w*.35,y:r0.y+r0.h/2+30},{t:0.9,x:r0.x+r0.w*.3,y:rows[2].y+rows[2].h/2},{t:1.8,x:r0.x+r0.w*.38,y:rows[4].y+rows[4].h/2},{t:2.8,x:r0.x+r0.w*.42,y:r6.y+r6.h/2}]});

  /* ── 3. Ranking : les leaders, zoom sur le n° 1 ── */
  await setView('ranking');
  const rk=await p.evaluate(()=>[...document.querySelectorAll('main tbody tr')].filter(r=>r.offsetParent).slice(0,6).map(r=>{const b=r.getBoundingClientRect(); return {x:b.left+scrollX,y:b.top+scrollY,w:b.width,h:b.height};}));
  const k0=rk[0], k2=rk[2];
  const yds=await p.evaluate(()=>{ const e=[...document.querySelectorAll('main th, main thead *')].find(x=>x.offsetParent&&/^yds$/i.test(x.textContent.trim())); if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left,w:r.width}; }) || {x:k0.x+k0.w*.62,w:40};
  const rL=k0.x-14, rW=Math.max(yds.x+yds.w+36-rL,L?420:300);
  await scene('ranking',{dur:2.6,cam:[
      {t:0,cx:VW/2,cy:Math.max(VH/2*(L?1:.7),k0.y+40),w:VW},
      {t:1.6,cx:rL+rW/2,cy:(k0.y+k2.y+k2.h)/2,w:rW},
      {t:2.6,cx:rL+rW*.47,cy:(k0.y+k2.y+k2.h)/2,w:rW*.92}],
    cur:[{t:0,x:VW*.75,y:k0.y+200},{t:1.5,x:k0.x+k0.w*.42,y:k0.y+k0.h/2+2},{t:2.6,x:k0.x+k0.w*.6,y:k0.y+k0.h/2+4}]});

  /* ── 4. Teams : la grille des 24 franchises ── */
  await setView('teams');
  const cards=await p.evaluate(()=>[...document.querySelectorAll('main .team-card')].filter(e=>e.offsetParent).slice(0,12).map(e=>{ const r=e.getBoundingClientRect(); return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height}; }));
  if(cards.length<8) throw new Error('cartes des équipes : '+cards.length);
  const c0=cards[0], sel=cards.slice(0,L?8:6), U={x:Math.min(...sel.map(c=>c.x)),y:Math.min(...sel.map(c=>c.y))}; U.r=Math.max(...sel.map(c=>c.x+c.w)); U.b=Math.max(...sel.map(c=>c.y+c.h));
  const cLast={x:U.x,y:U.y,w:U.r-U.x,h:U.b-U.y}, c0L=c0;
  const gw=L?VW*.55:VW*.78;
  const cc=i=>({x:cards[i].x+cards[i].w*.5,y:cards[i].y+cards[i].h*.55});
  await scene('teams',{dur:2.8,cam:[
      {t:0,cx:c0.x+c0.w*.9,cy:c0.y+c0.h*.9,w:gw*.75},
      {t:2.8,...fit(cLast,L?50:24)}],
    cur:[{t:0,x:cc(0).x,y:cc(0).y+30},{t:0.8,...cc(1)},{t:1.6,...cc(L?5:3)},{t:2.8,...cc(L?6:4)}]});

  /* ── 5. Retour à Live Now, plan large ── */
  await setView('live');
  const t2=await textBox('^LIVE$|^LIVE NOW$|^NOW$','main')||{x:120,y:150,w:200,h:60};
  const ttl=await box('main h1, main .h-title, main header h1')||t2;
  await scene('outro',{dur:2.4,cam:[
      {t:0,cx:ttl.x+(L?260:200),cy:ttl.y+ttl.h/2+(L?60:120),w:L?VW*.48:VW*.62},
      {t:2.0,...full(VH/2)},{t:2.4,...full(VH/2)}],
    cur:[{t:0,x:ttl.x+300,y:ttl.y+140},{t:2.4,x:VW*.7,y:VH*.6}]});

  fs.writeFileSync(path.join(OUT,'frames.json'),JSON.stringify({F,VW,VH,DPR,FPS,frames:meta}));
  if(errs.length) console.log('erreurs JS :',errs.slice(0,5));
  console.log(F,'images :',n);
  await b.close();
})().catch(e=>{ console.error(e); process.exit(1); });
