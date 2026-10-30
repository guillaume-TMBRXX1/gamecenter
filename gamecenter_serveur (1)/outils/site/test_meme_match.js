// Same Game Combo (section 86, 30/10/2026) — même cote dans la page et sur le serveur (sans navigateur).
//   node outils/site/test_meme_match.js          (depuis « gamecenter_serveur (1) »)
// Prend sgpPrice (gamecenter_source.html) et moteur/meme_match.py, et compare sur toutes les affiches des semaines du
// dépôt (cotes d'avant-match publiées) chaque combiné possible de 2 ou 3 sélections : même refus, même cote (± 0,2 %),
// même cote d'égalité. Lancé par tests_navigateur.sh.
const fs=require('fs'), path=require('path'), {execFileSync}=require('child_process');
const ROOT=path.resolve(__dirname,'..','..');
const src=fs.readFileSync(path.join(ROOT,'gamecenter_source.html'),'utf8');
const a=src.indexOf('const SG_MAX='), b=src.indexOf('const SG_WHY=');
if(a<0||b<0){ console.log('ÉCHEC : sgpPrice introuvable'); process.exit(1); }
const sgpPrice=new Function('SEASON','SERVER','decOf',src.slice(a,b)+'; return sgpPrice;')({},null,x=>x>0?1+x/100:1+100/(-x));
const dec=x=>x>0?1+x/100:1+100/(-x);
const cases=[];
for(const w of fs.readdirSync(path.join(ROOT,'data','weeks')).filter(x=>x.startsWith('week_')).sort().slice(-2)){
  const dir=path.join(ROOT,'data','weeks',w,'games');
  for(const f of fs.readdirSync(dir).filter(x=>/^w\d/.test(x))){
    const o=JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')).game.pregame_odds;
    if(!o||o.spread_home==null) continue;
    const pr=(mk,sd)=>mk==='ml'?dec(o.ml[sd]):mk==='sp'?dec(o.spread_prices[sd]):dec(o.total_prices[sd]);
    const S={ml:['home','away'],sp:['home','away'],tot:['over','under']};
    for(const mks of [['ml','sp'],['ml','tot'],['sp','tot'],['ml','sp','tot']]){
      const combos=mks.reduce((acc,mk)=>acc.flatMap(c=>S[mk].map(sd=>c.concat([[mk,sd]]))),[[]]);
      for(const legs of combos) cases.push({o,legs,decs:legs.map(l=>pr(...l))}); } } }
const py=JSON.parse(execFileSync('python3',['-c',`
import json,sys
from moteur import meme_match as MM
C=json.load(sys.stdin)
print(json.dumps([MM.prix(c["o"],[tuple(l) for l in c["legs"]],c["decs"]) for c in C]))`],{cwd:ROOT,input:JSON.stringify(cases),maxBuffer:1<<28}).toString());
let bad=0, n=0, acc=0;
cases.forEach((c,i)=>{ const j=sgpPrice(c.o,c.legs,c.decs), p=py[i]; n++;
  const same=j.refus||p.refus ? j.refus===p.refus : Math.abs(j.price_dec-p.price_dec)<=0.002*p.price_dec&&(p.push_price==null)===(j.push_price==null)&&(p.push_price==null||Math.abs(j.push_price-p.push_price)<=0.002*p.push_price);
  if(!j.refus&&!p.refus) acc++;
  if(!same&&bad++<5) console.log('  ✗',JSON.stringify(c.legs),'page',JSON.stringify(j),'serveur',JSON.stringify(p)); });
console.log(`  ${bad?'✗':'✓'} ${n} combinés (${acc} acceptés) : même cote dans la page et sur le serveur${bad?` · ${bad} écarts`:''}`);
console.log(bad?`ÉCHEC (${bad})`:'OK'); process.exit(bad?1:0);
