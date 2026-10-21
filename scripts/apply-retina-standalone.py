from pathlib import Path
import base64
import re

PATH = Path('hand-selector-standalone-test.html')
MARKER = 'retina-detail-display-v2-standalone'


def replace_one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


s = PATH.read_text()

# Use the high-resolution pencil sprite without changing its calibrated pose.
# Fresh standalone builds contain the base hand maps but not the wooden-pencil
# assignment yet, while already-patched pages contain explicit assignments.
hd_pencil = Path('assets/hand-wooden-pencil-hd.webp')
if hd_pencil.exists():
    sprite_url = 'data:image/webp;base64,' + base64.b64encode(hd_pencil.read_bytes()).decode('ascii')
    source_line = "recordingHandSources.woodenPencil = '" + sprite_url + "';"
    meta_line = 'recordingHandMeta.woodenPencil = {srcW:3072,srcH:2808,tipX:292.683,tipY:1569.041,scale:1.1};'
    source_pattern = r"recordingHandSources\.woodenPencil = '[^']*';"
    meta_pattern = r'recordingHandMeta\.woodenPencil = \{[^}]*\};'

    has_source = re.search(source_pattern, s) is not None
    has_meta = re.search(meta_pattern, s) is not None
    if has_source:
        s = re.sub(source_pattern, lambda _: source_line, s, count=1)
    if has_meta:
        s = re.sub(meta_pattern, meta_line, s, count=1)

    if not has_source or not has_meta:
        fresh_anchor = 'const recordingHands = {};'
        if fresh_anchor not in s:
            raise SystemExit('Fresh recording-hand insertion anchor missing')
        missing = []
        if not has_source:
            missing.append(source_line)
        if not has_meta:
            missing.append(meta_line)
        s = s.replace(fresh_anchor, '\n'.join(missing) + '\n' + fresh_anchor, 1)
    PATH.write_text(s)

# Add the two approved pen hands as separate recording-hand choices.
extra_hands = (
    ('modernFineLiner', Path('assets/hand-modern-fineliner.webp'),
     '{srcW:1312,srcH:1199,tipX:127,tipY:663,scale:1.1}'),
    ('classicInkPen', Path('assets/hand-classic-ink-pen.webp'),
     '{srcW:1312,srcH:1199,tipX:126,tipY:667,scale:1.1}'),
)
previous_key = 'woodenPencil'
for key, asset_path, meta in extra_hands:
    if not asset_path.exists():
        raise SystemExit(f'Missing recording-hand asset: {asset_path}')
    asset_url = 'data:image/webp;base64,' + base64.b64encode(asset_path.read_bytes()).decode('ascii')
    source_line = f"recordingHandSources.{key} = '{asset_url}';"
    source_pattern = rf"recordingHandSources\.{key} = '[^']*';"
    if re.search(source_pattern, s):
        s = re.sub(source_pattern, lambda _: source_line, s, count=1)
    else:
        anchor_pattern = rf"(recordingHandSources\.{previous_key} = '[^']*';)"
        s, count = re.subn(anchor_pattern, lambda m: m.group(1) + '\n' + source_line, s, count=1)
        if count != 1:
            raise SystemExit(f'Recording-hand source anchor missing for {key}')

    meta_line = f'recordingHandMeta.{key} = {meta};'
    meta_pattern = rf'recordingHandMeta\.{key} = \{{[^}}]*\}};'
    if re.search(meta_pattern, s):
        s = re.sub(meta_pattern, meta_line, s, count=1)
    else:
        meta_anchor = rf'(recordingHandMeta\.{previous_key} = \{{[^}}]*\}};)'
        s, count = re.subn(meta_anchor, lambda m: m.group(1) + '\n' + meta_line, s, count=1)
        if count != 1:
            raise SystemExit(f'Recording-hand metadata anchor missing for {key}')
    previous_key = key
PATH.write_text(s)

# Keep Vanya's preferred wooden-pencil recording setup as the page defaults.
# This patch is idempotent and is re-applied whenever the standalone page is rebuilt.
wooden_option = '<option value="woodenPencil">Wooden pencil</option>'
wooden_selected_option = '<option value="woodenPencil" selected>Wooden pencil</option>'
if wooden_option not in s and wooden_selected_option not in s:
    option_seed = '<option value="brownOatmeal">Brown + oatmeal</option>'
    if option_seed not in s:
        raise SystemExit('Fresh recording-hand selector anchor missing')
    s = s.replace(option_seed, option_seed + wooden_option, 1)

