// Vidéos verticales (bloc 2, étape 8) : filme le terrain du site en 1080×1920 (Playwright + serveur réel, crochet de
// test). Appelé par outils/video/faire_video.py :   node outils/video/filmer.js plan.json
// plan = {url, feed (chemin du GameFeed), out (dossier), top: {kicker, title, sub},
//         segments: [{type:"card", kicker, title, sub, dur} | {type:"play", index, speed, label, text, after, top?}]}
// (top d'une action : remplace le bandeau du haut à partir de cette action ; feed : l'action vient d'un autre match.)
// Tournage image par image (étape 8.3) : l'horloge de la page est pilotée (page.clock), elle avance de 1/60 s entre deux
// images en pleine résolution (1080×1920 : mise en page « téléphone » 432×768 × 2,5, terrain dessiné à × 2,5) ; la
// vidéo ne dépend donc ni de la vitesse de la machine ni de la qualité adaptative du site (qui baissait la résolution du
// terrain en temps réel). Écrit out/images/*.jpg, out/images.txt (liste ffmpeg « concat » : image + durée) et
// out/timeline.json (instants du snap et du résultat de chaque action, en secondes de vidéo : le son du stade s'y cale).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const plan=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const W=432, H=768, DPR=2.5;                       // 1080 × 1920 : la mise en page « téléphone » du site, nette
/* Zones sûres (étape 8.2) : l'interface de TikTok / Reels / Shorts couvre ≈ 215 px en haut (onglets), ≈ 400 px en bas
   (légende, nom du son) et ≈ 140 px à droite (boutons) sur 1920 × 1080 → ici 86, 160 et 56 px. L'enjeu est entre 86 et
   200, le terrain entre 200 et 630 (resserré : 46 yards de large au lieu de 70), le texte de l'action en bas du terrain. */
const VIEW_YARDS=46, FPS=60, DT=1000/FPS, JPEG=93;   // 60 images/s (choix du 13/10)

const CSS=`
  html,body{background:#0B0E1A!important}
  #modal{background:#0B0E1A!important}
  #modal .m-head,#modal .m-side,#modal .m-lower,#modal .m-main>*:not(.field),.toast,.fab,.ticker{display:none!important}
  #modal .m-panel{background:transparent!important;border:0!important;box-shadow:none!important}
  #modal .field.big{position:fixed!important;left:0!important;right:0!important;top:200px!important;height:430px!important;width:${W}px!important;
    margin:0!important;border-radius:0!important;z-index:9000}
  #modal .field.big>.pill,#modal .field.big .bug{display:none!important}
  .vid{position:fixed;left:0;width:${W}px;box-sizing:border-box;z-index:9999;color:#fff;pointer-events:none;font-family:Archivo,system-ui,sans-serif}
  #vidTop{top:0;height:200px;padding:86px 60px 0 22px;background:#0B0E1A}
  #vidTop .vk{font:800 12px/1 Archivo,system-ui;letter-spacing:.24em;color:#2EE6FF;text-transform:uppercase}
  #vidTop .vt{font:900 40px/1 'Big Shoulders Display',Archivo,system-ui;text-transform:uppercase;margin-top:8px;white-space:nowrap}
  #vidTop .vs{font:600 14px/1.3 Archivo,system-ui;color:#C9D3E6;margin-top:6px}
  #vidBot{top:556px;height:74px;padding:14px 60px 0 22px;background:linear-gradient(180deg,rgba(11,14,26,0),rgba(11,14,26,.9) 38%)}
  #vidFoot{top:630px;bottom:0;padding:16px 22px 0;background:#0B0E1A}
  #vidBot .vl{font:800 12px/1 Archivo,system-ui;letter-spacing:.2em;color:#2EE6FF;text-transform:uppercase}
  #vidBot .vx{font:800 19px/1.2 Archivo,system-ui;margin-top:8px}
  #vidFoot .vu{font:800 12px/1 Archivo,system-ui;letter-spacing:.22em;opacity:.8}
  #vidCard{top:0;height:${H}px;display:none;flex-direction:column;justify-content:center;padding:0 60px 0 30px;background:radial-gradient(120% 80% at 20% 0%,#2A4E74,#0B0E1A 70%)}
  #vidCard .vk{font:800 14px/1 Archivo,system-ui;letter-spacing:.26em;color:#2EE6FF;text-transform:uppercase}
  #vidCard .vt{font:900 60px/.95 'Big Shoulders Display',Archivo,system-ui;text-transform:uppercase;margin-top:14px}
  #vidCard .vs{font:600 17px/1.4 Archivo,system-ui;color:#C9D3E6;margin-top:16px}
  #vidCard .vu{margin-top:26px;font:800 15px/1 Archivo,system-ui;letter-spacing:.22em}
  /* étape 8.4 bis : l'adresse toujours visible (le bas de l'écran est sous la légende de TikTok) — badge au-dessus du
     texte de l'action, à gauche (le haut du terrain porte les étiquettes du site, la droite les boutons du réseau) */
  #vidMark{top:520px;left:16px;width:auto;display:flex;align-items:center;gap:7px;padding:4px 11px 4px 4px;border-radius:999px;
    background:rgba(11,14,26,.78);font:800 13px/1 Archivo,system-ui;letter-spacing:.06em}
  #vidMark i{width:22px;height:22px;border-radius:7px;background:linear-gradient(135deg,#2EE6FF,#7A5CFF 55%,#FF3D9A);display:grid;place-items:center}
  #vidMark svg{width:16px;height:16px}`;
