/**
 * The directory's back end: a free Apps Script web app that runs under your
 * Google account. The Streamlit app calls it to add reports. It is the only
 * thing that writes to the two workbooks, and the Streamlit app can't read
 * anything through it.
 *
 * See docs/SETUP.md. Run setup() once, then deploy as a web app.
 */

const PUBLIC_COLUMNS = [
  'record_id', 'employer_name', 'entity_type', 'state', 'city', 'position',
  'report_description', 'ratings', 'experience_period', 'submission_type',
  'date_reported', 'last_updated', 'verification_status', 'review_state', 'source',
  'pay_rate', 'avg_hours', 'rent_per_week',
];
const SUBMISSION_COLUMNS = ['received_at', ...PUBLIC_COLUMNS, 'original_details', 'contact'];
const QUEUE_COLUMNS = [
  'record_id', 'employer_name', 'state', 'submitted_at', 'review_status', 'priority',
  'reviewed_at', 'decision', 'reviewer_notes',
];
const CORRECTION_COLUMNS = [
  'received_at', 'record_id', 'role', 'problem', 'proposed', 'evidence', 'contact', 'status', 'notes',
];
const REMOVED_COLUMNS = [...PUBLIC_COLUMNS, 'removed_at', 'removed_status', 'reason'];
// Free-text columns only. A date such as 2026-11-01 looks like a phone number.
const MASKED_COLUMNS = [
  'employer_name', 'city', 'position', 'report_description',
  'pay_rate', 'avg_hours', 'rent_per_week',
];

const TAB = {
  PUBLIC: 'Public Directory',
  SUBMISSIONS: 'Submissions',
  QUEUE: 'Review Queue',
  CORRECTIONS: 'Corrections',
  REMOVED: 'Removed',
  ARCHIVE: 'Legacy Archive',
  SETTINGS: 'Settings',
};
const STATUS = {
  LIVE: 'Live',
  REVIEWED: 'Reviewed',
  CLARIFY: 'Requires Clarification',
  HELD: 'Held',
  REMOVED: 'Removed',
};
const OFF_SITE = [STATUS.HELD, STATUS.REMOVED];

const SUBMITTABLE_STATUSES = ['community_reported', 'unverified'];
const MAX_TEXT_LENGTH = 6000;
const MAX_FIELD_LENGTH = 300;
const NONCE_SECONDS = 3600;
const REPEAT_SECONDS = 21600;
const QUEUE_ROWS_WITH_DROPDOWN = 20000;

const EMAIL_PATTERN = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
const PHONE_PATTERN = /(?<![\w$.])\+?\d[\d\s().-]{7,}\d(?!\w)/g;
const PRIORITY_PATTERN = /traffick|\brape|assault|sexual|\bsex\b|molest|\bdrugs?\b|weapon|\bguns?\b|\bkill|threat|\bstole|\bsteal|fraud/i;

/** Run once. Creates both workbooks, the dropdown, settings and the edit trigger. */
function setup() {
  const props = PropertiesService.getScriptProperties();
  if (props.getProperty('PRIVATE_ID')) {
    throw new Error('Setup has already run.');
  }

  const publicBook = SpreadsheetApp.create('Directory - Public');
  const privateBook = SpreadsheetApp.create('Directory - Private (do not share)');
  const token = Utilities.getUuid() + Utilities.getUuid();

  const publicTab = publicBook.getSheets()[0].setName(TAB.PUBLIC);
  startTab(publicTab, PUBLIC_COLUMNS);

  const submissions = privateBook.getSheets()[0].setName(TAB.SUBMISSIONS);
  startTab(submissions, SUBMISSION_COLUMNS);
  const queue = startTab(privateBook.insertSheet(TAB.QUEUE), QUEUE_COLUMNS);
  startTab(privateBook.insertSheet(TAB.CORRECTIONS), CORRECTION_COLUMNS);
  startTab(privateBook.insertSheet(TAB.REMOVED), REMOVED_COLUMNS);
  privateBook.insertSheet(TAB.ARCHIVE);
  addStatusDropdown(queue);
  highlightPriorityRows(queue);

  const settings = privateBook.insertSheet(TAB.SETTINGS);
  settings.getRange(1, 1, 5, 3).setValues([
    ['setting', 'value', 'what it does'],
    ['auto_publish', true, 'TRUE publishes new reports straight away. FALSE saves them as Held.'],
    ['max_live_per_hour', 20, 'Past this many in an hour, new reports are saved as Held.'],
    ['public_workbook', publicBook.getUrl(), 'The public sheet.'],
    ['submit_token', token, 'Copy into Streamlit secrets. Keep private.'],
  ]);

  props.setProperties({
    PUBLIC_ID: publicBook.getId(),
    PRIVATE_ID: privateBook.getId(),
    SUBMIT_TOKEN: token,
    NEXT_ID: '1',
    ALLOW_SEED: 'true',
  });

  ScriptApp.newTrigger('onReviewEdit').forSpreadsheet(privateBook.getId()).onEdit().create();

  console.log('Public workbook: ' + publicBook.getUrl());
  console.log('Private workbook: ' + privateBook.getUrl());
}

