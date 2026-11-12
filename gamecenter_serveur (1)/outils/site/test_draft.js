// Front office FO-6 (My team › Draft : la draft des supporters) — test navigateur (Playwright + serveur réel, copie des
// deux dernières semaines, horloge réglée par GC_DEMO_AT).
//   node outils/site/test_draft.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// Les semaines publiées n'ont pas encore de draft : la copie de la semaine en cours reçoit une annonce (CTX_WR1, trois
// prospects tirés par moteur/draft.py) et une question de la semaine (comme test_front_office.js) ; la semaine d'avant,
// une draft (CTX_CB1) appliquée cette semaine (week.json → drafted, roster : la recrue « drafted_by_fans »).
// Vérifie (écrans validés sur l'iPad) :
//   - jeudi : onglet Draft avec le décompte, « Who replaces … ? », trois prospects verrouillés (ni noms ni notes dans la
//     page), « Remind me when it opens », la carte « Draft day » sur l'écran du vote ; VEC : pas d'onglet Draft ;
//   - vendredi 13:00 : « Open », « Pick …'s successor », trois prospects (Now / Ceiling / Growth, notes, Football IQ),
//     « Draft <nom> » enregistré sur le serveur puis changé ; téléphone 390 px sans défilement horizontal ;
//   - samedi (après le verrou) : « Closed », parts du vote, « Your pick » ;
//   - lundi : la révélation avec le résultat de la draft et la fiche du rookie (« Drafted by the fans · W… »), le badge
//     « Fans' pick » au roster ;
//   - GC_FRONT_OFFICE=off : pas d'onglet. Aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn, spawnSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8184, URL0=`http://localhost:${PORT}`;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const CAP=process.env.FO_CAPTURES||'';
const capture=async(p,nom,sel)=>{ if(!CAP) return; fs.mkdirSync(CAP,{recursive:true}); await p.waitForTimeout(400);
  const el=sel?await p.$(sel):null; await (el||p).screenshot({path:path.join(CAP,nom+'.png')}); };
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

/* ---- les données ---- */
const NOMS=fs.readdirSync(WEEKS).filter(n=>n.startsWith('week_')).sort().slice(-2);
const DATA=fs.mkdtempSync(path.join(os.tmpdir(),'gc-fo6-'));
process.on('exit',()=>{ try{ fs.rmSync(DATA,{recursive:true,force:true}); }catch(e){} });
for(const n of NOMS) fs.cpSync(path.join(WEEKS,n),path.join(DATA,'weeks',n),{recursive:true});
const [PREV,CUR]=NOMS.map(n=>path.join(DATA,'weeks',n,'week.json'));
const W=JSON.parse(fs.readFileSync(CUR,'utf8')), P=JSON.parse(fs.readFileSync(PREV,'utf8'));
const LUNDI=W.week.start, SUIVANT=new Date(Date.parse(LUNDI+'T12:00:00Z')+7*864e5).toISOString().slice(0,10);
const TEAMS=Object.keys(W.teams);
/* les annonces, tirées par le moteur (moteur/draft.py) */
const py=spawnSync('python3',['-c',`
import json, sys, copy
sys.path.insert(0, sys.argv[1])
from moteur import draft as dr
noms = ([f"Prenom{i}" for i in range(30)], [f"Nom{i}" for i in range(30)])
out = {}
for f, pid, cle in ((sys.argv[2], "CTX_WR1", int(sys.argv[4])), (sys.argv[3], "CTX_CB1", int(sys.argv[4]) - 1)):
    e = json.load(open(f))["players_next_week"]
    _, a = dr.annonceur()(e, pid, e["joueurs"][pid], cle, noms, set())
    out[pid] = a
print(json.dumps(out))`,ROOT,CUR,PREV,String(W.week.index)]);
if(py.status) throw new Error(String(py.stderr));
const A=JSON.parse(String(py.stdout)), AW=A.CTX_WR1, AC=A.CTX_CB1;
const question=(week,index,lever,label,q,opts)=>({version:'supporters-1',index,week,lever,label,question:q,side:'offense',setting:'x',
  options:opts.map(([id,l])=>({id,label:l})),teams:Object.fromEntries(TEAMS.map(a=>[a,{current:2,bands:[1,3],values:{}}]))});
