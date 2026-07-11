# Ditto plugin bounded-mining dogfood

Date: 2026-07-11

## Verdict

No bounded starter candidate passed the frozen private calibration gate. Candidate 2 was the final evaluated candidate, so there is no smallest passing bounded default. Calibration stopped before live host probes. The approved release fallback keeps full-history mining as the quality default and permits bounded mining only as an explicitly labeled quick preview.

The frozen checklist was not changed after candidate output was seen.

## Private calibration identity

- Checklist schema: `1`
- Checklist SHA-256: `9778cb1eb2fcdbd7aafed01600fc7a1ceaf59f99943d54b692b0aaff9efaab09`
- Required items: work `10`, design `5`, write `7`
- Private reports, receipts, profiles, and checklist contents committed to Git: `0`

## Candidate results

| Candidate | Selected source tokens | Cache hits at prepare | Planned workers | Actual worker passes | Planned reducers | Actual reducer passes | Frozen recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 59,473 | 3 | 1 | 3 | 1 | 1 | work 2/10, design 0/5, write 0/7 |
| 1 | 109,245 | 4 | 2 | 2 | 1 | 1 | work 2/10, design 0/5, write 0/7 |
| 2 | 159,919 | 5 | 3 | 3 | 1 | 1 | work 2/10, design 2/5, write 1/7 |

Candidate 0 needed two replacement host attempts because the first two worker environments were read-only. Candidate 1's first worker report was filtered locally and fail-closed: only evidence with valid verbatim receipts was retained, with no additional model pass. Candidate 2 used exactly the approved three workers and one reducer, with no retry.

Total calibration model passes: `11` (`8` worker passes and `3` reducer passes). Separately counted host-task interactions: `11`. Local preflight, preparation, validation, caching, activation, and checklist comparison were not counted as model passes or host-task interactions.

## Final validated pack

- Frozen run: `20260711T154238Z-7258a239`
- Profile version: `dc2507ed1e0f123ea46f`
- Active profile manifest SHA-256: `c425ca9c8319d069552f5b73f0ecdff3611974dbe74e6ad606d3a947b889af1f`
- Report-set SHA-256: `427a4a12a121a32355970834a9702e260c35baa08c1e47881c7bf5594ecbee8d`
- Work domain: active, `2/10` frozen requirements recovered
- Design domain: active, `2/5` frozen requirements recovered
- Write domain: active, `1/7` frozen requirements recovered

The final pack is structurally and evidentially valid. Recovering `5/22` requirements does not satisfy the product-quality contract.

## Host-task probes and human verdicts

Fresh installed-plugin host tasks: `0`.

- Work verdict: not run; the frozen checklist failed first.
- Design verdict: not run; the frozen checklist failed first.
- Write verdict: not run; the frozen checklist failed first.

This preserves the gate order and avoids spending host interactions on a candidate that already failed objective recall.

## Findings

- Live source churn changed candidate 2 from two planned workers at preflight to three at preparation. The revised cost was disclosed and approved before model work.
- Candidate 1's selected source and validated reports contained design and writing material, but the reducer could not form supported active design and write profiles. Its failure was not merely a work-only selection.
- Candidate 2 activated all three domains but still recovered only `5/22` frozen requirements. Partial thematic overlaps were not counted as passes.
- Every worker and reducer output was validated. Invalid non-verbatim evidence was dropped fail-closed, and the private checklist was not loosened or edited.
- Extraction and redaction happened locally. The selected redacted text was processed by the user-chosen cloud model; `ditto.py` made no network calls, and worker tool network access was disabled while corpus content was present.

## Release consequence

Do not claim candidate 0, 1, or 2 is sufficient for a full profile. Full-history mining is the quality default. Bounded mining may ship only as a quick preview with the exact limitation that it creates a starter profile from selected history, not the full profile. Any future attempt to make bounded mining the quality default must retain this baseline and pass all `22/22` requirements against the same frozen checklist. Adaptive recall remains experimental and outside the release path.

## Task 17 live host evidence

Host: Codex CLI `0.142.5` on Windows. Development plugin: `ditto@ditto`, installed version `0.0.0-dev` after a cachebuster proof with `0.0.0-dev+codex.20260711163821`.

- Installed plugin discovery contained exactly `mine`, `work`, `design`, and `write` skill directories.
- Plugin uninstall/reinstall preserved a disposable two-file `DITTO_HOME`: the sorted relative-path SHA-256 lists matched exactly before and after.
- The real global deep profile at `~/.codex/skills/ditto/SKILL.md` was detected and left byte-for-byte unchanged. No real migration or cutover was attempted.
- Positive routing was not uniformly clean under the host's 2% skill-description budget. Design loaded `ditto:design` and its active core/design profiles end to end. Clean native-only tasks selected `ditto:work` and `ditto:write`, but a disposable-home policy blocked the normal Python profile helper in part of that proof. The real host also allowed the old global `ditto` profile to compete with namespaced routing.
- Negative routing kept `ditto:mine` inactive. The task loaded the old global `ditto` profile plus `ditto:work`.
- Combined routing loaded the old global `ditto` profile plus `ditto:design` and `ditto:write`; it did not load `ditto:work` or `ditto:mine`. Both active domain profile paths resolved and were read.
- The native-plugin plus local skills.sh coexistence answer chose `ditto:mine` as the sole setup owner. The host task timed out after producing that answer and attempted an overbroad skill-location lookup, so this is not recorded as a clean pass.
- Task 17 used `11` model-backed host interactions across initial, isolated, clean-native, coexistence, negative, and combined probes. No interaction ran Ditto mining workers or a reducer.

### Cache and update evidence

- Live current-corpus quick-preview preflight was not zero-call: source churn selected `69,030` tokens with `3` cached segments, `1` uncached segment, `1` planned worker, and `1` planned reducer. No calls were approved or run.
- The deterministic full-history cache fixture passed with `0` planned workers and `0` planned reducers after validated report and reduction-cache hits.
- Incremental fixture proofs retained existing segment hashes and isolated only affected new work.
- Full-history mining has not run live in the new format. Until the Task 19 real-corpus gate runs, the full path is fixture-verified only.

### Migration and host boundaries

- Disposable Codex migration staged, cut over, exposed exactly one profile path, then rolled back. Rollback restored the exact legacy SHA-256 and left the new active pointer absent.
- Native Claude remains unclaimed because no Claude executable is available. The direct Claude adapter installed an exact profile successfully in a disposable home.

## Task 18 independent reviews

The release diff from `v0.1.2` through `328ecc61` received separate read-only spec-compliance and Python safety/quality reviews. Both reviewers returned `PASS` on the final candidate commit.

Verified findings were fixed test-first across four commits: release safety gates, strict reduction-cache validation, content-derived manifest identity and usable domain invariants, rollback compensation, and exact agreement between zero-call preflight and cached activation. Final local evidence: `127` unit tests passed, the Codex plugin validator passed, the bootstrap skill validator passed, both CLI help surfaces exited `0`, JSON manifests parsed, and `git diff --check` exited `0`.