function startTab(sheet, columns) {
  sheet.getRange(1, 1, 1, columns.length).setValues([columns]).setFontWeight('bold');
  sheet.getRange(1, 1, sheet.getMaxRows(), columns.length).setNumberFormat('@');
  sheet.setFrozenRows(1);
  return sheet;
}

function addStatusDropdown(queue) {
  const column = QUEUE_COLUMNS.indexOf('review_status') + 1;
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(Object.values(STATUS), true)
    .setAllowInvalid(false)
    .build();
  queue.getRange(2, column, QUEUE_ROWS_WITH_DROPDOWN, 1).setDataValidation(rule);
}

function highlightPriorityRows(queue) {
  const rule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$F2<>""')
    .setBackground('#fde8e8')
    .setRanges([queue.getRange(2, 1, QUEUE_ROWS_WITH_DROPDOWN, QUEUE_COLUMNS.length)])
    .build();
  queue.setConditionalFormatRules([rule]);
}

/** The web app's entry point. Every request needs the shared token. */
function doPost(e) {
  const props = PropertiesService.getScriptProperties();
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (error) {
    return reply({ ok: false, error: 'bad request' });
  }
  if (!body.token || body.token !== props.getProperty('SUBMIT_TOKEN')) {
    return reply({ ok: false, error: 'not authorised' });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    if (body.kind === 'ping') return reply({ ok: true });
    if (body.kind === 'submission') return reply(saveSubmission(body, props));
    if (body.kind === 'correction') return reply(saveCorrection(body));
    if (body.kind === 'seed') return reply(loadSeed(body, props));
    return reply({ ok: false, error: 'unknown request' });
  } finally {
    lock.releaseLock();
  }
}

function reply(result) {
  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

function saveSubmission(body, props) {
  const cache = CacheService.getScriptCache();
  const nonceKey = 'nonce:' + body.nonce;
  const earlier = cache.get(nonceKey);
  if (earlier) return JSON.parse(earlier);

  const record = cleanRecord(body.public || {});
  const repeatKey = 'repeat:' + fingerprint(record);
  const repeat = cache.get(repeatKey);
  if (repeat) return JSON.parse(repeat);

  const id = nextRecordId(props);
  const status = decideStatus(cache);
  const privateFields = body.private || {};
  const priority = needsPriority(record, privateFields);
  record.record_id = id;
  const row = PUBLIC_COLUMNS.map((column) => record[column] || '');

  appendSafe(privateTab(TAB.SUBMISSIONS), [
    new Date(), ...row,
    limit(privateFields.original_details, MAX_TEXT_LENGTH),
    limit(privateFields.contact, MAX_FIELD_LENGTH),
  ]);
  appendSafe(privateTab(TAB.QUEUE), [
    id, record.employer_name, record.state, new Date(), status, priority ? 'yes' : '', '', '', '',
  ]);
  if (status === STATUS.LIVE) {
    appendSafe(publicTab(), row);
  }

  notify(
    (priority ? 'PRIORITY: ' : '') + 'New report: ' + record.employer_name,
    [
      'Status: ' + status,
      'Reference: ' + id,
      'Employer: ' + record.employer_name,
      'Location: ' + [record.city, record.state].filter(Boolean).join(', '),
      '',
      record.report_description,
      '',
      'Review Queue: ' + privateBook().getUrl(),
    ]
  );

  const result = { ok: true, record_id: id, status: status };
  cache.put(nonceKey, JSON.stringify(result), NONCE_SECONDS);
  cache.put(repeatKey, JSON.stringify(result), REPEAT_SECONDS);
  return result;
}

/** Keeps only public columns, so nothing else can reach the public tab. */
function cleanRecord(input) {
  const record = {};
  PUBLIC_COLUMNS.forEach((column) => {
    const size = column === 'report_description' ? MAX_TEXT_LENGTH : MAX_FIELD_LENGTH;
    const value = limit(input[column], size);
    record[column] = MASKED_COLUMNS.includes(column) ? maskContacts(value) : value;
  });
  if (!SUBMITTABLE_STATUSES.includes(record.verification_status)) {
    record.verification_status = 'unverified';
  }
  record.review_state = 'unreviewed';
  return record;
}

function limit(value, size) {
  return String(value === undefined || value === null ? '' : value).trim().slice(0, size);
}

function maskContacts(text) {
  return text.replace(EMAIL_PATTERN, '[email removed]').replace(PHONE_PATTERN, '[number removed]');
}

function needsPriority(record, privateFields) {
  return PRIORITY_PATTERN.test(record.report_description + ' ' + (privateFields.original_details || ''));
}

function fingerprint(record) {
  const text = (record.employer_name + '|' + record.report_description).toLowerCase();
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, text);
  return Utilities.base64Encode(digest);
}

