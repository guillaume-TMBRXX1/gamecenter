// Audio System V0.1 — tests du AudioEventMapper (Node seul, sans navigateur)
//   node outils/audio/test_mapper_v01.js [dossier data/weeks]
// Vérifie sur toutes les semaines : chaque action produit au moins un événement, les fins de match ont
// VICTORY / DEFEAT / TIE (point de vue HOME), le contexte est cohérent (scores, meneur, TD décisif en fin de match).
const fs=require('fs'), path=require('path'), vm=require('vm');
const HERE=path.resolve(__dirname,'..','..');
const ctx={window:{}}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(HERE,'static/audio/AudioEventMapper.js'),'utf8'),ctx);
const M=ctx.window.GCAudioLib.AudioEventMapper;
const DATA=process.argv[2]||path.join(HERE,'data/weeks');
let plays=0, fails=[], winning=[], counts={};
const ok=(c,msg)=>{ if(!c) fails.push(msg); };
for(const w of fs.readdirSync(DATA)) for(const f of fs.readdirSync(path.join(DATA,w,'games'))){
  const feed=JSON.parse(fs.readFileSync(path.join(DATA,w,'games',f))), G=feed.game;
  const g={id:G.id,home:G.home.abbr,away:G.away.abbr,mode:'live',speed:1,plays:feed.plays,qs:G.quarter_seconds};
  let prev={quarter:0,seq:-1}, wp=null;
  feed.plays.forEach((P,i)=>{
    plays++;
    const s=M.mapSnap(g,P,prev), r=M.mapResolve(g,P,wp), c=r.ctx, tag=`${G.id}#${i}`;
    for(const e of s.events.concat(r.events)) counts[e]=(counts[e]||0)+1;
    ok(s.events.length>=1&&r.events.length>=1||P.result==='kickoff',`${tag}: aucun événement`);
    ok(c.score.home===P.after.score.home&&c.score.away===P.after.score.away,`${tag}: score après`);
    ok(c.importance>=0&&c.importance<=1,`${tag}: importance hors 0..1`);
    ok(['HOME','AWAY'].includes(c.team),`${tag}: équipe`);
    if(P.result==='interception'||P.result==='fumble_lost') ok(c.team===(P.offense==='home'?'AWAY':'HOME'),`${tag}: perte de balle attribuée à la défense`);
    if(c.isGameWinning){ ok(c.isLeadChange&&c.isLateGame,`${tag}: TD décisif incohérent`); winning.push(`${tag} ${P.result} ${JSON.stringify(c.scoreBefore)}→${JSON.stringify(c.score)} Q${c.quarter} ${c.timeRemaining}s imp=${c.importance}`); }
    if(P.after.status==='final') ok(r.events.includes('GAME_END')&&(r.events.includes('VICTORY')||r.events.includes('DEFEAT')||r.events.includes('TIE')),`${tag}: fin sans VICTORY/DEFEAT/TIE`);
    if(P.result==='touchdown') ok(r.events.includes('TOUCHDOWN'),`${tag}: TD manquant`);
    prev={quarter:s.ctx.quarter,seq:P.seq}; wp=P.win_prob_home;
  });
}
console.log(`${plays} actions · ${fails.length} échec(s)`); fails.slice(0,10).forEach(x=>console.log('  ✗',x));
console.log(`TD / FG décisifs en fin de match : ${winning.length}`); winning.slice(0,4).forEach(x=>console.log('  ',x));
// un TD ordinaire vs un TD qui donne l'avantage en fin de match
const gx={id:'x',home:'VEC',away:'CTX',mode:'live',speed:1,qs:180,plays:[]};
const mk=(q,clk,before,after)=>{ const a={seq:1,quarter:q,clock_start:clk+5,clock_end:clk,offense:'home',los_x:100,down:1,to_go:10,call:{type:'pass'},result:'touchdown',gain:10,text:'TD',after:{score:after,status:'live'},win_prob_home:.7};
  gx.plays=[{seq:0,after:{score:before}},a]; return M.mapResolve(gx,a,.4).ctx; };
const t1=mk(1,150,{home:0,away:0},{home:7,away:0}), t2=mk(4,30,{home:21,away:24},{home:28,away:24});
console.log('TD 1er quart-temps :', JSON.stringify({isGameWinning:t1.isGameWinning,isLeadChange:t1.isLeadChange,importance:t1.importance}));
console.log('TD décisif Q4 0:30 :', JSON.stringify({isGameWinning:t2.isGameWinning,isLeadChange:t2.isLeadChange,isLateGame:t2.isLateGame,importance:t2.importance}));
if(!(t2.isGameWinning&&!t1.isGameWinning&&t2.importance>t1.importance)) fails.push('distinction TD ordinaire / TD décisif');
process.exit(fails.length?1:0);
