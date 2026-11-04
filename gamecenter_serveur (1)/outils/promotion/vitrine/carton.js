// Vidéo « vitrine » : carton de fin (logo du site + « snapline.live »), polices du site.  node carton.js <L|P> <dossier> [url]
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const F=process.argv[2]||'L', OUT=process.argv[3]||'carton_'+F, URL=process.argv[4]||'http://localhost:8170/';
const W=F==='L'?640:360, H=F==='L'?360:640, FPS=30, DUR=+process.env.END_DUR||2.2;
fs.mkdirSync(OUT,{recursive:true});
(async()=>{
  const b=await chromium.launch({executablePath:EXE}); const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:3,colorScheme:'dark'});
  const p=await ctx.newPage(); await p.goto(URL,{waitUntil:'networkidle'});
  await p.evaluate(()=>document.fonts.load("900 80px 'Big Shoulders Display'"));
  await p.evaluate(([L])=>{
    const C=getComputedStyle(document.documentElement); const brand='linear-gradient(135deg,#2EE6FF 0%,#7A5CFF 55%,#FF3D9A 100%)';
    const svg=document.querySelector('.rail .mark svg').outerHTML;
    document.querySelectorAll('body > *').forEach(e=>e.remove());
    const st=document.createElement('style'); st.textContent=`
      html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#060A13!important}
      #ec{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:${L?14:16}px;color:#EEF1FF;font-family:Manrope,Sora,system-ui,sans-serif;
        background:radial-gradient(70% 60% at 20% 15%,rgba(38,110,140,.55) 0%,transparent 60%),radial-gradient(60% 50% at 90% 95%,rgba(122,92,255,.32) 0%,transparent 65%),#060A13}
      #mk{width:${L?76:84}px;height:${L?76:84}px;border-radius:${L?20:22}px;background:${brand};display:grid;place-items:center;box-shadow:0 0 50px rgba(139,92,255,.55)}
      #mk svg{width:62%;height:62%}
      #wm{font:900 ${L?78:64}px/.9 'Big Shoulders Display',Archivo,system-ui;letter-spacing:.01em;white-space:nowrap}
      #wm span{display:inline-block}
      #wm .dot{background:${brand};-webkit-background-clip:text;background-clip:text;color:transparent}
      #tg{font:700 ${L?12.5:12}px/1.3 Manrope,system-ui;letter-spacing:.2em;text-transform:uppercase;color:rgba(226,232,246,.72);text-align:center}
      #bar{width:${L?120:110}px;height:3px;border-radius:3px;background:${brand}}`;
    document.head.appendChild(st);
    const ec=document.createElement('div'); ec.id='ec';
    ec.innerHTML=`<div id="mk">${svg}</div><div id="wm">${[...'snapline'].map(c=>`<span>${c}</span>`).join('')}${[['.','#2EE6FF'],['l','#3FC4FF'],['i','#6A86FF'],['v','#9A5CF0'],['e','#E04CB8']].map(([c,k])=>`<span style="color:${k}">${c}</span>`).join('')}</div><div id="bar"></div><div id="tg">${L?'24 AI coaches · every game live · free':'24 AI coaches<br>every game live · free'}</div>`;
    document.body.appendChild(ec);
    const e3=q=>1-Math.pow(1-Math.max(0,Math.min(1,q)),3), bk=q=>{ q=Math.max(0,Math.min(1,q)); const c=1.6; return 1+(c+1)*Math.pow(q-1,3)+c*Math.pow(q-1,2); };
    window.__set=t=>{ const mk=document.getElementById('mk'); const q=t/0.45; mk.style.transform=`scale(${.4+.6*bk(q)}) rotate(${(1-e3(q))*-12}deg)`; mk.style.opacity=Math.min(1,q*2);
      [...document.querySelectorAll('#wm span')].forEach((s,i)=>{ const r=(t-.18-i*.035)/.32; s.style.opacity=Math.min(1,Math.max(0,r*1.6)); s.style.transform=`translateY(${(1-e3(r))*26}px)`; s.style.filter=`blur(${(1-e3(r))*6}px)`; });
      const bar=document.getElementById('bar'), rb=(t-.6)/.4; bar.style.transform=`scaleX(${e3(rb)})`;
      const tg=document.getElementById('tg'), rt=(t-.75)/.4; tg.style.opacity=Math.max(0,Math.min(1,rt)); tg.style.transform=`translateY(${(1-e3(rt))*8}px)`;
      const z=1+.03*t/2.2; document.getElementById('ec').style.transform=`scale(${z})`; };
  },[F==='L']);
  await p.evaluate(()=>document.fonts.ready);
  const n=Math.round(DUR*FPS);
  for(let i=0;i<n;i++){ await p.evaluate(t=>window.__set(t),i/FPS); await p.screenshot({path:path.join(OUT,`e${String(i).padStart(4,'0')}.png`)}); }
  console.log('carton',F,n); await b.close();
})().catch(e=>{ console.error(e); process.exit(1); });