default_settings = (
    ('<option value="woodenPencil">Wooden pencil</option>',
     '<option value="woodenPencil" selected>Wooden pencil</option>'),
    ('<span>Hand size <b id="recordingHandSizeValue" style="font-weight:600;">100%</b></span> <input type="range" id="recordingHandSize" min="60" max="140" value="100" step="5">',
     '<span>Hand size <b id="recordingHandSizeValue" style="font-weight:600;">115%</b></span> <input type="range" id="recordingHandSize" min="60" max="140" value="115" step="5">'),
    ('id="thicknessSlider" min="0.5" max="3" value="1" step="0.25"',
     'id="thicknessSlider" min="0.5" max="3" value="1.25" step="0.25"'),
    ('id="minSlider" min="0.5" max="6" value="1" step="0.5"',
     'id="minSlider" min="0.5" max="6" value="0.5" step="0.5"'),
    ('id="maxSlider" min="2" max="16" value="8" step="0.5"',
     'id="maxSlider" min="2" max="16" value="6" step="0.5"'),
    ("let selectedRecordingHand = 'human';", "let selectedRecordingHand = 'woodenPencil';"),
    ('let recordingHandUserScale = 1;', 'let recordingHandUserScale = 1.15;'),
)
settings_changed = False
for old, new in default_settings:
    if new in s:
        continue
    if old not in s:
        raise SystemExit('Wooden-pencil default anchor not found: ' + old[:80])
    s = s.replace(old, new, 1)
    settings_changed = True
if settings_changed:
    PATH.write_text(s)

# Safari can restore an older form selection after a reload, even when the
# HTML default and JavaScript default have changed. Explicitly sync the visible
# selector so existing iPad tabs show the wooden pencil after this update.
hand_select_sync = "if (recordingHandSelect) recordingHandSelect.value = selectedRecordingHand;"
if hand_select_sync not in s:
    hand_select_anchor = "let selectedRecordingHand = 'woodenPencil';\n"
    if hand_select_anchor not in s:
        raise SystemExit('Wooden-pencil selector sync anchor not found')
    s = s.replace(hand_select_anchor, hand_select_anchor + hand_select_sync + "\n", 1)
    PATH.write_text(s)

extra_options = (
    '<option value="modernFineLiner">Modern fine liner</option>'
    '<option value="classicInkPen">Classic ink pen</option>'
)
if '<option value="modernFineLiner">' not in s:
    option_anchor = '<option value="woodenPencil" selected>Wooden pencil</option>'
    if option_anchor not in s:
        raise SystemExit('Wooden-pencil selector option anchor not found')
    s = s.replace(option_anchor, option_anchor + extra_options, 1)

natural_hand_test = "['woodenPencil', 'modernFineLiner', 'classicInkPen'].includes(name)"
if natural_hand_test not in s:
    old_test = "name === 'woodenPencil'"
    if old_test in s:
        s = s.replace(old_test, natural_hand_test, 1)
    else:
        simple_onload = "  entry.img.onload = () => { entry.ready = true; };"
        natural_onload = """  entry.img.onload = () => {
    if (['woodenPencil', 'modernFineLiner', 'classicInkPen'].includes(name)) {
      const sprite = document.createElement('canvas');
      sprite.width = meta.srcW; sprite.height = meta.srcH;
      const spriteCtx = sprite.getContext('2d');
      spriteCtx.drawImage(entry.img, 0, 0);
      const pixels = spriteCtx.getImageData(0, 0, sprite.width, sprite.height);
      for (let i = 3; i < pixels.data.length; i += 4) {
        const alpha = pixels.data[i];
        pixels.data[i] = alpha < 128 ? 0 : alpha < 240 ? Math.round((alpha - 128) * 255 / 112) : 255;
      }
      spriteCtx.putImageData(pixels, 0, 0);
      entry.img = sprite;
    }
    entry.ready = true;
  };"""
        if simple_onload not in s:
            raise SystemExit('Natural-hand alpha cleanup anchor not found')
        s = s.replace(simple_onload, natural_onload, 1)

