from pathlib import Path
import base64
import re
from paper_multiply_patch import apply_paper_multiply

PATH = Path('hand-selector-standalone-test.html')
MARKER = 'retina-detail-display-v2-standalone'


def replace_one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


s = PATH.read_text()

# Opening defaults and the inline colour picker; preserve all drawing code.
s = s.replace('id="wobbleSlider" min="0" max="3" value="1"', 'id="wobbleSlider" min="0" max="3" value="0.5"')
s = s.replace("let currentColor = '#2a2620';", "let currentColor = '#000000';")
s = s.replace("ink:'#2a2620'", "ink:'#000000'")
s = s.replace("const colors = ['#2a2620',", "const colors = ['#000000',")
s = s.replace('id="colorPicker" value="#2a2620"', 'id="colorPicker" value="#000000"')
if 'scripts/sketchbook-color-picker.js' not in s:
    s = s.replace('</head>', '<script defer src="scripts/sketchbook-color-picker.js?v=1"></script>\n</head>')
PATH.write_text(s)


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

# Keep the video frame fixed while following the current canvas zoom and pan.
# Apply this before the retina early returns so both existing pages and fresh
# builds receive the same recording behavior.
recording_view_helpers = """let recordViewport = null;

function getLiveRecordingSourceRect() {
  if (!recordViewport) {
    return recordSourceRect || { x: 0, y: 0, width: drawCanvas.width, height: drawCanvas.height };
  }
  const canvasRect = drawCanvas.getBoundingClientRect();
  const wrapRect = wrap.getBoundingClientRect();
  const sx = drawCanvas.width / Math.max(1, canvasRect.width);
  const sy = drawCanvas.height / Math.max(1, canvasRect.height);
  // Do not intersect with the canvas again: that would stretch the remaining
  // artwork when panning past an edge. Areas outside the page stay paper-colored.
  return {
    x: (wrapRect.left + recordViewport.x - canvasRect.left) * sx,
    y: (wrapRect.top + recordViewport.y - canvasRect.top) * sy,
    width: recordViewport.width * sx,
    height: recordViewport.height * sy
  };
}
"""
recording_view_patches = (
    ('let recordSourceRect = null;\n',
     'let recordSourceRect = null;\n' + recording_view_helpers),
    ("  const visibleHeight = Math.max(1, visibleBottom - visibleTop);\n  recordSourceRect = {",
     """  const visibleHeight = Math.max(1, visibleBottom - visibleTop);
  recordViewport = {
    x: visibleLeft - wrapRectForRecording.left,
    y: visibleTop - wrapRectForRecording.top,
    width: visibleWidth,
    height: visibleHeight
  };
  recordSourceRect = {"""),
    ('  const source = recordSourceRect || { x: 0, y: 0, width: drawCanvas.width, height: drawCanvas.height };',
     '  const source = getLiveRecordingSourceRect();'),
    ('      const displayW = baseDisplayW * selected.scale * recordingHandUserScale;',
     """      const cameraScale = recordSourceRect ? recordSourceRect.width / source.width : 1;
      const displayW = baseDisplayW * selected.scale * recordingHandUserScale * cameraScale;"""),
    ('    ink.setTransform(sx, 0, 0, sy, -source.x * sx, -source.y * sy);',
     """    ink.save();
    ink.setTransform(sx, 0, 0, sy, -source.x * sx, -source.y * sy);
    ink.beginPath();
    ink.rect(0, 0, drawCanvas.width, drawCanvas.height);
    ink.clip();"""),
    ("    ink.setTransform(1, 0, 0, 1, 0, 0);\n    ink.globalCompositeOperation = 'source-over';",
     "    ink.restore();\n    ink.setTransform(1, 0, 0, 1, 0, 0);\n    ink.globalCompositeOperation = 'source-over';"),
    ('      recordCtx.setTransform(mapX, 0, 0, mapY, -cropX * mapX, -cropY * mapY);',
     """      recordCtx.setTransform(mapX, 0, 0, mapY, -cropX * mapX, -cropY * mapY);
      recordCtx.beginPath();
      recordCtx.rect(0, 0, cw, ch);
      recordCtx.clip();"""),
    ('The sketch overlay always stays private and is never recorded.</div>',
     'The sketch overlay always stays private and is never recorded. Zoom and pan are included in recordings.</div>'),
    ('recordingHintMsg: "Recording — only your paper and ink lines are captured, your reference stays private."',
     'recordingHintMsg: "Recording — zoom and pan are captured. The sketch overlay stays private."'),
)
for old, new in recording_view_patches:
    if '// artwork-color-layer-v1' in s and old.startswith('    ink.setTransform('):
        # The two-layer recorder applies the equivalent clip to each target.
        continue
    if new in s:
        continue
    s = replace_one(s, old, new, 'Live recording view')
PATH.write_text(s)

