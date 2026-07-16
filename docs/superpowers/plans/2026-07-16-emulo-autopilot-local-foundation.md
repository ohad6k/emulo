# Emulo Autopilot Contract Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the strict, atomic local contract foundation for evidence-bound Autopilot candidates, append-only founder decisions, generation manifests, and conservative policy classification.

**Architecture:** Add a focused `emulo_autopilot` stdlib-only package beside the existing one-file `emulo.py` runtime. This plan freezes strict record contracts, writes immutable candidates and decisions under `EMULO_HOME/autopilot`, and classifies candidates without activating anything. Session detection, activation, MCP exposure, cloud sync, and billing consume these contracts in later plans.

**Tech Stack:** Python 3.8+ standard library, `unittest`, existing Emulo atomic/private-path helpers, setuptools console scripts.

---

## Scope and sequence

This is plan 1 of 4:

1. **This plan:** strict contracts, immutable local candidate/decision store, and pure policy engine.
2. **Next plan:** stable-session inbox, reviewed activation, MCP exposure, rollback, and JSON CLI.
3. **Cloud plan:** device keys, client-side encryption, sync API, D1 schema, and local control center.
4. **Revenue plan:** Polar billing adapter, entitlement state machine, provider sandbox verification, private-beta gates, and staged launch.

This contract plan produces independently testable software with no cloud account and no behavior change to the current Emulo runtime. Later plans must consume its versioned formats rather than bypassing them.

## File structure

- `emulo_autopilot/__init__.py`: public package version and supported schema identifiers.
- `emulo_autopilot/contracts.py`: strict validation, canonical JSON, IDs, and immutable record builders.
- `emulo_autopilot/store.py`: safe local paths, lock, atomic records, and append-only candidate decisions.
- `emulo_autopilot/policy.py`: deterministic safe/review/reject classification.
- `tests/test_autopilot_contracts.py`: record and schema rejection tests.
- `tests/autopilot_helpers.py`: canonical candidate fixture builder shared by focused tests.
- `tests/test_autopilot_store.py`: atomicity, append-only decisions, and locking tests.
- `tests/test_autopilot_policy.py`: exhaustive policy table.
- `pyproject.toml`: package discovery only; no public console entry point in this foundation plan.

## Locked record contracts

### Candidate

```json
{
  "schema_version": "emulo.autopilot-candidate/v1",
  "candidate_id": "cand_<20 lowercase hex>",
  "kind": "directive",
  "domain": "work",
  "statement": "Verify the live URL before claiming a deployment is complete.",
  "scope": ["shipping"],
  "evidence": [
    {
      "receipt_id": "rcpt_<20 lowercase hex>",
      "session_id": "<16 lowercase hex>",
      "observed_at": "2026-07-16T10:00:00Z",
      "time_stratum": "2026-07"
    }
  ],
  "contradiction_count": 0,
  "risk_categories": [],
  "source_packet_hash": "<64 lowercase hex>",
  "prompt_contract_version": "emulo.autopilot-candidate-prompt/v1",
  "created_at": "2026-07-16T10:01:00Z"
}
```

Candidate identity is the first 20 hex characters of SHA-256 over canonical JSON excluding `candidate_id` and `created_at`. Evidence stores hashes and time metadata, never raw quotes.

### Decision

```json
{
  "schema_version": "emulo.autopilot-decision/v1",
  "decision_id": "dec_<20 lowercase hex>",
  "candidate_id": "cand_<20 lowercase hex>",
  "decision": "approve",
  "reason": "founder-review",
  "policy_class": "review",
  "decided_at": "2026-07-16T10:02:00Z"
}
```

Decisions are append-only. A candidate can have multiple decisions, but only its newest valid decision controls activation. `activate` requires newest decision `approve`.

### Overlay generation

```json
{
  "schema_version": "emulo.autopilot-generation/v1",
  "generation_id": "gen_<20 lowercase hex>",
  "parent_generation_id": null,
  "operation": "activate",
  "candidate_ids": ["cand_<20 lowercase hex>"],
  "domains": {
    "work": {
      "artifact": "work.md",
      "sha256": "<64 lowercase hex>"
    }
  },
  "created_at": "2026-07-16T10:03:00Z"
}
```

