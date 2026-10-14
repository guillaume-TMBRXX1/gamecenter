/* GameCenter Audio System — CommentaryCues (V0.2)
   Which recorded call fits a moment. The page still writes the full line (names, yards, score) for the
   caption; the voice says a generic call from the catalogue (pre-generated offline, no player names).
   A moment → 1 or 2 cues (e.g. the touchdown, then "that's the ball game"); a cue → one variant:
     • tone from the moment's importance: calm < .45 ≤ excited < .75 ≤ huge (falls back to a neighbour tone);
     • tags narrow it: strict tags (fd, nogain, goal, q2/q3/q4, ot) must match, soft ones (pass, run, lead)
       only add variety;
     • controlled choice: a hash of game | play | cue picks the variant — every viewer hears the same call —
       skipping the last ones heard in that game for that cue (no back-to-back repeats). */
(function(L){
'use strict';
const num=(v,f)=>(typeof v==='number'&&isFinite(v))?v:f;
const STRICT=new Set(['fd','nogain','goal','q2','q3','q4','ot']);
const TIER_ORDER={calm:['calm','excited','huge'],excited:['excited','huge','calm'],huge:['huge','excited','calm']};
function hsh(s){ let h=2166136261; for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }
const tierOf=imp=>imp>=.75?'huge':imp>=.45?'excited':'calm';

/* ---------- moment → cues (same conditions as the page's line writers) ---------- */
function resolveCues(c,P,g){
  const r=c.result, gain=c.gain, ty=c.callType, out=[], T=[];
  if(ty==='pass') T.push('pass'); if(ty==='run') T.push('run');
  if(c.isLeadChange||c.isGameWinning) T.push('lead');
  switch(r){
    case 'touchdown': out.push(ty==='kickoff'?{cue:'KICK_RETURN_TD',tags:[]}:{cue:'TOUCHDOWN',tags:T}); break;   /* bloc 2 : TD sur retour */
    case 'interception': out.push({cue:'INTERCEPTION',tags:T}); break;
    case 'fumble_lost': out.push({cue:'FUMBLE',tags:T}); break;
    case 'field_goal_good': out.push({cue:'FIELD_GOAL_GOOD',tags:T}); break;
    case 'field_goal_missed': out.push({cue:'FIELD_GOAL_MISS',tags:T}); break;
    case 'safety': out.push({cue:'SAFETY',tags:T}); break;
    case 'pat_good': out.push({cue:'PAT_GOOD',tags:[]}); break;          /* bloc 2 : transformation */
    case 'pat_missed': out.push({cue:'PAT_MISS',tags:[]}); break;
    case 'two_point_good': out.push({cue:'TWO_POINT_GOOD',tags:[]}); break;
    case 'two_point_failed': out.push({cue:'TWO_POINT_FAIL',tags:[]}); break;
    case 'sack': out.push({cue:'SACK',tags:T}); break;
    case 'complete':
      if(gain>=20) out.push({cue:'BIG_PLAY',tags:T.concat('pass')});
      else if(gain<=0) out.push({cue:'PASS_COMPLETE',tags:T.concat('nogain')});
      else out.push({cue:'PASS_COMPLETE',tags:c.isFirstDown?T.concat('fd'):T}); break;
    case 'incomplete': out.push({cue:'INCOMPLETE',tags:T}); break;
    case 'run':
      if(gain>=15) out.push({cue:'BIG_PLAY',tags:T.concat('run')});
      else if(gain<=0) out.push({cue:'RUN_STUFFED',tags:T});
      else out.push({cue:'RUN',tags:c.isFirstDown?T.concat('fd'):T}); break;
    case 'punt': { const pr=P.punt_return;   /* 12.2 sexdecies : punt avec retour */
      out.push(pr&&pr.td?{cue:'TOUCHDOWN',tags:[]}:pr&&pr.result==='return'&&(+pr.return||0)>=30?{cue:'KICK_RETURN_BIG',tags:[]}:{cue:'PUNT',tags:T}); } break;
    case 'kickoff': if(g&&g.idx!==0){ const kr=P.kick_return;   /* bloc 2 : coup d'envoi avec retour */
      out.push(kr&&kr.touchback?{cue:'TOUCHBACK',tags:[]}:kr&&(+kr.return||0)>=40?{cue:'KICK_RETURN_BIG',tags:[]}:{cue:'KICKOFF',tags:T}); } break;
  }
  if(c.status==='half') out.push({cue:'HALFTIME',tags:[],tier:'calm'});
  if(c.status==='final'){
    const ot=c.quarter>4?['ot']:[], s=c.score;
    out.push(s.home>s.away?{cue:'VICTORY',tags:ot}:s.away>s.home?{cue:'DEFEAT',tags:ot}:{cue:'TIE',tags:[],tier:'calm'});
  }
  return out.slice(-2);
}
const ADJ={hurry:'ADJ_HURRY',clock:'ADJ_CLOCK',shelve:'ADJ_SHELVE',shelve_form:'ADJ_SHELVE_FORM',d_deep:'ADJ_D_DEEP',d_heat:'ADJ_D_HEAT',
  d_run:'ADJ_D_RUN',d_press:'ADJ_D_PRESS',d_noblitz:'ADJ_D_NOBLITZ',d_prevent:'ADJ_D_PREVENT',d_attack:'ADJ_D_ATTACK',
  /* engine block D (12.2 octies): game plans, adjustments and counter-adjustments */
  plan_o:'ADJ_GAMEPLAN',plan_d:'ADJ_GAMEPLAN',o_quick:'ADJ_O_QUICK',o_protect:'ADJ_O_PROTECT',o_away:'ADJ_O_AWAY',
  d_bracket:'ADJ_D_BRACKET',d_rotate:'ADJ_D_ROTATE',d_disguise:'ADJ_D_DISGUISE'};
function snapCues(c,P){
  const out=[], A=Array.isArray(P.adjust)?P.adjust:[];
  for(const a of A){ const k=ADJ[a&&a.kind]; if(k){ out.push({cue:k,tags:[],tier:'calm'}); break; } }
  const ty=c.callType, gd=c.goalDist, goal=P.to_go>=gd;
  if(ty==='field_goal') out.push({cue:'FIELD_GOAL_UNIT',tags:[],tier:'calm'});
  else if(ty!=='punt'&&ty!=='kickoff'){
    if(P.down===4) out.push({cue:'FOURTH_DOWN_ATTEMPT',tags:[]});
    else if(P.down===3) out.push({cue:'THIRD_DOWN',tags:goal?['goal']:[],tier:'calm'});
    else if(gd<=20&&P.down===1) out.push({cue:goal?'FIRST_AND_GOAL':'RED_ZONE_FIRST',tags:[],tier:'calm'});
  }
  return out.slice(0,2);
}
function quarterCue(q){ return q>4?{cue:'OVERTIME',tags:[]}:{cue:'QUARTER_START',tags:['q'+q],tier:'calm'}; }
function introCue(g){ const P=g.cur; return g.mode==='replay'?{cue:'INTRO_REPLAY',tags:[]}:(!P||(g.idx<=1&&g.hs+g.as===0))?{cue:'INTRO_LIVE',tags:[]}:{cue:'INTRO_JOIN',tags:[]}; }

/* ---------- cue → variant ---------- */
class CuePicker{
  constructor(){ this.idx=null; this.recent=new Map(); }
  index(assets){                                   /* manifest commentary entries, grouped by cue */
    const m=new Map(); for(const a of assets||[]) if(a.cat==='commentary'){ (m.get(a.cue)||m.set(a.cue,[]).get(a.cue)).push(a); }
    this.idx=m; return m.size;
  }
  ready(){ return !!(this.idx&&this.idx.size); }
  candidates(cue,tier,tags){
    const all=this.idx&&this.idx.get(cue); if(!all) return [];
    const have=new Set(tags||[]);
    for(const t of TIER_ORDER[tier]||TIER_ORDER.calm){
      const ok=all.filter(a=>a.tier===t&&(a.tags||[]).every(x=>have.has(x))); if(!ok.length) continue;
      const strict=ok.filter(a=>(a.tags||[]).some(x=>STRICT.has(x)));
      return strict.length?strict:ok;
    }
    return [];
  }
  /* commit=false: what would be picked (prefetch), without touching the no-repeat memory */
  pick(gameId,seq,req,imp,commit){
    const tier=req.tier||tierOf(num(imp,0)), C=this.candidates(req.cue,tier,req.tags); if(!C.length) return null;
    const key=gameId+'|'+req.cue, rec=this.recent.get(key)||[], keep=Math.min(4,C.length-1);
    const fresh=C.filter(a=>!rec.slice(-keep).includes(a.id)), pool=fresh.length?fresh:C;
    const a=pool[hsh(gameId+'|'+seq+'|'+req.cue)%pool.length];
    if(commit){ rec.push(a.id); if(rec.length>8) rec.shift(); this.recent.set(key,rec); if(this.recent.size>64) this.recent.delete(this.recent.keys().next().value); }
    return a;
  }
}
L.CommentaryCues={resolveCues,snapCues,quarterCue,introCue,tierOf,CuePicker,hsh};
})(window.GCAudioLib=window.GCAudioLib||{});
