"""Replace the color brush's new strokes with a plain opaque canvas marker."""


def _apply_solid_marker_base(text: str) -> str:
    text = text.replace('<b id="colorBrushSizeValue">80</b>', '<b id="colorBrushSizeValue">24</b>')
    text = text.replace('id="colorBrushSize" min="2" max="240" step="1" value="80"',
                        'id="colorBrushSize" min="2" max="240" step="1" value="24"')
    text = text.replace('Number(colorBrushSize.value) || 80', 'Number(colorBrushSize.value) || 24')
    sync = "colorBrushSize.value = '24'; colorBrushSizeValue.textContent = '24';"
    if sync not in text:
        anchor = "const colorBrushSizeValue = document.getElementById('colorBrushSizeValue');"
        if text.count(anchor) != 1:
            raise SystemExit('Marker opening size anchor missing')
        text = text.replace(anchor, anchor + '\n' + sync, 1)
    if '// simple-solid-marker-v5' in text:
        return apply_rounded_taper(text)
    anchor = '  const sweep=op.sweep,outline=op.outline;'
    if text.count(anchor) != 1:
        raise SystemExit('Solid marker renderer anchor missing or ambiguous')
    text = text.replace(anchor, r'''  // simple-solid-marker-v5
  if (op.marker) {
    const path = op.sweep;
    if (!path || !path.length) return;
    target.save();
    target.globalCompositeOperation = 'source-over';
    target.globalAlpha = 1;
    target.shadowColor = 'transparent'; target.shadowBlur = 0;
    target.shadowOffsetX = 0; target.shadowOffsetY = 0;
    target.filter = 'none';
    target.strokeStyle = op.color; target.fillStyle = op.color;
    target.lineWidth = op.width; target.lineCap = 'round'; target.lineJoin = 'round';
    target.beginPath();
    if (path.length === 1) {
      // A single tap is one round dot, not a chain of repeated stamps.
      target.arc(path[0][0], path[0][1], op.width / 2, 0, Math.PI * 2);
      target.fill();
    } else {
      target.moveTo(path[0][0], path[0][1]);
      for (let i = 1; i < path.length; i++) target.lineTo(path[i][0], path[i][1]);
      target.stroke();
    }
    target.restore(); return;
  }
  // Retain replay support for strokes created before the plain marker.
''' + anchor, 1)
    first = text.index('function beginColorBrush(e) {')
    last = text.index('function startStroke(e) {', first)
    text = text[:first] + r'''function beginColorBrush(e) {
  const base = document.createElement('canvas');
  base.width = colorCanvas.width; base.height = colorCanvas.height;
  base.getContext('2d').drawImage(colorCanvas, 0, 0);
  const p = points[0];
  const size = Math.max(2, Number(colorBrushSize.value) || 24) * getDisplayDpr();
  const sample = [p.x, p.y, size / 2];
  const op = {kind:'brush', mode:'draw', marker:true, width:size, color:currentColor, sweep:[sample]};
  colorBrushStroke = {base, size, color:currentColor, op, bounds:null};
  if (detailVectorValid && activeDetailStroke) activeDetailStroke.ops = [op];
  inputModeEl.textContent = '(Solid marker — fixed width)';
  paintColorBrushLive([sample]);
}

function includeColorBrushBounds(sample) {
  const stroke = colorBrushStroke, [x,y,r] = sample;
  if (!stroke.bounds) stroke.bounds = {left:x-r, top:y-r, right:x+r, bottom:y+r};
  else {
    stroke.bounds.left = Math.min(stroke.bounds.left, x-r);
    stroke.bounds.top = Math.min(stroke.bounds.top, y-r);
    stroke.bounds.right = Math.max(stroke.bounds.right, x+r);
    stroke.bounds.bottom = Math.max(stroke.bounds.bottom, y+r);
  }
}

function paintColorBrushLive(sweep) {
  const stroke = colorBrushStroke;
  for (const sample of sweep) includeColorBrushBounds(sample);
  const op = {kind:'brush', mode:'draw', marker:true, width:stroke.size, color:stroke.color, sweep};
  // Draw each incoming segment immediately with the same renderer used by
  // zoom replay and recordings. No follower, stamps, or pressure simulation.
  paintColorBrushShape(colorCtx, op);
  drawDetailOpLive(op); artworkRevision++;
}

function renderColorBrushNow() {
  const stroke = colorBrushStroke, bounds = stroke && stroke.bounds;
  if (!bounds) return;
  const x = Math.max(0, Math.floor(bounds.left)-2), y = Math.max(0, Math.floor(bounds.top)-2);
  const w = Math.min(colorCanvas.width, Math.ceil(bounds.right)+2)-x;
  const h = Math.min(colorCanvas.height, Math.ceil(bounds.bottom)+2)-y;
  if (w <= 0 || h <= 0) return;
  colorCtx.save(); colorCtx.setTransform(1,0,0,1,0,0);
  colorCtx.globalCompositeOperation = 'source-over'; colorCtx.globalAlpha = 1;
  colorCtx.beginPath(); colorCtx.rect(x,y,w,h); colorCtx.clip();
  colorCtx.clearRect(x,y,w,h); colorCtx.drawImage(stroke.base,x,y,w,h,x,y,w,h);
  // Repaint the final continuous path once, without segment-edge seams.
  paintColorBrushShape(colorCtx, stroke.op); colorCtx.restore();
}

function continueColorBrush(e) {
  const stroke = colorBrushStroke;
  if (!stroke) return;
  const p = getPos(e), sweep = stroke.op.sweep, previous = sweep[sweep.length-1];
  // Holding still or changing pressure cannot enlarge or darken the stroke.
  if (Math.hypot(p.x-previous[0], p.y-previous[1]) < .00001) return;
  const sample = [p.x, p.y, stroke.size / 2];
  sweep.push(sample); moved = true;
  points.push(p); lastRenderedPoint = {x:p.x, y:p.y}; lastPenPos = {x:p.x, y:p.y};
  paintColorBrushLive([previous, sample]);
}

function finishColorBrush(cancel=false) {
  const stroke = colorBrushStroke;
  if (!stroke) return;
  if (cancel) {
    stroke.op = {...stroke.op, sweep:[]}; activeDetailStroke = null;
  } else if (detailVectorValid && activeDetailStroke) activeDetailStroke.ops = [stroke.op];
  renderColorBrushNow(); stroke.base.width = stroke.base.height = 0;
  colorBrushStroke = null; artworkRevision++; scheduleDetailRender();
}

''' + text[last:]
    text = text.replace(
        'A tapered oval brush that follows your Pencil directly; press harder for broader color beneath your ink lines.',
        'Solid opaque color beneath your ink lines. Use the size slider to set a fixed marker width.')
    return apply_rounded_taper(text)


