// Icône de l'onglet et des résultats Google (favicon) : le logo du site (ballon blanc sur le dégradé cyan → violet →
// rose de l'en-tête, de /og.png et de la photo TikTok). Écrit static/icons/favicon.svg, favicon-48/96/192.png et
// static/favicon.ico (PNG 16, 32, 48). L'icône de l'écran d'accueil (icon-180/192/512, bleu-vert) ne change pas.
// À relancer seulement si le logo change :   node outils/site/faire_favicon.js
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const STATIC=path.join(__dirname,'..','..','static');
/* le logo (même tracé que l'en-tête et faire_og.js) dans un carré arrondi de 48, à 73 % de sa taille */
const SVG=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2EE6FF"/><stop offset=".55" stop-color="#7A5CFF"/><stop offset="1" stop-color="#FF3D9A"/></linearGradient></defs>
<rect width="48" height="48" rx="12" fill="url(#g)"/>
<g transform="translate(6.5 6.5) scale(1.4583)"><path d="M1.6 9.6h3.6M.8 12h4.4M1.6 14.4h3.6" stroke="#fff" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/><path d="M7 12C9.7 7.3 19.3 7.3 22.4 12 19.3 16.7 9.7 16.7 7 12Z" fill="#fff"/><path d="M11.8 12h6.4M13.4 10.7v2.6M15 10.7v2.6M16.6 10.7v2.6" stroke="#1E5C78" stroke-width="1.2" stroke-linecap="round"/></g>
</svg>
`;
function ico(pngs){                      // fichier .ico dont chaque image est un PNG (accepté par tous les navigateurs)
  const head=Buffer.alloc(6+16*pngs.length); head.writeUInt16LE(0,0); head.writeUInt16LE(1,2); head.writeUInt16LE(pngs.length,4);
  let off=head.length;
  pngs.forEach(([n,b],i)=>{ const e=6+16*i; head.writeUInt8(n>=256?0:n,e); head.writeUInt8(n>=256?0:n,e+1); head.writeUInt8(0,e+2); head.writeUInt8(0,e+3);
    head.writeUInt16LE(1,e+4); head.writeUInt16LE(32,e+6); head.writeUInt32LE(b.length,e+8); head.writeUInt32LE(off,e+12); off+=b.length; });
  return Buffer.concat([head,...pngs.map(p=>p[1])]);
}
(async()=>{
  fs.writeFileSync(path.join(STATIC,'icons','favicon.svg'),SVG);
  const b=await chromium.launch({executablePath:EXE}); const p=await b.newPage();
  const rendu=async n=>{ await p.setViewportSize({width:n,height:n});
    await p.setContent(`<style>html,body{margin:0;background:transparent}img{display:block;width:${n}px;height:${n}px}</style><img src="data:image/svg+xml;base64,${Buffer.from(SVG).toString('base64')}">`);
    await p.waitForFunction(()=>document.images[0].complete);
    return p.screenshot({omitBackground:true}); };
  for(const n of [48,96,192]) fs.writeFileSync(path.join(STATIC,'icons',`favicon-${n}.png`),await rendu(n));
  const petits=[]; for(const n of [16,32,48]) petits.push([n,await rendu(n)]);
  fs.writeFileSync(path.join(STATIC,'favicon.ico'),ico(petits));
  await b.close(); console.log('écrit : static/icons/favicon.svg, favicon-48/96/192.png, static/favicon.ico');
})().catch(e=>{ console.error(e); process.exit(1); });