# Use bounded H.264 output on Apple devices, and verify the encoded result.
# Keep the 1s timeslice: WebKit's MP4 muxer can lose frames without it.
playback_marker = '// recording-playback-v2'
if playback_marker not in s:
    mime_start = s.index('function pickRecordingMimeType() {')
    mime_end = s.index('\nconst recordingSupport =', mime_start)
    s = s[:mime_start] + r'''// recording-playback-v2
function recordingMimeTypes(withAudio = false) {
  return [
    withAudio ? 'video/mp4;codecs=avc1,mp4a.40.2' : 'video/mp4;codecs=avc1',
    'video/mp4',
    withAudio ? 'video/webm;codecs=vp8,opus' : 'video/webm;codecs=vp8',
    'video/webm'
  ].filter(type => !MediaRecorder.isTypeSupported || MediaRecorder.isTypeSupported(type));
}

function pickRecordingMimeType() {
  return window.MediaRecorder ? (recordingMimeTypes()[0] || null) : null;
}

function usesAppleRecordingEncoder() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) ||
    (/Safari/.test(navigator.userAgent) && !/Chrome|Chromium|Android/.test(navigator.userAgent));
}

function recordingOutputSize(source) {
  const longSide = Math.max(source.width, source.height);
  const shortSide = Math.min(source.width, source.height);
  const apple = usesAppleRecordingEncoder();
  const phone = /iPhone|iPod/.test(navigator.userAgent) || Math.min(screen.width, screen.height) < 600;
  // Stay inside a 1920x1080 pixel budget on Safari, including desktop-mode iPads.
  // Replay ink geometry at this resolution instead of enlarging a bitmap.
  const scale = apple
    ? Math.min(1920 / Math.max(1, longSide), 1080 / Math.max(1, shortSide))
    : Math.max((phone ? 1920 : 3200) / Math.max(1, longSide), 1080 / Math.max(1, shortSide));
  const even = value => Math.max(2, Math.floor(value / 2) * 2);
  return { width: even(source.width * scale), height: even(source.height * scale) };
}

function createRecordingEncoder(stream) {
  let lastError;
  for (const mimeType of recordingMimeTypes(stream.getAudioTracks().length > 0)) {
    try {
      return new MediaRecorder(stream, {
        mimeType,
        videoBitsPerSecond: usesAppleRecordingEncoder() ? 10000000 : 30000000,
        audioBitsPerSecond: 256000
      });
    } catch (error) { lastError = error; }
  }
  throw lastError || new Error('No video encoder is available.');
}
''' + s[mime_end:]

    state_anchor = 'let recordRAF = null;'
    s = replace_one(s, state_anchor, state_anchor + '''
let recordVideoTrack = null;
let recordingStream = null;
let recordingBusy = false;
let recordingError = null;

function releaseRecordingCapture() {
  cancelAnimationFrame(recordRAF);
  recordRAF = null;
  if (recordingStream) recordingStream.getTracks().forEach(track => track.stop());
  recordingStream = null;
  recordVideoTrack = null;
  if (recordingMicrophoneStream) recordingMicrophoneStream.getTracks().forEach(track => track.stop());
  recordingMicrophoneStream = null;
  recordingAudioGain = null;
  if (recordingAudioContext) recordingAudioContext.close().catch(() => {});
  recordingAudioContext = null;
  if (recordCanvas && recordCanvas.parentNode) recordCanvas.remove();
  recordingInkLayer = null;
  recordingInkKey = '';
}

function resetRecordingButton() {
  recordingBusy = false;
  recordBtn.disabled = false;
  recordBtn.classList.remove('recording');
  recordBtn.querySelector('span').textContent = t('recordBtn');
}
''', 'Recording lifecycle state')

    s = replace_one(s, 'function compositeRecordFrame() {',
                    'function compositeRecordFrame() {\n  try {', 'Frame error handling')
    s = replace_one(s, '  recordRAF = requestAnimationFrame(compositeRecordFrame);\n}', '''
  if (recordVideoTrack && recordVideoTrack.readyState === 'live' && recordVideoTrack.requestFrame) {
    recordVideoTrack.requestFrame();
  }
  recordRAF = requestAnimationFrame(compositeRecordFrame);
  } catch (error) {
    recordingError = error;
    console.error('Recording frame failed.', error);
    stopRecording();
  }
}''', 'Explicit canvas frame delivery')

    # Retain the existing result panel and sharing behavior, but wait until the
    # actual encoded first frame decodes before announcing a ready recording.
    result_start = s.index('  const oldPanel = document.getElementById(\'recordingResultPanel\');')
    result_end = s.index('\n};\n  mediaRecorder.start(1000);', result_start)
    result_panel = s[result_start:result_end]
    result_panel = result_panel.replace("title.textContent = 'Your recording is ready';", "title.textContent = 'Checking your recording…';")
    result_panel = result_panel.replace("preview.src = url; preview.controls = true; preview.playsInline = true; preview.preload = 'metadata';",
        "preview.controls = true; preview.playsInline = true; preview.preload = 'auto';")
    result_panel = result_panel.replace("  const canShareFile = !!(navigator.share && navigator.canShare && navigator.canShare({ files: [recordingFile] }));", "  let canShareFile = false;\n  try { canShareFile = !!(navigator.share && navigator.canShare && navigator.canShare({ files: [recordingFile] })); } catch (_) {}")
    result_panel = result_panel[:result_panel.index("  recordBtn.classList.remove('recording');")]
    result_panel += r'''
  saveShare.disabled = true;
  download.style.pointerEvents = 'none';
  download.style.opacity = '.5';
  const instructions = note.textContent;
  note.textContent = 'Checking video playback…';
  let settled = false;
  const finishPreview = playable => {
    if (settled) return;
    settled = true;
    clearTimeout(previewTimeout);
    if (!overlay.isConnected) return;
    saveShare.disabled = false;
    download.style.pointerEvents = '';
    download.style.opacity = '';
    title.textContent = playable ? 'Your recording is ready' : 'Recording preview unavailable';
    note.textContent = playable ? instructions : 'The browser could not play this preview. You can download the file, or close this window and try a new recording.';
    hintText.textContent = playable ? 'Recording ready — play it or download it now.' : 'This recording could not be previewed.';
  };
  const previewTimeout = setTimeout(() => finishPreview(false), 15000);
  preview.addEventListener('loadeddata', () => finishPreview(preview.videoWidth > 0 && preview.videoHeight > 0), { once: true });
  preview.addEventListener('error', () => finishPreview(false), { once: true });
  preview.src = url;
  preview.load();
'''
    result_helper = r'''
function showRecordingResult(blob, outputMime) {
  const fileExt = outputMime.includes('mp4') ? 'mp4' : 'webm';
  const fileName = `ink-sketchbook-recording.${fileExt}`;
  const recordingFile = new File([blob], fileName, { type: outputMime });
  const url = URL.createObjectURL(blob);
  if (lastRecordingUrl) URL.revokeObjectURL(lastRecordingUrl);
  lastRecordingUrl = url;
''' + result_panel + '\n}\n'

    controller_start = s.index('function stopRecording() {')
    controller_end = s.index('\nfunction saveHistory() {', controller_start)
    old_controller = s[controller_start:controller_end]
    # Preserve the microphone capture setup, including Vanya's existing gain.
    audio_start = old_controller.index('  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {')
    audio_end = old_controller.index('\n  recordedChunks = [];', audio_start)
    audio_setup = old_controller[audio_start:audio_end]
    geometry_start = old_controller.index('  const canvasRectForRecording =')
    geometry_end = old_controller.index('  const isPhoneRecording =', geometry_start)
    geometry_setup = old_controller[geometry_start:geometry_end]
    controller = r'''function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    recordingBusy = true;
    recordBtn.disabled = true;
    recordBtn.querySelector('span').textContent = 'Saving…';
    mediaRecorder.stop();
  }
}

recordBtn.onclick = async () => {
  if (!recordingSupport || recordingBusy) return;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    stopRecording();
    return;
  }
  recordingBusy = true;
  recordBtn.disabled = true;
  recordBtn.querySelector('span').textContent = 'Preparing…';
  recordingError = null;
  recordedChunks = [];
  try {
  recordCanvas = document.createElement('canvas');
  recordCanvas.setAttribute('aria-hidden', 'true');
  // Keep the capture surface attached and paintable in Safari.
  recordCanvas.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;pointer-events:none;z-index:2147483647;box-shadow:none;';
  document.body.appendChild(recordCanvas);
''' + geometry_setup + r'''
  const outputSize = recordingOutputSize(recordSourceRect);
  recordCanvas.width = outputSize.width;
  recordCanvas.height = outputSize.height;
  recordCtx = recordCanvas.getContext('2d', { alpha: false });
  if (!recordCtx) throw new Error('The recording canvas could not be created.');
  recordCtx.fillStyle = paperColorPicker.value || '#ffffff';
  recordCtx.fillRect(0, 0, recordCanvas.width, recordCanvas.height);
  const stream = recordCanvas.captureStream(30);
  recordingStream = stream;
  recordVideoTrack = stream.getVideoTracks()[0];
  if (!recordVideoTrack) throw new Error('No video track was created.');
''' + audio_setup + r'''
  const recorder = createRecordingEncoder(stream);
  mediaRecorder = recorder;
  recorder.ondataavailable = event => {
    if (event.data && event.data.size > 0) recordedChunks.push(event.data);
  };
  recorder.onerror = event => {
    recordingError = event.error || new Error('The video encoder stopped unexpectedly.');
  };
  recorder.onstop = () => {
    const chunks = recordedChunks.slice();
    const outputMime = recorder.mimeType || (chunks.find(chunk => chunk.type) || {}).type || recordingSupport;
    const error = recordingError;
    releaseRecordingCapture();
    mediaRecorder = null;
    resetRecordingButton();
    const blob = new Blob(chunks, { type: outputMime });
    if (error || !blob.size) {
      hintText.textContent = 'The recording could not be saved. Please try recording again.';
      console.error('Recording export failed.', error || 'No encoded video data.');
      return;
    }
    showRecordingResult(blob, outputMime);
  };
  recorder.start(1000);
  // Start painting AFTER capture and encoding have started, including a first
  // explicit frame request. Do not run a second loop while awaiting the mic.
  compositeRecordFrame();
  if (recorder.state === 'recording') {
    recordingBusy = false;
    recordBtn.disabled = false;
    recordBtn.classList.add('recording');
    recordBtn.querySelector('span').textContent = t('stopRecordBtn');
    hintText.textContent = t('recordingHintMsg');
  }
  } catch (error) {
    releaseRecordingCapture();
    mediaRecorder = null;
    resetRecordingButton();
    hintText.textContent = 'Recording could not start. Please try again.';
    console.error('Recording startup failed.', error);
  }
};
'''
    s = s[:controller_start] + result_helper + '\n' + controller + s[controller_end:]
    PATH.write_text(s)

# Native share sheets identify the file by its container MIME, without codecs.
s = s.replace(
    'const recordingFile = new File([blob], fileName, { type: outputMime });',
    "const recordingFile = new File([blob], fileName, { type: outputMime.split(';')[0] });",
    1,
)
PATH.write_text(s)

