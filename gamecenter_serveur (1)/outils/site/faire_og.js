// Image de partage (Open Graph / Twitter, 1200×630) : static/og.png, servie par /og.png (bloc 2, étape 8).
// À relancer seulement si le visuel change :   node outils/site/faire_og.js
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const OUT=path.join(__dirname,'..','..','static','og.png');
const LOGO='<svg viewBox="0 0 24 24"><path d="M1.6 9.6h3.6M.8 12h4.4M1.6 14.4h3.6" stroke="#fff" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/><path d="M7 12C9.7 7.3 19.3 7.3 22.4 12 19.3 16.7 9.7 16.7 7 12Z" fill="#fff"/><path d="M11.8 12h6.4M13.4 10.7v2.6M15 10.7v2.6M16.6 10.7v2.6" stroke="#1E5C78" stroke-width="1.2" stroke-linecap="round"/></svg>';
const yard=[...Array(11)].map((_,i)=>`<i style="left:${8+i*8.4}%"></i>`).join('');
const HTML=`<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800;900&family=Archivo:wght@600;800&display=swap">
<style>
  html,body{margin:0;width:1200px;height:630px;overflow:hidden;background:#0B0E1A;font-family:Archivo,system-ui,sans-serif;color:#fff}
  .bg{position:absolute;inset:0;background:radial-gradient(90% 120% at 15% 0%,#2A4E74 0%,#0B0E1A 65%)}
  .turf{position:absolute;right:-60px;bottom:-40px;width:640px;height:420px;transform:perspective(900px) rotateX(48deg) rotateZ(-8deg);
    background:linear-gradient(90deg,#1E5C78 0 8%,#163a4d 8% 92%,#1E5C78 92%);border-radius:10px;opacity:.55}
  .turf i{position:absolute;top:0;bottom:0;width:2px;background:rgba(255,255,255,.35)}
  .wrap{position:absolute;left:80px;top:72px;right:80px}
  .brand{display:flex;align-items:center;gap:18px}
  .mk{width:76px;height:76px;border-radius:20px;background:linear-gradient(135deg,#2EE6FF,#7A5CFF 55%,#FF3D9A);display:grid;place-items:center}
  .mk svg{width:56px;height:56px}
  .nm{font:900 64px/1 'Big Shoulders Display',sans-serif;letter-spacing:.02em;text-transform:uppercase}
  h1{font:900 104px/.92 'Big Shoulders Display',sans-serif;text-transform:uppercase;margin:46px 0 0;max-width:820px}
  h1 em{font-style:normal;color:#2EE6FF}
  p{font:600 28px/1.35 Archivo,sans-serif;color:#C9D3E6;margin:22px 0 0;max-width:720px}
  .url{position:absolute;left:80px;bottom:56px;font:800 24px/1 Archivo,sans-serif;letter-spacing:.24em;color:#fff}
  .live{display:inline-flex;align-items:center;gap:10px;margin-left:26px;padding:8px 16px;border-radius:999px;background:#FF3D9A;font:800 20px/1 Archivo;letter-spacing:.16em}
  .live b{width:12px;height:12px;border-radius:50%;background:#fff}
</style>
<div class="bg"></div><div class="turf">${yard}</div>
<div class="wrap">
  <div class="brand"><div class="mk">${LOGO}</div><div class="nm">Snapline</div><span class="live"><b></b>LIVE</span></div>
  <h1>Live <em>simulated</em><br>American football</h1>
  <p>24 AI-coached teams · a full season every week · odds, picks, private leagues and replays</p>
</div>
<div class="url">SNAPLINE.LIVE</div>`;
(async()=>{
  const b=await chromium.launch({executablePath:EXE});
  const p=await b.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
  await p.setContent(HTML,{waitUntil:'networkidle'}).catch(()=>{});
  await p.evaluate(()=>document.fonts.ready);
  await p.screenshot({path:OUT});
  await b.close(); console.log('écrit :',OUT);
})().catch(e=>{ console.error(e); process.exit(1); });
