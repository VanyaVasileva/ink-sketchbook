from pathlib import Path

PATH = Path('hand-selector-standalone-test.html')
MARKER = 'retina-detail-display-v2-standalone'


def replace_one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


s = PATH.read_text()
if MARKER in s:
    print('Standalone retina layer already present; no patch needed.')
    raise SystemExit(0)

s = replace_one(
    s,
    "const wrap = document.querySelector('.canvas-wrap');\n",
    """const wrap = document.querySelector('.canvas-wrap');

// retina-detail-display-v2-standalone: screen-resolution ink replay used only
// while zoomed. drawCanvas remains authoritative for editing/save/export/
// recording; this transparent layer only improves what the artist sees.
const detailCanvas = document.createElement('canvas');
detailCanvas.id = 'detailCanvas';
detailCanvas.setAttribute('aria-hidden', 'true');
detailCanvas.style.cssText = 'position:absolute;left:0;top:0;z-index:4;pointer-events:none;display:none;box-shadow:none;';
wrap.appendChild(detailCanvas);
const detailCtx = detailCanvas.getContext('2d');
""",
    'canvas binding',
)

s = replace_one(
    s,
    "let view = { scale: 1, x: 0, y: 0, rotation: 0 }; // rotation in degrees\n",
    """let view = { scale: 1, x: 0, y: 0, rotation: 0 }; // rotation in degrees

// Lightweight stroke geometry for a retina-sharp DISPLAY replay. This is not
// a second artwork file and does not change export resolution or recording.
let detailStrokes = [];
let detailVisibleCount = 0;
let activeDetailStroke = null;
let detailHistory = [];
let detailRedoCounts = [];
let detailVectorValid = true;
let detailRenderRAF = null;
let detailPixelRatio = 1;
const DETAIL_ZOOM_THRESHOLD = 1.12;
""",
    'view state',
)