def apply_color_layer(text: str) -> str:
    """Keep editable color below ink throughout display, history and output."""
    if '// artwork-color-layer-v1' in text:
        return text

    def change(old: str, new: str, label: str) -> None:
        nonlocal text
        text = replace_one(text, old, new, 'Color layer: ' + label)

    def section(start: str, end: str, new: str) -> None:
        nonlocal text
        first = text.index(start)
        last = text.index(end, first)
        text = text[:first] + new + '\n' + text[last:]

    change('  #guideCanvas { z-index: 2; pointer-events: none; }',
           '''  #colorCanvas { z-index: 2; pointer-events: none; }
  #guideCanvas { z-index: 3; pointer-events: none; }
  .layer-switch { display:flex; align-items:center; gap:4px; }
  .layer-switch > span { font-size:12px; color:#6b6558; margin-right:2px; }
  .layer-switch button { padding:7px 10px; }
  #colorBrushControls[hidden] { display:none; }
  #colorBrushControls small { color:#8a8373; line-height:1.4; }''', 'layer styles')
    change('  #drawCanvas { z-index: 3; }', '  #drawCanvas { z-index: 4; }', 'ink stacking')
    change('<canvas id="guideCanvas"></canvas>',
           '<canvas id="colorCanvas" aria-hidden="true"></canvas>\n      <canvas id="guideCanvas"></canvas>', 'color canvas')
    change('      <button id="drawModeBtn"',
           '''      <div class="layer-switch" role="group" aria-label="Drawing layer">
        <span data-i18n="layerLabel">Layer</span>
        <button id="inkLayerBtn" class="active" type="button" aria-pressed="true" data-i18n="inkLayerLabel">Ink</button>
        <button id="colorLayerBtn" type="button" aria-pressed="false" data-i18n="colorLayerLabel">Color</button>
      </div>
      <button id="drawModeBtn"''', 'layer switch')
    change('      <div class="row palette" id="palette"></div>',
           '''      <div id="colorBrushControls" class="slider-group" hidden>
        <span><span data-i18n="colorBrushLabel">Color brush size</span> <b id="colorBrushSizeValue">28</b></span>
        <input type="range" id="colorBrushSize" min="2" max="100" step="1" value="28" aria-label="Color brush size">
        <small data-i18n="colorLayerHint">Paint here to keep color beneath your ink lines.</small>
      </div>
      <div class="row palette" id="palette"></div>''', 'color brush')
    change("const ctx = drawCanvas.getContext('2d', { willReadFrequently: true });",
           '''// artwork-color-layer-v1
const inkCtx = drawCanvas.getContext('2d', { willReadFrequently: true });
const colorCanvas = document.getElementById('colorCanvas');
const colorCtx = colorCanvas.getContext('2d', { willReadFrequently: true });
let ctx = inkCtx;
let activeLayer = 'ink';
let artworkRevision = 0;
const layerColors = { ink:'#2a2620', color:'#ddb69f' };
const inkLayerBtn = document.getElementById('inkLayerBtn');
const colorLayerBtn = document.getElementById('colorLayerBtn');
const colorBrushControls = document.getElementById('colorBrushControls');
const colorBrushSize = document.getElementById('colorBrushSize');
const colorBrushSizeValue = document.getElementById('colorBrushSizeValue');''', 'editing contexts')
    change("detailCanvas.style.cssText = 'position:absolute;left:0;top:0;z-index:4;",
           "detailCanvas.style.cssText = 'position:absolute;left:0;top:0;z-index:5;", 'sharp ink stacking')
    change("const detailCtx = detailCanvas.getContext('2d');",
           '''const detailCtx = detailCanvas.getContext('2d');
const detailColorCanvas = document.createElement('canvas');
detailColorCanvas.id = 'detailColorCanvas';
detailColorCanvas.setAttribute('aria-hidden', 'true');
detailColorCanvas.style.cssText = 'position:absolute;left:0;top:0;z-index:2;pointer-events:none;display:none;box-shadow:none;';
wrap.appendChild(detailColorCanvas);
const detailColorCtx = detailColorCanvas.getContext('2d');''', 'sharp color canvas')
    change('  en: {', '''  en: {
    layerLabel: "Layer", inkLayerLabel: "Ink", colorLayerLabel: "Color",
    colorBrushLabel: "Color brush size", colorLayerHint: "Paint here to keep color beneath your ink lines.",
    clearInkLayer: "Clear ink layer", clearColorLayer: "Clear color layer",''', 'labels')
    # Keep the small new controls translated with the app's existing languages.
    labels = {
        'es': ('Capa', 'Tinta', 'Color', 'Tamaño del pincel', 'El color queda debajo de las líneas.', 'Borrar tinta', 'Borrar color'),
        'fr': ('Calque', 'Encre', 'Couleur', 'Taille du pinceau', 'La couleur reste sous les traits.', "Effacer l’encre", 'Effacer la couleur'),
        'de': ('Ebene', 'Tusche', 'Farbe', 'Pinselgröße', 'Die Farbe bleibt unter den Linien.', 'Tuscheebene leeren', 'Farbebene leeren'),
        'it': ('Livello', 'Inchiostro', 'Colore', 'Dimensione pennello', 'Il colore rimane sotto le linee.', "Cancella inchiostro", 'Cancella colore'),
        'pt': ('Camada', 'Tinta', 'Cor', 'Tamanho do pincel', 'A cor fica por baixo das linhas.', 'Limpar tinta', 'Limpar cor'),
        'nl': ('Laag', 'Inkt', 'Kleur', 'Penseelgrootte', 'De kleur blijft onder de inktlijnen.', 'Inktlaag wissen', 'Kleurlaag wissen'),
        'ja': ('レイヤー', 'インク', '色', 'ブラシサイズ', '色はインク線の下に描かれます。', 'インクを消去', '色を消去'),
        'zh': ('图层', '墨线', '颜色', '画笔大小', '颜色始终位于墨线下方。', '清空墨线层', '清空颜色层'),
    }
    import json
    for lang, values in labels.items():
        keys = ('layerLabel', 'inkLayerLabel', 'colorLayerLabel', 'colorBrushLabel', 'colorLayerHint', 'clearInkLayer', 'clearColorLayer')
        additions = ', '.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in zip(keys, values))
        change(f'  {lang}: {{', f'  {lang}: {{\n    {additions},', f'{lang} labels')
    change("  hintText.textContent = t('hintDefault');\n}",
           "  hintText.textContent = t('hintDefault');\n  syncLayerControls();\n}", 'translated clear label')

    # Both native layers retain the original full print-resolution pixel grid.
    text = text.replace('[refCanvas, guideCanvas, drawCanvas, refDomLayer].forEach',
                        '[refCanvas, guideCanvas, colorCanvas, drawCanvas, refDomLayer].forEach')
    change('const prev = drawCanvas.width ? ctx.getImageData(0,0,drawCanvas.width,drawCanvas.height) : null;',
           '''const prev = drawCanvas.width ? inkCtx.getImageData(0,0,drawCanvas.width,drawCanvas.height) : null;
  const prevColor = colorCanvas.width ? colorCtx.getImageData(0,0,colorCanvas.width,colorCanvas.height) : null;''', 'preserve resize')
    change('  if (prev) ctx.putImageData(prev, 0, 0);',
           '  if (prev) inkCtx.putImageData(prev, 0, 0);\n  if (prevColor) colorCtx.putImageData(prevColor, 0, 0);\n  artworkRevision++;', 'restore resize')

    section('function ensureDetailCanvasSize() {', 'function scheduleDetailRender() {', r'''function ensureDetailCanvasSize() {
  const rect = wrap.getBoundingClientRect();
  detailPixelRatio = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
  const w = Math.max(2, Math.round(rect.width * detailPixelRatio));
  const h = Math.max(2, Math.round(rect.height * detailPixelRatio));
  for (const canvas of [detailCanvas, detailColorCanvas]) {
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
  }
}

function setDetailTransform(target = detailCtx) {
  const baseW = canvasDisplayCssW || canvasBaseCssW || 1;
  const baseH = canvasDisplayCssH || canvasBaseCssH || 1;
  target.setTransform(detailPixelRatio, 0, 0, detailPixelRatio, 0, 0);
  target.translate(canvasDisplayLeft + view.x, canvasDisplayTop + view.y);
  target.rotate(view.rotation * Math.PI / 180);
  target.scale(baseW * view.scale / Math.max(1, drawCanvas.width), baseH * view.scale / Math.max(1, drawCanvas.height));
}

function paintDetailOp(op, target = detailCtx) {
  if (!op) return;
  if (op.kind === 'clear') { target.clearRect(0, 0, drawCanvas.width, drawCanvas.height); return; }
  target.save();
  target.globalCompositeOperation = op.mode === 'erase' ? 'destination-out' : 'source-over';
  target.lineJoin = 'round'; target.lineCap = 'round'; target.lineWidth = op.width;
  target.fillStyle = target.strokeStyle = op.mode === 'erase' ? '#000' : op.color;
  target.beginPath();
  if (op.kind === 'dot') {
    target.arc(op.x, op.y, op.width / 2, 0, Math.PI * 2); target.fill();
  } else {
    target.moveTo(op.x1, op.y1); target.lineTo(op.x2, op.y2); target.stroke();
  }
  target.restore();
}

function renderDetailView() {
  detailRenderRAF = null;
  if (!detailZoomIsActive()) {
    detailCanvas.style.display = detailColorCanvas.style.display = 'none';
    drawCanvas.style.opacity = '';
    colorCanvas.style.opacity = '';
    return;
  }
  ensureDetailCanvasSize();
  for (const [canvas, target, layer] of [[detailColorCanvas, detailColorCtx, 'color'], [detailCanvas, detailCtx, 'ink']]) {
    target.setTransform(1, 0, 0, 1, 0, 0);
    target.globalCompositeOperation = 'source-over';
    target.clearRect(0, 0, canvas.width, canvas.height);
    canvas.style.display = 'block';
    target.save();
    setDetailTransform(target);
    target.beginPath(); target.rect(0, 0, drawCanvas.width, drawCanvas.height); target.clip();
    for (let i = 0; i < detailVisibleCount; i++) {
      const stroke = detailStrokes[i];
      if (stroke && (stroke.layer || 'ink') === layer) for (const op of stroke.ops) paintDetailOp(op, target);
    }
    if (activeDetailStroke && activeDetailStroke.layer === layer)
      for (const op of activeDetailStroke.ops) paintDetailOp(op, target);
    target.restore();
  }
  drawCanvas.style.opacity = '0';
  colorCanvas.style.opacity = '0';
}
''')
    change('if (detailVectorValid) activeDetailStroke = { ops: [] };',
           'if (detailVectorValid) activeDetailStroke = { layer:activeLayer, ops: [] };', 'tag strokes')
    section('function drawDetailOpLive(op) {', 'function recordDetailSegment(', r'''function drawDetailOpLive(op) {
  if (!detailZoomIsActive()) return;
  const canvas = activeLayer === 'color' ? detailColorCanvas : detailCanvas;
  const target = activeLayer === 'color' ? detailColorCtx : detailCtx;
  if (canvas.style.display === 'none') { scheduleDetailRender(); return; }
  target.save();
  setDetailTransform(target);
  target.beginPath(); target.rect(0, 0, drawCanvas.width, drawCanvas.height); target.clip();
  paintDetailOp(op, target);
  target.restore();
}
''')
    change('function recordDetailSegment(x1, y1, x2, y2, width, strokeMode, color) {',
           'function recordDetailSegment(x1, y1, x2, y2, width, strokeMode, color) {\n  artworkRevision++;', 'live segment revision')
    change('function recordDetailDot(x, y, width, strokeMode, color) {',
           'function recordDetailDot(x, y, width, strokeMode, color) {\n  artworkRevision++;', 'live dot revision')
    # Some upstream pages already have this fix; preserve in-progress geometry
    # when a second finger turns drawing into a zoom gesture on either layer.
    interrupted_stroke = "  } else if (activePointers.size === 2) {\n    drawing = false;"
    if interrupted_stroke in text:
        change(interrupted_stroke, """  } else if (activePointers.size === 2) {
    if (drawing && activeDetailStroke && activeDetailStroke.ops.length) {
      commitDetailStroke();
      saveHistory();
    } else {
      activeDetailStroke = null;
    }
    drawing = false;""", 'pinch during a stroke')

    section('function saveHistory() {', 'function getPos(e) {', r'''function saveHistory(changedLayer = activeLayer) {
  const previous = history[history.length - 1];
  const capture = (layer, target) => previous && changedLayer !== layer && changedLayer !== 'both'
    ? previous[layer] : target.getImageData(0, 0, drawCanvas.width, drawCanvas.height);
  // Reuse the unchanged layer's snapshot instead of doubling per-stroke memory.
  history.push({ ink:capture('ink', inkCtx), color:capture('color', colorCtx), detailCount:detailVisibleCount });
  if (history.length > 30) history.shift();
  redoStack = [];
  artworkRevision++;
  scheduleDetailRender();
}
saveHistory('both');

function restoreArtworkState(state) {
  inkCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  colorCtx.clearRect(0, 0, colorCanvas.width, colorCanvas.height);
  inkCtx.putImageData(state.ink, 0, 0);
  colorCtx.putImageData(state.color, 0, 0);
  detailVisibleCount = state.detailCount;
  activeDetailStroke = null;
  artworkRevision++;
  scheduleDetailRender();
}

function syncLayerControls() {
  inkLayerBtn.classList.toggle('active', activeLayer === 'ink');
  colorLayerBtn.classList.toggle('active', activeLayer === 'color');
  inkLayerBtn.setAttribute('aria-pressed', String(activeLayer === 'ink'));
  colorLayerBtn.setAttribute('aria-pressed', String(activeLayer === 'color'));
  colorBrushControls.hidden = activeLayer !== 'color';
  clearBtn.textContent = t(activeLayer === 'color' ? 'clearColorLayer' : 'clearInkLayer');
}

function selectArtworkLayer(layer) {
  if (layer !== 'ink' && layer !== 'color') return;
  if (drawing) endStroke();
  layerColors[activeLayer] = currentColor;
  activeLayer = layer;
  ctx = layer === 'color' ? colorCtx : inkCtx;
  currentColor = layerColors[layer];
  colorPicker.value = currentColor;
  document.querySelectorAll('.swatch').forEach(s => s.classList.remove('active'));
  syncLayerControls();
}
inkLayerBtn.onclick = () => selectArtworkLayer('ink');
colorLayerBtn.onclick = () => selectArtworkLayer('color');
colorBrushSize.oninput = () => { colorBrushSizeValue.textContent = colorBrushSize.value; };
syncLayerControls();
''')
    # A broad color brush has a dedicated size, keeping existing ink settings.
    change("  } else if (usingPressure) {", "  } else if (activeLayer === 'color') {\n    targetWidth = parseFloat(colorBrushSize.value) * dpr * (usingPressure ? 0.25 + Math.max(0.08, e.pressure) * 0.75 : 1);\n  } else if (usingPressure) {", 'color brush width')
    change("    if (wobbleIntensity > 0) {", "    if (activeLayer === 'ink' && wobbleIntensity > 0) {", 'color brush steadiness')
    change('      : minW + pressure * (maxW - minW);',
           "      : activeLayer === 'color' ? parseFloat(colorBrushSize.value) * dpr * (usingPressure ? 0.25 + pressure * 0.75 : 1)\n      : minW + pressure * (maxW - minW);", 'color brush dots')
    section('undoBtn.onclick = () => {', 'function flattenOntoBackground(bgColor) {', r'''undoBtn.onclick = () => {
  if (drawing) endStroke();
  if (history.length > 1) {
    redoStack.push(history.pop());
    restoreArtworkState(history[history.length - 1]);
  }
};
redoBtn.onclick = () => {
  if (drawing) endStroke();
  if (redoStack.length) {
    const state = redoStack.pop();
    history.push(state);
    restoreArtworkState(state);
  }
};
clearBtn.onclick = () => {
  if (drawing) endStroke();
  ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  if (detailVectorValid) {
    beginDetailStroke();
    activeDetailStroke.ops.push({kind:'clear'});
    commitDetailStroke();
  }
  saveHistory();
};

function composeArtworkCanvas() {
  const artwork = document.createElement('canvas');
  artwork.width = drawCanvas.width; artwork.height = drawCanvas.height;
  const target = artwork.getContext('2d');
  target.drawImage(colorCanvas, 0, 0);
  target.drawImage(drawCanvas, 0, 0);
  return artwork;
}
''')
    change('  fctx.drawImage(drawCanvas, 0, 0);',
           '  fctx.drawImage(colorCanvas, 0, 0);\n  fctx.drawImage(drawCanvas, 0, 0);', 'JPEG and PDF layers')
    change("const rawBytes = dataUrlToBytes(drawCanvas.toDataURL('image/png'));",
           "const rawBytes = dataUrlToBytes(composeArtworkCanvas().toDataURL('image/png'));", 'transparent PNG layers')
    change("    const dataUrl = drawCanvas.toDataURL('image/png');",
           "    const dataUrl = composeArtworkCanvas().toDataURL('image/png');\n    const inkDataUrl = drawCanvas.toDataURL('image/png');\n    const colorDataUrl = colorCanvas.toDataURL('image/png');", 'save independent layers')
    change('const entry = { id, dataUrl, savedAt: new Date().toISOString() };',
           'const entry = { id, version:2, dataUrl, inkDataUrl, colorDataUrl, savedAt: new Date().toISOString() };', 'saved file schema')
    section('function renderDrawingsList() {', '  const listEl =', r'''async function loadArtworkEntry(entry) {
  const decode = url => !url ? Promise.resolve(null) : new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Saved drawing could not be loaded.'));
    image.src = url;
  });
  const [ink, color] = await Promise.all([decode(entry.inkDataUrl || entry.dataUrl), decode(entry.colorDataUrl)]);
  if (drawing) endStroke();
  inkCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  colorCtx.clearRect(0, 0, colorCanvas.width, colorCanvas.height);
  if (ink) inkCtx.drawImage(ink, 0, 0, drawCanvas.width, drawCanvas.height);
  if (color) colorCtx.drawImage(color, 0, 0, colorCanvas.width, colorCanvas.height);
  // Legacy drawings load as ink; new drawings keep the two editable rasters.
  resetDetailVectors(false);
  history = [];
  saveHistory('both');
  selectArtworkLayer('ink');
}

function renderDrawingsList() {''')
    section('    thumb.onclick = () => {', "    const del = document.createElement('div');", r'''    thumb.onclick = async () => {
      try {
        await loadArtworkEntry(entry);
        document.getElementById('loadOverlay').classList.remove('show');
        hintText.textContent = t('drawingLoadedMsg');
      } catch (error) {
        hintText.textContent = error.message;
      }
    };
''')

    # Record each editable layer separately so erasing never cuts through both.
    section('let recordingInkLayer = null;', 'function compositeRecordFrame() {', r'''let recordingInkLayer = null;
let recordingInkKey = '';
let recordingColorLayer = null;
let recordingColorKey = '';
function paintRecordingInk(source) {
  if (typeof detailVectorValid === 'undefined' || !detailVectorValid || typeof detailStrokes === 'undefined') return false;
  for (const layer of ['color', 'ink']) {
    let canvas = layer === 'color' ? recordingColorLayer : recordingInkLayer;
    const oldKey = layer === 'color' ? recordingColorKey : recordingInkKey;
    if (!canvas || canvas.width !== recordCanvas.width || canvas.height !== recordCanvas.height) {
      canvas = document.createElement('canvas');
      canvas.width = recordCanvas.width; canvas.height = recordCanvas.height;
      if (layer === 'color') { recordingColorLayer = canvas; recordingColorKey = ''; }
      else { recordingInkLayer = canvas; recordingInkKey = ''; }
    }
    const activeCount = activeDetailStroke ? activeDetailStroke.ops.length : 0;
    const key = [artworkRevision, detailVisibleCount, activeCount, source.x, source.y,
      source.width, source.height, recordCanvas.width, recordCanvas.height].join(':');
    if (key !== oldKey) {
      const target = canvas.getContext('2d');
      target.setTransform(1, 0, 0, 1, 0, 0);
      target.clearRect(0, 0, canvas.width, canvas.height);
      const sx = recordCanvas.width / source.width, sy = recordCanvas.height / source.height;
      target.save();
      target.setTransform(sx, 0, 0, sy, -source.x * sx, -source.y * sy);
      target.beginPath(); target.rect(0, 0, drawCanvas.width, drawCanvas.height); target.clip();
      const paint = op => {
        if (op.kind === 'clear') { target.clearRect(0, 0, drawCanvas.width, drawCanvas.height); return; }
        target.globalCompositeOperation = op.mode === 'erase' ? 'destination-out' : 'source-over';
        target.lineCap = 'round'; target.lineJoin = 'round'; target.lineWidth = op.width;
        target.fillStyle = target.strokeStyle = op.mode === 'erase' ? '#000' : op.color;
        target.beginPath();
        if (op.kind === 'dot') { target.arc(op.x, op.y, op.width / 2, 0, Math.PI * 2); target.fill(); }
        else { target.moveTo(op.x1, op.y1); target.lineTo(op.x2, op.y2); target.stroke(); }
      };
      for (let i = 0; i < detailVisibleCount; i++) {
        const stroke = detailStrokes[i];
        if ((stroke.layer || 'ink') === layer) for (const op of stroke.ops) paint(op);
      }
      if (activeDetailStroke && (activeDetailStroke.layer || 'ink') === layer)
        for (const op of activeDetailStroke.ops) paint(op);
      target.restore();
      target.globalCompositeOperation = 'source-over';
      if (layer === 'color') recordingColorKey = key; else recordingInkKey = key;
    }
    recordCtx.drawImage(canvas, 0, 0);
  }
  return true;
}
''')
    change('  recordCtx.drawImage(drawCanvas, source.x, source.y, source.width, source.height, 0, 0, recordCanvas.width, recordCanvas.height);',
           '  recordCtx.drawImage(colorCanvas, source.x, source.y, source.width, source.height, 0, 0, recordCanvas.width, recordCanvas.height);\n  recordCtx.drawImage(drawCanvas, source.x, source.y, source.width, source.height, 0, 0, recordCanvas.width, recordCanvas.height);', 'saved layer recording')
    change("  recordingInkLayer = null;\n  recordingInkKey = '';",
           "  recordingInkLayer = null;\n  recordingInkKey = '';\n  recordingColorLayer = null;\n  recordingColorKey = '';", 'release color recording cache')
    return text


