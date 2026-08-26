import fs from 'node:fs/promises';
import vm from 'node:vm';

// Generated test pages are compiled here so Safari never has to run the wrapper chain itself.
const readLocal = (name) => fs.readFile(new URL('../' + name, import.meta.url), 'utf8');

const localFiles = {
  'hand-selector-v6-test.html': await readLocal('hand-selector-v6-test.html'),
  'hand-selector-v8-layers-test.html': await readLocal('hand-selector-v8-layers-test.html'),
  'hand-selector-v7-test.html': await readLocal('hand-selector-v7-test.html'),
};

function extractWrapperScript(html) {
  const start = html.indexOf('<script>');
  const end = html.lastIndexOf('</script>');
  if (start < 0 || end < start) throw new Error('Wrapper script not found');
  return html.slice(start + '<script>'.length, end);
}

class NodeFileReader {
  constructor() {
    this.result = null;
    this.onload = null;
    this.onerror = null;
  }
  readAsDataURL(blob) {
    blob.arrayBuffer().then((buffer) => {
      const type = blob.type || 'application/octet-stream';
      this.result = `data:${type};base64,${Buffer.from(buffer).toString('base64')}`;
      if (this.onload) this.onload({ target: this });
    }).catch((error) => {
      if (this.onerror) this.onerror(error);
    });
  }
}

function localResponse(text, contentType = 'text/html') {
  return new Response(text, {
    status: 200,
    headers: { 'content-type': contentType },
  });
}

function localNameFromUrl(input) {
  const raw = String(input);
  let pathname;
  try { pathname = new URL(raw).pathname; } catch { pathname = raw; }
  const name = pathname.split('/').pop();
  return name || '';
}

async function buildFetch(input, init) {
  const name = localNameFromUrl(input);
  if (localFiles[name]) return localResponse(localFiles[name]);
  const response = await fetch(input, init);
  if (!response.ok) throw new Error(`Build fetch failed ${response.status}: ${input}`);
  return response;
}

async function executeWrapper(wrapperHtml, label) {
  const script = extractWrapperScript(wrapperHtml);
  let written = '';
  const document = {
    body: { innerHTML: '' },
    open() {},
    write(value) { written = String(value); },
    close() {},
  };

  const sandbox = {
    console,
    document,
    fetch: buildFetch,
    FileReader: NodeFileReader,
    Response,
    Blob,
    URL,
    Buffer,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    queueMicrotask,
    TextEncoder,
    TextDecoder,
    atob: (value) => Buffer.from(value, 'base64').toString('binary'),
    btoa: (value) => Buffer.from(value, 'binary').toString('base64'),
  };
  sandbox.globalThis = sandbox;
  sandbox.window = sandbox;

  const result = vm.runInNewContext(script, sandbox, { filename: label });
  if (result && typeof result.then === 'function') await result;
  if (!written) {
    const message = document.body.innerHTML || 'wrapper produced no document';
    throw new Error(`${label}: ${message}`);
  }
  return written;
}

// v7's first 500% experiment changed v8's lookup key before v8 had created the
// control. Keep the original 300% lookup during assembly; we expand the finished
// HTML control immediately afterward instead.
let v7ForBuild = localFiles['hand-selector-v7-test.html'];
const eager500 = `'const refSizeControl=\\'<div class="slider-group"><span>Background size</span> <input type="range" id="refSizeSlider" min="25" max="500" value="100"></div>\\';'`;
const safe300 = `'const refSizeControl=\\'<div class="slider-group"><span>Background size</span> <input type="range" id="refSizeSlider" min="25" max="300" value="100"></div>\\';'`;
if (!v7ForBuild.includes(eager500)) throw new Error('Expected v7 background-size patch was not found');
v7ForBuild = v7ForBuild.replace(eager500, safe300);

console.log('1/3 Applying current video/UI test to v8...');
let transformedV8 = await executeWrapper(v7ForBuild, 'v7-wrapper');

const placementHook = '    html=html.replace(refSizeControl,refSizeControl+videoControls+guideControls);';
if (!transformedV8.includes(placementHook)) throw new Error('Background control placement hook not found after v7 transform');
transformedV8 = transformedV8.replace(
  placementHook,
  placementHook + "\n    html=html.replace('id=\"refSizeSlider\" min=\"25\" max=\"300\"', 'id=\"refSizeSlider\" min=\"25\" max=\"500\"');"
);

