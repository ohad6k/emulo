# Ditto mining contracts

Ditto uses one bounded worker pass per selected segment, followed by one reducer pass over validated reports. Workers never read another segment and the reducer never reads raw session logs.

## Per-segment worker contract

Read the entire assigned segment. It contains only selected, redacted user messages grouped under stable `session:<id>` headers. Cover all three domains in the same pass:

- `work`: execution laws, verification habits, planning, debugging, shipping, and failure modes
- `design`: UI/UX taste, visual hierarchy, structural redesign rules, references, and rejections
- `write`: voice, marketing, social replies, product copy, phrasing, and tone

Return JSON only. The complete serialized report must be no more than 8,192 bytes, contain at most 12 evidence items, and use no quote longer than 200 characters.

```json
{
  "schema_version": "1",
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
    "write": "no-signal"
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

1. `domain_coverage` must contain exactly `work`, `design`, and `write`. Use `evidence` only when at least one evidence item exists for that domain; otherwise use `no-signal`.
2. Use only `session_ids` present in the selected segment. Coverage must list every session in the segment even when it has no useful signal.
3. Every quote and contradiction receipt must be short, dated, and verbatim from the named session. Never paraphrase inside `text`.
4. Use `kind: inferred` for a pattern the user demonstrates. Use `kind: explicit` only when the user directly states the instruction as a rule or unambiguous command.
5. Record counter-evidence in `contradictions` with the same `{session_id, date, text}` receipt shape. Do not hide it.
6. Ban generic filler such as “be helpful,” “write good code,” or “values quality.” If a stranger could guess it without the receipts, omit it.
7. A truthful all-`no-signal` report with an empty `evidence` list is valid. Invented evidence is not.

## Reducer contract

Read only the validated JSON report paths supplied by the run plan. Group evidence by domain and by meaning, preserving every referenced `evidence_id` and contradiction. An inferred rule requires corroboration from at least two distinct user sessions and, when the selected history provides it, two source/time strata. One unequivocal explicit instruction may survive with a `low-frequency` confidence label when it is uncontradicted.

Write a private profile pack in the exact assigned `pack_path`. The pack contains a core work profile, optional design and writing profiles only when their domains pass, a private receipt appendix, a card whose counts are distinct supporting sessions, and a draft manifest linking every installed rule to validated evidence IDs. Never use worker/report counts as proof and never invent receipts or file hashes.