def apply_precise_eraser(text: str) -> str:
    """Use an exact screen-sized eraser that follows the pointer directly."""
    if '// precise-eraser-v1' in text:
        return text

    def change(old: str, new: str, label: str) -> None:
        nonlocal text
        text = replace_one(text, old, new, 'Precise eraser: ' + label)

    change('''<div class="slider-group"><span data-i18n="eraserSizeLabel">Eraser size</span> <input type="range" id="eraserSizeSlider" min="10" max="200" value="60"></div>''',
           '''<div class="slider-group">
        <label for="eraserSizeInput" data-i18n="eraserSizeLabel">Eraser size</label>
        <div style="display:flex;align-items:center;gap:6px;"><input type="number" id="eraserSizeInput" min="0.5" max="200" value="4" step="0.5" inputmode="decimal" style="width:76px;font:inherit;padding:6px;border:1px solid #d8d3c6;border-radius:6px;"><span>px</span></div>
        <input type="range" id="eraserSizeSlider" min="0.5" max="200" value="4" step="0.5" aria-label="Eraser size">
      </div>''', 'size control')
    change('function startStroke(e) {', r'''// precise-eraser-v1
function getEraserSize() {
  const size = parseFloat(eraserSizeSlider.value);
  return Math.max(0.5, Math.min(200, Number.isFinite(size) ? size : 4));
}

function getEraserCanvasWidth() {
  // The chosen diameter is in screen pixels. Zoom reveals finer artwork
  // beneath the same small eraser instead of enlarging the eraser with it.
  return getEraserSize() * getDisplayDpr() / Math.max(0.01, view.scale || 1);
}

function startStroke(e) {''', 'size conversion')
    change('  if (dist < 1.2 * dpr) return;',
           "  if (dist < (mode === 'erase' ? 0.02 * dpr / Math.max(0.01, view.scale || 1) : 1.2 * dpr)) return;", 'small movements')
    change('    targetWidth = parseFloat(eraserSizeSlider.value) * dpr;',
           '    targetWidth = getEraserCanvasWidth();', 'moving diameter')
    change('      ? parseFloat(eraserSizeSlider.value) * dpr',
           '      ? getEraserCanvasWidth()', 'tap diameter')
    change('  smoothedWidth = smoothedWidth === null ? targetWidth : smoothedWidth + (targetWidth - smoothedWidth) * 0.35;',
           "  smoothedWidth = mode === 'erase' || smoothedWidth === null ? targetWidth : smoothedWidth + (targetWidth - smoothedWidth) * 0.35;", 'fixed diameter')
    change('  const streamlineStrength = Math.max(0, Math.min(1, parseFloat(streamlineSlider.value) / 100));',
           "  const streamlineStrength = mode === 'erase' ? 0 : Math.max(0, Math.min(1, parseFloat(streamlineSlider.value) / 100));", 'direct pointer path')
    change('''    continueStroke(e);
  } else if (activePointers.size === 3''',
           '''    const samples = mode === 'erase' && typeof e.getCoalescedEvents === 'function' ? e.getCoalescedEvents() : null;
    if (samples && samples.length) for (const sample of samples) continueStroke(sample);
    else continueStroke(e);
  } else if (activePointers.size === 3''', 'precise pointer samples')
    change('''  if (activePointers.size === 0) {
    endStroke();''',
           '''  if (activePointers.size === 0) {
    if (drawing && mode === 'erase' && e.type === 'pointerup') continueStroke(e);
    endStroke();''', 'final pointer position')
    controls = r'''
// The eraser outline is a private UI aid; export/recording use artwork only.
const eraserSizeInput = document.getElementById('eraserSizeInput');
const eraserCursor = document.createElement('div');
eraserCursor.id = 'eraserCursor';
eraserCursor.setAttribute('aria-hidden', 'true');
eraserCursor.style.cssText = 'position:absolute;z-index:6;pointer-events:none;display:none;outline:1px solid #2a2620;border-radius:50%;box-shadow:0 0 0 2px #fff;transform:translate(-50%,-50%);';
wrap.appendChild(eraserCursor);
function syncEraserSize() {
  eraserSizeInput.value = String(getEraserSize());
  eraserCursor.style.width = eraserCursor.style.height = getEraserSize() + 'px';
}
eraserSizeSlider.addEventListener('input', syncEraserSize);
eraserSizeSlider.addEventListener('change', syncEraserSize);
eraserSizeInput.addEventListener('input', () => {
  const size = parseFloat(eraserSizeInput.value);
  if (!Number.isFinite(size) || size < 0.5 || size > 200) return;
  eraserSizeSlider.value = String(size);
  eraserCursor.style.width = eraserCursor.style.height = getEraserSize() + 'px';
});
eraserSizeInput.addEventListener('change', () => {
  const size = parseFloat(eraserSizeInput.value);
  eraserSizeSlider.value = String(Number.isFinite(size) ? Math.max(0.5, Math.min(200, size)) : 4);
  syncEraserSize();
});
function hideEraserCursor() { eraserCursor.style.display = 'none'; }
function showEraserCursor(e) {
  if (mode !== 'erase' || guideMoveMode || activePointers.size > 1) { hideEraserCursor(); return; }
  const rect = wrap.getBoundingClientRect();
  eraserCursor.style.left = (e.clientX - rect.left) + 'px';
  eraserCursor.style.top = (e.clientY - rect.top) + 'px';
  eraserCursor.style.display = 'block';
}
drawCanvas.addEventListener('pointerdown', showEraserCursor);
drawCanvas.addEventListener('pointermove', showEraserCursor);
drawCanvas.addEventListener('pointerleave', hideEraserCursor);
drawCanvas.addEventListener('pointercancel', hideEraserCursor);
drawCanvas.addEventListener('pointerup', e => { if (e.pointerType === 'touch') hideEraserCursor(); });
drawModeBtn.addEventListener('click', () => { drawCanvas.style.cursor = ''; hideEraserCursor(); });
eraseModeBtn.addEventListener('click', () => { drawCanvas.style.cursor = 'none'; });
syncEraserSize();
'''
    change('</script>\n</body>', controls + '\n</script>\n</body>', 'private size outline')
    return text