const Q4=[['prudent','Play it safe'],['coordinateur',"Coordinator's call"],['agressif','Go for it']];
const RP=[['plus_course','More runs'],['coordinateur',"Coordinator's call"],['plus_passe','More passes']];
W.fan_vote=question(SUIVANT,W.week.index+1,'quatrieme','4th down','How bold should we be on fourth down?',Q4);
W.fans={version:'supporters-1',lever:'course_passe',label:'Run or pass',side:'offense',setting:'pass_shift',file:'x',file_read:true,
  applied:Object.fromEntries(TEAMS.map(a=>[a,a==='CTX'?{choice:'plus_passe',source:'fans',votes:6}:{choice:'coordinateur',source:'coordinators',votes:0}]))};
P.fan_vote=question(LUNDI,P.week.index+1,'course_passe','Run or pass','Should we lean on the run or the pass?',RP);
W.draft={version:1,for_week:SUIVANT,announcements:[AW]};
P.draft={version:1,for_week:LUNDI,announcements:[AC]};
const HC=AC.prospects.find(p=>p.profile==='potentiel');
W.drafted=[{id:'CTX_CB1',team:'CTX',pos:AC.pos,retired:AC.retired,profile:'potentiel',name:HC.name,source:'fans',votes:6,coordinator:AC.coordinator}];
const rr=W.teams.CTX.roster.find(r=>r.id==='CTX_CB1');                 // la recrue au roster de la semaine
rr.name=HC.name; rr.progression=Object.assign({},rr.progression||{},{age:HC.age,ovr:HC.ovr,potential:HC.potential,dev:HC.dev,
  rookie:{week:W.week.index-1,replaces:AC.retired,profile:'potentiel',drafted_by_fans:true}});
fs.writeFileSync(CUR,JSON.stringify(W)); fs.writeFileSync(PREV,JSON.stringify(P));
const LOCK=Date.parse(W.week.standings_locked_at), OPEN=LOCK-11.5*3600e3;     // vendredi 12:00 → 23:30
const iso=ms=>new Date(ms).toISOString();
const OFF=(W.week.standings_locked_at.match(/([+-]\d\d:\d\d|Z)$/)||['','Z'])[1];

