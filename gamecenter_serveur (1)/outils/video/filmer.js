// Vidéos verticales (bloc 2, étape 8) : filme le terrain du site en 1080×1920 (Playwright + serveur réel, crochet de
// test). Appelé par outils/video/faire_video.py :   node outils/video/filmer.js plan.json
// plan = {url, feed (chemin du GameFeed), out (dossier), top: {kicker, title, sub}, coaches: {ABR: {offense, defense}},
//         segments: [{type:"card", kicker, title, sub, dur} | {type:"play", index, speed, label, text, after, top?}
//                    | {type:"stats", kicker, title, sub, team, stats:[{v, l}], dur}]}
// (stats, étape 8.6 a : carton aux couleurs de l'équipe, gros chiffres qui montent de 0 à leur valeur en 0,8 s ; une
//  valeur texte, « 49–21 », s'affiche telle quelle.)
// (top d'une action : remplace le bandeau du haut à partir de cette action ; feed : l'action vient d'un autre match.)
// Tournage image par image (étape 8.3) : l'horloge de la page est pilotée (page.clock), elle avance de 1/60 s entre deux
// images en pleine résolution (1080×1920 : mise en page « téléphone » 432×768 × 2,5, terrain dessiné à × 2,5) ; la
// vidéo ne dépend donc ni de la vitesse de la machine ni de la qualité adaptative du site. Écrit out/images/*.jpg,
// out/images.txt (liste ffmpeg « concat » : image + durée) et out/timeline.json (instants du snap et du résultat de
// chaque action, en secondes de vidéo : le son du stade s'y cale).
// Habillage « AI broadcast » (20/10/2026) : l'identité du site (thème sombre, ses couleurs et ses polices lues dans la
// page, couleurs des équipes, verre dépoli) ; le terrain du site en vue normale (le « Bigger field » du 19/10 tourne le
// match d'un quart de tour sur un téléphone tenu droit : la vidéo le montrait couché) ; le journal de l'agent IA qui
// appelle le jeu (coordinateur, lecture de la défense, 4e essai, scouting, appel, lecture du QB) tapé en direct ; la
// probabilité de victoire qui bascule ; le résultat frappé en grand avec un « punch » de caméra. Toutes les animations
// suivent l'horloge pilotée (requestAnimationFrame + performance.now) : même rendu à chaque tournage.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const plan=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const W=432, H=768, DPR=2.5;                       // 1080 × 1920 : la mise en page « téléphone » du site, nette
/* Zones sûres (étape 8.2) : l'interface de TikTok / Reels / Shorts couvre ≈ 215 px en haut (onglets), ≈ 400 px en bas
   (légende, nom du son) et ≈ 140 px à droite (boutons) sur 1920 × 1080 → ici 86, 160 et 56 px. L'accroche est entre 86
   et 188 (avec le score), le terrain entre 194 et 524 (resserré : 40 yards de large au lieu de 70), le journal de l'IA
   entre 490 et 604. */
const VIEW_YARDS=40, FPS=60, DT=1000/FPS, JPEG=97;   // 60 images/s (choix du 13/10)
const FT=194, FB=524;                              // terrain : haut, bas (px CSS)

