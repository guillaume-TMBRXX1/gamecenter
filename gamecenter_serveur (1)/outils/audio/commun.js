// Outils communs des tests navigateur de l'Audio System (11/10/2026).
// - GameFeeds de data/weeks, dans l'ordre (semaines puis matchs) ; « --semaines N » garde les N dernières semaines.
// - Attente du crochet de test (window.__gc, GC_TEST_HOOK=1) au lieu d'un délai fixe : la page met ≈ 4 s à démarrer.
// - LOT : matchs envoyés à la page par lots — tout data/weeks d'un coup (≈ 130 Mo de JSON) fait planter la page.
const fs=require('fs'), path=require('path');
const LOT=25;
function options(argv){ const a=argv.slice(2), i=a.indexOf('--semaines'); let semaines=0;
  if(i>=0){ semaines=parseInt(a[i+1],10)||0; a.splice(i,2); }
  return {args:a, semaines}; }
function lireFeeds(dir, semaines){
  let ws=fs.readdirSync(dir).filter(w=>fs.existsSync(path.join(dir,w,'games'))).sort();
  if(semaines>0) ws=ws.slice(-semaines);
  const out=[]; for(const w of ws) for(const f of fs.readdirSync(path.join(dir,w,'games')).sort()) out.push(JSON.parse(fs.readFileSync(path.join(dir,w,'games',f))));
  return out; }
async function ouvrir(p, url){ await p.goto(url); await p.waitForFunction(()=>window.__gc&&window.__gc.audio&&window.__gc.season,null,{timeout:30000}); }
module.exports={LOT,options,lireFeeds,ouvrir};