`head.json` contains only schema version and current generation ID. Rollback creates a new generation with `operation: rollback`; it never repoints history to hide an activation.

---

### Task 1: Package and strict contracts

**Files:**
- Create: `emulo_autopilot/__init__.py`
- Create: `emulo_autopilot/contracts.py`
- Create: `tests/autopilot_helpers.py`
- Create: `tests/test_autopilot_contracts.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing package and contract tests**

Create `tests/autopilot_helpers.py` with this exact reusable builder, then create tests that import the package, validate the resulting candidate, and reject extra keys, uppercase hashes, assistant evidence, unsupported kinds/domains, duplicate receipt IDs, non-UTC timestamps, raw quote fields, traversal-like artifact names, and candidate IDs that do not match canonical content.

```python
from emulo_autopilot import contracts


def candidate_fixture(evidence=3, strata=2, contradiction_count=0,
                      risk_categories=None, kind="directive", statement=None):
    receipts = []
    for index in range(evidence):
        month = 6 + (index % max(strata, 1))
        receipts.append({
            "receipt_id": "rcpt_" + format(index + 1, "020x"),
            "session_id": format(index + 1, "016x"),
            "observed_at": "2026-{0:02d}-16T10:00:00Z".format(month),
            "time_stratum": "2026-{0:02d}".format(month),
        })
    candidate = {
        "schema_version": contracts.CANDIDATE_SCHEMA,
        "candidate_id": "",
        "kind": kind,
        "domain": "work",
        "statement": statement or "Verify the live URL before claiming deployment is complete.",
        "scope": ["shipping"],
        "evidence": receipts,
        "contradiction_count": contradiction_count,
        "risk_categories": sorted(risk_categories or []),
        "source_packet_hash": "a" * 64,
        "prompt_contract_version": "emulo.autopilot-candidate-prompt/v1",
        "created_at": "2026-07-16T10:01:00Z",
    }
    candidate["candidate_id"] = contracts.candidate_identity(candidate)
    return candidate
```

```python
class CandidateContractTest(unittest.TestCase):
    def test_candidate_identity_is_content_bound(self):
        candidate = candidate_fixture()
        validated = contracts.validate_candidate(candidate)
        self.assertEqual(candidate, validated)

        changed = dict(candidate, statement="different")
        with self.assertRaisesRegex(ValueError, "candidate_id"):
            contracts.validate_candidate(changed)

    def test_raw_quote_is_rejected(self):
        candidate = candidate_fixture()
        candidate["evidence"] = [dict(candidate["evidence"][0], quote="private text")]
        with self.assertRaisesRegex(ValueError, "evidence keys"):
            contracts.validate_candidate(candidate)
```

- [ ] **Step 2: Run tests and verify import failure**

Run: `python -m unittest tests.test_autopilot_contracts -v`

Expected: FAIL because `emulo_autopilot` does not exist.

- [ ] **Step 3: Implement strict stdlib-only contracts**

Implement these public callables with exact-key validation and no permissive coercion. Keep the helper bodies in this task so later modules consume one contract implementation:

```python
import copy
import datetime
import hashlib
import json
import re

CANDIDATE_SCHEMA = "emulo.autopilot-candidate/v1"
DECISION_SCHEMA = "emulo.autopilot-decision/v1"
GENERATION_SCHEMA = "emulo.autopilot-generation/v1"
HEAD_SCHEMA = "emulo.autopilot-head/v1"
INBOX_SCHEMA = "emulo.autopilot-inbox/v1"
KINDS = frozenset({"directive", "correction", "preference", "workflow", "retirement"})
DOMAINS = frozenset({"work", "design", "write", "video"})
ID_PATTERNS = {
    "candidate": re.compile(r"^cand_[a-f0-9]{20}$"),
    "decision": re.compile(r"^dec_[a-f0-9]{20}$"),
    "generation": re.compile(r"^gen_[a-f0-9]{20}$"),
    "receipt": re.compile(r"^rcpt_[a-f0-9]{20}$"),
    "session": re.compile(r"^[a-f0-9]{16}$"),
    "sha256": re.compile(r"^[a-f0-9]{64}$"),
}

