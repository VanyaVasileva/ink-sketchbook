"""Natural tattoo-style stippling, retained for zoom, undo and recordings."""

HELPERS = r'''// natural-stipple-v1
const stippleTool = document.getElementById('stippleTool');
const stippleSettings = document.getElementById('stippleSettings');
const stippleArea = document.getElementById('stippleArea');
const stippleGrain = document.getElementById('stippleGrain');
const stippleFlow = document.getElementById('stippleFlow');
let stippleStroke = null;
function stippleSelected() { return stippleTool.value === 'stipple' && activeLayer === 'ink' && mode === 'draw'; }
function syncStippleControls() {
  stippleSettings.hidden = stippleTool.value !== 'stipple';
  for (const id of ['stippleArea','stippleGrain','stippleFlow'])
    document.getElementById(id+'Value').textContent = document.getElementById(id).value;
}
stippleTool.addEventListener('change', () => { if (drawing) endStroke(); syncStippleControls(); });
for (const input of [stippleArea,stippleGrain,stippleFlow]) input.addEventListener('input',syncStippleControls);
syncStippleControls();

function stippleRandom(seed) {
  let state = seed >>> 0 || 1;
  return () => { state ^= state << 13; state ^= state >>> 17; state ^= state << 5; return (state >>> 0) / 4294967296; };
}
function paintStipple(target, op) {
  // Replay the same irregular geometry at every resolution. No circular stamps,
  // tiled texture, blur filter or fresh randomness during export/recording.
  const random = stippleRandom(op.seed);
  target.save();
  target.globalCompositeOperation = 'source-over';
  target.fillStyle = op.color;
  for (let i=0; i<op.count; i++) {
    const theta=random()*Math.PI*2;
    const reach=Math.pow(random(),0.68)*op.radius;
    const x=op.x+Math.cos(theta)*reach, y=op.y+Math.sin(theta)*reach;
    const edge=reach/Math.max(0.001,op.radius);
    if(random()>1-edge*edge*0.82) continue;
    const size=op.grain*(0.23+Math.pow(random(),1.7)*0.92);
    const angle=op.angle+(random()-0.5)*Math.PI*1.7;
    const fleck=random()<0.17;
    const length=size*(fleck?1.9+random()*1.5:0.85+random()*0.65);
    const width=size*(0.55+random()*0.48);
    const vertices=6+Math.floor(random()*4);
    const ca=Math.cos(angle),sa=Math.sin(angle);
    target.globalAlpha=(0.30+random()*0.65)*(0.82-0.20*edge);
    target.beginPath();
    for(let j=0;j<vertices;j++) {
      const a=j/vertices*Math.PI*2;
      const irregular=0.64+random()*0.54;
      const u=Math.cos(a)*length*irregular/2, v=Math.sin(a)*width*irregular/2;
      const px=x+u*ca-v*sa,py=y+u*sa+v*ca;
      if(j===0) target.moveTo(px,py); else target.lineTo(px,py);
    }
    target.closePath(); target.fill();
  }
  target.restore();
}
function emitStipple(x,y,pressure,angle,amount) {
  const stroke=stippleStroke;
  if(!stroke || !(amount>0)) return;
  stroke.carry+=amount;
  const count=Math.floor(stroke.carry); stroke.carry-=count;
  if(!count) return;
  const unit=stroke.unit;
  const op={kind:'stipple',mode:'draw',color:stroke.color,x,y,angle,
    radius:stroke.area*unit/2*(0.76+pressure*0.32),
    grain:stroke.grain*unit*(0.84+pressure*0.24),
    count,seed:(Math.random()*4294967296)>>>0};
  paintStipple(ctx,op);
  artworkRevision++;
  if(detailVectorValid && activeDetailStroke) activeDetailStroke.ops.push(op);
  drawDetailOpLive(op);
}
function beginStipple(e) {
  const p=getPos(e), pressure=e.pointerType==='pen'?Math.max(0.06,e.pressure):0.5;
  stippleStroke={last:p,pressure,angle:0,color:currentColor,unit:getDisplayDpr(),
    area:Number(stippleArea.value),grain:Number(stippleGrain.value),flow:Number(stippleFlow.value)/100,
    carry:0,clock:performance.now(),raf:null};
  emitStipple(p.x,p.y,pressure,0,5+stippleStroke.flow*12);
  const tick=now=>{
    const s=stippleStroke;
    if(!s || !drawing) return;
    const dt=Math.min(40,Math.max(0,now-s.clock)); s.clock=now;
    emitStipple(s.last.x,s.last.y,s.pressure,s.angle,dt*s.flow*(0.5+s.pressure*0.9));
    s.raf=requestAnimationFrame(tick);
  };
  stippleStroke.raf=requestAnimationFrame(tick);
}
function continueStipple(e) {
  const s=stippleStroke,p=getPos(e),prev=s.last;
  const pressure=e.pointerType==='pen'?Math.max(0.06,e.pressure):0.5;
  const distance=Math.hypot(p.x-prev.x,p.y-prev.y);
  if(distance>0.001) {
    const angle=Math.atan2(p.y-prev.y,p.x-prev.x);
    const steps=Math.max(1,Math.ceil(distance/Math.max(s.unit*1.8,s.area*s.unit*0.075)));
    const amount=distance/s.unit*s.flow*(3.4+pressure*5.5)/steps;
    for(let i=0;i<steps;i++) {
      const t=(i+Math.random())/steps;
      emitStipple(prev.x+(p.x-prev.x)*t,prev.y+(p.y-prev.y)*t,pressure,angle,amount);
    }
    s.angle=angle; moved=true;
  }
  s.last=p; s.pressure=pressure;
  lastPenPos={x:p.x,y:p.y};
}
function stopStipple() {
  if(!stippleStroke) return;
  cancelAnimationFrame(stippleStroke.raf); stippleStroke=null;
}
'''

