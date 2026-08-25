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

console.log('1/3 Applying current video/UI test to v8...');
const transformedV8 = await executeWrapper(localFiles['hand-selector-v7-test.html'], 'v7-wrapper');

console.log('2/3 Applying layer test to v6...');
const transformedV6 = await executeWrapper(transformedV8, 'v8-wrapper');

console.log('3/3 Building final Ink Sketchbook HTML...');
const finalHtml = await executeWrapper(transformedV6, 'v6-wrapper');

const required = [
  'id="videoBgInput"',
  'id="guideCanvas"',
  'id="guideFileInput"',
  'id="recordReferenceBtn"',
  'id="floatingSettingsStyle"',
  'id="refSizeSlider" min="25" max="500"',
  'id="guideSizeSlider" min="10" max="500"',
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