console.log('2/3 Applying layer test to v6...');
const transformedV6 = await executeWrapper(transformedV8, 'v8-wrapper');

console.log('3/3 Building final Ink Sketchbook HTML...');
let finalHtml = await executeWrapper(transformedV6, 'v6-wrapper');

function replaceFinal(needle, replacement, label) {
  if (!finalHtml.includes(needle)) throw new Error(`Final quality patch failed: ${label}`);
  finalHtml = finalHtml.replace(needle, replacement);
}

// ---------------------------------------------------------------------------
// High-quality video background + social-ready recording output.
// ---------------------------------------------------------------------------

// Show the creator the native source resolution/format/estimated bitrate so a
// soft source file can be spotted before recording.
const videoStatusMarkup = '<div id="videoBgStatus" style="font-size:11px;color:#8a8373;text-align:center;">No video selected</div>';
replaceFinal(
  videoStatusMarkup,
  videoStatusMarkup + '<div id="videoBgQuality" style="font-size:11px;line-height:1.35;color:#8a8373;text-align:center;"></div>',
  'video source quality UI'
);
replaceFinal(
  "const videoBgStatus = document.getElementById('videoBgStatus');",
  "const videoBgStatus = document.getElementById('videoBgStatus');\nconst videoBgQuality = document.getElementById('videoBgQuality');",
  'video source quality DOM reference'
);
replaceFinal(
  'let backgroundVideoLoadToken = 0;',
  'let backgroundVideoLoadToken = 0;\nlet backgroundVideoFile = null;',
  'video source file state'
);

const videoQualityHelpers = [
  "function backgroundVideoFormatLabel(file) {",
  "  if (!file) return 'Video';",
  "  const mime = (file.type || '').toLowerCase();",
  "  if (mime.includes('mp4')) return 'MP4';",
  "  if (mime.includes('quicktime')) return 'MOV';",
  "  if (mime.includes('webm')) return 'WebM';",
  "  const name = file.name || '';",
  "  const ext = name.includes('.') ? name.split('.').pop().toUpperCase() : '';",
  "  return ext || 'Video';",
  "}",
  "function updateBackgroundVideoQualityInfo() {",
  "  if (!videoBgQuality || !backgroundVideo.videoWidth || !backgroundVideo.videoHeight) return;",
  "  const w = backgroundVideo.videoWidth;",
  "  const h = backgroundVideo.videoHeight;",
  "  const duration = Number.isFinite(backgroundVideo.duration) ? backgroundVideo.duration : 0;",
  "  const mbps = backgroundVideoFile && duration > 0 ? (backgroundVideoFile.size * 8 / duration / 1000000) : 0;",
  "  const format = backgroundVideoFormatLabel(backgroundVideoFile);",
  "  const socialReady = Math.min(w, h) >= 1080;",
  "  videoBgQuality.textContent = (socialReady ? '✓ ' : '⚠ ') + format + ' · ' + w + '×' + h + (mbps > 0 ? ' · ~' + mbps.toFixed(1) + ' Mbps' : '') + (socialReady ? ' · Social-HD source' : ' · below 1080px short side — may look soft');",
  "  videoBgQuality.style.color = socialReady ? '#5d7459' : '#9a6239';",
  "}"
].join('\n');
replaceFinal(
  "videoBgInput.addEventListener('change', async () => { const file = videoBgInput.files && videoBgInput.files[0]; if (!file) return;",
  videoQualityHelpers + "\nvideoBgInput.addEventListener('change', async () => { const file = videoBgInput.files && videoBgInput.files[0]; if (!file) return; backgroundVideoFile = file;",
  'video source quality helper injection'
);
replaceFinal(
  "backgroundVideo.addEventListener('loadedmetadata', () => { setVideoStatus('Preparing first frame…'); updateVideoControls();",
  "backgroundVideo.addEventListener('loadedmetadata', () => { setVideoStatus('Preparing first frame…'); updateBackgroundVideoQualityInfo(); updateVideoControls();",
  'video source metadata quality check'
);
replaceFinal(
  "videoBgInput.value = ''; videoBgPlayback.style.display = 'none';",
  "videoBgInput.value = ''; backgroundVideoFile = null; if (videoBgQuality) videoBgQuality.textContent = ''; videoBgPlayback.style.display = 'none';",
  'video source quality reset'
);

