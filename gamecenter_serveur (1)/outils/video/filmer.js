// Vidéos verticales (bloc 2, étape 8) : filme le terrain du site en 1080×1920 (Playwright + serveur réel, crochet de
// test). Appelé par outils/video/faire_video.py :   node outils/video/filmer.js plan.json
// plan = {url, feed (chemin du GameFeed), out (dossier), top: {kicker, title, sub},
//         segments: [{type:"card", kicker, title, sub, dur} | {type:"play", index, speed, label, text, after, top?}]}
// (top d'une action : remplace le bandeau du haut à partir de cette action.)
// Les images viennent du navigateur lui-même (Page.startScreencast, à la résolution de l'écran : 432×768 × 2,5), avec
// leur instant. Écrit out/images/*.jpg, out/images.txt (liste ffmpeg « concat » : image + durée) et out/timeline.json
// (instants du snap et du résultat de chaque action, en secondes depuis la première image : le son du stade s'y cale).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const plan=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const W=432, H=768, DPR=2.5;                       // 1080 × 1920 : la mise en page « téléphone » du site, nette
/* Zones sûres (étape 8.2) : l'interface de TikTok / Reels / Shorts couvre ≈ 215 px en haut (onglets), ≈ 400 px en bas
   (légende, nom du son) et ≈ 140 px à droite (boutons) sur 1920 × 1080 → ici 86, 160 et 56 px. L'enjeu est entre 86 et
   200, le terrain entre 200 et 630 (resserré : 46 yards de large au lieu de 70), le texte de l'action en bas du terrain. */
const VIEW_YARDS=46;

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
  #vidCard .vu{position:absolute;bottom:40px;left:30px;font:800 15px/1 Archivo,system-ui;letter-spacing:.22em}`;
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

