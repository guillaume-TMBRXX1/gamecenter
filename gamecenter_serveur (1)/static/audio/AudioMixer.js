/* GameCenter Audio System — AudioMixer (V0.1)
   One AudioContext, five categories:  COMMENTARY · CROWD · SFX · MUSIC → MASTER → speakers.
   Independent volume and mute per category, global mute, ducking of the crowd under the voice.
   V0.1 keeps the exact gains of the previous page sound (master curve vol^1.5, effects on/off,
   crowd ducked to 45 % while the commentator speaks), so nothing changes to the ear at default levels. */
(function(L){
'use strict';
const CATS=['commentary','crowd','sfx','music'];
const clamp=(v,a,b)=>v<a?a:(v>b?b:v);

class AudioMixer{
  constructor(){ this.ctx=null; this.duckDepth=.45; this.cfg={enabled:false,master:70,vol:{commentary:100,crowd:100,sfx:100,music:100},mute:{master:false,commentary:false,crowd:false,sfx:false,music:false}}; }
  /* Creates the context and the bus graph. Must be first called from a user gesture (browser autoplay rules). */
  ensure(){
    if(this.ctx) return this.ctx;
    const C=window.AudioContext||window.webkitAudioContext; if(!C) return null;
    let ac; try{ ac=new C(); }catch(e){ return null; }
    this.ctx=ac;
    const g=v=>{ const n=ac.createGain(); n.gain.value=v; return n; };
    this.master=g(0);
    /* safety limiter on the way out: recorded crowd, voice and music can add up — never clip, never pump at normal levels */
    try{ const l=ac.createDynamicsCompressor(); l.threshold.value=-3; l.knee.value=0; l.ratio.value=20; l.attack.value=.003; l.release.value=.25;
      this.master.connect(l); l.connect(ac.destination); this.limiter=l; }catch(e){ this.master.connect(ac.destination); }
    /* every category is a gain into MASTER; the crowd has a second gain, the duck, in front of it */
    this.buses={};
    for(const c of CATS){ this.buses[c]=g(1); this.buses[c].connect(this.master); }
    this.duckNode=g(1); this.duckNode.connect(this.buses.crowd);
    this.musicDuck=g(1); this.musicDuck.connect(this.buses.music);
    this.uiNode=this.master;              /* interface tones (bet placed, won…) go straight to MASTER, as before */
    /* Safari met parfois le contexte en pause (« interrupted » / « suspended ») en plein match : on le relance tout de
       suite, et sinon au prochain geste (clic, touche) — le son ne reste plus coupé jusqu'au rechargement */
    try{ ac.addEventListener('statechange',()=>{ if(window.GC_DIAG) window.GC_DIAG('audio',{state:ac.state});
      if(ac.state==='interrupted'||ac.state==='suspended'){ this.resume();
        if(!this._wake){ this._wake=()=>{ this._wake=null; this.resume(); };
          for(const t of ['pointerdown','keydown','touchend']) document.addEventListener(t,this._wake,{once:true,capture:true}); } } }); }catch(e){}
    this.apply();
    return ac;
  }
  /* where a category's sources connect */
  /* crowd = beds (ducked under the voice) · crowdFx = crowd reactions (not ducked: the roar rises under the call, as on TV)
     music = ducked under the voice too */
  input(cat){ if(!this.ctx) return null; return cat==='crowd'?this.duckNode:cat==='crowdFx'?this.buses.crowd:cat==='music'?this.musicDuck:cat==='ui'?this.uiNode:this.buses[cat]; }
  configure(cfg){
    const c=this.cfg; c.enabled=!!cfg.enabled; if(cfg.master!=null) c.master=clamp(+cfg.master||0,0,100);
    if(cfg.vol) for(const k of CATS) if(cfg.vol[k]!=null) c.vol[k]=clamp(+cfg.vol[k]||0,0,100);
    if(cfg.mute) for(const k in c.mute) if(cfg.mute[k]!=null) c.mute[k]=!!cfg.mute[k];
    this.apply();
  }
  /* effective linear gain of a category (0..1) — also used for the browser voice, which can't be routed here */
  level(cat){ const c=this.cfg; return c.mute[cat]?0:c.vol[cat]/100; }
  masterLevel(){ const c=this.cfg; return c.enabled&&!c.mute.master?Math.pow(c.master/100,1.5):0; }
  apply(){
    if(!this.ctx) return;
    const t=this.ctx.currentTime;
    this.master.gain.setTargetAtTime(this.masterLevel(),t,.06);
    this.buses.sfx.gain.setTargetAtTime(this.level('sfx'),t,.05);
    this.buses.crowd.gain.setTargetAtTime(this.level('crowd'),t,.05);
    this.buses.commentary.gain.setTargetAtTime(this.level('commentary'),t,.05);
    this.buses.music.gain.setTargetAtTime(this.level('music'),t,.4);
  }
  duck(on){ if(!this.ctx) return; const t=this.ctx.currentTime; this.duckNode.gain.setTargetAtTime(on?this.duckDepth:1,t,.15); this.musicDuck.gain.setTargetAtTime(on?.7:1,t,.25); }
  resume(){ const ac=this.ctx; if(ac&&(ac.state==='suspended'||ac.state==='interrupted')){ try{ const p=ac.resume(); if(p&&p.catch) p.catch(()=>{}); }catch(e){} } }
  state(){ return this.ctx?this.ctx.state:null; }
  running(){ return !!this.ctx&&this.ctx.state==='running'; }
  /* iOS: let Safari play through the silent switch when it supports it (navigator.audioSession, Safari 16.4+).
     Off in V0.1 (no audible change); switched on from V0.2. */
  playThroughSilent(on){ try{ if(navigator.audioSession) navigator.audioSession.type=on?'playback':'auto'; return !!navigator.audioSession; }catch(e){ return false; } }
}
AudioMixer.CATEGORIES=CATS;
L.AudioMixer=AudioMixer;
})(window.GCAudioLib=window.GCAudioLib||{});
