'use strict';
const assert=require('node:assert/strict');
const core=require('../web/review/core.js');
const data={batch_id:'a'.repeat(32),reviewer:'nikokoren',repository:'nikokoren/abyss',candidates:Array.from({length:16},(_,i)=>({id:i.toString(16).padStart(32,'0'),quality_score:i/16}))};
const pairs=core.makePairs(data.candidates,data.batch_id);
assert.equal(pairs.length,120);assert.equal(new Set(pairs.map(p=>p.key)).size,120);
assert.deepEqual(pairs,core.makePairs(data.candidates,data.batch_id));
const answers=Object.fromEntries(pairs.slice(0,50).map(p=>[p.key,{a:p.a,b:p.b,choice:'a',repetitive:[]} ]));
const urls=core.submissions(data,answers);assert.ok(urls.length>1);assert.ok(urls.every(u=>u.length<=6800));
let rows=[];for(const url of urls){const body=new URL(url).searchParams.get('body');rows.push(...JSON.parse(body.split('```abyss-feedback\n')[1].split('\n```')[0]).comparisons)}
assert.equal(rows.length,50);assert.equal(new Set(rows.map(r=>core.pairKey(r.a,r.b))).size,50);
assert.deepEqual(core.importAnswers(data,core.payload(data,answers)),answers);
assert.throws(()=>core.importAnswers(data,{schema_version:1,batch_id:'wrong',comparisons:[]}));
assert.throws(()=>core.payload(data,{bad:{a:'not-an-image',b:pairs[0].b,choice:'a'}}));
console.log('Review core passed: deterministic/exploratory pairs, safe issue chunking, backups and invalid input.');