const LOGO='<svg viewBox="0 0 24 24"><path d="M1.6 9.6h3.6M.8 12h4.4M1.6 14.4h3.6" stroke="#fff" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/><path d="M7 12C9.7 7.3 19.3 7.3 22.4 12 19.3 16.7 9.7 16.7 7 12Z" fill="#fff"/><path d="M11.8 12h6.4M13.4 10.7v2.6M15 10.7v2.6M16.6 10.7v2.6" stroke="#1E5C78" stroke-width="1.2" stroke-linecap="round"/></svg>';
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

(async()=>{
  let F=JSON.parse(fs.readFileSync(plan.feed,'utf8')), feedOuvert=plan.feed;
  const dir=path.join(plan.out,'images'); fs.mkdirSync(dir,{recursive:true});
  const b=await chromium.launch({executablePath:EXE,args:['--force-device-scale-factor='+DPR]});   // dessin natif × 2,5 : images 1080×1920 sans mise à l'échelle
  const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:DPR,isMobile:true,hasTouch:true});
  const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(()=>{ try{ localStorage.setItem('gc-theme','light'); }catch(e){} });
  await p.clock.install(); await p.clock.pauseAt(Date.now()+1000);   // le temps de la page n'avance que quand on le demande
  const attendre=ms=>p.clock.runFor(ms);
  await p.goto(plan.url);
  for(let k=0;!(await p.evaluate(()=>!!(window.__gc&&window.__gc.season)));k++){ if(k>600) throw new Error('le site ne démarre pas'); await attendre(100); }
  await p.evaluate(F=>{ window.__gc.openReplayFeed(F); const g=window.__gc.replayGame(); g.paused=true; },F);
  await p.evaluate(d=>window.__gc.fx(d,true),DPR);              // terrain net (× 2,5, halos), sans qualité adaptative
  await attendre(600);
  const th=await p.$('[data-theater][aria-pressed="false"]'); if(th) await th.click();
  await p.addStyleTag({content:CSS});
  const top=plan.top||{};
  await p.evaluate(([t,esc,logo])=>{ const e=new Function('return '+esc)();
    for(const id of ['vidTop','vidBot','vidFoot','vidMark','vidCard']){ const d=document.createElement('div'); d.id=id; d.className='vid'; document.body.appendChild(d); }
    document.getElementById('vidFoot').innerHTML='<div class="vu">SNAPLINE.LIVE</div>';
    document.getElementById('vidMark').innerHTML='<i>'+logo+'</i>snapline.live';
    window.__vidTop=t=>{ document.getElementById('vidTop').innerHTML=`<div class="vk">${e(t.kicker)}</div><div class="vt">${e(t.title)}</div><div class="vs">${e(t.sub)}</div>`;
      const vt=document.querySelector('#vidTop .vt'); for(let f=40;f>24&&vt.scrollWidth>vt.clientWidth;f-=2) vt.style.fontSize=f+'px'; };   /* le titre tient sur une ligne */
    window.__vidTop(t); },[top,esc.toString(),LOGO]);
  const resserrer=()=>p.evaluate(v=>{ const m=window.__gc.getModalView(); if(m){ m.viewW=v; m.resize(); } window.dispatchEvent(new Event('resize')); },VIEW_YARDS);
  await resserrer(); await attendre(800);
  const ouvrir=async(chemin,i)=>{                                // une action d'un autre match (« What is Snapline? »)
    F=JSON.parse(fs.readFileSync(chemin,'utf8')); feedOuvert=chemin;
    await p.evaluate(([F,i])=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); G.rpSeek(g,i); g.paused=true; },[F,i]);
    const th=await p.$('[data-theater][aria-pressed="false"]'); if(th) await th.click();
    await resserrer(); await attendre(1500); };

  const carton=s=>p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), c=document.getElementById('vidCard');
    c.innerHTML=`<div class="vk">${e(s.kicker)}</div><div class="vt">${e(s.title)}</div><div class="vs">${e(s.sub)}</div>${s.title==='snapline.live'?'':'<div class="vu">SNAPLINE.LIVE</div>'}`; c.style.display='flex'; },[s,esc.toString()]);
  if(plan.segments.length&&plan.segments[0].feed&&plan.segments[0].feed!==feedOuvert) await ouvrir(plan.segments[0].feed,plan.segments[0].index);
  else if(plan.segments.length&&plan.segments[0].type!=='card'){ await p.evaluate(i=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,i); g.paused=true; },plan.segments[0].index);
    await attendre(1500); }   // la 1re image (couverture) montre déjà l'action : la caméra a rejoint le ballon

  /* capture : une image toutes les 1/60 s de temps de la page ; le temps de la vidéo = images × durée */
  /* les images viennent du « screencast » du navigateur (rapide, à la résolution native) : après chaque pas d'horloge, on
     garde la première image produite après ce pas ; si rien n'a changé à l'écran (pas de nouvelle image), la précédente */
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
    if(s.type==='card'){                                     // un carton est fixe : une seule image, qui dure s.dur
      const a=now();
      await carton(s); await attendre(DT); await image(s.dur);
      await p.evaluate(()=>{ document.getElementById('vidCard').style.display='none'; });
      timeline.segments.push({type:'card',kind:s.kind||'card',from:a,to:now()});
      continue;
    }
    if(s.feed&&s.feed!==feedOuvert) await ouvrir(s.feed,s.index);
    await p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), G=window.__gc, g=G.replayGame(); G.rpSeek(g,s.index); g.speed=s.speed||1; g.paused=false;
      if(s.top) window.__vidTop(s.top);
      document.getElementById('vidBot').innerHTML=`<div class="vl">${e(s.label)}</div><div class="vx">${e(s.text)}</div>`; },[s,esc.toString()]);
    const a=now(); let snap=null, res=null;
    for(let k=0;k<50*FPS;k++){                                // au plus 50 s par action
      await pas();
      const st=await p.evaluate(()=>{ const g=window.__gc.replayGame(); return {idx:g.idx,phase:g.phase}; });
      if(snap===null&&st.idx===s.index&&st.phase!=='presnap') snap=now();
      if(res===null&&((st.idx===s.index&&st.phase==='post')||st.idx>s.index)) res=now();
      if(st.idx>s.index||st.phase==='done'||(res!==null&&now()-res>=(s.after==null?2.2:s.after))) break;
    }
    await p.evaluate(()=>{ window.__gc.replayGame().paused=true; });
    const P=F.plays[s.index];
    timeline.segments.push({type:'play',index:s.index,result:P.result,call:(P.call||{}).type,highlight:P.highlight||null,
      td:P.result==='touchdown'||!!(P.kick_return||{}).td,from:a,snap:snap===null?a:snap,res:res===null?now():res,to:now(),speed:s.speed||1});
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
