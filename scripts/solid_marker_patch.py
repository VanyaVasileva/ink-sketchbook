"""Replace the color brush's new strokes with a plain opaque canvas marker."""


def apply_solid_marker(text: str) -> str:
    if '// simple-solid-marker-v5' in text:
        return text
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
  const size = Math.max(2, Number(colorBrushSize.value) || 80) * getDisplayDpr();
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
    return text
