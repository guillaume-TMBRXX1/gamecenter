// Recherche du site (barre du haut, touche « / ») — test navigateur (Playwright, serveur réel avec le crochet de test).
// Remplace le test hors dépôt tsearch.py, perdu (bloc 1, étape 4, 11/10/2026). Lancé par outils/site/tests_navigateur.sh.
//   GC_TEST_HOOK=1 uvicorn serveur:app --port 8108   puis   node outils/site/test_recherche.js data/weeks 8108
// Équipes (code, nom, sans tenir compte des majuscules ni des accents), joueurs, coordinateurs, matchs, pages ; ↑ ↓,
// Entrée ouvre le résultat, Échap ferme, « / » donne le focus ; « Nothing matches » ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path');
const DATA=process.argv[2]||'data/weeks', PORT=process.argv[3]||8108, EXE=process.env.CHROMIUM_PATH||undefined;
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
(async()=>{
  const health=await (await fetch(`http://localhost:${PORT}/api/health`)).json();
  const W=JSON.parse(fs.readFileSync(path.join(DATA,'week_'+health.week,'week.json'),'utf8'));
  const T=W.teams[Object.keys(W.teams).sort()[0]], P=T.roster[0], oc=T.coordinators.offense;
  const G=W.schedule.find(g=>g.phase==='regular');
  const b=await chromium.launch({executablePath:EXE});
  const p=await b.newPage({viewport:{width:1280,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gcSearch,null,{timeout:30000});
  const results=()=>p.evaluate(()=>[...document.querySelectorAll('#searchList li')].map(li=>({g:li.classList.contains('sr-g'),none:li.classList.contains('sr-none'),t:li.textContent.trim()})));
  const chercher=async q=>{ await p.fill('#search',''); await p.type('#search',q); await p.waitForTimeout(80); return results(); };
  const groupe=(r,g)=>{ const i=r.findIndex(x=>x.g&&x.t===g); if(i<0) return []; const out=[]; for(const x of r.slice(i+1)){ if(x.g) break; out.push(x.t); } return out; };
  console.log(`semaine ${health.week} · équipe ${T.abbr} · joueur ${P.name} · coordinateur ${oc} · match ${G.away} @ ${G.home}`);

  await p.click('body',{position:{x:5,y:5}}); await p.keyboard.press('/');
  check(await p.evaluate(()=>document.activeElement&&document.activeElement.id==='search'),'« / » met le focus sur la recherche');
  let r=await chercher(T.abbr.toLowerCase());
  check(r[0]&&r[0].g&&r[0].t==='Teams'&&r[1]&&r[1].t.startsWith(T.abbr),`code en minuscules (${T.abbr.toLowerCase()}) → équipe en tête`);
  r=await chercher(T.name.split(' ').slice(-1)[0].toUpperCase().replace(/E/g,'É'));
  check(groupe(r,'Teams').some(t=>t.includes(T.name)),'nom avec majuscules et accents ajoutés → équipe trouvée');
  r=await chercher(P.name.split(' ').slice(-1)[0].slice(0,4).toLowerCase());
  check(groupe(r,'Players').some(t=>t.includes(P.name)),`début du nom d'un joueur → ${P.name}`);
  r=await chercher(oc);
  check(groupe(r,'Agents').some(t=>t.includes(oc)&&t.includes('Offensive coordinator')),`coordinateur → ${oc}`);
  r=await chercher(`${G.away} @ ${G.home}`);
  check(groupe(r,'Games').some(t=>t.includes(`${G.away} @ ${G.home}`)),`affiche ${G.away} @ ${G.home} → match`);
  r=await chercher('standings');
  check(groupe(r,'Pages').some(t=>t.startsWith('Standings')),'page « Standings »');
  r=await chercher('zzqxw');
  check(r.length===1&&r[0].none&&/Nothing matches/.test(r[0].t),'rien trouvé → message « Nothing matches »');
  await chercher(T.abbr); await p.keyboard.press('ArrowDown'); await p.keyboard.press('ArrowUp');
  const sel=await p.evaluate(()=>document.querySelector('#searchList [aria-selected="true"]')?.textContent||'');
  check(sel.startsWith(T.abbr),'↑ ↓ déplacent la sélection');
  await p.keyboard.press('Enter'); await p.waitForTimeout(400);
  const apres=await p.evaluate(()=>({pop:document.getElementById('searchPop').hidden,val:document.getElementById('search').value,
    teams:!!document.querySelector('#viewTeams .team-page')&&getComputedStyle(document.getElementById('viewTeams')).display!=='none'}));
  check(apres.pop&&apres.val===''&&apres.teams,'Entrée → page de l\'équipe, recherche fermée et vidée');
  await chercher('sched'); await p.keyboard.press('Escape');
  check(await p.evaluate(()=>document.getElementById('searchPop').hidden),'Échap ferme la liste');
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  await b.close(); console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