const CSS=`
  html,body{background:radial-gradient(90% 55% at 15% 8%,var(--vglow) 0%,transparent 60%),
    radial-gradient(70% 45% at 100% 100%,var(--vglow2) 0%,transparent 65%),var(--vbg)!important;background-attachment:fixed!important}
  #modal{background:transparent!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important;padding:0!important}
  body>.app{visibility:hidden!important}   /* le site derrière : seulement le match (comme « Bigger field ») */
  #modal .m-head,#modal .m-side,#modal .m-lower,#modal .m-main>*:not(.field),.toast,.fab,.ticker,#onAir{display:none!important}
  #modal .m-panel,#modal .m-body,#modal .m-main{background:transparent!important;border:0!important;box-shadow:none!important;transform:none!important;
    backdrop-filter:none!important;-webkit-backdrop-filter:none!important;filter:none!important;overflow:visible!important;max-height:none!important;contain:none!important}
  #modal .field.big{position:fixed!important;left:0!important;right:0!important;top:${FT}px!important;height:${FB-FT}px!important;width:${W}px!important;
    margin:0!important;border-radius:0!important;z-index:9000;transform-origin:50% 60%}
  #modal .field.big>.pill,#modal .field.big .bug,#modal .field.big>.chip-play{display:none!important}
  .vid{position:fixed;left:0;width:${W}px;box-sizing:border-box;z-index:9999;color:var(--vink);pointer-events:none;font-family:Manrope,Sora,system-ui,sans-serif}
  #vidTop{top:0;height:${FT}px;padding:84px 62px 0 18px}
  #vidTop .vk{display:inline-flex;align-items:center;gap:7px;height:22px;padding:0 10px;border-radius:999px;background:var(--vglass);
    border:1px solid var(--vline);font:800 10.5px/1 Manrope,system-ui;letter-spacing:.16em;text-transform:uppercase;color:var(--vink2)}
  #vidTop .vk i{width:7px;height:7px;border-radius:50%;background:var(--vlive);box-shadow:0 0 8px var(--vlive)}
  #vidTop .vt{font:900 38px/.98 'Big Shoulders Display',Archivo,system-ui;text-transform:uppercase;margin-top:9px;white-space:nowrap;letter-spacing:.005em}
  #vidTop .vt span{display:inline-block;transform-origin:0 80%}
  #vidTop .vs{display:none}
  #vidBug{top:${FT-36}px;left:18px;width:auto;display:flex;align-items:stretch;border-radius:12px;overflow:hidden;background:var(--vglass);
    border:1px solid var(--vline);backdrop-filter:blur(8px);font:800 13px/1 'Big Shoulders Display',Archivo,system-ui}
  #vidBug .t{display:flex;align-items:center;gap:6px;padding:6px 9px;border-top:3px solid var(--tc)}
  #vidBug .t b{font:900 19px/1 'Big Shoulders Display',system-ui;font-variant-numeric:tabular-nums}
  #vidBug .t em{font-style:normal;letter-spacing:.08em;font-size:13px;opacity:.9}
  #vidBug .c{display:flex;align-items:center;padding:0 9px;font:700 11px/1 Manrope,system-ui;color:var(--vink2);border-left:1px solid var(--vline)}
  #vidHud{top:490px;left:12px;width:${W-12-60}px;border-radius:16px;padding:9px 12px 10px;background:var(--vglass2);border:1px solid var(--vline);
    backdrop-filter:blur(10px);box-shadow:0 10px 30px rgba(0,0,0,.45)}
  #vidHud::before{content:"";position:absolute;inset:-1px;border-radius:inherit;padding:1px;background:var(--vbrand);
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;opacity:.85}
  #vidHud .vh-h{display:flex;align-items:center;gap:7px;font:800 10px/1 Manrope,system-ui;letter-spacing:.14em;text-transform:uppercase;color:var(--vink2)}
  #vidHud .vh-h .vh-ai{display:inline-grid;place-items:center;height:17px;padding:0 6px;border-radius:5px;background:var(--vbrand);color:#fff;letter-spacing:.08em;font-size:9.5px}
  #vidHud .vh-h .vh-who{color:var(--vink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
  #vidHud .vh-h .vh-mk{display:flex;align-items:center;gap:5px;color:var(--vink);letter-spacing:.04em;text-transform:none;font-size:10.5px}
  #vidHud .vh-h .vh-mk i{width:15px;height:15px;border-radius:5px;background:linear-gradient(135deg,#2EE6FF,#7A5CFF 55%,#FF3D9A);display:grid;place-items:center}
  #vidHud .vh-h .vh-mk svg{width:11px;height:11px}
  #vidHud .vh-l{margin-top:5px;font:600 12.5px/1.25 'Azeret Mono',ui-monospace,monospace;color:var(--vink);white-space:nowrap;overflow:hidden;min-height:15.6px}
  #vidHud .vh-l b{color:var(--vacc);font-weight:700}
  #vidHud .vh-l .vh-c{display:inline-block;width:7px;height:12px;margin-left:2px;vertical-align:-1px;background:var(--vacc)}
  #vidHud .vh-w{display:flex;align-items:center;gap:8px;margin-top:7px;font:800 10px/1 Manrope,system-ui;letter-spacing:.1em;color:var(--vink2);text-transform:uppercase}
  #vidHud .vh-w .vh-b{flex:1;height:7px;border-radius:4px;background:rgba(255,255,255,.12);overflow:hidden}
  #vidHud .vh-w .vh-b i{display:block;height:100%;border-radius:4px;background:var(--tc)}
  #vidHud .vh-w b{font:900 16px/1 'Big Shoulders Display',system-ui;color:var(--vink);letter-spacing:.02em;min-width:76px;text-align:right}
  #vidStamp{top:${FT}px;height:${FB-FT}px;display:grid;place-items:center;z-index:9998}
  #vidStamp div span{display:inline-block;white-space:nowrap}
  #vidStamp div{width:100%;box-sizing:border-box;font:900 66px/.9 'Big Shoulders Display',Archivo,system-ui;text-transform:uppercase;color:#fff;letter-spacing:.01em;
    text-shadow:0 0 22px var(--tc),0 0 4px var(--tc),0 4px 0 rgba(0,0,0,.35);opacity:0;text-align:center;padding:0 16px}
  #vidStamp div span::after{content:"";display:block;height:6px;margin:6px 6% 0;border-radius:3px;background:var(--vbrand)}
  #vidStamp div small{display:block;margin-top:6px;font:800 13px/1 Manrope,system-ui;letter-spacing:.2em;text-shadow:none;opacity:.92}
  #vidFlash{top:${FT}px;height:${FB-FT}px;z-index:9997;background:var(--tc);opacity:0;mix-blend-mode:screen}
  #vidFoot{top:610px;bottom:0;padding:0 18px;display:flex;align-items:flex-start;padding-top:16px}
  #vidFoot .vu{font:900 15px/1 'Big Shoulders Display',system-ui;letter-spacing:.2em;background:var(--vbrand);-webkit-background-clip:text;background-clip:text;color:transparent;opacity:.75}
  #vidCard{top:0;height:${H}px;display:none;flex-direction:column;justify-content:center;padding:0 64px 0 26px;
    background:radial-gradient(100% 60% at 10% 0%,var(--vglow) 0%,transparent 62%),radial-gradient(80% 50% at 100% 100%,var(--vglow2) 0%,transparent 70%),var(--vbg)}
  #vidCard .vk{display:inline-flex;align-self:flex-start;align-items:center;gap:7px;height:24px;padding:0 11px;border-radius:999px;background:var(--vglass);
    border:1px solid var(--vline);font:800 11px/1 Manrope,system-ui;letter-spacing:.18em;text-transform:uppercase;color:var(--vink2)}
  #vidCard .vk i{width:7px;height:7px;border-radius:50%;background:var(--vlive);box-shadow:0 0 8px var(--vlive)}
  #vidCard .vt{font:900 64px/.92 'Big Shoulders Display',Archivo,system-ui;text-transform:uppercase;margin-top:16px}
  #vidCard .vt.brand{background:var(--vbrand);-webkit-background-clip:text;background-clip:text;color:transparent;font-size:58px}
  #vidCard .vs{font:600 16px/1.4 Manrope,system-ui;color:var(--vink2);margin-top:14px}
  #vidCard .vu{margin-top:24px;font:900 17px/1 'Big Shoulders Display',system-ui;letter-spacing:.22em;background:var(--vbrand);-webkit-background-clip:text;background-clip:text;color:transparent}
  #vidCard .sg{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px}
  #vidCard .si{border-radius:14px;padding:12px 12px 11px;background:var(--vglass);border:1px solid var(--vline);border-top:3px solid var(--tc,var(--vacc))}
  #vidCard .si b{display:block;white-space:nowrap;font:900 44px/1 'Big Shoulders Display',Archivo,system-ui;font-variant-numeric:tabular-nums}
  #vidCard .si span{display:block;margin-top:6px;font:800 10.5px/1.25 Manrope,system-ui;letter-spacing:.14em;text-transform:uppercase;color:var(--vink2)}
  #vidCard .bar{width:64px;height:5px;border-radius:3px;background:var(--tc,var(--vacc));margin-top:16px}`;