function nextRecordId(props) {
  const number = Number(props.getProperty('NEXT_ID') || '1');
  props.setProperty('NEXT_ID', String(number + 1));
  return 'S-' + String(number).padStart(4, '0');
}

function decideStatus(cache) {
  const settings = readSettings();
  if (!settings.auto_publish) return STATUS.HELD;

  const hour = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMddHH');
  const key = 'live:' + hour;
  const count = Number(cache.get(key) || 0);
  if (count >= settings.max_live_per_hour) return STATUS.HELD;
  cache.put(key, String(count + 1), 7200);
  return STATUS.LIVE;
}

function readSettings() {
  const values = {};
  privateTab(TAB.SETTINGS).getDataRange().getValues().forEach((row) => {
    values[row[0]] = row[1];
  });
  return {
    auto_publish: String(values.auto_publish).toUpperCase() !== 'FALSE',
    max_live_per_hour: Number(values.max_live_per_hour) || 20,
  };
}

function saveCorrection(body) {
  const fields = body.private || {};
  const id = limit(fields.record_id, MAX_FIELD_LENGTH);
  appendSafe(privateTab(TAB.CORRECTIONS), [
    new Date(), id,
    limit(fields.role, MAX_FIELD_LENGTH),
    limit(fields.problem, MAX_TEXT_LENGTH),
    limit(fields.proposed, MAX_TEXT_LENGTH),
    limit(fields.evidence, MAX_FIELD_LENGTH),
    limit(fields.contact, MAX_FIELD_LENGTH),
    'New', '',
  ]);
  notify('Correction request: ' + (id || 'no reference given'), [
    limit(fields.problem, MAX_TEXT_LENGTH),
    '',
    'Corrections tab: ' + privateBook().getUrl(),
  ]);
  return { ok: true };
}

/** Installable trigger: changing a status in the Review Queue takes effect here. */
function onReviewEdit(e) {
  const sheet = e.range.getSheet();
  if (sheet.getName() !== TAB.QUEUE) return;

  const statusColumn = QUEUE_COLUMNS.indexOf('review_status') + 1;
  if (e.range.getColumn() > statusColumn || e.range.getLastColumn() < statusColumn) return;

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    for (let row = Math.max(e.range.getRow(), 2); row <= e.range.getLastRow(); row++) {
      applyQueueRow(sheet, row, statusColumn);
    }
  } finally {
    lock.releaseLock();
  }
}

function applyQueueRow(sheet, row, statusColumn) {
  const id = String(sheet.getRange(row, 1).getValue());
  const status = String(sheet.getRange(row, statusColumn).getValue());
  if (!id || !Object.values(STATUS).includes(status)) return;

  const decision = sheet.getRange(row, QUEUE_COLUMNS.indexOf('decision') + 1).getValue();
  applyStatus(id, status, decision);
  sheet.getRange(row, QUEUE_COLUMNS.indexOf('reviewed_at') + 1).setValue(new Date());
}

