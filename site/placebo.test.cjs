/**
 * DOM tests for placebo.html.
 *
 * The page's only conversion path is a form that composes a mailto and hands it to the mail
 * client. There is no backend, so nothing on the server side can notice that the form went
 * dead. If the submit handler stops firing, or the gate that enables the button inverts, the
 * page keeps looking finished and quietly receives nothing.
 *
 * That is the same failure scan.html shipped with, so these follow scan.ui.test.cjs: run the
 * page for real, and let a dead control fail the build.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

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

const html = fs.readFileSync(path.join(__dirname, 'placebo.html'), 'utf8');

/** Load the page with its scripts running, ignoring jsdom's refusal to navigate. */
function loadPage() {
  const { VirtualConsole } = require('jsdom');
  // Clicking a mailto anchor makes jsdom log "Not implemented: navigation". That is the
  // browser behaviour we want and not a defect, so it is swallowed rather than left to
  // look like an error in the output.
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', () => {});
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    url: 'https://emulo.vercel.app/placebo',
    virtualConsole,
  });
  const { window } = dom;
  // The handler writes the composed mailto onto a real anchor before clicking it, so the
  // thing the mail client would receive is readable without intercepting navigation.
  const sent = () => window.document.getElementById('mailtolink').getAttribute('href');
  return { window, document: window.document, sent };
}

/** Fill the four required answers the same way a person would. */
function fill(window, document, { publish = 'Name us either way' } = {}) {
  const set = (id, v) => {
    const el = document.getElementById(id);
    el.value = v;
    el.dispatchEvent(new window.Event('input', { bubbles: true }));
  };
  set('q1', 'Our agent reads the codebase first');
  set('q2', 'Answers cite real files instead of inventing paths');
  set('q3', 'Staging URL and a test account');
  const radio = [...document.querySelectorAll('input[name=pub]')]
    .find((r) => r.value === publish);
  radio.checked = true;
  radio.dispatchEvent(new window.Event('change', { bubbles: true }));
}

const submit = (window, document) =>
  document.getElementById('subform')
    .dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));

// -- the control must not be dead -------------------------------------------

test('submitting a filled form composes a mailto and sends the browser to it', { skip: needsJsdom }, () => {
  const { window, document, sent } = loadPage();
  fill(window, document);
  submit(window, document);

  assert.ok(sent(), 'the only conversion path on the page must actually fire');
  const href = decodeURIComponent(sent());
  assert.match(href, /^mailto:founder@viberaven\.dev\?/);
  assert.match(href, /Our agent reads the codebase first/, 'the answers must reach the draft');
  assert.match(href, /Staging URL and a test account/);
  assert.match(href, /Name us either way/, 'the publication choice is the one that must not be lost');
});

test('an empty form does not submit and says why', { skip: needsJsdom }, () => {
  const { window, document, sent } = loadPage();
  submit(window, document);

  assert.equal(sent(), null, 'an empty enquiry must not open a draft');
  assert.equal(document.getElementById('go').disabled, true);
  assert.match(document.getElementById('say').textContent, /starred/i,
    'a disabled button with no explanation reads as broken');
});

test('the button unlocks only once every required answer is present', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  const go = document.getElementById('go');
  assert.equal(go.disabled, true, 'starts locked');

  fill(window, document);
  assert.equal(go.disabled, false, 'unlocks when the four required answers are in');

  const q3 = document.getElementById('q3');
  q3.value = '   ';
  q3.dispatchEvent(new window.Event('input', { bubbles: true }));
  assert.equal(go.disabled, true, 'whitespace is not an answer');
});

test('choosing how a loss gets published is required, not assumed', { skip: needsJsdom }, () => {
  const { window, document, sent } = loadPage();
  const set = (id, v) => {
    const el = document.getElementById(id);
    el.value = v;
    el.dispatchEvent(new window.Event('input', { bubbles: true }));
  };
  set('q1', 'a'); set('q2', 'b'); set('q3', 'c');

  assert.equal(document.getElementById('go').disabled, true,
    'defaulting this would publish somebody\'s loss under their name without them choosing it');
  submit(window, document);
  assert.equal(sent(), null);
});

test('the copy fallback fills the box even when the clipboard is refused', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  document.execCommand = () => { throw new Error('clipboard blocked'); };
  fill(window, document, { publish: 'Anonymise us either way' });

  document.getElementById('copy')
    .dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));

  const fb = document.getElementById('fb');
  assert.equal(fb.hidden, false, 'a refused clipboard must still leave the text on screen');
  assert.match(document.getElementById('fbtext').value, /founder@viberaven\.dev/);
  assert.match(document.getElementById('fbtext').value, /Anonymise us either way/);
});

// -- the page must not become a payment surface -----------------------------

test('the page carries no price, because A1 excludes pricing surfaces', { skip: needsJsdom }, () => {
  assert.equal(html.includes('$'), false,
    'a price on this page would put it outside the authority it was published under');
});

test('the address people are told to write to is the one the form uses', { skip: needsJsdom }, () => {
  const { window, document, sent } = loadPage();
  fill(window, document);
  submit(window, document);

  const visible = document.getElementById('fb').textContent;
  const addresses = new Set([...html.matchAll(/[\w.+-]+@[\w.-]+\.\w+/g)].map((m) => m[0]));
  assert.deepEqual([...addresses], ['founder@viberaven.dev'],
    'one address only, or people write to a mailbox nobody reads');
  assert.match(visible, /founder@viberaven\.dev/);
  assert.match(decodeURIComponent(sent()), /founder@viberaven\.dev/);
});