def apply_rounded_taper(text: str) -> str:
    """Narrow rounded endpoints; continuous filled ribbons, never tip stamps."""
    if '// gradual-rounded-marker-v7' in text:
        return text
    if '// rounded-taper-marker-v6' in text:
        return text.replace('// rounded-taper-marker-v6', '// gradual-rounded-marker-v7', 1).replace(
            'const taper = op.width * .75;', 'const taper = op.width * 3;', 1)
    helpers = r'''// gradual-rounded-marker-v7
function markerRibbonSamples(op) {
  const raw = op.sweep, result = [];
  if (!raw || !raw.length) return result;
  const full = op.width / 2, tip = op.width * .22;
  const end = raw[raw.length-1][3] || 0;
  const taper = op.width * 3;
  const smooth = x => { x=Math.max(0,Math.min(1,x)); return x*x*(3-2*x); };
  const add = (x,y,d) => {
    let radius = tip+(full-tip)*smooth(d/taper);
    if (op.finished) radius=Math.min(radius,tip+(full-tip)*smooth((end-d)/Math.min(taper,Math.max(.01,end*.5))));
    result.push([x,y,radius,d]);
  };
  add(raw[0][0],raw[0][1],raw[0][3] || 0);
  for (let i=1;i<raw.length;i++) {
    const a=raw[i-1],b=raw[i],d0=a[3] || 0,d1=b[3] || 0;
    // Interpolate geometry only in the two short taper zones. The centerline
    // always reaches the actual newest Pencil sample without a follower.
    const tapered=d0<taper || (op.finished && end-d1<taper);
    const steps=tapered ? Math.max(1,Math.ceil((d1-d0)/Math.max(1,op.width*.08))) : 1;
    for(let j=1;j<=steps;j++) {
      const t=j/steps;add(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,d0+(d1-d0)*t);
    }
  }
  return result;
}

function paintMarkerRibbon(target,op) {
  const path=markerRibbonSamples(op);
  if(!path.length) return;
  target.save();target.globalCompositeOperation='source-over';target.globalAlpha=1;
  target.fillStyle=op.color;target.shadowColor='transparent';target.shadowBlur=0;
  target.shadowOffsetX=target.shadowOffsetY=0;target.filter='none';target.beginPath();
  const sector=(p,r,from,to) => {
    if(to<from) [from,to]=[to,from];
    target.moveTo(p[0],p[1]);target.lineTo(p[0]+Math.cos(from)*r,p[1]+Math.sin(from)*r);
    target.arc(p[0],p[1],r,from,to,false);target.closePath();
  };
  if(path.length===1) {
    target.arc(path[0][0],path[0][1],path[0][2],0,Math.PI*2);
  } else {
    let previousAngle=null,firstAngle=0,lastAngle=0;
    for(let i=1;i<path.length;i++) {
      const a=path[i-1],b=path[i],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);
      if(length<.000001) continue;
      const nx=-dy/length,ny=dx/length,angle=Math.atan2(dy,dx);
      if(previousAngle===null) firstAngle=angle;
      // Filled ribbon sections share their complete edges. Positive winding
      // makes crossings add solid coverage rather than cut holes.
      target.moveTo(a[0]-nx*a[2],a[1]-ny*a[2]);
      target.lineTo(b[0]-nx*b[2],b[1]-ny*b[2]);
      target.lineTo(b[0]+nx*b[2],b[1]+ny*b[2]);
      target.lineTo(a[0]+nx*a[2],a[1]+ny*a[2]);target.closePath();
      if(previousAngle!==null) {
        const turn=Math.atan2(Math.sin(angle-previousAngle),Math.cos(angle-previousAngle));
        if(Math.abs(turn)>.000001) {
          const from=previousAngle+(turn>0 ? -Math.PI/2 : Math.PI/2);
          // Only an outer corner join, never a repeated circular brush tip.
          sector(a,a[2],from,from+turn);
        }
      }
      previousAngle=angle;lastAngle=angle;
    }
    if(path[0][3]===0) sector(path[0],path[0][2],firstAngle+Math.PI/2,firstAngle+3*Math.PI/2);
    if(op.finished) sector(path[path.length-1],path[path.length-1][2],lastAngle-Math.PI/2,lastAngle+Math.PI/2);
  }
  target.fill('nonzero');target.restore();
}

'''
    anchor='function paintColorBrushShape(target,op) {'
    if text.count(anchor)!=1:
        raise SystemExit('Rounded marker renderer anchor missing')
    text=text.replace(anchor,helpers+anchor+"\n  if(op.roundedTaper) { paintMarkerRibbon(target,op); return; }",1)
    text=text.replace("const sample = [p.x, p.y, size / 2];", "const sample = [p.x, p.y, size / 2, 0];",1)
    text=text.replace("marker:true, width:size, color:currentColor, sweep:[sample]", "marker:true, roundedTaper:true, finished:false, width:size, color:currentColor, sweep:[sample]",1)
    text=text.replace("colorBrushStroke = {base, size, color:currentColor, op, bounds:null};", "colorBrushStroke = {base, size, color:currentColor, op, bounds:null, length:0};",1)
    text=text.replace("inputModeEl.textContent = '(Solid marker — fixed width)';", "inputModeEl.textContent = '(Solid marker — narrow rounded ends)';",1)
    text=text.replace("marker:true, width:stroke.size, color:stroke.color, sweep", "marker:true, roundedTaper:true, finished:false, width:stroke.size, color:stroke.color, sweep",1)
    text=text.replace("  const sample = [p.x, p.y, stroke.size / 2];", "  stroke.length += Math.hypot(p.x-previous[0], p.y-previous[1]);\n  const sample = [p.x, p.y, stroke.size / 2, stroke.length];",1)
    text=text.replace("  paintColorBrushLive([previous, sample]);", "  paintColorBrushLive(sweep.slice(-3));",1)
    text=text.replace("  } else if (detailVectorValid && activeDetailStroke) activeDetailStroke.ops = [stroke.op];", "  } else {\n    stroke.op.finished = true;\n    if (detailVectorValid && activeDetailStroke) activeDetailStroke.ops = [stroke.op];\n  }",1)
    text=text.replace('Solid opaque color beneath your ink lines. Use the size slider to set a fixed marker width.',
                      'Solid opaque color with gently narrower, rounded starts and ends. Use the size slider for the body width.')
    return text