// The still-photo reference already increases its backing resolution when the
// creator zooms in. Apply the same logic to video so a 4K source remains crisp
// while tracing instead of magnifying a 3000px intermediate canvas forever.
replaceFinal(
  "function updateRefResolutionForZoom() {\n  if (!refImage) return;",
  "function updateRefResolutionForZoom() {\n  const activeSourceLong = backgroundVideoReady ? Math.max(backgroundVideo.videoWidth || 0, backgroundVideo.videoHeight || 0) : (refImage ? Math.max(refImage.width, refImage.height) : 0);\n  if (!activeSourceLong) return;",
  'video-aware zoom resolution'
);
replaceFinal(
  '  const targetLong = Math.min(baseLong * view.scale, Math.max(refImage.width, refImage.height));',
  '  const targetLong = Math.min(baseLong * view.scale, activeSourceLong);',
  'video-aware zoom target'
);
replaceFinal(
  "function markVideoReady() { if (!backgroundVideo.videoWidth || !backgroundVideo.videoHeight) return; backgroundVideoReady = true; setVideoStatus('Video ready'); drawRef(); updateVideoControls(); }",
  "function markVideoReady() { if (!backgroundVideo.videoWidth || !backgroundVideo.videoHeight) return; backgroundVideoReady = true; lastRefResUpdate = 0; updateRefResolutionForZoom(); setVideoStatus('Video ready'); drawRef(); updateBackgroundVideoQualityInfo(); updateVideoControls(); }",
  'video ready high-resolution refresh'
);

// Do not record the already-rasterized refCanvas. Draw the original decoded
// image/video frame directly into the recording canvas using the same placement,
// fade and crop mapping. This removes one full resampling pass from the output.
const oldRecordingBackground = [
  '  if (recordReferenceInVideo && refVisible && (refImage || backgroundVideoReady)) {',
  '    const refScaleX = refCanvas.width / drawCanvas.width;',
  '    const refScaleY = refCanvas.height / drawCanvas.height;',
  '    recordCtx.drawImage(',
  '      refCanvas,',
  '      source.x * refScaleX, source.y * refScaleY,',
  '      source.width * refScaleX, source.height * refScaleY,',
  '      0, 0, recordCanvas.width, recordCanvas.height',
  '    );',
  '  }'
].join('\n');
const directRecordingBackground = [
  '  if (recordReferenceInVideo && refVisible && (refImage || backgroundVideoReady)) {',
  '    const activeRecordingRef = backgroundVideoReady ? backgroundVideo : refImage;',
  '    const iw = backgroundVideoReady ? backgroundVideo.videoWidth : refImage.width;',
  '    const ih = backgroundVideoReady ? backgroundVideo.videoHeight : refImage.height;',
  '    if (activeRecordingRef && iw > 0 && ih > 0) {',
  '      const cw = refCanvas.width, ch = refCanvas.height;',
  '      const fitScale = Math.min(cw / iw, ch / ih) * 0.9;',
  '      const autoScale = Math.min(fitScale, 1);',
  '      const userScale = (parseFloat(refSizeSlider.value) || 100) / 100;',
  '      const refDrawScale = autoScale * userScale;',
  '      const refW = iw * refDrawScale, refH = ih * refDrawScale;',
  '      const refX = (cw - refW) / 2, refY = (ch - refH) / 2;',
  '      const refScaleX = refCanvas.width / drawCanvas.width;',
  '      const refScaleY = refCanvas.height / drawCanvas.height;',
  '      const cropX = source.x * refScaleX, cropY = source.y * refScaleY;',
  '      const cropW = source.width * refScaleX, cropH = source.height * refScaleY;',
  '      const mapX = recordCanvas.width / Math.max(1, cropW);',
  '      const mapY = recordCanvas.height / Math.max(1, cropH);',
  '      recordCtx.save();',
  '      recordCtx.globalAlpha = Math.max(0, Math.min(1, (parseFloat(opacitySlider.value) || 100) / 100));',
  '      recordCtx.imageSmoothingEnabled = true;',
  "      recordCtx.imageSmoothingQuality = 'high';",
  '      recordCtx.setTransform(mapX, 0, 0, mapY, -cropX * mapX, -cropY * mapY);',
  '      try { recordCtx.drawImage(activeRecordingRef, refX, refY, refW, refH); } catch (_) {}',
  '      recordCtx.restore();',
  '    }',
  '  }'
].join('\n');
replaceFinal(oldRecordingBackground, directRecordingBackground, 'direct native background recording');