def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object")
    return value

def _exact_keys(value, expected, label):
    if set(value) != set(expected):
        raise ValueError(label + " keys are invalid")

def _string(value, label, minimum=1, maximum=2048):
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(label + " must be a bounded string")
    return value

def _identifier(value, kind, label):
    if not isinstance(value, str) or not ID_PATTERNS[kind].fullmatch(value):
        raise ValueError(label + " is invalid")
    return value

def _timestamp(value, label):
    _string(value, label, 20, 20)
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(label + " must be UTC seconds") from exc
    return value

def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def candidate_identity(candidate):
    identity = {key: value for key, value in candidate.items()
                if key not in {"candidate_id", "created_at"}}
    return "cand_" + sha256_text(canonical_json(identity))[:20]

def validate_candidate(value):
    value = _mapping(copy.deepcopy(value), "candidate")
    keys = {
        "schema_version", "candidate_id", "kind", "domain", "statement", "scope",
        "evidence", "contradiction_count", "risk_categories", "source_packet_hash",
        "prompt_contract_version", "created_at",
    }
    _exact_keys(value, keys, "candidate")
    if value["schema_version"] != CANDIDATE_SCHEMA:
        raise ValueError("unsupported candidate schema")
    _identifier(value["candidate_id"], "candidate", "candidate_id")
    if value["kind"] not in KINDS:
        raise ValueError("candidate kind is invalid")
    if value["domain"] not in DOMAINS:
        raise ValueError("candidate domain is invalid")
    _string(value["statement"], "candidate statement", 1, 2000)
    if not isinstance(value["scope"], list) or len(value["scope"]) > 16:
        raise ValueError("candidate scope is invalid")
    if any(not isinstance(item, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", item)
           for item in value["scope"]):
        raise ValueError("candidate scope item is invalid")
    if value["scope"] != sorted(set(value["scope"])):
        raise ValueError("candidate scope must be sorted and unique")
    if not isinstance(value["evidence"], list) or not 1 <= len(value["evidence"]) <= 64:
        raise ValueError("candidate evidence is invalid")
    receipts = set()
    for evidence in value["evidence"]:
        evidence = _mapping(evidence, "candidate evidence")
        _exact_keys(evidence, {"receipt_id", "session_id", "observed_at", "time_stratum"},
                    "candidate evidence")
        _identifier(evidence["receipt_id"], "receipt", "receipt_id")
        _identifier(evidence["session_id"], "session", "session_id")
        _timestamp(evidence["observed_at"], "evidence observed_at")
        if evidence["time_stratum"] != evidence["observed_at"][:7]:
            raise ValueError("evidence time_stratum does not match observed_at")
        if evidence["receipt_id"] in receipts:
            raise ValueError("duplicate receipt_id")
        receipts.add(evidence["receipt_id"])
    if isinstance(value["contradiction_count"], bool) or not isinstance(value["contradiction_count"], int) \
            or not 0 <= value["contradiction_count"] <= 1000:
        raise ValueError("contradiction_count is invalid")
    if not isinstance(value["risk_categories"], list) or len(value["risk_categories"]) > 16:
        raise ValueError("risk_categories is invalid")
    if any(not isinstance(item, str) or not re.fullmatch(r"[a-z][a-z-]{0,63}", item)
           for item in value["risk_categories"]):
        raise ValueError("risk category is invalid")
    if value["risk_categories"] != sorted(set(value["risk_categories"])):
        raise ValueError("risk_categories must be sorted and unique")
    _identifier(value["source_packet_hash"], "sha256", "source_packet_hash")
    if value["prompt_contract_version"] != "emulo.autopilot-candidate-prompt/v1":
        raise ValueError("unsupported prompt contract")
    _timestamp(value["created_at"], "candidate created_at")
    if value["candidate_id"] != candidate_identity(value):
        raise ValueError("candidate_id does not match content")
    return value

def validate_decision(value):
    value = _mapping(copy.deepcopy(value), "decision")
    _exact_keys(value, {"schema_version", "decision_id", "candidate_id", "decision",
                        "reason", "policy_class", "decided_at"}, "decision")
    if value["schema_version"] != DECISION_SCHEMA:
        raise ValueError("unsupported decision schema")
    _identifier(value["decision_id"], "decision", "decision_id")
    _identifier(value["candidate_id"], "candidate", "candidate_id")
    if value["decision"] not in {"approve", "reject"}:
        raise ValueError("decision is invalid")
    _string(value["reason"], "decision reason", 1, 200)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,199}", value["reason"]):
        raise ValueError("decision reason is invalid")
    if value["policy_class"] not in {"safe", "review", "reject"}:
        raise ValueError("policy_class is invalid")
    _timestamp(value["decided_at"], "decision decided_at")
    identity = {key: item for key, item in value.items() if key != "decision_id"}
    expected = "dec_" + sha256_text(canonical_json(identity))[:20]
    if value["decision_id"] != expected:
        raise ValueError("decision_id does not match content")
    return value

