// Visibilité (bloc 2, étape 8 — 12/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_visibilite.js         (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Vérifie : balises du <head> (titre, description, adresse canonique, Open Graph, Twitter, JSON-LD), balise de
// vérification Google (GC_GOOGLE_VERIFY), /robots.txt, /sitemap.xml, /og.png (1200×630), texte « What is Snapline? »
// sur l'accueil, bouton Share du grand écran (feuille de partage du téléphone, sinon lien copié) avec le lien ?watch=
// qui rouvre ce match ; mobile 390 px ; aucune erreur JS. Lancé par outils/site/tests_navigateur.sh (groupe site).
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8143, URL0=`http://localhost:${PORT}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

const week=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const W=JSON.parse(fs.readFileSync(path.join(WEEKS,week,'week.json'),'utf8'));
const reg=W.schedule.filter(g=>g.phase==='regular');
const G=reg.filter(g=>g.slot===1)[0];                                  // match terminé à l'heure du test
const AT=new Date(Date.parse(reg.filter(g=>g.slot===3)[0].kickoff)+60e3).toISOString();

async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-visib-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:AT,GC_PUSH_LOOP:'0',GC_GOOGLE_VERIFY:'abc"123'}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(URL0+'/api/time'); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const ouvrir=async(b,opts,q='',init)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  if(init) await ctx.addInitScript(init);
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message));
  await p.goto(URL0+'/'+q); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:30000}); return p; };

(async()=>{
  const srv=await server(); let b;
  try{
    console.log(`Visibilité — ${week}, match terminé ${G.id}`);
    /* fichiers du référencement */
    const rb=await fetch(URL0+'/robots.txt'), rt=await rb.text();
    check(rb.ok&&/^User-agent: \*/m.test(rt)&&/Disallow: \/api\//.test(rt)&&new RegExp('Sitemap: '+URL0+'/sitemap.xml').test(rt),'/robots.txt : tout le site, sauf /api/, et le plan du site');
    const sm=await fetch(URL0+'/sitemap.xml'), st=await sm.text();
    check(sm.ok&&/xml/.test(sm.headers.get('content-type'))&&st.includes(`<loc>${URL0}/</loc>`),'/sitemap.xml : la page d\'accueil');
    const og=await fetch(URL0+'/og.png'), ob=Buffer.from(await og.arrayBuffer());
    check(og.ok&&og.headers.get('content-type')==='image/png'&&ob.readUInt32BE(16)===1200&&ob.readUInt32BE(20)===630,'/og.png : PNG 1200×630');

    b=await chromium.launch({executablePath:EXE});
    const p=await ouvrir(b);
    const head=await p.evaluate(()=>{ const m=s=>{ const e=document.head.querySelector(s); return e&&(e.content||e.href||e.textContent); };
      return {title:document.title,desc:m('meta[name="description"]'),can:m('link[rel="canonical"]'),ogt:m('meta[property="og:title"]'),
        ogi:m('meta[property="og:image"]'),tw:m('meta[name="twitter:card"]'),ld:m('script[type="application/ld+json"]'),gv:m('meta[name="google-site-verification"]')}; });
    check(/Snapline/.test(head.title)&&/American football/.test(head.title),'titre : '+head.title);
    check(head.desc&&head.desc.length>=80&&head.desc.length<=170,`description (${head.desc&&head.desc.length} caractères)`);
    check(head.can==='https://snapline.live/','adresse canonique');
    check(head.ogt&&head.ogi==='https://snapline.live/og.png'&&head.tw==='summary_large_image','Open Graph et Twitter');
    let ld=null; try{ ld=JSON.parse(head.ld); }catch(e){}
    check(ld&&ld['@type']==='WebSite'&&ld.url==='https://snapline.live/','JSON-LD WebSite valide');
    check(head.gv==='abc"123','balise de vérification Google (GC_GOOGLE_VERIFY), échappée');
    const ab=await p.evaluate(()=>{ const s=document.getElementById('about'); return s&&{t:s.querySelector('h2').textContent,n:s.textContent.length,vis:!!s.offsetParent}; });
    check(ab&&ab.t==='What is Snapline?'&&ab.n>300&&ab.vis,'« What is Snapline? » sur l\'accueil');

    /* Share : feuille de partage du téléphone */
    const SHARE=()=>{ navigator.share=async d=>{ window.__shared=d; }; };
    const m=await ouvrir(b,{viewport:{width:390,height:844},isMobile:true,hasTouch:true},'?watch='+G.id,SHARE);
    await m.waitForSelector('#modal [data-share]',{timeout:15000});
    const sid=await m.getAttribute('#modal [data-share]','data-share');
    check(sid===G.id,'bouton Share sur le grand écran d\'un match terminé ('+sid+')');
    await m.click('#modal [data-share]');
    const sh=await m.evaluate(()=>window.__shared);
    check(sh&&sh.url===URL0+'/?watch='+G.id&&/ @ /.test(sh.title),'feuille de partage : '+(sh&&sh.url));
    const big=await m.evaluate(()=>{ const r=document.querySelector('#modal [data-share]').getBoundingClientRect(); return r.width>=24&&r.right<=390; });
    check(big,'mobile 390 px : le bouton tient dans l\'en-tête');
    const ab2=await m.evaluate(()=>document.documentElement.scrollWidth<=390);
    check(ab2,'mobile 390 px : pas de défilement horizontal');

    /* Share sans feuille de partage (ordinateur) : lien copié */
    const NOSHARE=()=>{ try{ delete Navigator.prototype.share; }catch(e){} navigator.share=undefined; };
    const ctxOpts={permissions:['clipboard-read','clipboard-write']};
    const d=await ouvrir(b,ctxOpts,'?watch='+G.id,NOSHARE);
    await d.waitForSelector('#modal [data-share]',{timeout:15000});
    await d.click('#modal [data-share]'); await d.waitForTimeout(300);
    const clip=await d.evaluate(()=>navigator.clipboard.readText()), toast=await d.textContent('#toast');
    check(clip===URL0+'/?watch='+G.id&&/Link copied/.test(toast),'ordinateur : lien copié ('+clip+')');

    /* le lien partagé rouvre le match */
    const r=await ouvrir(b,{},'?watch='+G.id);
    await r.waitForSelector('#modal .m-title',{timeout:15000});
    check(/@/.test(await r.textContent('#modal .m-title')),'le lien ?watch= rouvre le match au grand écran');

    const errs=[...p.errs,...m.errs,...d.errs,...r.errs];
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.join(' | '):''));
  }catch(e){ console.error(e); fail++; }
  finally{ if(b) await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC : ${fail}`:'OK'); process.exit(fail?1:0);
})();
