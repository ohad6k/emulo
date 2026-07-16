# Ditto mining contracts

The Plugin release uses one bounded worker pass per selected segment, followed by one reducer pass over validated reports. Workers never read another segment and the reducer never reads raw session logs.

## Experimental adaptive packet scout contract

Read only the assigned frozen receipt packet. Maximize recall independently for `work`, `design`, `write`, and `video`; do not merge rules across packets. Each domain has its own ceiling of 12 evidence items. Return JSON schema `3` with the exact `packet_hash`, all assigned `receipt_ids`, exact `source_tokens`, and an explicit `evidence` or `no-signal` state for every domain.

Every evidence item includes `domain`, `kind`, `scope`, `context`, `signal_family`, a concrete instruction and implication, plus exact receipt objects shaped as `{receipt_id, session_id, date, text}`. `scope` is either `universal` or `contextual`; contextual evidence must name the context. `write` evidence additionally requires a `register` per the register rules below; no other domain may carry one. Quotes and contradictions must copy the packet receipt text and date verbatim. The complete canonical JSON report may not exceed 24,576 bytes.

Before returning, run `python "$DITTO_PY" plugin validate-scout --run-id "$RUN_ID" --packet-hash "$PACKET_HASH" --report "$REPORT_PATH"`. Correct rejected output inside the same scout pass. The orchestrator caches only validated content-addressed reports.

The schema-1 segment contract below exists only for explicitly enabled legacy reproduction.

## Per-segment worker contract

Read the entire assigned segment. It contains only selected, redacted user messages grouped under stable `session:<id>` headers. Cover all four domains in the same pass:

- `work`: execution laws, verification habits, planning, debugging, shipping, and failure modes
- `design`: UI/UX taste, visual hierarchy, structural redesign rules, references, and rejections
- `write`: voice, marketing, social replies, product copy, phrasing, and tone
- `video`: motion and pacing taste, caption style, voiceover and clarity choices, character and shot selection, render and tooling decisions, and rejections

Every `write` evidence item must also carry a `register` classifying the voice by audience:

- `casual`: banter, friends, community replies, and the user's messages to the agent itself. Text addressed to the agent is casual signal only; it never supports a professional register.
- `professional`: writing aimed at a boss, client, customer, formal email, documentation, or official product copy.
- `shared`: a voice law that holds regardless of audience (a banned phrase, a punctuation rule, a structural tell). If a stranger reading only the receipts could not tell which audience it came from, it is not `shared` by default; classify by the receipts' actual audience.

Classify from the receipts, never from guesswork: who the text addresses, the platform it targets, and the artifact type. `register` is valid only on `write` evidence.

Return JSON only. The complete serialized report must be no more than 8,192 bytes, contain at most 12 evidence items, and use no quote longer than 200 characters.

```json
{
  "schema_version": "2",
  "segment_hash": "<exact assigned segment hash>",
  "coverage": {
    "session_ids": ["<every session id in the segment, exactly once>"],
    "sources": ["<exact segment source>"],
    "first_date": "<exact segment first date>",
    "last_date": "<exact segment last date>",
    "source_tokens": 20000
  },
  "domain_coverage": {
    "work": "evidence",
    "design": "no-signal",
    "write": "no-signal",
    "video": "no-signal"
  },
  "evidence": [
    {
      "evidence_id": "ev-<first 8 chars of segment hash>-<short-lowercase-slug>",
      "domain": "work",
      "kind": "inferred",
      "instruction": "<specific user law or constraint>",
      "implication": "<concrete behavior an agent must perform>",
      "quotes": [
        {"session_id": "<covered id>", "date": "YYYY-MM-DD", "text": "<short verbatim quote>"}
      ],
      "contradictions": []
    }
  ]
}
```

Rules:

1. `domain_coverage` must contain exactly `work`, `design`, `write`, and `video`. Use `evidence` only when at least one evidence item exists for that domain; otherwise use `no-signal`.
2. Use only `session_ids` present in the selected segment. Coverage must list every session in the segment even when it has no useful signal.
3. Every quote and contradiction receipt must be short, dated, and verbatim from the named session. Set `date` from the exact containing `[YYYY-MM-DD]` message header, not another message or the session date range. Never paraphrase inside `text`.
4. Use `kind: inferred` for a pattern the user demonstrates. Use `kind: explicit` only when the user directly states the instruction as a rule or unambiguous command.
5. Record counter-evidence in `contradictions` with the same `{session_id, date, text}` receipt shape. Do not hide it.
6. Ban generic filler such as “be helpful,” “write good code,” or “values quality.” If a stranger could guess it without the receipts, omit it.
7. A truthful all-`no-signal` report with an empty `evidence` list is valid. Invented evidence is not.
8. Every `write` evidence item requires `"register": "casual" | "professional" | "shared"` per the register rules above. No `work`, `design`, or `video` item may carry a `register`.