def apply_color_pressure_brush(text: str) -> str:
    """Paint a continuous pressure-shaped fill on the color layer."""
    if '// color-pressure-brush-v1' in text:
        return text

    def change(old: str, new: str, label: str) -> None:
        nonlocal text
        text = replace_one(text, old, new, 'Pressure color brush: ' + label)

    geometry = Path('scripts/perfect-freehand-1.2.3.js').read_text()
    helpers = r'''// color-pressure-brush-v1
let colorBrushStroke = null;
let colorBrushRAF = null;

function paintColorBrushShape(target, op) {
  const outline = op.outline;
  if (!outline || outline.length < 3) return;
  target.save();
  target.globalCompositeOperation = 'source-over';
  target.fillStyle = op.color;
  const last = outline[outline.length - 1], first = outline[0];
  target.beginPath();
  target.moveTo((last[0] + first[0]) / 2, (last[1] + first[1]) / 2);
  for (let i = 0; i < outline.length; i++) {
    const point = outline[i], next = outline[(i + 1) % outline.length];
    target.quadraticCurveTo(point[0], point[1], (point[0] + next[0]) / 2, (point[1] + next[1]) / 2);
  }
  target.closePath();
  target.fill();
  target.restore();
}

function beginColorBrush(e) {
  const base = document.createElement('canvas');
  base.width = colorCanvas.width; base.height = colorCanvas.height;
  base.getContext('2d').drawImage(colorCanvas, 0, 0);
  const p = points[0];
  const pressure = usingPressure ? Math.max(0.005, Math.min(1, e.pressure || 0.005)) : 1;
  colorBrushStroke = {
    base, samples:[[p.x, p.y, Math.pow(pressure, 1.2)]],
    size:Math.max(2, parseFloat(colorBrushSize.value) || 28) * getDisplayDpr(),
    pressure:usingPressure, color:currentColor, bounds:null, length:0,
    dirty:true,op:{kind:'brush',mode:'draw',color:currentColor,outline:[]}
  };
  scheduleColorBrushUpdate();
}

function scheduleColorBrushUpdate() {
  if (!colorBrushStroke) return;
  colorBrushStroke.dirty=true;
  if (colorBrushRAF === null) colorBrushRAF = requestAnimationFrame(() => {
    colorBrushRAF = null;
    renderColorBrushNow();
  });
}

function updateColorBrushShape(finished) {
  const stroke = colorBrushStroke;
  if (!stroke) return;
  stroke.dirty=false;
  if (finished && !moved) {
    const p = stroke.samples[0];
    stroke.op = {kind:'dot',mode:'draw',color:stroke.color,x:p[0],y:p[1],width:Math.max(0.4,stroke.size*p[2])};
  } else {
    stroke.op = {
      kind:'brush',mode:'draw',color:stroke.color,
      outline:getColorStrokeOutline(stroke.samples, {
        size:stroke.size / 2, thinning:1, smoothing:.55,
        streamline:Math.max(0, Math.min(.45, (parseFloat(streamlineSlider.value) || 0) / 250)),
        simulatePressure:false, last:true,
        start:{cap:false,taper:Math.min(stroke.size*.35, stroke.length*.2)},
        end:{cap:false,taper:finished ? Math.min(stroke.size*.4, stroke.length*.25) : 0}
      })
    };
  }
  if (detailVectorValid && activeDetailStroke) activeDetailStroke.ops = [stroke.op];
  artworkRevision++;
  scheduleDetailRender();
}

function renderColorBrushNow() {
  const stroke = colorBrushStroke;
  if (!stroke) return;
  if (stroke.dirty) updateColorBrushShape(false);
  let bounds = stroke.bounds;
  const include = (x, y) => {
    if (!bounds) bounds = {left:x,top:y,right:x,bottom:y};
    else { bounds.left=Math.min(bounds.left,x);bounds.top=Math.min(bounds.top,y);bounds.right=Math.max(bounds.right,x);bounds.bottom=Math.max(bounds.bottom,y); }
  };
  if (stroke.op.kind === 'dot') {
    const op = stroke.op;
    include(op.x-op.width/2,op.y-op.width/2); include(op.x+op.width/2,op.y+op.width/2);
  } else for (const p of stroke.op.outline) include(p[0],p[1]);
  if (!bounds) return;
  stroke.bounds = bounds;
  const x=Math.max(0,Math.floor(bounds.left)-2),y=Math.max(0,Math.floor(bounds.top)-2);
  const w=Math.min(colorCanvas.width,Math.ceil(bounds.right)+2)-x;
  const h=Math.min(colorCanvas.height,Math.ceil(bounds.bottom)+2)-y;
  if (w<=0 || h<=0) return;
  colorCtx.save();
  colorCtx.setTransform(1,0,0,1,0,0);
  colorCtx.globalCompositeOperation='source-over';
  colorCtx.beginPath();colorCtx.rect(x,y,w,h);colorCtx.clip();
  // Restore the previous paint before replacing the active outline. This
  // prevents old broad tips or overlapping round segments from accumulating.
  colorCtx.clearRect(x,y,w,h);
  colorCtx.drawImage(stroke.base,x,y,w,h,x,y,w,h);
  paintDetailOp(stroke.op,colorCtx);
  colorCtx.restore();
}

function continueColorBrush(e) {
  const stroke=colorBrushStroke;
  if (!stroke) return;
  const p=getPos(e),previous=stroke.samples[stroke.samples.length-1];
  const distance=Math.hypot(p.x-previous[0],p.y-previous[1]);
  const rawPressure=stroke.pressure
    ? (e.type==='pointerup' || !(e.pressure>0) ? Math.pow(previous[2],1/1.2) : Math.min(1,e.pressure)) : 1;
  const pressure=Math.pow(Math.max(.005,rawPressure),1.2);
  if (distance < .02 * getDisplayDpr() / Math.max(1,view.scale)) {
    if (Math.abs(pressure-previous[2])>.002) {
      previous[2]=pressure;scheduleColorBrushUpdate();
    }
    return;
  }
  stroke.samples.push([p.x,p.y,pressure]);
  stroke.length+=distance;
  moved=true;lastPressure=e.pressure;
  points.push(p);lastRenderedPoint={x:p.x,y:p.y};lastPenPos={x:p.x,y:p.y};
  scheduleColorBrushUpdate();
}

function finishColorBrush(cancel = false) {
  if (!colorBrushStroke) return;
  if (cancel) {
    colorBrushStroke.dirty=false;
    colorBrushStroke.op={kind:'brush',mode:'draw',color:colorBrushStroke.color,outline:[]};
    activeDetailStroke=null;
    artworkRevision++;
  } else updateColorBrushShape(true);
  if (colorBrushRAF !== null) cancelAnimationFrame(colorBrushRAF);
  colorBrushRAF=null;
  renderColorBrushNow();
  colorBrushStroke=null;
  scheduleDetailRender();
}

'''
    change('function startStroke(e) {', geometry + '\n' + helpers + 'function startStroke(e) {', 'brush controller')
    change("  if (!op) return;\n  if (op.kind === 'clear')",
           "  if (!op) return;\n  if (op.kind === 'brush') { paintColorBrushShape(target, op); return; }\n  if (op.kind === 'clear')", 'sharp display outline')
    change("      const paint = op => {\n        if (op.kind === 'clear')",
           "      const paint = op => {\n        if (op.kind === 'brush') { paintColorBrushShape(target, op); return; }\n        if (op.kind === 'clear')", 'recorded outline')
    change('''  lastPenPos = { x: points[0].x, y: points[0].y };
}''', '''  lastPenPos = { x: points[0].x, y: points[0].y };
  if (activeLayer === 'color' && mode === 'draw') beginColorBrush(e);
}''', 'begin color stroke')
    change('''function continueStroke(e) {
  if (!drawing) return;''', '''function continueStroke(e) {
  if (!drawing) return;
  if (colorBrushStroke) { continueColorBrush(e); return; }''', 'route color strokes')
    change('''function endStroke() {
  if (!drawing) return;''', '''function endStroke() {
  if (!drawing) return;
  if (colorBrushStroke) {
    finishColorBrush();drawing=false;commitDetailStroke();saveHistory();return;
  }''', 'finish color stroke')
    change('''  } else if (activePointers.size === 2) {
    if (drawing && activeDetailStroke''', '''  } else if (activePointers.size === 2) {
    if (colorBrushStroke) {
      const painted=moved;
      finishColorBrush(!painted);
      if (painted && !detailVectorValid) saveHistory();
    }
    if (drawing && activeDetailStroke''', 'pinch during color stroke')
    change("const samples = mode === 'erase' && typeof e.getCoalescedEvents === 'function'",
           "const samples = (mode === 'erase' || colorBrushStroke) && typeof e.getCoalescedEvents === 'function'", 'stylus pressure samples')
    change("if (drawing && mode === 'erase' && e.type === 'pointerup') continueStroke(e);",
           "if (drawing && (mode === 'erase' || colorBrushStroke) && e.type === 'pointerup') continueStroke(e);", 'final color sample')
    change('Paint here to keep color beneath your ink lines.',
           'Light pressure makes a fine tip; press harder for broad, smooth color beneath your ink lines.', 'brush help')
    # The English fallback is used by the existing data-i18n control.
    change('colorLayerHint: "Paint here to keep color beneath your ink lines."',
           'colorLayerHint: "Light pressure makes a fine tip; press harder for broad, smooth color beneath your ink lines."', 'translated brush help')
    return text


