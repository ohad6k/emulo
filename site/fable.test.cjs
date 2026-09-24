/**
 * DOM tests for fable/index.html.
 *
 * The page is a wall of generated outputs driven entirely by data.json. There is no
 * backend, so if the boot fails, a filter chip stops firing, or the viewer never opens,
 * the page keeps looking finished and shows either nothing or everything. Same rule as
 * scan.html and placebo.html: run the page for real, and let a dead control fail the build.
 *
 * The fixture below is a small data.json, not the real one, so the test does not depend
 * on which runs have finished.
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

const html = fs.readFileSync(path.join(__dirname, 'fable', 'index.html'), 'utf8');

function item(model, task, cond, rep) {
  const ext = task === 'tui' ? 'py' : 'html';
  const it = {
    id: `${model}/${task}-${cond}-${rep}`, model, model_id: model === 'fable51' ? 'claude-fable-5-1' : 'claude-opus-5',
    task, cond, cond_name: { a: 'cold', b: 'profile', c: 'placebo' }[cond], rep,
    file: `out/${model}/${task}-${cond}-${rep}.${ext}`, elapsed_s: 40, output_bytes: 5000,
    output_tokens: 5000, thinking_tokens: 100, cost_usd_list: 0.5, console: [],
  };
  if (task === 'tui') it.term = `out/${model}/${task}-${cond}-${rep}.term.html`;
  else it.shot = `shots/${model}/${task}-${cond}-${rep}.jpg`;
  return it;
}

function fixture() {
  const items = [];
  for (const model of ['opus5', 'fable51']) {
    for (const task of ['dash', 'page', 'ledger', 'tui']) {
      for (const cond of ['a', 'b', 'c']) {
        for (let rep = 0; rep < 2; rep++) items.push(item(model, task, cond, rep));
      }
    }
  }
  items[3].console = ['PAGE ERROR: ReferenceError: THREE is not defined'];
  return {
    generated: '2026-09-01', claude_code_version: '2.1.257 (Claude Code)', profile_bytes: 9551,
    placebo_bytes: 9495, base_system_prompt: 'You are an expert.', counts: { ok: items.length, failed: 0 },
    list_cost_usd: 12.5, task_order: ['dash', 'page', 'ledger', 'tui'], items,
    cells: { 'opus5/dash/M1_border_radius': { a: [1, 2, 3, 4, 5], b: [0, 0, 0, 0, 1], c: [0, 0, 1, 1, 1] } },
    H1: { opus5: { count: 3 }, fable51: { count: 1 }, verdict: 'PASS' },
    H2: { fable51: { count: 0, B_vs_C_reversed: [['page', 'M1_border_radius']] }, verdict: 'PASS' },
    H3_hits: {}, h3: { read: 0, confirmed: 0, verdict: 'PASS' },
    cold_vs_cold: { 'dash/M1_border_radius': { opus5: [1, 2, 3, 4, 5], fable51: [6, 7, 8, 9, 10], result: 'Fable HIGHER, separated' } },
  };
}

/** Load the page with its scripts running and the fixture already on window. */
function loadPage() {
  const { VirtualConsole } = require('jsdom');
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', () => {});
  const seeded = html.replace('<script>', '<script>window.__fableData=' + JSON.stringify(fixture()) + ';</script><script>');
  const dom = new JSDOM(seeded, {
    runScripts: 'dangerously',
    url: 'https://emulo.vercel.app/fable',
    virtualConsole,
    pretendToBeVisual: true,
  });
  // jsdom has no fetch; the page only uses it for terminal thumbnails and data.json.
  dom.window.fetch = () => Promise.reject(new Error('no fetch in test'));
  return { window: dom.window, document: dom.window.document };
}

const cards = (document) => document.querySelectorAll('#wall .card');
const press = (window, el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));

test('the wall renders every item and the headline facts come from the data', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  assert.equal(cards(document).length, 48, 'one card per run');
  assert.equal(document.getElementById('f-runs').textContent, '48');
  assert.equal(document.getElementById('f-fab').textContent, '0');
  assert.match(document.getElementById('count').textContent, /48 of 48/);
  assert.match(cards(document)[0].querySelector('img').getAttribute('src'), /^\/fable\/shots\//, 'served at /fable without a slash, so every asset path must be absolute');
});

test('a run that threw in the browser is marked on its card, not hidden', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  const bad = [...cards(document)].filter((c) => c.querySelector('.sub.bad'));
  assert.equal(bad.length, 1);
  assert.match(bad[0].textContent, /THREE is not defined/);
});

test('every filter chip narrows the wall and the count follows', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  press(window, document.querySelector('#controls [data-key=model] [data-v=fable51]'));
  assert.equal(cards(document).length, 24, 'model filter');
  press(window, document.querySelector('#controls [data-key=task] [data-v=dash]'));
  assert.equal(cards(document).length, 6, 'task filter stacks');
  press(window, document.querySelector('#controls [data-key=cond] [data-v=c]'));
  assert.equal(cards(document).length, 2, 'condition filter stacks');
  assert.match(document.getElementById('count').textContent, /2 of 48/);
  assert.equal(document.querySelector('#controls [data-key=cond] [data-v=c]').getAttribute('aria-pressed'), 'true');
  press(window, document.querySelector('#controls [data-key=model] [data-v=all]'));
  assert.equal(cards(document).length, 4, 'going back to Both keeps the other filters');
});

test('clicking a card opens the live file in the viewer and Escape closes it', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  const first = cards(document)[0];
  press(window, first);
  const viewer = document.getElementById('viewer');
  assert.ok(viewer.hasAttribute('open'), 'the viewer must open');
  const iframe = viewer.querySelector('iframe');
  assert.ok(iframe, 'the viewer shows the real output, not a still');
  assert.equal(iframe.getAttribute('src'), first.getAttribute('data-id').replace(/^(\w+)\/(.+)$/, '/fable/out/$1/$2.html'));
  assert.equal(iframe.getAttribute('sandbox'), 'allow-scripts', 'generated pages run sandboxed');
  assert.match(viewer.querySelector('a[href]').getAttribute('href'), /^\/fable\/out\//, 'the raw file is one click away');
  document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.equal(viewer.hasAttribute('open'), false);
});

test('the side by side shows both models for the picked run and follows the chips', { skip: needsJsdom }, () => {
  const { window, document } = loadPage();
  const src = (m) => document.querySelector(`#pane-${m} iframe`).getAttribute('src');
  assert.equal(src('opus5'), '/fable/out/opus5/dash-a-0.html');
  assert.equal(src('fable51'), '/fable/out/fable51/dash-a-0.html');
  press(window, document.querySelector('#cmp-cond [data-v=b]'));
  press(window, document.querySelector('#cmp-rep [data-v=1]'));
  assert.equal(src('fable51'), '/fable/out/fable51/dash-b-1.html');
  press(window, document.querySelector('#cmp-task [data-v=tui]'));
  assert.equal(src('fable51'), '/fable/out/fable51/tui-b-1.term.html', 'terminal runs show the rendered stdout');
});

test('the scorecard prints the verdicts and the counts they rest on', { skip: needsJsdom }, () => {
  const { document } = loadPage();
  const v = document.getElementById('verdicts').textContent;
  assert.match(v, /1 of 9/);
  assert.match(v, /3 of 9/);
  assert.match(v, /PASS/);
  assert.match(v, /page\/M1_border_radius/, 'a reversed separation is printed, not dropped');
  assert.match(document.getElementById('tbl-cold').textContent, /Fable HIGHER, separated/);
  assert.match(document.getElementById('tbl-all').textContent, /0 0 0 0 1/);
});