/** Makes the public tab agree with a record's status. */
function applyStatus(id, status, reason) {
  const directory = publicTab();
  const publicRow = findRow(directory, id);

  if (OFF_SITE.includes(status)) {
    if (publicRow) {
      const values = directory.getRange(publicRow, 1, 1, PUBLIC_COLUMNS.length).getValues()[0];
      appendSafe(privateTab(TAB.REMOVED), [...values, new Date(), status, reason]);
      directory.deleteRow(publicRow);
    }
    return;
  }

  const restoredRow = publicRow || restoreRecord(id);
  if (!restoredRow) return;
  const reviewState = status === STATUS.REVIEWED ? 'reviewed' : 'unreviewed';
  setPublicValue(directory, restoredRow, 'review_state', reviewState);
  setPublicValue(directory, restoredRow, 'last_updated', today());
}

function restoreRecord(id) {
  const removed = privateTab(TAB.REMOVED);
  const removedRow = findRow(removed, id);
  if (removedRow) {
    const values = removed.getRange(removedRow, 1, 1, PUBLIC_COLUMNS.length).getValues()[0];
    removed.deleteRow(removedRow);
    appendSafe(publicTab(), values);
    return publicTab().getLastRow();
  }

  const submissions = privateTab(TAB.SUBMISSIONS);
  const submissionRow = findRow(submissions, id, 2);
  if (!submissionRow) return 0;
  const values = submissions.getRange(submissionRow, 2, 1, PUBLIC_COLUMNS.length).getValues()[0];
  appendSafe(publicTab(), values);
  return publicTab().getLastRow();
}

function setPublicValue(directory, row, column, value) {
  directory.getRange(row, PUBLIC_COLUMNS.indexOf(column) + 1).setValue(value);
}

function findRow(sheet, id, column) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return 0;
  const values = sheet.getRange(2, column || 1, lastRow - 1, 1).getValues();
  const index = values.findIndex((row) => String(row[0]) === String(id));
  return index === -1 ? 0 : index + 2;
}

/** One-time import of the existing data. Closes itself once used. */
function loadSeed(body, props) {
  if (props.getProperty('ALLOW_SEED') !== 'true') {
    return { ok: false, error: 'seed is closed' };
  }
  writeRows(publicTab(), body.public);
  writeRows(privateTab(TAB.QUEUE), body.queue);
  writeRows(privateTab(TAB.ARCHIVE), body.archive);
  props.deleteProperty('ALLOW_SEED');
  return { ok: true, public: body.public.length, queue: body.queue.length, archive: body.archive.length };
}

function writeRows(sheet, rows) {
  const start = sheet.getLastRow() + 1;
  const cleaned = rows.map((row) => row.map(safeCell));
  sheet.getRange(start, 1, cleaned.length, cleaned[0].length).setValues(cleaned);
}

function appendSafe(sheet, row) {
  sheet.appendRow(row.map(safeCell));
}

/**
 * Sheets runs text starting with these characters as a formula, so a report
 * beginning "=IMPORTXML(...)" could send data elsewhere. The leading apostrophe
 * makes Sheets store it as plain text.
 */
function safeCell(value) {
  if (typeof value === 'string' && /^[=+\-@]/.test(value)) return "'" + value;
  return value;
}

function today() {
  return Utilities.formatDate(new Date(), 'UTC', 'yyyy-MM-dd');
}

function notify(subject, lines) {
  try {
    MailApp.sendEmail(Session.getEffectiveUser().getEmail(), subject, lines.join('\n'));
  } catch (error) {
    console.error('Could not send alert: ' + error);
  }
}

function privateBook() {
  const id = PropertiesService.getScriptProperties().getProperty('PRIVATE_ID');
  return SpreadsheetApp.openById(id);
}

function privateTab(name) {
  return privateBook().getSheetByName(name);
}

function publicTab() {
  const id = PropertiesService.getScriptProperties().getProperty('PUBLIC_ID');
  return SpreadsheetApp.openById(id).getSheetByName(TAB.PUBLIC);
}
