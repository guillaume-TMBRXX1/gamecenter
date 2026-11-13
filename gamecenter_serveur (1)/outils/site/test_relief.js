// Joueurs en relief et ballon en cloche (README section 118, 12/11/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_relief.js [dossier data/weeks]     (depuis « gamecenter_serveur (1) »)
// Deux réglages de Settings › Display, coupés par défaut. Sur un match réel rejoué en temps simulé (grand écran), le test
// compte ce que le terrain dessine (ellipses = ombres des joueurs debout et du ballon, pointillés du vol, numéros) :
//   · sans rien toucher : interrupteurs éteints, terrain d'origine (aucune ombre de joueur, aucun pointillé de vol) ;
//   · après deux vrais clics dans Settings : interrupteurs allumés, réglages enregistrés dans le navigateur, 22 joueurs
//     debout avec leur numéro (ceux de la composition du moteur), ballon en cloche plus haut que le dessin d'origine, avec
//     son pointillé et son anneau au point de chute ; l'action elle-même (positions, ballon du moteur) est identique ;
//   · après rechargement : les réglages sont gardés ; un clic les recoupe et le terrain d'origine revient ;
//   · aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), PORT=8186;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feed(){
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()[0], dir=path.join(WEEKS,w,'games');
  const f=fs.readdirSync(dir).sort()[0];
  return {F:JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')),src:`${w}/${f}`};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-relief-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:'auto'}),stdio:'ignore'});
  for(let i=0;i<120;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
/* Dans la page : rejoue le match jusqu'à une passe en l'air (près du sommet), puis redessine le grand écran en comptant
   ce que le canevas reçoit. Même match et même pas de temps à chaque appel : l'action trouvée est la même. */
const mesure=F=>{
  const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
  let ok=false;
  for(let i=0;i<200000&&g.status!=='final';i++){ G.stepGame(g,0.02);
    const f=g.plan&&g.plan.flight;
    if(g.phase==='play'&&g.plan.type==='pass'&&f&&f.peak>0.9&&Math.hypot(f.to.x-f.from.x,f.to.y-f.from.y)>12&&g.ball.h>f.peak*0.93){ ok=true; break; } }
  g.paused=true;
  if(!ok) return null;
  const v=G.getModalView(), P=CanvasRenderingContext2D.prototype, o={ell:0,dash:0,txt:[],ballY:null,arcs:0};
  const e0=P.ellipse, d0=P.setLineDash, t0=P.fillText, tr0=P.translate, a0=P.arc;
  P.ellipse=function(...a){ if(this===v.ctx) o.ell++; return e0.apply(this,a); };
  P.setLineDash=function(a){ if(this===v.ctx&&a.length&&a[0]<0.1) o.dash++; return d0.call(this,a); };
  P.fillText=function(...a){ if(this===v.ctx) o.txt.push(String(a[0])); return t0.apply(this,a); };
  P.translate=function(x,y){ if(this===v.ctx) o.ballY=y; return tr0.call(this,x,y); };   /* le dernier : le ballon */
  P.arc=function(...a){ if(this===v.ctx) o.arcs++; return a0.apply(this,a); };
  try{ v._sig=null; v.draw(5,performance.now()); } finally { P.ellipse=e0; P.setLineDash=d0; P.fillText=t0; P.translate=tr0; P.arc=a0; }
  const sm=G.slotMap(g), nums=s=>sm[s].map(p=>p&&p.number!=null?String(p.number):null).filter(Boolean);
  const f=g.plan.flight;
  return Object.assign(o,{seq:g.cur.seq,off:g.off.map(p=>[p.x,p.y]),def:g.def.map(p=>[p.x,p.y]),ball:[g.ball.x,g.ball.y,g.ball.h],
    sol:v.Y(g.ball.y),nums:nums('off').concat(nums('def')),dist:Math.hypot(f.to.x-f.from.x,f.to.y-f.from.y),s:v.s});
};
const reglages=p=>p.evaluate(()=>{ const sw=n=>{ const b=document.querySelector(`#viewSettings .switch[data-set="${n}"]`); return b?b.getAttribute('aria-checked'):null; };
  let d={}; try{ d=JSON.parse(localStorage.getItem('gc-settings-v1')||'{}'); }catch(e){}
  return {pawn:sw('pawn'),arc:sw('arc'),fx:sw('fx'),lsPawn:d.pawn,lsArc:d.arc}; });
const ouvrir=async p=>{ await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="pawn"]'); };

/* le grand écran du replay est fermé (Échap) avant de revenir aux réglages */
const versSettings=async p=>{ await p.keyboard.press('Escape'); await p.waitForFunction(()=>!window.__gc.getModalView(),null,{timeout:10000});
  await p.evaluate(()=>window.__gc.season.setView('settings')); await p.waitForSelector('#viewSettings .switch[data-set="pawn"]'); };

(async()=>{
  const {F,src}=feed();
  console.log(`${src} · ${F.plays.length} actions`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await ouvrir(p);
    let R=await reglages(p);
    check(R.pawn==='false'&&R.arc==='false','Settings › Display : « 3D players » et « Ball flight » présents, éteints par défaut');
    check(R.lsPawn!==true&&R.lsArc!==true,'rien d\'enregistré avant un clic');
    const A=await p.evaluate(mesure,F);
    check(!!A,'une passe longue en l\'air trouvée dans le match');
    if(!A) throw new Error('pas de passe');
    console.log(`   action ${A.seq} · passe de ${A.dist.toFixed(1)} yards · origine : ${A.ell} ellipse(s), ballon dessiné ${(A.sol-A.ballY).toFixed(1)} px au-dessus du sol`);
    check(A.ell<=2&&A.dash===0,'par défaut : terrain d\'origine (pas d\'ombre de joueur, pas de pointillé de vol)');

    await versSettings(p);
    await p.click('#viewSettings .switch[data-set="pawn"]'); await p.click('#viewSettings .switch[data-set="arc"]');
    R=await reglages(p);
    check(R.pawn==='true'&&R.arc==='true','deux clics : les interrupteurs sont allumés');
    check(R.lsPawn===true&&R.lsArc===true,'et les réglages sont enregistrés dans le navigateur');
    check(R.fx==='true','« Big-play effects » n\'a pas bougé');
    const B=await p.evaluate(mesure,F);
    check(!!B&&B.seq===A.seq,'même action retrouvée');
    if(B){
      console.log(`   relief : ${B.ell} ellipses, ${B.dash} pointillé(s) de vol, ballon dessiné ${(B.sol-B.ballY).toFixed(1)} px au-dessus du sol`);
      check(B.ell>=22+1,`22 joueurs debout (une ombre chacun) et l'ombre du ballon : ${B.ell} ellipses`);
      const manque=B.nums.filter(n=>!B.txt.includes(n));
      check(B.nums.length>=20&&!manque.length,`les numéros de la composition du moteur sont sur les joueurs (${B.nums.length-manque.length} / ${B.nums.length})`);
      check(B.dash===1,'le chemin déjà parcouru par le ballon est en pointillé');
      check(B.sol-B.ballY>(A.sol-A.ballY)*2&&B.sol-B.ballY>B.s*1.2,`la cloche est nettement plus haute que le dessin d'origine (${(B.sol-B.ballY).toFixed(1)} px contre ${(A.sol-A.ballY).toFixed(1)})`);
      check(B.arcs>=1,'anneau au point de chute');
      check(JSON.stringify([B.off,B.def,B.ball])===JSON.stringify([A.off,A.def,A.ball]),'l\'action est identique : mêmes positions des 22 joueurs, même ballon du moteur');
    }

    await ouvrir(p);                                   /* rechargement */
    R=await reglages(p);
    check(R.pawn==='true'&&R.arc==='true','après rechargement : les deux réglages sont gardés');
    const C=await p.evaluate(mesure,F);
    check(!!C&&C.ell>=23&&C.dash===1,'et le terrain en relief est dessiné dès l\'ouverture');
    await versSettings(p);
    await p.click('#viewSettings .switch[data-set="pawn"]'); await p.click('#viewSettings .switch[data-set="arc"]');
    R=await reglages(p);
    check(R.pawn==='false'&&R.arc==='false'&&R.lsPawn===false&&R.lsArc===false,'un clic les recoupe');
    const D=await p.evaluate(mesure,F);
    check(!!D&&D.ell===A.ell&&D.dash===0&&Math.abs((D.sol-D.ballY)-(A.sol-A.ballY))<0.01,'et le terrain d\'origine revient, identique');
    check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }finally{ await b.close(); srv.kill(); }
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})();
