/* GameCenter Audio System — AudioManager (V0.4)
   GAME ENGINE → GAME EVENTS → AUDIO MANAGER → AUDIO MIXER → BROWSER AUDIO
   The page reports what happened on the broadcast (snap, result, focus change, interface feedback) with
   the lines its writers produced; the manager maps it to events (AudioEventMapper), decides the
   reactions (recorded crowd and field effects — CrowdManager, SFXManager — with ProceduralAudio as the
   fallback for anything missing or not decoded yet), picks the recorded call for the
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
    this.sfxRec=new L.SFXManager(this.mixer,this.assets);
    this.crowd=new L.CrowdManager(this.mixer,this.assets);
    this.music=new L.MusicManager(this.mixer,this.assets); this.music.log=deps.log;
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
      this.sfxRec.index(m); this.crowd.index(m); this.music.index(m);
      /* stadium pack: every effect (small) and the crowd, in the background; data saver keeps to the essentials */
      const lite=this.assets.lite();
      this.assets.prefetch(this.sfxRec.ids(lite?['snap','whistle','tackle']:null));
      if(this.crowd.ready()) this.assets.prefetch(this.crowd.ids(lite));
      if(n){ this.prefetchStart(); if(this.d.onVoices) this.d.onVoices(); }
      this.apply(); return m; });
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
    const lvl=on&&S.crowd?this.d.crowdLevel():0;
    /* music: on unless muted, sound off or a data-saver link; with no game decided yet, the pregame piece */
    if(this.musicOn()){ if(this.music.state==null) this.music.request(this.musicState||'pregame',true); } else if(this.music.state!=null||this.music.cur) this.music.stop();
    if(this.crowd.ready()&&this.mixer.ctx){ this.mixer.duckDepth=.65; if(this.proc.ready) this.proc.setBed(0); this.crowd.apply(lvl); }   /* recorded stadium: lighter duck */
    else if(this.proc.ready) this.proc.setBed(lvl);
  }
  stadium(){ return this.sfxRec.ready()||this.crowd.ready(); }
  musicOn(){ const S=this.d.settings(); return !!S.snd&&!(S.mixMute&&S.mixMute.music)&&this.music.ready()&&!!this.mixer.ctx&&this.running()&&!this.assets.lite(); }
  setMusic(st,force){ this.musicState=st==='victory'||st==='defeat'||st==='silence'?null:st; if(this.musicOn()){ this.music.request(st,force); this.music.tick(); } }
  /* one effect through the recorded stadium: recorded take if decoded, else the procedural one.
     Same gating as sfx(). Crowd sounds (roar, ooh, groan) give way to the recorded crowd's reactions. */
  fx(name,delay,args,c){
    const S=this.d.settings(), log=this.d.log, a=[delay,...args], crowdCue=name==='roar'||name==='ooh'||name==='groan';
    if(crowdCue&&this.crowd.ready()) return;
    if(!this.on()||!this.running()){ log('sfx',name,{muted:true,args:a}); return; }
    if(!S.sfx&&name!=='roar'){ log('sfx',name,{muted:true,args:a}); return; }
    if(name==='roar'&&!S.crowd){ log('sfx',name,{args:a}); return; }
    let kind=null, v=1;
    if(name==='snap') kind='snap';
    else if(name==='kick') kind=c.callType==='field_goal'&&this.sfxRec.has('fg_good')?'fg_good':'kick';
    else if(name==='hit'){ kind=c.result==='sack'?'hit':'tackle'; v=args[0]==null?1:Math.min(1,.55+.45*args[0]); }
    else if(name==='horn') kind='horn';
    else if(name==='whistle'){
      if(c.status==='half'||c.status==='final'){ if(this._longFor===c.seq) return; this._longFor=c.seq; kind='whistle_long'; }   /* one long whistle instead of 2-3 short */
      else if((c.result==='interception'||c.result==='fumble_lost')&&delay>=.8) kind='turnover';
      else kind='whistle';
    }
    if(kind&&this.sfxRec.play(kind,delay,v,c.gameId+'|'+c.seq)){ log('sfx',name,{args:a,rec:kind}); return; }
    log('sfx',name,{args:a}); this.proc.play(name,delay,...args);
  }
  /* recorded-only touches the procedural set never had: the catch, the ball on the turf, the loose ball */
  extras(c){
    const S=this.d.settings(); if(!S.sfx||!this.sfxRec.ready()) return;
    const k=c.gameId+'|'+c.seq, r=c.result;
    if(r==='complete'&&c.gain>0) this.sfxRec.play('catch',0,.9,k);
    else if(r==='incomplete') this.sfxRec.play('incomplete',.05,1,k);
    else if(r==='fumble_lost') this.sfxRec.play('fumble',.1,1,k);
  }
  react(c,ev){
    const S=this.d.settings(); if(!this.crowd.ready()||!S.crowd) return;
    for(const [kind,delay,v] of L.CrowdManager.reactions(c,ev)) if(this.crowd.react(kind,delay,v,c.gameId+'|'+c.seq)) this.d.log('crowd',kind,{v});
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
    if(this.stadium()&&this.on()&&this.running()){ for(const [n,d,...a] of L.ProceduralAudio.cuesSnap(c)) this.fx(n,d,a,c); if(this.crowd.ready()) this.crowd.setMood(L.CrowdManager.mood(c,b.events)); }
    else for(const x of L.ProceduralAudio.cuesSnap(c)) this.sfx(...x);
    this.setMusic(L.MusicManager.stateFor(c,b.events));
    if(playLine) this.say(playLine.text,playLine.prio,g,{cues:CC().snapCues(c,P),imp:c.importance,seq:P.seq});
    this.prefetchResolve(g,P,c);
    return b;
  }
  resolve(g,P,wpBefore,line){
    const b=L.AudioEventMapper.mapResolve(g,P,wpBefore), c=b.ctx; this.emit(b);
    if(b.events.includes('GAME_END')||b.events.includes('HALFTIME')) this.setMusic(L.MusicManager.stateFor(c,b.events));
    if(this.stadium()&&this.on()&&this.running()){ this.extras(c); for(const [n,d,...a] of L.ProceduralAudio.cuesResolve(c)) this.fx(n,d,a,c); this.react(c,b.events); }
    else for(const x of L.ProceduralAudio.cuesResolve(c)) this.sfx(...x);
    if(line) this.say(line.text,line.prio,g,{cues:CC().resolveCues(c,P,g),imp:c.importance,seq:P.seq});
    return b;
  }
  focus(g,intro){ if(g){ const P=g.cur, st=P&&P.after&&P.after.status==='final'?'silence':'pregame'; this.musicState=st==='silence'?null:st; if(this.musicOn()) this.music.request(st,true); }
    if(g&&intro&&this.on()) this.say(intro,3,g,{cues:[CC().introCue(g)],imp:.5,seq:g.cur?g.cur.seq:0}); this.apply(); }
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
  stats(){ return {ctx:this.state(),cache:this.assets.stats(),sfx:this.sfxRec.stats(),crowd:this.crowd.stats(),music:this.music.stats(),voice:{recorded:this.voice.recorded(),busy:this.voice.busy()}}; }
}
L.AudioManager=AudioManager;
L.version='0.4';
})(window.GCAudioLib=window.GCAudioLib||{});
