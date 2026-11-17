// Splits rosters.js into the two files the game loads: current (small, loads first) and all-time (loads on demand).
const fs=require('fs'), path=require('path');
const here=__dirname, out=path.join(here,'dist');
const src=fs.readFileSync(path.join(here,'rosters.js'),'utf8');
const ctx={}; new Function('ctx', src.replace('var ROSTER_SEASON','ctx.ROSTER_SEASON').replace('var TEAMS','ctx.TEAMS'))(ctx);
const meta=ctx.TEAMS.map(t=>({id:t.id,city:t.city,name:t.name,div:t.div,color:t.color,ink:t.ink,ff:t.ff,cff:t.cff,c:t.c}));
const all={}; ctx.TEAMS.forEach(t=>all[t.id]=t.a);
fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(path.join(out,'rosters-current.js'),'/* THE 53 current rosters, '+ctx.ROSTER_SEASON+' season. Name|POS|rarity|aliases */\nwindow.T53_SEASON='+ctx.ROSTER_SEASON+';\nwindow.T53_TEAMS='+JSON.stringify(meta)+';\n');
fs.writeFileSync(path.join(out,'rosters-alltime.js'),'/* THE 53 all-time franchise rosters. Name|POS|rarity|aliases */\nwindow.T53_ALL='+JSON.stringify(all)+';\n');
const imgs=JSON.parse(fs.readFileSync(path.join(here,'images.json'),'utf8'));
const facesCache=process.env.FACES_CACHE||path.join(here,'faces_cache');
fs.rmSync(path.join(out,'img'),{recursive:true,force:true}); fs.rmSync(path.join(out,'faces'),{recursive:true,force:true});
fs.mkdirSync(path.join(out,'img'),{recursive:true}); fs.mkdirSync(path.join(out,'faces'),{recursive:true});
let faceCount=0;
for(const id in imgs){
  const arr=imgs[id].c; let last=arr.length; while(last>0 && !arr[last-1]) last--;
  fs.writeFileSync(path.join(out,'img','current-'+id+'.json'), JSON.stringify(arr.slice(0,last)));   /* ids: suggestion photos */
  const faces=arr.slice(0,last).map(i=>{ const f=i && path.join(facesCache,i+'.webp'); if(f && fs.existsSync(f)){ faceCount++; return fs.readFileSync(f).toString('base64'); } return ''; });
  fs.writeFileSync(path.join(out,'faces','current-'+id+'.json'), JSON.stringify(faces));            /* thumbnails, served with the game */
}
console.log('faces', faceCount);
console.log('ok', fs.statSync(path.join(out,'rosters-current.js')).size, fs.statSync(path.join(out,'rosters-alltime.js')).size);