recording_shadow_test = (
    "selectedRecordingHand === 'woodenPencil' || "
    "selectedRecordingHand === 'modernFineLiner' || "
    "selectedRecordingHand === 'classicInkPen'"
)
if recording_shadow_test not in s:
    old_shadow_test = "selectedRecordingHand === 'woodenPencil'"
    if old_shadow_test in s:
        s = s.replace(old_shadow_test, recording_shadow_test, 1)
    else:
        shadow_anchor = """      recordCtx.globalAlpha = 1;
      recordCtx.drawImage(selected.img, drawX, drawY, selected.srcW * scale, selected.srcH * scale);"""
        shadow_block = """      recordCtx.globalAlpha = 1;
      if (selectedRecordingHand === 'woodenPencil' || selectedRecordingHand === 'modernFineLiner' || selectedRecordingHand === 'classicInkPen') {
        recordCtx.shadowColor = 'rgba(40, 28, 18, 0.16)';
        recordCtx.shadowBlur = Math.max(1, displayW * 0.005);
        recordCtx.shadowOffsetX = displayW * 0.0015;
        recordCtx.shadowOffsetY = displayW * 0.003;
      }
      recordCtx.drawImage(selected.img, drawX, drawY, selected.srcW * scale, selected.srcH * scale);"""
        if shadow_anchor not in s:
            raise SystemExit('Natural-hand recording shadow anchor not found')
        s = s.replace(shadow_anchor, shadow_block, 1)
PATH.write_text(s)

# Give the classic nib and fingers a closer, directional cast shadow. Keep
# the existing lighter shadow for the wooden pencil and fine liner.
old_classic_shadow = """        recordCtx.shadowColor = 'rgba(40, 28, 18, 0.16)';
        recordCtx.shadowBlur = Math.max(1, displayW * 0.005);
        recordCtx.shadowOffsetX = displayW * 0.0015;
        recordCtx.shadowOffsetY = displayW * 0.003;"""
new_classic_shadow = """        const classicPen = selectedRecordingHand === 'classicInkPen';
        recordCtx.shadowColor = classicPen ? 'rgba(30, 25, 22, 0.28)' : 'rgba(40, 28, 18, 0.16)';
        recordCtx.shadowBlur = Math.max(1, displayW * (classicPen ? 0.009 : 0.005));
        recordCtx.shadowOffsetX = displayW * (classicPen ? 0.005 : 0.0015);
        recordCtx.shadowOffsetY = displayW * (classicPen ? 0.008 : 0.003);"""
if old_classic_shadow in s:
    s = s.replace(old_classic_shadow, new_classic_shadow, 1)
    PATH.write_text(s)

# Keep a constant recording-hand scale for both pens, matching the wooden pencil.
# Earlier builds constrained pen sprites to the frame and made them grow and shrink
# as the tip moved. Remove that position-dependent fit on every fresh build.
fit_pattern = re.compile(
    r"      const penBounds = selectedRecordingHand === 'modernFineLiner'\n"
    r".*?      const drawX = recordPenX - selected.tipX \* scale;",
    re.DOTALL,
)
s, fit_count = fit_pattern.subn(
    '      const scale = displayW / selected.srcW;\n'
    '      const drawX = recordPenX - selected.tipX * scale;',
    s,
    count=1,
)
if fit_count:
    PATH.write_text(s)

native_retina_hooks = [
    "detailCanvas.id = 'detailCanvas'",
    'const DETAIL_ZOOM_THRESHOLD = 1.12;',
    'recordDetailSegment(',
    "drawCanvas.style.opacity = '0';",
]
if MARKER in s:
    print('Standalone defaults checked; retina layer already present.')
    raise SystemExit(0)
if all(item in s for item in native_retina_hooks):
    anchor = "detailCanvas.id = 'detailCanvas';"
    s = s.replace(anchor, "// " + MARKER + "\n" + anchor, 1)
    PATH.write_text(s)
    print('Standalone already has native retina detail rendering; added compatibility marker.')
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
    'recordDetailSegment(',
    "drawCanvas.style.opacity = '0';",
]
for item in required:
    if item not in s:
        raise SystemExit('Missing final retina hook: ' + item)

PATH.write_text(s)
print('Patched exact standalone hand-selector page with retina-sharp zoom display.')