const LOGO='<svg viewBox="0 0 24 24"><path d="M1.6 9.6h3.6M.8 12h4.4M1.6 14.4h3.6" stroke="#fff" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/><path d="M7 12C9.7 7.3 19.3 7.3 22.4 12 19.3 16.7 9.7 16.7 7 12Z" fill="#fff"/><path d="M11.8 12h6.4M13.4 10.7v2.6M15 10.7v2.6M16.6 10.7v2.6" stroke="#1E5C78" stroke-width="1.2" stroke-linecap="round"/></svg>';
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---------- le journal de l'agent IA, tiré du GameFeed (ce que le moteur a vraiment décidé) ---------- */
const PRETTY=s=>String(s||'').replace(/_/g,' ').toLowerCase().replace(/\b(pa|rpo|qb|wr|te)\b/g,m=>m.toUpperCase());
const COV={'COVER_2':'Cover 2','COVER_3':'Cover 3','COVER_4':'Cover 4','MAN':'man','ZONE':'zone','BLITZ':'blitz','BOX_STACK':'stacked box'};
function hud(F,i,coaches){
  const P=F.plays[i], prev=i>0?F.plays[i-1]:null, G=F.game;
  const off=P.offense==='home'?G.home.abbr:G.away.abbr, dfn=P.offense==='home'?G.away.abbr:G.home.abbr;
  const c=P.call||{}, ty=c.type, dd=c.defense||{}, out=[];
  const coach=(coaches&&coaches[off])||{};
  const head={team:off, who:`${off} · AI OC${coach.offense?' '+coach.offense:''}`};
  const fd=P.fourth_down;
  if(fd&&fd.wp&&fd.choice){ const k=Object.keys(fd.wp); const pct=v=>Math.round(v*100);
    out.push(`4th & ${P.to_go}: ${k.map(x=>`${x} <b>${pct(fd.wp[x])}%</b>`).join(' vs ')} → <b>${String(fd.choice).toUpperCase()}</b>`); }
  const ps=P.presnap;
  if(ps&&ps.box_read!=null&&(ty==='run'||ty==='pass')) out.push(`reads <b>${ps.box_read} in the box</b>${ps.shell_shown?' · '+ps.shell_shown:''}${ps.audible?` → <b>audible ${ps.to&&ps.to.type==='run'?'RUN':'PASS'}</b>`:''}`);
  const sc=P.scout;
  const post=[];
  if(sc&&sc.def) out.push(`${dfn} AI keyed on the <b>${sc.def.key}</b> (${esc(sc.def.why||'')})`);
  if(sc&&sc.off&&sc.off.broke) out.push(`<b>breaks its tendency</b> — ${esc(sc.off.why||'')}`);
  if(ty==='run'||ty==='pass') out.push(`call: <b>${PRETTY(c.concept||c.play_id)}</b>${c.formation?' · '+PRETTY(c.formation):''} vs ${COV[dd.concept]||PRETTY(dd.concept)||'?'}`);
  else if(ty==='field_goal') out.push(`call: <b>field goal</b>`);
  else if(ty==='punt') out.push(`call: <b>punt</b>`);
  else if(ty==='kickoff') out.push(`kickoff`);
  const dk=P.decision;
  if(dk&&dk.coverage&&ty==='pass'){ const r=dk.reads?`read ${dk.read}/${dk.reads}`:'';
    post.push(`QB ${r} · ${dk.coverage}${dk.throw_time?` · throws in <b>${(+dk.throw_time).toFixed(1)}s</b>`:''}${dk.pressure?' · <b>pressured</b>':''}`); }
  const lines=out.slice(-(3-post.length)).map(t=>({t})).concat(post.map(t=>({t,post:true})));
  const side=P.offense, wb=prev&&prev.win_prob_home!=null?prev.win_prob_home:null, wa=P.win_prob_home!=null?P.win_prob_home:null;
  const wp=wb==null||wa==null?null:{team:off, avant:Math.round(100*(side==='home'?wb:1-wb)), apres:Math.round(100*(side==='home'?wa:1-wa))};
  const s0=prev&&prev.after&&prev.after.score?prev.after.score:{home:0,away:0};
  const s1=P.after&&P.after.score?P.after.score:s0;
  const bug={away:G.away.abbr, home:G.home.abbr, as:s0.away, hs:s0.home, as1:s1.away, hs1:s1.home, poss:P.offense};
  return {head,lines,wp,bug,off,dfn};
}
function frappe(P){                                         // le résultat frappé en grand, et son sous-titre
  const r=P.result, g=Math.round(+P.gain||0);
  if(P.conversion) return null;
  const T={touchdown:['Touchdown',''],interception:['Picked off',''],fumble_lost:['Fumble','turnover'],sack:['Sacked',`${g} yds`],
           field_goal_good:['It\'s good',''],field_goal_missed:['No good',''],safety:['Safety','2 points']}[r];
  if(T) return {t:T[0],s:T[1]};
  if((r==='run'||r==='complete')&&g>=20) return {t:`+${g}`,s:'big play'};
  if(/1st down/i.test(String(P.text||''))&&(P.down===3||P.down===4)) return {t:'Converted',s:`${P.down===3?'3rd':'4th'} & ${P.to_go}`};
  return null;
}