def apply_pressure_marker(text: str) -> str:
    """Pressure controls only moving-stroke width; endpoint limits win."""
    if '// pressure-ribbon-marker-v8' in text:
        return text

    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise SystemExit('Pressure marker anchor missing or ambiguous: ' + old[:70])
        text = text.replace(old, new, 1)

    first = text.index('function markerRibbonSamples(op) {')
    last = text.index('function paintMarkerRibbon(target,op) {', first)
    text = text[:first] + r'''// pressure-ribbon-marker-v8
function markerRibbonSamples(op) {
  const raw=op.sweep,result=[];
  if(!raw || !raw.length) return result;
  const full=op.width/2,tip=op.pressureWidth ? (op.tipRadius || op.width*.08) : op.width*.22;
  const end=raw[raw.length-1][3] || 0,taper=op.width*3;
  const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);};
  const add=(x,y,d,body) => {
    const startGain=smooth(d/taper);
    const endGain=op.finished ? smooth((end-d)/Math.min(taper,Math.max(.01,end*.5))) : 1;
    // Blend the width envelopes instead of taking a hard minimum. That avoids
    // shoulders where the pressure width meets an endpoint limit.
    let radius=op.pressureWidth
      ? tip+(Math.max(tip,Math.min(full,body))-tip)*startGain*endGain
      : tip+(full-tip)*startGain;
    if(!op.pressureWidth && op.finished) radius=Math.min(radius,tip+(full-tip)*endGain);
    result.push([x,y,radius,d]);
  };
  add(raw[0][0],raw[0][1],raw[0][3] || 0,raw[0][2]);
  for(let i=1;i<raw.length;i++) {
    const a=raw[i-1],b=raw[i],d0=a[3] || 0,d1=b[3] || 0;
    const tapered=d0<taper || (op.finished && end-d1<taper);
    const steps=tapered || op.pressureWidth ? Math.max(1,Math.ceil((d1-d0)/Math.max(1,op.width*.08))) : 1;
    for(let j=1;j<=steps;j++) {
      const t=j/steps;
      // Smooth width interpolation, independent of position: the centerline
      // still reaches the newest Pencil coordinates synchronously.
      const blend=smooth(t);
      add(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,d0+(d1-d0)*t,a[2]+(b[2]-a[2])*blend);
    }
  }
  return result;
}

''' + text[last:]
    change('  const sample = [p.x, p.y, size / 2, 0];', '''  const pen = e.pointerType === 'pen';
  const pressure = pen ? Math.max(0,Math.min(1,Number(e.pressure) || 0)) : .65;
  const tipRadius = Math.min(size*.08,1.5*getDisplayDpr());
  const bodyRadius = tipRadius + (size/2-tipRadius)*Math.pow(pressure,.85);
  const sample = [p.x, p.y, bodyRadius, 0];''')
    change("marker:true, roundedTaper:true, finished:false, width:size", "marker:true, roundedTaper:true, pressureWidth:true, tipRadius, finished:false, width:size")
    change("colorBrushStroke = {base, size, color:currentColor, op, bounds:null, length:0};", "colorBrushStroke = {base, size, color:currentColor, op, bounds:null, length:0, pen};")
    change("inputModeEl.textContent = '(Solid marker — narrow rounded ends)';", "inputModeEl.textContent = pen ? '(Pressure width — protected thin ends)' : '(Color marker — thin rounded ends)';")
    change("marker:true, roundedTaper:true, finished:false, width:stroke.size", "marker:true, roundedTaper:true, pressureWidth:true, tipRadius:stroke.op.tipRadius, finished:false, width:stroke.size")
    change('  const stroke = colorBrushStroke, [x,y,r] = sample;', '  const stroke = colorBrushStroke, [x,y] = sample, r = stroke.size / 2;')
    change('''  stroke.length += Math.hypot(p.x-previous[0], p.y-previous[1]);
  const sample = [p.x, p.y, stroke.size / 2, stroke.length];''', '''  const distance = Math.hypot(p.x-previous[0], p.y-previous[1]);
  stroke.length += distance;
  // Pressure changes at a stationary tip never paint. Ease width as distance
  // is travelled, and limit the slope so hard presses cannot form a step.
  const pressure = stroke.pen ? Math.max(0,Math.min(1,Number(e.pressure) || 0)) : .65;
  const tip = stroke.op.tipRadius;
  const desired = e.type === 'pointerup' ? previous[2]
    : tip + (stroke.size/2-tip)*Math.pow(pressure,.85);
  const eased = previous[2] + (desired-previous[2])*(1-Math.exp(-distance/Math.max(1,stroke.size*.65)));
  const limit = distance*.18;
  const radius = Math.max(tip, Math.min(stroke.size/2,
    previous[2]+Math.max(-limit,Math.min(limit,eased-previous[2]))));
  const sample = [p.x, p.y, radius, stroke.length];''')
    text=text.replace('Solid opaque color with gently narrower, rounded starts and ends. Use the size slider for the body width.',
                      'Pencil pressure changes width while moving; starts and ends stay thin and rounded. Color stays fully opaque.')
    return text


def apply_solid_marker(text: str) -> str:
    return preserve_marker_on_lift(apply_pressure_marker(_apply_solid_marker_base(text)))


def preserve_marker_on_lift(text: str) -> str:
    """Commit the live stroke without narrowing or repainting it on lift."""
    if '// preserve-marker-on-lift-v9' in text:
        return text
    old = '    stroke.op.finished = true;'
    if text.count(old) != 1:
        raise SystemExit('Marker release geometry anchor missing')
    text = text.replace(old, '    // preserve-marker-on-lift-v9: keep the live geometry on release.', 1)
    old = '  renderColorBrushNow(); stroke.base.width = stroke.base.height = 0;'
    if text.count(old) != 1:
        raise SystemExit('Marker release repaint anchor missing')
    text = text.replace(old, '  if (cancel) renderColorBrushNow();\n  stroke.base.width = stroke.base.height = 0;', 1)
    text = text.replace('Pencil pressure changes width while moving; starts and ends stay thin and rounded. Color stays fully opaque.',
                        'Pencil pressure changes width while moving. Starts stay thin; ease pressure for a thinner ending. Lifting preserves your stroke.')
    return text