def apply_solid_color_brush(text: str) -> str:
    """Union every painted section, including tight loops and reversals."""
    if '// solid-color-brush-v2' in text:
        return text

    def change(old: str, new: str, label: str) -> None:
        nonlocal text
        text = replace_one(text, old, new, 'Solid color brush: ' + label)

    # Use the library's smoothed centerline, with a coverage renderer whose
    # subpaths all have positive winding. Self-crossings can only add color.
    change('  return exports.getStroke;\n})();',
           '  exports.getStroke.getPoints = exports.getStrokePoints;\n  return exports.getStroke;\n})();', 'centerline geometry')
    first = text.index('function paintColorBrushShape(target, op) {')
    last = text.index('function beginColorBrush(e) {', first)
    text = text[:first] + r'''function paintColorBrushShape(target, op) {
  // solid-color-brush-v2
  const sweep=op.sweep,outline=op.outline;
  if (!sweep && (!outline || outline.length<3)) return;
  target.save();
  target.globalCompositeOperation='source-over';
  target.globalAlpha=1;
  target.fillStyle=op.color;
  target.beginPath();
  if (sweep) {
    for(let i=0;i<sweep.length;i++) {
      const p=sweep[i],r=p[2];
      if(r>0) {
        target.moveTo(p[0]+r,p[1]);
        target.arc(p[0],p[1],r,0,Math.PI*2);
        target.closePath();
      }
      if(i===0) continue;
      const a=sweep[i-1],distance=Math.hypot(p[0]-a[0],p[1]-a[1]);
      if(distance<.00001) continue;
      const nx=-(p[1]-a[1])/distance,ny=(p[0]-a[0])/distance;
      // This vertex order matches the circles' winding even when the brush
      // reverses direction. Fill the entire union once to avoid seam pixels.
      target.moveTo(a[0]+nx*a[2],a[1]+ny*a[2]);
      target.lineTo(a[0]-nx*a[2],a[1]-ny*a[2]);
      target.lineTo(p[0]-nx*r,p[1]-ny*r);
      target.lineTo(p[0]+nx*r,p[1]+ny*r);
      target.closePath();
    }
  } else {
    // Retain support for the earlier outline format in recording fixtures.
    const last=outline[outline.length-1],first=outline[0];
    target.moveTo((last[0]+first[0])/2,(last[1]+first[1])/2);
    for(let i=0;i<outline.length;i++) {
      const p=outline[i],next=outline[(i+1)%outline.length];
      target.quadraticCurveTo(p[0],p[1],(p[0]+next[0])/2,(p[1]+next[1])/2);
    }
    target.closePath();
  }
  target.fill('nonzero');
  target.restore();
}

function buildColorBrushSweep(stroke) {
  const centerline=getColorStrokeOutline.getPoints(stroke.samples,{
    size:stroke.size/2,
    streamline:Math.max(0,Math.min(.45,(parseFloat(streamlineSlider.value)||0)/250)),
    last:true
  });
  const sweep=[];
  const spacing=Math.max(.5,stroke.size/12);
  for(let i=0;i<centerline.length;i++) {
    const p=centerline[i];
    if(i===0) { sweep.push([p.point[0],p.point[1],stroke.size*.5*p.pressure]);continue; }
    const a=centerline[i-1];
    const distance=Math.hypot(p.point[0]-a.point[0],p.point[1]-a.point[1]);
    const steps=Math.max(1,Math.min(128,Math.ceil(distance/spacing)));
    for(let j=1;j<=steps;j++) {
      const t=j/steps,pressure=a.pressure+(p.pressure-a.pressure)*t;
      sweep.push([a.point[0]+(p.point[0]-a.point[0])*t,a.point[1]+(p.point[1]-a.point[1])*t,stroke.size*.5*pressure]);
    }
  }
  return sweep;
}

''' + text[last:]
    change('''      outline:getColorStrokeOutline(stroke.samples, {
        size:stroke.size / 2, thinning:1, smoothing:.55,
        streamline:Math.max(0, Math.min(.45, (parseFloat(streamlineSlider.value) || 0) / 250)),
        simulatePressure:false, last:true,
        start:{cap:false,taper:Math.min(stroke.size*.35, stroke.length*.2)},
        end:{cap:false,taper:finished ? Math.min(stroke.size*.4, stroke.length*.25) : 0}
      })''',
           '''      sweep:buildColorBrushSweep(stroke)''', 'solid pressure coverage')
    change('''  } else for (const p of stroke.op.outline) include(p[0],p[1]);''',
           '''  } else if (stroke.op.sweep) {
    for(const p of stroke.op.sweep) { include(p[0]-p[2],p[1]-p[2]);include(p[0]+p[2],p[1]+p[2]); }
  } else for (const p of stroke.op.outline) include(p[0],p[1]);''', 'painted bounds')
    return text


