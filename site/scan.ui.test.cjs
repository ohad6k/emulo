/**
 * DOM tests for scan.html.
 *
 * scan.test.cjs runs the #scan-core sandbox and only *parse-checks* the UI script. That is why
 * eight of eight tests passed on a page whose largest button did nothing: the capability check
 * ran at load, set the hidden attribute, and `.button` setting display beat the UA stylesheet's
 * [hidden] rule, so the control stayed on screen with no listener attached. Nothing in that file
 * could see it. Ohad clicked it an hour after the page shipped.
 *
 * These tests execute the page for real, so a dead control is a failing test.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
/**
 * jsdom is the one dependency this repository has outside Python, and it exists only for these
 * tests. Someone who clones the repo to use Emulo should not be forced to run npm install, so a
 * missing jsdom skips these rather than exploding.
 *
 * In CI it is a hard failure instead. A silent skip is exactly how the dead button shipped past
 * a green suite, and a guard that can quietly disable itself is not a guard.
 */
let JSDOM = null;
try {
  ({ JSDOM } = require('jsdom'));
} catch (err) {
  if (process.env.CI) {
    throw new Error('jsdom is not installed and this is CI. Run `npm ci`. Skipping the page '
      + 'tests here would hide exactly the class of defect they exist to catch.');
  }
}
const needsJsdom = JSDOM ? false : 'jsdom is not installed: run `npm install` to run the page tests';

const pagePath = path.join(__dirname, 'scan.html');
const html = fs.readFileSync(pagePath, 'utf8');

/**
 * Load the page with its scripts running.
 *
 * `directoryPicker` decides which browser we are pretending to be. jsdom has no File System
 * Access API of its own, so the default is exactly Ohad's case: the fallback branch.
 */
function loadPage({ directoryPicker = null, userAgent = null } = {}) {
  const listeners = [];
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    url: 'https://emulo.vercel.app/scan',
    beforeParse(window) {
      // Record every registration so a control with no handler is detectable, rather than
      // relying on knowing in advance which control broke.
      const real = window.EventTarget.prototype.addEventListener;
      window.EventTarget.prototype.addEventListener = function (type, fn, opts) {
        listeners.push({ target: this, type });
        return real.call(this, type, fn, opts);
      };
      if (directoryPicker) window.showDirectoryPicker = directoryPicker;
      if (userAgent) Object.defineProperty(window.navigator, 'userAgent',
        { value: userAgent, configurable: true });
    },
  });
  const { window } = dom;
  const has = (el, type) => listeners.some((l) => l.target === el && l.type === type);
  return { dom, window, document: window.document, listeners, has };
}

const click = (window, el) =>
  el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));

// -- the regression ---------------------------------------------------------

test('the primary folder button works on a browser with no File System Access API', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  assert.equal('showDirectoryPicker' in window, false, 'this is the browser Ohad was using');

  const button = document.getElementById('picker-button');
  const input = document.getElementById('folder-input');
  let opened = 0;
  input.click = () => { opened += 1; };

  click(window, button);
  assert.equal(opened, 1, 'clicking the page\'s primary control must open a folder picker');
});

test('the primary folder button is not hidden away on that browser', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  const button = document.getElementById('picker-button');
  assert.equal(button.hidden, false,
    'hiding it was the old fix, and CSS defeated it. It must work instead of disappear.');
});

test('the primary folder button uses the native picker when the browser has one', { skip: needsJsdom }, async () => {
  let native = 0;
  const picker = async () => {
    native += 1;
    const abort = new Error('user dismissed');
    abort.name = 'AbortError';
    throw abort;
  };
  const { window, document } = loadPage({ directoryPicker: picker });
  const input = document.getElementById('folder-input');
  let fallback = 0;
  input.click = () => { fallback += 1; };

  click(window, document.getElementById('picker-button'));
  await new Promise((r) => setTimeout(r, 20));

  assert.equal(native, 1, 'a browser with the API must get the real directory picker');
  assert.equal(fallback, 0, 'and must not also open the file input');
});

test('dismissing the native picker is silent, not an error screen', { skip: needsJsdom }, async () => {
  const picker = async () => { const e = new Error('x'); e.name = 'AbortError'; throw e; };
  const { window, document } = loadPage({ directoryPicker: picker });
  click(window, document.getElementById('picker-button'));
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(document.getElementById('error-state').classList.contains('active'), false,
    'changing your mind about a folder is not a failure');
});

test('a native picker that genuinely fails shows the error state', { skip: needsJsdom }, async () => {
  const picker = async () => { throw new Error('permission denied'); };
  const { window, document } = loadPage({ directoryPicker: picker });
  click(window, document.getElementById('picker-button'));
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(document.getElementById('error-state').classList.contains('active'), true);
});

// -- the general guard, which does not need to know what broke --------------

test('no control the page renders is left unwired', { skip: needsJsdom }, () => {
  const { document, has } = loadPage();
  const dead = [];
  for (const el of document.querySelectorAll('button, .button')) {
    const inLabel = el.closest('label') !== null;      // a label drives its own input
    if (!has(el, 'click') && !inLabel) dead.push(el.id || el.className);
  }
  assert.deepEqual(dead, [],
    'every clickable control must do something. This is the test that would have caught the '
    + 'folder button without anyone knowing it was broken.');
});

test('the fallback control still drives the file input', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  const span = document.getElementById('fallback-button');
  assert.ok(span.closest('label'), 'the secondary button is a label wrapping the real input');
  assert.equal(span.closest('label').querySelector('input[type=file]').id, 'folder-input');
});