helpers = r'''function detailZoomIsActive() {
  return detailVectorValid && view.scale >= DETAIL_ZOOM_THRESHOLD;
}

function ensureDetailCanvasSize() {
  const rect = wrap.getBoundingClientRect();
  // Match real display density. Above the screen DPR there is no visible gain,
  // only extra iPad memory use, so cap at 3x.
  detailPixelRatio = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
  const w = Math.max(2, Math.round(rect.width * detailPixelRatio));
  const h = Math.max(2, Math.round(rect.height * detailPixelRatio));
  if (detailCanvas.width !== w || detailCanvas.height !== h) {
    detailCanvas.width = w;
    detailCanvas.height = h;
  }
  detailCanvas.style.width = rect.width + 'px';
  detailCanvas.style.height = rect.height + 'px';
}

function setDetailTransform() {
  // The normal canvas is CSS-transformed for zoom. The detail layer itself is
  // not scaled as a bitmap; instead we replay the same stroke coordinates
  // through an equivalent transform directly into screen-resolution pixels.
  const baseW = parseFloat(drawCanvas.style.width) || canvasBaseCssW || 1;
  const baseH = parseFloat(drawCanvas.style.height) || canvasBaseCssH || 1;
  const left = parseFloat(drawCanvas.style.left) || EDGE_MARGIN;
  const top = parseFloat(drawCanvas.style.top) || EDGE_MARGIN;
  const sx = (baseW * view.scale) / Math.max(1, drawCanvas.width);
  const sy = (baseH * view.scale) / Math.max(1, drawCanvas.height);
  const rad = view.rotation * Math.PI / 180;
  detailCtx.setTransform(detailPixelRatio, 0, 0, detailPixelRatio, 0, 0);
  detailCtx.translate(left + view.x, top + view.y);
  detailCtx.rotate(rad);
  detailCtx.scale(sx, sy);
}

function paintDetailOp(op) {
  if (!op) return;
  detailCtx.save();
  detailCtx.globalCompositeOperation = op.mode === 'erase' ? 'destination-out' : 'source-over';
  detailCtx.lineJoin = 'round';
  detailCtx.lineCap = 'round';
  detailCtx.lineWidth = op.width;
  if (op.kind === 'dot') {
    detailCtx.fillStyle = op.mode === 'erase' ? 'rgba(0,0,0,1)' : op.color;
    detailCtx.beginPath();
    detailCtx.arc(op.x, op.y, op.width / 2, 0, Math.PI * 2);
    detailCtx.fill();
  } else {
    detailCtx.strokeStyle = op.mode === 'erase' ? 'rgba(0,0,0,1)' : op.color;
    detailCtx.beginPath();
    detailCtx.moveTo(op.x1, op.y1);
    detailCtx.lineTo(op.x2, op.y2);
    detailCtx.stroke();
  }
  detailCtx.restore();
}

function renderDetailView() {
  detailRenderRAF = null;
  if (!detailZoomIsActive()) {
    detailCanvas.style.display = 'none';
    drawCanvas.style.opacity = '';
    return;
  }

  ensureDetailCanvasSize();
  detailCtx.setTransform(1, 0, 0, 1, 0, 0);
  detailCtx.globalCompositeOperation = 'source-over';
  detailCtx.clearRect(0, 0, detailCanvas.width, detailCanvas.height);
  detailCanvas.style.display = 'block';
  drawCanvas.style.opacity = '0';

  setDetailTransform();
  for (let i = 0; i < detailVisibleCount; i++) {
    const stroke = detailStrokes[i];
    if (!stroke) continue;
    for (const op of stroke.ops) paintDetailOp(op);
  }
  if (activeDetailStroke) {
    for (const op of activeDetailStroke.ops) paintDetailOp(op);
  }

  detailCtx.setTransform(1, 0, 0, 1, 0, 0);
  detailCtx.globalCompositeOperation = 'source-over';
}

function scheduleDetailRender() {
  if (detailRenderRAF !== null) return;
  detailRenderRAF = requestAnimationFrame(renderDetailView);
}

function beginDetailStroke() {
  if (detailVectorValid) activeDetailStroke = { ops: [] };
}

function drawDetailOpLive(op) {
  if (!detailZoomIsActive()) return;
  if (detailCanvas.style.display === 'none') {
    scheduleDetailRender();
    return;
  }
  setDetailTransform();
  paintDetailOp(op);
  detailCtx.setTransform(1, 0, 0, 1, 0, 0);
  detailCtx.globalCompositeOperation = 'source-over';
}

function recordDetailSegment(x1, y1, x2, y2, width, strokeMode, color) {
  if (!detailVectorValid || !activeDetailStroke) return;
  const op = { kind: 'segment', x1, y1, x2, y2, width, mode: strokeMode, color };
  activeDetailStroke.ops.push(op);
  drawDetailOpLive(op);
}

function recordDetailDot(x, y, width, strokeMode, color) {
  if (!detailVectorValid || !activeDetailStroke) return;
  const op = { kind: 'dot', x, y, width, mode: strokeMode, color };
  activeDetailStroke.ops.push(op);
  drawDetailOpLive(op);
}

function commitDetailStroke() {
  if (!detailVectorValid) {
    activeDetailStroke = null;
    return;
  }
  if (!activeDetailStroke || activeDetailStroke.ops.length === 0) {
    activeDetailStroke = null;
    return;
  }
  if (detailVisibleCount < detailStrokes.length) detailStrokes.splice(detailVisibleCount);
  detailStrokes.push(activeDetailStroke);
  detailVisibleCount = detailStrokes.length;
  activeDetailStroke = null;
  scheduleDetailRender();
}

function resetDetailVectors(valid = true) {
  detailStrokes = [];
  detailVisibleCount = 0;
  activeDetailStroke = null;
  detailHistory = [];
  detailRedoCounts = [];
  detailVectorValid = valid;
  scheduleDetailRender();
}

'''
s = replace_one(s, 'function resize() {\n', helpers + 'function resize() {\n', 'resize')

s = replace_one(
    s,
    """function saveHistory() {
  history.push(ctx.getImageData(0,0,drawCanvas.width,drawCanvas.height));
  if (history.length > 30) history.shift();
  redoStack = []; // a new stroke invalidates whatever redo could have restored
}
""",
    """function saveHistory() {
  history.push(ctx.getImageData(0,0,drawCanvas.width,drawCanvas.height));
  detailHistory.push(detailVisibleCount);
  if (history.length > 30) {
    history.shift();
    detailHistory.shift();
  }
  redoStack = []; // a new stroke invalidates whatever redo could have restored
  detailRedoCounts = [];
  scheduleDetailRender();
}
""",
    'save history',
)

s = replace_one(
    s,
    """function startStroke(e) {
  drawing = true;
  points = [getPos(e)];
""",
    """function startStroke(e) {
  drawing = true;
  beginDetailStroke();
  points = [getPos(e)];
""",
    'stroke start',
)

s = replace_one(
    s,
    """  ctx.moveTo(renderPrev.x, renderPrev.y);
  ctx.lineTo(x, y);
  ctx.stroke();
  ctx.globalCompositeOperation = 'source-over'; // always reset immediately after
""",
    """  ctx.moveTo(renderPrev.x, renderPrev.y);
  ctx.lineTo(x, y);
  ctx.stroke();
  recordDetailSegment(renderPrev.x, renderPrev.y, x, y, smoothedWidth, mode, currentColor);
  ctx.globalCompositeOperation = 'source-over'; // always reset immediately after
""",
    'stroke segment',
)