Before returning, run the assigned read-only `python "$DITTO_PY" plugin validate-report --run-id "$RUN_ID" --report "$REPORT_PATH"` command. If it rejects the report, correct the report and run the same validation again inside this worker pass. Return only after it reports `status: valid`. The orchestrator caches the report after the worker exits.

## Experimental adaptive isolated domain reducer contract

Run one reducer for exactly one named domain. Read only that domain's validated evidence projection; never read another domain or raw history. Write one assigned JSON draft using schema `2`, the exact `domain` and `evidence_set_hash`, an `active` or permitted `inactive` status, rules with preserved evidence IDs and scope, discarded conflict records, and coverage counts for evidence items, distinct sessions, strata, and unresolved contradictions.

An inferred rule needs two distinct sessions and two available source/time strata. A single-provider pattern may qualify across two time strata. Contextual evidence cannot become a universal rule. Unresolved contradictions must be discarded, not installed. Work must remain active; inactive design/write/video drafts use the exact instruction `run ditto and deepen <domain>`.

Every `write` rule carries a `register`. When all referenced evidence shares one register, the rule keeps exactly that register; evidence from mixed registers reduces to `shared`. A rule may never claim a register its evidence does not show.

Before returning, run `python "$DITTO_PY" plugin validate-domain --run-id "$RUN_ID" --domain "$DOMAIN" --draft "$DRAFT_PATH"`. Correct rejected output within the same reducer pass. The orchestrator content-addresses only validated domain drafts.

## Legacy combined reducer contract

Read only the validated JSON report paths supplied by the run plan. Group evidence by domain and meaning while preserving every referenced `evidence_id` and contradiction. An inferred rule requires corroboration from at least two distinct user sessions and, when the selected history provides it, two source/time strata. One unequivocal explicit instruction may survive with `kind: explicit` and `confidence: low-frequency` when it is uncontradicted.

Write this complete private pack in the exact assigned `pack_path`:

```text
you.md
you-designer.md (only when design passes)
you-writer.md   (only when write passes)
you-video.md    (only when video passes)
appendix.md
card.json
draft-manifest.json
```

Use exact profile frontmatter names: `ditto-work-profile`, `ditto-design-profile`, `ditto-write-profile`, and `ditto-video-profile`. Every active profile must contain each installed rule and its operational implication.

An active `you-writer.md` groups its rules under exact register headings: `## Voice laws` for `shared` rules, `## Casual register` for `casual`, and `## Professional register` for `professional`. Omit a heading only when no rule carries that register. Every write rule in `draft-manifest.json` carries a `register` following the reducer register rules: a rule keeps its evidence's single shared register, and mixed-register evidence reduces to `shared`.

`draft-manifest.json` uses this shape:

```json
{
  "schema_version": "1",
  "profile_id": "default",
  "report_set_hash": "<exact run report_set_hash>",
  "domains": {
    "work": {
      "status": "active",
      "file": "you.md",
      "rules": [
        {
          "text": "<specific rule>",
          "implication": "<operational behavior>",
          "kind": "inferred",
          "evidence_ids": ["<validated id 1>", "<validated id 2>"]
        }
      ]
    },
    "design": {
      "status": "inactive",
      "reason": "insufficient evidence",
      "deepen_instruction": "run ditto and deepen design"
    },
    "write": {
      "status": "inactive",
      "reason": "insufficient evidence",
      "deepen_instruction": "run ditto and deepen write"
    },
    "video": {
      "status": "inactive",
      "reason": "insufficient evidence",
      "deepen_instruction": "run ditto and deepen video"
    }
  }
}
```

Work must be active. Activate design, write, or video only when that domain has valid rules, then use its exact filename and the same rule shape. Otherwise keep the exact inactive state above.

`appendix.md` contains every referenced evidence ID and every exact dated private quote or contradiction receipt behind it. Never turn unresolved contradiction into an installed rule.

`card.json` contains an archetype, up to three work-domain laws, and an optional truth. Each law text must exactly match a validated work rule. Its count is the number of distinct supporting sessions, formatted like `12 sessions`, never a worker/report count.

The truth must sting. Name the cost, not the habit: what it breaks, when it bites, and what it keeps costing them. If it could pass as a compliment or a LinkedIn strength ("cares deeply about quality"), it failed. Rewrite it until it is the line they would wince at before admitting it is true. Use no softeners such as "sometimes," "can tend to," or "a bit." Calibration for the right sharpness: "Their real bottleneck is trust recovery: once scope gets misread or success gets claimed without proof, they stop building the product and start building the process, until reality is observable again."

Do not invent file hashes. Python validates this draft pack, computes every file hash and immutable profile version, and refuses incomplete or generic output.

Before returning, run the assigned read-only `python "$DITTO_PY" plugin validate-pack --run-id "$RUN_ID" --pack "$PACK_DIR"` command. If it rejects the pack, correct only the assigned pack and run the same validation again inside this reducer pass. Return only after it reports `status: valid`. The orchestrator activates the pack after the reducer exits.
