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
const { JSDOM } = require('jsdom');

const pagePath = path.join(__dirname, 'scan.html');
const html = fs.readFileSync(pagePath, 'utf8');

/**
 * Load the page with its scripts running.
 *
 * `directoryPicker` decides which browser we are pretending to be. jsdom has no File System
 * Access API of its own, so the default is exactly Ohad's case: the fallback branch.
 */
function loadPage({ directoryPicker = null } = {}) {
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
    },
  });
  const { window } = dom;
  const has = (el, type) => listeners.some((l) => l.target === el && l.type === type);
  return { dom, window, document: window.document, listeners, has };
}

const click = (window, el) =>
  el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));

// -- the regression ---------------------------------------------------------

test('the primary folder button works on a browser with no File System Access API', () => {
  const { window, document } = loadPage();
  assert.equal('showDirectoryPicker' in window, false, 'this is the browser Ohad was using');

  const button = document.getElementById('picker-button');
  const input = document.getElementById('folder-input');
  let opened = 0;
  input.click = () => { opened += 1; };

  click(window, button);
  assert.equal(opened, 1, 'clicking the page\'s primary control must open a folder picker');
});

test('the primary folder button is not hidden away on that browser', () => {
  const { document } = loadPage();
  const button = document.getElementById('picker-button');
  assert.equal(button.hidden, false,
    'hiding it was the old fix, and CSS defeated it. It must work instead of disappear.');
});

test('the primary folder button uses the native picker when the browser has one', async () => {
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

test('dismissing the native picker is silent, not an error screen', async () => {
  const picker = async () => { const e = new Error('x'); e.name = 'AbortError'; throw e; };
  const { window, document } = loadPage({ directoryPicker: picker });
  click(window, document.getElementById('picker-button'));
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(document.getElementById('error-state').classList.contains('active'), false,
    'changing your mind about a folder is not a failure');
});

test('a native picker that genuinely fails shows the error state', async () => {
  const picker = async () => { throw new Error('permission denied'); };
  const { window, document } = loadPage({ directoryPicker: picker });
  click(window, document.getElementById('picker-button'));
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(document.getElementById('error-state').classList.contains('active'), true);
});

// -- the general guard, which does not need to know what broke --------------

test('no control the page renders is left unwired', () => {
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

test('the fallback control still drives the file input', () => {
  const { document } = loadPage();
  const span = document.getElementById('fallback-button');
  assert.ok(span.closest('label'), 'the secondary button is a label wrapping the real input');
  assert.equal(span.closest('label').querySelector('input[type=file]').id, 'folder-input');
});

// -- the promise the page makes ---------------------------------------------

test('the loaded page issues no network request', () => {
  const { document } = loadPage();
  for (const el of document.querySelectorAll('[src], link[href], form[action]')) {
    const url = el.getAttribute('src') || el.getAttribute('href') || el.getAttribute('action');
    assert.doesNotMatch(url || '', /^https?:/i, `${el.tagName} reaches off the machine: ${url}`);
  }
});

test('the reset controls return the page to the choose state', () => {
  const { window, document } = loadPage();
  document.getElementById('result-state').classList.add('active');
  click(window, document.getElementById('reset-button'));
  assert.equal(document.getElementById('choose-state').classList.contains('active'), true);
});

test('hidden means hidden even on an element whose class sets display', () => {
  const { window, document } = loadPage();
  const probe = document.createElement('div');
  probe.className = 'button';
  probe.hidden = true;
  document.body.appendChild(probe);
  assert.equal(window.getComputedStyle(probe).display, 'none',
    'without the [hidden] !important rule, .button display:inline-flex wins');
});
