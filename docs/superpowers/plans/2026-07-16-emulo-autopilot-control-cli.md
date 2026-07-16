# Emulo Autopilot Local Control CLI Implementation Plan

**Goal:** Give users a safe local control surface for inspecting Autopilot, reviewing candidates, activating approved improvements, rolling back generations, and recovering an inspected lock.

**Architecture:** Keep storage validation in `AutopilotStore`, put user-facing state and review rules in a small `service.py`, and expose a JSON-first `emulo-autopilot` command. The CLI remains local-only and never reads raw session text, calls a model, contacts the cloud, or changes the existing `emulo` command.

**Tech Stack:** Python 3.8+ standard library, `argparse`, existing Autopilot contracts/store/policy, `unittest`.

## Boundaries

- Existing `emulo` and deprecated `emulo-cli` entry points remain byte-compatible.
- Candidate approval is impossible when deterministic policy returns `reject`.
- Every approval/rejection is an append-only decision; CLI never edits old decisions.
- Activation still requires the newest explicit approval and never edits the mined base profile.
- Status and lists return bounded metadata; no raw session messages, receipt bodies, source paths, or secrets.
- Lock recovery requires the exact operation ID displayed by status.
- No daemon, browser UI, sync, account, billing, or provider dashboard work in this slice.

### Task 1: Strict read-side store inventory

**Files:**
- Modify: `emulo_autopilot/store.py`
- Modify: `tests/test_autopilot_store.py`

- [x] Add failing tests for sorted candidate and generation inventory, unexpected files, corrupt records, and missing/valid/corrupt lock inspection.
- [x] Implement `list_candidates()`, `list_generations()`, and `get_lock()` using existing validators, exact filename patterns, regular non-link paths, and fail-closed errors.
- [x] Run `python -m unittest tests.test_autopilot_store -v` and commit `feat: expose strict Autopilot local inventory`.

### Task 2: Review and status service

**Files:**
- Create: `emulo_autopilot/service.py`
- Create: `tests/test_autopilot_service.py`

- [x] Add failing tests for empty/locked/active status, pending queue classification, explicit approve/reject decisions, reject-policy approval refusal, and newest-decision state.
- [x] Implement `status_snapshot(store)`, `review_queue(store)`, and `record_review(store, candidate_id, decision, reason, decided_at)`.
- [x] Derive `policy_class` with `classify_candidate(..., auto_activate_enabled=False)`; reject approval when it returns `reject` and permit an explicit rejection record.
- [x] Return versioned JSON-safe dictionaries with IDs, statements, domains, kinds, policy reasons, decision state, counts, and active generation only.
- [x] Run `python -m unittest tests.test_autopilot_service tests.test_autopilot_store -v` and commit `feat: add local Autopilot review service`.

### Task 3: JSON-first CLI and package entry point

**Files:**
- Create: `emulo_autopilot/cli.py`
- Create: `tests/test_autopilot_cli.py`
- Modify: `pyproject.toml`

- [ ] Add failing tests for `status`, `queue`, `review`, `activate`, `rollback`, and exact-ID `recover-lock`, plus JSON stderr and nonzero exit on refusal.
- [ ] Implement `main(argv=None)` with global `--emulo-home` and subcommands. Generate UTC-second timestamps internally; do not expose timestamp spoofing flags.
- [ ] Add only `emulo-autopilot = "emulo_autopilot.cli:main"`; retain both existing entry points unchanged.
- [ ] Verify a built wheel contains the package and all three console scripts.
- [ ] Run the full suite, then commit `feat: add safe Autopilot control CLI`.

## Completion gate

- Full suite and wheel verification pass.
- Users can inspect, approve/reject, activate, rollback, and recover an inspected lock locally.
- No raw session text or receipt body is printed or persisted by the control layer.
- No existing Emulo command behavior changes.
- No cloud/provider action has been taken.