async function server(at,extra){
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:DATA,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_PUSH_FAKE:'1',GC_DEMO_AT:at},extra||{}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ const r=await fetch(URL0+'/api/time'); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}
const OUVERTES=[];
const arreter=async p=>{ while(OUVERTES.length) await OUVERTES.pop().close().catch(()=>{}); await new Promise(r=>{ p.on('exit',r); p.kill(); }); };
const api=async(u,body)=>{ const r=await fetch(URL0+'/api'+u,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}); return {status:r.status,json:await r.json().catch(()=>null)}; };
const sql=q=>{ const r=spawnSync('python3',['-c',`import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(sys.argv[2]); c.commit()`,path.join(DATA,'gamecenter.db'),q]); if(r.status) throw new Error(String(r.stderr)); };
const ouvrir=async(b,opts)=>{ const ctx=await b.newContext(Object.assign({viewport:{width:1440,height:1000}},opts||{}));
  const p=await ctx.newPage(); p.errs=[]; p.on('pageerror',e=>p.errs.push(e.message)); OUVERTES.push(ctx);
  await p.goto(URL0+'/',{timeout:120000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); return p; };
const connecter=async(p,c)=>{ await p.evaluate(c=>localStorage.setItem('gc-player-v1',JSON.stringify({token:c.token,name:c.name,account:true,fav_team:c.fav})),c);
  await p.reload({timeout:120000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:120000}); };
const myteam=async p=>{ await p.click('.rail-btn[data-view="myteam"]'); await p.waitForSelector('#viewMyteam .mt-bar, #viewMyteam .st-empty',{timeout:15000}); };
const onglet=async(p,k)=>{ await p.waitForSelector(`#viewMyteam .mt-tabs [data-mttab="${k}"]`,{timeout:15000}); await p.click(`#viewMyteam .mt-tabs [data-mttab="${k}"]`); };
const texte=async(p,s)=>((await p.textContent(s))||'').replace(/\s+/g,' ').trim();
const login=async pseudo=>{ const c=(await api('/account/login',{pseudo,password:'motdepasse1'})).json; return {token:c.token,name:c.name}; };

(async()=>{
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  let srv=await server(iso(OPEN-20*3600e3));                                      // jeudi : la draft est annoncée
  try{
    const reg=async(pseudo,fav)=>{ const c=(await api('/account/register',{pseudo,password:'motdepasse1'})).json;
      sql(`UPDATE players SET fav_team='${fav}' WHERE token='${c.token}'`); return {token:c.token,name:c.name,fav}; };
    const A1=await reg('DraftCTX','CTX'), B1=await reg('DraftVEC','VEC');
    sql([...Array(6).keys()].map(i=>`INSERT INTO fan_votes(player,week,team,lever,choice,at) VALUES('v${i}','${LUNDI}','CTX','course_passe','${i<4?'plus_passe':'plus_course'}',0);`).join('')
      +[...Array(6).keys()].map(i=>`INSERT INTO fan_votes(player,week,team,lever,choice,at) VALUES('d${i}','${LUNDI}','CTX','draft:CTX_CB1','${i<4?'potentiel':'pret'}',0);`).join('')
      +`INSERT INTO fan_votes(player,week,team,lever,choice,at) SELECT id,'${LUNDI}','CTX','draft:CTX_CB1','potentiel',0 FROM players WHERE token='${A1.token}';`);

    const p=await ouvrir(b); await connecter(p,A1); await myteam(p);
    await p.waitForSelector('#viewMyteam .mt-tabs [data-mttab="draft"]',{timeout:15000});
    const chip=await texte(p,'#viewMyteam .mt-tabs [data-mttab="draft"]');
    check(/^Draft\s*\d+ d \d+ h$|^Draft\s*\d+ h$/.test(chip),`jeudi : onglet Draft avec le décompte (« ${chip} »)`);
    await onglet(p,'draft'); await p.waitForSelector('#viewMyteam [data-drscreen="announced"]',{timeout:15000});
    const hero=await texte(p,'#viewMyteam .dr-hero');
    check(hero.includes(`Who replaces ${AW.retired}?`)&&/Draft day · Friday/.test(hero)&&/12:00 → 23:30/.test(hero),'« Who replaces … ? », « Draft day · Friday … 12:00 → 23:30 »');
    check(/Opens in/.test(hero)&&(await p.$$('#viewMyteam .dr-count div')).length===3,'décompte jours / heures / minutes');
    check((await p.$$('#viewMyteam .dr-lock')).length===3,'trois prospects verrouillés');
    const html=await p.innerHTML('#viewMyteam');
    check(AW.prospects.every(x=>!html.includes(x.name)),'ni noms ni notes des prospects avant l’ouverture');
    check(/Ready now/.test(html)&&/High ceiling/.test(html)&&/Football IQ/.test(html),'les trois profils');
    check((await texte(p,'#viewMyteam .dr-old')).includes(AW.retired)&&/Final season/i.test(await texte(p,'#viewMyteam .dr-old')),'la fiche du retraité (« Final season »)');
    check(/Remind me when it opens/.test(await texte(p,'#viewMyteam [data-drremind]')),'« Remind me when it opens »');
    await capture(p,'1-draft-annoncee','#viewMyteam');
    await onglet(p,'fo'); await p.waitForSelector('#viewMyteam [data-foscreen]',{timeout:15000});
    const v=await p.evaluate(()=>{ const b=document.querySelector('#viewMyteam [data-foview="vote"]'); if(b) b.click(); return !!b; });
    await p.waitForSelector('#viewMyteam [data-foscreen="vote"]',{timeout:15000});
    check((await texte(p,'#viewMyteam [data-dr="aside"]')).includes(`${AW.retired}’s final season`),'écran du vote : la carte « Draft day »');
    errs.push(...p.errs);
    const pb=await ouvrir(b); await connecter(pb,B1); await myteam(pb); await pb.waitForTimeout(1500);
    check(!(await pb.$('#viewMyteam .mt-tabs [data-mttab="draft"]')),'VEC : pas d’onglet Draft');
    errs.push(...pb.errs);
  }finally{ await arreter(srv); }

  /* ---- vendredi 13:00 : la draft est ouverte ---- */
  srv=await server(iso(OPEN+3600e3));
  try{
    const A1=Object.assign(await login('DraftCTX'),{fav:'CTX'});
    const p=await ouvrir(b); await connecter(p,A1); await myteam(p);
    await p.waitForSelector('#viewMyteam .mt-tabs [data-mttab="draft"] .dr-tchip.open',{timeout:15000});
    check(true,'vendredi : « Open » sur l’onglet');
    await onglet(p,'draft'); await p.waitForSelector('#viewMyteam [data-drscreen="open"]',{timeout:15000});
    const head=await texte(p,'#viewMyteam .dr-head');
    check(head.includes(`Pick ${AW.retired}’s successor`)&&/Closes tonight 23:30/.test(head),'« Pick …’s successor », « Closes tonight 23:30 »');
    const cards=await p.$$eval('#viewMyteam .dr-pro',e=>e.map(x=>x.textContent.replace(/\s+/g,' ')));
    check(cards.length===3&&AW.prospects.every((x,i)=>cards[i].includes(x.name)&&cards[i].includes('Ceiling')&&cards[i].includes('Growth')),'trois prospects : nom, Now / Ceiling / Growth');
    check(AW.pos==='QB'||cards.every(c=>/Football IQ/.test(c)),'la ligne « Football IQ »');
    const cta0=await p.evaluate(()=>{ const c=document.querySelector('#viewMyteam [data-drvote]'); return {d:c.disabled,t:c.textContent}; });
    check(cta0.d&&/Pick a prospect/.test(cta0.t),'bouton désactivé tant qu’aucun prospect n’est choisi');
    await p.click('#viewMyteam [data-drprof="potentiel"]');
    const nomHC=AW.prospects.find(x=>x.profile==='potentiel').name, last=nomHC.split(' ').pop();
    check(new RegExp(`Draft ${last}`).test(await p.textContent('#viewMyteam [data-drvote]')),`« Draft ${last} »`);
    await capture(p,'2-draft-ouverte','#viewMyteam');
    await p.click('#viewMyteam [data-drvote]'); await p.waitForSelector('#viewMyteam .fo-msg.ok',{timeout:10000});
    check(((await api('/draft?token='+A1.token)).json.my_picks||{}).CTX_WR1==='potentiel','choix enregistré sur le serveur');
    await p.click('#viewMyteam [data-drprof="intelligence"]');
    check(/instead/.test(await p.textContent('#viewMyteam [data-drvote]')),'« Draft … instead » pour changer');
    await p.click('#viewMyteam [data-drvote]'); await p.waitForSelector('#viewMyteam .fo-msg.ok',{timeout:10000});
    check(((await api('/draft?token='+A1.token)).json.my_picks||{}).CTX_WR1==='intelligence','choix changé');
    check(/Your pick/.test(await texte(p,'#viewMyteam [data-drprof="intelligence"]')),'« Your pick » sur le prospect choisi');
    errs.push(...p.errs);
    const ph=await ouvrir(b,{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true}); await connecter(ph,A1);
    await ph.evaluate(()=>window.__gc.season.setView('myteam')); await ph.waitForSelector('#viewMyteam .mt-bar',{timeout:15000});
    await onglet(ph,'draft'); await ph.waitForSelector('#viewMyteam [data-drscreen="open"]',{timeout:15000});
    const lay=await ph.evaluate(()=>({sw:document.documentElement.scrollWidth,w:innerWidth}));
    if(CAP){ await ph.waitForTimeout(400); await ph.screenshot({path:path.join(CAP,'5-telephone.png'),fullPage:true}); }
    check(lay.sw<=lay.w,`téléphone : pas de défilement horizontal (${lay.sw} px pour ${lay.w})`);
    errs.push(...ph.errs);
  }finally{ await arreter(srv); }

  /* ---- samedi : la draft est fermée ---- */
  srv=await server(iso(LOCK+10*3600e3));
  try{
    const A1=Object.assign(await login('DraftCTX'),{fav:'CTX'});
    const p=await ouvrir(b); await connecter(p,A1); await myteam(p); await onglet(p,'draft');
    await p.waitForSelector('#viewMyteam [data-drscreen="closed"]',{timeout:15000});
    const res=await texte(p,'#viewMyteam [data-dr="result"]');
    check(/Draft · 1 vote/.test(res)&&/100\s?%/.test(res)&&/✓ Your pick/.test(res)&&/Fewer than 5 votes/.test(res),`après le verrou : parts, « Your pick », moins de 5 votes (${res.slice(0,80)})`);
    check(/Closed/.test(await texte(p,'#viewMyteam .mt-tabs [data-mttab="draft"]')),'« Closed » sur l’onglet');
    await capture(p,'3-draft-fermee','#viewMyteam');
    errs.push(...p.errs);
  }finally{ await arreter(srv); }

  /* ---- lundi : la révélation et le rookie ---- */
  srv=await server(iso(Date.parse(LUNDI+'T09:00:00'+OFF)));
  try{
    const A1=Object.assign(await login('DraftCTX'),{fav:'CTX'});
    const p=await ouvrir(b); await connecter(p,A1); await myteam(p); await onglet(p,'fo');
    await p.waitForSelector('#viewMyteam [data-dr="rookie"]',{timeout:15000});
    const res=await texte(p,'#viewMyteam [data-dr="result"]'), rk=await texte(p,'#viewMyteam [data-dr="rookie"]');
    check(res.includes(HC.name)&&/Draft · 7 votes/.test(res)&&/✓ Your pick/.test(res)&&res.includes(`Joins the roster today in ${AC.retired}’s spot`),'révélation : le résultat de la draft (7 votes, « Your pick »)');
    check(rk.includes(HC.name)&&rk.includes(`replaced ${AC.retired}`)&&new RegExp(`Drafted by the fans · W${W.week.index-1}`,'i').test(rk)&&/Ceiling/.test(rk),'la fiche du rookie : « Drafted by the fans · W… », développement');
    await capture(p,'4-revelation-rookie','#viewMyteam');
    await onglet(p,'overview'); await p.waitForSelector('#viewMyteam .team-page',{timeout:15000});
    check(/Fans’ pick/.test(await texte(p,`#viewMyteam tr.pl-row[data-pl="CTX_CB1"]`)),'roster : le badge « Fans’ pick »');
    errs.push(...p.errs);
  }finally{ await arreter(srv); }

  /* ---- interrupteur coupé ---- */
  srv=await server(iso(OPEN+3600e3),{GC_FRONT_OFFICE:'off'});
  try{
    const A1=Object.assign(await login('DraftCTX'),{fav:'CTX'});
    const p=await ouvrir(b); await connecter(p,A1); await myteam(p); await p.waitForTimeout(1000);
    check(!(await p.$('#viewMyteam [data-mttab]')),'GC_FRONT_OFFICE=off : pas d’onglets');
    errs.push(...p.errs);
  }finally{ await arreter(srv); await b.close(); }
  check(errs.length===0,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  console.log(fail?`${fail} échec(s)`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
