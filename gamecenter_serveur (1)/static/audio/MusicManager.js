/* GameCenter Audio System — MusicManager (V0.4)
   Broadcast music under the game (original pieces, CC0, composed by outils/audio/composer_musique.py):
     loops   pregame · gameplay · close_game · red_zone · final_drive · overtime
     jingles victory · defeat (HOME point of view)
   The state follows the game on air, decided at each snap / result:
     no game yet or halftime → pregame · overtime → overtime · last half of Q4 and close → final_drive when the
     offense trails or is level, else close_game · in the red zone → red_zone · close in the 2nd half → close_game ·
     otherwise gameplay · final whistle → victory / defeat jingle, then silence until the next game.
   Clean transitions: equal-power crossfade (3 s), sample-accurate loops (loop points from the manifest), and
   hysteresis — tension rises at once, but the music only settles back after 20 s, so it never flip-flops.
   Kept low (it sits under the voice and the crowd, ducked when the commentator speaks); off on data-saver links. */
(function(L){
'use strict';
const XF=3, DWELL=20, LEVEL=1.2;   /* measured in a replay: the music bus sits ≈ at the crowd bed's level */
const RANK={gameplay:0,pregame:0,close_game:1,red_zone:2,final_drive:3,overtime:4};

function stateFor(c,ev){
  if(ev.includes('GAME_END')) return ev.includes('VICTORY')?'victory':ev.includes('DEFEAT')?'defeat':'silence';
  if(c.status==='half'||ev.includes('HALFTIME')) return 'pregame';
  if(c.isOvertime) return 'overtime';
  const s=c.score, offBehind=c.offense==='home'?s.home<=s.away:s.away<=s.home;
  if(c.isLateGame&&c.isCloseGame) return offBehind?'final_drive':'close_game';
  if(c.isRedZone&&(c.callType==='run'||c.callType==='pass')) return 'red_zone';
  if(c.isCloseGame&&c.quarter>=3) return 'close_game';
  return 'gameplay';
}

class MusicManager{
  constructor(mixer,assets){ this.mx=mixer; this.assets=assets; this.byState=new Map(); this.cur=null; this.state=null; this.since=0; this.want=null; this.tok=0; this.log=null; this.live=new Map(); }   /* live: source → its gain, every piece still sounding */
  index(manifest){ this.byState=new Map(); for(const a of (manifest&&manifest.assets)||[]) if(a.cat==='music') this.byState.set(a.state,a); return this.byState.size; }
  ready(){ return this.byState.size>0; }
  now(){ return this.mx.ctx?this.mx.ctx.currentTime:0; }
  /* ask for a state; hysteresis decides if and when it changes */
  request(st,force){
    if(!this.ready()) return;
    if(st===this.state||(st===this.want&&!force)) return;
    const up=(RANK[st]||0)>(RANK[this.state]||0), stinger=st==='victory'||st==='defeat'||st==='silence';
    if(force||stinger||up||this.state==null||this.now()-this.since>=DWELL) this.go(st);
    else this.want=st;                                   /* settle later */
  }
  tick(){ if(this.want&&this.want!==this.state&&this.now()-this.since>=DWELL){ const w=this.want; this.want=null; this.go(w); } }
  async go(st){
    const tok=++this.tok; this.want=null;
    const prevState=this.state; this.state=st; this.since=this.now();
    if(this.log) this.log('music',st,{from:prevState});
    if(st==='silence'){ this.fadeOut(XF); return; }
    const a=this.byState.get(st); if(!a){ this.fadeOut(XF); return; }
    const buf=await this.assets.get(a.id); if(tok!==this.tok||!buf||!this.mx.ctx) return;
    const ac=this.mx.ctx, t=ac.currentTime+.05, s=ac.createBufferSource(), g=ac.createGain(), lv=(a.gain||.6)*LEVEL;
    s.buffer=buf;
    if(a.kind==='loop'){ s.loop=true; s.loopStart=a.loopStart||0; s.loopEnd=a.loopEnd||buf.duration; }
    /* equal-power crossfade: the new piece rises as sin, the old one falls as cos */
    const n=32, up=new Float32Array(n), dn=new Float32Array(n);
    for(let i=0;i<n;i++){ const x=i/(n-1)*Math.PI/2; up[i]=Math.sin(x)*lv; dn[i]=Math.cos(x); }
    g.gain.setValueAtTime(0,t); g.gain.setValueCurveAtTime(up,t,XF);
    s.connect(g); g.connect(this.mx.input('music'));
    s.start(t,a.kind==='loop'?(a.loopStart||0):0);
    this.cutFading(t);                                    /* a third piece never stacks: older fades end now */
    this.live.set(s,g);
    const old=this.cur; this.cur={s,g,a,lv};
    if(old){ const v=old.g.gain.value||old.lv; this.live.set(old.s,old.g); for(let i=0;i<n;i++) dn[i]=Math.cos(i/(n-1)*Math.PI/2)*v;
      try{ old.g.gain.cancelScheduledValues(t); old.g.gain.setValueCurveAtTime(dn,t,XF); old.s.stop(t+XF+.05); }catch(e){} this.release(old); }
    if(a.kind!=='loop'){ s.onended=()=>{ this.live.delete(s); if(this.cur&&this.cur.s===s){ this.cur=null; this.state='silence'; } try{ s.disconnect(); g.disconnect(); }catch(e){} }; }
  }
  /* every source still sounding but no longer current: 30 ms ramp, then stop */
  cutFading(t){ for(const [x,g] of this.live){ if(this.cur&&x===this.cur.s) continue;
      try{ g.gain.cancelScheduledValues(t); g.gain.setTargetAtTime(0,t,.01); }catch(e){} this.live.delete(x); } }   /* silent at once; it disconnects when its scheduled stop comes */
  release(v){ v.s.onended=()=>{ this.live.delete(v.s); try{ v.s.disconnect(); v.g.disconnect(); }catch(e){} }; }
  fadeOut(sec){
    const v=this.cur; this.cur=null; if(!v||!this.mx.ctx) return;
    const t=this.mx.ctx.currentTime; try{ v.g.gain.cancelScheduledValues(t); v.g.gain.setTargetAtTime(0,t,sec/4); v.s.stop(t+sec+.1); }catch(e){} this.release(v);
  }
  /* sound off / music muted: stop and forget the state (it is decided again on the next play) */
  stop(){ this.tok++; if(this.mx.ctx) this.cutFading(this.mx.ctx.currentTime); this.fadeOut(.6); this.state=null; this.want=null; }
  stats(){ return {state:this.state,want:this.want,playing:!!this.cur,sources:this.live.size,pieces:this.byState.size}; }
}
MusicManager.stateFor=stateFor;
L.MusicManager=MusicManager;
})(window.GCAudioLib=window.GCAudioLib||{});
