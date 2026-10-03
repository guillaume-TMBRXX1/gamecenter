/* GameCenter Audio System — SFXManager (V0.3)
   Recorded field effects (pre-generated offline with ElevenLabs Sound Effects, listed in the manifest as
   cat "sfx"): snap, tackle, hit, catch, incomplete, whistle, whistle_long, kick, fg_good, fumble, turnover, horn.
   Broadcast, not arcade: modest levels, a tiny random variation of pitch and level per hit, at most 6 effects
   at once, a short cool-down per effect. Nothing waits on the network: an effect that isn't decoded yet
   returns false and the caller plays the procedural one instead. */
(function(L){
'use strict';
const MAX_VOICES=6, COOLDOWN=.06;
function hsh(s){ let h=2166136261; for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }

class SFXManager{
  constructor(mixer,assets){ this.mx=mixer; this.assets=assets; this.byKind=new Map(); this.active=new Set(); this.lastAt={}; this.lastId={}; this.n=0; }
  index(manifest){ this.byKind=new Map(); for(const a of (manifest&&manifest.assets)||[]) if(a.cat==='sfx'){ (this.byKind.get(a.kind)||this.byKind.set(a.kind,[]).get(a.kind)).push(a); } return this.byKind.size; }
  ready(){ return this.byKind.size>0; }
  has(kind){ return this.byKind.has(kind); }
  ids(kinds){ const out=[]; for(const [k,list] of this.byKind) if(!kinds||kinds.includes(k)) for(const a of list) out.push(a.id); return out; }
  /* kind, seconds from now, level (1 = catalogue level), key = what makes the variant choice repeatable */
  play(kind,delay,v,key){
    const list=this.byKind.get(kind); if(!list||!this.mx.ctx) return false;
    const ac=this.mx.ctx, t=ac.currentTime+(delay||0)+.01;
    if(this.lastAt[kind]!=null&&Math.abs(t-this.lastAt[kind])<COOLDOWN) return true;            /* same effect twice in 60 ms: once is enough */
    let pool=list.length>1?list.filter(a=>a.id!==this.lastId[kind]):list;
    const a=pool[hsh((key||'')+'|'+kind+'|'+(this.n++))%pool.length], buf=this.assets.peek(a.id);
    if(!buf) return false;
    if(this.active.size>=MAX_VOICES) return true;                                               /* full: the field is loud enough */
    const s=ac.createBufferSource(), g=ac.createGain(), r=hsh(a.id+this.n);
    s.buffer=buf; s.playbackRate.value=1+((r%61)-30)/1000;                                       /* ±3 % pitch */
    g.gain.value=(v==null?1:v)*(a.gain||1)*(1+(((r>>8)%11)-5)/100);                             /* ±5 % level */
    s.connect(g); g.connect(this.mx.input('sfx')); s.start(t);
    this.active.add(s); this.lastAt[kind]=t; this.lastId[kind]=a.id;
    s.onended=()=>{ this.active.delete(s); try{ s.disconnect(); g.disconnect(); }catch(e){} };
    return true;
  }
  stopAll(){ for(const s of this.active){ try{ s.onended=null; s.stop(); s.disconnect(); }catch(e){} } this.active.clear(); }
  stats(){ return {kinds:this.byKind.size,active:this.active.size}; }
}
L.SFXManager=SFXManager;
})(window.GCAudioLib=window.GCAudioLib||{});