// -- the promise the page makes ---------------------------------------------

test('the loaded page issues no network request', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  for (const el of document.querySelectorAll('[src], link[href], form[action]')) {
    const url = el.getAttribute('src') || el.getAttribute('href') || el.getAttribute('action');
    assert.doesNotMatch(url || '', /^https?:/i, `${el.tagName} reaches off the machine: ${url}`);
  }
});

test('the reset controls return the page to the choose state', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  document.getElementById('result-state').classList.add('active');
  click(window, document.getElementById('reset-button'));
  assert.equal(document.getElementById('choose-state').classList.contains('active'), true);
});

test('hidden means hidden even on an element whose class sets display', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  const probe = document.createElement('div');
  probe.className = 'button';
  probe.hidden = true;
  document.body.appendChild(probe);
  assert.equal(window.getComputedStyle(probe).display, 'none',
    'without the [hidden] !important rule, .button display:inline-flex wins');
});

// -- finding the folder, which is the real first obstacle -------------------

test('only one folder control is offered when both would do the same thing', { skip: needsJsdom }, () => {
  const { document } = loadPage();                    // no native picker: Ohad's browser
  assert.equal(document.getElementById('fallback-label').hidden, true,
    'without a native picker both buttons open the same dialog, so showing both is noise');
  assert.equal(document.getElementById('picker-button').hidden, false,
    'and the one that stays must be the one that works');
});

test('both controls remain when the browser has a native picker', { skip: needsJsdom }, () => {
  const { document } = loadPage({ directoryPicker: async () => { throw new Error('x'); } });
  assert.equal(document.getElementById('fallback-label').hidden, false,
    'the file input is the fallback for when the native picker fails, so it stays');
});

test('the path shown matches the platform', { skip: needsJsdom }, () => {
  const WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)';
  const MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)';

  const win = loadPage({ userAgent: WIN });
  const winPath = win.document.querySelector('.path-chip .path-value').textContent;
  // Asserted by shape, not against a literal, because a backslash in a literal is exactly the
  // escape-collapsing trap that has already cost this project two broken pushes.
  assert.ok(winPath.startsWith('%USERPROFILE%'),
    `a Windows dialog expands %USERPROFILE%; a tilde would paste literally and fail. Got ${winPath}`);
  assert.ok(winPath.endsWith('.claude'), `got ${winPath}`);
  assert.ok(!winPath.includes('~'), `a Windows path must not contain a tilde: ${winPath}`);

  const mac = loadPage({ userAgent: MAC });
  assert.equal(mac.document.querySelector('.path-chip .path-value').textContent, '~/.claude');
});

test('a path chip copies the path and says so', { skip: needsJsdom }, async () => {
  const { window, document } = loadPage();
  const chip = document.querySelector('.path-chip');
  let copied = null;
  Object.defineProperty(window.navigator, 'clipboard',
    { value: { writeText: async (v) => { copied = v; } }, configurable: true });

  chip.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 20));

  assert.ok(copied, 'clicking a path must put something on the clipboard');
  assert.match(copied, /\.claude$/, `copied the wrong thing: ${copied}`);
  assert.equal(chip.querySelector('.path-copy').textContent, 'copied');
});

test('a chip whose clipboard is refused selects the text instead of looking broken',
  { skip: needsJsdom }, async () => {
    const { window, document } = loadPage();
    const chip = document.querySelector('.path-chip');
    Object.defineProperty(window.navigator, 'clipboard',
      { value: { writeText: async () => { throw new Error('denied'); } }, configurable: true });

    chip.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 20));

    assert.equal(chip.querySelector('.path-copy').textContent, 'select and copy',
      'a refused clipboard must leave the user a way through, not a dead button');
  });

test('every path chip shows a path, not the placeholder markup', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  const chips = [...document.querySelectorAll('.path-chip')];
  assert.equal(chips.length, 2);
  for (const chip of chips) {
    const shown = chip.querySelector('.path-value').textContent;
    assert.match(shown, /\.(claude|codex)$/, `chip shows ${shown}`);
  }
});

test('the redaction stat says it counts messages, not items', { skip: needsJsdom }, async () => {
  // One message holding three redactable items: the page counts it once, like emulo.py.
  const row = JSON.stringify({ type: 'user', timestamp: '2026-09-20T10:00:00Z',
    message: { role: 'user', content: 'mail a@example.com and b@example.com token=abc123456789' } });
  const file = { kind: 'file', name: 'session.jsonl', getFile: async () => ({ text: async () => row + '\n' }) };
  const handle = { name: '.claude', kind: 'directory', values: async function* () { yield file; } };
  const { window, document } = loadPage({ directoryPicker: async () => handle });
  // jsdom has neither; the scan hashes long messages with them, as a browser does.
  window.TextEncoder = TextEncoder;
  Object.defineProperty(window, 'crypto', { value: require('node:crypto').webcrypto, configurable: true });
  click(window, document.getElementById('picker-button'));
  for (let i = 0; i < 50 && !document.getElementById('result-state').classList.contains('active'); i += 1) {
    await new Promise((r) => setTimeout(r, 20));
  }
  assert.ok(document.getElementById('result-state').classList.contains('active'),
    `the scan must finish: ${document.getElementById('error-message').textContent}`);
  const stats = [...document.querySelectorAll('#summary-grid .summary-stat')]
    .map((cell) => [cell.querySelector('strong').textContent, cell.querySelector('span').textContent]);
  assert.deepEqual(stats.at(-1), ['1', 'messages redacted']);
});
