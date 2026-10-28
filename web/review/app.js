(() => {
  'use strict';
  const data=JSON.parse(document.getElementById('gallery-data').textContent), core=globalThis.AbyssReview;
  const el=id=>document.getElementById(id), images=new Map(data.candidates.map(c=>[c.id,c]));
  const pairs=core.makePairs(data.candidates,data.batch_id), storageKey='abyss-review-v1:'+data.reviewer+':'+data.batch_id;
  let answers={}, history=[], cursor=0, mode='original', draftIndex=0, reviewMode=false, renderedPairKey=null;
  const toast=message=>{el('toast').textContent=message;};
  try {const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved)answers=core.importAnswers(data,saved);}catch{toast('Browser storage is unavailable or could not be read. Download a backup to keep your choices.');}
  function save(){try{localStorage.setItem(storageKey,JSON.stringify(core.payload(data,answers)));}catch{toast('Browser storage is unavailable. Download a backup before closing this gallery.');}}
  function current(){return pairs[cursor];}
  function next(){while(!reviewMode&&cursor<pairs.length&&answers[pairs[cursor].key])cursor++;render();}
  function render(){
    const count=Object.keys(answers).length;el('count').textContent=count+' choice'+(count===1?'':'s')+' saved';
    el('progress-bar').style.width=Math.min(100,count/40*100)+'%';el('submit').disabled=!count;el('export').disabled=!count;
    const urls=core.submissions(data,answers);draftIndex=Math.min(draftIndex,Math.max(0,urls.length-1));
    el('submit').textContent=urls.length>1?'Open GitHub draft '+(draftIndex+1)+' of '+urls.length+' →':'Submit choices →';
    const pair=current();el('pair-grid').hidden=!pair;el('pair-actions').hidden=!pair;el('complete').hidden=!!pair;
    el('undo').disabled=!history.length;
    if(!pair)return;
    const saved=answers[pair.key];
    if(renderedPairKey!==pair.key){for(const side of ['a','b'])el('repeat-'+side).checked=!!saved?.repetitive?.includes(pair[side]);renderedPairKey=pair.key;}
    for(const side of ['a','b']){const c=images.get(pair[side]);el('photo-'+side).src=c[mode];el('photo-'+side).alt=c.source_name+' — candidate '+side.toUpperCase();el('source-'+side).textContent=c.source_name;el('stamp-'+side).textContent=(c.fixture?'SYNTHETIC TEST · ':c.recorded_at?'Recording '+new Date(c.recorded_at).toUTCString()+' · ':'Recording time unknown · ')+'frame +'+Math.floor(c.frame_seconds/60)+':'+String(Math.floor(c.frame_seconds%60)).padStart(2,'0');const selected=saved&&saved.choice!=='neither'&&saved[saved.choice]===pair[side];el('image-'+side).closest('.card').dataset.selected=String(!!selected);}
    el('pair-note').textContent='Pair '+(cursor+1)+' of '+pairs.length+' · '+(cursor%5===4?'exploration':'compare by instinct');
  }
  function choose(choice){const pair=current();if(!pair)return;const repetitive=['a','b'].filter(s=>el('repeat-'+s).checked).map(s=>pair[s]);history.push({cursor,key:pair.key,previous:answers[pair.key]});answers[pair.key]={a:pair.a,b:pair.b,choice,repetitive};draftIndex=0;save();cursor++;next();}
  for(const side of ['a','b']){el('choose-'+side).onclick=()=>choose(side);el('image-'+side).onclick=()=>choose(side);}
  el('neither').onclick=()=>choose('neither');el('skip').onclick=()=>{cursor++;next();};
  el('undo').onclick=()=>{const last=history.pop();if(!last)return;if(last.previous)answers[last.key]=last.previous;else delete answers[last.key];cursor=last.cursor;save();render();};
  for(const m of ['paper','original'])el(m+'-mode').onclick=()=>{mode=m;for(const n of ['paper','original'])el(n+'-mode').setAttribute('aria-pressed',String(n===mode));render();};
  el('export').onclick=()=>{const blob=new Blob([JSON.stringify(core.payload(data,answers),null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='abyss-preferences-'+data.batch_id.slice(0,8)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  el('import').onclick=()=>el('import-file').click();el('import-file').onchange=async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>200000)throw Error('Backup is too large');answers={...answers,...core.importAnswers(data,JSON.parse(await file.text()))};cursor=0;save();next();toast('Backup restored.');}catch(error){toast(error.message);}finally{event.target.value='';}};
  el('submit').onclick=()=>{const urls=core.submissions(data,answers);if(!urls.length)return;const currentDraft=draftIndex;window.open(urls[currentDraft],'_blank','noopener,noreferrer');if(urls.length>1)draftIndex=(draftIndex+1)%urls.length;render();toast('Post the prefilled GitHub issue to send draft '+(currentDraft+1)+' of '+urls.length+'. Your browser copy stays saved.');};
  el('review-again').onclick=()=>{reviewMode=true;cursor=0;render();};
  el('edit-choices').onclick=()=>{reviewMode=true;cursor=0;render();};
  document.addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.altKey||['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName))return;if(event.key==='1'){event.preventDefault();choose('a');}if(event.key==='2'){event.preventDefault();choose('b');}if(event.key==='0'){event.preventDefault();choose('neither');}if(event.key.toLowerCase()==='s'){event.preventDefault();cursor++;next();}});
  el('profile').textContent='Personal taste · '+data.reviewer;el('attribution').textContent=data.attribution||'';el('license').textContent=data.license||'';
  if(data.model.status==='ready'){const e=data.model.evaluation;el('model-status').textContent='Model snapshot: '+data.model.comparisons+' comparisons · '+(e&&e.status==='measured'?'held-out checks available':'awaiting independent validation');}
  else el('model-status').textContent=data.model.comparisons?'Model snapshot: '+data.model.comparisons+' submitted comparisons · keep teaching with fresh scenes.':'Your choices will guide future selections. Aim for 30–50 comparisons.';
  if(data.review_status==='no_review_needed'){
    document.querySelector('h1').textContent='No review needed.';
    document.querySelector('.intro p').textContent='These snapshots show essentially the same view. No preference choices are needed for this batch.';
    el('complete').querySelector('.eyebrow').textContent='SIMILAR CAMERA VIEWS';
    el('complete').querySelector('h2').textContent='Nothing useful to compare this time.';
    el('complete').querySelector('p').textContent=(data.candidates[0]?.source_name||'This camera')+' stays in your display rotation. Review a fresh batch when the view changes.';
    el('review-again').hidden=true;el('goal').hidden=true;
    document.querySelector('.toolbar').hidden=true;document.querySelector('.bottom').hidden=true;
  }
  next();
})();
