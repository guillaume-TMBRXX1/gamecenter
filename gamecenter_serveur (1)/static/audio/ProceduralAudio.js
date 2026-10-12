/* GameCenter Audio System — ProceduralAudio (V0.1)
   The sounds the page used to make, moved here unchanged: crowd bed and roar made from filtered noise,
   whistle, snap, hit, kick, horn, "ooh", groan, and the interface tones. They stay as the fallback for
   any recorded asset that is missing or not loaded yet (V0.2+), so the game is never silent.
   cuesSnap / cuesResolve decide WHAT to play from an event context — the same choices as before. */
(function(L){
'use strict';

class ProceduralAudio{
  constructor(mixer,opts){ this.mx=mixer; this.o=opts||{}; this.ready=false; }
  /* builds the noise buffer, the crowd bed and the roar (needs a running mixer context) */
  init(){
    if(this.ready) return; const AC=this.mx.ctx; if(!AC) return;
    const crowdIn=this.mx.input('crowd');
    this.bed=AC.createGain(); this.bed.gain.value=0; this.bed.connect(crowdIn);
    this.roarG=AC.createGain(); this.roarG.gain.value=0; this.roarG.connect(crowdIn);
    /* 3 s of pink-ish noise, the raw material of every crowd sound */
    const n=AC.sampleRate*3, buf=AC.createBuffer(1,n,AC.sampleRate), d=buf.getChannelData(0);
    let b0=0,b1=0,b2=0; for(let i=0;i<n;i++){ const w=Math.random()*2-1; b0=.99765*b0+w*.099; b1=.963*b1+w*.2965; b2=.57*b2+w*1.0526; d[i]=(b0+b1+b2+w*.1848)*.16; }
    this.noise=buf;
    /* the crowd bed: two bands of murmur that breathe slowly */
    for(const [f,q,lfo] of [[420,.8,.07],[1250,1.1,.11]]){
      const src=AC.createBufferSource(); src.buffer=buf; src.loop=true; src.loopStart=Math.random();
      const bp=AC.createBiquadFilter(); bp.type='bandpass'; bp.frequency.value=f; bp.Q.value=q;
      const g=AC.createGain(); g.gain.value=.5;
      const o=AC.createOscillator(); o.frequency.value=lfo; const og=AC.createGain(); og.gain.value=.18; o.connect(og); og.connect(g.gain); o.start();
      src.connect(bp); bp.connect(g); g.connect(this.bed); src.start();
    }
    /* the roar: a brighter band the events push up and let fall back */
    const rs=AC.createBufferSource(); rs.buffer=buf; rs.loop=true; const rb=AC.createBiquadFilter(); rb.type='bandpass'; rb.frequency.value=1500; rb.Q.value=.6;
    rs.connect(rb); rb.connect(this.roarG); rs.start();
    this.ready=true;
  }
  setBed(level){ if(this.ready) this.bed.gain.setTargetAtTime(level,this.mx.ctx.currentTime,.4); }

  /* ---------- the effects ---------- */
  /* 09/10 : chaque effet débranche ses nœuds quand sa source s'arrête. Sans ça, filtres et gains restaient branchés au
     bus pour toujours (≈ 8 par action) : Safari ne les libère pas, l'iPad finissait par tuer l'onglet en plein replay. */
  drop(src,nodes){ src.onended=()=>{ for(const n of nodes) try{ n.disconnect(); }catch(e){} }; }
  env(g,t,a,peak,hold,rel){ g.gain.setValueAtTime(0,t); g.gain.linearRampToValueAtTime(peak,t+a); g.gain.setValueAtTime(peak,t+a+hold); g.gain.exponentialRampToValueAtTime(.0001,t+a+hold+rel); }
  noiseHit(t,type,freq,q,peak,a,hold,rel,dest){
    const AC=this.mx.ctx, s=AC.createBufferSource(); s.buffer=this.noise; s.loopStart=Math.random()*2;
    const f=AC.createBiquadFilter(); f.type=type; f.frequency.value=freq; f.Q.value=q||.7;
    const g=AC.createGain(); this.env(g,t,a,peak,hold,rel); s.connect(f); f.connect(g); g.connect(dest||this.mx.input('sfx'));
    s.start(t,Math.random()*2); s.stop(t+a+hold+rel+.05); this.drop(s,[s,f,g]); return f;
  }
  tone(t,type,f0,f1,peak,a,hold,rel,dest){
    const AC=this.mx.ctx, o=AC.createOscillator(); o.type=type; o.frequency.setValueAtTime(f0,t); if(f1&&f1!==f0) o.frequency.exponentialRampToValueAtTime(f1,t+a+hold+rel);
    const g=AC.createGain(); this.env(g,t,a,peak,hold,rel); o.connect(g); g.connect(dest||this.mx.input('sfx')); o.start(t); o.stop(t+a+hold+rel+.05); this.drop(o,[o,g]); return o;
  }
  /* plays one effect `delay` seconds from now; the caller has already checked that sound is on */
  play(name,delay,...args){ const fn=ProceduralAudio.LIB[name]; if(!fn||!this.ready) return; try{ fn.call(this,this.mx.ctx.currentTime+(delay||0)+.01,...args); }catch(e){} }
  ui(kind){
    const seq={on:[[660,.06],[990,.1]],placed:[[880,.05],[1320,.09]],won:[[523,.08],[659,.08],[784,.08],[1047,.22]],lost:[[392,.12],[294,.26]],push:[[587,.08],[587,.14]]}[kind];
    if(!seq) return; const t=this.mx.ctx.currentTime+.01; let d=0; for(const [f,l] of seq){ this.tone(t+d,'triangle',f,f,.12,.005,l*.6,l*.6,this.mx.input('ui')); d+=l*.9; }
  }
}
ProceduralAudio.LIB={
  whistle(t,v=1){ /* pea whistle: two close tones with a fast trill */
    const AC=this.mx.ctx, g=AC.createGain(); this.env(g,t,.015,.07*v,.26,.12); g.connect(this.mx.input('sfx'));
    const tr=AC.createOscillator(); tr.frequency.value=31; const tg=AC.createGain(); tg.gain.value=.5; tr.connect(tg);
    const vca=AC.createGain(); vca.gain.value=.5; tg.connect(vca.gain); vca.connect(g);
    const os=[]; for(const f of [2860,3010]){ const o=AC.createOscillator(); o.type='sine'; o.frequency.value=f; o.connect(vca); o.start(t); o.stop(t+.5); os.push(o); }
    tr.start(t); tr.stop(t+.55); this.drop(tr,[...os,tr,tg,vca,g]); },
  snap(t){ this.noiseHit(t,'lowpass',260,.7,.18,.004,.02,.08); },
  hit(t,v=1){ this.noiseHit(t,'lowpass',380,.9,.5*v,.004,.03,.18); this.tone(t,'sine',95,42,.5*v,.004,.02,.16); },
  kick(t){ this.tone(t,'sine',170,55,.55,.002,.01,.14); this.noiseHit(t,'highpass',1800,.7,.12,.001,.004,.03); },
  horn(t){ const AC=this.mx.ctx, lp=AC.createBiquadFilter(); lp.type='lowpass'; lp.frequency.value=1600; lp.connect(this.mx.input('sfx'));
    const ns=[lp]; let last=null;
    for(const [f,dt] of [[220,0],[277.2,.004],[329.6,.008],[440,.002]]){ const o=AC.createOscillator(); o.type='sawtooth'; o.frequency.value=f; o.detune.value=(Math.random()-.5)*8;
      const g=AC.createGain(); this.env(g,t+dt,.05,.07,1.05,.35); o.connect(g); g.connect(lp); o.start(t); o.stop(t+1.6); ns.push(o,g); last=o; }
    this.drop(last,ns); },
  ooh(t,v=1){ const f=this.noiseHit(t,'bandpass',720,2.2,.55*v,.12,.35,.8,this.mx.input('crowd')); f.frequency.setValueAtTime(720,t); f.frequency.exponentialRampToValueAtTime(330,t+1.2); },
  groan(t){ const f=this.noiseHit(t,'bandpass',520,2,.22,.1,.2,.6,this.mx.input('crowd')); f.frequency.exponentialRampToValueAtTime(260,t+.9); },
  roar(t,v=1,dur=1.6){ const p=this.roarG.gain; p.cancelScheduledValues(t); p.setValueAtTime(p.value,t); p.linearRampToValueAtTime(.55*v,t+.18); p.setValueAtTime(.55*v,t+dur*.45); p.exponentialRampToValueAtTime(.0001,t+dur); }
};

/* ---------- which effects an event calls for (same choices as the previous page sound) ----------
   A cue is [name, delay, ...args]; delay/args undefined where the old code left them out. */
ProceduralAudio.cuesSnap=function(ctx){
  const ty=ctx.callType;
  return ty==='punt'||ty==='field_goal'||ty==='kickoff'||ty==='extra_point' ? [['kick',.45]] : [['snap']];
};
ProceduralAudio.cuesResolve=function(ctx){
  const r=ctx.result, gain=ctx.gain, st=ctx.status, c=[];
  if(r==='touchdown'){ c.push(['horn'],['roar',0,1,3.2]); }
  else if(r==='interception'||r==='fumble_lost'){ c.push(['ooh'],['roar',.5,.85,2.4],['whistle',.9]); }
  else if(r==='field_goal_good'){ c.push(['roar',0,.7,2]); }
  else if(r==='safety'){ c.push(['hit',0,1.2],['roar',.05,1,3],['whistle',.6]); }
  else if(r==='field_goal_missed'||r==='pat_missed'||r==='two_point_failed'){ c.push(['groan']); }
  else if(r==='pat_good'){ c.push(['roar',0,.45,1.4]); }          /* bloc 2 : transformation (comme la page) */
  else if(r==='two_point_good'){ c.push(['roar',0,.9,2.4]); }
  else if(r==='sack'){ c.push(['hit',0,1.2],['roar',.05,.5,1.4],['whistle',.5]); }
  else if(r==='incomplete'){ c.push(['groan'],['whistle',.35,.7]); }
  else if(r==='run'||r==='complete'){ c.push(['hit',0,gain>=10?1:.65]); if(gain>=15) c.push(['roar',0,.45,1.6]); c.push(['whistle',.4,.7]); }
  else if(r==='punt'||r==='kickoff'){ c.push(['whistle',.3,.7]); }
  if(st==='half'){ c.push(['whistle',.9],['whistle',1.4]); }
  if(st==='final'){ c.push(['whistle',.8],['whistle',1.25],['whistle',1.7],['roar',1,1,4]); }
  return c;
};
L.ProceduralAudio=ProceduralAudio;
})(window.GCAudioLib=window.GCAudioLib||{});
