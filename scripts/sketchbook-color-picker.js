/* Inline, touch-friendly colour controls shared by ink and paper. */
(() => {
  'use strict';
  const style = document.createElement('style');
  style.textContent = `.sketch-color{width:100%;display:flex;flex-direction:column;gap:9px}.sketch-color button{width:100%;text-align:left;display:flex;align-items:center;gap:10px;min-height:44px}.sketch-color .chip{width:28px;height:28px;border:1px solid #bdb8ad;border-radius:6px;flex:none}.sketch-color .panel{display:flex;flex-direction:column;gap:12px}.sketch-color .panel[hidden]{display:none}.sketch-color .shade{height:180px;position:relative;border-radius:9px;touch-action:none;outline-offset:3px;background:linear-gradient(to top,#000,transparent),linear-gradient(to right,#fff,transparent),var(--hue)}.sketch-color .cursor{position:absolute;width:22px;height:22px;border:2px solid white;box-shadow:0 0 0 1px #555;border-radius:50%;transform:translate(-50%,-50%);pointer-events:none}.sketch-color .hue{width:100%;height:26px;margin:0;appearance:none;-webkit-appearance:none;border-radius:20px;background:linear-gradient(to right,red,#ff0,#0f0,#0ff,#00f,#f0f,red)}.sketch-color .hue::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:28px;height:28px;background:var(--hue);border:3px solid white;box-shadow:0 0 0 1px #aaa;border-radius:50%}.sketch-color .hue::-moz-range-thumb{width:22px;height:22px;background:var(--hue);border:3px solid white;border-radius:50%}.sketch-color .rgb{display:flex;gap:8px}.sketch-color label{flex:1;min-width:0;font-size:12px;color:#6b6558}.sketch-color input[type=number]{width:100%;min-height:40px;border:1px solid #d8d3c6;border-radius:7px;padding:7px;font:inherit;background:white;color:#292620}.sketch-color .done{justify-content:center;background:#292620;color:white}.sketch-color small{font-size:11px;color:#8a8373}`;
  document.head.append(style);
  function rgb(h,s,v) {
    const f=n=>{const k=(n+h/60)%6;return Math.round(255*v*(1-s*Math.max(0,Math.min(k,4-k,1))))};
    return [f(5),f(3),f(1)];
  }
  function hsv(hex) {
    const a=hex.match(/\w\w/g).map(x=>parseInt(x,16)/255),max=Math.max(...a),min=Math.min(...a),d=max-min;
    let h=d===0?0:max===a[0]?((a[1]-a[2])/d)%6:max===a[1]?(a[2]-a[0])/d+2:(a[0]-a[1])/d+4;
    return [(h*60+360)%360,max?d/max:0,max];
  }
  for (const [id,title] of [['colorPicker','Ink colour'],['paperColorPicker','Paper colour']]) {
    const input=document.getElementById(id);if(!input)continue;
    const root=document.createElement('div');root.className='sketch-color';
    root.innerHTML=`<button type="button" aria-expanded="false"><span class="chip"></span><span class="caption"></span></button><div class="panel" hidden><div class="shade" tabindex="0" role="group" aria-label="${title}: drag to choose saturation and brightness; arrow keys fine-tune"><span class="cursor"></span></div><small>Drag to choose a shade. Arrow keys fine-tune it.</small><label>Hue <output></output><input class="hue" aria-label="${title} hue" type="range" min="0" max="359" value="0"></label><div class="rgb">${['R','G','B'].map(c=>`<label>${c}<input type="number" min="0" max="255" step="1" aria-label="${title} ${c}"></label>`).join('')}</div><button class="done" type="button">Done</button></div>`;
    input.after(root);input.hidden=true;
    const toggle=root.querySelector('button'),panel=root.querySelector('.panel'),shade=root.querySelector('.shade'),cursor=root.querySelector('.cursor'),hue=root.querySelector('.hue'),fields=[...root.querySelectorAll('input[type=number]')];
    let [h,s,v]=hsv(input.value),emitting=false;
    function paint(){
      root.style.setProperty('--hue',`hsl(${h} 100% 50%)`);
      root.querySelector('.chip').style.background=input.value;
      root.querySelector('.caption').textContent=`${title} · ${input.value.toUpperCase()}`;
      cursor.style.left=`${s*100}%`;cursor.style.top=`${(1-v)*100}%`;
      hue.value=h;root.querySelector('output').textContent=`${Math.round(h)}°`;
      rgb(h,s,v).forEach((n,i)=>fields[i].value=n);
    }
    function commit(){input.value='#'+rgb(h,s,v).map(n=>n.toString(16).padStart(2,'0')).join('');emitting=true;input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));emitting=false;paint()}
    function sync(){[h,s,v]=hsv(input.value);paint()}
    function close(){panel.hidden=true;toggle.setAttribute('aria-expanded','false')}
    toggle.onclick=()=>{sync();panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden))};
    root.querySelector('.done').onclick=()=>{close();toggle.focus()};
    root.addEventListener('keydown',e=>{if(e.key==='Escape'){close();toggle.focus()}});
    function point(e){const b=shade.getBoundingClientRect();s=Math.max(0,Math.min(1,(e.clientX-b.left)/b.width));v=1-Math.max(0,Math.min(1,(e.clientY-b.top)/b.height));commit()}
    shade.onpointerdown=e=>{e.preventDefault();shade.setPointerCapture(e.pointerId);point(e)};
    shade.onpointermove=e=>{if(shade.hasPointerCapture(e.pointerId))point(e)};
    shade.onpointerup=e=>{if(shade.hasPointerCapture(e.pointerId)){point(e);shade.releasePointerCapture(e.pointerId)}};
    shade.onkeydown=e=>{const d=e.shiftKey?.1:.01;if(e.key==='ArrowRight')s=Math.min(1,s+d);else if(e.key==='ArrowLeft')s=Math.max(0,s-d);else if(e.key==='ArrowUp')v=Math.min(1,v+d);else if(e.key==='ArrowDown')v=Math.max(0,v-d);else return;e.preventDefault();commit()};
    hue.oninput=()=>{h=+hue.value;commit()};
    fields.forEach(field=>field.oninput=()=>{const a=fields.map(f=>Math.max(0,Math.min(255,Number(f.value)||0)));input.value='#'+a.map(n=>Math.round(n).toString(16).padStart(2,'0')).join('');sync();input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}))});
    input.addEventListener('input',()=>{if(!emitting)sync()});
    document.getElementById('palette')?.addEventListener('click',sync);
    for(const button of document.querySelectorAll('#inkLayerBtn,#colorLayerBtn'))button.addEventListener('click',sync);
    paint();
  }
})();
