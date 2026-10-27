// Le banc, les packages et les rotations (moteur 12.2 vicies quinquies, étape 7.3 — 21/10/2026) — test navigateur
// (Playwright + serveur réel).
//   node outils/site/test_banc.js [dossier data/weeks] [gamefeed.json]     (depuis « gamecenter_serveur (1) »)
// Prend le dernier match de data/weeks (ou le GameFeed donné) qui a un banc (game.rotation_model, play.subs) ; sinon un
// match réel auquel on ajoute un banc (11 remplaçants par côté) et des changements : 2e TE en 12 personnel, CB3 en nickel,
// rotations ordinaires (fatigue), QB2 en garbage time. Ne dépend pas de l'heure.
// Vérifie : les points du terrain portent le bon joueur action par action (play.subs), les rôles (« Nickel back »…), les
// noms avant le snap ; la fiche joueur (Depth, Snaps n (x %), énergie au coup de sifflet final) ; l'onglet Players
// (snaps) ; le tableau de profondeur ; play-by-play et commentateur seulement pour les changements marquants (QB2, goal
// line), pas pour les rotations ordinaires ; aucune erreur JS.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.resolve(process.argv[2]||path.join(ROOT,'data','weeks')), FEED=process.argv[3], PORT=8159;
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
let fail=0; const check=(c,msg)=>{ console.log((c?'  ✓ ':'  ✗ ')+msg); if(!c) fail++; };

function feeds(){
  const all=[];
  for(const w of fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().reverse()){
    const dir=path.join(WEEKS,w,'games');
    for(const f of fs.readdirSync(dir).sort()) all.push({file:path.join(dir,f),src:`${w}/${f}`});
  }
  return all;
}
const BANC=[['QB','QB2','QB2'],['RB','RB3','RB3'],['WR','WR4','WR4'],['TE','TE2','TE2'],['RT','RT2','OT'],['LG','LG2','OG'],
  ['EDGE','EDGE3','EDGE3'],['DT','DT3','DT3'],['LB','LB4','LB4'],['CB','CB3','CB3'],['S','S3','S3']];
