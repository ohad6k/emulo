const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { spawnSync } = require('node:child_process');

const pagePath = path.join(__dirname, 'scan.html');

function loadCore() {
  const html = fs.readFileSync(pagePath, 'utf8');
  const match = html.match(/<script id="scan-core">([\s\S]*?)<\/script>/);
  assert.ok(match, 'scan.html must expose its inline core through #scan-core');
  const sandbox = {
    console,
    crypto: webcrypto,
    performance,
    TextEncoder,
    setTimeout,
    clearTimeout,
  };
  sandbox.globalThis = sandbox;
  vm.runInNewContext(match[1], sandbox, { filename: 'scan-core.js' });
  return { core: sandbox.EmuloScanCore, html };
}

function line(value) {
  return JSON.stringify(value);
}

test('the scan is one local page with both directory selection paths and no network surface', () => {
  const { html } = loadCore();
  for (const [index, script] of Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g), (match) => match[1]).entries()) {
    assert.doesNotThrow(() => new vm.Script(script), `inline script ${index + 1} must parse`);
  }
  assert.match(html, /showDirectoryPicker/);
  assert.match(html, /webkitdirectory/);
  assert.doesNotMatch(html, /\bfetch\s*\(/);
  assert.doesNotMatch(html, /sendBeacon|XMLHttpRequest|WebSocket|EventSource/);
  assert.doesNotMatch(html, /(?:src|href)\s*=\s*["']https?:/i);
  assert.doesNotMatch(html, new RegExp(['Emulo', 'Pro'].join(' '), 'i'));
});

test('redaction matches the Python table without eating dates or plain password prose', () => {
  const { core } = loadCore();
  const input = [
    'mail me at dev@example.com from 192.168.1.4',
    ['sk-', 'abcdefghijklmnopqrstuvwxyz123456'].join(''),
    'token: abc123 and password is hunter2',
    'password is wrong on 2026-06-14 and v0.8.0',
    'call +972 52-123-4567.',
  ].join('\n');
  const output = core.redact(input);
  assert.equal(output, [
    'mail me at [EMAIL] from [IP]',
    '[OPENAI_KEY]',
    'token=[REDACTED] and password=[REDACTED]',
    'password is wrong on 2026-06-14 and v0.8.0',
    'call [PHONE].',
  ].join('\n'));
});

test('redaction is byte-for-byte equal to Python on the repository edge-case corpus', () => {
  const { core } = loadCore();
  const samples = [
    'the password is Hunter2!', 'psk Tr0ub4dor3', 'wifi key abc12345', 'password: sekritvalue1',
    'the password is wrong', 'password reset email', 'my token store', 'passwd prompt appeared',
    'boarding pass QF12345', 'pwd C:/Users/me/project1',
    '2026-06-14', '07/09/2026', 'v0.8.0', '0x04', '4.6 V', 'acer-15-6-aspire-lite-n4500',
    '18 payments of 150', 'PEX 543 777 2996', '129424534', '1,656 sessions',
    '07 5477 4500', '+61 400 123 456', '0400123456', '052-1234567', '0521234567',
    '03-1234567', 'reach me at +972 52-123-4567.', '(02) 9876 5432', '(03) 123-4567',
    '+1 (415) 555-2671', '07700 900123', '+49 151 12345678',
  ];
  const python = spawnSync('python', ['-c', 'import emulo,json,sys; print(json.dumps([emulo.redact(x) for x in json.loads(sys.argv[1])]))', JSON.stringify(samples)], {
    cwd: path.join(__dirname, '..'), encoding: 'utf8',
  });
  assert.equal(python.status, 0, python.stderr);
  assert.equal(JSON.stringify(samples.map(core.redact)), JSON.stringify(JSON.parse(python.stdout)));
});

test('JSONL extraction keeps only typed human turns across supported layouts', () => {
  const { core } = loadCore();
  const jsonl = [
    line({ type: 'user', timestamp: '2026-08-01T10:00:00Z', message: { role: 'user', content: 'Claude human' } }),
    line({ type: 'user', isMeta: true, message: { role: 'user', content: 'meta traffic' } }),
    line({ type: 'user', promptSource: 'sdk', entrypoint: 'sdk-cli', message: { role: 'user', content: 'sdk harness' } }),
    line({ type: 'user', promptSource: 'sdk', message: { role: 'user', content: 'Desktop human' } }),
    line({ type: 'response_item', timestamp: '2026-08-02T10:00:00Z', payload: { type: 'message', role: 'user', content: [{ type: 'input_text', text: '<heartbeat>x</heartbeat>Codex human<image name="x" path="C:/secret">' }] } }),
    line({ type: 'USER_INPUT', source: 'USER_EXPLICIT', created_at: '2026-08-03T10:00:00Z', content: '<USER_REQUEST>Antigravity human</USER_REQUEST><ADDITIONAL_METADATA>noise</ADDITIONAL_METADATA>' }),
    line({ type: 'USER_INPUT', source: 'HARNESS', content: '<USER_REQUEST>not human</USER_REQUEST>' }),
    line({ type: 'user.message', timestamp: '2026-08-04T10:00:00Z', data: { source: 'interactive', content: 'Copilot human' } }),
    line({ type: 'user.message', data: { source: 'system', content: 'system injection' } }),
    line({ type: 'assistant', message: { role: 'assistant', content: 'assistant text' } }),
    line({ type: 'user', message: { role: 'user', content: '# AGENTS.md instructions\nnot typed' } }),
    '{broken json',
  ].join('\n');

  assert.equal(
    JSON.stringify(core.extractMessages(jsonl)),
    JSON.stringify(
    [
      ['2026-08-01', 'Claude human'],
      ['', 'Desktop human'],
      ['2026-08-02', 'Codex human'],
      ['2026-08-03', 'Antigravity human'],
      ['2026-08-04', 'Copilot human'],
    ],
    ),
  );
});

test('mining sorts sessions, drops subagents, redacts, and collapses long duplicate prose', async () => {
  const { core } = loadCore();
  const long = `I already told you ${'context '.repeat(30)}`.trim();
  const files = [
    { path: '.claude/projects/b.jsonl', text: line({ type: 'user', timestamp: '2026-08-02', message: { role: 'user', content: long } }) },
    { path: '.claude/projects/a.jsonl', text: [
      line({ type: 'user', timestamp: '2026-08-01', message: { role: 'user', content: long } }),
      line({ type: 'user', timestamp: '2026-08-01', message: { role: 'user', content: 'email dev@example.com' } }),
    ].join('\n') },
    { path: '.claude/projects/subagents/child.jsonl', text: line({ type: 'user', message: { role: 'user', content: 'ignore me' } }) },
    { path: '.claude/projects/no-users.jsonl', text: line({ type: 'assistant', message: { role: 'assistant', content: 'ignore me' } }) },
  ];

  const mined = await core.mineFiles(files);
  assert.equal(mined.files, 3);
  assert.equal(mined.sessions, 1);
  assert.equal(mined.messages, 2);
  assert.equal(mined.redactions, 1);
  assert.equal(mined.duplicates, 1);
  assert.equal(mined.records[0].source, 'claude');
  assert.equal(mined.records[0].messages[1].text, 'email [EMAIL]');
});

test('coach ports all four deterministic checks with dated receipts', async () => {
  const { core } = loadCore();
  const reworded = [
    'Please keep the navigation compact and preserve the current page layout',
    'Please preserve the current page layout and keep the navigation compact',
    'Keep the navigation compact and please preserve the current page layout',
  ];
  const messages = [
    'Please run the exact full test suite now',
    'Please run the exact full test suite now!',
    'Please run the exact full test suite now.',
    ...reworded,
    'As I said, this stays entirely local',
    'I already told you to leave that file alone',
    'Like I said, do not deploy this',
    'No, keep this as one self contained page',
  ];
  const file = {
    path: '.codex/sessions/2026/08/session.jsonl',
    text: messages.map((text, index) => line({
      type: 'response_item',
      timestamp: `2026-08-${String(index + 1).padStart(2, '0')}T00:00:00Z`,
      payload: { type: 'message', role: 'user', content: [{ text }] },
    })).join('\n'),
  };

  const mined = await core.mineFiles([file]);
  const report = core.usageReport(mined.records);
  const byKey = Object.fromEntries(report.findings.map((finding) => [finding.key, finding]));

  assert.equal(report.sessions, 1);
  assert.equal(report.messages, 10);
  assert.equal(report.first_date, '2026-08-01');
  assert.equal(report.last_date, '2026-08-10');
  assert.equal(report.correction_rate, 10);
  assert.equal(byKey.repeat_sends.occurrences, 3);
  assert.equal(byKey.reword_loops.occurrences, 3);
  assert.equal(byKey.restated_context.occurrences, 3);
  assert.equal(byKey.corrections.occurrences, 1);
  assert.equal(byKey.restated_context.receipts[0].date, '2026-08-07');
  assert.match(byKey.corrections.receipts[0].text, /^No, keep this/);
});

test('pasted stack traces are excluded at the same strict threshold as Python', () => {
  const { core } = loadCore();
  const log = 'Traceback\n  File "a.py", line 1\nValueError\nplain';
  const notLog = 'Traceback\nplain\nplain\nplain';
  assert.equal(core.isPastedLog(log), true);
  assert.equal(core.isPastedLog(notLog), false);
});

test('browser extraction and coach output match the current Python implementation', async () => {
  const { core } = loadCore();
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'emulo-scan-parity-'));
  const logRoot = path.join(root, '.codex', 'sessions');
  fs.mkdirSync(logRoot, { recursive: true });
  const repeated = 'Please run the exact full test suite now';
  const rows = [
    repeated, `${repeated}!`, `${repeated}.`,
    'Make the release notes shorter and drop the roadmap section',
    'Make the release notes shorter and drop the roadmap part',
    'Make the release notes much shorter and drop the roadmap part',
    'As I said, this stays entirely local',
    'I already told you to leave that file alone',
    'Like I said, do not deploy this',
    'No, keep this as one self contained page',
    'mail dev@example.com about token: fake-value-123',
  ].map((text, index) => ({
    type: 'response_item',
    timestamp: `2026-07-${String(index + 1).padStart(2, '0')}T10:00:00Z`,
    payload: { type: 'message', role: 'user', content: [{ text }] },
  }));
  const filePath = path.join(logRoot, 'session.jsonl');
  fs.writeFileSync(filePath, rows.map(line).join('\n'), 'utf8');

  try {
    const jsMined = await core.mineFiles([{ path: '.codex/sessions/session.jsonl', text: fs.readFileSync(filePath, 'utf8') }]);
    const jsReport = JSON.parse(JSON.stringify(core.usageReport(jsMined.records)));
    for (const finding of jsReport.findings) {
      for (const receipt of finding.receipts) delete receipt.session_id;
    }

    const python = spawnSync('python', ['-c', [
      'import json, sys, inspect',
      'import emulo',
      'files = emulo.discover_files([sys.argv[1]])',
      // show_progress is not in every version of mine_files. Passing it unconditionally made
      // this test depend on an uncommitted local change to emulo.py: it passed on the machine
      // that had it and could not pass on the published repo. What is under test here is
      // extraction and report parity, not a progress flag.
      '_kw = {"show_progress": False} if "show_progress" in inspect.signature(emulo.mine_files).parameters else {}',
      'mined = emulo.mine_files(files, **_kw)',
      'report = emulo.usage_report(mined["records"])',
      'for finding in report["findings"]:',
      '    for receipt in finding["receipts"]: receipt.pop("session_id", None)',
      'print(json.dumps({"mined": {key: mined[key] for key in ("sessions", "messages", "chars", "redactions", "duplicates", "first_date", "last_date")}, "report": report}, sort_keys=True))',
    ].join('\n'), path.join(root, '.codex')], { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
    assert.equal(python.status, 0, python.stderr);
    const py = JSON.parse(python.stdout);
    assert.deepEqual({
      sessions: jsMined.sessions,
      messages: jsMined.messages,
      chars: jsMined.chars,
      redactions: jsMined.redactions,
      duplicates: jsMined.duplicates,
      first_date: jsMined.first_date,
      last_date: jsMined.last_date,
    }, py.mined);
    assert.deepEqual(jsReport, py.report);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
