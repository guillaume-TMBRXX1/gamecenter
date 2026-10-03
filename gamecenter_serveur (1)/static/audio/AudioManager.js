/* GameCenter Audio System — AudioManager (V0.2)
   GAME ENGINE → GAME EVENTS → AUDIO MANAGER → AUDIO MIXER → BROWSER AUDIO
   The page reports what happened on the broadcast (snap, result, focus change, interface feedback) with
   the lines its writers produced; the manager maps it to events (AudioEventMapper), decides the
   reactions (ProceduralAudio; recorded crowd / effects from V0.3), picks the recorded call for the
   commentator (CommentaryCues) and sends everything through the mixer. It never talks to the engine,
   nor to ElevenLabs: recorded calls are files made offline and listed in /audio/manifest.json.

   deps (from the page):
     settings() → {snd, vol, sfx, crowd, talk, voice, voiceSrc, rate, cap, mix:{commentary,crowd,sfx,music}, mixMute:{commentary,music}}
     log(kind,name,extra)   the page's audio log (tests)      caption(text) / captionHide()
     crowdLevel()           bed level for the game on air     onVoices()   the voice list or the recorded pack changed */
(function(L){
'use strict';
const CC=()=>L.CommentaryCues;
class AudioManager{
  constructor(deps){
    this.d=deps;
    this.mixer=new L.AudioMixer();
    this.proc=new L.ProceduralAudio(this.mixer);
    this.assets=new L.AssetLoader(this.mixer);
    this.voice=new L.CommentaryManager({mixer:this.mixer,assets:this.assets,settings:deps.settings,on:()=>this.on(),caption:deps.caption,log:deps.log,onVoices:deps.onVoices});
    this.last=null;                                   /* last event batch, for tests */
    this.listeners=new Set();
  }
  on(){ return !!this.d.settings().snd; }
  /* from a user gesture: create / resume the context (autoplay rules), build the procedural layer,
     read the manifest of recorded calls */
  unlock(){
    const ac=this.mixer.ensure(); if(!ac) return false;
    this.mixer.playThroughSilent(true);               /* iOS: play even with the silent switch on, where Safari allows it */
    this.proc.init(); this.mixer.resume(); this.apply();
    if(!this._mf) this._mf=this.assets.loadManifest().then(m=>{ const n=this.voice.setManifest(m);
      if(n){ this.prefetchStart(); if(this.d.onVoices) this.d.onVoices(); } return m; });
    return true;
  }
  recordedPack(){ return this.voice.picker.ready(); }
  /* settings → mixer (+ crowd bed level). Same gains as the previous page at default mixer levels. */
  apply(){
    const S=this.d.settings(), on=!!S.snd, mix=S.mix||{}, mm=S.mixMute||{};
    if(!on) this.voice.cancel();
    this.mixer.configure({enabled:on,master:S.vol,
      vol:{commentary:mix.commentary,crowd:mix.crowd,sfx:mix.sfx,music:mix.music},
      mute:{sfx:!S.sfx,commentary:!!mm.commentary,music:!!mm.music}});
    if(this.proc.ready) this.proc.setBed(on&&S.crowd?this.d.crowdLevel():0);
  }
  running(){ return this.mixer.running(); }
  /* one effect, with the previous page's gating and log lines */
  sfx(name,delay,...args){
    const S=this.d.settings(), log=this.d.log;
    const a=[delay,...args];
    if(!this.on()||!this.running()){ log('sfx',name,{muted:true,args:a}); return; }
    if(!S.sfx&&name!=='roar'){ log('sfx',name,{muted:true,args:a}); return; }
    log('sfx',name,{args:a});
    if(name==='roar'&&!S.crowd) return;              /* the roar belongs to the crowd switch */
    this.proc.play(name,delay,...args);
  }
  ui(kind){
    if(!this.on()||!this.running()){ this.d.log('ui',kind,{muted:true}); return; }
    this.d.log('ui',kind); this.proc.ui(kind);
  }
  /* req (optional): {cues:[{cue,tags,tier?}], imp, seq} — the moment, so a recorded call can be picked */
  say(text,prio,g,req){ this.voice.say(text,prio,g,req); }
  /* Broadcast hooks. lines = what the page wrote for this moment (captions + device voice). */
  snap(g,P,prev,lines){
    const b=L.AudioEventMapper.mapSnap(g,P,prev), c=b.ctx; this.emit(b);
    const [qLine,playLine]=lines||[];
    if(qLine) this.say(qLine.text,qLine.prio,g,{cues:[CC().quarterCue(c.quarter)],imp:c.importance,seq:P.seq});
    for(const x of L.ProceduralAudio.cuesSnap(c)) this.sfx(...x);
    if(playLine) this.say(playLine.text,playLine.prio,g,{cues:CC().snapCues(c,P),imp:c.importance,seq:P.seq});
    this.prefetchResolve(g,P,c);
    return b;
  }
  resolve(g,P,wpBefore,line){
    const b=L.AudioEventMapper.mapResolve(g,P,wpBefore), c=b.ctx; this.emit(b);
    for(const x of L.ProceduralAudio.cuesResolve(c)) this.sfx(...x);
    if(line) this.say(line.text,line.prio,g,{cues:CC().resolveCues(c,P,g),imp:c.importance,seq:P.seq});
    return b;
  }
  focus(g,intro){ if(g&&intro&&this.on()) this.say(intro,3,g,{cues:[CC().introCue(g)],imp:.5,seq:g.cur?g.cur.seq:0}); this.apply(); }
  /* ---------- prefetch: the calls that can follow, fetched while the play runs (~2-4 s) ---------- */
  prefetchResolve(g,P,c){
    if(!this.voice.recorded()||!this.on()) return;
    const ty=c.callType, T=ty?[ty]:[], lite=this.assets.lite(), R=[];
    if(ty==='pass') R.push({cue:'PASS_COMPLETE',tags:T},{cue:'INCOMPLETE',tags:T},{cue:'PASS_COMPLETE',tags:T.concat('fd')},{cue:'SACK',tags:T},{cue:'BIG_PLAY',tags:T});
    else if(ty==='run') R.push({cue:'RUN',tags:T},{cue:'RUN',tags:T.concat('fd')},{cue:'RUN_STUFFED',tags:T},{cue:'BIG_PLAY',tags:T});
    else if(ty==='field_goal') R.push({cue:'FIELD_GOAL_GOOD',tags:[]},{cue:'FIELD_GOAL_MISS',tags:[]});
    else if(ty==='punt') R.push({cue:'PUNT',tags:[]});
    else if(ty==='kickoff') R.push({cue:'KICKOFF',tags:[]});
    if(c.isRedZone&&(ty==='pass'||ty==='run')) R.unshift({cue:'TOUCHDOWN',tags:T});
    if(c.isLateGame) R.push({cue:'VICTORY',tags:[]},{cue:'DEFEAT',tags:[]});
    this.voice.prefetch(g,P.seq,lite?R.slice(0,3):R,Math.max(c.importance,.3));
  }
  prefetchStart(){ const L2=[{cue:'INTRO_LIVE',tags:[]},{cue:'INTRO_JOIN',tags:[]},{cue:'TEST',tags:[]}]; this.voice.prefetch(null,0,L2,.5); }
  emit(b){ this.last=b; for(const f of this.listeners){ try{ f(b); }catch(e){} } }
  onEvent(f){ this.listeners.add(f); return ()=>this.listeners.delete(f); }
  voices(){ return this.voice.voices; }
  pickVoice(){ return this.voice.pickVoice(); }
  hasTTS(){ return !!this.voice.tts; }
  state(){ return this.mixer.state(); }
}
L.AudioManager=AudioManager;
L.version='0.2';
})(window.GCAudioLib=window.GCAudioLib||{});
