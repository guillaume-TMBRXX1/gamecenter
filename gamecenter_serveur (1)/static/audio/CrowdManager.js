/* GameCenter Audio System — CrowdManager (V0.3)
   The stadium, recorded (pre-generated offline with ElevenLabs Sound Effects, manifest cat "crowd"):
     • beds, looped with a crossfade so the seam is never heard: idle murmur, and anticipation (3rd / 4th down,
       home team in the red zone, a close finish) — the bed follows the game, slowly;
     • reactions, one-shot: small / medium / huge cheer, boo, disappointment, touchdown, interception, victory.
   The crowd is the HOME crowd: a home touchdown makes the stadium explode, a visiting one gets booed; a
   takeaway by the home defense is cheered, one by the visitors draws a groan. Size follows the moment's
   importance (a routine first down is polite applause; a go-ahead touchdown late is the loudest moment).
   At most 2 reactions at once: a bigger one pushes the older one down. */
(function(L){
'use strict';
const XF=1.2;                                     /* bed loop crossfade, seconds */
/* makeup gains, measured on the generated files: beds −28 LUFS, reactions −23 LUFS, voice ≈ −17 LUFS.
   Beds sit ≈ 7 dB under the voice, reactions reach the voice's level (plenty of headroom: peaks −10 to −15 dBFS). */
const BED_MAKEUP=2.5, REACT_MAKEUP=2.2;
function hsh(s){ let h=2166136261; for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }
const RANK={cheer_small:1,disappointment:1,boo:2,cheer_medium:2,react_int:3,cheer_huge:3,react_td:4,react_victory:5};

/* ---------- what the home crowd does (pure: context + events → [kind, delay, level]) ---------- */
function reactions(c,ev){
  const has=e=>ev.includes(e), homeOff=c.offense==='home', imp=c.importance||0, big=imp>=.75, mid=imp>=.45, out=[];
  const late3=(c.down===3||c.down===4);
  if(has('GAME_END')){
    if(has('VICTORY')) out.push(['react_victory',.2,1]);
    else if(has('DEFEAT')) out.push([c.isCloseGame?'disappointment':'boo',.2,1]);
    else out.push(['disappointment',.2,.8]);
    return out;                                    /* the final reaction covers the last play */
  }
  if(has('TOUCHDOWN')) out.push(homeOff?['react_td',.1,big?1:.85]:[mid?'boo':'disappointment',.25,mid?1:.8]);
  else if(has('INTERCEPTION')||has('FUMBLE')) out.push(!homeOff?['react_int',.15,big?1:.85]:['disappointment',.15,1]);
  else if(has('TURNOVER_ON_DOWNS')) out.push(!homeOff?['cheer_medium',.15,1]:['disappointment',.15,1]);
  else if(has('FIELD_GOAL_GOOD')) out.push(homeOff?[big?'cheer_huge':'cheer_medium',.2,1]:['disappointment',.25,.7]);
  else if(has('FIELD_GOAL_MISS')) out.push(homeOff?['disappointment',.2,1]:['cheer_medium',.2,.9]);
  else if(has('SAFETY')) out.push(!homeOff?['cheer_huge',.15,1]:['disappointment',.15,1]);
  else if(has('SACK')) out.push(!homeOff?['cheer_medium',.1,big?1:.85]:['disappointment',.15,.8]);
  else if(has('BIG_PLAY')) out.push(homeOff?[big?'cheer_huge':'cheer_medium',.1,1]:['disappointment',.2,.8]);
  else if(has('FIRST_DOWN')){ if(homeOff) out.push(['cheer_small',.15,mid?1:.7]); }
  else if(has('INCOMPLETE')&&late3) out.push(homeOff?['disappointment',.15,.7]:['cheer_small',.15,.8]);
  else if(has('RUN')&&c.gain<=0&&!homeOff&&late3) out.push(['cheer_small',.15,.8]);
  if(has('HALFTIME')&&c.score.home>c.score.away) out.push(['cheer_small',.9,.8]);
  return out.slice(0,2);
}
/* the bed for the next play, decided at the snap */
function mood(c,ev){
  const homeOff=c.offense==='home';
  if(ev.includes('FOURTH_DOWN_ATTEMPT')||ev.includes('THIRD_DOWN')) return 'anticipation';
  if(ev.includes('RED_ZONE')&&homeOff) return 'anticipation';
  if(c.isLateGame&&c.isCloseGame) return 'anticipation';
  return 'idle';
}

class CrowdManager{
  constructor(mixer,assets){ this.mx=mixer; this.assets=assets; this.byKind=new Map(); this.beds={}; this.mood='idle'; this.level=0; this.live=[]; this.n=0; }
  index(manifest){ this.byKind=new Map(); for(const a of (manifest&&manifest.assets)||[]) if(a.cat==='crowd'){ (this.byKind.get(a.kind)||this.byKind.set(a.kind,[]).get(a.kind)).push(a); } return this.byKind.size; }
  /* recorded crowd is used once its idle bed and some reactions exist */
  ready(){ return this.byKind.has('bed_idle')&&this.byKind.size>=3; }
  ids(lite){ const out=[]; for(const [k,list] of this.byKind){ if(lite&&k==='bed_anticipation') continue; for(const a of (lite?list.slice(0,1):list)) out.push(a.id); } return out; }
  /* ---------- beds ---------- */
  bedFor(kind){
    let b=this.beds[kind]; if(b) return b;
    const a=(this.byKind.get('bed_'+kind)||[])[0]; if(!a||!this.mx.ctx) return null;
    const g=this.mx.ctx.createGain(); g.gain.value=0; g.connect(this.mx.input('crowd'));
    b=this.beds[kind]={a,g,timer:0,srcs:new Set(),on:false}; return b;
  }
  loop(b,t){                                       /* one pass of the bed, the next one starts XF before its end */
    const ac=this.mx.ctx, buf=this.assets.peek(b.a.id);
    if(!b.on) return;
    if(!buf){ b.timer=setTimeout(()=>this.loop(b,ac.currentTime+.05),400); return; }
    const d=buf.duration, x=Math.min(XF,d/4), s=ac.createBufferSource(), e=ac.createGain();
    s.buffer=buf; e.gain.setValueAtTime(0,t); e.gain.linearRampToValueAtTime(1,t+x); e.gain.setValueAtTime(1,t+d-x); e.gain.linearRampToValueAtTime(0,t+d);
    s.connect(e); e.connect(b.g); s.start(t); s.stop(t+d+.05); b.srcs.add(s);
    s.onended=()=>{ b.srcs.delete(s); try{ s.disconnect(); e.disconnect(); }catch(err){} };
    const next=t+d-x; b.timer=setTimeout(()=>this.loop(b,next),Math.max(50,(next-ac.currentTime-.5)*1000));
  }
  setBed(kind,on){
    const b=this.bedFor(kind); if(!b) return;
    if(on&&!b.on){ b.on=true; this.loop(b,this.mx.ctx.currentTime+.05); }
    else if(!on&&b.on){ b.on=false; clearTimeout(b.timer); const stop=this.mx.ctx.currentTime+2.5; for(const s of b.srcs){ try{ s.stop(stop); }catch(e){} } }
  }
  /* level: the page's crowd level for the game on air (0 = crowd off); beds crossfade slowly with the mood */
  apply(level){
    if(!this.mx.ctx||!this.ready()) return;
    this.level=level; const t=this.mx.ctx.currentTime, on=level>0, k=level/.22;
    const idle=this.bedFor('idle'), ant=this.byKind.has('bed_anticipation')?this.bedFor('anticipation'):null, a=this.mood==='anticipation'&&ant;
    if(idle){ this.setBed('idle',on); idle.g.gain.setTargetAtTime(on?(a?.45:1)*idle.a.gain*k*BED_MAKEUP:0,t,1.2); }
    if(ant){ this.setBed('anticipation',on&&!!a); ant.g.gain.setTargetAtTime(on&&a?ant.a.gain*k*BED_MAKEUP:0,t,1.0); }
  }
  setMood(m){ if(m!==this.mood){ this.mood=m; this.apply(this.level); } }
  /* ---------- reactions ---------- */
  react(kind,delay,v,key){
    const list=this.byKind.get(kind); if(!list||!this.mx.ctx) return false;
    const a=list[hsh((key||'')+'|'+kind)%list.length], buf=this.assets.peek(a.id); if(!buf) return false;
    const ac=this.mx.ctx, t=ac.currentTime+(delay||0)+.01, rank=RANK[kind]||1;
    this.live=this.live.filter(r=>r.end>ac.currentTime);
    if(this.live.length>=2){                                         /* 2 at most: the smaller one gives way */
      const low=this.live.reduce((m,r)=>r.rank<m.rank?r:m); if(low.rank>rank) return true;
      low.g.gain.setTargetAtTime(0,t,.12); try{ low.s.stop(t+.6); }catch(e){} this.live=this.live.filter(r=>r!==low);
    }
    for(const r of this.live) if(r.rank<rank) r.g.gain.setTargetAtTime(.35*r.v,t,.2);   /* a bigger moment pushes the older one down */
    const s=ac.createBufferSource(), g=ac.createGain(), lv=(v==null?1:v)*(a.gain||1)*REACT_MAKEUP*Math.max(.6,Math.min(1.3,this.level/.22||1));
    s.buffer=buf; g.gain.value=lv; s.connect(g); g.connect(this.mx.input('crowdFx')); s.start(t);
    const r={s,g,rank,v:lv,end:t+buf.duration}; this.live.push(r);
    s.onended=()=>{ this.live=this.live.filter(x=>x!==r); try{ s.disconnect(); g.disconnect(); }catch(e){} };
    return true;
  }
  stopAll(){ for(const k in this.beds) this.setBed(k,false); for(const r of this.live){ try{ r.s.stop(); }catch(e){} } this.live=[]; }
  stats(){ const beds={}; for(const k in this.beds) beds[k]={on:this.beds[k].on,srcs:this.beds[k].srcs.size}; return {kinds:this.byKind.size,mood:this.mood,live:this.live.length,beds}; }
}
CrowdManager.reactions=reactions; CrowdManager.mood=mood;
L.CrowdManager=CrowdManager;
})(window.GCAudioLib=window.GCAudioLib||{});
