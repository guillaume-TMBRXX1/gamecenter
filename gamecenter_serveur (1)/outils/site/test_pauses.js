// Pauses de retransmission (10/10/2026) — test navigateur (Playwright + serveur réel, crochet de test).
//   node outils/site/test_pauses.js            (depuis « gamecenter_serveur (1) » ; Python + fastapi/uvicorn, Playwright)
// 1. Replay complet d'un match, pas à pas (temps simulé) : les 3 pauses dans l'ordre (fin Q1, mi-temps, fin Q3), leurs
//    durées, rien d'ajouté ni de modifié dans les actions, reprise sur l'action suivante, écran final qui reste.
// 2. Écran de mi-temps et écran final : score, 3 cartes au plus par équipe, chaque valeur affichée = celle du Match centre
//    (computeStats), stats propres au poste ; finale : vainqueur, joueur du match ; panneaux latéraux utilisables.
// 3. « Resume now » en replay.
// 4. Direct (horloge du serveur) : page ouverte pendant la mi-temps d'un match, aucune action révélée pendant la pause,
//    reprise à l'heure, sans accélération ensuite.
let chromium; try{ ({chromium}=require('playwright')); }catch(e){ ({chromium}=require('/opt/node-tools/node_modules/playwright')); }
const fs=require('fs'), path=require('path'), os=require('os'), {spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..'), WEEKS=path.join(ROOT,'data','weeks');
const EXE=process.env.CHROMIUM_PATH||(fs.existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined);
const PLAY=6.5, BRK={q:10,half:40};
let fails=0; const ok=(c,msg)=>{ console.log((c?'  ok   ':'  FAIL ')+msg); if(!c){ fails++; process.exitCode=1; } };

function brkKind(P){ const A=P.after||{}; if(A.status==='half') return 'half'; return A.status==='live'&&P.clock_end!=null&&P.clock_end<=0?'q':null; }
function starts(P){ let off=0; return P.map((p,i)=>{ const s=i*PLAY+off; const b=brkKind(p); if(b) off+=BRK[b]; return s; }); }
const feedOf=(week,id)=>JSON.parse(fs.readFileSync(path.join(WEEKS,week,'games',id+'.json')));

async function server(at,port){
  const data=fs.mkdtempSync(path.join(os.tmpdir(),'gc-pauses-'));
  fs.cpSync(WEEKS,path.join(data,'weeks'),{recursive:true});
  const p=spawn('python3',['-m','uvicorn','serveur:app','--port',String(port)],{cwd:ROOT,env:Object.assign({},process.env,{GC_DATA:data,GC_TEST_HOOK:'1',GC_DEMO_AT:at}),stdio:'ignore'});
  for(let i=0;i<80;i++){ try{ const r=await fetch(`http://localhost:${port}/api/time`); if(r.ok) return p; }catch(e){} await new Promise(r=>setTimeout(r,250)); }
  p.kill(); throw new Error('server did not start');
}
async function page(b,port){
  const p=await b.newPage({viewport:{width:1440,height:1000}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(`http://localhost:${port}/`); await p.waitForFunction(()=>window.__gc&&window.__gc.season,null,{timeout:20000});
  return {p,errs};
}

(async()=>{
  const b=await chromium.launch({executablePath:EXE});
  const week='week_2026-10-05', gid='w2-r01', F=feedOf(week,gid);
  /* ---------- 1-3 : replay (any server time: the replay view never looks at the clock) ---------- */
  let srv=await server('2026-10-10T09:00:00+02:00',8131);
  try{
    const {p,errs}=await page(b,8131);
    console.log('Replay '+gid+' ('+F.plays.length+' plays)');
    const R=await p.evaluate(async F=>{
      const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame(); g.paused=false; g.speed=1;
      const before=JSON.stringify(g.plays), events=[], shots={};
      let t=0, cur=null;
      const dom=()=>{ const el=document.querySelector('.field.big .brk'); return el&&!el.hidden&&!el.classList.contains('out')?el:null; };
      /* what a break screen shows, checked against the match centre's stats at that moment */
      const check=kind=>{
        const el=dom(), st=G.computeStats(g,G.rpDone(g)), out={kind,visible:!!el,hs:g.hs,as:g.as,cards:[],errors:[]};
        if(!el) return out;
        out.title=el.querySelector('.brk-k').textContent; out.sub=(el.querySelector('.brk-sub')||{}).textContent||'';
        out.score=[...el.querySelectorAll('.brk-tm b')].map(x=>+x.textContent);
        out.potg=(el.querySelector('.brk-potg b')||{}).textContent||null;
        for(const side of ['away','home']){
          const sec=el.querySelector('.brk-side.'+side); if(!sec) continue;
          const top=G.brk.topPerformers(st,side,3), cards=[...sec.querySelectorAll('.brk-card')];
          out.cards.push({side,n:cards.length,expect:top.length});
          cards.forEach((c,i)=>{
            const x=top[i], name=c.querySelector('.brk-pl b').textContent;
            if(!x||x.p.name!==name){ out.errors.push(`${side} #${i+1}: ${name} ≠ ${x&&x.p.name}`); return; }
            const want=G.brk.perfStats(x.p,x.role).main.map(([l,v])=>l+'='+v).join(' ');
            const got=[...c.querySelectorAll('dl div')].map(d=>d.querySelector('dt').textContent+'='+d.querySelector('dd').textContent).join(' ');
            if(want!==got) out.errors.push(`${name}: ${got} ≠ ${want}`);
            /* the position's stats: QB passing, RB rushing, WR/TE receiving, K kicking, defenders tackles… */
            const pos=String(x.p.pos), first=got.split(' ')[0].split('=')[0];
            const exp={QB:'C/ATT',RB:'CAR',WR:'REC',TE:'REC',K:'FG'}[pos]||(['DT','EDGE','LB','CB','S'].includes(pos)?'TKL':null);
            if(exp&&first!==exp) out.errors.push(`${name} (${pos}) shows ${first}`);
            if(i&&top[i-1].v<x.v) out.errors.push('cards not ranked');
          });
        }
        /* side panels stay usable during the break */
        const tab=document.querySelector('#modal [data-st="players"]'); if(tab){ tab.click(); out.panel=!!document.querySelector('#modal .st-body table'); document.querySelector('#modal [data-st="team"]').click(); }
        return out;
      };
      for(let i=0;i<60000&&!(g.status==='final'&&g.paused);i++){
        G.stepGame(g,0.05); t+=0.05;
        const k=g.brk?g.brk.kind:null;
        if(k!==(cur&&cur.kind)){
          if(cur){ cur.dur=+(t-cur.t0).toFixed(2); cur.after={idx:g.idx,status:g.status,q:g.cur&&g.cur.quarter,phase:g.phase}; events.push(cur); }
          cur=k?{kind:k,q:g.brk.q,idx:g.idx,t0:t,pause0:g.pause,playQ:g.cur.quarter,clockEnd:g.cur.clock_end,status:g.cur.after.status}:null;
          if(k){ G.updateGameUI(g); await new Promise(r=>setTimeout(r,30)); if(k==='half'||k==='final') shots[k]=check(k); if(k==='q'&&!shots.q) shots.q=check('q'); }
        }
        if(k&&k!=='final'&&i%40===0&&g.idx!==cur.idx) cur.moved=true;   /* nothing plays during a break */
      }
      if(cur) events.push(Object.assign(cur,{dur:null,still:g.status==='final'&&g.paused}));
      const intact=JSON.stringify(g.plays)===before;
      /* final screen: hide it, the field is free; the tab brings it back */
      G.updateGameUI(g); await new Promise(r=>setTimeout(r,30));
      document.querySelector('.field.big [data-brk="hide"]').click(); await new Promise(r=>setTimeout(r,600));
      const hidden=document.querySelector('.field.big .brk').hidden, tab=!document.querySelector('.field.big .brk-tab').hidden;
      document.querySelector('.field.big .brk-tab').click(); G.updateGameUI(g); await new Promise(r=>setTimeout(r,50));
      const back=!document.querySelector('.field.big .brk').hidden;
      return {events,shots,intact,hidden,tab,back,n:g.plays.length};
    },F);
    const E=R.events, kinds=E.map(e=>e.kind+(e.q||'')).join(' ');
    ok(kinds==='q1 half2 q3 final4', `breaks in order: ${kinds}`);
    for(const e of E.filter(e=>e.kind!=='final')){
      /* the page's own animation loop also steps the replay while the test waits for the DOM (a few frames): the
         programmed length is exact, the measured one within 0.2 s */
      ok(e.pause0===BRK[e.kind]&&e.dur>=BRK[e.kind]-0.2&&e.dur<=BRK[e.kind]+0.06, `${e.kind} Q${e.q}: ${e.pause0} s programmed, ${e.dur} s measured (expected ${BRK[e.kind]})`);
      ok(e.clockEnd===0&&(e.kind==='half'?e.status==='half':e.status==='live'), `${e.kind} Q${e.q}: starts on the play ending the period (play ${e.idx})`);
      ok(!e.moved&&e.after.idx===e.idx+1&&e.after.status==='live'&&e.after.q===e.q+1&&e.after.phase==='presnap', `${e.kind} Q${e.q}: resumes on play ${e.after.idx}, Q${e.after.q}, ${e.after.status}`);
    }
    ok(E[E.length-1].kind==='final'&&E[E.length-1].still, 'final screen stays (replay stopped on it)');
    ok(R.intact, `plays untouched (${R.n}, same JSON before and after)`);
    for(const k of ['q','half','final']){ const s=R.shots[k]; if(!s){ ok(false,k+' screen captured'); continue; }
      ok(s.visible&&s.score[0]===s.as&&s.score[1]===s.hs, `${k}: screen shown, score ${s.as}-${s.hs} (“${s.title}”)`);
      if(k!=='q'){ ok(s.cards.length===2&&s.cards.every(c=>c.n===c.expect&&c.n<=3&&c.n>0), `${k}: cards ${s.cards.map(c=>c.side+' '+c.n).join(', ')}`);
        ok(!s.errors.length, `${k}: every card value = match centre (${s.errors.slice(0,3).join(' | ')||'ok'})`);
        ok(s.panel, `${k}: match centre usable during the screen`); }
      else ok(s.cards.length===0, 'q: short break, score only');
    }
    const fin=R.shots.final, win=F.plays[F.plays.length-1].after.score;
    ok(fin&&fin.potg&&(win.home===win.away?fin.sub==='Tie game':/ win$/.test(fin.sub)), `final: “${fin&&fin.sub}”, player of the game ${fin&&fin.potg}`);
    ok(R.hidden&&R.tab&&R.back, 'final: “Show the field” hides it, the tab brings it back');
    /* engine's own final totals (game.player_stats, not shown on the site) agree with the cards' defensive stats */
    const PS=F.game.player_stats||{};
    const defOk=await p.evaluate(F=>{ const G=window.__gc, g=G.replayGame(), st=G.computeStats(g,g.plays.length), bad=[];
      for(const [id,s] of Object.entries(F.game.player_stats||{})) if(s.tackles!=null){ const side=id.startsWith(F.game.home.abbr+'_')?'home':'away';
        const p=Object.values(st.pl[side]).find(x=>x.name===s.name); const d=p&&p.def||{tk:0,sk:0,i:0,pd:0};
        if(d.tk!==s.tackles||d.sk!==s.sacks||d.i!==s.interceptions||d.pd!==s.passes_defended) bad.push(s.name); }
      return bad; },F);
    ok(Object.keys(PS).length>0&&!defOk.length, `defensive stats = engine's player_stats (${defOk.join(', ')||'all'})`);
    /* 3. Resume now */
    const rs=await p.evaluate(async F=>{ const G=window.__gc; G.openReplayFeed(F); const g=G.replayGame();
      const q1=F.plays.findIndex(P=>P.after.status==='live'&&P.clock_end===0);
      g.idx=0; for(let i=0;i<30000&&!g.brk;i++) G.stepGame(g,0.05);
      const at=g.idx; G.updateGameUI(g); await new Promise(r=>setTimeout(r,30));
      document.querySelector('.field.big [data-brk="resume"]').click();
      return {q1,at,after:g.idx,brk:!!g.brk,pause:g.pause}; },F);
    ok(rs.at===rs.q1&&rs.after===rs.q1+1&&!rs.brk, `Resume now: break after play ${rs.at} skipped, on play ${rs.after}`);
    ok(!errs.length, 'no page error'+(errs.length?': '+errs.slice(0,2).join(' | '):''));
    await p.close();
  } finally { srv.kill(); }

  /* ---------- 4 : live, server clock inside the halftime of w2-r01 ---------- */
  const S=starts(F.plays), h=F.plays.findIndex(P=>brkKind(P)==='half'), ko=Date.parse(F.game.kickoff);
  const brkStart=ko+(S[h]+PLAY)*1000, brkEnd=brkStart+BRK.half*1000;
  srv=await server(new Date(brkEnd-14000).toISOString(),8132);
  try{
    const {p,errs}=await page(b,8132);
    console.log(`Live ${gid}: page opened 14 s before the end of halftime (play ${h})`);
    const L=await p.evaluate(async gid=>{ const G=window.__gc, g=G.byId['s-'+gid];
      if(!g) return {missing:true};
      G.updateGameUI(g);
      const el=document.querySelector(`.field [data-g="s-${gid}"][data-f="brk"]`);
      const a={idx:g.idx,brk:g.brk&&g.brk.kind,pause:+g.pause.toFixed(1),shown:!!el&&!el.hidden,label:el&&el.textContent.replace(/\s+/g,' ').trim().slice(0,60),n:g.plays.length};
      const d1=await (await fetch('/api/delta?have='+gid+':'+g.plays.length)).json();
      await new Promise(r=>setTimeout(r,3000));
      const d2=await (await fetch('/api/delta?have='+gid+':'+g.plays.length)).json();
      a.newPlays=[d1.plays[gid],d2.plays[gid]].filter(Boolean).length;
      return a; },gid);
    /* a real mouse click on the tile during the break opens the big screen, with the full halftime screen */
    let M=null;
    if(!L.missing){ await p.click(`.tile [data-open="s-${gid}"]`,{timeout:5000}).catch(()=>{}); await p.waitForTimeout(800);
      M=await p.evaluate(()=>{ const el=document.querySelector('#modal:not([hidden]) .field.big .brk'); return {open:!!el&&!el.hidden,cards:el?el.querySelectorAll('.brk-card').length:0,resume:!!(el&&el.querySelector('[data-brk="resume"]'))}; });
      await p.evaluate(()=>{ const c=document.querySelector('#modal [data-close]'); if(c) c.click(); }); }
    const L2=L.missing?L:await p.evaluate(async gid=>{ const G=window.__gc, g=G.byId['s-'+gid], a={};
      /* end of the break: the board resumes with the next play, at clock speed */
      let resumed=null, maxSpeed=0; const t0=performance.now(); a.left=g.pause;
      while(performance.now()-t0<22000){ await new Promise(r=>setTimeout(r,250)); maxSpeed=Math.max(maxSpeed,g.speed);
        if(!g.brk&&resumed===null) resumed={after:+((performance.now()-t0)/1000).toFixed(1),idx:g.idx,q:g.cur.quarter,status:g.status}; }
      a.resumed=resumed; a.maxSpeed=maxSpeed; a.idxEnd=g.idx; return a; },gid);
    Object.assign(L,L2);
    if(L.missing){ ok(false,'live board s-'+gid+' on the home page'); }
    else{
      ok(L.brk==='half'&&L.idx===h&&L.shown, `halftime on screen at load (play ${L.idx}, ${L.label})`);
      ok(L.pause>14&&L.pause<=14+PLAY+1, `remaining ${L.pause} s (break end + one play: the server sends the next play then)`);
      ok(L.newPlays===0, 'no play revealed by the server during the break');
      ok(M&&M.open&&M.cards>0&&!M.resume, `tile clicked during the break: big screen with the halftime screen (${M&&M.cards} cards, no “Resume now” live)`);
      ok(L.resumed&&L.resumed.idx===h+1&&L.resumed.q===3&&L.resumed.status==='live'&&Math.abs(L.resumed.after-L.left)<=1.5, `resumed on play ${L.resumed&&L.resumed.idx} (Q${L.resumed&&L.resumed.q}) after ${L.resumed&&L.resumed.after} s (${L.left&&L.left.toFixed(1)} s announced)`);
      ok(L.maxSpeed<=1.31, `no fast catch-up after the break (max speed ${L.maxSpeed})`);
    }
    ok(!errs.length, 'no page error'+(errs.length?': '+errs.slice(0,2).join(' | '):''));
    await p.close();
  } finally { srv.kill(); }
  await b.close();
  console.log(fails?`${fails} FAILED`:'ALL PASSED');
})().catch(e=>{ console.error(e); process.exit(1); });
