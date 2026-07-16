# Emulo Autopilot Session Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect stable supported session files and stage privacy-bounded local inbox records whose persisted bytes contain receipt hashes and timing metadata but no raw or redacted message text.

**Architecture:** Extend the frozen Autopilot contracts and atomic store with checkpoint and inbox records, then add a scanner that reuses Emulo's existing source discovery, human-turn filtering, and redaction. Stability requires two identical file observations separated by a configurable interval and a matching post-read stat. The scanner returns bounded redacted text only in memory; persisted state is metadata-only and idempotent.

**Tech Stack:** Python 3.8+ standard library, existing `emulo.py` source adapters, `unittest`.

---

## Locked boundaries

- No daemon, CLI, model invocation, profile mutation, MCP mutation, cloud call, or billing behavior.
- Session text is never written under `EMULO_HOME/autopilot`.
- Checkpoints contain a path hash, never a filesystem path.
- Assistant messages and injected control envelopes remain excluded by existing `emulo.user_messages` behavior.
- Every message is redacted before hashing or entering the transient in-memory packet.
- The scanner refuses symlinks/reparse points and detects changes that occur during reading.
- OpenCode virtual session paths observe the physical `opencode.db` file but keep the existing virtual session ID for human-turn extraction.

## Record contracts

Checkpoint:

```json
{
  "schema_version": "emulo.autopilot-checkpoint/v1",
  "path_hash": "<64 lowercase hex>",
  "source": "codex",
  "identity": {"size": 1234, "mtime_ns": 1784192400000000000},
  "unchanged_since": 1784192400,
  "processed_fingerprint": null
}
```

Inbox:

```json
{
  "schema_version": "emulo.autopilot-inbox/v1",
  "inbox_id": "inbox_<20 lowercase hex>",
  "session_id": "<16 lowercase hex>",
  "source": "codex",
  "session_fingerprint": "<64 lowercase hex>",
  "receipts": [
    {
      "receipt_id": "rcpt_<20 lowercase hex>",
      "session_id": "<16 lowercase hex>",
      "message_sha256": "<64 lowercase hex>",
      "observed_at": "2026-07-16T00:00:00Z",
      "time_stratum": "2026-07"
    }
  ],
  "message_count": 1,
  "truncated_message_count": 0,
  "created_at": "2026-07-16T10:00:00Z"
}
```

Inbox identity is SHA-256 over canonical content excluding `inbox_id` and `created_at`.

### Task 1: Checkpoint and inbox contracts

**Files:**
- Modify: `emulo_autopilot/contracts.py`
- Modify: `tests/test_autopilot_contracts.py`

- [x] **Step 1: Write failing contract tests**

Add valid builders inside the test module and test exact-key validation, real integer requirements, supported sources, path and message hashes, matching receipt session IDs, sorted unique receipts, count consistency, time-stratum consistency, and content-bound inbox identity. Add explicit rejection tests for `path`, `text`, `quote`, and `redacted_text` keys anywhere in persisted records.

```python
def test_inbox_rejects_persisted_text(self):
    inbox = inbox_fixture()
    inbox["receipts"][0]["redacted_text"] = "do not persist me"
    with self.assertRaisesRegex(ValueError, "receipt keys"):
        contracts.validate_inbox(inbox)
```

- [x] **Step 2: Run and verify red state**

Run: `python -m unittest tests.test_autopilot_contracts -v`

Expected: FAIL because checkpoint/inbox validators do not exist.

- [x] **Step 3: Implement exact validators and identity**

Add:

```python
CHECKPOINT_SCHEMA = "emulo.autopilot-checkpoint/v1"
INBOX_SCHEMA = "emulo.autopilot-inbox/v1"
SOURCES = frozenset({"codex", "claude", "copilot", "opencode", "antigravity", "custom"})

def inbox_identity(inbox):
    identity = {key: value for key, value in inbox.items()
                if key not in {"inbox_id", "created_at"}}
    return "inbox_" + sha256_text(canonical_json(identity))[:20]

def validate_checkpoint(value):
    value = _mapping(copy.deepcopy(value), "checkpoint")
    _exact_keys(value, {"schema_version", "path_hash", "source", "identity",
                        "unchanged_since", "processed_fingerprint"}, "checkpoint")
    if value["schema_version"] != CHECKPOINT_SCHEMA:
        raise ValueError("unsupported checkpoint schema")
    _identifier(value["path_hash"], "sha256", "checkpoint path_hash")
    if value["source"] not in SOURCES:
        raise ValueError("checkpoint source is invalid")
    identity = _mapping(value["identity"], "checkpoint identity")
    _exact_keys(identity, {"size", "mtime_ns"}, "checkpoint identity")
    for key in ("size", "mtime_ns"):
        if isinstance(identity[key], bool) or not isinstance(identity[key], int) or identity[key] < 0:
            raise ValueError("checkpoint identity is invalid")
    if isinstance(value["unchanged_since"], bool) or not isinstance(value["unchanged_since"], int) \
            or value["unchanged_since"] < 0:
        raise ValueError("checkpoint unchanged_since is invalid")
    if value["processed_fingerprint"] is not None:
        _identifier(value["processed_fingerprint"], "sha256", "processed_fingerprint")
    return value

def validate_inbox(value):
    value = _mapping(copy.deepcopy(value), "inbox")
    _exact_keys(value, {"schema_version", "inbox_id", "session_id", "source",
                        "session_fingerprint", "receipts", "message_count",
                        "truncated_message_count", "created_at"}, "inbox")
    if value["schema_version"] != INBOX_SCHEMA:
        raise ValueError("unsupported inbox schema")
    if not re.fullmatch(r"inbox_[a-f0-9]{20}", value["inbox_id"] or ""):
        raise ValueError("inbox_id is invalid")
    _identifier(value["session_id"], "session", "inbox session_id")
    if value["source"] not in SOURCES:
        raise ValueError("inbox source is invalid")
    _identifier(value["session_fingerprint"], "sha256", "session_fingerprint")
    if not isinstance(value["receipts"], list) or not value["receipts"]:
        raise ValueError("inbox receipts are invalid")
    receipt_ids = []
    for receipt in value["receipts"]:
        receipt = _mapping(receipt, "inbox receipt")
        _exact_keys(receipt, {"receipt_id", "session_id", "message_sha256",
                              "observed_at", "time_stratum"}, "inbox receipt")
        _identifier(receipt["receipt_id"], "receipt", "receipt_id")
        _identifier(receipt["message_sha256"], "sha256", "message_sha256")
        if receipt["session_id"] != value["session_id"]:
            raise ValueError("receipt session_id does not match inbox")
        _timestamp(receipt["observed_at"], "receipt observed_at")
        if receipt["time_stratum"] != receipt["observed_at"][:7]:
            raise ValueError("receipt time_stratum does not match observed_at")
        receipt_ids.append(receipt["receipt_id"])
    if receipt_ids != sorted(set(receipt_ids)):
        raise ValueError("receipt IDs must be sorted and unique")
    for key in ("message_count", "truncated_message_count"):
        if isinstance(value[key], bool) or not isinstance(value[key], int) or value[key] < 0:
            raise ValueError(key + " is invalid")
    if value["message_count"] != len(value["receipts"]):
        raise ValueError("message_count does not match receipts")
    _timestamp(value["created_at"], "inbox created_at")
    if value["inbox_id"] != inbox_identity(value):
        raise ValueError("inbox_id does not match content")
    return value
```

- [x] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_autopilot_contracts -v`

Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add emulo_autopilot/contracts.py tests/test_autopilot_contracts.py
git commit -m "feat: define private Autopilot inbox contracts"
```

### Task 2: Atomic checkpoint and inbox persistence

**Files:**
- Modify: `emulo_autopilot/store.py`
- Modify: `tests/test_autopilot_store.py`

- [x] **Step 1: Write failing persistence tests**

Test missing checkpoint, round-trip checkpoint, changed checkpoint overwrite, corrupt checkpoint failure, idempotent inbox write, conflicting same-ID bytes, sorted inbox listing, and a recursive byte scan proving seeded raw/redacted phrases do not appear anywhere under the Autopilot root.

- [x] **Step 2: Run and verify red state**

Run: `python -m unittest tests.test_autopilot_store -v`

Expected: FAIL because checkpoint/inbox store methods do not exist.

- [x] **Step 3: Implement checkpoint and inbox methods**

```python
    def checkpoint_path(self, path_hash):
        if not re.fullmatch(r"[a-f0-9]{64}", path_hash or ""):
            raise ValueError("path_hash is invalid")
        return self._child("checkpoints", path_hash + ".json")

    def get_checkpoint(self, path_hash):
        path = self.checkpoint_path(path_hash)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                return validate_checkpoint(json.load(handle))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("checkpoint is corrupt") from exc

    def put_checkpoint(self, checkpoint):
        checkpoint = validate_checkpoint(checkpoint)
        return self.atomic_write_json(self.checkpoint_path(checkpoint["path_hash"]), checkpoint)

    def put_inbox(self, inbox):
        inbox = validate_inbox(inbox)
        path = self._child("inbox", inbox["inbox_id"] + ".json")
        expected = (canonical_json(inbox) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing inbox bytes do not match identity")
            return path
        return self.atomic_write_json(path, inbox)

    def list_inbox(self):
        self.initialize()
        values = []
        for name in os.listdir(self._child("inbox")):
            if not re.fullmatch(r"inbox_[a-f0-9]{20}\.json", name):
                raise ValueError("unexpected inbox file")
            with open(self._child("inbox", name), "r", encoding="utf-8", errors="strict") as handle:
                values.append(validate_inbox(json.load(handle)))
        return sorted(values, key=lambda item: item["inbox_id"])
```

