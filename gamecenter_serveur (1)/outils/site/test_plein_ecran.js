// « Bigger field » = le match en plein écran (19/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_plein_ecran.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Ouvre le replay d'un match de la dernière semaine sur ordinateur (1440 × 900), sur un téléphone tenu droit (390 × 844)
// et tenu en paysage (844 × 390), passe en « Bigger field » et vérifie : le match occupe tout l'écran (plus de
// play-by-play, de panneaux ni de stats) ; le tableau de score, l'indicateur LIVE / REPLAY et le bandeau du 3e / 4e
// essai restent sur le terrain ; « On air » passe dans le match et le bandeau du 3e essai se range sous lui ; le
// bouton de sortie et les commandes du replay apparaissent au toucher, disparaissent après 2,5 s et ne couvrent
// jamais le score ; téléphone tenu droit : le match est tourné à l'horizontale et un toucher sur un joueur ouvre sa
// fiche ; le bouton ramène la vue normale (play-by-play, « On air » rendu à la page) ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8145;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop(), dir=path.join(WEEKS,w,'games');
  const f=fs.readdirSync(dir).filter(f=>/^w\d+-r\d+\.json$/.test(f)).sort()[0];
  return {F:JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')),src:`${w}/${f}`};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-plein-ecran-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const inter=(a,b)=>a&&b&&a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1;

/* « tourné » = un quart de tour (matrice de rotation), pas n'importe quelle transformation : à l'ouverture, le panneau
   glisse un instant (animation mIn / daUp, translateY) — sur une machine lente, la mesure tombait dedans */
async function cas(b,F,nom,opt){
  console.log(`— ${nom} (${opt.viewport.width} × ${opt.viewport.height})`);
  const ctx=await b.newContext(opt), p=await ctx.newPage(), errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(()=>{ try{ localStorage.setItem('gc-theater-v1','0'); }catch(e){} });
  await p.goto(`http://localhost:${PORT}/`,{waitUntil:"domcontentloaded",timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
  await p.evaluate(F=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
    for(let i=0;i<40000;i++){ G.stepGame(g,0.05); const P=g.cur; if(P&&P.down>=3&&g.idx>10&&g.phase==='presnap') break; }
    g.paused=true; },F);
  await p.click('[data-theater]'); await p.waitForTimeout(300);
  await p.evaluate(()=>Promise.all(document.querySelector('#modal .m-panel').getAnimations().map(a=>a.finished.catch(()=>{}))));
  const etat=()=>p.evaluate(()=>{
    const m=document.getElementById('modal'), q=s=>m.querySelector(s), R=e=>{ if(!e) return null; const r=e.getBoundingClientRect(); return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
    const op=e=>{ let o=1; for(let x=e;x&&x.nodeType===1;x=x.parentElement) o*=+getComputedStyle(x).opacity; return o; };
    const vis=e=>{ if(!e||e.hidden) return false; const r=e.getBoundingClientRect(), c=getComputedStyle(e);
      return r.width>0&&r.height>0&&c.display!=='none'&&c.visibility!=='hidden'&&op(e)>0.05; };
    const bar=[...q('.m-main').children].find(e=>!e.classList.contains('panel')&&!e.classList.contains('field'));
    const a=document.getElementById('onAir');
    return {theater:m.classList.contains('theater'),vw:innerWidth,vh:innerHeight,panel:R(q('.m-panel')),field:R(q('.m-main>.field')),
      fw:q('.m-main>.field').clientWidth,fh:q('.m-main>.field').clientHeight,turned:(e=>{ const t=getComputedStyle(e).transform; if(!t||t==='none') return false; const M=new DOMMatrix(t); return Math.abs(M.b)>0.5&&Math.abs(M.a)<0.5; })(q('.m-panel')),
      feed:vis(q('.m-main>.panel')),side:vis(q('.m-side')),lower:vis(q('.m-lower')),bug:vis(q('.field .bug')),bugR:R(q('.field .bug')),
      pill:vis(q('.field .pill')),third:q('.field .third')&&!q('.field .third').hidden,thirdTop:parseFloat(getComputedStyle(q('.field .third')).top),
      air:a&&a.parentNode===q('.m-panel'),btn:vis(q('[data-theater]')),bar:bar?vis(bar):null,barR:R(bar)};
  });
  let s=await etat();
  check(s.theater,'« Bigger field » activé');
  const plein=s.turned ? Math.abs(s.panel.width-s.vw)<2&&Math.abs(s.panel.height-s.vh)<2 : Math.abs(s.panel.width-s.vw)<2&&Math.abs(s.panel.height-s.vh)<2&&s.panel.left<1&&s.panel.top<1;
  check(plein&&s.fw>=(s.turned?s.vh:s.vw)-2,`le match occupe tout l'écran (${Math.round(s.panel.width)} × ${Math.round(s.panel.height)})`);
  check(!s.feed&&!s.side&&!s.lower,'plus de play-by-play, de panneaux ni de stats');
  if(!(s.bug&&s.pill)) console.log('   ',await p.evaluate(()=>{ const e=document.querySelector('#modal .field .pill'), c=getComputedStyle(e), r=e.getBoundingClientRect();
    return JSON.stringify({hidden:e.hidden,cls:e.className,disp:c.display,vis:c.visibility,op:c.opacity,r:[r.left,r.top,r.width,r.height]}); }));
  check(s.bug&&s.pill,'tableau de score et indicateur LIVE / REPLAY sur le terrain');
  check(s.air,'« On air » passe dans le match');
  check(s.thirdTop>=60,`le bandeau du 3e / 4e essai se range sous « On air » (top ${s.thirdTop}px)`);
  /* 20/10/2026 : la puce du résultat (en haut à gauche) n'est jamais recouverte par « On air » ni par le bandeau du
     3e essai (centrés en haut) — écran étroit, puce longue ; dans les deux ordres (légende puis puce, puce puis légende) */
  const recouvre=await p.evaluate(()=>{ const G=window.__gc, g=G.replayGame(), m=document.getElementById('modal');
    const ch=m.querySelector('.field>.chip-play'), a=document.getElementById('onAir'), t=m.querySelector('.field>.third');
    const R=e=>e&&!e.hidden?e.getBoundingClientRect():null;
    const x=(r1,r2)=>!!(r1&&r2&&r1.left<r2.right-1&&r2.left<r1.right-1&&r1.top<r2.bottom-1&&r2.top<r1.bottom-1);
    const out=[], long='Yardley picks up 14 yards and the first down. The Condors guessed pass, and they got burned.';
    G.caption(long); g.chip={t:'+14 · 1ST DOWN · OUT OF BOUNDS · BURNED',c:'good'}; G.showChip(g);
    out.push([x(R(ch),R(a)),x(R(ch),R(t)),!!R(a),!!R(t)]);
    g.chip={t:'TOUCHDOWN · BROKE TENDENCY',c:'td'}; G.showChip(g); G.caption(long+' '+long.slice(0,40));
    out.push([x(R(ch),R(a)),x(R(ch),R(t)),!!R(a),!!R(t)]);
    return out; });
  check(recouvre.every(r=>r[2]&&!r[0]),`la puce du résultat n'est pas recouverte par « On air » (${JSON.stringify(recouvre)})`);
  check(recouvre.every(r=>!r[3]||!r[1]),'ni par le bandeau du 3e / 4e essai');
  check(s.btn&&s.bar,'au toucher : bouton de sortie et commandes du replay visibles');
  check(!inter(s.barR,s.bugR),'les commandes du replay ne couvrent pas le tableau de score');
  if(opt.viewport.height>opt.viewport.width) check(s.turned&&s.fw>s.fh,'téléphone tenu droit : le match est tourné à l\'horizontale');
  else check(!s.turned,'pas de rotation quand l\'écran est déjà horizontal');
  await p.waitForTimeout(2500); s=await etat();          /* 2,5 s, puis le fondu : jusqu'à 4 s de plus sur une machine lente */
  for(let i=0;i<20&&(s.btn||s.bar);i++){ await p.waitForTimeout(200); s=await etat(); }
  check(!s.btn&&!s.bar,'2,5 s sans toucher : bouton et commandes disparaissent, le match seul');
  if(opt.hasTouch) await p.touchscreen.tap(Math.round(s.vw/2),Math.round(s.vh/2)); else { await p.mouse.move(400,300); await p.mouse.move(420,310); }
  await p.waitForTimeout(600); s=await etat();
  if(!s.btn) console.log('   ',await p.evaluate(()=>{ const b=document.querySelector('[data-theater]'), h=b.parentElement; return JSON.stringify({op:getComputedStyle(h).opacity,r:b.getBoundingClientRect(),d:getComputedStyle(b).display}); }));
  check(s.btn,'un toucher (ou la souris) les fait revenir');
  /* un joueur touché ouvre sa fiche, même quand le match est tourné */
  /* la vue doit avoir dessiné au moins une fois (sinon project() rend −10000 : machine lente) */
  await p.waitForFunction(()=>{ const G=window.__gc, v=G.views[G.views.length-1], pl=v&&v.g.off.find(Boolean); return !!pl&&v.project(pl.x,pl.y).x>-1e3; },null,{timeout:10000}).catch(()=>{});
  const pt=await p.evaluate(()=>{ const G=window.__gc, v=G.views[G.views.length-1], g=v.g, pl=g.off.find(Boolean); const q=v.project(pl.x,pl.y);
    const m=document.getElementById('modal'), turned=(e=>{ const t=getComputedStyle(e).transform; if(!t||t==='none') return false; const M=new DOMMatrix(t); return Math.abs(M.b)>0.5&&Math.abs(M.a)<0.5; })(m.querySelector('.m-panel'));
    return turned?{x:innerWidth-q.y,y:q.x}:{x:q.x,y:q.y}; });
  if(opt.hasTouch) await p.touchscreen.tap(Math.round(pt.x),Math.round(pt.y)); else await p.mouse.click(Math.round(pt.x),Math.round(pt.y));
  await p.waitForTimeout(300);
  check(await p.evaluate(()=>!!document.querySelector('.pcard:not([hidden])')),`un toucher sur un joueur ouvre sa fiche (${Math.round(pt.x)}, ${Math.round(pt.y)})`);
  await p.keyboard.press('Escape'); await p.waitForTimeout(100);
  await p.evaluate(()=>document.getElementById('modal').classList.add('fs-ui'));
  await p.click('[data-theater]'); await p.waitForTimeout(300); s=await etat();
  check(!s.theater&&s.feed&&!s.air,'le bouton ramène la vue normale (play-by-play, « On air » rendu à la page)');
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  await ctx.close();
}

(async()=>{
  const {F,src}=feed(); console.log(src);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    await cas(b,F,'ordinateur',{viewport:{width:1440,height:900}});
    await cas(b,F,'téléphone tenu droit',{viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
    await cas(b,F,'téléphone en paysage',{viewport:{width:844,height:390},isMobile:true,hasTouch:true,deviceScaleFactor:2});
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