s = replace_one(
    s,
    """    ctx.beginPath();
    ctx.arc(p.x, p.y, width / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
  }
  saveHistory();
}
""",
    """    ctx.beginPath();
    ctx.arc(p.x, p.y, width / 2, 0, Math.PI * 2);
    ctx.fill();
    recordDetailDot(p.x, p.y, width, mode, currentColor);
    ctx.globalCompositeOperation = 'source-over';
  }
  commitDetailStroke();
  saveHistory();
}
""",
    'stroke end',
)

s = replace_one(
    s,
    """function applyView() {
  const t = `translate(${view.x}px, ${view.y}px) rotate(${view.rotation}deg) scale(${view.scale})`;
  refCanvas.style.transform = t;
  refDomLayer.style.transform = t;
  guideCanvas.style.transform = t;
  drawCanvas.style.transform = t;
}
""",
    """function applyView() {
  const t = `translate(${view.x}px, ${view.y}px) rotate(${view.rotation}deg) scale(${view.scale})`;
  refCanvas.style.transform = t;
  refDomLayer.style.transform = t;
  guideCanvas.style.transform = t;
  drawCanvas.style.transform = t;
  scheduleDetailRender();
}
""",
    'apply view',
)

s = replace_one(
    s,
    """  } else if (activePointers.size === 2) {
    drawing = false;
    const pts = [...activePointers.values()];
""",
    """  } else if (activePointers.size === 2) {
    // If a second finger starts a pinch mid-stroke, preserve the part already
    // drawn in both the real canvas and the sharp replay history.
    if (drawing && activeDetailStroke && activeDetailStroke.ops.length) {
      commitDetailStroke();
      saveHistory();
    } else {
      activeDetailStroke = null;
    }
    drawing = false;
    const pts = [...activePointers.values()];
""",
    'two-finger gesture',
)

s = replace_one(
    s,
    """undoBtn.onclick = () => {
  if (history.length > 1) {
    redoStack.push(history.pop());
    ctx.putImageData(history[history.length - 1], 0, 0);
  }
};
redoBtn.onclick = () => {
  if (redoStack.length > 0) {
    const state = redoStack.pop();
    history.push(state);
    ctx.putImageData(state, 0, 0);
  }
};
clearBtn.onclick = () => {
  ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  history = [];
  saveHistory();
};
""",
    """undoBtn.onclick = () => {
  if (history.length > 1) {
    redoStack.push(history.pop());
    if (detailHistory.length > 1) detailRedoCounts.push(detailHistory.pop());
    detailVisibleCount = detailHistory.length ? detailHistory[detailHistory.length - 1] : 0;
    activeDetailStroke = null;
    ctx.putImageData(history[history.length - 1], 0, 0);
    scheduleDetailRender();
  }
};
redoBtn.onclick = () => {
  if (redoStack.length > 0) {
    const state = redoStack.pop();
    history.push(state);
    if (detailRedoCounts.length > 0) {
      const detailCount = detailRedoCounts.pop();
      detailHistory.push(detailCount);
      detailVisibleCount = detailCount;
    }
    ctx.putImageData(state, 0, 0);
    scheduleDetailRender();
  }
};
clearBtn.onclick = () => {
  ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  history = [];
  resetDetailVectors(true);
  saveHistory();
};
""",
    'undo/redo/clear',
)

s = replace_one(
    s,
    """        ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
        ctx.drawImage(loadImg, 0, 0, drawCanvas.width, drawCanvas.height);
        saveHistory();
""",
    """        ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
        ctx.drawImage(loadImg, 0, 0, drawCanvas.width, drawCanvas.height);
        // Older saved PNGs have no stroke geometry to replay, so keep their
        // normal raster display rather than inventing detail that is not there.
        resetDetailVectors(false);
        history = [];
        saveHistory();
""",
    'saved drawing load',
)

required = [
    MARKER,
    "detailCanvas.id = 'detailCanvas'",
    'const DETAIL_ZOOM_THRESHOLD = 1.12;',
    'recordDetailSegment(renderPrev.x, renderPrev.y, x, y, smoothedWidth, mode, currentColor);',
    "drawCanvas.style.opacity = '0';",
]
for item in required:
    if item not in s:
        raise SystemExit('Missing final retina hook: ' + item)

PATH.write_text(s)
print('Patched exact standalone hand-selector page with retina-sharp zoom display.')