function feedAvecBanc(){
  if(FEED) return {F:JSON.parse(fs.readFileSync(FEED,'utf8')),src:path.basename(FEED)+' (réel)'};
  const all=feeds();
  for(const {file,src} of all){
    const F=JSON.parse(fs.readFileSync(file,'utf8'));
    if(F.game.rotation_model&&F.plays.some(P=>(P.subs||[]).some(x=>x.pos==='QB'&&x.reason==='garbage'))&&F.plays.some(P=>(P.subs||[]).some(x=>x.reason==='package'&&x.pos==='WR3')))
      return {F,src:src+' (réel)'};
  }
  const {file,src}=all[0];
  const F=JSON.parse(fs.readFileSync(file,'utf8'));
  for(const s of ['home','away']){
    const R=F.game[s].roster, ab=R[0].id.split('_')[0], used=new Set(R.map(r=>r.number));
    R.forEach(r=>{ r.depth=1; r.profile='starter'; });
    for(const [pos,suf,slot] of BANC){
      const t=R.find(r=>r.pos===pos), n=[...Array(99).keys()].map(k=>k+1).find(k=>!used.has(k)); used.add(n);
      R.push({id:`${ab}_${suf}`,name:`Bench ${suf} ${ab}`,pos,number:n,ratings:Object.assign({},t.ratings),archetype:null,depth:2,
        profile:suf==='CB3'?'specialist':'veteran',slot,covers:[pos],specialty:suf==='CB3'?'slot corner':undefined});
    }
  }
  const ab=s=>F.game[s].roster[0].id.split('_')[0], k=F.plays.map((P,i)=>[P,i]).filter(([P])=>P.call&&(P.call.type==='run'||P.call.type==='pass'));
  const sub=(P,side,pos,i,o,reason)=>{ (P.subs=P.subs||[]).push({in:i,out:o,pos,reason,side}); };
  // 2e TE (12 personnel) sur la 3e action de scrimmage de l'attaque qui reçoit, puis retour du WR3
  const [P12]=k[2], o12=P12.offense;
  sub(P12,'off','WR3',`${ab(o12)}_TE2`,`${ab(o12)}_WR3`,'package'); P12.call.personnel='12';
  const nxt=k.find(([P],j)=>j>2&&P.offense===o12); sub(nxt[0],'off','WR3',`${ab(o12)}_WR3`,`${ab(o12)}_TE2`,'package');
  // CB3 en nickel sur une passe de l'autre attaque ; rotation ordinaire (DT3) sur la suivante
  const pn=k.find(([P],j)=>j>4&&P.call.type==='pass'&&P.offense!==o12)[0], dn=o12;
  sub(pn,'def','LB3',`${ab(dn)}_CB3`,`${ab(dn)}_LB3`,'package'); pn.call.defense=Object.assign({},pn.call.defense,{formation:'NICKEL'});
  const pf=k.find(([P])=>P.seq>pn.seq&&P.offense===pn.offense)[0]; sub(pf,'def','DT1',`${ab(dn)}_DT3`,`${ab(dn)}_DT1`,'fatigue');
  // QB2 en garbage time : la dernière série de l'attaque qui a le ballon en fin de match
  const last=k[k.length-1][0], og=last.offense, first=k.filter(([P])=>P.offense===og&&P.quarter===last.quarter).map(([P])=>P)[0]||last;
  sub(first,'off','QB',`${ab(og)}_QB2`,`${ab(og)}_QB1`,'garbage');
  // passeur / porteur QB1 ensuite : le QB2 (le moteur aligne le QB aligné)
  for(const [P] of k) if(P.seq>=first.seq&&P.offense===og){ const pp=P.players||{};
    if(pp.passer&&pp.passer.id===`${ab(og)}_QB1`) pp.passer={id:`${ab(og)}_QB2`,name:`Bench QB2 ${ab(og)}`};
    if(pp.carrier&&pp.carrier.id===`${ab(og)}_QB1`) pp.carrier={id:`${ab(og)}_QB2`,name:`Bench QB2 ${ab(og)}`}; }
  // snaps / énergie de fin de match (le site les lit dans le roster)
  F.game.rotation_model='rotations-1';
  for(const s of ['home','away']) F.game[s].roster.forEach(r=>{ r.energy=r.depth===2?95:70; });
  return {F,src:src+' (banc ajouté)'};
}
async function server(){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-banc-'));
  process.on('exit',()=>{ try{ fs.rmSync(data,{recursive:true,force:true}); }catch(e){} });   /* la copie des données ne reste pas dans le dossier temporaire */
  const w=fs.readdirSync(WEEKS).filter(w=>w.startsWith('week_')).sort().pop();
  fs.cpSync(path.join(WEEKS,w),path.join(data,'weeks',w),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(PORT)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1'}),stdio:'ignore'});
  for(let i=0;i<160;i++){ try{ const r=await fetch(`http://localhost:${PORT}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('le serveur ne démarre pas');
}

(async()=>{
  const {F,src}=feedAvecBanc();
  const S=F.plays.flatMap(P=>(P.subs||[]).map(x=>Object.assign({seq:P.seq},x)));
  console.log(`${src} · ${S.length} changements (package ${S.filter(x=>x.reason==='package').length}, fatigue ${S.filter(x=>x.reason==='fatigue').length}, garbage ${S.filter(x=>x.reason==='garbage').length})`);
  const srv=await server(), b=await chromium.launch({executablePath:EXE});
  try{
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
    await p.goto(`http://localhost:${PORT}/`,{waitUntil:'domcontentloaded',timeout:90000}); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:90000});
    const R=await p.evaluate(F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame();
      const RO={}; for(const s of ['home','away']) for(const r of F.game[s].roster) RO[r.id]=r;
      // alignement attendu, rejoué ici depuis les titulaires
      const PL={off:['LT','LG','C','RG','RT','QB','RB','TE','WR1','WR2','WR3'],def:['EDGE1','EDGE2','DT1','DT2','LB1','LB2','LB3','CB1','CB2','S1','S2']};
      const cur={};
      for(const s of ['home','away']){ const prof={}; F.game[s].roster.forEach(r=>(prof[r.pos]=prof[r.pos]||[]).push(r.id)); cur[s]={};
        for(const u of ['off','def']){ cur[s][u]={}; for(const pl of PL[u]){ const m=/^([A-Z]+?)(\d)?$/.exec(pl); cur[s][u][pl]=(prof[m[1]]||[])[(+(m[2]||1))-1]; } } }
      const OFF=[['C','C'],['LG','LG'],['RG','RG'],['LT','LT'],['RT','RT'],['TE','TE'],['QB','QB'],['RB','RB'],['WR1','WR1'],['WR2','WR2'],['WR3','WR3']];
      const out={ok:0,bad:[],tags:null,roleNickel:null,qbSpot:null,notes:[],lines:[],quiet:[]};
      const L=G.rotLineups(g);
      F.plays.forEach((P,k)=>{
        const t=P.call&&P.call.type; if(t!=='run'&&t!=='pass') return;
        const o=P.offense, d=o==='home'?'away':'home';
        for(const x of P.subs||[]) cur[x.side==='off'?o:d][x.side][x.pos]=x.in;
        const a=L.at[k];
        const same=PL.off.every(pl=>a[o].off[pl]===cur[o].off[pl])&&PL.def.every(pl=>a[d].def[pl]===cur[d].def[pl]);
        if(same) out.ok++; else out.bad.push(P.seq);
        const subs=P.subs||[];
        if(subs.length){
          G.rpSeek(g,k); g.paused=false; g.speed=1;
          for(let i=0;i<6000;i++){ G.stepGame(g,0.01); if(g.phase==='presnap') break; }
          for(let i=0;i<3000;i++){ const T=G.nameTags(g)||[]; if(T.length&&T[0].a>0.95) break; G.stepGame(g,0.01); }
          const sm=G.slotMap(g);
          const spot=OFF.map(([,pl])=>a[o].off[pl]);
          const ids=sm.off.filter(Boolean).map(x=>x.id).sort().join(), want=spot.filter(Boolean).sort().join();
          const offOk=ids===want;   /* les mêmes onze (le site déplace le porteur vers la place de course) */
          if(!offOk) out.bad.push('spot '+P.seq);
          if(subs.some(x=>x.pos==='WR3'&&x.reason==='package'&&RO[x.in].pos==='TE')){ const T=G.nameTags(g)||[];
            out.tags={want:RO[subs.find(x=>x.pos==='WR3').in].name.split(' ').slice(1).join(' '),got:T.map(x=>x.text),role:sm.roles.off[10]}; }
          const cb=subs.find(x=>x.side==='def'&&x.pos==='LB3'&&RO[x.in].pos==='CB');
          if(cb){ const i=sm.def.findIndex(x=>x&&x.id===cb.in); out.roleNickel={i,role:i>=0?sm.roles.def[i]:null};
            const h=G.playerCardHTML(g,'def',i); out.cardCB3=/Depth<\/span><b>Backup · /.test(h)&&/Snaps<\/span><b>\d+ \(\d+ %\)/.test(h); }
          const qb=subs.find(x=>x.pos==='QB'&&x.reason==='garbage');
          if(qb){ out.qbSpot=sm.off[6]&&sm.off[6].id===qb.in; }
          const note=/comes in/.test(G.rpFeedItem(g,P).text), line=(G.playLine(Object.assign({},g,{idx:k}),P)||{}).text||'';
          const notable=subs.some(x=>x.pos==='QB'&&x.reason==='garbage')||subs.some(x=>x.side==='def'&&x.pos==='CB2'&&RO[x.in].pos==='LB');
          if(notable){ out.notes.push(note); out.lines.push(/comes in|is in at quarterback|on the field/.test(line)); }
          else out.quiet.push(!note&&!/comes in|is in at quarterback/.test(line));
        }
      });
      // fin de match : énergie dans la fiche ; onglet Players (snaps)
      G.rpSeek(g,F.plays.length-1); g.paused=false; for(let i=0;i<20000&&!(g.status==='final'&&G.rpDone(g)>=F.plays.length);i++) G.stepGame(g,0.01);
      out.fin={status:g.status,done:G.rpDone(g),n:F.plays.length};
      g.idx=F.plays.length-1;
      const sm=G.slotMap(g), qbi=sm.off.findIndex(x=>x&&x.pos==='QB'), h=G.playerCardHTML(g,'off',qbi);
      out.finalCard=h.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(-300);
      out.energy=/Energy at the final whistle<\/span><b>\d+/.test(h); out.depthLine=/Depth<\/span><b>(Starter|Backup)/.test(h);
      const tot={home:0,away:0}; const c=L.cum[L.cum.length-1];
      out.snapsSum=['home','away'].every(s=>Object.values(c[s]).reduce((a,b)=>a+b,0)===11*(c.unit[s].off+c.unit[s].def));
      // tableau de profondeur (Teams, My team)
      const T={abbr:F.game.home.abbr||'HOME',roster:F.game.home.roster};
      const dc=G.depthChartHTML(T), box=document.createElement('div'); box.innerHTML=dc;
      out.depth={rows:box.querySelectorAll('tbody tr').length,b:box.querySelectorAll('.dc-p.b').length,s:box.querySelectorAll('.dc-p:not(.b)').length,
        qb2:/QB2 · /.test(dc)};
      return out;
    },F);
    check(!R.bad.length,`alignement action par action = celui des play.subs (${R.ok} actions${R.bad.length?' ; écarts '+R.bad.slice(0,5).join(', '):''})`);
    check(R.tags&&R.tags.got.includes(R.tags.want),`12 personnel : le 2e TE porte son nom avant le snap (${R.tags&&R.tags.want} · ${R.tags&&R.tags.got.join(', ')} · rôle ${R.tags&&R.tags.role})`);
    check(R.roleNickel&&R.roleNickel.i>=0&&R.roleNickel.role==='Nickel back',`nickel : le CB3 au poste de nickel back (${JSON.stringify(R.roleNickel)})`);
    check(R.cardCB3,'fiche en match du CB3 : « Depth : Backup · … », « Snaps n (x %) »');
    check(R.qbSpot===true,'garbage time : le QB2 au poste de QB');
    check(R.notes.length>0&&R.notes.every(Boolean)&&R.lines.every(Boolean),`play-by-play et commentateur : les changements marquants (${R.notes.length})`);
    check(R.quiet.length>0&&R.quiet.every(Boolean),`rien pour les packages et rotations ordinaires (${R.quiet.length} actions)`);
    check(R.energy&&R.depthLine,'fiche au coup de sifflet final : Depth, énergie'+(R.energy&&R.depthLine?'':' — '+JSON.stringify(R.fin)+' '+R.finalCard));
    check(R.snapsSum,'snaps : 11 par snap de chaque unité');
    check(R.depth.rows===11&&R.depth.b===11&&R.depth.s===25&&R.depth.qb2,`tableau de profondeur : 11 postes, 25 titulaires, 11 remplaçants (${JSON.stringify(R.depth)})`);
    // onglet Players du match (snaps)
    const tb=await p.$$('button'); for(const x of tb){ if((await x.innerText()).trim()==='Players'){ await x.click(); break; } }
    await p.waitForTimeout(500);
    const snapRows=await p.$$eval('table.pst',T=>{ const t=T.find(t=>/Snaps/i.test((t.querySelector('caption')||{}).textContent||'')); return t?t.querySelectorAll('tbody tr').length:0; });
    check(snapRows>=22,`onglet Players : tableau des snaps (${snapRows} joueurs)`);
    check(!errs.length,'aucune erreur JS'+(errs.length?' : '+errs.slice(0,3).join(' | '):''));
  } finally { await b.close(); srv.kill(); }
  console.log(fail?`ÉCHEC (${fail})`:'OK'); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