def validate_generation(value):
    value = _mapping(copy.deepcopy(value), "generation")
    _exact_keys(value, {"schema_version", "generation_id", "parent_generation_id", "operation",
                        "candidate_ids", "domains", "created_at"}, "generation")
    if value["schema_version"] != GENERATION_SCHEMA:
        raise ValueError("unsupported generation schema")
    _identifier(value["generation_id"], "generation", "generation_id")
    if value["parent_generation_id"] is not None:
        _identifier(value["parent_generation_id"], "generation", "parent_generation_id")
    if value["operation"] not in {"activate", "rollback"}:
        raise ValueError("generation operation is invalid")
    if not isinstance(value["candidate_ids"], list) or value["candidate_ids"] != sorted(set(value["candidate_ids"])):
        raise ValueError("candidate_ids must be sorted and unique")
    for candidate_id in value["candidate_ids"]:
        _identifier(candidate_id, "candidate", "generation candidate_id")
    domains = _mapping(value["domains"], "generation domains")
    if not set(domains).issubset(DOMAINS):
        raise ValueError("generation domain is invalid")
    for domain, metadata in domains.items():
        metadata = _mapping(metadata, "generation domain metadata")
        _exact_keys(metadata, {"artifact", "sha256"}, "generation domain metadata")
        if metadata["artifact"] != domain + ".md":
            raise ValueError("generation artifact name is invalid")
        _identifier(metadata["sha256"], "sha256", "generation artifact hash")
    _timestamp(value["created_at"], "generation created_at")
    identity = {key: item for key, item in value.items() if key != "generation_id"}
    expected = "gen_" + sha256_text(canonical_json(identity))[:20]
    if value["generation_id"] != expected:
        raise ValueError("generation_id does not match content")
    return value

def validate_head(value):
    value = _mapping(copy.deepcopy(value), "head")
    _exact_keys(value, {"schema_version", "generation_id"}, "head")
    if value["schema_version"] != HEAD_SCHEMA:
        raise ValueError("unsupported head schema")
    _identifier(value["generation_id"], "generation", "head generation_id")
    return value
```

Use `copy.deepcopy` on successful return. Reject booleans where integers are expected. Require domains in `{"work", "design", "write", "video"}`, kinds in `{"directive", "correction", "preference", "workflow", "retirement"}`, and timestamps matching `YYYY-MM-DDTHH:MM:SSZ` after a real `datetime.strptime` parse.

- [ ] **Step 4: Expose package version and package it**

`emulo_autopilot/__init__.py`:

```python
AUTOPILOT_VERSION = "0.1.0"
```

Modify the existing `project.scripts` and `tool.setuptools` tables in `pyproject.toml` to keep the current scripts unchanged and add package discovery. Do not create duplicate TOML tables:

```toml
[project.scripts]
emulo = "emulo:main"
emulo-cli = "emulo:main"