// Social media target: never intentionally save the phone copy at 720×1280.
// Keep iPad/tablet output slightly above 1080×1920, allow moderate upscaling if
// the creator is zoomed in, and use even dimensions for H.264 compatibility.
const oldRecordSize = [
  '  const recordMaxLongSide = isPhoneRecording ? 1280 : 2160;',
  '  const recordVideoScale = Math.min(1, recordMaxLongSide / Math.max(recordSourceRect.width, recordSourceRect.height));',
  '  recordCanvas.width = Math.max(2, Math.round(recordSourceRect.width * recordVideoScale));',
  '  recordCanvas.height = Math.max(2, Math.round(recordSourceRect.height * recordVideoScale));'
].join('\n');
const socialRecordSize = [
  '  const recordTargetLongSide = isPhoneRecording ? 1920 : 2160;',
  '  const sourceLongSide = Math.max(recordSourceRect.width, recordSourceRect.height);',
  '  const recordVideoScale = Math.min(2, recordTargetLongSide / Math.max(1, sourceLongSide));',
  '  const evenRecordSize = (value) => Math.max(2, Math.round(value / 2) * 2);',
  '  recordCanvas.width = evenRecordSize(recordSourceRect.width * recordVideoScale);',
  '  recordCanvas.height = evenRecordSize(recordSourceRect.height * recordVideoScale);'
].join('\n');
replaceFinal(oldRecordSize, socialRecordSize, 'social recording dimensions');

if (!finalHtml.includes('recordCanvas.captureStream(24)')) throw new Error('Final quality patch failed: 24fps capture stream not found');
finalHtml = finalHtml.replaceAll('recordCanvas.captureStream(24)', 'recordCanvas.captureStream(30)');
replaceFinal(
  'videoBitsPerSecond: isPhoneRecording ? 6000000 : 14000000, audioBitsPerSecond: 256000',
  'videoBitsPerSecond: isPhoneRecording ? 12000000 : 20000000, audioBitsPerSecond: 256000',
  'high recording bitrate'
);

const required = [
  'id="videoBgInput"',
  'id="videoBgQuality"',
  'id="guideCanvas"',
  'id="guideFileInput"',
  'id="recordReferenceBtn"',
  'id="floatingSettingsStyle"',
  'id="refSizeSlider" min="25" max="500"',
  'id="guideSizeSlider" min="10" max="500"',
  'const recordTargetLongSide = isPhoneRecording ? 1920 : 2160;',
  'recordCanvas.captureStream(30)',
  'videoBitsPerSecond: isPhoneRecording ? 12000000 : 20000000',
  'const activeRecordingRef = backgroundVideoReady ? backgroundVideo : refImage;',
  'Social-HD source',
];
for (const needle of required) {
  if (!finalHtml.includes(needle)) throw new Error(`Standalone validation failed: missing ${needle}`);
}

for (const match of finalHtml.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)) {
  const attrs = match[1] || '';
  const code = match[2] || '';
  if (/type\s*=\s*["'](?:application\/json|importmap)["']/i.test(attrs)) continue;
  try { new Function(code); }
  catch (error) { throw new Error(`Generated inline JavaScript does not parse: ${error.message}`); }
}

const banner = '<!-- GENERATED standalone test: no runtime wrapper chain. Do not hand-edit; rebuild from v7/v8/v6. -->\n';
const outputPath = new URL('../hand-selector-standalone-test.html', import.meta.url);
await fs.writeFile(outputPath, banner + finalHtml, 'utf8');
console.log(`Standalone page written: ${outputPath.pathname}`);
