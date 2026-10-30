// Fin d'un match en direct sur le tableau (31/10/2026) — test navigateur (Playwright + serveur réel).
//   node outils/site/test_fin_live.js          (depuis « gamecenter_serveur (1) »)
// Horloge du serveur 25 s avant la fin d'un match de la dernière semaine (GC_DEMO_AT). Avant : dès que le serveur
// déclarait le match fini, le tableau le relançait en replay ; ses dernières actions (souvent les genoux posés) et l'écran
// final n'étaient jamais montrés. Vérifie : la tuile reste un match en direct après la fin ; elle joue chacune de ses
// dernières actions, sans en sauter (un résultat reçu reconstruit le tableau sans la recaler) ; puis l'écran final ; il y est encore une minute après la fin ; aucune erreur JS. Lancé par tests_navigateur.sh.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn,execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks'), PORT=8179;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };
const W=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
const G=JSON.parse(execFileSync('python3',['-c',`
import os,sys,json,tempfile
d=tempfile.mkdtemp(); os.makedirs(d+'/weeks'); os.symlink(os.path.abspath('data/weeks/${W}'),d+'/weeks/${W}')
os.environ['GC_DATA']=d; sys.path.insert(0,'.')
import serveur; serveur.load_weeks(); w=list(serveur._WEEKS.values())[0]
g=sorted(w.reg,key=lambda g:g['ko'])[len(w.reg)//2]
print(json.dumps({'id':g['id'],'end':g['end'],'n':g['n']}))`],{cwd:ROOT}).toString());

(async()=>{
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-finlive-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });
  fs.mkdirSync(path.join(data,'weeks')); fs.symlinkSync(path.join(WEEKS,W),path.join(data,'weeks',W));
  const srv=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,
    env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_PUSH_LOOP:'0',GC_DEMO_AT:new Date(G.end-25e3).toISOString()}),stdio:'ignore'});
  for(let i=0;i<240;i++){ try{ if((await fetch(`http://localhost:${PORT}/api/time`)).ok) break; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  const b=await chromium.launch({executablePath:EXE}), errs=[];
  try{
    const p=await b.newPage({viewport:{width:1440,height:1000}}); p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:60000});
    const vus=new Set(), etats=[]; let finale=null, apres=null;
    for(let i=0;i<180;i++){
      const r=await p.evaluate(id=>{ const X=window.__gc, g=X.byId['s-'+id], s=X.season.SCHED.find(x=>x.id===id), t=X.season.nowMs();
        const el=document.querySelector(`#liveGrid .tile[data-gid="s-${id}"] .brk`);
        return {dt:(t-s.end)/1000, mode:g&&g.mode, status:g&&g.status, idx:g&&g.idx, brk:g&&g.brk&&g.brk.kind, txt:el&&!el.hidden?el.textContent.replace(/\s+/g,' '):''}; },G.id);
      if(r.mode==='live') vus.add(r.idx);
      etats.push(r);
      if(r.brk==='final'&&!finale) finale=r;
      if(r.dt>60){ apres=r; break; }
      await p.waitForTimeout(500);
    }
    const fin=etats.filter(r=>r.dt>=0);
    check(fin.length&&fin.every(r=>r.mode==='live'),`après la fin : la tuile reste un match en direct (${fin.length} relevés, aucun replay)`);
    const v=[...vus].sort((a,b)=>a-b), d0=v[0], attendu=Array.from({length:G.n-d0},(_,k)=>d0+k);
    check(G.n-d0>=3&&JSON.stringify(v)===JSON.stringify(attendu),`ses dernières actions jouées une à une, jusqu'à la dernière (${v.join(', ')} sur ${G.n})`);
    check(!!finale&&/Final/i.test(finale.txt)&&/win|Tie game/.test(finale.txt),`puis l'écran final, ${finale?Math.round(finale.dt)+' s après la fin':'jamais'} (« ${finale?finale.txt.slice(0,50):''} »)`);
    check(!!apres&&apres.mode==='live'&&apres.brk==='final','une minute après la fin : toujours l\'écran final');
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs[0]:''));
  }catch(e){ console.log(e); fail++; }
  finally{ await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})();
