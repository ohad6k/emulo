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

// The rows SECURITY.md is pinned to, read from tests/redaction_table.py so the browser port is
// held to exactly the samples the Python table test uses.
function redactionTable() {
  const python = spawnSync('python', ['-c', 'import json,sys; sys.path.insert(0, "tests"); import redaction_table as t; print(json.dumps({"rows": t.ROWS, "misses": t.MISSES, "negatives": t.NEGATIVES}))'], {
    cwd: path.join(__dirname, '..'), encoding: 'utf8',
  });
  assert.equal(python.status, 0, python.stderr);
  return JSON.parse(python.stdout);
}

test('every pattern SECURITY.md names redacts its sample to the documented placeholder', () => {
  const { core } = loadCore();
  const { rows, misses, negatives } = redactionTable();
  assert.ok(rows.length >= 40, `expected the full table, got ${rows.length} rows`);
  for (const row of [...rows, ...misses, ...negatives]) assert.equal(core.redact(row.input), row.expected, row.doc || row.input);
});

// Built from parts so no scanner mistakes the fixtures for live keys.
function credentialSamples() {
  const body = 'Ab3_dE-fGh'.repeat(9);
  const google = ['AI', 'za', 'SyD3_x-9QwErTyUiOpAsDfGhJkLzXcVbN12'.slice(0, 35)].join('');
  return [
    `use ${['sk-', 'ant-api03-', body, 'AA'].join('')} for the eval`,
    `ANTHROPIC_API_KEY ${['sk-', 'ant-oat01-', body].join('')}`,
    `old key ${['sk-', 'proj-', body, '_T3BlbkFJ', body].join('')} rotated`,
    `maps key ${google}.`, `?key=${google}&v=3`,
    'the AIza prefix marks a Google key', 'AIzaShort-123 is not a key', 'sk-ant is the prefix Anthropic uses',
    'postgres://app:s3cr3tpw@localhost:5432/db', 'DATABASE_URL=postgresql://app:hunter2@localhost/app_dev',
    'mysql://root:rootpw@dbhost:3306/shop', 'redis://:redispass@localhost:6379/0',
    'amqp://guest:guestpw@rabbit:5672/', 'jdbc:postgresql://svc:pw1@localhost/x', 'postgres://u:p@ss@localhost/db',
    'mongodb+srv://admin:M0ng0!pass@cluster0.abcde.mongodb.net/test',
    'git clone https://deploy:tok3nvalue@git.example.com/repo.git', 'postgres://app:pw@10.0.0.5/db',
    'https://example.com/path?q=1', 'http://localhost:3000/api', 'postgres://app@localhost/db',
    'ssh://deploy@build-box:22/srv/repo', 'see http://host:8080/a:b for details',
    // adjacency: a lookbehind reads a character a previous match already used; a rewrite without
    // one must still match here exactly as Python does
    'a://u:p@b://v:q@h', ['x://u:p@-sk-', 'ant-', 'A'.repeat(24)].join(''),
    '0521234567 0521234567', 'call +972 52-123-4567,+972 52-123-4567',
    'https://host:8443/path?u=a@b', 'http://localhost:3000?next=a@b.com', 'http://localhost:3000#to=a@b.com',
  ];
}

test('redaction covers Anthropic and Google keys and passwords in connection URLs', () => {
  const { core } = loadCore();
  const google = ['AI', 'za', 'SyD3_x-9QwErTyUiOpAsDfGhJkLzXcVbN12'.slice(0, 35)].join('');
  const cases = [
    [['sk-', 'ant-api03-', 'Ab3_dE-fGh'.repeat(9), 'AA'].join(''), '[ANTHROPIC_KEY]'],
    [['sk-', 'proj-', 'Ab3_dE-fGh'.repeat(9)].join(''), '[OPENAI_KEY]'],
    [`key ${google}`, 'key [GOOGLE_API_KEY]'],
    ['postgres://app:s3cr3tpw@localhost:5432/db', 'postgres://app:[REDACTED]@localhost:5432/db'],
    ['redis://:redispass@localhost:6379/0', 'redis://:[REDACTED]@localhost:6379/0'],
    ['postgres://u:p@ss@localhost/db', 'postgres://u:[REDACTED]@localhost/db'],
    ['postgres://app@localhost/db', 'postgres://app@localhost/db'],
    ['http://localhost:3000?next=a@b.com', 'http://localhost:3000?next=[EMAIL]'],
    ['https://host:8443/path?u=a@b', 'https://host:8443/path?u=a@b'],
    ['the AIza prefix marks a Google key', 'the AIza prefix marks a Google key'],
  ];
  for (const [input, expected] of cases) assert.equal(core.redact(input), expected, input);
});

