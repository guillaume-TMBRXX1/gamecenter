/* GameCenter Audio System — CommentaryManager (V0.2)
   One voice on air at a time, three priorities: 3 = cuts whatever is being said (scores, turnovers,
   halftime, final), 2 = waits for the current line (only the latest one is kept), 1 = said only if
   the voice is free. The crowd is ducked while the voice speaks.
   Two sources behind the same rules:
     • recorded calls (pre-generated offline with ElevenLabs, listed in /audio/manifest.json), played
       through the COMMENTARY bus — the default as soon as the manifest has commentary;
     • the browser's own English voice (Web Speech) — fallback when a call is missing or late, and the
       only source when the viewer picks "Device voice" or there is no recorded pack.
   The caption always shows the page's full line (names, yards, score). */
(function(L){
'use strict';
const clamp=(v,a,b)=>v<a?a:(v>b?b:v);
const LOAD_MS=350;                 /* a recorded call slower than this gives way to the device voice */

class CommentaryManager{
  /* deps: { mixer, assets, settings() → {talk, voice, rate, vol, voiceSrc}, on(), caption(text), log(kind,name,extra), onVoices() } */
  constructor(deps){
    this.d=deps; this.queue=null; this.voices=[]; this.picker=new L.CommentaryCues.CuePicker();
    this.cur=null; this.token=0;                     /* recorded call on air: {srcs, end} */
    this.tts=(typeof window.speechSynthesis!=='undefined'&&typeof window.SpeechSynthesisUtterance!=='undefined')?window.speechSynthesis:null;
    if(this.tts){ this.loadVoices(); const f=()=>this.loadVoices(); try{ this.tts.addEventListener('voiceschanged',f); }catch(e){ this.tts.onvoiceschanged=f; } }
  }
  /* manifest loaded → index the recorded calls */
  setManifest(m){ return this.picker.index(m&&m.assets); }
  recorded(){ return this.picker.ready()&&this.d.settings().voiceSrc!=='device'; }
  loadVoices(){ if(!this.tts) return; try{ this.voices=this.tts.getVoices().filter(v=>/^en([-_]|$)/i.test(v.lang)); }catch(e){ this.voices=[]; } if(this.d.onVoices) this.d.onVoices(); }
  pickVoice(){
    const V=this.voices, want=this.d.settings().voice;
    return V.find(v=>v.name===want)
      || V.find(v=>/en-GB/i.test(v.lang)&&/male|daniel|george|ryan|arthur|oliver/i.test(v.name))
      || V.find(v=>/en-US/i.test(v.lang)&&/guy|davis|alex|aaron|male/i.test(v.name))
      || V.find(v=>/en-(US|GB)/i.test(v.lang)) || V[0] || null;
  }
  busy(){ return !!this.cur||!!(this.tts&&(this.tts.speaking||this.tts.pending)); }
  next(){ const n=this.queue; this.queue=null; if(n&&this.d.on()) setTimeout(()=>this.start(n),120); }
  /* ---------- device voice ---------- */
  utter(text){
    const S=this.d.settings(), u=new SpeechSynthesisUtterance(text), v=this.pickVoice(), mx=this.d.mixer;
    if(v){ u.voice=v; u.lang=v.lang; } else u.lang='en-US';
    /* the browser voice can't go through Web Audio: its volume follows MASTER × COMMENTARY by hand */
    u.rate=S.rate; u.pitch=.95; u.volume=clamp(S.vol/100*1.1*mx.level('commentary'),0,1);
    u.onstart=()=>mx.duck(true);
    u.onend=u.onerror=()=>{ mx.duck(false); this.next(); };
    try{ this.tts.speak(u); }catch(e){}
  }
  /* ---------- recorded calls ---------- */
  async playClips(item){
    const tok=++this.token, A=this.d.assets;
    this.cur={srcs:[],tok};                                     /* on air from now on, even while loading */
    const bufs=await Promise.all(item.clips.map(a=>A.get(a.id,LOAD_MS)));
    if(tok!==this.token) return;                                /* something louder came in meanwhile */
    if(!this.d.on()){ this.cur=null; return; }
    if(bufs.some(b=>!b)){                                       /* missing or late: the device voice says the full line */
      this.d.log('voice','fallback',{clips:item.clips.map(a=>a.id)});
      this.cur=null; if(this.tts) this.utter(item.text); else this.next(); return;
    }
    const mx=this.d.mixer, ac=mx.ctx, out=mx.input('commentary'); let t=ac.currentTime+.02;
    const srcs=bufs.map(b=>{ const s=ac.createBufferSource(); s.buffer=b; s.connect(out); s.start(t); t+=b.duration+.12; return s; });
    this.cur={srcs,tok}; mx.duck(true);
    this.d.log('clip',item.clips.map(a=>a.id).join('+'),{prio:item.prio});
    srcs[srcs.length-1].onended=()=>{ for(const s of srcs) try{ s.disconnect(); }catch(e){}
      if(this.cur&&this.cur.tok===tok){ this.cur=null; mx.duck(false); this.next(); } };
  }
  stopClips(){
    const c=this.cur; this.cur=null; this.token++;
    if(c&&c.srcs.length) this.d.log('clip-cut','',{});
    if(c) for(const s of c.srcs){ try{ s.onended=null; s.stop(); s.disconnect(); }catch(e){} }
    this.d.mixer.duck(false);
  }
  start(item){ if(item.clips) this.playClips(item); else if(this.tts) this.utter(item.text); }
  /* g: the game the line is about (null for tests and the settings page).
     req: {cues:[{cue,tags,tier?}], imp, seq} — what the moment is, for a recorded call */
  say(text,prio,g,req){
    const d=this.d, S=d.settings();
    d.log('say',text,{prio,game:g&&g.id});
    if(!d.on()||S.talk==='off') return;
    if(S.talk==='big'&&prio<2) return;
    if(g&&g.speed>1&&prio<3) return;                               /* fast replays: big moments only */
    d.caption(text);
    if(d.mixer.cfg.mute.commentary) return;                         /* voice muted: the caption still shows */
    let clips=null;
    if(req&&req.cues&&req.cues.length&&this.recorded()&&d.mixer.running()){
      const id=g?g.id:'-', seq=req.seq!=null?req.seq:0;
      clips=req.cues.map(c=>this.picker.pick(id,seq,c,req.imp,true)).filter(Boolean);
      if(clips.length!==req.cues.length) clips=null;              /* a cue without a recording: device voice */
    }
    const item={text,prio,clips};
    if(!clips&&!this.tts) return;
    if(this.busy()){
      if(prio>=3){ this.queue=null; this.stopClips(); if(this.tts) try{ this.tts.cancel(); }catch(e){} setTimeout(()=>this.start(item),80); }
      else if(prio>=2) this.queue=item;
      return;
    }
    this.start(item);
  }
  /* calls likely to be needed soon: fetched and decoded ahead (no-repeat memory untouched) */
  prefetch(g,seq,reqs,imp){
    if(!this.recorded()) return;
    const ids=[]; for(const r of reqs){ const a=this.picker.pick(g?g.id:'-',seq,r,imp,false); if(a) ids.push(a.id); }
    this.d.assets.prefetch(ids);
  }
  cancel(){ this.queue=null; this.stopClips(); if(this.tts) try{ this.tts.cancel(); }catch(e){} }
}
L.CommentaryManager=CommentaryManager;
})(window.GCAudioLib=window.GCAudioLib||{});
