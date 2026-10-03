/* GameCenter Audio System — AudioEventMapper (V0.1)
   Turns what the engine published (one GameFeed play + the board's state) into audio events with
   their context. Pure functions: no sound, no DOM, no network — the engine is never called, it is
   only read. Point of view: HOME is the stadium (the crowd cheers the home team).

   Context (every event of a batch shares it):
   { gameId, seq, phase:'snap'|'resolve', mode, speed, result, callType, gain, status, quarter, timeRemaining,
     team:'HOME'|'AWAY' (side that made the play — the defence for a takeaway), offense, defense,
     score:{home,away}, scoreBefore:{home,away}, down, toGo, goalDist, isRedZone, isLateGame, isOvertime,
     isCloseGame, isTieGame, isLeadChange, isGameTying, isGameWinning, isFirstDown,
     wpBefore, wpAfter, wpSwing, importance (0..1), players:{carrier,passer,defender} } */
(function(L){
'use strict';
const num=(v,f)=>(typeof v==='number'&&isFinite(v))?v:f;
const clamp=(v,a,b)=>v<a?a:(v>b?b:v);
const lead=s=>s.home>s.away?'home':s.away>s.home?'away':null;

function base(g,P,phase){
  const off=P.offense==='away'?'away':'home', def=off==='home'?'away':'home';
  const x=num(P.los_x,60), goalDist=Math.max(1,Math.round(off==='home'?110-x:x-10));
  const q=num(P.quarter,1), qs=num(g.qs,900), tr=num(phase==='snap'?P.clock_start:P.clock_end,0);
  const after=(P.after&&P.after.score)||{home:num(g.hs,0),away:num(g.as,0)};
  let before={home:0,away:0};
  const i=Array.isArray(g.plays)?g.plays.indexOf(P):-1;
  if(i>0&&g.plays[i-1].after&&g.plays[i-1].after.score) before=g.plays[i-1].after.score;
  else if(i<0&&phase==='snap') before=after;
  const score=phase==='snap'?before:after;
  const late=q>4||(q>=4&&tr<=qs/2);
  const pl=P.players||{};
  return { gameId:g.id, seq:P.seq, phase, mode:g.mode||'replay', speed:num(g.speed,1),
    result:P.result, callType:P.call&&P.call.type, gain:num(P.gain,0), status:P.after&&P.after.status,
    quarter:q, timeRemaining:tr, offense:off, defense:def, team:off==='home'?'HOME':'AWAY',
    score:{home:score.home,away:score.away}, scoreBefore:{home:before.home,away:before.away},
    down:P.down, toGo:P.to_go, goalDist, isRedZone:goalDist<=20, isLateGame:late, isOvertime:q>4,
    isCloseGame:Math.abs(score.home-score.away)<=8, isTieGame:score.home===score.away,
    players:{carrier:pl.carrier&&pl.carrier.name||null,passer:pl.passer&&pl.passer.name||null,defender:pl.defender&&pl.defender.name||null} };
}

/* At the snap. prev = {quarter, seq} of the last play heard on this broadcast (0 / -1 when none). */
function mapSnap(g,P,prev){
  const c=base(g,P,'snap'), ev=[], pq=prev&&prev.quarter||0, ps=prev&&prev.seq!=null?prev.seq:-1;
  const jump=ps>=0&&P.seq!==ps+1&&P.seq!==ps;                     /* a seek: no "start of the quarter" */
  c.quarterChanged=c.quarter!==pq&&!jump&&!!pq;
  if(c.quarterChanged){ ev.push('QUARTER_END'); ev.push(c.quarter>4?'OVERTIME':'QUARTER_START'); }
  const ty=c.callType;
  ev.push(ty==='punt'||ty==='field_goal'||ty==='kickoff'?'KICK_SNAP':'SNAP');
  if(ty==='run'||ty==='pass'){ if(P.down===3) ev.push('THIRD_DOWN'); if(P.down===4) ev.push('FOURTH_DOWN_ATTEMPT'); if(c.isRedZone) ev.push('RED_ZONE'); }
  if(Array.isArray(P.adjust)&&P.adjust.length) ev.push('COORD_ADJUST');
  c.wpBefore=c.wpAfter=num(P.win_prob_home,null); c.wpSwing=0;
  c.importance=importance(c,ev);
  return {ctx:c,events:ev};
}

/* After the play. wpBefore: the board's win probability before this play (null if unknown). */
function mapResolve(g,P,wpBefore){
  const c=base(g,P,'resolve'), ev=[], r=c.result, ty=c.callType, gain=c.gain;
  c.isFirstDown=/1st down/i.test(String(P.text||''));
  const lb=lead(c.scoreBefore), la=lead(c.score), scored=c.score.home!==c.scoreBefore.home||c.score.away!==c.scoreBefore.away;
  c.isLeadChange=scored&&!!la&&la!==lb;
  c.isGameTying=scored&&!la&&!!lb;
  c.isGameWinning=c.isLeadChange&&c.isLateGame;
  const takeaway=r==='interception'||r==='fumble_lost';
  if(takeaway){ c.team=c.defense==='home'?'HOME':'AWAY'; }
  switch(r){
    case 'touchdown': ev.push('TOUCHDOWN'); break;
    case 'interception': ev.push('INTERCEPTION','TURNOVER'); break;
    case 'fumble_lost': ev.push('FUMBLE','TURNOVER'); break;
    case 'sack': ev.push('SACK'); break;
    case 'field_goal_good': ev.push('FIELD_GOAL_GOOD'); break;
    case 'field_goal_missed': ev.push('FIELD_GOAL_MISS'); break;
    case 'punt': ev.push('PUNT'); break;
    case 'kickoff': ev.push('KICKOFF'); break;
    case 'incomplete': ev.push('INCOMPLETE'); break;
    case 'complete': ev.push('PASS_COMPLETE'); break;
    case 'run': ev.push('RUN'); break;
  }
  if(P.possession_change==='downs') ev.push('TURNOVER_ON_DOWNS','TURNOVER');
  if(c.isFirstDown&&r!=='touchdown') ev.push('FIRST_DOWN');
  if(P.highlight==='BIG'||(ty==='pass'&&r==='complete'&&gain>=20)||(ty==='run'&&r==='run'&&gain>=15)) ev.push('BIG_PLAY');
  if(c.isLeadChange) ev.push('LEAD_CHANGE');
  if(c.status==='half') ev.push('HALFTIME');
  if(c.status==='final'){
    ev.push('GAME_END');
    const w=lead(c.score);
    ev.push(w==='home'?'VICTORY':w==='away'?'DEFEAT':'TIE');      /* HOME = the stadium's point of view */
  }
  const wa=num(P.win_prob_home,null);
  c.wpBefore=wpBefore==null?null:wpBefore; c.wpAfter=wa; c.wpSwing=wa!=null&&wpBefore!=null?Math.abs(wa-wpBefore):0;
  c.importance=importance(c,ev);
  return {ctx:c,events:ev};
}

/* 0..1 — how big the moment is: the event, then the game situation */
const WEIGHT={TOUCHDOWN:.55,INTERCEPTION:.5,FUMBLE:.5,TURNOVER_ON_DOWNS:.4,FIELD_GOAL_GOOD:.35,FIELD_GOAL_MISS:.35,SACK:.3,BIG_PLAY:.35,
  FOURTH_DOWN_ATTEMPT:.3,THIRD_DOWN:.15,FIRST_DOWN:.1,PUNT:.08,INCOMPLETE:.08,PASS_COMPLETE:.08,RUN:.08,SNAP:.05,KICK_SNAP:.08,KICKOFF:.08,
  HALFTIME:.4,GAME_END:.35,VICTORY:.55,DEFEAT:.3,TIE:.45,QUARTER_START:.2,QUARTER_END:.2,OVERTIME:.8,RED_ZONE:.2,COORD_ADJUST:.1,LEAD_CHANGE:.5};
function importance(c,ev){
  let v=0; for(const e of ev) v=Math.max(v,WEIGHT[e]||0);
  /* the same play matters more late: Q1-Q2 ×.25, Q3 ×.5, last half of Q4 and overtime ×1 */
  const late=c.isLateGame?1:c.quarter>=3?.5:.25;
  if(c.isGameWinning) v+=.25; else if(c.isLeadChange||c.isGameTying) v+=.15*late;
  if(c.isCloseGame) v+=.08*late;
  if(c.isOvertime) v+=.1;
  if(c.wpSwing) v+=Math.min(.15,c.wpSwing*.4);
  /* the final call: a close finish is a big moment, a blowout is not */
  if(c.isCloseGame&&(ev.includes('VICTORY')||ev.includes('DEFEAT'))) v+=.2;
  return Math.round(clamp(v,0,1)*100)/100;
}

L.AudioEventMapper={mapSnap,mapResolve,importance,EVENTS:Object.keys(WEIGHT)};
})(window.GCAudioLib=window.GCAudioLib||{});