(async()=>{
  const F=JSON.parse(fs.readFileSync(plan.feed,'utf8'));
  const dir=path.join(plan.out,'images'); fs.mkdirSync(dir,{recursive:true});
  const b=await chromium.launch({executablePath:EXE});
  const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:DPR,isMobile:true,hasTouch:true});
  const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.addInitScript(()=>{ try{ localStorage.setItem('gc-theme','light'); }catch(e){} });
  await p.goto(plan.url); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
  await p.evaluate(F=>{ window.__gc.openReplayFeed(F); const g=window.__gc.replayGame(); g.paused=true; },F);
  await p.waitForTimeout(600);
  const th=await p.$('[data-theater][aria-pressed="false"]'); if(th) await th.click();
  await p.addStyleTag({content:CSS});
  const top=plan.top||{};
  await p.evaluate(([t,esc])=>{ const e=new Function('return '+esc)();
    for(const id of ['vidTop','vidBot','vidFoot','vidCard']){ const d=document.createElement('div'); d.id=id; d.className='vid'; document.body.appendChild(d); }
    document.getElementById('vidFoot').innerHTML='<div class="vu">SNAPLINE.LIVE</div>';
    window.__vidTop=t=>{ document.getElementById('vidTop').innerHTML=`<div class="vk">${e(t.kicker)}</div><div class="vt">${e(t.title)}</div><div class="vs">${e(t.sub)}</div>`;
      const vt=document.querySelector('#vidTop .vt'); for(let f=40;f>24&&vt.scrollWidth>vt.clientWidth;f-=2) vt.style.fontSize=f+'px'; };   /* le titre tient sur une ligne */
    window.__vidTop(t); },[top,esc.toString()]);
  await p.evaluate(v=>{ const m=window.__gc.getModalView(); if(m){ m.viewW=v; m.resize(); } window.dispatchEvent(new Event('resize')); },VIEW_YARDS); await p.waitForTimeout(800);

  const carton=s=>p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), c=document.getElementById('vidCard');
    c.innerHTML=`<div class="vk">${e(s.kicker)}</div><div class="vt">${e(s.title)}</div><div class="vs">${e(s.sub)}</div><div class="vu">SNAPLINE.LIVE</div>`; c.style.display='flex'; },[s,esc.toString()]);
  if(plan.segments.length&&plan.segments[0].type==='card'){ await carton(plan.segments[0]); await p.waitForTimeout(200); }   // la 1re image est déjà le carton
  else if(plan.segments.length){ await p.evaluate(i=>{ const G=window.__gc, g=G.replayGame(); G.rpSeek(g,i); g.paused=true; },plan.segments[0].index);
    await p.waitForTimeout(1500); }   // la 1re image (couverture) montre déjà l'action : la caméra a rejoint le ballon

  /* capture : chaque image envoyée par le navigateur, avec son instant (horloge de la machine) */
  const cdp=await ctx.newCDPSession(p), frames=[]; let n=0;
  cdp.on('Page.screencastFrame',async f=>{ const file=path.join(dir,String(++n).padStart(6,'0')+'.jpg');
    fs.writeFileSync(file,Buffer.from(f.data,'base64')); frames.push({file,t:Date.now()/1000});
    try{ await cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}); }catch(e){} });
  const t0=Date.now()/1000, now=()=>Date.now()/1000-t0;
  await cdp.send('Page.startScreencast',{format:'jpeg',quality:88,maxWidth:W*DPR,maxHeight:H*DPR,everyNthFrame:1});
  const timeline={segments:[]};
  for(const s of plan.segments){
    if(s.type==='card'){
      const a=now();
      await carton(s);
      await p.waitForTimeout(s.dur*1000);
      await p.evaluate(()=>{ document.getElementById('vidCard').style.display='none'; });
      timeline.segments.push({type:'card',kind:s.kind||'card',from:a,to:now()});
      continue;
    }
    await p.evaluate(([s,esc])=>{ const e=new Function('return '+esc)(), G=window.__gc, g=G.replayGame(); G.rpSeek(g,s.index); g.speed=s.speed||1; g.paused=false;
      if(s.top) window.__vidTop(s.top);
      document.getElementById('vidBot').innerHTML=`<div class="vl">${e(s.label)}</div><div class="vx">${e(s.text)}</div>`; },[s,esc.toString()]);
    const a=now(); let snap=null, res=null;
    for(let k=0;k<500;k++){                                   // au plus 50 s par action
      const st=await p.evaluate(()=>{ const g=window.__gc.replayGame(); return {idx:g.idx,phase:g.phase}; });
      if(snap===null&&st.idx===s.index&&st.phase!=='presnap') snap=now();
      if(res===null&&((st.idx===s.index&&st.phase==='post')||st.idx>s.index)) res=now();
      if(st.idx>s.index||st.phase==='done'||(res!==null&&now()-res>=(s.after==null?2.2:s.after))) break;
      await p.waitForTimeout(80);
    }
    await p.evaluate(()=>{ window.__gc.replayGame().paused=true; });
    const P=F.plays[s.index];
    timeline.segments.push({type:'play',index:s.index,result:P.result,call:(P.call||{}).type,highlight:P.highlight||null,
      td:P.result==='touchdown'||!!(P.kick_return||{}).td,from:a,snap:snap===null?a:snap,res:res===null?now():res,to:now(),speed:s.speed||1});
  }
  const fin=now();
  await cdp.send('Page.stopScreencast'); await new Promise(r=>setTimeout(r,300));
  await ctx.close(); await b.close();
  if(!frames.length) throw new Error('aucune image capturée');
  /* liste ffmpeg : chaque image dure jusqu'à la suivante ; la première est à l'instant 0 de la vidéo */
  const base=frames[0].t; let txt='ffconcat version 1.0\n';
  frames.forEach((f,i)=>{ const next=i+1<frames.length?frames[i+1].t:t0+fin; txt+=`file '${path.basename(f.file)}'\nduration ${Math.max(0.001,next-f.t).toFixed(4)}\n`; });
  txt+=`file '${path.basename(frames[frames.length-1].file)}'\n`;
  fs.writeFileSync(path.join(dir,'images.txt'),txt);
  const decal=base-t0;                                         // la vidéo commence à la première image
  for(const s of timeline.segments) for(const k of ['from','to','snap','res']) if(s[k]!=null) s[k]=+(s[k]-decal).toFixed(3);
  timeline.end=+(fin-decal).toFixed(3); timeline.frames=frames.length;
  fs.writeFileSync(path.join(plan.out,'timeline.json'),JSON.stringify(timeline,null,1));
  if(errs.length){ console.error('erreurs JS :',errs); process.exit(1); }
  console.log(`filmé : ${timeline.end.toFixed(1)} s, ${frames.length} images, ${timeline.segments.length} segments`);
})().catch(e=>{ console.error(e); process.exit(1); });