def apply_direct_color_brush(text: str) -> str:
    """Follow raw Pencil samples and keep live work independent of stroke length."""
    if '// direct-color-brush-v3' in text:
        return text

    text = replace_one(text, '<b id="colorBrushSizeValue">28</b>',
                       '<b id="colorBrushSizeValue">80</b>', 'Broader default color brush label')
    text = replace_one(text, 'id="colorBrushSize" min="2" max="100" step="1" value="28"',
                       'id="colorBrushSize" min="2" max="240" step="1" value="80"', 'Broader color brush range')
    first = text.index('function buildColorBrushSweep(stroke) {')
    last = text.index('function startStroke(e) {', first)
    text = text[:first] + r'''function beginColorBrush(e) {
  // direct-color-brush-v3
  const base=document.createElement('canvas');
  base.width=colorCanvas.width;base.height=colorCanvas.height;
  base.getContext('2d').drawImage(colorCanvas,0,0);
  const p=points[0],pressure=usingPressure ? Math.max(.005,Math.min(1,e.pressure || .005)) : 1;
  const size=Math.max(2,parseFloat(colorBrushSize.value) || 80)*getDisplayDpr();
  const sample=[p.x,p.y,size*.5*pressure];
  const op={kind:'brush',mode:'draw',color:currentColor,sweep:[sample]};
  colorBrushStroke={base,size,pressure:usingPressure,color:currentColor,op,bounds:null};
  if(detailVectorValid && activeDetailStroke) activeDetailStroke.ops=[op];
  paintColorBrushLive([sample]);
}

function includeColorBrushBounds(sample) {
  const stroke=colorBrushStroke,[x,y,r]=sample;
  if(!stroke.bounds) stroke.bounds={left:x-r,top:y-r,right:x+r,bottom:y+r};
  else {
    stroke.bounds.left=Math.min(stroke.bounds.left,x-r);stroke.bounds.top=Math.min(stroke.bounds.top,y-r);
    stroke.bounds.right=Math.max(stroke.bounds.right,x+r);stroke.bounds.bottom=Math.max(stroke.bounds.bottom,y+r);
  }
}

function paintColorBrushLive(sweep) {
  const stroke=colorBrushStroke;
  // Only the newest section is painted while moving. No delayed follow point,
  // whole-stroke geometry rebuild, or second animation frame for zoomed paint.
  for(const sample of sweep) includeColorBrushBounds(sample);
  const op={kind:'brush',mode:'draw',color:stroke.color,sweep};
  paintColorBrushShape(colorCtx,op);
  drawDetailOpLive(op);
  artworkRevision++;
}

function renderColorBrushNow() {
  const stroke=colorBrushStroke,bounds=stroke && stroke.bounds;
  if(!bounds) return;
  const x=Math.max(0,Math.floor(bounds.left)-2),y=Math.max(0,Math.floor(bounds.top)-2);
  const w=Math.min(colorCanvas.width,Math.ceil(bounds.right)+2)-x;
  const h=Math.min(colorCanvas.height,Math.ceil(bounds.bottom)+2)-y;
  if(w<=0 || h<=0) return;
  colorCtx.save();colorCtx.setTransform(1,0,0,1,0,0);
  colorCtx.globalCompositeOperation='source-over';
  colorCtx.beginPath();colorCtx.rect(x,y,w,h);colorCtx.clip();
  colorCtx.clearRect(x,y,w,h);
  colorCtx.drawImage(stroke.base,x,y,w,h,x,y,w,h);
  // On release, union the complete stroke once for consistent clean edges
  // in the native artwork, sharp zoom display, exports and recordings.
  paintColorBrushShape(colorCtx,stroke.op);
  colorCtx.restore();
}

function continueColorBrush(e) {
  const stroke=colorBrushStroke;
  if(!stroke) return;
  const p=getPos(e),sweep=stroke.op.sweep,previous=sweep[sweep.length-1];
  const distance=Math.hypot(p.x-previous[0],p.y-previous[1]);
  const pressure=stroke.pressure
    ? (e.type==='pointerup' || !(e.pressure>0) ? previous[2]/(stroke.size*.5) : Math.min(1,e.pressure)) : 1;
  const sample=[p.x,p.y,stroke.size*.5*Math.max(.005,pressure)];
  if(distance<.00001) {
    // Keep pressure changes at a stationary tip; moving samples are never
    // filtered, resampled or pulled toward an earlier position.
    if(Math.abs(sample[2]-previous[2])>.001) {
      previous[2]=sample[2];includeColorBrushBounds(previous);renderColorBrushNow();
      artworkRevision++;scheduleDetailRender();
    }
    return;
  }
  sweep.push(sample);moved=true;lastPressure=e.pressure;
  points.push(p);lastRenderedPoint={x:p.x,y:p.y};lastPenPos={x:p.x,y:p.y};
  paintColorBrushLive([previous,sample]);
}

function finishColorBrush(cancel=false) {
  const stroke=colorBrushStroke;
  if(!stroke) return;
  if(cancel) {
    stroke.op={kind:'brush',mode:'draw',color:stroke.color,sweep:[]};
    activeDetailStroke=null;
  }
  renderColorBrushNow();
  stroke.base.width=stroke.base.height=0;
  colorBrushStroke=null;
  artworkRevision++;scheduleDetailRender();
}

''' + text[last:]
    return text


