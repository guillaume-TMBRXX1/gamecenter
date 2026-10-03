/* GameCenter Audio System — AssetLoader (V0.1)
   Recorded assets (pre-generated offline, never fetched from ElevenLabs during a game) are listed in
   /audio/manifest.json and served with content-hashed names, so the browser can cache them for a year.
   Decoded buffers are kept in an LRU under a memory budget (smaller on phones); a load that takes too
   long is dropped and the procedural sound plays instead. V0.1: the manifest is empty, nothing is fetched
   beyond it. */
(function(L){
'use strict';
class AssetLoader{
  constructor(mixer,opts){
    this.mx=mixer; this.o=opts||{}; this.base=this.o.base||'/audio/';
    const mem=navigator.deviceMemory||4, small=/iPhone|iPod|Android.+Mobile/i.test(navigator.userAgent||'');
    this.budget=this.o.budget||((small||mem<=2)?24:64)*1024*1024;   /* bytes of decoded PCM */
    this.cache=new Map(); this.bytes=0; this.pending=new Map(); this.manifest=null; this._mf=null;
  }
  /* slow link or data saver: callers keep to the essentials (no music, one crowd bed) */
  lite(){ const c=navigator.connection; return !!(c&&(c.saveData||/(^|-)2g$/.test(c.effectiveType||''))); }
  loadManifest(){
    if(this._mf) return this._mf;
    this._mf=fetch(this.base+'manifest.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null)
      .then(m=>{ this.manifest=m&&Array.isArray(m.assets)?m:{version:0,assets:[]}; this.byId=new Map(this.manifest.assets.map(a=>[a.id,a])); return this.manifest; });
    return this._mf;
  }
  has(id){ return !!(this.byId&&this.byId.get(id)); }
  /* resolves to an AudioBuffer, or null (unknown id, network error, or slower than timeoutMs) */
  get(id,timeoutMs){
    const hit=this.cache.get(id); if(hit){ this.cache.delete(id); this.cache.set(id,hit); return Promise.resolve(hit.buf); }
    const a=this.byId&&this.byId.get(id); if(!a||!this.mx.ctx) return Promise.resolve(null);
    let p=this.pending.get(id);
    if(!p){
      p=fetch(this.base+a.file).then(r=>r.ok?r.arrayBuffer():null)
        .then(ab=>ab?new Promise((res)=>{ try{ const q=this.mx.ctx.decodeAudioData(ab,res,()=>res(null)); if(q&&q.catch) q.catch(()=>res(null)); }catch(e){ res(null); } }):null)
        .then(buf=>{ this.pending.delete(id); if(buf) this.put(id,buf); return buf; })
        .catch(()=>{ this.pending.delete(id); return null; });
      this.pending.set(id,p);
    }
    if(!timeoutMs) return p;
    return Promise.race([p,new Promise(r=>setTimeout(()=>r(null),timeoutMs))]);
  }
  prefetch(ids){ for(const id of ids||[]) this.get(id); }
  put(id,buf){
    const size=buf.length*buf.numberOfChannels*4;
    this.cache.set(id,{buf,size}); this.bytes+=size;
    for(const [k,v] of this.cache){ if(this.bytes<=this.budget) break; if(k===id) continue; this.cache.delete(k); this.bytes-=v.size; }
  }
  clear(){ this.cache.clear(); this.bytes=0; }
  stats(){ return {entries:this.cache.size,bytes:this.bytes,budget:this.budget,pending:this.pending.size,assets:this.manifest?this.manifest.assets.length:null}; }
}
L.AssetLoader=AssetLoader;
})(window.GCAudioLib=window.GCAudioLib||{});