(async()=>{
  let F=JSON.parse(fs.readFileSync(plan.feed,'utf8')), feedOuvert=plan.feed;
  const dir=path.join(plan.out,'images'); fs.mkdirSync(dir,{recursive:true});
  const b=await chromium.launch({executablePath:EXE,args:['--force-device-scale-factor='+DPR]});   // dessin natif × 2,5 : images 1080×1920 sans mise à l'échelle
  const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:DPR,isMobile:true,hasTouch:true,colorScheme:'dark'});
  const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(()=>{ try{ localStorage.setItem('gc-theme','dark'); localStorage.setItem('gc-theater-v1','0'); }catch(e){} });
  await p.clock.install(); await p.clock.pauseAt(Date.now()+1000);   // le temps de la page n'avance que quand on le demande
  const attendre=ms=>p.clock.runFor(ms);
  await p.goto(plan.url);
  for(let k=0;!(await p.evaluate(()=>!!(window.__gc&&window.__gc.season)));k++){ if(k>600) throw new Error('le site ne démarre pas'); await attendre(100); }
  await p.evaluate(F=>{ window.__gc.openReplayFeed(F); const g=window.__gc.replayGame(); g.paused=true; },F);
  await p.evaluate(d=>window.__gc.fx(d,true),DPR);              // terrain net (× 2,5, halos), sans qualité adaptative
  await attendre(600);
  /* vue normale du grand écran (jamais « Bigger field » : il tourne le match sur un téléphone tenu droit) */
  const vueNormale=async()=>{ const th=await p.$('[data-theater][aria-pressed="true"]'); if(th) await th.click(); };
  await vueNormale();
  await p.addStyleTag({content:CSS});
  const top=plan.top||{};
  await p.evaluate(([t,esc,logo])=>{ const e=new Function('return '+esc)();
    /* l'identité du site : ses couleurs du thème sombre (lues dans la page), le dégradé de la marque */
    const C=getComputedStyle(document.documentElement), v=(n,f)=>(C.getPropertyValue(n)||'').trim()||f, R=document.documentElement.style;
    R.setProperty('--vbg','#060A13'); R.setProperty('--vink',v('--ink','#EEF1FF')); R.setProperty('--vink2','rgba(226,232,246,.72)');
    R.setProperty('--vacc',v('--cyan','#2EE6FF')); R.setProperty('--vlive','#FF3B30');
    R.setProperty('--vglow','rgba(38,110,140,.55)'); R.setProperty('--vglow2','rgba(122,92,255,.28)');
    R.setProperty('--vglass','rgba(16,24,40,.72)'); R.setProperty('--vglass2','rgba(10,16,30,.86)'); R.setProperty('--vline','rgba(255,255,255,.14)');
    R.setProperty('--vbrand','linear-gradient(90deg,#2EE6FF 0%,#7A5CFF 55%,#FF3D9A 100%)');
    for(const id of ['vidTop','vidBug','vidHud','vidFlash','vidStamp','vidCard']){ const d=document.createElement('div'); d.id=id; d.className='vid'; document.body.appendChild(d); }
    document.getElementById('vidStamp').innerHTML='<div></div>';
    window.__vidLogo=logo;
    /* animations sur l'horloge pilotée : chaque image avance de 1/60 s, le rendu est identique d'un tournage à l'autre */
    const A=[]; window.__vidAnim=(dur,f)=>{ A.push({t0:performance.now(),dur,f}); };
    const tick=()=>{ const now=performance.now(); for(let i=A.length-1;i>=0;i--){ const a=A[i], q=Math.min(1,(now-a.t0)/a.dur); a.f(q); if(q>=1) A.splice(i,1); } requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    const ease=q=>1-Math.pow(1-q,3), back=q=>{ const c=1.7; return 1+(c+1)*Math.pow(q-1,3)+c*Math.pow(q-1,2); };
    window.__vidTop=(t,pop)=>{ const el=document.getElementById('vidTop');
      el.innerHTML=`<div class="vk"><i></i>${e(t.kicker)}</div><div class="vt">${String(t.title||'').split(' ').map(w=>`<span>${e(w)}</span>`).join(' ')}</div><div class="vs">${e(t.sub)}</div>`;
      const vt=el.querySelector('.vt'); for(let f=38;f>22&&vt.scrollWidth>vt.clientWidth;f-=2) vt.style.fontSize=f+'px';   /* le titre tient sur une ligne */
      if(pop){ const ws=[...vt.querySelectorAll('span')]; ws.forEach((s,k)=>{ s.style.opacity=0; s.style.transform='translateY(8px) scale(.6)';
        setTimeout(()=>window.__vidAnim(260,q=>{ s.style.opacity=Math.min(1,q*2); s.style.transform=`translateY(${8*(1-ease(q))}px) scale(${.6+.4*back(q)})`; }),70*k); }); } };
    window.__vidTop(t,true); },[top,esc.toString(),LOGO]);
  const resserrer=()=>p.evaluate(v=>{ const m=window.__gc.getModalView(); if(m){ m.viewW=v; m.resize(); } window.dispatchEvent(new Event('resize')); },VIEW_YARDS);
  await resserrer(); await attendre(800);
  /* les polices chargées avant toute mesure (sinon le journal se mesure avec la police de secours, plus étroite) */
  await p.evaluate(()=>Promise.all(["600 12.5px 'Azeret Mono'","900 44px 'Big Shoulders Display'","800 10px Manrope"].map(f=>document.fonts.load(f))).then(()=>document.fonts.ready));
  const verifier=async()=>{ const v=await p.evaluate(()=>{ const m=document.getElementById('modal'), f=m.querySelector('.field.big'), r=f&&f.getBoundingClientRect();
      return {theater:m.classList.contains('theater'), tr:getComputedStyle(m.querySelector('.m-panel')).transform, w:r&&r.width, h:r&&r.height, top:r&&r.top}; });
    if(v.theater||(v.tr&&v.tr!=='none')||!v.w||v.w<v.h||Math.abs(v.top-FT)>2) throw new Error('terrain mal placé ou tourné : '+JSON.stringify(v)); };
  await verifier();
  const ouvrir=async(chemin,i)=>{                                // une action d'un autre match (« What is Snapline? »)
    F=JSON.parse(fs.readFileSync(chemin,'utf8')); feedOuvert=chemin;
    await p.evaluate(([F,i])=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); G.rpSeek(g,i); g.paused=true; },[F,i]);
    await vueNormale(); await resserrer(); await attendre(1500); await verifier(); };

  /* le bandeau de score, le journal de l'IA et sa probabilité de victoire, pour une action */
  const montrerHud=(h,lent,label)=>p.evaluate(([h,lent,label,W])=>{ const C=getComputedStyle(document.documentElement), tc=a=>(C.getPropertyValue('--t-'+a.toLowerCase())||'').trim()||'#2EE6FF';
    const bug=document.getElementById('vidBug'), B=h.bug;
    bug.innerHTML=`<div class="t" style="--tc:${tc(B.away)}"><em>${B.away}</em><b>${B.as}</b></div><div class="t" style="--tc:${tc(B.home)}"><em>${B.home}</em><b>${B.hs}</b></div><div class="c">${label||''}</div>`;
    const hud=document.getElementById('vidHud'); hud.style.setProperty('--tc',tc(h.off));
    const wp=h.wp?`<div class="vh-w"><span>${h.off} win prob</span><div class="vh-b"><i style="width:${h.wp.avant}%"></i></div><b>${h.wp.avant}%</b></div>`:'';
    hud.innerHTML=`<div class="vh-h"><span class="vh-ai">AI</span><span class="vh-who">${lent?'Replay · ':''}${h.head.who}</span><span class="vh-mk"><i>${window.__vidLogo}</i>snapline.live</span></div>`+
      h.lines.map(()=>'<div class="vh-l"></div>').join('')+wp;
    /* les lignes se tapent l'une après l'autre (≈ 55 caractères / s, 90 après le snap ; au ralenti, déjà écrites) ; celles d'après le
       snap (la lecture du QB) attendent le snap (window.__vidHudPost) */
    const els=[...hud.querySelectorAll('.vh-l')];
    /* chaque ligne tient sur une ligne : la police rétrécit (jusqu'à 9 px) plutôt que de couper le texte */
    /* (mesuré au canevas : le panneau peut être encore caché à cet instant) */
    const cv=(window.__vidCv=window.__vidCv||document.createElement('canvas')).getContext('2d'), large=W-72-26;
    const ajuster=(el,txt)=>{ const plain='› '+txt.replace(/<[^>]+>/g,'');
      for(let f=12.5;f>=9;f-=.5){ cv.font=`600 ${f}px 'Azeret Mono'`; el.style.fontSize=f+'px'; if(cv.measureText(plain).width<=large) break; } };
    h.lines.forEach((L,k)=>ajuster(els[k],L.t));
    const taper=(L,k,delai)=>{ const el=els[k], txt=L.t, plain=txt.replace(/<[^>]+>/g,'');
      setTimeout(()=>window.__vidAnim(Math.max(200,plain.length*(L.post?11:18)),q=>{ const n=Math.round(plain.length*q);
        let out='', c=0, i=0; while(i<txt.length&&c<n){ if(txt[i]==='<'){ const j=txt.indexOf('>',i); out+=txt.slice(i,j+1); i=j+1; continue; } out+=txt[i]; i++; c++; }
        if(q<1&&!/<\/b>$/.test(out)&&(out.match(/<b>/g)||[]).length>(out.match(/<\/b>/g)||[]).length) out+='</b>';
        el.innerHTML='› '+out+(q<1?'<span class="vh-c"></span>':''); }),delai); };
    let k0=0;
    h.lines.forEach((L,k)=>{ if(lent){ els[k].innerHTML='› '+L.t; return; } if(!L.post) taper(L,k,(k0++)*380+120); });
    window.__vidHudPost=()=>{ if(lent) return; let j=0; h.lines.forEach((L,k)=>{ if(L.post) taper(L,k,(j++)*300); }); window.__vidHudPost=()=>{}; };
  },[h,lent,label,W]);
  /* le résultat : la probabilité bascule, le mot est frappé en grand, la caméra donne un coup de zoom */
  const resultat=(h,fr,lent)=>p.evaluate(([h,fr,lent])=>{ const C=getComputedStyle(document.documentElement), tc=a=>(C.getPropertyValue('--t-'+a.toLowerCase())||'').trim()||'#2EE6FF';
    const ease=q=>1-Math.pow(1-q,3);
    if(h.wp){ const i=document.querySelector('#vidHud .vh-w .vh-b i'), bb=document.querySelector('#vidHud .vh-w b'), a=h.wp.avant, z=h.wp.apres;
      if(i) window.__vidAnim(lent?1100:700,q=>{ const v=Math.round(a+(z-a)*ease(q)); i.style.width=v+'%'; bb.textContent=q<1?v+'%':`${a}% → ${z}%`; }); }
    /* le score bug change au résultat (le chiffre qui a bougé saute) */
    const bs=document.querySelectorAll('#vidBug .t b');
    [[0,h.bug.as1],[1,h.bug.hs1]].forEach(([k,v])=>{ const b=bs[k]; if(!b||v==null||String(v)===b.textContent) return;
      b.textContent=v; window.__vidAnim(600,q=>{ b.style.display='inline-block'; b.style.transform=`scale(${1+.6*Math.sin(Math.PI*q)*(1-q*.3)})`; b.style.color=q<1?'var(--cyan)':''; }); });
    if(!fr) return;
    const st=document.getElementById('vidStamp'), d=st.firstElementChild, fl=document.getElementById('vidFlash'), fld=document.querySelector('#modal .field.big');
    st.style.setProperty('--tc',tc(h.off)); fl.style.setProperty('--tc',tc(h.off));
    d.innerHTML=`<span>${fr.t}</span>${fr.s?`<small>${fr.s}</small>`:''}`; d.style.fontSize='66px';
    const sp=d.firstElementChild; for(let f=66;f>30&&sp.offsetWidth>d.clientWidth-24;f-=3) d.style.fontSize=f+'px';
    window.__vidAnim(lent?1600:1200,q=>{ const k=q<.18?q/.18:1; d.style.opacity=q<.82?Math.min(1,k):Math.max(0,(1-q)/.18);
      d.style.transform=`scale(${q<.18?1.6-.6*ease(k):1+.04*q}) rotate(-3deg)`; });
    window.__vidAnim(380,q=>{ fl.style.opacity=.32*(1-q); });
    if(fld) window.__vidAnim(520,q=>{ const s=1+.07*Math.sin(Math.PI*q), j=(1-q)*3; fld.style.transform=`scale(${s}) translate(${Math.sin(q*40)*j}px,${Math.cos(q*33)*j}px)`; if(q>=1) fld.style.transform=''; });
  },[h,fr,lent]);

  const carton=s=>p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), c=document.getElementById('vidCard');
    const brand=s.title==='snapline.live';
    c.innerHTML=`<div class="vk"><i></i>${e(s.kicker)}</div><div class="vt${brand?' brand':''}">${e(s.title)}</div><div class="vs">${e(s.sub)}</div>${brand?'':'<div class="vu">SNAPLINE.LIVE</div>'}`; c.style.display='flex';
    /* le titre (un score, un nom) tient sur une ligne si possible : la police rétrécit, sinon il passe à la ligne */
    const vt=c.querySelector('.vt'); vt.style.whiteSpace='nowrap';
    for(let f=brand?58:64;f>30&&vt.scrollWidth>vt.clientWidth;f-=2) vt.style.fontSize=f+'px';
    if(vt.scrollWidth>vt.clientWidth) vt.style.whiteSpace=''; },[s,esc.toString()]);
  const statsCarton=s=>p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), c=document.getElementById('vidCard');
    const tc=s.team?getComputedStyle(document.documentElement).getPropertyValue('--t-'+s.team.toLowerCase()).trim():'';
    c.style.setProperty('--tc',tc||'');
    c.innerHTML=`<div class="vk"><i></i>${e(s.kicker)}</div><div class="vt">${e(s.title)}</div><div class="vs">${e(s.sub)}</div><div class="bar"></div>`+
      `<div class="sg">${(s.stats||[]).map(x=>`<div class="si"><b ${typeof x.v==='number'?`data-v="${x.v}">0`:`>${e(x.v)}`}</b><span>${e(x.l)}</span></div>`).join('')}</div>`+
      '<div class="vu">SNAPLINE.LIVE</div>';
    c.style.display='flex';
    const vt=c.querySelector('.vt'); for(let f=64;f>30&&vt.scrollWidth>vt.clientWidth;f-=2) vt.style.fontSize=f+'px';
    for(const b of c.querySelectorAll('.si b:not([data-v])')) for(let f=44;f>24&&b.scrollWidth>b.clientWidth;f-=2) b.style.fontSize=f+'px';
    const els=[...c.querySelectorAll('b[data-v]')];          /* horloge pilotée : même rendu à chaque fois */
    window.__vidAnim(800,q=>{ const k=1-Math.pow(1-q,3); for(const b of els) b.textContent=Math.round(+b.dataset.v*k).toLocaleString('en-US'); }); },[s,esc.toString()]);
  if(plan.segments.length&&plan.segments[0].feed&&plan.segments[0].feed!==feedOuvert) await ouvrir(plan.segments[0].feed,plan.segments[0].index);
  else if(plan.segments.length&&plan.segments[0].type==='play'){ await p.evaluate(i=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,i); g.paused=true; },plan.segments[0].index);
    await attendre(1500); }   // la 1re image (couverture) montre déjà l'action : la caméra a rejoint le ballon

  /* capture : une image toutes les 1/60 s de temps de la page ; le temps de la vidéo = images × durée */
  const cdp=await ctx.newCDPSession(p), liste=[]; let n=0, t=0, derniere=null, attente=null, vides=0;
  cdp.on('Page.screencastFrame',f=>{ cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{});
    if(attente&&f.metadata.timestamp>=attente.depuis){ const w=attente; attente=null; w.ok(f.data); } else derniere=derniere||f.data; });
  await cdp.send('Page.startScreencast',{format:'jpeg',quality:JPEG,maxWidth:W*DPR,maxHeight:H*DPR,everyNthFrame:1});
  const image=async dur=>{
    const data=await new Promise(ok=>{ const w={depuis:Date.now()/1000,ok}; attente=w;
      setTimeout(()=>{ if(attente===w){ attente=null; vides++; ok(null); } },400); });
    if(data) derniere=data;
    if(!derniere){ const r=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:JPEG}); derniere=r.data; }
    const file=String(++n).padStart(6,'0')+'.jpg'; fs.writeFileSync(path.join(dir,file),Buffer.from(derniere,'base64'));
    liste.push({file,dur}); t+=dur; };
  const pas=async()=>{ await attendre(DT); await image(1/FPS); };
  const now=()=>t;
  const timeline={segments:[]}, debut=Date.now();
  for(const s of plan.segments){
    if(s.type==='stats'){                                    // les chiffres montent (≈ 0,9 s d'images), puis une image fixe
      const a=now();
      await statsCarton(s);
      for(let k=0;k<Math.round(0.9*FPS);k++) await pas();
      await attendre(DT); await image(Math.max(1/FPS,(s.dur||3)-(now()-a)));
      await p.evaluate(()=>{ const c=document.getElementById('vidCard'); c.style.display='none'; c.style.removeProperty('--tc'); });
      timeline.segments.push({type:'card',kind:'stats',from:a,to:now()});
      continue;
    }
    if(s.type==='card'){                                     // un carton : son entrée (0,4 s d'images), puis une image fixe
      const a=now();
      await carton(s);
      await p.evaluate(()=>{ const c=document.getElementById('vidCard'), kids=[...c.children];
        kids.forEach((k,i)=>{ k.style.opacity=0; setTimeout(()=>window.__vidAnim(300,q=>{ k.style.opacity=q; k.style.transform=`translateY(${(1-q)*14}px)`; }),i*60); }); });
      for(let k=0;k<Math.round(0.45*FPS);k++) await pas();
      await attendre(DT); await image(Math.max(1/FPS,s.dur-(now()-a)));
      await p.evaluate(()=>{ document.getElementById('vidCard').style.display='none'; });
      timeline.segments.push({type:'card',kind:s.kind||'card',from:a,to:now()});
      continue;
    }
    if(s.feed&&s.feed!==feedOuvert) await ouvrir(s.feed,s.index);
    const h=hud(F,s.index,plan.coaches), fr=frappe(F.plays[s.index]), lent=(s.speed||1)<1;
    await p.evaluate(([s])=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,s.index); g.speed=s.speed||1; g.paused=false;
      if(s.top) window.__vidTop(s.top,true); },[s]);
    if(lent) for(let k=0;k<600;k++){                          // ralenti : il reprend au snap, sans images de l'avant-snap
      if(await p.evaluate(i=>{ const g=window.__gc.replayGame(); return g.idx!==i||g.phase!=='presnap'; },s.index)) break;
      await attendre(50); }
    await montrerHud(h,lent,s.label);
    const a=now(); let snap=null, res=null;
    for(let k=0;k<50*FPS;k++){                                // au plus 50 s par action
      await pas();
      const st=await p.evaluate(()=>{ const g=window.__gc.replayGame(); return {idx:g.idx,phase:g.phase}; });
      if(snap===null&&st.idx===s.index&&st.phase!=='presnap'){ snap=now(); await p.evaluate(()=>window.__vidHudPost&&window.__vidHudPost()); }
      if(res===null&&((st.idx===s.index&&st.phase==='post')||st.idx>s.index)){ res=now(); await resultat(h,fr,lent); }
      if(st.idx>s.index||st.phase==='done'||(res!==null&&now()-res>=(s.after==null?2.2:s.after))) break;
    }
    await p.evaluate(()=>{ window.__gc.replayGame().paused=true; });
    const P=F.plays[s.index];
    timeline.segments.push({type:'play',index:s.index,result:P.result,call:(P.call||{}).type,highlight:P.highlight||null,
      td:P.result==='touchdown'||!!(P.kick_return||{}).td,stamp:!!fr,from:a,snap:snap===null?a:snap,res:res===null?now():res,to:now(),speed:s.speed||1});
  }
  await cdp.send('Page.stopScreencast').catch(()=>{});
  await ctx.close(); await b.close();
  if(!liste.length) throw new Error('aucune image capturée');
  let txt='ffconcat version 1.0\n';
  for(const f of liste) txt+=`file '${f.file}'\nduration ${f.dur.toFixed(6)}\n`;
  txt+=`file '${liste[liste.length-1].file}'\n`;
  fs.writeFileSync(path.join(dir,'images.txt'),txt);
  for(const s of timeline.segments) for(const k of ['from','to','snap','res']) if(s[k]!=null) s[k]=+s[k].toFixed(3);
  timeline.end=+t.toFixed(3); timeline.frames=liste.length;
  fs.writeFileSync(path.join(plan.out,'timeline.json'),JSON.stringify(timeline,null,1));
  if(errs.length){ console.error('erreurs JS :',errs); process.exit(1); }
  console.log(`filmé : ${timeline.end.toFixed(1)} s, ${liste.length} images, ${timeline.segments.length} segments · tournage ${((Date.now()-debut)/1000).toFixed(0)} s` +
    (vides?` · ${vides} images reprises (écran inchangé)`:''));
})().catch(e=>{ console.error(e); process.exit(1); });