Add `checkpoints` to the exact initialized directory set. Import the new validators.

- [x] **Step 4: Run store and contract tests**

Run: `python -m unittest tests.test_autopilot_store tests.test_autopilot_contracts -v`

Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add emulo_autopilot/store.py tests/test_autopilot_store.py
git commit -m "feat: persist private Autopilot inbox metadata"
```

### Task 3: Stable-session scanner

**Files:**
- Create: `emulo_autopilot/sessions.py`
- Create: `tests/test_autopilot_sessions.py`

- [ ] **Step 1: Write failing scanner tests**

Use real temporary Codex/Claude JSONL fixtures. Test first observation pending, unchanged second observation before/after threshold, changed file resets stability, file change during read rejected through an injectable reader, processed fingerprint idempotency, assistant/injected messages excluded, secret redaction before hashes and transient text, metadata-only persisted inbox, 2,000-character per-message cap, 64-KiB total cap, undated fallback to file mtime, and OpenCode physical-path resolution.

- [ ] **Step 2: Run and verify red state**

Run: `python -m unittest tests.test_autopilot_sessions -v`

Expected: FAIL because `emulo_autopilot.sessions` does not exist.

- [ ] **Step 3: Implement observation and bounded receipts**

Public API:

```python
import collections
import datetime
import os
import stat
import time

import emulo

from . import contracts


ScanResult = collections.namedtuple("ScanResult", "state inbox transient_messages")

def physical_session_path(session_path):
    if emulo.OPENCODE_DB_SESSION_SEP in session_path:
        database, _, session_id = session_path.rpartition(emulo.OPENCODE_DB_SESSION_SEP)
        if database.endswith("opencode.db") and session_id:
            return database
    return session_path

def path_hash(session_path):
    physical = physical_session_path(session_path)
    normalized = os.path.normcase(os.path.realpath(os.path.abspath(physical)))
    if physical != session_path:
        _, _, session_id = session_path.rpartition(emulo.OPENCODE_DB_SESSION_SEP)
        normalized += emulo.OPENCODE_DB_SESSION_SEP + session_id
    return contracts.sha256_text(normalized)

def _file_state(session_path):
    physical = physical_session_path(session_path)
    info = os.lstat(physical)
    is_reparse = bool(
        hasattr(info, "st_file_attributes")
        and info.st_file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )
    if stat.S_ISLNK(info.st_mode) or is_reparse or not stat.S_ISREG(info.st_mode):
        raise ValueError("session path must be a regular file, not a link or reparse point")
    return physical, {"size": info.st_size, "mtime_ns": info.st_mtime_ns}

def _utc_seconds(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))

def _observed_at(date_value, fallback_epoch):
    try:
        datetime.datetime.strptime(date_value, "%Y-%m-%d")
        return date_value + "T00:00:00Z"
    except (TypeError, ValueError):
        return time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(fallback_epoch))

def _fit_utf8(text, maximum_bytes):
    payload = text.encode("utf-8")
    if len(payload) <= maximum_bytes:
        return text, False
    payload = payload[:maximum_bytes]
    while payload:
        try:
            return payload.decode("utf-8", errors="strict"), True
        except UnicodeDecodeError:
            payload = payload[:-1]
    return "", True