[tool.setuptools]
py-modules = ["emulo"]
packages = ["emulo_autopilot"]
```

Keep the existing compatibility comments on `emulo-cli`.

- [ ] **Step 5: Run focused and packaging tests**

Run:

```powershell
python -m unittest tests.test_autopilot_contracts tests.test_emulo -v
python -m build --wheel --outdir "$env:TEMP\emulo-autopilot-wheel"
python -c "import zipfile,glob; p=glob.glob(r'$env:TEMP\emulo-autopilot-wheel\*.whl')[-1]; z=zipfile.ZipFile(p); assert 'emulo_autopilot/contracts.py' in z.namelist()"
```

Expected: all tests pass and wheel assertion exits 0. If the `build` module is unavailable, use `python -m pip wheel . --no-deps -w "$env:TEMP\emulo-autopilot-wheel"` and record the command used.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml emulo_autopilot/__init__.py emulo_autopilot/contracts.py tests/autopilot_helpers.py tests/test_autopilot_contracts.py
git commit -m "feat: define strict Autopilot contracts"
```

### Task 2: Atomic local store and lock

**Files:**
- Create: `emulo_autopilot/store.py`
- Create: `tests/test_autopilot_store.py`

- [ ] **Step 1: Write failing store tests**

Cover initialization, path containment, candidate idempotency, conflicting same-ID bytes, append-only decisions, newest-decision selection, lock contention, explicit lock recovery, injected atomic-write failure, and corrupt-record fail-closed behavior.

```python
class AutopilotStoreTest(unittest.TestCase):
    def test_same_candidate_is_idempotent_but_conflict_fails(self):
        store = AutopilotStore(self.home)
        candidate = candidate_fixture()
        first = store.put_candidate(candidate)
        second = store.put_candidate(candidate)
        self.assertEqual(first, second)
        Path(first).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "existing candidate"):
            store.put_candidate(candidate)

    def test_lock_is_never_broken_implicitly(self):
        first = AutopilotStore(self.home)
        second = AutopilotStore(self.home)
        with first.lock("activate"):
            with self.assertRaisesRegex(RuntimeError, "locked"):
                with second.lock("activate"):
                    pass
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_autopilot_store -v`

Expected: FAIL because `emulo_autopilot.store` does not exist.

- [ ] **Step 3: Implement private paths and atomic writes**

Implement:

```python
import contextlib
import json
import os
import re
import socket
import stat
import tempfile
import time
import uuid

from .contracts import (
    canonical_json, validate_candidate, validate_decision,
)

class AutopilotStore:
    def __init__(self, emulo_home):
        self.emulo_home = os.path.realpath(os.path.abspath(emulo_home))
        self.root = os.path.join(self.emulo_home, "autopilot")

    def _child(self, *parts):
        for part in parts:
            if (not isinstance(part, str) or not part or part in {".", ".."}
                    or os.path.isabs(part) or os.sep in part
                    or (os.altsep and os.altsep in part)):
                raise ValueError("unsafe Autopilot path component")
        candidate = os.path.abspath(os.path.join(self.root, *parts))
        if os.path.commonpath([self.root, candidate]) != self.root:
            raise ValueError("Autopilot path escapes its root")
        probe = self.root
        for part in parts:
            probe = os.path.join(probe, part)
            if not os.path.lexists(probe):
                continue
            info = os.lstat(probe)
            if stat.S_ISLNK(info.st_mode) or (
                hasattr(info, "st_file_attributes")
                and info.st_file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            ):
                raise ValueError("Autopilot path cannot be a link or reparse point")
        return candidate

    def initialize(self):
        os.makedirs(self.emulo_home, mode=0o700, exist_ok=True)
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        for name in ("candidates", "decisions", "inbox", "generations", "operations"):
            os.makedirs(self._child(name), mode=0o700, exist_ok=True)
        return self.root

    def atomic_write_json(self, path, value):
        self.initialize()
        path = os.path.abspath(path)
        if os.path.commonpath([self.root, path]) != self.root:
            raise ValueError("write path escapes Autopilot root")
        parent = os.path.dirname(path)
        os.makedirs(parent, mode=0o700, exist_ok=True)
        payload = (canonical_json(value) + "\n").encode("utf-8")
        descriptor, staged = tempfile.mkstemp(prefix=".staged-", dir=parent)
        try:
            os.chmod(staged, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, path)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if os.path.exists(staged):
                os.unlink(staged)
        return path

    @contextlib.contextmanager
    def lock(self, operation):
        self.initialize()
        if not isinstance(operation, str) or not operation:
            raise ValueError("operation is required")
        operation_id = uuid.uuid4().hex
        path = self._child("lock.json")
        record = {
            "schema_version": "emulo.autopilot-lock/v1",
            "operation_id": operation_id,
            "operation": operation,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("Autopilot is locked; inspect status before recover-lock") from exc
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write((canonical_json(record) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            yield record
        finally:
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as handle:
                    current = json.load(handle)
                if current.get("operation_id") == operation_id:
                    os.unlink(path)
            except FileNotFoundError:
                pass

    def recover_lock(self, expected_operation_id):
        if not isinstance(expected_operation_id, str) or not re.fullmatch(r"[a-f0-9]{32}", expected_operation_id):
            raise ValueError("operation_id is invalid")
        path = self._child("lock.json")
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            value = json.load(handle)
        if set(value) != {"schema_version", "operation_id", "operation", "pid", "hostname", "created_at"} \
                or value["schema_version"] != "emulo.autopilot-lock/v1":
            raise ValueError("lock record is invalid")
        if value["operation_id"] != expected_operation_id:
            raise ValueError("operation_id does not match active lock")
        os.unlink(path)
        return value
```

On Windows, reject `FILE_ATTRIBUTE_REPARSE_POINT` paths. Lock records include `operation_id`, operation name, PID, hostname, and UTC creation time. A failed write must preserve the previous valid bytes.

- [ ] **Step 4: Implement candidates and decisions**

```python
    def put_candidate(self, candidate):
        candidate = validate_candidate(candidate)
        path = self._child("candidates", candidate["candidate_id"] + ".json")
        expected = (canonical_json(candidate) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing candidate bytes do not match identity")
            return path
        return self.atomic_write_json(path, candidate)

    def get_candidate(self, candidate_id):
        if not re.fullmatch(r"cand_[a-f0-9]{20}", candidate_id or ""):
            raise ValueError("candidate_id is invalid")
        path = self._child("candidates", candidate_id + ".json")
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                value = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("candidate is missing or corrupt") from exc
        return validate_candidate(value)

    def append_decision(self, decision):
        decision = validate_decision(decision)
        self.get_candidate(decision["candidate_id"])
        path = self._child("decisions", decision["decision_id"] + ".json")
        expected = (canonical_json(decision) + "\n").encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as handle:
                if handle.read() != expected:
                    raise ValueError("existing decision bytes do not match identity")
            return path
        return self.atomic_write_json(path, decision)

    def latest_decision(self, candidate_id):
        self.get_candidate(candidate_id)
        decisions = []
        root = self._child("decisions")
        if not os.path.isdir(root):
            return None
        for name in os.listdir(root):
            if not re.fullmatch(r"dec_[a-f0-9]{20}\.json", name):
                raise ValueError("unexpected decision file")
            path = self._child("decisions", name)
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                decision = validate_decision(json.load(handle))
            if decision["candidate_id"] == candidate_id:
                decisions.append(decision)
        if not decisions:
            return None
        return max(decisions, key=lambda item: (item["decided_at"], item["decision_id"]))
```

Decision identity is SHA-256 over canonical content excluding `decision_id`. Do not update candidate records with mutable status.

- [ ] **Step 5: Run store and existing profile-store tests**

