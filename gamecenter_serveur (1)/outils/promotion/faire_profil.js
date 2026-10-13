// Photo de profil des réseaux (TikTok, Instagram, YouTube ; étape 8) : le logo du site (marque de l'en-tête et de
// static/og.png), 1080×1080, affiché en rond par les réseaux (le ballon reste dans le cercle). Écrit
// outils/promotion/photo_profil.png. À relancer seulement si le logo change :   node outils/promotion/faire_profil.js
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const OUT=path.join(__dirname,'photo_profil.png');
const LOGO='<svg viewBox="0 0 24 24"><path d="M1.6 9.6h3.6M.8 12h4.4M1.6 14.4h3.6" stroke="#fff" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/><path d="M7 12C9.7 7.3 19.3 7.3 22.4 12 19.3 16.7 9.7 16.7 7 12Z" fill="#fff"/><path d="M11.8 12h6.4M13.4 10.7v2.6M15 10.7v2.6M16.6 10.7v2.6" stroke="#1E5C78" stroke-width="1.2" stroke-linecap="round"/></svg>';
const HTML=`<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;width:1080px;height:1080px;overflow:hidden}
  .mk{width:1080px;height:1080px;background:linear-gradient(135deg,#2EE6FF,#7A5CFF 55%,#FF3D9A);display:grid;place-items:center}
  .mk svg{width:820px;height:820px;transform:translateX(12px)}
</style>
<div class="mk">${LOGO}</div>`;
(async()=>{
  const b=await chromium.launch({executablePath:EXE});
  const p=await b.newPage({viewport:{width:1080,height:1080},deviceScaleFactor:1});
  await p.setContent(HTML);
  await p.screenshot({path:OUT});
  await b.close(); console.log('écrit :',OUT);
})().catch(e=>{ console.error(e); process.exit(1); });