class SessionScanner:
    def __init__(self, store, stable_seconds=120, clock=time.time, reader=emulo.user_messages):
        if isinstance(stable_seconds, bool) or not isinstance(stable_seconds, int) \
                or stable_seconds < 1:
            raise ValueError("stable_seconds must be a positive integer")
        self.store = store
        self.stable_seconds = stable_seconds
        self.clock = clock
        self.reader = reader

    def scan_path(self, session_path):
        physical, identity = _file_state(session_path)
        now = int(self.clock())
        checkpoint_hash = path_hash(session_path)
        source = emulo.source_kind(session_path)
        previous = self.store.get_checkpoint(checkpoint_hash)
        if previous is None or previous["identity"] != identity:
            checkpoint = {
                "schema_version": contracts.CHECKPOINT_SCHEMA,
                "path_hash": checkpoint_hash,
                "source": source,
                "identity": identity,
                "unchanged_since": now,
                "processed_fingerprint": None,
            }
            self.store.put_checkpoint(checkpoint)
            state = "pending" if previous is None else "changed"
            return ScanResult(state, None, [])
        if now - previous["unchanged_since"] < self.stable_seconds:
            return ScanResult("pending", None, [])

        messages = self.reader(session_path)
        _, after_identity = _file_state(session_path)
        if after_identity != identity:
            checkpoint = dict(
                previous,
                identity=after_identity,
                unchanged_since=now,
                processed_fingerprint=None,
            )
            self.store.put_checkpoint(checkpoint)
            return ScanResult("changed", None, [])

        session_id = emulo.stable_session_id(session_path)
        fallback_epoch = identity["mtime_ns"] // 1_000_000_000
        remaining = 65_536
        truncated = 0
        receipts = []
        transient = []
        for ordinal, (date_value, text) in enumerate(messages):
            redacted = emulo.redact((text or "").strip())
            if not redacted:
                continue
            was_truncated = False
            if len(redacted) > 2_000:
                redacted = redacted[:2_000]
                was_truncated = True
            bounded, byte_truncated = _fit_utf8(redacted, remaining)
            if byte_truncated:
                was_truncated = True
            if was_truncated:
                truncated += 1
            if not bounded:
                continue
            remaining -= len(bounded.encode("utf-8"))
            observed_at = _observed_at(date_value, fallback_epoch)
            message_sha = contracts.sha256_text(bounded)
            receipt_identity = {
                "session_id": session_id,
                "ordinal": ordinal,
                "message_sha256": message_sha,
                "observed_at": observed_at,
            }
            receipt_id = "rcpt_" + contracts.sha256_text(
                contracts.canonical_json(receipt_identity)
            )[:20]
            receipts.append({
                "receipt_id": receipt_id,
                "session_id": session_id,
                "message_sha256": message_sha,
                "observed_at": observed_at,
                "time_stratum": observed_at[:7],
            })
            transient.append({"receipt_id": receipt_id, "text": bounded})

        receipts.sort(key=lambda item: item["receipt_id"])
        fingerprint_identity = {
            "identity": identity,
            "receipt_ids": [item["receipt_id"] for item in receipts],
        }
        fingerprint = contracts.sha256_text(
            contracts.canonical_json(fingerprint_identity)
        )
        if previous["processed_fingerprint"] == fingerprint:
            return ScanResult("processed", None, [])

        checkpoint = dict(previous, processed_fingerprint=fingerprint)
        if not receipts:
            self.store.put_checkpoint(checkpoint)
            return ScanResult("empty", None, [])

        inbox = {
            "schema_version": contracts.INBOX_SCHEMA,
            "inbox_id": "",
            "session_id": session_id,
            "source": source,
            "session_fingerprint": fingerprint,
            "receipts": receipts,
            "message_count": len(receipts),
            "truncated_message_count": truncated,
            "created_at": _utc_seconds(previous["unchanged_since"]),
        }
        inbox["inbox_id"] = contracts.inbox_identity(inbox)
        self.store.put_inbox(inbox)
        self.store.put_checkpoint(checkpoint)
        return ScanResult("ready", inbox, transient)
```

States are exactly `pending`, `changed`, `empty`, `processed`, and `ready`.

Message rules:

- `redacted = emulo.redact(text.strip())[:2000]`;
- total UTF-8 bytes added to transient messages cannot exceed `65536`;
- truncated messages increment `truncated_message_count`;
- observed date uses the valid message `YYYY-MM-DD`, otherwise the physical file mtime UTC date;
- `message_sha256` hashes the bounded redacted message;
- `receipt_id` hashes canonical `{session_id, ordinal, message_sha256, observed_at}`;
- session fingerprint hashes canonical physical identity plus sorted receipt IDs;
- receipt metadata sorts by receipt ID before inbox identity;
- transient messages return in original human-turn order and are never passed to store methods.

- [ ] **Step 4: Run source and privacy regressions**

Run:

```powershell
python -m unittest tests.test_autopilot_sessions tests.test_autopilot_store tests.test_claude_human_turns tests.test_codex_control_envelopes tests.test_antigravity_source tests.test_opencode_source -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite and commit**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass; existing Windows symlink skips may remain.

```powershell
git add emulo_autopilot/sessions.py tests/test_autopilot_sessions.py
git commit -m "feat: detect stable sessions for Autopilot"
```

## Completion gate

- All existing and new tests pass.
- A stable real-format synthetic session produces one inbox record exactly once.
- No persisted checkpoint/inbox bytes contain a path, raw message, or redacted message.
- An active/changing file cannot produce an inbox record.
- Assistant and injected text remain excluded.
- Redaction occurs before receipt hashes and transient packet exposure.
- No benchmark, site, video, MCP, profile activation, cloud, or billing file changes.
