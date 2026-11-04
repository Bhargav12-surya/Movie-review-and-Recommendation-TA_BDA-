const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let catalog=[], history=[], key='', timer, request=0;
async function api(path, data) {
  const response = await fetch('/api/'+path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Request failed');
  return result;
}
function options() {
  const selected=$('movie').value, q=$('search').value.toLowerCase();
  $('movie').innerHTML=catalog.filter(m=>m.title.toLowerCase().includes(q)).slice(0,200).map(m=>`<option value="${esc(m.id)}">${esc(m.title)}</option>`).join('');
  if ([...$('movie').options].some(o=>o.value===selected)) $('movie').value=selected;
  metadata();
}
function metadata() {
  const m=catalog.find(m=>m.id===$('movie').value);
  $('metadata').textContent=m ? m.genres.join(' / ') + (m.rating_count ? ` • ${m.rating_count} dataset ratings` : ' • Demo metadata') : 'No matching titles';
}
function scoreCard(name, r) {
  const score=r.score, color=score===null?'muted':score>60?'positive':score<40?'negative':'balanced';
  return `<div class="score"><div class="row"><strong>${esc(name)}</strong><b class="${color}">${score===null?'No evidence':score+' / 100'}</b></div><div class="track"><div class="${color}" style="width:${score===null?0:score}%"></div></div>${r.evidence.length?`<details><summary>Supporting text</summary><p>${r.evidence.map(esc).join('<br>')}</p></details>`:''}</div>`;
}
async function analyze(version) {
  try {
    const r=await api('analyze',{text:$('review').value});
    if (version!==request) return;
    $('overall').innerHTML=`<span class="eyebrow">OVERALL SENTIMENT</span><div class="big">${r.score===null?'—':r.score}<small>${r.score===null?'':' / 100'}</small></div><strong>${esc(r.label)}</strong><p>${esc(r.method)}</p>`;
    $('aspects').innerHTML=Object.entries(r.aspects).map(([n,v])=>scoreCard(n,v)).join('');
    $('topics').innerHTML=['themes','genres'].map(group=>`<h4>${group==='themes'?'Themes':'Genre mentions'}</h4>`+(Object.entries(r[group]).map(([n,v])=>scoreCard(n,v)+`<p class="muted">${v.coverage}% clause coverage</p>`).join('')||'<p class="muted">No explicit mentions.</p>')).join('');
    $('status').textContent='Analysis ready';
  } catch(e) { if(version===request) $('status').textContent=e.message; }
}
async function refresh() {
  $('history').innerHTML=history.length?history.map(h=>`<p><strong>${esc(catalog.find(m=>m.id===h.id)?.title||h.id)}</strong><br>${h.rating} / 5 <button class="remove secondary" data-id="${esc(h.id)}">Remove</button></p>`).join(''):'<p class="muted">Your history is empty.</p>';
  try {
    const picks=await api('recommend',{history});
    $('recommendations').innerHTML=picks.map((m,i)=>`<article class="pick"><span class="number">${String(i+1).padStart(2,'0')}</span><div><h3>${esc(m.title)}</h3><p>${m.genres.map(esc).join(' · ')}</p><small>${m.reasons.map(esc).join(' · ')}</small><details><summary>Ranking details</summary><p>Genre ${m.components.genre}; theme ${m.components.theme}; aspect ${m.components.aspect}; prior ${m.components.prior}. Rank score ${m.match} (not a probability).</p></details></div></article>`).join('')||'<p>All available titles are in your history.</p>';
  }catch(e){$('recommendations').textContent=e.message;}
}
function storeHistory(){localStorage.setItem(key,JSON.stringify(history));refresh();}
$('review').addEventListener('input',()=>{clearTimeout(timer);const version=++request;$('status').textContent='Analyzing...';timer=setTimeout(()=>analyze(version),300);});
$('search').oninput=options;$('movie').onchange=metadata;
$('example').onclick=()=>{$('review').value='The acting was excellent but the story was weak. The music was beautiful. I loved the friendship theme and the comedy was funny.';$('review').dispatchEvent(new Event('input'));};
$('save').onclick=()=>{const id=$('movie').value;if(!id)return;history=history.filter(h=>h.id!==id);history.push({id,rating:Number($('rating').value),review:$('review').value});history=history.slice(-200);try{storeHistory();$('status').textContent='Saved to your history';}catch(e){$('status').textContent='Browser storage unavailable: '+e.message;}};
$('clear').onclick=()=>{history=[];storeHistory();};
$('history').onclick=e=>{if(e.target.matches('.remove')){history=history.filter(h=>h.id!==e.target.dataset.id);storeHistory();}};
(async()=>{try{const r=await api('catalog');catalog=r.movies;key='cinescope-midsem-'+r.dataset;try{history=JSON.parse(localStorage.getItem(key)||'[]');if(!Array.isArray(history))history=[];}catch{history=[];}history=history.filter(h=>catalog.some(m=>m.id===h.id));$('mode').textContent=r.dataset+' catalog / '+r.model;options();await refresh();await analyze(++request);}catch(e){$('mode').textContent=e.message;}})();