def apply_oval_color_brush(text: str) -> str:
    """Use a filled tapered oval nib while always painting the newest sample."""
    if '// oval-color-brush-v4' in text:
        return text

    first = text.index('function paintColorBrushShape(target, op) {')
    last = text.index('function startStroke(e) {', first)
    text = text[:first] + r'''function colorBrushTangent(sweep,index) {
  if(sweep.length<2) return [Math.SQRT1_2,-Math.SQRT1_2];
  let before=Math.max(0,index-1),after=Math.min(sweep.length-1,index+1);
  while(before>0 && sweep[before][0]===sweep[index][0] && sweep[before][1]===sweep[index][1]) before--;
  while(after<sweep.length-1 && sweep[after][0]===sweep[index][0] && sweep[after][1]===sweep[index][1]) after++;
  const dx=sweep[after][0]-sweep[before][0],dy=sweep[after][1]-sweep[before][1];
  const distance=Math.hypot(dx,dy);
  return distance>.00001 ? [dx/distance,dy/distance] : [Math.SQRT1_2,-Math.SQRT1_2];
}

function paintColorBrushShape(target,op) {
  // solid-color-brush-v2
  // direct-color-brush-v3
  // oval-color-brush-v4
  const sweep=op.sweep,outline=op.outline;
  if(!sweep) {
    if(!outline || outline.length<3) return;
    target.save();target.globalCompositeOperation='source-over';target.globalAlpha=1;
    target.fillStyle=op.color;target.beginPath();
    const last=outline[outline.length-1],first=outline[0];
    target.moveTo((last[0]+first[0])/2,(last[1]+first[1])/2);
    for(let i=0;i<outline.length;i++) {
      const p=outline[i],next=outline[(i+1)%outline.length];
      target.quadraticCurveTo(p[0],p[1],(p[0]+next[0])/2,(p[1]+next[1])/2);
    }
    target.closePath();target.fill('nonzero');target.restore();return;
  }
  if(!sweep.length) return;
  target.save();target.globalCompositeOperation='source-over';target.globalAlpha=1;
  target.fillStyle=op.color;target.beginPath();
  for(let i=0;i<sweep.length;i++) {
    const p=sweep[i],r=Math.max(.01,p[2]);
    const tangent=colorBrushTangent(sweep,i),angle=Math.atan2(tangent[1],tangent[0]);
    // A flattened oval nib gives the stroke a slim, tapered entrance instead
    // of the large circular blob made by a monoline brush.
    const along=Math.max(.35,r*.34);
    target.moveTo(p[0]+tangent[0]*along,p[1]+tangent[1]*along);
    target.ellipse(p[0],p[1],along,r,angle,0,Math.PI*2);
    target.closePath();
    if(i===0) continue;
    const a=sweep[i-1],dx=p[0]-a[0],dy=p[1]-a[1],distance=Math.hypot(dx,dy);
    if(distance<.00001) continue;
    const nx=-dy/distance,ny=dx/distance;
    // Join every pair of ovals with a solid ribbon. Even a very fast Pencil
    // jump is filled continuously; repeated stamps can never leave gaps.
    target.moveTo(a[0]+nx*a[2],a[1]+ny*a[2]);
    target.lineTo(a[0]-nx*a[2],a[1]-ny*a[2]);
    target.lineTo(p[0]-nx*r,p[1]-ny*r);
    target.lineTo(p[0]+nx*r,p[1]+ny*r);
    target.closePath();
  }
  target.fill('nonzero');target.restore();
}

function colorBrushSmoothstep(value) {
  const t=Math.max(0,Math.min(1,value));
  return t*t*(3-2*t);
}

function beginColorBrush(e) {
  const base=document.createElement('canvas');
  base.width=colorCanvas.width;base.height=colorCanvas.height;
  base.getContext('2d').drawImage(colorCanvas,0,0);
  const p=points[0],pressure=usingPressure ? Math.max(.005,Math.min(1,e.pressure || .005)) : 1;
  const size=Math.max(2,parseFloat(colorBrushSize.value) || 80)*getDisplayDpr();
  const tipRadius=Math.max(.65*getDisplayDpr(),size*.04);
  const targetRadius=Math.max(tipRadius,size*.5*pressure);
  const sample=[p.x,p.y,tipRadius,targetRadius,0];
  const op={kind:'brush',mode:'draw',color:currentColor,sweep:[sample]};
  colorBrushStroke={base,size,tipRadius,pressure:usingPressure,color:currentColor,op,bounds:null,length:0};
  if(detailVectorValid && activeDetailStroke) activeDetailStroke.ops=[op];
  paintColorBrushLive([sample]);
}

function includeColorBrushBounds(sample) {
  const stroke=colorBrushStroke,[x,y,r]=sample;
  if(!stroke.bounds) stroke.bounds={left:x-r,top:y-r,right:x+r,bottom:y+r};
  else {
    stroke.bounds.left=Math.min(stroke.bounds.left,x-r);stroke.bounds.top=Math.min(stroke.bounds.top,y-r);
    stroke.bounds.right=Math.max(stroke.bounds.right,x+r);stroke.bounds.bottom=Math.max(stroke.bounds.bottom,y+r);
  }
}

function paintColorBrushLive(sweep) {
  const stroke=colorBrushStroke;
  for(const sample of sweep) includeColorBrushBounds(sample);
  const op={kind:'brush',mode:'draw',color:stroke.color,sweep};
  // Draw the newest Pencil section synchronously on both native and zoomed
  // canvases. There is no smoothing follower or animation-frame queue.
  paintColorBrushShape(colorCtx,op);drawDetailOpLive(op);artworkRevision++;
}

function renderColorBrushNow() {
  const stroke=colorBrushStroke,bounds=stroke && stroke.bounds;
  if(!bounds) return;
  const x=Math.max(0,Math.floor(bounds.left)-2),y=Math.max(0,Math.floor(bounds.top)-2);
  const w=Math.min(colorCanvas.width,Math.ceil(bounds.right)+2)-x;
  const h=Math.min(colorCanvas.height,Math.ceil(bounds.bottom)+2)-y;
  if(w<=0 || h<=0) return;
  colorCtx.save();colorCtx.setTransform(1,0,0,1,0,0);
  colorCtx.globalCompositeOperation='source-over';
  colorCtx.beginPath();colorCtx.rect(x,y,w,h);colorCtx.clip();
  colorCtx.clearRect(x,y,w,h);colorCtx.drawImage(stroke.base,x,y,w,h,x,y,w,h);
  paintColorBrushShape(colorCtx,stroke.op);colorCtx.restore();
}

function continueColorBrush(e) {
  const stroke=colorBrushStroke;
  if(!stroke) return;
  const p=getPos(e),sweep=stroke.op.sweep,previous=sweep[sweep.length-1];
  const distance=Math.hypot(p.x-previous[0],p.y-previous[1]);
  const pressure=stroke.pressure ? Math.max(.005,Math.min(1,e.pressure || .005)) : 1;
  const targetRadius=Math.max(stroke.tipRadius,stroke.size*.5*pressure);
  if(distance<.00001) {
    if(Math.abs(targetRadius-previous[3])>.001 && sweep.length>1) {
      previous[3]=targetRadius;
      const ramp=colorBrushSmoothstep(previous[4]/Math.max(4,stroke.size*.3));
      previous[2]=stroke.tipRadius+(targetRadius-stroke.tipRadius)*ramp;
      includeColorBrushBounds(previous);renderColorBrushNow();
      artworkRevision++;scheduleDetailRender();
    }
    return;
  }
  stroke.length+=distance;
  const ramp=colorBrushSmoothstep(stroke.length/Math.max(4,stroke.size*.3));
  const radius=stroke.tipRadius+(targetRadius-stroke.tipRadius)*ramp;
  const sample=[p.x,p.y,radius,targetRadius,stroke.length];
  sweep.push(sample);moved=true;lastPressure=e.pressure;
  points.push(p);lastRenderedPoint={x:p.x,y:p.y};lastPenPos={x:p.x,y:p.y};
  paintColorBrushLive([previous,sample]);
}

function taperColorBrushEnd(stroke) {
  const sweep=stroke.op.sweep;
  if(sweep.length<2) return;
  let travelled=0;
  const taperLength=Math.max(5*getDisplayDpr(),stroke.size*.42);
  for(let i=sweep.length-1;i>=0;i--) {
    if(i<sweep.length-1) travelled+=Math.hypot(sweep[i+1][0]-sweep[i][0],sweep[i+1][1]-sweep[i][1]);
    const mix=colorBrushSmoothstep(travelled/taperLength);
    const target=sweep[i][3] === undefined ? sweep[i][2] : sweep[i][3];
    sweep[i][2]=stroke.tipRadius+(target-stroke.tipRadius)*mix;
    if(mix>=1) break;
  }
}

function finishColorBrush(cancel=false) {
  const stroke=colorBrushStroke;
  if(!stroke) return;
  if(cancel) {
    stroke.op={kind:'brush',mode:'draw',color:stroke.color,sweep:[]};activeDetailStroke=null;
  } else {
    taperColorBrushEnd(stroke);
    if(detailVectorValid && activeDetailStroke) activeDetailStroke.ops=[stroke.op];
  }
  renderColorBrushNow();stroke.base.width=stroke.base.height=0;
  colorBrushStroke=null;artworkRevision++;scheduleDetailRender();
}

''' + text[last:]

    helper = r'''function continueStrokeWithLatestPointer(e) {
  const samples=(mode==='erase' || colorBrushStroke) && typeof e.getCoalescedEvents==='function'
    ? e.getCoalescedEvents() : null;
  if(samples && samples.length) for(const sample of samples) continueStroke(sample);
  // getCoalescedEvents may contain only the older positions. Always process
  // the dispatch event too so the paint reaches the current Pencil tip now.
  continueStroke(e);
}

'''
    text = replace_one(text, 'const activePointers = new Map();',
                       helper + 'const activePointers = new Map();', 'Latest Pencil sample helper')
    old = """    const samples = (mode === 'erase' || colorBrushStroke) && typeof e.getCoalescedEvents === 'function' ? e.getCoalescedEvents() : null;
    if (samples && samples.length) for (const sample of samples) continueStroke(sample);
    else continueStroke(e);"""
    text = replace_one(text, old, '    continueStrokeWithLatestPointer(e);', 'Latest Pencil position')
    text = text.replace('Light pressure makes a fine tip; press harder for broad, smooth color beneath your ink lines.',
                        'A tapered oval brush that follows your Pencil directly; press harder for broader color beneath your ink lines.')
    return text


# Vanya prefers an unobstructed tip while erasing. The pointer handlers can set
# inline display values, so keep the outline hidden for every input device.
eraser_cursor_style = '<style id="eraserCursorVisibility">#eraserCursor{display:none!important}</style>'
if eraser_cursor_style not in s:
    s = replace_one(s, '</head>', eraser_cursor_style + '</head>', 'Hide eraser cursor')
    PATH.write_text(s)

native_retina_hooks = [
    "detailCanvas.id = 'detailCanvas'",
    'const DETAIL_ZOOM_THRESHOLD = 1.12;',
    'recordDetailSegment(',
    "drawCanvas.style.opacity = '0';",
]
if MARKER in s:
    PATH.write_text(apply_paper_multiply(apply_oval_color_brush(apply_direct_color_brush(apply_solid_color_brush(apply_color_pressure_brush(apply_precise_eraser(apply_color_layer(s))))))))
    print('Standalone defaults checked; retina layer already present.')
    raise SystemExit(0)
if all(item in s for item in native_retina_hooks):
    anchor = "detailCanvas.id = 'detailCanvas';"
    s = s.replace(anchor, "// " + MARKER + "\n" + anchor, 1)
    PATH.write_text(s)
    PATH.write_text(apply_paper_multiply(apply_oval_color_brush(apply_direct_color_brush(apply_solid_color_brush(apply_color_pressure_brush(apply_precise_eraser(apply_color_layer(s))))))))
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
PATH.write_text(apply_paper_multiply(apply_oval_color_brush(apply_direct_color_brush(apply_solid_color_brush(apply_color_pressure_brush(apply_precise_eraser(apply_color_layer(s))))))))
