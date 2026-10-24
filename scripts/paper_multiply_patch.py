"""Add optional still-paper blending to the standalone page, idempotently."""


def apply_paper_multiply(text: str) -> str:
    if 'paper-multiply-v1' in text:
        return text

    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise SystemExit('Paper Multiply anchor missing or ambiguous: ' + old[:80])
        text = text.replace(old, new, 1)

    change('  #refCanvas { z-index: 1; }', '''  #refCanvas { z-index: 1; }
  /* paper-multiply-v1: isolate blending from surrounding interface. */
  .canvas-wrap { isolation: isolate; }
  .canvas-wrap.paper-multiply #refDomLayer,
  .canvas-wrap.paper-multiply #refCanvas {
    z-index: 7; mix-blend-mode: multiply; pointer-events: none;
  }
''')
    change('      <div class="slider-group"><span>Background opacity</span>', '''      <label class="slider-group" style="flex-direction:row;align-items:center;">
        <input type="checkbox" id="paperMultiplyToggle"> Multiply paper texture
      </label>
      <div class="slider-group">
        <label for="paperMultiplyStrength">Texture strength <output id="paperMultiplyValue">100%</output></label>
        <input type="range" id="paperMultiplyStrength" min="0" max="100" value="100" disabled>
      </div>
      <div class="slider-group"><span>Background opacity</span>''')
    change('let refImage = null;', '''const paperMultiplyToggle = document.getElementById('paperMultiplyToggle');
const paperMultiplyStrength = document.getElementById('paperMultiplyStrength');
const paperMultiplyValue = document.getElementById('paperMultiplyValue');
function paperMultiplyActive() {
  return paperMultiplyToggle.checked && !!refImage && !backgroundVideoReady;
}
function paperMultiplyAlpha() {
  return paperMultiplyActive() ? Number(paperMultiplyStrength.value) / 100 : 1;
}
function syncPaperMultiplyDisplay() {
  wrap.classList.toggle('paper-multiply', paperMultiplyActive());
  paperMultiplyStrength.disabled = !paperMultiplyToggle.checked;
  paperMultiplyValue.value = paperMultiplyStrength.value + '%';
}
paperMultiplyToggle.addEventListener('change', drawRef);
paperMultiplyStrength.addEventListener('input', drawRef);

// Share the same image placement and crop as the native-quality background.
// Keep this above the artwork but below the recorded illustrated hand.
function paintPaperMultiply(target, source) {
  if (!paperMultiplyActive() || !refVisible) return;
  const iw = refImage.naturalWidth || refImage.width;
  const ih = refImage.naturalHeight || refImage.height;
  const cw = refCanvas.width, ch = refCanvas.height;
  if (!iw || !ih || !cw || !ch) return;
  const scale = Math.min(Math.min(cw / iw, ch / ih) * .9, 1)
    * (Number(refSizeSlider.value) || 100) / 100;
  const w = iw * scale, h = ih * scale;
  const rx = cw / drawCanvas.width, ry = ch / drawCanvas.height;
  const sx = target.canvas.width / (source.width * rx);
  const sy = target.canvas.height / (source.height * ry);
  target.save();
  target.globalCompositeOperation = 'multiply';
  target.globalAlpha = Number(opacitySlider.value) / 100 * paperMultiplyAlpha();
  target.imageSmoothingEnabled = true;
  target.imageSmoothingQuality = 'high';
  target.setTransform(sx, 0, 0, sy, -source.x * rx * sx, -source.y * ry * sy);
  target.beginPath(); target.rect(0, 0, cw, ch); target.clip();
  target.drawImage(refImage, (cw - w) / 2, (ch - h) / 2, w, h);
  target.restore();
}
function paperArtworkRect() {
  return {x:0, y:0, width:drawCanvas.width, height:drawCanvas.height};
}

let refImage = null;''')
    change('function drawRef() {', 'function drawRef() {\n  syncPaperMultiplyDisplay();')
    change("refDomImage.style.opacity = String(Math.max(0, Math.min(1, (parseFloat(opacitySlider.value) || 100) / 100)));",
           "refDomImage.style.opacity = String(Number(opacitySlider.value) / 100 * paperMultiplyAlpha());")
    change('  refCtx.globalAlpha = opacitySlider.value / 100;',
           '  refCtx.globalAlpha = opacitySlider.value / 100 * paperMultiplyAlpha();')
    change('if (recordReferenceInVideo && refVisible && (refImage || backgroundVideoReady)) {',
           'if (recordReferenceInVideo && refVisible && (refImage || backgroundVideoReady) && !paperMultiplyActive()) {')
    change('  const recordScaleX = recordCanvas.width / source.width;',
           '  if (recordReferenceInVideo) paintPaperMultiply(recordCtx, source);\n  const recordScaleX = recordCanvas.width / source.width;')
    change("  const target = artwork.getContext('2d');\n  target.drawImage(colorCanvas, 0, 0);", """  const target = artwork.getContext('2d');
  if (paperMultiplyActive() && refVisible) {
    target.fillStyle = paperColorPicker.value || '#ffffff';
    target.fillRect(0, 0, artwork.width, artwork.height);
  }
  target.drawImage(colorCanvas, 0, 0);"""
    )
    change('  target.drawImage(drawCanvas, 0, 0);\n  return artwork;',
           '  target.drawImage(drawCanvas, 0, 0);\n  paintPaperMultiply(target, paperArtworkRect());\n  return artwork;')
    change('  fctx.drawImage(drawCanvas, 0, 0);\n  return flat;',
           '  fctx.drawImage(drawCanvas, 0, 0);\n  paintPaperMultiply(fctx, paperArtworkRect());\n  return flat;')
    return text