Run:

```powershell
python -m unittest tests.test_autopilot_store tests.test_profile_store -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add emulo_autopilot/store.py tests/test_autopilot_store.py
git commit -m "feat: add atomic Autopilot local store"
```

### Task 3: Conservative policy engine

**Files:**
- Create: `emulo_autopilot/policy.py`
- Create: `tests/test_autopilot_policy.py`

- [ ] **Step 1: Write an exhaustive table test**

```python
class PolicyTest(unittest.TestCase):
    def test_policy_matrix(self):
        cases = [
            (candidate_fixture(evidence=3, strata=2), False, "review", "auto-disabled"),
            (candidate_fixture(evidence=3, strata=2), True, "safe", "repeated-explicit-low-risk"),
            (candidate_fixture(evidence=2, strata=2), True, "review", "insufficient-sessions"),
            (candidate_fixture(evidence=3, strata=1), True, "review", "insufficient-time-strata"),
            (candidate_fixture(contradiction_count=1), True, "review", "contradiction"),
            (candidate_fixture(risk_categories=["external-communication"]), True, "review", "prohibited-risk"),
            (candidate_fixture(kind="retirement"), True, "review", "retirement"),
        ]
        for candidate, enabled, expected_class, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                result = classify_candidate(candidate, auto_activate_enabled=enabled)
                self.assertEqual(expected_class, result.policy_class)
                self.assertEqual(expected_reason, result.reason)
```

Also test duplicate session IDs do not count, malformed candidates reject, and unknown risk categories reject rather than downgrade to review.

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_autopilot_policy -v`

Expected: FAIL because policy module does not exist.

- [ ] **Step 3: Implement pure deterministic classification**

```python
PolicyResult = collections.namedtuple("PolicyResult", "policy_class reason")

PROHIBITED_RISKS = frozenset({
    "security", "credentials", "permissions", "destructive",
    "purchase", "legal", "medical", "financial", "external-communication",
})

def classify_candidate(candidate, auto_activate_enabled=False):
    candidate = validate_candidate(candidate)
    if set(candidate["risk_categories"]) - PROHIBITED_RISKS:
        return PolicyResult("reject", "unknown-risk-category")
    if candidate["risk_categories"]:
        return PolicyResult("review", "prohibited-risk")
    if candidate["kind"] == "retirement":
        return PolicyResult("review", "retirement")
    if candidate["contradiction_count"]:
        return PolicyResult("review", "contradiction")
    sessions = {item["session_id"] for item in candidate["evidence"]}
    strata = {item["time_stratum"] for item in candidate["evidence"]}
    if len(sessions) < 3:
        return PolicyResult("review", "insufficient-sessions")
    if len(strata) < 2:
        return PolicyResult("review", "insufficient-time-strata")
    if not auto_activate_enabled:
        return PolicyResult("review", "auto-disabled")
    return PolicyResult("safe", "repeated-explicit-low-risk")
```

Policy output never activates anything. It only classifies.

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_autopilot_policy tests.test_autopilot_contracts -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add emulo_autopilot/policy.py tests/test_autopilot_policy.py
git commit -m "feat: classify Autopilot candidates conservatively"
```

## Completion gate

This plan is complete only when:

- strict candidate, decision, generation, and head contracts accept canonical valid fixtures and reject malformed or ambiguous records;
- candidates and decisions are immutable and idempotent by content-bound ID;
- local paths cannot escape `EMULO_HOME/autopilot` or traverse links/reparse points;
- a failed atomic write preserves previous valid bytes;
- locks are never broken implicitly and explicit recovery requires the exact operation ID;
- the complete policy table defaults to review and never activates anything;
- package build includes the new package while current `emulo` and `emulo-cli` entry points remain unchanged;
- focused tests and the existing profile-store tests pass;
- no file from the benchmark, site, or long-form video work is modified.

After this gate, write and execute the session/activation plan against the exact committed contracts. Do not start watcher, activation, Cloudflare, or billing work against unverified local formats.
