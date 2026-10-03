/* GameCenter Audio System — AudioManager (V0.1)
   GAME ENGINE → GAME EVENTS → AUDIO MANAGER → AUDIO MIXER → BROWSER AUDIO
   The page reports what happened on the broadcast (snap, result, focus change, interface feedback) with
   the lines its writers produced; the manager maps it to events (AudioEventMapper), decides the
   reactions (ProceduralAudio now, recorded assets from V0.2), sends the lines to the commentator and
   everything through the mixer. It never talks to the engine, nor to ElevenLabs.

   deps (from the page):
     settings() → {snd, vol, sfx, crowd, talk, voice, rate, cap, mix:{commentary,crowd,sfx,music}, mixMute:{commentary,music}}
     log(kind,name,extra)   the page's audio log (tests)      caption(text) / captionHide()
     crowdLevel()           bed level for the game on air     onVoices()   the voice list changed */
(function(L){
'use strict';
class AudioManager{
  constructor(deps){
    this.d=deps;
    this.mixer=new L.AudioMixer();
    this.proc=new L.ProceduralAudio(this.mixer);
    this.assets=new L.AssetLoader(this.mixer);
    this.voice=new L.CommentaryManager({mixer:this.mixer,settings:deps.settings,on:()=>this.on(),caption:deps.caption,log:deps.log,onVoices:deps.onVoices});
    this.last=null;                                   /* last event batch, for tests */
    this.listeners=new Set();
  }
  on(){ return !!this.d.settings().snd; }
  /* from a user gesture: create / resume the context (autoplay rules), build the procedural layer */
  unlock(){
    const ac=this.mixer.ensure(); if(!ac) return false;
    this.proc.init(); this.mixer.resume(); this.apply(); this.assets.loadManifest();
    return true;
  }
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
  say(text,prio,g){ this.voice.say(text,prio,g); }
  /* Broadcast hooks. lines = [{text,prio}] written by the page for this moment, in speaking order. */
  snap(g,P,prev,lines){
    const b=L.AudioEventMapper.mapSnap(g,P,prev); this.emit(b);
    const [qLine,playLines]=lines||[];
    if(qLine) this.say(qLine.text,qLine.prio,g);
    for(const c of L.ProceduralAudio.cuesSnap(b.ctx)) this.sfx(...c);
    if(playLines) this.say(playLines.text,playLines.prio,g);
    return b;
  }
  resolve(g,P,wpBefore,line){
    const b=L.AudioEventMapper.mapResolve(g,P,wpBefore); this.emit(b);
    for(const c of L.ProceduralAudio.cuesResolve(b.ctx)) this.sfx(...c);
    if(line) this.say(line.text,line.prio,g);
    return b;
  }
  focus(g,intro){ if(g&&intro&&this.on()) this.say(intro,3,g); this.apply(); }
  emit(b){ this.last=b; for(const f of this.listeners){ try{ f(b); }catch(e){} } }
  onEvent(f){ this.listeners.add(f); return ()=>this.listeners.delete(f); }
  voices(){ return this.voice.voices; }
  pickVoice(){ return this.voice.pickVoice(); }
  hasTTS(){ return !!this.voice.tts; }
  state(){ return this.mixer.state(); }
}
L.AudioManager=AudioManager;
L.version='0.1';
})(window.GCAudioLib=window.GCAudioLib||{});