test('no script in scan.html uses a regex lookbehind, which Safari before 16.4 cannot parse', () => {
  // One unparseable literal stops the whole inline script, so the scan would not load at all.
  const { html } = loadCore();
  const scripts = Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g), (match) => match[1]);
  assert.ok(scripts.length >= 2);
  for (const script of scripts) assert.doesNotMatch(script, /\(\?<[=!]/);
});

test('the connection URL rule stays linear on long tokens without a lookbehind', () => {
  const { core } = loadCore();
  const blob = 'a'.repeat(200000) + ' b://' + 'c'.repeat(200000) + ' x://u:' + 'p'.repeat(200000);
  const started = performance.now();
  const output = core.redactConnectionUrlPasswords(blob);
  assert.ok(performance.now() - started < 2000, `took ${performance.now() - started} ms`);
  assert.equal(output, blob);
  assert.equal(core.redactConnectionUrlPasswords('a://u:p@b://v:q@h'), 'a://u:[REDACTED]@b://v:[REDACTED]@h');
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
    ...credentialSamples(),
    ...(({ rows, misses, negatives }) => [...rows, ...misses, ...negatives].map((row) => row.input))(redactionTable()),
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

async function coachParity(texts) {
  const { core } = loadCore();
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'emulo-scan-parity-'));
  const logRoot = path.join(root, '.codex', 'sessions');
  fs.mkdirSync(logRoot, { recursive: true });
  const rows = texts.map((text, index) => ({
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
    return jsReport;
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('browser extraction and coach output match the current Python implementation', async () => {
  const repeated = 'Please run the exact full test suite now';
  await coachParity([
    repeated, `${repeated}!`, `${repeated}.`,
    'Make the release notes shorter and drop the roadmap section',
    'Make the release notes shorter and drop the roadmap part',
    'Make the release notes much shorter and drop the roadmap part',
    'As I said, this stays entirely local',
    'I already told you to leave that file alone',
    'Like I said, do not deploy this',
    'No, keep this as one self contained page',
    'mail dev@example.com about token: fake-value-123',
  ]);
});

test('quoted and pasted text is masked the same way as Python before markers and openers match', async () => {
  // A marker inside a fence, a "> " line, or a double-quoted span (straight or curly) is text
  // you quoted, not you restating anything. Three genuine markers still flag the finding.
  const report = await coachParity([
    'proofread this: "As I said in the last update, the launch moves to Friday."',
    '> like I said last week, the invoice is overdue\n\nhelp me answer this politely',
    'help me answer this politely\n> like I said last week, the invoice is overdue',
    'tighten this reply\n```\nLike I said on the call, the budget is fixed.\n```',
    'fix the grammar: \u201cas i said, we ship when its ready\u201d',
    '"No, we cannot ship on Friday" is what my manager wrote, draft a reply',
    // The same marker inside and outside the quote: only a masked search windows on the second.
    `"i told you in the memo" ${'z'.repeat(200)} i told you the header stays fixed`,
    'as I said, use pnpm not npm',
    '> I switched the config to yaml\n\nno, keep it as json',
    'like i said, no new dependencies',
  ]);
  const restated = report.findings.find((item) => item.key === 'restated_context');
  assert.ok(restated, 'three genuine markers must flag restated context');
  assert.equal(restated.occurrences, 3);
  assert.deepEqual(new Set(restated.receipts.map((receipt) => receipt.marker)), new Set(['i told you', 'as i said', 'like i said']));
  const windowed = restated.receipts.find((receipt) => receipt.text.includes('i told you the header stays fixed'));
  assert.ok(windowed, 'the receipt must window on the marker that was counted');
  assert.ok(!windowed.text.includes('in the memo'), 'not on the copy inside the quote');
  assert.equal(report.correction_rate, 10);
});

test('unclosed curly quotes stay linear on a long paste, so the page never freezes', () => {
  // German quotes close with U+201C, so a long paste is full of openers with no U+201D after
  // them. Before the fix this took 11 s at 400k characters, on the main thread.
  const { core } = loadCore();
  const text = '„ab“ '.repeat(80000);
  const record = { session_id: 's', source: 'codex', messages: [{ text, date: '2026-08-01', ordinal: 0 }] };
  const start = performance.now();
  core.usageReport([record]);
  assert.ok(performance.now() - start < 2000, 'masking a long German-quoted paste must stay fast');
});

function emuloChunk(messages) {
  // A chunk written by Emulo's own Python writer, so the page is tested against the real format.
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'emulo-scan-chunk-'));
  try {
    const source = path.join(root, 'source');
    fs.mkdirSync(source, { recursive: true });
    fs.writeFileSync(path.join(source, 'session.jsonl'), messages.map((text, index) => line({
      timestamp: `2026-07-08T10:0${index}:00Z`,
      payload: { type: 'message', role: 'user', content: [{ text }] },
    })).join('\n'), 'utf8');
    const python = spawnSync('python', ['-c', [
      'import os, sys',
      'import emulo',
      'mined = emulo.mine_files(emulo.discover_files([sys.argv[1]]))',
      'out = os.path.join(sys.argv[2], "emulo-out")',
      'emulo.write_outputs(mined["blocks"], out, 1)',
      'sys.stdout.buffer.write(open(os.path.join(out, "chunks", "chunk-01.txt"), "rb").read())',
    ].join('\n'), source, root], { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
    assert.equal(python.status, 0, python.stderr);
    assert.match(python.stdout, /^===== session:[A-Za-z0-9_-]+ source:[a-z0-9_-]+ =====\n/);
    return python.stdout;
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('an Emulo chunk sent to an agent is not read back as the user, same as Python', async () => {
  // Mining a history means handing chunks to an agent, and each of those prompts is logged as a
  // user message. Reading them back counted the markers inside them as the person restating things.
  const chunk = emuloChunk([
    'as i said, the header stays fixed on scroll',
    'i already told you to keep the release notes short',
    'like i said, never deploy from a feature branch',
  ]);
  const genuine = ['ship the settings page once the suite is green', 'use pnpm for every install'];
  const report = await coachParity([
    genuine[0],
    `Pull evidence for four domains from this chunk.\n\n${chunk}`,
    chunk,
    `Below is one chunk.\r\n\r\n${chunk.replace(/\n/g, '\r\n')}`,
    genuine[1],
  ]);
  assert.equal(report.messages, 2);
  assert.equal(report.findings.find((item) => item.key === 'restated_context'), undefined);
});

test('only a whole line in Emulo\'s exact chunk format marks a message as injected', () => {
  const { core } = loadCore();
  assert.equal(core.isInjectedContext('Read this.\n\n===== session:0123456789abcdef source:claude =====\n[2026-09-20]\nhi'), true);
  assert.equal(core.isInjectedContext('Read this.\r\n\r\n===== session:0123456789abcdef source:claude =====\r\n[2026-09-20]\r\nhi'), true);
  assert.equal(core.isInjectedContext('Packet.\n\n===== receipt:rcpt-0123456789abcdef0123 session:0123456789abcdef source:claude date:2026-09-20 =====\nhi\n'), true);
  for (const text of [
    'the chunk opens with ===== session:abc source:claude ===== and I want that gone',
    'why does it print\n=====\nsession: abc\nand then stop',
    '===== session notes =====\nkeep the header fixed',
    '===== session:abc =====\nno source on this line, so it is not Emulo\'s',
    '===== session:abc source:claude =====\rjunk after a bare carriage return',
    '====== session:abc source:claude =====\nsix on the left is a heading, not a chunk',
    '===== session:abc source:claude ======\nsix on the right is a heading, not a chunk',
    '==== session:abc source:claude ====\nfour on each side is a heading, not a chunk',
    'see: ===== session:abc source:claude =====\nwhy does emulo print this line?',
  ]) {
    assert.equal(core.isInjectedContext(text), false, text);
  }
});
