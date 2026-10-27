(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AbyssReview = factory();
})(globalThis, function() {
  'use strict';
  function pairKey(a, b) { return [a,b].sort().join(':'); }
  function random(seed) {
    let value = 2166136261;
    for (const c of seed) value = Math.imul(value ^ c.charCodeAt(0), 16777619);
    return () => { value ^= value << 13; value ^= value >>> 17; value ^= value << 5; return (value >>> 0) / 4294967296; };
  }
  function makePairs(candidates, seed) {
    const rng=random(seed), pairs=[];
    for(let i=0;i<candidates.length;i++) for(let j=i+1;j<candidates.length;j++) {
      const a=candidates[i], b=candidates[j];
      const pa=a.preference_score ?? a.quality_score, pb=b.preference_score ?? b.quality_score;
      pairs.push({a:a.id,b:b.id,key:pairKey(a.id,b.id),uncertainty:Math.abs(pa-pb),noise:rng()});
    }
    const uncertain=[...pairs].sort((a,b)=>a.uncertainty-b.uncertainty||a.noise-b.noise);
    const exploratory=[...pairs].sort((a,b)=>a.noise-b.noise), used=new Set(), result=[];
    while(result.length<pairs.length) {
      const pool=result.length%5===4 ? exploratory : uncertain;
      const next=pool.find(p=>!used.has(p.key));
      used.add(next.key); result.push(next);
    }
    return result;
  }
  function payload(data, answers) {
    const known=new Set(data.candidates.map(c=>c.id));
    const comparisons=Object.values(answers).map(row=>{
      if(!known.has(row.a)||!known.has(row.b)||row.a===row.b||!['a','b','neither'].includes(row.choice)) throw Error('Invalid saved choice');
      const repetitive=row.repetitive||[];
      if(!Array.isArray(repetitive)||repetitive.some(id=>id!==row.a&&id!==row.b))throw Error('Invalid repetitive flag');
      return {a:row.a,b:row.b,choice:row.choice,repetitive:[...new Set(repetitive)]};
    });
    if(comparisons.length>200)throw Error('At most 200 comparisons per gallery');
    return {schema_version:1,batch_id:data.batch_id,comparisons};
  }
  function submissions(data, answers) {
    const p=payload(data,answers), result=[];let pending=[];
    function url(rows,index) {
      const body='Personal image preferences for '+data.reviewer+'.\n\n```abyss-feedback\n'+JSON.stringify({...p,comparisons:rows})+'\n```';
      return 'https://github.com/'+data.repository+'/issues/new?title='+encodeURIComponent('Abyss preferences · '+data.batch_id.slice(0,8)+' · '+index)+'&body='+encodeURIComponent(body);
    }
    for(const row of p.comparisons) {
      if(pending.length && url([...pending,row],result.length+1).length>6800) {result.push(url(pending,result.length+1));pending=[];}
      pending.push(row);
    }
    if(pending.length)result.push(url(pending,result.length+1));
    return result;
  }
  function importAnswers(data, value) {
    if(value.schema_version!==1||value.batch_id!==data.batch_id||!Array.isArray(value.comparisons))throw Error('This backup belongs to another gallery');
    const answers={};
    for(const row of value.comparisons)answers[pairKey(row.a,row.b)]=row;
    payload(data,answers);return answers;
  }
  return {pairKey,makePairs,payload,submissions,importAnswers};
});