CONTROLS = '''<div class="slider-group" id="stippleToolGroup">
        <label for="stippleTool">Ink brush</label>
        <select id="stippleTool" style="width:100%;padding:8px;border:1px solid #d8d3c6;border-radius:7px;background:#fff;color:#2a2620;font:inherit">
          <option value="pen">Ink pen</option><option value="stipple">Natural stipple</option>
        </select>
      </div>
      <div id="stippleSettings" hidden>
        <div class="slider-group"><label for="stippleArea">Shading area <b id="stippleAreaValue">34</b></label><input id="stippleArea" type="range" min="8" max="120" value="34" step="1"></div>
        <div class="slider-group"><label for="stippleGrain">Speck size <b id="stippleGrainValue">1.4</b></label><input id="stippleGrain" type="range" min="0.4" max="3" value="1.4" step="0.1"></div>
        <div class="slider-group"><label for="stippleFlow">Ink flow <b id="stippleFlowValue">38</b></label><input id="stippleFlow" type="range" min="5" max="100" value="38" step="1"></div>
        <small style="color:#6b6558;line-height:1.5;display:block;margin:6px 0 10px">Uneven ink specks for natural shading. Sweep lightly; slow down or pass again to deepen the shadows. Use on the Ink layer.</small>
      </div>
      '''


def apply_stipple(text: str) -> str:
    if '// natural-stipple-v1' in text:
        return text

    def change(old, new, label):
        nonlocal text
        if old not in text:
            raise SystemExit('Natural stipple: missing ' + label)
        text = text.replace(old, new, 1)

    change('<div class="row palette" id="palette"></div>', CONTROLS + '<div class="row palette" id="palette"></div>', 'brush controls')
    change('function startStroke(e) {', HELPERS + '\nfunction startStroke(e) {', 'brush controller')
    change("  if (activeLayer === 'color' && mode === 'draw') beginColorBrush(e);", "  if (stippleSelected()) beginStipple(e);\n  else if (activeLayer === 'color' && mode === 'draw') beginColorBrush(e);", 'stroke start')
    change('function continueStroke(e) {\n  if (!drawing) return;', 'function continueStroke(e) {\n  if (!drawing) return;\n  if (stippleStroke) { continueStipple(e); return; }', 'stroke movement')
    change('function endStroke() {\n  if (!drawing) return;', 'function endStroke() {\n  if (!drawing) { stopStipple(); return; }\n  if (stippleStroke) { stopStipple(); drawing=false; commitDetailStroke(); saveHistory(); return; }', 'stroke finish')
    change('function paintDetailOp(op, target = detailCtx) {\n  if (!op) return;', "function paintDetailOp(op, target = detailCtx) {\n  if (!op) return;\n  if (op.kind === 'stipple') { paintStipple(target,op); return; }", 'zoom renderer')
    change('      const paint = op => {', "      const paint = op => {\n        if (op.kind === 'stipple') { paintStipple(target,op); return; }", 'recording renderer')
    change("  const samples=(mode==='erase' || colorBrushStroke)", "  const samples=(mode==='erase' || colorBrushStroke || stippleStroke)", 'Pencil samples')
    change("if (drawing && (mode === 'erase' || colorBrushStroke) && e.type === 'pointerup')", "if (drawing && (mode === 'erase' || colorBrushStroke || stippleStroke) && e.type === 'pointerup')", 'final Pencil position')
    change("  } else if (activePointers.size === 2) {\n    if (colorBrushStroke)", "  } else if (activePointers.size === 2) {\n    stopStipple();\n    if (colorBrushStroke)", 'pinch interruption')
    return text
