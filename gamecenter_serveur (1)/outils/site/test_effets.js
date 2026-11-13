// Effets visuels au choix du spectateur (README section 119, 13/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_effets.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Quatre réglages coupés par défaut : « Slow motion on big plays », « Routes before the snap », « Club colours on the
// field » (Settings › Match visuals) et « Interface motion » (Settings › Display). Sur un match réel rejoué en temps simulé :
//   · sans rien toucher : interrupteurs éteints, aucune action ralentie, aucun tracé, en-but d'origine, pas d'animation ;
//   · après quatre vrais clics : réglages enregistrés ; une grosse action est ralentie à son moment clé (pastille
//     « Slow-mo ») et dure EXACTEMENT le temps prévu, pour finir au même endroit que sans ralenti (ballon identique, joueurs à quelques centimètres près) ; les tracés de
//     l'attaque sont dessinés avant le snap, et cachés quand le pari « Next play » est ouvert ; le nom du club est
//     peint dans l'en-but, son sigle au centre ; un onglet ouvert arrive en cascade ; une cote cliquée vole vers le
//     bulletin et le gain potentiel roule jusqu'à sa valeur ;
//   · après rechargement : réglages gardés ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8187;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const NOMS=['slow','routes','club','motion'];
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()[0], dir=path.join(WEEKS,w,'games');
  const f=fs.readdirSync(dir).sort()[0];
  return {F:JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')),src:`${w}/${f}`};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-effets-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:'auto'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* Dans la page : rejoue le match au pas de 0,02 s. Pour chaque action : durée réelle (pas × 0,02), durée prévue, tronçon
   ralenti, pastille vue, positions à la fin. Avant un snap de passe : ce que le terrain dessine (tracés, en-but). */
const rejouer=F=>{
  const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
  const v=G.getModalView(), P=CanvasRenderingContext2D.prototype, plays={}, dessin={};
  const peindre=()=>{ const o={dash:0,fill:[],stroke:[]}, d0=P.setLineDash, f0=P.fillText, s0=P.strokeText;
    P.setLineDash=function(a){ if(this===v.ctx&&a.length) o.dash++; return d0.call(this,a); };
    P.fillText=function(...a){ if(this===v.ctx) o.fill.push(String(a[0])); return f0.apply(this,a); };
    P.strokeText=function(...a){ if(this===v.ctx) o.stroke.push(String(a[0])); return s0.apply(this,a); };
    try{ v._sig=null; v.draw(5,performance.now()); } finally { P.setLineDash=d0; P.fillText=f0; P.strokeText=s0; }
    return o; };
  let n=0, tag=false, slowSeen=false;
  for(let i=0;i<400000&&!(g.status==='final');i++){
    const ph=g.phase, P0=g.cur, sl=g.slow, dur=g.dur;
    if(ph==='presnap'&&!dessin.pre&&P0&&P0.seq>4&&!g.special&&P0.call&&P0.call.type==='pass'&&g.t>0.5&&g.status==='live'&&g.pause<=0){
      dessin.pre=peindre(); dessin.pre.plan=!!(g._pre&&g._pre.plan);
      const od=g.odds; g.odds=Object.assign({},od,{np:{run:-110,pass:-110}}); g._pre=null; dessin.np=peindre(); dessin.np.plan=!!(g._pre&&g._pre.plan); g.odds=od; g._pre=null;
      dessin.home=g.home; dessin.away=g.away; }
    G.stepGame(g,0.02);
    if(ph==='play'){ n++; if(g.slowOn){ slowSeen=true; if(!tag){ v.draw(0.02,performance.now()); tag=!!(v.slowEl&&!v.slowEl.hidden); } }
      if(g.phase!=='play'){ plays[P0.seq]={n,dur,slow:sl||null,slowSeen,tag,res:P0.result,gain:P0.gain,off:g.off.map(p=>[+p.x.toFixed(3),+p.y.toFixed(3)]),ball:[+g.ball.x.toFixed(3),+g.ball.y.toFixed(3)]}; n=0; tag=false; slowSeen=false; } }
    else n=0;
  }
  g.paused=true;
  return {plays,dessin,status:g.status,name:{home:G.byId[g.id]?g.home:g.home}};
};
const etat=p=>p.evaluate(N=>{ const o={}; let d={}; try{ d=JSON.parse(localStorage.getItem('gc-settings-v1')||'{}'); }catch(e){}
  for(const n of N){ const b=document.querySelector(`#viewSettings .switch[data-set="${n}"]`); o[n]=b?b.getAttribute('aria-checked'):null; o['ls_'+n]=d[n]; }
  o.body=document.body.classList.contains('mo-on'); o.html=document.documentElement.hasAttribute('data-mo'); return o; },NOMS);
const ouvrir=async p=>{ await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="motion"]'); };
const versSettings=async p=>{ await p.keyboard.press('Escape'); await p.waitForFunction(()=>!window.__gc.getModalView(),null,{timeout:10000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="motion"]'); };

(async()=>{
  const {F,src}=feed();
  console.log(`${src} · ${F.plays.length} actions`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await ouvrir(p);
    let R=await etat(p);
    check(NOMS.every(n=>R[n]==='false'&&R['ls_'+n]!==true),'les quatre réglages sont présents et éteints par défaut');
    check(!R.body&&!R.html,'pas de classe d\'animation sur la page');
    const A=await p.evaluate(rejouer,F), PA=Object.values(A.plays);
    check(A.status==='final'&&PA.length>40,`match rejoué jusqu'au bout (${PA.length} actions dessinées)`);
    check(PA.every(o=>!o.slow&&!o.slowSeen),'par défaut : aucune action ralentie');
    check(A.dessin.pre&&!A.dessin.pre.plan&&A.dessin.pre.dash===0,'par défaut : aucun tracé avant le snap');
    const nomH=String(F.game.home.name).toUpperCase(), nomA=String(F.game.away.name).toUpperCase();
    check(A.dessin.pre&&![nomH,nomA,String(F.game.home.abbr)].some(x=>A.dessin.pre.fill.includes(x)),'par défaut : terrain d\'origine (ni nom de club peint, ni sigle au centre)');
    await versSettings(p);
    const ret0=await p.evaluate(()=>document.getElementById('tRet').textContent);

    for(const n of NOMS) await p.click(`#viewSettings .switch[data-set="${n}"]`);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='true'&&R['ls_'+n]===true),'quatre clics : interrupteurs allumés, réglages enregistrés');
    check(R.body&&R.html,'la page porte la classe d\'animation');

    /* interface : un onglet ouvert arrive en cascade */
    const V=await p.evaluate(()=>{ window.__gc.season.setView('schedule'); const el=document.getElementById('viewSchedule');
      return {in:el.classList.contains('mo-in'),it:el.querySelectorAll('.mo-it').length,an:getComputedStyle(el.firstElementChild).animationName}; });
    check(V.in&&V.it>=3&&V.an==='moIn',`onglet Schedule : arrivée en fondu-glissé, ${V.it} lignes en cascade`);
    await p.waitForFunction(()=>!document.getElementById('viewSchedule').classList.contains('mo-in'),null,{timeout:5000});
    /* interface : une cote cliquée vole vers le bulletin, le gain potentiel roule */
    const odd=p.locator('#viewSchedule .odd[data-key]:not([disabled])').first();
    if(await odd.count()){
      await odd.scrollIntoViewIfNeeded(); await odd.click();
      const vol=await p.evaluate(()=>!![...document.querySelectorAll('body>.odd[aria-hidden="true"]')].length);
      const mid=await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(document.getElementById('tRet').textContent)))));
      await p.waitForTimeout(1300);
      const fin=await p.evaluate(()=>({ret:document.getElementById('tRet').textContent,reste:document.querySelectorAll('body>.odd[aria-hidden="true"]').length,
        attendu:document.querySelector('#slipList')?document.getElementById('fabR').textContent:null}));
      check(vol,'la cote cliquée s\'envole vers le bulletin (copie posée au-dessus de la page)');
      check(fin.reste===0,'et la copie est retirée à l\'arrivée');
      check(fin.ret!==ret0&&fin.ret===fin.attendu,`le gain potentiel finit sur sa vraie valeur (${fin.ret})`);
      check(mid!==fin.ret,`en passant par des valeurs intermédiaires (${mid})`);
    } else check(false,'une cote ouverte dans Schedule');

    const B=await p.evaluate(rejouer,F), PB=Object.values(B.plays);
    const lents=PB.filter(o=>o.slow);
    console.log(`   ${lents.length} actions ralenties sur ${PB.length}`);
    check(lents.length>=3,'des grosses actions sont ralenties');
    const gros=o=>o.res==='touchdown'||o.res==='interception'||((o.res==='complete'||o.res==='run')&&o.gain>=20);
    check(lents.every(gros),'seulement des touchdowns, interceptions ou gains de 20 yards et plus');
    check(lents.every(o=>o.slowSeen&&o.tag),'chacune passe par son ralenti, pastille « Slow-mo » affichée');
    const ecart=lents.map(o=>Math.abs(o.n*0.02-o.dur));
    check(ecart.every(e=>e<=0.021),`une action ralentie dure le temps prévu (écart maximal ${Math.max(...ecart).toFixed(3)} s)`);
    /* même nombre de pas, même ballon ; les joueurs à moins de 0,25 yard : le lissage des déplacements (section 83)
       dépend du rythme des images, donc un ralenti laisse un joueur à quelques centimètres près */
    let pire=0; const diff=Object.keys(A.plays).filter(k=>{ const x=A.plays[k], y=B.plays[k]; if(!y||y.n!==x.n||JSON.stringify(x.ball)!==JSON.stringify(y.ball)) return true;
      let m=0; x.off.forEach((q,i)=>{ m=Math.max(m,Math.abs(q[0]-y.off[i][0]),Math.abs(q[1]-y.off[i][1])); }); pire=Math.max(pire,m); return m>0.25; });
    check(Object.keys(B.plays).length===PA.length&&!diff.length,`toutes les actions durent autant et finissent au même endroit qu'avant (ballon identique, joueurs à ${pire.toFixed(2)} yard près)`+(diff.length?` — écarts : ${diff.slice(0,5)}`:''));
    check(B.dessin.pre&&B.dessin.pre.plan&&B.dessin.pre.dash>=2,`avant le snap : les tracés de l'attaque sont dessinés (${B.dessin.pre&&B.dessin.pre.dash} pointillés)`);
    check(B.dessin.np&&!B.dessin.np.plan&&B.dessin.np.dash===0,'pari « Next play » ouvert : aucun tracé (il révélerait course ou passe)');
    check(B.dessin.pre.fill.includes(nomH)||B.dessin.pre.fill.includes(nomA)||B.dessin.pre.fill.includes(String(F.game.home.abbr)),'terrain du club : nom peint dans l\'en-but ou sigle au centre');
    check(!B.dessin.pre.stroke.includes(nomH)&&!B.dessin.pre.stroke.includes(nomA),'et plus de nom en simple contour');

    await ouvrir(p);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='true')&&R.body&&R.html,'après rechargement : les quatre réglages sont gardés');
    for(const n of NOMS) await p.click(`#viewSettings .switch[data-set="${n}"]`);
    R=await etat(p);
    check(NOMS.every(n=>R[n]==='false'&&R['ls_'+n]===false)&&!R.body&&!R.html,'un clic les recoupe, la classe d\'animation est retirée');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
