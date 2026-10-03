/* GameCenter Audio System — CommentaryManager (V0.1)
   One voice on air at a time, three priorities: 3 = cuts whatever is being said (scores, turnovers,
   halftime, final), 2 = waits for the current line (only the latest one is kept), 1 = said only if
   the voice is free. The crowd is ducked while the voice speaks.
   V0.1 backend: the browser's own English voice (Web Speech), exactly as before. Recorded lines
   (ElevenLabs, pre-generated) arrive in V0.2 behind the same interface; the text stays as caption. */
(function(L){
'use strict';
const clamp=(v,a,b)=>v<a?a:(v>b?b:v);

class CommentaryManager{
  /* deps: { mixer, settings() → {talk, voice, rate, vol}, on() → sound on?, caption(text), log(kind,name,extra), onVoices() } */
  constructor(deps){
    this.d=deps; this.queue=null; this.voices=[];
    this.tts=(typeof window.speechSynthesis!=='undefined'&&typeof window.SpeechSynthesisUtterance!=='undefined')?window.speechSynthesis:null;
    if(this.tts){ this.loadVoices(); const f=()=>this.loadVoices(); try{ this.tts.addEventListener('voiceschanged',f); }catch(e){ this.tts.onvoiceschanged=f; } }
  }
  loadVoices(){ if(!this.tts) return; try{ this.voices=this.tts.getVoices().filter(v=>/^en([-_]|$)/i.test(v.lang)); }catch(e){ this.voices=[]; } if(this.d.onVoices) this.d.onVoices(); }
  pickVoice(){
    const V=this.voices, want=this.d.settings().voice;
    return V.find(v=>v.name===want)
      || V.find(v=>/en-GB/i.test(v.lang)&&/male|daniel|george|ryan|arthur|oliver/i.test(v.name))
      || V.find(v=>/en-US/i.test(v.lang)&&/guy|davis|alex|aaron|male/i.test(v.name))
      || V.find(v=>/en-(US|GB)/i.test(v.lang)) || V[0] || null;
  }
  utter(text){
    const S=this.d.settings(), u=new SpeechSynthesisUtterance(text), v=this.pickVoice(), mx=this.d.mixer;
    if(v){ u.voice=v; u.lang=v.lang; } else u.lang='en-US';
    /* the browser voice can't go through Web Audio: its volume follows MASTER × COMMENTARY by hand */
    u.rate=S.rate; u.pitch=.95; u.volume=clamp(S.vol/100*1.1*mx.level('commentary'),0,1);
    u.onstart=()=>mx.duck(true);
    u.onend=u.onerror=()=>{ mx.duck(false); const n=this.queue; this.queue=null; if(n&&this.d.on()) setTimeout(()=>this.utter(n),120); };
    try{ this.tts.speak(u); }catch(e){}
  }
  /* g: the game the line is about (null for tests and the settings page) */
  say(text,prio,g){
    const d=this.d, S=d.settings();
    d.log('say',text,{prio,game:g&&g.id});
    if(!d.on()||S.talk==='off') return;
    if(S.talk==='big'&&prio<2) return;
    if(g&&g.speed>1&&prio<3) return;                               /* fast replays: big moments only */
    d.caption(text);
    if(!this.tts||d.mixer.cfg.mute.commentary) return;            /* voice muted: the caption still shows */
    const T=this.tts;
    if(T.speaking||T.pending){
      if(prio>=3){ this.queue=null; try{ T.cancel(); }catch(e){} setTimeout(()=>this.utter(text),80); }
      else if(prio>=2) this.queue=text;
      return;
    }
    this.utter(text);
  }
  cancel(){ this.queue=null; if(this.tts) try{ this.tts.cancel(); }catch(e){} }
}
L.CommentaryManager=CommentaryManager;
})(window.GCAudioLib=window.GCAudioLib||{});
